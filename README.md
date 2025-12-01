SimpleEdit - Project Documentation
Overview
---
SimpleEdit is a Tkinter-based Python code editor featuring syntax highlighting, text formatting (bold/italic/underline), file management with MRU (Most Recently Used), optional AI autocomplete, and experimental JavaScript execution support.
Author: Joshua Richards | License: MIT | Version: 0.0.3

Core Features
1. Text Editing & Formatting
•	Syntax Highlighting - Dynamic Python code highlighting with configurable colors and keywords
•	Text Formatting - Toggle bold, italic, underline, small text on selections
•	Multiple Tabs - Open multiple files simultaneously with tabbed interface
•	Undo/Redo - Full undo/redo support (configurable via settings)
•	Find/Replace - Built-in find and replace functionality
•	Go To Line - Navigate to specific line numbers (Ctrl+G)
2. File Management
•	Save/Load - Standard file operations with error handling
•	Recent Files - MRU list with quick-open from menu (persisted to config.ini)
•	Multiple Formats - Support for plain text, HTML, Markdown, and more
•	Auto-detect - Detects HTML/Markdown content and parses to readable text
•	Markdown Export - Save with syntax highlighting as formatted Markdown or HTML
3. HTML/Markdown Rendering
•	HTML Parsing - Converts HTML fragments to readable plain text with metadata
•	Table Support - Preserves table structure with cell attributes (colspan, rowspan, alignment)
•	Code Block Syntax - <pre><code>Renders pre/code blocks with language-specific syntax highlighting</code></pre>
•	Supported languages: Python, JSON, JavaScript, HTML, YAML, C/C++, Markdown, Rathena NPC/YAML
•	Link Extraction - Captures and preserves hyperlinks with metadata
•	Whitespace Normalization - Intelligent HTML parsing that preserves content structure
4. JavaScript Execution (Experimental)
•	Script Loading - Extracts and executes script tags from HTML documents
•	jsmini Engine - Custom lightweight JavaScript interpreter
•	DOM Simulation - Basic DOM API support for element manipulation
•	Host Callbacks - Scripts can call host.setRaw() to update document content
•	JS Console - Optional popup console for script output and debugging
•	Error Context - Detailed error reporting with source code snippets
5. AI Features (Optional - requires ML dependencies)
•	AI Autocomplete - GPT-2 based code suggestion (if torch and tiktoken available)
•	Model Loading - Lazy-loads AI model with progress feedback
•	Context Window - Configurable token context (default: 512 tokens)
•	Temperature Control - Adjustable sampling temperature and top-k parameters
•	Model Management - Load/unload model from UI
•	Persistent Settings - AI preferences saved to config file
6. Configuration & Customization
•	Font Selection - Dropdown for font family and size
•	Color Scheme - Customizable colors for syntax elements (stored in config.ini)
•	Tag Colors - Per-element color configuration (keywords, strings, comments, etc.)
•	Syntax Presets - Load custom syntax highlighting rules from .ini files
•	Export CSS Modes - Choose inline, inline-block, or external CSS for HTML export
---
Test Suite
Located in PythonApplication1\tests\ directory:
Test File	Purpose
test_base.py	Core functionality tests
test_js_builtins.py	JavaScript built-in functions (alert, setTimeout, etc.)
test_js_builtins2.py	Extended JS builtins testing
test_json_reviver.py	JSON parsing and reviver pattern
test_object_helpers.py	Object manipulation utilities
test_run_scripts_update.py	Script execution and DOM handling
test_dom_events.py	DOM event dispatching
test_event_builtin.py	Event system built-ins
test_tokendiag_run_test.py	Syntax tokenization
Running Tests:

python -m pytest PythonApplication1/tests/

Usage

Starting the Application
python PythonApplication1.py

Or use the pre-built executable:
PythonApplication1.exe  # Windows (available in repo)

Basic Workflow
1.	New File - File → New or Ctrl+N
2.	Open File - File → Open or use Recent menu
3.	Edit - Type in main text area; formatting applied automatically
4.	Apply Formatting - Select text → Edit menu → choose Bold/Italic/Underline
5.	Save - File → Save or Ctrl+S
6.	Export - File → Save as Markdown (preserves syntax highlighting)
HTML/Markdown Mode
When opening .html, .md, or .php files:
•	Content is automatically parsed and displayed as readable text
•	Original HTML is preserved internally
•	Toggle between raw and rendered views via menu
JavaScript Execution
1.	Open an HTML file containing <script> tags
2.	Scripts automatically extract and execute
3.	Check Settings → Enable debug logging for detailed execution trace
4.	Output appears in optional JS Console (Settings → menu option)
AI Autocomplete
1.	Tools → Click AI Autocomplete button
2.	Model loads automatically on first use (takes ~30 seconds)
3.	Suggestion appears after loading completes
4.	Unload model via AI Unload button when not needed
Keyboard Shortcuts
Shortcut	Action
Ctrl+N	New file
Ctrl+O	Open file
Ctrl+S	Save
Ctrl+Z	Undo
Ctrl+Y	Redo
Ctrl+G	Go to line
Ctrl+W	Close tab
Ctrl+B	Toggle bold
Ctrl+I	Toggle italic
Ctrl+U	Toggle underline
---
Configuration
Config File: config.ini (created on first run)

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
jsConsoleOnRun=False
debug=False

[Recent]
files=["path/to/file1.py", "path/to/file2.html"]

[URLHistory]
urls=["https://example.com"]

Project Structure
SimpleEdit/
├── PythonApplication1.py        # Main GUI application
├── functions.py                 # Helper functions (HTML parsing, script execution)
├── jsmini.py                    # JavaScript interpreter
├── js_builtins.py               # JS built-in functions
├── model.py                     # GPT model (if ML available)
├── syntax_worker.py             # Syntax highlighting worker process
├── config.ini                   # Runtime configuration
├── tests/                       # Test suite
│   ├── test_*.py
│   └── __init__.py
└── syntax/                      # Syntax definition files
    ├── python.ini
    ├── json.ini
    ├── yaml.ini
    └── ...

Development Notes
Coding Standards (from CONTRIBUTING.md)
•	Indentation: 4 spaces
•	Naming: snake_case for functions/variables, CamelCase for classes
•	Exception Handling: Defensive, best-effort approach to keep UI responsive
•	Testing: Add tests for non-trivial logic
•	Configuration: Use explicit keys in config.ini under Section1
Key Dependencies
Required:
•	tkinter (built-in with Python)
Optional:
•	torch - AI autocomplete
•	tiktoken - AI tokenizer
•	pyinstaller - Windows executable building
Thread Safety
•	Syntax Highlighting - Runs in background worker thread
•	Script Execution - Runs in daemon thread (async by default)
•	File I/O - Threaded to keep UI responsive
•	GUI Updates - Scheduled via .after() for main thread safety
---
Known Limitations
•	AI model requires significant memory (~500MB+)
•	JavaScript interpreter is simplified; not all browser APIs available
•	HTML table editing is best-effort (metadata preserved but limited UI)
•	Syntax highlighting may lag on very large files (>50KB)
---
This documentation covers the essential features, testing approach, and usage patterns. For detailed API information, refer to docstrings in functions.py and PythonApplication1.py.
