    # inside make_context (after context_ref creation) -- example only
    def _array_ctor(interp, this, args):
        # when called as constructor via `new Array()` the interpreter will create `this` dict and set __proto__
        # ensure length property
        this.setdefault('length', 0)
        return this

    def _array_push(this, *args):
        # this is the receiver dict; treat numeric keys as array slots
        length = int(this.get('length', 0) or 0)
        for v in args:
            this[str(length)] = v
            length += 1
        this['length'] = length
        return length

    def _array_pop(this):
        length = int(this.get('length', 0) or 0)
        if length == 0:
            return undefined
        idx = length - 1
        val = this.get(str(idx), undefined)
        if str(idx) in this:
            del this[str(idx)]
        this['length'] = idx
        return val

    Arr = JSFunction(params=[], body=None, env=None, name='Array', native_impl=_array_ctor)
    # populate prototype methods with JSFunction wrappers (native implementations)
    Arr.prototype['push'] = JSFunction(params=[], body=None, env=None, name='push', native_impl=lambda interp, this, args: _array_push(this, *args))
    Arr.prototype['pop'] = JSFunction(params=[], body=None, env=None, name='pop', native_impl=lambda interp, this, args: _array_pop(this))

    context_ref['Array'] = Arr
