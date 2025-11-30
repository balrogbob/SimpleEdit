#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Small, dependency-free helper module to manage a persistent recent-files MRU list.

Usage (example):
    import configparser
    cfg = configparser.ConfigParser()
    cfg.read(ini_path)
    from PythonApplication1 import recent_files as rf
    rf.add_recent_file(cfg, ini_path, "/path/to/file", on_update=my_refresh_cb)

The module is GUI-agnostic and uses a simple JSON encoded list stored in the
ConfigParser under section "Recent", key "files".
"""
from __future__ import annotations
import os
import sys
import threading
import re
import configparser
import random
import time
import html
from html.parser import HTMLParser
import json
import base64
from io import StringIO
from threading import Thread
from tkinter import *
from tkinter import filedialog, messagebox, colorchooser, simpledialog
from tkinter import ttk
from typing import Callable, Iterable, List, Optional
import urllib.request as _urr
import urllib.parse as _up
import shutil, sys, os
import traceback as _traceback
import re as _re

def _format_js_error_context(script_src: str, exc: Exception, tb: str | None = None, context_lines: int = 2) -> str:
    """
    Best-effort: return a small snippet (with line numbers) from `script_src`
    that most likely relates to `exc` / `tb`. Uses:
      - numeric "line N" hints in traceback/message when available
      - quoted tokens from the exception message (searches script for token)
      - first non-empty line as fallback
    """
    try:
        tb_text = tb if tb is not None else (_traceback.format_exc() or "")
    except Exception:
        tb_text = ""

    # 1) try to find an explicit line number in traceback/text ("line 12", "Line:12", ":12")
    try:
        m = _re.search(r'line\s+(\d+)', tb_text, flags=_re.I)
        if not m:
            m = _re.search(r'[:@](\d{1,6})(?:\b|:)', tb_text)
        if m:
            ln = int(m.group(1))
        else:
            ln = None
    except Exception:
        ln = None

    lines = (script_src or "").splitlines()

    # If we have a plausible line number, return a small surrounding context.
    if ln and 1 <= ln <= len(lines):
        start = max(0, ln - 1 - context_lines)
        end = min(len(lines), ln - 1 + context_lines + 1)
        out = []
        for i in range(start, end):
            prefix = f"{i+1:>4}: " if (i == ln - 1) else "     "
            out.append(f"{prefix}{lines[i]}")
        return "\n".join(out)

    # 2) try to extract a quoted token from the exception message and locate it in the script
    try:
        msg = str(exc) or tb_text or ""
        qm = _re.search(r'["\']([^"\']{2,160})["\']', msg)
        if qm:
            token = qm.group(1)
            for idx, ln_text in enumerate(lines):
                if token in ln_text:
                    start = max(0, idx - context_lines)
                    end = min(len(lines), idx + context_lines + 1)
                    out = []
                    for j in range(start, end):
                        prefix = f"{j+1:>4}: " if (j == idx) else "     "
                        out.append(f"{prefix}{lines[j]}")
                    return "\n".join(out)
    except Exception:
        pass

    # 3) fallback: first non-empty line, or head truncated
    try:
        for idx, ln_text in enumerate(lines):
            if ln_text.strip():
                return f"{idx+1:>4}: {ln_text}"
    except Exception:
        pass

    return (script_src or "")[:400]

RECENT_MAX = 10

IN_CELL_NL = '\u2028'  # internal cell-newline marker (stored inside table cells so real \n doesn't break rows)
_SCRIPT_RE = re.compile(r'(?is)<script\b([^>]*)>(.*?)</script\s*>')

_DEFAULT_TAG_COLORS = {
    "number": {"fg": "#FDFD6A", "bg": ""},
    "selfs": {"fg": "yellow", "bg": ""},
    "variable": {"fg": "#8A2BE2", "bg": ""},
    "decorator": {"fg": "#66CDAA", "bg": ""},
    "class_name": {"fg": "#FFB86B", "bg": ""},
    "constant": {"fg": "#FF79C6", "bg": ""},
    "attribute": {"fg": "#33ccff", "bg": ""},
    "builtin": {"fg": "#9CDCFE", "bg": ""},
    "def": {"fg": "orange", "bg": ""},
    "keyword": {"fg": "red", "bg": ""},
    "string": {"fg": "#C9CA6B", "bg": ""},
    "operator": {"fg": "#AAAAAA", "bg": ""},
    "comment": {"fg": "#75715E", "bg": ""},
    "todo": {"fg": "#ffffff", "bg": "#B22222"},
    "currentLine": {"fg": "", "bg": "#222222"},
    "trailingWhitespace": {"fg": "", "bg": "#331111"},
    "find_match": {"fg": "white", "bg": "#444444"},
    "marquee": {"fg": "#FF4500", "bg": ""},
    "mark": {"fg": "", "bg": "#FFF177"},
    "code": {"fg": "#000000", "bg": "#F5F5F5"},
    "kbd": {"fg": "#000000", "bg": "#F5F5F5"},
    "sub": {"fg": "", "bg": ""},
    "sup": {"fg": "", "bg": ""},
    "small": {"fg": "", "bg": ""},
    # HTML element/attribute colors
    "html_tag": {"fg": "#569CD6", "bg": ""},            # element names
    "html_attr": {"fg": "#9CDCFE", "bg": ""},           # attribute names
    "html_attr_value": {"fg": "#CE9178", "bg": ""},     # attribute values (strings)
    "html_comment": {"fg": "#6A9955", "bg": ""}         # HTML comments
}

# Update DEFAULT_CONFIG to include JS console preference (persisted)
DEFAULT_CONFIG = {
    'Section1': {
        'fontName': 'consolas',
        'fontSize': '12',
        'fontColor': '#4AF626',
        'backgroundColor': 'black',
        'cursorColor': 'white',
        'undoSetting': 'True',
        'aiMaxContext': '512',
        'temperature': '1.1',
        'top_k': '300',
        'seed': '1337',
        'syntaxHighlighting': 'True',
        'loadAIOnOpen': 'False',
        'loadAIOnNew': 'False',
        'saveFormattingInFile': 'False',   # new: persist whether to embed formatting header
        'exportCssMode': 'inline-element', # 'inline-element' | 'inline-block' | 'external'
        'exportCssPath': '',               # used when 'external' chosen; default generated at save time
        'jsConsoleOnRun': 'False'          # new: when True open JS Console popup by default for run_scripts
    }
}
exportCssMode = 'inline-element'  # default
exportCssPath = ''

INI_PATH = 'config.ini'
config = configparser.ConfigParser()
if not os.path.isfile(INI_PATH):
    config.read_dict(DEFAULT_CONFIG)
    with open(INI_PATH, 'w') as f:
        config.write(f)
else:
    config.read(INI_PATH)

# -------------------------
# Config values (typed)
# -------------------------
fontName = config.get('Section1', 'fontName')
fontSize = int(config.get('Section1', 'fontSize'))
fontColor = config.get('Section1', 'fontColor')
backgroundColor = config.get('Section1', 'backgroundColor')
undoSetting = config.getboolean('Section1', 'undoSetting')
cursorColor = config.get('Section1', 'cursorColor')
aiMaxContext = int(config.get('Section1', 'aiMaxContext'))
temperature = float(config.get('Section1', 'temperature'))
top_k = int(config.get('Section1', 'top_k'))
seed = int(config.get('Section1', 'seed'))

def ensure_recent_section(config) -> None:
    """Ensure the 'Recent' section exists in the given ConfigParser."""
    if not config.has_section("Recent"):
        config.add_section("Recent")


def load_recent_files(config) -> List[str]:
    """Return list of recent absolute file paths (may be empty)."""
    ensure_recent_section(config)
    try:
        raw = config.get("Recent", "files", fallback="[]")
        return json.loads(raw)
    except Exception:
        return []


def save_recent_files(config, ini_path: str, lst: Iterable[str]) -> None:
    """Persist list (iterable) into config under Recent/files as JSON string."""
    ensure_recent_section(config)
    try:
        config.set("Recent", "files", json.dumps(list(lst)))
        with open(ini_path, "w", encoding="utf-8") as fh:
            config.write(fh)
    except Exception:
        # Best-effort: don't crash caller for IO/config errors
        pass

# New helpers to get/set the persisted JS console preference
def get_js_console_default() -> bool:
    """Return whether JS Console should open by default when running scripts."""
    try:
        return config.getboolean("Section1", "jsConsoleOnRun", fallback=False)
    except Exception:
        return False

def set_js_console_default(value: bool) -> None:
    """Persist the JS Console default preference into config.ini (Section1/jsConsoleOnRun)."""
    try:
        config.set("Section1", "jsConsoleOnRun", str(bool(value)))
        with open(INI_PATH, "w", encoding="utf-8") as fh:
            config.write(fh)
    except Exception:
        # best-effort: do not raise to caller
        pass

def _strip_leading_license_comment(src: str) -> str:
    """Remove a leading /*! ... */ license header (common in minified libs) to avoid jsmini parse issues.
    Keeps everything else intact. Safe no-op when nothing matches.
    """
    try:
        if not src:
            return src
        # remove a single leading /*! ... */ (and surrounding whitespace) if present
        return re.sub(r'^\s*/\*![\s\S]*?\*/\s*', '', src, count=1)
    except Exception:
        return src

def add_recent_file(
    config,
    ini_path: str,
    path: str,
    on_update: Optional[Callable[[], None]] = None,
    max_items: Optional[int] = None,
) -> None:
    """
    Add given path to the MRU, pushing it to front and truncating to max_items.
    If on_update is given it will be called after save (safely).
    """
    try:
        path = os.path.abspath(path)
        lst = load_recent_files(config)
        if path in lst:
            lst.remove(path)
        lst.insert(0, path)
        limit = max_items if max_items is not None else RECENT_MAX
        lst = lst[:limit]
        save_recent_files(config, ini_path, lst)
        if on_update:
            try:
                on_update()
            except Exception:
                pass
    except Exception:
        pass


_js_console_window = None
_js_console_text = None
_js_console_lock = None

def _init_js_console_lock():
    global _js_console_lock
    import threading as _thr
    if _js_console_lock is None:
        _js_console_lock = _thr.Lock()

def _ensure_js_console():
    """Create or reuse a single JS Console Toplevel and text widget (main-thread-safe calls via .after)."""
    global _js_console_window, _js_console_text
    _init_js_console_lock()
    try:
        # If already exists and is alive, return it
        try:
            if _js_console_window and str(_js_console_window.winfo_exists()) == '1':
                return _js_console_window, _js_console_text
        except Exception:
            pass

        # Create console UI on main thread synchronously if possible
        try:
            dlg = Toplevel()
            dlg.title("JS Console")
            dlg.geometry("800x320")
            frm = Frame(dlg)
            frm.pack(fill=BOTH, expand=True)
            txt = Text(frm, wrap='none', state='normal')
            txt.pack(side=LEFT, fill=BOTH, expand=True)
            vs = Scrollbar(frm, orient=VERTICAL, command=txt.yview)
            vs.pack(side=RIGHT, fill=Y)
            txt.config(yscrollcommand=vs.set)
            btn_frame = Frame(dlg)
            btn_frame.pack(fill=X)
            def _clear():
                try:
                    txt.delete('1.0', 'end')
                except Exception:
                    pass
            def _close():
                try:
                    dlg.destroy()
                except Exception:
                    pass
            Button(btn_frame, text="Clear", command=_clear).pack(side=LEFT, padx=6, pady=4)
            Button(btn_frame, text="Close", command=_close).pack(side=RIGHT, padx=6, pady=4)
            _js_console_window = dlg
            _js_console_text = txt
            try:
                dlg.lift()
                dlg.attributes('-topmost', True)
                dlg.after(100, lambda: dlg.attributes('-topmost', False))
            except Exception:
                pass
            return _js_console_window, _js_console_text
        except Exception:
            # Fallback: don't raise UI errors - console not available
            _js_console_window = None
            _js_console_text = None
            return None, None
    except Exception:
        return None, None

def _console_append(msg: str):
    """Append line to the shared JS console (thread-safe via .after)."""
    try:
        _init_js_console_lock()
        # ensure console exists (create on main thread if necessary)
        try:
            dlg, txt = _js_console_window, _js_console_text
            if not dlg or not txt or str(dlg.winfo_exists()) != '1':
                dlg, txt = _ensure_js_console()
        except Exception:
            dlg, txt = _ensure_js_console()
        if txt and dlg:
            try:
                # schedule insertion on UI thread
                txt.after(0, lambda m=msg, t=txt, d=dlg: (t.insert('end', m + '\n'), t.see('end'), d.update_idletasks()))
            except Exception:
                try:
                    txt.insert('end', msg + '\n')
                    txt.see('end')
                except Exception:
                    print(msg)
        else:
            # fallback to stdout
            print(msg)
    except Exception:
        try:
            print(msg)
        except Exception:
            pass

def _bring_console_to_front():
    """Bring the console to front briefly and allow UI to refresh."""
    try:
        dlg = _js_console_window
        if not dlg or str(dlg.winfo_exists()) != '1':
            return
        try:
            dlg.lift()
            dlg.focus_force()
            dlg.attributes('-topmost', True)
            dlg.after(150, lambda: dlg.attributes('-topmost', False))
            dlg.update_idletasks()
        except Exception:
            pass
    except Exception:
        pass

def clear_recent_files(config, ini_path: str, on_update: Optional[Callable[[], None]] = None) -> None:
    """Clear persisted recent list and optionally call on_update."""
    save_recent_files(config, ini_path, [])
    if on_update:
        try:
            on_update()
        except Exception:
            pass

# --- HTML parser to extract plain text and tag ranges from simple HTML fragments ---
class _SimpleHTMLToTagged(HTMLParser):
    """Parses a fragment of HTML and returns plain text plus tag ranges and explicit link entries.

    get_result() -> (plain_text, meta)
    meta is a dict: {'tags': {tag: [[s,e],...]}, 'links': [{'start':int,'end':int,'href':str,'title':str?}, ...]}
    """
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.pos = 0
        # Table / cell metadata collectors to preserve attributes and structure
        # Entries are populated during parsing and emitted via get_result() as meta['tables'].
        # Each table meta: {'start': int, 'end': int, 'attrs': dict, 'rows': [ [ { 'start':int,'end':int,'text':str,'attrs':dict,'type':'td'|'th' } ] ], 'colgroup': [...] }
        self._table_meta: list[dict] = []
        # Temporary stack for nested table attributes (parallel to stack entries)
        self._table_attr_stack: list[dict] = []
        # Capture cell-level attributes while inside table (populated on td/th start and end)
        self._cell_meta: list[dict] = []
        # Per-table and per-row builders used while parsing so the final table meta
        # mirrors the table-editor output (rows -> cells with attrs).
        # Stack of lists: each open <table> pushes a list of rows; each open <tr> pushes a current-row buffer.
        self._current_table_rows: list[list] = []
        self._current_row_cells: list[list] = []
         # stack entries: ('tag', start) or ('hyperlink', start, href, title)
        self.stack = []
        # stack to track nested ordered-list counters (one counter per open <ol>)
        self._ol_counters = []
        self.ranges = {}  # tag -> [[start,end], ...]
        self.hrefs = []   # list of {'start':int,'end':int,'href':str,'title':str}
        self._script_suppress_depth = 0  # nested <script> suppression counter
        self._style_suppress_depth = 0   # nested <style> suppression counter
        self._recent_br = 0  # count of immediately preceding <br>-generated newlines
        self._pending_li_leading = 0  # when >0, suppress leading newlines right after <li> to keep bullet inline
       # For block elements like <p>/<div>, suppress initial template-indent newlines after the opening tag.
        self._pending_block_leading: str | None = None  # 'p' | 'div' | None
        # code block capture: push ('__code__', start_pos, list_of_fragments)
        # We treat both <code> and <pre> as code blocks (best-effort).

   # --- Soft layout helpers (safe; do not interfere with code/pre capture) ---
    def _collapse_leading_blank_region(self, text: str) -> tuple[str, int]:
        """
        Collapse all leading whitespace into at most ONE newline.
        Returns (new_text, removed_char_count).
        This only touches the very beginning of the document to avoid breaking
        code block indent or any ranges elsewhere.
        """
        try:
            if not text:
                return text, 0
            m = re.search(r'\S', text)
            if not m:
                # all whitespace => keep a single newline if any existed
                had_nl = '\n' in text
                return ('\n' if had_nl else ''), (len(text) - (1 if had_nl else 0))
            i = m.start()
            if i == 0:
                return text, 0
            head = text[:i]
            keep_prefix = '\n' if '\n' in head else ''
            return keep_prefix + text[i:], (i - len(keep_prefix))
        except Exception:
            return text, 0

    def _shift_all_ranges_and_links(self, delta: int) -> None:
        """Shift every recorded range and link start/end by delta (can be negative)."""
        try:
            if delta == 0:
                return
            for k, spans in list(self.ranges.items()):
                new_spans = []
                for s, e in spans:
                    ns, ne = s + delta, e + delta
                    if ne > ns and ne > 0:
                        new_spans.append([max(0, ns), max(0, ne)])
                self.ranges[k] = new_spans
            if self.hrefs:
                for rec in self.hrefs:
                    if isinstance(rec, dict):
                        rec['start'] = max(0, int(rec.get('start', 0)) + delta)
                        rec['end'] = max(0, int(rec.get('end', 0)) + delta)
        except Exception:
            pass
    # --- Added helpers for block element spacing (<p>, <div>) ---
    def _current_tail_newline_count(self) -> int:
        """Return how many consecutive newlines appear at end of current output."""
        try:
            if not self.out:
                return 0
            s = ''.join(self.out)
            cnt = 0
            for ch in reversed(s):
                if ch == '\n':
                    cnt += 1
                else:
                    break
            return cnt
        except Exception:
            return 0

    def _ensure_leading_block_spacing(self, require_blank: bool):
        """
        Ensure appropriate separation before a new block element.
        require_blank=True -> want at least one blank line (>=2 trailing newlines).
        """
        try:
            if self.pos == 0:
                return
            tail_nl = self._current_tail_newline_count()
            if require_blank:
                if tail_nl >= 2:
                    return
                if tail_nl == 0:
                    self.out.append('\n\n')
                    self.pos += 2
                elif tail_nl == 1:
                    self.out.append('\n')
                    self.pos += 1
            else:
                if tail_nl == 0:
                    self.out.append('\n')
                    self.pos += 1
        except Exception:
            pass

    def _ensure_trailing_block_spacing(self, require_blank: bool):
        """
        Ensure trailing spacing after closing a block. For paragraphs we keep at least one blank line.
        """
        try:
            tail_nl = self._current_tail_newline_count()
            if require_blank:
                if tail_nl < 2:
                    self.out.append('\n' if tail_nl == 1 else '\n\n')
                    self.pos += 1 if tail_nl == 1 else 2
            else:
                if tail_nl == 0:
                    self.out.append('\n')
                    self.pos += 1
        except Exception:
            pass
    # --- Extra helpers to fine-tune block spacing (used for headings/.nav/.content) ---
    def _ensure_leading_newlines(self, required: int):
        """Ensure at least `required` trailing newlines exist before starting a block."""
        try:
            if self.pos == 0 or required <= 0:
                return
            tail = self._current_tail_newline_count()
            add = max(0, required - tail)
            if add:
                self.out.append('\n' * add)
                self.pos += add
        except Exception:
            pass

    def _ensure_trailing_newlines(self, required: int):
        """Ensure at least `required` trailing newlines exist after closing a block."""
        try:
            if required <= 0:
                return
            tail = self._current_tail_newline_count()
            add = max(0, required - tail)
            if add:
                self.out.append('\n' * add); self.pos += add
        except Exception:
            pass

    def _normalize_color_to_hex(self, col: str) -> str | None:
        if not col:
            return None
        c = col.strip().lower()
        c = re.sub(r"^['\"]|['\"]$", "", c)
        NAMED = {'red': '#ff0000', 'black': '#000000', 'white': '#ffffff', 'blue': '#0000ff', 'green': '#008000', 'yellow': '#ffff00', 'orange': '#ffa500'}
        if c in NAMED:
            c = NAMED[c]
        m = re.match(r'^#([0-9a-f]{3})$', c)
        if m:
            s = m.group(1)
            c = '#' + ''.join([ch*2 for ch in s])
        if re.match(r'^#[0-9a-f]{6}$', c):
            return c
        return None
    # Helpers to manage literal capture inside <code>/<pre>
    def _in_code_capture(self) -> bool:
        try:
            return bool(self.stack and isinstance(self.stack[-1], (tuple, list)) and self.stack[-1][0] == '__code__')
        except Exception:
            return False
    def _code_top(self):
        try:
            return self.stack[-1] if self._in_code_capture() else None
        except Exception:
            return None
    def _code_append(self, s: str):
        try:
            top = self._code_top()
            if top is None:
                return
            if len(top) >= 3 and isinstance(top[2], list):
                top[2].append(s)
        except Exception:
            pass
    def _reconstruct_start_tag(self, tag: str, attrs) -> str:
        try:
            parts = ['<', tag]
            for k, v in (attrs or []):
                if v is None:
                    parts.append(f' {k}')
                else:
                    val = str(v).replace('&', '&amp;').replace('"', '&quot;')
                    parts.append(f' {k}="{val}"')
            parts.append('>')
            return ''.join(parts)
        except Exception:
            return f"<{tag}>"
    def _reconstruct_end_tag(self, tag: str) -> str:
        return f"</{tag}>"
    def _reconstruct_startend_tag(self, tag: str, attrs) -> str:
        try:
            parts = ['<', tag]
            for k, v in (attrs or []):
                if v is None:
                    parts.append(f' {k}')
                else:
                    val = str(v).replace('&', '&amp;').replace('"', '&quot;')
                    parts.append(f' {k}="{val}"')
            parts.append(' />')
            return ''.join(parts)
        except Exception:
            return f"<{tag} />"

    # ---- Added: language extraction helpers & fenced splitter ---- 
    def _lang_from_attrs(self, attrs) -> str | None:
        try:
            attrd = dict(attrs or {})
            vals = []
            cls = attrd.get('class') or ''
            for part in re.split(r'[\s,]+', cls.lower()):
                if part.startswith('language-'):
                    vals.append(part.split('-', 1)[1])
                elif part.startswith('lang-'):
                    vals.append(part.split('-', 1)[1])
                elif part in ('python','json','html','markdown','md','javascript','js','c','cpp','c++','yaml','yml','rathena','npc','rathena-npc','rathena_yaml','rathena-yaml'):
                    vals.append(part)
            for k in ('data-lang','lang','type'):
                v = (attrd.get(k) or '').lower()
                if v:
                    if k == 'type':
                        m = re.search(r'(python|json|html|markdown|javascript|js|c\+\+|cpp|c|yaml|yml|rathena(?:-yaml|-npc)?)', v)
                        if m:
                            vals.append(m.group(1))
                    else:
                        vals.append(v)
            if not vals:
                return None
            for v in vals:
                if v == 'md': return 'markdown'
                if v in ('js','javascript'): return 'javascript'
                if v in ('c++','cpp'): return 'cpp'
                if v in ('yml','yaml'): return 'yaml'
                if v in ('rathena-yaml','rathena_yaml','rathenayaml','rathena yaml','rathena_yaml'): return 'rathena_yaml'
                if v in ('rathena','npc','rathena-npc','rathena_npc','rathenanpc','rathena npc'): return 'rathena_npc'
                return v
            return None
        except Exception:
            return None

    def _split_fenced_segments(self, raw_code: str):
        """
        Split code into segments by ```lang or '''lang fences.
        Returns list of {'lang': <str|None>, 'text': <str>}
        """
        segments = []
        pos = 0
        L = len(raw_code)
        fence_open = re.compile(r'^(?:```|\'\'\')\s*([A-Za-z0-9_+\-]+)?\s*$', re.MULTILINE)
        while pos < L:
            m = fence_open.search(raw_code, pos)
            if not m:
                segments.append({'lang': None, 'text': raw_code[pos:]})
                break
            start_line = m.start()
            if start_line > pos:
                segments.append({'lang': None, 'text': raw_code[pos:start_line]})
            lang_token = (m.group(1) or '').lower() if m.group(1) else None
            if lang_token == 'md': lang_token = 'markdown'
            if lang_token in ('js','javascript'): lang_token = 'javascript'
            if lang_token in ('c++','cpp'): lang_token = 'cpp'
            if lang_token in ('yml','yaml'): lang_token = 'yaml'
            if lang_token in ('rathena-yaml','rathena_yaml','rathenayaml','rathenayaml'): lang_token = 'rathena_yaml'
            if lang_token in ('rathena','npc','rathena-npc','rathena_npc','rathenanpc'): lang_token = 'rathena_npc'

            fence_seq = raw_code[m.start():m.end()]
            fence_kind = '```' if fence_seq.startswith('```') else "'''"
            close_re = re.compile(rf'^{re.escape(fence_kind)}\s*$', re.MULTILINE)
            search_from = m.end()
            m_close = close_re.search(raw_code, search_from)
            if not m_close:
                segments.append({'lang': lang_token, 'text': raw_code[m.start():]})
                break
            inner = raw_code[search_from:m_close.start()]
            segments.append({'lang': lang_token, 'text': inner})
            pos = m_close.end()
        return segments
    def handle_starttag(self, tag, attrs):
        try:
            tag = (tag or '').lower()

            # If already inside a code/pre capture, adjust behavior
            if self._in_code_capture():
                if tag in ('code', 'pre'):
                    try:
                        if isinstance(self.stack[-1], tuple):
                            self.stack[-1] = list(self.stack[-1]) + [0]
                        if len(self.stack[-1]) < 4:
                            self.stack[-1].append(0)
                        self.stack[-1][3] = int(self.stack[-1][3]) + 1
                    except Exception:
                        pass
                    return
                self._code_append(self._reconstruct_start_tag(tag, attrs))
                return

            # Special-case finalize table cells / rows / tables so we build detailed metadata
            # that matches the table-editor output (rows of cells with attrs + colgroup).

            # Suppress any <script ...> or <style ...> (regardless of attributes)
            if tag in ('script', 'style'):
                # Trim trailing whitespace before script to avoid tall gaps
                # (lightweight: remove only pure whitespace segments at tail)
                while self.out and self.out[-1] and self.out[-1].strip() == '':
                    self.pos -= len(self.out[-1])
                    self.out.pop()
                if tag == 'script':
                    self._script_suppress_depth += 1
                else:
                    self._style_suppress_depth += 1
                return
            # Enter code/pre capture (outermost) — do not emit literal tags
            if tag in ('code', 'pre'):
                 # Added language hint capture
                lang_hint = self._lang_from_attrs(attrs)
                self.stack.append(['__code__', self.pos, [], 0, lang_hint])
                return

            attrd = dict(attrs or {})
            cls = (attrd.get('class') or '').strip().lower()
            # Headings and blockquote (block-level)
            if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
                # Give H1/H2 a blank line before, others at least one newline
                self._ensure_leading_newlines(2 if tag in ('h1', 'h2') else 1)
                self.stack.append((tag, self.pos))
                return
            if tag == 'blockquote':
                self._ensure_leading_newlines(1)
                self.stack.append(('blockquote', self.pos))
                return
            # Block elements: improved handling for <p> and <div>
            if tag == 'p':
                self._ensure_leading_block_spacing(require_blank=True)
                self.stack.append(('p', self.pos))
               # Next whitespace chunk is likely template indentation/newlines; suppress it.
                self._pending_block_leading = 'p'
                return
            if tag == 'div':
                # Class-aware spacing
                if 'nav' in cls.split():
                    self._ensure_leading_newlines(2)
                    self.stack.append(('div_nav', self.pos))
                elif 'content' in cls.split():
                    self._ensure_leading_newlines(1)
                    self.stack.append(('div_content', self.pos))
                else:
                    self._ensure_leading_block_spacing(require_blank=False)
                    self.stack.append(('div', self.pos))
               # Suppress initial newline/indent after open <div> to avoid empty line before first text.
                self._pending_block_leading = 'div'
                return

            # Basic table/list handling
            if tag in ('table', 'tr', 'td', 'th', 'ul', 'ol', 'li'):
                if tag == 'tr':
                    if self.pos > 0:
                        self.out.append('\n'); self.pos += 1
                    # start a new in-memory row buffer so subsequent td/th closures can append cell metas
                    try:
                        self._current_row_cells.append([])
                    except Exception:
                        pass
                elif tag in ('td', 'th'):
                    prev_text = ''.join(self.out) if self.out else ''
                    if prev_text and not prev_text.endswith('\n'):
                        self.out.append('\t'); self.pos += 1
                    # record cell start and attrs so we can preserve rowspan/colspan/align on export
                    attrd = dict(attrs or {})
                    try:
                        # create a cell meta entry; end/text will be finalized on the matching endtag
                       cm = {'start': self.pos, 'end': None, 'attrs': attrd, 'type': tag}
                       self._cell_meta.append(cm)
                       # also leave a placeholder in the current row buffer if available
                       try:
                           if self._current_row_cells:
                               self._current_row_cells[-1].append(cm)
                       except Exception:
                           pass
                    except Exception:
                        pass
                elif tag == 'li':
                    if self.pos > 0 and not ''.join(self.out).endswith('\n'):
                        self.out.append('\n'); self.pos += 1
                    if self._ol_counters:
                        n = self._ol_counters[-1]; s_n = f"{n}. "
                        self.out.append(s_n); self.pos += len(s_n)
                        self._ol_counters[-1] = n + 1
                    else:
                        self.out.append('\u2022 '); self.pos += 2
                    self._pending_li_leading += 1  # next whitespace chunk should not insert a newline
                if tag == 'ol':
                    self._ol_counters.append(1)
                # record table start attrs for later reconstruction and push a new rows accumulator
                if tag == 'table':
                    try:
                        self._table_attr_stack.append(dict(attrd))
                    except Exception:
                        self._table_attr_stack.append({})
                    # start a per-table rows accumulator so <tr> can append into it
                    try:
                        self._current_table_rows.append([])
                    except Exception:
                        pass                        
                    self._table_attr_stack.append({})
                self.stack.append((tag, self.pos))
                return

            if tag in ('b', 'strong'):
                self.stack.append(('bold', self.pos)); return
            if tag == 'small':
                self.stack.append(('small', self.pos)); return
            if tag in ('i', 'em'):
                self.stack.append(('italic', self.pos)); return
            if tag == 'u':
                self.stack.append(('underline', self.pos)); return
            if tag == 'mark':
                self.stack.append(('mark', self.pos)); return
            if tag == 'kbd':
                self.stack.append(('kbd', self.pos)); return
            if tag == 'font':
                color = (attrd.get('color') or attrd.get('colour') or '').strip()
                hexcol = self._normalize_color_to_hex(color)
                if hexcol:
                    self.stack.append((f"font_{hexcol.lstrip('#')}", self.pos)); return
                self.stack.append((None, self.pos)); return

            if tag == 'marquee':
                self.stack.append(('marquee', self.pos)); return

            if tag == 'a':
                href = (attrd.get('href') or '').strip()
                title = (attrd.get('title') or '').strip() or None
                if href:
                    self.stack.append(('hyperlink', self.pos, href, title))
                else:
                    self.stack.append((None, self.pos))
                return

            if tag == 'span':
                # Respect class="todo" explicitly (even if no inline style)
                if 'todo' in cls.split():
                    self.stack.append(('todo', self.pos)); return
                style = (attrd.get('style') or '') or attrd.get('class', '')
                if style:
                    m = re.search(r'color\s*:\s*(#[0-9A-Fa-f]{3,6}|[A-Za-z]+)', style)
                    if m:
                        hexcol = self._normalize_color_to_hex(m.group(1))
                        if hexcol:
                            self.stack.append((f"font_{hexcol.lstrip('#')}", self.pos)); return
                    m2 = re.search(r'background(?:-color)?\s*:\s*(#[0-9A-Fa-f]{3,6}|[A-Za-z]+)', style)
                    if m2:
                        bg = m2.group(1).lower()
                        if bg in ('#b22222', 'b22222', 'red'):
                            self.stack.append(('todo', self.pos)); return
                self.stack.append((None, self.pos)); return

            self.stack.append((None, self.pos))
        except Exception:
            try:
                self.stack.append((None, self.pos))
            except Exception:
                pass

    def handle_startendtag(self, tag, attrs):
        try:
            tag = (tag or '').lower()
            if self._in_code_capture():
                # Do not emit literal <code/> or <pre/> self-closing inside capture
                if tag in ('code', 'pre'):
                    return
                self._code_append(self._reconstruct_startend_tag(tag, attrs))
                return
            if tag == 'br':
                # If inside suppressed script, ignore explicit breaks too
                if self._script_suppress_depth > 0:
                    return
                # record explicit line break so whitespace collapsers don't over-trim
                start = self.pos
                # record explicit line break so whitespace collapsers don't over-trim
                start = self.pos
                self.out.append('\n')
                self.pos += 1
                self._recent_br += 1
                self.ranges.setdefault('br', []).append([start, self.pos])
                return
            # Horizontal rule
            if tag == 'hr':
                self._ensure_leading_newlines(1)
                start = self.pos
                line = '-' * 40 + '\n'
                self.out.append(line)
                self.pos += len(line)
                self.ranges.setdefault('hr', []).append([start, self.pos])
                return
            # Image placeholder using alt text
            if tag == 'img':
                attrd = dict(attrs or {})
                alt = (attrd.get('alt') or '').strip()
                placeholder = f"[img: {alt}]" if alt else "[img]"
                start = self.pos
                self.out.append(placeholder)
                self.pos += len(placeholder)
                self.ranges.setdefault('img', []).append([start, self.pos])
                return
        except Exception:
            pass

    def handle_endtag(self, tag):
        try:
            tag_low = (tag or '').lower()

            # If currently inside a code/pre capture
            if self._in_code_capture():
                top = self._code_top()
                depth = 0
                try:
                    depth = int(top[3]) if len(top) >= 4 else 0
                except Exception:
                    depth = 0
                if tag_low in ('code', 'pre'):
                    if depth > 0:
                        # Closing a nested <code>/<pre>: adjust depth but DO NOT emit literal end tag
                        try:
                            top[3] = depth - 1
                        except Exception:
                            pass
                        return
                    # Finalize outermost capture below (no literal end tag)
                else:
                    # literal end tag for non-code inside capture
                    self._code_append(self._reconstruct_end_tag(tag_low))
                    return

            # Closing a suppressed <script>/<style>
            if tag_low == 'script' and self._script_suppress_depth > 0:
                try:
                    self._script_suppress_depth -= 1
                except Exception:
                    pass
                # After script removal, prevent large vertical gap: ensure at most one newline
                if self._current_tail_newline_count() > 1:
                    # collapse to single newline
                    while self._current_tail_newline_count() > 1:
                        # remove one newline char from tail
                        last = self.out[-1]
                        self.out[-1] = last[:-1]
                        self.pos -= 1
                return
            if tag_low == 'style' and self._style_suppress_depth > 0:
                try:
                    self._style_suppress_depth -= 1
                except Exception:
                    pass
                # Collapse excessive trailing newlines (same behavior as script)
                if self._current_tail_newline_count() > 1:
                    while self._current_tail_newline_count() > 1:
                        last = self.out[-1]
                        self.out[-1] = last[:-1]
                        self.pos -= 1
                return

            # Finalize outermost code/pre block (no literal end tag emitted)
            if tag_low in ('code', 'pre'):
                if not self.stack:
                    return
                item = self.stack.pop()
                if not item or item[0] != '__code__':
                    return
                fragments = item[2] if len(item) > 2 else []
                raw_code = ''.join(fragments) if fragments else ''
                # New: unified fenced parsing (``` / '''), attribute lang, heuristic fallback
                lang_hint = item[4] if len(item) > 4 else None
                segments = self._split_fenced_segments(raw_code)
                # If no fenced langs, apply attribute hint globally
                if lang_hint and all(seg['lang'] is None for seg in segments):
                    for seg in segments:
                        seg['lang'] = lang_hint
                # Heuristic fallback if still none
                if all(seg['lang'] is None for seg in segments):
                    guess = self._heuristic_guess_lang(raw_code) if hasattr(self, '_heuristic_guess_lang') else None
                    if guess:
                        for seg in segments:
                            seg['lang'] = guess

                # Build rendered block: newline + 4-space indent + wrapped/padded lines
                width = 60
                indent = '    '
                out_parts = ['\n']
                insert_start = self.pos
                current_abs_content_cursor = insert_start + 1
                content_spans = []
                # Collect per-segment per-line absolute starts to accurately map syntax tags
                syntax_segments = []  # list of {lang, lines:[str], abs_starts:[int]}

                for seg in segments:
                    seg_text = seg['text']
                    raw_lines = seg_text.splitlines() or ['']
                    wrapped_raw_lines = []
                    for line in raw_lines:
                        if line == '':
                            wrapped_raw_lines.append('')
                            continue
                        i = 0
                        while i < len(line):
                            chunk = line[i:i + width]
                            if len(chunk) == width and i + width < len(line):
                                sp = chunk.rfind(' ')
                                if sp > 0:
                                    wrapped_raw_lines.append(chunk[:sp].rstrip())
                                    i += sp + 1
                                    continue
                            wrapped_raw_lines.append(chunk)
                            i += len(chunk) if chunk else 1
                    padded_lines = [ln.ljust(width, ' ') for ln in wrapped_raw_lines] or [' ' * width]

                    # Track absolute starts for each content line in this segment
                    seg_abs_starts = []

                    for pl in padded_lines:
                        out_parts.append(indent + pl + '\n')
                        line_content_start = current_abs_content_cursor + len(indent)
                        line_content_end = line_content_start + len(pl)
                        # record global code_block content spans
                        content_spans.append((line_content_start, line_content_end))
                        # record per-line absolute start (for syntax highlighting)
                        seg_abs_starts.append(line_content_start)
                        # move cursor: past content and newline
                        current_abs_content_cursor = line_content_end + 1

                    if seg['lang']:
                        syntax_segments.append({
                            'lang': seg['lang'],
                            'lines': padded_lines,
                            'abs_starts': seg_abs_starts
                        })

                block_text = ''.join(out_parts)
                self.out.append(block_text)
                self.pos += len(block_text)

                # Tag the code_block content areas
                for s_abs, e_abs in content_spans:
                    self.ranges.setdefault('code_block', []).append([s_abs, e_abs])

                # Apply language-specific syntax tags per line to keep offsets exact
                for seg in syntax_segments:
                    lang = seg['lang']
                    for line_text, base_start in zip(seg['lines'], seg['abs_starts']):
                        try:
                            self._cb_apply_syntax(lang, line_text, base_start)
                        except Exception:
                            pass
                return

            # Normal non-code behavior
            if not self.stack:
                return
            item = self.stack.pop()
            if not item:
                return

            if isinstance(item, tuple) and item[0] == 'hyperlink':
                _, start, href, title = item
                end = self.pos
                if end > start:
                    self.ranges.setdefault('hyperlink', []).append([start, end])
                    try:
                        rec = {'start': start, 'end': end, 'href': href}
                        if title:
                            rec['title'] = title
                        self.hrefs.append(rec)
                    except Exception:
                        pass
                return

            if tag_low == 'ol':
                try:
                    if self._ol_counters:
                        self._ol_counters.pop()
                except Exception:
                    pass
                return

            # Closing block elements spacing
            if tag_low == 'p':
                self._ensure_trailing_block_spacing(require_blank=True)
            elif tag_low == 'div':
                self._ensure_trailing_block_spacing(require_blank=False)

            kind = item[0] if len(item) > 0 else None
            if kind in ('h1', 'h2'):
                # Ensure a blank line after H1/H2
                self._ensure_trailing_newlines(2)
            elif kind in ('h3', 'h4', 'h5', 'h6', 'blockquote'):
                self._ensure_trailing_newlines(1)
            elif kind == 'div_nav':
                # Give nav more breathing room
                self._ensure_trailing_newlines(2)
            elif kind == 'div_content':
                self._ensure_trailing_newlines(1)
            elif tag_low == 'p':
                self._ensure_trailing_block_spacing(require_blank=True)
            elif tag_low == 'div':
                self._ensure_trailing_block_spacing(require_blank=False)

            if tag_low == 'li':
                self._pending_li_leading = 0
            # Reset block-leading suppression when closing the block
            if tag_low in ('p', 'div'):
                # If still pending (no non-whitespace content was seen), clear it.
                self._pending_block_leading = None

            tagname = item[0] if len(item) > 0 else None
            start = item[1] if len(item) > 1 else None
            if not tagname or start is None:
                return
            end = self.pos
            if end > start:
                self.ranges.setdefault(tagname, []).append([start, end])
            # If this was a cell, finalize its recorded meta (end + text) and append to current row buffer.
            try:
                if tagname in ('td', 'th'):
                    # find the most-recent cell meta matching this start that has no end yet
                    found = None
                    for cm in reversed(self._cell_meta):
                        try:
                            if int(cm.get('start', -1)) == int(start) and (cm.get('end') is None or cm.get('end') == 0):
                                found = cm
                                break
                        except Exception:
                            continue
                    if found is not None:
                        try:
                            found['end'] = end
                            # extract the text content between start..end from the current output buffer
                            full_text = ''.join(self.out)
                            found['text'] = full_text[start:end]
                        except Exception:
                            try:
                                found['text'] = ''
                            except Exception:
                                pass
                        # Ensure the current row buffer contains this exact cm (append if missing)
                        try:
                            if self._current_row_cells:
                                cur = self._current_row_cells[-1]
                                if found not in cur:
                                    cur.append(found)
                        except Exception:
                            pass
            except Exception:
                pass

            # If this was a row close, finalize the row into the current table's rows list.
            try:
                if tagname == 'tr':
                    try:
                        if self._current_row_cells:
                            row_cells = self._current_row_cells.pop()
                        else:
                            row_cells = []
                        # attach this row to the most recent open table's rows accumulator
                        if self._current_table_rows:
                            self._current_table_rows[-1].append(row_cells)
                    except Exception:
                        pass
            except Exception:
                pass

            # If this was a table close, pop table attrs/rows and emit a table meta entry
            try:
                if tagname == 'table':
                    try:
                        attrs = self._table_attr_stack.pop() if self._table_attr_stack else {}
                    except Exception:
                        attrs = {}
                    try:
                        rows_meta = self._current_table_rows.pop() if self._current_table_rows else []
                    except Exception:
                        rows_meta = []
                    # compute a colgroup from rows_meta if possible
                    colgroup = []
                    try:
                        if rows_meta:
                            max_cols = max((len(r) for r in rows_meta), default=0)
                            col_widths = [0] * max_cols
                            for r in rows_meta:
                                for ci, cell in enumerate(r):
                                    try:
                                        txt = (cell.get('text') or '')
                                    except Exception:
                                        txt = ''
                         # Use the longest logical line inside the cell (respect IN_CELL_NL)
                                    try:
                                         logical_lines = txt.replace(IN_CELL_NL, '\n').split('\n')
                                         longest = max((len(ln) for ln in logical_lines), default=0)
                                    except Exception:
                                         longest = len(txt)
                                    col_widths[ci] = max(col_widths[ci], longest)                            
                            if max(col_widths, default=0) > 0 and max_cols > 0:
                                colgroup = [{'width': max(4, int(w))} for w in col_widths]
                    except Exception:
                        colgroup = []
                    try:
                        table_meta = {'start': start, 'end': end, 'attrs': attrs, 'rows': rows_meta, 'colgroup': colgroup}
                        self._table_meta.append(table_meta)
                    except Exception:
                        pass
            except Exception:
                pass        
        except Exception:
            pass

    def handle_data(self, data):
        try:
            if not data:
                return
           # Suppress script contents entirely
            if self._script_suppress_depth > 0:
                return
            # Suppress style contents entirely
            if self._style_suppress_depth > 0:
                return
            if self._in_code_capture():
                self._code_append(data)
                return

            # NEW: When parsing HTML, ignore purely-whitespace data that exists
            # between table-related tags (common in pretty-printed HTML). That
            # whitespace confuses downstream table reconstruction (it becomes
            # separate single-cell rows). Preserve whitespace when we are *inside*
            # an actual cell (i.e. a td/th has been opened and not closed).
            try:
                if data.strip() == '':
                    # Detect whether we are inside any table context:
                    in_table_stack = False
                    try:
                        # _current_table_rows and _table_attr_stack track open tables/tr parsing
                        if self._current_table_rows or self._table_attr_stack:
                            in_table_stack = True
                        else:
                            # also check explicit stack entries for an open table/tr/td/th
                            for entry in self.stack:
                                try:
                                    if isinstance(entry, (tuple, list)) and entry and entry[0] in ('table', 'tr', 'td', 'th'):
                                        in_table_stack = True
                                        break
                                except Exception:
                                    continue
                    except Exception:
                        in_table_stack = False

                    # If whitespace-only chunk and it is only layout whitespace between tags
                    # (we are in a table context but not inside an opened cell capture), drop it.
                    if in_table_stack:
                        # preserve whitespace if currently building cell content (open _cell_meta exists)
                        if not self._cell_meta:
                            return
                # end whitespace-between-table suppression
            except Exception:
                # on any error fall back to original behavior below
                pass

           # Tighten whitespace like an HTML renderer (outside code/pre):
           # - Collapse whitespace runs inside text nodes to single spaces.
           # - Limit vertical gaps between elements to at most two '\n'.
           # - Preserve explicit <br> vertical spacing (tracked via self._recent_br).
            s = data
            # Any chunk that is only whitespace?
            if s.strip() == '':
               # Special-case: immediately after opening <li> we may see template newlines/indent.
               # Keep bullet/number inline with the first content token (no newline).
                if self._pending_li_leading > 0:
                    # ensure at most a single separating space, but never a newline
                    prev_char = ''
                    if self.out:
                        last = self.out[-1]
                        prev_char = last[-1] if last else ''
                    if self.pos > 0 and prev_char not in (' ', '\t', '\n'):
                        self.out.append(' ')
                        self.pos += 1
                    self._pending_li_leading = max(0, self._pending_li_leading - 1)
                    return
                # Special-case: immediately after opening <p>/<div> suppress template newlines/indent.
                if self._pending_block_leading in ('p', 'div'):
                    # For paragraphs and generic divs, do NOT introduce a newline.
                    # If a separating space is useful (prev char is not whitespace), add a single space.
                    prev_char = ''
                    if self.out:
                        last = self.out[-1]
                        prev_char = last[-1] if last else ''
                    if prev_char not in (' ', '\t', '\n') and self.pos > 0:
                        self.out.append(' ')
                        self.pos += 1
                    # Consume this whitespace entirely
                    self._pending_block_leading = None
                    return
                has_nl = ('\n' in s)
                if has_nl:
                    # Add up to two newlines total at the tail, unless just added <br> lines.
                    tail_nl = self._current_tail_newline_count()
                    max_allowed = 2
                    add_nl = max(0, min(max_allowed - tail_nl, s.count('\n')))
                    if self._recent_br > 0:
                        # If the vertical space is intentional via <br>, don't add extra.
                        add_nl = 0
                    if add_nl > 0:
                        self.out.append('\n' * add_nl)
                        self.pos += add_nl
                else:
                    # Only spaces/tabs: emit at most a single separating space.
                    prev_char = ''
                    if self.out:
                        last = self.out[-1]
                        prev_char = last[-1] if last else ''
                    if self.pos > 0 and prev_char not in (' ', '\n', '\t'):
                        self.out.append(' ')
                        self.pos += 1
                # whitespace-only chunks don't reset <br> intent
                return

            # Mixed or non-whitespace content: collapse internal whitespace runs to single spaces.
            # Normalize all whitespace (including newlines) to a single space like HTML flow.
            s = re.sub(r'\s+', ' ', s)

            # Avoid inserting spaces around percent-encoded sequences like %20 (fixes " %20 " artifacts)
            try:
                s = re.sub(r'\s*(%[0-9A-Fa-f]{2})\s*', r'\1', s)
            except Exception:
                pass

            # Avoid leading pad if we're at start or after whitespace already.
            if s and self.pos == 0:
                s = s.lstrip()
            elif s and self.out:
                last = self.out[-1] or ''
                if last and last[-1] in (' ', '\n', '\t'):
                    s = s.lstrip()
            if not s:
                return
            self.out.append(s)
            self.pos += len(s)
            self._recent_br = 0
            self._pending_li_leading = 0
            self._pending_block_leading = None
        except Exception:
            pass
    def handle_entityref(self, name):
        try:
            if self._in_code_capture():
                self._code_append(f"&{name};")
                return
            if self._script_suppress_depth > 0:
                return
            if self._style_suppress_depth > 0:
                return
        except Exception:
            pass

    def handle_charref(self, name):
        try:
            if self._in_code_capture():
                self._code_append(f"&#{name};")
                return
            if self._script_suppress_depth > 0:
                return
            if self._style_suppress_depth > 0:
                return
        except Exception:
            pass

    def handle_comment(self, data):
        try:
            # Preserve comments inside code/pre blocks; suppress elsewhere.
            if self._in_code_capture():
                self._code_append(f"<!--{data}-->")
                return
            # Outside code capture, drop comments (including inside suppressed <script>)
            if self._style_suppress_depth > 0:
                return
            return
        except Exception:
            pass

    def get_result(self):
        """Produce final plain text and meta (tags, links, tables).
        This implementation preserves existing link/code metadata while applying
        aggressive, safe whitespace normalization for table cells and conservative
        padding that avoids pathological column expansion.
        """
        try:
            full = ''.join(self.out)

            # --- map markdown-style [text](url) into hyperlink ranges (preserve code blocks) ---
            try:
                md_link_re = re.compile(
                    r'\[([^\]]+)\]\('
                    r'(https?://[^\s)]+|file:///[^\s)]+|www\.[^\s)]+)'
                    r'\)'
                )
                protected = list(self.ranges.get('code_block', [])) if isinstance(self.ranges.get('code_block', []), list) else []
                existing_links = list(self.ranges.get('hyperlink', [])) if isinstance(self.ranges.get('hyperlink', []), list) else []

                def _overlaps_any(s: int, e: int, spans) -> bool:
                    for ps, pe in spans:
                        if not (e <= ps or s >= pe):
                            return True
                    return False

                new_out = []
                last = 0
                new_ranges = self.ranges.copy()
                new_hrefs = self.hrefs.copy()
                for m in md_link_re.finditer(full):
                    s_full, e_full = m.span()
                    s_text, e_text = m.start(1), m.end(1)
                    href = m.group(2).strip()
                    title = m.group(1).strip()

                    if _overlaps_any(s_text, e_text, protected) or _overlaps_any(s_text, e_text, existing_links):
                        continue

                    new_out.append(full[last:s_full])
                    link_start = sum(len(part) for part in new_out)
                    new_out.append(title)
                    link_end = link_start + len(title)

                    new_ranges.setdefault('hyperlink', []).append([link_start, link_end])
                    existing_links.append([link_start, link_end])

                    try:
                        rec = {'start': link_start, 'end': link_end, 'href': href}
                        if title:
                            rec['title'] = title
                        new_hrefs.append(rec)
                    except Exception:
                        pass

                    last = e_full
                new_out.append(full[last:])
                full = ''.join(new_out)
                self.ranges = new_ranges
                self.hrefs = new_hrefs
            except Exception:
                pass

            meta = {'tags': self.ranges}
            if self.hrefs:
                meta['links'] = list(self.hrefs)

            # --- Build table metadata with safe whitespace normalization and padding ---
            try:
                tables = []

                def _looks_like_layout_table(table_meta) -> bool:
                    try:
                        attrs = table_meta.get('attrs') or {}
                        style = (attrs.get('style') or '').lower()
                        layout_kw = ('width', 'padding', 'float', 'position', 'max-width', 'min-width')
                        if any(kw in style for kw in layout_kw):
                            return True

                        rows = table_meta.get('rows') or []
                        col_counts = [len(r) for r in rows if isinstance(r, list) and r]
                        if col_counts and (max(col_counts) != min(col_counts)):
                            return True

                        for r in rows:
                            for cell in r:
                                cattrs = (cell.get('attrs') or {}) if isinstance(cell, dict) else {}
                                cstyle = (cattrs.get('style') or '').lower()
                                if any(kw in cstyle for kw in ('width', 'padding', 'float')):
                                    return True
                                txt = (cell.get('text') or '') if isinstance(cell, dict) else ''
                                txt_l = str(txt).lower()
                                if 'img:' in txt_l or '<img' in txt_l or 'art-lightbox' in txt_l:
                                    return True
                                if re.search(r'\b(h1|h2|h3|h4|h5|h6)\b', txt_l):
                                    return True
                        return False
                    except Exception:
                        return False

                def _normalize_cell_text(s: str) -> str:
                    """Collapse runs of whitespace but preserve IN_CELL_NL as line separators."""
                    try:
                        if not isinstance(s, str):
                            return '' if s is None else str(s).strip()
                        # Protect IN_CELL_NL while collapsing other whitespace
                        placeholder = "__IN_CELL_NL__"
                        s2 = s.replace(IN_CELL_NL, placeholder)
                        # Collapse any whitespace (spaces, tabs, newlines) to single space
                        s2 = re.sub(r'\s+', ' ', s2)
                        # Restore protected cell-newlines and trim
                        s2 = s2.replace(placeholder, IN_CELL_NL)
                        return s2.strip()
                    except Exception:
                        return (s or '').strip()

                # Safety caps and thresholds
                MAX_COL_WIDTH_GLOBAL = 120      # prevents unbounded column width inflation
                LAYOUT_LONG_CELL_THRESHOLD = 200  # if any cell exceeds this, treat table as layout-like

                for t in self._table_meta:
                    try:
                        tstart = int(t.get('start', 0))
                        tend = int(t.get('end', 0))
                        if tstart < 0 or tend <= tstart or tstart >= len(full):
                            continue
                        tend = min(tend, len(full))

                        # Prefer structured rows if parser has them, else fall back to textual split
                        rows_meta = t.get('rows') if isinstance(t.get('rows'), list) and t.get('rows') else None
                        table_rows: List[List[dict]] = []

                        if rows_meta:
                            # Use recorded cell metas; normalize cell text in place
                            for r in rows_meta:
                                row_cells = []
                                for cm in r:
                                    cell_text = _normalize_cell_text(cm.get('text') or '')
                                    cell_entry = {
                                        'start': int(cm.get('start', 0)),
                                        'end': int(cm.get('end', 0)),
                                        'text': cell_text,
                                        'attrs': dict(cm.get('attrs', {})) if isinstance(cm.get('attrs', {}), dict) else {},
                                        'type': cm.get('type', 'td')
                                    }
                                    row_cells.append(cell_entry)
                                table_rows.append(row_cells)
                        else:
                            # Fallback: reconstruct rows/cells from raw slice using \n and \t
                            seg = full[tstart:tend]
                            rows = seg.split('\n')
                            abs_cursor = tstart
                            for rtext in rows:
                                cells = rtext.split('\t') if rtext != '' else ['']
                                row_cells = []
                                cell_cursor = abs_cursor
                                for cell_text in cells:
                                    cs = cell_cursor
                                    ce = cs + len(cell_text)
                                    norm = _normalize_cell_text(cell_text)
                                    cell_entry = {'start': cs, 'end': ce, 'text': norm, 'attrs': {}, 'type': 'td'}
                                    row_cells.append(cell_entry)
                                    cell_cursor = ce + 1
                                table_rows.append(row_cells)
                                abs_cursor += len(rtext) + 1

                        if not table_rows:
                            continue

                        # detect layout-like
                        layout_like = _looks_like_layout_table(t)

                        # Also treat tables with any extremely long cell as layout-like
                        any_long = any(len(cell.get('text') or '') >= LAYOUT_LONG_CELL_THRESHOLD for row in table_rows for cell in row)
                        if any_long:
                            layout_like = True

                        # Compute colgroup for data-like tables; otherwise leave empty and apply row padding
                        colgroup = t.get('colgroup', []) or []
                        if not colgroup and not layout_like:
                            max_cols = max((len(r) for r in table_rows), default=0)
                            if max_cols:
                                col_widths = [0] * max_cols
                                for r in table_rows:
                                    for ci, cell in enumerate(r):
                                        txt = (cell.get('text') or '')
                                        col_widths[ci] = max(col_widths[ci], len(txt))
                                # apply safety cap
                                col_widths = [min(w, MAX_COL_WIDTH_GLOBAL) for w in col_widths]
                                if max(col_widths, default=0) > 0 and max_cols > 0:
                                    colgroup = [{'width': max(4, int(w))} for w in col_widths]

                        # Build normalized/padded rows for metadata (tabs separate cells)
                        new_rows: List[str] = []

                        # Determine column count
                        max_cols = max((len(r) for r in table_rows), default=0)

                        # Helper: pad all logical lines inside a cell to a given width,
                        # preserving IN_CELL_NL as line separator.
                        def _pad_cell_lines(cell_text: str, width: int) -> str:
                            try:
                                if not isinstance(cell_text, str):
                                    cell_text = '' if cell_text is None else str(cell_text)
                                parts = cell_text.split(IN_CELL_NL) if IN_CELL_NL in cell_text else [cell_text]
                                out_parts = []
                                for p in parts:
                                    # collapse internal whitespace already done; just pad
                                    txt = p
                                    if len(txt) > width:
                                        txt = txt[:width]
                                    out_parts.append(txt.ljust(width))
                                # Rejoin with IN_CELL_NL so downstream renderer can convert to <br>
                                return IN_CELL_NL.join(out_parts)
                            except Exception:
                                return cell_text.ljust(width) if isinstance(cell_text, str) else ''

                        # Special-case: single-column tables should be padded to the table-wide width so they render as a solid block.
                        if max_cols == 1:
                            # Determine table width: prefer colgroup width if present, else compute from data and cap.
                            if colgroup and isinstance(colgroup, list) and len(colgroup) >= 1 and str(colgroup[0].get('width', '')).isdigit():
                                table_width = min(MAX_COL_WIDTH_GLOBAL, int(colgroup[0].get('width', MAX_COL_WIDTH_GLOBAL)))
                            else:
                                # compute longest logical line inside any cell (respect IN_CELL_NL)
                                max_len = 0
                                for r in table_rows:
                                    raw = (r[0].get('text') or '')
                                    # consider longest sub-line
                                    for sub in (raw.split(IN_CELL_NL) if IN_CELL_NL in raw else [raw]):
                                        max_len = max(max_len, len(sub))
                                table_width = min(MAX_COL_WIDTH_GLOBAL, max_len)

                            if table_width <= 0:
                                table_width = min(MAX_COL_WIDTH_GLOBAL, max((len(r[0].get('text') or '') for r in table_rows), default=0))

                            # Build rows: pad each logical line in the single cell to table_width
                            for r in table_rows:
                                txt = (r[0].get('text') or '')
                                padded = _pad_cell_lines(txt, table_width)
                                # for plain metadata rows, store as single-line (tabs separate cells)
                                # join logical lines into a single visible string by replacing IN_CELL_NL with spaces
                                # but keep metadata text containing IN_CELL_NL so renderer shows breaks
                                # For the plain text index we use IN_CELL_NL-preserved string.
                                # Use a single tab-less cell (no '\t') for single-column table row.
                                new_rows.append(padded)

                        else:
                            if not layout_like and colgroup:
                                # data-like: pad columns according to colgroup widths
                                widths = []
                                for c in colgroup:
                                    w = c.get('width')
                                    try:
                                        widths.append(int(w))
                                    except Exception:
                                        widths.append(0)
                                # fallback to computed widths if necessary
                                if not widths or any((not isinstance(w, int) or w <= 0) for w in widths):
                                    max_cols = max((len(r) for r in table_rows), default=0)
                                    widths = [0] * max_cols
                                    for r in table_rows:
                                        for ci, cell in enumerate(r):
                                            widths[ci] = max(widths[ci], len(cell.get('text') or ''))
                                    widths = [min(w, MAX_COL_WIDTH_GLOBAL) for w in widths]
                                for r in table_rows:
                                    padded = []
                                    for ci in range(len(widths)):
                                        text = r[ci].get('text') if ci < len(r) else ''
                                        # If cell contains multiple logical lines, pad each line then collapse for metadata row
                                        if IN_CELL_NL in (text or ''):
                                            cell_p = _pad_cell_lines(text, widths[ci] if widths[ci] > 0 else 0)
                                            # Convert logical-line separators to space for the plain cell string so it fits in a single tab field
                                            cell_for_field = cell_p.replace(IN_CELL_NL, ' ')
                                            padded.append(cell_for_field)
                                        else:
                                            padded.append((text or '').ljust(widths[ci] if widths[ci] > 0 else 0))
                                    new_rows.append('\t'.join(padded))
                            else:
                                # layout-like or no colgroup: strip excess whitespace already done;
                                # pad each row to its own max (capped), padding inside multi-line cells as well.
                                for r in table_rows:
                                    # compute per-cell max of its logical lines
                                    row_texts = [cell.get('text') or '' for cell in r]
                                    # compute longest logical sub-line across the row
                                    row_max = 0
                                    for txt in row_texts:
                                        if IN_CELL_NL in txt:
                                            for sub in txt.split(IN_CELL_NL):
                                                row_max = max(row_max, len(sub))
                                        else:
                                            row_max = max(row_max, len(txt))
                                    if row_max > MAX_COL_WIDTH_GLOBAL:
                                        row_max = MAX_COL_WIDTH_GLOBAL
                                    padded = []
                                    for txt in row_texts:
                                        # pad internal logical lines
                                        pcell = _pad_cell_lines(txt, row_max)
                                        # metadata row must be tab-separated single field; collapse IN_CELL_NL to space
                                        padded.append(pcell.replace(IN_CELL_NL, ' '))
                                    new_rows.append('\t'.join(padded))

                        new_seg = '\n'.join(new_rows)

                        # Update overall text and adjust offsets
                        start_abs = tstart + offset_shift if (tstart + offset_shift) < len(full) else tstart
                        end_abs = tend + offset_shift if (tend + offset_shift) <= len(full) else min(tend, len(full))
                        full = full[:start_abs] + new_seg + full[end_abs:]
                        delta = len(new_seg) - (end_abs - start_abs)
                        offset_shift += delta

                        # Build table_entry rows metadata to return (use normalized texts)
                        meta_rows = []
                        cursor = start_abs
                        for rstr in new_rows:
                            cells = rstr.split('\t') if rstr != '' else ['']
                            row_cells = []
                            cell_cursor = cursor
                            for c in cells:
                                cs = cell_cursor
                                ce = cs + len(c)
                                row_cells.append({'start': cs, 'end': ce, 'text': c, 'attrs': {}, 'type': 'td'})
                                cell_cursor = ce + 1
                            meta_rows.append(row_cells)
                            cursor = cursor + len(rstr) + 1

                        table_entry = {'start': start_abs, 'end': start_abs + len(new_seg), 'attrs': t.get('attrs', {}), 'rows': meta_rows, 'colgroup': colgroup}
                        if layout_like:
                            table_entry['layout_table'] = True

                        tables.append(table_entry)
                    except Exception:
                        continue
                if tables:
                    meta['tables'] = tables
            except Exception:
                pass

            # final top-of-document soft collapse (keep first content at top)
            try:
                new_full, removed = self._collapse_leading_blank_region(full)
                if removed > 0:
                    self._shift_all_ranges_and_links(-removed)
                    full = new_full
            except Exception:
                pass

            return full, meta
        except Exception:
            return ''.join(self.out), {'tags': self.ranges, 'links': list(self.hrefs)}
    # --- Codeblock syntax helpers (isolated tags: cb_*) ----------------------
    def _cb_apply_syntax(self, lang: str, text: str, base_off: int):
        lang = (lang or '').lower()
        if lang == 'python':
            self._cb_python(text, base_off)
        elif lang == 'json':
            self._cb_json(text, base_off)
        elif lang == 'html':
            self._cb_html(text, base_off)
        elif lang == 'markdown':
            self._cb_markdown(text, base_off)
        elif lang in ('javascript','js'):
            self._cb_javascript(text, base_off)
        elif lang in ('c','cpp'):
            self._cb_c(text, base_off)
        elif lang in ('yaml','yml'):
            self._cb_yaml(text, base_off)
        elif lang in ('rathena_npc','rathena-npc','npc','rathena','rathena_script'):
            self._cb_rathena_npc(text, base_off)
        elif lang in ('rathena_yaml','rathena-yaml','rathena_db'):
            # Rathena YAML uses YAML tokenization but we keep a distinct entry for future extensions
            self._cb_yaml(text, base_off)

    def _cb_add(self, tag: str, s: int, e: int):
        if e > s:
            self.ranges.setdefault(tag, []).append([s, e])

    def _cb_python(self, text: str, base: int):
        try:
            kw = (
                'if','else','elif','while','for','return','def','from','import','class','try','except',
                'finally','with','as','lambda','in','is','not','and','or','yield','raise','global',
                'nonlocal','assert','del','async','await','pass','break','continue','match','case','True','False','None'
            )
            kw_re = re.compile(r'\b(' + '|'.join(map(re.escape, kw)) + r')\b')
            str_re = re.compile(r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"[^"\n]*"|\'[^\'\n]*\')')
            com_re = re.compile(r'#[^\n]*')
            num_re = re.compile(r'\b(?:0b[01_]+|0o[0-7_]+|0x[0-9A-Fa-f_]+|\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?)\b')
            for m in str_re.finditer(text):
                self._cb_add('cb_string', base + m.start(), base + m.end())
            for m in com_re.finditer(text):
                self._cb_add('cb_comment', base + m.start(), base + m.end())
            for m in num_re.finditer(text):
                self._cb_add('cb_number', base + m.start(), base + m.end())
            prot = self.ranges.get('cb_string', []) + self.ranges.get('cb_comment', [])
            def _overlaps(s, e):
                for ps, pe in prot:
                    if not (e <= ps or s >= pe):
                        return True
                return False
            for m in kw_re.finditer(text):
                s, e = base + m.start(), base + m.end()
                if not _overlaps(s, e):
                    self._cb_add('cb_keyword', s, e)
        except Exception:
            pass

    def _cb_json(self, text: str, base: int):
        try:
            str_re = re.compile(r'"(?:\\.|[^"\\])*"')
            num_re = re.compile(r'\b-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?\b')
            kw_re = re.compile(r'\b(true|false|null)\b', re.IGNORECASE)
            for m in str_re.finditer(text):
                self._cb_add('cb_string', base + m.start(), base + m.end())
            for m in num_re.finditer(text):
                self._cb_add('cb_number', base + m.start(), base + m.end())
            for m in kw_re.finditer(text):
                self._cb_add('cb_keyword', base + m.start(), base + m.end())
        except Exception:
            pass

    def _cb_html(self, text: str, base: int):
        try:
            com_re = re.compile(r'<!--[\s\S]*?-->')
            tagname_re = re.compile(r'</?([A-Za-z][A-Za-z0-9:\-]*)')
            attr_re = re.compile(r'([A-Za-z_:][A-Za-z0-9_:.\-]*)\s*=')
            aval_re = re.compile(r'=\s*(?:"([^"]*?)"|\'([^\']*?)\'|([^\s>]+))')
            for m in com_re.finditer(text):
                self._cb_add('cb_comment', base + m.start(), base + m.end())
            for m in tagname_re.finditer(text):
                self._cb_add('cb_tag', base + m.start(1), base + m.end(1))
            for m in attr_re.finditer(text):
                self._cb_add('cb_attr', base + m.start(1), base + m.end(1))
            for m in aval_re.finditer(text):
                g = 1 if m.group(1) is not None else (2 if m.group(2) is not None else (3 if m.group(3) is not None else None))
                if g:
                    self._cb_add('cb_attr_value', base + m.start(g), base + m.end(g))
        except Exception:
            pass

    def _cb_markdown(self, text: str, base: int):
        try:
            head_re = re.compile(r'(?m)^(#{1,6}\s+.+)$')
            code_inline = re.compile(r'`([^`]+)`')
            for m in head_re.finditer(text):
                self._cb_add('cb_keyword', base + m.start(1), base + m.end(1))
            for m in code_inline.finditer(text):
                self._cb_add('cb_string', base + m.start(1), base + m.end(1))
        except Exception:
            pass

    # YAML tokenizer (generic)
    def _cb_yaml(self, text: str, base: int):
        try:
            # Comments
            com_re = re.compile(r'#[^\n]*')
            # Keys (before colon), avoid matching inside strings
            key_re = re.compile(r'(?m)^(?:\s*-?\s*)?([A-Za-z0-9_.-]+)\s*:(?=\s|$)')
            # Strings: single/double quoted
            str_re = re.compile(r'("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\')')
            # Numbers (ints, floats)
            num_re = re.compile(r'\b-?(?:0|[1-9]\d*)(?:\.\d+)?\b')
            # Booleans/null
            kw_re = re.compile(r'\b(true|false|null|on|off|yes|no)\b', re.IGNORECASE)
            for m in com_re.finditer(text):
                self._cb_add('cb_comment', base + m.start(), base + m.end())
            for m in str_re.finditer(text):
                self._cb_add('cb_string', base + m.start(), base + m.end())
            for m in key_re.finditer(text):
                self._cb_add('cb_attr', base + m.start(1), base + m.end(1))
            for m in num_re.finditer(text):
                self._cb_add('cb_number', base + m.start(), base + m.end())
            for m in kw_re.finditer(text):
                self._cb_add('cb_keyword', base + m.start(), base + m.end())
        except Exception:
            pass

    # Rathena NPC tokenizer (best-effort)
    def _cb_rathena_npc(self, text: str, base: int):
        try:
            # Comments: // line comments
            com_re = re.compile(r'//[^\n]*')
            # Strings: "..." and '...'
            str_re = re.compile(r'("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\')')
            # Numbers
            num_re = re.compile(r'\b\d+(?:\.\d+)?\b')
            # Keywords: common rAthena script commands and flow control
            kw = (
                'mes','next','close','end','goto','switch','case','break',
                'if','else','for','while','do','return',
                'set','setarray','getarg','getiteminfo','getitemname',
                'getitem','delitem','countitem','strcharinfo','select',
                'rand','input','npcname','disablenpc','enablenpc','announce',
                'sleep','callfunc','callsub','function','bonus','bonus2',
                'gettime','getmapxy','warp','areawarp','unitkill','specialeffect',
                'getnameditem','getinventorylist','getitem2','getitembound'
            )
            kw_re = re.compile(r'\b(' + '|'.join(map(re.escape, kw)) + r')\b', re.IGNORECASE)
            # Variables: .@local, @account, $global, $@arrays
            var_re = re.compile(r'(\.@[A-Za-z_]\w*|@[A-Za-z_]\w*|\$@?[A-Za-z_]\w*)')
            # Labels: e.g., OnInit:, OnTouch:, OnTimer1000:
            label_re = re.compile(r'(?m)^(On[A-Za-z0-9_]+)\s*:')
            # Operators: basic symbolic operators
            op_re = re.compile(r'([+\-*/%=!<>]{1,2})')
            # Apply
            for m in com_re.finditer(text):
                self._cb_add('cb_comment', base + m.start(), base + m.end())
            for m in str_re.finditer(text):
                self._cb_add('cb_string', base + m.start(), base + m.end())
            for m in num_re.finditer(text):
                self._cb_add('cb_number', base + m.start(), base + m.end())
            for m in kw_re.finditer(text):
                self._cb_add('cb_keyword', base + m.start(), base + m.end())
            for m in var_re.finditer(text):
                self._cb_add('cb_attr', base + m.start(1), base + m.end(1))
            for m in label_re.finditer(text):
                self._cb_add('cb_tag', base + m.start(1), base + m.end(1))
            for m in op_re.finditer(text):
                self._cb_add('cb_operator', base + m.start(1), base + m.end(1))
        except Exception:
            pass

    # Added JavaScript tokenizer
    def _cb_javascript(self, text: str, base: int):
        try:
            kw = ('function','return','var','let','const','if','else','for','while','switch','case',
                  'break','continue','new','class','extends','import','from','export','default','try',
                  'catch','finally','throw','async','await','this','null','true','false')
            kw_re = re.compile(r'\b(' + '|'.join(map(re.escape, kw)) + r')\b')
            str_re = re.compile(r'("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\'|`[^`]*`)')
            com_re = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/')
            num_re = re.compile(r'\b\d+(?:\.\d+)?\b')
            protected = []
            for m in str_re.finditer(text):
                self._cb_add('cb_string', base + m.start(), base + m.end()); protected.append((base + m.start(), base + m.end()))
            for m in com_re.finditer(text):
                self._cb_add('cb_comment', base + m.start(), base + m.end()); protected.append((base + m.start(), base + m.end()))
            for m in num_re.finditer(text):
                self._cb_add('cb_number', base + m.start(), base + m.end())
            for m in kw_re.finditer(text):
                s, e = base + m.start(), base + m.end()
                if not any(not (e <= ps or s >= pe) for ps, pe in protected):
                    self._cb_add('cb_keyword', s, e)
        except Exception:
            pass

    # Added C / C++ minimal tokenizer
    def _cb_c(self, text: str, base: int):
        try:
            kw = ('int','char','float','double','struct','typedef','return','if','else','for','while',
                  'switch','case','break','continue','static','const','void','class','public','private',
                  'protected','virtual','template','enum','union','sizeof')
            kw_re = re.compile(r'\b(' + '|'.join(map(re.escape, kw)) + r')\b')
            com_re = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/')
            str_re = re.compile(r'"([^"\\]|\\.)*"')
            num_re = re.compile(r'\b\d+(?:\.\d+)?\b')
            protected = []
            for m in str_re.finditer(text):
                self._cb_add('cb_string', base + m.start(), base + m.end()); protected.append((base + m.start(), base + m.end()))
            for m in com_re.finditer(text):
                self._cb_add('cb_comment', base + m.start(), base + m.end()); protected.append((base + m.start(), base + m.end()))
            for m in num_re.finditer(text):
                self._cb_add('cb_number', base + m.start(), base + m.end())
            for m in kw_re.finditer(text):
                s, e = base + m.start(), base + m.end()
                if not any(not (e <= ps or s >= pe) for ps, pe in protected):
                    self._cb_add('cb_keyword', s, e)
        except Exception:
            pass

    # Added simple heuristic guess (used when no fences / attrs)
    def _heuristic_guess_lang(self, text: str) -> str | None:
        try:
            t = text.strip()
            if not t:
                return None
            # JSON-like: leading brace with key:value pairs
            if re.search(r'^\s*{[\s\S]*:\s*["\']', t[:300]):
                return 'json'
            if re.search(r'\bdef\s+\w+\s*\(', t):
                return 'python'
            if '#include' in t:
                return 'c'
            if '<html' in t.lower() or '<div' in t.lower():
                return 'html'
            if re.search(r'\bclass\s+\w+\s*\{', t) and ';' in t:
                return 'cpp'
            # Markdown heuristics:
            # - Lines starting with heading marks (#, ##, etc.)
            # - List markers (-, *, +, or digit.) at line starts
            # - Code fences (``` without a language)
            # - Blockquotes starting with '>'
            # - Link or image markdown patterns [text](url), ![alt](src)
            md_head = re.search(r'(?m)^\s*#{1,6}\s+\S', t)
            md_list = re.search(r'(?m)^\s*(?:[-*+]|\d+\.)\s+\S', t)
            md_fence = re.search(r'(?m)^\s*```(?:\s*$|\s*\w+\s*$)', t)
            md_quote = re.search(r'(?m)^\s*>\s+\S', t)
            md_link = re.search(r'\[[^\]]+\]\([^)]+\)', t)
            md_img = re.search(r'!\[[^\]]*\]\([^)]+\)', t)
            md_table = re.search(r'(?m)^\s*\|.+\|\s*$', t) and re.search(r'(?m)^\s*[-|:]{3,}\s*$', t)
            if md_head or md_list or md_fence or md_quote or md_link or md_img or md_table:
                return 'markdown'
            # YAML-like: common patterns (key: value, dashes for lists)
            if re.search(r'(?m)^\s*-[ \t]', t) or re.search(r'(?m)^[A-Za-z0-9_.-]+\s*:', t):
                return 'yaml'
            # Rathena NPC heuristics:
            # presence of OnInit:/OnTouch:, mes;, and rAthena style variables (.@, $@, @)
            if re.search(r'(?m)^On[A-Za-z0-9_]+\s*:', t) or 'mes' in t or re.search(r'(\.@|@\w|\$@?)', t):
                return 'rathena_npc'
            return None
        except Exception:
            return None

