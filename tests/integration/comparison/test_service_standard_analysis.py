"""`AR-V3-OPT-IN` (`Q3`, `Q5`): a comparison reads the standard analysis and never mixes it with AR v3.

The version half is real (the rows of `test_service_db.py`); the runs come from a port fake that marks each candidate
as of the standard analysis or not -- the composition root's reader derives that mark from the run's pinned pair
(`tests/integration/dashboard/test_ar_v3_never_displaces_the_standard_result.py` proves that half on real rows).

* the default run of a side is its newest PUBLISHED run of the standard analysis; a published v3 run, however new, is
  skipped, and a side whose only published run is v3 has no analysis (`analysis_missing`);
* a run the caller NAMES that is a v3 run is refused as `analysis_not_comparable`, with its side, whatever its state;
* every other refusal and the happy path are as they were (the existing suite, unchanged, proves it).
"""

from __future__ import annotations

from auditmanager.comparison.public import (
    OUTCOME_COMPARED,
    OUTCOME_REFUSED,
    REFUSAL_REASONS,
    ComparisonRequest,
    RunCandidate,
    SavedPageText,
    VersionComparisonService,
)
from tests.integration.comparison.test_service_db import (  # type: ignore[import-not-found]
    DOCUMENT,
    PROJECT,
    R1,
    R2,
    SOURCE_PAGES,
    TARGET_PAGES,
    V1,
    V2,
    _Classifications,
    _seed,
)

V3_NEW = "run_01M2545JSD15ETSNNV904XB001"
V3_OLD = "run_01M2545JSD15ETSNNV904XB002"


class _Analyses:
    """Each version's runs, newest first, as the test sets them."""

    def __init__(self, runs: dict[str, tuple[RunCandidate, ...]]) -> None:
        self._runs = runs

    def runs_newest_first(self, session, *, version_uid):
        return self._runs.get(version_uid, ())

    def saved_page_text(self, session, *, run_id, version):
        # The seeded versions have 500 pages each; only the standard runs' text is ever read.
        return SavedPageText(run_id, "e" * 64, {R1: SOURCE_PAGES, R2: TARGET_PAGES}[run_id])

    def published_findings(self, session, *, run_id):
        return ()


def _service(runs: dict[str, tuple[RunCandidate, ...]]) -> VersionComparisonService:
    return VersionComparisonService(
        classifications=_Classifications({V1: ("R", "KJ"), V2: ("R", "KJ")}),
        analyses=_Analyses(runs),
        section_codes=frozenset({"AR", "KJ", "PS"}),
    )


def _request(**changes):
    return ComparisonRequest(**({
        "project_uid": PROJECT, "document_uid": DOCUMENT, "source_version_uid": V1, "target_version_uid": V2,
    } | changes))


def test_the_reason_is_declared_beside_the_other_run_refusals() -> None:
    assert REFUSAL_REASONS.index("analysis_not_comparable") == REFUSAL_REASONS.index("run_not_published") + 1


def test_a_newer_published_v3_run_does_not_become_the_default_run(comparison_session) -> None:
    _seed(comparison_session)
    result = _service({
        V1: (RunCandidate(R1, "published"),),
        V2: (RunCandidate(V3_NEW, "published", False), RunCandidate(R2, "published")),
    }).compare(comparison_session, _request())
    assert result.outcome == OUTCOME_COMPARED
    assert (result.source.run_id, result.target.run_id) == (R1, R2)


def test_a_side_whose_only_published_run_is_v3_has_no_analysis(comparison_session) -> None:
    _seed(comparison_session)
    result = _service({
        V1: (RunCandidate(V3_NEW, "published", False), RunCandidate(R1, "failed")),
        V2: (RunCandidate(R2, "published"),),
    }).compare(comparison_session, _request())
    assert (result.outcome, result.refusal.reason, result.refusal.side) == (OUTCOME_REFUSED, "analysis_missing", "source")


def test_a_v3_run_named_by_the_caller_is_refused_with_its_side_whatever_its_state(comparison_session) -> None:
    _seed(comparison_session)
    runs = {
        V1: (RunCandidate(V3_NEW, "published", False), RunCandidate(V3_OLD, "running", False), RunCandidate(R1, "published")),
        V2: (RunCandidate(R2, "published"),),
    }
    for named in (V3_NEW, V3_OLD):
        result = _service(runs).compare(comparison_session, _request(source_run_id=named))
        assert (result.outcome, result.refusal.reason, result.refusal.side) == (
            OUTCOME_REFUSED, "analysis_not_comparable", "source",
        ), named
        # Nothing was compared in its place.
        assert result.source is not None and result.source.run_id is None
    other_side = _service({V1: (RunCandidate(R1, "published"),), V2: (RunCandidate(V3_NEW, "published", False),)}).compare(
        comparison_session, _request(target_run_id=V3_NEW),
    )
    assert (other_side.refusal.reason, other_side.refusal.side) == ("analysis_not_comparable", "target")


def test_the_named_standard_run_and_the_older_refusals_are_unchanged(comparison_session) -> None:
    _seed(comparison_session)
    runs = {V1: (RunCandidate(R1, "published"),), V2: (RunCandidate(R2, "published"), RunCandidate(V3_NEW, "published", False))}
    named = _service(runs).compare(comparison_session, _request(target_run_id=R2))
    assert (named.outcome, named.target.run_id) == (OUTCOME_COMPARED, R2)
    foreign = _service(runs).compare(comparison_session, _request(source_run_id=R2))
    assert (foreign.refusal.reason, foreign.refusal.side) == ("run_not_of_version", "source")
    running = _service({V1: (RunCandidate(R1, "running"),), V2: runs[V2]}).compare(comparison_session, _request(source_run_id=R1))
    assert (running.refusal.reason, running.refusal.side) == ("run_not_published", "source")


def test_a_malformed_mark_is_an_integrity_error_not_a_guess(comparison_session) -> None:
    import pytest

    from auditmanager.comparison.public import ComparisonIntegrityError

    _seed(comparison_session)
    with pytest.raises(ComparisonIntegrityError):
        _service({V1: (RunCandidate(R1, "published", "yes"),), V2: (RunCandidate(R2, "published"),)}).compare(  # type: ignore[arg-type]
            comparison_session, _request(),
        )
