"""A complete expert map is one immutable, replayable transaction."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.public import PAGE_PROFILE_ALGO_VERSION
from auditmanager.comparison.stage_links.map import LinkInput, StageSheetMapService
from auditmanager.comparison.stage_links.read import StageSheetReadService
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid


def uid(prefix: str) -> str:
    return f"{prefix}_{new_ulid()}"


def seed(database: Session) -> tuple[StageSheetMapService, str, str, str, str, str]:
    project, actor, pair = uid("prj"), uid("usr"), uid("stp")
    database.execute(text(
        "INSERT INTO project (project_uid, name) VALUES (:project, 'Stage links')"
    ), {"project": project})
    database.execute(text(
        "INSERT INTO app_user (user_uid, login, password_algorithm, password_iterations, "
        "password_salt, password_hash) VALUES "
        "(:actor, :login, 'pbkdf2_sha256', 100000, :salt, :hash)"
    ), {"actor": actor, "login": f"stage-link-{new_ulid().lower()}",
        "salt": "a" * 32, "hash": "b" * 64})
    documents = []
    profiles = []
    for side in ("left", "right"):
        document, version = uid("doc"), uid("ver")
        documents.append(document)
        database.execute(text(
            "INSERT INTO document (document_uid, project_uid, display_title) "
            "VALUES (:document, :project, :title)"
        ), {"document": document, "project": project, "title": side})
        database.execute(text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
            "media_type, byte_size, sha256, page_count) "
            "VALUES (:version, :document, 1, 'application/pdf', 4096, :sha, 2)"
        ), {"version": version, "document": document, "sha": "a" * 64})
        for page in (1, 2):
            profile = uid("cpr")
            profiles.append(profile)
            database.execute(text(
                "INSERT INTO comparison_page_profile "
                "(comparison_page_profile_id, version_uid, page_number, content_key, "
                "algo_version, status, profile) "
                "VALUES (:profile, :version, :page, :key, :algo, 'ready', "
                "CAST(:summary AS jsonb))"
            ), {"profile": profile, "version": version, "page": page,
                "key": str(page) * 64, "algo": PAGE_PROFILE_ALGO_VERSION,
                "summary": json.dumps({"stamp": {
                    "sheet_name": "План 2-го этажа корпус 4" if page == 1 else "Разрез корпус 4",
                    "sheet_number": str(page),
                }})})
    database.execute(text(
        "INSERT INTO stage_pair (stage_pair_id, project_uid, left_document_uid, "
        "right_document_uid, state, confirmed_by_user_uid, confirmed_at, command_id) "
        "VALUES (:pair, :project, :left, :right, 'confirmed', :actor, "
        "clock_timestamp(), :command)"
    ), {"pair": pair, "project": project, "left": documents[0],
        "right": documents[1], "actor": actor,
        "command": _command(database)})
    sessions = sessionmaker(
        bind=database.connection(), expire_on_commit=False,
        future=True, join_transaction_mode="create_savepoint",
    )
    return StageSheetMapService(sessions), pair, actor, profiles[0], profiles[1], profiles[2]


def _command(database: Session, kind: str = "confirm_stage_pair") -> str:
    command = uid("cmd")
    database.execute(text(
        "INSERT INTO command_record "
        "(command_id, command_type, idempotency_key, payload_fingerprint, state) "
        "VALUES (:command, :kind, :key, :sha, 'in_progress')"
    ), {"command": command, "kind": kind,
        "key": f"seed-stage-pair-{new_ulid()}", "sha": "f" * 64})
    database.execute(text(
        "UPDATE command_record SET state = 'succeeded', outcome = '{}'::jsonb "
        "WHERE command_id = :command"
    ), {"command": command})
    return command


def test_map_revisions_replay_and_keep_many_to_many_and_unpaired(
    comparison_session: Session,
) -> None:
    service, pair, actor, left_one, left_two, right = seed(comparison_session)
    first_items = (
        LinkInput("paired", left_one, right),
        LinkInput("paired", left_two, right),
    )
    first = service.apply(
        pair_id=pair, base_revision_id=None, items=first_items,
        user_uid=actor, actor_roles=frozenset({"expert"}),
        idempotency_key=f"stage-map-{new_ulid()}",
    )
    assert first.revision_no == 1 and first.source == "expert"
    assert [item.confidence for item in first.items] == ["manual", "manual"]
    assert [item.right_profile_id for item in first.items] == [right, right]
    assert service.current(pair_id=pair) == service.get(revision_id=first.revision_id)

    second = service.apply(
        pair_id=pair, base_revision_id=first.revision_id,
        items=(LinkInput("paired", left_one, right), LinkInput("only_left", left_two, None)),
        user_uid=actor, actor_roles=frozenset({"expert"}),
        idempotency_key=f"stage-map-{new_ulid()}",
    )
    assert second.revision_no == 2 and second.base_revision_id == first.revision_id
    assert second.items[1].confidence == "unpaired"
    assert service.get(revision_id=first.revision_id) == first
    page, cursor = service.page(pair_id=pair, after_revision_no=None, limit=1)
    assert page == (second,) and cursor == 2
    page, cursor = service.page(pair_id=pair, after_revision_no=cursor, limit=1)
    assert page == (first,) and cursor is None
    event = comparison_session.execute(text(
        "SELECT payload FROM audit_event WHERE event_type = 'stage.sheet_map_applied' "
        "AND aggregate_id = :pair ORDER BY sequence_no DESC LIMIT 1"
    ), {"pair": pair}).scalar_one()
    assert event["revision_id"] in {first.revision_id, second.revision_id}


def test_map_replay_stale_base_and_scope_refusal(comparison_session: Session) -> None:
    service, pair, actor, left_one, _left_two, right = seed(comparison_session)
    key = f"stage-map-{new_ulid()}"
    request = dict(
        pair_id=pair, base_revision_id=None,
        items=(LinkInput("paired", left_one, right),),
        user_uid=actor, actor_roles=frozenset({"expert"}), idempotency_key=key,
    )
    first = service.apply(**request)
    assert service.apply(**request) == first
    with pytest.raises(DomainError) as reused:
        service.apply(**(request | {"items": (LinkInput("only_left", left_one, None),)}))
    assert reused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE
    with pytest.raises(DomainError) as stale:
        service.apply(**(request | {"idempotency_key": f"stage-map-{new_ulid()}"}))
    assert stale.value.code is ErrorCode.CONFLICT
    with pytest.raises(DomainError) as wrong_side:
        service.apply(**(request | {
            "base_revision_id": first.revision_id,
            "items": (LinkInput("paired", right, left_one),),
            "idempotency_key": f"stage-map-{new_ulid()}",
        }))
    assert wrong_side.value.code is ErrorCode.NOT_FOUND
    _other_service, _other_pair, _other_actor, foreign_left, _foreign_second, _foreign_right = seed(
        comparison_session
    )
    with pytest.raises(DomainError) as foreign:
        service.apply(**(request | {
            "base_revision_id": first.revision_id,
            "items": (LinkInput("paired", foreign_left, right),),
            "idempotency_key": f"stage-map-{new_ulid()}",
        }))
    assert foreign.value.code is ErrorCode.NOT_FOUND
    with pytest.raises(DomainError) as contradictory:
        service.apply(**(request | {
            "base_revision_id": first.revision_id,
            "items": (LinkInput("paired", left_one, right), LinkInput("only_left", left_one, None)),
            "idempotency_key": f"stage-map-{new_ulid()}",
        }))
    assert contradictory.value.code is ErrorCode.VALIDATION_FAILED
    assert service.current(pair_id=pair) == first


def test_passports_use_current_ready_profiles_and_refuse_missing_new_version(
    comparison_session: Session,
) -> None:
    service, pair, _actor, left_one, _left_two, right_one = seed(comparison_session)
    reader = StageSheetReadService(service._sessions)
    passports = reader.passports(pair_id=pair)
    assert len(passports) == 4
    assert (passports[0].profile_id, passports[0].side, passports[0].building,
            passports[0].floor) == (left_one, "left", "4", "2")
    hints = reader.suggestions(pair_id=pair)
    assert hints[0].left_profile_id == left_one
    assert hints[0].right_profile_id == right_one
    assert hints[0].confidence == "high"

    right_document = comparison_session.execute(text(
        "SELECT right_document_uid FROM stage_pair WHERE stage_pair_id = :pair"
    ), {"pair": pair}).scalar_one()
    comparison_session.execute(text(
        "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
        "media_type, byte_size, sha256, page_count) "
        "VALUES (:version, :document, 2, 'application/pdf', 4096, :sha, 1)"
    ), {"version": uid("ver"), "document": right_document, "sha": "b" * 64})
    with pytest.raises(DomainError) as missing:
        reader.passports(pair_id=pair)
    assert missing.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE


def test_unchanged_high_row_keeps_confidence_in_next_complete_revision(
    comparison_session: Session,
) -> None:
    service, pair, actor, left_one, left_two, right = seed(comparison_session)
    old_revision = uid("slk")
    comparison_session.execute(text(
        "INSERT INTO stage_link_revision "
        "(stage_link_revision_id, stage_pair_id, revision_no, source, input_sha256, "
        "actor_user_uid, command_id) "
        "VALUES (:revision, :pair, 1, 'automatic', :sha, :actor, :command)"
    ), {"revision": old_revision, "pair": pair, "sha": "e" * 64,
        "actor": actor, "command": _command(comparison_session, "apply_stage_sheet_map")})
    comparison_session.execute(text(
        "INSERT INTO stage_link_item "
        "(stage_link_item_id, stage_link_revision_id, row_no, left_profile_id, "
        "right_profile_id, relation, confidence) "
        "VALUES (:item, :revision, 1, :left, :right, 'paired', 'high')"
    ), {"item": uid("sli"), "revision": old_revision,
        "left": left_one, "right": right})
    changed = service.apply(
        pair_id=pair, base_revision_id=old_revision,
        items=(LinkInput("paired", left_one, right), LinkInput("only_left", left_two, None)),
        user_uid=actor, actor_roles=frozenset({"expert"}),
        idempotency_key=f"stage-map-{new_ulid()}",
    )
    assert [item.confidence for item in changed.items] == ["high", "unpaired"]
    assert service.get(revision_id=old_revision).items[0].confidence == "high"


def test_assembly_passports_follow_active_member_order(comparison_session: Session) -> None:
    service, pair, actor, _left_one, _left_two, _right_one = seed(comparison_session)
    project, original_left, original_right = comparison_session.execute(text(
        "SELECT project_uid, left_document_uid, right_document_uid "
        "FROM stage_pair WHERE stage_pair_id = :pair"
    ), {"pair": pair}).one()
    extra_document, extra_version, extra_profile, assembly = (
        uid("doc"), uid("ver"), uid("cpr"), uid("sas")
    )
    comparison_session.execute(text(
        "INSERT INTO document (document_uid, project_uid, display_title) "
        "VALUES (:document, :project, 'Assembly member')"
    ), {"document": extra_document, "project": project})
    comparison_session.execute(text(
        "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
        "media_type, byte_size, sha256, page_count) "
        "VALUES (:version, :document, 1, 'application/pdf', 4096, :sha, 1)"
    ), {"version": extra_version, "document": extra_document, "sha": "d" * 64})
    comparison_session.execute(text(
        "INSERT INTO comparison_page_profile "
        "(comparison_page_profile_id, version_uid, page_number, content_key, "
        "algo_version, status, profile) "
        "VALUES (:profile, :version, 1, :key, :algo, 'ready', '{}'::jsonb)"
    ), {"profile": extra_profile, "version": extra_version,
        "key": "9" * 64, "algo": PAGE_PROFILE_ALGO_VERSION})
    comparison_session.execute(text(
        "INSERT INTO stage_assembly "
        "(stage_assembly_id, project_uid, label, actor_user_uid, command_id) "
        "VALUES (:assembly, :project, 'Assembly', :actor, :command)"
    ), {"assembly": assembly, "project": project, "actor": actor,
        "command": _command(comparison_session, "create_stage_assembly")})
    for number, document in enumerate((original_right, extra_document), 1):
        comparison_session.execute(text(
            "INSERT INTO stage_assembly_member "
            "(stage_assembly_member_id, stage_assembly_id, member_no, document_uid, "
            "action, actor_user_uid, command_id) "
            "VALUES (:member, :assembly, :number, :document, 'add', :actor, :command)"
        ), {"member": uid("sam"), "assembly": assembly, "number": number,
            "document": document, "actor": actor,
            "command": _command(comparison_session, "stage_assembly_member_add")})
    comparison_session.execute(text(
        "UPDATE stage_pair SET state = 'archived', archived_at = clock_timestamp() "
        "WHERE stage_pair_id = :pair"
    ), {"pair": pair})
    assembly_pair = uid("stp")
    comparison_session.execute(text(
        "INSERT INTO stage_pair "
        "(stage_pair_id, project_uid, left_document_uid, stage_assembly_id, "
        "state, confirmed_by_user_uid, confirmed_at, command_id) "
        "VALUES (:pair, :project, :left, :assembly, 'confirmed', :actor, "
        "clock_timestamp(), :command)"
    ), {"pair": assembly_pair, "project": project, "left": original_left,
        "assembly": assembly, "actor": actor,
        "command": _command(comparison_session)})
    passports = StageSheetReadService(service._sessions).passports(pair_id=assembly_pair)
    assert [page.profile_id for page in passports[-3:]] == [
        page.profile_id for page in passports[2:4]
    ] + [extra_profile]
    assert all(page.side == "right" for page in passports[2:])
