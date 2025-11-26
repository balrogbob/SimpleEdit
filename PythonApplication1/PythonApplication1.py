#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SimpleEdit

A small Tkinter-based code editor with basic syntax highlighting, MRU,
formatting toggles and an experimental local GPT autocomplete.

License: MIT
Copyright (c) 2024 Joshua Richards
"""

# Built-in imports
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
import tkinter.font as tkfont
import shutil, sys, os


# Optional ML dependencies (wrapped so editor still runs without them)
try:
    import torch
    import tiktoken
    from model import GPTConfig, GPT
    _ML_AVAILABLE = True
except Exception:
    _ML_AVAILABLE = False
_AI_BUTTON_DEFAULT_TEXT = "AI Autocomplete (Experimental)"
__author__ = 'Joshua Richards'
__license__ = 'MIT'
__version__ = '0.0.3'

try:
    import functions as funcs
except Exception:
    import functions as funcs  # fallback if running as script
# -------------------------
# Config / MRU initialization
# -------------------------
DEFAULT_CONFIG = funcs.DEFAULT_CONFIG

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

RECENT_MAX = getattr(funcs, 'RECENT_MAX', 10)
manual_detect_after_id = None

def load_recent_files():
    return funcs.load_recent_files(config)


def save_recent_files(lst):
    return funcs.save_recent_files(config, INI_PATH, lst)


def add_recent_file(path):
    return funcs.add_recent_file(config, INI_PATH, path,
                                   on_update=lambda: refresh_recent_menu(),
                                   max_items=RECENT_MAX)


def clear_recent_files():
    return funcs.clear_recent_files(config, INI_PATH,
                                      on_update=lambda: refresh_recent_menu())

def _open_path(path: str, open_in_new_tab: bool = True):
    """Core logic to open `path` either in a new tab or in the current tab."""
    try:
        with open(path, 'r', errors='replace', encoding='utf-8') as fh:
            raw = fh.read()

        # First try to extract SIMPLEEDIT meta (preferred)
        content, meta = _extract_header_and_meta(raw)
        if meta:
            if open_in_new_tab:
                tx, fr = create_editor_tab(os.path.basename(path) or "Untitled", content, filename=path)
                _apply_tag_configs_to_widget(tx)
            else:
                textArea.delete('1.0', 'end')
                textArea.insert('1.0', content)
                # update current frame metadata
                try:
                    sel = editorNotebook.select()
                    if sel:
                        frame = root.nametowidget(sel)
                        frame.fileName = path
                        # update visible tab title so UI and tab-level metadata remain consistent
                        try:
                            editorNotebook.tab(sel, text=os.path.basename(path) or path)
                        except Exception:
                            pass                
                except Exception:
                    pass
                _apply_tag_configs_to_widget(textArea)

            statusBar['text'] = f"'{path}' opened successfully!"
            root.fileName = path
            add_recent_file(path)
            refresh_recent_menu()
            # schedule one-shot autodetect for in-place opens so detection behaves like new-tab opens
            try:
                prev = getattr(root, '_manual_detect_after_id', None)
                if prev:
                    try:
                        root.after_cancel(prev)
                    except Exception:
                        pass
                root._manual_detect_after_id = root.after(1000, lambda: manual_detect_syntax(force=False))
            except Exception:
                pass
            root.after(0, lambda: _apply_formatting_from_meta(meta))
            try:
                if _ML_AVAILABLE and loadAIOnOpen and not _model_loaded and not _model_loading:
                    Thread(target=lambda: _start_model_load(start_autocomplete=False), daemon=True).start()
            except Exception:
                pass
            if updateSyntaxHighlighting.get():
                root.after(0, highlightPythonInit)
            return

        ext = path.lower().split('.')[-1] if isinstance(path, str) else ''
        if ext in ('md', 'html', 'htm'):
            # optional autodetect -> apply a matching syntax preset before parsing if enabled
            try:
                if config.getboolean("Section1", "autoDetectSyntax", fallback=True):
                    preset_path = detect_syntax_preset_from_content(raw)
                    if preset_path:
                        applied = apply_syntax_preset(preset_path)
                        if applied:
                            statusBar['text'] = "Applied syntax preset from autodetect."
            except Exception:
                pass

            # respect "open as source" setting
            if config.getboolean("Section1", "openHtmlAsSource", fallback=False):
                if open_in_new_tab:
                    tx, fr = create_editor_tab(os.path.basename(path) or "Untitled", raw, filename=path)
                    _apply_tag_configs_to_widget(tx)
                    try:
                        fr._opened_as_source = True
                        fr._raw_html = raw
                        fr._raw_html_plain = raw
                        fr._raw_html_tags_meta = None
                        fr._view_raw = True
                        try:
                            root.after(0, update_view_status_indicator)
                        except Exception:
                            pass
                    except Exception:
                        pass
                else:
                    textArea.delete('1.0', 'end')
                    textArea.insert('1.0', raw)
                    _apply_tag_configs_to_widget(textArea)
                    try:
                        sel = editorNotebook.select()
                        if sel:
                            frame = root.nametowidget(sel)
                            frame._opened_as_source = True
                            frame._raw_html = raw
                            frame._raw_html_plain = raw
                            frame._raw_html_tags_meta = None
                            frame._view_raw = True
                            try:
                                root.after(0, update_view_status_indicator)
                            except Exception:
                                pass
                    except Exception:
                        pass
                statusBar['text'] = f"'{path}' opened (raw source)!"
                root.fileName = path
                add_recent_file(path)
                refresh_recent_menu()
                try:
                    prev = getattr(root, '_manual_detect_after_id', None)
                    if prev:
                        try:
                            root.after_cancel(manual_detect_after_id)
                        except Exception:
                            pass
                    manual_detect_after_id = root.after(1000, lambda: manual_detect_syntax(force=False))
                except Exception:
                    pass
                if updateSyntaxHighlighting.get():
                    root.after(0, highlightPythonInit)
                return

            plain, tags_meta = funcs._parse_html_and_apply(raw)
            if open_in_new_tab:
                tx, fr = create_editor_tab(os.path.basename(path) or "Untitled", plain, filename=path)
                _apply_tag_configs_to_widget(tx)
                # keep original raw HTML and parsed meta on the tab so we can toggle view later
                try:
                    fr._raw_html = raw
                    fr._raw_html_plain = plain
                    fr._raw_html_tags_meta = tags_meta
                    fr._view_raw = False
                except Exception:
                    pass
                try:
                    fr._opened_as_source = False
                except Exception:
                    pass
            else:
                textArea.delete('1.0', 'end')
                textArea.insert('1.0', plain)
                _apply_tag_configs_to_widget(textArea)
                try:
                    sel = editorNotebook.select()
                    if sel:
                        frame = root.nametowidget(sel)
                        frame._raw_html = raw
                        frame._raw_html_plain = plain
                        frame._raw_html_tags_meta = tags_meta
                        frame._view_raw = False
                except Exception:
                    pass
                try:
                    sel = editorNotebook.select()
                    if sel:
                        frame = root.nametowidget(sel)
                        frame._opened_as_source = False
                except Exception:
                    pass
            statusBar['text'] = f"'{path}' opened (HTML/MD parsed)!"
            root.fileName = path
            add_recent_file(path)
            refresh_recent_menu()
            # schedule one-shot autodetect after replacing current tab content
            try:
                prev = getattr(root, '_manual_detect_after_id', None)
                if prev:
                    try:
                        root.after_cancel(manual_detect_after_id)
                    except Exception:
                        pass
                manual_detect_after_id = root.after(1000, lambda: manual_detect_syntax(force=False))
            except Exception:
                pass
            if tags_meta and tags_meta.get('tags'):
                root.after(0, lambda: _apply_formatting_from_meta(tags_meta))
            if updateSyntaxHighlighting.get():
                root.after(0, highlightPythonInit)
            return

        # Fallback: raw
        if open_in_new_tab:
            tx, fr = create_editor_tab(os.path.basename(path) or "Untitled", raw, filename=path)
            _apply_tag_configs_to_widget(tx)
            try:
                fr._opened_as_source = False
            except Exception:
                pass
        else:
            textArea.delete('1.0', 'end')
            textArea.insert('1.0', raw)
            _apply_tag_configs_to_widget(textArea)
            try:
                sel = editorNotebook.select()
                if sel:
                    frame = root.nametowidget(sel)
                    frame._opened_as_source = False
            except Exception:
                pass

        statusBar['text'] = f"'{path}' opened successfully!"
        root.fileName = path
        try:
            if _ML_AVAILABLE and loadAIOnOpen and not _model_loaded and not _model_loading:
                Thread(target=lambda: _start_model_load(start_autocomplete=False), daemon=True).start()
        except Exception:
            pass

        add_recent_file(path)
        refresh_recent_menu()
        try:
            prev = getattr(root, '_manual_detect_after_id', None)
            if prev:
                try:
                    root.after_cancel(manual_detect_after_id)
                except Exception:
                    pass
            manual_detect_after_id = root.after(1000, lambda: manual_detect_syntax(force=False))
        except Exception:
            pass
        if updateSyntaxHighlighting.get():
            root.after(0, highlightPythonInit)
    except Exception as e:
        messagebox.showerror("Error", str(e))


def _ask_open_choice(path: str):
    """Modal: ask user whether to open a recent item in current or new tab, optional 'remember' checkbox."""
    try:
        dlg = Toplevel(root)
        dlg.transient(root)
        dlg.grab_set()
        dlg.title("Open recent file")
        container = ttk.Frame(dlg, padding=12)
        container.grid(row=0, column=0, sticky='nsew')
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)

        ttk.Label(container, text=f"Open '{os.path.basename(path)}'").grid(row=0, column=0, columnspan=2, sticky='w', pady=(0,8))

        choice_var = IntVar(value=1 if config.get("Section1", "recentOpenDefault", fallback="new") == "new" else 0)
        ttk.Radiobutton(container, text="Open in current tab", variable=choice_var, value=0).grid(row=1, column=0, sticky='w')
        ttk.Radiobutton(container, text="Open in new tab", variable=choice_var, value=1).grid(row=1, column=1, sticky='w')

        remember_var = IntVar(value=0)
        ttk.Checkbutton(container, text="Remember this choice (don't prompt again)", variable=remember_var).grid(row=2, column=0, columnspan=2, sticky='w', pady=(8,0))

        status = ttk.Label(container, text="")
        status.grid(row=3, column=0, columnspan=2, sticky='w', pady=(8,0))

        def do_cancel():
            try:
                dlg.grab_release()
            except Exception:
                pass
            dlg.destroy()

        def do_open():
            open_in_new = bool(choice_var.get())
            # if remember -> persist default and disable prompting
            if remember_var.get():
                try:
                    config.set("Section1", "recentOpenDefault", "new" if open_in_new else "current")
                    config.set("Section1", "promptOnRecentOpen", "False")
                    with open(INI_PATH, 'w') as f:
                        config.write(f)
                except Exception:
                    pass
            try:
                dlg.grab_release()
            except Exception:
                pass
            dlg.destroy()
            # intelligent open for URLs vs files
            _open_maybe_url(path, open_in_new_tab=open_in_new)

        btns = ttk.Frame(container)
        btns.grid(row=4, column=0, columnspan=2, sticky='e', pady=(8,0))
        ttk.Button(btns, text="Open", command=do_open).pack(side=RIGHT, padx=(6,0))
        ttk.Button(btns, text="Cancel", command=do_cancel).pack(side=RIGHT)
        dlg.update_idletasks()
        center_window(dlg)
    except Exception:
        pass

def open_recent_file(path: str):
    """Open a recent file (called from recent menu). Prompts user unless preference set."""
    try:
        # If user disabled prompting, use stored default
        if not config.getboolean("Section1", "promptOnRecentOpen", fallback=True):
            use_new = config.get("Section1", "recentOpenDefault", fallback="new") == "new"
            _open_maybe_url(path, open_in_new_tab=use_new)
            return

        # Otherwise show a small modal asking current/new with remember checkbox
        _ask_open_choice(path)
    except Exception as e:
        messagebox.showerror("Error", str(e))

def refresh_recent_menu():
    """Rebuild the `recentMenu` items from persisted MRU list."""
    try:
        recentMenu.delete(0, END)
        files = load_recent_files()
        if not files:
            recentMenu.add_command(label="(no recent files)", state='disabled')
            return

        for path in files:
            label = os.path.basename(path) or path
            recentMenu.add_command(label=label, command=lambda p=path: open_recent_file(p))

        recentMenu.add_separator()
        recentMenu.add_command(label="Clear Recent", command=clear_recent_files)
    except Exception:
        # keep UI resilient to errors
        pass


# -------------------------
# Config values (typed)
# -------------------------
fontName = config.get('Section1', 'fontName')
fontSize = int(config.get('Section1', 'fontSize'))
fontColor = config.get('Section1', 'fontColor')
backgroundColor = config.get('Section1', 'backgroundColor')
undoSetting = config.getboolean('Section1', 'undoSetting')
cursorColor = config.get('Section1', 'cursorColor')
# line-number colors (user-configurable)
lineNumberFg = config.get('Section1', 'lineNumberFg', fallback='#555555')
lineNumberBg = config.get('Section1', 'lineNumberBg', fallback='#000000')
currentLineBg = config.get('Section1', 'currentLineBg', fallback='#222222')
aiMaxContext = int(config.get('Section1', 'aiMaxContext'))
temperature = float(config.get('Section1', 'temperature'))
top_k = int(config.get('Section1', 'top_k'))
seed = int(config.get('Section1', 'seed'))

random.seed(seed)
if _ML_AVAILABLE:
    torch.manual_seed(seed + random.randint(0, 9999))
loadAIOnOpen = config.getboolean('Section1', 'loadAIOnOpen', fallback=False)
loadAIOnNew = config.getboolean('Section1', 'loadAIOnNew', fallback=False)

# -------------------------
# Optional model init (lazy-loaded on user request)
model = None
original_model = None
encode = lambda s: []
decode = lambda l: ""
_model_loading = False
_model_loaded = False

def unload_model():
    """Unload the AI model and update UI. Visible only when a model is loaded."""
    global model, original_model, encode, decode, _model_loaded, _model_loading
    try:
        if not _model_loaded:
            return
        # Clear references so Python can GC model memory
        model = None
        original_model = None
        encode = lambda s: []
        decode = lambda l: ""
        _model_loaded = False
        _model_loading = False

        # UI updates must run on main thread
        def ui_updates():
            try:
                statusBar['text'] = "AI model unloaded."
            except Exception:
                pass
            try:
                buttonAI.config(text=_AI_BUTTON_DEFAULT_TEXT)
            except Exception:
                pass
            try:
                # hide unload button
                buttonUnload.pack_forget()
            except Exception:
                pass
            try:
                # clear params label
                paramsLabel.config(text="")
            except Exception:
                pass

        root.after(0, ui_updates)
    except Exception:
        pass


def _start_model_load(start_autocomplete: bool = False):
    """Load model in a background thread and show a progress popup.
    If start_autocomplete is True, start `python_ai_autocomplete` after load."""
    global model, original_model, encode, decode, _model_loading, _model_loaded

    if _model_loaded or _model_loading:
        return

    dlg, pb, status = show_progress_popup("Loading AI model", determinate=True)
    status['text'] = "Initializing..."

    def worker():
        # Ensure assignments update module-level variables
        global model, original_model, encode, decode, _model_loading, _model_loaded
        nonlocal dlg, pb, status
        try:
            _model_loading = True
            root.after(0, lambda: status.config(text="Loading checkpoint..."))
            root.after(0, lambda: pb.config(value=10))
            try:
                init_from = 'resume'
                out_dir = 'out'
                ckpt_path = os.path.join(out_dir, 'ckpt.pt')
                checkpoint = torch.load(ckpt_path, map_location='cpu', weights_only=True)
            except Exception as ex:
                raise RuntimeError(f"Failed to load checkpoint: {ex}")

            root.after(0, lambda: pb.config(value=30))
            root.after(0, lambda: status.config(text="Constructing model..."))
            try:
                gptconf = GPTConfig(**checkpoint['model_args'])
                model_local = GPT(gptconf)
                state_dict = checkpoint['model']
                unwanted_prefix = '_orig_mod.'
                for k in list(state_dict.keys()):
                    if k.startswith(unwanted_prefix):
                        state_dict[k[len(unwanted_prefix):]] = state_dict.pop(k)
                model_local.load_state_dict(state_dict)
                model_local.eval()
                model_local.to('cpu')
            except Exception as ex:
                raise RuntimeError(f"Failed to construct/load model state: {ex}")

            root.after(0, lambda: pb.config(value=60))
            root.after(0, lambda: status.config(text="Compiling model (may take a moment)..."))
            try:
                # preserve original for fallback
                original_model = model_local
                if sys.platform == "win32" and shutil.which("cl") is None:
                    try:
                        compiled = torch.compile(model_local, backend="eager", mode="reduce-overhead")
                    except Exception:
                        compiled = model_local
                else:
                    try:
                        compiled = torch.compile(model_local, mode="reduce-overhead")
                    except Exception:
                        compiled = model_local
                model = compiled
            except Exception:
                # if compile fails, keep the eager model
                model = model_local

            root.after(0, lambda: pb.config(value=80))
            root.after(0, lambda: status.config(text="Initializing tokenizer..."))
            try:
                enc = tiktoken.get_encoding("gpt2")
                encode = lambda s: enc.encode(s, allowed_special={"<|endoftext|>"})
                decode = lambda l: enc.decode(l)
            except Exception:
                encode = lambda s: []
                decode = lambda l: ""

            _model_loaded = True
            root.after(0, lambda: statusBar.config(text="AI model loaded."))
            root.after(0, lambda: pb.config(value=100))

            # update UI: compute initial context token count on main thread (safe access to textArea)
            def set_loaded_ui():
                try:
                    # determine selection / context same as autocomplete does
                    try:
                        ranges = textArea.tag_ranges("sel")
                        if ranges:
                            start, end = ranges[0], ranges[1]
                        else:
                            start = textArea.index(f'insert-{aiMaxContext}c')
                            end = textArea.index('insert')
                    except Exception:
                        start = textArea.index(f'insert-{aiMaxContext}c')
                        end = textArea.index('insert')
                    try:
                        content = textArea.get(start, end)
                        n = len(encode(content)) if encode else 0
                    except Exception:
                        n = 0
                    try:
                        buttonAI.config(text=f"AI Autocomplete - ctx: {n}")
                    except Exception:
                        pass
                    try:
                        # show unload button (only when model is loaded)
                        buttonUnload.pack(side=LEFT, padx=2, pady=2)
                    except Exception:
                        pass
                    try:
                        # update params label
                        paramsLabel.config(text=_get_model_param_text())
                    except Exception:
                        pass
                except Exception:
                    pass

            root.after(0, set_loaded_ui)

        except Exception as e:
            model = None
            original_model = None
            _model_loaded = False
            root.after(0, lambda: statusBar.config(text=f"AI load error: {e}"))
        finally:
            _model_loading = False
            try:
                close_progress_popup(dlg, pb)
            except Exception:
                pass

            # if requested, automatically begin autocomplete after load
            if _model_loaded and start_autocomplete:
                try:
                    Thread(target=python_ai_autocomplete, daemon=True).start()
                except Exception:
                    pass

    Thread(target=worker, daemon=True).start()



def on_ai_button_click():
    """Handler bound to the AI toolbar button.
    If model is loaded -> start autocomplete. If not loaded -> load it (showing progress)."""
    global _model_loaded, _model_loading

    if not _ML_AVAILABLE:
        try:
            statusBar['text'] = "AI libraries not available."
        except Exception:
            pass
        return

    if _model_loaded:
        # Already loaded: run autocomplete in background to keep UI responsive
        Thread(target=python_ai_autocomplete, daemon=True).start()
        return

    if _model_loading:
        try:
            statusBar['text'] = "Model is already loading..."
        except Exception:
            pass
        return

    # Start load and immediately begin autocomplete after load completes
    _start_model_load(start_autocomplete=True)

# -------------------------
# Helper utilities
# -------------------------
# --- Font family & size dropdowns for presentational toolbar ---


def get_hex_color(color_tuple):
    return funcs.get_hex_color(color_tuple)

def _sanitize_tag_name(s: str) -> str:
    return funcs._sanitize_tag_name(s)

def get_system_fonts():
    """Return a sorted list of available system font family names (strings)."""
    try:
        families = list(tkfont.families())
        families_sorted = sorted(set(families), key=lambda x: x.lower())
        return families_sorted
    except Exception:
        return []

def _record_selection_for_font(event=None):
    """Record current selection (as normalized indices) so dropdown clicks don't clear it."""
    global _last_font_selection
    try:
        _last_font_selection = None
        if not textArea:
            return
        rng = textArea.tag_ranges('sel')
        if rng and len(rng) >= 2:
            _last_font_selection = (textArea.index(rng[0]), textArea.index(rng[1]))
    except Exception:
        _last_font_selection = None

def _restore_selection_for_font():
    """Restore previously recorded selection (if any)."""
    try:
        if not textArea:
            return
        sel = globals().get('_last_font_selection', None)
        if not sel:
            return
        s, e = sel
        try:
            textArea.tag_remove('sel', '1.0', 'end')
        except Exception:
            pass
        try:
            textArea.tag_add('sel', s, e)
            textArea.mark_set('insert', e)
        except Exception:
            pass
    except Exception:
        pass

def apply_tag_config_to_all(tag_name: str, kwargs: dict):
    """Apply tag_config for tag_name to every Text widget in open tabs (best-effort)."""
    try:
        # apply to current widget first
        try:
            textArea.tag_config(tag_name, **kwargs)
        except Exception:
            pass
        # apply to other open tabs
        for tab_id in editorNotebook.tabs():
            try:
                frame = root.nametowidget(tab_id)
                for child in frame.winfo_children():
                    if isinstance(child, Text):
                        try:
                            child.tag_config(tag_name, **kwargs)
                        except Exception:
                            pass
            except Exception:
                pass
    except Exception:
        pass

def _build_style_tag_name(b: bool, i: bool, u: bool) -> str:
    """Return canonical style tag name for a combination of bold/italic/underline."""
    try:
        parts = []
        if b:
            parts.append('b')
        if i:
            parts.append('i')
        if u:
            parts.append('u')
        if not parts:
            return 'style_plain'
        return 'style_' + '_'.join(parts)
    except Exception:
        return 'style_plain'

def _make_style_tag_name(font_tag: str | None, b: bool, i: bool, u: bool) -> str:
    """Return a sanitized style tag name optionally namespaced by a font tag."""
    try:
        parts = []
        if b:
            parts.append('b')
        if i:
            parts.append('i')
        if u:
            parts.append('u')
        if not parts:
            body = 'plain'
        else:
            body = '_'.join(parts)
        if font_tag:
            return f"style_{_sanitize_tag_name(font_tag)}_{body}"
        return f"style_native_{body}"
    except Exception:
        return f"style_native_plain"


def _ensure_style_tag(tag: str, bold: bool, italic: bool, underline: bool, font_tag: str | None = None):
    """Ensure a style tag exists that sets the combined font attributes.

    If a `font_tag` is supplied, derive family/size from that tag so weight/slant apply
    without changing the family/size. Falls back to global fontName/fontSize.
    """
    try:
        # if already configured with a font we assume it's OK
        try:
            cur = textArea.tag_cget(tag, 'font') or ''
            cur_ug = textArea.tag_cget(tag, 'underline') or ''
            if cur or cur_ug:
                return
        except Exception:
            pass

        # Derive base family/size from provided font_tag (if any) or defaults
        fam = fontName
        sz = fontSize
        try:
            if font_tag:
                # attempt to read its configured font (may be a tuple/string)
                fval = textArea.tag_cget(font_tag, 'font')
                if fval:
                    try:
                        fobj = tkfont.Font(font=fval)
                        fam = fobj.actual('family') or fam
                        sz = int(fobj.actual('size') or sz)
                    except Exception:
                        # try parsing simple "Family Size" string
                        m = re.match(r'([^\d]+)\s+(\d+)', str(fval))
                        if m:
                            fam = m.group(1).strip()
                            try:
                                sz = int(m.group(2))
                            except Exception:
                                sz = sz
        except Exception:
            pass

        # build a tkfont.Font with requested weight/slant
        try:
            weight = 'bold' if bold else 'normal'
            slant = 'italic' if italic else 'roman'
            u = 1 if underline else 0
            f = tkfont.Font(family=fam, size=sz, weight=weight, slant=slant, underline=u)
            textArea.tag_config(tag, font=f)
            # ensure underline explicitly for older Tk where Font underline may not be honored
            if underline:
                try:
                    textArea.tag_config(tag, underline=1)
                except Exception:
                    pass
        except Exception:
            # fallback: attempt simple tuple + underline kw
            try:
                specs = [fam, sz]
                if bold:
                    specs.append('bold')
                if italic:
                    specs.append('italic')
                textArea.tag_config(tag, font=tuple(specs), underline=1 if underline else 0)
            except Exception:
                pass
    except Exception:
        pass

def _raise_hex_tags_above(tw: Text):
    """Ensure any `hex_XXXXXX` tags are raised above other tags in the widget."""
    try:
        if not tw or not isinstance(tw, Text):
            return
        for t in tw.tag_names():
            try:
                if isinstance(t, str) and t.startswith('hex_'):
                    # try to place hex tag above everything (best-effort)
                    try:
                        tw.tag_raise(t)
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception:
        pass

def _raise_tag_over_marquee(tag: str):
    """Raise `tag` above marquee so its fg/bg win visually."""
    try:
        # If marquee exists, raise this tag above marquee; otherwise just raise it to top.
        if 'marquee' in textArea.tag_names():
            try:
                textArea.tag_raise(tag, 'marquee')
                return
            except Exception:
                pass
        try:
            textArea.tag_raise(tag)
        except Exception:
            pass
    except Exception:
        pass

def apply_font_to_selection(family: str | None = None, size: int | None = None):
    """Apply the chosen font family+size to the current selection (or entire buffer)."""
    try:
        fam = (family or font_family_var.get() or '').strip()
        sz = size if size is not None else (font_size_var.get() or '')
        if isinstance(sz, str):
            try:
                sz = int(sz)
            except Exception:
                sz = None
        if not fam and not sz:
            return

        label = f"{fam}_{sz}" if fam and sz else (fam or str(sz))
        tag = f"font_{_sanitize_tag_name(label)}"

        # create font tuple for tag_config
        font_tuple = None
        try:
            if fam and sz:
                font_tuple = (fam, int(sz))
            elif fam:
                font_tuple = (fam, fontSize)
            elif sz:
                font_tuple = (fontName, int(sz))
        except Exception:
            font_tuple = None

        kwargs = {}
        if font_tuple:
            kwargs['font'] = font_tuple

        # apply tag_config to all widgets so tag exists everywhere
        if kwargs:
            apply_tag_config_to_all(tag, kwargs)

        # add/remove tag for selection
        start, end = selection_or_all()
        try:
            # remove existing identical tag (toggle)
            ranges = textArea.tag_nextrange(tag, start, end)
            if ranges:
                textArea.tag_remove(tag, start, end)
            else:
                textArea.tag_add(tag, start, end)
                # ensure font tag wins over marquee
                _raise_tag_over_marquee(tag)
        except Exception:
            try:
                textArea.tag_add(tag, start, end)
                _raise_tag_over_marquee(tag)
            except Exception:
                pass
    except Exception:
        pass

def selection_or_all():
    """Return a (start, end) range for the current selection or entire buffer."""
    ranges = textArea.tag_ranges("sel")
    if ranges:
        return ranges[0], ranges[1]
    return "1.0", "end-1c"

def clear_font_from_selection():
    """Remove any applied font_* tags from the selection (or whole buffer if nothing selected)."""
    try:
        start, end = selection_or_all()
        # Remove all tags whose name starts with 'font_' that intersect the selection.
        for tag in textArea.tag_names():
            try:
                if not tag.startswith('font_'):
                    continue
                # Remove tag in the selected region only (safe even if tag not present there)
                textArea.tag_remove(tag, start, end)
            except Exception:
                pass
    except Exception:
        pass
# -------------------------
# Tkinter UI - create root and widgets
# -------------------------
root = Tk()
root._manual_detect_after_id = None
url_var = StringVar(value='')
root.geometry("800x600")
root.title('SimpleEdit')
root.fileName = ""
font_family_var = StringVar(value=config.get("Section1", "fontName", fallback=fontName))
font_size_var = StringVar(value=str(config.get("Section1", "fontSize", fallback=str(fontSize))))

menuBar = Menu(root)
root.config(menu=menuBar)

# File/Edit menus
fileMenu = Menu(menuBar, tearoff=False)
recentMenu = Menu(menuBar, tearoff=False)
editMenu = Menu(menuBar, tearoff=False)

menuBar.add_cascade(label="File", menu=fileMenu)
fileMenu.add_command(label='New', command=lambda: newFile())
fileMenu.add_separator()
fileMenu.add_command(label='Open', command=lambda: open_file_action())
fileMenu.add_cascade(label="Open Recent", menu=recentMenu)
fileMenu.add_separator()
fileMenu.add_command(label='Save', command=lambda: save_file())
fileMenu.add_command(label='Save As', command=lambda: save_file_as())
fileMenu.add_command(label='Save as Markdown', command=lambda: save_as_markdown(textArea))
fileMenu.add_separator()
fileMenu.add_command(label='Exit', command=root.destroy)

menuBar.add_cascade(label="Edit", menu=editMenu)
editMenu.add_command(label='Cut', command=lambda: cut_selected_text())
editMenu.add_command(label='Copy', command=lambda: copy_to_clipboard())
editMenu.add_command(label='Paste', command=lambda: paste_from_clipboard())
editMenu.add_separator()
editMenu.add_command(label='Undo', command=lambda: textArea.edit_undo(), accelerator='Ctrl+Z')
editMenu.add_command(label='Redo', command=lambda: textArea.edit_redo(), accelerator='Ctrl+Y')
editMenu.add_command(label='Find/Replace', command=lambda: open_find_replace())
editMenu.add_command(label='Go To Line', command=lambda: go_to_line(), accelerator='Ctrl+G')
root.bind('<Control-g>', lambda e: go_to_line())



# Helper to return a nicely formatted parameter count string for the loaded model
def _get_model_param_text():
    try:
        # prefer the original_model (uncompiled) if available for accurate counting
        m = original_model if 'original_model' in globals() and original_model is not None else model
        if m is None:
            return ""
        if hasattr(m, 'get_num_params'):
            n = int(m.get_num_params(non_embedding=True))
        else:
            n = sum(p.numel() for p in m.parameters())
        if n <= 0:
            return ""
        return f"Params: {n/1e6:.2f}M"
    except Exception:
        return ""

# --- Symbols menu & manager -------------------------------------------------
symbolsMenu = Menu(menuBar, tearoff=False)
menuBar.add_cascade(label="Symbols", menu=symbolsMenu)
symbolsMenu.add_command(label="Manage Symbols...", command=lambda: open_symbols_manager())


def open_symbols_manager():
    """Small dialog to view/edit/remove/swap persisted vars/defs."""
    global persisted_vars, persisted_defs

    dlg = Toplevel(root)
    dlg.title("Manage Symbols")
    dlg.transient(root)
    dlg.grab_set()
    dlg.resizable(False, False)

    container = ttk.Frame(dlg, padding=10)
    container.grid(row=0, column=0, sticky='nsew')

    # Vars column
    ttk.Label(container, text="Persisted Variables").grid(row=0, column=0, sticky='w')
    vars_frame = ttk.Frame(container)
    vars_frame.grid(row=1, column=0, padx=(0, 8), sticky='nsew')
    vars_lb = Listbox(vars_frame, selectmode=SINGLE, height=10, exportselection=False)
    vars_scroll = ttk.Scrollbar(vars_frame, orient=VERTICAL, command=vars_lb.yview)
    vars_lb.configure(yscrollcommand=vars_scroll.set)
    vars_lb.grid(row=0, column=0, sticky='nsew')
    vars_scroll.grid(row=0, column=1, sticky='ns')
    vars_frame.columnconfigure(0, weight=1)

    # Defs column
    ttk.Label(container, text="Persisted Definitions (defs/classes)").grid(row=0, column=1, sticky='w')
    defs_frame = ttk.Frame(container)
    defs_frame.grid(row=1, column=1, sticky='nsew')
    defs_lb = Listbox(defs_frame, selectmode=SINGLE, height=10, exportselection=False)
    defs_scroll = ttk.Scrollbar(defs_frame, orient=VERTICAL, command=defs_lb.yview)
    defs_lb.configure(yscrollcommand=defs_scroll.set)
    defs_lb.grid(row=0, column=0, sticky='nsew')
    defs_scroll.grid(row=0, column=1, sticky='ns')
    defs_frame.columnconfigure(0, weight=1)

    # populate lists
    def refresh_lists():
        vars_lb.delete(0, END)
        defs_lb.delete(0, END)
        for v in sorted(persisted_vars):
            vars_lb.insert(END, v)
        for d in sorted(persisted_defs):
            defs_lb.insert(END, d)
        _save_symbol_buffers(persisted_vars, persisted_defs)

    refresh_lists()

    # utilities
    ID_RE = re.compile(r'^[A-Za-z_]\w*$')

    def _get_sel(lb):
        sel = lb.curselection()
        if not sel:
            return None, None
        idx = sel[0]
        return idx, lb.get(idx)

    def do_edit(lb, src_set):
        idx, name = _get_sel(lb)
        if not name:
            return
        prompt = f"Edit identifier (current: {name})"
        new = simpledialog.askstring("Edit symbol", prompt, initialvalue=name, parent=dlg)
        if not new or new.strip() == "" or new == name:
            return
        new = new.strip()
        if not ID_RE.match(new):
            messagebox.showerror("Invalid name", "Name must be a valid Python identifier.", parent=dlg)
            return
        # don't allow duplicates across both buffers
        if new in persisted_vars or new in persisted_defs:
            messagebox.showerror("Duplicate", "That identifier already exists.", parent=dlg)
            return
        # perform rename
        try:
            src_set.discard(name)
            src_set.add(new)
        except Exception:
            return
        refresh_lists()
        highlightPythonInitT()

    def do_swap_from_vars():
        idx, name = _get_sel(vars_lb)
        if not name:
            return
        persisted_vars.discard(name)
        persisted_defs.add(name)
        refresh_lists()
        highlightPythonInitT()

    def do_swap_from_defs():
        idx, name = _get_sel(defs_lb)
        if not name:
            return
        persisted_defs.discard(name)
        persisted_vars.add(name)
        refresh_lists()
        highlightPythonInitT()

    def do_delete(lb, src_set):
        idx, name = _get_sel(lb)
        if not name:
            return
        if not messagebox.askyesno("Confirm", f"Delete '{name}'?", parent=dlg):
            return
        src_set.discard(name)
        refresh_lists()
        highlightPythonInitT()

    def do_clear_all():
        if messagebox.askyesno("Confirm", "Clear ALL persisted symbols?", parent=dlg):
            persisted_vars.clear()
            persisted_defs.clear()
            refresh_lists()
            highlightPythonInitT()

    # action buttons for vars
    btns_vars = ttk.Frame(container)
    btns_vars.grid(row=2, column=0, pady=(8, 0), sticky='ew')
    ttk.Button(btns_vars, text="Edit", command=lambda: do_edit(vars_lb, persisted_vars)).pack(side=LEFT, padx=4)
    ttk.Button(btns_vars, text="Swap → Defs", command=do_swap_from_vars).pack(side=LEFT, padx=4)
    ttk.Button(btns_vars, text="Delete", command=lambda: do_delete(vars_lb, persisted_vars)).pack(side=LEFT, padx=4)

    # action buttons for defs
    btns_defs = ttk.Frame(container)
    btns_defs.grid(row=2, column=1, pady=(8, 0), sticky='ew')
    ttk.Button(btns_defs, text="Edit", command=lambda: do_edit(defs_lb, persisted_defs)).pack(side=LEFT, padx=4)
    ttk.Button(btns_defs, text="Swap → Vars", command=do_swap_from_defs).pack(side=LEFT, padx=4)
    ttk.Button(btns_defs, text="Delete", command=lambda: do_delete(defs_lb, persisted_defs)).pack(side=LEFT, padx=4)

    # bottom actions
    action_frame = ttk.Frame(container)
    action_frame.grid(row=3, column=0, columnspan=2, pady=(12, 0), sticky='ew')
    ttk.Button(action_frame, text="Clear All", command=do_clear_all).pack(side=LEFT, padx=4)
    ttk.Button(action_frame, text="Close", command=dlg.destroy).pack(side=RIGHT, padx=4)

    # double-click to edit
    vars_lb.bind("<Double-Button-1>", lambda e: do_edit(vars_lb, persisted_vars))
    defs_lb.bind("<Double-Button-1>", lambda e: do_edit(defs_lb, persisted_defs))

    # keyboard shortcuts
    dlg.bind('<Delete>', lambda e: (do_delete(vars_lb, persisted_vars) if vars_lb.curselection() else do_delete(defs_lb, persisted_defs)))
    dlg.bind('<Escape>', lambda e: dlg.destroy())

    # ensure dialog centered
    dlg.update_idletasks()
    center_window(dlg)


