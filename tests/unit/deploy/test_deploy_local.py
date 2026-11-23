"""`infra/deploy/deploy-local.sh`: the server deploys its own checkout from its own origin, with no ssh (`FIRST-INSTALL-03`).

Real git against local bare repositories (an origin, a working copy that "pushes to main", the server's deploy clone), stub
`deploy.sh` and `verify-deployed.sh` inside the clone that record what they were called with, and `DEPLOY_LOCAL_TEST_MODE=1`, which
moves the state, the log and `/srv` into the test's directory. That the script runs the workflow's own remote script is held
byte for byte by `tests/contract/test_deploy_auto_workflow.py`; this file holds what the wrapper adds:

* the happy path: the tip of main is deployed, detached, `DEPLOY OK: <sha>`, and a log block is written;
* the refusals of that script, as they come out of this wrapper: a dirty tree (exit 3), an origin that is another repository
  (exit 4, before anything is fetched) -- bound to the repository recorded when the server was installed, not to whatever the
  origin says today -- and a commit that is not on main;
* the timer's run (`--if-moved`): nothing to do when main is what the clone runs, a deploy when it moved, a SHA that failed is not
  tried again until main moves (a person's run still tries it), an unreachable origin is a skip;
* the locks: never beside another deploy, never beside the first install; a timer skips, a person is told it is busy (75).
"""

from __future__ import annotations

import fcntl
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "infra" / "deploy" / "deploy-local.sh"
INSTANCE = "forkinst"
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

DEPLOY_STUB = """#!/bin/sh
echo "deploy head=$(git rev-parse HEAD) stdin=$(cat | wc -c)" >> "$STUB_DIR/calls.log"
echo "DEPLOY STUB CALLED"
exit "$(cat "$STUB_DIR/deploy.exit" 2>/dev/null || echo 0)"
"""
VERIFY_STUB = """#!/bin/sh
echo "verify head=$(git rev-parse HEAD) stdin=$(cat | wc -c)" >> "$STUB_DIR/calls.log"
echo "VERIFY STUB CALLED"
exit "$(cat "$STUB_DIR/verify.exit" 2>/dev/null || echo 0)"
"""


def git(*args: str, cwd: Path | None = None) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, env=os.environ | GIT_ENV, check=True)
    return done.stdout.strip()


