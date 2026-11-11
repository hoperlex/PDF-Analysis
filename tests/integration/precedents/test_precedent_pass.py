"""`PREC-PASS`: the pass over a run's findings and the two reads behind it, against real PostgreSQL with real pgvector (ADR-0029 decisions 4 to 6).

Every test runs inside one transaction that is rolled back (``journalled_sessions``): the advice is append-only and so is the memory's ledger. What is
real: the published run (a finished ``audit_run`` with grounded findings), the cases of the memory with their decisions, comments and vectors, the
probes and **the import of their vectors through the window's own function**, the settings journal (the section switch is appended through the real service),
the scan (pgvector's ``<=>`` in the database), the core's ``evaluate`` and the two services. What is replaced: the saved extended review (the callable the
composition root closes over its stores) and the encoder (a probe's vector is the one the test says).

Shown, each by the case that must come out the other way next to it:

* a finding with **no vector has no answer** («Недоступно») even when a case with the very same words is in the memory: there is no search by words;
* the pass is idempotent (a second pass writes nothing, a changed result is a whole new revision, the earlier one stays);
* **a withdrawn case leaves the marks at read time**, not at the next night;
* a section with its refusal labels **off shows no refusal mark** and an empty queue; the same finding is in the queue when the administrator turns the
  section on from a replay report (the switch is the real settings service, and its journal row carries the report's digest);
* the critic: the AI critic's ``accept`` vetoes, the deterministic critic's ``pass`` does not, a finding no critic reviewed (v2 and v3), outside the AI
  critic's window, or of a v2 run with no marker, is never in the queue, and a v2 finding the deterministic critic reviewed is;
* the card: similar cases with their verdicts, the comment that is the reason of the refusals (P1), the document's history (P5), the possible norms, and
  what ``shown_at_decision`` records;
* the window encodes the probes in the same round as the cases and its ``after_import`` hook runs the pass.
"""

from __future__ import annotations

import hashlib
import importlib.util
import math
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.decision_memory.public import withdraw_case
from auditmanager.precedents.public import (
    Exchange,
    PrecedentPass,
    PrecedentService,
    PrecedentSettingService,
    VectorWindowPass,
    shown_at_decision,
)
from auditmanager.precedents.vectors import repository as store
from auditmanager.precedents.vectors.intents import EMBEDDING_PROFILE, MODEL_REVISION, EncodedVector, build_finding_view, input_sha256
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    AnalysisProfileId,
    DecisionId,
    DecisionMemoryCaseId,
    DecisionMemoryCommentId,
    DecisionMemoryDecisionId,
    DocumentUid,
    FindingObservationId,
    FindingUid,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)

DIMENSIONS = 1024
SECTION = "AR"
CATEGORY = "dimensions"
NDOC = "ndoc_01M2545JSD15ETSNNV904X991K"
NPAR = "npar_01M2545JSD15ETSNNV904X991K"
EXPERT = lambda _session, _user: frozenset({"expert"})  # noqa: E731
ADMIN = lambda _session, _user: frozenset({"admin"})  # noqa: E731
VIEWER = lambda _session, _user: frozenset({"viewer"})  # noqa: E731


def unit(cosine_to_first_axis: float, axis: int = 1) -> list[float]:
    """A unit vector whose cosine with the first axis is ``cosine_to_first_axis`` (it leans on ``axis`` for the rest)."""
    vector = [0.0] * DIMENSIONS
    vector[0] = cosine_to_first_axis
    vector[axis] = math.sqrt(max(0.0, 1.0 - cosine_to_first_axis**2))
    return vector


def axis(index: int) -> list[float]:
    vector = [0.0] * DIMENSIONS
    vector[index] = 1.0
    return vector


def literal(values: Sequence[float]) -> str:
    return "[" + ",".join(format(value, ".9g") for value in values) + "]"


def digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


@dataclass
class Run:
    run_id: str
    project_uid: str
    document_uid: str
    version_uid: str
    findings: list[str]
    texts: list[str]


def seed_run(session: Session, texts: Sequence[str], *, section: str | None = SECTION, state: str = "published") -> Run:
    """A finished run of one version with one grounded finding per text. The rows are the publisher's; nothing here is a stub of the pass's own reads."""
    project, document, version, run = (ProjectUid.new().value, DocumentUid.new().value, VersionUid.new().value, RunId.new().value)
    profile, bundle, sha = AnalysisProfileId.new().value, PromptBundleId.new().value, digest(run)
    admin = session.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one()
    session.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'Проект')"), {"p": project})
    session.execute(text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'АР')"), {"d": document, "p": project})
    session.execute(text(
        "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, sha256, page_count) "
        "VALUES (:v, :d, 1, 'application/pdf', 1024, :s, 2)"), {"v": version, "d": document, "s": sha})
    if section is not None:
        session.execute(text(
            "INSERT INTO document_version_classification (version_uid, project_stage, section_code, confirmed_by_user_uid) "
            "VALUES (:v, 'P', :s, :a)"), {"v": version, "s": section, "a": admin})
    session.execute(text(
        "INSERT INTO audit_run (run_id, project_uid, version_uid, state, analysis_profile_id, prompt_bundle_id, provider_mode, frozen_input_digest) "
        "VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :s)"), {"r": run, "p": project, "v": version, "ap": profile, "pb": bundle, "s": sha})
    for step in ("queued", "running", "validating", *(("published",) if state == "published" else ())):
        published = step == "published"
        session.execute(text(
            "UPDATE audit_run SET state = :s, terminal_at = CASE WHEN :t THEN now() ELSE NULL END, "
            "degradation_set = CASE WHEN :t THEN '[]'::jsonb ELSE degradation_set END WHERE run_id = :r"), {"s": step, "t": published, "r": run})
    uids: list[str] = []
    for position, words in enumerate(texts):
        uid, observation = FindingUid.new().value, FindingObservationId.new().value
        session.execute(text(
            "INSERT INTO finding (finding_uid, project_uid, version_uid, allocated_by_run_id, category) VALUES (:f, :p, :v, :r, :c)"),
            {"f": uid, "p": project, "v": version, "r": run, "c": CATEGORY})
        session.execute(text(
            "INSERT INTO finding_observation (finding_observation_id, run_id, finding_uid, stage_id, category, finding_text, recommendation_text, "
            "grounded, analysis_profile_id, prompt_bundle_id, provider_mode) "
            "VALUES (:o, :r, :f, 'text_analysis', :c, :t, :rec, true, :ap, :pb, 'recorded')"),
            {"o": observation, "r": run, "f": uid, "c": CATEGORY, "t": words, "rec": "Привести в соответствие.", "ap": profile, "pb": bundle})
        session.execute(text(
            "INSERT INTO finding_evidence (finding_observation_id, evidence_ordinal, page_number, quote, char_start, char_end) "
            "VALUES (:o, 0, 1, 'x', :s, :e)"), {"o": observation, "s": position, "e": position + 1})
        session.execute(text("UPDATE finding SET canonical_observation_id = :o WHERE finding_uid = :f"), {"o": observation, "f": uid})
        uids.append(uid)
    return Run(run, project, document, version, uids, list(texts))


