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
import logging

# Define JSError locally to avoid circular import
class JSError(Exception):
    """Local JSError class to avoid circular import with jsmini."""
    def __init__(self, value):
        self.value = value
        super().__init__(str(value))

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
        # Defensive push: accept both dict-like JS objects and host objects.
        # Prefer dict semantics (the interpreter expects string-indexed dicts),
        # but tolerate other shapes to avoid silent failures when 'this' isn't a dict.
        try:
            if isinstance(this, dict):
                length = int(this.get("length", 0) or 0)
            else:
                # host object fallback: try attribute or mapping-like access
                try:
                    length = int(getattr(this, "length", 0) or 0)
                except Exception:
                    length = 0
            for v in args:
                if isinstance(this, dict):
                    this[str(length)] = v
                else:
                    # try attribute assignment; best-effort (not ideal for JS semantics,
                    # but prevents native_impl from raising and leaving ops half-done)
                    try:
                        setattr(this, str(length), v)
                    except Exception:
                        try:
                            # try mapping-like setitem
                            this[str(length)] = v
                        except Exception:
                            pass
                length += 1
            if isinstance(this, dict):
                this["length"] = length
            else:
                try:
                    setattr(this, "length", length)
                except Exception:
                    try:
                        this["length"] = length
                    except Exception:
                        pass
            return length
        except Exception:
            # On any error, fail-safe: return interpreter undefined sentinel if available
            try:
                return context.get("undefined")
            except Exception:
                return None

    def _array_pop(interp, this, args):
        # Defensive pop: mirror _array_push fallback behavior.
        try:
            if isinstance(this, dict):
                length = int(this.get("length", 0) or 0)
            else:
                try:
                    length = int(getattr(this, "length", 0) or 0)
                except Exception:
                    length = 0
            if length == 0:
                return context.get("undefined")
            idx = length - 1
            key = str(idx)
            if isinstance(this, dict):
                val = this.get(key, context.get("undefined"))
                if key in this:
                    try:
                        del this[key]
                    except Exception:
                        # best-effort
                        pass
                this["length"] = idx
                return val
            else:
                # host object fallback
                try:
                    # try mapping-like access first
                    val = this.get(key, context.get("undefined")) if hasattr(this, "get") else getattr(this, key, context.get("undefined"))
                except Exception:
                    try:
                        val = getattr(this, key)
                    except Exception:
                        try:
                            val = this[str(idx)]
                        except Exception:
                            val = context.get("undefined")
                try:
                    # attempt removal by attribute or mapping deletion
                    if hasattr(this, "__delitem__"):
                        try:
                            del this[key]
                        except Exception:
                            pass
                    else:
                        try:
                            delattr(this, key)
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    if hasattr(this, "__setattr__"):
                        try:
                            setattr(this, "length", idx)
                        except Exception:
                            pass
                    else:
                        try:
                            this["length"] = idx
                        except Exception:
                            pass
                except Exception:
                    pass
                return val
        except Exception:
            return context.get("undefined")

    def _array_for_each(interp, this, args):
        """Array.prototype.forEach with stack depth guard."""
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
            
            # Guard against deep recursion before callback
            if isinstance(cb, JSFunction):
                try:
                    call_depth = len(getattr(interp, '_call_stack', []))
                    if call_depth > 500:  # Conservative limit
                        raise RuntimeError(f"Array.forEach callback stack overflow (depth={call_depth})")
                except AttributeError:
                    pass
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
        """Array.prototype.map with stack depth guard."""
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
                # Skip holes in sparse arrays
                continue
            val = this.get(key)
            
            # Guard against deep recursion before callback
            if isinstance(cb, JSFunction):
                try:
                    call_depth = len(getattr(interp, '_call_stack', []))
                    if call_depth > 500:
                        raise RuntimeError(f"Array.map callback stack overflow (depth={call_depth})")
                except AttributeError:
                    pass
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
        """Array.prototype.filter with stack depth guard."""
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
            
            # Guard against deep recursion before callback
            if isinstance(cb, JSFunction):
                try:
                    call_depth = len(getattr(interp, '_call_stack', []))
                    if call_depth > 500:
                        raise RuntimeError(f"Array.filter callback stack overflow (depth={call_depth})")
                except AttributeError:
                    pass
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
    
    def _array_reduce(interp, this, args):
        """Array.prototype.reduce with stack depth guard (added for completeness)."""
        cb = args[0] if args else None
        length = int(this.get("length", 0) or 0)
        
        if not cb:
            raise JSError("TypeError: undefined is not a function")
        
        # Determine initial value
        has_initial = len(args) > 1
        if has_initial:
            accumulator = args[1]
            start_idx = 0
        else:
            # Find first non-hole element
            accumulator = context.get("undefined")
            start_idx = 0
            for i in range(length):
                key = str(i)
                if key in this:
                    accumulator = this.get(key)
                    start_idx = i + 1
                    break
            if accumulator is context.get("undefined"):
                raise JSError("TypeError: Reduce of empty array with no initial value")
        
        # Iterate and reduce
        for i in range(start_idx, length):
            key = str(i)
            if key not in this:
                continue
            val = this.get(key)
            
            # Guard against deep recursion before callback
            if isinstance(cb, JSFunction):
                try:
                    call_depth = len(getattr(interp, '_call_stack', []))
                    if call_depth > 500:
                        raise RuntimeError(f"Array.reduce callback stack overflow (depth={call_depth})")
                except AttributeError:
                    pass
                accumulator = cb.call(interp, context.get("undefined"), [accumulator, val, i, this])
            elif callable(cb):
                try:
                    accumulator = cb(accumulator, val, i, this)
                except Exception:
                    accumulator = context.get("undefined")
            else:
                raise JSError("TypeError: callback is not a function")
        
        return accumulator
    
    def _array_some(interp, this, args):
        """Array.prototype.some with stack depth guard (added for completeness)."""
        cb = args[0] if args else None
        this_arg = args[1] if len(args) > 1 else None
        length = int(this.get("length", 0) or 0)
        
        if not cb:
            return False
        
        for i in range(length):
            key = str(i)
            if key not in this:
                continue
            val = this.get(key)
            
            # Guard against deep recursion before callback
            if isinstance(cb, JSFunction):
                try:
                    call_depth = len(getattr(interp, '_call_stack', []))
                    if call_depth > 500:
                        raise RuntimeError(f"Array.some callback stack overflow (depth={call_depth})")
                except AttributeError:
                    pass
                test = cb.call(interp, this_arg, [val, i, this])
            elif callable(cb):
                try:
                    test = cb(this_arg, val, i, this) if this_arg is not None else cb(val, i, this)
                except Exception:
                    test = False
            else:
                test = False
            
            if interp._is_truthy(test):
                return True
        
        return False
    
    def _array_every(interp, this, args):
        """Array.prototype.every with stack depth guard (added for completeness)."""
        cb = args[0] if args else None
        this_arg = args[1] if len(args) > 1 else None
        length = int(this.get("length", 0) or 0)
        
        if not cb:
            return True
        
        for i in range(length):
            key = str(i)
            if key not in this:
                continue
            val = this.get(key)
            
            # Guard against deep recursion before callback
            if isinstance(cb, JSFunction):
                try:
                    call_depth = len(getattr(interp, '_call_stack', []))
                    if call_depth > 500:
                        raise RuntimeError(f"Array.every callback stack overflow (depth={call_depth})")
                except AttributeError:
                    pass
                test = cb.call(interp, this_arg, [val, i, this])
            elif callable(cb):
                try:
                    test = cb(this_arg, val, i, this) if this_arg is not None else cb(val, i, this)
                except Exception:
                    test = False
            else:
                test = False
            
            if not interp._is_truthy(test):
                return False
        
        return True
    
    def _array_find(interp, this, args):
        """Array.prototype.find with stack depth guard (added for completeness)."""
        cb = args[0] if args else None
        this_arg = args[1] if len(args) > 1 else None
        length = int(this.get("length", 0) or 0)
        
        if not cb:
            return context.get("undefined")
        
        for i in range(length):
            key = str(i)
            if key not in this:
                continue
            val = this.get(key)
            
            # Guard against deep recursion before callback
            if isinstance(cb, JSFunction):
                try:
                    call_depth = len(getattr(interp, '_call_stack', []))
                    if call_depth > 500:
                        raise RuntimeError(f"Array.find callback stack overflow (depth={call_depth})")
                except AttributeError:
                    pass
                test = cb.call(interp, this_arg, [val, i, this])
            elif callable(cb):
                try:
                    test = cb(this_arg, val, i, this) if this_arg is not None else cb(val, i, this)
                except Exception:
                    test = False
            else:
                test = False
            
            if interp._is_truthy(test):
                return val
        
        return context.get("undefined")
    
    def _array_find_index(interp, this, args):
        """Array.prototype.findIndex with stack depth guard (added for completeness)."""
        cb = args[0] if args else None
        this_arg = args[1] if len(args) > 1 else None
        length = int(this.get("length", 0) or 0)
        
        if not cb:
            return -1
        
        for i in range(length):
            key = str(i)
            if key not in this:
                continue
            val = this.get(key)
            
            # Guard against deep recursion before callback
            if isinstance(cb, JSFunction):
                try:
                    call_depth = len(getattr(interp, '_call_stack', []))
                    if call_depth > 500:
                        raise RuntimeError(f"Array.findIndex callback stack overflow (depth={call_depth})")
                except AttributeError:
                    pass
                test = cb.call(interp, this_arg, [val, i, this])
            elif callable(cb):
                try:
                    test = cb(this_arg, val, i, this) if this_arg is not None else cb(val, i, this)
                except Exception:
                    test = False
            else:
                test = False
            
            if interp._is_truthy(test):
                return i
        
        return -1

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

    # Add this to register_builtins() in js_builtins.py, after the Array.prototype methods:
    
    def _array_each_jquery_compat(interp, this, args):
        """
        jQuery-compatible .each() implementation.
        Signature: array.each(callback)
        - callback receives (index, value) (jQuery convention, REVERSED from standard forEach)
        - returns the array itself (for chaining)
        """
        cb = args[0] if args else None
        if not cb:
            return this
        
        length = int(this.get("length", 0) or 0)
        for i in range(length):
            key = str(i)
            if key not in this:
                continue
            val = this.get(key)
            
            # jQuery convention: callback(index, value) - REVERSED!
            if isinstance(cb, JSFunction):
                try:
                    # Break on false return (jQuery .each() stops iteration if callback returns false)
                    result = cb.call(interp, val, [i, val])  # this=element, args=[index, value]
                    if result is False:  # Explicit False breaks iteration
                        break
                except Exception:
                    pass
            elif callable(cb):
                try:
                    result = cb(i, val)
                    if result is False:
                        break
                except Exception:
                    pass
        
        return this  # Return array for chaining
    
    # Register it on Array.prototype

    # Create constructor and attach ALL prototype methods (replace existing block)
    Arr = JSFunction(params=[], body=None, env=None, name="Array", native_impl=_array_ctor)
    Arr.prototype["each"] = JSFunction(params=[], body=None, env=None, name="each", native_impl=_array_each_jquery_compat)
    # Mutating methods
    Arr.prototype["push"] = JSFunction(params=[], body=None, env=None, name="push", native_impl=_array_push)
    Arr.prototype["pop"] = JSFunction(params=[], body=None, env=None, name="pop", native_impl=_array_pop)
    Arr.prototype["splice"] = JSFunction(params=[], body=None, env=None, name="splice", native_impl=_array_splice)
    
    # Iteration methods (with stack guards)
    Arr.prototype["forEach"] = JSFunction(params=[], body=None, env=None, name="forEach", native_impl=_array_for_each)
    Arr.prototype["map"] = JSFunction(params=[], body=None, env=None, name="map", native_impl=_array_map)
    Arr.prototype["filter"] = JSFunction(params=[], body=None, env=None, name="filter", native_impl=_array_filter)
    Arr.prototype["reduce"] = JSFunction(params=[], body=None, env=None, name="reduce", native_impl=_array_reduce)
    Arr.prototype["some"] = JSFunction(params=[], body=None, env=None, name="some", native_impl=_array_some)
    Arr.prototype["every"] = JSFunction(params=[], body=None, env=None, name="every", native_impl=_array_every)
    Arr.prototype["find"] = JSFunction(params=[], body=None, env=None, name="find", native_impl=_array_find)
    Arr.prototype["findIndex"] = JSFunction(params=[], body=None, env=None, name="findIndex", native_impl=_array_find_index)
    
    # Non-mutating methods
    Arr.prototype["slice"] = JSFunction(params=[], body=None, env=None, name="slice", native_impl=_array_slice)
    Arr.prototype["concat"] = JSFunction(params=[], body=None, env=None, name="concat", native_impl=_array_concat)
    Arr.prototype["indexOf"] = JSFunction(params=[], body=None, env=None, name="indexOf", native_impl=_array_index_of)
    
    # Expose constructor
    context["Array"] = Arr

    def _jquery_static_each(interp, this, args):
        """
        jQuery.each(obj, callback) - static utility function
        **CRITICAL: This must NOT call jQuery.each recursively!**
        - Iterates over arrays (by index) or objects (by key)
        - Callback signature: callback.call(value, index_or_key, value)
        - Returns false to break iteration
        - Returns the collection (for chaining)
        """
        obj = args[0] if args else None
        callback = args[1] if len(args) > 1 else None
        
        if not obj or not callback:
            return obj
        
        # **CRITICAL FIX: Use native Python iteration, NOT jQuery.each!**
        # This prevents infinite recursion when jQuery's each() calls S.each(this, callback)
        
        try:
            # Array-like iteration (has 'length' property)
            if isinstance(obj, dict) and 'length' in obj:
                try:
                    length = int(obj.get('length', 0) or 0)
                except Exception:
                    length = 0
                
                # **USE PYTHON LOOP - DO NOT call any JS function that might recurse!**
                for i in range(length):
                    key = str(i)
                    if key not in obj:
                        continue
                    val = obj.get(key)
                    
                    # jQuery convention: callback.call(element, index, element)
                    if isinstance(callback, JSFunction):
                        try:
                            result = callback.call(interp, val, [i, val])
                            # Explicit false breaks iteration
                            if result is False:
                                break
                        except Exception as e:
                            # Log but don't break - match jQuery's error handling
                            print(f"[_jquery_static_each] Callback error at index {i}: {e}")
                            pass
                    elif callable(callback):
                        try:
                            result = callback(i, val)
                            if result is False:
                                break
                        except Exception:
                            pass
            
            # Object iteration (dict without 'length')
            elif isinstance(obj, dict):
                for key in list(obj.keys()):
                    if key == '__proto__':
                        continue
                    val = obj.get(key)
                    
                    if isinstance(callback, JSFunction):
                        try:
                            result = callback.call(interp, val, [key, val])
                            if result is False:
                                break
                        except Exception as e:
                            print(f"[_jquery_static_each] Callback error at key {key}: {e}")
                            pass
                    elif callable(callback):
                        try:
                            result = callback(key, val)
                            if result is False:
                                break
                        except Exception:
                            pass
        except Exception as e:
            print(f"[_jquery_static_each] Fatal error: {e}")
            pass
        
        return obj  # Return collection for chaining

    print(f"[js_builtins] Creating jQuery.each stub, id={id(_jquery_static_each)}")

    
    jquery_obj_plain = {
        'each': JSFunction(params=[], body=None, env=None, name='each', native_impl=_jquery_static_each)
    }
    # Replace the ProtectedJQuery approach with this interceptor:
    
    # Create jQuery stub WITHOUT protection
    jquery_obj_plain = {
        'each': JSFunction(params=[], body=None, env=None, name='each', native_impl=_jquery_static_each)
    }
    
    # Register it directly (no protection wrapper)
    context['jQuery'] = jquery_obj_plain
    context['$'] = jquery_obj_plain
    
    print(f"[js_builtins] Registered jQuery.each stub (will be replaced by jQuery's own implementation)")
    # ---- INTERNAL: safe caller that captures `context` closure ----
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

    def _call_js_fn(fn, this_obj, call_args, interp):
        """Call a JSFunction defensively and return value."""
        try:
            # Remove ALL the debug logging code - it's just noise
            rv = fn.call(interp, this_obj, call_args)
            return rv
        except RecursionError:
            # Only catch RecursionError
            raise
        # REMOVE the generic Exception handler - let exceptions propagate!
    # --- JSON.parse / stringify implementations (use _call_js_fn above) ----
    def _json_parse_native(interp, this, args):
        """JSON.parse(text[, reviver]) -> JS-shaped value; supports reviver."""
        print(f"[DEBUG _json_parse_native] interp type: {type(interp).__name__}")
        print(f"[DEBUG _json_parse_native] has _eval_stmt: {hasattr(interp, '_eval_stmt')}")
        print(f"[DEBUG _json_parse_native] args: {args}")        
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
    
        # Convert Python-native json result into JS-shaped value
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
    
        # Post-order traversal per spec
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
    
        def _walk(holder, key):
            val = holder.get(key) if isinstance(holder, dict) else None
    
            if isinstance(val, dict) and 'length' in val:
                try:
                    length = int(val.get('length', 0) or 0)
                except Exception:
                    length = 0
                for i in range(length):
                    k = str(i)
                    _walk(val, k)
            elif isinstance(val, dict):
                for k in list(val.keys()):
                    if k == "__proto__":
                        continue
                    _walk(val, k)
    
            # Re-fetch current value after children have been walked
            cur_val = holder.get(key) if isinstance(holder, dict) else None
    
            res = _call_js_fn(reviver, holder, [key, cur_val], interp)
            
            undef_sentinel = _get_interp_undefined_local(interp)
            if res is undef_sentinel:
                if isinstance(holder, dict) and key in holder:
                    del holder[key]
            else:
                if isinstance(holder, dict):
                    holder[key] = res
    
        wrapper = {"": top}
        _walk(wrapper, "")
        
        # Return the result
        if "" in wrapper:
            return wrapper[""]
        else:
            return _get_interp_undefined(interp)

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

        # small safe logger: prefer Python logging / stdout only
        def _dbg(msg: str):
            try:
                logger = logging.getLogger("js_builtins")
                if logger.handlers:
                    logger.debug(msg)
                else:
                    print(msg)
            except Exception:
                try:
                    print(msg)
                except Exception:
                    pass

        def _serialize(holder, key, value, stack, in_array=False, path=(), max_depth=100):
            """
            Serialize with depth limit to prevent runaway recursion.
            max_depth: Maximum nesting depth (default 100).
            """
            try:
                # Guard against excessive nesting depth
                if len(path) > max_depth:
                    raise JSError(f"JSON.stringify: Maximum nesting depth ({max_depth}) exceeded")
                
                # toJSON logic
                try:
                    if isinstance(value, dict):
                        tojson = value.get("toJSON", None)
                        if isinstance(tojson, JSFunction):
                            ret = _call_js_fn(tojson, value, [key], interp)
                            value = ret
                except Exception:
                    value = _get_interp_undefined(interp)
                
                # Replacer logic
                if replacer_fn:
                    value = _call_js_fn(replacer_fn, holder, [key, value], interp)
                
                # Check for undefined/function (omit from JSON)
                undef_check = _get_interp_undefined(interp)
                if value is undef_check or callable(value):
                    return UNSET
                
                # Array handling
                if isinstance(value, dict) and "length" in value:
                    vid = id(value)
                    if vid in stack:
                        raise JSError("Converting circular structure to JSON")
                    stack.add(vid)
                    out_list = []
                    try:
                        length = int(value.get("length", 0) or 0)
                    except Exception:
                        length = 0
                    for i in range(length):
                        k = str(i)
                        child_path = tuple(list(path) + [i])
                        if k in value:
                            pv = _serialize(value, k, value.get(k), stack, in_array=True, 
                                          path=child_path, max_depth=max_depth)
                            out_list.append(None if pv is UNSET else pv)
                        else:
                            out_list.append(None)
                    stack.remove(vid)
                    return out_list
                    
                # Object handling  
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
                        pv = _serialize(value, k, vv, stack, in_array=False, 
                                      path=child_path, max_depth=max_depth)
                        if pv is UNSET:
                            continue
                        obj_out[str(k)] = pv
                    stack.remove(vid)
                    return obj_out
                
                # Primitive handling (THIS WAS MISSING!)
                # null, boolean, number, string
                if value is None:
                    return None
                if isinstance(value, bool):
                    return value
                if isinstance(value, (int, float)):
                    # NaN and Infinity become null in JSON
                    if math.isnan(value) or math.isinf(value):
                        return None
                    return value
                if isinstance(value, str):
                    return value
                
                # Unknown type - omit
                return UNSET
                
            except JSError:
                raise
            except Exception as e:
                raise JSError(str(e))
        try:
            pure = _serialize({"": val}, "", val, set(), in_array=False, path=("",))
        except JSError:
            raise
        except Exception as e:
            raise JSError(str(e))

        if pure is UNSET:
            _dbg("[js_builtins] JSON.stringify: top-level value was omitted (replacer/toJSON returned undefined) -> returning undefined")
            return _get_interp_undefined(interp)

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
        """
        Return own enumerable property names as a JS-shaped array:
        - result is a dict with '__proto__' set to Arr.prototype and numeric string keys plus 'length'.
        - skips '__proto__' to avoid prototype-pollution mixing.
        """
        target = args[0] if args else None
        names: List[str] = []
        try:
            if isinstance(target, dict):
                # freeze keys to stable list and coerce to strings
                names = [str(k) for k in list(target.keys()) if str(k) != "__proto__"]
            elif hasattr(target, "__dict__"):
                names = [str(k) for k in vars(target).keys()]
            else:
                # best-effort: try to iterate keys() or fallback to empty
                try:
                    names = [str(k) for k in getattr(target, "keys", lambda: [])()]
                except Exception:
                    names = []
        except Exception:
            names = []

        res: Dict[str, Any] = {"__proto__": Arr.prototype, "length": 0}
        idx = 0
        for n in names:
            try:
                # always store property names as strings in the JS-shaped result
                res[str(idx)] = str(n)
            except Exception:
                # skip problematic names
                continue
            idx += 1
        res["length"] = idx
        return res

    def _object_assign(interp, this, args):
        """
        Object.assign(target, ...sources)
        Minimal, defensive implementation:
         - If target is not provided, return undefined sentinel.
         - Copies own enumerable properties from each source (dict-like) to target.
         - Skips "__proto__" to reduce prototype-pollution risk.
         - Returns the target (original object).
        """
        if not args:
            return context.get("undefined")
        target = args[0]
        if target is None or target is context.get("undefined"):
            return context.get("undefined")
        try:
            for src in args[1:]:
                if src is None or src is context.get("undefined"):
                    continue
                if isinstance(src, dict):
                    for k, v in list(src.items()):
                        if k == "__proto__":
                            continue
                        try:
                            if isinstance(target, dict):
                                target[k] = v
                            else:
                                setattr(target, k, v)
                        except Exception:
                            try:
                                target[k] = v
                            except Exception:
                                pass
                else:
                    try:
                        for k in getattr(src, "__dict__", {}).keys():
                            if k == "__proto__":
                                continue
                            try:
                                val = getattr(src, k)
                                if isinstance(target, dict):
                                    target[str(k)] = val
                                else:
                                    setattr(target, str(k), val)
                            except Exception:
                                pass
                    except Exception:
                        pass
        except Exception:
            try:
                return target
            except Exception:
                return context.get("undefined")
        return target

    def _has_own_property(interp, this, args):
        """
        Object.prototype.hasOwnProperty.call(obj, prop)
        Implemented as a native method attached to Object.prototype.
        Returns True if `this` has own property `prop` (does not walk __proto__).
        """
        prop = args[0] if args else None
        key = str(prop) if prop is not None else ''
        try:
            if isinstance(this, dict):
                return (key in this) and (key != "__proto__")
            # host object fallback: check __dict__ and attributes
            if hasattr(this, "__dict__"):
                return key in vars(this)
            return hasattr(this, key)
        except Exception:
            return False

    Obj = JSFunction(params=[], body=None, env=None, name="Object", native_impl=lambda i, t, a: t or {})
    setattr(Obj, "create", JSFunction(params=[], body=None, env=None, name="create", native_impl=_object_create))
    setattr(Obj, "keys", JSFunction(params=[], body=None, env=None, name="keys", native_impl=_object_keys))
    setattr(Obj, "assign", JSFunction(params=[], body=None, env=None, name="assign", native_impl=_object_assign))
    
    # Attach hasOwnProperty on Object.prototype so instances can call it (obj.hasOwnProperty('x'))
    try:
        Obj.prototype.setdefault("hasOwnProperty", JSFunction(params=[], body=None, env=None, name="hasOwnProperty", native_impl=_has_own_property))
    except Exception:
        # best-effort: assign directly if prototype not mapping-like
        try:
            Obj.prototype["hasOwnProperty"] = JSFunction(params=[], body=None, env=None, name="hasOwnProperty", native_impl=_has_own_property)
        except Exception:
            pass
    context["Object"] = Obj

    # --- Function.prototype.call / apply / bind ------------------------------
    def _fn_call(interp, this, args):
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

    # Attach call/apply/bind on Function.prototype
    JSFunction.prototype['call'] = JSFunction(params=[], body=None, env=None, name='call', native_impl=_fn_call)
    JSFunction.prototype['apply'] = JSFunction(params=[], body=None, env=None, name='apply', native_impl=_fn_apply)
    JSFunction.prototype['bind'] = JSFunction(params=[], body=None, env=None, name='bind', native_impl=_fn_bind)


    # --- Event constructor + prototype ------------------------------
    def _event_ctor(interp, this, args):
        """
        new Event(type) -> minimal event object
         - type: string
         - defaultPrevented: boolean
         - cancelBubble: boolean (stopPropagation flag)
         - target: set later by dispatch
         - also attach methods as own properties for robust lookup
        """
        try:
            etype = args[0] if args else ''
            try:
                etype = str(etype)
            except Exception:
                etype = ''
            this['type'] = etype
            this['defaultPrevented'] = False
            this['cancelBubble'] = False
            # Attach methods on the instance as own properties to avoid prototype lookup issues
            try:
                pd = Event.prototype.get('preventDefault')
                sp = Event.prototype.get('stopPropagation')
                if isinstance(pd, JSFunction):
                    this['preventDefault'] = pd
                if isinstance(sp, JSFunction):
                    this['stopPropagation'] = sp
            except Exception:
                pass
            # target will be injected by dispatcher (Element / document)
        except Exception:
            pass
        return this

    def _event_prevent_default(interp, this, args):
        """
        Sets defaultPrevented flag. Returns undefined (like DOM spec).
        Works for dict-backed events and host objects.
        """
        try:
            if isinstance(this, dict):
                this['defaultPrevented'] = True
            else:
                try:
                    setattr(this, 'defaultPrevented', True)
                except Exception:
                    pass
        except Exception:
            pass
        return context.get("undefined")
    
    def _event_stop_propagation(interp, this, args):
        """
        Sets cancelBubble flag. Returns undefined (like DOM spec).
        Works for dict-backed events and host objects.
        """
        try:
            if isinstance(this, dict):
                this['cancelBubble'] = True
            else:
                try:
                    setattr(this, 'cancelBubble', True)
                except Exception:
                    pass
        except Exception:
            pass
        return context.get("undefined")



    Event = JSFunction(params=[], body=None, env=None, name="Event", native_impl=_event_ctor)
    Event.prototype['preventDefault'] = JSFunction(params=[], body=None, env=None, name="preventDefault", native_impl=_event_prevent_default)
    Event.prototype['stopPropagation'] = JSFunction(params=[], body=None, env=None, name="stopPropagation", native_impl=_event_stop_propagation)
    context["Event"] = Event

    def _array_is_array(interp, this, args):
        """Array.isArray(obj) - critical for jQuery's each() to distinguish arrays from objects"""
        try:
            obj = args[0] if args else None
            # Check if object is array-like (has numeric 'length' and numeric indices)
            if isinstance(obj, dict) and 'length' in obj:
                try:
                    # Has __proto__ pointing to Array.prototype?
                    if obj.get('__proto__') is Arr.prototype:
                        return True
                    # Fallback: check for numeric indices
                    length = int(obj.get('length', 0))
                    if length == 0:
                        return True  # Empty array-like
                    # Check if first and last index exist (heuristic)
                    return '0' in obj or str(length - 1) in obj
                except Exception:
                    return False
            return False
        except Exception:
            return False
    
    # Attach isArray as static method on Array constructor
    Arr.isArray = JSFunction(params=[], body=None, env=None, name='isArray', native_impl=_array_is_array)
    
    # **ALSO: Ensure Array constructor is accessible via setattr for JS code**
    try:
        # Make sure static methods are accessible as properties
        if not hasattr(Arr, 'isArray'):
            setattr(Arr, 'isArray', Arr.isArray)
    except Exception:
        pass

    return None