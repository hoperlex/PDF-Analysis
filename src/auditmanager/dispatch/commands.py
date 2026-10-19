"""The dispatcher's commands: assign work, and move an assignment along its history.

Each takes the caller's session and the actor's role set **read in the same transaction**
(the composition root reads it through ``access``, as ``classifyDocumentVersion``'s adapter
does), and returns the assignment as it now stands. Each refusal is a :class:`DomainError`
with an existing catalog code; nothing is written by a refused command.

* :func:`assign_work` -- an administrator gives a project, or one document of it, to an
  active expert, with an optional note. One open assignment per scope: an exact repeat (same
  first and current assignee, same note) answers the stored assignment; anything else is
  ``conflict`` (``conflict_reason: assignment_open``) -- reassign or cancel that one instead.
* :func:`transition_assignment` -- ``started``/``completed``/``returned`` by the assignee,
  ``reassigned``/``cancelled`` by an administrator, decided by :func:`.policy.plan_transition`.
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auditmanager.access.public import ROLE_EXPERT, AccountRepository, UserUid
from auditmanager.dispatch.identity import AssignmentUid
from auditmanager.dispatch.policy import (
    AGGREGATE_TYPE,
    CONFLICT_ASSIGNMENT_OPEN,
    CONSTRAINT_ACTIVE_EXPERT,
    KIND_ASSIGNED,
    KIND_REASSIGNED,
    MAX_NOTE_LENGTH,
    MAX_REASON_LENGTH,
    TERMINAL_KINDS,
    TransitionRequest,
    can_read,
    normalize_text,
    plan_transition,
    require_admin,
    require_reader,
)
from auditmanager.dispatch.repository import AssignmentRecord, AssignmentRepository
from auditmanager.documents.public import DocumentRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, IdentityError, ProjectUid

__all__ = ["assign_work", "transition_assignment"]

_UNIQUE_VIOLATION = "23505"


def _parse_project(value: str) -> ProjectUid:
    try:
        return ProjectUid.parse(value)
    except IdentityError:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, field="project_uid", constraint="pattern"
        ) from None


def _parse_document(value: str | None) -> DocumentUid | None:
    try:
        return DocumentUid.parse_optional(value)
    except IdentityError:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, field="document_uid", constraint="pattern"
        ) from None


def _parse_user(value: str, *, field: str) -> str:
    try:
        return str(UserUid.parse(value))
    except DomainError:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, field=field, constraint="pattern"
        ) from None


def _require_active_expert(
    session: Session, accounts: AccountRepository, user_uid: str, *, field: str
) -> None:
    """The account exists, is not archived and holds ``expert`` -- read in this transaction."""
    account = accounts.get_account(session, user_uid)
    if account is None:
        problem = "no such account"
    elif account.record.archived:
        problem = "the account is archived"
    elif ROLE_EXPERT not in account.roles:
        problem = "the account does not hold the expert role"
    else:
        return
    raise DomainError(
        ErrorCode.VALIDATION_FAILED,
        message=f"work is assigned only to an active expert: {problem}",
        field=field,
        constraint=CONSTRAINT_ACTIVE_EXPERT,
    )


def _require_scope(
    session: Session,
    documents: DocumentRepository,
    project_uid: ProjectUid,
    document_uid: DocumentUid | None,
) -> None:
    """The project exists, and the document (when named) belongs to it."""
    documents.get_project(session, project_uid)
    if document_uid is None:
        return
    owner = documents.require_document(session, document_uid)
    if owner != project_uid:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Document")


def assign_work(
    session: Session,
    *,
    project_uid: str,
    document_uid: str | None,
    assignee_user_uid: str,
    note: str | None,
    actor_uid: str,
    actor_roles: frozenset[str],
    accounts: AccountRepository | None = None,
    documents: DocumentRepository | None = None,
    repository: AssignmentRepository | None = None,
) -> AssignmentRecord:
    """Create one assignment and its ``assigned`` event, or answer the stored exact repeat.

    Order: the actor is an administrator (``permission_denied``); the identifiers and the
    note are well formed (``validation_failed``); the project exists and the document belongs
    to it (``not_found``); the scope is locked and an open assignment there is either this
    request repeated (answered) or a ``conflict``; the assignee is an active expert
    (``validation_failed``, ``constraint: active_expert_required``); then the two inserts.
    """
    require_admin(frozenset(actor_roles))
    project = _parse_project(project_uid)
    document = _parse_document(document_uid)
    assignee = _parse_user(assignee_user_uid, field="assignee_user_uid")
    cleaned_note = normalize_text(note, field="note", maximum=MAX_NOTE_LENGTH)
    accounts = accounts or AccountRepository()
    documents = documents or DocumentRepository()
    repository = repository or AssignmentRepository()

    _require_scope(session, documents, project, document)
    scope_document = None if document is None else str(document)
    repository.lock_scope(session, project_uid=str(project), document_uid=scope_document)
    open_ = repository.open_in_scope(
        session,
        project_uid=str(project),
        document_uid=scope_document,
        terminal_kinds=TERMINAL_KINDS,
    )
    for record, first_assignee in open_:
        if (
            first_assignee == assignee
            and record.assignee_user_uid == assignee
            and record.note == cleaned_note
        ):
            return record
    if open_:
        raise DomainError(
            ErrorCode.CONFLICT,
            message=(
                "this project or document already has an open assignment; reassign or "
                "cancel it instead of assigning the work again"
            ),
            aggregate_type=AGGREGATE_TYPE,
            conflict_reason=CONFLICT_ASSIGNMENT_OPEN,
        )

    _require_active_expert(session, accounts, assignee, field="assignee_user_uid")
    assignment_uid = AssignmentUid.new()
    repository.insert_assignment(
        session,
        assignment_uid=assignment_uid,
        project_uid=str(project),
        document_uid=scope_document,
        assignee_user_uid=assignee,
        created_by_user_uid=actor_uid,
        note=cleaned_note,
    )
    repository.append_event(
        session, assignment_uid=assignment_uid, seq=1, kind=KIND_ASSIGNED, actor_user_uid=actor_uid
    )
    created = repository.get(session, assignment_uid)
    if created is None:  # pragma: no cover - inserted above in this transaction
        raise DomainError(ErrorCode.INTERNAL_ERROR, message="the new assignment is not readable")
    return created


def transition_assignment(
    session: Session,
    *,
    assignment_uid: str,
    kind: str,
    actor_uid: str,
    actor_roles: frozenset[str],
    reason: str | None = None,
    new_assignee_user_uid: str | None = None,
    accounts: AccountRepository | None = None,
    repository: AssignmentRepository | None = None,
) -> AssignmentRecord:
    """Append one event to an assignment, answer an exact repeat, or refuse.

    Order: the actor holds a role at all (``permission_denied``, `R-80`); the identifiers
    and the reason are well formed (``validation_failed``); the
    assignment exists and the actor may read it (``not_found`` otherwise -- an expert never
    learns that somebody else's assignment exists); the row is locked; the policy decides
    (``permission_denied``, an exact repeat, ``state_transition_not_allowed``,
    ``validation_failed``); a new assignee is an active expert; then the insert.
    """
    roles = frozenset(actor_roles)
    require_reader(roles)
    uid = AssignmentUid.parse(assignment_uid)
    new_assignee = (
        None
        if new_assignee_user_uid is None
        else _parse_user(new_assignee_user_uid, field="new_assignee_user_uid")
    )
    request = TransitionRequest(
        kind=kind,
        reason=normalize_text(reason, field="reason", maximum=MAX_REASON_LENGTH),
        new_assignee=new_assignee,
    )
    accounts = accounts or AccountRepository()
    repository = repository or AssignmentRepository()

    locked = repository.lock(session, uid)
    if locked is None or not can_read(
        current_assignee=locked.state.current_assignee, viewer_uid=actor_uid, viewer_roles=roles
    ):
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type=AGGREGATE_TYPE)
    plan = plan_transition(locked.state, request, actor_uid=actor_uid, actor_roles=roles)
    if plan == "append":
        if request.kind == KIND_REASSIGNED:
            assert request.new_assignee is not None
            _require_active_expert(
                session, accounts, request.new_assignee, field="new_assignee_user_uid"
            )
        try:
            repository.append_event(
                session,
                assignment_uid=uid,
                seq=locked.next_seq,
                kind=request.kind,
                actor_user_uid=actor_uid,
                reason=request.reason,
                new_assignee_user_uid=request.new_assignee,
            )
        except IntegrityError as exc:
            # Unreachable under the row lock; a writer that bypassed it lost the race.
            if str(getattr(exc.orig, "sqlstate", "") or "") == _UNIQUE_VIOLATION:
                raise DomainError(
                    ErrorCode.CONFLICT, aggregate_type=AGGREGATE_TYPE
                ) from exc
            raise
    current = repository.get(session, uid)
    if current is None:  # pragma: no cover - locked above in this transaction
        raise DomainError(ErrorCode.INTERNAL_ERROR, message="the assignment is not readable")
    return current
