"""The two reads of `CMP-VC-OVERVIEW-01`: the overview of a project's document sets and the comparison queue summary.

``getComparisonOverview`` answers, for every document set of the project, the state of the seven steps, the step the chip
proposes, the counters and the totals, and the batches still being uploaded. It runs a **fixed number of statements** for
the project whatever the number of sets (the repository reads whole columns of the project at once and the service groups
them in memory), in **one read-only ``REPEATABLE READ`` transaction**: it can write nothing, and every number comes from the
same snapshot. Nothing is enqueued and no model is called.

The states are derived by the rules the other lanes already own -- the profile digest, the order of the versions, the stale
reasons and the effective matrix of the matrix lane; the input digest and the stale reasons of the series lane -- applied to
rows read for the whole project; ``tests/integration/comparison/overview`` proves that the result equals what
``ComparisonMatrixService.get_matrix`` and ``ComparisonSeriesService.list_series`` answer for the same set.

``getComparisonQueueSummary`` answers the whole installation's queue: the module set, the pause, the items by state and by
module and kind, and the age of the oldest queued item.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.engine.limits import ALGO_VERSION as ENGINE_ALGO_VERSION
from auditmanager.comparison.matrix.effective import effective_matrix
from auditmanager.comparison.matrix.inputs import (
    profile_digest,
    profile_progress,
    resolve_order,
)
from auditmanager.comparison.matrix.inputs import stale_reasons as matrix_stale_reasons
from auditmanager.comparison.matrix.model import AiLinkRecord, BuildRecord, EditRecord
from auditmanager.comparison.matrix.repository import ProfileFact
from auditmanager.comparison.overview import model as m
from auditmanager.comparison.overview import rules
from auditmanager.comparison.overview.model import STEP_ORDER, Step
from auditmanager.comparison.overview.repository import (
    KIND_FOLLOW_UP,
    KIND_MATRIX_BUILD,
    KIND_PAGE_PROFILE,
    MAX_SETS,
    DocumentRow,
    OrderRow,
    OverviewRepository,
    SeriesRow,
    SetMetaRow,
    TransitionRow,
    VersionRow,
    WorkRow,
)
from auditmanager.comparison.profile.limits import ALGO_VERSION as PAGE_PROFILE_ALGO_VERSION
from auditmanager.comparison.series.inputs import CurrentInputs, SeriesInputs, chain_of
from auditmanager.comparison.series.inputs import stale_reasons as series_stale_reasons
from auditmanager.documents.public import DocumentRepository
from auditmanager.shared.db import session_scope
from auditmanager.shared.identity import ProjectUid

__all__ = ["ComparisonOverviewService", "QUEUE_STATES"]

_LOG = logging.getLogger(__name__)

#: The nine states of ``comparison_work`` in the order the contract's ``ComparisonQueueCounts`` lists them.
QUEUE_STATES: Final[tuple[str, ...]] = (
    "queued", "leased", "running", "retry_wait", "paused", "spend_unknown", "succeeded", "failed", "cancelled",
)
_PAGE_PROFILE_PREFIX: Final[str] = KIND_PAGE_PROFILE + ":"
_MATRIX_BUILD_PREFIX: Final[str] = KIND_MATRIX_BUILD + ":"
#: A transition "with changes" has a sheet that differs, needs a look, or was added or removed (``overview.py:176``).
_CHANGE_COUNTS: Final[tuple[str, ...]] = ("different", "needs_review", "added", "removed")


def _read_only(session: Session) -> None:
    """Make the whole call one snapshot that cannot write. Must be the first statement of the transaction."""
    session.connection(execution_options={"isolation_level": "REPEATABLE READ", "postgresql_readonly": True})


def _page_profile_version(dedupe_key: str | None) -> str | None:
    """``page_profile:<version>`` and ``page_profile:<version>:retry_failed`` name the version (``profile_queue/enqueue.py``)."""
    if dedupe_key is None or not dedupe_key.startswith(_PAGE_PROFILE_PREFIX):
        return None
    return dedupe_key[len(_PAGE_PROFILE_PREFIX):].split(":", 1)[0]


class ComparisonOverviewService:
    __slots__ = ("_factory", "_repo", "_documents", "_clock", "_paused")

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        paused: Callable[[Session], bool] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._factory = session_factory
        self._repo = OverviewRepository()
        self._documents = DocumentRepository()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._paused = paused

    # -- the overview -----------------------------------------------------------------------------------------

    def get_overview(self, *, project_uid: str) -> dict[str, Any]:
        with session_scope(self._factory) as session:
            _read_only(session)
            self._documents.get_project(session, ProjectUid.parse(project_uid))  # an absent project is 404
            sets = self._sets(session, project_uid)
            pending = self._repo.pending_uploads(session, project_uid)
        groups = [group for _view, group in sets]
        return {
            "project_uid": project_uid,
            "generated_at": self._clock(),
            "totals": rules.totals([int(view["version_count"]) for view, _group in sets]),
            "counters": rules.counters(groups),
            "sets": [view for view, _group in sets],
            "pending_uploads": [
                {
                    "upload_id": u.upload_id, "state": u.state, "declared_files": u.declared_files,
                    "sets_total": u.sets_total, "sets_done": u.sets_done,
                }
                for u in pending
            ],
        }

    def _sets(self, session: Session, project_uid: str) -> list[tuple[dict[str, Any], str]]:
        repo = self._repo
        documents = repo.documents(session, project_uid)
        if len(documents) > MAX_SETS:
            # the contract caps the list at 1000 and has no cursor or flag; the counters and totals follow the rows shown
            _LOG.warning("project %s has more than %d document sets; the overview shows the first %d", project_uid, MAX_SETS, MAX_SETS)
            documents = documents[:MAX_SETS]
        doc_ids = [d.document_uid for d in documents]
        by_doc_versions: dict[str, list[VersionRow]] = {d: [] for d in doc_ids}
        for v in repo.versions(session, project_uid):
            if v.document_uid in by_doc_versions:
                by_doc_versions[v.document_uid].append(v)
        version_ids = [v.version_uid for vs in by_doc_versions.values() for v in vs]
        facts_by_version: dict[str, list[ProfileFact]] = {}
        for fact in repo.profile_facts(session, version_ids, PAGE_PROFILE_ALGO_VERSION):
            facts_by_version.setdefault(fact.version_uid, []).append(fact)
        metadata = repo.set_metadata(session, project_uid)
        orders = repo.latest_orders(session, doc_ids)
        builds = repo.latest_builds(session, doc_ids)
        built = list(builds)
        edits = repo.edits(session, built)
        links = repo.ai_links(session, built)
        work = repo.work(session, project_uid)
        latest_series = repo.latest_series(session, doc_ids)
        transitions = repo.transitions(session, [s.series_id for s in latest_series.values()])
        bound = repo.bound_signatures(session, sorted({s.matrix_id for s in latest_series.values()}))

        version_doc = {v.version_uid: v.document_uid for vs in by_doc_versions.values() for v in vs}
        profile_work: dict[str, list[str]] = {}
        build_work: dict[str, list[WorkRow]] = {}
        follow_up: dict[str, list[str]] = {}
        for item in work:
            if item.kind == KIND_PAGE_PROFILE:
                version = _page_profile_version(item.dedupe_key)
                if version in version_doc:
                    profile_work.setdefault(version_doc[version], []).append(item.state)
            elif item.kind == KIND_MATRIX_BUILD and item.dedupe_key is not None and item.dedupe_key.startswith(_MATRIX_BUILD_PREFIX):
                build_work.setdefault(item.dedupe_key[len(_MATRIX_BUILD_PREFIX):], []).append(item)
            elif item.kind == KIND_FOLLOW_UP and item.document_uid is not None:
                follow_up.setdefault(item.document_uid, []).append(item.state)

        out: list[tuple[dict[str, Any], str]] = []
        for doc in documents:
            vs = by_doc_versions[doc.document_uid]
            out.append(self._one_set(
                doc, vs, metadata.get(doc.document_uid), orders.get(doc.document_uid), facts_by_version,
                builds.get(doc.document_uid), edits.get(doc.document_uid, []), links.get(doc.document_uid, []),
                profile_work.get(doc.document_uid, []), build_work.get(doc.document_uid, []),
                follow_up.get(doc.document_uid, []), latest_series.get(doc.document_uid),
                transitions, bound,
            ))
        out.sort(key=lambda pair: (
            pair[0].get("designation") is None, str(pair[0].get("designation", "")).casefold(),
            str(pair[0]["title"]).casefold(), pair[0]["document_uid"],
        ))
        return out

    def _one_set(
        self, doc: DocumentRow, versions: Sequence[VersionRow], meta: SetMetaRow | None, order_row: OrderRow | None,
        facts_by_version: Mapping[str, Sequence[ProfileFact]], build: BuildRecord | None,
        edits: Sequence[EditRecord], links: Sequence[AiLinkRecord], profile_states: Sequence[str],
        build_items: Sequence[WorkRow], follow_up_states: Sequence[str], series: SeriesRow | None,
        transitions: Mapping[str, Sequence[TransitionRow]], bound: Mapping[str, str],
    ) -> tuple[dict[str, Any], str]:
        ordered = sorted(versions, key=lambda v: v.ordinal)
        count = len(ordered)
        own = [v.version_uid for v in ordered]
        order = resolve_order(None if order_row is None else order_row.version_uids, own)
        page_counts = {v.version_uid: v.page_count for v in ordered}
        facts = [f for version in order for f in facts_by_version.get(version, ())]

        progress = profile_progress(facts, page_counts)
        profile = rules.profile_step(
            version_count=count, pages_total=progress["total"], ready=progress["ready"], failed=progress["failed"],
            live=rules.live_state(profile_states),
        )

        order_id = None if order_row is None else order_row.order_id
        reasons = [] if build is None else matrix_stale_reasons(build, order=order, order_id=order_id, digest=profile_digest(facts))
        live_builds = [w.state for w in build_items if w.state in rules.LIVE_WORK_STATES]
        newest = max(build_items, key=lambda w: (w.created_at, w.work_id), default=None)
        state = rules.matrix_state(
            has_build=build is not None, stale_reasons=reasons,
            live=bool(live_builds) or rules.live_state(profile_states) is not None,
            last_build_failed=newest is not None and newest.state == "failed"
            and (build is None or newest.created_at > build.created_at),
        )
        rows = unmatched = manual = 0
        if build is not None:
            built_counts = {k: int(v) for k, v in (build.summary.get("page_counts") or {}).items()}
            counts = effective_matrix(build, edits, links, page_counts=built_counts).counts
            rows, unmatched, manual = counts["rows"], counts["unmatched"], counts["manual"]
        matrix = rules.matrix_step(
            version_count=count, state=state, build_live=rules.live_state(live_builds), has_build=build is not None,
            rows=rows, unmatched=unmatched, manual=manual,
        )

        facts_of_series = None
        if series is not None:
            facts_of_series = self._series_facts(
                series, transitions.get(series.series_id, ()), order=order, order_id=order_id, facts_by_version=facts_by_version,
                build=build, edits=edits, bound=bound,
            )
        series_step = rules.series_step(
            version_count=count, latest=facts_of_series,
            follow_up_live=rules.live_state(follow_up_states) is not None,
        )

        steps: dict[str, Step] = {
            m.STEP_UPLOAD: rules.upload_step(version_count=count),
            m.STEP_PROFILE: profile,
            m.STEP_MATRIX: matrix,
            m.STEP_AI_PAIRS: rules.deferred_step(),
            m.STEP_SERIES: series_step,
            m.STEP_AI_CHANGES: rules.deferred_step(),
            m.STEP_REPORT: rules.deferred_step(),
        }
        proposed = rules.next_step(steps, count)
        view: dict[str, Any] = {
            "document_uid": doc.document_uid,
            "version_count": count,
            "steps": [_step_dict(name, steps[name]) for name in STEP_ORDER],
            "title": doc.title,
            "updated_at": max((v.published_at for v in ordered), default=doc.updated_at),
        }
        if meta is not None:
            for key in ("designation", "project_stage", "section_code"):
                value = getattr(meta, key)
                if value is not None:
                    view[key] = value
        if proposed is not None:
            view["next_step"] = proposed
        return view, rules.group_of(proposed, steps)

    @staticmethod
    def _series_facts(
        series: SeriesRow, transitions: Sequence[TransitionRow], *, order: Sequence[str], order_id: str | None,
        facts_by_version: Mapping[str, Sequence[ProfileFact]], build: BuildRecord | None, edits: Sequence[EditRecord],
        bound: Mapping[str, str],
    ) -> rules.SeriesFacts:
        """What ``ComparisonSeriesService._view_of`` and ``._stale`` derive for the series, from rows already read."""
        chain = chain_of([(t.source_version_uid, t.target_version_uid) for t in transitions])
        current = CurrentInputs(
            order=tuple(order), matrix_id=None if build is None else build.matrix_id,
            edit_no=max((e.edit_no for e in edits), default=0),
            profile_signature=profile_digest([f for v in chain for f in facts_by_version.get(v, ())]),
            engine_algo=ENGINE_ALGO_VERSION,
        )
        bound_inputs = SeriesInputs(
            chain=chain, matrix_id=series.matrix_id, edit_no=series.edit_no,
            profile_signature=bound.get(series.matrix_id, ""), engine_algo=ENGINE_ALGO_VERSION,
        )
        completed = [t for t in transitions if t.state == "completed"]
        with_changes = sum(
            1 for t in completed if t.summary and any(int(t.summary.get(key, 0) or 0) > 0 for key in _CHANGE_COUNTS)
        )
        return rules.SeriesFacts(
            state=series.state, transitions_total=len(transitions), transitions_done=len(completed),
            with_changes=with_changes, stale=bool(series_stale_reasons(series.input_sha256, bound_inputs, current)),
        )

    # -- the queue --------------------------------------------------------------------------------------------

    def get_queue_summary(self, *, modules: str) -> dict[str, Any]:
        """The whole installation's comparison queue. ``modules`` is the module set the deployment serves."""
        with session_scope(self._factory) as session:
            _read_only(session)
            rows = self._repo.queue_counts(session)
            oldest = self._repo.oldest_queued_at(session)
            paused = self._is_paused(session)
        total = dict.fromkeys(QUEUE_STATES, 0)
        by_kind: dict[tuple[str, str], dict[str, int]] = {}
        for row in rows:
            if row.state not in total:
                raise ValueError(f"unknown comparison work state {row.state!r}")
            total[row.state] += row.count
            by_kind.setdefault((row.module, row.kind), dict.fromkeys(QUEUE_STATES, 0))[row.state] += row.count
        out: dict[str, Any] = {
            "modules": modules,
            "paused": paused,
            "counts": total,
            "kinds": [
                {"kind": kind, "module": module, "counts": counts}
                for (module, kind), counts in sorted(by_kind.items())
            ],
        }
        if oldest is not None:
            out["oldest_queued_at"] = oldest
        return out

    def _is_paused(self, session: Session) -> bool:
        if self._paused is None:
            from auditmanager.comparison.work.gates import default_gates

            self._paused = default_gates().paused
        return bool(self._paused(session))


def _step_dict(name: str, step: Step) -> dict[str, Any]:
    out: dict[str, Any] = {"step": name, "state": step.state}
    if step.counts is not None:
        out["counts"] = dict(step.counts)
    return out
