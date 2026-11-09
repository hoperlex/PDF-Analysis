"""`EXEC2-AGENT-01` -- B2 section 11, test 3 (the package half): the agent package is deterministic.

``package.py`` builds the tarball the API image serves (``EXEC2-ENROLL-01``). The same inputs must give the same
bytes in any directory, at any time, under any umask; the archive's root holds ``install.sh``; tests, the
workspace and the Claude Code bridge are not in it; and the image build runs this script in the place the
stand reads.
"""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

import pytest

_SUPPORT = "executor_runner_agent_support"
if _SUPPORT not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_SUPPORT, Path(__file__).with_name("_agent_support.py"))
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_SUPPORT] = _module
    _spec.loader.exec_module(_module)
A = sys.modules[_SUPPORT]
package = A.load_module("exec_package_under_test", A.RUNNER_DIR / "package.py")

VERSION = "0.9.0"
NAME = f"auditmanager-agent-{VERSION}.tar.gz"


def _build(out: Path, source: Path = A.RUNNER_DIR, version: str = VERSION) -> tuple[subprocess.CompletedProcess, Path]:
    result = subprocess.run(
        [sys.executable, str(A.RUNNER_DIR / "package.py"), "--version", version, "--out", str(out), "--source", str(source)],
        capture_output=True, text=True, timeout=60, cwd=out.parent)
    return result, out / f"auditmanager-agent-{version}.tar.gz"


def _members(archive: Path) -> list[tarfile.TarInfo]:
    with tarfile.open(archive, "r:gz") as handle:
        return handle.getmembers()


def test_two_builds_are_byte_identical_and_the_printed_digest_is_the_files(tmp_path):
    first, second = tmp_path / "one", tmp_path / "two"
    one, archive_one = _build(first)
    two, archive_two = _build(second)
    assert one.returncode == two.returncode == 0, one.stderr + two.stderr
    assert archive_one.read_bytes() == archive_two.read_bytes()
    digest = hashlib.sha256(archive_one.read_bytes()).hexdigest()
    assert one.stdout.strip() == two.stdout.strip() == digest
    assert (first / (NAME + ".sha256")).read_text() == f"{digest}  {NAME}\n"  # sha256sum format, ENROLL-01's reader
    assert sorted(path.name for path in first.iterdir()) == [NAME, NAME + ".sha256"]


def test_the_bytes_do_not_depend_on_the_directory_the_clock_the_file_times_the_modes_or_the_umask(tmp_path):
    reference, archive = _build(tmp_path / "reference")
    assert reference.returncode == 0, reference.stderr
    copy = tmp_path / "elsewhere" / "deep" / "runner"
    shutil.copytree(A.RUNNER_DIR, copy, ignore=shutil.ignore_patterns("__pycache__"))
    for path in copy.rglob("*"):
        os.utime(path, (1_000_000_000, 1_000_000_000))
        if path.is_file():
            path.chmod(0o600)
    (copy / "a-stray-file.txt").write_text("not in the package")
    (copy / "tests").mkdir()
    (copy / "tests" / "test_x.py").write_text("x")
    old_umask = os.umask(0o077)
    try:
        other, other_archive = _build(tmp_path / "other-out", source=copy)
    finally:
        os.umask(old_umask)
    time.sleep(1.1)  # a build one second later
    later, later_archive = _build(tmp_path / "later-out", source=copy)
    assert other.returncode == later.returncode == 0, other.stderr + later.stderr
    assert archive.read_bytes() == other_archive.read_bytes() == later_archive.read_bytes()


def test_the_archive_is_sorted_rootless_and_carries_no_time_owner_or_name(tmp_path):
    result, archive = _build(tmp_path / "out")
    assert result.returncode == 0, result.stderr
    members = _members(archive)
    names = [member.name for member in members]
    assert names == sorted(names) and len(set(names)) == len(names)
    assert set(names) == set(package.PACKAGE_FILES) | {"VERSION"}
    assert "install.sh" in names and not any("/" in name or name.startswith(".") for name in names)
    for member in members:
        assert member.isreg() and member.mtime == 0 and member.uid == member.gid == 0
        assert member.uname == "" and member.gname == "" and member.devmajor == member.devminor == 0
        assert member.mode == (0o755 if member.name == "install.sh" else 0o644), member.name
    raw = archive.read_bytes()
    assert raw[:2] == b"\x1f\x8b" and raw[3] == 0, "gzip header: no file name (FLG = 0)"
    assert raw[4:8] == b"\x00\x00\x00\x00", "gzip header: no time"
    # `TarFile.format` of an archive opened for reading is the library's default (PAX since Python 3.8), not what the
    # archive was written in; the format is in the first header block: the POSIX ustar magic and version at offset 257,
    # and a regular file (typeflag `0`) first, not a pax extended header (`x`).
    tar = gzip.decompress(raw)
    assert tar[257:265] == b"ustar\x0000", "POSIX ustar, not GNU ('ustar  ') and not the old v7 header"
    assert tar[156:157] == tarfile.REGTYPE, "the first block is a file, not a pax extended header"


def test_the_content_is_the_sources_and_the_version_the_argument(tmp_path):
    result, archive = _build(tmp_path / "out", version="12.34.5")
    assert result.returncode == 0, result.stderr
    with tarfile.open(tmp_path / "out" / "auditmanager-agent-12.34.5.tar.gz", "r:gz") as handle:
        assert handle.extractfile("VERSION").read() == b"12.34.5\n"
        for name in package.PACKAGE_FILES:
            assert handle.extractfile(name).read() == (A.RUNNER_DIR / name).read_bytes(), name


