"""Offline toolchain from recorded human decisions to the six canonical AR scope maps.

``build_scope_maps`` turns one decision record (what the owner/expert decided for each
of C01-C22) into the six map byte-strings F1/F2/A1/A2/S1/S2 of the frozen composition;
``validate_scope_maps`` proves them acceptable before anybody spends time on promotion.
Nothing here reads a database, calls a model or approves anything: the toolchain only
records a supplied attestation, never infers one, and a missing input is a refusal,
never a default. Whether the promotion builders accept the bytes is decided by those
builders; this module checks the same invariants earlier and in one place.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime
import hashlib
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Mapping, NoReturn

from auditmanager.analysis.profiles.ar_v3.norm_map.beta_sources import (
    BetaItem,
    BetaSourcePolicy,
    BetaSourcePolicyRefused,
    load_beta_source_policy,
)
from auditmanager.analysis.profiles.ar_v3.scope_partition import (
    PROMPT_CHAR_CAP,
    ScopePartitionRefused,
    plan_scope_partition,
    scope_membership,
    validate_rendered_scope,
)
from auditmanager.norms.public import EMBEDDING_PROFILE
from auditmanager.shared.identity import NormDocumentId, NormParagraphId, NormsSnapshotId


DECISIONS_VERSION: Final[str] = "ar-beta-map-decisions-v1"
PARAGRAPHS_VERSION: Final[str] = "ar-beta-map-paragraphs-v1"
MAP_SCHEMA_VERSION: Final[str] = "ar-beta-scope-map-v1"
SUMMARY_VERSION: Final[str] = "ar-beta-map-pack-summary-v1"
PENDING_EXPERT: Final[str] = "pending_expert"
ATTESTATION_RECORDED: Final[str] = "attestation_recorded"
SCOPES: Final[tuple[str, ...]] = ("F1", "F2", "A1", "A2", "S1", "S2")
ITEM_IDS: Final[tuple[str, ...]] = tuple(f"C{number:02d}" for number in range(1, 23))
MAX_MAP_BYTES: Final[int] = 10_000_000
MAX_INPUT_BYTES: Final[int] = 50_000_000
# Mirrors `norms.retrieval.ranking.BUILDER_VERSION`, which has no public name; the
# contract test compares this renderer with the real `select_prompt_part`.
_RANKING_VERSION: Final[str] = "norm-ranking-prep-v1"
_MODES: Final[tuple[str, ...]] = ("provisional_citation", "context_only")
_TARGET_KINDS: Final[tuple[str, ...]] = ("clause", "table", "range")
# Edition evidence must be page material, not a registry card or editorial note.
_EVIDENCE_KINDS: Final[frozenset[str]] = frozenset({
    "official_pdf", "official_excerpt", "public_copy",
})
_TEXT_LIMIT: Final[int] = 2_000
_SHA = re.compile(r"[0-9a-f]{64}")
_REVISION = re.compile(r"[0-9a-f]{40}")
_BUILD = re.compile(re.escape(EMBEDDING_PROFILE) + r":characters-v[12]:[1-9][0-9]*")
_BRANCH_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,31}")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")

_DECISION_KEYS: Final[frozenset[str]] = frozenset({
    "decision_version", "synthetic", "comment", "identity", "query_vectors", "items",
})
_IDENTITY_KEYS: Final[frozenset[str]] = frozenset({
    "norms_snapshot_id", "reviewed_content_key", "embedding_build", "scenario",
})
_VECTOR_DECISION_KEYS: Final[frozenset[str]] = frozenset({
    "profile", "model_revision", "sha256_by_scope",
})
_VECTOR_MAP_KEYS: Final[frozenset[str]] = frozenset({"profile", "model_revision", "sha256"})
_MAP_KEYS: Final[frozenset[str]] = frozenset({
    "map_schema_version", "scope_id", "composition_sha256", "policy_sha256", "scenario",
    "synthetic", "norms_snapshot_id", "reviewed_content_key", "embedding_build",
    "query_vectors", "mapped_document_ids", "items",
})
_BASE_ITEM_KEYS: Final[frozenset[str]] = frozenset({"id", "mode", "targets"})
_CITATION_KEYS: Final[frozenset[str]] = frozenset({"branch", "edition_evidence"})
_TARGET_KEYS: Final[frozenset[str]] = frozenset({
    "norm_document_id", "designation", "edition", "kind", "ordinal_first", "ordinal_last",
    "norm_paragraph_id_first", "norm_paragraph_id_last",
})
_BRANCH_KEYS: Final[frozenset[str]] = frozenset({"id", "applicability"})
_EVIDENCE_KEYS: Final[frozenset[str]] = frozenset({"source_id", "pages", "page_sha256"})
_REVIEW_KEYS: Final[frozenset[str]] = frozenset({
    "reviewer", "capacity", "date", "decision_ref", "map_sha256",
})
_PARAGRAPH_SET_KEYS: Final[frozenset[str]] = frozenset({
    "paragraphs_version", "synthetic", "norms_snapshot_id", "paragraphs",
})
_PARAGRAPH_KEYS: Final[frozenset[str]] = frozenset({
    "norm_document_id", "norm_paragraph_id", "designation", "title", "ordinal",
    "clause_number", "page_label", "text", "reliable",
})
_SHARED_MAP_FIELDS: Final[tuple[str, ...]] = (
    "composition_sha256", "policy_sha256", "scenario", "synthetic", "norms_snapshot_id",
    "reviewed_content_key", "embedding_build",
)
SUMMARY_FILE: Final[str] = "pack-summary.json"


class MapPackRefused(ValueError):
    """A decision, map, paragraph or pack cannot be accepted; the message is the reason code."""


def _refuse(code: str) -> NoReturn:
    raise MapPackRefused(code)


@dataclass(frozen=True, slots=True)
class ScopeMap:
    scope_id: str
    data: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


@dataclass(frozen=True, slots=True)
class ScopeMaps:
    """Six map byte-strings in frozen scope order plus the attestation, if recorded."""

    maps: tuple[ScopeMap, ...]
    review: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class Paragraph:
    document_id: str
    paragraph_id: str
    designation: str
    title: str
    ordinal: int
    clause_number: str | None
    page_label: str | None
    text: str
    reliable: bool


@dataclass(frozen=True, slots=True)
class ParagraphSet:
    snapshot_id: str
    synthetic: bool
    rows: tuple[Paragraph, ...]


@dataclass(frozen=True, slots=True)
class _PlanItem:
    item_id: str


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _refuse("duplicate_json_key")
        result[key] = value
    return result


def _reject_constant(value: str) -> NoReturn:
    _refuse(f"invalid_json_constant:{value}")


def _load_json(raw: bytes, code: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                          parse_constant=_reject_constant)
    except MapPackRefused:
        raise  # a duplicate key or a constant keeps its own code; it is a ValueError too
    except (ValueError, RecursionError) as exc:
        # Bad UTF-8, bad JSON, and the plain ValueError of a 5,000-digit integer (beyond
        # Python's int/str conversion limit) all end as the file's code, not a traceback.
        raise MapPackRefused(code) from exc


def canonical_bytes(value: Any) -> bytes:
    """Canonical UTF-8 JSON as `promotion._checked` requires: sorted, compact, NFC, no floats.

    `norms.retrieval.artifact.canonical_json_bytes` has no public name; the contract test
    holds this encoder byte-equal to it.
    """
    def check(node: Any) -> None:
        if isinstance(node, str):
            if unicodedata.normalize("NFC", node) != node:
                _refuse("non_nfc_text")
        elif isinstance(node, dict):
            for key, child in node.items():
                if not isinstance(key, str):
                    _refuse("json_key_not_text")
                check(key)
                check(child)
        elif isinstance(node, (list, tuple)):
            for child in node:
                check(child)
        elif node is None or isinstance(node, (bool, int)):
            return
        else:
            _refuse("unsupported_json_value")

    try:
        check(value)
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":")).encode("utf-8")
    except RecursionError as exc:
        raise MapPackRefused("json_too_deep") from exc


def _nfc_text(value: object, code: str, *, strip: bool = True, limit: int = _TEXT_LIMIT) -> str:
    if (not isinstance(value, str) or not value or len(value) > limit
            or unicodedata.normalize("NFC", value) != value
            or (strip and value != value.strip())):
        _refuse(code)
    return value


def _sha(value: object, code: str) -> str:
    if not isinstance(value, str) or _SHA.fullmatch(value) is None:
        _refuse(code)
    return value


def _ident(value: object, identity: type, code: str) -> str:
    # An identity is the whole string: a line break is never part of one, whatever the shared
    # parser's anchoring accepts (it used to take a trailing newline).
    if not isinstance(value, str) or "\n" in value:
        _refuse(code)
    try:
        identity.parse(value)  # type: ignore[attr-defined]
    except (TypeError, ValueError):
        _refuse(code)
    return value


def _policy() -> BetaSourcePolicy:
    try:
        return load_beta_source_policy()
    except BetaSourcePolicyRefused as exc:
        raise MapPackRefused(f"policy_unavailable:{exc}") from exc


def _synthetic_flag(value: object, allow_synthetic: bool, code: str) -> bool:
    if type(value) is not bool:
        _refuse(code)
    if value and not allow_synthetic:
        _refuse("synthetic_refused")
    return value


# ---------------------------------------------------------------- items

def _check_targets(targets: object, item_id: str) -> None:
    if not isinstance(targets, list) or not targets:
        _refuse(f"targets_missing:{item_id}")
    keys: list[tuple[str, int, int]] = []
    for target in targets:
        if not isinstance(target, dict) or set(target) != _TARGET_KEYS:
            _refuse(f"target_shape_invalid:{item_id}")
        code = f"target_value_invalid:{item_id}"
        document = _ident(target["norm_document_id"], NormDocumentId, code)
        _ident(target["norm_paragraph_id_first"], NormParagraphId, code)
        _ident(target["norm_paragraph_id_last"], NormParagraphId, code)
        _nfc_text(target["designation"], code)
        _nfc_text(target["edition"], code)
        first, last = target["ordinal_first"], target["ordinal_last"]
        if (target["kind"] not in _TARGET_KINDS or type(first) is not int
                or type(last) is not int or first < 0 or last < first):
            _refuse(code)
        keys.append((document, first, last))
    if keys != sorted(set(keys)):
        _refuse(f"targets_not_canonical:{item_id}")


def _check_branch(branch: object, item_id: str) -> None:
    code = f"branch_invalid:{item_id}"
    if (not isinstance(branch, dict) or set(branch) != _BRANCH_KEYS
            or not isinstance(branch["id"], str) or _BRANCH_ID.fullmatch(branch["id"]) is None):
        _refuse(code)
    _nfc_text(branch["applicability"], code)


def _check_evidence(
    evidence: object, item_id: str, policy_item: BetaItem, policy: BetaSourcePolicy,
) -> None:
    if not isinstance(evidence, list):
        _refuse(f"edition_evidence_invalid:{item_id}")
    keys: list[tuple[str, str]] = []
    for entry in evidence:
        if not isinstance(entry, dict) or set(entry) != _EVIDENCE_KEYS:
            _refuse(f"edition_evidence_invalid:{item_id}")
        source_id = entry["source_id"]
        if (not isinstance(source_id, str) or source_id not in policy_item.source_ids
                or policy.sources[source_id].kind not in _EVIDENCE_KINDS):
            _refuse(f"edition_evidence_source_invalid:{item_id}")
        _nfc_text(entry["pages"], f"edition_evidence_invalid:{item_id}")
        keys.append((source_id, _sha(entry["page_sha256"], f"edition_evidence_invalid:{item_id}")))
    if keys != sorted(set(keys)):
        _refuse(f"edition_evidence_not_canonical:{item_id}")


def _check_item(
    item: object, item_id: str, policy_item: BetaItem, policy: BetaSourcePolicy,
) -> None:
    if not isinstance(item, dict):
        _refuse(f"item_shape_invalid:{item_id}")
    mode = item.get("mode")
    if mode not in _MODES:
        _refuse(f"item_mode_invalid:{item_id}")
    # The policy fixes some topics as context_only; a decision may only be stricter.
    if policy_item.mode == "context_only" and mode != "context_only":
        _refuse(f"context_only_upgrade_refused:{item_id}")
    if mode == "context_only" and set(item) & _CITATION_KEYS:
        _refuse(f"context_only_carries_citation:{item_id}")
    expected = _BASE_ITEM_KEYS | (_CITATION_KEYS if mode == "provisional_citation" else frozenset())
    if set(item) != expected:
        _refuse(f"item_keys_invalid:{item_id}")
    if item["id"] != item_id:
        _refuse(f"item_id_invalid:{item_id}")
    _check_targets(item["targets"], item_id)
    if mode == "provisional_citation":
        _check_branch(item["branch"], item_id)
        _check_evidence(item["edition_evidence"], item_id, policy_item, policy)


def _mapped_document_ids(items: list[dict[str, Any]]) -> list[str]:
    return sorted({target["norm_document_id"] for item in items for target in item["targets"]})


def _target_order(target: dict[str, Any]) -> tuple[str, int, int]:
    return (target["norm_document_id"], target["ordinal_first"], target["ordinal_last"])


def _evidence_order(entry: dict[str, Any]) -> tuple[str, str]:
    return (entry["source_id"], entry["page_sha256"])


def _ordered_item(item: dict[str, Any]) -> dict[str, Any]:
    """Sort list-valued parts so input order cannot change bytes; leave malformed parts to the checker."""
    ordered = dict(item)
    for key, order in (("targets", _target_order), ("edition_evidence", _evidence_order)):
        entries = ordered.get(key)
        if isinstance(entries, list) and all(isinstance(entry, dict) for entry in entries):
            try:
                ordered[key] = sorted(entries, key=order)
            except (KeyError, TypeError):
                pass
    return ordered


# ---------------------------------------------------------------- maps

def require_distinct_map_digests(digests: tuple[str, ...]) -> None:
    """0023's unique key needs a different map digest for every scope."""
    if len(set(digests)) != len(digests):
        _refuse("map_digests_not_distinct")


