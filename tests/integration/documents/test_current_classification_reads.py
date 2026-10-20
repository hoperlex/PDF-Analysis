"""`CLASSIFICATION-CORRECTION-01`: every read of a classification is the **current** one.

On real PostgreSQL rows, through the shipped repositories and the correction command:

* ``get_version``, ``list_documents``, ``list_versions`` and ``get_classification`` project the
  latest revision, with its number, its expert and its time; the stored original is untouched;
* the two section-view queries and the dashboard's breakdown place a set by its current
  version's **current** section: a set corrected out of ``AR`` leaves ``AR`` and enters the
  new section in all three, an older version's correction never counts for a set whose head
  moved on, and an unclassified set is unclassified whatever else says;
* the history lists every revision oldest first, with the reason of each correction;
* the command: the expert-only rule (its own check, not the route's), the chain (a foreign
  document, project or version is ``not_found``), an unclassified version, the exact repeat,
  the stale and the ahead ``expected_revision``, the no-op, the bounded reason, and two
  concurrent corrections of one version, which serialise on the lock;
* ``classify_document_version`` compares against the current classification (D4);
* a version's equality ignores its classification (D9), and a new version inherits nothing.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.access.public import AccountRepository, UserRepository
from auditmanager.dashboard.repository import DashboardRepository
from auditmanager.documents.public import DocumentRepository
from auditmanager.sections.public import classify_document_version, correct_document_version_classification
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid
from tests.integration.db.conftest import (  # type: ignore[import-not-found]  # noqa: F401
    configured_settings,
    maintenance_engine,
    migrated_database,
    migrated_database_factory,
    migrated_engine,
    migrated_template,
)
from tests.integration.documents.seeding import PASSWORD, Seeder

documents = DocumentRepository()
EXPERT = frozenset({"expert"})
REASON = "Раздел определён по штампу листа неверно"


@pytest.fixture
def session(migrated_engine: Engine) -> Iterator[Session]:
    with Session(migrated_engine) as opened:
        yield opened


def _second_expert(session: Session) -> str:
    uid = str(UserRepository().create_user(session, "boris@example.com", PASSWORD).user_uid)
    AccountRepository().complete_profile(
        session, user_uid=uid, email=None, last_name="Иванов", first_name="Борис"
    )
    AccountRepository().grant_role(session, user_uid=uid, role="expert", granted_by=None)
    return uid


class World:
    """One project, a few sets; helpers that go through the command."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.seed = Seeder(session)
        self.project = self.seed.project("Школа")
        self.first = self.seed.expert
        self.second = _second_expert(session)
        self.document = self.seed.document(self.project, "Комплект КЖ", legacy_section="AR")
        self.version = self.seed.version(self.document, classified=("P", "KJ"))

    def correct(
        self, version: str | None = None, *, stage: str = "R", section: str = "KJ",
        reason: str = REASON, expected: int = 1, actor: str | None = None,
        roles: frozenset[str] = EXPERT, document: str | None = None, project: str | None = None,
        session: Session | None = None,
    ) -> Any:
        return correct_document_version_classification(
            session or self.session,
            project_uid=project or self.project,
            document_uid=document or self.document,
            version_uid=version or self.version,
            project_stage=stage,
            section_code=section,
            reason=reason,
            expected_revision=expected,
            actor_uid=actor or self.second,
            actor_roles=roles,
        )


@pytest.fixture
def world(session: Session) -> World:
    built = World(session)
    session.commit()
    return built


def _refusal(call: Any) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call()
    return caught.value


