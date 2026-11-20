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
fake_github = _load("first_install_fake_github_for_norms_tests", Path(__file__).with_name("fake_github.py"))
publisher = _load("publish_bundle_release_for_norms_tests", ROOT / "infra" / "norms" / "publish_bundle_release.py")
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


if argv[:1] == ["inspect"]:
    print("running")
    sys.exit(0)
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
    if "auditmanager.norms.semantic_check" in command:
        sys.stdout.write(state.get("semantic_out", ""))
        sys.exit(int(state.get("semantic_exit", 0)))
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
        sequence = state.get("import_exit_sequence") or []
        if sequence:
            code = sequence.pop(0)
            state["import_exit_sequence"] = sequence
            save()
            sys.exit(int(code))
        sys.exit(int(state.get("import_exit", 0)))
    if action == "report":
        print("report: full match" if int(state.get("report_exit", 0)) == 0 else "report: DIFFERS")
        sys.exit(int(state.get("report_exit", 0)))
sys.exit(0)
'''
SEMANTIC_PASS = ('{"min_mean_inner_product": 0.97, "min_self_recall_at_10": 0.9, "mean_inner_product": 0.9812, "p05_inner_product": 0.95, '
                 '"self_recall_at_10": 0.934, "verdict": "PASS", "windows": 500}\n')
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
        self.set_state(running=["postgres", "s3", "web", "api", "worker", "proxy"], fingerprint=FINGERPRINT,
                       semantic_out=SEMANTIC_PASS, semantic_exit=0)
        self.stack, self._stop = fake_stack.serve()
        self.password_file = self.secret_dir / "auditmanager-admin-password.txt"
        done = fia.admin(fia.Client(self.stack.base, timeout=5, sleep=lambda _s: None), self.password_file, "owner@auditco.net",
                         lambda _line: None)
        assert done == 0
        self.bundles = tmp_path / "bundles-source"
        self.bundles.mkdir()
        self.github = fake_github.FakeGithub("acme-co/audit-install")
        self.upload_token = tmp_path / "upload-token"
        self.upload_token.write_text(self.github.token + "\n")
        self.upload_token.chmod(0o600)
        self.lock_path = self.repo / "infra/norms/bundle-release.lock"

    def close(self) -> None:
        self._stop()
        self.github.close()

    def publish(self, bundle: Path, part_size: int = 200) -> dict:
        """The real publisher against the stand-in GitHub; the lock goes into the clone and is committed (the clone stays clean)."""
        done = publisher.main(["--bundle", str(bundle), "--repo", "acme-co/audit-install", "--token-file", str(self.upload_token),
                               "--lock", str(self.lock_path), "--work-dir", str(self.tmp / "publish-work"), "--api-base", self.github.base,
                               "--part-size-bytes", str(part_size), "--allow-small-disk"])
        assert done == 0
        git = ["git", "-C", str(self.repo), "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run([*git, "add", "-f", "infra/norms/bundle-release.lock"], check=True)
        subprocess.run([*git, "commit", "-q", "-m", "the lock"], check=True)
        tag = next(iter(self.github.releases))
        return {"tag": tag, "parts": [a["name"] for a in self.github.release(tag)["assets"]]}

    def release_stage(self, **extra: str) -> subprocess.CompletedProcess[str]:
        """Stage 5 with no --norms-bundle: the lock file in the clone decides."""
        driver = (f'source "{self.repo}/infra/deploy/first-install.sh"; OPT_BUNDLE=""; INSTANCE=auditmanager; '
                  f'HTTP_PORT=31500; ALPHA_BASE="{self.stack.base}"; STATE_DIR="{self.tmp}/var-lib/auditmanager"; '
                  f'STATE_FILE="$STATE_DIR/first-install.state"; mkdir -p "$STATE_DIR"; stage_norms')
        return subprocess.run(["bash", "-c", driver], capture_output=True, text=True, env=self.env(**extra), cwd=self.repo, timeout=180)

    def downloaded_parts(self, tag: str) -> list[str]:
        directory = self.staging / "download" / tag
        return sorted(p.name for p in directory.iterdir()) if directory.exists() else []

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
            "BUNDLE_STAGING_MARGIN_BYTES": "0", "FIRST_INSTALL_SAMPLE_SECONDS": "0.1",
            "FIRST_INSTALL_RELEASE_BASE": self.github.base, "FIRST_INSTALL_RELEASE_API_BASE": self.github.base,
            "FIRST_INSTALL_RELEASE_RETRIES": "2", "FIRST_INSTALL_RELEASE_RETRY_DELAY": "1",
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

    def stage_and_semantic(self, bundle: Path, **extra: str) -> subprocess.CompletedProcess[str]:
        """The norms stage and then the semantic stage, in one shell, as the runner would run them."""
        driver = (f'source "{self.repo}/infra/deploy/first-install.sh"; OPT_BUNDLE="{bundle}"; INSTANCE=auditmanager; '
                  f'HTTP_PORT=31500; ALPHA_BASE="{self.stack.base}"; STATE_DIR="{self.tmp}/var-lib/auditmanager"; '
                  f'STATE_FILE="$STATE_DIR/first-install.state"; mkdir -p "$STATE_DIR"; stage_norms; stage_semantic')
        return subprocess.run(["bash", "-c", driver], capture_output=True, text=True, env=self.env(**extra), cwd=self.repo, timeout=120)

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
            elif sub == "up" and "worker" in argv:
                verbs.append("restart worker")
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


def test_an_unfinished_admission_exit_75_is_imported_again_by_the_stage_itself_under_the_same_waiver(norms: NormsRig) -> None:
    bundle = _make_bundle(norms.bundles)
    norms.set_state(import_exit_sequence=[75, 0])
    done = norms.stage(bundle)
    assert done.returncode == 0, done.stdout[-2500:]
    assert "importing again, which is safe" in done.stdout
    assert norms.docker_verbs().count("stop web api worker") == 1 and norms.docker_verbs().count("import") == 2


def test_an_importer_that_always_ends_unfinished_stops_after_three_attempts_with_a_wait_and_run_again(norms: NormsRig) -> None:
    bundle = _make_bundle(norms.bundles)
    norms.set_state(import_exit=75)
    done = norms.stage(bundle)
    assert done.returncode == 10 and _stop_codes(done) == ["norms_import_unfinished"], done.stdout[-1500:]
    assert norms.docker_verbs().count("import") == 3 and "ASK" not in done.stdout.splitlines()[-1]
    norms.set_state(import_exit=0)
    again = norms.stage(bundle)
    assert again.returncode == 0, again.stdout[-1500:]
    assert norms.docker_verbs().count("stop web api worker") == 1


def test_an_import_that_the_server_restart_interrupted_is_started_again_without_a_question(norms: NormsRig) -> None:
    bundle = _make_bundle(norms.bundles)
    norms.set_state(import_exit=2)
    assert _stop_codes(norms.stage(bundle)) == ["norms_import_failed"]
    (norms.staging / "logs" / f"{bundle.name}.import.exit").unlink()        # started, no exit status, the lock free: a restart
    norms.set_state(import_exit=0)
    done = norms.stage(bundle)
    assert done.returncode == 0, done.stdout[-2000:]
    assert "importing again, which is safe" in done.stdout
    assert norms.docker_verbs().count("import") == 2 and norms.docker_verbs().count("stop web api worker") == 1


def test_a_lock_held_by_another_step_is_a_wait_and_not_a_report(norms: NormsRig) -> None:
    import fcntl

    bundle = _make_bundle(norms.bundles)
    norms.staging.mkdir(mode=0o700)
    with open(norms.staging / "receive.lock", "w") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        done = norms.stage(bundle)
    assert _stop_codes(done) == ["norms_wait"], done.stdout[-1500:]
    assert "Wait five minutes" in done.stdout.splitlines()[-1] and "REPORT" not in done.stdout.splitlines()[-1]


def test_after_the_snapshot_is_current_the_gates_run_and_the_worker_is_pointed_at_the_embedder(norms: NormsRig) -> None:
    """The bundle given, the lookup turns on in the same run: norms stage, then the two gates, then the address."""
    bundle = _make_bundle(norms.bundles)
    done = norms.stage_and_semantic(bundle)
    assert done.returncode == 0, done.stdout[-3000:]
    assert norms.stack.snapshots[0]["current"] is True
    env = (norms.repo / "infra/deploy/env/alpha.env").read_text()
    assert "\nAUDITMANAGER_NORM_EMBED_URL=http://norm-embed:8080\n" in env and "\nALPHA_NORM_EMBED=yes\n" in env
    assert norms.docker_verbs() == ["stop web api worker", "import", "report", "start web api worker", "restart worker"]
    assert "both gates passed" in done.stdout


def test_a_failed_quality_gate_after_a_good_import_leaves_the_corpus_in_and_the_address_empty(norms: NormsRig) -> None:
    bundle = _make_bundle(norms.bundles)
    norms.set_state(semantic_out=SEMANTIC_PASS.replace('"mean_inner_product": 0.9812', '"mean_inner_product": 0.91').replace("PASS", "FAIL"),
                    semantic_exit=1)
    done = norms.stage_and_semantic(bundle)
    assert done.returncode == 10 and _stop_codes(done) == ["semantic_quality_failed"], done.stdout[-2000:]
    assert norms.stack.snapshots[0]["current"] is True            # the norms stay current: word search works on them
    assert "\nAUDITMANAGER_NORM_EMBED_URL=\n" in (norms.repo / "infra/deploy/env/alpha.env").read_text()
    assert "restart worker" not in norms.docker_verbs()


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


# ------------------------------------------------------------------ the bundle comes from the repository's release (FIRST-INSTALL-02)


def _downloads(norms: NormsRig) -> list[dict]:
    return [r for r in norms.github.requests if "/releases/download/" in r["path"] or "/releases/assets/" in r["path"]]


def test_the_release_is_downloaded_checked_streamed_into_receive_and_imported_by_the_unchanged_flow(norms: NormsRig) -> None:
    bundle = _make_bundle(norms.bundles)
    published = norms.publish(bundle)
    assert len(published["parts"]) >= 3, "the fixture must make several parts"
    done = norms.release_stage()
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-2000:]
    key = bundle.name
    # no --norms-bundle: the lock chose the release, and the received bundle is the directory's digest and the name's
    assert "norms: the release" in done.stdout and "norms: the bundle directory" not in done.stdout
    assert (norms.staging / "bundles" / key / "SHA256SUMS").is_file()
    assert hashlib.sha256((norms.staging / "bundles" / key / "SHA256SUMS").read_bytes()).hexdigest() == key.rsplit("+", 1)[1]
    assert "the digest of its SHA256SUMS is the lock's and the directory name's" in done.stdout
    # the import is the one flow, verb for verb
    assert norms.docker_verbs() == ["stop web api worker", "import", "report", "start web api worker"]
    assert norms.stack.snapshots[0]["current"] is True and norms.record()["state"] == "closed"
    # the public path asked for no credential, every part once (and a probe for its first byte)
    fetched = [r for r in _downloads(norms) if r["range"] != "bytes=0-0"]
    assert [r["path"].rsplit("/", 1)[1] for r in fetched] == published["parts"]
    assert all(r["anonymous"] for r in _downloads(norms))
    # the parts are deleted once the import succeeded, and nothing was written in the clone
    assert norms.downloaded_parts(published["tag"]) == []
    status = subprocess.run(["git", "-C", str(norms.repo), "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True).stdout
    assert status == ""


def test_a_second_run_after_the_import_downloads_nothing(norms: NormsRig) -> None:
    norms.publish(_make_bundle(norms.bundles))
    assert norms.release_stage().returncode == 0
    before = len(norms.github.requests)
    again = norms.release_stage()
    assert again.returncode == 0 and "designated by an earlier run" in again.stdout and len(norms.github.requests) == before


def test_a_partial_download_is_resumed_with_a_range_request_and_a_cut_connection_is_resumed_by_curl(norms: NormsRig) -> None:
    bundle = _make_bundle(norms.bundles)
    published = norms.publish(bundle)
    first, second = published["parts"][0], published["parts"][1]
    directory = norms.staging / "download" / published["tag"]
    directory.mkdir(parents=True)
    (directory / first).write_bytes(norms.github.asset_bytes(published["tag"], first)[:40])      # a run that was cut off
    norms.github.drop_download[second] = 25                                                       # a connection cut after 25 bytes, once
    done = norms.release_stage()
    assert done.returncode == 0, done.stdout[-2500:] + done.stderr[-1500:]
    ranges = [(r["path"].rsplit("/", 1)[1], r["range"]) for r in _downloads(norms)]
    assert (first, "bytes=40-") in ranges and (second, "bytes=25-") in ranges
    assert hashlib.sha256((norms.staging / "bundles" / bundle.name / "SHA256SUMS").read_bytes()).hexdigest() == bundle.name.rsplit("+", 1)[1]


def test_a_part_that_never_arrives_whole_is_a_run_again_and_the_rerun_keeps_what_it_has(norms: NormsRig) -> None:
    published = norms.publish(_make_bundle(norms.bundles))
    second = published["parts"][1]
    norms.github.drop_always[second] = 20
    done = norms.release_stage()
    assert done.returncode == 10 and _stop_codes(done) == ["norms_download_failed"], done.stdout[-1500:]
    assert "resumes where it stopped" in done.stdout.splitlines()[-1] and "REPORT" not in done.stdout.splitlines()[-1]
    assert norms.docker_verbs() == [] and not (norms.staging / "bundles").exists() or not list((norms.staging / "bundles").iterdir())
    kept = norms.downloaded_parts(published["tag"])
    assert published["parts"][0] in kept
    norms.github.drop_always.clear()
    again = norms.release_stage()
    assert again.returncode == 0, again.stdout[-2000:]


def test_a_part_with_the_wrong_checksum_is_downloaded_again_once_and_then_reported_and_nothing_is_imported(norms: NormsRig) -> None:
    published = norms.publish(_make_bundle(norms.bundles))
    second = published["parts"][1]
    good = norms.github.asset_bytes(published["tag"], second)
    norms.github.altered[second] = bytes([good[0] ^ 1]) + good[1:]            # the same size, one bit different
    done = norms.release_stage()
    assert done.returncode == 10 and _stop_codes(done) == ["norms_download_corrupt"], done.stdout[-1500:]
    last = done.stdout.splitlines()[-1]
    assert last.startswith("STOP [norms_download_corrupt]: REPORT TO THE OWNER") and second in last
    assert hashlib.sha256(good).hexdigest() in last and "downloading it again" in done.stdout
    assert len([r for r in _downloads(norms) if r["path"].endswith(second) and r["range"] != "bytes=0-0"]) == 2
    assert norms.docker_verbs() == [] and not (norms.staging / "download" / published["tag"] / second).exists()
    # a bad copy that is good on the second download is a recovery, not a stop
    norms.github.altered.clear()
    norms.github.altered_once[second] = bytes([good[0] ^ 1]) + good[1:]
    assert norms.release_stage().returncode == 0


def test_an_asset_that_is_not_in_the_release_is_a_report_that_names_it(norms: NormsRig) -> None:
    published = norms.publish(_make_bundle(norms.bundles))
    gone = published["parts"][1]
    norms.github.missing.add(gone)
    done = norms.release_stage()
    assert done.returncode == 10 and _stop_codes(done) == ["norms_release_missing"], done.stdout[-1500:]
    last = done.stdout.splitlines()[-1]
    assert last.startswith("STOP [norms_release_missing]: REPORT TO THE OWNER") and gone in last and published["tag"] in last
    assert "publish-bundle-release.sh" in last and norms.docker_verbs() == []
    # a release that was deleted altogether says the same
    norms.github.missing.clear()
    norms.github.releases.clear()
    assert _stop_codes(norms.release_stage()) == ["norms_release_missing"]


def test_a_directory_given_with_norms_bundle_wins_over_the_lock_and_nothing_is_downloaded(norms: NormsRig) -> None:
    bundle = _make_bundle(norms.bundles)
    norms.publish(bundle)
    done = norms.stage(bundle)                        # `stage()` sets OPT_BUNDLE, and the clone carries a lock
    assert done.returncode == 0, done.stdout[-2500:]
    assert "norms: the bundle directory" in done.stdout and "norms: the release" not in done.stdout
    assert _downloads(norms) == [] and norms.docker_verbs() == ["stop web api worker", "import", "report", "start web api worker"]


def test_a_lock_that_does_not_hold_together_is_reported_before_anything_is_fetched(norms: NormsRig) -> None:
    bundle = _make_bundle(norms.bundles)
    norms.publish(bundle)
    good = norms.lock_path.read_text()
    broken = {
        "the digest is not the name's": good.replace("bundle_sums_sha256=" + bundle.name.rsplit("+", 1)[1], "bundle_sums_sha256=" + "0" * 64),
        "the total is not the sum": re.sub(r"total_bytes=\d+", "total_bytes=1", good),
        "a part line is short": re.sub(r"(part=\S+ \d+ [0-9a-f]{64}) \d+", r"\1", good),
        "an unknown version": good.replace("lock_version=1", "lock_version=2"),
        "no parts": "\n".join(line for line in good.splitlines() if not line.startswith("part=")),
    }
    for why, text in broken.items():
        norms.lock_path.write_text(text)
        done = norms.release_stage()
        assert _stop_codes(done) == ["norms_lock_invalid"], (why, done.stdout[-600:])
        assert done.stdout.splitlines()[-1].startswith("STOP [norms_lock_invalid]: REPORT TO THE OWNER")
    assert _downloads(norms) == [] and norms.docker_verbs() == []


def test_a_private_repository_is_read_with_a_token_that_travels_in_a_header_file_never_in_an_argument(norms: NormsRig, tmp_path: Path) -> None:
    published = norms.publish(_make_bundle(norms.bundles))
    norms.github.require_download_token = True
    token_file = tmp_path / "read-token"
    token_file.write_text(norms.github.token + "\n")
    token_file.chmod(0o600)
    done = norms.release_stage(FIRST_INSTALL_NORMS_READ_TOKEN_FILE=str(token_file))
    assert done.returncode == 0, done.stdout[-2500:]
    assert norms.github.token not in done.stdout + done.stderr
    api = [r for r in norms.github.requests if "/releases/assets/" in r["path"] and r["method"] == "GET"]
    assert api and all(r["authorized"] and r["accept"] == "application/octet-stream" for r in api)
    assert not [r for r in norms.github.requests if "/releases/download/" in r["path"]]       # the public URL was not used
    # the script's only use of the token is a printf into a mode-600 header file that curl reads with -H @file
    script = (ROOT / "infra/deploy/first-install.sh").read_text()
    assert script.count("Bearer") == 1 and 'RELEASE_CURL+=(-H "@$RELEASE_HEADER")' in script
    assert published["tag"] in done.stdout


def test_the_download_counts_in_the_disk_the_stage_asks_for(norms: NormsRig) -> None:
    driver = (f'source "{norms.repo}/infra/deploy/first-install.sh"; STATE_DIR="{norms.tmp}/var-lib/auditmanager"; '
              f'STATE_FILE="$STATE_DIR/first-install.state"; mkdir -p "$STATE_DIR"; norms_check_disk 1000 "$1" 0')
    env = norms.env(STUB_DF_BYTES=str(10 * 1024**3))
    without = subprocess.run(["bash", "-c", driver, "x", "0"], capture_output=True, text=True, env=env, cwd=norms.repo)
    assert without.returncode == 0, without.stdout
    with_download = subprocess.run(["bash", "-c", driver, "x", str(3 * 1024**3)], capture_output=True, text=True, env=env, cwd=norms.repo)
    assert with_download.returncode == 10 and "STOP [norms_disk_low]" in with_download.stdout
    assert "10 GiB are free" in with_download.stdout and "12 GiB are needed" in with_download.stdout
    again = subprocess.run(["bash", "-c", driver, "x", str(3 * 1024**3)], capture_output=True, text=True, env=env, cwd=norms.repo)
    assert "STOP [norms_disk_too_small]: ASK THE OWNER" in again.stdout


def test_the_lock_is_the_only_thing_the_installer_trusts_about_the_release(norms: NormsRig) -> None:
    """A part of the right size whose bytes were replaced after publication is caught by the lock's sha256, never imported."""
    published = norms.publish(_make_bundle(norms.bundles))
    name = published["parts"][-1]
    asset = next(a for a in norms.github.release(published["tag"])["assets"] if a["name"] == name)
    asset["_content"] = bytes(len(asset["_content"]))                          # zeros: the same size
    done = norms.release_stage()
    assert _stop_codes(done) == ["norms_download_corrupt"] and norms.docker_verbs() == []
