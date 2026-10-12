"""`R-98`: the local fsynced journal file — chained, torn-tail tolerant, otherwise strict."""

from __future__ import annotations

import json
import os
import urllib.request
from decimal import Decimal
from pathlib import Path

import pytest

from auditmanager.norms.repair_journal import (
    CallIntent,
    CallState,
    JournalRefused,
    LocalJournal,
    Settlement,
    file_journal,
    money,
)
from tests.integration.norms.repair.support import (
    BASE,
    CLEAN_PAGE,
    MODEL,
    SUMS,
    Answer,
    Kit,
    LiveCallAttempted,
    MemoryStore,
    ScriptedTransport,
    openai_body,
    page,
)


def _open(directory: Path) -> LocalJournal:
    return LocalJournal(directory).open(
        base_snapshot=BASE, model=MODEL, ceiling_usd=Decimal(10), drop_sums_sha256=SUMS, now="t0"
    )


def _intent(call_id: str = "nrc_01HZZZZZZZZZZZZZZZZZZZZZZZ", attempt: int = 1) -> CallIntent:
    return CallIntent(
        call_id=call_id, document_slug="s", block_anchor="blk_1", page_label=1,
        crop_sha256="c" * 64, request_sha256="r" * 64, model=MODEL, attempt_number=attempt,
        ordinal=1, try_number=attempt, bound_usd=money("0.2145"), prepared_at="t1",
    )


def test_the_suite_cannot_open_a_connection() -> None:
    """The guard every test here relies on for "zero live calls" can actually fail a test."""
    with pytest.raises(LiveCallAttempted):
        urllib.request.urlopen("https://example.invalid/")
    import socket

    with pytest.raises(LiveCallAttempted):
        socket.create_connection(("example.invalid", 443))


def test_every_append_is_fsynced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    synced: list[int] = []
    real = os.fsync
    monkeypatch.setattr(file_journal.os, "fsync", lambda fd: (synced.append(fd), real(fd))[1])
    journal = _open(tmp_path / "j")
    before = len(synced)
    journal.append_intent(_intent())
    assert len(synced) == before + 1
    journal.write_response(_intent().call_id, b"body")
    assert len(synced) >= before + 3  # the body file and its directory
    journal.close()


def test_a_journal_reads_back_what_was_appended(tmp_path: Path) -> None:
    journal = _open(tmp_path / "j")
    intent = _intent()
    journal.append_intent(intent)
    journal.append_response(intent.call_id, "a" * 64, "t2")
    settlement = Settlement(CallState.COMPLETED, money("0.03"), cost_usd=money("0.03"),
                            response_model=MODEL)
    journal.append_settled(intent.call_id, settlement, "t3")
    journal.close()

    again = LocalJournal(tmp_path / "j").open(read_only=True)
    call = again.calls[intent.call_id]
    assert call.intent == intent
    assert call.response_sha256 == "a" * 64
    assert call.settlement.same_outcome(settlement)
    assert again.header["model"] == MODEL
    again.close()


def test_a_torn_last_line_is_dropped_and_truncated(tmp_path: Path) -> None:
    journal = _open(tmp_path / "j")
    journal.append_intent(_intent())
    journal.close()
    path = tmp_path / "j" / "journal.jsonl"
    whole = path.read_bytes()
    path.write_bytes(whole + b'{"seq": 3, "kind": "intent", "body": {"call_')

    reopened = _open(tmp_path / "j")
    assert reopened.dropped_torn_tail
    assert path.read_bytes() == whole
    assert len(reopened.calls) == 1
    reopened.close()


def test_a_damaged_line_before_the_end_refuses(tmp_path: Path) -> None:
    journal = _open(tmp_path / "j")
    journal.append_intent(_intent())
    journal.append_intent(_intent("nrc_01HYYYYYYYYYYYYYYYYYYYYYYY", attempt=2))
    journal.close()
    path = tmp_path / "j" / "journal.jsonl"
    lines = path.read_bytes().splitlines(keepends=True)
    lines[1] = lines[1].replace(b'"page_label":1', b'"page_label":2')
    path.write_bytes(b"".join(lines))
    with pytest.raises(JournalRefused, match="digest"):
        _open(tmp_path / "j")


def test_a_missing_line_refuses(tmp_path: Path) -> None:
    journal = _open(tmp_path / "j")
    journal.append_intent(_intent())
    journal.append_intent(_intent("nrc_01HYYYYYYYYYYYYYYYYYYYYYYY", attempt=2))
    journal.close()
    path = tmp_path / "j" / "journal.jsonl"
    lines = path.read_bytes().splitlines(keepends=True)
    path.write_bytes(lines[0] + lines[2])
    with pytest.raises(JournalRefused, match="chain"):
        _open(tmp_path / "j")


def test_two_writers_cannot_hold_one_journal(tmp_path: Path) -> None:
    first = _open(tmp_path / "j")
    with pytest.raises(JournalRefused, match="one writer"):
        _open(tmp_path / "j")
    first.close()
    _open(tmp_path / "j").close()


def test_a_journal_under_a_docker_volume_is_refused() -> None:
    with pytest.raises(JournalRefused, match="Docker volume"):
        LocalJournal(Path("/var/lib/docker/volumes/promotion/_data/repairs"))


def test_a_response_body_is_never_overwritten_with_other_bytes(tmp_path: Path) -> None:
    journal = _open(tmp_path / "j")
    call_id = _intent().call_id
    sha = journal.write_response(call_id, b"first")
    assert journal.write_response(call_id, b"first") == sha
    with pytest.raises(JournalRefused, match="different response"):
        journal.write_response(call_id, b"second")
    assert not list((tmp_path / "j" / "responses").glob("*.partial"))
    journal.close()


def test_a_response_body_that_fails_its_sha_is_refused(tmp_path: Path) -> None:
    journal = _open(tmp_path / "j")
    call_id = _intent().call_id
    sha = journal.write_response(call_id, b"first")
    (tmp_path / "j" / "responses" / f"{call_id}.body").write_bytes(b"tampered")
    with pytest.raises(JournalRefused, match="SHA-256"):
        journal.read_response(call_id, sha)
    journal.close()


def test_a_database_settlement_the_file_disagrees_with_refuses_the_start(tmp_path: Path) -> None:
    """The reverse of every forward rule: both sides settled, differently. Nothing resolves it."""
    store = MemoryStore()
    kit = Kit(directory=tmp_path / "j", store=store,
              transport=ScriptedTransport(script=[Answer(openai_body(CLEAN_PAGE, cost=0.02))]))
    kit.runner().run([page()])
    (row,) = store.rows.values()
    row["settlement"] = Settlement(CallState.COMPLETED, money("0.01"), cost_usd=money("0.01"),
                                   response_model=MODEL)
    with pytest.raises(JournalRefused, match="settled it differently"):
        kit.runner().reconcile()
    kit.close()


def test_the_journal_lines_carry_no_credential_and_no_body(tmp_path: Path) -> None:
    store = MemoryStore()
    kit = Kit(directory=tmp_path / "j", store=store,
              transport=ScriptedTransport(script=[Answer(openai_body(CLEAN_PAGE))]))
    kit.runner().run([page()])
    kit.close()
    text = (tmp_path / "j" / "journal.jsonl").read_text(encoding="utf-8")
    assert CLEAN_PAGE.split("\n")[0] not in text
    for line in text.splitlines():
        assert set(json.loads(line)) == {"seq", "kind", "at", "body", "prev", "digest"}
