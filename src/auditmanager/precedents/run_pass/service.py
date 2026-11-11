"""The two reads behind ``getRunPrecedents`` and ``getFindingPrecedents`` (contract 1.51.0, plan-v5 sections 2.3, 2.5 and 3.4), and the mark in force at a decision.

The routes read and write nothing themselves and ask this service through the port of ``api/routers/precedents_ports.py``; the composition root wires
``PrecedentService(sessions, read_extended_review=...)`` into ``build_router(precedents=...)``. The service answers in the contract's shapes (mappings the
route validates against ``RunPrecedents`` and ``FindingPrecedents``), opens its own session and decides what the router may not:

* **who**: an expert or an administrator, checked here again although the authorization seam has refused the viewer (the register is the first line, not the
  only one): ``permission_denied``, and nothing is read;
* **what exists**: an unknown run or finding is ``not_found``. A run the pass has not reached, or whose findings have no vector, is **not** an error: it
  is ``available: false`` and an empty list, the line over the list that says the precedents are computed at night;
* **the list** (``getRunPrecedents``) is what the pass stored at its latest revision -- unless the memory has moved since the pass computed it (a case
  withdrawn, restored or forgotten, a stop word, a threshold or a section switch journalled): then it is **evaluated again at read time**, so a withdrawn
  case leaves the marks at once and not at the next night (`plan-v5` 2.1). The two answers are the same rules over the same inputs;
* **the card** (``getFindingPrecedents``) is always evaluated at read time (it needs the words of the similar cases and of a comment, which the stored
  advice does not keep), and its «Возможные нормы» come from the saved extended review of the run: the very paragraphs the critic gets, never from the encoder;
* **the per-section switch** is applied to what is shown (``evaluation.apply_section_switch``): where the section's refusal labels are off, a label to
  refusal is ``few``, the hints that spoke of it are dropped and the finding is not in the queue; the card also lists no similar cases, which would say
  the same thing in other words;
* **no vector means «Недоступно»**: ``available: false``, ``label`` absent, no hints and no cases. There is no search by words.

:func:`shown_at_decision` is the function the decision's capture calls to write ``precedent_label_at_decision``, ``precedent_revision`` and
``precedent_history_verdict_shown`` (`CRIT-CAPTURE-01`).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy.orm import Session, sessionmaker

from auditmanager.precedents import settings as journal
from auditmanager.precedents.models import HINT_DOCUMENT_HISTORY, VERDICT_ACCEPTED, VERDICT_REJECTED
from auditmanager.precedents.run_pass import evaluation, reads, store
from auditmanager.precedents.run_pass.critic_input import link, possible_norms, read_critic_plan
from auditmanager.precedents.run_pass.evaluation import Evaluation, LabelView
from auditmanager.precedents.votes import WINDOW_MONTHS, case_vote, months_before
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = ["CASES_ON_CARD", "PrecedentService", "ShownAtDecision", "shown_at_decision"]

#: ``FindingPrecedents.cases`` holds at most this many (the contract's ``maxItems``).
CASES_ON_CARD: Final[int] = 10
_READERS: Final[frozenset[str]] = frozenset({"expert", "admin"})
_EXTENDED_REVIEW_DEPENDENCY: Final[str] = "extended_review"


def _roles_of(session: Session, user_uid: str) -> frozenset[str]:
    from auditmanager.access.public import AccountRepository

    return frozenset(str(role) for role in AccountRepository().roles_of(session, user_uid))


@dataclass(frozen=True, slots=True)
class ShownAtDecision:
    """What the server was showing for a finding at the moment an expert decided: the mark in force, the pass revision it comes from and the verdict
    of the document's history (hint P5) that was shown, if one was. The three values of the new columns of ``decision_memory_decision``."""

    label: str
    revision: int
    history_verdict_shown: str | None


@dataclass(frozen=True, slots=True)
class _Card:
    """The one finding's evaluation at read time, with what the run's section and switch say about it."""

    finding_uid: str
    run_id: str
    revision: int
    evaluation: Evaluation
    view: LabelView
    section: str | None


def _votes_of(view: LabelView) -> dict[str, int]:
    return {key: int(view.votes[key]) for key in ("total", "rejected", "accepted", "independent", "projects")}


def _label_body(finding_uid: str, view: LabelView, revision: int) -> dict[str, Any]:
    return {
        "finding_uid": finding_uid, "label": view.label, "critic_reviewed": view.critic_reviewed, "votes": _votes_of(view),
        "hint_codes": list(view.hint_codes), "revision": revision,
    }


def _context(session: Session, run_id: str, version_uid: str) -> tuple[reads.RunFacts, reads.VersionPlace, Any, bool, Any]:
    run = reads.run_facts(session, run_id)
    if run is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Run")
    place = reads.version_place(session, version_uid)
    base = journal.read_thresholds(session)
    thresholds, on = evaluation.effective_thresholds(base, place.section, journal.read_section_labels(session))
    return run, place, thresholds, on, journal.read_stop_words(session)


