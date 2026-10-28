"""The AI summary over the approved pairs against PostgreSQL (`COMPARE-PERSISTED-SUMMARY-01`, B2).

The same real half as ``test_sheet_pairing_db.py`` (versions, the command receipt, the append-only
histories, the audit trail) with the same port fakes for classifications, runs and page text, and a
**recorded** summary model: a reply committed under the digest of the exact request, here written by
the test into a directory of its own for the request the service will make (the committed recording
for the synthetic pair is replayed by ``test_the_committed_recording_answers_the_synthetic_pair``).
No live model is reachable from this module.

Needs a database migrated to ``0035_comparison_records`` or later with its summary table; run on a
private database (``DATABASE_URL``).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from auditmanager.comparison.public import (
    ApproveSheetPairingRequest,
    ComparisonRequest,
    RunCandidate,
    SavedPageText,
    SheetLinkRepository,
    SheetPairingService,
    SuppliedVersionClassification,
    VersionComparisonService,
    WithdrawSheetPairingRequest,
)
from auditmanager.comparison.summaries import (
    GenerateSummaryRequest,
    SummaryService,
    SummaryStore,
)
from auditmanager.comparison.summary_input import prepare_version_summary_input
from auditmanager.comparison.summary_model import RecordedSummaryModel, recording_document
from auditmanager.comparison.summary_prompt import build_request
from auditmanager.shared.errors import DomainError, ErrorCode

PROJECT = "prj_01M2545JSD15ETSNNV904XH001"
DOCUMENT = "doc_01M2545JSD15ETSNNV904XH001"
V1 = "ver_01M2545JSD15ETSNNV904XH001"
V2 = "ver_01M2545JSD15ETSNNV904XH002"
R1 = "run_01M2545JSD15ETSNNV904XH001"
R2 = "run_01M2545JSD15ETSNNV904XH002"
EXPERT = "usr_01M2545JSD15ETSNNV904XH001"
PAGES = 12
EXPERT_ROLES = frozenset({"expert"})


def _seed(session) -> None:
    session.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'Сводка')"), {"p": PROJECT})
    session.execute(
        text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'Комплект')"),
        {"d": DOCUMENT, "p": PROJECT},
    )
    for version, ordinal, digest in ((V1, 1, "a" * 64), (V2, 2, "b" * 64)):
        session.execute(
            text("INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, "
                 "byte_size, sha256, page_count) VALUES (:v, :d, :o, 'application/pdf', 4096, :s, :n)"),
            {"v": version, "d": DOCUMENT, "o": ordinal, "s": digest, "n": PAGES},
        )


def _page(number: int, revision: str) -> str:
    frame = "\n".join(f"Штамп строка {k}" for k in range(12))
    body = "\n".join(f"Лист {number} позиция {k} размер {k * 10}" for k in range(40))
    return f"{frame}\nЛист {number} изм. {revision}\n{body}\n"


SOURCE_PAGES = {n: _page(n, "1") for n in range(1, PAGES + 1)}
# Page 7 is redrawn in the newer set; every other sheet changes only its revision mark.
TARGET_PAGES = {n: _page(n, "2") for n in range(1, PAGES + 1)} | {
    7: _page(7, "2").replace("позиция 3 размер 30", "позиция 3 размер 35"),
}
# Two sheets that are word for word the same in both sets.
SAME = {n: _page(n, "1") for n in (1, 2)}
IDENTICAL_TARGET = dict(TARGET_PAGES) | SAME


class _Classifications:
    def read_classification(self, session, *, version_uid):
        return SuppliedVersionClassification(version_uid, "R", "KJ")


class _Analyses:
    def __init__(self, source, target) -> None:
        self.source, self.target = source, target

    def runs_newest_first(self, session, *, version_uid):
        return {V1: (RunCandidate(R1, "published"),), V2: (RunCandidate(R2, "published"),)}.get(version_uid, ())

    def saved_page_text(self, session, *, run_id, version):
        return SavedPageText(run_id, "e" * 64, {R1: self.source, R2: self.target}[run_id])

    def published_findings(self, session, *, run_id):
        return ()


class _Gate:
    """The cost meter's seat, as the command sees it: counts, and can refuse."""

    def __init__(self, refuse: bool = False) -> None:
        self.refuse, self.before, self.after = refuse, 0, 0

    def before_call(self) -> None:
        self.before += 1
        if self.refuse:
            raise DomainError(ErrorCode.COST_BUDGET_EXCEEDED, budget_scope="run")

    def after_unmetered_call(self) -> tuple[str, int]:
        self.after += 1
        return "unmetered", 0


