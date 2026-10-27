"""The run CSV's rule and the optimisation CSV's rule, side by side (`ACCESS-COMPARE-JUDGE-FIXES-01`).

Two files this system writes are opened in a spreadsheet, and each neutralises a text cell that could
be read as a formula: the run CSV by ``auditmanager.shared.spreadsheet.neutralise_formula`` and the
proposals CSV by its own ``escape_formula`` (``auditmanager.optimisation.proposals``). They are not the
same function. The proposals CSV looks past plain spaces and treats a line feed as a trigger; the run
CSV now also steps over a no-break space, a byte-order mark and the zero-width characters, knows the
fullwidth forms of ``= + - @``, and does not neutralise a cell that is blanks followed by a control
character and nothing dangerous. Adopting the shared function in the proposals CSV would change the
bytes of the cells in the last two columns of the table below, so it was not done; this test pins the
relation, so neither rule can move without the other being looked at.

Each row is ``(cell, run CSV neutralises, proposals CSV neutralises)``.
"""

from __future__ import annotations

import pytest

from auditmanager.optimisation.proposals.public import escape_formula
from auditmanager.shared.spreadsheet import neutralise_formula

AGREE_YES = [
    "=1+1", "+1", "-5", "@SUM(A1)", "\tx", "\rx", "\nx", "  =1+1", " \n=1", " +1",
]
AGREE_NO = ["", "plain", " x", "a=b", "x =1", "'=1", "5", "·=1", " "]
# blanks, then a control character, then nothing dangerous: only the proposals CSV neutralises
ONLY_PROPOSALS = [" \nx", " \tx", "  \rtext"]
# invisible or fullwidth in front of a trigger: only the run CSV neutralises
ONLY_RUN = [
    " =1", "﻿=1", "​=1", "‌+1", "‍-1", "⁠@x", "＝1", "＋1",
    "－1", "＠x", "  ﻿=1",
]


@pytest.mark.parametrize("value", AGREE_YES)
def test_both_neutralise(value: str) -> None:
    assert neutralise_formula(value) == "'" + value == escape_formula(value)


@pytest.mark.parametrize("value", AGREE_NO)
def test_neither_neutralises(value: str) -> None:
    assert neutralise_formula(value) == value == escape_formula(value)


@pytest.mark.parametrize("value", ONLY_PROPOSALS)
def test_only_the_proposals_csv_neutralises_blanks_then_a_harmless_control_character(
    value: str,
) -> None:
    assert neutralise_formula(value) == value
    assert escape_formula(value) == "'" + value


@pytest.mark.parametrize("value", ONLY_RUN)
def test_only_the_run_csv_neutralises_invisible_or_fullwidth_triggers(value: str) -> None:
    assert neutralise_formula(value) == "'" + value
    assert escape_formula(value) == value
