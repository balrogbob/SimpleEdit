import unittest
import sys
from typing import Optional

try:
    import jsmini
except Exception:
    jsmini = None


class CleanTestCase(unittest.TestCase):
    """Base class that drains jsmini timers and flushes stdout/stderr in tearDown.

    Tests that use jsmini should assign the context to `self.ctx` in setUp.
    """

    def setUp(self):
        self.ctx: Optional[dict] = None

    def tearDown(self):
        # Drain queued timers to avoid background callbacks racing with interpreter shutdown
        try:
            if jsmini is not None and self.ctx:
                jsmini.run_timers_from_context(self.ctx)
        except Exception:
            pass

        # Flush stdio to avoid buffered writes during finalization
        try:
            sys.stdout.flush()
        except Exception:
            pass
        try:
            sys.stderr.flush()
        except Exception:
            pass
