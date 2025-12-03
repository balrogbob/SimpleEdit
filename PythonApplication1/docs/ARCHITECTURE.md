# 🏗️ Architecture Guide

High-level overview of SimpleEdit's system design, data flow, and module relationships.

---

## Table of Contents

- [System Overview](#system-overview)
- [Module Dependency Graph](#module-dependency-graph)
- [Threading Model](#threading-model)
- [Data Flow Diagrams](#data-flow-diagrams)
- [Key Components](#key-components)
- [Configuration System](#configuration-system)
- [File I/O Pipeline](#file-io-pipeline)

---

## System Overview

SimpleEdit is a **Tkinter-based Python code editor** with HTML/Markdown rendering and experimental JavaScript execution.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│         SimpleEdit GUI (Tkinter)                    │
├─────────────────────────────────────────────────────┤
│  - Main Window (PythonApplication1.py)              │
│  - Editor Tabs (Text widgets)                       │
│  - Syntax Highlighting (background thread)         │
│  - Find/Replace, Settings dialogs                   │
├─────────────────────────────────────────────────────┤
│         Business Logic (functions.py)               │
│  - HTML/Markdown parsing                           │
│  - File I/O                                        │
│  - Script extraction & execution                   │
├─────────────────────────────────────────────────────┤
│      Runtime Engines                                │
│  - jsmini (JavaScript interpreter)                 │
│  - js_builtins (Array, Object, JSON, etc.)        │
│  - HTML Parser (_SimpleHTMLToTagged)               │
├─────────────────────────────────────────────────────┤
│         Persistent Storage                          │
│  - config.ini (user preferences)                   │
│  - Syntax definitions (*.ini files)                │
└─────────────────────────────────────────────────────┘
```

---

## Module Dependency Graph

### File Structure

```
PythonApplication1/
│
├── PythonApplication1.py          [GUI Main]
│   ├── imports: functions
│   ├── imports: jsmini
│   ├── imports: js_builtins
│   ├── imports: syntax_worker
│   └── creates: Tkinter UI
│
├── functions.py                   [Business Logic]
│   ├── HTML parsing (_SimpleHTMLToTagged)
│   ├── Script execution (run_scripts)
│   ├── File I/O utilities
│   └── uses: jsmini, js_builtins
│
├── jsmini.py                      [JS Interpreter]
│   ├── Tokenizer
│   ├── Parser (builds AST)
│   ├── Interpreter (executes AST)
│   ├── DOM shim
│   └── uses: js_builtins
│
├── js_builtins.py                 [JS Built-ins]
│   ├── Array methods
│   ├── Object methods
│   ├── JSON support
│   ├── Event system
│   └── uses: jsmini (JSFunction)
│
├── syntax_worker.py               [Background Tasks]
│   ├── Background syntax highlighting
│   ├── Tokenization
│   └── uses: jsmini, functions
│
├── model.py                       [Optional: ML Model]
│   ├── GPT-2 model loading
│   └── requires: torch, tiktoken
│
└── tests/
    ├── test_base.py               [Core parsing]
    ├── test_js_builtins.py        [JS APIs]
    ├── test_dom_events.py         [DOM/events]
    └── ... (10+ test files)
```

### Dependency Direction

```
GUI (PythonApplication1.py)
  ↓
Business Logic (functions.py)
  ↓
Engines (jsmini, js_builtins)
  ↓
Utilities (config, syntax)
```

**Key Rule:** Lower layers should never import from upper layers (no circular deps)

---

## Threading Model

SimpleEdit uses **multiple threads** to keep the UI responsive:

### Thread Roles

```
┌──────────────────────┐
│   Main Thread        │
│  (Tkinter GUI)       │
│  - Event handling    │
│  - UI rendering      │
│  - User interaction  │
└──────────────────────┘
         ↑ (data updates)
         │
┌──────────────────────┐
│ Syntax Worker Thread │
│ (background)         │
│  - Tokenization      │
│  - Tag application   │
│  - Large file parse  │
└──────────────────────┘

┌──────────────────────┐
│ Script Runner Thread │
│ (background/daemon)  │
│  - JS execution      │
│  - DOM operations    │
│  - Long operations   │
└──────────────────────┘

┌──────────────────────┐
│   Model Load Thread  │
│ (background/daemon)  │
│  - AI model loading  │
│  - First-time init   │
└──────────────────────┘
```

### Thread Safety

**Critical:** UI updates must run on **main thread** via `root.after()`:

```python
# ✅ Correct - schedules on main thread
root.after(0, lambda: textArea.insert('1.0', text))

# ❌ Wrong - direct call from worker thread
textArea.insert('1.0', text)  # May crash or corrupt UI
```

### Synchronization

- **Threading locks** used for config access
- **Queues** for worker→UI communication
- **Event variables** for state coordination

---

## Data Flow Diagrams

### Opening a File

```
User clicks "Open"
    ↓
File dialog opens (blocking)
    ↓
User selects file
    ↓
_open_path(filename)
    ├─ Read file from disk
    ├─ Detect file type (HTML? Python? etc.)
    ├─ If HTML: Parse & extract plain text + metadata
    ├─ Create tab in editor
    ├─ Insert text into Text widget
    ├─ Schedule syntax highlighting (background thread)
    └─ Update UI (status bar, recent files)
```

### Saving a File

```
User presses Ctrl+S
    ↓
save_file()
    ├─ If no filename: ask user (Save As dialog)
    ├─ Get current text from editor
    ├─ Write to disk
    ├─ Update window title
    ├─ Add to recent files
    └─ Status bar: "Saved"
```

### JavaScript Execution

```
User opens HTML file with <script>
    ↓
_open_path() detects .html
    ├─ Parse HTML
    ├─ Extract <script> tags (extract_script_tags)
    ├─ Create jsmini context
    └─ Schedule script execution (background thread)
    ↓
run_scripts() [background thread]
    ├─ For each script:
    │  ├─ Create Interpreter
    │  ├─ Register built-ins
    │  ├─ Execute script
    │  └─ Collect results/errors
    ├─ Optional: Call host callback (setRaw)
    └─ Return results to main thread
    ↓
Main thread updates display
    └─ Show rendered output or errors
```

### Syntax Highlighting

```
User types in editor
    ↓
Text widget detects change
    ↓
Throttled callback triggers (every 500ms typically)
    ↓
syntax_worker.highlightPythonInit() [background thread]
    ├─ Tokenize current text
    ├─ Identify keyword/string/comment regions
    ├─ Build tag ranges
    └─ Schedule tag application (main thread)
    ↓
Main thread applies tags
    └─ Text widget re-renders with colors
```

---

## Key Components

### 1. Text Editor (PythonApplication1.py)

**Role:** UI layer, event handling, user interaction

**Key Classes/Functions:**
- `Tk()` - Main window
- `Text` - Editor text area
- `Notebook` - Tab container
- Various menu handlers (open, save, find, etc.)

**Responsibilities:**
- Render UI elements
- Capture user input
- Update status bar
- Manage recent files menu
- Handle keyboard shortcuts

---

### 2. HTML/Markdown Parser (functions.py)

**Role:** Convert HTML/Markdown to plain text with metadata

**Key Class:**
- `_SimpleHTMLToTagged(HTMLParser)` - Parses HTML fragments

**Responsibilities:**
- Strip HTML tags, preserve structure
- Extract links and tables
- Detect code blocks with language hints
- Apply syntax highlighting to code blocks
- Return `(plain_text, metadata)` tuple

**Metadata Includes:**
- Tag ranges (bold, italic, links)
- Links with URLs and titles
- Table structure with cell data
- Code block language

---

### 3. JavaScript Interpreter (jsmini.py)

**Role:** Parse and execute JavaScript

**Key Components:**
- **Tokenizer:** Breaks source into token stream
- **Parser:** Builds Abstract Syntax Tree (AST)
- **Interpreter:** Executes AST nodes
- **DOM Shim:** Minimal DOM API

**Responsibilities:**
- Tokenize JS source code
- Parse into AST
- Execute with proper scoping
- Handle control flow (if, loops, break, continue)
- Throw errors with context

---

### 4. Built-ins (js_builtins.py)

**Role:** Provide JavaScript standard library

**Includes:**
- Array methods (push, pop, map, filter, reduce, etc.)
- Object methods (keys, assign, create)
- JSON (parse, stringify)
- Math functions
- Event system
- localStorage
- Callbacks & timers

**Pattern:** Each built-in is a `JSFunction` with native Python implementation

---

### 5. Configuration (functions.py / config.ini)

**Role:** Persist user preferences

**Storage:** `config.ini` (ini file format)

**Sections:**
- `[Section1]` - Font, colors, highlighting settings
- `[Recent]` - Recently opened files (JSON list)
- `[URLHistory]` - Visited URLs (JSON list)
- `[Syntax]` - Custom color overrides

**Loading:**
```python
config = configparser.ConfigParser()
config.read('config.ini')
fontName = config.get('Section1', 'fontName')
```

---

## Configuration System

### config.ini Structure

```ini
[Section1]
fontName=consolas
fontSize=12
fontColor=#4AF626
backgroundColor=black
syntaxHighlighting=True
aiMaxContext=512
temperature=1.1
top_k=300
loadAIOnOpen=False

[Recent]
files=["file1.py", "file2.html", ...]

[URLHistory]
urls=["http://...", ...]

[Syntax]
tag.keyword.fg=#FF0000
tag.keyword.bg=
```

### Defaults

If config.ini missing, created with `DEFAULT_CONFIG` from functions.py

### Per-Tab State

Tab-specific data stored as attributes on frame objects:
- `frame.fileName` - Current file path
- `frame._raw_html` - Original HTML
- `frame._view_raw` - Viewing mode (raw vs. rendered)

---

## File I/O Pipeline

### Reading a File

```python
with open(path, 'r', encoding='utf-8') as fh:
    raw = fh.read()

if is_html_like(path):
    plain, metadata = _parse_html_and_apply(raw)
else:
    plain = raw
    metadata = None

# Display in editor
textArea.insert('1.0', plain)

# Apply formatting (if metadata available)
if metadata and metadata.get('tags'):
    _apply_formatting_from_meta(metadata)
```

### Writing a File

```python
content = textArea.get('1.0', 'end-1c')  # Get all text

with open(path, 'w', encoding='utf-8') as fh:
    fh.write(content)

# Update recent files
add_recent_file(config, 'config.ini', path)

# Update window title
root.title(f'SimpleEdit - {filename}')
```

### Error Handling

All file I/O wrapped in try-except:

```python
try:
    # Read/write operations
except IOError as e:
    messagebox.showerror("Error", f"File error: {e}")
except Exception as e:
    messagebox.showerror("Error", f"Unexpected error: {e}")
```

---

## Extension Points

### Adding a New Language (Syntax Highlighting)

1. **Add tokenizer** in `functions.py`:
   ```python
   def _cb_mylang(self, text: str, base: int):
       # Regex patterns for keywords, strings, etc.
       # Apply tags using self._cb_add()
   ```

2. **Register in parser**:
   ```python
   elif lang == 'mylang':
       self._cb_mylang(text, base_off)
   ```

3. **Add to heuristic guesser**:
   ```python
   if 'pattern_for_mylang' in text:
       return 'mylang'
   ```

### Adding a Built-in Function

1. **Implement as native function**:
   ```python
   def _my_builtin(interp, this, args):
       # implementation
       return result
   ```

2. **Register in context**:
   ```python
   context['myBuiltin'] = JSFunction([], None, None, 'myBuiltin', native_impl=_my_builtin)
   ```

---

## Performance Considerations

### Bottlenecks

1. **Syntax highlighting** on large files (>50KB)
   - Solution: Background thread, disable for huge files

2. **HTML parsing** of complex documents
   - Solution: Streaming parse, lazy tag application

3. **JavaScript execution** (infinite loops, deep recursion)
   - Solution: Execution limits, recursion guards

### Optimizations

- **Lazy tag application:** Only highlight visible portions
- **Background threads:** Keep UI responsive during heavy ops
- **Caching:** Parse results cached when possible
- **Incremental highlighting:** Only re-highlight changed lines

---

## See Also

- [API Reference](API.md) - All available functions
- [Internal API Reference](INTERNAL-API.md) - Internal functions (contributors)
- [CONTRIBUTING.md](../CONTRIBUTING.md) - How to contribute
- [development-process.md](development-process.md) - Design history
- [JSMINI.md](JSMINI.md) - JavaScript engine internals
- [PERFORMANCE-TUNING.md](PERFORMANCE-TUNING.md) - Optimization tips