def extract_script_tags(html: str) -> list:
    """Return list of scripts found in HTML in document order.
    Each entry: {'src': <url or None>, 'inline': <source or None>, 'attrs': {k:v}}
    """
    out = []
    for m in _SCRIPT_RE.finditer(html):
        attrstr = m.group(1) or ''
        inline = m.group(2) or ''
        attrs = {}
        for am in re.finditer(r'([A-Za-z_:][A-Za-z0-9_:.\-]*)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', attrstr):
            key = am.group(1).lower()
            val = am.group(2) or am.group(3) or am.group(4) or ''
            attrs[key] = val
        src = attrs.get('src') or None
        out.append({'src': src, 'inline': inline if inline.strip() else None, 'attrs': attrs})
    return out

def run_scripts(scripts: list, base_url: Optional[str] = None, log_fn=None, host_update_cb: Optional[Callable[[str], None]] = None, show_console: Optional[bool] = None, run_blocking: bool = False):
    """Execute script entries using jsmini.

    Behaviour changes:
    - When called from the Tk main thread and `run_blocking` is False (default),
      scripts will run asynchronously on a background thread and this function
      returns immediately with `[('async', None)]`. This gives the same perceived
      responsiveness whether or not the JS Console is open.
    - Callers that need synchronous results can pass `run_blocking=True`.
    - `show_console` controls whether a reusable popup console is opened (when True)
      or the persisted default is used when None.
    - `log_fn` is still supported and will receive the same log lines as the console.
    """
    results = []
    try:
        import jsmini
    except Exception as e:
        for _ in scripts:
            results.append((False, f"jsmini import failed: {e}"))
        return results

    try:
        actual_show_console = show_console if show_console is not None else get_js_console_default()
    except Exception:
        actual_show_console = bool(show_console)

    on_main = threading.current_thread().name == 'MainThread'

    # If caller is on main thread and not forcing blocking, run asynchronously on a worker
    if on_main and not run_blocking:
        def _worker():
            local_results = []
            try:
                # create console if requested (scheduled on UI thread inside helper)
                try:
                    if actual_show_console:
                        _ensure_js_console()
                except Exception:
                    pass

                # combined logger: writes to console (if available) and to provided log_fn
                def _combined_log(s: str):
                    try:
                        if actual_show_console:
                            _console_append(s)
                        elif callable(log_fn):
                            # still forward to provided log_fn even when no console
                            try:
                                log_fn(s)
                            except Exception:
                                pass
                        else:
                            # fallback: print so there's some visible output
                            try:
                                print(s)
                            except Exception:
                                pass
                        # always call external log_fn as well if present
                        if callable(log_fn):
                            try:
                                log_fn(s)
                            except Exception:
                                pass
                    except Exception:
                        try:
                            print(s)
                        except Exception:
                            pass

                # create a shared context so timers/globals persist across scripts
                ctx = jsmini.make_context(log_fn=_combined_log if (actual_show_console or callable(log_fn)) else None)

                if host_update_cb:
                    try:
                        ctx['setRaw'] = host_update_cb
                        ctx['host'] = {'setRaw': host_update_cb, 'forceRerender': lambda: host_update_cb(None)}
                    except Exception:
                        pass

                for idx, s in enumerate(scripts):
                    try:
                        src_info = s.get('src') or '<inline>'
                        _combined_log(f"[jsconsole] Running script {idx + 1}/{len(scripts)} - {src_info}")
                        preview = (s.get('inline') or '')[:400] if not s.get('src') else None
                        if preview:
                            _combined_log(f"[jsconsole] Inline preview: {preview!r}{'...' if len(s.get('inline') or '')>400 else ''}")
                    except Exception:
                        pass

                    if s.get('src'):
                        src = s['src']
                        resolved = src
                        try:
                            if base_url:
                                resolved = _up.urljoin(base_url, src)
                            req = _urr.Request(resolved, headers={"User-Agent": "SimpleEdit/jsmini"})
                            with _urr.urlopen(req, timeout=10) as resp:
                                raw_bytes = resp.read()
                                script_src = raw_bytes.decode(resp.headers.get_content_charset() or 'utf-8', errors='replace')
                        except Exception as fe:
                            _combined_log(f"[jsconsole] Failed to fetch {resolved}: {fe}")
                            local_results.append((False, f"Failed to fetch {resolved}: {fe}"))
                            continue
                    else:
                        script_src = s.get('inline', '') or ''

                    run_src = _strip_leading_license_comment(script_src if 'script_src' in locals() else (s.get('inline') or ''))
                    if run_src != (script_src if 'script_src' in locals() else (s.get('inline') or '')):
                        """try:
                            _console_append("[jsconsole] Stripped leading /*!...*/ license header before execution (common in minified libs).")
                        except Exception:
                            pass"""
                    
                    try:
                        jsmini.run_with_interpreter(run_src, ctx)
                        _combined_log(f"[jsconsole] Script {idx + 1} executed successfully.")
                    except Exception as rexc:
                        # capture traceback string (best-effort)
                        try:
                            tb_str = _traceback.format_exc()
                        except Exception:
                            tb_str = None
                    
                        # Primary context from original source (helps identify problematic header/content)
                        try:
                            original_src = script_src if 'script_src' in locals() else (s.get('inline') or '')
                            ctx_primary = _format_js_error_context(original_src, rexc, tb_str)
                            _console_append(f"[jsconsole] Execution error in script {idx + 1}: {rexc}")
                            if ctx_primary:
                                _console_append("[jsconsole] Error context (from original source, approx):")
                                for ln in str(ctx_primary).splitlines():
                                    _console_append("  " + ln)
                        except Exception:
                            _console_append(f"[jsconsole] Execution error in script {idx + 1}: {rexc}")
                    
                        # Secondary context from cleaned source (if different) to show where execution actually reached
                        try:
                            if run_src and run_src != (original_src if 'original_src' in locals() else ''):
                                ctx_clean = _format_js_error_context(run_src, rexc, tb_str)
                                if ctx_clean:
                                    _console_append("[jsconsole] Error context (from cleaned source, approx):")
                                    for ln in str(ctx_clean).splitlines():
                                        _console_append("  " + ln)
                        except Exception:
                            pass
                    
                        results.append((False, f"Execution error: {rexc}"))
                        continue

                # run timers after scripts
                try:
                    _combined_log("[jsconsole] Running timers...")
                    jsmini.run_timers(ctx)
                    _combined_log("[jsconsole] Timers run complete.")
                except Exception as exc:
                    _combined_log(f"[jsconsole] Timers error: {exc}")

                _combined_log("[jsconsole] All scripts processed.")
            except Exception as e:
                try:
                    _console_append(f"[jsconsole] Unexpected error in async worker: {e}")
                except Exception:
                    try:
                        print(f"[jsconsole] Unexpected error in async worker: {e}")
                    except Exception:
                        pass
            finally:
                # If a caller later inspects results via side-channel you could persist them somewhere.
                return

        Thread(target=_worker, daemon=True).start()
        return [('async', None)]


    # Synchronous (blocking) path: run in current thread (used when run_blocking=True or not on main thread)
    console_created = False
    if actual_show_console:
        try:
            _ensure_js_console()
            console_created = True
            _console_append(f"[jsconsole] Opened console for {len(scripts)} script(s).")
        except Exception:
            console_created = False

    # combined logger for sync path
    def _combined_log_sync(s: str):
        try:
            if actual_show_console:
                _console_append(s)
            if callable(log_fn):
                try:
                    log_fn(s)
                except Exception:
                    pass
            if not actual_show_console and not callable(log_fn):
                try:
                    print(s)
                except Exception:
                    pass
        except Exception:
            try:
                print(s)
            except Exception:
                pass


    ctx = jsmini.make_context(log_fn=_combined_log_sync if (actual_show_console or callable(log_fn)) else None)
    if host_update_cb:
        try:
            ctx['setRaw'] = host_update_cb
            ctx['host'] = {
                'setRaw': host_update_cb,
                'forceRerender': lambda: host_update_cb(None)
            }
        except Exception:
            pass

    for idx, s in enumerate(scripts):
        try:
            try:
                src_info = s.get('src') or '<inline>'
                _combined_log_sync(f"[jsconsole] Running script {idx + 1}/{len(scripts)} - {src_info}")
                preview = (s.get('inline') or '')[:400] if not s.get('src') else None
                if preview:
                    _combined_log_sync(f"[jsconsole] Inline preview: {preview!r}{'...' if len(s.get('inline') or '')>400 else ''}")
            except Exception:
                pass

            if s.get('src'):
                src = s['src']
                resolved = src
                try:
                    if base_url:
                        resolved = _up.urljoin(base_url, src)
                    req = _urr.Request(resolved, headers={"User-Agent": "SimpleEdit/jsmini"})
                    with _urr.urlopen(req, timeout=10) as resp:
                        raw_bytes = resp.read()
                        script_src = raw_bytes.decode(resp.headers.get_content_charset() or 'utf-8', errors='replace')
                except Exception as fe:
                    _combined_log_sync(f"[jsconsole] Failed to fetch {resolved}: {fe}")
                    results.append((False, f"Failed to fetch {resolved}: {fe}"))
                    continue
            else:
                script_src = s.get('inline', '') or ''

            run_src = _strip_leading_license_comment(script_src if 'script_src' in locals() else (s.get('inline') or ''))
            if run_src != (script_src if 'script_src' in locals() else (s.get('inline') or '')):
                try:
                    _console_append("[jsconsole] Stripped leading /*!...*/ license header before execution (common in minified libs).")
                except Exception:
                    pass
            
            try:
                jsmini.run_with_interpreter(run_src, ctx)
                _combined_log_sync(f"[jsconsole] Script {idx + 1} executed successfully.")
            except Exception as rexc:
                # capture traceback string (best-effort)
                try:
                    tb_str = _traceback.format_exc()
                except Exception:
                    tb_str = None
            
                # Primary context from original source (helps identify problematic header/content)
                try:
                    original_src = script_src if 'script_src' in locals() else (s.get('inline') or '')
                    ctx_primary = _format_js_error_context(original_src, rexc, tb_str)
                    _console_append(f"[jsconsole] Execution error in script {idx + 1}: {rexc}")
                    if ctx_primary:
                        _console_append("[jsconsole] Error context (from original source, approx):")
                        for ln in str(ctx_primary).splitlines():
                            _console_append("  " + ln)
                except Exception:
                    _console_append(f"[jsconsole] Execution error in script {idx + 1}: {rexc}")
            
                # Secondary context from cleaned source (if different) to show where execution actually reached
                try:
                    if run_src and run_src != (original_src if 'original_src' in locals() else ''):
                        ctx_clean = _format_js_error_context(run_src, rexc, tb_str)
                        if ctx_clean:
                            _console_append("[jsconsole] Error context (from cleaned source, approx):")
                            for ln in str(ctx_clean).splitlines():
                                _console_append("  " + ln)
                except Exception:
                    pass
            
                results.append((False, f"Execution error: {rexc}"))
                continue

            try:
                if console_created:
                    _bring_console_to_front()
            except Exception:
                pass

            results.append((True, None))
        except Exception as e:
            _combined_log_sync(f"[jsconsole] Unexpected error running script {idx + 1}: {e}")
            results.append((False, str(e)))

    try:
        _combined_log_sync("[jsconsole] Running timers...")
        jsmini.run_timers(ctx)
        _combined_log_sync("[jsconsole] Timers run complete.")
    except Exception as exc:
        _combined_log_sync(f"[jsconsole] Timers error: {exc}")

    _combined_log_sync("[jsconsole] All scripts processed.")
    return results

