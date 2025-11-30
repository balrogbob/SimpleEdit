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
import json
import importlib
import math

def register_builtins(context: Dict[str, Any], JSFunction):
    # --- Host environment shims (conservative, inert defaults) ---
    # Provide aliases and minimal google_tag* structures so real-world tag code
    # probing these globals won't spin in tight re-check loops.
    context.setdefault('window', context)
    context.setdefault('globalThis', context)
    context.setdefault('google_tags_first_party', [])

    # Ensure google_tag_data.tidr has the minimal expected shape:
    #   google_tag_data = { 'tidr': { 'container': {}, 'injectedFirstPartyContainers': {} } }
    gtd = context.setdefault('google_tag_data', {})
    tidr = gtd.setdefault('tidr', {})
    tidr.setdefault('container', {})
    tidr.setdefault('injectedFirstPartyContainers', {})

    # Ensure timer containers used by setTimeout/setInterval exist on context
    context.setdefault('_timers', [])
    # Store active intervals and next timer id on context so run_timers_from_context
    # (in jsmini.py) can access them.
    context.setdefault('_intervals', {})
    context.setdefault('_next_timer_id', 1)

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

    # Minimal localStorage (string keys/values)
    _store: Dict[str, str] = {}

    def _ls_get_item(interp, this, args):
        k = str(args[0]) if args else None
        return _store.get(k, None)

    def _ls_set_item(interp, this, args):
        if len(args) >= 2:
            try:
                _store[str(args[0])] = str(args[1])
            except Exception:
                pass
        return None

    def _ls_remove_item(interp, this, args):
        if args:
            try:
                _store.pop(str(args[0]), None)
            except Exception:
                pass
        return None

    def _ls_clear(interp, this, args):
        _store.clear()
        return None

    context.setdefault('localStorage', {
        'getItem': JSFunction([], None, None, name='getItem', native_impl=_ls_get_item),
        'setItem': JSFunction([], None, None, name='setItem', native_impl=_ls_set_item),
        'removeItem': JSFunction([], None, None, name='removeItem', native_impl=_ls_remove_item),
        'clear': JSFunction([], None, None, name='clear', native_impl=_ls_clear),
    })

    # setInterval/clearInterval using context['_timers'] and context['_intervals']
    def _set_interval(interp, this, args):
        """
        setInterval(fn, delay, ...args) -> id
        - stores active interval in context['_intervals'] (fn, args_tuple)
        - enqueues a marker ('__interval__', id) into context['_timers'] so runner will call it
        """
        try:
            fn = args[0] if args else None
            # additional args to pass to callback when invoked
            extra_args = tuple(args[2:]) if len(args) > 2 else ()
        except Exception:
            fn = None
            extra_args = ()

        # allocate id on context so run_timers can see it
        try:
            tid = int(context.get('_next_timer_id', 1))
        except Exception:
            tid = 1
        try:
            context['_next_timer_id'] = tid + 1
        except Exception:
            # best-effort: ignore if cannot write
            pass

        try:
            context['_intervals'][tid] = (fn, extra_args)
        except Exception:
            # fall back to no-op if context not writable
            return None

        try:
            context['_timers'].append(('__interval__', tid))
        except Exception:
            # if timers not writable, still return id
            pass
        return tid

    def _clear_interval(interp, this, args):
        try:
            tid = int(args[0]) if args else None
        except Exception:
            tid = None
        if tid is None:
            return None
        try:
            context.get('_intervals', {}).pop(tid, None)
        except Exception:
            pass
        return None

    # Register interval functions as JSFunction instances
    context.setdefault('setInterval', JSFunction([], None, None, name='setInterval', native_impl=_set_interval))
    context.setdefault('clearInterval', JSFunction([], None, None, name='clearInterval', native_impl=_clear_interval))

    # Array prototype methods
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

    def _call_js_fn(fn, this_obj, call_args, interp):
        """Call a JSFunction defensively and return value; uses interp for lookup.
        Verbose diagnostics to track `undefined` sentinel identity and call shapes.
        """
        # small safe logger: prefer context.console.log -> fallback to print
        def _dbg(msg: str):
            try:
                c = context.get('console') if isinstance(context, dict) else None
                if isinstance(c, dict) and callable(c.get('log')):
                    try:
                        c.get('log')(msg)
                        return
                    except Exception:
                        pass
                print(msg)
            except Exception:
                try:
                    print(msg)
                except Exception:
                    pass

        try:
            # ensure context knows the interpreter (helps nested calls that expect context['_interp'])
            try:
                if isinstance(interp, dict) and interp.get('_interp') is None:
                    interp['_interp'] = interp
            except Exception:
                pass

            # Log call-site shape for diagnostics
            try:
                _dbg(f"[js_builtins] CALL: fn={getattr(fn,'name',str(fn))} this_obj={type(this_obj).__name__} id={id(this_obj)} call_args_preview={call_args[:2]}")
                # show context undefined vs module undefined
                try:
                    mod_name = getattr(interp.__class__, '__module__', None) if not isinstance(interp, dict) else None
                    module_undef = None
                    if mod_name:
                        mod = importlib.import_module(mod_name)
                        module_undef = getattr(mod, 'undefined', None)
                    ctx_undef = context.get('undefined', None)
                    _dbg(f"[js_builtins] SENTINELS: context.undefined={ctx_undef!r} id={id(ctx_undef)} module.undefined={module_undef!r} id={id(module_undef) if module_undef is not None else None}")
                except Exception:
                    pass
            except Exception:
                pass

            rv = fn.call(interp, this_obj, call_args)

            # Detailed post-call diagnostics
            try:
                # resolve interpreter sentinel for comparison
                interp_undef = _get_interp_undefined(interp)
                is_interp_undef = (rv is interp_undef)
                is_context_undef = (rv is context.get('undefined'))
                _dbg(f"[js_builtins] RETURN: fn={getattr(fn,'name',str(fn))} rv={rv!r} type={type(rv).__name__} is_interp_undef={is_interp_undef} is_context_undef={is_context_undef}")
            except Exception:
                _dbg(f"[js_builtins] RETURN: fn={getattr(fn,'name',str(fn))} rv={rv!r} (failed sentinel checks)")

            # Log surprising returns that commonly cause JSON.stringify to omit values:
            try:
                if rv is None or rv is _get_interp_undefined(interp):
                    _dbg(f"[js_builtins] _call_js_fn: fn={getattr(fn,'name',str(fn))} returned {rv!r} for args={call_args[:1]}")
            except Exception:
                pass

            return rv
        except Exception as e:
            # Log exception details then return interpreter undefined sentinel.
            try:
                _dbg(f"[js_builtins] _call_js_fn EXCEPTION: fn={getattr(fn,'name',str(fn))} args={call_args[:1]} error={e}")
            except Exception:
                pass
            return _get_interp_undefined(interp)

    def _get_interp_undefined(interp):
        # Prefer the sentinel stored on the shared context (set by make_context / run).
        try:
            if 'undefined' in context:
                return context['undefined']
        except Exception:
            pass
        # Fallback: attempt to locate module-level sentinel (best-effort)
        try:
            mod_name = getattr(interp.__class__, '__module__', None)
            if mod_name:
                mod = importlib.import_module(mod_name)
                return getattr(mod, 'undefined', None)
        except Exception:
            pass
        # Last-resort: None
        return None

    def _json_parse_native(interp, this, args):
        """JSON.parse(text[, reviver]) -> JS-shaped value; supports reviver.
    
        Reviver (if a JSFunction) is applied in post-order traversal:
          - Traverse object/array children first
          - Call reviver(holder, key, value) for each property/element
          - If reviver returns interpreter `undefined` sentinel -> delete the property
          - Otherwise assign the returned value
    
        Returns a JS-shaped structure (dicts for objects, array-like dicts with 'length').
        """
        s = args[0] if args else None
        reviver = args[1] if len(args) > 1 else None
        if not isinstance(s, str):
            try:
                s = str(s)
            except Exception:
                raise JSError("Invalid JSON input")
    
        try:
            py_val = json.loads(s)
        except Exception as e:
            raise JSError(str(e))
    
        # Convert Python-native json result into JS-shaped value our interpreter expects.
        def _to_js(v):
            if v is None:
                return None
            if isinstance(v, (str, bool, int, float)):
                return v
            if isinstance(v, list):
                out = {'__proto__': Arr.prototype, 'length': 0}
                for i, el in enumerate(v):
                    out[str(i)] = _to_js(el)
                out['length'] = len(v)
                return out
            if isinstance(v, dict):
                o = {}
                for k, vv in v.items():
                    o[str(k)] = _to_js(vv)
                return o
            try:
                return str(v)
            except Exception:
                return None
    
        top = _to_js(py_val)
    
        # If no reviver or reviver not callable JSFunction -> return converted structure
        if not isinstance(reviver, JSFunction):
            return top
    
        # Helper to locate interpreter undefined sentinel
        def _get_interp_undefined_local(interp_local):
            try:
                if 'undefined' in context:
                    return context['undefined']
            except Exception:
                pass
            try:
                mod_name = getattr(interp_local.__class__, '__module__', None)
                if mod_name:
                    mod = importlib.import_module(mod_name)
                    return getattr(mod, 'undefined', None)
            except Exception:
                pass
            return None
    
        # Post-order traversal per spec. `holder` is a dict-like parent; `key` is string key (or index string).
        def _walk(holder, key):
            try:
                # Obtain current value
                try:
                    val = holder.get(key)
                except Exception:
                    # If holder is not dict-like, cannot traverse further.
                    val = None
    
                # If value is an object/array-like, traverse its children first
                if isinstance(val, dict) and 'length' in val:
                    # array-like
                    try:
                        length = int(val.get('length', 0) or 0)
                    except Exception:
                        length = 0
                    for i in range(length):
                        k = str(i)
                        if k in val:
                            _walk(val, k)
                        else:
                            # holes are represented by absence; still call reviver with undefined
                            # Represent as interpreter undefined sentinel for the call
                            # create a temporary holder-like access so reviver sees undefined
                            _walk(val, k)
                elif isinstance(val, dict):
                    # object: traverse all own enumerable properties except "__proto__"
                    for k in list(val.keys()):
                        if k == "__proto__":
                            continue
                        _walk(val, k)
    
                # After children processed, call reviver for this property
                # Compose the current value (may have been modified by children)
                try:
                    cur_val = holder.get(key)
                except Exception:
                    cur_val = None
    
                # Call reviver with holder as `this`
                try:
                    res = _call_js_fn(reviver, holder, [key, cur_val], interp)
                except Exception:
                    # Propagate reviver exceptions as JSError to match prior behavior
                    raise
                # If reviver returned interpreter undefined sentinel -> delete property
                if res is _get_interp_undefined_local(interp):
                    try:
                        if key in holder:
                            del holder[key]
                    except Exception:
                        pass
                else:
                    try:
                        holder[key] = res
                    except Exception:
                        pass
            except JSError:
                # bubble up JSError
                raise
            except Exception:
                # best-effort: do not abort traversal on incidental errors
                pass
    
        # Wrapper per spec: start with a holder {"": top}
        wrapper = {"": top}
        _walk(wrapper, "")
        return wrapper[""]

    def _json_stringify_native(interp, this, args):
        """
        JSON.stringify(value, replacer=None, space=None)
        Returns JS string or JS undefined sentinel (from interpreter) when top-level omitted.
        Emits warnings when values become JSON `null` (and why) and when top-level becomes `undefined`.
        """
        val = args[0] if args else None
        replacer = args[1] if len(args) > 1 else None
        space = args[2] if len(args) > 2 else None

        UNSET = object()

        replacer_fn = replacer if isinstance(replacer, JSFunction) else None

        property_list: Optional[List[str]] = None
        try:
            if isinstance(replacer, dict) and "length" in replacer:
                prop_set = []
                try:
                    alen = int(replacer.get("length", 0) or 0)
                except Exception:
                    alen = 0
                seen = set()
                for i in range(alen):
                    k = replacer.get(str(i), None)
                    if k is None:
                        continue
                    ks = str(k)
                    if ks not in seen:
                        seen.add(ks)
                        prop_set.append(ks)
                property_list = prop_set
            elif isinstance(replacer, list):
                prop_set = []
                seen = set()
                for e in replacer:
                    ks = str(e)
                    if ks not in seen:
                        seen.add(ks)
                        prop_set.append(ks)
                property_list = prop_set
        except Exception:
            property_list = None

        indent_arg = None
        if space is not None:
            try:
                if isinstance(space, (int, float)):
                    indent_arg = max(0, min(10, int(space)))
                elif isinstance(space, str):
                    indent_arg = max(0, min(10, len(space)))
                else:
                    indent_arg = max(0, min(10, int(space)))
            except Exception:
                indent_arg = None

        # small safe logger: prefer context.console.log -> fallback to print
        def _dbg(msg: str):
            try:
                c = context.get('console') if isinstance(context, dict) else None
                if isinstance(c, dict) and callable(c.get('log')):
                    try:
                        c.get('log')(msg)
                        return
                    except Exception:
                        pass
                print(msg)
            except Exception:
                try:
                    print(msg)
                except Exception:
                    pass

        def _serialize(holder, key, value, stack, in_array=False, path=()):
            """
            holder: containing object (dict)
            key: property key string
            value: JS-shaped value (dict/list-like/primitive)
            stack: set of ids for circular detection
            in_array: whether this value is inside an array (affects undefined -> null behavior)
            path: tuple of path components for logging (root is ('',))
            returns: Python primitive / list / dict, or UNSET to indicate omitted property
            """
            # toJSON / replacer application
            try:
                # Debug: log presence/type of toJSON and incoming value for root diagnostics
                try:
                    p = '.'.join(map(str, path)) or '(root)'
                    if isinstance(value, dict):
                        _dbg(f"[js_builtins] _serialize BEFORE toJSON: path='{p}' key={key!r} value_keys={list(value.keys())}")
                    else:
                        _dbg(f"[js_builtins] _serialize BEFORE toJSON: path='{p}' key={key!r} value_type={type(value).__name__} value={value!r}")
                except Exception:
                    pass
                if isinstance(value, dict):
                    tojson = value.get("toJSON", None)
                    if isinstance(tojson, JSFunction):
                        # call toJSON and log the raw returned value for diagnosis
                        ret = _call_js_fn(tojson, value, [key], interp)
                        try:
                            _dbg(f"[js_builtins] toJSON called at path='{p}' returned: {ret!r} (type={type(ret).__name__})")
                        except Exception:
                            pass
                        value = ret
                if replacer_fn:
                    value = _call_js_fn(replacer_fn, holder, [key, value], interp)
            except JSError:
                raise
            except Exception:
                # replacer/toJSON unexpected error -> treat as interpreter undefined
                value = _get_interp_undefined(interp)

            # If interpreter undefined sentinel -> omitted in object, null in array
            if value is _get_interp_undefined(interp):
                p = '.'.join(map(str, path)) or '(root)'
                if in_array:
                    _dbg(f"[js_builtins] JSON.stringify: null at path '{p}' (replacer/toJSON returned undefined or threw)")
                    return None
                else:
                    _dbg(f"[js_builtins] JSON.stringify: property omitted at path '{p}' (replacer/toJSON returned undefined or threw)")
                    return UNSET

            # JS null -> Python None -> JSON null
            if value is None:
                p = '.'.join(map(str, path)) or '(root)'
                _dbg(f"[js_builtins] JSON.stringify: null at path '{p}' (JS null)")
                return None

            # Boolean
            if isinstance(value, bool):
                return value

            if isinstance(value, (int, float)):
                try:
                    # normalize to float for consistent behavior
                    fv = float(value)
                    # Debug: show numeric value/type observed
                    try:
                        _dbg(f"[js_builtins] numeric value at path '{p}': {fv!r} (type={type(value).__name__})")
                    except Exception:
                        pass
                    # NaN/Infinity become JSON null
                    if math.isnan(fv) or math.isinf(fv):
                        p = '.'.join(map(str, path)) or '(root)'
                        _dbg(f"[js_builtins] JSON.stringify: null at path '{p}' (NaN or Infinity coerced to null)")
                        return None
                    # normalize -0.0 -> 0
                    if fv == 0.0:
                        return 0
                    # return numeric value (use float to avoid unexpected host-object wrappers)
                    return fv
                except Exception:
                    # If converting to float fails, treat as JSON null (best-effort)
                    return None

            # String
            if isinstance(value, str):
                return value

            # Functions -> undefined (omitted in object, null in array)
            if isinstance(value, JSFunction) or callable(value):
                p = '.'.join(map(str, path)) or '(root)'
                if in_array:
                    _dbg(f"[js_builtins] JSON.stringify: null at path '{p}' (function in array -> null)")
                    return None
                else:
                    _dbg(f"[js_builtins] JSON.stringify: property omitted at path '{p}' (function -> undefined)")
                    return UNSET

            # Array-like detection (dict with 'length')
            if isinstance(value, dict) and "length" in value:
                try:
                    length = int(value.get("length", 0) or 0)
                except Exception:
                    length = 0
                vid = id(value)
                if vid in stack:
                    raise JSError("Converting circular structure to JSON")
                stack.add(vid)
                out_list = []
                for i in range(length):
                    k = str(i)
                    child_path = tuple(list(path) + [i])
                    if k in value:
                        pv = _serialize(value, k, value.get(k), stack, in_array=True, path=child_path)
                        out_list.append(None if pv is UNSET else pv)
                    else:
                        # hole -> null
                        _dbg(f"[js_builtins] JSON.stringify: null at path '{'.'.join(map(str, child_path))}' (array hole -> null)")
                        out_list.append(None)
                stack.remove(vid)
                return out_list

            # Plain object
            if isinstance(value, dict):
                vid = id(value)
                if vid in stack:
                    raise JSError("Converting circular structure to JSON")
                stack.add(vid)
                obj_out = {}
                keys = property_list if property_list is not None else [k for k in value.keys() if k != "__proto__"]
                for k in keys:
                    if k == "__proto__":
                        continue
                    if k not in value:
                        continue
                    vv = value.get(k)
                    child_path = tuple(list(path) + [k])
                    pv = _serialize(value, k, vv, stack, in_array=False, path=child_path)
                    # Debug: show what serialization returned for this property
                    try:
                        _dbg(f"[js_builtins] pv for path '{'.'.join(map(str, child_path))}': {pv!r} (type={type(pv).__name__})")
                    except Exception:
                        pass                    
                    if pv is UNSET:
                        continue
                    obj_out[str(k)] = pv
                stack.remove(vid)
                return obj_out

            # Host objects -> fallback to string
            try:
                s = str(value)
                p = '.'.join(map(str, path)) or '(root)'
                _dbg(f"[js_builtins] JSON.stringify: coercing host object at path '{p}' to string")
                return s
            except Exception:
                return None

        # perform serialization
        try:
            pure = _serialize({"": val}, "", val, set(), in_array=False, path=("",))
        except JSError:
            raise
        except Exception as e:
            raise JSError(str(e))

        # top-level omitted -> return JS undefined sentinel (and log)
        if pure is UNSET:
            _dbg("[js_builtins] JSON.stringify: top-level value was omitted (replacer/toJSON returned undefined) -> returning undefined")
            return _get_interp_undefined(interp)

        # produce JSON string
        try:
            if indent_arg is None or indent_arg == 0:
                return json.dumps(pure, separators=(",", ":"), ensure_ascii=False)
            else:
                return json.dumps(pure, indent=indent_arg, ensure_ascii=False)
        except Exception as e:
            raise JSError(str(e))

    # Register under context['JSON'] as JS-callable functions (overwrite any earlier registration)
    context['JSON'] = {
        'parse': JSFunction(params=[], body=None, env=None, name='JSON.parse', native_impl=_json_parse_native),
        'stringify': JSFunction(params=[], body=None, env=None, name='JSON.stringify', native_impl=_json_stringify_native),
    }
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
    return None