def _parse_map(
    scope_id: str, data: object, policy: BetaSourcePolicy,
    policy_items: Mapping[str, BetaItem], allow_synthetic: bool,
) -> dict[str, Any]:
    if type(data) is not bytes or not 1 <= len(data) <= MAX_MAP_BYTES:
        _refuse(f"map_bytes_invalid:{scope_id}")
    mapping = _load_json(data, f"map_json_invalid:{scope_id}")
    if not isinstance(mapping, dict) or canonical_bytes(mapping) != data:
        _refuse(f"map_not_canonical:{scope_id}")
    if set(mapping) != _MAP_KEYS:
        _refuse(f"map_keys_invalid:{scope_id}")
    membership = scope_membership(scope_id)
    if (mapping["map_schema_version"] != MAP_SCHEMA_VERSION
            or mapping["scope_id"] != scope_id
            or mapping["composition_sha256"] != membership.composition_sha256
            or mapping["policy_sha256"] != policy.sha256
            or mapping["scenario"] != policy.scenario):
        _refuse(f"map_identity_invalid:{scope_id}")
    synthetic = _synthetic_flag(mapping["synthetic"], allow_synthetic,
                                f"map_identity_invalid:{scope_id}")
    code = f"map_snapshot_invalid:{scope_id}"
    _ident(mapping["norms_snapshot_id"], NormsSnapshotId, code)
    if not synthetic and mapping["norms_snapshot_id"] != policy.snapshot_id:
        _refuse("snapshot_not_policy_snapshot")
    _nfc_text(mapping["reviewed_content_key"], code)
    if (not isinstance(mapping["embedding_build"], str)
            or _BUILD.fullmatch(mapping["embedding_build"]) is None):
        _refuse(code)
    vectors = mapping["query_vectors"]
    if (not isinstance(vectors, dict) or set(vectors) != _VECTOR_MAP_KEYS
            or vectors["profile"] != EMBEDDING_PROFILE):
        _refuse(f"query_vectors_invalid:{scope_id}")
    if (not isinstance(vectors["model_revision"], str)
            or _REVISION.fullmatch(vectors["model_revision"]) is None):
        _refuse(f"query_vectors_invalid:{scope_id}")
    _sha(vectors["sha256"], f"query_vectors_invalid:{scope_id}")
    items = mapping["items"]
    if not isinstance(items, list) or len(items) != len(membership.item_ids):
        _refuse(f"map_items_invalid:{scope_id}")
    for item, item_id in zip(items, membership.item_ids):
        _check_item(item, item_id, policy_items[item_id], policy)
    mapped = mapping["mapped_document_ids"]
    code = f"mapped_document_ids_invalid:{scope_id}"
    if (not isinstance(mapped, list) or not mapped
            or any(not isinstance(document, str) for document in mapped)
            or len(set(mapped)) != len(mapped)):
        _refuse(code)
    for document in mapped:
        _ident(document, NormDocumentId, code)
    if mapped != _mapped_document_ids(items):
        _refuse(f"mapped_documents_differ_from_targets:{scope_id}")
    return mapping


