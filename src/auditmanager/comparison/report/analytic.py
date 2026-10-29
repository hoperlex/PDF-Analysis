"""The analytic report: an analyst, a verifier and a composer, every answer checked by the program (`CMP-VC-REPORT-01`, plan 1.1).

A port of the original's ``md_report/stages.py`` (870 lines), ``md_report/schemas.py`` (241 lines), ``md_report/plan.py`` (as far as the
unit of work goes) and the prompts ``prompts/md_report_{rules,common,analyst,verifier,composer}.md`` (copied unchanged to ``prompts/``) at
commit ``23f379fd`` of ``SU10KAZ/PDF-proverka``. The model is not the only controller: identifiers, the coverage of the blocks, the ranges of
lines, a verdict for every claim and the order of the transitions are checked by the program (``stages.py:1-7``), and the labels A/B, the
dates, the completeness (by the coverage registry) and the sources (the passports of the facts: sheet, pages, line of the MD) are filled in
by the program. From the composer only fact IDs are taken.

The unit of work is **one transition** (the original splits a large transition into blocks for parallelism, ``plan.py:32-157``; here a
transition is one block ``B01``…, one group ``G01``… and one unit of verification ``U01``…, as with ``verify_unit=transition`` -- the default,
``settings.py:83-86``). A summary section that is not a transition is not sent to a model; it stays in the ``issues`` of the manifest.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Final

from auditmanager.comparison.report import client as client_module
from auditmanager.comparison.report import facts as facts_mod
from auditmanager.comparison.report import parse

__all__ = [
    "ANALYST_SCHEMA",
    "COMPOSER_SCHEMA",
    "EXCERPT_PAD",
    "MAX_SERIOUS",
    "PROMPT_NAMES",
    "PROMPT_VERSION",
    "VERDICTS",
    "VERIFIER_SCHEMA",
    "VERIFY_FULL_CHARS",
    "analyst_prompt",
    "assemble",
    "check_analyst",
    "check_composer",
    "check_verifier",
    "claims_for_unit",
    "clean_verifier",
    "completeness",
    "composer_prompt",
    "consistency",
    "distribution",
    "final_assessment",
    "make_plan",
    "normalize_scope",
    "normalize_significance",
    "numbers",
    "validate_report",
    "verifier_prompt",
    "verified_parts",
]

#: `[own design]` the prompt version of this port; the original's is ``mdr-p1`` (``settings.py:19``).
PROMPT_VERSION: Final[str] = "cmp-analytic/1"
PROMPTS_DIR: Final[Path] = Path(__file__).resolve().parent / "prompts"
PROMPT_NAMES: Final[tuple[str, ...]] = ("rules", "common", "analyst", "verifier", "composer")  # stages.py:21
RELATED_PER_TOKEN: Final[int] = 5  # stages.py:23
RELATED_MAX_TOKENS: Final[int] = 40
RELATED_MAX_CHARS: Final[int] = 40_000
EXCERPT_PAD: Final[int] = 2
WORD_LIMIT: Final[int] = 1000
MAX_SERIOUS: Final[int] = 5  # stages.py:597-598 -- more than five serious changes is a hard error
#: Full text of a unit goes to the verifier up to this many characters; above it only excerpts around the claims (settings.py:78-80).
VERIFY_FULL_CHARS: Final[int] = 150_000

# ------------------------------------------------------------------ the vocabularies (schemas.py:14-49)
SCOPES = (
    "Нет изменений содержания", "Только оформление", "Локальные изменения", "Существенные изменения", "Широкая переработка",
    "Не установлено",
)
SIGNIFICANCE = ("Нет новых технических изменений", "Низкая", "Средняя", "Высокая", "Не установлена")
CONTENT = ("technical", "formatting_only", "no_content_changes", "unknown")
VERDICTS: Final[tuple[str, ...]] = ("supported", "qualified", "contradictory", "insufficient", "rejected")
PRIORITIES = ("P1", "P2", "P3")
TECHNICAL_SCOPES = ("Локальные изменения", "Существенные изменения", "Широкая переработка")
#: The scale of a transition combined from parts cannot be lower than any verified part (schemas.py:22-26).
SCOPE_RANK = {
    "Не установлено": -1, "Нет изменений содержания": 0, "Только оформление": 1, "Локальные изменения": 2,
    "Существенные изменения": 3, "Широкая переработка": 4,
}
SIGNIFICANCE_RANK = {"Не установлена": -1, "Нет новых технических изменений": 0, "Низкая": 1, "Средняя": 2, "Высокая": 3}
SCOPE_SYNONYMS = {
    "без изменений": "Нет изменений содержания", "нет изменений": "Нет изменений содержания",
    "нет изменений содержания": "Нет изменений содержания", "только оформление": "Только оформление",
    "оформление": "Только оформление", "локальный": "Локальные изменения", "локальные изменения": "Локальные изменения",
    "существенный": "Существенные изменения", "существенные изменения": "Существенные изменения",
    "большой": "Широкая переработка", "очень большой": "Широкая переработка",
    "широкая переработка": "Широкая переработка", "не установлено": "Не установлено",
}
SIGNIFICANCE_SYNONYMS = {
    "нет новых технических изменений": "Нет новых технических изменений", "низкая": "Низкая", "средняя": "Средняя",
    "высокая": "Высокая", "не установлена": "Не установлена", "неопределённая": "Не установлена",
    "неопределенная": "Не установлена", "неизвестно": "Не установлена",
}


def normalize_scope(value: str | None) -> str | None:
    return SCOPE_SYNONYMS.get((value or "").strip().lower().rstrip("."))


def normalize_significance(value: str | None) -> str | None:
    return SIGNIFICANCE_SYNONYMS.get((value or "").strip().lower().rstrip("."))


# ------------------------------------------------------------------ the schemas of the answers (schemas.py:52-134)

def _s(desc: str = "") -> dict[str, Any]:
    return {"type": "string", "description": desc} if desc else {"type": "string"}


def _list(item: dict[str, Any], desc: str = "") -> dict[str, Any]:
    return {"type": "array", "items": item, "description": desc} if desc else {"type": "array", "items": item}


def _obj(props: dict[str, Any], desc: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {"type": "object", "additionalProperties": False, "required": list(props), "properties": props}
    if desc:
        out["description"] = desc
    return out


REF = _obj({"md_from": {"type": "integer"}, "md_to": {"type": "integer"}}, "включительный диапазон строк MD")
NOTE = _obj({"text": _s(), "evidence": _list(REF)})

ANALYST_SCHEMA: Final[dict[str, Any]] = _obj({
    "run_id": _s(), "group_id": _s(), "processed_block_ids": _list(_s()), "unprocessed_block_ids": _list(_s()),
    "partial": {"type": "boolean"}, "input_problems": _list(_s()),
    "transitions": _list(_obj({
        "transition_id": _s(), "analysis_complete": {"type": "boolean"},
        "content_status": {"type": "string", "enum": list(CONTENT)},
        "change_scope": {"type": "string", "enum": list(SCOPES)},
        "significance": {"type": "string", "enum": list(SIGNIFICANCE)},
        "assessment_basis": _s("короткое предметное основание оценок"), "systems": _list(_s()),
        "facts": _list(_obj({
            "fact_id": _s(), "object": _s(), "system": _s(), "before": _s(), "after": _s(), "possible_consequence": _s(),
            "evidence": _list(REF), "uncertainty": _s(), "related_objects": _list(_s("точное обозначение")),
            "serious_candidate": {"type": "boolean"},
        })),
        "construction_impact": _s(), "explicit_conditions": _list(NOTE), "contradictions": _list(NOTE),
        "missing_information": _list(_s()),
    })),
})

VERIFIER_SCHEMA: Final[dict[str, Any]] = _obj({
    "run_id": _s(), "unit_id": _s(),
    "claims": _list(_obj({
        "claim_id": _s(), "verdict": {"type": "string", "enum": list(VERDICTS)}, "verified_wording": _s(),
        "evidence": _list(REF), "brief_reason": _s(), "missing_information": _list(_s()), "linked_claim_ids": _list(_s()),
    })),
    "transitions": _list(_obj({
        "transition_id": _s(), "content_status": {"type": "string", "enum": list(CONTENT)},
        "change_scope": {"type": "string", "enum": list(SCOPES)},
        "significance": {"type": "string", "enum": list(SIGNIFICANCE)}, "assessment_basis": _s(), "main_changes": _s(),
        "construction_impact": _s(), "key_claim_ids": _list(_s()), "evidence": _list(REF),
    })),
    "significant_candidates": _list(_obj({
        "title": _s(), "claim_ids": _list(_s()), "version_range": _s(), "before_after": _s(), "consequence": _s(),
        "evidence": _list(REF),
    })),
    "unresolved_questions": _list(_s()), "missing_transitions_or_blocks": _list(_s()),
})

_FACT_IDS = _list(_s("ID факта из реестра, например «Ф0123»"))
COMPOSER_SCHEMA: Final[dict[str, Any]] = _obj({
    "run_id": _s(), "summary": _list(_s()), "summary_fact_ids": _FACT_IDS,
    "transitions": _list(_obj({
        "transition_id": _s(), "change_scope": {"type": "string", "enum": list(SCOPES)},
        "significance": {"type": "string", "enum": list(SIGNIFICANCE)},
        "main_changes": _s("1 предложение: характер изменений перехода"),
        "changes": _list(_obj({
            "object": _s("линия, аппарат, материал или узел с точным обозначением"), "before": _s("было"),
            "after": _s("стало"), "fact_ids": _FACT_IDS,
        }), "до 6 главных изменений «объект — было → стало»"),
        "construction_impact": _s("условное последствие для работ по предыдущей выдаче"), "impact_fact_ids": _FACT_IDS,
    })),
    "significant_changes": _list(_obj({
        "priority": {"type": "string", "enum": list(PRIORITIES)}, "title": _s(), "version_range": _s(), "before_after": _s(),
        "consequence": _s(), "claim_ids": _list(_s()), "fact_ids": _FACT_IDS,
    })),
    "limitations": _list(_s()),
})


# ------------------------------------------------------------------ prompts (stages.py:30-66)
_PLACEHOLDER = re.compile(r"\{\{([A-Z_]+)\}\}")


def prompt_text(name: str) -> str:
    return (PROMPTS_DIR / f"md_report_{name}.md").read_text(encoding="utf-8")


def _fill(template: str, values: dict[str, str]) -> str:
    missing = [m for m in _PLACEHOLDER.findall(template) if m not in values]
    if missing:
        raise ValueError(f"no value for {', '.join(sorted(set(missing)))}")
    return _PLACEHOLDER.sub(lambda m: values[m.group(1)], template)


def render(stage: str, values: dict[str, str], seed: str) -> str:
    """The common instruction plus the task of a stage; the labels of the block of data are chosen so that they are not in the data."""
    body = "\n".join(values.values())
    begin, end = client_module.boundary(seed, body)
    common = _fill(prompt_text("common"), {"BEGIN": begin, "END": end, "TRUSTED_ANALYSIS_RULES": prompt_text("rules").strip()})
    return common.rstrip() + "\n\n" + _fill(prompt_text(stage), values | {"BEGIN": begin, "END": end})


def _clean(text: str | None, limit: int = 160) -> str:
    return re.sub(r"[\x00-\x1f\x7f]+", " ", str(text or "")).strip()[:limit]


def source_metadata(source: dict[str, Any], manifest: dict[str, Any]) -> str:
    return json.dumps({
        "file": _clean(source.get("filename")), "sha256": source.get("sha256"), "bytes": source.get("bytes"),
        "lines": manifest["lines_total"], "project_code": _clean(manifest.get("project_code"), 80),
        "transitions": len(manifest["transitions"]), "basis": "только MD-сводка; исходные PDF не предоставлены",
    }, ensure_ascii=False)


def numbered(lines: list[str], ranges: list[list[int]], context: list[list[int]] | None = None) -> str:
    out = []
    for start, end in sorted(context or []):
        out += [f"[{i}] (контекст) {lines[i - 1]}" for i in range(start, end + 1)]
    for start, end in ranges:
        out += [f"[{i}] {lines[i - 1]}" for i in range(start, end + 1)]
    return "\n".join(out)


def _by_id(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {t["transition_id"]: t for t in manifest["transitions"]}


def _transition_line(transition: dict[str, Any], extra: str = "") -> str:
    notes = []
    if transition.get("explicit_no_content_changes"):
        notes.append("в сводке явная отметка «изменений содержания нет»")
    if transition.get("source_incomplete"):
        notes.append(f"в сводке есть неописанные места: {len(transition['source_incomplete'])}")
    return (
        f"- {transition['transition_id']}: {transition['label']} (A: {_clean(transition['a_label'])}; B: {_clean(transition['b_label'])}), "
        f"строки {transition['line_start']}–{transition['line_end']}, листов в сводке {len(transition['sheets'])}"
        + (f"; {extra}" if extra else "") + (f"; {'; '.join(notes)}" if notes else "")
    )


def make_plan(manifest: dict[str, Any]) -> dict[str, Any]:
    """The plan of the work: a transition is one block, one group and one unit of verification (see the module docstring)."""
    blocks, groups, units = [], [], []
    for position, transition in enumerate(manifest["transitions"], 1):
        block_id, group_id, unit_id = f"B{position:02d}", f"G{position:02d}", f"U{position:02d}"
        blocks.append({
            "block_id": block_id, "transition_id": transition["transition_id"], "kind": "transition",
            "ranges": [[transition["line_start"], transition["line_end"]]], "context": [], "chars": transition["chars"],
        })
        groups.append({"group_id": group_id, "transition_ids": [transition["transition_id"]], "block_ids": [block_id]})
        units.append({"unit_id": unit_id, "transition_ids": [transition["transition_id"]], "group_ids": [group_id]})
    return {"blocks": blocks, "groups": groups, "units": units}


# ------------------------------------------------------------------ the analyst (stages.py:100-169)

def analyst_prompt(
    run_id: str, source: dict[str, Any], manifest: dict[str, Any], plan: dict[str, Any], group: dict[str, Any], lines: list[str],
) -> str:
    by_block = {b["block_id"]: b for b in plan["blocks"]}
    transitions = _by_id(manifest)
    assigned = [_transition_line(transitions[tid]) for tid in group["transition_ids"]]
    manifest_lines, text_parts = [], []
    for block_id in group["block_ids"]:
        block = by_block[block_id]
        ranges = ", ".join(f"{s}–{e}" for s, e in block["ranges"])
        manifest_lines.append(f"- {block_id}: {block['transition_id']}, переход целиком, строки {ranges}, {block['chars']} символов")
        text_parts.append(f"=== Блок {block_id} ===\n" + numbered(lines, block["ranges"], block.get("context")))
    header_end = manifest["header"]["line_end"]
    return render("analyst", {
        "RUN_ID": run_id, "GROUP_ID": group["group_id"], "SOURCE_METADATA": source_metadata(source, manifest),
        "ASSIGNED_TRANSITIONS": "\n".join(assigned) or "- нет", "ASSIGNED_BLOCK_MANIFEST": "\n".join(manifest_lines),
        "SOURCE_LIMITATIONS": numbered(lines, [[1, header_end]]) if header_end else "—",
        "ASSIGNED_SOURCE_TEXT": "\n\n".join(text_parts),
    }, f"{run_id}:A:{group['group_id']}")


def _within(ranges: list[list[int]], start: int, end: int) -> bool:
    return any(s <= start and end <= e for s, e in ranges)


def check_analyst(answer: dict[str, Any], run_id: str, group: dict[str, Any], plan: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    """The program's check of the analyst's answer (stages.py:130-169): ``hard`` rejects (a retry), ``soft`` warns."""
    hard: list[str] = []
    soft: list[str] = []
    if answer.get("run_id") != run_id or answer.get("group_id") != group["group_id"]:
        hard.append("run_id or group_id does not match the task")
    wanted = set(group["transition_ids"])
    got = [t["transition_id"] for t in answer.get("transitions") or []]
    if set(got) != wanted or len(got) != len(set(got)):
        hard.append(f"the transitions of the answer {sorted(got)} are not the assigned {sorted(wanted)}")
    if set(answer.get("processed_block_ids") or []) != set(group["block_ids"]) or answer.get("unprocessed_block_ids"):
        hard.append(
            f"not every assigned block is processed: {sorted(answer.get('processed_block_ids') or [])} of {group['block_ids']}; "
            f"not processed {answer.get('unprocessed_block_ids')}"
        )
    elif answer.get("partial"):
        soft.append("partial = true with every block processed -- probably the part of a split transition")
    by_block = {b["block_id"]: b for b in plan["blocks"]}
    allowed = [r for bid in group["block_ids"] for r in by_block[bid]["ranges"]]
    if manifest["header"]["line_end"]:
        allowed.append([1, manifest["header"]["line_end"]])
    transitions = _by_id(manifest)
    bad = total = 0
    for item in answer.get("transitions") or []:
        parsed = transitions.get(item["transition_id"])
        refs = [r for f in item.get("facts") or [] for r in f.get("evidence") or []]
        refs += [r for n in (item.get("explicit_conditions") or []) + (item.get("contradictions") or []) for r in n.get("evidence") or []]
        for ref in refs:
            total += 1
            if not (ref["md_from"] <= ref["md_to"] and _within(allowed, ref["md_from"], ref["md_to"])):
                bad += 1
        for fact in item.get("facts") or []:
            if not fact.get("evidence"):
                hard.append(f"{item['transition_id']}/{fact.get('fact_id')}: a fact without lines of the source")
        if parsed and parsed.get("explicit_no_content_changes") and not parsed["sheets"]:
            if item.get("content_status") != "no_content_changes" or item.get("facts"):
                hard.append(f"{item['transition_id']}: the summary says «изменений содержания нет», the answer has changes")
    if bad:
        hard.append(f"{bad} of {total} references are to lines outside the assigned text")
    if answer.get("input_problems"):
        soft.append("the analyst reported problems of the input: " + "; ".join(answer["input_problems"])[:500])
    return {"ok": not hard, "hard": hard, "soft": soft}


# ------------------------------------------------------------------ the verifier (stages.py:174-357)

def claims_for_unit(results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """The claims to verify: the facts, the assessments, the conditions and the contradictions of every group of the unit."""
    out: list[dict[str, Any]] = []
    for gid, answer in results.items():
        for item in answer.get("transitions") or []:
            tid = item["transition_id"]
            out.append({
                "claim_id": f"{gid}.{tid}.A", "transition_id": tid, "kind": "оценка перехода",
                "text": f"масштаб «{item['change_scope']}», значимость «{item['significance']}», "
                        f"основание: {item['assessment_basis']}; последствия: {item['construction_impact']}",
                "evidence": [],
            })
            for fact in item.get("facts") or []:
                text = f"{fact['object']}: {fact['before']} → {fact['after']}"
                if fact.get("possible_consequence"):
                    text += f"; последствие: {fact['possible_consequence']}"
                if fact.get("uncertainty"):
                    text += f"; неясность: {fact['uncertainty']}"
                out.append({
                    "claim_id": f"{gid}.{tid}.{fact['fact_id']}", "transition_id": tid,
                    "kind": "факт" + (" (кандидат в серьёзные)" if fact.get("serious_candidate") else ""), "text": text,
                    "evidence": fact.get("evidence") or [], "related_objects": fact.get("related_objects") or [],
                    "serious": bool(fact.get("serious_candidate")),
                })
            for k, note in enumerate(item.get("explicit_conditions") or [], 1):
                out.append({"claim_id": f"{gid}.{tid}.K{k}", "transition_id": tid, "kind": "условие выдачи",
                            "text": note["text"], "evidence": note.get("evidence") or []})
            for k, note in enumerate(item.get("contradictions") or [], 1):
                out.append({"claim_id": f"{gid}.{tid}.X{k}", "transition_id": tid, "kind": "противоречие",
                            "text": note["text"], "evidence": note.get("evidence") or []})
    return out


_TOKEN = re.compile(r"[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё0-9.\-/]*\d[A-Za-zА-Яа-яЁё0-9.\-/]*")


def related_tokens(claims: list[dict[str, Any]]) -> list[str]:
    seen: list[str] = []
    for claim in claims:
        for obj in claim.get("related_objects") or []:
            for token in _TOKEN.findall(obj or ""):
                token = token.strip(".-/")
                if len(token) >= 3 and token not in seen:
                    seen.append(token)
    return seen[:RELATED_MAX_TOKENS]


def _excerpt_ranges(claims: list[dict[str, Any]], manifest: dict[str, Any], lines_total: int) -> list[list[int]]:
    marks: set[int] = set()
    for claim in claims:
        for ref in claim.get("evidence") or []:
            marks.update(range(max(1, ref["md_from"] - EXCERPT_PAD), min(lines_total, ref["md_to"] + EXCERPT_PAD) + 1))
            where = parse.locate(manifest, ref["md_from"])
            if where["sheet"]:
                marks.add(where["sheet"]["line_start"])
            if where["transition"]:
                marks.add(where["transition"]["line_start"])
    out: list[list[int]] = []
    for line in sorted(marks):
        if out and out[-1][1] + 1 == line:
            out[-1][1] = line
        else:
            out.append([line, line])
    return out


def verifier_prompt(
    run_id: str, source: dict[str, Any], manifest: dict[str, Any], plan: dict[str, Any], unit: dict[str, Any],
    results: dict[str, dict[str, Any]], claims: list[dict[str, Any]], lines: list[str],
) -> tuple[str, list[list[int]]]:
    """The task of the verifier and the ranges of lines shown to it (a reference is allowed only to those) -- stages.py:237-309."""
    transitions = _by_id(manifest)
    by_block = {b["block_id"]: b for b in plan["blocks"]}
    groups = {g["group_id"]: g for g in plan["groups"]}
    unit_ranges = [[transitions[t]["line_start"], transitions[t]["line_end"]] for t in unit["transition_ids"]]
    full = sum(sum(len(lines[i - 1]) + 1 for i in range(s, e + 1)) for s, e in unit_ranges) <= VERIFY_FULL_CHARS
    shown = unit_ranges if full else _excerpt_ranges(claims, manifest, len(lines))
    mode = (
        "Полный текст переходов этой единицы." if full else
        "Выдержки: строки доказательств аналитиков с соседними строками и заголовками листов "
        "(полный текст единицы больше предела одного задания)."
    )
    unit_lines = {i for s, e in unit_ranges for i in range(s, e + 1)}
    registry = manifest.get("registry")
    if registry:  # the coverage registry is not text of the summary: related places are not searched in it
        unit_lines |= set(range(registry["line_start"], registry["line_end"] + 1))
    related_ranges: list[list[int]] = []
    related_text: list[str] = []
    size = 0
    for token in related_tokens(claims):
        hits = [i for i, line in enumerate(lines, 1) if token in line and i not in unit_lines][:RELATED_PER_TOKEN]
        for i in hits:
            where = parse.locate(manifest, i)
            place = where["transition"]["label"] if where["transition"] else "заголовок"
            head = f" ({_clean(where['sheet']['heading'], 120)})" if where["sheet"] else ""
            row = f"[{i}] «{token}» — {place}{head}: {lines[i - 1]}"
            if size + len(row) > RELATED_MAX_CHARS:
                break
            related_text.append(row)
            related_ranges.append([i, i])
            size += len(row)
    unit_manifest = [_transition_line(transitions[t]) for t in unit["transition_ids"]]
    for gid in unit["group_ids"]:
        group = groups[gid]
        unit_manifest.append(f"- группа {gid}: блоки " + ", ".join(
            f"{b} ({', '.join(f'{s}–{e}' for s, e in by_block[b]['ranges'])})" for b in group["block_ids"]
        ))
    claim_lines = [
        f"- {c['claim_id']} [{c['transition_id']}, {c['kind']}]: {c['text']}"
        + (f" (строки {', '.join(str(r['md_from']) + '–' + str(r['md_to']) for r in c['evidence'])})" if c.get("evidence") else "")
        for c in claims
    ]
    # sorted keys: a result read back from the database has its keys in the order jsonb keeps them, and the same data must make the same prompt
    analyst_json = json.dumps({
        gid: {"transitions": answer.get("transitions"), "input_problems": answer.get("input_problems")}
        for gid, answer in results.items()
    }, ensure_ascii=False, sort_keys=True)
    prompt = render("verifier", {
        "UNIT_NOTE": "Все переходы единицы переданы целиком.", "RUN_ID": run_id, "UNIT_ID": unit["unit_id"],
        "SOURCE_METADATA": source_metadata(source, manifest), "UNIT_MANIFEST": "\n".join(unit_manifest),
        "ANALYST_RESULTS": analyst_json, "CLAIMS_TO_VERIFY": "\n".join(claim_lines), "SOURCE_MODE": mode,
        "SOURCE_TEXT": "\n".join(numbered(lines, [r]) for r in shown),
        "RELATED_TEXT": "\n".join(related_text) or "— связанных мест в других переходах не найдено",
    }, f"{run_id}:V:{unit['unit_id']}")
    allowed = shown + related_ranges
    if manifest["header"]["line_end"]:
        allowed = allowed + [[1, manifest["header"]["line_end"]]]
    return prompt, allowed


def check_verifier(answer: dict[str, Any], run_id: str, unit: dict[str, Any], claims: list[dict[str, Any]], shown: list[list[int]]) -> dict[str, Any]:
    """A verdict for every claim, a total for every transition of the unit, references only to the lines shown (stages.py:312-335)."""
    hard: list[str] = []
    soft: list[str] = []
    if answer.get("run_id") != run_id or answer.get("unit_id") != unit["unit_id"]:
        hard.append("run_id or unit_id does not match the task")
    wanted = {c["claim_id"] for c in claims}
    got = [c["claim_id"] for c in answer.get("claims") or []]
    missing = sorted(wanted - set(got))
    if missing:
        hard.append(f"no verdict for the claims: {', '.join(missing[:30])}" + (" …" if len(missing) > 30 else ""))
    extra = sorted(set(got) - wanted)
    if extra:
        soft.append(f"verdicts for unknown claims dropped: {', '.join(extra[:20])}")
    ids = [t["transition_id"] for t in answer.get("transitions") or []]
    if set(ids) != set(unit["transition_ids"]) or len(ids) != len(set(ids)):
        hard.append(f"the totals of the transitions {sorted(ids)} are not those of the unit {unit['transition_ids']}")
    refs = [r for c in answer.get("claims") or [] for r in c.get("evidence") or []]
    refs += [r for t in answer.get("transitions") or [] for r in t.get("evidence") or []]
    refs += [r for s in answer.get("significant_candidates") or [] for r in s.get("evidence") or []]
    bad = [r for r in refs if not (r["md_from"] <= r["md_to"] and _within(shown, r["md_from"], r["md_to"]))]
    if refs and len(bad) > max(2, 0.2 * len(refs)):
        hard.append(f"{len(bad)} of {len(refs)} references are to lines not shown in the task")
    elif bad:
        soft.append(f"references to lines not shown dropped: {len(bad)}")
    return {"ok": not hard, "hard": hard, "soft": soft, "bad_refs": bad}


def clean_verifier(answer: dict[str, Any], claims: list[dict[str, Any]], shown: list[list[int]]) -> dict[str, Any]:
    """Drop foreign verdicts, references outside what was shown and candidates that rest on rejected claims (stages.py:338-357)."""
    wanted = {c["claim_id"]: c for c in claims}

    def ok_ref(ref: dict[str, int]) -> bool:
        return ref["md_from"] <= ref["md_to"] and _within(shown, ref["md_from"], ref["md_to"])

    out = json.loads(json.dumps(answer))
    out["claims"] = [
        c | {"evidence": [r for r in c["evidence"] if ok_ref(r)], "transition_id": wanted[c["claim_id"]]["transition_id"],
             "kind": wanted[c["claim_id"]]["kind"]}
        for c in out["claims"] if c["claim_id"] in wanted
    ]
    verdict = {c["claim_id"]: c["verdict"] for c in out["claims"]}
    for item in out["transitions"]:
        item["evidence"] = [r for r in item["evidence"] if ok_ref(r)]
        item["key_claim_ids"] = [x for x in item["key_claim_ids"] if verdict.get(x) not in (None, "rejected")]
    candidates = []
    for candidate in out["significant_candidates"]:
        candidate["claim_ids"] = [x for x in candidate["claim_ids"] if verdict.get(x) not in (None, "rejected")]
        candidate["evidence"] = [r for r in candidate["evidence"] if ok_ref(r)]
        if candidate["claim_ids"]:
            candidates.append(candidate)
    out["significant_candidates"] = candidates
    return out


# ------------------------------------------------------------------ the composer (stages.py:362-668)

def verified_parts(verified: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for uid, result in verified.items():
        for item in result["transitions"]:
            out.setdefault(item["transition_id"], []).append(item | {"unit_id": uid})
    return out


def final_assessment(tid: str, composed: dict[str, Any], parts: dict[str, list[dict[str, Any]]]) -> tuple[str, str, str]:
    """(scale, significance, note). One verified total is the assessment; several parts take the composer's, never below a verified part
    (stages.py:371-386)."""
    found = parts.get(tid) or []
    if not found:
        return composed["change_scope"], composed["significance"], "нет проверенного итога"
    if len(found) == 1:
        return found[0]["change_scope"], found[0]["significance"], ""
    scope_part = max(found, key=lambda p: SCOPE_RANK[p["change_scope"]])["change_scope"]
    significance_part = max(found, key=lambda p: SIGNIFICANCE_RANK[p["significance"]])["significance"]
    scope, significance, note = composed["change_scope"], composed["significance"], ""
    if SCOPE_RANK[scope] < SCOPE_RANK[scope_part]:
        scope, note = scope_part, f"масштаб поднят до оценки части ({scope_part})"
    if SIGNIFICANCE_RANK[significance] < SIGNIFICANCE_RANK[significance_part]:
        significance = significance_part
        note = (note + "; " if note else "") + f"значимость поднята до оценки части ({significance_part})"
    return scope, significance, note


def registry_row(manifest: dict[str, Any], transition: dict[str, Any]) -> dict[str, Any] | None:
    registry = manifest.get("registry") or {}
    return next((r for r in registry.get("rows") or [] if r["label"] == transition["label"]), None)


def completeness(manifest: dict[str, Any], transition: dict[str, Any]) -> dict[str, Any]:
    """Completeness of a transition by the set of processed sheets of the coverage registry, not by the model's opinion (stages.py:395-412)."""
    row = registry_row(manifest, transition)
    if not row:
        gaps = len(transition.get("source_incomplete") or [])
        return {
            "complete": None, "registry": False, "marks": [],
            "text": "реестр покрытия в сводке не передан; полнота по набору листов не подтверждена"
                    + (f"; неописанных мест в сводке: {gaps}" if gaps else ""),
        }
    counts = row["counts"]
    total = row["sheets_total"]
    left, unclear = counts.get("не обработано", 0), counts.get("неоднозначно", 0)
    text = f"обработаны все {total} листов" if not left else f"не обработано {left} из {total} листов"
    if unclear:
        text += f"; неоднозначно {unclear}"
    return {
        "complete": not left, "registry": True, "sheets_total": total, "counts": counts, "text": text,
        "marks": [d["text"] for d in row["details"] if d["kind"] == "отметка документа"],
        "not_processed": [d["text"] for d in row["details"] if d["kind"] == "не обработано"],
        "ambiguous": [d["text"] for d in row["details"] if d["kind"] == "неоднозначно"],
    }