def test_tests_the_workspace_the_bridge_and_the_builder_are_not_in_the_package():
    assert set(package.PACKAGE_FILES) == {
        "install.sh", "agent.py", "runner_client.py", "detect.py", "host_mode.py", "api_answer.py", "codex_answer.py",
        "claude_answer.py", "pdf-analysis-agent.service", "agent.example.toml", "README.md"}
    for left_out in ("mcp_bridge.py", "package.py", "workspace", "ssh-forced-command.sh", "RUNNER_API.md",
                     "agent.claude-ssh.example.toml", "agent.codex-ssh.example.toml"):
        assert left_out not in package.PACKAGE_FILES
    for name in package.PACKAGE_FILES:
        assert (A.RUNNER_DIR / name).is_file(), name


def test_everything_the_installer_copies_is_in_the_package_and_nothing_it_needs_is_missing():
    script = (A.RUNNER_DIR / "install.sh").read_text()
    listed = re.search(r"^APP_FILES=\(([^)]*)\)", script, re.M).group(1).split()
    assert set(listed) <= set(package.PACKAGE_FILES)
    needed = set(listed) | {"install.sh", "pdf-analysis-agent.service", "agent.example.toml", "VERSION"}
    assert needed <= set(package.PACKAGE_FILES) | {"VERSION"}
    assert {"detect.py", "runner_client.py", "host_mode.py", "api_answer.py"} <= set(listed), \
        "the modules agent.py imports travel with it (host mode imports the answerers too)"


@pytest.mark.parametrize("bad", ["", "1", "1.2", "1.2.3.4", "v1.2.3", "1.2.3-rc1", "00001.2.3", "1.2.x", " 1.2.3", "1.2.3\n", "../1.2.3"])
def test_a_version_that_is_not_three_numbers_is_refused_and_nothing_is_written(tmp_path, bad):
    out = tmp_path / "out"
    result = subprocess.run([sys.executable, str(A.RUNNER_DIR / "package.py"), "--version", bad, "--out", str(out)],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 2 and result.stdout == "", result
    assert not out.exists() or list(out.iterdir()) == []


def test_a_missing_source_file_fails_without_leaving_a_partial_package(tmp_path):
    source = tmp_path / "source"
    shutil.copytree(A.RUNNER_DIR, source, ignore=shutil.ignore_patterns("__pycache__"))
    (source / "detect.py").unlink()
    result, archive = _build(tmp_path / "out", source=source)
    assert result.returncode == 2 and "detect.py" in result.stderr and result.stdout == ""
    assert not archive.exists() and not (tmp_path / "out").exists()


def test_a_symlinked_source_file_is_refused(tmp_path):
    source = tmp_path / "source"
    shutil.copytree(A.RUNNER_DIR, source, ignore=shutil.ignore_patterns("__pycache__"))
    (source / "agent.py").unlink()
    (source / "agent.py").symlink_to(A.RUNNER_DIR / "agent.py")
    result, _ = _build(tmp_path / "out", source=source)
    assert result.returncode == 2 and "agent.py" in result.stderr


def test_the_build_function_alone_is_deterministic_without_the_script():
    data = package.build(A.RUNNER_DIR, VERSION)
    assert data == package.build(A.RUNNER_DIR, VERSION)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as handle:
        assert handle.getnames() == sorted(set(package.PACKAGE_FILES) | {"VERSION"})


def test_the_stand_can_read_what_package_py_writes(tmp_path):
    """The location contract with EXEC2-ENROLL-01: ``<dir>/auditmanager-agent-V.tar.gz`` with ``install.sh`` at
    its root, and ``<dir>/auditmanager-agent-V.tar.gz.sha256`` holding ``<64 hex>  <name>``."""
    result, archive = _build(tmp_path / "agent-package")
    assert result.returncode == 0, result.stderr
    line = (archive.parent / (archive.name + ".sha256")).read_text()
    assert re.fullmatch(r"[0-9a-f]{64}  auditmanager-agent-[0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,4}\.tar\.gz\n", line)
    assert line.split()[0] == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert "install.sh" in [member.name for member in _members(archive)]
    assert archive.stat().st_size < 1 << 20  # a few source files, far under the stand's 32 MiB bound


def test_the_api_image_builds_the_package_where_the_stand_reads_it():
    dockerfile = (A.REPO / "infra" / "deploy" / "Dockerfile.api").read_text()
    _, build_stage, final_stage = re.split(r"^FROM ", dockerfile, flags=re.M)
    assert re.search(r"^COPY VERSION \S+$", build_stage, re.M)
    assert re.search(r"^COPY tools/executor-runner/ \S+$", build_stage, re.M)
    # A continued line is one instruction: join the continuations first, then read the instruction to its end. (A
    # pattern that reads `[^\n]*` and then a continuation cannot work: the first group has already taken the backslash.)
    instructions = build_stage.replace("\\\n", " ")
    run = re.search(r"^RUN python \S*package\.py\b[^\n]*", instructions, re.M)
    assert run is not None
    command = run.group(0)
    assert '--version "$(cat ' in command and "--out /app/agent-package" in command
    assert "COPY --from=build /app/agent-package/ /app/agent-package/" in final_stage
    from_lines = re.findall(r"^FROM (\S+)", dockerfile, re.M)
    assert len(from_lines) == 2 and all("@sha256:" in line for line in from_lines), "no new, unpinned base image"
    # the image reads the same directory ENROLL-01's default names
    assert "/app/agent-package" in dockerfile and "uv sync" in build_stage.split("package.py")[0]


def test_the_repository_version_is_a_package_version():
    version = (A.REPO / "VERSION").read_text().strip()
    assert package.VERSION_PATTERN.fullmatch(version), version
