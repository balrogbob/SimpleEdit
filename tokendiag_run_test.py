#!/usr/bin/env python3
import traceback
from pathlib import Path
from jsmini import parse, run_with_interpreter, run_timers, make_context

def main():
    src = Path("PythonApplication1/test.txt").read_text(encoding="utf-8", errors="replace")
    # use print as log_fn so console.log from JS is visible
    ctx = make_context(log_fn=print)
    try:
        print("Parsing... ", end="", flush=True)
        _ = parse(src)  # quick parse check (optional)
        print("OK")
    except Exception as e:
        print("Parse failed:")
        traceback.print_exc()
        return 1

    try:
        print("Running script...")
        result, interp = run_with_interpreter(src, ctx)
        print("Run finished. Result repr:", repr(result))
    except Exception as e:
        print("Runtime exception during run_with_interpreter:")
        traceback.print_exc()
        return 2

    # Inspect timers queued in context
    timers = ctx.get("_timers", [])
    print(f"Queued timers: {len(timers)}")
    for i, (fn, args) in enumerate(list(timers)):
        tkind = "JSFunction" if hasattr(fn, "call") else type(fn).__name__
        print(f"  [{i}] {tkind}, args={args}")

    # Execute timers (this will call JSFunction.call if interpreter present on ctx)
    try:
        print("Running timers...")
        run_timers(ctx)
        print("Timers executed; remaining queued:", len(ctx.get("_timers", [])))
    except Exception as e:
        print("Exception while running timers:")
        traceback.print_exc()
        return 3

    print("Done.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())