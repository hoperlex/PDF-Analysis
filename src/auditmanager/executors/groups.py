"""Executor groups and routing rules: the records and the rules that need no database (`EXEC2-GROUP-STORE-01`).

Pure: no SQL, no I/O. A *group* is a set of interchangeable executors of one model (ADR-0026 decision 10). Its
settings live in immutable *revisions*: ``pin_id``, ``gateway_model``, ``billing``, the rate snapshot taken from
the provider lock, ``strategy`` (``least_loaded``, the only one) and the *members*, each a connection and the
**revision** of it the group snapshots -- the connection's *current* revision at the moment the group revision is
made. A *rule* (decision 11) points a ``work_kind`` at an immutable group revision; rules are append-only and the
current rule of a work kind is its highest ``rule_no``. The routing mode is an append-only journal with no
singleton row: the latest event is the mode, and an empty journal is ``legacy`` (decision 17).

Homogeneity (decision 10), which :func:`refuse_member` holds before anything is written and the database holds
again (``am_check_executor_group_member``): every member's snapshot revision pins exactly the group revision's
``pin_id`` and ``gateway_model`` and shares its ``billing``. The rates follow from the pin (they are the provider
lock's, copied once into the group revision), so two members of one pin cannot differ in rate. A mixed group is
refused, never repaired.

The membership of a revision is closed when the revision is made: the revision declares ``member_count`` (the length
of the request's member list, one to sixteen -- :func:`refuse_settings` holds the range before any write) and the
database refuses a member beyond it and a commit that holds fewer. No member is ever added to a revision later.

Refusals reuse the catalogue (ADR-0026 decision 18): ``validation_failed`` with ``field`` and ``constraint``,
``conflict`` with ``conflict_reason``, ``not_found`` with ``aggregate_type``. A detail names a field and a
classifier and never echoes a value.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Final

from auditmanager.executors.model import (
    BILLINGS,
    CONFLICT_GROUP_ARCHIVED,
    CONFLICT_GROUP_NAME_IN_USE,
    CONFLICT_GROUP_ROUTED,
    CONSTRAINT_MEMBER_BILLING_MISMATCH,
    CONSTRAINT_MEMBER_KIND_NOT_SERVED,
    CONSTRAINT_MEMBER_MODEL_MISMATCH,
    CONSTRAINT_MEMBER_PIN_MISMATCH,
    CONSTRAINT_MEMBER_REPEATED,
    CONSTRAINT_MEMBER_REVISION_NOT_OF_CONNECTION,
    CONSTRAINT_RANGE,
    CONSTRAINT_TIE_BREAK_ORDER_REPEATED,
    CONSTRAINT_UNKNOWN_EXECUTOR_CONNECTION,
    GROUP_MEMBERS_MAX,
    GROUP_MEMBERS_MIN,
    GROUP_STRATEGIES,
    ROUTING_MODE_LEGACY,
    WORK_KINDS,
    ConnectionRecord,
    RevisionRecord,
)
from auditmanager.executors.queries import Occupancy
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "AGGREGATE_GROUP",
    "AGGREGATE_GROUP_REVISION",
    "AGGREGATE_RULE",
    "MAX_NAME_LENGTH",
    "TIE_BREAK_MAX",
    "TIE_BREAK_MIN",
    "GroupCapacity",
    "GroupDetail",
    "GroupMemberRecord",
    "GroupRecord",
    "GroupRevisionRecord",
    "GroupSettings",
    "GroupSummary",
    "MemberRequest",
    "MemberStatus",
    "ModeState",
    "RuleListing",
    "RuleRecord",
    "clean_display_name",
    "group_archived",
    "group_name_in_use",
    "group_not_found",
    "group_revision_not_found",
    "group_routed",
    "refuse_member",
    "refuse_settings",
    "refuse_work_kind",
]

AGGREGATE_GROUP: Final[str] = "ExecutorGroup"
AGGREGATE_GROUP_REVISION: Final[str] = "ExecutorGroupRevision"
AGGREGATE_RULE: Final[str] = "ExecutorRoutingRule"
MAX_NAME_LENGTH: Final[int] = 120
#: ``executor_group_member.tie_break_order`` is 1 to 16 (``ck_executor_group_member_tie_break_order``).
TIE_BREAK_MIN: Final[int] = 1
TIE_BREAK_MAX: Final[int] = 16

# Control characters, line and paragraph separators and surrogates have no place in a label (as for presets).
_UNPRINTABLE = re.compile(r"[\x00-\x1f\x7f-\x9f  \ud800-\udfff]")


# --- records --------------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GroupRecord:
    """One group. ``rotation_cursor`` is the persisted tie-break rotation of ``least_loaded`` dispatch: the only
    column that changes freely."""

    group_id: str
    display_name: str
    rotation_cursor: int
    created_at: datetime
    created_by: str
    archived_at: datetime | None = None
    archived_by: str | None = None
    #: `HOSTS-BACKEND-01` (ADR-0028 decision 3): the group of a (model, access) pair, kept by the stand; never revised or archived by hand.
    system_managed: bool = False


@dataclass(frozen=True, slots=True)
class GroupMemberRecord:
    connection_id: str
    connection_revision_id: str
    tie_break_order: int | None = None


@dataclass(frozen=True, slots=True)
class GroupRevisionRecord:
    """One immutable revision with its members, ordered by ``tie_break_order`` (those without one last) and then
    ``connection_id``. The rates are the provider lock's, in USD per million tokens, copied when it was made."""

    group_revision_id: str
    group_id: str
    revision_no: int
    pin_id: str
    gateway_model: str
    billing: str
    input_per_mtok_usd: Decimal
    output_per_mtok_usd: Decimal
    strategy: str
    created_at: datetime
    created_by: str
    members: tuple[GroupMemberRecord, ...] = ()


