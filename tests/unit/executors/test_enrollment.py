"""`EXEC2-ENROLL-01`: the enrollment grant, the exchange for a runner token, the agent's health and the
integration-authorisation mark (B2 section 11 items 2, 7 and 8, the server half).

No database: the repositories, the command ledger and the journal are stand-ins that record what they were
asked, so the properties that matter are visible -- a grant is stored only as a hash and shown once; it is
single-use, bound to its connection and valid for fifteen minutes; a new grant revokes the previous one; the
exchange gives a random runner token that nothing about the secret can recompute; a repeat by the same agent
process inside the window revokes that token and mints a fresh one, and any other process, the time after the
window and a token an administrator revoked are refused; a health report keeps closed enumerations only;
and no secret, hash or token reaches an event, a ledger outcome, an error detail or a repr. The same flows on
real rows are ``tests/integration/executors/test_enrollment.py``.
"""

from __future__ import annotations

import dataclasses
import hashlib
import hmac
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from auditmanager.executors import enrollment as enrollment_module
from auditmanager.executors import integration_mark as mark_module
from auditmanager.executors.agent_package import AgentPackage
from auditmanager.executors.enrollment import (
    ENROLLMENT_LIFETIME_SECONDS,
    EnrollmentPrincipal,
    authenticate_enrollment,
    TAG_LENGTH,
    exchange_key,
    generate_enrollment_secret,
    hash_enrollment_secret,
    instance_tag,
    issue_executor_enrollment,
    mint_runner_token,
    normalise_health_report,
    redeem_enrollment,
    report_runner_health,
)
from auditmanager.executors.enrollment_repository import (
    EnrollmentRecord,
    EnrollmentRepository,
    enrollment_state,
)
from auditmanager.executors.model import ConnectionRecord
from auditmanager.executors.runner import authenticate_runner, hash_token
from auditmanager.executors.runner_repository import RunnerTokenRecord, StoredToken
from auditmanager.ingest.public import CommandReplay, CommandStarted
from auditmanager.shared.errors import DomainError, ErrorCode

T0 = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
ADMIN = "usr_01M2545JSD15ETSNNV904X991K"
CONNECTION = "exc_01M2545JSD15ETSNNV904X991K"
OTHER_CONNECTION = "exc_01M2545JSD15ETSNNV904X991M"
INSTANCE = "agent-instance-0001"
SECRET_SHAPE = re.compile(r"ame_[0-9a-z]{8}_[A-Za-z0-9_-]{43}")
TOKEN_SHAPE = re.compile(r"amr_[0-9a-z]{8}_[A-Za-z0-9_-]{43}")
PACKAGE = AgentPackage(version="0.9.0", sha256="a" * 64, size_bytes=1, path=None)  # type: ignore[arg-type]


# -- stand-ins --------------------------------------------------------------------------------


class Clock:
    """The database clock, moved by a test."""

    def __init__(self) -> None:
        self.now = T0

    def advance(self, **delta: int) -> None:
        self.now += timedelta(**delta)


class FakeLedger:
    def __init__(self, replay: dict[str, Any] | None = None) -> None:
        self.replay = replay
        self.began: list[tuple[str, str]] = []
        self.succeeded: list[dict[str, Any]] = []

    def begin(self, session, *, command_type, idempotency_key, fingerprint):
        self.began.append((command_type, str(idempotency_key)))
        if self.replay is not None:
            return CommandReplay(command_id="cmd_replay", outcome=self.replay)  # type: ignore[arg-type]
        return CommandStarted(command_id="cmd_1")  # type: ignore[arg-type]

    def succeed(self, session, command_id, outcome) -> None:
        self.succeeded.append(dict(outcome))


class Journal:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def __call__(self, session, *, event_type, aggregate_type, aggregate_id, payload=None, **_) -> None:
        self.events.append({"event_type": event_type, "aggregate_type": aggregate_type,
                            "aggregate_id": aggregate_id, "payload": dict(payload or {})})

    def types(self) -> list[str]:
        return [event["event_type"] for event in self.events]


class FakeExecutors:
    def __init__(self, clock: Clock, *, kind: str = "pull", archived: bool = False,
                 revision: bool = True, exists: bool = True) -> None:
        self.clock, self.has_revision, self.exists = clock, revision, exists
        self.connection = ConnectionRecord(
            connection_id=CONNECTION, kind=kind, display_name="Claude", created_at=T0,
            created_by=ADMIN, archived_at=T0 if archived else None, archived_by=ADMIN if archived else None)
        self.locked: list[str] = []

    def get_connection(self, session, connection_id, *, lock=False):
        if lock:
            self.locked.append(connection_id)
        return self.connection if self.exists and connection_id == CONNECTION else None

    def current_revisions(self, session, connection_ids):
        return {connection_id: object() for connection_id in connection_ids} if self.has_revision else {}

    def archive(self) -> None:
        self.connection = dataclasses.replace(self.connection, archived_at=self.clock.now, archived_by=ADMIN)


