"""`RUN-RESTART-01` (`R-155b`): the decisions of a restart's lineage carried to the run that replaced it, on real PostgreSQL.

The unit suite (``tests/unit/decisions/test_restart_carry_plan.py``) holds every matching rule. This one holds what only the database can say: the
events the ledger really holds and the projection reads, the command per carried event and its unique key, the marker and the sweeper's question,
the lock that keeps an expert's own decision on the target, the origin the wire reads back (run and mode), and the failure of the decision memory's
port, which must leave the batch standing.

Isolation is by rollback, as next door (the ledger refuses DELETE): the sessions the carry opens are bound to the test's own connection and
joined to its transaction through savepoints, so the carry commits for itself and nothing survives the test.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.access.public import UserRepository
from auditmanager.decisions.public import (
    CARRY_DECISION_COMMAND_TYPE,
    CARRY_RUN_COMMAND_TYPE,
    append_decision_under_key,
    carried_origins,
    carry_restart_decisions,
    current_verdict,
    current_verdict_origins,
    decision_history,
    decision_journal,
    pending_restart_carries,
    register_decision_recorded,
    registered_decision_recorded,
)
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import (
    AnalysisProfileId,
    CommandId,
    DocumentUid,
    FindingObservationId,
    FindingUid,
    ProjectUid,
    PromptBundleId,
    RunId,
    VersionUid,
)

QUOTE = "Высота этажа 3,3 м."


@pytest.fixture(autouse=True)
def _no_port_left_behind() -> Iterator[None]:
    """No decision memory is wired in this suite unless a test installs a port; whatever it installs is removed."""
    before = registered_decision_recorded()
    register_decision_recorded(None)
    yield
    register_decision_recorded(before)


@pytest.fixture
def carrying(session: Session) -> sessionmaker[Session]:
    """The sessions the carry opens: on the test's connection, each one a savepoint of the test's transaction."""
    return sessionmaker(bind=session.get_bind(), expire_on_commit=False, future=True, join_transaction_mode="create_savepoint")


def _digest(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


class Stand:
    """One project, one document version, the accounts, and the runs of one restart chain."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.project_uid, document_uid = ProjectUid.new().value, DocumentUid.new().value
        self.version_uid = VersionUid.new().value
        self.profile, self.bundle = AnalysisProfileId.new().value, PromptBundleId.new().value
        session.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'Проект')"), {"p": self.project_uid})
        session.execute(
            text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, 'АР')"),
            {"d": document_uid, "p": self.project_uid},
        )
        session.execute(
            text(
                "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, sha256, page_count) "
                "VALUES (:v, :d, 1, 'application/pdf', 1024, :s, 2)"
            ),
            {"v": self.version_uid, "d": document_uid, "s": _digest(self.version_uid)},
        )
        self.actor = self.account("starter")
        self.other_expert = self.account("other")

    def account(self, name: str) -> str:
        login = f"restartcarry-{name}-{uuid.uuid4().hex[:10]}@example.com"
        return str(UserRepository().create_user(self.session, login, f"restartcarry-passphrase-{uuid.uuid4().hex}").user_uid)

    def command(self, command_type: str = "restart_run") -> str:
        """A succeeded command record (a command is created ``in_progress`` and moves once)."""
        command_id = CommandId.new().value
        self.session.execute(
            text(
                "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
                "VALUES (:c, :t, :k, :f)"
            ),
            {"c": command_id, "t": command_type, "k": f"rr-{uuid.uuid4().hex}", "f": _digest(command_id)},
        )
        self.session.execute(
            text("UPDATE command_record SET state = 'succeeded', outcome = CAST('{}' AS jsonb) WHERE command_id = :c"), {"c": command_id},
        )
        return command_id

    #: The path a run takes to each state: ``audit_run`` is created in ``created`` only, and every move is a transition of the state machine.
    _PATHS = {
        "created": (), "queued": ("queued",), "running": ("queued", "running"), "cancelled": ("cancelled",),
        "failed": ("queued", "failed"), "published": ("queued", "running", "validating", "published"),
        "partial": ("queued", "running", "validating", "partial"),
    }

    def run(self, state: str, *, source: str | None = None, restart_point: str | None = None) -> str:
        """A run of the version, moved to ``state`` the way the machine allows. A restart names its source, its starter and its command
        (the CHECKs of migration 0071 require them)."""
        run_id = RunId.new().value
        self.session.execute(
            text(
                "INSERT INTO audit_run (run_id, project_uid, version_uid, state, analysis_profile_id, prompt_bundle_id, provider_mode, "
                "frozen_input_digest, started_by_user_uid, started_from_run_id, restart_point, command_id) "
                "VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :s, :starter, :source, :point, :command)"
            ),
            {
                "r": run_id, "p": self.project_uid, "v": self.version_uid, "ap": self.profile, "pb": self.bundle, "s": _digest(run_id),
                "starter": self.actor if restart_point else None, "source": source, "point": restart_point,
                "command": self.command() if restart_point else None,
            },
        )
        for step in self._PATHS[state]:
            terminal = step in ("published", "partial", "failed", "cancelled")
            self.session.execute(
                text(
                    "UPDATE audit_run SET state = :step, terminal_at = CASE WHEN :terminal THEN now() END, "
                    "terminal_reason = CASE WHEN :step = 'failed' THEN 'analysis_failed' END, "
                    "degradation_set = CAST(:degradation AS jsonb) WHERE run_id = :r"
                ),
                {"step": step, "terminal": terminal, "r": run_id, "degradation": '["critic_timeout"]' if step == "partial" else "[]"},
            )
        return run_id

    def finding(
        self, run_id: str, finding_text: str = "Высота этажа не указана.", *, category: str = "dimensions",
        recommendation: str = "Указать высоту.", evidence: tuple[tuple[int, str, int, int], ...] | None = None,
        ref: str | None = None, severity: str | None = None,
    ) -> tuple[str, str]:
        """A published finding with one canonical observation; ``(finding_uid, finding_observation_id)``."""
        finding_uid, observation_id = FindingUid.new().value, FindingObservationId.new().value
        rows = ((1, QUOTE, 40, 40 + len(QUOTE)),) if evidence is None else evidence
        self.session.execute(
            text(
                "INSERT INTO finding (finding_uid, project_uid, version_uid, allocated_by_run_id, category) "
                "VALUES (:f, :p, :v, :r, :c)"
            ),
            {"f": finding_uid, "p": self.project_uid, "v": self.version_uid, "r": run_id, "c": category},
        )
        self.session.execute(
            text(
                "INSERT INTO finding_observation (finding_observation_id, run_id, finding_uid, stage_id, category, finding_text, "
                "recommendation_text, grounded, analysis_profile_id, prompt_bundle_id, provider_mode, proposed_severity, "
                "extended_observation_ref) "
                "VALUES (:o, :r, :f, 'text_analysis', :c, :t, :rec, true, :ap, :pb, 'recorded', :sev, :ref)"
            ),
            {
                "o": observation_id, "r": run_id, "f": finding_uid, "c": category, "t": finding_text, "rec": recommendation,
                "ap": self.profile, "pb": self.bundle, "sev": severity, "ref": ref,
            },
        )
        self.session.execute(
            text("UPDATE finding SET canonical_observation_id = :o WHERE finding_uid = :f"), {"o": observation_id, "f": finding_uid},
        )
        for ordinal, (page, quote, start, end) in enumerate(rows):
            self.session.execute(
                text(
                    "INSERT INTO finding_evidence (finding_observation_id, evidence_ordinal, page_number, quote, char_start, char_end) "
                    "VALUES (:o, :n, :p, :q, :s, :e)"
                ),
                {"o": observation_id, "n": ordinal, "p": page, "q": quote, "s": start, "e": end},
            )
        return finding_uid, observation_id

    def decide(
        self, finding: tuple[str, str], event_type: str, *, comment: str | None = None, severity: str | None = None,
        author: str | None = None,
    ) -> Any:
        event, _ = append_decision_under_key(
            self.session, finding_uid=finding[0], finding_observation_id=finding[1], event_type=event_type,
            idempotency_key=f"rrdecide-{uuid.uuid4().hex}", severity=severity, comment=comment,
            author_label="Иванов И. И.", author_user_uid=author or self.other_expert,
        )
        return event

    def history(self, finding_uid: str) -> tuple[Any, ...]:
        return decision_history(self.session, finding_uid)


