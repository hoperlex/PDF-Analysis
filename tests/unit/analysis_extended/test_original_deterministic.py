"""The original's deterministic critic and corrector for plan v2 (`V2-ORIGINAL-REVIEW-01`, R-154e..g).

The scenarios are those of PDF-proverka 3c994817 `tests/test_findings_deterministic_critic.py` and
`tests/test_findings_deterministic_corrector.py`, over the shape of a v2 record (observations and sources, a text layer) instead of the
original's files. The model pass of the original (checks 3 and 5) is not built, so its tests (`test_critic_semantic_unverified.py`, the
`llm_call` cases) have no counterpart; `test_no_model_pass_exists` pins that.
"""
from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path

from auditmanager.analysis.extended import original_deterministic as od
from auditmanager.analysis.extended.workflow import review_bundle_digest
from auditmanager.analysis import public

EXTENDED = Path(od.__file__).parent

#: `review_bundle_digest(section)` of the v3 bundle. The lane that added `original_deterministic.py` (`V2-ORIGINAL-REVIEW-01`) touched none of the
#: files the digest hashes, so v3's frozen `rules_sha256` was what it had been (AR `6696fb2e...`, KJ `d988f6cc...`, the tree of `ac76c1ce5`). A
#: deliberate change to the v3 bundle updates this line and says why. `CTX-CRITIC` did, on purpose: its paragraph is in `analysis/extended/review.py`,
#: which the digest hashes, so every v3 consent frozen before it refuses with `extended_rules_changed_requires_consent` (plan-v5 section 3.5).
V3_BUNDLE_DIGEST_AT_BASE = {
    "AR": "d6be61b5ed8387ecfb0da7e69ef9f78aaf16f5a6464945657c9f86f40a086143",
    "KJ": "f22ce6ccf241d39d9afd659492734eee378e7e076a5c710563111e9880ba2674",
}


def image(source_id, page):
    return {"source_id": source_id, "kind": "image", "page_number": page}


def text_source(source_id, page, quote):
    return {"source_id": source_id, "kind": "text", "page_number": page, "quote": quote}


def observation(number, source_ids, **fields):
    value = {"observation_id": f"xobs_{number:024d}", "title": f"Наблюдение {number}", "description": "Описание без ссылок",
        "source_ids": source_ids, "norm_queries": [], "norm_status": "unavailable", "norm_candidates": []}
    value.update(fields)
    return value


QUOTE = "Толщина утеплителя наружной стены 150 мм"
PAGES = {n: f"Текст страницы {n}." for n in range(1, 15)}


def run(observations, sources, pages=None):
    pages = PAGES if pages is None else pages
    done = od.review(observations, sources, pages)
    corrections = od.correct(done)
    return done, corrections


# --- check 1: evidence_presence ---------------------------------------------------------------------------------------------------------

def test_no_evidence():
    items = [observation(1, [])]
    done, corrections = run(items, [])
    critic = items[0]["critic"]
    assert critic["original_verdict"] == "no_evidence" and critic["failed_checks"] == ["evidence_presence"]
    assert critic["checks"] == {"evidence_presence": "fail", "block_exists": "not_applicable", "page_sheet_correct": "not_applicable"}
    assert len(done) == 1 and corrections[0]["action"] == "needs_context"


def test_source_ids_that_are_not_a_list_are_no_evidence():
    for value in (None, "B1-AAAA-BBB", 7, [None, ""]):
        items = [observation(1, value)]
        run(items, [image("B1-AAAA-BBB", 4)])
        assert items[0]["critic"]["original_verdict"] == "no_evidence"


def test_a_block_named_in_the_text_counts_as_evidence_when_it_exists():
    items = [observation(1, [], description="См. блок AB12-CD34-EF5 на плане"), observation(2, [], description="См. блок ZZ99-ZZ99-ZZ9")]
    run(items, [image("AB12-CD34-EF5", 4)])
    assert [item["critic"]["original_verdict"] for item in items] == ["pass", "phantom_block"]


