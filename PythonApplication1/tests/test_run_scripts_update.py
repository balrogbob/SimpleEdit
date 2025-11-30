import sys
from pathlib import Path
import unittest

# Ensure this test can import the local `functions` module kept in the same directory.
_test_dir = Path(__file__).resolve().parent
_test_dir_str = str(_test_dir)
if _test_dir_str not in sys.path:
    sys.path.insert(0, _test_dir_str)

import functions as funcs


class TestRunScriptsUpdate(unittest.TestCase):
    def setUp(self):
        # load example HTML used by the test
        self.html_path = Path(__file__).resolve().parent / "examples" / "demo.html"
        self.raw = self.html_path.read_text(encoding="utf-8")

    def _host_update_cb(self, new_raw):
        # host callback used by run_scripts — match original script behavior for verification
        print("host_update_cb called. new_raw is None => reparse existing; otherwise show preview.")
        if new_raw is None:
            print("[host] forceRerender requested")
        else:
            print("[host] setRaw called with (first 200 chars):")
            print(new_raw[:200])

    def test_run_scripts_update_executes_without_error(self):
        scripts = funcs.extract_script_tags(self.raw)
        # run scripts with a host callback but without a GUI
        results = funcs.run_scripts(
            scripts,
            base_url=None,
            log_fn=print,
            host_update_cb=self._host_update_cb
        )
        # Basic verification: results should be returned (non-None) and not raise
        self.assertIsNotNone(results)


if __name__ == "__main__":
    unittest.main()