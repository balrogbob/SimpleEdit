# -*- coding: utf-8 -*-
import re
import sys
import os
import json
import subprocess
import threading
import tempfile
import datetime
import socket
from collections import deque
from typing import List, Tuple, Dict, Any

# Minimal, tkinter-free worker module used by the main process via a separate subprocess.
# Keeps imports small so child processes start quickly.

# Compile stable regexes used by workers.
NUMBER_PATTERN = r'\b(?:0b[01_]+|0o[0-7_]+|0x[0-9A-Fa-f_]+|\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?)(?:[jJ])?\b'
NUMBER_RE = re.compile(NUMBER_PATTERN)
DECORATOR_RE = re.compile(r'(?m)^\s*@([A-Za-z_]\w*)')
CLASS_RE = re.compile(r'\bclass\s+([A-Za-z_]\w*)')
ATTRIBUTE_RE = re.compile(r'\.([A-Za-z_]\w*)')
DUNDER_RE = re.compile(r'\b__\w+__\b')
VAR_ASSIGN_RE = re.compile(r'(?m)^[ \t]*([A-Za-z_]\w*)\s*=')
SELFS_RE = re.compile(r'\b(?:[a-z])(?:[A-Z]?[a-z])*(?:[A-Z][a-z]*)|\b(self|root|after)\b')

# Local defaults for keywords/builtins (will be overridden if config present)
KEYWORDS: List[str] = []
BUILTINS: List[str] = []
KEYWORD_RE = re.compile(r'\b\b')
BUILTIN_RE = re.compile(r'\b\b')

# Additional regex slots that may be overridden by config
STRING_RE = re.compile(r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"[^"\n]*"|' + r"'[^'\n]*')", re.DOTALL)
COMMENT_RE = re.compile(r'#[^\n]*')
CONSTANT_RE = re.compile(r'(?m)^[ \t]*([A-Z][_A-Z0-9]+)\s*=')
TODO_RE = re.compile(r'#.*\b(TODO|FIXME|NOTE)\b', re.IGNORECASE)
VAR_ANNOT_RE = re.compile(r'(?m)^[ \t]*([A-Za-z_]\w*)\s*:\s*([^=\n]+)(?:=.*)?$')
FSTRING_RE = re.compile(r"(?:[fF][rRuU]?|[rR][fF]?)(\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?'''|\"[^\n\"]*\"|'[^\\n']*')", re.DOTALL)
CLASS_BASES_RE = re.compile(r'(?m)^[ \t]*class\s+[A-Za-z_]\w*\s*\(([^)]*)\)')

# ---- stderr capture globals ------------------------------------------------
# per-server stderr file paths and in-memory tail buffers for quick inspection
_server_stderr_paths: List[str] = []
_server_stderr_threads: List[threading.Thread] = []
_server_stderr_buffers: List[deque] = []

