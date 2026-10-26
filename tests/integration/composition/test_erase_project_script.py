"""`ERASE-WRAP-01` -- every refusal `infra/deploy/erase-project.sh` makes, and every one shown able to fail.

The convention is `test_purge_product_data_script.py`'s, for the same reason (`R-4`: a guard on a destructive operator
tool that has never been shown to fail is the most expensive kind of green):

1. an invocation that should trip a guard exits **3**, says why, and -- for the guards that run before any connection --
   makes **no `docker` call at all**;
2. the same invocation against a **copy of the script with exactly that guard block deleted** no longer produces that
   refusal. Where the guard sits after a connection the copy is also shown to reach the next destructive step (the
   `--apply` call), which is the harm;
3. a behaviour that is not a guard (the owner's url, the operator's uid, the four mounts, stdin, the resume command, the
   worker restart, the absence of any dump) is pinned by a test **and** by a text mutation of the script that turns it red.

Nothing here can touch a stand: `docker` is a stub on `PATH` that records its arguments (as JSON), the `DATABASE_URL` it
was handed and how much of its standard input it could read, and answers from a file the test writes. The part that needs a database -- the plan, the transaction, the objects -- is
`tests/integration/recovery/test_project_erase.py`; this file drives the wrapper's ORDER, ARGUMENTS and EXIT CODES.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "infra/deploy/erase-project.sh"
MODULE_DIR = ROOT / "scripts/recovery"
MODULES = ("project_erase", "product_purge", "schema_coverage", "blob_reference_audit")

INSTANCE, DATABASE, BUCKET, USER = "an-instance", "the_configured_database", "the-configured-bucket", "the_user"
REFUSED, FAILED, USAGE = 3, 4, 2
PROJECT = "prj_" + "0" * 26
OTHER_PROJECT = "prj_" + "1" * 26
ERASE = "era_" + "2" * 26
SHA = "a" * 64
OTHER_SHA = "b" * 64
ACTOR = "an.administrator@example.org"
REF = "owner mail of 2026-10-26, kept in the release record"
MANIFEST_TEXT = '{"blobs":[],"project":"' + PROJECT + '"}\n'
MANIFEST_SHA = hashlib.sha256(MANIFEST_TEXT.encode()).hexdigest()

#: The application role's url (`DATABASE_URL`) and the owner's (`MIGRATOR_DATABASE_URL`) are DIFFERENT strings here, so a
#: test can tell which one the wrapper hands the one-off container (`PROD-04-DB-ROLES-01`).
APP_URL = f"postgresql+psycopg://the_application_role:an-application-db-password-0001@postgres:5432/{DATABASE}"
MIGRATOR_URL = f"postgresql+psycopg://{USER}:an-owner-db-password-0002@postgres:5432/{DATABASE}"
ENV_FILE = (f"ALPHA_INSTANCE={INSTANCE}\nPOSTGRES_DB={DATABASE}\nPOSTGRES_USER={USER}\nS3_BUCKET={BUCKET}\n"
            f"DATABASE_URL={APP_URL}\nMIGRATOR_DATABASE_URL={MIGRATOR_URL}\n")

COMMON = ("--database", DATABASE, "--bucket", BUCKET)
PLAN = (*COMMON, "--project", PROJECT)
APPLY = (*PLAN, "--apply", "--actor", ACTOR, "--reason", "client_request", "--owner-permission-ref", REF,
         "--plan-sha256", SHA)
RESUME = (*COMMON, "--resume", ERASE, "--actor", ACTOR, "--owner-permission-ref", REF)
TYPED = f"{PROJECT}\n{SHA}\n"

STUB = r'''#!{python}
import json, os, sys
argv = sys.argv[1:]
stdin_bytes = -1 if sys.stdin.isatty() else len(sys.stdin.buffer.read())
with open(os.environ["STUB_LOG"], "a") as log:
    log.write(json.dumps({
        "argv": argv,
        # What the one-off container would be given as DATABASE_URL: compose substitutes the environment of THIS process.
        "database_url": os.environ.get("DATABASE_URL", "<unset>"),
        "stdin_bytes": stdin_bytes,
    }) + "\n")
config = json.load(open(os.environ["STUB_CONFIG"]))
rest = argv
while rest and rest[0] in ("compose", "--env-file", "--file"):
    rest = rest[1:] if rest[0] == "compose" else rest[2:]
if rest[:1] == ["stop"] or (rest[:1] == ["up"] and rest[-1] == "worker"):
    sys.exit(0)
if "scripts.recovery.project_erase" in rest:
    args = rest[rest.index("scripts.recovery.project_erase") + 1:]
    kind = "apply" if "--apply" in args else "resume" if "--resume" in args else "plan"
    entry = config[kind]
    written = entry.get("write_manifest")
    if written:
        mount = next(rest[i + 1][: -len(":/dump")] for i, item in enumerate(rest)
                     if item == "-v" and rest[i + 1].endswith(":/dump"))
        directory = os.path.join(mount, written["erase_id"])
        os.makedirs(directory, exist_ok=True)
        open(os.path.join(directory, "manifest.json"), "w").write(written["text"])
        open(os.path.join(directory, "plan.json"), "w").write("{}")
    sys.stdout.write(entry.get("stdout", ""))
    sys.stdout.flush()
    sys.stderr.write(entry.get("stderr", ""))
    sys.exit(entry.get("status", 0))
sys.stderr.write("docker stub: no answer for: " + " ".join(argv) + "\n")
sys.exit(99)
'''


def plan_text(*, sha: str = SHA, project: str = PROJECT) -> str:
    return (f"erase-project: database {DATABASE} (migration head 0033_ar_v3_cite_stage_id), bucket {BUCKET}\n"
            f"project: {project}\n\n-- rows of the project, by table (every one is deleted) --\n  project  (1 rows)\n"
            f"  total: 7 rows in 3 tables\n\nblobs-exclusive: 2\nblobs-shared: 0\nrows-to-delete: 7\nplan-sha256: {sha}")


def done_text(*, manifest_sha: str = MANIFEST_SHA, erase: str = ERASE) -> str:
    return (f"erase-id: {erase}\nobjects-deleted: 2\n"
            f"erase-project: {PROJECT} erased as {erase}.\nmanifest-sha256: {manifest_sha}\n"
            f"manifest: /dump/{erase}/manifest.json\nplan-sha256: {SHA}\nrows-deleted: 7\n\n"
            "Keep the manifest file with the release record: the database holds only its digest.\n"
            "An erase does not reach:\n  - manual dumps, mirrors and copies on the host\n")


def healthy() -> dict[str, dict[str, object]]:
    written = {"erase_id": ERASE, "text": MANIFEST_TEXT}
    return {
        "plan": {"stdout": plan_text()},
        "apply": {"stdout": done_text(), "write_manifest": written},
        "resume": {"stdout": done_text(), "write_manifest": written},
    }


class Rig:
    """A scratch deployment directory with the script, a compose file, an env file and a stub."""

    def __init__(self, tmp_path: Path, *, script: Path = SCRIPT, worker: bool = True,
                 module_dir: Path = MODULE_DIR, compose: bool = True) -> None:
        self.tmp = tmp_path
        self.deploy = tmp_path / "deploy"
        self.deploy.mkdir(parents=True, exist_ok=True)
        self.script = self.deploy / "erase-project.sh"
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
            block = re.compile(rf"^( *)# >>> guard: {re.escape(guard)}\n.*?^\1# <<< guard: {re.escape(guard)}\n",
                               re.DOTALL | re.MULTILINE)
            source, count = block.subn("", source)
            assert count == 1, f"the guard markers for {guard!r} are not a single block"
        return self._copy_with(source)

    def edited(self, old: str, new: str) -> Rig:
        """The same rig around a copy of the script in which one piece of text is replaced."""
        source = SCRIPT.read_text(encoding="utf-8")
        assert source.count(old) == 1, f"{old!r} is not exactly once in the script"
        return self._copy_with(source.replace(old, new))

    def _copy_with(self, source: str) -> Rig:
        copy = self.tmp / "mutant-script.sh"
        copy.write_text(source, encoding="utf-8")
        compose = self.deploy / "compose.server.yml"
        rig = Rig(self.tmp / "mutant", script=copy, module_dir=self.module_dir, compose=compose.exists(),
                  worker=compose.exists() and "  worker:" in compose.read_text(encoding="utf-8"))
        rig.answers = self.answers
        return rig

    def run(self, *args: str, env: dict[str, str] | None = None, typed: str = "") -> subprocess.CompletedProcess[str]:
        self.config.write_text(json.dumps(self.answers), encoding="utf-8")
        environment = dict(os.environ)
        environment.update(
            PATH=f"{self.bin}{os.pathsep}{environment['PATH']}", ALPHA_ENV_FILE=str(self.env_file),
            ALPHA_DUMP_ROOT=str(self.dumps), ALPHA_ERASE_MODULE_DIR=str(self.module_dir),
            STUB_LOG=str(self.log), STUB_CONFIG=str(self.config))
        environment.update(env or {})
        return subprocess.run(["bash", str(self.script), *args], capture_output=True, text=True, input=typed,
                              env=environment, timeout=120)

    @property
    def records(self) -> list[dict[str, object]]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    @property
    def calls(self) -> list[str]:
        return [" ".join(record["argv"]) for record in self.records]  # type: ignore[arg-type]

    def called(self, needle: str) -> bool:
        return any(needle in call for call in self.calls)

    def index(self, needle: str) -> int:
        return next(i for i, call in enumerate(self.calls) if needle in call)

    def tool_calls(self) -> list[dict[str, object]]:
        return [r for r in self.records if "scripts.recovery.project_erase" in r["argv"]]  # type: ignore[operator]

    def tool_args(self, call: dict[str, object]) -> list[str]:
        argv: list[str] = call["argv"]  # type: ignore[assignment]
        return argv[argv.index("scripts.recovery.project_erase") + 1:]

    def reached_the_erase(self) -> bool:
        return any("--apply" in self.tool_args(call) or "--resume" in self.tool_args(call) for call in self.tool_calls())


@pytest.fixture()
def rig(tmp_path: Path) -> Rig:
    return Rig(tmp_path)


def _env_without(*names: str) -> str:
    return "".join(line for line in ENV_FILE.splitlines(keepends=True) if not line.startswith(tuple(f"{n}=" for n in names)))


# --- the guards that run before any connection ------------------------------------------------

#: (guard, arguments, the refusal's words, typed input, whether the copy without the guard reaches the docker stub)
CASES: tuple[tuple[str, tuple[str, ...], str, bool], ...] = (
    ("known-options", (*PLAN, "--dryrun"), "unrecognised option: --dryrun", False),
    ("known-options", (*COMMON, "--project"), "--project needs a value", False),
    ("one-mode", (*APPLY, "--dry-run"), "were more than one", True),
    ("one-mode", (*RESUME, "--apply"), "were more than one", True),
    ("stop-worker-needs-a-write-mode", (*PLAN, "--stop-worker"), "--stop-worker belongs to --apply or --resume", True),
    ("options-match-the-mode", (*PLAN, "--reason", "test_data"), "belong to --apply (or --resume), and no --apply", True),
    ("options-match-the-mode", (*PLAN, "--plan-sha256", SHA), "belong to --apply (or --resume), and no --apply", True),
    ("options-match-the-mode", (*PLAN, "--actor", ACTOR, "--owner-permission-ref", REF),
     "belong to --apply (or --resume), and no --apply", True),
    ("options-match-the-mode", (*RESUME, "--plan-sha256", SHA), "belong to --apply; a --resume finishes", True),
    ("options-match-the-mode", (*RESUME, "--reason", "test_data"), "belong to --apply; a --resume finishes", True),
    ("names-required", ("--project", PROJECT), "--database and --bucket are both required", False),
    ("project-identity-shape", (*COMMON, "--project", "Kindergarten Sunshine"), "never a name", True),
    ("project-identity-shape", (*COMMON, "--project", "prj_" + "a" * 26), "never a name", True),
    ("project-identity-shape", (*COMMON,), "never a name", True),
    ("project-identity-shape", (*RESUME, "--project", PROJECT), "--project does not go with --resume", True),
    ("erase-identity-shape", (*COMMON, "--resume", "era_nope", "--actor", ACTOR, "--owner-permission-ref", REF),
     "--resume must be an erase identity", True),
    ("erase-identity-shape", (*COMMON, "--resume", PROJECT, "--actor", ACTOR, "--owner-permission-ref", REF),
     "--resume must be an erase identity", True),
    ("actor-required", (*APPLY[:-8], "--reason", "client_request", "--owner-permission-ref", REF, "--plan-sha256", SHA),
     "--actor must be the login", True),
    ("actor-required", (*COMMON, "--resume", ERASE, "--actor", "", "--owner-permission-ref", REF),
     "--actor must be the login", True),
    ("actor-required", (*COMMON, "--resume", ERASE, "--actor", "two words", "--owner-permission-ref", REF),
     "--actor must be the login", True),
    ("reason-closed-list", (*PLAN, "--apply", "--actor", ACTOR, "--reason", "because they asked",
                            "--owner-permission-ref", REF, "--plan-sha256", SHA), "--reason must be one of", True),
    ("reason-closed-list", (*PLAN, "--apply", "--actor", ACTOR, "--owner-permission-ref", REF, "--plan-sha256", SHA),
     "--reason must be one of", True),
    ("owner-permission-ref", (*PLAN, "--apply", "--actor", ACTOR, "--reason", "test_data", "--plan-sha256", SHA),
     "--owner-permission-ref is required", True),
    ("owner-permission-ref", (*PLAN, "--apply", "--actor", ACTOR, "--reason", "test_data", "--plan-sha256", SHA,
                              "--owner-permission-ref", "   "), "--owner-permission-ref is required", True),
    ("owner-permission-ref", (*PLAN, "--apply", "--actor", ACTOR, "--reason", "test_data", "--plan-sha256", SHA,
                              "--owner-permission-ref", "x" * 201), "--owner-permission-ref is required", True),
    ("owner-permission-ref", (*PLAN, "--apply", "--actor", ACTOR, "--reason", "test_data", "--plan-sha256", SHA,
                              "--owner-permission-ref", "line one\nline two"), "--owner-permission-ref is required", True),
    ("owner-permission-ref", (*COMMON, "--resume", ERASE, "--actor", ACTOR), "--owner-permission-ref is required", True),
    ("plan-digest-shape", (*PLAN, "--apply", "--actor", ACTOR, "--reason", "test_data", "--owner-permission-ref", REF),
     "--apply needs --plan-sha256", True),
    ("plan-digest-shape", (*PLAN, "--apply", "--actor", ACTOR, "--reason", "test_data", "--owner-permission-ref", REF,
                           "--plan-sha256", SHA.upper()), "--apply needs --plan-sha256", True),
    ("plan-digest-shape", (*PLAN, "--apply", "--actor", ACTOR, "--reason", "test_data", "--owner-permission-ref", REF,
                           "--plan-sha256", SHA[:63]), "--apply needs --plan-sha256", True),
    ("database-matches", ("--database", "some_other_database", "--bucket", BUCKET, "--project", PROJECT),
     "not the configured alpha database", True),
    ("bucket-matches", ("--database", DATABASE, "--bucket", "some-other-bucket", "--project", PROJECT),
     "not the configured alpha bucket", True),
)


@pytest.mark.parametrize(("guard", "args", "says", "reaches"), CASES, ids=[f"{c[0]}-{i}" for i, c in enumerate(CASES)])
def test_it_refuses_says_why_and_never_calls_docker(guard: str, args: tuple[str, ...], says: str, reaches: bool,
                                                    rig: Rig) -> None:
    completed = rig.run(*args)
    assert completed.returncode == REFUSED, (completed.stdout, completed.stderr)
    assert says in completed.stderr, completed.stderr
    assert not rig.log.exists(), f"{guard} refused, but only after running docker: {rig.calls}"


@pytest.mark.parametrize(("guard", "args", "says", "reaches"), CASES, ids=[f"{c[0]}-{i}" for i, c in enumerate(CASES)])
def test_deleting_the_guard_removes_the_refusal(guard: str, args: tuple[str, ...], says: str, reaches: bool,
                                                rig: Rig) -> None:
    broken = rig.mutant(guard)
    completed = broken.run(*args)
    assert says not in completed.stderr, (
        f"the {guard} guard was deleted and the refusal happened anyway: it was never testing that guard")
    if reaches:
        assert broken.log.exists(), f"with {guard} gone the script should have gone on to the stack: {completed.stderr}"


def test_a_missing_environment_file_is_refused_and_the_guard_can_fail(rig: Rig, tmp_path: Path) -> None:
    args = (*PLAN, "--env-file", str(tmp_path / "not-there.env"))
    completed = rig.run(*args)
    assert completed.returncode == REFUSED and "missing or unreadable" in completed.stderr and not rig.log.exists()
    broken = rig.mutant("env-file-present").run(*args)
    assert "missing or unreadable" not in broken.stderr


def test_a_half_configured_instance_is_refused_and_the_guard_can_fail(rig: Rig) -> None:
    rig.env_file.write_text(f"POSTGRES_DB={DATABASE}\n", encoding="utf-8")
    completed = rig.run(*PLAN)
    assert completed.returncode == REFUSED and "names no ALPHA_INSTANCE" in completed.stderr and not rig.log.exists()
    broken = rig.mutant("instance-configured")
    broken.env_file.write_text(f"POSTGRES_DB={DATABASE}\n", encoding="utf-8")
    assert "names no ALPHA_INSTANCE" not in broken.run(*PLAN).stderr


@pytest.mark.parametrize("line", [
    "", "MIGRATOR_DATABASE_URL=\n", "MIGRATOR_DATABASE_URL=postgresql://u:p@postgres:5432/d\n",
    "MIGRATOR_DATABASE_URL=not a url\n",
], ids=["absent", "empty", "wrong-scheme", "not-a-url"])
def test_a_missing_or_malformed_owner_url_is_refused_and_the_guard_can_fail(rig: Rig, line: str) -> None:
    """`PROD-04`: the erase deletes append-only rows, so the one-off container is handed the OWNER's url; an environment
    that has none is refused before any connection, in a sentence, and not by the tool's `owner-may-write` after one."""
    rig.env_file.write_text(_env_without("MIGRATOR_DATABASE_URL") + line, encoding="utf-8")
    completed = rig.run(*PLAN)
    assert completed.returncode == REFUSED and "[migrator_url_unset]" in completed.stderr, completed.stderr
    assert not rig.log.exists(), "the refusal came after docker was touched"
    cut = rig.mutant("migrator-url-configured")
    cut.env_file.write_text(_env_without("MIGRATOR_DATABASE_URL") + line, encoding="utf-8")
    assert "[migrator_url_unset]" not in cut.run(*PLAN).stderr


