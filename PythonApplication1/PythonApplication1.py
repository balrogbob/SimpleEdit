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


def open_recent_file(path: str):
    """Open a recent file (called from recent menu)."""
    try:
        with open(path, 'r', errors='replace', encoding='utf-8') as fh:
            raw = fh.read()

        # First try SIMPLEEDIT metadata (preferred)
        content, meta = _extract_header_and_meta(raw)
        if meta:
            textArea.delete('1.0', 'end')
            textArea.insert('1.0', content)
            statusBar['text'] = f"'{path}' opened successfully!"
            root.fileName = path
            try:
                if _ML_AVAILABLE and loadAIOnOpen and not _model_loaded and not _model_loading:
                    Thread(target=lambda: _start_model_load(start_autocomplete=False), daemon=True).start()
            except Exception:
                pass

            add_recent_file(path)
            if meta:
                root.after(0, lambda: _apply_formatting_from_meta(meta))

            if updateSyntaxHighlighting.get():
                root.after(0, highlightPythonInit)
            return

        # No SIMPLEEDIT meta — if file is .md/.html attempt HTML-aware parsing to reconstruct tags
        ext = path.lower().split('.')[-1] if isinstance(path, str) else ''
        if ext in ('md', 'html', 'htm'):
            plain, tags_meta = _parse_html_and_apply(raw)
            textArea.delete('1.0', 'end')
            textArea.insert('1.0', plain)
            statusBar['text'] = f"'{path}' opened (HTML/MD parsed)!"
            root.fileName = path
            add_recent_file(path)
            if tags_meta and tags_meta.get('tags'):
                root.after(0, lambda: _apply_formatting_from_meta(tags_meta))
            if updateSyntaxHighlighting.get():
                root.after(0, highlightPythonInit)
            refresh_recent_menu()
            return

        # Fallback: no meta and not md/html - insert raw content
        textArea.delete('1.0', 'end')
        textArea.insert('1.0', raw)
        statusBar['text'] = f"'{path}' opened successfully!"
        root.fileName = path
        try:
            if _ML_AVAILABLE and loadAIOnOpen and not _model_loaded and not _model_loading:
                Thread(target=lambda: _start_model_load(start_autocomplete=False), daemon=True).start()
        except Exception:
            pass

        add_recent_file(path)
        refresh_recent_menu()
        if updateSyntaxHighlighting.get():
            root.after(0, highlightPythonInit)
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


def get_hex_color(color_tuple):
    """Return a hex string from a colorchooser return value."""
    if not color_tuple:
        return ""
    if isinstance(color_tuple, tuple) and len(color_tuple) >= 2:
        # colorchooser returns ((r,g,b), '#rrggbb')
        return color_tuple[1]
    m = re.search(r'#\w+', str(color_tuple))
    return m.group(0) if m else ""


def selection_or_all():
    """Return a (start, end) range for the current selection or entire buffer."""
    ranges = textArea.tag_ranges("sel")
    if ranges:
        return ranges[0], ranges[1]
    return "1.0", "end-1c"


# -------------------------
# Tkinter UI - create root and widgets
# -------------------------
root = Tk()
root.geometry("800x600")
root.title('SimpleEdit')
root.fileName = ""

menuBar = Menu(root)
root.config(menu=menuBar)

# File/Edit menus
fileMenu = Menu(menuBar, tearoff=False)
recentMenu = Menu(menuBar, tearoff=False)
editMenu = Menu(menuBar, tearoff=False)

menuBar.add_cascade(label="File", menu=fileMenu)
fileMenu.add_command(label='New', command=lambda: newFile())
fileMenu.add_separator()
fileMenu.add_command(label='Open', command=lambda: open_file_threaded())
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

# initialize line numbers canvas placeholder
lineNumbersCanvas = None


