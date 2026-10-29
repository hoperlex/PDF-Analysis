"""The program's check of the model's answer, and the state of a sheet (`CMP-VC-AISHEET-01`; no model).

A port of the original's ``sheet_changes/validate.py`` (`23f379fd`, lines 1-269). The check is of **consistency, not of correctness of
the content**:

* the schema; ``packet_id`` and ``part_id`` (a typo in ``packet_id`` with the right ``part_id`` is a remark, not a refusal --
  ``validate.py:38-40``); the ids of candidates and pictures;
* every value gets a **tier**: ``from_text`` (the value is found in the text of its own side), ``from_image`` (read from the picture
  the model cited), ``unverified`` (neither). A value read from a picture is not refused (``validate.py:6-9``, ``:71-78``). The tier is
  kept for the two sides separately (the contract has ``was_tier`` and ``now_tier``);
* «исправлен текст» only with a checked second representation of the same value of the same object; otherwise the item goes to
  «Требует уточнения» (``validate.py:197-211``);
* a service phrase (a cloud, a mark, the issue date, a signature) is cut out of an item and does not destroy it; an item with nothing left
  goes to «Не включено в сводку» (``validate.py:184-195``); sentences with reasons and with judgements of correctness are cut out
  (``:192-196``);
* completeness: a candidate in no list is «не рассмотрен» and the sheet is «Частично» (``:233-239``).

**What this lane adds to the original's check** (ADR-0025 decision 20, the brief's safety rule): a claim about a place or a number that the
raw evidence does not contain is never a confirmed change. Besides the tiers of the values, the **summary** and the **place** of an item
are read for numbers and designations; one that is in no text of the candidate (A, B, the other sheets the packet named) and in no value
of the item's fields is the issue ``SUMMARY_UNSUPPORTED`` / ``PLACE_UNVERIFIED``, and the item is ``unclear`` with a limitation that
says so. An item is ``confirmed`` only when every value is ``from_text`` or ``from_image``, the model did not call any value unclear, and
the summary and the place hold nothing the evidence lacks.

The boxes of the evidence are the program's, taken from the candidates and the pointers, never from the answer.
"""

from __future__ import annotations

import copy
import difflib
import re
from collections.abc import Mapping, Sequence
from typing import Any, Final

from auditmanager.comparison.ai_sheets import geometry as geo
from auditmanager.comparison.ai_sheets import schema as sc
from auditmanager.comparison.ai_sheets.model import TIER_IMAGE, TIER_TEXT, TIER_UNVERIFIED

__all__ = ["PACKET_ID_MIN_RATIO", "check", "norm", "state_of", "tier_rank", "weakest"]

_HOMO: Final = str.maketrans("ABCEHKMOPTXaceopxyх×–—", "АВСЕНКМОРТХасеорхухх--")  # validate.py:31
SERVICE: Final = re.compile(
    r"(облак|отметк\w* изменени|отметк\w* «?\d{1,2}\.\d|дат\w* выпуск|подпис|\bQR\b|штамп|"
    r"рамк\w* лист|номер\w* изменени|таблиц\w* изменени)", re.IGNORECASE,
)  # validate.py:32-33
REASON: Final = re.compile(
    r"\b(из-за|в связи с|для того|чтобы|правильн\w*|корректн\w*|ошибк\w*|обоснован\w*|"
    r"соответству\w* (?:норм|требован|расч[её]т)\w*)\b", re.IGNORECASE,
)  # validate.py:34-35
_SENTENCE: Final = re.compile(r"(?<=[.!?])\s+(?=[А-ЯЁA-Z«])")  # validate.py:37
#: A model rewrites a 16-character ``packet_id`` with a typo (a dropped or an extra character; on the original's production 0.94-0.97
#: similar). The answer is still to its own packet -- one call per packet; a quite different number is still refused (validate.py:38-40).
PACKET_ID_MIN_RATIO: Final[float] = 0.8
#: A number or a designation in running text: a digit run (with a decimal part) or a designation with a digit.
_TOKEN: Final = re.compile(r"[A-Za-zА-Яа-яЁё]{0,4}[-.]?\d+(?:[.,]\d+)?(?:[-–][A-Za-zА-Яа-яЁё0-9]+)*")
_RANK: Final[Mapping[str, int]] = {TIER_UNVERIFIED: 0, TIER_IMAGE: 1, TIER_TEXT: 2}


