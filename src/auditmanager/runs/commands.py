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

The analysis input budget (`W55B-BUDGET-01`; plan section B3.3, G-11, R-118)
------------------------------------------------------------------------------
``start_audit_run`` and ``reaudit_run`` refuse a version whose recorded
``text_character_count`` is **above** ``input_budget_characters`` with
``analysis_input_budget_exceeded`` (``422``; ``character_count`` and ``budget_characters``).
A count exactly at the budget is accepted, and a version with **no** recorded count (published
before the portal-bundle upload) is not refused by this rule. A re-audit runs on the current
configuration (R-82), so it is checked against the budget in force now, never the source run's.

**Where the refusal sits.** After the version is read and *before* the idempotency key is
claimed, so a refusal leaves no ``command_record``, run, job or event behind -- it is not a
recorded outcome. That is the point: the budget is an operator setting, so a retry of the same
key after the operator raised the ceiling is a **fresh start**, not a replay of a stored
refusal. The one exception is a key that already exists: it is left to the ledger, which
replays the run that key created (or answers ``idempotency_key_reuse`` or ``..._in_progress``).
A client retrying an accepted start must be told what happened, not that the version it
already started has become too large for today's configuration.

**Windows (`SECTION-CHUNKED-ANALYSIS-01`).** ``input_budget_characters`` is the budget of **one model
call**. A section run above it is analysed in whole-page windows of at most that size, so these two
commands (not the AR v3 group, which keeps the one-call refusal) refuse a count above
``MAX_ANALYSIS_WINDOWS`` windows' worth, ``input_budget_characters * MAX_ANALYSIS_WINDOWS``, and the
refusal's ``budget_characters`` is that figure. A count not above the one-call budget is the run it always
was. The stage refuses, before any call, a text that packs into more windows than the limit.

``input_budget_characters`` is a keyword that defaults to ``None`` so the many callers that
predate the budget stay untouched. ``None`` means *no configuration* and is reachable only
from tests: the served application derives the budget once at start-up and always passes it
(``bootstrap/settings.py``, ``RunAdapter``; held by
``tests/integration/composition/test_the_served_application_always_passes_a_budget.py``).

Section routing (`W59-SECTION-SEAL-01`; `W59-SECTION-IDENTITY-DECISION-01`)
-----------------------------------------------------------------------------
The served application passes ``section_profiles`` -- the sealed section-to-profile table the
composition root loaded from the text-profile registry -- and **no** profile or bundle of its
own. ``start_audit_run`` and ``reaudit_run`` then read the version's **persisted**
classification (``0024_version_classification``) in the run-creating transaction and route
through :func:`auditmanager.sections.public.route_classified_version`: an unclassified
version is ``version_classification_required``, a confirmed section with no registered
profile ``section_profile_unavailable`` (`BETA-CONTRACT-SEAL-01`, `D-179`; both used to be
``required_norm_unavailable`` told apart by ``reference_kind``). There is no AR fallback: a
suggestion, a file name and the legacy ``document.section`` never reach this decision. Like the budget refusal, routing is
decided after the version is read and **before** the key is claimed, so a refusal writes
nothing; a key the ledger already knows replays the run it created, whose pinned profile is
read back for the fingerprint rather than re-routed -- an existing run keeps its profile.

An in-process caller (the integration suites, the offline harnesses) may still name a
profile and bundle explicitly and pass no table; that is a caller choosing a profile, not a
fallback, and the served path never takes it
(``tests/integration/composition/test_the_served_application_routes_by_section.py``).
Passing both, or neither, is a wiring fault and raises ``ValueError``.

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