def coverage_text(manifest: dict[str, Any], verified: dict[str, dict[str, Any]]) -> str:
    rows = []
    done = {t["transition_id"]: t for v in verified.values() for t in v["transitions"]}
    for transition in manifest["transitions"]:
        result = done.get(transition["transition_id"])
        comp = completeness(manifest, transition)
        extra = f"проверено: {'да' if result else 'НЕТ'}; полнота: {comp['text']}"
        if comp["marks"]:
            extra += "; отметка документа (не изменение оборудования, не доказательство согласования): " + " | ".join(comp["marks"])
        rows.append(_transition_line(transition, extra))
    return "\n".join(rows)


def _claim_refs(claim: dict[str, Any]) -> list[dict[str, int]]:
    return [r for r in claim.get("evidence") or [] if r["md_from"] <= r["md_to"]]


FACTS_PER_CLAIM: Final[int] = 4  # stages.py:433
FACTS_PER_CANDIDATE: Final[int] = 8  # :434


def composer_facts(registry: dict[str, Any], verified: dict[str, dict[str, Any]]) -> list[str]:
    """IDs of the facts shown in full in the composer's input: the first facts of every verified claim and candidate (a wide range of a claim
    -- hundreds of items of a specification -- is given as an ID reference, not as text, or the input would pass the window). Numbers of the
    answer are checked against the whole registry (stages.py:437-449)."""
    chosen: list[str] = []
    for result in verified.values():
        for claim in result["claims"]:
            if claim["verdict"] != "rejected":
                chosen += facts_mod.in_ranges(registry, _claim_refs(claim))[:FACTS_PER_CLAIM]
        for candidate in result["significant_candidates"]:
            chosen += facts_mod.in_ranges(registry, candidate.get("evidence") or [])[:FACTS_PER_CANDIDATE]
    order = {f["fact_id"]: k for k, f in enumerate(registry["facts"])}
    return sorted(dict.fromkeys(chosen), key=lambda x: order.get(x, 0))


