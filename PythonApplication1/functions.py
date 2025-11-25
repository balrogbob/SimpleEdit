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

RECENT_MAX = 10

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
        # stack entries: ('tag', start) or ('hyperlink', start, href, title)
        self.stack = []
        # stack to track nested ordered-list counters (one counter per open <ol>)
        self._ol_counters = []
        self.ranges = {}  # tag -> [[start,end], ...]
        self.hrefs = []   # list of {'start':int,'end':int,'href':str,'title':str}

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

    def handle_starttag(self, tag, attrs):
        try:
            tag = (tag or '').lower()
            attrd = dict(attrs or {})

            # Basic table/list handling: produce readable plain-text layout and record ranges.
            if tag in ('table', 'tr', 'td', 'th', 'ul', 'ol', 'li'):
                # row -> newline before starting a row (if not at start)
                if tag == 'tr':
                    if self.pos > 0:
                        # ensure a newline separating rows
                        self.out.append('\n')
                        self.pos += 1
                # cells -> separate with a tab so table columns remain aligned in plain text
                elif tag in ('td', 'th'):
                    prev_text = ''.join(self.out) if self.out else ''
                    if prev_text and not prev_text.endswith('\n'):
                        # insert a cell separator
                        self.out.append('\t')
                        self.pos += 1
                # list item -> newline + bullet (unordered) or dash (ordered fallback)
                elif tag == 'li':
                    # ensure newline, then a bullet + space
                    if self.pos > 0 and not ''.join(self.out).endswith('\n'):
                        self.out.append('\n')
                        self.pos += 1
                    # use a bullet for unordered lists; if inside an <ol> use numbering
                    if self._ol_counters:
                        # use current counter from the top of the ol stack
                        n = self._ol_counters[-1]
                        s_n = f"{n}. "
                        self.out.append(s_n)
                        self.pos += len(s_n)
                        # increment counter for next item
                        self._ol_counters[-1] = n + 1
                    else:
                        # unordered list bullet
                        self.out.append('\u2022 ')
                        self.pos += 2                # push the tag onto stack so handle_endtag will emit ranges
                # special-case <ol> to start a numbering counter
                if tag == 'ol':
                    # start numbering at 1
                    self._ol_counters.append(1)
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

            if tag == 'font':
                color = (attrd.get('color') or attrd.get('colour') or '').strip()
                hexcol = self._normalize_color_to_hex(color)
                if hexcol:
                    tagname = f"font_{hexcol.lstrip('#')}"
                    self.stack.append((tagname, self.pos)); return
                self.stack.append((None, self.pos)); return

            if tag == 'marquee':
                self.stack.append(('marquee', self.pos)); return

            # <a href="...">  record href and optional title on stack
            if tag == 'a':
                href = (attrd.get('href') or '').strip()
                title = (attrd.get('title') or '').strip() or None
                if href:
                    self.stack.append(('hyperlink', self.pos, href, title))
                else:
                    self.stack.append((None, self.pos))
                return

            if tag == 'span':
                style = (attrd.get('style') or '') or attrd.get('class', '')
                if style:
                    m = re.search(r'color\s*:\s*(#[0-9A-Fa-f]{3,6}|[A-Za-z]+)', style)
                    if m:
                        hexcol = self._normalize_color_to_hex(m.group(1))
                        if hexcol:
                            tagname = f"font_{hexcol.lstrip('#')}"
                            self.stack.append((tagname, self.pos)); return
                    m2 = re.search(r'background(?:-color)?\s*:\s*(#[0-9A-Fa-f]{3,6}|[A-Za-z]+)', style)
                    if m2:
                        bg = m2.group(1).lower()
                        if bg in ('#b22222', 'b22222', 'red'):
                            self.stack.append(('todo', self.pos)); return
                self.stack.append((None, self.pos)); return

            # fallback sentinel so handle_endtag can pop
            self.stack.append((None, self.pos))
        except Exception:
            try:
                self.stack.append((None, self.pos))
            except Exception:
                pass

    def handle_endtag(self, tag):
        try:
            if not self.stack:
                return
            item = self.stack.pop()
            if not item:
                return

            # hyperlink entries are ('hyperlink', start, href, title)
            if isinstance(item, tuple) and item[0] == 'hyperlink':
                _, start, href, title = item
                end = self.pos
                if end > start:
                    # record visible range for hyperlink (so tag ranges still work)
                    self.ranges.setdefault('hyperlink', []).append([start, end])
                    # also record link metadata so callers can restore clickable mappings
                    try:
                        rec = {'start': start, 'end': end, 'href': href}
                        if title:
                            rec['title'] = title
                        self.hrefs.append(rec)
                    except Exception:
                        pass
                return

            # if closing an ordered list, pop the counter stack
            if tag.lower() == 'ol':
                try:
                    if self._ol_counters:
                        self._ol_counters.pop()
                except Exception:
                    pass
                return

            # normal tags (tagname, start)
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
            # HTMLParser with convert_charrefs=True already converts char refs; keep data as-is
            self.out.append(data)
            self.pos += len(data)
        except Exception:
            pass

    def get_result(self):
        try:
            meta = {'tags': self.ranges}
            if self.hrefs:
                meta['links'] = list(self.hrefs)
            return ''.join(self.out), meta
        except Exception:
            return ''.join(self.out), {'tags': self.ranges, 'links': list(self.hrefs)}