class _Spy(RecordedSummaryModel):
    """The recorded model, counting what it is asked."""

    __slots__ = ("calls",)

    def __init__(self, directory: Path) -> None:
        super().__init__(directory)
        self.calls = 0

    def complete(self, request):
        self.calls += 1
        return super().complete(request)


def _world(directory: Path, *, target=None, gate=None, model="spy"):
    links, store = SheetLinkRepository(), SummaryStore()
    comparisons = VersionComparisonService(
        classifications=_Classifications(),
        analyses=_Analyses(SOURCE_PAGES, TARGET_PAGES if target is None else target),
        section_codes=frozenset({"AR", "KJ"}),
        links=links,
        summaries=store,
    )
    spy = _Spy(directory) if model == "spy" else model
    gate = _Gate() if gate is None else gate
    return {
        "comparisons": comparisons,
        "pairings": SheetPairingService(comparisons=comparisons, links=links),
        "summaries": SummaryService(
            comparisons=comparisons, links=links, summaries=store, model=spy,
            cost_gate=(lambda: gate) if spy is not None else None,
        ),
        "model": spy,
        "gate": gate,
        "store": store,
    }


def _request(**changes):
    return ComparisonRequest(**({
        "project_uid": PROJECT, "document_uid": DOCUMENT,
        "source_version_uid": V1, "target_version_uid": V2,
    } | changes))


def _approve(session, world, page: int, key: str):
    result = world["comparisons"].compare(session, _request())
    digest = next(r.suggestion_sha256 for r in result.sheets
                  if r.source_page_number == page and r.target_page_number == page)
    return world["pairings"].approve(
        session,
        ApproveSheetPairingRequest(
            project_uid=PROJECT, document_uid=DOCUMENT, source_version_uid=V1, target_version_uid=V2,
            source_page_number=page, target_page_number=page, suggestion_sha256=digest,
        ),
        actor_uid=EXPERT, actor_label="Иванов И. И.", actor_roles=EXPERT_ROLES, idempotency_key=key,
    ).event


def _generate(session, world, key: str, roles=EXPERT_ROLES):
    return world["summaries"].generate(
        session,
        GenerateSummaryRequest(
            project_uid=PROJECT, document_uid=DOCUMENT, source_version_uid=V1, target_version_uid=V2,
        ),
        actor_uid=EXPERT, actor_label="Иванов И. И.", actor_roles=roles, idempotency_key=key,
    )


def _prompt(session, world):
    """The request the service will make, computed independently of the command."""
    evidence = world["comparisons"].sealed_evidence(session, _request())
    assert evidence is not None and evidence.seal is not None
    return build_request(prepare_version_summary_input(
        version_pair=evidence.pair, raw_diffs=evidence.raw_diffs, raw_seal=evidence.seal,
    ))


def _record(directory: Path, prompt, statements: list[dict] | str) -> None:
    reply = statements if isinstance(statements, str) else json.dumps(
        {"statements": statements}, ensure_ascii=False)
    document = recording_document(
        request=prompt, output_text=reply, input_tokens=120, output_tokens=40,
        note="test", origin={"kind": "synthetic"},
    )
    (directory / f"{prompt.request_sha256}.json").write_text(
        json.dumps(document, ensure_ascii=False), encoding="utf-8")


def _raw(session, world) -> str:
    """The approved pairs' raw differences as bytes, summary left out."""
    approved = world["comparisons"].compare(session, _request()).approved_pairs
    return json.dumps(asdict(approved)["items"], ensure_ascii=False, sort_keys=True, default=str)


def _rows(session) -> list[tuple]:
    return list(session.execute(text(
        "SELECT summary_id, state, rejection_reason, provider_mode, model_identity, cost_basis, cost_micros "
        "FROM comparison_summary WHERE project_uid = :p ORDER BY created_at"), {"p": PROJECT}).all())


def _events(session, summary_id: str | None = None) -> list[tuple]:
    statement = ("SELECT audit_event_id, event_type, aggregate_id, payload FROM audit_event "
                 "WHERE event_type = 'comparison.summary_generated'")
    if summary_id is not None:
        return list(session.execute(text(statement + " AND audit_event_id = :i"), {"i": summary_id}).all())
    return list(session.execute(text(statement)).all())


def _reason(error: DomainError) -> str:
    return str(error.detail_fields["conflict_reason"])


