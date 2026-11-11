"""The original's deterministic critic and corrector for plan v2, as advice only (`V2-ORIGINAL-REVIEW-01`, R-154e..g).

Plan v2 is the original application's legacy flow. The original's production runs two procedures after its findings are merged: the
deterministic critic (checks 1, 2 and 4, no model) and the deterministic corrector (``findings_verify/runner.py`` calls
``run_deterministic_critic(llm_call=None)``). This module ports both over the observations and sources of a v2 record.

Both are advice. The critic writes the row v3's critic writes (``critic`` and ``review_status`` of an observation) and the corrector the row
v3's correction writes (``correction``). Neither edits an observation, a source or a verdict of the expert (ADR-0027, AGENTS section 4):
where the original's corrector edits the finding, the row here is a proposal beside the untouched original. No model is called and no executor
is needed. The best-effort model pass of the original (checks 3 and 5, ``evidence_relevance`` and ``text_consistency``) is not built.

Source: ``original_review/deterministic_{critic,corrector}.source.txt`` (PDF-proverka 3c994817, see ``original_review/SOURCE.json``). This file
stays outside ``workflow.review_bundle_digest``'s set on purpose: adding it must not change v3's ``rules_sha256``.
"""
from __future__ import annotations

from copy import deepcopy
import re

from .core import digest

#: The marker a fresh plan-v2 estimate freezes into the consent. A v2 consent without it runs exactly as it ran before.
ORIGINAL_REVIEW_V2 = "deterministic-v1"
SOURCE = {
    "repository": "https://github.com/SU10KAZ/PDF-proverka",
    "commit": "3c99481719218b9cfa7560886529916646c61939",
    "critic": {"path": "backend/app/pipeline/stages/findings_review/deterministic_critic.py",
        "sha256": "b34ca5a2af88f7edf47381b5d1e3f87d99762e8741502a4a410b21d8e12e0e6a"},
    "corrector": {"path": "backend/app/pipeline/stages/findings_review/deterministic_corrector.py",
        "sha256": "2191ceb8df8553b351d9d97fc9a0d8e6357de1c116cc89d46a729e5dad3e0e5e"},
    "production_call": "backend/app/pipeline/stages/findings_verify/runner.py: run_deterministic_critic(llm_call=None)",
}
#: ``block_NNN``, ``page_N_text`` and the portal's ``XXXX-XXXX-XXX`` identifiers an original finding may name in its text.
_BLOCK_REFERENCE = re.compile(r"\b(?:block_[0-9a-zA-Z_]+|page_\d+_[a-z]+|[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{3,})\b")
#: A quotation shorter than this says too little about the page it stands on to call its page wrong.
MIN_QUOTE_CHARACTERS = 12
MAX_DESCRIPTION = 3000

#: The original's verdict -> v3's advice vocabulary: (``llm_decision``, ``human_taxonomy_reason``, ``source_dependency``, ``needs_correction``).
#: Never ``reject``: nothing is cancelled by a rule (ADR-0027). ``weak_evidence`` and ``contradicts_text`` are the model pass's verdicts; they stand
#: in the table so that the vocabulary is the original's whole, and nothing here produces them. The reasons are in the lane's record.
VERDICT_ADVICE = {
    "pass": ("accept", None, "enough_source", False),
    "no_evidence": ("needs_human", "insufficient_source_context", "needs_more_context", False),
    "phantom_block": ("needs_human", "insufficient_source_context", "needs_more_context", False),
    "page_mismatch": ("rewrite", None, "enough_source", True),
    "weak_evidence": ("needs_human", "insufficient_source_context", "needs_more_context", False),
    "contradicts_text": ("needs_human", None, "enough_source", False),
}


def procedures() -> list[dict]:
    """The two procedures a v2 result with the marker plans after the norm verification."""
    return [{"id": "finding_review", "title": "Критик наблюдений · правила оригинала, без модели", "status": "queued", "model_called": False},
        {"id": "finding_correction", "title": "Предложения по уточнению · правила оригинала, без модели", "status": "queued", "model_called": False}]


def plan() -> dict:
    return {"version": ORIGINAL_REVIEW_V2, "mode": "deterministic", "model_called": False, "proposals_only": True,
        "expert_decisions_written": False, "checks": ["evidence_presence", "block_exists", "page_sheet_correct"],
        "checks_not_built": ["evidence_relevance", "text_consistency"], "source": deepcopy(SOURCE)}


def _listed(value) -> list:
    """A copy of ``value`` when it is a list, else nothing: a record whose ``source_ids`` is not a list is read, not trusted."""
    return list(value) if isinstance(value, list) else []


def _folded(value) -> str:
    return " ".join(value.split()).casefold() if isinstance(value, str) else ""


