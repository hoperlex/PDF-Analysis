"""The rules of the overview (`CMP-VC-OVERVIEW-01`): the state of each step, the next step, the groups, the counters.

The original is ``backend/app/services/version_comparison/overview.py`` at ``23f379fd`` (``OV``) and the client's grouping
``frontend/static/js/version-comparison-projects.js`` (``PJ``). Each table row below names the original's line it follows.
"""

from __future__ import annotations

import pytest

from auditmanager.comparison.overview import model as m
from auditmanager.comparison.overview import rules
from auditmanager.comparison.overview.model import Step
from auditmanager.comparison.overview.rules import SeriesFacts


def steps(*, upload: str = m.DONE, profile: str = m.DONE, matrix: str = m.DONE, series: str = m.DONE) -> dict[str, Step]:
    return {
        m.STEP_UPLOAD: Step(upload), m.STEP_PROFILE: Step(profile), m.STEP_MATRIX: Step(matrix),
        m.STEP_AI_PAIRS: rules.deferred_step(), m.STEP_SERIES: Step(series),
        m.STEP_AI_CHANGES: rules.deferred_step(), m.STEP_REPORT: rules.deferred_step(),
    }


# -- the live work of a step ------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("states", "expected"),
    [
        ([], None),
        (["succeeded", "failed", "cancelled"], None),
        (["queued"], m.QUEUED),
        (["retry_wait"], m.QUEUED),
        (["running"], m.RUNNING),
        (["leased", "queued"], m.RUNNING),
        (["queued", "failed"], m.QUEUED),
        (["paused"], m.PAUSED),
        (["paused", "queued"], m.QUEUED),
        (["paused", "running"], m.RUNNING),
    ],
)
def test_live_work_says_running_before_queued_before_paused(states: list[str], expected: str | None) -> None:
    assert rules.live_state(states) == expected


# -- step 2, «Разбор версий» (OV:62-76) -------------------------------------------------------------------------------


def test_profile_done_when_every_page_has_a_ready_profile() -> None:
    step = rules.profile_step(version_count=3, pages_total=12, ready=12, failed=0, live=None)
    assert step == Step(m.DONE, {"total": 12, "ready": 12, "failed": 0})


def test_profile_failed_when_a_page_ended_without_a_result_and_nothing_is_going_to_run() -> None:
    step = rules.profile_step(version_count=3, pages_total=12, ready=10, failed=2, live=None)
    assert step.state == m.FAILED and step.counts == {"total": 12, "ready": 10, "failed": 2}


def test_profile_running_wins_over_a_stored_failure_because_a_retry_is_in_progress() -> None:
    assert rules.profile_step(version_count=3, pages_total=12, ready=10, failed=2, live=m.RUNNING).state == m.RUNNING
    assert rules.profile_step(version_count=3, pages_total=12, ready=0, failed=0, live=m.QUEUED).state == m.QUEUED


def test_profile_partial_when_some_pages_are_stored_and_nothing_is_going_to_run() -> None:
    assert rules.profile_step(version_count=3, pages_total=12, ready=5, failed=0, live=None).state == m.PARTIAL


def test_profile_not_started_when_nothing_is_stored() -> None:
    step = rules.profile_step(version_count=3, pages_total=12, ready=0, failed=0, live=None)
    assert step == Step(m.NOT_STARTED, {"total": 12, "ready": 0, "failed": 0})


def test_a_set_without_a_version_has_nothing_to_profile() -> None:
    assert rules.profile_step(version_count=0, pages_total=0, ready=0, failed=0, live=None).state == m.NOT_APPLICABLE


# -- step 3, «Сопоставление листов» (OV:102-112) -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("state", "build_live", "has_build", "unmatched", "expected"),
    [
        ("ready", None, True, 0, m.DONE),  # OV:112 done
        ("ready", None, True, 4, m.ATTENTION),  # OV:112 attention: «не сопост. 4»
        ("stale", None, True, 0, m.STALE),  # OV:110-111 «устарело»
        ("failed", None, False, 0, m.FAILED),
        ("absent", None, False, 0, m.NOT_STARTED),  # OV:107-108 «не собрано»
        ("building", m.RUNNING, True, 0, m.RUNNING),
        ("building", m.QUEUED, False, 0, m.QUEUED),
        ("building", None, False, 0, m.NOT_STARTED),  # only page profiles are going to run: the build waits for them
        ("building", None, True, 0, m.STALE),
    ],
)
def test_matrix_step_follows_the_matrix_read(
    state: str, build_live: str | None, has_build: bool, unmatched: int, expected: str
) -> None:
    step = rules.matrix_step(
        version_count=3, state=state, build_live=build_live, has_build=has_build, rows=30, unmatched=unmatched, manual=2
    )
    assert step.state == expected