# ---- config-driven regex loader -------------------------------------------
def _load_syntax_from_config():
    """
    Attempt to read syntax overrides from the main application's config (via functions.config).
    If available, update module-level KEYWORDS/BUILTIN lists and compiled regex objects.
    This runs inside the worker process and is defensive: failure -> keep defaults.
    """
    try:
        # Import functions (module used by main app). This only reads config; avoid GUI interactions.
        import functions as funcs  # type: ignore
        cfg = getattr(funcs, 'config', None)
        if cfg is None or not cfg.has_section('Syntax'):
            return False

        # Keywords / builtins CSV
        kw_csv = cfg.get('Syntax', 'keywords.csv', fallback=None)
        bk_csv = cfg.get('Syntax', 'builtins.csv', fallback=None)

        global KEYWORDS, BUILTINS, KEYWORD_RE, BUILTIN_RE
        if kw_csv is not None:
            kws = [x.strip() for x in kw_csv.split(',') if x.strip()]
            KEYWORDS = kws
            try:
                KEYWORD_RE = re.compile(r'\b(' + r'|'.join(map(re.escape, KEYWORDS)) + r')\b') if KEYWORDS else re.compile(r'\b\b')
            except Exception:
                KEYWORD_RE = re.compile(r'\b\b')
        if bk_csv is not None:
            bks = [x.strip() for x in bk_csv.split(',') if x.strip()]
            BUILTINS = bks
            try:
                BUILTIN_RE = re.compile(r'\b(' + r'|'.join(map(re.escape, BUILTINS)) + r')\b') if BUILTINS else re.compile(r'\b\b')
            except Exception:
                BUILTIN_RE = re.compile(r'\b\b')

        # Generic regex overrides (if present)
        # Keys that require DOTALL
        dotall_keys = {'STRING_RE', 'FSTRING_RE'}
        # Map config key -> module variable name
        keys = [
            'STRING_RE', 'COMMENT_RE', 'NUMBER_RE', 'DECORATOR_RE', 'CLASS_RE', 'VAR_ASSIGN_RE',
            'CONSTANT_RE', 'ATTRIBUTE_RE', 'TODO_RE', 'SELFS_RE', 'VAR_ANNOT_RE', 'FSTRING_RE',
            'DUNDER_RE', 'CLASS_BASES_RE'
        ]
        for key in keys:
            cfg_key = f'regex.{key}'
            pat = cfg.get('Syntax', cfg_key, fallback=None)
            if not pat:
                continue
            try:
                compiled = re.compile(pat, re.DOTALL) if key in dotall_keys else re.compile(pat)
                globals()[key] = compiled
            except Exception:
                # ignore bad patterns
                pass

        return True
    except Exception:
        return False

# ---- slice processing (pure worker logic) ----------------------------------
def process_slice(content: str, s_start: int, s_end: int, protected_spans: List[Tuple[int, int]],
                  keywords: List[str], builtins: List[str]) -> Dict[str, List[Tuple[int, int]]]:
    """
    Scan substring content[s_start:s_end] and return a dict mapping tag -> list[(abs_s, abs_e)].
    protected_spans is a list of (s,e) absolute offsets to be skipped.
    keywords and builtins are lists of strings (may be empty).
    """
    rd = {
        'number': [], 'decorator': [], 'class_name': [], 'attribute': [],
        'def': [], 'keyword': [], 'builtin': [], 'selfs': [], 'variable': []
    }

    try:
        seg = content[s_start:s_end]
        base = s_start

        # Compile keyword/builtin regexes locally (prefer passed lists, fall back to module-level)
        try:
            kw_list = keywords if keywords else KEYWORDS
            if kw_list:
                KEYWORD_LOCAL = re.compile(r'\b(' + r'|'.join(map(re.escape, kw_list)) + r')\b')
            else:
                KEYWORD_LOCAL = re.compile(r'\b\b')
        except Exception:
            KEYWORD_LOCAL = re.compile(r'\b\b')

        try:
            bk_list = builtins if builtins else BUILTINS
            if bk_list:
                BUILTIN_LOCAL = re.compile(r'\b(' + r'|'.join(map(re.escape, bk_list)) + r')\b')
            else:
                BUILTIN_LOCAL = re.compile(r'\b\b')
        except Exception:
            BUILTIN_LOCAL = re.compile(r'\b\b')

        def overlaps_protected(a: int, b: int) -> bool:
            for ps, pe in protected_spans:
                if not (b <= ps or a >= pe):
                    return True
            return False

        # Numbers
        for m in NUMBER_RE.finditer(seg):
            s, e = m.span()
            if not overlaps_protected(base + s, base + e):
                rd['number'].append((base + s, base + e))

        # Decorators (line-anchored)
        for m in DECORATOR_RE.finditer(seg):
            try:
                s, e = m.span(1)
            except Exception:
                s, e = m.span()
            if not overlaps_protected(base + s, base + e):
                rd['decorator'].append((base + s, base + e))

        # Classes
        for m in CLASS_RE.finditer(seg):
            try:
                s, e = m.span(1)
            except Exception:
                s, e = m.span()
            if not overlaps_protected(base + s, base + e):
                rd['class_name'].append((base + s, base + e))

        # Attributes (a.b -> 'b')
        for m in ATTRIBUTE_RE.finditer(seg):
            try:
                s, e = m.span(1)
            except Exception:
                s, e = m.span()
            if not overlaps_protected(base + s, base + e):
                rd['attribute'].append((base + s, base + e))

        # Dunder names
        for m in DUNDER_RE.finditer(seg):
            s, e = m.span()
            if not overlaps_protected(base + s, base + e):
                rd['def'].append((base + s, base + e))

        # Keywords & builtins
        for m in KEYWORD_LOCAL.finditer(seg):
            s, e = m.span()
            if not overlaps_protected(base + s, base + e):
                rd['keyword'].append((base + s, base + e))
        for m in BUILTIN_LOCAL.finditer(seg):
            s, e = m.span()
            if not overlaps_protected(base + s, base + e):
                rd['builtin'].append((base + s, base + e))

        # self/attribute-like names
        for m in SELFS_RE.finditer(seg):
            s, e = m.span()
            if not overlaps_protected(base + s, base + e):
                rd['selfs'].append((base + s, base + e))

        # local variable assignments
        for m in VAR_ASSIGN_RE.finditer(seg):
            try:
                s, e = m.span(1)
            except Exception:
                s, e = m.span()
            if not overlaps_protected(base + s, base + e):
                rd['variable'].append((base + s, base + e))

    except Exception:
        # Worker should be resilient and return an empty-ish dict on failure.
        pass

    return rd

