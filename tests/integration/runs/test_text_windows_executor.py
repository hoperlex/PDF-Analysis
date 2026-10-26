"""`SECTION-CHUNKED-ANALYSIS-01` on the lane's PostgreSQL and MinIO: a windowed run through ``execute_run``.

A version whose recorded character count is above the one-call budget is analysed in whole-page windows: one
model call each, one run cost ceiling over all of them, one effect-journal entry and one ``model_call`` row per
window, and a saved reply per window so that a killed run is resumed without paying for a finished window
again. The cases (none of them calls a provider; the adapters are scripted and the socket guard is on):

* a three-window run publishes findings from every window, each tied to the call of its own window;
* a kill **between** windows is resumed by a new Attempt that calls the remaining windows only, counted at the
  adapter and in ``model_call``; a kill **inside** a window is still the ambiguous effect it always was and fails
  the run without a second call;
* the run's one cost ceiling stops the run at a window boundary with a named reason and publishes nothing;
* a saved reply that cannot be read stops the resumed run instead of being called again;
* a version within the one-call budget makes exactly one call and publishes what it always did.

The 8-page ``ar_baseline.pdf`` (pages of 509, 539, 482, 468, 442, 469, 427 and 404 characters) is cut into the
windows pages 1-2, 3-5 and 6-8 by a window of 1 500 characters, which a run cost ceiling of about USD 0.4612
yields for the pinned primary model (the budget is a function of the ceiling, ``analysis/text/budget.py``).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.public import input_budget_characters
from auditmanager.analysis.text import ModelResponse, ProviderConfig, ProviderMode
from auditmanager.documents.public import DocumentRepository
from auditmanager.findings import published_finding_evidence, published_findings
from auditmanager.jobs import JobRepository
from auditmanager.runs import execute_run, start_audit_run
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, VersionUid
from auditmanager.storage import BlobNotFoundError, parse_blob_id
from tests.support.v1_reference_profile import resolve_reference_profile

MODEL = "claude-opus-5"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RECORDINGS = REPOSITORY_ROOT / "fixtures" / "recorded" / "text_analysis"
LAYER = json.loads((RECORDINGS / "inputs" / "ar_baseline_text_layer.json").read_text(encoding="utf-8"))
BANNER = re.compile(r"=== Страница (\d+) ===")
#: The windows the 1 500-character window cuts the baseline into.
WINDOWS = [[1, 2], [3, 4, 5], [6, 7, 8]]
FIRST_PAGES = [1, 3, 6]


def _ceiling_for(window: int) -> float:
    """The smallest ceiling whose one-call budget is at least ``window`` characters."""
    low, high = 0.40, 1.0
    for _ in range(80):
        middle = (low + high) / 2
        if input_budget_characters(MODEL, middle) < window:
            low = middle
        else:
            high = middle
    return high


CEILING = _ceiling_for(1_500)
WINDOW = input_budget_characters(MODEL, CEILING)
#: pypdfium2's count of the baseline (``W55B-BUDGET-01`` section 3.2): above the window, within the limit.
COUNT = 3_810


class ProcessExit(BaseException):
    """A process loss: nothing in the executor can turn it into state."""


def _quote(page: int) -> str:
    return LAYER["pages"][page - 1]["text"].splitlines()[0]


def _answer(first_page: int, cost: float) -> ModelResponse:
    observation = {
        "category": "internal_contradiction",
        "finding_text": f"Расхождение в окне с первой страницей {first_page}",
        "recommendation_text": "Согласовать значение",
        "evidence": [{"page_number": first_page, "quote": _quote(first_page)}],
    }
    return ModelResponse(
        output_text=json.dumps({"observations": [observation]}, ensure_ascii=False),
        stop_reason="end_turn", input_tokens=1_000, output_tokens=100, latency_ms=7,
        reported_cost_usd=cost,
    )


class Scripted:
    """Answers a window by quoting the first line of its first page; can lose the process on a call."""

    def __init__(self, mode: ProviderMode, *, cost: float = 0.01, exit_on_call: int | None = None) -> None:
        self._mode = mode
        self._cost = cost
        self._exit_on_call = exit_on_call
        self.pages_seen: list[list[int]] = []

    @property
    def provider_mode(self) -> ProviderMode:
        return self._mode

    @property
    def calls(self) -> int:
        return len(self.pages_seen)

    def complete(self, request: Any) -> ModelResponse:
        pages = [int(n) for n in BANNER.findall(request.body["messages"][0]["content"])]
        self.pages_seen.append(pages)
        if self._exit_on_call == len(self.pages_seen):
            raise ProcessExit("the process was lost with the provider call in flight")
        return _answer(pages[0], self._cost)


def _config(mode: ProviderMode = ProviderMode.RECORDED, ceiling: float = CEILING) -> ProviderConfig:
    return ProviderConfig(
        mode=mode, model_id=MODEL, run_cost_ceiling_usd=ceiling, api_key=None, ceiling_is_explicit=True,
    )


def _counted_version(session: Session, seeded: Any, count: int | None) -> str:
    """A further published version of the seeded document carrying ``count`` as its recorded count."""
    documents = DocumentRepository()
    base = documents.get_version(session, VersionUid.parse(seeded.version_uid))
    counts = (
        {}
        if count is None
        else {"text_character_count": count, "textless_pages": (), "recognised_character_count": 0}
    )
    return str(documents.publish_version(
        session, document_uid=DocumentUid.parse(seeded.document_uid), media_type=base.media_type,
        byte_size=base.byte_size, sha256=base.sha256, page_count=base.page_count,
        source_filename=None, entries=base.manifest, **counts,
    ))


def _start(session: Session, seeded: Any, version_uid: str, mode: str, label: str, budget: int = WINDOW):
    return start_audit_run(
        session, version_uid=version_uid, analysis_profile_id=seeded.analysis_profile_id,
        prompt_bundle_id=seeded.prompt_bundle_id, provider_mode=mode,
        idempotency_key=f"cwin-{label}-{uuid4().hex}", input_budget_characters=budget,
    )


def _text_metrics(session: Session, run_id: str) -> dict[str, Any]:
    return session.execute(
        text("SELECT metrics FROM stage_result WHERE run_id = :r AND stage_id = 'text_analysis'"),
        {"r": run_id},
    ).scalar_one()


def _model_calls(session: Session, run_id: str) -> list[dict[str, Any]]:
    return [dict(row) for row in session.execute(
        text("SELECT model_call_id, parameters, cost_micros, status FROM model_call "
             "WHERE run_id = :r ORDER BY created_at, model_call_id"), {"r": run_id},
    ).mappings().all()]


def test_the_scripted_window_is_the_one_the_cases_are_written_for() -> None:
    assert [len(page["text"]) for page in LAYER["pages"]] == [509, 539, 482, 468, 442, 469, 427, 404]
    assert 1_392 <= WINDOW <= 1_529, "the window must cut the baseline into pages 1-2, 3-5 and 6-8"
    assert 0.46 < CEILING < 0.47 and COUNT > WINDOW


# -- a windowed run, end to end -------------------------------------------------------------------


def test_a_three_window_run_publishes_findings_from_every_window_each_tied_to_its_own_call(
    session: Session, seeded, blob_store, helpers
) -> None:
    version = _counted_version(session, seeded, COUNT)
    started = _start(session, seeded, version, "recorded", "three")
    adapter = Scripted(ProviderMode.RECORDED)

    result = execute_run(
        session, started.run_id, blob_store=blob_store, adapter=adapter,
        provider_config=_config(), text_profiles=resolve_reference_profile,
    )

    assert result.terminal_state == "published", (dict(result.stage_statuses), result.degradation_set)
    assert adapter.pages_seen == WINDOWS
    assert helpers.run_state_of(session, started.run_id) == "published"
    assert set(result.stage_statuses.values()) == {"succeeded"}

    calls = _model_calls(session, started.run_id)
    assert len(calls) == 3
    for index, call in enumerate(calls):
        assert call["parameters"]["text_window_index"] == index
        assert call["parameters"]["text_window_count"] == 3
        assert call["parameters"]["text_window_first_page"] == WINDOWS[index][0]
        assert call["parameters"]["text_window_last_page"] == WINDOWS[index][-1]
        assert len(call["parameters"]["text_window_key"]) == 64
        assert call["parameters"]["text_window_reply_blob_id"].startswith("blob_")
        assert call["status"] == "succeeded" and call["cost_micros"] == 10_000

    findings = published_findings(session, started.run_id)
    assert result.published_finding_count == len(findings) == 3
    by_call = {finding.model_call_id: finding for finding in findings}
    assert set(by_call) == {call["model_call_id"] for call in calls}, "each finding names its own window's call"

    evidence = {e.page_number: e for e in published_finding_evidence(session, started.run_id)}
    assert sorted(evidence) == FIRST_PAGES
    layer_text = "".join(page["text"] for page in LAYER["pages"])
    for page, item in evidence.items():
        assert layer_text[item.char_start:item.char_end] == item.quote == _quote(page)
    assert evidence[3].char_start >= len(LAYER["pages"][0]["text"]) + len(LAYER["pages"][1]["text"])

    metrics = _text_metrics(session, started.run_id)
    assert metrics["windows_total"] == 3 and metrics["windows_analysed"] == 3
    assert metrics["windows_recovered"] == 0 and metrics["windows_independent"] is True
    assert "каждое окно проверено отдельно" in metrics["windows_note"]
    assert metrics["cost_usd"] == pytest.approx(0.03)


def test_the_ceiling_counts_every_window_and_the_run_stops_at_a_boundary_publishing_nothing(
    session: Session, seeded, blob_store, helpers
) -> None:
    """Each window costs half the ceiling: after two the ceiling is reached and the third is not called."""
    version = _counted_version(session, seeded, COUNT)
    started = _start(session, seeded, version, "recorded", "ceiling")
    adapter = Scripted(ProviderMode.RECORDED, cost=CEILING / 2)

    result = execute_run(
        session, started.run_id, blob_store=blob_store, adapter=adapter,
        provider_config=_config(), text_profiles=resolve_reference_profile,
    )

    assert result.terminal_state == "failed"
    row = session.execute(
        text("SELECT terminal_reason FROM audit_run WHERE run_id = :r"), {"r": started.run_id}
    ).one()
    assert row[0] == ErrorCode.COST_BUDGET_EXCEEDED.value
    assert adapter.pages_seen == WINDOWS[:2], "the third window is not called"
    assert len(_model_calls(session, started.run_id)) == 2
    assert published_findings(session, started.run_id) == ()
    stage = session.execute(
        text("SELECT status, error, metrics FROM stage_result "
             "WHERE run_id = :r AND stage_id = 'text_analysis'"), {"r": started.run_id},
    ).mappings().one()
    assert stage["status"] == "failed" and stage["error"]["code"] == "cost_budget_exceeded"
    assert "stopped before window 3 of 3 (pages 6-8)" in stage["error"]["message"]
    assert stage["metrics"]["failed_window"] == 3 and stage["metrics"]["windows_completed"] == 2


# -- a kill, and what a restart pays for -----------------------------------------------------------


def _factory(engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _prepare_live_run(factory, helpers, blob_store, label: str):
    with factory() as session:
        seeded = helpers.seed_version(session, blob_store)
        version = _counted_version(session, seeded, COUNT)
        started = _start(session, seeded, version, "live", label)
        session.commit()
    return seeded, started


def _lose_the_attempt(factory, run_id: str) -> None:
    """The owner is dead: fence its Attempt exactly as the watchdog or the lease sweep does."""
    with factory() as controller:
        attempt_id = controller.execute(
            text("SELECT current_attempt_id FROM job WHERE run_id = :r"), {"r": run_id}
        ).scalar_one()
        assert JobRepository().reclaim_expired(controller, force_attempt_id=attempt_id) == 1
        controller.commit()


def test_a_kill_between_windows_resumes_and_the_restart_pays_for_the_remaining_windows_only(
    engine, blob_store, helpers
) -> None:
    factory = _factory(engine)
    _seeded, started = _prepare_live_run(factory, helpers, blob_store, "resume")
    first = Scripted(ProviderMode.LIVE)
    completed = 0

    def lose_the_process_after_window_one(boundary: str) -> None:
        nonlocal completed
        if boundary == "provider_call_completed":
            completed += 1
            if completed == 1:
                raise ProcessExit("after window one")

    with factory() as session:
        with pytest.raises(ProcessExit, match="after window one"):
            execute_run(
                session, started.run_id, blob_store=blob_store, adapter=first,
                provider_config=_config(ProviderMode.LIVE), text_profiles=resolve_reference_profile,
                effect_checkpoint=lose_the_process_after_window_one,
            )
    assert first.pages_seen == [[1, 2]]

    with factory() as observer:
        first_call = _model_calls(observer, started.run_id)
        assert len(first_call) == 1 and first_call[0]["parameters"]["text_window_index"] == 0
        blob = json.loads(blob_store.read(
            parse_blob_id(first_call[0]["parameters"]["text_window_reply_blob_id"]), verify=True
        ))
        assert json.loads(blob["output_text"])["observations"][0]["evidence"][0]["page_number"] == 1
        assert blob["window_key"] == first_call[0]["parameters"]["text_window_key"]
        assert blob["model_call_id"] == first_call[0]["model_call_id"]

    _lose_the_attempt(factory, started.run_id)
    with factory() as observer:
        assert observer.execute(
            text("SELECT state FROM audit_run WHERE run_id = :r"), {"r": started.run_id}
        ).scalar_one() == "running", "the lost Attempt was not ambiguous, so the run is resumed, not failed"
        assert observer.execute(
            text("SELECT state FROM job WHERE run_id = :r"), {"r": started.run_id}
        ).scalar_one() == "queued"

    second = Scripted(ProviderMode.LIVE)
    with factory() as session:
        result = execute_run(
            session, started.run_id, blob_store=blob_store, adapter=second,
            provider_config=_config(ProviderMode.LIVE), text_profiles=resolve_reference_profile,
        )
        session.commit()

    assert second.pages_seen == [[3, 4, 5], [6, 7, 8]], "window one is not paid for again"
    assert first.calls + second.calls == 3
    assert result.terminal_state == "published"
    with factory() as observer:
        calls = _model_calls(observer, started.run_id)
        assert len(calls) == 3, "one model_call per window, none repeated"
        assert [c["parameters"]["text_window_index"] for c in calls] == [0, 1, 2]
        assert first_call[0]["model_call_id"] == calls[0]["model_call_id"]
        metrics = _text_metrics(observer, started.run_id)
        assert metrics["windows_recovered"] == 1 and metrics["windows_total"] == 3
        findings = published_findings(observer, started.run_id)
        assert len(findings) == 3
        assert {f.model_call_id for f in findings} == {c["model_call_id"] for c in calls}
        # The ceiling was one for the run: the restart opened with window one's spend.
        assert metrics["cost_usd"] == pytest.approx(0.03)
        attempts = observer.execute(
            text("SELECT count(*) FROM attempt a JOIN job j ON j.job_id = a.job_id WHERE j.run_id = :r"),
            {"r": started.run_id},
        ).scalar_one()
        assert attempts == 2


def test_a_kill_inside_a_window_is_still_the_ambiguous_effect_it_always_was(
    engine, blob_store, helpers
) -> None:
    """The provider may have been sent window two and its reply is lost: the run fails, no second call."""
    factory = _factory(engine)
    _seeded, started = _prepare_live_run(factory, helpers, blob_store, "inflight")
    adapter = Scripted(ProviderMode.LIVE, exit_on_call=2)
    with factory() as session:
        with pytest.raises(ProcessExit):
            execute_run(
                session, started.run_id, blob_store=blob_store, adapter=adapter,
                provider_config=_config(ProviderMode.LIVE), text_profiles=resolve_reference_profile,
            )
    assert adapter.pages_seen == [[1, 2], [3, 4, 5]]

    _lose_the_attempt(factory, started.run_id)
    with factory() as observer:
        state = observer.execute(
            text("SELECT state, terminal_reason FROM audit_run WHERE run_id = :r"), {"r": started.run_id}
        ).one()
        assert tuple(state) == ("failed", "analysis_failed")
        effects = dict(observer.execute(
            text("SELECT state, count(*) FROM provider_call_effect WHERE run_id = :r GROUP BY state"),
            {"r": started.run_id},
        ).all())
        assert effects == {"completed": 1, "outcome_unknown": 1}
        assert observer.execute(
            text("SELECT state FROM job WHERE run_id = :r"), {"r": started.run_id}
        ).scalar_one() in {"failed", "dead_letter"}
    assert adapter.calls == 2


def test_a_saved_reply_that_cannot_be_read_stops_the_resumed_run_it_is_not_called_again(
    engine, blob_store, helpers
) -> None:
    factory = _factory(engine)
    _seeded, started = _prepare_live_run(factory, helpers, blob_store, "unreadable")
    seen = 0

    def lose_after_window_one(boundary: str) -> None:
        nonlocal seen
        if boundary == "provider_call_completed":
            seen += 1
            if seen == 1:
                raise ProcessExit("after window one")

    first = Scripted(ProviderMode.LIVE)
    with factory() as session:
        with pytest.raises(ProcessExit):
            execute_run(
                session, started.run_id, blob_store=blob_store, adapter=first,
                provider_config=_config(ProviderMode.LIVE), text_profiles=resolve_reference_profile,
                effect_checkpoint=lose_after_window_one,
            )
    with factory() as observer:
        reply_id = _model_calls(observer, started.run_id)[0]["parameters"]["text_window_reply_blob_id"]
    _lose_the_attempt(factory, started.run_id)

    class MissingReply:
        """The store with the first window's reply gone."""

        def __init__(self, inner: Any) -> None:
            self._inner = inner

        def read(self, blob_id: Any, *args: Any, **kwargs: Any) -> bytes:
            if str(blob_id) == reply_id:
                raise BlobNotFoundError(blob_id=reply_id)
            return self._inner.read(blob_id, *args, **kwargs)

        def __getattr__(self, name: str) -> Any:
            return getattr(self._inner, name)

    second = Scripted(ProviderMode.LIVE)
    with factory() as session:
        result = execute_run(
            session, started.run_id, blob_store=MissingReply(blob_store), adapter=second,
            provider_config=_config(ProviderMode.LIVE), text_profiles=resolve_reference_profile,
        )
        session.commit()
    assert result.terminal_state == "failed" and second.calls == 0
    with factory() as observer:
        row = observer.execute(
            text("SELECT terminal_reason, terminal_detail FROM audit_run WHERE run_id = :r"),
            {"r": started.run_id},
        ).mappings().one()
    assert row["terminal_reason"] == ErrorCode.ANALYSIS_INPUT_INVALID.value
    assert row["terminal_detail"]["reason"] == "window_reply_unreadable"