def get_hex_color(color_tuple):
    """Return a hex string from a colorchooser return value."""
    if not color_tuple:
        return ""
    if isinstance(color_tuple, tuple) and len(color_tuple) >= 2:
        return color_tuple[1]
    m = re.search(r'#\w+', str(color_tuple))
    return m.group(0) if m else ""

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    """Return (r,g,b) for hex like '#rrggbb' or 'rrggbb'."""
    try:
        s = (h or '').strip()
        if s.startswith('#'):
            s = s[1:]
        if len(s) == 3:
            s = ''.join(ch*2 for ch in s)
        if len(s) != 6:
            return (0, 0, 0)
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except Exception:
        return (0, 0, 0)

def _rgb_to_hex(r: int, g: int, b: int) -> str:
    """Return '#rrggbb' from 0-255 RGB."""
    try:
        return f"#{int(r):02x}{int(g):02x}{int(b):02x}"
    except Exception:
        return "#000000"

def _sanitize_tag_name(s: str) -> str:
    """Create a safe tag name from family and size (alnum + underscores only)."""
    try:
        return re.sub(r'[^0-9a-zA-Z_]', '_', s).strip('_')
    except Exception:
        return re.sub(r'\s+', '_', str(s))

def _lighten_color(hexcol: str, factor: float = 0.15) -> str:
    """Lighten hexcol by factor (0..1) toward white. Safe fallback if invalid."""
    try:
        r, g, b = _hex_to_rgb(hexcol or "#ffffff")
        nr = int(r + (255 - r) * factor)
        ng = int(g + (255 - g) * factor)
        nb = int(b + (255 - b) * factor)
        return _rgb_to_hex(nr, ng, nb)
    except Exception:
        return hexcol or "#ffffff"