@pytest.fixture
def seeded(comparison_session):
    _seed(comparison_session)
    return comparison_session


def test_a_summary_is_generated_from_the_sealed_input_and_stored_append_only(seeded, tmp_path) -> None:
    world = _world(tmp_path)
    link = _approve(seeded, world, 7, "summary-approve-1")
    prompt = _prompt(seeded, world)
    assert prompt.hunk_ids == (f"{link.sheet_link_id}:0", f"{link.sheet_link_id}:1")
    _record(tmp_path, prompt, [
        {"text": "Размер на листе 7 изменён с 30 на 35.", "hunk_ids": [prompt.hunk_ids[1]]},
        {"text": "Изменена отметка изменения.", "hunk_ids": [prompt.hunk_ids[0]]},
    ])
    outcome = _generate(seeded, world, "summary-key-1")
    stored = outcome.summary
    assert outcome.replayed is False and stored.state == "ready" and stored.rejection_reason is None
    assert stored.summary_id.startswith("evt_") and stored.link_revision == 1
    assert (stored.provider_mode, stored.model_identity) == ("recorded", "recorded")
    assert (stored.cost_basis, stored.cost_micros) == ("unmetered", 0)
    assert stored.input_sha256 == prompt.input_sha256 and stored.request_sha256 == prompt.request_sha256
    assert stored.raw_evidence_seal_sha256 == link.raw_evidence_seal_sha256
    assert [(s.text, s.hunk_ids) for s in stored.statements] == [
        ("Размер на листе 7 изменён с 30 на 35.", (prompt.hunk_ids[1],)),
        ("Изменена отметка изменения.", (prompt.hunk_ids[0],)),
    ]
    assert (world["gate"].before, world["gate"].after, world["model"].calls) == (1, 1, 1)
    # the audit event is the summary's own identity, ids and digests only
    (event,) = _events(seeded, stored.summary_id)
    assert event[2] == stored.comparison_id
    assert set(event[3]) == {"comparison_id", "link_revision", "summary_id", "input_sha256",
                             "raw_evidence_seal_sha256", "state", "actor_uid"}
    assert "Размер" not in str(event[3])
    assert [row[0] for row in _rows(seeded)] == [stored.summary_id]


def test_an_exact_repeat_answers_the_stored_summary_and_never_calls_the_model_again(seeded, tmp_path) -> None:
    world = _world(tmp_path)
    _approve(seeded, world, 7, "summary-approve-2")
    prompt = _prompt(seeded, world)
    _record(tmp_path, prompt, [{"text": "Размер изменён.", "hunk_ids": [prompt.hunk_ids[1]]}])
    first = _generate(seeded, world, "summary-key-2")
    same_key = _generate(seeded, world, "summary-key-2")
    other_key = _generate(seeded, world, "summary-key-3")
    assert (same_key.replayed, other_key.replayed) == (True, True)
    assert same_key.summary == first.summary == other_key.summary
    assert world["model"].calls == 1 and world["gate"].before == 1
    assert len(_rows(seeded)) == 1


def test_a_reply_citing_a_span_that_does_not_exist_is_recorded_as_rejected_and_is_not_an_error(
    seeded, tmp_path
) -> None:
    world = _world(tmp_path)
    link = _approve(seeded, world, 7, "summary-approve-3")
    prompt = _prompt(seeded, world)
    _record(tmp_path, prompt, [{"text": "Выдумано.", "hunk_ids": [f"{link.sheet_link_id}:9"]}])
    outcome = _generate(seeded, world, "summary-key-4")
    assert outcome.summary.state == "rejected" and outcome.summary.statements == ()
    assert outcome.summary.rejection_reason == "unknown_hunk_reference"
    assert world["gate"].after == 1  # the reply was paid for, so it is recorded
    assert [row[1:3] for row in _rows(seeded)] == [("rejected", "unknown_hunk_reference")]
    approved = world["comparisons"].compare(seeded, _request()).approved_pairs
    assert approved.summary.state == "rejected" and approved.summary.statements == ()


