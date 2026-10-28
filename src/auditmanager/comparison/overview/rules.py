"""The rules of the overview: the state of each step, the next step, the groups, the counters, the totals.

`CMP-VC-OVERVIEW-01`. Pure functions over plain facts; no database, no clock, no model. The original's rules are in
``backend/app/services/version_comparison/overview.py`` at the pinned commit ``23f379fd`` (``OV`` below) and the client's
grouping in ``frontend/static/js/version-comparison-projects.js`` (``PJ``).

Wave C1 serves four of the seven steps. The three steps of wave C2 (``ai_pairs``, ``ai_changes``, ``report``) are always
``not_applicable`` here, so the original's loop over the later stages (``OV:313-322``) reduces to the series, and the
rule for unmatched sheets (``OV:325-326``), which proposes the model check of doubtful pairs, proposes the matrix
instead: the other half of the original's own sentence, «или вручную».
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from auditmanager.comparison.overview import model as m
from auditmanager.comparison.overview.model import Step

__all__ = [
    "LIVE_WORK_STATES",
    "SERIES_LIVE_STATES",
    "SeriesFacts",
    "counters",
    "deferred_step",
    "group_of",
    "live_state",
    "matrix_state",
    "matrix_step",
    "next_step",
    "profile_step",
    "series_step",
    "totals",
    "upload_step",
]

#: The ``comparison_work`` states in which an item is still going to run (the matrix lane's ``_LIVE_STATES``).
LIVE_WORK_STATES: Final[frozenset[str]] = frozenset({"queued", "leased", "running", "retry_wait", "paused", "spend_unknown"})
#: The series states in which a series is live (at most one per document set, a partial unique index of ``0039``).
SERIES_LIVE_STATES: Final[frozenset[str]] = frozenset({"queued", "running", "paused"})
#: A preparation step that failed is red; a series that failed is amber, because «досчитать» is the action
#: (``OV:301-306`` against ``OV:321-322``: only the upload and the profile give the tone ``bad``).
_RED_WHEN_FAILED: Final[frozenset[str]] = frozenset({m.STEP_UPLOAD, m.STEP_PROFILE, m.STEP_MATRIX})


@dataclass(frozen=True, slots=True)
class SeriesFacts:
    """The latest series of a document set, as the overview needs it (``ComparisonSeries`` of the contract)."""

    state: str
    transitions_total: int
    transitions_done: int
    #: Completed transitions whose sheets differ, need a look or changed in composition (``OV:176``).
    with_changes: int
    #: ``stale_reasons`` is not empty (``OV:184-185``).
    stale: bool


def live_state(work_states: Iterable[str]) -> str | None:
    """What a set of live work items says together: ``running`` if any is leased or running, else ``queued`` if any waits,
    else ``paused``; ``None`` when none is going to run. A terminal item says nothing."""
    live = {s for s in work_states if s in LIVE_WORK_STATES}
    if not live:
        return None
    if live & {"leased", "running"}:
        return m.RUNNING
    if live & {"queued", "retry_wait"}:
        return m.QUEUED
    return m.PAUSED


def deferred_step() -> Step:
    """A step of wave C2 (``ai_pairs``, ``ai_changes``, ``report``): the contract's «not available» word."""
    return Step(m.NOT_APPLICABLE)


def upload_step(*, version_count: int) -> Step:
    """Step 1 «Загрузка». A document set exists because its versions were admitted in one transaction (``CMP-INGEST-01``),
    so the step is ``done`` whenever it has a version; the batches still being uploaded are ``pending_uploads``."""
    return Step(m.DONE) if version_count > 0 else Step(m.NOT_STARTED)


def profile_step(*, version_count: int, pages_total: int, ready: int, failed: int, live: str | None) -> Step:
    """Step 2 «Разбор версий» (``OV:62-76``). The figures are pages, as the matrix's ``progress`` gives them, so the two
    screens quote the same numbers: ``total`` pages of the set, ``ready`` with a ready profile, ``failed`` stored without a
    result. A running item wins over a stored failure (a retry is in progress); a failure wins over ``done``."""
    if version_count == 0:
        return deferred_step()
    counts = {"total": pages_total, "ready": ready, "failed": failed}
    if live is not None:
        return Step(live, counts)
    if failed > 0:
        return Step(m.FAILED, counts)
    if pages_total > 0 and ready == pages_total:
        return Step(m.DONE, counts)
    if ready > 0:
        return Step(m.PARTIAL, counts)
    return Step(m.NOT_STARTED, counts)


def matrix_state(*, has_build: bool, stale_reasons: Sequence[str], live: bool, last_build_failed: bool) -> str:
    """The state of the effective matrix of a document set, as the matrix read gives it (``ComparisonMatrixService._state``):
    ``ready`` when the build matches its inputs, else ``building`` while a build or a page profile is going to run, else
    ``failed`` when the newest build item failed after the build, else ``stale`` (a build exists) or ``absent``."""
    if has_build and not stale_reasons:
        return "ready"
    if live:
        return "building"
    if last_build_failed:
        return "failed"
    return "stale" if has_build else "absent"


def matrix_step(
    *, version_count: int, state: str | None, build_live: str | None, has_build: bool,
    rows: int = 0, unmatched: int = 0, manual: int = 0,
) -> Step:
    """Step 3 «Сопоставление листов» (``OV:102-112``). ``state`` is the matrix read's own (``absent``, ``building``,
    ``stale``, ``failed``, ``ready``); the figures are ``counts.rows``, ``counts.unmatched`` and ``counts.manual`` of the
    effective matrix, given whenever a build exists (a stale build is still shown as built, as in ``OV:104``)."""
    if version_count < 2:
        return deferred_step()
    counts = {"rows": rows, "unmatched": unmatched, "manual_edits": manual} if has_build else None
    if state == "ready":
        return Step(m.ATTENTION if unmatched else m.DONE, counts)
    if state == "failed":
        return Step(m.FAILED, counts)
    if state == "stale":
        return Step(m.STALE, counts)
    if state == "building":
        if build_live is not None:
            return Step(build_live, counts)
        # only page profiles are going to run: the build waits for them
        return Step(m.STALE if has_build else m.NOT_STARTED, counts)
    return Step(m.NOT_STARTED, counts)


