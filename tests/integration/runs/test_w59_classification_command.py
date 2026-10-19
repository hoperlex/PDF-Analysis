"""`W59-SECTION-SEAL-01`: the classify command and run routing on real PostgreSQL, without HTTP.

What the HTTP suite beside this one cannot reach:

* the command's **own** role check -- the request register refuses a non-expert before the
  route, so only a direct call proves the command does not rely on it (the decision's
  "reads the authenticated actor's current role set ... under one transaction");
* **concurrent first confirmations** of one version: the loser of the primary-key race
  waits for the winner's commit, then is answered by the winner's row (same choice, first
  confirmer kept) or refused with ``conflict`` (different choice) -- never an overwrite;
* **a newer version starts unclassified**: publishing moves ``current_version_uid`` and
  leaves the older version's classification and its runs exactly as they were;
* the routing guard's refusals at the command layer, and the replay of a key whose run was
  pinned before the version was classified.
"""

from __future__ import annotations

import threading
import uuid
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.documents.public import DocumentRepository
from auditmanager.runs import RunRepository, start_audit_run
from auditmanager.sections.public import classify_document_version, route_classified_version
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import DocumentUid, VersionUid

REGISTRY = load_text_profile_registry()


@pytest.fixture(autouse=True)
def _no_network() -> None:
    """This module opens no socket beyond PostgreSQL and MinIO; threads share the engine."""


