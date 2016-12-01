import logging
from threading import Lock
from builtins import object

from pyparsing import (
    ParserElement,
    Forward,
    Literal, Word,
    Combine, Group, Optional,
    nums, alphanums, alphas, sglQuotedString,
    delimitedList,
    opAssoc, oneOf)

try:
    from pyparsing import infixNotation
except ImportError:
    # For old versions of PyParsing
    from pyparsing import operatorPrecedence as infixNotation


from brabbel.functions import functions
from brabbel.nodes import (
    Const, Func, Variable,
    Call,
    Add, Sub, Mul, Div,
    In, List,
    Not, And, Or,
    LT, GT, LE, GE, EQ, NE)


"""
number    :: '0'..'9'+
string    :: '0'..'9''a'..'z''_'+
variable  :: '$' string

"""
log = logging.getLogger(__name__)
ParserElement.enablePackrat()

########################################################################
#                               Helpers                                #
########################################################################


def _str(s):
    return unicode(s.strip("'"))


def _number(s):
    try:
        return int(s)
    except ValueError:
        return float(s)


def _make_func(s, loc, toks):
    name = toks['name']
    args = toks['args']
    fn = functions[name]
    arity = len(args)
    if arity == 1:
        return Call(fn, args[0])
    return Func(fn, args[:])


binaries = {
    'and': And,
    'or': Or,
    '+': Add,
    '-': Sub,
    '*': Mul,
    '/': Div,
    '<': LT,
    'lt': LT,
    '>': GT,
    'gt': GT,
    '<=': LE,
    'le': LE,
    '>=': GE,
    'ge': GE,
    '==': EQ,
    'eq': EQ,
    '!=': NE,
    'ne': NE,
    'in': In }

unaries = { 'not': Not }


def _make_binary(s, loc, toks):
    toks = toks[0]
    a, op, b = toks[0], toks[1], toks[2]

    a = binaries[op](a, b)

    remaining = iter(toks[3:])
    while True:
        op = next(remaining, None)
        if op is None:
            break
        b = next(remaining)
        a = binaries[op](a, b)

    return a


def _make_unary(s, loc, toks):
    toks = toks[0]
    return unaries[toks[0]](toks[1])


########################################################################
#                                ATOMS                                 #
########################################################################
lpar = Literal("(")
lbr = Literal("[")
rpar = Literal(")")
rbr = Literal("]")
lquote = Literal("'")
rquote = Literal("'")
number = Combine(Optional("-") + Word(nums + '.'))
# TODO: Remove "-" from list of allowed chars. Is only here for
# compatibility. (None) <2014-10-28 14:04>
variable = Combine("$" + Word(alphanums + "_" + "-" + "."))
# FIXME: sglquotedstring will fail if the string contains a single
# quote. (ti) <2015-09-29 13:54>
string = sglQuotedString.copy()
identifier = Word(alphas + "_")
none = Literal("None")
true = Literal("True")
false = Literal("False")
atom = Forward()
infix = infixNotation(atom,
    [
    ('not', 1, opAssoc.RIGHT, _make_unary),
    (oneOf('* /'), 2, opAssoc.LEFT, _make_binary),
    (oneOf('+ -'), 2, opAssoc.LEFT, _make_binary),
    (oneOf('> gt >= ge < lt <= le != ne == eq'),
        2, opAssoc.LEFT, _make_binary),
    ('and', 2, opAssoc.LEFT, _make_binary),
    ('or', 2, opAssoc.LEFT, _make_binary),
    ('in', 2, opAssoc.LEFT, _make_binary),
    ])
dellist = delimitedList(Optional(atom))
listing = lbr.suppress() + dellist + rbr.suppress()
function = identifier.setResultsName('name') + lpar.suppress() + Group(
        Optional(delimitedList(atom))).setResultsName("args") + rpar.suppress()
atom <<= listing | number | string | variable | true | false | none | function

_false = Const(False)
_true = Const(True)

number.setParseAction(lambda t: Const(_number(t[0])))
variable.setParseAction(lambda t: Variable(t[0].strip("$")))
string.setParseAction(lambda t: Const(_str(t[0])))
none.setParseAction(lambda t: _false)
false.setParseAction(lambda t: _false)
true.setParseAction(lambda t: _true)
dellist.setParseAction(lambda s, l, t: List(t[:]))
function.setParseAction(_make_func)
atom.setParseAction(lambda s, l, t: t[0])

class Parser(object):

    """Parser class for python expression."""

    lock = Lock()

    def __init__(self):
        """@todo: to be defined1. """
        pass

    def parse(self, expr):
        """Returns the BNF-Tree of the given expression

        :expr: String of the expression
        :returns: Returns the parsed BNF form the the expression

        """
        try:
            with Parser.lock:
                return infix.parseString(expr)
        except Exception:
            log.exception("Error on parsing %s" % expr)
