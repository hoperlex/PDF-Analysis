"""GATE-PKG-01: the gate refuses to start on a host that cannot measure it, and waits fairly.

Every refusal here is a rule that was missing for a real failed gate (W48-W55a records):
a worktree without the corpus link or ``web/node_modules``, a dirty tree, a disk MinIO
cannot write to, a host without memory headroom, two gates at once. Each rule has a test
that turns it red, and the slot is exercised with real processes, because a lock that is
only ever read by the code that took it proves nothing.
"""

from __future__ import annotations

import fcntl
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "gate_host.py"
MAKEFILE = ROOT / "Makefile"

spec = importlib.util.spec_from_file_location("gate_host", SCRIPT)
assert spec and spec.loader
gate_host = importlib.util.module_from_spec(spec)
sys.modules["gate_host"] = gate_host
spec.loader.exec_module(gate_host)


def limits(**overrides: object) -> "gate_host.Limits":
    values = dict(min_available_mib=3072, min_free_disk_mib=6144, max_load=None, wait_max_s=60,
                  heartbeat_s=300, poll_s=1, sample_s=1)
    values.update(overrides)
    return gate_host.Limits(**values)


# --- a fake /proc --------------------------------------------------------------------------


def fake_proc(tmp_path: Path, *, mem_available_kb: int = 8 * 1024 * 1024, load: str = "1.00") -> Path:
    proc = tmp_path / "proc"
    proc.mkdir()
    (proc / "meminfo").write_text(
        f"MemTotal:       11000000 kB\nMemFree:          100000 kB\nMemAvailable:   {mem_available_kb} kB\n",
        encoding="ascii",
    )
    (proc / "loadavg").write_text(f"{load} 1.00 1.00 1/100 12345\n", encoding="ascii")
    return proc


def add_process(proc: Path, pid: int, ppid: int, argv: list[str], cwd: str = "/") -> None:
    entry = proc / str(pid)
    entry.mkdir()
    (entry / "cmdline").write_bytes(b"\0".join(part.encode() for part in argv) + b"\0")
    (entry / "status").write_text(f"Name:\tx\nPPid:\t{ppid}\n", encoding="utf-8")
    (entry / "stat").write_text(f"{pid} (x) S {ppid} 0 0\n", encoding="utf-8")
    os.symlink(cwd, entry / "cwd")


def test_meminfo_is_read_in_mebibytes_and_a_missing_line_refuses(tmp_path: Path) -> None:
    proc = fake_proc(tmp_path, mem_available_kb=3 * 1024 * 1024 + 512)
    assert gate_host.available_mib(proc) == 3072
    (proc / "meminfo").write_text("MemTotal: 1 kB\n", encoding="ascii")
    with pytest.raises(gate_host.Refusal, match="MemAvailable"):
        gate_host.available_mib(proc)


@pytest.mark.parametrize("argv,expected", [
    (["make", "gate"], True),
    (["/usr/bin/make", "-C", "/root/x", "gate"], True),
    (["make", "--no-print-directory", "gate", "GATE_BASE=abc"], True),
    (["make", "gate-static"], False),
    (["make", "light-acceptance"], False),
    (["bash", "-c", "while pgrep -f 'make gate'; do sleep 5; done"], False),
    ([], False),
])
def test_a_gate_is_recognised_by_its_argv_not_by_a_pattern(argv: list[str], expected: bool) -> None:
    assert gate_host.is_gate_make(argv) is expected


def test_foreign_gates_skip_this_gate_and_gates_queued_behind_its_slot(tmp_path: Path) -> None:
    proc = fake_proc(tmp_path)
    add_process(proc, 1, 0, ["init"])
    add_process(proc, 100, 1, ["make", "gate"], cwd="/root/old-lane")          # runs: foreign
    add_process(proc, 200, 1, ["make", "gate"], cwd="/root/queued")            # waits for our slot
    add_process(proc, 201, 200, ["bash", "-c", "x"])
    add_process(proc, 202, 201, [".venv/bin/python", "scripts/gate_host.py", "slot", "--owner-pid", "200"])
    add_process(proc, 300, 1, ["make", "gate"], cwd="/root/this")              # this gate
    add_process(proc, 301, 300, ["bash"])
    assert gate_host.foreign_gates(proc, own_pid=300) == [(100, "/root/old-lane")]


