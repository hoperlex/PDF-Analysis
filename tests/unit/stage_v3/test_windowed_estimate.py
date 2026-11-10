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
from auditmanager.comparison.stage_v3 import bridge, consolidation as c, procedures as legacy, windowed as w
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


def method(source, policy, monkeypatch, *, saved=None, changed=False, text_less=(), rows_written=True):
    """A V3Method over `source` whose saved page profiles are the snapshot's own (or changed, when asked).

    `rows_written=False` is the state in which the consent estimate is asked: the profiles hold the text, step 2 of the
    chain has not written a `stage_text_fragment` row yet, so the repository's snapshot has no fragments.
    """
    profiles = {row["profile_id"]: row for row in source["all_profiles"]}

    class Reader:
        def read_page_profile(self, profile_id):
            row = profiles[profile_id]
            return SimpleNamespace(profile_id=profile_id, row=SimpleNamespace(
                profile_blob_id="blob", content_key="changed" if changed else row["content_key"], version_uid=row["version_uid"]))

    def fragments(profile, side):
        if profile.profile_id in text_less:
            return []
        return [SimpleNamespace(normalised_text=row["normalised_text"], content_key=row["content_key"], box_anchor=row["box_anchor"])
                for row in source["fragments"] if row["page_profile_id"] == profile.profile_id]

    monkeypatch.setattr(bridge, "extract_fragments", fragments)
    monkeypatch.setattr(bridge, "results", lambda _session, _run, bundle=None: dict(saved or {}))
    return bridge.V3Method(Repo(source if rows_written else dict(source, fragments=[])), profile_reader=Reader(), v3_policy=policy)


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
    method(snapshot_of([["t"]] * 9, [["t"]] * 9), GLOBAL, monkeypatch).counts(None, request())
    refused = [(snapshot_of([["t"]] * 33, [["t"]] * 32), "65 pages"),
               (snapshot_of([["t"] * 801], [["t"] * 800]), "1601 fragments"),
               (snapshot_of([["я" * 120_001]], [["я" * 120_000]]), "240001 characters")]
    for policy in (WINDOWED, GLOBAL):                       # the windowed plans refuse with their own code, never the legacy one
        for source, _why in refused:
            with pytest.raises(StageAiValidationError, match="^v3_windowed_source_budget$"):
                method(source, policy, monkeypatch).counts(None, request())
    with pytest.raises(StageAiValidationError, match="^v3_native_source_budget$"):
        method(snapshot_of([["t"]] * 9, [["t"]] * 9), None, monkeypatch).counts(None, request())               # the legacy plan: 16 pages


@pytest.mark.parametrize("policy,rule,code", [(WINDOWED, w.source, "v3_windowed_source_budget"),
                                              (GLOBAL, w.source, "v3_windowed_source_budget"),
                                              (None, legacy.source, "v3_native_source_budget")])
def test_the_estimate_refuses_a_one_sided_revision_as_the_plan_does(monkeypatch, policy, rule, code):
    source = snapshot_of([["t"]] * 2, [])
    with pytest.raises(StageAiValidationError, match=f"^{code}$"):
        rule(source)                                                                                         # the plan refuses it ...
    with pytest.raises(StageAiValidationError, match=f"^{code}$"):
        method(source, policy, monkeypatch).counts(None, request())                                          # ... the estimate must too, with its code
    with pytest.raises(StageAiValidationError, match=f"^{code}$"):
        method(snapshot_of([], [["t"]] * 2), policy, monkeypatch).counts(None, request())                    # either side may be the empty one


@pytest.mark.parametrize("policy", [None, WINDOWED, GLOBAL], ids=["legacy", "windowed-v1", "windowed-global-v1"])
def test_the_estimate_is_given_before_the_text_rows_exist(monkeypatch, policy):
    """The consent estimate is asked before the chain's step 2 writes `stage_text_fragment` (a new pair, a new document
    version): the pages have text in their profiles, so the estimate is given, and equals the one after step 2."""
    before = method(SMALL, policy, monkeypatch, rows_written=False).counts(None, request())
    after = method(SMALL, policy, monkeypatch).counts(None, request())
    assert before == after and before.groups[0].calls == 1 and before.sheets == 2 and before.versions == 2


