"""
Minimal ES3-ish JavaScript interpreter (toy) — intended as a small, embeddable evaluator
 - for, switch, try/catch, throw, break, continue
 - new (constructor-like) semantics
 - setTimeout scheduler (simulated)
 - tiny DOM shim: document.createElement, getElementById, body.appendChild
Usage:
    from jsmini import run, run_with_interpreter, run_timers, make_context
    ctx = make_context(log_fn=print)
    result, interp = run_with_interpreter("var x=1; setTimeout(function(){ console.log('tick')}, 0);", ctx)
    run_timers(ctx)  # execute scheduled callbacks
"""
from __future__ import annotations
import re
import random
from typing import Any, Dict, List, Optional, Tuple

# --- Tokenizer --------------------------------------------------------------
Token = Tuple[str, str]  # (type, value)

TOKEN_SPEC = [
    ('NUMBER',   r'\d+(\.\d+)?'),
    ('STRING',   r'"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\''),
    ('IDENT',    r'[A-Za-z_$][A-Za-z0-9_$]*'),
    ('COMMENT',  r'//[^\n]*|/\*[\s\S]*?\*/'),            # <--- ensure comments are matched first
    # include logical operators && and || here (longer ops first)
    ('OP',       r'===|!==|==|!=|<=|>=|&&|\|\||\+\+|--|\+|-|\*|/|%|<|>|='),
    ('PUNC',     r'[(){},;\[\].:]'),
    ('SKIP',     r'[ \t\r\n]+'),
]
TOKEN_RE = re.compile('|'.join('(?P<%s>%s)' % pair for pair in TOKEN_SPEC), re.M)

def tokenize(src: str) -> List[Token]:
    """Tokenize source and include token start/end offsets for enhanced error reporting.

    Returns list of 4-tuples (type, value, start, end).
    """
    out = []
    for m in TOKEN_RE.finditer(src):
        typ = m.lastgroup
        val = m.group(0)
        start = m.start()
        end = m.end()
        if typ == 'SKIP' or typ == 'COMMENT':
            continue
        out.append((typ, val, start, end))
    out.append(('EOF', '', len(src), len(src)))
    return out

def _format_parse_error_context(src: str, err_pos: int, err_len: int = 1, window: int = 40) -> str:
    """Return a short snippet around err_pos with a caret marker and (line,col) info."""
    try:
        if not isinstance(src, str):
            src = str(src or '')
        # compute line/col
        before = src[:err_pos]
        lineno = before.count('\n') + 1
        last_nl = before.rfind('\n')
        if last_nl == -1:
            col = err_pos + 1
            line_start = 0
        else:
            col = err_pos - last_nl
            line_start = last_nl + 1
        line_end = src.find('\n', err_pos)
        if line_end == -1:
            line_end = len(src)
        line_text = src[line_start:line_end]
        # produce truncated context for very long lines (minified single-line)
        start = max(0, err_pos - window)
        end = min(len(src), err_pos + err_len + window)
        snippet = src[start:end].replace('\n', '\\n')
        # caret relative to snippet start
        caret_pos = err_pos - start
        caret_line = ' ' * caret_pos + '^' * max(1, err_len)
        return f"Line {lineno}, Col {col}\n{snippet}\n{caret_line}"
    except Exception:
        return f"(pos {err_pos})"
# --- AST nodes (simple tuples) ----------------------------------------------
# Use small node tuples like ('num', value), ('bin', op, left, right), ('var', name), etc.

