"""Unserved Run INSERT pin and v1/v2 frozen-digest compatibility."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from auditmanager.runs import repository as run_repository
from auditmanager.runs.commands import frozen_input_digest


SNAPSHOT = "ns_01M59N8QNBVN91ACA2HCE6VE74"
SET = "nrs_01M59N8QNBVN91ACA2HCE6VE74"


def _digest(*, snapshot: str | None, set_sha: str | None = None) -> str:
    return frozen_input_digest(
        version_uid="ver_01M59N8QNBVN91ACA2HCE6VE74",
        blob_ids={"source": "blob_01M59N8QNBVN91ACA2HCE6VE74"},
        analysis_profile_id="profile-v2", prompt_bundle_id="bundle-v2",
        norms_snapshot_id=snapshot, norm_retrieval_set_sha256=set_sha,
    )


def test_set_digest_is_added_only_when_explicitly_pinned() -> None:
    old_null = _digest(snapshot=None)
    old_snapshot = _digest(snapshot=SNAPSHOT)
    assert old_null == _digest(snapshot=None, set_sha=None)
    assert old_snapshot == _digest(snapshot=SNAPSHOT, set_sha=None)
    assert old_null != old_snapshot
    assert _digest(snapshot=SNAPSHOT, set_sha="a" * 64) != old_snapshot
    assert _digest(snapshot=SNAPSHOT, set_sha="b" * 64) != _digest(
        snapshot=SNAPSHOT, set_sha="a" * 64,
    )
    with pytest.raises(ValueError, match="snapshot pin"):
        _digest(snapshot=None, set_sha="a" * 64)
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        _digest(snapshot=SNAPSHOT, set_sha="A" * 64)


def test_run_insert_freezes_set_id_or_refuses_missing_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statements: list[dict[str, object]] = []
    session = SimpleNamespace(execute=lambda _statement, params: statements.append(params))
    repo = run_repository.RunRepository()
    monkeypatch.setattr(run_repository.RunRepository, "topology", lambda _self, _session: object())
    monkeypatch.setattr(run_repository, "assert_initial", lambda *_args: None)
    monkeypatch.setattr(run_repository, "append_execution_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(run_repository.RunRepository, "get", lambda _self, _session, run_id: run_id)

    kwargs = dict(
        run_id="run_01M59N8QNBVN91ACA2HCE6VE74", project_uid="project-id",
        version_uid="version-id", analysis_profile_id="profile-v2",
        prompt_bundle_id="bundle-v2", provider_mode="recorded",
        frozen_input_digest="a" * 64, command_id=None,
    )
    with pytest.raises(ValueError, match="snapshot pin"):
        repo.create(session, **kwargs, norm_retrieval_set_id=SET)
    assert not statements
    assert repo.create(session, **kwargs, norms_snapshot_id=SNAPSHOT,
                       norm_retrieval_set_id=SET) == kwargs["run_id"]
    assert statements[-1]["norm_retrieval_set_id"] == SET
    assert statements[-1]["norms_snapshot_id"] == SNAPSHOT
    repo.create(session, **kwargs)
    assert statements[-1]["norm_retrieval_set_id"] is None
