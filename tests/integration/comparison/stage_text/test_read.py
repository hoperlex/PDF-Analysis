"""Stored evidence reads distinguish absence from an empty verified page."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from auditmanager.comparison.stage_text.read import StageTextReadService
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity import new_ulid
from tests.integration.comparison.stage_text.test_store import _batch, _command, _completed_run, _seed


def test_read_pages_and_unmaterialized_refusal(comparison_session: Session) -> None:
    store, pair, revision, actor, left, right = _seed(comparison_session)
    reader = StageTextReadService(store._sessions)
    with pytest.raises(DomainError) as before:
        reader.fragments(pair_id=pair, after=None, limit=2)
    assert before.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    with pytest.raises(DomainError) as before_revision:
        reader.revision_rows(kind="differences", revision_id=revision, after=None, limit=2)
    assert before_revision.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE

    fragments, manifest, raw = _batch(left, right)
    store.write(pair_id=pair, revision_id=revision,
                fragments=fragments, expected_keys=manifest, raw=raw, hints=())
    _completed_run(comparison_session, pair, revision, actor, left, right)
    first, cursor = reader.fragments(pair_id=pair, after=None, limit=2)
    second, end = reader.fragments(pair_id=pair, after=cursor, limit=2)
    assert len(first) == len(second) == 2 and end is None
    assert len({row["content_key"] for row in first + second}) == 4
    exclusion, _ = reader.revision_rows(kind="exclusions", revision_id=revision,
                                        after=None, limit=10)
    difference, _ = reader.revision_rows(kind="differences", revision_id=revision,
                                         after=None, limit=10)
    hints, _ = reader.revision_rows(kind="hints", revision_id=revision,
                                    after=None, limit=10)
    assert len(exclusion) == len(difference) == 1 and hints == ()
    with pytest.raises(DomainError) as foreign_cursor:
        reader.fragments(pair_id=pair, after="f" * 64, limit=1)
    assert foreign_cursor.value.code is ErrorCode.VALIDATION_FAILED

    newer = f"slk_{new_ulid()}"
    comparison_session.execute(text(
        "INSERT INTO stage_link_revision (stage_link_revision_id, stage_pair_id, revision_no, "
        "base_revision_id, source, input_sha256, actor_user_uid, command_id) "
        "VALUES (:revision, :pair, 2, :base, 'expert', :sha, :actor, :command)"
    ), {"revision": newer, "pair": pair, "base": revision, "sha": "e" * 64,
        "actor": actor, "command": _command(comparison_session, "apply_stage_sheet_map")})
    historical, _ = reader.revision_rows(kind="differences", revision_id=revision,
                                         after=None, limit=10)
    assert len(historical) == 1
    with pytest.raises(DomainError) as unmaterialized_newer:
        reader.revision_rows(kind="differences", revision_id=newer, after=None, limit=10)
    assert unmaterialized_newer.value.code is ErrorCode.DEPENDENCY_UNAVAILABLE


def test_unknown_parent_is_not_an_empty_page(comparison_session: Session) -> None:
    store, _pair, _revision, _actor, _left, _right = _seed(comparison_session)
    reader = StageTextReadService(store._sessions)
    with pytest.raises(DomainError) as pair:
        reader.fragments(pair_id="stp_01ARZ3NDEKTSV4RRFFQ69G5FAV", after=None, limit=5)
    assert pair.value.code is ErrorCode.NOT_FOUND
    with pytest.raises(DomainError) as revision:
        reader.revision_rows(kind="hints", revision_id="slk_01ARZ3NDEKTSV4RRFFQ69G5FAV",
                             after=None, limit=5)
    assert revision.value.code is ErrorCode.NOT_FOUND
