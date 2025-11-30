import sys
from pathlib import Path
import unittest

# Add parent directory to sys.path so this test can import local modules kept separate from main code.
_project_root = Path(__file__).resolve().parent.parent
_project_root_str = str(_project_root)
if _project_root_str not in sys.path:
    sys.path.insert(0, _project_root_str)

import jsmini
from js_builtins import register_builtins


class TestJSBuiltins(unittest.TestCase):
    def test_array_push_pop(self):
        ctx = jsmini.make_context()
        register_builtins(ctx, jsmini.JSFunction)
        src = """
        var a = new Array();
        a.push(10);
        a.push(20);
        if (a.length !== 2) throw "len";
        var p = a.pop();
        if (p !== 20) throw "pop";
        """
        # should not raise
        jsmini.run(src, ctx)


if __name__ == '__main__':
    unittest.main()