class Rig:
    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.state_root = tmp / "var-lib"
        self.log_dir = tmp / "var-log"
        self.deploy_root = tmp / "srv"
        self.stub = tmp / "stub"
        self.origin = tmp / "remote" / "acme-co" / "audit-install.git"
        self.work = tmp / "work"
        self.deploy = self.deploy_root / INSTANCE
        for directory in (self.state_root, self.log_dir, self.deploy_root, self.stub, self.origin.parent):
            directory.mkdir(parents=True)
        seed = tmp / "seed"
        seed.mkdir()
        git("init", "-q", "-b", "main", str(seed))
        deployment = seed / "infra" / "deploy"
        deployment.mkdir(parents=True)
        shutil.copy2(SCRIPT, deployment / "deploy-local.sh")
        for name, body in (("deploy.sh", DEPLOY_STUB), ("verify-deployed.sh", VERIFY_STUB)):
            (deployment / name).write_text(body)
            (deployment / name).chmod(0o755)
        (seed / ".gitignore").write_text("infra/deploy/env/*.env\n")
        (seed / "README").write_text("one\n")
        git("add", "-A", cwd=seed)
        git("commit", "-q", "-m", "one", cwd=seed)
        git("clone", "-q", "--bare", str(seed), str(self.origin))
        git("clone", "-q", str(self.origin), str(self.work))
        self.first = git("rev-parse", "HEAD", cwd=self.work)
        # the deploy clone as the installer leaves it: detached at a commit of main, with its own (ignored) environment file
        git("clone", "-q", str(self.origin), str(self.deploy))
        git("checkout", "-q", "--detach", self.first, cwd=self.deploy)
        env_dir = self.deploy / "infra" / "deploy" / "env"
        env_dir.mkdir(parents=True)
        (env_dir / "alpha.env").write_text(f"ALPHA_INSTANCE={INSTANCE}\n")

    def push(self, text: str = "next", *, branch: str = "main") -> str:
        """A commit in the working copy pushed to `branch` of origin (a push to main is what the server deploys)."""
        git("checkout", "-q", "-B", branch, "origin/main" if branch != "main" else "main", cwd=self.work)
        (self.work / "README").write_text(text + "\n")
        git("add", "-A", cwd=self.work)
        git("commit", "-q", "-m", text, cwd=self.work)
        git("push", "-q", "origin", branch, cwd=self.work)
        return git("rev-parse", "HEAD", cwd=self.work)

    def env(self) -> dict[str, str]:
        return os.environ | {"DEPLOY_LOCAL_TEST_MODE": "1", "DEPLOY_LOCAL_STATE_ROOT": str(self.state_root),
                             "DEPLOY_LOCAL_LOG_DIR": str(self.log_dir), "DEPLOY_LOCAL_DEPLOY_ROOT": str(self.deploy_root),
                             "STUB_DIR": str(self.stub), "GIT_TERMINAL_PROMPT": "0"}

    def run(self, *args: str, script: Path = SCRIPT) -> subprocess.CompletedProcess[str]:
        return subprocess.run([str(script), *args], capture_output=True, text=True, env=self.env(), timeout=120)

    def deploy_local(self, *args: str) -> subprocess.CompletedProcess[str]:
        return self.run("--deploy-path", str(self.deploy), *args)

    def calls(self) -> list[str]:
        path = self.stub / "calls.log"
        return path.read_text().splitlines() if path.exists() else []

    def head(self) -> str:
        return git("rev-parse", "HEAD", cwd=self.deploy)

    @property
    def state(self) -> Path:
        return self.state_root / INSTANCE

    @property
    def log(self) -> Path:
        return self.log_dir / f"{INSTANCE}-deploy-local.log"


@pytest.fixture()
def rig(tmp_path: Path) -> Rig:
    return Rig(tmp_path)


def test_the_tip_of_main_is_deployed_detached_and_logged(rig: Rig) -> None:
    tip = rig.push("two")
    done = rig.deploy_local()
    assert done.returncode == 0, done.stdout + done.stderr
    assert f"DEPLOY OK: {tip}" in done.stdout and f"DEPLOYED {tip[:12]}" in done.stdout
    assert rig.head() == tip
    assert subprocess.run(["git", "-C", str(rig.deploy), "symbolic-ref", "-q", "HEAD"], capture_output=True).returncode != 0   # detached
    # the workflow's order: deploy, then verify, each on the new commit and with an empty standard input
    assert rig.calls() == [f"deploy head={tip} stdin=0", f"verify head={tip} stdin=0"]
    block = rig.log.read_text()
    assert f"{tip} of acme-co/audit-install in {rig.deploy} (manual run)" in block and f"DEPLOY OK: {tip}" in block
    assert not (rig.state / "deploy-local.failed").exists()
    assert (rig.state / "deploy-local.source").read_text().strip() == "acme-co/audit-install"
    assert git("status", "--porcelain", "--untracked-files=all", cwd=rig.deploy) == ""


def test_a_named_commit_is_deployed_when_it_is_on_main(rig: Rig) -> None:
    rig.push("two")
    done = rig.deploy_local("--sha", rig.first)
    assert done.returncode == 0 and rig.head() == rig.first and f"DEPLOY OK: {rig.first}" in done.stdout


def test_a_commit_that_is_not_on_main_is_refused_and_nothing_is_deployed(rig: Rig) -> None:
    rig.push("two")
    side = rig.push("only on a side branch", branch="side")
    before = rig.head()
    done = rig.deploy_local("--sha", side)
    assert done.returncode != 0 and "DEPLOY OK" not in done.stdout and rig.calls() == []
    assert rig.head() == before