def test_the_summary_never_changes_the_raw_differences(seeded, tmp_path) -> None:
    world = _world(tmp_path)
    _approve(seeded, world, 7, "summary-approve-4")
    before = _raw(seeded, world)
    prompt = _prompt(seeded, world)
    _record(tmp_path, prompt, [{"text": "Размер изменён.", "hunk_ids": [prompt.hunk_ids[1]]}])
    _generate(seeded, world, "summary-key-5")
    after = _raw(seeded, world)
    assert after == before and '"hunk_id"' in before
    # and the summary is read beside them, with its label
    summary = world["comparisons"].compare(seeded, _request()).approved_pairs.summary
    assert summary is not None and summary.state == "ready" and summary.is_current is True
    assert summary.label == "Сводка подготовлена моделью, проверка человеком не проводилась"
    assert summary.provider_mode == "recorded" and summary.statements[0].text == "Размер изменён."


def test_a_summary_of_a_superseded_approval_set_is_marked_and_a_new_one_is_a_new_row(seeded, tmp_path) -> None:
    world = _world(tmp_path)
    _approve(seeded, world, 7, "summary-approve-5")
    first_prompt = _prompt(seeded, world)
    _record(tmp_path, first_prompt, [{"text": "Размер изменён.", "hunk_ids": [first_prompt.hunk_ids[1]]}])
    first = _generate(seeded, world, "summary-key-6").summary
    _approve(seeded, world, 8, "summary-approve-6")
    read = world["comparisons"].compare(seeded, _request()).approved_pairs
    assert read.link_revision == 2 and read.summary.summary_id == first.summary_id
    assert read.summary.is_current is False
    second_prompt = _prompt(seeded, world)
    assert second_prompt.input_sha256 != first_prompt.input_sha256
    _record(tmp_path, second_prompt, [{"text": "Изменены два листа.", "hunk_ids": list(second_prompt.hunk_ids[:2])}])
    second = _generate(seeded, world, "summary-key-7")
    assert second.replayed is False and second.summary.link_revision == 2
    assert world["comparisons"].compare(seeded, _request()).approved_pairs.summary.is_current is True
    assert len(_rows(seeded)) == 2


def test_nothing_is_called_without_a_model_a_sealed_set_or_a_changed_line(seeded, tmp_path, monkeypatch) -> None:
    world = _world(tmp_path)
    # 1. no approved pair: not sealed
    with pytest.raises(DomainError) as refused, seeded.begin_nested():
        _generate(seeded, world, "summary-key-8")
    assert _reason(refused.value) == "summary_evidence_not_sealed"
    # 2. a pair whose pages are identical: nothing to summarise
    same = _world(tmp_path, target=IDENTICAL_TARGET)
    _approve(seeded, same, 1, "summary-approve-7")
    with pytest.raises(DomainError) as refused, seeded.begin_nested():
        _generate(seeded, same, "summary-key-9")
    assert _reason(refused.value) == "summary_input_empty"
    # 3. an input beyond the bound is refused, never shortened
    _approve(seeded, same, 7, "summary-approve-8")
    monkeypatch.setattr("auditmanager.comparison.summary_input.MAX_CHANGED_LINES", 1)
    with pytest.raises(DomainError) as refused, seeded.begin_nested():
        _generate(seeded, same, "summary-key-10")
    assert _reason(refused.value) == "summary_input_too_large"
    # 4. no model in the process (anything but recorded mode): dependency_unavailable, nothing stored
    bare = _world(tmp_path, model=None)
    with pytest.raises(DomainError) as refused, seeded.begin_nested():
        _generate(seeded, bare, "summary-key-11")
    assert refused.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert refused.value.detail_fields["dependency"] == "comparison_summary_model"
    assert world["model"].calls == same["model"].calls == 0 and _rows(seeded) == []


def test_the_cost_ceiling_halts_before_the_call_and_the_role_is_checked_first(seeded, tmp_path) -> None:
    halting = _world(tmp_path, gate=_Gate(refuse=True))
    _approve(seeded, halting, 7, "summary-approve-9")
    prompt = _prompt(seeded, halting)
    _record(tmp_path, prompt, [{"text": "Размер изменён.", "hunk_ids": [prompt.hunk_ids[1]]}])
    with pytest.raises(DomainError) as refused, seeded.begin_nested():
        _generate(seeded, halting, "summary-key-12")
    assert refused.value.code is ErrorCode.COST_BUDGET_EXCEEDED
    assert halting["model"].calls == 0 and _rows(seeded) == []
    with pytest.raises(DomainError) as denied, seeded.begin_nested():
        _generate(seeded, halting, "summary-key-13", roles=frozenset({"admin"}))
    assert denied.value.code is ErrorCode.PERMISSION_DENIED
    assert denied.value.detail_fields["required_capability"] == "role:expert"
    assert halting["gate"].before == 1  # the refused role never reached the meter


