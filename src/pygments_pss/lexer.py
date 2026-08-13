"""A Pygments lexer for the Accellera Portable Test and Stimulus Standard.

Structure follows ``DESIGN.md`` section 6. Two things are worth knowing before
editing:

* **Rule order is load-bearing.** ``DESIGN.md`` section 6.3 lists seven ordering
  constraints; each is marked in place below with the constraint number and has
  a snippet test behind it. A well-meaning reorder is the most likely way to
  break this lexer, so the comments are there to be read in review, not just by
  whoever wrote them.
* **The vocabulary is generated.** ``_keywords.py`` comes from ``pssparser``'s
  ``PSSLexer.g4`` via ``scripts/gen_keywords.py`` (``DESIGN.md`` section 5).
  Do not edit it, and do not add a keyword here.

Fragments must lex (goal G3): documentation shows snippets, never compilation
units, so no rule may depend on seeing a ``package`` or a balanced brace. A
syntax error degrades to plausible highlighting rather than a cascade of
``Token.Error`` (non-goal N1).
"""

from __future__ import annotations

import re

from pygments.lexer import RegexLexer, bygroups, default, include, words
from pygments.token import (
    Comment,
    Error,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
)
from pygments.util import get_bool_opt

from . import _keywords as kw
from ._builtins import BUILTINS

__all__ = ["PSSLexer"]


#: Declaration keywords whose operand is *not* a user-chosen name, and which
#: are therefore excluded from the "declaration keyword then name" rule
#: (``DESIGN.md`` section 6.5):
#:
#: * ``activity``/``exec`` -- the operand is a brace or another keyword.
#: * ``typedef``/``function`` -- the name comes *after* the type, so the rule
#:   would highlight the return type as though it were the declared name.
#:   ``sphinx-pss``'s lexer had exactly that bug. Nothing is lost: a function
#:   name is followed by ``(`` and a typedef name by ``;``, and the former
#:   already gets ``Name.Function`` from the call rule.
UNNAMED_DECLARATION_KEYWORDS = ("activity", "exec", "function", "typedef")

#: ``DESIGN.md`` section 6.5: the declared name is what a reader scans a
#: documentation page for, so it gets ``Name.Class``.
NAMED_DECLARATION_KEYWORDS = tuple(
    k for k in kw.DECLARATION_TYPES if k not in UNNAMED_DECLARATION_KEYWORDS
)

#: ``words()`` cannot be used here: it yields a non-capturing group, and this
#: rule needs the keyword in group 1 for ``bygroups``. Longest-first so a
#: keyword that prefixes another cannot win the alternation.
#:
#: The separator is horizontal whitespace only, not ``\s+``. With ``\s+`` a
#: declaration keyword at the end of a line claims the first identifier of the
#: *next* line as a declared name -- a visibly wrong highlight, and one that
#: shows up in any list of keywords. Declarations are written on one line in
#: practice, so the cost of the restriction is a wrapped declaration losing its
#: ``Name.Class``, which is invisible by comparison.
_DECLARATION_NAME_RE = r"\b(%s)([ \t]+)([a-zA-Z_]\w*)" % "|".join(
    sorted(NAMED_DECLARATION_KEYWORDS, key=len, reverse=True)
)

#: Negative lookahead for "the next word is a keyword". Used to keep the
#: package/import rule off ``import solve function pkg::f;`` -- the LRM allows
#: qualifiers between ``import`` and what follows, so the next word is not
#: always a package name.
_NOT_KEYWORD = r"(?!(?:%s)\b)" % "|".join(
    sorted(kw.ALL_KEYWORDS + kw.PSSPARSER_KEYWORDS, key=len, reverse=True)
)

#: Escape sequences Clause 4.7 permits in a quoted string. Anything else after
#: a backslash is illegal, and is lexed as ``Error`` rather than quietly
#: accepted -- the LRM is explicit, and a stray backslash in a documented
#: string is worth seeing.
_STRING_ESCAPE = r"\\['\"?\\abfnrtv]"
_OCTAL_ESCAPE = r"\\[0-7]{3}"