from auditmanager.analysis.public import MAX_ANALYSIS_WINDOWS, windowed_budget_characters
from auditmanager.documents.public import DocumentRepository
from auditmanager.norms.public import current_snapshot
from auditmanager.jobs.public import JobRepository, append_execution_event
from auditmanager.ingest.public import (
    CommandReplay,
    CommandRepository,
    CommandStarted,
    payload_fingerprint,
)
from auditmanager.runs.provider import FrozenRoute, RouteFreezer
from auditmanager.runs.repository import EXECUTOR_CHOSEN_EVENT, RunRepository, RunRow
from auditmanager.sections.public import route_classified_version
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
    norm_retrieval_set_sha256: str | None = None,
    ar_v3_group_id: str | None = None,
    ar_v3_scope_id: str | None = None,
    ar_v3_map_sha256: str | None = None,
    ar_v3_set_id: str | None = None,
) -> str:
    """The stored ``frozen_input_digest``: the input basis plus the pinned snapshot.

    The same canonical document as :func:`input_basis_digest`, with ``norms_snapshot_id``
    added when a snapshot is pinned. With none pinned the key is absent rather than null,
    so a NULL run's stored digest is **byte-identical** to its basis -- and to what the
    same run would have stored before W55. ``norms_snapshot_id`` has no default: a caller
    that forgot the pin would silently store a digest that claims none. A
    future v3 caller may also pass the verified retrieval-set digest; existing
    v1/v2 calls leave it absent and retain their exact stored bytes.
    """
    document = _frozen_document(
        version_uid=version_uid,
        blob_ids=blob_ids,
        analysis_profile_id=analysis_profile_id,
        prompt_bundle_id=prompt_bundle_id,
    )
    if norms_snapshot_id is not None:
        document["norms_snapshot_id"] = norms_snapshot_id
    if norm_retrieval_set_sha256 is not None:
        if norms_snapshot_id is None:
            raise ValueError("a retrieval set digest requires a snapshot pin")
        if not isinstance(norm_retrieval_set_sha256, str) or len(norm_retrieval_set_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in norm_retrieval_set_sha256
        ):
            raise ValueError("retrieval set digest must be lowercase SHA-256")
        document["norm_retrieval_set_sha256"] = norm_retrieval_set_sha256
    group_fields = (ar_v3_group_id, ar_v3_scope_id, ar_v3_map_sha256, ar_v3_set_id)
    if any(value is not None for value in group_fields):
        if any(value is None for value in group_fields) or norm_retrieval_set_sha256 is None:
            raise ValueError("an AR v3 group digest requires all four group pins and set digest")
        from auditmanager.shared.identity import ArV3RunGroupId, NormRetrievalSetId

        ArV3RunGroupId.parse(ar_v3_group_id)
        NormRetrievalSetId.parse(ar_v3_set_id)
        if ar_v3_scope_id not in ("F1", "F2", "A1", "A2", "S1", "S2"):
            raise ValueError("invalid AR v3 scope")
        if len(ar_v3_map_sha256) != 64 or any(c not in "0123456789abcdef" for c in ar_v3_map_sha256):
            raise ValueError("invalid AR v3 map digest")
        document["ar_v3_group_id"] = ar_v3_group_id
        document["ar_v3_scope_id"] = ar_v3_scope_id
        document["ar_v3_map_sha256"] = ar_v3_map_sha256
        document["ar_v3_set_id"] = ar_v3_set_id
    return _sha256_of(document)