def _card_core(session: Session, finding_uid: str, now: datetime) -> _Card | None:
    """The finding evaluated now, or ``None`` when it has no answer (no pass result for it, or no vector): the case of «Недоступно»."""
    head = reads.finding_head(session, finding_uid)
    if head is None:
        raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Finding")
    run_id, version_uid = head
    latest = store.latest_revision(session, run_id)
    if latest is None:
        return None
    stored = store.advice_at(session, run_id, latest).get(finding_uid)
    if stored is None:
        return None
    run, place, thresholds, on, stop_words = _context(session, run_id, version_uid)
    finding = next((item for item in reads.findings_of_run(session, run_id) if item.finding_uid == finding_uid), None)
    if finding is None:
        return None
    results = evaluation.evaluate_run(
        session, run=run, place=place, findings=[finding], projections={finding_uid: stored.votes.get("critic") or {}}, now=now,
        thresholds=thresholds, stop_words=stop_words, only=[finding_uid])
    result = results.get(finding_uid)
    if result is None:
        return None
    return _Card(finding_uid, run_id, latest, result, evaluation.view_from_advice(result.advice, section_on=on), place.section)


def shown_at_decision(session: Session, finding_uid: str, *, now: datetime | None = None) -> ShownAtDecision | None:
    """The mark in force for ``finding_uid`` right now, for the capture of an expert's decision to record. ``None`` when the finding has none (the pass
    has not given it a result, or it has no vector): the three columns stay NULL, which says «none was known».

    It is the card's own evaluation, so what is recorded is what the expert was shown when he opened the finding, counting the section's switch. Called inside
    the decision's transaction; reads only, and an unknown finding is ``not_found`` as it is for the card."""
    card = _card_core(session, finding_uid, now or datetime.now(UTC))
    if card is None:
        return None
    verdict: str | None = None
    if "p5" in card.view.hint_codes:
        verdict = next((hint.verdict for hint in card.evaluation.advice.hints if hint.code == HINT_DOCUMENT_HISTORY), None)
    return ShownAtDecision(card.view.shown_code, card.revision, verdict if verdict in (VERDICT_ACCEPTED, VERDICT_REJECTED) else None)


