"""
Register JavaScript built-ins (Array, Object, Function helpers) for jsmini.

Usage:
    from PythonApplication1.js_builtins import register_builtins
    register_builtins(context_ref, JSFunction)

Keep implementations small, defensive and pure Python; native_impl signature:
    native_impl(interp, this, args)
where:
 - interp is Interpreter instance
 - this is the receiver (dict for JS objects created by `new`)
 - args is list of evaluated arguments
"""
from typing import Any, Dict, List, Optional


def register_builtins(context: Dict[str, Any], JSFunction):
    # --- Array constructor + prototype methods --------------------------------
    def _array_ctor(interp, this, args):
        # this is created by Interpreter.new as a dict with '__proto__' set
        this.setdefault("length", 0)
        if args:
            if len(args) == 1 and isinstance(args[0], (int, float)):
                this["length"] = int(args[0])
            else:
                push_fn = Arr.prototype.get("push")
                if isinstance(push_fn, JSFunction):
                    push_fn.call(interp, this, args)
        return this

    def _array_push(interp, this, args):
        length = int(this.get("length", 0) or 0)
        for v in args:
            this[str(length)] = v
            length += 1
        this["length"] = length
        return length

    def _array_pop(interp, this, args):
        length = int(this.get("length", 0) or 0)
        if length == 0:
            return context.get("undefined")  # prefer interpreter's undefined if present
        idx = length - 1
        key = str(idx)
        val = this.get(key, context.get("undefined"))
        if key in this:
            del this[key]
        this["length"] = idx
        return val

    def _array_for_each(interp, this, args):
        cb = args[0] if args else None
        this_arg = args[1] if len(args) > 1 else None
        if not cb:
            return context.get("undefined")
        length = int(this.get("length", 0) or 0)
        for i in range(length):
            key = str(i)
            if key not in this:
                continue
            val = this.get(key)
            if isinstance(cb, JSFunction):
                cb.call(interp, this_arg, [val, i, this])
            elif callable(cb):
                try:
                    if this_arg is not None:
                        cb(this_arg, val, i, this)
                    else:
                        cb(val, i, this)
                except Exception:
                    pass
        return context.get("undefined")

    def _array_map(interp, this, args):
        cb = args[0] if args else None
        this_arg = args[1] if len(args) > 1 else None
        length = int(this.get("length", 0) or 0)
        res: Dict[str, Any] = {"__proto__": Arr.prototype, "length": 0}
        out_index = 0
        if not cb:
            return res
        for i in range(length):
            key = str(i)
            if key not in this:
                # minimal: skip holes
                continue
            val = this.get(key)
            if isinstance(cb, JSFunction):
                rv = cb.call(interp, this_arg, [val, i, this])
            elif callable(cb):
                try:
                    rv = cb(this_arg, val, i, this) if this_arg is not None else cb(val, i, this)
                except Exception:
                    rv = context.get("undefined")
            else:
                rv = context.get("undefined")
            res[str(out_index)] = rv
            out_index += 1
        res["length"] = out_index
        return res

    def _array_filter(interp, this, args):
        cb = args[0] if args else None
        this_arg = args[1] if len(args) > 1 else None
        length = int(this.get("length", 0) or 0)
        res: Dict[str, Any] = {"__proto__": Arr.prototype, "length": 0}
        out_index = 0
        if not cb:
            return res
        for i in range(length):
            key = str(i)
            if key not in this:
                continue
            val = this.get(key)
            if isinstance(cb, JSFunction):
                test = cb.call(interp, this_arg, [val, i, this])
            elif callable(cb):
                try:
                    test = cb(this_arg, val, i, this) if this_arg is not None else cb(val, i, this)
                except Exception:
                    test = False
            else:
                test = False
            if interp._is_truthy(test):
                res[str(out_index)] = val
                out_index += 1
        res["length"] = out_index
        return res

    def _array_slice(interp, this, args):
        length = int(this.get("length", 0) or 0)
        start = int(args[0]) if args else 0
        end = int(args[1]) if len(args) > 1 else length
        if start < 0:
            start = max(length + start, 0)
        else:
            start = min(start, length)
        if end < 0:
            end = max(length + end, 0)
        else:
            end = min(end, length)
        res: Dict[str, Any] = {"__proto__": Arr.prototype, "length": 0}
        out_index = 0
        for i in range(start, max(start, end)):
            key = str(i)
            if key in this:
                res[str(out_index)] = this.get(key)
            out_index += 1
        res["length"] = out_index
        return res

    def _array_splice(interp, this, args):
        length = int(this.get("length", 0) or 0)
        if not args:
            return {"__proto__": Arr.prototype, "length": 0}
        start = int(args[0])
        if start < 0:
            start = max(length + start, 0)
        else:
            start = min(start, length)
        if len(args) == 1:
            delete_count = length - start
        else:
            delete_count = int(args[1])
            delete_count = max(0, min(delete_count, length - start))
        inserts = list(args[2:]) if len(args) > 2 else []
        removed: Dict[str, Any] = {"__proto__": Arr.prototype, "length": 0}
        rem_idx = 0
        for i in range(start, start + delete_count):
            k = str(i)
            if k in this:
                removed[str(rem_idx)] = this.get(k)
            rem_idx += 1
        removed["length"] = rem_idx
        new_obj: Dict[str, Any] = {}
        idx = 0
        for i in range(0, start):
            k = str(i)
            if k in this:
                new_obj[str(idx)] = this.get(k)
            idx += 1
        for item in inserts:
            new_obj[str(idx)] = item
            idx += 1
        for i in range(start + delete_count, length):
            k = str(i)
            if k in this:
                new_obj[str(idx)] = this.get(k)
            idx += 1
        new_obj["__proto__"] = this.get("__proto__", Arr.prototype)
        new_obj["length"] = idx
        proto = this.get("__proto__", None)
        keys = [k for k in list(this.keys()) if k != "__proto__"]
        for k in keys:
            del this[k]
        for k, v in new_obj.items():
            this[k] = v
        if proto is not None:
            this["__proto__"] = proto
        return removed

    def _array_index_of(interp, this, args):
        search = args[0] if args else None
        from_index = int(args[1]) if len(args) > 1 else 0
        length = int(this.get("length", 0) or 0)
        if from_index < 0:
            from_index = max(length + from_index, 0)
        for i in range(from_index, length):
            k = str(i)
            if k not in this:
                continue
            if this.get(k) == search:
                return i
        return -1

    def _array_concat(interp, this, args):
        res: Dict[str, Any] = {"__proto__": Arr.prototype, "length": 0}
        out_idx = 0

        def _append(val):
            nonlocal out_idx
            res[str(out_idx)] = val
            out_idx += 1

        length = int(this.get("length", 0) or 0)
        for i in range(length):
            k = str(i)
            if k in this:
                _append(this.get(k))
        for a in args:
            if isinstance(a, dict) and "length" in a:
                alen = int(a.get("length", 0) or 0)
                for j in range(alen):
                    kk = str(j)
                    if kk in a:
                        _append(a.get(kk))
            else:
                _append(a)
        res["length"] = out_idx
        return res

    # Create constructor and attach prototype methods
    Arr = JSFunction(params=[], body=None, env=None, name="Array", native_impl=_array_ctor)
    Arr.prototype["push"] = JSFunction(params=[], body=None, env=None, name="push", native_impl=_array_push)
    Arr.prototype["pop"] = JSFunction(params=[], body=None, env=None, name="pop", native_impl=_array_pop)
    Arr.prototype["forEach"] = JSFunction(params=[], body=None, env=None, name="forEach", native_impl=_array_for_each)
    Arr.prototype["map"] = JSFunction(params=[], body=None, env=None, name="map", native_impl=_array_map)
    Arr.prototype["filter"] = JSFunction(params=[], body=None, env=None, name="filter", native_impl=_array_filter)
    Arr.prototype["slice"] = JSFunction(params=[], body=None, env=None, name="slice", native_impl=_array_slice)
    Arr.prototype["splice"] = JSFunction(params=[], body=None, env=None, name="splice", native_impl=_array_splice)
    Arr.prototype["indexOf"] = JSFunction(params=[], body=None, env=None, name="indexOf", native_impl=_array_index_of)
    Arr.prototype["concat"] = JSFunction(params=[], body=None, env=None, name="concat", native_impl=_array_concat)

    # expose constructor
    context["Array"] = Arr

    # --- Object helpers ------------------------------------------------------
    def _object_create(interp, this, args):
        proto = args[0] if args else None
        return {"__proto__": proto}

    def _object_keys(interp, this, args):
        target = args[0] if args else None
        if isinstance(target, dict):
            return [k for k in target.keys() if k != "__proto__"]
        return []

    Obj = JSFunction(params=[], body=None, env=None, name="Object", native_impl=lambda i, t, a: t or {})
    setattr(Obj, "create", JSFunction(params=[], body=None, env=None, name="create", native_impl=_object_create))
    setattr(Obj, "keys", JSFunction(params=[], body=None, env=None, name="keys", native_impl=_object_keys))
    context["Object"] = Obj

    # --- Function.prototype.call / apply / bind ------------------------------
    def _fn_call(interp, this, args):
        # this is the target function when called as target.call(...)
        target = this
        if not isinstance(target, JSFunction):
            return context.get("undefined")
        this_arg = args[0] if args else None
        fn_args = list(args[1:]) if len(args) > 1 else []
        return target.call(interp, this_arg, fn_args)

    def _fn_apply(interp, this, args):
        target = this
        if not isinstance(target, JSFunction):
            return context.get("undefined")
        this_arg = args[0] if args else None
        arg_array = args[1] if len(args) > 1 else None
        real_args: List[Any] = []
        if isinstance(arg_array, dict) and "length" in arg_array:
            alen = int(arg_array.get("length", 0) or 0)
            for i in range(alen):
                real_args.append(arg_array.get(str(i), context.get("undefined")))
        elif isinstance(arg_array, list):
            real_args = list(arg_array)
        elif arg_array is None:
            real_args = []
        else:
            real_args = [arg_array]
        return target.call(interp, this_arg, real_args)

    def _fn_bind(interp, this, args):
        target = this
        if not isinstance(target, JSFunction):
            return context.get("undefined")
        bound_this = args[0] if args else None
        bound_args = list(args[1:]) if len(args) > 1 else []

        def _bound_native(interp2, this2, call_args):
            call_args = list(call_args or [])
            full_args = bound_args + call_args
            return target.call(interp2, bound_this, full_args)

        return JSFunction(params=[], body=None, env=None, name="bound", native_impl=_bound_native)

    # Attach call/apply/bind as prototype methods on JSFunction so JS `fn.call(...)` resolves
    # via prototype lookup instead of shadowing the Python method on the class.
    # These are JSFunction instances (native_impl) so interpreter will treat them as JS functions.
    JSFunction.prototype['call'] = JSFunction(params=[], body=None, env=None, name='call', native_impl=_fn_call)
    JSFunction.prototype['apply'] = JSFunction(params=[], body=None, env=None, name='apply', native_impl=_fn_apply)
    JSFunction.prototype['bind'] = JSFunction(params=[], body=None, env=None, name='bind', native_impl=_fn_bind)
    # expose helper functions if host expects them
    context.setdefault("undefined", context.get("undefined", None))
    return None