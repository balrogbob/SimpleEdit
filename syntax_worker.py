import re
import sys
import os
import json
import subprocess
import threading
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

# ---- subprocess server support ---------------------------------------------
# The server mode runs when syntax_worker.py is executed as a script with --serve.
# The parent process can call map_slices(...) which will launch a persistent
# subprocess (same file, --serve) and send a single JSON request containing:
#   { "action": "map", "content": "<full_content>", "ranges":[[s,e],...], "protected_spans":[...], "keywords": [...], "builtins":[...] }
# The server returns JSON: { "results": [ rd_for_slice0, rd_for_slice1, ... ] }
#
# This design avoids importing the application's main module inside worker processes
# (which would otherwise cause Tk GUI side-effects when the spawn start method is used).

_server_proc = None
_server_lock = threading.Lock()
_server_stdin = None
_server_stdout = None

def _ensure_server() -> None:
    global _server_proc, _server_stdin, _server_stdout
    with _server_lock:
        if _server_proc and _server_proc.poll() is None:
            return
        # Launch a new Python interpreter running this file in server mode
        cmd = [sys.executable, os.path.abspath(__file__), '--serve']
        # use text mode for convenient JSON line protocol, unbuffered output
        _server_proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        _server_stdin = _server_proc.stdin
        _server_stdout = _server_proc.stdout

def _stop_server():
    global _server_proc, _server_stdin, _server_stdout
    with _server_lock:
        try:
            if _server_proc and _server_proc.poll() is None:
                try:
                    _server_stdin.write(json.dumps({"action":"shutdown"}) + "\n")
                    _server_stdin.flush()
                except Exception:
                    pass
                try:
                    _server_proc.wait(timeout=1)
                except Exception:
                    _server_proc.kill()
        finally:
            _server_proc = None
            _server_stdin = None
            _server_stdout = None

def map_slices(content: str, ranges: List[Tuple[int, int]],
               protected_spans: List[Tuple[int, int]], keywords: List[str],
               builtins: List[str], processes: int = 1) -> List[Dict[str, Any]]:
    """
    Ask the external server process to process the given slices.
    Returns list of result dictionaries matching process_slice outputs (one item per range).
    Falls back to local sequential calls on failure.
    """
    try:
        _ensure_server()
        req = {
            "action": "map",
            "content": content,
            "ranges": ranges,
            "protected_spans": protected_spans,
            "keywords": keywords,
            "builtins": builtins
        }
        with _server_lock:
            _server_stdin.write(json.dumps(req) + "\n")
            _server_stdin.flush()
            # read a single JSON line response
            line = _server_stdout.readline()
        if not line:
            raise RuntimeError("No response from syntax_worker server")
        resp = json.loads(line)
        return resp.get("results", [])
    except Exception:
        # fallback: run locally sequentially (still uses fast compiled regexes)
        out = []
        # Attempt to load config-driven overrides locally as well so fallback respects current config if possible
        _load_syntax_from_config()
        for s, e in ranges:
            out.append(process_slice(content, s, e, protected_spans, keywords, builtins))
        return out

# ---- server main (invoked when running this file directly with --serve) -----
def _server_main():
    """
    Read JSON line requests on stdin, write JSON line responses to stdout.
    Supports action 'map' and 'shutdown'.

    On startup, attempt to load syntax overrides from the application's config so
    the worker uses the same syntax rules that were active when the main app
    spawned the worker.
    """
    # Load syntax overrides at server start (best-effort)
    _load_syntax_from_config()

    try:
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            try:
                req = json.loads(line)
            except Exception:
                # ignore malformed lines
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

                # If caller did not pass keywords/builtins, prefer config-provided ones
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
                sys.stdout.write(json.dumps(out) + "\n")
                sys.stdout.flush()
            else:
                # unknown action -> ignore
                continue
    except Exception:
        pass

if __name__ == '__main__':
    # when run as a standalone server process
    if '--serve' in sys.argv:
        _server_main()
    else:
        # nothing to do when executed directly without --serve
        pass