@dataclass(frozen=True, slots=True)
class RuleRecord:
    """One revision of the rule of a work kind: it names an immutable group revision (and, through it, a group)."""

    rule_revision_id: str
    work_kind: str
    rule_no: int
    group_revision_id: str
    group_id: str
    set_at: datetime
    set_by: str


@dataclass(frozen=True, slots=True)
class ModeState:
    """The routing mode in force. ``mode_event_id`` and the rest are ``None`` while the journal is empty (``legacy``)."""

    mode: str = ROUTING_MODE_LEGACY
    mode_event_id: str | None = None
    changed_at: datetime | None = None
    changed_by: str | None = None


@dataclass(frozen=True, slots=True)
class GroupSummary:
    """A group with its current revision and the work kinds whose current rule names a revision of it."""

    group: GroupRecord
    current_revision: GroupRevisionRecord
    routed_work_kinds: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GroupDetail:
    """A group and every revision of it, newest first."""

    summary: GroupSummary
    revisions: tuple[GroupRevisionRecord, ...]


@dataclass(frozen=True, slots=True)
class RuleListing:
    """The current rule of each work kind that has one, ordered by work kind, and the routing mode."""

    routing_mode: ModeState
    rules: tuple[RuleRecord, ...]


@dataclass(frozen=True, slots=True)
class MemberStatus:
    """One member of the current revision as dispatch would see it now (derived at read time, stored nowhere)."""

    connection_id: str
    snapshot_revision_id: str
    current_revision_id: str | None
    occupancy: Occupancy | None
    issue: str | None

    @property
    def eligible(self) -> bool:
        """Dispatch would choose this member if work arrived now (``ExecutorGroupMemberStatus.eligible``). A member
        whose only issue is ``at_capacity`` is not eligible *now*, and ``issue`` says why not."""
        return self.issue is None


@dataclass(frozen=True, slots=True)
class GroupCapacity:
    """The capacity of a group's current revision: ``capacity`` and ``used`` sum the members in service (not
    archived, current revision equal to the snapshot); ``waiting`` counts the Runs and comparison jobs admitted
    on any revision of the group that are still ``pending``."""

    group_id: str
    group_revision_id: str
    members: tuple[MemberStatus, ...]
    capacity: int
    used: int
    waiting: int


# --- what an administrator asks for --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MemberRequest:
    """A member as named in a request: a connection and the revision of it to snapshot."""

    connection_id: str
    connection_revision_id: str
    tie_break_order: int | None = None


@dataclass(frozen=True, slots=True)
class GroupSettings:
    """The settings of one group revision as named in a request (the rates are taken from the provider lock)."""

    pin_id: str
    gateway_model: str
    billing: str
    strategy: str


# --- refusals ---------------------------------------------------------------------------------------------------


def _invalid(field: str, constraint: str, message: str = "the executor group is not acceptable") -> DomainError:
    return DomainError(ErrorCode.VALIDATION_FAILED, message=message, field=field, constraint=constraint)


def _conflict(reason: str) -> DomainError:
    return DomainError(
        ErrorCode.CONFLICT, message="the executor group is not in a state that allows this",
        conflict_reason=reason, aggregate_type=AGGREGATE_GROUP,
    )


def group_not_found() -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type=AGGREGATE_GROUP)


def group_revision_not_found() -> DomainError:
    return DomainError(ErrorCode.NOT_FOUND, aggregate_type=AGGREGATE_GROUP_REVISION)


def group_archived() -> DomainError:
    """``conflict`` / ``group_archived``: an archived group takes no revision and no rule."""
    return _conflict(CONFLICT_GROUP_ARCHIVED)


def group_name_in_use() -> DomainError:
    """``conflict`` / ``group_name_in_use``: an active group holds the name, without regard to case."""
    return _conflict(CONFLICT_GROUP_NAME_IN_USE)


def group_routed() -> DomainError:
    """``conflict`` / ``group_routed``: a rule still names the group, so it cannot be archived."""
    return _conflict(CONFLICT_GROUP_ROUTED)