class TestTheReadsAreTheCurrentClassification:
    def test_every_version_read_projects_the_latest_revision(self, session: Session, world: World) -> None:
        answered = world.correct(stage="R", section="AR", expected=1)
        session.commit()
        assert (answered.revision, answered.project_stage, answered.section_code) == (2, "R", "AR")
        assert answered.confirmed_by_user_uid == world.second
        version_uid = VersionUid.parse(world.version)
        for record in (
            documents.get_version(session, version_uid),
            documents.list_documents(session, ProjectUid.parse(world.project))[0],
            documents.list_versions(session, DocumentUid.parse(world.document))[0],
        ):
            classification = record.classification
            assert classification is not None
            assert (classification.revision, classification.project_stage, classification.section_code) == (2, "R", "AR")
            assert classification.confirmed_by_user_uid == world.second
            assert classification.confirmed_at == answered.confirmed_at
        stored = documents.get_classification(session, version_uid)
        assert stored is not None and stored.revision == 2 and stored.section_code == "AR"
        # the original row is exactly what the first expert confirmed
        original = session.execute(
            text("SELECT project_stage, section_code, confirmed_by_user_uid "
                 "FROM document_version_classification WHERE version_uid = :v"),
            {"v": world.version},
        ).one()
        assert tuple(original) == ("P", "KJ", world.first)

    def test_an_uncorrected_version_is_revision_one(self, session: Session, world: World) -> None:
        stored = documents.get_classification(session, VersionUid.parse(world.version))
        assert stored is not None and stored.revision == 1 and stored.confirmed_by_user_uid == world.first

    def test_the_history_lists_every_revision_oldest_first_with_its_reason(
        self, session: Session, world: World
    ) -> None:
        world.correct(stage="R", section="KJ", expected=1, reason="Это рабочая документация")
        world.correct(stage="R", section="AR", expected=2, actor=world.first, reason=REASON)
        session.commit()
        history = documents.list_classification_revisions(session, VersionUid.parse(world.version))
        assert [(item.revision, item.project_stage, item.section_code, item.actor_user_uid, item.reason)
                for item in history] == [
            (1, "P", "KJ", world.first, None),
            (2, "R", "KJ", world.second, "Это рабочая документация"),
            (3, "R", "AR", world.first, REASON),
        ]
        assert documents.list_classification_revisions(session, VersionUid.new()) == ()

    def test_the_lock_is_taken_only_on_a_classified_version(self, session: Session, world: World) -> None:
        bare = world.seed.version(world.seed.document(world.project, "Без раздела"))
        assert documents.lock_classification(session, VersionUid.parse(world.version)) is True
        assert documents.lock_classification(session, VersionUid.parse(bare)) is False

    def test_the_section_views_and_the_dashboard_follow_a_correction(
        self, session: Session, world: World
    ) -> None:
        ar_set = world.seed.document(world.project, "АР-1")
        ar_version = world.seed.version(ar_set, classified=("R", "AR"))
        unclassified = world.seed.document(world.project, "Без раздела", legacy_section="AR")
        world.seed.version(unclassified)
        session.commit()
        dashboard = DashboardRepository()

        def breakdown() -> dict[str | None, int]:
            return {row.section: row.document_count for row in dashboard.summary(session).section_breakdown}

        def members(code: str) -> set[str]:
            return {str(item.document_uid) for item in
                    documents.list_current_versions_in_section(session, section_code=code)}

        assert (members("AR"), members("KJ")) == ({ar_set}, {world.document})
        assert (breakdown()["AR"], breakdown()["KJ"], breakdown()[None]) == (1, 1, 1)

        world.correct(ar_version, document=ar_set, stage="R", section="OV", expected=1)
        session.commit()
        assert (members("AR"), members("OV"), members("KJ")) == (set(), {ar_set}, {world.document})
        assert (breakdown()["AR"], breakdown()["OV"], breakdown()["KJ"], breakdown()[None]) == (0, 1, 1, 1)
        unclassified_sets = {str(item.document_uid) for item in
                             documents.list_unclassified_current_versions(session)}
        assert unclassified_sets == {unclassified}
        placed = {str(item.document_uid): (item.project_stage, item.section_code) for item in
                  documents.list_current_versions_in_section(session, section_code="OV")}
        assert placed == {ar_set: ("R", "OV")}

    def test_an_older_versions_correction_never_counts_for_a_set_whose_head_moved_on(
        self, session: Session, world: World
    ) -> None:
        moving = world.seed.document(world.project, "Двигается")
        older = world.seed.version(moving, classified=("R", "OV"))
        world.seed.version(moving, classified=("P", "AR"))
        session.commit()
        world.correct(older, document=moving, stage="R", section="TX", expected=1)
        session.commit()
        placed = {str(item.document_uid) for item in
                  documents.list_current_versions_in_section(session, section_code="TX")}
        assert placed == set()
        counted = {row.section: row.document_count
                   for row in DashboardRepository().summary(session).section_breakdown}
        assert counted["TX"] == 0 and counted["AR"] == 1

    def test_a_new_version_inherits_nothing_from_a_corrected_one(self, session: Session, world: World) -> None:
        world.correct(stage="R", section="AR", expected=1)
        newer = world.seed.version(world.document)
        session.commit()
        assert documents.get_version(session, VersionUid.parse(newer)).classification is None
        assert documents.list_documents(session, ProjectUid.parse(world.project))[0].classification is None
        older = documents.get_version(session, VersionUid.parse(world.version)).classification
        assert older is not None and older.revision == 2

    def test_a_versions_equality_ignores_its_classification(self, session: Session, world: World) -> None:
        before = documents.get_version(session, VersionUid.parse(world.version))
        world.correct(stage="R", section="AR", expected=1)
        session.commit()
        after = documents.get_version(session, VersionUid.parse(world.version))
        assert before.classification is not None and after.classification is not None
        assert before.classification.revision == 1 and after.classification.revision == 2
        assert before == after, "a correction between two reads must not look like a changed version"


