# 🚀 SimpleEdit Advanced Examples

**Complex Use Cases, Patterns, and Optimization Recipes**

**Status:** Complete advanced examples collection  
**Last Updated:** January 12, 2025  
**For:** Advanced Users and Contributors

---

## Table of Contents

- [Overview](#overview)
- [Advanced JavaScript Patterns](#advanced-javascript-patterns)
- [System Integration Examples](#system-integration-examples)
- [Performance Optimization Recipes](#performance-optimization-recipes)
- [Advanced Configuration](#advanced-configuration)
- [Debugging & Profiling](#debugging--profiling)
- [Common Pitfalls](#common-pitfalls)

---

## Overview

This document covers **advanced use cases** for SimpleEdit, including complex JavaScript patterns, system integration techniques, performance optimization, and debugging strategies.

### Prerequisites

Before reading this guide:
- ✅ Read [API.md](API.md) - Understand public APIs
- ✅ Read [JSMINI.md](JSMINI.md) - Know JavaScript engine details
- ✅ Read [ARCHITECTURE.md](ARCHITECTURE.md) - Understand system design
- ✅ Familiar with Python and JavaScript

### Difficulty Levels

- 🟢 **Beginner** - Start here, common patterns
- 🟡 **Intermediate** - Some complexity, good patterns
- 🔴 **Advanced** - Complex scenarios, edge cases

---

## Advanced JavaScript Patterns

### Example 1: DOM Manipulation with Event Delegation 🟡

**Pattern:** Event delegation for dynamic content

**Use Case:** Handle clicks on dynamically generated elements without re-binding

```python
from functions import run_scripts, extract_script_tags

html = """
<html>
<body>
  <div id="container">
    <button class="item">Item 1</button>
    <button class="item">Item 2</button>
  </div>
  
  <script>
    var container = document.getElementById('container');
    var count = 0;
    
    // Event delegation: listen on parent, act on children
    container.addEventListener('click', function(e) {
      if (e.target && e.target.className === 'item') {
        count++;
        console.log('Item clicked. Count: ' + count);
        e.target.textContent = 'Clicked ' + count + ' times';
      }
    });
    
    // Dynamically add more items
    setTimeout(function() {
      var btn = document.createElement('button');
      btn.className = 'item';
      btn.textContent = 'Item 3 (dynamic)';
      container.appendChild(btn);
      console.log('Added dynamic button - still responds to event delegation');
    }, 100);
  </script>
</body>
</html>
"""

scripts = extract_script_tags(html)
results = run_scripts(
    scripts,
    return_dom=True,
    force_final_redraw=True,
    run_blocking=True
)

if results['results'][0]['ok']:
    print("✅ Event delegation worked")
    print(f"Final DOM:\n{results['final_dom']}")
else:
    print(f"❌ Error: {results['results'][0]['error']}")
```

**Key Learning:**
- Event delegation prevents memory leaks from repeated listeners
- Dynamic elements automatically respond to delegated events
- More efficient than re-binding to each element

---

### Example 2: Closures and Data Privacy 🔴

**Pattern:** Use closures to create private state

**Use Case:** Counter module with private variable access control

```python
from functions import run_scripts, extract_script_tags

html = """
<html>
<body>
  <script>
    // Module pattern with closures
    var Counter = (function() {
      var count = 0;  // private variable
      
      return {
        increment: function() {
          count++;
          return count;
        },
        decrement: function() {
          count--;
          return count;
        },
        getCount: function() {
          return count;
        },
        reset: function() {
          count = 0;
        }
      };
    })();
    
    console.log('Initial: ' + Counter.getCount());
    console.log('After increment: ' + Counter.increment());
    console.log('After increment: ' + Counter.increment());
    console.log('After decrement: ' + Counter.decrement());
    console.log('Final: ' + Counter.getCount());
    
    // Cannot access count directly (private)
    console.log('Direct access to count: ' + (Counter.count === undefined ? 'undefined (private)' : Counter.count));
  </script>
</body>
</html>
"""

scripts = extract_script_tags(html)
results = run_scripts(scripts, run_blocking=True)

for i, result in enumerate(results):
    if result['ok']:
        print(f"✅ Script {i+1} executed")
    else:
        print(f"❌ Script {i+1} error: {result['error']}")
```

**Key Learning:**
- Closures provide true data privacy in JavaScript
- Module pattern encapsulates state
- Prevents accidental global variable pollution

---

### Example 3: Higher-Order Functions and Functional Programming 🟡

**Pattern:** Functions that return functions

**Use Case:** Create reusable function transformers

```python
from functions import run_scripts, extract_script_tags

html = """
<html>
<body>
  <script>
    // Higher-order function: returns a new function
    function multiply(factor) {
      return function(number) {
        return number * factor;
      };
    }
    
    var double = multiply(2);
    var triple = multiply(3);
    
    console.log('5 * 2 = ' + double(5));    // 10
    console.log('5 * 3 = ' + triple(5));    // 15
    
    // Compose functions
    function compose(f, g) {
      return function(x) {
        return f(g(x));
      };
    }
    
    function add5(x) { return x + 5; }
    function multiplyBy2(x) { return x * 2; }
    
    var addThenMultiply = compose(multiplyBy2, add5);
    console.log('(3 + 5) * 2 = ' + addThenMultiply(3));  // 16
    
    // Array functional methods
    var numbers = [1, 2, 3, 4, 5];
    var result = numbers
      .filter(function(n) { return n > 2; })
      .map(function(n) { return n * 2; })
      .reduce(function(sum, n) { return sum + n; }, 0);
    
    console.log('Filter > 2, map *2, sum = ' + result);  // 24
  </script>
</body>
</html>
"""

scripts = extract_script_tags(html)
results = run_scripts(scripts, run_blocking=True)

print("✅ Functional programming patterns executed")
```

**Key Learning:**
- Higher-order functions enable powerful abstractions
- Function composition creates reusable transformations
- Functional methods (map, filter, reduce) are powerful

---

### Example 4: Error Handling and Try-Catch Patterns 🟡

**Pattern:** Robust error handling in JavaScript

**Use Case:** Graceful error recovery

```python
from functions import run_scripts, extract_script_tags

html = """
<html>
<body>
  <script>
    function safeJsonParse(jsonString) {
      try {
        var parsed = JSON.parse(jsonString);
        return { success: true, data: parsed };
      } catch (e) {
        return { success: false, error: e.toString() };
      }
    }
    
    // Valid JSON
    var result1 = safeJsonParse('{"name": "Alice", "age": 30}');
    console.log('Valid JSON: ' + (result1.success ? 'Parsed' : 'Failed'));
    
    // Invalid JSON
    var result2 = safeJsonParse('{invalid json}');
    console.log('Invalid JSON: ' + (result2.success ? 'Parsed' : 'Failed - ' + result2.error));
    
    // Nested try-catch with finally
    function riskyOperation() {
      var resource = null;
      try {
        console.log('Acquiring resource...');
        resource = 'database_connection';
        // Simulate error
        throw new Error('Connection failed');
      } catch (e) {
        console.log('Caught error: ' + e);
        return 'recovered';
      } finally {
        console.log('Cleanup: releasing ' + (resource || 'no resource'));
      }
    }
    
    console.log('Operation result: ' + riskyOperation());
  </script>
</body>
</html>
"""

scripts = extract_script_tags(html)
results = run_scripts(scripts, run_blocking=True)

if results[0]['ok']:
    print("✅ Error handling patterns executed successfully")
else:
    print(f"❌ Error: {results[0]['error']}")
```

**Key Learning:**
- Try-catch enables graceful error recovery
- Finally block always runs for cleanup
- Functional approach (return success/error) is more maintainable

---

### Example 5: Async Patterns with Timers and Callbacks 🔴

**Pattern:** Simulating asynchronous operations

**Use Case:** Staggered updates, debouncing, throttling

```python
from functions import run_scripts, extract_script_tags

html = """
<html>
<body id="output"></body>
<script>
    var output = document.getElementById('output');
    
    // Debounce pattern: delay execution until activity stops
    function debounce(func, delay) {
      var timeoutId = null;
      return function() {
        if (timeoutId !== null) {
          clearTimeout(timeoutId);
        }
        var args = arguments;
        var self = this;
        timeoutId = setTimeout(function() {
          func.apply(self, args);
        }, delay);
      };
    }
    
    var handleSearch = debounce(function(query) {
      var msg = 'Searching for: ' + query;
      console.log(msg);
      output.innerHTML += msg + '<br>';
    }, 300);
    
    // Simulate multiple rapid calls
    handleSearch('j');
    handleSearch('ja');
    handleSearch('jav');
    handleSearch('java');  // Only this one executes after 300ms
    
    // Throttle pattern: limit execution frequency
    function throttle(func, limit) {
      var inThrottle = false;
      return function() {
        if (!inThrottle) {
          var args = arguments;
          var self = this;
          func.apply(self, args);
          inThrottle = true;
          setTimeout(function() {
            inThrottle = false;
          }, limit);
        }
      };
    }
    
    var handleScroll = throttle(function() {
      console.log('Scroll event (throttled)');
    }, 1000);
    
    // Timer chain for sequential operations
    setTimeout(function() {
      console.log('Step 1: Starting');
      setTimeout(function() {
        console.log('Step 2: Processing');
        setTimeout(function() {
          console.log('Step 3: Complete');
        }, 100);
      }, 100);
    }, 100);
</script>
</html>
"""

scripts = extract_script_tags(html)
results = run_scripts(
    scripts,
    return_dom=True,
    run_blocking=True,
    force_final_redraw=True
)

print("✅ Async patterns with debounce and throttle executed")
```

**Key Learning:**
- Debounce delays execution until activity stops (useful for search)
- Throttle limits frequency of execution (useful for scroll events)
- Timers enable sequential operations

---

## System Integration Examples

### Example 6: Extending Syntax Highlighting for Custom Language 🟡

**Pattern:** Add support for a new language

**Use Case:** Highlight custom domain-specific language

```python
from syntax_worker import process_slice

def highlight_custom_yaml(content):
    """Highlight custom YAML-like configuration format."""
    
    # Custom keywords for our DSL
    keywords = [
        'DATABASE', 'SERVER', 'PORT', 'USERNAME', 'PASSWORD',
        'TIMEOUT', 'RETRIES', 'LOG_LEVEL', 'DEBUG'
    ]
    
    builtins = [
        'localhost', 'true', 'false', 'null'
    ]
    
    results = process_slice(
        content=content,
        s_start=0,
        s_end=len(content),
        protected_spans=[],
        keywords=keywords,
        builtins=builtins
    )
    
    return results

# Example custom config content
config = """
DATABASE:
  SERVER: localhost
  PORT: 5432
  USERNAME: admin
  PASSWORD: secret123
  TIMEOUT: 30
  RETRIES: 3

LOGGING:
  LOG_LEVEL: DEBUG
  DEBUG: true
"""

highlights = highlight_custom_yaml(config)

print("✅ Custom language highlighting:")
for tag_type, ranges in highlights.items():
    if ranges:
        print(f"  {tag_type}: {len(ranges)} occurrences")
```

**Key Learning:**
- Custom keyword lists enable new language support
- Syntax highlighting is pattern-based
- Can be integrated into editor workflow

---

### Example 7: Custom File Handler Integration 🔴

**Pattern:** Process files in custom format

**Use Case:** Handle proprietary file format with custom parsing

```python
from functions import _parse_html_and_apply
import json

def handle_custom_markup(raw_content):
    """
    Parse custom markup format:
    @TITLE: Document Title
    @AUTHOR: Author Name
    ---
    <html content>
    """
    
    # Extract metadata
    lines = raw_content.split('\n')
    metadata = {}
    content_start = 0
    
    for i, line in enumerate(lines):
        if line.startswith('@'):
            key, value = line[1:].split(':', 1)
            metadata[key.strip()] = value.strip()
        elif line.strip() == '---':
            content_start = i + 1
            break
    
    # Parse HTML content
    html_content = '\n'.join(lines[content_start:])
    plain_text, html_meta = _parse_html_and_apply(html_content)
    
    # Merge metadata
    result = {
        'custom_metadata': metadata,
        'text': plain_text,
        'html_metadata': html_meta
    }
    
    return result

# Example custom file
custom_file = """@TITLE: Advanced Guide
@AUTHOR: SimpleEdit Team
@VERSION: 1.0
---
<h1>Getting Started</h1>
<p>This is a <b>custom format</b> example.</p>
<a href="http://example.com">Learn more</a>
"""

result = handle_custom_markup(custom_file)

print("✅ Custom file handler executed:")
print(f"  Title: {result['custom_metadata'].get('TITLE')}")
print(f"  Author: {result['custom_metadata'].get('AUTHOR')}")
print(f"  Text length: {len(result['text'])} chars")
print(f"  Links found: {len(result['html_metadata'].get('links', []))}")
```

**Key Learning:**
- Custom formats can be parsed and integrated
- Metadata extraction before main processing
- Composition of existing parsers (HTML + custom)

---

### Example 8: DOM-to-Data Transformation Pipeline 🟡

**Pattern:** Extract structured data from DOM

**Use Case:** Parse HTML tables into JSON format

```python
from functions import run_scripts, extract_script_tags

html = """
<html>
<body>
  <table id="data">
    <thead>
      <tr><th>Name</th><th>Age</th><th>City</th></tr>
    </thead>
    <tbody>
      <tr><td>Alice</td><td>30</td><td>New York</td></tr>
      <tr><td>Bob</td><td>25</td><td>Los Angeles</td></tr>
      <tr><td>Charlie</td><td>35</td><td>Chicago</td></tr>
    </tbody>
  </table>
  
  <script>
    function tableToJson(tableId) {
      var table = document.getElementById(tableId);
      var headers = [];
      var rows = [];
      
      // Extract headers
      var headerCells = table.querySelectorAll('thead th');
      for (var i = 0; i < headerCells.length; i++) {
        headers.push(headerCells[i].textContent);
      }
      
      // Extract data rows
      var dataCells = table.querySelectorAll('tbody tr');
      for (var i = 0; i < dataCells.length; i++) {
        var row = {};
        var cells = dataCells[i].querySelectorAll('td');
        for (var j = 0; j < cells.length; j++) {
          row[headers[j]] = cells[j].textContent;
        }
        rows.push(row);
      }
      
      return rows;
    }
    
    var data = tableToJson('data');
    console.log('Extracted ' + data.length + ' records');
    console.log('First record: ' + JSON.stringify(data[0]));
  </script>
</body>
</html>
"""

scripts = extract_script_tags(html)
results = run_scripts(scripts, run_blocking=True)

print("✅ DOM-to-JSON transformation executed")
```

**Key Learning:**
- querySelectorAll enables complex DOM queries
- Data extraction from structured HTML
- JSON serialization for output

---

## Performance Optimization Recipes

### Example 9: Large File Handling Strategy 🔴

**Pattern:** Process files >50KB efficiently

**Use Case:** Syntax highlighting for large Python files

```python
from syntax_worker import process_slice

def highlight_large_file_efficiently(content, chunk_size=8192):
    """
    Process large files in chunks to avoid memory issues
    and enable incremental highlighting.
    """
    
    total_size = len(content)
    results = []
    
    # Process in chunks with small overlap
    overlap = 512
    for start in range(0, total_size, chunk_size):
        end = min(start + chunk_size, total_size)
        
        # Add overlap from previous chunk for continuity
        actual_start = max(0, start - overlap)
        
        # Highlight this chunk
        chunk_results = process_slice(
            content=content,
            s_start=actual_start,
            s_end=end,
            protected_spans=[],
            keywords=['def', 'class', 'if', 'else', 'return'],
            builtins=['print', 'len', 'range']
        )
        
        results.append({
            'chunk': start // chunk_size,
            'start': actual_start,
            'end': end,
            'tags_found': len(chunk_results)
        })
        
        # Progress indicator
        progress = (end * 100) // total_size
        print(f"  Progress: {progress}% ({end}/{total_size} bytes)")
    
    return results

# Simulate large file
large_content = """
def process_data(items):
    '''Process a list of items.'''
    result = []
    for item in items:
        if item > 0:
            result.append(item * 2)
    return result

class DataHandler:
    def __init__(self, name):
        self.name = name
        self.items = []
    
    def add_item(self, item):
        self.items.append(item)
        return len(self.items)

def main():
    handler = DataHandler('test')
    data = [1, 2, 3, 4, 5]
    processed = process_data(data)
    print('Done')

main()
""" * 2000  # Simulate large file

print(f"Processing {len(large_content)} byte file in chunks...")
results = highlight_large_file_efficiently(large_content)
print(f"✅ Processed {len(results)} chunks successfully")
```

**Key Learning:**
- Chunking prevents memory exhaustion
- Overlap maintains context at boundaries
- Progressive processing enables UI feedback

---

### Example 10: Syntax Highlighting Optimization 🟡

**Pattern:** Optimize highlighting for performance

**Use Case:** Fast highlighting of deeply nested structures

```python
from syntax_worker import process_slice

def optimized_highlighting(content):
    """
    Optimize highlighting by:
    1. Skipping already-protected regions
    2. Using efficient regex
    3. Limiting scope
    """
    
    # First pass: identify protected regions (strings, comments)
    protected_spans = []
    
    # Find all strings (simple heuristic)
    import re
    for m in re.finditer(r'["\']{1,3}[^"\']*["\']{1,3}', content):
        protected_spans.append(m.span())
    
    # Find all comments
    for m in re.finditer(r'#[^\n]*', content):
        protected_spans.append(m.span())
    
    # Second pass: highlight, skipping protected regions
    results = process_slice(
        content=content,
        s_start=0,
        s_end=len(content),
        protected_spans=protected_spans,
        keywords=['def', 'class', 'if', 'return'],
        builtins=['print', 'len']
    )
    
    return results, len(protected_spans)

code = """
def hello():
    # This is a comment
    name = "Alice"  # String literal
    print('Hello ' + name)  # Another string
    return name
"""

results, protected_count = optimized_highlighting(code)
print(f"✅ Optimized highlighting:")
print(f"  Protected regions: {protected_count}")
print(f"  Tags found: {sum(len(v) for v in results.values())}")
```

**Key Learning:**
- Pre-identify protected regions for efficiency
- Skip highlighting inside strings/comments
- Reduces redundant processing

---

### Example 11: Efficient JavaScript Execution 🟡

**Pattern:** Optimize script performance

**Use Case:** Minimize DOM operations

```python
from functions import run_scripts, extract_script_tags

html = """
<html>
<body id="container"></body>
<script>
    var container = document.getElementById('container');
    
    // INEFFICIENT: DOM operation inside loop
    function inefficientCreate() {
      console.log('Creating 100 elements (inefficient)');
      for (var i = 0; i < 100; i++) {
        var el = document.createElement('div');
        el.textContent = 'Item ' + i;
        container.appendChild(el);  // Forces reflow each time
      }
    }
    
    // EFFICIENT: Batch DOM operations
    function efficientCreate() {
      console.log('Creating 100 elements (efficient)');
      var fragment = document.createDocumentFragment ? 
        document.createDocumentFragment() : 
        null;
      
      if (fragment) {
        for (var i = 0; i < 100; i++) {
          var el = document.createElement('div');
          el.textContent = 'Item ' + i;
          fragment.appendChild(el);
        }
        container.appendChild(fragment);  // Single reflow
      } else {
        // Fallback: batch append
        var elements = [];
        for (var i = 0; i < 100; i++) {
          var el = document.createElement('div');
          el.textContent = 'Item ' + i;
          elements.push(el);
        }
        for (var i = 0; i < elements.length; i++) {
          container.appendChild(elements[i]);
        }
      }
    }
    
    // Efficient query caching
    var cached = null;
    function cachedQuery() {
      if (!cached) {
        cached = document.getElementById('container');
      }
      return cached;
    }
    
    console.log('Inefficient approach...');
    inefficientCreate();
    
    console.log('Efficient approach would be faster');
    console.log('Key: Batch operations, cache queries, minimize reflows');
</script>
</html>
"""

scripts = extract_script_tags(html)
results = run_scripts(scripts, run_blocking=True)

print("✅ JavaScript optimization patterns executed")
```

**Key Learning:**
- Batch DOM operations reduce reflows
- Cache DOM queries instead of repeated lookups
- Use document fragments for multiple insertions

---

## Advanced Configuration

### Example 12: Programmatic Configuration 🟡

**Pattern:** Modify configuration at runtime

**Use Case:** Change settings based on file type

```python
import configparser
from functions import config, INI_PATH

def configure_for_filetype(filetype):
    """Adjust configuration based on file type."""
    
    if filetype == 'python':
        config.set('Section1', 'syntaxHighlighting', 'True')
        config.set('Section1', 'fontSize', '11')
    elif filetype == 'json':
        config.set('Section1', 'syntaxHighlighting', 'True')
        config.set('Section1', 'fontSize', '10')
    elif filetype == 'html':
        config.set('Section1', 'syntaxHighlighting', 'True')
        config.set('Section1', 'fontSize', '12')
    else:
        config.set('Section1', 'syntaxHighlighting', 'False')
        config.set('Section1', 'fontSize', '12')
    
    # Persist changes
    try:
        with open(INI_PATH, 'w') as f:
            config.write(f)
        print(f"✅ Configured for {filetype}")
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

# Example usage
configure_for_filetype('python')
print(f"  Font size: {config.get('Section1', 'fontSize')}")
print(f"  Highlighting: {config.get('Section1', 'syntaxHighlighting')}")
```

**Key Learning:**
- Configuration can be changed programmatically
- Changes persist when written to INI file
- Useful for context-aware settings

---

### Example 13: Custom Color Schemes 🟡

**Pattern:** Create and apply custom themes

**Use Case:** Dark mode vs Light mode themes

```python
from functions import _hex_to_rgb, _rgb_to_hex, _lighten_color

def create_color_scheme(name, base_color):
    """Generate a color scheme from a base color."""
    
    r, g, b = _hex_to_rgb(base_color)
    
    scheme = {
        'name': name,
        'primary': base_color,
        'light': _lighten_color(base_color, 0.3),
        'lighter': _lighten_color(base_color, 0.6),
        'dark': _rgb_to_hex(
            int(r * 0.7), int(g * 0.7), int(b * 0.7)
        ),
        'accent': _rgb_to_hex(
            255 - r, 255 - g, 255 - b
        ),
    }
    
    return scheme

# Create themes
dark_theme = create_color_scheme('Dark', '#1a1a2e')
blue_theme = create_color_scheme('Blue', '#0066cc')
green_theme = create_color_scheme('Green', '#00aa00')

print("✅ Color schemes created:")
for theme_name in ['dark_theme', 'blue_theme', 'green_theme']:
    theme = locals()[theme_name]
    print(f"\n{theme['name']} Theme:")
    print(f"  Primary: {theme['primary']}")
    print(f"  Light: {theme['light']}")
    print(f"  Dark: {theme['dark']}")
    print(f"  Accent: {theme['accent']}")
```

**Key Learning:**
- Color manipulation enables theme creation
- Complementary colors improve readability
- Programmatic theme generation

---

## Debugging & Profiling

### Example 14: Debugging JavaScript with Context 🟡

**Pattern:** Extract error context and debug information

**Use Case:** Diagnose JavaScript execution errors

```python
from functions import run_scripts, extract_script_tags, _format_js_error_context

html = """
<html>
<body>
  <script>
    function buggy_function() {
      var x = 10;
      var y = 0;
      var z = x / y;  // Division by zero or other issue
      console.log('Result: ' + z);
      return z;
    }
    
    try {
      buggy_function();
    } catch (e) {
      console.log('Caught error: ' + e);
    }
  </script>
</body>
</html>
"""

scripts = extract_script_tags(html)
results = run_scripts(scripts, run_blocking=True)

for i, result in enumerate(results):
    if result['ok']:
        print(f"✅ Script {i+1} executed")
    else:
        error_msg = result['error']
        print(f"❌ Script {i+1} error:")
        print(f"  {error_msg}")
```

**Key Learning:**
- Error context helps identify problems
- Try-catch prevents crashes
- Console logging aids debugging

---

### Example 15: Performance Profiling JavaScript 🔴

**Pattern:** Measure and optimize script performance

**Use Case:** Identify slow operations

```python
from functions import run_scripts, extract_script_tags

html = """
<html>
<body>
  <script>
    // Simple performance measurement
    function measurePerformance(name, func) {
      var start = Date.now();
      var result = func();
      var elapsed = Date.now() - start;
      console.log(name + ': ' + elapsed + 'ms');
      return result;
    }
    
    // Slow algorithm: naive fibonacci
    function slowFib(n) {
      if (n <= 1) return n;
      return slowFib(n - 1) + slowFib(n - 2);
    }
    
    // Fast algorithm: memoized fibonacci
    function fastFib(n) {
      var memo = {};
      function fib(x) {
        if (x in memo) return memo[x];
        if (x <= 1) return x;
        memo[x] = fib(x - 1) + fib(x - 2);
        return memo[x];
      }
      return fib(n);
    }
    
    console.log('Performance comparison:');
    measurePerformance('Slow fib(25)', function() {
      return slowFib(25);
    });
    
    measurePerformance('Fast fib(25)', function() {
      return fastFib(25);
    });
    
    // Memory-efficient iteration
    function iterativeFib(n) {
      if (n <= 1) return n;
      var a = 0, b = 1, temp;
      for (var i = 2; i <= n; i++) {
        temp = a + b;
        a = b;
        b = temp;
      }
      return b;
    }
    
    measurePerformance('Iterative fib(25)', function() {
      return iterativeFib(25);
    });
  </script>
</body>
</html>
"""

scripts = extract_script_tags(html)
results = run_scripts(scripts, run_blocking=True)

if results[0]['ok']:
    print("✅ Performance profiling executed")
else:
    print(f"❌ Error: {results[0]['error']}")
```

**Key Learning:**
- Date.now() measures execution time
- Algorithm optimization significantly impacts performance
- Memoization and iteration beat recursion

---

## Common Pitfalls

### Pitfall 1: Scope Issues

```javascript
// ❌ WRONG: Variable leaked to global scope
function createCounter() {
  count = 0;  // Missing 'var', creates global!
  return function() { return ++count; };
}

// ✅ RIGHT: Proper variable declaration
function createCounter() {
  var count = 0;  // Explicit scope
  return function() { return ++count; };
}
```

### Pitfall 2: Async Timing

```javascript
// ❌ WRONG: Assumes variable is set immediately
function getData() {
  var result = null;
  setTimeout(function() { result = 42; }, 100);
  return result;  // Returns null!
}

// ✅ RIGHT: Use callback or promise pattern
function getData(callback) {
  setTimeout(function() { callback(42); }, 100);
}
```

### Pitfall 3: Event Listener Memory Leaks

```javascript
// ❌ WRONG: Re-binding creates multiple listeners
function setupListener() {
  var btn = document.getElementById('btn');
  btn.addEventListener('click', function() {
    console.log('clicked');
  });
}
setupListener();  // Creates one listener
setupListener();  // Creates another!

// ✅ RIGHT: Remove old listeners or use delegation
function setupListener() {
  var btn = document.getElementById('btn');
  btn.onclick = function() {  // Overwrites previous
    console.log('clicked');
  };
}
```

---

## Summary

This guide covered **15+ advanced patterns and optimization techniques**:

### JavaScript Patterns
- Event delegation for dynamic content
- Closures for data privacy
- Functional programming and composition
- Error handling and recovery
- Async patterns (debounce, throttle)

### System Integration
- Custom syntax highlighting
- File handler integration
- DOM-to-data transformation

### Performance Optimization
- Large file handling strategies
- Syntax highlighting optimization
- Efficient JavaScript execution

### Advanced Configuration
- Programmatic settings
- Custom color schemes

### Debugging & Profiling
- JavaScript debugging with context
- Performance measurement and optimization

---

## See Also

- **[API Reference](API.md)** - All available functions
- **[JSMINI Guide](JSMINI.md)** - JavaScript engine details
- **[INTERNAL-API](INTERNAL-API.md)** - Internal functions for contributors
- **[Architecture](ARCHITECTURE.md)** - System design
- **[Code Examples](EXAMPLES.md)** - Basic examples
- **[Performance Tuning](PERFORMANCE-TUNING.md)** - System-level optimization

---

**Advanced Examples for SimpleEdit**

*Complete reference to advanced use cases, complex patterns, performance optimization recipes, and debugging strategies for power users and contributors.*
