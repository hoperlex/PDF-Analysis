"""Evidence rows are one transaction under the current confirmed map revision."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.comparison.public import PAGE_PROFILE_ALGO_VERSION
from auditmanager.comparison.stage_text import SheetLink, TextFragment, build_raw_differences
from auditmanager.comparison.stage_text.fragments import canonical_text
from auditmanager.comparison.stage_text.store import StageTextEvidenceStore
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid


def _id(prefix: str) -> str:
    return f"{prefix}_{new_ulid()}"


def _command(session: Session, kind: str) -> str:
    command = _id("cmd")
    session.execute(text(
        "INSERT INTO command_record (command_id, command_type, idempotency_key, "
        "payload_fingerprint, state) VALUES "
        "(:id, :kind, :key, :sha, 'in_progress')"
    ), {"id": command, "kind": kind,
        "key": f"stage-test-{new_ulid()}", "sha": "f" * 64})
    session.execute(text(
        "UPDATE command_record SET state = 'succeeded', outcome = '{}'::jsonb "
        "WHERE command_id = :id"
    ), {"id": command})
    return command


def _seed(session: Session) -> tuple[StageTextEvidenceStore, str, str, str, str, str]:
    project, actor, pair, revision = _id("prj"), _id("usr"), _id("stp"), _id("slk")
    session.execute(text("INSERT INTO project (project_uid, name) VALUES (:id, 'Text store')"),
                    {"id": project})
    session.execute(text(
        "INSERT INTO app_user (user_uid, login, password_algorithm, password_iterations, "
        "password_salt, password_hash) VALUES "
        "(:id, :login, 'pbkdf2_sha256', 100000, :salt, :hash)"
    ), {"id": actor, "login": f"stage-text-{new_ulid().lower()}",
        "salt": "a" * 32, "hash": "b" * 64})
    profiles: list[str] = []
    documents: list[str] = []
    for side in ("left", "right"):
        document, version, profile = _id("doc"), _id("ver"), _id("cpr")
        documents.append(document)
        profiles.append(profile)
        session.execute(text(
            "INSERT INTO document (document_uid, project_uid, display_title) "
            "VALUES (:document, :project, :title)"
        ), {"document": document, "project": project, "title": side})
        session.execute(text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, "
            "media_type, byte_size, sha256, page_count) "
            "VALUES (:version, :document, 1, 'application/pdf', 4096, :sha, 1)"
        ), {"version": version, "document": document, "sha": "a" * 64})
        session.execute(text(
            "INSERT INTO comparison_page_profile (comparison_page_profile_id, version_uid, "
            "page_number, content_key, algo_version, status, profile) "
            "VALUES (:profile, :version, 1, :key, :algo, 'ready', '{}'::jsonb)"
        ), {"profile": profile, "version": version,
            "key": "1" * 64, "algo": PAGE_PROFILE_ALGO_VERSION})
    session.execute(text(
        "INSERT INTO stage_pair (stage_pair_id, project_uid, left_document_uid, "
        "right_document_uid, state, confirmed_by_user_uid, confirmed_at, command_id) "
        "VALUES (:pair, :project, :left, :right, 'confirmed', :actor, "
        "clock_timestamp(), :command)"
    ), {"pair": pair, "project": project, "left": documents[0], "right": documents[1],
        "actor": actor, "command": _command(session, "confirm_stage_pair")})
    session.execute(text(
        "INSERT INTO stage_link_revision (stage_link_revision_id, stage_pair_id, "
        "revision_no, source, input_sha256, actor_user_uid, command_id) "
        "VALUES (:revision, :pair, 1, 'expert', :sha, :actor, :command)"
    ), {"revision": revision, "pair": pair, "sha": "e" * 64,
        "actor": actor, "command": _command(session, "apply_stage_sheet_map")})
    session.execute(text(
        "INSERT INTO stage_link_item (stage_link_item_id, stage_link_revision_id, row_no, "
        "left_profile_id, right_profile_id, relation, confidence) "
        "VALUES (:id, :revision, 1, :left, :right, 'paired', 'manual')"
    ), {"id": _id("sli"), "revision": revision,
        "left": profiles[0], "right": profiles[1]})
    sessions = sessionmaker(bind=session.connection(), expire_on_commit=False,
                           future=True, join_transaction_mode="create_savepoint")
    return StageTextEvidenceStore(sessions), pair, revision, actor, profiles[0], profiles[1]


def _fragment(profile: str, side: str, value: str, ordinal: int) -> TextFragment:
    key = hashlib.sha256(f"{profile}:{ordinal}:{value}".encode()).hexdigest()
    return TextFragment(key, profile, side, 1, value, canonical_text(value),
                        {"x0": 10.0, "top": float(ordinal * 20),
                         "x1": 80.0, "bottom": float(ordinal * 20 + 8)})


def _batch(left: str, right: str):
    fragments = (
        _fragment(left, "left", "Кабель ВВГ 3х4", 1),
        _fragment(right, "right", "Кабель ВВГ 3х4", 1),
        _fragment(left, "left", "Нагрузка 10 кВт", 2),
        _fragment(right, "right", "Нагрузка 20 кВт", 2),
    )
    manifest = {profile: frozenset(f.content_key for f in fragments if f.profile_id == profile)
                for profile in (left, right)}
    raw = build_raw_differences([SheetLink(left, right)], fragments,
                                {left: (100, 100), right: (100, 100)}, manifest)
    return fragments, manifest, raw


def _completed_run(
    session: Session, pair: str, revision: str, actor: str, left: str, right: str,
) -> None:
    """A completed deterministic run seal for read-only storage fixtures."""
    pins = session.execute(text(
        "SELECT version_uid FROM comparison_page_profile "
        "WHERE comparison_page_profile_id = ANY(CAST(:ids AS text[])) "
        "ORDER BY array_position(CAST(:ids AS text[]), comparison_page_profile_id)"
    ), {"ids": [left, right]}).scalars().all()
    assert len(pins) == 2
    session.execute(text(
        "INSERT INTO stage_chain_run "
        "(stage_chain_run_id, stage_pair_id, stage_link_revision_id, input_sha256, "
        "pinned_version_uids, state, actor_user_uid, command_id) "
        "VALUES (:run, :pair, :revision, :sha, CAST(:pins AS jsonb), "
        "'completed', :actor, :command)"
    ), {"run": _id("crn"), "pair": pair, "revision": revision,
        "sha": "a" * 64, "pins": json.dumps(pins),
        "actor": actor, "command": _command(session, "recompute_stage_text_evidence")})


def test_atomic_write_and_exact_replay(comparison_session: Session) -> None:
    store, pair, revision, _actor, left, right = _seed(comparison_session)
    fragments, manifest, raw = _batch(left, right)
    request = dict(pair_id=pair, revision_id=revision, fragments=fragments,
                   expected_keys=manifest, raw=raw, hints=())
    first = store.write(**request)
    replay = store.write(**request)
    assert (first.fragment_count, first.exclusion_count, first.difference_count,
            first.hint_count, first.replayed) == (4, 1, 1, 0, False)
    assert replay == replace(first, replayed=True)
    for table, count in (("stage_text_fragment", 4), ("stage_text_exclusion", 1),
                         ("stage_text_difference", 1), ("stage_text_hint", 0)):
        actual = comparison_session.execute(text(
            f"SELECT count(*) FROM {table} WHERE stage_pair_id = :pair"
        ), {"pair": pair}).scalar_one()
        assert actual == count
    with pytest.raises(DomainError) as changed:
        store.write(**(request | {"hints": (), "raw": replace(raw, differences=())}))
    assert changed.value.code is ErrorCode.CONFLICT


def test_stale_map_and_wrong_side_refuse_without_writes(comparison_session: Session) -> None:
    store, pair, revision, actor, left, right = _seed(comparison_session)
    fragments, manifest, raw = _batch(left, right)
    newer = _id("slk")
    comparison_session.execute(text(
        "INSERT INTO stage_link_revision (stage_link_revision_id, stage_pair_id, revision_no, "
        "base_revision_id, source, input_sha256, actor_user_uid, command_id) "
        "VALUES (:revision, :pair, 2, :base, 'expert', :sha, :actor, :command)"
    ), {"revision": newer, "pair": pair, "base": revision, "sha": "e" * 64,
        "actor": actor, "command": _command(comparison_session, "apply_stage_sheet_map")})
    with pytest.raises(DomainError) as stale:
        store.write(pair_id=pair, revision_id=revision, fragments=fragments,
                    expected_keys=manifest, raw=raw, hints=())
    assert stale.value.code is ErrorCode.CONFLICT
    assert comparison_session.execute(text(
        "SELECT count(*) FROM stage_text_fragment WHERE stage_pair_id = :pair"
    ), {"pair": pair}).scalar_one() == 0
    with pytest.raises(DomainError) as unlinked:
        store.write(pair_id=pair, revision_id=newer, fragments=fragments,
                    expected_keys=manifest, raw=raw, hints=())
    assert unlinked.value.code is ErrorCode.CONFLICT
    bad = replace(fragments[0], profile_id=right)
    with pytest.raises(DomainError) as wrong_side:
        store.write(pair_id=pair, revision_id=newer,
                    fragments=(bad,) + fragments[1:], expected_keys={
                        right: frozenset({bad.content_key, fragments[1].content_key,
                                          fragments[3].content_key}),
                        left: frozenset({fragments[2].content_key}),
                    }, raw=raw, hints=())
    assert wrong_side.value.code is ErrorCode.NOT_FOUND


def test_failure_after_first_fragment_rolls_back_batch(comparison_session: Session) -> None:
    store, pair, revision, _actor, left, right = _seed(comparison_session)
    fragments, manifest, raw = _batch(left, right)
    malformed = replace(fragments[1], box_anchor={"x0": float("nan")})
    with pytest.raises(SQLAlchemyError):
        store.write(pair_id=pair, revision_id=revision,
                    fragments=(fragments[0], malformed, *fragments[2:]),
                    expected_keys=manifest, raw=raw, hints=())
    assert comparison_session.execute(text(
        "SELECT count(*) FROM stage_text_fragment WHERE stage_pair_id = :pair"
    ), {"pair": pair}).scalar_one() == 0