def test_a_missing_compose_file_is_refused_and_the_guard_can_fail(tmp_path: Path) -> None:
    bare = Rig(tmp_path / "a", compose=False)
    completed = bare.run(*PLAN)
    assert completed.returncode == REFUSED and "compose.server.yml is missing" in completed.stderr
    assert not bare.log.exists()
    broken = Rig(tmp_path / "b").mutant("compose-file-present")
    (broken.deploy / "compose.server.yml").unlink()
    assert "compose.server.yml is missing" not in broken.run(*PLAN).stderr


@pytest.mark.parametrize("absent", MODULES)
def test_a_checkout_without_one_of_the_four_modules_is_refused_and_the_guard_can_fail(absent: str, tmp_path: Path) -> None:
    partial = tmp_path / "partial"
    partial.mkdir()
    for module in MODULES:
        if module != absent:
            (partial / f"{module}.py").write_text("", encoding="utf-8")
    bare = Rig(tmp_path / "rig", module_dir=partial)
    completed = bare.run(*PLAN)
    assert completed.returncode == REFUSED and f"lacks {absent}.py" in completed.stderr, completed.stderr
    assert not bare.log.exists()
    assert f"lacks {absent}.py" not in bare.mutant("modules-present").run(*PLAN).stderr


def test_a_dump_directory_it_cannot_write_is_refused_before_the_stack_is_touched_and_the_guard_can_fail(
    rig: Rig, tmp_path: Path
) -> None:
    """The directory is a regular file where `erasures` should be, which `mkdir` cannot turn into a directory whoever
    the operator is (a mode bit would prove nothing to a root-run test)."""
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    (blocked / "erasures").write_text("in the way", encoding="utf-8")
    for args in (APPLY, RESUME):
        completed = rig.run(*args, env={"ALPHA_DUMP_ROOT": str(blocked)}, typed=TYPED)
        assert completed.returncode == REFUSED and "is not a writable directory" in completed.stderr, completed.stderr
        assert not rig.log.exists()
    broken = rig.mutant("dump-dir-writable")
    completed = broken.run(*APPLY, env={"ALPHA_DUMP_ROOT": str(blocked)}, typed=TYPED)
    assert "is not a writable directory" not in completed.stderr
    assert broken.reached_the_erase(), "with the guard gone the erase starts although nothing can be recorded"


