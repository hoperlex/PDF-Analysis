"""Content-derived API build identity over the W52 runtime file set."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Final

import auditmanager

_DIRECTORIES: Final[tuple[str, ...]] = (
    "src",
    "db",
    "contracts",
    "fixtures/recorded",
    "release-notes",
)
_FILES: Final[tuple[str, ...]] = (
    "VERSION",
    "uv.lock",
    "docs/program/P02_LOCK.json",
)


def _regular_files(root: Path) -> list[Path]:
    selected: list[Path] = []
    for name in _DIRECTORIES:
        directory = root / name
        if not directory.is_dir() or directory.is_symlink():
            raise FileNotFoundError(f"build identity root is absent: {name}")
        selected.extend(
            path
            for path in directory.rglob("*")
            if path.is_file()
            and not path.is_symlink()
            and path.suffix != ".pyc"
            and "__pycache__" not in path.relative_to(root).parts
        )
    for name in _FILES:
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(f"build identity file is absent: {name}")
        selected.append(path)
    return sorted(selected, key=lambda path: path.relative_to(root).as_posix())


def compute_build_id() -> str:
    """Hash the runtime inputs, using the installed package to locate their root.

    A missing input is a hard error. The later composition root owns converting
    that into its startup `ConfigurationError` and calling this only once.
    """
    root = Path(auditmanager.__file__).resolve().parents[2]
    manifest = hashlib.sha256()
    for path in _regular_files(root):
        name = path.relative_to(root).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest.update(f"{name}\t{digest}\n".encode("utf-8"))
    return "b" + manifest.hexdigest()[:16]