def test_a_dirty_tree_is_refused_with_exit_3_before_anything_is_fetched_or_deployed(rig: Rig) -> None:
    (rig.deploy / "scratch.txt").write_text("x")
    rig.push("two")
    done = rig.deploy_local()
    assert done.returncode == 3, done.stdout + done.stderr
    assert "has tracked or untracked changes" in done.stdout and "scratch.txt" in done.stdout   # the script's own words, in the log too
    assert "has tracked or untracked changes" in rig.log.read_text()
    assert rig.calls() == [] and rig.head() == rig.first
    # nothing was fetched: origin/main of the clone is still the first commit
    assert git("rev-parse", "origin/main", cwd=rig.deploy) == rig.first


def test_an_origin_that_is_another_repository_is_refused_with_exit_4_before_anything_is_read(rig: Rig, tmp_path: Path) -> None:
    assert rig.deploy_local().returncode == 0                                  # the binding is recorded at the first run
    other = tmp_path / "remote" / "someone-else" / "fork.git"
    other.parent.mkdir(parents=True)
    shutil.copytree(rig.origin, other)
    git("remote", "set-url", "origin", str(other), cwd=rig.deploy)
    calls = len(rig.calls())
    done = rig.deploy_local()
    assert done.returncode == 4, done.stdout + done.stderr
    assert "is a checkout of 'someone-else/fork', but this server accepts 'acme-co/audit-install'" in done.stderr
    assert len(rig.calls()) == calls and "DEPLOY OK" not in done.stdout


def test_the_repository_can_be_named_on_the_command_line_and_a_mismatch_is_refused(rig: Rig) -> None:
    done = rig.deploy_local("--repository", "Acme-Co/Audit-Install")             # the case is ignored, as in the workflow
    assert done.returncode == 0, done.stdout + done.stderr
    refused = rig.deploy_local("--repository", "owner/not-this")
    assert refused.returncode == 4 and "this server accepts 'owner/not-this'" in refused.stderr


def test_a_run_by_the_timer_with_nothing_to_do_prints_and_logs_nothing_and_deploys_nothing(rig: Rig) -> None:
    rig.push("two")
    assert rig.deploy_local().returncode == 0
    calls, log = rig.calls(), rig.log.read_text()
    again = rig.deploy_local("--if-moved")
    assert again.returncode == 0 and "nothing to do" in again.stdout
    assert rig.calls() == calls and rig.log.read_text() == log


def test_the_timer_deploys_when_main_moved(rig: Rig) -> None:
    done = rig.deploy_local("--if-moved")                                          # the clone runs the first commit and main is it
    assert done.returncode == 0 and "nothing to do" in done.stdout
    tip = rig.push("two")
    moved = rig.deploy_local("--if-moved")
    assert moved.returncode == 0, moved.stdout + moved.stderr
    assert f"DEPLOY OK: {tip}" in moved.stdout and rig.head() == tip and "(timer run)" in rig.log.read_text()


def _ahead_of_main(rig: Rig) -> str:
    """The deploy clone runs a commit main has not reached (a fork installed from its dev): main's tip is its ancestor."""
    ahead = rig.push("dev work", branch="dev")
    git("fetch", "-q", "origin", cwd=rig.deploy)
    git("checkout", "-q", "--detach", ahead, cwd=rig.deploy)
    return ahead


def test_the_timer_never_deploys_backwards_when_main_is_behind_what_runs(rig: Rig) -> None:
    ahead = _ahead_of_main(rig)
    skipped = rig.deploy_local("--if-moved")
    assert skipped.returncode == 0 and "not deploying backwards" in skipped.stdout, skipped.stdout + skipped.stderr
    assert rig.head() == ahead and rig.calls() == []
    # the case that differs: main moves past what runs, and the timer deploys it
    git("checkout", "-q", "main", cwd=rig.work)
    git("merge", "-q", "--ff-only", "origin/dev", cwd=rig.work)
    tip = rig.push("after dev")
    moved = rig.deploy_local("--if-moved")
    assert moved.returncode == 0 and f"DEPLOY OK: {tip}" in moved.stdout and rig.head() == tip


