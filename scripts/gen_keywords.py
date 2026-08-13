#!/usr/bin/env python3
"""Regenerate ``src/pygments_pss/_keywords.py`` from ``pssparser``'s grammar.

Hand-maintained keyword lists rot (``DESIGN.md`` section 5). The *vocabulary*
therefore comes from ``PSSLexer.g4``, which is what a working PSS front end
actually reserves; the *classification* -- which bucket a keyword falls into,
and so which token type it gets -- is not derivable from the grammar and lives
in ``BUCKETS`` below.

The generator is deliberately loud. A keyword the grammar has and the mapping
does not is an error, not a silent default to ``Keyword``: getting a new 3.x
keyword highlighted as a plain identifier is the exact failure this design
exists to prevent.

Usage::

    python scripts/gen_keywords.py            # rewrite _keywords.py
    python scripts/gen_keywords.py --check    # exit 1 if it would change
    python scripts/gen_keywords.py --grammar PATH
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "src" / "pygments_pss" / "_keywords.py"
DEFAULT_GRAMMAR = REPO_ROOT / "packages" / "pssparser" / "src" / "PSSLexer.g4"

#: The LRM revision the classification below was reviewed against. Bump it
#: only after actually re-reading Table 3 and Annex B, not on every edit.
LRM_REVISION = "PSS 3.1 Draft 19 (2026-07-14)"


# --------------------------------------------------------------------------
# Classification (DESIGN.md section 6.2)
# --------------------------------------------------------------------------
#
# Bucket name -> (emitted constant, keywords). The order here is the order the
# constants appear in the generated file; it carries no lexing significance,
# since rule order lives in lexer.py.
#
# Words the LRM places in two rows (`if`, `in`, `forall`, `default`, `file`)
# appear here exactly once. That is not a loss: every bucket they could go in
# maps to the same token type, so the choice is documentary only. `DESIGN.md`
# section 6.2 says as much.

BUCKETS: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    # Keyword.Declaration -- the things a documented object can be.
    "declaration_types": (
        "DECLARATION_TYPES",
        (
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
        ),
    ),
    # Keyword.Type
    "builtin_types": (
        "BUILTIN_TYPES",
        (
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
        ),
    ),
    # Keyword.Declaration -- modifiers and qualifiers.
    "modifiers": (
        "MODIFIERS",
        (
            "abstract",
            "atomic",
            "const",
            "dynamic",
            "export",
            "extend",
            "import",
            "instance",
            # A real 3.1 keyword, contra DESIGN.md section 3.1. See clause
            # 9.1.6 "Mutable component attributes" (Mantis8726/8693), Syntax 27,
            # and `component_data_decl_qualifier` in Annex B. Current
            # pssparser master reserves it; the checkout DESIGN.md was written
            # against predates that. Table 3's cell for it is one of the ones
            # the PDF conversion destroyed -- which is the same reason
            # `annotation` looks absent there.
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
        ),
    ),
    # Keyword.Constant
    "literals": ("LITERALS", ("true", "false", "null")),
    # Name.Builtin.Pseudo
    "pseudo_variables": ("PSEUDO_VARIABLES", ("this", "super")),
    # Keyword -- statement-level control flow.
    "control_flow": (
        "CONTROL_FLOW",
        (
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
        ),
    ),
    # Keyword -- activity and scheduling.
    "activity": (
        "ACTIVITY",
        (
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
        ),
    ),
    # Keyword -- constraint language.
    "constraints": (
        "CONSTRAINTS",
        (
            "constraint",
            "default",
            "disable",
            "dist",
            "iff",
            "in",
            "unique",
            "with",
        ),
    ),
    # Keyword -- coverage.
    "coverage": (
        "COVERAGE",
        (
            "bins",
            "cover",
            "coverpoint",
            "cross",
            "ignore_bins",
            "illegal_bins",
        ),
    ),
    # Keyword -- flow objects and resources.
    "flow_objects": (
        "FLOW_OBJECTS",
        ("bind", "inout", "input", "lock", "output", "pool", "share"),
    ),
    # Keyword -- exec blocks and their kinds (Annex B.5).
    "exec": (
        "EXEC",
        (
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
        ),
    ),
    # Keyword
    "functions": ("FUNCTIONS", ("function",)),
    # Comment.Preproc -- only in the sequences `compile if`, `compile has`,
    # `compile assert` (DESIGN.md section 6.3). Bare `has` and `assert` are
    # ordinary identifiers, which is why they are not in any Keyword bucket.
    "conditional_compilation": (
        "CONDITIONAL_COMPILATION",
        ("compile", "has", "assert"),
    ),
    # Keyword -- everything else the grammar reserves.
    "other": ("OTHER", ("as", "randomize")),
}

#: Non-standard words `pssparser` reserves (DESIGN.md sections 3.1, 6.6). Not
#: keywords under `dialect="std"`; `Keyword` under `dialect="pssparser"`.
PSSPARSER_KEYWORDS: Tuple[str, ...] = (
    "from",
    "init",
    "numeric",
    "option",
    "pyimport",
    "pyobj",
)

#: The subset of the above that D1 singles out: `numeric` is a `PSSLexer.g4`
#: token and occupies the alphabetically correct (damaged) cell in the LRM's
#: Table 3, but appears nowhere in Annex B's grammar. Kept as its own constant
#: so revisiting D1 against a clean 3.1 PDF is a one-line change.
STD_DIALECT_EXCLUSIONS: Tuple[str, ...] = ("numeric",)

#: Words the mapping carries that the grammar does not, each with the reason.
#: Without this set the "mapping entry no longer in the grammar" check would
#: fire on every one of them.
EXTRA_KEYWORDS: Dict[str, str] = {
    # In the LRM, missing from pssparser (DESIGN.md sections 3.1, 5).
    "pre_body": "LRM exec_kind; pssparser lags",
    "this": "LRM Table 3; pssparser lags",
    # PSSLexer.g4 comments these out with 'Make exec-block kinds local instead
    # of global keywords'. They are keywords in the LRM's Annex B.5 grammar and
    # a reader of a documentation page expects to see them highlighted.
    "body": "exec_kind; context-local in PSSLexer.g4",
    "declaration": "exec_kind; context-local in PSSLexer.g4",
    "header": "exec_kind; context-local in PSSLexer.g4",
    "init_down": "exec_kind; context-local in PSSLexer.g4",
    "init_up": "exec_kind; context-local in PSSLexer.g4",
    "post_solve": "exec_kind; context-local in PSSLexer.g4",
    "pre_solve": "exec_kind; context-local in PSSLexer.g4",
    "run_end": "exec_kind; context-local in PSSLexer.g4",
    "run_start": "exec_kind; context-local in PSSLexer.g4",
    # PSSLexer.g4 comments these out with 'This parser treats collection types
    # as parameterized classes'. The LRM lists them as built-in types.
    "array": "collection type; parameterized class in PSSLexer.g4",
    "list": "collection type; parameterized class in PSSLexer.g4",
    "map": "collection type; parameterized class in PSSLexer.g4",
    "set": "collection type; parameterized class in PSSLexer.g4",
    # pssparser legacy, commented out alongside the exec kinds. Carried so
    # dialect="pssparser" still highlights it in older sources.
    "init": "pssparser legacy; commented out in PSSLexer.g4",
}


# --------------------------------------------------------------------------
# Grammar parsing
# --------------------------------------------------------------------------

#: ANTLR block comments are used in PSSLexer.g4 to *disable* token rules, so
#: they have to be stripped before scanning -- otherwise the commented-out
#: exec kinds read as live keywords.
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"//[^\n]*")

#: `TOK_NAME: 'keyword';` -- only single-quoted literals that are themselves
#: valid identifiers count as keywords. This deliberately skips operators
#: ('==', '::'), fragments and parser directives.
_TOKEN_RULE = re.compile(
    r"^\s*[A-Z][A-Z0-9_]*\s*:\s*'([A-Za-z_][A-Za-z0-9_]*)'\s*;", re.MULTILINE
)


def grammar_keywords(text: str) -> Tuple[str, ...]:
    """Return the identifier-shaped literals the grammar reserves."""
    stripped = _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", text))
    return tuple(sorted(set(_TOKEN_RULE.findall(stripped))))


def resolve_grammar(explicit: Optional[str]) -> Path:
    """Resolve the grammar per plan P1.1: --grammar, $PSS_GRAMMAR, packages/."""
    for candidate in (explicit, os.environ.get("PSS_GRAMMAR"), str(DEFAULT_GRAMMAR)):
        if candidate:
            path = Path(candidate)
            if path.is_file():
                return path
    raise SystemExit(
        "error: PSSLexer.g4 not found. Pass --grammar, set $PSS_GRAMMAR, or run\n"
        "       `ivpm update` to populate packages/pssparser/."
    )


def grammar_commit(path: Path) -> str:
    """Last commit touching the grammar file, or 'unknown' outside a checkout.

    Deliberately the commit for *this file* rather than the repository HEAD:
    HEAD moves whenever `pssparser` changes anything at all, which would make
    the drift-guard test (T7.1) fail on unrelated upstream work.
    """
    try:
        out = subprocess.check_output(
            ["git", "log", "-1", "--format=%H %cs", "--", path.name],
            cwd=path.parent,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return "unknown"
    return out.decode().strip() or "unknown"


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


def _mapped_keywords() -> Dict[str, str]:
    """keyword -> bucket name, asserting each word is classified exactly once."""
    seen: Dict[str, str] = {}
    for bucket, (_, words) in BUCKETS.items():
        for word in words:
            if word in seen:
                raise SystemExit(
                    "error: %r is in two buckets (%s and %s); it must be classified "
                    "exactly once (T7.3)" % (word, seen[word], bucket)
                )
            seen[word] = bucket
    for word in PSSPARSER_KEYWORDS:
        if word in seen:
            raise SystemExit(
                "error: %r is both a standard keyword (%s) and a pssparser "
                "extension" % (word, seen[word])
            )
        seen[word] = "pssparser"
    return seen


def validate(keywords_in_grammar: Sequence[str]) -> Dict[str, str]:
    """Fail loudly on any drift between the grammar and the mapping."""
    mapped = _mapped_keywords()

    missing = sorted(set(keywords_in_grammar) - set(mapped))
    if missing:
        raise SystemExit(
            "error: PSSLexer.g4 reserves %d word(s) this generator does not classify:\n"
            "       %s\n"
            "       Add each to a bucket in BUCKETS (or to PSSPARSER_KEYWORDS if it is\n"
            "       a tool extension). Defaulting them to Keyword is not an option --\n"
            "       see DESIGN.md section 5." % (len(missing), ", ".join(missing))
        )

    stale = sorted(set(mapped) - set(keywords_in_grammar) - set(EXTRA_KEYWORDS))
    if stale:
        raise SystemExit(
            "error: %d mapped word(s) are no longer in PSSLexer.g4:\n"
            "       %s\n"
            "       Either drop them, or add them to EXTRA_KEYWORDS with the reason\n"
            "       they are carried anyway." % (len(stale), ", ".join(stale))
        )

    unused_extras = sorted(set(EXTRA_KEYWORDS) & set(keywords_in_grammar))
    if unused_extras:
        raise SystemExit(
            "error: %s now appear(s) in PSSLexer.g4 and should be removed from\n"
            "       EXTRA_KEYWORDS -- the justification there is stale."
            % ", ".join(unused_extras)
        )

    # DESIGN.md section 6.3, constraint 5. The literal form of the constraint
    # ("no keyword is a strict prefix of another in a different bucket") is
    # violated by PSS itself -- `in` prefixes `int`, `inout`, `input` and
    # `instance`; `type` prefixes `typedef`; `cover` prefixes `coverpoint`.
    # What actually keeps those safe is that every keyword rule carries a
    # trailing `\b`, which cannot match mid-identifier. So the enforceable
    # invariant is that every keyword is `\b`-delimitable: identifier-shaped,
    # so `\b` sits at both ends.
    for word in sorted(mapped):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", word):
            raise SystemExit(
                "error: keyword %r is not identifier-shaped, so a trailing `\\b` "
                "would not delimit it (DESIGN.md section 6.3 constraint 5)" % word
            )
    return mapped


# --------------------------------------------------------------------------
# Emission
# --------------------------------------------------------------------------


def _tuple_literal(name: str, words: Iterable[str], doc: str) -> str:
    body = "".join('    "%s",\n' % w for w in sorted(words))
    return '#: %s\n%s = (\n%s)\n' % (doc, name, body)


DOCS = {
    "DECLARATION_TYPES": "Type-declaring keywords -> Keyword.Declaration.",
    "BUILTIN_TYPES": "Built-in types -> Keyword.Type.",
    "MODIFIERS": "Declaration modifiers and qualifiers -> Keyword.Declaration.",
    "LITERALS": "Literal keywords -> Keyword.Constant.",
    "PSEUDO_VARIABLES": "Pseudo-variables -> Name.Builtin.Pseudo.",
    "CONTROL_FLOW": "Statement control flow -> Keyword.",
    "ACTIVITY": "Activity and scheduling constructs -> Keyword.",
    "CONSTRAINTS": "Constraint-language keywords -> Keyword.",
    "COVERAGE": "Coverage keywords -> Keyword.",
    "FLOW_OBJECTS": "Flow-object and resource keywords -> Keyword.",
    "EXEC": "Exec blocks and exec kinds (Annex B.5) -> Keyword.",
    "FUNCTIONS": "Function declaration -> Keyword.",
    "CONDITIONAL_COMPILATION": (
        "Conditional compilation -> Comment.Preproc, and only in the sequences\n"
        "#: `compile if`, `compile has`, `compile assert`. Bare `has`/`assert` are\n"
        "#: ordinary identifiers."
    ),
    "OTHER": "Remaining reserved words -> Keyword.",
}


def render(grammar: Path, keywords_in_grammar: Sequence[str]) -> str:
    digest = hashlib.sha256(grammar.read_bytes()).hexdigest()
    out = [
        '"""Keyword vocabulary for the PSS lexer -- GENERATED, DO NOT EDIT.\n',
        "Regenerate with ``python scripts/gen_keywords.py``; verify with\n",
        "``--check``. The classification lives in that script, not here.\n",
        "\n",
        "Provenance\n",
        "----------\n",
        "Source grammar : pssparser ``src/%s``\n" % grammar.name,
        "  sha256       : %s\n" % digest,
        "  last commit  : %s\n" % grammar_commit(grammar),
        "  keywords     : %d reserved words read from the grammar\n"
        % len(keywords_in_grammar),
        "Classification reviewed against : %s\n" % LRM_REVISION,
        "\n",
        "No generation timestamp is recorded on purpose: regenerating from an\n",
        "unchanged grammar must produce a byte-identical file, or the drift-guard\n",
        "test (T7.1) reports a diff on every run.\n",
        '"""\n\n',
        "GRAMMAR_SHA256 = %r\n" % digest,
        "GRAMMAR_COMMIT = %r\n" % grammar_commit(grammar),
        "LRM_REVISION = %r\n\n" % LRM_REVISION,
    ]

    for _, (const, words) in BUCKETS.items():
        out.append(_tuple_literal(const, words, DOCS[const]))
        out.append("\n")

    out.append(
        _tuple_literal(
            "PSSPARSER_KEYWORDS",
            PSSPARSER_KEYWORDS,
            "Non-standard words pssparser reserves. Keywords only under\n"
            "#: ``dialect=\"pssparser\"`` (DESIGN.md sections 3.1, 6.6, D1).",
        )
    )
    out.append("\n")
    out.append(
        _tuple_literal(
            "STD_DIALECT_EXCLUSIONS",
            STD_DIALECT_EXCLUSIONS,
            "Words excluded from ``dialect=\"std\"`` on the D1 reading specifically,\n"
            "#: as opposed to being plainly tool-specific.",
        )
    )
    out.append("\n")
    out.append(
        "#: Every standard keyword, in one flat tuple. Used by the drift-guard\n"
        "#: tests; the lexer consults the buckets, not this.\n"
        "ALL_KEYWORDS = (\n"
        + "".join(
            "    *%s,\n" % const for _, (const, _) in BUCKETS.items()
        )
        + ")\n"
    )
    return "".join(out)


# --------------------------------------------------------------------------


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--grammar", help="path to PSSLexer.g4")
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT))
    ap.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if the output file is not what would be generated",
    )
    args = ap.parse_args(argv)

    grammar = resolve_grammar(args.grammar)
    words = grammar_keywords(grammar.read_text())
    if not words:
        raise SystemExit("error: no token rules found in %s" % grammar)
    validate(words)
    rendered = render(grammar, words)

    output = Path(args.output)
    if args.check:
        current = output.read_text() if output.is_file() else ""
        if current != rendered:
            print(
                "error: %s is out of date with %s.\n"
                "       Run: python scripts/gen_keywords.py" % (output, grammar),
                file=sys.stderr,
            )
            return 1
        print("OK: %s matches %s (%d grammar keywords)" % (output, grammar, len(words)))
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered)
    print("wrote %s (%d grammar keywords)" % (output, len(words)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
