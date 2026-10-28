"""Staleness inputs, the work kind's outcomes and the edit validation, without a database (`CMP-MATRIX-01`)."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.comparison.matrix import settings
from auditmanager.comparison.matrix.handler import (
    MatrixBuildHandler,
    REASON_DOCUMENT_NOT_FOUND,
    REASON_PAYLOAD_INVALID,
    REASON_PROFILES_MISSING,
    WAIT_FOR_PROFILES_SECONDS,
    matrix_build_handler,
    read_payload,
)
from auditmanager.comparison.matrix.inputs import (
    profile_digest,
    profile_progress,
    profiles_complete,
    resolve_order,
    stale_reasons,
    versions_missing_profiles,
)
from auditmanager.comparison.matrix.model import BuildRecord, PageRef
from auditmanager.comparison.matrix.repository import ProfileFact
from auditmanager.comparison.matrix.service import BuildResult, ComparisonMatrixService, EditInput
from auditmanager.comparison.work.model import Completed, Failed, Yielded
from auditmanager.shared.errors import DomainError, ErrorCode

DOC = "doc_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def fact(version: str, number: int, key: str = "k", status: str = "ready") -> ProfileFact:
    return ProfileFact(f"cpr_{version}{number}", version, number, key * 64 if len(key) == 1 else key, status)


def build(order=("A", "B"), digest="d" * 64, order_id=None, algo=settings.ALGO_VERSION, rules=settings.RULES_VERSION) -> BuildRecord:
    return BuildRecord("cmx_1", 1, order_id, digest, rules, algo, [], [], {"order": list(order)}, datetime(2026, 10, 28, tzinfo=timezone.utc))


# -- the digest and the reasons ---------------------------------------------------------------------------------


def test_the_digest_does_not_depend_on_the_order_of_the_rows_and_does_on_every_part_of_a_row() -> None:
    rows = [fact("A", 1), fact("A", 2), fact("B", 1)]
    assert profile_digest(rows) == profile_digest(list(reversed(rows)))
    for changed in (fact("A", 1, key="z"), fact("A", 1, status="needs_review"), fact("C", 1), fact("A", 3)):
        assert profile_digest([changed, *rows[1:]]) != profile_digest(rows)
    assert profile_digest(rows + [fact("A", 3)]) != profile_digest(rows)


def test_the_stale_reasons_are_the_two_the_contract_names() -> None:
    now = profile_digest([fact("A", 1)])
    current = build(digest=now)
    assert stale_reasons(current, order=["A", "B"], order_id=None, digest=now) == []
    assert stale_reasons(current, order=["B", "A"], order_id=None, digest=now) == ["order_changed"]
    assert stale_reasons(current, order=["A", "B"], order_id="cvo_x", digest=now) == ["order_changed"]
    assert stale_reasons(current, order=["A", "B"], order_id=None, digest="e" * 64) == ["profiles_changed"]
    assert stale_reasons(current, order=["B", "A"], order_id=None, digest="e" * 64) == ["order_changed", "profiles_changed"]
    assert stale_reasons(build(digest=now, algo="cmp-matrix/0"), order=["A", "B"], order_id=None, digest=now) == ["profiles_changed"]
    assert stale_reasons(build(digest=now, rules="v1.1"), order=["A", "B"], order_id=None, digest=now) == ["profiles_changed"]


def test_the_order_is_the_latest_revision_then_the_versions_it_does_not_list() -> None:
    assert resolve_order(None, ["A", "B", "C"]) == ["A", "B", "C"]
    assert resolve_order((), ["A", "B", "C"]) == ["A", "B", "C"]
    assert resolve_order(("C", "A", "B"), ["A", "B", "C"]) == ["C", "A", "B"]
    assert resolve_order(("B", "A"), ["A", "B", "C"]) == ["B", "A", "C"], "a version published after the revision follows it"
    assert resolve_order(("B", "X", "A"), ["A", "B"]) == ["B", "A"], "a version the document does not have is dropped"


def test_progress_and_completeness_count_pages_by_status() -> None:
    facts = [fact("A", 1), fact("A", 2, status="needs_review"), fact("B", 1)]
    counts = {"A": 2, "B": 2}
    assert profile_progress(facts, counts) == {"total": 4, "ready": 2, "failed": 1}
    assert profiles_complete(facts, counts) is False
    assert versions_missing_profiles(facts, ["A", "B"], counts) == (["B"], ["A"])
    assert profiles_complete(facts + [fact("B", 2)], counts) is True
    assert versions_missing_profiles(facts + [fact("B", 2)], ["A", "B"], counts) == ([], ["A"])


# -- the work kind ----------------------------------------------------------------------------------------------


class FakeService:
    def __init__(self, result: BuildResult | None = None, raises: BaseException | None = None, pending: bool = False,
                 at_checkpoint: BaseException | None = None) -> None:
        self.result, self.raises, self.pending, self.at_checkpoint = result, raises, pending, at_checkpoint
        self.calls: list[dict[str, Any]] = []

    def build_matrix(self, **kwargs: Any) -> BuildResult:
        self.calls.append(kwargs)
        if self.at_checkpoint is not None:
            kwargs["checkpoint"]()
        if self.raises is not None:
            raise self.raises
        assert self.result is not None
        return self.result

    def profiles_pending(self, **kwargs: Any) -> bool:
        return self.pending


class FakeSession:
    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def commit(self) -> None:
        return None


def item(payload: dict[str, Any] | None = None, *, holds: bool = True, cancel: bool = False, lease_gone: bool = False):
    sessions = SimpleNamespace(factory=lambda: FakeSession())
    work = SimpleNamespace(heartbeat=lambda session, authority: holds, cancel_requested=lambda session, work_id: cancel)
    checked: list[str] = []
    value = SimpleNamespace(
        work_id="cq_X", attempt_no=1, project_uid="prj_X", payload={"document_uid": DOC} if payload is None else payload,
        authority=object(), lease_lost=threading.Event(), cancelled=threading.Event(),
        check_current=lambda session: checked.append("c"),
        require_current=lambda session: None,
    )
    if lease_gone:
        value.lease_lost.set()
    return value, SimpleNamespace(session_factory=sessions.factory, work=work, blob_store=None, engine=None), checked


def handler(service: FakeService, dependencies: Any) -> MatrixBuildHandler:
    return MatrixBuildHandler(dependencies, service=service)  # type: ignore[arg-type]


def test_the_factory_costs_nothing_and_the_kind_is_matrix_build() -> None:
    made = matrix_build_handler(SimpleNamespace())  # type: ignore[arg-type]
    assert made.kind == "matrix_build"


def test_the_payload_is_exactly_the_document() -> None:
    assert read_payload({"document_uid": DOC}) == DOC
    for bad in ({}, {"document_uid": 7}, {"document_uid": "x"}, {"document_uid": DOC, "extra": 1}, {"document_uid": "ver_" + DOC[4:]}):
        with pytest.raises(ValueError):
            read_payload(bad)


def test_a_payload_of_another_shape_fails_at_once_and_builds_nothing() -> None:
    it, deps, _ = item({"document_uid": "nope"})
    service = FakeService(BuildResult("built"))
    assert handler(service, deps).run(it) == Failed(REASON_PAYLOAD_INVALID) and service.calls == []


def test_a_built_or_existing_matrix_completes_the_item() -> None:
    for outcome in ("built", "existing"):
        it, deps, checked = item()
        service = FakeService(BuildResult(outcome))
        assert handler(service, deps).run(it) == Completed()
        assert service.calls[0]["project_uid"] == "prj_X" and service.calls[0]["document_uid"] == DOC
        assert service.calls[0]["publish_guard"] == it.require_current, "the lease fence runs in the publishing transaction"
        assert checked, "the lease is proved before the build"


def test_missing_profiles_with_a_profile_item_still_to_run_wait_and_with_none_fail_without_a_retry() -> None:
    it, deps, _ = item()
    waiting = handler(FakeService(BuildResult("incomplete", missing=("ver_A",)), pending=True), deps).run(it)
    assert waiting == Yielded(delay_seconds=WAIT_FOR_PROFILES_SECONDS)
    it, deps, _ = item()
    stuck = handler(FakeService(BuildResult("incomplete", missing=("ver_A",)), pending=False), deps).run(it)
    assert stuck == Failed(REASON_PROFILES_MISSING) and stuck.retry is False


def test_a_cancel_or_a_lost_lease_between_versions_yields_and_an_unknown_document_fails() -> None:
    it, deps, _ = item(cancel=True)
    cancelled = handler(FakeService(BuildResult("built"), at_checkpoint=RuntimeError("never")), deps).run(it)
    assert cancelled == Yielded() and it.cancelled.is_set()
    it, deps, _ = item(holds=False)
    assert handler(FakeService(BuildResult("built")), deps).run(it) == Yielded() and it.lease_lost.is_set()
    it, deps, _ = item(lease_gone=True)
    service = FakeService(BuildResult("built"))
    assert handler(service, deps).run(it) == Yielded() and service.calls == []
    it, deps, _ = item()
    gone = handler(FakeService(raises=DomainError(ErrorCode.NOT_FOUND, aggregate_type="Document")), deps).run(it)
    assert gone == Failed(REASON_DOCUMENT_NOT_FOUND)


def test_the_fence_refusing_the_publish_yields_and_any_other_failure_reaches_the_runner() -> None:
    it, deps, _ = item()
    fenced = handler(FakeService(raises=DomainError(ErrorCode.STALE_ATTEMPT)), deps).run(it)
    assert fenced == Yielded() and it.lease_lost.is_set()
    it, deps, _ = item()
    with pytest.raises(RuntimeError):
        handler(FakeService(raises=RuntimeError("boom")), deps).run(it)


# -- the validation of a batch -----------------------------------------------------------------------------------

COUNTS = {"ver_A": 3, "ver_B": 2}


def edit(kind: str, page: PageRef, other: PageRef | None = None, absent: str | None = None) -> EditInput:
    return EditInput(kind=kind, page=page, other_page=other, absent_version_uid=absent)


def refused(*edits: EditInput, index: dict | None = None) -> bool:
    try:
        ComparisonMatrixService._validate(edits, COUNTS, index or {})
    except DomainError as failure:
        assert failure.code is ErrorCode.VALIDATION_FAILED
        assert failure.detail_fields == {"field": "edits", "constraint": "comparison_edit_invalid"}
        return True
    return False


def test_a_batch_is_valid_only_for_pages_inside_their_versions_and_members_the_kind_takes() -> None:
    a1, a3, b2 = PageRef("ver_A", 1), PageRef("ver_A", 3), PageRef("ver_B", 2)
    assert not refused(edit("link", a1, b2), edit("unlink", a3), edit("mark_absent", a1, absent="ver_B"))
    assert refused(edit("unlink", PageRef("ver_A", 4)))  # past the version's last page
    assert refused(edit("unlink", PageRef("ver_A", 0)))
    assert refused(edit("unlink", PageRef("ver_Z", 1)))  # not a version of the document
    assert refused(edit("link", a1, PageRef("ver_A", 2)))  # joins a version to itself
    assert refused(edit("link", a1, PageRef("ver_B", 3)))  # the other page is outside its version
    assert refused(edit("link", a1))  # needs the other page
    assert refused(edit("unlink", a1, b2)) and refused(edit("unlink", a1, absent="ver_B"))
    assert refused(edit("mark_absent", a1)) and refused(edit("mark_absent", a1, absent="ver_A"))
    assert refused(edit("mark_absent", a1, absent="ver_Z")) and refused(edit("mark_absent", a1, b2, absent="ver_B"))
    assert refused(edit("undo", a1)), "an undo is asked for with its own operation"
    # a profile identity the build contradicts is refused; one it agrees with, or does not know, is not
    index = {("ver_A", 1): "cpr_known"}
    assert refused(edit("unlink", PageRef("ver_A", 1, "cpr_other")), index=index)
    assert not refused(edit("unlink", PageRef("ver_A", 1, "cpr_known")), index=index)
    assert not refused(edit("unlink", PageRef("ver_A", 2, "cpr_anything")), index=index)


def test_a_batch_over_the_limit_is_its_own_refusal() -> None:
    service = ComparisonMatrixService(session_factory=None)  # type: ignore[arg-type]
    with pytest.raises(DomainError) as failure:
        service.apply_edits(
            project_uid="prj_X", document_uid=DOC, base_matrix_id="cmx_X", base_edit_no=0,
            edits=[edit("unlink", PageRef("ver_A", 1))] * 501, user_uid="usr_X", actor_label="Т",
            actor_roles=frozenset({"expert"}), idempotency_key="k")
    assert failure.value.detail_fields == {"field": "edits", "constraint": "comparison_edits_limit"}
    with pytest.raises(DomainError) as failure:
        service.apply_edits(
            project_uid="prj_X", document_uid=DOC, base_matrix_id="cmx_X", base_edit_no=0,
            edits=[edit("unlink", PageRef("ver_A", 1))], user_uid="usr_X", actor_label="Т",
            actor_roles=frozenset({"admin"}), idempotency_key="k")
    assert failure.value.code is ErrorCode.PERMISSION_DENIED, "the role is checked before anything is read"