# ---- subprocess server support (multi-server) ------------------------------
# The server mode runs when syntax_worker.py is executed as a script with --serve.
# The parent process can call map_slices(...) which will send a JSON request to one of the
# running server processes. A lightweight round-robin is used to distribute slices.
#
# This design avoids importing the application's main module inside worker processes
# (which would otherwise cause Tk GUI side-effects when the spawn start method is used).

_server_procs: List[subprocess.Popen] = []
_server_locks: List[threading.Lock] = []
_server_stdins: List = []
_server_stdouts: List = []
_next_server = 0
_server_index_lock = threading.Lock()

def _stderr_reader_thread(proc: subprocess.Popen, stderr_path: str, buffer: deque):
    """
    Read proc.stderr lines and write to a rotating file + in-memory tail buffer.
    Runs in a daemon thread.

    Writes an initial header line immediately so the file is created even if the
    child hasn't produced stderr yet (this addresses the "no file created" symptom).
    """
    try:
        # Ensure file exists and write header immediately so user can find it
        try:
            os.makedirs(os.path.dirname(stderr_path), exist_ok=True)
        except Exception:
            pass

        with open(stderr_path, 'a', encoding='utf-8', errors='replace') as fh:
            header = f"=== syntax_worker stderr log started at {datetime.datetime.utcnow().isoformat()}Z ===\n"
            try:
                fh.write(header)
                fh.flush()
            except Exception:
                pass

            # read from proc.stderr (text mode)
            # Use readline loop so buffered lines are emitted as they appear.
            while True:
                # proc.stderr.readline() returns '' on EOF
                line = proc.stderr.readline()
                if line == '':
                    # process may have terminated or closed stderr — still keep file
                    break
                ts = datetime.datetime.utcnow().isoformat() + "Z "
                try:
                    fh.write(ts + line)
                    fh.flush()
                except Exception:
                    pass
                # push to small in-memory tail buffer (no newlines inside entries)
                try:
                    buffer.append(ts + line.rstrip('\n'))
                except Exception:
                    pass
    except Exception:
        # never let stderr capture crash caller
        pass