def _contrast_text_color(hexcolor: str) -> str:
    """Return black or white depending on perceived luminance for good contrast."""
    try:
        if not hexcolor:
            return '#000000'
        s = hexcolor.strip()
        if s.startswith('#'):
            s = s[1:]
        if len(s) == 3:
            s = ''.join(ch*2 for ch in s)
        if len(s) != 6:
            return '#000000'
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
        lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
        return '#000000' if lum > 0.56 else '#FFFFFF'
    except Exception:
        return '#000000'

def wrap_segment_by_tags(seg_text: str, active_tags: set):
    """Wrap a text segment according to active tag set into Markdown/HTML."""
    has_bold = any(t in active_tags for t in ('bold', 'bolditalic', 'boldunderline', 'all'))
    has_italic = any(t in active_tags for t in ('italic', 'bolditalic', 'underlineitalic', 'all'))
    has_underline = any(t in active_tags for t in ('underline', 'boldunderline', 'underlineitalic', 'all'))
    has_small = 'small' in active_tags
    inner = seg_text
    if has_bold and has_italic:
        inner = f"***{inner}***"
    elif has_bold:
        inner = f"**{inner}**"
    elif has_italic:
        inner = f"*{inner}*"

    if has_underline:
        inner = f"<u>{inner}</u>"

    if has_small:
        inner = f"<small>{inner}</small>"
    return inner