def norm(text: Any) -> str:
    """``validate.py:43-45``: the homoglyphs of the two alphabets are one, case and spaces are not significant, ``,`` is ``.``."""
    folded = str(text or "").translate(_HOMO).casefold().replace(",", ".")
    return re.sub(r"\s+", "", folded)


def tier_rank(tier: str) -> int:
    return _RANK[tier]


def weakest(tiers: Sequence[str]) -> str:
    """The weakest of some tiers (``unverified`` < ``from_image`` < ``from_text``); ``from_text`` of none."""
    return min(tiers, key=lambda t: _RANK[t]) if tiers else TIER_TEXT


def _side_texts(packet: Mapping[str, Any], candidate_ids: Sequence[str], side: str) -> str:
    """Everything the packet says on one side about these candidates (``validate.py:48-68``)."""
    by_id = {c["id"]: c for c in packet["candidates"]}
    pointers = packet["pointers"]
    parts: list[str] = []
    key_rows = "rows_a" if side == "A" else "rows_b"
    for cid in candidate_ids:
        candidate = by_id.get(cid)
        if not candidate:
            continue
        parts += [r["text"] for r in candidate.get(key_rows) or []]
        parts += list(candidate.get("labels_a" if side == "A" else "labels_b") or [])
        parts.append(candidate.get("words_a" if side == "A" else "words_b") or "")
        parts.append(candidate.get("header") or "")
        for pid in candidate.get("pointers") or []:
            parts.append(pointers[pid]["before" if side == "A" else "after"])
        for x in packet.get("xrefs") or []:
            if x["side"] == side and cid in x["for"]:
                parts.append(x["text"])
    for extra in packet.get("_extra_texts", {}).get(side, []):
        parts.append(extra)
    return norm(" ".join(parts))


def _tier(value: str, text: str, source: str, has_image: bool) -> str:
    """The tier of one value against the text of its side. An empty value is trivially fine (``validate.py:71-78``)."""
    if not value.strip() or norm(value) in text:
        return TIER_TEXT
    if source in ("image", "text_and_image") and has_image:
        return TIER_IMAGE
    return TIER_UNVERIFIED


def _strip(summary: str, rx: re.Pattern[str]) -> tuple[str, list[str]]:
    """Cut the sentences that match ``rx`` out of ``summary`` (``validate.py:81-86``)."""
    sentences = [s for s in _SENTENCE.split(summary.strip()) if s.strip()]
    keep, cut = [], []
    for sentence in sentences:
        (cut if rx.search(sentence) else keep).append(sentence)
    return " ".join(keep).strip(), cut


