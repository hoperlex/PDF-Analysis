"""The on-host norms import of `first-install.sh` (stage 5), driven through the REAL `receive-bundle.sh`, `copy-serve.sh`,
`push-bundle.sh` and `lib/forced-command.sh`, exactly as the install runs them: no SSH, the verb in `SSH_ORIGINAL_COMMAND`, the
tar of the bundle on the receiver's standard input, the account root.

`STAND-NORMS-IMPORT-RUNBOOK-01.md` marked this on-host variant UNVERIFIED. This is the first time it runs: the guards of both
scripts, the copy record, the import lock and the detached importer are real; the only stand-ins are `docker` (a recorder that
answers `compose ps/stop/start/exec/run` from a state file, and runs the "importer" as a short-lived process) and the loopback
API (`fake_stack.py`). What that proves: **the scripts need no change to be driven this way**, and the order of the verbs, the
resumability and the STOP codes. What it cannot prove: the real importer, the real PostgreSQL fingerprint, the real MinIO.

What is held:

* a whole run: receive, waiver, import, report, resume, designation; the record ends `closed`, the writers are started again
  and the snapshot is current;
* the verbs go in the runbook's order and the writers are stopped from the waiver until `resume`;
* a rerun after a complete run does nothing; a rerun after an interrupted one continues (no second receive, no second waiver);
* a refusal of the importer, a report that differs, a bundle that does not verify and too little disk are each their own STOP,
  and the record stays open when the report differs (the owner decides before the writers are resumed).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DEPLOY = ROOT / "infra" / "deploy"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


fake_stack = _load("first_install_fake_stack_for_norms_tests", Path(__file__).with_name("fake_stack.py"))
fia = _load("first_install_api_for_norms_tests", DEPLOY / "lib" / "first_install_api.py")

CONTENT_KEY = fake_stack.CONTENT_KEY
FINGERPRINT = "".join(f"{table}|{rows}|{hashlib.sha256(table.encode()).hexdigest()}\n"
                      for table, rows in (("alembic_version", 1), ("app_user", 2), ("blob", 3)))

DOCKER_STUB = r'''#!/usr/bin/env python3
"""A docker that answers what receive-bundle.sh and copy-serve.sh ask, from a JSON state file."""
import json, os, sys, time

argv = sys.argv[1:]
state_path = os.environ["STUB_STATE"] + "/docker.json"
with open(os.environ["STUB_STATE"] + "/docker.log", "a") as handle:
    handle.write(json.dumps(argv) + "\n")
state = json.load(open(state_path))


def save():
    json.dump(state, open(state_path, "w"))


if argv[:1] == ["info"]:
    if argv[1:2] == ["--format"]:
        print(os.environ["STUB_DOCKER_ROOT"])
    sys.exit(0)
if argv[:1] != ["compose"]:
    sys.exit(0)
position = 1
while position < len(argv) and argv[position] in ("--env-file", "--file"):
    position += 2
sub, rest = argv[position], argv[position + 1:]
if sub == "ps":
    if rest[-1] in state["running"]:
        print("cid-" + rest[-1])
    sys.exit(0)
if sub == "stop":
    state["running"] = [s for s in state["running"] if s not in rest]
    save()
    sys.exit(0)
if sub == "start":
    for service in rest:
        if service not in state["running"]:
            state["running"].append(service)
    save()
    sys.exit(0)
if sub == "exec":
    command = rest[2:]
    if command[0] == "psql":
        if "--command" in command:
            sql = command[command.index("--command") + 1]
            print("0" if "rejected" in sql else "0029_routing_refusal_codes")
        else:
            sys.stdin.read()
            sys.stdout.write(state["fingerprint"])
    sys.exit(0)
if sub == "run" and "auditmanager.norms.bundle" in rest:
    action = rest[rest.index("auditmanager.norms.bundle") + 1]
    time.sleep(float(state.get("importer_seconds", 0.6)))
    if action == "import":
        print("bundle: verified")
        print("importer stand-in finished")
        sys.exit(int(state.get("import_exit", 0)))
    if action == "report":
        print("report: full match" if int(state.get("report_exit", 0)) == 0 else "report: DIFFERS")
        sys.exit(int(state.get("report_exit", 0)))
sys.exit(0)
'''
DF_STUB = "#!/usr/bin/env bash\nprintf 'Avail\\n%s\\n' \"${STUB_DF_BYTES:-200000000000}\"\n"


def _make_bundle(parent: Path, *, tamper: bool = False) -> Path:
    files = {"manifest.json": b'{"snapshot": "stand-in"}\n', "objects/aa/one.pdf": b"%PDF-1.7 one\n" * 50,
             "objects/bb/two.pdf": b"%PDF-1.7 two\n" * 70}
    listing = "".join(f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(files.items()))
    digest = hashlib.sha256(listing.encode()).hexdigest()
    bundle = parent / f"{CONTENT_KEY}+{digest}"
    for name, data in files.items():
        path = bundle / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data + (b"X" if tamper and name == "manifest.json" else b""))
    (bundle / "SHA256SUMS").write_text(listing)
    return bundle


class NormsRig:
    def __init__(self, tmp_path: Path) -> None:
        self.tmp = tmp_path
        self.repo = tmp_path / "clone"
        self.bin = tmp_path / "bin"
        self.stub = tmp_path / "stubstate"
        self.copy_dir = tmp_path / "srv-copy"
        self.staging = tmp_path / "srv-bundles"
        self.secret_dir = tmp_path / "root-home"
        for directory in (self.bin, self.stub, self.secret_dir):
            directory.mkdir(parents=True)
        for relative in ("infra/deploy/first-install.sh", "infra/deploy/lib/first_install_env.py",
                         "infra/deploy/lib/first_install_api.py", "infra/deploy/lib/proxy-listeners.sh",
                         "infra/deploy/lib/forced-command.sh", "infra/deploy/receive-bundle.sh", "infra/deploy/copy-serve.sh",
                         "infra/deploy/push-bundle.sh", "infra/deploy/compose.server.yml",
                         "infra/deploy/env/alpha.env.example", "infra/deploy/env/provider.env.example"):
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        reload_stub = self.repo / "infra/deploy/reload-proxy.sh"
        reload_stub.write_text('#!/usr/bin/env bash\necho "reload-proxy $*" >> "$STUB_STATE/calls.log"\n')
        reload_stub.chmod(0o755)
        (self.repo / ".gitignore").write_text("infra/deploy/env/*.env\n")
        git = ["git", "-C", str(self.repo), "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run([*git, "init", "-q"], check=True)
        subprocess.run([*git, "add", "-A"], check=True)
        subprocess.run([*git, "commit", "-q", "-m", "clone"], check=True)
        # A real, valid environment file: the receiver and the copy key read it as data.
        env_dir = self.repo / "infra/deploy/env"
        subprocess.run([sys.executable, str(DEPLOY / "lib/first_install_env.py"), "create", "--env-dir", str(env_dir),
                        "--instance", "auditmanager", "--http-port", "31500"], check=True, capture_output=True)
        docker = self.bin / "docker"
        docker.write_text(DOCKER_STUB)
        docker.chmod(0o755)
        df = self.bin / "df"
        df.write_text(DF_STUB)
        df.chmod(0o755)
        self.set_state(running=["postgres", "s3", "web", "api", "worker", "proxy"], fingerprint=FINGERPRINT)
        self.stack, self._stop = fake_stack.serve()
        self.password_file = self.secret_dir / "auditmanager-admin-password.txt"
        done = fia.admin(fia.Client(self.stack.base, timeout=5, sleep=lambda _s: None), self.password_file, "owner@auditco.net",
                         lambda _line: None)
        assert done == 0
        self.bundles = tmp_path / "bundles-source"
        self.bundles.mkdir()

    def close(self) -> None:
        self._stop()

    def set_state(self, **values) -> None:
        path = self.stub / "docker.json"
        state = json.loads(path.read_text()) if path.exists() else {}
        state.update(values)
        path.write_text(json.dumps(state))

    def state(self) -> dict:
        return json.loads((self.stub / "docker.json").read_text())

    def env(self, **extra: str) -> dict[str, str]:
        environment = {
            "PATH": f"{self.bin}:/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(self.tmp), "LC_ALL": "C.UTF-8",
            "FIRST_INSTALL_TEST_MODE": "1", "FIRST_INSTALL_COPY_DIR": str(self.copy_dir),
            "FIRST_INSTALL_STAGING": str(self.staging), "FIRST_INSTALL_SECRET_DIR": str(self.secret_dir),
            "FIRST_INSTALL_STATE_ROOT": str(self.tmp / "var-lib"), "FIRST_INSTALL_LOG_DIR": str(self.tmp / "var-log"),
            "FIRST_INSTALL_POLL_SECONDS": "1", "FIRST_INSTALL_MEMINFO": str(self.tmp / "meminfo"),
            "STUB_STATE": str(self.stub), "STUB_DOCKER_ROOT": str(self.tmp),
            "BUNDLE_STAGING_MARGIN_BYTES": "0",
        }
        (self.tmp / "meminfo").write_text("MemTotal:  8000000 kB\nMemAvailable:  6000000 kB\n")
        environment.update(extra)
        return environment

    def stage(self, bundle: Path, **extra: str) -> subprocess.CompletedProcess[str]:
        """Run only stage 5, as the installer's runner would."""
        driver = (f'source "{self.repo}/infra/deploy/first-install.sh"; OPT_BUNDLE="{bundle}"; INSTANCE=auditmanager; '
                  f'HTTP_PORT=31500; ALPHA_BASE="{self.stack.base}"; STATE_DIR="{self.tmp}/var-lib/auditmanager"; '
                  f'STATE_FILE="$STATE_DIR/first-install.state"; mkdir -p "$STATE_DIR"; stage_norms')
        return subprocess.run(["bash", "-c", driver], capture_output=True, text=True, env=self.env(**extra), cwd=self.repo,
                              timeout=120)

    def docker_verbs(self) -> list[str]:
        verbs = []
        log = self.stub / "docker.log"
        for line in (log.read_text().splitlines() if log.exists() else []):
            argv = json.loads(line)
            if argv[:1] != ["compose"]:
                continue
            position = 1
            while position < len(argv) and argv[position] in ("--env-file", "--file"):
                position += 2
            sub = argv[position]
            if sub in ("stop", "start"):
                verbs.append(f"{sub} {' '.join(argv[position + 1:])}")
            elif sub == "run" and "auditmanager.norms.bundle" in argv:
                verbs.append(argv[argv.index("auditmanager.norms.bundle") + 1])
        return verbs

    def record(self) -> dict:
        return json.loads((self.copy_dir / "record.json").read_text())