#: Signatures for ``analyse_text``. Each is a construct that no other C-family
#: language has in this exact shape; the weights are small so that a file needs
#: several of them before the lexer claims it at all (``DESIGN.md`` section 6.8).
#:
#: ``DESIGN.md`` section 6.8 lists ``constraint \w*\s*\{`` among the signatures.
#: It is **not** used here: SystemVerilog classes have constraint blocks with
#: identical syntax, and `SystemVerilogLexer` has no ``analyse_text`` of its own
#: (it scores 0.0), so any weight at all would let PSS win a SystemVerilog file
#: outright. Every signature below is one no other C-family language has.
_ANALYSE_SIGNATURES = [
    (re.compile(r"\baction\s+\w+\s*\{"), 0.1),
    (re.compile(r"\bcomponent\s+\w+\s*\{"), 0.1),
    (re.compile(r"\bactivity\s*\{"), 0.1),
    (
        re.compile(
            r"\bexec\s+(?:body|header|declaration|pre_solve|post_solve|pre_body"
            r"|run_start|run_end|init_up|init_down)\b"
        ),
        0.1,
    ),
    (re.compile(r"\b(?:buffer|stream|resource|state)\s+\w+\s*\{"), 0.05),
    (re.compile(r"\bmonitor\s+\w+\s*\{"), 0.05),
    (re.compile(r"\bdo\s+\w+\s*(?:with\s*\{|;)"), 0.05),
]


def _no_token(lexer, match):
    """A rule action that emits nothing -- for zero-width lookahead guards.

    Pygments will not accept ``None`` as a plain rule action (only ``default()``
    uses that path), and a real token type here would put an empty-valued token
    in the stream and in every golden.
    """
    return iter(())


def _builtin_or_name(lexer, match):
    """Identifier callback: ``Name.Builtin`` for a core-library name.

    A callback rather than a ``words()`` rule because the ``builtins`` option
    has to be able to turn it off per instance, and ``RegexLexer.tokens`` is
    built once at class creation (``DESIGN.md`` section 6.7).
    """
    value = match.group()
    if lexer.builtins and value in BUILTINS:
        yield match.start(), Name.Builtin, value
    else:
        yield match.start(), Name, value


def _builtin_call_or_name(lexer, match):
    """Same, for the ``ident (`` and ``ident ::`` forms.

    Group 1 is the identifier, group 2 the separator, group 3 the punctuation
    or operator that identified the form.
    """
    name = match.group(1)
    if lexer.builtins and name in BUILTINS:
        token = Name.Builtin
    else:
        token = Name.Function if match.group(3) == "(" else Name.Namespace
    yield match.start(1), token, name
    if match.group(2):
        yield match.start(2), Text, match.group(2)
    yield match.start(3), (
        Punctuation if match.group(3) == "(" else Operator
    ), match.group(3)


def _doc_comment(fallback):
    """Token callback for a doc-comment form, honouring the ``docstrings`` option.

    ``RegexLexer.tokens`` is processed once at class creation, so an option
    cannot change the rule set (``DESIGN.md`` section 6.7). It can change the
    *token type* a rule emits, which is all this needs: with ``docstrings``
    off, ``///`` and ``/**`` fall back to the ordinary comment token.
    """

    def callback(lexer, match):
        token = Comment.Special if lexer.docstrings else fallback
        yield match.start(), token, match.group()

    return callback


