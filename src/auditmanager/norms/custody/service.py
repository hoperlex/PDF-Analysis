"""Two-phase custody of normative-corpus source PDFs and crops (`R-76`, `R-104`, plan §3.1).

**Phase one -- admission, then dispatch.** :func:`admit` appends one ``pending``
``norm_custody_admission`` row in the caller's transaction: the slot (role, target, anchor),
the content-derived ``blob_id`` and the declared size, SHA-256 and media type, each checked
against the verified bundle manifest. The row *is* the outbox entry; no object-store call
happens in that transaction, and the target need not exist yet. :class:`CustodyDispatcher`
then drives due ``pending`` rows, at least once: it declares the Blob row, stages the bytes,
reads them back, records them ``verifying``, publishes them canonically and, in a final
transaction, marks the Blob ``available`` and the admission ``confirmed``. **No binding is
visible after phase one.**

**Phase two -- binding publication.** :func:`publish_bindings` runs inside the transaction
that inserts or holds the target rows. It locks the confirmed admissions of those targets,
checks invariant 4 there (the target exists *now*), and inserts each binding with its audit
event. A confirmed admission whose target never arrives stays unbound and is reported; it is
never bound by guessing.

The five interruption points
----------------------------
A process lost at any of them leaves only states a later ``dispatch`` converges from, with one
Blob row, one canonical object and no binding:

1. ``admitted`` -- the admission committed, nothing dispatched;
2. ``blob_declared`` -- the Blob row is ``temporary`` (or was already there), nothing staged;
3. ``temporary_staged`` -- the bytes are staged under the admission's own upload token;
4. ``blob_verifying`` -- read back and recorded ``verifying``, not yet canonical;
5. ``object_published`` -- canonical, the confirmation transaction absent.

The upload token is the admission's ``nad`` identity, so a re-drive restages onto the same
temporary key; publication is idempotent by content, and a canonical object is reused only
after its recorded size, SHA-256 and media type are checked.

Failure classes
---------------
A byte mismatch, a media-type conflict, an object the store cannot vouch for and a ``rejected``
Blob (`D-143`) **reject the admission, never the shared Blob row**; the slot is then free for a
corrected admission with a new ``nad``. A transient failure (the store unreachable, a staged
upload lost, the source unreadable) counts one try and reschedules it (30 s, 5 min, 30 min,
2 h); the fifth failed try leaves the row ``poisoned`` until :func:`requeue`. Anything else
counts a try and is re-raised: an unclassified failure stops the pass loudly.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import (
    BlobAttributeConflictError,
    BlobDeclaration,
    BlobIntegrityError,
    BlobMetadataInvalidError,
    BlobMetadataRecord,
    BlobMetadataRepository,
    BlobNotFoundError,
    BlobState,
    BlobStore,
    StorageError,
    declare_blob,
    derive_blob_id,
    parse_blob_id,
    parse_blob_role,
)

from .errors import D143_REASON, CustodyRefused, d143_refusal
from .model import (
    MAX_ATTEMPTS,
    Admission,
    AdmissionRequest,
    AdmissionState,
    AdmitOutcome,
    BindingDigestEntry,
    BindingPublication,
    CustodyIncident,
    CustodyManifest,
    CustodyReconciliation,
    CustodyReport,
    CustodySlot,
    CustodySource,
    DeclaredContent,
    DispatchReport,
    DispatchResult,
    DispatchStep,
    IncidentKind,
    binding_digest,
)
from .repository import CustodyRepository
from .roles import require_anchor, require_target, shape_of

#: A hook called after each durable dispatch step. Tests raise from it to model a process
#: lost at that point; production passes ``None``.
Checkpoint = Callable[[str], None]

ADMIT_COMMAND_TYPE = "norm_custody.admit"
_ADMISSION_AGGREGATE = "NormCustodyAdmission"
_BINDING_AGGREGATE = "NormCustodyBinding"

_repository = CustodyRepository()


# --- phase one: admission ------------------------------------------------------------


def admit(
    session: Session,
    request: AdmissionRequest,
    *,
    manifest: CustodyManifest,
    blobs: BlobMetadataRepository | None = None,
) -> AdmitOutcome:
    """Append one admission in the caller's transaction, or replay the identical one.

    Refused before any write: an unknown role, target kind or anchor kind; a slot the
    manifest does not name, or names with other content; a live admission of the slot with
    other content (``idempotency_key_reuse``, scope = command type + slot); bytes whose Blob
    row is ``rejected`` (`D-143`); bytes already stored under another media type
    (``conflict``). The same slot with the same content replays and writes nothing.
    """
    shape = shape_of(request.role)
    require_target(shape, request.target_id)
    require_anchor(shape, request.anchor_kind, request.anchor)
    if not isinstance(request.media_type, str) or not 1 <= len(request.media_type) <= 255:
        raise CustodyRefused(
            "media_type_malformed",
            ErrorCode.VALIDATION_FAILED,
            field="media_type",
            constraint="1 to 255 characters",
        )
    try:
        declaration = declare_blob(
            sha256=request.sha256,
            size=request.size,
            role=parse_blob_role(shape.role),
            media_type=request.media_type,
        )
    except BlobMetadataInvalidError:
        raise CustodyRefused(
            "content_malformed",
            ErrorCode.VALIDATION_FAILED,
            field="declared_content",
            constraint="a 64-hex SHA-256 and a non-negative byte size",
        ) from None
    content = DeclaredContent(
        sha256=declaration.sha256, size=declaration.size, media_type=declaration.media_type
    )
    slot = CustodySlot(
        role=shape.role,
        target_kind=shape.target_kind,
        target_id=request.target_id,
        anchor_kind=request.anchor_kind,
        anchor=request.anchor,
    )

    manifested = manifest.declared(slot)
    if manifested is None:
        raise CustodyRefused(
            "not_in_manifest",
            ErrorCode.VALIDATION_FAILED,
            field="anchor",
            constraint="named by the verified bundle manifest",
        )
    if manifested != content:
        raise CustodyRefused(
            "manifest_mismatch",
            ErrorCode.VALIDATION_FAILED,
            field="declared_content",
            constraint="equal to the verified bundle manifest",
        )

    replay = _replay_or_refuse(_repository.live_in_slot(session, slot), content)
    if replay is not None:
        return replay

    record = (blobs or BlobMetadataRepository()).get(session, declaration.blob_id)
    if record is not None:
        if record.state is BlobState.REJECTED:
            raise d143_refusal()
        if record.media_type != content.media_type:
            raise _media_type_conflict()

    inserted = _repository.insert_admission(
        session, slot, blob_id=str(declaration.blob_id), content=content
    )
    if inserted is None:
        # A concurrent admission of the same slot committed between the read and the
        # insert; the partial unique index chose it. Replay it or refuse, as above.
        replay = _replay_or_refuse(_repository.live_in_slot(session, slot), content)
        if replay is None:  # pragma: no cover - the index guarantees a live row
            raise DomainError(ErrorCode.INTERNAL_ERROR)
        return replay
    _repository.append_event(
        session,
        event_type="norm_custody.admitted",
        aggregate_type=_ADMISSION_AGGREGATE,
        aggregate_id=inserted.admission_id,
        payload={
            "state": inserted.state.value,
            "role": inserted.role,
            "target_kind": inserted.target_kind,
            "target_id": inserted.target_id,
            "anchor_kind": inserted.anchor_kind,
            "blob_id": inserted.blob_id,
        },
    )
    return AdmitOutcome(admission=inserted, replayed=False)


def _replay_or_refuse(live: Admission | None, content: DeclaredContent) -> AdmitOutcome | None:
    if live is None:
        return None
    if live.content != content:
        raise CustodyRefused(
            "slot_reuse",
            ErrorCode.IDEMPOTENCY_KEY_REUSE,
            command_type=ADMIT_COMMAND_TYPE,
        )
    return AdmitOutcome(admission=live, replayed=True)


def _media_type_conflict() -> CustodyRefused:
    return CustodyRefused(
        "media_type_conflict",
        ErrorCode.CONFLICT,
        aggregate_type="Blob",
        conflict_reason="media_type_conflict",
    )


def requeue(session: Session, admission_ids: Sequence[str]) -> tuple[str, ...]:
    """Return ``poisoned`` admissions to ``pending`` with a fresh try count.

    A ``pending`` one is left as it is (an exact replay); a ``confirmed`` or ``rejected``
    one is terminal and refused before anything is written.
    """
    locked: list[Admission] = []
    for admission_id in sorted(set(admission_ids)):
        admission = _repository.lock(session, admission_id)
        if admission is None:
            raise CustodyRefused(
                "admission_unknown", ErrorCode.NOT_FOUND, aggregate_type=_ADMISSION_AGGREGATE
            )
        if admission.state in (AdmissionState.CONFIRMED, AdmissionState.REJECTED):
            raise CustodyRefused(
                "admission_terminal",
                ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
                machine="norm_custody_admission",
                current_state=admission.state.value,
                requested_state=AdmissionState.PENDING.value,
            )
        locked.append(admission)
    requeued: list[str] = []
    for admission in locked:
        if admission.state is AdmissionState.POISONED and _repository.requeue(session, admission):
            _repository.append_event(
                session,
                event_type="norm_custody.requeued",
                aggregate_type=_ADMISSION_AGGREGATE,
                aggregate_id=admission.admission_id,
                payload={"state": AdmissionState.PENDING.value, "from_state": "poisoned"},
            )
            requeued.append(admission.admission_id)
    return tuple(requeued)


# --- phase one: dispatch ---------------------------------------------------------------


class CustodyDispatcher:
    """At-least-once publication of admitted bytes, one due admission at a time."""

    __slots__ = ("_store", "_source", "_factory", "_blobs", "_checkpoint")

    def __init__(
        self,
        store: BlobStore,
        *,
        source: CustodySource,
        session_factory: sessionmaker[Session] | None = None,
        checkpoint: Checkpoint | None = None,
    ) -> None:
        self._store = store
        self._source = source
        self._factory = session_factory
        self._blobs = BlobMetadataRepository()
        self._checkpoint = checkpoint

    def dispatch(self, *, until_idle: bool = True) -> DispatchReport:
        """``dispatch --until-idle``: take due admissions until none is due now."""
        steps: list[DispatchStep] = []
        while True:
            step = self.dispatch_one()
            if step is None:
                break
            steps.append(step)
            if not until_idle:
                break
        with session_scope(self._factory) as session:
            counts = _repository.state_counts(session, role=None, target_ids=None)
        return DispatchReport(
            steps=tuple(steps),
            pending=counts.get(AdmissionState.PENDING, 0),
            poisoned=counts.get(AdmissionState.POISONED, 0),
        )

    def dispatch_one(self) -> DispatchStep | None:
        """Drive the next due admission through one try; ``None`` when none is due."""
        # Transaction 1: claim, check the Blob row, declare it.
        with session_scope(self._factory) as session:
            admission = _repository.claim_next(session)
            if admission is None:
                return None
            blob_id = parse_blob_id(admission.blob_id)
            self._blobs.lock(session, blob_id)
            record = self._blobs.get(session, blob_id)
            refusal = _blob_row_refusal(record, admission)
            if refusal is not None:
                return self._reject_in(session, admission, refusal)
            reuse = record is not None and record.state is BlobState.AVAILABLE
            if not reuse:
                try:
                    self._blobs.record_declared(session, _declaration(admission))
                except DomainError as exc:
                    return self._reject_in(session, admission, _domain_failure(exc))
        self._reached("blob_declared")

        try:
            if reuse:
                failure = self._check_canonical(admission)
                if failure is not None:
                    return self._reject(admission, failure)
            else:
                self._publish(admission)
        except _Rejected as rejected:
            return self._reject(admission, rejected.failure)
        except (StorageError, OSError) as exc:
            return self._failed_try(admission, _transient_failure(exc))
        except Exception:
            self._failed_try(admission, ErrorCode.INTERNAL_ERROR.value)
            raise

        # Transaction 3: confirm. The Blob becomes available in the same transaction.
        with session_scope(self._factory) as session:
            current = _repository.lock(session, admission.admission_id)
            if current is None or current.state is not AdmissionState.PENDING:
                return DispatchStep(admission.admission_id, DispatchResult.SETTLED_ELSEWHERE)
            self._blobs.mark_available(session, blob_id)
            _repository.confirm(session, current)
            _repository.append_event(
                session,
                event_type="norm_custody.confirmed",
                aggregate_type=_ADMISSION_AGGREGATE,
                aggregate_id=current.admission_id,
                payload={"state": AdmissionState.CONFIRMED.value, "blob_id": current.blob_id},
            )
        return DispatchStep(admission.admission_id, DispatchResult.CONFIRMED)

    # -- the external effect ---------------------------------------------------------

    def _publish(self, admission: Admission) -> None:
        declaration = _declaration(admission)
        content = self._source.open(admission)
        try:
            temporary = self._store.stage_temporary(
                content,
                declared_sha256=declaration.sha256,
                declared_size=declaration.size,
                role=declaration.role,
                media_type=declaration.media_type,
                upload_token=admission.admission_id,
            )
        finally:
            if not isinstance(content, (bytes, bytearray)):
                content.close()
        self._reached("temporary_staged")
        try:
            verified = self._store.verify_temporary(temporary)
        except BlobIntegrityError:
            # The adapter already removed the staged bytes.
            raise _Rejected("storage_integrity_error") from None
        try:
            with session_scope(self._factory) as session:
                self._blobs.record_verified(session, verified)
        except DomainError as exc:
            self._store.discard_temporary(temporary)
            raise _Rejected(_domain_failure(exc)) from None
        self._reached("blob_verifying")
        try:
            self._store.publish(verified)
        except BlobAttributeConflictError:
            raise _Rejected("media_type_conflict") from None
        except BlobMetadataInvalidError:
            raise _Rejected("object_unverifiable") from None
        except BlobIntegrityError:
            raise _Rejected("storage_integrity_error") from None
        self._reached("object_published")

    def _check_canonical(self, admission: Admission) -> str | None:
        """Reuse an ``available`` Blob only after its object's recorded facts are checked."""
        try:
            published = self._store.inspect(parse_blob_id(admission.blob_id))
        except BlobNotFoundError:
            return "canonical_object_missing"
        except BlobIntegrityError:
            return "storage_integrity_error"
        if not published.sha256:
            return "object_unverifiable"
        if published.sha256 != admission.declared_sha256 or published.size != admission.declared_size_bytes:
            return "storage_integrity_error"
        if published.media_type != admission.media_type:
            return "media_type_conflict"
        return None

    # -- settling one try ---------------------------------------------------------------

    def _reject(self, admission: Admission, failure: str) -> DispatchStep:
        with session_scope(self._factory) as session:
            current = _repository.lock(session, admission.admission_id)
            if current is None or current.state is not AdmissionState.PENDING:
                return DispatchStep(admission.admission_id, DispatchResult.SETTLED_ELSEWHERE)
            return self._reject_in(session, current, failure)

    def _reject_in(self, session: Session, admission: Admission, failure: str) -> DispatchStep:
        """Reject the admission, never the Blob row: the bytes' identity is shared."""
        _repository.reject(session, admission, failure)
        _repository.append_event(
            session,
            event_type="norm_custody.rejected",
            aggregate_type=_ADMISSION_AGGREGATE,
            aggregate_id=admission.admission_id,
            payload={"state": AdmissionState.REJECTED.value, "failure": failure},
        )
        return DispatchStep(admission.admission_id, DispatchResult.REJECTED, failure)

    def _failed_try(self, admission: Admission, failure: str) -> DispatchStep:
        with session_scope(self._factory) as session:
            current = _repository.lock(session, admission.admission_id)
            if current is None or current.state is not AdmissionState.PENDING:
                return DispatchStep(admission.admission_id, DispatchResult.SETTLED_ELSEWHERE)
            state = _repository.record_failed_try(session, current, failure)
            poisoned = state is AdmissionState.POISONED
            _repository.append_event(
                session,
                event_type="norm_custody.poisoned" if poisoned else "norm_custody.try_failed",
                aggregate_type=_ADMISSION_AGGREGATE,
                aggregate_id=current.admission_id,
                payload={
                    "state": state.value,
                    "failure": failure,
                    "attempt_count": min(current.attempt_count + 1, MAX_ATTEMPTS),
                },
            )
        return DispatchStep(
            admission.admission_id,
            DispatchResult.POISONED if poisoned else DispatchResult.RETRY_SCHEDULED,
            failure,
        )

    def _reached(self, point: str) -> None:
        if self._checkpoint is not None:
            self._checkpoint(point)


