"""The grounding gate against the real corpus, and against it perturbed.

Every ungrounded case here is built by perturbing a quotation that genuinely resolves,
so each test knows exactly what it broke and which of the five reasons that should
produce. An ungrounded fixture invented from nothing would prove only that the gate
rejects nonsense; these prove it rejects a *plausible* anchor — the one-character
change, the shifted offset, the right quotation on the wrong page — which is the only
kind a model actually produces.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from auditmanager.findings import (
    UNGROUNDED_REASONS,
    UngroundedReason,
    diagnostics,
    evidence_resolves,
    publish_gate_result,
    published_finding_count,
    published_finding_evidence,
    published_findings,
    run_grounding_gate,
)
from auditmanager.shared.db import nested_transaction
from auditmanager.shared.identity import FindingObservationId, FindingUid


def _observation(anchors, *, category="internal_contradiction", finding_text="Расхождение."):
    return {
        "category": category,
        "finding_text": finding_text,
        "recommendation_text": "Согласовать значения между разделами.",
        "evidence": anchors,
    }


def _reason_of(gate_result, ordinal=0):
    verdict = gate_result.verdicts[ordinal]
    assert not verdict.grounded, "the perturbation did not make the observation ungrounded"
    return verdict.reason


# ---------------------------------------------------------------------------
# The text layer the gate resolves against
# ---------------------------------------------------------------------------


class TestTheTextLayerIsTheCorpusOne:
    def test_offsets_are_code_points_and_not_bytes(self, corpus, text_layer) -> None:
        """The single most expensive mistake in §4.1, made checkable.

        The corpus is Russian, so the byte length of the document is far larger than its
        code-point length. If these two numbers were equal the whole suite would be
        blind to a byte-offset implementation, because every anchor would happen to land
        in the same place.
        """
        code_points = text_layer.total_char_count
        byte_length = len(text_layer.sequence.encode("utf-8"))
        assert byte_length > code_points, (
            "the corpus must contain non-ASCII text for a byte-offset bug to be "
            "detectable at all"
        )
        assert code_points == sum(len(page) for page in corpus.pages)

    def test_pages_are_contiguous_gapless_and_unseparated(self, text_layer, corpus) -> None:
        pages = text_layer.pages
        assert pages[0].char_start == 0
        for previous, page in zip(pages, pages[1:]):
            assert page.char_start == previous.char_end, "a gap or a separator between pages"
        assert pages[-1].char_end == text_layer.total_char_count
        assert text_layer.sequence == "".join(corpus.pages)

    def test_the_declared_normalization_is_named_once(self, text_layer) -> None:
        assert text_layer.normalization_id == "nfc_v1"


# ---------------------------------------------------------------------------
# The corpus grounds
# ---------------------------------------------------------------------------


class TestTheSeededIssuesGround:
    def test_every_seeded_quotation_resolves_at_its_manifest_anchor(
        self, corpus, text_layer, block_index, make_observations
    ) -> None:
        anchors = corpus.seeded_anchors()
        assert len(anchors) == 5, "three seeded issues, five quotations"
        observations = make_observations(
            [_observation([anchor], category=anchor["category"]) for anchor in anchors]
        )
        result = run_grounding_gate(observations, text_layer, block_index)
        assert result.ungrounded_count == 0, result.reason_counts()
        assert result.grounded_count == len(anchors)

    def test_a_recorded_run_publishes_both_contradictions_and_the_placeholder(
        self, session: Session, seeded, corpus, text_layer, block_index, make_observations
    ) -> None:
        by_issue: dict[str, list] = {}
        for anchor in corpus.seeded_anchors():
            by_issue.setdefault(anchor["issue_id"], []).append(anchor)

        items = [
            _observation(
                anchors,
                category=anchors[0]["category"],
                finding_text=anchors[0]["summary_ru"],
            )
            for anchors in by_issue.values()
        ]
        observations = make_observations(items)

        seeded.advance_to("validating")
        result = run_grounding_gate(observations, text_layer, block_index)
        publication = publish_gate_result(
            session,
            gate_result=result,
            observation_set=observations,
            run_id=seeded.run_id,
            project_uid=seeded.project_uid,
            version_uid=seeded.version_uid,
            model_call_ids={ordinal: seeded.model_call_id for ordinal in range(len(items))},
        )

        assert publication.published_count == 3
        assert publication.diagnostic_count == 0

        rows = published_findings(session, seeded.run_id)
        assert len(rows) == 3
        categories = sorted(row.category for row in rows)
        assert categories == [
            "explicit_placeholder",
            "internal_contradiction",
            "internal_contradiction",
        ]

        # Pages match the manifest, which is the acceptance oracle.
        evidence = published_finding_evidence(session, seeded.run_id)
        pages_by_observation: dict[str, set[int]] = {}
        for row in evidence:
            pages_by_observation.setdefault(row.finding_observation_id, set()).add(
                row.page_number
            )
        assert sorted(sorted(pages) for pages in pages_by_observation.values()) == [
            [2, 6],
            [3, 7],
            [8],
        ]

        # And every stored anchor still resolves when re-read from the database.
        page_intervals = [
            (page.page_number, page.char_start, page.char_end) for page in text_layer.pages
        ]
        assert (
            evidence_resolves(session, seeded.run_id, text_layer.sequence, page_intervals)
            == ()
        ), "a published evidence row does not resolve; the gate let something through"

    def test_provenance_travels_with_the_published_finding(
        self, session: Session, seeded, corpus, text_layer, block_index, make_observations
    ) -> None:
        anchor = corpus.seeded_anchors()[0]
        observations = make_observations([_observation([anchor], category=anchor["category"])])
        result = run_grounding_gate(observations, text_layer, block_index)
        publish_gate_result(
            session,
            gate_result=result,
            observation_set=observations,
            run_id=seeded.run_id,
            project_uid=seeded.project_uid,
            version_uid=seeded.version_uid,
            model_call_ids={0: seeded.model_call_id},
        )
        row = published_findings(session, seeded.run_id)[0]
        assert row.stage_id == "text_analysis"
        assert row.analysis_profile_id == seeded.analysis_profile_id
        assert row.prompt_bundle_id == seeded.prompt_bundle_id
        assert row.model_call_id == seeded.model_call_id
        assert row.provider_mode == "recorded", (
            "provider_mode is what makes a live run distinguishable from a recorded one"
        )


class TestControls:
    def test_a_control_statement_is_not_among_the_published_findings(
        self, session: Session, seeded, corpus, text_layer, block_index, make_observations
    ) -> None:
        """The run reports the seeded issues; no control quotation reaches a finding."""
        anchors = corpus.seeded_anchors()
        observations = make_observations(
            [_observation([anchor], category=anchor["category"]) for anchor in anchors]
        )
        result = run_grounding_gate(observations, text_layer, block_index)
        publish_gate_result(
            session,
            gate_result=result,
            observation_set=observations,
            run_id=seeded.run_id,
            project_uid=seeded.project_uid,
            version_uid=seeded.version_uid,
        )
        published_quotes = {row.quote for row in published_finding_evidence(session, seeded.run_id)}
        control_quotes = {anchor["quote"] for anchor in corpus.control_anchors()}
        assert published_quotes & control_quotes == set()

    def test_a_control_anchor_would_nonetheless_ground(
        self, corpus, text_layer, block_index, make_observations
    ) -> None:
        """Written down so nobody mistakes this gate for a precision filter.

        A control really is in the document, so an anchor on one resolves and the gate
        publishes it. Whether reporting it was *right* is precision, measured against
        the manifest's controls by a different suite. Confusing the two would let a
        change that quietly dropped controls look like a grounding improvement.
        """
        anchors = corpus.control_anchors()
        assert anchors, "the manifest declares controls"
        observations = make_observations([_observation([anchor]) for anchor in anchors])
        result = run_grounding_gate(observations, text_layer, block_index)
        assert result.ungrounded_count == 0, result.reason_counts()


# ---------------------------------------------------------------------------
# The five reasons, one perturbation each
# ---------------------------------------------------------------------------


class TestEachUngroundedReasonIsProducedByAPerturbation:
    def test_quotation_absent_from_a_one_character_change(
        self, corpus, text_layer, block_index, make_observations
    ) -> None:
        """One Cyrillic letter swapped for a Latin look-alike of the same length.

        The anchor is otherwise perfect: right page, right offsets, right length. This
        is the case a normalizing gate would wave through, and the reason this module
        compares with ``==`` and nothing else.
        """
        anchor = dict(corpus.seeded_anchors()[0])
        original = anchor["quote"]
        perturbed = original.replace("е", "e", 1)  # Cyrillic е -> Latin e
        assert perturbed != original and len(perturbed) == len(original)
        anchor["quote"] = perturbed
        result = run_grounding_gate(
            make_observations([_observation([anchor])]), text_layer, block_index
        )
        assert _reason_of(result) is UngroundedReason.QUOTATION_ABSENT

    def test_quotation_absent_from_a_shifted_offset(
        self, corpus, text_layer, block_index, make_observations
    ) -> None:
        """The quotation is real and on the declared page — the offsets are not."""
        anchor = dict(corpus.seeded_anchors()[0])
        anchor["char_start"] += 3
        anchor["char_end"] += 3
        anchor["block_id"] = None
        result = run_grounding_gate(
            make_observations([_observation([anchor])]), text_layer, block_index
        )
        assert _reason_of(result) is UngroundedReason.QUOTATION_ABSENT

    def test_quotation_on_different_page_from_the_right_quote_on_the_wrong_page(
        self, corpus, text_layer, block_index, make_observations
    ) -> None:
        """SI-01's page-6 quotation, declared on page 2 with a page-2 offset.

        Both pages carry a fire-resistance statement, which is exactly why a model gets
        this wrong. The quotation exists; it is simply not where the model said.
        """
        anchors = corpus.seeded_anchors()
        page_two = next(a for a in anchors if a["issue_id"] == "SI-01" and a["page_number"] == 2)
        page_six = next(a for a in anchors if a["issue_id"] == "SI-01" and a["page_number"] == 6)
        quote = page_six["quote"]
        perturbed = {
            "page_number": 2,
            "quote": quote,
            "char_start": page_two["char_start"],
            "char_end": page_two["char_start"] + len(quote),
            "block_id": None,
        }
        result = run_grounding_gate(
            make_observations([_observation([perturbed])]), text_layer, block_index
        )
        assert _reason_of(result) is UngroundedReason.QUOTATION_ON_DIFFERENT_PAGE
        assert text_layer.pages_containing(quote) == (6,)

    def test_span_outside_page_from_a_span_crossing_a_page_boundary(
        self, text_layer, make_observations, block_index
    ) -> None:
        """A span that starts on page 2 and runs into page 3.

        The quotation is genuinely at those offsets in the document-global sequence —
        the concatenation is one string, so a crossing span slices cleanly. It still
        belongs to no page, and check 1 is what notices.
        """
        page_two = text_layer.page(2)
        boundary = page_two.char_end
        char_start = boundary - 12
        char_end = boundary + 12
        quote = text_layer.slice(char_start, char_end)
        assert len(quote) == char_end - char_start
        assert text_layer.sequence[char_start:char_end] == quote, (
            "the span really does slice to the quote; only the page ownership is wrong"
        )
        perturbed = {
            "page_number": 2,
            "quote": quote,
            "char_start": char_start,
            "char_end": char_end,
            "block_id": None,
        }
        result = run_grounding_gate(
            make_observations([_observation([perturbed])]), text_layer, block_index
        )
        assert _reason_of(result) is UngroundedReason.SPAN_OUTSIDE_PAGE

    def test_span_outside_page_from_a_page_the_document_does_not_have(
        self, corpus, text_layer, block_index, make_observations
    ) -> None:
        anchor = dict(corpus.seeded_anchors()[0])
        anchor["page_number"] = 99
        anchor["block_id"] = None
        result = run_grounding_gate(
            make_observations([_observation([anchor])]), text_layer, block_index
        )
        assert _reason_of(result) is UngroundedReason.SPAN_OUTSIDE_PAGE

    def test_span_length_mismatch_from_a_byte_length_span(
        self, corpus, text_layer, block_index, make_observations
    ) -> None:
        """The byte-offset bug, made into a test.

        ``char_end`` is computed as ``char_start + len(quote.encode('utf-8'))`` — what a
        byte-counting implementation produces. On Russian text that is nearly twice the
        code-point length, so the gate sees a span that cannot possibly hold the quote.
        """
        anchor = dict(corpus.seeded_anchors()[0])
        byte_length = len(anchor["quote"].encode("utf-8"))
        assert byte_length > len(anchor["quote"]), "the quotation must be non-ASCII"
        anchor["char_end"] = anchor["char_start"] + byte_length
        anchor["block_id"] = None
        result = run_grounding_gate(
            make_observations([_observation([anchor])]), text_layer, block_index
        )
        assert _reason_of(result) is UngroundedReason.SPAN_LENGTH_MISMATCH

    def test_span_length_mismatch_from_a_one_character_longer_span(
        self, corpus, text_layer, block_index, make_observations
    ) -> None:
        anchor = dict(corpus.seeded_anchors()[0])
        anchor["char_end"] += 1
        anchor["block_id"] = None
        result = run_grounding_gate(
            make_observations([_observation([anchor])]), text_layer, block_index
        )
        assert _reason_of(result) is UngroundedReason.SPAN_LENGTH_MISMATCH

    def test_span_outside_block_from_the_neighbouring_block(
        self, corpus, text_layer, block_index, make_observations
    ) -> None:
        """Page and quotation both correct; only the declared block is wrong."""
        anchor = dict(corpus.seeded_anchors()[0])
        assert anchor["block_id"] is not None, "the anchor must declare a block to fail check 3"
        anchor["block_id"] = corpus.block_after(anchor["block_id"])
        result = run_grounding_gate(
            make_observations([_observation([anchor])]), text_layer, block_index
        )
        assert _reason_of(result) is UngroundedReason.SPAN_OUTSIDE_BLOCK

    def test_span_outside_block_from_a_block_the_index_does_not_carry(
        self, corpus, text_layer, block_index, make_observations
    ) -> None:
        anchor = dict(corpus.seeded_anchors()[0])
        anchor["block_id"] = "b_999999"
        result = run_grounding_gate(
            make_observations([_observation([anchor])]), text_layer, block_index
        )
        assert _reason_of(result) is UngroundedReason.SPAN_OUTSIDE_BLOCK

    def test_all_five_reasons_are_reachable_and_the_vocabulary_is_closed(
        self, corpus, text_layer, block_index, make_observations
    ) -> None:
        """The five perturbations in one gate run, so the mapping is asserted together
        rather than one reason at a time in isolation."""
        anchors = corpus.seeded_anchors()
        base = anchors[0]
        page_six = next(a for a in anchors if a["issue_id"] == "SI-01" and a["page_number"] == 6)
        page_two = next(a for a in anchors if a["issue_id"] == "SI-01" and a["page_number"] == 2)
        boundary = text_layer.page(2).char_end

        absent = dict(base)
        absent["quote"] = base["quote"].replace("е", "e", 1)

        different_page = {
            "page_number": 2,
            "quote": page_six["quote"],
            "char_start": page_two["char_start"],
            "char_end": page_two["char_start"] + len(page_six["quote"]),
            "block_id": None,
        }

        crossing_quote = text_layer.slice(boundary - 12, boundary + 12)
        outside_page = {
            "page_number": 2,
            "quote": crossing_quote,
            "char_start": boundary - 12,
            "char_end": boundary + 12,
            "block_id": None,
        }

        length_mismatch = dict(base)
        length_mismatch["char_end"] = base["char_start"] + len(base["quote"].encode("utf-8"))
        length_mismatch["block_id"] = None

        outside_block = dict(base)
        outside_block["block_id"] = corpus.block_after(base["block_id"])

        observations = make_observations(
            [
                _observation([absent]),
                _observation([different_page]),
                _observation([outside_page]),
                _observation([length_mismatch]),
                _observation([outside_block]),
            ]
        )
        result = run_grounding_gate(observations, text_layer, block_index)
        assert result.grounded_count == 0
        assert result.reason_counts() == {
            "quotation_absent": 1,
            "quotation_on_different_page": 1,
            "span_outside_page": 1,
            "span_length_mismatch": 1,
            "span_outside_block": 1,
        }
        assert set(result.reason_counts()) == UNGROUNDED_REASONS


# ---------------------------------------------------------------------------
# One bad item rejects the whole observation
# ---------------------------------------------------------------------------


class TestEveryEvidenceItemMustResolve:
    def test_one_ungrounded_item_rejects_the_observation(
        self, corpus, text_layer, block_index, make_observations
    ) -> None:
        """§5.1 says *every* item must resolve. A finding whose second quotation is
        invented is not half-true: for a cross-page contradiction the second anchor is
        the entire claim."""
        anchors = [dict(a) for a in corpus.seeded_anchors() if a["issue_id"] == "SI-01"]
        assert len(anchors) == 2
        anchors[1]["quote"] = anchors[1]["quote"].replace("е", "e", 1)
        result = run_grounding_gate(
            make_observations([_observation(anchors)]), text_layer, block_index
        )
        verdict = result.verdicts[0]
        assert not verdict.grounded
        assert verdict.evidence_verdicts[0].resolved is True
        assert verdict.evidence_verdicts[1].resolved is False
        assert verdict.reason is UngroundedReason.QUOTATION_ABSENT
        assert verdict.failing_evidence_ordinal == 1


# ---------------------------------------------------------------------------
# What reaches the database
# ---------------------------------------------------------------------------


class TestAnUngroundedObservationIsCountedNowhere:
    def test_it_appears_in_no_finding_query(
        self, session: Session, seeded, corpus, text_layer, block_index, make_observations
    ) -> None:
        """Proved by querying a real database, not by reading the query text."""
        good = corpus.seeded_anchors()[0]
        bad = dict(good)
        bad["quote"] = good["quote"].replace("е", "e", 1)

        observations = make_observations(
            [
                _observation([good], finding_text="Обоснованное наблюдение."),
                _observation([bad], finding_text="Необоснованное наблюдение."),
            ]
        )
        seeded.advance_to("validating")
        result = run_grounding_gate(observations, text_layer, block_index)
        publication = publish_gate_result(
            session,
            gate_result=result,
            observation_set=observations,
            run_id=seeded.run_id,
            project_uid=seeded.project_uid,
            version_uid=seeded.version_uid,
        )

        assert publication.published_count == 1
        assert publication.diagnostic_count == 1
        rejected = publication.diagnostics[0].finding_observation_id

        # It is in no finding query.
        assert published_finding_count(session, seeded.run_id) == 1
        assert rejected not in {row.finding_observation_id for row in published_findings(session, seeded.run_id)}
        assert rejected not in {
            row.finding_observation_id for row in published_finding_evidence(session, seeded.run_id)
        }

        # It carries no finding identity and no evidence rows at all.
        row = session.execute(
            text(
                "SELECT finding_uid, grounded, ungrounded_reason FROM finding_observation "
                "WHERE finding_observation_id = :id"
            ),
            {"id": rejected},
        ).mappings().one()
        assert row["finding_uid"] is None
        assert row["grounded"] is False
        assert row["ungrounded_reason"] == "quotation_absent"
        assert (
            session.execute(
                text(
                    "SELECT count(*) FROM finding_evidence "
                    "WHERE finding_observation_id = :id"
                ),
                {"id": rejected},
            ).scalar_one()
            == 0
        )

        # No finding row was allocated for it: the run allocated exactly one.
        assert (
            session.execute(
                text("SELECT count(*) FROM finding WHERE allocated_by_run_id = :run"),
                {"run": seeded.run_id},
            ).scalar_one()
            == 1
        )

        # It is retained as a diagnostic, which is the whole of its afterlife.
        retained = diagnostics(session, seeded.run_id)
        assert [entry.finding_observation_id for entry in retained] == [rejected]
        assert retained[0].ungrounded_reason == "quotation_absent"

    def test_it_reduces_the_published_count(
        self, session: Session, seeded, corpus, text_layer, block_index, make_observations
    ) -> None:
        anchors = corpus.seeded_anchors()
        clean = make_observations([_observation([a]) for a in anchors])
        clean_result = run_grounding_gate(clean, text_layer, block_index)
        assert clean_result.grounded_count == len(anchors)

        perturbed_anchors = [dict(a) for a in anchors]
        perturbed_anchors[0]["quote"] = perturbed_anchors[0]["quote"].replace("е", "e", 1)
        perturbed_anchors[1]["char_end"] += 1
        perturbed = make_observations([_observation([a]) for a in perturbed_anchors])

        seeded.advance_to("validating")
        result = run_grounding_gate(perturbed, text_layer, block_index)
        publish_gate_result(
            session,
            gate_result=result,
            observation_set=perturbed,
            run_id=seeded.run_id,
            project_uid=seeded.project_uid,
            version_uid=seeded.version_uid,
        )
        assert published_finding_count(session, seeded.run_id) == len(anchors) - 2
        assert len(diagnostics(session, seeded.run_id)) == 2


class TestTheDatabaseEnforcesThePairing:
    """The pairing is a CHECK constraint, not a Python assertion.

    Each attempt runs inside a savepoint, so a refusal discards only the attempt and the
    rows the fixture seeded survive for the next one. Rolling the whole unit of work
    back instead would leave a later statement matching nothing — and a statement that
    matches nothing cannot be refused, which is how a test like this passes while
    proving the opposite of what it claims.
    """

    def test_a_grounded_row_without_a_finding_uid_is_refused(
        self, session: Session, seeded
    ) -> None:
        with pytest.raises(IntegrityError):
            with nested_transaction(session):
                session.execute(
                    text(
                        "INSERT INTO finding_observation (finding_observation_id, run_id, "
                        "finding_uid, stage_id, category, finding_text, recommendation_text, "
                        "grounded, ungrounded_reason, analysis_profile_id, prompt_bundle_id, "
                        "provider_mode) VALUES (:id, :run, NULL, 'text_analysis', "
                        "'internal_contradiction', 'т', 'т', true, NULL, :ap, :pb, 'recorded')"
                    ),
                    {
                        "id": FindingObservationId.new().value,
                        "run": seeded.run_id,
                        "ap": seeded.analysis_profile_id,
                        "pb": seeded.prompt_bundle_id,
                    },
                )

    def test_a_grounded_row_carrying_a_reason_is_refused(
        self, session: Session, seeded
    ) -> None:
        finding_uid = FindingUid.new().value
        session.execute(
            text(
                "INSERT INTO finding (finding_uid, project_uid, version_uid, "
                "allocated_by_run_id, category) VALUES (:f, :prj, :ver, :run, "
                "'internal_contradiction')"
            ),
            {
                "f": finding_uid,
                "prj": seeded.project_uid,
                "ver": seeded.version_uid,
                "run": seeded.run_id,
            },
        )
        with pytest.raises(IntegrityError):
            with nested_transaction(session):
                session.execute(
                    text(
                        "INSERT INTO finding_observation (finding_observation_id, run_id, "
                        "finding_uid, stage_id, category, finding_text, recommendation_text, "
                        "grounded, ungrounded_reason, analysis_profile_id, prompt_bundle_id, "
                        "provider_mode) VALUES (:id, :run, :f, 'text_analysis', "
                        "'internal_contradiction', 'т', 'т', true, 'quotation_absent', :ap, "
                        ":pb, 'recorded')"
                    ),
                    {
                        "id": FindingObservationId.new().value,
                        "run": seeded.run_id,
                        "f": finding_uid,
                        "ap": seeded.analysis_profile_id,
                        "pb": seeded.prompt_bundle_id,
                    },
                )

    def test_an_ungrounded_row_carrying_a_finding_uid_is_refused(
        self, session: Session, seeded
    ) -> None:
        finding_uid = FindingUid.new().value
        session.execute(
            text(
                "INSERT INTO finding (finding_uid, project_uid, version_uid, "
                "allocated_by_run_id, category) VALUES (:f, :prj, :ver, :run, "
                "'internal_contradiction')"
            ),
            {
                "f": finding_uid,
                "prj": seeded.project_uid,
                "ver": seeded.version_uid,
                "run": seeded.run_id,
            },
        )
        with pytest.raises(IntegrityError):
            with nested_transaction(session):
                session.execute(
                    text(
                        "INSERT INTO finding_observation (finding_observation_id, run_id, "
                        "finding_uid, stage_id, category, finding_text, recommendation_text, "
                        "grounded, ungrounded_reason, analysis_profile_id, prompt_bundle_id, "
                        "provider_mode) VALUES (:id, :run, :f, 'text_analysis', "
                        "'internal_contradiction', 'т', 'т', false, 'quotation_absent', :ap, "
                        ":pb, 'recorded')"
                    ),
                    {
                        "id": FindingObservationId.new().value,
                        "run": seeded.run_id,
                        "f": finding_uid,
                        "ap": seeded.analysis_profile_id,
                        "pb": seeded.prompt_bundle_id,
                    },
                )


class TestTheUngroundedVocabularyIsClosed:
    """The five reasons of §5.1, and where that closure is actually enforced.

    A note for whoever reads this next: at the P02 migration head,
    ``finding_observation.ungrounded_reason`` carries **no CHECK constraint** limiting it
    to the five declared values — the column is plain nullable ``text`` and the database
    accepts any string, including ``'looked_wrong'``. ``db/migrations/**`` is not this
    session's to change, so the gap is reported rather than repaired, and closure is
    asserted at the only place this session owns: the vocabulary the gate can produce,
    and the values publication actually writes. Both assertions stay correct whether or
    not the constraint is added later.
    """

    def test_the_enum_is_exactly_the_five_declared_reasons(self) -> None:
        assert UNGROUNDED_REASONS == {
            "quotation_absent",
            "quotation_on_different_page",
            "span_outside_page",
            "span_outside_block",
            "span_length_mismatch",
        }

    def test_publication_writes_only_declared_reasons(
        self, session: Session, seeded, corpus, text_layer, block_index, make_observations
    ) -> None:
        """Every reason that reaches a row comes from the enum, so nothing outside the
        vocabulary can be stored by this path even with no constraint behind it."""
        anchors = corpus.seeded_anchors()
        base = anchors[0]
        page_two = next(a for a in anchors if a["issue_id"] == "SI-01" and a["page_number"] == 2)
        page_six = next(a for a in anchors if a["issue_id"] == "SI-01" and a["page_number"] == 6)
        boundary = text_layer.page(2).char_end

        absent = dict(base)
        absent["quote"] = base["quote"].replace("е", "e", 1)
        different_page = {
            "page_number": 2,
            "quote": page_six["quote"],
            "char_start": page_two["char_start"],
            "char_end": page_two["char_start"] + len(page_six["quote"]),
            "block_id": None,
        }
        outside_page = {
            "page_number": 2,
            "quote": text_layer.slice(boundary - 12, boundary + 12),
            "char_start": boundary - 12,
            "char_end": boundary + 12,
            "block_id": None,
        }
        length_mismatch = dict(base)
        length_mismatch["char_end"] = base["char_start"] + len(base["quote"].encode("utf-8"))
        length_mismatch["block_id"] = None
        outside_block = dict(base)
        outside_block["block_id"] = corpus.block_after(base["block_id"])

        observations = make_observations(
            [
                _observation([absent]),
                _observation([different_page]),
                _observation([outside_page]),
                _observation([length_mismatch]),
                _observation([outside_block]),
            ]
        )
        seeded.advance_to("validating")
        result = run_grounding_gate(observations, text_layer, block_index)
        publish_gate_result(
            session,
            gate_result=result,
            observation_set=observations,
            run_id=seeded.run_id,
            project_uid=seeded.project_uid,
            version_uid=seeded.version_uid,
        )
        stored = {entry.ungrounded_reason for entry in diagnostics(session, seeded.run_id)}
        assert stored == UNGROUNDED_REASONS, (
            "all five reasons reached the database from one run, and nothing else did"
        )


class TestObservationIdentityIsImmutable:
    def test_update_and_delete_are_refused_with_am003(
        self, session: Session, seeded, corpus, text_layer, block_index, make_observations
    ) -> None:
        """A rerun creates new observations and never rewrites or removes earlier ones.

        Each refusal is attempted inside its own savepoint, and each asserts it matched
        a row first. The earlier version of this test rolled the unit of work back
        between the two statements, which discarded the published row — so the DELETE
        matched nothing, was refused by nobody, and the test reported that the guard had
        failed to fire. ``rowcount == 1`` is what stops that from ever being silent.
        """
        anchor = corpus.seeded_anchors()[0]
        observations = make_observations([_observation([anchor])])
        result = run_grounding_gate(observations, text_layer, block_index)
        publication = publish_gate_result(
            session,
            gate_result=result,
            observation_set=observations,
            run_id=seeded.run_id,
            project_uid=seeded.project_uid,
            version_uid=seeded.version_uid,
        )
        observation_id = publication.published[0].finding_observation_id

        for statement in (
            "UPDATE finding_observation SET finding_text = 'изменено' "
            "WHERE finding_observation_id = :id",
            "DELETE FROM finding_observation WHERE finding_observation_id = :id",
        ):
            with pytest.raises(DBAPIError) as caught:
                with nested_transaction(session):
                    proxy = session.execute(text(statement), {"id": observation_id})
                    assert proxy.rowcount == 1, (
                        "the statement matched no row, so no trigger could have refused it"
                    )
            assert caught.value.orig.sqlstate == "AM003", (
                "the refusal must be identified by SQLSTATE, never by message text"
            )

        assert (
            session.execute(
                text(
                    "SELECT finding_text FROM finding_observation "
                    "WHERE finding_observation_id = :id"
                ),
                {"id": observation_id},
            ).scalar_one()
            != "изменено"
        ), "the row survived both refusals unchanged"

    def test_published_evidence_is_immutable_too(
        self, session: Session, seeded, corpus, text_layer, block_index, make_observations
    ) -> None:
        """An anchor cannot be nudged after publication. Otherwise a stored anchor that
        no longer resolves could be made to resolve by moving it."""
        anchor = corpus.seeded_anchors()[0]
        observations = make_observations([_observation([anchor])])
        result = run_grounding_gate(observations, text_layer, block_index)
        publication = publish_gate_result(
            session,
            gate_result=result,
            observation_set=observations,
            run_id=seeded.run_id,
            project_uid=seeded.project_uid,
            version_uid=seeded.version_uid,
        )
        observation_id = publication.published[0].finding_observation_id
        with pytest.raises(DBAPIError) as caught:
            with nested_transaction(session):
                proxy = session.execute(
                    text(
                        "UPDATE finding_evidence SET char_start = char_start + 1 "
                        "WHERE finding_observation_id = :id"
                    ),
                    {"id": observation_id},
                )
                assert proxy.rowcount == 1
        assert caught.value.orig.sqlstate == "AM003"

    def test_a_rerun_allocates_a_disjoint_set_of_finding_identities(
        self,
        session: Session,
        seeded_factory,
        observations_builder,
        corpus,
        text_layer,
        block_index,
    ) -> None:
        """§5.2: fresh per published observation, per run.

        Both runs are over the same document version and report the same observation
        with the same anchor — the case where cross-run matching *would* fire if PC-01
        did any. It does none, so the two runs produce two disjoint sets. A carried-over
        identity would attach one run's expert history to another run's text, and the
        earlier observation rows would have to be rewritten to point at it.
        """
        anchor = corpus.seeded_anchors()[0]
        first = seeded_factory()
        second = seeded_factory(first)

        uids: list[set[str]] = []
        observation_ids: list[set[str]] = []
        for run in (first, second):
            observation_set = observations_builder(run, [_observation([anchor])])
            result = run_grounding_gate(observation_set, text_layer, block_index)
            publication = publish_gate_result(
                session,
                gate_result=result,
                observation_set=observation_set,
                run_id=run.run_id,
                project_uid=run.project_uid,
                version_uid=run.version_uid,
            )
            assert publication.published_count == 1
            uids.append(set(publication.finding_uids))
            observation_ids.append(
                {entry.finding_observation_id for entry in publication.published}
            )

        assert uids[0] and uids[1]
        assert uids[0].isdisjoint(uids[1]), "a finding_uid was carried across runs"
        assert observation_ids[0].isdisjoint(observation_ids[1])

        # The first run's observation still stands, unrewritten and unremoved.
        assert (
            session.execute(
                text(
                    "SELECT count(*) FROM finding_observation WHERE run_id = :run"
                ),
                {"run": first.run_id},
            ).scalar_one()
            == 1
        )
