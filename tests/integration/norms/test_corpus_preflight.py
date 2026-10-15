"""Metadata-only corpus preflight never reads normative document bytes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.norms import corpus_preflight as preflight


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


def _measure(_root: Path, step: str, *, disk: int = 20 * preflight.GIB,
             memory: int = 8 * preflight.GIB) -> preflight.Capacity:
    return preflight.Capacity(disk, preflight.DISK_RESERVE + preflight.INCREMENTS[step], memory)


def _inspect(root: Path, manifest_sha: str, step: str = "bundle-export", **kwargs) -> preflight.Result:
    return preflight.inspect(root, step, expected_manifest_sha256=manifest_sha,
                             expected_documents=2, expected_files=3, **kwargs)


def test_preflight_passes_metadata_and_capacity_without_reading_a_document(
    tmp_path: Path, monkeypatch
) -> None:
    manifest_sha = _source(tmp_path)
    sums_sha = _sums(tmp_path)
    _dump(tmp_path)
    (tmp_path / "builds" / "some-content-key").mkdir(parents=True)
    (tmp_path / "builds" / "some-content-key" / "plan.json").write_text('{"batches": [{"index": 0}]}')
    inputs = tmp_path / "builds" / "some-content-key" / "inputs"
    inputs.mkdir()
    (inputs / "batch-00000.jsonl").write_text("{}\n")
    vectors = tmp_path / "builds" / "some-content-key" / "vectors"
    vectors.mkdir()
    (vectors / "batch-00000.jsonl").write_text("{}\n")
    (vectors / "batch-00000.jsonl.sha256").write_text("a" * 64)
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
    (tmp_path / "builds" / "key").mkdir(parents=True)
    (tmp_path / "builds" / "key" / "plan.json").write_text('{"batches": [{"index": 0}]}')
    result = _inspect(tmp_path, manifest_sha, measure=_measure)
    assert result.build_checkpoint == "plan_only_or_partial"
    assert "build_checkpoint_unavailable" in result.refusals
    (tmp_path / "promotion-dumps" / "promotion-20261015T000000Z.dump.verified").unlink()
    result = _inspect(tmp_path, manifest_sha, "restore-verify", measure=_measure)
    assert result.ok
    assert result.restore_verified_dump == "dump_metadata_present_unverified"


def test_preflight_refuses_both_current_host_floor_failures(tmp_path: Path) -> None:
    manifest_sha = _source(tmp_path)
    result = _inspect(tmp_path, manifest_sha, "source-sums", measure=lambda root, step: _measure(
        root, step, disk=preflight.DISK_RESERVE - 1, memory=preflight.MEMORY_FLOOR - 1
    ))
    assert result.refusals == ("disk_floor", "memory_floor")
    assert result.capacity is not None
    assert result.capacity.disk_required_bytes == 3 * preflight.GIB
    assert result.capacity.memory_required_bytes == 6 * preflight.GIB


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


def test_cli_returns_explicit_json_refusal_for_absent_root(tmp_path: Path, capsys) -> None:
    code = preflight.main(["--norms-root", str(tmp_path / "missing"), "--next-step", "base-load"])
    output = json.loads(capsys.readouterr().out)
    assert code == 2
    assert output["status"] == "REFUSED"
    assert output["refusals"] == ["norms_root_absent"]
