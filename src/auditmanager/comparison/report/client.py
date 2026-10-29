"""The client report: one model call per transition over the facts of the summary, a program check that drops every point the facts do not
confirm, one chronological table (`CMP-VC-REPORT-01`, plan 1.1 «Отчёт для заказчика · Изменения проектных решений»).

A port of the original's ``md_report/client_edit.py`` (926 lines) and ``md_report/client.py`` (234 lines) at commit ``23f379fd`` of
``SU10KAZ/PDF-proverka``; the file:line of each rule is in its docstring. The model chooses the main and writes the row of a transition;
every point cites facts, and the values «было → стало» are given apart (``values``) so that the program can check the whole link: a fact of
this transition → the object (its designations are in the fact) → the parameter → was → became (the side and the direction are those of the
fact's fields) → the units. **A point that fails the check is dropped from the report** (``check``: ``dropped``), and the count of what was
dropped is printed in the recall line of the PDF. Nothing the model writes reaches the PDF unless a fact of its own transition confirms it.

What is not ported: the editor's decision layer (``save_edit``, ``client_edit.py:714-750``, reserved in the original), the coverage diagnostic
of the important facts (``coverage``, ``:536-579``; internal, never printed) and the on-disk layout of results (``:609-691``): a result is a row
of ``comparison_report_part``. The prompt text is ``prompts/md_report_client_edit.md``, the original's file unchanged.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Final

__all__ = [
    "FIELD_CHARS",
    "NO_CHANGES",
    "POINTS_MAX",
    "PROMPT_VERSION",
    "SCOPES",
    "SCOPE_NONE",
    "boundary",
    "check",
    "edited_transitions",
    "fill",
    "important",
    "packet",
    "problems_text",
    "prompt_for",
    "prompt_text",
    "row_of",
    "schema",
    "is_unchanged",
]

#: `[own design]` the prompt version of this port; the original's is ``client-edit/3`` (``client_edit.py:23``).
PROMPT_VERSION: Final[str] = "cmp-client/1"
FIELD_CHARS: Final[int] = 110  # client_edit.py:24 -- the value of a field «было/стало» in the packet
TEXT_CHARS: Final[int] = 260  # :25 -- the text of a description without fields
NAME_CHARS: Final[int] = 36  # :26
MEMBER_CHARS: Final[int] = 60  # :27
TITLE_CHARS: Final[int] = 34  # :28
POINTS_MAX: Final[int] = 8  # :29
#: The scale of a transition is assessed by the model in the same call (client_edit.py:30-32).
SCOPES: Final[tuple[str, ...]] = (
    "Локальные изменения", "Существенные изменения", "Широкая переработка", "Только оформление", "Нет изменений содержания",
)
NO_CHANGES: Final[str] = "Технических изменений не выявлено."  # client.py:21
SCOPE_NONE: Final[str] = "Без технических изменений"  # client.py:22
SCOPE_NO_CONTENT: Final[str] = "Нет изменений содержания"
PROMPT_FILE: Final[Path] = Path(__file__).resolve().parent / "prompts" / "md_report_client_edit.md"

_SPEC_HEAD = re.compile(r"^Старая:.*?;\s*новая:.*?(?:\)|—)\.\s+")
_KV = re.compile(r"^(Поз\.|Наименование|Марка|раздел|Количество|Поставщик|Примечание|Тип)\s*:?\s*(.*)$")
_VERSION = re.compile(r"\bV\d{1,2}\b")
_ORDINAL_NUM = re.compile(r"^\d+-?(?:го|й|м|х|ом|ая|ой|ий|ые|ых)$")
_NUM = re.compile(r"\d+(?:[.,]\d+)?")
_DESIGNATION = re.compile(r"(?<![\w])(?=[\w.\-/…–]*\d)(?=[\w.\-/…–]*[A-Za-zА-Яа-яЁё])[\w][\w.\-/…–]*")


def _cut(text: str | None, limit: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def _spec_parts(fact: dict[str, Any]) -> tuple[dict[str, str], list[tuple[str, str, str]]]:
    """A position of the specification: the fields «ключ значение» and the changes «поле: было → стало» (client_edit.py:47-61)."""
    body = _SPEC_HEAD.sub("", fact.get("text") or "").rstrip(".")
    body = re.sub(r"^(Добавлено: не было →|Удалено:)\s*", "", body).replace(" → отсутствует", "")
    fields: dict[str, str] = {}
    changes: list[tuple[str, str, str]] = []
    for part in (x.strip() for x in body.split(";")):
        if "→" in part and ":" in part.split("→")[0]:
            name, rest = part.split(":", 1)
            before, after = rest.split("→", 1)
            changes.append((name.strip(), before.strip(), after.strip()))
            continue
        match = _KV.match(part)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    return fields, changes


def _qty(value: str) -> tuple[float | None, str]:
    match = re.match(r"^\s*(\d+(?:[.,]\d+)?)\s*([^\d\s].*)?$", value or "")
    if not match:
        return None, ""
    return float(match.group(1).replace(",", ".")), (match.group(2) or "").strip(" .")


def _fmt(value: float) -> str:
    return (f"{value:.2f}".rstrip("0").rstrip(".")).replace(".", ",")


def _all_fields(fact: dict[str, Any]) -> list[dict[str, Any]]:
    details = fact.get("details") or {}
    return (details.get("fields") or []) + [y for m in details.get("members") or [] for y in m.get("fields") or []]


def _uncertain_fact(fact: dict[str, Any]) -> bool:
    """A fact one cannot lean on as established: a question, an unverified description of a sheet, an ambiguous match of positions.
    One test for the model's packet («есть неясность») and for the check (client_edit.py:350-354)."""
    return (
        fact["kind"] == "ai_questions" or fact.get("confirmation_code") == "unverified"
        or (fact.get("details") or {}).get("change_kind") == "unresolved"
    )