@pytest.fixture
def sessions(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def _expert(label: str) -> str:
    from am_test_accounts import provisioned_record

    return str(provisioned_record(label).user_uid)


def _new_version(session: Session, seeded: Any) -> str:
    documents = DocumentRepository()
    base = documents.get_version(session, VersionUid.parse(seeded.version_uid))
    return str(
        documents.publish_version(
            session,
            document_uid=DocumentUid.parse(seeded.document_uid),
            media_type=base.media_type,
            byte_size=base.byte_size,
            sha256=base.sha256,
            page_count=base.page_count,
            source_filename=None,
            entries=base.manifest,
        )
    )


@pytest.fixture
def world(sessions: sessionmaker[Session], blob_store: Any, helpers: Any) -> Any:
    with sessions() as session:
        seeded = helpers.seed_version(session, blob_store)
        session.commit()
    return seeded


def _classify(session: Session, seeded: Any, version_uid: str, user: str, code: str,
              stage: str = "R", roles: frozenset[str] = frozenset({"expert"})) -> Any:
    return classify_document_version(
        session,
        project_uid=seeded.project_uid,
        document_uid=seeded.document_uid,
        version_uid=version_uid,
        project_stage=stage,
        section_code=code,
        actor_uid=user,
        actor_roles=roles,
    )


class TestTheCommandsOwnRoleCheck:
    @pytest.mark.parametrize("roles", [frozenset(), frozenset({"admin"})])
    def test_without_expert_the_command_refuses_and_writes_nothing(
        self, sessions, world, roles
    ) -> None:
        user = _expert("w59-command-expert")
        with sessions() as session:
            with pytest.raises(DomainError) as refused:
                _classify(session, world, world.version_uid, user, "KJ", roles=roles)
            assert refused.value.code is ErrorCode.PERMISSION_DENIED
            assert refused.value.detail_fields == {"required_capability": "role:expert"}
            session.rollback()
            assert DocumentRepository().get_classification(
                session, VersionUid.parse(world.version_uid)
            ) is None


class TestConcurrentFirstConfirmations:
    @pytest.mark.parametrize(("second_code", "outcome"), [("KJ", "same_row"), ("OV", "conflict")])
    def test_the_loser_waits_and_is_answered_by_the_winner(
        self, sessions, world, second_code, outcome
    ) -> None:
        first_user = _expert("w59-race-first")
        second_user = _expert("w59-race-second")
        result: dict[str, Any] = {}
        winner = sessions()
        stored = _classify(winner, world, world.version_uid, first_user, "KJ")

        def contender() -> None:
            with sessions() as session:
                try:
                    result["row"] = _classify(session, world, world.version_uid, second_user, second_code)
                    session.commit()
                except DomainError as refusal:
                    result["error"] = refusal

        thread = threading.Thread(target=contender)
        thread.start()
        thread.join(timeout=2)
        assert thread.is_alive(), "the contender must wait for the winner's uncommitted row"
        winner.commit()
        winner.close()
        thread.join(timeout=30)
        assert not thread.is_alive()
        if outcome == "same_row":
            row = result["row"]
            assert row.confirmed_by_user_uid == first_user == stored.confirmed_by_user_uid
            assert row.confirmed_at == stored.confirmed_at
        else:
            assert result["error"].code is ErrorCode.CONFLICT
            assert result["error"].detail_fields["conflict_reason"] == "version_already_classified"
        with sessions() as session:
            assert session.execute(
                text("SELECT count(*), min(section_code) FROM document_version_classification "
                     "WHERE version_uid = :v"),
                {"v": world.version_uid},
            ).one() == (1, "KJ")


class TestANewerVersion:
    def test_a_newer_version_starts_unclassified_and_the_older_one_keeps_its_pin(
        self, sessions, world
    ) -> None:
        user = _expert("w59-current-head")
        with sessions() as session:
            _classify(session, world, world.version_uid, user, "KJ")
            started = start_audit_run(
                session, version_uid=world.version_uid, provider_mode="recorded",
                idempotency_key="w59head-" + uuid.uuid4().hex[:12],
                section_profiles=REGISTRY.section_profiles(),
            )
            newer = _new_version(session, world)
            session.commit()
        with sessions() as session:
            documents = DocumentRepository()
            older = documents.get_version(session, VersionUid.parse(world.version_uid))
            current = documents.get_version(session, VersionUid.parse(newer))
            listed = documents.list_documents(session, older.project_uid)
            run = RunRepository().get(session, started.run_id)
        assert older.classification is not None and older.classification.section_code == "KJ"
        assert current.classification is None
        assert [str(item.version_uid) for item in listed] == [newer]
        assert listed[0].classification is None
        assert (run.version_uid, run.analysis_profile_id) == (
            world.version_uid, REGISTRY.section_profiles()["KJ"][0],
        )


class TestRouting:
    def test_the_guard_refuses_without_a_fallback(self, sessions, world) -> None:
        user = _expert("w59-route-guard")
        profiles = REGISTRY.section_profiles()
        with sessions() as session:
            documents = DocumentRepository()
            unclassified = documents.get_version(session, VersionUid.parse(world.version_uid))
            with pytest.raises(DomainError) as missing:
                route_classified_version(unclassified, profiles)
            assert missing.value.code is ErrorCode.REQUIRED_NORM_UNAVAILABLE
            assert missing.value.detail_fields == {"reference_kind": "version_classification"}
            _classify(session, world, world.version_uid, user, "KJ")
            classified = documents.get_version(session, VersionUid.parse(world.version_uid))
            without_kj = {code: pair for code, pair in profiles.items() if code != "KJ"}
            with pytest.raises(DomainError) as unavailable:
                route_classified_version(classified, without_kj)
            assert unavailable.value.detail_fields == {"reference_kind": "analysis_profile"}
            assert "AR" in without_kj, "the refusal must hold while AR stays registered"
            route = route_classified_version(classified, profiles)
            assert (route.analysis_profile_id, route.prompt_bundle_id) == profiles["KJ"]
            session.rollback()

    def test_a_key_accepted_before_classification_replays_its_pinned_run(
        self, sessions, world
    ) -> None:
        """An existing run keeps its profile: the replay reads the pin, it does not re-route."""
        key = "w59pinned-" + uuid.uuid4().hex[:12]
        with sessions() as session:
            legacy = start_audit_run(
                session, version_uid=world.version_uid, provider_mode="recorded",
                idempotency_key=key, analysis_profile_id=world.analysis_profile_id,
                prompt_bundle_id=world.prompt_bundle_id,
            )
            session.commit()
        with sessions() as session:
            replay = start_audit_run(
                session, version_uid=world.version_uid, provider_mode="recorded",
                idempotency_key=key, section_profiles=REGISTRY.section_profiles(),
            )
            run = RunRepository().get(session, replay.run_id)
        assert replay.replayed and replay.run_id == legacy.run_id
        assert run.analysis_profile_id == world.analysis_profile_id

    def test_both_or_neither_profile_source_is_a_wiring_fault(self, sessions, world) -> None:
        with sessions() as session:
            with pytest.raises(ValueError):
                start_audit_run(
                    session, version_uid=world.version_uid, provider_mode="recorded",
                    idempotency_key="w59-wiring-both", section_profiles=REGISTRY.section_profiles(),
                    analysis_profile_id=world.analysis_profile_id,
                    prompt_bundle_id=world.prompt_bundle_id,
                )
            with pytest.raises(ValueError):
                start_audit_run(
                    session, version_uid=world.version_uid, provider_mode="recorded",
                    idempotency_key="w59-wiring-neither",
                )
