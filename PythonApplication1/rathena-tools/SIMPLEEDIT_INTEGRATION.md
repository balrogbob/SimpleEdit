# SimpleEdit Integration Guide

## Quick Integration for SimpleEdit

This guide explains how to integrate the rAthena Script Generator into SimpleEdit as a plugin/feature.

---

## File Structure

```
SimpleEdit/
├── main_app.py                    (Main SimpleEdit code)
├── plugins/
│   ├── __init__.py               (Empty file)
│   ├── rathena_plugin.py         (Plugin wrapper - create this)
│   ├── rathena_script_gen.py     (Copy from toolkit)
│   └── rathena_script_ui.py      (Copy from toolkit)
└── ui/
    └── rathena_dialog.py         (UI implementation - optional)
```

---

## Step 1: Copy Core Files

Copy these files from the toolkit to SimpleEdit:
- `rathena_script_gen.py` → `SimpleEdit/plugins/`
- `rathena_script_ui.py` → `SimpleEdit/plugins/`
- Create empty `SimpleEdit/plugins/__init__.py`

---

## Step 2: Create Plugin Wrapper

Create `SimpleEdit/plugins/rathena_plugin.py`:

```python
"""
rAthena Script Generator Plugin for SimpleEdit
Bridges the generator to SimpleEdit's UI and editor
"""

from plugins.rathena_script_gen import (
    ScriptGenerator, ScriptNPC, ScriptFunction, LogLevel
)
from plugins.rathena_script_ui import (
    SimpleEditIntegration, ScriptValidator, DialogBuilder
)
from typing import Callable, Optional


class RathenaScriptPlugin:
    """Main plugin class for SimpleEdit integration"""
    
    def __init__(self, editor_ref):
        """
        Initialize plugin
        
        Args:
            editor_ref: Reference to main SimpleEdit instance
        """
        self.editor = editor_ref
        self.generator = ScriptGenerator(log_callback=self._on_log)
        self.integration = SimpleEditIntegration(self.generator)
        self.current_file = None
        
    def _on_log(self, level: LogLevel, message: str):
        """Receive log messages from generator"""
        # Send to SimpleEdit's status bar or output panel
        self.editor.log(f"[{level.value}] {message}")
    
    # --- File Operations ---
    
    def new_script_project(self):
        """Create new script project"""
        self.integration.on_new_project()
        self.editor.new_file("Script Name", language="rathena")
        self.editor.log("New rAthena script project created")
    
    def open_script_project(self, filepath: str):
        """Open existing script project"""
        self.current_file = filepath
        self.editor.log(f"Opening: {filepath}")
        # Load and parse if custom format
    
    def save_script_project(self):
        """Save current script project"""
        if self.current_file:
            self.editor.log(f"Saving: {self.current_file}")
        return self.integration.on_save_project()
    
    def export_script(self, filepath: str) -> bool:
        """Export generated script to file"""
        success = self.integration.on_export(filepath)
        if success:
            self.editor.log(f"Script exported to: {filepath}")
        else:
            self.editor.error("Export failed")
        return success
    
    # --- Script Building ---
    
    def add_npc(self, npc: ScriptNPC) -> bool:
        """Add NPC to current script"""
        success = self.generator.add_npc(npc)
        if success:
            self.editor.log(f"Added NPC: {npc.name}")
            self._update_preview()
        return success
    
    def add_function(self, func: ScriptFunction) -> bool:
        """Add function to current script"""
        success = self.generator.add_function(func)
        if success:
            self.editor.log(f"Added function: {func.name}")
            self._update_preview()
        return success
    
    def set_metadata(self, name: str, author: str = "", description: str = ""):
        """Set script metadata"""
        self.generator.set_metadata(name, author, description)
        self.editor.log(f"Script metadata: {name} by {author}")
    
    # --- Preview & Validation ---
    
    def preview_script(self) -> str:
        """Get current script preview"""
        return self.integration.on_preview()
    
    def validate_script(self) -> tuple:
        """Validate current script"""
        return ScriptValidator.validate_script(self.generator)
    
    def _update_preview(self):
        """Update script preview in editor"""
        preview = self.preview_script()
        self.editor.show_preview(preview, language="rathena")
    
    # --- UI Dialogs ---
    
    def open_npc_wizard(self):
        """Open NPC wizard dialog"""
        self.editor.show_dialog("npc_wizard")
    
    def open_dialog_builder(self):
        """Open dialog builder window"""
        self.editor.show_dialog("dialog_builder")
    
    def open_templates(self):
        """Show available templates"""
        self.editor.show_dialog("templates")
    
    # --- Status ---
    
    def get_status(self) -> dict:
        """Get current plugin status"""
        return self.integration.get_status_info()
    
    def get_stats(self) -> str:
        """Get formatted statistics"""
        status = self.get_status()
        return f"""
NPCs: {status['npcs']}
Functions: {status['functions']}
Script: {status['script_name']}
Author: {status['author']}
        """


# Plugin instance (singleton)
_plugin_instance: Optional[RathenaScriptPlugin] = None


def get_plugin(editor_ref) -> RathenaScriptPlugin:
    """Get or create plugin instance"""
    global _plugin_instance
    if _plugin_instance is None:
        _plugin_instance = RathenaScriptPlugin(editor_ref)
    return _plugin_instance
```

