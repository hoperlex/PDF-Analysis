"""The use cases of the matrix: read it, prepare it, edit it, undo an edit, build it.

`CMP-MATRIX-01` (ADR-0025 decisions 3, 5, 7, 13, 14, 16). One class holds the operations the contract seals for the
matrix and the build the worker runs. It takes plain values and answers plain values (contract-shaped dictionaries, small
dataclasses); the adapter in the composition root maps them to the generated models.

**Reads** start nothing and change nothing (``getComparisonMatrix``, ``listComparisonMatrixEdits``,
``listComparisonAiLinks``): the state of a document set is derived from its stored rows -- the latest build, the edit
history, the accepted AI links, the stored page profiles and, read-only, whether a profile or a build is still
queued or the last build failed.

**Writes** are an expert's act, checked again in the transaction that acts (decision 16), keyed (a repeat of the same
key and payload replays the recorded outcome, a repeat with another payload is ``idempotency_key_reuse``), and
append-only. An edit batch and an undo name the revision they started from, the pair *(build, number of edit events)*;
either part having moved is ``409 conflict`` / ``comparison_matrix_stale``, nothing is written and the client rebases
(decision 14). The advisory lock the edit-chain trigger takes is taken first, so the revision check and the inserts are
one decision.

**The build** reads the stored page profiles one page at a time (the archive of a page is a few megabytes; a document
set of a thousand pages is never in memory as profiles, only as the compact features the score uses), makes the rows
with :func:`~auditmanager.comparison.matrix.lineage.build_rows` and appends them once per input set. It runs in the
worker (kind ``matrix_build``); the lease fence of decision 7 is the ``publish_guard`` it calls in the publishing
transaction.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.matrix import settings
from auditmanager.comparison.matrix.effective import (
    EDIT_APPLIED,
    EffectiveMatrix,
    effective_matrix,
    latest_applied_edit,
    page_index,
)
from auditmanager.comparison.matrix.features import MaskCache, PageFeatures
from auditmanager.comparison.matrix.inputs import (
    profile_digest,
    profile_progress,
    profiles_complete,
    resolve_order,
    stale_reasons,
    versions_missing_profiles,
)
from auditmanager.comparison.matrix.lineage import build_rows
from auditmanager.comparison.matrix.model import (
    AiLinkRecord,
    BuildRecord,
    EditRecord,
    PageRef,
)
from auditmanager.comparison.matrix.pairs import AdjacentSheetPairs, adjacent_pairs
from auditmanager.comparison.matrix.repository import MatrixRepository, ProfileFact
from auditmanager.comparison.modules import MODULE_VERSIONS
from auditmanager.comparison.profile.limits import ALGO_VERSION as PAGE_PROFILE_ALGO_VERSION
from auditmanager.comparison.profile.reader import PageProfileReader
from auditmanager.comparison.profile_queue.enqueue import enqueue_version_page_profiles, page_profile_dedupe_key
from auditmanager.comparison.profile_queue.handler import PAGE_PROFILE_KIND
from auditmanager.comparison.work.repository import ComparisonWorkRepository
from auditmanager.documents.public import DocumentRepository
from auditmanager.ingest.public import CommandReplay, CommandRepository, payload_fingerprint
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, IdempotencyKey, ProjectUid

__all__ = [
    "BuildResult",
    "COMMAND_APPLY_EDITS",
    "COMMAND_PREPARE",
    "COMMAND_UNDO_EDIT",
    "ComparisonMatrixService",
    "EditInput",
    "EditPage",
    "MATRIX_BUILD_KIND",
    "AiLinkPage",
    "matrix_build_dedupe_key",
    "read_adjacent_sheet_pairs",
]

_LOG = logging.getLogger(__name__)

#: The command types are the snake case of the operationId (``scripts/recovery/product_purge.py`` registers them).
COMMAND_PREPARE: Final[str] = "prepare_comparison_matrix"
COMMAND_APPLY_EDITS: Final[str] = "apply_comparison_matrix_edits"
COMMAND_UNDO_EDIT: Final[str] = "undo_comparison_matrix_edit"
#: The work kind of the build (``comparison_work.kind``).
MATRIX_BUILD_KIND: Final[str] = "matrix_build"
PAGE_MAX: Final[int] = 200
_PROFILE_CHUNK: Final[int] = 100

STATE_ABSENT: Final[str] = "absent"
STATE_BUILDING: Final[str] = "building"
STATE_READY: Final[str] = "ready"
STATE_STALE: Final[str] = "stale"
STATE_FAILED: Final[str] = "failed"


def require_expert(roles: frozenset[str] | set[str]) -> None:
    """A matrix act is an expert's (ADR-0025 decision 16, ``R-60``): an administrator alone is refused. The edge
    refuses it too (``OPERATION_ROLES``); this is the command's own check, in the transaction that would act."""
    if "expert" not in roles:
        raise DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:expert")


