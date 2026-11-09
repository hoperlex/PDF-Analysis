"""`DECISION-MEMORY-01` phase M2: the operator tool ``scripts/recovery/memory_forget.py`` makes the memory forget cases, and every guard bites.

Real PostgreSQL and a real S3-compatible bucket (the lane's), in miniature: a clone of the migrated schema with two projects' cases, each with
content, evidence, a norm reference, a crop and the expert's comment, whose crop Blobs are real objects -- one Blob only project A's cases
reference, one that a case of project B shares with a case of A, one that a case of A shares with a LIVE document's artifact. Each test gets
its own clone and its own bucket.

**What "forgotten" and "kept" mean is measured with the TEST'S OWN queries**, not the tool's: row counts and digests of every memory table,
the objects actually listed in the bucket, the events actually in ``audit_event``.

Shown, for the plan, the apply and the resume:

* the dry run changes nothing -- not one row, not one object -- and its digest is what the apply requires;
* an apply by ``--origin-project`` removes exactly that project's content rows (content, evidence, norm references, crops, the expert's
  comments), leaves the case, its decisions and every other project's content byte for byte, leaves one ``forget`` tombstone per case
  (actor, reason, the owner's permission, the digest of the content that was forgotten), deletes the Blob rows and objects only those cases
  referenced and keeps the shared ones, writes ``memory.forget_requested`` and ``memory.forget_completed`` with identities, counts and digests
  only, and writes the plan and the manifest files whose digests the events carry;
* a crash after the commit leaves the Blobs in ``erasure_pending`` and ``--resume`` completes it; a finished forget is "nothing to do";
* every guard is shown able to fail: ``# >>> guard: <name>`` blocks are deleted one at a time from a COPY of the source, and the copy must
  no longer refuse (and, where the harm is a delete, must do it). The guards that only a fault inside the transaction or a fault in the
  bucket can trigger get the fault injected -- a trigger that skips a row, a trigger that inserts outside the scope, a trigger that
  switches another trigger off, a role that owns nothing, a lock held by another session, a bucket that does not delete -- and the last
  test of the file holds the list of the tool's guards to the list of the scenarios (`D-492`).
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import re
import secrets
import sys
import types
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text

from auditmanager.shared.db.engine import create_database_engine
from auditmanager.storage import S3StorageSettings
from auditmanager.storage.public import canonical_object_key_for_recovery, derive_blob_id
from scripts.recovery import memory_forget as tool
from scripts.recovery import project_erase as erase
from tests.integration.recovery.purge_seed import bucket_profile, digest_of, s3
from tests.integration.recovery.purge_stand import Stand, _empty_and_delete, _line, invoke
from tests.support.memory_seed import seed_case

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "scripts/recovery/memory_forget.py"
ADMIN = "admin"
REFERENCE = "owner message 2026-11-09, forget test"
PROJECT_A = "prj_01ARZ3NDEKTSV4RRFFQ69G5FAA"
PROJECT_B = "prj_01ARZ3NDEKTSV4RRFFQ69G5FAB"
MEMORY_TABLES = (
    "decision_memory_case", "decision_memory_decision", "decision_memory_decision_text", "decision_memory_content",
    "decision_memory_evidence", "decision_memory_norm_ref", "decision_memory_crop", "decision_memory_status_event",
)
CONTENT = ("decision_memory_content", "decision_memory_evidence", "decision_memory_norm_ref", "decision_memory_crop",
           "decision_memory_decision_text")


# --- the stand ----------------------------------------------------------------------------------------------------


def _blob(stand: Stand, body: bytes, role: str = "norm_crop") -> str:
    """A Blob in state ``available`` with its object in the bucket, as the storage layer leaves it."""
    digest = hashlib.sha256(body).hexdigest()
    blob_id = str(derive_blob_id(sha256=digest, size=len(body)))
    with stand.engine.begin() as connection:
        connection.execute(text("INSERT INTO blob (blob_id, state, sha256, size_bytes, media_type) "
                                "VALUES (:b, 'temporary', :h, :n, 'image/png')"), {"b": blob_id, "h": digest, "n": len(body)})
        for state in ("verifying", "available"):
            connection.execute(text("UPDATE blob SET state = :s WHERE blob_id = :b"), {"s": state, "b": blob_id})
    stand.client.put_object(Bucket=stand.bucket, Key=canonical_object_key_for_recovery(blob_id), Body=body, ContentType="image/png",
                            Metadata={"blob-id": blob_id, "blob-role": role, "content-sha256": digest, "content-size": str(len(body))})
    return blob_id


class Memory(types.SimpleNamespace):
    """What the stand holds: the cases and Blobs by name."""


@pytest.fixture
def stand(migrated_database_factory: Callable[[], Any], monkeypatch: pytest.MonkeyPatch) -> Iterator[Stand]:
    settings = migrated_database_factory()
    base = S3StorageSettings.from_env()
    bucket = f"{base.bucket[:36]}-mf-{secrets.token_hex(5)}"
    values = {
        "DATABASE_URL": settings.url.render_as_string(hide_password=False), "S3_ENDPOINT_URL": base.endpoint_url,
        "S3_REGION": base.region, "S3_ACCESS_KEY_ID": base.access_key_id, "S3_SECRET_ACCESS_KEY": base.secret_access_key,
        "S3_BUCKET": bucket,
    }
    client = s3(values)
    client.create_bucket(Bucket=bucket)
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    engine = create_database_engine(settings)
    built = Stand(str(settings.url.database), bucket, settings, engine, values, client, {})
    try:
        yield built
    finally:
        engine.dispose()
        _empty_and_delete(client, bucket)


@pytest.fixture
def memory(stand: Stand) -> Memory:
    """Project A: two cases (one crop only A references, one crop shared with a case of B). Project B: one case with the shared crop.
    A third case of A shares its crop with a LIVE artifact (an input manifest entry stands for a document that still exists)."""
    only_a, shared_ab, with_live = (_blob(stand, f"crop-{name}".encode() * 40) for name in ("only-a", "shared-ab", "live"))
    with stand.engine.begin() as connection:
        a1 = seed_case(connection, project=PROJECT_A, blob=only_a, verdicts=("accept", "reject"))
        a2 = seed_case(connection, project=PROJECT_A, blob=shared_ab)
        a3 = seed_case(connection, project=PROJECT_A, blob=with_live)
        b1 = seed_case(connection, project=PROJECT_B, blob=shared_ab)
        b2 = seed_case(connection, project=PROJECT_B, blob=None)
        connection.execute(text("INSERT INTO project (project_uid, name) VALUES ('prj_01ARZ3NDEKTSV4RRFFQ69G5FAC', 'live')"))
        connection.execute(text("INSERT INTO document (document_uid, project_uid, display_title) "
                                "VALUES ('doc_01ARZ3NDEKTSV4RRFFQ69G5FAC', 'prj_01ARZ3NDEKTSV4RRFFQ69G5FAC', 'live')"))
        connection.execute(text(
            "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, sha256, page_count) "
            "VALUES ('ver_01ARZ3NDEKTSV4RRFFQ69G5FAC', 'doc_01ARZ3NDEKTSV4RRFFQ69G5FAC', 1, 'application/pdf', 1024, :s, 1)"),
            {"s": "c" * 64})
        connection.execute(text(
            "INSERT INTO input_manifest_entry (version_uid, role, blob_id, sha256, size_bytes, media_type) "
            "SELECT 'ver_01ARZ3NDEKTSV4RRFFQ69G5FAC', 'zz_live_crop', blob_id, sha256, size_bytes, media_type FROM blob WHERE blob_id = :b"),
            {"b": with_live})
    return Memory(a1=a1["case_id"], a2=a2["case_id"], a3=a3["case_id"], b1=b1["case_id"], b2=b2["case_id"],
                  only_a=only_a, shared_ab=shared_ab, live=with_live, a_cases=sorted([a1["case_id"], a2["case_id"], a3["case_id"]]))


def count(stand: Stand, table: str, where: str = "true", **parameters: Any) -> int:
    with stand.engine.connect() as connection:
        return int(connection.execute(text(f"SELECT count(*) FROM {table} WHERE {where}"), parameters).scalar_one())


def scalars(stand: Stand, statement: str, **parameters: Any) -> list[Any]:
    with stand.engine.connect() as connection:
        return list(connection.execute(text(statement), parameters).scalars())


def rows(stand: Stand, statement: str, **parameters: Any) -> list[Any]:
    with stand.engine.connect() as connection:
        return [tuple(row) for row in connection.execute(text(statement), parameters)]


def state_of(stand: Stand) -> dict[str, Any]:
    return {"tables": {t: digest_of(stand.engine, t) for t in (*MEMORY_TABLES, "blob", "audit_event", "input_manifest_entry")},
            "bucket": bucket_profile(stand.client, stand.bucket)}


def object_exists(stand: Stand, blob_id: str) -> bool:
    return any(item["Key"] == canonical_object_key_for_recovery(blob_id)
               for page in stand.client.get_paginator("list_objects_v2").paginate(Bucket=stand.bucket) for item in page.get("Contents", []))


def forget_events(stand: Stand) -> list[tuple[str, str, str, dict[str, Any]]]:
    return [(a, b, c, dict(d)) for a, b, c, d in rows(
        stand, "SELECT event_type, aggregate_type, aggregate_id, payload FROM audit_event WHERE event_type LIKE 'memory.%' ORDER BY sequence_no")]


def flags(sha: str | None, dump: Path, **over: str | None) -> list[str]:
    values: dict[str, str | None] = {"--plan-sha256": sha, "--actor": ADMIN, "--reason": "client_request",
                                     "--owner-permission-ref": REFERENCE, "--dump-dir": str(dump)}
    values.update({"--" + key.replace("_", "-"): value for key, value in over.items()})
    argv = ["--apply"]
    for flag, value in values.items():
        if value is not None:
            argv += [flag, value]
    return argv


A_PROJECT = ["--origin-project", PROJECT_A]


def plan_and_apply(module: types.ModuleType, stand: Stand, dump: Path, selector: list[str] = A_PROJECT, **over: str | None) -> tuple[int, str, str]:
    code, out, err = invoke(module, stand, *selector)
    assert code == 0, (out, err)
    return invoke(module, stand, *selector, *flags(_line(out, "plan-sha256"), dump, **over))


# --- the guard-deleting harness (the convention of test_project_erase) ------------------------------------------------

_BLOCK = r"^[ \t]*# >>> guard: {name}\n.*?^[ \t]*# <<< guard: {name}\n"
_MUTANTS = iter(range(10**6))


def mutant(*guards: str) -> types.ModuleType:
    source = SOURCE.read_text(encoding="utf-8")
    for name in guards:
        source, matched = re.subn(_BLOCK.format(name=re.escape(name)), "", source, flags=re.DOTALL | re.MULTILINE)
        assert matched == 1, f"the guard markers for {name!r} are not a single block"
    module = types.ModuleType(f"scripts.recovery.memory_forget_mutant_{next(_MUTANTS)}")
    module.__file__ = str(SOURCE)
    sys.modules[module.__name__] = module
    exec(compile(source, f"<memory_forget without {guards}>", "exec"), module.__dict__)  # noqa: S102
    return module


# --- the plan --------------------------------------------------------------------------------------------------------


def test_the_dry_run_changes_nothing_and_says_what_the_apply_would_do(stand: Stand, memory: Memory) -> None:
    before = state_of(stand)
    code, out, err = invoke(tool, stand, *A_PROJECT)
    assert code == 0 and err == "", (out, err)
    assert state_of(stand) == before, "the dry run changed something"
    assert _line(out, "cases") == "3" and _line(out, "blobs-exclusive") == "1" and _line(out, "blobs-shared") == "2"
    assert re.fullmatch(r"[0-9a-f]{64}", _line(out, "plan-sha256"))
    assert "NOTHING ABOVE WAS CHANGED" in out
    # the same selection gives the same digest; another selection another
    assert _line(invoke(tool, stand, *A_PROJECT)[1], "plan-sha256") == _line(out, "plan-sha256")
    assert _line(invoke(tool, stand, "--case", memory.a1)[1], "plan-sha256") != _line(out, "plan-sha256")
    # the rows to delete are what the test counts itself: per case 1 content, 1 evidence, 1 norm ref, 1 crop and one comment per decision
    assert int(_line(out, "rows-to-delete")) == 3 * 4 + 2 + 1 + 1


# --- the apply ----------------------------------------------------------------------------------------------------------


def test_an_apply_removes_the_content_of_the_projects_cases_and_nothing_else_and_leaves_a_tombstone(
    stand: Stand, memory: Memory, tmp_path: Path
) -> None:
    before = state_of(stand)
    identity_before = {t: digest_of(stand.engine, t) for t in ("decision_memory_case", "decision_memory_decision")}
    b_before = {t: digest_of(stand.engine, t, "case_id = '%s'" % memory.b1) for t in ("decision_memory_content", "decision_memory_crop",
                                                                                      "decision_memory_evidence", "decision_memory_norm_ref")}
    case_digests = dict(rows(stand, "SELECT case_id, content_sha256 FROM decision_memory_case"))
    code, out, err = plan_and_apply(tool, stand, tmp_path)
    assert code == 0, (out, err)
    erase_id = _line(out, "forget-id")
    assert re.fullmatch(r"era_[0-9A-HJKMNP-TV-Z]{26}", erase_id)

    # (1) the content of project A's cases is gone, by the test's own count ...
    for table in CONTENT:
        scope = ("case_id = ANY(:cases)" if table != "decision_memory_decision_text" else
                 "memory_decision_id IN (SELECT memory_decision_id FROM decision_memory_decision WHERE case_id = ANY(:cases))")
        assert count(stand, table, scope, cases=memory.a_cases) == 0, table
    # (2) ... the cases and their decisions are not touched, and project B's content is byte for byte what it was
    assert {t: digest_of(stand.engine, t) for t in identity_before} == identity_before
    assert {t: digest_of(stand.engine, t, "case_id = '%s'" % memory.b1) for t in b_before} == b_before
    assert count(stand, "decision_memory_decision_text", "comment IS NOT NULL") == 2   # B's two cases kept their comments
    # (3) one tombstone per case with who, why, the owner's permission and the digest of what was forgotten
    tombstones = rows(stand, "SELECT case_id, kind, reason_code, owner_permission_ref, forgotten_content_sha256, actor_user_uid "
                             "FROM decision_memory_status_event ORDER BY case_id")
    admin = scalars(stand, "SELECT user_uid FROM app_user WHERE login = 'admin'")[0]
    assert [t[0] for t in tombstones] == memory.a_cases
    assert {(t[1], t[2], t[3], t[5]) for t in tombstones} == {("forget", "client_request", REFERENCE, admin)}
    assert all(t[4] == case_digests[t[0]] for t in tombstones)
    # (4) the Blobs: only A's rows and objects are gone; the shared and the live ones stay with their objects
    assert not object_exists(stand, memory.only_a) and count(stand, "blob", "blob_id = :b", b=memory.only_a) == 0
    for kept in (memory.shared_ab, memory.live):
        assert object_exists(stand, kept) and count(stand, "blob", "blob_id = :b", b=kept) == 1, kept
    assert count(stand, "blob", "state = 'erasure_pending'") == 0
    # (5) the journal: identities, counts and digests -- never content
    requested, completed = [e for e in forget_events(stand) if e[0] == "memory.forget_requested"], \
        [e for e in forget_events(stand) if e[0] == "memory.forget_completed"]
    assert len(requested) == 1 and len(completed) == 1 and requested[0][1:3] == ("DecisionMemoryForget", erase_id)
    request = requested[0][3]
    assert set(request) == {"actor_uid", "reason_code", "owner_permission_ref", "selector", "cases", "cases_sha256", "plan_sha256",
                            "manifest_sha256", "rows_deleted", "blobs_exclusive", "blobs_shared"}
    assert (request["cases"], request["blobs_exclusive"], request["blobs_shared"], request["rows_deleted"]) == (3, 1, 2, 16)
    assert request["selector"] == {"kind": "origin_project", "origin_project_uid": PROJECT_A}
    assert request["cases_sha256"] == hashlib.sha256("\n".join(memory.a_cases).encode()).hexdigest()
    assert set(completed[0][3]) == {"actor_uid", "reason_code", "owner_permission_ref", "plan_sha256", "manifest_sha256", "cases",
                                    "rows_deleted", "blobs_exclusive", "blobs_shared", "objects_deleted", "objects_missing", "outcome"}
    assert (completed[0][3]["objects_deleted"], completed[0][3]["outcome"]) == (1, "completed")
    body = json.dumps(forget_events(stand), default=str)
    assert "the expert wrote this" not in body and "recommendation" not in body       # identities, counts and digests: no content
    # (6) the files, whose digests the events carry
    manifest = (tmp_path / erase_id / "manifest.json").read_bytes()
    assert hashlib.sha256(manifest).hexdigest() == request["manifest_sha256"] == _line(out, "manifest-sha256")
    plan_file = json.loads((tmp_path / erase_id / "plan.json").read_text(encoding="utf-8"))
    assert plan_file["plan_sha256"] == request["plan_sha256"] and plan_file["plan"]["selector"]["origin_project_uid"] == PROJECT_A
    assert [b["blob_id"] for b in json.loads(manifest)["blobs"]] == [memory.only_a]
    # (7) nothing else in the database moved
    after = state_of(stand)
    for table in ("input_manifest_entry",):
        assert after["tables"][table] == before["tables"][table]
    assert set(after["bucket"]) == set(before["bucket"]) - {canonical_object_key_for_recovery(memory.only_a)}
    assert "A forget does not reach" in out and "training" in out


def test_a_finished_forget_run_again_is_nothing_to_do(stand: Stand, memory: Memory, tmp_path: Path) -> None:
    code, out, _ = invoke(tool, stand, *A_PROJECT)
    sha = _line(out, "plan-sha256")
    assert invoke(tool, stand, *A_PROJECT, *flags(sha, tmp_path))[0] == 0
    after = state_of(stand)
    code, again, err = invoke(tool, stand, *A_PROJECT, *flags(sha, tmp_path))
    assert code == 0 and "nothing to do" in again and err == ""
    assert state_of(stand) == after
    # the dry run of a project with nothing left to forget says so too, and has no digest to approve
    code, dry, _ = invoke(tool, stand, *A_PROJECT)
    assert code == 0 and "nothing to do" in dry and _line(dry, "cases") == "0"


def test_one_case_by_identity_and_everything_by_all(stand: Stand, memory: Memory, tmp_path: Path) -> None:
    code, out, err = plan_and_apply(tool, stand, tmp_path / "one", ["--case", memory.b1])
    assert code == 0, (out, err)
    assert count(stand, "decision_memory_content", "case_id = :c", c=memory.b1) == 0
    assert count(stand, "decision_memory_content") == 4                       # the other four cases kept theirs
    assert object_exists(stand, memory.shared_ab)                             # still referenced by a case of A
    code, out, err = plan_and_apply(tool, stand, tmp_path / "all", ["--all"])
    assert code == 0, (out, err)
    assert count(stand, "decision_memory_content") == 0 and count(stand, "decision_memory_status_event") == 5
    assert not object_exists(stand, memory.shared_ab) and object_exists(stand, memory.live)   # the live artifact still holds its crop
    assert count(stand, "decision_memory_case") == 5 and count(stand, "decision_memory_decision") == 6   # the identity side is whole


# --- a crash after the commit, and the resume --------------------------------------------------------------------------


def _crash(module: types.ModuleType, name: str) -> Callable[[], None]:
    real = getattr(module, name)

    def boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(f"simulated crash in {name}")

    setattr(module, name, boom)
    return lambda: setattr(module, name, real)


def test_a_crash_after_the_commit_leaves_pending_blobs_and_resume_finishes_it(stand: Stand, memory: Memory, tmp_path: Path) -> None:
    restore = _crash(tool, "delete_objects")
    try:
        code, out, err = plan_and_apply(tool, stand, tmp_path)
    finally:
        restore()
    assert code == tool.EXIT_FAILED and "the forget is not finished" in err, (out, err)
    erase_id = _line(out, "forget-id")
    assert f"--resume {erase_id}" in err
    # the database part is committed: no content, tombstones, the Blob waits in erasure_pending with its object still there
    assert count(stand, "decision_memory_content", "case_id = ANY(:c)", c=memory.a_cases) == 0
    assert scalars(stand, "SELECT blob_id FROM blob WHERE state = 'erasure_pending'") == [memory.only_a]
    assert object_exists(stand, memory.only_a)
    assert [e[0] for e in forget_events(stand)] == ["memory.forget_requested"]
    # a second forget (or an erase) is refused while one is pending
    code, _, refused = invoke(tool, stand, "--all")
    assert code == tool.EXIT_REFUSED and "erasure_pending" in refused

    resume = ["--resume", erase_id, "--actor", ADMIN, "--owner-permission-ref", REFERENCE, "--dump-dir", str(tmp_path)]
    code, out, err = invoke(tool, stand, *resume)
    assert code == 0, (out, err)
    assert not object_exists(stand, memory.only_a) and count(stand, "blob", "blob_id = :b", b=memory.only_a) == 0
    assert [e[0] for e in forget_events(stand)] == ["memory.forget_requested", "memory.forget_completed"]
    code, again, _ = invoke(tool, stand, *resume)
    assert code == 0 and "already complete" in again


def test_a_resume_rewrites_a_missing_manifest_and_refuses_a_foreign_one(stand: Stand, memory: Memory, tmp_path: Path) -> None:
    restore = _crash(tool, "delete_objects")
    try:
        _, out, _ = plan_and_apply(tool, stand, tmp_path)
    finally:
        restore()
    erase_id = _line(out, "forget-id")
    manifest = tmp_path / erase_id / "manifest.json"
    resume = ["--resume", erase_id, "--actor", ADMIN, "--owner-permission-ref", REFERENCE, "--dump-dir", str(tmp_path)]
    original = manifest.read_bytes()
    manifest.write_bytes(original + b" ")
    code, _, err = invoke(tool, stand, *resume)
    assert code == tool.EXIT_REFUSED and "differs from the manifest" in err
    assert object_exists(stand, memory.only_a)                                # nothing was deleted on a refusal
    manifest.unlink()
    code, out, err = invoke(tool, stand, *resume)
    assert code == 0 and "manifest-rewritten" in out, (out, err)
    assert manifest.read_bytes() == original


# --- the refusals, and every guard shown able to fail ---------------------------------------------------------------------


def refused(code: int, err: str, says: str) -> bool:
    return code == tool.EXIT_REFUSED and says in err


def test_an_apply_without_what_the_owner_requires_is_refused_and_changes_nothing(stand: Stand, memory: Memory, tmp_path: Path) -> None:
    sha = _line(invoke(tool, stand, *A_PROJECT)[1], "plan-sha256")
    before = state_of(stand)
    cases = [
        (flags(sha, tmp_path, owner_permission_ref=None), "--owner-permission-ref is required"),
        (flags(sha, tmp_path, owner_permission_ref="   "), "--owner-permission-ref is required"),
        (flags(sha, tmp_path, owner_permission_ref="x" * 201), "--owner-permission-ref is required"),
        (flags(sha, tmp_path, owner_permission_ref="line one\nline two"), "--owner-permission-ref is required"),
        (flags(sha, tmp_path, reason="because they asked"), "--reason must be one of"),
        (flags(sha, tmp_path, reason=None), "--reason must be one of"),
        (flags(None, tmp_path), "--apply needs --plan-sha256"),
        (flags("A" * 64, tmp_path), "--apply needs --plan-sha256"),
        (flags(sha, tmp_path, dump_dir=None), "--dump-dir is required"),
        (flags(sha, tmp_path, actor="nobody"), "--actor must be the login of an active"),
        (flags("0" * 64, tmp_path), "changed since the plan that was approved"),
    ]
    for argv, says in cases:
        code, out, err = invoke(tool, stand, *A_PROJECT, *argv)
        assert refused(code, err, says), (argv, code, out, err)
        assert state_of(stand) == before, f"{says}: the refusal changed something"


def test_the_selector_is_exactly_one_identity_never_a_name(stand: Stand, memory: Memory) -> None:
    before = state_of(stand)
    for argv, says in [
        ([], "name exactly one of"),
        (["--all", "--origin-project", PROJECT_A], "name exactly one of"),
        (["--case", memory.a1, "--all"], "name exactly one of"),
        (["--case", "Sunshine kindergarten"], "never a description"),
        (["--origin-project", "Sunshine kindergarten"], "never a name"),
        (["--origin-project", "prj_" + "a" * 26], "never a name"),
        (["--case", "dmc_01ARZ3NDEKTSV4RRFFQ69G5FZZ"], "not in this memory"),
    ]:
        code, out, err = invoke(tool, stand, *argv)
        assert refused(code, err, says), (argv, code, out, err)
    assert state_of(stand) == before


def test_a_plan_that_changed_since_it_was_approved_is_refused(stand: Stand, memory: Memory, tmp_path: Path) -> None:
    sha = _line(invoke(tool, stand, *A_PROJECT)[1], "plan-sha256")
    with stand.engine.begin() as connection:
        seed_case(connection, project=PROJECT_A)                              # a new case of the project arrived after the plan was read
    before = state_of(stand)
    code, out, err = invoke(tool, stand, *A_PROJECT, *flags(sha, tmp_path))
    assert refused(code, err, "changed since the plan that was approved"), (out, err)
    assert state_of(stand) == before
    broken = mutant("plan-unchanged")                                          # without the guard the stale plan is applied
    code, out, err = invoke(broken, stand, *A_PROJECT, *flags(sha, tmp_path))
    assert code == 0 and count(stand, "decision_memory_content", "case_id = ANY(:c)", c=memory.a_cases) == 0, (out, err)


def test_the_guard_is_gone_the_copy_no_longer_refuses(stand: Stand, memory: Memory, tmp_path: Path) -> None:
    """Each guard that argument checking or the catalog owns, deleted from a copy: the copy goes on where the real tool stops."""
    sha = _line(invoke(tool, stand, *A_PROJECT)[1], "plan-sha256")
    steps: list[tuple[str, list[str], str]] = [
        ("one-selector", [], "name exactly one of"),
        ("identity-shape", ["--case", "Sunshine kindergarten"], "never a description"),
        ("owner-permission-ref", [*A_PROJECT, *flags(sha, tmp_path, owner_permission_ref=None)], "--owner-permission-ref is required"),
        ("dump-dir-required", [*A_PROJECT, *flags(sha, tmp_path, dump_dir=None)], "--dump-dir is required"),
        ("plan-digest-required", [*A_PROJECT, *flags(None, tmp_path)], "--apply needs --plan-sha256"),
        ("reason-closed-list", [*A_PROJECT, *flags(sha, tmp_path, reason="because")], "--reason must be one of"),
        ("cases-exist", ["--case", "dmc_01ARZ3NDEKTSV4RRFFQ69G5FZZ"], "not in this memory"),
    ]
    for guard, argv, says in steps:
        real_code, _, real_err = invoke(tool, stand, *argv)
        assert refused(real_code, real_err, says), (guard, real_code, real_err)
        _, _, copy_err = invoke(mutant(guard), stand, *argv)
        assert says not in copy_err, f"{guard}: the copy refused the same way, so the guard was never what refused"


def test_the_forget_guard_must_be_installed_and_the_catalog_closed(stand: Stand, memory: Memory, tmp_path: Path) -> None:
    with stand.engine.begin() as connection:
        connection.execute(text("ALTER TABLE decision_memory_crop DISABLE TRIGGER trg_decision_memory_crop_forget_guard"))
    code, out, err = invoke(tool, stand, *A_PROJECT)
    assert refused(code, err, "the forget guard is not installed and enabled on exactly the content tables"), (out, err)
    # without the guard the dry run goes on (and a DELETE would then run unprotected: this is why the guard exists)
    code, out, err = invoke(mutant("forget-guard-installed"), stand, *A_PROJECT)
    assert code == 0, (out, err)


def test_a_pending_erasure_stops_a_second_one_and_the_guard_can_fail(stand: Stand, memory: Memory) -> None:
    orphan = _blob(stand, b"an orphan a crashed erase left behind" * 10)
    with stand.engine.begin() as connection:
        connection.execute(text("UPDATE blob SET state = 'erasure_pending' WHERE blob_id = :b"), {"b": orphan})
    code, out, err = invoke(tool, stand, *A_PROJECT)
    assert refused(code, err, "erasure_pending"), (out, err)
    code, out, err = invoke(mutant("no-pending-erasure"), stand, *A_PROJECT)
    assert code == 0, (out, err)


def test_a_blob_that_is_not_available_cannot_enter_the_erasure(stand: Stand, memory: Memory) -> None:
    unsettled = str(derive_blob_id(sha256="d" * 64, size=64))
    with stand.engine.begin() as connection:                                 # a crop whose Blob never finished uploading
        connection.execute(text("INSERT INTO blob (blob_id, state, sha256, size_bytes, media_type) "
                                "VALUES (:b, 'temporary', :h, 64, 'image/png')"), {"b": unsettled, "h": "d" * 64})
        seed_case(connection, project=PROJECT_A, blob=unsettled)
    code, out, err = invoke(tool, stand, *A_PROJECT)
    assert refused(code, err, "are not 'available'"), (code, out, err)
    code, out, err = invoke(mutant("blobs-available"), stand, *A_PROJECT)
    assert code == 0, (out, err)


def test_a_reference_that_appears_after_the_commit_stops_the_object_deletion_and_the_guard_can_fail(
    stand: Stand, memory: Memory, tmp_path: Path
) -> None:
    """A late binding to a Blob that waits in erasure_pending (an upload that raced the forget): the objects phase must refuse."""
    restore = _crash(tool, "delete_objects")
    try:
        _, out, _ = plan_and_apply(tool, stand, tmp_path)
    finally:
        restore()
    erase_id = _line(out, "forget-id")
    with stand.engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO input_manifest_entry (version_uid, role, blob_id, sha256, size_bytes, media_type) "
            "SELECT 'ver_01ARZ3NDEKTSV4RRFFQ69G5FAC', 'zz_late', blob_id, sha256, size_bytes, media_type FROM blob WHERE blob_id = :b"),
            {"b": memory.only_a})
    resume = ["--resume", erase_id, "--actor", ADMIN, "--owner-permission-ref", REFERENCE, "--dump-dir", str(tmp_path)]
    code, _, err = invoke(tool, stand, *resume)
    assert code == tool.EXIT_FAILED and "references Blob" in err and object_exists(stand, memory.only_a), err
    code, out, err = invoke(mutant("objects-unreferenced", "pending-unreferenced"), stand, *resume)
    assert not object_exists(stand, memory.only_a), (code, out, err)         # without the guards the late-bound object is deleted


def test_every_guard_marker_is_a_balanced_block() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    opened = re.findall(r"# >>> guard: ([a-z0-9-]+)", source)
    closed = re.findall(r"# <<< guard: ([a-z0-9-]+)", source)
    assert opened == closed and len(set(opened)) == len(opened) and len(opened) >= 25
    for name in opened:                                                        # each deletes to a module that still compiles
        mutant(name)


# --- D-492: the guards no scenario above had shown able to fail ----------------------------------------------------------
#
# Each test makes the fault the guard exists for, runs the real tool (which refuses, and leaves the data as it was), then runs a copy
# with that one block deleted (which does not say what the guard says and, where the guard protects data, does the harm).


def install_fault(stand: Stand, name: str, table: str, timing: str, event: str, body: str, when: str = "") -> None:
    """A row trigger on ``table`` that runs ``body``. Its name sorts before ``trg_*``, so a BEFORE trigger answers first."""
    with stand.engine.begin() as connection:
        connection.execute(text(f"CREATE FUNCTION public.{name}_fn() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN {body} END $$"))
        connection.execute(text(f"CREATE TRIGGER {name} {timing} {event} ON public.{table} FOR EACH ROW {when} EXECUTE FUNCTION public.{name}_fn()"))


def apply_args(stand: Stand, tmp_path: Path) -> list[str]:
    sha = _line(invoke(tool, stand, *A_PROJECT)[1], "plan-sha256")
    return [*A_PROJECT, *flags(sha, tmp_path)]


def a_content(stand: Stand, memory: Memory) -> int:
    return count(stand, "decision_memory_content", "case_id = ANY(:c)", c=memory.a_cases)


def forgets(stand: Stand) -> int:
    return count(stand, "decision_memory_status_event", "kind = 'forget'")


def _after(module: types.ModuleType, name: str, action: Callable[[], None]) -> Callable[[], None]:
    """Run ``action`` right after ``module.<name>`` returns: a fault that arrives between two phases."""
    real = getattr(module, name)

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        result = real(*args, **kwargs)
        action()
        return result

    setattr(module, name, wrapped)
    return lambda: setattr(module, name, real)


def pend(stand: Stand, blob_id: str) -> None:
    with stand.engine.begin() as connection:
        connection.execute(text("UPDATE blob SET state = 'erasure_pending' WHERE blob_id = :b"), {"b": blob_id})


def crashed_forget(stand: Stand, tmp_path: Path) -> tuple[str, list[str]]:
    """A forget that committed and whose objects phase crashed: its id and the arguments that resume it."""
    restore = _crash(tool, "delete_objects")
    try:
        _, out, _ = plan_and_apply(tool, stand, tmp_path)
    finally:
        restore()
    erase_id = _line(out, "forget-id")
    return erase_id, ["--resume", erase_id, "--actor", ADMIN, "--owner-permission-ref", REFERENCE, "--dump-dir", str(tmp_path)]


def new_role(stand: Stand) -> str:
    name = f"forget_probe_{secrets.token_hex(4)}"
    with stand.engine.begin() as connection:
        connection.execute(text(f"CREATE ROLE {name} LOGIN PASSWORD 'probe-password'"))
        connection.execute(text(f'GRANT CONNECT ON DATABASE "{stand.database}" TO {name}'))
        connection.execute(text(f"GRANT USAGE ON SCHEMA public TO {name}"))
        connection.execute(text(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {name}"))
    return name


def invoke_bucket(module: types.ModuleType, stand: Stand, bucket: str, *argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stderr(err):
        code = module.run([*argv, "--database", stand.database, "--bucket", bucket], out=out)
    return code, out.getvalue(), err.getvalue()


def test_a_database_at_another_migration_is_refused(stand: Stand, memory: Memory) -> None:
    with stand.engine.begin() as connection:
        connection.execute(text("UPDATE public.alembic_version SET version_num = '0099_a_future_head'"))
    code, out, err = invoke(tool, stand, *A_PROJECT)
    assert refused(code, err, "the tool was written for") and "0099_a_future_head" in err, (code, out, err)
    code, out, err = invoke(mutant("head-is-declared"), stand, *A_PROJECT)
    assert code == 0 and _line(out, "cases") == "3", (code, out, err)         # without the guard it plans against a schema it was not written for


def test_a_blob_column_the_registry_does_not_know_stops_the_forget(stand: Stand, memory: Memory) -> None:
    with stand.engine.begin() as connection:                                   # a new place a Blob can be referenced from, unclassified
        connection.execute(text("ALTER TABLE public.decision_memory_status_event ADD COLUMN stray_blob_id text"))
    code, out, err = invoke(tool, stand, *A_PROJECT)
    assert refused(code, err, "differ from the registry") and "stray_blob_id" in err, (code, out, err)
    code, out, err = invoke(mutant("blob-columns-closed"), stand, *A_PROJECT)
    assert code == 0, (code, out, err)                                         # without it a Blob a new column holds could be deleted


def test_a_role_that_does_not_own_the_tables_cannot_forget(stand: Stand, memory: Memory, monkeypatch: pytest.MonkeyPatch) -> None:
    role = new_role(stand)
    try:
        monkeypatch.setenv("DATABASE_URL", stand.settings.url.set(username=role, password="probe-password").render_as_string(hide_password=False))
        code, out, err = invoke(tool, stand, *A_PROJECT)
        assert refused(code, err, "does not own") and role in err, (code, out, err)
        code, out, err = invoke(mutant("owner-may-write"), stand, *A_PROJECT)
        assert code == 0, (code, out, err)                                     # the dry run only reads; the apply would meet the grants instead
    finally:
        with stand.engine.begin() as connection:
            connection.execute(text(f"DROP OWNED BY {role}"))
            connection.execute(text(f"DROP ROLE {role}"))


def test_the_typed_database_and_bucket_must_be_the_connected_ones(stand: Stand, memory: Memory) -> None:
    other = f"{stand.bucket}-x"                                                # a real bucket on the same endpoint that is not the configured one
    stand.client.create_bucket(Bucket=other)
    try:
        code, out, err = invoke(tool, stand, *A_PROJECT, database="not_this_database")
        assert refused(code, err, "typed names are not the connected ones") and "not_this_database" in err, (code, out, err)
        code, out, err = invoke_bucket(tool, stand, other, *A_PROJECT)
        assert refused(code, err, "typed names are not the connected ones") and other in err, (code, out, err)
        code, out, err = invoke(mutant("names-match"), stand, *A_PROJECT, database="not_this_database")
        assert code == 0 and _line(out, "cases") == "3", (code, out, err)
        code, out, err = invoke_bucket(mutant("names-match"), stand, other, *A_PROJECT)
        assert code == 0 and f"bucket {other}" in out, (code, out, err)       # without the guard the objects phase would work on the OTHER bucket
    finally:
        _empty_and_delete(stand.client, other)


def test_a_libpq_variable_that_could_redirect_the_connection_is_refused(stand: Stand, memory: Memory, monkeypatch: pytest.MonkeyPatch) -> None:
    """``PGCONNECT_TIMEOUT`` redirects nothing, so the copy without the guard can be run without harm."""
    monkeypatch.setenv("PGCONNECT_TIMEOUT", "5")
    code, out, err = invoke(tool, stand, *A_PROJECT)
    assert refused(code, err, "can redirect the connection") and "PGCONNECT_TIMEOUT" in err, (code, out, err)
    assert invoke(mutant("no-ambient-libpq"), stand, *A_PROJECT)[0] == 0


def test_another_forget_holding_the_lock_stops_this_one(stand: Stand, memory: Memory, tmp_path: Path) -> None:
    argv = apply_args(stand, tmp_path)
    holder = stand.engine.connect()
    try:
        holder.execute(text("SELECT pg_advisory_lock(hashtextextended(:name, 0))"), {"name": tool.ADVISORY_LOCK_NAME})
        holder.commit()                                                        # a session lock outlives the transaction: the other forget
        before = state_of(stand)
        code, out, err = invoke(tool, stand, *argv)
        assert refused(code, err, "another forget holds the lock"), (code, out, err)
        assert state_of(stand) == before and a_content(stand, memory) == 3
        code, out, err = invoke(mutant("forget-lock-free"), stand, *argv)
        assert code == 0 and a_content(stand, memory) == 0, (code, out, err)  # without the guard two forgets run side by side
    finally:
        holder.execute(text("SELECT pg_advisory_unlock_all()"))
        holder.close()


def test_a_writer_that_does_not_let_go_is_a_refusal_with_words_not_a_database_error(
    stand: Stand, memory: Memory, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    argv = apply_args(stand, tmp_path)
    monkeypatch.setattr(tool, "LOCK_TIMEOUT", "1s")
    monkeypatch.setenv("MEMORY_FORGET_LOCK_TIMEOUT", "1s")                      # read by the copy when it is built
    copy = mutant("lock-available")
    writer = stand.engine.connect()
    try:
        writer.execute(text("LOCK TABLE public.decision_memory_decision IN ROW EXCLUSIVE MODE"))   # what a capture in flight holds
        code, out, err = invoke(tool, stand, *argv)
        assert refused(code, err, "could not lock the tables within 1s"), (code, out, err)
        code, out, err = invoke(copy, stand, *argv)
        assert code == tool.EXIT_FAILED and "could not lock the tables" not in err and "lock timeout" in err, (code, out, err)
    finally:
        writer.rollback()
        writer.close()
    assert a_content(stand, memory) == 3


def fill_the_lock_table(stand: Stand, leave: int) -> Callable[[], None]:
    """Take session-level advisory locks (one lock-table slot each) until the server has none left, then give back ``leave`` of them.

    The lock table is server-wide, so this is what a forget of a great many cases runs into, made small: ``D-497`` item 6. The
    locks belong to a session of their own and outlive its transactions; the returned function lets them go."""
    holder = stand.engine.connect().execution_options(isolation_level="AUTOCOMMIT")

    def release() -> None:
        holder.execute(text("SELECT pg_advisory_unlock_all()"))
        holder.close()

    try:
        try:
            holder.execute(text("SELECT count(pg_advisory_lock(g)) FROM generate_series(1, 400000) g"))
        except Exception as error:  # noqa: BLE001
            assert getattr(getattr(error, "orig", None), "sqlstate", "") == "53200", error
        else:
            pytest.fail("the lock table did not fill: this server's lock table is larger than the test can fill")
        held = int(holder.execute(text("SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND pid = pg_backend_pid()")).scalar_one())
        assert held > leave, held
        holder.execute(text("SELECT count(pg_advisory_unlock(g)) FROM generate_series(CAST(:first AS bigint), CAST(:last AS bigint)) g"),
                       {"first": held - leave + 1, "last": held})
    except BaseException:
        release()          # a table left full would fail every test after this one for a reason that is not theirs
        raise
    return release


def test_a_selection_too_large_for_the_servers_lock_table_is_a_refusal_with_numbers_and_changes_nothing(
    stand: Stand, tmp_path: Path
) -> None:
    """``D-497`` item 6. A forget holds one advisory lock per case until it commits (the status guard takes it on the INSERT, so it cannot be
    skipped), and the lock table is shared by the whole server. Here the table is filled by another session until 250 slots are left and 500
    cases are asked for: the tool must say so in words, with the numbers, change nothing, and go through once the slots are back."""
    with stand.engine.begin() as connection:
        for _ in range(500):
            seed_case(connection, project=PROJECT_A)
    code, out, err = invoke(tool, stand, "--all")
    assert code == 0 and _line(out, "cases") == "500", (out, err)
    argv = ["--all", *flags(_line(out, "plan-sha256"), tmp_path)]
    before = state_of(stand)
    release = fill_the_lock_table(stand, leave=250)
    try:
        code, out, err = invoke(tool, stand, *argv)
        assert refused(code, err, "the server's lock table ran out"), (code, out, err)
        assert "500 cases need one advisory lock each" in err and "max_locks_per_transaction" in err and "Nothing was changed" in err
        assert "out of shared memory" not in err, "the operator reads words, not the database's error"
        taken = int(re.search(r"ran out after (\d+)", err).group(1))  # type: ignore[union-attr]
        assert 0 < taken < 500 and f"at most {taken // 2} cases" in err, err
        code, out, err = invoke(mutant("lock-table-room"), stand, *argv)
        assert code == tool.EXIT_FAILED and "out of shared memory" in err, (code, out, err)   # without the guard: the raw database error
    finally:
        release()
    assert state_of(stand) == before, "the refusal rolled everything back"
    code, out, err = invoke(tool, stand, *argv)                                  # the same plan, once the slots are back: it was the lock table
    assert code == 0, (code, out, err)
    assert forgets(stand) == 500 and count(stand, "decision_memory_content") == 0


def test_a_blob_that_would_not_move_to_erasure_pending_rolls_the_forget_back(stand: Stand, memory: Memory, tmp_path: Path) -> None:
    argv = apply_args(stand, tmp_path)
    install_fault(stand, "aa_fault_skip_pending", "blob", "BEFORE", "UPDATE", "RETURN NULL;", "WHEN (NEW.state = 'erasure_pending')")
    code, out, err = invoke(tool, stand, *argv)
    assert refused(code, err, "exclusive Blob(s) moved to erasure_pending; rolled back"), (code, out, err)
    assert a_content(stand, memory) == 3 and forgets(stand) == 0               # all of it rolled back
    code, out, err = invoke(mutant("blobs-pending"), stand, *argv)
    assert "moved to erasure_pending" not in err and a_content(stand, memory) == 0 and forgets(stand) == 3, (code, out, err)   # it committed


def test_a_delete_that_reaches_outside_the_chosen_cases_rolls_the_forget_back(stand: Stand, memory: Memory, tmp_path: Path) -> None:
    argv = apply_args(stand, tmp_path)
    install_fault(stand, "zz_fault_outside", "decision_memory_crop", "AFTER", "DELETE",
                  "INSERT INTO public.decision_memory_evidence (case_id, revision, ordinal, page_number, quote, char_start, char_end) "
                  f"VALUES ('{memory.b2}', 1, 5, 1, 'quote', 0, 5) ON CONFLICT DO NOTHING; RETURN NULL;")   # a row appears in a case that is not forgotten
    code, out, err = invoke(tool, stand, *argv)
    assert refused(code, err, "changed data outside the chosen cases") and "decision_memory_evidence:outside" in err, (code, out, err)
    assert a_content(stand, memory) == 3 and count(stand, "decision_memory_evidence", "case_id = :c", c=memory.b2) == 1
    code, out, err = invoke(mutant("keep-unchanged"), stand, *argv)
    assert "changed data outside" not in err and a_content(stand, memory) == 0, (code, out, err)
    assert count(stand, "decision_memory_evidence", "case_id = :c", c=memory.b2) == 2      # the stray row stayed in another project's case


def test_content_that_a_delete_did_not_remove_is_not_forgotten_by_the_tombstone(stand: Stand, memory: Memory, tmp_path: Path) -> None:
    argv = apply_args(stand, tmp_path)
    comments = "memory_decision_id IN (SELECT memory_decision_id FROM decision_memory_decision WHERE case_id = ANY(:c))"
    install_fault(stand, "aa_fault_skip_comment", "decision_memory_decision_text", "BEFORE", "DELETE", "RETURN NULL;")   # a leaf: nothing refuses first
    code, out, err = invoke(tool, stand, *argv)
    assert refused(code, err, "content of the chosen cases remains"), (code, out, err)
    assert a_content(stand, memory) == 3 and forgets(stand) == 0
    code, out, err = invoke(mutant("content-emptied"), stand, *argv)
    assert "content of the chosen cases remains" not in err and forgets(stand) == 3, (code, out, err)
    assert a_content(stand, memory) == 0
    assert count(stand, "decision_memory_decision_text", comments, c=memory.a_cases) == 4     # tombstoned, and the expert's words are still there


def test_a_trigger_the_forget_left_switched_off_rolls_it_back(stand: Stand, memory: Memory, tmp_path: Path) -> None:
    argv = apply_args(stand, tmp_path)
    guard = "trg_decision_memory_setting_event_immutable"
    install_fault(stand, "zz_fault_trigger_off", "decision_memory_crop", "AFTER", "DELETE",
                  f"ALTER TABLE public.decision_memory_setting_event DISABLE TRIGGER {guard}; RETURN NULL;")

    def state() -> str:
        return scalars(stand, "SELECT tgenabled::text FROM pg_trigger WHERE tgname = :n", n=guard)[0]

    code, out, err = invoke(tool, stand, *argv)
    assert refused(code, err, "a trigger's state differs after the forget; rolled back"), (code, out, err)
    assert state() == "O" and a_content(stand, memory) == 3
    code, out, err = invoke(mutant("triggers-restored"), stand, *argv)
    assert "a trigger's state differs" not in err and forgets(stand) == 3, (code, out, err)
    assert state() == "D"                                                      # a guard of the schema stayed off after the "forget"


def test_an_object_list_with_a_key_the_tool_cannot_derive_deletes_nothing(stand: Stand, memory: Memory) -> None:
    victim = "somebody-elses/keep-me.bin"
    stand.client.put_object(Bucket=stand.bucket, Key=victim, Body=b"not a Blob of this memory")
    blob = str(derive_blob_id(sha256="e" * 64, size=7))
    listed = [erase.PlanObject(victim, "canonical", blob, None)]               # a key that is not the canonical key of the Blob it names

    def exists() -> bool:
        return any(i["Key"] == victim for p in stand.client.get_paginator("list_objects_v2").paginate(Bucket=stand.bucket)
                   for i in p.get("Contents", []))

    with pytest.raises(tool.ForgetRefused, match="is not exactly the key"):
        tool.delete_objects(stand.engine, stand.client, bucket=stand.bucket, objects=listed, blob_ids=[blob])
    assert exists()
    result = mutant("object-key-shape").delete_objects(stand.engine, stand.client, bucket=stand.bucket, objects=listed, blob_ids=[blob])
    assert result["deleted"] == 1 and not exists()                             # without the guard a list can name any key


class _KeepsEverything:
    """A bucket that answers every delete with success and keeps the object."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def delete_object(self, **kwargs: Any) -> dict[str, Any]:
        return {}

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)


