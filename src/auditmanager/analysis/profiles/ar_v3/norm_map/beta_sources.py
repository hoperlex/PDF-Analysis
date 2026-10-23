"""Validate the exact AR beta source policy before forming any normative map.

The policy reports source availability, not legal applicability. In particular,
``provisional_citation`` only permits an expert-reviewed beta candidate; it
never proves a current edition or authorizes publication by itself.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, Mapping
from urllib.parse import urlparse

from auditmanager.analysis.profiles.ar_v3.scope_partition import scope_membership


POLICY_PATH: Final[Path] = Path(__file__).with_name("beta_sources.json")
POLICY_VERSION: Final[str] = "ar-beta-source-policy-v1"
SNAPSHOT_ID: Final[str] = "ns_01M59N8QNBVN91ACA2HCE6VE74"
COMPOSITION_SHA256: Final[str] = "79396188486c430729213279fb7c1c8fca7c13ede3f3f13388d06d9f93bbb781"
POLICY_SHA256: Final[str] = "ca6a41327a8c6af7679b413434651475b6615786a1b1724e571e0420b6b3a51d"
_IDS: Final[tuple[str, ...]] = tuple(f"C{index:02d}" for index in range(1, 23))
_SCOPES: Final[tuple[str, ...]] = ("F1", "F2", "A1", "A2", "S1", "S2")
_MODES: Final[frozenset[str]] = frozenset({"provisional_citation", "context_only"})
_KINDS: Final[frozenset[str]] = frozenset({
    "local_bundle", "official_pdf", "official_excerpt", "official_editorial",
    "official_metadata", "public_copy",
})
_TEXT_SOURCES: Final[frozenset[str]] = frozenset({
    "official_pdf", "official_excerpt", "public_copy",
})
_BLOCKED_ITEMS: Final[frozenset[str]] = frozenset({"C05", "C06", "C08", "C09", "C10", "C15", "C21", "C22"})
_SHA = re.compile(r"[0-9a-f]{64}\Z")


class BetaSourcePolicyRefused(ValueError):
    """An incomplete or altered policy cannot authorize a beta citation."""


@dataclass(frozen=True, slots=True)
class BetaSource:
    source_id: str
    kind: str
    url: str | None
    sha256: str | None


@dataclass(frozen=True, slots=True)
class BetaItem:
    item_id: str
    scope_id: str
    mode: str
    reason: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BetaSourcePolicy:
    sha256: str
    snapshot_id: str
    composition_sha256: str
    sources: Mapping[str, BetaSource]
    items: tuple[BetaItem, ...]

    def group(self, scope_id: str) -> tuple[BetaItem, ...]:
        scope_membership(scope_id)
        return tuple(item for item in self.items if item.scope_id == scope_id)

    def provisional_item_ids(self, scope_id: str) -> tuple[str, ...]:
        """Return candidates only; a later map/set/Attempt gate remains required."""
        return tuple(item.item_id for item in self.group(scope_id)
                     if item.mode == "provisional_citation")

    def context_only_item_ids(self, scope_id: str) -> tuple[str, ...]:
        return tuple(item.item_id for item in self.group(scope_id)
                     if item.mode == "context_only")


def _refuse(reason: str) -> None:
    raise BetaSourcePolicyRefused(reason)


def _source(source_id: str, value: object) -> BetaSource:
    if not isinstance(source_id, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]+", source_id):
        _refuse("source_id_invalid")
    if not isinstance(value, dict) or set(value) not in (
        {"kind", "url"}, {"kind", "sha256"},
    ):
        _refuse("source_shape_invalid")
    kind = value["kind"]
    if kind not in _KINDS:
        _refuse("source_kind_invalid")
    url = value.get("url")
    sha256 = value.get("sha256")
    if kind == "local_bundle":
        if not isinstance(sha256, str) or _SHA.fullmatch(sha256) is None:
            _refuse("local_source_digest_invalid")
    else:
        if not isinstance(url, str):
            _refuse("source_url_invalid")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            _refuse("source_url_invalid")
    return BetaSource(source_id, kind, url, sha256)


def load_beta_source_policy(path: Path | None = None) -> BetaSourcePolicy:
    """Load only the frozen, canonical policy shipped with this profile."""
    if path is None:
        path = POLICY_PATH
    if path != POLICY_PATH:
        _refuse("policy_path_invalid")
    try:
        data = path.read_bytes()
        document = json.loads(data.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BetaSourcePolicyRefused("policy_unavailable") from exc
    if not isinstance(document, dict):
        _refuse("policy_shape_invalid")
    canonical = json.dumps(document, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    if data != canonical + b"\n" or digest != POLICY_SHA256:
        _refuse("policy_digest_invalid")
    if set(document) != {"policy_version", "snapshot_id", "composition_sha256", "sources", "items"}:
        _refuse("policy_shape_invalid")
    if (document["policy_version"] != POLICY_VERSION
            or document["snapshot_id"] != SNAPSHOT_ID
            or document["composition_sha256"] != COMPOSITION_SHA256):
        _refuse("policy_identity_invalid")
    source_rows = document["sources"]
    if not isinstance(source_rows, dict) or not source_rows:
        _refuse("sources_missing")
    sources = {source_id: _source(source_id, value)
               for source_id, value in source_rows.items()}
    rows = document["items"]
    if not isinstance(rows, list) or len(rows) != len(_IDS):
        _refuse("item_count_invalid")
    items: list[BetaItem] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {"id", "mode", "reason", "sources"}:
            _refuse("item_shape_invalid")
        item_id = row["id"]
        if item_id != _IDS[index] or row["mode"] not in _MODES:
            _refuse("item_identity_or_mode_invalid")
        if not isinstance(row["reason"], str) or len(row["reason"].strip()) < 20:
            _refuse("item_reason_missing")
        source_ids = row["sources"]
        if (not isinstance(source_ids, list) or not source_ids
                or any(not isinstance(source_id, str) or source_id not in sources
                       for source_id in source_ids)
                or len(source_ids) != len(set(source_ids))):
            _refuse("item_sources_invalid")
        selected_kinds = {sources[source_id].kind for source_id in source_ids}
        if "local_bundle" not in selected_kinds:
            _refuse("canonical_source_missing")
        if (item_id in _BLOCKED_ITEMS and row["mode"] != "context_only"):
            _refuse("blocked_item_cannot_cite")
        if row["mode"] == "provisional_citation" and not selected_kinds.intersection(_TEXT_SOURCES):
            _refuse("provisional_text_source_missing")
        scope = next(scope_id for scope_id in _SCOPES
                     if item_id in scope_membership(scope_id).item_ids)
        items.append(BetaItem(item_id, scope, row["mode"], row["reason"],
                              tuple(source_ids)))
    for scope_id in _SCOPES:
        if tuple(item.item_id for item in items if item.scope_id == scope_id) != scope_membership(scope_id).item_ids:
            _refuse("scope_totality_invalid")
    if set(sources) != {source_id for item in items for source_id in item.source_ids}:
        _refuse("unused_source_invalid")
    return BetaSourcePolicy(digest, SNAPSHOT_ID, COMPOSITION_SHA256,
                            MappingProxyType(sources), tuple(items))


__all__ = ["BetaItem", "BetaSource", "BetaSourcePolicy", "BetaSourcePolicyRefused",
           "COMPOSITION_SHA256", "POLICY_SHA256", "load_beta_source_policy"]
