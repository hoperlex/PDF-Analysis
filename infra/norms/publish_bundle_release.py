#!/usr/bin/env python3
"""Publish a verified norms bundle as the assets of a GitHub release, and write the lock file the installer reads (`FIRST-INSTALL-02`).

    infra/norms/publish-bundle-release.sh --bundle DIR [--repo owner/name] [--tag TAG] [--token-file PATH] [--dry-run]

Run by the owner, on the host that holds the bundle, ONCE PER NEW NORMS SNAPSHOT. The wrapper `publish-bundle-release.sh` runs this
file under `nice` and `ionice`. Standard library only; `tar` and `zstd` are the host's.

WHAT IT DOES, IN ORDER

1. checks the bundle with the same rule the stand applies (`infra/deploy/push-bundle.sh --dry-run`: the directory name is
   `<content key>+<sha256 of SHA256SUMS>`, the files are exactly the listed ones and every file is RE-HASHED), and takes from it the
   byte count of the tar the stand's `receive` verb will be given;
2. creates the release `--tag` of `--repo` if it does not exist (GitHub REST API; `--dry-run` stops before any network use);
3. streams `tar` -- the very command `push-bundle.sh` sends, deterministic -- into `zstd -10 -T2` and cuts the compressed stream into
   parts of 1900 MiB (a release asset must be under 2 GiB). **Only one part is on disk at a time**: a part is written to the work
   directory, compared with what the release already holds, uploaded if it is not there, and deleted. Peak extra disk is one part;
4. uploads each part as an asset named `<tag>.tar.zst.NNN`, with its sha256 in the asset's label (`sha256:<hex>`);
5. writes the lock file (default `infra/norms/bundle-release.lock`): repo, tag, bundle directory name, the digest of its SHA256SUMS,
   the tar's byte count and sha256, and every part's name, size, sha256 and asset id. The owner commits it; the installer reads it.

RESUMABLE. The stream is deterministic, so a rerun produces the same parts. A part whose asset is already there with the same size,
state `uploaded` and the same sha256 (GitHub's own `digest` when it states one, else the label this tool set) is skipped; an asset
with the same name and a different size, label or state is deleted and uploaded again.

THE TOKEN. Contents read and write on this one repository, in a root-only file (`--token-file`, default
`/root/.config/auditmanager/github-upload-token`; refused when group or others can read it). It is read into memory, sent only as the
`Authorization` header of requests to GitHub, and never printed, logged, put on a command line or written anywhere. There is no
`--token` option on purpose.

Exit codes: 0 done; 2 the arguments or the bundle were refused (nothing was sent); 3 a failure after that (the message says which;
run it again, it resumes).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
PUSH_BUNDLE = REPO_ROOT / "infra" / "deploy" / "push-bundle.sh"
DEFAULT_TOKEN_FILE = "/root/.config/auditmanager/github-upload-token"
DEFAULT_LOCK = REPO_ROOT / "infra" / "norms" / "bundle-release.lock"
DEFAULT_API = "https://api.github.com"
#: A release asset must be smaller than 2 GiB; 1900 MiB leaves room.
PART_SIZE = 1900 * 1024 * 1024
ZSTD_LEVEL = 10
LOCK_VERSION = 1
#: Seconds to wait before the second and third attempt of one request or upload.
RETRY_WAIT = (5.0, 20.0)
#: Same bundle name grammar as `infra/deploy/lib/forced-command.sh` (`FC_BUNDLE_KEY_ERE`).
KEY_PATTERN = re.compile(
    r"^(undated|[0-9]{4}-[0-9]{2}-[0-9]{2}\.\.[0-9]{4}-[0-9]{2}-[0-9]{2})\+(0|[1-9][0-9]{0,5})d"
    r"(\+[1-9][0-9]{0,5}r(\+[1-9][0-9]{0,5}u)?|\+0r\+[1-9][0-9]{0,5}u)?\.[0-9a-f]{12}(\+seg-[a-z0-9]+(-[a-z0-9]+)*)?\+[0-9a-f]{64}$"
)
REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
TAG_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
#: The tar `push-bundle.sh` sends (`bundle_tar` there), byte for byte; a test holds the two equal.
TAR_FLAGS = ("--create", "--format=gnu", "--sort=name", "--owner=0", "--group=0", "--numeric-owner", "--mtime=@0",
             "--hard-dereference", "--mode=u+rwX,go+rX,go-w")


class Refused(Exception):
    """Exit 2: nothing was sent."""


class Failed(Exception):
    """Exit 3: a failure after the arguments were accepted."""


# ----------------------------------------------------------------------------------------------------------- GitHub


class Github:
    """The few REST calls the publisher needs. The token lives in this object's header and nowhere else."""

    def __init__(self, base: str, repo: str, token: str, *, opener: Callable[..., Any] = urllib.request.urlopen):
        self.base = base.rstrip("/")
        self.repo = repo
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "auditmanager-norms-publisher",
        }
        self._open = opener

    def request(self, method: str, url: str, body: Any = None, *, data_file: Path | None = None, size: int = 0,
                label: str = "request") -> Any:
        headers = dict(self._headers)
        data: Any = None
        if data_file is not None:
            data = open(data_file, "rb")
            headers["Content-Type"] = "application/octet-stream"
            headers["Content-Length"] = str(size)
        elif body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        try:
            request = urllib.request.Request(url, data=data, method=method, headers=headers)
            with self._open(request, timeout=600) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            raise GithubError(error.code, _message(error), label) from None
        except (urllib.error.URLError, OSError, TimeoutError) as error:
            raise GithubError(0, type(error).__name__, label) from None
        finally:
            if data_file is not None and data is not None:
                data.close()
        return json.loads(raw.decode("utf-8")) if raw else None

    def release_by_tag(self, tag: str) -> dict[str, Any] | None:
        try:
            return self.request("GET", f"{self.base}/repos/{self.repo}/releases/tags/{tag}", label="read the release")
        except GithubError as error:
            if error.status == 404:
                return None
            raise

    def create_release(self, tag: str, name: str, notes: str) -> dict[str, Any]:
        body = {"tag_name": tag, "name": name, "body": notes, "draft": False, "prerelease": False, "make_latest": "false"}
        try:
            return self.request("POST", f"{self.base}/repos/{self.repo}/releases", body, label="create the release")
        except GithubError as error:
            if error.status == 422:       # created meanwhile (a second publisher, or a rerun that raced): read it
                existing = self.release_by_tag(tag)
                if existing is not None:
                    return existing
            raise

    def delete_asset(self, asset_id: int) -> None:
        self.request("DELETE", f"{self.base}/repos/{self.repo}/releases/assets/{asset_id}", label="delete an asset")

    def upload_asset(self, release: dict[str, Any], name: str, label_text: str, path: Path, size: int) -> dict[str, Any]:
        template = str(release["upload_url"])
        url = template.split("{")[0] + "?" + urllib.parse.urlencode({"name": name, "label": label_text})
        return self.request("POST", url, data_file=path, size=size, label=f"upload {name}")


