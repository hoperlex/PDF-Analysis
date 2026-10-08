"""Build identity is a content digest, not a checkout path or a cache hash."""

from __future__ import annotations

import hashlib
import fnmatch
import subprocess
from pathlib import Path

import auditmanager
import pytest

from auditmanager.releases.public import compute_build_id


def _tree(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "src/auditmanager", "db", "contracts", "fixtures/recorded",
        "release-notes", "docs/program",
    ):
        (root / name).mkdir(parents=True)
    values = {
        "src/auditmanager/__init__.py": b"package\n",
        "db/migrations.py": b"revision\n",
        "contracts/schema.json": b"{}\n",
        "fixtures/recorded/sample.json": b"[]\n",
        "release-notes/0.3.0.json": b"release\n",
        "VERSION": b"0.3.0\n",
        "uv.lock": b"locked\n",
        "docs/program/P02_LOCK.json": b"{}\n",
    }
    for name, data in values.items():
        (root / name).write_bytes(data)
    monkeypatch.setattr(auditmanager, "__file__", str(root / "src/auditmanager/__init__.py"))


def _independent_digest(root: Path) -> str:
    names = [
        "VERSION", "contracts/schema.json", "db/migrations.py",
        "docs/program/P02_LOCK.json", "fixtures/recorded/sample.json",
        "release-notes/0.3.0.json", "src/auditmanager/__init__.py", "uv.lock",
    ]
    lines = "".join(
        f"{name}\t{hashlib.sha256((root / name).read_bytes()).hexdigest()}\n"
        for name in names
    )
    return "b" + hashlib.sha256(lines.encode("utf-8")).hexdigest()[:16]


def test_exact_manifest_and_checkout_location(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first = tmp_path / "first"
    _tree(first, monkeypatch)
    expected = _independent_digest(first)
    assert compute_build_id() == expected

    second = tmp_path / "other-location"
    _tree(second, monkeypatch)
    monkeypatch.chdir(tmp_path)
    assert compute_build_id() == expected == _independent_digest(second)


def test_included_byte_changes_the_build_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _tree(tmp_path, monkeypatch)
    before = compute_build_id()
    (tmp_path / "contracts/schema.json").write_bytes(b"{ }\n")
    assert compute_build_id() != before


def test_new_regular_file_changes_the_build_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _tree(tmp_path, monkeypatch)
    before = compute_build_id()
    (tmp_path / "src/auditmanager/new_module.py").write_bytes(b"added\n")
    assert compute_build_id() != before


def test_excluded_files_do_not_change_the_build_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _tree(tmp_path, monkeypatch)
    before = compute_build_id()
    cache = tmp_path / "src/auditmanager/__pycache__"
    cache.mkdir()
    (cache / "module.pyc").write_bytes(b"cache")
    (tmp_path / "src/auditmanager/other.pyc").write_bytes(b"cache")
    (tmp_path / "infra").mkdir()
    (tmp_path / "infra/deploy.py").write_bytes(b"not in the runtime roots")
    assert compute_build_id() == before


@pytest.mark.parametrize("missing", ["VERSION", "release-notes", "docs/program/P02_LOCK.json"])
def test_required_input_absence_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    _tree(tmp_path, monkeypatch)
    path = tmp_path / missing
    if missing == "release-notes":
        (path / "0.3.0.json").unlink()
        path.rmdir()
    else:
        path.unlink()
    with pytest.raises(FileNotFoundError):
        compute_build_id()


def test_no_tracked_build_input_is_hidden_by_dockerignore() -> None:
    """A clean checkout and /app must hash the same tracked byte set."""
    root = Path(__file__).resolve().parents[3]
    selected = subprocess.check_output(
        [
            "git", "ls-files", "-z", "--", "src", "db", "contracts",
            "fixtures/recorded", "release-notes", "VERSION", "uv.lock",
            "docs/program/P02_LOCK.json",
        ],
        cwd=root,
    ).decode("utf-8").strip("\0").split("\0")
    # Docker's current ignore patterns are simple path, basename or **/ rules.
    # Fail on a new syntax rather than silently proving an incomplete match.
    patterns = [
        line.strip()
        for line in (root / ".dockerignore").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert set(patterns) <= {
        ".git", ".local", ".venv", "**/node_modules", "web/.next",
        "**/__pycache__", "**/*.pyc", ".pytest_cache", ".mypy_cache",
        ".ruff_cache", "*.log", ".env", ".env.*", "!.env.example",
    }
    for name in selected:
        parts = name.split("/")
        for pattern in patterns:
            if pattern.startswith("!"):
                continue
            if pattern.startswith("**/"):
                assert not any(
                    fnmatch.fnmatchcase(part, pattern[3:]) for part in parts
                ), (name, pattern)
            elif "/" in pattern:
                assert not (name == pattern or name.startswith(pattern + "/")), (
                    name, pattern
                )
            else:
                assert not any(
                    fnmatch.fnmatchcase(part, pattern) for part in parts
                ), (name, pattern)
