"""An end without a result is stored once, for that pair only, and is not retried by the cache (`CMP-ENGINE-01`,
ADR-0025 decision 8). The key is the content, so the next request for the pair finds the row and starts no child."""

from __future__ import annotations

import pytest

from auditmanager.comparison.engine import compare_sheet_pair
from auditmanager.comparison.profile.limits import MIB, ChildLimits
from auditmanager.comparison.profile.runner import ChildStartError


class _Refuses:
    calls = 0

    def run(self, settings, limits):
        type(self).calls += 1
        raise AssertionError("a pair found in the cache must not start a child")


def test_a_pair_whose_child_passes_the_address_space_is_stored_render_failed_and_is_not_computed_again(lane) -> None:
    project = lane.project()
    v1, v2 = lane.seed("vs1/v1.pdf", 6, project_uid=project), lane.seed("vs1/v2.pdf", 6, project_uid=project)
    kwargs = dict(project_uid=project, page_a_profile_id=v1.pages[2], page_b_profile_id=v2.pages[2])
    failed = compare_sheet_pair(lane.sessions, lane.blob_store, child_limits=ChildLimits(120 * MIB, 300, 600.0), **kwargs)
    assert failed.status == "needs_review" and failed.created and failed.mask_blob_id is None and failed.child_end in ("overrun", "error:ImportError")
    row = lane.results(project)[0]
    assert "RENDER_FAILED" in row["reasons"] and row["mask_blob_id"] is None and row["result"]["mask"] is None
    assert all(c["state"] == "unchecked" for c in row["channels"].values())

    again = compare_sheet_pair(lane.sessions, lane.blob_store, runner=_Refuses(), **kwargs)
    assert again.cached and again.result_id == failed.result_id and _Refuses.calls == 0

    # The next pair of the same project is unaffected.
    fine = compare_sheet_pair(lane.sessions, lane.blob_store, project_uid=project, page_a_profile_id=v1.pages[3],
                              page_b_profile_id=v2.pages[3])
    assert fine.status == "different" and fine.child_end == "ok"


def test_a_child_that_never_started_stores_nothing(lane) -> None:
    project = lane.project()
    v1, v2 = lane.seed("vs1/v1.pdf", 6, project_uid=project), lane.seed("vs1/v2.pdf", 6, project_uid=project)

    class Broken:
        def run(self, settings, limits):
            raise ChildStartError("the interpreter is gone")

    with pytest.raises(ChildStartError):
        compare_sheet_pair(lane.sessions, lane.blob_store, project_uid=project, page_a_profile_id=v1.pages[2],
                           page_b_profile_id=v2.pages[2], runner=Broken())
    assert lane.results(project) == []
