# rAthena Tools Integration for SimpleEdit - Setup Guide

## Overview

This integration adds a complete **rAthena Tools** menu to SimpleEdit, providing easy access to the rAthena script development toolkit without leaving the editor.

## What Was Added

### 1. New File: `rathena_tools_menu.py`
Location: `PythonApplication1/rathena_tools_menu.py`

This module provides:
- **`create_rathena_menu()`**: Creates the rAthena Tools menu and adds it to SimpleEdit's menu bar
- **Menu Items**:
  - New NPC Script
  - New Function
  - NPC Wizard
  - Dialog Builder
  - Validate Script
  - Insert Quick NPC

- **Dialog Functions**:
  - `launch_npc_wizard()` - Step-by-step NPC creation wizard
  - `launch_function_creator()` - Create rAthena functions with parameters
  - `launch_dialog_builder()` - Build dialog command sequences
  - `insert_quick_npc()` - Insert pre-configured NPC templates
  - `validate_current_script()` - Validate rAthena scripts for errors

### 2. Updated File: `PythonApplication1.py`
Modified the menu initialization section to include:
- Import of `rathena_tools_menu`
- Menu creation call after the Symbols menu

## Menu Structure

```
File
Edit
Settings
Symbols
rAthena Tools ← NEW MENU
  ├─ New NPC Script
  ├─ New Function
  ├─ ─────────────
  ├─ NPC Wizard...
  ├─ Dialog Builder...
  ├─ ─────────────
  ├─ Validate Script
  └─ Insert Quick NPC
```

## How to Use

### 1. Create a Simple NPC
- Click **rAthena Tools → Insert Quick NPC**
- Fill in NPC Name, Map, X/Y Position, and Sprite ID
- Click "Create" to insert template into editor

### 2. Create a Function
- Click **rAthena Tools → New Function**
- Enter function name, parameters (comma-separated)
- Add function body commands
- Click "Insert" to add to current script

### 3. Build Dialogs
- Click **rAthena Tools → Dialog Builder...**
- Construct dialog command sequences
- Click "Generate & Insert" to add to script

### 4. Validate Your Script
- Write or paste rAthena script in editor
- Click **rAthena Tools → Validate Script**
- Errors/warnings displayed in dialog (if any)

## Integration Requirements

The rAthena Tools menu automatically appears when:
1. The rAthena tools modules are available in the project
2. `rathena_script_gen.py` can be imported
3. `rathena_script_ui.py` can be imported

If the tools are not available, the menu silently doesn't appear (graceful degradation).

## File Locations

```
SimpleEdit/
├── PythonApplication1.py          [MODIFIED]
├── rathena_tools_menu.py          [NEW]
├── rathena-tools/
│   ├── rathena_script_gen.py
│   ├── rathena_script_ui.py
│   └── __init__.py
└── ...
```

## Error Handling

The integration includes comprehensive error handling:
- If modules aren't available, menu doesn't appear
- Each dialog has try-catch blocks
- User-friendly error messages
- Graceful fallbacks for import failures

## Usage Examples

### Example 1: Quick NPC
```
1. File → New
2. rAthena Tools → Insert Quick NPC
3. Enter: Name="Healer", Map="prontera", X=150, Y=150, Sprite=111
4. Click Create
5. Script inserted with template NPC
```

### Example 2: Function Creation
```
1. rAthena Tools → New Function
2. Name: "my_function"
3. Parameters: "player, amount"
4. Body:
   set @result, @result + amount;
   mes "Added: " + amount;
   return @result;
5. Click Insert
```

### Example 3: Dialog Builder
```
1. rAthena Tools → Dialog Builder...
2. Example generates dialog commands
3. Click Generate & Insert
4. Dialog sequence added to current script
```

## Menu Items Details

### New NPC Script
Opens the NPC Wizard for guided NPC creation.

### New Function
Dialog to create reusable rAthena functions with:
- Function name (required)
- Parameter list
- Function body
- Auto-generation of script code

### NPC Wizard
Step-by-step wizard for creating NPCs with full configuration.

### Dialog Builder
Builds dialog command sequences for complex NPC interactions.

### Validate Script
Uses the ScriptValidator to check script syntax and conventions.

### Insert Quick NPC
Fast-track NPC creation with minimal configuration.

## Technical Details

### Dependencies
- `rathena_script_gen.py` - Core script generation
- `rathena_script_ui.py` - UI widgets and wizards
- Standard Tkinter libraries

### Architecture
- **Modular Design**: Menu logic isolated in separate file
- **Lazy Loading**: rAthena tools imported only when menu is created
- **Graceful Degradation**: Works without rAthena tools (menu just doesn't appear)
- **Thread-Safe**: All dialogs run on main thread

### Extension Points
To add more menu items:

```python
rathenaMenu.add_command(
    label="Your Feature",
    command=lambda: your_function(root, textArea)
)
```

## Troubleshooting

### Menu doesn't appear
- Check that `rathena_script_gen.py` exists
- Check that `rathena_script_ui.py` exists
- Check Python console for import errors

### "Tools not available" error
- Ensure rAthena tools files are in the correct location
- Check `rathena-tools/` directory structure
- Verify module imports work standalone

### Dialog doesn't respond
- Check if SimpleEdit window is responsive
- Try clicking Cancel and trying again
- Check Python console for detailed error messages

## Next Steps

1. **Verify Installation**: Launch SimpleEdit and check that rAthena Tools menu appears
2. **Test Menu Items**: Try each menu item with sample inputs
3. **Create Scripts**: Use the tools to generate rAthena scripts
4. **Customize**: Add your own menu items following the pattern in `rathena_tools_menu.py`

## Files Modified
- `PythonApplication1.py` - Added rAthena Tools menu initialization

## Files Created
- `rathena_tools_menu.py` - Complete rAthena Tools menu implementation

## Support
For issues or questions:
1. Check that all rAthena tool files exist in `rathena-tools/`
2. Verify the menu appears when SimpleEdit starts
3. Check Python console output for error messages
4. Review the RATHENA_TOOLS_README.md in rathena-tools directory

---

**Integration Complete!** The rAthena Tools menu is now fully integrated with SimpleEdit and ready to use.
