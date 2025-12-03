# ⚡ Performance Tuning Guide

Optimize SimpleEdit for speed and efficiency.

---

## Table of Contents

- [Quick Wins](#quick-wins)
- [Syntax Highlighting Optimization](#syntax-highlighting-optimization)
- [Large File Handling](#large-file-handling)
- [Memory Optimization](#memory-optimization)
- [Profiling & Diagnosis](#profiling--diagnosis)

---

## Quick Wins

### 1. Disable Syntax Highlighting (Biggest Impact)

**Problem:** Syntax highlighting causes lag on large files

**Solution:** Settings → uncheck "Syntax Highlighting"

**Impact:** ⚡⚡⚡ Dramatic speedup

### 2. Close Unused Tabs

**Problem:** Each open tab consumes memory

**Solution:** File → Close Tab or click `×` on tab

**Impact:** ⚡ Frees 5-10 MB per tab

### 3. Unload AI Model

**Problem:** AI model uses 500+ MB RAM

**Solution:** Click "AI Unload" button in toolbar

**Impact:** ⚡⚡ Frees 500+ MB if AI loaded

### 4. Split Large Files

**Problem:** Files > 50KB slow to edit, even without highlighting

**Solution:** Split into multiple files (e.g., chapters, sections)

**Impact:** ⚡ Each file faster to edit

---

## Syntax Highlighting Optimization

### Understanding the Issue

Syntax highlighting works by:
1. Tokenizing entire file
2. Building tag ranges for keywords, strings, comments
3. Applying Tkinter tags to Text widget

On large files (>50KB), step 3 becomes slow because Tkinter re-renders affected regions.

### Optimization Strategies

#### Strategy 1: Disable Highlighting

Most aggressive, fastest:
- Settings → uncheck "Syntax Highlighting"
- Restarts immediately

#### Strategy 2: Use Lighter Syntax

Some languages highlight slower than others:
- **Fast:** YAML, JSON, Markdown
- **Medium:** Python, JavaScript, HTML
- **Slow:** C/C++ (lots of preprocessor)

**Tip:** Open large C++ files without highlighting enabled.

#### Strategy 3: Background Worker Thread

Already enabled by default! Syntax highlighting runs in background thread.

**Check status:**
- If editor responsive while typing: ✅ Working well
- If editor freezes while typing: ❌ Highlighting blocking main thread

If freezing, disable highlighting (see above).

#### Strategy 4: Incremental Highlighting

**Future optimization (not implemented):**
- Only highlight visible portion
- Update as user scrolls
- Would dramatically improve large file performance

---

## Large File Handling

### Files 50-100 KB

**Recommended:**
1. Disable syntax highlighting
2. Editor should be usable
3. Scrolling may be slightly laggy

**If still slow:**
- Close other tabs
- Disable other background apps
- Restart editor

### Files 100-500 KB

**Recommended:**
1. Disable syntax highlighting
2. Split into multiple files
3. Consider external editor (VS Code, etc.)

**Worst case:**
- Disable syntax highlighting
- Close all other tabs
- May still be slow

### Files > 500 KB

**Recommendation:**
Use different editor (VS Code, Vim, etc.)

SimpleEdit not optimized for such large files.

---

## Memory Optimization

### Profile Memory Usage

```bash
# Check what's using memory
python -m tracemalloc PythonApplication1/PythonApplication1.py
```

### Reduce Memory Footprint

#### Close Unused Tabs

Each tab stores:
- Text content
- Syntax highlighting tags
- Undo history

**Savings:** 5-50 MB per tab (depends on file size)

#### Unload AI Model

If you're not using AI autocomplete:
- Click "AI Unload" button
- Frees 500-800 MB

#### Disable Undo

For very large files:
- Settings → uncheck "Undo Enabled"
- Disables undo/redo, saves memory

**Note:** Only do if you don't need undo!

#### Restart Editor

Over time, memory usage may creep up:
- Close all tabs
- Restart editor
- Resets memory state

---

## CPU Optimization

### What Uses CPU

1. **Syntax highlighting** (~70% of CPU usage)
   - Tokenization
   - Tag application
   - Text widget re-render

2. **JavaScript execution** (~20%)
   - Interpreting scripts
   - DOM updates

3. **UI rendering** (~10%)
   - Tkinter updates
   - Screen redraw

### Reduce CPU Usage

#### Disable Syntax Highlighting

Biggest impact: ⚡⚡⚡

```python
# In Settings
Syntax Highlighting: [x] Disable
```

#### Throttle Highlighting Updates

Edit slower to give highlighting time to catch up:
- Type slower
- Pause after large pastes
- Let background thread keep up

#### Close Unused Scripts

If running JavaScript:
- Avoid infinite loops
- Add timeout/exit conditions
- Close tabs with scripts

---

## JavaScript Execution Optimization

### Slow Script Execution

**Problem:** Script runs but very slowly

**Causes:**
1. Inefficient algorithm (O(n²) or worse)
2. Very large data structure processing
3. Deep recursion

**Solutions:**
1. Optimize algorithm (better data structures)
2. Break work into smaller chunks
3. Avoid deep recursion (use loops instead)

### Script Hanging

**Problem:** Script seems to hang forever

**Causes:**
1. Infinite loop
2. Infinite recursion
3. Waiting for external resource

**Solutions:**
1. Add loop counter (exit after 1000 iterations)
2. Add recursion guard (bail out after depth 100)
3. No network calls in jsmini (by design)

### Hit Execution Limit

**Error:** "Execution limit exceeded"

**Meaning:** Script exceeded 200,000 statement limit

**Solutions:**
1. Optimize inner loops
2. Break work into multiple scripts
3. See [JSMINI.md](JSMINI.md) for configuring limits

---

## Profiling & Diagnosis

### Enable Debug Logging

See where time is spent:

```python
# In Settings
Debug Logging: [x] Enable
```

Check terminal/Output for detailed timing information.

### Profile with Python

```bash
# Run with profiler
python -m cProfile -s cumulative PythonApplication1/PythonApplication1.py

# Top time consumers will show first
```

### Check Resource Usage

**Windows Task Manager:**
- Right-click taskbar → Task Manager
- Find SimpleEdit process
- Check CPU % and Memory usage

**macOS Activity Monitor:**
- Cmd+Space → "Activity Monitor"
- Find SimpleEdit process

**Linux top:**
```bash
top
# Find python process
```

### Identify Bottlenecks

#### If CPU high (50%+):
- Likely syntax highlighting
- Disable and check if it drops
- If yes: highlighting is the issue

#### If Memory high (500+ MB):
- Check how many tabs open
- Check if AI model loaded
- Close tabs or unload AI

#### If UI frozen (not responding):
- Definitely background thread issue
- Disable syntax highlighting
- Or close/restart

---

## System Configuration

### OS-Level Optimization

#### Windows

- Close background apps (browsers, Discord, etc.)
- Disable animations: Settings → Ease of Access → Display
- Increase virtual memory if low on RAM

#### macOS

- Close unused applications
- Reduce visual effects: System Preferences → Accessibility → Display
- Disable Spotlight indexing if editor directory uses high CPU

#### Linux

- Reduce desktop effects
- Run lightweight window manager (if possible)
- Free up RAM: `sudo sync; sudo sysctl -w vm.drop_caches=3`

---

## Before/After Checklist

### If SimpleEdit Is Slow

- [ ] Disable syntax highlighting (Settings)
- [ ] Close unused tabs (File → Close Tab)
- [ ] Unload AI model (click AI Unload button)
- [ ] Close other applications
- [ ] Restart editor
- [ ] Check file size (> 50 KB?)
- [ ] See [TROUBLESHOOTING.md](TROUBLESHOOTING.md#performance-issues)

### If Still Slow

- [ ] Consider splitting into smaller files
- [ ] Use external editor for very large files
- [ ] Profile to identify exact bottleneck
- [ ] Report issue on GitHub with details

---

## Expected Performance

### Normal Performance (Fast ✅)

- Typing is **instant** (no visible lag)
- Scrolling is **smooth**
- Saving is **immediate** (< 1 second)
- Opening is **quick** (< 2 seconds)

### Acceptable Performance (Okay ⚠️)

- Typing has **slight lag** (< 200 ms)
- Scrolling is **jerky** but usable
- Saving is **slow** (2-5 seconds)
- Opening is **slow** (5-10 seconds)

### Unacceptable Performance (Bad ❌)

- Typing **freezes** (> 1 second lag)
- UI **not responsive** to clicks
- **Crashes** frequently
- **High CPU/memory** constantly

If experiencing ❌ performance:
1. Follow [Quick Wins](#quick-wins) section
2. Read [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
3. Report issue on GitHub

---

## Benchmarks

### Typical Performance (Modern PC)

| Operation | Time | Notes |
|-----------|------|-------|
| Startup | < 1 sec | Cold start, no files |
| Open 10 KB file | < 100 ms | With highlighting |
| Open 100 KB file | 0.5-2 sec | With highlighting |
| Open 1 MB file | 3-10 sec | With highlighting, or longer |
| Syntax highlight (10 KB) | < 100 ms | Background thread |
| Syntax highlight (100 KB) | 0.5-2 sec | May be visible |
| Find (100 KB file) | < 200 ms | Regex find |
| Replace all | 0.5-2 sec | Depends on count |
| AI model load | 30+ sec | First load only |
| Run simple JS | < 50 ms | `2 + 2` etc |

### System Impact

| Feature | CPU | Memory |
|---------|-----|--------|
| **Idle** | < 1% | 50-100 MB |
| **Syntax highlighting (10 KB)** | 10-30% | +5 MB |
| **Syntax highlighting (100 KB)** | 20-50% | +20 MB |
| **AI model loaded** | < 1% | +500 MB |
| **Running JS script** | 50-100% | +10-50 MB |

---

## Future Optimization Ideas

- [ ] Lazy tag application (only visible viewport)
- [ ] Parse caching (same file, same tokens)
- [ ] Bytecode compilation for JS
- [ ] Native modules for performance-critical code
- [ ] Viewport-based rendering (only show visible lines)

---

## See Also

- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design (threading, data flow)
- [JSMINI.md](JSMINI.md) - JavaScript engine internals
