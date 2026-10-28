"""The adapter's answer to ``generateComparisonSummary`` carries the command's own ``is_current``.

``ComparisonAdapter.generate_comparison_summary`` used to write ``is_current=True`` whatever the command
decided, so a replay with an old idempotency key after a pair was withdrawn answered an old row as the
current one. The rule itself is tested against PostgreSQL in
``tests/integration/comparison/test_comparison_summary_db.py``; this file pins the seam: the flag the
service computed is the flag the response carries, in both directions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from auditmanager.bootstrap.adapters import ComparisonAdapter
from auditmanager.comparison.summaries import StoredSummary, SummaryOutcome

SUMMARY = StoredSummary(
    summary_id="evt_01M2545JSD15ETSNNV904XH001", comparison_id="cmp_1", link_revision=1,
    project_uid="prj_01M2545JSD15ETSNNV904XH001", raw_evidence_seal_sha256="a" * 64,
    input_sha256="b" * 64, request_sha256="c" * 64, prompt_version="comparison-summary-v1",
    provider_mode="recorded", model_identity="recorded", state="ready", rejection_reason=None,
    statements=(), cost_basis="unmetered", cost_micros=0, actor_user_uid="usr_01M2545JSD15ETSNNV904XH001",
    actor_label="Иванов И. И.", command_id="cmd_1",
    created_at=datetime(2026, 10, 28, tzinfo=timezone.utc),
)


class _Summaries:
    def __init__(self, outcome: SummaryOutcome) -> None:
        self.outcome = outcome

    def generate(self, session, request, **_kwargs):
        return self.outcome


def _answer(monkeypatch: pytest.MonkeyPatch, outcome: SummaryOutcome):
    import auditmanager.access.public as access
    import auditmanager.api.routers.correlation as correlation

    monkeypatch.setattr(access, "AccountRepository", lambda: SimpleNamespace(
        roles_of=lambda session, uid: frozenset({"expert"})))
    monkeypatch.setattr(correlation, "current_correlation_id", lambda: None)
    adapter = object.__new__(ComparisonAdapter)
    adapter._summaries = _Summaries(outcome)  # type: ignore[attr-defined]
    adapter._write = lambda work: work(None)  # type: ignore[method-assign]
    return adapter.generate_comparison_summary(
        project_uid="prj_01M2545JSD15ETSNNV904XH001", document_uid="doc_01M2545JSD15ETSNNV904XH001",
        source_version_uid="ver_01M2545JSD15ETSNNV904XH001",
        target_version_uid="ver_01M2545JSD15ETSNNV904XH002", mode="version", source_run_id=None,
        target_run_id=None, idempotency_key="key-1", author_label="Иванов И. И.",
        author_user_uid="usr_01M2545JSD15ETSNNV904XH001",
    )


@pytest.mark.parametrize(("replayed", "is_current"), [
    (True, False), (True, True), (False, True), (False, False),
])
def test_the_response_carries_the_flag_the_service_decided(
    monkeypatch: pytest.MonkeyPatch, replayed: bool, is_current: bool
) -> None:
    response = _answer(monkeypatch, SummaryOutcome(SUMMARY, replayed, is_current))
    assert (response.replayed, response.summary.is_current) == (replayed, is_current)
    assert response.summary.summary_id == SUMMARY.summary_id


# The rule that decides the flag, one condition at a time. A real set cannot show revision and seal
# apart (the seal covers the revision), so the conditions are exercised on the pure function.
def _evidence(*, seal="a" * 64, revision=1, comparison_id="cmp_1", sealed=True):
    from auditmanager.comparison.service import SealedEvidence

    return SealedEvidence(
        pair=None,  # type: ignore[arg-type]
        comparison_id=comparison_id, link_revision=revision, raw_diffs=(),
        seal=SimpleNamespace(seal_sha256=seal) if sealed else None,  # type: ignore[arg-type]
    )


@pytest.mark.parametrize(("evidence", "expected"), [
    (_evidence(), True),
    (None, False),                              # the comparison is refused now
    (_evidence(sealed=False), False),           # a pair's text changed, or nothing is approved
    (_evidence(revision=2), False),             # the set moved on, the seal left equal
    (_evidence(seal="d" * 64), False),          # same revision, another seal
    (_evidence(comparison_id="cmp_2"), False),  # another comparison
], ids=["current", "refused", "unsealed", "revision", "seal", "comparison"])
def test_a_stored_summary_is_current_only_for_the_same_comparison_revision_and_seal(evidence, expected) -> None:
    from auditmanager.comparison.summaries import _describes

    assert _describes(SUMMARY, evidence) is expected