def _evidence(packet: Mapping[str, Any], candidate_ids: Sequence[str], values: Mapping[str, set[str]]) -> list[dict[str, Any]]:
    """The boxes on the pages of A and B: the rows and pointers where the values of the item occur; otherwise the whole place
    (``validate.py:89-127``). Boxes are in the system of A (the canvas); a box of a row of B is carried over by the engine's matrix."""
    by_id = {c["id"]: c for c in packet["candidates"]}
    pointers = packet["pointers"]
    matrix = packet.get("transform") or geo.IDENTITY
    out: list[dict[str, Any]] = []

    def add(side: str, box: Sequence[float] | None, what: str, cid: str, *, system: str = "") -> None:
        if not box:
            return
        in_a = list(box) if (side == "A" or system == "A") else geo.b_page_to_a(matrix, box)
        out.append({"side": side, "box": geo.rounded(in_a), "what": what, "candidate": cid})

    for cid in candidate_ids:
        candidate = by_id.get(cid)
        if not candidate:
            continue
        found = False
        if candidate["kind"] == "table":
            for side, key in (("A", "rows_a"), ("B", "rows_b")):
                rows = candidate.get(key) or []
                # first the rows by designation; by the value only when there is no designation (the same size belongs to different products)
                hit = [r for r in rows if r.get("key") and norm(r["key"]) in values["keys"]]
                if not hit and not values["keys"] & {norm(r.get("key") or "") for r in candidate.get("rows_a", []) + candidate.get("rows_b", [])}:
                    hit = [r for r in rows if any(v and v in norm(r["text"]) for v in values[side])]
                for row in hit:
                    add(side, row["box"], f"строка таблицы «{row.get('key') or '—'}»", cid)
                    found = True
        else:
            for pid in candidate.get("pointers") or []:
                pointer = pointers[pid]
                hit_a = pointer["before"] and any(v and v in norm(pointer["before"]) for v in values["A"])
                hit_b = pointer["after"] and any(v and v in norm(pointer["after"]) for v in values["B"])
                if hit_a and pointer.get("bbox_a"):
                    add("A", pointer["bbox_a"], f"надпись «{pointer['before'][:40]}»", cid, system="A")
                    found = True
                if hit_b and pointer.get("bbox_b"):
                    add("B", pointer["bbox_b"], f"надпись «{pointer['after'][:40]}»", cid)
                    found = True
        if not found and candidate.get("area"):
            add("A", candidate["area"], "место кандидата", cid, system="A")
    for number, entry in enumerate(out, 1):
        entry["id"] = f"E{number}"
    return out


def _unsupported_tokens(text: str, evidence_text: str) -> list[str]:
    """The numbers and designations of ``text`` that occur in no evidence (``norm``-ed, as the values are)."""
    missing: list[str] = []
    for match in _TOKEN.finditer(text or ""):
        token = match.group(0).strip(" -.,;")
        if not re.search(r"\d", token):
            continue
        if norm(token) not in evidence_text and token not in missing:
            missing.append(token)
    return missing


