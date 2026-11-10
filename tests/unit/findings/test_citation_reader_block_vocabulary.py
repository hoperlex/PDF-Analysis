"""The citation reader's block vocabulary is the candidate publisher's, word for word (D-685).

The reader is an unserved, self-contained read and does not import the publisher; this suite is what keeps the two lists from drifting.
"""

from __future__ import annotations

from auditmanager.findings import citation_reader
from auditmanager.findings.artifacts import GROUNDING_PORTAL_BLOCK, GROUNDING_TEXT_SPAN
from auditmanager.findings.publication import (
    CATEGORY_CROSS_SOURCE,
    CATEGORY_DRAWING_DISCREPANCY,
    STAGE_BLOCK_ANALYSIS,
    STAGE_FINDING_MERGE,
)


def test_the_reader_reads_the_stages_and_categories_the_publisher_writes() -> None:
    assert set(citation_reader._STAGES_BY_GROUNDING) == {GROUNDING_TEXT_SPAN, GROUNDING_PORTAL_BLOCK}
    assert citation_reader._STAGES_BY_GROUNDING[GROUNDING_PORTAL_BLOCK] == {STAGE_BLOCK_ANALYSIS, STAGE_FINDING_MERGE}
    assert citation_reader._STAGES_BY_GROUNDING[GROUNDING_TEXT_SPAN] == {"text_analysis"}
    assert citation_reader._BLOCK_CATEGORIES == {CATEGORY_DRAWING_DISCREPANCY, CATEGORY_CROSS_SOURCE}


def test_no_block_category_is_a_norm_or_a_text_category() -> None:
    known = citation_reader._NORMATIVE | citation_reader._NON_NORMATIVE
    assert not citation_reader._BLOCK_CATEGORIES & known
