"""The start-audit-run command: the one way an ``AuditRun`` comes into existence.

Idempotency runs through ``command_record`` and its ``UNIQUE (command_type,
idempotency_key)``. The claim/replay machinery is ``B1``'s
:class:`auditmanager.ingest.CommandRepository`, which is generic in ``command_type``;
this module supplies a different command type and reuses it rather than growing a
second implementation of the same table's rules. **There is no automatic retry here.**
P02 §3.5 is explicit that a retry which does not consult the command record writes
duplicates, and the record is the thing a retry consults.

The frozen-at-creation set
--------------------------
A run freezes what it will analyse *before* it runs: the document version, the blob set
taken from that version's immutable input manifest, the analysis profile, the prompt
bundle and the norms snapshot. The first four are the **input basis**
(:func:`input_basis_digest`), the computation every run before W55 stored. The stored
``frozen_input_digest`` is that basis plus the pinned snapshot when one is pinned
(:func:`frozen_input_digest`), so a later reader can tell whether two runs saw the same
inputs without trusting that nothing moved underneath them.

The norms snapshot (`W55A-PIN-01`; plan section A3.3; R-82, R-113, CD-6)
-------------------------------------------------------------------------
``start_audit_run`` and ``reaudit_run`` read the **current** norms snapshot through
``auditmanager.norms.public.current_snapshot`` inside the run-creating transaction, after
the command ledger has accepted the key, and write it to ``audit_run.norms_snapshot_id``.
The snapshot is database state, read in the transaction; profile, bundle and mode stay the
caller's configuration. While no snapshot is current the pin is NULL and the stored digest
is byte-identical to the basis. No stage reads the pin before W57, so a NULL pin is
admitted; :mod:`auditmanager.runs.scope` records that as the ``OD-24`` non-evaluation.

**Neither idempotency fingerprint holds the snapshot.** ``start_run_fingerprint`` takes the
basis, under the key it has always used, so a key accepted before W55 replays and a retry
after an administrator designated another snapshot replays the run the first acceptance
created rather than refusing as a different payload. The re-audit fingerprint stays the
source run and the source's stored digest.

The reference-resolution guard PC-01 *does* evaluate
----------------------------------------------------
``created -> queued`` requires the run's references to resolve. PC-01 evaluates three of
the four clauses and does it here, at creation, where the answer is still actionable:
the version must exist and carry a ``source.document`` manifest entry, and the analysis
profile and prompt bundle identities must be well-formed. A pinned snapshot resolves by
construction (it is the current one, and ``fk_audit_run_norms_snapshot`` holds it); a NULL
pin is admitted until W57.

Why the command succeeds at creation
------------------------------------
The command's outcome is *the run identity*, and that identity exists the moment the row
is inserted. Recording success there is what makes "the same key with the same payload
returns the existing run and creates nothing, **including for a terminal run**" true
uniformly, instead of true only once the run happens to have finished. Execution is a
separate call against a run that is already durable — which is also why run and stage
state are persisted before execution rather than after it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Final, Mapping

from sqlalchemy.orm import Session
from sqlalchemy import text

from auditmanager.documents.public import DocumentRepository
from auditmanager.norms.public import current_snapshot
from auditmanager.jobs.public import JobRepository
from auditmanager.ingest.public import (
    CommandReplay,
    CommandRepository,
    CommandStarted,
    payload_fingerprint,
)
from auditmanager.runs.repository import RunRepository, RunRow
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    AnalysisProfileId,
    IdempotencyKey,
    PayloadFingerprint,
    PromptBundleId,
    RunId,
    VersionUid,
)

#: Matches ``ck_command_record_command_type``: lowercase snake_case, 3-64 characters.
COMMAND_TYPE_START_RUN: Final[str] = "start_audit_run"

#: The manifest role whose bytes ``source_preparation`` consumes.
# Imported, not restated. This was the third spelling of one concept in three trees: the
# storage blob role `source_document`, this module's own copy of the contract's
# `source.document`, and what ingest actually wrote into the manifest - which was the blob
# spelling, so the real upload path could not start a run while every fixture could.
from auditmanager.documents.public import MANIFEST_ROLE_SOURCE_DOCUMENT

ROLE_SOURCE_DOCUMENT: Final[str] = MANIFEST_ROLE_SOURCE_DOCUMENT


@dataclass(frozen=True, slots=True)
class StartedRun:
    """What the command answers with.

    ``replayed`` is ``True`` when the key had already been used with this exact payload,
    in which case nothing was created and ``run_id`` names the original run.
    """

    run_id: str
    command_id: str
    replayed: bool


#: Reads the norms snapshot a run being created pins: its ``ns_`` identity, or ``None``
#: while no snapshot is current. Called inside the run-creating transaction.
NormsSnapshotReader = Callable[[Session], str | None]


def current_norms_snapshot(session: Session) -> str | None:
    """The current norms snapshot's identity, or ``None`` while none is current (CD-6).

    The one reader every run-creating command uses: ``norms.public.current_snapshot``,
    which takes no lock. A designation committed concurrently is either seen or not; the
    run pins whichever snapshot was current when this statement ran.
    """
    current = current_snapshot(session)
    return None if current is None else str(current.norms_snapshot_id)


def _frozen_document(
    *,
    version_uid: str,
    blob_ids: Mapping[str, str],
    analysis_profile_id: str,
    prompt_bundle_id: str,
) -> dict[str, Any]:
    return {
        "analysis_profile_id": analysis_profile_id,
        "blob_ids": dict(sorted(blob_ids.items())),
        "prompt_bundle_id": prompt_bundle_id,
        "version_uid": version_uid,
    }


def _sha256_of(document: Mapping[str, Any]) -> str:
    payload = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def input_basis_digest(
    *,
    version_uid: str,
    blob_ids: Mapping[str, str],
    analysis_profile_id: str,
    prompt_bundle_id: str,
) -> str:
    """sha256 over the canonical serialization of the input basis.

    Sorted keys and no insignificant whitespace, so the digest depends on the values
    and not on dict ordering. This is exactly the computation every run before W55
    stored as its ``frozen_input_digest``, and it **never** holds the norms snapshot:
    it is what ``start_run_fingerprint`` takes, so a designation can never turn a retry
    into a different payload.
    """
    return _sha256_of(
        _frozen_document(
            version_uid=version_uid,
            blob_ids=blob_ids,
            analysis_profile_id=analysis_profile_id,
            prompt_bundle_id=prompt_bundle_id,
        )
    )


def frozen_input_digest(
    *,
    version_uid: str,
    blob_ids: Mapping[str, str],
    analysis_profile_id: str,
    prompt_bundle_id: str,
    norms_snapshot_id: str | None,
) -> str:
    """The stored ``frozen_input_digest``: the input basis plus the pinned snapshot.

    The same canonical document as :func:`input_basis_digest`, with ``norms_snapshot_id``
    added when a snapshot is pinned. With none pinned the key is absent rather than null,
    so a NULL run's stored digest is **byte-identical** to its basis -- and to what the
    same run would have stored before W55. ``norms_snapshot_id`` has no default: a caller
    that forgot the pin would silently store a digest that claims none.
    """
    document = _frozen_document(
        version_uid=version_uid,
        blob_ids=blob_ids,
        analysis_profile_id=analysis_profile_id,
        prompt_bundle_id=prompt_bundle_id,
    )
    if norms_snapshot_id is not None:
        document["norms_snapshot_id"] = norms_snapshot_id
    return _sha256_of(document)


def start_run_fingerprint(
    *,
    version_uid: str,
    analysis_profile_id: str,
    prompt_bundle_id: str,
    provider_mode: str,
    input_basis_digest_value: str,
) -> PayloadFingerprint:
    """The comparison value that distinguishes a repeat from a same-key conflict.

    Public because it is the *rule*, not an implementation detail: a caller that needs
    to know whether two requests are the same payload must ask the same question this
    command asks, and a second derivation of it elsewhere would be a second place to be
    wrong. It covers everything the **request** decides about what the run analyses or
    how.

    It takes the input basis (:func:`input_basis_digest`), never the stored digest: the
    norms snapshot is database state the server reads, not part of the request, so a
    retry after a designation change is the same payload and replays. The basis is
    recorded under the key ``frozen_input_digest`` -- the name it has carried since
    before W55, when the basis *was* the stored digest -- so every key accepted then
    still produces the fingerprint its ``command_record`` holds.
    """
    return payload_fingerprint(
        {
            "analysis_profile_id": analysis_profile_id,
            "frozen_input_digest": input_basis_digest_value,
            "prompt_bundle_id": prompt_bundle_id,
            "provider_mode": provider_mode,
            "version_uid": version_uid,
        }
    )


def _resolve_references(
    session: Session,
    *,
    version_uid: VersionUid,
    analysis_profile_id: str,
    prompt_bundle_id: str,
    documents: DocumentRepository,
) -> tuple[Any, dict[str, str]]:
    """The three ``created -> queued`` guard clauses PC-01 evaluates.

    Evaluated at creation rather than at the transition, because a run whose references
    do not resolve should never have become a row. The fourth clause is the
    ``NormsSnapshot`` one: the snapshot is read later, after the ledger accepts the key,
    and a NULL pin is admitted until W57 (CD-6).
    """
    version = documents.get_version(session, version_uid)

    blob_ids = {entry.role: str(entry.blob_id) for entry in version.manifest}
    if ROLE_SOURCE_DOCUMENT not in blob_ids:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message=(
                "the document version's input manifest carries no source.document "
                "entry, so there is nothing for source_preparation to read"
            ),
            reason="missing_required_input",
        )

    # Well-formedness of the two pinned identities. ``parse`` raises at the boundary
    # rather than letting a mis-prefixed value become a row pointing at nothing.
    AnalysisProfileId.parse(analysis_profile_id)
    PromptBundleId.parse(prompt_bundle_id)

    return version, blob_ids


def start_audit_run(
    session: Session,
    *,
    version_uid: VersionUid | str,
    analysis_profile_id: str,
    prompt_bundle_id: str,
    provider_mode: str,
    idempotency_key: IdempotencyKey | str,
    commands: CommandRepository | None = None,
    runs: RunRepository | None = None,
    documents: DocumentRepository | None = None,
    norms_snapshot: NormsSnapshotReader = current_norms_snapshot,
) -> StartedRun:
    """Create one durable ``AuditRun``, or answer what already happened under this key.

    The caller owns the transaction. This function opens no engine, commits nothing and
    writes no rollback of its own. The norms snapshot the new run pins is read here, in
    that transaction, by ``norms_snapshot`` -- the current one, or NULL while none is
    current.

    Outcomes:

    * a **new key** creates the run and returns it with ``replayed=False``;
    * the **same key with the same payload** returns the original run with
      ``replayed=True`` and creates nothing, whatever state that run has since reached;
    * the **same key with a different payload** raises ``idempotency_key_reuse``;
    * a **new key over a terminal run** creates a new run and leaves the old row alone,
      which needs no special case here: nothing in this path reads the earlier run.
    """
    command_repo = commands or CommandRepository()
    run_repo = runs or RunRepository()
    document_repo = documents or DocumentRepository()

    resolved_version = (
        version_uid if isinstance(version_uid, VersionUid) else VersionUid.parse(version_uid)
    )
    key = (
        idempotency_key
        if isinstance(idempotency_key, IdempotencyKey)
        else IdempotencyKey(idempotency_key)
    )

    _version, blob_ids = _resolve_references(
        session,
        version_uid=resolved_version,
        analysis_profile_id=analysis_profile_id,
        prompt_bundle_id=prompt_bundle_id,
        documents=document_repo,
    )

    basis = input_basis_digest(
        version_uid=str(resolved_version),
        blob_ids=blob_ids,
        analysis_profile_id=analysis_profile_id,
        prompt_bundle_id=prompt_bundle_id,
    )

    # Two requests differing in any of it are different payloads, so a client that
    # reuses a key after changing the profile learns about it rather than silently
    # receiving the first run back. The norms snapshot is not in it: it is not the
    # request's, and a retry after a designation change must replay.
    fingerprint = start_run_fingerprint(
        version_uid=str(resolved_version),
        analysis_profile_id=analysis_profile_id,
        prompt_bundle_id=prompt_bundle_id,
        provider_mode=provider_mode,
        input_basis_digest_value=basis,
    )

    claimed = command_repo.begin(
        session,
        command_type=COMMAND_TYPE_START_RUN,
        idempotency_key=key,
        fingerprint=fingerprint,
    )

    if isinstance(claimed, CommandReplay):
        run_id = claimed.outcome.get("run_id")
        if not isinstance(run_id, str):
            # The record succeeded without naming a run. Nothing can establish what it
            # created, which is exactly what the stale code means.
            raise DomainError(
                ErrorCode.IDEMPOTENCY_KEY_STALE, command_type=COMMAND_TYPE_START_RUN
            )
        return StartedRun(
            run_id=run_id, command_id=str(claimed.command_id), replayed=True
        )

    assert isinstance(claimed, CommandStarted)
    # `W55A-PIN-01`. Read only once the key is this caller's: a replay pins nothing new.
    snapshot = norms_snapshot(session)
    run_id = RunId.new().value
    run_repo.create(
        session,
        run_id=run_id,
        project_uid=str(_version.project_uid),
        version_uid=str(resolved_version),
        analysis_profile_id=analysis_profile_id,
        prompt_bundle_id=prompt_bundle_id,
        provider_mode=provider_mode,
        frozen_input_digest=frozen_input_digest(
            version_uid=str(resolved_version),
            blob_ids=blob_ids,
            analysis_profile_id=analysis_profile_id,
            prompt_bundle_id=prompt_bundle_id,
            norms_snapshot_id=snapshot,
        ),
        command_id=str(claimed.command_id),
        norms_snapshot_id=snapshot,
    )
    command_repo.succeed(session, claimed.command_id, {"run_id": run_id})
    return StartedRun(
        run_id=run_id, command_id=str(claimed.command_id), replayed=False
    )


def run_of_command(
    session: Session,
    *,
    idempotency_key: IdempotencyKey | str,
    commands: CommandRepository | None = None,
) -> RunRow | None:
    """The run a key created, or ``None`` when the key has not been used.

    A read, for callers that want to know before they ask for one to be created.
    """
    command_repo = commands or CommandRepository()
    key = (
        idempotency_key
        if isinstance(idempotency_key, IdempotencyKey)
        else IdempotencyKey(idempotency_key)
    )
    record = command_repo.find(
        session, command_type=COMMAND_TYPE_START_RUN, idempotency_key=key
    )
    if record is None or not record.outcome:
        return None
    run_id = record.outcome.get("run_id")
    if not isinstance(run_id, str):
        return None
    return RunRepository().find(session, run_id)


_TERMINAL_RUN_STATES = frozenset({"published", "partial", "failed", "cancelled"})
_CANCELLABLE_RUN_STATES = frozenset({"created", "queued", "running"})


def _require_run_control_role(roles: frozenset[str]) -> None:
    if not roles.intersection({"expert", "admin"}):
        raise DomainError(ErrorCode.PERMISSION_DENIED)


def cancel_audit_run(
    session: Session, *, run_id: str, roles: frozenset[str], idempotency_key: str,
    runs: RunRepository | None = None, jobs: JobRepository | None = None,
    commands: CommandRepository | None = None,
) -> str:
    """Idempotently fence a runnable run, its Job, Attempt and Lease."""
    _require_run_control_role(roles)
    repository = runs or RunRepository()
    ledger = commands or CommandRepository()
    # One run row is locked before anything else the command changes.
    session.execute(text(
        "SELECT run_id FROM audit_run WHERE run_id = :run_id FOR UPDATE"
    ), {"run_id": run_id}).scalar_one_or_none()
    source = repository.get(session, run_id)
    claimed = ledger.begin(
        session, command_type="cancel_audit_run",
        idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint({"run_id": run_id}),
    )
    if isinstance(claimed, CommandReplay):
        return run_id
    assert isinstance(claimed, CommandStarted)
    if source.state not in _CANCELLABLE_RUN_STATES:
        raise DomainError(
            ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
            machine="audit_run", current_state=source.state, requested_state="cancelled",
        )
    (jobs or JobRepository()).cancel_for_run(session, run_id=run_id)
    repository.terminate(session, run_id=run_id, from_state=source.state, to_state="cancelled")
    ledger.succeed(session, claimed.command_id, {"run_id": run_id})
    return run_id


def reaudit_run(
    session: Session, *, source_run_id: str, roles: frozenset[str],
    idempotency_key: str, analysis_profile_id: str, prompt_bundle_id: str,
    provider_mode: str, runs: RunRepository | None = None,
    jobs: JobRepository | None = None, commands: CommandRepository | None = None,
    documents: DocumentRepository | None = None,
    norms_snapshot: NormsSnapshotReader = current_norms_snapshot,
) -> StartedRun:
    """Create one new run of a terminal source's document version, on today's configuration.

    `R-82`: a re-audit is the same document version analysed on the **current** analysis
    profile, prompt bundle and provider mode. The caller passes the configuration the
    deployment executes (the same values ``start_run`` stamps); the new run records
    those, and a ``frozen_input_digest`` computed from them by the same guard and digest
    ``start_audit_run`` uses. The source is linked only by ``reaudit_of_run_id``.

    `W55A-PIN-01` (R-82, R-113, CD-6): the new run pins the **current** norms snapshot,
    read in this transaction exactly as ``start_audit_run`` reads it, never the source's.
    It is NULL while none is current, whatever the source pinned.

    The idempotency fingerprint is still the request -- the source run and its stored
    digest -- because the configuration and the snapshot are the server's, not the
    caller's. The source row never changes, so a retry after a designation change replays.
    """
    _require_run_control_role(roles)
    repository = runs or RunRepository()
    ledger = commands or CommandRepository()
    session.execute(text(
        "SELECT run_id FROM audit_run WHERE run_id = :run_id FOR UPDATE"
    ), {"run_id": source_run_id}).scalar_one_or_none()
    source = repository.get(session, source_run_id)
    claimed = ledger.begin(
        session, command_type="reaudit_run",
        idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint({
            "reaudit_of_run_id": source_run_id,
            "frozen_input_digest": source.frozen_input_digest,
        }),
    )
    if isinstance(claimed, CommandReplay):
        replay_run_id = claimed.outcome.get("run_id")
        if not isinstance(replay_run_id, str):
            raise DomainError(ErrorCode.IDEMPOTENCY_KEY_STALE, command_type="reaudit_run")
        return StartedRun(replay_run_id, str(claimed.command_id), True)
    assert isinstance(claimed, CommandStarted)
    if source.state not in _TERMINAL_RUN_STATES:
        raise DomainError(
            ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
            machine="audit_run", current_state=source.state, requested_state="reaudit",
        )
    busy = session.execute(text(
        "SELECT 1 FROM audit_run WHERE reaudit_of_run_id = :source "
        "AND state NOT IN ('published', 'partial', 'failed', 'cancelled') LIMIT 1"
    ), {"source": source_run_id}).scalar_one_or_none()
    if busy is not None:
        raise DomainError(ErrorCode.CONFLICT, message="a re-audit of this source is in progress")
    version_uid = VersionUid.parse(source.version_uid)
    _version, blob_ids = _resolve_references(
        session,
        version_uid=version_uid,
        analysis_profile_id=analysis_profile_id,
        prompt_bundle_id=prompt_bundle_id,
        documents=documents or DocumentRepository(),
    )
    snapshot = norms_snapshot(session)
    digest = frozen_input_digest(
        version_uid=str(version_uid),
        blob_ids=blob_ids,
        analysis_profile_id=analysis_profile_id,
        prompt_bundle_id=prompt_bundle_id,
        norms_snapshot_id=snapshot,
    )
    new_id = str(RunId.new())
    repository.create(
        session, run_id=new_id, project_uid=source.project_uid,
        version_uid=source.version_uid,
        analysis_profile_id=analysis_profile_id,
        prompt_bundle_id=prompt_bundle_id,
        provider_mode=provider_mode,
        frozen_input_digest=digest,
        command_id=str(claimed.command_id), reaudit_of_run_id=source_run_id,
        norms_snapshot_id=snapshot,
    )
    repository.advance(session, run_id=new_id, from_state="created", to_state="queued")
    (jobs or JobRepository()).enqueue(session, run_id=new_id)
    ledger.succeed(session, claimed.command_id, {"run_id": new_id})
    return StartedRun(new_id, str(claimed.command_id), False)


__all__ = [
    "COMMAND_TYPE_START_RUN",
    "NormsSnapshotReader",
    "ROLE_SOURCE_DOCUMENT",
    "StartedRun",
    "current_norms_snapshot",
    "frozen_input_digest",
    "input_basis_digest",
    "run_of_command",
    "cancel_audit_run",
    "reaudit_run",
    "start_audit_run",
    "start_run_fingerprint",
]