# --- check 2: block_exists ---------------------------------------------------------------------------------------------------------------

def test_phantom_block():
    items = [observation(1, ["GHOST-XXXX-YYY"])]
    run(items, [image("REAL-AAAA-BBB", 4)])
    critic = items[0]["critic"]
    assert critic["original_verdict"] == "phantom_block" and critic["failed_checks"] == ["block_exists"]
    assert "GHOST-XXXX-YYY" in critic["explanation"]


def test_one_existing_source_is_enough_the_original_flags_only_when_none_exists():
    items = [observation(1, ["GHOST-XXXX-YYY", "REAL-AAAA-BBB"])]
    run(items, [image("REAL-AAAA-BBB", 4)])
    assert items[0]["critic"]["original_verdict"] == "pass"


# --- check 4: page_sheet_correct ---------------------------------------------------------------------------------------------------------

def test_page_mismatch_tight_evidence():
    pages = {**PAGES, 4: f"Фрагмент. {QUOTE}. Конец.", 14: "Другой текст"}
    items = [observation(1, ["text:0"])]
    done, corrections = run(items, [text_source("text:0", 14, QUOTE)], pages)
    critic = items[0]["critic"]
    assert critic["original_verdict"] == "page_mismatch" and critic["failed_checks"] == ["page_sheet_correct"]
    assert "стр. 14" in critic["explanation"] and "стр. 4" in critic["explanation"]


def test_page_mismatch_skipped_when_the_quotation_is_broad():
    """The original flags only an exact binding (at most two pages); a quotation found on three other pages says nothing."""
    pages = {**PAGES, **{n: f"Раздел. {QUOTE}." for n in (4, 5, 6)}}
    items = [observation(1, ["text:0"])]
    run(items, [text_source("text:0", 14, QUOTE)], pages)
    assert items[0]["critic"]["original_verdict"] == "pass"


def test_quotation_on_the_stated_page_passes_whatever_else_holds_it():
    pages = {**PAGES, 14: f"Тут {QUOTE}.", 4: f"И тут {QUOTE}."}
    items = [observation(1, ["text:0"])]
    run(items, [text_source("text:0", 14, QUOTE)], pages)
    assert items[0]["critic"]["original_verdict"] == "pass" and items[0]["critic"]["checks"]["page_sheet_correct"] == "pass"


def test_a_paraphrase_found_nowhere_and_a_short_quotation_say_nothing_about_the_page():
    items = [observation(1, ["text:0"]), observation(2, ["text:1"])]
    run(items, [text_source("text:0", 14, "Совсем другая формулировка, чем в тексте"), text_source("text:1", 14, "п. 5")], {**PAGES, 4: "п. 5"})
    assert [item["critic"]["original_verdict"] for item in items] == ["pass", "pass"]


def test_whitespace_and_case_do_not_hide_a_quotation():
    pages = {**PAGES, 4: "Толщина   утеплителя\nНАРУЖНОЙ стены 150 мм"}
    items = [observation(1, ["text:0"])]
    run(items, [text_source("text:0", 14, QUOTE)], pages)
    assert items[0]["critic"]["original_verdict"] == "page_mismatch"


def test_image_sources_have_no_page_claim_here():
    items = [observation(1, ["B1-AAAA-BBB"])]
    run(items, [image("B1-AAAA-BBB", 4)])
    critic = items[0]["critic"]
    assert critic["original_verdict"] == "pass" and critic["checks"]["page_sheet_correct"] == "not_applicable"


# --- the corrector: proposals only, nothing deleted ---------------------------------------------------------------------------------------

def mixed_record():
    pages = {**PAGES, 4: f"Фрагмент. {QUOTE}. Конец."}
    sources = [image("B1-AAAA-BBB", 4), text_source("text:0", 14, QUOTE)]
    items = [observation(1, ["B1-AAAA-BBB"]), observation(2, []), observation(3, ["GHOST-XXXX-YYY"]), observation(4, ["text:0"])]
    return items, sources, pages


