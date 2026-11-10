"""`D-675`: the content key of a stored comparison answer carries the job's frozen cell; a job with no cell keeps the key it always had.

A job the stage layout admitted froze a cell -- model and effort (`HOSTS-CMP-01`; since `LIMITS-01` it has no answer limit and no timeout) -- and
the spend wrapper sends every call of it with that effort. The answer a call stores is found again by its **content key**; if the key did not carry
the cell, a job with another model or effort would be handed the answer of the first one and never ask. This file holds, for the pair check and the sheet
description (the two kinds whose key names a model and is built where the job's cell is at hand):

* the key of a job **with no cell** is the key of the base commit, byte for byte -- pinned digests computed on ``0b5b1eaf3`` before the change;
* a cell moves the key, and each of its model and effort moves it alone;
* the estimate (the route's cell) and the handler (the job's cell) read the same cell into the key, so what was priced is what is looked up;
* an answer stored under one cell is reused by a job with that cell and by no job with another.

Break-it-once: with the ``cell`` argument ignored in ``plans.content_key`` / ``ai_sheets.repository.content_key``, the tests of a moved key fail; with
``cell=route.cell`` / ``cell=job.cell`` dropped from the method or the handler, the tests of the wiring fail.
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

from auditmanager.analysis.public import CellSettings
from auditmanager.comparison.ai_jobs.model import AiMode, cell_key_document
from auditmanager.comparison.ai_pairs.handler import PairCheckHandler
from auditmanager.comparison.ai_pairs.method import PairCheckMethod
from auditmanager.comparison.ai_pairs.model import KIND_NO_PAIR, PageFacts, Question, QuestionPage
from auditmanager.comparison.ai_pairs.plans import PlanContext, content_key, forward_plan, reverse_plan
from auditmanager.comparison.ai_sheets.method import SheetChangesMethod, keys_for
from auditmanager.comparison.ai_sheets.repository import content_key as sheet_content_key

A, B = "ver_A", "ver_B"

#: Computed with the code of ``0b5b1eaf3`` (no cell in any key): the keys a job with no cell has always had.
LEGACY_FORWARD = "cf66adc40262586014fec66ee7ddaa784d90e3942651a7f0bc973578c7ba0a1c"
LEGACY_REVERSE = "81f654a21dee5ad59b73cd1f6ba5d6a99648ea95ef0038b68f998a3b6712d9a3"
LEGACY_DIRECT = "cb7bb3d3d1784f6e22d85445d99a3e77255947fa73ea1fb308582fdc6df44a58"
LEGACY_SHEET = "e816a82fef4ce960caa0c01b63842409c2fecaa66a032b5b768d85c09582849b"

CELL = CellSettings(cell_key="comparison_pair_check:main", model_id="gpt-6-sol", effort="high")
SHEET_CELL = CellSettings(cell_key="comparison_sheet_changes:main", model_id="gpt-6-sol", effort="high")


def facts(version: str, number: int, *, sheet: str = "", title: str = "") -> PageFacts:
    return PageFacts(
        page_profile_id=f"cpr_{version}_{number}", version_uid=version, page_number=number, content_key=f"key-{version}-{number}",
        sheet_number=sheet, title=title, preview_blob_id=f"blob_{version}_{number}", preview_sha256=f"{number:02d}" * 32, preview_size=1000,
    )


def pages_of() -> dict[tuple[str, int], PageFacts]:
    return {(v, n): facts(v, n, sheet=str(n), title=f"План {n}") for v in (A, B) for n in range(1, 8)}


def context(cell: CellSettings | None = None) -> PlanContext:
    return PlanContext(
        project_uid="prj_P", model_identity="claude-opus-5", provider_mode="live", order=(A, B), page_counts={A: 7, B: 7},
        facts=pages_of(), document_title="133/23-ГК-ЭО", cell=cell,
    )


def question() -> Question:
    return Question(
        kind=KIND_NO_PAIR, a=QuestionPage(A, 2, "cpr_ver_A_2"), b_version_uid=B,
        candidates=(QuestionPage(B, 2, "cpr_ver_B_2"), QuestionPage(B, 3, "cpr_ver_B_3")), back={3: (1, 4)},
    )


# -- a job with no cell has the key it always had ------------------------------------------------------------------------------


def test_a_job_with_no_cell_keeps_every_key_byte_identical() -> None:
    assert forward_plan(question(), context()).key == LEGACY_FORWARD
    reverse = reverse_plan(question(), 3, context())
    assert reverse is not None and reverse.key == LEGACY_REVERSE
    direct = content_key(
        project_uid="prj_P", model_identity="m", provider_mode="live", kind="no_pair", prompt="t", pages=[facts(A, 1)])
    assert direct == LEGACY_DIRECT
    assert sheet_content_key(project_uid="prj_1", kind="pair", subject_key="a" * 64, prompt_version="v", model="m") == LEGACY_SHEET
    assert cell_key_document(None) is None


# -- a cell moves the key; its model and effort each alone ---------------------------------------------------------------------------


def test_the_cells_key_document_names_the_model_and_the_effort_and_no_answer_limit() -> None:
    """`R-153n`: the answer limit left the cell, so it left the key; this is what makes an answer stored under the old key be asked again."""
    assert cell_key_document(CELL) == {"model_id": "gpt-6-sol", "effort": "high"}


def test_a_cell_moves_the_pair_check_key_and_each_of_its_model_and_effort_moves_it_alone() -> None:
    plain = forward_plan(question(), context()).key
    celled = forward_plan(question(), context(CELL)).key
    assert celled != plain and celled == forward_plan(question(), context(replace(CELL))).key
    moved = {
        forward_plan(question(), context(replace(CELL, model_id="gpt-6-astra"))).key,
        forward_plan(question(), context(replace(CELL, effort="medium"))).key,
    }
    assert len(moved | {celled, plain}) == 4, "the two changes and the two bases are four different keys"
    reverse = reverse_plan(question(), 3, context(CELL))
    assert reverse is not None and reverse.key != LEGACY_REVERSE and reverse.key != celled


def test_a_cell_moves_the_sheet_description_key_the_same_way() -> None:
    base = dict(project_uid="prj_1", kind="pair", subject_key="a" * 64, prompt_version="v", model="m")
    celled = sheet_content_key(**base, cell=SHEET_CELL)  # type: ignore[arg-type]
    assert celled != LEGACY_SHEET and celled == sheet_content_key(**base, cell=replace(SHEET_CELL))  # type: ignore[arg-type]
    for other in (replace(SHEET_CELL, model_id="gpt-6-astra"), replace(SHEET_CELL, effort="medium")):
        assert sheet_content_key(**base, cell=other) not in (celled, LEGACY_SHEET), other  # type: ignore[arg-type]


# -- the estimate and the handler read the same cell into the key -----------------------------------------------------------------


def test_the_pair_check_estimate_keys_on_the_cell_of_the_route() -> None:
    snapshot = SimpleNamespace(order=(A, B), page_counts={A: 7, B: 7}, facts=pages_of(), document_title="133/23-ГК-ЭО")

    def method_over(cell: CellSettings | None) -> PairCheckMethod:
        route = SimpleNamespace(pinned_model="claude-opus-5", cell=cell)
        return PairCheckMethod(provider_mode="live", route_reader=lambda session, work_kind, mode: route)  # type: ignore[arg-type,return-value]

    built = method_over(CELL).context(None, snapshot, "prj_P", "comparison_pair_check")  # type: ignore[arg-type]
    assert built.cell == CELL
    assert forward_plan(question(), built).key == forward_plan(question(), context(CELL)).key
    bare = method_over(None).context(None, snapshot, "prj_P", "comparison_pair_check")  # type: ignore[arg-type]
    assert bare.cell is None and forward_plan(question(), bare).key == LEGACY_FORWARD


class _Matrices:
    def build_by_id(self, session: Any, build_id: str) -> Any:
        return SimpleNamespace(order=(A, B), summary={"page_counts": {A: 7, B: 7}})


class _Pairs:
    def page_facts_of(self, session: Any, wanted: Any, algo: Any) -> Any:
        return pages_of()

    def require_document(self, session: Any, project_uid: str, document_uid: str) -> str:
        return "133/23-ГК-ЭО"


def test_the_pair_check_handler_keys_on_the_cell_the_job_froze() -> None:
    handler = PairCheckHandler(None, pairs=_Pairs(), matrices=_Matrices())  # type: ignore[arg-type]

    def key_of(cell: CellSettings | None) -> str:
        job = SimpleNamespace(
            matrix_id="mtx", project_uid="prj_P", document_uid="doc", pinned_model="claude-opus-5", provider_mode="live", cell=cell)
        built = handler._context(None, job, question())  # type: ignore[arg-type]
        assert built.cell == cell
        return forward_plan(question(), built).key

    assert key_of(None) == LEGACY_FORWARD
    assert key_of(CELL) == forward_plan(question(), context(CELL)).key != LEGACY_FORWARD
    assert key_of(replace(CELL, effort="medium")) != key_of(CELL), "two jobs with different cells never share a key"


def test_the_sheet_estimate_and_the_job_key_on_the_same_cell() -> None:
    pair = SimpleNamespace(pair_id="pair-1", project_uid="prj_1", subject_key="a" * 64, one_sided=False, transition_id="tr-1")
    assert keys_for([pair], "m")["pair-1"] != keys_for([pair], "m", SHEET_CELL)["pair-1"]  # type: ignore[list-item]
    assert keys_for([pair], "m", SHEET_CELL) == keys_for([pair], "m", replace(SHEET_CELL))  # type: ignore[list-item]

    stored_under: set[str] = set()

    class Repo:
        def stored_keys(self, session: Any, project_uid: str, keys: list[str]) -> list[str]:
            return [key for key in keys if key in stored_under]

    def method_with(cell: CellSettings | None) -> SheetChangesMethod:
        built = SheetChangesMethod(repository=Repo(), model_reader=lambda session: "m", cell_reader=lambda session: cell)  # type: ignore[arg-type]
        built.eligible_pairs = lambda session, scope: [pair]  # type: ignore[method-assign]
        built._group_of = lambda session, one: None  # type: ignore[method-assign]
        return built

    request = SimpleNamespace(scope=SimpleNamespace(project_uid="prj_1"), mode=AiMode.START)
    stored_under.add(keys_for([pair], "m", SHEET_CELL)["pair-1"])  # type: ignore[list-item]
    # The answer stored under SHEET_CELL is reused by a job with that cell and by no job with another cell or none.
    assert method_with(SHEET_CELL).counts(None, request).reused == 1  # type: ignore[arg-type]
    assert method_with(replace(SHEET_CELL, effort="medium")).counts(None, request).reused == 0  # type: ignore[arg-type]
    assert method_with(None).counts(None, request).reused == 0  # type: ignore[arg-type]

    # The job's side: the handler looks the description up under ``keys_for([pair], job.pinned_model, job.cell)`` (same function, same cell).
    chosen, keys, stored = method_with(None).wanted(None, request.scope, AiMode.START, "m", restart=False, cell=SHEET_CELL)  # type: ignore[arg-type]
    assert keys["pair-1"] in stored and chosen == []
    chosen, keys, stored = method_with(None).wanted(None, request.scope, AiMode.START, "m", restart=False)  # type: ignore[arg-type]
    assert keys["pair-1"] not in stored and chosen == [pair]


def test_the_default_sheet_cell_reader_reads_the_cell_of_the_route(monkeypatch: pytest.MonkeyPatch) -> None:
    from auditmanager.comparison.ai_jobs import estimate
    from auditmanager.comparison.ai_sheets.method import cell_reader_of_route

    asked: list[tuple[str, str]] = []

    def read_route(session: Any, work_kind: str, provider_mode: str) -> Any:
        asked.append((work_kind, provider_mode))
        return SimpleNamespace(pinned_model="m", cell=SHEET_CELL)

    monkeypatch.setattr(estimate, "read_route", read_route)
    assert cell_reader_of_route(None) == SHEET_CELL  # type: ignore[arg-type]
    assert asked == [("comparison_sheet_changes", "live")]
