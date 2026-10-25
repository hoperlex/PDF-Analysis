"""`AR-V3-BETA-PACK-INSTALL-01`: the sealed reviewed-pack manifest and its operator CLI.

Container-free. The loader is pure apart from reading one file; the CLI's database step is an
injected fake here, and its real counterpart is `tests/integration/db/test_ar_v3_pack_seal.py`.

Every refusal the task names is its own case, and each asserts the stable reason token, so a
guard that were deleted or reordered into another guard's reason turns exactly one case red.
"""

from __future__ import annotations

import copy
import io
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Iterator

import pytest

from auditmanager.analysis.public import resolve_beta_v3_profile
from auditmanager.norms.public import PromotionRefused, SetIdentity, VerifiedSetReference
from auditmanager.runs import v3_pack_cli
from auditmanager.runs.public import (
    PackManifestRefused,
    ReviewAttestation,
    TrustedPackRegistry,
    load_trusted_pack_registry,
    parse_manifest,
    seal_manifest,
)
from auditmanager.runs.v3_group import SCOPES, ReviewedScope, TrustedPack
from auditmanager.runs.v3_pack_manifest import MAX_MANIFEST_BYTES, load_manifest
from auditmanager.shared.identity import NormRetrievalSetId

ROOT = Path(__file__).resolve().parents[3]
PROFILE = resolve_beta_v3_profile("ap_01M5M28ZCDD8VPSP1BTAEW92YE", "pb_01M5M28ZCDVCR37BX1884JGSPM")
CHUNKING = "characters-v2:1200"
CONTENT_KEY = "ar-v3-beta-synthetic"
REVIEW = ReviewAttestation(
    reviewer="Test Reviewer", capacity="expert", reviewed_at="2026-10-26",
    decision_ref="TEST-RULING-1", scope_statement="six synthetic scopes, test only",
)


def _pack(**changes: Any) -> TrustedPack:
    scopes = tuple(
        ReviewedScope(
            scope_id=scope_id,
            identity=SetIdentity(
                map_sha256=f"{index:x}" * 64, snapshot_id=PROFILE.snapshot_id,
                reviewed_content_key=CONTENT_KEY,
                embedding_build=f"bge-m3-dense-v1:{CHUNKING}",
            ),
            chunking_profile=CHUNKING,
            set_id=str(NormRetrievalSetId.new()), set_sha256=f"{index + 8:x}" * 64,
        )
        for index, scope_id in enumerate(SCOPES, 1)
    )
    fields: dict[str, Any] = {
        "analysis_profile_id": str(PROFILE.analysis_profile_id),
        "prompt_bundle_id": str(PROFILE.prompt_bundle_id), "scopes": scopes,
    }
    fields.update(changes)
    return TrustedPack(**fields)


def _document(pack: TrustedPack | None = None) -> dict[str, Any]:
    return json.loads(seal_manifest(pack or _pack(), REVIEW))


def _dump(document: Any) -> bytes:
    return json.dumps(document, ensure_ascii=False).encode("utf-8")


def _resigned(document: dict[str, Any]) -> dict[str, Any]:
    """Recompute the digest over the (mutated) scopes so the case reaches the guard after it."""
    pack = TrustedPack(
        document["analysis_profile_id"], document["prompt_bundle_id"],
        tuple(
            ReviewedScope(
                scope_id=s["scope_id"],
                identity=SetIdentity(
                    s["map_sha256"], s["snapshot_id"], s["reviewed_content_key"],
                    s["embedding_build"], s["builder_version"],
                ),
                chunking_profile=s["chunking_profile"], set_id=s["set_id"],
                set_sha256=s["set_sha256"],
            )
            for s in document["scopes"]
        ),
    )
    return {**document, "pack_sha256": pack.sha256}


def _refusal(data: bytes) -> PackManifestRefused:
    with pytest.raises(PackManifestRefused) as caught:
        parse_manifest(data)
    return caught.value


# --- the sealed form -------------------------------------------------------------------------


