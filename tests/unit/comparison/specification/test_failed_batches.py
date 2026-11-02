"""A failed batch does not seal a side, progress writes counters, an empty "complete" extraction needs a table (`REVIEW-FIX-CMP-SPEC-1102`).

Code review 2026-11-02, S2-blocks-4-9-04, -06 and -11. The store, the reader and the session are fakes that record what they are handed
(the rows are immutable and content-keyed exactly as ``comparison_spec_extraction`` is); the parser and the check are the real ones. Every
guard here is shown failing on the behaviour it replaced.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.comparison.specification import batches, check, prompt, source as source_module, transition
from auditmanager.comparison.specification.reader import VersionStream
from auditmanager.comparison.specification.repository import ExtractionRow

PROJECT = "prj_01M2545JSD15ETSNNV904X991F"
VERSION = "ver_01M2545JSD15ETSNNV904X991J"


class Store:
    """``SpecificationRepository`` for extractions: immutable, ``ON CONFLICT DO NOTHING``, answering the row that exists."""

    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], ExtractionRow] = {}

    def find_extraction(self, session: Any, project_uid: str, content_key: str) -> ExtractionRow | None:
        return self.rows.get((project_uid, content_key))

    def insert_extraction(self, session: Any, *, project_uid: str, version_uid: str, content_key: str, state: str,
                          prompt_version: str, model_identity: str, recorded: bool, source_sha256: str,
                          positions: list[dict[str, Any]], coverage: dict[str, Any], model_call_id: str | None) -> ExtractionRow:
        row = ExtractionRow(f"cse_{len(self.rows):04d}", project_uid, version_uid, content_key, state, prompt_version, model_identity,
                            recorded, source_sha256, positions, coverage, model_call_id, datetime.now(timezone.utc))
        return self.rows.setdefault((project_uid, content_key), row)


class Reader:
    def __init__(self, parsed: list[dict[str, Any]]) -> None:
        self._parsed = parsed

    def version_stream(self, version_uid: str) -> VersionStream:
        stream = VersionStream(version_uid)
        stream.parsed = list(self._parsed)
        stream.parsed_pages = {page["page"] for page in self._parsed}
        stream.refs = {page["page"]: {"version_uid": version_uid, "page_number": page["page"]} for page in self._parsed}
        return stream


def factory() -> Any:
    return SimpleNamespace(commit=lambda: None, rollback=lambda: None, close=lambda: None)


@pytest.fixture
def small_batches(monkeypatch: pytest.MonkeyPatch) -> None:
    """Three lines to a batch, so that two small pages are several batches."""
    monkeypatch.setattr(batches, "OWNED_LINES", 3)


@pytest.fixture
def spec(drawn: Any) -> list[dict[str, Any]]:
    parsed = []
    for number in (1, 2):
        page = drawn.Page()
        for row in range(1, 4):
            page.row({"pos": str(row), "mark": f"М-{number}{row}", "name": f"Позиция {number}.{row}", "quantity": str(row)})
        result = page.parse()
        parsed.append({"page": number, "sheet": str(number), "name": "Спецификация", "columns": result["columns"], "rows": result["rows"]})
    return parsed


class Model:
    """The ``ask_batch`` of the job: answers a batch from the oracle, keeps the raw reply the way the handler does, and counts calls."""

    def __init__(self, store: Store, packets: dict[str, dict[str, Any]], whole: Any, *, broken: set[str] | None = None) -> None:
        self.store, self.packets, self.whole, self.broken = store, packets, whole, broken or set()
        self.asked: list[tuple[str, str]] = []

    def __call__(self, text: str, metadata: dict[str, Any]) -> transition.Answer:
        batch_id = metadata["batch_id"]
        self.asked.append((batch_id, metadata["raw_key"]))
        payload = {"blocks": []} if batch_id in self.broken else self.whole.faithful_answer(self.packets[batch_id])
        call_id = f"cmc_{len(self.asked):04d}"
        self.store.insert_extraction(None, project_uid=PROJECT, version_uid=VERSION, content_key=metadata["raw_key"], state="partial",
            prompt_version=batches.RAW_VERSION, model_identity="model", recorded=False, source_sha256=metadata["source_sha256"],
            positions=[], coverage={"record_kind": "raw_reply", "batch_id": batch_id}, model_call_id=call_id)
        return transition.Answer(payload, "model", False, call_id)


def plan_of(parsed: list[dict[str, Any]]) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    source = source_module.build_source(parsed, batched=True)
    return source, batches.plan(source)


def read(store: Store, reader: Reader, model: Model | None, **kw: Any) -> transition.Side:
    return transition.read_side(factory, reader, store, project_uid=PROJECT, version_uid=VERSION, ask=None,
                                ask_batch=model, **kw)  # type: ignore[arg-type]


def test_a_failed_batch_keeps_its_rows_and_does_not_seal_the_side(small_batches: None, spec: list[dict[str, Any]], whole: Any) -> None:
    source, plan = plan_of(spec)
    assert len(plan) >= 3
    store, reader = Store(), Reader(spec)
    model = Model(store, {b["batch_id"]: b["source"] for b in plan}, whole, broken={plan[1]["batch_id"]})
    side = read(store, reader, model)
    assert side.complete is False and side.reason == check.REASON_ANSWER and side.sent is True and side.rows == []
    # the paid work is kept: the first batch checked complete, the second checked partial, the tail was never asked
    assert [batch_id for batch_id, _ in model.asked] == [plan[0]["batch_id"], plan[1]["batch_id"]]
    first, second = (store.find_extraction(None, PROJECT, transition.batch_keys(PROJECT, plan[i]["batch_id"], 1)[0]) for i in (0, 1))
    assert first is not None and first.state == "complete" and second is not None and second.state == "partial"
    # ... but the aggregate is not stored under the text's key, so nothing answers every later read for it
    key = prompt.content_key(PROJECT, batches.digest({"source": source["source_sha256"], "plan": [b["batch_id"] for b in plan]}),
                             batches.PROMPT_VERSION)
    assert store.find_extraction(None, PROJECT, key) is None
    prepared = transition.prepare_side(factory, reader, store, project_uid=PROJECT, version_uid=VERSION)  # type: ignore[arg-type]
    assert prepared.stored is None and prepared.sendable is True


def test_without_a_new_consent_the_failed_batch_is_not_asked_again(small_batches: None, spec: list[dict[str, Any]], whole: Any) -> None:
    _, plan = plan_of(spec)
    store, reader = Store(), Reader(spec)
    packets = {b["batch_id"]: b["source"] for b in plan}
    read(store, reader, Model(store, packets, whole, broken={plan[1]["batch_id"]}))
    again = Model(store, packets, whole)
    side = read(store, reader, again)
    assert again.asked == [] and side.complete is False and side.reason == check.REASON_ANSWER


def test_a_fresh_consent_asks_the_failed_batch_and_the_tail_under_the_next_attempt(
        small_batches: None, spec: list[dict[str, Any]], whole: Any) -> None:
    source, plan = plan_of(spec)
    store, reader = Store(), Reader(spec)
    packets = {b["batch_id"]: b["source"] for b in plan}
    failed = plan[1]["batch_id"]
    read(store, reader, Model(store, packets, whole, broken={failed}))
    # the estimate and the job start read the next attempt of a batch whose check failed and whose paid reply is kept
    renewed = transition.prepare_side(factory, reader, store, project_uid=PROJECT, version_uid=VERSION,  # type: ignore[arg-type]
                                      renew_failed=True)
    attempts = {b["batch_id"]: b["attempt"] for b in renewed.batches}
    assert attempts[plan[0]["batch_id"]] == 1 and attempts[failed] == 2 and all(attempts[b["batch_id"]] == 1 for b in plan[2:])
    pinned = {failed: 2}
    model = Model(store, packets, whole)
    side = read(store, reader, model, attempts=pinned)
    assert [batch_id for batch_id, _ in model.asked] == [b["batch_id"] for b in plan[1:]]  # the first batch is reused, never asked
    assert model.asked[0][1] == transition.batch_keys(PROJECT, failed, 2)[1] != transition.batch_keys(PROJECT, failed, 1)[1]
    assert side.complete is True and len(side.rows) == sum(len(page["rows"]) for page in spec) and side.extraction_id is not None
    # the earlier attempt and its raw reply are untouched
    old = store.find_extraction(None, PROJECT, transition.batch_keys(PROJECT, failed, 1)[0])
    assert old is not None and old.state == "partial"


def test_a_failed_check_whose_paid_reply_is_not_kept_is_never_renewed(
        small_batches: None, spec: list[dict[str, Any]], whole: Any) -> None:
    _, plan = plan_of(spec)
    store, reader = Store(), Reader(spec)
    packets = {b["batch_id"]: b["source"] for b in plan}
    failed = plan[1]["batch_id"]
    read(store, reader, Model(store, packets, whole, broken={failed}))
    del store.rows[(PROJECT, transition.batch_keys(PROJECT, failed, 1)[1])]  # the raw reply is gone: the paid call is unaccounted for
    renewed = transition.prepare_side(factory, reader, store, project_uid=PROJECT, version_uid=VERSION,  # type: ignore[arg-type]
                                      renew_failed=True)
    assert {b["batch_id"]: b["attempt"] for b in renewed.batches}[failed] == 1


def test_a_side_whose_every_batch_passed_is_still_stored(small_batches: None, spec: list[dict[str, Any]], whole: Any) -> None:
    _, plan = plan_of(spec)
    store, reader = Store(), Reader(spec)
    model = Model(store, {b["batch_id"]: b["source"] for b in plan}, whole)
    side = read(store, reader, model)
    assert side.complete is True and side.extraction_id is not None
    again = Model(store, {}, whole)
    assert read(store, reader, again).complete is True and again.asked == []


# -- S2-06: progress is counters ------------------------------------------------------------------------------------


def test_progress_carries_counters_and_the_two_pins_only(small_batches: None, spec: list[dict[str, Any]], whole: Any) -> None:
    _, plan = plan_of(spec)
    store, reader = Store(), Reader(spec)
    written: list[dict[str, Any]] = []
    read(store, reader, Model(store, {b["batch_id"]: b["source"] for b in plan}, whole),
         progress=lambda version_uid, coverage: written.append(coverage))
    assert len(written) == len(plan)
    for coverage in written:
        assert set(coverage) <= set(batches.PROGRESS_KEYS)
        assert "batches" not in coverage and "candidate_positions" not in coverage and "issues" not in coverage
        assert coverage["planning_revision"] == batches.REVISION and coverage["source_key"]
    assert [c["batches_covered"] for c in written] == list(range(1, len(plan) + 1))
    assert len(json.dumps(written[-1])) < 600  # does not grow with the rows read so far


def test_the_whole_coverage_the_progress_replaces_does_grow(small_batches: None, spec: list[dict[str, Any]], whole: Any) -> None:
    """The mutation: writing ``aggregate``'s coverage as it was carries the batch list and every candidate position."""
    source, plan = plan_of(spec)
    records = [transition._BatchRecord("complete", [], {}) for _ in plan[:1]]  # noqa: SLF001
    _, _, coverage = batches.aggregate(source, plan, records)
    assert coverage["batches"] and "candidate_positions" in coverage
    assert set(batches.counters(coverage)) <= set(batches.PROGRESS_KEYS) and "batches" not in batches.counters(coverage)