# --- Parser -----------------------------------------------------------------

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.i = 0

    def peek(self):
        return self.tokens[self.i]

    def eat(self, typ: Optional[str]=None, val: Optional[str]=None):
        t, v = self.peek()
        if typ and t != typ:
            raise SyntaxError(f"Expected {typ} got {t} ({v})")
        if val and v != val:
            raise SyntaxError(f"Expected {val} got {v}")
        self.i += 1
        return (t, v)

    def match(self, typ: str, val: Optional[str]=None) -> bool:
        t, v = self.peek()
        if t != typ:
            return False
        if val is not None and v != val:
            return False
        return True

    def parse_program(self):
        stmts = []
        while not self.match('EOF'):
            stmts.append(self.parse_statement())
        return ('prog', stmts)

    def parse_statement(self):
        if self.match('PUNC',';'):
            # empty statement (just a semicolon) — consume and return explicit empty node
            self.eat('PUNC',';')
            return ('empty',)
        if self.match('IDENT','var'):
            return self.parse_var_decl()
        if self.match('IDENT','function'):
            return self.parse_function_decl()
        if self.match('PUNC','{'):
            return self.parse_block()
        if self.match('IDENT','return'):
            self.eat('IDENT','return')
            expr = self.parse_expression()
            if self.match('PUNC',';'):
                self.eat('PUNC',';')
            return ('return', expr)
        if self.match('IDENT','if'):
            return self.parse_if()
        if self.match('IDENT','while'):
            return self.parse_while()
        if self.match('IDENT','for'):
            return self.parse_for()
        if self.match('IDENT','switch'):
            return self.parse_switch()
        if self.match('IDENT','try'):
            return self.parse_try()
        if self.match('IDENT','throw'):
            return self.parse_throw()
        if self.match('IDENT','break'):
            self.eat('IDENT','break')
            if self.match('PUNC',';'): self.eat('PUNC',';')
            return ('break',)
        if self.match('IDENT','continue'):
            self.eat('IDENT','continue')
            if self.match('PUNC',';'): self.eat('PUNC',';')
            return ('continue',)
        # expression statement
        expr = self.parse_expression()
        if self.match('PUNC',';'):
            self.eat('PUNC',';')
        return ('expr', expr)

    def parse_block(self):
        self.eat('PUNC','{')
        stmts = []
        while not self.match('PUNC','}'):
            stmts.append(self.parse_statement())
        self.eat('PUNC','}')
        return ('block', stmts)

    def parse_var_decl(self):
        """Parse `var` with one-or-more declarators (e.g. `var a, b = 2, c;`)."""
        self.eat('IDENT', 'var')
        decls = []
        # one or more declarators separated by commas
        while True:
            if not self.match('IDENT'):
                raise SyntaxError("Expected identifier after 'var'")
            name = self.eat('IDENT')[1]
            init = None
            if self.match('OP', '='):
                self.eat('OP', '=')
                init = self.parse_expression()
            decls.append((name, init))
            if self.match('PUNC', ','):
                self.eat('PUNC', ',')
                continue
            break
        if self.match('PUNC', ';'):
            self.eat('PUNC', ';')
        return ('var', decls)

    def parse_function_decl(self):
        self.eat('IDENT','function')
        name = None
        if self.match('IDENT'):
            name = self.eat('IDENT')[1]
        self.eat('PUNC','(')
        params = []
        if not self.match('PUNC',')'):
            while True:
                params.append(self.eat('IDENT')[1])
                if self.match('PUNC',')'):
                    break
                self.eat('PUNC',',')
        self.eat('PUNC',')')
        body = self.parse_block()
        return ('func', name, params, body)

    def parse_if(self):
        self.eat('IDENT','if')
        self.eat('PUNC','(')
        cond = self.parse_expression()
        self.eat('PUNC',')')
        cons = self.parse_statement()
        alt = None
        if self.match('IDENT','else'):
            self.eat('IDENT','else')
            alt = self.parse_statement()
        return ('if', cond, cons, alt)

    def parse_while(self):
        self.eat('IDENT','while')
        self.eat('PUNC','(')
        cond = self.parse_expression()
        self.eat('PUNC',')')
        body = self.parse_statement()
        return ('while', cond, body)

    def parse_for(self):
        self.eat('IDENT','for')
        self.eat('PUNC','(')
        init = None
        if not self.match('PUNC',';'):
            if self.match('IDENT','var'):
                init = self.parse_var_decl()
            else:
                init = self.parse_expression()
                if self.match('PUNC',';'):
                    self.eat('PUNC',';')
        else:
            self.eat('PUNC',';')
        cond = None
        if not self.match('PUNC',';'):
            cond = self.parse_expression()
        self.eat('PUNC',';')
        post = None
        if not self.match('PUNC',')'):
            post = self.parse_expression()
        self.eat('PUNC',')')
        body = self.parse_statement()
        return ('for', init, cond, post, body)

    def parse_switch(self):
        self.eat('IDENT','switch')
        self.eat('PUNC','(')
        expr = self.parse_expression()
        self.eat('PUNC',')')
        self.eat('PUNC','{')
        cases = []
        default_block = None
        while not self.match('PUNC','}'):
            if self.match('IDENT','case'):
                self.eat('IDENT','case')
                case_expr = self.parse_expression()
                self.eat('PUNC',':')
                stmts = []
                while not (self.match('IDENT','case') or self.match('IDENT','default') or self.match('PUNC','}')):
                    stmts.append(self.parse_statement())
                cases.append((case_expr, stmts))
            elif self.match('IDENT','default'):
                self.eat('IDENT','default')
                self.eat('PUNC',':')
                stmts = []
                while not (self.match('IDENT','case') or self.match('PUNC','}') or self.match('IDENT','default')):
                    stmts.append(self.parse_statement())
                default_block = stmts
            else:
                # fallback consume
                self.parse_statement()
        self.eat('PUNC','}')
        return ('switch', expr, cases, default_block)

    def parse_try(self):
        self.eat('IDENT','try')
        try_block = self.parse_block()
        catch_name = None
        catch_block = None
        if self.match('IDENT','catch'):
            self.eat('IDENT','catch')
            self.eat('PUNC','(')
            catch_name = self.eat('IDENT')[1]
            self.eat('PUNC',')')
            catch_block = self.parse_block()
        return ('try', try_block, catch_name, catch_block)

    def parse_throw(self):
        self.eat('IDENT','throw')
        expr = self.parse_expression()
        if self.match('PUNC',';'): self.eat('PUNC',';')
        return ('throw', expr)

    # Expressions: assignment (=) lowest precedence
    def parse_expression(self):
        node = self.parse_assignment()
        return node

    def parse_assignment(self):
        left = self.parse_binary(-2)   # lowered min_prec to include ||/&&
        if self.match('OP', '='):
            self.eat('OP','=')
            right = self.parse_assignment()
            return ('assign', left, right)
        return left


    # Pratt-like binary precedence (very small table)
    # Higher number => higher precedence. Added logical OR/AND with lower precedence
    BINOPS = {
        '||': -2, '&&': -1,               # logical OR / AND (short-circuit)
        '==': 0, '!=': 0, '===': 0, '!==': 0,
        '<': 1, '>': 1, '<=': 1, '>=': 1,
        '+': 2, '-': 2,
        '*': 3, '/': 3, '%': 3,
    }

    def parse_binary(self, min_prec):
        left = self.parse_unary()
        while True:
            t,v = self.peek()
            if t == 'OP' and v in self.BINOPS and self.BINOPS[v] >= min_prec:
                prec = self.BINOPS[v]
                op = v
                self.eat('OP',v)
                right = self.parse_binary(prec+1)
                left = ('bin', op, left, right)
            else:
                break
        return left

    def parse_unary(self):
        # support prefix unary operators including ++ and --
        if self.match('OP','-'):
            self.eat('OP','-')
            node = self.parse_unary()
            return ('unary','-', node)
        if self.match('OP','++'):
            self.eat('OP','++')
            node = self.parse_unary()
            return ('preop','++', node)
        if self.match('OP','--'):
            self.eat('OP','--')
            node = self.parse_unary()
            return ('preop','--', node)
        # support typeof as a unary operator
        if self.match('IDENT','typeof'):
            self.eat('IDENT','typeof')
            node = self.parse_unary()
            return ('typeof', node)
        if self.match('IDENT','new'):
            self.eat('IDENT','new')
            # parse a call/member expression after new (may include args)
            node = self.parse_call_member()
            return ('new', node)
        return self.parse_call_member()

    def parse_call_member(self):
        node = self.parse_primary()
        while True:
            if self.match('PUNC','('):
                # call
                self.eat('PUNC','(')
                args = []
                if not self.match('PUNC',')'):
                    while True:
                        args.append(self.parse_expression())
                        if self.match('PUNC',')'):
                            break
                        self.eat('PUNC',',')
                self.eat('PUNC',')')
                node = ('call', node, args)
                continue
            if self.match('PUNC','.'):
                self.eat('PUNC','.')
                prop = self.eat('IDENT')[1]
                node = ('get', node, ('id', prop))
                continue
            if self.match('PUNC','['):
                self.eat('PUNC','[')
                idx = self.parse_expression()
                self.eat('PUNC',']')
                node = ('get', node, idx)
                continue
            # postfix ++ / --
            if self.match('OP','++'):
                self.eat('OP','++')
                node = ('postop','++', node)
                continue
            if self.match('OP','--'):
                self.eat('OP','--')
                node = ('postop','--', node)
                continue
            break
        return node

    def parse_primary(self):
        t, v = self.peek()
        if t == 'NUMBER':
            self.eat('NUMBER')
            return ('num', float(v))
        if t == 'STRING':
            self.eat('STRING')
            s = v[1:-1]
            s = s.encode('utf-8').decode('unicode_escape')
            return ('str', s)
        if t == 'IDENT':
            # support function expression here (anonymous or named)
            if v == 'function':
                # consume 'function'
                self.eat('IDENT','function')
                name = None
                if self.match('IDENT'):
                    name = self.eat('IDENT')[1]
                # parameter list
                self.eat('PUNC','(')
                params = []
                if not self.match('PUNC',')'):
                    while True:
                        params.append(self.eat('IDENT')[1])
                        if self.match('PUNC',')'):
                            break
                        self.eat('PUNC',',')
                self.eat('PUNC',')')
                body = self.parse_block()
                return ('func', name, params, body)

            # keywords handled in statements; here plain identifier or boolean/null
            if v in ('true','false','null','undefined'):
                self.eat('IDENT')
                if v == 'true': return ('bool', True)
                if v == 'false': return ('bool', False)
                if v == 'null': return ('null', None)
                return ('undef', None)
            self.eat('IDENT')
            return ('id', v)
        if t == 'PUNC' and v == '(':
            self.eat('PUNC','(')
            e = self.parse_expression()
            self.eat('PUNC',')')
            return e
        if t == 'PUNC' and v == '{':
            # object literal
            self.eat('PUNC','{')
            props = []
            if not self.match('PUNC','}'):
                while True:
                    key = None
                    if self.match('STRING'):
                        key = self.eat('STRING')[1][1:-1]
                    else:
                        key = self.eat('IDENT')[1]
                    self.eat('PUNC',':')
                    val = self.parse_expression()
                    props.append((key, val))
                    if self.match('PUNC','}'):
                        break
                    self.eat('PUNC',',')
            self.eat('PUNC','}')
            return ('obj', props)
        if t == 'PUNC' and v == '[':
            self.eat('PUNC','[')
            elems = []
            if not self.match('PUNC',']'):
                while True:
                    elems.append(self.parse_expression())
                    if self.match('PUNC',']'):
                        break
                    self.eat('PUNC',',')
            self.eat('PUNC',']')
            return ('arr', elems)
        raise SyntaxError(f"Unexpected token {t} {v}")

