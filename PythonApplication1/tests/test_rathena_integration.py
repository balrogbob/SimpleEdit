#!/usr/bin/env python3
"""Test script for rAthena tools integration with SimpleEdit."""

import unittest
import sys
import os

# Get the directory where rathena_script_gen.py and rathena_script_ui.py are located
# This is the PythonApplication1 directory
script_dir = os.path.dirname(os.path.abspath(__file__))

# If this script is in the tests/ subdirectory, go up one level
if os.path.basename(script_dir) == 'tests':
    script_dir = os.path.dirname(script_dir)

# Add the module directory to path
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Add rathena-tools to path
rathena_path = os.path.join(script_dir, 'rathena-tools')
if os.path.isdir(rathena_path):
    sys.path.insert(0, rathena_path)


class TestRathenaIntegration(unittest.TestCase):
    """Test rAthena tools integration with SimpleEdit."""

    def test_01_imports(self):
        """Test direct module imports."""
        try:
            from rathena_script_gen import ScriptGenerator, ScriptNPC
            from rathena_script_ui import DialogBuilder, NPCWizard
        except ImportError as e:
            self.fail(f"Failed to import: {e}")

    def test_02_create_instances(self):
        """Test creating instances of rAthena tools."""
        from rathena_script_gen import ScriptGenerator, ScriptNPC
        
        gen = ScriptGenerator()
        self.assertIsNotNone(gen)
        
        npc = ScriptNPC("TestNPC", "prontera", 150, 150)
        self.assertIsNotNone(npc)

    def test_03_convenience_functions(self):
        """Test convenience functions."""
        from rathena_script_gen import ScriptGenerator, ScriptNPC
        from rathena_script_ui import DialogBuilder
        
        gen = ScriptGenerator()
        npc = ScriptNPC("Merchant", "prontera", 100, 100)
        gen.add_npc(npc)
        
        builder = DialogBuilder()
        builder.add_message("Hello!")
        self.assertIsNotNone(builder)

    def test_04_generate_script(self):
        """Test script generation."""
        from rathena_script_gen import ScriptGenerator, ScriptNPC
        
        gen = ScriptGenerator()
        gen.set_metadata("test_script", "Test User")
        npc = ScriptNPC("TestNPC", "prontera", 150, 150)
        npc.add_command('mes "[TestNPC]";')
        npc.add_command('mes "Hello, adventurer!";')
        npc.add_command('close;')
        gen.add_npc(npc)
        script = gen.generate_script()
        
        self.assertIsNotNone(script)
        self.assertGreater(len(script), 20)
        self.assertIn("prontera", script)


if __name__ == '__main__':
    unittest.main()