class FakeEnrollments:
    """``EnrollmentRepository`` in memory. The hash is kept apart from the records, as the real one does."""

    def __init__(self, clock: Clock) -> None:
        self.clock = clock
        self.rows: dict[str, EnrollmentRecord] = {}
        self.hashes: dict[str, bytes] = {}
        self.health: dict[str, dict[str, Any]] = {}
        self.online: list[str] = []
        self.sequence = 0
        self.runner: "FakeRunner | None" = None

    def _stamp(self, record: EnrollmentRecord) -> EnrollmentRecord:
        return dataclasses.replace(record, read_at=self.clock.now)

    def insert_enrollment(self, session, *, connection_id, secret_prefix, secret_hash, lifetime_seconds,
                          actor_uid):
        pending = [row for row in self.rows.values()
                   if row.connection_id == connection_id and row.redeemed_at is None
                   and row.revoked_at is None]
        assert not pending, "ux_executor_enrollment_pending: one unredeemed, unrevoked grant per connection"
        self.sequence += 1
        record = EnrollmentRecord(
            enrollment_id=f"exen_{self.sequence:026d}", connection_id=connection_id,
            secret_prefix=secret_prefix, created_at=self.clock.now, created_by=actor_uid,
            expires_at=self.clock.now + timedelta(seconds=lifetime_seconds), redeemed_at=None,
            runner_token_id=None, revoked_at=None, revoked_by=None, read_at=self.clock.now)
        self.rows[record.enrollment_id] = record
        self.hashes[record.enrollment_id] = secret_hash
        return record

    def revoke_unredeemed(self, session, connection_id, *, actor_uid):
        revoked = []
        for key, row in list(self.rows.items()):
            if row.connection_id == connection_id and row.redeemed_at is None and row.revoked_at is None:
                self.rows[key] = dataclasses.replace(row, revoked_at=self.clock.now, revoked_by=actor_uid)
                revoked.append((key, row.expires_at > self.clock.now))
        return revoked

    def get_enrollment(self, session, enrollment_id, *, lock=False):
        row = self.rows.get(enrollment_id)
        return None if row is None else self._stamp(row)

    def by_prefix(self, session, secret_prefix):
        for key, row in self.rows.items():
            if row.secret_prefix == secret_prefix:
                return self._stamp(row), self.hashes[key]
        return None

    def list_for_connection(self, session, connection_id, *, limit=10):
        rows = [self._stamp(row) for row in self.rows.values() if row.connection_id == connection_id]
        return sorted(rows, key=lambda row: row.enrollment_id, reverse=True)[:limit]

    def mark_redeemed(self, session, enrollment_id, token_id):
        row = self.rows[enrollment_id]
        if row.redeemed_at is not None or row.revoked_at is not None or row.expires_at <= self.clock.now:
            return False
        assert self.clock.now <= row.expires_at, "ck_executor_enrollment_redeemed_in_window"
        self.rows[enrollment_id] = dataclasses.replace(
            row, redeemed_at=self.clock.now, runner_token_id=token_id)
        return True

    def set_current_token(self, session, enrollment_id, token_id):
        row = self.rows[enrollment_id]
        if row.redeemed_at is None:
            return False
        self.rows[enrollment_id] = dataclasses.replace(row, runner_token_id=token_id)
        return True

    def prefixes_starting(self, session, start):
        assert self.runner is not None
        return {row.token_prefix for row in self.runner.tokens.values() if row.token_prefix.startswith(start)}

    def online_tokens(self, session, connection_id):
        return list(self.online)

    def store_health(self, session, token_id, **report):
        if token_id not in self.known_tokens:
            return None
        self.health[token_id] = report
        return self.clock.now

    known_tokens: set[str] = set()


class FakeRunner:
    """``RunnerRepository`` in memory: the three token methods the exchange and the seam use."""

    def __init__(self, clock: Clock) -> None:
        self.clock = clock
        self.tokens: dict[str, RunnerTokenRecord] = {}
        self.hashes: dict[str, bytes] = {}
        self.inserted: list[dict[str, Any]] = []
        self.seen: list[str] = []

    def insert_token(self, session, *, connection_id, token_prefix, token_hash, expires_in_days, actor_uid):
        assert all(row.token_prefix != token_prefix for row in self.tokens.values()), "uq prefix"
        assert token_hash not in self.hashes.values(), "uq hash"
        record = RunnerTokenRecord(
            token_id=f"ern_{len(self.tokens) + 1:026d}", connection_id=connection_id,
            token_prefix=token_prefix, created_at=self.clock.now, created_by=actor_uid,
            expires_at=self.clock.now + timedelta(days=expires_in_days), revoked_at=None, revoked_by=None,
            last_seen_at=None, last_seen_address=None)
        self.tokens[record.token_id] = record
        self.hashes[record.token_id] = token_hash
        self.inserted.append({"connection_id": connection_id, "actor_uid": actor_uid,
                              "expires_in_days": expires_in_days, "token_prefix": token_prefix})
        return record

    def get_token(self, session, token_id, *, lock=False):
        return self.tokens.get(token_id)

    def token_by_prefix(self, session, token_prefix):
        for token_id, record in self.tokens.items():
            if record.token_prefix == token_prefix:
                usable = record.revoked_at is None and record.expires_at > self.clock.now
                return StoredToken(token_id, record.connection_id, self.hashes[token_id], usable)
        return None

    def touch_token(self, session, token_id, address, **_) -> None:
        self.seen.append(token_id)

    def revoke_token(self, session, token_id, *, actor_uid):
        self.tokens[token_id] = dataclasses.replace(
            self.tokens[token_id], revoked_at=self.clock.now, revoked_by=actor_uid)
        return self.tokens[token_id]

    def revoke(self, token_id: str) -> None:
        """An administrator's revocation."""
        self.revoke_token(None, token_id, actor_uid=ADMIN)


class World:
    """One connection, one clock, and the stand-ins wired together."""

    def __init__(self, **connection: Any) -> None:
        self.clock = Clock()
        self.executors = FakeExecutors(self.clock, **connection)
        self.grants = FakeEnrollments(self.clock)
        self.runner = FakeRunner(self.clock)
        self.grants.runner = self.runner
        self.ledger = FakeLedger()
        self.journal = Journal()

    def issue(self, key: str = "issue-1", *, roles=("admin",), origin="https://stand.example",
              package=lambda: PACKAGE, **extra: Any):
        return issue_executor_enrollment(
            None, connection_id=CONNECTION, roles=roles, idempotency_key=key, actor_uid=ADMIN,  # type: ignore[arg-type]
            configured_origin=origin, executors=self.executors,  # type: ignore[arg-type]
            repository=self.grants, commands=self.ledger, package_source=package,  # type: ignore[arg-type]
            journal=self.journal, **extra)

    def principal(self, secret: str) -> EnrollmentPrincipal | None:
        return authenticate_enrollment(None, secret, self.grants)  # type: ignore[arg-type]

    def redeem(self, principal: EnrollmentPrincipal, instance: str = INSTANCE):
        return redeem_enrollment(
            None, principal, runner_instance_id=instance, executors=self.executors,  # type: ignore[arg-type]
            repository=self.grants, runner=self.runner, journal=self.journal)  # type: ignore[arg-type]


