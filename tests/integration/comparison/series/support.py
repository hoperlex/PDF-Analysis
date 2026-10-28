"""Helpers of the series integration tests (`CMP-SERIES-01`): the calls an expert makes, a scripted engine, a runner."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from typing import Any
from unittest import mock

from sqlalchemy import text

from auditmanager.comparison.engine.child.status import FORCING_REASONS
from auditmanager.comparison.engine.repository import PairResultRepository
from auditmanager.comparison.engine.service import PairOutcome
from auditmanager.shared.db import session_scope
from auditmanager.shared.identity import new_ulid

EXPERT = frozenset({"expert"})
ADMIN = frozenset({"admin"})
LABEL = "Эксперт Т."


def key() -> str:
    return f"series-{new_ulid()}"


def build(matrix_service: Any, doc: Any) -> dict[str, Any]:
    """The algorithmic matrix of the document (no worker): the clone's profile rows are the input."""
    result = matrix_service.build_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid)
    assert result.outcome in ("built", "existing"), result
    state = matrix_service.get_matrix(project_uid=doc.project_uid, document_uid=doc.document_uid)
    assert state["state"] == "ready", state["state"]
    return state


def start(service: Any, doc: Any, user: str, *, restart: bool = False, base: int | None = None,
          idempotency_key: str | None = None, roles: frozenset[str] = EXPERT) -> dict[str, Any]:
    return service.start_series(
        project_uid=doc.project_uid, document_uid=doc.document_uid, restart=restart, base_order_revision_no=base,
        user_uid=user, actor_label=LABEL, actor_roles=roles, idempotency_key=idempotency_key or key())


def steer(service: Any, verb: str, series_id: str, user: str, *, idempotency_key: str | None = None,
          roles: frozenset[str] = EXPERT) -> dict[str, Any]:
    return getattr(service, f"{verb}_series")(
        series_id=series_id, user_uid=user, actor_roles=roles, idempotency_key=idempotency_key or key())


class ScriptedEngine:
    """A stand-in for ``compare_sheet_pair`` that writes a real result row and records every call.

    ``script`` maps ``(page_a_profile_id, page_b_profile_id)`` to a status (default ``default``); a status of ``raise``
    raises ``boom``. The result row is the engine's own repository insert under the caller's fence, so the foreign keys,
    the project trigger and the unique content key of the table all apply."""

    def __init__(self, sessions: Any, *, default: str = "same", script: dict[tuple[str, str], str] | None = None,
                 evidence: dict[str, Any] | None = None, part: dict[str, Any] | None = None,
                 part_script: dict[tuple[str, str], dict[str, Any]] | None = None) -> None:
        self.sessions = sessions
        self.default = default
        self.script = dict(script or {})
        self.evidence = evidence
        self.part = part
        self.part_script = dict(part_script or {})
        self.calls: list[dict[str, Any]] = []
        self.boom: Exception | None = None
        #: Called inside every comparison, before the result is written: where a test makes the world move mid-pair.
        self.on_call: Callable[..., None] | None = None
        #: Called after the result is written and before the comparison returns: where a lease is lost between the two.
        self.after_call: Callable[..., None] | None = None

    def __call__(self, session_factory: Any, blob_store: Any, *, project_uid: str, page_a_profile_id: str | None,
                 page_b_profile_id: str | None, link_reasons: Sequence[str] = (), part: str | None = None,
                 runner: Any = None, before_publish: Callable[[], None] | None = None,
                 fence: Callable[[Any], None] | None = None, **_ignored: Any) -> PairOutcome:
        self.calls.append({"a": page_a_profile_id, "b": page_b_profile_id, "reasons": tuple(link_reasons), "part": part})
        if self.on_call is not None:
            self.on_call(page_a_profile_id, page_b_profile_id)
        status = self.script.get((page_a_profile_id, page_b_profile_id), self.default)
        if status == "raise":
            assert self.boom is not None
            raise self.boom
        if FORCING_REASONS & set(link_reasons):  # the original's rule: a forcing link reason is a review (``status.py:45-66``)
            status = "needs_review"
        if before_publish is not None:
            before_publish()
        content_key = hashlib.sha256(json.dumps(
            [project_uid, page_a_profile_id, page_b_profile_id, sorted(link_reasons), part], sort_keys=True).encode()).hexdigest()
        reasons = sorted(set(link_reasons) - {"AI_MATCH", "TABLE_GROUP"})
        if status == "needs_review" and not reasons:
            reasons = ["NO_TEXT_LAYER"]
        result: dict[str, Any] = {
            "format": 1, "canvas": {"width_pt": 1190.55, "height_pt": 841.89}, "differences": [], "text_changes": [],
            "service_notes": [], "how_compared": {"algo_version": "scripted", "dpi": 50, "tolerance_pt": 0.5},
            "aligned_blocks": [], "mask": None,
        }
        if self.evidence is not None and status in ("different", "needs_review"):
            result |= self.evidence
        if part is not None and (self.part is not None or (page_a_profile_id, page_b_profile_id) in self.part_script):
            result["part"] = {"kind": part, **self.part_script.get((page_a_profile_id, page_b_profile_id), self.part or {})}
        with session_scope(self.sessions) as session:
            if fence is not None:
                fence(session)
            repository = PairResultRepository()
            result_id = repository.insert(
                session, project_uid=project_uid, content_key=content_key, algo_version="scripted", status=status,
                reasons=reasons, channels={"text": {"state": "checked", "diffs": 0 if status == "same" else 1}},
                result=result, page_a_profile_id=page_a_profile_id, page_b_profile_id=page_b_profile_id,
                mask_blob_id=None)
            if result_id is None:
                found = repository.find(session, project_uid, content_key)
                assert found is not None
                result_id = found.result_id
        if self.after_call is not None:
            self.after_call(page_a_profile_id, page_b_profile_id)
        return PairOutcome(status=status, result_id=result_id, reasons=tuple(reasons))