# ------------------------------------------------------------------ the important facts (the ★ of the packet)

def important(fact: dict[str, Any], profile: dict[str, Any] | None = None) -> str | None:
    """The category of an important fact of a sheet description -- what must not be lost behind calculated numbers. The features are the
    section profile's (``profile["important"]``: req / mark / size / rating); without a profile there are none (client_edit.py:476-502)."""
    features = (profile or {}).get("important") or {}
    if fact["kind"] != "ai_change" or not features:
        return None
    req, mark, size, rating = (features.get(k) for k in ("req", "mark", "size", "rating"))
    details = fact.get("details") or {}
    kind = details.get("change_kind")
    if kind == "документ":
        return None
    if kind in ("требование", "трасса") and req and req.search(fact["text"]):
        return "требование, материал или монтаж"
    for field in _all_fields(fact):
        before, after = field.get("before") or "", field.get("after") or ""
        if _norm(before) == _norm(after):
            continue
        if mark and mark.search(before + after):
            return "оборудование или марка"
        if size and size.search(after) and (size.search(before) or not before):
            return "типоразмер или сечение"
        if rating and rating.search(after) and rating.search(before):
            return "номинал или параметр"
    if kind == "замена" and req and req.search(fact["text"]):
        return "требование, материал или монтаж"
    return None


# ------------------------------------------------------------------ the packet of a transition (client_edit.py:77-179)

