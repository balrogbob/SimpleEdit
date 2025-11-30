#!/usr/bin/env python3
"""
Unittest wrapper for tokendiag_run_test behaviour.

This test fetches a jQuery build from Google CDN, parses it with jsmini,
executes it, runs queued timers and performs basic sanity checks.
"""
from __future__ import annotations
import sys
import unittest
from pathlib import Path
import urllib.request as _urr
import urllib.error as _urlerr

# Ensure local package directory is importable so the test remains separate from main code.
_this_dir = Path(__file__).resolve().parent
_this_dir_str = str(_this_dir)
if _this_dir_str not in sys.path:
    sys.path.insert(0, _this_dir_str)

import jsmini


class TestTokenDiagRun(unittest.TestCase):
    def setUp(self):
        # prepare a fresh context with console.log hooked to print
        self.ctx = jsmini.make_context(log_fn=print)

    def test_fetch_parse_and_run_jquery(self):
        """Fetch jQuery from Google CDN, parse and execute it without fatal errors."""
        url = "https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"
        try:
            req = _urr.Request(url, headers={"User-Agent": "tokendiag_run_test/1.0"})
            with _urr.urlopen(req, timeout=20) as resp:
                raw = resp.read()
                src_text = raw.decode("utf-8", errors="replace")
        except (OSError, _urlerr.URLError) as e:
            # Network unavailable; skip rather than failing the test on CI without network.
            self.skipTest(f"Unable to fetch jQuery from network: {e}")

        # Basic parse check with helpful diagnostic on failure
        try:
            jsmini.parse(src_text)
        except Exception as e:
            try:
                diag = jsmini.diagnose_parse(src_text, radius_tokens=40, radius_chars=120)
            except Exception:
                diag = f"(diagnose_parse failed: {e})"
            self.fail(f"Parse failed for fetched jQuery. Diagnostic:\n{diag}")

        # Execute script and ensure no runtime error is raised
        try:
            result, interp = jsmini.run_with_interpreter(src_text, self.ctx)
        except Exception as e:
            self.fail(f"Runtime exception during run_with_interpreter: {e}")

        # Show queued timers and execute them; test should not error
        timers = self.ctx.get("_timers", [])
        # Execute timers (should not raise)
        try:
            jsmini.run_timers(self.ctx)
        except Exception as e:
            self.fail(f"Exception while running timers: {e}")

        # Basic sanity assertions
        self.assertIsNotNone(result)
        self.assertIsInstance(timers, list)

if __name__ == "__main__":
    unittest.main()