class _Rejected(Exception):
    """An integrity failure of one admission's bytes. Internal to the dispatcher."""

    def __init__(self, failure: str) -> None:
        super().__init__(failure)
        self.failure = failure


def _declaration(admission: Admission) -> BlobDeclaration:
    return declare_blob(
        sha256=admission.declared_sha256,
        size=admission.declared_size_bytes,
        role=parse_blob_role(admission.role),
        media_type=admission.media_type,
    )


def _blob_row_refusal(record: BlobMetadataRecord | None, admission: Admission) -> str | None:
    if record is None:
        return None
    if record.state is BlobState.REJECTED:
        return D143_REASON
    if record.state not in (BlobState.TEMPORARY, BlobState.VERIFYING, BlobState.AVAILABLE):
        return "blob_not_publishable"
    if record.media_type != admission.media_type:
        return "media_type_conflict"
    if record.sha256 != admission.declared_sha256 or record.size_bytes != admission.declared_size_bytes:
        return "storage_integrity_error"
    return None


def _domain_failure(exc: DomainError) -> str:
    if exc.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED:
        # The only refused move of a declared, matching row is out of a terminal state.
        return D143_REASON
    if exc.code is ErrorCode.STORAGE_INTEGRITY_ERROR:
        return "storage_integrity_error"
    return exc.code.value