@pytest.fixture
def stand(session: Session) -> Stand:
    return Stand(session)


@pytest.fixture
def chain(stand: Stand) -> tuple[str, str]:
    """A failed root and the restart that replaced it, published: ``(root, target)``."""
    root = stand.run("failed")
    return root, stand.run("published", source=root, restart_point="review")


def _recorded_port() -> tuple[list[tuple[str, str, str | None]], Callable[..., None]]:
    seen: list[tuple[str, str, str | None]] = []

    def port(session: Session, event: Any, origin_kind: str) -> None:  # noqa: ARG001
        seen.append((origin_kind, event.event_type, event.carried_from_decision_id))

    return seen, port


class TestTheCarry:
    def test_verdicts_and_comments_reach_the_matching_findings_as_events_of_the_restart_starter(
        self, stand: Stand, chain: tuple[str, str], carrying: sessionmaker[Session],
    ) -> None:
        root, target = chain
        accepted, rejected = stand.finding(root, "Текст А."), stand.finding(root, "Текст Б.")
        undecided = stand.finding(root, "Текст В.")
        new_accepted, new_rejected = stand.finding(target, "Текст А."), stand.finding(target, "Текст Б.")
        new_undecided = stand.finding(target, "Текст В.")
        stand.finding(target, "Совсем новое замечание.")
        said_accept = stand.decide(accepted, "accept")
        said_reject = stand.decide(rejected, "reject", comment="Это не ошибка.")
        said_note = stand.decide(rejected, "comment", comment="Проверить у ГИПа.")

        report = carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.actor)

        assert (report.carried_verdicts, report.carried_comments, report.appended, report.failures) == (2, 2, 4, 0)
        assert report.lineage == (root,) and report.complete and not report.already_complete
        assert (report.sources_decided, report.unmatched_decisions, report.ties_skipped, report.already_decided) == (2, 0, 0, 0)
        assert current_verdict(stand.session, new_accepted[0]).current_verdict == "accepted"
        assert current_verdict(stand.session, new_rejected[0]).current_verdict == "rejected"
        assert current_verdict(stand.session, new_undecided[0]).decision_event_count == 0

        (carried_accept,) = stand.history(new_accepted[0])
        assert (carried_accept.event_type, carried_accept.verdict, carried_accept.carried_from_decision_id) == (
            "accept", "accepted", said_accept.decision_id,
        )
        assert carried_accept.author_user_uid == stand.actor and carried_accept.finding_observation_id == new_accepted[1]
        assert carried_accept.comment.startswith(f"Перенесено при перезапуске из прогона {root}.")
        assert "подтверждения" not in carried_accept.comment

        verdict, comment_one, comment_two = stand.history(new_rejected[0])
        assert (verdict.event_type, verdict.carried_from_decision_id) == ("reject", said_reject.decision_id)
        assert (comment_one.event_type, comment_one.carried_from_decision_id) == ("comment", None)
        assert comment_one.comment == f"Перенесено при перезапуске из прогона {root} (автор: Иванов И. И.): Это не ошибка."
        assert comment_two.comment == f"Перенесено при перезапуске из прогона {root} (автор: Иванов И. И.): Проверить у ГИПа."
        assert said_note.decision_id != comment_two.decision_id                                  # a new event, not the source's
        assert stand.history(accepted[0])[0].decision_id == said_accept.decision_id             # the source ledger is untouched
        assert stand.history(undecided[0]) == ()

    def test_one_command_per_carried_event_with_the_key_of_the_target_run_and_the_source_decision(
        self, stand: Stand, chain: tuple[str, str], carrying: sessionmaker[Session],
    ) -> None:
        root, target = chain
        source, new = stand.finding(root), stand.finding(target)
        said = stand.decide(source, "accept", comment="Согласен.")
        carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.actor)
        rows = stand.session.execute(
            text(
                "SELECT c.idempotency_key, c.state, c.outcome, e.event_type FROM expert_decision_event e "
                "JOIN command_record c ON c.command_id = e.command_id WHERE e.finding_uid = :f ORDER BY e.sequence_no"
            ),
            {"f": new[0]},
        ).mappings().all()
        assert [row["idempotency_key"] for row in rows] == [
            f"restart-carry:{target}:{said.decision_id}:v", f"restart-carry:{target}:{said.decision_id}:c",
        ]
        assert [row["state"] for row in rows] == ["succeeded", "succeeded"]
        outcome = rows[0]["outcome"]
        assert (outcome["mode"], outcome["run_id"], outcome["target_run_id"], outcome["kind"]) == ("restart", root, target, "verdict")
        assert (outcome["source_decision_id"], outcome["source_finding_uid"]) == (said.decision_id, source[0])
        assert stand.session.execute(
            text("SELECT count(*) FROM command_record WHERE command_type = :t AND idempotency_key LIKE :k"),
            {"t": CARRY_DECISION_COMMAND_TYPE, "k": f"restart-carry:{target}:%"},
        ).scalar_one() == 2

    def test_a_repeat_appends_nothing_and_answers_the_same_totals(
        self, stand: Stand, chain: tuple[str, str], carrying: sessionmaker[Session],
    ) -> None:
        root, target = chain
        source, new = stand.finding(root), stand.finding(target)
        stand.decide(source, "reject", comment="Нет.")
        first = carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.actor)
        events_after_first = len(stand.history(new[0]))
        second = carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.actor)
        assert len(stand.history(new[0])) == events_after_first == 2
        assert (second.appended, second.already_complete, second.complete) == (0, True, True)
        assert (second.carried_verdicts, second.carried_comments) == (first.carried_verdicts, first.carried_comments) == (1, 1)

    def test_the_sentences_and_keys_do_not_depend_on_who_calls_again(
        self, stand: Stand, chain: tuple[str, str], carrying: sessionmaker[Session],
    ) -> None:
        root, target = chain
        source, new = stand.finding(root), stand.finding(target)
        stand.decide(source, "accept")
        carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.actor)
        again = carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.other_expert)
        assert again.appended == 0 and len(stand.history(new[0])) == 1

    def test_a_carried_verdict_does_not_vote_and_a_carried_comment_is_not_a_decision(
        self, stand: Stand, chain: tuple[str, str], carrying: sessionmaker[Session],
    ) -> None:
        root, target = chain
        source, new = stand.finding(root), stand.finding(target)
        said = stand.decide(source, "accept", comment="Согласен.")
        seen, port = _recorded_port()
        register_decision_recorded(port)
        carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.actor)
        # `precedents.votes.case_vote` leaves out exactly the events the memory records as `carried`
        assert seen == [("carried", "accept", said.decision_id), ("direct", "comment", None)]
        assert stand.history(new[0])[0].carried_from_decision_id == said.decision_id