def refusal(call, *args: Any, **kwargs: Any) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call(*args, **kwargs)
    return caught.value


def details(error: DomainError) -> dict[str, Any]:
    return dict(error.detail_fields)


def everything_said(world: World, *extra: Any) -> str:
    """Every string the stand-ins were given or the module returned that a log or an audit trail could hold."""
    return repr([world.journal.events, world.ledger.began, world.ledger.succeeded, extra])


# -- the secret and the token derived from it -------------------------------------------------


def test_a_secret_has_the_shape_the_edge_and_the_secret_scanners_expect() -> None:
    value, prefix = generate_enrollment_secret()
    assert SECRET_SHAPE.fullmatch(value) and value.startswith(prefix + "_") and len(prefix) == 12
    assert len(value) == 56, "the contract's IssuedExecutorEnrollment.secret is 56 characters"
    assert len({generate_enrollment_secret()[0] for _ in range(50)}) == 50


def test_only_a_one_way_hash_is_derived_from_the_secret_and_it_is_not_the_exchange_key() -> None:
    value, _ = generate_enrollment_secret()
    assert hash_enrollment_secret(value) == hashlib.sha256(value.encode()).digest()
    assert exchange_key(value) != hash_enrollment_secret(value), "the stored hash cannot derive the token"
    assert exchange_key(value) == exchange_key(value) and len(exchange_key(value)) == 32


def test_an_instance_tag_is_stable_per_instance_and_unrelated_across_instances_and_grants() -> None:
    key = exchange_key(generate_enrollment_secret()[0])
    tag = instance_tag(key, INSTANCE)
    assert re.fullmatch(r"[0-9a-z]{7}", tag) and len(tag) == TAG_LENGTH
    assert instance_tag(key, INSTANCE) == tag
    assert instance_tag(key, "agent-instance-0002") != tag
    assert instance_tag(exchange_key(generate_enrollment_secret()[0]), INSTANCE) != tag


def test_a_minted_token_is_random_in_the_shape_of_a_runner_token_and_carries_only_the_tag_in_its_prefix() -> None:
    tag = instance_tag(exchange_key(generate_enrollment_secret()[0]), INSTANCE)
    value, prefix = mint_runner_token(tag, set())  # type: ignore[misc]
    assert TOKEN_SHAPE.fullmatch(value) and len(value) == 56 and value.startswith(prefix + "_")
    assert prefix.startswith("amr_" + tag) and len(prefix) == 12
    values = {mint_runner_token(tag, set())[0] for _ in range(50)}  # type: ignore[index]
    assert len(values) == 50, "nothing about the 256 random bits is fixed by the tag, the grant or the instance"
    assert len({value[13:] for value in values}) == 50


def test_a_minted_token_takes_a_free_slot_and_none_is_left_after_thirty_six() -> None:
    tag = "abcdefg"
    taken: set[str] = set()
    for _ in range(36):
        _, prefix = mint_runner_token(tag, taken)  # type: ignore[misc]
        assert prefix not in taken and prefix.startswith("amr_" + tag)
        taken.add(prefix)
    assert len(taken) == 36 and mint_runner_token(tag, taken) is None
    assert mint_runner_token("hijklmn", taken) is not None, "another instance's slots are its own"


def test_an_issued_enrollment_and_a_redeemed_token_never_print_their_values() -> None:
    world = World()
    issued = world.issue()
    assert issued.secret not in repr(issued) and issued.command not in repr(issued)
    redeemed = world.redeem(world.principal(issued.secret))  # type: ignore[arg-type]
    assert redeemed.value not in repr(redeemed)
    principal = world.principal(issued.secret)
    assert principal is not None and repr(principal.exchange_key) not in repr(principal)
    assert issued.secret not in repr(principal)


# -- issuing a grant --------------------------------------------------------------------------


def test_a_grant_is_stored_as_a_hash_for_fifteen_minutes_and_shown_once() -> None:
    world = World()
    issued = world.issue()
    record = issued.record
    assert world.grants.hashes[record.enrollment_id] == hash_enrollment_secret(issued.secret)
    assert issued.secret.encode() not in b"".join(world.grants.hashes.values())
    assert record.secret_prefix == issued.secret[:12] and record.state == "pending"
    assert record.expires_at - record.created_at == timedelta(seconds=ENROLLMENT_LIFETIME_SECONDS) == timedelta(minutes=15)
    assert record.created_by == ADMIN and record.connection_id == CONNECTION
    assert issued.package == PACKAGE and issued.command.count(issued.secret) == 1
    assert world.ledger.began == [("issue_executor_enrollment", "issue-1")]
    assert world.ledger.succeeded == [{"enrollment_id": record.enrollment_id}]
    assert world.executors.locked == [CONNECTION], "the connection is locked before its grants are touched"


def test_no_secret_hash_or_command_reaches_the_journal_or_the_ledger() -> None:
    world = World()
    issued = world.issue()
    said = everything_said(world)
    assert issued.secret not in said and issued.command not in said
    assert issued.secret[:12] not in said, "not even the prefix: an event names the grant by its identity"
    assert hash_enrollment_secret(issued.secret).hex() not in said
    assert world.journal.types() == ["executor.enrollment_issued"]
    event = world.journal.events[0]
    assert event["aggregate_type"] == "ExecutorEnrollment"
    assert event["aggregate_id"] == issued.record.enrollment_id
    assert event["payload"] == {"connection_id": CONNECTION, "actor_uid": ADMIN}


def test_a_repeat_of_the_key_cannot_show_the_secret_again() -> None:
    world = World()
    world.issue()
    world.ledger.replay = {"enrollment_id": "exen_x"}
    before = len(world.grants.rows)
    error = refusal(world.issue)
    assert error.code is ErrorCode.CONFLICT and details(error) == {"conflict_reason": "enrollment_shown_once"}
    assert len(world.grants.rows) == before and world.journal.types() == ["executor.enrollment_issued"]