def parse(src: str):
    """
    Parse source into AST with improved SyntaxError messages.
    - Tokenizer now returns positional info; parser instance keeps positions so
      we can map token index to source offsets on error.
    """
    # produce raw tokens with positions
    raw_toks = tokenize(src)
    # keep tokens in Parser as (type,value) for backwards-compatible parsing
    toks = [(t, v) for (t, v, s, e) in raw_toks]
    positions = [(s, e) for (t, v, s, e) in raw_toks]

    p = Parser(toks)
    # attach helper metadata for error reporting
    p._token_positions = positions
    p._src_text = src

    try:
        return p.parse_program()
    except SyntaxError as se:
        # try to locate failure token index and position
        try:
            idx = getattr(p, 'i', None)
            if idx is None:
                raise se
            # clamp idx
            if idx < 0:
                idx = 0
            if idx >= len(p._token_positions):
                idx = len(p._token_positions) - 1
            start, end = p._token_positions[idx]
            token = toks[idx] if idx < len(toks) else ('', '')
            context = _format_parse_error_context(src, start, max(1, end - start))
            # augment message with token info + snippet
            msg = f"SyntaxError at token #{idx} {token!r}: {se}\n{context}"
            raise SyntaxError(msg) from se
        except Exception:
            # fallback: re-raise original
            raise