def init_line_numbers():
    global lineNumbersCanvas
    if lineNumbersCanvas is None:
        lineNumbersCanvas = Canvas(root, width=40, bg='black', highlightthickness=0)
        lineNumbersCanvas.pack(side=LEFT, fill=Y)

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

init_line_numbers()

# Text area
textArea = Text(root, insertbackground=cursorColor, undo=undoSetting)
textArea.pack(side=LEFT, fill=BOTH, expand=True)
textArea['bg'] = backgroundColor
textArea['fg'] = fontColor
textArea['font'] = (fontName, fontSize)

# scrollbar
scroll = Scrollbar(root, command=textArea.yview)
textArea.configure(yscrollcommand=scroll.set)
scroll.pack(side=RIGHT, fill=Y)



# tag configs (extended)
textArea.tag_config("number", foreground="#FDFD6A")
textArea.tag_config("selfs", foreground="yellow")
textArea.tag_config("variable", foreground="#8A2BE2")
textArea.tag_config("decorator", foreground="#66CDAA")
textArea.tag_config("class_name", foreground="#FFB86B")
textArea.tag_config("constant", foreground="#FF79C6")
textArea.tag_config("attribute", foreground="#33ccff")
textArea.tag_config("builtin", foreground="#9CDCFE")
textArea.tag_config("def", foreground="orange")
textArea.tag_config("keyword", foreground="red")
textArea.tag_config("string", foreground="#C9CA6B")
textArea.tag_config("operator", foreground="#AAAAAA")
textArea.tag_config("comment", foreground="#75715E")
textArea.tag_config("todo", foreground="#ffffff", background="#B22222")
textArea.tag_config("bold", font=(fontName, fontSize, "bold"))
textArea.tag_config("italic", font=(fontName, fontSize, "italic"))
textArea.tag_config("underline", font=(fontName, fontSize, "underline"))
textArea.tag_config("all", font=(fontName, fontSize, "bold", "italic", "underline"))
textArea.tag_config("underlineitalic", font=(fontName, fontSize, "italic", "underline"))
textArea.tag_config("boldunderline", font=(fontName, fontSize, "bold", "underline"))
textArea.tag_config("bolditalic", font=(fontName, fontSize, "bold", "italic"))
textArea.tag_config("currentLine", background="#222222")
textArea.tag_config("trailingWhitespace", background="#331111")
textArea.tag_config("find_match", background="#444444", foreground='white')
# new variable tag


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
    "find_match": {"fg": "white", "bg": "#444444"}
}

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
                    textArea.tag_config(tag, **kwargs)
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
    swatches = {}
    inputs_fg = {}
    inputs_bg = {}
    for tag, defaults in _DEFAULT_TAG_COLORS.items():
        ttk.Label(tab_tags, text=tag).grid(row=row, column=0, sticky='w', padx=(0,8), pady=4)

        # FG entry + chooser
        ent_fg = ttk.Entry(tab_tags, width=18)
        ent_fg.grid(row=row, column=1, sticky='w', pady=4)
        ent_val_fg = config.get('Syntax', f'tag.{tag}.fg', fallback=defaults.get('fg', ''))
        ent_fg.insert(0, ent_val_fg)
        def make_choose_fg(e=ent_fg):
            def choose_fg():
                c = safe_askcolor(e.get())
                hexc = get_hex_color(c)
                if hexc:
                    e.delete(0, END)
                    e.insert(0, hexc)
                    # don't change swatch bg for fg chooser; swatch reflects background color
            return choose_fg
        ttk.Button(tab_tags, text='Choose FG...', command=make_choose_fg()).grid(row=row, column=2, padx=6)

        # BG entry + chooser
        ent_bg = ttk.Entry(tab_tags, width=18)
        ent_bg.grid(row=row, column=3, sticky='w', pady=4)
        ent_val_bg = config.get('Syntax', f'tag.{tag}.bg', fallback=defaults.get('bg', ''))
        ent_bg.insert(0, ent_val_bg)
        def make_choose_bg(e=ent_bg, s_tag=tag):
            def choose_bg():
                c = safe_askcolor(e.get())
                hexc = get_hex_color(c)
                if hexc:
                    e.delete(0, END)
                    e.insert(0, hexc)
                    sw = swatches.get(s_tag)
                    if sw and is_valid_color(hexc):
                        sw.config(bg=hexc)
            return choose_bg
        ttk.Button(tab_tags, text='Choose BG...', command=make_choose_bg()).grid(row=row, column=4, padx=6)

        # swatch shows background (preferred), fall back to fg or leave default if invalid
        sw = Label(tab_tags, width=3, relief='sunken')
        sw_color = ent_val_bg or defaults.get('bg') or ent_val_fg or defaults.get('fg', '')
        if is_valid_color(sw_color):
            sw.config(bg=sw_color)
        sw.grid(row=row, column=5, padx=(8,0))

        swatches[tag] = sw
        inputs_fg[tag] = ent_fg
        inputs_bg[tag] = ent_bg
        row += 1

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
    for key in ('STRING_RE', 'COMMENT_RE', 'NUMBER_RE', 'DECORATOR_RE', 'CLASS_RE', 'VAR_ASSIGN_RE', 'ATTRIBUTE_RE', 'TODO_RE'):
        ttk.Label(tab_regex, text=key).grid(row=r, column=0, sticky='nw', pady=(6,0))
        ent = Text(tab_regex, height=2, width=60)
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
                # update swatch
                sw_color = bg_val or fg_val or ''
                if is_valid_color(sw_color):
                    try:
                        swatches[tag].config(bg=sw_color)
                    except Exception:
                        pass
                else:
                    try:
                        swatches[tag].config(bg=tab_tags.cget('background'))
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
            # swatch: prefer default bg then fg; only apply if valid
            sw_color = defaults.get('bg') or defaults.get('fg') or ''
            if is_valid_color(sw_color):
                try:
                    swatches[tag].config(bg=sw_color)
                except Exception:
                    pass
            else:
                # clear any explicit bg if invalid (let system default show)
                try:
                    swatches[tag].config(bg=tab_tags.cget('background'))
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
    """Return header string (commented base64 JSON) for current non-syntax tags, or '' if no formatting."""
    try:
        tags_to_save = ('bold', 'italic', 'underline', 'all',
                        'underlineitalic', 'boldunderline', 'bolditalic')
        data = {}
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
        if not data:
            return ''
        meta = {'version': 1, 'tags': data}
        b64 = base64.b64encode(json.dumps(meta).encode('utf-8')).decode('ascii')
        return "# ---SIMPLEEDIT-META-BEGIN---\n# " + b64 + "\n# ---SIMPLEEDIT-META-END---\n"
    except Exception:
        return ''


