"""`D-511` -- every refusal `infra/deploy/memory-forget.sh` makes, and every one shown able to fail.

The convention is `test_erase_project_script.py`'s (`R-4`: a guard on a destructive operator tool that has never been shown to fail is the most
expensive kind of green):

1. an invocation that should trip a guard exits **3**, says why, and -- for the guards that run before any connection -- makes **no `docker`
   call at all**;
2. the same invocation against a **copy of the script with exactly that guard block deleted** no longer produces that refusal. Where the guard
   sits after a connection the copy is also shown to reach the next destructive step (the `--apply` call), which is the harm;
3. a behaviour that is not a guard (the owner's url, the operator's uid, the five mounts, stdin, the resume command, the services that stop and
   come back, the absence of any dump) is pinned by a test **and** by a text mutation of the script that turns it red.

Nothing here touches a stand: `docker` is a stub on `PATH` (`tests/support/wrapper_rig.py`). The module behind it -- the plan, the transaction,
the objects -- is `tests/integration/recovery/test_memory_forget.py`; the meeting of the two, with the real module behind a `docker` shim, is
`tests/integration/recovery/test_memory_ops_wrappers.py`. This file drives the wrapper's ORDER, ARGUMENTS and EXIT CODES.
"""

from __future__ import annotations

import hashlib
import os
import re
import shlex
import stat
from pathlib import Path

import pytest

from auditmanager.decision_memory.public import STATUS_REASON_CODES
from tests.support.wrapper_rig import ROOT, Rig, Wrapper, env_without, guard_names, modules_imported_by

SCRIPT = ROOT / "infra/deploy/memory-forget.sh"
MODULE_DIR = ROOT / "scripts/recovery"
MODULES = ("memory_forget", "project_erase", "product_purge", "schema_coverage", "blob_reference_audit")

INSTANCE, DATABASE, BUCKET, USER = "an-instance", "the_configured_database", "the-configured-bucket", "the_user"
REFUSED, FAILED, USAGE = 3, 4, 2
PROJECT = "prj_" + "0" * 26
OTHER_PROJECT = "prj_" + "1" * 26
CASE_A = "dmc_" + "1" * 26
CASE_B = "dmc_" + "2" * 26
FORGET = "era_" + "3" * 26
SHA = "a" * 64
OTHER_SHA = "b" * 64
ACTOR = "an.administrator@example.org"
REF = "owner mail of 2026-11-09, kept in the release record"
MANIFEST_TEXT = '{"blobs":[],"forget_id":"' + FORGET + '","version":1}\n'
MANIFEST_SHA = hashlib.sha256(MANIFEST_TEXT.encode()).hexdigest()

#: The application role's url (`DATABASE_URL`) and the owner's (`MIGRATOR_DATABASE_URL`) are DIFFERENT strings, so a test can tell which one the
#: wrapper hands the one-off container (`PROD-04-DB-ROLES-01`).
APP_URL = f"postgresql+psycopg://the_application_role:an-application-db-password-0001@postgres:5432/{DATABASE}"
MIGRATOR_URL = f"postgresql+psycopg://{USER}:an-owner-db-password-0002@postgres:5432/{DATABASE}"
ENV_TEXT = (f"ALPHA_INSTANCE={INSTANCE}\nPOSTGRES_DB={DATABASE}\nPOSTGRES_USER={USER}\nS3_BUCKET={BUCKET}\n"
            f"DATABASE_URL={APP_URL}\nMIGRATOR_DATABASE_URL={MIGRATOR_URL}\n")
WRAPPER = Wrapper(script=SCRIPT, tool="scripts.recovery.memory_forget", flavour="forget", env_text=ENV_TEXT,
                  module_env="ALPHA_MEMORY_MODULE_DIR")

COMMON = ("--database", DATABASE, "--bucket", BUCKET)
ORIGIN = ("--origin-project", PROJECT)
PLAN = (*COMMON, *ORIGIN)
CASES_COUNT = "3"
TYPED = f"{CASES_COUNT}\n{SHA}\n"


def apply_args(*, selector: tuple[str, ...] = ORIGIN, actor: str | None = ACTOR, reason: str | None = "client_request",
               ref: str | None = REF, sha: str | None = SHA) -> tuple[str, ...]:
    """An apply; a value of None leaves that option out."""
    options: list[str] = [*COMMON, *selector, "--apply"]
    for flag, value in (("--actor", actor), ("--reason", reason), ("--owner-permission-ref", ref), ("--plan-sha256", sha)):
        if value is not None:
            options += [flag, value]
    return tuple(options)


APPLY = apply_args()
RESUME = (*COMMON, "--resume", FORGET, "--actor", ACTOR, "--owner-permission-ref", REF)


def plan_text(*, sha: str = SHA, cases: int = 3) -> str:
    return (f"memory-forget: database {DATABASE} (migration head 0061_decision_memory_m2), bucket {BUCKET}\n"
            f'selector: {{"kind":"origin_project","origin_project_uid":"{PROJECT}"}}\n\n'
            f"-- cases to forget: {cases} (already forgotten and skipped: 0) --\n\n"
            f"cases: {cases}\nblobs-exclusive: 1\nblobs-shared: 2\nrows-to-delete: 16\nplan-sha256: {sha}")


def done_text(*, manifest_sha: str = MANIFEST_SHA, forget: str = FORGET) -> str:
    return (f"forget-id: {forget}\nobjects-deleted: 1\nobjects-missing: 0\n"
            f"memory-forget: 3 case(s) forgotten as {forget}.\nmanifest-sha256: {manifest_sha}\n"
            f"manifest: /dump/{forget}/manifest.json\nplan-sha256: {SHA}\nrows-deleted: 16\n\n"
            "Keep the plan and the manifest with the release record: the database holds only their digests.\n"
            "A forget does not reach:\n  - exports already produced and anything trained on them\n")


NOTHING = "memory-forget: no case of that selection is left to forget; nothing to do.\n"


def healthy() -> dict[str, object]:
    written = {"id": FORGET, "text": MANIFEST_TEXT}
    return {
        "plan": {"stdout": plan_text()},
        "apply": {"stdout": done_text(), "write_manifest": written},
        "resume": {"stdout": done_text(), "write_manifest": written},
        "running": ["postgres", "s3", "api", "worker", "web"],
    }


