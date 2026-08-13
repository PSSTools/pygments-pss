"""Packaging tests (plan section 3.5).

These are the only tests that exercise the installed distribution rather than
the module: the ``pygments.lexers`` entry point, the aliases, and the console
path. Nothing in the unit suite would notice if the metadata broke.
"""

import subprocess
import sys
import textwrap

import pytest
from pygments.lexers import (
    get_lexer_by_name,
    get_lexer_for_filename,
    get_lexer_for_mimetype,
)

from pygments_pss import PSSLexer, PssLexer

pytestmark = pytest.mark.unit


def test_alias_pss():
    """T5.1 -- the alias every existing ``.. code-block:: pss`` already uses."""
    assert isinstance(get_lexer_by_name("pss"), PSSLexer)


def test_alias_portable_stimulus():
    """T5.2."""
    assert isinstance(get_lexer_by_name("portable-stimulus"), PSSLexer)


def test_filename():
    """T5.3."""
    assert isinstance(get_lexer_for_filename("x.pss"), PSSLexer)


def test_mimetype():
    """T5.4."""
    assert isinstance(get_lexer_for_mimetype("text/x-pss"), PSSLexer)


def test_compat_alias_is_the_same_class():
    """T5.5 -- ``sphinx-pss`` imports ``PssLexer``; it must not be a subclass."""
    assert PssLexer is PSSLexer


def test_single_entry_point():
    """T5.6 -- exactly one advertised lexer, so no duplicate registration."""
    from importlib.metadata import distribution

    eps = [
        ep
        for ep in distribution("pygments-pss").entry_points
        if ep.group == "pygments.lexers"
    ]
    assert len(eps) == 1, eps
    assert eps[0].value == "pygments_pss.lexer:PSSLexer"


def test_pygmentize_subprocess(tmp_path):
    """T5.7 -- the real installed console path, which no in-process test covers."""
    src = tmp_path / "sample.pss"
    src.write_text(
        textwrap.dedent(
            """\
            component pss_top {
                action entry {}
            }
            """
        )
    )
    proc = subprocess.run(
        [sys.executable, "-m", "pygments", "-l", "pss", str(src)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "pss_top" in proc.stdout
