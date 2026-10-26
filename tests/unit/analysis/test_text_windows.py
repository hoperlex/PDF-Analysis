"""`SECTION-CHUNKED-ANALYSIS-01`: the pure part of the windowed text analysis.

Container-free. The window policy (when a run is windowed), the plan (whole pages, document-global offsets,
the limit), the request (the true page numbers, the single-window body untouched) and the journal key (each of
its inputs moves it) are checked here; the stage over scripted adapters is
``tests/integration/analysis_text/test_text_windowed_stage.py`` and the executor on the lane's stack is
``tests/integration/runs/test_text_windows_executor.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from auditmanager.analysis.text.adapter import build_request
from auditmanager.analysis.text.budget import (
    MAX_ANALYSIS_WINDOWS,
    input_budget_characters,
    windowed_budget_characters,
)
from auditmanager.analysis.text.prompt import render_document
from auditmanager.analysis.text.textlayer import load_text_layer
from auditmanager.analysis.text.windows import (
    PARAM_COUNT,
    PARAM_FIRST_PAGE,
    PARAM_INDEX,
    PARAM_KEY,
    PARAM_LAST_PAGE,
    PARAM_REPLY_BLOB_ID,
    PARAM_REPLY_BLOB_SHA256,
    PARAM_REPLY_BLOB_SIZE,
    WINDOW_PREAMBLE,
    WindowPolicy,
    build_window_request,
    plan_text_windows,
    render_window,
    text_window_policy,
    window_key,
)
from auditmanager.jobs import repository as jobs_repository
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.support.v1_reference_profile import V1_REFERENCE_PROFILE

PAGE = "Страница {n}. Высота потолка {n} м. Дверь {n}."
MODEL = "claude-opus-5"


def layer_document(texts: list[str], *, version_uid: str = "ver_01M2545JSD15ETSNNV904X991J") -> dict[str, Any]:
    pages = []
    offset = 0
    for number, body in enumerate(texts, start=1):
        pages.append({
            "page_number": number, "char_start": offset, "char_end": offset + len(body), "text": body,
        })
        offset += len(body)
    return {
        "artifact_role": "prepared.text_layer",
        "artifact_version": "1.0.0",
        "version_uid": version_uid,
        "normalization": {"id": "nfc_v1", "description": "NFC"},
        "total_char_count": offset,
        "pages": pages,
    }


def nine_pages() -> list[str]:
    return [PAGE.format(n=n) for n in range(1, 10)]


def three_window_plan(max_windows: int = MAX_ANALYSIS_WINDOWS):
    texts = nine_pages()
    layer = load_text_layer(layer_document(texts))
    # 3 pages fit a window; a fourth would not.
    return plan_text_windows(layer, WindowPolicy(3 * len(texts[0]) + 5, max_windows))


# -- the budget ----------------------------------------------------------------------


def test_the_windowed_budget_is_that_many_calls_and_one_window_is_the_call_budget() -> None:
    call = input_budget_characters(MODEL, 1.0)
    assert call == 152_361
    assert windowed_budget_characters(call) == call * MAX_ANALYSIS_WINDOWS
    assert windowed_budget_characters(call, 1) == call, "one window is exactly the one-call budget"
    assert windowed_budget_characters(call, 2) == 2 * call
    assert windowed_budget_characters(0) == 0


@pytest.mark.parametrize("bad", [-1, 1.5, True, "7"])
def test_the_windowed_budget_refuses_what_cannot_be_a_budget(bad: Any) -> None:
    with pytest.raises(ValueError):
        windowed_budget_characters(bad)


def test_the_window_limit_covers_the_upload_envelope_at_the_real_sets_density() -> None:
    """500 pages at 3 123 characters (the real set, 93 690 / 30) fit the primary model's windows."""
    per_page = 93_690 / 30
    needed = 500 * per_page / input_budget_characters(MODEL, 1.0)
    assert needed < MAX_ANALYSIS_WINDOWS, needed
    assert MAX_ANALYSIS_WINDOWS >= 2, "a limit of one is the rollback, not the shipped value"


# -- when a run is windowed ------------------------------------------------------------


def test_no_recorded_count_is_the_single_call() -> None:
    assert text_window_policy(text_character_count=None, model_id=MODEL, ceiling_usd=1.0) is None