def _apply_formatting_from_meta(meta):
    """Apply saved tag ranges (meta is dict with key 'tags') on the UI thread."""
    try:
        tags = meta.get('tags', {}) if isinstance(meta, dict) else {}
        # We need to ensure tags exist; tag_add will silently fail if indices out of range
        for tag, ranges in tags.items():
            for start, end in ranges:
                try:
                    textArea.tag_add(tag, f"1.0 + {int(start)}c", f"1.0 + {int(end)}c")
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
def toggle_tag_complex(tag):
    """High-level toggling that preserves combinations similar to original behaviour."""
    start, end = selection_or_all()
    if textArea.tag_ranges(tag):
        textArea.tag_remove(tag, start, end)
        return

    # Simplified combination logic: remove mutually exclusive combinations and add requested tag.
    # Keep the previous detailed transformations minimal but consistent.
    # Remove 'all' if adding single style; remove conflicting combos.
    for t in ('all', 'bolditalic', 'underlineitalic', 'boldunderline'):
        if textArea.tag_ranges(t):
            textArea.tag_remove(t, start, end)

    textArea.tag_add(tag, start, end)


def format_bold():
    toggle_tag_complex("bold")


def format_italic():
    toggle_tag_complex("italic")


def format_underline():
    toggle_tag_complex("underline")


