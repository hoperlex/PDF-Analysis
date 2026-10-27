"""Probe 3 -- the analysis input budget, as an operator configures it (`W55B-QA-01`).

The served application derives its budget at start-up from the configured model and
``AUDITMANAGER_RUN_COST_CEILING_USD`` (BUDGET); the unit is the pypdfium2 character count
INGEST stored at upload. Here a real process is started at each ceiling, a real bundle is
uploaded and counted, and ``startRun`` / ``reauditRun`` are asked over HTTP -- so the
boundary is the one a client meets, with the figures the wire carries.

The ceilings are chosen with ``analysis.public.input_budget_characters`` (the product's own
arithmetic) only to *pick* a configuration; what is asserted is what the separately started
process answers.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from w55b_qa_support import (
    call,
    classify,
    committed,
    create_project,
    member_by_suffix,
    new_key,
    pdfium_page_characters,
    scalar,
    start_run,
    text_rich_bundle,
    upload,
    wait_terminal,
    zip_members,
)

#: The model ``bootstrap/settings.load`` takes when ``AUDITMANAGER_MODEL_ID`` is unset.
DEFAULT_MODEL = "claude-opus-5"
#: The 30-page AR document set's count the start-up refusal is held to (`W55B-BUDGET-01` 3.4).
REFERENCE_CHARACTERS = 93_690
LOW_CEILING = "0.80"


def _budget(ceiling: str) -> int:
    from auditmanager.analysis.public import input_budget_characters

    return input_budget_characters(DEFAULT_MODEL, float(ceiling))


def _ceiling_for(budget: int) -> str:
    """A decimal ceiling at which the derived budget is exactly ``budget``."""
    low, high = Decimal("0.40"), Decimal("5.00")
    for _ in range(200):
        middle = (low + high) / 2
        figure = _budget(str(middle))
        if figure == budget:
            return str(middle)
        if figure < budget:
            low = middle
        else:
            high = middle
    raise AssertionError(f"no ceiling gives a budget of {budget}")


@pytest.fixture(scope="module")
def world(api_control, accounts) -> dict:
    """At the default ceiling ($1.00): a text-rich bundle between the low and the default
    budget, uploaded, and one run of it that reached a terminal state (the re-audit source);
    and the AR baseline, uploaded and run. Each version is classified (stage ``P``, section
    ``AR``) before its first run: an unclassified one is refused before the budget is
    consulted (`W59-SECTION-SEAL-01`)."""
    api_control.ensure(None)
    token = accounts.credential("budget-expert")
    project = create_project(token, "QA P3 budget")
    rich = text_rich_bundle(40)
    count = sum(pdfium_page_characters(member_by_suffix(zip_members(rich), ".pdf")))
    assert _budget(LOW_CEILING) < count < _budget("1.00"), count
    rich_version = upload(project, rich, token)
    assert rich_version.status == 201, rich_version
    classify(rich_version.json(), token)
    rich_run = start_run(rich_version.json()["version_uid"], token)
    assert rich_run.status == 202, rich_run
    rich_source = wait_terminal(rich_run.json()["run_id"], token)
    small_version = upload(project, committed("ar_baseline.zip"), token)
    assert small_version.status == 201, small_version
    classify(small_version.json(), token)
    small_run = start_run(small_version.json()["version_uid"], token)
    assert small_run.status == 202, small_run
    small_source = wait_terminal(small_run.json()["run_id"], token)
    return {
        "token": token,
        "count": count,
        "rich": rich_version.json()["version_uid"],
        "rich_source": rich_source["run_id"],
        "small": small_version.json()["version_uid"],
        "small_source": small_source["run_id"],
    }


def _runs_of(version_uid: str, token: str) -> list[str]:
    answer = call("GET", f"/versions/{version_uid}/runs?limit=100", token=token)
    assert answer.status == 200, answer
    return [r["run_id"] for r in answer.json()["items"]]


def test_the_stored_count_is_the_unit_the_budget_compares(world, engine) -> None:
    """Expected: the version's ``text_character_count`` is the independent pypdfium2 count of
    the uploaded PDF -- the same figure the refusals below must carry."""
    stored = scalar(
        engine, "SELECT text_character_count FROM document_version WHERE version_uid = :v", v=world["rich"]
    )
    assert stored == world["count"]


def test_at_a_low_ceiling_a_start_and_a_reaudit_over_one_call_are_accepted_as_windowed_runs(
    world, api_control
) -> None:
    """Expected at ``AUDITMANAGER_RUN_COST_CEILING_USD=0.80`` (after `SECTION-CHUNKED-ANALYSIS-01`):
    the budget derived at start-up (96 361 for the default model) is the budget of ONE model call,
    and a section run above it is analysed in whole-page windows. So ``startRun`` on the text-rich
    version (count above one call, far below ``budget x MAX_ANALYSIS_WINDOWS``) is ``202``, so is
    ``reauditRun`` of the run that version had at $1.00, and each creates its run. The refusal with
    both figures now needs a count above ``budget x MAX_ANALYSIS_WINDOWS`` (1.12 million characters
    at the lowest ceiling the application starts with, which this probe's 40-page bundle is not): it is
    pinned at that limit by ``tests/integration/runs/test_input_budget_over_http.py`` (start, re-audit,
    both figures, no run, no command record, the same key fresh after the ceiling is raised). What
    state a windowed run reaches under the served child's recorded provider is not asserted here."""
    api_control.ensure(LOW_CEILING)
    token, budget = world["token"], _budget(LOW_CEILING)
    assert budget == 96_361 and world["count"] > budget
    runs_before = _runs_of(world["rich"], token)

    started = start_run(world["rich"], token, key=new_key("budget-start"))
    assert started.status == 202, started
    reaudit = call("POST", f"/runs/{world['rich_source']}/reaudit", token=token, key=new_key("budget-reaudit"))
    assert reaudit.status == 202, reaudit
    created = set(_runs_of(world["rich"], token)) - set(runs_before)
    assert {started.json()["run_id"], reaudit.json()["run_id"]} <= created
    for run in (started, reaudit):
        wait_terminal(run.json()["run_id"], token)
    api_control.ensure(None)


def test_at_a_low_ceiling_a_document_under_the_budget_starts_and_reaudits(world, api_control) -> None:
    """Expected at ``0.80``: the AR baseline (3 810 characters) starts (``202``) and its earlier
    run re-audits (``202``); both runs reach ``published``."""
    api_control.ensure(LOW_CEILING)
    token = world["token"]
    started = start_run(world["small"], token)
    assert started.status == 202, started
    reaudit = call("POST", f"/runs/{world['small_source']}/reaudit", token=token, key=new_key("budget-small"))
    assert reaudit.status == 202, reaudit
    assert wait_terminal(started.json()["run_id"], token)["state"] == "published"
    assert wait_terminal(reaudit.json()["run_id"], token)["state"] == "published"


def test_a_document_at_the_budget_and_one_character_over_it_both_start(world, api_control) -> None:
    """Expected: at a ceiling whose derived one-call budget equals the version's count, ``startRun``
    is ``202`` (at the budget is one call); at a ceiling whose budget is one character less the version
    is above one call and is accepted as a windowed run, ``202`` too (before
    `SECTION-CHUNKED-ANALYSIS-01` it was ``422`` with ``budget_characters`` = count - 1; the refusal
    is now at ``budget x MAX_ANALYSIS_WINDOWS``, see the unit-level HTTP test)."""
    token, count = world["token"], world["count"]
    api_control.ensure(_ceiling_for(count - 1))
    over = start_run(world["rich"], token)
    assert over.status == 202, over
    wait_terminal(over.json()["run_id"], token)
    api_control.ensure(_ceiling_for(count))
    accepted = start_run(world["rich"], token)
    assert accepted.status == 202, accepted
    wait_terminal(accepted.json()["run_id"], token)


def test_the_application_refuses_to_start_at_a_ceiling_whose_budget_cannot_hold_the_ar_set(api_control) -> None:
    """Expected: ``serve.py`` with ``AUDITMANAGER_RUN_COST_CEILING_USD=0.78`` (budget 90 761 <
    93 690) exits non-zero on its own without binding a port, saying it refuses to start and
    naming the ceiling, the budget and the AR set's count; at ``0.80`` it starts (above)."""
    assert _budget("0.78") < REFERENCE_CHARACTERS <= _budget(LOW_CEILING)
    refusal = api_control.refuses_to_start("0.78")
    assert refusal.returncode == 2, refusal.output[-2000:]
    assert "refusing to start" in refusal.output
    assert "AUDITMANAGER_RUN_COST_CEILING_USD" in refusal.output
    assert str(_budget("0.78")) in refusal.output and str(REFERENCE_CHARACTERS) in refusal.output