# toolbar
toolBar = Frame(root, bg='blue')
toolBar.pack(side=TOP, fill=X)
# URL history + back/refresh support (in-memory + persisted via funcs)
url_history = funcs.load_url_history(config)  # most-recent-first
_url_history_max = 50
# stack of opened locations for back behavior (push on open)
url_back_stack = []
brainless_mode_var = BooleanVar(value=False)
def _is_likely_url(s: str) -> bool:
    try:
        if not s or not isinstance(s, str):
            return False
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+\-.]*://', s):
            return True
        if s.lower().startswith('www.'):
            return True
        if s.lower().startswith('file:///'):
            return True
        return False
    except Exception:
        return False

def _record_location_opened(loc: str, push_stack: bool = True):
    """Record an opened URL/file into persisted history and back-stack.
    If push_stack is False do not push into back stack (used for programmatic restores).
    """
    try:
        # Session-only override: when user enables Brainless Mode, do not persist or push anything.
        if brainless_mode_var.get():
            return

        if not loc:
            return
        # normalized string
        locs = str(loc)

        # Persist and back-stack ONLY for URLs (do not mix files into URL history)
        try:
            if _is_likely_url(locs):
                try:
                    funcs.add_url_history(config, INI_PATH, locs, max_items=_url_history_max)
                except Exception:
                    pass
                # update in-memory list and UI menu (if exists)
                try:
                    global url_history
                    url_history = funcs.load_url_history(config)
                    update_url_history_menu()
                except Exception:
                    pass
                # back-stack logic (only track URLs)
                if push_stack:
                    try:
                        # avoid consecutive duplicates
                        if not url_back_stack or url_back_stack[-1] != locs:
                            url_back_stack.append(locs)
                        # cap stack size
                        if len(url_back_stack) > (_url_history_max * 2):
                            url_back_stack[:] = url_back_stack[-(_url_history_max * 2):]
                    except Exception:
                        pass
        except Exception:
            pass
    except Exception:
        pass

def _push_back_stack(url: str):
    """Push `url` onto the in-memory back-stack (no persistence) and refresh UI/menu."""
    try:
        if not url or not _is_likely_url(url):
            return
        u = str(url)
        if not url_back_stack or url_back_stack[-1] != u:
            url_back_stack.append(u)
            # cap to sane limit
            if len(url_back_stack) > (_url_history_max * 2):
                url_back_stack[:] = url_back_stack[-(_url_history_max * 2):]
        # immediately refresh history menu / back button state
        try:
            update_url_history_menu()
        except Exception:
            pass
    except Exception:
        pass

def update_url_history_menu():
    """Rebuild the url history dropdown menu from `url_history`."""
    try:
        if not hasattr(globals().get('urlHistoryBtn', None), 'history_menu'):
            return
        menu = urlHistoryBtn.history_menu
        menu.delete(0, END)
        if not url_history:
            menu.add_command(label="(no history)", state='disabled')
        else:
            for u in url_history:
                label = os.path.basename(u) if not _is_likely_url(u) else (u if len(u) <= 60 else u[:56] + '...')
                menu.add_command(label=label, command=lambda uu=u: _open_history_item(uu))
            menu.add_separator()
            menu.add_command(label="Clear History", command=lambda: (funcs.clear_url_history(config, INI_PATH, on_update=update_url_history_menu), update_url_history_menu()))
        # enable/disable back button
        try:
            if url_back_stack and len(url_back_stack) > 1:
                backBtn.config(state=NORMAL)
            else:
                backBtn.config(state=DISABLED)
        except Exception:
            pass
    except Exception:
        pass

def _open_history_item(u: str):
    """Open history item in a new tab (always)."""
    try:
        if not u:
            return
        # open in new tab, prefer URL fetch helper
        try:
            _open_maybe_url(u, open_in_new_tab=True)
        except Exception:
            try:
                # fallback: use fetch helper for URLs
                fetch_and_open_url(u, open_in_new_tab=True)
            except Exception:
                try:
                    _open_path(u, open_in_new_tab=True)
                except Exception:
                    pass
        # record the open (do push to stack)
        _record_location_opened(u, push_stack=True)
    except Exception:
        pass

def _back_action():
    """Go back to previous opened location (open in current tab)."""
    try:
        if not url_back_stack or len(url_back_stack) < 2:
            return
        # pop current
        try:
            url_back_stack.pop()
        except Exception:
            pass
        if not url_back_stack:
            return
        prev = url_back_stack[-1]
        try:
            # Open the previous location WITHOUT recording it again on the back-stack
            _open_maybe_url(prev, open_in_new_tab=False, record_history=False)
        except Exception:
            try:
                fetch_and_open_url(prev, open_in_new_tab=False, record_history=False)
            except Exception:
                try:
                    _open_path(prev, open_in_new_tab=False)
                except Exception:
                    pass
        # do not push the back-open as a duplicate on the stack
    except Exception:
        pass

def _refresh_action():
    """Reload currently visible tab from its source (URL or file)."""
    try:
        fn = getattr(root, 'fileName', '') or ''
        # also prefer frame.fileName when available
        try:
            sel = editorNotebook.select()
            if sel:
                frame = root.nametowidget(sel)
                fn = getattr(frame, 'fileName', fn) or fn
        except Exception:
            pass
        if not fn:
            try:
                statusBar['text'] = "Nothing to refresh."
            except Exception:
                pass
            return
        # if URL -> fetch; if file-like -> open path
        if _is_likely_url(fn) or fn.lower().startswith('http') or fn.lower().startswith('file:///') or fn.lower().startswith('www.'):
            try:
                fetch_and_open_url(fn, open_in_new_tab=False)
            except Exception:
                try:
                    _open_maybe_url(fn, open_in_new_tab=False)
                except Exception:
                    pass
        else:
            try:
                if os.path.isfile(fn):
                    _open_path(fn, open_in_new_tab=False)
                else:
                    # try as file:// URI or fallback to _open_maybe_url
                    _open_maybe_url(fn, open_in_new_tab=False)
            except Exception:
                try:
                    _open_maybe_url(fn, open_in_new_tab=False)
                except Exception:
                    pass
    except Exception:
        pass
# initialize line numbers canvas placeholder
lineNumbersCanvas = None


def init_line_numbers():
    # no-op placeholder: canvases are created per-tab in create_editor_tab
    global lineNumbersCanvas
    lineNumbersCanvas = None

# status bar area (now a frame so we can place a button at lower-right)
statusFrame = Frame(root)
statusFrame.pack(side=BOTTOM, fill=X)

statusBar = Label(statusFrame, text="Ready", bd=1, relief=SUNKEN, anchor=W)
statusBar.pack(side=LEFT, fill=X, expand=True)

# Right-aligned params label (hidden/empty until model is loaded)
paramsLabel = Label(statusFrame, text="", bd=1, relief=SUNKEN, anchor=E)
paramsLabel.pack(side=RIGHT, padx=6)

# placeholder for refresh button (created below near bindings so function names exist)
refreshSyntaxButton = None

# Text area
init_line_numbers()



pairs = {'(': ')', '[': ']', '{': '}', '"': '"', "'": "'"}
IN_CELL_NL = '\u2028'  # internal cell-newline marker (stored inside table cells so real \n doesn't break rows)

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    return funcs._hex_to_rgb(h)

def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return funcs._rgb_to_hex(r, g, b)

_CLS_CLOSEST_COLOR_CACHE: dict[str, str] = {}
# Web-safe component steps (00,33,66,99,CC,FF) produce 216 colors — good compromise between variety & performance.
_WEBSAFE_STEPS = ['00', '33', '66', '99', 'cc', 'ff']
_WEBSAFE_PALETTE = [f"#{r}{g}{b}" for r in _WEBSAFE_STEPS for g in _WEBSAFE_STEPS for b in _WEBSAFE_STEPS]

def _normalize_hex_color(s: str) -> str | None:
    """Normalize input to '#rrggbb' lowercase or return None if invalid-looking."""
    try:
        if not s:
            return None
        s2 = str(s).strip()
        if s2.startswith('#'):
            s2 = s2[1:]
        # allow values like 'fff' or 'ffffff' or with extra whitespace
        if re.fullmatch(r'[0-9A-Fa-f]{3}', s2):
            s2 = ''.join(ch*2 for ch in s2)
        if not re.fullmatch(r'[0-9A-Fa-f]{6}', s2):
            return None
        return f"#{s2.lower()}"
    except Exception:
        return None

def _rgb_distance(a: tuple[int,int,int], b: tuple[int,int,int]) -> int:
    """Squared Euclidean distance (sufficient for nearest color)."""
    try:
        return (a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2
    except Exception:
        return 10**9

def _closest_websafe_color(hexcol: str) -> str:
    """Return the nearest web-safe color string (e.g. '#rrggbb'). Caches results."""
    try:
        if not hexcol:
            return _WEBSAFE_PALETTE[0]
        normalized = _normalize_hex_color(hexcol) or hexcol
        cached = _CLS_CLOSEST_COLOR_CACHE.get(normalized)
        if cached:
            return cached
        try:
            target = _hex_to_rgb(normalized)
        except Exception:
            # fall back to first websafe color
            return _WEBSAFE_PALETTE[0]
        best = None
        bestd = None
        for cand in _WEBSAFE_PALETTE:
            try:
                cr = _hex_to_rgb(cand)
                d = _rgb_distance(target, cr)
                if best is None or d < bestd:
                    best = cand
                    bestd = d
            except Exception:
                continue
        if not best:
            best = _WEBSAFE_PALETTE[0]
        _CLS_CLOSEST_COLOR_CACHE[normalized] = best
        return best
    except Exception:
        return _WEBSAFE_PALETTE[0]

def _safe_tag_config(tw: Text, tag: str, foreground: str | None = None, background: str | None = None):
    """
    Robust wrapper around `Text.tag_config` that:
      - Normalizes hex strings to '#rrggbb'.
      - If Tk rejects a color, substitutes nearest web-safe color.
    """
    try:
        if tw is None:
            return
        kwargs = {}
        if foreground:
            try:
                fg = _normalize_hex_color(foreground) or foreground
                # validate with root.winfo_rgb; if it raises, compute nearest
                try:
                    root.winfo_rgb(fg)
                except Exception:
                    fg = _closest_websafe_color(fg)
                kwargs['foreground'] = fg
            except Exception:
                pass
        if background:
            try:
                bg = _normalize_hex_color(background) or background
                try:
                    root.winfo_rgb(bg)
                except Exception:
                    bg = _closest_websafe_color(bg)
                kwargs['background'] = bg
            except Exception:
                pass
        if kwargs:
            try:
                tw.tag_config(tag, **kwargs)
            except Exception:
                # final fallback: try individual options to avoid a combined failure
                try:
                    if 'foreground' in kwargs:
                        tw.tag_config(tag, foreground=kwargs['foreground'])
                except Exception:
                    pass
                try:
                    if 'background' in kwargs:
                        tw.tag_config(tag, background=kwargs['background'])
                except Exception:
                    pass
    except Exception:
        pass

def _lighten_color(hexcol: str, factor: float = 0.15) -> str:
    return funcs._lighten_color(hexcol, factor)

def _iter_text_widgets():
    """Yield all Text widgets in open editor tabs."""
    out = []
    try:
        for tab_id in editorNotebook.tabs():
            try:
                frame = root.nametowidget(tab_id)
            except Exception:
                continue
            ln = getattr(frame, 'lineNumbersCanvas', None)
            if ln:
                try:
                    ln.config(bg=lineNumberBg)
                except Exception:
                    pass
            # redraw numbers for this tab using the new fg color
            try:
                _draw_line_numbers_for(frame)
            except Exception:
                pass
    except Exception:
        pass

def _apply_tag_configs_to_widget(tw):
    """Apply the same tag configuration used previously on a per-widget basis."""
    try:
        tw.tag_config("number", foreground="#FDFD6A")
        tw.tag_config("selfs", foreground="yellow")
        tw.tag_config("variable", foreground="#8A2BE2")
        tw.tag_config("decorator", foreground="#66CDAA")
        tw.tag_config("class_name", foreground="#FFB86B")
        tw.tag_config("constant", foreground="#FF79C6")
        tw.tag_config("attribute", foreground="#33ccff")
        tw.tag_config("builtin", foreground="#9CDCFE")
        tw.tag_config("def", foreground="orange")
        tw.tag_config("keyword", foreground="red")
        tw.tag_config("string", foreground="#C9CA6B")
        tw.tag_config("operator", foreground="#AAAAAA")
        tw.tag_config("comment", foreground="#75715E")
        tw.tag_config("todo", foreground="#ffffff", background="#B22222")
        try:
            tw.tag_config("marquee", foreground="#FF4500")
            # make marquee low priority so color/style tags can override it
            try:
                tw.tag_lower("marquee")
            except Exception:
                pass
        except Exception:
            pass
        tw.tag_config("bold", font=(fontName, fontSize, "bold"))
        tw.tag_config("italic", font=(fontName, fontSize, "italic"))
        tw.tag_config("underline", font=(fontName, fontSize, "underline"))
        tw.tag_config("all", font=(fontName, fontSize, "bold", "italic", "underline"))
        tw.tag_config("underlineitalic", font=(fontName, fontSize, "italic", "underline"))
        tw.tag_config("boldunderline", font=(fontName, fontSize, "bold", "underline"))
        tw.tag_config("bolditalic", font=(fontName, fontSize, "bold", "italic"))
        try:
            tw.tag_config("currentLine", background=currentLineBg)
        except Exception:
            # fallback to hard-coded default if config value invalid
            try:
                tw.tag_config("currentLine", background="#222222")
            except Exception:
                pass

        # Ensure currentLine sits behind the selection so selection highlight remains visible
        try:
            # Lower the currentLine tag beneath the 'sel' tag (selection). If 'sel' doesn't exist yet this is a no-op.
            tw.tag_lower("currentLine", "sel")
            # Also raise the selection tag to top to be sure it visually wins.
            tw.tag_raise("sel")
        except Exception:
            pass
        tw.tag_config("trailingWhitespace", background="#331111")
        tw.tag_config("find_match", background="#444444", foreground='white')
        # small formatting: reduce font size relative to editor fontSize
        try:
            small_size = max(6, int(fontSize - 2))
            tw.tag_config("small", font=(fontName, small_size))
        except Exception:
            pass

        # mark/code/kbd: prefer colors from Syntax config, fallback to _DEFAULT_TAG_COLORS defaults
        try:
            def _cfg_tag_values(tag):
                fg_cfg = config.get('Syntax', f'tag.{tag}.fg', fallback='').strip() if config and config.has_section('Syntax') else ''
                bg_cfg = config.get('Syntax', f'tag.{tag}.bg', fallback='').strip() if config and config.has_section('Syntax') else ''
                if not fg_cfg:
                    fg_cfg = _DEFAULT_TAG_COLORS.get(tag, {}).get('fg', '') or ''
                if not bg_cfg:
                    bg_cfg = _DEFAULT_TAG_COLORS.get(tag, {}).get('bg', '') or ''
                return (fg_cfg or None, bg_cfg or None)

            # mark
            m_fg, m_bg = _cfg_tag_values('mark')
            kwargs = {}
            if m_fg:
                kwargs['foreground'] = m_fg
            if m_bg:
                kwargs['background'] = m_bg
            if kwargs:
                tw.tag_config("mark", **kwargs)

            # code / kbd: enforce monospace font and configurable colors
            mono_font = ("Courier New", max(6, int(fontSize - 1)))
            for t in ('code', 'kbd'):
                fg, bg = _cfg_tag_values(t)
                cfg = {'font': mono_font}
                if fg:
                    cfg['foreground'] = fg
                if bg:
                    cfg['background'] = bg
                try:
                    tw.tag_config(t, **cfg)
                except Exception:
                    pass
        except Exception:
            pass

        # HTML-specific visual tags
        try:
            tw.tag_config("html_tag", foreground=_DEFAULT_TAG_COLORS["html_tag"]["fg"])
            tw.tag_config("html_attr", foreground=_DEFAULT_TAG_COLORS["html_attr"]["fg"])
            tw.tag_config("html_attr_value", foreground=_DEFAULT_TAG_COLORS["html_attr_value"]["fg"])
            tw.tag_config("html_comment", foreground=_DEFAULT_TAG_COLORS["html_comment"]["fg"])
            # ensure html_comment sits below other presentational tags so it retains comment look
            try:
                tw.tag_lower("html_comment")
            except Exception:
                pass
        except Exception:
            pass

        # Basic table/list visual styling so parsed tags are visible in editor
        try:
            # table container (no strong visual, but ensures presence)
            tw.tag_config("table", lmargin1=0, lmargin2=0)
            # each row starts on its own line (parser already inserted newlines)
            tw.tag_config("tr", lmargin1=0, lmargin2=0)

            # Compute a complimentary background for table cells:
            # - Use editor fontColor as base; compute simple RGB complement.
            # - If the computed color equals the overall background, nudge it slightly.
            def _compute_complementary(hexcol: str, fallback: str = "#F8F8F8") -> str:
                """Wrapper to the functions module; passes editor background for nudging."""
                return funcs._compute_complementary(hexcol, fallback, bg_hex=backgroundColor)

            try:
                # Make cell background several shades lighter than editor background
                base_bg = (backgroundColor or "#ffffff").strip() or "#ffffff"
                # apply a small incremental lighten (approx 3-4 subtle steps)
                td_bg = _lighten_color(base_bg, 0.18)
            except Exception:
                td_bg = "#F8F8F8"
            # cell styling: use complimentary background for table cells
            try:
                tw.tag_config("td", background=td_bg)
            except Exception:
                pass
            # header cell: bold + slightly darker background
            tw.tag_config("th", background=_lighten_color(base_bg, 0.08), font=(fontName, fontSize, "bold"))
            # lists: indent and slightly different margin
            tw.tag_config("li", lmargin1=20, lmargin2=20)
            tw.tag_config("ul", lmargin1=12, lmargin2=12)
            tw.tag_config("ol", lmargin1=12, lmargin2=12)

            try:
                bg_contrast = _contrast_text_color(base_bg)
                sep_color = "#000000" if bg_contrast == "#FFFFFF" else "#FFFFFF"
                # set both foreground and background so the tab slot appears as a solid block
                tw.tag_config("table_sep", foreground=sep_color, background=sep_color)
                # ensure separator displays above td backgrounds
                try:
                    tw.tag_raise("table_sep", "td")
                except Exception:
                    try:
                        tw.tag_raise("table_sep")
                    except Exception:
                        pass
            except Exception:
                pass

        except Exception:
            pass

        # hyperlink tag: blue + underline and mouse bindings to open link
        try:
            tw.tag_config("hyperlink", foreground="#0000EE", underline=True)
            # Ensure per-widget hyperlink mapping exists (used by click handler)
            if not hasattr(tw, '_hyperlink_map'):
                tw._hyperlink_map = {}
            def _resolve_href_for_index(w, idx):
                try:
                    rngs = w.tag_ranges('hyperlink')
                    for i in range(0, len(rngs), 2):
                        s = rngs[i]
                        e = rngs[i + 1]
                        if w.compare(s, '<=', idx) and w.compare(idx, '<', e):
                            key = (str(s), str(e))
                            entry = getattr(w, '_hyperlink_map', {}).get(key)
                            if entry:
                                if isinstance(entry, dict):
                                    return entry.get('href'), entry.get('title') or entry.get('text')
                                return str(entry), None
                            # fallback to visible text
                            try:
                                return w.get(s, e).strip(), None
                            except Exception:
                                return None, None
                except Exception:
                    pass
                return None, None
            # Mouse handlers for hyperlink tag (show hand cursor, open URL on click)
            def _on_hyper_enter(event):
                try:
                    w = event.widget
                    idx = w.index(f"@{event.x},{event.y}")
                    href, title = _resolve_href_for_index(w, idx)
                    # store previous status so we can restore on leave
                    try:
                        w._last_status_text = statusBar['text']
                    except Exception:
                        w._last_status_text = None
                    if href:
                        disp = href if not title else f"{title} → {href}"
                        try:
                            statusBar['text'] = disp
                        except Exception:
                            pass
                    try:
                        w.config(cursor='hand2')
                    except Exception:
                        pass
                except Exception:
                    pass

            def _on_hyper_leave(event):
                try:
                    w = event.widget
                    try:
                        prev = getattr(w, '_last_status_text', None)
                        if prev is not None:
                            statusBar['text'] = prev
                        else:
                            # fallback to showing caret position
                            update_status_bar()
                    except Exception:
                        try:
                            update_status_bar()
                        except Exception:
                            pass
                    try:
                        w.config(cursor='')
                    except Exception:
                        pass
                except Exception:
                    pass

            def _on_hyper_click(event):
                try:
                    w = event.widget
                    # get index under mouse
                    idx = w.index(f"@{event.x},{event.y}")
                    # find hyperlink span that contains this index
                    rngs = w.tag_ranges('hyperlink')
                    for i in range(0, len(rngs), 2):
                        s = rngs[i]
                        e = rngs[i + 1]
                        if w.compare(s, '<=', idx) and w.compare(idx, '<', e):
                            key = (str(s), str(e))
                            entry = getattr(w, '_hyperlink_map', {}).get(key)
                            href = None
                            if entry:
                                if isinstance(entry, dict):
                                    href = entry.get('href')
                                else:
                                    href = str(entry)
                            # fallback: use visible text if mapping missing
                            if not href:
                                try:
                                    href = w.get(s, e).strip()
                                except Exception:
                                    href = None
                            if href:
                                # Prefer intelligent open helper; fall back to fetch helper
                                try:
                                    statusBar['text'] = f"Opening: {href}"
                                except Exception:
                                    pass

                                # RECORD current location before navigating so Back becomes available immediately
                                try:
                                    sel = editorNotebook.select()
                                    prev = ''
                                    if sel:
                                        frame = root.nametowidget(sel)
                                        prev = getattr(frame, 'fileName', '') or getattr(root, 'fileName', '') or ''
                                    else:
                                        prev = getattr(root, 'fileName', '') or ''
                                   # push previous URL onto in-memory back-stack immediately (no persistence) so UI enables
                                    try:
                                        _record_location_opened(prev, push_stack=True)
                                    except Exception:
                                        pass
                                except Exception:
                                    pass

                                # Optimistically push the clicked target onto the back-stack
                                try:
                                    if href:
                                        _push_back_stack(href)
                                except Exception:
                                    pass

                                try:
                                    _open_maybe_url(href, open_in_new_tab=False)
                                except Exception:
                                    try:
                                        fetch_and_open_url(href, open_in_new_tab=False)
                                    except Exception:
                                        pass
                            break
                except Exception:
                    pass

            try:
                tw.tag_bind('hyperlink', '<Enter>', _on_hyper_enter)
                tw.tag_bind('hyperlink', '<Leave>', _on_hyper_leave)
                tw.tag_bind('hyperlink', '<Button-1>', _on_hyper_click)
            except Exception:
                pass
        except Exception:
            pass

    except Exception:
        pass

def _find_tag_range_at_index(widget: Text, idx: str, tag_name: str):
    """Return (start_index_str, end_index_str) if idx falls inside a tag range for tag_name, otherwise (None, None)."""
    try:
        rngs = widget.tag_ranges(tag_name)
        for i in range(0, len(rngs), 2):
            s = rngs[i]
            e = rngs[i+1]
            if widget.compare(s, "<=", idx) and widget.compare(idx, "<", e):
                return str(s), str(e)
    except Exception:
        pass
    return None, None

def _table_sync_column_at_index(widget: Text, idx: str):
    """Ensure the column containing idx has uniform first-line widths across rows by padding cells with spaces.

    Best-effort only: pads shorter first-lines in the same column so tab offsets remain aligned.
    """
    try:
        # find encompassing table range
        tstart, tend = _find_tag_range_at_index(widget, idx, 'table')
        if not tstart or not tend:
            return

        # get table text and base offset
        table_text = widget.get(tstart, tend)
        if not table_text:
            return
        base_off = len(widget.get('1.0', tstart))

        rows = table_text.split('\n')
        # determine column index of cursor within its row
        # compute cursor absolute offset within table
        cursor_abs = len(widget.get('1.0', widget.index(idx))) - base_off
        # locate row and cell containing cursor by walking the table string
        cum = 0
        cursor_row = None
        for r_i, r in enumerate(rows):
            row_len = len(r)
            if cum <= cursor_abs <= cum + row_len:
                cursor_row = r_i
                offset_in_row = cursor_abs - cum
                break
            cum += row_len + 1  # +1 for the newline
        if cursor_row is None:
            return
        # find column index by counting tabs in the row up to offset_in_row
        cur_row_cells = rows[cursor_row].split('\t')
        col_index = 0
        running = 0
        for ci, ctext in enumerate(cur_row_cells):
            running += len(ctext)
            if offset_in_row <= running:
                col_index = ci
                break
            # account for tab separator
            running += 1  # the tab char
            col_index = ci + 1

        # collect first-line lengths per row for this column and compute insert operations needed
        first_line_lens = []
        ops = []  # list of (abs_offset, text_to_insert)
        table_cursor = 0
        for r_idx, row in enumerate(rows):
            cells = row.split('\t')
            if col_index >= len(cells):
                first_line_lens.append(0)
                table_cursor += len(row) + 1
                continue
            cell = cells[col_index]
            # interpret internal marker as newline for first-line measurement
            first_line = cell.replace(IN_CELL_NL, '\n').split('\n')[0] if cell else ''
            first_line_lens.append(len(first_line))
            table_cursor += len(row) + 1

        if not first_line_lens:
            return

        target_max = max(first_line_lens)

        # if nothing to pad, exit
        if target_max <= 0:
            return

        # now compute where to insert padding for each row that is short
        # iterate rows again to compute precise cell start offsets
        abs_cursor = 0  # offset inside table_text
        for r_idx, row in enumerate(rows):
            row_start_off = abs_cursor
            cells = row.split('\t')
            # compute cell start offset by summing preceding cells+tabs
            cell_start_off = row_start_off
            for ci in range(min(col_index, len(cells))):
                cell_start_off += len(cells[ci]) + 1  # +1 for the tab
            if col_index >= len(cells):
                abs_cursor += len(row) + 1
                continue
            cell_text = cells[col_index]
            # find end of first-line inside this cell (either IN_CELL_NL or true end)
            repl = cell_text
            nl_pos = repl.find(IN_CELL_NL)
            if nl_pos >= 0:
                first_line_len = nl_pos
                insert_pos_in_cell = nl_pos  # insert before the marker so visual first-line padded
            else:
                # no internal marker; first line is the entire cell (we want to pad before the tab or row end)
                first_line_len = len(repl)
                insert_pos_in_cell = first_line_len
            cur_len = first_line_lens[r_idx]
            if cur_len < target_max:
                pad = target_max - cur_len
                abs_insert_off = base_off + cell_start_off + insert_pos_in_cell
                ops.append((abs_insert_off, ' ' * pad))
            abs_cursor += len(row) + 1

        if not ops:
            return

        # apply operations from highest offset to lowest so earlier inserts don't shift later offsets
        ops.sort(key=lambda x: x[0], reverse=True)
        for off, txt in ops:
            try:
                pos = widget.index(f"1.0 + {off}c")
                widget.insert(pos, txt)
            except Exception:
                pass

        # refresh visual tags & highlighting
        safe_highlight_event(None)
    except Exception:
        pass

def _table_live_adjust(event=None):
    """KeyRelease handler wrapper — only act when editing inside a table and when printable keys or deletes occur."""
    try:
        w = event.widget if hasattr(event, 'widget') else textArea
        if not isinstance(w, Text):
            return
        # cheap filter: only run on likely content keys to reduce churn
        ks = getattr(event, 'keysym', '') or ''
        ch = getattr(event, 'char', '')
        interesting = False
        if ch and (ch.isprintable() or ch.isspace()):
            interesting = True
        if ks in ('BackSpace', 'Delete'):
            interesting = True
        if not interesting:
            return
        idx = w.index('insert')
        # only run if cursor inside a table tag
        tstart, tend = _find_tag_range_at_index(w, idx, 'table')
        if not tstart:
            return
        _table_sync_column_at_index(w, idx)
    except Exception:
        pass

def _text_area_return(event):
    """Return handler for main Text widget: when inside a table cell insert an in-cell newline marker
    instead of breaking the table. Otherwise perform normal smart newline behavior."""
    try:
        w = event.widget
        if not isinstance(w, Text):
            return
        idx = w.index('insert')
        # if cursor is inside a td range, insert internal marker and keep table intact
        tags_here = w.tag_names(idx)
        if 'td' in tags_here:
            try:
                w.insert(idx, IN_CELL_NL)
                # move caret after inserted marker
                w.mark_set('insert', f"{idx} + 1c")
                # reapply a small visual highlight update
                safe_highlight_event(None)
            except Exception:
                pass
            return 'break'
        # otherwise default behavior: smart newline + UI refresh
        try:
            smart_newline(event)
        except Exception:
            pass
        try:
            safe_highlight_event(event)
        except Exception:
            pass
        return 'break'
    except Exception:
        return None

def reflow_numbered_lists():
    """Renumber ordered lists (lines starting with digits + '. ') across the current buffer.

    Finds contiguous runs of lines that look like ordered-list items and renumbers them from 1
    (preserving indentation and trailing text). Works on the active textArea and preserves tags
    as best-effort by using _replace_region_preserve_tags on the whole buffer.
    """
    try:
        if not textArea:
            return
        content = textArea.get('1.0', 'end-1c')
        if not content:
            return

        lines = content.splitlines()
        out_lines = []
        i = 0
        ordered_re = re.compile(r'^(\s*)(\d+)\.\s+(.*)$')
        while i < len(lines):
            m = ordered_re.match(lines[i])
            if not m:
                out_lines.append(lines[i])
                i += 1
                continue

            # Start of an ordered block
            indent = m.group(1)
            block_start = i
            seq = []
            # collect contiguous lines that match same indent (or deeper nested with same indent prefix)
            while i < len(lines):
                mm = ordered_re.match(lines[i])
                if not mm:
                    break
                # require identical indentation for simple reflow; preserve nested blocks separately
                if mm.group(1) != indent:
                    break
                seq.append(mm.group(3))  # store the item text only
                i += 1

            # Renumber collected sequence starting at 1
            for idx, item_text in enumerate(seq, start=1):
                out_lines.append(f"{indent}{idx}. {item_text}")
        new_content = "\n".join(out_lines)

        # If nothing changed, do nothing
        if new_content == content:
            return

        # Replace whole buffer while preserving tags where possible
        try:
            _replace_region_preserve_tags('1.0', 'end-1c', new_content)
        except Exception:
            # fallback: plain replace
            try:
                textArea.delete('1.0', 'end')
                textArea.insert('1.0', new_content)
            except Exception:
                pass

        # Refresh UI
        safe_highlight_event(None)
    except Exception:
        pass

def _on_text_right_click(event):
    """Show context menu if right-click is over a table range; otherwise default selection menu."""
    try:
        w = event.widget
        if not isinstance(w, Text):
            return
        idx = w.index(f"@{event.x},{event.y}")
        tstart, tend = _find_tag_range_at_index(w, idx, 'table')
        # build context menu
        menu = Menu(root, tearoff=0)

        # Always provide Find/Replace in context menu
        try:
            menu.add_command(label="Find/Replace...", command=lambda: open_find_replace())
            menu.add_separator()
        except Exception:
            pass

        # Add Table option (insert at cursor)
        try:
            menu.add_command(label="Add Table...", command=lambda w=w: open_table_editor(w, None, None))
            menu.add_separator()
        except Exception:
            pass

        if tstart and tend:
            menu.add_command(label="Edit table...", command=lambda s=tstart, e=tend, w=w: open_table_editor(w, s, e))
            menu.add_separator()

        # Reflow numbered lists for current buffer (best-effort)
        try:
            menu.add_command(label="Reflow numbered lists", command=lambda: reflow_numbered_lists())
            menu.add_separator()
        except Exception:
            pass

        # If selection contains an ordered-list block, offer reorder-selection
        try:
            sel = w.tag_ranges('sel')
            sel_has_ordered = False
            if sel and len(sel) >= 2:
                sel_text = w.get(sel[0], sel[1])
                if re.search(r'^\s*\d+\.\s+', sel_text, flags=re.MULTILINE):
                    sel_has_ordered = True
            else:
                # check current line
                cur_line_text = w.get(f"{w.index('insert').split('.')[0]}.0", f"{w.index('insert').split('.')[0]}.0 lineend")
                if re.match(r'^\s*\d+\.\s+', cur_line_text):
                    sel_has_ordered = True
            if sel_has_ordered:
                menu.add_command(label="Reorder selection", command=lambda: reorder_selection())
                menu.add_separator()
        except Exception:
            pass

        # fallback items (cut/copy/paste) kept minimal
        try:
            menu.add_separator()
            menu.add_command(label="Cut", command=lambda: cut_selected_text())
            menu.add_command(label="Copy", command=lambda: copy_to_clipboard())
            menu.add_command(label="Paste", command=lambda: paste_from_clipboard())
        except Exception:
            pass
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    except Exception:
        pass

def open_table_editor(widget: Text, start_idx: str, end_idx: str):
    """Open a grid editor for a table region. On save, replace region and reapply table/tr/td tags.
    If start_idx == end_idx == None the dialog will operate in 'insert at cursor' mode (Add Table)."""
    try:
        insert_mode = False
        if not start_idx or not end_idx:
            # create blank default 3x3 table
            grid = [['' for _ in range(3)] for _ in range(3)]
            insert_mode = True
            s_norm = None
            e_norm = None
        else:
            # normalize indices and extract text
            s_norm = widget.index(start_idx)
            e_norm = widget.index(end_idx)
            content = widget.get(s_norm, e_norm)
            rows = [r for r in content.split('\n')]
            grid = [r.split('\t') for r in rows]

        dlg = Toplevel(root)
        dlg.transient(root)
        dlg.grab_set()
        dlg.title("Edit Table")
        frm = ttk.Frame(dlg, padding=6) if 'ttk' in globals() else Frame(dlg)
        frm.pack(fill=BOTH, expand=True)

        # dynamic grid of Entry widgets
        entries = [ [None]*max(1, len(grid[0])) for _ in range(max(1, len(grid))) ]

        # Heuristic: if the first cell starts with a single accidental leading space,
        # remove that single space when populating the editor so the dialog doesn't show the spurious space.
        # Only strip a single leading space on row=0,col=0 to avoid changing intentional leading whitespace elsewhere.
        def _sanitize_initial_grid(g):
            try:
                if not g or not g[0]:
                    return g
                if len(g) >= 1 and len(g[0]) >= 1:
                    first = g[0][0]
                    # convert any stored in-cell newline markers back to real newlines for editing
                    if isinstance(first, str) and IN_CELL_NL in first:
                        g[0][0] = first.replace(IN_CELL_NL, '\n')
                    if isinstance(g[0][0], str):
                        first = g[0][0]
                        if first.startswith(' ') and not first.startswith('  '):
                            g[0][0] = first[1:]
                # also ensure any other cells replace IN_CELL_NL with real newlines
                for r in range(len(g)):
                    for c in range(len(g[r])):
                        if isinstance(g[r][c], str) and IN_CELL_NL in g[r][c]:
                            g[r][c] = g[r][c].replace(IN_CELL_NL, '\n')
                return g
            except Exception:
                return g

        grid = _sanitize_initial_grid(grid)

        def rebuild_grid(container, grid_data):
            # destroy existing children
            for child in container.winfo_children():
                child.destroy()
            rows = len(grid_data)
            cols = max(len(r) for r in grid_data) if rows else 0
            # ensure entries matrix matches grid size
            nonlocal entries
            entries = [ [None]*cols for _ in range(rows) ]
            for r in range(rows):
                for c in range(cols):
                    val = grid_data[r][c] if c < len(grid_data[r]) else ''
                    ent = Entry(container, width=max(10, max(10, len(val.splitlines()[0]) + 2 if val else 10)))
                    ent.grid(row=r, column=c, padx=2, pady=2, sticky='nsew')
                    # insert the single-line representation (internal newlines shown as literal newlines aren't supported in Entry)
                    # we preserve actual newlines by replacing them with a visible placeholder in the Entry UI (join with ' ↵ ').
                    if isinstance(val, str) and '\n' in val:
                        display = val.replace('\n', ' ↵ ')
                    else:
                        display = val
                    ent.insert(0, display)
                    entries[r][c] = ent
                # separator columns (visual black bar) as Labels (one per gap between columns)
                # place separators to the right of each column except last
                for c in range(cols - 1):
                    sep = Label(container, width=1, relief='flat', bd=0)
                    # color configured later via tag; here choose black/white based on editor bg
                    bg_contrast = _contrast_text_color(backgroundColor or "#ffffff")
                    sep_color = "#FFFFFF" if bg_contrast == "#FFFFFF" else "#000000"
                    sep.config(bg=sep_color)
                    # place separator in a separate grid column (interleaving is easier done by placing separators in same column index with sticky)
                    # We'll put separators using grid on the same column with sticky so they appear between entries visually.
                    # To keep things simple we won't create extra columns; visual separators rely on spacing between entries.
                    # (This label helps show a visual column border in the editor dialog.)
                    sep.grid(row=r, column=cols + c + 1, padx=0, pady=2, sticky='ns')
                # make columns expand equally
                for c in range(cols):
                    container.grid_columnconfigure(c, weight=1)

            # bind key handlers after rebuild so we can adjust widths live
            for cc in range(cols):
                def make_handler(col):
                    return lambda e: _sync_column_widths(col)
                for rr in range(rows):
                    ent = entries[rr][cc]
                    if ent:
                        ent.bind('<KeyRelease>', make_handler(cc), add=False)

            # sync initial widths
            for ccol in range(cols):
                _sync_column_widths(ccol)

        def _sync_column_widths(col_index: int):
            """Compute max visible length in a column and set each Entry width to match."""
            try:
                if not entries or col_index < 0:
                    return
                maxlen = 0
                rows_count = len(entries)
                for r in range(rows_count):
                    try:
                        ent = entries[r][col_index]
                        if not ent:
                            continue
                        txt = ent.get() or ''
                        # consider the visible representation length (replace internal ↵ with single char)
                        txt_len = max(len(part) for part in txt.replace(' ↵ ', '\n').splitlines()) if txt else 0
                        if txt_len > maxlen:
                            maxlen = txt_len
                    except Exception:
                        pass
                new_w = max(10, maxlen + 2)
                for r in range(rows_count):
                    try:
                        ent = entries[r][col_index]
                        if ent:
                            ent.config(width=new_w)
                    except Exception:
                        pass
            except Exception:
                pass

        # initialize entries structure sized to grid
        rows_init = max(1, len(grid))
        cols_init = max(1, max((len(r) for r in grid), default=1))
        entries = [ [None]*cols_init for _ in range(rows_init) ]
        rebuild_grid(frm, grid)

        # allow inserting/removing rows/cols controls (minimal)
        ctl = Frame(dlg)
        ctl.pack(fill=X, pady=(6,0))
        # control actions
        def add_row():
            rcount = len(entries)
            ccount = len(entries[0]) if entries else 1
            for r in entries:
                # ensure each row has same length
                while len(r) < ccount:
                    r.append(None)
            entries.append([None]*ccount)
            rebuild_grid(frm, [[entries[r][c].get() if entries[r][c] else '' for c in range(len(entries[0]))] for r in range(len(entries))])

        def remove_row():
            if len(entries) <= 1:
                return
            entries.pop()
            rebuild_grid(frm, [[entries[r][c].get() if entries[r][c] else '' for c in range(len(entries[0]))] for r in range(len(entries))])

        def add_col():
            for row in entries:
                row.append(None)
            rebuild_grid(frm, [[entries[r][c].get() if entries[r][c] else '' for c in range(len(entries[0]))] for r in range(len(entries))])

        def remove_col():
            if not entries or len(entries[0]) <= 1:
                return
            for row in entries:
                row.pop()
            rebuild_grid(frm, [[entries[r][c].get() if entries[r][c] else '' for c in range(len(entries[0]))] for r in range(len(entries))])

        # row/col controls
        def do_save():
            try:
                # reconstruct table text with tabs/newlines from current entries
                new_rows = []
                # gather values into a 2D list and compute column widths
                grid_vals = []
                for r in range(len(entries)):
                    row_vals = []
                    for c in range(len(entries[0])):
                        ent = entries[r][c]
                        val = ent.get() if ent else ''
                        # restore internal newline markers if the user used the visible ↵ marker
                        if ' ↵ ' in val:
                            val = val.replace(' ↵ ', '\n')
                        # Replace real newlines with internal marker so rows remain row-delimited in main Text widget
                        if '\n' in val:
                            val = val.replace('\n', IN_CELL_NL)
                        row_vals.append(val)
                    grid_vals.append(row_vals)

                # compute max width per column (characters)
                max_cols = max(len(row) for row in grid_vals) if grid_vals else 0
                col_widths = [0] * max_cols
                for row in grid_vals:
                    for ci in range(max_cols):
                        text = row[ci] if ci < len(row) else ''
                        # measure by longest line inside the cell (account for internal markers)
                        parts = text.replace(IN_CELL_NL, '\n').splitlines()
                        longest = max((len(p) for p in parts), default=0)
                        col_widths[ci] = max(col_widths[ci], longest)

                # pad cells to uniform widths so visual wrapping is consistent across rows
                for row in grid_vals:
                    padded_cells = []
                    for ci in range(max_cols):
                        text = row[ci] if ci < len(row) else ''
                        padded = text
                        # pad the first line so column alignment is preserved visually
                        parts = padded.replace(IN_CELL_NL, '\n').splitlines()
                        if parts:
                            parts[0] = parts[0].ljust(col_widths[ci])
                        else:
                            parts = [''.ljust(col_widths[ci])]
                        # rejoin using internal marker so the main buffer doesn't get real newlines inside cells
                        padded = IN_CELL_NL.join(parts)
                        padded_cells.append(padded)
                    new_rows.append('\t'.join(padded_cells))

                new_text = '\n'.join(new_rows)

                if insert_mode:
                    # insert at current cursor
                    ins_idx = widget.index('insert')
                    abs_start_off = len(widget.get('1.0', ins_idx))
                    widget.insert(ins_idx, new_text)
                    ins_start_idx = ins_idx
                else:
                    # replace region in widget
                    widget.delete(s_norm, e_norm)
                    widget.insert(s_norm, new_text)
                    abs_start_off = len(widget.get('1.0', s_norm))
                    ins_start_idx = s_norm
                # remove any existing table tags in the affected region
                try:
                    start_idx = ins_start_idx
                    end_idx = widget.index(f"{start_idx} + {len(new_text)}c")
                    for t in ('table','tr','td','th','table_sep'):
                        widget.tag_remove(t, start_idx, end_idx)
                except Exception:
                    pass
                # add new tags based on new_text geometry
                cursor_off = 0
                for r_idx, line in enumerate(new_rows):
                    row_start_off = abs_start_off + cursor_off
                    cells = line.split('\t')
                    # compute row_end_off once
                    row_end_off = row_start_off + len(line)
                    cell_cursor = row_start_off
                    for c_idx, cell_text in enumerate(cells):
                        cs = cell_cursor
                        ce = cs + len(cell_text)
                        # Add td background: include the separator (tab) so background fills cell area
                        if c_idx < len(cells) - 1:
                            ce_display = ce + 1  # include tab
                        else:
                            ce_display = row_end_off
                        # add td tag
                        try:
                            widget.tag_add('td', f"1.0 + {cs}c", f"1.0 + {ce_display}c")
                        except Exception:
                            pass
                        # add a visual separator tag on the tab char (if present)
                        if c_idx < len(cells) - 1:
                            try:
                                sep_offset = ce  # the tab character offset
                                widget.tag_add('table_sep', f"1.0 + {sep_offset}c", f"1.0 + {sep_offset + 1}c")
                            except Exception:
                                pass
                        # advance: account for tab char between cells (the stored new_rows include tabs)
                        cell_cursor = ce + 1
                    # add tr tag for the whole row
                    try:
                        widget.tag_add('tr', f"1.0 + {row_start_off}c", f"1.0 + {row_end_off}c")
                    except Exception:
                        pass
                    cursor_off += len(line) + 1  # plus newline
                # add table tag covering whole inserted region
                try:
                    widget.tag_add('table', ins_start_idx, f"1.0 + {abs_start_off + len(new_text)}c")
                except Exception:
                    pass
                # apply visual configs to ensure tags show
                _apply_tag_configs_to_widget(widget)
                # re-highlight and refresh
                safe_highlight_event(None)
            except Exception:
                pass
            finally:
                try:
                    dlg.grab_release()
                except Exception:
                    pass
                dlg.destroy()

        def do_cancel():
            try:
                dlg.grab_release()
            except Exception:
                pass
            dlg.destroy()

        Button(ctl, text="Save", command=do_save).pack(side=RIGHT, padx=6)
        Button(ctl, text="Cancel", command=do_cancel).pack(side=RIGHT)
        # Add row/col controls left of Save/Cancel
        Frame(ctl).pack(side=LEFT, expand=True)
        btn_add_row = Button(ctl, text="Add Row", command=add_row)
        btn_add_row.pack(side=LEFT, padx=4)
        btn_remove_row = Button(ctl, text="Remove Row", command=remove_row)
        btn_remove_row.pack(side=LEFT, padx=4)
        btn_add_col = Button(ctl, text="Add Col", command=add_col)
        btn_add_col.pack(side=LEFT, padx=4)
        btn_remove_col = Button(ctl, text="Remove Col", command=remove_col)
        btn_remove_col.pack(side=LEFT, padx=4)
        # ensure dialog sized sensibly
        dlg.update_idletasks()
        center_window(dlg)
        dlg.focus_force()
    except Exception:
        pass

def reorder_selection():
    """Renumber ordered list items inside current selection (or current paragraph/lines if no selection)."""
    try:
        if not textArea:
            return
        # determine region: use selection if present, otherwise current line or contiguous ordered-block around cursor
        sel = textArea.tag_ranges('sel')
        if sel and len(sel) >= 2:
            s_idx = sel[0]
            e_idx = sel[1]
        else:
            # select current contiguous block of lines around cursor
            cur_line = int(textArea.index('insert').split('.')[0])
            # expand up
            start_line = cur_line
            while start_line > 1:
                line_text = textArea.get(f"{start_line-1}.0", f"{start_line-1}.0 lineend")
                if re.match(r'^\s*\d+\.\s+', line_text):
                    start_line -= 1
                else:
                    break
            # expand down
            end_line = cur_line
            max_line = int(textArea.index('end-1c').split('.')[0])
            while end_line < max_line:
                line_text = textArea.get(f"{end_line+1}.0", f"{end_line+1}.0 lineend")
                if re.match(r'^\s*\d+\.\s+', line_text):
                    end_line += 1
                else:
                    break
            s_idx = f"{start_line}.0"
            e_idx = f"{end_line}.0 lineend"
        # get text and split lines
        block = textArea.get(s_idx, e_idx)
        lines = block.splitlines()
        ordered_re = re.compile(r'^(\s*)(\d+)\.\s+(.*)$')
        # detect whether there is at least one ordered line
        has_ordered = any(ordered_re.match(l) for l in lines)
        if not has_ordered:
            return
        # renumber contiguous ordered sub-blocks inside selection separately
        out_lines = []
        i = 0
        while i < len(lines):
            m = ordered_re.match(lines[i])
            if not m:
                out_lines.append(lines[i])
                i += 1
                continue
            # collect contiguous same-indent block
            indent = m.group(1)
            seq = []
            while i < len(lines):
                mm = ordered_re.match(lines[i])
                if not mm or mm.group(1) != indent:
                    break
                seq.append(mm.group(3))
                i += 1
            for idx, item in enumerate(seq, start=1):
                out_lines.append(f"{indent}{idx}. {item}")
        new_block = "\n".join(out_lines)
        # replace region preserving tags if possible
        try:
            _replace_region_preserve_tags(s_idx, e_idx, new_block)
        except Exception:
            textArea.delete(s_idx, e_idx)
            textArea.insert(s_idx, new_block)
        safe_highlight_event(None)
    except Exception:
        pass

def auto_pair(event):
    ch = event.char
    if ch in pairs:
        sel = textArea.tag_ranges('sel')
        if sel:
            start, end = sel
            inside = textArea.get(start, end)
            textArea.delete(start, end)
            textArea.insert(start, ch + inside + pairs[ch])
            textArea.mark_set('insert', f"{start}+{len(ch) + len(inside)}c")
        else:
            textArea.insert('insert', ch + pairs[ch])
            textArea.mark_set('insert', 'insert-1c')
        return 'break'
def _configure_text_widget(tw):
    """Configure an individual Text widget to match editor defaults and bindings."""
    try:
        tw.config(insertbackground=cursorColor, undo=undoSetting, bg=backgroundColor, fg=fontColor, font=(fontName, fontSize))
    except Exception:
        pass

    # event bindings (same behavior as before) -- bound per-widget
    for k in ['(', '[', '{', '"', "'"]:
        tw.bind(k, auto_pair)
    tw.bind('<Return>', lambda e: _text_area_return(e))
    tw.bind(
        '<KeyRelease>',
        lambda e: (
            _table_live_adjust(e),
            safe_highlight_event(e),
            detect_header_and_prompt(e),
            highlight_current_line(),
            redraw_line_numbers(),
            update_status_bar(),
            show_trailing_whitespace()
        )
    )
    tw.bind('<Button-1>', lambda e: tw.after_idle(lambda: (safe_highlight_event(e), highlight_current_line(), redraw_line_numbers(), update_status_bar(), show_trailing_whitespace())))
    tw.bind('<MouseWheel>', lambda e: (safe_highlight_event(e), redraw_line_numbers(), show_trailing_whitespace()))
    tw.bind('<Button-4>', lambda e: (redraw_line_numbers(), show_trailing_whitespace(), safe_highlight_event(e)), add=False)
    tw.bind('<Button-5>', lambda e: (redraw_line_numbers(), show_trailing_whitespace(), safe_highlight_event(e)), add=False)
    tw.bind('<Configure>', lambda e: (redraw_line_numbers(), show_trailing_whitespace()))
    # right-click context for table editing
    try:
        tw.bind('<Button-3>', _on_text_right_click, add=True)
    except Exception:
        pass

def create_editor_tab(title='Untitled', content='', filename=''):
    """Create a new tab containing a Text widget and return (text_widget, frame)."""
    frame = Frame(editorNotebook)
    frame.pack(fill=BOTH, expand=True)

    # initialize per-tab template-prompt flags so we don't repeatedly ask
    frame._template_prompted_html = False
    frame._template_prompted_py = False
    frame._template_prompted_md = False
    frame._template_prompted_json = False
    frame._opened_as_source = False
    frame._view_raw = False

    # per-tab line numbers canvas (left) - use configured bg
    ln_canvas = Canvas(frame, width=40, bg=lineNumberBg, highlightthickness=0)
    ln_canvas.pack(side=LEFT, fill=Y)
    frame.lineNumbersCanvas = ln_canvas

    # text area for this tab (center)
    tx = Text(frame)
    tx.pack(side=LEFT, fill=BOTH, expand=True)

    # per-tab scrollbar (right)
    # wrap the scrollbar command so scrolling also updates quick highlighting immediately
    def _scroll_cmd(*args, _tx=tx):
        try:
            _tx.yview(*args)
        except Exception:
            pass
        try:
            safe_highlight_event(None)
        except Exception:
            pass
    scr = Scrollbar(frame, command=_scroll_cmd)    
    tx.configure(yscrollcommand=scr.set)
    scr.pack(side=RIGHT, fill=Y)

    # apply per-widget configuration and insert content
    _configure_text_widget(tx)
    _apply_tag_configs_to_widget(tx)
    tx.insert('1.0', content)
    # color literal hex codes in this new widget (so #rrggbb/#rgb are shown)
    try:
        color_hex_codes(tx, "1.0", "end-1c")
    except Exception:
        pass
    # metadata: keep filename per-tab on the frame object
    frame.fileName = filename

        # record opened location (file path or URL) into history/back-stack
    try:
        if filename:
            _record_location_opened(filename, push_stack=True)
    except Exception:
        pass

    editorNotebook.add(frame, text=title)
    editorNotebook.select(frame)

    # ensure global references update
    _on_tab_changed(None)
    return tx, frame

def _on_tab_changed(event):
    """Synchronize global state when the selected tab changes."""
    try:
        sel = editorNotebook.select()
        if not sel:
            # clear URL when no selection
            try:
                if 'url_var' in globals():
                    url_var.set('')
            except Exception:
                pass
            return
        frame = root.nametowidget(sel)
        # find the Text widget inside the selected frame
        child_text = None
        for child in frame.winfo_children():
            if isinstance(child, Text):
                child_text = child
                break
        if child_text is None:
            return
        # update global reference used throughout the file
        global textArea, lineNumbersCanvas
        textArea = child_text

        # use the frame's per-tab line-numbers canvas
        lineNumbersCanvas = getattr(frame, 'lineNumbersCanvas', None)

        # update root.fileName to reflect current tab
        root.fileName = getattr(frame, 'fileName', '')

        # Update toolbar URL field to reflect current tab (if toolbar exists)
        try:
            if 'url_var' in globals():
                fn = getattr(frame, 'fileName', '') or ''
                if fn:
                    # If it's already a URL, show as-is. Otherwise show file://<abs>
                    if re.match(r'^[a-zA-Z][a-zA-Z0-9+\-.]*://', fn):
                        url_var.set(fn)
                    else:
                        try:
                            p = os.path.abspath(fn)
                            # Convert to a file:// URI (use forward slashes)
                            p_posix = p.replace('\\', '/')
                            if re.match(r'^[A-Za-z]:', p_posix):
                                # Windows absolute path -> file:///C:/path
                                url_var.set('file:///' + p_posix)
                            else:
                                url_var.set('file://' + p_posix)
                        except Exception:
                            url_var.set(fn)
                else:
                    url_var.set('')
        except Exception:
            pass

        # refresh UI elements which depend on active textArea
        highlight_current_line()
        redraw_line_numbers()
        update_status_bar()
        show_trailing_whitespace()
        # update view-state indicator (raw vs rendered / source)
        try:
            update_view_status_indicator()
        except Exception:
            pass


        try:
            prev = getattr(root, '_manual_detect_after_id', None)
            if prev:
                try:
                    root.after_cancel(manual_detect_after_id)
                except Exception:
                    pass
            # run after 1 second so UI settle and any initial insertions complete
            manual_detect_after_id = root.after(1000, lambda: manual_detect_syntax(force=False))
        except Exception:
            pass
    except Exception:
        pass

# Editor notebook for tabbed editing (ensure this exists earlier where it was created)
editorNotebook = ttk.Notebook(root)
editorNotebook.bind('<<NotebookTabChanged>>', _on_tab_changed)

# create initial tab (replaces original single textArea creation)
textArea, _initial_tab_frame = create_editor_tab('Untitled', '')
textArea['bg'] = backgroundColor
textArea['fg'] = fontColor
textArea['font'] = (fontName, fontSize)



def _toggle_simple_tag(tag: str):
    """Toggle a simple text tag for the current selection or whole buffer."""
    try:
        start, end = selection_or_all()
        # If selection has the tag in the region, remove it; otherwise add it.
        # Use tag_ranges to detect presence anywhere in the selected region.
        ranges = textArea.tag_ranges(tag)
        if ranges:
            textArea.tag_remove(tag, start, end)
        else:
            textArea.tag_add(tag, start, end)
    except Exception:
        pass

def format_strong():
    """Apply/remove <strong> semantics -> 'bold' tag."""
    toggle_tag_complex("bold")

def format_em():
    """Apply/remove <em> semantics -> 'italic' tag."""
    toggle_tag_complex("italic")

def format_small():
    _toggle_simple_tag("small")

def format_mark():
    _toggle_simple_tag("mark")

def format_code():
    _toggle_simple_tag("code")

def format_kbd():
    _toggle_simple_tag("kbd")

def format_sub():
    _toggle_simple_tag("sub")

def format_sup():
    _toggle_simple_tag("sup")

def format_marquee():
    """Toggle marquee tag and start/stop animation when enabled."""
    try:
        start, end = selection_or_all()
        ranges = textArea.tag_ranges("marquee")
        if ranges:
            # If any marquee exists in selection, remove for the selection
            textArea.tag_remove("marquee", start, end)
            _stop_marquee_loop()
        else:
            textArea.tag_add("marquee", start, end)
            # ensure trailing space and start loop if visible
            _ensure_marquee_trailing_space()
            if _is_marquee_visible():
                _start_marquee_loop()
    except Exception:
        pass


# -------------------------
# Precompiled regexes / keyword lists (module scope)
# -------------------------
KEYWORDS = [
    'if', 'else', 'while', 'for', 'return', 'def', 'from', 'import', 'class',
    'try', 'except', 'finally', 'with', 'as', 'lambda', 'in', 'is', 'not',
    'and', 'or', 'yield', 'raise', 'global', 'nonlocal', 'assert', 'del',
    'async', 'await', 'pass', 'break', 'continue', 'match', 'case'
]
KEYWORD_RE = re.compile(r'\b(' + r'|'.join(map(re.escape, KEYWORDS)) + r')\b')

# short list of builtins you want highlighted (extend as needed)
BUILTINS = ['len', 'range', 'print', 'open', 'isinstance', 'int', 'str', 'list', 'dict', 'set', 'True', 'False', 'None']
BUILTIN_RE = re.compile(r'\b(' + r'|'.join(map(re.escape, BUILTINS)) + r')\b')
URL_RE = re.compile(r'(?i)\b(?:https?://[^\s<>"]+|file:///[^\s<>"]+|www\.[^\s<>"]+)\b')
HEX_COLOR_RE = re.compile(r'#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})\b')
STRING_RE = re.compile(r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"[^"\n]*"|' + r"'[^'\n]*')", re.DOTALL)
COMMENT_RE = re.compile(r'#[^\n]*')
# better number regex (precompile at module scope)
NUMBER_RE = re.compile(
    r'\b(?:0b[01_]+|0o[0-7_]+|0x[0-9A-Fa-f_]+|'
    r'\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?)(?:[jJ])?\b'
)
DECORATOR_RE = re.compile(r'(?m)^\s*@([A-Za-z_]\w*)')
CLASS_RE = re.compile(r'\bclass\s+([A-Za-z_]\w*)')
VAR_ASSIGN_RE = re.compile(r'(?m)^[ \t]*([A-Za-z_]\w*)\s*=')
CONSTANT_RE = re.compile(r'(?m)^[ \t]*([A-Z][_A-Z0-9]+)\s*=')
ATTRIBUTE_RE = re.compile(r'\.([A-Za-z_]\w*)')
TODO_RE = re.compile(r'#.*\b(TODO|FIXME|NOTE)\b', re.IGNORECASE)
# extend `selfs` to include attribute names like 'after'
SELFS_RE = re.compile(r'\b(?:[a-z])(?:[A-Z]?[a-z])*(?:[A-Z][a-z]*)|\b(self|root|after)\b')
# variable annotation (may include optional assignment)
VAR_ANNOT_RE = re.compile(r'(?m)^[ \t]*([A-Za-z_]\w*)\s*:\s*([^=\n]+)(?:=.*)?$')
FSTRING_RE = re.compile(r"(?:[fF][rRuU]?|[rR][fF]?)(\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?'''|\"[^\n\"]*\"|'[^\\n']*')", re.DOTALL)
DUNDER_RE = re.compile(r'\b__\w+__\b')
CLASS_BASES_RE = re.compile(r'(?m)^[ \t]*class\s+[A-Za-z_]\w*\s*\(([^)]*)\)')

