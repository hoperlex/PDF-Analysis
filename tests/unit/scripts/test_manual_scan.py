"""`PROD-09-MANUAL-SCAN-01`: `scripts/release/manual_scan.sh` never reports a clean scan it did not run.

The helper is the owner's manual dependency and image scan (`ADR-0021` section 7, line 3;
accepted risk `A-3`). What is under test is the refusal, not the scanners: with a required tool
missing it must exit non-zero, name the tool and never print the success line; with a scanner
that exits non-zero it must exit non-zero and quote what the scanner said; and the success line
appears only when every scanner was present, ran and exited 0.

**Nothing here needs a network, docker or an installed scanner.** The script runs under a
`PATH` that holds only symlinks to the few system programs it uses and stub scanners written by
the test; `MANUAL_SCAN_ROOT` points it at a small synthetic tree (the one real-tree case reads
the repository's own lock files and compose file). Each stub appends what it was called with to
a log, so a case can say which scanner ran, with which arguments, on which input.

The shape of each guard case is the repository's usual one (`test_stand_copy_refusals.py`): the
refusal is shown, and the same invocation with exactly the guarded thing in place is shown not to
refuse. `test_a_check_that_cannot_fail_is_not_a_check` shows the one text check can fail.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/release/manual_scan.sh"
RELEASE_PROCESS = ROOT / "docs/program/RELEASE_PROCESS.md"
BASH = shutil.which("bash") or "/bin/bash"

#: The system programs the script uses besides bash builtins and python3.
SYSTEM_TOOLS = ("mktemp", "rm", "date")

SUCCESS = "MANUAL SCAN RESULT: NO FINDINGS"
NOT_COMPLETE = "MANUAL SCAN RESULT: NOT COMPLETE"
IMAGE_SCANNER_WORDS = "fakescan image --exit-code 1"

STUB = """#!/bin/bash
# stub {name}: records its call, reads the requirement list it was given, then behaves as told.
printf 'CALL\\t{name}\\t%s\\n' "$*" >> "$STUB_LOG"
previous=""
for arg in "$@"; do
    if [ "$previous" = "--requirement" ]; then
        while IFS= read -r line || [ -n "$line" ]; do
            printf 'REQ\\t%s\\n' "$line" >> "$STUB_LOG"
        done < "$arg"
    fi
    previous="$arg"
done
printf '%s\\n' "${{{var}_OUT:-}}"
exit "${{{var}_RC:-0}}"
"""
STUBS = {"pip-audit": "STUB_PIP_AUDIT", "npm": "STUB_NPM", "fakescan": "STUB_IMAGE"}

UV_LOCK = """version = 1
requires-python = "==3.12.*"

[[package]]
name = "demo-lib"
version = "1.2.3"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "other-lib"
version = "0.9"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "the-project"
version = "0.0.0"
source = { virtual = "." }
"""
PACKAGE_LOCK = {
    "lockfileVersion": 3,
    "packages": {
        "": {"name": "web"},
        "node_modules/left-pad": {"version": "1.3.0"},
        "node_modules/a/node_modules/@scope/b": {"version": "2.0.0"},
    },
}
DIGEST_A = "nginx:1.27-alpine@sha256:" + "a" * 64
DIGEST_B = "postgres:17-trixie@sha256:" + "b" * 64
DIGEST_COMMENTED = "ghcr.io/example/ignored:1@sha256:" + "c" * 64
COMPOSE = f"""services:
  postgres:
    build:
      args:
        POSTGRES_BASE_IMAGE: {DIGEST_B}
    image: ${{ALPHA_INSTANCE:?ALPHA_INSTANCE is unset.}}-postgres:17
  api:
    image: ${{ALPHA_INSTANCE:?ALPHA_INSTANCE is unset.}}-api
  # image: {DIGEST_COMMENTED}
  proxy:
    image: {DIGEST_A}