def _check_review(review: object, shas: dict[str, str], synthetic: bool) -> None:
    if review is None:
        return
    if not isinstance(review, dict) or set(review) != _REVIEW_KEYS:
        _refuse("attestation_incomplete")
    for key in ("reviewer", "capacity", "decision_ref"):
        _nfc_text(review[key], "attestation_incomplete")
    date = review["date"]
    if not isinstance(date, str) or _DATE.fullmatch(date) is None:
        _refuse("attestation_incomplete")
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        _refuse("attestation_incomplete")
    if synthetic:
        _refuse("synthetic_cannot_be_attested")
    if review["map_sha256"] != shas:
        _refuse("attestation_map_digest_mismatch")


def check_scope_maps(
    maps: ScopeMaps, *, allow_synthetic: bool = False,
) -> tuple[dict[str, Any], ...]:
    """Check everything that needs only the six byte-strings; return the parsed maps."""
    if (not isinstance(maps, ScopeMaps) or not isinstance(maps.maps, tuple)
            or tuple(getattr(entry, "scope_id", None) for entry in maps.maps) != SCOPES):
        _refuse("scope_set_invalid")
    policy = _policy()
    policy_items = {item.item_id: item for item in policy.items}
    parsed = tuple(
        _parse_map(entry.scope_id, entry.data, policy, policy_items, allow_synthetic)
        for entry in maps.maps
    )
    for field in _SHARED_MAP_FIELDS:
        if len({json.dumps(mapping[field]) for mapping in parsed}) != 1:
            _refuse(f"pack_identity_inconsistent:{field}")
    if len({(mapping["query_vectors"]["profile"], mapping["query_vectors"]["model_revision"])
            for mapping in parsed}) != 1:
        _refuse("pack_identity_inconsistent:query_vectors")
    require_distinct_map_digests(tuple(entry.sha256 for entry in maps.maps))
    _check_review(maps.review, {entry.scope_id: entry.sha256 for entry in maps.maps},
                  parsed[0]["synthetic"])
    return parsed


