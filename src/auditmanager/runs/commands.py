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
commands refuse a count above
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

Admission on a group or by a rule (`EXEC2-GROUP-RUN-01`; ADR-0026 decisions 12 and 13)
---------------------------------------------------------------------------------------
A start that names ``executor_group_id`` -- or that names nothing while the routing mode is ``rules`` -- is **admitted**,
not frozen: the run records the immutable group revision (and the rule revision when a rule routed it) and
``binding_state = 'pending'``, and **no connection revision**. The claim binds a member, once, at dispatch. The
estimate, the budget and the consent follow the group revision's pin; ``RunCostConsent`` works as for any start, against
an estimate that carries the group and no connection, and the consent snapshot stays in this command's outcome.

Exclusivity and the refusals precede the key's claim, so nothing is written: a group together with an executor
connection or a preset is ``validation_failed`` on ``executor_group_id``; the ``environment`` source (no admitter) refuses a
group; an unknown group, an archived group and a work kind with no rule are the admitter's typed refusals. An
explicit connection and a preset are untouched by the routing mode: they stay ``frozen_at_start`` exactly as before, and a
start that names nothing while the mode is ``legacy`` follows the route exactly as before.

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

from auditmanager.analysis.public import (
    MAX_ANALYSIS_WINDOWS, relaxed_profile_pair, relaxed_window_characters,
    windowed_budget_characters,
)
from auditmanager.documents.public import MANIFEST_ROLE_COMPARISON_PDF, UPLOAD_KIND_COMPARISON_PDF, DocumentRepository
from auditmanager.norms.public import current_snapshot
from auditmanager.jobs.public import JobRepository, append_execution_event
from auditmanager.ingest.public import (
    CommandReplay,
    CommandRepository,
    CommandStarted,
    payload_fingerprint,
)
from auditmanager.runs.provider import (
    AdmittedGroup,
    ChosenPreset,
    FrozenRoute,
    GroupAdmitter,
    PresetResolver,
    RouteFreezer,
)
from auditmanager.runs.repository import EXECUTOR_CHOSEN_EVENT, RunRepository, RunRow
from auditmanager.runs.stage_layout import FrozenStagePlan
from auditmanager.runs.stage_plan import StagePlanDraft, StagePlanSource
from auditmanager.runs.stage_reuse import plan_stage_reuse, require_startable_stage, visual_only_pages_allowed
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

