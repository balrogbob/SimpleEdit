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
import shutil, sys, os
import textwrap

RECENT_MAX = 10

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
        'exportCssPath': ''                # used when 'external' chosen; default generated at save time
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
                elif tag in ('td', 'th'):
                    prev_text = ''.join(self.out) if self.out else ''
                    if prev_text and not prev_text.endswith('\n'):
                        self.out.append('\t'); self.pos += 1
                    # record cell start and attrs so we can preserve rowspan/colspan/align on export
                    attrd = dict(attrs or {})
                    try:
                        self._cell_meta.append({'start': self.pos, 'end': None, 'attrs': attrd, 'type': tag})
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
                # record table start attrs for later reconstruction
                if tag == 'table':
                    try:
                        self._table_attr_stack.append(dict(attrd))
                    except Exception:
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
        try:
            full = ''.join(self.out)
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

            # Build meta and perform a final soft top-of-document whitespace collapse.
            # This keeps the first rendered content at the top (or one line down),
            # without touching code/pre or internal spacing elsewhere.
            meta = {'tags': self.ranges}
            if self.hrefs:
                meta['links'] = list(self.hrefs)
            # Build rich table metadata (rows, cells with attrs) using recorded _table_meta and _cell_meta.
            try:
                tables = []
                for t in self._table_meta:
                    try:
                        tstart = int(t.get('start', 0))
                        tend = int(t.get('end', 0))
                        if tstart < 0 or tend <= tstart or tstart >= len(full):
                            continue
                        tend = min(tend, len(full))
                        seg = full[tstart:tend]
                        rows = seg.split('\n')
                        # build cell offsets by scanning rows/cells and map to nearest recorded cell meta (by overlap)
                        abs_cursor = tstart
                        table_rows = []
                        for rtext in rows:
                            cells = rtext.split('\t') if rtext != '' else ['']
                            row_cells = []
                            cell_cursor = abs_cursor
                            for cell_text in cells:
                                cs = cell_cursor
                                ce = cs + len(cell_text)
                                # find matching recorded cell meta overlapping this region
                                matched = None
                                for cm in t.get('cells', []):
                                    # simple overlap test
                                    if not (cm.get('end') <= cs or cm.get('start') >= ce):
                                        matched = cm
                                        break
                                cell_entry = {
                                    'start': cs,
                                    'end': ce,
                                    'text': cell_text,
                                    'attrs': dict(matched.get('attrs', {})) if matched else {},
                                    'type': (matched.get('type') if matched else 'td')
                                }
                                row_cells.append(cell_entry)
                                # advance by cell length plus one for tab (except last)
                                cell_cursor = ce + 1
                            table_rows.append(row_cells)
                            abs_cursor += len(rtext) + 1
                        table_entry = {'start': tstart, 'end': tend, 'attrs': t.get('attrs', {}), 'rows': table_rows, 'colgroup': t.get('colgroup', [])}
                        tables.append(table_entry)
                    except Exception:
                        continue
                if tables:
                    meta['tables'] = tables
            except Exception:
                pass
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

