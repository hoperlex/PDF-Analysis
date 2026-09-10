"""Fixtures for the decision-ledger suite.

The findings this suite judges are **really published**: they go through
``run_grounding_gate`` and ``publish_gate_result``, not through a hand-written INSERT.
A ledger tested against rows that never passed the gate would not have shown that a
decision can only target something grounded — which is the property that makes an
expert verdict mean anything.

The text layer here is small and hand-built rather than extracted from the corpus PDF:
this suite is about the ledger, and the corpus's job is done next door in
``tests/integration/findings``. It is Russian all the same, so an offset counted in
bytes would still land in the wrong place and be caught.

As next door: real PostgreSQL, never a skip, and isolation by rollback because the
ledger refuses DELETE with ``AM002`` — the very property under test.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Iterator
from typing import Any, Callable

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.findings import (
    BlockIndex,
    ObservationSet,
    TextLayer,
    publish_gate_result,
    run_grounding_gate,
)
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import (
    AnalysisProfileId,
    CommandId,
    DocumentUid,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)

#: Two short Russian pages. Every quotation below is non-ASCII, so a byte-counted
#: offset misplaces it exactly as it would on the real corpus.
PAGE_ONE = "Степень огнестойкости здания — II.\nВысота этажа 3,3 м.\n"
PAGE_TWO = "Степень огнестойкости здания — III.\nТип заполнения — уточнить.\n"


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        pytest.fail(
            "DATABASE_URL is not set. tests/integration/decisions runs against real "
            "PostgreSQL: the append-only triggers, the command_id unique index and the "
            "finding_current_verdict view are all database behaviour. This suite never "
            "skips — a skip would let the append-only claim go unchecked and look green."
        )
    settings = DatabaseSettings(url=parse_database_url(raw))
    built = create_database_engine(settings)
    try:
        with built.connect() as connection:
            present = connection.execute(
                text("SELECT to_regclass('public.finding_current_verdict')")
            ).scalar_one_or_none()
        if present is None:
            pytest.fail(
                "the configured database has no finding_current_verdict view. Run "
                "`make migrate` (or `make foundation`) for this lane first."
            )
        yield built
    finally:
        built.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """A unit of work that is always rolled back. The ledger cannot be cleaned up:
    DELETE on ``expert_decision_event`` raises ``AM002``, which is the point."""
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


def _text_layer_artifact() -> dict[str, Any]:
    pages = [PAGE_ONE, PAGE_TWO]
    entries = []
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
        "normalization": {"id": "nfc_v1", "description": "Unicode NFC."},
        "total_char_count": cursor,
        "pages": entries,
    }


@pytest.fixture(scope="session")
def text_layer() -> TextLayer:
    return TextLayer.from_artifact(_text_layer_artifact())


class PublishedRun:
    """One run with published findings, reached through the gate."""

    def __init__(self, session: Session, text_layer: TextLayer) -> None:
        self.session = session
        self.project_uid = ProjectUid.new().value
        self.document_uid = DocumentUid.new().value
        self.version_uid = VersionUid.new().value
        self.run_id = RunId.new().value
        self.analysis_profile_id = AnalysisProfileId.new().value
        self.prompt_bundle_id = PromptBundleId.new().value
        self.text_layer = text_layer
        self._seed()
        self.publication = self._publish()

    def _seed(self) -> None:
        digest = hashlib.sha256(self.run_id.encode("utf-8")).hexdigest()
        self.session.execute(
            text("INSERT INTO project (project_uid, name) VALUES (:p, 'Проект')"),
            {"p": self.project_uid},
        )
        self.session.execute(
            text(
                "INSERT INTO document (document_uid, project_uid, display_title) "
                "VALUES (:d, :p, 'АР')"
            ),
            {"d": self.document_uid, "p": self.project_uid},
        )
        self.session.execute(
            text(
                "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
                "media_type, byte_size, sha256, page_count) "
                "VALUES (:v, :d, 1, 'application/pdf', 1024, :s, 2)"
            ),
            {"v": self.version_uid, "d": self.document_uid, "s": digest},
        )
        self.session.execute(
            text(
                "INSERT INTO audit_run (run_id, project_uid, version_uid, state, "
                "analysis_profile_id, prompt_bundle_id, provider_mode, frozen_input_digest) "
                "VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :s)"
            ),
            {
                "r": self.run_id,
                "p": self.project_uid,
                "v": self.version_uid,
                "ap": self.analysis_profile_id,
                "pb": self.prompt_bundle_id,
                "s": digest,
            },
        )

    def _publish(self):
        quote_one = "Степень огнестойкости здания — II."
        quote_two = "Степень огнестойкости здания — III."
        page_two = self.text_layer.page(2)
        assert page_two is not None
        payload = {
            "artifact_role": "analysis.text_observations",
            "artifact_version": "1.0.0",
            "run_id": self.run_id,
            "stage_id": "text_analysis",
            "analysis_profile_id": self.analysis_profile_id,
            "prompt_bundle_id": self.prompt_bundle_id,
            "provider_mode": "recorded",
            "pages_analysed": [1, 2],
            "observations": [
                {
                    "observation_ordinal": 0,
                    "category": "internal_contradiction",
                    "finding_text": "Степень огнестойкости указана по-разному.",
                    "recommendation_text": "Согласовать степень огнестойкости.",
                    "evidence": [
                        {
                            "evidence_ordinal": 0,
                            "page_number": 1,
                            "quote": quote_one,
                            "char_start": 0,
                            "char_end": len(quote_one),
                        },
                        {
                            "evidence_ordinal": 1,
                            "page_number": 2,
                            "quote": quote_two,
                            "char_start": page_two.char_start,
                            "char_end": page_two.char_start + len(quote_two),
                        },
                    ],
                },
                {
                    "observation_ordinal": 1,
                    "category": "explicit_placeholder",
                    "finding_text": "Тип заполнения не определён.",
                    "recommendation_text": "Указать тип заполнения.",
                    "evidence": [
                        {
                            "evidence_ordinal": 0,
                            "page_number": 2,
                            "quote": "Тип заполнения — уточнить.",
                            "char_start": page_two.char_start + len(quote_two) + 1,
                            "char_end": page_two.char_start
                            + len(quote_two)
                            + 1
                            + len("Тип заполнения — уточнить."),
                        }
                    ],
                },
                {
                    # Deliberately ungrounded: the quotation is not in the document at
                    # all. It gives the suite a real diagnostic row to try to judge.
                    "observation_ordinal": 2,
                    "category": "internal_contradiction",
                    "finding_text": "Наблюдение без основания.",
                    "recommendation_text": "Ничего.",
                    "evidence": [
                        {
                            "evidence_ordinal": 0,
                            "page_number": 1,
                            "quote": "Степень огнестойкости здания — IV.",
                            "char_start": 0,
                            "char_end": len("Степень огнестойкости здания — IV."),
                        }
                    ],
                },
            ],
        }
        observation_set = ObservationSet.from_artifact(payload)
        result = run_grounding_gate(observation_set, self.text_layer, BlockIndex.empty())
        assert result.grounded_count == 2 and result.ungrounded_count == 1, (
            f"the suite's own fixture did not come out as intended: "
            f"{result.grounded_count} grounded, {result.reason_counts()}"
        )
        return publish_gate_result(
            self.session,
            gate_result=result,
            observation_set=observation_set,
            run_id=self.run_id,
            project_uid=self.project_uid,
            version_uid=self.version_uid,
        )

    @property
    def finding_uid(self) -> str:
        return self.publication.published[0].finding_uid

    @property
    def finding_observation_id(self) -> str:
        return self.publication.published[0].finding_observation_id

    @property
    def second_finding_uid(self) -> str:
        return self.publication.published[1].finding_uid

    @property
    def second_finding_observation_id(self) -> str:
        return self.publication.published[1].finding_observation_id

    @property
    def ungrounded_observation_id(self) -> str:
        """The diagnostic row: a real observation carrying no finding identity."""
        return self.publication.diagnostics[0].finding_observation_id


@pytest.fixture
def published(session: Session, text_layer: TextLayer) -> PublishedRun:
    return PublishedRun(session, text_layer)


@pytest.fixture
def command(session: Session) -> Callable[..., str]:
    """Create a command record, so an idempotent replay has a key to replay under."""

    def make(idempotency_key: str, command_type: str = "record_expert_decision") -> str:
        command_id = CommandId.new().value
        session.execute(
            text(
                "INSERT INTO command_record (command_id, command_type, idempotency_key, "
                "payload_fingerprint) VALUES (:c, :t, :k, :f)"
            ),
            {
                "c": command_id,
                "t": command_type,
                "k": idempotency_key,
                "f": hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest(),
            },
        )
        return command_id

    return make
