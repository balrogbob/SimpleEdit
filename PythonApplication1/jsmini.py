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
import math
import html
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple
try:
    import js_builtins
except Exception:
    js_builtins = None
# --- Tokenizer --------------------------------------------------------------
Token = Tuple[str, str]  # (type, value)

_LAST_INTERPRETER = None

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

    def call(self, interpreter, this, args):
        """
        Invoke this JSFunction.

        interpreter may be:
          - an Interpreter instance (normal)
          - a context dict containing an Interpreter under '_interp' (host helpers)
          - (fallback) missing/incorrectly passed: try module-level _LAST_INTERPRETER

        This function is defensive because native built-ins and host code sometimes
        call JSFunction.call with different shapes during interop.
        """
        interp = interpreter
        try:
            # Common: caller passed a context dict instead of Interpreter
            if not hasattr(interp, '_eval_stmt'):
                if isinstance(interp, dict):
                    interp = interp.get('_interp', interp)
                # Some callers stash interpreter on `this` (rare)
                if not hasattr(interp, '_eval_stmt') and isinstance(this, dict):
                    interp = this.get('_interp', interp)
        except Exception:
            pass

        # Last-resort: use module-level last-interpreter if available.
        global _LAST_INTERPRETER
        if not hasattr(interp, '_eval_stmt'):
            if _LAST_INTERPRETER is not None and hasattr(_LAST_INTERPRETER, '_eval_stmt'):
                interp = _LAST_INTERPRETER

        if not hasattr(interp, '_eval_stmt'):
            raise RuntimeError(
                f"JSFunction.call expected Interpreter instance as first arg (or context with '_interp'); "
                f"got {type(interpreter)!r}"
            )

        # Native implementation takes precedence
        if self.native_impl is not None:
            try:
                return self.native_impl(interp, this, list(args or ()))
            except ReturnExc as r:
                return r.value
            except Exception:
                return undefined

        # Scripted function execution
        local = Env(self.env)
        # bind `this` into the function local scope
        local.set_local('this', this)
        for i, p in enumerate(self.params):
            local.set_local(p, args[i] if i < len(args) else undefined)
        if self.name:
            local.set_local(self.name, self)

        # push function name onto interpreter call-stack (for diagnostics)
        fn_label = self.name or '<anon>'
        try:
            # ensure interpreter has call-stack attributes
            if not hasattr(interp, '_call_stack'):
                interp._call_stack = []
            interp._call_stack.append(fn_label)
        except Exception:
            pass

        try:
            try:
                return interp._eval_stmt(self.body, local, this)
            except ReturnExc as r:
                return r.value
        finally:
            # pop call-stack safely
            try:
                if hasattr(interp, '_call_stack') and interp._call_stack:
                    interp._call_stack.pop()
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
        # runtime instrumentation: counters and call stack to diagnose hangs
        # sensible default; increase if your script legitimately runs many statements
        self._exec_count = 0
        self._exec_limit = 200_000
        self._call_stack: List[str] = []
        self._trace = False  # set True for periodic progress prints
        # record last-created interpreter so JSFunction.call can recover it as a best-effort fallback
        global _LAST_INTERPRETER
        try:
            _LAST_INTERPRETER = self
        except Exception:
            _LAST_INTERPRETER = None


    def _prop_get(self, obj, key):
        """Prototype-aware property lookup. Returns `undefined` when not found."""
        try:
            # dict-like JS objects: walk __proto__ chain
            if isinstance(obj, dict):
                cur = obj
                while cur is not None:
                    if key in cur:
                        return cur[key]
                    cur = cur.get('__proto__', None)
                return undefined

            # JSFunction instances: prefer prototype lookup (JS semantics).
            # Do not return Python methods on the JSFunction instance object.
            if isinstance(obj, JSFunction):
                try:
                    # instance prototype (per-instance) then class-level prototype
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
                # fallthrough: if not found on prototypes, do not expose Python methods as properties;
                # return undefined to preserve JS semantics.
                return undefined

            # fallback for host/python objects: use attribute
            return getattr(obj, key, undefined)
        except Exception:
            return undefined

    def _prop_set(self, obj, key, value):
        """Interpreter method: set own property on object (no prototype walk)."""
        try:
            if isinstance(obj, dict):
                obj[key] = value
                return True
            setattr(obj, key, value)
            return True
        except Exception:
            return False

    def run_ast(self, ast):
        return self._eval_prog(ast, self.global_env)

    def _eval_prog(self, node, env):
        assert node[0] == 'prog'
        res = undefined
        try:
            for st in node[1]:
                res = self._eval_stmt(st, env, None)
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
                    elif isinstance(lhs, tuple) and lhs[0] == 'get':
                        try:
                            tgt_obj = self._eval_expr(lhs[1], local, this)
                            prop_node = lhs[2]
                            if prop_node[0] == 'id':
                                prop_name = prop_node[1]
                            else:
                                prop_name = self._eval_expr(prop_node, local, this)
                            if isinstance(tgt_obj, dict):
                                tgt_obj[prop_name] = k
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

        # Object literal: ('obj', [(key, val_node), ...])
        if t == 'obj':
            _, props = node
            out = {}
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
            out: Dict[str, Any] = {}
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

            return self._apply_bin(op, lhs, rhs)

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
                # prototype-aware lookup (includes own properties)
                return self._prop_get(obj, key)
            except Exception:
                return undefined

        if t == 'call':
            _, callee_node, args_nodes = node

            # member call: callee_node can be ('get', target, prop)
            receiver = None
            fn_val = None
            if isinstance(callee_node, tuple) and callee_node[0] == 'get':
                # evaluate receiver object
                receiver = self._eval_expr(callee_node[1], env, this)
                prop_node = callee_node[2]
                if prop_node[0] == 'id':
                    fn_val = self._prop_get(receiver, prop_node[1])
                else:
                    fn_val = self._eval_expr(prop_node, env, this)
            else:
                fn_val = self._eval_expr(callee_node, env, this)

            args = [self._eval_expr(a, env, this) for a in args_nodes]

            # JSFunction (scripted/native)
            if isinstance(fn_val, JSFunction):
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
                    while cur is not None:
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
        # children is a JSList so JS code can read `.length`
        self.children: JSList = JSList()
        self.id: Optional[str] = None
        self.parent = None  # parentNode reference for DOM manipulations
        # simple classList representation (exposes add/remove/contains/toggle)
        self._class_set = set()

    def setAttribute(self, k: str, v: Any) -> None:
        self.attrs[k] = v
        if k == 'id':
            self.id = v
        if k == 'class':
            try:
                # keep classSet in sync with attribute
                self._class_set = set(str(v).split())
            except Exception:
                self._class_set = set()

    def appendChild(self, child: Any) -> None:
        # keep underlying storage and expose JS-like API
        # set parent pointer for element children
        try:
            if isinstance(child, Element):
                child.parent = self
            self.children.append(child)
        except Exception:
            # fallback append
            try:
                self.children.append(child)
            except Exception:
                pass

    def removeChild(self, child: Any) -> None:
        """Remove a child (no exception thrown on failure)."""
        try:
            # support JSList and Python lists
            if isinstance(self.children, JSList):
                lst = list(self.children._list)
                if child in lst:
                    lst.remove(child)
                    self.children = JSList(lst)
                    try:
                        if isinstance(child, Element):
                            child.parent = None
                    except Exception:
                        pass
            else:
                if child in self.children:
                    self.children.remove(child)
                    try:
                        if isinstance(child, Element):
                            child.parent = None
                    except Exception:
                        pass
        except Exception:
            pass

    def insertBefore(self, newNode: Any, referenceNode: Any) -> None:
        """Insert newNode before referenceNode; append if referenceNode not found."""
        try:
            lst = self.children._list
            try:
                idx = lst.index(referenceNode)
            except ValueError:
                idx = len(lst)
            if isinstance(newNode, Element):
                newNode.parent = self
            lst.insert(idx, newNode)
        except Exception:
            try:
                self.appendChild(newNode)
            except Exception:
                pass

    def replaceChild(self, newNode: Any, oldNode: Any) -> None:
        """Replace oldNode with newNode."""
        try:
            lst = self.children._list
            try:
                idx = lst.index(oldNode)
                if isinstance(newNode, Element):
                    newNode.parent = self
                lst[idx] = newNode
                try:
                    if isinstance(oldNode, Element):
                        oldNode.parent = None
                except Exception:
                    pass
            except ValueError:
                # fallback: append
                if isinstance(newNode, Element):
                    newNode.parent = self
                lst.append(newNode)
        except Exception:
            pass

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
        """Replace children with a single text node."""
        try:
            self.children = JSList([str(val)])
        except Exception:
            pass

    @property
    def innerHTML(self) -> str:
        """Simple serializer of children to an HTML-ish string (minimal)."""
        try:
            parts = []
            for c in self.children:
                if isinstance(c, Element):
                    # Minimal tag + text serialization (does not preserve attributes beyond id/class)
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
        """
        innerHTML setter: parse a small, safe subset of HTML into Element/text children.
        - No script/style execution.
        - Supports simple tags and text nodes.
        """
        try:
            raw = str(html_str or '')
            nodes = _parse_inner_html_fragment(raw)
            # attach parent links for parsed Element nodes
            for n in nodes:
                if isinstance(n, Element):
                    n.parent = self
            self.children = JSList(nodes)
        except Exception:
            # fallback: replace with raw text (safe)
            try:
                self.children = JSList([str(html_str)])
            except Exception:
                pass

    @property
    def classList(self):
        """Expose a simple classList object with add/remove/contains/toggle methods."""
        el = self

        def _add(this, *cls_names):
            try:
                for nm in cls_names:
                    el._class_set.add(str(nm))
                el.attrs['class'] = ' '.join(el._class_set)
            except Exception:
                pass

        def _remove(this, *cls_names):
            try:
                for nm in cls_names:
                    el._class_set.discard(str(nm))
                el.attrs['class'] = ' '.join(el._class_set)
            except Exception:
                pass

        def _contains(this, name):
            try:
                return str(name) in el._class_set
            except Exception:
                return False

        def _toggle(this, name, force=None):
            try:
                n = str(name)
                if force is None:
                    if n in el._class_set:
                        el._class_set.remove(n)
                        present = False
                    else:
                        el._class_set.add(n)
                        present = True
                else:
                    if bool(force):
                        el._class_set.add(n); present = True
                    else:
                        el._class_set.discard(n); present = False
                el.attrs['class'] = ' '.join(el._class_set)
                return present
            except Exception:
                return False

        # Return a plain dict-like object with callables; JS code will call these via the interpreter.
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