def _short_list(values, limit=5) -> str:
    shown = ", ".join(str(value) for value in values[:limit])
    return shown + (f" и ещё {len(values) - limit}" if len(values) > limit else "")


def verdict(item: dict, registry: dict, pages: dict) -> tuple[str, dict, dict]:
    """Checks 1, 2 and 4 of ``deterministic_critic.deterministic_verdict`` over one observation: ``(verdict, checks, detail)``.

    1 ``evidence_presence``: the observation names a source (``source_ids``, or an identifier its text mentions).
    2 ``block_exists``: at least one named source is in the record (the original: ``phantom_block`` when none is).
    4 ``page_sheet_correct``: the original compares the page a finding states with the pages of its evidence. An observation here has no page of
    its own; the page a text source states is the one claim in the record, so the check asks whether that source's quotation is on that page of
    the text layer (``pages`` holds the folded text of each page). Like the original it flags only a tight case: the quotation is on one or two
    other pages and not on the stated one. A paraphrase found nowhere says nothing about the page, and no sheet stamp exists in a v2 record, so
    neither is judged.
    """
    ids = item.get("source_ids")
    declared = [value for value in ids if isinstance(value, str) and value] if isinstance(ids, list) else []
    mentioned = _BLOCK_REFERENCE.findall(" ".join(str(item.get(key) or "") for key in ("description", "title")))
    references = list(dict.fromkeys([*declared, *mentioned]))
    checks = {"evidence_presence": "pass", "block_exists": "pass", "page_sheet_correct": "not_applicable"}
    if not references:
        return "no_evidence", {**checks, "evidence_presence": "fail", "block_exists": "not_applicable"}, {}

    def is_text(reference):
        return registry.get(reference, {}).get("kind") == "text" or (
            reference not in registry and re.fullmatch(r"page_\d+_text", reference) is not None)
    text_references = [reference for reference in references if is_text(reference)]
    image_references = [reference for reference in references if reference not in text_references]
    existing_image = [reference for reference in image_references if reference in registry]
    existing_text = [reference for reference in text_references if reference in registry or reference.endswith("_text")]
    if image_references and not existing_image and not existing_text:
        return "phantom_block", {**checks, "block_exists": "fail"}, {"missing": image_references}

    claims = []
    for reference in declared:
        source = registry.get(reference)
        if source is None or source.get("kind") != "text":
            continue
        stated, quote = source.get("page_number"), _folded(source.get("quote"))
        if type(stated) is int and stated in pages and len(quote) >= MIN_QUOTE_CHARACTERS:
            claims.append((reference, stated, quote, source["quote"]))
    if claims:
        checks["page_sheet_correct"] = "pass"
    for reference, stated, quote, raw in claims:
        if quote in pages[stated]:
            continue
        elsewhere = sorted(number for number, text in pages.items() if number != stated and quote in text)
        if 1 <= len(elsewhere) <= 2:
            return "page_mismatch", {**checks, "page_sheet_correct": "fail"}, {
                "source_id": reference, "stated_page": stated, "found_on_pages": elsewhere, "quote": raw[:2000]}
    return "pass", checks, {}


def _explanation(kind: str, detail: dict) -> str:
    if kind == "pass":
        return ("Структурные проверки оригинала пройдены: у наблюдения есть источник, источник есть в записи, страница цитаты не опровергнута. "
            "Смысловая проверка не выполнялась: модель не вызывалась.")
    if kind == "no_evidence":
        return ("Проверка 1 оригинала «наличие доказательства»: у наблюдения нет ни одного источника и нет ссылки на блок в тексте. "
            "Наблюдение сохранено; решение за экспертом.")
    if kind == "phantom_block":
        return ("Проверка 2 оригинала «блок существует»: источники наблюдения отсутствуют в записи: "
            + _short_list(detail["missing"]) + ". Наблюдение сохранено; решение за экспертом.")
    if kind == "page_mismatch":
        return (f"Проверка 4 оригинала «страница указана верно»: источник {detail['source_id']} указывает стр. {detail['stated_page']}, "
            f"а его цитата найдена в тексте документа на стр. {_short_list(detail['found_on_pages'])}. Наблюдение сохранено; решение за экспертом.")
    return "Вердикт оригинала, который даёт только смысловая проверка моделью; здесь она не выполняется."