# -- below the old budget, nothing changed -----------------------------------------------------------


def test_a_version_within_the_one_call_budget_makes_one_call_and_publishes_what_it_always_did(
    session: Session, seeded, blob_store, recorded_adapter, provider_config
) -> None:
    """Counts of ``None`` and of exactly the budget are the single call: same request, same recording."""
    budget = input_budget_characters(provider_config.model_id, provider_config.run_cost_ceiling_usd)
    shapes = []
    for label, count in (("none", None), ("at-budget", budget)):
        version = _counted_version(session, seeded, count)
        started = _start(session, seeded, version, "recorded", label, budget)

        class Counting:
            provider_mode = recorded_adapter.provider_mode

            def __init__(self) -> None:
                self.calls = 0

            def complete(self, request: Any) -> Any:
                self.calls += 1
                return recorded_adapter.complete(request)

        adapter = Counting()
        result = execute_run(
            session, started.run_id, blob_store=blob_store, adapter=adapter,
            provider_config=provider_config, text_profiles=resolve_reference_profile,
        )
        assert result.terminal_state == "published" and adapter.calls == 1
        metrics = _text_metrics(session, started.run_id)
        assert "windows_total" not in metrics, "a single call carries no window metrics"
        assert (RECORDINGS / f"{metrics['request_sha256']}.json").is_file(), "it asked the recorded question"
        calls = _model_calls(session, started.run_id)
        assert len(calls) == 1 and "text_window_key" not in calls[0]["parameters"]
        findings = published_findings(session, started.run_id)
        shapes.append((
            metrics["request_sha256"], metrics["observations_emitted"],
            sorted(f.finding_text for f in findings),
            sorted(
                (e.page_number, e.char_start, e.char_end)
                for e in published_finding_evidence(session, started.run_id)
            ),
        ))
    assert shapes[0] == shapes[1], "a count at the budget publishes exactly what no count publishes"