def make_dom_shim():
    registry: Dict[str, Element] = {}
    root = Element('document')
    body = Element('body')
    root.body = body

    # helper: simple CSS selector matcher (supports "#id", ".class", "tag", "[attr=value]")
    def _matches(el: Element, selector: str) -> bool:
        try:
            selector = selector.strip()
            if not selector:
                return False
            if selector.startswith('#'):
                return (el.id == selector[1:])
            if selector.startswith('.'):
                cls = selector[1:]
                classes = (el.attrs.get('class') or '').split()
                return cls in classes
            # attribute selector [attr=value] or [attr]
            m = re.match(r'^\[([\w:-]+)(?:=(["\']?)(.*?)\2)?\]$', selector)
            if m:
                attr = m.group(1)
                val = m.group(3)
                if attr not in el.attrs:
                    return False if val is not None else False
                if val is None:
                    return True
                return str(el.attrs.get(attr)) == val
            # tag name
            return el.tagName.lower() == selector.lower()
        except Exception:
            return False

    def _query_within_single(root_el: Element, selector: str, many: bool):
        # Support simple selectors; if selector contains spaces, treat as descendant by splitting and narrowing
        try:
            parts = [p.strip() for p in selector.split() if p.strip()]
            candidates = [root_el]
            for part in parts:
                new_candidates = []
                for c in candidates:
                    # traverse subtree (breadth-first)
                    stack = [c]
                    while stack:
                        node = stack.pop(0)
                        for ch in (node.children if isinstance(node.children, JSList) else []):
                            if isinstance(ch, Element):
                                if _matches(ch, part):
                                    new_candidates.append(ch)
                                stack.append(ch)
                candidates = new_candidates
            if many:
                return JSList(candidates)
            return candidates[0] if candidates else None
        except Exception:
            return JSList([]) if many else None

    def querySelector(sel: str) -> Optional[Element]:
        # support comma-separated selectors: return first match in selector-list order
        try:
            for part in (s.strip() for s in (sel or '').split(',') if s.strip()):
                found = _query_within_single(body, part, many=False)
                if found:
                    return found
            return None
        except Exception:
            return None

    def querySelectorAll(sel: str):
        # support comma-separated selectors: union of results, preserve order, avoid duplicates
        try:
            seen = set()
            out: List[Any] = []
            for part in (s.strip() for s in (sel or '').split(',') if s.strip()):
                res = _query_within_single(body, part, many=True)
                if not res:
                    continue
                for e in list(res._list if isinstance(res, JSList) else []):
                    # identify elements by id() to avoid Python unhashable Elements - use id()
                    uid = ('el', id(e))
                    if uid in seen:
                        continue
                    seen.add(uid)
                    out.append(e)
            return JSList(out)
        except Exception:
            return JSList([])

    def createElement(tag: str) -> Element:
        return Element(tag)

    def getElementById(idv: str) -> Optional[Element]:
        # naive walk
        if body.id == idv:
            return body
        for c in body.children:
            if isinstance(c, Element) and c.id == idv:
                return c
            # deep search
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
        body.appendChild(el)

    # document is a dict (so document['body'] resolves to Element via dict.get in evaluator)
    document = {
        'createElement': createElement,
        'getElementById': getElementById,
        'querySelector': querySelector,
        'querySelectorAll': querySelectorAll,
        'body': body,
        'appendChild': append_to_body
    }
    return document

