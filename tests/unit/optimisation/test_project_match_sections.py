"""`OPT-PROJECT-ALL-SECTIONS-01`: «Спецификация и цены» reads a version of any of the fifteen sections.

Container-free, over in-memory stand-ins for the documents projection, the price-list
repository and the runs-and-text port. The subject is the one rule that used to say «AR only»
(`project_match.py`, `if classification.section_code != SECTION_AR`):

* a version an expert confirmed in **any** of the fifteen sections is read and priced, the
  section is reported on the answer and changes nothing else: the rows, statuses, amounts and
  totals equal the АР read of the same text (the extraction, the matcher and the price list
  know no section);
* a version nobody classified is still ``version_unclassified`` and reads nothing further;
* ``section_not_ar`` is never produced any more, and stays a member of :data:`STATES` and of the
  wire enum (removing a value would be a breaking change);
* the later preconditions still stop the read in their order for a non-АР version.

**What this does not measure.** The saved text is a fake reader's Form-7 page. It is the text
the АР tests have always used; it is *not* the saved text layer of a real run of any non-АР
section: no recorded section fixture holds a specification table, so nothing here says that the
extraction understands a real ПБ, ОВ or КЖ volume.
"""

from __future__ import annotations

import typing
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from auditmanager.api.schemas import models
from auditmanager.documents.public import (
    DocumentVersionRecord,
    ProjectRecord,
    VersionClassificationRecord,
)
from auditmanager.optimisation.policy import SECTION_ORDER
from auditmanager.optimisation.project_match import (
    STATE_ANALYSIS_MISSING,
    STATE_PRICE_LIST_MISSING,
    STATE_READY,
    STATE_SECTION_NOT_AR,
    STATE_TEXT_UNAVAILABLE,
    STATE_VERSION_UNCLASSIFIED,
    STATES,
    RunCandidate,
    SavedPageText,
    SpecificationPrices,
    read_specification_prices,
)
from auditmanager.optimisation.proposals.policy import PASS_REFUSAL_REASONS
from auditmanager.optimisation.repository import PriceListPositionRecord, PriceListRevisionRecord
from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)
EXPERT = "usr_01M2545JSD15ETSNNV904XA0E1"
RUN = "run_01M2545JSD15ETSNNV904XA002"
PRICE_LIST = "prl_01M2545JSD15ETSNNV904XA001"
LAYER = "e" * 64

FORM7_PAGE = (
    "Поз. Наименование и техническая характеристика Тип, марка Код Завод- Ед. Кол. Масса Примечание\n"
    "изготовитель изм. 1 ед., кг\n"
    "1 Дверь противопожарная ДПМ-01/60 EI60 ООО «Промет» шт. 4 45,5\n"
    "2 Окно ПВХ двухкамерное ОП В2 1460х1460 шт 12\n"
    "3 Анкер химический HIT-HY 200 шт 200\n"
    "Изм. Кол.уч. Лист №док. Подпись Дата\n"
    "Стадия Лист Листов\n"
    "Р 7 12\n"
)
PRICES = (
    ("Дверь противопожарная", "ДПМ-01/60", "шт", "25000", "RUB"),
    ("Окно ПВХ двухкамерное ОП В2 1460х1460", None, "шт", "18500.5", "RUB"),
)


class _Documents:
    """One project with one document set whose current version has the classification given."""

    def __init__(self, section: str | None) -> None:
        self.project = ProjectUid.new()
        self.document = DocumentUid.new()
        version = VersionUid.new()
        self.record = DocumentVersionRecord(
            version_uid=version,
            document_uid=self.document,
            project_uid=self.project,
            version_ordinal=1,
            display_title="Комплект",
            section=None,
            media_type="application/pdf",
            byte_size=100,
            sha256="b" * 64,
            page_count=1,
            published_at=NOW,
            manifest=(),
            classification=(
                None if section is None else VersionClassificationRecord(version, "R", section, EXPERT, NOW)
            ),
        )

    def get_project(self, session: Any, project_uid: ProjectUid) -> ProjectRecord:
        return ProjectRecord(project_uid, "Школа", NOW)

    def require_document(self, session: Any, document_uid: DocumentUid) -> ProjectUid:
        return self.project

    def list_documents(self, session: Any, project_uid: ProjectUid) -> tuple[DocumentVersionRecord, ...]:
        return (self.record,)


@dataclass
class _Prices:
    with_price_list: bool = True
    asked: list[str] = field(default_factory=list)

    def list_price_lists(self, session: Any, project_uid: str) -> tuple[PriceListRevisionRecord, ...]:
        self.asked.append(project_uid)
        if not self.with_price_list:
            return ()
        return (
            PriceListRevisionRecord(
                price_list_id=PRICE_LIST, project_uid=project_uid, revision_number=1,
                uploaded_by_user_uid=EXPERT, uploaded_at=NOW, blob_id="blob_01M2545JSD15ETSNNV904XA001",
                sha256="c" * 64, size_bytes=10, media_type="text/csv", source_format="csv",
                source_filename="prices.csv", default_currency=None, parse_report={},
                data_row_count=len(PRICES), accepted_row_count=len(PRICES), skipped_row_count=0,
                is_current=True,
            ),
        )

    def position_page(
        self, session: Any, price_list_id: str, *, offset: int, limit: int
    ) -> tuple[PriceListPositionRecord, ...]:
        rows = [
            PriceListPositionRecord(
                price_list_position_id=f"prp_01M2545JSD15ETSNNV904XA0{index}",
                price_list_id=price_list_id, row_number=index, code=None, name=name, mark=mark,
                unit=unit, unit_price=Decimal(price), currency=currency, vendor=None, section_code=None,
            )
            for index, (name, mark, unit, price, currency) in enumerate(PRICES, start=2)
        ]
        return tuple(rows[offset : offset + limit])