# -- S2-11: an empty "complete" extraction needs a table --------------------------------------------------------------


def _source_of_lines(*lines: str) -> dict[str, Any]:
    block = {"block_id": "p1", "page": 1, "kind": "table", "lines": [{"line": n, "text": t} for n, t in enumerate(lines, 1)]}
    return {"blocks": [block], "source_sha256": "a" * 64}


def _one_batch(source: dict[str, Any]) -> list[dict[str, Any]]:
    owned = [line["line"] for line in source["blocks"][0]["lines"]]
    return [{"batch_id": "sb_1", "index": 0, "owned_line_ids": owned, "context_line_ids": [], "source_sha256": "b" * 64}]


def test_no_position_and_no_recognised_table_is_not_a_complete_empty_specification() -> None:
    source = _source_of_lines("Общие данные", "Примечания к чертежу")
    complete, positions, coverage = batches.aggregate(source, _one_batch(source), [transition._BatchRecord("complete", [], {})])  # noqa: SLF001
    assert complete is False and positions == [] and coverage["table_headers"] == 0
    assert "No specification position and no recognised table header" in coverage["issues"]


def test_a_recognised_header_and_no_data_line_is_an_explicit_empty_table() -> None:
    header, separator = source_module.page_lines(["pos", "name", "quantity"], [])
    source = _source_of_lines(header, separator)
    complete, positions, coverage = batches.aggregate(source, _one_batch(source), [transition._BatchRecord("complete", [], {})])  # noqa: SLF001
    assert complete is True and positions == [] and coverage["table_headers"] == 1 and coverage["rows_total"] == 0


