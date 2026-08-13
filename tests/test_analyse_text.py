"""``analyse_text`` (plan T-P2.4, ``DESIGN.md`` section 6.8).

Two failure modes matter, and they pull in opposite directions: claiming too
little means `guess_lexer` never finds PSS, and claiming too much means PSS
steals files from SystemVerilog and C. The second is worse -- someone who
writes ```` ```pss ```` was never relying on guessing, but someone whose C file
renders as PSS did nothing wrong.
"""

from __future__ import annotations

import textwrap

import pytest
from pygments.lexers import CLexer, SystemVerilogLexer

from conftest import CORPUS, read_corpus
from pygments_pss import PSSLexer

pytestmark = pytest.mark.unit

#: Three corpus files spanning the styles the corpus covers: hand-written,
#: LRM-derived, and machine-generated.
REPRESENTATIVE = [
    "example2/pss_top.pss",
    "language-ref/flow_basic.pss",
    "pss31/behavioral_coverage.pss",
]

C_SOURCE = textwrap.dedent(
    """\
    #include <stdio.h>

    struct point { int x; int y; };

    static int add(int a, int b) {
        return a + b;
    }

    int main(void) {
        struct point p = {1, 2};
        printf("%d\\n", add(p.x, p.y));
        return 0;
    }
    """
)

SV_SOURCE = textwrap.dedent(
    """\
    class transaction;
        rand bit [7:0] data;
        rand bit [3:0] addr;

        constraint c_addr { addr inside {[0:7]}; }

        function new();
        endfunction
    endclass

    module tb;
        initial begin
            transaction t = new();
            $display("%0d", t.addr);
        end
    endmodule
    """
)


@pytest.mark.parametrize("name", REPRESENTATIVE)
def test_pss_scores_above_the_c_family_alternatives(name):
    path = CORPUS / name
    assert path.is_file(), path
    text = read_corpus(path)

    pss = PSSLexer.analyse_text(text)
    assert pss > 0.0, "%s scored nothing" % name
    assert pss > CLexer.analyse_text(text), name
    assert pss > SystemVerilogLexer.analyse_text(text), name


def test_a_c_file_does_not_look_like_pss():
    """The one that matters: no signature may fire on ordinary C."""
    assert PSSLexer.analyse_text(C_SOURCE) == 0.0


def test_a_systemverilog_file_does_not_look_like_pss():
    """The near miss, and the reason `constraint` is not a signature.

    `SystemVerilogLexer` has no `analyse_text` of its own -- it scores 0.0 on
    its own source. So *any* non-zero PSS score on a SystemVerilog file wins
    the guess outright. DESIGN.md section 6.8 lists `constraint \\w*\\s*\\{` as a
    signature; it is dropped for exactly this reason.
    """
    assert SystemVerilogLexer.analyse_text(SV_SOURCE) == 0.0, (
        "SystemVerilogLexer grew an analyse_text; the reasoning below may need "
        "revisiting"
    )
    assert PSSLexer.analyse_text(SV_SOURCE) == 0.0


def test_the_score_is_capped():
    """DESIGN.md section 6.8: never claim more than 0.3, however PSS-ish."""
    every_signature = textwrap.dedent(
        """\
        component pss_top {
            buffer b { }
            monitor m { }
            action a {
                constraint c { x > 0; }
                activity { do other_a; }
                exec body { }
            }
        }
        """
    )
    assert PSSLexer.analyse_text(every_signature) == 0.3


def test_an_empty_file_scores_nothing():
    assert PSSLexer.analyse_text("") == 0.0
