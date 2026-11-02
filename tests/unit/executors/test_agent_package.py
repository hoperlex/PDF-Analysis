"""`EXEC2-ENROLL-01`: the agent package as the image holds it, and the command that installs it.

No database and no network: a temporary directory stands for the image's package directory
(``agent_package.PACKAGE_DIRECTORY_ENV``). What is shown: the highest version is chosen by number, the served
bytes always have the digest the command carries, a version the image does not hold -- malformed, traversing
or merely absent -- is the same ``package_version_unknown`` and never a listing, a broken image is a
``dependency_unavailable`` and never an older package, and the install command carries the enrollment secret
only as the value of an environment variable in front of ``sudo``, never in an argument vector.
"""

from __future__ import annotations

import hashlib
import os
import shlex
from pathlib import Path

import pytest

from auditmanager.executors import agent_package as package
from auditmanager.shared.errors import DomainError, ErrorCode

SECRET = "ame_ab12cd34_" + "x" * 43


def _publish(
    directory: Path, version: str, content: bytes = b"archive-bytes", *, declared: str | None = None,
    sidecar: bool = True,
) -> Path:
    archive = directory / package.PACKAGE_NAME.format(version=version)
    archive.write_bytes(content)
    if sidecar:
        digest = declared or hashlib.sha256(content).hexdigest()
        (directory / (archive.name + package.CHECKSUM_SUFFIX)).write_text(
            f"{digest}  {archive.name}\n", encoding="ascii")
    return archive


def _refusal(call, *args, **kwargs) -> DomainError:
    with pytest.raises(DomainError) as caught:
        call(*args, **kwargs)
    return caught.value


# -- where the image keeps it -----------------------------------------------------------------


def test_the_directory_is_the_images_unless_the_environment_names_another(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.delenv(package.PACKAGE_DIRECTORY_ENV, raising=False)
    assert package.package_directory() == Path("/app/agent-package")
    monkeypatch.setenv(package.PACKAGE_DIRECTORY_ENV, str(tmp_path))
    assert package.package_directory() == tmp_path
    assert package.package_directory({}) == Path("/app/agent-package")
    assert package.package_directory({package.PACKAGE_DIRECTORY_ENV: "/elsewhere"}) == Path("/elsewhere")


def test_the_file_names_are_the_contract_with_the_package_builder() -> None:
    assert package.PACKAGE_NAME.format(version="0.9.0") == "auditmanager-agent-0.9.0.tar.gz"
    assert package.CHECKSUM_SUFFIX == ".sha256"


# -- which version, and which bytes ------------------------------------------------------------


def test_the_latest_version_is_chosen_by_number_and_not_by_text(tmp_path: Path) -> None:
    for version in ("1.9.0", "1.10.0", "0.9.2"):
        _publish(tmp_path, version)
    assert package.available_versions(tmp_path) == ("0.9.2", "1.9.0", "1.10.0")
    assert package.latest_package(directory=tmp_path).version == "1.10.0"


def test_a_package_is_served_with_the_digest_of_its_bytes(tmp_path: Path) -> None:
    content = b"\x1f\x8b gzip bytes"
    _publish(tmp_path, "0.9.0", content)
    found, served = package.load_package("0.9.0", directory=tmp_path)
    assert served == content
    assert found.sha256 == hashlib.sha256(content).hexdigest()
    assert found.size_bytes == len(content) and found.file_name == "auditmanager-agent-0.9.0.tar.gz"
    assert str(tmp_path) not in repr(found), "the location of the image's files is in no repr"


def test_a_checksum_file_in_sha256sum_format_or_bare_is_read(tmp_path: Path) -> None:
    archive = _publish(tmp_path, "0.9.0", b"abc", sidecar=False)
    digest = hashlib.sha256(b"abc").hexdigest()
    sidecar = tmp_path / (archive.name + package.CHECKSUM_SUFFIX)
    for text in (f"{digest}  {archive.name}\n", f"{digest}\n", f"{digest} *{archive.name}"):
        sidecar.write_text(text, encoding="ascii")
        assert package.load_package("0.9.0", directory=tmp_path)[0].sha256 == digest


# -- what is refused ----------------------------------------------------------------------------


@pytest.mark.parametrize("version", [
    "9.9.9", "latest", "", "1.2", "1.2.3.4", "1.2.x", "../etc/passwd", "..", "0.9.0/../../x",
    "0.9.0%2f..", "0.9.0\n", " 0.9.0", "0.9.0 ", "١.٢.٣", "00000.1.1", "0.9.0.tar.gz",
])
def test_an_unknown_or_malformed_version_is_the_same_422_and_lists_nothing(
    tmp_path: Path, version: str,
) -> None:
    _publish(tmp_path, "0.9.0")
    error = _refusal(package.load_package, version, directory=tmp_path)
    assert error.code is ErrorCode.VALIDATION_FAILED
    assert dict(error.detail_fields) == {"field": "version", "constraint": "package_version_unknown"}
    assert "0.9.0" not in str(error) or version == "0.9.0"


def test_an_image_with_no_package_is_a_dependency_that_is_down(tmp_path: Path) -> None:
    for call in (lambda: package.load_package("0.9.0", directory=tmp_path),
                 lambda: package.latest_package(directory=tmp_path),
                 lambda: package.load_package("0.9.0", directory=tmp_path / "missing")):
        error = _refusal(call)
        assert error.code is ErrorCode.DEPENDENCY_UNAVAILABLE
        assert dict(error.detail_fields) == {"dependency": "agent_package"}


@pytest.mark.parametrize("damage", ["no checksum file", "unreadable checksum", "digest differs",
                                    "oversized", "a link"])
def test_a_package_that_cannot_be_trusted_is_never_served_and_never_replaced_by_an_older_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str,
) -> None:
    _publish(tmp_path, "0.9.0", b"the older, good one")
    newest = "0.10.0"
    if damage == "no checksum file":
        _publish(tmp_path, newest, b"new", sidecar=False)
    elif damage == "unreadable checksum":
        _publish(tmp_path, newest, b"new", declared="not-a-digest")
    elif damage == "digest differs":
        _publish(tmp_path, newest, b"new", declared="0" * 64)
    elif damage == "oversized":
        _publish(tmp_path, newest, b"x" * 64)
        monkeypatch.setattr(package, "MAX_PACKAGE_BYTES", 32)
    else:
        target = tmp_path / "elsewhere"
        target.write_bytes(b"new")
        (tmp_path / package.PACKAGE_NAME.format(version=newest)).symlink_to(target)
        (tmp_path / (package.PACKAGE_NAME.format(version=newest) + package.CHECKSUM_SUFFIX)).write_text(
            hashlib.sha256(b"new").hexdigest(), encoding="ascii")
    for call in (lambda: package.load_package(newest, directory=tmp_path),
                 lambda: package.latest_package(directory=tmp_path)):
        error = _refusal(call)
        assert error.code is ErrorCode.DEPENDENCY_UNAVAILABLE
        assert dict(error.detail_fields) == {"dependency": "agent_package"}
    # The older package is untouched and still addressable by its own version.
    assert package.load_package("0.9.0", directory=tmp_path)[1] == b"the older, good one"