class PSSLexer(RegexLexer):
    """Lexer for `PSS <https://accellera.org/downloads/standards/portable-stimulus>`_
    source.

    .. versionadded:: 0.1.0

    Options accepted (``DESIGN.md`` section 6.7):

    `docstrings`
        Highlight ``///``, ``//!``, ``/** */`` and ``/*! */`` as
        ``Comment.Special``. These are a psstools convention rather than a PSS
        one, but they cost nothing for projects that do not use them.
        (default: ``True``)

    `builtins`
        Highlight core-library names (Annex C: ``std_pkg``, ``executor_pkg``,
        ``addr_reg_pkg``, ``sync_pkg``) as ``Name.Builtin``. Costs a false
        positive on a user-defined name that shadows one -- see
        ``_builtins.py``. (default: ``True``)
    """

    name = "PSS"
    aliases = ["pss", "portable-stimulus"]
    filenames = ["*.pss"]
    mimetypes = ["text/x-pss"]
    url = "https://accellera.org/downloads/standards/portable-stimulus"
    # Empty for an out-of-tree plugin; set to a real Pygments release only if
    # this is ever contributed upstream (DESIGN.md section 11).
    version_added = ""

    def __init__(self, **options):
        self.docstrings = get_bool_opt(options, "docstrings", True)
        self.builtins = get_bool_opt(options, "builtins", True)
        super().__init__(**options)

    def analyse_text(text):
        """Confidence that ``text`` is PSS (``DESIGN.md`` section 6.8).

        Deliberately conservative and capped well below 0.5. PSS shares most of
        its surface with SystemVerilog, and over-claiming steals files from
        other lexers -- a worse outcome than not being guessed, because the
        user who wrote ``.. code-block:: pss`` was never relying on guessing in
        the first place.

        Only multi-word signatures no other C-family language has are counted;
        no single one of them is enough on its own.
        """
        score = 0.0
        for pattern, weight in _ANALYSE_SIGNATURES:
            if pattern.search(text):
                score += weight
        return min(score, 0.3)

    tokens = {
        "root": [
            (r"\s+", Text),
            #
            # Comments. Constraint 6: before the `/` operator.
            #
            (r"//[/!][^\n]*", _doc_comment(Comment.Single)),
            (r"//[^\n]*", Comment.Single),
            # `/**/` is an empty block comment, not a doc comment: the
            # negative lookahead stops `/**` from claiming its own terminator.
            (r"/\*[*!](?!/)", _doc_comment(Comment.Multiline), "docblock"),
            (r"/\*", Comment.Multiline, "block"),
            #
            # Conditional compilation. Only the two-word sequences are
            # preprocessor-ish; bare `compile`, `has` and `assert` are
            # ordinary identifiers (DESIGN.md section 6.2). Must precede the
            # keyword rules, which would otherwise claim `if`.
            #
            # Horizontal whitespace only, for the same reason as
            # _DECLARATION_NAME_RE: `\s+` lets a trailing `compile` on one line
            # pair with an unrelated `has` on the next.
            (
                r"(compile)([ \t]+)(if|has|assert)\b",
                bygroups(Comment.Preproc, Text, Comment.Preproc),
            ),
            #
            # Escaped identifiers -- Clause 4.3. Constraint 4: before every
            # operator rule, or `\busa+index` shatters into operator soup.
            # They run to whitespace, so no inner character needs escaping.
            #
            (r"\\[\x21-\x7e]+", Name),
            #
            # Annotations -- Annex B.6. The `{ .field = ... }` form gets its
            # own state so `.field` can be an attribute rather than
            # punctuation-then-name.
            #
            (
                r"(@)([a-zA-Z_]\w*)(\s*)(\{)",
                bygroups(Name.Decorator, Name.Decorator, Text, Punctuation),
                "annotation-params",
            ),
            (r"(@)([a-zA-Z_]\w*)", bygroups(Name.Decorator, Name.Decorator)),
            #
            # Strings -- Clause 4.7. Constraint 7: `"""` before `"`.
            #
            (r'"""', String.Heredoc, "tqstring"),
            (r'"', String.Double, "string"),
            #
            # Numbers -- Clause 4.6. Order is constraints 1-3, and the token
            # is chosen by base character (DESIGN.md section 7).
            #
            # 1. Based literals first: `4'sd12` must not split into `4` and
            #    `'sd12`, and the leading `'` must be claimed here before
            #    anything else can look at it.
            (r"(?:[1-9][0-9_]*)?'[sS]?[bB][01xXzZ?_]+", Number.Bin),
            (r"(?:[1-9][0-9_]*)?'[sS]?[oO][0-7xXzZ?_]+", Number.Oct),
            (r"(?:[1-9][0-9_]*)?'[sS]?[dD][0-9xXzZ?_]+", Number.Integer),
            (r"(?:[1-9][0-9_]*)?'[sS]?[hH][0-9a-fA-FxXzZ?_]+", Number.Hex),
            # 2. `0x`/`0b` before the octal rule, or `0` lexes alone and
            #    `x1F` becomes a name.
            (r"0[xX][0-9a-fA-F_]+", Number.Hex),
            (r"0[bB][01_]+", Number.Bin),
            # 3. Float before integer, so `1.5` is not `1` `.` `5`. Both
            #    forms: digits are required on *both* sides of the point
            #    (`20 .15` is illegal per Clause 4.6), and the exponent-only
            #    form has no point at all -- `sphinx-pss`'s lexer omitted it,
            #    so `2e6` lexed as `2` followed by a name.
            (r"\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d[\d_]*)?", Number.Float),
            (r"\d[\d_]*[eE][+-]?\d[\d_]*", Number.Float),
            # A leading `0` makes it octal -- but a bare `0` is emitted as
            # Number.Integer (plan P-D5): nobody reads `0` as octal.
            (r"0[0-7_]+", Number.Oct),
            (r"[1-9][\d_]*|0", Number.Integer),
            #
            # Package and import paths -> Name.Namespace (DESIGN.md section
            # 6.5). Before the declaration-name rule, which would otherwise
            # make a package name a Name.Class. The lookahead keeps it off
            # `import solve function pkg::f;`, where what follows `import` is
            # a qualifier rather than a package path.
            #
            (
                r"\b(package|import)([ \t]+)" + _NOT_KEYWORD,
                bygroups(Keyword.Declaration, Text),
                "qualified-name",
            ),
            #
            # Declaration keyword then name (DESIGN.md section 6.5). Before
            # the plain keyword rules, which would consume the keyword and
            # leave the name as an ordinary identifier.
            #
            (
                _DECLARATION_NAME_RE,
                bygroups(Keyword.Declaration, Text, Name.Class),
                "declaration-suffix",
            ),
            #
            # Keywords. Constraint 5: a keyword that prefixes another is safe
            # only because every rule here carries a trailing `\b`; the
            # generator asserts every keyword is identifier-shaped so that
            # holds. (`in` prefixes `int`, `inout`, `input` and `instance`.)
            #
            (words(kw.LITERALS, suffix=r"\b"), Keyword.Constant),
            (words(kw.PSEUDO_VARIABLES, suffix=r"\b"), Name.Builtin.Pseudo),
            (words(kw.BUILTIN_TYPES, suffix=r"\b"), Keyword.Type),
            (words(kw.DECLARATION_TYPES, suffix=r"\b"), Keyword.Declaration),
            (words(kw.MODIFIERS, suffix=r"\b"), Keyword.Declaration),
            (
                words(
                    kw.CONTROL_FLOW
                    + kw.ACTIVITY
                    + kw.CONSTRAINTS
                    + kw.COVERAGE
                    + kw.FLOW_OBJECTS
                    + kw.EXEC
                    + kw.FUNCTIONS
                    + kw.OTHER,
                    suffix=r"\b",
                ),
                Keyword,
            ),
            #
            # Names.
            #
            (r"([a-zA-Z_]\w*)(\s*)(::)", _builtin_call_or_name),
            (r"([a-zA-Z_]\w*)(\s*)(\()", _builtin_call_or_name),
            (r"[a-zA-Z_]\w*", _builtin_or_name),
            #
            # Operators, longest first. An explicit alternation rather than a
            # character class: `[-+*/%!~^&|<>=?:]+` would merge `a =- b` into
            # one operator token and hide the `..`/`...` distinction.
            #
            (r"<<=|>>=|\.\.\.", Operator),
            (
                r"\*\*|->|:=|:/|::|\.\.|==|!=|<=|>=|&&|\|\||<<|>>|[-+*/%|&^]=",
                Operator,
            ),
            (r"[-+*/%!~^&|<>=?:#]", Operator),
            #
            # Punctuation. After the operators so `..` is not two `.`.
            #
            (r"[{}()\[\];,.]", Punctuation),
        ],
        #
        # Names introduced by a declaration (DESIGN.md section 6.5, P2.3).
        #
        # `package a::b` and `import a::b::*;` -- every component of the path
        # is a namespace, including the last, which the `ident ::` rule in root
        # cannot see.
        "qualified-name": [
            (r"[ \t]+", Text),
            (r"[a-zA-Z_]\w*", Name.Namespace),
            (r"::", Operator),
            (r"\*", Operator),
            default("#pop"),
        ],
        # Whatever follows a declared name: an inheritance clause gets its base
        # type highlighted like the declaration it derives from. Anything else
        # -- `{`, `;`, `(`, a template parameter list -- pops without consuming.
        "declaration-suffix": [
            (r"[ \t]+", Text),
            (r":", Operator, "base-type"),
            default("#pop"),
        ],
        "base-type": [
            (r"[ \t]+", Text),
            (r"([a-zA-Z_]\w*)([ \t]*)(::)", bygroups(Name.Namespace, Text, Operator)),
            # Pops both states: the declaration is finished with.
            (r"[a-zA-Z_]\w*", Name.Class, "#pop:2"),
            default("#pop:2"),
        ],
        #
        # Comments.
        #
        "block": [
            (r"[^*/]+", Comment.Multiline),
            (r"\*/", Comment.Multiline, "#pop"),
            (r"[*/]", Comment.Multiline),
        ],
        "docblock": [
            (r"[^*/]+", _doc_comment(Comment.Multiline)),
            (r"\*/", _doc_comment(Comment.Multiline), "#pop"),
            (r"[*/]", _doc_comment(Comment.Multiline)),
        ],
        #
        # Strings.
        #
        "string": [
            (_OCTAL_ESCAPE, String.Escape),
            (_STRING_ESCAPE, String.Escape),
            # A backslash-newline is a line continuation in pssparser's
            # grammar, though Clause 4.7 does not mention it.
            (r"\\\n", String.Escape),
            (r"\\.", Error),
            (r'"', String.Double, "#pop"),
            # Clause 4.7: a quoted string is single-line. Terminating the
            # state here is the whole defence against a runaway string
            # swallowing a documentation page -- the ugliest failure this
            # lexer can have, because it is silent and user-visible (risk R-1).
            (r"\n", Error, "#pop"),
            (r'[^\\"\n]+', String.Double),
        ],
        "tqstring": [
            # pssparser's grammar has an EscapedTripleQuote fragment, so a
            # `\"""` inside the body is content, not a terminator. Matching it
            # first is what keeps the string from ending early.
            (r'\\"""', String.Escape),
            (r'"""', String.Heredoc, "#pop"),
            # Clause 4.7.1 (Mantis8730/8356): a target template is mostly
            # opaque text with a few live PSS expressions in it, and those
            # expressions are the interesting part.
            (r"\{\{", String.Interpol, "tqexpr"),
            (r"\{%%\}", Comment.Preproc),
            (r"\{%", Comment.Preproc, "tqdirective"),
            # Stop at `{` so the two rules above get a chance; `"` and `\` are
            # split out for the same reason.
            (r'[^"\\{]+', String.Heredoc),
            (r'[\\"{]', String.Heredoc),
        ],
        # `{{ expression }}` -- PSS tokens between String.Interpol delimiters.
        "tqexpr": [
            (r"\}\}", String.Interpol, "#pop"),
            # Bounded by the enclosing string's terminator as well as its own,
            # so an unclosed `{{` cannot swallow the rest of the file (risk
            # R-1). Zero-width and silent: it emits no token, it just hands the
            # `"""` back to the tqstring state that knows what to do with it.
            (r'(?=""")', _no_token, "#pop"),
            include("expr"),
        ],
        # `{% if (...) %}`, `{% foreach ... %}` -- control-flow directives.
        "tqdirective": [
            (r"%\}", Comment.Preproc, "#pop"),
            (r'(?=""")', _no_token, "#pop"),
            include("expr"),
        ],
        # PSS expression tokens, for use inside a template element. Deliberately
        # not `include("root")`: root's string rules could re-enter `tqstring`,
        # and a declaration inside a mustache expression is not a thing.
        "expr": [
            (r"[ \t]+", Text),
            (r"\n", Text),
            (r"(?:[1-9][0-9_]*)?'[sS]?[bB][01xXzZ?_]+", Number.Bin),
            (r"(?:[1-9][0-9_]*)?'[sS]?[oO][0-7xXzZ?_]+", Number.Oct),
            (r"(?:[1-9][0-9_]*)?'[sS]?[dD][0-9xXzZ?_]+", Number.Integer),
            (r"(?:[1-9][0-9_]*)?'[sS]?[hH][0-9a-fA-FxXzZ?_]+", Number.Hex),
            (r"0[xX][0-9a-fA-F_]+", Number.Hex),
            (r"0[bB][01_]+", Number.Bin),
            (r"\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d[\d_]*)?", Number.Float),
            (r"\d[\d_]*[eE][+-]?\d[\d_]*", Number.Float),
            (r"0[0-7_]+", Number.Oct),
            (r"[1-9][\d_]*|0", Number.Integer),
            (r"\"[^\"\n]*\"", String.Double),
            (words(kw.LITERALS, suffix=r"\b"), Keyword.Constant),
            (words(kw.PSEUDO_VARIABLES, suffix=r"\b"), Name.Builtin.Pseudo),
            (
                words(
                    kw.CONTROL_FLOW + kw.ACTIVITY + kw.CONSTRAINTS, suffix=r"\b"
                ),
                Keyword,
            ),
            (r"([a-zA-Z_]\w*)(\s*)(::)", _builtin_call_or_name),
            (r"([a-zA-Z_]\w*)(\s*)(\()", _builtin_call_or_name),
            (r"[a-zA-Z_]\w*", _builtin_or_name),
            (r"<<=|>>=|\.\.\.", Operator),
            (
                r"\*\*|->|:=|:/|::|\.\.|==|!=|<=|>=|&&|\|\||<<|>>|[-+*/%|&^]=",
                Operator,
            ),
            (r"[-+*/%!~^&|<>=?:#]", Operator),
            (r"[()\[\];,.]", Punctuation),
            # A brace inside a template element is not a nesting construct --
            # emitting it as punctuation and staying put keeps the state from
            # both running away and popping early.
            (r"[{}]", Punctuation),
        ],
        #
        # Annotations.
        #
        "annotation-params": [
            (r"\}", Punctuation, "#pop"),
            # Nest rather than pop on an inner brace, so an aggregate value
            # cannot close the parameter list early.
            (r"\{", Punctuation, "#push"),
            (r"(\.)([a-zA-Z_]\w*)", bygroups(Punctuation, Name.Attribute)),
            # Values are ordinary PSS expressions. These three rules come
            # first so `}` and `.field` are not claimed by root's punctuation.
            include("root"),
        ],
    }