def test_only_an_administrator_issues_a_grant_and_nothing_is_begun_for_anyone_else() -> None:
    world = World()
    for roles in ((), ("expert",)):
        error = refusal(world.issue, roles=roles)
        assert error.code is ErrorCode.PERMISSION_DENIED and details(error) == {"required_capability": "role:admin"}
    assert world.ledger.began == [] and world.grants.rows == {}


@pytest.mark.parametrize(("connection", "code", "detail"), [
    ({"exists": False}, ErrorCode.NOT_FOUND, {"aggregate_type": "ExecutorConnection"}),
    ({"archived": True}, ErrorCode.CONFLICT, {"conflict_reason": "connection_archived"}),
    ({"kind": "http_api"}, ErrorCode.VALIDATION_FAILED, {"field": "kind", "constraint": "kind_not_pull"}),
    ({"kind": "ssh_command"}, ErrorCode.VALIDATION_FAILED, {"field": "kind", "constraint": "kind_not_pull"}),
    ({"revision": False}, ErrorCode.CONFLICT, {"conflict_reason": "no_revision"}),
])
def test_a_grant_is_refused_for_a_connection_that_cannot_take_an_agent(
    connection: dict[str, Any], code: ErrorCode, detail: dict[str, str],
) -> None:
    world = World(**connection)
    error = refusal(world.issue)
    assert error.code is code and details(error) == detail
    assert world.grants.rows == {} and world.journal.events == [] and world.ledger.succeeded == []


def test_a_grant_is_redeemed_at_the_one_instant_that_decides_its_window() -> None:
    """``mark_redeemed`` read ``clock_timestamp()`` twice, in the ``WHERE`` and in the ``SET``: a grant that
    expired between the two was written ``redeemed_at > expires_at`` and the CHECK made it a 500. The clock is
    read once, in a materialised CTE, and that value is both the test and the stamp. (The race itself needs a
    database: ``tests/integration/executors/test_enrollment.py``.)"""

    class Recording:
        def __init__(self) -> None:
            self.statements: list[tuple[str, dict[str, Any]]] = []

        def execute(self, statement: Any, params: dict[str, Any]) -> Any:
            self.statements.append((" ".join(str(statement).split()), dict(params)))
            return type("Result", (), {"rowcount": 1})()

    session = Recording()
    assert EnrollmentRepository().mark_redeemed(session, "exen_X", "ern_T") is True  # type: ignore[arg-type]
    (sql, params), = session.statements
    assert params == {"id": "exen_X", "token": "ern_T"}
    assert sql.count("clock_timestamp()") == 1, "one read of the clock, not one per use"
    assert sql.startswith("WITH moment AS MATERIALIZED (SELECT clock_timestamp() AS t) UPDATE executor_enrollment")
    assert "redeemed_at = moment.t" in sql and "expires_at > moment.t" in sql, "the test and the stamp are one instant"
    assert "redeemed_at IS NULL AND revoked_at IS NULL" in sql


def test_an_image_without_a_package_or_a_stand_without_an_origin_issues_nothing() -> None:
    world = World()

    def no_package() -> AgentPackage:
        raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency="agent_package")

    error = refusal(world.issue, package=no_package)
    assert error.code is ErrorCode.DEPENDENCY_UNAVAILABLE and details(error) == {"dependency": "agent_package"}
    for origin in ("not an origin", None, ""):
        began = len(world.ledger.began)
        error = refusal(world.issue, origin=origin)
        assert error.code is ErrorCode.DEPENDENCY_UNAVAILABLE and details(error) == {"dependency": "public_origin"}
        assert world.grants.rows == {} and world.journal.events == []
        assert len(world.ledger.began) == began, "not even the idempotency key is recorded: it is still free"


def test_a_new_grant_revokes_the_previous_unredeemed_one_and_the_old_secret_stops_working() -> None:
    world = World()
    first = world.issue("issue-1")
    world.clock.advance(minutes=3)
    second = world.issue("issue-2")
    old = world.grants.rows[first.record.enrollment_id]
    assert old.state == "revoked" and old.revoked_by == ADMIN
    pending = [row for row in world.grants.rows.values() if row.state == "pending"]
    assert [row.enrollment_id for row in pending] == [second.record.enrollment_id]
    assert world.principal(first.secret) is None, "a revoked grant is the one None"
    assert world.principal(second.secret) is not None
    revoked = [event for event in world.journal.events if event["event_type"] == "executor.enrollment_revoked"]
    assert [event["aggregate_id"] for event in revoked] == [first.record.enrollment_id]
    assert revoked[0]["payload"] == {"connection_id": CONNECTION, "actor_uid": ADMIN, "reason": "superseded"}


def test_an_expired_unredeemed_grant_is_closed_for_the_index_but_stays_expired_and_is_not_journaled() -> None:
    world = World()
    first = world.issue("issue-1")
    world.clock.advance(minutes=16)
    world.issue("issue-2")
    closed = world.grants.rows[first.record.enrollment_id]
    assert closed.revoked_at is not None and closed.state == "expired"
    assert "executor.enrollment_revoked" not in world.journal.types()


def test_a_redeemed_grant_is_not_revoked_by_the_next_one() -> None:
    world = World()
    first = world.issue("issue-1")
    world.redeem(world.principal(first.secret))  # type: ignore[arg-type]
    world.issue("issue-2")
    assert world.grants.rows[first.record.enrollment_id].state == "redeemed"
    assert "executor.enrollment_revoked" not in world.journal.types()


def test_moving_an_agent_is_allowed_and_journaled_only_when_one_is_online() -> None:
    world = World()
    world.issue("issue-1")
    assert "executor.agent_move_requested" not in world.journal.types()
    world.grants.online = ["ern_new", "ern_old"]
    issued = world.issue("issue-2")
    assert issued.secret and "executor.agent_move_requested" in world.journal.types()
    move = next(e for e in world.journal.events if e["event_type"] == "executor.agent_move_requested")
    assert move["aggregate_type"] == "ExecutorConnection" and move["aggregate_id"] == CONNECTION
    assert move["payload"] == {"connection_id": CONNECTION, "token_id": "ern_new", "actor_uid": ADMIN,
                               "reason": "online_agent"}