class PrecedentService:
    """The surface as the routes show it. ``read_extended_review`` is the saved extended review of a run (``runs.public.read_extended_review`` closed over
    the stores): without it the card has no «Возможные нормы»."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        read_extended_review: Callable[[str], Mapping[str, Any] | None] | None = None,
        clock: Callable[[], datetime] | None = None,
        roles_of: Callable[[Session, str], frozenset[str]] = _roles_of,
    ) -> None:
        self._sessions = session_factory
        self._read_extended = read_extended_review
        self._clock = clock or (lambda: datetime.now(UTC))
        self._roles_of = roles_of

    def _require_reader(self, session: Session, user_uid: str) -> None:
        if not (_READERS & self._roles_of(session, user_uid)):
            raise DomainError(ErrorCode.PERMISSION_DENIED, required_capability="role:admin|expert")

    # -- the list ------------------------------------------------------------------------------------------------------------

    def get_run_precedents(self, *, run_id: str, user_uid: str) -> dict[str, Any]:
        now = self._clock()
        with self._sessions() as session:
            self._require_reader(session, user_uid)
            run = reads.run_facts(session, run_id)
            if run is None:
                raise DomainError(ErrorCode.NOT_FOUND, aggregate_type="Run")
            row = store.run_row(session, run_id)
            body: dict[str, Any] = {"run_id": run_id, "available": False, "items": []}
            if row is None:
                return body
            body.update(pass_state=row.state, revision=row.revision)
            latest = store.latest_revision(session, run_id)
            if latest is None:
                return body
            stored = store.advice_at(session, run_id, latest)
            if not stored:
                return body
            place = reads.version_place(session, run.version_uid)
            thresholds, on = evaluation.effective_thresholds(journal.read_thresholds(session), place.section, journal.read_section_labels(session))
            if reads.memory_changed_since(session, max(item.computed_at for item in stored.values())):
                views = self._evaluated_again(session, run, place, thresholds, on, stored, now)
            else:
                views = {
                    uid: evaluation.view_from_stored(item.label, item.critic_reviewed, item.votes, item.hint_codes, section_on=on)
                    for uid, item in stored.items()
                }
            body["items"] = [_label_body(uid, views[uid], latest) for uid in sorted(views)]
            body.update(available=bool(body["items"]), revision=latest)
            return body

    def _evaluated_again(
        self, session: Session, run: reads.RunFacts, place: reads.VersionPlace, thresholds: Any, on: bool,
        stored: Mapping[str, store.StoredAdvice], now: datetime,
    ) -> dict[str, LabelView]:
        findings = [item for item in reads.findings_of_run(session, run.run_id) if item.finding_uid in stored]
        results = evaluation.evaluate_run(
            session, run=run, place=place, findings=findings, projections={uid: item.votes.get("critic") or {} for uid, item in stored.items()},
            now=now, thresholds=thresholds, stop_words=journal.read_stop_words(session), only=sorted(stored))
        return {uid: evaluation.view_from_advice(result.advice, section_on=on) for uid, result in results.items()}

    # -- the card ------------------------------------------------------------------------------------------------------------

    def get_finding_precedents(self, *, finding_uid: str, user_uid: str) -> dict[str, Any]:
        now = self._clock()
        with self._sessions() as session:
            self._require_reader(session, user_uid)
            card = _card_core(session, finding_uid, now)
            head = reads.finding_head(session, finding_uid)
            assert head is not None
            run_id = head[0]
            body: dict[str, Any] = {
                "finding_uid": finding_uid, "run_id": run_id, "available": False, "hints": [], "cases": [],
                "possible_norms": self._possible_norms(session, run_id, finding_uid),
            }
            if card is None:
                return body
            body.update(
                available=True, label=_label_body(finding_uid, card.view, card.revision), hints=self._hints(card),
                cases=[] if card.view.masked else self._cases(session, card, now))
            return body

    @staticmethod
    def _hints(card: _Card) -> list[dict[str, Any]]:
        """The card's hints: the core's, those the switch left standing, with the words of a rejecting voice for P1 (an expert's comment, never a model's)."""
        shown = set(card.view.hint_codes)
        out: list[dict[str, Any]] = []
        for hint in card.evaluation.advice.hints:
            code = evaluation.WIRE_HINT_CODES[hint.code]
            if code not in shown:
                continue
            item: dict[str, Any] = {"code": code}
            if hint.text:
                item["text"] = hint.text
            if hint.case_id is not None:
                item["case_id"] = hint.case_id
            out.append(item)
        return out

    @staticmethod
    def _cases(session: Session, card: _Card, now: datetime) -> list[dict[str, Any]]:
        """The similar cases, best first, at most ten: the cases the corpus rules admit (active, the finding's section and class, not its own run, with a
        verdict inside the window) at or above the similar threshold. The cosine of each is its similarity."""
        finding_section, window_start = card.section, months_before(now, WINDOW_MONTHS)
        eligible = []
        for item in card.evaluation.scored:
            case = item.case
            vote = case_vote(case, now)
            if (case.section is None or case.section != finding_section or case.run_id == card.run_id or vote is None
                    or vote.decided_at < window_start or vote.verdict not in (VERDICT_ACCEPTED, VERDICT_REJECTED)):
                continue
            eligible.append((item, vote))
        eligible.sort(key=lambda pair: (-pair[0].cosine, pair[0].case.case_id))
        chosen = eligible[:CASES_ON_CARD]
        texts = reads.case_texts(session, [pair[0].case.case_id for pair in chosen])
        cases: list[dict[str, Any]] = []
        for item, vote in chosen:
            words = texts.get(item.case.case_id)
            if words is None:
                continue
            entry: dict[str, Any] = {
                "case_id": item.case.case_id, "verdict": vote.verdict, "category": words.category,
                "similarity": round(max(0.0, min(1.0, item.cosine)), 6), "finding_text": words.finding_text[:4000],
            }
            commented = [comment for comment in item.case.comments if comment.text.strip()]
            if commented:
                entry["comment"] = max(commented, key=lambda comment: comment.written_at).text.strip()[:4000]
            cases.append(entry)
        return cases

    def _possible_norms(self, session: Session, run_id: str, finding_uid: str) -> list[dict[str, Any]]:
        """«Возможные нормы»: the paragraphs the finding's linked candidates stand on, from the run's saved extended review. A run that has none saved has
        none to show (an empty list). A review that exists and cannot be read is a ``dependency_unavailable``, not an empty list."""
        if self._read_extended is None:
            return []
        finding = next((item for item in reads.findings_of_run(session, run_id) if item.finding_uid == finding_uid), None)
        if finding is None:
            return []
        try:
            plan = read_critic_plan(self._read_extended(run_id))
        except DomainError:
            raise
        except Exception as exc:  # noqa: BLE001 - an unreadable review is told, not hidden as an empty list
            raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, dependency=_EXTENDED_REVIEW_DEPENDENCY) from exc
        linked = link(plan, extended_observation_refs=finding.extended_observation_refs, category=finding.category, finding_text=finding.finding_text)
        return [norm.as_dict() for norm in possible_norms(linked)]