# --- Runtime / evaluator ---------------------------------------------------
class Undefined:
    def __repr__(self):
        return "undefined"
undefined = Undefined()

class JSError(Exception):
    def __init__(self, value):
        self.value = value

class BreakExc(Exception):
    pass

class ContinueExc(Exception):
    pass

class Env:
    def __init__(self, parent: Optional['Env']=None):
        self.vars: Dict[str, Any] = {}
        self.parent = parent

    def get(self, name: str):
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.get(name)
        raise NameError(name)

    def set_local(self, name: str, value: Any):
        self.vars[name] = value

    def set(self, name: str, value: Any):
        # set on nearest environment that already has the name, otherwise local
        if name in self.vars:
            self.vars[name] = value
            return
        if self.parent:
            try:
                self.parent.get(name)
                self.parent.set(name, value)
                return
            except NameError:
                pass
        self.vars[name] = value

class JSFunction:
    def __init__(self, params, body, env: Env, name: Optional[str]=None):
        self.params = params
        self.body = body
        self.env = env
        self.name = name

    def call(self, interpreter, this, args):
        local = Env(self.env)
        # params
        for i, p in enumerate(self.params):
            local.set_local(p, args[i] if i < len(args) else undefined)
        # function name binding (for recursion)
        if self.name:
            local.set_local(self.name, self)
        try:
            return interpreter._eval_stmt(self.body, local, this)
        except ReturnExc as r:
            return r.value
    def __repr__(self):
        return f"<JSFunction {self.name or '<anon>'}>"