def test_the_listed_grants_carry_a_derived_state_and_no_secret() -> None:
    world = World()
    first = world.issue("issue-1")
    world.clock.advance(minutes=1)
    second = world.issue("issue-2")
    listed = enrollment_module.enrollments_of(None, CONNECTION, world.grants, limit=10)  # type: ignore[arg-type]
    assert [row.enrollment_id for row in listed] == [second.record.enrollment_id, first.record.enrollment_id]
    assert [row.state for row in listed] == ["pending", "revoked"]
    assert not any(hasattr(row, name) for row in listed for name in ("secret", "secret_hash", "hash"))


@pytest.mark.parametrize(("redeemed", "revoked", "expires", "now", "state"), [
    (None, None, T0 + timedelta(minutes=15), T0, "pending"),
    (None, None, T0, T0, "expired"),
    (T0, None, T0 + timedelta(minutes=15), T0 + timedelta(hours=1), "redeemed"),
    (None, T0, T0 + timedelta(minutes=15), T0, "revoked"),
    (None, T0 + timedelta(minutes=20), T0 + timedelta(minutes=15), T0 + timedelta(minutes=30), "expired"),
])
def test_the_state_of_a_grant_is_derived_in_one_order(
    redeemed: datetime | None, revoked: datetime | None, expires: datetime, now: datetime, state: str,
) -> None:
    assert enrollment_state(redeemed_at=redeemed, revoked_at=revoked, expires_at=expires, now=now) == state


# -- authenticating a secret ------------------------------------------------------------------


class SpyStore:
    def __init__(self, found=None) -> None:
        self.found, self.reads = found, []

    def by_prefix(self, session, prefix):
        self.reads.append(prefix)
        return self.found


@pytest.mark.parametrize("presented", [
    "", "am2.payload.tag", "amr_abcd1234_" + "x" * 43, "ame_short", "Bearer x",
    "ame_ABCDEFGH_" + "x" * 43, "ame_abcdefgh_" + "x" * 42, "ame_abcdefgh_" + "x" * 44,
    "ame_abcdefgh-" + "x" * 43, "ame_abcdefgh_" + "x" * 42 + "\n",
])
def test_a_wrong_shape_a_runner_token_or_a_users_credential_costs_no_read(presented: str) -> None:
    store = SpyStore()
    assert authenticate_enrollment(None, presented, store) is None  # type: ignore[arg-type]
    assert store.reads == []


def test_a_known_secret_authenticates_to_its_grant_and_its_connection() -> None:
    world = World()
    issued = world.issue()
    principal = world.principal(issued.secret)
    assert principal is not None
    assert (principal.enrollment_id, principal.connection_id) == (issued.record.enrollment_id, CONNECTION)
    assert principal.exchange_key == exchange_key(issued.secret)


def test_the_right_prefix_with_the_wrong_secret_is_the_same_none_as_an_unknown_one() -> None:
    world = World()
    issued = world.issue()
    forged = issued.secret[:12] + "_" + "z" * 43
    assert world.principal(forged) is None
    unknown = "ame_zzzzzzzz_" + "z" * 43
    assert world.principal(unknown) is None


def test_the_hash_is_compared_in_constant_time_and_a_miss_takes_the_same_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = World()
    issued = world.issue()
    calls: list[tuple[bytes, bytes]] = []
    real = hmac.compare_digest

    def spy(a, b):
        calls.append((a, b))
        return real(a, b)

    monkeypatch.setattr(enrollment_module.hmac, "compare_digest", spy)
    world.principal(issued.secret)
    world.principal("ame_zzzzzzzz_" + "z" * 43)
    assert len(calls) == 2 and all(len(a) == len(b) == 32 for a, b in calls)


def test_an_expired_or_revoked_unredeemed_grant_is_the_same_none_as_a_wrong_secret() -> None:
    world = World()
    issued = world.issue()
    world.clock.advance(seconds=ENROLLMENT_LIFETIME_SECONDS)
    assert world.principal(issued.secret) is None
    fresh = World()
    second = fresh.issue()
    fresh.issue("issue-2")
    assert fresh.principal(second.secret) is None


def test_a_redeemed_grant_is_still_authenticated_so_that_the_exchange_can_say_so() -> None:
    world = World()
    issued = world.issue()
    world.redeem(world.principal(issued.secret))  # type: ignore[arg-type]
    world.clock.advance(hours=3)
    assert world.principal(issued.secret) is not None


# -- the exchange (B2 section 11, item 2: the command is run on a host and the agent registers) -----


def test_the_exchange_issues_a_runner_token_of_the_grants_connection_and_marks_the_grant_redeemed() -> None:
    world = World()
    issued = world.issue()
    redeemed = world.redeem(world.principal(issued.secret))  # type: ignore[arg-type]
    assert TOKEN_SHAPE.fullmatch(redeemed.value)
    record = redeemed.record
    assert record.connection_id == CONNECTION and record.created_by == ADMIN
    assert record.token_prefix == redeemed.value[:12] and record.revoked_at is None
    assert record.token_prefix[4:4 + TAG_LENGTH] == instance_tag(exchange_key(issued.secret), INSTANCE)
    assert world.runner.hashes[record.token_id] == hash_token(redeemed.value), "only the hash is stored"
    assert redeemed.value.encode() not in b"".join(world.runner.hashes.values())
    grant = world.grants.rows[issued.record.enrollment_id]
    assert grant.state == "redeemed" and grant.runner_token_id == record.token_id
    assert world.journal.types() == ["executor.enrollment_issued", "executor.enrollment_redeemed"]
    assert world.journal.events[-1]["payload"] == {"connection_id": CONNECTION, "token_id": record.token_id}
    assert redeemed.value not in everything_said(world) and issued.secret not in everything_said(world)
    assert world.executors.locked[-1] == CONNECTION