def test_a_dry_run_does_not_need_the_dump_directory(rig: Rig, tmp_path: Path) -> None:
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    (blocked / "erasures").write_text("in the way", encoding="utf-8")
    assert rig.run(*PLAN, env={"ALPHA_DUMP_ROOT": str(blocked)}).returncode == 0


def test_help_is_a_usage_error_with_its_own_status(rig: Rig) -> None:
    completed = rig.run("--help")
    assert completed.returncode == USAGE and "usage: erase-project.sh" in completed.stderr
    assert "NO DUMP IS TAKEN" in completed.stderr
    assert not rig.log.exists()


# --- the dry run is the default ---------------------------------------------------------------


def test_with_no_mode_option_it_is_the_dry_run_and_does_one_read_only_call(rig: Rig) -> None:
    completed = rig.run(*PLAN)
    assert completed.returncode == 0, completed.stderr
    assert len(rig.calls) == 1 and rig.reached_the_erase() is False
    args = rig.tool_args(rig.tool_calls()[0])
    assert args == ["--database", DATABASE, "--bucket", BUCKET, "--project", PROJECT]
    assert f"plan-sha256: {SHA}" in completed.stdout and "dry run. NOTHING ABOVE WAS CHANGED" in completed.stdout
    assert f"--plan-sha256 {SHA}" in completed.stdout, "the dry run tells the operator what the apply needs"
    assert not rig.dumps.exists(), "a dry run creates nothing on disk"
    mounts = [item for item in rig.tool_calls()[0]["argv"] if str(item).endswith(":/dump")]  # type: ignore[union-attr]
    assert mounts == [], "a dry run mounts no writable directory"
    assert rig.run(*PLAN, "--dry-run").returncode == 0