def test_a_sealed_pack_round_trips_to_the_same_pack_and_review() -> None:
    pack = _pack()
    sealed = seal_manifest(pack, REVIEW)
    parsed = parse_manifest(sealed)
    assert parsed.pack == pack
    assert parsed.review == REVIEW
    assert json.loads(sealed)["pack_sha256"] == pack.sha256
    assert parsed.registry.installed == (pack,)
    assert parsed.registry.registry_version == TrustedPackRegistry.empty().registry_version
    assert parsed.registry.select_beta() == pack


def test_sealing_is_canonical_and_deterministic() -> None:
    pack = _pack()
    sealed = seal_manifest(pack, REVIEW)
    assert sealed == seal_manifest(pack, REVIEW)
    canonical = json.dumps(
        json.loads(sealed), sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    assert sealed == canonical
    assert not sealed.endswith(b"\n")


def test_non_ascii_review_text_is_kept_as_utf8() -> None:
    review = ReviewAttestation("Иванов И. И.", "expert", "2026-10-26", "Р-1", "шесть карт")
    sealed = seal_manifest(_pack(), review)
    assert "Иванов И. И.".encode("utf-8") in sealed
    assert parse_manifest(sealed).review == review


def test_the_loader_validates_meaning_not_byte_form() -> None:
    pack = _pack()
    reordered = dict(reversed(list(_document(pack).items())))
    parsed = parse_manifest(json.dumps(reordered, indent=4).encode("utf-8") + b"\n")
    assert (parsed.pack, parsed.review) == (pack, REVIEW)


def test_sealing_refuses_what_the_loader_would_refuse() -> None:
    duplicate = _pack()
    scopes = list(duplicate.scopes)
    scopes[1] = ReviewedScope(
        scopes[1].scope_id, scopes[1].identity, scopes[1].chunking_profile,
        scopes[0].set_id, scopes[1].set_sha256,
    )
    with pytest.raises(PackManifestRefused) as same_set:
        seal_manifest(_pack(scopes=tuple(scopes)), REVIEW)
    assert same_set.value.reason == "scope_set_duplicate"
    with pytest.raises(PackManifestRefused) as unknown:
        seal_manifest(_pack(analysis_profile_id="ap_01M5M28ZCDD8VPSP1BTAEW92YF"), REVIEW)
    assert unknown.value.reason == "pack_refused"
    with pytest.raises(PackManifestRefused) as blank:
        seal_manifest(_pack(), ReviewAttestation("  ", "expert", "2026-10-26", "r", "s"))
    assert blank.value.reason == "manifest_value"


# --- the environment ---------------------------------------------------------------------------


@pytest.mark.parametrize("unset", [None, "", "   "])
def test_no_variable_is_the_empty_registry(unset: str | None) -> None:
    registry = load_trusted_pack_registry(unset)
    assert registry == TrustedPackRegistry.empty()
    assert registry.select_beta() is None


def test_a_good_file_installs_exactly_one_pack(tmp_path: Path) -> None:
    pack = _pack()
    path = tmp_path / "pack.json"
    path.write_bytes(seal_manifest(pack, REVIEW))
    registry = load_trusted_pack_registry(str(path))
    assert registry.installed == (pack,)
    assert load_trusted_pack_registry(f"  {path}  ").installed == (pack,)


# --- every refusal, as its own case -----------------------------------------------------------


def _set(path: tuple[Any, ...], value: Any) -> Callable[[dict[str, Any]], None]:
    def mutate(document: dict[str, Any]) -> None:
        target: Any = document
        for step in path[:-1]:
            target = target[step]
        target[path[-1]] = value
    return mutate


def _drop(*path: Any) -> Callable[[dict[str, Any]], None]:
    def mutate(document: dict[str, Any]) -> None:
        target: Any = document
        for step in path[:-1]:
            target = target[step]
        del target[path[-1]]
    return mutate


def _swap_first_two(document: dict[str, Any]) -> None:
    document["scopes"][0], document["scopes"][1] = document["scopes"][1], document["scopes"][0]


def _all_snapshots(value: str) -> Callable[[dict[str, Any]], None]:
    def mutate(document: dict[str, Any]) -> None:
        for scope in document["scopes"]:
            scope["snapshot_id"] = value
    return mutate


def _every_field_blank_but(name: str) -> Callable[[dict[str, Any]], None]:
    return _set(("review", name), "   ")


#: (id, mutation, whether to recompute the digest afterwards, reason, detail fragment)
REFUSALS: list[tuple[str, Callable[[dict[str, Any]], None], bool, str, str]] = [
    ("root_unknown_key", _set(("extra",), 1), False, "manifest_keys", "unknown=[extra]"),
    ("root_missing_key", _drop("prompt_bundle_id"), False, "manifest_keys", "missing=[prompt_bundle_id]"),
    ("review_unknown_key", _set(("review", "approved"), True), False, "manifest_keys", "review"),
    ("review_missing_key", _drop("review", "decision_ref"), False, "manifest_keys", "missing=[decision_ref]"),
    ("scope_unknown_key", _set(("scopes", 2, "note"), "x"), False, "manifest_keys", "scopes[2]"),
    ("scope_missing_key", _drop("scopes", 3, "set_sha256"), False, "manifest_keys", "missing=[set_sha256]"),
    ("scope_not_object", _set(("scopes", 0), "F1"), False, "manifest_keys", "scopes[0]"),
    ("wrong_format", _set(("format",), "ar-v3-beta-reviewed-pack-manifest/2"), False, "manifest_format", ""),
    ("format_not_a_string", _set(("format",), 1), False, "manifest_format", ""),
    ("profile_id_blank", _set(("analysis_profile_id",), " "), False, "manifest_value", "analysis_profile_id"),
    ("bundle_id_number", _set(("prompt_bundle_id",), 7), False, "manifest_value", "prompt_bundle_id"),
    ("reviewer_empty", _set(("review", "reviewer"), ""), False, "manifest_value", "review.reviewer"),
    ("capacity_blank", _every_field_blank_but("capacity"), False, "manifest_value", "review.capacity"),
    ("decision_ref_empty", _set(("review", "decision_ref"), ""), False, "manifest_value", "review.decision_ref"),
    ("scope_statement_empty", _set(("review", "scope_statement"), ""), False, "manifest_value", "review.scope_statement"),
    ("reviewed_at_empty", _set(("review", "reviewed_at"), ""), False, "manifest_value", "review.reviewed_at"),
    ("reviewed_at_not_a_date", _set(("review", "reviewed_at"), "2026-13-01"), False, "manifest_value", "reviewed_at"),
    ("reviewed_at_wrong_shape", _set(("review", "reviewed_at"), "26-10-2026"), False, "manifest_value", "reviewed_at"),
    ("reviewed_at_compact", _set(("review", "reviewed_at"), "20261026"), False, "manifest_value", "reviewed_at"),
    ("reviewed_at_number", _set(("review", "reviewed_at"), 20261026), False, "manifest_value", "review.reviewed_at"),
    ("pack_sha_uppercase", _set(("pack_sha256",), "A" * 64), False, "manifest_value", "pack_sha256"),
    ("pack_sha_short", _set(("pack_sha256",), "a" * 63), False, "manifest_value", "pack_sha256"),
    ("map_sha_uppercase", _set(("scopes", 0, "map_sha256"), "A" * 64), False, "manifest_value", "map_sha256"),
    ("set_sha_short", _set(("scopes", 4, "set_sha256"), "1" * 40), False, "manifest_value", "set_sha256"),
    ("set_id_malformed", _set(("scopes", 5, "set_id"), "nrs_not_an_id"), False, "manifest_value", "set_id"),
    ("set_id_other_entity", _set(("scopes", 5, "set_id"), "ver_01M25P3TH08VVTTGJRXYBZZ7RP"), False, "manifest_value", "set_id"),
    ("scope_text_empty", _set(("scopes", 1, "reviewed_content_key"), ""), False, "manifest_value", "reviewed_content_key"),
    ("embedding_build_mismatch", _set(("scopes", 0, "embedding_build"), "bge-m3-dense-v1:characters-v2:900"), False, "manifest_value", "embedding_build"),
    ("five_scopes", lambda d: d["scopes"].pop(), False, "scope_count", ""),
    ("seven_scopes", lambda d: d["scopes"].append(copy.deepcopy(d["scopes"][0])), False, "scope_count", ""),
    ("scopes_not_a_list", _set(("scopes",), {"F1": 1}), False, "scope_count", ""),
    ("scope_ids_reordered", _swap_first_two, False, "scope_order", "F1,F2"),
    ("scope_ids_duplicated", _set(("scopes", 5, "scope_id"), "F1"), False, "scope_id_duplicate", ""),
    ("scope_id_unknown", _set(("scopes", 5, "scope_id"), "S3"), False, "scope_order", ""),
    ("map_sha_duplicated", lambda d: d["scopes"][1].update(map_sha256=d["scopes"][0]["map_sha256"]), False, "scope_map_duplicate", ""),
    ("set_id_duplicated", lambda d: d["scopes"][1].update(set_id=d["scopes"][0]["set_id"]), False, "scope_set_duplicate", ""),
    ("digest_tampered_scope", _set(("scopes", 2, "set_sha256"), "e" * 64), False, "pack_digest_mismatch", ""),
    ("digest_tampered_profile", _set(("prompt_bundle_id",), "pb_01M5M28ZCDVCR37BX1884JGSPN"), False, "pack_digest_mismatch", ""),
    ("digest_forged_other_value", _set(("pack_sha256",), "0" * 64), False, "pack_digest_mismatch", ""),
    ("profile_unresolved", _set(("analysis_profile_id",), "ap_01M5M28ZCDD8VPSP1BTAEW92YF"), True, "pack_refused", "required_norm_unavailable (analysis_profile)"),
    ("bundle_unresolved", _set(("prompt_bundle_id",), "pb_01M5M28ZCDVCR37BX1884JGSPN"), True, "pack_refused", "analysis_profile"),
    ("snapshot_differs_from_profile", _all_snapshots("ns_01M59N8QNBVN91ACA2HCE6VE75"), True, "pack_refused", "required_norm_unavailable"),
]


@pytest.mark.parametrize(
    ("mutate", "resign", "reason", "fragment"),
    [pytest.param(m, r, why, frag, id=case) for case, m, r, why, frag in REFUSALS],
)
def test_each_refusal_has_its_own_reason(
    mutate: Callable[[dict[str, Any]], None], resign: bool, reason: str, fragment: str,
) -> None:
    document = _document()
    mutate(document)
    if resign:
        document = _resigned(document)
    refused = _refusal(_dump(document))
    assert refused.reason == reason
    assert fragment in refused.detail


@pytest.mark.parametrize(
    ("data", "reason"),
    [
        pytest.param(b"", "manifest_not_json", id="empty"),
        pytest.param(b"not json", "manifest_not_json", id="garbage"),
        pytest.param(b"\xff\xfe\x00{", "manifest_not_json", id="not_utf8"),
        pytest.param(b"\xef\xbb\xbf{}", "manifest_not_json", id="byte_order_mark"),
        pytest.param(b'{"format":NaN}', "manifest_not_json", id="non_finite_number"),
        pytest.param(b'{"format":"a","format":"b"}', "manifest_not_json", id="duplicate_key"),
        pytest.param(b"[" * 5000, "manifest_not_json", id="nesting_bomb"),
        pytest.param(b"[]", "manifest_keys", id="array"),
        pytest.param(b"null", "manifest_keys", id="null"),
        pytest.param(b"{}", "manifest_keys", id="empty_object"),
    ],
)
def test_bytes_that_are_not_a_manifest_object_are_refused(data: bytes, reason: str) -> None:
    assert _refusal(data).reason == reason


def test_a_duplicate_key_is_never_resolved_in_the_last_ones_favour() -> None:
    sealed = seal_manifest(_pack(), REVIEW).decode("utf-8")
    duplicated = sealed.replace('"format":', '"format":"x","format":', 1)
    assert _refusal(duplicated.encode("utf-8")).reason == "manifest_not_json"


def test_an_oversized_manifest_is_refused_before_it_is_parsed() -> None:
    pack = _pack()
    sealed = seal_manifest(pack, REVIEW)
    padding = b" " * (MAX_MANIFEST_BYTES + 1 - len(sealed))
    assert _refusal(sealed + padding).reason == "manifest_too_large"
    exactly = sealed + padding[:-1]
    assert len(exactly) == MAX_MANIFEST_BYTES
    assert parse_manifest(exactly).pack == pack


def test_refusal_details_never_echo_manifest_values() -> None:
    document = _document()
    document["review"]["reviewer"] = ""
    document["scopes"][0]["set_id"] = "SECRET-LOOKING-VALUE"
    refused = _refusal(_dump(document))
    assert "SECRET-LOOKING-VALUE" not in str(refused)


# --- the file --------------------------------------------------------------------------------


def _reason(path: Path | str) -> str:
    with pytest.raises(PackManifestRefused) as caught:
        load_trusted_pack_registry(str(path))
    return caught.value.reason


def test_a_missing_file_refuses(tmp_path: Path) -> None:
    assert _reason(tmp_path / "absent.json") == "manifest_missing"


def test_a_directory_refuses(tmp_path: Path) -> None:
    assert _reason(tmp_path) == "manifest_not_regular_file"


def test_a_symlink_to_a_valid_manifest_refuses(tmp_path: Path) -> None:
    real = tmp_path / "real.json"
    real.write_bytes(seal_manifest(_pack(), REVIEW))
    link = tmp_path / "link.json"
    link.symlink_to(real)
    assert load_trusted_pack_registry(str(real)).installed
    assert _reason(link) == "manifest_not_regular_file"


def test_a_symlinked_directory_on_the_way_is_a_mount_not_a_refusal(tmp_path: Path) -> None:
    (tmp_path / "mounted").mkdir()
    (tmp_path / "mounted" / "pack.json").write_bytes(seal_manifest(_pack(), REVIEW))
    (tmp_path / "alias").symlink_to(tmp_path / "mounted", target_is_directory=True)
    assert load_trusted_pack_registry(str(tmp_path / "alias" / "pack.json")).installed


def test_a_fifo_refuses_without_blocking(tmp_path: Path) -> None:
    fifo = tmp_path / "pipe"
    os.mkfifo(fifo)
    assert _reason(fifo) == "manifest_not_regular_file"


def test_an_oversized_file_refuses(tmp_path: Path) -> None:
    big = tmp_path / "big.json"
    big.write_bytes(b" " * (MAX_MANIFEST_BYTES + 1))
    assert _reason(big) == "manifest_too_large"


def test_a_file_at_the_limit_is_read_in_full_and_judged_on_content(tmp_path: Path) -> None:
    edge = tmp_path / "edge.json"
    edge.write_bytes(b" " * MAX_MANIFEST_BYTES)
    assert _reason(edge) == "manifest_not_json"


def test_an_unreadable_file_refuses_with_the_errno(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "pack.json"
    path.write_bytes(seal_manifest(_pack(), REVIEW))

    def deny(*_args: Any, **_kwargs: Any) -> int:
        raise PermissionError(13, "denied")

    monkeypatch.setattr(os, "open", deny)
    with pytest.raises(PackManifestRefused) as caught:
        load_trusted_pack_registry(str(path))
    assert (caught.value.reason, caught.value.detail) == ("manifest_unreadable", "EACCES")


def test_a_path_with_a_nul_refuses() -> None:
    assert _reason("/tmp/pack\x00.json") == "manifest_unreadable"


def test_a_bad_file_never_degrades_to_the_empty_registry(tmp_path: Path) -> None:
    path = tmp_path / "pack.json"
    path.write_bytes(b"{}")
    with pytest.raises(PackManifestRefused):
        load_trusted_pack_registry(str(path))


# --- the operator CLI --------------------------------------------------------------------------


class FakeSets:
    """An injected stand-in for the one read-only database transaction."""

    def __init__(self, pack: TrustedPack, *, unverified: str | None = None) -> None:
        self.pack = pack
        self.unverified = unverified
        self.urls: list[str] = []
        self.asked: list[str] = []
        self.closed = 0

    @contextmanager
    def __call__(self, url: str) -> Iterator[Callable[[SetIdentity, str], VerifiedSetReference]]:
        self.urls.append(url)
        try:
            yield self.select
        finally:
            self.closed += 1

    def select(self, identity: SetIdentity, chunking_profile: str) -> VerifiedSetReference:
        scope = next(s for s in self.pack.scopes if s.identity.map_sha256 == identity.map_sha256)
        self.asked.append(scope.scope_id)
        if scope.scope_id == self.unverified:
            raise PromotionRefused("verified retrieval set with custody is unavailable")
        return VerifiedSetReference(
            set_id=scope.set_id, snapshot_id=identity.snapshot_id, map_sha256=identity.map_sha256,
            reviewed_content_key=identity.reviewed_content_key, chunking_profile=chunking_profile,
            embedding_profile="bge-m3-dense-v1", builder_version=identity.builder_version,
            set_sha256=scope.set_sha256, catalogue_sha256="2" * 64, set_blob_id="blob_a",
            set_size_bytes=10, catalogue_blob_id="blob_b", catalogue_size_bytes=11,
        )


def _spec(pack: TrustedPack) -> dict[str, Any]:
    return {
        "analysis_profile_id": pack.analysis_profile_id,
        "prompt_bundle_id": pack.prompt_bundle_id,
        "scopes": [
            {
                "scope_id": s.scope_id, "map_sha256": s.identity.map_sha256,
                "snapshot_id": s.identity.snapshot_id,
                "reviewed_content_key": s.identity.reviewed_content_key,
                "embedding_build": s.identity.embedding_build,
                "builder_version": s.identity.builder_version,
                "chunking_profile": s.chunking_profile,
            }
            for s in pack.scopes
        ],
    }


def _run(argv: list[str], **kwargs: Any) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    status = v3_pack_cli.main(argv, out=out, err=err, **kwargs)
    return status, out.getvalue(), err.getvalue()


def _seal_argv(spec: Path, out: Path, *extra: str) -> list[str]:
    return [
        "seal", "--scopes", str(spec), "--reviewer", REVIEW.reviewer, "--capacity", REVIEW.capacity,
        "--reviewed-at", REVIEW.reviewed_at, "--decision-ref", REVIEW.decision_ref,
        "--scope-statement", REVIEW.scope_statement, "--out", str(out), *extra,
    ]


def _write_spec(tmp_path: Path, pack: TrustedPack, mutate: Callable[[dict[str, Any]], None] | None = None) -> Path:
    spec = _spec(pack)
    if mutate is not None:
        mutate(spec)
    path = tmp_path / "scopes.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    return path


def test_seal_writes_the_manifest_the_server_loads(tmp_path: Path) -> None:
    pack = _pack()
    fake = FakeSets(pack)
    out = tmp_path / "manifest.json"
    status, stdout, stderr = _run(
        _seal_argv(_write_spec(tmp_path, pack), out, "--database-url", "postgresql+psycopg://u@h/d"),
        open_selector=fake, environ={},
    )
    assert (status, stderr) == (0, "")
    assert fake.asked == list(SCOPES) and fake.closed == 1
    assert fake.urls == ["postgresql+psycopg://u@h/d"]
    assert out.read_bytes() == seal_manifest(pack, REVIEW)
    assert load_trusted_pack_registry(str(out)).installed == (pack,)
    assert stdout.startswith("v3-pack SEALED pack_sha256=" + pack.sha256)
    assert (out.stat().st_mode & 0o777) == 0o600
    assert sorted(p.name for p in tmp_path.iterdir()) == ["manifest.json", "scopes.json"]


def test_seal_takes_the_database_from_the_environment_unless_told_otherwise(tmp_path: Path) -> None:
    pack = _pack()
    spec = _write_spec(tmp_path, pack)
    fake = FakeSets(pack)
    assert _run(_seal_argv(spec, tmp_path / "a.json"), open_selector=fake,
                environ={"DATABASE_URL": "postgresql+psycopg://env/d"})[0] == 0
    assert _run(_seal_argv(spec, tmp_path / "b.json", "--database-url", "postgresql+psycopg://arg/d"),
                open_selector=fake, environ={"DATABASE_URL": "postgresql+psycopg://env/d"})[0] == 0
    assert fake.urls == ["postgresql+psycopg://env/d", "postgresql+psycopg://arg/d"]


def test_seal_without_any_database_refuses_before_reading_the_database(tmp_path: Path) -> None:
    pack = _pack()
    fake = FakeSets(pack)
    status, _out, err = _run(_seal_argv(_write_spec(tmp_path, pack), tmp_path / "m.json"),
                             open_selector=fake, environ={})
    assert status == 2 and "database_url_missing" in err
    assert fake.urls == [] and not (tmp_path / "m.json").exists()


def test_seal_refuses_when_any_scope_has_no_verified_set_and_writes_nothing(tmp_path: Path) -> None:
    pack = _pack()
    fake = FakeSets(pack, unverified="A2")
    out = tmp_path / "m.json"
    status, _stdout, err = _run(
        _seal_argv(_write_spec(tmp_path, pack), out, "--database-url", "postgresql+psycopg://u@h/d"),
        open_selector=fake, environ={},
    )
    assert status == 2 and err.startswith("v3-pack REFUSED scope_unverified") and "A2" in err
    assert fake.asked == ["F1", "F2", "A1", "A2"] and fake.closed == 1
    assert sorted(p.name for p in tmp_path.iterdir()) == ["scopes.json"]


def test_seal_refuses_a_set_answered_for_another_identity(tmp_path: Path) -> None:
    pack = _pack()

    class Wrong(FakeSets):
        def select(self, identity: SetIdentity, chunking_profile: str) -> VerifiedSetReference:
            return replace(super().select(identity, chunking_profile), map_sha256="f" * 64)

    status, _o, err = _run(
        _seal_argv(_write_spec(tmp_path, pack), tmp_path / "m.json", "--database-url", "x"),
        open_selector=Wrong(pack), environ={},
    )
    assert status == 2 and "scope_unverified" in err and not (tmp_path / "m.json").exists()


def test_seal_refuses_to_overwrite_without_force_and_replaces_with_it(tmp_path: Path) -> None:
    pack = _pack()
    spec = _write_spec(tmp_path, pack)
    out = tmp_path / "m.json"
    out.write_bytes(b"previous")
    fake = FakeSets(pack)
    status, _o, err = _run(_seal_argv(spec, out, "--database-url", "x"), open_selector=fake, environ={})
    assert status == 2 and "out_exists" in err
    assert out.read_bytes() == b"previous" and fake.urls == []
    assert _run(_seal_argv(spec, out, "--database-url", "x", "--force"), open_selector=fake, environ={})[0] == 0
    assert out.read_bytes() == seal_manifest(pack, REVIEW)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["m.json", "scopes.json"]


def test_a_target_that_appears_between_check_and_publish_is_not_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    pack = _pack()
    out = tmp_path / "m.json"

    def lose_the_race(_source: str, target: str) -> None:
        Path(target).write_bytes(b"winner")
        raise FileExistsError(17, "exists")

    monkeypatch.setattr(os, "link", lose_the_race)
    status, _o, err = _run(
        _seal_argv(_write_spec(tmp_path, pack), out, "--database-url", "x"),
        open_selector=FakeSets(pack), environ={},
    )
    assert status == 2 and "out_exists" in err
    assert out.read_bytes() == b"winner"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["m.json", "scopes.json"]


def test_seal_into_a_missing_directory_is_a_typed_write_failure(tmp_path: Path) -> None:
    pack = _pack()
    status, _o, err = _run(
        _seal_argv(_write_spec(tmp_path, pack), tmp_path / "nope" / "m.json", "--database-url", "x"),
        open_selector=FakeSets(pack), environ={},
    )
    assert status == 2 and "write_failed" in err


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        pytest.param(lambda s: s.update(extra=1), "spec_keys", id="root_unknown_key"),
        pytest.param(lambda s: s.pop("prompt_bundle_id"), "spec_keys", id="root_missing_key"),
        pytest.param(lambda s: s["scopes"][0].update(set_id="nrs_x"), "spec_keys", id="spec_names_a_set"),
        pytest.param(lambda s: s["scopes"].pop(), "spec_scopes", id="five_scopes"),
        pytest.param(lambda s: s["scopes"].reverse(), "spec_scopes", id="reordered"),
        pytest.param(lambda s: s["scopes"][1].update(map_sha256=s["scopes"][0]["map_sha256"]), "spec_scopes", id="duplicate_map"),
        pytest.param(lambda s: s["scopes"][0].update(map_sha256="A" * 64), "spec_value", id="map_not_lowercase_hex"),
        pytest.param(lambda s: s["scopes"][0].update(snapshot_id=""), "spec_value", id="blank_value"),
    ],
)
def test_a_malformed_scopes_file_is_refused_before_any_database_read(
    tmp_path: Path, mutate: Callable[[dict[str, Any]], None], reason: str,
) -> None:
    pack = _pack()
    fake = FakeSets(pack)
    status, _o, err = _run(
        _seal_argv(_write_spec(tmp_path, pack, mutate), tmp_path / "m.json", "--database-url", "x"),
        open_selector=fake, environ={},
    )
    assert status == 2 and f"REFUSED {reason}" in err
    assert fake.urls == []


