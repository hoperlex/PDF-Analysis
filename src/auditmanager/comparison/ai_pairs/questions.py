"""Which cells of the effective matrix are doubtful, and what is asked of each (the original's ``questions``,
``sheet_match.py:124-166``).

A pure function of the effective matrix (:func:`~auditmanager.comparison.matrix.effective.effective_matrix`: the algorithm, then
the accepted AI links, then the manual edits) and of what the stored page profiles say of the pages. For each adjacent pair of
versions (A, B) and each row whose cell in A holds a sheet:

* the cell of B is ``unmatched`` and has candidates -> a ``no_pair`` question over up to four candidates, the ones that are not
  specification sheets (``:151-158``);
* the cell of B is ``matched`` at ``medium`` confidence, was not decided by an expert and is not a bridge across a missing
  version -> a ``medium_pair`` question over the algorithm's page and its neighbours that are not specification sheets
  (``:159-165``).

Not asked (the original's ``continue``): a sheet that an expert placed (``manual``, ``:145``); a specification sheet (it is
compared whole, ``:148-149``); a sheet inside a table group «▤» of the pair of versions, that is decided by the group rule
(``:152-153``); a cell with no candidate left (``:155-156``). A cell the model has already settled (``ai``), an expert's cell and
an absent cell are not doubtful, so they come out of the effective matrix without a question and a rerun asks nothing twice.

A page that has no stored preview cannot be shown to the model: it is not a candidate, and a sheet A without one asks nothing.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, Final

from auditmanager.comparison.ai_pairs.model import (
    KIND_MEDIUM_PAIR,
    KIND_NO_PAIR,
    MAX_CANDIDATES_NO_PAIR,
    PageFacts,
    Question,
    QuestionPage,
)

__all__ = ["askable", "derive_questions", "facts_key", "is_multi_sheet_spec", "is_spec_page", "paired_pages"]

_SPEC_TITLE: Final[re.Pattern[str]] = re.compile(r"^спецификаци[яи]\b", re.IGNORECASE)
_DRAWING_WORDS: Final[re.Pattern[str]] = re.compile(r"\b(план|схема|разрез|узел)\b", re.IGNORECASE)


def facts_key(version_uid: str, page_number: int) -> tuple[str, int]:
    return (version_uid, page_number)


def is_spec_page(facts: PageFacts | None) -> bool:
    """A specification sheet (``_spec_page``, ``sheet_match.py:118-121``): the stamp's designation ends in «.СО», or the title is
    «Спецификация…», unless the title is a plan, scheme, section or detail. The original's kind also reads a column header
    («Поз.», «Наименование», «Кол.») from the words of the top of the sheet; the words are in the page archive and the summary this
    reads carries none, so a specification sheet with neither mark is not recognised here (report, limits)."""
    if facts is None:
        return False
    marked = facts.designation.strip().upper().endswith(".СО") or _SPEC_TITLE.match(facts.title.strip()) is not None
    return marked and _DRAWING_WORDS.search(facts.title) is None


def is_multi_sheet_spec(page: int, version_uid: str, facts: Mapping[tuple[str, int], PageFacts]) -> bool:
    """Sheet ``page`` is a specification sheet and a neighbour is one too (``sheet_match.py:150``): a table that goes on over
    several sheets, which the model answers unstably (``:3-4``), so it is only ever a hint."""
    return is_spec_page(facts.get(facts_key(version_uid, page))) and (
        is_spec_page(facts.get(facts_key(version_uid, page - 1))) or is_spec_page(facts.get(facts_key(version_uid, page + 1)))
    )


def _cells(row: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {cell["version_uid"]: cell for cell in row["cells"]}


def _page(cell: Mapping[str, Any]) -> QuestionPage:
    page = cell["page"]
    return QuestionPage(str(page["version_uid"]), int(page["page_number"]), str(page["page_profile_id"]))


def paired_pages(rows: Sequence[Mapping[str, Any]], version_a: str, version_b: str) -> frozenset[int]:
    """The pages of ``version_b`` that stand in a row with a sheet of ``version_a`` -- paired, by the algorithm, by the model
    or by an expert (the original's ``taken_b``, ``sheet_match.py:135-136``). Not narrowed to a question's candidates: a page an
    expert has paired since is gone from the candidates of the cell, and is still taken."""
    cells = [_cells(row) for row in rows]
    return frozenset(
        int(c[version_b]["page"]["page_number"]) for c in cells
        if c.get(version_b, {}).get("state") == "matched" and c.get(version_a, {}).get("state") == "matched"
    )


def derive_questions(
    *, order: Sequence[str], page_counts: Mapping[str, int], rows: Sequence[Mapping[str, Any]],
    facts: Mapping[tuple[str, int], PageFacts],
) -> list[Question]:
    """The questions of an effective matrix, in the order of the transitions and of the rows."""
    out: list[Question] = []
    for k in range(len(order) - 1):
        ia, ib = order[k], order[k + 1]
        cells = [_cells(row) for row in rows]
        group_a = [
            int(c[ia]["page"]["page_number"]) for c in cells
            if c.get(ia, {}).get("state") == "matched" and c.get(ib, {}).get("state") == "matched"
            and c[ib].get("confidence") == "group"
        ]
        taken_b = paired_pages(rows, ia, ib)
        back = {
            int(c[ib]["page"]["page_number"]): tuple(int(x["page"]["page_number"]) for x in c[ia].get("candidates", ()))
            for c in cells if c.get(ib, {}).get("state") == "matched" and c.get(ia, {}).get("state") == "unmatched"
        }
        for c in cells:
            ca, cb = c.get(ia, {}), c.get(ib, {})
            if ca.get("state") != "matched" or ca.get("confidence") == "manual":
                continue
            a = _page(ca)
            fa = facts.get(facts_key(ia, a.page_number))
            if is_spec_page(fa) or fa is None or fa.preview_blob_id is None:
                continue
            multi = is_multi_sheet_spec(a.page_number, ia, facts)
            if cb.get("state") == "unmatched" and cb.get("candidates"):
                if group_a and min(group_a) <= a.page_number <= max(group_a):
                    continue  # inside a table group: the rule «группа» decides (:152-153)
                numbers = sorted({
                    int(x["page"]["page_number"]) for x in cb["candidates"]
                    if askable(facts.get(facts_key(ib, int(x["page"]["page_number"]))))
                })[:MAX_CANDIDATES_NO_PAIR]
                pages = _pages_of(ib, numbers, facts)
                if not pages:
                    continue
                out.append(Question(
                    kind=KIND_NO_PAIR, a=a, b_version_uid=ib, candidates=pages, multi=multi,
                    taken_b=frozenset(taken_b & set(numbers)),
                    back={n: back.get(n, ()) for n in numbers if back.get(n)},
                ))
            elif cb.get("state") == "matched" and cb.get("confidence") == "medium" and "bridge" not in cb.get("flags", ()):
                b = int(cb["page"]["page_number"])
                if not askable(facts.get(facts_key(ib, b))):
                    continue
                numbers = sorted({b} | {
                    n for n in (b - 1, b + 1)
                    if 1 <= n <= int(page_counts.get(ib, 0)) and askable(facts.get(facts_key(ib, n)))
                })
                out.append(Question(
                    kind=KIND_MEDIUM_PAIR, a=a, b_version_uid=ib, candidates=_pages_of(ib, numbers, facts), algo_b=b,
                    multi=multi,
                ))
    return out


def askable(facts: PageFacts | None) -> bool:
    """A page the model can be shown: it has a stored preview and is not a specification sheet."""
    return facts is not None and facts.preview_blob_id is not None and not is_spec_page(facts)


def _pages_of(version_uid: str, numbers: Sequence[int], facts: Mapping[tuple[str, int], PageFacts]) -> tuple[QuestionPage, ...]:
    return tuple(
        QuestionPage(version_uid, n, facts[facts_key(version_uid, n)].page_profile_id)
        for n in numbers if facts_key(version_uid, n) in facts
    )
