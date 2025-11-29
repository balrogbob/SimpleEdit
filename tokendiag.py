#!/usr/bin/env python3
"""
tokendiag.py - simple CLI to fetch a JS source (http(s) or local file) and run jsmini diagnostics.

Usage:
    python -u tokendiag.py -src=http://iconofgaming.com/jquery.js
    python -u tokendiag.py -src=./vendors/jquery.min.js --dump-tokens 215 --radius-tokens 48

Outputs diagnostic text from `PythonApplication1.jsmini.diagnose_parse` and optionally a token dump.
"""
from __future__ import annotations
import argparse
import os
import sys
import urllib.request as _urr
import urllib.parse as _up
from typing import Optional

# ensure repo root is importable (script placed in repo root)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

try:
    from PythonApplication1 import jsmini
except Exception as e:
    print("ERROR: Failed importing PythonApplication1.jsmini:", e, file=sys.stderr)
    sys.exit(2)


def fetch_src(src: str, timeout: int = 20) -> str:
    """Fetch a source string from URL or read a local file. Returns text (utf-8, errors replaced)."""
    parsed = _up.urlparse(src)
    if parsed.scheme in ("http", "https"):
        req = _urr.Request(src, headers={"User-Agent": "tokendiag/1.0"})
        with _urr.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return raw.decode("utf-8", errors="replace")
    # treat as local path
    if os.path.isfile(src):
        with open(src, "rb") as f:
            return f.read().decode("utf-8", errors="replace")
    raise FileNotFoundError(f"Source not found: {src}")


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="tokendiag.py", description="Fetch JS and run jsmini tokenizer/parser diagnostics")
    p.add_argument("-src", required=True, help="Source URL or local path (http://... or ./file.js)")
    p.add_argument("--dump-tokens", type=int, default=None, metavar="IDX",
                   help="Also dump tokens around token index IDX using jsmini.dump_tokens")
    p.add_argument("--radius-tokens", type=int, default=40, help="Token dump window size (tokens)")
    p.add_argument("--radius-chars", type=int, default=80, help="Source snippet window (chars)")
    p.add_argument("--timeout", type=int, default=20, help="HTTP fetch timeout (seconds)")
    args = p.parse_args(argv)

    try:
        src_text = fetch_src(args.src, timeout=args.timeout)
    except Exception as e:
        print(f"ERROR: unable to load source '{args.src}': {e}", file=sys.stderr)
        return 2

    print(f"Loaded {len(src_text)} bytes from {args.src}\n---\n")

    # run diagnose (best-effort; it returns informative string)
    try:
        diag = jsmini.diagnose_parse(src_text, radius_tokens=args.radius_tokens, radius_chars=args.radius_chars)
        print(diag)
    except Exception as e:
        print("ERROR running diagnose_parse():", e, file=sys.stderr)
        return 2

    # optional token dump
    if args.dump_tokens is not None:
        try:
            print("\n--- token dump ---\n")
            td = jsmini.dump_tokens(src_text, args.dump_tokens, count=args.radius_tokens)
            print(td)
        except Exception as e:
            print("ERROR running dump_tokens():", e, file=sys.stderr)
            return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