def build_scope_maps(
    decisions: Mapping[str, Any], *, allow_synthetic: bool = False,
) -> ScopeMaps:
    """Assemble the six canonical maps from one decision record; refuse, never repair."""
    policy = _policy()
    policy_items = {item.item_id: item for item in policy.items}
    if not isinstance(decisions, dict) or set(decisions) not in (
        _DECISION_KEYS, _DECISION_KEYS | {"review"},
    ):
        _refuse("decisions_shape_invalid")
    if decisions["decision_version"] != DECISIONS_VERSION:
        _refuse("decisions_version_invalid")
    synthetic = _synthetic_flag(decisions["synthetic"], allow_synthetic, "synthetic_flag_invalid")
    _nfc_text(decisions["comment"], "decisions_comment_invalid")
    identity = decisions["identity"]
    if not isinstance(identity, dict) or set(identity) != _IDENTITY_KEYS:
        _refuse("identity_shape_invalid")
    vectors = decisions["query_vectors"]
    if not isinstance(vectors, dict) or set(vectors) != _VECTOR_DECISION_KEYS:
        _refuse("query_vectors_shape_invalid")
    by_scope = vectors["sha256_by_scope"]
    if not isinstance(by_scope, dict) or set(by_scope) != set(SCOPES):
        _refuse("query_vectors_scopes_invalid")
    rows = decisions["items"]
    if not isinstance(rows, list):
        _refuse("items_shape_invalid")
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_id = row.get("id") if isinstance(row, dict) else None
        if row_id not in ITEM_IDS:
            _refuse("item_unknown")
        if row_id in by_id:
            _refuse(f"item_duplicate:{row_id}")
        by_id[row_id] = row
    missing = [item_id for item_id in ITEM_IDS if item_id not in by_id]
    if missing:
        _refuse("item_missing:" + ",".join(missing))
    built: list[ScopeMap] = []
    for scope_id in SCOPES:
        membership = scope_membership(scope_id)
        items: list[dict[str, Any]] = []
        for item_id in membership.item_ids:
            item = _ordered_item(by_id[item_id])
            _check_item(item, item_id, policy_items[item_id], policy)
            items.append(item)
        mapping = {
            "map_schema_version": MAP_SCHEMA_VERSION,
            "scope_id": scope_id,
            "composition_sha256": membership.composition_sha256,
            "policy_sha256": policy.sha256,
            "scenario": identity["scenario"],
            "synthetic": synthetic,
            "norms_snapshot_id": identity["norms_snapshot_id"],
            "reviewed_content_key": identity["reviewed_content_key"],
            "embedding_build": identity["embedding_build"],
            "query_vectors": {
                "profile": vectors["profile"],
                "model_revision": vectors["model_revision"],
                "sha256": by_scope[scope_id],
            },
            "mapped_document_ids": _mapped_document_ids(items),
            "items": items,
        }
        built.append(ScopeMap(scope_id, canonical_bytes(mapping)))
    maps = ScopeMaps(tuple(built), decisions.get("review"))
    check_scope_maps(maps, allow_synthetic=allow_synthetic)
    return maps