def test_a_model_that_reports_a_cost_this_wave_cannot_verify_is_refused(seeded, tmp_path) -> None:
    class Metered(RecordedSummaryModel):
        __slots__ = ()

        @property
        def unmetered(self) -> bool:
            return False

    world = _world(tmp_path, model=Metered(tmp_path))
    _approve(seeded, world, 7, "summary-approve-10")
    prompt = _prompt(seeded, world)
    _record(tmp_path, prompt, [{"text": "Размер изменён.", "hunk_ids": [prompt.hunk_ids[1]]}])
    with pytest.raises(DomainError) as refused, seeded.begin_nested():
        _generate(seeded, world, "summary-key-14")
    assert refused.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert refused.value.detail_fields["reason"] == "cost_unverifiable"
    assert _rows(seeded) == []


def test_a_missing_recording_is_an_explicit_refusal_and_stores_nothing(seeded, tmp_path) -> None:
    world = _world(tmp_path)
    _approve(seeded, world, 7, "summary-approve-11")
    with pytest.raises(DomainError) as refused, seeded.begin_nested():
        _generate(seeded, world, "summary-key-15")
    assert refused.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert refused.value.detail_fields["reason"] == "recording_missing"
    assert _rows(seeded) == []


def test_the_recording_is_keyed_by_the_input_so_another_input_has_no_answer(seeded, tmp_path) -> None:
    world = _world(tmp_path)
    _approve(seeded, world, 7, "summary-approve-12")
    prompt = _prompt(seeded, world)
    _record(tmp_path, prompt, [{"text": "Размер изменён.", "hunk_ids": [prompt.hunk_ids[1]]}])
    # the newer set's page 7 is redrawn once more: the recording above answers another question
    redrawn = TARGET_PAGES | {7: TARGET_PAGES[7].replace("размер 35", "размер 36")}
    other = _world(tmp_path, target=redrawn)
    # its approval would have to be re-made over the new text; the old approval is then text_changed,
    # so the summary is refused before any recording is read
    with pytest.raises(DomainError) as refused, seeded.begin_nested():
        _generate(seeded, other, "summary-key-16")
    assert _reason(refused.value) == "summary_evidence_not_sealed"


def test_the_database_holds_the_summary_rules(seeded, tmp_path) -> None:
    world = _world(tmp_path)
    link = _approve(seeded, world, 7, "summary-approve-13")
    prompt = _prompt(seeded, world)
    _record(tmp_path, prompt, [{"text": "Размер изменён.", "hunk_ids": [prompt.hunk_ids[1]]}])
    stored = _generate(seeded, world, "summary-key-17").summary
    for statement in (
        "UPDATE comparison_summary SET state = 'rejected'",
        "DELETE FROM comparison_summary",
    ):
        with pytest.raises(DBAPIError) as refused, seeded.begin_nested():
            seeded.execute(text(statement))
        assert str(getattr(refused.value.orig, "sqlstate", "")) == "AM003"
    # a later approval supersedes the revision: a summary of the old set can no longer be written
    _approve(seeded, world, 8, "summary-approve-14")
    columns = ("summary_id, comparison_id, link_revision, project_uid, raw_evidence_seal_sha256, input_sha256, "
               "request_sha256, prompt_version, provider_mode, model_identity, state, rejection_reason, "
               "statements, cost_basis, cost_micros, actor_user_uid, actor_label, command_id")
    copy = ("INSERT INTO comparison_summary (" + columns + ") SELECT 'evt_01M2545JSD15ETSNNV904XHZ99', "
            "comparison_id, link_revision, project_uid, raw_evidence_seal_sha256, input_sha256 || '', "
            "request_sha256, 'comparison-summary-v2', provider_mode, model_identity, state, rejection_reason, "
            "statements, cost_basis, cost_micros, actor_user_uid, actor_label, command_id "
            "FROM comparison_summary WHERE summary_id = :i")
    with pytest.raises(DBAPIError) as refused, seeded.begin_nested():
        seeded.execute(text(copy), {"i": stored.summary_id})
    assert str(getattr(refused.value.orig, "sqlstate", "")) in {"AM001", "23505"}
    assert link.link_revision == 1 and len(_rows(seeded)) == 1


