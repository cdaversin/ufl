"""Defines symbol and variable constructs."""

from __future__ import absolute_import

__authors__ = "Martin Sandve Alnes"
__date__ = "2008-05-20 -- 2008-10-27"

from collections import defaultdict
from .common import Counted
from .output import ufl_assert
from .base import UFLObject, Terminal

class Variable(Terminal, Counted):
    """A Variable is a representative for another expression.
    
    It will be used by the end-user mainly for:
    - Defining a quantity to differentiate w.r.t. using diff.
    
    Internally, it is also used for:
    - Marking good spots to split an expression for optimized computation.
    - Reuse of expressions during e.g. automatic differentation.
    """
    __slots__ = ("_expression", "_diffcache")
    _globalcount = 0
    def __init__(self, expression, count=None):
        Counted.__init__(self, count)
        ufl_assert(isinstance(expression, UFLObject), "Expecting an UFLObject.")
        self._expression = expression
        self._diffcache = defaultdict(list)
    
    def operands(self):
        return ()
    
    def free_indices(self):
        return self._expression.free_indices()
    
    def shape(self):
        return self._expression.shape()
    
    def __eq__(self, other):
        return isinstance(other, Variable) and self._count == other._count
        
    def __str__(self):
        return "Variable(%s, %d)" % (self._expression, self._count)
    
    def __repr__(self):
        return "Variable(%r, %r)" % (self._expression, self._count)