def test_an_object_that_is_still_there_after_its_delete_is_not_counted_as_deleted(stand: Stand, memory: Memory) -> None:
    blob = _blob(stand, b"a crop the bucket will not let go" * 10)
    listed = [erase.PlanObject(tool.purge.canonical_key(blob), "canonical", blob, None)]
    keeper = _KeepsEverything(stand.client)
    with pytest.raises(tool.ForgetFailed, match="is still in the bucket after its delete"):
        tool.delete_objects(stand.engine, keeper, bucket=stand.bucket, objects=listed, blob_ids=[blob])
    result = mutant("objects-gone").delete_objects(stand.engine, keeper, bucket=stand.bucket, objects=listed, blob_ids=[blob])
    assert result["deleted"] == 1 and object_exists(stand, blob)               # without the check the summary says deleted of an object that is there


@pytest.mark.parametrize("without", [False, True], ids=["tool", "guard-deleted"])
def test_pending_blobs_that_are_not_the_manifest_are_not_deleted_at_the_finish(
    stand: Stand, memory: Memory, tmp_path: Path, without: bool
) -> None:
    module = mutant("finish-matches-manifest") if without else tool
    orphan = _blob(stand, b"a Blob another erasure left pending" * 10)
    restore = _after(module, "delete_objects", lambda: pend(stand, orphan))    # it arrives between the objects phase and the finish
    try:
        code, out, err = plan_and_apply(module, stand, tmp_path)
    finally:
        restore()
    says = "are not the manifest of era_"
    assert code == tool.EXIT_FAILED, (code, out, err)
    if not without:
        assert says in err and [e[0] for e in forget_events(stand)] == ["memory.forget_requested"], err
    else:
        assert says not in err, err                                            # the copy goes on to the next net (pending-cleared)
        assert "still pending; rolled back" in err and [e[0] for e in forget_events(stand)] == ["memory.forget_requested"]


