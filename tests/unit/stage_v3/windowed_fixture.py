"""Builders and a driver for the windowed-v1 / windowed-global-v1 tests; synthetic, no provider, no I/O.

The driver walks a plan implementation (`windowed` or `consolidation`) phase by phase exactly as the
runtime does: ask for the plans of a phase, answer the first one that has no saved result, parse the
answer with the implementation's own `parse`, save it under its group id. Every answer is the
source-bound synthetic reply of `recorded_fixture` unless the caller edits it first.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

from auditmanager.comparison.stage_ai.runtime import request_for_plan
from tests.unit.stage_v3.recorded_fixture import synthetic_response

MODEL = "recorded-v3-fixture"
PHASES = ("review", "classify", "synthesize")


def snapshot_of(old, new, *, pair="pair-test"):
    """A saved-revision snapshot. `old`/`new` are lists of pages; a page is a list of block texts.

    Block ids are `stf_<n>` in creation order (OLD first), so a test can name any block it built.
    """
    profiles, fragments, number = [], [], 0
    for side, pages in (("left", old), ("right", new)):
        for page_number, texts in enumerate(pages, 1):
            profile = f"cpr_{side}_{page_number}"
            profiles.append({"profile_id": profile, "version_uid": f"ver_{side}", "page_number": page_number,
                             "side": side, "content_key": f"page-key-{profile}"})
            for position, text in enumerate(texts):
                number += 1
                fragments.append({"stage_text_fragment_id": f"stf_{number}", "page_profile_id": profile,
                    "normalised_text": text, "content_key": f"fragment-key-{number}",
                    "box_anchor": {"x0": 10, "top": 20 + position, "x1": 180, "bottom": 30 + position}})
    return {"stage_pair_id": pair, "stage_link_revision_id": "revision-test", "all_profiles": profiles,
            "fragments": fragments, "links": [], "differences": []}


def numbered(count, template="узел {n} параметр {n} мм"):
    return [template.format(n=index) for index in range(1, count + 1)]


def region(region_id, old, new):
    return {"region_id": region_id, "old_pages": list(old), "new_pages": list(new),
            "engineering_domain": "Тест", "scope": "Тестовая область", "locations": [],
            "reason_for_correspondence": "Тестовое соответствие.", "important_text_blocks": [],
            "important_table_blocks": [], "important_graphic_blocks": [], "confidence": 0.5}


def mapping_edit(regions, unmatched_old=(), unmatched_new=()):
    """An `edit` for `drive` that replaces the synthetic Mapper's single region by the given mapping."""
    def edit(procedure, _plan, answer):
        if procedure == "mapper":
            answer.update(regions=list(regions), unmatched_old=list(unmatched_old), unmatched_new=list(unmatched_new))
    return edit


def answer_of(plan, edit=None):
    """The synthetic reply to one plan, as a dict, after the optional caller edit."""
    reply, payload = synthetic_response(request_for_plan(plan))
    answer = json.loads(reply.output_text)
    if edit is not None:
        edit(payload["_experimental_procedure"], plan, answer)
    return answer


def row_of(answer, stop_reason="end_turn"):
    return {"output_text": json.dumps(answer, ensure_ascii=False), "stop_reason": stop_reason}


def drive(impl, source, *, edit=None, results=None, phases=PHASES, limit=600):
    """Run the phases to the end. Returns `SimpleNamespace(results, calls, plans)`; `calls` are
    `(procedure, group_id)` in call order, `plans` maps group id to the plan that was answered."""
    results = {} if results is None else results
    calls, plans = [], {}
    for phase in phases:
        for _ in range(limit):
            pending = [plan for plan in impl.plans_for(phase, source, results, MODEL) if plan.group_id not in results]
            if not pending:
                break
            plan = pending[0]
            answer = answer_of(plan, edit)
            results[plan.group_id] = impl.parse(plan, row_of(answer), source)
            calls.append((plan.payload["_experimental_procedure"], plan.group_id))
            plans[plan.group_id] = plan
        else:
            raise AssertionError((phase, "did not terminate"))
    return SimpleNamespace(results=results, calls=calls, plans=plans)


def procedures(run):
    return [procedure for procedure, _group in run.calls]


def count(run, procedure):
    return procedures(run).count(procedure)


def evidence_for(source, block_id, side, page):
    """A Miner/Consolidator evidence item that cites a real saved block exactly."""
    fragment = next(row for row in source["fragments"] if row["stage_text_fragment_id"] == block_id)
    anchor = fragment["box_anchor"]
    return {"side": side, "source_pdf": "ver_left" if side == "OLD" else "ver_right", "physical_page": page,
            "block_id": block_id, "block_type": "TEXT", "bbox": [anchor[key] for key in ("x0", "top", "x1", "bottom")],
            "crop_ref": "", "relevant_fragment": fragment["normalised_text"], "evidence_role": "тест"}


def hint_for(source, block_id, side, page, *, old_pages, new_pages, identity="H1"):
    return {"hint_id": identity, "kind": "UNRESOLVED_HINT", "engineering_subject": "Тест", "suspected_change": "Тест",
            "old_pages": old_pages, "new_pages": new_pages, "evidence_items": [evidence_for(source, block_id, side, page)],
            "missing_proof_or_conflict": "Нет доказательства."}


# Four OLD pages (the first has four blocks) against four NEW pages: room for the Mapper's rules.
MAPPER_SOURCE = snapshot_of([numbered(4), numbered(2)], [numbered(2), numbered(2)])