def test_matrix_counts_are_rows_unmatched_and_manual_and_exist_with_a_build_only() -> None:
    with_build = rules.matrix_step(version_count=3, state="stale", build_live=None, has_build=True, rows=30, unmatched=4, manual=2)
    assert with_build.counts == {"rows": 30, "unmatched": 4, "manual_edits": 2}
    assert rules.matrix_step(version_count=3, state="absent", build_live=None, has_build=False).counts is None


def test_matrix_needs_two_versions() -> None:
    for count in (0, 1):  # OV:105-106 «na»
        assert rules.matrix_step(version_count=count, state="absent", build_live=None, has_build=False).state == m.NOT_APPLICABLE


@pytest.mark.parametrize(
    ("has_build", "reasons", "live", "failed", "expected"),
    [
        (True, [], False, False, "ready"),
        (True, [], True, True, "ready"),  # a build that matches its inputs is ready whatever the queue holds
        (True, ["order_changed"], True, False, "building"),
        (True, ["profiles_changed"], False, True, "failed"),
        (True, ["profiles_changed"], False, False, "stale"),
        (False, [], False, False, "absent"),
        (False, [], True, False, "building"),
        (False, [], False, True, "failed"),
    ],
)
def test_the_matrix_state_is_the_matrix_reads(
    has_build: bool, reasons: list[str], live: bool, failed: bool, expected: str
) -> None:
    assert rules.matrix_state(has_build=has_build, stale_reasons=reasons, live=live, last_build_failed=failed) == expected


# -- step 5, «Сравнение соседних» (OV:148-189; PJ:68-69) ---------------------------------------------------------------


def facts(state: str, *, total: int = 3, done: int = 0, changes: int = 0, stale: bool = False) -> SeriesFacts:
    return SeriesFacts(state=state, transitions_total=total, transitions_done=done, with_changes=changes, stale=stale)


@pytest.mark.parametrize(
    ("latest", "expected"),
    [
        (facts("queued"), m.QUEUED),
        (facts("running", done=1), m.RUNNING),  # «идёт», transitions_done of transitions_total
        (facts("paused", done=1), m.PAUSED),  # «пауза»
        (facts("completed", done=3, changes=2), m.DONE),  # «готово»
        (facts("completed", done=3, stale=True), m.STALE),  # «по старому порядку» (OV:184-185)
        (facts("failed", done=1), m.FAILED),  # «ошибка»
        (facts("cancelled", done=1), m.INTERRUPTED),  # «прервано» (OV:181-183 cancelled → interrupted)
    ],
)
def test_series_step_maps_the_latest_series(latest: SeriesFacts, expected: str) -> None:
    assert rules.series_step(version_count=4, latest=latest, follow_up_live=False).state == expected


def test_no_series_is_not_started_with_the_expected_transitions() -> None:
    step = rules.series_step(version_count=4, latest=None, follow_up_live=False)
    assert step == Step(m.NOT_STARTED, {"total": 3, "done": 0})  # OV:154-155


def test_a_follow_up_that_waits_makes_the_series_queued_before_it_exists() -> None:
    assert rules.series_step(version_count=4, latest=None, follow_up_live=True).state == m.QUEUED
    # and after a finished series of an earlier order
    assert rules.series_step(version_count=4, latest=facts("completed", done=3), follow_up_live=True).state == m.QUEUED
    # but never over a live one
    assert rules.series_step(version_count=4, latest=facts("running", done=1), follow_up_live=True).state == m.RUNNING