class ReturnExc(Exception):
    def __init__(self, value):
        self.value = value

class Interpreter:
    def __init__(self, globals_map: Optional[Dict[str, Any]]=None):
        self.global_env = Env()
        if globals_map:
            for k,v in globals_map.items():
                self.global_env.set_local(k, v)

    def run_ast(self, ast):
        return self._eval_prog(ast, self.global_env)

    def _eval_prog(self, node, env):
        assert node[0] == 'prog'
        res = undefined
        for st in node[1]:
            res = self._eval_stmt(st, env, None)
        return res

    def _eval_stmt(self, node, env: Env, this):
        typ = node[0]
        if typ == 'empty':
            return undefined
        if typ == 'var':
            # support multiple declarators: node format ('var', [(name, init), ...])
            _, decls = node
            last_val = undefined
            try:
                for name, init in decls:
                    val = undefined if init is None else self._eval_expr(init, env, this)
                    env.set_local(name, val)
                    last_val = val
            except Exception:
                # best-effort: if any declarator evaluation fails, leave previous ones intact
                pass
            return last_val
        if typ == 'func':
            _, name, params, body = node
            fn = JSFunction(params, body, env, name)
            if name:
                env.set_local(name, fn)
            return fn
        if typ == 'block':
            _, stmts = node
            local = Env(env)
            res = undefined
            for s in stmts:
                res = self._eval_stmt(s, local, this)
            return res
        if typ == 'return':
            _, expr = node
            val = self._eval_expr(expr, env, this)
            raise ReturnExc(val)
        if typ == 'if':
            _, cond, cons, alt = node
            c = self._eval_expr(cond, env, this)
            if self._is_truthy(c):
                return self._eval_stmt(cons, env, this)
            elif alt:
                return self._eval_stmt(alt, env, this)
            return undefined
        if typ == 'while':
            _, cond, body = node
            res = undefined
            while self._is_truthy(self._eval_expr(cond, env, this)):
                try:
                    res = self._eval_stmt(body, env, this)
                except BreakExc:
                    break
                except ContinueExc:
                    continue
            return res
        if typ == 'for':
            _, init, cond, post, body = node
            local = Env(env)
            if init is not None:
                if isinstance(init, tuple) and init[0] == 'var':
                    self._eval_stmt(init, local, this)
                else:
                    self._eval_expr(init, local, this)
            res = undefined
            while True:
                if cond is not None and not self._is_truthy(self._eval_expr(cond, local, this)):
                    break
                try:
                    res = self._eval_stmt(body, local, this)
                except BreakExc:
                    break
                except ContinueExc:
                    # continue to post/next iter
                    pass
                if post is not None:
                    self._eval_expr(post, local, this)
            return res
        if typ == 'switch':
            _, expr, cases, default_block = node
            val = self._eval_expr(expr, env, this)
            executed = False
            try:
                for case_expr, stmts in cases:
                    cval = self._eval_expr(case_expr, env, this)
                    if cval == val or executed:
                        executed = True
                        for s in stmts:
                            self._eval_stmt(s, env, this)
                if not executed and default_block:
                    for s in default_block:
                        self._eval_stmt(s, env, this)
            except BreakExc:
                pass
            return undefined
        if typ == 'try':
            _, try_block, catch_name, catch_block = node
            try:
                return self._eval_stmt(try_block, env, this)
            except JSError as je:
                if catch_name and catch_block:
                    local = Env(env)
                    local.set_local(catch_name, je.value)
                    return self._eval_stmt(catch_block, local, this)
                raise
        if typ == 'throw':
            _, expr = node
            val = self._eval_expr(expr, env, this)
            raise JSError(val)
        if typ == 'break':
            raise BreakExc()
        if typ == 'continue':
            raise ContinueExc()
        if typ == 'expr':
            return self._eval_expr(node[1], env, this)
        raise RuntimeError(f"Unknown stmt {typ}")

    def _eval_expr(self, node, env: Env, this):
        t = node[0]
        if t == 'num': return node[1]
        if t == 'str': return node[1]
        if t == 'bool': return node[1]
        if t == 'null': return None
        if t == 'undef': return undefined

        # typeof unary
        if t == 'typeof':
            _, expr_node = node
            try:
                v = self._eval_expr(expr_node, env, this)
            except Exception:
                return 'undefined'
            # JS typeof semantics (simplified)
            if v is undefined:
                return 'undefined'
            if v is None:
                return 'object'   # typeof null === 'object'
            if isinstance(v, bool):
                return 'boolean'
            if isinstance(v, (int, float)):
                return 'number'
            if isinstance(v, str):
                return 'string'
            # functions: JSFunction or callable python callables exposed as functions
            if isinstance(v, JSFunction) or callable(v):
                return 'function'
            # arrays / dicts / objects / Element -> object
            return 'object'

        # Helpers for ++/-- handling (unchanged) ...
        def _to_number(v):
            if v is undefined or v is None:
                return 0.0
            if isinstance(v, bool):
                return 1.0 if v else 0.0
            if isinstance(v, (int, float)):
                return float(v)
            try:
                return float(v)
            except Exception:
                try:
                    return float(str(v))
                except Exception:
                    return float('nan')

        def _get_target_value(target_node):
            # identifier
            if target_node[0] == 'id':
                name = target_node[1]
                try:
                    return env.get(name)
                except NameError:
                    try:
                        return self.global_env.get(name)
                    except NameError:
                        return undefined
            # property access
            if target_node[0] == 'get':
                tgt_obj = self._eval_expr(target_node[1], env, this)
                prop_node = target_node[2]
                if prop_node[0] == 'id':
                    key = prop_node[1]
                else:
                    key = self._eval_expr(prop_node, env, this)
                try:
                    if isinstance(tgt_obj, dict):
                        return tgt_obj.get(key, undefined)
                    return getattr(tgt_obj, key, undefined)
                except Exception:
                    return undefined
            # fallback: evaluate normally
            return self._eval_expr(target_node, env, this)

        def _set_target_value(target_node, value):
            if target_node[0] == 'id':
                name = target_node[1]
                env.set(name, value)
                return True
            if target_node[0] == 'get':
                tgt_obj = self._eval_expr(target_node[1], env, this)
                prop_node = target_node[2]
                if prop_node[0] == 'id':
                    key = prop_node[1]
                else:
                    key = self._eval_expr(prop_node, env, this)
                try:
                    if isinstance(tgt_obj, dict):
                        tgt_obj[key] = value
                    else:
                        setattr(tgt_obj, key, value)
                    return True
                except Exception:
                    return False
            return False

        # prefix ++/--
        if t == 'preop':
            _, op, target = node
            old = _get_target_value(target)
            nold = _to_number(old)
            delta = 1.0 if op == '++' else -1.0
            newv = nold + delta
            _set_target_value(target, newv)
            return newv

        # postfix ++/--
        if t == 'postop':
            _, op, target = node
            old = _get_target_value(target)
            nold = _to_number(old)
            delta = 1.0 if op == '++' else -1.0
            newv = nold + delta
            _set_target_value(target, newv)
            # Return original value (best-effort)
            return old

        # Function expression (returns a JSFunction closure)
        if t == 'func':
            _, name, params, body = node
            fn = JSFunction(params, body, env, name)
            return fn

        if t == 'id':
            name = node[1]
            try:
                return env.get(name)
            except NameError:
                # fallback global
                try:
                    return self.global_env.get(name)
                except NameError:
                    return undefined
        if t == 'bin':
            _, op, a, b = node
            # short-circuit logical operators with JS-like truthiness and short-circuit semantics
            if op == '&&':
                lhs = self._eval_expr(a, env, this)
                if not self._is_truthy(lhs):
                    return lhs
                return self._eval_expr(b, env, this)
            if op == '||':
                lhs = self._eval_expr(a, env, this)
                if self._is_truthy(lhs):
                    return lhs
                return self._eval_expr(b, env, this)
            lhs = self._eval_expr(a, env, this)
            rhs = self._eval_expr(b, env, this)
            return self._apply_bin(op, lhs, rhs)
        if t == 'unary':
            _, op, x = node
            v = self._eval_expr(x, env, this)
            if op == '-':
                return -float(v)
        if t == 'assign':
            _, left, right = node
            r = self._eval_expr(right, env, this)
            # left can be id or get (property)
            if left[0] == 'id':
                name = left[1]
                env.set(name, r)
                return r
            if left[0] == 'get':
                target = self._eval_expr(left[1], env, this)
                prop_node = left[2]
                if prop_node[0] == 'id':
                    key = prop_node[1]
                else:
                    key = self._eval_expr(prop_node, env, this)
                try:
                    if isinstance(target, dict):
                        target[key] = r
                    else:
                        setattr(target, key, r)
                except Exception:
                    pass
                return r
            raise RuntimeError("Invalid assignment target")
        if t == 'get':
            _, target_node, prop_node = node
            obj = self._eval_expr(target_node, env, this)
            if prop_node[0] == 'id':
                key = prop_node[1]
            else:
                key = self._eval_expr(prop_node, env, this)
            try:
                if isinstance(obj, dict):
                    return obj.get(key, undefined)
                return getattr(obj, key, undefined)
            except Exception:
                return undefined
        if t == 'call':
            _, callee_node, args_nodes = node
            callee_val = self._eval_expr(callee_node, env, this)
            args = [self._eval_expr(a, env, this) for a in args_nodes]
            # builtin python-callable
            if callable(callee_val) and not isinstance(callee_val, JSFunction):
                return callee_val(*args)
            if isinstance(callee_val, JSFunction):
                return callee_val.call(self, None, args)
            return undefined
        if t == 'new':
            # node contains either ('call', callee, args) or an identifier / get node
            inner = node[1]
            args = []
            if inner[0] == 'call':
                callee_node = inner[1]
                args_nodes = inner[2]
                args = [self._eval_expr(a, env, this) for a in args_nodes]
            else:
                callee_node = inner
            ctor = self._eval_expr(callee_node, env, this)
            if isinstance(ctor, JSFunction):
                # create a naive object and call function with that as `this`
                obj = {}
                # call constructor: if returns object, use it; else use obj
                res = ctor.call(self, obj, args)
                if isinstance(res, dict) or res is not None:
                    return res
                return obj
            return undefined
        if t == 'obj':
            _, props = node
            out = {}
            for k, v in props:
                out[k] = self._eval_expr(v, env, this)
            return out
        if t == 'arr':
            _, elems = node
            return [ self._eval_expr(e, env, this) for e in elems ]
        raise RuntimeError(f"Unhandled expr {t}")

    def _apply_bin(self, op, a, b):
        if op == '+':
            return a + b
        if op == '-':
            return a - b
        if op == '*':
            return a * b
        if op == '/':
            return a / b
        if op == '%':
            return a % b
        if op in ('==','==='):
            return a == b
        if op in ('!=','!=='):
            return a != b
        if op == '<': return a < b
        if op == '>': return a > b
        if op == '<=': return a <= b
        if op == '>=': return a >= b
        return None

    def _is_truthy(self, v):
        if v is undefined or v is None: return False
        if isinstance(v, bool): return v
        if isinstance(v, (int,float)): return v != 0
        if isinstance(v, str): return v != ''
        if isinstance(v, (list, dict)): return True
        return True

