# rAthena Tools Menu - Quick Reference

## Menu Location
**Top Menu Bar → rAthena Tools** (appears between "Symbols" and tools menus)

## Menu Items at a Glance

| Menu Item | Shortcut | Purpose | When to Use |
|-----------|----------|---------|------------|
| New NPC Script | — | Launch NPC Wizard | Creating new NPCs from scratch |
| New Function | — | Create rAthena function | Writing reusable functions |
| NPC Wizard... | — | Interactive NPC builder | Step-by-step NPC creation |
| Dialog Builder... | — | Dialog sequence builder | Creating complex NPC dialogs |
| Validate Script | — | Check script validity | Before saving/deploying scripts |
| Insert Quick NPC | — | Insert template NPC | Quick NPC prototyping |

## Step-by-Step Guides

### Creating Your First NPC (5 minutes)

1. **Open SimpleEdit**
   - Launch SimpleEdit application
   
2. **Create New File**
   - File → New
   
3. **Insert Quick NPC**
   - rAthena Tools → Insert Quick NPC
   - Fill dialog:
     - NPC Name: `MyNPC`
     - Map: `prontera`
     - X Position: `100`
     - Y Position: `100`
     - Sprite ID: `111`
   - Click "Create"
   
4. **View Generated Script**
   - Script automatically inserted into editor
   - Shows NPC definition with basic dialog
   
5. **Save Script**
   - File → Save As
   - Choose location and filename
   - Click Save

### Creating a Custom Function (7 minutes)

1. **Open Script**
   - File → New or File → Open existing script
   
2. **Launch Function Creator**
   - rAthena Tools → New Function
   
3. **Configure Function**
   - Name: `calculate_reward`
   - Parameters: `player_level, base_reward`
   - Body (multi-line):
     ```
     set @bonus, player_level * 10;
     set @final, base_reward + @bonus;
     return @final;
     ```
   
4. **Insert Function**
   - Click "Insert"
   - Function code appears in editor
   
5. **Save**
   - File → Save

### Building a Dialog Sequence (10 minutes)

1. **Open Script**
   - File → New
   
2. **Launch Dialog Builder**
   - rAthena Tools → Dialog Builder...
   
3. **Build Dialog**
   - Example commands shown in window
   - Shows pattern for complex dialogs
   - Click "Generate & Insert"
   
4. **Customize Generated Code**
   - Edit the inserted commands
   - Add your own message/logic
   
5. **Test**
   - Save and test in game

### Validating Your Script (2 minutes)

1. **Have Script Open**
   - Script must be in editor
   
2. **Run Validator**
   - rAthena Tools → Validate Script
   
3. **Review Results**
   - "Script is valid!" = All good ✓
   - Error list = Issues to fix
   
4. **Fix Errors**
   - Address any reported issues
   - Re-validate as needed

## Keyboard Shortcuts

Currently, no direct keyboard shortcuts are assigned. Use menu navigation:
- **Alt+R** - Access rAthena Tools menu (if using Windows menu navigation)

## Common Tasks & Solutions

### Task: Create Multiple NPCs
1. **For Each NPC:**
   - rAthena Tools → Insert Quick NPC
   - Enter NPC details
   - Click Create
2. **All NPCs** appear in same script (with separators)

### Task: Reuse Code
1. **Create Function** with common logic
2. **Call Function** from multiple NPCs
3. **Benefits:** DRY principle, easier maintenance

### Task: Build Complex Dialog
1. **Start** with Dialog Builder template
2. **Customize** for your needs
3. **Add** conditionals and logic
4. **Test** in game

### Task: Fix Validation Errors
1. **Run** Validate Script
2. **Note** errors listed
3. **Edit** script in editor
4. **Re-run** Validate Script
5. **Repeat** until valid

## Tips & Tricks

### 💡 Tip 1: Use Quick NPC for Prototyping
- Insert Quick NPC gives you a working template
- Edit and customize from there
- Faster than coding from scratch

### 💡 Tip 2: Validate Before Saving
- Always validate before saving important scripts
- Catches syntax errors early
- Prevents loading errors in-game

### 💡 Tip 3: Organize with Functions
- Create functions for common operations
- Makes scripts cleaner and reusable
- Easier to maintain

### 💡 Tip 4: Use Dialog Builder for Templates
- Don't start dialogs from scratch
- Use builder as starting point
- Modify to your needs

### 💡 Tip 5: Keep Scripts Organized
- One file per NPC or system
- Use consistent naming
- Document complex functions

## Menu Appearance

If rAthena Tools menu doesn't appear:
1. ✓ Verify rathena-tools folder exists
2. ✓ Check rathena_script_gen.py is present
3. ✓ Check rathena_script_ui.py is present
4. ✓ Restart SimpleEdit
5. ✓ Check Python console for errors

## Troubleshooting

### Problem: "Not Available" Message
**Solution:** Ensure rAthena tools are installed in rathena-tools/ folder

### Problem: Dialog Opens Then Nothing Happens
**Solution:** Try again or restart SimpleEdit

### Problem: Generated Code Looks Wrong
**Solution:** Edit as needed - templates are starting points, not final code

### Problem: Validation Always Says Errors
**Solution:** Read error messages carefully - they indicate what needs fixing

## Keyboard Navigation

### In Dialogs:
- **Tab** - Move between fields
- **Enter** - Confirm (same as clicking button)
- **Escape** - Cancel dialog
- **Alt+O** or **Alt+C** - Shortcut to buttons (if available)

## Output Locations

All generated code:
- **Inserted at end** of current editor content
- **Appended with newlines** for separation
- **Ready to edit** immediately

## File Compatibility

Works with rAthena scripts:
- `.txt` files (plain text NPC scripts)
- `.npc` files (if you use that extension)
- Any text format

## Next Steps

1. **Try Insert Quick NPC** - Easiest starting point
2. **Read generated code** - Learn syntax patterns
3. **Experiment with New Function** - Create reusable code
4. **Use Dialog Builder** - Build complex interactions
5. **Validate frequently** - Catch errors early

## Getting Help

1. Check **RATHENA_TOOLS_MENU_SETUP.md** for setup details
2. Review **RATHENA_SCRIPT_GUIDE.md** for scripting reference
3. Look at examples in generated code templates
4. Check Python console (View → Output) for error details

---

**Happy rAthena Scripting!** 🎮

With the rAthena Tools menu, you can create powerful scripts faster and with fewer errors.