def test_the_committed_recording_answers_the_synthetic_pair(seeded) -> None:
    """The recording shipped under ``fixtures/recorded/comparison`` answers the request over the
    synthetic pair of ``fixtures/recorded/comparison/build_fixtures.py``, through the default directory."""
    import importlib.util

    builder = Path(__file__).resolve().parents[3] / "fixtures/recorded/comparison/build_fixtures.py"
    spec = importlib.util.spec_from_file_location("comparison_fixture_builder", builder)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    prompt = module.synthetic_request()
    reply = RecordedSummaryModel().complete(prompt)
    parsed = json.loads(reply.output_text)
    assert parsed["statements"] and all(s["hunk_ids"] for s in parsed["statements"])
    assert set(i for s in parsed["statements"] for i in s["hunk_ids"]) <= set(prompt.hunk_ids)


def _withdraw(session, world, link, key: str):
    return world["pairings"].withdraw(
        session,
        WithdrawSheetPairingRequest(
            project_uid=PROJECT, document_uid=DOCUMENT, source_version_uid=V1,
            sheet_link_id=link.sheet_link_id,
        ),
        actor_uid=EXPERT, actor_label="Иванов И. И.", actor_roles=EXPERT_ROLES, idempotency_key=key,
    ).event


def _approved_and_summarised(seeded, tmp_path, tag: str):
    """Page 7 approved, its summary generated once under ``summary-replay-<tag>``."""
    world = _world(tmp_path)
    link = _approve(seeded, world, 7, f"summary-replay-approve-{tag}")
    prompt = _prompt(seeded, world)
    _record(tmp_path, prompt, [{"text": "Размер изменён.", "hunk_ids": [prompt.hunk_ids[1]]}])
    first = _generate(seeded, world, f"summary-replay-{tag}")
    return world, link, first


def test_a_replay_of_a_fresh_summary_is_still_current_and_every_first_answer_is(seeded, tmp_path) -> None:
    world, _link, first = _approved_and_summarised(seeded, tmp_path, "fresh")
    replay = _generate(seeded, world, "summary-replay-fresh")
    other_key = _generate(seeded, world, "summary-replay-fresh-other")
    assert first.is_current is True and first.replayed is False
    assert (replay.replayed, replay.is_current, replay.summary) == (True, True, first.summary)
    assert (other_key.replayed, other_key.is_current) == (True, True)
    assert world["model"].calls == 1


def test_a_replay_after_the_pair_was_withdrawn_returns_the_old_summary_but_not_as_current(seeded, tmp_path) -> None:
    world, link, first = _approved_and_summarised(seeded, tmp_path, "withdrawn")
    _withdraw(seeded, world, link, "summary-replay-withdraw-withdrawn")
    replay = _generate(seeded, world, "summary-replay-withdrawn")
    assert replay.replayed is True and replay.summary == first.summary
    assert replay.is_current is False
    # the read path says the same about the same row
    read = world["comparisons"].compare(seeded, _request()).approved_pairs.summary
    assert read.summary_id == first.summary.summary_id and read.is_current is False
    assert world["model"].calls == 1  # a replay never pays


def test_a_replay_after_another_pair_was_approved_is_not_current(seeded, tmp_path) -> None:
    world, _link, first = _approved_and_summarised(seeded, tmp_path, "later")
    _approve(seeded, world, 8, "summary-replay-approve-later-8")
    replay = _generate(seeded, world, "summary-replay-later")
    assert replay.replayed is True and replay.summary == first.summary and replay.is_current is False


def test_a_replay_after_withdraw_and_approve_again_is_not_current_though_the_set_looks_the_same(
    seeded, tmp_path
) -> None:
    world, link, first = _approved_and_summarised(seeded, tmp_path, "again")
    _withdraw(seeded, world, link, "summary-replay-withdraw-again")
    _approve(seeded, world, 7, "summary-replay-approve-again-7")
    read = world["comparisons"].compare(seeded, _request()).approved_pairs
    assert read.link_revision == 3 and read.summary.is_current is False
    replay = _generate(seeded, world, "summary-replay-again")
    assert replay.replayed is True and replay.summary.link_revision == 1
    assert replay.is_current is False


def test_a_replay_after_the_text_of_the_approved_sheet_changed_is_not_current(seeded, tmp_path) -> None:
    world, _link, first = _approved_and_summarised(seeded, tmp_path, "text")
    redrawn = TARGET_PAGES | {7: TARGET_PAGES[7].replace("размер 35", "размер 36")}
    changed = _world(tmp_path, target=redrawn)
    replay = _generate(seeded, changed, "summary-replay-text")
    assert replay.replayed is True and replay.summary == first.summary
    assert replay.is_current is False
