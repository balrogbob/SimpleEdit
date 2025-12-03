# 🚀 Quick Start Guide

## Get Started in 5 Minutes

Welcome to SimpleEdit! This guide will get you up and running quickly.

> **📖 For a complete documentation overview, see the [Documentation Index](INDEX.md)**

---

## Table of Contents

- [Installation](#installation)
- [Your First File](#your-first-file)
- [Basic Features](#basic-features)
- [Next Steps](#next-steps)

---

## Installation

### Option 1: Windows Executable (Easiest)

1. Download `PythonApplication1.exe` from [releases](https://github.com/balrogbob/SimpleEdit/releases)
2. Run the executable
3. Done! ✨

No Python installation needed.

### Option 2: Python Source (Windows/Mac/Linux)

**Prerequisites:** Python 3.8+

```bash
# Clone repository
git clone https://github.com/balrogbob/SimpleEdit.git
cd SimpleEdit

# Run directly
python PythonApplication1/PythonApplication1.py
```

---

## Your First File

### Step 1: Create a New File

- **Menu:** File → New
- **Keyboard:** `Ctrl+N`

### Step 2: Write Some Code

```python
def hello(name):
    print(f"Hello, {name}!")

hello("World")
```

Notice the syntax highlighting! Keywords are red, strings are green, etc.

### Step 3: Save Your Work

- **Menu:** File → Save
- **Keyboard:** `Ctrl+S`

Choose a location and filename (e.g., `hello.py`)

### Step 4: Format Your Text

Select some text and apply formatting:
- **Bold:** `Ctrl+B` or Edit → Bold
- **Italic:** `Ctrl+I` or Edit → Italic
- **Underline:** `Ctrl+U` or Edit → Underline

---

## Basic Features

### 🔍 Find & Replace

- **Open:** `Ctrl+H` or Edit → Find/Replace
- Type search term and replacement
- Click Replace or Replace All

### 📍 Go to Line

- **Open:** `Ctrl+G` or Edit → Go To Line
- Enter line number
- Jump instantly

### 📑 Multiple Tabs

- Click the `+` button to open new tabs
- Click the `x` to close tabs
- Use `Ctrl+Tab` to switch between tabs

### 📋 Recent Files

- **Menu:** File → Open Recent
- Quickly re-open files you've edited recently
- Remembers up to 10 files

### 🌐 HTML & Markdown Viewing

Open an HTML or Markdown file and SimpleEdit automatically renders it as readable text while preserving the source.

**Try it:**
1. Create a file with `.html` extension
2. Add some HTML: `<h1>Hello</h1><p>Test</p>`
3. Open it—it displays as clean text, not raw HTML!

---

## Next Steps

### Learn More

- **[Full API Documentation](API.md)** - All available functions and features
- **[Settings Guide](EDITOR-USAGE.md)** - Configure fonts, colors, behavior
- **[Advanced Features](EDITOR-USAGE.md)** - Tabs, rendering, JavaScript

### Explore JavaScript Execution

SimpleEdit can run JavaScript from HTML files:

1. Create a file named `test.html`
2. Paste this:

```html
<html>
<body>
  <h1>JavaScript Test</h1>
  <div id="output"></div>
  <script>
    var el = document.getElementById('output');
    el.textContent = 'Hello from JavaScript!';
  </script>
</body>
</html>
```

3. Open it—the JavaScript runs automatically!

### Customize Your Theme

- **Menu:** Settings → Settings...
- Adjust font, size, colors
- Changes saved automatically

---

## Common Tasks

### Open a File

- **Menu:** File → Open (`Ctrl+O`)
- Select file from browser
- File opens in current tab (or new tab if you prefer)

### Save & Export

- **Save:** `Ctrl+S` - Save current file
- **Save As:** `Ctrl+Shift+S` - Save with new name
- **Export as Markdown:** File → Save as Markdown

### Undo/Redo

- **Undo:** `Ctrl+Z`
- **Redo:** `Ctrl+Y`

### Close Files

- **Close Tab:** `Ctrl+W` or File → Close Tab
- **Close All:** File → Close All Tabs

---

## Keyboard Shortcuts Cheat Sheet

| Action | Windows/Linux | Mac |
|--------|---------------|-----|
| New | `Ctrl+N` | `⌘+N` |
| Open | `Ctrl+O` | `⌘+O` |
| Save | `Ctrl+S` | `⌘+S` |
| Save As | `Ctrl+Shift+S` | `⌘+Shift+S` |
| Undo | `Ctrl+Z` | `⌘+Z` |
| Redo | `Ctrl+Y` | `⌘+Shift+Z` |
| Find/Replace | `Ctrl+H` | `⌘+H` |
| Go to Line | `Ctrl+G` | `⌘+G` |
| Close Tab | `Ctrl+W` | `⌘+W` |
| Bold | `Ctrl+B` | `⌘+B` |
| Italic | `Ctrl+I` | `⌘+I` |
| Underline | `Ctrl+U` | `⌘+U` |

---

## Troubleshooting

**Syntax highlighting not working?**
- Check Settings → Settings... → "Syntax Highlighting" is enabled
- Restart the editor

**File won't save?**
- Ensure you have write permissions for the directory
- Try File → Save As to save elsewhere

**Running slow?**
- Disable syntax highlighting for very large files
- Close unnecessary tabs
- See [PERFORMANCE-TUNING.md](PERFORMANCE-TUNING.md)

---

## Get Help & Learn More

### 📚 Documentation
- **[Documentation Index](INDEX.md)** - Find any documentation you need
- **[Editor Features Guide](EDITOR-USAGE.md)** - Learn about all features
- **[API Reference](API.md)** - Complete function reference
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions
- **[FAQ](FAQ.md)** - Frequently asked questions

### 🎓 Advanced Topics
- **[Code Examples](EXAMPLES.md)** - Practical recipes
- **[Syntax Highlighting](SYNTAX.md)** - Language support and configuration
- **[JavaScript Engine](JSMINI.md)** - How to use jsmini
- **[Performance Tuning](PERFORMANCE-TUNING.md)** - Speed optimization

### 💬 Community & Support
- 🐛 [Report a Bug](https://github.com/balrogbob/SimpleEdit/issues)
- ✨ [Request a Feature](https://github.com/balrogbob/SimpleEdit/issues)
- ⭐ [Star on GitHub](https://github.com/balrogbob/SimpleEdit)

---

**Ready to dive deeper?** → [Documentation Index](INDEX.md)