def test_headroom_names_each_missing_condition(tmp_path: Path) -> None:
    proc = fake_proc(tmp_path, mem_available_kb=1024 * 1024, load="30.0")
    add_process(proc, 1, 0, ["init"])
    add_process(proc, 100, 1, ["make", "gate"], cwd="/root/other")
    problems = gate_host.headroom_problems(limits(max_load=10.0), proc_root=proc, own_pid=1)
    assert any("MemAvailable 1024 MiB < GATE_MIN_AVAILABLE_MIB=3072" in p for p in problems)
    assert any("load average 30.0 > GATE_MAX_LOAD=10" in p for p in problems)
    assert any("pid 100 in /root/other" in p for p in problems)


def test_headroom_is_clear_on_a_quiet_host(tmp_path: Path) -> None:
    proc = fake_proc(tmp_path)
    add_process(proc, 1, 0, ["init"])
    assert gate_host.headroom_problems(limits(max_load=10.0), proc_root=proc, own_pid=1) == []


# --- preflight -------------------------------------------------------------------------------


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, text=True, capture_output=True).stdout.strip()


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    repo = tmp_path / "checkout"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "gate@example.test")
    git(repo, "config", "user.name", "gate")
    (repo / ".gitignore").write_text(".venv/\n.local/\n.env\nweb/node_modules/\n", encoding="utf-8")
    git(repo, "add", ".gitignore")
    git(repo, "commit", "-q", "-m", "base")
    return repo


def provision(repo: Path) -> None:
    python = repo / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\n", encoding="utf-8")
    python.chmod(0o755)
    (repo / "web" / "node_modules").mkdir(parents=True)
    (repo / ".local" / "norms" / "corpus").mkdir(parents=True)
    (repo / ".env").write_text("FOUNDATION_INSTANCE=x\n", encoding="utf-8")


class Statvfs:
    def __init__(self, free_mib: int) -> None:
        self.f_bavail = free_mib
        self.f_frsize = 1024 * 1024


def run_preflight(repo: Path, *, free_mib: int = 50_000, docker: object = None) -> list[str]:
    def docker_root() -> Path:
        if isinstance(docker, Exception):
            raise docker
        return repo
    return gate_host.preflight_findings(repo, limits(), docker_root=docker_root,
                                        statvfs=lambda _path: Statvfs(free_mib), log=lambda _line: None)


def test_a_provisioned_clean_checkout_may_start(checkout: Path) -> None:
    provision(checkout)
    assert run_preflight(checkout) == []


def test_a_fresh_worktree_is_refused_with_every_missing_piece_named(checkout: Path) -> None:
    findings = " | ".join(run_preflight(checkout))
    for expected in (".venv/bin/python is missing", "web/node_modules is missing",
                     ".local/norms/corpus is missing", ".env is missing"):
        assert expected in findings


def test_a_dirty_tree_is_refused_because_the_gate_certifies_a_commit(checkout: Path) -> None:
    provision(checkout)
    (checkout / "draft.py").write_text("x = 1\n", encoding="utf-8")
    assert run_preflight(checkout) == [
        "the tree has 1 uncommitted path(s); a complete gate certifies a commit, so commit or remove them"
    ]


def test_low_disk_is_refused_for_both_filesystems(checkout: Path) -> None:
    provision(checkout)
    findings = run_preflight(checkout, free_mib=1000)
    assert len(findings) == 2
    assert all("1000 MiB free, below GATE_MIN_FREE_DISK_MIB=6144" in f for f in findings)
    assert any("worktree filesystem" in f for f in findings)
    assert any("docker data filesystem" in f for f in findings)


