# 📚 Examples & Recipes

Practical examples and recipes for using SimpleEdit.

---

## Table of Contents

- [Text Editing](#text-editing)
- [Working with Code](#working-with-code)
- [HTML & Markdown](#html--markdown)
- [JavaScript Execution](#javascript-execution)
- [Advanced Workflows](#advanced-workflows)

---

## Text Editing

### Example 1: Format a Code Block

**Task:** Make Python function definition bold and italic

**Steps:**
1. Open Python file
2. Select: `def my_function(x):`
3. Press `Ctrl+B` to make bold
4. Press `Ctrl+I` to make italic
5. Save as Markdown to preserve formatting

---

## Working with Code

### Example 2: Find All Undefined Variables

**Task:** Find all uses of variable `x` in large file

**Steps:**
1. Press `Ctrl+H` (Find & Replace)
2. Enter search: `\bx\b` (regex for whole word)
3. Enable "Regex" checkbox
4. Click "Find All"
5. All matches highlighted

**Result:** Quickly identify variable usage patterns

### Example 3: Batch Rename Function

**Task:** Rename `old_func` to `new_func` everywhere

**Steps:**
1. Press `Ctrl+H` (Find & Replace)
2. Search: `old_func`
3. Replace with: `new_func`
4. Click "Replace All"
5. Verify changes

---

## HTML & Markdown

### Example 4: Create a Simple Web Page

**Create file:** `page.html`

**Content:**
```html
<html>
<head>
    <title>My Page</title>
</head>
<body>
    <h1>Welcome</h1>
    <p>This is my page!</p>
    
    <h2>Features</h2>
    <ul>
        <li>Feature 1</li>
        <li>Feature 2</li>
    </ul>
</body>
</html>
```

**Result:** Open file → SimpleEdit renders as readable text

### Example 5: Export Code as Markdown

**Task:** Document Python code with formatting

**Steps:**
1. Open Python file
2. Select function you want to document
3. Format with `Ctrl+B`, `Ctrl+I`, `Ctrl+U`
4. Use File → Save as Markdown
5. Open `.md` file in another editor or Markdown viewer

---

## JavaScript Execution

### Example 6: Auto-Execute JavaScript in HTML

**Create file:** `demo.html`

**Content:**
```html
<!DOCTYPE html>
<html>
<body>
    <h1 id="title">Loading...</h1>
    <div id="content"></div>
    
    <script>
        // This runs automatically when you open in SimpleEdit!
        var title = document.getElementById('title');
        title.textContent = 'Hello from JavaScript!';
        
        var content = document.getElementById('content');
        content.textContent = 'Script executed successfully';
    </script>
</body>
</html>
```

**Result:** Open file → JavaScript runs → DOM updates show in editor

### Example 7: Interactive Content Generation

**Create file:** `interactive.html`

**Content:**
```html
<html>
<body>
    <h1>Generated List</h1>
    <ul id="list"></ul>
    
    <script>
        var items = ['Apple', 'Banana', 'Cherry'];
        var list = document.getElementById('list');
        
        items.forEach(function(item) {
            var li = document.createElement('li');
            li.textContent = item;
            list.appendChild(li);
        });
        
        // Update page in SimpleEdit
        host.setRaw(document.body.innerHTML);
    </script>
</body>
</html>
```

**Result:** Rendered view shows dynamically generated list

### Example 8: JavaScript Debugging

**Create file:** `debug.html`

**Content:**
```html
<html>
<body>
    <h1>Debug Output</h1>
    <pre id="output"></pre>
    
    <script>
        console.log('Script started');
        
        try {
            var data = {x: 1, y: 2};
            var json = JSON.stringify(data);
            console.log('JSON:', json);
            console.log('Parsed:', JSON.parse(json));
        } catch(e) {
            console.error('Error:', e);
        }
        
        console.log('Script finished');
        
        // Show console output
        var output = document.getElementById('output');
        output.textContent = 'Check console for debug output';
    </script>
</body>
</html>
```

**Enable debugging:**
1. Settings → Enable debug logging
2. Or: Settings → Install JS Console
3. Open HTML file
4. Check Output window for console messages

---

## Advanced Workflows

### Example 9: Multi-Tab Project Workflow

**Scenario:** Working on interconnected files

**Setup:**
1. Open `main.py` (Tab 1)
2. Open `utils.py` (Tab 2)
3. Open `test.py` (Tab 3)
4. Open `README.md` (Tab 4)

**Workflow:**
- `Ctrl+Tab` to switch between tabs
- Edit in one file, refer to another
- Save each tab with `Ctrl+S`
- Quick access via Recent files

### Example 10: Compare Two Files

**Task:** Compare two versions side-by-side

**Setup:**
1. Open `version1.py` in Tab 1
2. Open `version2.py` in Tab 2
3. Resize window to see both at once:
   - Move divider between code and OS
   - Use Alt+Tab to switch editor windows

**Find differences:**
1. In Tab 2, use `Ctrl+H` to find differences
2. Use `Ctrl+G` to jump to specific lines
3. Verify changes

### Example 11: Document Code While Reading

**Task:** Read and annotate someone's code

**Steps:**
1. Open source code file
2. Select text that needs documentation
3. Press `Ctrl+B` to highlight important sections
4. Add comments above complex logic
5. Format with italics for explanations
6. Save as Markdown for documentation

### Example 12: Format and Export Documentation

**Task:** Create formatted API documentation

**Steps:**
1. Create file `api.md`
2. Write Markdown:
   ```markdown
   # API Documentation
   
   ## Function: calculate()
   
   **Parameters:**
   - `x` (int): Input value
   - `y` (int): Another value
   
   **Returns:**
   - Result (int): Sum of x and y
   
   **Example:**
   ```python
   result = calculate(5, 3)  # Returns 8
   ```
   ```

3. Save and View → Open in Markdown viewer

---

## Tips

- **Combine features:** Use Find/Replace + Formatting + Export for powerful workflows
- **Save often:** Use `Ctrl+S` frequently
- **Recent files:** File → Open Recent for quick access
- **Keyboard efficiency:** Learn shortcuts to edit faster
- **Organize with tabs:** Keep related files open together

---

## See Also

- [EDITOR-USAGE.md](EDITOR-USAGE.md) - Full feature guide
- [QUICKSTART.md](QUICKSTART.md) - Getting started
- [JSMINI.md](JSMINI.md) - JavaScript engine capabilities