def test_no_observation_is_ever_deleted_and_none_is_changed():
    items, sources, pages = mixed_record()
    before = deepcopy(items)
    done, corrections = run(items, sources, pages)
    assert len(done) == len(items) == 4
    annotations = {"critic", "review_status", "correction"}
    assert [{k: v for k, v in item.items() if k not in annotations} for item in items] == before
    assert [item["review_status"] for item in items] == ["reviewed"] * 4


def test_the_rows_are_advice_and_never_a_cancellation_or_an_expert_decision():
    items, sources, pages = mixed_record()
    done, corrections = run(items, sources, pages)
    for _, critic, _ in done:
        assert critic["llm_decision"] != "reject" and critic["expert_decision"] is False
        assert critic["status"] == "requires_expert_review" and critic["model_called"] is False and critic["mode"] == "deterministic"
        assert critic["confidence"] is None and critic["evidence_checked"] is False
    for row in corrections:
        assert row["expert_decision"] is False and row["status"] == "requires_expert_review" and row["model_called"] is False
    assert {critic["llm_decision"] for _, critic, _ in done} == {"accept", "needs_human", "rewrite"}


def test_verdict_table_is_the_originals_six_verdicts_and_never_rejects():
    assert set(od.VERDICT_ADVICE) == {"pass", "no_evidence", "phantom_block", "weak_evidence", "page_mismatch", "contradicts_text"}
    assert all(row[0] in {"accept", "borderline", "needs_human", "rewrite"} for row in od.VERDICT_ADVICE.values())
    # v3's own rules for a critic row: ``rewrite`` needs a correction and ``accept`` none.
    for decision, _, _, needs_correction in od.VERDICT_ADVICE.values():
        assert (decision == "rewrite") == needs_correction


def test_pass_gets_no_correction_row_and_keeps_every_other_field():
    items = [observation(1, ["B1-AAAA-BBB"], norm_quote="СП 256... п.7.1", norm_status="candidates")]
    done, corrections = run(items, [image("B1-AAAA-BBB", 4)])
    assert corrections == [] and "correction" not in items[0]
    assert items[0]["norm_quote"] == "СП 256... п.7.1" and items[0]["norm_status"] == "candidates"


def test_no_evidence_and_phantom_ask_for_a_source_and_propose_no_text():
    items = [observation(1, []), observation(2, ["GHOST-XXXX-YYY"])]
    run(items, [image("REAL-AAAA-BBB", 4)])
    for item in items:
        row = item["correction"]
        assert row["action"] == "needs_context" and row["candidate"] is None and row["required_context"]
        assert row["original"]["title"] == item["title"] and row["original"]["description"] == item["description"]
        assert item["critic"]["llm_decision"] == "needs_human" and item["critic"]["source_dependency"] == "needs_more_context"


def test_page_mismatch_proposes_a_revision_beside_the_untouched_original():
    items, sources, pages = mixed_record()
    run(items, sources, pages)
    item = items[3]
    row, critic = item["correction"], item["critic"]
    assert critic["llm_decision"] == "rewrite" and critic["needs_correction"] is True and critic["suggested_fix"]
    assert row["action"] == "propose_revision" and row["candidate"]["status"] == "proposed_requires_expert_review"
    assert item["description"] == "Описание без ссылок"  # the original is not edited
    assert row["candidate"]["description"].startswith("Описание без ссылок") and "стр. 4" in row["candidate"]["description"]
    assert row["candidate"]["source_ids"] == ["text:0"] and row["candidate"]["source_evidence"] == [{"source_id": "text:0", "quote": QUOTE}]
    assert row["original"]["description"] == "Описание без ссылок"


def test_a_description_that_cannot_hold_the_page_note_becomes_a_request_for_context():
    pages = {**PAGES, 4: QUOTE + "."}
    items = [observation(1, ["text:0"], description="x" * od.MAX_DESCRIPTION)]
    run(items, [text_source("text:0", 14, QUOTE)], pages)
    row = items[0]["correction"]
    assert row["action"] == "needs_context" and row["candidate"] is None
    assert row["required_context"] == ["Физическая страница цитаты: 4"]
    assert items[0]["description"] == "x" * od.MAX_DESCRIPTION


