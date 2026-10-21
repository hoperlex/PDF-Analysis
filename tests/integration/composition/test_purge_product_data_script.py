"""`STAND-PURGE-TOOL-01` -- every refusal `infra/deploy/purge-product-data.sh` makes, and every one shown able to fail.

The convention is `test_reset_script_refusals.py`'s, for the same reason (`R-4`: a guard on a
destructive operator tool that has never been shown to fail is the most expensive kind of green):

1. an invocation that should trip a guard exits **3**, says why, and -- for the guards that run
   before any connection -- makes **no `docker` call at all**;
2. the same invocation against a **copy of the script with exactly that guard block deleted**
   no longer produces that refusal. Where the guard sits after a connection, the copy is also
   shown to reach the next destructive step (`pg_dump`, `apply`), which is the harm.

Nothing here can touch a stand: `docker` is a stub on `PATH` that records its arguments and
answers from a script the test writes, so the cases drive the script's ORDER and EXIT CODES
without a database. The part that needs a database -- the classification, the transaction, the
objects -- is `tests/integration/recovery/test_product_purge.py`, and the two halves meet in
`test_product_purge_script.py` there, which runs this script against a real PostgreSQL and bucket.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "infra/deploy/purge-product-data.sh"
MODULE_DIR = ROOT / "scripts/recovery"

INSTANCE, DATABASE, BUCKET, USER = "an-instance", "the_configured_database", "the-configured-bucket", "the_user"
REFUSED, FAILED, USAGE = 3, 4, 2
SHA = "a" * 64
OBJECTS_SHA = "b" * 64

ENV_FILE = f"ALPHA_INSTANCE={INSTANCE}\nPOSTGRES_DB={DATABASE}\nPOSTGRES_USER={USER}\nS3_BUCKET={BUCKET}\n"

COMMON = ("--database", DATABASE, "--bucket", BUCKET)

STUB = r'''#!{python}
import json, os, sys
argv = sys.argv[1:]
with open(os.environ["STUB_LOG"], "a") as log:
    log.write(" ".join(argv) + "\n")
config = json.load(open(os.environ["STUB_CONFIG"]))
rest = argv
while rest and rest[0] in ("compose", "--env-file", "--file"):
    rest = rest[2:] if rest[0] != "compose" else rest[1:]
def answer(entry):
    sys.stdout.write(entry.get("stdout", ""))
    sys.stdout.flush()
    sys.stderr.write(entry.get("stderr", ""))
    sys.exit(entry.get("status", 0))
if rest[:1] == ["stop"] or (rest[:1] == ["up"] and rest[-1] == "worker"):
    sys.exit(0)
if rest[:3] == ["exec", "-T", "postgres"]:
    command = rest[3:]
    if command[0] == "pg_dump":
        answer(config["pg_dump"])
    if command[0] == "pg_restore" and "--list" in command:
        answer(config["pg_restore_list"])
    if command[0] == "pg_restore" and "--file=-" in command:
        answer(config["pg_restore_expand"])
if "scripts.recovery.product_purge" in rest:
    sub = rest[rest.index("scripts.recovery.product_purge") + 1]
    if sub == "snapshot-objects" and config[sub].get("status", 0) == 0:
        mount = next(rest[i + 1].split(":")[0] for i, item in enumerate(rest) if item == "-v" and rest[i + 1].endswith(":/dump"))
        os.makedirs(os.path.join(mount, "objects"), exist_ok=True)
        open(os.path.join(mount, "objects.attrs"), "w").write("")
        open(os.path.join(mount, "product-objects.tsv"), "w").write("")
    answer(config[sub])
sys.stderr.write("docker stub: no answer for: " + " ".join(argv) + "\n")
sys.exit(99)
'''


def plan_text(*, sha: str = SHA, nothing: str = "no", db_bytes: int = 1000, obj_bytes: int = 10) -> str:
    return (f"-- PRODUCT tables --\n  project  (5 rows)\nnothing-to-purge: {nothing}\n"
            f"database-bytes: {db_bytes}\nproduct-object-bytes: {obj_bytes}\nplan-sha256: {sha}\n")


def healthy() -> dict[str, dict[str, object]]:
    return {
        "plan": {"stdout": plan_text()},
        "pg_dump": {"stdout": "PGDMP-a-dump-of-the-database"},
        "pg_restore_list": {}, "pg_restore_expand": {},
        "snapshot-objects": {"stdout": f"snapshot-objects: 2 objects, 9 bytes copied to /dump/objects\n"
                                       f"plan-sha256: {SHA}\nobjects-sha256: {OBJECTS_SHA}\n"},
        "apply": {"stdout": "purge-product-data: committed.\n"},
        "delete-objects": {"stdout": "purge-product-data: objects deleted by exact key: 2 deleted (9 bytes), 0 already absent\n"},
    }


class Rig:
    """A scratch deployment directory with the script, a compose file, an env file and a stub."""

    def __init__(self, tmp_path: Path, *, script: Path = SCRIPT, worker: bool = True,
                 module_dir: Path = MODULE_DIR, compose: bool = True) -> None:
        self.tmp = tmp_path
        self.deploy = tmp_path / "deploy"
        self.deploy.mkdir(parents=True, exist_ok=True)
        self.script = self.deploy / "purge-product-data.sh"
        self.script.write_text(script.read_text(encoding="utf-8"), encoding="utf-8")
        if compose:
            (self.deploy / "compose.server.yml").write_text(
                "services:\n  api:\n    image: x\n" + ("  worker:\n    image: x\n" if worker else ""), encoding="utf-8")
        self.env_file = tmp_path / "alpha.env"
        self.env_file.write_text(ENV_FILE, encoding="utf-8")
        self.bin = tmp_path / "bin"
        self.bin.mkdir(exist_ok=True)
        stub = self.bin / "docker"
        stub.write_text(STUB.replace("{python}", sys.executable), encoding="utf-8")
        stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
        self.log = tmp_path / "docker.log"
        self.config = tmp_path / "stub.json"
        self.dumps = tmp_path / "dumps"
        self.module_dir = module_dir
        self.answers = healthy()

    def mutant(self, *guards: str) -> Rig:
        """The same rig around a copy of the script with those guard blocks deleted."""
        source = SCRIPT.read_text(encoding="utf-8")
        for guard in guards:
            block = re.compile(rf"^# >>> guard: {re.escape(guard)}\n.*?^# <<< guard: {re.escape(guard)}\n",
                               re.DOTALL | re.MULTILINE)
            source, count = block.subn("", source)
            assert count == 1, f"the guard markers for {guard!r} are not a single block"
        copy = self.tmp / "mutant-script.sh"
        copy.write_text(source, encoding="utf-8")
        compose = self.deploy / "compose.server.yml"
        rig = Rig(self.tmp / "mutant", script=copy, module_dir=self.module_dir, compose=compose.exists(),
                  worker=compose.exists() and "  worker:" in compose.read_text(encoding="utf-8"))
        rig.answers = self.answers
        return rig

    def run(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        self.config.write_text(json.dumps(self.answers), encoding="utf-8")
        environment = dict(os.environ)
        environment.update(
            PATH=f"{self.bin}{os.pathsep}{environment['PATH']}", ALPHA_ENV_FILE=str(self.env_file),
            ALPHA_DUMP_ROOT=str(self.dumps), ALPHA_PURGE_MODULE_DIR=str(self.module_dir),
            STUB_LOG=str(self.log), STUB_CONFIG=str(self.config))
        environment.update(env or {})
        return subprocess.run(["bash", str(self.script), *args], capture_output=True, text=True,
                              env=environment, timeout=120)

    @property
    def calls(self) -> list[str]:
        return self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []

    def called(self, needle: str) -> bool:
        return any(needle in call for call in self.calls)

    def index(self, needle: str) -> int:
        return next(i for i, call in enumerate(self.calls) if needle in call)


@pytest.fixture()
def rig(tmp_path: Path) -> Rig:
    return Rig(tmp_path)


# --- the guards that run before any connection ------------------------------------------------

CASES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("known-options", (*COMMON, "--dry-run", "--dryrun"), "unrecognised option: --dryrun"),
    ("destructive-flag", COMMON, "no --yes-purge-product-data and no --dry-run"),
    ("one-mode", (*COMMON, "--dry-run", "--yes-purge-product-data"), "were more than one"),
    ("names-required", ("--dry-run",), "--database and --bucket are both required"),
    ("database-matches", ("--database", "some_other_database", "--bucket", BUCKET, "--dry-run"),
     "not the configured alpha database"),
    ("bucket-matches", ("--database", DATABASE, "--bucket", "some-other-bucket", "--dry-run"),
     "not the configured alpha bucket"),
)


@pytest.mark.parametrize(("guard", "args", "says"), CASES, ids=[c[0] for c in CASES])
def test_it_refuses_says_why_and_never_calls_docker(guard: str, args: tuple[str, ...], says: str, rig: Rig) -> None:
    completed = rig.run(*args)
    assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
    assert says in completed.stderr, completed.stderr
    assert not rig.log.exists(), f"{guard} refused, but only after running docker: {rig.calls}"


@pytest.mark.parametrize(("guard", "args", "says"), CASES, ids=[c[0] for c in CASES])
def test_deleting_the_guard_removes_the_refusal(guard: str, args: tuple[str, ...], says: str, rig: Rig) -> None:
    completed = rig.mutant(guard).run(*args)
    assert says not in completed.stderr, (
        f"the {guard} guard was deleted and the refusal happened anyway: it was never testing that guard")


def test_a_missing_environment_file_is_refused_and_the_guard_can_fail(rig: Rig, tmp_path: Path) -> None:
    args = (*COMMON, "--dry-run", "--env-file", str(tmp_path / "not-there.env"))
    completed = rig.run(*args)
    assert completed.returncode == REFUSED and "missing or unreadable" in completed.stderr and not rig.log.exists()
    assert "missing or unreadable" not in rig.mutant("env-file-present").run(*args).stderr


def test_a_half_configured_instance_is_refused_and_the_guard_can_fail(rig: Rig) -> None:
    rig.env_file.write_text(f"POSTGRES_DB={DATABASE}\n", encoding="utf-8")
    completed = rig.run(*COMMON, "--dry-run")
    assert completed.returncode == REFUSED and "names no ALPHA_INSTANCE" in completed.stderr and not rig.log.exists()
    broken = rig.mutant("instance-configured")
    broken.env_file.write_text(f"POSTGRES_DB={DATABASE}\n", encoding="utf-8")
    assert "names no ALPHA_INSTANCE" not in broken.run(*COMMON, "--dry-run").stderr


def test_a_missing_compose_file_is_refused_and_the_guard_can_fail(tmp_path: Path) -> None:
    rig = Rig(tmp_path / "a", compose=False)
    completed = rig.run(*COMMON, "--dry-run")
    assert completed.returncode == REFUSED and "compose.server.yml is missing" in completed.stderr
    assert not rig.log.exists()
    broken = Rig(tmp_path / "b").mutant("compose-file-present")
    (broken.deploy / "compose.server.yml").unlink()
    assert "compose.server.yml is missing" not in broken.run(*COMMON, "--dry-run").stderr


def test_a_checkout_without_the_classification_module_is_refused_and_the_guard_can_fail(tmp_path: Path) -> None:
    empty = tmp_path / "no-module"
    empty.mkdir()
    rig = Rig(tmp_path / "rig", module_dir=empty)
    completed = rig.run(*COMMON, "--dry-run")
    assert completed.returncode == REFUSED and "product_purge.py or schema_coverage.py is missing" in completed.stderr
    assert not rig.log.exists()
    assert "product_purge.py or schema_coverage.py is missing" not in rig.mutant("module-present").run(*COMMON, "--dry-run").stderr


def test_finish_objects_needs_a_dump_directory_of_ours(rig: Rig, tmp_path: Path) -> None:
    half = tmp_path / "half-a-dump"
    half.mkdir()
    (half / "product-objects.tsv").write_text("", encoding="utf-8")  # objects.sha256 is absent
    completed = rig.run(*COMMON, "--finish-objects", str(half))
    assert completed.returncode == REFUSED and "is not one of this script's dump directories" in completed.stderr
    assert not rig.log.exists()
    assert "is not one of this script's dump directories" not in rig.mutant("finish-dir-valid").run(
        *COMMON, "--finish-objects", str(half)).stderr


def test_help_is_a_usage_error_with_its_own_status(rig: Rig) -> None:
    completed = rig.run("--help")
    assert completed.returncode == USAGE and "usage: purge-product-data.sh" in completed.stderr
    assert not rig.log.exists()


# --- the preflight ----------------------------------------------------------------------------


@pytest.mark.parametrize(("plan", "status", "says"), (
    ({"stdout": "", "stderr": "product_purge: REFUSED: table(s) classified as neither\n", "status": 3},
     REFUSED, "the preflight refused"),
    ({"stdout": "", "stderr": "product_purge: FAILED: connection refused\n", "status": 4},
     FAILED, "the preflight could not complete"),
    ({"stdout": "no digest on this screen\n", "status": 0}, FAILED, "printed no plan digest"),
), ids=["refused", "failed", "no-digest"])
def test_a_preflight_that_did_not_complete_stops_before_anything_is_dumped(
    plan: dict[str, object], status: int, says: str, rig: Rig
) -> None:
    rig.answers["plan"] = plan
    for mode in ("--dry-run", "--yes-purge-product-data"):
        rig.log.unlink(missing_ok=True)
        completed = rig.run(*COMMON, mode)
        assert completed.returncode == status, (mode, completed.stdout, completed.stderr)
        assert says in completed.stderr
        assert not rig.called("pg_dump") and not rig.called("stop worker") and not rig.called("apply")


@pytest.mark.parametrize("plan", (
    {"stdout": "", "stderr": "REFUSED\n", "status": 3},
    {"stdout": "no digest on this screen\n", "status": 0},
), ids=["refused", "no-digest"])
def test_the_preflight_guard_is_shown_able_to_fail(plan: dict[str, object], rig: Rig) -> None:
    rig.answers["plan"] = plan
    broken = rig.mutant("preflight-ran")
    completed = broken.run(*COMMON, "--yes-purge-product-data")
    assert "the preflight refused" not in completed.stderr and "printed no plan digest" not in completed.stderr
    assert broken.called("pg_dump"), "with the guard gone the script goes on to dump and purge"


def test_a_dry_run_asks_the_preflight_once_and_does_nothing_else(rig: Rig) -> None:
    completed = rig.run(*COMMON, "--dry-run")
    assert completed.returncode == 0, completed.stderr
    assert len(rig.calls) == 1 and "product_purge plan" in rig.calls[0] and "--dry-run" in rig.calls[0]
    assert "--dry-run. NOTHING ABOVE WAS CHANGED" in completed.stdout
    assert not rig.dumps.exists()


def test_a_second_run_that_finds_nothing_says_so_and_writes_nothing(rig: Rig) -> None:
    rig.answers["plan"] = {"stdout": plan_text(nothing="yes")}
    completed = rig.run(*COMMON, "--yes-purge-product-data")
    assert completed.returncode == 0, completed.stderr
    assert "nothing to purge. Nothing was dumped and nothing was changed." in completed.stdout
    assert len(rig.calls) == 1 and not rig.dumps.exists()


# --- dump, verify, purge, objects -------------------------------------------------------------


def test_the_order_is_preflight_stop_dump_objects_verify_plan_check_purge_objects_start(rig: Rig) -> None:
    completed = rig.run(*COMMON, "--yes-purge-product-data")
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    order = ["product_purge plan", "stop worker", "pg_dump", "product_purge snapshot-objects",
             "pg_restore --list", "pg_restore --file=-", "product_purge apply",
             "product_purge delete-objects", "up -d --no-deps worker"]
    indexes = [rig.index(item) for item in order]
    assert indexes == sorted(indexes) and len(set(indexes)) == len(order), rig.calls
    assert rig.calls[rig.index("product_purge apply")].count(f"--expect-plan {SHA}") == 1
    assert f"--objects-sha256 {OBJECTS_SHA}" in rig.calls[rig.index("product_purge delete-objects")]
    dump = next(rig.dumps.glob(f"{INSTANCE}-purge-*"))
    assert (dump / "database.dump").read_text() == "PGDMP-a-dump-of-the-database"
    assert (dump / "plan.txt").read_text().strip() == plan_text().strip()
    assert (dump / "objects.sha256").read_text().strip() == OBJECTS_SHA
    assert f"{dump}" in completed.stdout and "--restore" in completed.stdout
    assert "reset.sh" in completed.stdout


def test_no_worker_service_means_no_worker_is_touched(tmp_path: Path) -> None:
    rig = Rig(tmp_path, worker=False)
    assert rig.run(*COMMON, "--yes-purge-product-data").returncode == 0
    assert not rig.called("stop worker") and not rig.called("up -d --no-deps worker")


def test_the_dump_is_checked_for_room_before_anything_is_stopped(rig: Rig) -> None:
    rig.answers["plan"] = {"stdout": plan_text(db_bytes=10**18)}
    completed = rig.run(*COMMON, "--yes-purge-product-data")
    assert completed.returncode == REFUSED and "KiB free" in completed.stderr
    assert not rig.called("stop worker") and not rig.called("pg_dump") and not list(rig.dumps.glob("*-purge-*"))
    broken = rig.mutant("dump-has-room")
    assert "KiB free" not in broken.run(*COMMON, "--yes-purge-product-data").stderr
    assert broken.called("pg_dump")


@pytest.mark.parametrize(("key", "answer", "says"), (
    ("pg_dump", {"stdout": ""}, "is empty"),
    ("pg_restore_list", {"status": 1}, "could not be read back"),
    ("pg_restore_expand", {"status": 1}, "lists but does not expand"),
), ids=["empty-dump", "unreadable-toc", "truncated-payload"])
def test_an_unverified_dump_stops_the_purge_and_the_worker_comes_back(
    key: str, answer: dict[str, object], says: str, rig: Rig
) -> None:
    rig.answers[key] = answer
    completed = rig.run(*COMMON, "--yes-purge-product-data")
    assert completed.returncode == REFUSED and says in completed.stderr, (completed.stdout, completed.stderr)
    assert not rig.called("product_purge apply") and not rig.called("delete-objects")
    assert rig.index("up -d --no-deps worker") > rig.index("stop worker"), "the worker must be started again"
    broken = rig.mutant("dump-verified")
    assert says not in broken.run(*COMMON, "--yes-purge-product-data").stderr
    assert broken.called("product_purge apply"), "with the guard gone the purge goes ahead on an unverified dump"


def test_a_plan_that_moved_while_the_dump_was_taken_stops_the_purge(rig: Rig) -> None:
    rig.answers["snapshot-objects"] = {"stdout": f"plan-sha256: {'c' * 64}\nobjects-sha256: {OBJECTS_SHA}\n"}
    completed = rig.run(*COMMON, "--yes-purge-product-data")
    assert completed.returncode == REFUSED and "changed while the dump was taken" in completed.stderr
    assert not rig.called("product_purge apply")
    broken = rig.mutant("plan-unchanged")
    assert "changed while the dump was taken" not in broken.run(*COMMON, "--yes-purge-product-data").stderr
    assert broken.called("product_purge apply")


@pytest.mark.parametrize(("step", "answer", "status", "says"), (
    ("snapshot-objects", {"stderr": "REFUSED\n", "status": 3}, REFUSED, "the object copy was refused"),
    ("snapshot-objects", {"stderr": "boom\n", "status": 4}, FAILED, "the object copy failed"),
    ("apply", {"stderr": "REFUSED\n", "status": 3}, REFUSED, "the purge was refused and rolled back"),
    ("apply", {"stderr": "boom\n", "status": 4}, FAILED, "the purge transaction failed"),
), ids=["copy-refused", "copy-failed", "apply-refused", "apply-failed"])
def test_a_step_that_refuses_or_fails_before_the_commit_deletes_no_object(
    step: str, answer: dict[str, object], status: int, says: str, rig: Rig
) -> None:
    rig.answers[step] = answer
    completed = rig.run(*COMMON, "--yes-purge-product-data")
    assert completed.returncode == status, (completed.stdout, completed.stderr)
    assert says in completed.stderr
    assert not rig.called("delete-objects"), "no object is deleted unless the database part committed"
    assert rig.index("up -d --no-deps worker") > rig.index("stop worker")


def test_objects_that_could_not_all_be_deleted_say_the_database_is_committed_and_how_to_finish(rig: Rig) -> None:
    rig.answers["delete-objects"] = {"stderr": "FAILED: 1 object(s) could not be deleted\n", "status": 4}
    completed = rig.run(*COMMON, "--yes-purge-product-data")
    assert completed.returncode == FAILED
    assert "THE DATABASE PART IS COMMITTED" in completed.stderr and "--finish-objects" in completed.stderr
    dump = next(rig.dumps.glob(f"{INSTANCE}-purge-*"))
    assert str(dump) in completed.stderr
    assert rig.index("up -d --no-deps worker") > rig.index("delete-objects")


def test_finish_objects_runs_only_the_deletion_from_the_dumped_list(rig: Rig, tmp_path: Path) -> None:
    dump = tmp_path / "an-earlier-dump"
    dump.mkdir()
    (dump / "product-objects.tsv").write_text("", encoding="utf-8")
    (dump / "objects.sha256").write_text(f"{OBJECTS_SHA}\n", encoding="utf-8")
    completed = rig.run(*COMMON, "--finish-objects", str(dump))
    assert completed.returncode == 0, completed.stderr
    assert len(rig.calls) == 1
    call = rig.calls[0]
    assert "product_purge delete-objects" in call and f"--objects-sha256 {OBJECTS_SHA}" in call
    assert f"-v {dump}:/dump" in call and "--objects-file /dump/product-objects.tsv" in call
    rig.answers["delete-objects"] = {"status": 3, "stderr": "REFUSED\n"}
    assert rig.run(*COMMON, "--finish-objects", str(dump)).returncode == REFUSED
    rig.answers["delete-objects"] = {"status": 4, "stderr": "FAILED\n"}
    assert rig.run(*COMMON, "--finish-objects", str(dump)).returncode == FAILED


def test_the_python_half_runs_inside_the_api_image_from_a_mounted_module_directory(rig: Rig) -> None:
    assert rig.run(*COMMON, "--dry-run").returncode == 0
    call = rig.calls[0]
    assert "run --rm --no-deps -T --user root" in call and "--entrypoint python api -m scripts.recovery.product_purge" in call
    assert f"-v {MODULE_DIR}:/purge/scripts/recovery:ro" in call and "PYTHONPATH=/app/src:/purge" in call


def test_allow_running_reaches_every_python_step(rig: Rig) -> None:
    assert rig.run(*COMMON, "--yes-purge-product-data", "--allow-running").returncode == 0
    for step in ("product_purge plan", "product_purge snapshot-objects", "product_purge apply"):
        assert "--allow-running" in rig.calls[rig.index(step)], step
    rig.log.unlink()
    assert rig.run(*COMMON, "--yes-purge-product-data").returncode == 0
    assert not any("--allow-running" in call for call in rig.calls)


def test_every_guard_in_the_script_has_a_case_here() -> None:
    markers = set(re.findall(r"^# >>> guard: ([a-z-]+)$", SCRIPT.read_text(encoding="utf-8"), re.MULTILINE))
    me = Path(__file__).read_text(encoding="utf-8")
    missing = sorted(name for name in markers if f'"{name}"' not in me)
    assert not missing, f"guards with no case: {missing}"
    assert len(markers) == 15
    for name in markers:
        assert len(re.findall(rf"^# <<< guard: {re.escape(name)}$", SCRIPT.read_text(encoding="utf-8"), re.MULTILINE)) == 1
