# 🛠️ Development Process: Building jsmini

## Overview

This document chronicles the iterative development of **jsmini**, a lightweight JavaScript interpreter built entirely through reverse-engineering via test-driven iteration. Rather than designing the interpreter upfront, jsmini emerged organically from a simple question: *"What if I could execute JavaScript loaded from web pages inside my text editor?"*

---

## Table of Contents

- [The Inspiration](#the-inspiration)
- [Phase 1: Tokenizer Discovery](#phase-1-tokenizer-discovery)
- [Phase 2: Parser Construction](#phase-2-parser-construction)
- [Phase 3: Runtime & Built-ins](#phase-3-runtime--built-ins)
- [Phase 4: DOM Shim](#phase-4-dom-shim)
- [Phase 5: Guards & Refinement](#phase-5-guards--refinement)
- [Key Learnings](#key-learnings)
- [Iteration Patterns](#iteration-patterns)
- [Testing Strategy](#testing-strategy)
- [Future Directions](#future-directions)

---

## The Inspiration

### The Problem

SimpleEdit had evolved into a full-featured code editor with HTML/Markdown parsing capabilities. While testing with web pages, a question emerged:

> *"I can parse the HTML and extract `<script>` tags... but what if I could actually run them?"*

At the time, this seemed impossible without adding heavyweight dependencies like `V8` or `node.js`. The alternative was clear: **build a JavaScript interpreter from scratch**.

### The Constraint

Rather than design a complete interpreter specification upfront, I decided to adopt an **empirical, test-first approach**:

1. **Feed real JavaScript code** to the system
2. **Observe where it fails**
3. **Fix the specific failure point**
4. **Repeat**

This proved to be far more effective than trying to anticipate every language feature.

---

## Phase 1: Tokenizer Discovery

### Starting Point

The tokenizer is the foundation. It breaks JavaScript source into a stream of tokens (NUMBER, STRING, IDENT, OP, PUNC, etc.).

### The Reverse-Engineering Process

#### Iteration 1: Basic Tokens

**Start with:**
```python
TOKEN_SPEC = [
    ('NUMBER',   r'\d+'),
    ('STRING',   r'"[^"]*"|\'[^\']*\''),
    ('IDENT',    r'[A-Za-z_][A-Za-z0-9_]*'),
    ('OP',       r'[+\-*/=<>!&|]'),
    ('PUNC',     r'[(){},;:\[\].]'),
]
```

**Test with:**
```javascript
var x = 42;
var name = "hello";
```

**Result:** ✅ Works! Can tokenize simple variable declarations.

#### Iteration 2: Operators & Precedence

**Feed:**
```javascript
var result = x + y * 2;
```

**Error:** `===` not recognized

**Discovery:** Operators can be multi-character. Need to order them longest-first:

```python
('OP', r'\+\+|--|===|!==|==|!=|<=|>=|&&|\|\||[+\-*/=<>!&|%^~]'),
```

**Why this matters:** Without longest-first matching, `===` would tokenize as `==` then `=`, breaking parsing.

**Lesson:** Multi-character operators must be checked before single-character ones.

#### Iteration 3: Decimals & Scientific Notation

**Feed:**
```javascript
var pi = 3.14159;
var small = 1.5e-10;
var hex = 0xFF;
```

**Error:** Decimal tokenizer breaks on `.14159` and scientific notation

**Discovery:** Numbers can be:
- Integers: `42`
- Decimals: `3.14`
- Leading-dot decimals: `.5` (shorthand for `0.5`)
- Scientific notation: `1e10`, `1e-5`, `1.5e+3`
- Hex: `0xFF`, `0x1A`
- Octal: `0o77`
- Binary: `0b1010`

**Updated regex:**
```python
('NUMBER', r'(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|0[xX][0-9A-Fa-f]+|0[bB][01]+|0[oO][0-7]+'),
```

**Lesson:** Always test edge cases. Real code uses scientific notation, hex literals, and shorthand decimals.

#### Iteration 4: Regex Literal Hell

**Feed:**
```javascript
var pattern = /^[a-z]+$/i;
var divide = x / y;
```

**Error:** Tokenizer can't distinguish `/pattern/` from `/` (division operator)

**Challenge:** Whether `/` starts a regex depends on **context**, not syntax:
- After `=`, operators, keywords like `return` → likely a regex
- After numbers, identifiers, `)` → likely division

**Solution:** Context-aware heuristic (still imperfect, but effective):

```python
def _prev_allows_regex():
    """
    Heuristic: return True if previous token allows a regex to follow.
    """
    if prev_type is None:
        return True  # Start of input
    
    # After these tokens, / likely starts a regex
    if prev_type == 'PUNC' and prev_val in ('(', '{', '[', ',', ';', ':', '?'):
        return True
    
    if prev_type == 'OP':
        return True
    
    if prev_type == 'IDENT' and prev_val in ('return', 'case', 'throw', 'new', 'typeof'):
        return True
    
    # After these, / is probably division
    if prev_type in ('NUMBER', 'STRING', 'IDENT'):
        return False
    
    return False
```

**Lesson:** Some parsing problems can't be solved with pure tokenization. Regex literal detection requires lookahead and context awareness.

#### Iteration 5: Comments & Strings with Escapes

**Feed:**
```javascript
// Single-line comment
/* Multi-line comment */
var str = "Escaped \"quote\" and newline \\n";
var multiline = "Line 1 \
Line 2";
```

**Error:** Escaped quotes break string parsing; comments consume code as strings

**Solution:**
- Match strings with escape sequences: `"([^"\\]|\\.)*"`
- Add comment patterns, process before other tokens:

```python
TOKEN_SPEC = [
    ('COMMENT',  r'//[^\n]*|/\*[\s\S]*?\*/'),  # Must come early!
    ('STRING',   r'"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\''),
    # ... rest
]
```

**Lesson:** Token order matters. Comments, strings, and numbers must be tried before general operators.

---

## Phase 2: Parser Construction

### From Tokens to AST

Once tokenization was solid, the next challenge: building an Abstract Syntax Tree (AST) that represents the program structure.

#### Iteration 1: Expressions

**Start simple:**
```javascript
2 + 3
```

**AST needed:**
```python
('prog', [('expr', ('bin', '+', ('num', 2.0), ('num', 3.0)))])
```

**Approach:** Recursive descent parser with precedence climbing:

```python
def parse_binary(self, min_prec):
    left = self.parse_unary()
    while True:
        op = self.peek_op()
        if op not in BINOPS or BINOPS[op] < min_prec:
            break
        self.eat_op(op)
        right = self.parse_binary(BINOPS[op] + 1)
        left = ('bin', op, left, right)
    return left
```

**Why precedence climbing:** Handles `2 + 3 * 4` correctly:
- `*` binds tighter than `+`
- Parser naturally builds `('bin', '+', ('num', 2), ('bin', '*', ('num', 3), ('num', 4)))`

**Lesson:** Operator precedence is critical and easy to get wrong by hand.

#### Iteration 2: Variables & Scoping

**Feed:**
```javascript
var x = 42;
var y = x + 1;
console.log(y);
```

**Error:** Variables not tracked; x resolves to undefined

**Solution:** Build `Env` (environment) class for scope chain:

```python
class Env:
    def __init__(self, parent=None):
        self.vars = {}
        self.parent = parent
    
    def get(self, name):
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.get(name)
        raise NameError(name)
    
    def set(self, name, value):
        # Assign to nearest scope that has it, else local
        if name in self.vars:
            self.vars[name] = value
        elif self.parent:
            try:
                self.parent.get(name)
                self.parent.set(name, value)
                return
            except NameError:
                pass
        self.vars[name] = value
```

**Lesson:** Scope chains are essential for real languages. Early versions without proper scoping led to confusing bugs.

#### Iteration 3: Functions & Closures

**Feed:**
```javascript
function add(a, b) {
    return a + b;
}
console.log(add(2, 3));
```

**Error:** Function calls execute but parameters aren't bound

**Solution:** Capture environment at function definition time (closure):

```python
class JSFunction:
    def __init__(self, params, body, env, name=None):
        self.params = params      # ['a', 'b']
        self.body = body          # AST node
        self.env = env            # Captured environment
        self.name = name
    
    def call(self, interpreter, this, args):
        # Create new scope with captured env as parent
        local = Env(self.env)
        
        # Bind parameters
        for i, param in enumerate(self.params):
            local.set_local(param, args[i] if i < len(args) else undefined)
        
        # Execute body
        return interpreter._eval_stmt(self.body, local, this)
```

**Lesson:** Closures emerge naturally from capturing the definition environment. This single concept enables callbacks, higher-order functions, and async patterns.

#### Iteration 4: Control Flow

**Feed:**
```javascript
if (x > 0) {
    console.log('positive');
} else {
    console.log('non-positive');
}
```

**Iterative challenges:**
1. `if-else` chains
2. `switch-case` fall-through
3. `break` and `continue` needing to escape loops
4. Labeled `break` and `continue`

**Solution for break/continue:** Custom exception types:

```python
class BreakExc(Exception):
    def __init__(self, label=None):
        self.label = label

class ContinueExc(Exception):
    def __init__(self, label=None):
        self.label = label
```

Then in loop evaluators:

```python
def _eval_while(self, node, env):
    while self._is_truthy(self._eval_expr(cond, env, this)):
        try:
            self._eval_stmt(body, env, this)
        except BreakExc as be:
            if be.label is None:  # Unlabeled break
                break
            raise  # Re-raise labeled break for outer label
        except ContinueExc as ce:
            if ce.label is None:  # Unlabeled continue
                continue
            raise  # Re-raise labeled continue
```

**Lesson:** Exceptions are the cleanest way to handle non-local control flow. Trying to use return values led to messy, error-prone code.

---

## Phase 3: Runtime & Built-ins

### Making It Useful

A JavaScript interpreter that can't call `Array.map()` or `JSON.stringify()` is mostly useless. Built-ins had to be added through real-world testing.

#### Iteration 1: Array Methods

**Feed:**
```javascript
var arr = [1, 2, 3];
arr.push(4);
console.log(arr);
```

**Error:** Arrays exist as dicts but no `.push()` method

**Solution:** Implement Array as a "constructor" with prototype methods:

```python
def _array_push(interp, this, args):
    length = int(this.get("length", 0))
    for v in args:
        this[str(length)] = v
        length += 1
    this["length"] = length
    return length

Arr = JSFunction([], None, None, "Array", native_impl=_array_ctor)
Arr.prototype["push"] = JSFunction([], None, None, "push", native_impl=_array_push)
```

**Testing revealed:** Methods need access to `this` and the interpreter.

**Lesson:** Native (Python-implemented) JavaScript functions need a standard signature: `(interp, this, args) -> value`

#### Iteration 2: Higher-Order Methods (map, filter, reduce)

**Feed:**
```javascript
var doubled = [1, 2, 3].map(function(x) { return x * 2; });
```

**Challenge:** Callback functions need to be invoked with the right context and can throw errors.

**Approach:** Guards against infinite recursion:

```python
def _array_map(interp, this, args):
    cb = args[0] if args else None
    if not cb:
        return {'__proto__': Arr.prototype, 'length': 0}
    
    length = int(this.get("length", 0))
    res = {'__proto__': Arr.prototype, 'length': 0}
    
    for i in range(length):
        key = str(i)
        if key not in this:
            continue
        val = this.get(key)
        
        # Guard: Check recursion depth before calling callback
        if isinstance(cb, JSFunction):
            call_depth = len(getattr(interp, '_call_stack', []))
            if call_depth > 500:
                raise RuntimeError(f"Array.map callback stack overflow")
        
        result = cb.call(interp, None, [val, i, this])
        res[str(i)] = result
    
    res["length"] = length
    return res
```

**Why guards matter:** jQuery's `.each()` could inadvertently recurse when scripts didn't guard against it.

**Lesson:** Callbacks are dangerous. Always add recursion depth checks.

#### Iteration 3: JSON Support

**Feed:**
```javascript
var obj = {x: 1, y: 2};
var json = JSON.stringify(obj);
var parsed = JSON.parse(json);
```

**Challenge:** JSON requires converting between Python native types and JS-shaped dicts:

```python
def _to_js(py_val):
    """Convert Python native JSON result to JS-shaped value."""
    if py_val is None:
        return None
    if isinstance(py_val, (str, bool, int, float)):
        return py_val
    if isinstance(py_val, list):
        out = {'__proto__': Arr.prototype, 'length': 0}
        for i, el in enumerate(py_val):
            out[str(i)] = _to_js(el)
        out['length'] = len(py_val)
        return out
    if isinstance(py_val, dict):
        return {str(k): _to_js(v) for k, v in py_val.items()}
    return str(py_val)
```

**Lesson:** JS object model (string-keyed dicts) doesn't match Python naturally. Conversion layers are necessary.

---

## Phase 4: DOM Shim

### Enabling Web Automation

To execute real web scripts, a minimal DOM API was essential.

#### Iteration 1: Basic Elements

**Feed:**
```javascript
var el = document.createElement('div');
el.setAttribute('id', 'main');
el.textContent = 'Hello';
document.body.appendChild(el);
```

**Solution:** Simple Element class:

```python
class Element:
    def __init__(self, tag):
        self.tagName = tag
        self.attrs = {}
        self.children = []
        self.id = None
    
    def setAttribute(self, name, value):
        self.attrs[name] = value
        if name == 'id':
            self.id = value
    
    def appendChild(self, child):
        self.children.append(child)
    
    @property
    def innerHTML(self):
        """Serialize children to HTML."""
        # Recursive serialization...
```

**Lesson:** A minimal DOM implementation is surprisingly simple when you don't need full HTML5 spec compliance.

#### Iteration 2: Event System

**Feed:**
```javascript
button.addEventListener('click', function(e) {
    console.log('Clicked!');
});
button.dispatchEvent('click');
```

**Challenge:** Callbacks must be enqueued to avoid synchronous re-entry, which could cause infinite loops.

**Solution:** Re-entrancy guard:

```python
def dispatchEvent(self, ev):
    dispatch_key = (id(self), ev.get('type'))
    
    # Track active dispatches to prevent re-entry
    active_dispatches = ctx.setdefault('_active_dispatches', set())
    
    if dispatch_key in active_dispatches:
        # Already dispatching this event on this element
        return
    
    active_dispatches.add(dispatch_key)
    try:
        for handler in self._listeners.get(ev.get('type'), []):
            if isinstance(handler, JSFunction):
                handler.call(interp, self, [ev])
    finally:
        active_dispatches.discard(dispatch_key)
```

**Why this matters:** jQuery's `.each()` pattern could trigger event handlers that re-triggered the same event, causing infinite loops. The guard prevents this.

**Lesson:** DOM event systems are surprisingly tricky to get right. Guard against re-entry and batch duplicate events.

#### Iteration 3: Host Callbacks

**Feed (from SimpleEdit):**
```javascript
// Inside the editor, scripts can update DOM via callbacks
host.setRaw(document.body.innerHTML);  // Update the rendered view
```

**Solution:** Expose Python callbacks to JavaScript:

```python
host_obj = {
    'setRaw': host_update_cb,
    'forceRerender': lambda: host_update_cb(None),
}
ctx['host'] = host_obj
```

**Lesson:** Bridging Python and JavaScript requires careful callback design. Always make callbacks defensive (wrap in try-except).

---

## Phase 5: Guards & Refinement

### Preventing Catastrophic Failures

As scripts became more complex, protecting against runaway execution became critical.

#### Iteration 1: Statement Execution Limit

**Problem:** A simple infinite loop crashed the editor:
```javascript
while (true) {
    // Infinite loop
}
```

**Solution:** Count every statement executed, abort when limit exceeded:

```python
def _eval_stmt(self, node, env, this):
    try:
        self._exec_count += 1
    except AttributeError:
        self._exec_count = 1
    
    if getattr(self, '_exec_limit', 0) and self._exec_count > self._exec_limit:
        raise RuntimeError(
            f"Execution limit exceeded ({self._exec_count} statements)"
        )
    
    # ... rest of evaluation
```

**Default limit:** 200,000 statements (caught most runaway loops within ~1 second)

**Lesson:** Limits are essential for embedded interpreters. Always provide a way to abort.

#### Iteration 2: Call Stack Depth Guard

**Problem:** Deep recursion crashed with `RecursionError`:
```javascript
function recurse(n) {
    return recurse(n - 1);  // Infinite recursion
}
recurse(1);
```

**Solution:** Track call stack depth:

```python
def _eval_prog(self, node, env):
    # ... setup
    try:
        for st in node[1]:
            res = self._eval_stmt(st, env, None)
            # Guard: detect runaway recursion by stack length
            if hasattr(self, '_call_stack') and len(self._call_stack) > 100:
                stack = self._call_stack[-100:]
                if len(set(stack)) == 1:  # All identical
                    raise RuntimeError(
                        f"Infinite recursion detected: {stack[0]}"
                    )
    finally:
        pass
```

**Lesson:** Stack depth detection is crude but effective. Better to catch early than let Python blow up.

#### Iteration 3: Per-Function Recursion Tracking

**Problem:** jQuery's `.each()` could recurse per-function without hitting overall depth limits:

```javascript
jQuery.each(arr, function(i, v) {
    jQuery.each(v, function(j, u) {
        jQuery.each(u, ...);  // Deep nesting in same function
    });
});
```

**Solution:** Track depth per function:

```python
def call(self, interpreter, this, args):
    fn_id = id(self)
    depth = getattr(interpreter, '_per_fn_call_depth', {}).get(fn_id, 0)
    threshold = getattr(interpreter, '_per_fn_call_threshold', 1500)
    
    if threshold and depth > threshold:
        raise RuntimeError(
            f"Per-function recursion limit for {self.name} (depth={depth})"
        )
    
    # Increment, execute, decrement...
```

**Lesson:** Different limits are needed for different scenarios. Overall execution limits catch tight loops; per-function limits catch pathological recursion patterns.

---

## Key Learnings

### Design Principles That Emerged

#### 1. **Empirical > Theoretical**

Rather than trying to design a perfect language spec upfront, building via test iteration was more effective:
- Real code revealed edge cases (hex literals, scientific notation, regex heuristics)
- Iterative fixes were small and focused
- Each test failure clarified the requirement

#### 2. **Closures Are Fundamental**

Capturing the definition environment at function creation time enabled:
- Proper scoping
- Callbacks
- Higher-order functions
- Event handlers
- Async patterns

This single concept is worth understanding deeply.

#### 3. **Exceptions for Control Flow**

Using custom exceptions (`BreakExc`, `ContinueExc`, `ReturnExc`) for non-local control flow was cleaner than:
- Return values with special meanings
- Flags checked at each level
- Goto-like patterns

#### 4. **Guards Are Non-Negotiable**

Embeddable interpreters must protect their hosts:
- Statement execution limits
- Call stack depth
- Per-function recursion tracking
- Event dispatch re-entry guards

Each emerged from real failures.

#### 5. **Context is King**

Regex vs. division, string escape sequences, operator precedence—all depend on context. When tokenization seemed ambiguous, it was really a design challenge:
- Tokenize greedily (longest tokens first)
- Let the parser disambiguate when possible
- Use heuristics for ambiguous cases (regex detection)

#### 6. **Type Coercion is Messy**

JavaScript's type coercion rules are weird but important:
```javascript
null == undefined  // true
null === undefined  // false
0 == false         // true
0 === false        // false
"5" > 4            // true (coerced to number)
```

Implementing these correctly required studying the spec and testing against real JS engines.

---

## Iteration Patterns

### The Core Development Loop

Every feature followed this pattern:

1. **Write a test** with real JavaScript code
2. **Run it** against jsmini
3. **Observe the failure** (parse error, runtime error, wrong result)
4. **Fix the specific issue**
   - Add token pattern
   - Extend parser rule
   - Implement missing built-in
   - Add guard logic
5. **Re-test** to ensure fix works and doesn't break existing tests
6. **Commit** with explanation of why the fix was needed

### Example: Adding Bitwise Operators

**Test:**
```javascript
var x = 5 & 3;  // Should be 1
var y = 5 | 3;  // Should be 7
var z = ~5;     // Should be -6 (bitwise NOT)
```

**Failure:** `ParseError: unexpected operator '&'`

**Fix 1 - Tokenize:** Add `&`, `|`, `^`, `~` to operator regex

**Failure:** `TypeError: unsupported operand type(s) for &: float and float`

**Fix 2 - Implement bitwise ops:**
```python
def _to_int32(val):
    """Convert to 32-bit signed int (JS spec)."""
    n = int(float(val))
    n = n & 0xFFFFFFFF
    return n - 0x100000000 if n & 0x80000000 else n

# In binary operator handler:
if op == '&':
    return _to_int32(lhs) & _to_int32(rhs)
```

**Failure:** Results are 64-bit Python ints, not 32-bit

**Fix 3 - Normalize results:**
```python
r = r & 0xFFFFFFFF
return r - 0x100000000 if r & 0x80000000 else r
```

**Success!** All tests pass.

---

## Testing Strategy

### Three Levels of Testing

#### 1. **Unit Tests** (jsmini core)
Focus on parser correctness:
```python
def test_parse_binary_operators():
    ast = parse("2 + 3 * 4")
    # Verify * binds tighter than +
    assert ast[1][0][2][0] == 'bin'  # Root is +
    assert ast[1][0][2][2][0] == 'bin'  # Right child is *
```

#### 2. **Integration Tests** (full execution)
Feed real JavaScript, verify output:
```python
def test_array_map():
    ctx = make_context()
    result = run("""
        [1,2,3].map(function(x) { return x*2; })
    """, ctx)
    assert result['length'] == 3
    assert result['0'] == 2
    assert result['1'] == 4
    assert result['2'] == 6
```

#### 3. **Regression Tests** (real scripts)
Keep a growing test suite of real JavaScript:
- jQuery patterns (`.each()`, method chaining)
- ES5 built-ins (Array methods, JSON)
- DOM manipulation (createElement, appendChild, event listeners)
- Edge cases (regex literals, scientific notation, destructuring)

### Test Organization

```
tests/
├── test_base.py                    # Core parser & tokenizer
├── test_js_builtins.py             # Array, Object, JSON
├── test_dom_events.py              # DOM & event system
├── test_run_scripts_update.py       # Full script execution
└── test_object_helpers.py           # Edge cases & type coercion
```

Each test file grew as new features were added. Current coverage: ~200+ test cases.

---

## The "Blind Iteration" Workflow

### What Made This Effective

1. **No Overthinking:** Added features only when needed, driven by real code

2. **Fast Feedback:** Each test run took seconds; quick iteration cycle

3. **Visible Progress:** New test files passing = tangible achievement

4. **Self-Documenting:** Test suite became both verification and documentation

5. **Debt Avoidance:** Fixing things right the first time beats technical debt later

### What Would Be Done Differently

Looking back, a few things would have accelerated development:

- **Earlier integration with SimpleEdit:** Would have caught DOM/event issues sooner
- **More edge case testing upfront:** Regex, unicode, NaN/Infinity edge cases
- **Performance profiling earlier:** Could have optimized hot paths sooner
- **Formal spec study:** Understanding JS spec quirks (type coercion, hoisting) would have prevented some bugs

But honestly? The iterative, test-driven approach proved remarkably effective. Features emerged naturally, bugs were caught quickly, and the result is maintainable code.

---

## Future Directions

### Low-Hanging Fruit

- **Generators & yield:** Parsed but not executed
- **Async/await:** Currently synchronous; could add real Promise support
- **Spread operator:** Limited support; could be expanded
- **Template literals:** Basic support; nested templates would be useful
- **Regular expressions:** Currently regex literals are strings; could add regex engine

### Higher-Effort Features

- **Symbols, WeakMap, Set:** Require new data structures
- **Proxy objects:** Would need metaprogramming support
- **Module system:** (import/export) - significant architectural change
- **Proper hoisting:** Currently incomplete; would require two-pass evaluation

### Performance

- **Caching:** Parse tree caching for repeated execution
- **Bytecode compilation:** Could speed up execution significantly
- **JIT-like optimization:** Detect hot paths and optimize
- **Native binding optimization:** Currently all native calls go through Python reflection

### Quality

- **Formal test suite:** Property-based testing (e.g., QuickCheck)
- **Fuzzing:** Random JavaScript to find crashes
- **Performance benchmarking:** Track execution time, memory usage
- **Documentation:** This file is a start; more needed

---

## Conclusion

Building jsmini through blind iteration and empirical testing was surprisingly effective. Rather than getting bogged down in language specification design, each test failure immediately highlighted what was missing. This created a tight feedback loop:

**Test → Fail → Understand → Fix → Pass → Next Test**

The result is a 2000-line JavaScript interpreter that handles real-world scripts from jQuery to modern ES5+ code. It's not a replacement for a full JS engine, but it proves that building useful tools doesn't always require perfect upfront design—sometimes, iterative testing and real-world feedback are better guides.

### Key Takeaway

> **Don't let perfectionism block iteration. Build something, test it with real data, fix what breaks, repeat. You'll be surprised what emerges.**

---

## References

### Files Mentioned

- `jsmini.py` - Core interpreter implementation
- `js_builtins.py` - Built-in functions (Array, Object, JSON, etc.)
- `functions.py` - HTML parsing and script extraction
- `tests/` - Growing test suite

### External Resources

- [ECMAScript Specification](https://tc39.es/ecma262/)
- [MDN JavaScript Reference](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference)
- [You Don't Know JS Series](https://github.com/getify/You-Dont-Know-JS) - Deep JavaScript semantics

### See Also

- [API Documentation](API.md)
- [Syntax Highlighting Guide](SYNTAX.md)
- [JSMINI.md](JSMINI.md) - User documentation
