"""The consent estimate of the V3 plans (`V3Method.counts`): the first request is the bounded catalogue call, every
resume estimates exactly the next known request, nothing is charged in advance for work that is not planned yet.

SPRINT3-STAGE-1030.md ("Consent and durable recovery"): "Initial consent estimates the bounded catalogue call.
Each subsequent resume estimates the exact next known plan using its actual prompt/output bounds."
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from auditmanager.comparison.ai_jobs.model import AiMode
from auditmanager.comparison.stage_ai.validation import StageAiValidationError
from auditmanager.comparison.stage_v3 import bridge, consolidation as c, windowed as w
from auditmanager.comparison.stage_v3.policy import GLOBAL_LIMITS, GLOBAL_VERSION, LIMITS, VERSION
from auditmanager.shared.errors import DomainError
from tests.unit.stage_v3.windowed_fixture import MODEL, drive, mapping_edit, numbered, region, snapshot_of

WINDOWED = {"plan_version": VERSION, "bundle": w.BUNDLE, "limits": LIMITS}
GLOBAL = {"plan_version": GLOBAL_VERSION, "bundle": c.BUNDLE, "limits": GLOBAL_LIMITS}


class Repo:
    def __init__(self, source):
        self.source = source

    def revision(self, _session, _revision):
        return self.source

    def run(self, _session, _run):
        return {"revision_id": "revision-test"}


def method(source, policy, monkeypatch, *, saved=None, changed=False, text_less=()):
    """A V3Method over `source` whose saved page profiles are the snapshot's own (or changed, when asked)."""
    profiles = {row["profile_id"]: row for row in source["all_profiles"]}

    class Reader:
        def read_page_profile(self, profile_id):
            row = profiles[profile_id]
            return SimpleNamespace(profile_id=profile_id, row=SimpleNamespace(
                profile_blob_id="blob", content_key="changed" if changed else row["content_key"], version_uid=row["version_uid"]))

    def fragments(profile, side):
        if profile.profile_id in text_less:
            return []
        return [SimpleNamespace(normalised_text=row["normalised_text"], content_key=row["content_key"])
                for row in source["fragments"] if row["page_profile_id"] == profile.profile_id]

    monkeypatch.setattr(bridge, "extract_fragments", fragments)
    monkeypatch.setattr(bridge, "results", lambda _session, _run, bundle=None: dict(saved or {}))
    return bridge.V3Method(Repo(source), profile_reader=Reader(), v3_policy=policy)


def request(mode=AiMode.START, run=None):
    return SimpleNamespace(scope=SimpleNamespace(stage_link_revision_id="revision-test", stage_chain_run_id=run), mode=mode)


SMALL = snapshot_of([["ширина прохода 100 мм"]], [["ширина прохода 120 мм"]])


def test_the_first_estimate_of_a_windowed_run_is_one_catalogue_call_independent_of_the_text_volume(monkeypatch):
    short = method(SMALL, WINDOWED, monkeypatch).counts(None, request())
    long_source = snapshot_of([["я" * 35_000]], [["я" * 35_000]])               # within the legacy plan's 80,000 as well
    long = method(long_source, WINDOWED, monkeypatch).counts(None, request())
    for counts in (short, long):
        assert len(counts.groups) == 1 and counts.groups[0].calls == 1 and counts.groups[0].output_tokens == 8000
        assert counts.units == 1 and counts.sheets == 2 and counts.versions == 2
    assert short.groups[0].prompt_chars == long.groups[0].prompt_chars          # the catalogue is bounded: text volume is not charged
    legacy_short = method(SMALL, None, monkeypatch).counts(None, request())
    legacy_long = method(long_source, None, monkeypatch).counts(None, request())
    assert legacy_short.groups[0].output_tokens == 4000
    assert legacy_long.groups[0].prompt_chars > legacy_short.groups[0].prompt_chars + 60_000      # the legacy plan sends the text


def test_the_estimate_grows_with_the_number_of_pages_the_catalogue_lists(monkeypatch):
    two = method(SMALL, WINDOWED, monkeypatch).counts(None, request()).groups[0].prompt_chars
    many = method(snapshot_of([["t"]] * 20, [["t"]] * 20), WINDOWED, monkeypatch).counts(None, request()).groups[0].prompt_chars
    assert many > two + 10_000