# HTML-specific regexes for tag/attr/value/comment highlighting
HTML_TAG_RE = re.compile(r'</?([A-Za-z][A-Za-z0-9:\-]*)')  # group 1 is tag name
HTML_ATTR_RE = re.compile(r'([A-Za-z_:][A-Za-z0-9_:.\-]*)\s*=')  # attribute name before =
HTML_ATTR_VAL_RE = re.compile(r'=\s*(?:"([^"]*?)"|\'([^\']*?)\'|([^\s>]+))')  # captures value in one of groups 1/2/3
HTML_COMMENT_RE = re.compile(r'<!--([\s\S]*?)-->')

# -------------------------
# Runtime-editable syntax defaults and loader
# -------------------------
# default tag color map (keeps same defaults as above)
# default tag color map (explicit fg/bg for every tag)
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

def open_url_action():
    """Prompt for a URL, fetch it on a background thread and open parsed HTML in a tab."""
    try:
        dlg = Toplevel(root)
        dlg.title("Open URL")
        dlg.transient(root)
        dlg.grab_set()
        dlg.resizable(False, False)

        container = ttk.Frame(dlg, padding=12)
        container.grid(row=0, column=0, sticky='nsew')
        container.columnconfigure(1, weight=1)

        ttk.Label(container, text="URL:").grid(row=0, column=0, sticky='w', pady=(0,6))
        url_var = StringVar(value='')
        url_entry = ttk.Entry(container, textvariable=url_var, width=60)
        url_entry.grid(row=0, column=1, sticky='ew', padx=(6,0), pady=(0,6))

        new_tab_var = IntVar(value=1)
        chk_newtab = ttk.Checkbutton(container, text="Open in new tab", variable=new_tab_var)
        chk_newtab.grid(row=1, column=1, sticky='w', pady=(0,8))

        status = ttk.Label(container, text="")
        status.grid(row=2, column=0, columnspan=2, sticky='w')

        def do_cancel():
            try:
                dlg.grab_release()
            except Exception:
                pass
            dlg.destroy()

        def do_open():
            u = url_var.get().strip()
            if not u:
                status.config(text="No URL provided.")
                return
            try:
                dlg.grab_release()
            except Exception:
                pass
            dlg.destroy()

            def worker(url, open_in_new_tab):
                try:
                    # lazy import to avoid changing top-of-file imports
                    import urllib.request as urr
                    import urllib.parse as up
                    # ensure scheme
                    parsed = up.urlsplit(url)
                    if not parsed.scheme:
                        url2 = 'http://' + url
                    else:
                        url2 = url
                    req = urr.Request(url2, headers={"User-Agent": "SimpleEdit/1.0"})
                    with urr.urlopen(req, timeout=15) as resp:
                        # attempt to get charset from headers; fallback to utf-8
                        charset = None
                        try:
                            ct = resp.headers.get_content_charset()
                            if ct:
                                charset = ct
                        except Exception:
                            pass
                        raw_bytes = resp.read()
                        enc = charset or 'utf-8'
                        try:
                            raw = raw_bytes.decode(enc, errors='replace')
                        except Exception:
                            raw = raw_bytes.decode('utf-8', errors='replace')

                    # reuse existing HTML parsing flow
                    # Respect the user preference: if configured to open HTML/MD "as source",
                    # treat fetched bytes as raw text and do NOT parse into visual tags.
                    preset_path = None
                    if config.getboolean("Section1", "openHtmlAsSource", fallback=False):
                        plain = raw
                        tags_meta = None
                        # still attempt syntax autodetect (but apply on UI thread so highlighting uses the widget)
                        try:
                            if config.getboolean("Section1", "autoDetectSyntax", fallback=True):
                                preset_path = detect_syntax_preset_from_content(raw, filename_hint=url2)
                        except Exception:
                            preset_path = None
                    else:
                        plain, tags_meta = funcs._parse_html_and_apply(raw)
                        # when parsed HTML, we may still want to autodetect syntax for non-HTML fragments
                        try:
                            if config.getboolean("Section1", "autoDetectSyntax", fallback=True) and not preset_path:
                                preset_path = detect_syntax_preset_from_content(raw, filename_hint=url2)
                        except Exception:
                            preset_path = None
                    def ui():
                        try:
                            title = up.urlsplit(url2).netloc or url2
                            if open_in_new_tab:
                                tx, fr = create_editor_tab(title, plain, filename=url2)
                                tx.focus_set()
                                _apply_tag_configs_to_widget(tx)
                                try:
                                    fr._raw_html = raw
                                    fr._raw_html_plain = plain
                                    fr._raw_html_tags_meta = tags_meta
                                    fr._view_raw = False
                                except Exception:
                                    pass
                            else:
                                # When navigating in the current tab, record the previous URL (if any)
                                try:
                                    sel = editorNotebook.select()
                                    prev = ''
                                    if sel:
                                        frame = root.nametowidget(sel)
                                        prev = getattr(frame, 'fileName', '') or getattr(root, 'fileName', '') or ''
                                    else:
                                        prev = getattr(root, 'fileName', '') or ''
                                    # Persist / push the previous location exactly like other open-path code
                                    # (this updates the url history UI + back-stack immediately)
                                    try:
                                        _record_location_opened(prev, push_stack=True)
                                    except Exception:
                                        pass
                                except Exception:
                                    pass

                                # replace current tab content and set metadata to new URL
                                textArea.delete('1.0', 'end')
                                textArea.insert('1.0', plain)
                                _apply_tag_configs_to_widget(textArea)
                                try:
                                    sel = editorNotebook.select()
                                    if sel:
                                        frame = root.nametowidget(sel)
                                        frame.fileName = url2
                                        # store raw/parsed for toggle
                                        frame._raw_html = raw
                                        frame._raw_html_plain = plain
                                        frame._raw_html_tags_meta = tags_meta
                                        frame._view_raw = False
                                    root.fileName = url2
                                except Exception:
                                    root.fileName = url2

                                # record the new URL open into history/back-stack
                                try:
                                    _record_location_opened(url2, push_stack=True)
                                except Exception:
                                    pass

                                # if autodetect yielded a preset, apply it now on the UI thread so highlighting rules update
                                try:
                                    if preset_path:
                                        applied = apply_syntax_preset(preset_path)
                                        if applied:
                                            statusBar['text'] = "Applied syntax preset from autodetect."
                                except Exception:
                                    pass

                            statusBar['text'] = f"Opened URL: {url2}"
                            # Do NOT add URLs to recent files (recent list is for local files only)
                            if tags_meta and tags_meta.get('tags'):
                                root.after(0, lambda: _apply_formatting_from_meta(tags_meta))
                            if updateSyntaxHighlighting.get():
                                root.after(0, highlightPythonInit)
                            # keep the toolbar field in sync with what we opened
                            try:
                                if 'url_var' in globals():
                                    url_var.set(url2)
                            except Exception:
                                pass
                        except Exception as e:
                            try:
                                messagebox.showerror("Error", str(e))
                            except Exception:
                                pass

                    root.after(0, ui)

                except Exception as e:
                    def ui_err():
                        try:
                            messagebox.showerror("Fetch error", f"Failed to fetch URL: {e}")
                        except Exception:
                            pass
                    root.after(0, ui_err)

            Thread(target=worker, args=(u, bool(new_tab_var.get())), daemon=True).start()

        btn_frame = ttk.Frame(container)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=(6,0), sticky='e')
        ttk.Button(btn_frame, text="Open", command=do_open).pack(side=RIGHT, padx=(6,0))
        ttk.Button(btn_frame, text="Cancel", command=do_cancel).pack(side=RIGHT)

        dlg.update_idletasks()
        center_window(dlg)
        url_entry.focus_set()
    except Exception:
        pass

# Marquee animator: shifts text inside 'marquee' tag left once per second while visible.
_marquee_after_id = None
_marquee_running = False

def _is_marquee_visible():
    """Return True if any 'marquee' tag range intersects the visible viewport."""
    try:
        if not textArea:
            return False
        first_visible = textArea.index('@0,0')
        last_visible = textArea.index(f'@0,{textArea.winfo_height()}')
        first_line = int(first_visible.split('.')[0])
        last_line = int(last_visible.split('.')[0])
        ranges = textArea.tag_ranges('marquee')
        if not ranges:
            return False
        for i in range(0, len(ranges), 2):
            s = str(ranges[i])
            e = str(ranges[i + 1])
            s_line = int(s.split('.')[0])
            e_line = int(e.split('.')[0])
            if not (e_line < first_line or s_line > last_line):
                return True
        return False
    except Exception:
        return False

def _marquee_schedule_tick():
    global _marquee_after_id
    try:
        # schedule tick on main thread after 1000ms
        _marquee_after_id = root.after(1000, _marquee_tick)
    except Exception:
        _marquee_after_id = None

def _ensure_marquee_trailing_space():
    """Ensure each marquee range ends with a space so rotation doesn't join first/last chars."""
    try:
        if not textArea:
            return
        ranges = list(textArea.tag_ranges('marquee'))
        for i in range(0, len(ranges), 2):
            s = str(ranges[i])
            e = str(ranges[i + 1])
            try:
                content = textArea.get(s, e)
            except Exception:
                continue
            if not content:
                continue
            # Add one trailing space if missing
            if not content.endswith(' '):
                try:
                    # Insert space at the old end, then reapply marquee tag to include it
                    textArea.insert(e, ' ')
                    new_end = f"{s} + {len(content) + 1}c"
                    # remove old tag span and add new extended span
                    textArea.tag_remove('marquee', s, e)
                    textArea.tag_add('marquee', s, new_end)
                except Exception:
                    pass
    except Exception:
        pass

def _start_marquee_loop():
    """Start the marquee tick loop if not already running. Ensure trailing space first."""
    global _marquee_running
    try:
        if _marquee_running:
            return
        if not textArea:
            return
        if not textArea.tag_ranges('marquee'):
            return
        # ensure a trailing space so rotation preserves separation
        _ensure_marquee_trailing_space()
        _marquee_running = True
        _marquee_schedule_tick()
    except Exception:
        _marquee_running = False

def _stop_marquee_loop():
    """Stop the marquee tick loop."""
    global _marquee_after_id, _marquee_running
    try:
        if _marquee_after_id:
            try:
                root.after_cancel(_marquee_after_id)
            except Exception:
                pass
        _marquee_after_id = None
    finally:
        _marquee_running = False

def _replace_region_preserve_tags(start_idx: str, end_idx: str, new_text: str):
    """Replace text in [start_idx, end_idx) with new_text while preserving overlapping tags.

    - Records tag ranges overlapping the region (except 'sel' which is handled separately).
    - Removes those tag spans inside the region, performs the replace, and re-adds tags
      at the same relative positions inside the region.
    """
    try:
        if not textArea:
            return
        s = textArea.index(start_idx)
        e = textArea.index(end_idx)

        # compute absolute offsets for region start/end
        region_start_off = len(textArea.get('1.0', s))
        region_end_off = len(textArea.get('1.0', e))
        region_len = max(0, region_end_off - region_start_off)

        # collect overlapping tag fragments (tag, rel_start, rel_end)
        preserved = []
        for tag in textArea.tag_names():
            if tag == 'sel':
                continue
            try:
                rngs = textArea.tag_ranges(tag)
                for i in range(0, len(rngs), 2):
                    rs = textArea.index(rngs[i])
                    re_ = textArea.index(rngs[i+1])
                    rs_off = len(textArea.get('1.0', rs))
                    re_off = len(textArea.get('1.0', re_))
                    # overlap test
                    if re_off <= region_start_off or rs_off >= region_end_off:
                        continue
                    rel_s = max(0, rs_off - region_start_off)
                    rel_e = min(region_len, re_off - region_start_off)
                    if rel_e > rel_s:
                        preserved.append((tag, rel_s, rel_e))
            except Exception:
                pass

        # deduplicate preserved entries to avoid duplicate re-adds
        seen = set()
        uniq_preserved = []
        for tag, rs, re_ in preserved:
            key = (tag, rs, re_)
            if key in seen:
                continue
            seen.add(key)
            uniq_preserved.append((tag, rs, re_))

        # remove all preserved tag spans in region
        try:
            for tag, _, _ in uniq_preserved:
                try:
                    textArea.tag_remove(tag, s, e)
                except Exception:
                    pass
        except Exception:
            pass

        # record selection to restore roughly (best-effort)
        sel_ranges = textArea.tag_ranges('sel')

        # replace text (delete + insert)
        try:
            textArea.delete(s, e)
            textArea.insert(s, new_text)
        except Exception:
            return

        # reapply preserved tag spans relative to start
        try:
            for tag, rel_s, rel_e in uniq_preserved:
                try:
                    ns = textArea.index(f"{s} + {int(rel_s)}c")
                    ne = textArea.index(f"{s} + {int(rel_e)}c")
                    textArea.tag_add(tag, ns, ne)
                except Exception:
                    pass
        except Exception:
            pass

        # restore selection roughly if present (best-effort)
        try:
            if sel_ranges and len(sel_ranges) >= 2:
                try:
                    textArea.tag_remove('sel', '1.0', 'end')
                except Exception:
                    pass
                try:
                    # if selection was after replace region, we place it at region end
                    textArea.tag_add('sel', s, textArea.index(f"{s} + {len(new_text)}c"))
                    textArea.mark_set('insert', textArea.index(f"{s} + {len(new_text)}c"))
                except Exception:
                    pass
        except Exception:
            pass
    except Exception:
        pass


def _marquee_tick():
    """One animation tick: rotate characters left for each marquee range, preserving other tags."""
    global _marquee_after_id, _marquee_running
    try:
        if not _marquee_running:
            return
        # snapshot of marquee ranges (work on a copy)
        ranges = list(textArea.tag_ranges('marquee'))
        if not ranges:
            _stop_marquee_loop()
            return

        for i in range(0, len(ranges), 2):
            try:
                s = str(ranges[i])
                e = str(ranges[i + 1])
                try:
                    content = textArea.get(s, e)
                except Exception:
                    continue
                if not content or len(content) <= 1:
                    continue

                # produce rotated string (left rotate by one char)
                new = content[1:] + content[0]

                # replace region preserving tags
                _replace_region_preserve_tags(s, e, new)

                # ensure marquee tag still covers the full replaced region
                try:
                    textArea.tag_remove('marquee', s, f"{s} + {len(new)}c")
                    textArea.tag_add('marquee', s, f"{s} + {len(new)}c")
                except Exception:
                    pass

            except Exception:
                # continue with other ranges even on error
                pass

        # Continue if marquee remains visible
        if _is_marquee_visible():
            _marquee_schedule_tick()
        else:
            _stop_marquee_loop()
    except Exception:
        _stop_marquee_loop()

