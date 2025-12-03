# rAthena Tools - Quick Reference Card

**Fast reference for SimpleEdit rAthena Tools Menu**

---

## Menu Access

```
SimpleEdit → rAthena Tools → [Select Tool]
```

---

## Tools at a Glance

| Tool | Shortcut | Use When |
|------|----------|----------|
| **NPC Wizard** | `Ctrl+Shift+N` | Creating complete NPCs |
| **Dialog Builder** | `Ctrl+Shift+D` | Building dialog sequences |
| **Function Creator** | `Ctrl+Shift+F` | Making reusable functions |
| **Script Validator** | `Ctrl+Shift+V` | Testing script validity |
| **Quick NPC** | - | Need simple template NPC |

---

## NPC Wizard Steps

```
1. Name & Location  → Set map position
2. Appearance       → Choose sprite
3. Dialog Editor    → Build interactions
4. NPC Type         → Select category  
5. Confirmation     → Review & insert
```

---

## Dialog Builder Actions

### Basic
- **Message** → Display text
- **Next** → Wait for input
- **Close** → End dialog
- **Menu** → Choice selection
- **Script** → Raw command

### Advanced
- **Warp** → Teleport player
- **Check Item** → Verify possession
- **Give Item** → Award items
- **Remove Item** → Take items

---

## Menu Branching

```
1. Click "Menu" button
2. Enter options: Accept|Decline|More
3. Choose "Yes" for branches
4. Build each branch visually
5. Auto-generates switch/case
```

**Branch Builder Opens:**
- Full action list
- Add/remove/reorder
- Save or Skip

---

## Script Commands

### Common Commands

```javascript
// Items
getitem <id>, <amount>
delitem <id>, <amount>
countitem(<id>)

// Variables
set <var>, <value>
@variable           // Account var
$variable           // Global var
.@variable          // Local var

// Flow Control
if (<condition>) { }
switch(select(...)) { }
goto <label>

// Player Actions
warp "map", x, y
heal <hp>, <sp>
input <variable>

// Functions
callfunc("<name>")
callsub <label>
getarg(<index>)

// System
announce "text", <flag>
end;
close;
```

---

## Preview & Insert

### Dialog Builder

**Two insert options:**

1. **Preview Pane**
   - Button: "Insert into Editor"
   - Stays open for iteration
   
2. **Bottom Button**
   - Button: "Insert into Script"
   - Closes after insert

Both insert same content!

---

## Script Format

### NPC Structure
```javascript
mapname,x,y,facing	script	NPCName	SpriteID,{
    mes "[NPCName]";
    mes "Dialog text";
    next;
    close;
}
```

### Function Structure
```javascript
function	FunctionName	{
    // commands
    return;
}
```

---

## Common Sprite IDs

| ID | Description |
|----|-------------|
| 111 | Soldier |
| 112 | Merchant |
| 120 | Generic NPC |
| 4_F_KAFRA1 | Kafra |
| 4_M_BARBER | Barber |
| 4_M_OILMAN | Oil Merchant |

---

## Direction Values

```
    4 (N)
  3   5
2 (W)   6 (E)
  1   7
    0 (S)
```

---

## Quest Variables

```javascript
QUEST_VAR         // Custom variable
#CASHPOINTS       // Cash shop
Zeny              // Money
BaseLevel         // Level
JobLevel          // Job level
```

---

## Validation Checks

✅ NPC name present  
✅ Map location defined  
✅ Commands included  
✅ Proper syntax  

---

## Tips

💡 **Build incrementally** - Test often  
💡 **Use branches** - Organize complex dialogs  
💡 **Name clearly** - Descriptive NPC names  
💡 **Validate first** - Before deploying  
💡 **Save backups** - Version your scripts  

---

## Troubleshooting Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| Tools unavailable | Check rathena-tools folder exists |
| No editor | Open/create file first |
| Won't insert | Click in editor window |
| Preview stuck | Add/remove action to refresh |
| Branch lost | Must click "Save Branch" |

---

## Examples

### Simple Greeter
```javascript
prontera,150,150,4	script	Greeter	120,{
    mes "[Greeter]";
    mes "Hello!";
    close;
}
```

### Quest Giver
```javascript
prontera,150,150,4	script	Quest	120,{
    mes "[Quest Giver]";
    mes "I need help!";
    next;
    
    switch(select("Accept:Decline")) {
        case 1:
            mes "Thank you!";
            set QUEST_VAR, 1;
            break;
        case 2:
            mes "Maybe later.";
            break;
    }
    close;
}
```

### Healer
```javascript
prontera,150,150,4	script	Healer	120,{
    mes "[Healer]";
    mes "Need healing?";
    next;
    
    heal 100, 100;
    mes "There you go!";
    close;
}
```

---

## Documentation

📖 **Full Guide:** [RATHENA_TOOLS_MENU.md](RATHENA_TOOLS_MENU.md)  
📖 **Script Guide:** [RATHENA_SCRIPT_GUIDE.md](RATHENA_SCRIPT_GUIDE.md)  
📖 **Examples:** [EXAMPLES.md](EXAMPLES.md)  

---

**Version:** 1.0  
**Last Updated:** 2024

---

*Print this card for desk reference!*