@pytest.mark.parametrize("without", [False, True], ids=["tool", "guard-deleted"])
def test_a_finish_that_could_not_delete_the_blob_rows_does_not_write_forget_completed(
    stand: Stand, memory: Memory, tmp_path: Path, without: bool
) -> None:
    install_fault(stand, "aa_fault_keep_blob_row", "blob", "BEFORE", "DELETE", "RETURN NULL;", "WHEN (OLD.state = 'erasure_pending')")
    module = mutant("pending-cleared") if without else tool
    code, out, err = plan_and_apply(module, stand, tmp_path)
    events = [e[0] for e in forget_events(stand)]
    if not without:
        assert code == tool.EXIT_FAILED and "0 of 1 Blob row(s) deleted, 1 still pending; rolled back" in err, (code, out, err)
        assert events == ["memory.forget_requested"]
    else:
        assert code == 0 and events == ["memory.forget_requested", "memory.forget_completed"], (code, out, err)
        assert scalars(stand, "SELECT blob_id FROM blob WHERE state = 'erasure_pending'") == [memory.only_a]   # "completed", and the row is there


@pytest.mark.parametrize("without", [False, True], ids=["tool", "guard-deleted"])
def test_a_reference_that_arrives_before_the_finish_stops_the_blob_rows_going(
    stand: Stand, memory: Memory, tmp_path: Path, without: bool
) -> None:
    module = mutant("pending-unreferenced") if without else tool

    def late_reference() -> None:
        with stand.engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO input_manifest_entry (version_uid, role, blob_id, sha256, size_bytes, media_type) "
                "SELECT 'ver_01ARZ3NDEKTSV4RRFFQ69G5FAC', 'zz_late', blob_id, sha256, size_bytes, media_type FROM blob WHERE blob_id = :b"),
                {"b": memory.only_a})

    restore = _after(module, "delete_objects", late_reference)
    try:
        code, out, err = plan_and_apply(module, stand, tmp_path)
    finally:
        restore()
    assert code == tool.EXIT_FAILED, (code, out, err)
    assert [e[0] for e in forget_events(stand)] == ["memory.forget_requested"]
    assert ("referenced again" in err) is (not without), err                   # the copy is stopped by the foreign key instead, in other words


