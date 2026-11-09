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
  no longer refuse (and, where the harm is a delete, must do it).
"""

from __future__ import annotations

import hashlib
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
