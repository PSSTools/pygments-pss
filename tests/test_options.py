"""Lexer options (plan section 3.6).

Targeted assertions per option; the full cross-product is swept for R1-R3 in
``test_no_error_tokens.py::test_r5_...``. Options land phase by phase, so this
file grows: ``dialect`` (T6.1/T6.2) with P3.1 and ``builtins`` (T6.3) with P2.5.
"""

from __future__ import annotations

import pytest
from pygments.token import Comment

from pygments.util import OptionError

from conftest import lex
from pygments_pss import PSSLexer

pytestmark = pytest.mark.unit


def test_t6_4_docstrings_false():
    """T6.4 -- `/// x` falls back to Comment.Single."""
    assert lex("/// x", docstrings=False) == [(Comment.Single, "/// x")]


def test_docstrings_true_is_the_default():
    assert lex("/// x") == [(Comment.Special, "/// x")]
    assert lex("/// x", docstrings=True) == [(Comment.Special, "/// x")]


@pytest.mark.parametrize("value", ["yes", "no", "true", "false", "1", "0", "on", "off"])
def test_docstrings_accepts_the_string_forms_sphinx_passes(value):
    """`highlight_options` and `pygmentize -O` deliver strings, not bools."""
    PSSLexer(docstrings=value)


def test_t6_5_unknown_option_value_raises():
    """T6.5 -- a typo must fail loudly, not silently take the default.

    A silently-ignored option is worse than an error: the page renders, looks
    plausible, and does not do what the author asked for.
    """
    with pytest.raises(OptionError):
        PSSLexer(docstrings="maybe")


def test_unknown_option_name_is_ignored_by_pygments():
    """Documents the boundary: Pygments validates values, never names.

    Not a defect this package can fix -- `Lexer.__init__` stores unknown keys
    without inspecting them -- but worth pinning, because it is the reason
    T6.5 is about values.
    """
    PSSLexer(no_such_option=True)
