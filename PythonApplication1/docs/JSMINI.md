# ⚙️ JavaScript Engine Documentation (jsmini)

## Overview

**jsmini** is a lightweight, embeddable JavaScript interpreter written in pure Python. It supports ES3-like syntax with select ES6+ features (arrow functions, async/await, template literals, destructuring) and includes a minimal DOM shim for web automation.

> **Status:** Experimental, not production-ready. Use for scripting and automation, not as a general JS runtime replacement.

---

## Table of Contents

- [Architecture](#architecture)
- [Language Support](#language-support)
- [Core API](#core-api)
- [DOM Shim](#dom-shim)
- [Built-ins](#built-ins)
- [Performance & Limits](#performance--limits)
- [Debugging](#debugging)
- [Examples](#examples)
- [Known Limitations](#known-limitations)

---

## Architecture

### Design Philosophy

jsmini prioritizes:
1. **Simplicity** - Minimal code footprint (~2000 lines)
2. **Safety** - Recursion limits, execution guards
3. **Embeddability** - Easy integration into Python applications
4. **Extensibility** - Native JS-like functions defined in Python

### Components

```
┌─────────────────────────────────────────┐
│     JavaScript Source (.js)             │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  Tokenizer (Token Stream)               │
│  - Regex literal detection              │
│  - String/comment parsing               │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  Parser (Builds AST)                    │
│  - Recursive descent parser             │
│  - Operator precedence                  │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  Interpreter (Executes AST)             │
│  - Environment/scopes                   │
│  - Type coercion                        │
│  - Error handling                       │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│     Result / Side Effects               │
│  - Return value                         │
│  - DOM mutations                        │
│  - console.log() output                 │
└─────────────────────────────────────────┘
```

---

## Language Support

### ✅ Supported

#### Statements
- `var`, `let`, `const` (all treated similarly)
- `function` declarations and expressions
- `if/else`, `switch/case`, `for`, `while`, `do-while`
- `for-in` loops (iterates over object/array keys)
- `try-catch-finally`, `throw`
- `break`, `continue` (with optional labels)
- `return`, `new`

#### Expressions
- Arithmetic: `+`, `-`, `*`, `/`, `%`
- Relational: `<`, `>`, `<=`, `>=`, `==`, `!=`, `===`, `!==`
- Logical: `&&`, `||`, `!`
- Bitwise: `&`, `|`, `^`, `~`, `<<`, `>>`, `>>>`
- Assignment: `=`, `+=`, `-=`, `*=`, `/=`, `%=`, `&=`, `|=`, `^=`
- Unary: `-`, `+`, `!`, `~`, `typeof`, `delete`, `void`, `++`, `--`
- Conditional (ternary): `condition ? true_val : false_val`
- Comma: `expr1, expr2` (evaluates both, returns second)
- Member access: `.`, `[]`
- Function call: `func(args)`
- Object literals: `{key: value, ...}`
- Array literals: `[elem, ...]`
- `instanceof`, `in` operators
- String concatenation (automatic)

#### Built-in Objects
- `Array` + methods (push, pop, map, filter, etc.)
- `Object` + methods (keys, assign, create)
- `Function.prototype` (call, apply, bind)
- `JSON` (parse, stringify)
- `Math` (min, max, floor, ceil, round, random, sin, cos, etc.)
- `Event`, `Element` (DOM)
- `localStorage` (in-memory key-value store)

### ⚠️ Partially Supported

- **Arrow functions:** Basic `=> function bodies (no advanced destructuring)
- **Template literals:** `` `string ${expr}` `` (no nested templates)
- **Regex literals:** `/pattern/flags` parsed but not executed (returned as string)
- **async/await:** Parsed but not enforced (timers are synchronous in basic usage)
- **Spread operator:** Limited support in function calls and array literals
- **Destructuring:** Very limited; basic object/array unpacking only

### ❌ Not Supported

- **Generators:** `function*`, `yield` (syntax recognized, not executed)
- **Proxies, Symbols, WeakMap, Set:** No implementation
- **Classes (full ES6):** Parsed, limited runtime support
- **Promises, async iterators**
- **Module system:** No `import/export`
- **Strict mode:** No enforcement
- **with statement**
- **eval()**

---

## Core API

### Basic Execution

#### `make_context(log_fn=None) -> dict`

Create a JavaScript execution environment.

**Parameters:**
- `log_fn`: Optional callback for console.log: `fn(message: str)`

**Returns:** Context dict containing global objects, undefined sentinel, timers, etc.

**Example:**
```python
import jsmini

def my_logger(msg):
    print(f"[JS] {msg}")

ctx = jsmini.make_context(log_fn=my_logger)
```

---

#### `run(src: str, context=None) -> Any`

Parse and execute JavaScript source.

**Parameters:**
- `src`: JavaScript source code (string)
- `context`: Optional execution context (created if None)

**Returns:** Result of last expression

**Example:**
```python
result = jsmini.run("2 + 2")
print(result)  # 4.0

result = jsmini.run("""
    var x = 10;
    x * 2;
""")
print(result)  # 20.0
```

---

#### `run_with_interpreter(src: str, context=None) -> Tuple[Any, Interpreter]`

Execute and return interpreter instance for state inspection.

**Returns:** Tuple `(result, Interpreter_instance)`

**Use Case:** Access interpreter globals, manipulate state between runs.

**Example:**
```python
result, interp = jsmini.run_with_interpreter("var x = 42;", ctx)

# Access global variable
x_value = interp.global_env.get('x')
print(x_value)  # 42

# Execute another script in same environment
result2 = jsmini.run("x + 8;", ctx)
print(result2)  # 50
```

---

#### `run_timers(context: dict)`

Execute all enqueued timers (setTimeout) in the context.

**Example:**
```python
ctx = jsmini.make_context()
jsmini.run("""
    console.log('immediate');
    setTimeout(function() {
        console.log('delayed');
    }, 0);
""", ctx)
# Output: immediate

jsmini.run_timers(ctx)
# Output: delayed
```

---

### Tokenizer

#### `tokenize(src: str) -> List[Tuple[str, str, int, int]]`

Break source into tokens with position info.

**Returns:** List of `(type, value, start, end)` tuples

**Token Types:** NUMBER, STRING, IDENT, OP, PUNC, REGEX, COMMENT, SKIP, EOF

**Example:**
```python
tokens = jsmini.tokenize("var x = 42;")
for tok in tokens:
    print(tok)
# ('IDENT', 'var', 0, 3)
# ('IDENT', 'x', 4, 5)
# ('OP', '=', 6, 7)
# ('NUMBER', '42', 8, 10)
# ('PUNC', ';', 10, 11)
# ('EOF', '', 11, 11)
```

---

### Parser

#### `parse(src: str) -> tuple`

Build Abstract Syntax Tree from source.

**Returns:** AST root node (typically `('prog', [statements])`)

**Raises:** `SyntaxError` with context information

**Example:**
```python
ast = jsmini.parse("2 + 2")
print(ast)
# ('prog', [('expr', ('bin', '+', ('num', 2.0), ('num', 2.0)))])
```

---

### DOM Shim

#### `make_dom_shim(host=None) -> dict`

Create minimal DOM API for JavaScript.

**Returns:** Document object with methods and properties

**Key Methods:**
- `createElement(tag)` → Element
- `getElementById(id)` → Element or None
- `querySelector(selector)` → Element or None
- `querySelectorAll(selector)` → JSList
- `addEventListener(event, handler)`
- `removeEventListener(event, handler)`

**Key Properties:**
- `body` → Element (root element)
- `document` → Self-reference

**Example:**
```python
ctx = jsmini.make_context()
doc = ctx['document']

# Create element
el = doc['createElement']('div')
el.setAttribute('id', 'main')
el.textContent = 'Hello'

# Append to body
doc['body'].appendChild(el)

# Query
found = doc['getElementById']('main')
print(found.textContent)  # 'Hello'

# Get final HTML
html = doc['body'].innerHTML
print(html)  # '<div id="main">Hello</div>'
```

---

#### Element Methods

- `setAttribute(name, value)` - Set attribute
- `removeAttribute(name)` - Remove attribute
- `hasAttribute(name)` → bool
- `appendChild(child)` - Add child
- `removeChild(child)` - Remove child
- `insertBefore(new, ref)` - Insert before reference
- `replaceChild(new, old)` - Replace child
- `addEventListener(event, handler)` - Attach event listener
- `removeEventListener(event, handler)` - Remove listener
- `dispatchEvent(event)` - Trigger event

#### Element Properties

- `tagName` → str (tag name)
- `id` → str
- `className` → str (class attribute)
- `innerHTML` → str (serialized children, get/set)
- `textContent` → str (text only, get/set)
- `parentNode` → Element or None
- `childNodes` → JSList
- `children` → JSList (elements only)
- `firstChild`, `lastChild` → Element or None
- `nextSibling`, `previousSibling` → Element or None

---

## Built-ins

### Console

```javascript
console.log(msg, ...)     // Print message
console.error(msg, ...)   // Print error (same as log)
console.warn(msg, ...)    // Print warning (same as log)
```

### Math

Full set of methods: `abs`, `floor`, `ceil`, `round`, `max`, `min`, `pow`, `sqrt`, `sin`, `cos`, `tan`, `random`, etc.

```javascript
Math.abs(-5)           // 5
Math.floor(3.7)        // 3
Math.random()          // 0.0 - 1.0
Math.max(1, 2, 3)      // 3
```

### Array Methods

**Mutating:**
- `push(...items)` - Add to end
- `pop()` - Remove last
- `splice(start, count, ...items)` - Insert/remove
- `shift()` - Remove first
- `unshift(...items)` - Add to start

**Iteration (with stack guards):**
- `forEach(callback)` - Execute for each
- `map(callback)` - Transform elements
- `filter(callback)` - Filter elements
- `reduce(callback[, init])` - Accumulate value
- `some(callback)` → bool - Any match
- `every(callback)` → bool - All match
- `find(callback)` → value - First match
- `findIndex(callback)` → index

**Access:**
- `slice(start[, end])` - Get subarray
- `concat(...arrays)` - Combine arrays
- `indexOf(item[, start])` → index
- `each(callback)` - jQuery-style each

### Object Methods

- `Object.keys(obj)` → Array of keys
- `Object.assign(target, ...sources)` - Copy properties
- `Object.create(proto)` - Create with prototype
- `obj.hasOwnProperty(name)` → bool

### JSON

- `JSON.parse(text[, reviver])` - Parse JSON string
- `JSON.stringify(value[, replacer][, space])` - Serialize to JSON

### localStorage

```javascript
localStorage.getItem(key)      // Get value
localStorage.setItem(key, val) // Set value
localStorage.removeItem(key)   // Delete key
localStorage.clear()           // Clear all
```

### setTimeout / setInterval

```javascript
var id = setTimeout(function() {
    console.log('delayed');
}, 1000);

clearTimeout(id);

var id2 = setInterval(function() {
    console.log('repeated');
}, 500);

clearInterval(id2);
```

### Function Methods

- `fn.call(thisArg, ...args)` - Call with explicit this
- `fn.apply(thisArg, argsArray)` - Call with args array
- `fn.bind(thisArg, ...args)` → function - Create bound function

---

## Performance & Limits

### Execution Guards

jsmini includes multiple recursion/runaway checks:

| Guard | Limit | Purpose |
|-------|-------|---------|
| **Total statement execution** | 200,000 | Prevent infinite loops |
| **Call stack depth** | 2,000 | Prevent stack overflow |
| **Per-function depth** | 1,500 | Detect infinite recursion per-function |
| **Nesting depth (JSON)** | 100 | Prevent deeply nested structures |

### Configuring Limits

```python
ctx = jsmini.make_context()
interp = ctx.get('_interp')  # After first run

# Set custom limits
interp._exec_limit = 500_000       # Total statements
interp._max_js_call_depth = 5_000  # Call stack
interp._per_fn_call_threshold = 2_000  # Per-function depth
```

### Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| **Tokenize** | O(n) | Linear in source length |
| **Parse** | O(n) | Linear with fixed depth |
| **Execute simple** | <1ms | Arithmetic, variable access |
| **Array.map (1000 items)** | ~50ms | Callback overhead |
| **JSON.stringify (1000 objs)** | ~20ms | Object serialization |

---

## Debugging

### Enable Debug Output

```python
ctx = jsmini.make_context()
result, interp = jsmini.run_with_interpreter(src, ctx)

# Enable trace mode
interp._trace = True

# Run more code to see trace
jsmini.run("...", ctx)
# [jsmini.trace] executed=50000 call_stack=[...]
```

### Inspect Call Stack on Error

```python
try:
    jsmini.run(src, ctx)
except RecursionError:
    interp = ctx.get('_interp')
    print(f"Call stack: {getattr(interp, '_call_stack', [])}")
    print(f"Execution count: {interp._exec_count}")
```

### Error Context Display

Parser errors include source snippets:

```
SyntaxError at token #42 ('OP', '='):
Expected identifier after 'var'
  Line 5, Col 12
    var x = ;
        ^^^
```

---

## Examples

### Example 1: Simple Arithmetic

```python
import jsmini

result = jsmini.run("""
    var a = 10;
    var b = 20;
    a + b;
""")
print(result)  # 30.0
```

### Example 2: Array Processing

```python
import jsmini

ctx = jsmini.make_context()
jsmini.run("""
    var numbers = [1, 2, 3, 4, 5];
    var doubled = numbers.map(function(n) {
        return n * 2;
    });
    console.log(doubled);
""", ctx)
# Output: [2, 4, 6, 8, 10]
```

### Example 3: DOM Manipulation

```python
import jsmini

ctx = jsmini.make_context()
jsmini.run("""
    var article = document.createElement('article');
    article.setAttribute('class', 'post');
    
    var heading = document.createElement('h1');
    heading.textContent = 'My Post';
    article.appendChild(heading);
    
    var body = document.createElement('div');
    body.setAttribute('class', 'body');
    body.textContent = 'Post content here.';
    article.appendChild(body);
    
    document.body.appendChild(article);
    
    console.log('DOM created');
""", ctx)

doc = ctx['document']
html = doc['body'].innerHTML
print(html)
```

### Example 4: Event Handling

```python
import jsmini

ctx = jsmini.make_context()
jsmini.run("""
    var button = document.createElement('button');
    button.textContent = 'Click me';
    
    var clicked = false;
    button.addEventListener('click', function(event) {
        clicked = true;
        console.log('Button clicked!');
    });
    
    document.body.appendChild(button);
    
    // Dispatch event
    button.dispatchEvent('click');
""", ctx)
# Output: Button clicked!
```

### Example 5: Timers & Async

```python
import jsmini

ctx = jsmini.make_context()
jsmini.run("""
    console.log('Start');
    
    setTimeout(function() {
        console.log('After 1');
    }, 0);
    
    setTimeout(function() {
        console.log('After 2');
    }, 0);
    
    console.log('End');
""", ctx)
# Output: Start, End

jsmini.run_timers(ctx)
# Output: After 1, After 2
```

### Example 6: JSON Processing

```python
import jsmini

ctx = jsmini.make_context()
result = jsmini.run("""
    var data = JSON.parse('{"name":"John","age":30}');
    data.name;
""", ctx)
print(result)  # 'John'

result = jsmini.run("""
    var obj = {x: 1, y: 2};
    JSON.stringify(obj);
""", ctx)
print(result)  # '{"x":1,"y":2}'
```

---

## Known Limitations

### JavaScript Compatibility

| Issue | Impact | Workaround |
|-------|--------|-----------|
| No true async | Low | Use timers for delays |
| No Promises | Low | Use callbacks |
| Limited regex | Medium | Pre-compile in Python |
| No WeakMap/Set | Low | Use objects/arrays |
| Regex literals as strings | High | Use `new RegExp()` |
| No module system | High | Split scripts manually |
| Hoisting incomplete | Medium | Declare before use |

### Performance

| Issue | Impact | Workaround |
|-------|--------|-----------|
| Slow large arrays | Medium | Process in Python |
| String operations | Medium | Use native Python |
| Deep nesting limit | Low | Flatten structures |
| No JIT compilation | High | Use Python for heavy code |

### Security

⚠️ **WARNING:** jsmini is NOT sandboxed. JavaScript code has full Python interpreter access via clever tricks. Use only for trusted scripts.

---

## Architecture Notes

### AST Node Types

Common nodes:

```python
('prog', [statements])                    # Program root
('expr', expression)                      # Expression statement
('var', [(name, init), ...])             # Variable declaration
('func', name, params, body)              # Function declaration
('if', cond, cons, alt)                   # If statement
('while', cond, body)                     # While loop
('for', init, cond, post, body)           # For loop
('block', [statements])                   # Block scope
('bin', op, left, right)                  # Binary operation
('unary', op, operand)                    # Unary operation
('call', function, [args])                # Function call
('get', object, property)                 # Property access
('obj', [(key, val), ...])               # Object literal
('arr', [elements])                       # Array literal
('num', value)                            # Number literal
('str', value)                            # String literal
('id', name)                              # Identifier
```

### Scope Chain

```
┌──────────────────┐
│ Global Scope     │  (functions, Array, Object, Math, etc.)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Function Scope 1 │  (function variables, parameters)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Block Scope      │  (let/const in blocks)
└──────────────────┘
```

Variables are looked up by walking the scope chain from innermost to global.

---

## See Also

- [API Documentation](API.md)
- [Syntax Highlighting Guide](SYNTAX.md)
- [jsmini.py Source](../jsmini.py) - Full implementation