def test_the_token_the_exchange_yields_authenticates_as_any_runner_token_does() -> None:
    world = World()
    issued = world.issue()
    redeemed = world.redeem(world.principal(issued.secret))  # type: ignore[arg-type]
    principal = authenticate_runner(None, redeemed.value, address="10.0.0.9", repository=world.runner)  # type: ignore[arg-type]
    assert principal is not None
    assert (principal.token_id, principal.connection_id) == (redeemed.record.token_id, CONNECTION)
    assert world.runner.seen == [redeemed.record.token_id]


def test_a_repeat_by_the_same_instance_inside_the_window_revokes_the_first_token_and_mints_a_fresh_one() -> None:
    world = World()
    issued = world.issue()
    first = world.redeem(world.principal(issued.secret))  # type: ignore[arg-type]
    world.clock.advance(minutes=5)
    again = world.redeem(world.principal(issued.secret))  # type: ignore[arg-type]
    assert TOKEN_SHAPE.fullmatch(again.value)
    assert again.value != first.value and again.record.token_id != first.record.token_id
    assert again.record.token_prefix != first.record.token_prefix
    assert again.record.token_prefix[4:4 + TAG_LENGTH] == first.record.token_prefix[4:4 + TAG_LENGTH]
    assert len(world.runner.inserted) == 2 and world.runner.hashes[again.record.token_id] == hash_token(again.value)
    old = world.runner.tokens[first.record.token_id]
    assert old.revoked_at == world.clock.now and old.revoked_by == ADMIN, "the token it never saw stops working"
    assert authenticate_runner(None, first.value, address=None, repository=world.runner) is None  # type: ignore[arg-type]
    assert authenticate_runner(None, again.value, address=None, repository=world.runner) is not None  # type: ignore[arg-type]
    assert world.grants.rows[issued.record.enrollment_id].runner_token_id == again.record.token_id
    assert world.grants.rows[issued.record.enrollment_id].state == "redeemed"
    assert world.journal.types()[-3:] == [
        "executor.enrollment_redeemed", "executor.runner_token_revoked", "executor.enrollment_redeemed"]
    revoked, repeated = world.journal.events[-2], world.journal.events[-1]
    assert revoked["aggregate_type"] == "ExecutorConnection" and revoked["aggregate_id"] == CONNECTION
    assert revoked["payload"] == {"connection_id": CONNECTION, "token_id": first.record.token_id,
                                  "reason": "enrollment_repeat"}
    assert repeated["payload"] == {"connection_id": CONNECTION, "token_id": again.record.token_id,
                                   "reason": "repeat"}
    assert again.value not in everything_said(world) and first.value not in everything_said(world)


def test_the_same_instance_may_repeat_again_and_only_the_latest_token_is_ever_in_force() -> None:
    world = World()
    issued = world.issue()
    tokens = [world.redeem(world.principal(issued.secret))]  # type: ignore[arg-type]
    for _ in range(3):
        world.clock.advance(minutes=1)
        tokens.append(world.redeem(world.principal(issued.secret)))  # type: ignore[arg-type]
    live = [token for token in tokens
            if authenticate_runner(None, token.value, address=None, repository=world.runner)]  # type: ignore[arg-type]
    assert live == [tokens[-1]]
    assert len({token.record.token_prefix for token in tokens}) == 4


def test_a_grant_hands_one_instance_at_most_thirty_six_tokens() -> None:
    world = World()
    issued = world.issue()
    principal = world.principal(issued.secret)
    for _ in range(36):
        world.redeem(principal)  # type: ignore[arg-type]
    error = refusal(world.redeem, principal)
    assert error.code is ErrorCode.CONFLICT and details(error) == {"conflict_reason": "enrollment_redeemed"}
    assert len(world.runner.inserted) == 36
    assert sum(1 for token in world.runner.tokens.values() if token.revoked_at is None) == 1


def test_a_repeat_changes_nothing_for_an_instance_that_is_not_the_one_it_was_given_to() -> None:
    world = World()
    issued = world.issue()
    first = world.redeem(world.principal(issued.secret))  # type: ignore[arg-type]
    refusal(world.redeem, world.principal(issued.secret), "agent-instance-0002")
    assert world.runner.tokens[first.record.token_id].revoked_at is None, "a stranger revokes nothing"
    assert world.grants.rows[issued.record.enrollment_id].runner_token_id == first.record.token_id
    assert authenticate_runner(None, first.value, address=None, repository=world.runner) is not None  # type: ignore[arg-type]


def test_another_instance_after_a_redemption_is_refused_and_issues_nothing() -> None:
    world = World()
    issued = world.issue()
    world.redeem(world.principal(issued.secret))  # type: ignore[arg-type]
    error = refusal(world.redeem, world.principal(issued.secret), "agent-instance-0002")
    assert error.code is ErrorCode.CONFLICT and details(error) == {"conflict_reason": "enrollment_redeemed"}
    assert len(world.runner.inserted) == 1


def test_a_repeat_after_the_window_is_refused_even_by_the_same_instance() -> None:
    world = World()
    issued = world.issue()
    world.redeem(world.principal(issued.secret))  # type: ignore[arg-type]
    world.clock.advance(seconds=ENROLLMENT_LIFETIME_SECONDS + 1)
    error = refusal(world.redeem, world.principal(issued.secret))
    assert error.code is ErrorCode.CONFLICT and details(error) == {"conflict_reason": "enrollment_redeemed"}


def test_a_repeat_after_the_token_was_revoked_is_refused() -> None:
    world = World()
    issued = world.issue()
    redeemed = world.redeem(world.principal(issued.secret))  # type: ignore[arg-type]
    world.runner.revoke(redeemed.record.token_id)
    error = refusal(world.redeem, world.principal(issued.secret))
    assert error.code is ErrorCode.CONFLICT and details(error) == {"conflict_reason": "enrollment_redeemed"}