def packet(facts: list[dict[str, Any]], label: str, profile: dict[str, Any] | None = None) -> tuple[str, dict[str, list[str]], dict[str, str]]:
    """The facts of a transition as the model reads them, the expansion of the group codes of the specification and the group lines.
    Repeated positions of the specification (one name and mark in different sections) are folded into groups with a code «С001» and the sum of
    the quantity; the program expands the code back to fact IDs. Returns ``(text, {code: [fact ids]}, {code: group line})``."""
    own = [f for f in facts if f["transition"] == label]
    lines: list[str] = []
    sheets = [f for f in own if f["kind"] in ("ai_change", "ai_single")]
    if sheets:
        lines.append("## Описания листов (поля: было → стало)")
    for fact in sheets:
        title = re.split(r"\s+—\s+часть листа", fact.get("sheet_title") or "")[0]
        head = f"{fact['fact_id']} [{fact.get('sheet') or 'лист'} {_cut(title, TITLE_CHARS)}]".replace(" ]", "]")
        if fact["kind"] == "ai_single":
            lines.append(f"{head} лист добавлен/удалён | {_cut(fact['text'], TEXT_CHARS)}")
            continue
        details = fact.get("details") or {}
        star = "★ " if important(fact, profile) else ""
        bits = [f"{star}{head} {details.get('change_kind') or 'изменение'}", f"объект: {_cut(details.get('object'), 80)}"]
        if details.get("place"):
            bits.append(f"место: {_cut(details['place'], 50)}")
        if details.get("mapping") and details["mapping"] != "one_to_one":
            bits.append(f"соответствие объектов: {details['mapping']}")
        if _uncertain_fact(fact):
            bits.append("есть неясность")
        fields = details.get("fields") or []
        for x in fields:
            unit = f" [{x['unit']}]" if x.get("unit") else ""
            flag = " (неясно)" if x.get("certainty") == "unclear" else ""
            bits.append(
                f"{_cut(x.get('name'), 36)}: {_cut(x.get('before') or 'нет', FIELD_CHARS)} → "
                f"{_cut(x.get('after') or 'нет', FIELD_CHARS)}{unit}{flag}"
            )
        if not fields:
            bits.append(_cut(fact["text"], TEXT_CHARS))
        # The members carry the values of single lines or apparatus; a repeat of the fact's fields is not duplicated.
        seen = {(x.get("before"), x.get("after")) for x in fields}
        members = []
        for member in details.get("members") or []:
            values = [
                f"{_cut(x.get('name'), 24)}: {_cut(x.get('before') or 'нет', MEMBER_CHARS)} → "
                f"{_cut(x.get('after') or 'нет', MEMBER_CHARS)}"
                for x in member.get("fields") or [] if (x.get("before"), x.get("after")) not in seen
            ]
            if values:
                members.append(f"{_cut(member.get('object'), 40)} — " + "; ".join(values))
        if members:
            bits.append("состав: " + " / ".join(members))
        lines.append(" | ".join(bits))
    questions = [f for f in own if f["kind"] == "ai_questions"]
    if questions:
        lines.append("\n## Вопросы, не установленные описанием листа (не утверждать как изменение)")
    for fact in questions:
        for q in (fact.get("details") or {}).get("questions") or []:
            lines.append(
                f"{fact['fact_id']} [{fact.get('sheet') or 'лист'}] вопрос: {_cut(q.get('object'), 80)} — {_cut(q.get('question'), 170)}"
            )
    spec = [f for f in own if f["kind"] == "spec_entry"]
    changed = [f for f in spec if (f.get("details") or {}).get("change_kind") == "changed"]
    unresolved = [f for f in spec if (f.get("details") or {}).get("change_kind") == "unresolved"]
    if changed:
        lines.append("\n## Спецификация: изменённые позиции")
    for fact in changed:
        fields, changes = _spec_parts(fact)
        what = " ".join(x for x in (_cut(fields.get("Наименование"), NAME_CHARS), fields.get("Марка", "")) if x)
        section = f" | раздел: {_cut(fields['раздел'], 40)}" if fields.get("раздел") else ""
        lines.append(f"{fact['fact_id']} {what}{section} | " + "; ".join(f"{n}: {_cut(a, 70)} → {_cut(b, 70)}" for n, a, b in changes))
    groups: dict[str, list[str]] = {}
    support: dict[str, str] = {}
    by_key: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for fact in spec:
        kind = (fact.get("details") or {}).get("change_kind")
        if kind in ("added", "removed"):
            fields, _ = _spec_parts(fact)
            by_key[(kind, fields.get("Наименование", ""), fields.get("Марка", ""))].append(fact)
    if by_key:
        lines.append("\n## Спецификация: добавленные и удалённые позиции (сведены по наименованию и марке)")
    for number, ((kind, name, mark), members_) in enumerate(sorted(by_key.items(), key=lambda x: (x[0][0], -len(x[1]), x[0][1])), 1):
        word = "добавлено" if kind == "added" else "исключено"
        what = " ".join(x for x in (_cut(name, NAME_CHARS), mark) if x) or "позиция"
        quantities = [_qty(_spec_parts(f)[0].get("Количество", "")) for f in members_]
        units = {u for v, u in quantities if v is not None}
        total = ""
        if all(v is not None for v, _ in quantities) and len(units) <= 1:
            total = f", всего {_fmt(sum(v for v, _ in quantities))} {next(iter(units), '')}".rstrip()  # type: ignore[misc]
        sections = sorted({_spec_parts(f)[0].get("раздел", "") for f in members_} - {""})
        where = f" | разделы: {_cut('; '.join(sections), 70)}" if sections else ""
        if len(members_) == 1:
            quantity = _spec_parts(members_[0])[0].get("Количество", "")
            line = f"{members_[0]['fact_id']} {word}: {what}{', ' + quantity if quantity else ''}{where}"
        else:
            code = f"С{number:03d}"
            groups[code] = [f["fact_id"] for f in members_]
            line = f"{code} {word} позиций: {len(members_)}: {what}{total}{where}"
            support[code] = line
        lines.append(line)
    moved = [f for f in spec if (f.get("details") or {}).get("change_kind") in ("moved", "section_renamed")]
    if moved:
        lines.append("\n## Спецификация: перенос позиций и переименование групп (без изменения позиции)")
    for fact in moved:
        body = _SPEC_HEAD.sub("", fact["text"])
        body = re.sub(r";\s*(Поз\.|Код|Поставщик)[^;]*", "", body.replace("\\|", "").replace("|", ""))
        lines.append(f"{fact['fact_id']} {_cut(body, 150)}")  # _cut already collapses the white space
    if unresolved:
        lines.append("\n## Спецификация: соответствие позиций неоднозначно (не утверждать замену)")
    for fact in unresolved:
        lines.append(f"{fact['fact_id']} {_cut(_SPEC_HEAD.sub('', fact['text']), 200)}")
    return "\n".join(lines), groups, support


