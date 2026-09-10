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
taken from that version's immutable input manifest, the analysis profile and the prompt
bundle. Those four go into ``frozen_input_digest``, so a later reader can tell whether
two runs saw the same inputs without trusting that nothing moved underneath them. The
norms snapshot stays NULL and is read by no PC-01 path — see
:mod:`auditmanager.runs.scope` for why that is a recorded ``OD-24`` non-evaluation
rather than an oversight.

The reference-resolution guard PC-01 *does* evaluate
----------------------------------------------------
``created -> queued`` requires the run's references to resolve. PC-01 evaluates three of
the four clauses and does it here, at creation, where the answer is still actionable:
the version must exist and carry a ``source.document`` manifest entry, and the analysis
profile and prompt bundle identities must be well-formed. The fourth clause, the
``NormsSnapshot`` one, has nothing to resolve.

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
from typing import Any, Final, Mapping

from sqlalchemy.orm import Session

from auditmanager.documents import DocumentRepository
from auditmanager.ingest import (
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
    PromptBundleId,
    RunId,
    VersionUid,
)

#: Matches ``ck_command_record_command_type``: lowercase snake_case, 3-64 characters.
COMMAND_TYPE_START_RUN: Final[str] = "start_audit_run"

#: The manifest role whose bytes ``source_preparation`` consumes.
ROLE_SOURCE_DOCUMENT: Final[str] = "source.document"


@dataclass(frozen=True, slots=True)
class StartedRun:
    """What the command answers with.

    ``replayed`` is ``True`` when the key had already been used with this exact payload,
    in which case nothing was created and ``run_id`` names the original run.
    """

    run_id: str
    command_id: str
    replayed: bool


def frozen_input_digest(
    *,
    version_uid: str,
    blob_ids: Mapping[str, str],
    analysis_profile_id: str,
    prompt_bundle_id: str,
) -> str:
    """sha256 over the canonical serialization of the frozen-at-creation set.

    Sorted keys and no insignificant whitespace, so the digest depends on the values
    and not on dict ordering. ``norms_snapshot_id`` is deliberately absent: including a
    field that is always NULL would suggest PC-01 pins one.
    """
    document = {
        "analysis_profile_id": analysis_profile_id,
        "blob_ids": dict(sorted(blob_ids.items())),
        "prompt_bundle_id": prompt_bundle_id,
        "version_uid": version_uid,
    }
    payload = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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
    ``NormsSnapshot`` one and there is nothing to resolve for it.
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
) -> StartedRun:
    """Create one durable ``AuditRun``, or answer what already happened under this key.

    The caller owns the transaction. This function opens no engine, commits nothing and
    writes no rollback of its own.

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

    digest = frozen_input_digest(
        version_uid=str(resolved_version),
        blob_ids=blob_ids,
        analysis_profile_id=analysis_profile_id,
        prompt_bundle_id=prompt_bundle_id,
    )

    # The fingerprint covers everything that would change what the run analyses or how.
    # Two requests differing in any of it are different payloads, so a client that
    # reuses a key after changing the profile learns about it rather than silently
    # receiving the first run back.
    fingerprint = payload_fingerprint(
        {
            "analysis_profile_id": analysis_profile_id,
            "frozen_input_digest": digest,
            "prompt_bundle_id": prompt_bundle_id,
            "provider_mode": provider_mode,
            "version_uid": str(resolved_version),
        }
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
    run_id = RunId.new().value
    run_repo.create(
        session,
        run_id=run_id,
        project_uid=str(_version.project_uid),
        version_uid=str(resolved_version),
        analysis_profile_id=analysis_profile_id,
        prompt_bundle_id=prompt_bundle_id,
        provider_mode=provider_mode,
        frozen_input_digest=digest,
        command_id=str(claimed.command_id),
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


__all__ = [
    "COMMAND_TYPE_START_RUN",
    "ROLE_SOURCE_DOCUMENT",
    "StartedRun",
    "frozen_input_digest",
    "run_of_command",
    "start_audit_run",
]
