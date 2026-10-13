"""`W55B-BUDGET-01`: the budget's constants are held by the measurements that fixed them.

Container-free. ``budget.py`` carries two calibrated numbers -- characters per token and the
page-framing allowance -- and its docstring says they come from recorded evidence. This file
re-derives them from that evidence on every run, so a constant that stops covering a measured
document, or an envelope that outgrows the allowance, turns a test red instead of turning a
real run into a ``cost_budget_exceeded``.

The evidence is the repository's only **measured** model usage (``cost_basis: measured``,
``provider_mode: live``): the fourteen documents of the PC-02 baseline
(``artifacts/validation/PC-02/baseline/ledger.json``) and the synthetic AR baseline of the
PC-01 re-certification. ``fixtures/recorded/text_analysis`` is deliberately **not** used: its
README says its token counts are authored, not measured.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from auditmanager.analysis.stages.extraction import extract_document
from auditmanager.analysis.stages.source_preparation import _build_text_layer
from auditmanager.analysis.text.budget import (
    CHARACTERS_PER_TOKEN,
    PAGE_FRAMING_ALLOWANCE_CHARACTERS,
    REFERENCE_DOCUMENT_CHARACTERS,
    _fixed_prompt_characters,
    input_budget_characters,
)
from auditmanager.analysis.text.lock import provider_lock
from auditmanager.analysis.text.prompt import AR_TEXT_PROMPT_BUNDLE, render_document
from auditmanager.analysis.text.textlayer import load_text_layer
from auditmanager.ingest import MAX_PAGES
from auditmanager.ingest.envelope import inspect_pdf

REPO = Path(__file__).resolve().parents[3]
PC02_LEDGER = REPO / "artifacts/validation/PC-02/baseline/ledger.json"
PC02_DOCUMENTS = REPO / "fixtures/validation/PC-02/documents"
RECERTIFICATIONS = sorted((REPO / "artifacts/checkpoints/PC-01").glob("recertification-*.json"))
AR_BASELINE = REPO / "fixtures/synthetic/ar/ar_baseline.pdf"
PRIMARY = "claude-opus-5"


def _require(path: Path) -> Path:
    if not path.is_file():
        pytest.fail(f"the calibration evidence {path.relative_to(REPO)} is missing; it is never skipped")
    return path


def _measure(pdf: Path) -> dict[str, int]:
    """pypdfium2's count, pdfplumber's text and the prompt the product would render, for one PDF."""
    payload = _require(pdf).read_bytes()
    facts = inspect_pdf(payload, require_text=False)
    document = extract_document(payload)
    layer = load_text_layer(_build_text_layer(document, version_uid="ver_01M2FRWKW5Z4JK0M0K6PXGHDBT"))
    return {
        "pages": facts.page_count,
        "pdfium": sum(facts.page_characters),
        "plumber": sum(len(page.text) for page in document.pages),
        "rendered": len(render_document(layer)),
    }


def _measured_documents() -> list[dict[str, Any]]:
    """Every document the repository holds a live, measured input-token count for."""
    ledger = json.loads(_require(PC02_LEDGER).read_text(encoding="utf-8"))["documents"]
    documents: list[dict[str, Any]] = []
    for label, row in sorted(ledger.items()):
        assert row["provider_mode"] == ["live"] and row["cost_basis"] == ["measured"], (
            f"{label}: the evidence is no longer live and measured, so it calibrates nothing"
        )
        documents.append(
            {"label": label, "tokens": int(row["input_tokens"])}
            | _measure(PC02_DOCUMENTS / f"{label}.pdf")
        )
    assert RECERTIFICATIONS, "the PC-01 re-certification records are missing"
    counts = set()
    for record in RECERTIFICATIONS:
        live = json.loads(record.read_text(encoding="utf-8"))["live_run"]
        assert live["provider_mode"] == "live" and live["cost_basis"] == "measured"
        counts.add(int(live["input_tokens"]))
    assert len(counts) == 1, "the AR baseline's tokenisation is deterministic; the records disagree"
    documents.append(
        {"label": "ar_baseline", "tokens": counts.pop()} | _measure(AR_BASELINE)
    )
    return documents


@pytest.fixture(scope="module")
def measured() -> list[dict[str, Any]]:
    return _measured_documents()


def _characters_per_token(document: dict[str, Any]) -> float:
    """What the request cost: its characters (system prompt, schema, rendered document) per token."""
    return (_fixed_prompt_characters() + document["rendered"]) / document["tokens"]


class TestTheCharactersPerTokenConstantIsHeldByTheMeasurements:
    def test_the_evidence_is_the_expected_fifteen_documents(self, measured: list[dict[str, Any]]) -> None:
        assert len(measured) == 15
        assert {m["label"] for m in measured} >= {"PC02-C01", "PC02-S05", "ar_baseline"}

    def test_the_assumed_density_is_never_kinder_than_a_measured_document(
        self, measured: list[dict[str, Any]]
    ) -> None:
        """The request's characters over the assumed ratio must reach every measured token count."""
        for document in measured:
            predicted_tokens = (_fixed_prompt_characters() + document["rendered"]) / float(
                CHARACTERS_PER_TOKEN
            )
            assert predicted_tokens >= document["tokens"], (
                f"{document['label']}: the budget would call {document['tokens']} real input "
                f"tokens {predicted_tokens:.0f}"
            )

    def test_the_margin_over_the_densest_measured_document_is_at_least_a_quarter(
        self, measured: list[dict[str, Any]]
    ) -> None:
        densest = min(_characters_per_token(document) for document in measured)
        assert densest >= 1.25 * float(CHARACTERS_PER_TOKEN), (
            f"the densest measured document costs {densest:.3f} characters per token; "
            f"{float(CHARACTERS_PER_TOKEN)} leaves less than a quarter of margin"
        )

    def test_the_densest_document_is_the_ar_baseline(self, measured: list[dict[str, Any]]) -> None:
        """Pinned so the report's sentence ("the AR baseline is the densest") stays true."""
        densest = min(measured, key=_characters_per_token)
        assert densest["label"] == "ar_baseline"
        assert 1.9 <= _characters_per_token(densest) <= 2.0

    def test_a_document_at_the_budget_still_finishes_under_the_ceiling_at_the_densest_measured_rate(
        self, measured: list[dict[str, Any]]
    ) -> None:
        """The run must finish, not merely start (`cost.py` halts after the call that overspends).

        Priced from the lock at the densest *measured* density, with the output cap spent in
        full, a document exactly at the default budget costs less than the ceiling.
        """
        pin = provider_lock().model(PRIMARY)
        ceiling = json.loads((REPO / "docs/program/P02_LOCK.json").read_text(encoding="utf-8"))[
            "models"
        ]["run_cost_ceiling_usd"]
        budget = input_budget_characters(PRIMARY, ceiling)
        densest = min(_characters_per_token(document) for document in measured)
        request_characters = _fixed_prompt_characters() + budget + PAGE_FRAMING_ALLOWANCE_CHARACTERS
        input_usd = request_characters / densest * pin.input_per_mtok_usd / 1_000_000
        output_usd = AR_TEXT_PROMPT_BUNDLE.max_output_tokens * pin.output_per_mtok_usd / 1_000_000
        assert input_usd + output_usd < ceiling
        # And at the constant's own (kinder to the ceiling, harsher on the document) density
        # the same document lands on the ceiling to within the rounding of a character.
        assumed_usd = request_characters / float(CHARACTERS_PER_TOKEN) * pin.input_per_mtok_usd / 1e6
        assert abs(assumed_usd + output_usd - ceiling) < 0.001