def test_a_project_that_was_erased_already_is_nothing_to_do_and_asks_nothing(rig: Rig) -> None:
    rig.answers["plan"] = {"stdout": f"erase-project: {PROJECT} was erased as {ERASE} and that erase is complete; "
                                     "nothing to do.\n"}
    completed = rig.run(*APPLY)
    assert completed.returncode == 0, completed.stderr
    assert "nothing to do" in completed.stdout and len(rig.calls) == 1 and "retype" not in completed.stdout


# --- the plan that did not complete -----------------------------------------------------------


@pytest.mark.parametrize(("plan", "status", "says"), (
    ({"stdout": "", "stderr": "project_erase: REFUSED: no such project\n", "status": 3}, REFUSED, "the plan was refused"),
    ({"stdout": "", "stderr": "project_erase: FAILED: connection refused\n", "status": 4}, FAILED, "the plan failed"),
    ({"stdout": "no digest on this screen\n", "status": 0}, FAILED, "the plan printed no digest"),
), ids=["refused", "failed", "no-digest"])
def test_a_plan_that_did_not_complete_stops_before_anything_is_erased(
    plan: dict[str, object], status: int, says: str, rig: Rig
) -> None:
    rig.answers["plan"] = plan
    for args in (PLAN, APPLY):
        rig.log.unlink(missing_ok=True)
        completed = rig.run(*args, typed=TYPED)
        assert completed.returncode == status, (args, completed.stdout, completed.stderr)
        assert says in completed.stderr
        assert not rig.reached_the_erase() and not rig.called("stop worker")


