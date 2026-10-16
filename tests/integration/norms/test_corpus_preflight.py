"""Metadata-only corpus preflight never reads normative document bytes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.norms import corpus_preflight as preflight
from auditmanager.norms.embedding.checkpoint import BuildIdentity, prepare_plan
from auditmanager.norms.embedding.model import ChunkInput
from auditmanager.norms.embedding.profile import EMBEDDING_PROFILE

SYNTHETIC_SNAPSHOT_ID = "ns_" + "0" * 26
SYNTHETIC_CHUNKING_PROFILE = "characters-v2:1000"


def _source(root: Path) -> str:
    corpus = root / "corpus"
    for name in ("a", "b"):
        directory = corpus / name
        directory.mkdir(parents=True)
        (directory / "document.pdf").write_bytes(b"fake PDF, preflight must not read this")
    raw = json.dumps({"summary": {"documents": 2}, "documents": [{"slug": "a"}, {"slug": "b"}]}).encode()
    (corpus / "MANIFEST.json").write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _sums(root: Path) -> str:
    directory = root / "corpus-sums" / "2026-10-15"
    directory.mkdir(parents=True, exist_ok=True)
    data = "".join(f"{'a' * 64} *./{name}/document.pdf\n" for name in ("a", "b"))
    data += "\n"
    data += f"{'b' * 64}  ./MANIFEST.json\n"
    (directory / "SHA256SUMS").write_text(data)
    return hashlib.sha256(data.encode()).hexdigest()


def _dump(root: Path) -> None:
    directory = root / "promotion-dumps"
    directory.mkdir()
    dump = directory / "promotion-20261015T000000Z.dump"
    dump.write_bytes(b"dump bytes are not read by preflight")
    (directory / (dump.name + ".sha256")).write_text(f"{'a' * 64}  {dump.name}\n")
    (directory / (dump.name + ".fingerprint")).write_text("row fingerprint\n")
    (directory / (dump.name + ".verified")).touch()


def _repair_plan(root: Path) -> tuple[Path, str]:
    directory = root / "repairs"
    directory.mkdir()
    path = directory / "plan-20261016.json"
    raw = json.dumps({
        "dry_run": True, "model": preflight.REPAIR_MODEL,
        "pages": preflight.REPAIR_PAGES, "base_snapshot": preflight.BASE_SNAPSHOT,
        "ceiling_usd": "10", "max_call_bound_usd": "0.224515",
        "sample_blocks": [f"blk_{character * 32}" for character in "abc"],
        "spent_usd": "0",
    }).encode()
    path.write_bytes(raw)
    return path, hashlib.sha256(raw).hexdigest()


def _bundle(root: Path, sums_sha: str) -> None:
    directory = root / "bundles"
    raw = f"{'a' * 64}  manifest.json\n".encode()
    digest = hashlib.sha256(raw).hexdigest()
    candidate = directory / f"undated+2d.abcdefabcdef+{digest}"
    (candidate / "build").mkdir(parents=True)
    (candidate / "build" / "chunks-00000.jsonl").write_text("{}\n")
    (candidate / "SHA256SUMS").write_bytes(raw)
    (candidate / "manifest.json").write_text(json.dumps({
        "content_key": "undated+2d.abcdefabcdef", "build": {"embedding_set_sha256": "c" * 64},
        "drop": {"sums_sha256": sums_sha},
    }))


def _build_checkpoint(root: Path, *, complete: bool = True,
                      embedding_profile: str = EMBEDDING_PROFILE) -> Path:
    (root / "builds").mkdir()
    directory = root / "builds" / "undated+2d.abcdefabcdef"
    identity = BuildIdentity(norms_snapshot_id=SYNTHETIC_SNAPSHOT_ID,
                             content_key=directory.name,
                             chunking_profile=SYNTHETIC_CHUNKING_PROFILE,
                             embedding_profile=embedding_profile)
    plan, created = prepare_plan(
        directory, identity,
        [ChunkInput("source", 0, "text", 0, 0, (4,))],
    )
    assert created and len(plan.batches) == 1
    if complete:
        vectors = directory / "vectors"
        vectors.mkdir()
        (vectors / plan.batches[0].name).write_text("unverified checkpoint\n")
        (vectors / f"{plan.batches[0].name}.sha256").write_text("unverified sidecar\n")
    return directory


def _measure(_root: Path, step: str, *, disk: int = 20 * preflight.GIB,
             memory: int = 8 * preflight.GIB, load: float = 0.0) -> preflight.Capacity:
    return preflight.Capacity(disk, preflight.DISK_RESERVE + preflight.INCREMENTS[step], memory, load)


def _inspect(root: Path, manifest_sha: str, step: str = "bundle-export", **kwargs) -> preflight.Result:
    promotion_root = kwargs.pop("promotion_root", root)
    if step == "bundle-export":
        kwargs.setdefault("build_snapshot_id", SYNTHETIC_SNAPSHOT_ID)
        kwargs.setdefault("build_chunking_profile", SYNTHETIC_CHUNKING_PROFILE)
    expected_sums = kwargs.pop("expected_source_sums_sha256", None)
    if expected_sums is None:
        listings = list((root / "corpus-sums").glob("*/SHA256SUMS"))
        expected_sums = (hashlib.sha256(listings[0].read_bytes()).hexdigest()
                         if len(listings) == 1 else preflight.SOURCE_SUMS_SHA256)
    return preflight.inspect(root, step, expected_manifest_sha256=manifest_sha,
                             expected_documents=2, expected_files=3,
                             expected_source_sums_sha256=expected_sums,
                             promotion_root=promotion_root, **kwargs)


def test_preflight_passes_metadata_and_capacity_without_reading_a_document(
    tmp_path: Path, monkeypatch
) -> None:
    manifest_sha = _source(tmp_path)
    sums_sha = _sums(tmp_path)
    _dump(tmp_path)
    _build_checkpoint(tmp_path)
    _bundle(tmp_path, sums_sha)
    read_bytes = Path.read_bytes

    def refuse_pdf(self: Path) -> bytes:
        if self.suffix == ".pdf" or self.suffix == ".dump":
            raise AssertionError("preflight read a large artifact")
        return read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", refuse_pdf)
    result = _inspect(tmp_path, manifest_sha, measure=_measure)
    assert result.ok
    assert result.document_directories == 2 and result.regular_files == 3
    assert result.bundle_candidate == "build_declared_payload_present_unverified"
    assert "not authorization" in result.qualification


def test_empty_bundle_build_is_only_an_incomplete_candidate(tmp_path: Path) -> None:
    manifest_sha = _source(tmp_path)
    sums_sha = _sums(tmp_path)
    _bundle(tmp_path, sums_sha)
    next((tmp_path / "bundles").glob("*/build/chunks-*.jsonl")).unlink()
    result = _inspect(tmp_path, manifest_sha, "base-load", measure=_measure)
    assert result.bundle_candidate == "absent_or_ambiguous_complete_candidate"


def test_preflight_refuses_missing_prerequisites_and_tampered_manifest(tmp_path: Path) -> None:
    manifest_sha = _source(tmp_path)
    result = _inspect(tmp_path, manifest_sha, measure=_measure)
    assert set(result.refusals) == {
        "source_sums_unavailable", "restore_verified_dump_unavailable", "build_checkpoint_unavailable"
    }
    (tmp_path / "corpus" / "MANIFEST.json").write_text("{}")
    result = _inspect(tmp_path, manifest_sha, measure=_measure)
    assert "source_manifest_digest" in result.refusals
    assert "source_manifest_malformed" in result.refusals


def test_plan_alone_is_not_a_build_checkpoint_and_verify_dump_is_not_circular(tmp_path: Path) -> None:
    manifest_sha = _source(tmp_path)
    _sums(tmp_path)
    _dump(tmp_path)
    _build_checkpoint(tmp_path, complete=False)
    result = _inspect(tmp_path, manifest_sha, measure=_measure)
    assert result.build_checkpoint == "plan_only_or_partial"
    assert "build_checkpoint_unavailable" in result.refusals
    (tmp_path / "promotion-dumps" / "promotion-20261015T000000Z.dump.verified").unlink()
    result = _inspect(tmp_path, manifest_sha, "restore-verify", measure=_measure)
    assert result.ok
    assert result.restore_verified_dump == "dump_metadata_present_unverified"


def test_bundle_preflight_requires_an_explicit_snapshot_and_profile(tmp_path: Path) -> None:
    manifest_sha = _source(tmp_path)
    _sums(tmp_path)
    _dump(tmp_path)
    _build_checkpoint(tmp_path)
    result = _inspect(tmp_path, manifest_sha, build_snapshot_id=None,
                      build_chunking_profile=None, measure=_measure)
    assert result.build_checkpoint == "target_unbound"
    assert "build_target_required" in result.refusals
    assert "build_checkpoint_unavailable" in result.refusals
    assert not result.ok


@pytest.mark.parametrize("snapshot, profile", [
    ("ns_" + "1" * 26, SYNTHETIC_CHUNKING_PROFILE),
    (SYNTHETIC_SNAPSHOT_ID, "characters-v2:1200"),
])
def test_bundle_preflight_does_not_use_another_snapshots_or_profiles_checkpoint(
    tmp_path: Path, snapshot: str, profile: str
) -> None:
    manifest_sha = _source(tmp_path)
    _sums(tmp_path)
    _dump(tmp_path)
    _build_checkpoint(tmp_path)
    result = _inspect(tmp_path, manifest_sha, build_snapshot_id=snapshot,
                      build_chunking_profile=profile, measure=_measure)
    assert result.build_checkpoint == "absent"
    assert result.refusals == ("build_checkpoint_unavailable",)
    assert result.build_snapshot_id == snapshot
    assert result.build_chunking_profile == profile


@pytest.mark.parametrize("snapshot, profile", [
    ("ns_invalid", SYNTHETIC_CHUNKING_PROFILE),
    (SYNTHETIC_SNAPSHOT_ID, "characters-v1:1000"),
])
def test_bundle_preflight_refuses_an_invalid_or_undesignatable_target(
    tmp_path: Path, snapshot: str, profile: str
) -> None:
    manifest_sha = _source(tmp_path)
    _sums(tmp_path)
    _dump(tmp_path)
    _build_checkpoint(tmp_path)
    result = _inspect(tmp_path, manifest_sha, build_snapshot_id=snapshot,
                      build_chunking_profile=profile, measure=_measure)
    assert result.build_checkpoint == "target_unbound"
    assert "build_target_invalid" in result.refusals
    assert "build_checkpoint_unavailable" in result.refusals


def test_cli_passes_the_selected_build_target_to_the_read_only_preflight(
    tmp_path: Path, capsys
) -> None:
    _source(tmp_path)
    _sums(tmp_path)
    _dump(tmp_path)
    _build_checkpoint(tmp_path)
    code = preflight.main([
        "--source-root", str(tmp_path), "--promotion-root", str(tmp_path),
        "--next-step", "bundle-export", "--snapshot", SYNTHETIC_SNAPSHOT_ID,
        "--chunking-profile", SYNTHETIC_CHUNKING_PROFILE,
    ])
    output = json.loads(capsys.readouterr().out)
    assert code == 2  # synthetic source differs from the frozen real manifest/sums
    assert output["build_snapshot_id"] == SYNTHETIC_SNAPSHOT_ID
    assert output["build_chunking_profile"] == SYNTHETIC_CHUNKING_PROFILE
    assert output["build_checkpoint"] == "batch_files_present_unverified"
    assert "build_target_required" not in output["refusals"]


@pytest.mark.parametrize("change", ["fabricated", "wrong_directory", "wrong_profile", "oversize"])
def test_bundle_preflight_refuses_batch_files_from_an_invalid_or_misbound_plan(
    tmp_path: Path, change: str
) -> None:
    manifest_sha = _source(tmp_path)
    _sums(tmp_path)
    _dump(tmp_path)
    directory = _build_checkpoint(tmp_path, embedding_profile=(
        "another-profile" if change == "wrong_profile" else EMBEDDING_PROFILE
    ))
    if change == "fabricated":
        (directory / "plan.json").write_text('{"batches": [{"index": 0}]}')
    elif change == "wrong_directory":
        directory.rename(directory.with_name("another-content-key"))
    elif change == "oversize":
        (directory / "plan.json").write_bytes(b"x" * (preflight.MAX_BUILD_PLAN_BYTES + 1))

    result = _inspect(tmp_path, manifest_sha, measure=_measure)
    assert result.build_checkpoint == "absent"
    assert "build_checkpoint_unavailable" in result.refusals


def test_preflight_refuses_both_current_host_floor_failures(tmp_path: Path) -> None:
    manifest_sha = _source(tmp_path)
    result = _inspect(tmp_path, manifest_sha, "source-sums", measure=lambda root, step: _measure(
        root, step, disk=preflight.DISK_RESERVE - 1, memory=preflight.MEMORY_FLOOR - 1
    ))
    assert result.refusals == ("disk_floor", "memory_floor")
    assert result.capacity is not None
    assert result.capacity.disk_required_bytes == 3 * preflight.GIB
    assert result.capacity.memory_required_bytes == 6 * preflight.GIB


@pytest.mark.parametrize("load, refused", [(7.999, False), (8.0, True), (8.001, True)])
def test_preflight_requires_the_recorded_w54_cpu_window(
    tmp_path: Path, load: float, refused: bool
) -> None:
    manifest_sha = _source(tmp_path)
    result = _inspect(tmp_path, manifest_sha, "source-sums",
                      measure=lambda root, step: _measure(root, step, load=load))
    assert ("load_floor" in result.refusals) is refused
    assert result.capacity is not None
    assert result.capacity.load_average_1 == load
    assert result.capacity.load_limit_exclusive == 8.0
    assert result.ok is not refused


@pytest.mark.parametrize("load", [float("nan"), float("inf"), float("-inf"), -0.01])
def test_preflight_refuses_an_invalid_cpu_measurement(tmp_path: Path, load: float) -> None:
    manifest_sha = _source(tmp_path)
    result = _inspect(tmp_path, manifest_sha, "source-sums",
                      measure=lambda root, step: _measure(root, step, load=load))
    assert result.refusals == ("capacity_unavailable",)
    assert result.capacity is None
    assert not result.ok


def test_host_capacity_samples_one_minute_load_and_refuses_unavailable_load(
    tmp_path: Path, monkeypatch
) -> None:
    manifest_sha = _source(tmp_path)
    original_read_text = Path.read_text

    def stable_memory(path: Path, *args, **kwargs) -> str:
        if path == Path("/proc/meminfo"):
            return "MemAvailable: 8388608 kB\n"
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", stable_memory)
    monkeypatch.setattr(preflight.os, "getloadavg", lambda: (8.25, 0.0, 0.0))
    result = _inspect(tmp_path, manifest_sha, "source-sums")
    assert result.capacity is not None and result.capacity.load_average_1 == 8.25
    assert result.refusals == ("load_floor",)

    def unavailable() -> tuple[float, float, float]:
        raise OSError("load average unavailable")

    monkeypatch.setattr(preflight.os, "getloadavg", unavailable)
    result = _inspect(tmp_path, manifest_sha, "source-sums")
    assert result.refusals == ("capacity_unavailable",)
    assert result.capacity is None


def test_preflight_refuses_incomplete_or_ambiguous_sums(tmp_path: Path) -> None:
    manifest_sha = _source(tmp_path)
    _sums(tmp_path)
    sums = tmp_path / "corpus-sums" / "2026-10-15" / "SHA256SUMS"
    sums.write_text(f"{'a' * 64}  ./a/document.pdf\n" * 3)
    result = _inspect(tmp_path, manifest_sha, "base-load", measure=_measure)
    assert result.source_sums == "malformed"
    assert "source_sums_unavailable" in result.refusals
    sums.write_text("".join(f"{'a' * 64}  ./alien-{n}.pdf\n" for n in range(3)))
    assert _inspect(tmp_path, manifest_sha, "base-load", measure=_measure).source_sums == "path_set_mismatch"
    _sums(tmp_path)
    another = tmp_path / "corpus-sums" / "2026-10-16"
    another.mkdir()
    (another / "SHA256SUMS").write_bytes(sums.read_bytes())
    assert _inspect(tmp_path, manifest_sha, "base-load", measure=_measure).source_sums == "ambiguous"


@pytest.mark.parametrize("step", ["base-load", "restore-verify", "repair-sample", "bundle-export"])
def test_post_checksum_steps_refuse_a_changed_listing_with_the_same_paths(
    tmp_path: Path, step: str
) -> None:
    manifest_sha = _source(tmp_path)
    pinned_sums = _sums(tmp_path)
    _dump(tmp_path)
    sums = tmp_path / "corpus-sums" / "2026-10-15" / "SHA256SUMS"
    sums.write_text(sums.read_text().replace("a" * 64, "c" * 64))
    assert hashlib.sha256(sums.read_bytes()).hexdigest() != pinned_sums

    result = _inspect(tmp_path, manifest_sha, step,
                      expected_source_sums_sha256=pinned_sums, measure=_measure)
    assert result.source_sums == "listed_unverified"
    assert "source_sums_digest_mismatch" in result.refusals
    assert not result.ok

    preparatory = _inspect(tmp_path, manifest_sha, "source-sums",
                           expected_source_sums_sha256=pinned_sums, measure=_measure)
    assert "source_sums_digest_mismatch" not in preparatory.refusals


def test_cli_returns_explicit_json_refusal_for_absent_root(tmp_path: Path, capsys) -> None:
    code = preflight.main(["--source-root", str(tmp_path / "missing"),
                           "--promotion-root", str(tmp_path), "--next-step", "base-load"])
    output = json.loads(capsys.readouterr().out)
    assert code == 2
    assert output["status"] == "REFUSED"
    assert output["refusals"] == ["source_root_absent"]


def test_split_roots_read_the_base_dump_without_copying_payload(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "source"
    promotion = tmp_path / "promotion"
    source.mkdir()
    promotion.mkdir()
    manifest_sha = _source(source)
    _sums(source)
    _dump(promotion)
    read_bytes = Path.read_bytes

    def refuse_payload(self: Path) -> bytes:
        if self.suffix in {".pdf", ".dump"}:
            raise AssertionError("preflight read corpus or dump payload")
        return read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", refuse_payload)
    measured: list[Path] = []

    def measure(root: Path, step: str) -> preflight.Capacity:
        measured.append(root)
        return _measure(root, step)

    result = _inspect(source, manifest_sha, "bundle-export", promotion_root=promotion, measure=measure)
    assert result.restore_verified_dump == "restore_marker_present_unrehashed"
    assert result.source_sums == "listed_unverified"
    assert result.refusals == ("build_checkpoint_unavailable",)
    assert measured == [promotion]


def test_relative_or_symlink_roots_and_child_directories_fail_closed(tmp_path: Path) -> None:
    source = tmp_path / "source"
    promotion = tmp_path / "promotion"
    source.mkdir()
    promotion.mkdir()
    manifest_sha = _source(source)
    _sums(source)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "promotion-dumps").mkdir()
    (promotion / "promotion-dumps").symlink_to(outside / "promotion-dumps", target_is_directory=True)
    result = _inspect(source, manifest_sha, promotion_root=promotion, measure=_measure)
    assert result.restore_verified_dump == "unsafe_directory"
    assert "restore_verified_dump_unavailable" in result.refusals

    alias = tmp_path / "alias"
    alias.symlink_to(source, target_is_directory=True)
    result = _inspect(alias, manifest_sha, promotion_root=promotion, measure=_measure)
    assert result.refusals == ("source_root_unsafe",)
    result = _inspect(Path("relative/source"), manifest_sha, promotion_root=promotion, measure=_measure)
    assert result.refusals == ("source_root_unsafe",)
    promotion_alias = tmp_path / "promotion-alias"
    promotion_alias.symlink_to(promotion, target_is_directory=True)
    result = _inspect(source, manifest_sha, promotion_root=promotion_alias, measure=_measure)
    assert result.refusals == ("promotion_root_unsafe",)


def test_repair_sample_binds_pinned_plan_sums_and_restore_marker_without_payload_reads(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "source"
    promotion = tmp_path / "promotion"
    source.mkdir()
    promotion.mkdir()
    manifest_sha = _source(source)
    sums_sha = _sums(source)
    _dump(promotion)
    plan, plan_sha = _repair_plan(promotion)
    monkeypatch.setattr(preflight, "SOURCE_SUMS_SHA256", sums_sha)
    monkeypatch.setattr(preflight, "BASE_DUMP_SHA256", "a" * 64)
    read_bytes = Path.read_bytes

    def refuse_payload(self: Path) -> bytes:
        if self.suffix in {".pdf", ".dump"}:
            raise AssertionError("repair preflight read a corpus or dump payload")
        return read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", refuse_payload)
    result = _inspect(source, manifest_sha, "repair-sample", promotion_root=promotion,
                      repair_plan=plan, expected_repair_plan_sha256=plan_sha, measure=_measure)
    assert result.ok
    assert result.repair_plan == "frozen_plan_present_unverified"
    assert result.restore_verified_dump == "restore_marker_present_unrehashed"
    assert result.capacity is not None and result.capacity.disk_required_bytes == 6 * preflight.GIB
    assert "not authorization" in result.qualification


def test_repair_sample_refuses_missing_changed_or_wrong_model_plan(tmp_path: Path, monkeypatch) -> None:
    manifest_sha = _source(tmp_path)
    sums_sha = _sums(tmp_path)
    _dump(tmp_path)
    plan, plan_sha = _repair_plan(tmp_path)
    monkeypatch.setattr(preflight, "SOURCE_SUMS_SHA256", sums_sha)
    monkeypatch.setattr(preflight, "BASE_DUMP_SHA256", "a" * 64)

    def inspect_plan(*, expected: str = plan_sha, path: Path | None = plan):
        return _inspect(tmp_path, manifest_sha, "repair-sample", repair_plan=path,
                        expected_repair_plan_sha256=expected, measure=_measure)

    assert inspect_plan(path=None).refusals == ("repair_plan_unavailable",)
    raw = json.loads(plan.read_text())
    raw["model"] = "claude-sonnet-5"
    plan.write_text(json.dumps(raw))
    assert inspect_plan().repair_plan == "digest_mismatch"
    changed_sha = hashlib.sha256(plan.read_bytes()).hexdigest()
    result = inspect_plan(expected=changed_sha)
    assert result.repair_plan == "frozen_plan_mismatch"
    assert "repair_plan_unavailable" in result.refusals
    plan.unlink()
    plan.symlink_to(tmp_path / "outside.json")
    assert inspect_plan().repair_plan == "unsafe_path"


def test_repair_sample_refuses_wrong_sums_and_dump_digest(tmp_path: Path) -> None:
    manifest_sha = _source(tmp_path)
    _sums(tmp_path)
    _dump(tmp_path)
    plan, plan_sha = _repair_plan(tmp_path)
    result = _inspect(tmp_path, manifest_sha, "repair-sample", repair_plan=plan,
                      expected_repair_plan_sha256=plan_sha,
                      expected_source_sums_sha256=preflight.SOURCE_SUMS_SHA256,
                      measure=_measure)
    assert "source_sums_digest_mismatch" in result.refusals
    assert "frozen_base_dump_unavailable" in result.refusals
    (tmp_path / "promotion-dumps" / "promotion-20261015T000000Z.dump.verified").unlink()
    result = _inspect(tmp_path, manifest_sha, "repair-sample", repair_plan=plan,
                      expected_repair_plan_sha256=plan_sha, measure=_measure)
    assert "frozen_base_dump_unavailable" in result.refusals
