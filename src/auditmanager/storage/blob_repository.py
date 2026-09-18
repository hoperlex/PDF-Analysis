"""Blob-metadata persistence: the lifecycle record for bytes the BlobStore holds.

Added by ``B1`` at the Gate A boundary, as ``port.py`` anticipated: "It is an
*addition*: it persists the :class:`PublishedBlob` records this port already returns and
the ``machines.blob`` state each record already carries."

**This repository is not the identity authority, and cannot become one.**
``blob_id`` is derived by :func:`auditmanager.storage.models.derive_blob_id` from
``(sha256, size)``. This module never allocates one; every write re-derives the
identifier from the content facts it is given and refuses the write if the result
disagrees with the identifier the adapter handed it. That check is what keeps the row
and the object addressing the same bytes, and it is why the schema's
``uq_blob_available_content`` on ``(sha256, size_bytes)`` agrees with the adapter rather
than competing with it: identical content collides on the primary key first.

Lifecycle
---------
The declared ``blob`` machine is ``temporary -> verifying -> available``, with
``-> rejected`` as the refusal edge. Every move is checked twice, on purpose:

* by :mod:`auditmanager.shared.statemachine` before the statement is issued, so a caller
  gets the typed catalog code instead of a driver error;
* by ``trg_blob_state_guard`` in the database, which reads the same
  ``contract_state_transition`` rows. No code path bypasses the second check.

The row is written **after verification and before publication**. That ordering is what
makes an interrupted publication recoverable: a committed ``verifying`` row is the
database's record that these exact bytes were about to become canonical, so
``auditmanager.ingest.reconciliation`` can find an orphaned object by asking the store
about a blob the database never finished -- without the port needing a ``list``
operation it deliberately does not have.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.statemachine import Topology, assert_initial, assert_transition
from auditmanager.shared.statemachine import load as load_topology

from .models import BlobId, BlobState, VerifiedBlob, derive_blob_id, parse_blob_id

__all__ = ["BLOB_MACHINE", "BlobMetadataRecord", "BlobMetadataRepository"]

#: The machine name as ``contract_state_transition`` spells it.
BLOB_MACHINE: Final[str] = "blob"

_COLUMNS = "blob_id, state, sha256, size_bytes, media_type, created_at, updated_at"

_SELECT = text(f"SELECT {_COLUMNS} FROM blob WHERE blob_id = :blob_id")
_INSERT = text(
    "INSERT INTO blob (blob_id, state, sha256, size_bytes, media_type) "
    "VALUES (:blob_id, :state, :sha256, :size_bytes, :media_type)"
)
_ADVANCE = text(
    "UPDATE blob SET state = :to_state, updated_at = now() "
    "WHERE blob_id = :blob_id AND state = :from_state"
)
_SELECT_IN_STATES = text(
    f"SELECT {_COLUMNS} FROM blob WHERE state = ANY(:states) ORDER BY created_at"
)


@dataclass(frozen=True, slots=True)
class BlobMetadataRecord:
    """One row of ``blob``. Content facts and lifecycle state, never a location.

    The table carries no bucket and no object-key column at all -- that is the schema's
    own comment on it -- so this record cannot expose one.
    """

    blob_id: BlobId
    state: BlobState
    sha256: str | None
    size_bytes: int | None
    media_type: str | None
    created_at: datetime
    updated_at: datetime

    @property
    def is_available(self) -> bool:
        return self.state is BlobState.AVAILABLE

    @property
    def is_settled(self) -> bool:
        """True when the lifecycle reached a state reconciliation need not revisit."""
        return self.state in (BlobState.AVAILABLE, BlobState.REJECTED, BlobState.ERASED)


def _record(row: Any) -> BlobMetadataRecord:
    blob_id, state, sha256, size_bytes, media_type, created_at, updated_at = tuple(row)
    return BlobMetadataRecord(
        blob_id=parse_blob_id(blob_id),
        state=BlobState(state),
        sha256=sha256,
        size_bytes=None if size_bytes is None else int(size_bytes),
        media_type=media_type,
        created_at=created_at,
        updated_at=updated_at,
    )


class BlobMetadataRepository:
    """Persist and advance the lifecycle of blobs the BlobStore holds."""

    __slots__ = ("_topology",)

    def __init__(self) -> None:
        self._topology: Topology | None = None

    def topology(self, session: Session) -> Topology:
        """The declared topology, read from the rows the trigger reads.

        Cached on the instance: ``contract_state_transition`` is reference data the
        migration freezes against INSERT, UPDATE and DELETE alike, so it cannot change
        under a live process without a migration.
        """
        if self._topology is None:
            self._topology = load_topology(session)
        return self._topology

    # -- reads ---------------------------------------------------------------

    def get(self, session: Session, blob_id: BlobId) -> BlobMetadataRecord | None:
        row = session.execute(_SELECT, {"blob_id": str(blob_id)}).first()
        return None if row is None else _record(row)

    def require(self, session: Session, blob_id: BlobId) -> BlobMetadataRecord:
        record = self.get(session, blob_id)
        if record is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Blob")
        return record

    def unsettled(self, session: Session) -> tuple[BlobMetadataRecord, ...]:
        """Every blob whose lifecycle stopped before a settled state.

        These are exactly the candidates an interrupted publication leaves behind, and
        the reason the metadata row is written before the object is made canonical.
        """
        rows = session.execute(
            _SELECT_IN_STATES,
            {"states": [BlobState.TEMPORARY.value, BlobState.VERIFYING.value]},
        ).all()
        return tuple(_record(row) for row in rows)

    # -- writes --------------------------------------------------------------

    def record_verified(
        self, session: Session, verified: VerifiedBlob
    ) -> BlobMetadataRecord:
        """Record verified content as ``verifying``: about to be published.

        Idempotent by content. Re-recording bytes already ``available`` returns the
        existing row untouched -- available metadata is write-once and the adapter is
        idempotent by ``(sha256, size)`` -- and resuming an interrupted publication
        finds the row already in ``verifying`` and leaves it there.
        """
        self._assert_derived(verified)
        topology = self.topology(session)

        existing = self.get(session, verified.blob_id)
        if existing is None:
            assert_initial(topology, BLOB_MACHINE, BlobState.TEMPORARY.value)
            session.execute(
                _INSERT,
                {
                    "blob_id": str(verified.blob_id),
                    "state": BlobState.TEMPORARY.value,
                    "sha256": verified.sha256,
                    "size_bytes": verified.size,
                    "media_type": verified.media_type,
                },
            )
            existing = self.require(session, verified.blob_id)

        if existing.state in (BlobState.AVAILABLE, BlobState.VERIFYING):
            self._assert_same_content(existing, verified)
            return existing
        return self._advance(
            session, verified.blob_id, existing.state, BlobState.VERIFYING
        )

    def mark_available(self, session: Session, blob_id: BlobId) -> BlobMetadataRecord:
        """``verifying -> available``. The bytes are canonical and readable."""
        current = self.require(session, blob_id)
        if current.state is BlobState.AVAILABLE:
            return current
        return self._advance(session, blob_id, current.state, BlobState.AVAILABLE)

    def mark_rejected(self, session: Session, blob_id: BlobId) -> BlobMetadataRecord:
        """``temporary|verifying -> rejected``. The bytes never became canonical."""
        current = self.require(session, blob_id)
        if current.state is BlobState.REJECTED:
            return current
        return self._advance(session, blob_id, current.state, BlobState.REJECTED)

    # -- internals -----------------------------------------------------------

    def _advance(
        self,
        session: Session,
        blob_id: BlobId,
        from_state: BlobState,
        to_state: BlobState,
    ) -> BlobMetadataRecord:
        assert_transition(
            self.topology(session), BLOB_MACHINE, from_state.value, to_state.value
        )
        result = session.execute(
            _ADVANCE,
            {
                "blob_id": str(blob_id),
                "from_state": from_state.value,
                "to_state": to_state.value,
            },
        )
        if result.rowcount != 1:
            # Somebody else moved the row between the read and the write. Report the
            # transition that is no longer available rather than retrying: a retry that
            # does not consult the command record writes duplicates.
            raise DomainError(
                ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
                machine=BLOB_MACHINE,
                current_state=from_state.value,
                requested_state=to_state.value,
            )
        return self.require(session, blob_id)

    @staticmethod
    def _assert_derived(verified: VerifiedBlob) -> None:
        """Refuse any identifier this repository did not just re-derive from content.

        The repository records lifecycle. If it ever accepted an identifier it could not
        reproduce from ``(sha256, size)``, it would have become the allocator, and the
        row and the object could then address different bytes.
        """
        expected = derive_blob_id(sha256=verified.sha256, size=verified.size)
        if expected != verified.blob_id:
            raise DomainError(
                ErrorCode.STORAGE_INTEGRITY_ERROR,
                blob_id=str(verified.blob_id),
                expected_sha256=verified.sha256,
            )

    @staticmethod
    def _assert_same_content(
        existing: BlobMetadataRecord, verified: VerifiedBlob
    ) -> None:
        if existing.sha256 is None:
            # `D-4`, the second site. This used to send `existing.sha256 or ""` into the
            # envelope -- an empty string where a digest is expected, and a claim about
            # bytes nothing has looked at, which is the exact shape `verify_version` was
            # repaired for at `1b2549b`.
            #
            # **It is unreachable, and saying so is the repair.** The row reaches here
            # only in `available` or `verifying`. `ck_blob_available_is_verified` forbids
            # a NULL digest on an `available` row outright; a `verifying` row could carry
            # one as far as the schema is concerned, and does not, because `_INSERT` is
            # the only statement in the tree that creates a `blob` row and it always
            # supplies `verified.sha256`. So the `| None` on the record is the column's
            # type, not a state this writer can produce.
            #
            # An unreachable branch that invents a plausible value is worse than one that
            # refuses: the empty string would have reached an operator looking exactly
            # like a digest of nothing. This names the invariant instead.
            raise DomainError(
                ErrorCode.INTERNAL_ERROR,
                message=(
                    "a blob row in a verified state carries no digest; this is a "
                    "storage invariant, not a fact about the bytes the caller sent"
                ),
            )
        if existing.sha256 != verified.sha256 or existing.size_bytes != verified.size:
            raise DomainError(
                ErrorCode.STORAGE_INTEGRITY_ERROR,
                blob_id=str(verified.blob_id),
                expected_sha256=verified.sha256,
                actual_sha256=existing.sha256,
            )
