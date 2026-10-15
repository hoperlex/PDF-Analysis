"""Read-only W54 corpus inventory and capacity preflight.

Run with the *shared* norms root, not a worktree-relative ``.local``::

    python scripts/norms/corpus_preflight.py --norms-root /path/to/.local/norms \
        --next-step bundle-export

This checks metadata and current host headroom without opening source PDFs, a database,
S3, or a provider. ``METADATA_READY`` is not permission to start a heavy operation:
source sums, dump and build bytes still need their owning verifiers, and the operator
remeasures in the night window. A bundle candidate is never called verified here;
``auditmanager.norms.bundle verify`` must re-hash it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

# Standalone operator invocation from a checkout, like other repository scripts.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from auditmanager.norms.corpus_source import DropSumsInvalid, read_drop_sums  # noqa: E402

MANIFEST_SHA256 = "160fdc7ea261b44298757b3a066982fd167b389fde614fb119c4c1d0d72fbb3b"
DOCUMENTS = 674
FILES = 31_619
GIB = 1024**3
MEMORY_FLOOR = 6 * GIB
DISK_RESERVE = 3 * GIB
# W54 §3.9: source-sums has no stated increment, so check the 3 GiB reserve only.
# Base load and restore-verify each have a 3 GiB increment; bundle adds 0.6 GiB.
INCREMENTS = {"source-sums": 0, "base-load": 3 * GIB, "restore-verify": 3 * GIB,
              "bundle-export": (6 * GIB + 9) // 10}
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class Capacity:
    disk_available_bytes: int
    disk_required_bytes: int
    memory_available_bytes: int
    memory_required_bytes: int = MEMORY_FLOOR


@dataclass(frozen=True)
class Result:
    next_step: str
    manifest_sha256: str | None
    document_directories: int | None
    regular_files: int | None
    source_sums: str
    restore_verified_dump: str
    build_checkpoint: str
    bundle_candidate: str
    capacity: Capacity | None
    refusals: tuple[str, ...]
    qualification: str = (
        "metadata-only, not authorization to operate: run sha256sum -c for the source, "
        "restore-verify for the dump, embedding status/load for the build, and full "
        "bundle verify; stand capacity and P3 compatibility were not checked"
    )

    @property
    def ok(self) -> bool:
        return not self.refusals


def _is_regular(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def _inventory(corpus: Path) -> tuple[int, set[str], bool]:
    """Only directory entries and lstat metadata; no document content reads."""
    documents = 0
    files: set[str] = set()
    unsafe = False
    for base, dirs, names in os.walk(corpus, followlinks=False):
        here = Path(base)
        if here == corpus:
            documents = sum((here / name).is_dir() and not (here / name).is_symlink() for name in dirs)
        for name in dirs:
            if (here / name).is_symlink():
                unsafe = True
        for name in names:
            if _is_regular(here / name):
                files.add((here / name).relative_to(corpus).as_posix())
            else:
                unsafe = True
    return documents, files, unsafe


def _sums(root: Path, source_paths: set[str] | None) -> tuple[str, str | None]:
    candidates = sorted((root / "corpus-sums").glob("*/SHA256SUMS"))
    if not candidates:
        return "absent", None
    if len(candidates) != 1:
        return "ambiguous", None
    path = candidates[0]
    if not _is_regular(path):
        return "not_regular", None
    try:
        parsed = read_drop_sums(path)  # same parser as repair and bundle export
    except DropSumsInvalid:
        return "malformed", None
    if source_paths is None or set(parsed.entries) != source_paths:
        return "path_set_mismatch", None
    return "listed_unverified", parsed.sha256


def _dump(root: Path) -> str:
    directory = root / "promotion-dumps"
    candidates = sorted(directory.glob("promotion-*.dump"))
    if not candidates:
        return "absent"
    latest = candidates[-1]
    if not _is_regular(latest):
        return "not_regular"
    marker = Path(str(latest) + ".verified")
    sha = Path(str(latest) + ".sha256")
    fingerprint = Path(str(latest) + ".fingerprint")
    if not all(_is_regular(path) for path in (sha, fingerprint)):
        return "missing_dump_metadata"
    if not fingerprint.stat().st_size:
        return "malformed_dump_metadata"
    parts = sha.read_text(encoding="ascii", errors="replace").strip().split()
    if len(parts) != 2 or not HEX64.fullmatch(parts[0]) or parts[1] != latest.name:
        return "malformed_dump_metadata"
    if not _is_regular(marker):
        return "dump_metadata_present_unverified"
    if marker.stat().st_size != 0:
        return "malformed_restore_proof"
    return "restore_marker_present_unrehashed"


def _build(root: Path) -> str:
    builds = root / "builds"
    candidates = [path for path in builds.glob("*/plan.json") if _is_regular(path)]
    if not candidates:
        return "absent"
    for plan in candidates:
        try:
            batches = json.loads(plan.read_bytes())["batches"]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if not isinstance(batches, list) or not batches:
            continue
        indices = [row.get("index") for row in batches if isinstance(row, dict)]
        if indices != list(range(len(batches))):
            continue
        vectors = plan.parent / "vectors"
        inputs = plan.parent / "inputs"
        if all(
            _is_regular(inputs / f"batch-{index:05d}.jsonl")
            and _is_regular(vectors / f"batch-{index:05d}.jsonl")
            and _is_regular(vectors / f"batch-{index:05d}.jsonl.sha256")
            for index in indices
        ):
            return "batch_files_present_unverified"
    return "plan_only_or_partial"


def _bundle(root: Path, drop_sums_sha: str | None) -> str:
    bundles = root / "bundles"
    candidates = [path for path in bundles.iterdir()] if bundles.is_dir() else []
    if not candidates:
        return "absent"
    valid = []
    for path in candidates:
        if not path.is_dir() or path.is_symlink() or "+" not in path.name:
            continue
        digest = path.name.rsplit("+", 1)[-1]
        sums = path / "SHA256SUMS"
        manifest = path / "manifest.json"
        if not HEX64.fullmatch(digest) or not _is_regular(sums) or not _is_regular(manifest):
            continue
        if hashlib.sha256(sums.read_bytes()).hexdigest() != digest:
            continue
        try:
            metadata = json.loads(manifest.read_bytes())
        except (OSError, ValueError):
            continue
        if (
            not isinstance(metadata, dict)
            or metadata.get("build") is None
            or not isinstance(metadata.get("drop"), dict)
            or metadata["drop"].get("sums_sha256") != drop_sums_sha
            or metadata.get("content_key") != path.name.rsplit("+", 1)[0]
            or not (path / "build").is_dir()
            or not any(_is_regular(item) for item in (path / "build").glob("chunks-*.jsonl"))
        ):
            continue
        valid.append(path)
    if len(valid) != 1:
        return "absent_or_ambiguous_complete_candidate"
    return "build_declared_payload_present_unverified"


def _capacity(root: Path, next_step: str) -> Capacity:
    disk = os.statvfs(root)
    disk_available = disk.f_bavail * disk.f_frsize  # df -B1 Avail semantics
    meminfo = Path("/proc/meminfo").read_text(encoding="ascii")
    match = re.search(r"^MemAvailable:\s+(\d+) kB$", meminfo, re.MULTILINE)
    if match is None:
        raise ValueError("MemAvailable is unavailable")
    memory_available = int(match.group(1)) * 1024  # free -b available, no swap
    return Capacity(disk_available, DISK_RESERVE + INCREMENTS[next_step], memory_available)


def inspect(
    root: Path,
    next_step: str,
    *,
    expected_manifest_sha256: str = MANIFEST_SHA256,
    expected_documents: int = DOCUMENTS,
    expected_files: int = FILES,
    measure: Callable[[Path, str], Capacity] = _capacity,
) -> Result:
    if next_step not in INCREMENTS:
        raise ValueError(f"unsupported next step: {next_step}")
    refusals: list[str] = []
    manifest_sha: str | None = None
    docs: int | None = None
    files: int | None = None
    source_paths: set[str] | None = None
    if not root.is_dir() or root.is_symlink():
        refusals.append("norms_root_absent")
        return Result(next_step, None, None, None, "absent", "absent", "absent", "absent", None, tuple(refusals))
    corpus = root / "corpus"
    manifest = corpus / "MANIFEST.json"
    if not corpus.is_dir() or corpus.is_symlink() or not _is_regular(manifest):
        refusals.append("source_manifest_absent")
    else:
        raw = manifest.read_bytes()
        manifest_sha = hashlib.sha256(raw).hexdigest()
        if manifest_sha != expected_manifest_sha256:
            refusals.append("source_manifest_digest")
        try:
            data = json.loads(raw)
            if data["summary"]["documents"] != expected_documents or len(data["documents"]) != expected_documents:
                refusals.append("source_manifest_count")
        except (ValueError, KeyError, TypeError):
            refusals.append("source_manifest_malformed")
        docs, source_paths, unsafe = _inventory(corpus)
        files = len(source_paths)
        if unsafe:
            refusals.append("source_nonregular_entry")
        if docs != expected_documents or files != expected_files:
            refusals.append("source_tree_count")
    source_sums, sums_sha = _sums(root, source_paths)
    dump = _dump(root)
    build = _build(root)
    bundle = _bundle(root, sums_sha)
    if next_step != "source-sums" and source_sums != "listed_unverified":
        refusals.append("source_sums_unavailable")
    if next_step == "restore-verify" and dump not in {
        "dump_metadata_present_unverified", "restore_marker_present_unrehashed"
    }:
        refusals.append("dump_metadata_unavailable")
    if next_step == "bundle-export" and dump != "restore_marker_present_unrehashed":
        refusals.append("restore_verified_dump_unavailable")
    if next_step == "bundle-export" and build != "batch_files_present_unverified":
        refusals.append("build_checkpoint_unavailable")
    try:
        capacity = measure(root, next_step)
    except (OSError, ValueError):
        capacity = None
        refusals.append("capacity_unavailable")
    else:
        if capacity.disk_available_bytes < capacity.disk_required_bytes:
            refusals.append("disk_floor")
        if capacity.memory_available_bytes < capacity.memory_required_bytes:
            refusals.append("memory_floor")
    return Result(next_step, manifest_sha, docs, files, source_sums, dump, build, bundle,
                  capacity, tuple(refusals))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--norms-root", required=True, type=Path)
    parser.add_argument("--next-step", required=True, choices=sorted(INCREMENTS))
    args = parser.parse_args(argv)
    result = inspect(args.norms_root, args.next_step)
    print(json.dumps({"status": "METADATA_READY" if result.ok else "REFUSED", **asdict(result)},
                     ensure_ascii=False, indent=2))
    return 0 if result.ok else 2


if __name__ == "__main__":
    sys.exit(main())