def start_servers(count: int) -> None:
    """
    Spawn `count` worker processes and connect to each worker's TCP server.

    Worker process creates a listening socket on localhost and prints a JSON
    ready line containing the port. Parent connects to that port and uses the
    socket makefile for convenient text I/O (JSON lines).
    """
    global _server_procs, _server_locks, _server_stdins, _server_stdouts
    global _server_stderr_paths, _server_stderr_threads, _server_stderr_buffers
    try:
        if count <= 0:
            return
        if len(_server_procs) >= count:
            return

        # directory for on-disk logs (easy to find in project root)
        try:
            base_logs = os.path.abspath(os.path.join(os.getcwd(), "worker_logs"))
            os.makedirs(base_logs, exist_ok=True)
        except Exception:
            base_logs = tempfile.gettempdir()

        for _ in range(len(_server_procs), count):
            cmd = [sys.executable, '-u', os.path.abspath(__file__), '--serve']
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            lock = threading.Lock()

            # prepare stderr capture targets (unchanged)
            pid = getattr(proc, "pid", None) or id(proc)
            stderr_path = os.path.join(base_logs, f"syntax_worker_{pid}.stderr.log")
            stderr_buffer = deque(maxlen=400)
            try:
                with open(stderr_path, 'a', encoding='utf-8', errors='replace') as fh:
                    try:
                        fh.write(f"=== log file created {datetime.datetime.utcnow().isoformat()}Z (pid={pid}) ===\n")
                        fh.flush()
                    except Exception:
                        pass
            except Exception:
                try:
                    stderr_path = os.path.join(tempfile.gettempdir(), f"syntax_worker_{pid}.stderr.log")
                    with open(stderr_path, 'a', encoding='utf-8', errors='replace'):
                        pass
                except Exception:
                    stderr_path = ""

            thr = None
            if proc.stderr is not None and stderr_path:
                thr = threading.Thread(target=_stderr_reader_thread, args=(proc, stderr_path, stderr_buffer), daemon=True)
                thr.start()

            # Read worker ready JSON from stdout (blocks briefly)
            port = None
            try:
                ready_line = proc.stdout.readline()
                if ready_line:
                    try:
                        j = json.loads(ready_line)
                        port = j.get("port")
                    except Exception:
                        # old workers may only send {"ready":true}; fall through
                        pass
            except Exception:
                pass

            # If worker didn't print a port, fall back to stdio mode (previous behavior)
            if not port:
                # keep using proc.stdin/proc.stdout for compatibility
                _server_procs.append(proc)
                _server_locks.append(lock)
                _server_stdins.append(proc.stdin)
                _server_stdouts.append(proc.stdout)
                _server_stderr_paths.append(stderr_path)
                _server_stderr_threads.append(thr)
                _server_stderr_buffers.append(stderr_buffer)
                continue

            # connect to worker TCP server
            try:
                sock = socket.create_connection(('127.0.0.1', int(port)), timeout=5)
                # text-mode file objects for convenient readline()/write()
                fr = sock.makefile('r', encoding='utf-8', newline='\n')
                fw = sock.makefile('w', encoding='utf-8', newline='\n')
                _server_procs.append(proc)
                _server_locks.append(lock)
                _server_stdins.append(fw)    # write JSON requests to fw
                _server_stdouts.append(fr)   # read JSON responses from fr
                _server_stderr_paths.append(stderr_path)
                _server_stderr_threads.append(thr)
                _server_stderr_buffers.append(stderr_buffer)
            except Exception:
                # connection failed -> fallback to stdio files
                try:
                    _server_procs.append(proc)
                    _server_locks.append(lock)
                    _server_stdins.append(proc.stdin)
                    _server_stdouts.append(proc.stdout)
                    _server_stderr_paths.append(stderr_path)
                    _server_stderr_threads.append(thr)
                    _server_stderr_buffers.append(stderr_buffer)
                except Exception:
                    pass
    except Exception:
        pass

def stop_servers() -> None:
    """Shutdown all server subprocesses cleanly (best-effort)."""
    global _server_procs, _server_locks, _server_stdins, _server_stdouts
    global _server_stderr_paths, _server_stderr_threads, _server_stderr_buffers
    try:
        for stdin, proc, lock in zip(_server_stdins, _server_procs, _server_locks):
            try:
                with lock:
                    try:
                        stdin.write(json.dumps({"action":"shutdown"}) + "\n")
                        stdin.flush()
                    except Exception:
                        pass
                try:
                    proc.wait(timeout=1)
                except Exception:
                    proc.kill()
            except Exception:
                pass
    finally:
        _server_procs = []
        _server_locks = []
        _server_stdins = []
        _server_stdouts = []
        # leave stderr log files in temp dir for inspection but clear in-memory structures
        _server_stderr_paths = []
        _server_stderr_threads = []
        _server_stderr_buffers = []