def test_the_guard_that_stops_the_object_deletion_is_not_the_only_net(stand: Stand, memory: Memory, tmp_path: Path) -> None:
    """`objects-unreferenced` alone: the object of a late-bound Blob is deleted, and the finish still refuses (`pending-unreferenced`)."""
    erase_id, resume = crashed_forget(stand, tmp_path)
    with stand.engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO input_manifest_entry (version_uid, role, blob_id, sha256, size_bytes, media_type) "
            "SELECT 'ver_01ARZ3NDEKTSV4RRFFQ69G5FAC', 'zz_late', blob_id, sha256, size_bytes, media_type FROM blob WHERE blob_id = :b"),
            {"b": memory.only_a})
    code, out, err = invoke(mutant("objects-unreferenced"), stand, *resume)
    assert not object_exists(stand, memory.only_a), (code, out, err)           # the first net is gone: the object a row references was deleted
    assert code == tool.EXIT_FAILED and "referenced again" in err              # the second net held: no completion, the Blob row stays
    assert [e[0] for e in forget_events(stand)] == ["memory.forget_requested"] and erase_id in err


def test_resuming_a_forget_the_database_does_not_know_is_refused(stand: Stand, memory: Memory, tmp_path: Path) -> None:
    unknown = "era_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    resume = ["--resume", unknown, "--actor", ADMIN, "--owner-permission-ref", REFERENCE, "--dump-dir", str(tmp_path)]
    code, out, err = invoke(tool, stand, *resume)
    assert refused(code, err, "has no memory.forget_requested event"), (code, out, err)
    code, out, err = invoke(mutant("forget-id-known"), stand, *resume)
    assert "has no memory.forget_requested event" not in err and code != 0, (code, out, err)     # an IndexError, not a refusal