def start_run_fingerprint(
    *,
    version_uid: str,
    analysis_profile_id: str,
    prompt_bundle_id: str,
    provider_mode: str,
    input_basis_digest_value: str,
    executor_connection_id: str | None = None,
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

    ``executor_connection_id`` (`EXEC-PAR-START-01`) is the executor the caller **named**. It is
    part of the request, so the same key with another executor is a different payload
    (``idempotency_key_reuse``), not a replay. It is added to the document only when named: an
    absent choice leaves the fingerprint byte-for-byte what it was, so every key accepted before
    this field existed still replays.
    """
    document: dict[str, Any] = {
        "analysis_profile_id": analysis_profile_id,
        "frozen_input_digest": input_basis_digest_value,
        "prompt_bundle_id": prompt_bundle_id,
        "provider_mode": provider_mode,
        "version_uid": version_uid,
    }
    if executor_connection_id is not None:
        document["executor_connection_id"] = executor_connection_id
    return payload_fingerprint(document)


#: The sealed section → ``(analysis_profile_id, prompt_bundle_id)`` table run start routes
#: through (`W59-SECTION-SEAL-01`), loaded once by the composition root.
SectionProfiles = Mapping[str, tuple[str, str]]


def _explicit_or_routed(
    analysis_profile_id: str | None,
    prompt_bundle_id: str | None,
    section_profiles: SectionProfiles | None,
) -> None:
    """Exactly one profile source: an explicit pair (in-process callers) or the table."""
    explicit = analysis_profile_id is not None or prompt_bundle_id is not None
    if section_profiles is not None and explicit:
        raise ValueError(
            "a routed run start takes its profile from the section table; an explicit "
            "profile or bundle beside it is a wiring fault"
        )
    if section_profiles is None and (analysis_profile_id is None or prompt_bundle_id is None):
        raise ValueError(
            "a run start needs either the section profile table or an explicit profile "
            "and bundle; there is no default profile"
        )


def _pinned_profile(
    session: Session, run_id: object, runs: RunRepository
) -> tuple[str, str] | None:
    """The profile pair a run already pinned, or ``None`` when the outcome names no run."""
    if not isinstance(run_id, str):
        return None
    pinned = runs.find(session, run_id)
    if pinned is None:
        return None
    return pinned.analysis_profile_id, pinned.prompt_bundle_id


def _resolve_references(
    session: Session,
    *,
    version_uid: VersionUid,
    analysis_profile_id: str,
    prompt_bundle_id: str,
    documents: DocumentRepository,
    version: Any | None = None,
) -> tuple[Any, dict[str, str]]:
    """The three ``created -> queued`` guard clauses PC-01 evaluates.

    Evaluated at creation rather than at the transition, because a run whose references
    do not resolve should never have become a row. The fourth clause is the
    ``NormsSnapshot`` one: the snapshot is read later, after the ledger accepts the key,
    and a NULL pin is admitted until W57 (CD-6). ``version`` is the record a caller has
    already read in this transaction, so it is not read twice.
    """
    if version is None:
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


def _checked_budget(input_budget_characters: int | None) -> int | None:
    """The budget argument, or the refusal of one that cannot be a budget.

    ``None`` is "no configuration" (tests only). Anything else must be a whole number of
    characters, zero or more: a negative or fractional budget handed in by a caller is a wiring
    fault, and treating it as "no budget" would be the silent fallback this check exists to
    prevent.
    """
    if input_budget_characters is None:
        return None
    if (
        isinstance(input_budget_characters, bool)
        or not isinstance(input_budget_characters, int)
        or input_budget_characters < 0
    ):
        raise ValueError("input_budget_characters must be a non-negative whole number or None")
    return input_budget_characters


def _refuse_over_budget(
    character_count: int | None, input_budget_characters: int | None
) -> None:
    """``analysis_input_budget_exceeded`` when the version's text is above the budget.

    Strictly above: a count equal to the budget is accepted. ``None`` on either side is
    accepted -- no budget configured (tests), or a version published before the bundle upload
    that recorded no count -- and is never read as zero.
    """
    if input_budget_characters is None or character_count is None:
        return
    if character_count > input_budget_characters:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_BUDGET_EXCEEDED,
            character_count=int(character_count),
            budget_characters=int(input_budget_characters),
        )


def _refuse_over_window_budget(
    character_count: int | None, input_budget_characters: int | None
) -> None:
    """``analysis_input_budget_exceeded`` when the version's text is above ``MAX_ANALYSIS_WINDOWS`` windows.

    The section runs' counterpart of :func:`_refuse_over_budget`: ``input_budget_characters`` is the
    budget of one call, a window is never larger, and the limit is that many windows. Strictly above is
    refused (a count exactly at the limit is accepted); ``None`` on either side is accepted, as there.
    ``budget_characters`` in the refusal is the limit, so the two integers the client sees are the version's
    count and the most a run takes.
    """
    if input_budget_characters is None or character_count is None:
        return
    limit = windowed_budget_characters(input_budget_characters, MAX_ANALYSIS_WINDOWS)
    if character_count > limit:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_BUDGET_EXCEEDED,
            character_count=int(character_count),
            budget_characters=int(limit),
        )


def _chosen_executor_unserved() -> DomainError:
    """A named executor and no freezer to honour it (the ``environment`` source, or a bare
    wiring): refused, because running the work on the process's own adapter instead would be the
    silent fallback an explicit choice forbids."""
    return DomainError(
        ErrorCode.DEPENDENCY_UNAVAILABLE,
        message="this deployment does not serve a chosen executor connection",
        dependency="executor_connection",
    )


def _freeze_for(
    session: Session, connection_route: RouteFreezer, connection_id: str | None
) -> FrozenRoute:
    """Freeze through the seam: the route when no connection was named (called exactly as it
    always was), else the named connection. A freezer that answers any other connection than the
    one asked for is a wiring fault and nothing is written."""
    if connection_id is None:
        return connection_route(session)
    frozen = connection_route(session, connection_id=connection_id)
    if frozen.chosen_connection_id != connection_id:
        raise ValueError("the route freezer did not freeze the connection that was named")
    return frozen


def start_audit_run(
    session: Session,
    *,
    version_uid: VersionUid | str,
    analysis_profile_id: str | None = None,
    prompt_bundle_id: str | None = None,
    provider_mode: str,
    idempotency_key: IdempotencyKey | str,
    commands: CommandRepository | None = None,
    runs: RunRepository | None = None,
    documents: DocumentRepository | None = None,
    norms_snapshot: NormsSnapshotReader = current_norms_snapshot,
    input_budget_characters: int | None = None,
    section_profiles: SectionProfiles | None = None,
    connection_route: RouteFreezer | None = None,
    executor_connection_id: str | None = None,
) -> StartedRun:
    """Create one durable ``AuditRun``, or answer what already happened under this key.

    The caller owns the transaction. This function opens no engine, commits nothing and
    writes no rollback of its own. The norms snapshot the new run pins is read here, in
    that transaction, by ``norms_snapshot`` -- the current one, or NULL while none is
    current.

    ``input_budget_characters`` is the analysis input budget in force (`W55B-BUDGET-01`; see
    the module docstring). A version whose recorded character count is above it is refused
    with ``analysis_input_budget_exceeded`` **before** the key is claimed, so nothing is
    written. ``None`` means "no configuration" and is reachable only from tests: the served
    application always passes the budget it derived at start-up.

    Outcomes:

    * a **new key** creates the run and returns it with ``replayed=False``;
    * the **same key with the same payload** returns the original run with
      ``replayed=True`` and creates nothing, whatever state that run has since reached;
    * the **same key with a different payload** raises ``idempotency_key_reuse``;
    * a **new key over a terminal run** creates a new run and leaves the old row alone,
      which needs no special case here: nothing in this path reads the earlier run.

    ``section_profiles`` (`W59-SECTION-SEAL-01`): when given, the profile and bundle are
    routed from the version's persisted classification and ``analysis_profile_id`` /
    ``prompt_bundle_id`` must be omitted; see the module docstring.

    ``connection_route`` (`EXEC-HTTP-01`): with the provider source ``database`` the freezer
    resolves the ``text_analysis`` route to a connection revision in this transaction, **for a
    new key only**; the revision is written to the run, which freezes it, and the input budget
    is the one that follows that revision's pinned model, replacing ``input_budget_characters``.
    A route with nothing usable is refused here as ``dependency_unavailable``
    (``executor_route_missing``) before the key is claimed, so nothing is written. A standby chosen
    in place of the primary is journaled once the run exists.

    ``executor_connection_id`` (`EXEC-PAR-START-01`): the connection the caller **named**. The
    freezer then freezes that connection's current revision instead of the route's, and the start
    is refused -- before the key is claimed, so nothing is written -- when the connection is
    unknown, archived, not served, or not probed ``ok``; it never becomes the standby or another
    connection. The choice is part of the idempotency fingerprint and is journaled once the run
    exists (``audit_run.executor_chosen``). Absent, the start is what it always was.
    """
    _explicit_or_routed(analysis_profile_id, prompt_bundle_id, section_profiles)
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

    budget = _checked_budget(input_budget_characters)

    version_record = document_repo.get_version(session, resolved_version)
    # Read only when a pre-claim decision needs it (the budget or the route), exactly as the
    # budget alone read it before this seal.
    known = (
        command_repo.find(session, command_type=COMMAND_TYPE_START_RUN, idempotency_key=key)
        if budget is not None or section_profiles is not None or connection_route is not None
        or executor_connection_id is not None
        else None
    )
    if section_profiles is not None:
        # `W59-SECTION-SEAL-01`. A known key is answered by the ledger below with the
        # profile its run pinned; only a new key is routed, and a refusal writes nothing.
        pinned = None if known is None else _pinned_profile(
            session, (known.outcome or {}).get("run_id"), run_repo
        )
        if pinned is None:
            routed = route_classified_version(version_record, section_profiles)
            pinned = (routed.analysis_profile_id, routed.prompt_bundle_id)
        analysis_profile_id, prompt_bundle_id = pinned
    assert analysis_profile_id is not None and prompt_bundle_id is not None

    _version, blob_ids = _resolve_references(
        session,
        version_uid=resolved_version,
        analysis_profile_id=analysis_profile_id,
        prompt_bundle_id=prompt_bundle_id,
        documents=document_repo,
        version=version_record,
    )

    # `W55B-BUDGET-01`. Up front: after the version is read, before the key is claimed, so a
    # refusal writes no command record and a retry after the operator raises the ceiling is a
    # fresh start. A key the ledger already knows is not refused here -- it is answered below,
    # as a replay, whatever today's budget is.
    frozen: FrozenRoute | None = None
    if executor_connection_id is not None and connection_route is None and known is None:
        raise _chosen_executor_unserved()
    if connection_route is not None and known is None:
        frozen = _freeze_for(session, connection_route, executor_connection_id)
        budget = frozen.input_budget_characters
    if budget is not None and known is None:
        _refuse_over_window_budget(_version.text_character_count, budget)

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
        executor_connection_id=executor_connection_id,
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
        connection_revision_id=None if frozen is None else frozen.revision_id,
    )
    _journal_standby(session, run_id, frozen)
    _journal_executor_choice(session, run_id, frozen)
    command_repo.succeed(session, claimed.command_id, {"run_id": run_id})
    return StartedRun(
        run_id=run_id, command_id=str(claimed.command_id), replayed=False
    )


def _journal_standby(session: Session, run_id: str, frozen: FrozenRoute | None) -> None:
    """A standby used instead of the primary is an event of the run (plan section 2): there is
    no implicit fallback, so every use leaves a record beside the run's frozen revision."""
    if frozen is None or frozen.standby_reason is None:
        return
    append_execution_event(
        session, event_type="audit_run.standby_used", aggregate_type="AuditRun",
        aggregate_id=run_id, run_id=run_id,
        payload={
            "revision_id": frozen.revision_id,
            "primary_connection_id": frozen.primary_connection_id,
            "standby_connection_id": frozen.standby_connection_id,
            "reason": frozen.standby_reason,
        },
    )


def _journal_executor_choice(session: Session, run_id: str, frozen: FrozenRoute | None) -> None:
    """A connection the caller named is an event of the run, beside its frozen revision: the run
    row alone cannot tell a named executor from a routed one, and a repeat must keep the former
    (`EXEC-PAR-START-01`). Identities only; the connection's name, address and key never enter."""
    if frozen is None or frozen.chosen_connection_id is None:
        return
    append_execution_event(
        session, event_type=EXECUTOR_CHOSEN_EVENT, aggregate_type="AuditRun",
        aggregate_id=run_id, run_id=run_id,
        payload={
            "connection_id": frozen.chosen_connection_id,
            "revision_id": frozen.revision_id,
        },
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
    idempotency_key: str, analysis_profile_id: str | None = None,
    prompt_bundle_id: str | None = None,
    provider_mode: str, runs: RunRepository | None = None,
    jobs: JobRepository | None = None, commands: CommandRepository | None = None,
    documents: DocumentRepository | None = None,
    norms_snapshot: NormsSnapshotReader = current_norms_snapshot,
    input_budget_characters: int | None = None,
    section_profiles: SectionProfiles | None = None,
    connection_route: RouteFreezer | None = None,
) -> StartedRun:
    """Create one new run of a terminal source's document version, on today's configuration.

    ``connection_route`` (`EXEC-HTTP-01`) freezes the connection revision of the new run exactly
    as ``start_audit_run`` does, on today's route, for a new key only.

    `EXEC-PAR-START-01`: a source whose executor was **named** at its start (it carries an
    ``audit_run.executor_chosen`` event) is repeated on that same connection -- its current
    revision -- and not on today's route. If that connection can no longer serve, the repeat is
    refused before the key is claimed; it is never redirected to the route, the standby or another
    connection. The new run journals the same choice, so its own repeat keeps it too.

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

    `W55B-BUDGET-01`: the source's version is checked against ``input_budget_characters``,
    the budget in force **now** -- a re-audit runs on the current configuration, so it faces
    today's budget and not the one the source run was accepted under. The refusal precedes
    the key's claim (see the module docstring), and a key the ledger already knows replays.
    ``None`` means "no configuration" and is reachable only from tests.

    `W59-SECTION-SEAL-01`: with ``section_profiles`` the new run is routed from the
    version's persisted classification **now** -- never from the source run's profile --
    and an unclassified version or a section without a registered profile is refused before
    the key is claimed. A known key replays whatever it created.
    """
    _require_run_control_role(roles)
    _explicit_or_routed(analysis_profile_id, prompt_bundle_id, section_profiles)
    budget = _checked_budget(input_budget_characters)
    repository = runs or RunRepository()
    ledger = commands or CommandRepository()
    document_repo = documents or DocumentRepository()
    session.execute(text(
        "SELECT run_id FROM audit_run WHERE run_id = :run_id FOR UPDATE"
    ), {"run_id": source_run_id}).scalar_one_or_none()
    source = repository.get(session, source_run_id)
    source_version = None
    frozen: FrozenRoute | None = None
    if (section_profiles is not None or budget is not None or connection_route is not None) and ledger.find(
        session, command_type="reaudit_run", idempotency_key=IdempotencyKey(idempotency_key)
    ) is None:
        source_version = document_repo.get_version(session, VersionUid.parse(source.version_uid))
        if section_profiles is not None:
            routed = route_classified_version(source_version, section_profiles)
            analysis_profile_id = routed.analysis_profile_id
            prompt_bundle_id = routed.prompt_bundle_id
        chosen_connection_id = repository.chosen_executor_connection(session, source_run_id)
        if chosen_connection_id is not None and connection_route is None:
            raise _chosen_executor_unserved()
        if connection_route is not None:
            frozen = _freeze_for(session, connection_route, chosen_connection_id)
            budget = frozen.input_budget_characters
        if budget is not None:
            _refuse_over_window_budget(source_version.text_character_count, budget)
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
    if section_profiles is not None and analysis_profile_id is None:
        # Defensive: ``find`` reported the key known, so routing was deferred to the
        # ledger's replay, and yet this request claimed it. Route now, before any write.
        routed = route_classified_version(
            source_version or document_repo.get_version(session, version_uid),
            section_profiles,
        )
        analysis_profile_id = routed.analysis_profile_id
        prompt_bundle_id = routed.prompt_bundle_id
    assert analysis_profile_id is not None and prompt_bundle_id is not None
    _version, blob_ids = _resolve_references(
        session,
        version_uid=version_uid,
        analysis_profile_id=analysis_profile_id,
        prompt_bundle_id=prompt_bundle_id,
        documents=document_repo,
        version=source_version,
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
        connection_revision_id=None if frozen is None else frozen.revision_id,
    )
    _journal_standby(session, new_id, frozen)
    _journal_executor_choice(session, new_id, frozen)
    repository.advance(session, run_id=new_id, from_state="created", to_state="queued")
    (jobs or JobRepository()).enqueue(session, run_id=new_id)
    ledger.succeed(session, claimed.command_id, {"run_id": new_id})
    return StartedRun(new_id, str(claimed.command_id), False)


__all__ = [
    "COMMAND_TYPE_START_RUN",
    "NormsSnapshotReader",
    "SectionProfiles",
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