@pytest.fixture()
def rig(tmp_path: Path) -> Rig:
    built = Rig(tmp_path, WRAPPER)
    built.answers = healthy()
    return built


def tool_reached_the_write(rig_: Rig) -> bool:
    return any("--apply" in rig_.tool_args(call) or "--resume" in rig_.tool_args(call) for call in rig_.tool_calls())


# --- the guards that run before any connection ------------------------------------------------

#: (guard, arguments, the refusal's words, whether the copy without the guard goes on to the docker stub)
CASES: tuple[tuple[str, tuple[str, ...], str, bool], ...] = (
    ("known-options", (*PLAN, "--dryrun"), "unrecognised option: --dryrun", False),
    ("known-options", (*COMMON, "--origin-project"), "--origin-project needs a value", False),
    ("known-options", (*COMMON, "--all", "--reason"), "--reason needs a value", False),
    ("one-mode", (*APPLY, "--dry-run"), "were more than one", True),
    ("one-mode", (*RESUME, "--apply"), "were more than one", True),
    ("stop-services-needs-a-write-mode", (*PLAN, "--stop-services"), "--stop-services belongs to --apply or --resume", True),
    ("options-match-the-mode", (*PLAN, "--reason", "test_data"), "belong to --apply (or --resume), and no --apply", True),
    ("options-match-the-mode", (*PLAN, "--plan-sha256", SHA), "belong to --apply (or --resume), and no --apply", True),
    ("options-match-the-mode", (*PLAN, "--actor", ACTOR, "--owner-permission-ref", REF),
     "belong to --apply (or --resume), and no --apply", True),
    ("options-match-the-mode", (*RESUME, "--plan-sha256", SHA), "belong to --apply; a --resume finishes", True),
    ("options-match-the-mode", (*RESUME, "--reason", "test_data"), "belong to --apply; a --resume finishes", True),
    ("names-required", ("--origin-project", PROJECT), "--database and --bucket are both required", False),
    ("names-required", ("--database", DATABASE, "--all"), "--database and --bucket are both required", False),
    # which cases is the whole question: no selector must never mean "all of them"
    ("one-selector", COMMON, "name exactly one of --case", True),
    ("one-selector", (*COMMON, "--all", *ORIGIN), "name exactly one of --case", True),
    ("one-selector", (*COMMON, "--case", CASE_A, "--all"), "name exactly one of --case", True),
    ("one-selector", (*COMMON, "--case", CASE_A, *ORIGIN), "name exactly one of --case", True),
    ("one-selector", (*RESUME, "--all"), "do not go with --resume", True),
    ("one-selector", (*RESUME, "--case", CASE_A), "do not go with --resume", True),
    ("one-selector", (*RESUME, *ORIGIN), "do not go with --resume", True),
    ("selector-identity-shape", (*COMMON, "--case", "Kindergarten Sunshine"), "never a description", True),
    ("selector-identity-shape", (*COMMON, "--case", "dmc_" + "a" * 26), "never a description", True),
    ("selector-identity-shape", (*COMMON, "--case", CASE_A, "--case", "dmc_short"), "never a description", True),
    ("selector-identity-shape", (*COMMON, "--origin-project", "Kindergarten Sunshine"), "never a name", True),
    ("selector-identity-shape", (*COMMON, "--origin-project", "prj_" + "a" * 26), "never a name", True),
    ("forget-identity-shape", (*COMMON, "--resume", "era_nope", "--actor", ACTOR, "--owner-permission-ref", REF),
     "--resume must be a forget identity", True),
    ("forget-identity-shape", (*COMMON, "--resume", PROJECT, "--actor", ACTOR, "--owner-permission-ref", REF),
     "--resume must be a forget identity", True),
    ("actor-required", apply_args(actor=None), "--actor must be the login", True),
    ("actor-required", apply_args(actor=""), "--actor must be the login", True),
    ("actor-required", apply_args(actor="two words"), "--actor must be the login", True),
    ("actor-required", apply_args(actor="-x"), "--actor must be the login", True),
    ("actor-required", (*COMMON, "--resume", FORGET, "--actor", "", "--owner-permission-ref", REF), "--actor must be the login", True),
    ("reason-closed-list", apply_args(reason="because they asked"), "--reason must be one of", True),
    ("reason-closed-list", apply_args(reason=None), "--reason must be one of", True),
    ("reason-closed-list", apply_args(reason="erasure"), "--reason must be one of", True),
    ("owner-permission-ref", apply_args(ref=None), "--owner-permission-ref is required", True),
    ("owner-permission-ref", apply_args(ref="   "), "--owner-permission-ref is required", True),
    ("owner-permission-ref", apply_args(ref="x" * 201), "--owner-permission-ref is required", True),
    ("owner-permission-ref", apply_args(ref="line one\nline two"), "--owner-permission-ref is required", True),
    ("owner-permission-ref", (*COMMON, "--resume", FORGET, "--actor", ACTOR), "--owner-permission-ref is required", True),
    ("plan-digest-shape", apply_args(sha=None), "--apply needs --plan-sha256", True),
    ("plan-digest-shape", apply_args(sha=SHA.upper()), "--apply needs --plan-sha256", True),
    ("plan-digest-shape", apply_args(sha=SHA[:63]), "--apply needs --plan-sha256", True),
    ("database-matches", ("--database", "some_other_database", "--bucket", BUCKET, *ORIGIN), "not the configured alpha database", True),
    ("bucket-matches", ("--database", DATABASE, "--bucket", "some-other-bucket", *ORIGIN), "not the configured alpha bucket", True),
)


@pytest.mark.parametrize(("guard", "args", "says", "reaches"), CASES, ids=[f"{c[0]}-{i}" for i, c in enumerate(CASES)])
def test_it_refuses_says_why_and_never_calls_docker(guard: str, args: tuple[str, ...], says: str, reaches: bool, rig: Rig) -> None:
    completed = rig.run(*args)
    assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
    assert says in completed.stderr, completed.stderr
    assert not rig.log.exists(), f"{guard} refused, but only after running docker: {rig.calls}"


