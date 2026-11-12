"""Plan literal norm searches without interpreting applicability or changing evidence.

An absent model query is not proof that a normative question is absent. Explicit
standard references remain searchable with their original number and edition. An
explicit normative statement without a designation supplies an exact passage for
search; retrieval, applicability and editorial validity remain separate questions.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import re


_FAMILY = (r"(?:ГОСТ(?:[ \t]+(?:Р|РК|ISO|IEC|ИСО|МЭК)){0,3}"
           r"|(?:СНиП|СН|СП)(?:[ \t]+(?:РК|РФ))?"
           r"|(?:ISO|IEC|ИСО|МЭК)(?:[ \t]*/[ \t]*(?:ISO|IEC|ИСО|МЭК))?)")
_DESIGNATION = re.compile(
    rf"(?<![\w]){_FAMILY}[\s_]*[0-9]+(?:[.:\-/\u2010-\u2015][0-9]+)*"
    r"(?![\w/\-:\u2010-\u2015]|\.[0-9])",
    re.IGNORECASE,
)
# This is deliberately conservative: an explicit, unsearchable reference must not
# become 'not applicable'. General 'требует сверки' wording is not a norm claim.
_NORMATIVE_STATEMENT = re.compile(
    r"(?<![\w])(?:ГОСТ|СНиП|СН|СП|ISO|IEC|ИСО|МЭК)(?![\w])"
    r"|(?<![\w])(?:норматив[а-яё]*|стандарт[а-яё]*|регламент[а-яё]*"
    r"|норм(?:а|ы|е|у|ой|ам|ами|ах)|требовани[а-яё]*)(?![\w])",
    re.IGNORECASE,
)
_PROVENANCE_FIELDS = (
    "query", "source_kind", "field", "literal", "character_start", "character_end", "source_id",
)


def _texts(observation: Mapping[str, Any]):
    for field in ("title", "description"):
        value = observation.get(field)
        if isinstance(value, str):
            yield value, {"source_kind": "observation", "field": field}
    evidence = observation.get("source_evidence", [])
    if isinstance(evidence, list):
        for index, item in enumerate(evidence):
            if not isinstance(item, Mapping):
                continue
            quote = item.get("quote")
            if isinstance(quote, str):
                origin = {"source_kind": "source_evidence", "field": f"source_evidence[{index}].quote"}
                if isinstance(item.get("source_id"), str):
                    origin["source_id"] = item["source_id"]
                yield quote, origin


def serialise_norm_query_provenance(plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Copy only the helper's JSON-safe provenance fields into a durable receipt."""
    return [{key: row[key] for key in _PROVENANCE_FIELDS if key in row}
            for row in plan.get("provenance", [])]


def _literal_excerpt(text: str, start: int, end: int) -> tuple[str, int, int] | None:
    """Keep one exact searchable passage without cutting a word, number or edition."""
    left = max(0, start - 60)
    right = min(len(text), left + 160)
    if left:
        while left < start and not text[left - 1].isspace():
            left += 1
    if right < len(text):
        while right > end and not text[right].isspace():
            right -= 1
    while left < right and text[left].isspace():
        left += 1
    while right > left and text[right - 1].isspace():
        right -= 1
    if (left > start or right < end or right <= left or right - left > 160
            or (left and not text[left - 1].isspace())
            or (right < len(text) and not text[right].isspace())):
        return None
    return text[left:right], left, right


def plan_norm_queries(observation: Mapping[str, Any]) -> dict[str, Any]:
    """Return queries, decision, and literal origins; never assert norm verification.

    ``status`` is ``proposed`` for unchanged model queries, ``derived`` for literal
    designations or exact normative passages, ``requires_query`` for an explicit
    normative statement that cannot yield a bounded literal query,
    or ``not_applicable`` when neither a query nor a normative statement is present.
    The caller performs retrieval and retains its actual success/failure receipts.
    """
    proposed = observation.get("norm_queries", [])
    if (not isinstance(proposed, list)
            or any(not isinstance(query, str) or not query.strip() for query in proposed)):
        raise ValueError("norm_queries_invalid")
    if proposed:
        return {"queries": list(proposed), "status": "proposed", "reason": "model_proposed",
                "normative_question": True, "provenance": [
                    {"query": query, "source_kind": "model_proposed", "field": f"norm_queries[{index}]",
                     "literal": query, "character_start": 0, "character_end": len(query)}
                    for index, query in enumerate(proposed)]}

    queries: list[str] = []
    provenance: list[dict[str, Any]] = []
    explicit_statement = False
    excerpts = []
    for text, origin in _texts(observation):
        statement = _NORMATIVE_STATEMENT.search(text)
        explicit_statement = explicit_statement or statement is not None
        if statement is not None:
            excerpt = _literal_excerpt(text, statement.start(), statement.end())
            if excerpt is not None:
                query, start, end = excerpt
                if not any(row["query"] == query for row in excerpts):
                    excerpts.append({"query": query, **origin, "literal": query,
                        "character_start": start, "character_end": end})
        for match in _DESIGNATION.finditer(text):
            literal = match.group(0)
            if literal not in queries:
                queries.append(literal)
            provenance.append({"query": literal, **origin, "literal": literal,
                               "character_start": match.start(), "character_end": match.end()})
    if queries:
        return {"queries": queries, "status": "derived", "reason": "literal_standard_reference",
                "normative_question": True, "provenance": provenance}
    if excerpts:
        selected = excerpts
        return {"queries": [row["query"] for row in selected], "status": "derived",
                "reason": "literal_normative_claim", "normative_question": True, "provenance": selected}
    if explicit_statement:
        return {"queries": [], "status": "requires_query", "reason": "explicit_normative_claim_without_query",
                "normative_question": True, "provenance": []}
    return {"queries": [], "status": "not_applicable", "reason": "no_normative_question",
            "normative_question": False, "provenance": []}