# default regex string map (patterns as strings; flags handled below)
_DEFAULT_REGEXES = {
    "KEYWORDS": r'\b(' + r'|'.join(map(re.escape, KEYWORDS)) + r')\b',
    "BUILTINS": r'\b(' + r'|'.join(map(re.escape, BUILTINS)) + r')\b',
    "STRING_RE": r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"[^"\n]*"|' + r"'[^'\n]*')",
    "COMMENT_RE": r'#[^\n]*',
    "NUMBER_RE": r'\b(?:0b[01_]+|0o[0-7_]+|0x[0-9A-Fa-f_]+|\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?)(?:[jJ])?\b',
    "DECORATOR_RE": r'(?m)^\s*@([A-Za-z_]\w*)',
    "CLASS_RE": r'\bclass\s+([A-Za-z_]\w*)',
    "VAR_ASSIGN_RE": r'(?m)^[ \t]*([A-Za-z_]\w*)\s*=',
    "CONSTANT_RE": r'(?m)^[ \t]*([A-Z][_A-Z0-9]+)\s*=',
    "ATTRIBUTE_RE": r'\.([A-Za-z_]\w*)',
    "TODO_RE": r'#.*\b(TODO|FIXME|NOTE)\b',
    "SELFS_RE": r'\b(?:[a-z])(?:[A-Z]?[a-z])*(?:[A-Z][a-z]*)|\b(self|root|after)\b',
    "VAR_ANNOT_RE": r'(?m)^[ \t]*([A-Za-z_]\w*)\s*:\s*([^=\n]+)(?:=.*)?$',
    "FSTRING_RE": r"(?:[fF][rRuU]?|[rR][fF]?)(\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?'''|\"[^\n\"]*\"|'[^\\n']*')",
    "DUNDER_RE": r'\b__\w+__\b',
    "CLASS_BASES_RE": r'(?m)^[ \t]*class\s+[A-Za-z_]\w*\s*\(([^)]*)\)'
}

def scan_syntax_presets(dirname='syntax'):
    """Return list of (path, name, filename_lower) for .ini presets in `dirname`."""
    out = []
    try:
        base = os.path.abspath(dirname)
        if not os.path.isdir(base):
            return out
        for fn in sorted(os.listdir(base)):
            if not fn.lower().endswith('.ini'):
                continue
            p = os.path.join(base, fn)
            try:
                cp = configparser.ConfigParser()
                cp.read(p)
                name = cp.get('Syntax', 'name', fallback=os.path.splitext(fn)[0])
            except Exception:
                name = os.path.splitext(fn)[0]
            out.append((p, name, fn.lower()))
    except Exception:
        pass
    return out


def detect_syntax_preset_from_content(raw, filename_hint: str | None = None):
    """Return preset path if a matching preset looks appropriate for `raw`, otherwise None.

    Detection rules are read from each preset's [Syntax] section. Supported detection keys:
      - detect.regex, detect.regex.N : regular expressions (applied with re.I|re.S)
      - detect.contains                : comma/semicolon/newline-separated literal substrings
      - detect.priority                : integer priority (higher wins when multiple presets match)
      - detect.filename                : substring matched against provided filename_hint (optional)
    This makes detection extensible by editing / adding presets under `syntax/`.
    """
    try:
        if not raw or not isinstance(raw, str):
            return None

        presets = scan_syntax_presets()
        if not presets:
            return None

        matches = []  # list of (priority:int, index:int, path:str)

        for idx, (path, name, fname) in enumerate(presets):
            try:
                cp = configparser.ConfigParser()
                cp.read(path)
                if not cp.has_section('Syntax'):
                    continue

                pr = 0
                try:
                    pr = int(cp.get('Syntax', 'detect.priority', fallback='0') or '0')
                except Exception:
                    pr = 0

                # 1) regex-based detection (can provide multiple keys detect.regex, detect.regex.1, ...)
                matched = False
                try:
                    for opt, val in cp.items('Syntax'):
                        if opt.startswith('detect.regex'):
                            pat = (val or '').strip()
                            if not pat:
                                continue
                            try:
                                if re.search(pat, raw, flags=re.I | re.S):
                                    matches.append((pr, idx, path))
                                    matched = True
                                    break
                            except Exception:
                                # ignore invalid pattern
                                continue
                    if matched:
                        continue
                except Exception:
                    pass

                # 2) contains-based detection: comma/semicolon/newline separated tokens
                try:
                    contains = cp.get('Syntax', 'detect.contains', fallback='').strip()
                    if contains:
                        tokens = [t.strip() for t in re.split(r'[,\n;]+', contains) if t.strip()]
                        low = raw.lower()
                        for tok in tokens:
                            if tok.lower() in low:
                                matches.append((pr, idx, path))
                                matched = True
                                break
                    if matched:
                        continue
                except Exception:
                    pass

                # 3) filename hint match (useful when caller supplies the filename)
                if filename_hint:
                    try:
                        det_fn = cp.get('Syntax', 'detect.filename', fallback='').strip().lower()
                        if det_fn and det_fn in (filename_hint or '').lower():
                            matches.append((pr, idx, path))
                            continue
                    except Exception:
                        pass

                # 4) fallback: some presets may include a simple 'detect.ext' comma list
                try:
                    det_ext = cp.get('Syntax', 'detect.ext', fallback='').strip()
                    if det_ext and filename_hint:
                        exts = [e.strip().lstrip('.').lower() for e in re.split(r'[,\n;]+', det_ext) if e.strip()]
                        if any((filename_hint.lower().endswith('.' + e) for e in exts)):
                            matches.append((pr, idx, path))
                            continue
                except Exception:
                    pass

            except Exception:
                # skip preset on error
                continue

        # if any preset matched, choose highest priority, then lowest index (stable)
        if matches:
            matches.sort(key=lambda x: (-x[0], x[1]))
            return matches[0][2]

        # legacy heuristics (keep existing simple html detection)
        try:
            if re.search(r'(?i)<!doctype\s+html\b', raw) or re.search(r'(?i)<html\b', raw) or re.search(r'(?i)<head\b', raw) or re.search(r'(?i)<body\b', raw):
                presets = scan_syntax_presets()
                for path, name, fname in presets:
                    if 'html' in name.lower() or 'html' in fname:
                        return path
                if presets:
                    return presets[0][0]
        except Exception:
            pass

    except Exception:
        pass
    return None


def apply_syntax_preset(path):
    """Apply Syntax section values from a preset INI into main `config` and persist + reload."""
    try:
        if not path or not os.path.isfile(path):
            return False
        cp = configparser.ConfigParser()
        cp.read(path)
        if not cp.has_section('Syntax'):
            return False

        if not config.has_section('Syntax'):
            config.add_section('Syntax')

        # copy all options prefixed for Syntax from the preset into the main config
        for opt, val in cp.items('Syntax'):
            # copy everything under Syntax (including name, tag.*, regex.* etc.)
            try:
                if val is None:
                    # if empty, remove option if present
                    try:
                        config.remove_option('Syntax', opt)
                    except Exception:
                        pass
                else:
                    config.set('Syntax', opt, val)
            except Exception:
                pass

        # persist and apply
        try:
            with open(INI_PATH, 'w') as f:
                config.write(f)
        except Exception:
            pass

        # reload runtime syntax
        try:
            load_syntax_config()
            return True
        except Exception:
            return False
    except Exception:
        return False



def load_syntax_config():
    """Load tag colors and regex overrides from config and apply them at runtime."""
    global KEYWORDS, KEYWORD_RE, BUILTINS, BUILTIN_RE
    global STRING_RE, COMMENT_RE, NUMBER_RE, DECORATOR_RE, CLASS_RE, VAR_ASSIGN_RE, CONSTANT_RE
    global ATTRIBUTE_RE, TODO_RE, SELFS_RE, VAR_ANNOT_RE, FSTRING_RE, DUNDER_RE, CLASS_BASES_RE

    try:
        if not config.has_section('Syntax'):
            return

        # helper: validate a color string using tkinter (root.winfo_rgb raises on invalid)
        def _valid_color(c):
            if not c:
                return False
            try:
                root.winfo_rgb(c)
                return True
            except Exception:
                return False

        # Apply tag colors (validate config values and defaults before applying)
        for tag, defaults in _DEFAULT_TAG_COLORS.items():
            fg_cfg = config.get('Syntax', f'tag.{tag}.fg', fallback=defaults.get('fg', '')).strip()
            bg_cfg = config.get('Syntax', f'tag.{tag}.bg', fallback=defaults.get('bg', '')).strip()

            kwargs = {}
            if fg_cfg and _valid_color(fg_cfg):
                kwargs['foreground'] = fg_cfg
            if bg_cfg and _valid_color(bg_cfg):
                kwargs['background'] = bg_cfg

            # If config contained invalid colors, try to fall back to validated defaults
            if not kwargs:
                # attempt to use validated defaults if present
                df = defaults.get('fg', '').strip()
                db = defaults.get('bg', '').strip()
                if df and _valid_color(df):
                    kwargs['foreground'] = df
                if db and _valid_color(db):
                    kwargs['background'] = db

            if kwargs:
                try:
                    _safe_tag_config(textArea, tag, foreground=kwargs.get('foreground'), background=kwargs.get('background'))
                except Exception:
                    pass

        # Regexes and keyword lists
        # KEYWORDS and BUILTINS stored as comma-separated lists for ease of editing
        kw_csv = config.get('Syntax', 'keywords.csv', fallback=','.join(KEYWORDS))
        bk_csv = config.get('Syntax', 'builtins.csv', fallback=','.join(BUILTINS))
        try:
            KEYWORDS = [x.strip() for x in kw_csv.split(',') if x.strip()]
            KEYWORD_RE = re.compile(r'\b(' + r'|'.join(map(re.escape, KEYWORDS)) + r')\b') if KEYWORDS else re.compile(r'\b\b')
        except Exception:
            pass
        try:
            BUILTINS = [x.strip() for x in bk_csv.split(',') if x.strip()]
            BUILTIN_RE = re.compile(r'\b(' + r'|'.join(map(re.escape, BUILTINS)) + r')\b') if BUILTINS else re.compile(r'\b\b')
        except Exception:
            pass

        # Generic regex patterns (store raw pattern strings)
        for key, default_pattern in _DEFAULT_REGEXES.items():
            cfg_key = f'regex.{key}'
            pat = config.get('Syntax', cfg_key, fallback=default_pattern)
            if not pat:
                continue
            try:
                # flags: STRING_RE and FSTRING_RE need DOTALL; DECORATOR/VAR/CLASS use multiline anchors already encoded in pattern
                if key in ('STRING_RE', 'FSTRING_RE'):
                    compiled = re.compile(pat, re.DOTALL)
                else:
                    compiled = re.compile(pat)
                # assign to appropriate global variable name(s)
                if key == 'STRING_RE':
                    STRING_RE = compiled
                elif key == 'COMMENT_RE':
                    COMMENT_RE = compiled
                elif key == 'NUMBER_RE':
                    NUMBER_RE = compiled
                elif key == 'DECORATOR_RE':
                    DECORATOR_RE = compiled
                elif key == 'CLASS_RE':
                    CLASS_RE = compiled
                elif key == 'VAR_ASSIGN_RE':
                    VAR_ASSIGN_RE = compiled
                elif key == 'CONSTANT_RE':
                    CONSTANT_RE = compiled
                elif key == 'ATTRIBUTE_RE':
                    ATTRIBUTE_RE = compiled
                elif key == 'TODO_RE':
                    TODO_RE = compiled
                elif key == 'SELFS_RE':
                    SELFS_RE = compiled
                elif key == 'VAR_ANNOT_RE':
                    VAR_ANNOT_RE = compiled
                elif key == 'FSTRING_RE':
                    FSTRING_RE = compiled
                elif key == 'DUNDER_RE':
                    DUNDER_RE = compiled
                elif key == 'CLASS_BASES_RE':
                    CLASS_BASES_RE = compiled
                # KEYWORDS/BUILTINS handled above
            except Exception:
                # ignore bad patterns
                pass

        # After reloading syntax, refresh highlighting
        try:
            if updateSyntaxHighlighting.get():
                highlightPythonInit()
        except Exception:
            pass
    except Exception:
        pass


def setting_syntax_modal():
    """Wrapper for backward compatibility and toolbar/button binding."""

    try:
        load_syntax_config()
    except Exception:
        pass
    open_syntax_editor()


def is_valid_color(s):
    """Return True if tkinter accepts the color string `s` (non-empty)."""
    if not s:
        return False
    try:
        # root exists at module scope; winfo_rgb raises on invalid color names/hex
        root.winfo_rgb(s)
        return True
    except Exception:
        return False

def safe_askcolor(initial_str=None, **kwargs):
    """Call colorchooser.askcolor but avoid passing empty/invalid initialcolor to Tk."""
    init = (initial_str or '').strip()
    if not init or not is_valid_color(init):
        init = None
    return colorchooser.askcolor(initialcolor=init, **kwargs)

def export_syntax_preset(inputs_fg=None, inputs_bg=None, kw_ent=None, bk_ent=None, regex_entries=None, preset_name=None):
    """
    Export current syntax settings to a .ini file inside the `syntax/` folder.
    If widget references are provided (from open_syntax_editor) their current values
    are exported; otherwise current values from `config` are used.
    """
    try:
        # Ensure syntax directory exists
        syntax_dir = os.path.abspath('syntax')
        os.makedirs(syntax_dir, exist_ok=True)

        # Build a sensible default filename
        default_name = preset_name or config.get('Syntax', 'preset_name', fallback='syntax_preset')
        default_path = os.path.join(syntax_dir, f"{default_name}.ini")

        # Ask user for destination file (modal)
        file_path = filedialog.asksaveasfilename(
            initialdir=syntax_dir,
            initialfile=os.path.basename(default_path),
            title="Export Syntax Preset",
            defaultextension='.ini',
            filetypes=(("INI files", "*.ini"), ("All files", "*.*"))
        )
        if not file_path:
            return  # user cancelled

        cp = configparser.ConfigParser()
        cp.add_section('Syntax')

        # store a human-readable name
        cp.set('Syntax', 'name', os.path.splitext(os.path.basename(file_path))[0])

        # tags: either from provided widgets or from current config
        for tag in _DEFAULT_TAG_COLORS.keys():
            if inputs_fg and tag in inputs_fg:
                fg_val = inputs_fg[tag].get().strip()
            else:
                fg_val = config.get('Syntax', f'tag.{tag}.fg', fallback='').strip()
            if inputs_bg and tag in inputs_bg:
                bg_val = inputs_bg[tag].get().strip()
            else:
                bg_val = config.get('Syntax', f'tag.{tag}.bg', fallback='').strip()

            if fg_val:
                cp.set('Syntax', f'tag.{tag}.fg', fg_val)
            if bg_val:
                cp.set('Syntax', f'tag.{tag}.bg', bg_val)

        # keywords & builtins
        if kw_ent:
            kw_txt = kw_ent.get().strip()
        else:
            kw_txt = config.get('Syntax', 'keywords.csv', fallback=','.join(KEYWORDS))
        if bk_ent:
            bk_txt = bk_ent.get().strip()
        else:
            bk_txt = config.get('Syntax', 'builtins.csv', fallback=','.join(BUILTINS))

        if kw_txt:
            cp.set('Syntax', 'keywords.csv', kw_txt)
        if bk_txt:
            cp.set('Syntax', 'builtins.csv', bk_txt)

        # regex entries: prefer passed widgets, otherwise current config/defaults
        if regex_entries:
            keys = list(regex_entries.keys())
        else:
            keys = list(_DEFAULT_REGEXES.keys())
        for key in keys:
            if regex_entries and key in regex_entries:
                val = regex_entries[key].get('1.0', 'end-1c').strip()
            else:
                val = config.get('Syntax', f'regex.{key}', fallback=_DEFAULT_REGEXES.get(key, '')).strip()
            if val:
                cp.set('Syntax', f'regex.{key}', val)

        # Write to file
        with open(file_path, 'w', encoding='utf-8') as fh:
            cp.write(fh)

        try:
            messagebox.showinfo("Export Complete", f"Syntax preset exported to:\n{file_path}")
        except Exception:
            pass
    except Exception as e:
        try:
            messagebox.showerror("Export Failed", str(e))
        except Exception:
            pass


def open_syntax_editor():
    """Modal window to edit tag colors and regex/keyword lists; writes to config and reloads."""
    dlg = Toplevel(root)
    dlg.transient(root)
    dlg.grab_set()
    dlg.title("Edit Syntax Highlighting")
    dlg.resizable(False, False)

    container = ttk.Frame(dlg, padding=10)
    container.grid(row=0, column=0, sticky='nsew')
    container.columnconfigure(0, weight=1)
    container.columnconfigure(1, weight=1)

    # Helper to scan syntax presets directory for .ini files and return (path, display_name)
    def scan_syntax_dir(dirname='syntax'):
        out = []
        try:
            base = os.path.abspath(dirname)
            if not os.path.isdir(base):
                return out
            for fn in sorted(os.listdir(base)):
                if not fn.lower().endswith('.ini'):
                    continue
                p = os.path.join(base, fn)
                try:
                    cp = configparser.ConfigParser()
                    cp.read(p)
                    if cp.has_section('Syntax'):
                        name = cp.get('Syntax', 'name', fallback=os.path.splitext(fn)[0])
                    else:
                        name = os.path.splitext(fn)[0]
                except Exception:
                    name = os.path.splitext(fn)[0]
                out.append((p, name))
        except Exception:
            pass
        return out

    # Tabs for Tags and Regex/Lists
    nb = ttk.Notebook(container)
    nb.grid(row=0, column=0, columnspan=2, sticky='nsew')

    # Tags tab
    tab_tags = ttk.Frame(nb, padding=8)
    nb.add(tab_tags, text='Tags')

    row = 0
    swatches_fg = {}
    swatches_bg = {}
    inputs_fg = {}
    inputs_bg = {}

    # Small helper to build a clickable swatch bound to an entry
    def build_clickable_swatch(parent, init_color, entry_widget):
        sw = Label(parent, width=3, relief='sunken')
        if is_valid_color(init_color):
            sw.config(bg=init_color)
        try:
            sw.config(cursor="hand2")
        except Exception:
            pass

        def on_click(e=None, ent=entry_widget, s=sw):
            c = safe_askcolor(ent.get())
            hexc = get_hex_color(c)
            if hexc:
                ent.delete(0, END)
                ent.insert(0, hexc)
                if is_valid_color(hexc):
                    try:
                        s.config(bg=hexc)
                    except Exception:
                        pass
        sw.bind("<Button-1>", on_click)
        return sw

    # Header row (optional, simple hints)
    ttk.Label(tab_tags, text="Tag").grid(row=row, column=0, sticky='w', padx=(0,8))
    ttk.Label(tab_tags, text="FG").grid(row=row, column=1, sticky='w')
    ttk.Label(tab_tags, text=" ").grid(row=row, column=2, sticky='w')  # swatch column
    ttk.Label(tab_tags, text="BG").grid(row=row, column=3, sticky='w')
    ttk.Label(tab_tags, text=" ").grid(row=row, column=4, sticky='w')  # swatch column
    row += 1

    # Render tags in 4 blocks across to avoid vertical overflow
    tags_list = list(_DEFAULT_TAG_COLORS.items())
    per_row = 3  # number of tag blocks per visual row
    block_width = 5  # columns per block (Tag, FG, swatch, BG, swatch)
    start_row = row
    for idx, (tag, defaults) in enumerate(tags_list):
        r = start_row + (idx // per_row)
        block = idx % per_row
        base_col = block * block_width

        ttk.Label(tab_tags, text=tag).grid(row=r, column=base_col, sticky='w', padx=(0,8), pady=4)

        # FG entry + swatch (clickable)
        ent_fg = ttk.Entry(tab_tags, width=14)
        ent_fg.grid(row=r, column=base_col + 1, sticky='w', pady=4)
        ent_val_fg = config.get('Syntax', f'tag.{tag}.fg', fallback=defaults.get('fg', ''))
        ent_fg.insert(0, ent_val_fg)
        sw_fg = build_clickable_swatch(tab_tags, ent_val_fg, ent_fg)
        sw_fg.grid(row=r, column=base_col + 2, padx=(6,0))

        # BG entry + swatch (clickable)
        ent_bg = ttk.Entry(tab_tags, width=14)
        ent_bg.grid(row=r, column=base_col + 3, sticky='w', pady=4)
        ent_val_bg = config.get('Syntax', f'tag.{tag}.bg', fallback=defaults.get('bg', ''))
        ent_bg.insert(0, ent_val_bg)
        sw_bg = build_clickable_swatch(tab_tags, ent_val_bg, ent_bg)
        sw_bg.grid(row=r, column=base_col + 4, padx=(6,0))

        swatches_fg[tag] = sw_fg
        swatches_bg[tag] = sw_bg
        inputs_fg[tag] = ent_fg
        inputs_bg[tag] = ent_bg
    # ensure columns can expand reasonably (give some weight so widgets don't collapse)
    try:
        max_cols = per_row * block_width
        for c in range(max_cols):
            tab_tags.grid_columnconfigure(c, weight=1 if c % block_width != 0 else 0)
    except Exception:
        pass

    # Regex / lists tab
    tab_regex = ttk.Frame(nb, padding=8)
    nb.add(tab_regex, text='Regex & Lists')

    r = 0
    # Keywords (CSV)
    ttk.Label(tab_regex, text="Keywords (comma-separated)").grid(row=r, column=0, sticky='w', pady=4)
    kw_ent = ttk.Entry(tab_regex, width=60)
    kw_ent.grid(row=r, column=1, pady=4)
    kw_ent.insert(0, config.get('Syntax', 'keywords.csv', fallback=','.join(KEYWORDS)))
    r += 1
    # Builtins
    ttk.Label(tab_regex, text="Builtins (comma-separated)").grid(row=r, column=0, sticky='w', pady=4)
    bk_ent = ttk.Entry(tab_regex, width=60)
    bk_ent.grid(row=r, column=1, pady=4)
    bk_ent.insert(0, config.get('Syntax', 'builtins.csv', fallback=','.join(BUILTINS)))
    r += 1

    # Generic regexes: show a few common ones in multi-line entries
    regex_entries = {}
    regex_keys = (
        'STRING_RE', 'COMMENT_RE', 'NUMBER_RE', 'DECORATOR_RE', 'CLASS_RE',
        'VAR_ASSIGN_RE', 'ATTRIBUTE_RE', 'TODO_RE', 'CONSTANT_RE', 'VAR_ANNOT_RE',
        'FSTRING_RE', 'DUNDER_RE', 'CLASS_BASES_RE'
    )
    for key in regex_keys:
        ttk.Label(tab_regex, text=key).grid(row=r, column=0, sticky='nw', pady=(6,0))
        ent = Text(tab_regex, height=2 if key not in ('FSTRING_RE','CLASS_BASES_RE') else 3, width=60)
        ent.grid(row=r, column=1, pady=(6,0))
        ent.insert('1.0', config.get('Syntax', f'regex.{key}', fallback=_DEFAULT_REGEXES.get(key, '')))
        regex_entries[key] = ent
        r += 1

    # Preset selector (dropdown) + preview/import actions
    preset_frame = ttk.Frame(container)
    preset_frame.grid(row=1, column=0, columnspan=2, pady=(8,6), sticky='ew')
    preset_frame.columnconfigure(1, weight=1)

    ttk.Label(preset_frame, text="Import preset:").grid(row=0, column=0, sticky='w')
    preset_var = StringVar(value='')
    preset_combo = ttk.Combobox(preset_frame, textvariable=preset_var, state='readonly', width=40)
    preset_combo.grid(row=0, column=1, sticky='ew', padx=(6,4))

    presets = scan_syntax_dir()
    preset_paths = []
    try:
        preset_names = [name for (_, name) in presets]
        preset_paths = [path for (path, _) in presets]
        preset_combo['values'] = preset_names
    except Exception:
        preset_combo['values'] = []

    def load_preset_into_dialog(path):
        """Populate dialog fields from an INI at `path` (preview, no persistence)."""
        try:
            cp = configparser.ConfigParser()
            cp.read(path)
            # tags
            for tag, _ in _DEFAULT_TAG_COLORS.items():
                fg_val = cp.get('Syntax', f'tag.{tag}.fg', fallback='')
                bg_val = cp.get('Syntax', f'tag.{tag}.bg', fallback='')
                inputs_fg[tag].delete(0, END)
                if fg_val:
                    inputs_fg[tag].insert(0, fg_val)
                inputs_bg[tag].delete(0, END)
                if bg_val:
                    inputs_bg[tag].insert(0, bg_val)
                # update swatches independently
                try:
                    if is_valid_color(fg_val):
                        swatches_fg[tag].config(bg=fg_val)
                    else:
                        swatches_fg[tag].config(bg=tab_tags.cget('background'))
                except Exception:
                    pass
                try:
                    if is_valid_color(bg_val):
                        swatches_bg[tag].config(bg=bg_val)
                    else:
                        swatches_bg[tag].config(bg=tab_tags.cget('background'))
                except Exception:
                    pass
            # lists
            kw_ent.delete(0, END)
            kw_ent.insert(0, cp.get('Syntax', 'keywords.csv', fallback=','.join(KEYWORDS)))
            bk_ent.delete(0, END)
            bk_ent.insert(0, cp.get('Syntax', 'builtins.csv', fallback=','.join(BUILTINS)))
            # regexes
            for key, ent in regex_entries.items():
                ent.delete('1.0', 'end')
                ent.insert('1.0', cp.get('Syntax', f'regex.{key}', fallback=_DEFAULT_REGEXES.get(key, '')))
        except Exception:
            pass

    def on_preview():
        sel = preset_combo.current()
        if sel is None or sel < 0 or sel >= len(preset_paths):
            return
        load_preset_into_dialog(preset_paths[sel])

    def on_import():
        """Copy chosen preset values into main config, persist, and apply."""
        sel = preset_combo.current()
        if sel is None or sel < 0 or sel >= len(preset_paths):
            return
        path = preset_paths[sel]
        try:
            cp = configparser.ConfigParser()
            cp.read(path)
            if not config.has_section('Syntax'):
                config.add_section('Syntax')
            # tags
            for tag, _ in _DEFAULT_TAG_COLORS.items():
                fg_val = cp.get('Syntax', f'tag.{tag}.fg', fallback='').strip()
                bg_val = cp.get('Syntax', f'tag.{tag}.bg', fallback='').strip()
                if fg_val:
                    config.set('Syntax', f'tag.{tag}.fg', fg_val)
                else:
                    try:
                        config.remove_option('Syntax', f'tag.{tag}.fg')
                    except Exception:
                        pass
                if bg_val:
                    config.set('Syntax', f'tag.{tag}.bg', bg_val)
                else:
                    try:
                        config.remove_option('Syntax', f'tag.{tag}.bg')
                    except Exception:
                        pass
            # lists
            kw = cp.get('Syntax', 'keywords.csv', fallback='').strip()
            bk = cp.get('Syntax', 'builtins.csv', fallback='').strip()
            if kw:
                config.set('Syntax', 'keywords.csv', kw)
            else:
                try:
                    config.remove_option('Syntax', 'keywords.csv')
                except Exception:
                    pass
            if bk:
                config.set('Syntax', 'builtins.csv', bk)
            else:
                try:
                    config.remove_option('Syntax', 'builtins.csv')
                except Exception:
                    pass
            # regexes
            for key in regex_entries.keys():
                txt = cp.get('Syntax', f'regex.{key}', fallback='').strip()
                if txt:
                    config.set('Syntax', f'regex.{key}', txt)
                else:
                    try:
                        config.remove_option('Syntax', f'regex.{key}')
                    except Exception:
                        pass
            # optional: copy a human-readable preset name into config
            try:
                preset_name = cp.get('Syntax', 'name', fallback='')
                if preset_name:
                    config.set('Syntax', 'preset_name', preset_name)
            except Exception:
                pass
            # persist
            with open(INI_PATH, 'w') as f:
                config.write(f)
            # apply and close
            load_syntax_config()
            dlg.destroy()
        except Exception:
            pass

    btn_preview = ttk.Button(preset_frame, text='Preview', command=on_preview)
    btn_preview.grid(row=0, column=2, padx=(4,2))
    btn_import = ttk.Button(preset_frame, text='Import', command=on_import)
    btn_import.grid(row=0, column=3, padx=(2,0))
    btn_export = ttk.Button(preset_frame, text='Export Preset', command=lambda: export_syntax_preset(inputs_fg, inputs_bg, kw_ent, bk_ent, regex_entries))
    btn_export.grid(row=0, column=4, padx=6)

    # Buttons (Save / Reset / Close)
    btn_frame = ttk.Frame(container)
    btn_frame.grid(row=2, column=0, columnspan=2, pady=(8,0), sticky='ew')
    btn_frame.columnconfigure(0, weight=1)

    def do_save():
        if not config.has_section('Syntax'):
            config.add_section('Syntax')
        # tags: save both fg and bg
        for tag in inputs_fg.keys():
            fg_val = inputs_fg[tag].get().strip()
            bg_val = inputs_bg[tag].get().strip()
            if fg_val:
                config.set('Syntax', f'tag.{tag}.fg', fg_val)
            else:
                try:
                    config.remove_option('Syntax', f'tag.{tag}.fg')
                except Exception:
                    pass
            if bg_val:
                config.set('Syntax', f'tag.{tag}.bg', bg_val)
            else:
                try:
                    config.remove_option('Syntax', f'tag.{tag}.bg')
                except Exception:
                    pass
        # lists
        config.set('Syntax', 'keywords.csv', kw_ent.get().strip())
        config.set('Syntax', 'builtins.csv', bk_ent.get().strip())
        # regexes
        for key, ent in regex_entries.items():
            txt = ent.get('1.0', 'end-1c').strip()
            if txt:
                config.set('Syntax', f'regex.{key}', txt)
            else:
                try:
                    config.remove_option('Syntax', f'regex.{key}')
                except Exception:
                    pass
        try:
            with open(INI_PATH, 'w') as f:
                config.write(f)
        except Exception:
            pass
        load_syntax_config()
        dlg.destroy()

    def do_reset():
        # clear Syntax section so defaults are used
        try:
            if config.has_section('Syntax'):
                config.remove_section('Syntax')
            with open(INI_PATH, 'w') as f:
                config.write(f)
        except Exception:
            pass
        # update UI to defaults (both fg and bg)
        for tag, defaults in _DEFAULT_TAG_COLORS.items():
            inputs_fg[tag].delete(0, END)
            if defaults.get('fg'):
                inputs_fg[tag].insert(0, defaults.get('fg'))
            inputs_bg[tag].delete(0, END)
            if defaults.get('bg'):
                inputs_bg[tag].insert(0, defaults.get('bg'))
            # update swatches independently
            try:
                df = defaults.get('fg') or ''
                if is_valid_color(df):
                    swatches_fg[tag].config(bg=df)
                else:
                    swatches_fg[tag].config(bg=tab_tags.cget('background'))
            except Exception:
                pass
            try:
                db = defaults.get('bg') or ''
                if is_valid_color(db):
                    swatches_bg[tag].config(bg=db)
                else:
                    swatches_bg[tag].config(bg=tab_tags.cget('background'))
            except Exception:
                pass
        kw_ent.delete(0, END)
        kw_ent.insert(0, ','.join(KEYWORDS))
        bk_ent.delete(0, END)
        bk_ent.insert(0, ','.join(BUILTINS))
        for key, ent in regex_entries.items():
            ent.delete('1.0', 'end')
            ent.insert('1.0', _DEFAULT_REGEXES.get(key, ''))

    ttk.Button(btn_frame, text='Save', command=do_save).grid(row=0, column=1, padx=6)
    ttk.Button(btn_frame, text='Reset to defaults', command=do_reset).grid(row=0, column=2, padx=6)
    ttk.Button(btn_frame, text='Close', command=dlg.destroy).grid(row=0, column=3, padx=6)

    center_window(dlg)

# persisted symbol buffers (vars + defs) — load/save from config
def _load_symbol_buffers():
    vars_raw = config.get('Symbols', 'vars', fallback='')
    defs_raw = config.get('Symbols', 'defs', fallback='')
    vars_set = set(x for x in (v.strip() for v in vars_raw.split(',')) if x)
    defs_set = set(x for x in (d.strip() for d in defs_raw.split(',')) if x)
    return vars_set, defs_set

# Add menu and toolbar entries (safe to run anywhere after fileMenu/toolBar exist)
try:
    # Insert "Open URL..." into File menu (position after Open)
    try:
        fileMenu.insert_command(3, label='Open URL...', command=lambda: open_url_action())
    except Exception:
        # if insert_command not supported simply add at end
        fileMenu.add_command(label='Open URL...', command=lambda: open_url_action())
except Exception:
    pass

def open_url_from_field():
    """Handler for toolbar Open URL button: use URL field if present, otherwise show dialog."""
    try:
        u = url_var.get().strip() if 'url_var' in globals() else ''
        if u:
            fetch_and_open_url(u, open_in_new_tab=True)
            return
        # fallback to the dialog if the field is empty
        open_url_action()
    except Exception:
        try:
            open_url_action()
        except Exception:
            pass

try:
    # Back button
    backBtn = Button(toolBar, text='◀', width=3, command=_back_action, state=DISABLED)
    backBtn.pack(side=LEFT, padx=(6,2), pady=2)

    # History dropdown (Menubutton)
    urlHistoryBtn = Menubutton(toolBar, text='History', relief=RAISED)
    urlHistoryBtn.history_menu = Menu(urlHistoryBtn, tearoff=0)
    urlHistoryBtn.config(menu=urlHistoryBtn.history_menu)
    urlHistoryBtn.pack(side=LEFT, padx=(2,2), pady=2)
    brainless_chk = ttk.Checkbutton(toolBar, text='Brainless Mode', variable=brainless_mode_var)
    brainless_chk.pack(side=LEFT, padx=(6,2), pady=2)
    # URL entry + Open
    url_entry = Entry(toolBar, textvariable=url_var, width=40)
    url_entry.pack(side=LEFT, padx=(6,2), pady=2)
    btnOpenURL = Button(toolBar, text='Open URL', command=open_url_from_field)
    btnOpenURL.pack(side=LEFT, padx=2, pady=2)

    # Refresh button
    refreshBtn = Button(toolBar, text='⟳', width=3, command=_refresh_action)
    refreshBtn.pack(side=LEFT, padx=(2,6), pady=2)

    # initialize history menu from persisted store
    update_url_history_menu()
except Exception:
    pass

def _save_symbol_buffers(vars_set, defs_set):
    if not config.has_section('Symbols'):
        config.add_section('Symbols')
    config.set('Symbols', 'vars', ','.join(sorted(vars_set)))
    config.set('Symbols', 'defs', ','.join(sorted(defs_set)))
    try:
        with open(INI_PATH, 'w') as f:
            config.write(f)
    except Exception:
        pass

def _serialize_formatting():
    """Return header string (commented base64 JSON) for current tags, hyperlinks and tag configs.

    Coalesce legacy bold/italic/underline into combined `style_*` tags (per-font when possible)
    so round-trips restore composed styling reliably.
    """
    try:
        if not textArea:
            return ''

        # Tags we explicitly consider internal / syntax-only and should NOT be serialized
        internal_tags = {
            'string', 'keyword', 'comment', 'selfs', 'def', 'number', 'variable',
            'decorator', 'class_name', 'constant', 'attribute', 'builtin', 'todo',
            'currentLine', 'trailingWhitespace', 'find_match', 'number', 'operator',
            # marquee is presentation-only and animated; we still save ranges but visual priority handled by tags
        }

        # Build tag -> ranges dict by inspecting all widget tags (raw tags)
        tags_data = {}
        for tag in textArea.tag_names():
            try:
                if tag in internal_tags:
                    continue
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
                    tags_data[tag] = arr
            except Exception:
                pass

        # collect hyperlink mappings (if any) and convert to absolute offsets
        links = []
        try:
            mapping = getattr(textArea, '_hyperlink_map', {}) or {}
            for (s_idx, e_idx), entry in mapping.items():
                try:
                    snorm = textArea.index(s_idx)
                    enorm = textArea.index(e_idx)
                    start = len(textArea.get('1.0', snorm))
                    end = len(textArea.get('1.0', enorm))
                    if end <= start:
                        continue
                    if isinstance(entry, dict):
                        href = entry.get('href') or ''
                        title = entry.get('title') or None
                    else:
                        href = str(entry or '')
                        title = None
                    if not href:
                        continue
                    rec = {'start': start, 'end': end, 'href': href}
                    if title:
                        rec['title'] = title
                    links.append(rec)
                except Exception:
                    continue
        except Exception:
            links = []

        # Collect raw tag visual configs for tags we will save (store values as-is)
        tag_configs = {}
        try:
            for tag in sorted(tags_data.keys()):
                try:
                    cfg = {}
                    for opt in ('foreground', 'background', 'font', 'underline', 'overstrike'):
                        try:
                            val = textArea.tag_cget(tag, opt)
                        except Exception:
                            val = None
                        if val is not None and str(val).strip() != '':
                            cfg[opt] = str(val)
                    if not cfg and tag.startswith('font_'):
                        try:
                            hexpart = tag.split('_', 1)[1]
                            if re.match(r'^[0-9a-fA-F]{6}$', hexpart):
                                cfg['foreground'] = f"#{hexpart.lower()}"
                        except Exception:
                            pass
                    if cfg:
                        tag_configs[tag] = cfg
                except Exception:
                    pass
        except Exception:
            tag_configs = {}

        # Build composed style ranges from legacy tags (bold/italic/underline combos) partitioned per-font
        try:
            content = textArea.get('1.0', 'end-1c')
            N = len(content)
            if N > 0:
                # boolean arrays
                b_arr = [False] * N
                i_arr = [False] * N
                u_arr = [False] * N

                # helper mark ranges
                def mark_flag_for_tag(tname, b=False, i=False, u=False):
                    try:
                        for j in range(0, len(textArea.tag_ranges(tname)), 2):
                            s = textArea.tag_ranges(tname)[j]
                            e = textArea.tag_ranges(tname)[j+1]
                            so = len(textArea.get('1.0', s))
                            eo = len(textArea.get('1.0', e))
                            so = max(0, min(N, so))
                            eo = max(0, min(N, eo))
                            for p in range(so, eo):
                                if b:
                                    b_arr[p] = True
                                if i:
                                    i_arr[p] = True
                                if u:
                                    u_arr[p] = True
                    except Exception:
                        pass

                # mark legacy tags
                mark_flag_for_tag('bold', b=True)
                mark_flag_for_tag('italic', i=True)
                mark_flag_for_tag('underline', u=True)
                mark_flag_for_tag('bolditalic', b=True, i=True)
                mark_flag_for_tag('boldunderline', b=True, u=True)
                mark_flag_for_tag('underlineitalic', i=True, u=True)
                mark_flag_for_tag('all', b=True, i=True, u=True)

                # iterate and group contiguous spans by (b,i,u,font_tag)
                p = 0
                while p < N:
                    b = b_arr[p]
                    i = i_arr[p]
                    u = u_arr[p]
                    # if no style flags at this char move on
                    if not (b or i or u):
                        p += 1
                        continue
                    # determine font tag at this position
                    idx = textArea.index(f"1.0 + {p}c")
                    tags_here = textArea.tag_names(idx)
                    font_here = None
                    for tt in tags_here:
                        if tt.startswith('font_'):
                            font_here = tt
                            break
                    # find run end where all attributes and font_here remain the same
                    run_end = p + 1
                    while run_end < N:
                        if b_arr[run_end] != b or i_arr[run_end] != i or u_arr[run_end] != u:
                            break
                        idx2 = textArea.index(f"1.0 + {run_end}c")
                        tags2 = textArea.tag_names(idx2)
                        f2 = None
                        for tt in tags2:
                            if tt.startswith('font_'):
                                f2 = tt
                                break
                        if f2 != font_here:
                            break
                        run_end += 1
                    # construct style tag and record range
                    style_tag = _make_style_tag_name(font_here, b, i, u)
                    tags_data.setdefault(style_tag, []).append([p, run_end])
                    # create tag_config for style_tag so load can reproduce composed font
                    if style_tag not in tag_configs:
                        try:
                            cfg = {}
                            # derive base family/size from font_here if present
                            fam = fontName
                            sz = fontSize
                            if font_here:
                                try:
                                    fval = textArea.tag_cget(font_here, 'font')
                                    if fval:
                                        fobj = tkfont.Font(font=fval)
                                        fam = fobj.actual('family') or fam
                                        sz = int(fobj.actual('size') or sz)
                                except Exception:
                                    pass
                            # build font string preserving family/size and adding weight/slant
                            font_parts = [str(fam), str(sz)]
                            if b:
                                font_parts.append('bold')
                            if i:
                                font_parts.append('italic')
                            cfg['font'] = ' '.join(font_parts)
                            if u:
                                cfg['underline'] = 1
                            tag_configs[style_tag] = cfg
                        except Exception:
                            pass
                    p = run_end
        except Exception:
            pass

        # Remove legacy simple style tags from tags_data and tag_configs to avoid duplication
        for legacy in ('bold', 'italic', 'underline', 'bolditalic', 'boldunderline', 'underlineitalic', 'all'):
            try:
                if legacy in tags_data:
                    tags_data.pop(legacy, None)
                if legacy in tag_configs:
                    tag_configs.pop(legacy, None)
            except Exception:
                pass

        # nothing to save -> return empty
        if not tags_data and not links and not tag_configs:
            return ''

        meta = {'version': 1, 'tags': tags_data}
        if links:
            meta['links'] = links
        if tag_configs:
            meta['tag_configs'] = tag_configs

        b64 = base64.b64encode(json.dumps(meta).encode('utf-8')).decode('ascii')
        return "# ---SIMPLEEDIT-META-BEGIN---\n# " + b64 + "\n# ---SIMPLEEDIT-META-END---\n"
    except Exception:
        return ''

def _apply_template_to_widget(tw, kind: str):
    """Replace widget content with a standard template for `kind` ('html'|'python'|'md'|'json')."""
    try:
        if kind == 'html':
            tpl = (
                "<!doctype html>\n"
                "<html lang=\"en\">\n"
                "<head>\n"
                "  <meta charset=\"utf-8\">\n"
                "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
                "  <title>SimpleEdit — HTML Template (demo)</title>\n"
                "  <!-- demo CSS to show semantic classes and colors used by the editor export -->\n"
                "  <style>\n"
                "    body { background:#ffffff; color:#111; font-family:Segoe UI, Roboto, Arial, sans-serif; padding:16px; }\n"
                "    .nav { background:#f3f4f6; padding:8px; border-radius:4px; }\n"
                "    .content { margin-top:12px; }\n"
                "    pre { background:#f5f5f5; padding:8px; border-radius:4px; overflow:auto }\n"
                "    table { border-collapse:collapse; margin-top:8px }\n"
                "    th, td { border:1px solid #ccc; padding:8px }\n"
                "    .todo { color:#fff; background:#B22222; padding:2px 6px; border-radius:3px }\n"
                "  </style>\n"
                "</head>\n"
                "<body>\n"
                "  <!-- HTML comment: top-of-file demo -->\n"
                "  <header class=\"nav\">\n"
                "    <h1>SimpleEdit HTML demo</h1>\n"
                "    <p><small>Shows element names, attributes, attribute-values, comments and special cases.</small></p>\n"
                "  </header>\n"
                "  <section class=\"content\">\n"
                "    <h2>Elements & Attributes</h2>\n"
                "    <p>Tag name example: <code>&lt;section&gt;</code>, attribute examples below:</p>\n                \n                "  
                "<div data-info=demo disabled title='A single-quoted title' custom-flag>\n"
                "      <p>Unquoted attribute: <code>data-info=demo</code></p>\n                "
                "      <p>Double-quoted attribute: <code>class=\"content\"</code></p>\n"
                "      <p>Single-quoted attribute: <code>title='A single-quoted title'</code></p>\n"
                "    </div>\n"
                "\n"
                "    <h3>Inline styles & font tag</h3>\n"
                "    <p><span style=\"color:#CE9178\">Span with inline style (color) — should map to font_xxxxxx</span></p>\n"
                "    <p><font color=\"#ff0000\">Legacy &lt;font&gt; tag (color)</font> — parser maps this to font_xxxxxx too.</p>\n"
                "\n"
                "    <h3>Attribute value styles</h3>\n"
                "    <p><img src=\"https://via.placeholder.com/120\" alt=\"placeholder\" width=120 height=80></p>\n"
                "\n"
                "    <h3>Links</h3>\n"
                "    <p><a href=\"https://example.com\" title=\"Example site\">Visit Example.com</a> — anchor with href + title.</p>\n"
                "    <p>Markdown-style link example: <code>[Example](https://example.com)</code></p>\n"
                "\n"
                "    <h3>Comments & TODO</h3>\n"
                "    <!-- This is an HTML comment and should be highlighted as such -->\n"
                "    <p>Inline TODO example: <span style=\"background:#B22222;color:#ffffff\" class=\"todo\">TODO: update content</span></p>\n"
                "\n"
                "    <h3>Table (parsed to td/th ranges)</h3>\n"
                "    <table>\n"
                "      <thead>\n"
                "        <tr><th>Feature</th><th>Example</th></tr>\n"
                "      </thead>\n"
                "      <tbody>\n"
                "        <tr><td>Marquee</td><td>&lt;marquee&gt; — legacy but supported in demo</td></tr>\n"
                "        <tr><td>Attributes</td><td>single/double/unquoted</td></tr>\n"
                "      </tbody>\n"
                "    </table>\n"
                "\n"
                "    <h3>Code & pre</h3>\n"
                "    <pre><code>&lt;!-- Example snippet --&gt;\n"
                "&lt;div class=&quot;widget&quot;&gt;Hello&lt;/div&gt;\n"
                "</code></pre>\n"
                "\n"
                "    <h3>Script & Style blocks</h3>\n"
                "    <style>/* inline css example */ .widget{color:#FF5733}</style>\n"
                "    <script>/* inline JS example */ console.log('hello from demo');</script>\n"
                "\n"
                "    <p>Example hex color literal: <code>#FF5733</code></p>\n"
                "\n"
                "    <p>Back-to-top: <a href=\"#\">Top</a></p>\n"
                "\n"
                "    <hr />\n"
                "    <footer><small>Generated by SimpleEdit — template demonstrates parser features: html_tag, html_attr, html_attr_value, html_comment, font_*, todo, table ranges, hyperlinks.</small></footer>\n"
                "  </section>\n"
                "</body>\n"
                "</html>\n"
            )
        elif kind == 'md' or kind == 'markdown':
            tpl = (
                "# Title\n\n"
                "A short description paragraph.\n\n"
                "## Features\n\n"
                "- Feature one\n"
                "- Feature two\n\n"
                "### Example Code\n\n"
                "```python\n"
                "def hello():\n"
                "    print('Hello, Markdown')\n"
                "```\n\n"
                "## Notes\n\n"
                "Write your content here.\n"
            )
        elif kind == 'json':
            tpl = (
                "{\n"
                '  "name": "example",\n'
                '  "version": "1.0.0",\n'
                '  "description": "A sample JSON document",\n'
                '  "items": [\n'
                '    { "id": 1, "name": "Item One" },\n'
                '    { "id": 2, "name": "Item Two" }\n'
                "  ]\n"
                "}\n"
            )
        else:  # python (default)
            tpl = (
                "#!/usr/bin/env python3\n"
                "# -*- coding: utf-8 -*-\n"
                "\"\"\"\n"
                "Module description.\n"
                "\"\"\"\n\n"
                "def main():\n"
                "    pass\n\n\n"
                "if __name__ == \"__main__\":\n"
                "    main()\n"
            )
        tw.delete('1.0', 'end')
        tw.insert('1.0', tpl)
        try:
            # ensure tags/configs applied to this widget after replacing text
            _apply_tag_configs_to_widget(tw)
            # best-effort re-highlight (Python/Markdown may benefit)
            highlight_python_helper(None, scan_start="1.0", scan_end="end-1c")
        except Exception:
            pass
    except Exception:
        pass

def create_template(kind: str, open_in_new_tab: bool = True):
    """Create a template of `kind` ('python'|'html'|'md'|'json').

    By default opens in a new tab. Uses `_apply_template_to_widget` for content.
    """
    try:
        title_map = {
            'python': 'New - Python',
            'html': 'New - HTML',
            'md': 'New - Markdown',
            'markdown': 'New - Markdown',
            'json': 'New - JSON'
        }
        kind_norm = (kind or 'python').lower()
        title = title_map.get(kind_norm, 'Untitled')

        if open_in_new_tab:
            tx, fr = create_editor_tab(title, '', filename='')
            # Insert template into the new text widget
            try:
                _apply_template_to_widget(tx, kind_norm)
                _apply_tag_configs_to_widget(tx)
                tx.focus_set()
            except Exception:
                pass
            return tx, fr

        # fallback: replace current tab content
        try:
            textArea.delete('1.0', 'end')
            _apply_template_to_widget(textArea, kind_norm)
            _apply_tag_configs_to_widget(textArea)
            textArea.focus_set()
            # ensure per-tab metadata updated
            sel = editorNotebook.select()
            if sel:
                try:
                    frame = root.nametowidget(sel)
                    frame.fileName = ''
                except Exception:
                    pass
            root.fileName = ''
        except Exception:
            pass
        return textArea, getattr(root, 'nametowidget', lambda s: None)(editorNotebook.select())
    except Exception:
        return None, None

def _ask_template_modal(kind: str, tw):
    """Show modal asking whether to create a template for kind in widget `tw`."""
    try:
        if globals().get('suppress_template_prompt_session') and suppress_template_prompt_session.get():
                return
    except Exception:
        pass
    try:
        dlg = Toplevel(root)
        dlg.transient(root)
        dlg.grab_set()
        dlg.title("Create Template?")
        container = ttk.Frame(dlg, padding=12)
        container.grid(row=0, column=0, sticky='nsew')
        msg = f"Hey — it looks like you're starting an {kind.upper()} file.\nWould you like me to create a standard {kind.upper()} template for this tab?"
        ttk.Label(container, text=msg, justify='left').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0,8))

        remember_var = IntVar(value=0)
        ttk.Checkbutton(container, text="Don't ask again for this tab", variable=suppress_template_prompt_session).grid(row=1, column=0, columnspan=2, sticky='w')

        def do_cancel():
            try:
                dlg.grab_release()
            except Exception:
                pass
            dlg.destroy()

        def do_create():
            try:
                frame = tw.master
                if remember_var.get():
                    if kind == 'html':
                        setattr(frame, '_template_prompted_html', True)
                        # also set flag on the Text widget itself to be robust
                        try:
                            setattr(tw, '_template_prompted_html', True)
                        except Exception:
                            pass
                    else:
                        setattr(frame, '_template_prompted_py', True)
                        try:
                            setattr(tw, '_template_prompted_py', True)
                        except Exception:
                            pass
                    # Also suppress all template prompts for this session (modal checkbox => session opt-out)
                    try:
                        suppress_template_prompt_session.set(True)
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                _apply_template_to_widget(tw, kind)
            finally:
                try:
                    dlg.grab_release()
                except Exception:
                    pass
                dlg.destroy()

        btns = ttk.Frame(container)
        btns.grid(row=2, column=0, columnspan=2, sticky='e', pady=(8,0))
        ttk.Button(btns, text="Yes", command=do_create).pack(side=RIGHT, padx=(6,0))
        ttk.Button(btns, text="No", command=do_cancel).pack(side=RIGHT)
        dlg.update_idletasks()
        center_window(dlg)
    except Exception:
        pass