def _id_ranges(ids: list[str]) -> list[str]:
    """«Ф0100, Ф0101, …, Ф0350» → «Ф0100–Ф0350» (stages.py:452-465)."""
    numbers_ = sorted({int(x[1:]) for x in ids if x[1:].isdigit()})
    out: list[str] = []
    start = previous = None
    for n in [*numbers_, None]:
        if start is None:
            start = previous = n
            continue
        if n is not None and n == previous + 1:  # type: ignore[operator]
            previous = n
            continue
        out.append(f"Ф{start:04d}" if start == previous else f"Ф{start:04d}–Ф{previous:04d}")
        start = previous = n
    return out


def composer_prompt(
    run_id: str, source: dict[str, Any], manifest: dict[str, Any], verified: dict[str, dict[str, Any]],
    retry_note: str = "", registry: dict[str, Any] | None = None,
) -> str:
    registry = registry or {"facts": []}
    data: dict[str, Any] = {"transitions": [], "claims": [], "significant_candidates": [], "unresolved_questions": []}
    parts = verified_parts(verified)
    for uid, result in verified.items():
        data["transitions"] += [
            t | {"unit_id": uid, "partial_of_split_transition": len(parts[t["transition_id"]]) > 1} for t in result["transitions"]
        ]
        data["claims"] += [
            {k: c[k] for k in ("claim_id", "transition_id", "kind", "verdict", "verified_wording", "linked_claim_ids")}
            | {"fact_ids": _id_ranges(facts_mod.in_ranges(registry, _claim_refs(c)))}
            for c in result["claims"] if c["verdict"] != "rejected"
        ]
        data["significant_candidates"] += [
            s | {"fact_ids": _id_ranges(facts_mod.in_ranges(registry, s.get("evidence") or []))}
            for s in result["significant_candidates"]
        ]
        data["unresolved_questions"] += result["unresolved_questions"]
    order = {t["transition_id"]: k for k, t in enumerate(manifest["transitions"])}
    data["transitions"].sort(key=lambda t: order.get(t["transition_id"], 999))
    for item in data["transitions"]:
        item.pop("evidence", None)
    for item in data["significant_candidates"]:
        item.pop("evidence", None)
    by_id = facts_mod.index(registry)
    used = composer_facts(registry, verified)
    fact_text = "\n".join(facts_mod.model_line(by_id[f]) for f in used) or "— фактов нет"
    return render("composer", {
        "RUN_ID": run_id, "SOURCE_METADATA": source_metadata(source, manifest),
        "VERIFIED_COVERAGE": coverage_text(manifest, verified), "VERIFIED_RESULTS": json.dumps(data, ensure_ascii=False, sort_keys=True),
        "FACTS": fact_text, "RETRY_NOTE": retry_note,
    }, f"{run_id}:C")


