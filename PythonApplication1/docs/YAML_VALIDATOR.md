# rAthena YAML Database Validator

## 🎯 **Overview**

The YAML Database Validator validates rAthena database files (quest_db.yml, item_db.yml, mob_db.yml, etc.) for:
- **YAML syntax errors** (indentation, colons, quotes)
- **Schema compliance** (required fields, data types)
- **Value ranges** (negative values, rate limits)
- **Reference integrity** (monster names, item names, maps)

---

## 📋 **Features**

### **Phase 1: Core Validation** ✅ (Implemented)

1. **YAML Syntax Validation**
   - Indentation errors
   - Missing colons
   - Invalid list syntax
   - Unclosed quotes
   - Invalid characters

2. **Structure Validation**
   - Required sections (Header, Body, Footer)
   - Correct data types
   - Header.Type and Header.Version

3. **Quest Database Schema**
   - Required fields: Id, Title
   - Optional fields: TimeLimit, Targets, Drops
   - Target validation (Mob, Count, Id)
   - Drop validation (Item, Rate, Count)
   - Rate range: 0-10000 (0-100%)

### **Phase 2: Advanced Validation** 🚧 (Planned)

1. **Reference Validation**
   - Unknown monster names
   - Unknown item names
   - Invalid map names
   - Duplicate quest IDs

2. **Item Database Schema**
   - Item properties validation
   - Type/SubType combinations
   - Weight, Buy/Sell prices
   - Script validation

3. **Monster Database Schema**
   - Monster stats validation
   - Sprite IDs
   - Drop rates
   - AI modes

---

## 🚀 **Usage**

### **1. From Menu**

```
rAthena Tools → Validate YAML Database
```

### **2. Validation Results**

The validator shows results in three tabs:

**Errors Tab:**
```
✗ Line 52: Quest entry 1: Missing required field 'Id'
✗ Line 67: Quest entry 3: TimeLimit cannot be negative
```

**Warnings Tab:**
```
⚠ Line 45: Quest entry 1: Rate exceeds 10000 (>100%)
⚠ Line 89: Quest entry 5: Count should be an integer
```

**Suggestions Tab:**
```
💡 Header.Version is recommended
💡 Quest entry 2: Consider adding TimeLimit for timed quests
```

---

## 📝 **Validation Examples**

### **Example 1: Valid Quest Database**

**Input:**
```yaml
Header:
  Type: QUEST_DB
  Version: 3

Body:
  - Id: 1000
    Title: "Sample Quest"
    TimeLimit: 0
    Targets:
      - Mob: Poring
        Count: 10
        Id: 1
    Drops:
      - Mob: 0
        Item: Apple
        Count: 1
        Rate: 1000
```

**Result:**
```
✓ YAML validation passed!
✓ No errors
✓ No warnings
✓ No suggestions
```

---

### **Example 2: Syntax Error**

**Input:**
```yaml
Header:
  Type: QUEST_DB
  Version: 3

Body:
  - Id: 1000
    Title: "Unclosed quote
    TimeLimit: 0
```

**Result:**
```
✗ Line 7: YAML Syntax Error: found unexpected end of stream
```

---

### **Example 3: Schema Error**

**Input:**
```yaml
Header:
  Type: QUEST_DB
  Version: 3

Body:
  - Title: "Missing ID Quest"
    TimeLimit: -100
    Drops:
      - Item: Apple
        Rate: 15000
```

**Result:**
```
✗ Quest entry 1: Missing required field 'Id'
✗ Quest entry 1: TimeLimit cannot be negative
⚠ Quest entry 1, Drop 1: Rate exceeds 10000 (>100%)
```

---

### **Example 4: Type Validation**

**Input:**
```yaml
Header:
  Type: QUEST_DB
  Version: 3

Body:
  - Id: "1000"          # Should be int
    Title: 123          # Should be string
    TimeLimit: "zero"   # Should be int
    Targets:
      - Mob: Poring
        Count: "ten"    # Should be int
```

**Result:**
```
⚠ Quest entry 1: Id should be an integer
⚠ Quest entry 1: Title should be a string
⚠ Quest entry 1: TimeLimit should be an integer
⚠ Quest entry 1, Target 1: Count should be an integer
```

---

## 🔧 **Integration**

### **Standalone Use**

```python
from rathena_yaml_validator import validate_yaml_content

# Read YAML file
with open('quest_db.yml', 'r') as f:
    yaml_text = f.read()

# Validate
errors, warnings, suggestions = validate_yaml_content(yaml_text)

# Display results
for line, col, msg in errors:
    print(f"ERROR Line {line}: {msg}")

for line, col, msg in warnings:
    print(f"WARNING Line {line}: {msg}")
```

### **With SimpleEdit**

The validator is automatically integrated into the rAthena Tools menu when `rathena_yaml_validator.py` is present.