def _transient_failure(exc: Exception) -> str:
    if isinstance(exc, StorageError):
        return exc.code
    return "source_unavailable"


# --- phase two: binding publication -----------------------------------------------------


def publish_bindings(
    session: Session, role: str, targets: Sequence[str]
) -> BindingPublication:
    """``publish_bindings(role, target)`` (CD-19), in the transaction holding the targets.

    Locks every non-rejected admission of ``role`` for these targets, refuses before any
    write if a named target is absent now or an admission is not ``confirmed``, checks each
    Blob is ``available`` with the declared facts, then inserts one binding per admission
    with its ``norm_custody.bound`` event. An exact replay inserts nothing and reports the
    bindings as already bound. ``trg_norm_custody_binding_guard`` re-checks invariants 1-4.
    """
    shape = shape_of(role)
    target_ids = sorted({require_target(shape, target) for target in targets})
    if not target_ids:
        return BindingPublication(bound=(), already_bound=0)
    present = _repository.existing_targets(
        session, target_kind=shape.target_kind, target_ids=target_ids
    )
    if set(target_ids) - present:
        raise CustodyRefused(
            "target_absent",
            ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
            machine="norm_custody_binding",
            current_state="target_absent",
            requested_state="bound",
        )
    admissions = _repository.lock_for_targets(
        session, role=shape.role, target_kind=shape.target_kind, target_ids=target_ids
    )
    for admission in admissions:
        if admission.state is not AdmissionState.CONFIRMED:
            raise CustodyRefused(
                "admission_not_confirmed",
                ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
                machine="norm_custody_admission",
                current_state=admission.state.value,
                requested_state="bound",
            )
    facts = _repository.blob_facts(session, sorted({a.blob_id for a in admissions}))
    for admission in admissions:
        fact = facts.get(admission.blob_id)
        if fact is None or fact != (
            BlobState.AVAILABLE.value,
            admission.declared_sha256,
            admission.declared_size_bytes,
            admission.media_type,
        ):
            raise CustodyRefused(
                "blob_not_verified",
                ErrorCode.STORAGE_INTEGRITY_ERROR,
                blob_id=admission.blob_id,
                expected_sha256=admission.declared_sha256,
                role=admission.role,
            )
    bound = []
    already = 0
    for admission in admissions:
        binding = _repository.insert_binding(session, admission)
        if binding is None:
            already += 1
            continue
        _repository.append_event(
            session,
            event_type="norm_custody.bound",
            aggregate_type=_BINDING_AGGREGATE,
            aggregate_id=binding.binding_id,
            payload={
                "norm_custody_admission_id": binding.admission_id,
                "role": binding.role,
                "target_kind": binding.target_kind,
                "target_id": binding.target_id,
                "anchor_kind": binding.anchor_kind,
                "blob_id": binding.blob_id,
            },
        )
        bound.append(binding)
    return BindingPublication(bound=tuple(bound), already_bound=already)