@pytest.fixture()
def norms(tmp_path: Path):
    rig = NormsRig(tmp_path)
    yield rig
    rig.close()


def _stop_codes(result: subprocess.CompletedProcess[str]) -> list[str]:
    return re.findall(r"^STOP \[([a-z_]+)\]", result.stdout, re.M)


def test_the_whole_on_host_import_runs_through_the_real_scripts_in_the_runbooks_order(norms: NormsRig) -> None:
    bundle = _make_bundle(norms.bundles)
    done = norms.stage(bundle)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-2000:]
    key = bundle.name
    # the bundle was kept, verified, on the staging side
    assert (norms.staging / "bundles" / key / "SHA256SUMS").is_file()
    assert (norms.staging / "logs" / f"{key}.import.exit").read_text().strip() == "0"
    # the order of the verbs: writers stopped by the waiver, the importer, the report, the writers started again
    assert norms.docker_verbs() == ["stop web api worker", "import", "report", "start web api worker"]
    record = norms.record()
    assert record["kind"] == "test_data_waiver" and record["state"] == "closed" and record["real_data_marker"] is False
    assert not (norms.copy_dir / "real_data").exists()
    assert set(norms.state()["running"]) >= {"web", "api", "worker"}
    # the report matched after a successful import, so the receiver removed the objects it no longer needs
    assert not (norms.staging / "bundles" / key / "objects").exists()
    assert any(line.startswith("reload-proxy") for line in (norms.stub / "calls.log").read_text().splitlines())
    # the designation
    assert norms.stack.snapshots[0]["current"] is True
    assert "is now the current norms snapshot" in done.stdout
    # the stage's own marks
    assert "s5.designated=ok" in (norms.tmp / "var-lib/auditmanager/first-install.state").read_text()