def test_the_pass_is_repeatable_and_summarised():
    first, sources, pages = mixed_record()
    second = deepcopy(first)
    done_a, corrections_a = run(first, sources, pages)
    done_b, corrections_b = run(second, sources, pages)
    assert first == second
    assert od.summary(done_a, corrections_a) == {"reviewed": 4, "verdicts": {"pass": 1, "no_evidence": 1, "phantom_block": 1, "page_mismatch": 1},
        "proposals": {"needs_context": 2, "propose_revision": 1}}


def test_an_empty_record_is_reviewed_without_a_row():
    assert od.review([], [], {}) == [] and od.correct([]) == []
    assert od.summary([], []) == {"reviewed": 0, "verdicts": {}, "proposals": {}}


# --- no model, the plan, the provenance ----------------------------------------------------------------------------------------------------

def test_no_model_pass_exists():
    tree = ast.parse(Path(od.__file__).read_text(encoding="utf-8"))
    imported = {node.module if isinstance(node, ast.ImportFrom) else alias.name for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in getattr(node, "names", [])}
    assert imported == {"__future__", "copy", "re", "core"}  # no adapter, no provider, no request builder
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "complete"]
    assert od.plan()["checks_not_built"] == ["evidence_relevance", "text_consistency"]
    assert od.plan()["model_called"] is False and od.plan()["proposals_only"] is True and od.plan()["expert_decisions_written"] is False
    assert [p["id"] for p in od.procedures()] == ["finding_review", "finding_correction"]
    assert all(p["status"] == "queued" and p["model_called"] is False for p in od.procedures())


def test_provenance_matches_the_pinned_source():
    pinned = json.loads((EXTENDED / "original_review" / "SOURCE.json").read_text(encoding="utf-8"))
    assert od.SOURCE["commit"] == pinned["commit"]
    assert od.SOURCE["critic"]["sha256"] == pinned["files"]["deterministic_critic.source.txt"]["sha256"]
    assert od.SOURCE["corrector"]["sha256"] == pinned["files"]["deterministic_corrector.source.txt"]["sha256"]
    assert od.SOURCE["critic"]["path"] == pinned["files"]["deterministic_critic.source.txt"]["source"]
    assert od.SOURCE["corrector"]["path"] == pinned["files"]["deterministic_corrector.source.txt"]["source"]
    assert "llm_call=None" in od.SOURCE["production_call"]


def test_the_facade_is_the_module():
    items = [observation(1, [])]
    done = public.original_review_critic(items, [], PAGES)
    assert public.original_review_corrector(done) and public.ORIGINAL_REVIEW_V2 == od.ORIGINAL_REVIEW_V2 == "deterministic-v1"
    assert public.original_review_summary(done, [items[0]["correction"]])["reviewed"] == 1
    assert public.original_review_plan() == od.plan() and public.original_review_procedures() == od.procedures()


# --- v3's bundle identity is untouched -----------------------------------------------------------------------------------------------------

def test_v3_bundle_digest_is_what_it_was_before_the_original_review_was_added():
    assert {section: review_bundle_digest(section) for section in V3_BUNDLE_DIGEST_AT_BASE} == V3_BUNDLE_DIGEST_AT_BASE


def test_the_new_module_is_outside_the_files_the_bundle_digest_hashes():
    """Moving it under ``original_review/`` or into the listed files would change v3's frozen ``rules_sha256``."""
    hashed = {path.name for path in (EXTENDED / "original_review").rglob("*") if path.is_file()}
    listed = {"core.py", "workflow.py", "review.py", "native_pages.py", "coverage.py", "cross_window.py", "cross_window_review.py", "block_ensemble.py"}
    assert Path(od.__file__).name not in hashed | listed and Path(od.__file__).parent == EXTENDED