def test_series_counts_carry_the_progress_and_the_changed_transitions_only_when_completed() -> None:
    done = rules.series_step(version_count=4, latest=facts("completed", total=3, done=3, changes=2), follow_up_live=False)
    assert done.counts == {"total": 3, "done": 3, "with_changes": 2}
    running = rules.series_step(version_count=4, latest=facts("running", total=3, done=1, changes=1), follow_up_live=False)
    assert running.counts == {"total": 3, "done": 1}


def test_series_needs_two_versions() -> None:
    assert rules.series_step(version_count=1, latest=None, follow_up_live=False).state == m.NOT_APPLICABLE


def test_an_unknown_series_state_is_refused_not_guessed() -> None:
    with pytest.raises(ValueError):
        rules.series_step(version_count=3, latest=facts("exploded"), follow_up_live=False)


# -- the steps of wave C2 and step 1 ------------------------------------------------------------------------------------


def test_the_steps_of_wave_c2_are_not_applicable() -> None:
    assert rules.deferred_step() == Step(m.NOT_APPLICABLE)


def test_upload_is_done_for_a_set_with_a_version() -> None:
    assert rules.upload_step(version_count=1).state == m.DONE
    assert rules.upload_step(version_count=0).state == m.NOT_STARTED


# -- the next step (OV:297-331) and the group (PJ:319) ------------------------------------------------------------------

#: (name, version count, steps, the step the chip proposes, the group). Each row is a set state the original names.
NEXT_STEP_CASES = [
    ("upload failed", 3, dict(upload=m.FAILED), m.STEP_UPLOAD, m.GROUP_FAILED),  # OV:301-302 tone bad
    ("upload running", 3, dict(upload=m.RUNNING), m.STEP_UPLOAD, m.GROUP_RUNNING),  # OV:303-304
    ("profile failed", 3, dict(profile=m.FAILED, matrix=m.NOT_STARTED, series=m.NOT_STARTED), m.STEP_PROFILE, m.GROUP_FAILED),  # OV:305-306
    ("profile failed with one version", 1, dict(profile=m.FAILED), m.STEP_PROFILE, m.GROUP_FAILED),  # failed before the version count
    ("one version", 1, dict(profile=m.DONE, matrix=m.NOT_APPLICABLE, series=m.NOT_APPLICABLE), None, m.GROUP_READY),  # OV:307-308 muted
    ("profile running", 3, dict(profile=m.RUNNING, matrix=m.NOT_STARTED, series=m.NOT_STARTED), m.STEP_PROFILE, m.GROUP_RUNNING),  # OV:309-310
    ("profile queued", 3, dict(profile=m.QUEUED, matrix=m.NOT_STARTED, series=m.NOT_STARTED), m.STEP_PROFILE, m.GROUP_RUNNING),
    ("nothing prepared", 3, dict(profile=m.NOT_STARTED, matrix=m.NOT_STARTED, series=m.NOT_STARTED), m.STEP_PROFILE, m.GROUP_WAITING),  # OV:311-312 prepare
    ("profiles partial", 3, dict(profile=m.PARTIAL, matrix=m.NOT_STARTED, series=m.NOT_STARTED), m.STEP_PROFILE, m.GROUP_WAITING),
    ("profiles done, no matrix", 3, dict(matrix=m.NOT_STARTED, series=m.NOT_STARTED), m.STEP_MATRIX, m.GROUP_WAITING),  # OV:311-312
    ("matrix stale", 3, dict(matrix=m.STALE, series=m.DONE), m.STEP_MATRIX, m.GROUP_WAITING),  # OV:311-312 beats a finished series
    ("matrix building", 3, dict(matrix=m.RUNNING, series=m.NOT_STARTED), m.STEP_MATRIX, m.GROUP_RUNNING),
    ("matrix failed", 3, dict(matrix=m.FAILED, series=m.NOT_STARTED), m.STEP_MATRIX, m.GROUP_FAILED),
    ("ready to compare", 3, dict(series=m.NOT_STARTED), m.STEP_SERIES, m.GROUP_WAITING),  # OV:323-324 «запустить»
    ("series stale", 3, dict(series=m.STALE), m.STEP_SERIES, m.GROUP_WAITING),  # OV:323-324
    ("series running", 3, dict(series=m.RUNNING), m.STEP_SERIES, m.GROUP_RUNNING),  # OV:317-318
    ("series queued", 3, dict(series=m.QUEUED), m.STEP_SERIES, m.GROUP_RUNNING),
    ("series paused", 3, dict(series=m.PAUSED), m.STEP_SERIES, m.GROUP_WAITING),  # OV:319-320 act, not run
    ("series interrupted", 3, dict(series=m.INTERRUPTED), m.STEP_SERIES, m.GROUP_WAITING),  # OV:321-322 «досчитать»
    ("series failed", 3, dict(series=m.FAILED), m.STEP_SERIES, m.GROUP_WAITING),  # OV:321-322: amber, not red
    ("series done, sheets left unmatched", 3, dict(matrix=m.ATTENTION, series=m.DONE), m.STEP_MATRIX, m.GROUP_WAITING),  # OV:325-326, C1: by hand
    ("series done", 3, dict(series=m.DONE), None, m.GROUP_READY),  # OV:331 «Готово»
    ("unmatched sheets while the series is not done", 3, dict(matrix=m.ATTENTION, series=m.NOT_STARTED), m.STEP_SERIES, m.GROUP_WAITING),  # OV:323 first
]