def get_all_worker_stderr_tail() -> List[str]:
    """Return concatenated in-memory tail lines for all workers (most recent first per worker)."""
    out = []
    try:
        for buf in _server_stderr_buffers:
            # return as joined string (newest lines last)
            out.append("\n".join(list(buf)))
    except Exception:
        pass
    return out

def get_worker_stderr_path(index: int) -> str:
    """Return filesystem path to stored stderr log for worker `index` or ''."""
    try:
        return _server_stderr_paths[index]
    except Exception:
        return ""

def map_slices(content: str, ranges: List[Tuple[int, int]],
               protected_spans: List[Tuple[int, int]], keywords: List[str],
               builtins: List[str], processes: int = 1) -> List[Dict[str, Any]]:
    """
    Distribute `ranges` across available worker connections and collect results.

    Changes:
    - If a single full-file range was supplied but multiple workers exist,
      proactively slice that single range into N worker chunks (with small
      overlap) so work actually gets distributed instead of being sent whole
      to one worker.
    - Otherwise partition ranges round-robin across servers as before.
    - Any ranges that don't receive a response are processed locally as fallback.
    """
    global _next_server
    # quick sanity
    total_ranges = len(ranges)
    if total_ranges == 0:
        return []

    try:
        if not _server_procs:
            raise RuntimeError("No syntax servers running")

        n_servers = len(_server_procs)

        # If there is exactly one range that covers the full buffer and multiple
        # servers exist, split it into multiple overlapping chunks so every
        # worker receives work (avoids the "single worker gets whole file" case).
        if n_servers > 1 and total_ranges == 1:
            try:
                full_s, full_e = ranges[0]
                content_len = len(content)
                if full_s == 0 and full_e == content_len and content_len >= 4096:
                    overlap = 256
                    chunk_size = max(4096, (content_len + n_servers - 1) // n_servers)
                    tmp = []
                    for i in range(n_servers):
                        s = i * chunk_size
                        e = min(content_len, (i + 1) * chunk_size)
                        s = max(0, s - overlap)
                        e = min(content_len, e + overlap)
                        tmp.append((s, e))
                    # coalesce adjacent/overlapping
                    new_ranges = []
                    for s, e in tmp:
                        if not new_ranges or s > new_ranges[-1][1]:
                            new_ranges.append((s, e))
                        else:
                            new_ranges[-1] = (new_ranges[-1][0], max(new_ranges[-1][1], e))
                    ranges = new_ranges
                    total_ranges = len(ranges)
            except Exception:
                # if anything goes wrong, keep original single range
                pass

        # If only one server available, preserve prior behavior (send all ranges to it)
        if n_servers <= 1:
            with _server_index_lock:
                idx = _next_server % max(1, n_servers)
                _next_server += 1
            stdin_like = _server_stdins[idx]
            stdout_like = _server_stdouts[idx]
            lock = _server_locks[idx]

            req = {
                "action": "map",
                "content": content,
                "ranges": ranges,
                "protected_spans": protected_spans,
                "keywords": keywords,
                "builtins": builtins
            }
            with lock:
                try:
                    stdin_like.write(json.dumps(req) + "\n")
                    stdin_like.flush()
                    line = stdout_like.readline()
                except Exception:
                    line = None
            if not line:
                # include stderr tail if available
                try:
                    tail = list(_server_stderr_buffers[idx])
                    if tail:
                        raise RuntimeError("No response from syntax_worker server; stderr tail:\n" + "\n".join(tail[-10:]))
                except Exception:
                    raise RuntimeError("No response from syntax_worker server")
            resp = json.loads(line)
            return resp.get("results", [])

        # Multiple servers: partition ranges round-robin across servers
        assignments: Dict[int, List[Tuple[int, Tuple[int, int]]]] = {i: [] for i in range(n_servers)}
        for orig_i, r in enumerate(ranges):
            sidx = orig_i % n_servers
            assignments[sidx].append((orig_i, r))

        # container for results; fill with None until set
        results_by_index: Dict[int, Dict[str, Any]] = {}
        results_lock = threading.Lock()

        def dispatch_to_server(server_idx: int, assigned: List[Tuple[int, Tuple[int, int]]]):
            """Send assigned ranges to one server and populate results_by_index."""
            if not assigned:
                return
            stdin_like = _server_stdins[server_idx]
            stdout_like = _server_stdouts[server_idx]
            lock = _server_locks[server_idx]
            # build ranges payload in the same order assigned
            ranges_payload = [r for (_i, r) in assigned]
            req = {
                "action": "map",
                "content": content,
                "ranges": ranges_payload,
                "protected_spans": protected_spans,
                "keywords": keywords,
                "builtins": builtins
            }
            try:
                with lock:
                    stdin_like.write(json.dumps(req) + "\n")
                    stdin_like.flush()
                    line = stdout_like.readline()
                if not line:
                    # record failures for these indices
                    with results_lock:
                        for orig_i, _ in assigned:
                            results_by_index[orig_i] = {}
                    return
                resp = json.loads(line)
                res_list = resp.get("results", [])
                # map returned results back to original indices
                with results_lock:
                    for (orig_i, _), rd in zip(assigned, res_list):
                        results_by_index[orig_i] = rd if isinstance(rd, dict) else {}
            except Exception:
                with results_lock:
                    for orig_i, _ in assigned:
                        results_by_index[orig_i] = {}

        # Launch dispatch threads (one per server with assigned ranges)
        threads: List[threading.Thread] = []
        for srv_idx, assigned in assignments.items():
            if not assigned:
                continue
            th = threading.Thread(target=dispatch_to_server, args=(srv_idx, assigned), daemon=True)
            threads.append(th)
            th.start()

        # Wait for all dispatches to finish with a conservative timeout (seconds)
        # Timeout chosen to avoid UI hangs; if threads still alive we fallback those ranges locally.
        timeout_seconds = max(3, min(10, total_ranges // 50 + 3))
        for th in threads:
            th.join(timeout_seconds)

        # For any indices not filled by workers, run local fallback per-range
        missing = [i for i in range(total_ranges) if i not in results_by_index]
        if missing:
            # try to load config-driven syntax before local processing
            _load_syntax_from_config()
            for i in missing:
                s, e = ranges[i]
                try:
                    rd = process_slice(content, int(s), int(e), protected_spans, keywords, builtins)
                except Exception:
                    rd = {}
                results_by_index[i] = rd

        # Build ordered results list
        ordered_results = [results_by_index[i] for i in range(total_ranges)]
        return ordered_results

    except Exception:
        # final fallback: sequential local processing
        out = []
        _load_syntax_from_config()
        for s, e in ranges:
            out.append(process_slice(content, s, e, protected_spans, keywords, builtins))
        return out

# ---- server main (invoked when running this file directly with --serve) -----
def _server_main():
    """
    Worker server: create a TCP listening socket on localhost, print ready JSON with port,
    accept a single parent connection and handle JSON-line requests on that socket.

    Verbose logging: write received packets and responses to both stderr and a local
    per-worker log file so the parent can inspect worker activity.
    """
    # Load syntax overrides at server start (best-effort)
    _load_syntax_from_config()

    # Prepare a local logfile for verbose logging (best-effort)
    lf = None
    try:
        try:
            base_logs = os.path.abspath(os.path.join(os.getcwd(), "worker_logs"))
            os.makedirs(base_logs, exist_ok=True)
        except Exception:
            base_logs = tempfile.gettempdir()
        log_path = os.path.join(base_logs, f"syntax_worker_{os.getpid()}.worker.log")
        try:
            lf = open(log_path, 'a', encoding='utf-8', errors='replace')
            header = f"=== worker log started at {datetime.datetime.utcnow().isoformat()}Z pid={os.getpid()} ===\n"
            try:
                lf.write(header)
                lf.flush()
            except Exception:
                pass
        except Exception:
            lf = None
    except Exception:
        lf = None

    # Create listening socket bound to localhost on an ephemeral port
    lsock = None
    conn = None
    fr = None
    fw = None
    try:
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lsock.bind(('127.0.0.1', 0))
        lsock.listen(1)
        port = lsock.getsockname()[1]

        # announce readiness with port so parent can connect
        try:
            ready_json = json.dumps({"ready": True, "port": port})
            sys.stdout.write(ready_json + "\n")
            sys.stdout.flush()
            # also log the ready message
            ts = datetime.datetime.utcnow().isoformat() + "Z "
            try:
                sys.stderr.write(ts + "READY: " + ready_json + "\n")
                sys.stderr.flush()
            except Exception:
                pass
            if lf:
                try:
                    lf.write(ts + "READY: " + ready_json + "\n")
                    lf.flush()
                except Exception:
                    pass
        except Exception:
            pass

        # accept a single parent connection (blocking)
        conn, _addr = lsock.accept()
        fr = conn.makefile('r', encoding='utf-8', newline='\n')
        fw = conn.makefile('w', encoding='utf-8', newline='\n')

        # now service JSON-line requests on the socket
        while True:
            line = fr.readline()
            if not line:
                break

            # Verbose log of received packet
            ts = datetime.datetime.utcnow().isoformat() + "Z "
            try:
                # normalize newline visibility
                log_line = line.rstrip('\n')
                try:
                    sys.stderr.write(ts + "RECV: " + log_line + "\n")
                    sys.stderr.flush()
                except Exception:
                    pass
                if lf:
                    try:
                        lf.write(ts + "RECV: " + log_line + "\n")
                        lf.flush()
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                req = json.loads(line)
            except Exception:
                # log malformed JSON and continue
                try:
                    msg = f"Malformed JSON: {line!r}"
                    sys.stderr.write(ts + "WARN: " + msg + "\n")
                    sys.stderr.flush()
                    if lf:
                        try:
                            lf.write(ts + "WARN: " + msg + "\n")
                            lf.flush()
                        except Exception:
                            pass
                except Exception:
                    pass
                continue

            action = req.get("action")
            if action == "shutdown":
                break
            if action == "map":
                content = req.get("content", "")
                ranges = req.get("ranges", [])
                protected_spans = req.get("protected_spans", []) or []
                keywords = req.get("keywords", []) or []
                builtins = req.get("builtins", []) or []

                if not keywords and KEYWORDS:
                    keywords = KEYWORDS
                if not builtins and BUILTINS:
                    builtins = BUILTINS

                results = []
                for s, e in ranges:
                    try:
                        rd = process_slice(content, int(s), int(e), protected_spans, keywords, builtins)
                    except Exception:
                        rd = {}
                    results.append(rd)
                out = {"results": results}
                outjson = json.dumps(out)

                # Verbose log of response
                try:
                    sys.stderr.write(ts + "SEND: " + outjson + "\n")
                    sys.stderr.flush()
                except Exception:
                    pass
                if lf:
                    try:
                        lf.write(ts + "SEND: " + outjson + "\n")
                        lf.flush()
                    except Exception:
                        pass

                try:
                    fw.write(outjson + "\n")
                    fw.flush()
                except Exception:
                    # if socket write fails, break and let parent fallback
                    break
            else:
                # ignore unknown actions but log them
                try:
                    sys.stderr.write(ts + "IGNORED_ACTION: " + repr(action) + "\n")
                    sys.stderr.flush()
                    if lf:
                        try:
                            lf.write(ts + "IGNORED_ACTION: " + repr(action) + "\n")
                            lf.flush()
                        except Exception:
                            pass
                except Exception:
                    pass
                continue
    except Exception:
        # best-effort silence: worker should not crash the parent if it fails
        try:
            ts = datetime.datetime.utcnow().isoformat() + "Z "
            sys.stderr.write(ts + "WORKER_EXCEPTION\n")
            sys.stderr.flush()
            if lf:
                try:
                    lf.write(ts + "WORKER_EXCEPTION\n")
                    lf.flush()
                except Exception:
                    pass
        except Exception:
            pass
    finally:
        try:
            if fr:
                fr.close()
        except Exception:
            pass
        try:
            if fw:
                fw.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        try:
            if lsock:
                lsock.close()
        except Exception:
            pass
        try:
            if lf:
                lf.close()
        except Exception:
            pass

if __name__ == '__main__':
    # when run as a standalone server process
    if '--serve' in sys.argv:
        _server_main()
    else:
        # nothing to do when executed directly without --serve
        pass