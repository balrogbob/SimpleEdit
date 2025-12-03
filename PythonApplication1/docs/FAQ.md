# ❓ Frequently Asked Questions

Common questions about SimpleEdit and answers.

---

## General Questions

### What is SimpleEdit?

SimpleEdit is a **lightweight Python code editor** built with Tkinter. It features:
- Syntax highlighting for 10+ languages
- HTML/Markdown rendering and parsing
- Experimental JavaScript execution
- Optional AI-powered code suggestions (GPT-2)

### Why would I use SimpleEdit instead of VS Code?

**SimpleEdit advantages:**
- ✅ Lightweight (no Electron, just Python)
- ✅ Renders HTML/Markdown directly in editor
- ✅ Can run JavaScript from HTML files
- ✅ Fast startup (< 1 second)
- ✅ Small download (~30 MB exe or source)
- ✅ Pure Python (modifiable)

**VS Code advantages:**
- ✅ Larger ecosystem of extensions
- ✅ More mature language support
- ✅ Built-in debugging
- ✅ More configured settings

**TL;DR:** Use SimpleEdit if you like lightweight, quick startup. Use VS Code if you need advanced IDE features.

### Is SimpleEdit production-ready?

**Current status:** Experimental / Hobby Project

SimpleEdit is stable for:
- ✅ Reading and editing code
- ✅ Formatting and syntax highlighting
- ✅ Rendering HTML/Markdown
- ✅ Running simple scripts

Not recommended for:
- ❌ Large projects (use VS Code, JetBrains, etc.)
- ❌ Complex debugging workflows
- ❌ Mission-critical development

### How much does SimpleEdit cost?

**Free!** Licensed under MIT. You can:
- Download and use for free
- Modify the source code
- Distribute your modifications (must preserve license)

---

## Installation & Setup

### What are the system requirements?

**Minimum:**
- Python 3.8+ (if running from source)
- Or Windows 7+ / Linux / macOS with the .exe

**Recommended:**
- Python 3.10+
- 2GB+ RAM
- 100MB+ disk space

### Can I run SimpleEdit on macOS?

**Yes!** Two options:

1. **Source:** `python3 PythonApplication1/PythonApplication1.py`
2. **Via Homebrew:** `brew install python3`, then run above

No native macOS app yet, but source runs fine.

### Can I run SimpleEdit on Linux?

**Yes!** Install Python and Tkinter:

**Ubuntu/Debian:**
```bash
sudo apt-get install python3 python3-tk
python3 PythonApplication1/PythonApplication1.py
```

**Fedora:**
```bash
sudo dnf install python3 python3-tkinter
python3 PythonApplication1/PythonApplication1.py
```

### Do I need Python installed to run the .exe?

**No!** The Windows `.exe` includes Python. Just download and double-click.

---

## Features & Usage

### Can I use SimpleEdit to edit large files?

**Yes, but...** Syntax highlighting may lag on files > 50KB.

**Solution:** Disable syntax highlighting:
- Settings → uncheck "Syntax Highlighting"
- Or see [PERFORMANCE-TUNING.md](PERFORMANCE-TUNING.md)

### Does SimpleEdit support plugins/extensions?

**Not yet.** The codebase is designed to be hacked on directly:
- Fork the repo
- Modify Python source
- Contribute back if useful

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Can I use SimpleEdit as a library?

**Yes!** You can import and use components:

```python
import jsmini
result = jsmini.run("2 + 2")  # Returns 4.0

from functions import _parse_html_and_apply
plain, meta = _parse_html_and_apply("<p>Hello</p>")
```

See [API.md](API.md) for full library documentation.

### How do I customize syntax highlighting?

Edit `config.ini` under `[Syntax]` section:

```ini
[Syntax]
tag.keyword.fg=#FF0000
tag.string.fg=#00FF00
```

Or use Settings → Settings... → Highlighting tab.

See [SYNTAX.md](SYNTAX.md) for complete guide.

---

## JavaScript & Execution

### Can I run JavaScript?

**Yes!** Open an HTML file with `<script>` tags, and scripts run automatically.

```html
<script>
    console.log('Hello');
    document.body.textContent = 'JavaScript executed!';
</script>
```

### Is the JavaScript interpreter a full JS engine?

**No.** jsmini is a simplified interpreter supporting:
- ✅ ES5 syntax
- ✅ Most common methods (Array, Object, JSON)
- ✅ Basic DOM API
- ❌ Promises, async/await (parsed but not truly async)
- ❌ Regex execution (regex literals are strings)
- ❌ Most ES6+ features

See [JSMINI.md](JSMINI.md) for full capabilities.

### Will it run arbitrary JavaScript from the web?

**Probably not.** jsmini is **not sandboxed** and **not production-safe**:
- ❌ Don't run untrusted scripts
- ⚠️ Use only for scripts you wrote or trust

It's designed for local automation, not web security.

### How do I debug JavaScript?

Enable debug logging:
- Settings → Enable debug logging
- Or: Settings → Install JS Console menu

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md#javascript-execution) for details.

---

## AI Features

### What is the AI Autocomplete feature?

Optional experimental feature using GPT-2:
- Click "AI Autocomplete" button
- Model loads (~30 seconds first time)
- Suggests code completions based on context

**Note:** Requires `torch` and `tiktoken` (large downloads).

### How do I enable AI?

```bash
pip install torch tiktoken
```

Then: Click "AI Autocomplete" button in toolbar.

### Is the AI good?

