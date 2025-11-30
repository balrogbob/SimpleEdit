"""# Run in REPL or a small script (not added to repo)
import urllib.request as _urr, jsmini
src = _urr.urlopen("http://iconofgaming.com/jquery.js").read().decode('utf-8', errors='replace')
print(jsmini.dump_tokens(src, 8275, count=80))
print()
print(jsmini.diagnose_parse(src, radius_tokens=80, radius_chars=160))"""

# Run in REPL (not saved into repo)
import urllib.request as _urr, jsmini
src = _urr.urlopen("http://iconofgaming.com/jquery.js").read().decode('utf-8', errors='replace')
print(jsmini.dump_tokens(src, 37934, count=80))
print()
print(jsmini.diagnose_parse(src, radius_tokens=80, radius_chars=160))