def remove_all_formatting():
    start, end = selection_or_all()
    for t in ("underline", "underlineitalic", "all", "boldunderline", "italic", "bold", "bolditalic"):
        textArea.tag_remove(t, start, end)


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
    if not root.fileName:
        save_file_as()
        return
    try:
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
    except Exception as e:
        messagebox.showerror("Error", str(e))


def open_file_threaded():
    # runs in thread
    try:
        fileName = filedialog.askopenfilename(
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
        if not fileName:
            return
        with open(fileName, 'r', errors='replace', encoding='utf-8') as f:
            raw = f.read()

        # First try to extract SIMPLEEDIT meta (preferred)
        content, meta = _extract_header_and_meta(raw)
        if meta:
            textArea.delete('1.0', 'end')
            textArea.insert('1.0', content)
            statusBar['text'] = f"'{fileName}' opened successfully!"
            root.fileName = fileName
            add_recent_file(fileName)
            refresh_recent_menu()
            root.after(0, lambda: _apply_formatting_from_meta(meta))
            try:
                if _ML_AVAILABLE and loadAIOnOpen and not _model_loaded and not _model_loading:
                    Thread(target=lambda: _start_model_load(start_autocomplete=False), daemon=True).start()
            except Exception:
                pass
            if updateSyntaxHighlighting.get():
                root.after(0, highlightPythonInit)
            return

        # If no meta and file is .md or .html attempt HTML-aware parsing to reconstruct tags
        ext = fileName.lower().split('.')[-1]
        if ext in ('md', 'html', 'htm'):
            plain, tags_meta = _parse_html_and_apply(raw)
            textArea.delete('1.0', 'end')
            textArea.insert('1.0', plain)
            root.fileName = fileName
            statusBar['text'] = f"'{fileName}' opened (HTML/MD parsed)!"
            add_recent_file(fileName)
            refresh_recent_menu()
            if tags_meta and tags_meta.get('tags'):
                root.after(0, lambda: _apply_formatting_from_meta(tags_meta))
            # still run normal syntax-highlighting pass to refresh persisted symbol highlights
            if updateSyntaxHighlighting.get():
                root.after(0, highlightPythonInit)
            return

        # Fallback: no meta and not md/html - insert raw
        textArea.delete('1.0', 'end')
        textArea.insert('1.0', raw)
        statusBar['text'] = f"'{fileName}' opened successfully!"
        root.fileName = fileName
        try:
            if _ML_AVAILABLE and loadAIOnOpen and not _model_loaded and not _model_loading:
                Thread(target=lambda: _start_model_load(start_autocomplete=False), daemon=True).start()
        except Exception:
            pass
        add_recent_file(fileName)
        refresh_recent_menu()
        if updateSyntaxHighlighting.get():
            root.after(0, highlightPythonInit)
    except Exception as e:
        messagebox.showerror("Error", str(e))

def _collect_formatting_ranges():
    """Return dict mapping formatting tag -> list of (start_offset, end_offset)."""
    tags_to_check = ('bold', 'italic', 'underline', 'all',
                     'underlineitalic', 'boldunderline', 'bolditalic')
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
    """Wrap a text segment according to active tag set into Markdown/HTML."""
    # Determine boolean flags considering explicit combo tags and 'all'
    has_bold = any(t in active_tags for t in ('bold', 'bolditalic', 'boldunderline', 'all'))
    has_italic = any(t in active_tags for t in ('italic', 'bolditalic', 'underlineitalic', 'all'))
    has_underline = any(t in active_tags for t in ('underline', 'boldunderline', 'underlineitalic', 'all'))

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

    return inner

def save_as_markdown(textArea):
    fileName = funcs.save_as_markdown(textArea)
    statusBar['text'] = f"'{fileName}' saved successfully!"
    root.fileName = fileName
    add_recent_file(fileName)
    refresh_recent_menu()



# --- Parse saved HTML fragments or full HTML docs back into plain text + tags ---
def _parse_html_and_apply(raw):
    """
    Parse raw HTML fragment or document and extract plain text and tag ranges.
    Returns (plain_text, tags_dict) where tags_dict matches _apply_formatting_from_meta format.
    """
    try:
        # If full document, try to extract body contents heuristically
        m = re.search(r'<body[^>]*>(.*)</body>', raw, flags=re.DOTALL | re.IGNORECASE)
        fragment = m.group(1) if m else raw

        parser = funcs._SimpleHTMLToTagged()
        parser.feed(fragment)
        plain, ranges = parser.get_result()
        # convert ranges (already [[s,e],...]) into meta shape
        return plain, {'tags': ranges}
    except Exception:
        return raw, {}


# -------------------------
# Highlighting
# -------------------------
# Highlighting toggle (initialized from config)
updateSyntaxHighlighting = IntVar(value=config.getboolean("Section1", "syntaxHighlighting", fallback=True))


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

        # determine region to scan (visible region by default)
        if scan_start is None or scan_end is None:
            try:
                first_visible = textArea.index('@0,0')
                last_visible = textArea.index(f'@0,{textArea.winfo_height()}')
                start_line = int(first_visible.split('.')[0])
                end_line = int(last_visible.split('.')[0])
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
            textArea.tag_remove(t, start, end)

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
                # optionally tag inner expression as 'builtin'/'keyword' by re-applying regex on sub
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
    """Trigger a non-blocking initial syntax scan on load (snapshot + background worker)."""
    if not updateSyntaxHighlighting.get():
        # clear tags (include new tags)
        for t in ('string', 'keyword', 'comment', 'selfs', 'def', 'number', 'variable',
                  'decorator', 'class_name', 'constant', 'attribute', 'builtin', 'todo'):
            textArea.tag_remove(t, "1.0", "end")
        statusBar['text'] = "Syntax highlighting disabled."
        return

    statusBar['text'] = "Processing initial syntax..."
    root.update_idletasks()

    try:
        content_snapshot = textArea.get("1.0", "end-1c")
    except Exception:
        content_snapshot = ""

    # show progress popup (starts indeterminate)
    dlg, pb, status = show_progress_popup("Initial syntax highlighting")
    status['text'] = "Scanning..."

    # progress callback MUST be safe to call from worker thread.
    def progress_cb(pct, msg=""):
        # schedule UI update on main thread
        def ui():
            try:
                # switch to determinate on first meaningful update
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
        # schedule application of tags on UI thread and finish-up steps
        def apply_and_finish():
            try:
                _apply_full_tags(actions, new_vars, new_defs)
                # Full content scan to discover new symbols (persist them)
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

                # force full-buffer scan and tagging
                highlight_python_helper(None, scan_start="1.0", scan_end="end-1c")
                statusBar['text'] = "Ready"
            finally:
                close_progress_popup(dlg, pb)

        try:
            root.after(0, apply_and_finish)
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


pairs = {'(': ')', '[': ']', '{': '}', '"': '"', "'": "'"}


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


def redraw_line_numbers(event=None):
    global lineNumbersCanvas
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
        lineNumbersCanvas.create_text(2, y, anchor='nw', text=line, fill='#555555')
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


# -------------------------
# Bindings & widget wiring
# -------------------------
# toolbar buttons (single definitions)
btn1 = Button(toolBar, text='New', command=lambda: newFile())
btn1.pack(side=LEFT, padx=2, pady=2)
btn2 = Button(toolBar, text='Open', command=lambda: open_file_threaded)
btn2.pack(side=LEFT, padx=2, pady=2)
btn3 = Button(toolBar, text='Save', command=lambda: save_file_as())
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

# create refresh button on status bar (lower-right)
refreshSyntaxButton = Button(statusFrame, text='Refresh Syntax', command=refresh_full_syntax)
refreshSyntaxButton.pack(side=RIGHT, padx=4, pady=2)

# Bindings
for k in ['(', '[', '{', '"', "'"]:
    textArea.bind(k, auto_pair)
textArea.bind('<Return>', lambda e: (smart_newline, highlight_python_helper(e)))
textArea.bind('<KeyRelease>', lambda e: (highlight_python_helper(e), highlight_current_line(), redraw_line_numbers(), update_status_bar(), show_trailing_whitespace()))
textArea.bind('<Button-1>', lambda e: root.after_idle(lambda: (highlight_python_helper(e), highlight_current_line(), redraw_line_numbers(), update_status_bar(), show_trailing_whitespace())))
textArea.bind('<MouseWheel>', lambda e: (highlight_python_helper(e), redraw_line_numbers(), show_trailing_whitespace()))
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
    undoCheck.grid(row=5, column=1, sticky='w', pady=6)

    syntaxCheckVar = IntVar(value=config.getboolean("Section1", "syntaxHighlighting", fallback=True))
    syntaxCheck = ttk.Checkbutton(container, text="Enable syntax highlighting", variable=syntaxCheckVar)
    syntaxCheck.grid(row=5, column=1, sticky='w', pady=6)

    aiMaxContextField = mk_row("Max AI Context", 6, config.get("Section1", "aiMaxContext"))
    temperatureField = mk_row("AI Temperature", 7, config.get("Section1", "temperature"))
    top_kField = mk_row("AI top_k", 8, config.get("Section1", "top_k"))
    seedField = mk_row("AI seed", 9, config.get("Section1", "seed"))

    loadAIOnOpenVar = IntVar(value=config.getboolean("Section1", "loadAIOnOpen", fallback=False))
    loadAIOnNewVar = IntVar(value=config.getboolean("Section1", "loadAIOnNew", fallback=False))
    saveFormattingVar = IntVar(value=config.getboolean("Section1", "saveFormattingInFile", fallback=False))
    ttk.Checkbutton(container, text="Save formatting into file (hidden header)", variable=saveFormattingVar).grid(row=12, column=1, sticky='w', pady=6)
    ttk.Checkbutton(container, text="Load AI when opening a file", variable=loadAIOnOpenVar).grid(row=10, column=1, sticky='w', pady=6)
    ttk.Checkbutton(container, text="Load AI when creating a new file", variable=loadAIOnNewVar).grid(row=11, column=1, sticky='w', pady=6)

    # CSS export controls
    css_mode = config.get("Section1", "exportCssMode", fallback="inline-element")
    cssModeVar = StringVar(value=css_mode)
    ttk.Label(container, text="Export CSS mode").grid(row=13, column=0, sticky='e', padx=(0,8), pady=6)
    css_frame = ttk.Frame(container)
    css_frame.grid(row=13, column=1, sticky='w')
    ttk.Radiobutton(css_frame, text="Inline styles (per-element)", variable=cssModeVar, value='inline-element').pack(anchor='w')
    ttk.Radiobutton(css_frame, text="Inline CSS block (<style>)", variable=cssModeVar, value='inline-block').pack(anchor='w')
    ttk.Radiobutton(css_frame, text="External CSS file", variable=cssModeVar, value='external').pack(anchor='w')

    cssPathField = mk_row("External CSS path", 14, config.get("Section1", "exportCssPath", fallback=""))
    def choose_css_path():
        p = filedialog.asksaveasfilename(initialdir=os.path.expanduser("~"),
                                         title="Choose CSS file path",
                                         defaultextension='.css',
                                         filetypes=(("CSS files","*.css"),("All files","*.*")))
        if p:
            cssPathField.delete(0, END)
            cssPathField.insert(0, p)

    ttk.Button(container, text="Browse CSS path...", command=choose_css_path).grid(row=14, column=2, padx=6)

    sw_font = Label(container, width=3, relief='sunken', bg=config.get("Section1", "fontColor"))
    sw_font.grid(row=2, column=2, padx=(8,0))
    sw_bg = Label(container, width=3, relief='sunken', bg=config.get("Section1", "backgroundColor"))
    sw_bg.grid(row=3, column=2, padx=(8,0))
    sw_cursor = Label(container, width=3, relief='sunken', bg=config.get("Section1", "cursorColor"))
    sw_cursor.grid(row=4, column=2, padx=(8,0))

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

    btn_frame = ttk.Frame(container)
    btn_frame.grid(row=10, column=0, columnspan=3, pady=(8,0), sticky='ew')
    btn_frame.columnconfigure(0, weight=1)
    ttk.Button(btn_frame, text='Choose Font Color', command=choose_font_color).grid(row=0, column=0, padx=4, sticky='w')
    ttk.Button(btn_frame, text='Choose Background', command=choose_background_color).grid(row=0, column=1, padx=4, sticky='w')
    ttk.Button(btn_frame, text='Choose Cursor Color', command=choose_cursor_color).grid(row=0, column=2, padx=4, sticky='w')

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

        # persist new options
        config.set("Section1", "syntaxHighlighting", str(bool(syntaxCheckVar.get())))
        config.set("Section1", "loadAIOnOpen", str(bool(loadAIOnOpenVar.get())))
        config.set("Section1", "loadAIOnNew", str(bool(loadAIOnNewVar.get())))
        config.set("Section1", "saveFormattingInFile", str(bool(saveFormattingVar.get())))
        config.set("Section1", "exportCssMode", cssModeVar.get())
        config.set("Section1", "exportCssPath", cssPathField.get())

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

        try:
            syntaxCheckVar.set(config.getboolean("Section1", "syntaxHighlighting", fallback=True))
            loadAIOnOpenVar.set(config.getboolean("Section1", "loadAIOnOpen", fallback=False))
            loadAIOnNewVar.set(config.getboolean("Section1", "loadAIOnNew", fallback=False))
            saveFormattingVar.set(config.getboolean("Section1", "saveFormattingInFile", fallback=False))
            cssModeVar.set(config.get("Section1", "exportCssMode", fallback="inline-element"))
            cssPathField.delete(0, END)
            cssPathField.insert(0, config.get("Section1", "exportCssPath", fallback=""))
        except Exception:
            pass

        try:
            sw_font.config(bg=config.get("Section1", "fontColor"))
            sw_bg.config(bg=config.get("Section1", "backgroundColor"))
            sw_cursor.config(bg=config.get("Section1", "cursorColor"))
        except Exception:
            pass

    ttk.Button(action_frame, text="Save", command=on_closing).grid(row=0, column=1, padx=6)
    ttk.Button(action_frame, text="Refresh from file", command=refresh_from_file).grid(row=0, column=2, padx=6)
    ttk.Button(action_frame, text="Close", command=top.destroy).grid(row=0, column=3, padx=6)

    fontNameField.focus_set()
    center_window(top)
    refresh_from_file()


def nonlocal_values_reload():
    global fontName, fontSize, fontColor, backgroundColor, undoSetting, cursorColor, aiMaxContext, temperature, top_k, seed, exportCssMode, exportCssPath
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

    # load css export settings
    exportCssMode = config.get("Section1", "exportCssMode", fallback="inline-element")
    exportCssPath = config.get("Section1", "exportCssPath", fallback="")

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
    textArea.delete('1.0', 'end')
    statusBar['text'] = "New Document!"
    try:
        if _ML_AVAILABLE and loadAIOnNew and not _model_loaded and not _model_loading:
            Thread(target=lambda: _start_model_load(start_autocomplete=False), daemon=True).start()
    except Exception:
        pass
    Thread(target=ready_update, daemon=True).start()

# populate recent menu
try:
    refresh_recent_menu()
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