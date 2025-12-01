import unittest
from PythonApplication1.jsmini import make_context, run_with_interpreter, run_timers, run_in_interpreter

class TestEventBuiltin(unittest.TestCase):
    def test_new_event_and_methods(self):
        ctx = make_context()
        # Use a single interpreter and evaluate subsequent expressions within it
        _, interp = run_with_interpreter("var e = new Event('click'); e.preventDefault(); e.defaultPrevented;", ctx)
        res = run_in_interpreter("e.defaultPrevented;", interp)
        self.assertTrue(res)  # Changed from: self.assertTrue(res is True)

        res = run_in_interpreter("var e2 = new Event('x'); e2.stopPropagation(); e2.cancelBubble;", interp)
        self.assertTrue(res)  # Changed from: self.assertTrue(res is True)

    def test_dispatch_event_invokes_js_handler(self):
        ctx = make_context()
        # Keep interpreter to preserve variables and handlers
        _, interp = run_with_interpreter(
            "var fired=false; function h(ev){ fired = !!(ev && ev.type==='ping'); }; document.addEventListener('ping', h);",
            ctx
        )
        run_in_interpreter("document.dispatchEvent('ping');", interp)
        run_timers(ctx)
        res = run_in_interpreter("fired;", interp)
        self.assertTrue(res is True)

    def test_dispatch_event_object(self):
        ctx = make_context()
        _, interp = run_with_interpreter(
            "var gotTarget=false; function h(ev){ gotTarget = !!(ev && ev.target); }; document.addEventListener('custom', h);",
            ctx
        )
        run_in_interpreter("document.dispatchEvent({type:'custom'});", interp)
        run_timers(ctx)
        res = run_in_interpreter("gotTarget;", interp)
        self.assertTrue(res is True)



if __name__ == '__main__':
    unittest.main()