def test_the_archive_is_read_through_a_bound_and_never_whole(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A file that grew after the size was looked at is never read into memory in full: at most
    ``MAX_PACKAGE_BYTES + 1`` bytes are asked of the opened file, and the byte over the bound is a refusal."""
    archive = _publish(tmp_path, "0.9.0", b"x" * 1024)
    monkeypatch.setattr(package, "MAX_PACKAGE_BYTES", 32)
    asked: list[int] = []
    real_fdopen = os.fdopen

    class Spy:
        def __init__(self, handle) -> None:
            self._handle = handle

        def __enter__(self) -> "Spy":
            return self

        def __exit__(self, *exc) -> None:
            self._handle.close()

        def fileno(self) -> int:
            return self._handle.fileno()

        def read(self, size: int = -1) -> bytes:
            asked.append(size)
            return self._handle.read(size)

    monkeypatch.setattr(package.os, "fdopen", lambda descriptor, mode: Spy(real_fdopen(descriptor, mode)))
    error = _refusal(package.load_package, "0.9.0", directory=tmp_path)
    assert error.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert dict(error.detail_fields) == {"dependency": "agent_package"}
    assert asked == [33], "one read, of the bound plus one byte -- never read_bytes()"
    # Exactly at the bound is served.
    asked.clear()
    archive.write_bytes(b"y" * 32)
    (tmp_path / (archive.name + package.CHECKSUM_SUFFIX)).write_text(
        hashlib.sha256(b"y" * 32).hexdigest(), encoding="ascii")
    assert package.load_package("0.9.0", directory=tmp_path)[1] == b"y" * 32
    assert asked == [33]


def test_a_link_or_a_non_file_swapped_in_after_the_check_is_refused_by_the_open(tmp_path: Path) -> None:
    target = tmp_path / "elsewhere"
    target.write_bytes(b"new")
    link = tmp_path / "link.tar.gz"
    link.symlink_to(target)
    for refused in (link, tmp_path, tmp_path / "missing"):
        error = _refusal(package._read_bounded, refused)
        assert error.code is ErrorCode.DEPENDENCY_UNAVAILABLE
        assert dict(error.detail_fields) == {"dependency": "agent_package"}
    assert package._read_bounded(target) == b"new"


def test_a_directory_entry_that_is_not_an_archive_name_is_not_a_version(tmp_path: Path) -> None:
    _publish(tmp_path, "0.9.0")
    (tmp_path / "auditmanager-agent-latest.tar.gz").write_bytes(b"x")
    (tmp_path / "auditmanager-agent-1.2.3.tar").write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("x")
    assert package.available_versions(tmp_path) == ("0.9.0",)


# -- the origin the command points at -----------------------------------------------------------


@pytest.mark.parametrize(("given", "wanted"), [
    ("https://stand.example", "https://stand.example"),
    ("HTTPS://Stand.Example:8443", "https://stand.example:8443"),
    ("http://10.0.0.5:8080", "http://10.0.0.5:8080"),
    ("https://[::1]:443", "https://[::1]:443"),
    (" https://stand.example ", "https://stand.example"),
])
def test_an_origin_is_normalised(given: str, wanted: str) -> None:
    assert package.normalise_origin(given) == wanted


@pytest.mark.parametrize("given", [
    "", "stand.example", "ftp://stand.example", "https://", "https://stand.example/path",
    "https://stand.example/", "https://user@stand.example", "https://stand.example?x=1",
    "https://stand.example#x", "https://stand.example:0", "https://stand.example:70000",
    "https://stand.example:", "https://stand.example:80:90", "https://sta nd.example",
    "https://stand.example;rm -rf", "https://stand.example'$(id)'", "https://stand_example",
    "https://-stand.example", "javascript:alert(1)", "https://stand.example\\\\evil",
])
def test_anything_that_is_not_an_origin_is_refused_before_it_reaches_a_shell(given: str) -> None:
    with pytest.raises(ValueError):
        package.normalise_origin(given)


def test_the_origin_is_the_configured_one_and_only_that() -> None:
    assert package.resolve_origin("https://stand.example") == "https://stand.example"
    assert package.resolve_origin(" HTTPS://Stand.Example:8443 ") == "https://stand.example:8443"


@pytest.mark.parametrize("configured", [
    None, "", "   ", "not an origin", "https://stand.example/path", "ftp://stand.example",
    "https://user@stand.example", "https://stand.example;rm -rf",
])
def test_an_absent_or_malformed_configured_origin_is_a_refusal_and_never_guessed(
    configured: str | None,
) -> None:
    error = _refusal(package.resolve_origin, configured)
    assert error.code is ErrorCode.DEPENDENCY_UNAVAILABLE
    assert dict(error.detail_fields) == {"dependency": "public_origin"}


def test_no_origin_can_be_taken_from_a_request() -> None:
    import inspect

    assert list(inspect.signature(package.resolve_origin).parameters) == ["configured"]


# -- the command -------------------------------------------------------------------------------


def _command(origin: str = "https://stand.example") -> tuple[str, package.AgentPackage]:
    digest = hashlib.sha256(b"archive").hexdigest()
    found = package.AgentPackage(version="0.9.0", sha256=digest, size_bytes=7, path=Path("/nowhere"))
    return package.install_command(origin=origin, package=found, secret=SECRET, model="claude-opus-5"), found


def test_the_command_downloads_verifies_unpacks_and_installs_in_that_order() -> None:
    command, found = _command()
    steps = command.split(" && ")
    assert steps[0] == 'cd "$(mktemp -d)"'
    assert "curl" in steps[1] and "https://stand.example/api/v1/runner/agent-package/0.9.0" in steps[1]
    assert f"{found.sha256}  agent.tar.gz" in steps[2] and "sha256sum -c -" in steps[2]
    assert steps[3] == "tar -xzf agent.tar.gz"
    assert steps[4].endswith("bash install.sh") and len(steps) == 5
    assert len(command) <= 4096


def test_the_secret_is_in_one_environment_assignment_and_in_no_argument_vector() -> None:
    command, _ = _command()
    assert command.count(SECRET) == 1
    install = command.split(" && ")[-1]
    words = shlex.split(install)
    assignments = [word for word in words if "=" in word and word.split("=", 1)[0].isupper()]
    assert f"{package.ENROLLMENT_SECRET_ENV}={SECRET}" in assignments
    # Everything from the first word that is not an assignment is what the process list shows: the secret
    # is not in it, and `sudo` is told the variable's name and never its value.
    first_argument = next(index for index, word in enumerate(words) if word not in assignments)
    argv = words[first_argument:]
    assert argv[0] == "sudo" and all(SECRET not in word for word in argv)
    assert (f"--preserve-env={package.ENROLLMENT_SECRET_ENV},{package.STAND_ORIGIN_ENV},"
            f"{package.AGENT_MODEL_ENV}") in argv
    # The model the agent declares is the connection's pinned one, never the installer's choice.
    assert f"{package.AGENT_MODEL_ENV}=claude-opus-5" in assignments
    assert not any(word in ("env", "-E") for word in argv), "no `env VAR=value` and no value in argv"
    assert SECRET not in command.split(" && ")[1] and SECRET not in command.split(" && ")[2]


def test_an_https_origin_refuses_a_downgrade_and_an_http_one_does_not_pretend() -> None:
    secure, _ = _command("https://stand.example")
    plain, _ = _command("http://10.0.0.5:8080")
    assert "--proto '=https'" in secure and "--tlsv1.2" in secure
    assert "--proto" not in plain and "http://10.0.0.5:8080/api/v1/runner/agent-package/0.9.0" in plain


def test_the_command_has_no_command_substitution_but_its_one_temporary_directory() -> None:
    command, _ = _command()
    assert command.count("$(") == 1 and "`" not in command and ";" not in command
    assert "\n" not in command


def test_an_issued_package_names_no_path_in_its_repr() -> None:
    found = package.AgentPackage(
        version="0.9.0", sha256="a" * 64, size_bytes=1, path=Path("/app/agent-package/x.tar.gz"))
    assert "/app" not in repr(found)