class TestTheSeverity:
    def test_it_is_carried_when_the_target_observation_can_hold_one(
        self, stand: Stand, chain: tuple[str, str], carrying: sessionmaker[Session],
    ) -> None:
        root, target = chain
        source, new = stand.finding(root, severity="critical"), stand.finding(target, severity="operational")
        stand.decide(source, "accept", severity="critical")
        report = carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.actor)
        assert (report.carried_verdicts, report.severities_skipped, report.failures) == (1, 0, 0)
        assert current_verdict(stand.session, new[0]).decided_severity == "critical"

    def test_it_is_dropped_and_reported_when_it_cannot_and_the_verdict_still_carries(
        self, stand: Stand, chain: tuple[str, str], carrying: sessionmaker[Session],
    ) -> None:
        root, target = chain
        source, new = stand.finding(root, severity="critical"), stand.finding(target)
        stand.decide(source, "accept", severity="critical")
        report = carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.actor)
        assert (report.carried_verdicts, report.severities_skipped, report.failures) == (1, 1, 0)
        view = current_verdict(stand.session, new[0])
        assert (view.current_verdict, view.decided_severity) == ("accepted", None)


class TestWhatIsNotCarried:
    def test_a_decision_with_no_matching_finding_is_reported_and_holds_nothing_back(
        self, stand: Stand, chain: tuple[str, str], carrying: sessionmaker[Session],
    ) -> None:
        root, target = chain
        gone = stand.finding(root, "Исчезнувшее замечание.")
        stand.decide(gone, "accept")
        stand.finding(target, "Другое замечание.")
        report = carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.actor)
        assert (report.unmatched_decisions, report.carried_verdicts, report.failures, report.complete) == (1, 0, 0, True)

    def test_a_block_finding_without_evidence_matches_on_text_and_category(
        self, stand: Stand, chain: tuple[str, str], carrying: sessionmaker[Session],
    ) -> None:
        root, target = chain
        source, new = stand.finding(root, "Блок.", evidence=()), stand.finding(target, "Блок.", evidence=())
        other = stand.finding(target, "Блок.", evidence=(), category="layout")
        stand.decide(source, "reject")
        carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.actor)
        assert current_verdict(stand.session, new[0]).current_verdict == "rejected"
        assert stand.history(other[0]) == ()

    def test_evidence_that_moved_is_another_finding(
        self, stand: Stand, chain: tuple[str, str], carrying: sessionmaker[Session],
    ) -> None:
        root, target = chain
        source = stand.finding(root)
        moved = stand.finding(target, evidence=((1, QUOTE, 41, 41 + len(QUOTE)),))
        stand.decide(source, "accept")
        report = carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.actor)
        assert stand.history(moved[0]) == () and report.unmatched_decisions == 1

    def test_twins_with_references_are_paired_in_order_and_without_them_are_skipped_and_counted(
        self, stand: Stand, chain: tuple[str, str], carrying: sessionmaker[Session],
    ) -> None:
        root, target = chain
        first_source, second_source = stand.finding(root, "Двойник.", ref="primary_text_2"), stand.finding(root, "Двойник.", ref="primary_text_10")
        first_new, second_new = stand.finding(target, "Двойник.", ref="primary_text_4"), stand.finding(target, "Двойник.", ref="primary_text_11")
        stand.decide(first_source, "accept")
        stand.decide(second_source, "reject")
        bare_source, bare_new = [stand.finding(root, "Без ссылок.") for _ in range(2)], [stand.finding(target, "Без ссылок.") for _ in range(2)]
        stand.decide(bare_source[0], "accept")
        report = carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.actor)
        assert current_verdict(stand.session, first_new[0]).current_verdict == "accepted"
        assert current_verdict(stand.session, second_new[0]).current_verdict == "rejected"
        assert [stand.history(item[0]) for item in bare_new] == [(), ()]
        assert (report.ties_skipped, report.carried_verdicts, report.failures) == (2, 2, 0)

    def test_a_finding_an_expert_already_decided_on_the_new_run_is_left_to_the_expert(
        self, stand: Stand, chain: tuple[str, str], carrying: sessionmaker[Session],
    ) -> None:
        root, target = chain
        source, new = stand.finding(root), stand.finding(target)
        stand.decide(source, "accept")
        own = stand.decide(new, "reject", comment="Моё решение.")
        report = carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.actor)
        assert stand.history(new[0]) == (own,)
        assert (report.already_decided, report.appended, report.failures, report.complete) == (1, 0, 0, True)
        assert current_verdict(stand.session, new[0]).current_verdict == "rejected"


