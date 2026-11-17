"""The catalog reads PostgreSQL identities and current expert classifications."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.bootstrap.adapters import ComparisonStagePairAdapter
from auditmanager.comparison.stage.assemblies import StageAssemblyService
from auditmanager.comparison.stage.pairs import StagePairCommandService, StagePairReadRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid


def uid(prefix: str) -> str:
    return f"{prefix}_{new_ulid()}"


def add_classified_document(
    session: Session, project: str, actor: str, stage: str, title: str,
) -> str:
    document = uid("doc")
    version = uid("ver")
    session.execute(
        text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, :t)"),
        {"d": document, "p": project, "t": title},
    )
    session.execute(
        text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, "
            "byte_size, sha256, page_count) VALUES (:v, :d, 1, 'application/pdf', 4096, :sha, 1)"
        ),
        {"v": version, "d": document, "sha": "c" * 64},
    )
    session.execute(
        text(
            "INSERT INTO document_version_classification "
            "(version_uid, project_stage, section_code, confirmed_by_user_uid) "
            "VALUES (:v, :stage, 'AR', :actor)"
        ),
        {"v": version, "stage": stage, "actor": actor},
    )
    return document


def seed(session: Session) -> tuple[str, str, str, str, str]:
    project = uid("prj")
    actor = uid("usr")
    session.execute(text("INSERT INTO project (project_uid, name) VALUES (:id, 'Stage read')"), {"id": project})
    session.execute(
        text(
            "INSERT INTO app_user (user_uid, login, password_algorithm, password_iterations, "
            "password_salt, password_hash) VALUES (:id, :login, 'pbkdf2_sha256', 100000, :salt, :hash)"
        ),
        {"id": actor, "login": f"stage-{new_ulid().lower()}", "salt": "a" * 32, "hash": "b" * 64},
    )
    left = add_classified_document(session, project, actor, "P", " Site 01 ")
    right = add_classified_document(session, project, actor, "R", "site 01")
    other = add_classified_document(session, project, actor, "R", "Other 02")
    return project, left, right, other, actor


def test_stage_pair_read_uses_confirmed_classifications_and_opaque_ids(
    comparison_session: Session,
) -> None:
    project, left, right, _other, _actor = seed(comparison_session)
    repository = StagePairReadRepository()
    suggestions = repository.suggestions(comparison_session, project_uid=project)
    assert len(suggestions) == 1
    suggestion = suggestions[0]
    assert (suggestion.left_document_uid, suggestion.right_document_uid) == (left, right)

    pair = uid("stp")
    comparison_session.execute(
        text(
            "INSERT INTO stage_pair (stage_pair_id, project_uid, left_document_uid, "
            "right_document_uid, state) VALUES (:pair, :project, :left, :right, 'suggested')"
        ),
        {"pair": pair, "project": project, "left": left, "right": right},
    )
    page, next_pair = repository.page(
        comparison_session, project_uid=project, after_pair_id=None, limit=1,
    )
    assert next_pair is None
    assert len(page) == 1
    assert page[0] == repository.get(comparison_session, pair)
    assert (page[0].left_document_uid, page[0].right_document_uid) == (left, right)


def test_expert_pair_confirmation_is_keyed_and_binds_document_identities(
    comparison_session: Session,
) -> None:
    project, left, right, other, actor = seed(comparison_session)
    sessions = sessionmaker(
        bind=comparison_session.connection(), expire_on_commit=False,
        future=True, join_transaction_mode="create_savepoint",
    )
    service = StagePairCommandService(sessions)
    request = {
        "project_uid": project, "left_document_uid": left,
        "right_document_uid": right, "assembly_id": None,
        "user_uid": actor, "idempotency_key": f"stage-confirm-{new_ulid()}",
    }
    created = service.confirm_pair(**request)
    replay = service.confirm_pair(**request)
    assert created == replay
    assert created.state == "confirmed"
    assert created.left_document_uid == left
    assert created.right_document_uid == right
    assert created.confirmed_at is not None
    assert comparison_session.execute(
        text("SELECT count(*) FROM stage_pair WHERE project_uid = :project"),
        {"project": project},
    ).scalar_one() == 1
    assert StagePairReadRepository.suggestions(
        comparison_session, project_uid=project,
    ) == ()

    with pytest.raises(DomainError) as reused:
        service.confirm_pair(**(request | {"right_document_uid": other}))
    assert reused.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSE

    with pytest.raises(DomainError) as duplicate:
        service.confirm_pair(**(request | {"idempotency_key": f"stage-duplicate-{new_ulid()}"}))
    assert duplicate.value.code is ErrorCode.CONFLICT

    choice = {
        "pair_id": created.pair_id, "completeness": "partial",
        "user_uid": actor, "idempotency_key": f"stage-completeness-{new_ulid()}",
    }
    changed = service.set_completeness(**choice)
    assert changed.completeness == "partial"
    assert service.set_completeness(**choice) == changed
    event = comparison_session.execute(
        text(
            "SELECT payload FROM audit_event "
            "WHERE aggregate_type = 'StagePair' AND aggregate_id = :pair "
            "AND event_type = 'stage.pair_completeness_changed'"
        ),
        {"pair": created.pair_id},
    ).scalar_one()
    assert event["from"] == "unknown" and event["to"] == "partial"
    assert event["actor_uid"] == actor


def test_two_R_documents_form_an_append_only_assembly_and_pair(
    comparison_session: Session,
) -> None:
    project, left, right, other, actor = seed(comparison_session)
    sessions = sessionmaker(
        bind=comparison_session.connection(), expire_on_commit=False,
        future=True, join_transaction_mode="create_savepoint",
    )
    assemblies = StageAssemblyService(sessions)
    request = {
        "project_uid": project, "label": "Корпус А",
        "document_uids": (right, other), "user_uid": actor,
        "idempotency_key": f"stage-assembly-{new_ulid()}",
    }
    created = assemblies.create(**request)
    assert assemblies.create(**request) == created
    assert created.member_revision_no == 2
    assert [(m.document_uid, m.member_no) for m in created.members] == [(right, 1), (other, 2)]
    assert comparison_session.execute(
        text("SELECT count(DISTINCT command_id) FROM stage_assembly_member WHERE stage_assembly_id = :id"),
        {"id": created.assembly_id},
    ).scalar_one() == 2

    third = add_classified_document(comparison_session, project, actor, "R", "Third 03")
    revision = {
        "assembly_id": created.assembly_id, "base_member_no": 2,
        "add_document_uids": (third,), "remove_document_uids": (right,),
        "user_uid": actor, "idempotency_key": f"stage-assembly-revise-{new_ulid()}",
    }
    revised = assemblies.revise(**revision)
    assert assemblies.revise(**revision) == revised
    assert [(m.document_uid, m.member_no) for m in revised.members] == [(other, 2), (third, 4)]
    assert comparison_session.execute(
        text("SELECT count(*) FROM stage_assembly_member WHERE stage_assembly_id = :id"),
        {"id": created.assembly_id},
    ).scalar_one() == 4
    with pytest.raises(DomainError) as stale:
        assemblies.revise(**(revision | {"idempotency_key": f"stage-stale-{new_ulid()}"}))
    assert stale.value.code is ErrorCode.CONFLICT

    fourth = add_classified_document(comparison_session, project, actor, "R", "Fourth 04")
    added = assemblies.revise(
        assembly_id=created.assembly_id, base_member_no=revised.member_revision_no,
        add_document_uids=(fourth,), remove_document_uids=(), user_uid=actor,
        idempotency_key=f"stage-add-fourth-{new_ulid()}",
    )
    removed = assemblies.revise(
        assembly_id=created.assembly_id, base_member_no=added.member_revision_no,
        add_document_uids=(), remove_document_uids=(fourth,), user_uid=actor,
        idempotency_key=f"stage-remove-fourth-{new_ulid()}",
    )
    assert removed.member_revision_no == 6
    assert max(member.member_no for member in removed.members) == 4
    assert assemblies.get(created.assembly_id).member_revision_no == 6

    pair = StagePairCommandService(sessions).confirm_pair(
        project_uid=project, left_document_uid=left, right_document_uid=None,
        assembly_id=created.assembly_id, user_uid=actor,
        idempotency_key=f"stage-pair-assembly-{new_ulid()}",
    )
    assert pair.assembly_id == created.assembly_id
    assert pair.right_document_uid is None
    assert StagePairReadRepository.suggestions(
        comparison_session, project_uid=project,
    ) == ()


def test_pair_command_refuses_a_foreign_document_without_revealing_it(
    comparison_session: Session,
) -> None:
    project, left, _right, _other, actor = seed(comparison_session)
    foreign_project = uid("prj")
    comparison_session.execute(
        text("INSERT INTO project (project_uid, name) VALUES (:project, 'Foreign stage')"),
        {"project": foreign_project},
    )
    foreign = add_classified_document(
        comparison_session, foreign_project, actor, "R", "Site 01",
    )
    sessions = sessionmaker(
        bind=comparison_session.connection(), expire_on_commit=False,
        future=True, join_transaction_mode="create_savepoint",
    )
    with pytest.raises(DomainError) as refused:
        StagePairCommandService(sessions).confirm_pair(
            project_uid=project, left_document_uid=left,
            right_document_uid=foreign, assembly_id=None, user_uid=actor,
            idempotency_key=f"stage-foreign-{new_ulid()}",
        )
    assert refused.value.code is ErrorCode.NOT_FOUND
    assert comparison_session.execute(
        text("SELECT count(*) FROM stage_pair WHERE project_uid = :project"),
        {"project": project},
    ).scalar_one() == 0


# --- how many documents have no pair (`UIP-S16-02`) --------------------------------------------------------------------------


def add_unclassified_document(session: Session, project: str, title: str) -> str:
    document = uid("doc")
    version = uid("ver")
    session.execute(
        text("INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, :t)"),
        {"d": document, "p": project, "t": title},
    )
    session.execute(
        text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, "
            "byte_size, sha256, page_count) VALUES (:v, :d, 1, 'application/pdf', 4096, :sha, 1)"
        ),
        {"v": version, "d": document, "sha": "d" * 64},
    )
    return document


def test_unpaired_counts_follow_the_confirmed_pairs_and_assemblies_of_the_whole_project(
    comparison_session: Session,
) -> None:
    project, left, right, other, actor = seed(comparison_session)
    repository = StagePairReadRepository()
    sessions = sessionmaker(
        bind=comparison_session.connection(), expire_on_commit=False,
        future=True, join_transaction_mode="create_savepoint",
    )

    def counts() -> tuple[int, int]:
        found = repository.unpaired_counts(comparison_session, project_uid=project)
        return found.stage_p, found.stage_r

    # the seed: one П, two Р, all classified by the expert
    assert counts() == (1, 2)

    # not counted: a document nobody classified, an archived one, and a document of another project
    add_unclassified_document(comparison_session, project, "No stage yet")
    archived = add_classified_document(comparison_session, project, actor, "R", "Archived 09")
    comparison_session.execute(
        text("UPDATE document SET archived_at = clock_timestamp(), archived_by_user_uid = :actor WHERE document_uid = :d"),
        {"d": archived, "actor": actor},
    )
    foreign_project = uid("prj")
    comparison_session.execute(
        text("INSERT INTO project (project_uid, name) VALUES (:project, 'Foreign counts')"), {"project": foreign_project},
    )
    add_classified_document(comparison_session, foreign_project, actor, "P", "Foreign P")
    assert counts() == (1, 2)

    # a pair that is only suggested binds nothing; the second П document counts
    extra = add_classified_document(comparison_session, project, actor, "P", "Extra 03")
    comparison_session.execute(
        text(
            "INSERT INTO stage_pair (stage_pair_id, project_uid, left_document_uid, "
            "right_document_uid, state) VALUES (:pair, :project, :left, :right, 'suggested')"
        ),
        {"pair": uid("stp"), "project": project, "left": extra, "right": other},
    )
    assert counts() == (2, 2)

    # a confirmed pair binds its two documents
    pairs = StagePairCommandService(sessions)
    pairs.confirm_pair(
        project_uid=project, left_document_uid=left, right_document_uid=right, assembly_id=None,
        user_uid=actor, idempotency_key=f"stage-count-pair-{new_ulid()}",
    )
    assert counts() == (1, 1)

    # an assembly binds nothing until a confirmed pair names it, and then binds its current members
    third = add_classified_document(comparison_session, project, actor, "R", "Third 04")
    assemblies = StageAssemblyService(sessions)
    assembly = assemblies.create(
        project_uid=project, label="Корпус Б", document_uids=(other, third), user_uid=actor,
        idempotency_key=f"stage-count-assembly-{new_ulid()}",
    )
    assert counts() == (1, 2)
    pairs.confirm_pair(
        project_uid=project, left_document_uid=extra, right_document_uid=None, assembly_id=assembly.assembly_id,
        user_uid=actor, idempotency_key=f"stage-count-assembly-pair-{new_ulid()}",
    )
    assert counts() == (0, 0)
    # one revision takes `third` out and puts `fourth` in (an assembly keeps two to a hundred members): the member taken out has no pair
    # again and the member put in is bound by the pair that names the assembly
    fourth = add_classified_document(comparison_session, project, actor, "R", "Fourth 05")
    assert counts() == (0, 1), "a Р document that is in no assembly yet has no pair"
    assemblies.revise(
        assembly_id=assembly.assembly_id, base_member_no=assembly.member_revision_no,
        add_document_uids=(fourth,), remove_document_uids=(third,), user_uid=actor,
        idempotency_key=f"stage-count-assembly-revise-{new_ulid()}",
    )
    assert counts() == (0, 1), "`third` is out of the assembly and has no pair again, `fourth` is in it and has one"

    # the wire answer carries the same two numbers on every page, whatever the page holds
    adapter = ComparisonStagePairAdapter(sessions, comparison_modules="versions,stages")
    first = adapter.list_pairs(project_uid=project, cursor=None, limit=1)
    assert len(first.items) == 1 and first.page.next_cursor is not None
    second = adapter.list_pairs(project_uid=project, cursor=first.page.next_cursor, limit=1)
    whole = adapter.list_pairs(project_uid=project, cursor=None, limit=50)
    assert len(second.items) == 1 and len(whole.items) == 3, "two confirmed pairs and the suggested one"
    for page in (first, second, whole):
        assert (page.unpaired_p_count, page.unpaired_r_count) == (0, 1)
