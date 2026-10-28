"""What the overview copies from the other lanes is pinned to them (`CMP-VC-OVERVIEW-01`).

The overview reads rows set-wise and applies the other lanes' pure rules; the three work kinds it looks for, the dedupe
keys it parses and the states it treats as live are written here once and must equal the lanes' own, so a rename in
`CMP-MATRIX-01`, `CMP-PROFILE-QUEUE-01`, `CMP-SERIES-01` or `CMP-WORK-01` turns this red instead of turning a step silently
``not_started``.
"""

from __future__ import annotations

from auditmanager.comparison.matrix.repository import _LIVE_STATES as MATRIX_LIVE_STATES  # noqa: PLC2701
from auditmanager.comparison.matrix.service import MATRIX_BUILD_KIND, matrix_build_dedupe_key
from auditmanager.comparison.overview import repository as overview_repository
from auditmanager.comparison.overview import rules
from auditmanager.comparison.overview.service import QUEUE_STATES, _page_profile_version
from auditmanager.comparison.profile_queue.enqueue import page_profile_dedupe_key
from auditmanager.comparison.profile_queue.handler import PAGE_PROFILE_KIND
from auditmanager.comparison.series.followup import follow_up_dedupe_key
from auditmanager.comparison.series.model import SERIES_AFTER_PREPARATION_KIND, SERIES_LIVE
from auditmanager.comparison.work.model import LIVE_STATES, WORK_STATES

VERSION = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"
DOCUMENT = "doc_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def test_the_three_work_kinds_are_the_lanes_own() -> None:
    assert overview_repository.KIND_PAGE_PROFILE == PAGE_PROFILE_KIND
    assert overview_repository.KIND_MATRIX_BUILD == MATRIX_BUILD_KIND
    assert overview_repository.KIND_FOLLOW_UP == SERIES_AFTER_PREPARATION_KIND


def test_the_dedupe_keys_the_overview_parses_are_the_lanes_own() -> None:
    assert _page_profile_version(page_profile_dedupe_key(VERSION)) == VERSION
    assert _page_profile_version(page_profile_dedupe_key(VERSION, retry_failed=True)) == VERSION
    assert _page_profile_version(None) is None and _page_profile_version("matrix_build:" + DOCUMENT) is None
    assert matrix_build_dedupe_key(DOCUMENT) == "matrix_build:" + DOCUMENT
    assert follow_up_dedupe_key("cus_1").startswith(SERIES_AFTER_PREPARATION_KIND + ":")


def test_the_live_states_are_the_queues_and_the_matrix_lanes() -> None:
    assert rules.LIVE_WORK_STATES == frozenset(LIVE_STATES) == frozenset(MATRIX_LIVE_STATES)
    assert set(overview_repository._LIVE) == set(LIVE_STATES)  # noqa: SLF001
    assert rules.SERIES_LIVE_STATES == frozenset(SERIES_LIVE)


def test_the_queue_states_are_the_nine_of_the_queue_in_the_contracts_order() -> None:
    assert set(QUEUE_STATES) == set(WORK_STATES) and len(QUEUE_STATES) == 9
    assert QUEUE_STATES[:3] == ("queued", "leased", "running")
