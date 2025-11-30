#!/usr/bin/env python3
"""
tokendiag_run_test.py - run a JS file (local path or http(s) URL) through jsmini,
execute it, run queued timers and print useful diagnostics.

Usage:
    python -u tokendiag_run_test.py --src=./test.txt
    python -u tokendiag_run_test.py --src=https://example.com/script.js --verbose --dump-tokens 27172
"""
from __future__ import annotations
import argparse
import sys
import urllib.request as _urr
import urllib.parse as _up
import traceback
from pathlib import Path
from typing import Optional

# Try to import jsmini from either package location used in this repo
try:
    # preferred path when running from repo root
    from PythonApplication1.jsmini import parse, run_with_interpreter, run_timers, make_context, dump_tokens, diagnose_parse
except Exception:
    try:
        # fallback if module is on sys.path as `jsmini`
        from jsmini import parse, run_with_interpreter, run_timers, make_context, dump_tokens, diagnose_parse
    except Exception as e:
        print("ERROR: failed to import jsmini module:", e, file=sys.stderr)
        raise


def fetch_src(src: str, timeout: int = 20) -> str:
    """Fetch a source string from URL or read a local file. Returns text (utf-8, errors replaced)."""
    parsed = _up.urlparse(src)
    if parsed.scheme in ("http", "https"):
        req = _urr.Request(src, headers={"User-Agent": "tokendiag_run_test/1.0"})
        with _urr.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return raw.decode("utf-8", errors="replace")
    # treat as local path
    p = Path(src)
    if p.is_file():
        return p.read_text(encoding="utf-8", errors="replace")
    raise FileNotFoundError(f"Source not found: {src}")


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="tokendiag_run_test.py", description="Run jsmini on a file or URL and execute it")
    p.add_argument("--src", required=True, help="Source URL (http(s)://...) or local path to JS file")
    p.add_argument("--timeout", type=int, default=20, help="HTTP fetch timeout (seconds)")
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    p.add_argument("--dump-tokens", type=int, default=None, metavar="IDX",
                   help="Dump tokens around token index (uses jsmini.dump_tokens)")
    p.add_argument("--radius-tokens", type=int, default=40, help="Token dump window size (tokens)")
    p.add_argument("--radius-chars", type=int, default=80, help="Source snippet window (chars) for diagnostics")
    args = p.parse_args(argv)

    try:
        src_text = fetch_src(args.src, timeout=args.timeout)
    except Exception as e:
        print(f"ERROR: unable to load source '{args.src}': {e}", file=sys.stderr)
        return 2

    print(f"Loaded {len(src_text)} bytes from {args.src}")

    # quick parse diagnostics
    try:
        print("Parsing... ", end="", flush=True)
        _ = parse(src_text)
        print("OK")
    except Exception as e:
        print("Parse failed:")
        # try to produce richer diagnostic using diagnose_parse if available
        try:
            diag = diagnose_parse(src_text, radius_tokens=args.radius_tokens, radius_chars=args.radius_chars)
            print(diag)
        except Exception:
            traceback.print_exc()
        return 3

    # optional token dump up-front when requested
    if args.dump_tokens is not None:
        try:
            print("\n--- token dump ---\n")
            td = dump_tokens(src_text, args.dump_tokens, count=args.radius_tokens)
            print(td)
        except Exception as e:
            print("ERROR running dump_tokens():", e, file=sys.stderr)

    # prepare context with console.log hooked to print
    ctx = make_context(log_fn=print)

    # Run script
    try:
        print("\nRunning script...")
        result, interp = run_with_interpreter(src_text, ctx)
        print("Run finished. Result repr:", repr(result))
    except Exception as e:
        print("Runtime exception during run_with_interpreter:")
        traceback.print_exc()
        # attempt a diagnose_parse fallback to show parser context if runtime seems silent
        try:
            diag = diagnose_parse(src_text, radius_tokens=args.radius_tokens, radius_chars=args.radius_chars)
            print("\nAdditional parser diagnostics (post-runtime):\n", diag)
        except Exception:
            pass
        return 4

    # show queued timers
    timers = ctx.get("_timers", [])
    print(f"\nQueued timers: {len(timers)}")
    for i, (fn, args_) in enumerate(list(timers)):
        tkind = "JSFunction" if hasattr(fn, "call") else type(fn).__name__
        print(f"  [{i}] {tkind}, args={args_}")

    # run queued timers
    try:
        print("\nRunning timers...")
        run_timers(ctx)
        remaining = len(ctx.get("_timers", []))
        print("Timers executed; remaining queued:", remaining)
    except Exception as e:
        print("Exception while running timers:")
        traceback.print_exc()
        return 5

    if args.verbose:
        # extra helpful checks: try a re-parse with diagnose_parse and show summary
        try:
            diag = diagnose_parse(src_text, radius_tokens=args.radius_tokens, radius_chars=args.radius_chars)
            print("\nParser diagnostic summary:\n", diag)
        except Exception:
            pass

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())