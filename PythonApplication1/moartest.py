from pathlib import Path
from jsmini import parse, Interpreter, make_context
src = Path("test.txt").read_text(encoding="utf-8", errors="replace")
ast = parse(src)
ctx = make_context(log_fn=print)
interp = Interpreter(ctx)      # create interpreter with context
interp._exec_limit = 2_000_000   # raise limit
interp._trace = True             # periodic progress prints
ctx['_interp'] = interp
try:
    interp.run_ast(ast)
except Exception as e:
    print("RUN ERROR:", type(e), e)
    # print last counters and call stack if present
    print("exec_count:", getattr(interp, "_exec_count", None))
    print("call_stack:", getattr(interp, "_call_stack", None))