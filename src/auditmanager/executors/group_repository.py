"""The only writer and reader of the ``executor_group*`` and ``executor_routing_*`` tables (migration ``0047``).

Statements only: the rules live in ``groups.py`` and ``group_commands.py``. Every method takes the caller's session
and never commits.

What is written, and by whom the database holds the rest:

* ``executor_group`` is inserted, archived once (``archived_at`` and ``archived_by`` are write-once) and has its
  ``rotation_cursor`` advanced; its name and creation are frozen by a trigger and the row is never deleted;
* ``executor_group_revision`` and ``executor_group_member`` are inserted and never changed (``am_immutable_row``); the
  revision chain, an archived group and the homogeneity of a member are checked again by triggers. A revision is
  written with ``member_count`` -- the number of members it is made with -- in the same transaction as those members:
  the database refuses a member beyond the count and refuses to commit a revision that holds fewer, so the membership
  is closed once the revision exists;
* ``executor_routing_rule_revision`` is inserted and never changed (``am_append_only``);
* ``executor_routing_mode_event`` is read (an empty journal is ``legacy``) and, since ``EXEC2-CUTOVER-01``, appended
  to by :meth:`insert_mode_event` under the journal's advisory lock (:meth:`lock_mode_journal`), the same lock
  ``am_check_executor_routing_mode_event`` takes; the number written is the highest plus one, as the trigger requires.

Numbering is taken under a lock first -- the group row for a group's revisions, the same advisory key the trigger
takes for a work kind's rules -- so two administrators cannot take one number; the unique keys are the backstop.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any, Final

from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.executors.groups import (
    GroupMemberRecord,
    GroupRecord,
    GroupRevisionRecord,
    GroupSettings,
    MemberRequest,
    ModeState,
    RuleRecord,
)
from auditmanager.shared.identity import (
    ExecutorGroupId,
    ExecutorGroupRevisionId,
    ExecutorRoutingModeEventId,
    ExecutorRoutingRuleRevisionId,
)

__all__ = ["GroupRepository"]

_GROUP_COLUMNS: Final = (
    "group_id, display_name, rotation_cursor, created_at, created_by, archived_at, archived_by, system_managed")
_REVISION_COLUMNS: Final = (
    "group_revision_id, group_id, revision_no, pin_id, gateway_model, billing, input_per_mtok_usd, "
    "output_per_mtok_usd, strategy, created_at, created_by"
)
#: ``r.`` -- the rule joined to its group revision, for the group the rule names.
_RULE_COLUMNS: Final = (
    "r.rule_revision_id, r.work_kind, r.rule_no, r.group_revision_id, g.group_id, r.set_at, r.set_by"
)
_RULE_FROM: Final = (
    "executor_routing_rule_revision r JOIN executor_group_revision g "
    "ON g.group_revision_id = r.group_revision_id"
)

#: The Run states after which a Run waits for nothing (``RUN_STATES`` of ``0002``) and the comparison job states in
#: which a job is live (``JOB_LIVE`` of ``0040``). A ``pending`` binding on a finished Run or job is history, not a wait.
_RUN_FINISHED: Final = "('published', 'partial', 'failed', 'cancelled')"
_JOB_LIVE: Final = "('queued', 'running', 'paused')"
_PENDING_COUNT = text(
    "SELECT "
    "(SELECT count(*) FROM audit_run arun JOIN executor_group_revision grev "
    "ON grev.group_revision_id = arun.executor_group_revision_id "
    f"WHERE grev.group_id = :group_id AND arun.binding_state = 'pending' AND arun.state NOT IN {_RUN_FINISHED}) "
    "+ (SELECT count(*) FROM comparison_ai_job cjob JOIN executor_group_revision grev "
    "ON grev.group_revision_id = cjob.executor_group_revision_id "
    f"WHERE grev.group_id = :group_id AND cjob.binding_state = 'pending' AND cjob.state IN {_JOB_LIVE})"
)


def _group(row: Mapping[str, Any]) -> GroupRecord:
    return GroupRecord(**{name: row[name] for name in (
        "group_id", "display_name", "rotation_cursor", "created_at", "created_by", "archived_at", "archived_by",
        "system_managed")})


def _member(row: Mapping[str, Any]) -> GroupMemberRecord:
    return GroupMemberRecord(
        connection_id=row["connection_id"], connection_revision_id=row["connection_revision_id"],
        tie_break_order=row["tie_break_order"],
    )


def _revision(row: Mapping[str, Any], members: Sequence[GroupMemberRecord]) -> GroupRevisionRecord:
    return GroupRevisionRecord(
        **{name: row[name] for name in (
            "group_revision_id", "group_id", "revision_no", "pin_id", "gateway_model", "billing",
            "input_per_mtok_usd", "output_per_mtok_usd", "strategy", "created_at", "created_by")},
        members=tuple(members),
    )


def _rule(row: Mapping[str, Any]) -> RuleRecord:
    return RuleRecord(**{name: row[name] for name in (
        "rule_revision_id", "work_kind", "rule_no", "group_revision_id", "group_id", "set_at", "set_by")})


class GroupRepository:
    """Stateless; every method takes the caller's session and never commits."""

    # -- groups ------------------------------------------------------------------------------------------

    def lock_name(self, session: Session, display_name: str) -> None:
        """Serialise two creations of one name (without regard to case) until the transaction ends, so the check
        below and the insert are one decision. The unique index on ``lower(display_name)`` is the backstop."""
        session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                        {"key": f"executor_group_name:{display_name.lower()}"})

    def name_in_use(self, session: Session, display_name: str) -> bool:
        """Does an **active** group hold this name? ``lower`` is the function the unique index applies."""
        return bool(session.execute(text(
            "SELECT EXISTS (SELECT 1 FROM executor_group WHERE lower(display_name) = lower(:name) "
            "AND archived_at IS NULL)"
        ), {"name": display_name}).scalar_one())

    def insert_group(self, session: Session, *, display_name: str, actor_uid: str) -> GroupRecord:
        row = session.execute(text(
            "INSERT INTO executor_group (group_id, display_name, created_by) VALUES (:id, :name, :actor) "
            f"RETURNING {_GROUP_COLUMNS}"
        ), {"id": str(ExecutorGroupId.new()), "name": display_name, "actor": actor_uid}).mappings().one()
        return _group(row)

    def active_group_names(self, session: Session) -> set[str]:
        """The names of the **active** groups, lower-cased as the unique index compares them (`EXEC2-CUTOVER-01`: the
        preview proposes a name no active group holds)."""
        return {str(row[0]) for row in session.execute(text(
            "SELECT lower(display_name) FROM executor_group WHERE archived_at IS NULL"
        )).all()}

    def get_group(self, session: Session, group_id: str, *, lock: bool = False) -> GroupRecord | None:
        """One group. ``lock`` takes the row lock that serialises its revisions, its archive and a rule that
        names it (the first lock of ADR-0026 decision 14's order that this lane takes)."""
        row = session.execute(text(
            f"SELECT {_GROUP_COLUMNS} FROM executor_group WHERE group_id = :id" + (" FOR UPDATE" if lock else "")
        ), {"id": group_id}).mappings().first()
        return None if row is None else _group(row)

    def list_groups(self, session: Session, *, limit: int = 500) -> list[GroupRecord]:
        """Active groups first, then archived ones; newest first inside each. The system groups of the hosts are not listed."""
        rows = session.execute(text(
            f"SELECT {_GROUP_COLUMNS} FROM executor_group WHERE NOT system_managed "
            "ORDER BY archived_at IS NOT NULL, created_at DESC, group_id DESC LIMIT :limit"
        ), {"limit": limit}).mappings().all()
        return [_group(row) for row in rows]

    def archive_group(self, session: Session, group_id: str, *, actor_uid: str) -> GroupRecord:
        """Archive once. The caller holds the group's row lock (``FOR UPDATE``, :meth:`get_group` with ``lock``) and has
        checked that no rule names it. The insert triggers of a revision, a member and a rule read the archive with
        ``FOR SHARE``, so they wait for that lock and see the archive."""
        row = session.execute(text(
            "UPDATE executor_group SET archived_at = clock_timestamp(), archived_by = :actor "
            f"WHERE group_id = :id AND archived_at IS NULL RETURNING {_GROUP_COLUMNS}"
        ), {"id": group_id, "actor": actor_uid}).mappings().one()
        return _group(row)

    def advance_rotation(self, session: Session, group_id: str) -> int:
        """Move the persisted tie-break rotation on by one and return its new value. Called by the dispatcher
        under the group's row lock each time it dispatches to a member of this group, so that members that tie
        on load take turns (:func:`~auditmanager.executors.group_selection.choose`)."""
        return int(session.execute(text(
            "UPDATE executor_group SET rotation_cursor = rotation_cursor + 1 WHERE group_id = :id "
            "RETURNING rotation_cursor"
        ), {"id": group_id}).scalar_one())

    def lock_connections(self, session: Session, connection_ids: Sequence[str]) -> set[str]:
        """Lock the named connections against a concurrent revision or archive until the transaction ends, in
        ascending ``connection_id`` (the order of ADR-0026 decision 14), and return those that exist. A share lock:
        two groups may be made over one connection at once, but a connection cannot get a new revision between the
        read of its current one and the group that snapshots it."""
        if not connection_ids:
            return set()
        rows = session.execute(text(
            "SELECT connection_id FROM executor_connection WHERE connection_id = ANY(:ids) "
            "ORDER BY connection_id FOR SHARE"
        ), {"ids": sorted(set(connection_ids))}).all()
        return {str(row[0]) for row in rows}

    # -- revisions ---------------------------------------------------------------------------------------

    def next_revision_no(self, session: Session, group_id: str) -> int:
        """The next number of the group's chain. The caller holds the group's row lock."""
        return int(session.execute(text(
            "SELECT COALESCE(MAX(revision_no), 0) + 1 FROM executor_group_revision WHERE group_id = :id"
        ), {"id": group_id}).scalar_one())

    def insert_revision(
        self, session: Session, *, group_id: str, revision_no: int, settings: GroupSettings,
        input_per_mtok_usd: Decimal, output_per_mtok_usd: Decimal, members: Sequence[MemberRequest],
        actor_uid: str,
    ) -> GroupRevisionRecord:
        """Write the revision and its members. Immutable from here on; the database checks the chain and, per member,
        the homogeneity again.

        The revision declares ``member_count`` = the number of members written here, and the members must follow in
        this transaction: the database refuses to commit a revision that holds a different number, and a member added
        later is refused."""
        row = session.execute(text(
            "INSERT INTO executor_group_revision (group_revision_id, group_id, revision_no, pin_id, "
            "gateway_model, billing, input_per_mtok_usd, output_per_mtok_usd, strategy, member_count, created_by) "
            "VALUES (:id, :group_id, :no, :pin, :model, :billing, :rate_in, :rate_out, :strategy, :member_count, "
            ":actor) "
            f"RETURNING {_REVISION_COLUMNS}"
        ), {"id": str(ExecutorGroupRevisionId.new()), "group_id": group_id, "no": revision_no,
            "pin": settings.pin_id, "model": settings.gateway_model, "billing": settings.billing,
            "rate_in": input_per_mtok_usd, "rate_out": output_per_mtok_usd,
            "strategy": settings.strategy, "member_count": len(members), "actor": actor_uid}).mappings().one()
        for member in members:
            session.execute(text(
                "INSERT INTO executor_group_member (group_revision_id, connection_id, connection_revision_id, "
                "tie_break_order) VALUES (:revision, :connection, :connection_revision, :tie)"
            ), {"revision": row["group_revision_id"], "connection": member.connection_id,
                "connection_revision": member.connection_revision_id, "tie": member.tie_break_order})
        stored = self._members(session, [row["group_revision_id"]])
        return _revision(row, stored.get(row["group_revision_id"], ()))

    def _members(
        self, session: Session, revision_ids: Sequence[str]
    ) -> dict[str, list[GroupMemberRecord]]:
        if not revision_ids:
            return {}
        rows = session.execute(text(
            "SELECT group_revision_id, connection_id, connection_revision_id, tie_break_order "
            "FROM executor_group_member WHERE group_revision_id = ANY(:ids) "
            "ORDER BY group_revision_id, tie_break_order NULLS LAST, connection_id"
        ), {"ids": list(revision_ids)}).mappings().all()
        found: dict[str, list[GroupMemberRecord]] = {}
        for row in rows:
            found.setdefault(row["group_revision_id"], []).append(_member(row))
        return found

    def get_revision(self, session: Session, group_revision_id: str) -> GroupRevisionRecord | None:
        row = session.execute(text(
            f"SELECT {_REVISION_COLUMNS} FROM executor_group_revision WHERE group_revision_id = :id"
        ), {"id": group_revision_id}).mappings().first()
        if row is None:
            return None
        return _revision(row, self._members(session, [group_revision_id]).get(group_revision_id, ()))

    def list_revisions(self, session: Session, group_id: str) -> list[GroupRevisionRecord]:
        """Every revision of the group with its members, newest first."""
        rows = session.execute(text(
            f"SELECT {_REVISION_COLUMNS} FROM executor_group_revision WHERE group_id = :id "
            "ORDER BY revision_no DESC"
        ), {"id": group_id}).mappings().all()
        members = self._members(session, [row["group_revision_id"] for row in rows])
        return [_revision(row, members.get(row["group_revision_id"], ())) for row in rows]

    def current_revisions(
        self, session: Session, group_ids: Sequence[str]
    ) -> dict[str, GroupRevisionRecord]:
        """The highest-numbered revision of each group that has one, with its members."""
        if not group_ids:
            return {}
        rows = session.execute(text(
            f"SELECT DISTINCT ON (group_id) {_REVISION_COLUMNS} FROM executor_group_revision "
            "WHERE group_id = ANY(:ids) ORDER BY group_id, revision_no DESC"
        ), {"ids": list(group_ids)}).mappings().all()
        members = self._members(session, [row["group_revision_id"] for row in rows])
        return {row["group_id"]: _revision(row, members.get(row["group_revision_id"], ())) for row in rows}

    # -- rules -------------------------------------------------------------------------------------------

    def lock_rule(self, session: Session, work_kind: str) -> None:
        """The advisory lock ``am_check_executor_routing_rule`` takes for the same work kind, taken first so the
        number read below is the number the trigger expects (the lock is re-entrant within the transaction)."""
        session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                        {"key": f"executor_routing_rule:{work_kind}"})

    def insert_rule(
        self, session: Session, *, work_kind: str, group_revision_id: str, actor_uid: str
    ) -> RuleRecord:
        """Append the next rule of the work kind. The caller holds the group's row lock (so the group is not being
        archived) and has called :meth:`lock_rule`."""
        number = int(session.execute(text(
            "SELECT COALESCE(MAX(rule_no), 0) + 1 FROM executor_routing_rule_revision WHERE work_kind = :kind"
        ), {"kind": work_kind}).scalar_one())
        rule_id = str(ExecutorRoutingRuleRevisionId.new())
        session.execute(text(
            "INSERT INTO executor_routing_rule_revision (rule_revision_id, work_kind, rule_no, "
            "group_revision_id, set_by) VALUES (:id, :kind, :no, :revision, :actor)"
        ), {"id": rule_id, "kind": work_kind, "no": number, "revision": group_revision_id, "actor": actor_uid})
        found = self.get_rule(session, rule_id)
        assert found is not None
        return found

    def get_rule(self, session: Session, rule_revision_id: str) -> RuleRecord | None:
        row = session.execute(text(
            f"SELECT {_RULE_COLUMNS} FROM {_RULE_FROM} WHERE r.rule_revision_id = :id"
        ), {"id": rule_revision_id}).mappings().first()
        return None if row is None else _rule(row)

    def current_rules(self, session: Session) -> list[RuleRecord]:
        """The current rule (highest ``rule_no``) of each work kind that has one, ordered by work kind."""
        rows = session.execute(text(
            f"SELECT DISTINCT ON (r.work_kind) {_RULE_COLUMNS} FROM {_RULE_FROM} "
            "ORDER BY r.work_kind, r.rule_no DESC"
        )).mappings().all()
        return [_rule(row) for row in rows]

    def current_rule(self, session: Session, work_kind: str) -> RuleRecord | None:
        row = session.execute(text(
            f"SELECT {_RULE_COLUMNS} FROM {_RULE_FROM} WHERE r.work_kind = :kind "
            "ORDER BY r.rule_no DESC LIMIT 1"
        ), {"kind": work_kind}).mappings().first()
        return None if row is None else _rule(row)

    # -- the routing mode ---------------------------------------------------------------------------------

    def lock_mode_journal(self, session: Session) -> None:
        """The advisory lock ``am_check_executor_routing_mode_event`` takes, taken first by every writer of the journal
        and by ``setExecutorRoute`` (`EXEC2-CUTOVER-01`), so that a route change and a mode change are serialised and
        two events cannot take one number. Held until the transaction ends; re-entrant within it."""
        session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended('executor_routing_mode_event', 0))"))

    def insert_mode_event(
        self, session: Session, *, mode: str, preview_digest: str | None, mapping: Sequence[Mapping[str, str]],
        actor_uid: str,
    ) -> tuple[ModeState, int]:
        """Append one event to the routing-mode journal and return the mode it makes current with its number.

        ``event_no`` is the highest number plus one, read in the same statement as the insert; the caller holds
        :meth:`lock_mode_journal`, so no other writer can take the number and the trigger's check passes. A ``rules``
        event carries the confirmed digest and the 1 to 6 entries of the mapping; a ``legacy`` event carries neither."""
        row = session.execute(text(
            "INSERT INTO executor_routing_mode_event (mode_event_id, event_no, mode, preview_digest, mapping, "
            "changed_by) SELECT :id, COALESCE(MAX(event_no), 0) + 1, :mode, CAST(:digest AS text), "
            "CAST(:mapping AS jsonb), :actor FROM executor_routing_mode_event "
            "RETURNING mode, mode_event_id, event_no, changed_at, changed_by"
        ), {"id": str(ExecutorRoutingModeEventId.new()), "mode": mode, "digest": preview_digest,
            "mapping": json.dumps([dict(entry) for entry in mapping], sort_keys=True), "actor": actor_uid},
        ).mappings().one()
        state = ModeState(
            mode=row["mode"], mode_event_id=row["mode_event_id"], changed_at=row["changed_at"],
            changed_by=row["changed_by"],
        )
        return state, int(row["event_no"])

    def current_mode(self, session: Session) -> ModeState:
        """The routing mode in force: the event with the highest ``event_no``; an empty journal is ``legacy``."""
        row = session.execute(text(
            "SELECT mode, mode_event_id, changed_at, changed_by FROM executor_routing_mode_event "
            "ORDER BY event_no DESC LIMIT 1"
        )).mappings().first()
        if row is None:
            return ModeState()
        return ModeState(
            mode=row["mode"], mode_event_id=row["mode_event_id"], changed_at=row["changed_at"],
            changed_by=row["changed_by"],
        )

    # -- waiting work -------------------------------------------------------------------------------------

    def pending_count(self, session: Session, group_id: str) -> int:
        """The Runs and comparison jobs admitted on any revision of the group that are still ``pending`` (not yet
        bound to a connection) and not finished. Read at the moment it is asked and stored nowhere."""
        return int(session.execute(_PENDING_COUNT, {"group_id": group_id}).scalar_one())