# Designations of versions, sheets and pages are not numeric claims («V12», «л.9», «лист 9», «стр. PDF 14») -- stages.py:500-503.
_SKIP_NUM = re.compile(
    r"(?:\bV|\bл\.\s*|\bлист(?:а|е|у|ом|ы|ов|ах)?\s*№?\s*|\bP|стр\.\s*(?:PDF\s*)?|страниц[аеыу]?\s*(?:PDF\s*)?|СО\s+л\.\s*)\d+",
    re.IGNORECASE,
)
_NUM = re.compile(r"\d+(?:[.,]\d+)?")


def numbers(text: str | None) -> set[str]:
    text = _SKIP_NUM.sub(" ", text or "")
    return {n.replace(",", ".") for n in _NUM.findall(text)}


ARROW: Final[str] = "→"
#: The consequence is worded conditionally: «при выполнении по предыдущей версии потребовалась бы…», «если…» (stages.py:519-522).
CONDITIONAL = re.compile(
    r"\bесли\b|\bпри\b|в случае|может|могл|возможн|требовал|потребова|бы\b|проверк|не выявлен|не установлен|неизвестн|уточн", re.I
)


def _row_texts(answer: dict[str, Any]) -> list[tuple[str, str, list[str]]]:
    out = []
    for item in answer.get("transitions") or []:
        for k, change in enumerate(item.get("changes") or [], 1):
            out.append((
                f"строка {item['transition_id']} / изменение {k} «{change.get('object', '')[:50]}»",
                f"{change.get('before', '')} {ARROW} {change.get('after', '')}", change.get("fact_ids") or [],
            ))
    for k, change in enumerate(answer.get("significant_changes") or [], 1):
        out.append((f"серьёзное изменение {k} «{change.get('title', '')[:50]}»", change.get("before_after", ""), change.get("fact_ids") or []))
    return out