def detect_header_and_prompt(event=None):
    """Detect typed file-header hints (HTML DOCTYPE/HTML or Python shebang/triple-quote) and prompt for templates."""
    try:
        # Session opt-out: if user checked "Don't ask again" in any modal this session, skip prompting
        try:
            if globals().get('suppress_template_prompt_session') and suppress_template_prompt_session.get():
                return
        except Exception:
            pass
        # Global opt-out: toolbar checkbox 'Suppress Template Prompt' — when checked we skip prompting
        try:
            if globals().get('templatePromptVar', BooleanVar(value=False)).get():
                return
        except Exception:
            pass
        if not event or not hasattr(event, 'widget'):
            return
        tw = event.widget
        if not isinstance(tw, Text):
            return

        # find parent frame (the tab frame)
        frame = getattr(tw, 'master', None)
        if frame is None:
            return

        # avoid repeated prompting per tab
        # consider flags set on the frame OR the text widget (be robust)
        html_prompted = getattr(frame, '_template_prompted_html', False) or getattr(tw, '_template_prompted_html', False)
        py_prompted = getattr(frame, '_template_prompted_py', False) or getattr(tw, '_template_prompted_py', False)
        if html_prompted and py_prompted:            return

        # inspect the start of buffer and the line around insert
        try:
            head = tw.get('1.0', '1.0 + 1024c').lower()
        except Exception:
            head = ''

        # Improved HTML detection:
        # - existing checks for DOCTYPE / <html remain
        # - also detect presence of <table>, <th>, or common HTML head tags early
        is_html_sig = False
        try:
            if ('<!doctype html' in head) or ('<html' in head) or ('<head' in head) or ('<body' in head):
                is_html_sig = True
            # table-ish content often indicates HTML fragment
            if not is_html_sig and ('<table' in head or '<th' in head or '<tr' in head or '<td' in head):
                is_html_sig = True
        except Exception:
            is_html_sig = False

        # HTML prompt
        if (not getattr(frame, '_template_prompted_html', False)) and is_html_sig:
            _ask_template_modal('html', tw)
            return

        # Python detection: shebang at start or triple quote at top
        if not getattr(frame, '_template_prompted_py', False):
            stripped = head.lstrip()
            if stripped.startswith('#!') or stripped.startswith('"""') or stripped.startswith("'''"):
                _ask_template_modal('python', tw)
                return
    except Exception:
        pass

def _init_toolbar_color_buttons():
    """Apply FG/BG appearances after UI is realized. Run a couple of times to work around platform theme timing.

    If the configured color is blank/invalid we explicitly set the button text color to white so
    the label remains readable even on dark/unknown backgrounds.
    """
    try:
        for btn, var in ((btn_fg, fg_color_var), (btn_bg, bg_color_var)):
            try:
                c = (var.get() or '').strip()
                if c and is_valid_color(c):
                    contrast = _contrast_text_color(c)
                    # Apply both common option names and multiple states to increase chance platform honors them.
                    try:
                        btn.configure(bg=c, activebackground=c, activeforeground=contrast)
                    except Exception:
                        pass
                    try:
                        btn.configure(fg=contrast, foreground=contrast)
                    except Exception:
                        pass
                else:
                    # No valid color configured -> ensure button text is white for readability
                    try:
                        btn.configure(fg='#FFFFFF', activeforeground='#FFFFFF')
                    except Exception:
                        pass

                # Some platforms/themes only apply appearance after a short delay / widget realization.
                try:
                    btn.update_idletasks()
                    btn.update()
                except Exception:
                    pass
            except Exception:
                pass
    except Exception:
        pass

def _apply_formatting_from_meta(meta):
    """Apply saved tag ranges (meta is dict with key 'tags' and optional 'links' and 'tag_configs') on the UI thread.

    This version applies the saved tag_cget values directly (no special parsing/normalization).
    """
    try:
        tags = meta.get('tags', {}) if isinstance(meta, dict) else {}

        # Apply any explicit tag visual configs exactly as saved (foreground/background/font/underline/overstrike)
        try:
            tag_configs = meta.get('tag_configs', {}) if isinstance(meta, dict) else {}
            if tag_configs:
                for tag, cfg in tag_configs.items():
                    try:
                        kwargs = {}
                        for opt in ('foreground', 'background', 'font', 'underline', 'overstrike'):
                            v = cfg.get(opt)
                            if v is not None and str(v).strip() != '':
                                kwargs[opt] = v
                        if kwargs:
                            # apply per-widget so visuals survive round-trip
                            _safe_tag_config(textArea, tag, foreground=kwargs.get('foreground'), background=kwargs.get('background'))
                    except Exception:
                        pass
        except Exception:
            pass

        # Legacy: ensure any per-color font_xxxxxx tags still get a fallback color if missing
        try:
            for tag in list(tags.keys()):
                if tag.startswith("font_"):
                    hexpart = tag.split("_", 1)[1] if "_" in tag else ''
                    if re.match(r'^[0-9a-fA-F]{6}$', hexpart):
                        color = f"#{hexpart.lower()}"
                        try:
                            root.winfo_rgb(color)
                            cur = ''
                            try:
                                cur = textArea.tag_cget(tag, 'foreground') or ''
                            except Exception:
                                cur = ''
                            if not cur:
                                textArea.tag_config(tag, foreground=color)
                        except Exception:
                            pass
        except Exception:
            pass

        # Ensure sensible defaults for presentational tags if not configured
        try:
            for present in ('mark', 'code', 'kbd', 'sub', 'sup', 'small', 'marquee'):
                if present in tags:
                    try:
                        has_font = bool(textArea.tag_cget(present, "font"))
                        has_bg = bool(textArea.tag_cget(present, "background"))
                    except Exception:
                        has_font = False
                        has_bg = False
                    if not has_font and not has_bg:
                        try:
                            if present == 'mark':
                                textArea.tag_config(present, background="#FFF177")
                            elif present in ('code', 'kbd'):
                                textArea.tag_config(present, font=("Courier New", max(6, int(fontSize - 1))), background="#F5F5F5")
                            elif present in ('sub', 'sup', 'small'):
                                textArea.tag_config(present, font=(fontName, max(6, int(fontSize - 2))))
                            elif present == 'marquee':
                                textArea.tag_config('marquee', foreground="#FF4500")
                        except Exception:
                            pass
        except Exception:
            pass

        # Apply tag ranges (after configs applied)
        for tag, ranges in tags.items():
            for start, end in ranges:
                try:
                    textArea.tag_add(tag, f"1.0 + {int(start)}c", f"1.0 + {int(end)}c")
                except Exception:
                    pass

        # Restore explicit links produced by parser (if any)
        try:
            links = meta.get('links', []) if isinstance(meta, dict) else []
            if links:
                if not hasattr(textArea, '_hyperlink_map'):
                    textArea._hyperlink_map = {}
                for link in links:
                    try:
                        s = int(link.get('start', 0))
                        e = int(link.get('end', 0))
                        href = str(link.get('href', '')).strip()
                        title = link.get('title') or link.get('text') or None
                        if e > s and href:
                            start_idx = textArea.index(f"1.0 + {s}c")
                            end_idx = textArea.index(f"1.0 + {e}c")
                            try:
                                textArea.tag_add('hyperlink', start_idx, end_idx)
                            except Exception:
                                pass
                            try:
                                entry = {'href': href}
                                if title:
                                    entry['title'] = title
                                textArea._hyperlink_map[(start_idx, end_idx)] = entry
                            except Exception:
                                pass
                    except Exception:
                        pass
        except Exception:
            pass
        # ensure any literal hex codes are colored as well (HTML imports may introduce them)
        try:
            color_hex_codes()
        except Exception:
            pass

    except Exception:
        pass

def toggle_raw_rendered():
    """Toggle current tab between raw HTML and rendered (parsed/plain + tags).

    Behavior improvements:
    - When switching FROM Raw -> Rendered we parse the *current* buffer contents (so edits made
      in Raw view are immediately re-rendered without needing to save/reload).
    - When switching FROM Rendered -> Raw we prefer the stored raw source (if any); otherwise
      show the current rendered/plain text as a fallback raw representation.
    """
    try:
        sel = editorNotebook.select()
        if not sel:
            return
        frame = root.nametowidget(sel)
        # find the Text widget inside frame
        tw = None
        for child in frame.winfo_children():
            if isinstance(child, Text):
                tw = child
                break
        if tw is None:
            return

        # If there's no stored raw at all and no parsed data, nothing to do
        raw_stored = getattr(frame, '_raw_html', None)
        currently_raw = bool(getattr(frame, '_view_raw', False))

        if currently_raw:
            # User is viewing/editing raw HTML. Re-parse the *current* buffer content and render it.
            try:
                raw_text = tw.get('1.0', 'end-1c')
            except Exception:
                raw_text = raw_stored or ''

            # Persist the edited raw into frame so future toggles keep it
            try:
                frame._raw_html = raw_text
            except Exception:
                pass

            # Parse the current raw text into plain + tag meta (this re-renders from edits)
            try:
                plain, tags_meta = funcs._parse_html_and_apply(raw_text)
            except Exception:
                plain, tags_meta = raw_text, None

            # Store parsed results on the frame for toggling back later
            try:
                frame._raw_html_plain = plain
                frame._raw_html_tags_meta = tags_meta
            except Exception:
                pass

            # Replace widget content with parsed plain text and apply tag configs/meta
            try:
                tw.delete('1.0', 'end')
                tw.insert('1.0', plain or '')
                _apply_tag_configs_to_widget(tw)
                if tags_meta and tags_meta.get('tags'):
                    # Ensure _apply_formatting_from_meta operates on the correct widget
                    prev_ta = globals().get('textArea', None)
                    try:
                        globals()['textArea'] = tw
                        _apply_formatting_from_meta(tags_meta)
                    finally:
                        if prev_ta is not None:
                            globals()['textArea'] = prev_ta
                        else:
                            try:
                                del globals()['textArea']
                            except Exception:
                                pass
            except Exception:
                pass

            frame._view_raw = False
            statusBar['text'] = "Rendered HTML view (from current raw buffer)"
        else:
            # Currently rendered -> switch to raw. Prefer stored original raw if present,
            # otherwise fall back to the current text widget contents.
            try:
                raw_to_show = getattr(frame, '_raw_html', None)
                if not raw_to_show:
                    # If there is no stored raw, use the visible buffer as a reasonable raw fallback
                    raw_to_show = tw.get('1.0', 'end-1c')
                # persist to frame so toggles remain consistent
                try:
                    frame._raw_html = raw_to_show
                except Exception:
                    pass

                # show raw text
                tw.delete('1.0', 'end')
                tw.insert('1.0', raw_to_show or '')
                _apply_tag_configs_to_widget(tw)
                frame._view_raw = True
                statusBar['text'] = "Raw HTML view"
            except Exception:
                statusBar['text'] = "Failed to switch to Raw view"
        # refresh lightweight highlighting and UI
        try:
            safe_highlight_event(None)
        except Exception:
            pass
        # update toolbar/status indicator for current tab view
        try:
            update_view_status_indicator()
        except Exception:
            pass
    except Exception:
        pass

def update_view_status_indicator():
    """Update the small status label indicating Raw/Rendered and source/URL state for current tab."""
    try:
        # If viewIndicator doesn't exist (older UI), skip
        if 'viewIndicator' not in globals():
            return
        sel = editorNotebook.select()
        if not sel:
            viewIndicator.config(text='View: —')
            return
        frame = root.nametowidget(sel)
        view_raw = bool(getattr(frame, '_view_raw', False))
        opened_src = bool(getattr(frame, '_opened_as_source', False))
        fn = getattr(frame, 'fileName', '') or ''
        if view_raw:
            txt = 'View: Raw'
        else:
            txt = 'View: Rendered'
        if opened_src:
            txt += ' (source)'
        else:
            # annotate URL tabs
            try:
                if _is_likely_url(fn) or (isinstance(fn, str) and (fn.lower().startswith('http') or fn.lower().startswith('file:///') or fn.lower().startswith('www.'))):
                    txt += ' (URL)'
            except Exception:
                pass
        viewIndicator.config(text=txt)
    except Exception:
        pass

def safe_highlight_event(event=None):
    """
    Centralized event handler used by input/scroll/click bindings.

    - Runs the local syntax highlighter only when `updateSyntaxHighlighting` is enabled.
    - Always performs lightweight UI updates (current-line highlight, line numbers,
      status bar and trailing-whitespace) so the editor remains responsive.
    """
    try:
        # only run the (potentially expensive) syntax pass when enabled
        if updateSyntaxHighlighting.get():
            try:
                highlight_python_helper(event)
            except Exception:
                pass

        # lightweight UI updates always run
        try:
            highlight_current_line()
        except Exception:
            pass
        try:
            redraw_line_numbers()
        except Exception:
            pass
        try:
            update_status_bar()
        except Exception:
            pass
        try:
            show_trailing_whitespace()
        except Exception:
            pass
        # Always color literal hex codes even if syntax highlighting is off
        try:
            color_hex_codes()
        except Exception:
            pass
        try:
            _raise_hex_tags_above(textArea)
        except Exception:
            pass
    except Exception:
        pass

   
def _extract_header_and_meta(raw):
    """
    If raw begins with the SIMPLEEDIT header return (content, meta) where content
    is the visible file without header and meta is the parsed dict; otherwise return (raw, None).
    """
    try:
        if not raw.startswith("# ---SIMPLEEDIT-META-BEGIN---"):
            return raw, None
        lines = raw.splitlines(True)
        i = 0
        if lines[0].strip() != "# ---SIMPLEEDIT-META-BEGIN---":
            return raw, None
        i = 1
        b64_parts = []
        while i < len(lines) and lines[i].strip() != "# ---SIMPLEEDIT-META-END---":
            line = lines[i]
            if line.startswith('#'):
                b64_parts.append(line[1:].strip())
            i += 1
        if i >= len(lines):
            return raw, None
        # content starts after the END marker line
        content = ''.join(lines[i + 1:])
        b64 = ''.join(b64_parts)
        try:
            meta = json.loads(base64.b64decode(b64).decode('utf-8'))
            return content, meta
        except Exception:
            return content, None
    except Exception:
        return raw, None

def _apply_full_tags(actions, new_vars, new_defs):
    """Apply tag actions on the main/UI thread and persist discovered symbols."""
    try:
        # clear tags across the whole buffer first
        for t in ('string', 'keyword', 'comment', 'selfs', 'def', 'number', 'variable',
                  'decorator', 'class_name', 'constant', 'attribute', 'builtin', 'todo'):
            textArea.tag_remove(t, "1.0", "end")

        # add tags collected by the worker
        for tag, ranges in actions.items():
            if not ranges:
                continue
            for s, e in ranges:
                # s/e are absolute character offsets from start of buffer
                textArea.tag_add(tag, f"1.0 + {s}c", f"1.0 + {e}c")

        # persist newly discovered symbols (union)
        updated = False
        if new_vars:
            if not new_vars.issubset(persisted_vars):
                persisted_vars.update(new_vars)
                updated = True
        if new_defs:
            if not new_defs.issubset(persisted_defs):
                persisted_defs.update(new_defs)
                updated = True
        if updated:
            _save_symbol_buffers(persisted_vars, persisted_defs)

        statusBar['text'] = "Ready"
    except Exception:
        # keep UI resilient to errors
        pass