class TestTheCommand:
    def test_only_an_expert_corrects_and_the_command_checks_it_itself(
        self, session: Session, world: World
    ) -> None:
        for roles in (frozenset(), frozenset({"admin"})):
            refused = _refusal(lambda roles=roles: world.correct(roles=roles))
            assert refused.code is ErrorCode.PERMISSION_DENIED
            assert refused.detail_fields == {"required_capability": "role:expert"}
        session.rollback()
        assert documents.get_classification(session, VersionUid.parse(world.version)).revision == 1  # type: ignore[union-attr]

    def test_the_chain_is_proved_before_anything_else(self, session: Session, world: World) -> None:
        other_project = world.seed.project("Другой")
        other_document = world.seed.document(other_project, "Чужой")
        other_version = world.seed.version(other_document, classified=("P", "AR"))
        session.commit()
        for kwargs in (
            {"project": other_project},                      # the document is not in that project
            {"document": other_document},                    # the version is not in that document
            {"version": other_version},                      # a version of another document
            {"version": str(VersionUid.new())},              # unknown
            {"project": str(ProjectUid.new())},              # unknown project
        ):
            refused = _refusal(lambda kwargs=kwargs: world.correct(**kwargs))
            assert refused.code is ErrorCode.NOT_FOUND, kwargs
        session.rollback()
        assert documents.get_classification(session, VersionUid.parse(other_version)).revision == 1  # type: ignore[union-attr]

    def test_an_unclassified_version_has_nothing_to_correct(self, session: Session, world: World) -> None:
        bare = world.seed.version(world.seed.document(world.project, "Без раздела"))
        bare_document = documents.get_version(session, VersionUid.parse(bare)).document_uid
        refused = _refusal(lambda: world.correct(bare, document=str(bare_document)))
        assert refused.code is ErrorCode.CONFLICT
        assert refused.detail_fields["conflict_reason"] == "version_not_classified"

    def test_revisions_are_numbered_in_order_and_the_expert_and_reason_are_stored(
        self, session: Session, world: World
    ) -> None:
        second = world.correct(stage="R", section="KJ", expected=1, reason="  Это рабочая документация  ")
        third = world.correct(stage="R", section="AR", expected=2, actor=world.first)
        assert (second.revision, third.revision) == (2, 3)
        assert second.confirmed_by_user_uid == world.second and third.confirmed_by_user_uid == world.first
        stored = documents.list_classification_revisions(session, VersionUid.parse(world.version))
        assert stored[1].reason == "Это рабочая документация"

    def test_an_exact_repeat_answers_the_stored_revision_and_writes_nothing(
        self, session: Session, world: World
    ) -> None:
        first = world.correct(stage="R", section="AR", expected=1)
        again = world.correct(stage="R", section="AR", expected=1)
        assert again == first
        later = world.correct(stage="P", section="OV", expected=2, actor=world.first)
        replay = world.correct(stage="R", section="AR", expected=1)  # a retry, after someone corrected again
        assert replay == first and later.revision == 3
        assert session.execute(
            text("SELECT count(*) FROM document_version_classification_correction")
        ).scalar_one() == 2

    def test_stale_ahead_and_no_op_are_refused_and_write_nothing(self, session: Session, world: World) -> None:
        world.correct(stage="R", section="AR", expected=1)
        stale = _refusal(lambda: world.correct(stage="P", section="OV", expected=1, actor=world.first))
        assert stale.code is ErrorCode.CONFLICT
        assert stale.detail_fields["conflict_reason"] == "classification_revision_stale"
        ahead = _refusal(lambda: world.correct(stage="P", section="OV", expected=9))
        assert (ahead.code, ahead.detail_fields["constraint"]) == (ErrorCode.VALIDATION_FAILED, "exceeds_current_revision")
        no_op = _refusal(lambda: world.correct(stage="R", section="AR", expected=2))
        assert (no_op.code, no_op.detail_fields["constraint"]) == (ErrorCode.VALIDATION_FAILED, "differs_from_current")
        assert session.execute(
            text("SELECT count(*) FROM document_version_classification_correction")
        ).scalar_one() == 1

    @pytest.mark.parametrize("reason", ["", "   ", "...", "а" * 2001, "до\x00после"])
    def test_a_reason_must_be_a_real_bounded_sentence(self, session: Session, world: World, reason: str) -> None:
        refused = _refusal(lambda: world.correct(reason=reason))
        assert refused.code is ErrorCode.VALIDATION_FAILED and refused.detail_fields["field"] == "reason"
        assert session.execute(
            text("SELECT count(*) FROM document_version_classification_correction")
        ).scalar_one() == 0

    def test_classify_compares_against_the_current_classification(self, session: Session, world: World) -> None:
        world.correct(stage="R", section="AR", expected=1)
        session.commit()

        def classify(stage: str, section: str) -> Any:
            return classify_document_version(
                session, project_uid=world.project, document_uid=world.document,
                version_uid=world.version, project_stage=stage, section_code=section,
                actor_uid=world.first, actor_roles=EXPERT,
            )

        stored = classify("R", "AR")  # an exact repeat of the CURRENT values answers the current row
        assert stored.revision == 2 and stored.confirmed_by_user_uid == world.second
        original_request = _refusal(lambda: classify("P", "KJ"))  # the retry of the first request
        assert original_request.code is ErrorCode.CONFLICT
        assert original_request.detail_fields["conflict_reason"] == "version_already_classified"