def _compute_complementary(hexcol: str, fallback: str = "#F8F8F8") -> str:
    try:
        if not hexcol:
            return fallback
        s = hexcol.strip()
        if s.startswith('#'):
            s = s[1:]
        if len(s) == 3:
            s = ''.join(ch*2 for ch in s)
        if len(s) != 6:
            return fallback
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
        cr = 255 - r
        cg = 255 - g
        cb = 255 - b
        try:
            bg = (backgroundColor or "").strip()
            if bg and bg.startswith('#'):
                bgc = bg[1:]
                if len(bgc) == 3:
                    bgc = ''.join(ch*2 for ch in bgc)
                if len(bgc) == 6:
                    br = int(bgc[0:2], 16)
                    bg_ = int(bgc[2:4], 16)
                    bb = int(bgc[4:6], 16)
                    if (cr, cg, cb) == (br, bg_, bb):
                        cr = max(0, min(255, cr - 16))
                        cg = max(0, min(255, cg - 8))
                        cb = max(0, min(255, cb - 4))
        except Exception:
            pass
        return f"#{cr:02x}{cg:02x}{cb:02x}"
    except Exception:
        return fallback

def _strip_whitespace_between_tags(html: str) -> str:
    """
    Return a copy of `html` with inter-tag layout whitespace removed (">   <" -> "><"),
    while preserving content inside sensitive tags (script/style/pre/code).

    Also normalizes anchor inner text and avoids merging adjacent anchors by inserting
    a single separator space when necessary (prevents adjacent anchors from collapsing).
    """
    try:
        if not isinstance(html, str) or html == '':
            return html

        # Preserve sensitive blocks by replacing them with placeholders
        placeholder_fmt = "__HTML_PRESERVE_%d__"
        preserved = []

        def _preserve_match(m):
            idx = len(preserved)
            preserved.append(m.group(0))
            return placeholder_fmt % idx

        # find script/style/pre/code blocks (case-insensitive, DOTALL)
        block_re = re.compile(r'(?is)<(script|style|pre|code)(?:\s[^>]*)?>.*?</\1\s*>')
        working = block_re.sub(_preserve_match, html)

        # Remove whitespace between tags: any ">" then whitespace then "<" -> "><"
        # This collapses pretty-printing indentation/newlines used for layout.
        working = re.sub(r'>\s+<', '><', working)

        # Trim excessive leading/trailing whitespace around document edges
        working = re.sub(r'^\s+<', '<', working)
        working = re.sub(r'>\s+$', '>', working)

        # --- Normalize anchor inner HTML ---
        # Trim/collapse whitespace inside anchors but preserve inline tags.
        try:
            anchor_re = re.compile(r'(?is)<a\b([^>]*)>(.*?)</a\s*>')

            def _trim_anchor_inner(m):
                inner = m.group(2) or ''
                if inner.strip() == '':
                    new_inner = ''
                else:
                    parts = re.split(r'(<[^>]+>)', inner)
                    for i, p in enumerate(parts):
                        if not p:
                            continue
                        if p.startswith('<'):
                            continue
                        # collapse whitespace in text fragments
                        parts[i] = re.sub(r'\s+', ' ', p)
                        # remove spaces that were accidentally placed around percent-encoded tokens like %20
                        try:
                            parts[i] = re.sub(r'\s*(%[0-9A-Fa-f]{2})\s*', r'\1', parts[i])
                        except Exception:
                            pass
                    new_inner = ''.join(parts).strip()
                return f"<a{m.group(1)}>{new_inner}</a>"

            working = anchor_re.sub(_trim_anchor_inner, working)
        except Exception:
            pass

        # Ensure adjacent anchors remain visually separated but avoid inserting excessive spaces.
        try:
            # Insert a single space between adjacent anchors if they were collapsed to `</a><a...`
            working = re.sub(r'</\s*a\s*>\s*<\s*a\b', '</a> <a', working, flags=re.I)
        except Exception:
            pass

        # Restore preserved blocks
        if preserved:
            for i, original in enumerate(preserved):
                working = working.replace(placeholder_fmt % i, original)

        return working
    except Exception:
        return html