def fact_refs(answer: dict[str, Any]) -> list[tuple[str, str | None, list[str]]]:
    out: list[tuple[str, str | None, list[str]]] = [("общий вывод", None, answer.get("summary_fact_ids") or [])]
    for item in answer.get("transitions") or []:
        for k, change in enumerate(item.get("changes") or [], 1):
            out.append((f"{item['transition_id']} / изменение {k}", item["transition_id"], change.get("fact_ids") or []))
        out.append((f"{item['transition_id']} / последствия", item["transition_id"], item.get("impact_fact_ids") or []))
    for k, change in enumerate(answer.get("significant_changes") or [], 1):
        out.append((f"серьёзное изменение {k}", None, change.get("fact_ids") or []))
    return out


def _fact_pool(by_id: dict[str, dict[str, Any]], ids: list[str]) -> str:
    out = []
    for i in ids:
        fact = by_id.get(facts_mod.normalize_id(i))
        if fact:
            out.append(fact["text"])
            out.append(json.dumps(fact.get("details") or {}, ensure_ascii=False))
    return "\n".join(out)


def is_chain(text: str) -> bool:
    """A chain is several «→» in a row in one record («150 → 35 → 18 м»). A list of separate «was → became» through «;» is a combined
    conclusion, not a chain (stages.py:560-564)."""
    text = re.sub(r"\bV\d+\s*→\s*V\d+", "", text or "")
    return any(segment.count(ARROW) >= 2 for segment in re.split(r"[;\n]|\.\s", text))


