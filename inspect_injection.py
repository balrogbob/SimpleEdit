#!/usr/bin/env python3
import sys
from pathlib import Path
import argparse

def find_and_dump(path: Path, patterns, radius_chars=240):
    s = path.read_text(encoding='utf-8', errors='replace')
    for pat in patterns:
        idx = 0
        found = False
        while True:
            i = s.find(pat, idx)
            if i == -1:
                break
            found = True
            start = max(0, i - radius_chars)
            end = min(len(s), i + len(pat) + radius_chars)
            snippet = s[start:end].replace('\n', '\\n')
            print(f"--- match '{pat}' at {i} (snippet {start}:{end}) ---")
            print(snippet)
            print()
            idx = i + 1
        if not found:
            print(f"No occurrences of '{pat}'")
    return

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--src', default='PythonApplication1/test.txt')
    p.add_argument('--patterns', nargs='+', default=['injectedFirstPartyContainers','function mk','function Mm'])
    p.add_argument('--radius', type=int, default=300)
    args = p.parse_args(argv)
    path = Path(args.src)
    if not path.exists():
        print("Source not found:", path)
        return 2
    find_and_dump(path, args.patterns, radius_chars=args.radius)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())