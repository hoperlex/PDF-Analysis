"""`CMP-VC-REPORT-01`: the MD summary of a stored series and the draft of a report (database and bucket).

The summary is the same bytes for the same data and exists only once a sheet is described; a draft is made from it or from an uploaded MD file with
its estimate, **calls no model and spends nothing**, and the upload's refusals write nothing."""

from __future__ import annotations

import hashlib
from typing import Any

import pytest

from auditmanager.comparison.report.model import MAX_SOURCE_BYTES
from auditmanager.shared.errors import DomainError, ErrorCode
from tests.integration.comparison.report.conftest import ADMIN, EXPERT

UPLOAD = """# Сводка изменений X

## 1. X: V1 → V2

A: V1, файл «a.pdf». B: V2, файл «b.pdf».

### л.1 · План (A стр. PDF 1 → B стр. PDF 1)

- **Кабель ВВГнг(А)-LS** — 3×2,5 → 3×4

## 2. X: V2 → V3

_По данным сравнения изменений содержания нет._
""".encode("utf-8")


def counts(db: Any) -> dict[str, int]:
    return {t: db.state(f"SELECT count(*) FROM {t}") for t in (
        "comparison_report", "comparison_report_part", "comparison_report_artifact", "comparison_ai_job", "comparison_model_call",
        "command_record",
    )}


def refused(db: Any, call: Any) -> DomainError:
    with pytest.raises(DomainError) as info:
        call()
    return info.value


def test_the_summary_is_the_same_bytes_for_the_same_data_and_describes_what_is_stored(db: Any, world: Any) -> None:
    first = db.service().read_series_summary(series_id=world["series"])
    assert db.service().read_series_summary(series_id=world["series"]) == first
    text = first.decode("utf-8")
    assert "## 1. 133/23-ГК-ЭМ2: V1 → V2" in text and "A: V1, файл «v1.pdf». B: V2, файл «v2.pdf»." in text
    assert "### л.1 · План (A стр. PDF 1 → B стр. PDF 1)" in text
    assert "**Кабель ВВГнг(А)-LS** — щит ЩР-1: 3×2,5 → 3×4 (с изображения)" in text
    assert "ИИ-описание не запускалось" in text  # the second transition's sheet has no description: a gap, never «no changes»
    assert "## Реестр покрытия" in text and text.endswith("\n")


def test_the_summary_is_unavailable_until_a_sheet_is_described_and_an_unknown_series_is_not_found(db: Any, route: Any, h: Any) -> None:
    bare = h.report_world(db.connection, described=False)
    error = refused(db, lambda: db.service().read_series_summary(series_id=bare["series"]))
    assert error.code is ErrorCode.CONFLICT and error.detail_fields["conflict_reason"] == "comparison_summary_unavailable"
    missing = refused(db, lambda: db.service().read_series_summary(series_id="cser_01ARZ3NDEKTSV4RRFFQ69G5FAV"))
    assert missing.code is ErrorCode.NOT_FOUND
    h.describe(db.connection, bare["project"], bare["pairs"][0]["result"])
    assert db.service().read_series_summary(series_id=bare["series"])


def test_a_draft_from_the_summary_has_its_estimate_and_calls_no_model(db: Any, world: Any, make: Any) -> None:
    before = counts(db)
    report = make(world)
    after = counts(db)
    assert after["comparison_report"] == before["comparison_report"] + 1 and after["comparison_report_artifact"] == before["comparison_report_artifact"] + 1
    assert after["comparison_ai_job"] == before["comparison_ai_job"] and after["comparison_model_call"] == before["comparison_model_call"]
    assert db.answers.calls == 0
    assert (report["kind"], report["source"], report["state"], report["reuse"]) == ("client", "series_summary", "draft", False)
    estimate = report["estimate"]
    # only the first transition has a description to write about: the other two are finished by the program, with no call
    assert estimate["method"] == "report" and estimate["calls"] == 1 and estimate["units"] == 1 and estimate["reused"] == 0
    assert estimate["transitions"] == 3 and estimate["images"] == 0 and len(estimate["estimate_digest"]) == 64
    assert report["parts"] == [] and "job" not in report
    assert [a["kind"] for a in report["artifacts"]] == ["source_md"]
    source = db.service().read_report_source_md(report_id=report["report_id"])
    assert hashlib.sha256(source).hexdigest() == report["artifacts"][0]["sha256"]
    assert source == db.service().read_series_summary(series_id=world["series"])  # the exact MD the report is built from


def test_an_analytic_draft_counts_two_calls_per_transition_and_the_composer(db: Any, world: Any, make: Any) -> None:
    estimate = make(world, "analytic")["estimate"]
    assert estimate["calls"] == 3 * 2 + 1 and estimate["units"] == 3


