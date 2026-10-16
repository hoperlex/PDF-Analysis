"""A mirrored bucket is complete only when every listed payload is present and sealed."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts/recovery/object_copy.py"
SPEC = importlib.util.spec_from_file_location("offline_object_copy", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
object_copy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(object_copy)


def _fixture(tmp_path: Path) -> tuple[bytes, Path]:
    root = tmp_path / "objects"
    (root / "blobs/00").mkdir(parents=True)
    root.chmod(0o700)
    (root / "blobs/00/one").write_bytes(b"first payload")
    (root / "blobs/00/two").write_bytes(b"")
    inventory = b"blobs/00/one\t13\tfirst-etag\nblobs/00/two\t0\tsecond-etag\n"
    return inventory, root


def test_complete_mirror_seals_and_rechecks_exact_payloads(tmp_path: Path) -> None:
    inventory, root = _fixture(tmp_path)
    seal = object_copy.build_manifest(inventory, root)
    assert seal["count"] == 2
    assert seal["bytes"] == 13
    assert seal["inventory_sha256"] == hashlib.sha256(inventory).hexdigest()
    assert seal["objects"][0]["sha256"] == hashlib.sha256(b"first payload").hexdigest()
    saved = object_copy.manifest_bytes(seal)
    object_copy.verify_manifest(inventory, root, saved)
    object_copy.verify_manifest(inventory, root, saved)  # safe repeat


@pytest.mark.parametrize("change", ("missing", "extra", "size", "same_size_tamper", "symlink"))
def test_copy_cannot_be_sealed_if_object_set_or_bytes_are_wrong(tmp_path: Path, change: str) -> None:
    inventory, root = _fixture(tmp_path)
    if change == "missing":
        (root / "blobs/00/one").unlink()
    elif change == "extra":
        (root / "blobs/00/unlisted").write_bytes(b"stale")
    elif change == "size":
        (root / "blobs/00/one").write_bytes(b"truncated")
    elif change == "same_size_tamper":
        sealed = object_copy.manifest_bytes(object_copy.build_manifest(inventory, root))
        (root / "blobs/00/one").write_bytes(b"other payload")
        with pytest.raises(object_copy.ObjectCopyRefused, match="sealed object manifest"):
            object_copy.verify_manifest(inventory, root, sealed)
        return
    else:
        (root / "blobs/00/one").unlink()
        (root / "blobs/00/one").symlink_to(tmp_path / "outside")
    with pytest.raises(object_copy.ObjectCopyRefused):
        object_copy.build_manifest(inventory, root)


def test_fifo_at_listed_object_refuses_without_waiting_for_a_writer(tmp_path: Path) -> None:
    inventory, root = _fixture(tmp_path)
    object_path = root / "blobs/00/one"
    object_path.unlink()
    os.mkfifo(object_path, 0o600)
    code = """
import sys
from pathlib import Path
from scripts.recovery.object_copy import ObjectCopyRefused, build_manifest

try:
    build_manifest(b"blobs/00/one\\t13\\tfirst-etag\\nblobs/00/two\\t0\\tsecond-etag\\n", Path(sys.argv[1]))
except ObjectCopyRefused:
    print("REFUSED")
else:
    raise AssertionError("FIFO object was accepted")
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(root)], capture_output=True, text=True,
        timeout=3, check=False, cwd=Path(__file__).resolve().parents[3],
    )
    assert result.returncode == 0 and result.stdout == "REFUSED\n"
    assert object_path.is_fifo()


@pytest.mark.parametrize(
    "inventory",
    (
        b"blobs/../escape\t1\tetag\n",
        b"blobs/00/one\t13\te\nblobs/00/one\t13\te\n",
        b"blobs/00/two\t0\te\nblobs/00/one\t13\te\n",
        b"blobs/00/one\t013\te\n",
        b"blobs/00/one\t13\te",  # incomplete transfer
    ),
)
def test_ambiguous_or_unsafe_inventory_is_refused(inventory: bytes) -> None:
    with pytest.raises(object_copy.ObjectCopyRefused):
        object_copy.parse_inventory(inventory)


def test_cli_seal_is_repeatable_and_refuses_changed_manifest(tmp_path: Path) -> None:
    inventory, root = _fixture(tmp_path)
    listing = tmp_path / "inventory.tsv"
    listing.write_bytes(inventory)
    manifest = tmp_path / "objects.json"
    assert object_copy.main(["seal", str(listing), str(root), str(manifest)]) == 0
    assert object_copy.main(["seal", str(listing), str(root), str(manifest)]) == 0
    assert object_copy.main(["verify", str(listing), str(root), str(manifest)]) == 0
    assert manifest.stat().st_mode & 0o077 == 0
    manifest.write_bytes(b"{}\n")
    with pytest.raises(SystemExit) as refused:
        object_copy.main(["seal", str(listing), str(root), str(manifest)])
    assert refused.value.code == 3


def test_concurrent_manifest_creation_is_never_overwritten(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = tmp_path / "objects.json"
    real_link = object_copy.os.link

    def competing_link(source: str, destination: Path, **kwargs: object) -> None:
        destination.write_bytes(b"competitor seal\n")
        real_link(source, destination, **kwargs)

    monkeypatch.setattr(object_copy.os, "link", competing_link)
    with pytest.raises(object_copy.ObjectCopyRefused, match="appeared while sealing"):
        object_copy._seal(manifest, b"our seal\n")
    assert manifest.read_bytes() == b"competitor seal\n"
