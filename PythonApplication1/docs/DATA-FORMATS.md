# 📋 SimpleEdit Data Formats Reference

**Complete File Format Specifications and Data Structure Documentation**

**Status:** Complete data format reference  
**Last Updated:** January 12, 2025  
**For:** Developers, Contributors, and Power Users

---

## Table of Contents

- [Overview](#overview)
- [config.ini Format](#configini-format)
- [Syntax Definition Files](#syntax-definition-files)
- [HTML Metadata Structure](#html-metadata-structure)
- [Recent Files Format](#recent-files-format)
- [JavaScript Context Structure](#javascript-context-structure)
- [File Type Detection](#file-type-detection)
- [Data Serialization Formats](#data-serialization-formats)
- [Internal Data Structures](#internal-data-structures)

---

## Overview

This document specifies all **file formats, data structures, and serialization formats** used throughout SimpleEdit.

### Format Categories

1. **Configuration** - `config.ini` format and schema
2. **Syntax Definitions** - Language highlighting patterns (`.ini` files)
3. **Metadata** - HTML parsing results, tag ranges
4. **Storage** - Recent files, URL history (JSON in INI)
5. **JavaScript Context** - Runtime environment structure
6. **Detection** - How file types are identified

### Editing Guidelines

When manually editing SimpleEdit data files:
- ✅ Use UTF-8 encoding
- ✅ Validate JSON in recent files lists
- ✅ Use valid hex colors (#RRGGBB format)
- ✅ Maintain INI file structure (sections and keys)
- ✅ Back up config.ini before editing

---

## config.ini Format

### Location

`config.ini` - Located in SimpleEdit application directory

### File Structure

Complete `config.ini` schema with all sections and keys:

```ini
[Section1]
# UI Settings
fontName=string              # Font family name (e.g., 'consolas', 'courier new')
fontSize=int                 # Font size in points (8-72, typical 10-14)
fontColor=hex                # Text color (#RRGGBB format)
backgroundColor=hex          # Editor background color
cursorColor=hex              # Cursor/caret color

# Behavior Settings
syntaxHighlighting=bool      # Enable/disable syntax highlighting
undoSetting=bool             # Enable undo/redo
jsConsoleOnRun=bool          # Auto-open JS Console on script execution
debug=bool                   # Enable debug logging

# AI Settings (if model.py/torch available)
aiMaxContext=int             # Max tokens for AI (typical 256-2048)
temperature=float            # Randomness (0.0=deterministic, 2.0=very random)
top_k=int                    # Sample from top K tokens (50-500)
seed=int                     # Random seed for reproducibility

# AI Model Loading
loadAIOnOpen=bool            # Load model when opening file
loadAIOnNew=bool             # Load model on new file

# Formatting & Export
saveFormattingInFile=bool    # Embed formatting in saved files
exportCssMode=string         # 'inline-element' | 'inline-block' | 'external'
exportCssPath=string         # Path to external CSS file (if exportCssMode='external')

[Recent]
files=json_list              # JSON array of recent file paths
                             # Format: ["path1", "path2", ...]
                             # Most recent first

[URLHistory]
urls=json_list               # JSON array of recently visited URLs
                             # Format: ["url1", "url2", ...]
                             # Most recent first
```

### Field Details

#### UI Settings

| Field | Type | Range | Default | Notes |
|-------|------|-------|---------|-------|
| `fontName` | string | System fonts | 'consolas' | Use monospace fonts for best results |
| `fontSize` | int | 8-72 | 12 | Point size, affects readability |
| `fontColor` | hex | #000000-#FFFFFF | '#4AF626' | Text color |
| `backgroundColor` | hex | #000000-#FFFFFF | 'black' | Editor background |
| `cursorColor` | hex | #000000-#FFFFFF | 'white' | Cursor visibility |

#### Behavior Settings

| Field | Type | Values | Default | Notes |
|-------|------|--------|---------|-------|
| `syntaxHighlighting` | bool | True/False | True | Highlight code syntax |
| `undoSetting` | bool | True/False | True | Enable undo/redo |
| `jsConsoleOnRun` | bool | True/False | False | Show console when running scripts |
| `debug` | bool | True/False | False | Enable verbose debug logging |

#### AI Settings

| Field | Type | Range | Default | Notes |
|-------|------|-------|---------|-------|
| `aiMaxContext` | int | 128-4096 | 512 | Context window for model |
| `temperature` | float | 0.0-2.0 | 1.1 | Higher = more random output |
| `top_k` | int | 1-1000 | 300 | Vocabulary restriction |
| `seed` | int | 1-2^31 | 1337 | Reproducibility |

#### Export Settings

| Field | Type | Values | Default | Notes |
|-------|------|--------|---------|-------|
| `exportCssMode` | string | inline-element \| inline-block \| external | inline-element | CSS embedding method |
| `exportCssPath` | string | file path | '' | Used only when mode='external' |

### Example config.ini

```ini
[Section1]
fontName=consolas
fontSize=12
fontColor=#4AF626
backgroundColor=black
cursorColor=white
syntaxHighlighting=True
undoSetting=True
aiMaxContext=512
temperature=1.1
top_k=300
seed=1337
loadAIOnOpen=False
loadAIOnNew=False
saveFormattingInFile=False
exportCssMode=inline-element
exportCssPath=
jsConsoleOnRun=False
debug=False

[Recent]
files=["C:\\Users\\user\\project\\main.py", "C:\\Users\\user\\docs\\readme.md"]

[URLHistory]
urls=["https://github.com/balrogbob/SimpleEdit", "https://python.org"]
```

### Editing Tips

**Safe Font Names (Cross-Platform):**
- Windows/Linux/macOS: `consolas`, `courier new`, `courier`, `monospace`
- Windows only: `lucida console`
- macOS only: `menlo`, `monaco`
- Linux only: `dejavu sans mono`, `liberation mono`

**Valid Color Values:**
- Hex format: `#RRGGBB` (e.g., `#FF0000` = red)
- Common values:
  - Black: `#000000`
  - White: `#FFFFFF`
  - Green: `#00FF00`
  - Cyan: `#00FFFF`

**Safe AI Settings:**
- Low context: 256 (minimal, fast)
- Medium context: 512 (balanced, recommended)
- High context: 1024 (more memory, slower)
- Max context: 2048 (very memory-intensive)

---

## Syntax Definition Files

### Location

`PythonApplication1/syntax/` directory

### File Format

Syntax definition files are `.ini` format with keyword lists and regex patterns.

### Structure

```ini
[keywords]
keyword=keyword1, keyword2, keyword3, keyword4, ...

[patterns]
pattern_name=regex_pattern
pattern_name2=regex_pattern2
...
```

### Keywords Section

Comma-separated list of language keywords to highlight:

```ini
[keywords]
keyword=if, else, elif, for, while, return, def, class, import, from
```

**Best Practices:**
- One keyword per entry
- Separate with commas and spaces
- Use lowercase keywords
- Include all language keywords

### Patterns Section

Python raw string regex patterns for syntax elements:

```ini
[patterns]
string_double=r'"[^"\n]*"'
string_single=r"'[^'\n]*'"
comment=r'#.*$'
number=r'\b\d+(?:\.\d+)?\b'
```

**Pattern Names:**
| Name | Matches | Example |
|------|---------|---------|
| `string_double` | Double-quoted strings | `"hello"` |
| `string_single` | Single-quoted strings | `'hello'` |
| `comment` | Line comments | `# comment` |
| `number` | Numeric literals | `123`, `3.14` |
| `operator` | Operators | `+`, `-`, `*` |
| `builtin` | Built-in functions | `print`, `len` |
| `decorator` | Decorators | `@decorator` |
| `class_name` | Class definitions | `class MyClass` |

### Example: Python Syntax File

**File: `python.ini`**

```ini
[keywords]
keyword=if, else, elif, for, while, return, def, class, import, from, as, try, except, finally, with, lambda, yield, raise, assert, del, pass, break, continue, global, nonlocal

[patterns]
comment=r'#.*$'
string_double=r'"(?:\\.|[^"\\])*"'
string_single=r"'(?:\\.|[^'\\])*'"
number=r'\b(?:0[bB][01_]+|0[oO][0-7_]+|0[xX][0-9a-fA-F_]+|\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?)\b'
```

### Example: JSON Syntax File

**File: `json.ini`**

```ini
[keywords]
keyword=true, false, null

[patterns]
comment=r''
string_double=r'"(?:\\.|[^"\\])*"'
number=r'\b(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?\b'
```

### Creating Custom Language File

**Steps:**

1. **Create file:** `PythonApplication1/syntax/mylang.ini`

2. **Define keywords:**
```ini
[keywords]
keyword=BEGIN, END, PROCESS, IF, ELSE
```

3. **Define patterns:**
```ini
[patterns]
comment=r'--[^\n]*'
string=r'"[^"]*"'
number=r'\d+'
```

4. **Save and restart** SimpleEdit

5. **Use on files:** `.mylang` extension files will use your syntax

---

## HTML Metadata Structure

### Source

Returned by `_parse_html_and_apply()` in `functions.py`

### Structure

```python
metadata = {
    # Character ranges for formatting tags
    'tags': {
        'bold': [[start, end], [start, end], ...],
        'italic': [[start, end], ...],
        'underline': [[start, end], ...],
        'hyperlink': [[start, end], ...],
        'code_block': [[start, end], ...],
        # ... other tag types
    },
    
    # Hyperlinks with URLs
    'links': [
        {
            'start': int,        # Character position start
            'end': int,          # Character position end
            'href': str,         # URL
            'title': str|None    # Optional title attribute
        },
        ...
    ],
    
    # Table structures
    'tables': [
        {
            'start': int,
            'end': int,
            'attrs': {           # Table attributes
                'class': str,
                'style': str,
                ...
            },
            'rows': [            # Table rows
                [                # Single row
                    {            # Cell
                        'start': int,
                        'end': int,
                        'text': str,
                        'type': 'td'|'th',
                        'attrs': {
                            'colspan': int,
                            'rowspan': int,
                            'align': str,
                            ...
                        }
                    },
                    ...
                ],
                ...
            ],
            'colgroup': [        # Column info
                {'width': int},
                ...
            ]
        },
        ...
    ],
    
    # Original and processed HTML
    'raw_fragment': str,         # Original HTML
    'prochtml': str              # HTML with whitespace normalized
}
```

### Tag Types

**Formatting Tags:**
- `bold` - Bold/strong text
- `italic` - Italic/emphasized text
- `underline` - Underlined text
- `small` - Small text
- `mark` - Highlighted text
- `code` - Inline code

**Block Tags:**
- `code_block` - `<pre><code>` blocks
- `blockquote` - Quoted text

**Special Tags:**
- `hyperlink` - Links (also in `links` array)
- `todo` - TODO/FIXME markers

### Example Metadata

```python
{
    'tags': {
        'bold': [[6, 11]],           # "world" in "Hello world"
        'hyperlink': [[14, 19]],     # Link text positions
        'code_block': [[25, 45]]     # Code block position
    },
    'links': [
        {
            'start': 14,
            'end': 19,
            'href': 'https://example.com',
            'title': None
        }
    ],
    'tables': [],
    'raw_fragment': '<p>Hello <b>world</b> <a href="...">link</a></p>...',
    'prochtml': '<p>Hello <b>world</b> <a href="...">link</a></p>...'
}
```

---

## Recent Files Format

### Location

In `config.ini` under `[Recent]` section, key `files`

### Format

JSON array of absolute file paths:

```json
["C:\\path\\to\\file1.py", "D:\\path\\to\\file2.md", "C:\\path\\to\\file3.txt"]
```

**Format Rules:**
- ✅ Valid JSON array format (square brackets)
- ✅ Double quotes for strings
- ✅ Commas between entries
- ✅ Absolute file paths (full path from root)
- ✅ Paths use forward slashes OR backslashes (platform handles both)
- ✅ Most recent file first

### Example

```ini
[Recent]
files=["C:\\Users\\Alice\\project\\main.py", "C:\\Users\\Alice\\docs\\README.md", "C:\\Users\\Alice\\config\\settings.json"]
```

### Size Limits

- Maximum entries: 10 (default, configurable)
- Maximum filename length: 255 characters (OS limit)
- Total size: Limited by INI file size (typically 64KB)

### Editing Safely

**Adding a file manually:**

```ini
[Recent]
files=["C:\\new\\file.py", "C:\\old\\file.md"]
```

**Remove a file manually:**

```ini
[Recent]
files=["C:\\remaining\\file.md"]
```

**Validation:**
- Ensure JSON is valid (use `json.loads()` to test)
- Verify paths are accessible
- Use absolute paths only

---

## JavaScript Context Structure

### Source

Created by `jsmini.make_context()` in `jsmini.py`

### Complete Structure

```python
context = {
    # Console object
    'console': {
        'log': function,
        'error': function,
        'warn': function
    },
    
    # Document object (DOM shim)
    'document': {
        'createElement': function(tag_name),
        'getElementById': function(id),
        'querySelector': function(selector),
        'querySelectorAll': function(selector),
        'body': Element,
        'addEventListener': function,
        'removeEventListener': function,
        'forceRedraw': function,
        '__setHost': function,
        # ... other document methods
    },
    
    # Window object
    'window': {
        # References to global objects
    },
    
    # Math object
    'Math': {
        'PI': 3.14159...,
        'E': 2.71828...,
        'abs': function,
        'floor': function,
        'ceil': function,
        'round': function,
        'max': function,
        'min': function,
        'random': function,
        'sin': function,
        'cos': function,
        'tan': function,
        'sqrt': function,
        'pow': function,
        # ... other math functions
    },
    
    # Array constructor
    'Array': constructor,
    
    # Object constructor
    'Object': constructor,
    
    # JSON object
    'JSON': {
        'parse': function(text, reviver),
        'stringify': function(value, replacer, space)
    },
    
    # localStorage (in-memory key-value store)
    'localStorage': {
        'getItem': function(key),
        'setItem': function(key, value),
        'removeItem': function(key),
        'clear': function
    },
    
    # Timer functions
    'setTimeout': function(callback, delay),
    'setInterval': function(callback, interval),
    'clearTimeout': function(timer_id),
    'clearInterval': function(timer_id),
    
    # Event constructor
    'Event': constructor,
    
    # Element constructor
    'Element': constructor,
    
    # Undefined sentinel
    'undefined': undefined_object,
    
    # Internal structures (not for direct use)
    '_timers': [],           # Pending timers
    '_dom_changes': [],      # DOM mutation log (if logging enabled)
    '_interp': Interpreter,  # Interpreter instance
    '__attachHost': function # Host bridge function
}
```

### Element Object

**Properties:**
- `tagName` - Element tag name
- `id` - ID attribute
- `className` - Class attribute
- `innerHTML` - Serialized child HTML (get/set)
- `textContent` - Text content (get/set)
- `parentNode` - Parent element reference
- `childNodes` - All children (text + elements)
- `children` - Element children only
- `firstChild`, `lastChild` - First/last children
- `nextSibling`, `previousSibling` - Sibling navigation

**Methods:**
- `setAttribute(name, value)` - Set attribute
- `getAttribute(name)` - Get attribute
- `removeAttribute(name)` - Remove attribute
- `hasAttribute(name)` - Check attribute
- `appendChild(child)` - Add child
- `removeChild(child)` - Remove child
- `insertBefore(new, reference)` - Insert before reference
- `replaceChild(new, old)` - Replace child
- `addEventListener(event, handler)` - Add event listener
- `removeEventListener(event, handler)` - Remove listener
- `dispatchEvent(event)` - Trigger event
- `querySelectorAll(selector)` - Find descendants

### Example Context Usage

```python
import jsmini

ctx = jsmini.make_context()

# Access global objects
Math = ctx['Math']
console = ctx['console']
document = ctx['document']

# Create element
div = document['createElement']('div')
div.setAttribute('id', 'main')
document['body'].appendChild(div)

# Access data
data = ctx['localStorage'].getItem('key')
parsed = ctx['JSON'].parse('{"name": "value"}')

# Timers
ctx['setTimeout'](callback, 1000)
```

---

## File Type Detection

### Detection Rules

SimpleEdit detects file types by:

1. **Extension-based** (primary)
2. **Content inspection** (fallback)
3. **User override** (explicit)

### Supported Types

| Extension | Type | Handler | Notes |
|-----------|------|---------|-------|
| `.py` | Python | Syntax highlighting | Full support |
| `.js` | JavaScript | Syntax highlighting | Full support |
| `.html` | HTML | HTML parser + rendering | Script execution |
| `.md` | Markdown | HTML parser | Renders as HTML |
| `.json` | JSON | Syntax highlighting | Validatable |
| `.txt` | Text | Plain text | No highlighting |
| `.ini` | INI | Syntax highlighting | Config file |
| `.yaml` | YAML | Syntax highlighting | Config file |
| `.xml` | XML | Syntax highlighting | Markup |
| `.c` | C | Syntax highlighting | Code |
| `.cpp` | C++ | Syntax highlighting | Code |
| `.cs` | C# | Syntax highlighting | Code |

### Content-Based Detection

When extension unclear, SimpleEdit checks:

```python
# Python indicators
if 'def ' in content or 'import ' in content:
    return 'python'

# JavaScript indicators
if 'function ' in content or 'var ' in content:
    return 'javascript'

# HTML indicators
if '<html' in content.lower() or '<div' in content.lower():
    return 'html'

# JSON indicators
if content.strip().startswith('{') or content.strip().startswith('['):
    return 'json'

# Markdown indicators
if '#' in content and '\n' in content:
    return 'markdown'
```

---

## Data Serialization Formats

### JSON Serialization

Used for storing complex data in INI files:

```python
# Python object
data = {
    'files': ['file1.py', 'file2.md'],
    'urls': ['http://example.com'],
    'settings': {'key': 'value'}
}

# Serialized (stored in config.ini)
json_string = json.dumps(data)
# {"files": ["file1.py", "file2.md"], ...}

# Deserialized (read from config.ini)
loaded = json.loads(json_string)
```

### String Escaping

In INI files, JSON arrays must be properly quoted:

```ini
# ✅ Correct - JSON is value
files=["path1", "path2"]

# ❌ Wrong - unquoted
files=[path1, path2]

# ✅ With escape sequences
files=["C:\\path\\to\\file", "D:\\another\\file"]
```

### URL Storage

URLs stored as JSON array in INI:

```ini
[URLHistory]
urls=["https://github.com", "https://python.org", "file:///C:/Users/user/file.html"]
```

---

## Internal Data Structures

### Tag Range Format

All tag positions use inclusive `[start, end)` ranges:

```python
# Tag range represents characters from start to end (exclusive)
# For string "Hello world"
# 0: H
# 1: e
# ...
# 6: w
# ...
# 11: (end of string)

'bold': [[6, 11]]  # Represents "world"
```

### Cell Content Separator

Table cells with multiple lines use `IN_CELL_NL` marker:

```python
IN_CELL_NL = '\u2028'  # Unicode line separator

# Cell with multiple lines
cell_text = "Line 1\u2028Line 2\u2028Line 3"

# When exporting to HTML
cell_text.replace(IN_CELL_NL, '<br>')
# Result: "Line 1<br>Line 2<br>Line 3"
```

### Script Entry Format

Format for script entries from `extract_script_tags()`:

```python
script_entry = {
    'src': 'http://example.com/script.js' or None,
    'inline': '<script code>' or None,
    'attrs': {
        'type': 'text/javascript',
        'async': '',
        'defer': '',
        'charset': 'utf-8',
        # ... other attributes
    }
}
```

### Result Entry Format

Format for results from `run_scripts()`:

```python
result = {
    'ok': True or False,           # Success indicator
    'error': 'error message' or None  # Error if failed
}

# Extended format (when return_dom=True)
extended_result = {
    'results': [result, ...],           # List of above
    'final_dom': '<html>...</html>',    # Final HTML
    'per_script_dom': [...] or None,    # Per-script snapshots
    'dom_changes': [...] or None        # Mutation log
}
```

---

## Summary Reference Table

| Format | Location | Type | Primary Use |
|--------|----------|------|-------------|
| **config.ini** | App directory | INI | Settings/config |
| **Syntax files** | syntax/ | INI | Language highlighting |
| **HTML metadata** | Return value | Dict | Tag ranges & links |
| **Recent files** | config.ini | JSON | File history |
| **URL history** | config.ini | JSON | URL history |
| **JS context** | Runtime | Dict | Execution environment |
| **Table cells** | Metadata | String | Multi-line cells |
| **Script entries** | Parse result | Dict | Script info |

---

## Validation Checklist

When creating or modifying data:

- [ ] **config.ini:** Valid INI format, proper sections
- [ ] **Syntax files:** Valid regex patterns in raw strings
- [ ] **JSON data:** Valid JSON syntax (test with `json.loads()`)
- [ ] **File paths:** Absolute paths, UTF-8 encoded
- [ ] **Colors:** Valid hex format (#RRGGBB)
- [ ] **HTML metadata:** Correct range positions
- [ ] **Backup:** Config backed up before editing

---

## See Also

- **[API Reference](API.md)** - Function signatures
- **[JSMINI Guide](JSMINI.md)** - JavaScript engine details
- **[INTERNAL-API](INTERNAL-API.md)** - Internal functions
- **[Advanced Examples](ADVANCED-EXAMPLES.md)** - Data usage patterns
- **[ARCHITECTURE](ARCHITECTURE.md)** - System design
- **[Configuration Guide](EDITOR-USAGE.md#configuration)** - User config instructions

---

**Data Formats Reference for SimpleEdit**

*Complete specification of all file formats, data structures, and serialization methods used throughout SimpleEdit. Essential reference for developers working with file I/O, configuration, and data persistence.*
