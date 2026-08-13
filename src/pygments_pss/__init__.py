"""A Pygments plugin providing a lexer for Accellera PSS.

Installing this package registers ``PSSLexer`` through the ``pygments.lexers``
entry point, so ``pygmentize -l pss``, Sphinx ``.. code-block:: pss``, MkDocs
```` ```pss ```` fences and ``get_lexer_by_name("pss")`` all work with no
further configuration.
"""

from .__version__ import get_version
from .lexer import PSSLexer

#: Deprecated alias kept so ``sphinx-pss``'s migration is a one-line change
#: (``DESIGN.md`` section 4.3).
PssLexer = PSSLexer

__version__ = get_version()

__all__ = ["PSSLexer", "PssLexer", "__version__"]
