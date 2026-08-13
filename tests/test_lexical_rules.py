"""Targeted assertions on the rules the goldens cannot state as intent.

A golden records *what* the lexer does. These record *why*: each test names the
``DESIGN.md`` section 6.3 ordering constraint or LRM clause it protects, so a
failure says which rule moved rather than just which byte changed.
"""

from __future__ import annotations

import pytest
from pygments.token import (
    Comment,
    Error,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
)

from conftest import lex

pytestmark = pytest.mark.unit


def significant(text: str, **options):
    """Tokens with whitespace dropped -- the shape of the line, not its layout."""
    return [(t, v) for t, v in lex(text, **options) if v.strip()]


def only(text: str, **options):
    """Assert the text lexes to exactly one token, and return it."""
    toks = significant(text, **options)
    assert len(toks) == 1, "expected one token, got %r" % (toks,)
    return toks[0]


# ---------------------------------------------------------------- constraint 1
@pytest.mark.parametrize(
    "text,expected",
    [
        ("4'sd12", Number.Integer),
        ("'d12", Number.Integer),
        ("8'hFF", Number.Hex),
        ("'hff", Number.Hex),
        ("8'b1010_1010", Number.Bin),
        ("3'o7", Number.Oct),
        ("16'sH_FF", Number.Hex),
    ],
)
def test_based_literals_are_one_token(text, expected):
    """Constraint 1: based literals before anything else that could take `'`.

    Without it, `4'sd12` splits into `4` and `'sd12` -- and the `'` has no rule
    of its own, so the tail becomes an Error.
    """
    token, value = only(text)
    assert (token, value) == (expected, text)


# ---------------------------------------------------------------- constraint 2
@pytest.mark.parametrize(
    "text,expected",
    [
        ("0xDEAD_BEEF", Number.Hex),
        ("0Xff", Number.Hex),
        ("0b1101", Number.Bin),
        ("0B1010", Number.Bin),
    ],
)
def test_hex_and_bin_prefixes_beat_the_octal_rule(text, expected):
    """Constraint 2: `0x`/`0b` before octal, or `0` lexes alone and `x1F` is a name."""
    assert only(text) == (expected, text)


# ---------------------------------------------------------------- constraint 3
@pytest.mark.parametrize(
    "text",
    ["1.5", "20.14", "1_0.2_5", "2e6", "1e-9", "6.02E+23", "3.0e0"],
)
def test_floats_are_one_token(text):
    """Constraint 3: float before integer, so `1.5` is not `1` `.` `5`.

    `2e6` is the case `sphinx-pss` got wrong: it had no exponent-only rule, so
    the value lexed as the number `2` followed by the identifier `e6`.
    """
    assert only(text) == (Number.Float, text)


def test_octal_and_decimal():
    """Clause 4.6 plus plan P-D5: a leading `0` is octal, a bare `0` is not."""
    assert only("0755") == (Number.Oct, "0755")
    assert only("00") == (Number.Oct, "00")
    assert only("0") == (Number.Integer, "0")
    assert only("42") == (Number.Integer, "42")
    assert only("1_000_000") == (Number.Integer, "1_000_000")


# ---------------------------------------------------------------- constraint 4
@pytest.mark.parametrize(
    "text",
    [
        r"\busa+index",
        r"\-clock",
        r"\***error-condition***",
        r"\net1/\net2",
        r"\{a,b}",
        r"\a*(b+c)",
    ],
)
def test_escaped_identifiers_are_one_name(text):
    """Constraint 4: escaped identifiers before every operator rule.

    All six are the LRM's own examples (Clause 4.3). Without the rule each one
    shatters into operator soup -- the single most likely omission in a
    C-family lexer applied to PSS.
    """
    assert only(text + " ") == (Name, text)


def test_escaped_identifier_ends_at_whitespace_not_punctuation():
    """Clause 4.3 is explicit: the terminator is white space.

    So `\\net2;` really does include the semicolon. Surprising, faithful, and
    documented in reference/deviations.md rather than worked around.
    """
    assert only(r"\net1;") == (Name, r"\net1;")