#: `R-151i`: a new run that reuses the completed stage outputs of an earlier one before the chosen stage.
COMMAND_TYPE_START_RUN_FROM_STAGE: Final[str] = "start_run_from_stage"

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
) -> str:
    """The stored ``frozen_input_digest``: the input basis plus the pinned snapshot.

    The same canonical document as :func:`input_basis_digest`, with ``norms_snapshot_id``
    added when a snapshot is pinned. With none pinned the key is absent rather than null,
    so a NULL run's stored digest is **byte-identical** to its basis -- and to what the
    same run would have stored before W55. ``norms_snapshot_id`` has no default: a caller
    that forgot the pin would silently store a digest that claims none. A
    caller that pinned a verified retrieval set may also pass its digest; existing
    calls leave it absent and retain their exact stored bytes.
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
    return _sha256_of(document)


def start_run_fingerprint(
    *,
    version_uid: str,
    analysis_profile_id: str,
    prompt_bundle_id: str,
    provider_mode: str,
    input_basis_digest_value: str,
    executor_connection_id: str | None = None,
    preset_id: str | None = None,
    relaxed_limits: bool = False,
    cost_consent: Mapping[str, Any] | None = None,
    executor_group_id: str | None = None,
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

    ``preset_id`` (`ANALYSIS-PRESETS-01`) is the preset the caller **named**; it is part of the
    request in the same way and added to the document only when named. A start through a preset
    carries the preset and **not** the executor connection the preset resolved to: the request is
    "this preset", so a retry after an administrator revised the preset is the same payload and
    replays the run that exists, while the same key with a hand-chosen executor, or with another
    preset, is ``idempotency_key_reuse``.

    ``executor_group_id`` (`EXEC2-GROUP-RUN-01`) is the group the caller **named**, added to the document only when
    named. The group, not the member the claim will choose, is the request: a retry after the group was revised
    replays the run that exists. A start that names nothing -- routed by a rule or by the route -- adds nothing, so
    every key accepted before this field existed still replays.
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
    if preset_id is not None:
        document["preset_id"] = preset_id
    if executor_group_id is not None:
        document["executor_group_id"] = executor_group_id
    if relaxed_limits:
        document["relaxed_limits"] = True
    if cost_consent is not None:
        document["cost_consent"] = dict(cost_consent)
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


#: Legacy refusal for operations that still require portal structure (the AR six-check group).
COMPARISON_ONLY_VERSION_REASON: Final[str] = "comparison_only_version"


def refuse_comparison_only_version(version: Any) -> None:
    """Refuse a portal-only operation on a version that has no portal bundle.

    The legacy six-check AR group still needs portal blocks. Ordinary section runs
    can instead prepare native PDF text and page visuals from ``comparison.source_pdf``.
    """
    if getattr(version, "upload_kind", None) == UPLOAD_KIND_COMPARISON_PDF:
        raise DomainError(
            ErrorCode.ANALYSIS_INPUT_INVALID,
            message="this operation requires the portal bundle's structured inputs",
            reason=COMPARISON_ONLY_VERSION_REASON,
        )


def analysis_source_entry(version: Any) -> Any:
    """Select the PDF manifest entry for an ordinary run without changing the stored manifest."""
    role = (MANIFEST_ROLE_COMPARISON_PDF if getattr(version, "upload_kind", None) == UPLOAD_KIND_COMPARISON_PDF
            else ROLE_SOURCE_DOCUMENT)
    entry = next((item for item in version.manifest if item.role == role), None)
    if entry is None:
        raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, reason="missing_required_input")
    return entry


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
    blob_ids[ROLE_SOURCE_DOCUMENT] = str(analysis_source_entry(version).blob_id)

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


def refuse_group_conflicts(
    executor_group_id: str | None, executor_connection_id: str | None, preset_id: str | None,
) -> None:
    """A group is a third way to choose the same thing: exclusive with a connection and with a preset
    (`EXEC2-GROUP-RUN-01`; ``validation_failed`` on ``executor_group_id`` with ``conflicts_with_executor_connection_id``
    or ``conflicts_with_preset_id``). Precedes everything that reads a row or claims a key."""
    if executor_group_id is None:
        return
    if executor_connection_id is not None:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="a group and an executor connection are two ways to choose the same thing",
            field="executor_group_id", constraint="conflicts_with_executor_connection_id",
        )
    if preset_id is not None:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="a group and a preset are two ways to choose the same thing",
            field="executor_group_id", constraint="conflicts_with_preset_id",
        )


def admit_group_for_start(
    session: Session, group_admitter: GroupAdmitter | None, *, executor_group_id: str | None,
    executor_connection_id: str | None, preset_id: str | None,
) -> AdmittedGroup | None:
    """The group a start is admitted on, or ``None`` when the executor is frozen at start as it always was.

    Decision 13 and the rollback rule in one place, shared by the estimate and the start:

    * a named connection or preset is never admitted by a group, whatever the routing mode says;
    * a named group is admitted in either mode, and needs an admitter -- the ``environment`` source has none and
      refuses (``validation_failed``, ``environment_source``), because it runs no group work;
    * a start that names nothing is admitted by the rule only while the mode is ``rules``; the admitter answers
      ``None`` while it is ``legacy``, and a deployment with no admitter has no rules to apply.
    """
    refuse_group_conflicts(executor_group_id, executor_connection_id, preset_id)
    if executor_connection_id is not None or preset_id is not None:
        return None
    if group_admitter is None:
        if executor_group_id is not None:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message="the environment provider source runs no executor group work",
                field="executor_group_id", constraint="environment_source",
            )
        return None
    return group_admitter(session, group_id=executor_group_id)


def refuse_selectors_under_layout(
    *, executor_connection_id: str | None, preset_id: str | None, executor_group_id: str | None,
) -> None:
    """`HOSTS-LAYOUT-01` (ADR-0028 decision 14): while the stage layout is on, the models of a run are the layout's and the servers are
    the stand's. A start that names a connection, a preset or a group is ``validation_failed`` on that field
    (``constraint: stage_layout_enabled``), before the key is claimed, so nothing is written; it is never read as absent."""
    for field, value in (
        ("executor_connection_id", executor_connection_id), ("preset_id", preset_id), ("executor_group_id", executor_group_id),
    ):
        if value is not None:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message="the stage layout chooses the models of a run; a start names no executor, preset or group",
                field=field, constraint="stage_layout_enabled",
            )


def _planned_columns(plan: FrozenStagePlan | None) -> dict[str, Any]:
    """What ``RunRepository.create`` is told of a run frozen with a stage plan: ``pending`` (every cell is bound at dispatch), the plan,
    and -- by the omission of the group, connection and preset -- the fourth shape of ``ck_audit_run_binding_shape``."""
    if plan is None:
        return {}
    return {"binding_state": "pending", "stage_plan": plan.to_json()}


def _journal_stage_plan(session: Session, run_id: str, plan: FrozenStagePlan | None) -> None:
    """A run frozen with a plan is an event of the run beside its row. Identities and classifiers only: the layout revision it froze and
    the set; the models are in the row."""
    if plan is None:
        return
    append_execution_event(
        session, event_type="audit_run.stage_plan_frozen", aggregate_type="AuditRun",
        aggregate_id=run_id, run_id=run_id,
        payload={"revision_id": plan.layout_revision_id, "state": "pending", "reason": plan.kit},
    )


def _planned_estimate_kwargs(planned: StagePlanDraft | None, stage_plans: StagePlanSource | None) -> dict[str, Any]:
    """The estimate is told of the layout when the command asked about it: the draft while it is on, ``None`` while it is off (so the
    estimate does not ask again and cannot disagree with the command). With no seam at all a preflight that predates the layout is
    called exactly as before."""
    return {} if stage_plans is None else {"stage_plan": planned}


def _plan_of(estimate: Any, planned: StagePlanDraft | None) -> FrozenStagePlan | None:
    """The plan an estimate froze. A layout was on and the estimate returned none: refused (the consent would hold no plan)."""
    if planned is None:
        return None
    plan = getattr(estimate, "stage_plan", None)
    if not isinstance(plan, FrozenStagePlan):
        raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="analysis_cost_preflight")
    return plan


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
    preset_id: str | None = None,
    preset_resolver: PresetResolver | None = None,
    relaxed_limits: bool = False,
    text_profiles: Any = None,
    operational_model_id: str | None = None,
    cost_preflight: Any = None,
    cost_consent: Mapping[str, Any] | None = None,
    cost_actor_uid: str | None = None,
    executor_group_id: str | None = None,
    group_admitter: GroupAdmitter | None = None,
    started_by_user_uid: str | None = None,
    stage_plans: StagePlanSource | None = None,
) -> StartedRun:
    """Create one durable ``AuditRun``, or answer what already happened under this key.

    ``stage_plans`` (`HOSTS-LAYOUT-01`, ADR-0028 decisions 5, 8 and 14) is the seam that reads the stage layout when a run **starts**. For a
    new key it answers ``None`` while the layout is off -- the start is then exactly what it was -- or the draft of the layout in force.
    With a draft the run is frozen with a ``stage_plan``: the cost preflight prices it by model and the consent v2 is held against it,
    the run is written ``pending`` with the plan and no connection, group or preset, and every cell is bound at dispatch. A start that
    also names a connection, a preset or a group is ``validation_failed`` (:func:`refuse_selectors_under_layout`), and a layout with no
    cost preflight is ``dependency_unavailable``: a planned run is never started without the consent that binds its models.

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

    ``preset_id`` and ``preset_resolver`` (`ANALYSIS-PRESETS-01`): the preset the caller **named**.
    For a new key the resolver reads the preset's current revision in this transaction and the start
    **is** the start of a hand-chosen executor -- the preset's connection is handed to the freezer
    as ``executor_connection_id``, with the same usability test, the same refusals, the same frozen
    revision, budget, event and job -- and the run row additionally records the preset revision. An
    unknown or archived preset is refused before the key is claimed, so nothing is written. A preset
    together with ``executor_connection_id`` is ``validation_failed`` on ``preset_id``: a person
    either takes a preset or names an executor. A known key is answered before the preset is read
    (the replay of a run that exists), as for the executor. See :func:`start_run_fingerprint`.

    ``executor_group_id`` and ``group_admitter`` (`EXEC2-GROUP-RUN-01`): the group the caller **named**, and the seam
    that admits a start on a group or by the routing rules (see the module docstring). For a new key the run is
    admitted -- ``binding_state = 'pending'``, the group revision and, when a rule routed it, the rule revision -- and
    freezes **no connection**; the budget and the estimate follow the group revision's pin. A group together with a
    connection or a preset is ``validation_failed`` on ``executor_group_id``, and every refusal precedes the key's claim.
    """
    if type(relaxed_limits) is not bool:
        raise ValueError("relaxed_limits must be a boolean")
    if relaxed_limits and section_profiles is None:
        raise ValueError("relaxed_limits requires the section profile registry")
    if preset_id is not None and executor_connection_id is not None:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="a preset and an executor connection are two ways to choose the same thing",
            field="preset_id", constraint="conflicts_with_executor_connection_id",
        )
    refuse_group_conflicts(executor_group_id, executor_connection_id, preset_id)
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
        or executor_connection_id is not None or preset_id is not None or cost_preflight is not None or cost_consent is not None
        or executor_group_id is not None or group_admitter is not None or stage_plans is not None
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
        standard_pair = pinned
        if known is None and relaxed_limits:
            analysis_profile_id, prompt_bundle_id = relaxed_profile_pair(
                analysis_profile_id, prompt_bundle_id
            )
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
    chosen_preset: ChosenPreset | None = None
    admitted: AdmittedGroup | None = None
    approved_cost = None
    planned: StagePlanDraft | None = None
    stage_plan: FrozenStagePlan | None = None
    if known is None and stage_plans is not None:
        # `HOSTS-LAYOUT-01`: the switch is read here, in the run-creating transaction, and nowhere else.
        planned = stage_plans(session)
        if planned is not None:
            refuse_selectors_under_layout(
                executor_connection_id=executor_connection_id, preset_id=preset_id, executor_group_id=executor_group_id)
            if cost_preflight is None:
                raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="analysis_cost_preflight")
    if known is None and cost_preflight is not None:
        estimate = cost_preflight.estimate_run(session, version_uid=str(resolved_version),
            executor_connection_id=executor_connection_id, preset_id=preset_id, relaxed_limits=relaxed_limits,
            version_record=version_record, parse_native_text=False,
            **({"executor_group_id": executor_group_id} if executor_group_id is not None else {}),
            **_planned_estimate_kwargs(planned, stage_plans))
        approved_cost = estimate.approve(None if cost_consent is None else dict(cost_consent), actor_user_uid=cost_actor_uid)
        frozen, chosen_preset = estimate.frozen_route, estimate.chosen_preset
        admitted = getattr(estimate, "admitted_group", None)
        stage_plan = _plan_of(estimate, planned)
        budget = approved_cost["window_characters"]
    elif known is None and cost_consent is not None:
        raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="analysis_cost_preflight")
    elif known is None:
        # `EXEC2-GROUP-RUN-01`: with no cost preflight the start asks the admitter itself. A named group, or the
        # rule of the work kind while the mode is `rules`, admits the run and freezes no connection; the budget follows
        # the group revision's pin. `None` (a connection, a preset, mode `legacy`) leaves the start as it always was.
        admitted = admit_group_for_start(
            session, group_admitter, executor_group_id=executor_group_id,
            executor_connection_id=executor_connection_id, preset_id=preset_id,
        )
        if admitted is not None:
            budget = admitted.input_budget_characters
    if preset_id is not None and known is None and approved_cost is None:
        # `ANALYSIS-PRESETS-01`. Before the freezer: the preset only fills the field a person could
        # fill by hand, and everything after this line is the hand-chosen executor's start.
        if preset_resolver is None:
            raise _chosen_executor_unserved()
        chosen_preset = preset_resolver(session, preset_id)
        if chosen_preset.preset_id != preset_id:
            raise ValueError("the preset resolver did not resolve the preset that was named")
        executor_connection_id = chosen_preset.executor_connection_id
    if executor_connection_id is not None and connection_route is None and known is None:
        raise _chosen_executor_unserved()
    if connection_route is not None and known is None and approved_cost is None and admitted is None:
        frozen = _freeze_for(session, connection_route, executor_connection_id)
        budget = frozen.input_budget_characters
    if relaxed_limits and known is None and approved_cost is None:
        model_id = (
            admitted.pin_id if admitted is not None
            else frozen.model_id if frozen is not None else operational_model_id
        )
        if model_id is None or text_profiles is None:
            raise ValueError("relaxed section start needs a pinned model and profile resolver")
        resolve = text_profiles.resolve if hasattr(text_profiles, "resolve") else text_profiles
        normal_profile = resolve(*standard_pair)
        budget = relaxed_window_characters(model_id, normal_profile.prompt_bundle)
    # Even with monetary halts disabled, 12 whole-page windows remain the worker's
    # watchdog-bound execution envelope. Refuse before claiming the key.
    if budget is not None and known is None and approved_cost is None:
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
        # A start through a preset carries the preset and not the connection it resolved to.
        executor_connection_id=None if preset_id is not None else executor_connection_id,
        preset_id=preset_id,
        relaxed_limits=relaxed_limits,
        cost_consent=cost_consent,
        executor_group_id=executor_group_id,
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
        preset_revision_id=None if chosen_preset is None else chosen_preset.revision_id,
        started_by_user_uid=started_by_user_uid,  # `R-151v`
        **_admission_columns(admitted),
        **_planned_columns(stage_plan),
    )
    _journal_standby(session, run_id, frozen)
    _journal_executor_choice(session, run_id, frozen)
    _journal_admission(session, run_id, admitted)
    _journal_stage_plan(session, run_id, stage_plan)
    command_repo.succeed(session, claimed.command_id, {
        "run_id": run_id, **({"relaxed_limits": True} if relaxed_limits else {}),
        **({"cost_consent": approved_cost} if approved_cost is not None else {}),
    })
    return StartedRun(
        run_id=run_id, command_id=str(claimed.command_id), replayed=False
    )


def _admission_columns(admitted: AdmittedGroup | None) -> dict[str, Any]:
    """What ``RunRepository.create`` is told of an admission: nothing for a run whose executor is frozen at start."""
    if admitted is None:
        return {}
    return {
        "binding_state": "pending",
        "executor_group_revision_id": admitted.group_revision_id,
        "routing_rule_revision_id": admitted.rule_revision_id,
    }


def _journal_admission(session: Session, run_id: str, admitted: AdmittedGroup | None) -> None:
    """A run admitted on a group is an event of the run beside its row (`EXEC2-GROUP-RUN-01`): ``reason`` is
    ``rule`` when the routing rule chose the group and ``group`` when the caller named it. The group's identity is on
    the run row; the journal carries classifiers only."""
    if admitted is None:
        return
    append_execution_event(
        session, event_type="audit_run.group_admitted", aggregate_type="AuditRun",
        aggregate_id=run_id, run_id=run_id,
        payload={"work_kind": "text_analysis", "state": "pending",
                 "reason": "group" if admitted.rule_revision_id is None else "rule"},
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


#: `RUN-DELETE-01`: the runs an expert may delete from the run lists -- the ones that ended without a published result. A
#: ``published`` run is the result of the audit and is never deleted; a run that has not ended is cancelled first.
_DELETABLE_RUN_STATES = frozenset({"partial", "failed", "cancelled"})


def delete_audit_run(
    session: Session, *, run_id: str, roles: frozenset[str], user_uid: str, idempotency_key: str,
    runs: RunRepository | None = None, commands: CommandRepository | None = None,
) -> str:
    """Idempotently remove a ``partial``, ``failed`` or ``cancelled`` run from every list of runs (owner hotfix 2026-11-11).

    A **tombstone**, never a deletion of data: one immutable ``audit_run_deletion`` row. The run, its stage results, findings,
    expert decisions and Blobs stay stored and ``getRunStatus`` still answers it by its identity. There is no restore.

    An unknown run, and a run that already has a tombstone, are ``not_found`` -- the run is no longer there for a list or for a
    second delete; a repeat of the *same* keyed call replays the first answer, whatever has become of the run since. A run in
    any other state is ``state_transition_not_allowed``: a ``published`` run is the result of the audit, and one that has not
    ended must be cancelled first (``cancelRun``). Nothing is written when the call is refused, and a refused call leaves no
    command record (the transaction ends with the refusal), exactly as ``cancel_audit_run``.
    """
    _require_run_control_role(roles)
    repository = runs or RunRepository()
    ledger = commands or CommandRepository()
    # One run row is locked before anything else the command changes: two deletes of one run, and a delete beside a re-audit
    # that names the run as its source, take turns.
    session.execute(text(
        "SELECT run_id FROM audit_run WHERE run_id = :run_id FOR UPDATE"
    ), {"run_id": run_id}).scalar_one_or_none()
    source = repository.get(session, run_id)
    claimed = ledger.begin(
        session, command_type="delete_audit_run",
        idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint({"run_id": run_id}),
    )
    if isinstance(claimed, CommandReplay):
        return run_id
    assert isinstance(claimed, CommandStarted)
    if repository.is_deleted(session, run_id):
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="AuditRun")
    if source.state not in _DELETABLE_RUN_STATES:
        raise DomainError(
            ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
            machine="audit_run", current_state=source.state, requested_state="delete",
        )
    repository.record_deletion(session, run_id=run_id, user_uid=user_uid, command_id=str(claimed.command_id))
    ledger.succeed(session, claimed.command_id, {"run_id": run_id})
    return run_id


def _named_group_of(
    session: Session, source: RunRow, chosen_connection_id: str | None, group_admitter: GroupAdmitter | None,
) -> str | None:
    """The group a source run's start **named**, or ``None`` when it named none (`EXEC2-GROUP-RUN-01`).

    A run admitted by a group carries its group revision; one of them carries a rule revision too exactly when the rule
    chose the group, and that start named nothing. A source admitted on a named group with no admitter to read the
    group back through is a wiring fault and refuses (``environment_source``) rather than re-auditing on another
    executor."""
    group_revision_id = getattr(source, "executor_group_revision_id", None)
    if (getattr(source, "binding_state", "frozen_at_start") == "frozen_at_start"
            or getattr(source, "routing_rule_revision_id", None) is not None
            or chosen_connection_id is not None or group_revision_id is None):
        return None
    if group_admitter is None:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="the environment provider source runs no executor group work",
            field="executor_group_id", constraint="environment_source",
        )
    group_id = group_admitter.group_of(session, group_revision_id)
    if group_id is None:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, message="the executor group is not acceptable",
            field="executor_group_id", constraint="unknown_executor_group",
        )
    return group_id


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
    cost_preflight: Any = None,
    cost_consent: Mapping[str, Any] | None = None,
    cost_actor_uid: str | None = None,
    group_admitter: GroupAdmitter | None = None,
    started_by_user_uid: str | None = None,
    stage_plans: StagePlanSource | None = None,
) -> StartedRun:
    """Create one new run of a terminal source's document version, on today's configuration.

    `HOSTS-LAYOUT-01`: with ``stage_plans`` answering a draft (the stage layout is on) the new run takes **today's** plan, whatever the
    source ran on: the executor, group or preset its start named are not carried over, and the consent is v2 over the layout's models.
    With the layout off, or no seam, the re-audit is exactly what it was.

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

    `EXEC2-GROUP-RUN-01`: a re-audit keeps the **kind** of selector the original start used. A named connection stays
    that connection (above). A source that was admitted on a **named group** (``pending`` or ``bound``, no rule
    revision) is admitted again on that group's *current* revision; a source routed by a **rule** names nothing, so the
    re-audit follows today's configuration exactly as a start that names nothing does -- the current rule while the
    mode is ``rules``, the route while it is ``legacy``. Never a silent fallback: a group that was archived since
    refuses the re-audit (``group_archived``) and the new run is not written.

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
    source_version = document_repo.get_version(session, VersionUid.parse(source.version_uid))
    frozen: FrozenRoute | None = None
    admitted: AdmittedGroup | None = None
    approved_cost = None
    planned: StagePlanDraft | None = None
    stage_plan: FrozenStagePlan | None = None
    if (section_profiles is not None or budget is not None or connection_route is not None
            or cost_preflight is not None or cost_consent is not None
            or group_admitter is not None or stage_plans is not None) and ledger.find(
        session, command_type="reaudit_run", idempotency_key=IdempotencyKey(idempotency_key)
    ) is None:
        if section_profiles is not None:
            routed = route_classified_version(source_version, section_profiles)
            analysis_profile_id = routed.analysis_profile_id
            prompt_bundle_id = routed.prompt_bundle_id
        planned = None if stage_plans is None else stage_plans(session)
        if planned is not None and cost_preflight is None:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="analysis_cost_preflight")
        # Under the layout the source's named connection is not carried over: the stand chooses the servers.
        chosen_connection_id = None if planned is not None else repository.chosen_executor_connection(session, source_run_id)
        if chosen_connection_id is not None and connection_route is None:
            raise _chosen_executor_unserved()
        if cost_preflight is not None:
            estimate = cost_preflight.estimate_reaudit(session, run_id=source_run_id, version_record=source_version,
                parse_native_text=False, **_planned_estimate_kwargs(planned, stage_plans))
            approved_cost = estimate.approve(None if cost_consent is None else dict(cost_consent), actor_user_uid=cost_actor_uid)
            frozen = estimate.frozen_route
            admitted = getattr(estimate, "admitted_group", None)
            stage_plan = _plan_of(estimate, planned)
            budget = approved_cost["window_characters"]
        elif cost_consent is not None:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="analysis_cost_preflight")
        else:
            admitted = admit_group_for_start(
                session, group_admitter,
                # The group the original start named, if it named one (admitted by a group, no rule routed it).
                executor_group_id=_named_group_of(session, source, chosen_connection_id, group_admitter),
                executor_connection_id=chosen_connection_id, preset_id=None,
            )
            if admitted is not None:
                budget = admitted.input_budget_characters
            elif connection_route is not None:
                frozen = _freeze_for(session, connection_route, chosen_connection_id)
                budget = frozen.input_budget_characters
        if budget is not None and approved_cost is None:
            _refuse_over_window_budget(source_version.text_character_count, budget)
    claimed = ledger.begin(
        session, command_type="reaudit_run",
        idempotency_key=IdempotencyKey(idempotency_key),
        fingerprint=payload_fingerprint({
            "reaudit_of_run_id": source_run_id,
            "frozen_input_digest": source.frozen_input_digest,
            **({"cost_consent": dict(cost_consent)} if cost_consent is not None else {}),
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
        started_by_user_uid=started_by_user_uid,  # `R-151v`
        **_admission_columns(admitted),
        **_planned_columns(stage_plan),
    )
    _journal_standby(session, new_id, frozen)
    _journal_executor_choice(session, new_id, frozen)
    _journal_admission(session, new_id, admitted)
    _journal_stage_plan(session, new_id, stage_plan)
    repository.advance(session, run_id=new_id, from_state="created", to_state="queued")
    (jobs or JobRepository()).enqueue(session, run_id=new_id)
    ledger.succeed(session, claimed.command_id, {"run_id": new_id,
        **({"cost_consent": approved_cost} if approved_cost is not None else {})})
    return StartedRun(new_id, str(claimed.command_id), False)


def start_run_from_stage(
    session: Session, *, source_run_id: str, start_stage_id: str, roles: frozenset[str],
    idempotency_key: str, analysis_profile_id: str | None = None,
    prompt_bundle_id: str | None = None,
    provider_mode: str, runs: RunRepository | None = None,
    jobs: JobRepository | None = None, commands: CommandRepository | None = None,
    documents: DocumentRepository | None = None,
    norms_snapshot: NormsSnapshotReader = current_norms_snapshot,
    input_budget_characters: int | None = None,
    section_profiles: SectionProfiles | None = None,
    connection_route: RouteFreezer | None = None,
    cost_preflight: Any = None,
    cost_consent: Mapping[str, Any] | None = None,
    cost_actor_uid: str | None = None,
    group_admitter: GroupAdmitter | None = None,
    started_by_user_uid: str | None = None,
    stage_plans: StagePlanSource | None = None,
) -> StartedRun:
    """Create one new run of a terminal source's document version that reuses the source's stage outputs before ``start_stage_id``.

    `HOSTS-LAYOUT-01`: with ``stage_plans`` answering a draft the new run takes **today's** plan, as a re-audit does. The stages it
    reuses are the PC-01 stages before the chosen one -- the preparation stages, which run no model -- and ``text_analysis`` is always
    computed, so a model's work is never reused under another plan.

    `R-151i` (`UI-A-60`, `D-301`; ``docs/program/RUN-FROM-STAGE-01.md``). The new run is a **new** aggregate: the source is
    never changed and is linked only by ``started_from_run_id`` and ``start_stage_id`` (migration 0060), not by
    ``reaudit_of_run_id`` -- a re-audit recomputes everything and this does not. The configuration is today's, exactly as
    for ``reaudit_run`` (`R-82`, `W55A-PIN-01`, `W59-SECTION-SEAL-01`, `EXEC-PAR-START-01`, `EXEC2-GROUP-RUN-01`,
    `W55B-BUDGET-01`): the stages it reuses read none of it, and ``text_analysis``, which does, is always computed.

    The reuse is decided by :func:`~auditmanager.runs.stage_reuse.plan_stage_reuse` before the key is claimed, so a refusal
    (``analysis_input_invalid`` with ``stage_id`` and ``reason``) writes nothing; the executor decides it again when it
    materialises the reuse. Only the stages from ``start_stage_id`` are priced: with a cost preflight the estimate and the
    consent are those of the remaining stages and bound to this source and stage.

    **The idempotency key** is the caller's ``Idempotency-Key``, as for every run start; the fingerprint is the request --
    the source run, the chosen stage, the source's stored digest and the cost consent -- so the same key with another stage
    is ``idempotency_key_reuse`` and a retry replays the run the first acceptance created. Two different keys for the same
    source and stage are two decisions, but not two in flight: while a run from this source and stage has not ended, a
    second is ``conflict`` (as a second re-audit of one source is).
    """
    _require_run_control_role(roles)
    start_stage_id = require_startable_stage(start_stage_id)
    _explicit_or_routed(analysis_profile_id, prompt_bundle_id, section_profiles)
    budget = _checked_budget(input_budget_characters)
    repository = runs or RunRepository()
    ledger = commands or CommandRepository()
    document_repo = documents or DocumentRepository()
    session.execute(text(
        "SELECT run_id FROM audit_run WHERE run_id = :run_id FOR UPDATE"
    ), {"run_id": source_run_id}).scalar_one_or_none()
    source = repository.get(session, source_run_id)
    source_version = document_repo.get_version(session, VersionUid.parse(source.version_uid))
    key = IdempotencyKey(idempotency_key)
    frozen: FrozenRoute | None = None
    admitted: AdmittedGroup | None = None
    approved_cost = None
    planned: StagePlanDraft | None = None
    stage_plan: FrozenStagePlan | None = None
    if ledger.find(session, command_type=COMMAND_TYPE_START_RUN_FROM_STAGE, idempotency_key=key) is None:
        # A run that has not ended has no finished stages to take; say so before the reuse rule is asked.
        if source.state not in _TERMINAL_RUN_STATES:
            raise DomainError(
                ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
                machine="audit_run", current_state=source.state, requested_state="start_from_stage",
            )
        if section_profiles is not None:
            routed = route_classified_version(source_version, section_profiles)
            analysis_profile_id = routed.analysis_profile_id
            prompt_bundle_id = routed.prompt_bundle_id
        planned = None if stage_plans is None else stage_plans(session)
        if planned is not None and cost_preflight is None:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="analysis_cost_preflight")
        chosen_connection_id = None if planned is not None else repository.chosen_executor_connection(session, source_run_id)
        if chosen_connection_id is not None and connection_route is None:
            raise _chosen_executor_unserved()
        if cost_preflight is not None:
            estimate = cost_preflight.estimate_from_stage(
                session, run_id=source_run_id, start_stage_id=start_stage_id, version_record=source_version,
                parse_native_text=False, **_planned_estimate_kwargs(planned, stage_plans))
            approved_cost = estimate.approve(None if cost_consent is None else dict(cost_consent), actor_user_uid=cost_actor_uid)
            frozen = estimate.frozen_route
            admitted = getattr(estimate, "admitted_group", None)
            stage_plan = _plan_of(estimate, planned)
            budget = approved_cost["window_characters"]
        elif cost_consent is not None:
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="analysis_cost_preflight")
        else:
            admitted = admit_group_for_start(
                session, group_admitter,
                executor_group_id=_named_group_of(session, source, chosen_connection_id, group_admitter),
                executor_connection_id=chosen_connection_id, preset_id=None,
            )
            if admitted is not None:
                budget = admitted.input_budget_characters
            elif connection_route is not None:
                frozen = _freeze_for(session, connection_route, chosen_connection_id)
                budget = frozen.input_budget_characters
        # The same rule the estimate applied, now against the consent actually accepted (its extended-review plan is the
        # new run's flag); a refusal here, like the one above, precedes the claim and writes nothing.
        plan_stage_reuse(
            session, source_run_id=source_run_id, start_stage_id=start_stage_id,
            visual_only_pages=visual_only_pages_allowed(
                None if approved_cost is None else approved_cost.get("extended_review")),
            runs=repository,
        )
        if budget is not None and approved_cost is None:
            _refuse_over_window_budget(source_version.text_character_count, budget)
    claimed = ledger.begin(
        session, command_type=COMMAND_TYPE_START_RUN_FROM_STAGE, idempotency_key=key,
        fingerprint=payload_fingerprint({
            "started_from_run_id": source_run_id,
            "start_stage_id": start_stage_id,
            "frozen_input_digest": source.frozen_input_digest,
            **({"cost_consent": dict(cost_consent)} if cost_consent is not None else {}),
        }),
    )
    if isinstance(claimed, CommandReplay):
        replay_run_id = claimed.outcome.get("run_id")
        if not isinstance(replay_run_id, str):
            raise DomainError(ErrorCode.IDEMPOTENCY_KEY_STALE, command_type=COMMAND_TYPE_START_RUN_FROM_STAGE)
        return StartedRun(replay_run_id, str(claimed.command_id), True)
    assert isinstance(claimed, CommandStarted)
    if source.state not in _TERMINAL_RUN_STATES:
        raise DomainError(
            ErrorCode.STATE_TRANSITION_NOT_ALLOWED,
            machine="audit_run", current_state=source.state, requested_state="start_from_stage",
        )
    busy = session.execute(text(
        "SELECT 1 FROM audit_run WHERE started_from_run_id = :source AND start_stage_id = :stage "
        "AND state NOT IN ('published', 'partial', 'failed', 'cancelled') LIMIT 1"
    ), {"source": source_run_id, "stage": start_stage_id}).scalar_one_or_none()
    if busy is not None:
        raise DomainError(ErrorCode.CONFLICT, message="a run from this stage of this source is in progress")
    version_uid = VersionUid.parse(source.version_uid)
    if section_profiles is not None and analysis_profile_id is None:
        # Defensive, as in ``reaudit_run``: the key was unknown to the pre-claim read and yet replayed nothing.
        routed = route_classified_version(source_version, section_profiles)
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
        command_id=str(claimed.command_id),
        started_from_run_id=source_run_id, start_stage_id=start_stage_id,
        norms_snapshot_id=snapshot,
        connection_revision_id=None if frozen is None else frozen.revision_id,
        started_by_user_uid=started_by_user_uid,  # `R-151v`
        **_admission_columns(admitted),
        **_planned_columns(stage_plan),
    )
    _journal_standby(session, new_id, frozen)
    _journal_executor_choice(session, new_id, frozen)
    _journal_admission(session, new_id, admitted)
    _journal_stage_plan(session, new_id, stage_plan)
    repository.advance(session, run_id=new_id, from_state="created", to_state="queued")
    (jobs or JobRepository()).enqueue(session, run_id=new_id)
    ledger.succeed(session, claimed.command_id, {"run_id": new_id,
        "started_from_run_id": source_run_id, "start_stage_id": start_stage_id,
        **({"cost_consent": approved_cost} if approved_cost is not None else {})})
    return StartedRun(new_id, str(claimed.command_id), False)


__all__ = [
    "COMMAND_TYPE_START_RUN",
    "COMMAND_TYPE_START_RUN_FROM_STAGE",
    "NormsSnapshotReader",
    "SectionProfiles",
    "COMPARISON_ONLY_VERSION_REASON",
    "ROLE_SOURCE_DOCUMENT",
    "StartedRun",
    "current_norms_snapshot",
    "frozen_input_digest",
    "input_basis_digest",
    "run_of_command",
    "cancel_audit_run",
    "delete_audit_run",
    "reaudit_run",
    "admit_group_for_start",
    "refuse_comparison_only_version",
    "refuse_group_conflicts",
    "refuse_selectors_under_layout",
    "start_audit_run",
    "start_run_from_stage",
    "start_run_fingerprint",
]