def test_a_second_run_after_a_complete_one_does_nothing(norms: NormsRig) -> None:
    bundle = _make_bundle(norms.bundles)
    assert norms.stage(bundle).returncode == 0
    verbs = norms.docker_verbs()
    again = norms.stage(bundle)
    assert again.returncode == 0 and "designated by an earlier run" in again.stdout
    assert norms.docker_verbs() == verbs


def test_a_rerun_after_an_interruption_does_not_receive_or_attest_again(norms: NormsRig) -> None:
    bundle = _make_bundle(norms.bundles)
    norms.set_state(import_exit=2)
    failed = norms.stage(bundle)
    assert failed.returncode == 10 and _stop_codes(failed) == ["norms_import_failed"], failed.stdout[-1500:]
    assert norms.record()["state"] == "open"
    received = (norms.staging / "logs" / f"{bundle.name}.received").read_text()
    norms.set_state(import_exit=0)
    # An import that exited non-zero is final for that bundle until the owner decides: the rerun reports it again.
    again = norms.stage(bundle)
    assert again.returncode == 10 and _stop_codes(again) == ["norms_import_failed"]
    assert (norms.staging / "logs" / f"{bundle.name}.received").read_text() == received
    assert norms.docker_verbs().count("stop web api worker") == 1


def test_an_unfinished_admission_exit_75_is_imported_again_under_the_same_waiver(norms: NormsRig) -> None:
    bundle = _make_bundle(norms.bundles)
    norms.set_state(import_exit=75)
    first = norms.stage(bundle)
    assert _stop_codes(first) == ["norms_import_failed"] and "75" in first.stdout
    norms.set_state(import_exit=0)
    second = norms.stage(bundle)
    assert second.returncode == 0, second.stdout[-2000:]
    assert norms.docker_verbs().count("stop web api worker") == 1
    assert norms.docker_verbs().count("import") == 2