@pytest.mark.parametrize(("guard", "args", "says", "reaches"), CASES, ids=[f"{c[0]}-{i}" for i, c in enumerate(CASES)])
def test_deleting_the_guard_removes_the_refusal(guard: str, args: tuple[str, ...], says: str, reaches: bool, rig: Rig) -> None:
    broken = rig.mutant(guard)
    completed = broken.run(*args)
    assert says not in completed.stderr, (
        f"the {guard} guard was deleted and the refusal happened anyway: it was never testing that guard")
    if reaches:
        assert broken.log.exists(), f"with {guard} gone the script should have gone on to the stack: {completed.stderr}"


def test_without_the_selector_guard_the_script_would_forget_everything(rig: Rig) -> None:
    """The harm behind `one-selector`: the fallback of the copy is `--all`, so a command that named nothing is a plan for the whole memory."""
    broken = rig.mutant("one-selector")
    broken.run(*COMMON)
    assert broken.tool_args(broken.tool_calls()[0]) == ["--database", DATABASE, "--bucket", BUCKET, "--all"]


def test_a_missing_environment_file_is_refused_and_the_guard_can_fail(rig: Rig, tmp_path: Path) -> None:
    args = (*PLAN, "--env-file", str(tmp_path / "not-there.env"))
    completed = rig.run(*args)
    assert completed.returncode == REFUSED and "missing or unreadable" in completed.stderr and not rig.log.exists()
    assert "missing or unreadable" not in rig.mutant("env-file-present").run(*args).stderr


def test_a_half_configured_instance_is_refused_and_the_guard_can_fail(rig: Rig) -> None:
    rig.env_file.write_text(f"POSTGRES_DB={DATABASE}\n", encoding="utf-8")
    completed = rig.run(*PLAN)
    assert completed.returncode == REFUSED and "names no ALPHA_INSTANCE" in completed.stderr and not rig.log.exists()
    broken = rig.mutant("instance-configured")
    broken.env_file.write_text(f"POSTGRES_DB={DATABASE}\n", encoding="utf-8")
    assert "names no ALPHA_INSTANCE" not in broken.run(*PLAN).stderr


@pytest.mark.parametrize("line", [
    "", "MIGRATOR_DATABASE_URL=\n", "MIGRATOR_DATABASE_URL=postgresql://u:p@postgres:5432/d\n", "MIGRATOR_DATABASE_URL=not a url\n",
], ids=["absent", "empty", "wrong-scheme", "not-a-url"])
def test_a_missing_or_malformed_owner_url_is_refused_and_the_guard_can_fail(rig: Rig, line: str) -> None:
    """`PROD-04`: the forget deletes rows only the OWNER may delete, so the one-off container is handed the owner's url; an environment that has
    none is refused before any connection, in a sentence, and not by the tool's `owner-may-write` after one."""
    rig.env_file.write_text(env_without(ENV_TEXT, "MIGRATOR_DATABASE_URL") + line, encoding="utf-8")
    completed = rig.run(*PLAN)
    assert completed.returncode == REFUSED and "[migrator_url_unset]" in completed.stderr, completed.stderr
    assert not rig.log.exists(), "the refusal came after docker was touched"
    cut = rig.mutant("migrator-url-configured")
    cut.env_file.write_text(env_without(ENV_TEXT, "MIGRATOR_DATABASE_URL") + line, encoding="utf-8")
    assert "[migrator_url_unset]" not in cut.run(*PLAN).stderr


def test_a_missing_compose_file_is_refused_and_the_guard_can_fail(tmp_path: Path) -> None:
    bare = Rig(tmp_path / "a", WRAPPER, compose=False)
    completed = bare.run(*PLAN)
    assert completed.returncode == REFUSED and "compose.server.yml is missing" in completed.stderr and not bare.log.exists()
    broken = Rig(tmp_path / "b", WRAPPER).mutant("compose-file-present")
    (broken.deploy / "compose.server.yml").unlink()
    assert "compose.server.yml is missing" not in broken.run(*PLAN).stderr


@pytest.mark.parametrize("absent", MODULES)
def test_a_checkout_without_one_of_the_five_modules_is_refused_and_the_guard_can_fail(absent: str, tmp_path: Path) -> None:
    partial = tmp_path / "partial"
    partial.mkdir()
    for module in MODULES:
        if module != absent:
            (partial / f"{module}.py").write_text("", encoding="utf-8")
    bare = Rig(tmp_path / "rig", WRAPPER, module_dir=partial)
    completed = bare.run(*PLAN)
    assert completed.returncode == REFUSED and f"lacks {absent}.py" in completed.stderr, completed.stderr
    assert not bare.log.exists()
    assert f"lacks {absent}.py" not in bare.mutant("modules-present").run(*PLAN).stderr


def test_a_dump_directory_it_cannot_write_is_refused_before_the_stack_is_touched_and_the_guard_can_fail(rig: Rig, tmp_path: Path) -> None:
    """The directory is a regular file where `forgets` should be, which `mkdir` cannot turn into a directory whoever the operator is (a mode bit
    would prove nothing to a root-run test)."""
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    (blocked / "forgets").write_text("in the way", encoding="utf-8")
    for args in (APPLY, RESUME):
        completed = rig.run(*args, env={"ALPHA_DUMP_ROOT": str(blocked)}, typed=TYPED)
        assert completed.returncode == REFUSED and "is not a writable directory" in completed.stderr, completed.stderr
        assert not rig.log.exists()
    broken = rig.mutant("dump-dir-writable")
    completed = broken.run(*APPLY, env={"ALPHA_DUMP_ROOT": str(blocked)}, typed=TYPED)
    assert "is not a writable directory" not in completed.stderr
    assert tool_reached_the_write(broken), "with the guard gone the forget starts although nothing can be recorded"


def test_a_dry_run_does_not_need_the_dump_directory(rig: Rig, tmp_path: Path) -> None:
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    (blocked / "forgets").write_text("in the way", encoding="utf-8")
    assert rig.run(*PLAN, env={"ALPHA_DUMP_ROOT": str(blocked)}).returncode == 0


def test_help_is_a_usage_error_with_its_own_status(rig: Rig) -> None:
    completed = rig.run("--help")
    assert completed.returncode == USAGE and "usage: memory-forget.sh" in completed.stderr
    assert "NO DUMP IS TAKEN" in completed.stderr and "--stop-services" in completed.stderr
    assert not rig.log.exists()