def seed_case(
    session: Session, *, verdict: str, vector: Sequence[float], days_ago: float = 30, project: str | None = None, section: str | None = SECTION,
    words: str = "Другая находка про высоту помещения", comment: str | None = None, document: str | None = None, version: str | None = None,
    data_class: str = "test", label: str | None = None,
) -> str:
    """One case of the memory with its content, one decision, its vector and, if given, a comment: committed to the rolled-back transaction."""
    case = DecisionMemoryCaseId.new().value
    session.execute(text(
        "INSERT INTO decision_memory_case (case_id, origin_observation_id, origin_finding_uid, origin_project_uid, origin_document_uid, "
        "origin_version_uid, origin_run_id, category, section_code, data_class, crop_state, capture_version, content_sha256) "
        "VALUES (:c, :o, :f, :p, :d, :v, :r, :cat, :s, :dc, 'none_available', 'dm-capture/1', :sha)"),
        {"c": case, "o": FindingObservationId.new().value, "f": FindingUid.new().value, "p": project or ProjectUid.new().value,
         "d": document or DocumentUid.new().value, "v": version or VersionUid.new().value, "r": RunId.new().value, "cat": CATEGORY, "s": section,
         "dc": data_class, "sha": digest(case)})
    session.execute(text(
        "INSERT INTO decision_memory_content (case_id, revision, finding_text, recommendation_text, stage_id, analysis_profile_id, "
        "prompt_bundle_id, provider_mode) VALUES (:c, 1, :t, 'Привести в соответствие.', 'text_analysis', :ap, :pb, 'recorded')"),
        {"c": case, "t": words, "ap": AnalysisProfileId.new().value, "pb": PromptBundleId.new().value})
    decided = datetime.now(UTC) - timedelta(days=days_ago)
    session.execute(text(
        "INSERT INTO decision_memory_decision (memory_decision_id, case_id, source_decision_id, event_type, verdict, origin_kind, decided_at, "
        "precedent_label_at_decision, precedent_revision) VALUES (:m, :c, :s, :e, :v, 'direct', :at, :label, :rev)"),
        {"m": DecisionMemoryDecisionId.new().value, "c": case, "s": DecisionId.new().value, "e": "reject" if verdict == "rejected" else "accept",
         "v": verdict, "at": decided, "label": label, "rev": None if label is None else 1})
    session.execute(text(
        "INSERT INTO decision_memory_embedding (case_id, revision, view_kind, embedding_profile, model_revision, input_sha256, embedding_sha256, embedding) "
        "VALUES (:c, 1, 'finding_v1', :p, :m, :i, :e, CAST(:v AS vector))"),
        {"c": case, "p": EMBEDDING_PROFILE, "m": MODEL_REVISION, "i": digest("i" + case), "e": digest("e" + case), "v": literal(vector)})
    if comment is not None:
        session.execute(text(
            "INSERT INTO decision_memory_comment (comment_id, case_id, source_decision_id, comment, decided_at) VALUES (:k, :c, :s, :t, :at)"),
            {"k": DecisionMemoryCommentId.new().value, "c": case, "s": DecisionId.new().value, "t": comment, "at": decided + timedelta(minutes=1)})
    return case


def seed_refusals(session: Session, count: int = 7, *, cosine: float = 0.9, projects: int = 2) -> list[str]:
    """``count`` independent refusals of the section, spread over ``projects`` projects, all near the first axis."""
    pool = [ProjectUid.new().value for _ in range(projects)]
    return [seed_case(session, verdict="rejected", vector=unit(cosine), days_ago=200 - index, project=pool[index % projects]) for index in range(count)]


def give_vectors(session: Session, run: Run, vectors: Mapping[int, Sequence[float]]) -> int:
    """What the window does after a round: store a vector for each probe the encoder was asked about -- through the window's own import function.
    ``vectors`` maps the position of a finding to its vector; a finding not named is left without one."""
    probes = {probe.input_id: probe for probe in store.pending_probe_texts(session, limit=500) if probe.run_id == run.run_id}
    encoded = []
    for position, values in vectors.items():
        probe = probes[run.findings[position]]
        assert probe.matches, "the text the encoder would be given is the text the probe was queued for"
        encoded.append(EncodedVector(probe.input_sha256, digest("v" + probe.input_sha256), tuple(values)))
    outcome = store.import_vectors(session, vectors=encoded, over_limit=(), rejected=(), missing=())
    return outcome.probes_done


