import pytest
from PythonApplication1 import jsmini
from js_builtins import register_builtins

def test_array_push_pop():
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
