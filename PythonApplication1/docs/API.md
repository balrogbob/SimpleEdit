# 📖 SimpleEdit API Documentation

## Overview

SimpleEdit provides a comprehensive Python API for programmatic interaction with the editor, file management, HTML/Markdown parsing, and JavaScript execution. This document covers the main modules and their public functions.

---

## Table of Contents

- [Core Modules](#core-modules)
- [functions.py API](#functionspy-api)
- [jsmini.py API](#jsminpy-api)
- [js_builtins.py API](#js_builtinspy-api)
- [Configuration](#configuration)
- [Examples](#examples)

---

## Core Modules

### Module Structure

```
PythonApplication1/
├── PythonApplication1.py      # Main GUI application (Tkinter)
├── functions.py               # Helper functions (HTML, scripts, file management)
├── jsmini.py                  # JavaScript interpreter and DOM shim
├── js_builtins.js             # JavaScript built-in functions (Array, Object, etc.)
├── model.py                   # GPT model (optional, ML-dependent)
└── syntax_worker.py           # Background syntax highlighting
```

---

## functions.py API

### Recent Files Management

#### `load_recent_files(config: ConfigParser) -> List[str]`

Load the list of recently opened files from persistent storage.

**Parameters:**
- `config`: `ConfigParser` instance (typically `config` from `config.ini`)

**Returns:** List of absolute file paths (most-recent-first)

**Example:**
```python
from functions import load_recent_files
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
recent = load_recent_files(config)
print(f"Recent files: {recent}")
```

---

#### `add_recent_file(config, ini_path, path, on_update=None, max_items=10)`

Add a file to the MRU list and persist to config.

**Parameters:**
- `config`: `ConfigParser` instance
- `ini_path`: Path to `config.ini` file
- `path`: Absolute path to file to add
- `on_update`: Optional callback function invoked after save
- `max_items`: Maximum number of items to retain (default: 10)

**Returns:** None (void)

**Example:**
```python
from functions import add_recent_file

add_recent_file(config, 'config.ini', '/path/to/file.py', 
                on_update=lambda: print("Recent files updated"))
```

---

#### `clear_recent_files(config, ini_path, on_update=None)`

Clear the entire recent files list.

**Parameters:**
- `config`: `ConfigParser` instance
- `ini_path`: Path to `config.ini`
- `on_update`: Optional callback after clear

**Returns:** None

---

### URL History Management

#### `load_url_history(config) -> List[str]`

Load the list of visited URLs (most-recent-first).

**Returns:** List of URLs

---

#### `add_url_history(config, ini_path, url, max_items=50)`

Add a URL to the history.

**Parameters:**
- `url`: URL string
- `max_items`: Maximum history size (default: 50)

---

### HTML/Markdown Parsing

#### `_parse_html_and_apply(raw: str) -> Tuple[str, dict]`

Parse raw HTML/Markdown fragment and extract plain text with metadata.

**Parameters:**
- `raw`: Raw HTML string

**Returns:** Tuple of `(plain_text, metadata_dict)`

**Metadata Structure:**
```python
{
    'tags': {
        'tag_name': [[start, end], ...],  # Character ranges for formatting
        ...
    },
    'links': [
        {'start': int, 'end': int, 'href': str, 'title': str},
        ...
    ],
    'tables': [
        {
            'start': int,
            'end': int,
            'rows': [[{'start': int, 'end': int, 'text': str, 'attrs': {...}}, ...]],
            'colgroup': [{'width': int}, ...]
        }
    ],
    'prochtml': str,          # Processed HTML (whitespace normalized)
    'raw_fragment': str       # Original HTML fragment
}
```

**Example:**
```python
from functions import _parse_html_and_apply

html = "<p>Hello <b>world</b></p>"
plain, meta = _parse_html_and_apply(html)
print(f"Plain text: {plain}")
print(f"Tags: {meta.get('tags')}")
```

---

#### `extract_script_tags(html: str) -> List[dict]`

Extract all `<script>` tags from HTML.

**Returns:** List of script entries:
```python
[
    {
        'src': 'http://example.com/script.js' or None,
        'inline': 'var x = 1;' or None,
        'attrs': {'async': '', 'defer': '', ...}
    },
    ...
]
```

**Example:**
```python
from functions import extract_script_tags

html = "<script>console.log('hi');</script>"
scripts = extract_script_tags(html)
```

---

### Script Execution

#### `run_scripts(scripts, base_url=None, log_fn=None, host_update_cb=None, return_dom=False, collect_dom_each=False, **kwargs)`

Execute a list of script entries using the jsmini JavaScript interpreter.

**Parameters:**
- `scripts`: List of script dicts from `extract_script_tags()`
- `base_url`: Base URL for resolving relative script paths
- `log_fn`: Callback for log messages `fn(message: str)`
- `host_update_cb`: Callback for DOM mutations `fn(html: str)`
- `return_dom`: If True, return dict with DOM snapshots
- `collect_dom_each`: If True, capture DOM after each script
- `show_console`: Open JS console popup on execution
- `run_blocking`: Run synchronously (blocking) instead of async

**Returns:** 
- Legacy mode (return_dom=False): List of result dicts
- Extended mode: Dict with `results`, `final_dom`, `dom_changes`

**Result Structure:**
```python
{'ok': bool, 'error': str or None}
```

**Example:**
```python
from functions import extract_script_tags, run_scripts

scripts = extract_script_tags(html_content)
results = run_scripts(scripts, base_url='http://example.com')

for i, result in enumerate(results):
    if result['ok']:
        print(f"Script {i+1}: OK")
    else:
        print(f"Script {i+1}: ERROR - {result['error']}")
```

---

#### `run_scripts(..., return_dom=True) -> dict`

**Extended Return:**
```python
{
    'results': [{'ok': bool, 'error': str}, ...],
    'per_script_dom': ['<div>...</div>', ...] or None,
    'final_dom': '<body>...</body>',
    'dom_changes': [{'op': 'createElement', 'tag': 'div', ...}, ...]
}
```

---

### Color Utilities

#### `_hex_to_rgb(h: str) -> Tuple[int, int, int]`

Convert hex color to RGB tuple.

**Example:**
```python
r, g, b = _hex_to_rgb('#FF0000')  # (255, 0, 0)
```

---

#### `_rgb_to_hex(r: int, g: int, b: int) -> str`

Convert RGB to hex color.

**Example:**
```python
hex_color = _rgb_to_hex(255, 0, 0)  # '#ff0000'
```

---

#### `_lighten_color(hexcol: str, factor: float = 0.15) -> str`

Lighten a hex color by blending toward white.

**Parameters:**
- `factor`: Amount to lighten (0.0 to 1.0)

---

### Configuration

#### `get_js_console_default() -> bool`

Get whether JS console should open by default.

---

#### `set_js_console_default(value: bool)`

Persist JS console preference to config.

---

#### `get_debug_default() -> bool`

Get debug logging preference.

---

#### `set_debug_default(value: bool)`

Persist debug logging preference.

---

## jsmini.py API

### JavaScript Interpreter

#### `make_context(log_fn=None) -> dict`

Create a JavaScript execution context with built-ins.

**Parameters:**
- `log_fn`: Optional callback for `console.log()` messages

**Returns:** Context dict containing:
```python
{
    'console': {'log': fn},
    'document': {...},
    'Math': {...},
    'window': {...},
    'setTimeout': fn,
    'localStorage': {...},
    'undefined': undefined_sentinel,
    '_timers': [],
    ...
}
```

**Example:**
```python
import jsmini

ctx = jsmini.make_context(log_fn=print)
result = jsmini.run("var x = 2 + 2; console.log(x);", ctx)
```

---

#### `run(src: str, context: dict = None) -> Any`

Parse and execute JavaScript source string.

**Parameters:**
- `src`: JavaScript source code
- `context`: Optional execution context (created if not provided)

**Returns:** Result of last expression

**Example:**
```python
import jsmini

result = jsmini.run("2 + 2")  # Returns 4.0
```

---

#### `run_with_interpreter(src: str, context: dict = None) -> Tuple[Any, Interpreter]`

Execute JavaScript and return both result and interpreter instance.

**Returns:** Tuple of `(result, interpreter)`

**Use Case:** Access interpreter state, modify globals, run subsequent scripts in same context.

---

#### `run_timers(context: dict)`

Execute all enqueued timers in the context.

**Example:**
```python
import jsmini

ctx = jsmini.make_context()
jsmini.run("""
    setTimeout(function() {
        console.log('Timer fired!');
    }, 0);
""", ctx)
jsmini.run_timers(ctx)  # Execute the timer
```

---

### DOM API

#### `make_dom_shim(host=None) -> dict`

Create a minimal DOM implementation for JavaScript.

**Returns:** Document object with properties:
```python
{
    'createElement': fn(tag_name) -> Element,
    'getElementById': fn(id) -> Element or None,
    'querySelector': fn(selector) -> Element or None,
    'querySelectorAll': fn(selector) -> JSList,
    'body': Element,
    'addEventListener': fn(event, handler),
    'addEventListener': fn(event, handler),
    ...
}
```

**Example:**
```python
import jsmini

doc = jsmini.make_dom_shim()
el = doc['createElement']('div')
el.setAttribute('id', 'my-div')
doc['body'].appendChild(el)
html = doc['body'].innerHTML
print(html)  # '<div id="my-div"></div>'
```

---

### Element Class

#### `Element(tag_name: str)`

Constructor for DOM elements.

**Methods:**
- `setAttribute(name, value)` - Set attribute
- `removeAttribute(name)` - Remove attribute
- `hasAttribute(name) -> bool` - Check attribute exists
- `appendChild(child)` - Add child node
- `removeChild(child)` - Remove child
- `insertBefore(new, reference)` - Insert before reference
- `replaceChild(new, old)` - Replace child
- `addEventListener(event, handler)` - Attach event listener
- `removeEventListener(event, handler)` - Remove listener
- `dispatchEvent(event)` - Trigger event

**Properties:**
- `tagName: str` - Element tag
- `id: str` - ID attribute
- `className: str` - Class attribute
- `innerHTML: str` - Serialized child HTML
- `textContent: str` - Text content
- `parentNode: Element` - Parent element
- `childNodes: JSList` - Child nodes
- `children: JSList` - Child elements

---

### Parser/Tokenizer

#### `parse(src: str) -> tuple`

Parse JavaScript source into AST.

**Parameters:**
- `src`: JavaScript source code

**Returns:** AST root node (typically `('prog', [statements])`)

**Raises:** `SyntaxError` with context information on parse failure

---

#### `tokenize(src: str) -> List[Tuple]`

Tokenize JavaScript source.

**Returns:** List of `(type, value, start, end)` tuples

---

## js_builtins.py API

### Builtin Registration

#### `register_builtins(context: dict, JSFunction)`

Register JavaScript standard library into execution context.

**Parameters:**
- `context`: Context dict from `make_context()`
- `JSFunction`: JSFunction class from jsmini

**Installs:**
- `Array` constructor + methods (push, pop, map, filter, forEach, etc.)
- `Object` constructor + methods (keys, assign, create)
- `JSON` (parse, stringify)
- `localStorage` (getItem, setItem, removeItem, clear)
- `setTimeout` / `clearTimeout`
- `Event` constructor

**Example:**
```python
import jsmini
from js_builtins import register_builtins

ctx = jsmini.make_context()
register_builtins(ctx, jsmini.JSFunction)

# Now JS code can use Array, Object, JSON, etc.
jsmini.run("""
    var arr = [1, 2, 3];
    var doubled = arr.map(function(x) { return x * 2; });
    console.log(doubled);
""", ctx)
```

---

### Array Methods

All standard JavaScript Array methods are available on array objects:

- **Mutating:** `push()`, `pop()`, `splice()`, `shift()`, `unshift()`
- **Iteration:** `forEach()`, `map()`, `filter()`, `reduce()`, `some()`, `every()`, `find()`, `findIndex()`
- **Access:** `slice()`, `concat()`, `indexOf()`, `lastIndexOf()`
- **jQuery compat:** `each(callback)` - jQuery-style iteration with callback(index, value)

**Example:**
```python
jsmini.run("""
    var arr = [1, 2, 3, 4];
    var result = arr
        .filter(function(x) { return x > 2; })
        .map(function(x) { return x * 2; });
    console.log(result);  // [6, 8]
""", ctx)
```

---

### Object Methods

- `Object.create(proto)` - Create object with prototype
- `Object.keys(obj)` - Get own property names
- `Object.assign(target, ...sources)` - Copy properties
- `obj.hasOwnProperty(name)` - Check own property

---

### JSON Methods

#### `JSON.parse(text[, reviver]) -> value`

Parse JSON string with optional reviver function.

**Reviver signature:** `reviver(key, value) -> transformed_value`

---

#### `JSON.stringify(value[, replacer][, space]) -> string`

Serialize value to JSON string.

**Parameters:**
- `replacer`: Array of keys or function for filtering
- `space`: Indentation (number or string, max 10 chars)

---

### localStorage

Minimal in-memory key-value store (not persisted to disk).

- `localStorage.getItem(key)` - Get value
- `localStorage.setItem(key, value)` - Set value
- `localStorage.removeItem(key)` - Delete key
- `localStorage.clear()` - Clear all items

---

## Configuration

### config.ini Structure

```ini
[Section1]
fontName=consolas
fontSize=12
fontColor=#4AF626
backgroundColor=black
cursorColor=white
syntaxHighlighting=True
aiMaxContext=512
temperature=1.1
top_k=300
seed=1337
undoSetting=True
jsConsoleOnRun=False
debug=False

[Recent]
files=["path1", "path2", ...]

[URLHistory]
urls=["url1", "url2", ...]
```

---

## Examples

### Example 1: Load and Parse HTML

```python
from functions import _parse_html_and_apply

html = """
<div>
  <h1>Hello</h1>
  <p>This is <b>bold</b> text.</p>
  <a href="https://example.com">Link</a>
</div>
"""

plain, meta = _parse_html_and_apply(html)
print("Plain text:", plain)
print("Bold ranges:", meta['tags'].get('bold'))
print("Links:", meta['links'])
```

---

### Example 2: Execute JavaScript with DOM

```python
import jsmini

ctx = jsmini.make_context()
jsmini.run("""
    var el = document.createElement('div');
    el.setAttribute('class', 'container');
    el.textContent = 'Hello, World!';
    document.body.appendChild(el);
    console.log('DOM updated');
""", ctx)

# Retrieve final HTML
final_html = ctx['document']['body'].innerHTML
print(final_html)
```

---

### Example 3: Run Scripts with Host Callback

```python
from functions import extract_script_tags, run_scripts

html = """
<html>
<body id="output"></body>
<script>
    var el = document.getElementById('output');
    el.textContent = 'Script executed!';
    host.setRaw(document.body.innerHTML);
</script>
</html>
"""

scripts = extract_script_tags(html)

def on_dom_change(new_html):
    print("DOM changed:", new_html)

results = run_scripts(
    scripts,
    base_url='http://example.com',
    host_update_cb=on_dom_change,
    return_dom=True
)

print("Final DOM:", results['final_dom'])
```

---

### Example 4: Custom Syntax Highlighting

```python
from PythonApplication1 import PythonApplication1

# Access syntax highlighting via TextArea tag configuration
# (See PythonApplication1.py for _apply_tag_configs_to_widget)

# Tags available: 'keyword', 'string', 'comment', 'number', 'bold', 'italic', etc.
```

---

## Error Handling

### JavaScript Errors

```python
import jsmini

ctx = jsmini.make_context()
try:
    jsmini.run("throw new Error('Custom error')", ctx)
except jsmini.JSError as e:
    print(f"JS error: {e.value}")
```

### Parse Errors

```python
import jsmini

try:
    ast = jsmini.parse("var x = ;")  # Syntax error
except SyntaxError as e:
    print(f"Parse error: {e}")
```

---

## Performance Considerations

| Operation | Performance | Notes |
|-----------|-------------|-------|
| **HTML Parsing** | O(n) | Linear in HTML size; uses HTMLParser |
| **Script Execution** | Varies | Depends on script complexity; timeout protection available |
| **DOM Creation** | O(n) | Linear in number of elements |
| **Large Files** | ~50KB+ | Syntax highlighting may lag; use background thread |

---

## Debugging

### Enable Debug Logging

```python
from functions import set_debug_default

set_debug_default(True)
```

### Trace Script Execution

```python
import jsmini

ctx = jsmini.make_context()
ctx['_interp']._trace = True  # After first run()
```

---

## See Also

- **[Quick Start](QUICKSTART.md)** - Getting started guide
- **[Internal API Reference](INTERNAL-API.md)** - Internal functions and helper utilities
- **[Code Examples](EXAMPLES.md)** - Practical recipes using these APIs
- **[Advanced Examples](ADVANCED-EXAMPLES.md)** - Complex use cases and patterns
- **[JavaScript Engine](JSMINI.md)** - jsmini-specific APIs and features
- **[Editor Usage Guide](EDITOR-USAGE.md)** - How to use the editor GUI
- **[Documentation Index](INDEX.md)** - Browse all available documentation
- **[Contributing Guide](../CONTRIBUTING.md)** - How to extend SimpleEdit

