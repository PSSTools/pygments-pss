"""Drift guards between ``pssparser``'s grammar and ``_keywords.py``.

Marked ``upstream``: a ``pssparser`` keyword addition must **fail** CI, not
skip it. The whole point of generating the vocabulary (``DESIGN.md`` section 5)
is that a new 3.x keyword can never quietly lex as an ordinary identifier, and
a guard that skips when the grammar is missing gives exactly that outcome.

If these fail in a fresh checkout, the fix is ``ivpm update`` -- not a skip.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

from pygments_pss import _keywords as kw

pytestmark = [pytest.mark.upstream, pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATOR = REPO_ROOT / "scripts" / "gen_keywords.py"
GENERATED = REPO_ROOT / "src" / "pygments_pss" / "_keywords.py"


def _load_generator():
    """Import the generator by path: `scripts/` is not an importable package."""
    assert GENERATOR.is_file(), "generator missing: %s" % GENERATOR
    spec = importlib.util.spec_from_file_location("_gen_keywords", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_gen_keywords"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generator():
    return _load_generator()


@pytest.fixture(scope="module")
def grammar(generator):
    try:
        return generator.resolve_grammar(None)
    except SystemExit as exc:  # pragma: no cover - environment failure
        pytest.fail(
            "PSSLexer.g4 not found, so the vocabulary cannot be checked against "
            "its source. Run `ivpm update`, or set $PSS_GRAMMAR.\n%s" % exc
        )


def test_t7_1_checked_in_vocabulary_matches_the_generator(generator, grammar):
    """T7.1 -- regenerating in memory reproduces the checked-in file exactly."""
    words = generator.grammar_keywords(grammar.read_text())
    generator.validate(words)
    expected = generator.render(grammar, words)
    assert GENERATED.read_text() == expected, (
        "_keywords.py is out of date with %s.\n"
        "Run: python scripts/gen_keywords.py" % grammar
    )


def test_t7_2_provenance_names_the_grammar_that_was_read(grammar):
    """T7.2 -- catches a stale `packages/` checkout.

    Recorded as a content hash rather than a repository HEAD: HEAD moves on
    every unrelated ``pssparser`` commit, which would make this fail for
    reasons that have nothing to do with the vocabulary.
    """
    digest = hashlib.sha256(grammar.read_bytes()).hexdigest()
    assert digest == kw.GRAMMAR_SHA256, (
        "the grammar at %s (sha256 %s) is not the one _keywords.py was generated "
        "from (%s). Run `ivpm update`, then "
        "`python scripts/gen_keywords.py`." % (grammar, digest, kw.GRAMMAR_SHA256)
    )


def test_t7_3_every_keyword_is_in_exactly_one_bucket():
    """T7.3 -- a word in two buckets has two token types; only one can win."""
    buckets = {
        "DECLARATION_TYPES": kw.DECLARATION_TYPES,
        "BUILTIN_TYPES": kw.BUILTIN_TYPES,
        "MODIFIERS": kw.MODIFIERS,
        "LITERALS": kw.LITERALS,
        "PSEUDO_VARIABLES": kw.PSEUDO_VARIABLES,
        "CONTROL_FLOW": kw.CONTROL_FLOW,
        "ACTIVITY": kw.ACTIVITY,
        "CONSTRAINTS": kw.CONSTRAINTS,
        "COVERAGE": kw.COVERAGE,
        "FLOW_OBJECTS": kw.FLOW_OBJECTS,
        "EXEC": kw.EXEC,
        "FUNCTIONS": kw.FUNCTIONS,
        "CONDITIONAL_COMPILATION": kw.CONDITIONAL_COMPILATION,
        "OTHER": kw.OTHER,
        "PSSPARSER_KEYWORDS": kw.PSSPARSER_KEYWORDS,
    }
    seen = {}
    for name, words in buckets.items():
        for word in words:
            assert word not in seen, "%r is in both %s and %s" % (
                word,
                seen[word],
                name,
            )
            seen[word] = name

    assert set(kw.ALL_KEYWORDS) == set(seen) - set(kw.PSSPARSER_KEYWORDS)


def test_all_keywords_are_identifier_shaped():
    """The trailing `\\b` on every keyword rule only delimits identifiers.

    This is DESIGN.md section 6.3 constraint 5 in the form that is actually
    true of PSS -- see the comment in scripts/gen_keywords.py.
    """
    import re

    for word in kw.ALL_KEYWORDS + kw.PSSPARSER_KEYWORDS:
        assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", word), word


def test_lrm_3_1_additions_are_present():
    """P1.2's acceptance list: the words a 3.0-era vocabulary would be missing."""
    for word in (
        "annotation",
        "atomic",
        "cover",
        "eventually",
        "forall",
        "match",
        "monitor",
        "mutable",
        "overlap",
        "pre_body",
        "replicate",
        "symbol",
        "this",
        "yield",
    ):
        assert word in kw.ALL_KEYWORDS, "%r missing from the vocabulary" % word


def test_pssparser_extensions_are_not_standard_keywords():
    """DESIGN.md section 6.6: these are tool extensions, not PSS."""
    for word in ("from", "init", "numeric", "option", "pyimport", "pyobj"):
        assert word in kw.PSSPARSER_KEYWORDS
        assert word not in kw.ALL_KEYWORDS
