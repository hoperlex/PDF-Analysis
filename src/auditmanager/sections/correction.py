"""Pure rules for correcting a version's confirmed project stage and section.

`CLASSIFICATION-CORRECTION-01`, closing ``D-182``. ``W59-SECTION-SEAL-01`` stores one
expert confirmation per version and refuses every different choice
(``version_already_classified``); `W59-SECTION-IDENTITY-DECISION-01` named the way out: a
separately specified, **append-only** correction with actor, reason and revision. This module
is that specification, with no I/O; migration ``0028`` and the command that persists it
(phase B) obey it and add nothing to it.

The model
---------
A version's classification is a numbered history. **Revision 1** is the original expert
confirmation (the stored ``document_version_classification`` row, never touched again);
corrections are revisions **2..n**, each with the expert who made it and a reason. The
**current classification** is the latest revision -- derived, never stored as a second copy
that could disagree. Every revision is a full ``(project_stage, section_code)`` pair, so
"what a correction may change" is the stage, the section or both, and the one thing it may
not be is a no-op.

Rules, in the order they are decided (:func:`plan_classification_correction`)
------------------------------------------------------------------------------
1. **Who** (``permission_denied``, ``required_capability: role:expert``): only an account
   holding ``expert``. ``admin`` alone does not imply it, exactly as for the original
   confirmation. Decided first, so a caller who may not correct learns nothing about the
   request's validity or the version's state. The corrector need not be the first confirmer.
2. **The request's shape** (``validation_failed``): both target values are members of the
   catalogue (stage ``P``/``R``, one of the fifteen codes); the reason is present, trimmed,
   not longer than :data:`MAX_REASON_LENGTH`, holds a letter or a digit and no control or
   surrogate character; ``expected_revision`` is an integer of at least 1 (a ``bool`` is not).
3. **The history** is checked, not trusted (``internal_error`` if it is inconsistent, because
   no request can repair it): revisions run 1..n without a gap, belong to this version, carry
   valid values and a valid actor, revision 1 has no reason, every later one has one, and no
   revision repeats the values of the one before it.
4. **A correction presupposes the confirmation** (``conflict``, ``conflict_reason:
   version_not_classified``): an empty history has nothing to correct; classify first.
5. **``expected_revision`` is optimistic concurrency.** It names the revision the caller was
   looking at.

   * greater than the current revision: the caller claims a revision that does not exist
     (``validation_failed``, ``constraint: exceeds_current_revision``);
   * less than the current revision: either this is an **exact repeat** -- revision
     ``expected_revision + 1`` was written by the same actor with the same target values and
     the same reason -- and the answer is that stored revision, ``unchanged``, nothing written;
     or the version moved on since the caller looked, and it is ``conflict`` with
     ``conflict_reason: classification_revision_stale``, nothing written. A second expert who
     lost a race lands here even when they asked for the same values: the first correction
     stands, and their reason is not recorded under it;
   * equal to the current revision: proceed.
6. **No-op** (``validation_failed``, ``field: section_code``, ``constraint:
   differs_from_current``): the target must differ from the **current** classification, not
   from the original -- correcting back to the original values is a legitimate revision.
7. Otherwise the plan is to **append** revision ``current + 1``.

The reason is part of what makes a repeat exact on purpose: a retry sends the same body, and
a request that differs only in its reason is not a retry, so it is refused with a message
that says the first reason stands instead of answering as if the new one had been recorded.

What this module does not do
----------------------------
It reads no database and no clock (a revision's time is the database's), allocates nothing,
and does not know of runs: a run keeps the profile it pinned when it started, whatever the
classification becomes afterwards, and re-auditing is what routes from the corrected one.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final, Literal

from auditmanager.access.public import ROLE_EXPERT, ROLES, UserUid
from auditmanager.sections.suggestion import _catalogue
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdentityError, VersionUid

__all__ = [
    "AGGREGATE_TYPE",
    "CAPABILITY_EXPERT",
    "CHANGED_SECTION",
    "CHANGED_STAGE",
    "CONFLICT_REVISION_STALE",
    "CONFLICT_VERSION_NOT_CLASSIFIED",
    "CONSTRAINT_DIFFERS_FROM_CURRENT",
    "CONSTRAINT_EXCEEDS_CURRENT_REVISION",
    "MAX_REASON_LENGTH",
    "ORIGINAL_REVISION",
    "PROJECT_STAGES",
    "ClassificationRevision",
    "CorrectionPlan",
    "CorrectionRequest",
    "changed_fields",
    "current_revision",
    "normalize_reason",
    "plan_classification_correction",
]

#: ``aggregate_type`` on this module's ``conflict`` refusals (the seal's own, kept equal).
AGGREGATE_TYPE: Final[str] = "DocumentVersionClassification"
#: ``permission_denied`` ``required_capability``, the same as the original confirmation's.
CAPABILITY_EXPERT: Final[str] = "role:expert"

#: Revision 1 is the original confirmation; corrections start at 2.
ORIGINAL_REVISION: Final[int] = 1

#: The explicit project stages. Restated from the confirmation policy's literal on purpose:
#: a migration's CHECK restates it too, and a test holds the two equal.
PROJECT_STAGES: Final[tuple[str, ...]] = ("P", "R")

#: The longest reason, in characters after trimming. ``0028`` restates it in a CHECK
#: (phase B) and a test holds the two equal; it matches the dispatcher's reason bound.
MAX_REASON_LENGTH: Final[int] = 2000

#: ``conflict`` ``conflict_reason``: ``expected_revision`` is behind the version's current
#: revision and the request is not an exact repeat of the revision after it.
CONFLICT_REVISION_STALE: Final[str] = "classification_revision_stale"
#: ``conflict`` ``conflict_reason``: the version has no confirmation yet, so nothing to correct.
CONFLICT_VERSION_NOT_CLASSIFIED: Final[str] = "version_not_classified"
#: ``validation_failed`` ``constraint`` on ``section_code``: the target equals the current one.
CONSTRAINT_DIFFERS_FROM_CURRENT: Final[str] = "differs_from_current"
#: ``validation_failed`` ``constraint`` on ``expected_revision``: no such revision exists yet.
CONSTRAINT_EXCEEDS_CURRENT_REVISION: Final[str] = "exceeds_current_revision"

#: What a correction can change, as :func:`changed_fields` names it.
CHANGED_STAGE: Final[str] = "project_stage"
CHANGED_SECTION: Final[str] = "section_code"

#: Whitespace that is legitimate inside a reason; every other control character is refused.
_ALLOWED_CONTROLS: Final[str] = "\n\r\t"


@dataclass(frozen=True, slots=True)
class ClassificationRevision:
    """One numbered entry of a version's classification history, as stored.

    ``reason`` is ``None`` for revision 1 (the original confirmation) and a trimmed,
    non-empty text for every correction. The entry's time is the database's and is not
    part of the rules.
    """

    version_uid: str
    revision: int
    project_stage: str
    section_code: str
    actor_user_uid: str
    reason: str | None

    @property
    def is_original(self) -> bool:
        return self.revision == ORIGINAL_REVISION


@dataclass(frozen=True, slots=True)
class CorrectionRequest:
    """What a caller asks for: the full target pair, why, and the revision they looked at."""

    project_stage: str
    section_code: str
    reason: str
    expected_revision: int


@dataclass(frozen=True, slots=True)
class CorrectionPlan:
    """The decision: write ``revision`` (``append``) or answer it as already stored.

    For ``append``, ``revision`` is the entry to insert (``current + 1``, reason trimmed);
    for ``unchanged`` it is the stored entry this exact request created earlier. ``changed``
    names which of the two values that entry changed relative to the one before it.
    """

    action: Literal["append", "unchanged"]
    revision: ClassificationRevision
    changed: frozenset[str]


# -- the pieces other contexts and the command reuse ---------------------------------------


def changed_fields(
    previous_stage: str, previous_section: str, stage: str, section: str
) -> frozenset[str]:
    """Which of ``project_stage`` / ``section_code`` differ between two pairs."""
    changed: set[str] = set()
    if previous_stage != stage:
        changed.add(CHANGED_STAGE)
    if previous_section != section:
        changed.add(CHANGED_SECTION)
    return frozenset(changed)


def normalize_reason(raw: object) -> str:
    """Trim a reason and refuse one that is absent, unbounded, unprintable or empty of words.

    Returns the text that is stored and compared. A reason must hold at least one letter or
    digit: whitespace, punctuation and zero-width characters alone are not a reason.
    """
    if not isinstance(raw, str):
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="reason", constraint="type")
    cleaned = raw.strip()
    if not cleaned:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="a correction needs a reason",
            field="reason",
            constraint="required",
        )
    if len(cleaned) > MAX_REASON_LENGTH:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=f"reason is longer than {MAX_REASON_LENGTH} characters",
            field="reason",
            constraint="max_length",
        )
    has_substance = False
    for character in cleaned:
        category = unicodedata.category(character)
        if category == "Cs" or (category == "Cc" and character not in _ALLOWED_CONTROLS):
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message="reason holds a control or surrogate character",
                field="reason",
                constraint="printable",
            )
        if category[0] in ("L", "N"):
            has_substance = True
    if not has_substance:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="a reason holds at least one letter or digit",
            field="reason",
            constraint="required",
        )
    return cleaned


def current_revision(
    version_uid: str, history: Sequence[ClassificationRevision]
) -> ClassificationRevision | None:
    """The latest revision of a checked history, or ``None`` when the version is unclassified."""
    checked = _checked_history(version_uid, history)
    return checked[-1] if checked else None


# -- the decision --------------------------------------------------------------------------


def plan_classification_correction(
    *,
    version_uid: str,
    history: Sequence[ClassificationRevision],
    request: CorrectionRequest,
    actor_uid: str,
    actor_roles: frozenset[str],
) -> CorrectionPlan:
    """Decide one correction against the version's stored history, or refuse (module docstring).

    ``history`` is every stored revision of ``version_uid``, oldest first, read in the
    transaction that will write the plan, after the version's chain was proved and its
    classification locked. ``actor_roles`` must come from the authenticated account's state
    in that transaction, never from the client.
    """
    _require_expert(actor_uid, actor_roles)
    stage, section, reason, expected = _checked_request(request)
    revisions = _checked_history(version_uid, history)
    if not revisions:
        raise DomainError(
            ErrorCode.CONFLICT,
            message="this version has no classification to correct; classify it first",
            aggregate_type=AGGREGATE_TYPE,
            conflict_reason=CONFLICT_VERSION_NOT_CLASSIFIED,
        )
    current = revisions[-1]
    if expected > current.revision:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="expected_revision names a revision this version does not have",
            field="expected_revision",
            constraint=CONSTRAINT_EXCEEDS_CURRENT_REVISION,
        )
    if expected < current.revision:
        stored = revisions[expected]  # revision ``expected + 1``: index ``expected``
        if _is_same_request(stored, actor_uid, stage, section, reason):
            before = revisions[expected - 1]
            return CorrectionPlan(
                "unchanged",
                stored,
                changed_fields(
                    before.project_stage, before.section_code, stored.project_stage,
                    stored.section_code,
                ),
            )
        raise DomainError(
            ErrorCode.CONFLICT,
            message=_stale_message(stored, actor_uid, stage, section, current.revision),
            aggregate_type=AGGREGATE_TYPE,
            conflict_reason=CONFLICT_REVISION_STALE,
        )
    changed = changed_fields(current.project_stage, current.section_code, stage, section)
    if not changed:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="the requested project stage and section equal the current classification",
            field="section_code",
            constraint=CONSTRAINT_DIFFERS_FROM_CURRENT,
        )
    return CorrectionPlan(
        "append",
        ClassificationRevision(
            version_uid=version_uid,
            revision=current.revision + 1,
            project_stage=stage,
            section_code=section,
            actor_user_uid=actor_uid,
            reason=reason,
        ),
        changed,
    )


# -- parts ---------------------------------------------------------------------------------


def _require_expert(actor_uid: str, actor_roles: frozenset[str]) -> None:
    denied = DomainError(ErrorCode.PERMISSION_DENIED, required_capability=CAPABILITY_EXPERT)
    try:
        UserUid.parse(actor_uid)
    except DomainError:
        raise denied from None
    if (
        not isinstance(actor_roles, frozenset)
        or not actor_roles.issubset(ROLES)
        or ROLE_EXPERT not in actor_roles
    ):
        raise denied


def _checked_request(request: CorrectionRequest) -> tuple[str, str, str, int]:
    if not isinstance(request, CorrectionRequest):
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="body", constraint="type")
    stage = request.project_stage
    if not isinstance(stage, str) or stage not in PROJECT_STAGES:
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="project_stage", constraint="enum")
    section = request.section_code
    if not isinstance(section, str) or section not in _section_codes():
        raise DomainError(ErrorCode.VALIDATION_FAILED, field="section_code", constraint="enum")
    reason = normalize_reason(request.reason)
    expected = request.expected_revision
    if type(expected) is not int:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, field="expected_revision", constraint="type"
        )
    if expected < ORIGINAL_REVISION:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=f"expected_revision is at least {ORIGINAL_REVISION}",
            field="expected_revision",
            constraint="minimum",
        )
    return stage, section, reason, expected


def _checked_history(
    version_uid: str, history: Sequence[ClassificationRevision]
) -> tuple[ClassificationRevision, ...]:
    """The history as a tuple, or ``internal_error``: no request can repair a bad history."""
    try:
        VersionUid.parse(version_uid)
    except IdentityError:
        raise _inconsistent("version_identity_invalid") from None
    revisions = tuple(history)
    codes = _section_codes()
    previous: ClassificationRevision | None = None
    for number, entry in enumerate(revisions, start=ORIGINAL_REVISION):
        if not isinstance(entry, ClassificationRevision):
            raise _inconsistent("revision_invalid")
        if entry.version_uid != version_uid:
            raise _inconsistent("revision_version_mismatch")
        if type(entry.revision) is not int or entry.revision != number:
            raise _inconsistent("revision_sequence_broken")
        if (
            not isinstance(entry.project_stage, str)
            or entry.project_stage not in PROJECT_STAGES
            or not isinstance(entry.section_code, str)
            or entry.section_code not in codes
        ):
            raise _inconsistent("revision_value_unknown")
        try:
            UserUid.parse(entry.actor_user_uid)
        except DomainError:
            raise _inconsistent("revision_actor_invalid") from None
        if entry.is_original:
            if entry.reason is not None:
                raise _inconsistent("original_revision_has_reason")
        elif (
            not isinstance(entry.reason, str)
            or not entry.reason
            or entry.reason != entry.reason.strip()
        ):
            raise _inconsistent("correction_reason_invalid")
        if previous is not None and not changed_fields(
            previous.project_stage, previous.section_code, entry.project_stage, entry.section_code
        ):
            raise _inconsistent("revision_repeats_previous")
        previous = entry
    return revisions


def _is_same_request(
    stored: ClassificationRevision, actor_uid: str, stage: str, section: str, reason: str
) -> bool:
    return (
        stored.actor_user_uid == actor_uid
        and stored.project_stage == stage
        and stored.section_code == section
        and stored.reason == reason
    )


def _stale_message(
    stored: ClassificationRevision, actor_uid: str, stage: str, section: str, current: int
) -> str:
    if (
        stored.actor_user_uid == actor_uid
        and stored.project_stage == stage
        and stored.section_code == section
    ):
        return (
            "this correction is already recorded with a different reason; the first reason "
            "stands and nothing was changed"
        )
    return (
        f"the classification is now at revision {current}; it changed since the revision "
        "this correction was based on, and nothing was changed -- read it again"
    )


def _inconsistent(reason: str) -> DomainError:
    # A stored history the database's own constraints should have made impossible: a fault
    # to surface, never a request a caller can correct.
    return DomainError(
        ErrorCode.INTERNAL_ERROR, message=f"classification history inconsistent: {reason}"
    )


def _section_codes() -> frozenset[str]:
    return frozenset(entry.code for entry in _catalogue())
