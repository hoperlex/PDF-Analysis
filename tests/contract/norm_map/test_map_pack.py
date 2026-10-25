"""The map-pack toolchain turns recorded decisions into six acceptable canonical maps.

Everything runs on the SYNTHETIC fixture under ``tests/fixtures/ar_v3_map_pack``; the real
decisions, official-edition page evidence, query vectors and expert signature do not exist
in this repository. The real W57 builders and the v3 parser are used as the oracle for what
a map and its prompt part must be.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import sys
from array import array
from pathlib import Path
from typing import Any, Callable

import pytest

from auditmanager.analysis.profiles.ar_v3.norm_map import map_pack
from auditmanager.analysis.profiles.ar_v3.norm_map.beta_sources import load_beta_source_policy
from auditmanager.analysis.profiles.ar_v3.norm_map.map_pack import (
    MapPackRefused,
    ScopeMap,
    ScopeMaps,
    build_scope_maps,
    canonical_bytes,
    check_scope_maps,
    parse_paragraphs,
    require_distinct_map_digests,
    validate_scope_maps,
)
from auditmanager.analysis.profiles.ar_v3.prompt_material import prepare_v3_prompt
from auditmanager.analysis.profiles.ar_v3.scope_partition import scope_membership
from auditmanager.analysis.profiles.ar_v3.set_input import parse_v3_set_input
from auditmanager.analysis.text.textlayer import Page, TextLayer
from auditmanager.norms.embedding import vectors as norm_vectors
from auditmanager.norms.embedding.profile import DIMENSIONS
from auditmanager.norms.retrieval.artifact import (
    ArtifactRefused,
    SetIdentity,
    SnapshotBinding,
    SourceParagraph,
    build_retrieval_set,
    canonical_json_bytes,
)
from auditmanager.norms.retrieval import promote_cli
from auditmanager.norms.retrieval.promotion import PromotionRequest, _checked
from auditmanager.norms.retrieval.ranking import (
    RetrievalItem,
    RetrievalParagraph,
    TargetSpan,
    select_prompt_part,
)
from auditmanager.shared.identity import NormDocumentId, NormRetrievalSetId


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "ar_v3_map_pack"
SRC = Path(__file__).resolve().parents[3] / "src"
COMPOSITION = "79396188486c430729213279fb7c1c8fca7c13ede3f3f13388d06d9f93bbb781"
SCOPE_IDS = ("F1", "F2", "A1", "A2", "S1", "S2")
BLOCKED = ("C05", "C06", "C08", "C09", "C10", "C15", "C21", "C22")
# Golden digests of the synthetic fixture under the frozen beta policy.
GOLDEN_SHA256 = {
    "F1": "b3b675f6a15d7d537d30dadbda475b8b7eed90c60ff312fdc4b1f1b8873496e7",
    "F2": "82b911b71dc31457f4a65d4c30a0678bad553dfc90648b4f9b1b6f106a309965",
    "A1": "95e5913540608c39bcc33025ca826733f230834b0e3fbbde1c56bcde295adee7",
    "A2": "9a7e61f4be980e4c59de2cc4fb56e2ad4361ed5265d93b34e0c7d28580353b75",
    "S1": "efe44772581449e2149f098b3c7449179fe7a6c012aa49b8ac7979e93757bfca",
    "S2": "e56fd4a2334ce652fe999230e7d05ad58a60c167766286aef83c26e78600c52f",
}


def _decisions() -> dict[str, Any]:
    return json.loads((FIXTURES / "synthetic-decisions.json").read_text(encoding="utf-8"))


def _paragraph_payload() -> dict[str, Any]:
    return json.loads((FIXTURES / "synthetic-paragraphs.json").read_text(encoding="utf-8"))


def _paragraphs(payload: dict[str, Any] | None = None):
    payload = _paragraph_payload() if payload is None else payload
    return parse_paragraphs(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def _build(decisions: dict[str, Any] | None = None) -> ScopeMaps:
    return build_scope_maps(_decisions() if decisions is None else decisions, allow_synthetic=True)


def _item(decisions: dict[str, Any], item_id: str) -> dict[str, Any]:
    return next(item for item in decisions["items"] if item["id"] == item_id)


def _refused(code: str):
    return pytest.raises(MapPackRefused, match="^" + re.escape(code))


def _remap(maps: ScopeMaps, scope_id: str, mutate: Callable[[dict[str, Any]], None]) -> ScopeMaps:
    """Re-encode one canonical map after a mutation, so only that mutation can refuse."""
    changed = []
    for entry in maps.maps:
        if entry.scope_id == scope_id:
            mapping = json.loads(entry.data)
            mutate(mapping)
            entry = ScopeMap(scope_id, canonical_bytes(mapping))
        changed.append(entry)
    return ScopeMaps(tuple(changed), maps.review)


def _real_like() -> tuple[dict[str, Any], dict[str, Any]]:
    """The synthetic content relabelled as a non-synthetic pack on the policy snapshot."""
    snapshot = load_beta_source_policy().snapshot_id
    decisions, payload = _decisions(), _paragraph_payload()
    decisions["synthetic"] = False
    decisions["identity"]["norms_snapshot_id"] = snapshot
    payload["synthetic"] = False
    payload["norms_snapshot_id"] = snapshot
    return decisions, payload


# ---------------------------------------------------------------- the pack as built

def test_synthetic_pack_has_six_canonical_maps_in_frozen_order_with_golden_digests() -> None:
    maps = _build()
    assert tuple(entry.scope_id for entry in maps.maps) == SCOPE_IDS
    assert {entry.scope_id: entry.sha256 for entry in maps.maps} == GOLDEN_SHA256
    assert len({entry.sha256 for entry in maps.maps}) == 6
    for entry in maps.maps:
        mapping = json.loads(entry.data)
        assert canonical_bytes(mapping) == entry.data
        assert mapping["composition_sha256"] == COMPOSITION
        assert tuple(item["id"] for item in mapping["items"]) == scope_membership(entry.scope_id).item_ids
    assert [item["id"] for entry in maps.maps for item in json.loads(entry.data)["items"]] == [
        f"C{number:02d}" for number in range(1, 23)
    ]


def test_build_is_deterministic_and_independent_of_input_order() -> None:
    first = _build()
    assert _build() == first
    shuffled = _decisions()
    shuffled["items"].reverse()
    two_targets = _decisions()
    _item(two_targets, "C01")["targets"].append(copy.deepcopy(_item(two_targets, "C02")["targets"][0]))
    reordered = copy.deepcopy(two_targets)
    _item(reordered, "C01")["targets"].reverse()
    assert _build(shuffled) == first
    assert _build(reordered) == _build(two_targets) != first


def test_summary_records_six_digests_composition_char_counts_and_pending_review() -> None:
    maps = _build()
    summary = validate_scope_maps(maps, _paragraphs(), allow_synthetic=True)
    assert summary["composition_sha256"] == COMPOSITION
    assert summary["review_state"] == "pending_expert" and summary["review"] is None
    assert summary["synthetic"] is True and summary["prompt_part_cap"] == 22_000
    assert [scope["map_sha256"] for scope in summary["scopes"]] == [GOLDEN_SHA256[s] for s in SCOPE_IDS]
    assert all(0 < scope["prompt_part_characters"] <= 22_000 for scope in summary["scopes"])
    f2 = summary["scopes"][1]
    assert f2["context_only_item_ids"] == ["C05", "C06", "C08", "C09", "C10"]
    assert f2["provisional_item_ids"] == ["C04", "C07"]
    assert summary["scopes"][0]["edition_evidence_missing"] == ["C02", "C03"]


def test_mapped_document_ids_are_what_the_real_promotion_check_requires() -> None:
    for entry in _build().maps:
        mapping = json.loads(entry.data)
        request = PromotionRequest(
            set_id=str(NormRetrievalSetId.new()),
            identity=SetIdentity(entry.sha256, mapping["norms_snapshot_id"],
                                 mapping["reviewed_content_key"], mapping["embedding_build"]),
            map_bytes=entry.data, reviewed_designations=(), items=(),
            chunking_profile="characters-v2:1000",
            independently_checked_source_digest="1" * 64,
            independently_checked_embedding_digest="2" * 64,
            expected_set_sha256="3" * 64, expected_catalogue_sha256="4" * 64,
        )
        assert _checked(request) == tuple(mapping["mapped_document_ids"])
        assert mapping["mapped_document_ids"] and len(set(mapping["mapped_document_ids"])) == len(
            mapping["mapped_document_ids"])


def test_canonical_encoder_is_byte_equal_to_the_norms_encoder() -> None:
    values = [{}, [], "text", {"b": 1, "a": [True, None, 0]}, {"к": "Нормы — ёж"},
              {"n": {"m": [{"z": 1, "y": "é"}]}}]
    for value in values:
        assert canonical_bytes(value) == canonical_json_bytes(value)
    for value in ({"f": 1.5}, {"s": "é"}, {1: "x"}, {"t": object()}):
        with pytest.raises(ArtifactRefused):
            canonical_json_bytes(value)
        with pytest.raises(MapPackRefused):
            canonical_bytes(value)


# ---------------------------------------------------------------- the real builders accept the pack

def _unit() -> array:
    return array("f", [1.0] + [0.0] * (DIMENSIONS - 1))


def test_every_map_and_its_prompt_part_pass_the_real_set_builder_and_v3_material() -> None:
    maps = _build()
    paragraphs = _paragraphs()
    summary = validate_scope_maps(maps, paragraphs, allow_synthetic=True)
    for entry, scope in zip(maps.maps, summary["scopes"]):
        mapping = json.loads(entry.data)
        mapped = set(mapping["mapped_document_ids"])
        rows = tuple(
            RetrievalParagraph(
                document_id=p.document_id, paragraph_id=p.paragraph_id, designation=p.designation,
                title=p.title, ordinal=p.ordinal, clause_number=p.clause_number,
                page_label=p.page_label, text=p.text, reliable=p.reliable)
            for p in paragraphs.rows if p.document_id in mapped
        )
        items = tuple(
            RetrievalItem(item["id"], _unit(), tuple(
                TargetSpan(t["norm_document_id"], t["ordinal_first"], t["ordinal_last"])
                for t in item["targets"]))
            for item in mapping["items"]
        )
        selection = select_prompt_part(items, rows, ())
        # The tool's target-only render is the real renderer's output, byte for byte.
        assert hashlib.sha256(selection.prompt_part.encode("utf-8")).hexdigest() == scope["prompt_part_sha256"]
        assert len(selection.prompt_part) == scope["prompt_part_characters"]
        identity = SetIdentity(entry.sha256, mapping["norms_snapshot_id"],
                               mapping["reviewed_content_key"], mapping["embedding_build"])
        blob = build_retrieval_set(
            identity=identity, map_bytes=entry.data,
            snapshot=SnapshotBinding(mapping["norms_snapshot_id"], mapping["reviewed_content_key"],
                                     "a" * 64, mapping["embedding_build"], len(mapped)),
            selection=selection,
            paragraphs=tuple(SourceParagraph(row, hashlib.sha256(row.text.encode()).hexdigest())
                             for row in rows),
        )
        parsed = parse_v3_set_input(
            blob.data, expected_sha256=blob.sha256, expected_snapshot_id=mapping["norms_snapshot_id"],
            expected_map_sha256=entry.sha256)
        assert parsed.selected_item_ids == scope_membership(entry.scope_id).item_ids
        text = "synthetic page text"
        layer = TextLayer("ver_fixture", "NFC", (Page(1, 0, len(text), text),), text)
        assert prepare_v3_prompt(layer, parsed).prompt_part_characters == scope["prompt_part_characters"]


# ---------------------------------------------------------------- totality and modes

@pytest.mark.parametrize(("mutate", "code"), [
    (lambda d: d["items"].pop(), "item_missing:C22"),
    (lambda d: d["items"].append(copy.deepcopy(d["items"][4])), "item_duplicate:C05"),
    (lambda d: d["items"].__setitem__(0, dict(d["items"][0], id="C23")), "item_unknown"),
    (lambda d: d["items"].append("C23"), "item_unknown"),
])
def test_every_item_c01_to_c22_must_be_decided_exactly_once(mutate, code: str) -> None:
    decisions = _decisions()
    mutate(decisions)
    with _refused(code):
        _build(decisions)


def test_policy_context_only_items_are_exactly_the_eight_blocked_ones() -> None:
    policy = load_beta_source_policy()
    assert tuple(item.item_id for item in policy.items if item.mode == "context_only") == BLOCKED


@pytest.mark.parametrize("item_id", BLOCKED)
def test_a_context_only_item_can_never_be_upgraded_by_the_decision_file(item_id: str) -> None:
    decisions = _decisions()
    item = _item(decisions, item_id)
    item["mode"] = "provisional_citation"
    item["branch"] = {"id": "N", "applicability": "SYNTHETIC upgrade attempt"}
    item["edition_evidence"] = []
    with _refused(f"context_only_upgrade_refused:{item_id}"):
        _build(decisions)
    # The same upgrade smuggled into finished map bytes is refused by the validator too.
    maps = _build()

    def upgrade(mapping: dict[str, Any]) -> None:
        for entry in mapping["items"]:
            if entry["id"] == item_id:
                entry.update(mode="provisional_citation", branch=item["branch"], edition_evidence=[])

    scope = next(s for s in SCOPE_IDS if item_id in scope_membership(s).item_ids)
    with _refused(f"context_only_upgrade_refused:{item_id}"):
        check_scope_maps(_remap(maps, scope, upgrade), allow_synthetic=True)


def test_a_provisional_item_may_be_downgraded_to_context_only() -> None:
    decisions = _decisions()
    item = _item(decisions, "C02")
    item["mode"] = "context_only"
    del item["branch"], item["edition_evidence"]
    mapping = json.loads(next(e for e in _build(decisions).maps if e.scope_id == "F1").data)
    assert [i["mode"] for i in mapping["items"]] == ["provisional_citation", "context_only", "provisional_citation"]


@pytest.mark.parametrize("field", ["branch", "edition_evidence"])
def test_context_only_items_never_carry_a_citation_branch(field: str) -> None:
    decisions = _decisions()
    _item(decisions, "C05")[field] = {"id": "N", "applicability": "x"} if field == "branch" else []
    with _refused("context_only_carries_citation:C05"):
        _build(decisions)


@pytest.mark.parametrize("field", ["branch", "edition_evidence"])
def test_a_provisional_item_must_state_its_branch_and_evidence_list(field: str) -> None:
    decisions = _decisions()
    del _item(decisions, "C01")[field]
    with _refused("item_keys_invalid:C01"):
        _build(decisions)


def test_edition_evidence_is_unique_and_sorted_whatever_the_input_order() -> None:
    entries = [{"source_id": "D1_MCHS_1", "pages": "1", "page_sha256": "1" * 64},
               {"source_id": "D1_PUBLIC_2", "pages": "2", "page_sha256": "2" * 64},
               {"source_id": "D1_PUBLIC_2", "pages": "3", "page_sha256": "0" * 64}]
    forward, backward = _decisions(), _decisions()
    _item(forward, "C01")["edition_evidence"] = entries
    _item(backward, "C01")["edition_evidence"] = list(reversed(entries))
    assert _build(forward) == _build(backward)
    mapping = json.loads(_build(forward).maps[0].data)
    assert [e["page_sha256"] for e in mapping["items"][0]["edition_evidence"]] == ["1" * 64, "0" * 64, "2" * 64]
    duplicated = _decisions()
    _item(duplicated, "C01")["edition_evidence"] = [entries[0], dict(entries[0])]
    with _refused("edition_evidence_not_canonical:C01"):
        _build(duplicated)
    unsorted = _build(forward)
    with _refused("edition_evidence_not_canonical:C01"):
        check_scope_maps(_remap(unsorted, "F1", lambda m: m["items"][0]["edition_evidence"].reverse()),
                         allow_synthetic=True)


def test_evidence_must_come_from_a_text_source_the_policy_names_for_that_item() -> None:
    entry = {"source_id": "D1_LOCAL", "pages": "1", "page_sha256": "0" * 64}
    for source_id in ("D1_LOCAL", "NOT_A_SOURCE", "D3_PUBLIC_CONSOLIDATED"):
        decisions = _decisions()
        _item(decisions, "C01")["edition_evidence"] = [dict(entry, source_id=source_id)]
        with _refused("edition_evidence_source_invalid:C01"):
            _build(decisions)
    decisions = _decisions()
    _item(decisions, "C01")["edition_evidence"] = [dict(entry, source_id="D1_PUBLIC_2")]
    assert _build(decisions) != _build()


# ---------------------------------------------------------------- strict shapes

def _extra(locate: Callable[[dict[str, Any]], dict[str, Any]]) -> Callable[[dict[str, Any]], None]:
    return lambda decisions: locate(decisions).__setitem__("unexpected", 1)


@pytest.mark.parametrize(("mutate", "code"), [
    (_extra(lambda d: d), "decisions_shape_invalid"),
    (_extra(lambda d: d["identity"]), "identity_shape_invalid"),
    (_extra(lambda d: d["query_vectors"]), "query_vectors_shape_invalid"),
    (_extra(lambda d: d["query_vectors"]["sha256_by_scope"]), "query_vectors_scopes_invalid"),
    (_extra(lambda d: _item(d, "C01")), "item_keys_invalid:C01"),
    (_extra(lambda d: _item(d, "C05")), "item_keys_invalid:C05"),
    (_extra(lambda d: _item(d, "C01")["targets"][0]), "target_shape_invalid:C01"),
    (_extra(lambda d: _item(d, "C01")["branch"]), "branch_invalid:C01"),
    (_extra(lambda d: _item(d, "C01")["edition_evidence"][0]), "edition_evidence_invalid:C01"),
])
def test_unknown_keys_are_refused_at_every_level_of_the_decision_file(mutate, code: str) -> None:
    decisions = _decisions()
    mutate(decisions)
    with _refused(code):
        _build(decisions)


def test_unknown_keys_in_finished_map_bytes_are_refused() -> None:
    maps = _build()
    with _refused("map_keys_invalid:F1"):
        check_scope_maps(_remap(maps, "F1", lambda m: m.__setitem__("approved", True)), allow_synthetic=True)
    with _refused("target_shape_invalid:C01"):
        check_scope_maps(
            _remap(maps, "F1", lambda m: m["items"][0]["targets"][0].__setitem__("x", 1)),
            allow_synthetic=True)
    with _refused("query_vectors_invalid:F1"):
        check_scope_maps(
            _remap(maps, "F1", lambda m: m["query_vectors"].__setitem__("x", 1)), allow_synthetic=True)


def test_duplicate_json_keys_and_non_finite_numbers_are_refused() -> None:
    with _refused("duplicate_json_key"):
        map_pack.parse_decisions(b'{"a":1,"a":2}')
    with _refused("invalid_json_constant"):
        map_pack.parse_decisions(b'{"a":NaN}')
    with _refused("decisions_json_invalid"):
        map_pack.parse_decisions(b"\xef\xbb\xbf{}")


@pytest.mark.parametrize(("path", "value", "code"), [
    (("targets", 0, "ordinal_first"), 1.5, "target_value_invalid:C01"),
    (("targets", 0, "ordinal_first"), True, "target_value_invalid:C01"),
    (("targets", 0, "ordinal_last"), -1, "target_value_invalid:C01"),
    (("targets", 0, "kind"), "paragraph", "target_value_invalid:C01"),
    (("targets", 0, "norm_document_id"), "ndoc_lowercase", "target_value_invalid:C01"),
    (("targets", 0, "edition"), " padded", "target_value_invalid:C01"),
    (("targets", 0, "edition"), "é", "target_value_invalid:C01"),
    (("targets",), [], "targets_missing:C01"),
    (("branch", "id"), "bad id", "branch_invalid:C01"),
    (("branch", "applicability"), "", "branch_invalid:C01"),
    (("mode",), "approved", "item_mode_invalid:C01"),
])
def test_item_values_are_checked_strictly(path: tuple, value: Any, code: str) -> None:
    decisions = _decisions()
    node = _item(decisions, "C01")
    for step in path[:-1]:
        node = node[step]
    node[path[-1]] = value
    with _refused(code):
        _build(decisions)


def test_duplicate_or_unsorted_targets_are_not_canonical() -> None:
    decisions = _decisions()
    target = _item(decisions, "C01")["targets"][0]
    _item(decisions, "C01")["targets"].append(copy.deepcopy(target))
    with _refused("targets_not_canonical:C01"):
        _build(decisions)
    decisions = _decisions()
    _item(decisions, "C01")["targets"].append(copy.deepcopy(_item(decisions, "C02")["targets"][0]))
    maps = _build(decisions)
    with _refused("targets_not_canonical:C01"):
        check_scope_maps(_remap(maps, "F1", lambda m: m["items"][0]["targets"].reverse()),
                         allow_synthetic=True)


# ---------------------------------------------------------------- map bytes, identity and distinct digests

@pytest.mark.parametrize("damage", [
    lambda data: data + b"\n",
    lambda data: json.dumps(json.loads(data), ensure_ascii=False, indent=1).encode("utf-8"),
    lambda data: data.replace(b'"scope_id"', b' "scope_id"', 1),
])
def test_map_bytes_must_be_exactly_the_canonical_encoding(damage) -> None:
    maps = _build()
    damaged = ScopeMaps((ScopeMap("F1", damage(maps.maps[0].data)), *maps.maps[1:]))
    with _refused("map_not_canonical:F1"):
        check_scope_maps(damaged, allow_synthetic=True)


def test_scope_set_must_be_the_six_scopes_in_frozen_order() -> None:
    maps = _build()
    for broken in (ScopeMaps(maps.maps[:5]), ScopeMaps(tuple(reversed(maps.maps)))):
        with _refused("scope_set_invalid"):
            check_scope_maps(broken, allow_synthetic=True)
    # A foreign map placed in a slot cannot pass for that scope.
    with _refused("map_identity_invalid:S2"):
        check_scope_maps(ScopeMaps((*maps.maps[:5], ScopeMap("S2", maps.maps[0].data))),
                         allow_synthetic=True)


def test_a_map_for_the_wrong_scope_or_composition_or_policy_is_refused() -> None:
    maps = _build()
    for field, value in (("scope_id", "F2"), ("composition_sha256", "0" * 64),
                         ("policy_sha256", "0" * 64), ("scenario", "other_scenario"),
                         ("map_schema_version", "v0")):
        with _refused("map_identity_invalid:F1"):
            check_scope_maps(_remap(maps, "F1", lambda m, f=field, v=value: m.__setitem__(f, v)),
                             allow_synthetic=True)


def test_maps_of_one_pack_must_share_one_snapshot_build_and_vector_model() -> None:
    maps = _build()
    with _refused("pack_identity_inconsistent:reviewed_content_key"):
        check_scope_maps(_remap(maps, "A1", lambda m: m.__setitem__("reviewed_content_key", "OTHER")),
                         allow_synthetic=True)
    with _refused("pack_identity_inconsistent:embedding_build"):
        check_scope_maps(
            _remap(maps, "A1", lambda m: m.__setitem__("embedding_build", "bge-m3-dense-v1:characters-v2:900")),
            allow_synthetic=True)
    with _refused("pack_identity_inconsistent:query_vectors"):
        check_scope_maps(
            _remap(maps, "A1", lambda m: m["query_vectors"].__setitem__("model_revision", "1" * 40)),
            allow_synthetic=True)


def test_mapped_document_ids_must_be_the_unique_union_of_the_item_targets() -> None:
    maps = _build()
    other = "ndoc_00000000000000000000SYNTD9"
    cases = {
        "mapped_document_ids_invalid:F1": [
            lambda m: m.__setitem__("mapped_document_ids", []),
            lambda m: m.__setitem__("mapped_document_ids", m["mapped_document_ids"] * 2),
            lambda m: m.__setitem__("mapped_document_ids", ["not an id"]),
        ],
        "mapped_documents_differ_from_targets:F1": [
            lambda m: m.__setitem__("mapped_document_ids", [other]),
            lambda m: m.__setitem__("mapped_document_ids", [*m["mapped_document_ids"], other]),
        ],
    }
    for code, mutations in cases.items():
        for mutate in mutations:
            with _refused(code):
                check_scope_maps(_remap(maps, "F1", mutate), allow_synthetic=True)


def test_the_six_map_digests_must_be_distinct() -> None:
    digests = tuple(entry.sha256 for entry in _build().maps)
    require_distinct_map_digests(digests)
    with _refused("map_digests_not_distinct"):
        require_distinct_map_digests((*digests[:5], digests[0]))


# ---------------------------------------------------------------- synthetic and real identity

def test_synthetic_decisions_are_refused_unless_explicitly_allowed() -> None:
    with _refused("synthetic_refused"):
        build_scope_maps(_decisions())
    maps = _build()
    with _refused("synthetic_refused"):
        check_scope_maps(maps)
    with _refused("synthetic_refused"):
        validate_scope_maps(maps, _paragraphs())
    assert json.loads(maps.maps[0].data)["synthetic"] is True


def test_a_non_synthetic_pack_must_sit_on_the_policy_snapshot() -> None:
    decisions, payload = _real_like()
    maps = build_scope_maps(decisions)
    assert json.loads(maps.maps[0].data)["synthetic"] is False
    assert validate_scope_maps(maps, _paragraphs(payload))["synthetic"] is False
    decisions["identity"]["norms_snapshot_id"] = "ns_00000000000000000000SYNTH1"
    with _refused("snapshot_not_policy_snapshot"):
        build_scope_maps(decisions)


def test_the_flag_must_be_a_boolean_and_the_scenario_the_policy_scenario() -> None:
    decisions = _decisions()
    decisions["synthetic"] = "false"
    with _refused("synthetic_flag_invalid"):
        _build(decisions)
    decisions = _decisions()
    decisions["identity"]["scenario"] = "reconstruction"
    with _refused("map_identity_invalid:F1"):
        _build(decisions)


@pytest.mark.parametrize(("path", "value", "code"), [
    (("identity", "norms_snapshot_id"), "ns_bad", "map_snapshot_invalid:F1"),
    (("identity", "embedding_build"), "bge-m3-dense-v1", "map_snapshot_invalid:F1"),
    (("identity", "reviewed_content_key"), "", "map_snapshot_invalid:F1"),
    (("query_vectors", "profile"), "other-profile", "query_vectors_invalid:F1"),
    (("query_vectors", "model_revision"), "short", "query_vectors_invalid:F1"),
    (("query_vectors", "sha256_by_scope", "F1"), "abc", "query_vectors_invalid:F1"),
])
def test_identity_and_query_vector_provenance_are_checked(path: tuple, value: Any, code: str) -> None:
    decisions = _decisions()
    node = decisions
    for step in path[:-1]:
        node = node[step]
    node[path[-1]] = value
    with _refused(code):
        _build(decisions)


def test_every_scope_needs_its_own_query_vector_digest() -> None:
    decisions = _decisions()
    del decisions["query_vectors"]["sha256_by_scope"]["S2"]
    with _refused("query_vectors_scopes_invalid"):
        _build(decisions)


# ---------------------------------------------------------------- the 22,000-character budget

def _padded(payload: dict[str, Any], extra: int) -> dict[str, Any]:
    payload = copy.deepcopy(payload)
    first = next(p for p in payload["paragraphs"]
                 if p["norm_document_id"].endswith("SYNTD1") and p["ordinal"] == 0)
    first["text"] += "x" * extra
    return payload


def test_prompt_part_of_exactly_22000_characters_passes_and_one_more_is_refused_untruncated() -> None:
    maps = _build()
    base = validate_scope_maps(maps, _paragraphs(), allow_synthetic=True)["scopes"][0]["prompt_part_characters"]
    at_cap = validate_scope_maps(maps, _paragraphs(_padded(_paragraph_payload(), 22_000 - base)),
                                 allow_synthetic=True)["scopes"][0]
    assert at_cap["prompt_part_characters"] == 22_000
    # The recorded digest is of the whole, uncut part: the real renderer agrees at the cap.
    paragraphs = _paragraphs(_padded(_paragraph_payload(), 22_000 - base))
    mapping = json.loads(maps.maps[0].data)
    rows = tuple(
        RetrievalParagraph(p.document_id, p.paragraph_id, p.designation, p.title, p.ordinal,
                           p.clause_number, p.page_label, p.text, p.reliable)
        for p in paragraphs.rows if p.document_id in mapping["mapped_document_ids"])
    items = tuple(RetrievalItem(i["id"], _unit(), tuple(
        TargetSpan(t["norm_document_id"], t["ordinal_first"], t["ordinal_last"]) for t in i["targets"]))
        for i in mapping["items"])
    real = select_prompt_part(items, rows, ())
    assert len(real.prompt_part) == 22_000
    assert hashlib.sha256(real.prompt_part.encode()).hexdigest() == at_cap["prompt_part_sha256"]
    with _refused("prompt_part_over_cap:F1:22001>22000"):
        validate_scope_maps(maps, _paragraphs(_padded(_paragraph_payload(), 22_001 - base)),
                            allow_synthetic=True)


def test_an_over_cap_scope_is_refused_even_when_the_other_five_fit() -> None:
    maps = _build()
    payload = _paragraph_payload()
    for paragraph in payload["paragraphs"]:
        if paragraph["norm_document_id"].endswith("SYNTD5"):
            paragraph["text"] = "y" * 8_000
    with _refused("prompt_part_over_cap:S1:"):
        validate_scope_maps(maps, _paragraphs(payload), allow_synthetic=True)


# ---------------------------------------------------------------- targets resolve against the paragraphs

def _paragraph(payload: dict[str, Any], document: str, ordinal: int) -> dict[str, Any]:
    return next(p for p in payload["paragraphs"]
                if p["norm_document_id"].endswith(document) and p["ordinal"] == ordinal)


def test_targets_must_resolve_to_the_declared_reliable_paragraphs() -> None:
    maps = _build()
    wrong_id = _paragraph_payload()
    _paragraph(wrong_id, "SYNTD1", 1)["norm_paragraph_id"] = "npar_00000000000000000000SYNXTH"
    with _refused("target_not_in_paragraphs:C01"):
        validate_scope_maps(maps, _paragraphs(wrong_id), allow_synthetic=True)
    wrong_first = _paragraph_payload()
    _paragraph(wrong_first, "SYNTD1", 0)["norm_paragraph_id"] = "npar_00000000000000000000SYNXTH"
    with _refused("target_not_in_paragraphs:C01"):
        validate_scope_maps(maps, _paragraphs(wrong_first), allow_synthetic=True)
    missing = _paragraph_payload()
    missing["paragraphs"].remove(_paragraph(missing, "SYNTD1", 1))
    with _refused("target_not_in_paragraphs:C01"):
        validate_scope_maps(maps, _paragraphs(missing), allow_synthetic=True)
    unreliable = _paragraph_payload()
    _paragraph(unreliable, "SYNTD3", 3)["reliable"] = False
    with _refused("target_paragraph_unreliable:C12"):
        validate_scope_maps(maps, _paragraphs(unreliable), allow_synthetic=True)
    gap = _paragraph_payload()
    gap["paragraphs"].remove(_paragraph(gap, "SYNTD5", 1))
    with _refused("target_paragraph_missing:C21"):
        validate_scope_maps(maps, _paragraphs(gap), allow_synthetic=True)
    relabelled = _paragraph_payload()
    for paragraph in relabelled["paragraphs"]:
        if paragraph["norm_document_id"].endswith("SYNTD4"):
            paragraph["designation"] = "OTHER-DESIGNATION"
    with _refused("target_designation_mismatch:C19"):
        validate_scope_maps(maps, _paragraphs(relabelled), allow_synthetic=True)


def test_the_paragraph_file_must_match_the_pack_snapshot_and_synthetic_flag() -> None:
    maps = _build()
    other_snapshot = _paragraph_payload()
    other_snapshot["norms_snapshot_id"] = "ns_00000000000000000000SYNTH2"
    with _refused("paragraphs_snapshot_mismatch"):
        validate_scope_maps(maps, _paragraphs(other_snapshot), allow_synthetic=True)
    real_flag = _paragraph_payload()
    real_flag["synthetic"] = False
    with _refused("paragraphs_synthetic_mismatch"):
        validate_scope_maps(maps, _paragraphs(real_flag), allow_synthetic=True)


@pytest.mark.parametrize(("mutate", "code"), [
    (lambda p: p.__setitem__("extra", 1), "paragraphs_shape_invalid"),
    (lambda p: p["paragraphs"][0].__setitem__("extra", 1), "paragraph_row_invalid"),
    (lambda p: p["paragraphs"][0].__setitem__("text", ""), "paragraph_row_invalid"),
    (lambda p: p["paragraphs"][0].__setitem__("reliable", "yes"), "paragraph_row_invalid"),
    (lambda p: p["paragraphs"].append(copy.deepcopy(p["paragraphs"][0])), "paragraph_row_duplicate"),
])
def test_paragraph_rows_are_read_strictly(mutate, code: str) -> None:
    payload = _paragraph_payload()
    mutate(payload)
    with _refused(code):
        _paragraphs(payload)


# ---------------------------------------------------------------- review attestation

def _attestation(maps: ScopeMaps) -> dict[str, Any]:
    return {"reviewer": "Test Reviewer", "capacity": "expert", "date": "2026-10-26",
            "decision_ref": "TEST-REF-1", "map_sha256": {e.scope_id: e.sha256 for e in maps.maps}}


def test_pending_expert_is_the_default_and_an_attestation_is_only_recorded() -> None:
    decisions, payload = _real_like()
    pending = build_scope_maps(decisions)
    assert validate_scope_maps(pending, _paragraphs(payload))["review_state"] == "pending_expert"
    decisions["review"] = _attestation(pending)
    attested = build_scope_maps(decisions)
    assert attested.maps == pending.maps  # the attestation never changes the reviewed bytes
    summary = validate_scope_maps(attested, _paragraphs(payload))
    assert summary["review_state"] == "attestation_recorded"
    assert summary["review"] == decisions["review"]
    assert not any(key in json.loads(e.data) for e in attested.maps for key in ("review", "review_state"))


@pytest.mark.parametrize("missing", ["reviewer", "capacity", "date", "decision_ref", "map_sha256"])
def test_an_incomplete_attestation_is_refused_not_downgraded_to_pending(missing: str) -> None:
    decisions, _ = _real_like()
    review = _attestation(build_scope_maps(decisions))
    del review[missing]
    decisions["review"] = review
    with _refused("attestation_incomplete"):
        build_scope_maps(decisions)


@pytest.mark.parametrize(("key", "value"), [
    ("date", "26.10.2026"), ("date", "2026-13-01"), ("reviewer", ""), ("capacity", " expert"),
    ("extra", "unknown key"),
])
def test_attestation_fields_are_checked_strictly(key: str, value: str) -> None:
    decisions, _ = _real_like()
    review = _attestation(build_scope_maps(decisions))
    review[key] = value
    decisions["review"] = review
    with _refused("attestation_incomplete"):
        build_scope_maps(decisions)


def test_an_attestation_must_name_the_exact_six_map_digests() -> None:
    decisions, _ = _real_like()
    pending = build_scope_maps(decisions)
    stale = _attestation(pending)
    stale["map_sha256"]["F2"] = "0" * 64
    decisions["review"] = stale
    with _refused("attestation_map_digest_mismatch"):
        build_scope_maps(decisions)
    # A decision edited after review changes the bytes, so the old attestation no longer fits.
    decisions, _ = _real_like()
    decisions["review"] = _attestation(pending)
    _item(decisions, "C02")["mode"] = "context_only"
    del _item(decisions, "C02")["branch"], _item(decisions, "C02")["edition_evidence"]
    with _refused("attestation_map_digest_mismatch"):
        build_scope_maps(decisions)


def test_a_synthetic_pack_can_never_be_attested() -> None:
    decisions = _decisions()
    decisions["review"] = _attestation(_build())
    with _refused("synthetic_cannot_be_attested"):
        _build(decisions)


# ---------------------------------------------------------------- command line

def _cli(*args: str) -> int:
    return map_pack.main(list(args))


def _paths(tmp_path: Path) -> tuple[str, str, str]:
    return (str(FIXTURES / "synthetic-decisions.json"), str(FIXTURES / "synthetic-paragraphs.json"),
            str(tmp_path / "pack"))


def test_cli_builds_writes_seven_files_and_validates_them(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    decisions, paragraphs, out = _paths(tmp_path)
    assert _cli("build", "--decisions", decisions, "--paragraphs", paragraphs, "--out", out,
                "--allow-synthetic") == 0
    printed = capsys.readouterr().out
    assert "review_state pending_expert" in printed and COMPOSITION in printed
    assert sorted(p.name for p in Path(out).iterdir()) == sorted(
        [f"scope-{scope}.map.json" for scope in SCOPE_IDS] + ["pack-summary.json"])
    for scope in SCOPE_IDS:
        data = (Path(out) / f"scope-{scope}.map.json").read_bytes()
        assert hashlib.sha256(data).hexdigest() == GOLDEN_SHA256[scope]
        assert canonical_bytes(json.loads(data)) == data
    assert _cli("validate", "--maps", out, "--paragraphs", paragraphs, "--allow-synthetic") == 0


def test_cli_build_twice_into_two_directories_gives_identical_bytes(tmp_path: Path) -> None:
    decisions, paragraphs, _ = _paths(tmp_path)
    for name in ("a", "b"):
        assert _cli("build", "--decisions", decisions, "--paragraphs", paragraphs,
                    "--out", str(tmp_path / name), "--allow-synthetic") == 0
    for path in (tmp_path / "a").iterdir():
        assert path.read_bytes() == (tmp_path / "b" / path.name).read_bytes()


def test_cli_refuses_with_exit_2_and_a_reason(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    decisions, paragraphs, out = _paths(tmp_path)
    assert _cli("build", "--decisions", decisions, "--paragraphs", paragraphs, "--out", out) == 2
    assert "REFUSED: synthetic_refused" in capsys.readouterr().err
    assert not Path(out).exists()
    assert _cli("build", "--decisions", str(tmp_path / "missing.json"), "--paragraphs", paragraphs,
                "--out", out, "--allow-synthetic") == 2
    assert "file_unreadable:missing.json" in capsys.readouterr().err


def test_cli_never_overwrites_an_existing_pack(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    decisions, paragraphs, out = _paths(tmp_path)
    args = ("build", "--decisions", decisions, "--paragraphs", paragraphs, "--out", out, "--allow-synthetic")
    assert _cli(*args) == 0
    capsys.readouterr()
    before = {p.name: p.read_bytes() for p in Path(out).iterdir()}
    assert _cli(*args) == 2
    assert "REFUSED: output_exists" in capsys.readouterr().err
    assert {p.name: p.read_bytes() for p in Path(out).iterdir()} == before


def test_cli_validate_refuses_a_tampered_map_a_tampered_summary_and_a_missing_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    decisions, paragraphs, out = _paths(tmp_path)
    assert _cli("build", "--decisions", decisions, "--paragraphs", paragraphs, "--out", out,
                "--allow-synthetic") == 0
    capsys.readouterr()
    validate = ("validate", "--maps", out, "--paragraphs", paragraphs, "--allow-synthetic")
    assert _cli(*validate) == 0
    capsys.readouterr()
    summary = Path(out) / "pack-summary.json"
    original = summary.read_bytes()
    summary.write_bytes(original.replace(b"pending_expert", b"attestation_recorded"))
    assert _cli(*validate) == 2
    assert "REFUSED: summary_differs_from_maps" in capsys.readouterr().err
    summary.write_bytes(original.replace(b'"review": null', b'"review": {"reviewer": "x"}'))
    assert _cli(*validate) == 2
    assert "REFUSED: attestation_incomplete" in capsys.readouterr().err
    summary.write_bytes(original)
    map_file = Path(out) / "scope-A1.map.json"
    good = map_file.read_bytes()
    map_file.write_bytes(good + b"\n")
    assert _cli(*validate) == 2
    assert "REFUSED: map_not_canonical:A1" in capsys.readouterr().err
    map_file.unlink()
    assert _cli(*validate) == 2
    assert "file_unreadable:scope-A1.map.json" in capsys.readouterr().err


def test_python_dash_m_entry_point_exits_2_on_refusal(tmp_path: Path) -> None:
    decisions, paragraphs, out = _paths(tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "auditmanager.analysis.profiles.ar_v3.norm_map.map_pack", "build",
         "--decisions", decisions, "--paragraphs", paragraphs, "--out", out],
        capture_output=True, text=True, cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(SRC)},
        check=False)
    assert result.returncode == 2
    assert "REFUSED: synthetic_refused" in result.stderr


# ---------------------------------------------------------------- AR-V3-BETA-REVIEW-FIXES-02
#
# The set tool (`promote_cli`) must follow the maps this tool writes; these tests hold the two
# formats together. The rest are the robustness findings of the review of this tool itself.

DOCUMENT_ID = "ndoc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B"


class _LenientIdentity:
    """What the shared identity parser did before it used fullmatch: any text passed."""

    @staticmethod
    def parse(value: str) -> str:
        return value


def test_an_identity_with_a_line_break_is_refused_without_relying_on_the_shared_parser() -> None:
    assert map_pack._ident(DOCUMENT_ID, _LenientIdentity, "code") == DOCUMENT_ID
    for value in (DOCUMENT_ID + "\n", "\n" + DOCUMENT_ID, DOCUMENT_ID[:6] + "\n" + DOCUMENT_ID[6:]):
        with _refused("code"):
            map_pack._ident(value, _LenientIdentity, "code")


def test_an_identity_with_a_trailing_newline_is_refused_in_every_input_that_names_one() -> None:
    decisions = _decisions()
    target = _item(decisions, "C01")["targets"][0]
    target["norm_document_id"] += "\n"
    with _refused("target_value_invalid:C01"):
        _build(decisions)
    decisions = _decisions()
    _item(decisions, "C01")["targets"][0]["norm_paragraph_id_first"] += "\n"
    with _refused("target_value_invalid:C01"):
        _build(decisions)
    payload = _paragraph_payload()
    payload["paragraphs"][0]["norm_document_id"] += "\n"
    with _refused("paragraph_row_invalid"):
        _paragraphs(payload)
    payload = _paragraph_payload()
    payload["norms_snapshot_id"] += "\n"
    with _refused("paragraphs_shape_invalid"):
        _paragraphs(payload)
    maps = _build()
    with _refused("mapped_document_ids_invalid:F1"):
        check_scope_maps(_remap(maps, "F1", lambda m: m["mapped_document_ids"].__setitem__(
            0, m["mapped_document_ids"][0] + "\n")), allow_synthetic=True)


# --- the set tool binds its request to these maps -------------------------------------------------

def _request_for(mapping: dict[str, Any], *, widen: bool = False) -> dict[str, Any]:
    packed = norm_vectors.pack([1.0] + [0.0] * (DIMENSIONS - 1))
    return {
        "format": promote_cli.REQUEST_FORMAT,
        "set_id": str(NormRetrievalSetId.new()),
        "snapshot_id": mapping["norms_snapshot_id"],
        "reviewed_content_key": mapping["reviewed_content_key"],
        "embedding_build": mapping["embedding_build"],
        "chunking_profile": "characters-v2:1000",
        "independently_checked_source_digest": "1" * 64,
        "independently_checked_embedding_digest": "2" * 64,
        "designations": [
            {"document_id": document, "slug": "synthetic_slug", "designation": "SYNTH"}
            for document in mapping["mapped_document_ids"]
        ],
        "items": [{
            "item_id": item["id"],
            "query_vector_base64": norm_vectors.to_base64(packed),
            "provenance": {"query_text_sha256": "3" * 64,
                           "query_vector_sha256": norm_vectors.sha256(packed)},
            "targets": [
                {"document_id": target["norm_document_id"], "ordinal_first": target["ordinal_first"],
                 "ordinal_last": target["ordinal_last"] + (1 if widen else 0)}
                for target in item["targets"]
            ],
        } for item in mapping["items"]],
    }


def _bundle_of(tmp_path: Path, name: str, entry: ScopeMap, request: dict[str, Any]) -> Path:
    directory = tmp_path / name
    directory.mkdir()
    (directory / "map.json").write_bytes(entry.data)
    (directory / "request.json").write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
    return directory


def test_the_set_tool_accepts_each_real_map_with_a_request_that_repeats_its_targets(
    tmp_path: Path,
) -> None:
    decisions, _ = _real_like()
    for entry in build_scope_maps(decisions).maps:
        mapping = json.loads(entry.data)
        loaded = promote_cli.load_bundle(
            _bundle_of(tmp_path, entry.scope_id, entry, _request_for(mapping)), require_expected=False,
        )
        assert [item.item_id for item in loaded.request.items] == list(
            scope_membership(entry.scope_id).item_ids)
        assert loaded.request.identity.map_sha256 == entry.sha256


def test_the_set_tool_refuses_the_same_map_bytes_with_spans_widened_by_one_paragraph(
    tmp_path: Path,
) -> None:
    # The review's reproduction: same map, same `map_sha256`, 5 prompt rows became 8 and the
    # set digest changed, and the library built it. The map lists the spans; the request may not.
    decisions, _ = _real_like()
    entry = build_scope_maps(decisions).maps[0]
    mapping = json.loads(entry.data)
    promote_cli.load_bundle(_bundle_of(tmp_path, "same", entry, _request_for(mapping)),
                            require_expected=False)
    with pytest.raises(promote_cli.CliRefused) as refused:
        promote_cli.load_bundle(
            _bundle_of(tmp_path, "widened", entry, _request_for(mapping, widen=True)),
            require_expected=False,
        )
    assert refused.value.reason == "request_targets_differ_from_map"


def test_the_set_tool_refuses_a_synthetic_map_that_this_tool_wrote(tmp_path: Path) -> None:
    entry = _build().maps[0]
    mapping = json.loads(entry.data)
    assert mapping["synthetic"] is True
    with pytest.raises(promote_cli.CliRefused) as refused:
        promote_cli.load_bundle(_bundle_of(tmp_path, "synthetic", entry, _request_for(mapping)),
                                require_expected=False)
    assert refused.value.reason == "map_synthetic"


# --- build is all or nothing -------------------------------------------------------------------

def _build_args(tmp_path: Path, out: Path) -> list[str]:
    decisions, paragraphs, _ = _paths(tmp_path)
    return ["build", "--decisions", decisions, "--paragraphs", paragraphs, "--out", str(out),
            "--allow-synthetic"]


@pytest.mark.parametrize("dangling", ["pack-summary.json", "scope-F1.map.json", "scope-S2.map.json"])
def test_a_dangling_symlink_in_the_output_refuses_before_any_file_is_written(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], dangling: str,
) -> None:
    out = tmp_path / "pack"
    out.mkdir()
    (out / dangling).symlink_to(tmp_path / "nowhere")
    for _attempt in range(2):  # the second run must say the same thing, not `output_exists` later
        assert _cli(*_build_args(tmp_path, out)) == 2
        assert "REFUSED: output_exists" in capsys.readouterr().err
        assert sorted(path.name for path in out.iterdir()) == [dangling]
        assert (out / dangling).is_symlink() and not (out / dangling).exists()


@pytest.mark.parametrize("failure", [OSError(28, "No space left on device"), KeyboardInterrupt()],
                         ids=["disk_full", "interrupt"])
@pytest.mark.parametrize("existing_directory", [False, True], ids=["new_directory", "empty_directory"])
def test_a_write_that_fails_part_way_leaves_nothing_and_a_rerun_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    failure: BaseException, existing_directory: bool,
) -> None:
    out = tmp_path / "nested" / "pack"
    if existing_directory:
        out.mkdir(parents=True)
    original = Path.open

    def fail_on_the_fourth_file(self: Path, *args: Any, **kwargs: Any):
        if self.name == "scope-S1.map.json" and args[:1] == ("xb",):
            raise failure
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_on_the_fourth_file)
    argv = _build_args(tmp_path, out)
    if isinstance(failure, KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            _cli(*argv)
    else:
        assert _cli(*argv) == 2
        assert "REFUSED: output_unwritable" in capsys.readouterr().err
    assert sorted(out.iterdir()) == [] if existing_directory else not (tmp_path / "nested").exists()
    monkeypatch.undo()
    assert _cli(*argv) == 0
    assert len(list(out.iterdir())) == 7


def test_a_file_that_appears_between_the_check_and_the_create_is_never_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    out = tmp_path / "pack"
    original = Path.open

    def lose_the_race(self: Path, *args: Any, **kwargs: Any):
        if self.name == "scope-A1.map.json" and args[:1] == ("xb",):
            original(self, "wb").write(b"someone else's file")
            raise FileExistsError(17, "File exists")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", lose_the_race)
    assert _cli(*_build_args(tmp_path, out)) == 2
    assert "REFUSED: output_unwritable" in capsys.readouterr().err
    assert [path.name for path in out.iterdir()] == ["scope-A1.map.json"]
    assert (out / "scope-A1.map.json").read_bytes() == b"someone else's file"


# --- hostile input is a typed refusal, never a traceback ----------------------------------------

HUGE_INTEGER = "1" * 5_000  # beyond Python's 4,300-digit int/str conversion limit


def test_a_5000_digit_integer_is_a_typed_refusal_in_every_input_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    with _refused("decisions_json_invalid"):
        map_pack.parse_decisions(f'{{"a": {HUGE_INTEGER}}}'.encode())
    with _refused("paragraphs_json_invalid"):
        parse_paragraphs(f'{{"a": {HUGE_INTEGER}}}'.encode())
    decisions, paragraphs, out = _paths(tmp_path)
    huge = tmp_path / "huge.json"
    huge.write_text(f'{{"decision_version": {HUGE_INTEGER}}}', encoding="utf-8")
    assert _cli("build", "--decisions", str(huge), "--paragraphs", paragraphs, "--out", out,
                "--allow-synthetic") == 2
    assert "REFUSED: decisions_json_invalid" in capsys.readouterr().err
    assert not Path(out).exists()
    assert _cli(*_build_args(tmp_path, Path(out))) == 0
    capsys.readouterr()
    validate = ("validate", "--maps", out, "--paragraphs", paragraphs, "--allow-synthetic")
    pack = Path(out)
    summary, first_map = pack / "pack-summary.json", pack / "scope-F1.map.json"
    good_summary, good_map = summary.read_bytes(), first_map.read_bytes()
    summary.write_text(f'{{"review": {HUGE_INTEGER}}}', encoding="utf-8")
    assert _cli(*validate) == 2
    assert "REFUSED: summary_json_invalid" in capsys.readouterr().err
    summary.write_bytes(good_summary)
    first_map.write_text(f'{{"x": {HUGE_INTEGER}}}', encoding="utf-8")
    assert _cli(*validate) == 2
    assert "REFUSED: map_json_invalid:F1" in capsys.readouterr().err
    first_map.write_bytes(good_map)
    assert _cli(*validate) == 0


def test_a_duplicate_key_keeps_its_own_code_next_to_the_broadened_json_errors() -> None:
    # `MapPackRefused` is a `ValueError`; broadening the JSON guard must not re-label it.
    with _refused("duplicate_json_key"):
        map_pack.parse_decisions(b'{"a":1,"a":2}')
    with _refused("invalid_json_constant:NaN"):
        map_pack.parse_decisions(b'{"a":NaN}')
    with _refused("decisions_json_invalid"):
        map_pack.parse_decisions(b"[" * 500_000)