def test_a_count_up_to_and_including_the_call_budget_is_the_single_call() -> None:
    budget = input_budget_characters(MODEL, 1.0)
    for count in (0, 1, budget - 1, budget):
        assert text_window_policy(text_character_count=count, model_id=MODEL, ceiling_usd=1.0) is None


def test_a_count_strictly_above_the_call_budget_is_windowed_at_the_call_budget() -> None:
    budget = input_budget_characters(MODEL, 1.0)
    policy = text_window_policy(text_character_count=budget + 1, model_id=MODEL, ceiling_usd=1.0)
    assert policy == WindowPolicy(window_characters=budget, max_windows=MAX_ANALYSIS_WINDOWS)


def test_one_window_as_the_limit_is_the_rollback_and_never_windows() -> None:
    budget = input_budget_characters(MODEL, 1.0)
    assert text_window_policy(
        text_character_count=10 * budget, model_id=MODEL, ceiling_usd=1.0, max_windows=1
    ) is None


def test_an_unpinned_model_is_refused_as_the_stage_refuses_it() -> None:
    with pytest.raises(DomainError):
        text_window_policy(text_character_count=1, model_id="not-a-pinned-model", ceiling_usd=1.0)


@pytest.mark.parametrize("bad", [-1, 1.5, True])
def test_a_count_that_is_not_a_count_is_a_wiring_fault(bad: Any) -> None:
    with pytest.raises(ValueError):
        text_window_policy(text_character_count=bad, model_id=MODEL, ceiling_usd=1.0)


def test_a_windowed_policy_takes_at_least_two_windows() -> None:
    with pytest.raises(ValueError):
        WindowPolicy(window_characters=10, max_windows=1)


# -- the plan --------------------------------------------------------------------------


def test_the_plan_is_whole_pages_in_order_with_document_global_offsets() -> None:
    plan = three_window_plan()
    assert [(w.index, w.first_page, w.last_page) for w in plan.windows] == [(0, 1, 3), (1, 4, 6), (2, 7, 9)]
    layer = plan.layer
    for window in plan.windows:
        assert window.char_start == layer.pages[window.first_page - 1].char_start
        assert window.char_end == layer.pages[window.last_page - 1].char_end
        assert window.text == layer.slice(window.char_start, window.char_end)
    assert plan.windows[0].char_start == 0 and plan.windows[-1].char_end == len(layer.document_text)
    assert "".join(w.text for w in plan.windows) == layer.document_text


def test_a_plan_of_exactly_the_limit_is_accepted_and_one_more_is_refused_with_both_figures() -> None:
    assert len(three_window_plan(max_windows=3).windows) == 3
    with pytest.raises(DomainError) as refused:
        three_window_plan(max_windows=2)
    error = refused.value
    assert error.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert error.detail_fields["reason"] == "window_plan_over_limit"
    assert "3 windows" in str(error) and "at most 2" in str(error)


def test_a_page_larger_than_a_window_is_refused_and_named_not_split() -> None:
    texts = nine_pages()
    texts[4] = texts[4] + "x" * 500
    layer = load_text_layer(layer_document(texts))
    with pytest.raises(DomainError) as refused:
        plan_text_windows(layer, WindowPolicy(3 * len(texts[0]) + 5, 12))
    assert refused.value.detail_fields["reason"] == "window_page_exceeds_limit"
    assert "page 5" in str(refused.value)


def test_a_budget_with_no_room_for_text_is_refused() -> None:
    layer = load_text_layer(layer_document(nine_pages()))
    with pytest.raises(DomainError) as refused:
        plan_text_windows(layer, WindowPolicy(0, 12))
    assert refused.value.detail_fields["reason"] == "window_ceiling_unusable"


# -- the request -----------------------------------------------------------------------


def test_a_window_request_shows_the_fragment_with_the_documents_own_page_numbers() -> None:
    plan = three_window_plan()
    second = plan.windows[1]
    request = build_window_request(
        model_id=MODEL, bundle=V1_REFERENCE_PROFILE.prompt_bundle, plan=plan, window=second
    )
    content = request.body["messages"][0]["content"]
    assert content == render_window(plan, second)
    assert content.startswith(WINDOW_PREAMBLE.format(index=2, count=3, first=4, last=6, total=9))
    banners = [line for line in content.splitlines() if line.startswith("=== Страница")]
    assert banners == ["=== Страница 4 ===", "=== Страница 5 ===", "=== Страница 6 ==="]
    for page in plan.pages_of(second):
        assert page.text in content
    assert "Высота потолка 1 м" not in content and "Высота потолка 9 м" not in content


