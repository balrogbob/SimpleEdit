# 🆘 Troubleshooting Guide

Common issues and solutions for SimpleEdit.

---

## Table of Contents

- [Installation Issues](#installation-issues)
- [Startup & UI Issues](#startup--ui-issues)
- [Editing & Display](#editing--display)
- [File Operations](#file-operations)
- [Syntax Highlighting](#syntax-highlighting)
- [JavaScript Execution](#javascript-execution)
- [AI Features](#ai-features)
- [Performance Issues](#performance-issues)
- [Getting Additional Help](#getting-additional-help)

---

## Installation Issues

### "python: command not found"

**Problem:** Python not recognized in terminal

**Solution:**
- On Windows: Reinstall Python and check "Add Python to PATH"
- On Mac/Linux: Use `python3` instead of `python`
- Verify: `python3 --version`

### "No module named 'tkinter'"

**Problem:** Tkinter (GUI framework) not installed

**Solution:**
- **Windows:** Reinstall Python, ensure tcl/tk is selected
- **Ubuntu/Debian:** `sudo apt-get install python3-tk`
- **Fedora/RHEL:** `sudo dnf install python3-tkinter`
- **macOS:** `brew install python-tk`

### "ModuleNotFoundError: No module named 'functions'"

**Problem:** SimpleEdit modules not found

**Solution:**
- Ensure you're in the SimpleEdit root directory
- Run: `python PythonApplication1/PythonApplication1.py` (not `python PythonApplication1.py`)

### See Also

- [INSTALLATION.md](INSTALLATION.md) - Complete setup guide
- [FAQ.md](FAQ.md) - Frequently asked questions

---

## Startup & UI Issues

### Editor Takes 30+ Seconds to Start

**Cause:** Syntax highlighting initialization on first run

**Solution:**
- First launch is slower (normal)
- Subsequent launches are faster
- If AI is enabled and you click AI button, first model load adds ~30 seconds

### UI Not Responding / Frozen

**Problem:** Editor becomes unresponsive

**Causes & Solutions:**
1. **Large file with syntax highlighting**
   - Disable: Settings → Settings... → uncheck "Syntax Highlighting"
   - Or see [PERFORMANCE-TUNING.md](PERFORMANCE-TUNING.md)

2. **JavaScript running indefinitely**
   - Press `Ctrl+C` in terminal to interrupt
   - Check script has exit conditions
   - Recusrion prevention guards against infinite loops, if one is encountered please submit a bug report 

3. **Memory issue**
   - Close unused tabs
   - Disable AI if enabled
   - Restart editor

### Window Doesn't Appear

**Problem:** Running editor but no window shows up

**Solution:**
- Check terminal for error messages (see stderr)
- Verify Tkinter is installed (see above)
- Try running from terminal instead of double-clicking

---

## Editing & Display

### Text Not Appearing / Disappearing

**Problem:** Text you type doesn't show, or shows then vanishes

**Solutions:**
- Save file: `Ctrl+S`
- Undo recent changes: `Ctrl+Z`
- Close without saving, then reopen file
- Check file permissions (read-only?)

### Formatting Not Saving

**Problem:** Bold/italic applied but doesn't persist when file reopened

**Note:** SimpleEdit supports formatting display but storage requires saving with SIMPLEEDIT metadata header. Standard `.txt` files don't preserve formatting.

**Solution:**
- Use File → Save as Markdown to export with formatting preserved

### Text Disappears When Scrolling

**Problem:** Text seems to vanish when scrolling large files

**Cause:** Rendering issue with syntax highlighting

**Solution:**
- Disable syntax highlighting: Settings → uncheck "Syntax Highlighting"
- See [PERFORMANCE-TUNING.md](PERFORMANCE-TUNING.md)

### Special Characters Not Displaying

**Problem:** Unicode or special characters show as `?` or garbled

**Solution:**
- Check file encoding: Make sure file is saved as UTF-8
- Try File → Save As and explicitly select UTF-8 encoding

---

## File Operations

### File Not Saving

**Problem:** Clicking Save doesn't work

**Solutions:**
1. Check directory permissions: Are you allowed to write there?
2. Try File → Save As to save elsewhere
3. Check disk space (if drive full, saves fail silently)
4. Verify filename is valid (no `< > : " / \ | ? *`)

### Can't Open File

**Problem:** File → Open browser doesn't work

**Solution:**
- Try entering path directly: See if Recent Files work
- Check file exists and is readable
- Try opening a test `.txt` file first

### Recent Files List Empty

**Problem:** File → Open Recent shows no files

**Solution:**
- This is normal if you just installed SimpleEdit
- Open and save some files—they'll appear in recent
- Check config.ini has `[Recent]` section

### File Corruption Warning

**Problem:** Warning when opening file

**Solutions:**
- File may have been corrupted—try backup
- Try opening in another editor to verify
- If SimpleEdit can't read it, no other editor probably can either

---

## Syntax Highlighting

### Colors Not Appearing

**Problem:** Syntax highlighting disabled or colors wrong

**Solutions:**
1. Check Settings → Syntax Highlighting is enabled
2. Verify hex colors valid: `#RRGGBB` (e.g., `#FF0000`)
3. Check config.ini `[Syntax]` section
4. Restart editor to apply changes

### Language Not Detected

**Problem:** Python code not highlighted as Python

**Solutions:**
1. Save file with correct extension (`.py` for Python, `.js` for JavaScript)
2. Check file is in `PythonApplication1/syntax/` directory
3. For HTML code blocks, explicitly specify language:
   ````
   ```python
   code here
   ```
   ````

### Performance Issues with Highlighting

**Problem:** Editor slow when editing large files

**Solutions:**
- Disable syntax highlighting: Settings → uncheck "Syntax Highlighting"
- Split large file into smaller files
- See [PERFORMANCE-TUNING.md](PERFORMANCE-TUNING.md)

### See Also

- [SYNTAX.md](SYNTAX.md) - Full syntax highlighting guide
- [PERFORMANCE-TUNING.md](PERFORMANCE-TUNING.md) - Performance optimization

---

## JavaScript Execution

### Script Not Running

**Problem:** JavaScript in HTML doesn't execute

**Solutions:**
1. Verify file is `.html` extension
2. Check script has `<script>` tags
3. Enable debug logging to see errors: Settings → Enable debug logging
4. Check browser console or JS Console (Settings menu)

### "Execution limit exceeded" Error

**Problem:** Script hit execution limit

**Cause:** Infinite loop or very intensive operation

**Solutions:**
1. Add exit condition to loops
2. Break complex operations into smaller chunks
3. See [JSMINI.md](JSMINI.md) for execution limits

### Script Errors Not Showing

**Problem:** Script fails silently

**Solutions:**
1. Open JS Console: Settings → Install JS Console → Enable debug logging
2. Check terminal for error output
3. Add `console.log()` statements to debug
4. See [JSMINI.md](JSMINI.md) for debugging

### DOM Not Updating

**Problem:** JavaScript creates DOM elements but they don't appear

**Solutions:**
1. Verify elements created with `document.createElement()`
2. Append to `document.body`: `document.body.appendChild(el)`
3. Call `host.setRaw()` to update display
4. Check console for errors

### See Also

- [JSMINI.md](JSMINI.md) - JavaScript engine documentation
- [development-process.md](development-process.md) - How jsmini was built
- [EXAMPLES.md](EXAMPLES.md) - JavaScript execution examples

---

## AI Features

### "AI Autocomplete" Button Not Working

**Problem:** Clicking button does nothing

**Solutions:**
1. Verify torch installed: `pip install torch tiktoken`
2. Check RAM available (needs ~2 GB)
3. Check disk space (needs ~1 GB for model)
4. See terminal for error messages

### AI Model Won't Load

**Problem:** "Failed to load checkpoint" error

**Solutions:**
1. **First time:** Model downloads on first use—takes ~30 seconds
2. **Missing dependencies:** `pip install torch tiktoken`
3. **Not enough memory:** Close other applications, try again
4. **Corrupt download:** Delete `out/` directory, retry
5. **Check logs:** Enable debug logging in Settings

### AI Autocomplete Very Slow

**Problem:** AI button takes 1+ minute

**Cause:** Model is loading (first time only)

**Solution:**
- First model load always slow (~30 seconds minimum)
- Subsequent loads fast
- If very slow (>1 min), check system resources

### AI Not Available

**Problem:** Button greyed out / "AI libraries not available"

**Cause:** torch or tiktoken not installed

**Solution:**
```bash
pip install torch tiktoken
```

**Note:** These are optional—SimpleEdit works fine without them.

---

## Performance Issues

### Large Files Very Slow

**Problem:** Editing or scrolling large files is sluggish

**Solutions:**
1. **Disable syntax highlighting:** Settings → uncheck "Syntax Highlighting"
2. **Split into smaller files:** Break ~50KB+ files into chunks
3. **Close unnecessary tabs:** Each tab consumes resources
4. **See [PERFORMANCE-TUNING.md](PERFORMANCE-TUNING.md)**

### Memory Usage High

**Problem:** SimpleEdit uses lots of RAM

**Causes & Solutions:**
1. **Many tabs open:** Close unused tabs
2. **AI model loaded:** Click "AI Unload" button
3. **Very large file:** Split into smaller files
4. **Memory leak:** Restart editor

### CPU Usage High

**Problem:** Editor uses lots of CPU

**Cause:** Usually syntax highlighting on large file

**Solution:**
- Disable: Settings → uncheck "Syntax Highlighting"
- Or see [PERFORMANCE-TUNING.md](PERFORMANCE-TUNING.md)

### See Also

- [PERFORMANCE-TUNING.md](PERFORMANCE-TUNING.md) - Optimization guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - Threading model

---

## Getting Additional Help

### Check Other Resources

1. **[FAQ.md](FAQ.md)** - Frequently asked questions
2. **[INSTALLATION.md](INSTALLATION.md)** - Setup issues
3. **[API.md](API.md)** - Using SimpleEdit as a library
4. **[EXAMPLES.md](EXAMPLES.md)** - Practical examples

### Report a Bug

[Open GitHub Issue](https://github.com/balrogbob/SimpleEdit/issues/new?template=bug_report.md)

Include:
- OS and Python version
- Steps to reproduce
- Error messages
- Screenshots if helpful

### Request a Feature

[Open GitHub Discussion](https://github.com/balrogbob/SimpleEdit/discussions/new)

### Search Existing Issues

[GitHub Issues](https://github.com/balrogbob/SimpleEdit/issues)

---

**Still stuck?** Join the community on [GitHub Discussions](https://github.com/balrogbob/SimpleEdit/discussions) 💬