# --- the dry run is the default ---------------------------------------------------------------


def test_with_no_mode_option_it_is_the_dry_run_and_does_one_read_only_call(rig: Rig) -> None:
    completed = rig.run(*PLAN)
    assert completed.returncode == 0, completed.stderr
    assert len(rig.calls) == 1 and tool_reached_the_write(rig) is False
    assert rig.tool_args(rig.tool_calls()[0]) == ["--database", DATABASE, "--bucket", BUCKET, "--origin-project", PROJECT]
    assert f"plan-sha256: {SHA}" in completed.stdout and "dry run. NOTHING ABOVE WAS CHANGED" in completed.stdout
    assert f"--plan-sha256 {SHA}" in completed.stdout, "the dry run tells the operator what the apply needs"
    assert "api and worker should not be running for the apply" in completed.stdout and "--stop-services" in completed.stdout
    assert not rig.dumps.exists(), "a dry run creates nothing on disk"
    assert [item for item in rig.tool_calls()[0]["argv"] if str(item).endswith(":/dump")] == [], "a dry run mounts no writable directory"
    assert rig.run(*PLAN, "--dry-run").returncode == 0


def test_the_selector_reaches_the_tool_as_given(rig: Rig) -> None:
    rig.run(*COMMON, "--case", CASE_B, "--case", CASE_A)
    rig.run(*COMMON, "--all")
    first, second = rig.tool_calls()
    assert rig.tool_args(first) == ["--database", DATABASE, "--bucket", BUCKET, "--case", CASE_B, "--case", CASE_A]
    assert rig.tool_args(second) == ["--database", DATABASE, "--bucket", BUCKET, "--all"]


def test_a_selection_with_nothing_left_to_forget_is_nothing_to_do_and_asks_nothing(rig: Rig) -> None:
    rig.answers["plan"] = {"stdout": plan_text(cases=0) + "\n" + NOTHING}
    for args in (PLAN, APPLY):
        rig.log.unlink(missing_ok=True)
        completed = rig.run(*args)
        assert completed.returncode == 0, completed.stderr
        assert "nothing to do. Nothing was changed." in completed.stdout and len(rig.calls) == 1 and "retype" not in completed.stdout


def test_an_apply_that_finds_nothing_left_at_the_last_moment_is_nothing_to_do(rig: Rig) -> None:
    """Between the plan and the transaction another operator forgot the same cases: the module answers `nothing to do` and writes no manifest."""
    rig.answers["apply"] = {"stdout": NOTHING}
    completed = rig.run(*APPLY, typed=TYPED)
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    assert "nothing to do. Nothing was changed." in completed.stdout and "verified against the file" not in completed.stdout


# --- the plan that did not complete -----------------------------------------------------------


@pytest.mark.parametrize(("plan", "status", "says"), (
    ({"stdout": "", "stderr": "memory_forget: REFUSED: 1 case(s) are not in this memory\n", "status": 3}, REFUSED, "the plan was refused"),
    ({"stdout": "", "stderr": "memory_forget: FAILED: connection refused\n", "status": 4}, FAILED, "the plan failed"),
    ({"stdout": "no digest on this screen\n", "status": 0}, FAILED, "the plan printed no digest or no number of cases"),
    ({"stdout": plan_text().replace("cases: 3", "cases: none"), "status": 0}, FAILED, "the plan printed no digest or no number of cases"),
), ids=["refused", "failed", "no-digest", "no-count"])
def test_a_plan_that_did_not_complete_stops_before_anything_is_forgotten(
    plan: dict[str, object], status: int, says: str, rig: Rig
) -> None:
    rig.answers["plan"] = plan
    for args in (PLAN, APPLY):
        rig.log.unlink(missing_ok=True)
        completed = rig.run(*args, typed=TYPED)
        assert completed.returncode == status, (args, completed.stdout, completed.stderr)
        assert says in completed.stderr
        assert not tool_reached_the_write(rig) and not rig.called("stop api")


@pytest.mark.parametrize("plan", (
    {"stdout": "", "stderr": "REFUSED\n", "status": 3},
    {"stdout": "", "stderr": "FAILED\n", "status": 4},
    {"stdout": "no digest on this screen\n", "status": 0},
), ids=["refused", "failed", "no-digest"])
def test_the_preflight_guard_is_shown_able_to_fail(plan: dict[str, object], rig: Rig) -> None:
    """With a plan that gave no digest the later checks have nothing to compare, so they go too: the harm is a forget."""
    rig.answers["plan"] = plan
    broken = rig.mutant("preflight-ran", "plan-approved", "retyped-confirmation")
    completed = broken.run(*APPLY, typed=TYPED)
    assert "the plan was refused" not in completed.stderr and "the plan printed no digest" not in completed.stderr
    assert tool_reached_the_write(broken), "with the guard gone the script goes on to forget on a plan it never read"


# --- the apply --------------------------------------------------------------------------------


def test_the_order_is_plan_then_retype_then_apply_with_no_dump_anywhere(rig: Rig) -> None:
    completed = rig.run(*APPLY, typed=TYPED)
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    plan_call, apply_call = rig.tool_calls()
    assert rig.tool_args(plan_call) == ["--database", DATABASE, "--bucket", BUCKET, "--origin-project", PROJECT]
    assert rig.tool_args(apply_call) == [
        "--database", DATABASE, "--bucket", BUCKET, "--origin-project", PROJECT, "--apply", "--plan-sha256", SHA,
        "--actor", ACTOR, "--reason", "client_request", "--owner-permission-ref", REF, "--dump-dir", "/dump"]
    assert "retype the number of cases" in completed.stdout and "retype the plan digest" in completed.stdout
    assert f"THIS FORGETS THE CONTENT OF THE {CASES_COUNT} CASE(S) ABOVE" in completed.stdout
    assert len(rig.calls) == 2, rig.calls
    for record in rig.records:
        assert not {"exec", "stop", "up", "ps"} & set(record["argv"]), record["argv"]
        assert not any(word in item for item in record["argv"] for word in ("pg_dump", "pg_restore", "mirror")), record["argv"]


