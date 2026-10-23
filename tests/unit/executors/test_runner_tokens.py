"""`EXEC-PULL-01`: a runner token's shape, hash and authentication (``executors/runner.py``).

No database: the repository is a stand-in that records what it was asked, so the properties
that matter are visible -- a wrong shape costs no read, the comparison is constant-time, a
revoked or expired token is the same ``None`` as a wrong one, and the value is in no repr.
"""

from __future__ import annotations

import hashlib
import hmac
import re

import pytest

from auditmanager.executors import runner
from auditmanager.executors.runner import (
    IssuedToken,
    authenticate_runner,
    generate_token,
    hash_token,
)
from auditmanager.executors.runner_repository import RunnerTokenRecord, StoredToken

SHAPE = re.compile(r"amr_[0-9a-z]{8}_[A-Za-z0-9_-]{43}")


class FakeStore:
    def __init__(self, stored: StoredToken | None = None) -> None:
        self.stored = stored
        self.reads: list[str] = []
        self.touched: list[tuple[str, str | None]] = []

    def token_by_prefix(self, session, prefix: str):
        self.reads.append(prefix)
        return self.stored

    def touch_token(self, session, token_id: str, address: str | None, **_: object) -> None:
        self.touched.append((token_id, address))


def _stored(value: str, *, usable: bool = True) -> StoredToken:
    return StoredToken("ern_X", "exc_Y", hash_token(value), usable)


def test_a_token_has_the_shape_the_edge_and_the_secret_scanners_expect() -> None:
    value, prefix = generate_token()
    assert SHAPE.fullmatch(value) and value.startswith(prefix + "_") and len(prefix) == 12
    assert len({generate_token()[0] for _ in range(50)}) == 50


def test_only_a_one_way_hash_is_derived_from_the_value() -> None:
    value, _ = generate_token()
    assert hash_token(value) == hashlib.sha256(value.encode()).digest()
    assert value.encode() not in hash_token(value)


def test_an_issued_token_never_prints_its_value() -> None:
    value, prefix = generate_token()
    record = RunnerTokenRecord("ern_X", "exc_Y", prefix, None, "usr_Z", None, None, None, None, None)  # type: ignore[arg-type]
    issued = IssuedToken(record=record, value=value)
    assert value not in repr(issued) and value not in str(issued)


@pytest.mark.parametrize("presented", [
    "", "am2.payload.tag", "amr_short", "Bearer x", "amr_ABCDEFGH_" + "x" * 43,
    "amr_abcdefgh_" + "x" * 42, "amr_abcdefgh_" + "x" * 44, "amr_abcdefgh-" + "x" * 43,
])
def test_a_wrong_shape_costs_no_read(presented: str) -> None:
    store = FakeStore()
    assert authenticate_runner(None, presented, address="1.2.3.4", repository=store) is None  # type: ignore[arg-type]
    assert store.reads == [] and store.touched == []


def test_a_known_token_authenticates_and_is_seen() -> None:
    value, prefix = generate_token()
    store = FakeStore(_stored(value))
    principal = authenticate_runner(None, value, address="10.0.0.9", repository=store)  # type: ignore[arg-type]
    assert principal is not None and (principal.token_id, principal.connection_id) == ("ern_X", "exc_Y")
    assert store.reads == [prefix] and store.touched == [("ern_X", "10.0.0.9")]


def test_the_address_is_cut_to_what_the_column_holds() -> None:
    value, _ = generate_token()
    store = FakeStore(_stored(value))
    authenticate_runner(None, value, address="a" * 200, repository=store)  # type: ignore[arg-type]
    assert len(store.touched[0][1] or "") == 64


def test_the_wrong_secret_behind_a_real_prefix_is_refused_and_not_seen() -> None:
    value, prefix = generate_token()
    forged = prefix + "_" + "z" * 43
    store = FakeStore(_stored(value))
    assert authenticate_runner(None, forged, address=None, repository=store) is None  # type: ignore[arg-type]
    assert store.touched == []


@pytest.mark.parametrize("known", [False, True], ids=["unknown prefix", "revoked or expired"])
def test_an_unknown_and_an_unusable_token_are_the_same_answer(known: bool) -> None:
    value, _ = generate_token()
    store = FakeStore(_stored(value, usable=False) if known else None)
    assert authenticate_runner(None, value, address="1.1.1.1", repository=store) is None  # type: ignore[arg-type]
    assert store.touched == []


def test_the_hash_is_compared_in_constant_time(monkeypatch: pytest.MonkeyPatch) -> None:
    value, _ = generate_token()
    calls: list[tuple[bytes, bytes]] = []
    real = hmac.compare_digest

    def spy(a, b):
        calls.append((a, b))
        return real(a, b)

    monkeypatch.setattr(runner.hmac, "compare_digest", spy)
    authenticate_runner(None, value, address=None, repository=FakeStore(_stored(value)))  # type: ignore[arg-type]
    authenticate_runner(None, value, address=None, repository=FakeStore(None))  # type: ignore[arg-type]
    assert len(calls) == 2 and all(len(a) == len(b) == 32 for a, b in calls)
