"""`EXEC-PAR-QUEUE-01` -- ``AUDITMANAGER_WORKER_SLOTS``: strict, once, and by name in the stack.

Container-free: ``settings.load`` reads a mapping, and the composition root never dials the
closed local port it is given (an engine and an object-store client are lazy).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from auditmanager.bootstrap.public import ConfigurationError, build_worker_runtime
from auditmanager.bootstrap.settings import (
    DEFAULT_WORKER_SLOTS,
    MAX_WORKER_SLOTS,
    WORKER_SLOTS_ENV,
    load,
)
from auditmanager.workers.__main__ import serve

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ROOT / "infra/deploy/compose.server.yml"
ALPHA_ENV = ROOT / "infra/deploy/env/alpha.env.example"

_WORKER = {
    "DATABASE_URL": "postgresql+psycopg://user:password@127.0.0.1:9/nothing",
    "S3_ENDPOINT_URL": "http://127.0.0.1:9", "S3_REGION": "us-east-1",
    "S3_ACCESS_KEY_ID": "an-access-key", "S3_SECRET_ACCESS_KEY": "a-secret-key",
    "S3_BUCKET": "a-bucket", "EXECUTION_ROLE": "worker",
}


def test_the_variable_is_named_as_the_task_names_it() -> None:
    assert WORKER_SLOTS_ENV == "AUDITMANAGER_WORKER_SLOTS"
    assert (DEFAULT_WORKER_SLOTS, MAX_WORKER_SLOTS) == (1, 16)


def test_unset_is_one_slot_and_one_run_at_a_time() -> None:
    assert load(_WORKER).worker_slots == 1


@pytest.mark.parametrize("value", ["1", "2", "4", "9", "16", " 4 "])
def test_a_whole_number_from_one_to_sixteen_is_taken_as_written(value: str) -> None:
    assert load(_WORKER | {WORKER_SLOTS_ENV: value}).worker_slots == int(value)


@pytest.mark.parametrize("value", [
    "0", "17", "-1", "100", "99999999999999999999",      # out of range, never clamped
    "", "   ",                                           # present and blank is not "unset"
    "+4", "04", "4.0", "1e1", "0x4", "4 4", "4,0", "four", "٤", "１６",   # not written plainly
])
def test_anything_else_refuses_the_start_and_names_the_variable(value: str) -> None:
    with pytest.raises(ConfigurationError, match=WORKER_SLOTS_ENV):
        load(_WORKER | {WORKER_SLOTS_ENV: value})


def test_the_worker_process_refuses_to_start_and_registers_nothing(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``serve`` returns 2 from the configuration, before any connection or registration."""
    from auditmanager.workers import service

    def must_not_be_built(*args: object, **kwargs: object) -> None:
        raise AssertionError("a refused configuration built a worker service")

    monkeypatch.setattr(service, "WorkerService", must_not_be_built)
    assert serve(_WORKER | {WORKER_SLOTS_ENV: "17"}) == 2
    assert f"refusing to start: {WORKER_SLOTS_ENV} is 17" in capsys.readouterr().err


def test_the_runtime_hands_the_setting_to_the_service_and_sizes_the_pool_for_it() -> None:
    """One slot is the pool it always was (5 + 5); each further slot adds two connections."""
    one = build_worker_runtime(environ=dict(_WORKER))
    four = build_worker_runtime(environ=_WORKER | {WORKER_SLOTS_ENV: "4"})
    sixteen = build_worker_runtime(environ=_WORKER | {WORKER_SLOTS_ENV: "16"})
    assert (one.slots, four.slots, sixteen.slots) == (1, 4, 16)
    assert (one.engine.pool.size(), four.engine.pool.size(), sixteen.engine.pool.size()) == (5, 11, 35)
    assert one.engine.pool._max_overflow == four.engine.pool._max_overflow == 5  # type: ignore[attr-defined]


def _worker_block() -> str:
    text = COMPOSE.read_text(encoding="utf-8")
    match = re.search(r"^  worker:\n(.*?)(?=^  [a-z0-9_-]+:\n)", text, flags=re.S | re.M)
    assert match is not None, "no worker service in the compose file"
    return match.group(1)


def test_the_stack_passes_the_variable_to_the_worker_by_name_with_the_default_one() -> None:
    assert f"      {WORKER_SLOTS_ENV}: ${{{WORKER_SLOTS_ENV}:-1}}" in _worker_block().splitlines()


def test_no_service_before_the_worker_carries_it() -> None:
    """The ``api`` never reads it; the worker is the only service that names the variable."""
    before_the_worker = COMPOSE.read_text(encoding="utf-8").split("\n  worker:\n")[0]
    assert WORKER_SLOTS_ENV not in before_the_worker


def test_the_environment_example_documents_it_with_the_default() -> None:
    lines = ALPHA_ENV.read_text(encoding="utf-8").splitlines()
    assert f"{WORKER_SLOTS_ENV}=1" in lines