# --- report and reconcile ---------------------------------------------------------------


def report(
    session: Session, *, role: str | None = None, targets: Sequence[str] | None = None
) -> CustodyReport:
    """``custody report``: read-only. Optionally scoped to one role and its targets.

    Lists poisoned and rejected admissions, confirmed admissions still unbound (a target
    that never arrived), the binding count and digest, and every ``rejected`` Blob row
    (`D-143`) with whether a custody admission names it. Never touches the object store.
    """
    if role is not None:
        shape_of(role)
    target_ids = None if targets is None else sorted(set(targets))
    bindings = _repository.bindings(session, role=role, target_ids=target_ids)
    return CustodyReport(
        counts=_repository.state_counts(session, role=role, target_ids=target_ids),
        poisoned=_repository.in_state(
            session, AdmissionState.POISONED, role=role, target_ids=target_ids
        ),
        rejected_admissions=_repository.in_state(
            session, AdmissionState.REJECTED, role=role, target_ids=target_ids
        ),
        unbound_confirmed=_repository.unbound_confirmed(
            session, role=role, target_ids=target_ids
        ),
        binding_count=len(bindings),
        binding_digest=binding_digest(
            BindingDigestEntry(
                role=binding.role,
                target_kind=binding.target_kind,
                target_id=binding.target_id,
                blob_id=binding.blob_id,
                anchor_kind=binding.anchor_kind,
                anchor=binding.anchor,
            )
            for binding in bindings
        ),
        rejected_blobs=_repository.rejected_blobs(session),
    )


