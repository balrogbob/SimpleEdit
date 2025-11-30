



from jsmini import make_context, run_with_interpreter, run_timers
ctx = make_context(log_fn=print)
js = open("test/test-stringify-replacer-space.js").read()
res, interp = run_with_interpreter(js, ctx)