@pytest.mark.parametrize(("name", "count", "states", "proposed", "group"), NEXT_STEP_CASES, ids=[c[0] for c in NEXT_STEP_CASES])
def test_the_next_step_rule_on_the_set_states_the_original_names(
    name: str, count: int, states: dict[str, str], proposed: str | None, group: str
) -> None:
    built = steps(**states)
    assert rules.next_step(built, count) == proposed, name
    assert rules.group_of(proposed, built) == group, name


def test_every_state_vector_gets_a_step_that_exists_and_exactly_one_group() -> None:
    import itertools

    every = (m.NOT_STARTED, m.QUEUED, m.RUNNING, m.PAUSED, m.INTERRUPTED, m.DONE, m.PARTIAL, m.STALE, m.ATTENTION, m.FAILED)
    for profile, matrix, series in itertools.product(every, every, every):
        for count in (0, 1, 2, 5):
            built = steps(profile=profile, matrix=matrix, series=series)
            proposed = rules.next_step(built, count)
            assert proposed in (None, *m.STEP_ORDER)
            assert rules.group_of(proposed, built) in (m.GROUP_WAITING, m.GROUP_RUNNING, m.GROUP_FAILED, m.GROUP_READY)


def test_a_chip_for_a_step_that_is_not_done_is_never_ready() -> None:
    built = steps(series=m.NOT_STARTED)
    assert rules.group_of(rules.next_step(built, 3), built) != m.GROUP_READY


def test_the_group_of_a_failed_series_is_waiting_because_the_action_is_to_finish_it() -> None:
    built = steps(series=m.FAILED)
    assert rules.group_of(m.STEP_SERIES, built) == m.GROUP_WAITING
    assert rules.group_of(m.STEP_PROFILE, steps(profile=m.FAILED)) == m.GROUP_FAILED


# -- the counters and the totals (PJ:320-328) --------------------------------------------------------------------------


def test_counters_count_exactly_the_rows_given() -> None:
    groups = [m.GROUP_WAITING, m.GROUP_WAITING, m.GROUP_RUNNING, m.GROUP_FAILED, m.GROUP_READY, m.GROUP_READY, m.GROUP_READY]
    assert rules.counters(groups) == {"all": 7, "waiting": 2, "running": 1, "failed": 1, "ready": 3}
    assert rules.counters([]) == {"all": 0, "waiting": 0, "running": 0, "failed": 0, "ready": 0}


def test_the_four_groups_add_up_to_all() -> None:
    groups = [m.GROUP_WAITING, m.GROUP_RUNNING, m.GROUP_RUNNING, m.GROUP_READY]
    c = rules.counters(groups)
    assert c["waiting"] + c["running"] + c["failed"] + c["ready"] == c["all"]


def test_totals_are_versions_and_transitions_between_neighbours() -> None:
    assert rules.totals([3, 1, 0, 5]) == {"versions": 9, "transitions": 2 + 0 + 0 + 4}
    assert rules.totals([]) == {"versions": 0, "transitions": 0}