class GithubError(Exception):
    def __init__(self, status: int, message: str, what: str):
        super().__init__(f"{what}: {status or 'no answer'} {message}")
        self.status = status


def _message(error: urllib.error.HTTPError) -> str:
    try:
        return str(json.loads(error.read().decode("utf-8")).get("message", ""))[:200]
    except (ValueError, AttributeError, OSError):
        return ""


def retrying(action: Callable[[], Any], what: str, say: Callable[[str], None]) -> Any:
    """Three attempts for a transient failure (no answer, or a 5xx); anything else is final."""
    for attempt, wait in enumerate((0.0, *RETRY_WAIT)):
        if wait:
            time.sleep(wait)
        try:
            return action()
        except GithubError as error:
            transient = error.status == 0 or error.status >= 500
            if not transient or attempt == len(RETRY_WAIT):
                raise
            say(f"{what}: {error}; trying again")
    raise AssertionError("unreachable")


# ------------------------------------------------------------------------------------------------------- the bundle


def verify_bundle(bundle: Path) -> tuple[str, str, int]:
    """(directory name, digest of SHA256SUMS, tar byte count) after the stand's own rule has been applied to the directory."""
    if bundle.is_symlink() or not bundle.is_dir():
        raise Refused(f"{bundle} is not a directory")
    key = bundle.name
    if not KEY_PATTERN.fullmatch(key):
        raise Refused(f"'{key}' is not a bundle name the stand admits (<content key>+<sha256 of SHA256SUMS>)")
    digest = key.rsplit("+", 1)[1]
    if not PUSH_BUNDLE.is_file():
        raise Refused(f"{PUSH_BUNDLE} is missing: the bundle cannot be checked")
    done = subprocess.run([str(PUSH_BUNDLE), "--dry-run", str(bundle)], capture_output=True, text=True)
    if done.returncode != 0:
        last = (done.stderr.strip().splitlines() or done.stdout.strip().splitlines() or ["no message"])[-1]
        raise Refused(f"the bundle does not verify: {last}")
    match = re.search(r"would send ([0-9]+) bytes as: receive ", done.stdout)
    if match is None:
        raise Refused("push-bundle.sh --dry-run did not say how large the tar is")
    return key, digest, int(match.group(1))