def test_an_unreachable_docker_is_refused(checkout: Path) -> None:
    provision(checkout)
    assert run_preflight(checkout, docker=gate_host.Refusal("docker info failed (exit 1): no daemon")) == [
        "docker info failed (exit 1): no daemon"
    ]


@pytest.mark.parametrize("name,value", [("GATE_MIN_AVAILABLE_MIB", "lots"), ("GATE_WAIT_MAX_S", "-1")])
def test_a_malformed_threshold_refuses_instead_of_defaulting(name: str, value: str) -> None:
    with pytest.raises(gate_host.Refusal, match=name):
        gate_host.Limits.from_env({name: value})


# --- the battery's first suites ----------------------------------------------------------------


def test_first_suites_follow_changed_contexts_and_changed_suites_only() -> None:
    suites = gate_host.first_suites(
        [
            "src/auditmanager/norms/search.py",
            "tests/integration/releases/test_loader.py",
            "tests/integration/foundation/test_x.py",
            "src/auditmanager/unmapped_context/x.py",
            "docs/program/CURRENT_STATE.md",
            "web/src/_pages/home/ui/page.tsx",
        ],
        ROOT,
        gate_host.load_context_suites(),
    )
    assert suites == ["norms", "releases"]


def test_the_context_map_is_the_light_acceptance_map() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import light_acceptance
    finally:
        sys.path.remove(str(ROOT / "scripts"))
    assert gate_host.load_context_suites() == light_acceptance.CONTEXT_SUITES


def test_an_explicit_base_must_be_a_full_ancestor_sha(checkout: Path) -> None:
    with pytest.raises(gate_host.Refusal, match="GATE_BASE"):
        gate_host.battery_base(checkout, {"GATE_BASE": "abc123"})
    base = git(checkout, "rev-parse", "HEAD")
    assert gate_host.battery_base(checkout, {"GATE_BASE": base}) == base


# --- the slot, with real processes -------------------------------------------------------------


def slot_env(tmp_path: Path, proc: Path, **extra: str) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GATE_")}
    env.update({
        "GATE_SLOT_DIR": str(tmp_path / "slot"),
        "GATE_PROC_ROOT": str(proc),
        "GATE_MIN_AVAILABLE_MIB": "1",
        "GATE_POLL_S": "1",
        "GATE_HEARTBEAT_S": "1",
        "GATE_SAMPLE_S": "1",
        "GATE_WAIT_MAX_S": "30",
    })
    env.update(extra)
    return env


def run_slot(owner: int, env: dict[str, str], timeout: float = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), "slot", "--owner-pid", str(owner)],
                          env=env, text=True, capture_output=True, timeout=timeout)


def lock_is_free(path: Path) -> bool:
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return False
    finally:
        os.close(fd)
    return True


def wait_until(condition, seconds: float = 10.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.2)
    return condition()


@pytest.fixture
def owner():
    process = subprocess.Popen(["sleep", "300"])
    yield process
    if process.poll() is None:
        process.kill()
        process.wait()


def test_the_slot_is_held_while_make_lives_and_freed_when_it_ends(tmp_path: Path, owner) -> None:
    proc = fake_proc(tmp_path)
    env = slot_env(tmp_path, proc)
    result = run_slot(owner.pid, env)
    assert result.returncode == 0, result.stderr
    assert "GATE SLOT HELD:" in result.stdout
    lock = tmp_path / "slot" / "gate-slot.flock"
    record = json.loads((tmp_path / "slot" / "gate-slot.json").read_text(encoding="utf-8"))
    assert record["owner_pid"] == owner.pid
    assert not lock_is_free(lock), "the holder must keep the slot after the slot command exits"

    second = run_slot(owner.pid, slot_env(tmp_path, proc, GATE_WAIT_MAX_S="2"))
    assert second.returncode == 3
    assert "GATE NOT STARTED: waited" in second.stderr
    assert f"held by pid {record['holder_pid']}" in second.stderr

    report = subprocess.run([sys.executable, str(SCRIPT), "report", "--owner-pid", str(owner.pid)],
                            env=env, text=True, capture_output=True, timeout=30)
    assert wait_until(lambda: Path(record["samples"]).exists())
    assert report.returncode == 0

    owner.send_signal(signal.SIGKILL)
    owner.wait()
    assert wait_until(lambda: lock_is_free(lock)), "the slot must free once make is gone"
    assert wait_until(lambda: not (tmp_path / "slot" / "gate-slot.json").exists())