**It's okay for simple suggestions.** GPT-2 is older (2019):
- ✅ Decent for simple patterns
- ❌ Not as good as modern models (GPT-3, Copilot)
- ❌ No context about your project

Use for inspiration, not production code generation.

### Can I use a different model?

**Yes, modify `model.py`.** But:
- Would require major refactoring
- No support currently provided
- Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md)

### How much disk space does the AI model use?

**~500MB** for the model download (~1GB for dependencies).

---

## File Format & Compatibility

### What file formats does SimpleEdit support?

**Text-based files:**
- ✅ `.py` (Python)
- ✅ `.js` (JavaScript)
- ✅ `.html`, `.htm` (HTML)
- ✅ `.md`, `.markdown` (Markdown)
- ✅ `.json` (JSON)
- ✅ `.yaml`, `.yml` (YAML)
- ✅ `.c`, `.cpp`, `.cs`, `.java` (Various languages)
- ✅ `.txt` (Plain text)

**Binary files:**
- ❌ Images, PDFs, Word docs (open as text, unreadable)

### Does SimpleEdit preserve formatting when I save?

**Not by default.** To preserve formatting:
- Use File → Save as Markdown
- Or enable "Save Formatting in File" (Settings) to embed metadata

### Can I convert documents to Markdown?

**Yes!** File → Save as Markdown exports with formatting preserved.

---

## Performance

### Why is SimpleEdit slow on large files?

**Syntax highlighting** is the usual culprit.

**Solution:**
- Disable highlighting: Settings → uncheck "Syntax Highlighting"
- Or split file into smaller chunks
- See [PERFORMANCE-TUNING.md](PERFORMANCE-TUNING.md)

### Why does it use so much memory?

**Common reasons:**
1. **Many tabs open** → Close unused tabs
2. **AI model loaded** → Click "AI Unload" button
3. **Very large file** → Split into smaller files
4. **Syntax highlighting** → Disable for large files

### How can I make it faster?

See [PERFORMANCE-TUNING.md](PERFORMANCE-TUNING.md) for optimization tips.

---

## Contributing & Development

### How can I contribute?

See [CONTRIBUTING.md](CONTRIBUTING.md) for full guide. Quick version:

1. Fork repo on GitHub
2. Create feature branch: `git checkout -b feature/my-feature`
3. Make changes and test
4. Submit pull request
5. Wait for review and feedback

**Areas needing help:**
- 🐛 Bug fixes
- ✨ New features
- 📖 Documentation
- ✅ Tests

### Can I use SimpleEdit code in my project?

**Yes!** Licensed under MIT:
- ✅ Use in commercial projects
- ✅ Modify the code
- ✅ Distribute modified versions
- ⚠️ Must include MIT license notice

See [LICENSE.txt](../LICENSE.txt) for details.

### Is the project actively maintained?

**Current status:** Active, but not a full-time project.

Expect:
- ✅ Bug fixes
- ✅ Community contributions welcome
- ⚠️ May be slow to review PRs (depends on schedule)

See [GitHub Issues](https://github.com/balrogbob/SimpleEdit/issues) for current activity.

---

## Getting Help

### I found a bug. How do I report it?

[Open GitHub Issue](https://github.com/balrogbob/SimpleEdit/issues/new?template=bug_report.md)

Include:
- OS and Python version
- Steps to reproduce
- Error messages/screenshots
- Expected vs. actual behavior

### I have a feature request.

[Open GitHub Discussion](https://github.com/balrogbob/SimpleEdit/discussions/new)

Or [GitHub Issue](https://github.com/balrogbob/SimpleEdit/issues/new?template=feature_request.md)

### Where's the documentation?

**Main docs:** [PythonApplication1/docs/](../)

- 📖 [API Reference](API.md)
- 🎨 [Syntax Highlighting](SYNTAX.md)
- ⚙️ [JavaScript Engine](JSMINI.md)
- 🚀 [Quick Start](QUICKSTART.md)
- And 6 more...

### Can I get help on Discord/Slack?

**Not currently.** But you can:
- Open GitHub issue/discussion
- Email: Check repo for contact info
- Read existing documentation

---

## Miscellaneous

### Who created SimpleEdit?

**Joshua Richards** as a personal weekend project.

See [development-process.md](development-process.md) for the story of how jsmini (the JS interpreter) was built.

### What does "SimpleEdit" mean?

Simple + Edit = A simple editor. The name reflects the philosophy: lightweight, straightforward, easy to understand.

### Why is it called "0.0.3"?

Version scheme:
- MAJOR.MINOR.PATCH
- Still pre-1.0 = experimental
- Versions increment as features stabilize

### Can I donate to SimpleEdit?

Currently no donation mechanism. **Best support:**
- ⭐ Star on GitHub
- 🐛 Report bugs
- 💬 Contribute code/docs
- 📢 Tell others about it!

### Is there a roadmap?

No formal roadmap, but ideas for future work:
- Generators & Promises in jsmini
- Better regex support
- More language syntax highlighting
- Performance optimizations
- UI improvements

See [GitHub Issues](https://github.com/balrogbob/SimpleEdit/issues?q=is%3Aopen+label%3Aenhancement) for "enhancement" ideas.

---

## Still Have Questions?

- 🔍 Search [GitHub Issues](https://github.com/balrogbob/SimpleEdit/issues)
- 💬 Check [GitHub Discussions](https://github.com/balrogbob/SimpleEdit/discussions)
- 📖 Read all [Documentation](../)
- 🆘 See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

**Last updated:** SimpleEdit v0.0.3
