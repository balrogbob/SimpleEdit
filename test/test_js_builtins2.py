import pytest
from PythonApplication1 import jsmini
from js_builtins import register_builtins

def make_test_context():
    ctx = jsmini.make_context()
    # ensure built-ins are registered (jsmini.make_context may already register inline; safe to call)
    register_builtins(ctx, jsmini.JSFunction)
    return ctx

def test_array_push_pop_and_index():
    logs = []
    ctx = make_test_context()
    ctx['console'] = {'log': lambda *a: logs.append(" ".join(str(x) for x in a))}
    src = """
    var a = new Array();
    a.push(10);
    a.push(20);
    console.log("len", a.length);
    console.log("idx0", a[0]);
    var p = a.pop();
    console.log("popped", p);
    """
    jsmini.run(src, ctx)
    assert "len 2" in logs[0]
    assert "idx0 10" in logs[1]
    assert "popped 20" in logs[2]

def test_array_map_filter_concat():
    logs = []
    ctx = make_test_context()
    ctx['console'] = {'log': lambda *a: logs.append(" ".join(str(x) for x in a))}
    src = """
    var a = new Array();
    a.push(1); a.push(2); a.push(3);
    var m = a.map(function(x){ return x * 2; });
    console.log("maplen", m.length);
    var f = a.filter(function(x){ return x % 2 == 1; });
    console.log("filterlen", f.length);
    var c = a.concat([4,5], 6);
    console.log("concatlen", c.length);
    """
    jsmini.run(src, ctx)
    assert any("maplen" in s and "3" in s for s in logs)
    assert any("filterlen" in s and "2" in s for s in logs)
    assert any("concatlen" in s and "6" in s for s in logs)

def test_function_call_apply_bind():
    logs = []
    ctx = make_test_context()
    ctx['console'] = {'log': lambda *a: logs.append(" ".join(str(x) for x in a))}
    src = """
    function f(a,b){ return (this && this.v ? this.v : 0) + a + b; }
    var o = { v: 5 };
    console.log("call", f.call(o, 2, 3));
    console.log("apply", f.apply(o, [2,3]));
    var g = f.bind(o, 2);
    console.log("bind", g(3));
    """
    jsmini.run(src, ctx)
    assert any("call 10" in s for s in logs)
    assert any("apply 10" in s for s in logs)
    assert any("bind 10" in s for s in logs)