def test_without_stop_services_the_apply_says_api_and_worker_are_not_stopped_and_what_that_risks(rig: Rig) -> None:
    out = rig.run(*APPLY, typed=TYPED).stdout
    assert "api and worker are NOT being stopped (no --stop-services)" in out and "deadlock or roll back" in out
    stopped = Rig(rig.tmp / "stopped", WRAPPER)
    stopped.answers = healthy()
    assert "NOT being stopped" not in stopped.run(*APPLY, "--stop-services", typed=TYPED).stdout


def test_the_reason_list_is_the_modules_and_the_check_can_fail() -> None:
    listed = re.search(r'case "\$REASON" in\n\s+([^)]+)\) ;;', SCRIPT.read_text(encoding="utf-8"))
    assert listed is not None and set(listed.group(1).split("|")) == set(STATUS_REASON_CODES)
    assert set(listed.group(1).split("|")) - {"other"} != set(STATUS_REASON_CODES)


def test_every_reason_of_the_module_is_accepted(rig: Rig) -> None:
    for reason in STATUS_REASON_CODES:
        rig.log.unlink(missing_ok=True)
        assert rig.run(*apply_args(reason=reason), typed=TYPED).returncode == 0, reason
        assert rig.tool_args(rig.tool_calls()[1])[rig.tool_args(rig.tool_calls()[1]).index("--reason") + 1] == reason


def test_the_apply_prints_the_manifest_the_digest_the_queries_and_what_it_did_not_reach(rig: Rig) -> None:
    completed = rig.run(*APPLY, typed=TYPED)
    out = completed.stdout
    manifest = rig.dumps / "forgets" / FORGET / "manifest.json"
    assert manifest.read_text(encoding="utf-8") == MANIFEST_TEXT
    assert f"manifest: {manifest}" in out and "/dump/" not in out.replace("--dump-dir", ""), out
    assert f"manifest-sha256 {MANIFEST_SHA} (verified against the file)" in out
    assert "select count(*) from blob where state = 'erasure_pending'" in out
    assert "decision_memory_content c where exists" in out and "e.kind = 'forget'" in out
    assert f"event_type = 'memory.forget_completed' and aggregate_id = '{FORGET}'" in out
    assert "NO DUMP WAS TAKEN" in out and "still holds the content" in out
    assert "A forget does not reach:" in out, "the module's closing list reaches the operator"
    assert f"psql -U {USER} -d {DATABASE}" in out


def test_the_directory_is_the_operators_0700_and_the_container_runs_as_the_operators_uid(rig: Rig) -> None:
    rig.run(*APPLY, typed=TYPED)
    directory = rig.dumps / "forgets"
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    call = rig.tool_calls()[1]["argv"]
    assert call[call.index("--user") + 1] == f"{os.getuid()}:{os.getgid()}", call
    assert next(c for c in call if str(c).endswith(":/dump")) == f"{directory}:/dump", "the dump directory is mounted writable (no :ro)"


def test_the_five_modules_are_mounted_read_only_and_nothing_else_of_the_checkout(rig: Rig) -> None:
    rig.run(*APPLY, typed=TYPED)
    for call in rig.tool_calls():
        argv = [str(item) for item in call["argv"]]
        mounts = sorted(argv[i + 1] for i, item in enumerate(argv) if item == "-v" and ":/purge/" in argv[i + 1])
        assert mounts == sorted(f"{MODULE_DIR}/{m}.py:/purge/scripts/recovery/{m}.py:ro" for m in MODULES), mounts
        assert "PYTHONPATH=/app/src:/purge" in argv
        at = argv.index("--entrypoint")
        assert argv[at + 1:at + 5] == ["python", "api", "-m", "scripts.recovery.memory_forget"]
        assert {"run", "--rm", "--no-deps", "-T"} <= set(argv)


def test_the_mounted_list_is_the_modules_own_import_closure_and_the_check_can_fail() -> None:
    """The api image does not carry `scripts/recovery`: a module that gains an import without the list gaining a file fails in the container and
    nowhere else. The closure is read from the sources, transitively."""
    closure = modules_imported_by("memory_forget")
    declared = set(re.search(r"^MODULES=\(([^)]*)\)", SCRIPT.read_text(encoding="utf-8"), re.MULTILINE).group(1).split())  # type: ignore[union-attr]
    assert declared == closure == set(MODULES)
    assert declared - {"schema_coverage"} != closure, "the comparison cannot tell a list that lacks a module from the closure"


AMBIENT = "postgresql+psycopg://ambient:ambient@elsewhere:5432/ambient"


def test_the_python_half_is_handed_the_owners_url_at_every_step_and_never_the_applications(rig: Rig) -> None:
    """`api`'s own `DATABASE_URL` is the application role's, which the tool refuses; the owner's goes in the environment of the `docker compose`
    process, an ambient `DATABASE_URL` is overridden, no `PG*` variable is passed to the container and no command line carries a url."""
    env = {"DATABASE_URL": AMBIENT, "PGHOST": "elsewhere", "PGPASSWORD": "ambient-secret", "PGSERVICE": "x"}
    assert rig.run(*APPLY, env=env, typed=TYPED).returncode == 0
    assert [r["database_url"] for r in rig.tool_calls()] == [MIGRATOR_URL, MIGRATOR_URL]
    assert APP_URL not in "".join(str(r["database_url"]) for r in rig.records)
    for record in rig.tool_calls():
        argv = [str(item) for item in record["argv"]]
        assert not any(item.startswith("PG") or "=PG" in item for item in argv), argv
        assert not any("postgresql+psycopg://" in item or "an-owner-db-password-0002" in item or "ambient-secret" in item for item in argv), argv


def test_the_owner_url_assertion_can_fail_without_the_environment_prefix(rig: Rig) -> None:
    broken = rig.edited('DATABASE_URL="$MIGRATOR_URL" compose run', "compose run")
    assert broken.run(*APPLY, env={"DATABASE_URL": AMBIENT}, typed=TYPED).returncode == 0
    assert {r["database_url"] for r in broken.tool_calls()} == {AMBIENT}