@pytest.mark.parametrize("policy,code", [(WINDOWED, "v3_windowed_source_budget"), (GLOBAL, "v3_windowed_source_budget"),
                                         (None, "v3_native_source_budget")], ids=["windowed-v1", "windowed-global-v1", "legacy"])
def test_the_estimate_before_the_text_rows_exist_still_refuses_what_the_plan_refuses(monkeypatch, policy, code):
    """D-532 holds on the facts of the profiles: the plan's own code, with no stored row to read."""
    refused = [snapshot_of([["t"]] * 2, []), snapshot_of([], [["t"]] * 2), snapshot_of([["t"]] * 33, [["t"]] * 32),
               snapshot_of([["t"] * 801], [["t"] * 800]), snapshot_of([["я" * 120_001]], [["я" * 120_000]])]
    if policy is None:
        refused.append(snapshot_of([["t"]] * 9, [["t"]] * 9))
    for source in refused:
        with pytest.raises(StageAiValidationError, match=f"^{code}$"):
            method(source, policy, monkeypatch, rows_written=False).counts(None, request())


def test_a_page_profile_without_stored_rows_is_read_from_its_profile_beside_stored_ones(monkeypatch):
    """Rows that exist are the plan's facts; a profile with none is read from its own text, so neither refuses."""
    source = snapshot_of([["t"]], [["t"]])
    seen = []
    real = w.source
    monkeypatch.setattr(w, "source", lambda snapshot: seen.append(snapshot["fragments"]) or real(snapshot))
    repo_rows = [row for row in source["fragments"] if row["page_profile_id"] == "cpr_left_1"]
    built = method(source, WINDOWED, monkeypatch)
    built._repo = Repo(dict(source, fragments=repo_rows))               # only the left page has a stored row
    assert built.counts(None, request()).groups[0].calls == 1
    assert [row["page_profile_id"] for row in seen[0]] == ["cpr_left_1", "cpr_right_1"]
    assert seen[0][0] is repo_rows[0]                                  # the stored row itself, not a copy made from the profile


def test_a_page_without_text_or_a_changed_saved_profile_is_refused_before_any_spend(monkeypatch):
    # The page without text is asked in the state in which one exists: its profile reads empty and step 2 has written no row for it
    # (a stored row of a profile that reads empty is not a state step 2 can leave). The plan's own rule refuses it (N3-2).
    with pytest.raises(StageAiValidationError, match="v3_native_page_without_text"):
        method(SMALL, WINDOWED, monkeypatch, text_less={"cpr_left_1"}, rows_written=False).counts(None, request())
    with pytest.raises(DomainError):
        method(SMALL, WINDOWED, monkeypatch, changed=True).counts(None, request())


#: (the plan's policy, the plan's own source rule, a source over a budget of that plan, the page of it that has no text,
#: the plan's code for the budget). The windowed plans are shown on the page-count, the fragment-count and the legacy plan on both.
OVER_BUDGET = [
    pytest.param(None, legacy.source, snapshot_of([["t"]] * 9, [["t"]] * 8), "cpr_left_1", "v3_native_source_budget", id="legacy-17-pages"),
    pytest.param(None, legacy.source, snapshot_of([["t"] * 401, ["x"]], [["t"]]), "cpr_left_2", "v3_native_source_budget", id="legacy-401-fragments"),
    pytest.param(WINDOWED, w.source, snapshot_of([["t"]] * 33, [["t"]] * 32), "cpr_left_1", "v3_windowed_source_budget", id="windowed-65-pages"),
    pytest.param(WINDOWED, w.source, snapshot_of([["t"] * 1601, ["x"]], [["t"]]), "cpr_left_2", "v3_windowed_source_budget",
                 id="windowed-1601-fragments"),
    pytest.param(GLOBAL, w.source, snapshot_of([["t"]] * 33, [["t"]] * 32), "cpr_left_1", "v3_windowed_source_budget", id="global-65-pages"),
    pytest.param(GLOBAL, w.source, snapshot_of([["t"] * 1601, ["x"]], [["t"]]), "cpr_left_2", "v3_windowed_source_budget",
                 id="global-1601-fragments"),
]


