"""`infra/norms/publish-bundle-release.sh` (and `publish_bundle_release.py` behind it): a norms bundle becomes the assets of a GitHub
release, and a lock file says what to download. Against a stand-in GitHub (`fake_github.py`) and a bundle of a few kilobytes cut into
parts of 24 kB; nothing here reaches the network.

What is held:

* the release is created once, each part is uploaded under `<tag>.tar.zst.NNN` with its sha256 in the label, and the lock file names
  the parts (name, size, sha256, asset id), the bundle directory, the digest of its SHA256SUMS and the tar's bytes -- all of which a
  test recomputes from what the server holds, by decompressing the parts and listing the tar;
* the stream is deterministic and the tar is the one `push-bundle.sh` sends, so a rerun produces the same parts;
* it resumes: an asset that is there with the same size and sha256 is skipped, one that is truncated, relabelled or half-made is
  deleted and uploaded again, and a failure in the middle writes no lock file;
* the token reaches GitHub in the `Authorization` header and nowhere else: not in the output, not on a command line (there is no
  option that takes it), and a file others can read is refused before any request;
* `--dry-run` verifies the bundle and prints the plan, and touches neither the network nor the token nor the disk.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
PUBLISHER = ROOT / "infra" / "norms" / "publish_bundle_release.py"
WRAPPER = ROOT / "infra" / "norms" / "publish-bundle-release.sh"
PUSH_BUNDLE = ROOT / "infra" / "deploy" / "push-bundle.sh"
REPO = "acme-co/audit-install"
PART = 24_000


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


publisher = _load("publish_bundle_release_under_test", PUBLISHER)
fake_github = _load("fake_github_for_publisher_tests", Path(__file__).with_name("fake_github.py"))


@pytest.fixture(autouse=True)
def _no_waiting(monkeypatch):
    monkeypatch.setattr(publisher, "RETRY_WAIT", (0.0, 0.0))


@pytest.fixture()
def github():
    server = fake_github.FakeGithub(REPO)
    yield server
    server.close()


class Rig:
    def __init__(self, tmp: Path, github) -> None:
        self.tmp = tmp
        self.github = github
        (tmp / "bundles").mkdir()
        self.bundle = fake_github.make_bundle(tmp / "bundles")
        self.key = self.bundle.name
        self.digest = self.key.rsplit("+", 1)[1]
        self.tag = f"norms-0a1bafe103ff-{self.digest[:8]}"
        self.lock = tmp / "out" / "bundle-release.lock"
        self.work = tmp / "work"
        self.token = github.token
        self.token_file = tmp / "token"
        self.token_file.write_text(self.token + "\n")
        self.token_file.chmod(0o600)

    def argv(self, *extra: str) -> list[str]:
        return ["--bundle", str(self.bundle), "--repo", REPO, "--token-file", str(self.token_file), "--lock", str(self.lock),
                "--work-dir", str(self.work), "--api-base", self.github.base, "--part-size-bytes", str(PART), "--allow-small-disk", *extra]

    def publish(self, capsys, *extra: str) -> tuple[int, str, str]:
        code = publisher.main(self.argv(*extra))
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    def lock_values(self) -> dict:
        text = self.lock.read_text()
        values = {}
        parts = []
        for line in text.splitlines():
            if line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            if name == "part":
                parts.append(value.split(" "))
            else:
                values[name] = value
        values["parts"] = parts
        return values

    def asset_names(self) -> list[str]:
        return sorted(a["name"] for a in self.github.release(self.tag)["assets"])

    def archive(self) -> bytes:
        names = self.asset_names()
        return b"".join(self.github.asset_bytes(self.tag, name) for name in names)

    def tar(self) -> bytes:
        return subprocess.run(["zstd", "-dc"], input=self.archive(), capture_output=True, check=True).stdout


@pytest.fixture()
def rig(tmp_path: Path, github):
    return Rig(tmp_path, github)


def test_a_publication_creates_the_release_uploads_every_part_and_writes_a_lock_that_matches_what_the_server_holds(rig: Rig, capsys) -> None:
    code, out, err = rig.publish(capsys)
    assert code == 0, out + err
    release = rig.github.release(rig.tag)
    assert release is not None and release["make_latest"] == "false" and len(rig.github.releases) == 1
    names = rig.asset_names()
    assert names == [f"{rig.tag}.tar.zst.{n:03d}" for n in range(len(names))] and len(names) >= 3
    for asset in release["assets"]:
        assert asset["state"] == "uploaded" and asset["label"] == "sha256:" + hashlib.sha256(asset["_content"]).hexdigest()
        assert asset["size"] <= PART and len(asset["_content"]) == asset["size"]
    # the parts are one zstd stream of the stand's tar: it lists the bundle and its length and hash are the lock's
    tar = rig.tar()
    listing = subprocess.run(["tar", "-t"], input=tar, capture_output=True, check=True).stdout.decode().splitlines()
    assert f"{rig.key}/SHA256SUMS" in listing and f"{rig.key}/manifest.json" in listing and len(listing) >= 6
    values = rig.lock_values()
    assert values["lock_version"] == "1" and values["repo"] == REPO and values["tag"] == rig.tag and values["bundle"] == rig.key
    assert values["bundle_sums_sha256"] == rig.digest == hashlib.sha256((rig.bundle / "SHA256SUMS").read_bytes()).hexdigest()
    assert int(values["tar_bytes"]) == len(tar) and values["tar_sha256"] == hashlib.sha256(tar).hexdigest()
    assert values["zstd_level"] == "10" and int(values["part_size_bytes"]) == PART
    assert int(values["part_count"]) == len(names) == len(values["parts"])
    assert int(values["total_bytes"]) == sum(len(a["_content"]) for a in release["assets"])
    for (name, size, sha, asset_id), asset in zip(values["parts"], release["assets"]):
        assert (name, int(size), sha, int(asset_id)) == (asset["name"], asset["size"], hashlib.sha256(asset["_content"]).hexdigest(), asset["id"])
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", values["created"])
    # every call carried the token
    assert rig.github.requests and all(r["authorized"] for r in rig.github.requests)
    assert not rig.work.exists() or not list(rig.work.iterdir())          # no part is left on disk


def test_the_default_tag_is_the_content_key_and_the_digest_and_the_lock_is_written_where_asked(rig: Rig, capsys) -> None:
    assert publisher.short_key(rig.key) == rig.tag
    assert rig.publish(capsys)[0] == 0 and rig.lock.is_file() and not rig.lock.with_name(rig.lock.name + ".tmp").exists()
    # a tag of the owner's choice names the release and the assets
    other = rig.publish(capsys, "--tag", "norms-custom")
    assert other[0] == 0 and rig.github.release("norms-custom")["assets"][0]["name"] == "norms-custom.tar.zst.000"


def test_the_tar_is_the_one_push_bundle_sends() -> None:
    import shlex

    text = PUSH_BUNDLE.read_text()
    body = text[text.index("bundle_tar()"):text.index("\n}", text.index("bundle_tar()"))]
    command = shlex.split(body.split("tar ", 1)[1].replace("\\\n", " "))
    sent = tuple(word for word in command[:command.index("--directory")] if word.startswith("--"))
    assert sent == publisher.TAR_FLAGS
    assert publisher.tar_command(Path("/a/b/KEY"))[-4:] == ["--directory", "/a/b", "--", "KEY"] and command[command.index("--directory"):][2] == "--"


def test_a_rerun_makes_the_same_parts_and_uploads_nothing(rig: Rig, capsys) -> None:
    assert rig.publish(capsys)[0] == 0
    first = rig.lock_values()
    uploads = dict(rig.github.uploads_of)
    code, out, _ = rig.publish(capsys)
    assert code == 0 and rig.github.uploads_of == uploads
    assert out.count("already there and verified: skipped") == len(uploads)
    second = rig.lock_values()
    assert {k: v for k, v in second.items() if k != "created"} == {k: v for k, v in first.items() if k != "created"}


def test_a_failure_in_the_middle_writes_no_lock_and_the_rerun_uploads_only_what_is_missing(rig: Rig, capsys) -> None:
    second_part = f"{rig.tag}.tar.zst.001"
    rig.github.fail_uploads[second_part] = 99
    code, out, err = rig.publish(capsys)
    assert code == 3 and "FAILED" in err and "Run it again" in err and not rig.lock.exists()
    assert rig.github.uploads_of[f"{rig.tag}.tar.zst.000"] == 1 and rig.github.uploads_of[second_part] == 3   # three attempts
    rig.github.fail_uploads.clear()
    code, out, err = rig.publish(capsys)
    assert code == 0, out + err
    assert rig.github.uploads_of[f"{rig.tag}.tar.zst.000"] == 1                     # not uploaded again
    assert rig.lock.is_file() and len(rig.lock_values()["parts"]) == len(rig.asset_names())


def test_a_truncated_or_relabelled_or_half_made_asset_is_replaced_not_trusted(rig: Rig, capsys) -> None:
    assert rig.publish(capsys)[0] == 0
    good = {a["name"]: bytes(a["_content"]) for a in rig.github.release(rig.tag)["assets"]}
    names = sorted(good)
    assets = {a["name"]: a for a in rig.github.release(rig.tag)["assets"]}
    assets[names[0]]["_content"] = good[names[0]][:-10]                       # truncated: the size no longer matches
    assets[names[0]]["size"] = len(good[names[0]]) - 10
    assets[names[1]]["label"] = "sha256:" + "0" * 64                          # same size, another label
    assets[names[2]]["state"] = "starter"                                      # an upload that never finished
    before = dict(rig.github.uploads_of)
    code, out, err = rig.publish(capsys)
    assert code == 0, out + err
    for name in names[:3]:
        assert rig.github.uploads_of[name] == before[name] + 1, name
    for name in names[3:]:
        assert rig.github.uploads_of[name] == before[name], name
    assert {n: rig.github.asset_bytes(rig.tag, n) for n in names} == good
    assert all(a["state"] == "uploaded" for a in rig.github.release(rig.tag)["assets"])


def test_the_asset_digest_github_states_is_preferred_to_the_label(rig: Rig, capsys) -> None:
    assert rig.publish(capsys)[0] == 0
    asset = rig.github.release(rig.tag)["assets"][0]
    asset["digest"] = "sha256:" + "f" * 64          # GitHub says the bytes are not what the label claims
    before = rig.github.uploads_of[asset["name"]]
    assert rig.publish(capsys)[0] == 0
    assert rig.github.uploads_of[asset["name"]] == before + 1


def test_a_failed_upload_that_leaves_a_half_made_asset_is_cleaned_before_the_next_attempt(rig: Rig, capsys) -> None:
    name = f"{rig.tag}.tar.zst.000"
    rig.github.fail_uploads[name] = 1
    rig.github.starter_on_failure = True
    code, out, err = rig.publish(capsys)
    assert code == 0, out + err
    assert rig.github.uploads_of[name] == 2
    assert [a["state"] for a in rig.github.release(rig.tag)["assets"] if a["name"] == name] == ["uploaded"]


def test_the_token_is_sent_to_github_and_never_printed_or_taken_on_a_command_line(rig: Rig, tmp_path: Path, capsys) -> None:
    result = subprocess.run([str(WRAPPER), *rig.argv()], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert rig.token not in result.stdout + result.stderr and rig.token not in " ".join(rig.argv())
    assert rig.github.requests and all(r["authorized"] for r in rig.github.requests)
    assert str(rig.token_file) in " ".join(rig.argv())                           # the argument is the FILE
    refused = subprocess.run([str(WRAPPER), "--bundle", str(rig.bundle), "--token", rig.token], capture_output=True, text=True)
    assert refused.returncode == 2 and rig.token not in refused.stdout + refused.stderr and "no --token option" in refused.stderr
    for argument in (f"--token={rig.token}", f"--tok"):
        again = subprocess.run([str(WRAPPER), "--bundle", str(rig.bundle), argument, rig.token], capture_output=True, text=True)
        assert again.returncode == 2 and rig.token not in again.stdout + again.stderr
    pasted = subprocess.run([str(WRAPPER), "--bundle", str(rig.bundle), "--token-file", rig.token], capture_output=True, text=True)
    assert pasted.returncode == 2 and rig.token not in pasted.stdout + pasted.stderr
    # a wrong token is a failure that names the answer, not the token
    rig.token_file.write_text("ghp_wrongtoken000000000000\n")
    result = subprocess.run([str(WRAPPER), *rig.argv()], capture_output=True, text=True)
    assert result.returncode == 3 and "401" in result.stderr and "ghp_wrongtoken000000000000" not in result.stdout + result.stderr


def test_a_token_file_others_can_read_or_that_is_missing_is_refused_before_any_request(rig: Rig, capsys) -> None:
    rig.token_file.chmod(0o644)
    code, out, err = rig.publish(capsys)
    assert code == 2 and "can be read by others" in err and rig.token not in out + err and rig.github.requests == []
    rig.token_file.unlink()
    code, out, err = rig.publish(capsys)
    assert code == 2 and "cannot be read" in err and rig.github.requests == []
    rig.token_file.write_text("two tokens here\n")
    rig.token_file.chmod(0o600)
    assert rig.publish(capsys)[0] == 2


def test_a_dry_run_verifies_the_bundle_and_prints_the_plan_and_does_nothing_else(rig: Rig, tmp_path: Path, capsys) -> None:
    rig.token_file.unlink()                               # no token is needed, and none is read
    code, out, err = rig.publish(capsys, "--dry-run")
    assert code == 0, out + err
    assert f"release {REPO} tag {rig.tag}" in out and f"{rig.tag}.tar.zst.000" in out and "dry run: nothing was sent, no token was read" in out
    assert rig.github.requests == [] and not rig.lock.exists() and not rig.work.exists()
    assert re.search(r"tar [0-9]+ bytes", out)


def test_a_bundle_that_does_not_verify_or_is_not_named_like_one_is_refused_before_any_request(rig: Rig, tmp_path: Path, capsys) -> None:
    (tmp_path / "tampered").mkdir()
    tampered = fake_github.make_bundle(tmp_path / "tampered", tamper=True)
    argv = rig.argv()
    argv[argv.index("--bundle") + 1] = str(tampered)
    assert publisher.main(argv) == 2
    assert "does not verify" in capsys.readouterr().err and rig.github.requests == []
    odd = tmp_path / "bundles" / "not-a-bundle-name"
    odd.mkdir()
    argv[argv.index("--bundle") + 1] = str(odd)
    assert publisher.main(argv) == 2
    assert "not a bundle name" in capsys.readouterr().err and rig.github.requests == []


def test_the_repository_defaults_to_the_one_of_the_checkouts_origin(tmp_path: Path, monkeypatch) -> None:
    for address, expected in (("https://github.com/hoperlex/PDF-Analysis.git", "hoperlex/PDF-Analysis"),
                              ("git@github.com:acme-co/audit-install", "acme-co/audit-install"),
                              ("ssh://git@github.com/acme-co/audit-install.git/", "acme-co/audit-install")):
        checkout = tmp_path / address.replace("/", "_").replace(":", "_")
        subprocess.run(["git", "init", "-q", str(checkout)], check=True)
        subprocess.run(["git", "-C", str(checkout), "remote", "add", "origin", address], check=True)
        monkeypatch.setattr(publisher, "REPO_ROOT", checkout)
        assert publisher.repo_from_origin() == expected
    bare = tmp_path / "no-origin"
    subprocess.run(["git", "init", "-q", str(bare)], check=True)
    monkeypatch.setattr(publisher, "REPO_ROOT", bare)
    with pytest.raises(publisher.Refused):
        publisher.repo_from_origin()


def test_a_work_directory_without_room_for_one_part_is_a_failure_before_the_pipeline(rig: Rig, capsys, monkeypatch) -> None:
    monkeypatch.setattr(publisher.shutil, "disk_usage", lambda _path: SimpleNamespace(total=10**9, used=10**9 - 1000, free=1000))
    argv = [a for a in rig.argv() if a != "--allow-small-disk"]
    assert publisher.main(argv) == 3
    assert "one part needs" in capsys.readouterr().err and rig.github.releases == {} and rig.github.requests == []


def test_assets_of_another_publication_in_the_same_release_are_left_alone_and_named(rig: Rig, capsys) -> None:
    release = rig.github.seed_release(rig.tag)
    rig.github.seed_asset(rig.tag, "README.txt", b"hello")
    code, out, err = rig.publish(capsys)
    assert code == 0, out + err
    assert "README.txt" in out and "assets this publication did not make" in out
    assert rig.github.asset_bytes(rig.tag, "README.txt") == b"hello" and release is rig.github.release(rig.tag)


def test_the_wrapper_runs_it_at_low_priority_and_is_shellcheck_clean() -> None:
    text = WRAPPER.read_text()
    assert "nice -n 10" in text and "ionice -c 2 -n 7" in text and "python3 -I" in text
    if shutil.which("shellcheck"):
        done = subprocess.run(["shellcheck", "-x", str(WRAPPER)], capture_output=True, text=True, cwd=ROOT)
        assert done.returncode == 0, done.stdout


def test_the_publisher_has_no_option_that_takes_a_token_and_writes_it_nowhere() -> None:
    source = PUBLISHER.read_text()
    assert '"--token"' not in source and "--token-file" in source
    code = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))
    for sink in ("print(token", "say(token", "f\"{token", "write_text(token", "os.environ[\"GITHUB_TOKEN\"]"):
        assert sink not in code