def chain_problems(answer: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> list[str]:
    """A chain of values over several facts is allowed only for a confirmed single line: every fact has the same letter-and-digit designation of
    the object. Otherwise the changes are given apart (stages.py:567-581)."""
    out = []
    for where, text, ids in _row_texts(answer):
        ids = [facts_mod.normalize_id(i) for i in ids]
        known = [by_id[i] for i in ids if i in by_id]
        if not is_chain(text) or len(known) < 2:
            continue
        keys = {f.get("identity") for f in known}
        if None in keys or len(keys) != 1:
            out.append(
                f"{where}: a chain of values from the facts {', '.join(f['fact_id'] for f in known)} without a confirmed single line "
                "(no common designation) -- give the changes in separate rows, each with its own fact"
            )
    return out


_CLAIM_ID = re.compile(r"\bG\d{2}\.T\d{2}(?:\.[A-Z]+\d*)?\b")
_FACT_TEXT = re.compile(r"\b[ФF]\d{4}\b")


def _user_texts(answer: dict[str, Any]) -> list[str]:
    parts = list(answer.get("summary") or []) + list(answer.get("limitations") or [])
    for item in answer.get("transitions") or []:
        parts += [item.get("main_changes", ""), item.get("construction_impact", "")]
        for change in item.get("changes") or []:
            parts += [change.get("object", ""), change.get("before", ""), change.get("after", "")]
    for change in answer.get("significant_changes") or []:
        parts += [change.get("title", ""), change.get("before_after", ""), change.get("consequence", ""), change.get("version_range", "")]
    return parts


def _id_pattern(manifest: dict[str, Any], lines: list[str]) -> re.Pattern[str] | None:
    """The program's transition designations (T01 …) that are not in the source text are internal (stages.py:687-691)."""
    source = "\n".join(lines)
    ids = [t["transition_id"] for t in manifest["transitions"] if not re.search(rf"\b{t['transition_id']}\b", source)]
    return re.compile(r"\b(" + "|".join(ids) + r")\b") if ids else None


def internal_ids(answer: dict[str, Any], manifest: dict[str, Any], lines: list[str]) -> list[str]:
    pattern = _id_pattern(manifest, lines)
    found: set[str] = set()
    for text in _user_texts(answer):
        found.update(_CLAIM_ID.findall(text))
        found.update(_FACT_TEXT.findall(text))
        if pattern:
            found.update(pattern.findall(text))
    return sorted(found)


def humanize(text: str, manifest: dict[str, Any], pattern: re.Pattern[str] | None) -> str:
    """A safeguard after the check: an internal transition ID → «V10→V11»; claim references and fact IDs in the text are removed (stages.py:705-712)."""
    labels = {t["transition_id"]: t["label"] for t in manifest["transitions"]}
    text = _FACT_TEXT.sub("", _CLAIM_ID.sub("", text))
    if pattern:
        text = pattern.sub(lambda m: labels[m.group(1)], text)
    return re.sub(r"\s+([,.;:])", r"\1", re.sub(r"\(\s*[,;]*\s*\)", "", text))


def word_count(answer: dict[str, Any]) -> int:
    return sum(len(re.findall(r"\w+", p)) for p in _user_texts(answer))


def check_composer(
    answer: dict[str, Any], run_id: str, manifest: dict[str, Any], verified: dict[str, dict[str, Any]], lines: list[str],
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The check of the composer's answer (stages.py:584-669): exactly the transitions of the report, at most 5 serious changes, each citing
    verified claims, **every number of the text found in the cited facts or in the verified wordings**, no internal identifiers."""
    hard: list[str] = []
    soft: list[str] = []
    fixable: list[str] = []
    registry = registry or {"facts": []}
    by_id = facts_mod.index(registry)
    if answer.get("run_id") != run_id:
        hard.append("run_id does not match the task")
    wanted = [t["transition_id"] for t in manifest["transitions"]]
    got = [t["transition_id"] for t in answer.get("transitions") or []]
    if sorted(got) != sorted(wanted):
        hard.append(f"the report must hold exactly the transitions {wanted}; got {got}")
    claims = {c["claim_id"]: c for v in verified.values() for c in v["claims"]}
    significant = answer.get("significant_changes") or []
    if len(significant) > MAX_SERIOUS:
        hard.append(f"{len(significant)} serious changes -- at most {MAX_SERIOUS} are allowed")
    for i, change in enumerate(significant):
        bad = [x for x in change.get("claim_ids") or [] if x not in claims or claims[x]["verdict"] == "rejected"]
        if bad:
            hard.append(f"serious change {i + 1} rests on unknown or rejected claims: {bad}")
        if not change.get("claim_ids"):
            hard.append(f"serious change {i + 1} has no verified claims (claim_ids)")
        if not change.get("fact_ids"):
            fixable.append(f"serious change {i + 1} has no facts (fact_ids)")
    unknown: list[str] = []
    foreign: list[str] = []
    for where, tid, ids in fact_refs(answer):
        for x in ids:
            fact = by_id.get(facts_mod.normalize_id(x))
            if fact is None:
                unknown.append(f"{where}: {x}")
            elif tid and fact["transition_id"] != tid:
                foreign.append(f"{where}: {x} ({fact['transition']})")
    if unknown:
        fixable.append("unknown fact IDs: " + "; ".join(unknown[:20]) + (" …" if len(unknown) > 20 else ""))
    if foreign:
        fixable.append("facts of another transition in a row of a transition: " + "; ".join(foreign[:20]) + (" …" if len(foreign) > 20 else ""))
    fixable += chain_problems(answer, by_id)
    unconfirmed: list[dict[str, Any]] = []
    for i, change in enumerate(significant):
        pool = _fact_pool(by_id, change.get("fact_ids") or []) + "\n" + "\n".join(
            claims[x]["verified_wording"] for x in change.get("claim_ids") or [] if x in claims
        )
        missing = (numbers(change.get("before_after", "")) | numbers(change.get("consequence", "")) | numbers(change.get("title", ""))) - numbers(pool)
        if missing:
            unconfirmed.append({"where": f"серьёзное изменение {i + 1} «{change.get('title', '')[:60]}»", "numbers": sorted(missing)})
    parts_ = verified_parts(verified)
    for item in answer.get("transitions") or []:
        tid = item["transition_id"]
        ids = [x for c in item.get("changes") or [] for x in c.get("fact_ids") or []] + (item.get("impact_fact_ids") or [])
        pool = _fact_pool(by_id, ids) + "\n" + json.dumps(parts_.get(tid) or [], ensure_ascii=False) + "\n" + "\n".join(
            c["verified_wording"] for c in claims.values() if c.get("transition_id") == tid
        )
        text = " ".join(
            [item.get("main_changes", ""), item.get("construction_impact", "")]
            + [f"{c.get('object', '')} {c.get('before', '')} {c.get('after', '')}" for c in item.get("changes") or []]
        )
        missing = numbers(text) - numbers(pool)
        if missing:
            unconfirmed.append({"where": f"строка таблицы {tid}", "numbers": sorted(missing)})
        if item.get("construction_impact") and not CONDITIONAL.search(item["construction_impact"]):
            soft.append(f"{tid}: the consequence is worded unconditionally -- «{item['construction_impact'][:80]}»")
    pool_all = "\n".join(c["verified_wording"] for c in claims.values()) + "\n" + _fact_pool(by_id, answer.get("summary_fact_ids") or [])
    missing = set().union(*[numbers(x) for x in answer.get("summary") or []] or [set()]) - numbers(pool_all) - {str(len(wanted))}
    if missing:
        unconfirmed.append({"where": "общий вывод", "numbers": sorted(missing)})
    if unconfirmed:
        fixable.append(
            "numbers found neither in the cited facts nor in the verified wordings: "
            + "; ".join(f"{u['where']}: {', '.join(u['numbers'])}" for u in unconfirmed)
        )
    leaked = internal_ids(answer, manifest, lines)
    if leaked:
        fixable.append(
            "internal identifiers in the text for a person: " + ", ".join(leaked)
            + " -- name the transitions by versions (e.g. «V10→V11»), fact IDs only in the fields fact_ids"
        )
    words = word_count(answer)
    if words > WORD_LIMIT:
        fixable.append(f"the text is longer than the limit: {words} words, the target is 900")
    for item in answer.get("transitions") or []:
        scope, significance, note = final_assessment(item["transition_id"], item, parts_)
        if (scope, significance) != (item["change_scope"], item["significance"]):
            soft.append(
                f"{item['transition_id']}: the composer's assessment ({item['change_scope']} / {item['significance']}) was replaced by the "
                f"verified one ({scope} / {significance}){'; ' + note if note else ''}"
            )
    return {
        "ok": not hard and not fixable, "hard": hard, "fixable": fixable, "soft": soft, "unconfirmed_numbers": unconfirmed,
        "words": words, "bad_fact_refs": unknown + foreign, "chains": chain_problems(answer, by_id),
    }


# ------------------------------------------------------------------ assembly of report_v2 (stages.py:719-843)
_MD_MARK = re.compile(r"\*\*|__|`+|</?[A-Za-z][^<>]{0,40}>")


def plain(text: str | None) -> str:
    """Text for the PDF without Markdown or HTML that came from the source or the answer (stages.py:724-728)."""
    text = _MD_MARK.sub("", str(text or ""))
    text = re.sub(r"^\s*[-*•]\s+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _bare(text: str | None) -> str:
    """A cell «object / was / became» without the closing full stop: a row of a table is not a sentence."""
    return plain(text).rstrip(" .;")


def _strip_label(text: str, label: str) -> str:
    """The designation of the transition at the start of a row text is superfluous: it is in the first column already."""
    a, b = label.split("→", 1)
    match = re.match(rf"^\s*{re.escape(a)}\s*→\s*{re.escape(b)}\s*[:—–-]\s*", text)
    return text[match.end():] if match else text


def _valid_ids(by_id: dict[str, dict[str, Any]], ids: list[str], tid: str | None, dropped: list[str], where: str) -> list[str]:
    out: list[str] = []
    for x in ids or []:
        fact = by_id.get(facts_mod.normalize_id(x))
        if fact is None or (tid and fact["transition_id"] != tid):
            dropped.append(f"{where}: {x}" + ("" if fact is None else f" (a fact of {fact['transition']})"))
            continue
        if fact["fact_id"] not in out:
            out.append(fact["fact_id"])
    return out


def assemble(
    answer: dict[str, Any], manifest: dict[str, Any], verified: dict[str, dict[str, Any]], source: dict[str, Any],
    lines: list[str], registry: dict[str, Any],
) -> dict[str, Any]:
    """``report_v2`` from the composer's answer: the order, the labels A/B and the dates come from the parse, the assessments are the verified
    ones, the completeness is by the coverage registry, the sources are the passports of the named facts (stages.py:756-843)."""
    by_id = facts_mod.index(registry)
    pattern = _id_pattern(manifest, lines)
    answer = json.loads(json.dumps(answer))
    dropped: list[str] = []
    for key in ("summary", "limitations"):
        answer[key] = [humanize(x, manifest, pattern) for x in answer[key]]
    for item in answer["transitions"]:
        label = next(m["label"] for m in manifest["transitions"] if m["transition_id"] == item["transition_id"])
        for key in ("main_changes", "construction_impact"):
            item[key] = _strip_label(humanize(item[key], manifest, pattern), label)
        for change in item.get("changes") or []:
            for key in ("object", "before", "after"):
                change[key] = humanize(change[key], manifest, pattern)
    for change in answer["significant_changes"]:
        for key in ("title", "before_after", "consequence", "version_range"):
            change[key] = humanize(change[key], manifest, pattern)
    chains = set(chain_problems(answer, by_id))
    parts_ = verified_parts(verified)
    composed = {t["transition_id"]: t for t in answer["transitions"]}
    cited: list[str] = []

    def cite(ids: list[str]) -> list[str]:
        for x in ids:
            if x not in cited:
                cited.append(x)
        return ids

    transitions = []
    for transition in manifest["transitions"]:
        tid = transition["transition_id"]
        item = composed[tid]
        scope, significance, _note = final_assessment(tid, item, parts_)
        rows = []
        for k, change in enumerate(item.get("changes") or [], 1):
            ids = cite(_valid_ids(by_id, change.get("fact_ids"), tid, dropped, f"{transition['label']} / изменение {k}"))
            if not ids:
                dropped.append(f"{transition['label']} / изменение {k} «{plain(change['object'])[:50]}» — убрано: нет фактов")
                continue
            rows.append({
                "object": _bare(change["object"]), "before": _bare(change["before"]), "after": _bare(change["after"]),
                "sources": ids, "chain_unconfirmed": any(w.startswith(f"строка {tid} / изменение {k} ") for w in chains),
            })
        impact = cite(_valid_ids(by_id, item.get("impact_fact_ids"), tid, dropped, f"{transition['label']} / последствия"))
        comp = completeness(manifest, transition)
        transitions.append({
            "transition_id": tid, "from_version": transition["from_version"], "to_version": transition["to_version"],
            "from_label": transition["a_label"], "to_label": transition["b_label"], "from_date": transition["from_date"],
            "to_date": transition["to_date"], "change_scope": scope, "significance": significance, "completeness": comp,
            "main_changes": plain(item["main_changes"]), "changes": rows,
            "construction_impact": plain(item["construction_impact"]), "impact_sources": impact,
            "document_marks": comp["marks"],
            "sources": list(dict.fromkeys([x for r in rows for x in r["sources"]] + impact)),
        })
    significant_out = []
    for k, change in enumerate(answer["significant_changes"], 1):
        ids = cite(_valid_ids(by_id, change.get("fact_ids"), None, dropped, f"серьёзное изменение {k}"))
        if not ids:
            dropped.append(f"серьёзное изменение {k} «{plain(change['title'])[:50]}» — убрано: нет действительных фактов")
            continue
        significant_out.append({
            "priority": change["priority"], "title": plain(change["title"]), "version_range": plain(change["version_range"]),
            "before_after": plain(change["before_after"]), "consequence": plain(change["consequence"]),
            "claim_ids": change["claim_ids"], "sources": ids,
            "chain_unconfirmed": any(w.startswith(f"серьёзное изменение {k} ") for w in chains),
        })
    summary_ids = cite(_valid_ids(by_id, answer.get("summary_fact_ids"), None, dropped, "общий вывод"))
    order = {f["fact_id"]: n for n, f in enumerate(registry["facts"])}
    return {
        "schema_version": "report_v2",
        "project_code": manifest.get("project_code") or Path(source["filename"]).stem,
        "title": "Оценка изменений версий документации", "input_filename": source["filename"],
        "analysis_basis": {
            "type": "ai_change_summary", "description": "Анализ готовой ИИ-сводки изменений версий; исходные PDF не проверялись.",
            "source_pdf_checked": False, "records": bool(registry.get("with_records")),
        },
        "summary": [plain(x) for x in answer["summary"] if plain(x)], "summary_sources": summary_ids,
        "transitions": transitions, "significant_changes": significant_out,
        "limitations": [plain(x) for x in answer["limitations"] if plain(x)],
        "facts": [facts_mod.passport(by_id[x]) for x in sorted(cited, key=lambda x: order[x])],
        "facts_total": len(registry["facts"]),
        "coverage": [{"label": t["label"], **completeness(manifest, t)} for t in manifest["transitions"]],
        "reference_warnings": dropped,
    }


def distribution(report: dict[str, Any]) -> dict[str, int]:
    """The distribution of the transitions is counted by the program (stages.py:846-854)."""
    out = {"total": 0, "technical": 0, "no_content_change": 0, "formatting_only": 0, "unknown": 0}
    for item in report["transitions"]:
        out["total"] += 1
        scope = normalize_scope(item["change_scope"])
        key = (
            "technical" if scope in TECHNICAL_SCOPES else "no_content_change" if scope == "Нет изменений содержания"
            else "formatting_only" if scope == "Только оформление" else "unknown"
        )
        out[key] += 1
    return out


def consistency(report: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    """The report matches the parse: one row per transition in the source order, the explicit marks kept (stages.py:857-870)."""
    problems = []
    wanted = [(t["from_version"], t["to_version"]) for t in manifest["transitions"]]
    got = [(t["from_version"], t["to_version"]) for t in report["transitions"]]
    if wanted != got:
        problems.append("the order or the set of transitions differs from the source")
    for item, parsed in zip(report["transitions"], manifest["transitions"]):
        scope = normalize_scope(item["change_scope"])
        if parsed.get("explicit_no_content_changes") and not parsed["sheets"] and scope != "Нет изменений содержания":
            problems.append(f"{parsed['label']}: the summary says «изменений содержания нет», the report «{item['change_scope']}»")
        if parsed["sheets"] and parsed["items"] and scope == "Нет изменений содержания":
            problems.append(f"{parsed['label']}: the summary has sheets and items, the report says «{item['change_scope']}»")
    return problems


# ------------------------------------------------------------------ the contract of report_v2 (schemas.py:143-241)

def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_ids(ids: Any, where: str, errors: list[str], known: set[str]) -> None:
    if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
        errors.append(f"{where}: a list of fact IDs")
        return
    bad = [x for x in ids if x not in known]
    if bad:
        errors.append(f"{where}: IDs without a passport in the registry: {', '.join(bad[:10])}")


def validate_report(report: Any, lines_total: int | None = None) -> list[str]:
    """The check of ``report_v2``; an empty list is fit. A source is the ID of a fact whose passport is in the registry (schemas.py:156-241)."""
    errors: list[str] = []
    if not isinstance(report, dict):
        return ["the report must be an object"]
    if report.get("schema_version") != "report_v2":
        errors.append("schema_version: report_v2 expected")
    for key in ("project_code", "title", "input_filename"):
        if not isinstance(report.get(key), str) or not report.get(key):
            errors.append(f"{key}: a non-empty string")
    basis = report.get("analysis_basis")
    if not isinstance(basis, dict) or not isinstance(basis.get("source_pdf_checked"), bool) or not isinstance(basis.get("type"), str) or not isinstance(basis.get("description"), str):
        errors.append("analysis_basis: {type, description, source_pdf_checked: bool}")
    for key in ("summary", "limitations"):
        value = report.get(key)
        if not isinstance(value, list) or not all(isinstance(x, str) and x.strip() for x in value):
            errors.append(f"{key}: a list of non-empty strings")
    if not report.get("summary"):
        errors.append("summary: the general conclusion is empty")
    facts = report.get("facts")
    if not isinstance(facts, list):
        errors.append("facts: the registry of sources is a list")
        facts = []
    known: set[str] = set()
    for i, fact in enumerate(facts):
        where = f"facts[{i}]"
        if not isinstance(fact, dict) or not isinstance(fact.get("fact_id"), str):
            errors.append(f"{where}: a passport with fact_id")
            continue
        known.add(fact["fact_id"])
        line = fact.get("md_line")
        if not _is_int(line) or line < 1 or (lines_total and line > lines_total):
            errors.append(f"{where}.md_line: a line of the MD within the file")
        if not isinstance(fact.get("transition"), str) or not fact.get("transition"):
            errors.append(f"{where}.transition: the transition")
        for key in ("pages_a", "pages_b"):
            if not isinstance(fact.get(key), list) or not all(_is_int(x) for x in fact.get(key) or []):
                errors.append(f"{where}.{key}: a list of pages")
    _check_ids(report.get("summary_sources") or [], "summary_sources", errors, known)
    transitions = report.get("transitions")
    if not isinstance(transitions, list) or not transitions:
        errors.append("transitions: a non-empty list")
        transitions = []
    for i, item in enumerate(transitions):
        where = f"transitions[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: an object")
            continue
        for key in ("from_version", "to_version", "main_changes", "construction_impact"):
            if not isinstance(item.get(key), str) or not item.get(key).strip():
                errors.append(f"{where}.{key}: a non-empty string")
        if normalize_scope(item.get("change_scope")) is None:
            errors.append(f"{where}.change_scope: unknown value «{item.get('change_scope')}»")
        if normalize_significance(item.get("significance")) is None:
            errors.append(f"{where}.significance: unknown value «{item.get('significance')}»")
        if not isinstance(item.get("completeness"), dict) or not isinstance(item["completeness"].get("text"), str):
            errors.append(f"{where}.completeness: completeness by the coverage registry")
        for j, change in enumerate(item.get("changes") or []):
            if not all(isinstance(change.get(k), str) for k in ("object", "before", "after")):
                errors.append(f"{where}.changes[{j}]: object, before, after are strings")
            _check_ids(change.get("sources"), f"{where}.changes[{j}].sources", errors, known)
            if not change.get("sources"):
                errors.append(f"{where}.changes[{j}].sources: a change must have a fact")
        _check_ids(item.get("impact_sources") or [], f"{where}.impact_sources", errors, known)
        _check_ids(item.get("sources"), f"{where}.sources", errors, known)
    significant = report.get("significant_changes")
    if not isinstance(significant, list):
        errors.append("significant_changes: a list (may be empty)")
        significant = []
    for i, change in enumerate(significant):
        where = f"significant_changes[{i}]"
        if not isinstance(change, dict):
            errors.append(f"{where}: an object")
            continue
        for key in ("priority", "title", "version_range", "before_after", "consequence"):
            if not isinstance(change.get(key), str) or not change.get(key).strip():
                errors.append(f"{where}.{key}: a non-empty string")
        if not change.get("sources"):
            errors.append(f"{where}.sources: a serious change must have a source")
        _check_ids(change.get("sources") or [], f"{where}.sources", errors, known)
    return errors