@pytest.mark.parametrize("plan", (
    {"stdout": "", "stderr": "REFUSED\n", "status": 3},
    {"stdout": "", "stderr": "FAILED\n", "status": 4},
    {"stdout": "no digest on this screen\n", "status": 0},
), ids=["refused", "failed", "no-digest"])
def test_the_preflight_guard_is_shown_able_to_fail(plan: dict[str, object], rig: Rig) -> None:
    """With a plan that gave no digest the later checks have nothing to compare, so they go too: the harm is an erase."""
    rig.answers["plan"] = plan
    broken = rig.mutant("preflight-ran", "plan-approved", "retyped-confirmation")
    completed = broken.run(*APPLY, typed=TYPED)
    assert "the plan was refused" not in completed.stderr and "the plan printed no digest" not in completed.stderr
    assert broken.reached_the_erase(), "with the guard gone the script goes on to erase on a plan it never read"


# --- the apply --------------------------------------------------------------------------------


def test_the_order_is_plan_then_retype_then_apply_with_no_dump_anywhere(rig: Rig) -> None:
    completed = rig.run(*APPLY, typed=TYPED)
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    plan_call, apply_call = rig.tool_calls()
    assert rig.tool_args(plan_call) == ["--database", DATABASE, "--bucket", BUCKET, "--project", PROJECT]
    assert rig.tool_args(apply_call) == [
        "--database", DATABASE, "--bucket", BUCKET, "--project", PROJECT, "--apply", "--plan-sha256", SHA,
        "--actor", ACTOR, "--reason", "client_request", "--owner-permission-ref", REF, "--dump-dir", "/dump"]
    assert "retype the project id" in completed.stdout and "retype the plan digest" in completed.stdout
    # ... and nothing but the module was ever run: no dump, no restore, no mirror, no listing of the bucket.
    assert len(rig.calls) == 2, rig.calls
    assert not any(word in call for call in rig.calls for word in ("pg_dump", "pg_restore", "mirror", "exec"))


def test_the_apply_prints_the_manifest_the_digest_the_queries_and_what_it_did_not_reach(rig: Rig) -> None:
    completed = rig.run(*APPLY, typed=TYPED)
    out = completed.stdout
    manifest = rig.dumps / "erasures" / ERASE / "manifest.json"
    assert manifest.read_text(encoding="utf-8") == MANIFEST_TEXT
    assert f"manifest: {manifest}" in out and "/dump/" not in out.replace("--dump-dir", ""), out
    assert f"manifest-sha256 {MANIFEST_SHA} (verified against the file)" in out
    assert "select count(*) from blob where state = 'erasure_pending'" in out
    assert f"select count(*) from project where project_uid = '{PROJECT}'" in out
    assert f"aggregate_id = '{ERASE}'" in out
    assert "NO DUMP WAS TAKEN" in out and "still holds the project" in out
    assert "An erase does not reach:" in out, "the module's closing list reaches the operator"
    assert f"psql -U {USER} -d {DATABASE}" in out


def test_the_directory_is_the_operators_0700_and_the_container_runs_as_the_operators_uid(rig: Rig) -> None:
    rig.run(*APPLY, typed=TYPED)
    directory = rig.dumps / "erasures"
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    call = rig.tool_calls()[1]["argv"]
    assert call[call.index("--user") + 1] == f"{os.getuid()}:{os.getgid()}", call  # type: ignore[index]
    assert "root" not in call[call.index("--user") + 1]  # type: ignore[index]
    assert "-v" in call and f"{directory}:/dump" in call, "the dump directory is mounted writable (no :ro)"  # type: ignore[operator]
    assert next(c for c in call if str(c).endswith(":/dump")) == f"{directory}:/dump"  # type: ignore[union-attr]


def test_the_four_modules_are_mounted_read_only_and_nothing_else_of_the_checkout(rig: Rig) -> None:
    rig.run(*APPLY, typed=TYPED)
    for call in rig.tool_calls():
        argv = [str(item) for item in call["argv"]]  # type: ignore[union-attr]
        mounts = sorted(argv[i + 1] for i, item in enumerate(argv) if item == "-v" and ":/purge/" in argv[i + 1])
        assert mounts == sorted(f"{MODULE_DIR}/{m}.py:/purge/scripts/recovery/{m}.py:ro" for m in MODULES), mounts
        assert "PYTHONPATH=/app/src:/purge" in argv and "-e" in argv
        at = argv.index("--entrypoint")
        assert argv[at + 1 : at + 5] == ["python", "api", "-m", "scripts.recovery.project_erase"]
        assert "run" in argv and "--rm" in argv and "--no-deps" in argv and "-T" in argv


AMBIENT = "postgresql+psycopg://ambient:ambient@elsewhere:5432/ambient"


def _pg_in_argv(rig: Rig) -> bool:
    return any(str(item).startswith("PG") or "=PG" in str(item) for r in rig.tool_calls() for item in r["argv"])  # type: ignore[union-attr]