# ---------------------------------------------------------------- constraint 5
def test_keyword_prefixes_do_not_shadow_longer_keywords():
    """Constraint 5, in its enforceable form.

    The literal claim in DESIGN.md -- no keyword prefixes another -- is false
    of PSS itself: `in` prefixes `int`, `inout`, `input` and `instance`. What
    makes them safe is the trailing `\\b` on every keyword rule.
    """
    for text, expected in [
        ("in", Keyword),
        ("int", Keyword.Type),
        ("inout", Keyword),
        ("input", Keyword),
        ("instance", Keyword.Declaration),
        ("init_down", Keyword),
        ("type", Keyword.Declaration),
        ("typedef", Keyword.Declaration),
        ("cover", Keyword),
        ("coverpoint", Keyword),
        ("covergroup", Keyword.Declaration),
        ("join_branch", Keyword),
    ]:
        assert only(text) == (expected, text), text


def test_keyword_does_not_match_inside_an_identifier():
    assert only("integer_value") == (Name, "integer_value")
    assert only("my_action") == (Name, "my_action")


# ---------------------------------------------------------------- constraint 6
def test_comments_beat_the_divide_operator():
    """Constraint 6: `//` and `/*` before `/`."""
    assert significant("a / b")[1] == (Operator, "/")
    assert only("// comment") == (Comment.Single, "// comment")
    assert [t for t, _ in significant("/* c */")] == [Comment.Multiline] * 3


# ---------------------------------------------------------------- constraint 7
def test_triple_quote_beats_single_quote():
    """Constraint 7: `\"\"\"` before `\"`."""
    tokens = significant('"""a"""')
    assert [t for t, _ in tokens] == [String.Heredoc] * 3
    assert tokens[0][1] == '"""'


def test_empty_triple_quoted_string():
    """`\"\"\"\"\"\"` is an empty heredoc, not an unterminated one."""
    assert [v for _, v in significant('""""""')] == ['"""', '"""']


# ---------------------------------------------------------------- strings
def test_illegal_escape_is_an_error_not_silently_accepted():
    """Clause 4.7 lists the legal escapes exhaustively."""
    tokens = significant(r'"a\qb"')
    assert (Error, "\\q") in tokens


def test_unterminated_string_stops_at_the_newline():
    """Risk R-1: a runaway string swallowing a page is the ugliest failure here.

    The next line must lex as ordinary PSS, not as string content.
    """
    tokens = significant('string s = "oops\nint x = 1;\n')
    assert (Keyword.Type, "int") in tokens
    assert not any(
        t in String and "\n" in v for t, v in tokens
    ), "a string token spans a line break"


# ---------------------------------------------------------------- names
def test_namespace_and_call_forms():
    assert significant("my_pkg::thing")[0] == (Name.Namespace, "my_pkg")
    assert significant("foo(1)")[0] == (Name.Function, "foo")
    assert significant("if (x)")[0] == (Keyword, "if"), "a keyword is not a call"


def test_builtins_win_over_the_namespace_and_call_forms():
    """P2.2: a core-library name is Name.Builtin wherever it appears."""
    tokens = significant("std_pkg::print(x)")
    assert tokens[0] == (Name.Builtin, "std_pkg")
    assert tokens[2] == (Name.Builtin, "print")
    assert significant("urandom_range(1, 2)")[0] == (Name.Builtin, "urandom_range")
    assert significant("addr_claim_s c;")[0] == (Name.Builtin, "addr_claim_s")


def test_builtins_off_falls_back_to_the_structural_token():
    """T6.3: with the option off the name is still namespace-or-call, just not builtin."""
    tokens = significant("std_pkg::print(x)", builtins=False)
    assert tokens[0] == (Name.Namespace, "std_pkg")
    assert tokens[2] == (Name.Function, "print")
    assert significant("urandom(1)", builtins=False)[0] == (Name.Function, "urandom")


def test_user_name_shadowing_a_builtin_is_an_accepted_false_positive():
    """Documented in reference/deviations.md; pinned here so it cannot drift silently."""
    assert significant("function void print(string s);")[2] == (Name.Builtin, "print")