def series_step(*, version_count: int, latest: SeriesFacts | None, follow_up_live: bool) -> Step:
    """Step 5 «Сравнение соседних» (``OV:148-189``). ``latest`` is the newest series of the document set (``OV:152-156``);
    ``follow_up_live`` is a ``series_after_preparation`` item of the set that is still going to run (a batch asked for the
    comparison after the preparation): the series is queued although its row does not exist yet."""
    if version_count < 2:
        return deferred_step()
    expected = {"total": version_count - 1, "done": 0}
    live = latest is not None and latest.state in SERIES_LIVE_STATES
    if latest is None:
        return Step(m.QUEUED if follow_up_live else m.NOT_STARTED, expected)
    if follow_up_live and not live:
        return Step(m.QUEUED, expected)
    counts: dict[str, int] = {"total": latest.transitions_total, "done": latest.transitions_done}
    if latest.state == "queued":
        return Step(m.QUEUED, counts)
    if latest.state == "running":
        return Step(m.RUNNING, counts)
    if latest.state == "paused":
        return Step(m.PAUSED, counts)
    if latest.state == "completed":
        counts["with_changes"] = latest.with_changes
        return Step(m.STALE if latest.stale else m.DONE, counts)
    if latest.state == "failed":
        return Step(m.FAILED, counts)
    if latest.state == "cancelled":
        return Step(m.INTERRUPTED, counts)
    raise ValueError(f"unknown series state {latest.state!r}")


def next_step(steps: Mapping[str, Step], version_count: int) -> str | None:
    """The step the chip proposes (``OV:297-331``), or ``None`` when nothing is left to do.

    The order is the original's. Only the steps wave C1 serves can hold a state that decides; the three steps of wave C2
    are ``not_applicable``. ``prepare`` of the original (``OV:311-312``) names the profile when it is not done and the
    matrix otherwise. A failed matrix is a preparation failure (``jobs.matrix`` failed when the profiles did, ``jobs.py``)
    and is proposed right after the profile's. The original's unmatched-sheets rule (``OV:325-326``) proposes the model check
    of the pairs or the matrix by hand; the model check is wave C2, so the matrix is proposed.
    """
    up, pr, mx, se = (steps[k].state for k in (m.STEP_UPLOAD, m.STEP_PROFILE, m.STEP_MATRIX, m.STEP_SERIES))
    if up == m.FAILED or up in m.RUNNING_STATES:  # OV:301-304
        return m.STEP_UPLOAD
    if pr == m.FAILED:  # OV:305-306
        return m.STEP_PROFILE
    if version_count < 2:  # OV:307-308: «Одна версия — сравнивать не с чем»
        return None
    if pr in m.RUNNING_STATES or pr == m.PAUSED:  # OV:309-310
        return m.STEP_PROFILE
    if mx == m.FAILED or mx in m.RUNNING_STATES or mx == m.PAUSED:
        return m.STEP_MATRIX
    if pr in (m.NOT_STARTED, m.PARTIAL):  # OV:311-312
        return m.STEP_PROFILE
    if mx in (m.NOT_STARTED, m.STALE):  # OV:311-312
        return m.STEP_MATRIX
    if se in (m.QUEUED, m.RUNNING, m.PAUSING, m.PAUSED, m.INTERRUPTED, m.FAILED):  # OV:315-322
        return m.STEP_SERIES
    if se in (m.NOT_STARTED, m.STALE):  # OV:323-324
        return m.STEP_SERIES
    if mx == m.ATTENTION:  # OV:325-326
        return m.STEP_MATRIX
    return None  # OV:327-331: «Готово» / «Изменений содержания нет»


def group_of(proposed: str | None, steps: Mapping[str, Step]) -> str:
    """The counter a row falls in (``PJ:319``: ``next.tone`` ``run`` → Идут, ``bad`` → Ошибки, ``ok`` and ``muted`` → Готовы,
    otherwise Ждут действия), derived from the step the chip proposes and that step's state. A client derives the same."""
    if proposed is None:
        return m.GROUP_READY
    state = steps[proposed].state
    if state in m.RUNNING_STATES:
        return m.GROUP_RUNNING
    if state == m.FAILED and proposed in _RED_WHEN_FAILED:
        return m.GROUP_FAILED
    return m.GROUP_WAITING


def counters(groups: Sequence[str]) -> dict[str, int]:
    """«Все / Ждут действия / Идут / Ошибки / Готовы» over exactly the rows given (``PJ:320-324``)."""
    return {
        "all": len(groups),
        "waiting": sum(1 for g in groups if g == m.GROUP_WAITING),
        "running": sum(1 for g in groups if g == m.GROUP_RUNNING),
        "failed": sum(1 for g in groups if g == m.GROUP_FAILED),
        "ready": sum(1 for g in groups if g == m.GROUP_READY),
    }


def totals(version_counts: Sequence[int]) -> dict[str, int]:
    """«N версий · M переходов» (``PJ:325-328``): the versions, and the transitions between neighbours."""
    return {"versions": sum(version_counts), "transitions": sum(max(0, n - 1) for n in version_counts)}