def get_hex_color(color_tuple):
    """Return a hex string from a colorchooser return value."""
    if not color_tuple:
        return ""
    if isinstance(color_tuple, tuple) and len(color_tuple) >= 2:
        # colorchooser returns ((r,g,b), '#rrggbb')
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
        # perceived luminance (0..1)
        lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
        return '#000000' if lum > 0.56 else '#FFFFFF'
    except Exception:
        return '#000000'

def wrap_segment_by_tags(seg_text: str, active_tags: set):
    """Wrap a text segment according to active tag set into Markdown/HTML."""
    # Determine boolean flags considering explicit combo tags and 'all'
    has_bold = any(t in active_tags for t in ('bold', 'bolditalic', 'boldunderline', 'all'))
    has_italic = any(t in active_tags for t in ('italic', 'bolditalic', 'underlineitalic', 'all'))
    has_underline = any(t in active_tags for t in ('underline', 'boldunderline', 'underlineitalic', 'all'))
    has_small = 'small' in active_tags
    inner = seg_text
    # Prefer Markdown bold+italic triple-star where supported
    if has_bold and has_italic:
        inner = f"***{inner}***"
    elif has_bold:
        inner = f"**{inner}**"
    elif has_italic:
        inner = f"*{inner}*"

    if has_underline:
        # Markdown doesn't have native underline; use HTML <u> for compatibility
        inner = f"<u>{inner}</u>"

    if has_small:
        # wrap in <small> so exported HTML/MD keeps the visual reduction
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
            # simple complement
            cr = 255 - r
            cg = 255 - g
            cb = 255 - b
            # nudge if equals background color
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
                            # rotate the complement slightly
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
        # meta already shaped as {'tags': {...}, 'links': [...]}
        return plain, meta
    except Exception:
        return raw, {}

