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
import logging
import re
import random
import math
import html
import sys
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple
try:
    from . import js_builtins
except ImportError:
    import js_builtins

try:
    sys.setrecursionlimit(5000)  # Allow deep recursion for complex JS
except Exception:
    pass  # Ignore if setting fails

# --- Tokenizer --------------------------------------------------------------
Token = Tuple[str, str]  # (type, value)

_LAST_INTERPRETER = None
JSFUNCTION_REGISTRY: Dict[int, str] = {}
# -- Token definitions (fixed to accept leading-dot decimals and exponents) --
TOKEN_SPEC = [
    ('NUMBER',   r'(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?'),   # accepts 1, 1.0, .1, 1., 1e3, .1e-2
    ('STRING',   r'"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\''), 
    ('IDENT',    r'[A-Za-z_$][A-Za-z0-9_$]*'),
    ('COMMENT',  r'//[^\n]*|/\*[\s\S]*?\*/'),            # ensure comments are matched first
    # longer operators first: include full set of shift / unsigned-shift and compound-assign forms
    ('OP',       r'\+=|-=|\*=|/=|%=|&=|\|=|\^=|>>>=|<<=|>>=|>>>|<<|>>|===|!==|==|!=|<=|>=|&&|\|\||\+\+|--|!|&|\^|\||~|\+|-|\*|/|%|<|>|='),
    ('PUNC',     r'[(){},;\[\].:?]'),
    ('SKIP',     r'[ \t\r\n]+'),
]
TOKEN_RE = re.compile('|'.join('(?P<%s>%s)' % pair for pair in TOKEN_SPEC), re.M)

