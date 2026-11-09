"""The agent package as the image holds it, and the command that installs it (`EXEC2-ENROLL-01`).

ADR-0026 decision 6: the package is built deterministically from ``tools/executor-runner/`` by
`EXEC2-AGENT-01` into the API image, and served **by exact version without authentication**. It is public
code with no secret; its integrity is the sha256 that ``issueExecutorEnrollment`` writes into the install
command, so the stand must never hand out bytes whose digest differs from the one it told the host.

The location contract with `EXEC2-AGENT-01`
-------------------------------------------
For each version ``V`` the image holds -- the repository ``VERSION`` (``major.minor.patch``, one to four
digits each, the contract's ``AgentPackageVersion``) -- in one directory (integrator decision, 2026-11-02):

``<dir>/auditmanager-agent-V.tar.gz``
    a gzip-compressed tar archive whose **root holds** ``install.sh``;
``<dir>/auditmanager-agent-V.tar.gz.sha256``
    one line in ``sha256sum`` format: the 64 lower-case hexadecimal digits of the archive's sha256, two
    spaces and the file name (the stand reads the first token).

``<dir>`` is :data:`DEFAULT_PACKAGE_DIRECTORY` (``/app/agent-package``, beside ``/app/contracts``) unless the
environment variable :data:`PACKAGE_DIRECTORY_ENV` names another. The directory is read-only to the API, and
the highest version present is the one a new enrollment installs.

The install command (path B) reads two environment variables, :data:`ENROLLMENT_SECRET_ENV` and
:data:`STAND_ORIGIN_ENV`, and is run as ``bash install.sh`` from the extracted archive's root.

What is refused, and how
------------------------
* a version that is not three dot-separated numbers, or that no file of the directory answers to:
  ``422 validation_failed``, field ``version``, constraint ``package_version_unknown``. The answer is the same
  for ``../etc/passwd``, ``latest`` and ``9.9.9``; it never lists the versions that exist, and the file name is
  built from the validated digits, never from the caller's text, so no path component can come from outside;
* an image with no package at all, an archive without a readable checksum, an archive over
  :data:`MAX_PACKAGE_BYTES`, a symbolic link, or bytes whose digest is not the declared one:
  ``503 dependency_unavailable``, dependency ``agent_package``. Fail closed: an older package is never served
  in place of a broken newer one;
* an absent or malformed ``AUDITMANAGER_PUBLIC_ORIGIN``: ``503 dependency_unavailable``, dependency
  ``public_origin``. The command's origin comes from that setting alone and is never guessed from the request.

Nothing here reads a secret. The command it builds carries the enrollment secret **only** as the value of an
environment variable assigned in front of ``sudo`` (the shell sets it in the child's environment, so it is
in no argument vector, and ``--preserve-env`` names the variables, not their values).
"""

from __future__ import annotations

import hashlib
import os
import re
import shlex
import stat
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from auditmanager.executors.model import (
    CONSTRAINT_PACKAGE_VERSION_UNKNOWN,
    DEPENDENCY_AGENT_PACKAGE,
)
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "CHECKSUM_SUFFIX",
    "DEFAULT_PACKAGE_DIRECTORY",
    "DOWNLOAD_PATH",
    "ENROLLMENT_SECRET_ENV",
    "MAX_PACKAGE_BYTES",
    "PACKAGE_DIRECTORY_ENV",
    "PACKAGE_NAME",
    "STAND_ORIGIN_ENV",
    "AgentPackage",
    "available_versions",
    "install_command",
    "latest_package",
    "load_package",
    "normalise_origin",
    "package_directory",
    "resolve_origin",
]

#: The environment variable that moves the directory (a test and a stand with another layout set it).
PACKAGE_DIRECTORY_ENV: Final[str] = "AUDITMANAGER_AGENT_PACKAGE_DIR"
#: Where the image holds the packages: beside ``/app/contracts``. `EXEC2-AGENT-01` writes here.
DEFAULT_PACKAGE_DIRECTORY: Final[str] = "/app/agent-package"
#: The archive's name for a version, and the suffix of the file that declares its digest.
PACKAGE_NAME: Final[str] = "auditmanager-agent-{version}.tar.gz"
CHECKSUM_SUFFIX: Final[str] = ".sha256"
#: The most bytes of an archive the stand reads into memory to serve it. The package is a few source files.
MAX_PACKAGE_BYTES: Final[int] = 32 * 1024 * 1024
#: The two variables ``install.sh`` reads. The first is the enrollment secret and exists nowhere else.
ENROLLMENT_SECRET_ENV: Final[str] = "AUDITMANAGER_ENROLLMENT_SECRET"
STAND_ORIGIN_ENV: Final[str] = "AUDITMANAGER_STAND_ORIGIN"
#: The model the agent declares (`EXEC2-INT-1`): the ``gateway_model`` of the connection's current revision,
#: which the stand holds every pull answer equal to. ``install.sh`` never picks a model of its own.
AGENT_MODEL_ENV: Final[str] = "AUDITMANAGER_AGENT_MODEL"
#: The served path of the package route, relative to the origin (the proxy mounts the API at ``/api/v1``).
DOWNLOAD_PATH: Final[str] = "/api/v1/runner/agent-package/{version}"

