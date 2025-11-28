# Run the inline scripts from the demo HTML using jsmini.
# Place this next to your project and run with the project PYTHONPATH so `jsmini` is importable.

import re
import jsmini
import functions as funcs  # optional: use existing extractor in your project

# replace the simple utf-8 read with tolerant decoding
with open("examples/demo.html", "rb") as fh:
    raw_bytes = fh.read()
try:
    RAW_HTML = raw_bytes.decode("utf-8")
except UnicodeDecodeError:
    # try common fallback and preserve content, then optionally re-encode to utf-8 for downstream code
    RAW_HTML = raw_bytes.decode("cp1252", errors="replace")

# extract scripts (reuse your project's helper if present)
try:
    scripts = funcs.extract_script_tags(RAW_HTML)
except Exception:
    # fallback simple extractor (inline only)
    SCRIPT_RE = re.compile(r'(?is)<script\b[^>]*>(.*?)</script\s*>')
    scripts = []
    for m in SCRIPT_RE.finditer(RAW_HTML):
        body = m.group(1) or ''
        scripts.append({'src': None, 'inline': body, 'attrs': {}})

# prepare shared context capturing console.log
logs = []
def capture_log(s):
    logs.append(str(s))

ctx = jsmini.make_context(log_fn=capture_log)

# run inline scripts in document order
for s in scripts:
    if s.get('inline'):
        try:
            # run and keep interpreter on ctx so setTimeout handlers can be executed later
            jsmini.run_with_interpreter(s['inline'], ctx)
        except Exception as ex:
            print("Execution error:", ex)

# run queued timers (simulated setTimeout)
jsmini.run_timers(ctx)

# inspect results
print("JS console logs:")
for line in logs:
    print("  ", line)

# inspect tiny DOM shim state
doc = ctx.get('document')
if doc:
    body = doc.get('body')
    if body:
        print("document.body children count:", len(getattr(body, 'children', [])))
        for idx, child in enumerate(body.children):
            print(f" child[{idx}] ->", repr(child))