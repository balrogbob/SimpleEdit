# 🪟 Windows Build Guide

Instructions for building a standalone Windows executable (.exe) from the Python source.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Building the Executable](#building-the-executable)
- [Customization](#customization)
- [Distribution](#distribution)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### TL;DR

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable (from SimpleEdit root)
pyinstaller --onefile --windowed --name PythonApplication1 PythonApplication1/PythonApplication1.py

# Output: dist/PythonApplication1.exe
```

That's it! The `.exe` is in the `dist/` folder.

**⚠️ Important AI Note:** The compiled .exe does **not** support AI inference (CPU mode won't work). For AI features, either:
1. **Use the Python file directly** (CPU inference supported)
2. **Build with CUDA GPU support** (requires NVIDIA GPU + CUDA toolkit) - See [AI Executable Setup](#ai-executable-setup) below

---

## Prerequisites

### Software

1. **Python 3.8+** (must have)
   - Download from [python.org](https://www.python.org/downloads/)
   - ✅ Check "Add Python to PATH" during installation

2. **PyInstaller** (must have)
   ```bash
   pip install pyinstaller
   ```

3. **Optional: torch/tiktoken** (for AI features)
   ```bash
   pip install torch tiktoken
   ```
   - Large download (~2 GB)
   - Only needed if including AI in build

### Verify Installation

```bash
# Check Python
python --version

# Check PyInstaller
pyinstaller --version

# Should show version numbers
```

---

## Building the Executable

### Step 1: Prepare Environment

```bash
# Navigate to SimpleEdit root
cd C:\path\to\SimpleEdit

# Create fresh build (optional but recommended)
rm -r build dist *.spec  # Or use Windows delete

# Verify files present
dir PythonApplication1  # Should show *.py files
```

### Step 2: Build Basic Executable

```bash
pyinstaller --onefile --windowed \
    --name PythonApplication1 \
    PythonApplication1/PythonApplication1.py
```

**Flags explained:**
- `--onefile` - Bundle everything into single .exe (slower startup but easier distribution)
- `--windowed` - No console window (GUI-only)
- `--name` - Output filename
- Path - Main Python file to package

### Step 3: Find Your Executable

```bash
# Output directory
dir dist/

# Should contain:
# - PythonApplication1.exe (main file)
# - (optional) supporting files
```

**Size:** ~50-70 MB (includes Python, tkinter, and all dependencies)

### Step 4: Test the Executable

```bash
# Run from dist folder
.\dist\PythonApplication1.exe

# Should launch editor normally
```

**Verify:**
- Window opens
- Can create/open files
- Syntax highlighting works
- No errors

---

## AI Executable Setup (Optional - Advanced)

### ⚠️ Important Limitations

**CPU-based AI will NOT work in compiled .exe files.**

This is a known limitation with PyInstaller and torch/tiktoken packaging. The compiled environment expects CUDA GPU support, which fails gracefully when unavailable.

### Recommended Solution: Use Python File Directly

For the best user experience with AI support, **recommend users run the Python file instead of the .exe**:

```bash
# Navigate to SimpleEdit directory
cd C:\path\to\SimpleEdit

# Run with Python (AI works in CPU mode)
python PythonApplication1/PythonApplication1.py
```

**Benefits:**
- ✅ AI inference works on CPU
- ✅ No dependency on PyInstaller environment
- ✅ Easier to update (just replace .py files)
- ✅ More reliable and stable

### Optional: Build .exe with GPU Support

If your users have **NVIDIA GPUs** and want a compiled executable with AI:

#### Prerequisites

1. **NVIDIA GPU** (required)
   - Check: `Device Manager` → `Display adapters`
   - Must be NVIDIA CUDA-capable GPU

2. **NVIDIA CUDA Toolkit** (required)
   - Download: [nvidia.com/cuda](https://developer.nvidia.com/cuda-downloads)
   - Choose Windows version
   - **Install CUDA 12.1 or matching your torch version**

3. **cuDNN** (optional, improves performance)
   - Download from NVIDIA website
   - Extract to CUDA installation directory

#### Step 1: Install CUDA-Enabled PyTorch

```bash
# Remove CPU torch first (if installed)
pip uninstall torch tiktoken -y

# Install CUDA torch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Verify CUDA support
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

**Output should be:** `CUDA available: True`

If `False`, your system doesn't have proper CUDA setup - use Python file method instead.

#### Step 2: Build Executable with PyInstaller

```bash
# From SimpleEdit root
pyinstaller --onefile --windowed \
    --name PythonApplication1_AI \
    --collect-all torch \
    --collect-all tiktoken \
    PythonApplication1/PythonApplication1.py
```

**Flags explained:**
- `--collect-all torch` - Include all CUDA libraries
- `--collect-all tiktoken` - Include tokenizer data
- Output: `dist/PythonApplication1_AI.exe`

#### Step 3: Test GPU Support

```bash
# Run the AI-enabled executable
.\dist\PythonApplication1_AI.exe

# Click AI Autocomplete button
# Should use GPU (check GPU usage in Task Manager → Performance)
```

#### File Size Warning

- **Basic .exe:** 50-70 MB
- **AI GPU .exe:** 2-3 GB (includes CUDA libraries)

**Not recommended for distribution** unless targeting advanced users with NVidia GPUs.

### Why CPU AI Doesn't Work in .exe

PyInstaller's packaging environment assumes CUDA availability for torch. When the .exe runs:
1. torch loads expecting CUDA
2. CUDA libraries aren't available in PyInstaller environment
3. Fallback to CPU fails silently
4. AI features disabled

**Workaround:** Use Python file directly (above), which handles CPU/GPU detection properly.

### Summary: Best Practices

| Use Case | Recommendation |
|----------|---|
| **Most users (no GPU)** | Distribute `.exe` for file editing; recommend Python for AI |
| **Power users (NVIDIA GPU)** | Build AI .exe using CUDA steps above |
| **Development/Testing** | Always use Python file for fastest iteration |
| **Safe default** | Just distribute regular .exe without AI |

---

## Customization

### Build with Icon

Create a Windows icon file (`.ico`):

**Option 1: Convert image to icon**
- Use online tool: [convertio.co](https://convertio.co/png-ico/)
- Or Photoshop, GIMP, etc.
- Save as `icon.ico`

**Option 2: Use from repository** (if available)
- Check if SimpleEdit repo has `icon.ico`

Then build with icon:

```bash
pyinstaller --onefile --windowed \
    --name PythonApplication1 \
    --icon=icon.ico \
    PythonApplication1/PythonApplication1.py
```

### Build with Metadata

Create a spec file for advanced options:

```bash
# Generate spec file
pyinstaller --onefile --windowed \
    --name PythonApplication1 \
    PythonApplication1/PythonApplication1.py

# Edit PythonApplication1.spec
# Then rebuild from spec
pyinstaller PythonApplication1.spec
```

### Include AI Model (Optional)

⚠️ **Important:** AI features require CUDA GPU support when compiled to .exe. **See [AI Executable Setup](#ai-executable-setup) above for detailed instructions.**

CPU-based AI inference does **not work** in compiled executables due to PyInstaller environment limitations. Your options:

1. **Recommend Python file** (easiest)
   - Users run: `python PythonApplication1/PythonApplication1.py`
   - AI works perfectly in CPU mode
   - See [Recommended Solution](#recommended-solution-use-python-file-directly)

2. **Build GPU .exe** (advanced users with NVIDIA GPU)
   - Requires NVIDIA GPU, CUDA toolkit, and CUDA torch
   - Creates 2-3 GB executable
   - See [Optional: Build .exe with GPU Support](#optional-build-exe-with-gpu-support)

For most distributions, **do not include AI** in the .exe - it won't function anyway. Instead, clearly document that users can enable AI by running the Python file.

### Reduce Executable Size

If 50 MB is too large:

```bash
# Build as directory (not --onefile)
pyinstaller --windowed \
    --name PythonApplication1 \
    PythonApplication1/PythonApplication1.py

# Output: dist/PythonApplication1/ (directory with files)
# Size: ~30 MB in directory, but faster startup

# To distribute: Zip the directory
7z a PythonApplication1.zip dist/PythonApplication1/
```

---

## Distribution

### Create Installer (Optional)

Use **NSIS** or **Inno Setup** to create professional installer:

#### NSIS Example

1. Install NSIS from [nsis.sourceforge.io](https://nsis.sourceforge.io/)

2. Create `installer.nsi`:

```nsis
!include "MUI2.nsh"

Name "SimpleEdit"
OutFile "SimpleEdit-Installer.exe"
InstallDir "$PROGRAMFILES\SimpleEdit"

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "Install"
  SetOutPath "$INSTDIR"
  File /r "dist\PythonApplication1\*.*"
  CreateShortcut "$SMPROGRAMS\SimpleEdit.lnk" "$INSTDIR\PythonApplication1.exe"
SectionEnd
```

3. Run NSIS:
   - Open installer.nsi with NSIS Compiler
   - Click Compile
   - Creates installer .exe

### Share the Executable

#### Option 1: Direct Download

1. Upload `.exe` to GitHub Releases:
   ```bash
   git tag v0.0.4
   git push origin v0.0.4
   ```
   Then add .exe in GitHub releases UI

2. Users download and run

#### Option 2: Package with Installer

1. Create NSIS or Inno Setup installer (above)
2. Upload installer to GitHub Releases
3. Users run installer (creates Start Menu shortcut, etc.)

#### Option 3: Portable Folder

1. Build as directory (not --onefile)
2. Zip the directory
3. Users extract .zip and run .exe

---

## Updates & Versioning

### Version Number

Edit version in code before building:

```python
# In PythonApplication1.py
__version__ = '0.0.4'
```

Or auto-detect from git tag:

```python
import subprocess
try:
    version = subprocess.check_output(['git', 'describe', '--tags']).decode().strip()
except:
    version = 'dev'
```

### Create Release

```bash
# Tag commit
git tag v0.0.4

# Push tag
git push origin v0.0.4

# GitHub automatically shows releases tab
# Add .exe file there
```

### Update Existing Installation

Users must:
1. Download new .exe
2. Replace old one
3. OR run installer to overwrite

(No auto-update built-in)

---

## Advanced Options

### Sign the Executable (Optional)

Code signing verifies the .exe hasn't been modified:

```bash
# Requires code signing certificate
signtool sign /f certificate.pfx \
    /p password \
    dist/PythonApplication1.exe
```

Benefits:
- ✅ Windows SmartScreen won't warn
- ✅ Trusted branding
- ❌ Requires paid certificate ($100+ per year)

### Build for Different Python Versions

```bash
# Ensure you're using target Python version
python --version  # Shows current

# Create venv for specific version
python3.9 -m venv venv39
.\venv39\Scripts\activate

# Install deps in venv
pip install -r requirements.txt

# Build from venv
pyinstaller --onefile PythonApplication1/PythonApplication1.py
```

### Command-Line Arguments

Enable running with arguments:

```bash
# Users can run:
PythonApplication1.exe filename.py

# Parse in Python:
import sys
if len(sys.argv) > 1:
    initial_file = sys.argv[1]
```

---

## Troubleshooting

### "AI Autocomplete button does nothing" or "AI features disabled"

**This is expected behavior** for the standard .exe build. CPU-based AI inference does not work in PyInstaller-compiled executables.

**Solutions:**

1. **Run Python file instead** (recommended for most users):
   ```bash
   python PythonApplication1/PythonApplication1.py
   ```
   AI will work in CPU mode without any CUDA setup.

2. **Build special GPU executable** (if you have NVIDIA GPU):
   - Follow [AI Executable Setup → Build .exe with GPU Support](#optional-build-exe-with-gpu-support)
   - Requires NVIDIA GPU, CUDA toolkit, and CUDA torch
   - Creates 2-3 GB executable

3. **Use standard .exe without AI features**:
   - AI simply won't be available
   - Editor works perfectly fine for all other features

**Don't worry about this limitation** - most users don't need AI features and will use the editor for file editing. For those who want AI, running the Python file is straightforward and gives better results.

### "PyInstaller not found"

```bash
# Install it
pip install pyinstaller

# Verify
pyinstaller --version
```

### Executable Won't Start

**Possible causes:**
1. Missing dependencies
2. Tkinter not included
3. Python path issues

**Solutions:**
- Run with console to see errors:
  ```bash
  pyinstaller --onefile --console \
      PythonApplication1/PythonApplication1.py
  ```
- Check error output
- Ensure all imports available

### "Module not found" Error

**Cause:** PyInstaller didn't detect all imports

**Solution - Add hidden import:**

```bash
pyinstaller --onefile --windowed \
    --hidden-import=functions \
    --hidden-import=jsmini \
    --hidden-import=js_builtins \
    PythonApplication1/PythonApplication1.py
```

### Large File Size (70+ MB)

**Cause:** Including numpy, scipy, or other heavy libraries

**Solution:**
1. Use `--onedir` instead of `--onefile` (faster startup)
2. Or accept larger size
3. Or remove unused dependencies

### Slow Startup (> 5 seconds)

**Cause:** Usually `--onefile` unpacking

**Solutions:**
1. Use `--onedir` (much faster)
2. Users notice delay only first time

### Windows SmartScreen Warning

**Cause:** Unsigned executable

**Solutions:**
1. Ignore warning (click "More info" → "Run anyway")
2. Buy code signing certificate (expensive)
3. Include installer (NSIS/Inno Setup)

### Antivirus False Positive

**Cause:** PyInstaller-built .exe sometimes flagged

**Solutions:**
1. Submit to antivirus vendor as false positive
2. Ask users to whitelist
3. Sign executable (reduces false positives)

---

## CI/CD Automation

### GitHub Actions Build

Create `.github/workflows/build.yml`:

```yaml
name: Build Windows EXE

on:
  push:
    tags: ['v*']

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install pyinstaller
      - run: pyinstaller --onefile --windowed PythonApplication1/PythonApplication1.py
      - uses: softprops/action-gh-release@v1
        with:
          files: dist/PythonApplication1.exe
```

Now each git tag automatically builds and releases .exe!

---

## See Also

- [INSTALLATION.md](INSTALLATION.md) - Installation for users
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development setup
- [PyInstaller Docs](https://pyinstaller.readthedocs.io/) - Full PyInstaller reference