class CustodyReconciler:
    """``custody reconcile``: point-inspect every confirmed admission's object. Read-only.

    A confirmed admission (bound or not) whose object is absent, unverifiable or recorded
    with other facts is a storage integrity incident: it is reported and fails closed, and
    no replacement identity is allocated. ``pending`` rows already due are listed for a
    re-drive. The store is never listed; an object no row names stays invisible here, as it
    must when the port has no ``list``.
    """

    __slots__ = ("_store", "_factory")

    def __init__(
        self, store: BlobStore, *, session_factory: sessionmaker[Session] | None = None
    ) -> None:
        self._store = store
        self._factory = session_factory

    def reconcile(self) -> CustodyReconciliation:
        with session_scope(self._factory) as session:
            rows = _repository.confirmed_with_binding(session)
            redrive = _repository.redrive_due(session)
        incidents: list[CustodyIncident] = []
        verdicts: dict[str, IncidentKind | None] = {}
        for admission_id, blob_id, sha256, size, media_type, binding_id, blob_state in rows:
            kind: IncidentKind | None
            if blob_state != BlobState.AVAILABLE.value:
                kind = IncidentKind.BLOB_ROW_NOT_AVAILABLE
            else:
                key = f"{blob_id}|{sha256}|{size}|{media_type}"
                if key not in verdicts:
                    verdicts[key] = self._inspect(str(blob_id), str(sha256), int(size), str(media_type))
                kind = verdicts[key]
            if kind is not None:
                incidents.append(
                    CustodyIncident(
                        kind=kind,
                        admission_id=str(admission_id),
                        binding_id=None if binding_id is None else str(binding_id),
                        blob_id=str(blob_id),
                    )
                )
        return CustodyReconciliation(
            incidents=tuple(incidents),
            redrive_due=redrive,
            checked_blobs=len({row[1] for row in rows}),
        )

    def _inspect(
        self, blob_id: str, sha256: str, size: int, media_type: str
    ) -> IncidentKind | None:
        try:
            published = self._store.inspect(parse_blob_id(blob_id))
        except BlobNotFoundError:
            return IncidentKind.OBJECT_MISSING
        except BlobIntegrityError:
            return IncidentKind.OBJECT_METADATA_DIFFERS
        if not published.sha256:
            return IncidentKind.OBJECT_UNVERIFIABLE
        if (
            published.sha256 != sha256
            or published.size != size
            or published.media_type != media_type
        ):
            return IncidentKind.OBJECT_METADATA_DIFFERS
        return None


def blob_id_for(sha256: str, size: int) -> str:
    """The content-derived ``blob_id`` an admission of these bytes will name."""
    return str(derive_blob_id(sha256=sha256.strip().lower(), size=size))


__all__ = [
    "ADMIT_COMMAND_TYPE",
    "Checkpoint",
    "CustodyDispatcher",
    "CustodyReconciler",
    "admit",
    "blob_id_for",
    "publish_bindings",
    "report",
    "requeue",
]
