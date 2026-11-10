#!/usr/bin/env python3
"""Build the agent package: a deterministic tarball of the universal agent and its sha256.

    python3 package.py --version 0.9.0 --out /app/agent-package

writes, into ``--out``,

    auditmanager-agent-<version>.tar.gz          the package
    auditmanager-agent-<version>.tar.gz.sha256   ``<hex digest>  <file name>`` (``sha256sum`` format)

and prints the digest. The API image runs this in its build stage (``infra/deploy/Dockerfile.api``) and the
stand serves the result by exact version (``EXEC2-ENROLL-01``, ADR-0026 decision 6); the digest is what the
copyable install command checks before anything is unpacked.

The same inputs give the same bytes, on any host and in any directory: the file list is fixed in
:data:`PACKAGE_FILES` (never a glob, so a stray file cannot ride along), entries are sorted by name, every
header has mtime 0, uid and gid 0, empty owner names and a fixed mode, file contents are read as bytes (a
file's own mtime and mode are never used), and the gzip header carries no time and no file name. The
archive's root holds ``install.sh``, ``VERSION`` (the ``--version`` value) and the agent files, no
directory entries; tests, ``workspace/`` and the Claude Code bridge are not in it.

Standard library only.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import os
import re
import sys
import tarfile
from pathlib import Path
from typing import Optional, Sequence

#: The contract's ``AgentPackageVersion``.
VERSION_PATTERN = re.compile(r"^[0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,4}$")
ARCHIVE_NAME = "auditmanager-agent-{version}.tar.gz"
CHECKSUM_SUFFIX = ".sha256"

#: name in the archive -> mode bits. ``VERSION`` is not a source file: it is written from ``--version``.
PACKAGE_FILES = {
    "install.sh": 0o755,
    "agent.py": 0o644,
    "runner_client.py": 0o644,
    "detect.py": 0o644,
    "host_mode.py": 0o644,
    "api_answer.py": 0o644,
    "codex_answer.py": 0o644,
    "claude_answer.py": 0o644,
    "pdf-analysis-agent.service": 0o644,
    "agent.example.toml": 0o644,
    "README.md": 0o644,
}
VERSION_FILE = "VERSION"


class PackageError(Exception):
    pass


def entries(source: Path, version: str) -> list[tuple[str, int, bytes]]:
    """``(name, mode, content)`` of every archive member, sorted by name."""
    members: dict[str, tuple[int, bytes]] = {VERSION_FILE: (0o644, (version + "\n").encode("ascii"))}
    for name, mode in PACKAGE_FILES.items():
        path = source / name
        if path.is_symlink() or not path.is_file():
            raise PackageError(f"{name} is missing from {source}")
        members[name] = (mode, path.read_bytes())
    return [(name, *members[name]) for name in sorted(members)]


def build(source: Path, version: str) -> bytes:
    """The package bytes for ``version``."""
    if VERSION_PATTERN.fullmatch(version) is None:
        raise PackageError("--version must be three dot-separated numbers of at most four digits (for example 0.9.0)")
    raw = io.BytesIO()
    # ``filename=""`` and a nameless buffer: no FNAME field; ``mtime=0``: no time. The OS byte is fixed by Python.
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for name, mode, content in entries(source, version):
                header = tarfile.TarInfo(name)
                header.size = len(content)
                header.mode = mode
                header.mtime = 0
                header.uid = header.gid = 0
                header.uname = header.gname = ""
                header.type = tarfile.REGTYPE
                archive.addfile(header, io.BytesIO(content))
    return raw.getvalue()


def write(source: Path, version: str, out: Path) -> tuple[Path, str]:
    """Build and write the archive and its checksum file; return the archive's path and sha256."""
    data = build(source, version)
    digest = hashlib.sha256(data).hexdigest()
    name = ARCHIVE_NAME.format(version=version)
    out.mkdir(parents=True, exist_ok=True)
    archive = out / name
    # The checksum file is written last: a reader that finds it finds a finished archive.
    for path, payload in ((archive, data), (out / (name + CHECKSUM_SUFFIX), f"{digest}  {name}\n".encode("ascii"))):
        temporary = path.with_name(path.name + ".part")
        temporary.write_bytes(payload)
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    return archive, digest


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="package.py", description="Build the deterministic agent package.")
    parser.add_argument("--version", required=True, help="the package version, x.y.z (the repository VERSION)")
    parser.add_argument("--out", required=True, help="the directory to write the archive and its .sha256 file into")
    parser.add_argument("--source", default=str(Path(__file__).resolve().parent),
                        help="the directory holding the agent files (default: this file's directory)")
    args = parser.parse_args(argv)
    try:
        _, digest = write(Path(args.source), args.version, Path(args.out))
    except (PackageError, OSError) as error:
        print(f"package.py: {error}", file=sys.stderr)
        return 2
    print(digest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