class TestTheLineage:
    def test_the_whole_chain_is_read_the_newest_verdict_wins_and_every_comment_is_carried(
        self, stand: Stand, carrying: sessionmaker[Session],
    ) -> None:
        root = stand.run("cancelled")
        middle = stand.run("partial", source=root, restart_point="blocks")
        target = stand.run("published", source=middle, restart_point="review")
        in_root, in_middle, new = stand.finding(root), stand.finding(middle), stand.finding(target)
        stand.decide(in_root, "accept", comment="Первое слово.")
        newest = stand.decide(in_middle, "reject")
        stand.decide(in_middle, "comment", comment="Второе слово.")
        report = carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.actor)
        assert report.lineage == (middle, root) and report.failures == 0
        assert current_verdict(stand.session, new[0]).current_verdict == "rejected"
        events = stand.history(new[0])
        assert [(event.event_type, event.carried_from_decision_id) for event in events] == [
            ("reject", newest.decision_id), ("comment", None), ("comment", None),
        ]
        assert [event.comment.rsplit(": ", 1)[-1] for event in events[1:]] == ["Первое слово.", "Второе слово."]

    def test_a_second_restart_carries_from_the_first_and_does_not_nest_the_sentences(
        self, stand: Stand, carrying: sessionmaker[Session],
    ) -> None:
        root = stand.run("failed")
        middle = stand.run("partial", source=root, restart_point="review")
        in_root, in_middle = stand.finding(root), stand.finding(middle)
        stand.decide(in_root, "accept", comment="Слова.")
        carry_restart_decisions(carrying, run_id=middle, actor_user_uid=stand.actor)
        target = stand.run("published", source=middle, restart_point="norms")
        new = stand.finding(target)
        report = carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.actor)
        assert report.failures == 0
        verdict, comment = stand.history(new[0])
        assert current_verdict(stand.session, new[0]).current_verdict == "accepted"
        # the verdict follows the copy in the run before (its newest source) and the words are the root's, once
        assert verdict.carried_from_decision_id == stand.history(in_middle[0])[0].decision_id
        assert comment.comment == f"Перенесено при перезапуске из прогона {root} (автор: Иванов И. И.): Слова."

    def test_a_run_that_started_from_a_stage_is_the_root_not_a_link_of_the_chain(
        self, stand: Stand, carrying: sessionmaker[Session],
    ) -> None:
        before = stand.run("published")
        root = RunId.new().value
        stand.session.execute(
            text(
                "INSERT INTO audit_run (run_id, project_uid, version_uid, state, analysis_profile_id, prompt_bundle_id, provider_mode, "
                "frozen_input_digest, started_by_user_uid, started_from_run_id, start_stage_id) "
                "VALUES (:r, :p, :v, 'created', :ap, :pb, 'recorded', :s, :u, :f, 'text_analysis')"
            ),
            {"r": root, "p": stand.project_uid, "v": stand.version_uid, "ap": stand.profile, "pb": stand.bundle, "s": _digest(root),
             "u": stand.actor, "f": before},
        )
        for step in ("queued", "failed"):
            stand.session.execute(
                text(
                    "UPDATE audit_run SET state = :s, terminal_at = CASE WHEN :s = 'failed' THEN now() END, "
                    "terminal_reason = CASE WHEN :s = 'failed' THEN 'analysis_failed' END WHERE run_id = :r"
                ),
                {"s": step, "r": root},
            )
        target = stand.run("published", source=root, restart_point="review")
        ignored, new = stand.finding(before), stand.finding(target)
        stand.decide(ignored, "accept")
        report = carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.actor)
        assert report.lineage == (root,) and stand.history(new[0]) == ()