def test_a_window_request_differs_from_the_whole_documents_only_in_the_user_message() -> None:
    plan = three_window_plan()
    bundle = V1_REFERENCE_PROFILE.prompt_bundle
    whole = build_request(model_id=MODEL, bundle=bundle, text_layer=plan.layer)
    window = build_window_request(model_id=MODEL, bundle=bundle, plan=plan, window=plan.windows[0])
    assert {k: v for k, v in window.body.items() if k != "messages"} == {
        k: v for k, v in whole.body.items() if k != "messages"
    }
    assert window.request_sha256 != whole.request_sha256
    assert len({
        build_window_request(model_id=MODEL, bundle=bundle, plan=plan, window=w).request_sha256
        for w in plan.windows
    }) == 3, "every window asks its own question"


def test_the_body_without_a_user_content_is_what_it_always_was() -> None:
    plan = three_window_plan()
    bundle = V1_REFERENCE_PROFILE.prompt_bundle
    request = build_request(model_id=MODEL, bundle=bundle, text_layer=plan.layer)
    assert request.body["messages"] == [{"role": "user", "content": render_document(plan.layer)}]


# -- the journal key -------------------------------------------------------------------


def _key(plan, window, **override: Any) -> str:
    request = build_window_request(
        model_id=MODEL, bundle=V1_REFERENCE_PROFILE.prompt_bundle, plan=plan, window=window
    )
    arguments: dict[str, Any] = {
        "plan": plan, "window": window, "profile_sha256": V1_REFERENCE_PROFILE.content_sha256,
        "model_id": MODEL, "request_sha256": request.request_sha256,
    }
    arguments.update(override)
    return window_key(**arguments)


def test_the_key_is_stable_for_the_same_window_of_the_same_text() -> None:
    first, second = three_window_plan(), three_window_plan()
    assert _key(first, first.windows[0]) == _key(second, second.windows[0])


def test_the_key_moves_with_the_window_the_text_the_profile_the_model_and_the_request() -> None:
    plan = three_window_plan()
    base = _key(plan, plan.windows[0])
    assert _key(plan, plan.windows[1]) != base, "another window"
    assert _key(plan, plan.windows[0], profile_sha256="0" * 64) != base, "another profile or prompt"
    assert _key(plan, plan.windows[0], model_id="claude-sonnet-5") != base, "another model"
    assert _key(plan, plan.windows[0], request_sha256="1" * 64) != base, "another request"

    texts = nine_pages()
    texts[7] = texts[7] + "!"
    changed = plan_text_windows(
        load_text_layer(layer_document(texts)), WindowPolicy(3 * len(texts[0]) + 5, 12)
    )
    assert changed.windows[0].text == plan.windows[0].text, "the first window's own pages are unchanged"
    assert _key(changed, changed.windows[0]) != base, "a changed text never replays an old reply"

    other_version = plan_text_windows(
        load_text_layer(layer_document(nine_pages(), version_uid="ver_01M2545JSD15ETSNNV904X991K")),
        WindowPolicy(3 * len(nine_pages()[0]) + 5, 12),
    )
    assert _key(other_version, other_version.windows[0]) != base, "another version"


# -- the two spellings of the saved window's parameters --------------------------------


def test_jobs_reads_the_same_parameter_names_the_analysis_writes() -> None:
    """``jobs`` may not import ``analysis``, so the names are spelled twice; this holds them together."""
    assert jobs_repository._WINDOW_KEY == PARAM_KEY
    assert jobs_repository._WINDOW_INDEX == PARAM_INDEX
    assert jobs_repository._WINDOW_COUNT == PARAM_COUNT
    assert jobs_repository._WINDOW_FIRST == PARAM_FIRST_PAGE
    assert jobs_repository._WINDOW_LAST == PARAM_LAST_PAGE
    assert jobs_repository._WINDOW_BLOB_ID == PARAM_REPLY_BLOB_ID
    assert jobs_repository._WINDOW_BLOB_SHA == PARAM_REPLY_BLOB_SHA256
    assert jobs_repository._WINDOW_BLOB_SIZE == PARAM_REPLY_BLOB_SIZE
