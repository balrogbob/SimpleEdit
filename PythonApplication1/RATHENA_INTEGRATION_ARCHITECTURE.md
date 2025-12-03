<!--
NOTE: Public-facing rAthena documentation has been consolidated into the
`docs/` folder and the package README under `rathena-tools/`.
See `docs/RATHENA_TOOLS_PACKAGE_OVERVIEW.md` for a short summary and
`docs/RATHENA_TOOLS_MENU.md`, `docs/RATHENA_TOOLS_COMPLETE_FEATURES.md`,
and `docs/RATHENA_TOOLS_QUICK_REF.md` for the canonical user-facing docs.
This file is retained for history and developer reference.
-->

# rAthena Tools - Proper Package Integration Architecture

## Architecture Overview

The rAthena Tools are integrated into SimpleEdit as a **separate package module** following Python best practices.

```
SimpleEdit Application
    │
    ├─ PythonApplication1.py (Main app)
    │
    ├─ rathena_tools_menu.py (Integration layer)
    │    │
    │    └─→ sys.path setup
    │         │
    │         └─→ rathena-tools/ package
    │              │
    │              ├─ __init__.py
    │              ├─ rathena_script_gen.py
    │              ├─ rathena_script_ui.py
    │              └─ [other modules]
    │
    └─ [other SimpleEdit files]
```

## Why Separate Package?

✅ **Modularity** - rAthena tools are independent of SimpleEdit core  
✅ **Reusability** - Can be used by other applications  
✅ **Maintainability** - Changes to tools don't affect SimpleEdit directly  
✅ **Clarity** - Clear separation of concerns  
✅ **Versioning** - Can be versioned independently  

## Integration Strategy

### 1. Path Setup (rathena_tools_menu.py)

```python
import os
import sys

# Ensure rathena-tools package is in path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_rathena_path = os.path.join(_current_dir, 'rathena-tools')
if _rathena_path not in sys.path:
    sys.path.insert(0, _rathena_path)
```

**Why this approach?**
- Doesn't move files around (keeps package intact)
- Works from anywhere in the codebase
- Uses absolute paths (reliable)
- Checks before adding (avoids duplicates)

### 2. Import Pattern

```python
# AFTER path setup, imports work normally
from rathena_script_gen import ScriptGenerator, ScriptNPC
from rathena_script_ui import DialogBuilder, NPCWizard
```

**Key Point**: Path must be set up BEFORE imports

### 3. Module Isolation

The rathena-tools package remains completely isolated:
- ✅ No files moved to root
- ✅ No modifications to SimpleEdit core needed
- ✅ Self-contained __init__.py
- ✅ Own dependencies and documentation

## Proper File Locations

### ✅ CORRECT Structure
```
SimpleEdit/
├── PythonApplication1/
│   ├── PythonApplication1.py
│   ├── rathena_tools_menu.py          ← Integration layer
│   ├── rathena-tools/                 ← Package module (separate)
│   │   ├── __init__.py
│   │   ├── rathena_script_gen.py
│   │   ├── rathena_script_ui.py
│   │   └── ...
│   └── [other files]
```

### ❌ INCORRECT Structure
```
SimpleEdit/
├── PythonApplication1/
│   ├── PythonApplication1.py
│   ├── rathena_script_gen.py          ← WRONG: Mixed into root
│   ├── rathena_script_ui.py           ← WRONG: Mixed into root
│   ├── rathena-tools/                 ← WRONG: Empty package
│   └── [other files]
```

## Implementation Details

### In rathena_tools_menu.py

```python
#!/usr/bin/env python3
import os
import sys

# Setup path to rathena-tools package
_current_dir = os.path.dirname(os.path.abspath(__file__))
_rathena_path = os.path.join(_current_dir, 'rathena-tools')
if _rathena_path not in sys.path:
    sys.path.insert(0, _rathena_path)

# Now imports work
try:
    from rathena_script_gen import ScriptGenerator, ScriptNPC, ScriptFunction
    from rathena_script_ui import DialogBuilder, NPCWizard, ScriptValidator
    _RATHENA_TOOLS_AVAILABLE = True
except ImportError as e:
    _RATHENA_TOOLS_AVAILABLE = False
    print(f"[DEBUG] Failed to import rAthena tools: {e}")
```

### In other modules

If other SimpleEdit modules need to use rAthena tools:

```python
# Method 1: If called from SimpleEdit main module
# (path already set up by rathena_tools_menu)
from rathena_script_gen import ScriptGenerator

# Method 2: If called independently
import os, sys
sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), 'rathena-tools'
))
from rathena_script_gen import ScriptGenerator
```

## Verification Checklist

- ✅ `rathena-tools/` directory exists in PythonApplication1/
- ✅ `rathena-tools/__init__.py` exists and has imports
- ✅ `rathena_script_gen.py` is IN `rathena-tools/`, not root
- ✅ `rathena_script_ui.py` is IN `rathena-tools/`, not root
- ✅ `rathena_tools_menu.py` sets up path correctly
- ✅ Path setup uses `os.path` (cross-platform)
- ✅ Path setup checks before adding to avoid duplicates
- ✅ No files moved to root directory

## Common Mistakes to Avoid

❌ **Mistake 1**: Moving files to root
```python
# WRONG - Don't do this
PythonApplication1/
├── rathena_script_gen.py    ← WRONG location
├── rathena_script_ui.py     ← WRONG location
```

❌ **Mistake 2**: Relative imports without path setup
```python
# WRONG - This will fail
from rathena_script_gen import ScriptGenerator
```

❌ **Mistake 3**: Using hardcoded paths
```python
# WRONG - Won't work on other computers
sys.path.insert(0, 'C:\\Users\\YourName\\rathena-tools')
```

✅ **Correct**: Using proper path setup
```python
# RIGHT - Works everywhere
import os, sys
_rathena_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 
    'rathena-tools'
)
sys.path.insert(0, _rathena_path)
```

## Benefits of This Architecture

| Benefit | How Achieved |
|---------|-------------|
| **Modularity** | rAthena-tools is separate package |
| **Maintainability** | Clear integration point (rathena_tools_menu.py) |
| **Reusability** | Package can be imported from anywhere |
| **Clarity** | Obvious what's SimpleEdit vs rAthena tools |
| **Isolation** | Changes to tools don't break SimpleEdit |
| **Extensibility** | Easy to add more integration points |

## Moving Forward

### Current Status
✅ Integration architecture is correct
✅ Path setup is proper
✅ rathena_tools_menu.py handles all setup
✅ Package remains in rathena-tools/ directory

### Next Issues to Address
🔧 Issues within the rathena-tools module itself (to be fixed next)
🔧 Module API refinements as needed
🔧 Additional test coverage

---

**Summary**: The rAthena Tools are now properly integrated as a separate Python package module within SimpleEdit, following all best practices for Python package organization and integration.