_VERSION: Final[re.Pattern[str]] = re.compile(r"[0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,4}")
_ARCHIVE: Final[re.Pattern[str]] = re.compile(
    r"auditmanager-agent-([0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,4})\.tar\.gz")
_DIGEST: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}")
_HOST: Final[re.Pattern[str]] = re.compile(
    r"[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?|\[[0-9a-f:.]{2,45}\]")
_CHECKSUM_FILE_LIMIT: Final[int] = 512


@dataclass(frozen=True, slots=True)
class AgentPackage:
    """One package of the image, as verified: its version, the sha256 of its bytes and their size."""

    version: str
    sha256: str
    size_bytes: int
    #: Where the archive is. Internal: it appears in no answer.
    path: Path = field(repr=False)

    @property
    def file_name(self) -> str:
        return PACKAGE_NAME.format(version=self.version)


def package_directory(environ: Mapping[str, str] | None = None) -> Path:
    """The directory the image keeps its packages in: the environment override, else the default."""
    source = os.environ if environ is None else environ
    return Path(source.get(PACKAGE_DIRECTORY_ENV) or DEFAULT_PACKAGE_DIRECTORY)


def _unavailable() -> DomainError:
    return DomainError(
        ErrorCode.DEPENDENCY_UNAVAILABLE, message="the image holds no agent package to install",
        dependency=DEPENDENCY_AGENT_PACKAGE,
    )


def _unknown_version() -> DomainError:
    return DomainError(
        ErrorCode.VALIDATION_FAILED, message="the image holds no agent package of this version",
        field="version", constraint=CONSTRAINT_PACKAGE_VERSION_UNKNOWN,
    )


def _numeric(version: str) -> tuple[int, int, int]:
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)


def _regular_file(path: Path) -> bool:
    """A regular file that is not a link: a link in a read-only image is a misbuilt image."""
    try:
        return path.is_file() and not path.is_symlink()
    except OSError:
        return False


def available_versions(directory: Path | None = None) -> tuple[str, ...]:
    """The versions the directory holds an archive entry for, oldest first.

    Internal: no route lists them. An entry counts whatever it is -- a link or a half-published archive with
    no checksum file is *held*, and :func:`load_package` refuses it as untrustworthy rather than the version
    quietly disappearing in favour of an older one. An unreadable or missing directory holds none."""
    root = package_directory() if directory is None else directory
    try:
        names = [entry.name for entry in os.scandir(root)]
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        return ()
    found = {match.group(1) for name in names if (match := _ARCHIVE.fullmatch(name)) is not None}
    return tuple(sorted(found, key=_numeric))


def _declared_digest(path: Path) -> str | None:
    """The digest a checksum file declares, or ``None`` when it declares none the stand can read."""
    try:
        with path.open("rb") as handle:
            head = handle.read(_CHECKSUM_FILE_LIMIT)
    except OSError:
        return None
    tokens = head.decode("ascii", errors="replace").split()
    if not tokens or _DIGEST.fullmatch(tokens[0]) is None:
        return None
    return tokens[0]


