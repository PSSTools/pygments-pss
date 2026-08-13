"""Golden token dumps (plan section 3.4, ``DESIGN.md`` section 8.2).

One snippet per ordering constraint in ``DESIGN.md`` section 6.3, one per
keyword bucket in section 6.2, one per construct in section 7. These are what
make a taxonomy change *reviewable*: the diff of a ``.tokens`` file says
exactly what the reader will see differently.

Regenerate after an intentional change::

    python -m pytest tests/test_snippets.py --update-goldens

and read the resulting diff before committing it. A golden that is regenerated
without being read is worse than no golden at all.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import SNIPPETS, lex

pytestmark = pytest.mark.unit

SNIPPET_FILES = sorted(SNIPPETS.glob("*.pss"))
SNIPPET_IDS = [p.stem for p in SNIPPET_FILES]

#: Snippets lexed with non-default options, so an option's effect is itself a
#: reviewable golden. Keyed by snippet stem; `s-comment-nodoc.pss` is a copy of
#: `s-comment.pss`, so the two goldens diff to exactly what the option does.
SNIPPET_OPTIONS = {
    "s-comment-nodoc": {"docstrings": False},
    "s-builtin-off": {"builtins": False},
}


def render(text: str, **options) -> str:
    """A stable, diffable dump: one token per line, value then token type."""
    lines = []
    for token, value in lex(text, **options):
        lines.append("%-24s %s" % (repr(value), token))
    return "\n".join(lines) + "\n"


@pytest.mark.parametrize("path", SNIPPET_FILES, ids=SNIPPET_IDS)
def test_snippet_matches_golden(path: Path, request):
    options = SNIPPET_OPTIONS.get(path.stem, {})
    actual = render(path.read_text(), **options)
    golden = path.with_suffix(".tokens")

    if request.config.getoption("--update-goldens"):
        golden.write_text(actual)
        pytest.skip("golden updated: %s" % golden.name)

    assert golden.is_file(), (
        "%s has no golden. Run: python -m pytest tests/test_snippets.py "
        "--update-goldens" % path.name
    )
    assert actual == golden.read_text(), (
        "%s differs from its golden. If the change is intended, regenerate with "
        "--update-goldens and review the diff." % path.name
    )


def test_every_snippet_has_a_golden():
    """A snippet with no golden passes vacuously; that must not be possible."""
    missing = [p.name for p in SNIPPET_FILES if not p.with_suffix(".tokens").is_file()]
    assert not missing, "snippets with no golden: %r" % missing


def test_no_orphan_goldens():
    """A golden whose input was deleted is dead weight that still reads as coverage."""
    orphans = [
        g.name for g in SNIPPETS.glob("*.tokens") if not g.with_suffix(".pss").is_file()
    ]
    assert not orphans, "goldens with no snippet: %r" % orphans