@dataclass
class _Reader:
    runs: Sequence[RunCandidate] = (RunCandidate(RUN, "published"),)
    pages: Mapping[int, str] | None = field(default_factory=lambda: {1: FORM7_PAGE})
    asked_runs: list[str] = field(default_factory=list)

    def runs_newest_first(self, session: Any, *, version_uid: str) -> Sequence[RunCandidate]:
        self.asked_runs.append(version_uid)
        return tuple(self.runs)

    def saved_page_text(
        self, session: Any, *, run_id: str, version_uid: str, page_count: int
    ) -> SavedPageText | None:
        return None if self.pages is None else SavedPageText(run_id, LAYER, dict(self.pages))


def _read(section: str | None, *, prices: _Prices | None = None, reader: _Reader | None = None):
    documents = _Documents(section)
    answer = read_specification_prices(
        None,  # type: ignore[arg-type]
        project_uid=str(documents.project),
        document_uid=str(documents.document),
        actor_roles=frozenset({"expert"}),
        reader=reader or _Reader(),
        limit=200,
        documents=documents,  # type: ignore[arg-type]
        repository=prices or _Prices(),  # type: ignore[arg-type]
    )
    return answer, documents


def _outcome(answer: SpecificationPrices) -> tuple[Any, ...]:
    """Everything the read says except the identities of the set (they differ per call)."""
    assert answer.rows is not None and answer.matching is not None
    return (
        answer.state,
        answer.page_count,
        answer.position_count,
        answer.run_id,
        answer.text_layer_sha256,
        tuple(
            (m.row.page_number, m.row.position, m.row.name, m.row.quantity, m.status, m.basis, m.reason,
             m.excluded_reason, m.amount)
            for m in answer.rows.items
        ),
        tuple((t.currency, t.amount, t.row_count) for t in answer.totals),
        dict(answer.matching.excluded_by_reason),
    )


def test_the_fifteen_sections_are_the_ones_the_policy_lists() -> None:
    assert len(SECTION_ORDER) == 15 and "AR" in SECTION_ORDER and "PB" in SECTION_ORDER


@pytest.mark.parametrize("section", SECTION_ORDER)
def test_a_version_confirmed_in_any_section_is_read_and_priced_like_an_ar_one(section: str) -> None:
    answer, documents = _read(section)
    assert answer.state == STATE_READY, answer.state
    assert answer.section_code == section and answer.project_stage == "R"
    assert answer.version_uid == str(documents.record.version_uid)
    reference, _ = _read("AR")
    assert _outcome(answer) == _outcome(reference)
    # not vacuous: the door (by mark) and the window (by name) were matched and priced
    assert answer.rows is not None
    assert [(m.status, m.amount) for m in answer.rows.items][:2] == [
        ("matched", Decimal("100000")),
        ("matched", Decimal("222006.0")),
    ]


def test_an_unclassified_version_is_still_an_explicit_state_and_reads_nothing_further() -> None:
    prices, reader = _Prices(), _Reader()
    answer, _ = _read(None, prices=prices, reader=reader)
    assert answer.state == STATE_VERSION_UNCLASSIFIED
    assert (answer.section_code, answer.price_list, answer.rows) == (None, None, None)
    assert prices.asked == [] and reader.asked_runs == []


@pytest.mark.parametrize("section", ["AR", "KJ", "PB", "OV"])
def test_the_later_preconditions_stop_a_version_of_any_section_in_their_order(section: str) -> None:
    unpriced, _ = _read(section, prices=_Prices(with_price_list=False))
    assert (unpriced.state, unpriced.section_code, unpriced.price_list) == (STATE_PRICE_LIST_MISSING, section, None)

    no_run, _ = _read(section, reader=_Reader(runs=(RunCandidate(RUN, "failed"),)))
    assert (no_run.state, no_run.section_code, no_run.run_id) == (STATE_ANALYSIS_MISSING, section, None)
    assert no_run.price_list is not None

    no_text, _ = _read(section, reader=_Reader(pages=None))
    assert (no_text.state, no_text.section_code, no_text.run_id) == (STATE_TEXT_UNAVAILABLE, section, RUN)


@pytest.mark.parametrize("section", SECTION_ORDER)
def test_section_not_ar_is_never_produced_for_a_confirmed_section(section: str) -> None:
    answer, _ = _read(section, prices=_Prices(with_price_list=False))
    assert answer.state != STATE_SECTION_NOT_AR


def test_section_not_ar_stays_in_the_vocabulary_nothing_removes_a_value() -> None:
    """Removing an enum value is a breaking change: it stays in the code and on the wire."""
    assert STATE_SECTION_NOT_AR == "section_not_ar" and STATE_SECTION_NOT_AR in STATES
    assert STATE_SECTION_NOT_AR in PASS_REFUSAL_REASONS
    wire = typing.get_args(models.SpecificationPrices.model_fields["state"].annotation)
    assert STATE_SECTION_NOT_AR in wire
    assert set(wire) == set(STATES)