def test_docker_never_reads_the_answers_the_operator_types(rig: Rig) -> None:
    """`docker compose run` forwards stdin to the container, so a pipe feeding the retype would be eaten by the plan step: the stub reads whatever
    stdin it is given, and must be given none."""
    assert rig.run(*APPLY, typed=TYPED).returncode == 0
    assert [r["stdin_bytes"] for r in rig.records] == [0, 0]
    broken = rig.edited('--entrypoint python api -m scripts.recovery.memory_forget "$@" </dev/null',
                        '--entrypoint python api -m scripts.recovery.memory_forget "$@"')
    completed = broken.run(*APPLY, typed=TYPED)
    assert completed.returncode == REFUSED and "what was retyped is not the number of cases" in completed.stderr
    assert not tool_reached_the_write(broken)


def test_the_option_order_does_not_matter(rig: Rig) -> None:
    shuffled = ("--plan-sha256", SHA, "--apply", "--owner-permission-ref", REF, "--reason", "client_request", "--actor", ACTOR,
                "--origin-project", PROJECT, "--bucket", BUCKET, "--database", DATABASE)
    assert rig.run(*shuffled, typed=TYPED).returncode == 0 and tool_reached_the_write(rig)


# --- the plan the operator approved, and what they retype -------------------------------------


def test_a_plan_that_changed_since_it_was_approved_is_refused_and_the_guard_can_fail(rig: Rig) -> None:
    rig.answers["plan"] = {"stdout": plan_text(sha=OTHER_SHA)}
    completed = rig.run(*APPLY, typed=f"{CASES_COUNT}\n{OTHER_SHA}\n")
    assert completed.returncode == REFUSED and "not the plan you approved" in completed.stderr, completed.stderr
    assert OTHER_SHA in completed.stderr and SHA in completed.stderr
    assert not tool_reached_the_write(rig) and "retype" not in completed.stdout, "it must not even ask"
    broken = rig.mutant("plan-approved")
    completed = broken.run(*APPLY, typed=f"{CASES_COUNT}\n{OTHER_SHA}\n")
    assert "not the plan you approved" not in completed.stderr
    assert tool_reached_the_write(broken), "with the guard gone the apply is sent with a digest the memory no longer has"


@pytest.mark.parametrize("typed", (
    "", f"{CASES_COUNT}\n", f"4\n{SHA}\n", f"{CASES_COUNT}\n{OTHER_SHA}\n", f"{SHA}\n{CASES_COUNT}\n", f"{CASES_COUNT} \n{SHA}\n", "\n\n",
    f"03\n{SHA}\n",
), ids=["nothing", "no-digest", "other-count", "other-digest", "swapped", "trailing-space", "blank-lines", "leading-zero"])
def test_what_is_retyped_must_be_the_count_and_the_digest_and_the_guard_can_fail(typed: str, rig: Rig) -> None:
    completed = rig.run(*APPLY, "--stop-services", typed=typed)
    assert completed.returncode == REFUSED and "what was retyped is not the number of cases" in completed.stderr, completed.stderr
    assert not tool_reached_the_write(rig) and not rig.called("stop api"), "nothing is stopped for an answer nobody gave"
    broken = rig.mutant("retyped-confirmation")
    completed = broken.run(*APPLY, typed=typed)
    assert "what was retyped is not the number of cases" not in completed.stderr
    assert tool_reached_the_write(broken), "with the guard gone the forget runs on an answer nobody gave"


def test_the_answers_come_from_the_keyboard_not_from_the_command_line(rig: Rig) -> None:
    completed = rig.run(*APPLY, "--yes")
    assert completed.returncode == REFUSED and "unrecognised option: --yes" in completed.stderr
    completed = rig.run(*APPLY)  # no input at all: an end of input is no answer
    assert completed.returncode == REFUSED and "retyped" in completed.stderr and not tool_reached_the_write(rig)


# --- a stop after the commit ------------------------------------------------------------------


def _resume_line(stderr: str) -> str:
    return next(line.strip() for line in stderr.splitlines() if "--resume" in line and line.strip().startswith(("ALPHA_DUMP_ROOT", "/")))


@pytest.mark.parametrize("status", (FAILED, REFUSED))
def test_a_stop_after_the_commit_is_a_failure_that_prints_the_forget_id_and_the_exact_resume_command(status: int, rig: Rig) -> None:
    """A module status of 3 after the commit is still a failure here: 3 promises that nothing was changed."""
    rig.answers["apply"] = {"stdout": f"forget-id: {FORGET}\n", "stderr": "memory_forget: FAILED: 1 object could not be deleted\n",
                            "status": status}
    completed = rig.run(*APPLY, typed=TYPED)
    assert completed.returncode == FAILED, (completed.stdout, completed.stderr)
    assert "THE DATABASE PART OF THE FORGET IS COMMITTED" in completed.stderr and FORGET in completed.stderr
    assert f"{rig.dumps}/forgets/{FORGET}/" in completed.stderr, "where the plan and the manifest are"
    # The line is a command the operator can paste: run it and the wrapper resumes that forget, with the same words.
    tokens = shlex.split(_resume_line(completed.stderr))
    env = dict(token.split("=", 1) for token in tokens[:1] if re.match(r"^[A-Z_]+=", token))
    command = tokens[len(env):]
    assert command[0].endswith("memory-forget.sh")
    assert env == {"ALPHA_DUMP_ROOT": str(rig.dumps)}
    rig.log.unlink()
    rig.answers["resume"] = {"stdout": done_text(), "write_manifest": {"id": FORGET, "text": MANIFEST_TEXT}}
    resumed = rig.run(*command[1:], env=env)
    assert resumed.returncode == 0, resumed.stderr
    assert rig.tool_args(rig.tool_calls()[0]) == [
        "--database", DATABASE, "--bucket", BUCKET, "--resume", FORGET, "--actor", ACTOR,
        "--owner-permission-ref", REF, "--dump-dir", "/dump"]


def test_the_resume_hint_is_shown_able_to_fail(rig: Rig) -> None:
    rig.answers["apply"] = {"stdout": f"forget-id: {FORGET}\n", "stderr": "boom\n", "status": FAILED}
    assert "--resume" in rig.run(*APPLY, typed=TYPED).stderr
    broken = rig.edited('"  $(resume_command "$forget_id")" \\\n', '"  (no command)" \\\n')
    assert "--resume" not in broken.run(*APPLY, typed=TYPED).stderr