# ------------------------------------------------------------------ the task and the schema (client_edit.py:184-220)

def schema() -> dict[str, Any]:
    text = {"type": "string"}
    ids = {"type": "array", "items": text}
    value = {
        "type": "object", "additionalProperties": False, "required": ["parameter", "before", "after", "fact_id"],
        "properties": {"parameter": text, "before": text, "after": text, "fact_id": text},
    }
    point = {
        "type": "object", "additionalProperties": False, "required": ["object", "text", "fact_ids", "values", "status"],
        "properties": {
            "object": text, "text": text, "fact_ids": ids, "values": {"type": "array", "items": value},
            "status": {"type": "string", "enum": ["confirmed", "needs_clarification"]},
        },
    }
    question = {
        "type": "object", "additionalProperties": False, "required": ["text", "fact_ids"],
        "properties": {"text": text, "fact_ids": ids},
    }
    skipped = {
        "type": "object", "additionalProperties": False, "required": ["fact_id", "reason"],
        "properties": {"fact_id": text, "reason": text},
    }
    return {
        "type": "object", "additionalProperties": False,
        "required": ["transition", "change_scope", "lead", "points", "impact", "impact_fact_ids", "questions", "not_included"],
        "properties": {
            "transition": text, "change_scope": {"type": "string", "enum": list(SCOPES)}, "lead": text,
            "points": {"type": "array", "items": point}, "impact": text, "impact_fact_ids": ids,
            "questions": {"type": "array", "items": question}, "not_included": {"type": "array", "items": skipped},
        },
    }


def prompt_text() -> str:
    return PROMPT_FILE.read_text(encoding="utf-8")


_PLACEHOLDER = re.compile(r"\{\{([A-Z_]+)\}\}")


def fill(template: str, values: dict[str, str]) -> str:
    """One pass of substitution: inserted data is not parsed again (``{{…}}`` in the MD is plain text) -- stages.py:38-43."""
    missing = [m for m in _PLACEHOLDER.findall(template) if m not in values]
    if missing:
        raise ValueError(f"no value for {', '.join(sorted(set(missing)))}")
    return _PLACEHOLDER.sub(lambda m: values[m.group(1)], template)