def test_a_grant_that_expired_or_was_revoked_after_authentication_is_authentication_required() -> None:
    world = World()
    issued = world.issue()
    principal = world.principal(issued.secret)
    world.clock.advance(seconds=ENROLLMENT_LIFETIME_SECONDS)
    error = refusal(world.redeem, principal)
    assert error.code is ErrorCode.AUTHENTICATION_REQUIRED and world.runner.inserted == []
    other = World()
    second = other.issue()
    principal = other.principal(second.secret)
    other.issue("issue-2")
    error = refusal(other.redeem, principal)
    assert error.code is ErrorCode.AUTHENTICATION_REQUIRED and other.runner.inserted == []


def test_an_archived_connection_takes_no_agent_whether_the_grant_is_pending_or_redeemed() -> None:
    world = World()
    issued = world.issue()
    principal = world.principal(issued.secret)
    world.executors.archive()
    error = refusal(world.redeem, principal)
    assert error.code is ErrorCode.CONFLICT and details(error) == {"conflict_reason": "connection_archived"}
    assert world.runner.inserted == [] and world.grants.rows[issued.record.enrollment_id].state == "pending"
    later = World()
    second = later.issue()
    later.redeem(later.principal(second.secret))  # type: ignore[arg-type]
    later.executors.archive()
    error = refusal(later.redeem, later.principal(second.secret))
    assert details(error) == {"conflict_reason": "connection_archived"}


def test_a_grant_of_one_connection_never_yields_a_token_of_another() -> None:
    world = World()
    issued = world.issue()
    principal = world.principal(issued.secret)
    assert principal is not None
    foreign = dataclasses.replace(principal, connection_id=OTHER_CONNECTION)
    assert refusal(world.redeem, foreign).code is ErrorCode.AUTHENTICATION_REQUIRED
    assert world.runner.inserted == []


@pytest.mark.parametrize("instance", ["", "short", "x" * 65, "has space 1", "semi;colon1", "ünicode-0001", "a" * 8 + "\n"])
def test_an_instance_id_outside_the_declared_form_is_refused_before_anything_is_read(instance: str) -> None:
    world = World()
    issued = world.issue()
    principal = world.principal(issued.secret)
    error = refusal(world.redeem, principal, instance)
    assert error.code is ErrorCode.VALIDATION_FAILED
    assert details(error) == {"field": "runner_instance_id", "constraint": "pattern"}
    assert world.runner.inserted == []


def test_a_grant_serves_one_agent_process_even_when_two_ask_at_once_in_turn() -> None:
    world = World()
    issued = world.issue()
    principal = world.principal(issued.secret)
    a = world.redeem(principal, "agent-instance-aaaa")  # type: ignore[arg-type]
    assert refusal(world.redeem, principal, "agent-instance-bbbb").code is ErrorCode.CONFLICT
    again = world.redeem(principal, "agent-instance-aaaa")  # type: ignore[arg-type]
    assert again.value != a.value and world.runner.tokens[a.record.token_id].revoked_at is not None
    assert refusal(world.redeem, principal, "agent-instance-bbbb").code is ErrorCode.CONFLICT


# -- health (B2 section 11, item 8, the server half) --------------------------------------------

REPORT = dict(
    agent_version="0.9.0",
    clis=[{"cli": "claude", "installed": True, "version": "2.1.3", "auth_state": "valid"},
          {"cli": "codex", "installed": False, "auth_state": "unknown"}],
    concurrency=1, execution_profile="command", features=["images"],
)


def test_a_valid_report_is_kept_as_closed_enumerations_and_bounded_strings() -> None:
    report = normalise_health_report(**REPORT)
    assert report.agent_version == "0.9.0" and report.concurrency == 1
    assert report.execution_profile == "command" and report.features == ("images",)
    assert [dict(item) for item in report.clis] == [
        {"cli": "claude", "installed": True, "auth_state": "valid", "version": "2.1.3"},
        {"cli": "codex", "installed": False, "auth_state": "unknown"},
    ]


def test_anything_the_report_carries_beyond_the_declared_fields_is_dropped_not_stored() -> None:
    noisy = dict(REPORT, clis=[{
        "cli": "claude", "installed": True, "auth_state": "login_required", "version": "2.1.3",
        "token": "sk-live-secret", "path": "/root/.claude/credentials.json", "account": "a@b.c",
    }])
    stored = normalise_health_report(**noisy)
    assert set(stored.clis[0]) == {"cli", "installed", "auth_state", "version"}
    assert "sk-live-secret" not in repr(stored) and "credentials" not in repr(stored)


@pytest.mark.parametrize(("change", "field", "constraint"), [
    ({"agent_version": ""}, "agent_version", "pattern"),
    ({"agent_version": "../0.9.0"}, "agent_version", "pattern"),
    ({"agent_version": "0.9.0\n"}, "agent_version", "pattern"),
    ({"agent_version": "v" * 65}, "agent_version", "pattern"),
    ({"agent_version": None}, "agent_version", "pattern"),
    ({"concurrency": 0}, "concurrency", "range"),
    ({"concurrency": 17}, "concurrency", "range"),
    ({"concurrency": True}, "concurrency", "range"),
    ({"concurrency": "1"}, "concurrency", "range"),
    ({"execution_profile": "shell"}, "execution_profile", "enum"),
    ({"features": ["images", "images"]}, "features", "unique"),
    ({"features": ["gpu"]}, "features", "enum"),
    ({"features": ["images"] * 9}, "features", "length"),
    ({"features": "images"}, "features", "length"),
    ({"clis": "claude"}, "clis", "length"),
    ({"clis": [{"cli": "claude", "installed": True, "auth_state": "valid"}] * 2}, "clis", "unique"),
    ({"clis": [{"cli": "gemini", "installed": True, "auth_state": "valid"}]}, "clis", "enum"),
    ({"clis": [{"cli": "claude", "installed": "yes", "auth_state": "valid"}]}, "clis", "type"),
    ({"clis": [{"cli": "claude", "installed": True, "auth_state": "logged in as root"}]}, "clis", "type"),
    ({"clis": [{"cli": "claude", "installed": True, "auth_state": "valid", "version": "1 2"}]}, "clis", "pattern"),
    ({"clis": [{"cli": "claude", "installed": False, "auth_state": "valid"}]}, "clis", "not_installed"),
    ({"clis": [{"cli": "claude", "installed": False, "auth_state": "unknown", "version": "1.0"}]}, "clis", "not_installed"),
    ({"clis": ["claude"]}, "clis", "type"),
])
def test_a_report_outside_the_closed_vocabulary_is_a_422_that_names_the_field(
    change: dict[str, Any], field: str, constraint: str,
) -> None:
    error = refusal(normalise_health_report, **dict(REPORT, **change))
    assert error.code is ErrorCode.VALIDATION_FAILED
    assert details(error) == {"field": field, "constraint": constraint}
    assert "root" not in str(error) and "claude" not in str(error)