# ---------------------------------------------------------------- P2.3
def test_package_and_import_paths_are_namespaces():
    assert significant("package my_pkg::sub;")[1] == (Name.Namespace, "my_pkg")
    assert significant("package my_pkg::sub;")[3] == (Name.Namespace, "sub")
    assert significant("import addr_reg_pkg::*;")[1] == (Name.Namespace, "addr_reg_pkg")
    assert significant("import std_pkg;")[1] == (Name.Namespace, "std_pkg")


def test_import_qualifiers_are_not_package_names():
    """`import solve function pkg::f;` -- what follows `import` is not always a path."""
    tokens = significant("import solve function ext_pkg::alloc_addr;")
    assert tokens[1] == (Keyword.Declaration, "solve")
    assert tokens[2] == (Keyword, "function")
    assert tokens[3] == (Name.Namespace, "ext_pkg")


def test_inheritance_base_type_is_a_class():
    assert significant("component pss_top : base_c {")[3] == (Name.Class, "base_c")
    tokens = significant("action a : other_pkg::base_a {")
    assert tokens[3] == (Name.Namespace, "other_pkg")
    assert tokens[5] == (Name.Class, "base_a")


def test_declaration_suffix_state_does_not_capture_a_label():
    """A `:` that is not an inheritance clause must not strand the state."""
    tokens = significant("action a { }\nlabel_x : cover { }")
    assert (Keyword, "cover") in tokens


def test_declaration_name_gets_name_class():
    tokens = significant("action my_action {}")
    assert tokens[0] == (Keyword.Declaration, "action")
    assert tokens[1] == (Name.Class, "my_action")


def test_declaration_name_rule_does_not_cross_a_line_break():
    """A trailing keyword must not claim the next line's first identifier."""
    tokens = significant("action\nsome_variable")
    assert tokens[1] == (Name, "some_variable")


def test_function_return_type_is_not_the_function_name():
    """`function int add(...)`: the name is `add`, not `int`.

    ``sphinx-pss``'s lexer treated `function` as a "keyword then name" form and
    so highlighted the return type as the declared name.
    """
    tokens = significant("function int add(int x);")
    assert tokens[1] == (Keyword.Type, "int")
    assert tokens[2] == (Name.Function, "add")


def test_exec_and_activity_operands_are_not_names():
    """DESIGN.md section 6.5: their operand is a keyword or a brace."""
    assert significant("exec body {}")[1] == (Keyword, "body")
    assert significant("activity {}")[1] == (Punctuation, "{")


# ---------------------------------------------------------------- annotations
def test_annotation_forms():
    assert significant("@bare")[0] == (Name.Decorator, "@")
    tokens = significant('@desc {.text = "x"}')
    assert (Name.Attribute, "text") in tokens
    assert tokens[-1] == (Punctuation, "}")


def test_annotation_params_do_not_leak_into_the_rest_of_the_file():
    """An annotation is followed by ordinary code, in the root state."""
    tokens = significant('@desc {.text = "x"}\naction a {}')
    assert (Keyword.Declaration, "action") in tokens
    assert (Name.Class, "a") in tokens


# ---------------------------------------------------------------- options
def test_docstrings_option_off():
    """P1.11 / T6.4: doc forms fall back to ordinary comment tokens."""
    assert only("/// x", docstrings=False) == (Comment.Single, "/// x")
    assert only("//! x", docstrings=False) == (Comment.Single, "//! x")
    assert [t for t, _ in significant("/** x */", docstrings=False)] == [
        Comment.Multiline
    ] * 3


def test_docstrings_option_on_by_default():
    assert only("/// x") == (Comment.Special, "/// x")
    assert only("//! x") == (Comment.Special, "//! x")
    assert [t for t, _ in significant("/** x */")] == [Comment.Special] * 3


def test_empty_block_comment_is_not_a_doc_comment():
    """`/**/` must not be read as `/**` plus a stray terminator."""
    assert [t for t, _ in significant("/**/")] == [Comment.Multiline] * 2
