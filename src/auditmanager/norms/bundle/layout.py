"""The bundle on disk: its name, its ``SHA256SUMS`` and the tree rule both ends apply.

`W54-TRANSPORT-01` froze the shape (its report §3 items 1-2, ``lib/forced-command.sh``):

* the directory is named ``<content_key>+<bundle digest>``;
* the bundle digest is 64 lowercase hex, the SHA-256 of the bundle's ``SHA256SUMS``;
* ``SHA256SUMS`` is GNU ``sha256sum`` text (``<hex>␠␠<path>``), lists every other regular
  file exactly once, never itself, with ASCII paths of at most eight components
  ``[A-Za-z0-9_+=-][A-Za-z0-9._+=-]*``;
* the tree holds nothing else but directories.

The regular expressions below are the shell's EREs written for Python;
``tests/integration/norms/bundle/test_layout.py`` runs both over the same strings, so the two
cannot drift apart unnoticed.

**Discarded objects.** After an import that ``report`` matched, the inbound key's ``report``
verb removes ``objects/`` from the staged bundle and keeps the rest (plan §3.5 step 5;
`W54-BUNDLE-01` report §4). :func:`verify_bundle` with ``allow_discarded_objects`` then
accepts a tree whose ``objects/`` directory is absent **as a whole**; a tree missing some
objects but not all is refused, because that is damage, not a discard.
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .errors import BundleRefused

SUMS_NAME: Final[str] = "SHA256SUMS"
MANIFEST_NAME: Final[str] = "manifest.json"
OBJECTS_DIR: Final[str] = "objects"
ROWS_DIR: Final[str] = "rows"
BUILD_DIR: Final[str] = "build"

_COMPONENT = r"[A-Za-z0-9_+=-][A-Za-z0-9._+=-]{0,127}"
PATH_PATTERN: Final[re.Pattern[str]] = re.compile(rf"{_COMPONENT}(?:/{_COMPONENT}){{0,7}}")

_WINDOW = r"(?:undated|[0-9]{4}-[0-9]{2}-[0-9]{2}\.\.[0-9]{4}-[0-9]{2}-[0-9]{2})"
_REPAIRS = r"(?:\+[1-9][0-9]{0,5}r(?:\+[1-9][0-9]{0,5}u)?|\+0r\+[1-9][0-9]{0,5}u)?"
_CONTENT_KEY = (
    rf"{_WINDOW}\+(?:0|[1-9][0-9]{{0,5}})d{_REPAIRS}\.[0-9a-f]{{12}}"
    r"(?:\+seg-[a-z0-9]+(?:-[a-z0-9]+)*)?"
)
CONTENT_KEY_PATTERN: Final[re.Pattern[str]] = re.compile(_CONTENT_KEY)
BUNDLE_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(rf"({_CONTENT_KEY})\+([0-9a-f]{{64}})")
_SUMS_LINE = re.compile(r"([0-9a-f]{64})  (.+)")
_HEX64 = re.compile(r"[0-9a-f]{64}")

_CHUNK = 1 << 20


def sha256_file(path: Path) -> tuple[str, int]:
    """``(sha256, size)`` of one file, read in 1 MiB pieces."""
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while piece := handle.read(_CHUNK):
            digest.update(piece)
            size += len(piece)
    return digest.hexdigest(), size


def require_content_key(content_key: str) -> str:
    if not CONTENT_KEY_PATTERN.fullmatch(content_key):
        raise BundleRefused(
            "content_key_grammar",
            f"{content_key!r} is not a content key the inbound key's grammar admits",
        )
    return content_key


def require_bundle_path(path: str) -> str:
    if not PATH_PATTERN.fullmatch(path) or path == SUMS_NAME:
        raise BundleRefused("bundle_path_grammar", f"{path!r} is not a bundle path")
    return path


def bundle_name(content_key: str, sums: bytes) -> str:
    """``<content_key>+<sha256(SHA256SUMS)>``."""
    require_content_key(content_key)
    return f"{content_key}+{hashlib.sha256(sums).hexdigest()}"


def split_bundle_name(name: str) -> tuple[str, str]:
    match = BUNDLE_NAME_PATTERN.fullmatch(name)
    if match is None:
        raise BundleRefused(
            "bundle_name_grammar", f"{name!r} is not <content_key>+<64 hex bundle digest>"
        )
    return match.group(1), match.group(2)


def render_sums(entries: Mapping[str, str]) -> bytes:
    """GNU ``sha256sum`` text, one line per path, in byte order of the path."""
    lines = []
    for path in sorted(entries, key=lambda value: value.encode("ascii")):
        require_bundle_path(path)
        sha = entries[path]
        if not _HEX64.fullmatch(sha):
            raise BundleRefused("sums_malformed", f"{path}: {sha!r} is not a SHA-256")
        lines.append(f"{sha}  {path}\n")
    if not lines:
        raise BundleRefused("sums_malformed", "a bundle lists at least one file")
    return "".join(lines).encode("ascii")


def parse_sums(data: bytes) -> dict[str, str]:
    """``path -> sha256`` from a ``SHA256SUMS``, refusing anything the shell would refuse."""
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError:
        raise BundleRefused("sums_malformed", "SHA256SUMS is not ASCII") from None
    if not text or not text.endswith("\n"):
        raise BundleRefused("sums_malformed", "SHA256SUMS is empty or does not end in a newline")
    entries: dict[str, str] = {}
    for line in text[:-1].split("\n"):
        match = _SUMS_LINE.fullmatch(line)
        if match is None or not PATH_PATTERN.fullmatch(match.group(2)):
            raise BundleRefused("sums_malformed", f"SHA256SUMS line {line[:80]!r} is malformed")
        path = match.group(2)
        if path == SUMS_NAME:
            raise BundleRefused("sums_malformed", "SHA256SUMS names itself")
        if path in entries:
            raise BundleRefused("sums_malformed", f"SHA256SUMS names {path} twice")
        entries[path] = match.group(1)
    return entries


@dataclass(frozen=True, slots=True)
class VerifiedBundle:
    """A bundle directory whose name, sums and (named) files were checked."""

    directory: Path
    content_key: str
    digest: str
    sums: Mapping[str, str]
    #: Byte size of every verified file present.
    sizes: Mapping[str, int]
    #: ``objects/`` was absent as a whole (the boundary discarded it after a matched report).
    objects_discarded: bool

    def path(self, relative: str) -> Path:
        return self.directory / relative

    @property
    def object_paths(self) -> tuple[str, ...]:
        return tuple(path for path in self.sums if path.startswith(f"{OBJECTS_DIR}/"))


def _tree(directory: Path) -> tuple[set[str], list[str]]:
    """Every regular file under ``directory`` (relative, POSIX) and every stray entry."""
    files: set[str] = set()
    strays: list[str] = []
    for current, directories, names in os.walk(directory, followlinks=False):
        base = Path(current)
        for name in list(directories):
            if (base / name).is_symlink():
                strays.append((base / name).relative_to(directory).as_posix())
                directories.remove(name)
        for name in names:
            entry = base / name
            relative = entry.relative_to(directory).as_posix()
            mode = entry.lstat().st_mode
            if stat.S_ISREG(mode):
                files.add(relative)
            else:
                strays.append(relative)
    return files, strays


def read_sums(directory: Path) -> tuple[str, str, dict[str, str]]:
    """``(content_key, digest, sums)`` after the name and the sums file are checked."""
    if not directory.is_dir() or directory.is_symlink():
        raise BundleRefused("bundle_absent", f"{directory} is not a bundle directory")
    content_key, digest = split_bundle_name(directory.name)
    sums_path = directory / SUMS_NAME
    if sums_path.is_symlink() or not sums_path.is_file():
        raise BundleRefused("sums_absent", "the bundle has no SHA256SUMS regular file")
    data = sums_path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != digest:
        raise BundleRefused(
            "sums_digest", f"SHA256SUMS hashes to {actual}; the bundle name says {digest}"
        )
    return content_key, digest, parse_sums(data)


def verify_bundle(
    directory: Path,
    *,
    only: Iterable[str] | None = None,
    allow_discarded_objects: bool = False,
) -> VerifiedBundle:
    """Check the bundle's name, its sums and its files, and return what was verified.

    ``only`` restricts re-hashing to those listed paths (``report`` re-hashes the manifest
    alone); the tree rule (exactly the listed files, nothing but regular files and
    directories) is checked either way.
    """
    content_key, digest, sums = read_sums(directory)
    present, strays = _tree(directory)
    present.discard(SUMS_NAME)
    if strays:
        raise BundleRefused("bundle_tree", f"not a regular file or directory: {min(strays)}")
    listed = set(sums)
    discarded = False
    if present != listed:
        objects = {path for path in listed if path.startswith(f"{OBJECTS_DIR}/")}
        if (
            allow_discarded_objects
            and objects
            and present == listed - objects
            and not (directory / OBJECTS_DIR).exists()
        ):
            discarded = True
        else:
            missing = sorted(listed - present)
            extra = sorted(present - listed)
            raise BundleRefused(
                "bundle_tree",
                "the files are not exactly the ones SHA256SUMS lists "
                f"(missing {missing[:3]!r}, unlisted {extra[:3]!r})",
            )
    wanted = sorted(present if only is None else set(only))
    sizes: dict[str, int] = {}
    for relative in wanted:
        if relative not in present:
            raise BundleRefused("bundle_tree", f"{relative} is not in the bundle")
        sha, size = sha256_file(directory / relative)
        if sha != sums[relative]:
            raise BundleRefused("bundle_bytes", f"{relative} hashes to {sha}, SHA256SUMS says {sums[relative]}")
        sizes[relative] = size
    return VerifiedBundle(
        directory=directory,
        content_key=content_key,
        digest=digest,
        sums=sums,
        sizes=sizes,
        objects_discarded=discarded,
    )


def object_path(sha256: str) -> str:
    """Where an object's bytes live in a bundle: content-addressed, ASCII."""
    if not _HEX64.fullmatch(sha256):
        raise BundleRefused("object_digest", f"{sha256!r} is not a SHA-256")
    return f"{OBJECTS_DIR}/{sha256[:2]}/{sha256}.pdf"


__all__ = [
    "BUILD_DIR",
    "BUNDLE_NAME_PATTERN",
    "CONTENT_KEY_PATTERN",
    "MANIFEST_NAME",
    "OBJECTS_DIR",
    "PATH_PATTERN",
    "ROWS_DIR",
    "SUMS_NAME",
    "VerifiedBundle",
    "bundle_name",
    "object_path",
    "parse_sums",
    "read_sums",
    "render_sums",
    "require_bundle_path",
    "require_content_key",
    "sha256_file",
    "split_bundle_name",
    "verify_bundle",
]
