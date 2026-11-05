"""A document's lifecycle after upload: archive, restore, rename (`UI-PARITY-P0G`, ruling `R-151a`).

The original deletes and renames folders; the owner ruled «Архив и переименование» instead. Nothing here deletes:

* ``set_document_archived`` hides a document from lists (``archived_at``, ``archived_by_user_uid``, migration 0052) or
  brings it back; its versions, runs, findings and decisions stay exactly as they were and stay addressable.
* ``rename_document`` changes ``document.display_title``; ``document_uid`` is the identity and never changes.

Each is a keyed command (``CommandRepository``): a replay of the same key and payload answers the same state and
writes nothing twice; the same key with another payload is ``idempotency_key_reuse``. Each appends one ``audit_event``
of aggregate ``Document`` in the same transaction -- the history of the flag and of the title -- and an archive or a
restore that would not change the state still records nothing.
"""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.ingest.commands import CommandReplay, CommandRepository, CommandStarted, payload_fingerprint
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import AuditEventId, DocumentUid, IdempotencyKey

#: The title bound of ``ck_document_display_title_length`` (migration 0002).
TITLE_MAX = 400

_LOCK = text(
    "SELECT document_uid, project_uid, archived_at, display_title FROM document "
    "WHERE document_uid = :document_uid FOR UPDATE"
)
_ARCHIVE = text(
    "UPDATE document SET archived_at = now(), archived_by_user_uid = :actor, updated_at = now() "
    "WHERE document_uid = :document_uid"
)
_RESTORE = text(
    "UPDATE document SET archived_at = NULL, archived_by_user_uid = NULL, updated_at = now() "
    "WHERE document_uid = :document_uid"
)
_RENAME = text(
    "UPDATE document SET display_title = :title, updated_at = now() WHERE document_uid = :document_uid"
)
_EVENT = text(
    "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, aggregate_id, payload) "
    "VALUES (:event_id, :event_type, 'Document', :document_uid, CAST(:payload AS jsonb))"
)


def _lock(session: Session, document_uid: str, project_uid: str) -> tuple[bool, str]:
    """Lock the document of this project; answer whether it is archived and its title. Unknown is ``not_found``."""
    row = session.execute(_LOCK, {"document_uid": document_uid}).first()
    if row is None or str(row[1]) != project_uid:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Document")
    return row[2] is not None, str(row[3])


def _event(session: Session, event_type: str, document_uid: str, payload: dict[str, str]) -> None:
    session.execute(_EVENT, {
        "event_id": str(AuditEventId.new()),
        "event_type": event_type,
        "document_uid": document_uid,
        "payload": json.dumps(payload, sort_keys=True, ensure_ascii=False),
    })


def set_document_archived(
    session: Session, *, project_uid: str, document_uid: str, archived: bool, actor_uid: str,
    idempotency_key: str, commands: CommandRepository | None = None,
) -> None:
    """Archive or restore one document. A document already in the asked state is left as it is."""
    DocumentUid.parse(document_uid)
    ledger = commands or CommandRepository()
    claimed = ledger.begin(
        session, command_type="set_document_archived", idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint({"document_uid": document_uid, "archived": archived}),
    )
    if isinstance(claimed, CommandReplay):
        return
    assert isinstance(claimed, CommandStarted)
    is_archived, _title = _lock(session, document_uid, project_uid)
    if archived and not is_archived:
        session.execute(_ARCHIVE, {"document_uid": document_uid, "actor": actor_uid})
        _event(session, "document.archived", document_uid, {"actor_uid": actor_uid})
    elif not archived and is_archived:
        session.execute(_RESTORE, {"document_uid": document_uid})
        _event(session, "document.restored", document_uid, {"actor_uid": actor_uid})
    ledger.succeed(session, claimed.command_id, {"document_uid": document_uid, "archived": archived})


def clean_title(value: str) -> str:
    """The title as stored: trimmed, inner runs of spaces kept; 1 to 400 characters, never blank."""
    title = value.strip()
    if not title or len(title) > TITLE_MAX:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, field="display_title", constraint="length",
            message=f"the display title is 1 to {TITLE_MAX} characters and not blank",
        )
    return title


def rename_document(
    session: Session, *, project_uid: str, document_uid: str, display_title: str, actor_uid: str,
    idempotency_key: str, commands: CommandRepository | None = None,
) -> None:
    """Change a document's display title; its identity stays. The same title again records nothing."""
    DocumentUid.parse(document_uid)
    title = clean_title(display_title)
    ledger = commands or CommandRepository()
    claimed = ledger.begin(
        session, command_type="rename_document", idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint({"document_uid": document_uid, "display_title": title}),
    )
    if isinstance(claimed, CommandReplay):
        return
    assert isinstance(claimed, CommandStarted)
    _archived, previous = _lock(session, document_uid, project_uid)
    if previous != title:
        session.execute(_RENAME, {"document_uid": document_uid, "title": title})
        _event(session, "document.renamed", document_uid, {"actor_uid": actor_uid, "from": previous, "to": title})
    ledger.succeed(session, claimed.command_id, {"document_uid": document_uid, "display_title": title})