def matrix_build_dedupe_key(document_uid: str) -> str:
    """One live build item per document set."""
    return f"{MATRIX_BUILD_KIND}:{document_uid}"


@dataclass(frozen=True, slots=True)
class EditInput:
    """One edit of a batch, as the adapter hands it over."""

    kind: str
    page: PageRef
    other_page: PageRef | None = None
    absent_version_uid: str | None = None


@dataclass(frozen=True, slots=True)
class EditPage:
    items: list[dict[str, Any]]
    next_before_edit_no: int | None


@dataclass(frozen=True, slots=True)
class AiLinkPage:
    items: list[dict[str, Any]]
    next_after: tuple[str, str] | None


@dataclass(frozen=True, slots=True)
class BuildResult:
    """How a build ended: ``built`` a new one, ``existing`` (this input set was already built) or ``incomplete``
    (some page has no stored profile; ``missing`` names the versions)."""

    outcome: str
    build: BuildRecord | None = None
    missing: tuple[str, ...] = ()


@dataclass(slots=True)
class _Inputs:
    project_uid: str
    document_uid: str
    order: list[str]
    order_id: str | None
    page_counts: dict[str, int]
    facts: list[ProfileFact]

    @property
    def digest(self) -> str:
        return profile_digest(self.facts)


def _invalid() -> DomainError:
    return DomainError(ErrorCode.VALIDATION_FAILED, field="edits", constraint="comparison_edit_invalid")