# --- timers / scheduler -----------------------------------------------------
def make_timers_container():
    return {'_timers': []}  # timers: list of (fn, args)

def run_timers_from_context(context: Dict[str,Any]):
    """Run queued timers stored in context['_timers'].

    Behavior:
    - Processes a snapshot of the current timers queue so newly re-queued intervals
      are not executed in the same run.
    - Supports plain timers stored as (fn, args).
    - Supports interval markers stored as ('__interval__', id) where a mapping of
      active intervals may live in `context['_intervals']`. If an interval id is
      still active after execution it will be re-queued for the next cycle.
    - When calling JSFunction instances, prefer the interpreter stored at
      context['_interp'] or fall back to module-level _LAST_INTERPRETER. If an
      interpreter is found, ensure it is also stored into context['_interp'] so
      JSFunction.call can discover it.
    """
    # Ensure timers list exists and operate on the actual list in context.
    timers = context.setdefault('_timers', [])
    # Prefer interpreter from context; fall back to last-created interpreter.
    interp = context.get('_interp') or _LAST_INTERPRETER
    if interp is not None and context.get('_interp') is None:
        try:
            context['_interp'] = interp
        except Exception:
            pass

    # Intervals mapping (optional). js_builtins should store active intervals here
    # if it wants run_timers to be able to look them up.
    intervals = context.get('_intervals', None)

    # Process a snapshot (initial length) so re-queued intervals are not processed
    # in this same invocation.
    initial_len = len(timers)
    for _ in range(initial_len):
        item = timers.pop(0)
        try:
            # Special interval marker: ('__interval__', tid)
            if isinstance(item, tuple) and len(item) == 2 and item[0] == '__interval__':
                tid = item[1]
                if not intervals:
                    # No interval registry available; ignore marker.
                    continue
                entry = intervals.get(tid)
                if not entry:
                    # interval was cleared
                    continue
                fn, it_args = entry  # it_args expected to be a sequence/tuple
                # Ensure interpreter available for JSFunction.call
                call_interp = interp or _LAST_INTERPRETER
                if isinstance(fn, JSFunction):
                    if call_interp:
                        # make sure context has interp for nested JSFunction.call lookup
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
                # If interval still active, re-queue marker for next cycle
                if tid in intervals:
                    timers.append(('__interval__', tid))
                continue

            # Normal timer entry: (fn, args)
            fn, args = item
            # JSFunction: call with interpreter as required
            if isinstance(fn, JSFunction):
                call_interp = interp or _LAST_INTERPRETER
                if call_interp:
                    try:
                        if context.get('_interp') is None:
                            context['_interp'] = call_interp
                    except Exception:
                        pass
                    fn.call(call_interp, None, list(args or ()))
                else:
                    # no interpreter available - skip JSFunction invocation
                    pass
            # Python callable
            elif callable(fn):
                try:
                    fn(*list(args or ()))
                except Exception:
                    pass
        except Exception:
            # swallow errors from timer callbacks (best-effort)
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
    context_ref['undefined'] = undefined
    # --- Host shims to satisfy common tag runtime checks (avoid tight re-check loops) ---
    # Real environments expose `window.google_tags_first_party` and `google_tag_data`.
    # Provide minimal sane defaults so minified code paths that probe these don't loop.
    context_ref['google_tags_first_party'] = []           # empty list of first-party container ids
    # google_tag_data.tidr is used by Pj() to store container state; give a minimal holder
    context_ref['google_tag_data'] = {'tidr': {}}
    # --- Register minimal built-ins: Array and Object -----------------------
    # Array constructor (native): ensures `this` is an object with length and optional initial items
    def _array_ctor(interp, this, args):
        # this is provided by `new` as a dict and already has '__proto__' set by interpreter
        this.setdefault('length', 0)
        # if called with arguments, push them
        if args:
            # single numeric arg sets length (simplified)
            if len(args) == 1 and isinstance(args[0], (int, float)):
                this['length'] = int(args[0])
            else:
                # push provided values
                push_fn = Arr.prototype.get('push')
                if isinstance(push_fn, JSFunction):
                    push_fn.call(interp, this, args)
        return this

    def _array_push(interp, this, args):
        length = int(this.get('length', 0) or 0)
        for v in args:
            this[str(length)] = v
            length += 1
        this['length'] = length
        return length

    def _array_pop(interp, this, args):
        length = int(this.get('length', 0) or 0)
        if length == 0:
            return undefined
        idx = length - 1
        key = str(idx)
        val = this.get(key, undefined)
        if key in this:
            del this[key]
        this['length'] = idx
        return val

    # Object constructor (native) - returns plain object; when used with `new` interpreter sets __proto__
    def _object_ctor(interp, this, args):
        # ensure object exists and return it
        return this

    # Object.create static: Object.create(proto) -> new object whose __proto__ is proto
    def _object_create(interp, this, args):
        proto = args[0] if args else None
        obj = {'__proto__': proto}
        return obj

    def _object_keys(interp, this, args):
        target = args[0] if args else None
        if isinstance(target, dict):
            return [k for k in target.keys() if k != '__proto__']
        return []

    # Create JSFunction constructors and attach prototype methods
    Arr = JSFunction(params=[], body=None, env=None, name='Array', native_impl=_array_ctor)
    # --- Array prototype: add common methods (forEach, map, filter, slice, splice, indexOf, concat)
    def _array_for_each(interp, this, args):
        cb = args[0] if args else None
        this_arg = args[1] if len(args) > 1 else None
        if not cb:
            return undefined
        # iterate over numeric keys 0..length-1, skipping holes
        length = int(this.get('length', 0) or 0)
        for i in range(length):
            key = str(i)
            if key not in this:
                continue
            val = this.get(key)
            # call callback: callback.call(interp, thisArg, [val, i, this])
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
        return undefined

    def _array_map(interp, this, args):
        cb = args[0] if args else None
        this_arg = args[1] if len(args) > 1 else None
        length = int(this.get('length', 0) or 0)
        res = {'__proto__': Arr.prototype, 'length': 0}
        out_index = 0
        if not cb:
            return res
        for i in range(length):
            key = str(i)
            if key not in this:
                # preserve holes in a minimal way: skip in result (JS normally creates hole)
                continue
            val = this.get(key)
            if isinstance(cb, JSFunction):
                rv = cb.call(interp, this_arg, [val, i, this])
            elif callable(cb):
                try:
                    rv = cb(this_arg, val, i, this) if this_arg is not None else cb(val, i, this)
                except Exception:
                    rv = undefined
            else:
                rv = undefined
            res[str(out_index)] = rv
            out_index += 1
        res['length'] = out_index
        return res

    def _array_filter(interp, this, args):
        cb = args[0] if args else None
        this_arg = args[1] if len(args) > 1 else None
        length = int(this.get('length', 0) or 0)
        res = {'__proto__': Arr.prototype, 'length': 0}
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
        res['length'] = out_index
        return res

    def _array_slice(interp, this, args):
        length = int(this.get('length', 0) or 0)
        start = int(args[0]) if args else 0
        end = int(args[1]) if len(args) > 1 else length
        # normalize negatives
        if start < 0:
            start = max(length + start, 0)
        else:
            start = min(start, length)
        if end < 0:
            end = max(length + end, 0)
        else:
            end = min(end, length)
        res = {'__proto__': Arr.prototype, 'length': 0}
        out_index = 0
        for i in range(start, max(start, end)):
            key = str(i)
            if key in this:
                res[str(out_index)] = this.get(key)
            out_index += 1
        res['length'] = out_index
        return res

    def _array_splice(interp, this, args):
        length = int(this.get('length', 0) or 0)
        if not args:
            # nothing to delete or insert
            return {'__proto__': Arr.prototype, 'length': 0}
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
        # collect removed
        removed = {'__proto__': Arr.prototype, 'length': 0}
        rem_idx = 0
        for i in range(start, start + delete_count):
            k = str(i)
            if k in this:
                removed[str(rem_idx)] = this.get(k)
            rem_idx += 1
        removed['length'] = rem_idx
        # build new backing mapping
        new_obj = {}
        # copy items before start
        idx = 0
        for i in range(0, start):
            k = str(i)
            if k in this:
                new_obj[str(idx)] = this.get(k)
            idx += 1
        # insert new items
        for item in inserts:
            new_obj[str(idx)] = item
            idx += 1
        # copy tail after deleted segment
        for i in range(start + delete_count, length):
            k = str(i)
            if k in this:
                new_obj[str(idx)] = this.get(k)
            idx += 1
        new_obj['__proto__'] = this.get('__proto__', Arr.prototype)
        new_obj['length'] = idx
        # replace contents of this dict in-place to preserve identity
        # clear existing keys except __proto__
        proto = this.get('__proto__', None)
        keys = [k for k in list(this.keys()) if k != '__proto__']
        for k in keys:
            del this[k]
        # copy new keys into this
        for k, v in new_obj.items():
            this[k] = v
        # restore proto explicitly (already set by copy above)
        if proto is not None:
            this['__proto__'] = proto
        return removed

    def _array_index_of(interp, this, args):
        search = args[0] if args else None
        from_index = int(args[1]) if len(args) > 1 else 0
        length = int(this.get('length', 0) or 0)
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
        res = {'__proto__': Arr.prototype, 'length': 0}
        out_idx = 0
        # helper to append an element
        def _append(val):
            nonlocal out_idx
            res[str(out_idx)] = val
            out_idx += 1
        # append this array elements
        length = int(this.get('length', 0) or 0)
        for i in range(length):
            k = str(i)
            if k in this:
                _append(this.get(k))
        # append arguments: if arg is array-like (dict with length) flatten, else push value
        for a in args:
            if isinstance(a, dict) and 'length' in a:
                alen = int(a.get('length', 0) or 0)
                for j in range(alen):
                    kk = str(j)
                    if kk in a:
                        _append(a.get(kk))
            else:
                _append(a)
        res['length'] = out_idx
        return res

    # Register JS built-ins if available (idempotent)
    try:
        if js_builtins is not None and not context_ref.get("_builtins_registered"):
            # register_builtins(context, JSFunction) is expected by js_builtins
            js_builtins.register_builtins(context_ref, JSFunction)
            context_ref["_builtins_registered"] = True
    except Exception:
        # non-fatal: keep context creation robust even if built-ins fail to register
        pass
    # attach to Arr.prototype
    Arr.prototype['push'] = JSFunction(params=[], body=None, env=None, name='push', native_impl=lambda interp, this, a: _array_push(interp, this, a))
    Arr.prototype['pop'] = JSFunction(params=[], body=None, env=None, name='pop', native_impl=lambda interp, this, a: _array_pop(interp, this, a))
    Arr.prototype['forEach'] = JSFunction(params=[], body=None, env=None, name='forEach', native_impl=_array_for_each)
    Arr.prototype['map'] = JSFunction(params=[], body=None, env=None, name='map', native_impl=_array_map)
    Arr.prototype['filter'] = JSFunction(params=[], body=None, env=None, name='filter', native_impl=_array_filter)
    Arr.prototype['slice'] = JSFunction(params=[], body=None, env=None, name='slice', native_impl=_array_slice)
    Arr.prototype['splice'] = JSFunction(params=[], body=None, env=None, name='splice', native_impl=_array_splice)
    Arr.prototype['indexOf'] = JSFunction(params=[], body=None, env=None, name='indexOf', native_impl=_array_index_of)
    Arr.prototype['concat'] = JSFunction(params=[], body=None, env=None, name='concat', native_impl=_array_concat)
    # Object constructor
    Obj = JSFunction(params=[], body=None, env=None, name='Object', native_impl=_object_ctor)
    # Attach static methods as attributes on the function object (Object.create, Object.keys)
    setattr(Obj, 'create', JSFunction(params=[], body=None, env=None, name='create', native_impl=lambda interp, this, a: _object_create(interp, this, a)))
    setattr(Obj, 'keys', JSFunction(params=[], body=None, env=None, name='keys', native_impl=lambda interp, this, a: _object_keys(interp, this, a)))

    # Expose constructors on global context
    context_ref['Array'] = Arr
    context_ref['Object'] = Obj
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