def tar_command(bundle: Path) -> list[str]:
    return ["tar", *TAR_FLAGS, "--directory", str(bundle.parent), "--", bundle.name]


class PartWriter:
    """The compressed stream, cut into parts of at most `part_size`, one file on disk at a time."""

    def __init__(self, work: Path, prefix: str, part_size: int, finished: Callable[[int, Path, int, str], None]):
        self.work, self.prefix, self.part_size, self.finished = work, prefix, part_size, finished
        self.index = 0
        self.count = 0
        self._open_part()

    def _open_part(self) -> None:
        self.path = self.work / f"{self.prefix}.{self.index:03d}.part"
        self.handle = open(self.path, "wb")
        self.size = 0
        self.sha = hashlib.sha256()

    def write(self, chunk: bytes) -> None:
        view = memoryview(chunk)
        while view:
            room = self.part_size - self.size
            piece = view[:room]
            self.handle.write(piece)
            self.sha.update(piece)
            self.size += len(piece)
            view = view[len(piece):]
            if self.size == self.part_size:
                self._finish(more=True)

    def close(self) -> None:
        if self.size > 0:
            self._finish(more=False)
        else:
            self.handle.close()
            self.path.unlink(missing_ok=True)

    def _finish(self, *, more: bool) -> None:
        self.handle.close()
        try:
            self.finished(self.index, self.path, self.size, self.sha.hexdigest())
        finally:
            self.path.unlink(missing_ok=True)
        self.count += 1
        self.index += 1
        if more:
            self._open_part()