# --- Tiny DOM shim helpers --------------------------------------------------
# --- Tiny DOM shim helpers --------------------------------------------------
class JSList:
    """Small wrapper that behaves like a JS Array for our shim:
    - exposes .length property
    - supports append, indexing, iteration and a Pythonic repr
    """
    def __init__(self, items: Optional[List[Any]] = None):
        self._list: List[Any] = list(items or [])

    def append(self, item: Any) -> None:
        self._list.append(item)

    def __len__(self) -> int:
        return len(self._list)

    def __repr__(self) -> str:
        return repr(self._list)

    def __getitem__(self, idx: int) -> Any:
        try:
            return self._list[idx]
        except Exception:
            return None

    def __iter__(self):
        return iter(self._list)

    @property
    def length(self) -> int:
        return len(self._list)

    def get(self, idx: int, default: Any = None) -> Any:
        if 0 <= idx < len(self._list):
            return self._list[idx]
        return default


class Element:
    def __init__(self, tag: str):
        self.tagName = tag
        self.attrs: Dict[str, Any] = {}
        # children is a JSList so JS code can read `.length`
        self.children: JSList = JSList()
        self.id: Optional[str] = None

    def setAttribute(self, k: str, v: Any) -> None:
        self.attrs[k] = v
        if k == 'id':
            self.id = v

    def appendChild(self, child: Any) -> None:
        # keep underlying storage and expose JS-like API
        self.children.append(child)

    def __repr__(self) -> str:
        return f"<Element {self.tagName} id={self.id}>"