def _parse_html_and_apply(raw) -> tuple[str, dict]:
    """
    Parse raw HTML fragment or document and extract plain text and tag ranges.
    Pre-process the HTML by removing whitespace between tags (while preserving
    script/style/pre/code contents). Returns (plain_text, meta) where meta
    contains at least 'tags' and includes 'prochtml' (the processed HTML).

    Post-process anchors from `prochtml` to robustly map multiple anchors per
    line into distinct hyperlink ranges in the produced `plain` text. This
    avoids adjacent-anchor merging issues from earlier passes.
    """
    try:
        m = re.search(r'<body[^>]*>(.*)</body>', raw, flags=re.DOTALL | re.IGNORECASE)
        fragment = m.group(1) if m else raw

        # Keep original fragment (so callers can store the raw buffer separately)
        raw_fragment = fragment

        # Produce prochtml: fragment with whitespace removed between tags (but preserving code/style/script/pre)
        try:
            prochtml = _strip_whitespace_between_tags(raw_fragment)
        except Exception:
            prochtml = raw_fragment

        parser = _SimpleHTMLToTagged()
        # Feed the processed HTML to the parser (this is the key change)
        parser.feed(prochtml)
        plain, meta = parser.get_result()

        # Attach both raw and processed HTML to meta so caller/UI can keep raw and re-process later
        try:
            if not isinstance(meta, dict):
                meta = dict(meta or {})
            meta['raw_fragment'] = raw_fragment
            meta['prochtml'] = prochtml
        except Exception:
            pass

        # --- NEW: Robust anchor remapping based on prochtml -> plain
        # This guarantees each <a ...>...</a> in the processed HTML yields a
        # separate entry in meta['links'] and a corresponding non-overlapping
        # 'hyperlink' range in meta['tags'] even when anchors sit adjacent.
        try:
            # Helper: extract anchors from prochtml (preserving order)
            anchors = []
            for m_a in re.finditer(r'(?is)<a\b([^>]*)>(.*?)</a\s*>', prochtml):
                try:
                    attrstr = m_a.group(1) or ''
                    inner_html = m_a.group(2) or ''
                    # find href and title (best-effort)
                    href = None
                    title = None
                    ah = re.search(r'href\s*=\s*(?:"([^"]+)"|\'([^\']+)\'|([^\s>]+))', attrstr, flags=re.I)
                    if ah:
                        href = ah.group(1) or ah.group(2) or ah.group(3)
                    th = re.search(r'title\s*=\s*(?:"([^"]+)"|\'([^\']+)\'|([^\s>]+))', attrstr, flags=re.I)
                    if th:
                        title = th.group(1) or th.group(2) or th.group(3)
                    # strip inner tags to get visible text
                    visible = re.sub(r'<[^>]+>', '', inner_html)
                    visible = html.unescape(visible or '')
                    visible_norm = re.sub(r'\s+', ' ', visible).strip()
                    anchors.append({'href': href, 'title': title, 'visible': visible, 'visible_norm': visible_norm})
                except Exception:
                    continue

            if anchors:
                new_links = []
                new_hyper_ranges = []
                # Walk anchors sequentially and locate their visible text in `plain`.
                # Use a moving search start so repeated identical link texts map in order.
                search_pos = 0
                plain_for_search = plain or ''
                for a in anchors:
                    vn = a.get('visible_norm', '') or ''
                    if not vn:
                        # If no visible text (e.g. image-only link) try to locate small token or skip
                        # fallback: attempt to find an empty boundary near search_pos
                        # skip mapping if we can't reasonably locate text
                        continue
                    # Build a flexible regex from normalized visible text: allow arbitrary whitespace in source
                    esc = re.escape(vn)
                    esc = esc.replace(r'\ ', r'\s+')
                    rx = re.compile(esc)
                    m_found = rx.search(plain_for_search, search_pos)
                    if not m_found:
                        # try a looser exact substring search (fallback)
                        idx = plain_for_search.find(vn, search_pos)
                        if idx >= 0:
                            s_idx = idx
                            e_idx = idx + len(vn)
                        else:
                            # as a last resort, try from beginning
                            m_found = rx.search(plain_for_search)
                            if m_found:
                                s_idx, e_idx = m_found.span()
                            else:
                                continue
                    else:
                        s_idx, e_idx = m_found.span()

                    # Accept and record
                    try:
                        link_rec = {'start': int(s_idx), 'end': int(e_idx), 'href': a.get('href'), 'title': a.get('title') or None}
                        new_links.append(link_rec)
                        new_hyper_ranges.append([int(s_idx), int(e_idx)])
                        search_pos = e_idx
                    except Exception:
                        continue

                # Merge with any pre-existing non-anchor links (e.g., markdown-links) safely:
                existing_meta_links = list(meta.get('links') or [])
                # prefer mapped anchors first (they correspond to literal <a> elements)
                combined_links = new_links + [l for l in existing_meta_links if not any((l.get('start') == nl.get('start') and l.get('end') == nl.get('end')) for nl in new_links)]
                # update meta and parser structures
                meta['links'] = combined_links
                tags = meta.get('tags') or {}
                # replace/merge hyperlink tag ranges
                if new_hyper_ranges:
                    tags['hyperlink'] = new_hyper_ranges
                    meta['tags'] = tags
        except Exception:
            # best-effort: if mapping fails, keep parser's original hrefs
            pass

        return plain, meta
    except Exception:
        return raw, {'tags': {}}

