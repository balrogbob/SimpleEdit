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

            # <a href="..."> — record href and optional title on stack
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
                    self.ranges.setdefault('hyperlink', []).append([start, end])
                    try:
                        rec = {'start': start, 'end': end, 'href': href}
                        if title:
                            rec['title'] = title
                        self.hrefs.append(rec)
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
    Produce HTML fragment. Behavior depends on `exportCssMode`:
     - 'inline-element': (original) produce per-element inline style attributes
     - 'inline-block': produce class-based spans and caller should include <style> with _generate_css()
     - 'external': produce class-based spans; caller should write CSS file and include <link>
    """
    try:
        content = textArea.get('1.0', 'end-1c')
        if not content:
            return ''

        tags_by_name = _collect_all_tag_ranges(textArea)  # dict tag -> [[s,e], ...]
        # build events list
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
        active = []  # track active tags for nested closing
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
                            # use class wrappers for formatting when using block/external CSS
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
                        # syntax tags
                        if exportCssMode in ('inline-block', 'external'):
                            # class-based
                            if tag == 'todo':
                                out_parts.append(f'<span class="se-{tag}">')
                            else:
                                out_parts.append(f'<span class="se-{tag}">')
                        else:
                            # inline style attribute as before
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
            seg_escaped = html.escape(seg)
            out_parts.append(seg_escaped)

        # close any remaining open tags
        while active:
            t = active.pop()
            if t in ('bold', 'italic', 'underline'):
                if exportCssMode in ('inline-block', 'external'):
                    if t == 'bold':
                        out_parts.append('</strong>')
                    elif t == 'italic':
                        out_parts.append('</em>')
                    elif t == 'underline':
                        out_parts.append('</u>')
                else:
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