def _parse_html_and_apply(raw) -> tuple[str, dict]:
    """
    Parse raw HTML fragment or document and extract plain text and tag ranges.
    Returns (plain_text, meta) where meta is {'tags': {...}, 'links': [...]}
    """
    try:
        m = re.search(r'<body[^>]*>(.*)</body>', raw, flags=re.DOTALL | re.IGNORECASE)
        fragment = m.group(1) if m else raw

        parser = _SimpleHTMLToTagged()
        parser.feed(fragment)
        plain, meta = parser.get_result()
        return plain, meta
    except Exception:
        return raw, {}

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
                    rows = [r for r in block_text.split('\n') if r is not None]
                    # Try to enrich rendering using stored table metadata (if present)
                    table_meta_for_span = None
                    try:
                        tmetas = getattr(textArea, '_tables_meta', []) or []
                        # best-effort: match by start offset
                        for tm in tmetas:
                            try:
                                if int(tm.get('start', -1)) == int(s):
                                    table_meta_for_span = tm
                                    break
                            except Exception:
                                continue
                    except Exception:
                        table_meta_for_span = None

                    # If we can, emit a colgroup (either explicit from metadata or computed widths)
                    colgroup_html = ''
                    if table_meta_for_span:
                        try:
                            # if explicit colgroup present in metadata, prefer it
                            cg = table_meta_for_span.get('colgroup', []) or []
                            if cg:
                                cols = []
                                for c in cg:
                                    w = c.get('width')
                                    if w:
                                        # allow numeric widths or strings; if numeric assume characters -> use ch
                                        try:
                                            wi = int(w)
                                            cols.append(f'<col style="width:{wi}ch">')
                                        except Exception:
                                            cols.append(f'<col style="width:{html.escape(str(w))}">')
                                    else:
                                        cols.append('<col>')
                                if cols:
                                    colgroup_html = '<colgroup>' + ''.join(cols) + '</colgroup>'
                            else:
                                # compute widths from metadata rows (character counts)
                                rows_meta = table_meta_for_span.get('rows', []) or []
                                if rows_meta:
                                    max_cols = max((len(r) for r in rows_meta), default=0)
                                    col_widths = [0] * max_cols
                                    for r in rows_meta:
                                        for ci, cell in enumerate(r):
                                            txt = (cell.get('text') or '')
                                            # measure visible first-line length (internal markers replaced)
                                            visible = txt.replace('\u2028', '\n').split('\n', 1)[0]
                                            col_widths[ci] = max(col_widths[ci], len(visible))
                                    cols = []
                                    for w in col_widths:
                                        # Ensure at least a small width to avoid zero-width cols
                                        wch = max(4, int(w))
                                        cols.append(f'<col style="width:{wch}ch">')
                                    colgroup_html = '<colgroup>' + ''.join(cols) + '</colgroup>'
                        except Exception:
                            colgroup_html = ''
                    else:
                        # fallback: compute widths from the textual table if reasonable
                        try:
                            cell_rows = [r.split('\t') if r != '' else [''] for r in rows]
                            if cell_rows:
                                max_cols = max((len(r) for r in cell_rows), default=0)
                                col_widths = [0] * max_cols
                                for r in cell_rows:
                                    for ci, cell in enumerate(r):
                                        visible = cell.replace('\u2028', '\n').split('\n', 1)[0]
                                        col_widths[ci] = max(col_widths[ci], len(visible))
                                # only emit colgroup if we have more than 1 column or widths non-trivial
                                if max(col_widths, default=0) > 0 and max_cols > 0:
                                    cols = []
                                    for w in col_widths:
                                        wch = max(4, int(w))
                                        cols.append(f'<col style="width:{wch}ch">')
                                    colgroup_html = '<colgroup>' + ''.join(cols) + '</colgroup>'
                        except Exception:
                            colgroup_html = ''

                    out_parts.append('<table>')
                    if colgroup_html:
                        out_parts.append(colgroup_html)

                    if table_meta_for_span:
                        # Use precise rows/cells with attributes
                        for row_cells in table_meta_for_span.get('rows', []):
                            out_parts.append('<tr>')
                            for cell in row_cells:
                                txt = html.escape(cell.get('text', ''))
                                attrs = cell.get('attrs', {}) or {}
                                typ = cell.get('type', 'td')
                                attr_str = ''
                                # support common attributes: colspan, rowspan, align
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
                                # alignment (align or style text-align)
                                align = attrs.get('align') or ''
                                if not align:
                                    style = (attrs.get('style') or '')
                                    m = re.search(r'text-align\s*:\s*(left|right|center|justify)', style, flags=re.I) if style else None
                                    if m:
                                        align = m.group(1)
                                if align:
                                    attr_str += f' align="{html.escape(str(align))}"'
                                if typ == 'th':
                                    out_parts.append(f'<th{attr_str}>{txt}</th>')
                                else:
                                    out_parts.append(f'<td{attr_str}>{txt}</td>')
                            out_parts.append('</tr>')
                    else:
                        # Fallback: simple split-based reconstruction (legacy behavior)
                        for ridx, row in enumerate(rows):
                            if row == '' and len(rows) == 1:
                                continue
                            out_parts.append('<tr>')
                            cells = row.split('\t')
                            # Header inference: first row only if any th tag ranges exist globally
                            is_header_table = bool('th' in tags_by_name and tags_by_name['th'])
                            for cell_text in cells:
                                cell_text_escaped = html.escape(cell_text)
                                if is_header_table and ridx == 0:
                                    out_parts.append(f'<th>{cell_text_escaped}</th>')
                                else:
                                    out_parts.append(f'<td>{cell_text_escaped}</td>')
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