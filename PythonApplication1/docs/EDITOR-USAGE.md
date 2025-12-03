# 📖 Editor Usage Guide

Complete guide to using SimpleEdit features and configuring your workflow.

---

## Table of Contents

- [Getting Around](#getting-around)
- [Editing Text](#editing-text)
- [File Management](#file-management)
- [Finding & Replacing](#finding--replacing)
- [Formatting](#formatting)
- [Tabs & Organization](#tabs--organization)
- [Browsing Mode](#browsing-mode)
- [Settings & Customization](#settings--customization)
- [Keyboard Shortcuts](#keyboard-shortcuts)

---

## Getting Around

### The Editor Interface

```
┌─ Menu Bar ────────────────────────────┐
│ File  Edit  Settings  Symbols         │
├─ Toolbar ────────────────────────────┤
│ [Font] [Size] [Bold] [Italic] [AI]   │
├─ Tabs ────────────────────────────────┤
│ ✓ [file1.py] [file2.html] [+]        │
├─────────────────────────────────────┤
│                                      │
│  Editor Area (Text with highlighting)│
│                                      │
│                                      │
├─ Status Bar ──────────────────────────┤
│ Ready  Line 42, Col 8                │
└──────────────────────────────────────┘
```

### Navigation Basics

- **Cursor Movement:**
  - Arrow keys: Move one character
  - Ctrl+Left/Right: Move by word
  - Ctrl+Home/End: Start/end of document
  - Ctrl+G: Go to specific line number

- **Selection:**
  - Shift+Arrow: Select character by character
  - Shift+Ctrl+Arrow: Select word by word
  - Ctrl+A: Select all

---

## Editing Text

### Basic Editing

- **Type:** Type normally (full keyboard input)
- **Paste:** `Ctrl+V`
- **Delete:** `Delete` key or `Backspace`
- **Undo:** `Ctrl+Z`
- **Redo:** `Ctrl+Y`

### Multi-Line Editing

- **Line:** Edit by pressing Enter at line end, then modify
- **Copy/Cut:** Select line(s) and use `Ctrl+C` / `Ctrl+X`
- **Indent:** Select and press `Tab` to indent, `Shift+Tab` to unindent

### Search Within Selection

- Highlight text
- Use Find (Ctrl+H)
- Replace within selection only

---

## File Management

### Creating New Files

**Menu:** File → New (or `Ctrl+N`)

- Creates new empty tab
- Enter filename when you save (Ctrl+S)

### Opening Files

**Menu:** File → Open (or `Ctrl+O`)

Options:
1. **Browse:** Click folder icon, navigate to file
2. **Recent:** File → Open Recent (quick access)
3. **Keyboard:** `Ctrl+O`, then type path

### Saving Files

| Action | Shortcut | Menu |
|--------|----------|------|
| Save | `Ctrl+S` | File → Save |
| Save As | `Ctrl+Shift+S` | File → Save As |
| Save as Markdown | - | File → Save as Markdown |

### Auto-Save

SimpleEdit does **not** auto-save. Always manually save your work!

**Tip:** Enable syntax highlighting (Settings) to get visual feedback on file changes.

---

## Finding & Replacing

### Basic Find

**Menu:** Edit → Find/Replace (or `Ctrl+H`)

1. Enter search term
2. Click "Find Next" or "Find All"
3. Matches highlighted in editor

### Replace

1. Enter search term and replacement
2. Click "Replace" (single) or "Replace All"
3. Confirm replacements

### Advanced Options

- **Case Sensitive:** Match exact letter case
- **Whole Word:** Match complete words only
- **Regex:** Use regular expressions for pattern matching

### Go to Line

**Menu:** Edit → Go To Line (or `Ctrl+G`)

- Enter line number
- Instantly jump to that line

---

## Formatting

### Text Formatting

Select text, then apply:

| Format | Shortcut | Menu |
|--------|----------|------|
| Bold | `Ctrl+B` | Edit → Bold |
| Italic | `Ctrl+I` | Edit → Italic |
| Underline | `Ctrl+U` | Edit → Underline |
| Small | - | Edit → Small |

**Note:** Formatting is applied as tags for display. To preserve formatting when saving:
- Use File → Save as Markdown
- Or save with SIMPLEEDIT metadata header

### Toggle Formatting

Apply same formatting again to remove it (toggle behavior)

### Font Selection

**Toolbar:** Font dropdown and size dropdown

- Select font: Click dropdown, choose from available system fonts
- Select size: Click size field or dropdown
- Applies to selection (or whole document if nothing selected)

---

## Tabs & Organization

### Tab Basics

**New Tab:** Click `+` button or File → New (`Ctrl+N`)

**Close Tab:** Click `×` on tab or use File → Close Tab (`Ctrl+W`)

**Switch Tabs:** Click tab name or `Ctrl+Tab` to cycle through

### Tab Features

| Feature | Action |
|---------|--------|
| Rename tab | Double-click tab name (for display) |
| Reorder tabs | Click and drag tab left/right |
| Close one | Click `×` on specific tab |
| Close others | File → Close Other Tabs |
| Close all | File → Close All Tabs |

### Tab State

Each tab remembers:
- Filename (if saved)
- Current scroll position
- Selection
- Formatting applied

---

## Browsing Mode

### HTML/Markdown Rendering

When you open `.html`, `.md`, or `.php` files:

- **Automatic rendering:** SimpleEdit detects file type
- **Rendered view:** Shows readable plain text (not raw HTML)
- **Original preserved:** Original HTML stored internally

### Switching Views

**Menu:** Settings → Toggle Browsing Mode

- **Rendered (default):** Shows parsed plain text
- **Raw source:** Shows original HTML/Markdown

### Rendered Features

- Links appear as clickable text
- Tables displayed with structure
- Code blocks highlighted by language
- Formatting (bold, italic) applied

### Inline JavaScript

Scripts in HTML files **run automatically** when you open them:

```html
<script>
    document.getElementById('output').textContent = 'Hello!';
</script>
```

The output updates in the rendered view!

---

## Settings & Customization

### Settings Dialog

**Menu:** Settings → Settings...

Opens configuration panel with tabs:

#### Display Tab

- **Font family:** Choose from system fonts
- **Font size:** 8-72 points
- **Text color:** Hex color (e.g., `#4AF626`)
- **Background color:** Dark/light theme
- **Cursor color:** Easy to spot cursor

#### Highlighting Tab

- **Enable syntax highlighting:** Toggle on/off
- **Tag colors:** Customize keyword, string, comment colors
- **Import theme:** Load custom color schemes

#### AI Tab (if available)

- **Load model on open:** Auto-load GPT-2 model
- **Context size:** Tokens to use for autocomplete
- **Temperature:** Randomness of suggestions

#### General Tab

- **Undo enabled:** Toggle undo/redo
- **Default recent open:** New tab vs. current tab
- **Debug logging:** Enable verbose output

### Saving Settings

All settings auto-saved to `config.ini`

Changes apply immediately (no restart needed)

### Custom Colors

```ini
# In config.ini [Syntax] section
tag.keyword.fg=#FF5555
tag.string.fg=#55FF55
tag.comment.fg=#808080
```

---

## Keyboard Shortcuts Cheat Sheet

### File Operations

| Action | Shortcut |
|--------|----------|
| New file | `Ctrl+N` |
| Open file | `Ctrl+O` |
| Save | `Ctrl+S` |
| Save As | `Ctrl+Shift+S` |
| Close tab | `Ctrl+W` |

### Editing

| Action | Shortcut |
|--------|----------|
| Undo | `Ctrl+Z` |
| Redo | `Ctrl+Y` |
| Cut | `Ctrl+X` |
| Copy | `Ctrl+C` |
| Paste | `Ctrl+V` |
| Select all | `Ctrl+A` |

### Navigation

| Action | Shortcut |
|--------|----------|
| Go to line | `Ctrl+G` |
| Find/Replace | `Ctrl+H` |
| Next tab | `Ctrl+Tab` |
| Previous tab | `Ctrl+Shift+Tab` |

### Formatting

| Action | Shortcut |
|--------|----------|
| Bold | `Ctrl+B` |
| Italic | `Ctrl+I` |
| Underline | `Ctrl+U` |

### Cursor Movement

| Action | Shortcut |
|--------|----------|
| Word left | `Ctrl+Left` |
| Word right | `Ctrl+Right` |
| Line start | `Home` |
| Line end | `End` |
| Doc start | `Ctrl+Home` |
| Doc end | `Ctrl+End` |

### Selection (add Shift to move commands)

| Action | Shortcut |
|--------|----------|
| Select to word left | `Ctrl+Shift+Left` |
| Select to word right | `Ctrl+Shift+Right` |
| Select to line start | `Shift+Home` |
| Select to line end | `Shift+End` |
| Select all | `Ctrl+A` |

---

## Tips & Tricks

### Efficient Editing

1. **Use Find/Replace** for bulk changes
2. **Go to Line** for quick navigation in large files
3. **Multiple tabs** for comparing files side-by-side
4. **Copy/Paste formatting** between documents

### Working with Code

1. **Syntax highlighting** helps spot errors
2. **Save as Markdown** to export formatted code
3. **Comment with #** while reading others' code
4. **Run scripts** directly from HTML files

### Performance

- **Large files:** Disable syntax highlighting if sluggish
- **Many tabs:** Close unused tabs to free memory
- **AI features:** Disable if not using (saves RAM)

---

## See Also

- [QUICKSTART.md](QUICKSTART.md) - Get started in 5 minutes
- [SYNTAX.md](SYNTAX.md) - Syntax highlighting customization
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues
- [KEYBOARD SHORTCUTS](#keyboard-shortcuts-cheat-sheet) - Full reference