def check(packet: Mapping[str, Any], answer: Any) -> dict[str, Any]:
    """Check the answer. Returns ``{ok, changes, unresolved, excluded, issues, coverage, context_requests}``; the answer itself is not
    changed (it is kept byte for byte, for the record and the cache)."""
    issues: list[dict[str, Any]] = []

    def issue(code: str, text: str, ref: str = "") -> None:
        issues.append({"code": code, "text": text, "ref": ref})

    answer = copy.deepcopy(answer)
    errors = sc.validate_answer(answer, sc.SHEET_CHANGES_SCHEMA)
    if errors:
        issue("SCHEMA", "; ".join(errors[:5]))
        return {"ok": False, "schema_errors": errors[:10], "issues": issues}
    own = str(packet["packet_id"])
    typo = answer["packet_id"] != own and difflib.SequenceMatcher(None, answer["packet_id"], own).ratio() >= PACKET_ID_MIN_RATIO
    if (answer["packet_id"] != own and not typo) or answer["part_id"] != packet["part_id"]:
        issue("MIXED_INPUT", f"{answer['packet_id']}/{answer['part_id']}")
        return {"ok": False, "issues": issues}
    if typo:
        issue("PACKET_ID_TYPO", f"{answer['packet_id']} -> {own}")
    candidates = {c["id"] for c in packet["candidates"]}
    image_ids = {i["id"] for i in packet["images"]} | set(packet.get("_extra_images") or [])
    image_candidates = {i["id"]: set(i["candidates"]) for i in packet["images"]}

    def clean_ids(ids: list[str], ref: str) -> list[str]:
        bad = [i for i in ids if i not in candidates]
        if bad:
            issue("UNKNOWN_CANDIDATE", ", ".join(bad), ref)
        return [i for i in ids if i in candidates]

    def clean_images(ids: list[str], ref: str) -> list[str]:
        bad = [i for i in ids if i not in image_ids]
        if bad:
            issue("UNKNOWN_IMAGE", ", ".join(bad), ref)
        return [i for i in ids if i in image_ids]

    changes: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for number, raw in enumerate(answer["changes"], 1):
        ref = f"CH{number}"
        change = dict(raw)
        change["candidate_ids"] = clean_ids(change["candidate_ids"], ref)
        change["image_ids"] = clean_images(change["image_ids"], ref)
        change["flags"] = []
        if not change["candidate_ids"]:
            issue("NO_CANDIDATE", "пункт без действительных кандидатов", ref)
            change["flags"].append("no_candidate")
        text_a = _side_texts(packet, change["candidate_ids"], "A")
        text_b = _side_texts(packet, change["candidate_ids"], "B")
        has_image = bool(change["image_ids"])
        all_fields = list(change["fields"]) + [f for m in change["members"] for f in m["fields"]]
        for f in all_fields:
            f["was_tier"] = _tier(f["before"], text_a, f["source"], has_image)
            f["now_tier"] = _tier(f["after"], text_b, f["source"], has_image)
            f["confirmation"] = weakest([f["was_tier"], f["now_tier"]])
            if f["confirmation"] == TIER_UNVERIFIED:
                issue("VALUE_UNVERIFIED", f"{f['name']}: «{f['before']}» → «{f['after']}» — нет ни в тексте своей стороны, "
                      "ни на указанном изображении", ref)
        # A service part and the reasons: cut the sentences, not the whole item.
        summary, cut = _strip(change["summary"], SERVICE)
        if cut:
            issue("SERVICE_PART_REMOVED", " | ".join(cut), ref)
        if not summary:
            excluded.append({
                "candidate_ids": change["candidate_ids"], "reason": "revision_mark",
                "note": "пункт состоял только из служебной части: " + change["summary"][:200], "source": "program",
            })
            continue
        reduced, cut_reasons = _strip(summary, REASON)
        if cut_reasons and reduced:
            issue("REASON_REMOVED", " | ".join(cut_reasons), ref)
            summary = reduced
        change["summary"] = summary
        # «Исправлен текст» only with a checked second representation of the same object.
        if change["kind"] == "text_correction":
            other = change["other_representation"]
            afters = {norm(f["after"]) for f in change["fields"] if f["after"].strip()}
            ok = bool(
                other["what"].strip() and other["value_a"].strip() and norm(other["value_a"]) == norm(other["value_b"])
                and norm(other["value_a"]) in afters and other["image_id"] in change["image_ids"]
                and (not image_candidates.get(other["image_id"]) or image_candidates[other["image_id"]] & set(change["candidate_ids"]))
            )
            if not ok:
                issue("TEXT_CORRECTION_UNCHECKED", "«исправлен текст» без проверки того же значения в другом представлении", ref)
                unresolved.append({
                    "object": change["object"], "place": change["place"],
                    "question": f"{summary} Исправлен ли только текст или изменено значение — по другому представлению объекта не подтверждено.",
                    "candidate_ids": change["candidate_ids"], "image_ids": change["image_ids"], "source": "program",
                })
                continue
        values = {
            "A": {norm(f["before"]) for f in all_fields if f["before"].strip()},
            "B": {norm(f["after"]) for f in all_fields if f["after"].strip()},
            "keys": {norm(f[k]) for f in all_fields for k in ("before", "after") if f[k].strip()},
        }
        change["evidence"] = _evidence(packet, change["candidate_ids"], values)
        change["kind_label"] = sc.KIND_LABELS.get(change["kind"], change["kind"])
        # The summary and the place must hold nothing the evidence lacks. The evidence of an item is the texts of its candidates on
        # both sides, the other sheets the packet named, and the values of its own fields (the model may name a value by itself).
        evidence_text = text_a + text_b + "".join(sorted(values["A"] | values["B"]))
        if has_image:
            # What was read from a picture the model cited is not in the text: the values it named are the evidence of that reading.
            evidence_text += "".join(norm(f[k]) for f in all_fields for k in ("before", "after"))
        wrong_summary = _unsupported_tokens(summary, evidence_text)
        wrong_place = _unsupported_tokens(change["place"], evidence_text + _anchor_text(packet, change["candidate_ids"]))
        if wrong_summary:
            issue("SUMMARY_UNSUPPORTED", ", ".join(wrong_summary), ref)
        if wrong_place:
            issue("PLACE_UNVERIFIED", ", ".join(wrong_place), ref)
        change["tier_was"] = weakest([f["was_tier"] for f in all_fields])
        change["tier_now"] = weakest([f["now_tier"] for f in all_fields])
        change["confirmation"] = weakest([change["tier_was"], change["tier_now"]])
        change["unsupported"] = {"summary": wrong_summary, "place": wrong_place}
        change["unclear"] = bool(
            any(f["certainty"] == "unclear" for f in all_fields) or change["limitation"].strip() or wrong_summary or wrong_place
            or change["confirmation"] == TIER_UNVERIFIED or "no_candidate" in change["flags"]
        )
        changes.append(change)
    for raw in answer["unresolved"]:
        unresolved.append(dict(
            raw, candidate_ids=clean_ids(raw["candidate_ids"], "unresolved"), image_ids=clean_images(raw["image_ids"], "unresolved"),
            source="model",
        ))
    for raw in answer["excluded"]:
        excluded.append(dict(raw, candidate_ids=clean_ids(raw["candidate_ids"], "excluded"), source="model"))
    for number, change in enumerate(changes, 1):
        change["id"] = f"CH{number}"
    for number, item in enumerate(unresolved, 1):
        item["id"] = f"U{number}"
        item["evidence"] = _evidence(packet, item["candidate_ids"], {"A": set(), "B": set(), "keys": set()})
    covered = {i for x in changes + unresolved + excluded for i in x["candidate_ids"]}
    not_reviewed = sorted(candidates - covered, key=lambda v: int(v[1:]))
    if not_reviewed:
        issue("NOT_REVIEWED", ", ".join(not_reviewed))
    coverage = {
        "candidates": len(candidates), "in_changes": len({i for c in changes for i in c["candidate_ids"]}),
        "in_unresolved": len({i for u in unresolved for i in u["candidate_ids"]}),
        "excluded": len({i for e in excluded for i in e["candidate_ids"]}), "not_reviewed": not_reviewed,
    }
    return {
        "ok": True, "changes": changes, "unresolved": unresolved, "excluded": excluded, "issues": issues, "coverage": coverage,
        "context_requests": answer["context_requests"],
    }


def _anchor_text(packet: Mapping[str, Any], candidate_ids: Sequence[str]) -> str:
    """The designations near the places and the titles of the tables: a place such as «у Лк-1» is named by them."""
    by_id = {c["id"]: c for c in packet["candidates"]}
    parts: list[str] = []
    for cid in candidate_ids:
        candidate = by_id.get(cid) or {}
        parts += list(candidate.get("anchors") or [])
        parts.append(candidate.get("title") or "")
        parts.append(candidate.get("view") or "")
    return norm(" ".join(parts))


def state_of(checked: Mapping[str, Any], packet: Mapping[str, Any]) -> str:
    """``validate.py:244-254``."""
    if not checked.get("ok"):
        return "failed"
    if checked["coverage"]["not_reviewed"]:
        return "partial"
    if checked["unresolved"]:
        return "needs_clarification"
    if not checked["changes"]:
        notes = packet["engine"].get("notes") or []
        return "partial" if notes else "no_construction_changes"
    return "done"
