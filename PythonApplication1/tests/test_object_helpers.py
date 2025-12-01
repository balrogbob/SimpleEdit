import sys
from pathlib import Path
import unittest
from test_base import CleanTestCase

# Add parent directory to sys.path so this test can import local modules kept separate from main code.
_project_root = Path(__file__).resolve().parent.parent
_project_root_str = str(_project_root)
if _project_root_str not in sys.path:
    sys.path.insert(0, _project_root_str)

import jsmini
from js_builtins import register_builtins


class TestObjectHelpers(CleanTestCase):
    def setUp(self):
        super().setUp()
        self.ctx = jsmini.make_context()
        # register the project builtins implementation into the context
        register_builtins(self.ctx, jsmini.JSFunction)

    def test_object_create_and_keys(self):
        src = """
        var proto = { p: 1 };
        var o = Object.create(proto);
        o.a = 10;
        o.b = 20;
        // keys should list own enumerable properties only
        var k = Object.keys(o);
        if (k.length !== 2) throw "keys_len";
        var seen = {};
        seen[k[0]] = true; seen[k[1]] = true;
        if (!seen['a'] || !seen['b']) throw "keys_vals";
        // keys of created object should not include prototype members
        if (Object.keys(o).indexOf('p') !== -1) throw "keys_proto_included";
        """
        # should not raise
        jsmini.run(src, self.ctx)

    def test_object_assign(self):
        src = """
        var t = {};
        Object.assign(t, { x: 1 }, { y: 2 });
        if (t.x !== 1) throw "assign_x";
        if (t.y !== 2) throw "assign_y";
        // attempt to assign __proto__ should be ignored by our defensive assign
        var t2 = {};
        Object.assign(t2, { "__proto__": { "evil": 1 } });
        if (t2.evil !== undefined) throw "assign_proto_pollution";
        """
        jsmini.run(src, self.ctx)

    def test_object_create_prototype_access(self):
        src = """
        var p = { z: 3 };
        var c = Object.create(p);
        // inherited property should be accessible
        if (c.z !== 3) throw "create_proto_access";
        // own keys should be empty
        if (Object.keys(c).length !== 0) throw "create_keys";
        """
        jsmini.run(src, self.ctx)


if __name__ == '__main__':
    unittest.main()