def _ensure_url_section(cfg):
    """Ensure the 'URLHistory' section exists."""
    if not cfg.has_section("URLHistory"):
        cfg.add_section("URLHistory")

def load_url_history(cfg) -> List[str]:
    """Load URL history list (most-recent-first) from config JSON."""
    _ensure_url_section(cfg)
    try:
        raw = cfg.get("URLHistory", "urls", fallback="[]")
        return json.loads(raw)
    except Exception:
        return []

def save_url_history(cfg, ini_path: str, lst: Iterable[str]) -> None:
    """Persist URL history (iterable) into config under URLHistory/urls as JSON string."""
    _ensure_url_section(cfg)
    try:
        cfg.set("URLHistory", "urls", json.dumps(list(lst)))
        with open(ini_path, "w", encoding="utf-8") as fh:
            cfg.write(fh)
    except Exception:
        pass

def add_url_history(cfg, ini_path: str, url: str, max_items: int = 50) -> None:
    """Add `url` to history (front), dedupe and truncate to `max_items`."""
    try:
        if not url:
            return
        lst = load_url_history(cfg)
        u = str(url)
        if u in lst:
            lst.remove(u)
        lst.insert(0, u)
        lst = lst[:max_items]
        save_url_history(cfg, ini_path, lst)
    except Exception:
        pass

def clear_url_history(cfg, ini_path: str, on_update: Optional[Callable[[], None]] = None) -> None:
    """Clear persisted URL history and optionally call on_update."""
    save_url_history(cfg, ini_path, [])
    if on_update:
        try:
            on_update()
        except Exception:
            pass

def _serialize_tags(tags_dict):
    """Return header string (commented base64 JSON) for provided tags dict, or '' if empty."""
    try:
        if not tags_dict:
            return ''
        meta = {'version': 1, 'tags': tags_dict}
        b64 = base64.b64encode(json.dumps(meta).encode('utf-8')).decode('ascii')
        return "# ---SIMPLEEDIT-META-BEGIN---\n# " + b64 + "\n# ---SIMPLEEDIT-META-END---\n\n"
    except Exception:
        return ''

def get_result(self):
    try:
        full = ''.join(self.out)
        table_ranges = list(self.ranges.get('table', [])) if isinstance(self.ranges.get('table', []), list) else []
        if table_ranges:
            table_ranges = sorted(table_ranges, key=lambda r: r[0])
            offset_shift = 0
            for t in ('table', 'tr', 'td', 'th'):
                if t in self.ranges:
                    self.ranges.pop(t, None)

            for orig_start, orig_end in table_ranges:
                try:
                    start = orig_start + offset_shift
                    end = orig_end + offset_shift
                    if start < 0 or end <= start or start >= len(full):
                        continue
                    end = min(end, len(full))
                    seg = full[start:end]
                    rows = seg.split('\n')
                    cells_by_row = [r.split('\t') if r != '' else [''] for r in rows]

                    if not cells_by_row:
                        continue

                    max_cols = max(len(row) for row in cells_by_row)
                    col_widths = [0] * max_cols
                    for row in cells_by_row:
                        for ci, cell in enumerate(row):
                            col_widths[ci] = max(col_widths[ci], len(cell))

                    new_rows = []
                    for row in cells_by_row:
                        padded_cells = []
                        for ci in range(max_cols):
                            text = row[ci] if ci < len(row) else ''
                            padded = text.ljust(col_widths[ci])
                            padded_cells.append(padded)
                        new_rows.append('\t'.join(padded_cells))
                    new_seg = '\n'.join(new_rows)

                    full = full[:start] + new_seg + full[end:]
                    delta = len(new_seg) - (end - start)
                    offset_shift += delta

                    table_start = start
                    table_end = start + len(new_seg)
                    self.ranges.setdefault('table', []).append([table_start, table_end])

                    cursor = table_start
                    for ridx, rtext in enumerate(new_rows):
                        row_start = cursor
                        cell_cursor = row_start
                        cells = rtext.split('\t')
                        for cidx, cell_text in enumerate(cells):
                            cs = cell_cursor
                            ce = cs + len(cell_text)
                            is_header = False
                            if ridx == 0:
                                is_header = False
                            if is_header:
                                self.ranges.setdefault('th', []).append([cs, ce])
                            else:
                                self.ranges.setdefault('td', []).append([cs, ce])
                            cell_cursor = ce + 1
                        row_end = cursor + len(rtext)
                        self.ranges.setdefault('tr', []).append([row_start, row_end])
                        cursor = row_end + 1
                except Exception:
                    continue

            self.out = [full]
            self.pos = len(full)

        meta = {'tags': self.ranges}
        if self.hrefs:
            meta['links'] = list(self.hrefs)
        return full, meta
    except Exception:
        try:
            return ''.join(self.out), {'tags': self.ranges, 'links': list(self.hrefs)}
        except Exception:
            return ''.join(self.out), {'tags': self.ranges}

def _parse_simple_markdown(md_text):
    """
    Very small markdown parser to extract bold/italic/underline markers and return plain text
    plus a tags dict compatible with _apply_formatting_from_meta (i.e. {tag: [[start,end], ...]}).
    Supports: ***bolditalic***, **bold**, *italic*, and <u>underline</u>.
    """
    tags = {'bold': [], 'italic': [], 'underline': [], 'bolditalic': []}
    plain_parts = []
    last = 0
    out_index = 0

    pattern = re.compile(r'\*\*\*([^\*]+?)\*\*\*|\*\*([^\*]+?)\*\*|\*([^\*]+?)\*|<u>(.*?)</u>', re.DOTALL)
    for m in pattern.finditer(md_text):
        start, end = m.span()
        seg = md_text[last:start]
        plain_parts.append(seg)
        out_index += len(seg)
        content = None
        tag_name = None
        if m.group(1) is not None:
            content = m.group(1)
            tag_name = 'bolditalic'
        elif m.group(2) is not None:
            content = m.group(2)
            tag_name = 'bold'
        elif m.group(3) is not None:
            content = m.group(3)
            tag_name = 'italic'
        elif m.group(4) is not None:
            content = m.group(4)
            tag_name = 'underline'
        else:
            content = md_text[start:end]
            tag_name = None

        if content is None:
            content = ''
        plain_parts.append(content)
        if tag_name:
            tags.setdefault(tag_name, []).append([out_index, out_index + len(content)])
        out_index += len(content)
        last = end

    tail = md_text[last:]
    plain_parts.append(tail)
    plain_text = ''.join(plain_parts)
    tags = {k: v for k, v in tags.items() if v}
    return plain_text, tags

def _collect_all_tag_ranges(textArea):
    """Collect ranges for both formatting and syntax tags as absolute offsets."""
    tags_to_save = (
        'bold', 'italic', 'underline', 'all',
        'underlineitalic', 'boldunderline', 'bolditalic',
        'small',
        'string', 'keyword', 'comment', 'selfs', 'def', 'number', 'variable',
        'decorator', 'class_name', 'constant', 'attribute', 'builtin', 'todo'
    )
    data = {}
    try:
        for tag in tags_to_save:
            ranges = textArea.tag_ranges(tag)
            if not ranges:
                continue
            arr = []
            for i in range(0, len(ranges), 2):
                s = ranges[i]
                e = ranges[i + 1]
                start = len(textArea.get('1.0', s))
                end = len(textArea.get('1.0', e))
                if end > start:
                    arr.append([start, end])
            if arr:
                data[tag] = arr
    except Exception:
        pass
    return data