@pytest.mark.parametrize("policy,rule,source,textless,code", OVER_BUDGET)
def test_a_budget_the_source_exceeds_is_named_before_a_page_without_text_as_the_plan_does(monkeypatch, policy, rule, source, textless, code):
    """N3-2: over a budget AND a page without text, the plan's rule says the budget (it judges its budgets before its pages), so the estimate
    must say the same; the estimate used to refuse the page first, with a code the run would never give."""
    after_step_2 = dict(source, fragments=[row for row in source["fragments"] if row["page_profile_id"] != textless])
    with pytest.raises(StageAiValidationError, match=f"^{code}$"):
        rule(after_step_2)                                                                                   # the plan on the rows step 2 writes ...
    with pytest.raises(StageAiValidationError, match=f"^{code}$"):
        method(source, policy, monkeypatch, text_less={textless}, rows_written=False).counts(None, request())    # ... the estimate must too


@pytest.mark.parametrize("policy,rule,source,textless", [
    pytest.param(None, legacy.source, snapshot_of([["я" * 40_001], ["x"]], [["я" * 40_000]]), "cpr_left_2", id="legacy-80001-characters"),
    pytest.param(WINDOWED, w.source, snapshot_of([["я" * 120_001], ["x"]], [["я" * 120_000]]), "cpr_left_2", id="windowed-240001-characters"),
    pytest.param(GLOBAL, w.source, snapshot_of([["я" * 120_001], ["x"]], [["я" * 120_000]]), "cpr_left_2", id="global-240001-characters"),
])
def test_a_page_without_text_is_named_before_the_character_budget_as_the_plan_does(monkeypatch, policy, rule, source, textless):
    """The other order of the same rules: the plans judge the characters AFTER their pages, so a page without text wins there. Taking the
    plan's own rule as the reference (and not a copy of its order) keeps the estimate from drifting either way."""
    after_step_2 = dict(source, fragments=[row for row in source["fragments"] if row["page_profile_id"] != textless])
    with pytest.raises(StageAiValidationError, match="^v3_native_page_without_text$"):
        rule(after_step_2)
    with pytest.raises(StageAiValidationError, match="^v3_native_page_without_text$"):
        method(source, policy, monkeypatch, text_less={textless}, rows_written=False).counts(None, request())


@pytest.mark.parametrize("policy", [None, WINDOWED, GLOBAL], ids=["legacy", "windowed-v1", "windowed-global-v1"])
@pytest.mark.parametrize("stored", ["cpr_right_1", "cpr_left_1"], ids=["rows-of-the-right-side", "rows-of-the-left-side"])
def test_a_resume_with_the_rows_of_some_pages_only_estimates_the_opening_window(monkeypatch, policy, stored):
    """N3-1: a new document version on one side of a pair whose other side was written before; the chain is cancelled while step 2 has
    written the rows of one side only. Nothing is planned yet, so the resume is the opening call, as at start, and it must be given (it
    used to refuse `v3_native_page_without_text` for the pages without rows and the run could not be resumed)."""
    source = snapshot_of([["ширина прохода 100 мм"]], [["ширина прохода 120 мм"]])
    built = method(source, policy, monkeypatch)
    built._repo = Repo(dict(source, fragments=[row for row in source["fragments"] if row["page_profile_id"] == stored]))
    resumed = built.counts(None, request(AiMode.LEFT, "run-1"))
    opening = method(source, policy, monkeypatch, rows_written=False).counts(None, request())
    assert len(resumed.groups) == 1 and resumed.groups[0].calls == 1 and resumed.sheets == 2 and resumed.versions == 2
    assert resumed == opening


@pytest.mark.parametrize("policy", [None, WINDOWED, GLOBAL], ids=["legacy", "windowed-v1", "windowed-global-v1"])
def test_a_resume_with_the_rows_of_some_pages_only_still_refuses_what_the_plan_refuses(monkeypatch, policy):
    """The opening window is not an escape from D-532: a one-sided revision with the rows of one page stored is refused with the plan's code."""
    code = "v3_native_source_budget" if policy is None else "v3_windowed_source_budget"
    source = snapshot_of([["t"]] * 2, [])
    built = method(source, policy, monkeypatch)
    built._repo = Repo(dict(source, fragments=[row for row in source["fragments"] if row["page_profile_id"] == "cpr_left_1"]))
    with pytest.raises(StageAiValidationError, match=f"^{code}$"):
        built.counts(None, request(AiMode.LEFT, "run-1"))


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