def clean_display_name(raw: object) -> str:
    """The name as it is stored: trimmed, 1 to 120 characters, nothing unprintable.

    ``validation_failed`` on ``display_name`` with ``type`` (not text), ``required`` (blank after trimming),
    ``printable`` or ``max_length``. The database holds the length bounds as a CHECK; uniqueness among active
    groups, without regard to case, is a unique index and the command's own check."""
    if not isinstance(raw, str):
        raise _invalid("display_name", "type")
    name = raw.strip(" \t\r\n")
    if not name:
        raise _invalid("display_name", "required")
    if _UNPRINTABLE.search(name) is not None:
        raise _invalid("display_name", "printable")
    if len(name) > MAX_NAME_LENGTH:
        raise _invalid("display_name", "max_length")
    return name


def refuse_work_kind(work_kind: str) -> None:
    """``validation_failed`` on ``work_kind`` (``enum``) for a value the enumeration does not name."""
    if work_kind not in WORK_KINDS:
        raise _invalid("work_kind", "enum", "the work kind is not known")


def refuse_settings(
    settings: GroupSettings, members: Sequence[MemberRequest], *, pinned_model_ids: Collection[str],
) -> None:
    """Refuse what is wrong with a request before any row is read: the pin, the billing, the strategy, the number of
    members, a connection named twice and a tie-break order named twice or out of range.

    * ``pin_id`` / ``model_not_pinned`` -- the provider lock does not hold the pin (so there are no rates to copy);
    * ``billing`` / ``enum``, ``strategy`` / ``enum``;
    * ``members`` / ``range`` -- not one to sixteen;
    * ``members`` / ``member_repeated`` -- a connection twice (a duplicate member is refused, not merged);
    * ``members`` / ``tie_break_order_repeated`` -- one order twice; ``members`` / ``range`` -- an order outside 1..16.
    """
    if settings.pin_id not in pinned_model_ids:
        raise _invalid("pin_id", "model_not_pinned")
    if settings.billing not in BILLINGS:
        raise _invalid("billing", "enum")
    if settings.strategy not in GROUP_STRATEGIES:
        raise _invalid("strategy", "enum")
    if not GROUP_MEMBERS_MIN <= len(members) <= GROUP_MEMBERS_MAX:
        raise _invalid("members", CONSTRAINT_RANGE)
    if len({member.connection_id for member in members}) != len(members):
        raise _invalid("members", CONSTRAINT_MEMBER_REPEATED)
    orders = [member.tie_break_order for member in members if member.tie_break_order is not None]
    if any(not TIE_BREAK_MIN <= order <= TIE_BREAK_MAX for order in orders):
        raise _invalid("members", CONSTRAINT_RANGE)
    if len(set(orders)) != len(orders):
        raise _invalid("members", CONSTRAINT_TIE_BREAK_ORDER_REPEATED)


def refuse_member(
    settings: GroupSettings, member: MemberRequest, *, connection: ConnectionRecord | None,
    named: RevisionRecord | None, current: RevisionRecord | None, served: bool,
) -> None:
    """Refuse one member that cannot join a revision of ``settings`` (decision 10), in this order.

    * no such connection: ``422`` ``members`` / ``unknown_executor_connection``;
    * an archived connection: ``409`` ``connection_archived``;
    * the revision named is not the connection's **current** revision (it does not exist, belongs to another
      connection, or is an earlier revision of this one -- a group snapshots what the connection is *now*):
      ``422`` ``members`` / ``member_revision_not_of_connection``;
    * a kind this release does not serve: ``422`` ``members`` / ``member_kind_not_served``;
    * a revision that pins another model: ``422`` ``pin_id`` / ``member_pin_mismatch``; one that names another
      gateway model: ``gateway_model`` / ``member_model_mismatch``; one that is billed another way (mixed billing
      is not accepted): ``billing`` / ``member_billing_mismatch``.

    ``current`` is the connection's current revision as read under the connection's lock; ``served`` is whether
    this release serves that connection and revision. Nothing here echoes a value.
    """
    if connection is None:
        raise _invalid("members", CONSTRAINT_UNKNOWN_EXECUTOR_CONNECTION)
    if connection.archived_at is not None:
        raise DomainError(
            ErrorCode.CONFLICT, message="the connection is not in a state that allows this",
            conflict_reason="connection_archived",
        )
    if (
        named is None or current is None or named.connection_id != connection.connection_id
        or named.revision_id != current.revision_id
    ):
        raise _invalid("members", CONSTRAINT_MEMBER_REVISION_NOT_OF_CONNECTION)
    if not served:
        raise _invalid("members", CONSTRAINT_MEMBER_KIND_NOT_SERVED)
    pinned = named.settings
    if pinned.pin_id != settings.pin_id:
        raise _invalid("pin_id", CONSTRAINT_MEMBER_PIN_MISMATCH)
    if pinned.gateway_model != settings.gateway_model:
        raise _invalid("gateway_model", CONSTRAINT_MEMBER_MODEL_MISMATCH)
    if pinned.billing != settings.billing:
        raise _invalid("billing", CONSTRAINT_MEMBER_BILLING_MISMATCH)
