"""The comparison journal: ``comparison.*`` events in ``audit_event`` (`COMPARE-PERSISTED-SUMMARY-01`).

An expert who approves or withdraws a sheet pairing leaves a row in the append-only
``audit_event`` table **in the transaction of the change it describes** -- the idiom of the access
journal (`PROD-06`): the writer takes the caller's :class:`~sqlalchemy.orm.Session` and lets every
error propagate, so the change and its event commit or roll back together. A writer that opened its
own connection or swallowed its own failure would let the change commit without its event.

What a payload may hold: identities (``cmp_``, ``sln_``, ``ver_``, ``usr_``), page numbers, the link
revision and two digests -- nothing else. Never page text, a quote, a file name, a label or a model's
words. Three independent things keep it so, as in the access journal: a per-type allow-list of keys,
a value rule per key, and typed entry points that take arguments rather than a mapping.

The aggregate is the comparison (``Comparison``, addressed by its ``cmp_`` id). The id is not a
foreign key (``audit_event`` is a trail that must survive what it describes).
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.access.public import UserUid
from auditmanager.shared.errors import DomainError
from auditmanager.shared.identity import (
    AuditEventId,
    ComparisonId,
    CorrelationId,
    IdentityError,
    SheetLinkId,
    VersionUid,
)

AGGREGATE_TYPE: Final[str] = "Comparison"
EVENT_SHEET_LINK_APPROVED: Final[str] = "comparison.sheet_link_approved"
EVENT_SHEET_LINK_WITHDRAWN: Final[str] = "comparison.sheet_link_withdrawn"
EVENT_SUMMARY_GENERATED: Final[str] = "comparison.summary_generated"

_SHEET_KEYS: Final[frozenset[str]] = frozenset({
    "comparison_id", "sheet_link_id", "link_revision", "source_version_uid", "target_version_uid",
    "source_page_number", "target_page_number", "actor_uid",
})
#: ``event_type`` -> (keys that must be present, keys that may be present). The seal of a
#: withdrawal that empties the approved set does not exist, so that key is optional there.
PAYLOAD_KEYS: Final[Mapping[str, tuple[frozenset[str], frozenset[str]]]] = {
    EVENT_SHEET_LINK_APPROVED: (_SHEET_KEYS | {"raw_evidence_seal_sha256"}, frozenset()),
    EVENT_SHEET_LINK_WITHDRAWN: (_SHEET_KEYS, frozenset({"raw_evidence_seal_sha256"})),
}
PAYLOAD_KEYS = {
    **PAYLOAD_KEYS,
    EVENT_SUMMARY_GENERATED: (
        frozenset({
            "comparison_id", "link_revision", "summary_id", "input_sha256",
            "raw_evidence_seal_sha256", "state", "actor_uid",
        }),
        frozenset(),
    ),
}
COMPARISON_EVENT_TYPES: Final[tuple[str, ...]] = tuple(PAYLOAD_KEYS)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_INSERT = text(
    "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, aggregate_id, "
    "correlation_id, payload) VALUES (:event_id, :event_type, :aggregate_type, "
    ":aggregate_id, :correlation_id, CAST(:payload AS jsonb))"
)

_IDENTITY_KEYS: Final[Mapping[str, type]] = {
    "comparison_id": ComparisonId,
    "sheet_link_id": SheetLinkId,
    "source_version_uid": VersionUid,
    "target_version_uid": VersionUid,
    "actor_uid": UserUid,
}


def _checked(key: str, value: object) -> object:
    if key in _IDENTITY_KEYS:
        try:
            return str(_IDENTITY_KEYS[key].parse(value))  # type: ignore[attr-defined]
        except (IdentityError, DomainError, TypeError):
            raise ValueError(f"comparison journal: {key} is not a valid identity") from None
    if key == "link_revision":
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError("comparison journal: link_revision must be a positive integer")
        return value
    if key in ("source_page_number", "target_page_number"):
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 500:
            raise ValueError(f"comparison journal: {key} must be a page number")
        return value
    if key in ("raw_evidence_seal_sha256", "input_sha256"):
        if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
            raise ValueError(f"comparison journal: {key} must be a SHA-256")
        return value
    if key == "summary_id":
        try:
            return str(AuditEventId.parse(value))
        except (IdentityError, DomainError, TypeError):
            raise ValueError("comparison journal: summary_id is not a valid identity") from None
    if key == "state":
        if value not in ("ready", "rejected"):
            raise ValueError("comparison journal: state is outside the closed vocabulary")
        return value
    raise ValueError(f"comparison journal: no value rule for {key!r}")  # pragma: no cover


def validated(event_type: str, payload: Mapping[str, object]) -> dict[str, object]:
    """The payload as it will be stored, or a ``ValueError`` naming what is wrong."""
    required, optional = PAYLOAD_KEYS[event_type]
    keys = set(payload)
    if not required <= keys:
        raise ValueError(f"comparison journal: {event_type} lacks {sorted(required - keys)}")
    if not keys <= required | optional:
        raise ValueError(
            f"comparison journal: {event_type} payload contains a non-allowlisted field "
            f"{sorted(keys - (required | optional))}"
        )
    return {key: _checked(key, value) for key, value in payload.items()}


def _append(
    session: Session, *, event_type: str, payload: Mapping[str, object],
    correlation_id: str | None, event_id: str | None = None,
) -> None:
    """INSERT one event on the caller's session. It never commits and never swallows."""
    checked = validated(event_type, payload)
    bound = None if correlation_id is None else str(CorrelationId.parse(correlation_id))
    session.execute(_INSERT, {
        "event_id": str(AuditEventId.new()) if event_id is None else str(AuditEventId.parse(event_id)),
        "event_type": event_type,
        "aggregate_type": AGGREGATE_TYPE,
        "aggregate_id": checked["comparison_id"],
        "correlation_id": bound,
        "payload": json.dumps(checked, sort_keys=True),
    })