# --- URL history (persisted) -------------------------------------------------
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
        # normalize as string
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
        # Build the plain-text output
        full = ''.join(self.out)

        # If there are table ranges, post-process each table to compute column widths
        # and replace the plain segment with a padded version for nicer in-editor alignment.
        table_ranges = list(self.ranges.get('table', [])) if isinstance(self.ranges.get('table', []), list) else []
        if table_ranges:
            # Sort by start so adjustments can accumulate
            table_ranges = sorted(table_ranges, key=lambda r: r[0])
            offset_shift = 0
            # Remove existing structural table tags -- we'll rebuild them to match padded layout
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
                    # Split into rows then cells (parser used '\n' between rows and '\t' between cells)
                    rows = seg.split('\n')
                    cells_by_row = [r.split('\t') if r != '' else [''] for r in rows]

                    if not cells_by_row:
                        continue

                    # compute column widths across all rows
                    max_cols = max(len(row) for row in cells_by_row)
                    col_widths = [0] * max_cols
                    for row in cells_by_row:
                        for ci, cell in enumerate(row):
                            col_widths[ci] = max(col_widths[ci], len(cell))

                    # build new padded rows using spaces to align columns; preserve tabs as separators
                    new_rows = []
                    for row in cells_by_row:
                        padded_cells = []
                        for ci in range(max_cols):
                            text = row[ci] if ci < len(row) else ''
                            padded = text.ljust(col_widths[ci])
                            padded_cells.append(padded)
                        new_rows.append('\t'.join(padded_cells))
                    new_seg = '\n'.join(new_rows)

                    # replace full text segment
                    full = full[:start] + new_seg + full[end:]
                    delta = len(new_seg) - (end - start)
                    offset_shift += delta

                    # Recreate table/tr/td/th ranges for this table using new_seg geometry
                    table_start = start
                    table_end = start + len(new_seg)
                    self.ranges.setdefault('table', []).append([table_start, table_end])

                    # compute per-row/per-cell positions and record tr/td/th ranges
                    cursor = table_start
                    for ridx, rtext in enumerate(new_rows):
                        row_start = cursor
                        # iterate cells separated by '\t'
                        cell_cursor = row_start
                        cells = rtext.split('\t')
                        for cidx, cell_text in enumerate(cells):
                            cs = cell_cursor
                            ce = cs + len(cell_text)
                            # treat first row as header if original parser had any 'th' within original table range
                            is_header = False
                            # If original had 'th' ranges, prefer them. Check overlap with original table orig_start..orig_end
                            th_ranges = self.ranges.get('th', []) if isinstance(self.ranges.get('th', []), list) else []
                            # But we removed 'th' earlier; instead infer header if first row or if any <th> existed originally
                            # Heuristic: if the original segment included any '<th>' we will mark first row as header
                            # Use the original parser info: if there was any 'th' in original ranges list of table region
                            # Since we removed earlier, we can't reliably inspect; fallback to making first row header only if it contains non-empty cells and original first-row likely header
                            if ridx == 0:
                                # Make header if any cell had non-empty and original segment contained "<th" or if every cell is non-empty.
                                # We can attempt to detect original th occurrences by searching for '<th' in the original (non-escaped) seg,
                                # but parser already stripped tags. So practical heuristic: treat first row as header only if any original row started with capital or it's the only indicator.
                                # For safety, do not force header unless a 'th' tag originally existed - best-effort: skip header detection here.
                                is_header = False
                            if is_header:
                                self.ranges.setdefault('th', []).append([cs, ce])
                            else:
                                self.ranges.setdefault('td', []).append([cs, ce])
                            cell_cursor = ce + 1  # skip the tab that follows in new layout
                        row_end = cursor + len(rtext)
                        self.ranges.setdefault('tr', []).append([row_start, row_end])
                        cursor = row_end + 1  # move past newline
                except Exception:
                    # On any per-table error continue to next table
                    continue

            # Replace out and pos with updated full
            self.out = [full]
            self.pos = len(full)

        # Build meta based on (possibly updated) ranges
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
    This is intentionally simple and not a full markdown implementation.
    """
    tags = {'bold': [], 'italic': [], 'underline': [], 'bolditalic': []}
    plain_parts = []
    last = 0
    out_index = 0

    # pattern captures groups: g1=***text***, g2=**text**, g3=*text*, g4=<u>text</u>
    pattern = re.compile(r'\*\*\*([^\*]+?)\*\*\*|\*\*([^\*]+?)\*\*|\*([^\*]+?)\*|<u>(.*?)</u>', re.DOTALL)
    for m in pattern.finditer(md_text):
        start, end = m.span()
        # append intermediate plain text
        seg = md_text[last:start]
        plain_parts.append(seg)
        out_index += len(seg)
        # choose which group matched and its content
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
        # append content and record tag range
        plain_parts.append(content)
        if tag_name:
            tags.setdefault(tag_name, []).append([out_index, out_index + len(content)])
        out_index += len(content)
        last = end

    # append tail
    tail = md_text[last:]
    plain_parts.append(tail)
    plain_text = ''.join(plain_parts)

    # remove empty tag lists
    tags = {k: v for k, v in tags.items() if v}
    return plain_text, tags

def _collect_all_tag_ranges(textArea):
    """Collect ranges for both formatting and syntax tags as absolute offsets."""
    tags_to_save = (
        # formatting tags
        'bold', 'italic', 'underline', 'all',
        'underlineitalic', 'boldunderline', 'bolditalic',
        'small',
        # syntax/highlight tags
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
                # compute char offsets relative to buffer start
                start = len(textArea.get('1.0', s))
                end = len(textArea.get('1.0', e))
                if end > start:
                    arr.append([start, end])
            if arr:
                data[tag] = arr
    except Exception:
        pass
    return data

# --- Convert buffer to HTML fragment (used for .md and .html outputs) ---
def _convert_buffer_to_html_fragment(textArea):
    """
    Produce HTML fragment. Special-case: reconstruct real <table>...</table> elements
    when 'table'/'tr'/'td'/'th' tags are present in the tag ranges. For other regions
    we fall back to the existing span/class approach.
    """
    try:
        content = textArea.get('1.0', 'end-1c')
        if not content:
            return ''

        tags_by_name = _collect_all_tag_ranges(textArea)  # dict tag -> [[s,e], ...]
        # If no table tags present, keep existing rendering path (fast path)
        if 'table' not in tags_by_name:
            # reuse original conversion logic (escape plain text with inline spans)
            # build events list as before
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

        # If tables exist: produce output by slicing plain content and substituting table HTML for table ranges.
        table_ranges = sorted(tags_by_name.get('table', []), key=lambda r: r[0])
        out_parts = []
        last = 0
        for tstart, tend in table_ranges:
            # append escaped content before table
            if last < tstart:
                out_parts.append(html.escape(content[last:tstart]))
            # build table HTML for this table segment
            seg = content[tstart:tend]
            # split into rows and cells (parser uses '\n' and '\t')
            rows = [r for r in seg.split('\n') if r is not None]
            out_parts.append('<table border="1" cellpadding="4" cellspacing="0">')
            for ridx, row in enumerate(rows):
                # skip empty trailing lines
                if row == '' and len(rows) == 1:
                    continue
                out_parts.append('<tr>')
                cells = row.split('\t')
                # for each cell determine whether it was originally a header by checking th ranges overlap
                for cell_text in cells:
                    cell_text_escaped = html.escape(cell_text)
                    # simple heuristic: treat first row as header if 'th' tag exists anywhere in table tags
                    is_header = bool('th' in tags_by_name and tags_by_name['th'])
                    if is_header and ridx == 0:
                        out_parts.append(f'<th>{cell_text_escaped}</th>')
                    else:
                        out_parts.append(f'<td>{cell_text_escaped}</td>')
                out_parts.append('</tr>')
            out_parts.append('</table>')
            last = tend
        # append remainder
        if last < len(content):
            out_parts.append(html.escape(content[last:]))

        return ''.join(out_parts)
    except Exception:
        try:
            return html.escape(textArea.get('1.0', 'end-1c'))
        except Exception:
            return ''

def _generate_css():
    """Return CSS text used for inline-block or external export modes."""
    try:
        # Base wrapper class to preserve whitespace and colors
        parts = []
        parts.append(".simpleedit-export{")
        parts.append(f"background: {backgroundColor};")
        parts.append(f"color: {fontColor};")
        parts.append(f"font-family: {fontName}, monospace;")
        parts.append("white-space: pre-wrap;")
        parts.append("padding: 8px;")
        parts.append("}")
        # map tag classes to colors/backgrounds
        for tag, color in _TAG_COLOR_MAP.items():
            cls = f".se-{tag}"
            if tag == 'todo':
                parts.append(f"{cls}{{ color:#ffffff; background:#B22222; }}")
            else:
                parts.append(f"{cls}{{ color: {color}; }}")
        # formatting classes
        parts.append(".se-bold{ font-weight: bold; }")
        parts.append(".se-italic{ font-style: italic; }")
        parts.append(".se-underline{ text-decoration: underline; }")
        parts.append(".se-small{ font-size: 0.85em; }")
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
    'todo': '#FFFFFF',  # todo uses white text on red background - background handled specially
}
# reverse map for parsing spans back to tag names (normalized to lower hex)
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

        # Prepare wrapper that always preserves whitespace and base styling (but for inline-block/external actual colors come from CSS)
        wrapper_attrs = []
        if exportCssMode == 'inline-element':
            # keep previous inline wrapper style for background/text/font
            wrapper_style = (
                f"background:{backgroundColor};"
                f"color:{fontColor};"
                f"font-family:{fontName},monospace;"
                "white-space:pre-wrap;"
                "padding:8px;"
            )
            wrapped_fragment = f'<div style="{wrapper_style}">{fragment}</div>'
        else:
            # class-based wrapper; CSS provides colors
            wrapped_fragment = f'<div class="simpleedit-export">{fragment}</div>'

        if fileName.lower().endswith('.html'):
            if exportCssMode == 'external':
                # determine css path: prefer explicit exportCssPath or same-name .css next to file
                css_path = exportCssPath or os.path.splitext(fileName)[0] + '.css'
                # write css file
                try:
                    with open(css_path, 'w', encoding='utf-8') as cssf:
                        cssf.write(_generate_css())
                except Exception:
                    pass
                # compute relative link href (use basename if in same directory)
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
            # .md: Markdown engines vary, but raw HTML is allowed in many viewers.
            if exportCssMode == 'external':
                css_path = exportCssPath or os.path.splitext(fileName)[0] + '.css'
                try:
                    with open(css_path, 'w', encoding='utf-8') as cssf:
                        cssf.write(_generate_css())
                except Exception:
                    pass
                # add link tag at top (may or may not be respected by renderer)
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