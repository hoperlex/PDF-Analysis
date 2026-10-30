"""Plain data the report unit tests share: a stored series as the MD summary reads it, built from plain dataclasses (no database).
Loaded by path, as the C2 lanes load their helpers (a test never imports a ``conftest``)."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from auditmanager.comparison.report.summary import (
    AiChange,
    SheetDescription,
    SheetInfo,
    SpecChangeInfo,
    SpecInfo,
    SummaryData,
    TransitionInfo,
    VersionInfo,
)

CODE = "133/23-ГК-ЭМ2"
WHEN = datetime(2026, 10, 29, 5, 0, tzinfo=timezone.utc)


def sheet(number: int, status: str, description: SheetDescription | None = None, **over) -> SheetInfo:
    base = dict(pair_no=number, state="done", status=status, a_page=number, b_page=number, a_sheet=str(number),
                b_sheet=str(number), a_title="План", b_title="План", description=description)
    base.update(over)
    return SheetInfo(**base)


def described() -> SheetDescription:
    return SheetDescription(
        state="done", model="claude-opus-5", unresolved=("Что за щит?",),
        changes=(
            AiChange("c1", "Кабель ВВГнг(А)-LS", kind="замена", was="3×2,5", now="3×4", was_tier="from_text", now_tier="from_image"),
            AiChange("c2", "Автомат QF1", was="16 А", now="25 А", certainty="unclear", now_tier="unverified"),
        ),
    )


def summary_data(*, shuffled: bool = False, recorded: bool = False) -> SummaryData:
    description = described()
    if recorded:
        description = replace(description, recorded=True)
    sheets = (sheet(1, "different", description), sheet(2, "same"), sheet(3, "different"))
    if shuffled:
        sheets = tuple(reversed(sheets))
    first = TransitionInfo(
        1, "completed", VersionInfo(1, "a.pdf"), VersionInfo(2, "b.pdf"),
        {"sheets": 3, "compared": 3, "same": 1, "zones_only": 0, "different": 2, "style_only": 0, "needs_review": 0, "added": 0,
         "removed": 0, "failed": 0, "ai_dependent": 1},
        ("different",), sheets,
    )
    second = TransitionInfo(
        2, "completed", VersionInfo(2, "b.pdf"), VersionInfo(3, "c.pdf"),
        {"sheets": 1, "compared": 1, "same": 1, "zones_only": 0, "different": 0, "style_only": 0, "needs_review": 0, "added": 0,
         "removed": 0, "failed": 0, "ai_dependent": 0},
        ("content_same",), (sheet(1, "same"),),
    )
    return SummaryData(code=CODE, transitions=(first, second), data_at=WHEN)


def spec_data() -> SummaryData:
    base = summary_data()
    spec = SpecInfo(
        state="completed", model="claude-opus-5",
        changes=(
            SpecChangeInfo("s1", "changed", fields=(("quantity", "2", "3"),), old={"name": "Светильник", "mark": "LED-1", "page": {"page_number": 5}},
                           new={"name": "Светильник", "mark": "LED-1", "quantity": "3", "page": {"page_number": 6}}, old_page=5, new_page=6, old_sheet="12", new_sheet="12"),
            SpecChangeInfo("s2", "added", new={"name": "Кабель", "mark": "ВВГ 3х2,5", "quantity": "100 м", "page": {"page_number": 6}}, new_page=6),
        ),
    )
    return SummaryData(code=CODE, transitions=(replace(base.transitions[0], spec=spec), base.transitions[1]), data_at=WHEN)
