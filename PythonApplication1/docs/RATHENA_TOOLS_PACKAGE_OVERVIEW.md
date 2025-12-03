# rAthena Tools — Package Overview and Public Documentation

This document consolidates the public-facing rAthena documentation that existed at the project root and points users to the authoritative docs in the `docs/` folder and the `rathena-tools/` package README.

Purpose:
- Collect public integration, usage and package-overview information from root-level files into a single, short reference in `docs/`.
- Avoid duplication between root maintenance/verification documents and user-facing docs.
- Provide clear pointers to in-depth guides in `docs/` and `rathena-tools/`.

Contents included (high-level):
- Package layout and integration architecture
- Path setup and import pattern for SimpleEdit integration
- Where to find full user guides, feature references and quick refs

---

## Package layout (summary)

Place the `rathena-tools/` package inside the `PythonApplication1/` folder. Keep it as a separate package module with its own `__init__.py` and documentation.

Recommended structure:

```
PythonApplication1/
├── PythonApplication1.py
├── rathena_tools_menu.py       # integration wrapper (sets up sys.path)
├── rathena-tools/              # package module
│   ├── __init__.py
│   ├── rathena_script_gen.py
│   ├── rathena_script_ui.py
│   ├── RATHENA_SCRIPT_GUIDE.md
│   └── README.md
└── docs/                       # consolidated documentation for users
```

## Quick integration snippet

Use absolute paths and set up `sys.path` before imports. Example (use `rathena_tools_menu.py` to centralize this):

```python
import os
import sys

_current_dir = os.path.dirname(os.path.abspath(__file__))
_rathena_path = os.path.join(_current_dir, 'rathena-tools')
if _rathena_path not in sys.path:
    sys.path.insert(0, _rathena_path)

# then import modules from the package
from rathena_script_gen import ScriptGenerator
from rathena_script_ui import DialogBuilder
```

## Where to find full documentation and references

Authoritative, user-facing docs are located in the `docs/` folder:

- `docs/RATHENA_TOOLS_MENU.md` — Main user guide and walkthroughs
- `docs/RATHENA_TOOLS_COMPLETE_FEATURES.md` — Detailed feature reference
- `docs/RATHENA_TOOLS_QUICK_REF.md` — One-page quick reference
- `docs/INDEX.md` — Documentation index (links to the rAthena tools docs)

Additionally, the `rathena-tools/README.md` (package README) provides a package-level overview and examples that can be consumed by developers integrating the package directly.

## Purpose of root-level rAthena files

Some files in the project root are maintenance, verification, or integration notes created during development. Where those files contain public, user-facing information it has been consolidated into this document and into `docs/` files. Root-level files that are internal (audit logs, verification checklists, migration notes) remain in the root for project history and developer reference.

If you maintain the repository, prefer updating the `docs/` versions and the package `rathena-tools/README.md` for user-facing changes.

---

Links
- See `docs/RATHENA_TOOLS_MENU.md` for step-by-step usage and examples.
- See `rathena-tools/README.md` for package examples and developer-level integration notes.