def test_a_scopes_file_that_is_missing_or_not_json_is_refused(tmp_path: Path) -> None:
    fake = FakeSets(_pack())
    missing = _run(_seal_argv(tmp_path / "none.json", tmp_path / "m.json", "--database-url", "x"),
                   open_selector=fake, environ={})
    assert missing[0] == 2 and "scopes_file_unreadable" in missing[2]
    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    refused = _run(_seal_argv(broken, tmp_path / "m.json", "--database-url", "x"),
                   open_selector=fake, environ={})
    assert refused[0] == 2 and "spec_not_json" in refused[2]
    assert fake.urls == []


def test_a_review_the_loader_would_refuse_is_never_written(tmp_path: Path) -> None:
    pack = _pack()
    argv = _seal_argv(_write_spec(tmp_path, pack), tmp_path / "m.json", "--database-url", "x")
    argv[argv.index("--reviewed-at") + 1] = "yesterday"
    status, _o, err = _run(argv, open_selector=FakeSets(pack), environ={})
    assert status == 2 and "manifest_value" in err and not (tmp_path / "m.json").exists()


def test_verify_prints_one_line_and_exits_zero(tmp_path: Path) -> None:
    pack = _pack()
    path = tmp_path / "m.json"
    path.write_bytes(seal_manifest(pack, REVIEW))
    status, stdout, stderr = _run(["verify", "--manifest", str(path)])
    assert (status, stderr) == (0, "")
    assert stdout.count("\n") == 1
    assert f"pack_sha256={pack.sha256}" in stdout
    assert "scopes=F1,F2,A1,A2,S1,S2" in stdout
    assert "maps=" + ",".join(s.identity.map_sha256[:12] for s in pack.scopes) in stdout
    assert 'reviewer="Test Reviewer"' in stdout