def critic_row(key: str, item: dict, kind: str, checks: dict, detail: dict) -> dict:
    """The critic's row, in v3's shape, marked as the original's rule and not a model's word (``mode``, ``model_called``)."""
    decision, reason, dependency, needs_correction = VERDICT_ADVICE[kind]
    fix = (f"Проверить страницу: цитата источника найдена на стр. {_short_list(detail['found_on_pages'])}, указана стр. {detail['stated_page']}."
        if kind == "page_mismatch" else "")
    return {"input_id": key, "observation_id": item.get("observation_id", key), "source_ids": _listed(item.get("source_ids")),
        "llm_decision": decision, "human_taxonomy_reason": reason, "confidence": None,
        "explanation": _explanation(kind, detail), "evidence_checked": False, "source_dependency": dependency,
        "needs_correction": needs_correction, "suggested_fix": fix, "source_evidence": [],
        "status": "requires_expert_review", "expert_decision": False,
        "mode": "deterministic", "model_called": False, "policy": ORIGINAL_REVIEW_V2, "original_verdict": kind,
        "failed_checks": [name for name, result in checks.items() if result == "fail"], "checks": dict(checks)}


def correction_row(item: dict, critic: dict, detail: dict) -> dict | None:
    """The corrector's row for a verdict that is not ``pass``: a proposal beside the original, never an edit of it.

    What the original's corrector does to the finding, and what it becomes here. ``phantom_block`` and ``no_evidence`` (drop the missing ids;
    downgrade or flag the finding): nothing is left to keep or to propose, so the row asks for a source (``needs_context``); the flag is the
    critic's ``needs_human``. ``page_mismatch`` (set the page from the evidence): a proposed revision that states the page the quotation was found
    on, with that quotation, beside the original, which is not changed.
    """
    kind = critic["original_verdict"]
    if kind == "pass":
        return None
    original = {"title": item.get("title"), "description": item.get("description"), "source_ids": _listed(item.get("source_ids"))}
    row = {"input_id": critic["input_id"], "observation_id": critic["observation_id"], "original": original, "candidate": None,
        "action": "needs_context", "source_ids": list(original["source_ids"]),
        "reason": "Исправить нечем: указать источник должен эксперт. Наблюдение сохранено без изменений.",
        "required_context": ["Блок или страница документа, подтверждающие наблюдение"],
        "status": "requires_expert_review", "expert_decision": False,
        "mode": "deterministic", "model_called": False, "policy": ORIGINAL_REVIEW_V2, "original_verdict": kind}
    if kind == "page_mismatch":
        note = (f"\n\nУточнение страницы: цитата источника найдена на стр. {_short_list(detail['found_on_pages'])}; "
            f"в записи указана стр. {detail['stated_page']}.")
        if isinstance(item.get("description"), str) and len(item["description"]) + len(note) <= MAX_DESCRIPTION:
            row.update(action="propose_revision", required_context=[],
                reason="Предложена редакция с уточнённой страницей; исходная запись сохранена.",
                candidate={"title": item["title"], "description": item["description"] + note, "source_ids": list(original["source_ids"]),
                    "source_evidence": [{"source_id": detail["source_id"], "quote": detail["quote"]}], "norm_evidence": [],
                    "status": "proposed_requires_expert_review"})
        else:
            row.update(reason="Предложить редакцию нельзя: описание не вместит уточнение. Проверьте страницу вручную.",
                required_context=[f"Физическая страница цитаты: {_short_list(detail['found_on_pages'])}"])
    return row


def review(observations: list, sources: list, pages: dict) -> list[tuple[dict, dict, dict]]:
    """The critic over every observation: each gets ``critic`` and ``review_status``; its own fields are not changed.

    ``pages`` maps a physical page number to its text-layer text. Returns ``(observation, critic row, detail)`` for the corrector.
    """
    registry = {source["source_id"]: source for source in sources if isinstance(source, dict) and isinstance(source.get("source_id"), str)}
    folded = {number: _folded(text) for number, text in pages.items()}
    done = []
    for item in observations:
        key = "xrd_" + digest({"observation_id": item.get("observation_id")})[:24]
        kind, checks, detail = verdict(item, registry, folded)
        critic = critic_row(key, item, kind, checks, detail)
        item.update(critic=critic, review_status="reviewed")
        done.append((item, critic, detail))
    return done


def correct(done: list[tuple[dict, dict, dict]]) -> list[dict]:
    """The corrector over the critic's rows: a ``correction`` beside each observation whose verdict is not ``pass``."""
    corrections = []
    for item, critic, detail in done:
        row = correction_row(item, critic, detail)
        if row is not None:
            item["correction"] = row
            corrections.append(row)
    return corrections


def summary(done: list[tuple[dict, dict, dict]], corrections: list[dict]) -> dict:
    """What the result records of the run, beside the plan: the verdicts and the proposals, counted."""
    verdicts: dict[str, int] = {}
    for _, critic, _ in done:
        verdicts[critic["original_verdict"]] = verdicts.get(critic["original_verdict"], 0) + 1
    actions: dict[str, int] = {}
    for row in corrections:
        actions[row["action"]] = actions.get(row["action"], 0) + 1
    return {"reviewed": len(done), "verdicts": verdicts, "proposals": actions}
