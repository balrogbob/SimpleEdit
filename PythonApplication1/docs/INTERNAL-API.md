# 📚 SimpleEdit Internal API Reference

**Internal Functions, Helper Utilities, and Private APIs**

**Status:** Complete internal API documentation  
**Last Updated:** January 12, 2025  
**For:** SimpleEdit Contributors and Advanced Users

---

## Table of Contents

- [Overview](#overview)
- [functions.py Internal API](#functionspy-internal-api)
- [syntax_worker.py Internal API](#syntax_workerpy-internal-api)
- [model.py Internal API](#modelpy-internal-api)
- [Private Attributes & Context](#private-attributes--context)
- [Thread Safety Patterns](#thread-safety-patterns)
- [Best Practices](#best-practices)
- [Examples](#examples)

---

## Overview

This document describes **internal, non-public APIs** of SimpleEdit. These functions and classes are subject to change without notice. Use them only when:

- Contributing to SimpleEdit core
- Extending functionality beyond public APIs
- Building custom features that require deep system access
- Debugging or profiling

For public APIs, see [API.md](API.md).

---

## functions.py Internal API

The `functions.py` module contains core business logic for HTML parsing, script management, file I/O, and configuration handling.

### HTML Parser: _SimpleHTMLToTagged

**Module:** `functions.py`

**Type:** `HTMLParser` subclass

**Purpose:** Parse HTML fragments and extract plain text with tag ranges, links, and table metadata.

#### Constructor

```python
parser = _SimpleHTMLToTagged()
```

#### Main Methods

##### feed(html_string: str)

**Signature:** `None`

**Purpose:** Parse HTML content and populate internal structures.

**Example:**
```python
from functions import _SimpleHTMLToTagged

parser = _SimpleHTMLToTagged()
parser.feed("<p>Hello <b>world</b></p>")
plain_text, metadata = parser.get_result()
print(plain_text)  # "Hello world"
print(metadata['tags']['bold'])  # [[6, 11]]
```

##### get_result() → tuple[str, dict]

**Returns:** `(plain_text: str, metadata: dict)`

**Metadata Structure:**
```python
{
    'tags': {
        'bold': [[start, end], ...],
        'italic': [[start, end], ...],
        'hyperlink': [[start, end], ...],
        'code_block': [[start, end], ...],
        # ... other tags
    },
    'links': [
        {'start': int, 'end': int, 'href': str, 'title': str|None},
        ...
    ],
    'tables': [
        {
            'start': int,
            'end': int,
            'attrs': dict,
            'rows': [
                [
                    {'start': int, 'end': int, 'text': str, 'type': 'td'|'th', 'attrs': dict},
                    ...
                ],
                ...
            ],
            'colgroup': [{'width': int}, ...]
        },
        ...
    ],
    'raw_fragment': str,     # original HTML
    'prochtml': str          # processed HTML (whitespace-normalized)
}
```

#### Private Methods (Internal Use Only)

**`handle_starttag(tag, attrs)`** - Process opening tags (called by HTMLParser)

**`handle_endtag(tag)`** - Process closing tags (called by HTMLParser)

**`handle_data(data)`** - Process text content (called by HTMLParser)

**`_cb_python(text, base)`** - Apply Python syntax highlighting to code blocks

**`_cb_javascript(text, base)`** - Apply JavaScript syntax highlighting

**`_cb_json(text, base)`** - Apply JSON syntax highlighting

**Example: Custom Syntax Extension**
```python
# To add Ruby syntax highlighting:
parser = _SimpleHTMLToTagged()
parser.feed("<pre><code>def hello; puts 'world'; end</code></pre>")
# Internally calls _cb_python (detected by heuristic)
plain_text, meta = parser.get_result()
```

---

### HTML Processing: _parse_html_and_apply

**Signature:** `(raw: str) → tuple[str, dict]`

**Purpose:** High-level HTML parsing with robustness against formatting.

**Features:**
- Removes inter-tag whitespace (layout normalization)
- Detects and normalizes anchors
- Preserves code/script/style blocks
- Remaps anchor text to link ranges

**Returns:** `(plain_text, metadata)`

**Example:**
```python
html = """
<div>
  <p>Check out <a href="https://example.com">example</a></p>
  <pre><code>print("hello")</code></pre>
</div>
"""

plain_text, meta = _parse_html_and_apply(html)
# plain_text will have proper spacing
# meta['links'] contains anchor references
# meta['tags']['code_block'] marks code regions
```

---

### Color Utilities

#### _hex_to_rgb(h: str) → tuple[int, int, int]

**Purpose:** Convert hex color to RGB tuple.

**Example:**
```python
from functions import _hex_to_rgb
r, g, b = _hex_to_rgb("#FF5733")
print(r, g, b)  # 255, 87, 51
```

**Handles:**
- 6-digit hex: `#RRGGBB`
- 3-digit hex: `#RGB` (expands to 6)
- With or without `#` prefix
- Invalid input returns `(0, 0, 0)`

#### _rgb_to_hex(r: int, g: int, b: int) → str

**Purpose:** Convert RGB to hex string.

**Example:**
```python
from functions import _rgb_to_hex
hex_color = _rgb_to_hex(255, 87, 51)
print(hex_color)  # "#ff5733"
```

#### _lighten_color(hexcol: str, factor: float = 0.15) → str

**Purpose:** Create lighter version of color.

**Parameters:**
- `hexcol` - Color hex code
- `factor` - Lightness increase (0.0 to 1.0), default 0.15

**Example:**
```python
from functions import _lighten_color
lighter = _lighten_color("#333333", 0.3)
# Result: lighter shade toward white
```

#### _contrast_text_color(hexcolor: str) → str

**Purpose:** Choose black or white text color for readability over background.

**Returns:** `"#000000"` or `"#FFFFFF"`

**Example:**
```python
from functions import _contrast_text_color
# For light backgrounds
text_color = _contrast_text_color("#EEEEEE")  # "#000000"
# For dark backgrounds
text_color = _contrast_text_color("#1a1a1a")  # "#FFFFFF"
```

---

### Script Management

#### extract_script_tags(html: str) → list[dict]

**Purpose:** Find all `<script>` tags in HTML.

**Returns:** List of script entries:
```python
[
    {
        'src': 'https://example.com/script.js' | None,
        'inline': '<script code>' | None,
        'attrs': {'type': 'text/javascript', ...}
    },
    ...
]
```

**Example:**
```python
from functions import extract_script_tags

html = """
<html>
<head>
  <script src="lib.js"></script>
</head>
<body>
  <script>
    console.log('inline');
  </script>
</body>
</html>
"""

scripts = extract_script_tags(html)
# scripts[0] = {'src': 'lib.js', 'inline': None, 'attrs': {...}}
# scripts[1] = {'src': None, 'inline': "console.log('inline');", 'attrs': {...}}
```

#### run_scripts(scripts, base_url=None, ...) → list[dict] | dict

**Purpose:** Execute scripts using jsmini with DOM capture.

**Parameters:**
- `scripts` - List of script entries
- `base_url` - Base URL for relative script paths
- `log_fn` - Function to call with log messages
- `host_update_cb` - Callback when DOM changes
- `return_dom` - If True, return dict with DOM snapshots
- `run_blocking` - Execute synchronously (default: async)
- `force_final_redraw` - Flush final DOM changes

**Returns (Legacy):** `list[dict]` with `{'ok': bool, 'error': str|None}`

**Returns (Extended):** `dict` with:
```python
{
    'results': [...],
    'final_dom': '<div id="demo">...</div>',
    'per_script_dom': ['<div>...</div>', ...],  # if collect_dom_each=True
    'dom_changes': [...]  # if collect_dom_changes=True
}
```

**Example:**
```python
from functions import extract_script_tags, run_scripts

scripts = extract_script_tags(html)
results = run_scripts(
    scripts,
    base_url='https://example.com',
    return_dom=True,
    force_final_redraw=True
)

if results['results'][0]['ok']:
    print("Script executed successfully")
    print("Final DOM:", results['final_dom'])
```

#### _should_execute_script(attrs: dict | None) → bool

**Purpose:** Determine if a `<script>` with given attributes should run as JavaScript.

**Rules:**
- No type/language attribute → execute
- `type` contains "javascript" or "ecmascript" → execute
- `language` is "javascript" or "js" → execute
- `type` is "module" or contains "json" → skip

**Example:**
```python
from functions import _should_execute_script

# Execute as JavaScript
_should_execute_script({'type': 'text/javascript'})  # True
_should_execute_script({})  # True

# Skip (not JavaScript)
_should_execute_script({'type': 'application/json'})  # False
_should_execute_script({'type': 'module'})  # False
```

#### _load_script_text(entry: dict, base_url: str | None) → tuple[str | None, str | None]

**Purpose:** Load script content from various sources.

**Supports:**
- Inline scripts (`entry['inline']`)
- HTTP/HTTPS URLs
- `file://` URLs
- `data:` URLs (base64 and URL-encoded)
- Filesystem paths (relative to base_url)

**Returns:** `(script_text, error_message)` or `(None, error_message)` on failure

**Example:**
```python
from functions import _load_script_text

entry = {
    'src': 'https://cdn.example.com/lib.js',
    'inline': None,
    'attrs': {}
}

script_text, error = _load_script_text(entry, 'https://example.com/')
if error:
    print(f"Failed to load: {error}")
else:
    print(f"Loaded {len(script_text)} bytes")
```

---

### Configuration Management

#### get_js_console_default() → bool

**Purpose:** Get persisted JS console visibility preference.

**Returns:** `True` if JS Console should auto-open by default

#### set_js_console_default(value: bool) → None

**Purpose:** Persist JS Console visibility preference.

**Example:**
```python
from functions import get_js_console_default, set_js_console_default

# Check current preference
if get_js_console_default():
    print("JS Console will auto-open")

# Change preference
set_js_console_default(True)
```

#### get_debug_default() → bool

**Purpose:** Get debug logging preference.

#### set_debug_default(value: bool) → None

**Purpose:** Persist debug logging preference.

---

### Recent Files Management

#### load_recent_files(config) → list[str]

**Purpose:** Load list of recently opened files from config.

**Returns:** List of absolute file paths (most recent first)

#### save_recent_files(config, ini_path: str, lst: list[str]) → None

**Purpose:** Persist recent files list to config.ini.

#### add_recent_file(config, ini_path: str, path: str, on_update=None, max_items=None) → None

**Purpose:** Add file to MRU list, deduplicating and truncating.

**Parameters:**
- `path` - File path to add
- `on_update` - Optional callback after save
- `max_items` - Max items to keep (default: 10)

**Example:**
```python
from functions import add_recent_file
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

def on_update():
    print("Recent files updated")

add_recent_file(config, 'config.ini', '/path/to/file.py', on_update=on_update)
```

#### clear_recent_files(config, ini_path: str, on_update=None) → None

**Purpose:** Clear all recent files.

---

### JavaScript Console Window

#### _ensure_js_console() → tuple[Toplevel, Text] | tuple[None, None]

**Purpose:** Create or reuse the JS Console window.

**Returns:** `(window, text_widget)` or `(None, None)` on failure

**Thread Safety:** Safe to call from any thread; creates window on main thread if necessary.

#### _console_append(msg: str) → None

**Purpose:** Append message to JS Console (thread-safe).

**Thread Safety:** Safe to call from worker threads via `root.after()`.

#### _bring_console_to_front() → None

**Purpose:** Raise console window to top briefly for visibility.

---

### Internal Helpers

#### _strip_leading_license_comment(src: str) → str

**Purpose:** Remove leading `/*! ... */` license headers from minified JavaScript.

**Example:**
```python
src = """/*! Copyright 2024 */
function hello() { ... }"""

cleaned = _strip_leading_license_comment(src)
# Returns: "function hello() { ... }"
```

#### _format_js_error_context(script_src: str, exc: Exception, tb: str | None, context_lines: int = 2) → str

**Purpose:** Extract error context from script and traceback.

**Returns:** Snippet of source code with error location marked (if detectable)

**Example:**
```python
try:
    jsmini.run("x = y + z", ctx)
except Exception as e:
    context = _format_js_error_context(script_src, e, None)
    print(context)  # "  3:    x = y + z" with line number
```

---

## syntax_worker.py Internal API

The `syntax_worker.py` module manages background syntax highlighting via subprocess workers.

### Process Slice

#### process_slice(content: str, s_start: int, s_end: int, protected_spans: list[tuple[int, int]], keywords: list[str], builtins: list[str]) → dict[str, list[tuple[int, int]]]

**Purpose:** Scan substring and identify syntax elements (keywords, strings, numbers, etc.).

**Parameters:**
- `content` - Full source text
- `s_start`, `s_end` - Substring boundaries (absolute offsets)
- `protected_spans` - Ranges to skip (strings, comments)
- `keywords` - List of keyword strings
- `builtins` - List of builtin strings

**Returns:** Dict mapping tag name to list of `(start, end)` tuples:
```python
{
    'number': [(12, 14), (25, 27)],
    'keyword': [(0, 2), (3, 7)],
    'string': [(15, 20)],
    'comment': [(32, 50)],
    'decorator': [...],
    'class_name': [...],
    # ... other tags
}
```

**Example:**
```python
from syntax_worker import process_slice

code = "def hello(x):\n  return x + 1  # comment"
result = process_slice(
    content=code,
    s_start=0,
    s_end=len(code),
    protected_spans=[],
    keywords=['def', 'return'],
    builtins=[]
)

print(result['keyword'])   # [(0, 3), (13, 19)]  - "def" and "return"
print(result['number'])    # [(27, 28)]  - "1"
print(result['comment'])   # [(30, 40)]  - "# comment"
```

---

### Server Management

#### start_servers(count: int) → None

**Purpose:** Spawn `count` worker subprocess servers for syntax highlighting.

**Design:** Each worker listens on a TCP port and waits for JSON-line requests.

**Thread Safety:** Safe to call once at startup; called automatically by main app.

#### stop_servers() → None

**Purpose:** Shutdown all worker servers gracefully.

#### map_slices(content: str, ranges: list[tuple[int, int]], protected_spans: list, keywords: list, builtins: list, processes: int = 1) → list[dict]

**Purpose:** Distribute syntax highlighting work across worker servers.

**Parameters:**
- `content` - Source code
- `ranges` - List of `(start, end)` offsets to highlight
- `protected_spans` - Ranges already marked (strings, comments)
- `keywords`, `builtins` - Python identifiers
- `processes` - Number of workers to use

**Returns:** List of result dicts (one per range):
```python
[
    {'number': [...], 'keyword': [...], ...},  # for ranges[0]
    {'number': [...], 'keyword': [...], ...},  # for ranges[1]
    ...
]
```

**Load Balancing:** If a single full-file range exists and multiple workers available, automatically splits it into overlapping chunks for distribution.

**Fallback:** Any ranges not processed by workers are processed locally.

**Example:**
```python
from syntax_worker import start_servers, map_slices

# Start 4 worker servers
start_servers(4)

code = "x = 1 + 2\ny = 'hello'"
ranges = [(0, 9), (10, 21)]  # two lines

results = map_slices(
    content=code,
    ranges=ranges,
    protected_spans=[],
    keywords=['if', 'def', 'return'],
    builtins=['print', 'len'],
    processes=4
)

for i, result in enumerate(results):
    print(f"Range {i}: numbers={result['number']}")
```

#### get_all_worker_stderr_tail() → list[str]

**Purpose:** Get recent stderr lines from all workers for debugging.

**Returns:** List of tail lines (most recent per worker)

#### get_worker_stderr_path(index: int) → str

**Purpose:** Get filesystem path to worker's stderr log.

---

## model.py Internal API

The `model.py` module provides optional GPT-2 text generation.

### Model Loading

#### load_model(model_name: str = "gpt2", device: str = "cpu") → object | None

**Purpose:** Load pre-trained language model.

**Parameters:**
- `model_name` - Model identifier (default: "gpt2")
- `device` - "cpu" or "cuda" (if available)

**Returns:** Model object or None on failure

**Memory:** ~500MB for GPT-2

**First Load:** ~30 seconds

#### unload_model() → None

**Purpose:** Unload model from memory to free resources.

---

### Inference

#### generate(prompt: str, max_tokens: int = 50, temperature: float = 1.0, top_k: int = 50) → str | None

**Purpose:** Generate text continuation from prompt.

**Parameters:**
- `prompt` - Starting text
- `max_tokens` - Max output tokens
- `temperature` - Randomness (0=deterministic, 2=very random)
- `top_k` - Vocabulary restriction (top K most likely tokens)

**Returns:** Generated text or None on error

**Example:**
```python
from model import load_model, generate

model = load_model("gpt2")
if model:
    output = generate("The sky is", max_tokens=20, temperature=0.8)
    print(output)  # "The sky is blue and beautiful..."
```

---

## Private Attributes & Context

### Frame Attributes

When opening files, the text widget's parent frame stores metadata:

```python
# Access via frame object:
frame.fileName       # str: current file path
frame._raw_html      # str: original HTML (if file was HTML)
frame._view_raw      # bool: viewing mode (True=raw HTML, False=rendered)
frame._tables_meta   # list: table metadata for exports
```

### JavaScript Context

Passed to jsmini interpreter:

```python
ctx = {
    'console': {'log': fn, 'error': fn},
    'document': {...},           # DOM object
    'window': {...},             # Window object
    'Math': {...},               # Math object
    'Array': constructor,        # Array constructor
    'Object': constructor,       # Object constructor
    'JSON': {'parse': fn, 'stringify': fn},
    'localStorage': {...},       # Key-value store
    'setTimeout': fn,            # Timer function
    'host': {                    # Host bridge (if provided)
        'setRaw': callback,
        'forceRerender': lambda: ...
    },
    '_timers': [],               # Internal timer queue
    '_dom_changes': [],          # Internal DOM mutation log
}
```

---

## Thread Safety Patterns

### Safe Configuration Access

```python
# From any thread:
value = config.get('Section1', 'key')  # thread-safe read

# To write (use functions):
from functions import set_js_console_default
set_js_console_default(True)  # handles file I/O safely
```

### Safe Console Output

```python
# From worker thread:
from functions import _console_append

_console_append("Message from worker")  # thread-safe
# Internally uses root.after() to schedule on main thread
```

### Safe DOM Updates

```python
# From jsmini context:
ctx['host']['setRaw'](html_string)  # calls user's host_update_cb
# Callback receives HTML snapshot, can update UI
```

---

## Best Practices

### 1. Error Handling

Always catch exceptions when working with internal APIs:

```python
try:
    parser = _SimpleHTMLToTagged()
    parser.feed(html_string)
    plain_text, meta = parser.get_result()
except Exception as e:
    print(f"Parse failed: {e}")
    # Fall back to raw text
    plain_text = html_string
    meta = {'tags': {}}
```

### 2. Memory Management

Be careful with large HTML/JavaScript:

```python
# Bad: holds entire DOM in memory indefinitely
for file in all_files:
    html = open(file).read()
    parser = _SimpleHTMLToTagged()
    parser.feed(html)
    # parser never garbage collected!

# Good: scope parser to local block
for file in all_files:
    html = open(file).read()
    parser = _SimpleHTMLToTagged()
    parser.feed(html)
    result = parser.get_result()
    del parser  # or let it go out of scope
```

### 3. Use Public APIs When Possible

```python
# Prefer:
from jsmini import run_with_interpreter
run_with_interpreter(code, context)

# Over:
from functions import run_scripts
# (which is for full script entries with DOM)
```

### 4. Thread Safety

```python
# When calling from worker thread:
# ✅ Use internal callback mechanisms
from functions import _console_append
_console_append("msg")  # safe

# ❌ Don't touch Tkinter directly
# textArea.insert(...)  # NOT SAFE from worker!

# ✅ Instead, schedule on main thread
root.after(0, lambda: textArea.insert('end', 'msg'))
```

### 5. Context Preservation

When working with jsmini context:

```python
ctx = jsmini.make_context()

# ✅ Preserve context for multiple scripts
script1_result = jsmini.run(script1, ctx)
script2_result = jsmini.run(script2, ctx)  # script2 sees script1's globals

# ❌ Don't create new context for each script
ctx1 = jsmini.make_context()
jsmini.run(script1, ctx1)
ctx2 = jsmini.make_context()  # Lost script1 globals!
jsmini.run(script2, ctx2)
```

---

## Examples

### Example 1: Extract and Highlight Code Blocks

```python
from functions import _parse_html_and_apply
from syntax_worker import process_slice

html = """
<div>
<pre><code class="python">
def hello():
    print("world")
</code></pre>
</div>
"""

plain_text, meta = _parse_html_and_apply(html)

# Find code blocks in metadata
for s, e in meta['tags'].get('code_block', []):
    code = plain_text[s:e]
    
    # Highlight the code
    results = process_slice(
        content=code,
        s_start=0,
        s_end=len(code),
        protected_spans=[],
        keywords=['def', 'print', 'return'],
        builtins=['print']
    )
    
    print(f"Keywords: {results['keyword']}")
    print(f"Numbers: {results['number']}")
```

### Example 2: Programmatic Script Execution with DOM Capture

```python
from functions import extract_script_tags, run_scripts

html = """
<html>
<body id="app"></body>
<script>
document.getElementById('app').innerHTML = '<h1>Hello</h1>';
</script>
</html>
"""

scripts = extract_script_tags(html)

results = run_scripts(
    scripts,
    base_url='https://example.com/',
    return_dom=True,
    force_final_redraw=True,
    run_blocking=True
)

if results['results'][0]['ok']:
    final_html = results['final_dom']
    print(f"Result: {final_html}")
else:
    print(f"Error: {results['results'][0]['error']}")
```

### Example 3: Extending Syntax Highlighting

```python
from syntax_worker import process_slice

# Add custom language support
def highlight_custom_lang(content, language):
    """Highlight custom domain-specific language."""
    
    # Define your patterns
    keywords = ['BEGIN', 'END', 'DATA', 'PROCESS']
    builtins = ['print', 'read', 'write']
    
    results = process_slice(
        content=content,
        s_start=0,
        s_end=len(content),
        protected_spans=[],
        keywords=keywords,
        builtins=builtins
    )
    
    return results

# Usage
code = "BEGIN\n  DATA x\n  PROCESS x\nEND"
highlights = highlight_custom_lang(code, 'mycustom')
print(highlights)
```

---

## See Also

- [API.md](API.md) - Public API reference
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design and threading model
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- [JSMINI.md](JSMINI.md) - JavaScript interpreter details

---

**Internal API Documentation for SimpleEdit**

*Complete reference to internal functions, helper utilities, and private APIs used by SimpleEdit contributors and advanced users.*
