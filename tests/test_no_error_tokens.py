"""Rule assertions swept over the whole corpus (plan section 3.3).

The highest value-per-line tests available. R2 in particular is the one that
catches a runaway state, which produces perfectly *valid* tokens and so slips
straight past an error check.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from pygments.token import Comment, Error, String

from conftest import (
    _is_pathological,
    corpus_files,
    corpus_id,
    option_combinations,
    read_corpus,
    tokens_of,
)

pytestmark = pytest.mark.corpus

#: Longest token accepted outside comments and triple-quoted strings, both of
#: which are legitimately long. Chosen well above any real PSS identifier or
#: literal, so a failure means a state ran away rather than that someone wrote
#: a long name.
MAX_TOKEN_LEN = 200

#: Token types allowed to exceed it.
LONG_TOKEN_TYPES = (Comment, String.Heredoc)

CLEAN = [f for f in corpus_files() if not _is_pathological(f)]
PATHOLOGICAL = [f for f in corpus_files() if _is_pathological(f)]
IDS_CLEAN = [corpus_id(f) for f in CLEAN]
IDS_PATH = [corpus_id(f) for f in PATHOLOGICAL]


def _oversized(tokens):
    for token, value in tokens:
        if len(value) <= MAX_TOKEN_LEN:
            continue
        if any(token in allowed for allowed in LONG_TOKEN_TYPES):
            continue
        yield token, value


@pytest.mark.parametrize("path", CLEAN, ids=IDS_CLEAN)
def test_r1_no_error_tokens(path: Path):
    """R1 -- valid PSS produces no ``Token.Error`` (non-goal N1)."""
    bad = [value for token, value in tokens_of(path) if token is Error]
    assert not bad, "Error tokens in %s: %r" % (corpus_id(path), bad[:5])


@pytest.mark.parametrize("path", corpus_files(), ids=[corpus_id(f) for f in corpus_files()])
def test_r2_no_oversized_token(path: Path):
    """R2 -- no runaway state.

    A token longer than a couple of lines almost always means a string or
    comment state failed to terminate and is swallowing the rest of the file.
    That is risk R-1: silent, and visible to the reader of a docs page.
    """
    bad = list(_oversized(tokens_of(path)))
    assert not bad, "oversized tokens in %s: %r" % (
        corpus_id(path),
        [(str(t), v[:60] + "...") for t, v in bad[:3]],
    )


@pytest.mark.parametrize("path", corpus_files(), ids=[corpus_id(f) for f in corpus_files()])
def test_r3_round_trip(path: Path):
    """R3 -- the token values concatenate back to the input.

    Pygments guarantees this; a mis-grouped ``bygroups`` or a callback that
    drops a character breaks it, and nothing else in the suite would notice.
    """
    actual = "".join(value for _, value in tokens_of(path))
    assert actual == read_corpus(path), "round-trip differs for %s" % corpus_id(path)


@pytest.mark.parametrize("path", PATHOLOGICAL, ids=IDS_PATH)
def test_r4_pathological_input_terminates(path: Path):
    """R4 -- broken input lexes quickly and does not run away.

    Deliberately broken files are allowed to produce ``Token.Error`` -- that
    is what they are for -- but they must still satisfy R2 and R3, and must
    not hang. The time bound is generous: these files are tiny, so anything
    approaching it means catastrophic backtracking, not slowness.
    """
    start = time.monotonic()
    tokens = list(tokens_of(path))
    elapsed = time.monotonic() - start
    assert elapsed < 2.0, "%s took %.2fs to lex" % (corpus_id(path), elapsed)

    assert not list(_oversized(tokens)), "runaway state on %s" % corpus_id(path)

    assert "".join(v for _, v in tokens) == read_corpus(path)


@pytest.mark.parametrize("options", option_combinations(), ids=str)
def test_r5_rules_hold_for_every_option_combination(options):
    """R5 -- R1-R3 are not properties of the default options alone."""
    for path in corpus_files():
        tokens = list(tokens_of(path, **options))

        if not _is_pathological(path):
            errors = [v for t, v in tokens if t is Error]
            assert not errors, "R1 broken for %s with %r" % (corpus_id(path), options)

        assert not list(_oversized(tokens)), "R2 broken for %s with %r" % (
            corpus_id(path),
            options,
        )

        assert "".join(v for _, v in tokens) == read_corpus(path), (
            "R3 broken for %s with %r" % (corpus_id(path), options)
        )