def test_the_slot_waits_for_memory_and_then_refuses_to_start(tmp_path: Path, owner) -> None:
    proc = fake_proc(tmp_path, mem_available_kb=512 * 1024)
    result = run_slot(owner.pid, slot_env(tmp_path, proc, GATE_MIN_AVAILABLE_MIB="3072", GATE_WAIT_MAX_S="2"))
    assert result.returncode == 3
    assert "GATE NOT STARTED: waited" in result.stderr
    assert "MemAvailable 512 MiB < GATE_MIN_AVAILABLE_MIB=3072" in result.stderr
    assert "GATE SLOT: still waiting" in result.stdout
    assert lock_is_free(tmp_path / "slot" / "gate-slot.flock"), "a refused gate must not keep the slot"


def test_the_slot_refuses_when_the_calling_make_is_already_gone(tmp_path: Path) -> None:
    finished = subprocess.Popen(["true"])
    finished.wait()
    result = run_slot(finished.pid, slot_env(tmp_path, fake_proc(tmp_path)))
    assert result.returncode == 3
    assert f"the calling make (pid {finished.pid}) is gone" in result.stderr


# --- the Makefile keeps every component of the gate ----------------------------------------------


def recipe(text: str, target: str) -> str:
    start = text.index(f"\n{target}:")
    end = text.find("\n\n", start + 1)
    return text[start:end]


def function(text: str, name: str) -> str:
    start = text.index(f"{name}() {{")
    return text[start:text.index("\n}", start)]


def test_the_gate_runs_cheap_refusals_first_and_keeps_every_component() -> None:
    text = MAKEFILE.read_text(encoding="utf-8")
    assert "\ngate: gate-preflight gate-slot gate-static foundation\n" in text
    assert "scripts/gate_host.py preflight" in recipe(text, "gate-preflight")
    assert 'scripts/gate_host.py slot --owner-pid "$$PPID"' in recipe(text, "gate-slot")
    static = recipe(text, "gate-static")
    order = [static.index(step) for step in ("check_whitespace", "run_frontend", "load_env", "run_contract")]
    assert order == sorted(order)
    gate = recipe(text, "gate")
    assert gate.index("run_battery") < gate.index("gate_memory_report") < gate.index('"GATE OK:')


def test_tests_contract_moves_out_of_the_battery_without_leaving_the_gate() -> None:
    text = MAKEFILE.read_text(encoding="utf-8")
    battery, contract = function(text, "run_battery"), function(text, "run_contract")
    assert "--ignore=tests/contract \\" in battery
    assert "tests/contract \\" in contract
    for cp00 in ("test_cp00_candidate.py", "test_cp00_final_state.py", "test_validate_bootstrap.py"):
        assert f"--ignore=tests/contract/{cp00}" in contract
        assert cp00 not in battery.split("--ignore=tests/contract \\")[1]
    assert "--ignore=tests/checkpoint" in battery and "--ignore=tests/integration/foundation" in battery


def test_the_first_suites_are_skipped_in_the_rest_of_the_battery() -> None:
    battery = function(MAKEFILE.read_text(encoding="utf-8"), "run_battery")
    assert 'skip+=("--ignore=tests/integration/$$suite")' in battery
    assert '"$${skip[@]}"' in battery
    assert battery.index('"$${first[@]/#/tests/integration/}"') < battery.index("tests --ignore=tests/checkpoint")