# ---------------------------------------------------------------- paragraphs and budget

def parse_paragraphs(raw: bytes) -> ParagraphSet:
    """Strictly read the supplied paragraph rows used to render and measure each scope."""
    payload = _load_json(raw, "paragraphs_json_invalid")
    if not isinstance(payload, dict) or set(payload) != _PARAGRAPH_SET_KEYS:
        _refuse("paragraphs_shape_invalid")
    if payload["paragraphs_version"] != PARAGRAPHS_VERSION:
        _refuse("paragraphs_version_invalid")
    synthetic = payload["synthetic"]
    if type(synthetic) is not bool:
        _refuse("paragraphs_shape_invalid")
    snapshot_id = _ident(payload["norms_snapshot_id"], NormsSnapshotId, "paragraphs_shape_invalid")
    entries = payload["paragraphs"]
    if not isinstance(entries, list) or not entries:
        _refuse("paragraphs_shape_invalid")
    rows: list[Paragraph] = []
    seen_ordinals: set[tuple[str, int]] = set()
    seen_ids: set[str] = set()
    for entry in entries:
        code = "paragraph_row_invalid"
        if not isinstance(entry, dict) or set(entry) != _PARAGRAPH_KEYS:
            _refuse(code)
        ordinal = entry["ordinal"]
        if type(ordinal) is not int or ordinal < 0 or type(entry["reliable"]) is not bool:
            _refuse(code)
        for optional in ("clause_number", "page_label"):
            if entry[optional] is not None:
                _nfc_text(entry[optional], code)
        row = Paragraph(
            document_id=_ident(entry["norm_document_id"], NormDocumentId, code),
            paragraph_id=_ident(entry["norm_paragraph_id"], NormParagraphId, code),
            designation=_nfc_text(entry["designation"], code),
            title=_nfc_text(entry["title"], code),
            ordinal=ordinal, clause_number=entry["clause_number"],
            page_label=entry["page_label"],
            text=_nfc_text(entry["text"], code, strip=False, limit=1_000_000),
            reliable=entry["reliable"],
        )
        if (row.document_id, row.ordinal) in seen_ordinals or row.paragraph_id in seen_ids:
            _refuse("paragraph_row_duplicate")
        seen_ordinals.add((row.document_id, row.ordinal))
        seen_ids.add(row.paragraph_id)
        rows.append(row)
    return ParagraphSet(snapshot_id, synthetic, tuple(rows))