@pytest.mark.parametrize(("answer", "status", "says"), (
    ({"stderr": "memory_forget: REFUSED: the plan changed\n", "status": 3}, REFUSED, "the forget was refused"),
    ({"stderr": "memory_forget: FAILED: connection reset\n", "status": 4}, FAILED, "the forget failed"),
), ids=["refused", "failed"])
def test_a_stop_before_the_commit_says_nothing_was_changed_and_offers_no_resume(
    answer: dict[str, object], status: int, says: str, rig: Rig
) -> None:
    rig.answers["apply"] = answer
    completed = rig.run(*APPLY, typed=TYPED)
    assert completed.returncode == status and says in completed.stderr
    assert "COMMITTED" not in completed.stderr and "--resume" not in completed.stderr
    assert (status == REFUSED) == ("Nothing was changed" in completed.stderr)


def test_an_earlier_unfinished_erase_or_forget_is_named_and_the_operator_is_sent_to_the_runbook(rig: Rig) -> None:
    rig.answers["plan"] = {"stdout": "", "status": 3, "stderr": (
        "memory_forget: REFUSED: 2 Blob row(s) are in erasure_pending: an earlier erase or forget committed and did not finish. "
        "Resume it (--resume era_<id>, found in its erasure.requested or memory.forget_requested event) first.\n")}
    completed = rig.run(*APPLY, typed=TYPED)
    assert completed.returncode == REFUSED and "an earlier erase or forget committed and did not finish" in completed.stderr
    assert "runbook section 21" in completed.stderr and not tool_reached_the_write(rig)


# --- a lock that could not be taken, and the services -----------------------------------------

LOCK = {"stdout": "", "stderr": "memory_forget: REFUSED: could not lock the tables within 15s: something is still writing. "
                                "Stop api/worker and run it again; nothing was changed.\n", "status": 3}


def test_could_not_lock_offers_the_stop_services_option_and_then_names_what_else_may_write(rig: Rig) -> None:
    rig.answers["apply"] = LOCK
    completed = rig.run(*APPLY, typed=TYPED)
    assert completed.returncode == REFUSED and "--stop-services" in completed.stderr and "Nothing was changed" in completed.stderr
    assert not rig.called("stop api")
    again = rig.run(*APPLY, "--stop-services", typed=TYPED)
    assert again.returncode == REFUSED and "something besides api and worker is still writing" in again.stderr


def test_the_services_that_run_are_stopped_for_the_apply_only_and_started_again_after_it(rig: Rig) -> None:
    completed = rig.run(*APPLY, "--stop-services", typed=TYPED)
    assert completed.returncode == 0, completed.stderr
    plan_i = rig.index("scripts.recovery.memory_forget")
    ps_i, stop_i = rig.index("ps --status running --services"), rig.index("stop api worker")
    apply_i, up_i = rig.index("--apply"), rig.index("up -d --no-deps api worker")
    assert plan_i < ps_i < stop_i < apply_i < up_i, rig.calls
    assert "stopping api worker" in completed.stdout and "starting api worker again" in completed.stdout


def test_only_the_writers_that_were_running_are_stopped_and_started_again(rig: Rig) -> None:
    """A service the operator had stopped on purpose is not ours to start: the list comes from what is running, and `web` is never touched."""
    rig.answers["running"] = ["postgres", "s3", "worker", "web"]
    assert rig.run(*APPLY, "--stop-services", typed=TYPED).returncode == 0
    assert rig.called("stop worker") and not rig.called("stop api") and not rig.called("stop api worker")
    assert rig.called("up -d --no-deps worker") and not rig.called("up -d --no-deps api")
    assert not any("web" in call.split("stop ")[-1] for call in rig.calls if " stop " in call)


def test_the_list_of_what_to_stop_is_shown_able_to_fail(rig: Rig) -> None:
    broken = rig.edited('WRITERS=(api worker)', 'WRITERS=(api worker web)')
    broken.answers["running"] = ["postgres", "s3", "api", "worker", "web"]
    assert broken.run(*APPLY, "--stop-services", typed=TYPED).returncode == 0
    assert broken.called("stop api worker web"), "the assertion above would not notice a third service"


def test_with_neither_writer_running_nothing_is_stopped_or_started(rig: Rig) -> None:
    rig.answers["running"] = ["postgres", "s3", "web"]
    completed = rig.run(*APPLY, "--stop-services", typed=TYPED)
    assert completed.returncode == 0 and "neither api nor worker is running; nothing to stop" in completed.stdout
    assert not any({"stop", "up"} & set(record["argv"]) for record in rig.records), rig.calls


def test_a_stack_that_cannot_list_its_services_is_a_failure_before_anything_is_written(rig: Rig) -> None:
    rig.answers["ps_status"] = 1
    completed = rig.run(*APPLY, "--stop-services", typed=TYPED)
    assert completed.returncode == FAILED and "could not list the running services" in completed.stderr
    assert not tool_reached_the_write(rig)


@pytest.mark.parametrize(("answer", "status"), (
    ({"stderr": "REFUSED\n", "status": 3}, REFUSED),
    ({"stderr": "FAILED\n", "status": 4}, FAILED),
    ({"stdout": f"forget-id: {FORGET}\n", "stderr": "FAILED\n", "status": 4}, FAILED),
), ids=["refused", "failed", "failed-after-commit"])
def test_the_services_come_back_whatever_the_apply_did(answer: dict[str, object], status: int, rig: Rig) -> None:
    rig.answers["apply"] = answer
    completed = rig.run(*APPLY, "--stop-services", typed=TYPED)
    assert completed.returncode == status
    assert rig.index("up -d --no-deps api worker") > rig.index("stop api worker")
    broken = rig.edited("trap cleanup EXIT\n", "")
    assert broken.run(*APPLY, "--stop-services", typed=TYPED).returncode == status
    assert broken.called("stop api worker") and not broken.called("up -d --no-deps"), "without the trap a refusal leaves the services stopped"


def test_without_the_option_the_services_are_left_alone(rig: Rig) -> None:
    assert rig.run(*APPLY, typed=TYPED).returncode == 0
    assert not any({"stop", "up", "ps"} & set(record["argv"]) for record in rig.records), rig.calls


# --- the manifest on disk is the one the database holds ---------------------------------------