class TestConcurrentCorrections:
    @pytest.mark.parametrize(("second_section", "outcome"), [("AR", "conflict_same_values"), ("OV", "conflict")])
    def test_two_experts_looking_at_the_same_revision_the_loser_conflicts(
        self, migrated_engine: Engine, second_section: str, outcome: str
    ) -> None:
        sessions = sessionmaker(bind=migrated_engine, expire_on_commit=False, future=True)
        with sessions() as setup:
            world = World(setup)
            setup.commit()
        winner = sessions()
        won = world.correct(stage="R", section="AR", expected=1, actor=world.second, session=winner)
        result: dict[str, Any] = {}

        def contender() -> None:
            with sessions() as other:
                try:
                    result["row"] = world.correct(
                        stage="R", section=second_section, expected=1, actor=world.first, session=other
                    )
                    other.commit()
                except DomainError as refusal:
                    result["error"] = refusal

        thread = threading.Thread(target=contender)
        thread.start()
        thread.join(timeout=2)
        assert thread.is_alive(), "the second correction must wait for the first one's lock"
        winner.commit()
        winner.close()
        thread.join(timeout=30)
        assert not thread.is_alive()
        error = result["error"]
        assert error.code is ErrorCode.CONFLICT
        assert error.detail_fields["conflict_reason"] == "classification_revision_stale"
        with sessions() as check:
            rows = check.execute(
                text("SELECT revision, corrected_by_user_uid FROM document_version_classification_correction")
            ).all()
        assert [tuple(row) for row in rows] == [(2, world.second)], outcome
        assert won.revision == 2

    def test_two_identical_retries_serialise_and_write_one_row(self, migrated_engine: Engine) -> None:
        sessions = sessionmaker(bind=migrated_engine, expire_on_commit=False, future=True)
        with sessions() as setup:
            world = World(setup)
            setup.commit()
        first = sessions()
        written = world.correct(stage="R", section="AR", expected=1, session=first)
        result: dict[str, Any] = {}

        def retry() -> None:
            with sessions() as other:
                result["row"] = world.correct(stage="R", section="AR", expected=1, session=other)
                other.commit()

        thread = threading.Thread(target=retry)
        thread.start()
        thread.join(timeout=2)
        assert thread.is_alive()
        first.commit()
        first.close()
        thread.join(timeout=30)
        assert not thread.is_alive()
        assert result["row"] == written
        with sessions() as check:
            assert check.execute(
                text("SELECT count(*) FROM document_version_classification_correction")
            ).scalar_one() == 1