def boundary(seed: str, body: str) -> tuple[str, str]:
    """The labels of the block of data, chosen so that they are not in the data (the original's ``prompt.boundary``): content between them is
    data, never an instruction. Deterministic in ``seed`` and ``body``."""
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:10].upper()
    counter = 0
    while True:
        begin, end = f"<<<ДАННЫЕ-{digest}-{counter}>>>", f"<<<КОНЕЦ-ДАННЫХ-{digest}-{counter}>>>"
        if begin not in body and end not in body:
            return begin, end
        counter += 1


def prompt_for(transition: dict[str, Any], packet_text: str, template: str, seed: str, profile: dict[str, Any]) -> str:
    """The task of a transition (client_edit.py:210-220); the features of the section come from its profile, and with no profile the text is
    neutral, without the priorities of any section."""
    label = f"{transition['from_version']}→{transition['to_version']}"
    head = f"Раздел: {profile['name']}." if profile.get("name") else ""
    begin, end = boundary(seed, packet_text)
    return fill(template, {
        "TRANSITION": label, "DISCIPLINE": "\n".join(x for x in (head, profile["priorities"]) if x),
        "PREV": transition["from_version"], "FACTS": packet_text, "BEGIN": begin, "END": end,
    })


# ------------------------------------------------------------------ the check of an answer (client_edit.py:232-461)

def _norm(value: str | None) -> str:
    value = (value or "").lower().replace("ё", "е")
    value = re.sub(r"[×xх]", "x", value)
    value = value.replace(",", ".").replace("«", "").replace("»", "").replace('"', "")
    return re.sub(r"\s+", "", value)


def _nums(value: str | None) -> list[str]:
    return [n.replace(",", ".") for n in _NUM.findall(value or "")]


def _fact_sides(fact: dict[str, Any]) -> list[tuple[str, str]]:
    """The pairs (was, became) of a fact for the check of the direction (client_edit.py:243-259)."""
    if fact["kind"] == "ai_change":
        details = fact.get("details") or {}
        pairs = [
            (x.get("before") or "", x.get("after") or "")
            for x in (details.get("fields") or []) + [y for m in details.get("members") or [] for y in m.get("fields") or []]
        ]
        return pairs or [("", fact.get("text") or "")]
    if fact["kind"] == "spec_entry":
        kind = (fact.get("details") or {}).get("change_kind")
        fields, changes = _spec_parts(fact)
        whole = " ".join(f"{k} {v}" for k, v in fields.items())
        if kind == "added":
            return [("", whole)]
        if kind == "removed":
            return [(whole, "")]
        return [(a, b) for _, a, b in changes] + [(whole, whole)]
    return [("", fact.get("text") or "")]


def _fact_text(fact: dict[str, Any]) -> str:
    details = fact.get("details") or {}
    extra = [details.get("object") or "", details.get("place") or ""]
    extra += [f"{x.get('name')} {x.get('before')} {x.get('after')} {x.get('unit')}" for x in details.get("fields") or []]
    extra += [f"{q.get('object')} {q.get('question')}" for q in details.get("questions") or []]
    for member in details.get("members") or []:
        extra.append(f"{member.get('object')} {member.get('place')}")
        extra += [f"{x.get('name')} {x.get('before')} {x.get('after')} {x.get('unit')}" for x in member.get("fields") or []]
    return " ".join([fact.get("text") or "", fact.get("sheet") or "", fact.get("sheet_title") or ""] + extra)


def _side_ok(claim: str, side: str) -> bool:
    if not claim.strip() or _norm(claim) in ("нет", "небыло", "отсутствует", "—", "-"):
        return True
    parts = [x for x in _norm(claim).split("…") if x]  # a value cut in the packet («…») is judged by its parts
    if parts and all(x in _norm(side) for x in parts):
        return True
    numbers = _nums(claim)
    return bool(numbers) and all(n in _nums(side) for n in numbers)


_CUT_WORD = re.compile(r"([\w\-«»\"]{3,})…(?=[\s,.;:)]|$)")