def make_dom_shim():
    registry: Dict[str, Element] = {}
    root = Element('document')
    body = Element('body')
    root.body = body

    def createElement(tag: str) -> Element:
        return Element(tag)

    def getElementById(idv: str) -> Optional[Element]:
        # naive walk
        if body.id == idv:
            return body
        for c in body.children:
            if isinstance(c, Element) and c.id == idv:
                return c
        return None

    def append_to_body(el: Any) -> None:
        body.appendChild(el)

    # document is a dict (so document['body'] resolves to Element via dict.get in evaluator)
    document = {
        'createElement': createElement,
        'getElementById': getElementById,
        'body': body,
        'appendChild': append_to_body
    }
    return document

# --- timers / scheduler -----------------------------------------------------
def make_timers_container():
    return {'_timers': []}  # timers: list of (fn, args)

def run_timers_from_context(context: Dict[str,Any]):
    """Run queued timers stored in context['_timers'].
    Each timer may be a Python callable or a JSFunction instance (JSFunction.call requires Interpreter).
    If the interpreter instance was stored in context['_interp'], JS functions will be invoked through it.
    """
    timers = context.get('_timers') or []
    interp = context.get('_interp')
    while timers:
        fn, args = timers.pop(0)
        try:
            if isinstance(fn, JSFunction):
                if interp:
                    fn.call(interp, None, list(args or ()))
                else:
                    # no interpreter to call JSFunction - skip
                    pass
            elif callable(fn):
                fn(*list(args or ()))
        except Exception:
            pass