def record_sheet_link_approved(
    session: Session,
    *,
    comparison_id: str,
    sheet_link_id: str,
    link_revision: int,
    source_version_uid: str,
    target_version_uid: str,
    source_page_number: int,
    target_page_number: int,
    actor_uid: str,
    raw_evidence_seal_sha256: str,
    correlation_id: str | None,
) -> None:
    _append(
        session,
        event_type=EVENT_SHEET_LINK_APPROVED,
        payload={
            "comparison_id": comparison_id, "sheet_link_id": sheet_link_id,
            "link_revision": link_revision, "source_version_uid": source_version_uid,
            "target_version_uid": target_version_uid, "source_page_number": source_page_number,
            "target_page_number": target_page_number, "actor_uid": actor_uid,
            "raw_evidence_seal_sha256": raw_evidence_seal_sha256,
        },
        correlation_id=correlation_id,
    )


def record_sheet_link_withdrawn(
    session: Session,
    *,
    comparison_id: str,
    sheet_link_id: str,
    link_revision: int,
    source_version_uid: str,
    target_version_uid: str,
    source_page_number: int,
    target_page_number: int,
    actor_uid: str,
    raw_evidence_seal_sha256: str | None,
    correlation_id: str | None,
) -> None:
    payload: dict[str, object] = {
        "comparison_id": comparison_id, "sheet_link_id": sheet_link_id,
        "link_revision": link_revision, "source_version_uid": source_version_uid,
        "target_version_uid": target_version_uid, "source_page_number": source_page_number,
        "target_page_number": target_page_number, "actor_uid": actor_uid,
    }
    if raw_evidence_seal_sha256 is not None:
        payload["raw_evidence_seal_sha256"] = raw_evidence_seal_sha256
    _append(
        session, event_type=EVENT_SHEET_LINK_WITHDRAWN, payload=payload,
        correlation_id=correlation_id,
    )


def record_summary_generated(
    session: Session,
    *,
    event_id: str,
    comparison_id: str,
    link_revision: int,
    input_sha256: str,
    raw_evidence_seal_sha256: str,
    state: str,
    actor_uid: str,
    correlation_id: str | None,
) -> None:
    """A summary was stored (``ready``) or its reply was refused (``rejected``). ``event_id`` is the
    summary's own identity: one id, the row and its event."""
    _append(
        session,
        event_type=EVENT_SUMMARY_GENERATED,
        payload={
            "comparison_id": comparison_id, "link_revision": link_revision, "summary_id": event_id,
            "input_sha256": input_sha256, "raw_evidence_seal_sha256": raw_evidence_seal_sha256,
            "state": state, "actor_uid": actor_uid,
        },
        correlation_id=correlation_id,
        event_id=event_id,
    )


__all__ = [
    "AGGREGATE_TYPE", "COMPARISON_EVENT_TYPES", "EVENT_SHEET_LINK_APPROVED",
    "EVENT_SHEET_LINK_WITHDRAWN", "EVENT_SUMMARY_GENERATED", "PAYLOAD_KEYS",
    "record_sheet_link_approved", "record_sheet_link_withdrawn", "record_summary_generated",
    "validated",
]
