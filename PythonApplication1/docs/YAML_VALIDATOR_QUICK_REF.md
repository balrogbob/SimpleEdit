# YAML Validator Quick Reference

## 🚀 Quick Start

### **1. Open YAML File**
Open any rAthena YAML database file (`.yml`) in SimpleEdit

### **2. Validate**
```
Menu: rAthena Tools → Validate YAML Database
```

### **3. Review Results**
- **Errors** ✗ - Must fix (prevents loading)
- **Warnings** ⚠ - Should fix (potential issues)
- **Suggestions** 💡 - Best practices

---

## 📋 Common Errors

| Error | Fix |
|-------|-----|
| Missing required field 'Id' | Add `Id: <number>` |
| TimeLimit cannot be negative | Use `TimeLimit: 0` or positive |
| Rate exceeds 10000 | Max is `Rate: 10000` (100%) |
| YAML Syntax Error | Check indentation/colons |
| Id should be an integer | Remove quotes: `Id: 1000` |

---

## ✅ Validation Checklist

**Header:**
- [ ] Type: QUEST_DB (or appropriate type)
- [ ] Version: 3 (recommended)

**Quest Entry:**
- [ ] Id: Positive integer, unique
- [ ] Title: Non-empty string
- [ ] TimeLimit: 0 or positive (optional)

**Target:**
- [ ] Mob: Valid monster name
- [ ] Count: Positive integer
- [ ] Id: Positive integer (if used)

**Drop:**
- [ ] Item: Valid item name
- [ ] Rate: 0-10000 (0-100%)
- [ ] Count: Positive integer

---

## 💡 Pro Tips

1. **Validate before committing** - Catch errors early
2. **Fix errors first** - They prevent server loading
3. **Check rate values** - 10000 = 100%, 1000 = 10%
4. **Use consistent indent** - 2 spaces per level
5. **Test with template** - Use `templates/template.yml`

---

## 📚 See Also

- Full docs: `docs/YAML_VALIDATOR.md`
- Template: `templates/template.yml`
- Script validator: `rAthena Tools → Validate Script`
