from pathlib import Path
import functions as funcs

html_path = Path(__file__).parent / "examples" / "demo.html"
raw = html_path.read_text(encoding='utf-8')

scripts = funcs.extract_script_tags(raw)

# host callback used by run_scripts — here just print and show before/after
def host_update_cb(new_raw):
    print("host_update_cb called. new_raw is None => reparse existing; otherwise show preview.")
    if new_raw is None:
        print("[host] forceRerender requested")
    else:
        print("[host] setRaw called with (first 200 chars):")
        print(new_raw[:200])

# run scripts with a host callback but without a GUI
results = funcs.run_scripts(scripts, base_url=None, log_fn=print, host_update_cb=host_update_cb)
print("run_scripts results:", results)