def _read_bounded(path: Path) -> bytes:
    """The archive's bytes, at most :data:`MAX_PACKAGE_BYTES` of them, read from one opened file.

    The file is opened without following a link (``O_NOFOLLOW``: a link swapped in after the check of
    :func:`_regular_file` is refused, not read; ``O_NONBLOCK``: a FIFO swapped in does not hang the open) and
    must be a regular file. At most ``MAX_PACKAGE_BYTES + 1`` bytes are asked of it, so a file that grew past
    the bound after a ``stat`` is never read whole into memory. A byte over the bound fails closed
    (``503 agent_package``), as does any error of the open or the read."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    except OSError:
        raise _unavailable() from None
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise _unavailable()
        handle = os.fdopen(descriptor, "rb")
    except DomainError:
        os.close(descriptor)
        raise
    except OSError:
        os.close(descriptor)
        raise _unavailable() from None
    try:
        with handle:
            content = handle.read(MAX_PACKAGE_BYTES + 1)
    except OSError:
        raise _unavailable() from None
    if len(content) > MAX_PACKAGE_BYTES:
        raise _unavailable()
    return content


def load_package(
    version: str, *, directory: Path | None = None
) -> tuple[AgentPackage, bytes]:
    """The package of exactly ``version`` with its bytes, verified against its declared digest.

    ``422 package_version_unknown`` for a version that is not a version or that the image does not hold;
    ``503 agent_package`` for an image with no package at all, and for a package that cannot be trusted."""
    if _VERSION.fullmatch(version) is None:
        raise _unknown_version()
    root = package_directory() if directory is None else directory
    archive = root / PACKAGE_NAME.format(version=version)
    held = available_versions(root)
    if version not in held:
        # An image with no package at all is a dependency that is down; a version that is not there while
        # others are is the caller's mistake. Neither answer lists what exists.
        raise _unknown_version() if held else _unavailable()
    if not _regular_file(archive):
        raise _unavailable()
    declared = _declared_digest(root / (archive.name + CHECKSUM_SUFFIX))
    if declared is None:
        raise _unavailable()
    content = _read_bounded(archive)
    actual = hashlib.sha256(content).hexdigest()
    if actual != declared:
        raise _unavailable()
    return AgentPackage(version=version, sha256=actual, size_bytes=len(content), path=archive), content


def latest_package(*, directory: Path | None = None) -> AgentPackage:
    """The highest version the image holds, verified. ``503 agent_package`` when there is none or when the
    highest cannot be trusted: an older package is not served in its place."""
    root = package_directory() if directory is None else directory
    versions = available_versions(root)
    if not versions:
        raise _unavailable()
    package, _ = load_package(versions[-1], directory=root)
    return package


# -- the origin the command points at ---------------------------------------------------------


def normalise_origin(candidate: str) -> str:
    """``scheme://host[:port]`` in lower case, or ``ValueError``.

    Only ``http`` and ``https``, a plain host name, an IPv4 address or a bracketed IPv6 address, an optional
    port; no user information, path, query or fragment. The origin ends up inside a shell command, so
    anything else is refused rather than quoted."""
    text = candidate.strip()
    scheme, separator, rest = text.partition("://")
    scheme = scheme.lower()
    if not separator or scheme not in ("http", "https") or not rest or any(c in rest for c in "/?#@ \t\r\n\\"):
        raise ValueError("not an origin")
    host, port, has_port = rest, "", False
    if rest.startswith("["):
        closing = rest.find("]")
        if closing == -1:
            raise ValueError("not an origin")
        host, tail = rest[: closing + 1], rest[closing + 1:]
        if tail:
            if not tail.startswith(":"):
                raise ValueError("not an origin")
            port, has_port = tail[1:], True
    elif ":" in rest:
        host, _, port = rest.partition(":")
        has_port = True
    host = host.lower()
    if _HOST.fullmatch(host) is None:
        raise ValueError("not an origin")
    if has_port:
        if not port.isdigit() or not port.isascii() or not 1 <= int(port) <= 65535:
            raise ValueError("not an origin")
        return f"{scheme}://{host}:{int(port)}"
    return f"{scheme}://{host}"


def resolve_origin(configured: str | None) -> str:
    """The origin the install command downloads from: the stand's configured public origin, validated.

    The configured value (``AUDITMANAGER_PUBLIC_ORIGIN``) is the **only** source. The request's own ``Host``
    is never consulted: behind the web tier the forwarded ``Host`` and ``X-Forwarded-*`` are dropped, so a
    request-derived origin would silently be the API's internal name (``http://api:8000``), a command that
    names no host the agent can reach. The value is checked by :func:`normalise_origin` because it ends up
    inside a shell command. ``503 dependency_unavailable`` (dependency ``public_origin``) when it is absent or
    malformed: a command that names no reachable stand is no command, and nothing is written."""
    if configured:
        try:
            return normalise_origin(configured)
        except ValueError:
            pass
    raise DomainError(
        ErrorCode.DEPENDENCY_UNAVAILABLE, message="the stand's public origin is not configured",
        dependency="public_origin",
    )


# -- the command ------------------------------------------------------------------------------


def install_command(*, origin: str, package: AgentPackage, secret: str, model: str | None = None) -> str:
    """The copyable command of path B: download the package, verify its sha256, unpack it, run ``install.sh``.

    The secret is the value of :data:`ENROLLMENT_SECRET_ENV`, assigned in front of ``sudo`` -- an assignment
    of the shell, which puts it in the child's environment and in no argument vector -- and carried through
    ``sudo`` by ``--preserve-env`` (which names variables and takes no value). The command runs in a fresh
    temporary directory. ``--proto =https`` is added when the origin is ``https``: a downgrade is a refusal.
    ``model`` is the connection's pinned ``gateway_model`` (:data:`AGENT_MODEL_ENV`): the installer configures
    the agent to declare exactly it and derives the CLI from it, never a default of its own. **No model** (`HOSTS-BACKEND-01`,
    ADR-0028 decision 1) is the command of a host agent: the installer then asks for none and installs host mode, which serves every
    model its machine can reach."""
    url = origin + DOWNLOAD_PATH.format(version=package.version)
    flags = "-fsSL --proto '=https' --tlsv1.2" if origin.startswith("https://") else "-fsSL"
    archive = "agent.tar.gz"
    carried = f"{ENROLLMENT_SECRET_ENV},{STAND_ORIGIN_ENV}" + ("" if model is None else f",{AGENT_MODEL_ENV}")
    assigned = (f"{ENROLLMENT_SECRET_ENV}={shlex.quote(secret)} {STAND_ORIGIN_ENV}={shlex.quote(origin)} "
                + ("" if model is None else f"{AGENT_MODEL_ENV}={shlex.quote(model)} "))
    return " && ".join((
        'cd "$(mktemp -d)"',
        f"curl {flags} -o {archive} {shlex.quote(url)}",
        f"echo {shlex.quote(f'{package.sha256}  {archive}')} | sha256sum -c -",
        f"tar -xzf {archive}",
        f"{assigned}sudo --preserve-env={carried} bash install.sh",
    ))