class TestTheMarkerAndTheSweeper:
    def test_a_published_restart_is_pending_until_its_carry_completes(
        self, stand: Stand, chain: tuple[str, str], carrying: sessionmaker[Session],
    ) -> None:
        root, target = chain
        stand.finding(root), stand.finding(target)
        assert target in pending_restart_carries(stand.session)
        assert root not in pending_restart_carries(stand.session)                  # no restart
        carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.actor)
        assert target not in pending_restart_carries(stand.session)
        marker = stand.session.execute(
            text("SELECT state, outcome FROM command_record WHERE command_type = :t AND idempotency_key = :k"),
            {"t": CARRY_RUN_COMMAND_TYPE, "k": f"restart-carry-run:{target}"},
        ).mappings().one()
        assert marker["state"] == "succeeded" and marker["outcome"]["mode"] == "restart" and marker["outcome"]["complete"] is True

    def test_a_partial_restart_is_pending_too_and_a_run_that_has_not_published_is_not(
        self, stand: Stand, chain: tuple[str, str],
    ) -> None:
        root, _ = chain
        partial = stand.run("partial", source=root, restart_point="text")
        running = stand.run("running", source=stand.run("failed"), restart_point="text")
        failed = stand.run("failed", source=stand.run("cancelled"), restart_point="text")
        listed = pending_restart_carries(stand.session)
        assert partial in listed and running not in listed and failed not in listed

    def test_a_run_that_is_no_published_restart_is_refused_before_anything_is_written(
        self, stand: Stand, chain: tuple[str, str], carrying: sessionmaker[Session],
    ) -> None:
        root, _ = chain
        running = stand.run("running", source=stand.run("failed"), restart_point="text")
        for refused in (root, running):
            with pytest.raises(DomainError) as caught:
                carry_restart_decisions(carrying, run_id=refused, actor_user_uid=stand.actor)
            assert caught.value.code is ErrorCode.CONFLICT
            assert caught.value.detail_fields["conflict_reason"] == "restart_carry_run_not_a_published_restart"
        with pytest.raises(DomainError) as unknown:
            carry_restart_decisions(carrying, run_id=RunId.new().value, actor_user_uid=stand.actor)
        assert unknown.value.code is ErrorCode.NOT_FOUND
        assert stand.session.execute(
            text("SELECT count(*) FROM command_record WHERE command_type = :t"), {"t": CARRY_RUN_COMMAND_TYPE},
        ).scalar_one() == 0

    def test_an_unknown_or_malformed_actor_is_refused(
        self, stand: Stand, chain: tuple[str, str], carrying: sessionmaker[Session],
    ) -> None:
        _, target = chain
        with pytest.raises(DomainError) as malformed:
            carry_restart_decisions(carrying, run_id=target, actor_user_uid="usr_x")
        assert malformed.value.code is ErrorCode.VALIDATION_FAILED
        with pytest.raises(DomainError) as unknown:
            carry_restart_decisions(carrying, run_id=target, actor_user_uid="usr_01M5F21PBT7E8WRN3M61BDQFDD")
        assert unknown.value.code is ErrorCode.NOT_FOUND
        assert target in pending_restart_carries(stand.session)


