"""Which member of a group would be chosen, and why one would not (`EXEC2-GROUP-STORE-01`, ADR-0026 decisions 10 and 14).

Pure: no SQL, no I/O, no clock. Two readers of the same fact share this module so that they cannot disagree:

* ``getExecutorGroupCapacity`` shows, per member, whether dispatch would choose it and, if not, the first reason
  (:func:`member_issue`);
* the dispatcher of ``EXEC2-GROUP-RUN-01`` and ``EXEC2-GROUP-CMP-01`` takes the members that are eligible and calls
  :func:`choose` under the group and member locks.

**Eligibility** (decision 14, in the order of the contract's ``ExecutorGroupMemberIssue``): the connection's
current revision is the snapshot the group revision holds; the connection is not archived; this release serves it;
its probe on the current key is ``ok``; for a ``pull`` connection a runner is online; and it has a free unit
(decision 1). The first that fails is the one reported.

**Selection** (``least_loaded``). Among the members that have a free unit, the one with the lowest
``used / capacity``. The ratio is compared by cross-multiplication in integers, so there is no division, no
float and no rounding, and a capacity of zero (which no stored revision has) is a member with no free unit and
is never divided by. Members that tie on the ratio are ordered by ``tie_break_order`` (a member without one
after those with one), then by ``connection_id``; the persisted rotation (``executor_group.rotation_cursor``)
picks the ``rotation mod n``-th of them. The same members, loads and rotation give the same answer, and the
caller advances the rotation by one under the group lock each time it dispatches, so equal members take turns.
When no member has a free unit the answer is ``None``: the work waits (decision 15), it is not sent anywhere.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from auditmanager.executors.model import GROUP_MEMBER_ISSUES

__all__ = [
    "ISSUE_AT_CAPACITY",
    "ISSUE_CONNECTION_ARCHIVED",
    "ISSUE_NOT_SERVED",
    "ISSUE_PROBE_NOT_OK",
    "ISSUE_REVISION_CHANGED",
    "ISSUE_RUNNER_OFFLINE",
    "GroupMember",
    "MemberFacts",
    "choose",
    "member_issue",
]

ISSUE_REVISION_CHANGED: Final[str] = "revision_changed"
ISSUE_CONNECTION_ARCHIVED: Final[str] = "connection_archived"
ISSUE_NOT_SERVED: Final[str] = "not_served"
ISSUE_PROBE_NOT_OK: Final[str] = "probe_not_ok"
ISSUE_RUNNER_OFFLINE: Final[str] = "runner_offline"
ISSUE_AT_CAPACITY: Final[str] = "at_capacity"


@dataclass(frozen=True, slots=True)
class GroupMember:
    """A member as :func:`choose` needs it: its connection and its optional tie-break order (1 to 16)."""

    connection_id: str
    tie_break_order: int | None = None


@dataclass(frozen=True, slots=True)
class MemberFacts:
    """What is true of one member right now. The caller reads the rows; this module decides.

    ``runner_online`` is ``True`` for a connection that is not a ``pull`` connection (it has no runner to be
    offline). ``capacity`` and ``used`` are the occupancy of decision 1: ``max_active_runs`` of the connection's
    current revision and the units in use.
    """

    connection_id: str
    tie_break_order: int | None
    revision_is_snapshot: bool
    archived: bool
    served: bool
    probed_ok: bool
    runner_online: bool
    capacity: int
    used: int

    @property
    def in_service(self) -> bool:
        """Counted in the group's capacity: not archived, and the revision is still the snapshot."""
        return self.revision_is_snapshot and not self.archived

    @property
    def has_free_unit(self) -> bool:
        return self.capacity > 0 and self.used < self.capacity

    def as_member(self) -> GroupMember:
        return GroupMember(self.connection_id, self.tie_break_order)


def member_issue(facts: MemberFacts) -> str | None:
    """Why dispatch would not choose this member now: the first of ``GROUP_MEMBER_ISSUES`` that applies, or ``None``.

    The order is the contract's: ``revision_changed``, ``connection_archived``, ``not_served``, ``probe_not_ok``,
    ``runner_offline``, ``at_capacity``. A member with an issue other than ``at_capacity`` is not eligible and is
    left out of :func:`choose`; one whose only issue is ``at_capacity`` is eligible and waits for a free unit.
    """
    failed = {
        ISSUE_REVISION_CHANGED: not facts.revision_is_snapshot,
        ISSUE_CONNECTION_ARCHIVED: facts.archived,
        ISSUE_NOT_SERVED: not facts.served,
        ISSUE_PROBE_NOT_OK: not facts.probed_ok,
        ISSUE_RUNNER_OFFLINE: not facts.runner_online,
        ISSUE_AT_CAPACITY: not facts.has_free_unit,
    }
    assert tuple(failed) == GROUP_MEMBER_ISSUES, "the issues are listed in the contract's order"
    return next((issue for issue, applies in failed.items() if applies), None)


def _order(member: GroupMember) -> tuple[bool, int, str]:
    return (member.tie_break_order is None, member.tie_break_order or 0, member.connection_id)


def choose(
    members: Sequence[GroupMember], used: Mapping[str, int], capacity: Mapping[str, int], rotation: int,
) -> str | None:
    """The ``connection_id`` of the member to dispatch to, or ``None`` when no member has a free unit.

    ``members`` are the eligible members (the caller has already left out those with an issue other than
    ``at_capacity``); ``used`` and ``capacity`` give each member's units in use and its capacity, keyed by
    ``connection_id``. A member missing from ``capacity`` has none (nothing is assumed), and one missing from
    ``used`` has none in use. A member is a candidate only while ``used < capacity``; a capacity lowered below
    what is in use makes it full, as decision 1 says, and never negative room.

    Among the candidates the lowest ``used / capacity`` wins, compared exactly. Candidates tied on it are
    ordered (``tie_break_order``, then ``connection_id``) and the ``rotation mod n``-th is taken.

    Pure and total: no division is performed, so no capacity can divide by zero. It refuses, with
    ``ValueError`` and no silent repair, what a caller must never pass: a connection twice in ``members``, a
    negative number of units in use or a negative rotation.
    """
    if rotation < 0:
        raise ValueError("the rotation is a counter and is not negative")
    seen: set[str] = set()
    best: list[GroupMember] = []
    best_used = best_capacity = 0
    for member in members:
        if member.connection_id in seen:
            raise ValueError("a connection is a member of a group once")
        seen.add(member.connection_id)
        in_use = used.get(member.connection_id, 0)
        total = capacity.get(member.connection_id, 0)
        if in_use < 0:
            raise ValueError("units in use are not negative")
        if total <= 0 or in_use >= total:
            continue
        if not best:
            best, best_used, best_capacity = [member], in_use, total
            continue
        # in_use / total  versus  best_used / best_capacity, both denominators positive.
        left, right = in_use * best_capacity, best_used * total
        if left < right:
            best, best_used, best_capacity = [member], in_use, total
        elif left == right:
            best.append(member)
    if not best:
        return None
    ordered = sorted(best, key=_order)
    return ordered[rotation % len(ordered)].connection_id
