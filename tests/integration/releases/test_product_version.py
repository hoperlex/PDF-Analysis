"""The product version is one strict line beside the installed package."""

from __future__ import annotations

from pathlib import Path

import auditmanager
import pytest

from auditmanager.releases.public import read_product_version


def _version_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    package = tmp_path / "src/auditmanager/__init__.py"
    package.parent.mkdir(parents=True)
    package.write_bytes(b"")
    monkeypatch.setattr(auditmanager, "__file__", str(package))
    return tmp_path / "VERSION"


@pytest.mark.parametrize("contents", [b"0.3.0", b"0.3.0\n", b"1.0.0-rc.1\n"])
def test_one_canonical_line_is_returned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, contents: bytes
) -> None:
    path = _version_path(tmp_path, monkeypatch)
    path.write_bytes(contents)
    monkeypatch.chdir(path.parent / "src")
    assert read_product_version() == contents.decode("ascii").removesuffix("\n")


@pytest.mark.parametrize(
    "contents",
    [b"", b"0.3.0\n\n", b" 0.3.0", b"0.3.0 ", b"0.3.0\r\n",
     b"0.3.0+build", b"01.0.0", "0.3.0-α".encode("utf-8")],
)
def test_invalid_file_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, contents: bytes
) -> None:
    _version_path(tmp_path, monkeypatch).write_bytes(contents)
    with pytest.raises(ValueError):
        read_product_version()


def test_missing_file_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _version_path(tmp_path, monkeypatch)
    with pytest.raises(FileNotFoundError):
        read_product_version()