def repair_cut(text: str, source: str) -> tuple[str, bool]:
    """A stub «FIRESTO…» (a value cut in the packet and rewritten by the model): complete it to the whole word of the cited facts. Returns
    (text, whether stubs remain). Ranges «TA1.1…TA1.6» are not touched (client_edit.py:291-304)."""
    left = False

    def fix(match: re.Match[str]) -> str:
        nonlocal left
        fragment = match.group(1)
        full = re.search(r"(?<![\w])" + re.escape(fragment) + r"[\w\-]*", source)
        if full and len(full.group(0)) > len(fragment):
            return full.group(0)
        left = True
        return match.group(0)

    return _CUT_WORD.sub(fix, text), left


_NONE = ("", "нет", "небыло", "отсутствует", "отсутствовал", "—", "-")
_ADDED_WORD = re.compile(r"^(?:добавлен\w*|введен\w*|появил\w*|предусмотрен\w*)\.?$")
_REMOVED_WORD = re.compile(r"^(?:исключен\w*|удален\w*|отменен\w*|нет)\.?$")


def _parts(value: str) -> list[str]:
    """A composite value by parts: «/», «;» and a comma with a space (a decimal comma «2,2» does not divide) -- client_edit.py:312-314."""
    return [x for x in re.split(r"\s*[/;]\s*|,\s+", (value or "").strip()) if x.strip()]


def _value_ok(before: str, after: str, sides: list[tuple[str, str]]) -> bool:
    """A value is confirmed by a pair «was/became» of the fact; a composite one («63 / 20 / 100 → 50 / 63 / 40») pairwise, each part by its own
    pair of the same fact, **with the same direction**. «нет → добавлен» / «X → исключён» when the fact has a side of appearing / disappearing
    (client_edit.py:317-337)."""
    if any(_side_ok(before, a) and _side_ok(after, b) for a, b in sides):
        return True
    nb, na = _norm(before), _norm(after)
    if nb in _NONE and _ADDED_WORD.match(na):
        return any(not a.strip() and b.strip() for a, b in sides)
    if nb not in _NONE and _REMOVED_WORD.match(na):
        return any(_side_ok(before, a) and not b.strip() for a, b in sides)
    parts_before, parts_after = _parts(before), _parts(after)
    if nb in _NONE:
        return len(parts_after) > 1 and all(any(_side_ok(y, b) for a, b in sides if b.strip()) for y in parts_after)
    if na in _NONE:
        return len(parts_before) > 1 and all(any(_side_ok(x, a) for a, b in sides if a.strip()) for x in parts_before)
    if len(parts_before) < 2 or len(parts_before) != len(parts_after):
        return False
    return all(
        any(_side_ok(x, a) and _side_ok(y, b) and (_nums(x) or _nums(y)) for a, b in sides if a.strip() or b.strip())
        for x, y in zip(parts_before, parts_after)
    )


#: Phrases that never reach a client (client_edit.py:340-347).
_FORBIDDEN: Final = [
    (re.compile(r"\b[ФF]\d{4}\b|\bС\d{3}\b"), "служебный ID факта или группы в тексте"),
    (re.compile(r"\bMD\b|сводк|стр\. PDF|реестр|покрытие листов|покрыти[ея] отч", re.I), "служебная подпись процесса"),
    (re.compile(r"(?<=[а-яё»)] )[AB](?=[\s,.;:])"), "обозначение стороны A/B вместо номера выдачи"),
    (re.compile(r"из-за ошибк|ошибк\w* проектировщ|по требованию заказчик|для приведения к норм|по причине", re.I), "причина решения без основания"),
    (re.compile(r"переделк|затрат|стоимост|задержк|штраф|нарушени", re.I), "переделки/затраты/нарушения без основания"),
]


