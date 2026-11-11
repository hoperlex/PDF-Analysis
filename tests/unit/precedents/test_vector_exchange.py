"""`EMBED-01`: the directory the worker and the host's timer meet in (`precedents/vectors/exchange.py`).

The worker's side only: the files it writes are written whole (the host never reads half a request) and in the order the host relies on (the
deadline before the request), a stale file of an earlier round is refused rather than read as this round's, and the host's account is read exactly.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from auditmanager.precedents.vectors.exchange import EXCHANGE_DIR_ENV, Exchange, HostResult

REQUEST = {"format": "auditmanager-embed-texts-request/1", "texts": [{"id": "a" * 64, "text": "Находка"}]}


def test_the_request_and_its_deadline_are_written_whole_and_the_deadline_is_there_first(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    exchange = Exchange(tmp_path)
    replaced: list[str] = []
    real_replace = os.replace

    def replace(source: object, target: object) -> None:
        replaced.append(Path(str(target)).name)
        real_replace(source, target)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "replace", replace)
    exchange.write_request(REQUEST, deadline_epoch=1_800_000_000)
    assert replaced == ["deadline", "request.json"], "a host that sees the request always sees its deadline"
    assert json.loads((tmp_path / "request.json").read_text(encoding="utf-8")) == REQUEST
    assert (tmp_path / "deadline").read_text(encoding="ascii") == "1800000000\n"
    assert not list(tmp_path.glob("*.part")), "no half-written file is left behind"
    assert exchange.has_request() and exchange.read_request() == REQUEST


def test_a_round_that_left_its_files_is_refused_not_overwritten(tmp_path: Path) -> None:
    exchange = Exchange(tmp_path)
    for name in ("response.json", "over_limit.json", "result", "abort"):
        (tmp_path / name).write_text("x", encoding="utf-8")
        with pytest.raises(FileExistsError):
            exchange.write_request(REQUEST, deadline_epoch=1)
        (tmp_path / name).unlink()
    exchange.write_request(REQUEST, deadline_epoch=1)


def test_clear_removes_the_round_and_keeps_the_hosts_heartbeat(tmp_path: Path) -> None:
    exchange = Exchange(tmp_path)
    exchange.write_request(REQUEST, deadline_epoch=1)
    for name in ("response.json", "over_limit.json", "result", "stderr.log"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    exchange.request_abort()
    (tmp_path / "heartbeat").write_text("epoch=5\n", encoding="utf-8")
    exchange.clear()
    assert sorted(path.name for path in tmp_path.iterdir()) == ["heartbeat"]
    exchange.clear()   # idempotent


def test_the_hosts_account_is_read_exactly_and_a_broken_one_is_an_error_not_an_absence(tmp_path: Path) -> None:
    exchange = Exchange(tmp_path)
    assert exchange.result() is None
    (tmp_path / "result").write_text("exit_code=137\nfinished_epoch=1799999999\n", encoding="utf-8")
    assert exchange.result() == HostResult(137, 1799999999)
    (tmp_path / "result").write_text("exit_code=oops\n", encoding="utf-8")
    with pytest.raises(ValueError):
        exchange.result()


def test_a_response_that_is_not_json_is_an_error(tmp_path: Path) -> None:
    exchange = Exchange(tmp_path)
    assert exchange.read_response() is None and exchange.read_over_limit() is None
    (tmp_path / "response.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError):
        exchange.read_response()


def test_the_heartbeat_age_is_seconds_since_the_hosts_last_look(tmp_path: Path) -> None:
    exchange = Exchange(tmp_path)
    now = datetime(2026, 11, 11, 1, 0, tzinfo=UTC)
    assert exchange.heartbeat_age_seconds(now) is None
    (tmp_path / "heartbeat").write_text(f"epoch={int(now.timestamp()) - 90}\n", encoding="utf-8")
    assert exchange.heartbeat_age_seconds(now) == 90
    (tmp_path / "heartbeat").write_text("garbage\n", encoding="utf-8")
    assert exchange.heartbeat_age_seconds(now) is None, "a heartbeat nobody can read is no heartbeat"


def test_the_exchange_is_named_by_the_environment_and_only_by_it(tmp_path: Path) -> None:
    assert Exchange.from_environment({}) is None
    assert Exchange.from_environment({EXCHANGE_DIR_ENV: "  "}) is None
    found = Exchange.from_environment({EXCHANGE_DIR_ENV: str(tmp_path)})
    assert found is not None and found.directory == tmp_path