class TestPypdfium2CountsTheTextThePromptIsBuiltFrom:
    def test_the_count_never_falls_below_the_text_layer_on_the_measured_documents(
        self, measured: list[dict[str, Any]]
    ) -> None:
        """pypdfium2 counts generated line breaks (two characters) where pdfplumber joins with one.

        Measured ratio 1.016 to 1.019 on the fifteen documents; the budget treats the two as
        equal, which is the safe side as long as the count is not the smaller one.
        """
        for document in measured:
            ratio = document["pdfium"] / document["plumber"]
            assert 1.0 <= ratio <= 1.05, f"{document['label']}: pdfium/pdfplumber is {ratio:.4f}"

    def test_the_framing_the_prompt_adds_is_the_pages_banners_and_one_preamble(
        self, measured: list[dict[str, Any]]
    ) -> None:
        for document in measured:
            framing = document["rendered"] - document["plumber"]
            assert 20 * document["pages"] < framing < 45 * document["pages"], document["label"]


class TestThePageFramingAllowanceCoversTheLargestDocumentTheEnvelopeAdmits:
    def test_the_framing_of_a_maximum_page_document_fits_the_allowance(self) -> None:
        pages = [
            {"page_number": number, "char_start": 0, "char_end": 0, "text": ""}
            for number in range(1, MAX_PAGES + 1)
        ]
        layer = load_text_layer(
            {
                "artifact_role": "prepared.text_layer",
                "artifact_version": "1.0.0",
                "normalization": {"id": "framing-probe"},
                "pages": pages,
                "version_uid": "ver_01M2FRWKW5Z4JK0M0K6PXGHDBT",
            }
        )
        framing = len(render_document(layer))
        assert framing <= PAGE_FRAMING_ALLOWANCE_CHARACTERS, (
            f"{MAX_PAGES} pages frame to {framing} characters; the allowance is "
            f"{PAGE_FRAMING_ALLOWANCE_CHARACTERS}"
        )
        # Not generously more than the need either: an allowance twice the framing would be
        # budget thrown away on pages that do not exist.
        assert framing >= 0.8 * PAGE_FRAMING_ALLOWANCE_CHARACTERS


class TestTheReferenceDocument:
    def test_the_default_budget_admits_the_thirty_page_ar_set_with_margin(self) -> None:
        ceiling = json.loads((REPO / "docs/program/P02_LOCK.json").read_text(encoding="utf-8"))[
            "models"
        ]["run_cost_ceiling_usd"]
        assert input_budget_characters(PRIMARY, ceiling) >= 1.5 * REFERENCE_DOCUMENT_CHARACTERS

    def test_the_cheapest_ceiling_that_admits_it_is_between_seventy_and_eighty_five_cents(self) -> None:
        """Pins where the start-up refusal bites for the primary model."""
        admitted = [
            cents / 100
            for cents in range(0, 200)
            if input_budget_characters(PRIMARY, cents / 100) >= REFERENCE_DOCUMENT_CHARACTERS
        ]
        assert 0.70 <= admitted[0] <= 0.85, admitted[0]