@contextmanager
def fenced(engine: Any, project: str, hold_kinds: tuple[str, ...] = ()) -> Iterator[None]:
    """Lock every queued item that is not this project's (or that is of a held kind) so a claim skips it."""
    with engine.connect() as fence:
        fence.execute(text(
            "SELECT comparison_work_id FROM comparison_work WHERE state = 'queued' AND (project_uid <> :p "
            "OR kind = ANY (CAST(:k AS text[]))) ORDER BY comparison_work_id FOR UPDATE SKIP LOCKED"),
            {"p": project, "k": list(hold_kinds)})
        try:
            yield
        finally:
            fence.rollback()


def make_due(sessions: Any, project: str, *, except_kind: str | None = None) -> None:
    """Every queued item of the project is due now (a yield put its next look in the future)."""
    with sessions() as session:
        session.execute(text("UPDATE comparison_work SET not_before = clock_timestamp() - interval '1 second' "
                             "WHERE project_uid = :p AND state = 'queued' AND kind IS DISTINCT FROM :k"),
                        {"p": project, "k": except_kind})
        session.commit()


def runner_with(sessions: Any, engine: Any, blob_store: Any, *, compare: Callable[..., PairOutcome] | None = None) -> Any:
    """The comparison runner the worker builds from the shipped tuple, with the pair comparison replaced by ``compare``
    (the real engine when ``None``). The Run-priority gate reads nothing, so a claim sees only comparison work."""
    from auditmanager.bootstrap import composition
    from auditmanager.comparison.public import ClaimGates, default_gates, series_pair_handler
    from auditmanager.comparison.series import SeriesPairHandler

    factories = composition.COMPARISON_HANDLER_FACTORIES
    if compare is not None:
        factories = tuple(
            (lambda deps, _c=compare: SeriesPairHandler(deps, compare=_c)) if f is series_pair_handler else f
            for f in factories)
    gates = lambda: ClaimGates(paused=default_gates().paused, run_claimable=lambda session: False)  # noqa: E731
    with mock.patch.object(composition, "COMPARISON_HANDLER_FACTORIES", factories), \
            mock.patch("auditmanager.comparison.work.runner.default_gates", gates):
        return composition.build_comparison_work(
            sessions=sessions, engine=engine, blob_store=blob_store,
            environ={"AUDITMANAGER_COMPARISON_MODULES": "versions"})


def drain(runner: Any, worker_id: str, engine: Any, sessions: Any, project: str, *, rounds: int = 60,
          limit: int = 400, hold: tuple[str, ...] = ()) -> list[tuple[str, str]]:
    """Claim and execute the project's items until none is claimable; ``[(kind, resulting state), ...]``.

    The polling item (``series_drive``) has the strongest priority and yields to its next look, so it is taken only when
    nothing else is claimable (as the 15 s of its delay let the pairs go first in a worker), and then once. ``hold`` names
    kinds that are not claimed at all."""
    ran: list[tuple[str, str]] = []
    for _ in range(rounds):
        while len(ran) < limit:
            make_due(sessions, project, except_kind="series_drive")
            with fenced(engine, project, ("series_drive", *hold)):
                item = runner.claim(worker_id)
            if item is None:
                break
            assert item.project_uid == project
            ran.append((item.kind, runner.execute(item)))
        make_due(sessions, project)
        with fenced(engine, project, hold):
            item = runner.claim(worker_id)
        if item is None:
            break
        ran.append((item.kind, runner.execute(item)))
    return ran


def pair_rows(lab: Any, series_id: str) -> list[dict[str, Any]]:
    return lab.rows(
        "SELECT t.transition_no, p.pair_no, p.comparison_sheet_pair_id AS id, p.state, p.status, p.page_a_profile_id AS a, "
        "p.page_b_profile_id AS b, p.confidence, p.flags, p.result_id, p.ai_dependent, p.permit, p.parts, p.failure_reason "
        "FROM comparison_sheet_pair p JOIN comparison_transition t ON t.comparison_transition_id = p.comparison_transition_id "
        "WHERE t.comparison_series_id = :s ORDER BY t.transition_no, p.pair_no", s=series_id)


def items(lab: Any, series_id: str) -> list[dict[str, Any]]:
    return lab.rows(
        "SELECT comparison_work_id AS id, kind, state, dedupe_key, priority, comparison_series_id, failure_reason, payload "
        "FROM comparison_work WHERE comparison_series_id = :s ORDER BY created_at, comparison_work_id", s=series_id)


def expire_lease(sessions: Any, work_id: str) -> None:
    """The holder's lease ran out (and nobody has reclaimed it yet): the state a stalled worker is in."""
    with sessions() as session:
        session.execute(text(
            "UPDATE comparison_work_attempt SET lease_expires_at = clock_timestamp() - interval '5 minutes' "
            "WHERE comparison_work_id = :w AND state IN ('leased', 'running')"), {"w": work_id})
        session.commit()
