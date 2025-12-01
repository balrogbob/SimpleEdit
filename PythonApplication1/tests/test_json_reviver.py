import sys
from pathlib import Path
import unittest
from test_base import CleanTestCase

# Add parent directory to sys.path so this test (kept separate) can import the local jsmini module.
_project_root = Path(__file__).resolve().parent.parent
_project_root_str = str(_project_root)
if _project_root_str not in sys.path:
    sys.path.insert(0, _project_root_str)

import jsmini


class TestJSONReviver(CleanTestCase):
    def setUp(self):
        super().setUp()
        # make_context registers builtins (including JSON) so pass the same context to interpreter
        self.ctx = jsmini.make_context(log_fn=None)

    def test_reviver_deletes_property(self):
        src = r"""JSON.parse('{"a":1,"b":2}', function(k,v){ console.log('k=', k, 'v=', v); if(k==='b') return undefined; return v; })"""
        res, _interp = jsmini.run_with_interpreter(src, self.ctx)
        # result should be JS object mapping; 'a' present, 'b' removed
        self.assertIsInstance(res, dict)
        self.assertIn('a', res)
        self.assertNotIn('b', res)

    def test_reviver_transforms_nested(self):
        src = r"""JSON.parse('{"x":{"y":1}}', function(k,v){ if(k==='y') return v*10; return v; })"""
        res, _interp = jsmini.run_with_interpreter(src, self.ctx)
        self.assertIsInstance(res, dict)
        x = res.get('x')
        self.assertIsInstance(x, dict)
        # numeric conversions come out as float in interpreter
        self.assertEqual(x.get('y'), 10.0)

if __name__ == '__main__':
    unittest.main()