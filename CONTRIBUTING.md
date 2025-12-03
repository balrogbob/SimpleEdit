# 🤝 Contributing to SimpleEdit

Thank you for considering contributing to SimpleEdit! This document provides guidelines and instructions for contributing.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Code Standards](#code-standards)
- [Configuration & Preferences](#configuration--preferences)
- [Syntax Highlighting Policy](#syntax-highlighting-policy-critical)
- [Testing](#testing)
- [Git Workflow](#git-workflow)
- [Reporting Issues](#reporting-issues)
- [Documentation](#documentation)
- [JavaScript Built-ins](#javascript-built-ins-interpreter-guidance)
- [Developer Workflow](#developer-workflow)

---

## Getting Started

### Ways to Contribute

- 🐛 **Bug fixes** - Fix reported issues
- ✨ **New features** - Add requested functionality
- 📖 **Documentation** - Improve guides and examples
- ✅ **Tests** - Add test coverage
- 🎨 **Syntax highlighting** - Add language support
- 💬 **Feedback** - Report issues and suggest improvements

### Prerequisites

- Python 3.8+
- Git
- Basic understanding of Python and Tkinter (for GUI changes)

### Core Principles

This repository follows a small set of UI and editor behavior invariants that must be preserved by all code changes. The goal is predictable editor UX and avoiding surprising global side-effects caused by syntax preset application.

- **Keep changes small and focused.** Open a pull request with a clear title and description.
- **Add or update tests** for non-trivial logic when possible.
- **Preserve existing public behavior** unless explicitly changing defaults; document any behavioral changes in the PR description.
- **Keep UI text and error messages** clear and user-friendly.
- **Respect invariants** documented below (especially Syntax Highlighting Policy).

---

## Development Setup

### 1. Fork and Clone

```bash
# Fork on GitHub, then:
git clone https://github.com/YOUR-USERNAME/SimpleEdit.git
cd SimpleEdit
git remote add upstream https://github.com/balrogbob/SimpleEdit.git
```

### 2. Create Development Branch

```bash
# For JavaScript/HTML work, branch from beta-javascript-support:
git checkout -b feature/your-feature-name beta-javascript-support

# Or branch from main for other work:
git checkout -b fix/issue-description main
```

### 3. Install Development Dependencies

```bash
# Basic installation (editor works without ML)
python PythonApplication1/PythonApplication1.py

# Install test framework
pip install pytest pytest-cov

# Optional: AI features (large download ~2GB)
pip install torch tiktoken

# Optional: Code formatting/linting
pip install black flake8
```

### 4. Run Tests

```bash
# Run all tests
pytest PythonApplication1/tests/

# Run specific test file
pytest PythonApplication1/tests/test_base.py

# Run specific test
pytest PythonApplication1/tests/test_base.py::test_tokenize_numbers

# With coverage report
pytest --cov=PythonApplication1 PythonApplication1/tests/

# Verbose output
pytest -v
```

---

## How to Contribute

### Bug Fixes

1. **Find an issue** on [GitHub Issues](https://github.com/balrogbob/SimpleEdit/issues?state=open)
2. **Create a branch:** `git checkout -b fix/issue-123`
3. **Make changes** - See [Code Standards](#code-standards) below
4. **Add tests** if fixing a bug with reproducible steps
5. **Open a PR** with description of the fix

### New Features

1. **Open an issue first** to discuss the feature
2. **Wait for approval** (or start if the issue is labeled `help wanted`)
3. **Create a branch:** `git checkout -b feature/awesome-feature`
4. **Implement feature** - Start small and iterate
5. **Add tests** for the new functionality
6. **Open a PR** with before/after examples

### Documentation

1. **Identify gaps** - Check existing docs in `PythonApplication1/docs/`
2. **Create or update** the relevant `.md` file
3. **Build locally** to verify formatting
4. **Submit PR** with improvements

---

## Code Standards

### General Principles

- **Follow Python idioms** consistent with the existing codebase
- **Use 4-space indentation** (never tabs)
- **Keep functions small and focused;** prefer helper functions for repeated logic
- **Preserve the project's exception-handling style** (defensive, best-effort to keep UI responsive)
- **Use descriptive variable and function names.** Prefer `snake_case` for functions/variables and `CamelCase` for classes
- **Avoid global side-effects** when making per-tab visual changes. Prefer per-frame / per-widget transient state
- **Always keep code style consistent** with `.editorconfig` (when present)

### Naming Conventions

```python
# ✅ Good
def calculate_syntax_highlighting(text):
    pass

class TokenParser:
    pass

BUFFER_SIZE = 1024
_private_helper = None

# ❌ Avoid
def calc_syntax_high(text):
    pass

class tokenParser:
    pass

buffersize = 1024
PRIVATE_HELPER = None
```

### Indentation & Formatting

- Use **4 spaces** (never tabs)
- No trailing whitespace
- Aim for **80-100 characters** per line (longer lines OK for URLs, strings, complex expressions)

### Comments

```python
# ✅ Good - explains WHY, not WHAT
# Guard against infinite recursion in callbacks
if depth > 500:
    raise RuntimeError("Stack overflow")

# ❌ Avoid - obvious from code
# Increment depth
depth += 1
```

### Type Hints (where possible)

```python
# ✅ Good - type hints clarify intent
def tokenize(src: str) -> List[Tuple[str, str]]:
    pass

# ❌ Avoid - no hints
def tokenize(src):
    pass
```

### Defensive Programming

SimpleEdit prioritizes robustness:

```python
# ✅ Good - defensive, logs issues
try:
    result = func(value)
except Exception:
    # Best-effort: log and continue
    print(f"Warning: {value} failed")
    result = None

# ❌ Avoid - crashes on error
result = func(value)
```

### Exception Handling

```python
# ✅ Good - specific exceptions
try:
    config.set("Section1", "value", setting)
except configparser.Error as e:
    print(f"Config error: {e}")
except Exception:
    pass  # Defensive fallback

# ❌ Avoid - swallows errors silently
try:
    config.set("Section1", "value", setting)
except:
    pass
```

---

## Configuration & Preferences

Project-wide runtime settings live in `config.ini` under the `Section1` header. When adding a new configurable behavior:

1. Use an explicit key under `Section1`
2. Provide a reasonable default in the code and the `DEFAULT_CONFIG` structure in `functions.py`
3. Do not modify or remove mandatory configuration keys without migration and clear documentation
4. Update the Settings UI so users can edit new preferences via the dialog

### Example: `renderOnOpenExtensions` Preference

```ini
[Section1]
renderOnOpenExtensions=html,htm,md,markdown,php,js
```

- **Type:** comma-separated string
- **Default:** `html,htm,md,markdown,php,js`
- **Purpose:** Lists file extensions (without leading dots) that should default to the "Rendered" view when opened. Files matching these extensions and any URL-like location (`http://`, `https://`, `file://`, or `www.`) will default to rendered mode unless the user checks "Open as source" or uses the per-tab override.

### Behavioral Notes

- When a tab is in Rendered view (parsed HTML/MD/markup display), the standard worker-driven syntax highlighter is disabled to avoid conflicts with the rendering engine
- Users can still toggle between Raw and Rendered view per-tab
- Changes that alter the default set of extensions should update `DEFAULT_CONFIG` in `functions.py` and the Settings UI

---

## Syntax Highlighting Policy (CRITICAL)

This project enforces a strict rule:

**Syntax highlighting MUST NEVER be applied while a tab is in Rendered view** (i.e. when the tab/frame property `_view_raw` is False).

### Details

- **"Rendered view"** refers to the editor state where parsed HTML/Markdown has been converted to a presentational form and is being displayed. The frame attribute `_view_raw` indicates raw/source vs rendered state. When `_view_raw` is False, the tab is Rendered.

- **Under no circumstance** should any syntax tags (e.g., `string`, `keyword`, `comment`, `html_tag`, `html_attr`, `table`, etc.), transient preset colors, or regex-based highlighting be applied to a Text widget showing Rendered content.

- **Detection (auto-detect presets)** MAY run in the background for convenience, but it MUST NOT apply presets to widgets in Rendered view. If detection finds a matching preset for a rendered document, the code SHOULD store the detected preset path on the frame (e.g., `frame._detected_syntax_preset`) or on root for later manual application. It should NOT call functions that configure tags on the Text widget, and it should NOT mutate the global `config` via `apply_syntax_preset()` while the tab is rendered.

- **When a user switches a rendered tab to Raw/Source view** (via toggle), any stored detected preset may be applied at that point if the user requests it or as explicitly permitted by user-configured options. Only then may transient or persistent syntax tag configs be applied to the Text widget.

- **All code paths** that open content (file dialog, URL bar, hyperlink click, history/back/refresh, templates) must respect this rule. This includes both immediate application and transient application on new tab creation.

### Rationale

Applying syntax highlighting while the editor is showing a Rendered representation produces confusing UI: highlighting may change the visual appearance of parsed HTML, and persistent config changes can surprise users when following hyperlinks or toggling views. This rule preserves a clear separation between presentational rendering and source-mode editing.

---

## Implementation Guidance

When making code changes, follow these concrete rules:

1. **`apply_syntax_preset_transient(path, text_widget)`** MUST return without configuring the widget if the target widget's parent frame reports `_view_raw == False`. The function may still record the detected preset on the frame for later application.

2. **Calls to `apply_syntax_preset(...)`** (persistent apply to global config) MUST NOT be invoked for content opened in rendered mode. Instead, detected presets may be stored for later use (e.g., `frame._detected_syntax_preset`).

3. **`manual_detect_syntax()` and UI-driven detection flows** must respect the frame's `_view_raw` state and only apply transient/persistent presets when the frame is in Raw/Source mode.

4. **`highlight_python_helper()`, `safe_highlight_event()`, and other highlighter entry points** already short-circuit when `_view_raw` is False; ensure no other code path configures tags unconditionally.

5. **If a code path currently applies transient presets** when opening a URL/file in a new tab (e.g., `open_url_action()`, `fetch_and_open_url()`, `_open_path()`), update it to either:
   - Only apply transient presets when the new tab is opened in Raw/Source mode; or
   - Store the detected preset on the frame (e.g., `fr._detected_syntax_preset = path`) and set a status message indicating the preset is detected but suppressed for Rendered view.

---

## Testing

### Running Tests

```bash
# All tests
pytest PythonApplication1/tests/

# Specific test file
pytest PythonApplication1/tests/test_base.py

# Specific test
pytest PythonApplication1/tests/test_base.py::test_tokenize_numbers

# Verbose output
pytest -v

# With coverage
pytest --cov=PythonApplication1
```

### Writing Tests

Create test files in `PythonApplication1/tests/` following pattern `test_*.py`:

```python
import pytest
from PythonApplication1 import jsmini, functions

class TestTokenizer:
    """Tests for JavaScript tokenizer."""
    
    def test_tokenize_numbers(self):
        """Should recognize various number formats."""
        tokens = jsmini.tokenize("42 3.14 1e10 0xFF")
        numbers = [t for t in tokens if t[0] == 'NUMBER']
        assert len(numbers) == 4
    
    def test_tokenize_strings(self):
        """Should handle escaped quotes."""
        tokens = jsmini.tokenize(r'"He said \"Hi\""')
        strings = [t for t in tokens if t[0] == 'STRING']
        assert len(strings) == 1
    
    @pytest.mark.skip(reason="TODO: implement")
    def test_regex_literals(self):
        """Regex literal detection - needs context awareness."""
        pass
```

### Test Requirements

Add unit or manual tests validating:

- **All open flows** (File → Open modal, URL dialog, hyperlink clicks, history/back/refresh) do not apply syntax tags on tabs that end up in Rendered mode
- **Preset detection** for rendered pages is only applied after switching the tab to Raw/Source view (and not before)
- **Edge cases** in new functionality

Use **unittest-compliant testing** scripts in `tests/` for easier testing across multiple vectors:

```bash
python -m unittest discover PythonApplication1/tests
```

### Test Organization

```
tests/
├── test_base.py                 # Parser, tokenizer basics
├── test_js_builtins.py          # Array, Object, JSON methods
├── test_dom_events.py           # DOM and event system
├── test_run_scripts_update.py   # Full script execution
└── test_object_helpers.py       # Edge cases, type coercion
```

---

## Git Workflow

### Commit Messages

Write clear, concise commit messages:

```
# ✅ Good
Fix regex literal detection in tokenizer

The tokenizer was incorrectly treating /pattern/ as division
when it followed assignment operators. Added context-aware
heuristic to detect regex literals by examining previous token.

Fixes #42

# ❌ Avoid
fixed stuff
bugfix
update
```

### Developer Workflow

- **Branch from `beta-javascript-support`** for JS/HTML related work
- **Branch from `main`** for other work
- **Run the app and manually test** open/save flows for both local files and URLs
- **If adding a new config key:**
  - Update `DEFAULT_CONFIG` in `functions.py`
  - Add UI to `Settings` where appropriate
- **If modifying detection or apply flows:**
  - Update this document accordingly
  - When in doubt, prefer *not applying* highlighting in Rendered mode

### Before Submitting PR

```bash
# Update your branch with latest upstream
git fetch upstream
git rebase upstream/beta-javascript-support  # or main

# Run tests locally
pytest

# Check code style (if linter available)
flake8 PythonApplication1/

# Commit with clear message
git commit -m "fix: clear description"

# Push to your fork
git push origin feature/your-feature
```

### Pull Request Template

When opening a PR, include:

```markdown
## Description
Brief explanation of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Performance improvement

## Related to Rendered/Raw View?
- [ ] Touches syntax highlighting
- [ ] Affects Rendered view behavior
- [ ] Modifies configuration

## How to Test
Steps to verify the fix works

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code follows style guide
- [ ] No new warnings from linter
- [ ] Syntax highlighting policy respected
```

### Code Review Process

**What Reviewers Look For:**

1. ✅ **Correctness** - Does it work? Are there edge cases?
2. ✅ **Testing** - Is it tested? Are tests comprehensive?
3. ✅ **Style** - Does it follow guidelines?
4. ✅ **Performance** - Any regressions?
5. ✅ **Policy** - Does it respect Syntax Highlighting Policy and other invariants?
6. ✅ **Documentation** - Is it documented?

**Responding to Review Feedback:**

- 📝 Address comments constructively
- 💬 Ask for clarification if needed
- 🔄 Make changes and push them
- ✨ Don't force-push unless asked

---

## Reporting Issues

### Bug Report Template

When reporting bugs, include:

```markdown
## Describe the Bug
Clear description of what's broken

## To Reproduce
1. Open SimpleEdit
2. File → Open
3. Select large HTML file
4. ...

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: Windows 10 / macOS / Linux
- Python version: 3.9
- SimpleEdit version: 0.0.3

## Screenshots/Logs
Error messages or screenshots
```

### Feature Request Template

```markdown
## Description
What feature would be useful?

## Motivation
Why do you need it?

## Example Usage
How would it be used?

## Alternatives
Other ways to achieve this?
```

---

## Documentation

### Guidelines

- Use **Markdown** (.md files)
- Keep explanations **clear and concise**
- Include **code examples** for features
- Add **tables** for reference material
- Link to related documentation

### Structure

```
PythonApplication1/docs/
├── README.md                      # Overview
├── QUICKSTART.md                  # 5-minute intro
├── INSTALLATION.md                # Setup instructions
├── API.md                         # API reference
├── SYNTAX.md                      # Syntax highlighting
├── JSMINI.md                      # JS engine docs
├── development-process.md         # How jsmini was built
├── CONTRIBUTING.md                # This file
├── ARCHITECTURE.md                # System design
├── EDITOR-USAGE.md                # User guide
├── TROUBLESHOOTING.md             # Common issues
├── EXAMPLES.md                    # Practical recipes
├── FAQ.md                         # Q&A
├── PERFORMANCE-TUNING.md          # Optimization
└── WINDOWS-BUILD.md               # Building .exe
```

### Documentation Checklist

For new features, ensure:

- [ ] Feature documented in relevant `.md` file
- [ ] Code examples provided
- [ ] Edge cases mentioned
- [ ] Related features linked

---

## JavaScript Built-ins (Interpreter Guidance)

When adding built-in JavaScript objects or functions (e.g., `Array`, `Object`, `Date`) to the jsmini interpreter, follow these project patterns:

### Implementation Guidelines

- **Implement small, focused native implementations** as Python callables or as `JSFunction` instances with a `native_impl` when constructor/`new` semantics are required
- **Attach a plain-dict `prototype` object** to `JSFunction` instances and set instance `__proto__` when `new` is used. Store prototype methods as callables on the prototype dict
- **Prefer implementing prototype methods as Python callables** and ensure the evaluator passes the correct `this` value when invoking methods (member calls should set `this` to the object)
- **Keep behavior conservative and documented:** Full ECMAScript semantics are not required; implement the subset needed by the libraries you intend to run (e.g., `Array.prototype.push`, `pop`, `length` semantics; `Object.create`, `Object.keys`)
- **Add small unit tests** for any non-trivial native implementation and document edge-cases in the PR

### Recommended Location and Structure

For best practices, keep the interpreter core (`jsmini.py`) focused on parsing and evaluation. Place built-in implementations in a separate module and register them from `make_context()`:

```python
# In PythonApplication1/js_builtins.py
def register_builtins(context: Dict[str, Any], JSFunction):
    """Register JavaScript standard library into context."""
    
    # Create Array constructor
    Arr = JSFunction('Array', native_impl=_array_ctor)
    Arr.prototype['push'] = JSFunction('push', native_impl=_array_push)
    Arr.prototype['pop'] = JSFunction('pop', native_impl=_array_pop)
    context['Array'] = Arr
    
    # Create Object constructor
    Obj = JSFunction('Object', native_impl=_object_ctor)
    Obj['create'] = JSFunction('create', native_impl=_object_create)
    Obj['keys'] = JSFunction('keys', native_impl=_object_keys)
    context['Object'] = Obj
    
    # etc.
```

**In `jsmini.py` `make_context()`:**

```python
def make_context(log_fn=None):
    context = {
        'console': {'log': log_fn or print},
        'document': make_dom_shim(),
        # ... other globals
    }
    
    # Register JavaScript built-ins
    from PythonApplication1.js_builtins import register_builtins
    register_builtins(context, JSFunction)
    
    return context
```

This keeps `make_context()` readable while keeping built-in logic modular.

### Testing & Documentation

- **Tests:** Put unit tests under `tests/` at repo root (preferred) or under `PythonApplication1/tests/`
  - Example: `tests/test_js_builtins.py` with small scripts executed via `jsmini.run()` and assertions of returned or logged values
  
- **Documentation:** Document registered built-ins in this file and add small examples in `PythonApplication1/examples/` or `run_jsmini_demo.py`

---

## Tooling

We maintain a small set of helper scripts in the repository for diagnostic and development tasks. Tools should be small, dependency-free where possible, and placed in the repository root or the `PythonApplication1` package when they import project modules.

### Available Tools

- **`tokendiag.py`** — A minimal CLI utility to fetch a JS file (HTTP or local path) and run the project's `jsmini` tokenizer/parser diagnostics

  **Usage examples:**
  ```bash
  python -u tokendiag.py -src=http://example.com/jquery.js
  python -u tokendiag.py -file=path/to/file.js --dump-tokens 215
  ```

### Tooling Guidelines

- **Prefer using project's internal diagnostic helpers** (e.g., `jsmini.diagnose_parse()`) so diagnostics match runtime behavior
- **Keep CLI options simple** and document usage in the script header and this file
- **Avoid heavy third-party dependencies** for small utilities; prefer `urllib.request`, `argparse`, and standard library modules

---

## Development Tips

### Useful Tools

```bash
# Format code
black PythonApplication1/

# Check style
flake8 PythonApplication1/

# Find type errors (if you add type hints)
mypy PythonApplication1/

# Profile performance
python -m cProfile -s cumulative PythonApplication1/PythonApplication1.py
```

### Debugging

```python
# Add debug output
print(f"[DEBUG] variable={variable}")

# Conditional breakpoint (if using IDE)
import pdb; pdb.set_trace()

# Enable debug logging in SimpleEdit
from functions import set_debug_default
set_debug_default(True)
```

### Running Specific Features

```python
# Test jsmini directly
import jsmini
result = jsmini.run("2 + 2")

# Test HTML parsing
from functions import _parse_html_and_apply
plain, meta = _parse_html_and_apply("<p>Hello</p>")

# List available tests
python -m pytest --collect-only
```

---

## Areas for Contribution

### High-Priority Items

- 🐛 Bug fixes from [open issues](https://github.com/balrogbob/SimpleEdit/issues)
- ✅ Test coverage expansion
- 📖 Documentation improvements
- 🎨 New language syntax highlighting

### Good First Issues

Look for issues labeled:
- `good first issue`
- `help wanted`
- `documentation`

---

## Questions?

- 💬 Open a [GitHub Discussion](https://github.com/balrogbob/SimpleEdit/discussions)
- 📧 Check [docs/FAQ.md](PythonApplication1/docs/FAQ.md)
- 🔍 Search existing [Issues](https://github.com/balrogbob/SimpleEdit/issues)

---

## Code of Conduct

- Be respectful and inclusive
- Welcome diverse perspectives
- Focus on the code, not the person
- Help others learn and improve

---

## License

By contributing, you agree your contributions will be licensed under the **MIT License** (same as SimpleEdit).

---

## Notes for Contributors

- **If you modify detection or apply flows,** update this document accordingly
- **When in doubt,** prefer *not applying* highlighting in Rendered mode; store the detected preset for an explicit later application instead
- **If you're unsure about a change** or need help testing, open an issue or contact the maintainers via GitHub

---

**Thank you for contributing to SimpleEdit! 🎉**