def test_a_repeat_of_a_key_replays_and_another_payload_under_it_is_refused(db: Any, world: Any, make: Any) -> None:
    first = make(world, key="key-1")
    again = make(world, key="key-1")
    assert again["report_id"] == first["report_id"] and db.state("SELECT count(*) FROM comparison_report") == 1
    clash = refused(db, lambda: make(world, "analytic", key="key-1"))
    assert clash.code is ErrorCode.IDEMPOTENCY_KEY_REUSE and db.state("SELECT count(*) FROM comparison_report") == 1


def test_every_write_is_an_experts_act_and_the_module_flag_comes_first(db: Any, world: Any, make: Any) -> None:
    before = counts(db)
    denied = refused(db, lambda: db.service().create_report(
        series_id=world["series"], kind="client", reuse=False, user_uid=h_actor(), actor_label="A", actor_roles=ADMIN, idempotency_key="k-admin"))
    assert denied.code is ErrorCode.PERMISSION_DENIED and denied.detail_fields["required_capability"] == "role:expert"
    off = refused(db, lambda: db.service(modules="none").create_report(
        series_id="cser_01ARZ3NDEKTSV4RRFFQ69G5FAV", kind="client", reuse=False, user_uid=h_actor(), actor_label="A", actor_roles=EXPERT,
        idempotency_key="k-off"))
    assert off.code is ErrorCode.DEPENDENCY_UNAVAILABLE and off.detail_fields["dependency"] == "comparison_modules"  # before the unknown series is found
    assert counts(db) == before
    for read in (lambda: db.service(modules="none").read_series_summary(series_id=world["series"]),
                 lambda: db.service(modules="none").get_report(report_id="crt_01ARZ3NDEKTSV4RRFFQ69G5FAV")):
        assert refused(db, read).detail_fields["dependency"] == "comparison_modules"


def h_actor() -> str:
    from tests.integration.comparison.report.conftest import support

    return support.ACTOR


# -- the upload ---------------------------------------------------------------------------------------------------------------------

def upload(db: Any, world: Any, content: bytes, **over: Any) -> dict[str, Any]:
    return db.service().upload_report_source(
        series_id=world["series"], kind=over.pop("kind", "client"), reuse=over.pop("reuse", False), content=content,
        source_name=over.pop("source_name", "summary.md"), user_uid=h_actor(), actor_label="Эксперт", actor_roles=EXPERT,
        idempotency_key=over.pop("key", "up-" + hashlib.sha256(content).hexdigest()[:16]),
    )


def test_an_uploaded_md_file_makes_a_draft_with_its_estimate_and_no_model_call(db: Any, world: Any) -> None:
    report = upload(db, world, UPLOAD)
    assert (report["source"], report["state"], report["source_name"]) == ("uploaded_md", "draft", "summary.md")
    assert report["estimate"]["calls"] == 1 and report["estimate"]["transitions"] == 2  # the second transition is the confirmed absence of changes
    assert db.answers.calls == 0 and db.state("SELECT count(*) FROM comparison_model_call") == 0
    assert db.service().read_report_source_md(report_id=report["report_id"]) == UPLOAD


@pytest.mark.parametrize("content", [
    b"", "# нет переходов\n\nтекст\n".encode(), "## 1. Х: V1 - V2 текст\n".encode("cp1251"), b"\xff\xfe\x00bad",
    "## 1. X: V1 → V2\n\n## 1. X: V2 → V3\n".encode(),  # a number twice
    "## 9. X: V1 → V2\n".encode(),  # a transition the series does not have
])
def test_an_upload_that_is_not_a_summary_of_this_series_is_refused_and_writes_nothing(db: Any, world: Any, content: bytes) -> None:
    before = counts(db)
    error = refused(db, lambda: upload(db, world, content))
    assert error.code is ErrorCode.VALIDATION_FAILED and error.detail_fields["constraint"] == "comparison_report_source_invalid"
    assert error.detail_fields["field"] == "content"
    assert counts(db) == before


def test_an_upload_over_20_mib_is_refused_and_one_of_exactly_20_mib_is_not(db: Any, world: Any) -> None:
    assert MAX_SOURCE_BYTES == 20 * 1024 * 1024
    before = counts(db)
    big = UPLOAD + b" " * (MAX_SOURCE_BYTES - len(UPLOAD) + 1)
    assert refused(db, lambda: upload(db, world, big)).detail_fields["constraint"] == "comparison_report_source_invalid"
    assert counts(db) == before
    assert upload(db, world, UPLOAD + b"\n" * 5)["state"] == "draft"


def test_an_upload_to_an_unknown_series_is_not_found(db: Any, world: Any) -> None:
    other = dict(world, series="cser_01ARZ3NDEKTSV4RRFFQ69G5FAV")
    assert refused(db, lambda: upload(db, other, UPLOAD)).code is ErrorCode.NOT_FOUND
