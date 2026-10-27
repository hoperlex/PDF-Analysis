"""The order in which the versions of a document set are compared: append-only revisions, an expert's act.

ADR-0025 decisions 14 and 16 (`CMP-INGEST-01`). «Порядок версий» is the user's: the numbers in file names, the
«Изм.» of the stamps and the release dates are hints (the proposal, :mod:`.proposal`), and the order the user
confirms is what a comparison reads. It is stored as revisions of ``comparison_version_order``: each a JSON array of
the document's version identities, numbered ``1, 2, 3, ...`` without a gap, **never updated or deleted** (the table
refuses both). A new revision names the latest revision the caller saw (``base_revision_no``, ``0`` for none); a
stale one is ``conflict`` (``comparison_version_order_stale``) and the caller rebases.

**The order never changes the documents' ordinal.** ``document_version.version_ordinal`` is the document's
publication order, which runs and finding carry-over use (``D-5``); it is immutable, and nothing here writes it. A
revision lists **every** version of the document exactly once (a version left out, listed twice or belonging to
another document is ``validation_failed`` / ``comparison_set_members``, the registered reason for a member list that
is not the set's): a partial order would silently drop a version from every comparison, and there is no fallback to
"the versions that were listed".

**An expert's act** (decision 16, ``R-60``): an administrator without the ``expert`` role is refused. The edge
refuses it first (``OPERATION_ROLES``); :func:`~.service.require_expert` is this command's own check.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.documents.public import DocumentRepository
from auditmanager.ingest.commands import (
    CommandReplay,
    CommandRepository,
    CommandStarted,
    payload_fingerprint,
)
from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, IdempotencyKey, ProjectUid

from .repository import ComparisonUploadRepository, OrderRow, new_order_id
from .service import require_expert
from .views import OrderPageView, OrderView

__all__ = ["COMMAND_APPEND_ORDER", "ComparisonVersionOrderService", "ORDER_PAGE_MAX"]

#: The command type is the snake case of the operationId (``scripts/recovery/product_purge.py`` registers it).
COMMAND_APPEND_ORDER: Final[str] = "append_comparison_version_order"
#: The most revisions one page returns; the contract's ``limit`` bound is the edge's, this is the floor's.
ORDER_PAGE_MAX: Final[int] = 200
_SOURCE_EXPERT: Final[str] = "expert"


def _view(row: OrderRow) -> OrderView:
    return OrderView(
        order_id=row.order_id,
        document_uid=row.document_uid,
        revision_no=row.revision_no,
        version_uids=row.version_uids,
        source=row.source,
        created_at=row.created_at,
        created_by=row.actor_user_uid,
    )


class ComparisonVersionOrderService:
    __slots__ = ("_factory", "_documents", "_commands", "_repo")

    def __init__(self, *, session_factory: sessionmaker[Session] | None = None) -> None:
        self._factory = session_factory
        self._documents = DocumentRepository()
        self._commands = CommandRepository()
        self._repo = ComparisonUploadRepository()

    def _require_document(self, session: Session, project_uid: str, document_uid: str) -> None:
        """The project exists and owns the document; either missing is ``not_found`` naming what was addressed."""
        self._documents.get_project(session, ProjectUid.parse(project_uid))
        if str(self._documents.require_document(session, DocumentUid.parse(document_uid))) != project_uid:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Document")

    def list_orders(
        self, *, project_uid: str, document_uid: str, before_revision: int | None, limit: int
    ) -> OrderPageView:
        """The revisions, newest first. ``before_revision`` is the oldest revision the previous page held."""
        bounded = max(1, min(limit, ORDER_PAGE_MAX))
        with session_scope(self._factory) as session:
            self._require_document(session, project_uid, document_uid)
            rows = self._repo.list_orders(session, document_uid, before_revision=before_revision, limit=bounded + 1)
        page = rows[:bounded]
        more = len(rows) > bounded
        return OrderPageView(
            items=tuple(_view(row) for row in page),
            next_before_revision=page[-1].revision_no if more and page else None,
        )

    def append_order(
        self,
        *,
        project_uid: str,
        document_uid: str,
        version_uids: Sequence[str],
        base_revision_no: int,
        user_uid: str,
        actor_label: str,
        actor_roles: frozenset[str],
        idempotency_key: str,
    ) -> OrderView:
        """Append one revision, or answer the recorded outcome of an identical earlier request."""
        require_expert(actor_roles)
        key = IdempotencyKey(idempotency_key)
        fingerprint = payload_fingerprint(
            {
                "command": "append_comparison_version_order.v1",
                "project_uid": project_uid,
                "document_uid": document_uid,
                "version_uids": list(version_uids),
                "base_revision_no": base_revision_no,
            }
        )
        label = " ".join(actor_label.split())[:128]
        with session_scope(self._factory) as session:
            self._require_document(session, project_uid, document_uid)
            claim = self._commands.begin(
                session, command_type=COMMAND_APPEND_ORDER, idempotency_key=key, fingerprint=fingerprint
            )
            if isinstance(claim, CommandReplay):
                recorded = self._repo.latest_order_of_command(session, str(claim.command_id))
                if recorded is None:  # pragma: no cover - a succeeded command names the revision it appended
                    raise DomainError(ErrorCode.IDEMPOTENCY_KEY_STALE, command_type=COMMAND_APPEND_ORDER)
                return _view(recorded)
            assert isinstance(claim, CommandStarted)

            # One decision: the chain trigger takes this lock too, so the stale check and the insert cannot be split.
            self._repo.lock_document_order(session, document_uid)
            latest = self._repo.latest_order(session, document_uid)
            latest_no = latest.revision_no if latest else 0
            if base_revision_no != latest_no:
                raise DomainError(ErrorCode.CONFLICT, conflict_reason="comparison_version_order_stale")

            held = {str(item.version_uid) for item in self._documents.list_versions(session, DocumentUid.parse(document_uid))}
            if not version_uids or len(set(version_uids)) != len(version_uids) or set(version_uids) != held:
                raise DomainError(
                    ErrorCode.VALIDATION_FAILED, field="version_uids", constraint="comparison_set_members"
                )
            row = self._repo.insert_order(
                session,
                order_id=new_order_id(),
                project_uid=project_uid,
                document_uid=document_uid,
                revision_no=latest_no + 1,
                version_uids=version_uids,
                source=_SOURCE_EXPERT,
                actor_user_uid=user_uid,
                actor_label=label or "эксперт",
                command_id=str(claim.command_id),
            )
            self._commands.succeed(session, claim.command_id, {"order_id": row.order_id, "revision_no": row.revision_no})
            return _view(row)
