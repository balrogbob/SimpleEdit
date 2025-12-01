# 🎨 Syntax Highlighting Guide

## Overview

SimpleEdit provides comprehensive syntax highlighting for multiple programming languages and markup formats. This guide explains how to configure colors, customize themes, and extend language support.

---

## Table of Contents

- [Supported Languages](#supported-languages)
- [Color Configuration](#color-configuration)
- [Tag Reference](#tag-reference)
- [Custom Themes](#custom-themes)
- [Language-Specific Rules](#language-specific-rules)
- [Extending Support](#extending-support)

---

## Supported Languages

| Language | File Extension | Status | Notes |
|----------|---|--------|-------|
| **Python** | `.py` | ✅ Full | Keywords, strings, numbers, comments |
| **JavaScript** | `.js` | ✅ Full | ES5+ syntax, regex literals, async/await |
| **JSON** | `.json` | ✅ Full | Keys, values, numbers, strings |
| **HTML** | `.html` | ✅ Full | Tags, attributes, entities |
| **CSS** | `.css` | ✅ Full | Properties, values, colors |
| **Markdown** | `.md`, `.markdown` | ✅ Full | Headings, code blocks, emphasis |
| **YAML** | `.yaml`, `.yml` | ✅ Full | Keys, values, lists |
| **C/C++** | `.c`, `.cpp`, `.h` | ✅ Full | Keywords, strings, preprocessor |
| **C#** | `.cs` | ✅ Full | Keywords, strings, attributes |
| **Rathena NPC** | `.npc`, `.conf` | ✅ Full | Scripts, functions, variables |
| **Rathena YAML** | `.yml` | ✅ Full | Database format |

---

## Color Configuration

### Default Tag Colors

Colors are defined in `PythonApplication1.py` under `_DEFAULT_TAG_COLORS`:

```python
_DEFAULT_TAG_COLORS = {
    "number": {"fg": "#FDFD6A", "bg": ""},
    "string": {"fg": "#C9CA6B", "bg": ""},
    "keyword": {"fg": "red", "bg": ""},
    "comment": {"fg": "#75715E", "bg": ""},
    "builtin": {"fg": "#9CDCFE", "bg": ""},
    "operator": {"fg": "#AAAAAA", "bg": ""},
    # ... more tags
}
```

### Persisting Custom Colors

Colors are stored in **`config.ini`** under the `[Syntax]` section:

```ini
[Syntax]
tag.keyword.fg=#FF0000
tag.keyword.bg=
tag.string.fg=#00AA00
tag.string.bg=#000000
tag.comment.fg=#808080
tag.comment.bg=
```

**Format:**
- `tag.{tag_name}.fg` - Foreground (text) color (hex: `#RRGGBB`)
- `tag.{tag_name}.bg` - Background color (hex: `#RRGGBB`, empty for none)

### Applying Colors Programmatically

```python
from functions import get_hex_color
from tkinter import colorchooser

# Let user pick a color
color = colorchooser.askcolor()
hex_color = get_hex_color(color)

# Apply to a tag (example from PythonApplication1.py)
textArea.tag_config("keyword", foreground=hex_color)
```

---

## Tag Reference

### Text Formatting Tags

| Tag | Purpose | Default Color |
|-----|---------|---------|
| `bold` | Bold text | Default |
| `italic` | Italic text | Default |
| `underline` | Underlined text | Default |
| `small` | Reduced font size | Default |
| `mark` | Highlighted/marked text | `#FFF177` bg |

### Syntax Tags (Code)

| Tag | Purpose | Default Color |
|-----|---------|---------|
| `keyword` | Language keywords (if, for, while, etc.) | Red |
| `string` | String literals | `#C9CA6B` |
| `comment` | Comments (// or /* */) | `#75715E` |
| `number` | Numeric literals | `#FDFD6A` |
| `operator` | Operators (+, -, *, /, etc.) | `#AAAAAA` |
| `builtin` | Built-in functions | `#9CDCFE` |
| `function` | Function names | Default |
| `variable` | Variable names | `#8A2BE2` |
| `decorator` | Decorators (@) | `#66CDAA` |
| `class_name` | Class names | `#FFB86B` |
| `constant` | Constants (CONSTANT_VALUE) | `#FF79C6` |
| `attribute` | Object attributes | `#33ccff` |
| `def` | Function/method definition | Orange |
| `selfs` | `self` keyword | Yellow |

### HTML/Markdown Tags

| Tag | Purpose | Default Color |
|-----|---------|---------|
| `html_tag` | HTML element names | `#569CD6` |
| `html_attr` | HTML attribute names | `#9CDCFE` |
| `html_attr_value` | Attribute values | `#CE9178` |
| `html_comment` | HTML comments | `#6A9955` |

### Code Block Tags (inside `<code>` / `<pre>`)

| Tag | Purpose | Default Color |
|-----|---------|---------|
| `code_block` | Code block container | White bg, black text |
| `cb_keyword` | Keywords in code block | Inherited |
| `cb_string` | Strings in code block | Inherited |
| `cb_comment` | Comments in code block | Inherited |
| `cb_number` | Numbers in code block | Inherited |
| `cb_tag` | HTML tags in code block | `#569CD6` |
| `cb_attr` | HTML attributes in code block | `#9CDCFE` |

### Special/UI Tags

| Tag | Purpose | Default Color |
|-----|---------|---------|
| `currentLine` | Current line highlighting | `#222222` bg |
| `trailingWhitespace` | Trailing spaces | `#331111` bg |
| `find_match` | Find/replace matches | `#444444` bg, white text |
| `marquee` | Marquee/selected text | `#FF4500` |
| `code` | Inline code (Markdown) | Monospace, white bg |
| `kbd` | Keyboard input | Monospace, white bg |
| `todo` | TODO markers | White text, `#B22222` bg |
| `hyperlink` | Hyperlinks | `#0000EE`, underlined |
| `mark` | Marked text | `#FFF177` bg |
| `table` | Table container | Default |
| `tr` | Table row | Default |
| `td` | Table cell | Light background |
| `th` | Table header | Darker background, bold |

---

## Custom Themes

### Creating a Custom Theme

1. **Create a new theme config file:**

```ini
# my_dark_theme.ini
[Syntax]
# Keywords (control flow)
tag.keyword.fg=#FF5C8D
tag.keyword.bg=

# Strings
tag.string.fg=#00FF00
tag.string.bg=

# Comments
tag.comment.fg=#808080
tag.comment.bg=

# Numbers
tag.number.fg=#FFD700
tag.number.bg=

# Built-ins
tag.builtin.fg=#00BFFF
tag.builtin.bg=

# Operators
tag.operator.fg=#00FF00
tag.operator.bg=
```

2. **Load the theme programmatically:**

```python
import configparser
from functions import _parse_html_and_apply

theme = configparser.ConfigParser()
theme.read('my_dark_theme.ini')

# Merge into main config
for key, value in theme.items('Syntax'):
    config.set('Syntax', key, value)

with open('config.ini', 'w') as f:
    config.write(f)
```

3. **Apply to editor:**

```python
# Restart editor or call:
from PythonApplication1 import _apply_tag_configs_to_widget

_apply_tag_configs_to_widget(textArea)
```

### Pre-Built Themes

Save these in `PythonApplication1/themes/` directory:

#### Light Theme

```ini
[Syntax]
tag.keyword.fg=#0000AA
tag.keyword.bg=
tag.string.fg=#008000
tag.string.bg=
tag.comment.fg=#808080
tag.comment.bg=
tag.number.fg=#FF6600
tag.number.bg=
tag.builtin.fg=#0066CC
tag.builtin.bg=
```

#### Monokai Theme

```ini
[Syntax]
tag.keyword.fg=#F92672
tag.keyword.bg=
tag.string.fg=#E6DB74
tag.string.bg=
tag.comment.fg=#75715E
tag.comment.bg=
tag.number.fg=#AE81FF
tag.number.bg=
tag.builtin.fg=#66D9EF
tag.builtin.bg=
```

#### High Contrast Theme

```ini
[Syntax]
tag.keyword.fg=#FF0000
tag.keyword.bg=
tag.string.fg=#00FF00
tag.string.bg=
tag.comment.fg=#CCCCCC
tag.comment.bg=#000000
tag.number.fg=#FFFF00
tag.number.bg=
tag.builtin.fg=#00FFFF
tag.builtin.bg=
```

---

## Language-Specific Rules

### Python Highlighting

**Supported:**
- Keywords: `if`, `else`, `for`, `while`, `def`, `class`, `return`, `try`, `except`, `import`, `from`, `async`, `await`, etc.
- Triple-quoted strings: `"""..."""` and `'''...'''`
- F-strings: `f"...{x}..."`
- Comments: `#` line comments
- Decorators: `@decorator`

**Example:**
```python
@dataclass
class MyClass:
    """Class docstring."""
    value: int = 0
    
    def method(self):
        # Comment
        return f"Value: {self.value}"
```

### JavaScript Highlighting

**Supported:**
- ES5+ keywords: `function`, `var`, `let`, `const`, `async`, `await`, `class`, `extends`, etc.
- Regex literals: `/pattern/flags`
- Template strings: `` `string ${expr}` ``
- Comments: `//` line and `/* */` block
- Arrow functions: `() => {}`

**Example:**
```javascript
async function* generator(items) {
    for (const item of items) {
        yield `Processing: ${item}`;
    }
}

const pattern = /^[a-z]+$/i;
```

### HTML/XML Highlighting

**Supported:**
- Opening/closing tags
- Attributes and values
- Entities: `&nbsp;`, `&lt;`, etc.
- Comments: `<!-- -->`
- CDATA sections

**Example:**
```html
<div class="container" data-value="123">
    <!-- Comment -->
    Content &amp; special chars
    <script type="text/javascript">
        // Nested JavaScript
    </script>
</div>
```

### Markdown Highlighting

**Supported:**
- Headings: `# H1`, `## H2`, etc.
- Emphasis: `*italic*`, `**bold**`, `***bold-italic***`
- Code: Inline `` `code` `` and fenced ` ``` `
- Links: `[text](url)`
- Lists: `- item`, `1. item`
- Blockquotes: `> quote`

**Example:**
```markdown
# Heading

This is **bold** and *italic* text.

- List item 1
- List item 2

[Link text](https://example.com)

```python
code_block = "highlighted"
```
```

### Code Block Language Detection

When code blocks are embedded in HTML/Markdown, language is detected from:

1. **Fence language hint:** ` ```python` or ` ```javascript`
2. **`class` attribute:** `class="language-python"` or `class="lang-javascript"`
3. **`data-lang` attribute:** `data-lang="yaml"`
4. **Heuristic guess:** Based on content patterns
   - `def ` → Python
   - `function ` → JavaScript
   - `#include` → C/C++
   - `key: value` → YAML/TOML

---

## Extending Support

### Adding a New Language

1. **Define tokenizer in `functions.py`:**

```python
class _SimpleHTMLToTagged(HTMLParser):
    def _cb_mylang(self, text: str, base: int):
        """Tokenizer for MyLanguage."""
        try:
            # Keywords
            kw_re = re.compile(r'\b(keyword1|keyword2|keyword3)\b')
            # Strings
            str_re = re.compile(r'"[^"]*"|\'[^\']*\'')
            # Comments
            com_re = re.compile(r'#[^\n]*')
            
            # Apply tags
            for m in kw_re.finditer(text):
                self._cb_add('cb_keyword', base + m.start(), base + m.end())
            for m in str_re.finditer(text):
                self._cb_add('cb_string', base + m.start(), base + m.end())
            for m in com_re.finditer(text):
                self._cb_add('cb_comment', base + m.start(), base + m.end())
        except Exception:
            pass
```

2. **Register in `_cb_apply_syntax`:**

```python
def _cb_apply_syntax(self, lang: str, text: str, base_off: int):
    lang = (lang or '').lower()
    # ... existing cases ...
    elif lang in ('mylang', 'ml'):
        self._cb_mylang(text, base_off)
```

3. **Update heuristic guesser:**

```python
def _heuristic_guess_lang(self, text: str) -> str | None:
    # ... existing checks ...
    if re.search(r'PATTERN_FOR_MYLANG', text):
        return 'mylang'
    return None
```

### Custom Tokenizer Example: YAML

```python
def _cb_yaml(self, text: str, base: int):
    """YAML tokenizer (keys, values, comments)."""
    try:
        # Keys (before colon)
        key_re = re.compile(r'^(?:\s*-?\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*:(?=\s|$)', re.MULTILINE)
        # Values (quoted strings, numbers, booleans)
        str_re = re.compile(r'("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\')')
        num_re = re.compile(r'\b-?(?:0|[1-9]\d*)(?:\.\d+)?\b')
        kw_re = re.compile(r'\b(true|false|null|on|off|yes|no)\b', re.IGNORECASE)
        # Comments
        com_re = re.compile(r'#[^\n]*')
        
        # Apply
        for m in key_re.finditer(text):
            self._cb_add('cb_attr', base + m.start(1), base + m.end(1))
        for m in str_re.finditer(text):
            self._cb_add('cb_string', base + m.start(), base + m.end())
        for m in num_re.finditer(text):
            self._cb_add('cb_number', base + m.start(), base + m.end())
        for m in kw_re.finditer(text):
            self._cb_add('cb_keyword', base + m.start(), base + m.end())
        for m in com_re.finditer(text):
            self._cb_add('cb_comment', base + m.start(), base + m.end())
    except Exception:
        pass
```

### Registering Syntax Presets

Syntax presets are stored in `PythonApplication1/syntax/` as `.ini` files.

**Format:**
```ini
[Syntax]
# Tag color definitions
tag.keyword.fg=#FF0000
tag.keyword.bg=
# ...
```

Load programmatically:
```python
config = configparser.ConfigParser()
config.read('PythonApplication1/syntax/python.ini')
```

---

## Performance Tips

| Optimization | Impact | Usage |
|--------------|--------|-------|
| **Background highlighting** | High | Large files (>50KB) |
| **Disable real-time highlighting** | High | Performance mode |
| **Cache tokenizer results** | Medium | Repeated parsing |
| **Lazy tag application** | Low | Visible viewport only |

### Enable Background Highlighting

Already enabled by default. Access via:

```python
from PythonApplication1 import updateSyntaxHighlighting
updateSyntaxHighlighting.get()  # Check if enabled
```

---

## Troubleshooting

### Colors Not Appearing

1. **Check config.ini:**
   ```bash
   cat config.ini | grep "\[Syntax\]" -A 10
   ```

2. **Verify hex colors are valid:**
   ```python
   # Valid formats: #RRGGBB, #RGB (auto-expanded)
   import re
   if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
       print(f"Invalid color: {color}")
   ```

3. **Restart editor to apply changes**

### Language Not Being Detected

1. **Add to heuristic guesser** (see Extending Support above)
2. **Explicitly set code block fence:**
   ````
   ```python
   code here
   ```
   ````

### Performance Issues

1. **Disable real-time highlighting for large files:**
   ```python
   # Settings → Settings... → uncheck "Syntax Highlighting"
   ```

2. **Profile syntax highlighting:**
   ```python
   # In PythonApplication1.py, uncomment debug timings
   ```

---

## See Also

- [API Documentation](API.md)
- [JavaScript Engine Docs](JSMINI.md)
- [Color Reference](https://htmlcolorcodes.com/)