def test_a_person_is_refused_going_backwards_unless_the_commit_is_named(rig: Rig) -> None:
    ahead = _ahead_of_main(rig)
    refused = rig.deploy_local()
    assert refused.returncode == 3 and "would go backwards" in refused.stderr, refused.stdout + refused.stderr
    assert rig.head() == ahead and rig.calls() == []
    named = rig.deploy_local("--sha", rig.first)
    assert named.returncode == 0 and f"DEPLOY OK: {rig.first}" in named.stdout and rig.head() == rig.first


def test_a_failed_sha_is_not_tried_again_by_the_timer_until_main_moves_but_a_person_may_retry(rig: Rig) -> None:
    tip = rig.push("two")
    (rig.stub / "deploy.exit").write_text("5")
    failed = rig.deploy_local("--if-moved")
    assert failed.returncode == 5, failed.stdout + failed.stderr
    assert "DEPLOY OK" not in failed.stdout and "FAILED with status 5" in failed.stderr and "verify" not in " ".join(rig.calls())
    record = (rig.state / "deploy-local.failed").read_text().split()
    assert record[0] == tip and record[-1] == "status=5"
    calls = len(rig.calls())
    # the next ticks do nothing: not a deploy, not a log block, not a failure of the unit
    for _ in range(3):
        skipped = rig.deploy_local("--if-moved")
        assert skipped.returncode == 0 and "failed before" in skipped.stdout and "status=5" in skipped.stdout
    assert len(rig.calls()) == calls
    # a person's run is not held back by the record, and when it succeeds the record is gone
    (rig.stub / "deploy.exit").unlink()
    manual = rig.deploy_local()
    assert manual.returncode == 0 and f"DEPLOY OK: {tip}" in manual.stdout and not (rig.state / "deploy-local.failed").exists()
    # a failure again, then main moves: the timer tries the new commit
    (rig.stub / "deploy.exit").write_text("5")
    newer = rig.push("three")
    assert rig.deploy_local("--if-moved").returncode == 5
    (rig.stub / "deploy.exit").unlink()
    newest = rig.push("four")
    done = rig.deploy_local("--if-moved")
    assert done.returncode == 0 and f"DEPLOY OK: {newest}" in done.stdout and newer != newest


def test_a_failing_verification_is_a_failure_with_its_own_status_and_is_recorded(rig: Rig) -> None:
    tip = rig.push("two")
    (rig.stub / "verify.exit").write_text("6")
    done = rig.deploy_local()
    assert done.returncode == 6 and "DEPLOY OK" not in done.stdout
    assert (rig.state / "deploy-local.failed").read_text().startswith(tip)


def test_an_origin_that_does_not_answer_is_a_skip_for_the_timer_and_a_failure_for_a_person(rig: Rig, tmp_path: Path) -> None:
    assert rig.deploy_local().returncode == 0
    # the same owner/name, nowhere to be read: the binding holds, the question to origin does not
    git("remote", "set-url", "origin", str(tmp_path / "gone" / "acme-co" / "audit-install.git"), cwd=rig.deploy)
    timer = rig.deploy_local("--if-moved")
    assert timer.returncode == 0 and "origin did not answer" in timer.stdout
    person = rig.deploy_local()
    assert person.returncode == 3 and "origin did not answer" in person.stderr


def test_a_second_deploy_at_the_same_time_is_a_skip_for_the_timer_and_busy_for_a_person(rig: Rig) -> None:
    rig.push("two")
    rig.state.mkdir(parents=True, exist_ok=True)
    with open(rig.state / "deploy-local.lock", "w") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        timer = rig.deploy_local("--if-moved")
        person = rig.deploy_local()
    assert timer.returncode == 0 and "skipped: another deploy-local.sh is running" in timer.stdout
    assert person.returncode == 75 and "busy: another deploy-local.sh is running" in person.stderr
    assert rig.calls() == [] and rig.head() == rig.first
    assert rig.deploy_local().returncode == 0                                       # the lock was released with its holder


