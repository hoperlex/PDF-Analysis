"""Fixtures for the grounding-gate suite.

Two things this file is careful about.

**The text layer is the real one.** It is extracted from the bytes of the committed
``fixtures/synthetic/ar/ar_baseline.pdf`` with ``tools/fixtures/ar_corpus/pdfextract``,
the extractor the corpus manifest's own ``page_text_sha256`` values were computed with,
and :func:`_assert_text_layer_is_the_corpus_one` checks every one of those digests
before a single test runs. So the sequence the gate resolves anchors against is the
corpus's declared text layer, character for character, and the manifest's
``char_offset_in_page_text`` values index straight into it. A gate proved against an
invented payload would prove nothing about the corpus every downstream measurement uses.

This is a *test* dependency on the fixture generator, not a second production extractor:
``B2`` owns ``prepared.text_layer`` and this suite consumes the shape §4.3 declares. The
sys.path insertion mirrors ``tests/contract/fixtures_ar``, which does the same thing for
the same reason — ``tools/fixtures`` is on no import path, and the root ``pyproject.toml``
that would put it there is a single-owner hotspot this session does not own.

**The database is real and the suite never skips.** A missing ``DATABASE_URL`` is a hard
failure. A skipped integration suite reports success while proving nothing, and the
constraints under test here — the ``grounded``/``finding_uid`` pairing, the append-only
triggers, the projection view — have no in-memory equivalent to fall back to.

Isolation is by rollback, not by cleanup. ``finding_observation`` refuses ``DELETE``
(SQLSTATE ``AM003``) and so does the ledger (``AM002``), which is exactly the property
the suite asserts; a fixture that tore rows down afterwards would have to defeat it.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import unicodedata
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Callable

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.findings import BlockIndex, ObservationSet, TextLayer
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    AnalysisProfileId,
    DocumentUid,
    ModelCallId,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = REPOSITORY_ROOT / "tools" / "fixtures"
CORPUS_DIR = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar"
BASELINE = CORPUS_DIR / "ar_baseline.pdf"
MANIFEST = CORPUS_DIR / "expected_issues.json"

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from ar_corpus import pdfextract  # noqa: E402

#: The one declared normalization (§4.3). Applied once, here, standing in for
#: ``source_preparation``. The gate applies none.
NORMALIZATION_ID = "nfc_v1"


# ---------------------------------------------------------------------------
# The corpus, as the three artifacts the gate consumes
# ---------------------------------------------------------------------------


def _page_texts() -> list[str]:
    pages = pdfextract.extract_pages(BASELINE.read_bytes())
    # NFC, once. The corpus is already NFC, so this changes nothing and is written
    # anyway: it is the declared normalization, and applying it here is what makes
    # "the gate does not normalize again" a statement about a real prior step.
    return [unicodedata.normalize("NFC", page) for page in pages]


def _assert_text_layer_is_the_corpus_one(pages: list[str], manifest: dict) -> None:
    declared = manifest["baseline"]["page_text_sha256"]
    if len(pages) != len(declared):
        pytest.fail(f"extracted {len(pages)} pages, the manifest declares {len(declared)}")
    for number, (page, digest) in enumerate(zip(pages, declared), start=1):
        actual = hashlib.sha256(page.encode("utf-8")).hexdigest()
        if actual != digest:
            pytest.fail(
                f"page {number} of the extracted text layer does not match the digest "
                f"the corpus manifest declares. The suite's anchors index a text layer "
                f"that is not the corpus's, so nothing it asserts about grounding would "
                f"be about the corpus. expected {digest}, got {actual}"
            )


def _text_layer_artifact(pages: list[str], version_uid: str) -> dict[str, Any]:
    """Build ``prepared.text_layer`` (§4.3) — contiguous, gapless, no separator."""
    entries: list[dict[str, Any]] = []
    cursor = 0
    for number, page in enumerate(pages, start=1):
        entries.append(
            {
                "page_number": number,
                "char_start": cursor,
                "char_end": cursor + len(page),
                "text": page,
            }
        )
        cursor += len(page)
    return {
        "artifact_role": "prepared.text_layer",
        "artifact_version": "1.0.0",
        "version_uid": version_uid,
        "extractor": {
            "name": "ar_corpus.pdfextract",
            "version": "fixture",
            "options_sha256": hashlib.sha256(b"ar_corpus.pdfextract").hexdigest(),
        },
        "normalization": {
            "id": NORMALIZATION_ID,
            "description": (
                "Unicode NFC. No case folding, no whitespace collapsing, no punctuation "
                "substitution and no line-ending rewriting beyond the extractor's own output."
            ),
        },
        "total_char_count": cursor,
        "pages": entries,
    }


def _block_index_artifact(pages: list[str], version_uid: str) -> dict[str, Any]:
    """Build ``geometry.block_index`` (§4.4): one block per rendered line.

    A line is the right granularity here because the corpus guarantees every quotation
    lies wholly within one rendered line, so a correct anchor is inside exactly one
    block and the ``span_outside_block`` case has to be constructed deliberately rather
    than happening by accident. ``block_id`` is assigned in ``(page_number,
    block_ordinal)`` order across the whole document, starting at ``b_000001``, as §4.4
    requires. The newline between lines belongs to no block, which is what makes a
    two-line span fail check 3 instead of quietly passing.
    """
    blocks: list[dict[str, Any]] = []
    page_start = 0
    counter = 0
    for number, page in enumerate(pages, start=1):
        offset = 0
        for ordinal, line in enumerate(page.split("\n")):
            counter += 1
            blocks.append(
                {
                    "block_id": f"b_{counter:06d}",
                    "page_number": number,
                    "block_ordinal": ordinal,
                    "bbox": {"x0": 56.7, "y0": 70.9, "x1": 538.6, "y1": 118.4},
                    "bbox_unit": "pt",
                    "bbox_origin": "top_left",
                    "char_start": page_start + offset,
                    "char_end": page_start + offset + len(line),
                }
            )
            offset += len(line) + 1  # the newline separating this line from the next
        page_start += len(page)
    return {
        "artifact_role": "geometry.block_index",
        "artifact_version": "1.0.0",
        "version_uid": version_uid,
        "text_layer_sha256": hashlib.sha256("".join(pages).encode("utf-8")).hexdigest(),
        "blocks": blocks,
    }


class Corpus:
    """The corpus as the gate sees it, plus the manifest that says what is true."""

    def __init__(self, version_uid: str) -> None:
        self.manifest: dict = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.pages = _page_texts()
        _assert_text_layer_is_the_corpus_one(self.pages, self.manifest)
        self.text_layer_artifact = _text_layer_artifact(self.pages, version_uid)
        self.block_index_artifact = _block_index_artifact(self.pages, version_uid)
        self.text_layer = TextLayer.from_artifact(self.text_layer_artifact)
        self.block_index = BlockIndex.from_artifact(self.block_index_artifact)

    # -- offsets ----------------------------------------------------------------
    def page_start(self, page_number: int) -> int:
        page = self.text_layer.page(page_number)
        assert page is not None, f"page {page_number} is not in the text layer"
        return page.char_start

    def page_end(self, page_number: int) -> int:
        page = self.text_layer.page(page_number)
        assert page is not None
        return page.char_end

    def block_containing(self, char_start: int, char_end: int) -> str | None:
        for block in self.block_index:
            if block.contains(char_start, char_end):
                return block.block_id
        return None

    def block_after(self, block_id: str) -> str:
        ids = [block.block_id for block in self.block_index]
        position = ids.index(block_id)
        return ids[(position + 1) % len(ids)]

    # -- anchors from the manifest ----------------------------------------------
    def seeded_anchors(self) -> list[dict[str, Any]]:
        """Every seeded-issue quotation, as a grounded evidence item.

        The offsets come from the manifest's own ``char_offset_in_page_text`` plus the
        page's start in the document-global sequence. They are not searched for: an
        anchor the suite discovered by scanning would test the scanner, not the gate.
        """
        anchors: list[dict[str, Any]] = []
        for issue in self.manifest["seeded_issues"]:
            for item in issue["evidence"]:
                page_number = item["page"]
                quote = item["quotation"]
                char_start = self.page_start(page_number) + item["char_offset_in_page_text"]
                char_end = char_start + len(quote)
                anchors.append(
                    {
                        "issue_id": issue["id"],
                        "category": issue["category"],
                        "page_number": page_number,
                        "quote": quote,
                        "char_start": char_start,
                        "char_end": char_end,
                        "block_id": self.block_containing(char_start, char_end),
                        "summary_ru": issue["summary_ru"],
                    }
                )
        return anchors

    def control_anchors(self) -> list[dict[str, Any]]:
        """The six controls, as anchors. A control is a statement a correct analyzer
        must not report; it is nonetheless really in the text, so an anchor on one is
        *grounded*. Grounding is about the quotation resolving, never about whether
        reporting it was a good idea — that is precision, and a different measurement."""
        anchors: list[dict[str, Any]] = []
        for control in self.manifest["controls"]:
            quote = control["quotation"]
            for page_number in control.get("pages", []):
                page_text = self.pages[page_number - 1]
                offset = page_text.find(quote)
                if offset < 0:
                    pytest.fail(
                        f"control {control['id']} is not on its declared page {page_number}"
                    )
                char_start = self.page_start(page_number) + offset
                anchors.append(
                    {
                        "control_id": control["id"],
                        "page_number": page_number,
                        "quote": quote,
                        "char_start": char_start,
                        "char_end": char_start + len(quote),
                        "block_id": self.block_containing(char_start, char_start + len(quote)),
                    }
                )
        return anchors


# ---------------------------------------------------------------------------
# Observation artifacts
# ---------------------------------------------------------------------------


def build_observations_artifact(
    items: list[dict[str, Any]],
    *,
    run_id: str,
    analysis_profile_id: str,
    prompt_bundle_id: str,
    provider_mode: str = "recorded",
    pages_analysed: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8),
    stage_id: str = "text_analysis",
) -> dict[str, Any]:
    """Assemble ``analysis.text_observations`` (§4.7) from evidence specs.

    Each item is ``{"category", "finding_text", "recommendation_text", "evidence": [...]}``
    where every evidence entry is a raw anchor dict. Nothing here is normalized or
    corrected: the whole point is to hand the gate exactly what a model declared,
    including when that is wrong.
    """
    observations = []
    for ordinal, item in enumerate(items):
        evidence = []
        for index, anchor in enumerate(item["evidence"]):
            entry = {
                "evidence_ordinal": index,
                "page_number": anchor["page_number"],
                "quote": anchor["quote"],
                "char_start": anchor["char_start"],
                "char_end": anchor["char_end"],
            }
            if anchor.get("block_id") is not None:
                entry["block_id"] = anchor["block_id"]
            evidence.append(entry)
        observations.append(
            {
                "observation_ordinal": ordinal,
                "category": item["category"],
                "finding_text": item["finding_text"],
                "recommendation_text": item.get(
                    "recommendation_text", "Согласовать значения между разделами."
                ),
                "model_call_id": item.get("model_call_id"),
                "evidence": evidence,
            }
        )
    return {
        "artifact_role": "analysis.text_observations",
        "artifact_version": "1.0.0",
        "run_id": run_id,
        "stage_id": stage_id,
        "analysis_profile_id": analysis_profile_id,
        "prompt_bundle_id": prompt_bundle_id,
        "provider_mode": provider_mode,
        "pages_analysed": list(pages_analysed),
        "observations": observations,
    }


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail(
            "DATABASE_URL is not set. tests/integration/findings runs against real "
            "PostgreSQL: the grounded/finding_uid pairing, the immutability triggers "
            "and the projection view are all database behaviour with no in-memory "
            "equivalent. This suite never skips."
        )
    settings = DatabaseSettings(url=parse_database_url(raw))
    built = create_database_engine(settings)
    try:
        with built.connect() as connection:
            present = connection.execute(
                text("SELECT to_regclass('public.finding_observation')")
            ).scalar_one_or_none()
        if present is None:
            pytest.fail(
                "the configured database has no finding_observation table. Run "
                "`make migrate` (or `make foundation`) for this lane first; this suite "
                "asserts on the migrated schema and does not create it."
            )
        yield built
    finally:
        built.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """One unit of work on a transaction that is always rolled back.

    Rollback rather than cleanup, because the rows this suite writes cannot be deleted:
    ``finding_observation`` refuses DELETE with ``AM003`` and the ledger with ``AM002``.
    That refusal is under test, so the fixture must not be built on defeating it.
    """
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False, future=True)
    opened = factory()
    try:
        yield opened
    finally:
        opened.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="session")
def version_uid() -> str:
    return VersionUid.new().value


@pytest.fixture(scope="session")
def corpus(version_uid: str) -> Corpus:
    return Corpus(version_uid)


@pytest.fixture(scope="session")
def text_layer(corpus: Corpus) -> TextLayer:
    return corpus.text_layer


@pytest.fixture(scope="session")
def block_index(corpus: Corpus) -> BlockIndex:
    return corpus.block_index


class SeededRun:
    """The rows a finding needs to exist at all: project, document, version, run."""

    def __init__(
        self, session: Session, version_uid: str, reuse: "SeededRun | None" = None
    ) -> None:
        self.session = session
        self.version_uid = version_uid
        self.run_id = RunId.new().value
        self.analysis_profile_id = AnalysisProfileId.new().value
        self.prompt_bundle_id = PromptBundleId.new().value
        self.model_call_id = ModelCallId.new().value
        if reuse is None:
            self.project_uid = ProjectUid.new().value
            self.document_uid = DocumentUid.new().value
            self._insert_document()
        else:
            # A rerun is a second run over the *same* published version: the document
            # and the version are immutable and are never re-created for it.
            self.project_uid = reuse.project_uid
            self.document_uid = reuse.document_uid
        self._insert_run()

    def _insert_document(self) -> None:
        self.session.execute(
            text(
                "INSERT INTO project (project_uid, name) VALUES (:uid, :name)"
            ),
            {"uid": self.project_uid, "name": "Синтетический проект"},
        )
        self.session.execute(
            text(
                "INSERT INTO document (document_uid, project_uid, display_title) "
                "VALUES (:doc, :prj, :title)"
            ),
            {"doc": self.document_uid, "prj": self.project_uid, "title": "СП-7-АР"},
        )
        self.session.execute(
            text(
                "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
                "media_type, byte_size, sha256, page_count) "
                "VALUES (:ver, :doc, 1, 'application/pdf', :size, :sha, 8)"
            ),
            {
                "ver": self.version_uid,
                "doc": self.document_uid,
                "size": BASELINE.stat().st_size,
                "sha": hashlib.sha256(BASELINE.read_bytes()).hexdigest(),
            },
        )

    def _insert_run(self) -> None:
        digest = hashlib.sha256(self.run_id.encode("utf-8")).hexdigest()
        self.session.execute(
            text(
                "INSERT INTO audit_run (run_id, project_uid, version_uid, state, "
                "analysis_profile_id, prompt_bundle_id, provider_mode, frozen_input_digest) "
                "VALUES (:run, :prj, :ver, 'created', :ap, :pb, 'recorded', :digest)"
            ),
            {
                "run": self.run_id,
                "prj": self.project_uid,
                "ver": self.version_uid,
                "ap": self.analysis_profile_id,
                "pb": self.prompt_bundle_id,
                "digest": digest,
            },
        )
        self.session.execute(
            text(
                "INSERT INTO model_call (model_call_id, run_id, stage_id, provider, "
                "model_identity, provider_mode, request_sha256, response_sha256, status) "
                "VALUES (:mc, :run, 'text_analysis', 'anthropic', 'recorded-fixture', "
                "'recorded', :req, :resp, 'succeeded')"
            ),
            {
                "mc": self.model_call_id,
                "run": self.run_id,
                "req": digest,
                "resp": digest,
            },
        )

    def advance_to(self, state: str) -> None:
        """Walk the declared audit_run topology to ``state``.

        Each hop is a real UPDATE against the state-guard trigger, so a path the
        contract does not declare fails here rather than being assumed.
        """
        path = {
            "queued": ("queued",),
            "running": ("queued", "running"),
            "validating": ("queued", "running", "validating"),
        }[state]
        for target in path:
            self.session.execute(
                text("UPDATE audit_run SET state = :state WHERE run_id = :run"),
                {"state": target, "run": self.run_id},
            )

    def terminate(self, selection) -> None:  # noqa: ANN001 - findings.TerminalSelection
        self.session.execute(
            text(
                "UPDATE audit_run SET state = :state, terminal_at = now(), "
                "terminal_reason = :reason, degradation_set = CAST(:degraded AS jsonb) "
                "WHERE run_id = :run"
            ),
            {
                "state": selection.state,
                "reason": selection.terminal_reason,
                "degraded": json.dumps(list(selection.degradation_set)),
                "run": self.run_id,
            },
        )

    def state(self) -> str:
        return self.session.execute(
            text("SELECT state FROM audit_run WHERE run_id = :run"), {"run": self.run_id}
        ).scalar_one()


@pytest.fixture
def seeded_factory(session: Session, version_uid: str) -> Callable[[], SeededRun]:
    """Seed another run over the *same* document version.

    A rerun is a second run over one version, so the version identity is shared and
    everything else is fresh. That is what makes the disjoint-``finding_uid`` assertion
    about identity allocation rather than about two unrelated documents.
    """

    def make(reuse: SeededRun | None = None) -> SeededRun:
        return SeededRun(session, version_uid, reuse)

    return make


@pytest.fixture
def seeded(seeded_factory: Callable[[], SeededRun]) -> SeededRun:
    return seeded_factory()


def observations_for(run: SeededRun, items: list[dict[str, Any]], **kwargs: Any) -> ObservationSet:
    """Build an ``ObservationSet`` naming one seeded run."""
    payload = build_observations_artifact(
        items,
        run_id=run.run_id,
        analysis_profile_id=run.analysis_profile_id,
        prompt_bundle_id=run.prompt_bundle_id,
        **kwargs,
    )
    return ObservationSet.from_artifact(payload)


@pytest.fixture
def make_observations(seeded: SeededRun) -> Callable[..., ObservationSet]:
    """Build an ``ObservationSet`` for this run from evidence specs."""

    def build(items: list[dict[str, Any]], **kwargs: Any) -> ObservationSet:
        return observations_for(seeded, items, **kwargs)

    return build


@pytest.fixture
def observations_builder() -> Callable[..., ObservationSet]:
    """The same builder, for a run the test seeded itself."""
    return observations_for