def test_verify_refuses_a_tampered_copy_with_status_two_and_the_reason(tmp_path: Path) -> None:
    document = _document()
    document["scopes"][0]["set_sha256"] = "e" * 64
    path = tmp_path / "tampered.json"
    path.write_bytes(_dump(document))
    status, stdout, stderr = _run(["verify", "--manifest", str(path)])
    assert (status, stdout) == (2, "")
    assert stderr == "v3-pack REFUSED pack_digest_mismatch: pack_sha256 differs from the scopes\n"


def test_the_command_line_has_no_fallback_for_a_missing_argument() -> None:
    assert _run(["verify"])[0] == 2
    assert _run(["seal", "--scopes", "x"])[0] == 2
    assert _run([])[0] == 2


def test_the_module_runs_as_a_command_and_the_exit_status_is_the_contract(tmp_path: Path) -> None:
    good = tmp_path / "good.json"
    good.write_bytes(seal_manifest(_pack(), REVIEW))
    document = _document()
    document["scopes"][0]["set_sha256"] = "e" * 64
    bad = tmp_path / "bad.json"
    bad.write_bytes(_dump(document))
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}

    def run(manifest: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "auditmanager.runs.v3_pack_cli", "verify", "--manifest", str(manifest)],
            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60, check=False,
        )

    ok, refused = run(good), run(bad)
    assert (ok.returncode, ok.stderr) == (0, "")
    assert ok.stdout.startswith("v3-pack OK pack_sha256=")
    assert refused.returncode == 2 and "pack_digest_mismatch" in refused.stderr


def test_load_manifest_returns_the_review_for_the_operator(tmp_path: Path) -> None:
    path = tmp_path / "m.json"
    path.write_bytes(seal_manifest(_pack(), REVIEW))
    assert load_manifest(str(path)).review == REVIEW
