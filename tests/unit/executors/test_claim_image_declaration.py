"""`CMP-EXEC-IMAGES-01`: the claim's declared ``max_images`` reaches the two statements that hand out a task.

The statements themselves (the gate in SQL) are proven on real rows in
``tests/integration/executors/test_claim_image_gating.py``. This file holds the rest of the chain
without a database: an absent value means one, a declared value is passed on unchanged to both
the fresh claim and the redelivery, and a value outside 1..8 is refused before a statement runs.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.executors.runner import RunnerPrincipal, claim_task
from auditmanager.executors.runner_repository import (
    DEFAULT_CLAIM_IMAGES,
    MAX_CLAIM_IMAGES,
    RunnerRepository,
    _image_count,
)


class _Session:
    def __enter__(self) -> _Session:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def commit(self) -> None:
        return None


class _Executors:
    def current_revisions(self, session: Any, connection_ids: Any) -> dict[str, Any]:
        return {}


class _Recording:
    """A repository that hands out nothing and remembers what each statement was asked."""

    def __init__(self) -> None:
        self.asked: list[tuple[str, int]] = []

    def sweep(self, session: Any, connection_id: str) -> None: ...

    def clear_terminal_payloads(self, session: Any, **kwargs: Any) -> None: ...

    def held_claims(self, session: Any, token_id: str) -> int:
        return 0

    def redeliver(self, session: Any, **kwargs: Any) -> None:
        self.asked.append(("redeliver", kwargs["max_images"]))

    def claim_next(self, session: Any, **kwargs: Any) -> None:
        self.asked.append(("claim_next", kwargs["max_images"]))


def _claim(max_images: int | None, **extra: Any) -> list[tuple[str, int]]:
    rows = _Recording()
    claim_task(_Session, RunnerPrincipal("ern_a", "exc_a"), wait_seconds=0, executors=_Executors(),
               repository=rows, max_images=max_images, **extra)  # type: ignore[arg-type]
    return rows.asked


def test_a_claim_that_declares_nothing_is_a_claim_for_one_image() -> None:
    assert (DEFAULT_CLAIM_IMAGES, MAX_CLAIM_IMAGES) == (1, 8)
    assert _claim(None) == [("redeliver", 1), ("claim_next", 1)]


@pytest.mark.parametrize("declared", [1, 2, 5, 8])
def test_a_declared_value_reaches_both_the_redelivery_and_the_fresh_claim(declared: int) -> None:
    assert _claim(declared) == [("redeliver", declared), ("claim_next", declared)]


@pytest.mark.parametrize("bad", [0, -1, 9, True, 2.0, "3"])
def test_a_value_outside_one_to_eight_is_refused_before_any_statement(bad: Any) -> None:
    store = RunnerRepository()

    class _NoSql:
        def execute(self, *args: Any, **kwargs: Any) -> Any:
            raise AssertionError("no statement may run for an undeclarable max_images")

    with pytest.raises(ValueError):
        store.claim_next(_NoSql(), connection_id="exc_a", token_id="ern_a", lease_seconds=1,  # type: ignore[arg-type]
                         max_images=bad)
    with pytest.raises(ValueError):
        store.redeliver(_NoSql(), token_id="ern_a", lease_seconds=1, max_images=bad)  # type: ignore[arg-type]


def test_the_sql_count_of_a_payload_fails_closed_on_a_malformed_member() -> None:
    sql = _image_count("p")
    assert "p.payload" in sql and "jsonb_array_length" in sql
    assert f"ELSE {MAX_CLAIM_IMAGES + 1} END" in sql, "a non-array member counts as more than any claim serves"
    assert "payload" in _image_count() and "p." not in _image_count()