---

## 📊 **Validation Rules**

### **Quest Database (quest_db.yml)**

| Field | Required | Type | Validation |
|-------|----------|------|------------|
| `Id` | ✅ Yes | int | Positive integer |
| `Title` | ✅ Yes | string | Non-empty |
| `TimeLimit` | ❌ No | int | Non-negative |
| `Targets` | ❌ No | list | Valid target objects |
| `Drops` | ❌ No | list | Valid drop objects |

### **Quest Target**

| Field | Required | Type | Validation |
|-------|----------|------|------------|
| `Mob` | ❌ No | string | Valid monster name |
| `Count` | ❌ No | int | Non-negative |
| `Id` | ❌ No | int | Positive integer |
| `Race` | ❌ No | string | Valid race enum |
| `Size` | ❌ No | string | Valid size enum |
| `Element` | ❌ No | string | Valid element enum |

### **Quest Drop**

| Field | Required | Type | Validation |
|-------|----------|------|------------|
| `Mob` | ❌ No | int/string | 0 or valid monster |
| `Item` | ✅ Yes | string | Valid item name |
| `Count` | ❌ No | int | Positive integer |
| `Rate` | ❌ No | int | 0-10000 (0-100%) |

---

## 🎨 **Visual Feedback**

### **In Editor** (Planned)
```yaml
Header:
  Type: QUEST_DB
  Version: 3

Body:
  - Id: 1000           # ✓ Valid
    Title:             # ✗ Empty string error
    TimeLimit: -50     # ⚠ Negative value warning
    Drops:
      - Item: Apple
        Rate: 15000    # ⚠ Rate >100% warning
```

---

## 🚀 **Roadmap**

### **Phase 1: Core Validation** ✅
- [x] YAML syntax parsing
- [x] Structure validation (Header/Body/Footer)
- [x] Quest database schema
- [x] Basic type checking
- [x] Value range validation

### **Phase 2: Reference Validation** 🚧
- [ ] Load monster names from mob_db.yml
- [ ] Load item names from item_db.yml
- [ ] Load map names from maps list
- [ ] Cross-reference validation
- [ ] Duplicate ID detection

### **Phase 3: Multi-Database Support** 🔮
- [ ] Item database validation
- [ ] Monster database validation
- [ ] Skill database validation
- [ ] Auto-detect database type

### **Phase 4: Advanced Features** 🔮
- [ ] Auto-fix suggestions
- [ ] Template insertion
- [ ] Schema documentation
- [ ] Export validation reports

---

## 💡 **Tips**

### **1. Use Validation Before Committing**
Always validate YAML databases before committing changes to catch errors early.

### **2. Fix Errors First, Then Warnings**
- **Errors** will prevent the server from loading the database
- **Warnings** indicate potential issues but won't crash the server
- **Suggestions** are best practices

### **3. Check Rate Values**
```yaml
Rate: 10000  # = 100% drop rate
Rate: 5000   # = 50% drop rate
Rate: 1000   # = 10% drop rate
Rate: 100    # = 1% drop rate
```

### **4. Use Consistent Indentation**
YAML requires consistent indentation (usually 2 spaces per level):
```yaml
Body:
  - Id: 1000        # 2 spaces
    Title: "Quest"  # 4 spaces
    Targets:        # 4 spaces
      - Mob: Poring # 6 spaces
```

---

## 🐛 **Common Errors**

### **1. Missing Required Fields**
```yaml
# ✗ ERROR: Missing 'Id'
- Title: "My Quest"
  TimeLimit: 0

# ✓ CORRECT
- Id: 1000
  Title: "My Quest"
  TimeLimit: 0
```

### **2. Incorrect Data Types**
```yaml
# ✗ ERROR: Id should be int
- Id: "1000"

# ✓ CORRECT
- Id: 1000
```

### **3. Negative Values**
```yaml
# ✗ ERROR: TimeLimit cannot be negative
- Id: 1000
  TimeLimit: -100

# ✓ CORRECT
- Id: 1000
  TimeLimit: 0
```

### **4. Rate Out of Range**
```yaml
# ⚠ WARNING: Rate > 100%
Drops:
  - Item: Apple
    Rate: 15000

# ✓ CORRECT (100% drop)
Drops:
  - Item: Apple
    Rate: 10000
```

---

## 📚 **See Also**

- [Script Validator](VALIDATOR_MULTILINE_COMMENT_FIX_SIMPLE.md)
- [rAthena Tools Menu](RATHENA_TOOLS_MENU.md)
- [YAML Syntax Reference](https://yaml.org/spec/1.2/spec.html)
- [rAthena Database Documentation](https://github.com/rathena/rathena/wiki/Database)

---

**The YAML Database Validator helps catch database errors before they cause production issues!** 🎉