def stream_parts(bundle: Path, work: Path, prefix: str, part_size: int, level: int,
                 finished: Callable[[int, Path, int, str], None]) -> tuple[int, str, int]:
    """Run tar | zstd and hand every part to `finished` as it is complete. Returns (tar bytes, tar sha256, part count)."""
    environment = dict(os.environ, LC_ALL="C")
    tar = subprocess.Popen(tar_command(bundle), stdout=subprocess.PIPE, env=environment)
    zstd = subprocess.Popen(["zstd", f"-{level}", "-T2", "-q", "-c"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    tar_sha = hashlib.sha256()
    counted = {"bytes": 0}

    def relay() -> None:
        assert tar.stdout is not None and zstd.stdin is not None
        try:
            while True:
                chunk = tar.stdout.read(1 << 20)
                if not chunk:
                    break
                tar_sha.update(chunk)
                counted["bytes"] += len(chunk)
                zstd.stdin.write(chunk)
        except BrokenPipeError:
            pass
        finally:
            try:
                zstd.stdin.close()
            except BrokenPipeError:
                pass

    thread = threading.Thread(target=relay, daemon=True)
    thread.start()
    writer = PartWriter(work, prefix, part_size, finished)
    try:
        assert zstd.stdout is not None
        while True:
            chunk = zstd.stdout.read(1 << 20)
            if not chunk:
                break
            writer.write(chunk)
        writer.close()
    except BaseException:
        # Our own two children, by their handles: the stream is abandoned.
        for process in (tar, zstd):
            process.kill()
        raise
    finally:
        thread.join()
        for process in (tar, zstd):
            process.wait()
    if tar.returncode != 0 or zstd.returncode != 0:
        raise Failed(f"the archive could not be made (tar status {tar.returncode}, zstd status {zstd.returncode})")
    return counted["bytes"], tar_sha.hexdigest(), writer.count


# --------------------------------------------------------------------------------------------------------- the lock


def render_lock(*, repo: str, tag: str, key: str, digest: str, tar_bytes: int, tar_sha256: str, level: int, part_size: int,
                parts: list[tuple[str, int, str, int]], created: str) -> str:
    lines = [
        "# The norms bundle this repository publishes as a GitHub release. Written by infra/norms/publish-bundle-release.sh;",
        "# read as DATA (NAME=VALUE, one `part=` line per part), never sourced, by infra/deploy/first-install.sh.",
        f"lock_version={LOCK_VERSION}",
        f"repo={repo}",
        f"tag={tag}",
        f"bundle={key}",
        f"bundle_sums_sha256={digest}",
        f"tar_bytes={tar_bytes}",
        f"tar_sha256={tar_sha256}",
        f"zstd_level={level}",
        f"part_size_bytes={part_size}",
        f"created={created}",
        f"total_bytes={sum(size for _, size, _, _ in parts)}",
        f"part_count={len(parts)}",
        "# part=<asset name> <size in bytes> <sha256> <asset id>",
    ]
    lines += [f"part={name} {size} {sha} {asset_id}" for name, size, sha, asset_id in parts]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------------------------------------------------- run


def remote_matches(asset: dict[str, Any], size: int, sha: str) -> bool:
    if asset.get("state") != "uploaded" or asset.get("size") != size:
        return False
    digest = str(asset.get("digest") or "")
    if digest.startswith("sha256:"):
        return digest[len("sha256:"):] == sha
    return asset.get("label") == f"sha256:{sha}"


TOKEN_SHAPE = re.compile(r"(^|/)(gh[pousr]_|github_pat_)[A-Za-z0-9_]{10,}")


def read_token(path: Path) -> str:
    if TOKEN_SHAPE.search(str(path)):
        raise Refused("--token-file takes the NAME of a file that holds the token, and was given something that looks like a token")
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError:
        raise Refused(f"the token file {path} cannot be read; the owner creates it (fine-grained, Contents read and write on this repository only)") from None
    if mode & 0o077:
        raise Refused(f"the token file {path} can be read by others (mode {mode:o}); it must be 600")
    token = path.read_text(encoding="utf-8").strip()
    if not token or any(character.isspace() for character in token):
        raise Refused(f"the token file {path} does not hold exactly one token")
    return token


def repo_from_origin() -> str:
    done = subprocess.run(["git", "-C", str(REPO_ROOT), "remote", "get-url", "origin"], capture_output=True, text=True)
    url = done.stdout.strip()
    match = re.search(r"[:/]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/*$", url)
    if done.returncode != 0 or match is None:
        raise Refused("this checkout has no origin to take the repository from: pass --repo owner/name")
    return f"{match.group(1)}/{match.group(2)}"


def short_key(key: str) -> str:
    """`norms-<12 hex of the content key>-<first 8 hex of the digest>`."""
    return f"norms-{re.search(r'[.]([0-9a-f]{12})(?:[+]|$)', key).group(1)}-{key.rsplit('+', 1)[1][:8]}"


def run(arguments: argparse.Namespace, say: Callable[[str], None]) -> int:
    bundle = Path(arguments.bundle).resolve()
    repo = arguments.repo or repo_from_origin()
    if not REPO_PATTERN.fullmatch(repo):
        raise Refused("--repo is owner/name")
    key, digest, tar_bytes = verify_bundle(bundle)
    tag = arguments.tag or short_key(key)
    if not TAG_PATTERN.fullmatch(tag):
        raise Refused("--tag is letters, digits, '.', '_' and '-'")
    work = Path(arguments.work_dir)
    lock_path = Path(arguments.lock)
    part_size = arguments.part_size_bytes
    estimate = max(1, -(-int(tar_bytes * 0.8) // part_size))
    say(f"bundle {key}")
    say(f"  tar {tar_bytes} bytes; release {repo} tag {tag}; assets {tag}.tar.zst.000 ... (about {estimate} of at most {part_size} bytes)")
    say(f"  lock file {lock_path}")
    if arguments.dry_run:
        say("dry run: nothing was sent, no token was read, nothing was written")
        return 0
    token = read_token(Path(arguments.token_file))
    work.mkdir(parents=True, exist_ok=True)
    work.chmod(0o700)
    free = shutil.disk_usage(work).free
    if free < part_size + (256 << 20) and not arguments.allow_small_disk:
        raise Failed(f"{work} has {free} bytes free and one part needs {part_size}: pass --work-dir on a larger disk")
    github = Github(arguments.api_base, repo, token)
    release = retrying(lambda: github.release_by_tag(tag), "read the release", say)
    if release is None:
        notes = (f"The norms bundle `{key}`, compressed with zstd and cut into parts. `infra/norms/bundle-release.lock` of the repository "
                 f"names the parts and their sha256; infra/deploy/first-install.sh downloads and imports them.")
        release = retrying(lambda: github.create_release(tag, f"Norms bundle {tag}", notes), "create the release", say)
        say(f"created the release {tag}")
    else:
        say(f"the release {tag} exists with {len(release.get('assets', []))} assets")
    prefix = f"{tag}.tar.zst"
    uploaded: dict[str, tuple[int, str, int]] = {}
    counts = {"uploaded": 0, "skipped": 0}

    def finished(index: int, path: Path, size: int, sha: str) -> None:
        name = f"{prefix}.{index:03d}"
        current = retrying(lambda: github.release_by_tag(tag), "read the release", say) or release
        existing = {a["name"]: a for a in current.get("assets", [])}
        asset = existing.get(name)
        if asset is not None and remote_matches(asset, size, sha):
            say(f"part {index:03d}: {size} bytes sha256 {sha[:12]}: already there and verified: skipped")
            uploaded[name] = (size, sha, int(asset["id"]))
            counts["skipped"] += 1
            return
        if asset is not None:
            say(f"part {index:03d}: the asset of that name differs (size {asset.get('size')}, state {asset.get('state')}): replaced")
            retrying(lambda: github.delete_asset(int(asset["id"])), "delete an asset", say)

        def send() -> dict[str, Any]:
            try:
                return github.upload_asset(current, name, f"sha256:{sha}", path, size)
            except GithubError:
                # A failed upload can leave a half-made asset of that name; it would make the next attempt a conflict.
                again = github.release_by_tag(tag) or {"assets": []}
                for leftover in again.get("assets", []):
                    if leftover["name"] == name:
                        github.delete_asset(int(leftover["id"]))
                raise

        answer = retrying(send, f"upload {name}", say)
        if answer.get("size") != size or answer.get("state") != "uploaded":
            raise Failed(f"GitHub answered for {name} with size {answer.get('size')} and state {answer.get('state')}")
        uploaded[name] = (size, sha, int(answer["id"]))
        counts["uploaded"] += 1
        say(f"part {index:03d}: {size} bytes sha256 {sha[:12]}: uploaded")

    counted, tar_sha, count = stream_parts(bundle, work, f"{tag}", part_size, arguments.zstd_level, finished)
    if counted != tar_bytes:
        raise Failed(f"the tar made here has {counted} bytes and push-bundle.sh counted {tar_bytes}: the two tar commands differ")
    final = retrying(lambda: github.release_by_tag(tag), "read the release", say)
    assets = {a["name"]: a for a in (final or {}).get("assets", [])}
    parts: list[tuple[str, int, str, int]] = []
    for index in range(count):
        name = f"{prefix}.{index:03d}"
        size, sha, asset_id = uploaded[name]
        asset = assets.get(name)
        if asset is None or not remote_matches(asset, size, sha):
            raise Failed(f"after the upload the release does not hold {name} as it was made")
        parts.append((name, size, sha, asset_id))
    created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    text = render_lock(repo=repo, tag=tag, key=key, digest=digest, tar_bytes=tar_bytes, tar_sha256=tar_sha, level=arguments.zstd_level,
                       part_size=part_size, parts=parts, created=created)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = lock_path.with_name(lock_path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, lock_path)
    stray = sorted(set(assets) - {name for name, *_ in parts})
    say(f"{count} parts, {sum(p[1] for p in parts)} bytes ({counts['uploaded']} uploaded, {counts['skipped']} skipped); lock written: {lock_path}")
    say("commit the lock file; the installer downloads this release by itself")
    if stray:
        say(f"note: the release also holds assets this publication did not make: {', '.join(stray)}")
    try:
        work.rmdir()
    except OSError:
        pass
    return 0


class QuietParser(argparse.ArgumentParser):
    """argparse echoes the arguments it does not understand; a token pasted by mistake must not be echoed with them."""

    def error(self, message: str) -> None:  # type: ignore[override]
        self.print_usage(sys.stderr)
        print("publish-bundle-release: REFUSED: the arguments were not understood (they are not repeated here); there is no --token "
              "option: the token is read from the file --token-file names", file=sys.stderr)
        raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    parser = QuietParser(prog="publish-bundle-release.sh", description="Publish a norms bundle as a GitHub release.", allow_abbrev=False)
    parser.add_argument("--bundle", required=True, help="the bundle directory (named <content key>+<sha256 of SHA256SUMS>)")
    parser.add_argument("--repo", help="owner/name of the PUBLIC repository (default: from this checkout's origin)")
    parser.add_argument("--tag", help="the release tag (default: norms-<12 hex of the content key>-<8 hex of the digest>)")
    parser.add_argument("--token-file", default=DEFAULT_TOKEN_FILE, help=f"default {DEFAULT_TOKEN_FILE}")
    parser.add_argument("--lock", default=str(DEFAULT_LOCK), help="where the lock file is written (default infra/norms/bundle-release.lock)")
    parser.add_argument("--work-dir", default=os.path.join(os.environ.get("TMPDIR", "/var/tmp"), f"norms-publish-{os.getuid()}"),
                        help="where one part at a time is written (needs about 2 GiB free)")
    parser.add_argument("--dry-run", action="store_true", help="verify the bundle and print the plan; send and write nothing")
    # For the tests: a small part, a stand-in API, a small disk.
    parser.add_argument("--part-size-bytes", type=int, default=PART_SIZE, help=argparse.SUPPRESS)
    parser.add_argument("--zstd-level", type=int, default=ZSTD_LEVEL, help=argparse.SUPPRESS)
    parser.add_argument("--api-base", default=DEFAULT_API, help=argparse.SUPPRESS)
    parser.add_argument("--allow-small-disk", action="store_true", help=argparse.SUPPRESS)
    arguments = parser.parse_args(argv)

    def say(line: str) -> None:
        print(f"publish-bundle-release: {line}", flush=True)

    try:
        return run(arguments, say)
    except Refused as error:
        print(f"publish-bundle-release: REFUSED: {error}", file=sys.stderr)
        return 2
    except (Failed, GithubError) as error:
        print(f"publish-bundle-release: FAILED: {error}. Run it again: finished parts are skipped.", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