def test_the_python_half_is_handed_the_owners_url_at_every_step_and_never_the_applications(rig: Rig) -> None:
    """`api`'s own `DATABASE_URL` is the application role's, which the tool refuses; the owner's goes in the environment
    of the `docker compose` process, an ambient `DATABASE_URL` is overridden, no `PG*` variable is passed to the container
    and no command line carries a url or a password."""
    env = {"DATABASE_URL": AMBIENT, "PGHOST": "elsewhere", "PGPASSWORD": "ambient-secret", "PGSERVICE": "x"}
    assert rig.run(*APPLY, env=env, typed=TYPED).returncode == 0
    assert [r["database_url"] for r in rig.tool_calls()] == [MIGRATOR_URL, MIGRATOR_URL]
    assert APP_URL not in "".join(str(r["database_url"]) for r in rig.records)
    assert not _pg_in_argv(rig)
    for record in rig.tool_calls():
        argv = [str(item) for item in record["argv"]]  # type: ignore[union-attr]
        assert not any("postgresql+psycopg://" in item or "an-owner-db-password-0002" in item for item in argv), argv
        assert not any("ambient-secret" in item for item in argv), argv


def test_the_owner_url_assertion_can_fail_without_the_environment_prefix(rig: Rig) -> None:
    broken = rig.edited('DATABASE_URL="$MIGRATOR_URL" compose run', "compose run")
    assert broken.run(*APPLY, env={"DATABASE_URL": AMBIENT}, typed=TYPED).returncode == 0
    assert {r["database_url"] for r in broken.tool_calls()} == {AMBIENT}


def test_the_pg_variable_assertion_can_fail(rig: Rig) -> None:
    broken = rig.edited("-e PYTHONPATH=/app/src:/purge", "-e PYTHONPATH=/app/src:/purge -e PGHOST=postgres")
    assert broken.run(*APPLY, typed=TYPED).returncode == 0
    assert _pg_in_argv(broken)


def test_docker_never_reads_the_answers_the_operator_types(rig: Rig) -> None:
    """`docker compose run` forwards stdin to the container, so a pipe feeding the retype would be eaten by the plan
    step: the stub reads whatever stdin it is given, and must be given none."""
    assert rig.run(*APPLY, typed=TYPED).returncode == 0
    assert [r["stdin_bytes"] for r in rig.records] == [0, 0]
    broken = rig.edited("--entrypoint python api -m scripts.recovery.project_erase \"$@\" </dev/null",
                        "--entrypoint python api -m scripts.recovery.project_erase \"$@\"")
    completed = broken.run(*APPLY, typed=TYPED)
    assert completed.returncode == REFUSED and "what was retyped is not the project" in completed.stderr
    assert not broken.reached_the_erase()


def test_the_option_order_does_not_matter(rig: Rig) -> None:
    shuffled = ("--plan-sha256", SHA, "--apply", "--owner-permission-ref", REF, "--reason", "client_request",
                "--actor", ACTOR, "--project", PROJECT, "--bucket", BUCKET, "--database", DATABASE)
    assert rig.run(*shuffled, typed=TYPED).returncode == 0 and rig.reached_the_erase()


# --- the plan the operator approved, and what they retype -------------------------------------


def test_a_plan_that_changed_since_it_was_approved_is_refused_and_the_guard_can_fail(rig: Rig) -> None:
    rig.answers["plan"] = {"stdout": plan_text(sha=OTHER_SHA)}
    completed = rig.run(*APPLY, typed=f"{PROJECT}\n{OTHER_SHA}\n")
    assert completed.returncode == REFUSED and "not the plan you approved" in completed.stderr, completed.stderr
    assert OTHER_SHA in completed.stderr and SHA in completed.stderr
    assert not rig.reached_the_erase() and "retype" not in completed.stdout, "it must not even ask"
    broken = rig.mutant("plan-approved")
    completed = broken.run(*APPLY, typed=f"{PROJECT}\n{OTHER_SHA}\n")
    assert "not the plan you approved" not in completed.stderr
    assert broken.reached_the_erase(), "with the guard gone the apply is sent with a digest the project no longer has"


@pytest.mark.parametrize("typed", (
    "", f"{PROJECT}\n", f"{OTHER_PROJECT}\n{SHA}\n", f"{PROJECT}\n{OTHER_SHA}\n", f"{SHA}\n{PROJECT}\n",
    f"{PROJECT} \n{SHA}\n", "\n\n",
), ids=["nothing", "no-digest", "other-project", "other-digest", "swapped", "trailing-space", "blank-lines"])
def test_what_is_retyped_must_be_the_project_and_the_digest_and_the_guard_can_fail(typed: str, rig: Rig) -> None:
    completed = rig.run(*APPLY, typed=typed)
    assert completed.returncode == REFUSED and "what was retyped is not the project" in completed.stderr, completed.stderr
    assert not rig.reached_the_erase() and not rig.called("stop worker")
    broken = rig.mutant("retyped-confirmation")
    completed = broken.run(*APPLY, typed=typed)
    assert "what was retyped is not the project" not in completed.stderr
    assert broken.reached_the_erase(), "with the guard gone the erase runs on an answer nobody gave"


def test_the_answers_come_from_the_keyboard_not_from_the_command_line(rig: Rig) -> None:
    completed = rig.run(*APPLY, "--yes")
    assert completed.returncode == REFUSED and "unrecognised option: --yes" in completed.stderr
    completed = rig.run(*APPLY)  # no input at all: an end of input is no answer
    assert completed.returncode == REFUSED and "retyped" in completed.stderr and not rig.reached_the_erase()


# --- a stop after the commit ------------------------------------------------------------------


def _resume_line(stderr: str) -> str:
    return next(line.strip() for line in stderr.splitlines() if "--resume" in line and line.strip().startswith(("ALPHA_DUMP_ROOT", "/")))