def test_a_resume_argument_that_is_not_an_identity_is_refused_before_the_database(stand: Stand, memory: Memory, tmp_path: Path) -> None:
    resume = ["--resume", "not-an-identity", "--actor", ADMIN, "--owner-permission-ref", REFERENCE, "--dump-dir", str(tmp_path)]
    code, out, err = invoke(tool, stand, *resume)
    assert refused(code, err, "--resume must be a forget identity"), (code, out, err)
    code, out, err = invoke(mutant("resume-id-shape"), stand, *resume)
    assert "--resume must be a forget identity" not in err and "not-an-identity has no memory.forget_requested" in err, (code, out, err)


def test_pending_blobs_that_are_not_the_ones_the_forget_committed_stop_the_resume(stand: Stand, memory: Memory, tmp_path: Path) -> None:
    _, resume = crashed_forget(stand, tmp_path)
    orphan = _blob(stand, b"a Blob another erasure left pending" * 10)
    pend(stand, orphan)
    code, out, err = invoke(tool, stand, *resume)
    assert refused(code, err, "are not the manifest"), (code, out, err)
    assert object_exists(stand, memory.only_a)
    code, out, err = invoke(mutant("resume-manifest-matches"), stand, *resume)
    assert "are not the manifest" not in err and "differs from the manifest" in err, (code, out, err)   # the file on disk is the next net
    assert object_exists(stand, memory.only_a)