# --- Public helpers ---------------------------------------------------------
def make_context(log_fn=None):
    """Return a globals dict suitable for Interpreter — pass log_fn to capture console.log."""
    def _log(*args):
        s = ' '.join(str(x) for x in args)
        if log_fn:
            log_fn(s)
        else:
            print(s)
    # tiny document
    document = make_dom_shim()
    timers = []
    def setTimeout(fn, delay=0, *args):
        # store function + args; fn may be a JSFunction (from interpreter) or a python callable
        ctx_t = context_ref
        ctx_t['_timers'].append((fn, args))
        return len(ctx_t['_timers'])
    # small Math object
    Math = {
        'random': lambda: random.random(),
        'floor': lambda x: int(x)//1
    }
    # context - created mutable to allow setTimeout closure reference
    context_ref: Dict[str,Any] = {
        'console': {'log': _log},
        'Math': Math,
        'document': document,
        '_timers': [],
        'setTimeout': setTimeout
    }
    return context_ref

def run(src: str, context: Optional[Dict[str,Any]]=None):
    """Backward-compatible: Parse and execute JS source string in a fresh interpreter with given context dict."""
    ast = parse(src)
    interp = Interpreter(context or {})
    # expose interpreter on context for timers/constructors
    if context is not None:
        context['_interp'] = interp
    return interp.run_ast(ast)

def run_with_interpreter(src: str, context: Optional[Dict[str,Any]]=None):
    """Run and return (result, interpreter). Caller can later call run_timers_from_context(context)."""
    ast = parse(src)
    ctx = context or {}
    interp = Interpreter(ctx)
    ctx['_interp'] = interp
    res = interp.run_ast(ast)
    return res, interp

def run_timers(context: Dict[str,Any]):
    """Convenience wrapper to execute stored timers in given context."""
    run_timers_from_context(context)

# quick test when executed as script
if __name__ == '__main__':
    ctx = make_context()
    run("var x = 2; function f(n){ return n*3; } console.log('res', f(x));", ctx)
    # demonstration setTimeout
    run("setTimeout(function(){ console.log('delayed', 1) }, 0);", ctx)
    run_timers(ctx)