def check(
    answer: dict[str, Any], transition: dict[str, Any], facts: list[dict[str, Any]], groups: dict[str, list[str]],
    support: dict[str, str],
) -> dict[str, Any]:
    """The check of the answer of a transition (client_edit.py:357-461). ``hard``: the answer is unfit (a retry while the limit lasts);
    ``dropped``: points that failed the link check, **not in the report**; ``kept``: the accepted points; ``fixes``: a status the facts
    changed to «уточнить»."""
    label = f"{transition['from_version']}→{transition['to_version']}"
    by_id = {f["fact_id"]: f for f in facts}
    own = {f["fact_id"] for f in facts if f["transition"] == label}
    hard: list[str] = []
    if answer.get("transition") != label:
        hard.append(f"transition «{answer.get('transition')}» instead of «{label}»")
    lead = (answer.get("lead") or "").strip()
    if not lead or len(lead) > 230 or len(re.findall(r"[.!?](?:\s|$)", lead)) > 1:
        hard.append("lead is exactly one sentence of at most 230 characters")
    texts = [lead, answer.get("impact") or ""] + [q.get("text") or "" for q in answer.get("questions") or []]
    texts += [f"{p.get('object')} {p.get('text')}" for p in answer.get("points") or []]
    for pattern, why in _FORBIDDEN:
        for text in texts:
            match = pattern.search(text)
            if match:
                hard.append(f"{why}: «{match.group(0)}» in «{_cut(text, 80)}»")
                break

    def expand(ids: list[str]) -> tuple[list[str], list[str]]:
        out: list[str] = []
        bad: list[str] = []
        for i in ids:
            i = i.strip().strip("[]")
            if i in groups:
                out += groups[i]
            elif i in own:
                out.append(i)
            else:
                bad.append(i)
        return out, bad

    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    fixes: list[str] = []
    points = answer.get("points") or []
    if not points or len(points) > POINTS_MAX:
        hard.append(f"{len(points)} points; from 1 to {POINTS_MAX} are needed")
    for point in points:
        why: list[str] = []
        ids, bad = expand(point.get("fact_ids") or [])
        if bad:
            why.append("ID not from this transition: " + ", ".join(bad[:5]))
        if not ids:
            why.append("no facts")
        cited = [by_id[i] for i in ids if i in by_id]
        haystack = _norm(
            " ".join(_fact_text(f) for f in cited) + " " + " ".join(support[c] for c in (point.get("fact_ids") or []) if c in support)
        )
        tokens = [x for token in _DESIGNATION.findall(point.get("object") or "") for x in re.split(r"[/–…,]+", token)]
        for token in tokens:
            if len(token) >= 3 and re.search(r"\d", token) and not _ORDINAL_NUM.match(token) and _norm(token) not in haystack:
                why.append(f"the designation «{token}» is not in the cited facts")
        for number in _nums(_VERSION.sub(" ", f"{point.get('object')} {point.get('text')}")):
            if number not in _nums(haystack.replace("x", " ")) and number not in haystack:
                why.append(f"the number {number} is not found in the cited facts")
        said = _norm(f"{point.get('text')} " + " ".join(f"{v.get('before')} {v.get('after')}" for v in point.get("values") or []))
        uncertain = any(
            _uncertain_fact(f) or any(
                x.get("certainty") == "unclear"
                and any(len(_norm(y)) >= 3 and _norm(y) in said for y in (x.get("before"), x.get("after")) if y)
                for x in _all_fields(f)
            )
            for f in cited
        )
        for value in point.get("values") or []:
            fid = (value.get("fact_id") or "").strip()
            if fid in groups:
                sides = [("", support[fid])] if "добавлено" in support[fid] else [(support[fid], "")]
            elif fid in own and fid in ids:
                sides = _fact_sides(by_id[fid])
            else:
                why.append(f"the value «{value.get('parameter')}» cites {fid or 'an empty ID'} outside the point or the transition")
                continue
            if not _value_ok(value.get("before") or "", value.get("after") or "", sides):
                why.append(
                    f"«{value.get('parameter')}: {_cut(value.get('before'), 40)} → {_cut(value.get('after'), 40)}» "
                    f"is not confirmed by the fields of {fid} (side or direction)"
                )
        if uncertain and point.get("status") == "confirmed":
            # The status is set by the facts, not by the model: the point is not thrown out, it is marked «уточнить» (client_edit.py:429-433).
            point = dict(point, status="needs_clarification")
            fixes.append(f"«{_cut(point.get('object'), 40)}»: status «уточнить» -- the point rests on an unclear fact")
        source = " ".join(_fact_text(f) for f in cited) + " " + " ".join(
            support[c] for c in point.get("fact_ids") or [] if c in support
        )
        fixed, left = repair_cut(point.get("text") or "", source)
        if left:
            why.append("a cut value «…» is left in the text of the point")
        point = dict(point, text=fixed)
        (dropped if why else kept).append({"point": point, "fact_ids": ids, "problems": why})
    if points and not kept:
        # A retry only when no fit point is left; the points the check drops simply stay out of the report (client_edit.py:441-444).
        hard.append(f"{len(dropped)} of {len(points)} points failed the check")
    impact_ids, bad = expand(answer.get("impact_fact_ids") or [])
    if bad:
        hard.append("impact_fact_ids are not from this transition: " + ", ".join(bad[:5]))
    impact = answer.get("impact") or ""
    sentences = re.split(r"(?<=[.!?])\s+", impact.strip())
    if len(sentences) > 2:
        impact = " ".join(sentences[:2])  # the surplus is cut, not completed; no retry needed
    pool = _norm(" ".join(_fact_text(by_id[i]) for i in impact_ids + [x for k in kept for x in k["fact_ids"]] if i in by_id))
    for number in _nums(_VERSION.sub(" ", impact)):
        if number not in pool:
            hard.append(f"the number {number} of the consequence is not in the facts")
    for question in answer.get("questions") or []:
        _, bad_ids = expand(question.get("fact_ids") or [])
        if bad_ids or not question.get("fact_ids"):
            hard.append(f"the question «{_cut(question.get('text'), 50)}» has no facts of this transition")
    return {"ok": not hard and not dropped, "hard": hard, "kept": kept, "dropped": dropped, "impact": impact, "fixes": fixes}


