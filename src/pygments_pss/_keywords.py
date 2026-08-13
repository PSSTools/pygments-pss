"""Keyword vocabulary for the PSS lexer -- GENERATED, DO NOT EDIT.
Regenerate with ``python scripts/gen_keywords.py``; verify with
``--check``. The classification lives in that script, not here.

Provenance
----------
Source grammar : pssparser ``src/PSSLexer.g4``
  sha256       : 1ce6bd763ebbcd44e7fb49a13a52c7e68c818a3f61e5917f3d6663d5e9674f3b
  last commit  : c5d699ae9ef51ead64d20ae3c931b64b4ff00f39 2026-08-13
  keywords     : 106 reserved words read from the grammar
Classification reviewed against : PSS 3.1 Draft 19 (2026-07-14)

No generation timestamp is recorded on purpose: regenerating from an
unchanged grammar must produce a byte-identical file, or the drift-guard
test (T7.1) reports a diff on every run.
"""

GRAMMAR_SHA256 = '1ce6bd763ebbcd44e7fb49a13a52c7e68c818a3f61e5917f3d6663d5e9674f3b'
GRAMMAR_COMMIT = 'c5d699ae9ef51ead64d20ae3c931b64b4ff00f39 2026-08-13'
LRM_REVISION = 'PSS 3.1 Draft 19 (2026-07-14)'

#: Type-declaring keywords -> Keyword.Declaration.
DECLARATION_TYPES = (
    "action",
    "annotation",
    "buffer",
    "class",
    "component",
    "covergroup",
    "enum",
    "monitor",
    "package",
    "resource",
    "state",
    "stream",
    "struct",
    "typedef",
)

#: Built-in types -> Keyword.Type.
BUILTIN_TYPES = (
    "array",
    "bit",
    "bool",
    "chandle",
    "float32",
    "float64",
    "int",
    "list",
    "map",
    "set",
    "string",
    "void",
)

#: Declaration modifiers and qualifiers -> Keyword.Declaration.
MODIFIERS = (
    "abstract",
    "atomic",
    "const",
    "dynamic",
    "export",
    "extend",
    "import",
    "instance",
    "mutable",
    "override",
    "private",
    "protected",
    "public",
    "pure",
    "rand",
    "ref",
    "solve",
    "static",
    "symbol",
    "target",
    "type",
)

#: Literal keywords -> Keyword.Constant.
LITERALS = (
    "false",
    "null",
    "true",
)

#: Pseudo-variables -> Name.Builtin.Pseudo.
PSEUDO_VARIABLES = (
    "super",
    "this",
)

#: Statement control flow -> Keyword.
CONTROL_FLOW = (
    "break",
    "continue",
    "do",
    "else",
    "foreach",
    "if",
    "match",
    "repeat",
    "return",
    "while",
)

#: Activity and scheduling constructs -> Keyword.
ACTIVITY = (
    "activity",
    "concat",
    "eventually",
    "forall",
    "join_branch",
    "join_first",
    "join_none",
    "join_select",
    "overlap",
    "parallel",
    "replicate",
    "schedule",
    "select",
    "sequence",
    "yield",
)

#: Constraint-language keywords -> Keyword.
CONSTRAINTS = (
    "constraint",
    "default",
    "disable",
    "dist",
    "iff",
    "in",
    "unique",
    "with",
)

#: Coverage keywords -> Keyword.
COVERAGE = (
    "bins",
    "cover",
    "coverpoint",
    "cross",
    "ignore_bins",
    "illegal_bins",
)

#: Flow-object and resource keywords -> Keyword.
FLOW_OBJECTS = (
    "bind",
    "inout",
    "input",
    "lock",
    "output",
    "pool",
    "share",
)

#: Exec blocks and exec kinds (Annex B.5) -> Keyword.
EXEC = (
    "body",
    "declaration",
    "exec",
    "file",
    "header",
    "init_down",
    "init_up",
    "post_solve",
    "pre_body",
    "pre_solve",
    "run_end",
    "run_start",
)

#: Function declaration -> Keyword.
FUNCTIONS = (
    "function",
)

#: Conditional compilation -> Comment.Preproc, and only in the sequences
#: `compile if`, `compile has`, `compile assert`. Bare `has`/`assert` are
#: ordinary identifiers.
CONDITIONAL_COMPILATION = (
    "assert",
    "compile",
    "has",
)

#: Remaining reserved words -> Keyword.
OTHER = (
    "as",
    "randomize",
)

#: Non-standard words pssparser reserves. Keywords only under
#: ``dialect="pssparser"`` (DESIGN.md sections 3.1, 6.6, D1).
PSSPARSER_KEYWORDS = (
    "from",
    "init",
    "numeric",
    "option",
    "pyimport",
    "pyobj",
)

#: Words excluded from ``dialect="std"`` on the D1 reading specifically,
#: as opposed to being plainly tool-specific.
STD_DIALECT_EXCLUSIONS = (
    "numeric",
)

#: Every standard keyword, in one flat tuple. Used by the drift-guard
#: tests; the lexer consults the buckets, not this.
ALL_KEYWORDS = (
    *DECLARATION_TYPES,
    *BUILTIN_TYPES,
    *MODIFIERS,
    *LITERALS,
    *PSEUDO_VARIABLES,
    *CONTROL_FLOW,
    *ACTIVITY,
    *CONSTRAINTS,
    *COVERAGE,
    *FLOW_OBJECTS,
    *EXEC,
    *FUNCTIONS,
    *CONDITIONAL_COMPILATION,
    *OTHER,
)