def _bg_full_scan_and_collect(content, progress_callback=None):
    """Background worker: scan content string and return tag ranges + discovered symbols.

    Accepts optional progress_callback(percent:int, message:str) which will be called
    periodically from the worker thread. Caller must ensure UI updates happen on main thread
    (i.e. use root.after inside the callback).
    Returns (actions_dict, new_vars_set, new_defs_set)
    where actions_dict is mapping tag -> list of (abs_start, abs_end) offsets.
    """
    actions = {
        'string': [], 'comment': [], 'number': [], 'decorator': [], 'class_name': [], 'variable': [],
        'constant': [], 'attribute': [], 'def': [], 'keyword': [], 'builtin': [], 'selfs': [], 'todo': []
    }

    def report(pct, msg=None):
        try:
            if progress_callback:
                progress_callback(int(pct), msg or "")
        except Exception:
            pass

    try:
        # We'll report progress in steps as we run each major pass.
        # List of passes (name, function to run)
        protected_spans = []

        # Pass 1: strings
        report(2, "Scanning strings...")
        for m in STRING_RE.finditer(content):
            s, e = m.span()
            actions['string'].append((s, e))
            protected_spans.append((s, e))
        report(8)

        # Pass 2: comments and TODOs
        report(9, "Scanning comments...")
        for m in COMMENT_RE.finditer(content):
            s, e = m.span()
            actions['comment'].append((s, e))
            protected_spans.append((s, e))
            mm = TODO_RE.search(content, m.start(), m.end())
            if mm:
                ts, te = mm.span()
                actions['todo'].append((ts, te))
        report(14)

        def overlaps_protected(s, e):
            for ps, pe in protected_spans:
                if not (e <= ps or s >= pe):
                    return True
            return False

        # Pass 3: numbers
        report(16, "Scanning numbers...")
        for i, m in enumerate(NUMBER_RE.finditer(content)):
            s, e = m.span()
            if not overlaps_protected(s, e):
                actions['number'].append((s, e))
            # occasionally yield progress
            if i and (i % 200) == 0:
                report(16 + min(10, i // 200), "Scanning numbers...")
                time.sleep(0)  # yield thread
        report(22)

        # Pass 4: decorators
        report(23, "Scanning decorators...")
        for m in DECORATOR_RE.finditer(content):
            s, e = m.span(1)
            if not overlaps_protected(s, e):
                actions['decorator'].append((s, e))
        report(27)

        # Pass 5: classes
        report(28, "Scanning classes...")
        for m in CLASS_RE.finditer(content):
            s, e = m.span(1)
            if not overlaps_protected(s, e):
                actions['class_name'].append((s, e))
        report(32)

        # Pass 6: variable assignments
        report(33, "Scanning variable assignments...")
        for i, m in enumerate(VAR_ASSIGN_RE.finditer(content)):
            s, e = m.span(1)
            if not overlaps_protected(s, e):
                actions['variable'].append((s, e))
            if i and (i % 200) == 0:
                report(33 + min(8, i // 200), "Scanning variable assignments...")
                time.sleep(0)
        report(41)

        # Pass 7: constants ALL_CAPS
        report(42, "Scanning constants...")
        for m in CONSTANT_RE.finditer(content):
            s, e = m.span(1)
            if not overlaps_protected(s, e):
                actions['constant'].append((s, e))
        report(46)

        # Pass 8: attributes (a.b -> tag 'b')
        report(47, "Scanning attributes...")
        for i, m in enumerate(ATTRIBUTE_RE.finditer(content)):
            s, e = m.span(1)
            if not overlaps_protected(s, e):
                actions['attribute'].append((s, e))
            if i and (i % 500) == 0:
                report(47 + min(8, i // 500), "Scanning attributes...")
                time.sleep(0)
        report(55)

        # Pass 9: dunder names
        report(56, "Scanning dunder names...")
        for m in DUNDER_RE.finditer(content):
            s, e = m.span()
            if not overlaps_protected(s, e):
                actions['def'].append((s, e))
        report(60)

        # Pass 10: f-strings (tag whole)
        report(61, "Scanning f-strings...")
        for m in FSTRING_RE.finditer(content):
            s, e = m.span()
            # already tagged as "string"; we keep for completeness
        report(64)

        # Pass 11: defs discovery and marking
        report(65, "Discovering defs...")
        try:
            DEF_RE = re.compile(r'(?m)^[ \t]*def\s+([A-Za-z_]\w*)\s*\(')
        except Exception:
            DEF_RE = None
        new_defs = set()
        if DEF_RE:
            for i, m in enumerate(DEF_RE.finditer(content)):
                name = m.group(1)
                new_defs.add(name)
                if i and (i % 200) == 0:
                    report(65 + min(6, i // 200), "Discovering defs...")
                    time.sleep(0)
        report(72)

        # Pass 12: create def-tags by searching occurrences
        report(73, "Tagging defs...")
        if new_defs:
            pattern = re.compile(r'\b(' + r'|'.join(re.escape(x) for x in new_defs) + r')\b')
            for m in pattern.finditer(content):
                s, e = m.span(1)
                if not overlaps_protected(s, e):
                    actions['def'].append((s, e))
        report(76)

        # Pass 13: keywords and builtins
        report(77, "Scanning keywords and builtins...")
        for i, m in enumerate(KEYWORD_RE.finditer(content)):
            s, e = m.span()
            if not overlaps_protected(s, e):
                actions['keyword'].append((s, e))
            if i and (i % 1000) == 0:
                report(77 + min(8, i // 1000), "Scanning keywords...")
                time.sleep(0)
        for i, m in enumerate(BUILTIN_RE.finditer(content)):
            s, e = m.span()
            if not overlaps_protected(s, e):
                actions['builtin'].append((s, e))
            if i and (i % 1000) == 0:
                report(85 + min(5, i // 1000), "Scanning builtins...")
                time.sleep(0)
        report(88)

        # Pass 14: selfs/attributes highlight
        report(89, "Scanning self/attributes...")
        for m in SELFS_RE.finditer(content):
            s, e = m.span()
            if not overlaps_protected(s, e):
                actions['selfs'].append((s, e))
        report(90)

        # Pass 15: variables discovered across full file
        report(91, "Collecting variables...")
        new_vars = {m.group(1) for m in VAR_ASSIGN_RE.finditer(content)}
        report(93)

        # Pass 16: include persisted buffers
        report(94, "Tagging persisted symbols...")
        if persisted_vars:
            try:
                pattern_pv = re.compile(r'\b(' + r'|'.join(re.escape(x) for x in persisted_vars) + r')\b')
                for m in pattern_pv.finditer(content):
                    s, e = m.span(1)
                    if not overlaps_protected(s, e):
                        actions['variable'].append((s, e))
            except re.error:
                pass
        if persisted_defs:
            try:
                pattern_pd = re.compile(r'\b(' + r'|'.join(re.escape(x) for x in persisted_defs) + r')\b')
                for m in pattern_pd.finditer(content):
                    s, e = m.span(1)
                    if not overlaps_protected(s, e):
                        actions['def'].append((s, e))
            except re.error:
                pass
        report(98)

        # Finalize
        report(100, "Done, please wait while highlighting is applied")
        return actions, new_vars, new_defs
    except Exception:
        report(100, "Error")
        return actions, set(), set()

# initialize persisted buffers
persisted_vars, persisted_defs = _load_symbol_buffers()

# -------------------------
# Actions: clipboard / cut / paste
# -------------------------
def copy_to_clipboard():
    try:
        copiedText = textArea.selection_get()
        root.clipboard_clear()
        root.clipboard_append(copiedText)
    except Exception:
        pass


def paste_from_clipboard():
    try:
        pastedText = root.clipboard_get()
        textArea.insert('insert', pastedText)
    except Exception:
        pass


def cut_selected_text():
    try:
        cuttedText = textArea.selection_get()
        textArea.delete(SEL_FIRST, SEL_LAST)
        root.clipboard_clear()
        root.clipboard_append(cuttedText)
    except Exception:
        pass


# -------------------------
# Formatting toggles
# -------------------------
def _tag_implies_attribute(tag: str, attr: str) -> bool:
    """Return True if `tag` implies `attr` ('bold'|'italic'|'underline')."""
    try:
        if not tag:
            return False
        # legacy mappings
        if attr == 'bold':
            if tag in ('bold', 'bolditalic', 'boldunderline', 'all'):
                return True
        if attr == 'italic':
            if tag in ('italic', 'bolditalic', 'underlineitalic', 'all'):
                return True
        if attr == 'underline':
            if tag in ('underline', 'boldunderline', 'underlineitalic', 'all'):
                return True
        # style_* tags end with a suffix that encodes combination, e.g. style_native_b_i or style_fontname_b
        if tag.startswith('style_'):
            try:
                body = tag.rsplit('_', 1)[1]
                if attr == 'bold' and 'b' in body:
                    return True
                if attr == 'italic' and 'i' in body:
                    return True
                if attr == 'underline' and 'u' in body:
                    return True
            except Exception:
                pass
        # nothing implies attribute
        return False
    except Exception:
        return False

def _range_fully_has_attribute(start_idx: str, end_idx: str, attr: str) -> bool:
    """Return True if every character in [start_idx, end_idx) has `attr` applied."""
    try:
        # normalize indices
        s = textArea.index(start_idx)
        e = textArea.index(end_idx)
        s_off = len(textArea.get('1.0', s))
        e_off = len(textArea.get('1.0', e))
        if e_off <= s_off:
            return False
        # For each char position, ensure at least one tag present that implies the attribute
        for p in range(s_off, e_off):
            idx = textArea.index(f"1.0 + {p}c")
            tags_here = textArea.tag_names(idx)
            has_attr = False
            for t in tags_here:
                if _tag_implies_attribute(t, attr):
                    has_attr = True
                    break
            if not has_attr:
                return False
        return True
    except Exception:
        return False

def toggle_tag_complex(tag):
    """Toggle bold/italic/underline across the selection, respecting font_* boundaries and composite style tags.

    Behavior:
    - If the entire selection already has the attribute, remove it (clear composite/legacy tags for that attr).
    - Otherwise apply the attribute by creating per-font composite style tags so family/size are preserved.
    """
    try:
        start, end = selection_or_all()

        if tag not in ('bold', 'italic', 'underline'):
            # fallback to simple toggle for other tags
            try:
                ranges = textArea.tag_ranges(tag)
                if ranges:
                    textArea.tag_remove(tag, start, end)
                else:
                    textArea.tag_add(tag, start, end)
            except Exception:
                pass
            return

        attr = tag  # 'bold'|'italic'|'underline'
        # if entire range currently has attr -> we'll remove it
        fully_has = _range_fully_has_attribute(start, end, attr)
        if fully_has:
            # remove any style_* and legacy tags that imply this attribute inside the selection
            try:
                for t in list(textArea.tag_names()):
                    if t.startswith('style_') or t in ('bold', 'italic', 'underline', 'all', 'bolditalic', 'boldunderline', 'underlineitalic'):
                        try:
                            textArea.tag_remove(t, start, end)
                        except Exception:
                            pass
            except Exception:
                pass
            return

        # otherwise we need to add the attribute across the selection.
        # We'll remove legacy/simple style tags first to avoid overlapping duplicates,
        # then partition by font_* boundaries and add composite style tags per partition.
        try:
            for t in list(textArea.tag_names()):
                if t.startswith('style_') or t in ('bold', 'italic', 'underline', 'all', 'bolditalic', 'boldunderline', 'underlineitalic'):
                    try:
                        textArea.tag_remove(t, start, end)
                    except Exception:
                        pass
        except Exception:
            pass

        # compute absolute offsets
        s_off = len(textArea.get('1.0', start))
        e_off = len(textArea.get('1.0', end))
        pos = s_off
        while pos < e_off:
            try:
                # find contiguous run where the active font_* tag is the same
                idx = textArea.index(f"1.0 + {pos}c")
                tags_here = textArea.tag_names(idx)
                font_here = None
                for tt in tags_here:
                    if tt.startswith('font_'):
                        font_here = tt
                        break
                run_end = pos + 1
                while run_end < e_off:
                    idx2 = textArea.index(f"1.0 + {run_end}c")
                    tags2 = textArea.tag_names(idx2)
                    f2 = None
                    for tt in tags2:
                        if tt.startswith('font_'):
                            f2 = tt
                            break
                    if f2 != font_here:
                        break
                    run_end += 1

                ns = textArea.index(f"1.0 + {pos}c")
                ne = textArea.index(f"1.0 + {run_end}c")

                # Determine resulting combination flags for this run:
                # Check existing attributes on this run to preserve other flags (we are toggling one attr)
                # Build booleans by sampling first char in run
                sample_idx = ns
                existing_b = False
                existing_i = False
                existing_u = False
                tags_sample = textArea.tag_names(sample_idx)
                for t in tags_sample:
                    if _tag_implies_attribute(t, 'bold'):
                        existing_b = True
                    if _tag_implies_attribute(t, 'italic'):
                        existing_i = True
                    if _tag_implies_attribute(t, 'underline'):
                        existing_u = True

                # Toggle the requested attr on this run (we want to set it to True)
                if attr == 'bold':
                    new_b = True
                    new_i = existing_i
                    new_u = existing_u
                elif attr == 'italic':
                    new_b = existing_b
                    new_i = True
                    new_u = existing_u
                else:  # underline
                    new_b = existing_b
                    new_i = existing_i
                    new_u = True

                # create composite style tag name and ensure config
                style_tag = _make_style_tag_name(font_here, new_b, new_i, new_u)
                _ensure_style_tag(style_tag, new_b, new_i, new_u, font_tag=font_here)
                try:
                    textArea.tag_add(style_tag, ns, ne)
                    _raise_tag_over_marquee(style_tag)
                except Exception:
                    pass

                pos = run_end
            except Exception:
                pos += 1
    except Exception:
        pass


def format_bold():
    toggle_tag_complex("bold")


def format_italic():
    toggle_tag_complex("italic")


def format_underline():
    toggle_tag_complex("underline")


def remove_all_formatting():
    """Remove all presentational tags from selection (or whole buffer) while leaving syntax tags intact."""
    try:
        start, end = selection_or_all()
        # Tags considered syntax/internal which we should not remove
        internal_tags = {
            'string', 'keyword', 'comment', 'selfs', 'def', 'number', 'variable',
            'decorator', 'class_name', 'constant', 'attribute', 'builtin', 'todo',
            'currentLine', 'trailingWhitespace', 'find_match', 'operator'
        }
        for t in list(textArea.tag_names()):
            try:
                if t in internal_tags:
                    continue
                # Keep hyperlink mappings intact (but remove visual hyperlink tag if requested)
                # We remove all presentation tags including style_*, font_*, hex_*, and explicit mark/code/etc.
                if True:
                    try:
                        textArea.tag_remove(t, start, end)
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception:
        pass


# -------------------------
# File operations (single-copy implementations)
# -------------------------
def get_size_of_textarea_lines():
    """Return count of lines as a simple progress metric."""
    return len(textArea.get('1.0', 'end-1c').splitlines()) or 1


def save_file_as():
    # asks save-as if no filename is set
    fileName = filedialog.asksaveasfilename(
        initialdir=os.path.expanduser("~"),
        title="Save as SimpleEdit Text (.set), Markdown (.md) or other",
        defaultextension='.set',
        filetypes=(
            ("SimpleEdit Text files", "*.set"),
            ("Markdown files", "*.md"),
            ("Text files", "*.txt"),
            ("Python Source files", "*.py"),
            ("All files", "*.*"),
        )
    )
    if not fileName:
        return
    root.fileName = fileName
    # fall through to normal save
    save_file()


def save_file_as2():
    fileName2 = filedialog.asksaveasfilename(
        initialdir=os.path.expanduser("~"),
        title="Save as SimpleEdit Text (.set), Markdown (.md) or other",
        defaultextension='.set',
        filetypes=(
            ("SimpleEdit Text files", "*.set"),
            ("Markdown files", "*.md"),
            ("Text files", "*.txt"),
            ("Python Source files", "*.py"),
            ("All files", "*.*"),
        )
    )
    if not fileName2:
        return
    root.fileName = fileName2
    save_file()


def save_file():
    # If current tab points to a URL, prefer Save-as-Markdown flow (respect open-as-source)
    try:
        fn = getattr(root, 'fileName', '') or ''
        # prefer frame.fileName when available (keeps per-tab behavior correct)
        try:
            sel = editorNotebook.select()
            if sel:
                frame = root.nametowidget(sel)
                fn = getattr(frame, 'fileName', '') or fn
        except Exception:
            pass
        if not fn:
            save_file_as()
            return
        if _is_likely_url(fn) or fn.lower().startswith('http') or fn.lower().startswith('file:///') or fn.lower().startswith('www.'):
            # remote page -> show Save-as-Markdown dialog (preserves open-as-source behavior)
            save_as_markdown(textArea)
            return
    except Exception:
        # fallback to original flow
        if not root.fileName:
            save_file_as()
            return
    try:
        # If the current tab is showing RAW view, prefer saving the raw HTML source directly to file
        try:
            sel = editorNotebook.select()
            frame = root.nametowidget(sel) if sel else None
            view_raw = bool(getattr(frame, '_view_raw', False)) if frame is not None else False
        except Exception:
            view_raw = False

        # If viewing raw and target is a local file, write raw content directly
        if view_raw and fn and not _is_likely_url(fn):
            try:
                raw_content = getattr(frame, '_raw_html', None) or textArea.get('1.0', 'end-1c')
                with open(fn, 'w', errors='replace', encoding='utf-8') as f:
                    f.write(raw_content)
                statusBar['text'] = f"'{fn}' saved (raw source)!"
                add_recent_file(fn)
                refresh_recent_menu()
                # update tab/frame metadata
                try:
                    if sel:
                        frame.fileName = fn
                        editorNotebook.tab(sel, text=os.path.basename(fn) or fn)
                    root.fileName = fn
                except Exception:
                    pass
                return
            except Exception as e:
                messagebox.showerror("Error", str(e))
                return

        # Otherwise default save behavior (may include formatting header)

    
        content = textArea.get('1.0', 'end-1c')
        # automatically embed formatting header for .set files,
        # or if the user explicitly enabled the option in settings.
        save_formatting = config.getboolean("Section1", "saveFormattingInFile", fallback=False) \
                          or (isinstance(root.fileName, str) and root.fileName.lower().endswith('.set'))
        header = _serialize_formatting() if save_formatting else ''
        with open(root.fileName, 'w', errors='replace') as f:
            if header:
                f.write(header)
            f.write(content)
        statusBar['text'] = f"'{root.fileName}' saved successfully!"
        add_recent_file(root.fileName)
        refresh_recent_menu()

        # persist the filename into the current tab's metadata so future tab operations use it
        try:
            sel = editorNotebook.select()
            if sel:
                frame = root.nametowidget(sel)
                frame.fileName = root.fileName
                # update visible tab title to the saved filename
                try:
                    editorNotebook.tab(sel, text=os.path.basename(root.fileName) or root.fileName)
                except Exception:
                    pass        
        except Exception:
            pass
    except Exception as e:
        messagebox.showerror("Error", str(e))

# Add this function near other file-open helpers (above or next to open_file_threaded)
def open_file_action():
    """File->Open entry point. Show custom modal when enabled, otherwise use native dialog."""
    try:
        use_modal = config.getboolean("Section1", "openDialogModal", fallback=True)
        if use_modal:
            open_file_threaded()
            return

        # native file picker path (no custom modal)
        p = filedialog.askopenfilename(
            initialdir=os.path.expanduser("~"),
            title="Select file",
            filetypes=(
                ("SimpleEdit Text files", "*.set"),
                ("Markdown files", "*.md"),
                ("HTML files", "*.html"),
                ("Text files", "*.txt"),
                ("Python Source files", "*.py"),
                ("All files", "*.*"),
            )
        )
        if not p:
            return

        # read on background thread and marshal to UI (reuse _open_path on main thread)
        def worker(path):
            try:
                with open(path, 'r', errors='replace', encoding='utf-8') as fh:
                    _ = fh.read()  # just verify readable; _open_path will re-read as needed on UI thread
            except Exception as e:
                root.after(0, lambda: messagebox.showerror("Error", str(e)))
                return
            root.after(0, lambda: _open_path(path, open_in_new_tab=True))

        Thread(target=worker, args=(p,), daemon=True).start()
    except Exception as e:
        messagebox.showerror("Error", str(e))

def open_file_threaded():
    """Open file dialog with 'Open in new tab' checkbox; load file on background thread."""
    try:
        dlg = Toplevel(root)
        dlg.title("Open File")
        dlg.transient(root)
        dlg.grab_set()
        dlg.resizable(False, False)

        container = ttk.Frame(dlg, padding=12)
        container.grid(row=0, column=0, sticky='nsew')
        container.columnconfigure(1, weight=1)

        ttk.Label(container, text="File:").grid(row=0, column=0, sticky='w', pady=(0,6))
        path_var = StringVar(value='')
        path_entry = ttk.Entry(container, textvariable=path_var, width=60)
        path_entry.grid(row=0, column=1, sticky='ew', padx=(6,0), pady=(0,6))

        def on_browse():
            p = filedialog.askopenfilename(
                initialdir=os.path.expanduser("~"),
                title="Select file",
                filetypes=(
                    ("SimpleEdit Text files", "*.set"),
                    ("Markdown files", "*.md"),
                    ("HTML files", "*.html"),
                    ("Text files", "*.txt"),
                    ("Python Source files", "*.py"),
                    ("All files", "*.*"),
                )
            )
            if p:
                path_var.set(p)

        btn_browse = ttk.Button(container, text="Browse...", command=on_browse)
        btn_browse.grid(row=0, column=2, padx=(6,0), pady=(0,6))

        new_tab_var = IntVar(value=1)
        chk_newtab = ttk.Checkbutton(container, text="Open in new tab", variable=new_tab_var)
        chk_newtab.grid(row=1, column=1, sticky='w', pady=(0,8))

        # New: remember checkbox (same purpose as the recent-files remember)
        remember_var = IntVar(value=0)
        chk_remember = ttk.Checkbutton(container, text="Remember this choice for recent files (don't prompt)", variable=remember_var)
        chk_remember.grid(row=2, column=1, sticky='w', pady=(0,6))

        status = ttk.Label(container, text="")
        status.grid(row=3, column=0, columnspan=3, sticky='w')

        def do_cancel():
            try:
                dlg.grab_release()
            except Exception:
                pass
            dlg.destroy()

        def do_open():
            p = path_var.get().strip()
            if not p:
                status.config(text="No file selected.")
                return
            # persist remember choice if checked
            if remember_var.get():
                try:
                    config.set("Section1", "openDialogDefault", "new" if new_tab_var.get() else "current")
                    config.set("Section1", "openDialogModal", "False")
                    config.set("Section1", "recentOpenDefault", "new" if new_tab_var.get() else "current")
                    config.set("Section1", "promptOnRecentOpen", "False")
                    with open(INI_PATH, 'w') as f:
                        config.write(f)
                except Exception:
                    pass
            try:
                dlg.grab_release()
            except Exception:
                pass
            dlg.destroy()

            # background worker reads and processes the file (reuse existing worker code)
            def worker(path, open_in_new_tab):
                try:
                    with open(path, 'r', errors='replace', encoding='utf-8') as fh:
                        raw = fh.read()
                except Exception as e:
                    root.after(0, lambda: messagebox.showerror("Error", str(e)))
                    return

                # reuse the same core open logic but marshal UI updates to main thread via _open_path
                root.after(0, lambda: _open_path(path, open_in_new_tab=open_in_new_tab))

            Thread(target=worker, args=(p, bool(new_tab_var.get())), daemon=True).start()

        btn_frame = ttk.Frame(container)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=(6,0), sticky='e')
        ttk.Button(btn_frame, text="Open", command=do_open).pack(side=RIGHT, padx=(6,0))
        ttk.Button(btn_frame, text="Cancel", command=do_cancel).pack(side=RIGHT)

        # center and show
        dlg.update_idletasks()
        center_window(dlg)
        path_entry.focus_set()
    except Exception as e:
        messagebox.showerror("Error", str(e))

def _on_status_syntax_toggle():
    """Persist the syntax highlighting toggle immediately and apply change.

    When disabling: remove all syntax and HTML-specific tags from every open Text widget
    (so parser-applied html_tag/html_attr/html_comment/ table/hyperlink ranges do not remain).
    """
    try:
        # persist change to config immediately
        config.set("Section1", "syntaxHighlighting", str(bool(updateSyntaxHighlighting.get())))
        with open(INI_PATH, 'w') as cfgf:
            config.write(cfgf)
    except Exception:
        pass

    try:
        if updateSyntaxHighlighting.get():
            # enable -> run a full initial highlight
            highlightPythonInit()
            statusBar['text'] = "Syntax highlighting enabled."
        else:
            # disable -> clear tags across all text widgets and update status
            SYNTAX_TAGS = (
                'string', 'keyword', 'comment', 'selfs', 'def', 'number', 'variable',
                'decorator', 'class_name', 'constant', 'attribute', 'builtin', 'todo',
                # HTML / markup specific tags
                'html_tag', 'html_attr', 'html_attr_value', 'html_comment',
                # tables and separators used by HTML parser
                'table', 'tr', 'td', 'th', 'table_sep',
                # presentational tags that were applied by parser (keep other presentational tags if desired)
                'hyperlink', 'marquee'
            )
            try:
                # iterate every open tab and the global textArea to remove tags and hyperlink maps
                widgets = []
                # current global textArea (if available)
                try:
                    if 'textArea' in globals() and isinstance(globals().get('textArea'), Text):
                        widgets.append(globals().get('textArea'))
                except Exception:
                    pass
                # all tabs' widgets
                try:
                    for tab_id in editorNotebook.tabs():
                        try:
                            frame = root.nametowidget(tab_id)
                        except Exception:
                            continue
                        for child in frame.winfo_children():
                            if isinstance(child, Text):
                                widgets.append(child)
                except Exception:
                    pass

                for tw in widgets:
                    try:
                        # remove explicitly named tags
                        for t in SYNTAX_TAGS:
                            try:
                                tw.tag_remove(t, "1.0", "end")
                            except Exception:
                                pass
                        # remove any hex_ tags? keep them so color tokens still show; if you want to remove, uncomment:
                        # for t in list(tw.tag_names()):
                        #     if t.startswith('hex_'):
                        #         try:
                        #             tw.tag_remove(t, "1.0", "end")
                        #         except Exception:
                        #             pass
                        # stop any marquee loops if present in this widget (global marquee loop checks tag ranges)
                        try:
                            tw.tag_remove('marquee', "1.0", "end")
                        except Exception:
                            pass
                    except Exception:
                        pass

                # Ensure UI-level refresh so removed tags vanish immediately
                try:
                    # refresh each tab's line numbers and the active caret highlight
                    for tab_id in editorNotebook.tabs():
                        try:
                            frame = root.nametowidget(tab_id)
                            _draw_line_numbers_for(frame)
                        except Exception:
                            pass
                    # global refresh helpers
                    try:
                        highlight_current_line()
                    except Exception:
                        pass
                    try:
                        redraw_line_numbers()
                    except Exception:
                        pass
                    try:
                        update_status_bar()
                    except Exception:
                        pass
                except Exception:
                    pass

            except Exception:
                pass

            statusBar['text'] = "Syntax highlighting disabled."
    except Exception:
        pass

def _collect_formatting_ranges():
    """Return dict mapping formatting tag -> list of (start_offset, end_offset)."""
    tags_to_check = ('bold', 'italic', 'underline', 'all',
                     'underlineitalic', 'boldunderline', 'bolditalic',
                     'small', 'mark', 'code', 'kbd', 'sub', 'sup')
    out = {}
    for tag in tags_to_check:
        ranges = textArea.tag_ranges(tag)
        arr = []
        for i in range(0, len(ranges), 2):
            s = ranges[i]
            e = ranges[i + 1]
            start = len(textArea.get('1.0', s))
            end = len(textArea.get('1.0', e))
            if end > start:
                arr.append((start, end))
        out[tag] = arr
    return out


def _wrap_segment_by_tags(seg_text: str, active_tags: set):
    return funcs.wrap_segment_by_tags(seg_text, active_tags)

def save_as_markdown(textArea):
    """Save current buffer. If the active tab is showing RAW view, save raw HTML.
    Otherwise use the existing rendered Markdown/HTML export flow."""
    try:
        # determine active frame and whether current tab is showing raw view
        opened_as_source = False
        view_raw = False
        frame = None
        try:
            sel = editorNotebook.select()
            if sel:
                frame = root.nametowidget(sel)
                opened_as_source = bool(getattr(frame, '_opened_as_source', False))
                view_raw = bool(getattr(frame, '_view_raw', False))
        except Exception:
            opened_as_source = False
            view_raw = False

        # Clarify dialog title depending on what will be saved
        if view_raw or opened_as_source:
            dlg_title = "Save file (raw HTML source)"
        else:
            dlg_title = "Save rendered view as Markdown/HTML (preserves highlighting)"

        # Ask user for target file
        fileName = filedialog.asksaveasfilename(
            initialdir=os.path.expanduser("~"),
            title=dlg_title,
            defaultextension='.md' if not (view_raw or opened_as_source) else '.html',
            filetypes=(
                ("Markdown files", "*.md"),
                ("HTML files", "*.html"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            )
        )
        if not fileName:
            return None

        # If user is viewing raw/source -> write raw HTML exactly as seen
        if view_raw or opened_as_source:
            try:
                # Prefer stored raw HTML on the frame when available
                raw_content = None
                try:
                    raw_content = getattr(frame, '_raw_html', None)
                except Exception:
                    raw_content = None
                if not raw_content:
                    raw_content = textArea.get('1.0', 'end-1c')
                with open(fileName, 'w', errors='replace', encoding='utf-8') as fh:
                    fh.write(raw_content)
                statusBar['text'] = f"'{fileName}' saved (raw source)!"
                root.fileName = fileName
                add_recent_file(fileName)
                refresh_recent_menu()
                # Update window title to reflect saved raw source
                try:
                    root.title(f"SimpleEdit — {os.path.basename(fileName)} (raw)")
                except Exception:
                    pass
                return fileName
            except Exception as e:
                messagebox.showerror("Error", str(e))
                return None

        # Otherwise save rendered content using existing export helper
        try:
            saved = funcs.save_as_markdown(textArea)
            if saved:
                statusBar['text'] = f"'{saved}' saved successfully!"
                root.fileName = saved
                add_recent_file(saved)
                refresh_recent_menu()
                try:
                    root.title(f"SimpleEdit — {os.path.basename(saved)} (rendered)")
                except Exception:
                    pass
            return saved
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return None

    except Exception:
        return None

def fetch_and_open_url(url: str, open_in_new_tab: bool = True, record_history: bool = True):
    """Fetch `url` on a background thread and open parsed HTML in a tab (reusable helper).

    record_history: when False do NOT call _record_location_opened for the opened URL.
    """
    def worker(url_in, open_tab, record_hist):
        try:
            import urllib.request as urr
            import urllib.parse as up
            parsed = up.urlsplit(url_in)
            if not parsed.scheme:
                url2 = 'http://' + url_in
            else:
                url2 = url_in
            req = urr.Request(url2, headers={"User-Agent": "SimpleEdit/1.0"})
            with urr.urlopen(req, timeout=15) as resp:
                charset = None
                try:
                    ct = resp.headers.get_content_charset()
                    if ct:
                        charset = ct
                except Exception:
                    pass
                raw_bytes = resp.read()
                enc = charset or 'utf-8'
                try:
                    raw = raw_bytes.decode(enc, errors='replace')
                except Exception:
                    raw = raw_bytes.decode('utf-8', errors='replace')

            # Respect the 'open as source' preference for fetched HTML/MD
            preset_path = None
            if config.getboolean("Section1", "openHtmlAsSource", fallback=False):
                plain = raw
                tags_meta = None
                try:
                    if config.getboolean("Section1", "autoDetectSyntax", fallback=True):
                        # provide filename hint so presets with detect.filename/detect.ext can match
                        preset_path = detect_syntax_preset_from_content(raw, filename_hint=url2)
                except Exception:
                    preset_path = None
            else:
                plain, tags_meta = funcs._parse_html_and_apply(raw)
                try:
                    if config.getboolean("Section1", "autoDetectSyntax", fallback=True) and not preset_path:
                        preset_path = detect_syntax_preset_from_content(raw, filename_hint=url2)
                except Exception:
                    preset_path = None

            def ui():
                try:
                    title = up.urlsplit(url2).netloc or url2
                    if open_tab:
                        tx, fr = create_editor_tab(title, plain, filename=url2)
                        tx.focus_set()
                        _apply_tag_configs_to_widget(tx)
                        # store raw/parsed data and view flags on the new tab like _open_path does
                        try:
                            fr._raw_html = raw
                            fr._raw_html_plain = plain
                            fr._raw_html_tags_meta = tags_meta
                            # If tags_meta contains tags -> parsed/rendered view; otherwise treat as "opened as source"
                            is_source = not bool(tags_meta and tags_meta.get('tags'))
                            fr._opened_as_source = bool(is_source)
                            fr._view_raw = bool(is_source)
                        except Exception:
                            pass
                        try:
                            root.after(0, update_view_status_indicator)
                        except Exception:
                            pass
                    else:
                        # When navigating in the current tab, record the previous URL (if any)
                        try:
                            sel = editorNotebook.select()
                            prev = ''
                            if sel:
                                frame = root.nametowidget(sel)
                                prev = getattr(frame, 'fileName', '') or getattr(root, 'fileName', '') or ''
                            else:
                                prev = getattr(root, 'fileName', '') or ''
                                try:
                                   # ensure previous location is available immediately in the in-memory stack
                                    _push_back_stack(prev)
                                except Exception:
                                    pass
                        except Exception:
                            pass

                        # replace current tab content and set per-tab filename so refresh/back work
                        textArea.delete('1.0', 'end')
                        textArea.insert('1.0', plain)
                        _apply_tag_configs_to_widget(textArea)
                        try:
                            sel = editorNotebook.select()
                            if sel:
                                frame = root.nametowidget(sel)
                                frame.fileName = url2
                                # store raw/parsed for toggle and source flag
                                try:
                                    frame._raw_html = raw
                                    frame._raw_html_plain = plain
                                    frame._raw_html_tags_meta = tags_meta
                                    frame._view_raw = not bool(tags_meta and tags_meta.get('tags'))  # show raw if no parsed tags
                                    frame._opened_as_source = not bool(tags_meta and tags_meta.get('tags'))
                                except Exception:
                                    pass
                                # mark whether this tab contains raw source (no tags) or parsed HTML
                                try:
                                    frame._opened_as_source = not bool(tags_meta and tags_meta.get('tags'))
                                except Exception:
                                    pass
                                   # update visible tab title to reflect the loaded page immediately
                                try:
                                    editorNotebook.tab(sel, text=title)
                                except Exception:
                                    pass
                            root.fileName = url2
                        except Exception:
                            root.fileName = url2

                        # schedule one-shot autodetect after in-place URL load/refresh
                        try:
                            prev = getattr(root, '_manual_detect_after_id', None)
                            if prev:
                                try:
                                    root.after_cancel(manual_detect_after_id)
                                except Exception:
                                    pass
                            manual_detect_after_id = root.after(1000, lambda: manual_detect_syntax(force=False))
                        except Exception:
                            pass

                        # record opened URL into history/back-stack (only URLs are stored)
                        try:
                            if record_hist:
                                _record_location_opened(url2, push_stack=True)
                        except Exception:
                            pass

                       # apply autodetected syntax preset (run on UI thread so config+highlighting update correctly)
                        try:
                            if preset_path:
                                applied = apply_syntax_preset(preset_path)
                                if applied:
                                    statusBar['text'] = "Applied syntax preset from autodetect."
                        except Exception:
                            pass
                    statusBar['text'] = f"Opened URL: {url2}"
                    # Do NOT add URLs to recent files (recent list is for local files only)
                    if tags_meta and tags_meta.get('tags'):
                        root.after(0, lambda: _apply_formatting_from_meta(tags_meta))
                    if updateSyntaxHighlighting.get():
                        root.after(0, highlightPythonInit)
                    # keep the toolbar field in sync with what we opened
                    try:
                        if 'url_var' in globals():
                            url_var.set(url2)
                    except Exception:
                        pass
                except Exception as e:
                    try:
                        messagebox.showerror("Error", str(e))
                    except Exception:
                        pass

            root.after(0, ui)

        except Exception as e:
            def ui_err():
                try:
                    messagebox.showerror("Fetch error", f"Failed to fetch URL: {e}")
                except Exception:
                    pass
            root.after(0, ui_err)

    Thread(target=worker, args=(url, bool(open_in_new_tab), bool(record_history)), daemon=True).start()

# -------------------------
# Highlighting
# -------------------------
# Highlighting toggle (initialized from config)
updateSyntaxHighlighting = IntVar(value=config.getboolean("Section1", "syntaxHighlighting", fallback=True))
fullScanEnabled = IntVar(value=config.getboolean("Section1", "fullScanEnabled", fallback=True))
openHtmlAsSourceVar = IntVar(value=config.getboolean("Section1", "openHtmlAsSource", fallback=False))

def _on_open_as_source_toggle():
    """Persist the 'Open HTML/MD as source' toggle and update status text."""
    try:
        config.set("Section1", "openHtmlAsSource", str(bool(openHtmlAsSourceVar.get())))
        with open(INI_PATH, 'w') as cfgf:
            config.write(cfgf)
    except Exception:
        pass
    try:
        statusBar['text'] = "Open HTML/MD as source: ON" if openHtmlAsSourceVar.get() else "Open HTML/MD as source: OFF"
    except Exception:
        pass

def match_case_like_this(start, end):
    pattern = r'def\s+([\w_]+)\s*\('
    matches = []
    for line in textArea.get(start, end).splitlines():
        m = re.search(pattern, line)
        if m:
            matches.append(r'\b' + re.escape(m.group(1)) + r'\b')
    return r'|'.join(matches) if matches else r'\b\b'


match_string = r'\b\b'


def highlight_python_helper(event=None, scan_start=None, scan_end=None):
    """Highlight a local region near the current cursor.

    By default this function will only scan the visible region to reduce work
    on large files. It will also tag names from the persisted buffers so those
    identifiers remain highlighted even if their definition is outside the visible region.
    """
    try:
        global persisted_vars, persisted_defs

        # determine current tab frame and any transient syntax
        trans = None
        try:
            sel = editorNotebook.select()
            if sel:
                frame = root.nametowidget(sel)
                trans = getattr(frame, '_transient_syntax', None)
            else:
                trans = getattr(root, '_transient_syntax', None)
        except Exception:
            trans = getattr(root, '_transient_syntax', None)

        # select regexes and lists from transient if present, otherwise fall back to globals
        STRING_RE_loc = trans['regexes'].get('STRING_RE') if (trans and 'STRING_RE' in trans.get('regexes', {})) else STRING_RE
        COMMENT_RE_loc = trans['regexes'].get('COMMENT_RE') if (trans and 'COMMENT_RE' in trans.get('regexes', {})) else COMMENT_RE
        NUMBER_RE_loc = trans['regexes'].get('NUMBER_RE') if (trans and 'NUMBER_RE' in trans.get('regexes', {})) else NUMBER_RE
        DECORATOR_RE_loc = trans['regexes'].get('DECORATOR_RE') if (trans and 'DECORATOR_RE' in trans.get('regexes', {})) else DECORATOR_RE
        CLASS_RE_loc = trans['regexes'].get('CLASS_RE') if (trans and 'CLASS_RE' in trans.get('regexes', {})) else CLASS_RE
        VAR_ASSIGN_RE_loc = trans['regexes'].get('VAR_ASSIGN_RE') if (trans and 'VAR_ASSIGN_RE' in trans.get('regexes', {})) else VAR_ASSIGN_RE
        CONSTANT_RE_loc = trans['regexes'].get('CONSTANT_RE') if (trans and 'CONSTANT_RE' in trans.get('regexes', {})) else CONSTANT_RE
        ATTRIBUTE_RE_loc = trans['regexes'].get('ATTRIBUTE_RE') if (trans and 'ATTRIBUTE_RE' in trans.get('regexes', {})) else ATTRIBUTE_RE
        DUNDER_RE_loc = trans['regexes'].get('DUNDER_RE') if (trans and 'DUNDER_RE' in trans.get('regexes', {})) else DUNDER_RE
        FSTRING_RE_loc = trans['regexes'].get('FSTRING_RE') if (trans and 'FSTRING_RE' in trans.get('regexes', {})) else FSTRING_RE

        # keywords/builtins
        KEYWORD_RE_loc = trans['keywords'][1] if (trans and trans.get('keywords')) else KEYWORD_RE
        BUILTIN_RE_loc = trans['builtins'][1] if (trans and trans.get('builtins')) else BUILTIN_RE

        # determine region to scan (visible region by default)
        if scan_start is None or scan_end is None:
            try:
                # compute visible viewport lines and add a small padding margin
                first_visible = textArea.index('@0,0')
                last_visible = textArea.index(f'@0,{textArea.winfo_height()}')
                start_line = int(first_visible.split('.')[0])
                end_line = int(last_visible.split('.')[0])
                # add small padding of a couple lines to give context
                start_line = max(1, start_line - 2)
                end_line = end_line + 2
                start = f'{start_line}.0'
                end = f'{end_line}.0 lineend'
            except Exception:
                start = "1.0"
                end = "end-1c"
        else:
            start = scan_start
            end = scan_end

        # content for region and absolute char offset of region start
        content = textArea.get(start, end)
        base_offset = 0
        if start != "1.0":
            before = textArea.get("1.0", start)
            base_offset = len(before)

        # remove tags only in the scanned region
        for t in ('string', 'keyword', 'comment', 'selfs', 'def', 'number', 'variable',
                  'decorator', 'class_name', 'constant', 'attribute', 'builtin', 'todo'):
            try:
                textArea.tag_remove(t, start, end)
            except Exception:
                pass

        protected_spans = []  # keep (s, e) offsets relative to content for strings/comments

        # strings and comments first -- protect their spans
        for m in STRING_RE.finditer(content):
            s, e = m.span()
            textArea.tag_add("string", f"1.0 + {base_offset + s}c", f"1.0 + {base_offset + e}c")
            protected_spans.append((s, e))
        for m in COMMENT_RE.finditer(content):
            s, e = m.span()
            textArea.tag_add("comment", f"1.0 + {base_offset + s}c", f"1.0 + {base_offset + e}c")
            protected_spans.append((s, e))
            mm = TODO_RE.search(content, m.start(), m.end())
            if mm:
                ts, te = mm.span()
                textArea.tag_add("todo", f"1.0 + {base_offset + ts}c", f"1.0 + {base_offset + te}c")

        def overlaps_protected(s, e):
            for ps, pe in protected_spans:
                if not (e <= ps or s >= pe):
                    return True
            return False

        # HTML-specific tagging: tag comments, element names, attributes and attribute values.
        # Run early so html_comment spans become protected for later passes.
        try:
            if '<' in content and '>' in content:
                # HTML comments
                for m in HTML_COMMENT_RE.finditer(content):
                    s, e = m.span()
                    if not overlaps_protected(s, e):
                        textArea.tag_add("html_comment", f"1.0 + {base_offset + s}c", f"1.0 + {base_offset + e}c")
                    # Always protect HTML comments from other tagging
                    protected_spans.append((s, e))
                # Tag element names (e.g. <div, </a)
                for m in HTML_TAG_RE.finditer(content):
                    try:
                        s, e = m.span(1)
                        if not overlaps_protected(s, e):
                            textArea.tag_add("html_tag", f"1.0 + {base_offset + s}c", f"1.0 + {base_offset + e}c")
                    except Exception:
                        pass
                # Tag attribute names
                for m in HTML_ATTR_RE.finditer(content):
                    try:
                        s, e = m.span(1)
                        if not overlaps_protected(s, e):
                            textArea.tag_add("html_attr", f"1.0 + {base_offset + s}c", f"1.0 + {base_offset + e}c")
                    except Exception:
                        pass
                # Tag attribute values (captured in group 1/2/3)
                for m in HTML_ATTR_VAL_RE.finditer(content):
                    try:
                        # find which group matched (1,2 or 3). m.start(n) works only if group matched
                        for gi in (1, 2, 3):
                            try:
                                if m.group(gi) is not None:
                                    s = m.start(gi)
                                    e = m.end(gi)
                                    if not overlaps_protected(s, e):
                                        textArea.tag_add("html_attr_value", f"1.0 + {base_offset + s}c", f"1.0 + {base_offset + e}c")
                                    break
                            except Exception:
                                continue
                    except Exception:
                        pass
        except Exception:
            pass

        # numbers
        for m in NUMBER_RE.finditer(content):
            s, e = m.span()
            if not overlaps_protected(s, e):
                textArea.tag_add("number", f"1.0 + {base_offset + s}c", f"1.0 + {base_offset + e}c")

        # decorators
        for m in DECORATOR_RE.finditer(content):
            s, e = m.span(1)
            if not overlaps_protected(s, e):
                textArea.tag_add("decorator", f"1.0 + {base_offset + s}c", f"1.0 + {base_offset + e}c")

        # classes
        for m in CLASS_RE.finditer(content):
            s, e = m.span(1)
            if not overlaps_protected(s, e):
                textArea.tag_add("class_name", f"1.0 + {base_offset + s}c", f"1.0 + {base_offset + e}c")

        # variable assignments (first non-whitespace word on a line)
        for m in VAR_ASSIGN_RE.finditer(content):
            s, e = m.span(1)
            if not overlaps_protected(s, e):
                textArea.tag_add("variable", f"1.0 + {base_offset + s}c", f"1.0 + {base_offset + e}c")

        # constants ALL_CAPS
        for m in CONSTANT_RE.finditer(content):
            s, e = m.span(1)
            if not overlaps_protected(s, e):
                textArea.tag_add("constant", f"1.0 + {base_offset + s}c", f"1.0 + {base_offset + e}c")

        # attribute names (a.b -> tag 'b')
        for m in ATTRIBUTE_RE.finditer(content):
            s, e = m.span(1)
            if not overlaps_protected(s, e):
                textArea.tag_add("attribute", f"1.0 + {base_offset + s}c", f"1.0 + {base_offset + e}c")

        for m in DUNDER_RE.finditer(content):
            s, e = m.span()
            textArea.tag_add("def", f"1.0 + {base_offset + s}c", f"1.0 + {base_offset + e}c")
        for m in FSTRING_RE.finditer(content):
            s, e = m.span()
            # tag entire fstring as "string" already covered; then highlight expressions in braces
            ftext = m.group(0)
            for be in re.finditer(r'\{([^}]+)\}', ftext):
                expr_s = s + be.start(1)
                expr_e = s + be.end(1)
                # if you want to treat inner expression with keywords/builtins:
                sub = content[expr_s:expr_e]
                # small heuristic: run keyword/builtin regex on sub and tag matches (or tag whole expr)
                textArea.tag_add("string", f"1.0 + {base_offset + s}c", f"1.0 + {base_offset + e}c")

        # dynamic defs (existing behaviour)
        global match_string
        match_string = match_case_like_this(start, end)
        if match_string and match_string != r'\b\b':
            for m in re.finditer(match_string, content):
                s, e = m.span()
                if not overlaps_protected(s, e):
                    textArea.tag_add("def", f"1.0 + {base_offset + s}c", f"1.0 + {base_offset + e}c")

        # keywords and builtins
        for m in KEYWORD_RE.finditer(content):
            s, e = m.span()
            if not overlaps_protected(s, e):
                textArea.tag_add("keyword", f"1.0 + {base_offset + s}c", f"1.0 + {base_offset + e}c")
        for m in BUILTIN_RE.finditer(content):
            s, e = m.span()
            if not overlaps_protected(s, e):
                textArea.tag_add("builtin", f"1.0 + {base_offset + s}c", f"1.0 + {base_offset + e}c")

        # selfs/attributes highlight (include 'after' as requested)
        for m in SELFS_RE.finditer(content):
            s, e = m.span()
            if not overlaps_protected(s, e):
                textArea.tag_add("selfs", f"1.0 + {base_offset + s}c", f"1.0 + {base_offset + e}c")

        # tag persisted buffers inside the scanned region (so removed window items still highlight)
        if persisted_vars:
            pattern = re.compile(r'\b(' + r'|'.join(re.escape(x) for x in persisted_vars) + r')\b')
            for m in pattern.finditer(content):
                s, e = m.span(1)
                if not overlaps_protected(s, e):
                    textArea.tag_add("variable", f"1.0 + {base_offset + s}c", f"1.0 + {base_offset + e}c")
        if persisted_defs:
            pattern_def = re.compile(r'\b(' + r'|'.join(re.escape(x) for x in persisted_defs) + r')\b')
            for m in pattern_def.finditer(content):
                s, e = m.span(1)
                if not overlaps_protected(s, e):
                    textArea.tag_add("def", f"1.0 + {base_offset + s}c", f"1.0 + {base_offset + e}c")

        # Markdown-style links: [text](url) -> tag only the visible text and remember href
        try:
            md_link_re = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
            if not hasattr(textArea, '_hyperlink_map'):
                textArea._hyperlink_map = {}
            for m in md_link_re.finditer(content):
                full_s, full_e = m.span()
                text_s, text_e = m.span(1)  # visible anchor text
                href = m.group(2).strip()
                if overlaps_protected(text_s, text_e):
                    continue
                abs_s = base_offset + text_s
                abs_e = base_offset + text_e
                # normalize indices via textArea.index so keys match tag_ranges values
                start_idx = textArea.index(f"1.0 + {abs_s}c")
                end_idx = textArea.index(f"1.0 + {abs_e}c")
                try:
                    textArea.tag_add("hyperlink", start_idx, end_idx)
                except Exception:
                    pass
                # only set mapping if one isn't already present (HTML/imported meta wins)
                key = (start_idx, end_idx)
                if key not in textArea._hyperlink_map:
                    try:
                        entry = {'href': href}
                        textArea._hyperlink_map[key] = entry
                    except Exception:
                        pass
        except Exception:
            pass

        # hyperlink detection (http(s) / file:/// / www.)
        try:
            if not hasattr(textArea, '_hyperlink_map'):
                textArea._hyperlink_map = {}
            for m in URL_RE.finditer(content):
                s, e = m.span()
                if not overlaps_protected(s, e):
                    abs_s = base_offset + s
                    abs_e = base_offset + e
                    start_idx = textArea.index(f"1.0 + {abs_s}c")
                    end_idx = textArea.index(f"1.0 + {abs_e}c")
                    try:
                        textArea.tag_add("hyperlink", start_idx, end_idx)
                    except Exception:
                        pass
                    # store mapping only when not already present so parser-applied links remain authoritative
                    key = (start_idx, end_idx)
                    if key in textArea._hyperlink_map:
                        continue
                    url_text = content[s:e].strip()
                    if url_text.lower().startswith("www."):
                        url_text = "http://" + url_text
                    try:
                        entry = {'href': url_text}
                        textArea._hyperlink_map[key] = entry
                    except Exception:
                        pass
        except Exception:
            pass

        # after tagging work inside highlight_python_helper:
        try:
            if textArea.tag_ranges('marquee') and _is_marquee_visible():
                _start_marquee_loop()
            else:
                _stop_marquee_loop()
        except Exception:
            pass
    except Exception:
        pass

def color_hex_codes(tw: Text | None = None, scan_start: str = "1.0", scan_end: str = "end-1c"):
    """Find literal hex colors in the given Text widget region and color them.

    Creates tags named 'hex_rrggbb' and sets their foreground to that color.
    This runs independently of syntax-highlight toggle.
    """
    try:
        if tw is None:
            tw = globals().get('textArea')
        if not tw or not isinstance(tw, Text):
            return

        # If caller did not request a specific region (defaults), limit to the visible viewport to avoid scanning huge files.
        if tw is None:
            tw = globals().get('textArea')
        # compute viewport when defaults are used (use line numbers so constructed indices are valid)
        try:
            if (scan_start == "1.0" and scan_end == "end-1c") and isinstance(tw, Text):
                first_vis = tw.index('@0,0')
                last_vis = tw.index(f'@0,{tw.winfo_height()}')
                first_line = int(first_vis.split('.')[0])
                last_line = int(last_vis.split('.')[0])
                scan_start = f"{first_line}.0"
                scan_end = f"{last_line}.0 lineend"
        except Exception:
            pass
        try:
            content = tw.get(scan_start, scan_end)
        except Exception:
            return

        # Remove previous hex_ tag spans in the requested region (leave tag configs intact)
        try:
            for t in list(tw.tag_names()):
                if t.startswith('hex_'):
                    try:
                        tw.tag_remove(t, scan_start, scan_end)
                    except Exception:
                        pass
        except Exception:
            pass

        # compute base offset for region start to convert match offsets to indices
        base_offset = 0
        if scan_start != "1.0":
            try:
                before = tw.get("1.0", scan_start)
                base_offset = len(before)
            except Exception:
                base_offset = 0

        for m in HEX_COLOR_RE.finditer(content):
            s, e = m.span()
            hexpart = m.group(1)
            # expand shorthand (#rgb -> #rrggbb)
            if len(hexpart) == 3:
                hex6 = ''.join(ch*2 for ch in hexpart).lower()
            else:
                hex6 = hexpart.lower()
            start_idx = f"1.0 + {base_offset + s}c"
            end_idx = f"1.0 + {base_offset + e}c"
            tag = f"hex_{hex6}"
            try:
                tw.tag_add(tag, start_idx, end_idx)
                # only set config if not already configured (avoid overwriting existing visuals)
                cur_fg = ''
                try:
                    cur_fg = tw.tag_cget(tag, 'foreground') or ''
                except Exception:
                    cur_fg = ''
                if not cur_fg:
                    try:
                        _safe_tag_config(tw, tag, foreground=f"#{hex6}")
                    except Exception:
                        pass
                # ensure color tags visually win over marquee
                try:
                    tw.tag_raise(tag, 'marquee')
                except Exception:
                    try:
                        tw.tag_raise(tag)
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception:
        pass


# -------------------------
# Progress popup helpers (centered, auto-close)
# -------------------------
def center_window(win):
    win.update_idletasks()
    w = win.winfo_width()
    h = win.winfo_height()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = max(0, (sw // 2) - (w // 2))
    y = max(0, (sh // 2) - (h // 2))
    win.geometry(f"{w}x{h}+{x}+{y}")


def show_progress_popup(title, determinate=True):
    """
    Create a centered progress dialog and return (dlg, progressbar, status_label).

    By default the progressbar is determinate (determinate=True). Callers that
    prefer an indeterminate spinner can pass determinate=False.

    The returned Progressbar widget will have a 0-100 range when determinate.
    """
    dlg = Toplevel(root)
    dlg.title(title)
    dlg.transient(root)
    dlg.grab_set()
    Label(dlg, text=title).pack(padx=10, pady=(10, 0))

    if determinate:
        pb = ttk.Progressbar(dlg, mode='determinate', length=360, maximum=100, value=0)
    else:
        pb = ttk.Progressbar(dlg, mode='indeterminate', length=360)

    pb.pack(padx=10, pady=10)
    status = Label(dlg, text="")
    status.pack(padx=10, pady=(0, 10))
    dlg.update_idletasks()
    center_window(dlg)

    # start indeterminate only when requested
    if not determinate:
        try:
            pb.start()
        except Exception:
            pass

    return dlg, pb, status


def close_progress_popup(dlg, pb=None):
    try:
        if pb:
            pb.stop()
    except Exception:
        pass
    try:
        dlg.grab_release()
    except Exception:
        pass
    try:
        dlg.destroy()
    except Exception:
        pass


def highlightPythonInit():
    """Trigger initial syntax scan on load. Full or quick depending on fullScanEnabled."""
    if not updateSyntaxHighlighting.get():
        for t in ('string', 'keyword', 'comment', 'selfs', 'def', 'number', 'variable',
                  'decorator', 'class_name', 'constant', 'attribute', 'builtin', 'todo'):
            textArea.tag_remove(t, "1.0", "end")
        statusBar['text'] = "Syntax highlighting disabled."
        return

    # Quick mode: skip background worker + symbol discovery
    if not fullScanEnabled.get():
        statusBar['text'] = "Quick syntax highlight..."
        try:
            highlight_python_helper(None)
        except Exception:
            pass
        statusBar['text'] = "Ready"
        return

    statusBar['text'] = "Processing initial syntax..."
    root.update_idletasks()

    try:
        content_snapshot = textArea.get("1.0", "end-1c")
    except Exception:
        content_snapshot = ""

    dlg, pb, status = show_progress_popup("Initial syntax highlighting")
    status['text'] = "Scanning..."

    def progress_cb(pct, msg=""):
        def ui():
            try:
                if pb['mode'] != 'determinate':
                    pb.config(mode='determinate', maximum=100)
                pb['value'] = max(0, min(100, int(pct)))
                status['text'] = msg or f"{pb['value']}%"
                dlg.update_idletasks()
            except Exception:
                pass
        root.after(0, ui)

    def worker():
        actions, new_vars, new_defs = _bg_full_scan_and_collect(content_snapshot, progress_callback=progress_cb)
        def apply_and_finish():
            try:
                _apply_full_tags(actions, new_vars, new_defs)
                full = textArea.get("1.0", "end-1c")
                new_vars2 = {m.group(1) for m in VAR_ASSIGN_RE.finditer(full)}
                try:
                    DEF_RE = re.compile(r'(?m)^[ \t]*def\s+([A-Za-z_]\w*)\s*\(')
                except Exception:
                    DEF_RE = None
                new_defs2 = set()
                if DEF_RE:
                    new_defs2 = {m.group(1) for m in DEF_RE.finditer(full)}
                if new_vars2:
                    persisted_vars.update(new_vars2)
                if new_defs2:
                    persisted_defs.update(new_defs2)
                _save_symbol_buffers(persisted_vars, persisted_defs)
                highlight_python_helper(None, scan_start="1.0", scan_end="end-1c")
                statusBar['text'] = "Ready"
            finally:
                close_progress_popup(dlg, pb)
        try:
            root.after(0, apply_and_finish)
        except Exception:
            close_progress_popup(dlg, pb)

    Thread(target=worker, daemon=True).start()



def apply_syntax_preset_transient(path: str, text_widget: Text | None = None) -> bool:
    """Apply syntax preset from `path` only for the given Text widget (transient, non-persistent).

    - Does NOT write to the global `config`.
    - Configures tag colors on the provided widget and compiles per-widget regexes used
      by `highlight_python_helper` when that tab is active.
    - Stores compiled regexes and tag-colors on the tab frame as `_transient_syntax`.
    """
    try:
        if not path or not os.path.isfile(path):
            return False
        cp = configparser.ConfigParser()
        cp.read(path)
        if not cp.has_section('Syntax'):
            return False

        # Build tag color map (per-tag fg/bg) and compiled regexes/keyword lists
        tag_colors = {}
        for tag, defaults in _DEFAULT_TAG_COLORS.items():
            fg = cp.get('Syntax', f'tag.{tag}.fg', fallback='').strip()
            bg = cp.get('Syntax', f'tag.{tag}.bg', fallback='').strip()
            if fg or bg:
                tag_colors[tag] = {'fg': fg or defaults.get('fg', ''), 'bg': bg or defaults.get('bg', '')}

        # keywords/builtins
        kw_csv = cp.get('Syntax', 'keywords.csv', fallback=','.join(KEYWORDS))
        bk_csv = cp.get('Syntax', 'builtins.csv', fallback=','.join(BUILTINS))
        try:
            kw_list = [x.strip() for x in kw_csv.split(',') if x.strip()]
            kw_re = re.compile(r'\b(' + r'|'.join(map(re.escape, kw_list)) + r')\b') if kw_list else re.compile(r'\b\b')
        except Exception:
            kw_list, kw_re = [], KEYWORD_RE
        try:
            bk_list = [x.strip() for x in bk_csv.split(',') if x.strip()]
            bk_re = re.compile(r'\b(' + r'|'.join(map(re.escape, bk_list)) + r')\b') if bk_list else re.compile(r'\b\b')
        except Exception:
            bk_list, bk_re = [], BUILTIN_RE

        # Generic regex keys
        compiled = {}
        for key, default_pattern in _DEFAULT_REGEXES.items():
            cfg_key = f'regex.{key}'
            pat = cp.get('Syntax', cfg_key, fallback=default_pattern)
            if not pat:
                continue
            try:
                if key in ('STRING_RE', 'FSTRING_RE'):
                    compiled[key] = re.compile(pat, re.DOTALL)
                else:
                    compiled[key] = re.compile(pat)
            except Exception:
                # fallback to global for this key
                pass

        # Build transient syntax object
        trans = {
            'tag_colors': tag_colors,
            'regexes': compiled,
            'keywords': (kw_list, kw_re),
            'builtins': (bk_list, bk_re)
        }

        # Find target widget and its tab frame
        if text_widget is None:
            try:
                sel = editorNotebook.select()
                if sel:
                    frm = root.nametowidget(sel)
                    # find the Text widget inside
                    tw = None
                    for child in frm.winfo_children():
                        if isinstance(child, Text):
                            tw = child
                            break
                    text_widget = tw or globals().get('textArea')
                else:
                    text_widget = globals().get('textArea')
            except Exception:
                text_widget = globals().get('textArea')

        if not text_widget or not isinstance(text_widget, Text):
            return False

        # Apply tag color config to this widget only (do not touch global config)
        for tag, cfg in trans['tag_colors'].items():
            try:
                kwargs = {}
                if cfg.get('fg'):
                    try:
                        text_widget.tag_config(tag, foreground=cfg.get('fg'))
                    except Exception:
                        pass
                if cfg.get('bg'):
                    try:
                        text_widget.tag_config(tag, background=cfg.get('bg'))
                    except Exception:
                        pass
            except Exception:
                pass

        # Store transient syntax on the tab frame so highlighting can pick it up
        try:
            # find the parent frame (tab)
            parent_frame = getattr(text_widget, 'master', None)
            if parent_frame is None:
                sel = editorNotebook.select()
                parent_frame = root.nametowidget(sel) if sel else None
            if parent_frame is not None:
                parent_frame._transient_syntax = trans
            else:
                # global fallback (least preferred)
                root._transient_syntax = trans
        except Exception:
            root._transient_syntax = trans

        return True
    except Exception:
        return False

def manual_detect_syntax(force: bool = False):
    """Manually detect a syntax preset for the current tab and apply it.

    - Uses a small prefix (2KB) for detection to keep work cheap.
    - Respects brainless mode and the autoDetectSyntax setting unless `force` is True.
    - Applies preset transiently to the active tab only (no persistence).
    """
    try:
        # session override
        if brainless_mode_var.get():
            return
        # respect user preference unless forced
        if not force and not config.getboolean("Section1", "autoDetectSyntax", fallback=True):
            return

        # get current buffer prefix (safe and cheap)
        try:
            # prefer per-tab widget if available
            snippet = textArea.get("1.0", "1.0 + 2048c")
        except Exception:
            snippet = ""
        if not snippet:
            return

        # cheap detection
        preset = None
        try:
            # pass current tab filename when available to improve detection (templates / ext-based rules)
            hint = ''
            try:
                sel = editorNotebook.select()
                if sel:
                    frm = root.nametowidget(sel)
                    hint = getattr(frm, 'fileName', '') or getattr(root, 'fileName', '') or ''
            except Exception:
                hint = getattr(root, 'fileName', '') or ''
            preset = detect_syntax_preset_from_content(snippet, filename_hint=hint)
        except Exception:
            preset = None

        if not preset:
            # nothing detected; update status briefly and exit
            try:
                statusBar['text'] = "No syntax preset detected."
                root.after(1200, lambda: statusBar.config(text="Ready"))
            except Exception:
                pass
            return

        # Apply preset transiently to the current tab widget (do NOT persist)
        applied = False
        try:
            # determine active text widget to configure
            tw = None
            sel = editorNotebook.select()
            if sel:
                frame = root.nametowidget(sel)
                for child in frame.winfo_children():
                    if isinstance(child, Text):
                        tw = child
                        break
            if tw is None:
                tw = globals().get('textArea')
            applied = apply_syntax_preset_transient(preset, text_widget=tw)
        except Exception:
            applied = False

        # If applied, run highlight (quick vs full based on Full Scan)
        try:
            if applied:
                statusBar['text'] = "Applied syntax preset (transient) from autodetect."
            if updateSyntaxHighlighting.get():
                if fullScanEnabled.get():
                    # full initial highlight (may show progress)
                    highlightPythonInit()
                else:
                    # quick bounded highlight to avoid heavy work on large files
                    # scan only visible viewport (let helper compute it)
                    highlight_python_helper(None)
            # clear transient status after a moment
            root.after(1200, lambda: statusBar.config(text="Ready"))
        except Exception:
            pass
    except Exception:
        pass

# REPLACE existing refresh_full_syntax() with updated version
def refresh_full_syntax():
    """Manual refresh for syntax highlighting respecting fullScanEnabled."""
    if not updateSyntaxHighlighting.get():
        for t in ('string', 'keyword', 'comment', 'selfs', 'def', 'number', 'variable',
                  'decorator', 'class_name', 'constant', 'attribute', 'builtin', 'todo'):
            textArea.tag_remove(t, "1.0", "end")
        statusBar['text'] = "Syntax highlighting disabled."
        return

    # Quick mode path
    if not fullScanEnabled.get():
        statusBar['text'] = "Quick refresh..."
        try:
            highlight_python_helper(None)
        except Exception:
            pass
        statusBar['text'] = "Ready"
        return

    statusBar['text'] = "Refreshing syntax..."
    root.update_idletasks()

    try:
        content_snapshot = textArea.get("1.0", "end-1c")
    except Exception:
        content_snapshot = ""

    dlg, pb, status = show_progress_popup("Refreshing syntax")
    status['text'] = "Scanning..."

    def progress_cb(pct, msg=""):
        def ui():
            try:
                if pb['mode'] != 'determinate':
                    pb.config(mode='determinate', maximum=100)
                pb['value'] = max(0, min(100, int(pct)))
                status['text'] = msg or f"{pb['value']}%"
                dlg.update_idletasks()
            except Exception:
                pass
        root.after(0, ui)

    def worker():
        actions, new_vars, new_defs = _bg_full_scan_and_collect(content_snapshot, progress_callback=progress_cb)
        def apply_and_close():
            try:
                _apply_full_tags(actions, new_vars, new_defs)
                full = textArea.get("1.0", "end-1c")
                new_vars2 = {m.group(1) for m in VAR_ASSIGN_RE.finditer(full)}
                try:
                    DEF_RE = re.compile(r'(?m)^[ \t]*def\s+([A-Za-z_]\w*)\s*\(')
                except Exception:
                    DEF_RE = None
                new_defs2 = set()
                if DEF_RE:
                    new_defs2 = {m.group(1) for m in DEF_RE.finditer(full)}
                if new_vars2:
                    persisted_vars.update(new_vars2)
                if new_defs2:
                    persisted_defs.update(new_defs2)
                _save_symbol_buffers(persisted_vars, persisted_defs)
                highlight_python_helper(None, scan_start="1.0", scan_end="end-1c")
                statusBar['text'] = "Ready"
            finally:
                close_progress_popup(dlg, pb)
        try:
            root.after(0, apply_and_close)
        except Exception:
            close_progress_popup(dlg, pb)

    Thread(target=worker, daemon=True).start()


def highlightPythonInitT():
    """Compatibility wrapper used around the codebase; simply calls the non-blocking init."""
    highlightPythonInit()


def refresh_full_syntax():
    """Manual refresh for full-file syntax highlighting with progress popup."""
    if not updateSyntaxHighlighting.get():
        for t in ('string', 'keyword', 'comment', 'selfs', 'def', 'number', 'variable',
                  'decorator', 'class_name', 'constant', 'attribute', 'builtin', 'todo'):
            textArea.tag_remove(t, "1.0", "end")
        statusBar['text'] = "Syntax highlighting disabled."
        return

    statusBar['text'] = "Refreshing syntax..."
    root.update_idletasks()

    try:
        content_snapshot = textArea.get("1.0", "end-1c")
    except Exception:
        content_snapshot = ""

    dlg, pb, status = show_progress_popup("Refreshing syntax")
    status['text'] = "Scanning..."

    def progress_cb(pct, msg=""):
        def ui():
            try:
                if pb['mode'] != 'determinate':
                    pb.config(mode='determinate', maximum=100)
                pb['value'] = max(0, min(100, int(pct)))
                status['text'] = msg or f"{pb['value']}%"
                dlg.update_idletasks()
            except Exception:
                pass
        root.after(0, ui)

    def worker():
        actions, new_vars, new_defs = _bg_full_scan_and_collect(content_snapshot, progress_callback=progress_cb)
        def apply_and_close():
            try:
                _apply_full_tags(actions, new_vars, new_defs)
                # persist any discoveries from a full scan
                full = textArea.get("1.0", "end-1c")
                new_vars2 = {m.group(1) for m in VAR_ASSIGN_RE.finditer(full)}
                try:
                    DEF_RE = re.compile(r'(?m)^[ \t]*def\s+([A-Za-z_]\w*)\s*\(')
                except Exception:
                    DEF_RE = None
                new_defs2 = set()
                if DEF_RE:
                    new_defs2 = {m.group(1) for m in DEF_RE.finditer(full)}
                if new_vars2:
                    persisted_vars.update(new_vars2)
                if new_defs2:
                    persisted_defs.update(new_defs2)
                _save_symbol_buffers(persisted_vars, persisted_defs)
                highlight_python_helper(None, scan_start="1.0", scan_end="end-1c")
                statusBar['text'] = "Ready"
            finally:
                close_progress_popup(dlg, pb)

        try:
            root.after(0, apply_and_close)
        except Exception:
            close_progress_popup(dlg, pb)

    Thread(target=worker, daemon=True).start()


# -------------------------
# Utility ribbons: trailing whitespace, line numbers, caret
# -------------------------
def show_trailing_whitespace():
    try:
        first_visible = textArea.index('@0,0')
        last_visible = textArea.index(f'@0,{textArea.winfo_height()}')
        start_line = int(first_visible.split('.')[0])
        end_line = int(last_visible.split('.')[0])
        for ln in range(start_line, end_line + 1):
            textArea.tag_remove('trailingWhitespace', f'{ln}.0', f'{ln}.0 lineend')
        for ln in range(start_line, end_line + 1):
            line_text = textArea.get(f'{ln}.0', f'{ln}.0 lineend')
            m = re.search(r'[ \t]+$', line_text)
            if m:
                s = f'{ln}.0 + {m.start()}c'
                e = f'{ln}.0 + {m.end()}c'
                textArea.tag_add('trailingWhitespace', s, e)
    except Exception:
        pass


def _draw_line_numbers_for(frame):
    """Redraw line numbers for the given tab frame using the current settings."""
    try:
        ln = getattr(frame, 'lineNumbersCanvas', None)
        if not ln:
            return
        # find the Text widget inside the frame
        tw = None
        for child in frame.winfo_children():
            if isinstance(child, Text):
                tw = child
                break
        if tw is None:
            return

        ln.delete('all')
        i = tw.index('@0,0')
        while True:
            dline = tw.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            line = i.split('.')[0]
            try:
                fill = lineNumberFg
            except Exception:
                fill = '#555555'
            ln.create_text(2, y, anchor='nw', text=line, fill=fill)
            i = tw.index(f'{i}+1line')
    except Exception:
        pass


def redraw_line_numbers(event=None):
    global lineNumbersCanvas, lineNumberFg
    if not lineNumbersCanvas:
        return
    lineNumbersCanvas.delete('all')
    i = textArea.index('@0,0')
    while True:
        dline = textArea.dlineinfo(i)
        if dline is None:
            break
        y = dline[1]
        line = i.split('.')[0]
        try:
            fill = lineNumberFg
        except Exception:
            fill = '#555555'
        lineNumbersCanvas.create_text(2, y, anchor='nw', text=line, fill=fill)
        i = textArea.index(f'{i}+1line')


def go_to_line():
    line = simpledialog.askinteger("Go To Line", "Line number:", parent=root, minvalue=1)
    if line:
        max_line = int(textArea.index('end-1c').split('.')[0])
        if line > max_line:
            line = max_line
        textArea.mark_set('insert', f'{line}.0')
        textArea.see(f'{line}.0')
        highlight_current_line()
        update_status_bar()

def _open_maybe_url(path: str, open_in_new_tab: bool = True, record_history: bool = True):
    """Open `path` as a URL (http/https/file) or as a local file intelligently.

    If `path` is a relative URL and there is a current page (toolbar URL or current tab's fileName),
    attempt to resolve it with urllib.parse.urljoin before opening.

    record_history: when False do NOT call _record_location_opened for the target URL (used by Back).
    """
    try:
        import urllib.parse as up
        parsed = up.urlsplit(path)
        scheme = parsed.scheme.lower() if parsed.scheme else ''

        # If path looks like a relative URL (no scheme, not starting with www. or file:///),
        # attempt to resolve against a sensible base (toolbar URL or current tab fileName if it is a URL).
        try:
            if not scheme and not path.lower().startswith('www.') and not path.lower().startswith('file:///'):
                # find base URL from toolbar field or current tab
                base = ''
                try:
                    if 'url_var' in globals():
                        base = url_var.get().strip() or ''
                except Exception:
                    base = ''
                if not base:
                    try:
                        sel = editorNotebook.select()
                        if sel:
                            frame = root.nametowidget(sel)
                            base = getattr(frame, 'fileName', '') or ''
                    except Exception:
                        base = ''
                # Only attempt to join when base appears to be a URL
                if base and _is_likely_url(base):
                    try:
                        resolved = up.urljoin(base, path)
                        fetch_and_open_url(resolved, open_in_new_tab=open_in_new_tab, record_history=record_history)
                        return
                    except Exception:
                        # fall through to normal handling on failure
                        pass
        except Exception:
            pass

        # common www. shorthand
        if not scheme and path.lower().startswith('www.'):
            fetch_and_open_url('http://' + path, open_in_new_tab=open_in_new_tab, record_history=record_history)
            return
        if scheme in ('http', 'https'):
            fetch_and_open_url(path, open_in_new_tab=open_in_new_tab, record_history=record_history)
            return
        if scheme == 'file':
            p = parsed.path
            if re.match(r'^/[A-Za-z]:', p):
                p = p.lstrip('/')
            p = p.replace('/', os.sep)
            _open_path(p, open_in_new_tab=open_in_new_tab)
            return
    except Exception:
        pass
    # fallback: if file exists treat as file, otherwise try http
    try:
        if os.path.exists(path):
            _open_path(path, open_in_new_tab=open_in_new_tab)
            return
    except Exception:
        pass
    # last resort: try http
    fetch_and_open_url(path, open_in_new_tab=open_in_new_tab, record_history=record_history)

def open_find_replace():
    fr = Toplevel(root)
    fr.title("Find / Replace")
    Label(fr, text="Find").grid(row=0, column=0)
    findE = Entry(fr, width=30)
    findE.grid(row=0, column=1)
    Label(fr, text="Replace").grid(row=1, column=0)
    replE = Entry(fr, width=30)
    replE.grid(row=1, column=1)
    statusL = Label(fr, text="")
    statusL.grid(row=3, columnspan=2)

    def do_find():
        textArea.tag_remove('find_match', '1.0', 'end')
        pat = findE.get()
        if not pat:
            return
        content = textArea.get('1.0', 'end-1c')
        count = 0
        for m in re.finditer(re.escape(pat), content):
            start = f"1.0 + {m.start()}c"
            end = f"1.0 + {m.end()}c"
            textArea.tag_add('find_match', start, end)
            count += 1
        statusL.config(text=f"Matches: {count}")

    def do_replace():
        pat = findE.get()
        repl = replE.get()
        if not pat:
            return
        content = textArea.get('1.0', 'end-1c')
        new_content = content.replace(pat, repl)
        textArea.delete('1.0', 'end')
        textArea.insert('1.0', new_content)
        do_find()

    Button(fr, text='Find', command=do_find).grid(row=2, column=0)
    Button(fr, text='Replace All', command=do_replace).grid(row=2, column=1)


def update_status_bar(event=None):
    try:
        line, col = textArea.index('insert').split('.')
        statusBar['text'] = f"Ln {line} Col {int(col) + 1}"
    except Exception:
        pass

    # update params display if model is loaded (kept separate so line/col remains primary)
    try:
        if _model_loaded:
            paramsLabel.config(text=_get_model_param_text())
    except Exception:
        pass


def highlight_current_line(event=None):
    try:
        textArea.tag_remove('currentLine', '1.0', 'end')
        line = textArea.index('insert').split('.')[0]
        textArea.tag_add('currentLine', f'{line}.0', f'{line}.0 lineend+1c')
        # Ensure the currentLine highlight is rendered beneath the selection so selections remain visually on top.
        try:
            # Lower currentLine below 'sel' and raise 'sel' to guarantee selection visibility.
            textArea.tag_lower('currentLine', 'sel')
            textArea.tag_raise('sel')
        except Exception:
            # If 'sel' doesn't exist yet or platform doesn't support, ignore silently.
            pass
    except Exception:
        pass


# CHANGED: smart newline that preserves indentation context
def smart_newline(event):
    try:
        insert_index = textArea.index('insert')
        line_no = int(insert_index.split('.')[0])
        line_start = f"{line_no}.0"
        before = textArea.get(line_start, insert_index)
        leading_ws_match = re.match(r'([ \t]*)', before)
        current_indent = leading_ws_match.group(1) if leading_ws_match else ''
        indent_unit = '\t' if '\t' in current_indent else ' ' * 4
        stripped_left = before.rstrip()
        dedent_keywords = ('return', 'pass', 'break', 'continue', 'raise', 'yield')
        new_indent = current_indent
        if stripped_left.endswith(':'):
            new_indent = current_indent + indent_unit
        else:
            left_no_comment = re.split(r'#', stripped_left, 1)[0].strip()
            left_tokens = left_no_comment.split()
            if left_tokens and left_tokens[0] in dedent_keywords:
                if current_indent.endswith(indent_unit):
                    new_indent = current_indent[:-len(indent_unit)]
                else:
                    new_indent = current_indent[:-len(indent_unit)] if len(current_indent) >= len(indent_unit) else ''
            elif current_indent == '' and stripped_left.strip() != '':
                prev = line_no - 1
                prev_indent = ''
                while prev >= 1:
                    prev_line = textArea.get(f'{prev}.0', f'{prev}.end')
                    if prev_line.strip() != '':
                        m = re.match(r'([ \t]*)', prev_line)
                        prev_indent = m.group(1) if m else ''
                        break
                    prev -= 1
                new_indent = prev_indent

        textArea.insert('insert', '\n' + new_indent)
    except Exception:
        textArea.insert('insert', '\n')
    return 'break'


# -------------------------
# AI autocomplete (optional)
# -------------------------
def python_ai_autocomplete():
    global buttonAI
    if model is None:
        statusBar['text'] = "AI model not available."
        return

    try:
        try:
            ranges = textArea.tag_ranges("sel")
            if ranges:
                start, end = ranges[0], ranges[1]
            else:
                start = textArea.index(f'insert-{aiMaxContext}c')
                end = textArea.index('insert')
        except Exception:
            start = textArea.index(f'insert-{aiMaxContext}c')
            end = textArea.index('insert')

        content = textArea.get(start, end)
        maxTokens = int(len(content) / 8 + 128)
        skipstrip = False
        if content == '':
            skipstrip = True
            content = '<|endoftext|>'

        start_ids = encode(content)
        # prepare tensor on CPU
        idx = torch.tensor(start_ids, dtype=torch.long, device='cpu')[None, :]

        # update button to show current context length (UI thread)
        try:
            root.after(0, lambda n=int(idx.size(1)): buttonAI.config(text=f"AI Autocomplete - ctx: {n}"))
        except Exception:
            pass

        # ensure UI is prepared: delete selection and set insert at start on main thread
        prep_done = threading.Event()

        def ui_prep():
            try:
                textArea.mark_set('insert', end)
                textArea.tag_remove("sel", '1.0', 'end')
            finally:
                prep_done.set()

        root.after(0, ui_prep)
        prep_done.wait()

        generated_ids = []

        # generation loop: sample one token at a time and stream it to the UI
        with torch.inference_mode():
            for _ in range(maxTokens):
                # crop context if needed
                idx_cond = idx if idx.size(1) <= model.config.block_size else idx[:, -model.config.block_size:]
                logits, _ = model(idx_cond)
                logits = logits[:, -1, :] / temperature
                if top_k is not None:
                    v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                    logits[logits < v[:, [-1]]] = -float('Inf')
                probs = torch.nn.functional.softmax(logits, dim=-1)
                next_id = torch.multinomial(probs, num_samples=1)
                idx = torch.cat((idx, next_id), dim=1)

                # update button with new context length (UI thread)
                try:
                    root.after(0, lambda n=int(idx.size(1)): buttonAI.config(text=f"AI Autocomplete - ctx: {n}"))
                except Exception:
                    pass

                token_id = int(next_id[0, 0].item())
                generated_ids.append(token_id)

                # decode only the newly sampled token to a string fragment
                try:
                    piece = decode([token_id])
                except Exception:
                    piece = ''

                # map end-of-text token to newline or strip according to previous behaviour
                if '<|endoftext|>' in piece:
                    if not skipstrip:
                        piece = piece.replace('<|endoftext|>', '\n')
                    else:
                        piece = piece.replace('<|endoftext|>', '')

                # schedule UI insertion of this token fragment
                def ui_insert(p=piece):
                    try:
                        textArea.insert('insert', p)
                        textArea.see(INSERT)
                        highlight_python_helper(p)
                        update_status_bar()
                    except Exception:
                        pass

                root.after(0, ui_insert)

        # final UI update + status
        root.after(0, lambda: statusBar.config(text="AI: insertion complete."))
    except Exception as e:
        try:
            statusBar['text'] = f"AI error: {e}"
        except Exception:
            pass

fg_color_var = StringVar(value=config.get("Section1", "fontColor", fallback=fontColor))
bg_color_var = StringVar(value=config.get("Section1", "backgroundColor", fallback=backgroundColor))

def _range_has_tag_entirely(tag: str, start: str, end: str) -> bool:
    """Return True if `tag` exists at least once in the region (used for simple toggle logic)."""
    try:
        return bool(textArea.tag_nextrange(tag, start, end))
    except Exception:
        return False

def _contrast_text_color(hexcolor: str) -> str:
    return funcs._contrast_text_color(hexcolor)

def _raise_tag_to_top_all(tag_name: str):
    """Raise tag to top in every Text widget so its fg/bg take precedence."""
    try:
        # current widget first
        try:
            textArea.tag_raise(tag_name)
        except Exception:
            pass
        # other tabs
        for tab_id in editorNotebook.tabs():
            try:
                frame = root.nametowidget(tab_id)
                for child in frame.winfo_children():
                    if isinstance(child, Text):
                        try:
                            child.tag_raise(tag_name)
                        except Exception:
                            pass
            except Exception:
                pass
    except Exception:
        pass

def apply_color_to_selection(foreground: str | None = None, background: str | None = None):
    """Apply or toggle a foreground/background color tag on the current selection (or whole buffer)."""
    try:
        start, end = selection_or_all()

        if foreground:
            hex_fg = foreground.lstrip('#').lower()
            fg_tag = f"color_{hex_fg}"
            # configure tag globally (all widgets) with explicit foreground
            try:
                apply_tag_config_to_all(fg_tag, {'foreground': f"#{hex_fg}"})
            except Exception:
                pass
            # toggle: if the selection already has this exact color tag, remove it; otherwise add it.
            try:
                if _range_has_tag_entirely(fg_tag, start, end):
                    textArea.tag_remove(fg_tag, start, end)
                else:
                    textArea.tag_add(fg_tag, start, end)
                    # ensure this color tag visually wins
                    _raise_tag_to_top_all(fg_tag)
            except Exception:
                pass

        if background:
            hex_bg = background.lstrip('#').lower()
            bg_tag = f"bg_{hex_bg}"
            # configure tag globally with explicit background
            try:
                apply_tag_config_to_all(bg_tag, {'background': f"#{hex_bg}"})
            except Exception:
                pass
            try:
                if _range_has_tag_entirely(bg_tag, start, end):
                    textArea.tag_remove(bg_tag, start, end)
                else:
                    textArea.tag_add(bg_tag, start, end)
                    # raise background tag to top so it is visible above other tags (including marquee)
                    _raise_tag_to_top_all(bg_tag)
            except Exception:
                pass

        # refresh UI lightly
        try:
            safe_highlight_event(None)
        except Exception:
            pass
    except Exception:
        pass

def _choose_fg_from_toolbar(event=None):
    """Show color chooser for FG, preserve selection and apply result. Button updates to contrast text color."""
    try:
        _record_selection_for_font(event)
        c = safe_askcolor(fg_color_var.get(), title="Choose foreground color")
        hexc = get_hex_color(c)
        if hexc:
            fg_color_var.set(hexc)
            try:
                contrast = _contrast_text_color(hexc)
                btn_fg.config(bg=hexc, activebackground=hexc, fg=contrast, activeforeground=contrast)
            except Exception:
                pass
            _restore_selection_for_font()
            apply_color_to_selection(foreground=hexc)
            try:
                textArea.focus_set()
            except Exception:
                pass
    except Exception:
        pass

def _choose_bg_from_toolbar(event=None):
    """Show color chooser for BG, preserve selection and apply result. Button updates to contrast text color."""
    try:
        _record_selection_for_font(event)
        c = safe_askcolor(bg_color_var.get(), title="Choose background color")
        hexc = get_hex_color(c)
        if hexc:
            bg_color_var.set(hexc)
            try:
                contrast = _contrast_text_color(hexc)
                btn_bg.config(bg=hexc, activebackground=hexc, fg=contrast, activeforeground=contrast)
            except Exception:
                pass
            _restore_selection_for_font()
            apply_color_to_selection(background=hexc)
            try:
                textArea.focus_set()
            except Exception:
                pass
    except Exception:
        pass
# -------------------------
# Bindings & widget wiring
# -------------------------
# toolbar buttons (single definitions)
topBarContainer = Frame(root)
topBarContainer.pack(side=TOP, fill=X)

# primary toolbar (left-aligned actions)
toolBar = Frame(topBarContainer, bg='blue')
toolBar.pack(side=TOP, fill=X)
btn1 = Button(toolBar, text='New', command=lambda: newFile())
btn1.pack(side=LEFT, padx=2, pady=2)
btn2 = Button(toolBar, text='Open', command=lambda: open_file_action())
btn2.pack(side=LEFT, padx=2, pady=2)
btn3 = Button(toolBar, text='Save', command=lambda: save_file())
btn3.pack(side=LEFT, padx=2, pady=2)
btnSaveMD = Button(toolBar, text='Save MD', command=lambda: save_as_markdown(textArea))
btnSaveMD.pack(side=LEFT, padx=2, pady=2)
formatButton1 = Button(toolBar, text='Bold', command=format_bold)
formatButton1.pack(side=LEFT, padx=2, pady=2)
formatButton2 = Button(toolBar, text='Italic', command=format_italic)
formatButton2.pack(side=LEFT, padx=2, pady=2)
formatButton3 = Button(toolBar, text='Underline', command=format_underline)
formatButton3.pack(side=LEFT, padx=2, pady=2)
formatButton4 = Button(toolBar, text='Remove Formatting', command=remove_all_formatting)
formatButton4.pack(side=LEFT, padx=2, pady=2)
if _ML_AVAILABLE:
    buttonAI = Button(toolBar, text=_AI_BUTTON_DEFAULT_TEXT, command=lambda: Thread(target=on_ai_button_click, daemon=True).start())
    # create unload button but don't show it until model is loaded
    buttonUnload = Button(toolBar, text='Unload AI', command=unload_model)
else:
    buttonAI = Button(toolBar, text='AI Unavailable', state='disabled')
    buttonUnload = Button(toolBar, text='Unload AI', state='disabled')
buttonAI.pack(side=LEFT, padx=2, pady=2)

formatButton5 = Button(toolBar, text='Settings', command=lambda: setting_modal())
formatButton5.pack(side=RIGHT, padx=2, pady=2)
formatButton6 = Button(toolBar, text='Edit Syntax', command=lambda: setting_syntax_modal())
formatButton6.pack(side=RIGHT, padx=2, pady=2)
# Toolbar toggle: "Suppress Template Prompt" (checked = suppress prompts)
# Persisted config key remains 'promptTemplate' (True means "prompt enabled"), so we invert when storing.
templatePromptVar = BooleanVar(value=not config.getboolean("Section1", "promptTemplate", fallback=True))
suppress_template_prompt_session = BooleanVar(value=False)


def _on_template_prompt_toggle():
    try:
        # invert semantics for stored config: stored 'promptTemplate' should be True when prompting is enabled
        cfg_val = not bool(templatePromptVar.get())
        config.set("Section1", "promptTemplate", str(cfg_val))
        with open(INI_PATH, 'w') as cfgf:
            config.write(cfgf)
    except Exception:
        pass
try:
    tpl_chk = ttk.Checkbutton(toolBar, text='Suppress Template Prompt', variable=templatePromptVar, command=_on_template_prompt_toggle)
    tpl_chk.pack(side=RIGHT, padx=2, pady=2)
except Exception:
    pass
presentToolBar = Frame(topBarContainer, bg=toolBar.cget('bg'))
presentToolBar.pack(side=TOP, fill=X)
editorNotebook.pack(side=LEFT, fill=BOTH, expand=True)

# Font family menu (render each entry in its own font) + selection-safe behavior
font_family_var = StringVar(value=config.get("Section1", "fontName", fallback=fontName))
font_size_var = StringVar(value=str(config.get("Section1", "fontSize", fallback=str(fontSize))))

# Menubutton + Menu so we can set a font per menu entry
font_menu_btn = Menubutton(presentToolBar, textvariable=font_family_var, relief=RAISED, direction='below')
font_menu = Menu(font_menu_btn, tearoff=0)
try:
    fonts = get_system_fonts()
    for fam in fonts:
        try:
            # show entry in its family (small preview size)
            preview_font = tkfont.Font(family=fam, size=max(9, min(14, int(font_size_var.get()) if font_size_var.get().isdigit() else 11)))
            font_menu.add_command(label=fam, font=preview_font, command=lambda f=fam: _on_font_menu_select(f))
        except Exception:
            # fallback: add without custom font
            font_menu.add_command(label=fam, command=lambda f=fam: _on_font_menu_select(f))
except Exception:
    pass
font_menu_btn.config(menu=font_menu)
font_menu_btn.pack(side=LEFT, padx=(6,2), pady=2)

# Clear-font button (removes any font_* tags from selection)
btn_clear_font = Button(presentToolBar, text='Clear Font', command=clear_font_from_selection)
btn_clear_font.pack(side=LEFT, padx=2, pady=2)

# Common sizes (Combobox) — restore selection before applying size
_common_sizes = ['8','9','10','11','12','13','14','16','18','20','22','24','28','32','36','48','72']
font_size_cb = ttk.Combobox(presentToolBar, textvariable=font_size_var, values=_common_sizes, width=6, state='readonly')
font_size_cb.pack(side=LEFT, padx=(2,6), pady=2)

# Hooks to preserve selection when interacting with dropdowns
font_menu_btn.bind('<Button-1>', _record_selection_for_font, add=True)
font_size_cb.bind('<Button-1>', _record_selection_for_font, add=True)

def _on_font_menu_select(family: str):
    """Menu command handler — restore selection, apply family, restore focus."""
    try:
        _restore_selection_for_font()
        font_family_var.set(family)
        apply_font_to_selection(family=family, size=None)
    finally:
        try:
            textArea.focus_set()
        except Exception:
            pass

def _on_font_size_selected(event=None):
    try:
        _restore_selection_for_font()
        apply_font_to_selection(family=None, size=int(font_size_var.get()))
    except Exception:
        pass

# bind size selection (and initial readonly selection)
font_size_cb.bind('<<ComboboxSelected>>', _on_font_size_selected)
# Create the buttons in the presentational toolbar (placed after font size combobox)
btn_fg = Button(presentToolBar, text='FG', command=lambda: _choose_fg_from_toolbar(), width=5)
try:
    # Prefer using configured color when valid; otherwise ensure button text is white so it's readable.
    c = (fg_color_var.get() or '').strip()
    if is_valid_color(c):
        try:
            contrast = _contrast_text_color(c)
            btn_fg.config(bg=c, activebackground=c, fg=contrast, activeforeground=contrast)
        except Exception:
            btn_fg.config(bg=c, activebackground=c)
    else:
        # blank/invalid color -> force readable white text on the button
        try:
            btn_fg.config(fg='#FFFFFF', activeforeground='#FFFFFF')
        except Exception:
            pass
except Exception:
    pass
btn_fg.pack(side=LEFT, padx=2, pady=2)
# preserve selection when interacting
btn_fg.bind('<Button-1>', _record_selection_for_font, add=True)

btn_bg = Button(presentToolBar, text='BG', command=lambda: _choose_bg_from_toolbar(), width=5)
try:
    c = (bg_color_var.get() or '').strip()
    if is_valid_color(c):
        try:
            contrast = _contrast_text_color(c)
            btn_bg.config(bg=c, activebackground=c, fg=contrast, activeforeground=contrast)
        except Exception:
            btn_bg.config(bg=c, activebackground=c)
    else:
        # blank/invalid color -> force readable white text on the button
        try:
            btn_bg.config(fg='#FFFFFF', activeforeground='#FFFFFF')
        except Exception:
            pass
except Exception:
    pass
btn_bg.pack(side=LEFT, padx=2, pady=2)
btn_bg.bind('<Button-1>', _record_selection_for_font, add=True)

# Presentational/tag buttons (map to HTML-like tags)
btn_strong = Button(presentToolBar, text='Strong', command=format_strong)
btn_strong.pack(side=LEFT, padx=2, pady=2)
btn_em = Button(presentToolBar, text='Em', command=format_em)
btn_em.pack(side=LEFT, padx=2, pady=2)

btn_small = Button(presentToolBar, text='Small', command=format_small)
btn_small.pack(side=LEFT, padx=2, pady=2)
btn_mark = Button(presentToolBar, text='Mark', command=format_mark)
btn_mark.pack(side=LEFT, padx=2, pady=2)
btn_code = Button(presentToolBar, text='Code', command=format_code)
btn_code.pack(side=LEFT, padx=2, pady=2)
btn_kbd = Button(presentToolBar, text='Kbd', command=format_kbd)
btn_kbd.pack(side=LEFT, padx=2, pady=2)
btn_sub = Button(presentToolBar, text='Sub', command=format_sub)
btn_sub.pack(side=LEFT, padx=2, pady=2)
btn_sup = Button(presentToolBar, text='Sup', command=format_sup)
btn_sup.pack(side=LEFT, padx=2, pady=2)
btn_marquee = Button(presentToolBar, text='Marquee', command=format_marquee)
btn_marquee.pack(side=LEFT, padx=2, pady=2)
try:
    add_table_btn = Button(presentToolBar, text='Add Table', command=lambda: open_table_editor(textArea, None, None))
    add_table_btn.pack(side=RIGHT, padx=2, pady=2)
except Exception:
    pass
try:
    templatesBtn = Menubutton(presentToolBar, text='Templates', relief=RAISED)
    templates_menu = Menu(templatesBtn, tearoff=0)
    templates_menu.add_command(label='Python', command=lambda: create_template('python', open_in_new_tab=True))
    templates_menu.add_command(label='HTML', command=lambda: create_template('html', open_in_new_tab=True))
    templates_menu.add_command(label='Markdown', command=lambda: create_template('md', open_in_new_tab=True))
    templates_menu.add_command(label='JSON', command=lambda: create_template('json', open_in_new_tab=True))
    templatesBtn.config(menu=templates_menu)
    templatesBtn.pack(side=RIGHT, padx=2, pady=2)
except Exception:
    pass
# create refresh button on status bar (lower-right)
refreshSyntaxButton = Button(statusFrame, text='Refresh Syntax', command=refresh_full_syntax)
refreshSyntaxButton.pack(side=RIGHT, padx=4, pady=2)
# Detect Syntax (manual trigger) — runs quick autodetect on current tab
detectSyntaxButton = Button(statusFrame, text='Detect Syntax', command=lambda: manual_detect_syntax(force=True))
detectSyntaxButton.pack(side=RIGHT, padx=4, pady=2)
btnToggleRaw = Button(statusFrame, text='Toggle Raw', command=toggle_raw_rendered)
btnToggleRaw.pack(side=RIGHT, padx=4, pady=2)
# small view-state indicator (updates with active tab)
viewIndicator = Label(statusFrame, text='View: —', bd=1, relief=SUNKEN, anchor=W, width=18)
viewIndicator.pack(side=RIGHT, padx=4, pady=2)

syntaxToggleCheckbox = ttk.Checkbutton(
    statusFrame,
    text='Syntax',
    variable=updateSyntaxHighlighting,
    command=_on_status_syntax_toggle
)
# pack to the left of the refresh button (pack order: refresh first, then checkbox -> checkbox sits left)
syntaxToggleCheckbox.pack(side=RIGHT, padx=(4,0), pady=2)

def _on_full_scan_toggle():
    """Persist full-scan toggle and update status text (does not trigger a scan itself)."""
    try:
        config.set("Section1", "fullScanEnabled", str(bool(fullScanEnabled.get())))
        with open(INI_PATH, 'w') as cfgf:
            config.write(cfgf)
    except Exception:
        pass
    try:
        statusBar['text'] = "Full scan enabled." if fullScanEnabled.get() else "Quick (local) highlighting mode."
    except Exception:
        pass

fullScanToggleCheckbox = ttk.Checkbutton(
    statusFrame,
    text='Full Scan',
    variable=fullScanEnabled,
    command=_on_full_scan_toggle
)
fullScanToggleCheckbox.pack(side=RIGHT, padx=(4,0), pady=2)
openAsSourceCheckbox = ttk.Checkbutton(
    statusFrame,
    text='Open as source',
    variable=openHtmlAsSourceVar,
    command=_on_open_as_source_toggle
)
openAsSourceCheckbox.pack(side=RIGHT, padx=(4,0), pady=2)


# Bindings
for k in ['(', '[', '{', '"', "'"]:
    textArea.bind(k, auto_pair)
try:
    textArea.bind('<Return>', _text_area_return)
except Exception:
    try:
        textArea.bind('<Return>', lambda e: (safe_highlight_event(e), smart_newline(e)))
    except Exception:
        pass
try:
    textArea.bind(
        '<KeyRelease>',
        lambda e: (
            _table_live_adjust(e),
            safe_highlight_event(e),
            detect_header_and_prompt(e),
            highlight_current_line(),
            redraw_line_numbers(),
            update_status_bar(),
            show_trailing_whitespace()
        )
    )
except Exception:
    textArea.bind('<KeyRelease>', lambda e: (safe_highlight_event(e), detect_header_and_prompt(e), highlight_current_line(), redraw_line_numbers(), update_status_bar(), show_trailing_whitespace()))
textArea.bind('<Button-1>', lambda e: root.after_idle(lambda: (safe_highlight_event(e), highlight_current_line(), redraw_line_numbers(), update_status_bar(), show_trailing_whitespace())))
textArea.bind('<MouseWheel>', lambda e: (safe_highlight_event(e), redraw_line_numbers(), show_trailing_whitespace()))
textArea.bind('<Configure>', lambda e: (redraw_line_numbers(), show_trailing_whitespace()))
root.bind('<Control-Key-s>', lambda event: save_file())

# -------------------------
# Settings modal
# -------------------------
def create_config_window():
    top = Toplevel(root)
    top.transient(root)
    top.grab_set()
    top.title("Settings")
    top.resizable(False, False)

    container = ttk.Frame(top, padding=12)
    container.grid(row=0, column=0, sticky='nsew')
    container.columnconfigure(0, weight=0)
    container.columnconfigure(1, weight=1)
    container.columnconfigure(2, weight=0)

    def mk_row(label_text, row, initial='', width=24):
        ttk.Label(container, text=label_text).grid(row=row, column=0, sticky='e', padx=(0,8), pady=6)
        ent = ttk.Entry(container, width=width)
        ent.grid(row=row, column=1, sticky='ew', pady=6)
        ent.insert(0, initial)
        return ent

    fontNameField = mk_row("Font", 0, config.get("Section1", "fontName"))
    fontSizeField = mk_row("Font Size", 1, config.get("Section1", "fontSize"))
    fontColorChoice = mk_row("Font Color", 2, config.get("Section1", "fontColor"))
    backgroundColorField = mk_row("Background", 3, config.get("Section1", "backgroundColor"))
    cursorColorField = mk_row("Cursor Color", 4, config.get("Section1", "cursorColor"))

    undoCheckVar = IntVar(value=config.getboolean("Section1", "undoSetting"))
    undoCheck = ttk.Checkbutton(container, text="Enable undo", variable=undoCheckVar)
    undoCheck.grid(row=5, column=0, sticky='w', pady=6)

    syntaxCheckVar = IntVar(value=config.getboolean("Section1", "syntaxHighlighting", fallback=True))
    syntaxCheck = ttk.Checkbutton(container, text="Enable syntax highlighting", variable=syntaxCheckVar)
    syntaxCheck.grid(row=5, column=1, sticky='w', pady=6)

    # New: open HTML/MD as source (do not parse) — still parse SIMPLEEDIT headers
    openAsSourceVar = IntVar(value=config.getboolean("Section1", "openHtmlAsSource", fallback=False))
    ttk.Checkbutton(container, text="Open HTML/MD as source (do not parse)", variable=openAsSourceVar).grid(row=6, column=1, sticky='e', pady=6, padx=(0,8))

    aiMaxContextField = mk_row("Max AI Context", 7, config.get("Section1", "aiMaxContext"))
    temperatureField = mk_row("AI Temperature", 8, config.get("Section1", "temperature"))
    top_kField = mk_row("AI top_k", 9, config.get("Section1", "top_k"))
    seedField = mk_row("AI seed", 10, config.get("Section1", "seed"))

    loadAIOnOpenVar = IntVar(value=config.getboolean("Section1", "loadAIOnOpen", fallback=False))
    loadAIOnNewVar = IntVar(value=config.getboolean("Section1", "loadAIOnNew", fallback=False))
    promptOnRecentOpen = config.getboolean("Section1", "promptOnRecentOpen", fallback=True)
    recentOpenDefault = config.get("Section1", "recentOpenDefault", fallback="new")  # "new" or "current"
    saveFormattingVar = IntVar(value=config.getboolean("Section1", "saveFormattingInFile", fallback=False))
    ttk.Checkbutton(container, text="Save formatting into file (hidden header)", variable=saveFormattingVar).grid(row=11, column=1, sticky='w', pady=6)
    ttk.Checkbutton(container, text="Load AI when opening a file", variable=loadAIOnOpenVar).grid(row=12, column=1, sticky='w', pady=6)
    ttk.Checkbutton(container, text="Load AI when creating a new file", variable=loadAIOnNewVar).grid(row=13, column=1, sticky='w', pady=6)
    # near other checkboxes in create_config_window()
    autoDetectVar = IntVar(value=config.getboolean("Section1", "autoDetectSyntax", fallback=True))
    ttk.Checkbutton(container, text="Autodetect syntax from file content", variable=autoDetectVar).grid(row=14, column=1, sticky='w', pady=6)
    promptRecentOpenVar = IntVar(value=config.getboolean("Section1", "promptOnRecentOpen", fallback=True))
    ttk.Checkbutton(container, text="Prompt when opening recent files", variable=promptRecentOpenVar).grid(row=16, column=1, sticky='w', pady=6)
    # New: control whether File->Open shows the custom modal
    promptOpenDialogVar = IntVar(value=config.getboolean("Section1", "openDialogModal", fallback=True))
    ttk.Checkbutton(container, text="Use custom Open dialog for File → Open", variable=promptOpenDialogVar).grid(row=18, column=1, sticky='w', pady=6)
    # CSS export controls
    css_mode = config.get("Section1", "exportCssMode", fallback="inline-element")
    cssModeVar = StringVar(value=css_mode)
    ttk.Label(container, text="Export CSS mode").grid(row=15, column=0, sticky='e', padx=(0,8), pady=6)
    css_frame = ttk.Frame(container)
    css_frame.grid(row=15, column=1, sticky='w')
    ttk.Radiobutton(css_frame, text="Inline styles (per-element)", variable=cssModeVar, value='inline-element').pack(anchor='w')
    ttk.Radiobutton(css_frame, text="Inline CSS block (<style>)", variable=cssModeVar, value='inline-block').pack(anchor='w')
    ttk.Radiobutton(css_frame, text="External CSS file", variable=cssModeVar, value='external').pack(anchor='w')

    cssPathField = mk_row("External CSS path", 17, config.get("Section1", "exportCssPath", fallback=""))
    def choose_css_path():
        p = filedialog.asksaveasfilename(initialdir=os.path.expanduser("~"),
                                         title="Choose CSS file path",
                                         defaultextension='.css',
                                         filetypes=(("CSS files","*.css"),("All files","*.*")))
        if p:
            cssPathField.delete(0, END)
            cssPathField.insert(0, p)

    ttk.Button(container, text="Browse CSS path...", command=choose_css_path).grid(row=17, column=2, padx=6)

    sw_font = Label(container, width=3, relief='sunken', bg=config.get("Section1", "fontColor"))
    sw_font.grid(row=2, column=2, padx=(8,0))
    sw_bg = Label(container, width=3, relief='sunken', bg=config.get("Section1", "backgroundColor"))
    sw_bg.grid(row=3, column=2, padx=(8,0))
    sw_cursor = Label(container, width=3, relief='sunken', bg=config.get("Section1", "cursorColor"))
    sw_cursor.grid(row=4, column=2, padx=(8,0))

        # make the small color swatches clickable (left-click opens chooser)
    try:
        sw_font.config(cursor="hand2")
        sw_bg.config(cursor="hand2")
        sw_cursor.config(cursor="hand2")

        sw_font.bind("<Button-1>", lambda e: choose_font_color())
        sw_bg.bind("<Button-1>", lambda e: choose_background_color())
        sw_cursor.bind("<Button-1>", lambda e: choose_cursor_color())
    except Exception:
        pass

        # Line numbers color controls
    lineNumberFgField = mk_row("Line numbers FG", 19, config.get("Section1", "lineNumberFg", fallback="#555555"))
    lineNumberBgField = mk_row("Line numbers BG", 20, config.get("Section1", "lineNumberBg", fallback="#000000"))
    lineHighlightField = mk_row("Line highlight BG", 21, config.get("Section1", "currentLineBg", fallback="#222222"))


    sw_ln_fg = Label(container, width=3, relief='sunken', bg=config.get("Section1", "lineNumberFg", fallback="#555555"))
    sw_ln_fg.grid(row=19, column=2, padx=(8,0))
    sw_ln_bg = Label(container, width=3, relief='sunken', bg=config.get("Section1", "lineNumberBg", fallback="#000000"))
    sw_ln_bg.grid(row=20, column=2, padx=(8,0))
    sw_line_high = Label(container, width=3, relief='sunken', bg=config.get("Section1", "currentLineBg", fallback="#222222"))
    sw_line_high.grid(row=21, column=2, padx=(8,0))

    try:
        sw_ln_fg.config(cursor="hand2")
        sw_ln_bg.config(cursor="hand2")
        sw_ln_fg.bind("<Button-1>", lambda e: choose_line_number_fg())
        sw_ln_bg.bind("<Button-1>", lambda e: choose_line_number_bg())
        sw_line_high.config(cursor="hand2")
        sw_line_high.bind("<Button-1>", lambda e: choose_line_highlight())
    except Exception:
        pass

    def choose_line_number_fg():
        c = safe_askcolor(lineNumberFgField.get(), title="Line numbers FG")
        hexc = get_hex_color(c)
        if hexc:
            lineNumberFgField.delete(0, END)
            lineNumberFgField.insert(0, hexc)
            try:
                sw_ln_fg.config(bg=hexc)
            except Exception:
                pass

    def choose_line_number_bg():
        c = safe_askcolor(lineNumberBgField.get(), title="Line numbers BG")
        hexc = get_hex_color(c)
        if hexc:
            lineNumberBgField.delete(0, END)
            lineNumberBgField.insert(0, hexc)
            try:
                sw_ln_bg.config(bg=hexc)
            except Exception:
                pass

    def choose_line_highlight():
        c = safe_askcolor(lineHighlightField.get(), title="Line highlight BG")
        hexc = get_hex_color(c)
        if hexc:
            lineHighlightField.delete(0, END)
            lineHighlightField.insert(0, hexc)
            try:
                sw_line_high.config(bg=hexc)
            except Exception:
                pass

    def choose_font_color():
        c = safe_askcolor(fontColorChoice.get(), title="Font Color")
        hexc = get_hex_color(c)
        if hexc:
            fontColorChoice.delete(0, END)
            fontColorChoice.insert(0, hexc)
            sw_font.config(bg=hexc)

    def choose_background_color():
        c = safe_askcolor(backgroundColorField.get(), title='Background Color')
        hexc = get_hex_color(c)
        if hexc:
            backgroundColorField.delete(0, END)
            backgroundColorField.insert(0, hexc)
            sw_bg.config(bg=hexc)

    def choose_cursor_color():
        c = safe_askcolor(cursorColorField.get(), title="Cursor Color")
        hexc = get_hex_color(c)
        if hexc:
            cursorColorField.delete(0, END)
            cursorColorField.insert(0, hexc)
            sw_cursor.config(bg=hexc)
    action_frame = ttk.Frame(top, padding=(12,8))
    action_frame.grid(row=1, column=0, sticky='ew')
    action_frame.columnconfigure(0, weight=1)
    action_frame.columnconfigure(1, weight=0)
    action_frame.columnconfigure(2, weight=0)
    action_frame.columnconfigure(3, weight=0)

    def on_closing():
        config.set("Section1", "fontName", fontNameField.get())
        config.set("Section1", "fontSize", fontSizeField.get())
        config.set("Section1", "fontColor", fontColorChoice.get())
        config.set("Section1", "backgroundColor", backgroundColorField.get())
        config.set("Section1", "cursorColor", cursorColorField.get())
        config.set("Section1", "undoSetting", str(bool(undoCheckVar.get())))
        config.set("Section1", "aiMaxContext", aiMaxContextField.get())
        config.set("Section1", "temperature", temperatureField.get())
        config.set("Section1", "top_k", top_kField.get())
        config.set("Section1", "seed", seedField.get())
        # persist Open-dialog preference
        config.set("Section1", "openDialogModal", str(bool(promptOpenDialogVar.get())))
        config.set("Section1", "lineNumberFg", lineNumberFgField.get())
        config.set("Section1", "lineNumberBg", lineNumberBgField.get())
        config.set("Section1", "currentLineBg", lineHighlightField.get())
        # persist new options
        config.set("Section1", "syntaxHighlighting", str(bool(syntaxCheckVar.get())))
        config.set("Section1", "loadAIOnOpen", str(bool(loadAIOnOpenVar.get())))
        config.set("Section1", "loadAIOnNew", str(bool(loadAIOnNewVar.get())))
        config.set("Section1", "saveFormattingInFile", str(bool(saveFormattingVar.get())))
        config.set("Section1", "exportCssMode", cssModeVar.get())
        config.set("Section1", "exportCssPath", cssPathField.get())
        # persist new open-as-source option
        config.set("Section1", "openHtmlAsSource", str(bool(openAsSourceVar.get())))
        config.set("Section1", "promptOnRecentOpen", str(bool(promptRecentOpenVar.get())))
        try:
            with open(INI_PATH, 'w') as configfile:
                config.write(configfile)
        except Exception:
            pass

        nonlocal_values_reload()

        try:
            updateSyntaxHighlighting.set(1 if syntaxCheckVar.get() else 0)
            if syntaxCheckVar.get():
                highlightPythonInit()
            else:
                for t in ('string', 'keyword', 'comment', 'selfs', 'def', 'number', 'variable',
                          'decorator', 'class_name', 'constant', 'attribute', 'builtin', 'todo'):
                    textArea.tag_remove(t, "1.0", "end")
                statusBar['text'] = "Syntax highlighting disabled."
        except Exception:
            pass

                # apply new line-number colors to all open tabs


        global loadAIOnOpen, loadAIOnNew
        try:
            loadAIOnOpen = bool(loadAIOnOpenVar.get())
            loadAIOnNew = bool(loadAIOnNewVar.get())
        except Exception:
            pass

        top.destroy()

    def refresh_from_file():
        fontNameField.delete(0, END)
        fontNameField.insert(0, config.get("Section1", "fontName"))
        fontSizeField.delete(0, END)
        fontSizeField.insert(0, config.get("Section1", "fontSize"))
        fontColorChoice.delete(0, END)
        fontColorChoice.insert(0, config.get("Section1", "fontColor"))
        backgroundColorField.delete(0, END)
        backgroundColorField.insert(0, config.get("Section1", "backgroundColor"))
        cursorColorField.delete(0, END)
        cursorColorField.insert(0, config.get("Section1", "cursorColor"))
        undoCheckVar.set(config.getboolean("Section1", "undoSetting"))
        aiMaxContextField.delete(0, END)
        aiMaxContextField.insert(0, config.get("Section1", "aiMaxContext"))
        top_kField.delete(0, END)
        top_kField.insert(0, config.get("Section1", "top_k"))
        seedField.delete(0, END)
        seedField.insert(0, config.get("Section1", "seed"))
        temperatureField.delete(0, END)
        temperatureField.insert(0, config.get("Section1", "temperature"))
            
        lineNumberFgField.delete(0, END)
        lineNumberFgField.insert(0, config.get("Section1", "lineNumberFg", fallback="#555555"))
        lineNumberBgField.delete(0, END)
        lineNumberBgField.insert(0, config.get("Section1", "lineNumberBg", fallback="#000000"))
        lineHighlightField.delete(0, END)
        lineHighlightField.insert(0, config.get("Section1", "currentLineBg", fallback="#222222"))

        try:
            syntaxCheckVar.set(config.getboolean("Section1", "syntaxHighlighting", fallback=True))
            loadAIOnOpenVar.set(config.getboolean("Section1", "loadAIOnOpen", fallback=False))
            loadAIOnNewVar.set(config.getboolean("Section1", "loadAIOnNew", fallback=False))
            saveFormattingVar.set(config.getboolean("Section1", "saveFormattingInFile", fallback=False))
            cssModeVar.set(config.get("Section1", "exportCssMode", fallback="inline-element"))
            cssPathField.delete(0, END)
            cssPathField.insert(0, config.get("Section1", "exportCssPath", fallback=""))
            # refresh open-as-source checkbox from config
            openAsSourceVar.set(config.getboolean("Section1", "openHtmlAsSource", fallback=False))
            autoDetectVar.set(config.getboolean("Section1", "autoDetectSyntax", fallback=True))
            promptRecentOpenVar.set(config.getboolean("Section1", "promptOnRecentOpen", fallback=True))
            promptOpenDialogVar.set(config.getboolean("Section1", "openDialogModal", fallback=True))

        except Exception:
            pass

        try:
            sw_font.config(bg=config.get("Section1", "fontColor"))
            sw_bg.config(bg=config.get("Section1", "backgroundColor"))
            sw_cursor.config(bg=config.get("Section1", "cursorColor"))
            sw_ln_fg.config(bg=config.get("Section1", "lineNumberFg", fallback="#555555"))
            sw_ln_bg.config(bg=config.get("Section1", "lineNumberBg", fallback="#000000"))

        except Exception:
            pass

    ttk.Button(action_frame, text="Save", command=on_closing).grid(row=0, column=1, padx=6)
    ttk.Button(action_frame, text="Refresh from file", command=refresh_from_file).grid(row=0, column=2, padx=6)
    ttk.Button(action_frame, text="Close", command=top.destroy).grid(row=0, column=3, padx=6)

    fontNameField.focus_set()
    center_window(top)
    refresh_from_file()


def nonlocal_values_reload():
    global fontName, fontSize, fontColor, backgroundColor, undoSetting, cursorColor, aiMaxContext, temperature, top_k, seed, exportCssMode, exportCssPath, openHtmlAsSource, promptOnRecentOpen, recentOpenDefault
    fontName = config.get("Section1", "fontName")
    fontSize = int(config.get("Section1", "fontSize"))
    fontColor = config.get("Section1", "fontColor")
    backgroundColor = config.get("Section1", "backgroundColor")
    undoSetting = config.getboolean("Section1", "undoSetting")
    cursorColor = config.get("Section1", "cursorColor")
    aiMaxContext = int(config.get("Section1", "aiMaxContext"))
    seed = int(config.get("Section1", "seed"))
    top_k = int(config.get("Section1", "top_k"))
    temperature = float(config.get("Section1", "temperature"))
    loadAIOnOpen = config.getboolean("Section1", "loadAIOnOpen", fallback=False)
    loadAIOnNew = config.getboolean("Section1", "loadAIOnNew", fallback=False)
    saveFormattingInFile = config.getboolean("Section1", "saveFormattingInFile", fallback=False)
        # line number colors
    lineNumberFg = config.get("Section1", "lineNumberFg", fallback="#555555")
    lineNumberBg = config.get("Section1", "lineNumberBg", fallback="#000000")
    currentLineBg = config.get("Section1", "currentLineBg", fallback="#222222")

    # load css export settings
    exportCssMode = config.get("Section1", "exportCssMode", fallback="inline-element")
    exportCssPath = config.get("Section1", "exportCssPath", fallback="")

    # load open-as-source setting
    openHtmlAsSource = config.getboolean("Section1", "openHtmlAsSource", fallback=False)
    try:
        openHtmlAsSourceVar.set(1 if openHtmlAsSource else 0)
    except Exception:
        pass
    # load recent-open settings
    promptOnRecentOpen = config.getboolean("Section1", "promptOnRecentOpen", fallback=True)
    recentOpenDefault = config.get("Section1", "recentOpenDefault", fallback="new")
    # load open-dialog settings
    openDialogModal = config.getboolean("Section1", "openDialogModal", fallback=True)
    openDialogDefault = config.get("Section1", "openDialogDefault", fallback="new")
    textArea.config(font=(fontName, fontSize), bg=backgroundColor, fg=fontColor, insertbackground=cursorColor, undo=undoSetting)
    # reapply any saved/edited syntax overrides
    try:
        load_syntax_config()
    except Exception:
        pass

def setting_modal():
    create_config_window()


# -------------------------
# Misc helpers / periodic tasks
# -------------------------
stop_event = threading.Event()


def ready_update():
    root.after(1000, lambda: statusBar.config(text="Ready"))



def newFile():
    # create a new untitled tab instead of clearing the current buffer
    try:
        create_editor_tab('Untitled', content='', filename='')
        statusBar['text'] = "New Document (tab)!"
        if _ML_AVAILABLE and loadAIOnNew and not _model_loaded and not _model_loading:
            Thread(target=lambda: _start_model_load(start_autocomplete=False), daemon=True).start()
    except Exception:
        # fallback to old behavior if something goes wrong
        try:
            textArea.delete('1.0', 'end')
            statusBar['text'] = "New Document!"
        except Exception:
            pass
    Thread(target=ready_update, daemon=True).start()

# populate recent menu
try:
    refresh_recent_menu()
except Exception:
    pass
try:
    root.after(250, _init_toolbar_color_buttons)
    root.after(1200, _init_toolbar_color_buttons)
except Exception:
    pass

# -------------------------
# Main loop
# -------------------------
def main():
    try:
        root.mainloop()
    finally:
        stop_event.set()

if __name__ == '__main__':
    main()