class TestTheDecisionMemoryFailing:
    def test_a_failing_port_loses_only_its_item_leaves_the_run_pending_and_the_next_call_finishes(
        self, stand: Stand, chain: tuple[str, str], carrying: sessionmaker[Session],
    ) -> None:
        root, target = chain
        sources = [stand.finding(root, f"Замечание {n}.") for n in range(3)]
        news = [stand.finding(target, f"Замечание {n}.") for n in range(3)]
        for source in sources:
            stand.decide(source, "accept")
        poisoned = news[1][0]

        def port(session: Session, event: Any, origin_kind: str) -> None:  # noqa: ARG001
            if event.finding_uid == poisoned:
                raise RuntimeError("the memory could not be written")

        register_decision_recorded(port)
        first = carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.actor)
        assert (first.carried_verdicts, first.appended, first.failures, first.complete) == (2, 2, 1, False)
        assert "RuntimeError: the memory could not be written" in first.failure_details[0]
        assert [len(stand.history(item[0])) for item in news] == [1, 0, 1]
        assert target in pending_restart_carries(stand.session)                # no marker while an item failed
        assert stand.session.execute(
            text("SELECT count(*) FROM command_record WHERE command_type = :t AND idempotency_key LIKE :k"),
            {"t": CARRY_DECISION_COMMAND_TYPE, "k": f"restart-carry:{target}:%"},
        ).scalar_one() == 2                                                    # the failed item's command rolled back with it

        register_decision_recorded(None)
        second = carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.actor)
        assert (second.carried_verdicts, second.appended, second.replayed, second.failures, second.complete) == (3, 1, 2, 0, True)
        assert [len(stand.history(item[0])) for item in news] == [1, 1, 1]      # nothing doubled
        assert target not in pending_restart_carries(stand.session)

    def test_a_failure_after_the_insert_leaves_no_event_of_that_item(
        self, stand: Stand, chain: tuple[str, str], carrying: sessionmaker[Session],
    ) -> None:
        root, target = chain
        source, new = stand.finding(root), stand.finding(target)
        stand.decide(source, "reject", comment="Слова.")
        calls: list[str] = []

        def port(session: Session, event: Any, origin_kind: str) -> None:  # noqa: ARG001
            calls.append(event.event_type)
            if event.event_type == "reject":
                raise RuntimeError("boom")

        register_decision_recorded(port)
        report = carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.actor)
        # the verdict raised after its INSERT and is gone; the comment, a later item of the same transaction, is carried
        assert calls == ["reject", "comment"]
        assert [event.event_type for event in stand.history(new[0])] == ["comment"]
        assert (report.carried_verdicts, report.carried_comments, report.failures) == (0, 1, 1)


class TestTheOriginTheWireReads:
    def test_the_run_and_the_mode_come_back_with_the_origin_of_the_verdict_and_of_the_event(
        self, stand: Stand, chain: tuple[str, str], carrying: sessionmaker[Session],
    ) -> None:
        root, target = chain
        source, new = stand.finding(root), stand.finding(target)
        said = stand.decide(source, "accept")
        carry_restart_decisions(carrying, run_id=target, actor_user_uid=stand.actor)
        (carried,) = stand.history(new[0])
        by_verdict = current_verdict_origins(stand.session, [new[0], source[0]])
        by_event = carried_origins(stand.session, [carried.decision_id, said.decision_id])
        for origin in (by_verdict[new[0]], by_event[carried.decision_id]):
            assert (origin.decision_id, origin.finding_uid, origin.run_id, origin.mode) == (said.decision_id, source[0], root, "restart")
            assert origin.version_uid == stand.version_uid and origin.version_ordinal == 1
        assert source[0] not in by_verdict and said.decision_id not in by_event      # a decision made directly has no origin
        entry = next(item for item in decision_journal(stand.session, project_uid=stand.project_uid) if item.decision_id == carried.decision_id)
        assert (entry.carried_from.run_id, entry.carried_from.mode) == (root, "restart")
