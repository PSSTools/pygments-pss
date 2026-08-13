"""Shared fixtures: the corpus inventory and the lexer option matrix."""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import Dict, Iterator, List, Tuple

import pytest

from pygments_pss import PSSLexer

CORPUS = Path(__file__).parent / "corpus"
SNIPPETS = Path(__file__).parent / "snippets"

#: Directories of deliberately broken input. Excluded from the no-`Error` rule
#: (T3.1); everything else still applies to them (T3.4).
PATHOLOGICAL_DIRS = {"pathological"}

#: The option matrix asserted in the R1-R3 sweep (plan section 3.6). Options
#: not yet implemented are absent rather than listed with a single value, so
#: adding one here is the only edit a later phase needs.
OPTION_VALUES: Dict[str, Tuple[object, ...]] = {
    "docstrings": (True, False),
    "builtins": (True, False),
}


def option_combinations() -> List[Dict[str, object]]:
    """Every combination in the option matrix, defaults included."""
    keys = sorted(OPTION_VALUES)
    return [
        dict(zip(keys, values))
        for values in itertools.product(*(OPTION_VALUES[k] for k in keys))
    ]


def corpus_files(include_pathological: bool = True) -> List[Path]:
    files = sorted(CORPUS.rglob("*.pss"))
    if not include_pathological:
        files = [f for f in files if not _is_pathological(f)]
    assert files, "corpus is empty -- tests/corpus/ should be vendored, not generated"
    return files


def _is_pathological(path: Path) -> bool:
    return any(part in PATHOLOGICAL_DIRS for part in path.parts)


def corpus_id(path: Path) -> str:
    return str(path.relative_to(CORPUS))


@pytest.fixture(scope="session")
def lexer() -> PSSLexer:
    return PSSLexer()


def lex(text: str, **options) -> List[Tuple[object, str]]:
    """Lex a string through the rule set, with no Pygments preprocessing.

    ``Lexer.get_tokens`` strips leading and trailing newlines (``stripnl``,
    default on) and appends one (``ensurenl``) before the rules ever see the
    text. Those are Pygments' behaviours, not this lexer's, and they make an
    exact round-trip assertion (R3) impossible to state. ``get_tokens_unprocessed``
    is the rule set on its own, which is what these tests are about.
    """
    return [(token, value) for _, token, value in PSSLexer(**options).get_tokens_unprocessed(text)]


def tokens_of(path: Path, **options) -> List[Tuple[object, str]]:
    """Lex a corpus file from disk."""
    return lex(read_corpus(path), **options)


def read_corpus(path: Path) -> str:
    """Corpus text as the lexer will see it, with line endings normalised.

    ``\\r\\n`` normalisation *is* part of ``get_tokens``' contract for every
    Pygments lexer, so doing it here keeps a CRLF checkout from failing R3
    for a reason that has nothing to do with PSS.
    """
    return path.read_text().replace("\r\n", "\n").replace("\r", "\n")


def pytest_addoption(parser):
    parser.addoption(
        "--update-goldens",
        action="store_true",
        default=False,
        help="rewrite tests/snippets/*.tokens from the current lexer output",
    )