def _convert_buffer_to_html_fragment(textArea):
    """
    Produce HTML fragment. Special-case: reconstruct real <table>...</table> elements,
    wrap code blocks into <pre>, and turn marked div/p ranges into actual HTML blocks.
    """
    try:
        content = textArea.get('1.0', 'end-1c')
        if not content:
            return ''

        tags_by_name = _collect_all_tag_ranges(textArea)

        # If we have structural ranges (table | code_block | div_* | p), we slice and rebuild HTML blocks.
        structural_present = any(
            k in tags_by_name for k in (
                'table',
                'div', 'div_nav', 'div_content', 'p',
                'h1','h2','h3','h4','h5','h6','hr','blockquote'
            )
        )
        if structural_present:
            # Build a combined list of segments to render specially
            special_keys = []
            for k in ('table','div_nav','div_content','div','p',
                      'h1','h2','h3','h4','h5','h6','hr','blockquote'):

                if k in tags_by_name:
                    for s, e in tags_by_name[k]:
                        special_keys.append((s, e, k))
            # Sort by start
            special_keys.sort(key=lambda x: x[0])

            out_parts = []
            last = 0
            for s, e, kind in special_keys:
                # Append escaped text before special block
                if last < s:
                    out_parts.append(html.escape(content[last:s]))

                block_text = content[s:e]

                if kind == 'table':
                    # Prefer to build table from parser/table-editor metadata when available.
                    # We still fall back to legacy split-based reconstruction when no meta exists.
                    # Try to find matching meta for this table span (best-effort by overlap / proximity).
                    table_meta_for_span = None
                    try:
                        tmetas = getattr(textArea, '_tables_meta', []) or []
                        s_int = int(s)
                        e_int = int(e)
                        best = None
                        best_dist = None
                        for tm in tmetas:
                            try:
                                ts = int(tm.get('start', -1))
                                te = int(tm.get('end', -1))
                            except Exception:
                                continue
                            if (ts <= s_int < te) or (s_int <= ts < e_int) or (ts < e_int and te > s_int):
                                table_meta_for_span = tm
                                best = None
                                break
                            dist = abs(ts - s_int)
                            if best is None or dist < best_dist:
                                best = tm
                                best_dist = dist
                        if table_meta_for_span is None and best is not None and best_dist is not None and best_dist <= 32:
                            table_meta_for_span = best
                    except Exception:
                        table_meta_for_span = None

                    # Emit <table> using precise metadata when available
                    out_parts.append('<table>')
                    try:
                        if table_meta_for_span:
                            # prefer explicit colgroup if present
                            cg = table_meta_for_span.get('colgroup', []) or []
                            if cg:
                                cols = []
                                for c in cg:
                                    w = c.get('width')
                                    if w:
                                        try:
                                            wi = int(w)
                                            cols.append(f'<col style="width:{wi}ch">')
                                        except Exception:
                                            cols.append(f'<col style="width:{html.escape(str(w))}">')
                                    else:
                                        cols.append('<col>')
                                if cols:
                                    out_parts.append('<colgroup>' + ''.join(cols) + '</colgroup>')

                            for row_cells in table_meta_for_span.get('rows', []):
                                out_parts.append('<tr>')
                                for cell in row_cells:
                                    # cell text may contain internal IN_CELL_NL markers -> render as <br>
                                    raw_txt = (cell.get('text') or '') or ''
                                    # convert internal marker to HTML line breaks prior to escaping replacement
                                    raw_txt = raw_txt.replace(IN_CELL_NL, '\n')
                                    esc = html.escape(raw_txt).replace('\n', '<br>')
                                    attrs = cell.get('attrs', {}) or {}
                                    typ = cell.get('type', 'td')
                                    attr_str = ''
                                    if 'colspan' in attrs and str(attrs.get('colspan')).strip():
                                        try:
                                            attr_str += f' colspan="{int(attrs.get("colspan"))}"'
                                        except Exception:
                                            attr_str += f' colspan="{html.escape(str(attrs.get("colspan")))}"'
                                    if 'rowspan' in attrs and str(attrs.get('rowspan')).strip():
                                        try:
                                            attr_str += f' rowspan="{int(attrs.get("rowspan"))}"'
                                        except Exception:
                                            attr_str += f' rowspan="{html.escape(str(attrs.get("rowspan")))}"'
                                    align = attrs.get('align') or ''
                                    if not align:
                                        style = (attrs.get('style') or '')
                                        m = re.search(r'text-align\s*:\s*(left|right|center|justify)', style, flags=re.I) if style else None
                                        if m:
                                            align = m.group(1)
                                    if align:
                                        attr_str += f' align="{html.escape(str(align))}"'
                                    if typ == 'th':
                                        out_parts.append(f'<th{attr_str}>{esc}</th>')
                                    else:
                                        out_parts.append(f'<td{attr_str}>{esc}</td>')
                                out_parts.append('</tr>')
                        else:
                            # legacy fallback: split rows/tabs
                            rows = block_text.split('\n')
                            for ridx, row in enumerate(rows):
                                if row == '' and len(rows) == 1:
                                    continue
                                out_parts.append('<tr>')
                                cells = row.split('\t')
                                is_header_table = bool('th' in tags_by_name and tags_by_name['th'])
                                for cell_text in cells:
                                    cell_text_escaped = html.escape(cell_text.replace(IN_CELL_NL, '\n')).replace('\n', '<br>')
                                    if is_header_table and ridx == 0:
                                        out_parts.append(f'<th>{cell_text_escaped}</th>')
                                    else:
                                        out_parts.append(f'<td>{cell_text_escaped}</td>')
                                out_parts.append('</tr>')
                    except Exception:
                        # strong fallback: basic escaped table content
                        rows = block_text.split('\n')
                        for row in rows:
                            out_parts.append('<tr>')
                            for cell_text in (row.split('\t') if row != '' else ['']):
                                out_parts.append('<td>' + html.escape(cell_text) + '</td>')
                            out_parts.append('</tr>')
                    out_parts.append('</table>')

                elif kind == 'code_block':
                    # Wrap exact slice in <pre> to allow CSS styling
                    # Preserve content; it's already "raw" text, so escape for HTML.
                    out_parts.append('<pre>')
                    out_parts.append(html.escape(block_text))
                    out_parts.append('</pre>')

                elif kind == 'div_nav':
                    out_parts.append('<div class="nav">')
                    out_parts.append(html.escape(block_text))
                    out_parts.append('</div>')

                elif kind == 'div_content':
                    out_parts.append('<div class="content">')
                    out_parts.append(html.escape(block_text))
                    out_parts.append('</div>')

                elif kind == 'div':
                    out_parts.append('<div>')
                    out_parts.append(html.escape(block_text))
                    out_parts.append('</div>')

                elif kind == 'p':
                    out_parts.append('<p>')
                    out_parts.append(html.escape(block_text))
                    out_parts.append('</p>')

                elif kind in ('h1','h2','h3','h4','h5','h6'):
                    out_parts.append(f'<{kind}>')
                    out_parts.append(html.escape(block_text))
                    out_parts.append(f'</{kind}>')

                elif kind == 'hr':
                    out_parts.append('<hr />')

                elif kind == 'blockquote':
                    out_parts.append('<blockquote>')
                    out_parts.append(html.escape(block_text))
                    out_parts.append('</blockquote>')

                last = e

            # Append escaped remainder
            if last < len(content):
                out_parts.append(html.escape(content[last:]))

            return ''.join(out_parts)

        # Fallback: original inline-span rendering path
        events = []
        for tag, ranges in tags_by_name.items():
            for s, e in ranges:
                events.append((s, 'start', tag))
                events.append((e, 'end', tag))
        if not events:
            return html.escape(content)

        events_by_pos = {}
        for pos, kind, tag in events:
            events_by_pos.setdefault(pos, []).append((kind, tag))
        positions = sorted(set(list(events_by_pos.keys()) + [0, len(content)]))
        for pos in events_by_pos:
            events_by_pos[pos].sort(key=lambda x: 0 if x[0] == 'end' else 1)

        out_parts = []
        active = []
        for i in range(len(positions) - 1):
            pos = positions[i]
            for kind, tag in events_by_pos.get(pos, []):
                if kind == 'end':
                    for j in range(len(active) - 1, -1, -1):
                        if active[j] == tag:
                            for k in range(len(active) - 1, j - 1, -1):
                                t = active.pop()
                                if t in ('bold', 'italic', 'underline'):
                                    if t == 'bold':
                                        out_parts.append('</strong>')
                                    elif t == 'italic':
                                        out_parts.append('</em>')
                                    elif t == 'underline':
                                        out_parts.append('</u>')
                                else:
                                    out_parts.append('</span>')
                            break
                elif kind == 'start':
                    if tag in ('bold', 'italic', 'underline'):
                        if exportCssMode in ('inline-block', 'external'):
                            if tag == 'bold':
                                out_parts.append('<strong class="se-bold">')
                            elif tag == 'italic':
                                out_parts.append('<em class="se-italic">')
                            elif tag == 'underline':
                                out_parts.append('<u class="se-underline">')
                        else:
                            if tag == 'bold':
                                out_parts.append('<strong>')
                            elif tag == 'italic':
                                out_parts.append('<em>')
                            elif tag == 'underline':
                                out_parts.append('<u>')
                        active.append(tag)
                    else:
                        if exportCssMode in ('inline-block', 'external'):
                            out_parts.append(f'<span class="se-{tag}">')
                        else:
                            if tag == 'todo':
                                out_parts.append(f'<span style="color:#ffffff;background-color:#B22222">')
                            else:
                                color = _TAG_COLOR_MAP.get(tag)
                                if color:
                                    out_parts.append(f'<span style="color:{color}">')
                                else:
                                    out_parts.append('<span>')
                        active.append(tag)

            next_pos = positions[i + 1]
            if next_pos <= pos:
                continue
            seg = content[pos:next_pos]
            out_parts.append(html.escape(seg))

        while active:
            t = active.pop()
            if t in ('bold', 'italic', 'underline'):
                if t == 'bold':
                    out_parts.append('</strong>')
                elif t == 'italic':
                    out_parts.append('</em>')
                elif t == 'underline':
                    out_parts.append('</u>')
            else:
                out_parts.append('</span>')

        return ''.join(out_parts)
    except Exception:
        try:
            return html.escape(textArea.get('1.0', 'end-1c'))
        except Exception:
            return ''

def _generate_css():
    """Return CSS text used for inline-block or external export modes."""
    try:
        parts = []
        parts.append(".simpleedit-export{")
        parts.append(f"background: {backgroundColor};")
        parts.append(f"color: {fontColor};")
        parts.append(f"font-family: {fontName}, monospace;")
        parts.append("white-space: pre-wrap;")
        parts.append("padding: 8px;")
        parts.append("}")
        # Syntax color classes for span-based tags
        for tag, color in _TAG_COLOR_MAP.items():
            cls = f".se-{tag}"
            if tag == 'todo':
                parts.append(f"{cls}{{ color:#ffffff; background:#B22222; padding:2px 6px; border-radius:3px; }}")
            else:
                parts.append(f"{cls}{{ color: {color}; }}")
        # Formatting classes
        parts.append(".se-bold{ font-weight: bold; }")
        parts.append(".se-italic{ font-style: italic; }")
        parts.append(".se-underline{ text-decoration: underline; }")
        parts.append(".se-small{ font-size: 0.85em; }")
        # Template/layout styles (to render provided template elements)
        parts.append("body{ background:#ffffff; color:#111; font-family:Segoe UI, Roboto, Arial, sans-serif; padding:16px; }")
        parts.append(".nav{ background:#f3f4f6; padding:8px; border-radius:4px; }")
        parts.append(".content{ margin-top:12px; }")
        parts.append("pre{ background:#f5f5f5; padding:8px; border-radius:4px; overflow:auto; }")
        parts.append("table{ border-collapse:collapse; margin-top:8px; }")
        parts.append("th,td{ border:1px solid #ccc; padding:8px; }")
        parts.append(".todo{ color:#fff; background:#B22222; padding:2px 6px; border-radius:3px; }")
        # Extra styles for newly supported elements
        parts.append("blockquote{ border-left:4px solid #ddd; margin:8px 0; padding:4px 8px; }")
        parts.append("h1{ font-size:1.6em; margin:0.8em 0 0.4em; }")
        parts.append("h2{ font-size:1.4em; margin:0.7em 0 0.35em; }")
        parts.append("h3{ font-size:1.2em; margin:0.6em 0 0.3em; }")
        parts.append("hr{ border:none; border-top:1px solid #ddd; margin:12px 0; }")
        parts.append("mark{ background:#fff59d; }")
        parts.append("kbd{ font-family:Consolas, monospace; background:#eee; border:1px solid #ccc; border-radius:3px; padding:1px 4px; }")
        
        return "\n".join(parts)
    except Exception:
        return ""

_TAG_COLOR_MAP = {
    'number': '#FDFD6A',
    'selfs': '#FFFF00',
    'variable': '#8A2BE2',
    'decorator': '#66CDAA',
    'class_name': '#FFB86B',
    'constant': '#FF79C6',
    'attribute': '#33CCFF',
    'builtin': '#9CDCFE',
    'def': '#FFA500',
    'keyword': '#FF0000',
    'string': '#C9CA6B',
    'operator': '#AAAAAA',
    'comment': '#75715E',
    'todo': '#FFFFFF',
}
_COLOR_TO_TAG = {v.lower(): k for k, v in _TAG_COLOR_MAP.items()}

def save_as_markdown(textArea):
    """
    Save as .md or .html honoring exportCssMode:
      - inline-element: current per-element inline `style="color:..."`
      - inline-block: prepend <style>...</style> (generated by _generate_css) into .md or embed in <head> for .html
      - external: write a .css file next to saved file (or to exportCssPath) and include <link> (for .html)
    """
    fileName = filedialog.asksaveasfilename(
        initialdir=os.path.expanduser("~"),
        title="Save as Markdown (.md) or HTML (.html) (preserves visible highlighting)",
        defaultextension='.md',
        filetypes=(
            ("Markdown files", "*.md"),
            ("HTML files", "*.html"),
            ("Text files", "*.txt"),
            ("All files", "*.*"),
        )
    )
    if not fileName:
        return

    try:
        fragment = _convert_buffer_to_html_fragment(textArea)

        wrapper_attrs = []
        if exportCssMode == 'inline-element':
            wrapper_style = (
                f"background:{backgroundColor};"
                f"color:{fontColor};"
                f"font-family:{fontName},monospace;"
                "white-space:pre-wrap;"
                "padding:8px;"
            )
            wrapped_fragment = f'<div style="{wrapper_style}">{fragment}</div>'
        else:
            wrapped_fragment = f'<div class="simpleedit-export">{fragment}</div>'

        if fileName.lower().endswith('.html'):
            if exportCssMode == 'external':
                css_path = exportCssPath or os.path.splitext(fileName)[0] + '.css'
                try:
                    with open(css_path, 'w', encoding='utf-8') as cssf:
                        cssf.write(_generate_css())
                except Exception:
                    pass
                href = os.path.relpath(css_path, os.path.dirname(fileName))
                head_includes = f'<link rel="stylesheet" href="{href}">'
            elif exportCssMode == 'inline-block':
                css_text = _generate_css()
                head_includes = f'<style>\n{css_text}\n</style>'
            else:
                head_includes = ''

            html_doc = (
                '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
                '<title>SimpleEdit Export</title>\n'
                f'{head_includes}\n'
                '</head>\n<body>\n{body}\n</body>\n</html>\n'
            ).format(body=wrapped_fragment)
            with open(fileName, 'w', errors='replace', encoding='utf-8') as f:
                f.write(html_doc)

        else:
            if exportCssMode == 'external':
                css_path = exportCssPath or os.path.splitext(fileName)[0] + '.css'
                try:
                    with open(css_path, 'w', encoding='utf-8') as cssf:
                        cssf.write(_generate_css())
                except Exception:
                    pass
                md_prefix = f'<link rel="stylesheet" href="{os.path.basename(css_path)}">\n\n'
                md_body = md_prefix + wrapped_fragment
            elif exportCssMode == 'inline-block':
                css_text = _generate_css()
                md_prefix = f'<style>\n{css_text}\n</style>\n\n'
                md_body = md_prefix + wrapped_fragment
            else:
                md_body = wrapped_fragment

            with open(fileName, 'w', errors='replace', encoding='utf-8') as f:
                f.write(md_body)
            return fileName

    except Exception as e:
        messagebox.showerror("Error", str(e))