def ai(decision: str) -> dict[str, Any]:
    return {"input_id": "xri_1", "llm_decision": decision, "explanation": "..."}


def deterministic(decision: str = "accept") -> dict[str, Any]:
    return {"input_id": "xrd_1", "llm_decision": decision, "mode": "deterministic", "model_called": False, "policy": "deterministic-v1",
            "original_verdict": "pass"}


def review_of(run: Run, *, position: int = 0, workflow: str = "extended-review-v3", critic: dict[str, Any] | None = None, status: str | None = None,
              marker: bool = False, norms: Sequence[dict[str, Any]] = (), source: str | None = None) -> dict[str, Any]:
    """The saved extended review of the run, with one candidate that restates the finding at ``position``."""
    primary = {"category": CATEGORY, "finding_text": run.texts[position]}
    item: dict[str, Any] = {"observation_id": "xobs_1", "source_ids": [source or ("primary_text_aa" if workflow.endswith("v3") else "text:0")],
                            "title": CATEGORY, "description": run.texts[position], "norm_candidates": list(norms)}
    if workflow.endswith("v3"):
        item["original_primary_observation"] = primary
    if critic is not None:
        item.update(critic=critic, review_status=status or "reviewed")
    elif status is not None:
        item["review_status"] = status
    result: dict[str, Any] = {"workflow_version": workflow, "observations": [item]}
    if marker:
        result["original_review"] = {"version": "deterministic-v1", "mode": "deterministic", "model_called": False}
    return {"run_id": run.run_id, "status": "completed", "result": result}


def norm(paragraph: str = NPAR) -> dict[str, Any]:
    return {"document_id": NDOC, "paragraph_id": paragraph, "designation": "СП 54.13330.2022", "clause_number": "6.1", "page_label": 12, "quote": "x"}


class Stand:
    """The pass and the services over one rolled-back transaction, with the saved extended review of each run in a dictionary."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self.sessions = sessions
        self.reviews: dict[str, Any] = {}
        self.pass_ = PrecedentPass(sessions, read_extended_review=lambda run_id: self.reviews.get(run_id), interval_seconds=0)
        self.expert = PrecedentService(sessions, read_extended_review=lambda run_id: self.reviews.get(run_id), roles_of=EXPERT)

    def label_of(self, run: Run, position: int = 0, *, service: PrecedentService | None = None) -> dict[str, Any] | None:
        body = (service or self.expert).get_run_precedents(run_id=run.run_id, user_uid="usr_x")
        found = [item for item in body["items"] if item["finding_uid"] == run.findings[position]]
        return found[0] if found else None

    def queue(self, run: Run) -> list[str]:
        body = self.expert.get_run_precedents(run_id=run.run_id, user_uid="usr_x")
        return [item["finding_uid"] for item in body["items"] if item["label"] == "cancel_suggested"]


@pytest.fixture
def stand(journalled_sessions: sessionmaker[Session]) -> Stand:
    return Stand(journalled_sessions)


@pytest.fixture
def session(journalled_sessions: sessionmaker[Session]) -> Session:
    opened = journalled_sessions()
    try:
        yield opened  # type: ignore[misc]
    finally:
        opened.close()


def turn_section_on(sessions: sessionmaker[Session], admin_uid: str, section: str = SECTION, *, analogous: float | None = None) -> dict[str, Any]:
    """The administrator's act: ``section_labels`` appended through the real service with the digest of a replay report."""
    entry: dict[str, Any] = {"enabled": True, "report_sha256": digest("replay report of " + section)}
    if analogous is not None:
        entry["analogous"] = analogous
    return PrecedentSettingService(sessions, roles_of=ADMIN).append_precedent_setting(
        setting_name="section_labels", value={section: entry}, user_uid=admin_uid, idempotency_key=f"prec-pass-{section}-{digest(str(entry))[:12]}")


# -- no vector, no answer ------------------------------------------------------------------------------------------------------------------


def test_a_finding_with_no_vector_has_no_answer_even_when_a_case_with_the_same_words_is_in_the_memory(stand: Stand, session: Session) -> None:
    words = "Высота помещения менее нормы на втором этаже"
    run = seed_run(session, [words])
    for _ in range(7):                                            # seven refusals of the very same words: a search by words would find all of them
        seed_case(session, verdict="rejected", vector=unit(0.9), words=words)
    session.flush()
    outcome = stand.pass_.compute_run(run.run_id)
    assert outcome.status == "waiting_for_vectors" and outcome.changed, "the probe is queued, nothing is answered"
    body = stand.expert.get_run_precedents(run_id=run.run_id, user_uid="usr_x")
    assert body == {"run_id": run.run_id, "available": False, "pass_state": "pending", "revision": 1, "items": []}
    card = stand.expert.get_finding_precedents(finding_uid=run.findings[0], user_uid="usr_x")
    assert card["available"] is False and "label" not in card and card["cases"] == [] and card["hints"] == []
    assert shown_at_decision(session, run.findings[0]) is None, "no answer: the columns of the decision stay NULL"
    # the same finding the moment its vector arrives is the case that differs
    assert give_vectors(session, run, {0: axis(0)}) == 1
    assert stand.pass_.compute_run(run.run_id).status == "computed"
    assert stand.label_of(run)["votes"]["total"] == 7, "the neighbours are found by their vectors, whatever the words"


