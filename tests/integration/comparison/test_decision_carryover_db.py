"""Confirmed decision carryover against PostgreSQL (`W59-DECISION-CARRYOVER-01`).

The ledger half is real: ``project``, ``document``, two ``document_version`` rows, two
``audit_run`` rows, the findings with their observations and evidence, accounts, decision
events, command records and the ``finding_current_verdict`` view, all in one rolled-back
transaction under the schema's triggers and CHECKs. Classifications, run lists and page text
come from port fakes (as in ``test_service_db.py``); published findings are read back from
the database the way the composition root's adapter reads them.

Fixture, two pages per version (page 1 identical, page 2 redrawn):

=====  =========================================  ============================
pair   source (V1)                                target (V2)
=====  =========================================  ============================
A      accepted (with a comment)                  no event        -> candidate
F      rejected                                   no event        -> candidate
E      rejected                                   a comment       -> not
B      no decision                                no event        -> not
S      accepted with severity ``critical``        can hold one    -> candidate
T      accepted with severity ``critical``        cannot hold one -> candidate
C      accepted, quote gone in V2                 --              -> probably_fixed
D      --                                         new             -> new
=====  =========================================  ============================
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, replace

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.access.public import ROLE_ADMIN, ROLE_EXPERT, UserRepository
from auditmanager.comparison.public import (
    CarryoverRequest,
    ComparisonRequest,
    DecisionCarryoverService,
    FindingEvidenceSnapshot,
    FindingSnapshot,
    RunCandidate,
    SavedPageText,
    SuppliedVersionClassification,
    VersionComparisonService,
    carryover_candidates,
)
from auditmanager.decisions.public import (
    CARRYOVER_COMMAND_TYPE,
    CarryoverProvenance,
    append_decision_under_key,
    carryover_comment,
    current_verdict,
    decision_history,
)
from auditmanager.findings.queries import published_finding_evidence, published_findings
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    AnalysisProfileId,
    DecisionId,
    DocumentUid,
    FindingObservationId,
    FindingUid,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)

PAGE_ONE = (
    "Лист 1. План этажа\n"
    "Степень огнестойкости здания — II.\n"
    "Высота этажа 3,3 м.\n"
    "Класс функциональной пожарной опасности Ф1.3.\n"
    "Ширина эвакуационного выхода 1,2 м.\n"
)
SOURCE_PAGE_TWO = (
    "Лист 2. Разрез 1-1\n"
    "Отметка кровли +12,600.\n"
    "Тип заполнения — уточнить.\n"
    "Утеплитель минераловатный 150 мм.\n"
    "Пароизоляция по всей площади.\n"
    "Гидроизоляция в два слоя.\n"
)
TARGET_PAGE_TWO = (
    "Лист 2. Разрез 1-1\n"
    "Отметка кровли +12,600.\n"
    "Тип заполнения — ПВХ.\n"
    "Утеплитель минераловатный 150 мм.\n"
    "Пароизоляция по всей площади.\n"
    "Гидроизоляция в два слоя.\n"
    "Новая отметка +13,000.\n"
)

#: name -> (category, finding text, page, quote)
ISSUES = {
    "A": ("internal_contradiction", "Степень огнестойкости указана по-разному.", 1,
          "Степень огнестойкости здания — II."),
    "F": ("internal_contradiction", "Толщина утеплителя не обоснована.", 2,
          "Утеплитель минераловатный 150 мм."),
    "E": ("internal_contradiction", "Высота этажа ниже нормы.", 1, "Высота этажа 3,3 м."),
    "B": ("internal_contradiction", "Не указан материал гидроизоляции.", 2,
          "Гидроизоляция в два слоя."),
    "S": ("layout", "Класс опасности не согласован с планировкой.", 1,
          "Класс функциональной пожарной опасности Ф1.3."),
    "T": ("layout", "Ширина выхода не обоснована.", 1, "Ширина эвакуационного выхода 1,2 м."),
    "C": ("explicit_placeholder", "Тип заполнения не определён.", 2, "Тип заполнения — уточнить."),
    "D": ("internal_contradiction", "Отметка не согласована.", 2, "Новая отметка +13,000."),
}
SOURCE_ISSUES = ("A", "F", "E", "B", "S", "T", "C")
TARGET_ISSUES = ("A", "F", "E", "B", "S", "T", "D")
#: Issues whose observation proposes a severity (the v2 discriminator), per side.
SEVERE = {"source": {"S", "T"}, "target": {"S"}}


@dataclass(frozen=True)
class Seeded:
    project_uid: str
    document_uid: str
    v1: str
    v2: str
    r1: str
    r2: str
    source: dict[str, tuple[str, str]]
    target: dict[str, tuple[str, str]]
    decisions: dict[str, str]
    expert: str
    second_expert: str
    admin: str
    foreign_finding: str


def _key() -> str:
    return f"w59carry-{uuid.uuid4().hex[:20]}"


def _account(session: Session) -> str:
    login = f"w59carry-{uuid.uuid4().hex[:12]}@example.com"
    return str(UserRepository().create_user(
        session, login, f"w59carry-passphrase-{uuid.uuid4().hex}",
    ).user_uid)


def _offset(page_text: str, page_start: int, quote: str) -> tuple[int, int]:
    start = page_text.index(quote)
    return page_start + start, page_start + start + len(quote)


def _finding(session: Session, *, project: str, version: str, run: str, profile: str,
             bundle: str, issue: str, pages: dict[int, str], severe: bool) -> tuple[str, str]:
    category, finding_text, page, quote = ISSUES[issue]
    finding_uid, observation = FindingUid.new().value, FindingObservationId.new().value
    session.execute(text(
        "INSERT INTO finding (finding_uid, project_uid, version_uid, allocated_by_run_id, "
        "category) VALUES (:f, :p, :v, :r, :c)"
    ), {"f": finding_uid, "p": project, "v": version, "r": run, "c": category})
    session.execute(text(
        "INSERT INTO finding_observation (finding_observation_id, run_id, finding_uid, "
        "stage_id, category, finding_text, recommendation_text, grounded, "
        "analysis_profile_id, prompt_bundle_id, provider_mode, proposed_severity) "
        "VALUES (:o, :r, :f, 'text_analysis', :c, :t, 'Устранить.', true, :ap, :pb, "
        "'recorded', :s)"
    ), {"o": observation, "r": run, "f": finding_uid, "c": category, "t": finding_text,
        "ap": profile, "pb": bundle, "s": "critical" if severe else None})
    session.execute(text(
        "UPDATE finding SET canonical_observation_id = :o WHERE finding_uid = :f"
    ), {"o": observation, "f": finding_uid})
    page_start = sum(len(pages[number]) for number in range(1, page))
    start, end = _offset(pages[page], page_start, quote)
    session.execute(text(
        "INSERT INTO finding_evidence (finding_observation_id, evidence_ordinal, page_number, "
        "quote, char_start, char_end) VALUES (:o, 0, :n, :q, :s, :e)"
    ), {"o": observation, "n": page, "q": quote, "s": start, "e": end})
    return finding_uid, observation


def _decide(session: Session, finding: tuple[str, str], event_type: str, *,
            severity: str | None = None, comment: str | None = None,
            author: str | None = None) -> str:
    event, _ = append_decision_under_key(
        session, finding_uid=finding[0], finding_observation_id=finding[1],
        event_type=event_type, severity=severity, comment=comment,
        idempotency_key=_key(), author_label="Исходный эксперт", author_user_uid=author,
    )
    return event.decision_id


def _seed(session: Session) -> Seeded:
    project, other_project = ProjectUid.new().value, ProjectUid.new().value
    document, other_document = DocumentUid.new().value, DocumentUid.new().value
    v1, v2, v_foreign = VersionUid.new().value, VersionUid.new().value, VersionUid.new().value
    r1, r2, r_foreign = RunId.new().value, RunId.new().value, RunId.new().value
    profile, bundle = AnalysisProfileId.new().value, PromptBundleId.new().value
    for p in (project, other_project):
        session.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'Перенос')"),
                        {"p": p})
    for d, p in ((document, project), (other_document, other_project)):
        session.execute(text(
            "INSERT INTO document (document_uid, project_uid, display_title) "
            "VALUES (:d, :p, 'Комплект АР')"
        ), {"d": d, "p": p})
    for v, d, ordinal in ((v1, document, 1), (v2, document, 2), (v_foreign, other_document, 1)):
        session.execute(text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
            "media_type, byte_size, sha256, page_count) "
            "VALUES (:v, :d, :o, 'application/pdf', 2048, :s, 2)"
        ), {"v": v, "d": d, "o": ordinal, "s": hashlib.sha256(v.encode()).hexdigest()})
    for r, p, v in ((r1, project, v1), (r2, project, v2), (r_foreign, other_project, v_foreign)):
        session.execute(text(
            "INSERT INTO audit_run (run_id, project_uid, version_uid, state, "
            "analysis_profile_id, prompt_bundle_id, provider_mode, frozen_input_digest) "
            "VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :s)"
        ), {"r": r, "p": p, "v": v, "ap": profile, "pb": bundle,
            "s": hashlib.sha256(r.encode()).hexdigest()})
    source_pages = {1: PAGE_ONE, 2: SOURCE_PAGE_TWO}
    target_pages = {1: PAGE_ONE, 2: TARGET_PAGE_TWO}
    source = {
        issue: _finding(session, project=project, version=v1, run=r1, profile=profile,
                        bundle=bundle, issue=issue, pages=source_pages,
                        severe=issue in SEVERE["source"])
        for issue in SOURCE_ISSUES
    }
    target = {
        issue: _finding(session, project=project, version=v2, run=r2, profile=profile,
                        bundle=bundle, issue=issue, pages=target_pages,
                        severe=issue in SEVERE["target"])
        for issue in TARGET_ISSUES
    }
    foreign = _finding(session, project=other_project, version=v_foreign, run=r_foreign,
                       profile=profile, bundle=bundle, issue="A", pages=source_pages,
                       severe=False)
    decisions = {
        "A": _decide(session, source["A"], "accept", comment="Подтверждаю."),
        "F": _decide(session, source["F"], "reject"),
        "E": _decide(session, source["E"], "reject"),
        "S": _decide(session, source["S"], "accept", severity="critical"),
        "T": _decide(session, source["T"], "accept", severity="critical"),
        "C": _decide(session, source["C"], "accept"),
    }
    _decide(session, target["E"], "comment", comment="Посмотрю позже.")
    return Seeded(
        project, document, v1, v2, r1, r2, source, target, decisions,
        _account(session), _account(session), _account(session), foreign[0],
    )


class _Classifications:
    def __init__(self, stored: dict[str, tuple[str, str]]) -> None:
        self._stored = stored

    def read_classification(self, session, *, version_uid):  # noqa: ANN001, ANN201
        value = self._stored.get(version_uid)
        return None if value is None else SuppliedVersionClassification(version_uid, *value)


class _Analyses:
    """Runs and page text from the fixture; published findings from the database."""

    def __init__(self, runs: dict[str, tuple[str, ...]], pages: dict[str, dict[int, str]]):
        self._runs, self._pages = runs, pages

    def runs_newest_first(self, session, *, version_uid):  # noqa: ANN001, ANN201
        return tuple(RunCandidate(run, "published") for run in self._runs.get(version_uid, ()))

    def saved_page_text(self, session, *, run_id, version):  # noqa: ANN001, ANN201
        return SavedPageText(run_id, "e" * 64, self._pages[run_id])

    def published_findings(self, session, *, run_id):  # noqa: ANN001, ANN201
        evidence: dict[str, list] = {}
        for item in published_finding_evidence(session, run_id):
            evidence.setdefault(item.finding_observation_id, []).append(item)
        return tuple(
            FindingSnapshot(
                row.finding_uid, row.finding_observation_id, row.category, row.finding_text,
                tuple(FindingEvidenceSnapshot(item.page_number, item.quote)
                      for item in evidence.get(row.finding_observation_id, ())),
            )
            for row in published_findings(session, run_id)
        )


def _comparisons(seeded: Seeded, *, classes=None, runs=None, pages=None):  # noqa: ANN001, ANN202
    return VersionComparisonService(
        classifications=_Classifications(
            classes or {seeded.v1: ("R", "AR"), seeded.v2: ("R", "AR")}
        ),
        analyses=_Analyses(
            runs or {seeded.v1: (seeded.r1,), seeded.v2: (seeded.r2,)},
            pages or {
                seeded.r1: {1: PAGE_ONE, 2: SOURCE_PAGE_TWO},
                seeded.r2: {1: PAGE_ONE, 2: TARGET_PAGE_TWO},
            },
        ),
        section_codes=frozenset({"AR", "KJ"}),
    )


def _request(seeded: Seeded, issue: str, **changes) -> CarryoverRequest:  # noqa: ANN003
    return replace(CarryoverRequest(
        project_uid=seeded.project_uid, document_uid=seeded.document_uid,
        source_version_uid=seeded.v1, target_version_uid=seeded.v2,
        source_finding_uid=seeded.source[issue][0],
        target_finding_uid=seeded.target[issue][0],
        source_decision_id=changes.pop("source_decision_id", None) or seeded.decisions[issue],
    ), **changes)


def _carry(session: Session, seeded: Seeded, request: CarryoverRequest, *,
           actor: str | None = None, label: str = "Иванова Е. В.",
           roles: frozenset[str] = frozenset({ROLE_EXPERT}), key: str | None = None,
           comparisons: VersionComparisonService | None = None):  # noqa: ANN202
    return DecisionCarryoverService(comparisons=comparisons or _comparisons(seeded)).carry_over(
        session, request, actor_uid=actor or seeded.expert, actor_label=label,
        actor_roles=roles, idempotency_key=key or _key(),
    )


def _refusal(call) -> DomainError:  # noqa: ANN001
    with pytest.raises(DomainError) as caught:
        call()
    return caught.value


def _events(session: Session, finding_uid: str) -> int:
    return session.execute(text(
        "SELECT count(*) FROM expert_decision_event WHERE finding_uid = :f"
    ), {"f": finding_uid}).scalar_one()


@pytest.fixture
def seeded(comparison_session: Session) -> Seeded:
    return _seed(comparison_session)


# -- the read ------------------------------------------------------------------------


def test_candidates_are_unchanged_pairs_with_a_decided_source_and_an_untouched_target(
    comparison_session: Session, seeded: Seeded,
) -> None:
    comparison = _comparisons(seeded).compare(comparison_session, ComparisonRequest(
        seeded.project_uid, seeded.document_uid, seeded.v1, seeded.v2,
    ))
    kinds = {
        (p.source_finding.finding_uid if p.source_finding else None,
         p.target_finding.finding_uid if p.target_finding else None): p.kind
        for p in comparison.findings.proposals
    }
    assert kinds[(seeded.source["C"][0], None)] == "probably_fixed"
    assert kinds[(None, seeded.target["D"][0])] == "new"
    for issue in "AFEBST":
        assert kinds[(seeded.source[issue][0], seeded.target[issue][0])] == "unchanged"

    candidates = carryover_candidates(comparison_session, comparison)
    by_target = {item.target_finding.finding_uid: item for item in candidates}
    assert set(by_target) == {seeded.target[issue][0] for issue in "AFST"}
    a = by_target[seeded.target["A"][0]]
    assert a.source_finding.finding_uid == seeded.source["A"][0]
    assert (a.source_decision.decision_id, a.source_decision.verdict) == (
        seeded.decisions["A"], "accepted",
    )
    assert (a.source_decision.comment, a.source_decision.author_label) == (
        "Подтверждаю.", "Исходный эксперт",
    )
    assert a.source_decision.recorded_at is not None
    assert by_target[seeded.target["F"][0]].source_decision.verdict == "rejected"
    assert by_target[seeded.target["S"][0]].source_decision.severity == "critical"
    # In the proposals' order, so a page shows them as the comparison lists them.
    order = [p.target_finding.finding_uid for p in comparison.findings.proposals
             if p.target_finding and p.target_finding.finding_uid in by_target]
    assert [item.target_finding.finding_uid for item in candidates] == order


def test_a_refused_comparison_has_no_candidates(comparison_session, seeded) -> None:
    comparison = _comparisons(seeded, classes={seeded.v2: ("R", "AR")}).compare(
        comparison_session,
        ComparisonRequest(seeded.project_uid, seeded.document_uid, seeded.v1, seeded.v2),
    )
    assert comparison.outcome == "refused"
    assert carryover_candidates(comparison_session, comparison) == ()


# -- the command ---------------------------------------------------------------------


def test_a_confirmed_carryover_appends_one_attributed_event_with_its_provenance(
    comparison_session: Session, seeded: Seeded,
) -> None:
    source_before = decision_history(comparison_session, seeded.source["A"][0])
    outcome = _carry(comparison_session, seeded, _request(seeded, "A"))

    assert outcome.replayed is False
    event = outcome.event
    assert (event.finding_uid, event.finding_observation_id) == seeded.target["A"]
    assert (event.event_type, event.verdict, event.severity) == ("accept", "accepted", None)
    assert (event.author_user_uid, event.author_label) == (seeded.expert, "Иванова Е. В.")
    expected = carryover_comment(CarryoverProvenance(
        seeded.source["A"][0], seeded.decisions["A"], seeded.v1, 1, seeded.v2, "version",
    ))
    assert event.comment == expected
    for fragment in ("из версии 1", "сравнение версий", seeded.decisions["A"],
                     seeded.source["A"][0], seeded.v1, seeded.v2):
        assert fragment in expected
    assert outcome.target_current_verdict == "accepted"
    assert (outcome.source_decision.decision_id, outcome.source_version_ordinal) == (
        seeded.decisions["A"], 1,
    )
    # The source and its ledger are only read.
    assert decision_history(comparison_session, seeded.source["A"][0]) == source_before
    # The command record repeats the provenance, under the carryover's own command type.
    record = comparison_session.execute(text(
        "SELECT c.command_type, c.state, c.outcome FROM command_record c "
        "JOIN expert_decision_event e ON e.command_id = c.command_id "
        "WHERE e.decision_id = :d"
    ), {"d": event.decision_id}).one()
    assert (record.command_type, record.state) == (CARRYOVER_COMMAND_TYPE, "succeeded")
    assert record.outcome == {
        "decision_id": event.decision_id, "source_decision_id": seeded.decisions["A"],
        "source_finding_uid": seeded.source["A"][0], "source_version_uid": seeded.v1,
        "target_version_uid": seeded.v2, "mode": "version",
    }
    # Carried, it is no longer a candidate.
    comparison = _comparisons(seeded).compare(comparison_session, ComparisonRequest(
        seeded.project_uid, seeded.document_uid, seeded.v1, seeded.v2,
    ))
    remaining = {c.target_finding.finding_uid for c in carryover_candidates(
        comparison_session, comparison)}
    assert seeded.target["A"][0] not in remaining and seeded.target["F"][0] in remaining


def test_a_rejection_is_carried_as_a_rejection(comparison_session, seeded) -> None:
    outcome = _carry(comparison_session, seeded, _request(seeded, "F"))
    assert (outcome.event.event_type, outcome.event.verdict) == ("reject", "rejected")
    assert current_verdict(comparison_session, seeded.target["F"][0]).current_verdict == "rejected"


def test_an_exact_repeat_answers_the_first_event_and_its_expert(comparison_session, seeded) -> None:
    key = _key()
    first = _carry(comparison_session, seeded, _request(seeded, "A"), key=key)
    same_key = _carry(comparison_session, seeded, _request(seeded, "A"), key=key)
    other_expert = _carry(comparison_session, seeded, _request(seeded, "A"),
                          actor=seeded.second_expert, label="Петров П. П.")
    assert same_key.replayed and other_expert.replayed
    assert same_key.event == first.event == other_expert.event
    assert other_expert.event.author_user_uid == seeded.expert
    assert _events(comparison_session, seeded.target["A"][0]) == 1


def test_one_key_for_another_carryover_is_a_reused_key(comparison_session, seeded) -> None:
    key = _key()
    _carry(comparison_session, seeded, _request(seeded, "A"), key=key)
    refused = _refusal(lambda: _carry(comparison_session, seeded, _request(seeded, "F"), key=key))
    assert refused.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
    assert _events(comparison_session, seeded.target["F"][0]) == 0


@pytest.mark.parametrize("roles", [frozenset({ROLE_ADMIN}), frozenset()])
def test_only_an_expert_carries_and_admin_alone_does_not(comparison_session, seeded, roles) -> None:
    refused = _refusal(lambda: _carry(
        comparison_session, seeded, _request(seeded, "A"), actor=seeded.admin, roles=roles,
    ))
    assert refused.code is ErrorCode.PERMISSION_DENIED
    assert dict(refused.detail_fields) == {"required_capability": "role:expert"}
    assert _events(comparison_session, seeded.target["A"][0]) == 0
    both = _carry(comparison_session, seeded, _request(seeded, "A"), actor=seeded.admin,
                  roles=frozenset({ROLE_ADMIN, ROLE_EXPERT}))
    assert both.event.author_user_uid == seeded.admin


def _conflict_reason(refused: DomainError) -> str:
    assert refused.code is ErrorCode.CONFLICT, refused
    return refused.detail_fields["conflict_reason"]


def test_a_target_with_any_event_refuses_the_carryover(comparison_session, seeded) -> None:
    refused = _refusal(lambda: _carry(comparison_session, seeded, _request(seeded, "E")))
    assert _conflict_reason(refused) == "carryover_target_already_decided"
    assert _events(comparison_session, seeded.target["E"][0]) == 1
    # A carried target is decided too: a later source verdict cannot be carried over it.
    _carry(comparison_session, seeded, _request(seeded, "A"))
    newer = _decide(comparison_session, seeded.source["A"], "reject")
    refused = _refusal(lambda: _carry(
        comparison_session, seeded, _request(seeded, "A", source_decision_id=newer),
    ))
    assert _conflict_reason(refused) == "carryover_target_already_decided"


def test_a_source_decision_that_is_no_longer_current_is_refused(comparison_session, seeded) -> None:
    _decide(comparison_session, seeded.source["A"], "reject")
    stale = _refusal(lambda: _carry(comparison_session, seeded, _request(seeded, "A")))
    assert _conflict_reason(stale) == "carryover_source_decision_not_current"
    undecided = _refusal(lambda: _carry(comparison_session, seeded, _request(
        seeded, "B", source_decision_id=DecisionId.new().value,
    )))
    assert _conflict_reason(undecided) == "carryover_source_decision_not_current"
    foreign_decision = _refusal(lambda: _carry(comparison_session, seeded, _request(
        seeded, "F", source_decision_id=seeded.decisions["E"],
    )))
    assert _conflict_reason(foreign_decision) == "carryover_source_decision_not_current"
    # The same verdict, given again, is a newer decision: the one shown is no longer current.
    _decide(comparison_session, seeded.source["F"], "reject", comment="Повторно.")
    superseded = _refusal(lambda: _carry(comparison_session, seeded, _request(seeded, "F")))
    assert _conflict_reason(superseded) == "carryover_source_decision_not_current"
    assert _events(comparison_session, seeded.target["A"][0]) == 0
    assert _events(comparison_session, seeded.target["F"][0]) == 0


@pytest.mark.parametrize(
    "pair",
    [
        ("A", "F"),         # crossed: both unchanged, but not with each other
        ("swap", "A"),      # the target finding named as the source
        ("C", "D"),         # probably_fixed source and a new target: never a pair
        ("same", "A"),      # one finding twice
        ("foreign", "A"),   # a finding of another project's version
        ("unknown", "A"),   # a well-formed identity no finding carries
    ],
)
def test_a_pair_the_comparison_does_not_propose_is_refused(comparison_session, seeded, pair) -> None:
    source_name, target_name = pair
    source_uid = {
        "swap": seeded.target["A"][0], "same": seeded.target["A"][0],
        "foreign": seeded.foreign_finding, "unknown": FindingUid.new().value,
    }.get(source_name) or seeded.source[source_name][0]
    request = _request(
        seeded, "A", source_finding_uid=source_uid,
        target_finding_uid=seeded.target[target_name][0],
        source_decision_id=seeded.decisions.get(source_name, seeded.decisions["A"]),
    )
    refused = _refusal(lambda: _carry(comparison_session, seeded, request))
    assert _conflict_reason(refused) == "carryover_pair_not_proposed"
    assert _events(comparison_session, seeded.target[target_name][0]) == 0


def test_a_pair_a_newer_run_no_longer_proposes_is_refused(comparison_session, seeded) -> None:
    newer = RunId.new().value
    comparison_session.execute(text(
        "INSERT INTO audit_run (run_id, project_uid, version_uid, state, analysis_profile_id, "
        "prompt_bundle_id, provider_mode, frozen_input_digest) SELECT :r, project_uid, "
        "version_uid, 'created', analysis_profile_id, prompt_bundle_id, provider_mode, :s "
        "FROM audit_run WHERE run_id = :old"
    ), {"r": newer, "old": seeded.r2, "s": "f" * 64})
    pages = {
        seeded.r1: {1: PAGE_ONE, 2: SOURCE_PAGE_TWO},
        seeded.r2: {1: PAGE_ONE, 2: TARGET_PAGE_TWO},
        newer: {1: PAGE_ONE, 2: TARGET_PAGE_TWO},
    }
    moved_on = _comparisons(
        seeded, runs={seeded.v1: (seeded.r1,), seeded.v2: (newer, seeded.r2)}, pages=pages,
    )
    refused = _refusal(lambda: _carry(
        comparison_session, seeded, _request(seeded, "A"), comparisons=moved_on,
    ))
    assert _conflict_reason(refused) == "carryover_pair_not_proposed"
    # Naming the run the expert was shown keeps the comparison -- and the pair -- as it was.
    pinned = _carry(comparison_session, seeded, _request(seeded, "A", target_run_id=seeded.r2),
                    comparisons=moved_on)
    assert pinned.event.finding_uid == seeded.target["A"][0]


def test_a_refused_comparison_proposes_nothing_to_carry(comparison_session, seeded) -> None:
    unclassified = _comparisons(seeded, classes={seeded.v1: ("R", "AR")})
    refused = _refusal(lambda: _carry(
        comparison_session, seeded, _request(seeded, "A"), comparisons=unclassified,
    ))
    assert _conflict_reason(refused) == "carryover_pair_not_proposed"
    wrong_mode = _refusal(lambda: _carry(comparison_session, seeded, _request(seeded, "A", mode="stage")))
    assert _conflict_reason(wrong_mode) == "carryover_pair_not_proposed"


def test_the_design_to_working_mode_is_recorded_in_the_provenance(comparison_session, seeded) -> None:
    staged = _comparisons(seeded, classes={seeded.v1: ("P", "AR"), seeded.v2: ("R", "AR")})
    outcome = _carry(comparison_session, seeded, _request(seeded, "A", mode="stage"),
                     comparisons=staged)
    assert outcome.mode == "stage"
    assert "сравнение стадий П → Р" in outcome.event.comment


def test_a_severity_is_carried_with_the_accept(comparison_session, seeded) -> None:
    outcome = _carry(comparison_session, seeded, _request(seeded, "S"))
    assert (outcome.event.event_type, outcome.event.severity) == ("accept", "critical")
    assert current_verdict(comparison_session, seeded.target["S"][0]).decided_severity == "critical"


def test_a_severity_the_target_cannot_hold_is_refused_not_dropped(comparison_session, seeded) -> None:
    refused = _refusal(lambda: _carry(comparison_session, seeded, _request(seeded, "T")))
    assert _conflict_reason(refused) == "carryover_severity_not_carryable"
    assert _events(comparison_session, seeded.target["T"][0]) == 0


def test_an_unknown_path_is_not_found(comparison_session, seeded) -> None:
    other = _refusal(lambda: _carry(comparison_session, seeded, _request(
        seeded, "A", project_uid=ProjectUid.new().value,
    )))
    assert other.code is ErrorCode.NOT_FOUND


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_finding_uid", "fnd_not-an-id"),
        ("source_decision_id", "dec_"),
        ("target_version_uid", "doc_01M2545JSD15ETSNNV904XA001"),
        ("target_run_id", "run_x"),
        ("mode", "object"),
    ],
)
def test_a_malformed_request_is_refused_before_anything_is_read(
    comparison_session, seeded, field, value,
) -> None:
    refused = _refusal(lambda: _carry(comparison_session, seeded, _request(seeded, "A", **{field: value})))
    assert refused.code is ErrorCode.VALIDATION_FAILED
    assert refused.detail_fields["field"] == field
