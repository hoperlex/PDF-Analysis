"""`CRIT-CAPTURE-01` part D: the three members of ``DecisionFact`` that say what the server was showing when the expert decided, with no database.

Shown: they are optional and the decision is what it always was without them; the label and the revision are both given or both absent (the table's own
pair check, refused here first); a value the table would refuse is refused here; and they are **decision metadata, not case content** -- the content
digest of a case is the one pinned from the code before they existed, whatever a decision carries, so a second decision under another mark on a known
observation is no conflict.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone

import pytest

from auditmanager.decision_memory.public import (
    CaptureSnapshot,
    CaseContent,
    CaseOrigin,
    DecisionFact,
    EvidenceItem,
    content_digest,
)
from auditmanager.shared.errors import DomainError

#: The digest of ``_content()`` below: the very value ``test_block_evidence.py`` pins from the code before block evidence existed. A decision that
#: carries a mark must not move it (a stored case compares its digest with the one a later decision computes; a moved body would read as a conflict).
PINNED_DIGEST = "85330c54181cabd21ab35cd2b35cb70af91eee951ca5d09b564f8a2d4551e156"
NOW = datetime(2026, 11, 11, 9, 0, tzinfo=timezone.utc)


def _content() -> CaseContent:
    return CaseContent(
        category="internal_contradiction", finding_text="Степень указана по-разному.", recommendation_text="Согласовать.",
        proposed_severity=None, required_value=None, stated_value=None, stage_id="text_analysis",
        analysis_profile_id="ap_01M5F21PBT7E8WRN3M61BDQFDD", prompt_bundle_id="pb_01M5F21PBT7E8WRN3M61BDQFDD", provider_mode="recorded",
        evidence=(EvidenceItem(ordinal=0, page_number=1, quote="Степень огнестойкости здания — II.", char_start=0, char_end=34),),
        norm_refs=(),
    )


def _decision(**extra: object) -> DecisionFact:
    values: dict[str, object] = dict(
        source_decision_id="dec_01M5F21PBT7E8WRN3M61BDQFDD", event_type="reject", severity=None, comment="Не нарушение.",
        author_user_uid=None, origin_kind="direct", decided_at=NOW,
    )
    values.update(extra)
    return DecisionFact(**values)  # type: ignore[arg-type]


def _snapshot(decision: DecisionFact) -> CaptureSnapshot:
    return CaptureSnapshot(
        origin=CaseOrigin(
            observation_id="fobs_01M5F21PBT7E8WRN3M61BDQFDD", finding_uid="fnd_01M5F21PBT7E8WRN3M61BDQFDD",
            project_uid="prj_01M5F21PBT7E8WRN3M61BDQFDD", document_uid="doc_01M5F21PBT7E8WRN3M61BDQFDD",
            version_uid="ver_01M5F21PBT7E8WRN3M61BDQFDD", run_id="run_01M5F21PBT7E8WRN3M61BDQFDD",
        ),
        content=_content(), section_code="AR", data_class="test", crops=(), decision=decision,
    )


def test_a_decision_without_a_mark_is_what_it_always_was() -> None:
    plain = _decision()
    assert (plain.precedent_label_at_decision, plain.precedent_revision, plain.precedent_history_verdict_shown) == (None, None, None)
    assert plain.verdict == "rejected"


def test_a_decision_may_carry_the_mark_the_revision_and_the_verdict_the_history_showed() -> None:
    shown = _decision(precedent_label_at_decision="cancel_suggested", precedent_revision=3, precedent_history_verdict_shown="rejected")
    assert (shown.precedent_label_at_decision, shown.precedent_revision, shown.precedent_history_verdict_shown) == ("cancel_suggested", 3, "rejected")
    # the neutral display is the word ``neutral``, which is a code like any other
    assert _decision(precedent_label_at_decision="neutral", precedent_revision=1).precedent_label_at_decision == "neutral"
    # the history's verdict is independent of the mark: it can be the only one given with a mark, never without the pair's rule being kept
    assert _decision(precedent_label_at_decision="few", precedent_revision=2, precedent_history_verdict_shown="accepted")


@pytest.mark.parametrize("extra", [
    {"precedent_label_at_decision": "often_rejected"},                      # a mark with no revision
    {"precedent_revision": 2},                                              # a revision with no mark
    {"precedent_label_at_decision": "Often Rejected", "precedent_revision": 1},
    {"precedent_label_at_decision": "", "precedent_revision": 1},
    {"precedent_label_at_decision": "few", "precedent_revision": 0},
    {"precedent_label_at_decision": "few", "precedent_revision": -1},
    {"precedent_label_at_decision": "few", "precedent_revision": True},     # a boolean is not a revision
    {"precedent_label_at_decision": "few", "precedent_revision": 1, "precedent_history_verdict_shown": "withdrawn"},
])
def test_a_value_the_table_would_refuse_is_refused_before_it_gets_there(extra: dict[str, object]) -> None:
    with pytest.raises(DomainError):
        _decision(**extra)


def test_the_mark_is_decision_metadata_and_never_moves_the_digest_of_the_case() -> None:
    assert content_digest(_content()) == PINNED_DIGEST
    for decision in (
        _decision(),
        _decision(precedent_label_at_decision="cancel_suggested", precedent_revision=7, precedent_history_verdict_shown="rejected"),
        _decision(event_type="accept", precedent_label_at_decision="likely_accepted", precedent_revision=1),
    ):
        assert content_digest(_snapshot(decision).content) == PINNED_DIGEST


def test_case_content_has_no_member_for_the_mark_so_it_cannot_reach_the_digest() -> None:
    """The structural half of the pin: were a mark ever added to ``CaseContent`` it would enter the body of the digest's walk, and this names it."""
    members = {field.name for field in dataclasses.fields(CaseContent)}
    assert not {name for name in members if "precedent" in name}, members
    assert {"precedent_label_at_decision", "precedent_revision", "precedent_history_verdict_shown"} <= {
        field.name for field in dataclasses.fields(DecisionFact)}