@pytest.mark.parametrize("status", (FAILED, REFUSED))
def test_a_stop_after_the_commit_is_a_failure_that_prints_the_erase_id_and_the_exact_resume_command(
    status: int, rig: Rig
) -> None:
    """A module status of 3 after the commit is still a failure here: 3 promises that nothing was changed."""
    rig.answers["apply"] = {"stdout": f"erase-id: {ERASE}\n", "stderr": "project_erase: FAILED: 1 object could not be deleted\n",
                            "status": status}
    completed = rig.run(*APPLY, typed=TYPED)
    assert completed.returncode == FAILED, (completed.stdout, completed.stderr)
    assert "THE DATABASE PART OF THE ERASE IS COMMITTED" in completed.stderr and ERASE in completed.stderr
    assert f"{rig.dumps}/erasures/{ERASE}/" in completed.stderr, "where the plan and the manifest are"
    # The line is a command the operator can paste: run it and the wrapper resumes that erase, with the same words.
    tokens = shlex.split(_resume_line(completed.stderr))
    env = dict(token.split("=", 1) for token in tokens[:1] if re.match(r"^[A-Z_]+=", token))
    command = tokens[len(env):]
    assert command[0].endswith("erase-project.sh")
    assert env == {"ALPHA_DUMP_ROOT": str(rig.dumps)}
    rig.log.unlink()
    rig.answers["resume"] = {"stdout": done_text(), "write_manifest": {"erase_id": ERASE, "text": MANIFEST_TEXT}}
    resumed = rig.run(*command[1:], env=env)
    assert resumed.returncode == 0, resumed.stderr
    assert rig.tool_args(rig.tool_calls()[0]) == [
        "--database", DATABASE, "--bucket", BUCKET, "--resume", ERASE, "--actor", ACTOR,
        "--owner-permission-ref", REF, "--dump-dir", "/dump"]


def test_the_resume_hint_is_shown_able_to_fail(rig: Rig) -> None:
    rig.answers["apply"] = {"stdout": f"erase-id: {ERASE}\n", "stderr": "boom\n", "status": FAILED}
    assert "--resume" in rig.run(*APPLY, typed=TYPED).stderr
    broken = rig.edited('"  $(resume_command "$erase_id")" \\\n', '"  (no command)" \\\n')
    assert "--resume" not in broken.run(*APPLY, typed=TYPED).stderr


@pytest.mark.parametrize(("answer", "status", "says"), (
    ({"stderr": "project_erase: REFUSED: the plan changed\n", "status": 3}, REFUSED, "the erase was refused"),
    ({"stderr": "project_erase: FAILED: connection reset\n", "status": 4}, FAILED, "the erase failed"),
), ids=["refused", "failed"])
def test_a_stop_before_the_commit_says_nothing_was_changed_and_offers_no_resume(
    answer: dict[str, object], status: int, says: str, rig: Rig
) -> None:
    rig.answers["apply"] = answer
    completed = rig.run(*APPLY, typed=TYPED)
    assert completed.returncode == status and says in completed.stderr
    assert "COMMITTED" not in completed.stderr and "--resume" not in completed.stderr
    assert (status == REFUSED) == ("Nothing was changed" in completed.stderr)


def test_an_earlier_unfinished_erase_is_named_with_the_command_that_finishes_it(rig: Rig) -> None:
    rig.answers["plan"] = {"stdout": "", "status": 3, "stderr": (
        f"project_erase: REFUSED: {PROJECT} has no rows left and {ERASE} is not complete: resume it with "
        f"--resume {ERASE}. Nothing was touched.\n")}
    completed = rig.run(*APPLY, typed=TYPED)
    assert completed.returncode == REFUSED and "an earlier erase of this project did not finish" in completed.stderr
    assert f"--resume {ERASE}" in completed.stderr and "<admin login>" not in completed.stderr
    assert not rig.reached_the_erase()


# --- a lock that could not be taken, and the worker -------------------------------------------

LOCK = {"stdout": "", "stderr": "project_erase: REFUSED: could not lock the tables within 15s: something is still writing. "
                                "Nothing was touched.\n", "status": 3}


def test_could_not_lock_offers_the_stop_worker_option_and_names_what_else_may_write(rig: Rig) -> None:
    rig.answers["apply"] = LOCK
    completed = rig.run(*APPLY, typed=TYPED)
    assert completed.returncode == REFUSED and "--stop-worker" in completed.stderr
    assert "stop api web" not in completed.stderr
    assert not rig.called("stop worker")
    again = rig.run(*APPLY, "--stop-worker", typed=TYPED)
    assert again.returncode == REFUSED and "stop api web" in again.stderr and "up -d --no-deps api web" in again.stderr


def test_the_worker_is_stopped_for_the_apply_only_and_started_again_after_it(rig: Rig) -> None:
    completed = rig.run(*APPLY, "--stop-worker", typed=TYPED)
    assert completed.returncode == 0, completed.stderr
    plan_i = rig.index("scripts.recovery.project_erase")
    stop_i, apply_i, up_i = rig.index("stop worker"), rig.index("--apply"), rig.index("up -d --no-deps worker")
    assert plan_i < stop_i < apply_i < up_i, rig.calls


@pytest.mark.parametrize(("answer", "status"), (
    ({"stderr": "REFUSED\n", "status": 3}, REFUSED),
    ({"stderr": "FAILED\n", "status": 4}, FAILED),
    ({"stdout": f"erase-id: {ERASE}\n", "stderr": "FAILED\n", "status": 4}, FAILED),
), ids=["refused", "failed", "failed-after-commit"])
def test_the_worker_comes_back_whatever_the_apply_did(answer: dict[str, object], status: int, rig: Rig) -> None:
    rig.answers["apply"] = answer
    completed = rig.run(*APPLY, "--stop-worker", typed=TYPED)
    assert completed.returncode == status
    assert rig.index("up -d --no-deps worker") > rig.index("stop worker")
    broken = rig.edited("trap cleanup EXIT\n", "")
    assert broken.run(*APPLY, "--stop-worker", typed=TYPED).returncode == status
    assert broken.called("stop worker") and not broken.called("up -d --no-deps worker"), (
        "without the trap a refusal leaves the worker stopped")


def test_no_worker_service_means_no_worker_is_touched(tmp_path: Path) -> None:
    bare = Rig(tmp_path, worker=False)
    assert bare.run(*APPLY, "--stop-worker", typed=TYPED).returncode == 0
    assert not bare.called("stop worker") and not bare.called("up -d --no-deps worker")


def test_without_the_option_the_worker_is_left_alone(rig: Rig) -> None:
    assert rig.run(*APPLY, typed=TYPED).returncode == 0
    assert not rig.called("stop worker") and not rig.called("up -d")


