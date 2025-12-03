# rAthena Tools Menu - Complete User Guide

**Version:** 1.0  
**Integration:** SimpleEdit Text Editor  
**Author:** SimpleEdit Development Team

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Menu Items Reference](#menu-items-reference)
4. [NPC Wizard](#npc-wizard)
5. [Dialog Builder](#dialog-builder)
6. [Function Creator](#function-creator)
7. [Script Validator](#script-validator)
8. [Quick NPC](#quick-npc)
9. [Advanced Features](#advanced-features)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The **rAthena Tools** menu provides a comprehensive suite of visual tools for creating and editing rAthena server scripts directly within SimpleEdit. These tools eliminate the need to memorize script syntax and provide interactive wizards for common scripting tasks.

### Key Features

✅ **Visual NPC Creation** - Step-by-step wizard for building NPCs  
✅ **Interactive Dialog Builder** - Drag-and-drop dialog creation  
✅ **Menu Branching** - Visual menu system with conditional branches  
✅ **Live Preview** - See generated code in real-time  
✅ **Script Validation** - Check scripts for common errors  
✅ **Template System** - Quick insertion of common NPC types  

### Menu Location

Access the rAthena Tools via the main menu bar:

```
SimpleEdit → rAthena Tools → [Tool Selection]
```

---

## Getting Started

### Prerequisites

1. **SimpleEdit Editor** - Version with rAthena Tools integration
2. **rathena-tools Package** - Located in `PythonApplication1/rathena-tools/`
3. **Python 3.x** - Required for script generation

### Quick Start

1. Open SimpleEdit
2. Create a new file or open existing `.txt` script
3. Go to **rAthena Tools** menu
4. Select **NPC Wizard** for guided NPC creation
5. Follow the step-by-step prompts
6. Generated script appears in your editor!

---

## Menu Items Reference

### Complete Menu Structure

```
rAthena Tools
├── New NPC Script          (Ctrl+Shift+N) - Launch NPC Wizard
├── New Function            (Ctrl+Shift+F) - Create custom function
├── ────────────────
├── NPC Wizard...           - Step-by-step NPC creator
├── Dialog Builder...       - Visual dialog designer
├── ────────────────
├── Validate Script         - Check current script
└── Insert Quick NPC        - Template-based quick insert
```

### Tool Descriptions

| Tool | Purpose | Best For |
|------|---------|----------|
| **NPC Wizard** | Complete NPC creation | New NPCs, complex dialogs |
| **Dialog Builder** | Dialog sequence only | Adding dialogs to existing NPCs |
| **Function Creator** | Custom functions | Reusable script functions |
| **Script Validator** | Error checking | Testing scripts before deployment |
| **Quick NPC** | Template insertion | Simple NPCs (healer, warp, etc.) |

---

## NPC Wizard

The **NPC Wizard** guides you through creating a complete NPC in 5 easy steps.

### Step-by-Step Guide

#### **Step 1: Name and Location**

Define where your NPC will appear in the game world.

**Fields:**
- **NPC Name:** Display name (e.g., "Quest Giver")
- **Map:** Map identifier (e.g., "prontera")
- **X Position:** Horizontal coordinate (0-400+)
- **Y Position:** Vertical coordinate (0-400+)
- **Direction:** Facing direction (0-7)
  - 0 = South, 1 = SW, 2 = West, 3 = NW
  - 4 = North, 5 = NE, 6 = East, 7 = SE

**Example:**
```
Name: Helper
Map: prontera
X: 150
Y: 150
Direction: 4 (North)
```

#### **Step 2: Appearance**

Choose the NPC's visual sprite.

**Features:**
- Sprite ID dropdown (common sprites pre-loaded)
- Live sprite preview (if sprite images available)
- Manual ID entry supported

**Common Sprite IDs:**
- `111` - Soldier
- `112` - Merchant
- `120` - Generic NPC
- `4_F_KAFRA1` - Kafra

**Preview Display:**
- Shows sprite image when available
- Falls back to filename if image unsupported
- Scales large sprites automatically

#### **Step 3: Dialog Editor** ⭐

Build your NPC's dialog sequence using the interactive editor.

**Action Buttons:**

| Button | Function | Example |
|--------|----------|---------|
| **Message** | Add dialog text | "Hello, adventurer!" |
| **Next** | Add next button | Pauses for user input |
| **Close** | Add close button | Ends dialog |
| **Menu** | Add menu choices | Accept/Decline/Ask More |
| **Script** | Add raw command | `set Zeny, Zeny - 100` |

**Advanced Actions:**

| Button | Function | Parameters |
|--------|----------|------------|
| **Warp** | Teleport player | Map, X, Y coordinates |
| **Check Item** | Verify item possession | Item ID, Count |
| **Give Item** | Award items | Item ID, Amount |
| **Remove Item** | Take items | Item ID, Amount |

**Menu Branching System:**

When adding a menu, you can define what happens for each choice:

1. Enter options: `Accept|Decline|Tell me more`
2. Choose "Yes" to define branches
3. For each option, a **full dialog builder** opens
4. Build the branch dialog visually
5. System generates proper `switch/case` code

**Example Workflow:**
```
1. Add Message: "I have a quest!"
2. Add Next
3. Add Menu: "Accept|Decline"
   
   Accept Branch:
   - Add Message: "Great! Collect 10 apples."
   - Add Script: set QUEST_VAR, 1
   - Add Close
   
   Decline Branch:
   - Add Message: "Maybe later."
   - Add Close

4. Preview shows complete switch/case structure!
```

**Reorder Controls:**
- **↑** Move action up
- **↓** Move action down
- **✕ Remove** Delete action

#### **Step 4: NPC Type**

Select the NPC's functional type.

**Available Types:**
- Dialog NPC (default)
- Shop Keeper
- Quest Giver
- Healer
- Teleporter
- Custom Script

*Note: Type affects default behaviors and generated code structure.*

#### **Step 5: Confirmation**

Review your NPC before generation.

**Summary Shows:**
- NPC name and location
- Sprite ID
- NPC type
- Number of dialog actions

**Preview:**
- Complete generated script
- Proper formatting and indentation
- Ready to insert into editor

**Actions:**
- **Next** → Generate and insert script
- **Back** → Return to previous step
- **Cancel** → Abort creation

### Generated Script Example

```javascript
prontera,150,150,4	script	Helper	120,{
    mes "[Helper]";
    mes "I have a quest for you!";
    next;
    
    switch(select("Accept:Decline")) {
        case 1:
            mes "Great! Collect 10 apples.";
            set QUEST_VAR, 1;
            close;
            break;
        case 2:
            mes "Maybe later.";
            close;
            break;
    }
}
```

---

## Dialog Builder

The **Dialog Builder** is a standalone tool for creating dialog sequences that can be inserted into any script.

### Interface Layout

```
┌──────────────────────────────────────────────────────┐
│               Dialog Builder                         │
├─────────────────────────┬────────────────────────────┤
│ LEFT: Actions           │ RIGHT: Preview             │
├─────────────────────────┼────────────────────────────┤
│ Dialog Actions:         │ Preview:                   │
│ ┌─────────────────────┐ │ ┌────────────────────────┐ │
│ │ Message: Welcome!   │ │ │mes "Welcome!";         │ │
│ │ Next Button         │ │ │next;                   │ │
│ │ Menu: Options [2]   │ │ │switch(select(...)) {   │ │
│ │ Close Button        │ │ │  case 1: ...           │ │
│ └─────────────────────┘ │ │}                       │ │
│                         │ │close;                  │ │
│ Add Action:             │ └────────────────────────┘ │
│ [Msg][Next][Close]      │                            │
│ [Menu][Script]          │ [Insert into Editor]       │
│                         │                            │
│ Advanced:               │                            │
│ [Warp][Check Item]      │                            │
│ [Give Item][Remove]     │                            │
│                         │                            │
│ Reorder: [↑][↓][✕]     │                            │
├─────────────────────────┴────────────────────────────┤
│        [Insert into Script]    [Cancel]              │
└──────────────────────────────────────────────────────┘
```

### Features

#### **Split-Pane Interface**
- **Left:** Action builder with buttons
- **Right:** Live preview of generated code

#### **Live Preview**
- Updates in real-time as you build
- Shows properly formatted code
- Color-coded syntax (if supported)

#### **Dual Insert Options**

1. **Insert into Editor** (Preview Pane)
   - Inserts without closing dialog
   - Allows iterative building
   - Great for testing and refining

2. **Insert into Script** (Bottom)
   - Inserts and closes dialog
   - Shows success confirmation
   - Traditional workflow

### Action Types

#### **Basic Actions**

**Message**
```javascript
mes "Your text here";
```
- Displays dialog text to player
- Supports variables and formatting
- Can include NPC name tags

**Next**
```javascript
next;
```
- Shows "Next" button
- Waits for player input
- Continues to next message

**Close**
```javascript
close;
```
- Ends dialog
- Closes NPC window
- Returns control to player

#### **Interactive Actions**

**Menu**
```javascript
switch(select("Option1:Option2:Option3")) {
    case 1:
        // Option1 code
        break;
    case 2:
        // Option2 code
        break;
    case 3:
        // Option3 code
        break;
}
```

**Creating Menus:**
1. Click **Menu** button
2. Enter options: `Accept|Decline|Ask More`
3. Choose "Yes" for branch definition
4. Build each branch using full dialog builder
5. Branches saved and generated automatically

**Menu Features:**
- Unlimited options
- Full dialog builder per branch
- Visual branch count display
- Nested menus supported

**Script Command**
```javascript
// Any rAthena script command
set Zeny, Zeny - 500;
getitem 501, 10;
warp "geffen", 120, 100;
```

**Command Dropdown Includes:**
- `getitem <id>, <amount>`
- `delitem <id>, <amount>`
- `set <variable>, <value>`
- `if (<condition>) {`
- `warp "<map>", <x>, <y>`
- `heal <hp>, <sp>`
- `input <variable>`
- `setarray <array>, <values>`
- `getarg(<index>)`
- `callfunc("<function>")`
- `callsub <label>`
- `announce "<text>", <flag>`

**Custom Commands:**
- Enter any valid rAthena command
- No validation (trust developer)
- Inserted as raw script

#### **Advanced Actions**

**Warp**
```javascript
warp "mapname", x, y;
```
- Teleports player
- Requires map name and coordinates

**Check Item**
```javascript
if (countitem(item_id) < count)
```
- Verifies player has items
- Used in quest logic
- Returns true/false

**Give Item**
```javascript
getitem item_id, amount;
```
- Awards items to player
- Adds to inventory
- Can specify quantity

**Remove Item**
```javascript
delitem item_id, amount;
```
- Takes items from player
- Used for crafting/quests
- Validates possession first

### Usage Examples

#### **Example 1: Simple Greeting**

**Actions:**
1. Add Message: "Hello, adventurer!"
2. Add Next
3. Add Message: "Welcome to our town!"
4. Add Close

**Generated:**
```javascript
mes "Hello, adventurer!";
next;
mes "Welcome to our town!";
close;
```

#### **Example 2: Shop Dialog**

**Actions:**
1. Add Message: "Welcome to my shop!"
2. Add Menu: "Buy Items|Sell Items|Leave"
   - Buy Items branch:
     - Message: "Here are my wares!"
     - Close
   - Sell Items branch:
     - Message: "What do you want to sell?"
     - Close
   - Leave branch:
     - Message: "Come back soon!"
     - Close

**Generated:**
```javascript
mes "Welcome to my shop!";
switch(select("Buy Items:Sell Items:Leave")) {
    case 1:
        mes "Here are my wares!";
        close;
        break;
    case 2:
        mes "What do you want to sell?";
        close;
        break;
    case 3:
        mes "Come back soon!";
        close;
        break;
}
```

#### **Example 3: Quest with Items**

**Actions:**
1. Add Message: "I need 10 apples!"
2. Add Next
3. Add Check Item: ID=512, Count=10
4. Add Message: "You have them! Here's your reward."
5. Add Give Item: ID=501, Amount=5
6. Add Remove Item: ID=512, Amount=10
7. Add Close

**Generated:**
```javascript
mes "I need 10 apples!";
next;
if (countitem(512) < 10)
mes "You have them! Here's your reward.";
getitem 501, 5;
delitem 512, 10;
close;
```

---

## Function Creator

Create reusable script functions with parameters.

### Interface

**Fields:**
- **Function Name:** Identifier (no spaces)
- **Parameters:** Comma-separated list
- **Function Body:** Multi-line script editor

### Features

- Syntax highlighting in body editor
- Parameter validation
- Auto-formatting
- Direct insertion

### Example

**Input:**
```
Name: GiveReward
Parameters: item_id, amount, bonus
Body:
    getitem item_id, amount;
    if (bonus > 0) {
        set Zeny, Zeny + bonus;
    }
```

**Generated:**
```javascript
function	GiveReward	{
    getitem getarg(0), getarg(1);
    if (getarg(2) > 0) {
        set Zeny, Zeny + getarg(2);
    }
    return;
}
```

---

## Script Validator

Validate scripts before deployment.

### Validation Checks

✅ **Structure Validation**
- NPC definition present
- Required commands included
- Proper formatting

✅ **Syntax Checks**
- Common command usage
- Basic error detection
- Best practices

### Results

**Valid Script:**
```
✓ Script looks valid!

Contains NPC definition and commands.
```

**Issues Found:**
```
⚠ Validation Issues

Script may be incomplete.

Make sure to include:
• NPC location (e.g., 'prontera')
• NPC commands (e.g., 'mes', 'close')
```

---

## Quick NPC

Rapidly insert template-based NPCs.

### Interface

**Fields:**
- NPC Name
- Map (default: prontera)
- X Position (default: 100)
- Y Position (default: 100)
- Sprite ID (default: 111)

### Generated Template

```javascript
prontera,100,100,4	script	NPCName	111,{
    mes "[NPCName]";
    mes "Hello there!";
    close;
}
```

### Use Cases

- Quick testing NPCs
- Placeholder NPCs
- Simple greeting NPCs
- Starting templates for expansion

---

## Advanced Features

### Menu Branching Deep Dive

#### **Branch Dialog Builder**

Each menu option gets its own **complete dialog builder**:

**Features:**
- Full action list
- Add/remove/reorder controls
- Message, Next, Close, Script buttons
- Nested menu support
- Live action preview

**Example: Complex Quest**

```
Main Menu: "Accept Quest|Decline|Ask About Reward"

Accept Branch Builder:
├── Message: "Great! Find 5 herbs."
├── Script: set QUEST_ACTIVE, 1
├── Next
├── Menu: "Where are herbs?|What do they look like?"
│   ├── Where Branch:
│   │   ├── Message: "In the forest south of town."
│   │   └── Close
│   └── Look Branch:
│       ├── Message: "Small green plants."
│       └── Close
└── Close

Decline Branch Builder:
├── Message: "Maybe another time."
└── Close

Reward Branch Builder:
├── Message: "You'll get 1000 Zeny!"
├── Next
├── Message: "Plus a free potion."
└── Close
```

**Generated Code:**
```javascript
switch(select("Accept Quest:Decline:Ask About Reward")) {
    case 1:
        mes "Great! Find 5 herbs.";
        set QUEST_ACTIVE, 1;
        next;
        switch(select("Where are herbs?:What do they look like?")) {
            case 1:
                mes "In the forest south of town.";
                close;
                break;
            case 2:
                mes "Small green plants.";
                close;
                break;
        }
        close;
        break;
    case 2:
        mes "Maybe another time.";
        close;
        break;
    case 3:
        mes "You'll get 1000 Zeny!";
        next;
        mes "Plus a free potion.";
        close;
        break;
}
```

### Script Command System

#### **{SCRIPT} Prefix**

Commands prefixed with `{SCRIPT}` are inserted as raw script:

**Storage:**
```javascript
DialogAction(MESSAGE, {'message': '{SCRIPT}set Zeny, Zeny - 100'})
```

**Display:**
```
Script: set Zeny, Zeny - 100
```

**Generated:**
```javascript
set Zeny, Zeny - 100;
```

#### **Command Dropdown**

Pre-loaded common commands:
- Item manipulation
- Variable operations
- Flow control
- Function calls
- System commands

**Custom Entry:**
- Any valid rAthena command
- No syntax validation
- Full developer control

### Live Preview System

#### **Real-time Updates**

Preview updates automatically when:
- Adding actions
- Removing actions
- Reordering actions
- Modifying branches

#### **Preview Features**

- Syntax highlighting
- Proper indentation
- Line numbers (if supported)
- Scrollable view
- Copy-friendly formatting

#### **Insert Workflow**

**Option 1: Preview Insert**
```
Build → Preview Updates → Insert into Editor → Keep Building
```

**Option 2: Final Insert**
```
Build → Preview Updates → Insert into Script → Close & Done
```

---

## Troubleshooting

### Common Issues

#### **"rAthena Tools not available"**

**Cause:** Module import failed

**Solution:**
1. Check `PythonApplication1/rathena-tools/` exists
2. Verify `rathena_script_gen.py` present
3. Verify `rathena_script_ui.py` present
4. Restart SimpleEdit

#### **"No text editor found"**

**Cause:** No active editor tab

**Solution:**
1. Create new file (Ctrl+N)
2. Or open existing file (Ctrl+O)
3. Try tool again

#### **Script doesn't insert**

**Cause:** Focus issue or permission error

**Solution:**
1. Click in editor window first
2. Ensure file is not read-only
3. Check cursor position
4. Try Save As first

#### **Preview not updating**

**Cause:** Dialog builder state issue

**Solution:**
1. Click action to refresh
2. Add/remove dummy action
3. Close and reopen builder

#### **Menu branches not saving**

**Cause:** Didn't click "Save Branch"

**Solution:**
1. Must click "Save Branch" button
2. "Skip" discards changes
3. Check branch count in main list

### Performance Tips

✅ **Build smaller NPCs** - Break complex NPCs into functions  
✅ **Use templates** - Quick NPC for simple cases  
✅ **Test incrementally** - Insert and test frequently  
✅ **Save often** - Save script file before heavy edits  

### Best Practices

✅ **Name NPCs clearly** - Use descriptive names  
✅ **Comment branches** - Add script comments for clarity  
✅ **Validate before deploy** - Always run validator  
✅ **Test in-game** - Use test server first  
✅ **Version control** - Keep backups of scripts  

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+N` | New NPC Script (Wizard) |
| `Ctrl+Shift+F` | New Function |
| `Ctrl+Shift+V` | Validate Script |
| `Ctrl+Shift+D` | Dialog Builder |

*Note: Shortcuts may vary by SimpleEdit version*

---

## Version History

### Version 1.0 (Current)
- ✅ Complete NPC Wizard (5 steps)
- ✅ Interactive Dialog Builder
- ✅ Menu branching with visual builder
- ✅ Live preview system
- ✅ Dual insert options
- ✅ Script command dropdown
- ✅ Advanced actions (Warp, Items)
- ✅ Function creator
- ✅ Script validator
- ✅ Quick NPC templates

---

## Additional Resources

### Documentation
- [rAthena Script Guide](RATHENA_SCRIPT_GUIDE.md)
- [Script Commands Reference](../script_commands.txt)
- [Quest Variables](../quest_variables.txt)
- [Examples](EXAMPLES.md)

### External Links
- [rAthena Wiki](https://github.com/rathena/rathena/wiki)
- [Script Commands](https://github.com/rathena/rathena/wiki/Script-Commands)
- [Sample Scripts](https://github.com/rathena/rathena/tree/master/npc)

---

## Support

For issues or feature requests:

1. Check [Troubleshooting](#troubleshooting) section
2. Review [Examples](EXAMPLES.md) documentation
3. Submit issue on GitHub repository
4. Contact SimpleEdit support

---

**Last Updated:** 2024  
**Maintained by:** SimpleEdit Development Team  
**License:** MIT

---

*This documentation is part of the SimpleEdit rAthena Tools integration package.*