def test_the_estimate_refuses_exactly_what_the_plan_would_refuse(monkeypatch):
    method(snapshot_of([["t"]] * 32, [["t"]] * 32), WINDOWED, monkeypatch).counts(None, request())            # 64 pages
    method(snapshot_of([["t"]] * 9, [["t"]] * 9), WINDOWED, monkeypatch).counts(None, request())               # more than legacy admits
    with pytest.raises(StageAiValidationError, match="source_budget"):
        method(snapshot_of([["t"]] * 33, [["t"]] * 32), WINDOWED, monkeypatch).counts(None, request())          # 65 pages
    with pytest.raises(StageAiValidationError, match="source_budget"):
        method(snapshot_of([["t"]] * 9, [["t"]] * 9), None, monkeypatch).counts(None, request())               # the legacy plan: 16 pages
    with pytest.raises(StageAiValidationError, match="source_budget"):
        method(snapshot_of([["t"] * 801], [["t"] * 800]), WINDOWED, monkeypatch).counts(None, request())        # 1601 fragments
    with pytest.raises(StageAiValidationError, match="source_budget"):
        method(snapshot_of([["я" * 120_001]], [["я" * 120_000]]), WINDOWED, monkeypatch).counts(None, request())  # 240001 characters


@pytest.mark.xfail(strict=True, reason="D-532: V3Method.counts admits a one-sided revision that windowed.source refuses at plan time "
                                       "(the fix is in bridge.py, outside this lane)")
def test_the_estimate_refuses_a_one_sided_revision_as_the_plan_does(monkeypatch):
    source = snapshot_of([["t"]] * 2, [])
    with pytest.raises(StageAiValidationError, match="source_budget"):
        w.source(source)                                                                                     # the plan refuses it ...
    with pytest.raises(StageAiValidationError, match="source_budget"):
        method(source, WINDOWED, monkeypatch).counts(None, request())                                        # ... the estimate must too


def test_a_page_without_text_or_a_changed_saved_profile_is_refused_before_any_spend(monkeypatch):
    with pytest.raises(StageAiValidationError, match="v3_native_page_without_text"):
        method(SMALL, WINDOWED, monkeypatch, text_less={"cpr_left_1"}).counts(None, request())
    with pytest.raises(DomainError):
        method(SMALL, WINDOWED, monkeypatch, changed=True).counts(None, request())


def test_a_resume_estimates_only_the_next_known_request_of_the_windowed_plan(monkeypatch):
    source = snapshot_of([numbered(65)], [numbered(3, "размер 200 мм новый {n}")])
    run = drive(w, source)
    order = [group for _, group in run.calls]
    assert [name for name, _ in run.calls] == ["mapper", "miner", "miner", "dedupe", "verify", "verify"]

    def next_request(done):
        saved = {group: run.results[group] for group in order[:done]}
        counts = method(source, WINDOWED, monkeypatch, saved=saved).counts(None, request(AiMode.LEFT, "run-1"))
        for phase in ("review", "classify", "synthesize"):
            pending = [plan for plan in w.plans_for(phase, source, saved, "estimate") if plan.group_id not in saved]
            if pending:
                break
        return counts, pending

    for done in range(len(order)):
        counts, pending = next_request(done)
        first = pending[0]
        assert len(counts.groups) == 1 and counts.groups[0].calls == 1
        assert counts.groups[0].prompt_chars == first.prompt_chars and counts.groups[0].output_tokens == first.max_output_tokens
    counts, _ = next_request(2)                       # mapper and the first miner pack are saved: the second pack is next, not the dedupe
    second_pack = run.plans[order[2]]
    assert counts.groups[0].prompt_chars == second_pack.prompt_chars
    finished, _ = next_request(len(order))
    assert finished.groups == () and finished.units == 0


def test_a_resume_of_the_global_plan_estimates_the_next_consolidator_call(monkeypatch):
    source = snapshot_of([["ширина прохода 100 мм"]] * 9, [["ширина прохода 120 мм"]] * 9)
    run = drive(c, source, edit=mapping_edit([region(f"R{n:03d}", [n], [n]) for n in range(1, 10)]))
    consolidators = [group for name, group in run.calls if name == "consolidate"]
    assert len(consolidators) == 2
    saved = {group: run.results[group] for _, group in run.calls[:-1]}                # the last Consolidator call is still to pay
    counts = method(source, GLOBAL, monkeypatch, saved=saved).counts(None, request(AiMode.LEFT, "run-1"))
    last = run.plans[consolidators[-1]]
    assert counts.groups[0].prompt_chars == last.prompt_chars and counts.groups[0].output_tokens == last.max_output_tokens == 6000
    done = method(source, GLOBAL, monkeypatch, saved=dict(run.results)).counts(None, request(AiMode.LEFT, "run-1"))
    assert done.groups == ()


def test_a_start_estimate_ignores_anything_saved(monkeypatch):
    run = drive(w, SMALL)
    counts = method(SMALL, WINDOWED, monkeypatch, saved=dict(run.results)).counts(None, request(AiMode.START, "run-1"))
    assert len(counts.groups) == 1 and counts.groups[0].output_tokens == 8000
