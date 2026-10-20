"""The vendor-list commands: an administrator's global list and an expert's project override.

Each takes the caller's session and the actor's role set **read in the same transaction** (the
composition root reads it through ``access``), appends at most one immutable revision, and
returns the revision now in force for that scope and section. Refusals are
:class:`DomainError` with existing catalog codes; a refused command writes nothing.

* :func:`set_global_vendor_list` -- ``admin``; mode is always ``list`` (an empty list is an
  explicit "no restriction").
* :func:`set_project_vendor_list` -- ``expert``; mode ``list`` (these entries apply to the
  project) or ``inherit`` (remove the override, the global list applies again).

Both answer an exact repeat with the stored revision and write nothing, and both refuse an
``expected_vendor_list_id`` that is not the latest revision of that scope and section
(``conflict``, ``conflict_reason: vendor_list_changed``). Writers of one scope and section
serialise on an advisory lock, so ``revision_number`` never collides.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from auditmanager.documents.public import DocumentRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdentityError, ProjectUid

from .identity import VendorListId
from .policy import (
    AGGREGATE_VENDOR_LIST,
    CONFLICT_VENDOR_LIST_CHANGED,
    MODE_INHERIT,
    MODE_LIST,
    SCOPE_GLOBAL,
    SCOPE_PROJECT,
    VendorListEntry,
    normalize_entries,
    parse_mode,
    parse_section_code,
    require_admin,
    require_expert,
)
from .repository import OptimisationRepository, VendorListRevisionRecord

__all__ = ["VendorListChange", "set_global_vendor_list", "set_project_vendor_list"]


@dataclass(frozen=True, slots=True)
class VendorListChange:
    """What a set command did: the revision in force (``None``: no list) and whether it wrote."""

    revision: VendorListRevisionRecord | None
    created: bool


def _parse_project(value: str) -> ProjectUid:
    try:
        return ProjectUid.parse(value)
    except IdentityError:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, field="project_uid", constraint="pattern"
        ) from None


def _expected(value: str | None) -> str | None:
    return None if value is None else str(VendorListId.parse(value))


def _check_expected(latest: VendorListRevisionRecord | None, expected: str | None, given: bool) -> None:
    if not given:
        return
    current = None if latest is None else latest.vendor_list_id
    if current != expected:
        raise DomainError(
            ErrorCode.CONFLICT,
            message="the vendor list changed since it was read; reload it and apply the change again",
            aggregate_type=AGGREGATE_VENDOR_LIST,
            conflict_reason=CONFLICT_VENDOR_LIST_CHANGED,
        )


def _append(
    session: Session,
    repository: OptimisationRepository,
    *,
    scope: str,
    project_uid: str | None,
    section: str,
    mode: str,
    entries: tuple[VendorListEntry, ...],
    latest: VendorListRevisionRecord | None,
    actor_uid: str,
) -> VendorListRevisionRecord:
    vendor_list_id = VendorListId.new()
    repository.insert_vendor_list(
        session,
        vendor_list_id=vendor_list_id,
        scope=scope,
        project_uid=project_uid,
        section=section,
        mode=mode,
        revision_number=1 if latest is None else latest.revision_number + 1,
        entries=entries,
        set_by_user_uid=actor_uid,
    )
    stored = repository.get_vendor_list(session, str(vendor_list_id))
    if stored is None:  # pragma: no cover - inserted above in this transaction
        raise DomainError(ErrorCode.INTERNAL_ERROR, message="the new vendor list is not readable")
    return stored


def set_global_vendor_list(
    session: Session,
    *,
    section_code: str,
    entries: Sequence[Any] | None,
    actor_uid: str,
    actor_roles: frozenset[str],
    expected_vendor_list_id: str | None = None,
    expect_current: bool = False,
    repository: OptimisationRepository | None = None,
) -> VendorListChange:
    """Append a global revision for one section, or answer the stored exact repeat.

    ``expect_current`` turns the concurrency check on: the caller says which revision it read
    (``expected_vendor_list_id``; ``None`` meaning "there was none").
    """
    require_admin(
        frozenset(actor_roles),
        aggregate_type=AGGREGATE_VENDOR_LIST,
        act="change the global vendor list",
    )
    section = parse_section_code(section_code)
    cleaned = normalize_entries(entries)
    expected = _expected(expected_vendor_list_id)
    repository = repository or OptimisationRepository()

    repository.lock_vendor_scope(session, project_uid=None, section=section)
    latest = repository.latest_vendor_list(session, project_uid=None, section=section)
    _check_expected(latest, expected, expect_current or expected is not None)
    if latest is not None and latest.mode == MODE_LIST and latest.entries == cleaned:
        return VendorListChange(latest, created=False)
    stored = _append(
        session,
        repository,
        scope=SCOPE_GLOBAL,
        project_uid=None,
        section=section,
        mode=MODE_LIST,
        entries=cleaned,
        latest=latest,
        actor_uid=actor_uid,
    )
    return VendorListChange(stored, created=True)


def set_project_vendor_list(
    session: Session,
    *,
    project_uid: str,
    section_code: str,
    mode: str,
    entries: Sequence[Any] | None,
    actor_uid: str,
    actor_roles: frozenset[str],
    expected_vendor_list_id: str | None = None,
    expect_current: bool = False,
    documents: DocumentRepository | None = None,
    repository: OptimisationRepository | None = None,
) -> VendorListChange:
    """Append a project revision for one section, or answer the current state unchanged.

    ``mode: inherit`` with entries is ``validation_failed`` (``constraint: inherit_has_no_entries``);
    an ``inherit`` when no override is in force writes nothing and answers the latest project
    revision (or ``None``).
    """
    require_expert(
        frozenset(actor_roles),
        aggregate_type=AGGREGATE_VENDOR_LIST,
        act="change a project's vendor list",
    )
    project = _parse_project(project_uid)
    section = parse_section_code(section_code)
    chosen = parse_mode(mode)
    cleaned = normalize_entries(entries)
    if chosen == MODE_INHERIT and cleaned:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, field="entries", constraint="inherit_has_no_entries"
        )
    expected = _expected(expected_vendor_list_id)
    documents = documents or DocumentRepository()
    repository = repository or OptimisationRepository()

    documents.get_project(session, project)
    repository.lock_vendor_scope(session, project_uid=str(project), section=section)
    latest = repository.latest_vendor_list(session, project_uid=str(project), section=section)
    _check_expected(latest, expected, expect_current or expected is not None)
    if chosen == MODE_INHERIT and (latest is None or latest.mode == MODE_INHERIT):
        return VendorListChange(latest, created=False)
    if (
        chosen == MODE_LIST
        and latest is not None
        and latest.mode == MODE_LIST
        and latest.entries == cleaned
    ):
        return VendorListChange(latest, created=False)
    stored = _append(
        session,
        repository,
        scope=SCOPE_PROJECT,
        project_uid=str(project),
        section=section,
        mode=chosen,
        entries=cleaned,
        latest=latest,
        actor_uid=actor_uid,
    )
    return VendorListChange(stored, created=True)
