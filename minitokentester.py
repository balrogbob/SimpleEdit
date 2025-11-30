"""# Run in REPL or a small script (not added to repo)
import urllib.request as _urr, jsmini
src = _urr.urlopen("http://iconofgaming.com/jquery.js").read().decode('utf-8', errors='replace')
print(jsmini.dump_tokens(src, 8275, count=80))
print()
print(jsmini.diagnose_parse(src, radius_tokens=80, radius_chars=160))"""

from pathlib import Path
import jsmini

# Absolute path example (raw string to avoid backslash escapes)
file_path = Path(r"C:\Users\User\source\repos\SimpleEdit\test.txt")

# Or relative to this script:
# file_path = Path(__file__).resolve().parent / "test.txt"

# Read file safely with utf-8 and replacement for invalid bytes
src = file_path.read_text(encoding="utf-8", errors="replace")

print(jsmini.dump_tokens(src, 27160, count=64))
print()
print(jsmini.diagnose_parse(src, radius_tokens=64, radius_chars=240))