def problems_text(result: dict[str, Any]) -> list[str]:
    out = list(result["hard"])
    for item in result["dropped"]:
        out.append(f"the point «{_cut(item['point'].get('object'), 50)}»: " + "; ".join(item["problems"]))
    return out


# ------------------------------------------------------------------ the transitions and the view (client.py:122-194)

def is_unchanged(transition: dict[str, Any]) -> bool:
    """A transition the summary itself marks «изменений содержания нет» and has no sheet or item: no call is made for it
    (``edited_transitions``, client_edit.py:762-772, whose test is ``scope == «Нет изменений содержания» and complete``)."""
    return bool(transition.get("explicit_no_content_changes")) and not transition["sheets"] and not transition["items"]


def edited_transitions(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """The transitions that need a selection: all but the confirmed absence of changes."""
    return [t for t in manifest["transitions"] if not is_unchanged(t)]


def _date(iso: str | None) -> str:
    if not iso:
        return ""
    year, month, day = iso.split("-")
    return f"{day}.{month}.{year}"


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\s*\[?\b[ФF]\d{4}\b\]?", "", text or "")).strip()


def row_of(transition: dict[str, Any], stored: dict[str, Any] | None) -> dict[str, Any]:
    """The row of the table for one transition (client.py:137-161): the label and the dates, the scale, the one-sentence lead (bold in the
    PDF), the accepted points «объект — было → стало», the questions and the consequence. ``stored`` is the part's stored result
    (``answer``, ``kept``, ``impact``); without one the transition is the confirmed absence of changes."""
    label = f"{transition['from_version']}→{transition['to_version']}"
    row: dict[str, Any] = {
        "label": label, "from_version": transition["from_version"], "to_version": transition["to_version"],
        "dates": [_date(transition.get("from_date")), _date(transition.get("to_date"))],
        "scale": SCOPE_NONE, "lead": NO_CHANGES, "points": [], "impact": "", "questions": [],
    }
    if stored is None:
        return row
    answer = stored["answer"]
    scope = answer.get("change_scope") or SCOPE_NO_CONTENT
    row["scale"] = SCOPE_NONE if scope == SCOPE_NO_CONTENT else scope
    row["lead"] = _clean(answer["lead"])
    row["points"] = [
        {"object": _clean(k["point"]["object"]), "text": _clean(k["point"]["text"])} for k in stored["kept"]
    ]
    row["questions"] = [_clean(q["text"]) for q in answer.get("questions") or []]
    row["impact"] = _clean(stored.get("impact", answer.get("impact")))
    return row