def test_a_report_that_differs_stops_and_leaves_the_record_open_and_the_writers_stopped(norms: NormsRig) -> None:
    bundle = _make_bundle(norms.bundles)
    norms.set_state(report_exit=1)
    done = norms.stage(bundle)
    assert done.returncode == 10 and _stop_codes(done) == ["norms_report_differs"], done.stdout[-1500:]
    assert norms.record()["state"] == "open"
    assert not set(norms.state()["running"]) & {"web", "api", "worker"}
    assert norms.stack.snapshots[0]["current"] is False


def test_a_bundle_that_does_not_verify_is_refused_before_a_byte_is_sent(norms: NormsRig) -> None:
    bundle = _make_bundle(norms.bundles, tamper=True)
    done = norms.stage(bundle)
    assert _stop_codes(done) == ["norms_bundle_invalid"], done.stdout[-1500:]
    assert not (norms.staging / "bundles").exists() or not list((norms.staging / "bundles").iterdir())
    assert norms.docker_verbs() == []


def test_too_little_disk_for_the_bundle_is_its_own_stop(norms: NormsRig) -> None:
    bundle = _make_bundle(norms.bundles)
    done = norms.stage(bundle, STUB_DF_BYTES=str(1024**3))
    code_lines = [line for line in done.stdout.splitlines() if line.startswith("STOP")]
    assert code_lines and code_lines[-1].startswith("STOP [norms_disk_low]"), done.stdout[-1500:]


def test_a_stale_waiver_is_closed_and_replaced_before_the_import(norms: NormsRig) -> None:
    bundle = _make_bundle(norms.bundles)
    # Open a waiver by hand through the copy key, then age it past the point where the import's window is too short.
    env = norms.env(SSH_ORIGINAL_COMMAND="attest --test-data", ALPHA_CHECKOUT=str(norms.repo), STAND_COPY_DIR=str(norms.copy_dir),
                    BUNDLE_STAGING=str(norms.staging))
    norms.copy_dir.mkdir(mode=0o700)
    norms.staging.mkdir(mode=0o700)
    assert subprocess.run([str(norms.repo / "infra/deploy/copy-serve.sh")], env=env, capture_output=True, text=True).returncode == 0
    record = norms.copy_dir / "record.json"
    old = norms.record()["quiesced_at"]
    stale = "2026-01-01T00:00:00Z"
    record.write_text(record.read_text().replace(old, f'"{stale}"') if old.startswith('"') else record.read_text().replace(old, stale))
    first_stamp = norms.record()["stamp"]
    done = norms.stage(bundle)
    assert done.returncode == 0, done.stdout[-2500:]
    assert "too little of its window left" in done.stdout
    assert norms.record()["stamp"] != first_stamp and norms.record()["state"] == "closed"


def test_the_stage_never_touches_a_foreign_open_record(norms: NormsRig) -> None:
    bundle = _make_bundle(norms.bundles)
    norms.copy_dir.mkdir(mode=0o700)
    norms.staging.mkdir(mode=0o700)
    (norms.copy_dir / "record.json").write_text(
        '{\n  "record_version": 1,\n  "kind": "copy",\n  "stamp": "20261101T000000Z",\n  "state": "open",\n'
        '  "purpose": "publish",\n  "target_sha": null,\n  "quiesced_at": null\n}\n')
    before = (norms.copy_dir / "record.json").read_bytes()
    done = norms.stage(bundle)
    assert done.returncode == 10 and _stop_codes(done) == ["norms_busy"], done.stdout[-1500:]
    assert (norms.copy_dir / "record.json").read_bytes() == before
    assert not (norms.staging / "bundles").exists() or not list((norms.staging / "bundles").iterdir())
    assert norms.docker_verbs() == []


def test_the_directories_the_scripts_require_are_made_private_and_outside_the_clone(norms: NormsRig) -> None:
    bundle = _make_bundle(norms.bundles)
    norms.stage(bundle)
    for directory in (norms.copy_dir, norms.staging):
        assert oct(directory.stat().st_mode & 0o777) == "0o700"
        assert str(norms.repo) not in str(directory.resolve())
    status = subprocess.run(["git", "-C", str(norms.repo), "status", "--porcelain", "--untracked-files=all"],
                            capture_output=True, text=True).stdout
    assert status == ""