def test_a_run_nobody_computed_and_an_unknown_run_or_finding(stand: Stand, session: Session) -> None:
    run = seed_run(session, ["Находка без прохода"])
    body = stand.expert.get_run_precedents(run_id=run.run_id, user_uid="usr_x")
    assert body == {"run_id": run.run_id, "available": False, "items": []}, "no pass row yet: no state, no revision"
    for call, aggregate in ((lambda: stand.expert.get_run_precedents(run_id=RunId.new().value, user_uid="usr_x"), "Run"),
                            (lambda: stand.expert.get_finding_precedents(finding_uid=FindingUid.new().value, user_uid="usr_x"), "Finding")):
        with pytest.raises(DomainError) as caught:
            call()
        assert caught.value.code is ErrorCode.NOT_FOUND and caught.value.detail_fields["aggregate_type"] == aggregate


# -- the pass: labels, idempotency, revisions ------------------------------------------------------------------------------------------------


def test_the_pass_labels_the_findings_that_have_a_vector_and_is_idempotent(stand: Stand, session: Session, journalled_sessions: sessionmaker[Session]) -> None:
    run = seed_run(session, ["Первая находка про высоту", "Вторая находка про ширину"])
    seed_refusals(session)
    stand.reviews[run.run_id] = review_of(run, critic=ai("reject"))
    assert stand.pass_.compute_run(run.run_id).status == "waiting_for_vectors"
    assert give_vectors(session, run, {0: axis(0), 1: axis(7)}) == 2           # the second finding is far from every case
    first = stand.pass_.compute_run(run.run_id)
    assert (first.status, first.revision, first.changed) == ("computed", 1, True)
    with journalled_sessions() as check:
        rows = check.execute(text(
            "SELECT finding_uid, label, critic_reviewed, hint_codes, votes FROM decision_memory_precedent_advice WHERE run_id = :r ORDER BY finding_uid"),
            {"r": run.run_id}).all()
        state = check.execute(text("SELECT state, revision, failure_code FROM decision_memory_precedent_run WHERE run_id = :r"), {"r": run.run_id}).one()
    by_uid = {row[0]: row for row in rows}
    near, far = by_uid[run.findings[0]], by_uid[run.findings[1]]
    assert (near[1], near[2], list(near[3])) == ("cancel_suggested", True, [])
    assert {key: near[4][key] for key in ("total", "rejected", "accepted", "independent", "projects")} == {
        "total": 7, "rejected": 7, "accepted": 0, "independent": 7, "projects": 2}
    assert near[4]["critic"] == {"in_plan": True, "linked": 1, "records": [{"d": "reject", "k": []}]}
    assert (far[1], far[2]) == ("none", False), "a finding with a vector and no neighbour is answered: none"
    assert tuple(state) == ("done", 1, None)

    again = stand.pass_.compute_run(run.run_id)
    assert (again.status, again.revision, again.changed) == ("unchanged", 1, False), "the same result writes nothing"
    assert stand.pass_.run_once(refresh=True) >= 0 and stand.pass_.after_import() is None
    with journalled_sessions() as check:
        assert check.execute(text("SELECT count(*), max(revision) FROM decision_memory_precedent_advice WHERE run_id = :r"), {"r": run.run_id}).one() == (2, 1)

    body = stand.expert.get_run_precedents(run_id=run.run_id, user_uid="usr_x")
    assert body["available"] is True and body["pass_state"] == "done" and body["revision"] == 1 and len(body["items"]) == 2


def test_a_changed_result_is_a_whole_new_revision_and_the_earlier_one_stays(stand: Stand, session: Session, journalled_sessions: sessionmaker[Session]) -> None:
    run = seed_run(session, ["Находка про толщину слоя"])
    seed_refusals(session, 6)
    stand.reviews[run.run_id] = review_of(run, critic=ai("reject"))
    stand.pass_.compute_run(run.run_id)
    give_vectors(session, run, {0: axis(0)})
    assert stand.pass_.compute_run(run.run_id).revision == 1
    seed_case(session, verdict="accepted", vector=unit(0.9), days_ago=1)       # an acceptance arrives: six of seven is not 90 %
    second = stand.pass_.compute_run(run.run_id)
    assert (second.status, second.revision) == ("computed", 2)
    with journalled_sessions() as check:
        labels = dict(check.execute(text("SELECT revision, label FROM decision_memory_precedent_advice WHERE run_id = :r"), {"r": run.run_id}).all())
        assert check.execute(text("SELECT revision FROM decision_memory_precedent_run WHERE run_id = :r"), {"r": run.run_id}).scalar_one() == 2
    assert labels == {1: "cancel_suggested", 2: "often_rejected"}, "revision 1 is still there to be read by the decision that names it"


# -- a withdrawn case leaves the marks at read time --------------------------------------------------------------------------------------------


def test_a_withdrawn_case_leaves_the_marks_at_read_time_not_at_the_next_night(
    stand: Stand, session: Session, journalled_sessions: sessionmaker[Session], admin_uid: str,
) -> None:
    run = seed_run(session, ["Находка про отметку пола"])
    cases = seed_refusals(session, 6)
    stand.reviews[run.run_id] = review_of(run, critic=ai("reject"))
    turn_section_on(journalled_sessions, admin_uid)          # before the pass, so that nothing journalled after it makes the read evaluate again
    stand.pass_.compute_run(run.run_id)
    give_vectors(session, run, {0: axis(0)})
    stand.pass_.compute_run(run.run_id)
    before = stand.label_of(run)
    assert before["label"] == "cancel_suggested" and before["votes"]["total"] == 6, "the control: with nothing withdrawn the mark stands"
    assert stand.label_of(run)["revision"] == 1 and stand.queue(run) == [run.findings[0]]

    withdraw_case(session, case_id=cases[0], actor_user_uid=admin_uid, reason_code="wrong_decision")
    withdraw_case(session, case_id=cases[1], actor_user_uid=admin_uid, reason_code="wrong_decision")
    after = stand.label_of(run)
    assert after["votes"]["total"] == 4 and after["label"] == "few", "four voters are not enough: the withdrawn cases no longer count"
    assert stand.queue(run) == [] and after["revision"] == 1, "read at once, with no new pass"
    with journalled_sessions() as check:
        stored = check.execute(text("SELECT label FROM decision_memory_precedent_advice WHERE run_id = :r AND revision = 1"), {"r": run.run_id}).scalar_one()
    assert stored == "cancel_suggested", "the stored revision is what the night computed; the read is what is true now"
    # the next night's pass writes what the read already says
    assert stand.pass_.compute_run(run.run_id).revision == 2 and stand.label_of(run)["label"] == "few"


