# 🤝 Contributing to SimpleEdit

Thank you for considering contributing to SimpleEdit! This document provides guidelines and instructions for contributing.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Git Workflow](#git-workflow)
- [Reporting Issues](#reporting-issues)
- [Documentation](#documentation)

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
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 3. Install Development Dependencies

```bash
# Install test framework and tools
pip install pytest pytest-cov

# Optional: AI features (large download)
pip install torch tiktoken
```

### 4. Run Tests

```bash
# Run all tests
pytest PythonApplication1/tests/

# Run specific test file
pytest PythonApplication1/tests/test_base.py

# With coverage report
pytest --cov=PythonApplication1 PythonApplication1/tests/
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
3. **Build locally** to verify formatting (optional: `python -m http.server`)
4. **Submit PR** with improvements

---

## Code Standards

### Style Guide

Follow **PEP 8** with these specific conventions:

#### Naming

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

#### Indentation

- Use **4 spaces** (never tabs)
- No trailing whitespace

#### Comments

```python
# ✅ Good - explains WHY, not WHAT
# Guard against infinite recursion in callbacks
if depth > 500:
    raise RuntimeError("Stack overflow")

# ❌ Avoid - obvious from code
# Increment depth
depth += 1
```

#### Type Hints (where possible)

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
# ✅ Good - defensive
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

### Line Length

- Aim for **80-100 characters** per line
- Longer lines OK for URLs, strings, or complex expressions

---

## Testing

### Running Tests

```bash
# All tests
pytest

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

### Before Submitting PR

```bash
# Update your branch with latest upstream
git fetch upstream
git rebase upstream/main

# Run tests locally
pytest

# Check code style (if linter available)
flake8 PythonApplication1/

# Commit with clear message
git commit -m "Fix: description"

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

## How to Test
Steps to verify the fix works

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code follows style guide
- [ ] No new warnings from linter
```

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
├── README.md                      # Overview (in repo root)
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

## Code Review Process

### What Reviewers Look For

1. ✅ **Correctness** - Does it work? Are there edge cases?
2. ✅ **Testing** - Is it tested? Are tests comprehensive?
3. ✅ **Style** - Does it follow guidelines?
4. ✅ **Performance** - Any regressions?
5. ✅ **Documentation** - Is it documented?

### Responding to Review Feedback

- 📝 Address comments constructively
- 💬 Ask for clarification if needed
- 🔄 Make changes and push them
- ✨ Don't force-push unless asked

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
- 📧 Check [FAQ.md](FAQ.md)
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

**Thank you for contributing to SimpleEdit! 🎉**