---

## Step 3: Register with SimpleEdit

Add to SimpleEdit's main initialization code:

```python
# In SimpleEdit/main.py or plugin loader

from plugins.rathena_plugin import get_plugin

class SimpleEdit:
    def __init__(self):
        # ... existing initialization ...
        
        # Initialize rAthena plugin
        self.rathena_plugin = get_plugin(self)
        self._setup_rathena_menu()
    
    def _setup_rathena_menu(self):
        """Set up rAthena menu items"""
        menu = self.create_menu("rAthena")
        
        menu.add_item("New Script Project", 
                     self.rathena_plugin.new_script_project)
        menu.add_item("Open Script Project", 
                     lambda: self.open_file(
                         filter="rAthena Projects (*.json)",
                         callback=self.rathena_plugin.open_script_project))
        
        menu.add_separator()
        
        menu.add_item("NPC Wizard", 
                     self.rathena_plugin.open_npc_wizard)
        menu.add_item("Dialog Builder", 
                     self.rathena_plugin.open_dialog_builder)
        menu.add_item("View Templates", 
                     self.rathena_plugin.open_templates)
        
        menu.add_separator()
        
        menu.add_item("Preview Script", 
                     self.rathena_plugin._update_preview)
        menu.add_item("Validate Script", 
                     self._validate_current_script)
        menu.add_item("Export Script", 
                     lambda: self._export_current_script())
        
        menu.add_separator()
        
        menu.add_item("Script Guide (F1)", 
                     lambda: self.open_file("RATHENA_SCRIPT_GUIDE.md"))
        menu.add_item("Quick Reference (Ctrl+?)", 
                     lambda: self.open_file("QUICK_REFERENCE.md"))
    
    def _validate_current_script(self):
        """Validate and display results"""
        valid, errors = self.rathena_plugin.validate_script()
        
        if valid:
            self.show_message("Script Validation", 
                            "✓ Script is valid and ready to export!",
                            type="success")
        else:
            error_text = "\n".join(f"  - {e}" for e in errors)
            self.show_message("Script Validation Errors",
                            f"Errors found:\n{error_text}",
                            type="error")
    
    def _export_current_script(self):
        """Export script to file"""
        filepath = self.save_file_dialog(
            title="Export rAthena Script",
            filter="rAthena Scripts (*.txt)|All Files (*.*)"
        )
        
        if filepath:
            if self.rathena_plugin.export_script(filepath):
                self.show_message("Export Successful",
                                f"Script exported to:\n{filepath}",
                                type="success")
            else:
                self.show_message("Export Failed",
                                "Could not export script",
                                type="error")
```

---

## Step 4: Create UI Dialogs (Optional but Recommended)

Create `SimpleEdit/ui/rathena_dialogs.py`:

```python
"""
UI Dialog implementations for rAthena script generator
Compatible with PyQt, Tkinter, or other frameworks
"""

from typing import Callable, Optional


class NPCWizardDialog:
    """Visual NPC wizard dialog"""
    
    def __init__(self, parent, on_complete: Callable):
        self.on_complete = on_complete
        self.parent = parent
        
        # Build UI (framework-specific)
        self._build_ui()
    
    def _build_ui(self):
        """Build dialog UI - implement for your framework"""
        # This would contain framework-specific UI code
        pass
    
    def show(self):
        """Display dialog"""
        pass


class DialogBuilderWindow:
    """Visual dialog builder window"""
    
    def __init__(self, parent):
        self.parent = parent
        self._build_ui()
    
    def _build_ui(self):
        """Build dialog builder UI"""
        pass
    
    def get_dialog_builder(self):
        """Get configured DialogBuilder instance"""
        pass


class TemplatesDialog:
    """Templates selection dialog"""
    
    def __init__(self, parent, on_select: Callable):
        self.on_select = on_select
        self.parent = parent
        self._build_ui()
    
    def _build_ui(self):
        """Build templates UI"""
        pass
```

---

## Step 5: Add Menu Shortcuts

Add to SimpleEdit's shortcuts configuration:

```python
SHORTCUTS = {
    "rathena_new": "Ctrl+Shift+N",
    "rathena_preview": "Ctrl+Shift+P",
    "rathena_export": "Ctrl+Shift+E",
    "rathena_validate": "Ctrl+Shift+V",
    "rathena_guide": "F1",
    "rathena_reference": "Ctrl+?",
}
```