def _render_prompt_part(mapping: dict[str, Any], by_key: Mapping[tuple[str, int], Paragraph]) -> str:
    """Target-only prompt part, serialised exactly as the W57 renderer does with zero windows."""
    rendered: list[dict[str, Any]] = []
    for item in mapping["items"]:
        item_id = item["id"]
        keys: set[tuple[str, int]] = set()
        for target in item["targets"]:
            document, first, last = (
                target["norm_document_id"], target["ordinal_first"], target["ordinal_last"],
            )
            if (getattr(by_key.get((document, first)), "paragraph_id", None)
                    != target["norm_paragraph_id_first"]
                    or getattr(by_key.get((document, last)), "paragraph_id", None)
                    != target["norm_paragraph_id_last"]):
                _refuse(f"target_not_in_paragraphs:{item_id}")
            for ordinal in range(first, last + 1):
                row = by_key.get((document, ordinal))
                if row is None:
                    _refuse(f"target_paragraph_missing:{item_id}")
                if not row.reliable:
                    _refuse(f"target_paragraph_unreliable:{item_id}")
                if row.designation != target["designation"]:
                    _refuse(f"target_designation_mismatch:{item_id}")
                keys.add((document, ordinal))
        for row in sorted((by_key[key] for key in keys),
                          key=lambda row: (row.designation, row.ordinal, row.document_id)):
            rendered.append({
                "item_id": item_id, "label": f"N{len(rendered) + 1}",
                "norm_document_id": row.document_id, "norm_paragraph_id": row.paragraph_id,
                "designation": row.designation, "title": row.title, "ordinal": row.ordinal,
                "clause_number": row.clause_number, "page_label": row.page_label,
                "text": row.text,
                "text_sha256": hashlib.sha256(row.text.encode("utf-8")).hexdigest(),
            })
    return json.dumps({"builder_version": _RANKING_VERSION, "paragraphs": rendered},
                      ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validate_scope_maps(
    maps: ScopeMaps, paragraphs: ParagraphSet, *, allow_synthetic: bool = False,
) -> dict[str, Any]:
    """Prove the six maps acceptable and return the pack summary (never approval)."""
    parsed = check_scope_maps(maps, allow_synthetic=allow_synthetic)
    if not isinstance(paragraphs, ParagraphSet):
        _refuse("paragraphs_required")
    if paragraphs.synthetic != parsed[0]["synthetic"]:
        _refuse("paragraphs_synthetic_mismatch")
    if paragraphs.snapshot_id != parsed[0]["norms_snapshot_id"]:
        _refuse("paragraphs_snapshot_mismatch")
    by_key = {(row.document_id, row.ordinal): row for row in paragraphs.rows}
    plan = plan_scope_partition(tuple(_PlanItem(item_id) for item_id in ITEM_IDS))
    scopes: list[dict[str, Any]] = []
    for entry, mapping in zip(maps.maps, parsed):
        part = _render_prompt_part(mapping, by_key)
        try:
            rendered = validate_rendered_scope(plan, entry.scope_id, part)
        except ScopePartitionRefused as exc:
            raise MapPackRefused(
                f"prompt_part_over_cap:{entry.scope_id}:{len(part)}>{PROMPT_CHAR_CAP}") from exc
        items = mapping["items"]
        scopes.append({
            "scope_id": entry.scope_id,
            "item_ids": [item["id"] for item in items],
            "map_sha256": entry.sha256,
            "map_bytes": len(entry.data),
            "mapped_document_count": len(mapping["mapped_document_ids"]),
            "prompt_part_characters": rendered.prompt_part_characters,
            "prompt_part_sha256": rendered.prompt_part_sha256,
            "provisional_item_ids": [
                item["id"] for item in items if item["mode"] == "provisional_citation"],
            "context_only_item_ids": [
                item["id"] for item in items if item["mode"] == "context_only"],
            "edition_evidence_missing": [
                item["id"] for item in items
                if item["mode"] == "provisional_citation" and not item["edition_evidence"]],
        })
    review = None if maps.review is None else dict(maps.review)
    return {
        "summary_version": SUMMARY_VERSION,
        "composition_sha256": parsed[0]["composition_sha256"],
        "policy_sha256": parsed[0]["policy_sha256"],
        "synthetic": parsed[0]["synthetic"],
        "review_state": PENDING_EXPERT if review is None else ATTESTATION_RECORDED,
        "review": review,
        "prompt_part_cap": PROMPT_CHAR_CAP,
        "prompt_part_basis": "target_rows_only_zero_retrieved_windows",
        "scopes": scopes,
    }


def render_summary(summary: Mapping[str, Any]) -> bytes:
    return (json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def parse_decisions(raw: bytes) -> dict[str, Any]:
    payload = _load_json(raw, "decisions_json_invalid")
    if not isinstance(payload, dict):
        _refuse("decisions_shape_invalid")
    return payload


# ---------------------------------------------------------------- files and CLI

def _read(path: Path) -> bytes:
    try:
        with path.open("rb") as handle:
            data = handle.read(MAX_INPUT_BYTES + 1)
    except OSError as exc:
        raise MapPackRefused(f"file_unreadable:{path.name}") from exc
    if len(data) > MAX_INPUT_BYTES:
        _refuse(f"file_too_large:{path.name}")
    return data


def _map_file(directory: Path, scope_id: str) -> Path:
    return directory / f"scope-{scope_id}.map.json"


def write_pack(directory: Path, maps: ScopeMaps, summary: Mapping[str, Any]) -> None:
    """Write seven new files, all or none; an existing name is a refusal, never an overwrite.

    Every target is looked at with ``lstat`` first, so a dangling symlink counts as taken and
    nothing is written. Each file is created exclusively (``xb``); if any step still fails, or
    the process is interrupted, every file and directory this call created is removed again, so
    a re-run starts from the same state and a half-written pack never exists to be validated.
    """
    files = [(_map_file(directory, entry.scope_id), entry.data) for entry in maps.maps]
    files.append((directory / SUMMARY_FILE, render_summary(summary)))
    created: list[Path] = []
    new_directories: list[Path] = []
    try:
        if any(os.path.lexists(path) for path, _ in files):
            _refuse("output_exists")
        missing = directory
        while not os.path.lexists(missing):
            new_directories.append(missing)
            missing = missing.parent
        directory.mkdir(parents=True, exist_ok=True)
        for path, data in files:
            with path.open("xb") as handle:
                # Recorded only once the exclusive create succeeded: never a stranger's file.
                created.append(path)
                handle.write(data)
    except BaseException as exc:
        for path in created:
            with contextlib.suppress(OSError):
                path.unlink()
        for path in new_directories:  # deepest first: the list was built from the leaf upward
            with contextlib.suppress(OSError):
                path.rmdir()
        if isinstance(exc, OSError):
            raise MapPackRefused("output_unwritable") from exc
        raise


def read_pack(directory: Path) -> tuple[ScopeMaps, bytes]:
    """Read the six maps and the summary; the recorded attestation lives only in the summary."""
    summary_bytes = _read(directory / SUMMARY_FILE)
    summary = _load_json(summary_bytes, "summary_json_invalid")
    if not isinstance(summary, dict) or "review" not in summary:
        _refuse("summary_shape_invalid")
    maps = tuple(ScopeMap(scope_id, _read(_map_file(directory, scope_id))) for scope_id in SCOPES)
    return ScopeMaps(maps, summary["review"]), summary_bytes


def _report(summary: Mapping[str, Any]) -> str:
    lines = [f"{scope['scope_id']} {scope['map_sha256']} {scope['prompt_part_characters']}"
             for scope in summary["scopes"]]
    lines.append(f"composition {summary['composition_sha256']}")
    lines.append(f"review_state {summary['review_state']}")
    return "\n".join(lines)


def _run_build(args: argparse.Namespace) -> str:
    maps = build_scope_maps(parse_decisions(_read(args.decisions)),
                            allow_synthetic=args.allow_synthetic)
    summary = validate_scope_maps(maps, parse_paragraphs(_read(args.paragraphs)),
                                  allow_synthetic=args.allow_synthetic)
    write_pack(args.out, maps, summary)
    return _report(summary)


def _run_validate(args: argparse.Namespace) -> str:
    maps, recorded = read_pack(args.maps)
    summary = validate_scope_maps(maps, parse_paragraphs(_read(args.paragraphs)),
                                  allow_synthetic=args.allow_synthetic)
    if render_summary(summary) != recorded:
        _refuse("summary_differs_from_maps")
    return _report(summary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="map_pack", description="Build and validate the six AR scope maps offline.")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="decisions + paragraphs -> six maps + summary")
    build.add_argument("--decisions", type=Path, required=True)
    build.add_argument("--paragraphs", type=Path, required=True)
    build.add_argument("--out", type=Path, required=True)
    validate = commands.add_parser("validate", help="re-check a written pack")
    validate.add_argument("--maps", type=Path, required=True)
    validate.add_argument("--paragraphs", type=Path, required=True)
    for command in (build, validate):
        command.add_argument("--allow-synthetic", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = _run_build(args) if args.command == "build" else _run_validate(args)
    except MapPackRefused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(report)
    return 0


__all__ = [
    "ATTESTATION_RECORDED", "DECISIONS_VERSION", "ITEM_IDS", "MAP_SCHEMA_VERSION",
    "MapPackRefused", "PARAGRAPHS_VERSION", "PENDING_EXPERT", "Paragraph", "ParagraphSet",
    "SCOPES", "SUMMARY_FILE", "SUMMARY_VERSION", "ScopeMap", "ScopeMaps", "build_scope_maps",
    "canonical_bytes", "check_scope_maps", "main", "parse_decisions", "parse_paragraphs",
    "read_pack", "render_summary", "require_distinct_map_digests", "validate_scope_maps",
    "write_pack",
]


if __name__ == "__main__":
    raise SystemExit(main())