def tokenize(src: str) -> List[Token]:
    """Tokenize source and include token start/end offsets for enhanced error reporting.

    Returns list of 4-tuples (type, value, start, end).
    Heuristic: tries to detect JS regex literals starting with '/' when context allows.
    """
    out = []
    pos = 0
    prev_type = None
    prev_val = None
    L = len(src)

    def _prev_allows_regex():
        """
        Improved heuristic for deciding whether a '/' may start a regex literal.

        Rules implemented:
        - At start of input -> allow.
        - After punctuation that can start an expression: ( { [ , ; : ? -> allow
        - After an operator token (binary or unary) -> allow
        - After certain keywords that expect an expression -> allow (return, case, throw, else,
          new, typeof, instanceof, delete, void)
        - Disallow after literal/identifier/regex where a binary operator or property access is expected.
        """
        if prev_type is None:
            return True

        # Punctuation that opens an expression context
        if prev_type == 'PUNC' and prev_val in ('(', '{', '[', ',', ';', ':', '?'):
            return True

        # Operators generally allow an expression after them (e.g. `=`, `+`, `-`, `&&`, ...)
        if prev_type == 'OP':
            return True

        # Keywords that can be followed by an expression / value
        if prev_type == 'IDENT' and prev_val in (
            'return', 'case', 'throw', 'else', 'new', 'typeof', 'instanceof', 'delete', 'void'
        ):
            return True

        # If previous token is a literal, identifier, or regex literal, a '/' is more likely division
        if prev_type in ('NUMBER', 'STRING', 'REGEX', 'IDENT'):
            return False

        # Conservative default: do not allow (safer than mis-recognizing division as regex)
        return False

    # helper regex to recognize a regex literal (no newlines inside; supports escaped slashes/classes)
    _regex_re = re.compile(
        r'/((?:\\.|(?:\[(?:\\.|[^\]\\])*\])|[^/\\\n])*)/([gimuy]*)'
    )


    while pos < L:
        m = TOKEN_RE.match(src, pos)
        if not m:
            # Build informative error with surrounding snippet and offending character info
            ch = src[pos] if pos < L else ''
            ord_ch = ord(ch) if ch else None
            window = 40
            start_snip = max(0, pos - window)
            end_snip = min(L, pos + window)
            snippet = src[start_snip:end_snip].replace('\n', '\\n')
            caret_pos = pos - start_snip
            caret_line = ' ' * caret_pos + '^'
            msg = (
                f"Illegal character {repr(ch)} (ord={ord_ch}) in input at position {pos}.\n"
                f"...{snippet}...\n   {caret_line}"
            )
            raise SyntaxError(msg)
        typ = m.lastgroup
        val = m.group(0)
        start = m.start()
        end = m.end()

        # skip whitespace / comments
        if typ == 'SKIP' or typ == 'COMMENT':
            pos = end
            continue

        # Heuristic: when we see a slash-like token, decide whether it's a regex literal.
        # TOKEN_RE may match compound operators like '/=' before we get a chance to inspect.
        # If the matched token starts with '/' and context allows a regex, try to consume a regex literal.
        if typ == 'OP' and val.startswith('/'):
            if _prev_allows_regex():
                # try to match a regex literal starting at current pos
                rm = _regex_re.match(src, pos)
                if rm:
                    lit = rm.group(0)
                    out.append(('REGEX', lit, pos, pos + len(lit)))
                    prev_type = 'REGEX'
                    prev_val = lit
                    pos += len(lit)
                    continue
            # else fall through and treat as OP ('/' or '/=' etc.)

        # fallback: normal append of token
        out.append((typ, val, start, end))
        prev_type = typ
        prev_val = val
        pos = end

    out.append(('EOF', '', L, L))
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

        # support label: statement (e.g. `label: { ... }`), avoiding reserved keywords
        if self.match('IDENT'):
            # lookahead for colon token
            if self.i + 1 < len(self.tokens):
                nt, nv = self.tokens[self.i + 1]
                if nt == 'PUNC' and nv == ':':
                    # avoid treating language keywords as labels
                    cur_ident = self.peek()[1]
                    if cur_ident not in ('var','function','return','if','while','do','for','switch','try','throw','break','continue'):
                        name = self.eat('IDENT')[1]
                        self.eat('PUNC', ':')
                        stmt = self.parse_statement()
                        return ('label', name, stmt)

        if self.match('IDENT','var'):
            return self.parse_var_decl()
        if self.match('IDENT','function'):
            return self.parse_function_decl()
        if self.match('PUNC','{'):
            return self.parse_block()
        if self.match('IDENT','return'):
            # `return` may be followed by an expression or by nothing (automatic semicolon/closing brace).
            # Treat missing expression as `undefined`.
            self.eat('IDENT','return')
            # if next token cannot start an expression (semicolon, closing brace, EOF), it's an empty return
            t, v = self.peek()
            if t == 'PUNC' and v in (';', '}', ')') or t == 'EOF':
                # optional semicolon following empty return
                if self.match('PUNC',';'):
                    self.eat('PUNC',';')
                return ('return', ('undef', None))
            # otherwise parse expression as normal
            expr = self.parse_expression()
            if self.match('PUNC',';'):
                self.eat('PUNC',';')
            return ('return', expr)
        if self.match('IDENT','if'):
            return self.parse_if()
        if self.match('IDENT','while'):
            return self.parse_while()
        if self.match('IDENT','do'):
            # do-while: `do <statement> while (<expr>);`
            self.eat('IDENT', 'do')
            body = self.parse_statement()
            # consume optional semicolon after body (common in minified code there's none)
            # require the `while` keyword and parenthesized condition
            if self.match('IDENT', 'while'):
                self.eat('IDENT', 'while')
                self.eat('PUNC', '(')
                cond = self.parse_expression()
                self.eat('PUNC', ')')
                if self.match('PUNC', ';'):
                    self.eat('PUNC', ';')
                return ('do', body, cond)
            # best-effort: if `while` missing, treat as a plain block
            return ('block', [body])
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
            # optional label after break (e.g. `break myLabel;`)
            label = None
            if self.match('IDENT'):
                label = self.eat('IDENT')[1]
            if self.match('PUNC',';'): self.eat('PUNC',';')
            return ('break', label)
        if self.match('IDENT','continue'):
            self.eat('IDENT','continue')
            label = None
            if self.match('IDENT'):
                label = self.eat('IDENT')[1]
            if self.match('PUNC',';'): self.eat('PUNC',';')
            return ('continue', label)
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
                # use parse_assignment here so comma separators in surrounding syntax are not consumed
                init = self.parse_assignment()
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

        # Handle `for (var x in obj)` and `for (x in obj)` (for-in) as a special case.
        # Otherwise fall back to classic `for (init; cond; post)` parsing.
        init = None
        # If the header is not an immediate semicolon, parse an initial clause
        if not self.match('PUNC',';'):
            # var-declaration may be the LHS of a for-in
            if self.match('IDENT','var'):
                # parse the var-decl (may consume a trailing semicolon)
                init = self.parse_var_decl()
                # if the next token is `in`, treat this as `for (var ... in right)`
                if self.match('IDENT', 'in'):
                    self.eat('IDENT', 'in')
                    right = self.parse_expression()
                    self.eat('PUNC', ')')
                    body = self.parse_statement()
                    return ('for_in', init, right, body)
            else:
                # Parse a left-hand-side candidate using parse_call_member so we don't
                # accidentally consume an `in` token as a binary operator.
                saved_i = self.i
                lhs_candidate = None
                try:
                    lhs_candidate = self.parse_call_member()
                except SyntaxError:
                    # restore on failure
                    self.i = saved_i
                    lhs_candidate = None

                # If we see `in` after a valid LHS candidate, it's a for-in form.
                if lhs_candidate is not None and self.match('IDENT', 'in'):
                    self.eat('IDENT', 'in')
                    right = self.parse_expression()
                    self.eat('PUNC', ')')
                    body = self.parse_statement()
                    return ('for_in', lhs_candidate, right, body)

                # Otherwise treat parsed content as the init expression of a normal C-style for.
                # If we restored earlier, parse a full expression now.
                if lhs_candidate is None:
                    init = self.parse_expression()
                else:
                    # parse_call_member may have consumed only a left-hand prefix (e.g. a string or id)
                    # while the full init expression continues (e.g. `"boolean" == typeof s ...`).
                    # If the next token can continue an expression, restore and parse the full expression.
                    try:
                        t, v = self.peek()
                    except Exception:
                        t, v = None, None
                    # Accept tokens that indicate the expression continues:
                    # - operator tokens (OP)
                    # - identifiers that are binary operators (e.g. 'in', 'instanceof' stored in BINOPS)
                    # - comma (',' PUNC) which is the comma operator and valid inside `for` init clause
                    if t == 'OP' or (t == 'IDENT' and v in self.BINOPS) or (t == 'PUNC' and v == ','):
                        # restore position and parse the complete expression
                        self.i = saved_i
                        init = self.parse_expression()
                    else:
                        init = lhs_candidate

                # consume required semicolon (best-effort recovery if missing)
                if self.match('PUNC', ';'):
                    self.eat('PUNC', ';')
                else:
                    self.eat('PUNC', ';')
        else:
            # empty init; consume semicolon
            self.eat('PUNC',';')

        # classic for(init; cond; post)
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

    def parse_expression(self):
        # Support comma operator: a, b  (returns last expression)
        node = self.parse_assignment()
        # comma has lowest precedence in JS expressions
        while self.match('PUNC', ','):
            self.eat('PUNC', ',')
            right = self.parse_assignment()
            node = ('comma', node, right)
        return node

    def parse_assignment(self):
        """
        Parse assignment and (new) conditional expression:
        - assignment: left = right
        - compound-assignment: left += right, left -= right, ...
        - conditional: left ? true_expr : false_expr
        """
        left = self.parse_binary(-2)   # lowered min_prec to include ||/&&

        # assignment (=) and compound assignments (+=, -=, etc.)
        if self.match('OP') and self.peek()[1] in ('=', '+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '<<=', '>>=', '>>>='):
            op = self.eat('OP')[1]
            right = self.parse_assignment()
            if op == '=':
                return ('assign', left, right)
            # desugar compound assignment `L op= R` into `L = L op R`
            # map '<<=' -> '<<', '>>>=' -> '>>>', etc.
            bin_op = op[:-1]  # removes trailing '=' -> '+='=>'+'; '<<='=>'<<'
            return ('assign', left, ('bin', bin_op, left, right))

        # conditional (ternary) operator
        if self.match('PUNC', '?'):
            self.eat('PUNC', '?')
            true_expr = self.parse_assignment()
            self.eat('PUNC', ':')
            false_expr = self.parse_assignment()
            return ('cond', left, true_expr, false_expr)

        return left

    # Pratt-like binary precedence (very small table)
    # Higher number => higher precedence.
    # Added bitwise &, ^, | with precedence near equality (conservative).
    # Also support `in` and `instanceof` (as IDENT tokens with relational precedence).
    BINOPS = {
        '||': -2, '&&': -1,               # logical OR / AND (short-circuit)
        '==': 0, '!=': 0, '===': 0, '!==': 0,
        '&': 0, '^': 0, '|': 0,            # bitwise ops (conservative precedence)
        'in': 1, 'instanceof': 1,         # relational-like operators
        '<<': 1, '>>': 1, '>>>': 1,       # shift operators (added)
        '<': 1, '>': 1, '<=': 1, '>=': 1,
        '+': 2, '-': 2,
        '*': 3, '/': 3, '%': 3,
    }

    def parse_binary(self, min_prec):
        left = self.parse_unary()
        while True:
            t, v = self.peek()
            # accept operator coming as OP or as IDENT (instanceof, in)
            if (t == 'OP' or (t == 'IDENT' and v in self.BINOPS)) and v in self.BINOPS and self.BINOPS[v] >= min_prec:
                prec = self.BINOPS[v]
                op = v
                # consume operator token with correct type
                if t == 'OP':
                    self.eat('OP', v)
                else:
                    self.eat('IDENT', v)
                right = self.parse_binary(prec + 1)
                left = ('bin', op, left, right)
            else:
                break
        return left

    def parse_unary(self):
        # support prefix unary operators including ++, --, logical-not '!' and bitwise-not '~'
        if self.match('OP','-'):
            self.eat('OP','-')
            node = self.parse_unary()
            return ('unary','-', node)
        # unary plus (e.g. +x)
        if self.match('OP','+'):
            self.eat('OP','+')
            node = self.parse_unary()
            return ('unary','+', node)
        if self.match('OP','!'):
            self.eat('OP','!')
            node = self.parse_unary()
            return ('unary','!', node)
        if self.match('OP','~'):
            self.eat('OP','~')
            node = self.parse_unary()
            return ('unary','~', node)
        if self.match('OP','++'):
            self.eat('OP','++')
            node = self.parse_unary()
            return ('preop','++', node)
        if self.match('OP','--'):
            self.eat('OP','--')
            node = self.parse_unary()
            return ('preop','--', node)
        # support `delete` as a unary operator (identifier token)
        if self.match('IDENT', 'delete'):
            self.eat('IDENT', 'delete')
            node = self.parse_unary()
            return ('delete', node)
        # support typeof as a unary operator
        if self.match('IDENT','typeof'):
            self.eat('IDENT','typeof')
            node = self.parse_unary()
            return ('typeof', node)
        # support void as a unary operator (e.g. `void 0`)
        if self.match('IDENT','void'):
            self.eat('IDENT','void')
            node = self.parse_unary()
            return ('void', node)
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
                        # use parse_assignment so argument separators (commas) remain delimiters
                        args.append(self.parse_assignment())
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
                # use parse_assignment so commas inside expressions aren't mistaken for element separators
                idx = self.parse_assignment()
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
        if t == 'REGEX':
            # regex literal token (kept as raw literal including slashes and flags)
            self.eat('REGEX')
            return ('regex', v)
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
                    # allow STRING, NUMBER or IDENT as object literal key (numbers treated as keys)
                    if self.match('STRING'):
                        key = self.eat('STRING')[1][1:-1]
                    elif self.match('NUMBER'):
                        key = self.eat('NUMBER')[1]
                    else:
                        key = self.eat('IDENT')[1]
                    self.eat('PUNC',':')
                    # use parse_assignment so the object-property separator comma is not consumed
                    val = self.parse_assignment()
                    props.append((key, val))
                    if self.match('PUNC','}'):
                        break
                    self.eat('PUNC',',')
            self.eat('PUNC','}')
            return ('obj', props)
        if t == 'PUNC' and v == '[':
            self.eat('PUNC','[')
            elems = []
            # Allow trailing commas and sparse arrays (e.g. [a, b,] and [a,,b])
            while not self.match('PUNC', ']'):
                # If comma appears immediately, record a hole (undefined) and continue
                if self.match('PUNC', ','):
                    elems.append(('undef', None))
                    self.eat('PUNC', ',')
                    continue
                # Normal element
                elems.append(self.parse_assignment())
                # If comma follows the element, consume it; allow a trailing comma before closing bracket
                if self.match('PUNC', ','):
                    self.eat('PUNC', ',')
                    if self.match('PUNC', ']'):
                        break
                    continue
                break
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
    def __init__(self, label: Optional[str] = None):
        self.label = label

class ContinueExc(Exception):
    def __init__(self, label: Optional[str] = None):
        self.label = label

class Env:
    def __init__(self, parent: Optional['Env']=None):
        self.vars: Dict[str, Any] = {}
        self.parent = parent

    def get(self, name: str):
        # Iterative lookup with cycle detection to avoid infinite recursion when
        # parent chains contain cycles (defensive).
        cur = self
        seen = set()
        while cur is not None:
            cid = id(cur)
            if cid in seen:
                # Defensive: stop and surface a clearer error instead of RecursionError.
                raise RuntimeError("Environment parent chain contains a cycle")
            seen.add(cid)
            if name in cur.vars:
                return cur.vars[name]
            cur = cur.parent
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
    # Shared class-level prototype dict so callers can set JS-level Function.prototype safely.
    prototype: Dict[str, Any] = {}

    def __init__(self, params=None, body=None, env: Optional[Env]=None, name: Optional[str]=None, native_impl: Optional[callable]=None):
        # Scripted function fields
        self.params = params or []
        self.body = body
        self.env = env
        self.name = name
        # Optional native implementation: native_impl(interpreter, this, args) -> value
        self.native_impl = native_impl
        # each function gets its own prototype object by default; fall back to class-level shared prototype
        try:
            # keep per-instance prototype but if absent, point at class prototype
            self.prototype: Dict[str, Any] = {} if not getattr(self.__class__, 'prototype', None) else self.__class__.prototype
            # ensure constructor link exists (best-effort)
            try:
                self.prototype.setdefault('constructor', self)
            except Exception:
                pass
        except Exception:
            # defensive fallback
            try:
                self.prototype = {}
                self.prototype.setdefault('constructor', self)
            except Exception:
                self.prototype = {}

        # Debugging aid: stable short descriptor for anonymous functions so logs identify the specific JSFunction object.
        try:
            body_head = None
            if isinstance(self.body, tuple) and len(self.body) > 0:
                body_head = self.body[0]
            elif self.body is None:
                body_head = 'native-body'
            else:
                body_head = str(type(self.body))
            # keep a short body snippet (repr) to help identify creation site when recursion prints
            try:
                body_snippet = repr(self.body)
                if len(body_snippet) > 200:
                    body_snippet = body_snippet[:200] + "..."
            except Exception:
                body_snippet = body_head
            self._debug_label = f"{self.name or '<anon>'}@{id(self)} params={len(self.params)} body_head={body_head}"
            # register snippet globally for quick lookup during recursion diagnostics
            try:
                JSFUNCTION_REGISTRY[id(self)] = body_snippet
            except Exception:
                pass
        except Exception:
            self._debug_label = f"{self.name or '<anon>'}@{id(self)}"

    def debug_label(self):
        """Return a compact debug label for this JSFunction instance."""
        try:
            return self._debug_label
        except Exception:
            return f"{self.name or '<anon>'}@{id(self)}"

    @staticmethod
    def _compress_call_stack(cs: List[str], max_run_display: int = 6) -> List[str]:
        """
        Compress consecutive repeated frames in a call-stack for clearer logging.
        """
        try:
            if not cs:
                return []
            out: List[str] = []
            last = cs[0]
            run = 1
            for e in cs[1:]:
                if e == last:
                    run += 1
                else:
                    if run > max_run_display:
                        out.append(f"{last} (repeated {run}x)")
                    elif run > 1:
                        out.extend([last] * run)
                    else:
                        out.append(last)
                    last = e
                    run = 1
            if run > max_run_display:
                out.append(f"{last} (repeated {run}x)")
            elif run > 1:
                out.extend([last] * run)
            else:
                out.append(last)
            return out
        except Exception:
            return cs

    def call(self, interpreter, this, args):
        """
        Invoke this JSFunction with interpreter and JS-like `this`.
        Includes a deterministic per-function recursion depth guard.
        """
        interp = interpreter
        try:
            if not hasattr(interp, '_eval_stmt'):
                if isinstance(interp, dict):
                    interp = interp.get('_interp', interp)
                if not hasattr(interp, '_eval_stmt') and isinstance(this, dict):
                    interp = this.get('_interp', interp)
        except Exception:
            pass

        # Last-resort: use module-level last interpreter
        global _LAST_INTERPRETER
        if not hasattr(interp, '_eval_stmt'):
            if _LAST_INTERPRETER is not None and hasattr(_LAST_INTERPRETER, '_eval_stmt'):
                interp = _LAST_INTERPRETER

        try:
            if not hasattr(interp, '_eval_stmt'):
                logger = logging.getLogger('jsmini')
                caller_repr = repr(interpreter)[:200]
                logger.warning("JSFunction.call received non-Interpreter interp (type=%s). Caller repr (trimmed): %s",
                               type(interpreter).__name__, caller_repr)
        except Exception:
            pass

        if not hasattr(interp, '_eval_stmt'):
            raise RuntimeError(
                f"JSFunction.call expected Interpreter instance as first arg (or context with '_interp'); got {type(interpreter)!r}"
            )

        # Deterministic per-function recursion depth guard
        fn_id = id(self)
        depth_limit = int(getattr(interp, '_per_fn_call_threshold', 0) or 0)
        try:
            cur_depth = int(getattr(interp, '_per_fn_call_depth', {}).get(fn_id, 0))
        except Exception:
            cur_depth = 0
        try:
            if not hasattr(interp, '_per_fn_call_depth'):
                interp._per_fn_call_depth = {}
            interp._per_fn_call_depth[fn_id] = cur_depth + 1
            if depth_limit and (cur_depth + 1) > depth_limit:
                try:
                    cs = list(getattr(interp, '_call_stack', []))
                    cs_comp = self._compress_call_stack(cs)
                    import sys, re
                    print(f"[jsmini.recursion] Per-function recursion depth limit hit for {self.debug_label()} (depth={cur_depth + 1}). Call stack:", file=sys.stderr)
                    for line in cs_comp[-80:]:
                        m = re.search(r'@(\d+)', line)
                        if m:
                            try:
                                fn_id_m = int(m.group(1))
                                snip = JSFUNCTION_REGISTRY.get(fn_id_m)
                                if snip:
                                    print(f"  {line} -> snippet: {snip!r}", file=sys.stderr)
                                    continue
                            except Exception:
                                pass
                        print(f"  {line}", file=sys.stderr)
                except Exception:
                    pass
                raise RuntimeError(f"Per-function recursion limit hit for {self.debug_label()} (count/depth={cur_depth + 1})")
        except RuntimeError:
            try:
                d = interp._per_fn_call_depth.get(fn_id, 1)
                if d <= 1:
                    interp._per_fn_call_depth.pop(fn_id, None)
                else:
                    interp._per_fn_call_depth[fn_id] = d - 1
            except Exception:
                pass
            raise
        except Exception:
            pass

        # Native implementation
        if self.native_impl is not None:
            try:
                try:
                    if hasattr(interp, '_per_fn_call_counts'):
                        interp._per_fn_call_counts[fn_id] = interp._per_fn_call_counts.get(fn_id, 0) + 1
                except Exception:
                    pass
                return self.native_impl(interp, this, list(args or ()))
            except ReturnExc as r:
                return r.value
            except JSError as je:
                raise je
            except Exception:
                try:
                    return getattr(interp, '_get_interp_undefined', lambda: None)()
                except Exception:
                    return None
            finally:
                # decrement depth
                try:
                    d = getattr(interp, '_per_fn_call_depth', {}).get(fn_id, 1)
                    if d <= 1:
                        interp._per_fn_call_depth.pop(fn_id, None)
                    else:
                        interp._per_fn_call_depth[fn_id] = d - 1
                except Exception:
                    pass

        # Scripted function
        local = Env(self.env)
        local.set_local('this', this)
        for i, p in enumerate(self.params):
            local.set_local(p, args[i] if i < len(args) else undefined)
        if self.name:
            local.set_local(self.name, self)

        fn_label = self.debug_label()
        try:
            if not hasattr(interp, '_call_stack'):
                interp._call_stack = []
            max_depth = getattr(interp, '_max_js_call_depth', 0)
            try:
                current_depth = len(interp._call_stack)
            except Exception:
                current_depth = 0
            if max_depth and current_depth > max_depth:
                try:
                    cs = list(interp._call_stack)
                    cs_comp = self._compress_call_stack(cs)
                    import sys, re
                    print(f"[jsmini.recursion] Deep JS call stack detected (len={len(cs)}). Top frames:", file=sys.stderr)
                    for line in cs_comp[-50:]:
                        m = re.search(r'@(\d+)', line)
                        if m:
                            try:
                                fn_id_m = int(m.group(1))
                                snip = JSFUNCTION_REGISTRY.get(fn_id_m)
                                if snip:
                                    print(f"  {line} -> snippet: {snip!r}", file=sys.stderr)
                                    continue
                            except Exception:
                                pass
                        print(f"  {line}", file=sys.stderr)
                except Exception:
                    pass
                raise RuntimeError(f"Deep JS recursion detected; call_stack (top->bottom): {getattr(interp, '_call_stack', None)}")
            interp._call_stack.append(fn_label)
        except Exception:
            pass

        try:
            try:
                try:
                    if hasattr(interp, '_per_fn_call_counts'):
                        interp._per_fn_call_counts[fn_id] = interp._per_fn_call_counts.get(fn_id, 0) + 1
                except Exception:
                    pass
                return interp._eval_stmt(self.body, local, this)
            except ReturnExc as r:
                return r.value
            except RecursionError:
                try:
                    cs = getattr(interp, '_call_stack', None) or []
                    cs_comp = self._compress_call_stack(list(cs))
                    import traceback, sys, re
                    print(f"[jsmini.recursion] RecursionError in JSFunction {self.debug_label()}; call_stack (top->bottom):", file=sys.stderr)
                    for line in cs_comp[-100:]:
                        m = re.search(r'@(\d+)', line)
                        if m:
                            try:
                                fn_id_m = int(m.group(1))
                                snip = JSFUNCTION_REGISTRY.get(fn_id_m)
                                if snip:
                                    print(f"  {line} -> snippet: {snip!r}", file=sys.stderr)
                                    continue
                            except Exception:
                                pass
                        print(f"  {line}", file=sys.stderr)
                    traceback.print_exc()
                except Exception:
                    pass
                raise
        finally:
            # pop call-stack and decrement per-function depth
            try:
                if hasattr(interp, '_call_stack') and interp._call_stack:
                    interp._call_stack.pop()
            except Exception:
                pass
            try:
                d = getattr(interp, '_per_fn_call_depth', {}).get(fn_id, 1)
                if d <= 1:
                    interp._per_fn_call_depth.pop(fn_id, None)
                else:
                    interp._per_fn_call_depth[fn_id] = d - 1
            except Exception:
                pass

    def __repr__(self):
        return f"<JSFunction {self.name or '<anon>'}>"    
class ReturnExc(Exception):
    def __init__(self, value):
        self.value = value

class Interpreter:
    def __init__(self, globals_map: Optional[Dict[str, Any]] = None):
        self.global_env = Env()
        if globals_map:
            for k, v in globals_map.items():
                self.global_env.set_local(k, v)
        self._exec_count = 0
        self._exec_limit = 200_000
        self._call_stack: List[str] = []
        self._trace = False
        self._max_js_call_depth = 2000
        self._context: Optional[Dict[str, Any]] = globals_map if isinstance(globals_map, dict) else None
        # New: per-function reentrancy guard counters
        # - _per_fn_call_counts: total calls (legacy counter kept for diagnostics)
        # - _per_fn_call_depth: current call depth per function (used to guard recursion deterministically)
        self._per_fn_call_counts: Dict[int, int] = {}
        self._per_fn_call_depth: Dict[int, int] = {}
        # Threshold at which we abort with a descriptive RuntimeError.
        # Applied to the per-function DEPTH so we stop before Python recursion blows up.
        self._per_fn_call_threshold: int = 1500  # Increased from 1200 for jQuery

        global _LAST_INTERPRETER
        try:
            _LAST_INTERPRETER = self
        except Exception:
            _LAST_INTERPRETER = None

        """Prototype-aware property lookup with cycle detection. Returns `undefined` when not found."""
    def _prop_get(self, obj, key):
        try:
            # dict-like JS objects: walk __proto__ chain with cycle detection
            if isinstance(obj, dict):
                lookup_key = self._norm_prop_key(key)
                cur = obj
                seen = set()  # Track visited object IDs to detect cycles
                
                while cur is not None:
                    obj_id = id(cur)
                    if obj_id in seen:
                        # Cycle detected in prototype chain - return undefined to break loop
                        return undefined
                    seen.add(obj_id)
                    
                    if lookup_key in cur:
                        return cur[lookup_key]
                    cur = cur.get('__proto__', None)
                return undefined
    
            # JSFunction instances: prefer prototype lookup (JS semantics)
            if isinstance(obj, JSFunction):
                try:
                    proto = getattr(obj, 'prototype', None)
                    if isinstance(proto, dict) and key in proto:
                        return proto[key]
                except Exception:
                    pass
                try:
                    cls_proto = getattr(obj.__class__, 'prototype', None)
                    if isinstance(cls_proto, dict) and key in cls_proto:
                        return cls_proto[key]
                except Exception:
                    pass
                try:
                    attr = getattr(obj, key, undefined)
                    if isinstance(attr, JSFunction):
                        return attr
                    if attr is not undefined and not callable(attr):
                        return attr
                except Exception:
                    pass
                return undefined
    
            # fallback for host/python objects
            return getattr(obj, key, undefined)
        except Exception:
            return undefined
    
    def _prop_set(self, obj, key, value):
        """Interpreter method: set own property on object (no prototype walk)."""
        try:
            if isinstance(obj, dict):
                obj[self._norm_prop_key(key)] = value
                return True
            setattr(obj, key, value)
            return True
        except Exception:
            return False
     
    def _norm_prop_key(self, key):
        """Normalize a property key to the string form used for dict-backed JS objects.
     
        JS semantics: property keys are strings. Numeric indices like 0 or 0.0 should map to "0".
        This helper:
         - converts integral floats to integer string (0.0 -> "0")
         - converts ints to string
         - converts booleans to "true"/"false"
         - returns str(key) as fallback
        """
        try:
            # interpreter's undefined sentinel -> "undefined"
            if key is undefined:
                return "undefined"
            if isinstance(key, bool):
                return "true" if key else "false"
            if isinstance(key, int):
                return str(key)
            if isinstance(key, float):
                # treat integral floats as ints (0.0 -> "0")
                try:
                    if math.isfinite(key) and float(key).is_integer():
                        return str(int(key))
                except Exception:
                    pass
                return str(key)
            return str(key)
        except Exception:
            try:
                return str(key)
            except Exception:
                return ""
     
    def run_ast(self, ast):
        return self._eval_prog(ast, self.global_env)
     
    def _eval_prog(self, node, env):
        assert node[0] == 'prog'
        res = undefined

        jquery_each_depth = getattr(self, '_jquery_each_depth', 0)

        try:
            for st in node[1]:
                res = self._eval_stmt(st, env, None)
                
                # **GUARD: Detect runaway jQuery.each recursion**
                try:
                    # Check if we're stuck in a loop calling the same function repeatedly
                    if hasattr(self, '_call_stack') and len(self._call_stack) > 100:
                        # Count consecutive identical frames
                        stack = self._call_stack[-100:]
                        if len(set(stack)) == 1:  # All frames are identical
                            # Extract function being called
                            frame = stack[0]
                            if 'each' in frame.lower():
                                raise RuntimeError(
                                    f"Detected infinite jQuery.each() recursion loop. "
                                    f"Stack has {len(stack)} identical frames: {frame}"
                                )
                except RuntimeError:
                    raise
                except Exception:
                    pass
                    
            return res
        except BreakExc:
            # Uncaught `break` bubbled out of any loop context -> provide a clear runtime error.
            raise RuntimeError("Uncaught 'break' (break statement not inside loop or switch)")
        except ContinueExc:
            # Uncaught `continue` bubbled out of any loop context -> provide a clear runtime error.
            raise RuntimeError("Uncaught 'continue' (continue statement not inside loop)")
     
    def _eval_stmt(self, node, env: Env, this):
        # lightweight execution watchdog to diagnose runaway execution/hangs.
        # Increment the interpreter-wide counter and emit a helpful error when the
        # configured execution limit is exceeded.
        try:
            self._exec_count += 1
        except Exception:
            # if attribute missing for some reason, initialize defensively
            try:
                self._exec_count = 1
            except Exception:
                pass
     
        # optional periodic trace output
        try:
            if getattr(self, '_trace', False) and (self._exec_count % 50000) == 0:
                cs = getattr(self, '_call_stack', None)
                print(f"[jsmini.trace] executed={self._exec_count} call_stack={cs}")
        except Exception:
            pass
     
        # abort with diagnostic when execution count passes configured limit
        try:
            if getattr(self, '_exec_limit', 0) and self._exec_count > self._exec_limit:
                call_stack = getattr(self, '_call_stack', None)
                raise RuntimeError(
                    f"Execution limit exceeded ({self._exec_count} statements). "
                    f"Call stack (top->bottom): {call_stack}. Current node: {node!r}"
                )
        except RuntimeError:
            raise
        except Exception:
            # ignore instrumentation failures (do not alter semantics)
            pass
     
        typ = node[0]
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
        if typ == 'label':
            # Labels don't introduce scope in this toy interpreter;
            # evaluate the inner statement and intercept labelled breaks/continues.
            _, label_name, stmt = node
            try:
                return self._eval_stmt(stmt, env, this)
            except BreakExc as be:
                # If break targets this label, it's handled here (drop out of labelled statement).
                if getattr(be, 'label', None) == label_name:
                    return undefined
                # otherwise re-raise to be handled by an outer label/loop
                raise
            except ContinueExc as ce:
                # `continue label` should target an enclosing loop labelled with label_name.
                # If we catch one here and it targets this label but the labelled statement
                # is not a loop, surface a clearer runtime error.
                if getattr(ce, 'label', None) == label_name:
                    raise RuntimeError(f"Invalid 'continue {label_name}' target (not a loop)")
                raise
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
                except BreakExc as be:
                    # handle unlabeled break; labeled breaks bubble up to enclosing labels
                    if getattr(be, 'label', None) is None:
                        break
                    raise
                except ContinueExc as ce:
                    # handle unlabeled continue; labeled continues bubble up
                    if getattr(ce, 'label', None) is None:
                        continue
                    raise
            return res
     
        # do-while loop support (handles labeled break/continue robustly)
        if typ == 'do':
            _, body, cond = node
            res = undefined
            while True:
                try:
                    res = self._eval_stmt(body, env, this)
                except BreakExc as be:
                    # only consume unlabeled breaks here
                    if getattr(be, 'label', None) is None:
                        break
                    raise
                except ContinueExc as ce:
                    # only consume unlabeled continues here (still evaluate condition)
                    if getattr(ce, 'label', None) is None:
                        pass
                    else:
                        raise
                # evaluate condition after body; break when falsy
                try:
                    if not self._is_truthy(self._eval_expr(cond, env, this)):
                        break
                except Exception:
                    break
            return res
     
        # for-in evaluator (handles labeled break/continue)
        if typ == 'for_in':
            _, lhs, rhs, body = node
            local = Env(env)
            # If lhs is a var-declaration, create the binding(s) first so RHS can see hoisted names
            if isinstance(lhs, tuple) and lhs[0] == 'var':
                try:
                    self._eval_stmt(lhs, local, this)
                except Exception:
                    pass
     
            res = undefined
            try:
                target = self._eval_expr(rhs, local, this)
            except Exception:
                target = None
     
            # Collect enumerable keys (best-effort)
            keys: List[str] = []
            try:
                if isinstance(target, dict):
                    keys = [k for k in target.keys() if k != '__proto__']
                elif isinstance(target, JSList):
                    keys = [str(i) for i in range(len(target))]
                elif isinstance(target, list):
                    keys = [str(i) for i in range(len(target))]
                elif hasattr(target, '__dict__'):
                    keys = list(vars(target).keys())
                else:
                    try:
                        seq = list(target)
                        keys = [str(i) for i in range(len(seq))]
                    except Exception:
                        keys = []
            except Exception:
                keys = []
     
            for k in keys:
                try:
                    # assign iteration variable according to lhs shape
                    if isinstance(lhs, tuple) and lhs[0] == 'var':
                        try:
                            name = lhs[1][0][0]
                            local.set(name, k)
                        except Exception:
                            pass
                    elif isinstance(lhs, tuple) and lhs[0] == 'id':
                        name = lhs[1]
                        local.set(name, k)
                    if isinstance(lhs, tuple) and lhs[0] == 'get':
                        try:
                            tgt_obj = self._eval_expr(lhs[1], local, this)
                            prop_node = lhs[2]
                            if prop_node[0] == 'id':
                                prop_name = prop_node[1]
                            else:
                                prop_name = self._eval_expr(prop_node, local, this)
                            if isinstance(tgt_obj, dict):
                                tgt_obj[self._norm_prop_key(prop_name)] = k
                            else:
                                setattr(tgt_obj, prop_name, k)
                        except Exception:
                            pass
                    # execute loop body with local env and handle labeled control flow
                    try:
                        res = self._eval_stmt(body, local, this)
                    except BreakExc as be:
                        if getattr(be, 'label', None) is None:
                            break
                        raise
                    except ContinueExc as ce:
                        if getattr(ce, 'label', None) is None:
                            continue
                        raise
                except Exception:
                    # per-iteration errors should not abort entire loop
                    continue
            return res
     
        # classic C-style for(init; cond; post)
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
                except BreakExc as be:
                    # unlabeled break stops loop; labeled break bubbles up
                    if getattr(be, 'label', None) is None:
                        break
                    raise
                except ContinueExc as ce:
                    # unlabeled continue proceeds to post; labeled continue bubbles up
                    if getattr(ce, 'label', None) is None:
                        # continue to post/next iteration
                        pass
                    else:
                        raise
                if post is not None:
                    try:
                        self._eval_expr(post, local, this)
                    except Exception:
                        # post-expression errors ignored (best-effort)
                        pass
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
            except BreakExc as be:
                # swallow unlabeled break inside switch; re-raise labeled break to be handled by an outer label
                if getattr(be, 'label', None) is None:
                    pass
                else:
                    raise
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
            # node format ('break', label_or_None)
            _, label = node
            raise BreakExc(label)
        if typ == 'continue':
            # node format ('continue', label_or_None)
            _, label = node
            raise ContinueExc(label)
        if typ == 'expr':
            return self._eval_expr(node[1], env, this)
        raise RuntimeError(f"Unknown stmt {typ}")
     
    def _eval_expr(self, node, env: Env, this):
        t = node[0]
        if t == 'num': return node[1]
        if t == 'str': return node[1]
        if t == 'regex': 
            # Return regex literal as its raw source for now (consumer may parse flags/pattern later)
            return node[1]
        if t == 'bool': return node[1]
        if t == 'null': return None
        if t == 'undef': return undefined
     
        # delete unary operator: best-effort removal of property; returns True/False like JS (non-strict)
        if t == 'delete':
            _, target_node = node
            try:
                # delete applied to property access: delete obj.prop or delete obj['prop']
                if target_node[0] == 'get':
                    base = self._eval_expr(target_node[1], env, this)
                    prop_node = target_node[2]
                    if prop_node[0] == 'id':
                        key = prop_node[1]
                    else:
                        key = self._eval_expr(prop_node, env, this)
                    try:
                        if isinstance(base, dict):
                            if key in base:
                                del base[key]
                            return True
                        # try attribute deletion on host objects
                        try:
                            delattr(base, key)
                            return True
                        except Exception:
                            # deletion may still be considered successful in non-strict mode
                            return True
                    except Exception:
                        return True
                # delete applied to an identifier (variable) - cannot delete local bindings; return False
                if target_node[0] == 'id':
                    name = target_node[1]
                    # If it's a property on global_env represented as dict, allow delete
                    try:
                        # If variable exists in current local env, JS semantics: delete variable -> false
                        if name in env.vars:
                            return False
                    except Exception:
                        pass
                    try:
                        # attempt to remove from global env dictionary
                        if name in self.global_env.vars:
                            del self.global_env.vars[name]
                            return True
                    except Exception:
                        pass
                    return False
            except Exception:
                return True
     
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
     
        # void unary: evaluate operand for side-effects, always return undefined
        if t == 'void':
            _, expr_node = node
            try:
                # evaluate operand but ignore the result
                self._eval_expr(expr_node, env, this)
            except Exception:
                # swallow errors (best-effort like other unary handlers)
                pass
            return undefined
     
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
                        # dictionary-backed JS objects use string keys
                        return tgt_obj.get(self._norm_prop_key(key), undefined)
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
                        # always coerce property keys to string for dict-like JS objects
                        tgt_obj[self._norm_prop_key(key)] = value
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
     
        # Object literal: ('obj', [(key, val_node), ...])
        if t == 'obj':
            _, props = node
            out = {}
            # Link to Object.prototype for proper inheritance
            try:
                obj_ctor = self._context.get('Object') if self._context else None
                if obj_ctor and hasattr(obj_ctor, 'prototype'):
                    out['__proto__'] = obj_ctor.prototype
            except Exception:
                pass
            for k, v_node in props:
                try:
                    # evaluate property value (best-effort)
                    val = undefined if v_node is None else self._eval_expr(v_node, env, this)
                except Exception:
                    val = undefined
                out[str(k)] = val
            return out
     
        # Array literal: ('arr', [elem_node, ...]) - supports holes represented as ('undef', None)
        if t == 'arr':
            _, elems = node
            out: Dict[str, Any] = {'__proto__': None}
            # Try to get Arr.prototype from context
            try:
                arr_ctor = self._context.get('Array') if self._context else None
                if arr_ctor and hasattr(arr_ctor, 'prototype'):
                    out['__proto__'] = arr_ctor.prototype
            except Exception:
                pass
            idx = 0
            for el in elems:
                # sparse array hole
                if isinstance(el, tuple) and el and el[0] == 'undef':
                    idx += 1
                    continue
                try:
                    v = self._eval_expr(el, env, this)
                except Exception:
                    v = undefined
                out[str(idx)] = v
                idx += 1
            out['length'] = idx
            return out
     
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
        # Conditional (ternary) expression: ('cond', cond, true_expr, false_expr)
        if t == 'cond':
            _, cond_node, true_node, false_node = node
            c = self._eval_expr(cond_node, env, this)
            if self._is_truthy(c):
                return self._eval_expr(true_node, env, this)
            return self._eval_expr(false_node, env, this)
     
        # Comma operator: evaluate left (for side-effects) then return right
        if t == 'comma':
            _, left_node, right_node = node
            try:
                self._eval_expr(left_node, env, this)
            except Exception:
                # best-effort continue to evaluate right
                pass
            return self._eval_expr(right_node, env, this)
     
        if t == 'unary':
            _, op, x = node
            v = self._eval_expr(x, env, this)
            if op == '-':
                return -float(v)
            if op == '!':
                # JS '!' returns boolean - invert JS truthiness
                return not self._is_truthy(v)
            if op == '~':
                # JS bitwise NOT: ToInt32 then bitwise not, return signed 32-bit result
                def _to_int32(val):
                    try:
                        n = int(float(val))
                    except Exception:
                        try:
                            n = int(str(val))
                        except Exception:
                            n = 0
                    n = n & 0xFFFFFFFF
                    return n - 0x100000000 if n & 0x80000000 else n
                iv = _to_int32(v)
                res = (~iv) & 0xFFFFFFFF
                return res - 0x100000000 if res & 0x80000000 else res
     
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
     
            # Bitwise operations: ToInt32 semantics (best-effort)
            def _to_int32_local(x):
                try:
                    n = int(float(x))
                except Exception:
                    try:
                        n = int(str(x))
                    except Exception:
                        n = 0
                n = n & 0xFFFFFFFF
                return n - 0x100000000 if n & 0x80000000 else n
     
            if op == '&' or op == '|' or op == '^':
                ai = _to_int32_local(lhs)
                bi = _to_int32_local(rhs)
                if op == '&':
                    r = ai & bi
                elif op == '|':
                    r = ai | bi
                else:  # '^'
                    r = ai ^ bi
                # normalize to signed-32
                r = r & 0xFFFFFFFF
                return r - 0x100000000 if r & 0x80000000 else r

            if op in ('<<', '>>', '>>>'):
                ai = _to_int32_local(lhs)
                bi = _to_int32_local(rhs) & 0x1F  # Mask to 5 bits (JS spec)
                
                if op == '<<':
                    r = (ai << bi) & 0xFFFFFFFF
                elif op == '>>':
                    # Signed right shift
                    if ai & 0x80000000:
                        r = (ai >> bi) | ~(0xFFFFFFFF >> bi)
                    else:
                        r = ai >> bi
                else:  # '>>>'
                    # Unsigned right shift
                    r = (ai & 0xFFFFFFFF) >> bi
                
                return r - 0x100000000 if r & 0x80000000 else r
            
            return self._apply_bin(op, lhs, rhs)
     
        if t == 'assign':
            _, left, right = node
            r = self._eval_expr(right, env, this)
            
            # **NEW: Intercept jQuery.each assignment and replace with native implementation**
            try:
                # Detect if we're assigning to jQuery.each or $.each
                is_jquery_each_assignment = False
                target_obj = None
                
                if left[0] == 'get':
                    # Assignment to property: obj.prop or obj['prop']
                    target_node = left[1]
                    prop_node = left[2]
                    
                    # Get property name
                    if prop_node[0] == 'id':
                        prop_name = prop_node[1]
                    else:
                        prop_name = self._eval_expr(prop_node, env, this)
                    
                    # Check if property is 'each'
                    if str(prop_name) == 'each':
                        # Evaluate the target object
                        target_obj = self._eval_expr(target_node, env, this)
                        
                        # Check if target is jQuery or $ (stored in global context)
                        try:
                            jquery_obj = self.global_env.vars.get('jQuery')
                            dollar_obj = self.global_env.vars.get('$')
                            
                            if (isinstance(target_obj, dict) and 
                                'fn' in target_obj and  # jQuery.fn exists
                                'extend' in target_obj):  # jQuery.extend exists
                                is_jquery_each_assignment = True
                        except Exception:
                            pass
                
                # If assigning to jQuery.each or $.each, replace with our native implementation
                if is_jquery_each_assignment and target_obj is not None:
                    # Import the native implementation from js_builtins
                    try:
                        # Get the native jQuery.each from context (registered by js_builtins)
                        native_jquery = self._context.get('jQuery') if self._context else None
                        if native_jquery and isinstance(native_jquery, dict):
                            native_each = native_jquery.get('each')
                            if native_each:
                                # Override jQuery's each with our native version
                                if isinstance(target_obj, dict):
                                    target_obj['each'] = native_each
                                print(f"[jsmini.intercept] Replaced jQuery.each with native implementation")
                                return native_each  # Return the native function, not jQuery's
                    except Exception as e:
                        print(f"[jsmini.intercept] Failed to replace jQuery.each: {e}")
            except Exception:
                pass  # Fall through to normal assignment
            
            # Normal assignment continues...
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
                        target[self._norm_prop_key(key)] = r
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
                # prototype-aware lookup (includes own properties)
                return self._prop_get(obj, key)
            except Exception:
                return undefined
     
        if t == 'call':
            _, callee_node, args_nodes = node
     
            receiver = None
            fn_val = None
            if isinstance(callee_node, tuple) and callee_node[0] == 'get':
                receiver = self._eval_expr(callee_node[1], env, this)
                prop_node = callee_node[2]
                if prop_node[0] == 'id':
                    fn_val = self._prop_get(receiver, prop_node[1])
                    if prop_node[1] == 'each' and isinstance(fn_val, JSFunction):
                        # Check if we're already deep in this specific function
                        fn_id = id(fn_val)
                        try:
                            depth = self._per_fn_call_depth.get(fn_id, 0)
                            # jQuery's each should never recurse more than 2-3 levels
                            if depth > 100:
                                print(f"[jsmini.guard] Blocking deep jQuery.each recursion (depth={depth})")
                                return undefined  # Break the loop by returning early
                        except Exception:
                            pass
                else:
                    fn_val = self._eval_expr(prop_node, env, this)
            else:
                fn_val = self._eval_expr(callee_node, env, this)
            
            args = [self._eval_expr(a, env, this) for a in args_nodes]
     
            # JSFunction (scripted/native)
            if isinstance(fn_val, JSFunction):
                # New: per-function reentrancy guard — count repeated invocations
                try:
                    fid = id(fn_val)
                    cnt = self._per_fn_call_counts.get(fid, 0) + 1
                    self._per_fn_call_counts[fid] = cnt
                    if self._per_fn_call_threshold and cnt > self._per_fn_call_threshold:
                        # Emit compressed call stack and annotate the offending function
                        try:
                            cs = list(getattr(self, '_call_stack', []))
                            cs_comp = JSFunction._compress_call_stack(cs)
                            import sys, re
                            print(f"[jsmini.recursion] Per-function call threshold exceeded for {fn_val.debug_label()} (count={cnt}). Call stack:", file=sys.stderr)
                            for line in cs_comp[-80:]:
                                m = re.search(r'@(\d+)', line)
                                if m:
                                    try:
                                        fn_id = int(m.group(1))
                                        snip = JSFUNCTION_REGISTRY.get(fn_id)
                                        if snip:
                                            print(f"  {line} -> snippet: {snip!r}", file=sys.stderr)
                                            continue
                                    except Exception:
                                        pass
                                print(f"  {line}", file=sys.stderr)
                        except Exception:
                            pass
                        raise RuntimeError(f"Per-function recursion limit hit for {fn_val.debug_label()} (count={cnt})")
                except Exception:
                    # if guard bookkeeping fails, continue without guard
                    pass
     
                return fn_val.call(self, receiver, args)
     
            # Host python-callable (native helpers)
            if callable(fn_val) and not isinstance(fn_val, JSFunction):
                try:
                    if receiver is not None:
                        return fn_val(receiver, *args)
                    return fn_val(*args)
                except TypeError:
                    return fn_val(*args)
     
            return undefined
     
        if t == 'new':
            # node shape: ('new', callee_node)
            # callee_node may itself be a ('call', target, args) when parentheses present.
            _, callee_node = node
            # Normalize to (target_node, args_nodes)
            if isinstance(callee_node, tuple) and callee_node and callee_node[0] == 'call':
                target_node = callee_node[1]
                args_nodes = callee_node[2]
            else:
                target_node = callee_node
                args_nodes = []
     
            # Evaluate constructor and arguments
            ctor = self._eval_expr(target_node, env, this)
            args_vals = [self._eval_expr(a, env, this) for a in args_nodes]
     
            # If constructor is a JSFunction, perform JS 'new' semantics:
            # - create a fresh object with its __proto__ set to ctor.prototype
            # - call ctor with that object as `this`
            # - if ctor returns an object, return it; otherwise return the newly created object
            try:
                if isinstance(ctor, JSFunction):
                    proto = getattr(ctor, 'prototype', None)
                    new_obj: Dict[str, Any] = {'__proto__': proto} if isinstance(proto, dict) or proto is not None else {}
                    # Ensure 'length' absent unless ctor sets it
                    try:
                        res = ctor.call(self, new_obj, args_vals)
                    except Exception:
                        return undefined
                    # If ctor returned an object (dict or JSFunction), return it; otherwise return the constructed object
                    if isinstance(res, dict) or isinstance(res, JSFunction):
                        return res
                    return new_obj
     
                # If ctor is a host-callable (unlikely for JS constructors), try calling it.
                if callable(ctor) and not isinstance(ctor, JSFunction):
                    try:
                        res = ctor(*args_vals)
                        if isinstance(res, dict) or isinstance(res, JSFunction):
                            return res
                    except Exception:
                        pass
                    # best-effort fallback: return a plain object
                    return {}
     
            except Exception:
                # On error, return undefined sentinel (best-effort)
                return undefined
     
    def _apply_bin(self, op, a, b):
        # existing arithmetic / comparison handlers...
        try:
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
        except TypeError:
            # fall through to guarded handling below when operands aren't directly comparable
            pass
     
        # 'in' operator: property in object
        if op == 'in':
            try:
                key = a if isinstance(a, str) else str(a)
                if isinstance(b, dict):
                    return key in b
                return hasattr(b, key)
            except Exception:
                return False
     
        # 'instanceof' semantics: walk prototype chain
        if op == 'instanceof':
            try:
                if isinstance(b, JSFunction):
                    target_proto = getattr(b, 'prototype', None)
                    cur = None
                    if isinstance(a, dict):
                        cur = a.get('__proto__', None)
                    else:
                        cur = getattr(a, '__proto__', None)
                    
                    # Add cycle detection for prototype chain walk
                    seen = set()
                    while cur is not None:
                        cur_id = id(cur)
                        if cur_id in seen:
                            # Cycle detected - not an instance
                            return False
                        seen.add(cur_id)
                        
                        if cur is target_proto:
                            return True
                        if isinstance(cur, dict):
                            cur = cur.get('__proto__', None)
                        else:
                            cur = getattr(cur, '__proto__', None)
                    return False
                if callable(b):
                    try:
                        return isinstance(a, b)
                    except Exception:
                        return False
                return False
            except Exception:
                return False
     
        if op in ('==','==='):
            return a == b
        if op in ('!=','!=='):
            return a != b
     
        # Relational comparisons: guard against incompatible Python comparisons (e.g. Undefined)
        if op in ('<', '>', '<=', '>='):
            # If both are strings, perform lexicographic compare (JS does this when both ToPrimitive yield strings)
            if isinstance(a, str) and isinstance(b, str):
                if op == '<': return a < b
                if op == '>': return a > b
                if op == '<=': return a <= b
                if op == '>=': return a >= b
     
            # JS-like numeric coercion for relation: undefined -> NaN, null -> 0, booleans -> 1/0
            def _relnum(x):
                if x is undefined:
                    return float('nan')
                if x is None:
                    return 0.0
                if isinstance(x, bool):
                    return 1.0 if x else 0.0
                if isinstance(x, (int, float)):
                    return float(x)
                try:
                    return float(x)
                except Exception:
                    # non-numeric string / object -> NaN for relation
                    return float('nan')
     
            na = _relnum(a)
            nb = _relnum(b)
            # Any NaN in relational comparison -> false (matches JS behavior where ToNumber(undefined) is NaN)
            if math.isnan(na) or math.isnan(nb):
                return False
            if op == '<': return na < nb
            if op == '>': return na > nb
            if op == '<=': return na <= nb
            if op == '>=': return na >= nb
     
        # fallback comparisons and operators preserved
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
        self.children: JSList = JSList()
        self.id: Optional[str] = None
        self.parent = None
        self._class_set = set()
        # Host / document links (set by make_dom_shim or when appended)
        self._host = None
        self._owner_document = None
        # DOM change logger (callable: (element, op, details_dict) -> None), injected by make_context/__enableDomLog
        self._dom_log = None
            
    def _dom_path(self) -> str:
        """Return a simple CSS-like path for this element (#id > tag.class)."""
        try:
            parts = []
            cur = self
            while isinstance(cur, Element):
                name = cur.tagName or 'node'
                pid = f"#{cur.id}" if cur.id else ''
                cls = cur.attrs.get('class') or ''
                cls_sfx = ('.' + '.'.join(cls.split())) if cls else ''
                parts.append(f"{name}{pid}{cls_sfx}")
                cur = getattr(cur, 'parent', None)
            return ' > '.join(reversed(parts))
        except Exception:
            return self.tagName or 'node'

    def _log_change(self, op: str, details: Dict[str, Any]) -> None:
        try:
            cb = getattr(self, '_dom_log', None)
            if not callable(cb):
                # fallback: try from ownerDocument (document dict stores fn under '__dom_log_fn')
                try:
                    doc = getattr(self, '_owner_document', None)
                    if isinstance(doc, dict):
                        cb = doc.get('__dom_log_fn')
                except Exception:
                    cb = None
            if callable(cb):
                cb(self, op, details or {})
        except Exception:
            pass

    def _notify_dom_change(self):
        """
        Best-effort: when this element (or any descendant) mutates, push updated body HTML
        through host.setRaw(). Uses ownerDocument['body'].innerHTML for serialization.
        """
        try:
            host = self._host
            doc = self._owner_document
            if not host or not isinstance(host, dict):
                return
            if not doc or not isinstance(doc, dict):
                return
            body = doc.get('body')
            if not isinstance(body, Element):
                return
            set_raw = host.get('setRaw')
            if callable(set_raw):
                set_raw(body.innerHTML)
        except Exception:
            pass

    def setAttribute(self, k: str, v: Any) -> None:
        self.attrs[k] = v
        if k == 'id':
            self.id = v
        if k == 'class':
            try:
                self._class_set = set(str(v).split())
            except Exception:
                self._class_set = set()
        self._log_change('setAttribute', {'name': k, 'value': v, 'path': self._dom_path()})
        self._notify_dom_change()

    def removeAttribute(self, k: str) -> None:
        try:
            self.attrs.pop(k, None)
            if k == 'id':
                self.id = None
            if k == 'class':
                self._class_set = set()
        except Exception:
            pass
        self._log_change('removeAttribute', {'name': k, 'path': self._dom_path()})
        self._notify_dom_change()

    def appendChild(self, child: Any) -> None:
        """Attach child, propagate host/document and notify."""
        try:
            if isinstance(child, Element):
                child.parent = self
                child._host = self._host
                child._owner_document = self._owner_document
                # propagate logger
                child._dom_log = getattr(self, '_dom_log', None) or (self._owner_document.get('__dom_log_fn') if isinstance(self._owner_document, dict) else None)
            if isinstance(self.children, JSList):
                self.children.append(child)
            else:
                self.children.append(child)
        except Exception:
            try:
                self.children.append(child)
            except Exception:
                pass
        self._log_change('appendChild', {'child': getattr(child, 'tagName', type(child).__name__), 'path': self._dom_path()})
        self._notify_dom_change()

    def removeChild(self, child: Any) -> None:
        """Detach child and notify (no exception on failure)."""
        try:
            if isinstance(self.children, JSList):
                lst = self.children._list
                if child in lst:
                    lst.remove(child)
                    if isinstance(child, Element):
                        child.parent = None
            else:
                if child in self.children:
                    self.children.remove(child)
                    if isinstance(child, Element):
                        child.parent = None
        except Exception:
            pass
        self._log_change('removeChild', {'child': getattr(child, 'tagName', type(child).__name__), 'path': self._dom_path()})
        self._notify_dom_change()

    def insertBefore(self, newNode: Any, referenceNode: Any) -> None:
        """Insert newNode before referenceNode; append if ref not found; notify."""
        try:
            lst = self.children._list
            try:
                idx = lst.index(referenceNode)
            except ValueError:
                idx = len(lst)
            if isinstance(newNode, Element):
                newNode.parent = self
                newNode._host = self._host
                newNode._owner_document = self._owner_document
                newNode._dom_log = getattr(self, '_dom_log', None) or (self._owner_document.get('__dom_log_fn') if isinstance(self._owner_document, dict) else None)
            lst.insert(idx, newNode)
        except Exception:
            try:
                self.appendChild(newNode)
                return
            except Exception:
                pass
        self._log_change('insertBefore', {
            'newNode': getattr(newNode, 'tagName', type(newNode).__name__),
            'referenceNode': getattr(referenceNode, 'tagName', type(referenceNode).__name__),
            'path': self._dom_path()
        })
        self._notify_dom_change()

    def replaceChild(self, newNode: Any, oldNode: Any) -> None:
        """Replace oldNode with newNode and notify."""
        try:
            lst = self.children._list
            try:
                idx = lst.index(oldNode)
                if isinstance(newNode, Element):
                    newNode.parent = self
                    newNode._host = self._host
                    newNode._owner_document = self._owner_document
                    newNode._dom_log = getattr(self, '_dom_log', None) or (self._owner_document.get('__dom_log_fn') if isinstance(self._owner_document, dict) else None)
                lst[idx] = newNode
                if isinstance(oldNode, Element):
                    oldNode.parent = None
            except ValueError:
                if isinstance(newNode, Element):
                    newNode.parent = self
                    newNode._host = self._host
                    newNode._owner_document = self._owner_document
                    newNode._dom_log = getattr(self, '_dom_log', None) or (self._owner_document.get('__dom_log_fn') if isinstance(self._owner_document, dict) else None)
                lst.append(newNode)
        except Exception:
            pass
        self._log_change('replaceChild', {
            'newNode': getattr(newNode, 'tagName', type(newNode).__name__),
            'oldNode': getattr(oldNode, 'tagName', type(oldNode).__name__),
            'path': self._dom_path()
        })
        self._notify_dom_change()

    @property
    def classList(self):
        el = self
        def _add(this, *cls_names):
            try:
                for nm in cls_names:
                    el._class_set.add(str(nm))
                el.attrs['class'] = ' '.join(el._class_set)
            except Exception:
                pass
            el._notify_dom_change()
        def _remove(this, *cls_names):
            try:
                for nm in cls_names:
                    el._class_set.discard(str(nm))
                el.attrs['class'] = ' '.join(el._class_set)
            except Exception:
                pass
            el._notify_dom_change()
        def _contains(this, name):
            try:
                return str(name) in el._class_set
            except Exception:
                return False
        def _toggle(this, name, force=None):
            try:
                n = str(name)
                if force is None:
                    present = n not in el._class_set
                    if present:
                        el._class_set.add(n)
                    else:
                        el._class_set.remove(n)
                else:
                    if bool(force):
                        el._class_set.add(n); present = True
                    else:
                        el._class_set.discard(n); present = False
                el.attrs['class'] = ' '.join(el._class_set)
            except Exception:
                present = False
            el._notify_dom_change()
            return present
        return {
            'add': lambda *a: _add(None, *a),
            'remove': lambda *a: _remove(None, *a),
            'contains': lambda a: _contains(None, a),
            'toggle': lambda a, f=None: _toggle(None, a, f)
        }

    def hasAttribute(self, k: str) -> bool:
        try:
            return k in self.attrs
        except Exception:
            return False

    def addEventListener(self, event: str, handler, useCapture: bool = False) -> None:
        try:
            if not hasattr(self, '_listeners'):
                self._listeners = {}
            lst = self._listeners.setdefault(event, [])
            if handler not in lst:  # ← Prevent duplicates
                lst.append(handler)
        except Exception:
            pass

    def removeEventListener(self, event: str, handler=None) -> None:
        try:
            if not hasattr(self, '_listeners'):
                return
            if handler is None:
                self._listeners.pop(event, None)
                return
            lst = self._listeners.get(event)
            if not lst:
                return
            try:
                while handler in lst:
                    lst.remove(handler)
            except Exception:
                pass
            if not lst:
                self._listeners.pop(event, None)
        except Exception:
            pass

    def dispatchEvent(self, ev) -> None:
        """
        Dispatch event to stored listeners.
        - Accepts a string event type or an event object (dict-like).
        - For JSFunction handlers: enqueue via context timers to avoid synchronous re-entry.
        - Ensures event.target, event.type, defaultPrevented flag semantics.
        - RE-ENTRANCY GUARD: Prevents infinite recursion when handlers trigger more events.
        - BATCH GUARD: Only enqueues each (element, event) pair once per timer drain cycle.
        """
        try:
            # Normalize event object
            if isinstance(ev, str):
                ev_obj = {'type': ev, 'defaultPrevented': False, 'cancelBubble': False, 'target': self}
            elif isinstance(ev, dict):
                ev_obj = ev
                try:
                    if 'type' not in ev_obj or not isinstance(ev_obj.get('type'), str):
                        ev_obj['type'] = str(ev_obj.get('type', ''))
                except Exception:
                    ev_obj['type'] = ''
                try:
                    ev_obj.setdefault('defaultPrevented', False)
                    ev_obj.setdefault('cancelBubble', False)
                    ev_obj['target'] = self
                except Exception:
                    pass
            else:
                ev_obj = {'type': str(ev), 'defaultPrevented': False, 'cancelBubble': False, 'target': self}
    
            etype = ev_obj.get('type')
            
            # **RE-ENTRANCY GUARD**: Check if we're already dispatching this event type on this element
            dispatch_key = (id(self), etype)
            
            # Get or create the global dispatch tracker (lives on _LAST_INTERPRETER context)
            try:
                if _LAST_INTERPRETER is not None and hasattr(_LAST_INTERPRETER, '_context'):
                    ctx = _LAST_INTERPRETER._context
                elif hasattr(self, '_interp') and getattr(self, '_interp', None) is not None:
                    ctx = getattr(self, '_interp', None)._context
                else:
                    ctx = None
                    
                if ctx is not None:
                    active_dispatches = ctx.setdefault('_active_dispatches', set())
                    
                    # If already dispatching this event on this element, SKIP to avoid recursion
                    if dispatch_key in active_dispatches:
                        print(f"[Element.dispatchEvent] RE-ENTRY BLOCKED: {etype!r} on element {id(self)}")
                        return  # ← CRITICAL: Exit immediately
                    
                    # Mark as active
                    active_dispatches.add(dispatch_key)
                    
                    # **NEW: BATCH GUARD** - Track which (element, event) pairs have been enqueued this cycle
                    pending_events = ctx.setdefault('_pending_events', set())
                    
                    # If this event is already pending in the queue, don't enqueue again
                    if dispatch_key in pending_events:
                        print(f"[Element.dispatchEvent] BATCH DUPLICATE BLOCKED: {etype!r} on element {id(self)} (already in queue)")
                        active_dispatches.discard(dispatch_key)  # Clean up re-entrancy marker
                        return  # ← Skip duplicate enqueue
            except Exception:
                # Fallback: proceed without guard (safer than blocking valid events)
                ctx = None
                active_dispatches = None
                pending_events = None
            
            handlers = getattr(self, '_listeners', {}).get(etype, [])
    
            print(f"[Element.dispatchEvent] etype={etype!r}, num_handlers={len(handlers)}, handler_ids={[id(h) for h in handlers]}")
    
            for h in list(handlers):
                print(f"[Element.dispatchEvent] Processing handler id={id(h)}, is_callable={callable(h)}, is_JSFunction={isinstance(h, JSFunction)}")
                try:
                    # Plain python callable -> invoke inline
                    if callable(h) and not isinstance(h, JSFunction):
                        print(f"[Element.dispatchEvent] Calling Python handler inline")
                        try:
                            h(ev_obj)
                        except Exception as e:
                            print(f"[Element.dispatchEvent] Python handler raised: {e}")
                        print(f"[Element.dispatchEvent] Python handler done, continuing...")
                        continue
                    
                    print(f"[Element.dispatchEvent] Handler is JSFunction, enqueuing...")
    
                    # JSFunction: enqueue into timers to avoid deep sync recursion
                    handler_ctx = ctx  # Use the same context we checked earlier
                    if handler_ctx is None:
                        try:
                            if hasattr(self, '_interp') and getattr(self, '_interp', None) is not None:
                                handler_ctx = getattr(self, '_interp', None)._context
                        except Exception:
                            handler_ctx = None
                    if handler_ctx is None and _LAST_INTERPRETER is not None:
                        try:
                            handler_ctx = getattr(_LAST_INTERPRETER, '_context', None)
                        except Exception:
                            handler_ctx = None
    
                    if handler_ctx is not None:
                        try:
                            # **Mark this event as pending before enqueuing**
                            if pending_events is not None:
                                pending_events.add(dispatch_key)
                            
                            handler_ctx.setdefault('_timers', []).append((h, (ev_obj,)))
                            print(f"[Element.dispatchEvent] Enqueued handler, queue length now: {len(handler_ctx['_timers'])}")
                            continue  # ← CRITICAL: Skip direct call!
                        except Exception:
                            pass  # Fall through to direct call on enqueue failure
    
                    # Last resort: direct call (only if ctx was None)
                    try:
                        if isinstance(h, JSFunction):
                            h.call(_LAST_INTERPRETER, self, [ev_obj])
                        elif callable(h):
                            h(ev_obj)
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            # **CLEANUP**: Remove from active dispatches when done
            try:
                if ctx is not None and active_dispatches is not None:
                    active_dispatches.discard(dispatch_key)
            except Exception:
                pass

    def matches(self, selector: str) -> bool:
        """Minimal selector support used by libraries: #id, .class, tag name."""
        try:
            sel = (selector or '').strip()
            if not sel:
                return False
            if sel.startswith('#'):
                return self.id == sel[1:]
            if sel.startswith('.'):
                cls = sel[1:]
                return cls in (self.attrs.get('class') or '').split()
            return self.tagName.lower() == sel.lower()
        except Exception:
            return False

    def appendChild(self, child: Any) -> None:
        """Attach child, propagate host/document and notify."""
        try:
            if isinstance(child, Element):
                child.parent = self
                child._host = self._host
                child._owner_document = self._owner_document
            if isinstance(self.children, JSList):
                self.children.append(child)
            else:
                self.children.append(child)
        except Exception:
            try:
                self.children.append(child)
            except Exception:
                pass
        self._notify_dom_change()

    def removeChild(self, child: Any) -> None:
        """Detach child and notify (no exception on failure)."""
        try:
            if isinstance(self.children, JSList):
                lst = self.children._list
                if child in lst:
                    lst.remove(child)
                    if isinstance(child, Element):
                        child.parent = None
            else:
                if child in self.children:
                    self.children.remove(child)
                    if isinstance(child, Element):
                        child.parent = None
        except Exception:
            pass
        self._notify_dom_change()

    def insertBefore(self, newNode: Any, referenceNode: Any) -> None:
        """Insert newNode before referenceNode; append if ref not found; notify."""
        try:
            lst = self.children._list
            try:
                idx = lst.index(referenceNode)
            except ValueError:
                idx = len(lst)
            if isinstance(newNode, Element):
                newNode.parent = self
                newNode._host = self._host
                newNode._owner_document = self._owner_document
            lst.insert(idx, newNode)
        except Exception:
            try:
                self.appendChild(newNode)
            except Exception:
                pass
        self._notify_dom_change()

    def replaceChild(self, newNode: Any, oldNode: Any) -> None:
        """Replace oldNode with newNode and notify."""
        try:
            lst = self.children._list
            try:
                idx = lst.index(oldNode)
                if isinstance(newNode, Element):
                    newNode.parent = self
                    newNode._host = self._host
                    newNode._owner_document = self._owner_document
                lst[idx] = newNode
                if isinstance(oldNode, Element):
                    oldNode.parent = None
            except ValueError:
                if isinstance(newNode, Element):
                    newNode.parent = self
                    newNode._host = self._host
                    newNode._owner_document = self._owner_document
                lst.append(newNode)
        except Exception:
            pass
        self._notify_dom_change()

    @property
    def parentNode(self):
        return self.parent

    @property
    def firstChild(self):
        try:
            return self.children.get(0)
        except Exception:
            return None

    @property
    def lastChild(self):
        try:
            if len(self.children) == 0:
                return None
            return self.children.get(len(self.children) - 1)
        except Exception:
            return None

    @property
    def nextSibling(self):
        try:
            if not self.parent:
                return None
            siblings = self.parent.children._list
            try:
                idx = siblings.index(self)
            except ValueError:
                return None
            if idx + 1 < len(siblings):
                return siblings[idx + 1]
            return None
        except Exception:
            return None

    @property
    def previousSibling(self):
        try:
            if not self.parent:
                return None
            siblings = self.parent.children._list
            try:
                idx = siblings.index(self)
            except ValueError:
                return None
            if idx - 1 >= 0:
                return siblings[idx - 1]
            return None
        except Exception:
            return None

    @property
    def textContent(self) -> str:
        """Return concatenated text of this element's subtree (recursive)."""
        try:
            out = []
            for c in self.children:
                if isinstance(c, Element):
                    out.append(c.textContent)
                else:
                    out.append(str(c))
            return ''.join(out)
        except Exception:
            return ''

    @textContent.setter
    def textContent(self, val: Any) -> None:
        try:
            self.children = JSList([str(val)])
        except Exception:
            pass
        self._log_change('setTextContent', {'value': str(val)[:120], 'path': self._dom_path()})
        self._notify_dom_change()

    @property
    def innerHTML(self) -> str:
        """Simple serializer of children to an HTML-ish string (minimal)."""
        try:
            parts = []
            for c in self.children:
                if isinstance(c, Element):
                    attrs = []
                    if c.id:
                        attrs.append(f'id="{c.id}"')
                    if c.attrs.get('class'):
                        attrs.append(f'class="{html.escape(str(c.attrs.get("class")))}"')
                    attr_str = (' ' + ' '.join(attrs)) if attrs else ''
                    parts.append(f"<{c.tagName}{attr_str}>{html.escape(c.textContent)}</{c.tagName}>")
                else:
                    parts.append(html.escape(str(c)))
            return ''.join(parts)
        except Exception:
            return ''

    @innerHTML.setter
    def innerHTML(self, html_str: Any) -> None:
        try:
            raw = str(html_str or '')
            nodes = _parse_inner_html_fragment(raw)
            for n in nodes:
                if isinstance(n, Element):
                    n.parent = self
                    n._host = self._host
                    n._owner_document = self._owner_document
                    n._dom_log = getattr(self, '_dom_log', None) or (self._owner_document.get('__dom_log_fn') if isinstance(self._owner_document, dict) else None)
            self.children = JSList(nodes)
        except Exception:
            try:
                self.children = JSList([str(html_str)])
            except Exception:
                pass
        self._log_change('setInnerHTML', {'length': len(str(html_str or '')), 'path': self._dom_path()})
        self._notify_dom_change()

    @property
    def nodeType(self) -> int:
        """Return DOM node type (1 == Element)."""
        try:
            return 1
        except Exception:
            return 1

    @property
    def nodeName(self) -> str:
        """Return tag name in DOM-style (typically uppercase in many environments)."""
        try:
            return (self.tagName or '').upper()
        except Exception:
            return (self.tagName or '').upper()

    @property
    def className(self) -> str:
        """Reflect the 'class' attribute as a string (get/set)."""
        try:
            return str(self.attrs.get('class') or '')
        except Exception:
            return ''

    @className.setter
    def className(self, val: Any) -> None:
        try:
            s = '' if val is None else str(val)
            self.attrs['class'] = s
            self._class_set = set(s.split())
        except Exception:
            pass
        self._log_change('setClassName', {'value': str(val), 'path': self._dom_path()})
        self._notify_dom_change()

    @property
    def childNodes(self) -> JSList:
        """Alias to children; preserves JS-like `.length` semantics."""
        try:
            return self.children
        except Exception:
            return JSList([])

    @property
    def ownerDocument(self):
        """Return owner document if set by make_dom_shim; otherwise None."""
        return getattr(self, '_owner_document', None)

    def contains(self, other) -> bool:
        """Return True if `other` is this node or a descendant of this node."""
        try:
            if other is None:
                return False
            if other is self:
                return True
            # walk up parents from `other`
            cur = getattr(other, 'parent', None)
            while cur is not None:
                if cur is self:
                    return True
                cur = getattr(cur, 'parent', None)
            return False
        except Exception:
            return False

    def closest(self, selector: str):
        """
        Return the closest ancestor (including self) that matches selector.
        Uses the same simple selector syntax as `matches`.
        """
        try:
            sel = selector or ''
            cur = self
            while cur is not None:
                try:
                    if isinstance(cur, Element) and cur.matches(sel):
                        return cur
                except Exception:
                    pass
                cur = getattr(cur, 'parent', None)
            return None
        except Exception:
            return None

    def getElementsByClassName(self, class_name: str):
        """
        Return JSList of descendant elements that have the given class name.
        Mirrors DOM semantics for a single class token (space-separated in the attribute).
        """
        try:
            if not class_name:
                return JSList([])
            want = str(class_name)
            out: List[Any] = []

            def walk(node):
                try:
                    if not isinstance(node, Element):
                        return
                    classes = (node.attrs.get('class') or '').split()
                    if want in classes:
                        out.append(node)
                    for ch in (node.children if isinstance(node.children, JSList) else []):
                        walk(ch)
                except Exception:
                    pass

            for ch in self.children:
                walk(ch)
            return JSList(out)
        except Exception:
            return JSList([])

    @property
    def classList(self):
        el = self
        def _add(this, *cls_names):
            try:
                for nm in cls_names:
                    el._class_set.add(str(nm))
                el.attrs['class'] = ' '.join(el._class_set)
            except Exception:
                pass
            el._log_change('classList.add', {'tokens': [str(n) for n in cls_names], 'path': el._dom_path()})
            el._notify_dom_change()
        def _remove(this, *cls_names):
            try:
                for nm in cls_names:
                    el._class_set.discard(str(nm))
                el.attrs['class'] = ' '.join(el._class_set)
            except Exception:
                pass
            el._log_change('classList.remove', {'tokens': [str(n) for n in cls_names], 'path': el._dom_path()})
            el._notify_dom_change()
        def _contains(this, name):
            try:
                return str(name) in el._class_set
            except Exception:
                return False
        def _toggle(this, name, force=None):
            try:
                n = str(name)
                if force is None:
                    present = n not in el._class_set
                    if present:
                        el._class_set.add(n)
                    else:
                        el._class_set.remove(n)
                else:
                    if bool(force):
                        el._class_set.add(n); present = True
                    else:
                        el._class_set.discard(n); present = False
                el.attrs['class'] = ' '.join(el._class_set)
            except Exception:
                present = False
            el._log_change('classList.toggle', {'token': str(name), 'force': None if force is None else bool(force), 'path': el._dom_path()})
            el._notify_dom_change()
            return present
        return {
            'add': lambda *a: _add(None, *a),
            'remove': lambda *a: _remove(None, *a),
            'contains': lambda a: _contains(None, a),
            'toggle': lambda a, f=None: _toggle(None, a, f)
        }

    def getElementsByTagName(self, tag: str):
        """Return JSList of descendant elements matching tag (case-insensitive)."""
        try:
            out = []

            def walk(node):
                try:
                    if isinstance(node, Element):
                        if not tag or node.tagName.lower() == tag.lower():
                            out.append(node)
                        for ch in node.children:
                            walk(ch)
                except Exception:
                    pass

            for ch in self.children:
                walk(ch)
            return JSList(out)
        except Exception:
            return JSList([])

    def __repr__(self) -> str:
        return f"<Element {self.tagName} id={self.id}>"

class _InnerHTMLParser(HTMLParser):
    """
    Build Element/text node list from an HTML fragment.
    - Only builds Elements and text nodes (strings).
    - Does not execute or include <script> or <style> contents (they are ignored).
    - Preserves id and class attributes; other attributes stored in attrs mapping.
    """
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element('fragment')
        self.stack = [self.root]
        self._suppress_depth = 0  # suppress script/style content

    def handle_starttag(self, tag, attrs):
        lt = tag.lower()
        if lt in ('script', 'style'):
            # suppress inner data and do not create node
            self._suppress_depth += 1
            return
        try:
            el = Element(lt)
            # set attributes (id/class + others into attrs dict)
            for k, v in attrs:
                el.attrs[k] = v
                if k == 'id':
                    el.id = v
                if k == 'class':
                    try:
                        el._class_set = set(str(v).split())
                    except Exception:
                        el._class_set = set()
            # append to current top
            parent = self.stack[-1]
            parent.appendChild(el)
            # push element on stack
            self.stack.append(el)
        except Exception:
            pass

    def handle_endtag(self, tag):
        lt = tag.lower()
        if lt in ('script', 'style'):
            if self._suppress_depth > 0:
                self._suppress_depth -= 1
            return
        # pop stack until matching tag found (best-effort)
        try:
            for i in range(len(self.stack) - 1, -1, -1):
                node = self.stack[i]
                if isinstance(node, Element) and node.tagName == lt:
                    # pop including node
                    del self.stack[i:]
                    break
            # ensure there's at least root
            if not self.stack:
                self.stack = [self.root]
        except Exception:
            self.stack = [self.root]

    def handle_data(self, data):
        if self._suppress_depth > 0:
            return
        if not data:
            return
        # append text node to current parent (keep as plain string)
        parent = self.stack[-1]
        parent.appendChild(data)

def _parse_inner_html_fragment(src: str) -> List[Any]:
    """Return list of nodes (Element or str) parsed from the fragment `src` (safe subset)."""
    try:
        p = _InnerHTMLParser()
        p.feed(src)
        # children of fragment root are the parsed nodes
        nodes = list(p.root.children._list)
        # detach the artificial root parent
        for n in nodes:
            if isinstance(n, Element):
                n.parent = None  # parent will be set by caller when inserted
        return nodes
    except Exception:
        # fallback: single text node
        return [src]

def make_dom_shim(host=None):
    registry: Dict[str, Element] = {}
    root = Element('document')
    body = Element('body')
    root.body = body

    # Attach host / document pointers to body
    body._host = host
    document = {}  # placeholder until populated
    body._owner_document = document

    def _notify_dom_change():
        try:
            if host and isinstance(host, dict):
                set_raw = host.get('setRaw')
                if callable(set_raw):
                    set_raw(body.innerHTML)
        except Exception:
            pass

    def _force_redraw():
        """Explicit redraw: recompute body.innerHTML and push through host.setRaw."""
        try:
            _notify_dom_change()
        except Exception:
            pass
        return body.innerHTML

    def _attach(el: Element):
        try:
            el._host = host
            el._owner_document = document
            # inherit logger if already configured on document
            try:
                el._dom_log = document.get('__dom_log_fn')
            except Exception:
                pass
        except Exception:
            pass
        return el

    def createElement(tag: str) -> Element:
        el = _attach(Element(tag))
        try:
            cb = document.get('__dom_log_fn')
            if callable(cb):
                cb(el, 'createElement', {'tag': tag, 'path': el._dom_path()})
        except Exception:
            pass
        return el

    def getElementById(idv: str) -> Optional[Element]:
        if body.id == idv:
            return body
        for c in body.children:
            if isinstance(c, Element) and c.id == idv:
                return c
            stack = [c] if isinstance(c, Element) else []
            while stack:
                n = stack.pop(0)
                if n.id == idv:
                    return n
                for ch in n.children:
                    if isinstance(ch, Element):
                        stack.append(ch)
        return None

    def append_to_body(el: Any) -> None:
        if isinstance(el, Element):
            _attach(el)
        body.appendChild(el)
        # appendChild logs; also log document-level append for clarity
        try:
            cb = document.get('__dom_log_fn')
            if callable(cb):
                cb(body, 'document.appendChild', {'child': getattr(el, 'tagName', type(el).__name__), 'path': body._dom_path()})
        except Exception:
            pass
        _notify_dom_change()

    def querySelector(sel: str) -> Optional[Element]:
        """Minimal querySelector: supports #id, .class, tag selectors."""
        try:
            if not sel:
                return None
            sel = sel.strip()
            if sel.startswith('#'):
                return getElementById(sel[1:])
            # For class/tag, do a simple walk (not optimized)
            if sel.startswith('.'):
                cls = sel[1:]
                for el in [body] + list(body.getElementsByClassName(cls)):
                    if isinstance(el, Element):
                        return el
                return None
            # Tag selector
            for el in [body] + list(body.getElementsByTagName(sel)):
                if isinstance(el, Element):
                    return el
            return None
        except Exception:
            return None

    def querySelectorAll(sel: str):
        """Minimal querySelectorAll: returns JSList."""
        try:
            if not sel:
                return JSList([])
            sel = sel.strip()
            if sel.startswith('.'):
                return body.getElementsByClassName(sel[1:])
            return body.getElementsByTagName(sel)
        except Exception:
            return JSList([])

    # Document-level event helpers (unchanged)
    def _doc_add_event_listener(ev_type, handler, useCapture: bool = False):
        try:
            if ev_type is None:
                return
            et = ev_type[2:] if isinstance(ev_type, str) and ev_type.startswith('on') else ev_type
            if not hasattr(root, '_listeners'):
                root._listeners = {}
            listeners = root._listeners.setdefault(et, [])
            
            print(f"[_doc_add_event_listener] event={et!r}, handler_id={id(handler)}, already_in_list={handler in listeners}, list_len={len(listeners)}")
            
            if handler not in listeners:
                listeners.append(handler)
                print(f"[_doc_add_event_listener] ADDED handler, new_len={len(listeners)}")
            else:
                print(f"[_doc_add_event_listener] SKIPPED (duplicate)")
        except Exception as e:
            print(f"[_doc_add_event_listener] EXCEPTION: {e}")

    def _doc_remove_event_listener(ev_type, handler=None, useCapture: bool = False):
        try:
            if ev_type is None:
                return
            et = ev_type[2:] if isinstance(ev_type, str) and ev_type.startswith('on') else ev_type
            if not hasattr(root, '_listeners'):
                return
            if handler is None:
                root._listeners.pop(et, None)
                return
            lst = root._listeners.get(et)
            if not lst:
                return
            try:
                while handler in lst:
                    lst.remove(handler)
            except Exception:
                pass
            if not lst:
                root._listeners.pop(et, None)
        except Exception:
            pass

    def _doc_attach_event(evt_name, handler):
        try:
            if not isinstance(evt_name, str):
                return
            name = evt_name[2:] if evt_name.startswith('on') else evt_name
            _doc_add_event_listener(name, handler, False)
        except Exception:
            pass

    def _doc_dispatch_event(ev):
        print(f"[_doc_dispatch_event] CALLED with ev={ev!r}")
        try:
            root.dispatchEvent(ev)
        except Exception:
            pass

    # Flexible wrappers that work for both Python and JS callers
    def _w_create_element(*args):
        tag = args[1] if len(args) > 1 else args[0] if args else ''
        return createElement(tag)

    def _w_get_element_by_id(*args):
        idv = args[1] if len(args) > 1 else args[0] if args else ''
        return getElementById(idv)

    def _w_append_child(*args):
        el = args[1] if len(args) > 1 else args[0] if args else None
        return append_to_body(el)

    def _w_add_event_listener(*args):
        # args can be (doc, ev_type, handler, useCapture) or (ev_type, handler, useCapture)
        if len(args) >= 3:
            # Assume first arg is doc (from JS), rest are actual params
            return _doc_add_event_listener(args[1], args[2], args[3] if len(args) > 3 else False)
        elif len(args) >= 2:
            # Called from Python without doc
            return _doc_add_event_listener(args[0], args[1], args[2] if len(args) > 2 else False)
        return None

    def _w_remove_event_listener(*args):
        if len(args) >= 2:
            # (doc, ev_type, handler, useCapture) from JS
            return _doc_remove_event_listener(args[1], args[2] if len(args) > 2 else None, args[3] if len(args) > 3 else False)
        elif len(args) >= 1:
            # (ev_type, handler, useCapture) from Python
            return _doc_remove_event_listener(args[0], args[1] if len(args) > 1 else None, args[2] if len(args) > 2 else False)
        return None

    def _w_attach_event(*args):
        if len(args) >= 2:
            return _doc_attach_event(args[1], args[2] if len(args) > 2 else None)
        elif len(args) >= 1:
            return _doc_attach_event(args[0], args[1] if len(args) > 1 else None)
        return None

    def _w_dispatch_event(*args):
        print(f"[_w_dispatch_event] CALLED with args={args}")
        ev = args[1] if len(args) > 1 else args[0] if args else None
        return _doc_dispatch_event(ev)

    # document is a dict; values are flexible wrappers
    def _w_query_selector(*args):
        sel = args[1] if len(args) > 1 else args[0] if args else ''
        return querySelector(sel)

    def _w_query_selector_all(*args):
        sel = args[1] if len(args) > 1 else args[0] if args else ''
        return querySelectorAll(sel)

    document = {
        'createElement': _w_create_element,
        'getElementById': lambda *a: getElementById(a[1] if len(a) > 1 else a[0] if a else ''),
        'querySelector': lambda *a: querySelector(a[1] if len(a) > 1 else a[0] if a else ''),
        'querySelectorAll': lambda *a: querySelectorAll(a[1] if len(a) > 1 else a[0] if a else ''),
        'body': body,
        'appendChild': _w_append_child,
        'addEventListener': _w_add_event_listener,
        'removeEventListener': _w_remove_event_listener,
        'attachEvent': _w_attach_event,
        'dispatchEvent': _w_dispatch_event,
        'forceRedraw': lambda: _force_redraw(),          
        '_notify_dom_change': _notify_dom_change,
        '__setHost': lambda h: (_set_host(h))
    }
    body._owner_document = document

    def _set_host(h):
        nonlocal host
        host = h
        body._host = h
        document['host'] = h
        _notify_dom_change()

    if host is not None:
        _set_host(host)

    return document
# --- timers / scheduler -----------------------------------------------------
def make_timers_container():
    return {'_timers': []}  # timers: list of (fn, args)

def run_timers_from_context(context: Dict[str,Any]):
    """Run queued timers with enhanced guards against infinite loops."""
    timers = context.setdefault('_timers', [])
    interp = context.get('_interp') or _LAST_INTERPRETER
    if interp is not None and context.get('_interp') is None:
        try:
            context['_interp'] = interp
        except Exception:
            pass

    intervals = context.get('_intervals', None)
    
    # Enhanced: Track total timer executions across all drain cycles
    total_executed = context.get('_total_timer_executions', 0)
    max_total_executions = 10000  # Absolute cap
    
    if total_executed >= max_total_executions:
        raise RuntimeError(
            f"Timer execution limit exceeded ({total_executed} total executions). "
            "Possible infinite timer loop detected."
        )

    initial_len = len(timers)
    executed_count = 0
    
    # **NEW GUARD**: Detect runaway queue growth (enqueuing faster than executing)
    max_growth_per_cycle = 100  # Allow queue to grow by max 100 items per drain
    
    for _ in range(initial_len):
        if executed_count >= 1000:  # Per-drain-cycle limit
            break
        
        # **CHECK QUEUE GROWTH**: If queue is growing too fast, abort
        current_queue_size = len(timers)
        if current_queue_size > (initial_len + max_growth_per_cycle):
            raise RuntimeError(
                f"Timer queue explosion detected: started with {initial_len} timers, "
                f"now have {current_queue_size} after {executed_count} executions. "
                "Event handlers are likely enqueuing new events faster than they can be processed."
            )
            
        if not timers:  # Queue emptied early
            break
            
        item = timers.pop(0)
        try:
            def _check_timer_guard(fn_obj):
                try:
                    if not isinstance(fn_obj, JSFunction):
                        return
                    interp_local = context.get('_interp') or _LAST_INTERPRETER
                    limit = int(getattr(interp_local, '_per_fn_call_threshold', 0) or 0)
                    if not limit:
                        return
                    counts = context.setdefault('_timer_call_counts', {})
                    fid = id(fn_obj)
                    cnt = counts.get(fid, 0) + 1
                    counts[fid] = cnt
                    if cnt > limit:
                        raise RuntimeError(
                            f"Per-function recursion limit hit for {fn_obj.debug_label()} "
                            f"(timer-invocations={cnt})"
                        )
                except RuntimeError:
                    raise
                except Exception:
                    pass

            # Interval handling
            if isinstance(item, tuple) and len(item) == 2 and item[0] == '__interval__':
                tid = item[1]
                if not intervals:
                    continue
                entry = intervals.get(tid)
                if not entry:
                    continue
                fn, it_args = entry
                _check_timer_guard(fn)
                
                call_interp = interp or _LAST_INTERPRETER
                if isinstance(fn, JSFunction):
                    if call_interp:
                        try:
                            if context.get('_interp') is None:
                                context['_interp'] = call_interp
                        except Exception:
                            pass
                        fn.call(call_interp, None, list(it_args or ()))
                elif callable(fn):
                    try:
                        fn(*list(it_args or ()))
                    except Exception:
                        pass
                if tid in intervals:
                    timers.append(('__interval__', tid))
                executed_count += 1
                continue

            # Regular timer
            fn, args = item
            _check_timer_guard(fn)
            if isinstance(fn, JSFunction):
                call_interp = interp or _LAST_INTERPRETER
                if call_interp:
                    try:
                        if context.get('_interp') is None:
                            context['_interp'] = call_interp
                    except Exception:
                        pass
                    fn.call(call_interp, None, list(args or ()))
            elif callable(fn):
                try:
                    fn(*list(args or ()))
                except Exception:
                    pass
            executed_count += 1
            
        except Exception as e:
            if isinstance(e, RuntimeError) and "recursion limit" in str(e).lower():
                raise
            pass
    
    # Update total execution counter
    context['_total_timer_executions'] = total_executed + executed_count
    
    # **NEW: Clear the pending events batch tracker for next cycle**
    try:
        context.pop('_pending_events', None)
    except Exception:
        pass

# --- Public helpers ---------------------------------------------------------
def run_in_interpreter(src: str, interp) -> Any:
    """Evaluate `src` in an existing Interpreter (preserves variables and function bindings)."""
    ast = parse(src)
    return interp.run_ast(ast)

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
    Math = { 'random': lambda: random.random(), 'floor': lambda x: int(x)//1 }

    # context - created mutable to allow setTimeout closure reference
    context_ref = {
        'console': {'log': _log},
        'Math': Math,
        'document': document,
        '_timers': [],
        'setTimeout': setTimeout
    }
    context_ref['undefined'] = undefined

        # minimal environment metadata helpful to many libraries (jQuery, gtag)
    try:
        # window/globalThis refer to the context dict itself (document already present)
        context_ref.setdefault('window', context_ref)
        context_ref.setdefault('globalThis', context_ref)
        # minimal location object (string fields only)
        context_ref.setdefault('location', {'href': '', 'protocol': '', 'host': '', 'hostname': '', 'pathname': ''})
        # navigator stub
        context_ref.setdefault('navigator', {'userAgent': 'jsmini/0'})
    except Exception:
        pass
    # --- Host shims to satisfy common tag runtime checks (avoid tight re-check loops) ---
    # Real environments expose `window.google_tags_first_party` and `google_tag_data`.
    # Provide minimal sane defaults so minified code paths that probe these don't loop.
    context_ref['google_tags_first_party'] = []           # empty list of first-party container ids
    # google_tag_data.tidr is used by Pj() to store container state; give a minimal holder
    context_ref['google_tag_data'] = {'tidr': {}}
    context_ref['__flushDom'] = lambda: (document.get('forceRedraw')() if callable(document.get('forceRedraw')) else None)

    # Prefer centralized builtins module; register early so consumers of the context get canonical builtins.
    # Fall back to very small safe stubs when js_builtins is missing or registration fails.
    
   
    js_builtins.register_builtins(context_ref, JSFunction)
    context_ref["_builtins_registered"] = True

    # DOM mutation logger: opt-in
    def _enable_dom_log(verbose: bool = False):
        context_ref['_dom_changes'] = []
        context_ref['_dom_log_verbose'] = bool(verbose)

        def _dom_log(element: Any, op: str, details: Dict[str, Any]):
            try:
                entry = {
                    'op': op,
                    'tag': getattr(element, 'tagName', None),
                    'id': getattr(element, 'id', None),
                    'path': element._dom_path() if hasattr(element, '_dom_path') else None,
                    'details': details or {}
                }
                context_ref['_dom_changes'].append(entry)
                # Optional debug stream (only when verbose)
                if verbose:
                    try:
                        _log(f"[jsmini.trace][dom] {op} {entry.get('path')} {details}")
                    except Exception:
                        pass
            except Exception:
                pass

        # bind logger to document and existing body
        try:
            document['__dom_log_fn'] = _dom_log
            body = document.get('body')
            if isinstance(body, Element):
                body._dom_log = _dom_log
        except Exception:
            pass

    # expose toggles/accessors
    context_ref['__enableDomLog'] = _enable_dom_log
    context_ref['getDomChanges'] = lambda: list(context_ref.get('_dom_changes', []))

    # Helper to set host later (used by run_scripts)
    context_ref['__attachHost'] = lambda h: (
        document.get('__setHost') and document['__setHost'](h)
    )
    
    return context_ref
def run(src: str, context: Optional[Dict[str,Any]]=None):
    """Backward-compatible: Parse and execute JS source string in a fresh interpreter with given context dict."""
    ast = parse(src)
    interp = Interpreter(context or {})
    # expose interpreter on context for timers/constructors
    if context is not None:
        context['_interp'] = interp
        # ensure context['undefined'] refers to interpreter sentinel so builtins see correct undefined
        context['undefined'] = undefined
    return interp.run_ast(ast)

def run_with_interpreter(src: str, context: Optional[Dict[str,Any]]=None):
    """Run and return (result, interpreter). Caller can later call run_timers_from_context(context)."""
    ast = parse(src)
    ctx = context or {}
    interp = Interpreter(ctx)
    ctx['_interp'] = interp
    # ensure context['undefined'] refers to the interpreter sentinel
    ctx['undefined'] = undefined
    res = interp.run_ast(ast)
    return res, interp

def run_timers(context: Dict[str,Any]):
    """Convenience wrapper to execute stored timers in given context."""
    run_timers_from_context(context)

def dump_tokens(src: str, start_index: int, count: int = 40) -> str:
    """
    Return a readable token dump around `start_index`.
    start_index may be negative (interpreted as 0).
    """
    try:
        raw = tokenize(src)
    except Exception as e:
        return f"tokenize() failed: {e}"
    toks = [(t, v, s, e) for (t, v, s, e) in raw]
    n = len(toks)
    idx = max(0, start_index)
    lo = max(0, idx - count // 2)
    hi = min(n, lo + count)
    lines = []
    lines.append(f"Tokens {lo}..{hi-1} (total {n}):")
    for i in range(lo, hi):
        t, v, s, e = toks[i]
        snippet = src[s:e].replace('\n', '\\n')
        markers = '<--' if i == idx else ''
        lines.append(f"{i:4}: {t:7} {v!r}  [{s}:{e}]  {snippet} {markers}")
    return "\n".join(lines)

def diagnose_parse(src: str, radius_tokens: int = 24, radius_chars: int = 80) -> str:
    """
    Try parsing and on SyntaxError return:
      - parser index
      - token dump around index
      - source snippet with caret
    Use this to quickly locate why the parser expected a different token.
    """
    try:
        # attempt parse (this will raise on SyntaxError)
        parse(src)
        return "Parsed successfully (no error)"
    except SyntaxError as se:
        # Try to get parser index by running Parser and catching the same error position
        try:
            # produce raw tokens with positions
            raw = tokenize(src)
            toks = [(t, v) for (t, v, s, e) in raw]
            positions = [(s, e) for (t, v, s, e) in raw]
            p = Parser(toks)
            try:
                p.parse_program()
            except SyntaxError:
                idx = getattr(p, 'i', None)
                if idx is None:
                    raise
                start, end = positions[idx] if idx < len(positions) else (0, 0)
                token = toks[idx] if idx < len(toks) else ('', '')
                token_ctx = dump_tokens(src, idx, count=radius_tokens)
                # source char snippet
                start_char = max(0, start - radius_chars)
                end_char = min(len(src), end + radius_chars)
                text_snip = src[start_char:end_char].replace('\n', '\\n')
                caret = ' ' * (start - start_char) + '^' * max(1, end - start)
                return (
                    f"SyntaxError: {se}\nParser token index: {idx} token={token!r}\n\n"
                    f"{token_ctx}\n\nSource context:\n...{text_snip}...\n{caret}"
                )
        except Exception:
            pass
        # fallback: return original message
        return f"SyntaxError (no parser index): {se}"

# quick test when executed as script
if __name__ == '__main__':
    ctx = make_context()
    run("var x = 2; function f(n){ return n*3; } console.log('res', f(x));", ctx)
    # demonstration setTimeout
    run("setTimeout(function(){ console.log('delayed', 1) }, 0);", ctx)
    run_timers(ctx)