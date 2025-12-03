# 📥 Installation Guide

Complete setup instructions for SimpleEdit on all platforms.

---

## Table of Contents

- [System Requirements](#system-requirements)
- [Windows Installation](#windows-installation)
- [Linux Installation](#linux-installation)
- [macOS Installation](#macos-installation)
- [Optional Dependencies](#optional-dependencies)
- [Verify Installation](#verify-installation)
- [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|------------|
| **OS** | Windows 7+ / Linux (any) / macOS 10.12+ |
| **Python** | 3.8+ (for source installation) |
| **Memory** | 512 MB RAM minimum |
| **Disk Space** | 50 MB (source) or 30 MB (Windows exe) |

### Recommended Requirements

| Component | Recommendation |
|-----------|------------|
| **Python** | 3.10+ |
| **Memory** | 2+ GB RAM |
| **Disk Space** | 100+ MB |

---

## Windows Installation

### Option 1: Windows Executable (Recommended for Most Users)

**Easiest method—no Python required!**

1. **Download**
   - Visit [GitHub Releases](https://github.com/balrogbob/SimpleEdit/releases)
   - Download `PythonApplication1.exe` (latest version)

2. **Run**
   - Double-click the `.exe` file
   - Editor opens immediately
   - No setup wizard required

3. **Optional: Create Shortcut**
   - Right-click → Send to → Desktop (create shortcut)
   - Pin to Start Menu for quick access

**Advantages:**
- ✅ No Python installation needed
- ✅ Single executable file
- ✅ Works offline
- ✅ Fast startup

**Disadvantages:**
- ❌ Slightly larger file size (~50 MB)
- ❌ Harder to modify source code

---

### Option 2: Python Source on Windows

**Better if you want to modify code or don't trust .exe files.**

#### Prerequisites

1. **Install Python 3.8+**
   - Download from [python.org](https://www.python.org/downloads/)
   - During installation: ✅ Check **"Add Python to PATH"**
   - Verify installation:
     ```bash
     python --version
     ```

2. **Install Git** (optional but recommended)
   - Download from [git-scm.com](https://git-scm.com/download/win)
   - Or use GitHub Desktop

#### Installation Steps

```bash
# Clone the repository
git clone https://github.com/balrogbob/SimpleEdit.git
cd SimpleEdit

# Run the editor
python PythonApplication1/PythonApplication1.py
```

**That's it!** The editor will launch.

#### Creating a Windows Shortcut

Create a `.bat` file on your desktop:

```batch
@echo off
cd C:\path\to\SimpleEdit
python PythonApplication1/PythonApplication1.py
pause
```

Save as `SimpleEdit.bat` and double-click to run.

---

## Linux Installation

### Debian/Ubuntu

#### Prerequisites

```bash
# Install Python and Tkinter
sudo apt-get update
sudo apt-get install python3 python3-tk python3-pip
```

#### Installation

```bash
# Clone repository
git clone https://github.com/balrogbob/SimpleEdit.git
cd SimpleEdit

# Run
python3 PythonApplication1/PythonApplication1.py
```

#### Creating a Desktop Shortcut

Create `~/.local/share/applications/simpleedit.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=SimpleEdit
Exec=python3 /path/to/SimpleEdit/PythonApplication1/PythonApplication1.py
Icon=text-editor
Categories=Development;TextEditor;
```

Then make it executable:
```bash
chmod +x ~/.local/share/applications/simpleedit.desktop
```

### Fedora/RHEL

```bash
# Install dependencies
sudo dnf install python3 python3-tkinter python3-pip

# Clone and run
git clone https://github.com/balrogbob/SimpleEdit.git
cd SimpleEdit
python3 PythonApplication1/PythonApplication1.py
```

### Arch Linux

```bash
# Install Python
sudo pacman -S python tk

# Clone and run
git clone https://github.com/balrogbob/SimpleEdit.git
cd SimpleEdit
python3 PythonApplication1/PythonApplication1.py
```

---

## macOS Installation

### Prerequisites

1. **Ensure Python 3.8+ is installed**
   ```bash
   python3 --version
   ```

2. **If not installed, use Homebrew:**
   ```bash
   brew install python3
   ```

### Installation

```bash
# Clone repository
git clone https://github.com/balrogbob/SimpleEdit.git
cd SimpleEdit

# Run
python3 PythonApplication1/PythonApplication1.py
```

### Creating a macOS Application

Create a simple script `simpleedit.sh`:

```bash
#!/bin/bash
cd /path/to/SimpleEdit
python3 PythonApplication1/PythonApplication1.py
```

Make it executable:
```bash
chmod +x simpleedit.sh
```

Double-click to run, or add to Dock for quick access.

---

## Optional Dependencies

### AI Autocomplete Features

To enable experimental GPT-2 powered code suggestions:

```bash
pip install torch tiktoken
```

**Note:** This downloads a large model (~500MB) on first use. Only install if you want AI features.

**System Requirements:**
- 2+ GB available RAM (for model loading)
- 1+ GB available disk space

**To enable in editor:**
- Click "AI Autocomplete" button in toolbar
- Model loads automatically on first click

### Development/Contributing

If you plan to modify SimpleEdit or run tests:

```bash
pip install pytest pytest-cov
```

Then run tests:
```bash
pytest PythonApplication1/tests/
```

---

## Verify Installation

### Quick Verification

1. **Start the editor**
   ```bash
   python PythonApplication1/PythonApplication1.py
   ```

2. **Check window appears** with menu bar and editor

3. **Test basic operation:**
   - File → New
   - Type: `print("Hello World")`
   - File → Save (as `test.py`)
   - ✅ Should complete without errors

### Detailed Verification

```bash
# Check Python version
python --version  # Should be 3.8+

# Verify Tkinter available
python -c "import tkinter; print('Tkinter OK')"

# Verify can import SimpleEdit modules
python -c "import sys; sys.path.insert(0, 'PythonApplication1'); import functions; print('Import OK')"
```

---

## Troubleshooting

### Python Not Found

**Error:** `python: command not found`

**Solution:**
- On Linux/Mac: Use `python3` instead of `python`
- On Windows: Reinstall Python and ensure "Add Python to PATH" is checked

### Tkinter Missing

**Error:** `ModuleNotFoundError: No module named 'tkinter'`

**Solution:**
- **Ubuntu/Debian:** `sudo apt-get install python3-tk`
- **Fedora:** `sudo dnf install python3-tkinter`
- **macOS:** `brew install python-tk`
- **Windows:** Reinstall Python, ensure tcl/tk is selected

### Permission Denied

**Error:** `PermissionError: [Errno 13] Permission denied`

**Solution:**
- Make script executable: `chmod +x PythonApplication1/PythonApplication1.py`
- Or run with explicit Python: `python PythonApplication1/PythonApplication1.py`

### Module Not Found on Import

**Error:** `ModuleNotFoundError: No module named 'functions'`

**Solution:**
- Ensure you're in the SimpleEdit root directory
- Run: `python PythonApplication1/PythonApplication1.py` (not `python PythonApplication1.py`)

### Slow Startup

**Symptom:** Takes 30+ seconds to launch

**Solutions:**
- First launch is slower (syntax highlighting initializes)
- If AI is enabled, model loads on first AI button click (first time: ~30 seconds)
- Subsequent launches are fast

### AI Model Won't Load

**Error:** `RuntimeError: Failed to load checkpoint` or similar

**Solutions:**
1. Ensure `torch` and `tiktoken` installed: `pip install torch tiktoken`
2. Check disk space (needs ~1 GB)
3. Check RAM available (needs ~2 GB)
4. Delete cache: Remove `out/` directory and retry
5. See [Troubleshooting.md](TROUBLESHOOTING.md#ai-model-wont-load)

### UI Not Responding / Frozen

**Symptom:** Editor becomes unresponsive while typing

**Solutions:**
- This is typically background syntax highlighting on large files
- Disable: Settings → Settings... → uncheck "Syntax Highlighting"
- Or see [PERFORMANCE-TUNING.md](PERFORMANCE-TUNING.md)

---

## Building Windows Executable (Advanced)

If you want to build your own `.exe`:

### Prerequisites

```bash
pip install pyinstaller
```

### Build Steps

```bash
# From SimpleEdit root directory
pyinstaller --onefile --windowed \
    --name PythonApplication1 \
    --icon icon.ico \
    PythonApplication1/PythonApplication1.py

# Output: dist/PythonApplication1.exe
```

See [WINDOWS-BUILD.md](WINDOWS-BUILD.md) for detailed instructions.

---

## Next Steps

- 📖 [Quick Start Guide](QUICKSTART.md) - First steps with SimpleEdit
- ⚙️ [Configuration Guide](EDITOR-USAGE.md) - Customize your setup
- 🆘 [Troubleshooting](TROUBLESHOOTING.md) - Solutions to common issues

---

## Getting Help

- 💬 [Report Installation Issues](https://github.com/balrogbob/SimpleEdit/issues/new?title=Installation%20Help)
- 📧 Check [FAQ.md](FAQ.md) for common questions
- 🔍 Search existing [GitHub Issues](https://github.com/balrogbob/SimpleEdit/issues)
