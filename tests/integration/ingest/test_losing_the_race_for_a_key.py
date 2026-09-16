"""Where criterion 9's safety actually lives: the collision, not the pre-read.

``CommandRepository.begin`` reads for an existing claim before inserting. `W6-CERT` nulled that
pre-read and the whole criterion-9 suite stayed green — because the safety is carried by the
``UNIQUE`` constraint on ``(command_type, idempotency_key)`` and by the recovery that reads
the winner back after the insert collides. The pre-read is an optimisation: it saves a
doomed insert and a wasted identifier.

That recovery had no test. Every existing ``idempotency_key_stale`` case is about an
**abandoned** key, which is a different branch reached a different way. So the lines that
make a repeated request safe under concurrency were the lines nothing exercised.

Reaching that recovery needs the pre-read to **miss while the row exists**, and commit
ordering alone cannot produce it: under ``READ COMMITTED`` each statement sees fresh data,
so a pre-read issued after the winner commits simply finds the winner. The first version of
these tests ordered two real sessions by commit and proved nothing — both mutations below
stayed green, because every call was taking the pre-read path the mutations do not touch.

So the stale read is arranged directly: ``find`` returns ``None`` exactly once, for the
losing caller's pre-read, while the winner's row is really in the database and really
committed. That is a simulation of the timing window, not of the collision — the insert
that follows is a real insert, the ``UNIQUE`` violation is the database's, and the read-back
is the production one. Threads would reproduce the window authentically and flakily; it is
microseconds wide, and a test that passes because it lost a race is not evidence.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.ingest.commands import CommandRecord, CommandReplay, CommandStarted, CommandRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import IdempotencyKey, PayloadFingerprint

COMMAND_TYPE = "start_audit_run"


class _StaleOnce(CommandRepository):
    """A repository whose first ``find`` misses, as a concurrent caller's really would.

    Subclassed rather than patched: ``CommandRepository`` uses ``slots``, and a subclass
    keeps the substitution visible in the diff instead of hidden in a fixture. Only the
    pre-read is affected -- the second call, inside the recovery, is the real one.
    """

    finds = 0

    def find(self, *args, **kwargs):  # type: ignore[override]
        type(self).finds += 1
        if type(self).finds == 1:
            return None
        return super().find(*args, **kwargs)

    def __init__(self) -> None:
        super().__init__()
        type(self).finds = 0


def _key() -> IdempotencyKey:
    return IdempotencyKey(f"w8-race-{uuid.uuid4()}")


def _fingerprint(value: str = "a" * 64) -> PayloadFingerprint:
    return PayloadFingerprint(value)


def _claims(session: Session) -> int:
    return session.execute(
        text("SELECT count(*) FROM command_record WHERE command_type = :t"),
        {"t": COMMAND_TYPE},
    ).scalar_one()


def test_the_race_really_is_a_race(session_factory: sessionmaker[Session]) -> None:
    """The precondition: uncontested, the same call claims the key and starts.

    Without it, a refusal below could be caused by anything — a malformed key, a missing
    table — and would still look like the collision path working.
    """
    store = CommandRepository()
    key = _key()
    with session_factory() as solo:
        outcome = store.begin(
            solo,
            command_type=COMMAND_TYPE,
            idempotency_key=key,
            fingerprint=_fingerprint(),
        )
        solo.commit()
        assert isinstance(outcome, CommandStarted), outcome
        assert _claims(solo) == 1


def _lose_the_race(store, a, b, key, fingerprint, *, winner_succeeds: bool):
    """Arrange a real collision and return what the loser was told.

    B claims the key and commits, so the row exists. A's pre-read is then made to miss
    once -- the stale read a concurrent caller would really have -- and everything after
    it is production code: a real insert, the database's own UNIQUE violation, and the
    recovery that reads the winner back.
    """
    started = store.begin(
        b, command_type=COMMAND_TYPE, idempotency_key=key, fingerprint=fingerprint
    )
    assert isinstance(started, CommandStarted), started
    if winner_succeeds:
        store.succeed(b, started.command_id, {"run_id": "run_" + "0" * 26})
    b.commit()

    loser = _StaleOnce()
    outcome = loser.begin(
        a, command_type=COMMAND_TYPE, idempotency_key=key, fingerprint=fingerprint
    )
    assert loser.finds >= 2, (
        "the recovery never read the winner back, so the insert did not collide and this "
        "test is not exercising the branch it claims to"
    )
    return started, outcome


def test_the_loser_of_a_race_against_a_running_command_is_told_to_retry(
    session_factory: sessionmaker[Session],
) -> None:
    """Winner still running: the loser gets the typed retryable refusal, not a start.

    This is the branch `W6-CERT` showed was load-bearing. A's pre-read has already missed,
    so the only thing between two callers and two commands under one key is the UNIQUE
    violation and the read-back after it.
    """
    store = CommandRepository()
    key = _key()

    with session_factory() as a, session_factory() as b:
        with pytest.raises(DomainError) as raised:
            _lose_the_race(store, a, b, key, _fingerprint(), winner_succeeds=False)
        assert raised.value.code is ErrorCode.IDEMPOTENCY_KEY_IN_PROGRESS, (
            "the caller that lost the race was not told it lost; two callers both "
            f"believing they started is what criterion 9 forbids: {raised.value.code}"
        )

    with session_factory() as check:
        assert _claims(check) == 1, (
            "the key carries more than one command record, so the UNIQUE constraint or "
            "the recovery after it did not hold"
        )


def test_the_loser_of_a_race_against_a_finished_command_is_replayed_its_outcome(
    session_factory: sessionmaker[Session],
) -> None:
    """Winner already succeeded: the loser gets the winner's result, not a second run.

    The other half of the same collision, and the half that makes a repeat safe rather
    than merely refused. Answering from A's own aborted insert, or starting a second
    command, would both create work under a key that already has a result.
    """
    store = CommandRepository()
    key = _key()

    with session_factory() as a, session_factory() as b:
        started, outcome = _lose_the_race(
            store, a, b, key, _fingerprint(), winner_succeeds=True
        )
        assert isinstance(outcome, CommandReplay), (
            f"the loser was not answered from the winner's record: {outcome!r}"
        )
        assert outcome.command_id == started.command_id, (
            "the loser was answered from some other record than the winner's"
        )
        assert outcome.outcome["run_id"] == "run_" + "0" * 26

    with session_factory() as check:
        assert _claims(check) == 1


def test_the_losers_transaction_survives_losing(
    session_factory: sessionmaker[Session],
) -> None:
    """The SAVEPOINT is the reason the loser can be answered at all.

    Losing the key is a step that is allowed to fail. If the collision poisoned A's whole
    unit of work, A could not read the winner back, and a correct refusal would reach the
    caller as an aborted transaction instead.
    """
    store = CommandRepository()
    key = _key()

    with session_factory() as a, session_factory() as b:
        with pytest.raises(DomainError):
            _lose_the_race(store, a, b, key, _fingerprint(), winner_succeeds=False)

        assert a.execute(text("SELECT 1")).scalar_one() == 1, (
            "the losing session cannot be read from after the collision, so the failed "
            "insert took the enclosing transaction with it"
        )


def test_a_different_payload_under_the_same_key_is_refused_not_replayed(
    session_factory: sessionmaker[Session],
) -> None:
    """The recovery answers *what happened*, not merely *that something did*.

    A loser carrying a different payload must not be handed the winner's outcome: that
    would let two different requests share one result under one key.
    """
    store = CommandRepository()
    key = _key()

    with session_factory() as a, session_factory() as b:
        assert store.find(a, command_type=COMMAND_TYPE, idempotency_key=key) is None
        store.begin(
            b,
            command_type=COMMAND_TYPE,
            idempotency_key=key,
            fingerprint=_fingerprint("a" * 64),
        )
        b.commit()

        with pytest.raises(DomainError) as raised:
            store.begin(
                a,
                command_type=COMMAND_TYPE,
                idempotency_key=key,
                fingerprint=_fingerprint("b" * 64),
            )
        assert raised.value.code.value == "idempotency_key_reuse", raised.value.code