class ComparisonMatrixService:
    __slots__ = ("_factory", "_blob_store", "_reader", "_documents", "_commands", "_repo", "_work")

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        blob_store: Any = None,
        profile_reader: PageProfileReader | None = None,
    ) -> None:
        self._factory = session_factory
        self._blob_store = blob_store
        self._reader = profile_reader
        self._documents = DocumentRepository()
        self._commands = CommandRepository()
        self._repo = MatrixRepository()
        self._work = ComparisonWorkRepository()

    # -- shared reads -----------------------------------------------------------------------------------------

    def _require_document(self, session: Session, project_uid: str, document_uid: str) -> None:
        """The project exists and owns the document; either missing is ``not_found`` naming what was addressed."""
        self._documents.get_project(session, ProjectUid.parse(project_uid))
        if str(self._documents.require_document(session, DocumentUid.parse(document_uid))) != project_uid:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Document")

    def _inputs(self, session: Session, project_uid: str, document_uid: str) -> _Inputs:
        versions = sorted(
            self._documents.list_versions(session, DocumentUid.parse(document_uid)), key=lambda v: v.version_ordinal
        )
        own_order = [str(v.version_uid) for v in versions]
        latest = self._repo.latest_order(session, document_uid)
        order = resolve_order(None if latest is None else latest.version_uids, own_order)
        counts = {str(v.version_uid): int(v.page_count) for v in versions}
        facts = self._repo.profile_facts(session, order, PAGE_PROFILE_ALGO_VERSION)
        return _Inputs(
            project_uid=project_uid, document_uid=document_uid, order=order,
            order_id=None if latest is None else latest.order_id, page_counts=counts, facts=facts,
        )

    def _state(
        self, session: Session, inputs: _Inputs, build: BuildRecord | None
    ) -> tuple[str, list[str], str | None]:
        """``(state, stale reasons, failure reason)`` of the document set."""
        dedupe = matrix_build_dedupe_key(inputs.document_uid)
        live_build = self._repo.live_work(
            session, project_uid=inputs.project_uid, kind=MATRIX_BUILD_KIND, dedupe_keys=[dedupe]
        )
        live_profiles = self._repo.live_work(
            session, project_uid=inputs.project_uid, kind=PAGE_PROFILE_KIND,
            dedupe_keys=[
                key for v in inputs.order
                for key in (page_profile_dedupe_key(v), page_profile_dedupe_key(v, retry_failed=True))
            ],
        )
        live = bool(live_build or live_profiles)
        last = self._repo.latest_work(
            session, project_uid=inputs.project_uid, kind=MATRIX_BUILD_KIND, dedupe_key=dedupe
        )
        failed = (
            last is not None
            and last.state == "failed"
            and (build is None or last.created_at > build.created_at)
        )
        reasons: list[str] = []
        if build is not None:
            reasons = stale_reasons(build, order=inputs.order, order_id=inputs.order_id, digest=inputs.digest)
            if not reasons:
                return STATE_READY, [], None
        if live:
            return STATE_BUILDING, reasons, None
        if failed:
            assert last is not None
            return STATE_FAILED, reasons, last.failure_reason
        return (STATE_STALE if build is not None else STATE_ABSENT), reasons, None

    # -- the effective matrix --------------------------------------------------------------------------------

    def _snapshot(
        self, session: Session, project_uid: str, document_uid: str
    ) -> tuple[_Inputs, BuildRecord | None, list[EditRecord], list[AiLinkRecord], EffectiveMatrix | None]:
        inputs = self._inputs(session, project_uid, document_uid)
        build = self._repo.latest_build(session, document_uid)
        edits = self._repo.all_edits(session, document_uid)
        links = self._repo.ai_links(session, document_uid)
        eff = None
        if build is not None:
            counts = {k: int(v) for k, v in (build.summary.get("page_counts") or {}).items()}
            eff = effective_matrix(build, edits, links, page_counts=counts)
        return inputs, build, edits, links, eff

    def get_matrix(self, *, project_uid: str, document_uid: str) -> dict[str, Any]:
        with session_scope(self._factory) as session:
            self._require_document(session, project_uid, document_uid)
            return self._wire_matrix(session, project_uid, document_uid)

    def _wire_matrix(self, session: Session, project_uid: str, document_uid: str) -> dict[str, Any]:
        inputs, build, edits, _links, eff = self._snapshot(session, project_uid, document_uid)
        state, reasons, failure = self._state(session, inputs, build)
        out: dict[str, Any] = {
            "project_uid": project_uid,
            "document_uid": document_uid,
            "state": state,
            "progress": profile_progress(inputs.facts, inputs.page_counts),
        }
        if build is not None and eff is not None:
            out["revision"] = {"matrix_id": build.matrix_id, "edit_no": max((e.edit_no for e in edits), default=0)}
            if build.order_id is not None:
                out["order_id"] = build.order_id
            if reasons:
                out["stale_reasons"] = reasons
            out["columns"] = eff.columns
            out["rows"] = eff.rows
            out["unassigned_pages"] = eff.unassigned_pages
            out["counts"] = eff.counts
            out["orphaned_edit_ids"] = eff.orphaned_edit_ids
            out["built_at"] = build.created_at
        if failure:
            out["failure_reason"] = failure[:128]
        return out

    # -- lists ------------------------------------------------------------------------------------------------

    def list_edits(
        self, *, project_uid: str, document_uid: str, before_edit_no: int | None, limit: int
    ) -> EditPage:
        bounded = max(1, min(limit, PAGE_MAX))
        with session_scope(self._factory) as session:
            self._require_document(session, project_uid, document_uid)
            _inputs, build, edits, links, eff = self._snapshot(session, project_uid, document_uid)
            index = {} if build is None else page_index(build)
            status = {} if eff is None else eff.edit_status
            undone = {e.undoes_edit_id for e in edits if e.kind == "undo"}
            rows = self._repo.edits_page(session, document_uid, before=before_edit_no, limit=bounded + 1)
        page = rows[:bounded]
        items = [
            self._wire_edit(e, document_uid, index, status.get(e.edit_id) or ("undone" if e.edit_id in undone else EDIT_APPLIED))
            for e in page
        ]
        return EditPage(items=items, next_before_edit_no=page[-1].edit_no if len(rows) > bounded and page else None)

    @staticmethod
    def _wire_ref(ref: PageRef | None, index: Mapping[tuple[str, int], str]) -> dict[str, Any] | None:
        if ref is None:
            return None
        out: dict[str, Any] = {"version_uid": ref.version_uid, "page_number": ref.page_number}
        profile = ref.page_profile_id or index.get(ref.key)
        if profile:
            out["page_profile_id"] = profile
        return out

    def _wire_edit(
        self, edit: EditRecord, document_uid: str, index: Mapping[tuple[str, int], str], status: str
    ) -> dict[str, Any]:
        out: dict[str, Any] = {
            "edit_id": edit.edit_id,
            "document_uid": document_uid,
            "edit_no": edit.edit_no,
            "kind": edit.kind,
            "source": edit.source,
            "status": status,
            "created_at": edit.decided_at,
            "created_by": edit.actor_user_uid,
        }
        page = self._wire_ref(edit.page, index)
        other = self._wire_ref(edit.other_page, index)
        if page is not None:
            out["page"] = page
        if other is not None:
            out["other_page"] = other
        if edit.absent_version_uid is not None:
            out["absent_version_uid"] = edit.absent_version_uid
        if edit.undoes_edit_id is not None:
            out["undoes_edit_id"] = edit.undoes_edit_id
        if edit.order_id is not None:
            out["order_id"] = edit.order_id
        if edit.source == "migrated_sheet_link" and edit.provenance:
            out["provenance"] = {
                "comparison_id": edit.provenance["comparison_id"],
                "sheet_link_id": edit.provenance["sheet_link_id"],
                "link_revision": int(edit.provenance["link_revision"]),
            }
        return out

    def list_ai_links(
        self, *, project_uid: str, document_uid: str, after: tuple[str, str] | None, limit: int
    ) -> AiLinkPage:
        bounded = max(1, min(limit, PAGE_MAX))
        with session_scope(self._factory) as session:
            self._require_document(session, project_uid, document_uid)
            _inputs, build, _edits, links, eff = self._snapshot(session, project_uid, document_uid)
            index = {} if build is None else page_index(build)
            status = {} if eff is None else eff.ai_status
        ordered = sorted(links, key=lambda x: (x.created_at, x.ai_link_id), reverse=True)
        if after is not None:
            ordered = [x for x in ordered if (x.created_at.isoformat(), x.ai_link_id) < after]
        page = ordered[:bounded]
        items = [
            {
                "ai_link_id": link.ai_link_id,
                "document_uid": document_uid,
                "matrix_id": link.matrix_id,
                "page": self._wire_ref(link.page, index),
                "other_page": self._wire_ref(link.other_page, index),
                "answered_state": link.answered_state,
                "status": status.get(link.ai_link_id, "superseded"),
                "created_at": link.created_at,
            }
            for link in page
        ]
        more = len(ordered) > bounded and bool(page)
        return AiLinkPage(items=items, next_after=(page[-1].created_at.isoformat(), page[-1].ai_link_id) if more else None)

    # -- preparation -------------------------------------------------------------------------------------------

    def prepare_matrix(
        self, *, project_uid: str, document_uid: str, user_uid: str, actor_roles: frozenset[str], idempotency_key: str
    ) -> dict[str, Any]:
        """Queue the profiles that are missing or failed, then the build (``prepareComparisonMatrix``)."""
        require_expert(actor_roles)
        key = IdempotencyKey(idempotency_key)
        fingerprint = payload_fingerprint(
            {"command": "prepare_comparison_matrix.v1", "project_uid": project_uid, "document_uid": document_uid}
        )
        with session_scope(self._factory) as session:
            self._require_document(session, project_uid, document_uid)
            claim = self._commands.begin(
                session, command_type=COMMAND_PREPARE, idempotency_key=key, fingerprint=fingerprint
            )
            if isinstance(claim, CommandReplay):
                return self._preparation(session, project_uid, document_uid)
            inputs = self._inputs(session, project_uid, document_uid)
            build = self._repo.latest_build(session, document_uid)
            missing, failed = versions_missing_profiles(inputs.facts, inputs.order, inputs.page_counts)
            queued_profiles = False
            for version in inputs.order:
                if version in missing or version in failed:
                    # ``retry_failed`` also builds the pages that have no row yet: the builder skips only stored ones.
                    enqueue_version_page_profiles(
                        session, project_uid=project_uid, version_uid=version,
                        created_by_user_uid=user_uid, retry_failed=version in failed,
                    )
                    queued_profiles = True
            current = (
                build is not None
                and not stale_reasons(build, order=inputs.order, order_id=inputs.order_id, digest=inputs.digest)
            )
            if queued_profiles or not current:
                self._work.enqueue(
                    session, project_uid=project_uid, module=MODULE_VERSIONS, kind=MATRIX_BUILD_KIND,
                    payload={"document_uid": document_uid}, dedupe_key=matrix_build_dedupe_key(document_uid),
                    created_by_user_uid=user_uid,
                )
            self._commands.succeed(session, claim.command_id, {"document_uid": document_uid})
            return self._preparation(session, project_uid, document_uid)

    def _preparation(self, session: Session, project_uid: str, document_uid: str) -> dict[str, Any]:
        inputs = self._inputs(session, project_uid, document_uid)
        build = self._repo.latest_build(session, document_uid)
        state, _reasons, _failure = self._state(session, inputs, build)
        return {
            "document_uid": document_uid,
            "state": state,
            "progress": profile_progress(inputs.facts, inputs.page_counts),
        }

    # -- edits -------------------------------------------------------------------------------------------------

    def _check_base(
        self, session: Session, document_uid: str, base_matrix_id: str, base_edit_no: int
    ) -> tuple[BuildRecord, int]:
        build = self._repo.latest_build(session, document_uid)
        newest = self._repo.max_edit_no(session, document_uid)
        if build is None or build.matrix_id != base_matrix_id or newest != base_edit_no:
            raise DomainError(ErrorCode.CONFLICT, conflict_reason="comparison_matrix_stale")
        return build, newest

    def apply_edits(
        self,
        *,
        project_uid: str,
        document_uid: str,
        base_matrix_id: str,
        base_edit_no: int,
        edits: Sequence[EditInput],
        user_uid: str,
        actor_label: str,
        actor_roles: frozenset[str],
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Apply a drafted batch together or not at all (``applyComparisonMatrixEdits``)."""
        require_expert(actor_roles)
        if len(edits) > settings.MAX_EDITS_PER_BATCH:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="edits", constraint="comparison_edits_limit")
        key = IdempotencyKey(idempotency_key)
        fingerprint = payload_fingerprint(
            {
                "command": "apply_comparison_matrix_edits.v1",
                "project_uid": project_uid,
                "document_uid": document_uid,
                "base_revision": {"matrix_id": base_matrix_id, "edit_no": base_edit_no},
                "edits": [
                    {
                        "kind": e.kind,
                        "page": [e.page.version_uid, e.page.page_number],
                        "other_page": None if e.other_page is None else [e.other_page.version_uid, e.other_page.page_number],
                        "absent_version_uid": e.absent_version_uid,
                    }
                    for e in edits
                ],
            }
        )
        label = " ".join(actor_label.split())[:128] or "эксперт"
        with session_scope(self._factory) as session:
            self._require_document(session, project_uid, document_uid)
            claim = self._commands.begin(
                session, command_type=COMMAND_APPLY_EDITS, idempotency_key=key, fingerprint=fingerprint
            )
            if isinstance(claim, CommandReplay):
                return self._wire_matrix(session, project_uid, document_uid)
            self._repo.lock_edits(session, document_uid)
            build, newest = self._check_base(session, document_uid, base_matrix_id, base_edit_no)
            inputs = self._inputs(session, project_uid, document_uid)
            self._validate(edits, inputs.page_counts, page_index(build))
            for position, edit in enumerate(edits, start=1):
                self._repo.insert_edit(
                    session, project_uid=project_uid, document_uid=document_uid, edit_no=newest + position,
                    batch_position=position, kind=edit.kind, page=PageRef(edit.page.version_uid, edit.page.page_number),
                    other_page=None if edit.other_page is None else PageRef(edit.other_page.version_uid, edit.other_page.page_number),
                    absent_version_uid=edit.absent_version_uid, undoes_edit_id=None, order_id=inputs.order_id,
                    actor_user_uid=user_uid, actor_label=label, command_id=str(claim.command_id),
                )
            self._commands.succeed(session, claim.command_id, {"edits": len(edits), "first_edit_no": newest + 1})
            return self._wire_matrix(session, project_uid, document_uid)

    @staticmethod
    def _validate(edits: Sequence[EditInput], page_counts: Mapping[str, int], index: Mapping[tuple[str, int], str]) -> None:
        """``comparison_edit_invalid``: a page outside its version or of a version that is not the document's, a link
        that joins a version to itself, or a member the kind does not take; a profile identity that the build
        contradicts."""

        def page_ok(ref: PageRef) -> bool:
            count = page_counts.get(ref.version_uid)
            if count is None or not 1 <= ref.page_number <= count:
                return False
            known = index.get(ref.key)
            return ref.page_profile_id is None or known is None or known == ref.page_profile_id

        for edit in edits:
            if edit.kind not in ("link", "unlink", "mark_absent") or not page_ok(edit.page):
                raise _invalid()
            if edit.kind == "link":
                if (
                    edit.other_page is None
                    or edit.absent_version_uid is not None
                    or not page_ok(edit.other_page)
                    or edit.other_page.version_uid == edit.page.version_uid
                ):
                    raise _invalid()
            elif edit.kind == "unlink":
                if edit.other_page is not None or edit.absent_version_uid is not None:
                    raise _invalid()
            else:
                if (
                    edit.other_page is not None
                    or edit.absent_version_uid is None
                    or edit.absent_version_uid not in page_counts
                    or edit.absent_version_uid == edit.page.version_uid
                ):
                    raise _invalid()

    def undo_edit(
        self,
        *,
        project_uid: str,
        document_uid: str,
        base_matrix_id: str,
        base_edit_no: int,
        user_uid: str,
        actor_label: str,
        actor_roles: frozenset[str],
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Reverse the latest applied edit (``undoComparisonMatrixEdit``); the history keeps both."""
        require_expert(actor_roles)
        key = IdempotencyKey(idempotency_key)
        fingerprint = payload_fingerprint(
            {
                "command": "undo_comparison_matrix_edit.v1",
                "project_uid": project_uid,
                "document_uid": document_uid,
                "base_revision": {"matrix_id": base_matrix_id, "edit_no": base_edit_no},
            }
        )
        label = " ".join(actor_label.split())[:128] or "эксперт"
        with session_scope(self._factory) as session:
            self._require_document(session, project_uid, document_uid)
            claim = self._commands.begin(
                session, command_type=COMMAND_UNDO_EDIT, idempotency_key=key, fingerprint=fingerprint
            )
            if isinstance(claim, CommandReplay):
                return self._wire_matrix(session, project_uid, document_uid)
            self._repo.lock_edits(session, document_uid)
            _build, newest = self._check_base(session, document_uid, base_matrix_id, base_edit_no)
            target = latest_applied_edit(self._repo.all_edits(session, document_uid))
            if target is None:
                raise DomainError(ErrorCode.CONFLICT, conflict_reason="comparison_edit_none")
            latest_order = self._repo.latest_order(session, document_uid)
            self._repo.insert_edit(
                session, project_uid=project_uid, document_uid=document_uid, edit_no=newest + 1, batch_position=1,
                kind="undo", page=None, other_page=None, absent_version_uid=None, undoes_edit_id=target.edit_id,
                order_id=None if latest_order is None else latest_order.order_id,
                actor_user_uid=user_uid, actor_label=label, command_id=str(claim.command_id),
            )
            self._commands.succeed(session, claim.command_id, {"undoes_edit_id": target.edit_id, "edit_no": newest + 1})
            return self._wire_matrix(session, project_uid, document_uid)

    # -- for the series ----------------------------------------------------------------------------------------

    def adjacent_sheet_pairs(self, *, project_uid: str, document_uid: str) -> AdjacentSheetPairs:
        """The sheet pairs of every adjacent transition, from the effective matrix of the latest build.

        ``CMP-SERIES-01`` reads this. A document set with no build is ``not_found`` (``MatrixNotBuilt`` is the
        series' to refuse earlier: it should read :meth:`get_matrix` ``state`` first); a stale build answers with the
        order it walked, and ``order``/``order_id`` say which.
        """
        with session_scope(self._factory) as session:
            self._require_document(session, project_uid, document_uid)
            _inputs, build, edits, _links, eff = self._snapshot(session, project_uid, document_uid)
        if build is None or eff is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="ComparisonMatrix")
        return adjacent_pairs(build, eff, edit_no=max((e.edit_no for e in edits), default=0), order=build.order)

    # -- the build (the worker's) --------------------------------------------------------------------------------

    def profiles_pending(self, *, project_uid: str, document_uid: str, versions: Sequence[str]) -> bool:
        """Is a ``page_profile`` item of one of ``versions`` still going to run? (The build waits for it.)"""
        keys = [
            key for v in versions for key in (page_profile_dedupe_key(v), page_profile_dedupe_key(v, retry_failed=True))
        ]
        with session_scope(self._factory) as session:
            return bool(
                self._repo.live_work(session, project_uid=project_uid, kind=PAGE_PROFILE_KIND, dedupe_keys=keys)
            )

    def _profile_reader(self) -> PageProfileReader:
        if self._reader is None:
            self._reader = PageProfileReader(self._factory, self._blob_store)
        return self._reader

    def build_matrix(
        self,
        *,
        project_uid: str,
        document_uid: str,
        checkpoint: Callable[[], None] | None = None,
        publish_guard: Callable[[Session], None] | None = None,
    ) -> BuildResult:
        """Build the algorithmic matrix of the document set from its stored page profiles, once per input set.

        ``checkpoint`` is called before the first version and after each (the worker proves its lease, extends it
        and stops on a cancel there); ``publish_guard`` is called in the publishing transaction before the insert
        (``WorkItem.require_current``: a worker that lost its lease writes nothing).
        """
        with session_scope(self._factory) as session:
            self._require_document(session, project_uid, document_uid)
            inputs = self._inputs(session, project_uid, document_uid)
        if not profiles_complete(inputs.facts, inputs.page_counts):
            missing, _failed = versions_missing_profiles(inputs.facts, inputs.order, inputs.page_counts)
            return BuildResult("incomplete", missing=tuple(missing))
        with session_scope(self._factory) as session:
            existing = self._repo.build_for_inputs(
                session, document_uid=document_uid, order_id=inputs.order_id, signature=inputs.digest,
                rules=settings.RULES_VERSION, algo=settings.ALGO_VERSION,
            )
        if existing is not None:
            return BuildResult("existing", build=existing)

        if checkpoint is not None:
            checkpoint()
        cache = MaskCache()
        reader = self._profile_reader()
        read_facts: list[ProfileFact] = []
        features: dict[str, list[PageFeatures]] = {}
        for version in inputs.order:
            pages: list[PageFeatures] = []
            after = 0
            while True:
                rows, more = reader.list_profiles(version, after_page=after, limit=_PROFILE_CHUNK)
                for row in rows:
                    read_facts.append(
                        ProfileFact(row.page_profile_id, row.version_uid, row.page_number, row.content_key, row.status)
                    )
                    pages.append(PageFeatures(reader.open_profile(row), rules=settings.RULES, cache=cache))
                if not more or not rows:
                    break
                after = rows[-1].page_number
            for position, page in enumerate(pages):
                page.rel = position / max(1, len(pages) - 1)
            features[version] = pages
            if checkpoint is not None:
                checkpoint()
        digest = profile_digest(read_facts)
        result = build_rows(inputs.order, features, settings.RULES)
        summary = {
            "order": inputs.order,
            "page_counts": {v: len(features[v]) for v in inputs.order},
            "duplicates": result["duplicates"],
            "splits": result["splits"],
            "profile_algo": PAGE_PROFILE_ALGO_VERSION,
            "structure": settings.STRUCTURE_REVISION,
            "rows": len(result["rows"]),
        }
        with session_scope(self._factory) as session:
            if publish_guard is not None:
                publish_guard(session)
            self._repo.lock_builds(session, document_uid)
            existing = self._repo.build_for_inputs(
                session, document_uid=document_uid, order_id=inputs.order_id, signature=digest,
                rules=settings.RULES_VERSION, algo=settings.ALGO_VERSION,
            )
            if existing is not None:
                return BuildResult("existing", build=existing)
            built = self._repo.insert_build(
                session, project_uid=project_uid, document_uid=document_uid, order_id=inputs.order_id,
                signature=digest, rules=settings.RULES_VERSION, algo=settings.ALGO_VERSION,
                rows=result["rows"], unassigned=result["unassigned"], summary=summary,
            )
        if built is None:  # the same input set was built meanwhile
            with session_scope(self._factory) as session:
                built = self._repo.build_for_inputs(
                    session, document_uid=document_uid, order_id=inputs.order_id, signature=digest,
                    rules=settings.RULES_VERSION, algo=settings.ALGO_VERSION,
                )
            assert built is not None
            return BuildResult("existing", build=built)
        return BuildResult("built", build=built)


def read_adjacent_sheet_pairs(
    session_factory: sessionmaker[Session], *, project_uid: str, document_uid: str
) -> AdjacentSheetPairs:
    """The function ``CMP-SERIES-01`` reads: the sheet pairs of each adjacent transition of the effective matrix of
    ``document_uid`` (the latest build, the accepted AI links and the manual edits applied, a manual edit winning).
    See :mod:`~auditmanager.comparison.matrix.pairs` for what a pair is. A document set with no build is
    ``not_found``."""
    return ComparisonMatrixService(session_factory=session_factory).adjacent_sheet_pairs(
        project_uid=project_uid, document_uid=document_uid
    )