"""


@dataclass
class Harness:
    """One test's world: a stub `bin`, a synthetic tree, a temp dir and the stub log."""

    root: Path
    bin: Path
    tmp: Path
    tree: Path
    log: Path

    def env(self, **extra: str) -> dict[str, str]:
        env = {
            "PATH": str(self.bin),
            "HOME": str(self.root),
            "TMPDIR": str(self.tmp),
            "MANUAL_SCAN_ROOT": str(self.tree),
            "MANUAL_SCAN_IMAGE_SCANNER": IMAGE_SCANNER_WORDS,
            "STUB_LOG": str(self.log),
        }
        env.update(extra)
        return env

    def run(self, *args: str, env: Mapping[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [BASH, str(SCRIPT), *args],
            env=dict(self.env() if env is None else env),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    def calls(self) -> list[tuple[str, str]]:
        if not self.log.exists():
            return []
        rows = [line.split("\t") for line in self.log.read_text(encoding="utf-8").splitlines()]
        return [(row[1], row[2]) for row in rows if row[0] == "CALL"]

    def requirements(self) -> list[str]:
        if not self.log.exists():
            return []
        rows = [line.split("\t") for line in self.log.read_text(encoding="utf-8").splitlines()]
        return [row[1] for row in rows if row[0] == "REQ"]


def _link_system_tools(bin_dir: Path) -> None:
    python = Path(os.path.realpath(sys.executable))
    (bin_dir / "python3").symlink_to(python)
    for tool in SYSTEM_TOOLS:
        found = shutil.which(tool)
        assert found, f"{tool} is not on this host's PATH"
        (bin_dir / tool).symlink_to(Path(found).resolve())


def _write_stub(bin_dir: Path, name: str) -> None:
    path = bin_dir / name
    path.write_text(STUB.format(name=name, var=STUBS[name]), encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _write_tree(tree: Path) -> None:
    (tree / "web").mkdir(parents=True)
    (tree / "infra/deploy").mkdir(parents=True)
    (tree / "uv.lock").write_text(UV_LOCK, encoding="utf-8")
    (tree / "web/package-lock.json").write_text(json.dumps(PACKAGE_LOCK), encoding="utf-8")
    (tree / "infra/deploy/compose.server.yml").write_text(COMPOSE, encoding="utf-8")


@pytest.fixture
def world(tmp_path_factory: pytest.TempPathFactory) -> Harness:
    # Neutral names: the script prints these paths and a case greps its output for the word it
    # must never print, so a test-named directory must not carry that word.
    root = tmp_path_factory.mktemp("w")
    harness = Harness(
        root=root, bin=root / "bin", tmp=root / "tmp", tree=root / "tree", log=root / "stub.log"
    )
    harness.bin.mkdir()
    harness.tmp.mkdir()
    _link_system_tools(harness.bin)
    for name in STUBS:
        _write_stub(harness.bin, name)
    _write_tree(harness.tree)
    return harness


def _missing_names(output: str) -> set[str]:
    return {m.group(1) for m in re.finditer(r"^MISSING ([a-z0-9 -]+?):", output, re.M)}


def _tree_digest(tree: Path) -> dict[str, str]:
    return {
        str(p.relative_to(tree)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(tree.rglob("*"))
        if p.is_file()
    }


def _no_success_claim(result: subprocess.CompletedProcess[str]) -> None:
    combined = result.stdout + result.stderr
    assert SUCCESS not in combined
    assert not re.search(r"(?i)\bpass(ed|es)?\b", combined), combined


# --- the tools --------------------------------------------------------------------------------


def test_check_tools_is_ready_only_when_every_required_tool_is_present(world: Harness) -> None:
    result = world.run("--check-tools")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CHECK-TOOLS: READY" in result.stdout
    assert _missing_names(result.stdout) == set()
    assert world.calls() == [], "--check-tools must not run a scanner"


@pytest.mark.parametrize(
    ("hidden", "named"),
    [
        ("pip-audit", "pip-audit"),
        ("npm", "npm"),
        ("fakescan", "image scanner"),
        ("python3", "python3"),
    ],
)
def test_check_tools_detects_each_removal_alone(world: Harness, hidden: str, named: str) -> None:
    (world.bin / hidden).unlink()
    result = world.run("--check-tools")
    assert result.returncode != 0
    assert _missing_names(result.stdout) == {named}, result.stdout
    assert "CHECK-TOOLS: READY" not in result.stdout
    assert "required tool(s) missing" in result.stderr


def test_check_tools_detects_an_image_scanner_nobody_named(world: Harness) -> None:
    env = world.env()
    del env["MANUAL_SCAN_IMAGE_SCANNER"]
    result = world.run("--check-tools", env=env)
    assert result.returncode != 0
    assert _missing_names(result.stdout) == {"image scanner"}
    assert "MANUAL_SCAN_IMAGE_SCANNER is not set" in result.stdout


def test_check_tools_names_all_when_everything_is_hidden(world: Harness) -> None:
    for name in ("pip-audit", "npm", "fakescan", "python3"):
        (world.bin / name).unlink()
    result = world.run("--check-tools")
    assert result.returncode != 0
    assert _missing_names(result.stdout) == {"python3", "pip-audit", "npm", "image scanner"}


def test_a_scan_with_every_scanner_hidden_exits_non_zero_and_claims_nothing(world: Harness) -> None:
    for name in ("pip-audit", "npm", "fakescan"):
        (world.bin / name).unlink()
    result = world.run()
    assert result.returncode == 2, result.stdout + result.stderr
    assert _missing_names(result.stdout) == {"pip-audit", "npm", "image scanner"}
    assert NOT_COMPLETE in result.stdout
    for scanner in ("pip-audit", "npm audit", "image scanner"):
        assert f"NOT RUN {scanner} (missing)" in result.stdout
    _no_success_claim(result)
    assert world.calls() == []


def test_a_scan_with_nothing_on_the_path_still_refuses(world: Harness) -> None:
    empty = world.root / "empty"
    empty.mkdir()
    result = world.run(env={**world.env(), "PATH": str(empty)})
    assert result.returncode != 0
    assert SUCCESS not in result.stdout + result.stderr
    assert "NOT COMPLETE" in result.stdout or "NOT COMPLETE" in result.stderr


@pytest.mark.parametrize(
    ("hidden", "named", "not_run"),
    [
        ("pip-audit", "pip-audit", "pip-audit (missing)"),
        ("npm", "npm", "npm audit (missing)"),
        ("fakescan", "image scanner", "image scanner (missing)"),
    ],
)
def test_one_missing_scanner_makes_a_scan_not_complete_though_the_others_run_clean(
    world: Harness, hidden: str, named: str, not_run: str
) -> None:
    (world.bin / hidden).unlink()
    result = world.run()
    assert result.returncode == 2, result.stdout + result.stderr
    assert _missing_names(result.stdout) == {named}
    assert f"NOT RUN {not_run}" in result.stdout
    assert NOT_COMPLETE in result.stdout
    _no_success_claim(result)
    ran = {name for name, _ in world.calls()}
    assert ran == {"pip-audit", "npm", "fakescan"} - {hidden}, "the other scanners still run"


# --- the scanners ------------------------------------------------------------------------------


def test_every_scanner_clean_gives_the_success_line_and_exit_zero(world: Harness) -> None:
    result = world.run()
    assert result.returncode == 0, result.stdout + result.stderr
    lines = result.stdout.splitlines()
    assert lines[-1].startswith(SUCCESS)
    assert result.stdout.count("MANUAL SCAN RESULT:") == 1
    assert "D-122 stays open" in result.stdout
    assert "scanners that ran and exited 0: 4" in result.stdout  # pip-audit, npm audit, 2 images
    calls = world.calls()
    assert [name for name, _ in calls] == ["pip-audit", "npm", "fakescan", "fakescan"]
    assert list(world.tmp.iterdir()) == [], "the script leaves its temporary directory behind"


def test_the_scanners_are_called_with_the_arguments_the_adr_names_on_the_inventory(world: Harness) -> None:
    result = world.run()
    assert result.returncode == 0
    by_name = {}
    for name, args in world.calls():
        by_name.setdefault(name, []).append(args)
    (pip_args,) = by_name["pip-audit"]
    assert re.fullmatch(r"--requirement \S+/requirements\.txt --no-deps --disable-pip --strict", pip_args)
    assert world.requirements() == ["demo-lib==1.2.3", "other-lib==0.9"]
    assert by_name["npm"] == [f"audit --package-lock-only --prefix {world.tree}/web"]
    assert sorted(by_name["fakescan"]) == sorted(
        f"image --exit-code 1 {ref}" for ref in (DIGEST_A, DIGEST_B)
    ), "exactly the digest references of the compose file, none from a comment, none built locally"
    assert "left-pad@1.3.0" in result.stdout and "@scope/b@2.0.0" in result.stdout
    assert "demo-lib==1.2.3" in result.stdout
    assert "project itself, not a dependency: the-project" in result.stdout


@pytest.mark.parametrize(
    ("stub", "label"),
    [
        ("STUB_PIP_AUDIT", "pip-audit"),
        ("STUB_NPM", "npm audit"),
        ("STUB_IMAGE", "image scanner"),
    ],
)
def test_a_scanner_that_exits_non_zero_makes_the_scan_exit_non_zero_and_is_quoted(
    world: Harness, stub: str, label: str
) -> None:
    message = f"VULN-0001 {label} found demo-lib 1.2.3 is vulnerable (CVE-0000-0000)"
    result = world.run(env={**world.env(), f"{stub}_RC": "1", f"{stub}_OUT": message})
    assert result.returncode == 1, result.stdout + result.stderr
    assert f"    | {message}" in result.stdout.splitlines(), "the finding is quoted line by line"
    assert re.search(rf"^FINDING {re.escape(label)}.*: exit 1 ", result.stdout, re.M)
    assert re.search(rf"^FINDING {re.escape(label)}", result.stdout.split("== Result")[1], re.M)
    assert result.stdout.splitlines()[-1].startswith(NOT_COMPLETE)
    _no_success_claim(result)


def test_a_scanner_that_could_not_reach_its_database_is_a_finding_too(world: Harness) -> None:
    unreachable = "ERROR: could not reach the vulnerability service"
    result = world.run(env={**world.env(), "STUB_NPM_RC": "1", "STUB_NPM_OUT": unreachable})
    assert result.returncode == 1
    assert f"    | {unreachable}" in result.stdout
    _no_success_claim(result)


def test_one_image_with_a_finding_is_enough_and_the_other_is_still_scanned(world: Harness) -> None:
    result = world.run(env={**world.env(), "STUB_IMAGE_RC": "7", "STUB_IMAGE_OUT": "HIGH: libfoo"})
    assert result.returncode == 1
    assert len([c for c in world.calls() if c[0] == "fakescan"]) == 2
    assert result.stdout.count("FINDING image scanner:") >= 2
    _no_success_claim(result)


def test_a_finding_and_a_missing_scanner_together_exit_two_and_list_both(world: Harness) -> None:
    (world.bin / "npm").unlink()
    result = world.run(env={**world.env(), "STUB_PIP_AUDIT_RC": "1", "STUB_PIP_AUDIT_OUT": "VULN-9"})
    assert result.returncode == 2
    assert "FINDING pip-audit (exit 1)" in result.stdout
    assert "NOT RUN npm audit (missing)" in result.stdout
    _no_success_claim(result)


# --- the inventory -----------------------------------------------------------------------------


def _rewrite(world: Harness, rel: str, text: str | None) -> None:
    path = world.tree / rel
    if text is None:
        path.unlink()
    else:
        path.write_text(text, encoding="utf-8")


@pytest.mark.parametrize(
    ("rel", "text", "expected"),
    [
        (
            "uv.lock",
            UV_LOCK + '\n[[package]]\nname = "gitlib"\nversion = "1"\nsource = { git = "https://example.invalid/x" }\n',
            "GAP python package gitlib 1 has source git",
        ),
        ("uv.lock", None, "INPUT ERROR cannot read uv.lock"),
        ("uv.lock", "this is not toml [", "INPUT ERROR cannot parse uv.lock"),
        ("uv.lock", 'version = 1\n[[package]]\nname = "p"\nversion = "1"\nsource = { virtual = "." }\n', "INPUT ERROR uv.lock lists no registry package"),
        ("web/package-lock.json", None, "INPUT ERROR cannot read web/package-lock.json"),
        ("web/package-lock.json", '{"lockfileVersion": 1, "dependencies": {}}', "INPUT ERROR cannot read the packages of web/package-lock.json"),
        ("infra/deploy/compose.server.yml", COMPOSE.replace(DIGEST_A, "nginx:1.27").replace(DIGEST_B, "postgres:17"), "INPUT ERROR compose.server.yml names no image digest"),
        ("infra/deploy/compose.server.yml", None, "INPUT ERROR cannot read infra/deploy/compose.server.yml"),
    ],
)
def test_an_input_the_scanners_cannot_cover_makes_the_scan_not_complete(
    world: Harness, rel: str, text: str | None, expected: str
) -> None:
    _rewrite(world, rel, text)
    result = world.run()  # every stub exits 0: only the inventory can refuse here
    assert result.returncode == 2, result.stdout + result.stderr
    assert expected in result.stdout, result.stdout
    assert NOT_COMPLETE in result.stdout
    _no_success_claim(result)


def test_the_inventory_guard_can_fail_the_same_tree_unspoiled_is_clean(world: Harness) -> None:
    assert world.run().returncode == 0


def test_a_scan_changes_nothing_in_the_tree_it_reads(world: Harness) -> None:
    before = _tree_digest(world.tree)
    world.run()
    world.run(env={**world.env(), "STUB_NPM_RC": "1"})
    assert _tree_digest(world.tree) == before
    assert list(world.tmp.iterdir()) == []


def test_the_real_tree_inventory_is_what_the_lock_files_and_compose_say(world: Harness) -> None:
    env = world.env()
    env["MANUAL_SCAN_ROOT"] = str(ROOT)
    result = world.run(env=env)
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    expected = sorted(
        f"{p['name']}=={p['version']}" for p in lock["package"] if "registry" in p["source"]
    )
    assert expected, "uv.lock lists registry packages"
    assert sorted(world.requirements()) == expected
    code = "\n".join(
        line
        for line in (ROOT / "infra/deploy/compose.server.yml").read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    )
    refs = set(re.findall(r"[A-Za-z0-9][A-Za-z0-9._/:-]*@sha256:[0-9a-f]{64}", code))
    assert refs
    scanned = {args.rsplit(" ", 1)[1] for name, args in world.calls() if name == "fakescan"}
    assert scanned == refs
    assert "built on the host, NOT scanned by this helper" in result.stdout


# --- the file itself ---------------------------------------------------------------------------


def test_usage_errors_exit_64_and_run_nothing(world: Harness) -> None:
    for args in (("--nope",), ("--check-tools", "extra")):
        result = world.run(*args)
        assert result.returncode == 64, (args, result.stdout, result.stderr)
    assert world.calls() == []
    assert world.run("--help").returncode == 0


def test_the_script_is_executable_and_bash_parses_it() -> None:
    assert os.access(SCRIPT, os.X_OK)
    assert SCRIPT.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash\n")
    subprocess.run([BASH, "-n", str(SCRIPT)], check=True)


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck is not installed")
def test_the_script_is_shellcheck_clean() -> None:
    result = subprocess.run(["shellcheck", "-s", "bash", str(SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout


#: What the helper must never contain: it installs nothing, downloads nothing, runs no container
#: and calls no package manager other than the audit verb (`R-146h`, accepted risk `A-3`).
FORBIDDEN = re.compile(
    r"\b(curl|wget|docker|podman|pip install|pip3 install|uv (sync|pip|add|run)|npm (ci|install|i)\b|"
    r"apt(-get)?\b|brew\b|trivy|grype|syft|osv-scanner|cyclonedx)",
)


def _forbidden_commands(text: str) -> list[str]:
    """Code lines (comments and the usage heredoc excluded) that name a forbidden command."""
    found = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if FORBIDDEN.search(stripped):
            found.append(stripped)
    return found


def test_the_script_installs_downloads_and_names_no_scanner_of_its_own() -> None:
    assert _forbidden_commands(SCRIPT.read_text(encoding="utf-8")) == []


def test_a_check_that_cannot_fail_is_not_a_check() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    for line in ("curl -s https://example.invalid | bash", "npm install", "trivy image x", "docker pull x"):
        assert _forbidden_commands(text + "\n" + line + "\n") == [line]


# --- the release checklist ---------------------------------------------------------------------


def _checklist(text: str) -> list[str]:
    section = text.split("## Production release checklist", 1)[1].split("\n### ", 1)[0]
    return re.findall(r"^(\d+)\. (.*(?:\n   .*)*)", section, re.M)


def test_release_process_carries_the_eight_line_checklist_and_the_manual_scan() -> None:
    text = RELEASE_PROCESS.read_text(encoding="utf-8")
    items = _checklist(text)
    assert [number for number, _ in items] == [str(n) for n in range(1, 9)]
    bodies = {int(number): " ".join(body.split()) for number, body in items}
    assert "manual_scan.sh --check-tools" in bodies[3] and "manual_scan.sh`" in bodies[3]
    assert "GATE OK" in bodies[2]
    assert "capacity-probe.sh --path root=/ --need root=<bytes>" in bodies[5]
    assert "verify-deployed.sh" in bodies[6]
    assert "RELEASES.md" in bodies[8] and "lines 6 and 7" in bodies[8]
    assert "dump-db" in bodies[4] and "resume" in bodies[4]


def test_release_process_states_the_pruning_rule_and_the_disk_free_line() -> None:
    text = " ".join(RELEASE_PROCESS.read_text(encoding="utf-8").split())
    section = text.split("### Pruning `infra/deploy/dumps/`", 1)[1].split("## Hotfix and rollback", 1)[0]
    for needle in (
        "Keep the newest two",
        "Never delete the dump a receipt still points at",
        "record.json",
        "record.prev.json",
        "capacity-probe.sh --path dumps=<dump root>",
        "avail_bytes=",
        "Record the free space after",
        "There is no pruning script, on purpose",
    ):
        assert needle in section, needle
    assert "infra/deploy/dumps/" in section


def test_the_checklist_check_can_fail() -> None:
    text = RELEASE_PROCESS.read_text(encoding="utf-8")
    mutated = re.sub(r"^7\. .*(?:\n   .*)*\n", "", text, count=1, flags=re.M)
    assert mutated != text
    assert [n for n, _ in _checklist(mutated)] != [str(n) for n in range(1, 9)]