---

## Step 6: Add Language Support

Create `SimpleEdit/syntax/rathena.py` (optional, for syntax highlighting):

```python
"""
rAthena syntax highlighting for SimpleEdit
"""

KEYWORDS = [
    'mes', 'next', 'close', 'close2', 'clear', 'end',
    'if', 'else', 'switch', 'case', 'default', 'break',
    'for', 'while', 'do',
    'getitem', 'delitem', 'countitem',
    'warp', 'goto', 'return', 'callfunc', 'callsub',
    'set', 'input', 'menu', 'select',
    'function', 'script', 'npc',
    'OnInit', 'OnTouch', 'OnClock', 'OnDay',
    'true', 'false'
]

FUNCTIONS = [
    'getarg', 'getarraysize', 'getitemname', 'getiteminfo',
    'getequipid', 'getequipname', 'getequiprefinerycnt',
    'strcharinfo', 'rand', 'announce', 'broadcast'
]

VARIABLES = [
    'Zeny', 'Hp', 'MaxHp', 'Sp', 'MaxSp',
    'BaseLevel', 'JobLevel', 'StatusPoint', 'SkillPoint',
    'Weight', 'MaxWeight', 'Sex', 'Class', 'Upper'
]
```

---

## Usage from SimpleEdit

Once integrated, users can:

1. **New rAthena Script** → Create new script project
2. **NPC Wizard** → Guided NPC creation
3. **Dialog Builder** → Build dialogs visually
4. **Validate** → Check for errors before export
5. **Preview** → See generated script in real-time
6. **Export** → Save to .txt file for server

---

## Example: Complete Integration Function

```python
def integrate_rathena_to_simpleedit(editor_instance):
    """
    Complete integration function
    Call this in SimpleEdit's initialization
    """
    from plugins.rathena_plugin import get_plugin
    
    # Get plugin instance
    plugin = get_plugin(editor_instance)
    
    # Register menu
    editor_instance.register_menu("rAthena", [
        ("New Script Project", plugin.new_script_project, "Ctrl+Shift+N"),
        ("Open Script", plugin.open_script_project, "Ctrl+Shift+O"),
        ("Save Script", plugin.save_script_project, "Ctrl+Shift+S"),
        None,  # Separator
        ("NPC Wizard", plugin.open_npc_wizard, "Ctrl+Shift+W"),
        ("Dialog Builder", plugin.open_dialog_builder, "Ctrl+Shift+D"),
        ("Templates", plugin.open_templates, "Ctrl+Shift+T"),
        None,
        ("Preview", plugin._update_preview, "Ctrl+Shift+P"),
        ("Validate", editor_instance._validate_current_script, "Ctrl+Shift+V"),
        ("Export", editor_instance._export_current_script, "Ctrl+Shift+E"),
        None,
        ("Script Guide", lambda: editor_instance.open_file(
            "RATHENA_SCRIPT_GUIDE.md"), "F1"),
        ("Quick Reference", lambda: editor_instance.open_file(
            "QUICK_REFERENCE.md"), "Ctrl+?"),
    ])
    
    # Register syntax highlighter
    editor_instance.register_language("rathena", {
        'keywords': KEYWORDS,
        'functions': FUNCTIONS,
        'variables': VARIABLES,
    })
    
    return plugin
```

---

## Testing the Integration

Create a test file `SimpleEdit/test_rathena_integration.py`:

```python
"""Test rAthena plugin integration"""

from plugins.rathena_plugin import RathenaScriptPlugin
from plugins.rathena_script_gen import ScriptNPC


class MockEditor:
    """Mock editor for testing"""
    def log(self, msg): print(f"[LOG] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")
    def show_preview(self, content, language): print(f"[PREVIEW] {language}")
    def show_dialog(self, dialog_type): print(f"[DIALOG] {dialog_type}")


def test_basic_flow():
    """Test basic plugin workflow"""
    editor = MockEditor()
    plugin = RathenaScriptPlugin(editor)
    
    # Create NPC
    npc = ScriptNPC("TestNPC", "prontera", 100, 100)
    npc.add_command('mes "Hello";')
    npc.add_command('close;')
    
    # Add to plugin
    plugin.add_npc(npc)
    
    # Validate
    valid, errors = plugin.validate_script()
    print(f"Valid: {valid}")
    
    # Export (mock)
    script = plugin.preview_script()
    print(f"Script lines: {len(script.split(chr(10)))}")


if __name__ == "__main__":
    test_basic_flow()
```

---

## Support & Help

If integration issues occur:

1. Check that all files are in correct locations
2. Verify imports match file structure
3. Test with simple example first
4. Check SimpleEdit's plugin loading mechanism
5. Refer to RATHENA_TOOLS_README.md for API details

---

**Version:** 1.0  
**Last Updated:** 2025-05-17
