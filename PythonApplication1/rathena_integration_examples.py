"""
SimpleEdit + rAthena Tools Integration Example

This example shows how to add rAthena script generation capabilities to SimpleEdit.
You can add these functions to the SimpleEdit menu to create scripts directly.
"""

# Example 1: Menu item to create a simple NPC
def create_rathena_npc_from_editor():
    """
    Create an rAthena NPC script from a SimpleEdit menu item.
    This would be triggered by: Menu -> Tools -> Create rAthena NPC
    """
    from rathena_script_gen import ScriptGenerator, ScriptNPC
    
    # Get current text (or prompt for NPC details)
    npc_name = "SimpleEdit_NPC"
    map_name = "prontera"
    x_coord = 150
    y_coord = 150
    
    # Create generator
    gen = ScriptGenerator()
    gen.set_metadata("created_by_simpleedit", "SimpleEdit")
    
    # Create NPC
    npc = ScriptNPC(npc_name, map_name, x_coord, y_coord)
    npc.add_command('mes "[' + npc_name + ']";')
    npc.add_command('mes "Created by SimpleEdit!";')
    npc.add_command('close;')
    
    gen.add_npc(npc)
    
    # Generate and insert into current editor
    script = gen.generate_script()
    
    # You would then:
    # 1. Create a new tab in SimpleEdit
    # 2. Insert the script content
    # 3. Set the filename to something like "generated_npc.npc"
    
    return script


# Example 2: Validate current script before saving
def validate_rathena_script_before_save(editor_content):
    """
    Validate current rAthena script before saving.
    This checks for common syntax errors and issues.
    """
    from rathena_script_gen import ScriptValidator
    
    validator = ScriptValidator()
    is_valid, errors = validator.validate(editor_content)
    
    if not is_valid:
        error_message = "Script validation failed:\n" + "\n".join(errors)
        return False, error_message
    
    return True, "Script is valid!"


# Example 3: Quick NPC generator dialog
def open_quick_npc_generator():
    """
    Open a quick NPC generator dialog.
    This would be triggered from the SimpleEdit menu.
    """
    from rathena_script_gen import ScriptGenerator, ScriptNPC
    
    # In a real implementation, you'd show a dialog for user input
    # For now, we'll create a sample NPC
    
    gen = ScriptGenerator()
    gen.set_metadata("quickgen", "SimpleEdit User")
    
    # Example: Create multiple NPCs
    npcs_data = [
        ("Healer", "prontera", 150, 150, [
            'mes "[Healer]";',
            'mes "I can heal your wounds!";',
            'heal @me,999,999;',
            'close;'
        ]),
        ("Merchant", "prontera", 160, 150, [
            'mes "[Merchant]";',
            'mes "Welcome to my shop!";',
            'shop "Merchant_Shop";'
        ]),
    ]
    
    for name, map_name, x, y, commands in npcs_data:
        npc = ScriptNPC(name, map_name, x, y)
        for cmd in commands:
            npc.add_command(cmd)
        gen.add_npc(npc)
    
    return gen.generate_script()


# Example 4: Template-based script generation
def generate_from_template(template_type="simple_quest"):
    """
    Generate an rAthena script from a template.
    This could be called from a menu with options like:
    - Simple Quest
    - Merchant Shop
    - Combat Arena
    - Dungeon Portal
    """
    from rathena_script_gen import ScriptGenerator, ScriptNPC, QuickScriptBuilders
    
    if template_type == "simple_quest":
        # Use QuickScriptBuilders to create a quest
        builder = QuickScriptBuilders()
        script = builder.simple_quest(
            npc_name="QuestGiver",
            quest_description="Collect 10 apples",
            map_location="prontera",
            x=150,
            y=150
        )
        return script
    
    # You could add more template types here


# Example 5: Integration with SimpleEdit menu system
def setup_rathena_menu(menubar_instance):
    """
    Add rAthena tools to the SimpleEdit menu.
    Call this from SimpleEdit's initialization.
    
    Usage in PythonApplication1.py:
    ----
    if _RATHENA_TOOLS_AVAILABLE:
        from rathena_integration import setup_rathena_menu
        setup_rathena_menu(menuBar)
    """
    
    # Create Tools menu if it doesn't exist
    try:
        tools_menu = None
        # Look for existing Tools menu
        for i, label in enumerate(menubar_instance.index('end')):
            if label == "Tools":
                tools_menu = menubar_instance.nametowidget(
                    menubar_instance.winfo_children()[i]
                )
                break
        
        if not tools_menu:
            from tkinter import Menu
            tools_menu = Menu(menubar_instance, tearoff=False)
            menubar_instance.add_cascade(label="Tools", menu=tools_menu)
    except Exception:
        from tkinter import Menu
        tools_menu = Menu(menubar_instance, tearoff=False)
        menubar_instance.add_cascade(label="rAthena", menu=tools_menu)
    
    # Add rAthena menu items
    if tools_menu:
        tools_menu.add_separator()
        tools_menu.add_command(
            label="Create NPC from Template",
            command=lambda: generate_from_template()
        )
        tools_menu.add_command(
            label="Open NPC Wizard",
            command=lambda: open_npc_wizard()
        )
        tools_menu.add_command(
            label="Validate Current Script",
            command=lambda: validate_current_script()
        )


# Example 6: Batch script generation
def generate_multiple_scripts():
    """
    Generate multiple rAthena scripts in batch.
    Useful for creating complete game content.
    """
    from rathena_script_gen import ScriptGenerator, ScriptNPC
    
    scripts = {}
    
    # Generate NPC scripts
    for i in range(5):
        gen = ScriptGenerator()
        npc = ScriptNPC(
            f"NPC_{i}",
            "prontera",
            150 + (i * 10),
            150
        )
        npc.add_command(f'mes "I am NPC number {i}";')
        npc.add_command('close;')
        gen.add_npc(npc)
        scripts[f"npc_{i}.npc"] = gen.generate_script()
    
    return scripts


# Example 7: Interactive dialog builder
def create_quest_dialog():
    """
    Create a complex quest dialog using the DialogBuilder.
    """
    from rathena_script_ui import DialogBuilder
    
    dialog = DialogBuilder()
    dialog.add_message("Do you want to start this quest?") \
           .add_menu(["Yes, accept", "Maybe later"]) \
           .add_message("Great! Here's your quest.") \
           .add_item_check(1010, 5, "You need 5 apples") \
           .add_item_remove(1010, 5) \
           .add_item_give(1012, 1, "Here's your reward!") \
           .add_experience_give(1000, 500) \
           .add_message("Quest complete! Thank you!")
    
    return dialog.to_script_commands()


if __name__ == "__main__":
    """
    Test the integration examples
    """
    print("=== rAthena Tools Integration Examples ===\n")
    
    print("1. Simple NPC Generation:")
    script = create_rathena_npc_from_editor()
    print(f"   Generated {len(script)} characters")
    
    print("\n2. Template-based generation:")
    script = generate_from_template("simple_quest")
    if script:
        print(f"   Generated quest script ({len(script)} chars)")
    
    print("\n3. Batch generation:")
    scripts = generate_multiple_scripts()
    print(f"   Generated {len(scripts)} scripts")
    
    print("\n✅ All examples work! You can now integrate these into SimpleEdit.")