def test_a_stop_word_journalled_after_the_pass_acts_at_read_time(stand: Stand, session: Session, journalled_sessions: sessionmaker[Session], admin_uid: str) -> None:
    run = seed_run(session, ["Срочно уточнить толщину слоя"])
    seed_refusals(session)
    stand.reviews[run.run_id] = review_of(run, critic=ai("reject"))
    turn_section_on(journalled_sessions, admin_uid)
    stand.pass_.compute_run(run.run_id)
    give_vectors(session, run, {0: axis(0)})
    stand.pass_.compute_run(run.run_id)
    assert stand.queue(run) == [run.findings[0]]
    PrecedentSettingService(journalled_sessions, roles_of=ADMIN).append_precedent_setting(
        setting_name="stop_words", value={"words": ["срочный"]}, user_uid=admin_uid, idempotency_key="prec-pass-stop-words-1")
    assert stand.queue(run) == [], "the owner's stop word (matched by its stem) hides the «снять» at once"
    assert stand.label_of(run)["label"] == "often_rejected"


def test_a_read_evaluates_again_only_while_the_memory_has_moved_since_the_last_pass(
    stand: Stand, session: Session, journalled_sessions: sessionmaker[Session], admin_uid: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The stored advice is read as it is until something the labels depend on is journalled; a pass whose result comes out the same still moves the
    moment the advice speaks for, so the next read takes the stored rows again and does not evaluate on every request for ever."""
    run = seed_run(session, ["Находка про отметку лестницы"])
    seed_refusals(session)
    stand.reviews[run.run_id] = review_of(run, critic=ai("reject"))
    turn_section_on(journalled_sessions, admin_uid)
    stand.pass_.compute_run(run.run_id)
    give_vectors(session, run, {0: axis(0)})
    stand.pass_.compute_run(run.run_id)
    again: list[int] = []
    original = PrecedentService._evaluated_again

    def spy(self: PrecedentService, *args: Any, **kwargs: Any) -> Any:
        again.append(1)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(PrecedentService, "_evaluated_again", spy)
    assert stand.label_of(run)["label"] == "cancel_suggested" and again == [], "nothing moved: the stored rows"
    PrecedentSettingService(journalled_sessions, roles_of=ADMIN).append_precedent_setting(
        setting_name="stop_words", value={"words": ["несуществующее"]}, user_uid=admin_uid, idempotency_key="prec-pass-fresh-1")
    assert stand.label_of(run)["label"] == "cancel_suggested" and again == [1], "a setting was journalled after the pass: evaluated again"
    assert stand.pass_.compute_run(run.run_id).status == "unchanged", "the same result writes no rows"
    assert stand.label_of(run)["label"] == "cancel_suggested" and again == [1], "but the moment the advice speaks for has moved: the stored rows again"
    with journalled_sessions() as check:
        assert check.execute(text("SELECT count(*) FROM decision_memory_precedent_advice WHERE run_id = :r"), {"r": run.run_id}).scalar_one() == 1


# -- the per-section switch -----------------------------------------------------------------------------------------------------------------------


def test_a_switched_off_section_shows_no_refusal_marks_and_the_same_finding_is_in_the_queue_when_it_is_on(
    stand: Stand, session: Session, journalled_sessions: sessionmaker[Session], admin_uid: str,
) -> None:
    run = seed_run(session, ["Находка про высоту этажа"])
    seed_refusals(session)
    stand.reviews[run.run_id] = review_of(run, critic=ai("reject"))
    stand.pass_.compute_run(run.run_id)
    give_vectors(session, run, {0: axis(0)})
    stand.pass_.compute_run(run.run_id)

    off = stand.label_of(run)
    assert off["label"] == "few" and off["votes"]["total"] == 7 and off["hint_codes"] == [] and off["critic_reviewed"] is True
    assert stand.queue(run) == []
    card = stand.expert.get_finding_precedents(finding_uid=run.findings[0], user_uid="usr_x")
    assert card["label"]["label"] == "few" and card["cases"] == [], "the card says nothing of refusal either"
    assert shown_at_decision(session, run.findings[0]).label == "few", "and what the decision records is what was shown"

    made = turn_section_on(journalled_sessions, admin_uid)
    assert made["setting_name"] == "section_labels" and made["value"][SECTION]["report_sha256"] == digest("replay report of " + SECTION), \
        "the journal row carries the digest of the report"
    on = stand.label_of(run)
    assert on["label"] == "cancel_suggested" and stand.queue(run) == [run.findings[0]]
    assert shown_at_decision(session, run.findings[0]).label == "cancel_suggested"
    # another section is not turned on by it
    other = seed_run(session, ["Находка другого раздела"], section="KM")
    for _ in range(7):
        seed_case(session, verdict="rejected", vector=unit(0.9), section="KM")
    stand.reviews[other.run_id] = review_of(other, critic=ai("reject"))
    stand.pass_.compute_run(other.run_id)
    give_vectors(session, other, {0: axis(0)})
    stand.pass_.compute_run(other.run_id)
    assert stand.label_of(other)["label"] == "few" and stand.queue(other) == []


def test_a_section_is_computed_at_the_threshold_its_report_chose(stand: Stand, session: Session, journalled_sessions: sessionmaker[Session], admin_uid: str) -> None:
    run = seed_run(session, ["Находка про шаг колонн"])
    seed_refusals(session, 7, cosine=0.87)                      # analogous at 0.85, not at 0.90
    stand.reviews[run.run_id] = review_of(run, critic=ai("reject"))
    stand.pass_.compute_run(run.run_id)
    give_vectors(session, run, {0: axis(0)})
    stand.pass_.compute_run(run.run_id)
    turn_section_on(journalled_sessions, admin_uid)
    assert stand.queue(run) == [run.findings[0]]
    turn_section_on(journalled_sessions, admin_uid, analogous=0.9)
    assert stand.label_of(run)["votes"]["total"] == 0 and stand.queue(run) == [], "admitted at 0,90, the section counts only what is that near"


# -- the critic ----------------------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(("name", "review", "in_queue"), [
    ("v3 AI critic: reject, no veto", lambda run: review_of(run, critic=ai("reject")), True),
    ("v3 AI critic: accept is a veto", lambda run: review_of(run, critic=ai("accept")), False),
    ("v3 AI critic: needs_human is a veto", lambda run: review_of(run, critic=ai("needs_human")), False),
    ("v3 outside the AI critic's window", lambda run: review_of(run, status="not_reviewed"), False),
    ("v3, no candidate stands for the finding", lambda run: review_of(run, source="blk_" + "a" * 32), False),
    ("v3 with no saved review at all", lambda run: None, False),
    ("v2, the deterministic critic reviewed it", lambda run: review_of(run, workflow="extended-review-v2", marker=True, critic=deterministic("needs_human")), True),
    ("v2, the deterministic critic's pass does not veto", lambda run: review_of(run, workflow="extended-review-v2", marker=True, critic=deterministic("accept")), True),
    ("v2, the deterministic critic did not reach it", lambda run: review_of(run, workflow="extended-review-v2", marker=True), False),
    ("v2 without the marker: no critic in plan", lambda run: review_of(run, workflow="extended-review-v2", critic=deterministic("accept")), False),
])
def test_only_a_finding_a_critic_reviewed_without_an_ai_veto_enters_the_queue(
    stand: Stand, session: Session, journalled_sessions: sessionmaker[Session], admin_uid: str, name: str, review: Callable[[Run], Any], in_queue: bool,
) -> None:
    run = seed_run(session, ["Находка про отметку кровли"])
    seed_refusals(session)
    stand.reviews[run.run_id] = review(run)
    turn_section_on(journalled_sessions, admin_uid)
    stand.pass_.compute_run(run.run_id)
    give_vectors(session, run, {0: axis(0)})
    stand.pass_.compute_run(run.run_id)
    label = stand.label_of(run)
    assert (stand.queue(run) == [run.findings[0]]) is in_queue, (name, label)
    assert label["label"] == ("cancel_suggested" if in_queue else "often_rejected"), (name, label)
    assert label["critic_reviewed"] is (in_queue or "veto" in name or "needs_human" in name), (name, label)


def test_an_unreadable_saved_review_fails_the_pass_loudly_and_is_not_read_as_no_review(stand: Stand, session: Session, journalled_sessions: sessionmaker[Session]) -> None:
    run = seed_run(session, ["Находка про отметку кровли"])
    seed_refusals(session)
    stand.pass_.compute_run(run.run_id)
    give_vectors(session, run, {0: axis(0)})

    def broken(run_id: str) -> Any:
        raise DomainError(ErrorCode.STORAGE_INTEGRITY_ERROR, role="analysis.extended_review")

    failing = PrecedentPass(journalled_sessions, read_extended_review=broken, interval_seconds=0)
    outcome = failing.compute_run(run.run_id)
    assert (outcome.status, outcome.changed) == ("failed", True)
    with journalled_sessions() as check:
        assert tuple(check.execute(text("SELECT state, failure_code FROM decision_memory_precedent_run WHERE run_id = :r"), {"r": run.run_id}).one()) == (
            "failed", "critic_unreadable")
        assert check.execute(text("SELECT count(*) FROM decision_memory_precedent_advice WHERE run_id = :r"), {"r": run.run_id}).scalar_one() == 0
    assert stand.pass_.compute_run(run.run_id).status == "computed", "and the next pass, over a review that reads, recovers"


# -- the card -------------------------------------------------------------------------------------------------------------------------------------


def test_the_card_lists_the_similar_cases_the_reason_of_the_refusals_the_history_and_the_norms(
    stand: Stand, session: Session, journalled_sessions: sessionmaker[Session], admin_uid: str,
) -> None:
    run = seed_run(session, ["Находка про отметку пола"])
    refusals = seed_refusals(session, 6)
    earlier_version = VersionUid.new().value
    history = seed_case(session, verdict="rejected", vector=unit(0.95), days_ago=40, document=run.document_uid, version=earlier_version,
                        comment="Показано на другом листе")
    accepted = seed_case(session, verdict="accepted", vector=unit(0.8), days_ago=20, words="Принятая находка про ширину")   # similar, not analogous
    far = seed_case(session, verdict="rejected", vector=unit(0.5), days_ago=20)                                                # below similar
    other_section = seed_case(session, verdict="rejected", vector=unit(0.99), section="KM")
    stand.reviews[run.run_id] = review_of(run, critic=ai("reject"), norms=[norm()])
    turn_section_on(journalled_sessions, admin_uid)
    stand.pass_.compute_run(run.run_id)
    give_vectors(session, run, {0: axis(0)})
    stand.pass_.compute_run(run.run_id)

    card = stand.expert.get_finding_precedents(finding_uid=run.findings[0], user_uid="usr_x")
    assert card["available"] is True and card["run_id"] == run.run_id
    assert card["label"]["label"] == "cancel_suggested" and card["label"]["votes"] == {"total": 7, "rejected": 7, "accepted": 0, "independent": 7, "projects": 3}
    case_ids = [item["case_id"] for item in card["cases"]]
    assert case_ids[0] == history and set(case_ids) == {*refusals, history, accepted}, "best first; nothing of another section or below the similar threshold"
    assert far not in case_ids and other_section not in case_ids
    top = card["cases"][0]
    assert (top["verdict"], top["category"], round(top["similarity"], 2), top["comment"]) == ("rejected", CATEGORY, 0.95, "Показано на другом листе")
    assert next(item for item in card["cases"] if item["case_id"] == accepted)["verdict"] == "accepted"
    codes = [hint["code"] for hint in card["hints"]]
    assert codes == ["p1", "p5"] and card["label"]["hint_codes"] == ["p1", "p5"]
    assert card["hints"][0] == {"code": "p1", "text": "Показано на другом листе", "case_id": history}
    assert card["hints"][1] == {"code": "p5", "case_id": history}
    assert card["possible_norms"] == [{"norm_document_id": NDOC, "norm_paragraph_id": NPAR, "designation": "СП 54.13330.2022", "clause_number": "6.1", "page_label": 12}]
    shown = shown_at_decision(session, run.findings[0])
    assert (shown.label, shown.revision, shown.history_verdict_shown) == ("cancel_suggested", 1, "rejected"), "the history verdict shown is recorded"


def test_a_card_of_a_finding_with_no_vector_still_names_its_possible_norms(stand: Stand, session: Session) -> None:
    run = seed_run(session, ["Находка про уклон"])
    stand.reviews[run.run_id] = review_of(run, critic=ai("reject"), norms=[norm()])
    stand.pass_.compute_run(run.run_id)
    card = stand.expert.get_finding_precedents(finding_uid=run.findings[0], user_uid="usr_x")
    assert card["available"] is False and "label" not in card and card["possible_norms"][0]["norm_paragraph_id"] == NPAR, "the norms never depend on the encoder"


def test_the_card_never_lists_more_than_ten_cases(stand: Stand, session: Session) -> None:
    run = seed_run(session, ["Находка про лестницу"])
    for index in range(13):
        seed_case(session, verdict="accepted" if index % 2 else "rejected", vector=unit(0.8 + index * 0.01), days_ago=10 + index)
    stand.reviews[run.run_id] = review_of(run, critic=ai("reject"))
    stand.pass_.compute_run(run.run_id)
    give_vectors(session, run, {0: axis(0)})
    stand.pass_.compute_run(run.run_id)
    cases = stand.expert.get_finding_precedents(finding_uid=run.findings[0], user_uid="usr_x")["cases"]
    assert len(cases) == 10 and [item["similarity"] for item in cases] == sorted((item["similarity"] for item in cases), reverse=True)


def test_a_decision_taken_under_a_shown_refusal_is_not_an_independent_vote_and_a_hidden_one_is(
    stand: Stand, session: Session, journalled_sessions: sessionmaker[Session], admin_uid: str,
) -> None:
    """What ``shown_at_decision`` records is what the core later reads as the independence of that vote (`plan-v5` 2.1): the refusal that was shown makes the
    vote dependent, the refusal that the switch hid does not."""
    run = seed_run(session, ["Находка про карниз"])
    seed_refusals(session)
    stand.reviews[run.run_id] = review_of(run, critic=ai("reject"))
    stand.pass_.compute_run(run.run_id)
    give_vectors(session, run, {0: axis(0)})
    stand.pass_.compute_run(run.run_id)
    hidden = shown_at_decision(session, run.findings[0])
    turn_section_on(journalled_sessions, admin_uid)
    shown = shown_at_decision(session, run.findings[0])
    from auditmanager.precedents.models import DecisionEvent
    from auditmanager.precedents.votes import is_independent

    when = datetime.now(UTC)
    assert is_independent(DecisionEvent("accepted", when, "direct", hidden.label, None)) is True
    assert is_independent(DecisionEvent("accepted", when, "direct", shown.label, None)) is False


# -- who ----------------------------------------------------------------------------------------------------------------------------------------


def test_the_viewer_gets_permission_denied_and_an_expert_and_an_administrator_read(stand: Stand, session: Session, journalled_sessions: sessionmaker[Session]) -> None:
    run = seed_run(session, ["Находка про дверь"])
    for roles, allowed in ((VIEWER, False), (EXPERT, True), (ADMIN, True)):
        service = PrecedentService(journalled_sessions, roles_of=roles)
        for call in (lambda: service.get_run_precedents(run_id=run.run_id, user_uid="usr_x"),
                     lambda: service.get_finding_precedents(finding_uid=run.findings[0], user_uid="usr_x")):
            if allowed:
                assert call()["available"] is False
            else:
                with pytest.raises(DomainError) as caught:
                    call()
                assert caught.value.code is ErrorCode.PERMISSION_DENIED


def test_the_roles_are_read_through_the_access_boundary_for_the_seeded_administrator(journalled_sessions: sessionmaker[Session], admin_uid: str, session: Session) -> None:
    run = seed_run(session, ["Находка про окно"])
    assert PrecedentService(journalled_sessions).get_run_precedents(run_id=run.run_id, user_uid=admin_uid)["run_id"] == run.run_id
    with pytest.raises(DomainError) as caught:
        PrecedentService(journalled_sessions).get_run_precedents(run_id=run.run_id, user_uid="usr_01M2545JSD15ETSNNV904X991K")
    assert caught.value.code is ErrorCode.PERMISSION_DENIED, "an account that holds no role reads nothing"


# -- the pass chooses its runs -------------------------------------------------------------------------------------------------------------------


def test_the_pass_takes_a_finished_run_with_findings_once_and_leaves_the_rest_alone(stand: Stand, session: Session, journalled_sessions: sessionmaker[Session]) -> None:
    ready = seed_run(session, ["Готовая находка про лифт"])
    running = seed_run(session, ["Находка прогона, который идёт"], state="validating")
    empty = seed_run(session, [])
    big = PrecedentPass(journalled_sessions, read_extended_review=lambda _run_id: None, interval_seconds=0, batch=1000)
    assert big.compute_run(running.run_id).status == "not_ready"
    assert big.compute_run(empty.run_id).status == "no_findings"
    assert big.compute_run(RunId.new().value).status == "not_ready"
    moved = big.run_once()
    assert moved >= 1
    with journalled_sessions() as check:
        taken = {row[0] for row in check.execute(text("SELECT run_id FROM decision_memory_precedent_run")).all()}
    assert ready.run_id in taken and running.run_id not in taken and empty.run_id not in taken
    assert big.run_once() == 0, "a second tick finds nothing new"
    with journalled_sessions() as check:
        assert check.execute(text("SELECT count(*) FROM decision_memory_probe WHERE run_id = :r"), {"r": ready.run_id}).scalar_one() == 1


def test_a_run_whose_version_has_no_section_is_answered_with_no_neighbours(stand: Stand, session: Session) -> None:
    run = seed_run(session, ["Находка без раздела"], section=None)
    seed_refusals(session)
    stand.pass_.compute_run(run.run_id)
    give_vectors(session, run, {0: axis(0)})
    stand.pass_.compute_run(run.run_id)
    assert stand.label_of(run)["label"] == "none" and stand.label_of(run)["votes"]["total"] == 0, "a finding of no section has no corpus"


# -- the window encodes the probes ------------------------------------------------------------------------------------------------------------


def _load(name: str, filename: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] / "jobs" / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_the_night_window_encodes_the_probes_with_the_intents_and_its_after_import_hook_runs_the_pass(
    tmp_path: Path, stand: Stand, session: Session, journalled_sessions: sessionmaker[Session],
) -> None:
    w = _load("embed01_vector_window_support", "vector_window_support.py")
    w.reset_control(journalled_sessions)
    with journalled_sessions() as check:
        assert store.running_work(check) == 0, "a suite left work running: the drain below would wait for it"
    run = seed_run(session, ["Ночная находка про высоту помещения", "Ночная находка про ширину проёма"])
    stand.pass_.compute_run(run.run_id)
    assert stand.pass_.compute_run(run.run_id).status == "waiting_for_vectors"
    exchange_dir = tmp_path / "ex"
    exchange_dir.mkdir()
    exchange = Exchange(exchange_dir)
    vector_pass = VectorWindowPass(journalled_sessions, exchange, interval_seconds=0, after_import=stand.pass_.after_import)
    w.heartbeat(exchange_dir, w.INSIDE)
    vector_pass.run(w.INSIDE)
    assert w.control(journalled_sessions)["state"] == "encoding", "a pending probe alone opens the window"
    request = w.request_of(exchange_dir)
    asked = {item["id"] for item in request["texts"]}
    expected = {input_sha256(build_finding_view(category=CATEGORY, finding_text=words, recommendation_text="Привести в соответствие.")) for words in run.texts}
    assert expected <= asked, "the probes of the findings are in the batch"
    w.host_answers(exchange_dir)
    vector_pass.run(w.INSIDE)
    with journalled_sessions() as check:
        probes = check.execute(text("SELECT state, vector_dims(embedding), vector_norm(embedding) FROM decision_memory_probe WHERE run_id = :r"), {"r": run.run_id}).all()
        state = check.execute(text("SELECT state, revision FROM decision_memory_precedent_run WHERE run_id = :r"), {"r": run.run_id}).one()
        advice = check.execute(text("SELECT count(*) FROM decision_memory_precedent_advice WHERE run_id = :r"), {"r": run.run_id}).scalar_one()
    assert [(row[0], row[1]) for row in probes] == [("done", 1024), ("done", 1024)] and all(abs(float(row[2]) - 1.0) <= 0.0001 for row in probes)
    assert tuple(state) == ("done", 1) and advice == 2, "the hook ran the pass: both findings have their answer"
    w.reset_control(journalled_sessions)


def test_a_probe_over_the_token_limit_is_poisoned_and_its_finding_stays_without_an_answer(stand: Stand, session: Session) -> None:
    run = seed_run(session, ["Слишком длинная находка", "Обычная находка"])
    stand.pass_.compute_run(run.run_id)
    probes = {probe.input_id: probe for probe in store.pending_probe_texts(session, limit=500) if probe.run_id == run.run_id}
    long_digest = probes[run.findings[0]].input_sha256
    outcome = store.import_vectors(
        session, vectors=[EncodedVector(probes[run.findings[1]].input_sha256, digest("v"), tuple(axis(0)))], over_limit=[long_digest], rejected=(), missing=())
    assert (outcome.probes_done, outcome.probes_poisoned) == (1, 1)
    assert stand.pass_.compute_run(run.run_id).status == "computed"
    body = stand.expert.get_run_precedents(run_id=run.run_id, user_uid="usr_x")
    assert body["pass_state"] == "done" and [item["finding_uid"] for item in body["items"]] == [run.findings[1]]
    reason = session.execute(text("SELECT poison_reason FROM decision_memory_probe WHERE run_id = :r AND input_id = :i"), {"r": run.run_id, "i": run.findings[0]}).scalar_one()
    assert reason == "token_limit_exceeded"