def _stored(state: str, positions: list[Any], **coverage: Any) -> ExtractionRow:
    return ExtractionRow("cse_1", PROJECT, VERSION, "k" * 64, state, batches.PROMPT_VERSION, "model", False, "s" * 64, positions,
                         coverage, None, datetime.now(timezone.utc))


def _side() -> transition.Side:
    return transition.Side(version_uid=VERSION, sheets=1, complete=False)


def test_a_stored_complete_extraction_without_positions_needs_an_explicit_empty_table() -> None:
    bare = transition._from_stored(_side(), _stored("complete", [], blocks_total=1, rows_total=0))  # noqa: SLF001
    assert bare.complete is False and bare.reason == transition.REASON_STORED_UNUSABLE
    legacy = transition._from_stored(_side(), _stored("complete", [], blocks_total=1, rows_total=0, table_headers=0))  # noqa: SLF001
    assert legacy.complete is False
    empty = transition._from_stored(_side(), _stored("complete", [], blocks_total=1, rows_total=0, table_headers=1))  # noqa: SLF001
    assert empty.complete is True and empty.rows == []
    with_rows = transition._from_stored(_side(), _stored("complete", [{"id": "sr_1"}], blocks_total=1, rows_total=1))  # noqa: SLF001
    assert with_rows.complete is True and with_rows.rows == [{"id": "sr_1"}]
