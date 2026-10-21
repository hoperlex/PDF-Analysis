"""Read-only W54 corpus inventory and capacity preflight.

Name the source drop and the promotion workspace separately::

    python scripts/norms/corpus_preflight.py \
        --source-root /path/to/source/.local/norms \
        --promotion-root /path/to/promotion/.local/norms \
        --next-step bundle-export --snapshot <ns_id> \
        --chunking-profile characters-v2:1200

For the first paid repair operation, use ``--next-step repair-sample`` and
``--repair-plan`` with the zero-call plan under the promotion root. This only
checks the frozen plan and host metadata; it never requests a credential.

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
import math
import os
import re
import stat
import sys
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

# Standalone operator invocation from a checkout, like other repository scripts.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from auditmanager.norms.corpus_source import DropSumsInvalid, read_drop_sums  # noqa: E402
from auditmanager.norms.chunking import (  # noqa: E402
    RELIABLE_CHUNKING_PROFILE_VERSION,
    parse_chunking_profile,
)
from auditmanager.norms.embedding.checkpoint import (  # noqa: E402
    CheckpointRefused,
    read_plan,
    require_identity,
)
from auditmanager.norms.embedding.profile import require_snapshot_id  # noqa: E402

MANIFEST_SHA256 = "160fdc7ea261b44298757b3a066982fd167b389fde614fb119c4c1d0d72fbb3b"
SOURCE_SUMS_SHA256 = "eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5"
BASE_DUMP_SHA256 = "e1280373ffd7fa3deaa0716429def1844d7e858e79bae7fbad5ade6d516ff74d"
REPAIR_PLAN_SHA256 = "045f8b636ccae1aa2503015c305575e0a9beb3349055c0aaa365b4474e573365"
BASE_SNAPSHOT = "2026-07-23..2026-08-20+17d.4b74348debf7"
REPAIR_MODEL = "claude-opus-5"
DOCUMENTS = 674
FILES = 31_619
REPAIR_PAGES = 121
GIB = 1024**3
MEMORY_FLOOR = 6 * GIB
DISK_RESERVE = 3 * GIB
# The verified W54 promotion operation used a load-under-8 window on this
# eight-CPU host (W54-CORPUS-PROMOTION-01.md). This is an operator-window
# criterion in addition to W54-PLAN.md §3.9's disk and memory stop rule.
LOAD_LIMIT = 8.0
MAX_BUILD_PLAN_BYTES = 1 << 20  # metadata-only preflight, not a checkpoint payload reader
# W54 §3.9: source-sums has no stated increment, so check the 3 GiB reserve only.
# Base load and restore-verify each have a 3 GiB increment; use that conservative
# increment for the repair sample until its output size is measured. Bundle adds 0.6 GiB.
INCREMENTS = {"source-sums": 0, "base-load": 3 * GIB, "restore-verify": 3 * GIB,
              "repair-sample": 3 * GIB,
              "bundle-export": (6 * GIB + 9) // 10}
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
BLOCK_ID = re.compile(r"blk_[0-9a-f]{32}\Z")


@dataclass(frozen=True)
class Capacity:
    disk_available_bytes: int
    disk_required_bytes: int
    memory_available_bytes: int
    load_average_1: float
    memory_required_bytes: int = MEMORY_FLOOR
    load_limit_exclusive: float = LOAD_LIMIT


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
    repair_plan: str = "not_checked"
    build_snapshot_id: str | None = None
    build_chunking_profile: str | None = None
    qualification: str = (
        "metadata-only, not authorization to operate: run sha256sum -c for the source, "
        "restore-verify for the dump, embedding status/load for the build, and full "
        "bundle verify; bundle-export requires the same snapshot/profile as export; "
        "repair-sample also needs a credential and durable journal; "
        "capacity covers the promotion-root filesystem only; "
        "Docker data, stand capacity and P3 compatibility were not checked"
    )

    @property
    def ok(self) -> bool:
        return not self.refusals


def _is_regular(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def _root_refusal(path: Path, kind: str) -> str | None:
    """Refuse an implicit cwd, missing root, or lexical/symlink escape."""
    if not path.is_absolute():
        return f"{kind}_root_unsafe"
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError):
        return f"{kind}_root_absent"
    if resolved != path or path.is_symlink() or not path.is_dir():
        return f"{kind}_root_unsafe"
    return None


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
    if (root / "corpus-sums").is_symlink():
        return "unsafe_directory", None
    candidates = sorted((root / "corpus-sums").glob("*/SHA256SUMS"))
    if not candidates:
        return "absent", None
    if len(candidates) != 1:
        return "ambiguous", None
    path = candidates[0]
    if path.parent.is_symlink():
        return "unsafe_directory", None
    if not _is_regular(path):
        return "not_regular", None
    try:
        parsed = read_drop_sums(path)  # same parser as repair and bundle export
    except DropSumsInvalid:
        return "malformed", None
    if source_paths is None or set(parsed.entries) != source_paths:
        return "path_set_mismatch", None
    return "listed_unverified", parsed.sha256


def _dump(root: Path) -> tuple[str, str | None]:
    directory = root / "promotion-dumps"
    if directory.is_symlink():
        return "unsafe_directory", None
    candidates = sorted(directory.glob("promotion-*.dump"))
    if not candidates:
        return "absent", None
    latest = candidates[-1]
    if not _is_regular(latest):
        return "not_regular", None
    marker = Path(str(latest) + ".verified")
    sha = Path(str(latest) + ".sha256")
    fingerprint = Path(str(latest) + ".fingerprint")
    if not all(_is_regular(path) for path in (sha, fingerprint)):
        return "missing_dump_metadata", None
    if not fingerprint.stat().st_size:
        return "malformed_dump_metadata", None
    parts = sha.read_text(encoding="ascii", errors="replace").strip().split()
    if len(parts) != 2 or not HEX64.fullmatch(parts[0]) or parts[1] != latest.name:
        return "malformed_dump_metadata", None
    if not _is_regular(marker):
        return "dump_metadata_present_unverified", parts[0]
    if marker.stat().st_size != 0:
        return "malformed_restore_proof", None
    return "restore_marker_present_unrehashed", parts[0]


def _repair_plan(root: Path, path: Path | None, expected_sha256: str) -> str:
    """Check only the small saved zero-call plan, never a corpus or dump payload."""
    if path is None:
        return "absent"
    directory = root / "repairs"
    if not path.is_absolute() or directory.is_symlink() or path.parent != directory:
        return "unsafe_path"
    try:
        if path.is_symlink():
            return "unsafe_path"
        if path.resolve(strict=True) != path or not _is_regular(path):
            return "unsafe_path"
        if path.stat().st_size > 4096:
            return "malformed"
        raw = path.read_bytes()
    except (OSError, RuntimeError):
        return "absent"
    if not HEX64.fullmatch(expected_sha256) or hashlib.sha256(raw).hexdigest() != expected_sha256:
        return "digest_mismatch"
    try:
        plan = json.loads(raw)
        bound = Decimal(plan["max_call_bound_usd"])
    except (ValueError, TypeError, KeyError, InvalidOperation):
        return "malformed"
    if not isinstance(plan, dict):
        return "malformed"
    blocks = plan.get("sample_blocks")
    if (
        plan.get("dry_run") is not True
        or plan.get("model") != REPAIR_MODEL
        or plan.get("base_snapshot") != BASE_SNAPSHOT
        or type(plan.get("pages")) is not int or plan["pages"] != REPAIR_PAGES
        or plan.get("ceiling_usd") != "10"
        or plan.get("spent_usd") != "0"
        or not bound.is_finite() or not 0 < bound < Decimal("10")
        or not isinstance(blocks, list) or len(blocks) != 3
        or any(not isinstance(item, str) or not BLOCK_ID.fullmatch(item) for item in blocks)
        or len(set(blocks)) != 3
    ):
        return "frozen_plan_mismatch"
    return "frozen_plan_present_unverified"


def _build(root: Path, target: tuple[str, str] | None = None) -> str:
    builds = root / "builds"
    if builds.is_symlink():
        return "unsafe_directory"
    candidates = [path for path in builds.glob("*/plan.json") if not path.parent.is_symlink() and _is_regular(path)]
    if not candidates:
        return "absent"
    matched_target = False
    for plan in candidates:
        try:
            if plan.stat().st_size > MAX_BUILD_PLAN_BYTES:
                continue
            parsed = read_plan(plan.parent)
            require_identity(parsed, norms_snapshot_id=parsed.identity.norms_snapshot_id,
                             chunking_profile=parsed.identity.chunking_profile)
        except (CheckpointRefused, OSError, ValueError, TypeError, KeyError, IndexError,
                AttributeError, OverflowError, RecursionError):
            continue
        if parsed.identity.content_key != plan.parent.name:
            continue
        if target is not None:
            if (parsed.identity.norms_snapshot_id, parsed.identity.chunking_profile) != target:
                continue
            matched_target = True
        vectors = plan.parent / "vectors"
        inputs = plan.parent / "inputs"
        if vectors.is_symlink() or inputs.is_symlink():
            continue
        if all(
            _is_regular(inputs / batch.name)
            and _is_regular(vectors / batch.name)
            and _is_regular(vectors / f"{batch.name}.sha256")
            for batch in parsed.batches
        ):
            return "batch_files_present_unverified"
    return "plan_only_or_partial" if target is None or matched_target else "absent"


def _bundle(root: Path, drop_sums_sha: str | None) -> str:
    bundles = root / "bundles"
    if bundles.is_symlink():
        return "unsafe_directory"
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
            or (path / "build").is_symlink()
            or not (path / "build").is_dir()
            or not any(_is_regular(item) for item in (path / "build").glob("chunks-*.jsonl"))
        ):
            continue
        valid.append(path)
    if len(valid) != 1:
        return "absent_or_ambiguous_complete_candidate"
    return "build_declared_payload_present_unverified"


def _capacity(promotion_root: Path, next_step: str) -> Capacity:
    disk = os.statvfs(promotion_root)
    disk_available = disk.f_bavail * disk.f_frsize  # df -B1 Avail semantics
    meminfo = Path("/proc/meminfo").read_text(encoding="ascii")
    match = re.search(r"^MemAvailable:\s+(\d+) kB$", meminfo, re.MULTILINE)
    if match is None:
        raise ValueError("MemAvailable is unavailable")
    memory_available = int(match.group(1)) * 1024  # free -b available, no swap
    return Capacity(disk_available, DISK_RESERVE + INCREMENTS[next_step],
                    memory_available, os.getloadavg()[0])


def inspect(
    source_root: Path,
    next_step: str,
    *,
    promotion_root: Path,
    repair_plan: Path | None = None,
    build_snapshot_id: str | None = None,
    build_chunking_profile: str | None = None,
    expected_repair_plan_sha256: str = REPAIR_PLAN_SHA256,
    expected_source_sums_sha256: str = SOURCE_SUMS_SHA256,
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
    for kind, path in (("source", source_root), ("promotion", promotion_root)):
        issue = _root_refusal(path, kind)
        if issue is not None:
            refusals.append(issue)
    if refusals:
        return Result(next_step, None, None, None, "absent", "absent", "absent", "absent", None,
                      tuple(refusals), build_snapshot_id=build_snapshot_id,
                      build_chunking_profile=build_chunking_profile)
    build_target: tuple[str, str] | None = None
    if next_step == "bundle-export":
        if build_snapshot_id is None or build_chunking_profile is None:
            refusals.append("build_target_required")
        else:
            try:
                require_snapshot_id(build_snapshot_id)
                version, _ = parse_chunking_profile(build_chunking_profile)
            except (TypeError, ValueError):
                refusals.append("build_target_invalid")
            else:
                if version != RELIABLE_CHUNKING_PROFILE_VERSION:
                    refusals.append("build_target_invalid")
                else:
                    build_target = (build_snapshot_id, build_chunking_profile)
    corpus = source_root / "corpus"
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
    source_sums, sums_sha = _sums(source_root, source_paths)
    dump, dump_sha = _dump(promotion_root)
    build = (_build(promotion_root, build_target)
             if next_step != "bundle-export" or build_target is not None else "target_unbound")
    bundle = _bundle(promotion_root, sums_sha)
    plan = (_repair_plan(promotion_root, repair_plan, expected_repair_plan_sha256)
            if next_step == "repair-sample" else "not_checked")
    if next_step != "source-sums":
        if source_sums != "listed_unverified":
            refusals.append("source_sums_unavailable")
        elif sums_sha != expected_source_sums_sha256:
            refusals.append("source_sums_digest_mismatch")
    if next_step == "restore-verify" and dump not in {
        "dump_metadata_present_unverified", "restore_marker_present_unrehashed"
    }:
        refusals.append("dump_metadata_unavailable")
    if next_step == "bundle-export" and dump != "restore_marker_present_unrehashed":
        refusals.append("restore_verified_dump_unavailable")
    if next_step == "bundle-export" and build != "batch_files_present_unverified":
        refusals.append("build_checkpoint_unavailable")
    if next_step == "repair-sample":
        if dump != "restore_marker_present_unrehashed" or dump_sha != BASE_DUMP_SHA256:
            refusals.append("frozen_base_dump_unavailable")
        if plan != "frozen_plan_present_unverified":
            refusals.append("repair_plan_unavailable")
    try:
        capacity = measure(promotion_root, next_step)
    except (OSError, ValueError):
        capacity = None
        refusals.append("capacity_unavailable")
    else:
        if (
            not math.isfinite(capacity.load_average_1)
            or capacity.load_average_1 < 0
            or not math.isfinite(capacity.load_limit_exclusive)
            or capacity.load_limit_exclusive != LOAD_LIMIT
        ):
            capacity = None
            refusals.append("capacity_unavailable")
        else:
            if capacity.disk_available_bytes < capacity.disk_required_bytes:
                refusals.append("disk_floor")
            if capacity.memory_available_bytes < capacity.memory_required_bytes:
                refusals.append("memory_floor")
            if capacity.load_average_1 >= capacity.load_limit_exclusive:
                refusals.append("load_floor")
    return Result(next_step, manifest_sha, docs, files, source_sums, dump, build, bundle,
                  capacity, tuple(refusals), repair_plan=plan,
                  build_snapshot_id=build_snapshot_id,
                  build_chunking_profile=build_chunking_profile)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--promotion-root", required=True, type=Path)
    parser.add_argument("--next-step", required=True, choices=sorted(INCREMENTS))
    parser.add_argument("--snapshot", help="snapshot ID for bundle-export, matching bundle export")
    parser.add_argument("--chunking-profile", help="reliability-aware profile for bundle-export")
    parser.add_argument("--repair-plan", type=Path,
                        help="absolute saved zero-call plan under promotion-root/repairs")
    args = parser.parse_args(argv)
    result = inspect(args.source_root, args.next_step, promotion_root=args.promotion_root,
                     repair_plan=args.repair_plan, build_snapshot_id=args.snapshot,
                     build_chunking_profile=args.chunking_profile)
    print(json.dumps({"status": "METADATA_READY" if result.ok else "REFUSED",
                      "source_root": str(args.source_root), "promotion_root": str(args.promotion_root),
                      **asdict(result)},
                     ensure_ascii=False, indent=2))
    return 0 if result.ok else 2


if __name__ == "__main__":
    sys.exit(main())