def test_more_than_eight_clients_are_refused() -> None:
    clis = [{"cli": "claude", "installed": True, "auth_state": "valid"}] * 9
    assert details(refusal(normalise_health_report, **dict(REPORT, clis=clis))) == {
        "field": "clis", "constraint": "length"}


def test_the_report_replaces_what_the_token_held_and_a_token_that_is_gone_is_unauthenticated() -> None:
    world = World()
    world.grants.known_tokens = {"ern_1"}
    recorded = report_runner_health(None, "ern_1", repository=world.grants, **REPORT)  # type: ignore[arg-type]
    assert recorded == T0 and world.grants.health["ern_1"]["agent_version"] == "0.9.0"
    world.clock.advance(minutes=1)
    report_runner_health(None, "ern_1", repository=world.grants, **dict(REPORT, concurrency=2))  # type: ignore[arg-type]
    assert world.grants.health["ern_1"]["concurrency"] == 2
    error = refusal(report_runner_health, None, "ern_gone", repository=world.grants, **REPORT)
    assert error.code is ErrorCode.AUTHENTICATION_REQUIRED


def test_a_refused_report_stores_nothing() -> None:
    world = World()
    world.grants.known_tokens = {"ern_1"}
    refusal(report_runner_health, None, "ern_1", repository=world.grants,
            **dict(REPORT, execution_profile="shell"))
    assert world.grants.health == {}


# -- the integration-authorisation mark (R-149b) --------------------------------------------------


class FakeMarks:
    def __init__(self, clock: Clock) -> None:
        self.clock, self.current = clock, None

    def marks_of(self, session, connection_ids):
        return {} if self.current is None else {CONNECTION: self.current}

    def set_mark(self, session, connection_id, *, actor_uid):
        if self.current is not None:
            return False
        self.current = mark_module.IntegrationMark(CONNECTION, self.clock.now, actor_uid)
        return True

    def clear_mark(self, session, connection_id):
        had, self.current = self.current is not None, None
        return had


def _mark(world: World, marks: FakeMarks, authorised: bool, key: str = "mark-1", roles=("admin",)):
    return mark_module.set_integration_authorisation(
        None, connection_id=CONNECTION, authorised=authorised, roles=roles, idempotency_key=key,  # type: ignore[arg-type]
        actor_uid=ADMIN, executors=world.executors, repository=marks, commands=world.ledger,  # type: ignore[arg-type]
        journal=world.journal)


def test_setting_and_clearing_the_mark_is_journaled_and_a_no_op_is_not() -> None:
    world = World()
    marks = FakeMarks(world.clock)
    mark = _mark(world, marks, True)
    assert mark is not None and mark.authorised_by == ADMIN and mark.authorised_at == T0
    again = _mark(world, marks, True, "mark-2")
    assert again == mark, "setting a set mark answers the connection as it stands"
    assert world.journal.types() == ["executor.integration_authorised"]
    assert _mark(world, marks, False, "mark-3") is None
    assert _mark(world, marks, False, "mark-4") is None
    assert world.journal.types() == ["executor.integration_authorised", "executor.integration_authorisation_cleared"]
    assert all(event["payload"] == {"connection_id": CONNECTION, "actor_uid": ADMIN}
               for event in world.journal.events)
    assert [began[0] for began in world.ledger.began] == ["set_executor_integration_authorisation"] * 4


@pytest.mark.parametrize(("connection", "code", "detail"), [
    ({"exists": False}, ErrorCode.NOT_FOUND, {"aggregate_type": "ExecutorConnection"}),
    ({"archived": True}, ErrorCode.CONFLICT, {"conflict_reason": "connection_archived"}),
    ({"kind": "http_api"}, ErrorCode.VALIDATION_FAILED, {"field": "kind", "constraint": "kind_not_pull"}),
])
def test_the_mark_is_refused_for_a_connection_that_cannot_hold_it(
    connection: dict[str, Any], code: ErrorCode, detail: dict[str, str],
) -> None:
    world = World(**connection)
    marks = FakeMarks(world.clock)
    error = refusal(_mark, world, marks, True)
    assert error.code is code and details(error) == detail
    assert marks.current is None and world.journal.events == []


def test_only_an_administrator_sets_the_mark_and_it_implies_no_other_status() -> None:
    world = World()
    marks = FakeMarks(world.clock)
    assert refusal(_mark, world, marks, True, roles=("expert",)).code is ErrorCode.PERMISSION_DENIED
    assert world.ledger.began == [] and marks.current is None
    _mark(world, marks, True)
    assert world.grants.health == {} and world.grants.rows == {}, "the mark touches no health, token or grant"


def test_a_repeat_of_the_mark_key_answers_the_mark_as_it_stands_and_changes_nothing() -> None:
    world = World()
    marks = FakeMarks(world.clock)
    _mark(world, marks, True)
    world.ledger.replay = {"connection_id": CONNECTION}
    before = list(world.journal.events)
    assert _mark(world, marks, False, "mark-1") is not None, "a replay does not clear what it recorded"
    assert world.journal.events == before