def test_a_manifest_file_that_was_changed_stops_the_resume_and_the_guard_can_fail(stand: Stand, memory: Memory, tmp_path: Path) -> None:
    erase_id, resume = crashed_forget(stand, tmp_path)
    manifest = tmp_path / erase_id / "manifest.json"
    original = manifest.read_bytes()
    manifest.write_bytes(original + b" ")
    code, out, err = invoke(tool, stand, *resume)
    assert refused(code, err, "differs from the manifest") and object_exists(stand, memory.only_a), (code, out, err)
    code, out, err = invoke(mutant("resume-manifest-file-matches"), stand, *resume)
    assert code == 0 and not object_exists(stand, memory.only_a), (code, out, err)     # finished against a record that no longer matches
    assert manifest.read_bytes() == original + b" "


GUARDS_WITH_A_SCENARIO = (
    # arguments and the selector
    "one-selector", "identity-shape", "resume-id-shape", "owner-permission-ref", "dump-dir-required", "plan-digest-required",
    "reason-closed-list", "cases-exist", "names-match", "no-ambient-libpq",
    # the catalog and the plan
    "head-is-declared", "forget-guard-installed", "blob-columns-closed", "owner-may-write", "no-pending-erasure", "blobs-available",
    # the transaction
    "forget-lock-free", "lock-available", "lock-table-room", "plan-unchanged", "blobs-pending", "keep-unchanged", "content-emptied",
    "triggers-restored",
    # the objects and the finish
    "object-key-shape", "objects-unreferenced", "objects-gone", "finish-matches-manifest", "pending-unreferenced", "pending-cleared",
    # the resume
    "forget-id-known", "resume-manifest-matches", "resume-manifest-file-matches",
)


def test_every_guard_of_the_tool_has_a_scenario_above() -> None:
    """A guard added to the tool without a test that deletes it fails here, which is the reminder to write one (`D-492`)."""
    source = SOURCE.read_text(encoding="utf-8")
    opened = re.findall(r"^[ \t]*# >>> guard: ([a-z0-9-]+)$", source, flags=re.MULTILINE)
    closed = re.findall(r"^[ \t]*# <<< guard: ([a-z0-9-]+)$", source, flags=re.MULTILINE)
    assert opened == closed and len(opened) == 33
    assert sorted(opened) == sorted(GUARDS_WITH_A_SCENARIO)