# --- the manifest on disk is the one the database holds ---------------------------------------


@pytest.mark.parametrize(("manifest_sha", "text"), (
    (OTHER_SHA, MANIFEST_TEXT), (MANIFEST_SHA, MANIFEST_TEXT + " "), ("not-a-digest", MANIFEST_TEXT),
), ids=["digest-differs", "file-differs", "no-digest"])
def test_a_manifest_that_does_not_hash_to_the_journalled_digest_is_a_failure_and_the_guard_can_fail(
    manifest_sha: str, text: str, rig: Rig
) -> None:
    rig.answers["apply"] = {"stdout": done_text(manifest_sha=manifest_sha), "write_manifest": {"erase_id": ERASE, "text": text}}
    completed = rig.run(*APPLY, typed=TYPED)
    assert completed.returncode == FAILED and "THE ERASE COMPLETED but the manifest on disk" in completed.stderr
    assert "verified against the file" not in completed.stdout
    broken = rig.mutant("manifest-verified")
    completed = broken.run(*APPLY, typed=TYPED)
    assert "THE ERASE COMPLETED but the manifest on disk" not in completed.stderr
    assert completed.returncode == 0 and "verified against the file" in completed.stdout, (
        "with the guard gone the operator is told to keep a file that was never compared with anything")


def test_a_manifest_that_is_missing_is_a_failure(rig: Rig) -> None:
    rig.answers["apply"] = {"stdout": done_text()}  # the stub writes no file
    completed = rig.run(*APPLY, typed=TYPED)
    assert completed.returncode == FAILED and "<unreadable>" in completed.stderr


# --- --resume ---------------------------------------------------------------------------------


def test_a_resume_runs_the_module_once_asks_nothing_and_verifies_the_manifest(rig: Rig) -> None:
    completed = rig.run(*RESUME)
    assert completed.returncode == 0, completed.stderr
    assert len(rig.tool_calls()) == 1, "a resume has no plan step"
    assert rig.tool_args(rig.tool_calls()[0]) == [
        "--database", DATABASE, "--bucket", BUCKET, "--resume", ERASE, "--actor", ACTOR,
        "--owner-permission-ref", REF, "--dump-dir", "/dump"]
    assert "retype" not in completed.stdout and f"manifest-sha256 {MANIFEST_SHA} (verified" in completed.stdout
    assert [r["database_url"] for r in rig.tool_calls()] == [MIGRATOR_URL]


def test_a_resume_of_a_finished_erase_says_so_and_changes_nothing(rig: Rig) -> None:
    rig.answers["resume"] = {"stdout": f"erase-project: {ERASE} is already complete; nothing to do.\n"}
    completed = rig.run(*RESUME)
    assert completed.returncode == 0 and "already complete" in completed.stdout and "verified against" not in completed.stdout


def test_a_resume_that_stops_again_prints_the_same_command(rig: Rig) -> None:
    rig.answers["resume"] = {"stdout": f"erase-id: {ERASE}\n", "stderr": "FAILED: still no\n", "status": FAILED}
    completed = rig.run(*RESUME)
    assert completed.returncode == FAILED and f"--resume {ERASE}" in completed.stderr
    tokens = shlex.split(_resume_line(completed.stderr))
    assert tokens[tokens.index("--owner-permission-ref") + 1] == REF, "the reference survives the shell quoting"
    assert tokens[tokens.index("--actor") + 1] == ACTOR


def test_a_resume_can_stop_the_worker_too(rig: Rig) -> None:
    assert rig.run(*RESUME, "--stop-worker").returncode == 0
    assert rig.index("stop worker") < rig.index("--resume") < rig.index("up -d --no-deps worker")


# --- what this script does not do -------------------------------------------------------------


def test_the_script_takes_no_dump_and_no_mirror_and_the_check_can_fail(rig: Rig) -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    for word in ("pg_dump", "pg_restore", "snapshot-objects", "objects.attrs", "reset.sh", "mc mirror"):
        assert word not in code, f"{word!r} appears in the code of a script that must take no dump"
    assert "NO DUMP" in text
    broken = rig.edited('echo "erase-project.sh: erasing (one transaction',
                        'compose exec -T postgres pg_dump --format=custom --dbname "$DATABASE" > /dev/null\n'
                        'echo "erase-project.sh: erasing (one transaction')
    broken.run(*APPLY, typed=TYPED)  # the stub has no answer for a dump, so the script stops there
    assert broken.called("pg_dump"), "the call recorder sees a dump if one is taken"
    assert rig.run(*APPLY, typed=TYPED).returncode == 0 and not rig.called("pg_dump")


def test_the_copy_key_file_list_does_not_gain_this_script() -> None:
    """Runbook section 13 lists the five files the copy key installs. The erase is an interactive act of an
    administrator with the owner's permission and must not be reachable from an unattended key, so it is not one."""
    runbook = (ROOT / "docs/program/DEPLOYMENT_RUNBOOK.md").read_text(encoding="utf-8")
    listing = re.search(r"for f in (copy-serve\.sh [^;]+); do", runbook)
    assert listing is not None
    assert "erase-project.sh" not in listing.group(1)
    copy_serve = (ROOT / "infra/deploy/copy-serve.sh").read_text(encoding="utf-8")
    assert "erase-project" not in copy_serve


def test_the_script_is_executable_and_in_the_deploy_directory() -> None:
    assert SCRIPT.exists() and os.access(SCRIPT, os.X_OK)
    assert SCRIPT.parent == ROOT / "infra/deploy"


def test_every_guard_in_the_script_has_a_case_here() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    markers = set(re.findall(r"^ *# >>> guard: ([a-z-]+)$", text, re.MULTILINE))
    me = Path(__file__).read_text(encoding="utf-8")
    missing = sorted(name for name in markers if f'"{name}"' not in me)
    assert not missing, f"guards with no case: {missing}"
    assert len(markers) == 23, sorted(markers)
    for name in markers:
        assert len(re.findall(rf"^ *# <<< guard: {re.escape(name)}$", text, re.MULTILINE)) == 1
