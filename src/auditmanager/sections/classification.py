"""Served W59 section identity: classify a version, review it, route a run from it.

`W59-SECTION-SEAL-01` wires the pure preparations of this package
(:mod:`.confirmation`, :mod:`.review`, :mod:`.staged_routing`) to the persisted
classification ``documents`` stores in ``document_version_classification``
(``0024_version_classification``). Three entry points, each taking the caller's session:

* :func:`classify_document_version` -- the expert's explicit stage and section for one
  version, authorized from the account's role set read in the same transaction. An exact
  repeat answers the stored row (first confirmer kept); a different choice is ``conflict``
  with ``conflict_reason: version_already_classified`` and writes nothing.
* :func:`correct_document_version_classification` -- an expert's append-only correction of
  the stage and/or section (`CLASSIFICATION-CORRECTION-01`): the rules are
  :mod:`auditmanager.sections.correction`'s; this reads the version's whole history under a
  lock, applies them and appends one revision, or answers the revision an exact repeat created.
* :func:`read_section_review` -- the facts a review needs, read in one session; the review
  itself (:func:`build_section_review`) is computed afterwards, outside any transaction,
  because the recognised-text evidence is read from the object store.
* :func:`route_classified_version` -- run start's guard: the persisted classification, the
  staged route and the caller's sealed profile table, with no AR fallback.

No file name, suggestion or legacy ``document.section`` is a classification here; each is
display evidence at most.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Final

from sqlalchemy.orm import Session

from auditmanager.documents.public import (
    MANIFEST_ROLE_MARKDOWN,
    ClassificationRevisionRecord,
    DocumentRepository,
    DocumentVersionRecord,
    ManifestEntry,
    VersionClassificationRecord,
)
from auditmanager.sections.correction import (
    ClassificationRevision,
    CorrectionRequest,
    plan_classification_correction,
)
from auditmanager.sections.confirmation import (
    ExpertSectionConfirmation,
    SectionConfirmationRefused,
    prepare_section_confirmation,
)
from auditmanager.sections.review import SectionReviewPacket, prepare_section_review
from auditmanager.sections.routing import SectionRouteUnavailable
from auditmanager.sections.staged_routing import StagedSectionRoute, route_staged_section
from auditmanager.sections.suggestion import _catalogue
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid

__all__ = [
    "CONFLICT_VERSION_ALREADY_CLASSIFIED",
    "ClassifiedRoute",
    "ReviewFacts",
    "SECTION_CODES",
    "build_section_review",
    "classify_document_version",
    "correct_document_version_classification",
    "read_section_review",
    "route_classified_version",
    "section_names",
]

#: ``conflict`` detail: the version already holds a different stage or section.
CONFLICT_VERSION_ALREADY_CLASSIFIED: Final[str] = "version_already_classified"
#: The fifteen section codes, from the one reviewed catalogue this package owns.
SECTION_CODES: Final[frozenset[str]] = frozenset(entry.code for entry in _catalogue())

#: Refusals of :func:`route_staged_section` that mean "no executable profile for the
#: confirmed code"; every other reason is a missing or inconsistent classification.
_PROFILE_REASONS: Final[frozenset[str]] = frozenset(
    {
        "section_unknown",
        "section_profile_unavailable",
        "section_profile_invalid",
        "section_profile_registry_invalid",
    }
)


def section_names() -> Mapping[str, str]:
    """Code to Russian name, from the reviewed suggestion catalogue."""
    return {entry.code: entry.name for entry in _catalogue()}


# -- classify ------------------------------------------------------------------------


def classify_document_version(
    session: Session,
    *,
    project_uid: str,
    document_uid: str,
    version_uid: str,
    project_stage: str,
    section_code: str,
    actor_uid: str,
    actor_roles: frozenset[str],
    documents: DocumentRepository | None = None,
) -> VersionClassificationRecord:
    """Persist one expert's classification of one version, or answer the stored one.

    The caller owns the transaction and reads ``actor_roles`` from the account inside it.
    Order: the version chain (``not_found``), then the pure confirmation policy against the
    stored row, then the insert. The insert is ``ON CONFLICT DO NOTHING``; a concurrent
    first confirmation that won is re-read and answered by the same rule as a stored one.
    """
    repository = documents or DocumentRepository()
    version = repository.get_version_in(
        session,
        project_uid=ProjectUid.parse(project_uid),
        document_uid=DocumentUid.parse(document_uid),
        version_uid=VersionUid.parse(version_uid),
    )
    stored = version.classification
    plan = _plan(version_uid, project_stage, section_code, actor_uid, actor_roles, stored)
    if plan is None:
        assert stored is not None
        return stored

    inserted = repository.insert_classification(
        session,
        version_uid=VersionUid.parse(version_uid),
        project_stage=project_stage,
        section_code=section_code,
        confirmed_by_user_uid=actor_uid,
    )
    if inserted is not None:
        return inserted
    winner = repository.get_classification(session, VersionUid.parse(version_uid))
    if winner is None:  # pragma: no cover - DO NOTHING returned no row and none exists
        raise DomainError(
            ErrorCode.CONFLICT,
            aggregate_type="DocumentVersionClassification",
            conflict_reason=CONFLICT_VERSION_ALREADY_CLASSIFIED,
        )
    if _plan(version_uid, project_stage, section_code, actor_uid, actor_roles, winner) is None:
        return winner
    raise AssertionError("an unchanged plan must be answered above")  # pragma: no cover


def _plan(
    version_uid: str,
    project_stage: str,
    section_code: str,
    actor_uid: str,
    actor_roles: frozenset[str],
    stored: VersionClassificationRecord | None,
) -> object | None:
    """``None`` when ``stored`` already answers the request; a plan to insert otherwise."""
    previous = (
        None
        if stored is None
        else ExpertSectionConfirmation(
            version_uid=str(stored.version_uid),
            code=stored.section_code,
            stage=stored.project_stage,  # type: ignore[arg-type]
            expert_uid=stored.confirmed_by_user_uid,
        )
    )
    try:
        plan = prepare_section_confirmation(
            version_uid=version_uid,
            code=section_code,
            stage=project_stage,
            expert_uid=actor_uid,
            actor_roles=actor_roles,
            previous=previous,
        )
    except SectionConfirmationRefused as refusal:
        raise _domain_refusal(str(refusal)) from None
    return None if plan.action == "unchanged" else plan


def _domain_refusal(reason: str) -> DomainError:
    if reason == "expert_role_required":
        return DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:expert")
    if reason in {"section_already_confirmed", "previous_confirmation_stage_mismatch"}:
        return DomainError(
            ErrorCode.CONFLICT,
            message=(
                "this version is already classified with a different project stage or "
                "section; the classification stands and was not changed -- an expert "
                "corrects it with a reason instead"
            ),
            aggregate_type="DocumentVersionClassification",
            conflict_reason=CONFLICT_VERSION_ALREADY_CLASSIFIED,
        )
    if reason == "section_unknown":
        return DomainError(
            ErrorCode.VALIDATION_FAILED, field="section_code", constraint="enum"
        )
    if reason == "version_stage_unclassified":
        return DomainError(
            ErrorCode.VALIDATION_FAILED, field="project_stage", constraint="enum"
        )
    if reason == "expert_identity_invalid":
        return DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:expert")
    # A version identity the chain lookup already resolved cannot be malformed here, and a
    # stored row the database checked cannot disagree with its own version: either is a
    # fault, never a request a caller can correct.
    return DomainError(ErrorCode.INTERNAL_ERROR, message=f"classification refused: {reason}")


# -- correct -------------------------------------------------------------------------


def correct_document_version_classification(
    session: Session,
    *,
    project_uid: str,
    document_uid: str,
    version_uid: str,
    project_stage: str,
    section_code: str,
    reason: str,
    expected_revision: int,
    actor_uid: str,
    actor_roles: frozenset[str],
    documents: DocumentRepository | None = None,
) -> VersionClassificationRecord:
    """Append one expert correction of a version's classification, or answer its exact repeat.

    The caller owns the transaction and reads ``actor_roles`` from the account inside it.
    Order: the version chain (``not_found``); the version's original classification row is
    locked, so corrections of one version serialise; its whole history is read under the lock;
    the pure rules decide (:func:`plan_classification_correction`); an ``append`` is inserted
    as the next revision, an ``unchanged`` answers the stored revision the same request
    created. The answer is that revision as a classification: its values, the expert who made
    it and when, and its number -- not necessarily the version's current one when someone
    corrected after it.
    """
    repository = documents or DocumentRepository()
    version_id = VersionUid.parse(version_uid)
    repository.get_version_in(
        session,
        project_uid=ProjectUid.parse(project_uid),
        document_uid=DocumentUid.parse(document_uid),
        version_uid=version_id,
    )
    repository.lock_classification(session, version_id)
    stored = repository.list_classification_revisions(session, version_id)
    plan = plan_classification_correction(
        version_uid=str(version_id),
        history=[_revision_of(entry) for entry in stored],
        request=CorrectionRequest(
            project_stage=project_stage,
            section_code=section_code,
            reason=reason,
            expected_revision=expected_revision,
        ),
        actor_uid=actor_uid,
        actor_roles=actor_roles,
    )
    if plan.action == "unchanged":
        answered = next(
            entry for entry in stored if entry.revision == plan.revision.revision
        )
    else:
        assert plan.revision.reason is not None  # corrections always carry a reason
        answered = repository.insert_correction(
            session,
            version_uid=version_id,
            revision=plan.revision.revision,
            project_stage=plan.revision.project_stage,
            section_code=plan.revision.section_code,
            corrected_by_user_uid=plan.revision.actor_user_uid,
            reason=plan.revision.reason,
        )
    return VersionClassificationRecord(
        version_uid=answered.version_uid,
        project_stage=answered.project_stage,
        section_code=answered.section_code,
        confirmed_by_user_uid=answered.actor_user_uid,
        confirmed_at=answered.decided_at,
        revision=answered.revision,
    )


def _revision_of(entry: ClassificationRevisionRecord) -> ClassificationRevision:
    return ClassificationRevision(
        version_uid=str(entry.version_uid),
        revision=entry.revision,
        project_stage=entry.project_stage,
        section_code=entry.section_code,
        actor_user_uid=entry.actor_user_uid,
        reason=entry.reason,
    )


# -- review --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ReviewFacts:
    """What one review needs from the database, read in one session."""

    version_uid: str
    classification: VersionClassificationRecord | None
    source_filename: str
    markdown: ManifestEntry | None
    #: `CLASSIFICATION-CORRECTION-01`. Every revision of the classification, oldest first
    #: (revision 1 is the original confirmation); empty while the version is unclassified.
    revisions: tuple[ClassificationRevisionRecord, ...] = ()


def read_section_review(
    session: Session,
    *,
    project_uid: str,
    document_uid: str,
    version_uid: str,
    documents: DocumentRepository | None = None,
) -> ReviewFacts:
    """The version through its chain, its classification, upload name and markdown entry."""
    repository = documents or DocumentRepository()
    version: DocumentVersionRecord = repository.get_version_in(
        session,
        project_uid=ProjectUid.parse(project_uid),
        document_uid=DocumentUid.parse(document_uid),
        version_uid=VersionUid.parse(version_uid),
    )
    markdown = next(
        (entry for entry in version.manifest if entry.role == MANIFEST_ROLE_MARKDOWN), None
    )
    return ReviewFacts(
        version_uid=str(version.version_uid),
        classification=version.classification,
        source_filename=repository.source_filename_of(session, version.version_uid) or "",
        markdown=markdown,
        revisions=repository.list_classification_revisions(session, version.version_uid),
    )


def build_section_review(
    facts: ReviewFacts, *, recognised_text: str | None
) -> SectionReviewPacket:
    """All fifteen options with display evidence; ``recognised_text`` ``None`` means none.

    A version without a recognised-text markdown has only its upload name as evidence; the
    caller reports which it was. Nothing here selects, confirms or routes.
    """
    return prepare_section_review(
        version_uid=facts.version_uid,
        filename=facts.source_filename,
        extracted_text=recognised_text or "",
    )


# -- run routing ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ClassifiedRoute:
    """The checked route and the profile pair run start pins."""

    route: StagedSectionRoute
    analysis_profile_id: str
    prompt_bundle_id: str


def route_classified_version(
    version: DocumentVersionRecord,
    profiles: Mapping[str, tuple[str, str]],
) -> ClassifiedRoute:
    """Route a run from the version's persisted classification, or refuse.

    ``profiles`` is the sealed section-to-``(analysis_profile_id, prompt_bundle_id)`` table
    the composition root loaded. Each refusal has its own code (`BETA-CONTRACT-SEAL-01`,
    `D-179`): ``version_classification_required`` when the version has no (consistent) stage
    and section, ``section_profile_unavailable`` when the confirmed section has no registered
    profile. There is no AR fallback: a missing route is a refusal, never a default.
    """
    classification = version.classification
    if classification is None:
        raise _unroutable(ErrorCode.VERSION_CLASSIFICATION_REQUIRED)
    confirmation = ExpertSectionConfirmation(
        version_uid=str(classification.version_uid),
        code=classification.section_code,
        stage=classification.project_stage,  # type: ignore[arg-type]
        expert_uid=classification.confirmed_by_user_uid,
    )
    try:
        route = route_staged_section(
            version_uid=str(version.version_uid),
            project_stage=classification.project_stage,
            confirmation=confirmation,
            available_profiles={code: pair[0] for code, pair in profiles.items()},
        )
    except SectionRouteUnavailable as refusal:
        code = (
            ErrorCode.SECTION_PROFILE_UNAVAILABLE
            if str(refusal) in _PROFILE_REASONS
            else ErrorCode.VERSION_CLASSIFICATION_REQUIRED
        )
        raise _unroutable(code) from None
    analysis_profile_id, prompt_bundle_id = profiles[route.section_code]
    return ClassifiedRoute(
        route=route,
        analysis_profile_id=analysis_profile_id,
        prompt_bundle_id=prompt_bundle_id,
    )


def _unroutable(code: ErrorCode) -> DomainError:
    message = (
        "this version has no expert classification (project stage and section), so no "
        "analysis profile can be selected; classify it first"
        if code is ErrorCode.VERSION_CLASSIFICATION_REQUIRED
        else "the version's confirmed section has no registered text profile, so a run "
        "cannot start; no other section's profile is substituted"
    )
    return DomainError(code, message=message)


#: A reader of one manifest entry's bytes as text, supplied by the composition root.
RecognisedTextReader = Callable[[ManifestEntry], str]