def test_a_deploy_never_runs_beside_the_first_install(rig: Rig) -> None:
    rig.push("two")
    rig.state.mkdir(parents=True, exist_ok=True)
    with open(rig.state / "first-install.lock", "w") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        timer = rig.deploy_local("--if-moved")
        person = rig.deploy_local()
    assert timer.returncode == 0 and "skipped: first-install.sh is running" in timer.stdout
    assert person.returncode == 75 and "busy: first-install.sh is running" in person.stderr
    assert rig.calls() == []


def test_the_deploy_holds_its_lock_while_it_runs_so_a_second_one_cannot_start_in_the_middle(rig: Rig) -> None:
    rig.push("two")
    marker = rig.stub / "inside"
    probe = rig.stub / "probe.exit"
    # The stub deploy.sh asks, from inside, whether a second deploy-local.sh would be let in.
    deploy = rig.deploy / "infra" / "deploy" / "deploy.sh"
    deploy.write_text(f'#!/bin/sh\ncat >/dev/null\n"{SCRIPT}" --deploy-path "{rig.deploy}" --if-moved > "{marker}" 2>&1 || echo $? > "{probe}"\n')
    git("update-index", "--assume-unchanged", "infra/deploy/deploy.sh", cwd=rig.deploy)
    done = rig.deploy_local()
    assert done.returncode == 0, done.stdout + done.stderr
    assert "skipped: another deploy-local.sh is running" in marker.read_text()
    git("update-index", "--no-assume-unchanged", "infra/deploy/deploy.sh", cwd=rig.deploy)


def test_without_a_path_it_deploys_the_clone_it_is_in_when_that_holds_an_installation(rig: Rig) -> None:
    tip = rig.push("two")
    inside = rig.deploy / "infra" / "deploy" / "deploy-local.sh"
    done = rig.run(script=inside)
    assert done.returncode == 0, done.stdout + done.stderr and f"DEPLOY OK: {tip}" in done.stdout
    # a clone with no installation does not guess: the working copy is refused
    refused = rig.run(script=rig.work / "infra" / "deploy" / "deploy-local.sh")
    assert refused.returncode == 2 and "holds no installation" in refused.stderr


def test_the_instance_names_the_checkout_and_the_state(rig: Rig) -> None:
    tip = rig.push("two")
    done = rig.run("--instance", INSTANCE)
    assert done.returncode == 0, done.stdout + done.stderr and f"DEPLOY OK: {tip}" in done.stdout
    assert rig.log.is_file() and (rig.state / "deploy-local.source").is_file()


@pytest.mark.parametrize("args", [["--bogus"], ["--sha", "abc"], ["--sha"], ["--deploy-path", "relative/dir"], ["--deploy-path", "/srv/../etc"],
                                  ["--deploy-path", "/srv/has space"]])
def test_bad_arguments_are_a_usage_error_before_anything_happens(rig: Rig, args: list[str]) -> None:
    done = rig.run(*args) if args[0] == "--deploy-path" else rig.deploy_local(*args)
    assert done.returncode == 2 and "usage: sudo infra/deploy/deploy-local.sh" in done.stderr
    assert rig.calls() == []


def test_a_directory_that_is_not_a_clone_is_refused(rig: Rig, tmp_path: Path) -> None:
    plain = tmp_path / "srv" / "plain"
    plain.mkdir()
    done = rig.run("--deploy-path", str(plain))
    assert done.returncode == 2 and "is not a git clone" in done.stderr


def test_the_script_is_shellcheck_clean_and_deletes_nothing_but_its_own_record() -> None:
    if shutil.which("shellcheck"):
        done = subprocess.run(["shellcheck", "-x", str(SCRIPT)], capture_output=True, text=True, cwd=ROOT)
        assert done.returncode == 0, done.stdout
    code = "\n".join(line for line in SCRIPT.read_text().splitlines() if not line.lstrip().startswith("#"))
    code = re.sub(r"(?ms)<<'REMOTE'\n.*?\nREMOTE\n", "", code)
    assert re.findall(r"\brm [^;&|\n]+", code) == ['rm -f "$failed_file"']
    for forbidden in ("kill", "docker", "systemctl", "git clean", "git reset", "git checkout"):
        assert forbidden not in code
