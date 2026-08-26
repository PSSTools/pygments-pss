"""Shared fixtures: the corpus inventory and the lexer option matrix."""

from __future__ import annotations

import itertools
import os
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

import pytest

from pygments_pss import PSSLexer

SNIPPETS = Path(__file__).parent / "snippets"

_REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Corpus discovery -- pss-corpus PLAN.md section 5.1, item C-13
# ---------------------------------------------------------------------------
#
# The corpus used to live at tests/corpus/ in this repo, vendored so the suite
# would run standalone (DESIGN.md section 8.1). It now lives in `pss-corpus`,
# shared with pssfmt and pssparser, and this repo was the donor.
#
# The twenty lines below are deliberately duplicated in each consumer rather
# than shared through a package: a package to hold one path lookup would add a
# build, a release cadence and a version-skew failure mode to a repository
# whose whole value is having none of those.


def _sweep_root(path: Path) -> Path:
    """The subtree to sweep, given a corpus location.

    ``curated/`` and ``breadth/`` carry different promises -- curated files
    have recorded provenance and a bucket policy, breadth files are bulk input
    of unknown validity -- so a consumer selects between them with a *path*
    rather than with a filter it maintains itself.

    Keeping this at the *sweep* root rather than the repository root is what
    keeps ``corpus_id`` stable across the migration: IDs stay
    ``pathological/unterminated_block_comment.pss`` and do not gain a
    ``curated/`` component. pssfmt learned that the hard way -- its corpus IDs
    shifted, and six ``xfail(strict=True)`` markers silently stopped matching
    their files.

    Falling back to ``path`` itself keeps a bare directory usable: ``$PSS_CORPUS``
    pointed at a scratch tree of ``.pss`` files.
    """
    curated = path / "curated"
    return curated if curated.is_dir() else path


def _find_corpus() -> Optional[Path]:
    """Locate the corpus, in decreasing order of how settled it is."""
    if os.environ.get("PYGMENTS_PSS_CORPUS") and not os.environ.get("PSS_CORPUS"):
        raise RuntimeError(
            "PYGMENTS_PSS_CORPUS is not read; the variable names the corpus, "
            "not the consumer. Export PSS_CORPUS instead.")

    override = os.environ.get("PSS_CORPUS")
    candidates = []
    if override:
        candidates.append(Path(override))
    candidates += [
        _REPO_ROOT / "packages" / "pss-corpus",   # ivpm dependency
        _REPO_ROOT.parent / "pss-corpus",         # sibling checkout
    ]
    for path in candidates:
        if not path.is_dir():
            continue
        root = _sweep_root(path)
        if any(root.rglob("*.pss")):
            return root
    return None


#: The corpus root. ``None`` when no corpus was found -- which is a **failure**,
#: not a skip (section 5.2): a sweep that quietly finds nothing reports success
#: in exactly the case it exists to catch. ``corpus_files()`` raises.
CORPUS = _find_corpus()


def _manifest() -> dict:
    """Bucket policy from the corpus's own ``manifest.toml``, if it has one."""
    if CORPUS is None:
        return {}
    for candidate in (CORPUS.parent, CORPUS):
        path = candidate / "manifest.toml"
        if path.is_file():
            import tomllib
            return tomllib.loads(path.read_text(encoding="utf-8")).get(
                "bucket", {})
    return {}


#: Directories of deliberately broken input. Excluded from the no-`Error` rule
#: (T3.1); everything else still applies to them (T3.4).
#:
#: Read from the corpus manifest where there is one, so a new bucket arrives
#: carrying its policy instead of needing a matching commit in three repos. The
#: literal is the fallback for a corpus without a manifest, and
#: ``test_the_manifest_agrees_with_the_fallback`` pins the two together.
FALLBACK_PATHOLOGICAL_DIRS = {"pathological"}

PATHOLOGICAL_DIRS = {
    name for name, spec in _manifest().items() if not spec.get("parses", True)
} or FALLBACK_PATHOLOGICAL_DIRS

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
    assert CORPUS is not None, (
        "no PSS corpus found. It is a declared ivpm dependency and should be "
        "at packages/pss-corpus -- run `ivpm update`, or set PSS_CORPUS. "
        "Failing rather than skipping is deliberate: a sweep that finds "
        "nothing and passes reports success in exactly the case it exists to "
        "catch.")
    files = sorted(CORPUS.rglob("*.pss"))
    if not include_pathological:
        files = [f for f in files if not _is_pathological(f)]
    assert files, "corpus is empty at %s" % CORPUS
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