@pytest.mark.parametrize(("manifest_sha", "text"), (
    (OTHER_SHA, MANIFEST_TEXT), (MANIFEST_SHA, MANIFEST_TEXT + " "), ("not-a-digest", MANIFEST_TEXT),
), ids=["digest-differs", "file-differs", "no-digest"])
def test_a_manifest_that_does_not_hash_to_the_journalled_digest_is_a_failure_and_the_guard_can_fail(
    manifest_sha: str, text: str, rig: Rig
) -> None:
    rig.answers["apply"] = {"stdout": done_text(manifest_sha=manifest_sha), "write_manifest": {"id": FORGET, "text": text}}
    completed = rig.run(*APPLY, typed=TYPED)
    assert completed.returncode == FAILED and "THE FORGET COMPLETED but the manifest on disk" in completed.stderr
    assert "verified against the file" not in completed.stdout
    broken = rig.mutant("manifest-verified")
    completed = broken.run(*APPLY, typed=TYPED)
    assert "THE FORGET COMPLETED but the manifest on disk" not in completed.stderr
    assert completed.returncode == 0 and "verified against the file" in completed.stdout, (
        "with the guard gone the operator is told to keep a file that was never compared with anything")


def test_a_manifest_that_is_missing_is_a_failure(rig: Rig) -> None:
    rig.answers["apply"] = {"stdout": done_text()}  # the stub writes no file
    completed = rig.run(*APPLY, typed=TYPED)
    assert completed.returncode == FAILED and "<unreadable>" in completed.stderr


def test_an_apply_that_printed_no_manifest_is_a_failure_that_says_the_database_part_is_done(rig: Rig) -> None:
    rig.answers["apply"] = {"stdout": f"forget-id: {FORGET}\n"}
    completed = rig.run(*APPLY, typed=TYPED)
    assert completed.returncode == FAILED and "printed no manifest digest" in completed.stderr


# --- --resume ---------------------------------------------------------------------------------


def test_a_resume_runs_the_module_once_asks_nothing_and_verifies_the_manifest(rig: Rig) -> None:
    completed = rig.run(*RESUME)
    assert completed.returncode == 0, completed.stderr
    assert len(rig.tool_calls()) == 1, "a resume has no plan step"
    assert rig.tool_args(rig.tool_calls()[0]) == [
        "--database", DATABASE, "--bucket", BUCKET, "--resume", FORGET, "--actor", ACTOR,
        "--owner-permission-ref", REF, "--dump-dir", "/dump"]
    assert "retype" not in completed.stdout and f"manifest-sha256 {MANIFEST_SHA} (verified" in completed.stdout
    assert [r["database_url"] for r in rig.tool_calls()] == [MIGRATOR_URL]


def test_a_resume_of_a_finished_forget_says_so_and_changes_nothing(rig: Rig) -> None:
    rig.answers["resume"] = {"stdout": f"memory-forget: {FORGET} is already complete; nothing to do.\n"}
    completed = rig.run(*RESUME)
    assert completed.returncode == 0 and "already complete" in completed.stdout and "verified against" not in completed.stdout


def test_a_resume_that_stops_again_prints_the_same_command(rig: Rig) -> None:
    rig.answers["resume"] = {"stdout": f"forget-id: {FORGET}\n", "stderr": "FAILED: still no\n", "status": FAILED}
    completed = rig.run(*RESUME)
    assert completed.returncode == FAILED and f"--resume {FORGET}" in completed.stderr
    tokens = shlex.split(_resume_line(completed.stderr))
    assert tokens[tokens.index("--owner-permission-ref") + 1] == REF, "the reference survives the shell quoting"
    assert tokens[tokens.index("--actor") + 1] == ACTOR


def test_a_resume_can_stop_the_services_too(rig: Rig) -> None:
    assert rig.run(*RESUME, "--stop-services").returncode == 0
    assert rig.index("stop api worker") < rig.index("--resume") < rig.index("up -d --no-deps api worker")


# --- what this script does not do -------------------------------------------------------------


def test_the_script_takes_no_dump_and_no_mirror_and_the_check_can_fail(rig: Rig) -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    for word in ("pg_dump", "pg_restore", "snapshot-objects", "objects.attrs", "reset.sh", "mc mirror"):
        assert word not in code, f"{word!r} appears in the code of a script that must take no dump"
    assert "NO DUMP" in text
    broken = rig.edited('echo "memory-forget.sh: forgetting (one transaction',
                        'compose exec -T postgres pg_dump --format=custom --dbname "$DATABASE" > /dev/null\n'
                        'echo "memory-forget.sh: forgetting (one transaction')
    broken.run(*APPLY, typed=TYPED)  # the stub has no answer for a dump, so the script stops there
    assert broken.called("pg_dump"), "the call recorder sees a dump if one is taken"
    assert rig.run(*APPLY, typed=TYPED).returncode == 0 and not rig.called("pg_dump")


def test_the_copy_key_file_list_does_not_gain_this_script() -> None:
    """Runbook section 13 lists the five files the copy key installs. A forget is an interactive act of an administrator with the owner's
    permission and must not be reachable from an unattended key."""
    runbook = (ROOT / "docs/program/DEPLOYMENT_RUNBOOK.md").read_text(encoding="utf-8")
    listing = re.search(r"for f in (copy-serve\.sh [^;]+); do", runbook)
    assert listing is not None and "memory-forget.sh" not in listing.group(1)
    assert "memory-forget" not in (ROOT / "infra/deploy/copy-serve.sh").read_text(encoding="utf-8")


def test_the_script_is_executable_and_in_the_deploy_directory() -> None:
    assert SCRIPT.exists() and os.access(SCRIPT, os.X_OK)
    assert SCRIPT.parent == ROOT / "infra/deploy"


def test_every_guard_in_the_script_has_a_case_here() -> None:
    markers = guard_names(SCRIPT)
    me = Path(__file__).read_text(encoding="utf-8")
    missing = sorted(name for name in markers if f'"{name}"' not in me)
    assert not missing, f"guards with no case: {missing}"
    assert len(markers) == 24, sorted(markers)
    text = SCRIPT.read_text(encoding="utf-8")
    for name in markers:
        assert len(re.findall(rf"^ *# <<< guard: {re.escape(name)}$", text, re.MULTILINE)) == 1
