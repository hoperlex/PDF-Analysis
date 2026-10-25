"""The sealed AR v3 beta reviewed-pack manifest: how a reviewed pack reaches the server.

``TrustedPackRegistry`` is server-owned and the API cannot add a candidate to it. This module
is the one installer. An operator seals a manifest from six already-verified retrieval sets
(``v3_pack_cli seal``) and the composition root loads it at process start from the file named
by ``AR_V3_BETA_PACK_MANIFEST``. No variable means the empty registry, exactly as before: group
starts then refuse with ``DEPENDENCY_UNAVAILABLE / ar_v3_trusted_pack``. A variable that is set
and names anything the loader cannot accept refuses the start; the empty registry is never a
fallback for a manifest that was meant to install a pack.

The manifest carries the reviewer's attestation as a record. The loader checks that it is
present and shaped; it never infers that anyone approved anything. It also recomputes
``TrustedPack.sha256`` and compares it with the sealed ``pack_sha256``, so a hand-edited scope
is refused unless the editor also forged the digest -- which is no review.

Pure: no database, no network. Reading the file is the only effect, and only ``load_*`` has it.
"""

from __future__ import annotations

import errno
import json
import os
import re
import stat
from dataclasses import dataclass
from datetime import date
from typing import Any, Final

from auditmanager.norms.public import EMBEDDING_PROFILE, SetIdentity
from auditmanager.runs.v3_group import SCOPES, ReviewedScope, TrustedPack, TrustedPackRegistry
from auditmanager.shared.errors import DomainError
from auditmanager.shared.identity import NormRetrievalSetId

#: The one environment variable that names a sealed manifest. Absent or blank: no pack.
PACK_MANIFEST_ENV: Final = "AR_V3_BETA_PACK_MANIFEST"
MANIFEST_FORMAT: Final = "ar-v3-beta-reviewed-pack-manifest/1"
#: A manifest is six short scopes and a review record; more than this is not one.
MAX_MANIFEST_BYTES: Final = 64 * 1024

_ROOT_KEYS: Final = frozenset({
    "format", "analysis_profile_id", "prompt_bundle_id", "pack_sha256", "review", "scopes",
})
_REVIEW_KEYS: Final = frozenset({
    "reviewer", "capacity", "reviewed_at", "decision_ref", "scope_statement",
})
_SCOPE_KEYS: Final = frozenset({
    "scope_id", "map_sha256", "snapshot_id", "reviewed_content_key", "embedding_build",
    "builder_version", "chunking_profile", "set_id", "set_sha256",
})
_SHA256 = re.compile(r"[0-9a-f]{64}")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


class PackManifestRefused(ValueError):
    """A manifest, or the file that should hold one, cannot install a pack.

    ``reason`` is a stable token; ``detail`` names the object, key or field at fault and never
    carries a value read from the manifest or a path.
    """

    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}" if detail else reason)


@dataclass(frozen=True, slots=True)
class ReviewAttestation:
    """A human decision recorded with the pack. Presence and shape are all that is checked."""

    reviewer: str
    capacity: str
    reviewed_at: str
    decision_ref: str
    scope_statement: str


@dataclass(frozen=True, slots=True)
class ParsedPackManifest:
    pack: TrustedPack
    review: ReviewAttestation

    @property
    def registry(self) -> TrustedPackRegistry:
        return TrustedPackRegistry(
            TrustedPackRegistry.empty().registry_version, (self.pack,),
        )


def _refuse_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    keys = [key for key, _ in pairs]
    if len(set(keys)) != len(keys):
        raise PackManifestRefused("manifest_not_json", "duplicate object key")
    return dict(pairs)


def _refuse_constant(_name: str) -> Any:
    raise PackManifestRefused("manifest_not_json", "non-finite number")


def _object(value: Any, where: str, keys: frozenset[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PackManifestRefused("manifest_keys", f"{where} is not an object")
    if set(value) != keys:
        missing = ",".join(sorted(keys - set(value)))
        unknown = ",".join(sorted(str(key) for key in set(value) - keys))
        raise PackManifestRefused(
            "manifest_keys", f"{where} missing=[{missing}] unknown=[{unknown}]",
        )
    return value


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PackManifestRefused("manifest_value", f"{where} must be a non-empty string")
    return value


def _sha256(value: Any, where: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise PackManifestRefused("manifest_value", f"{where} must be a lowercase SHA-256")
    return value


def _review(value: Any) -> ReviewAttestation:
    raw = _object(value, "review", _REVIEW_KEYS)
    fields = {name: _text(raw[name], f"review.{name}") for name in _REVIEW_KEYS}
    stamp = fields["reviewed_at"]
    try:
        if _DATE.fullmatch(stamp) is None:
            raise ValueError(stamp)
        date.fromisoformat(stamp)
    except ValueError:
        raise PackManifestRefused(
            "manifest_value", "review.reviewed_at must be a calendar date YYYY-MM-DD",
        ) from None
    return ReviewAttestation(**fields)


def _scope(value: Any, index: int) -> ReviewedScope:
    where = f"scopes[{index}]"
    raw = _object(value, where, _SCOPE_KEYS)
    text = {
        name: _text(raw[name], f"{where}.{name}")
        for name in _SCOPE_KEYS - {"map_sha256", "set_sha256"}
    }
    map_sha256 = _sha256(raw["map_sha256"], f"{where}.map_sha256")
    set_sha256 = _sha256(raw["set_sha256"], f"{where}.set_sha256")
    try:
        NormRetrievalSetId.parse(text["set_id"])
    except ValueError:
        raise PackManifestRefused(
            "manifest_value", f"{where}.set_id is not a retrieval-set identity",
        ) from None
    # `select_verified_retrieval_set` refuses any other pairing at every group start; refuse it
    # here once, when the operator can still see which file it came from.
    if text["embedding_build"] != f"{EMBEDDING_PROFILE}:{text['chunking_profile']}":
        raise PackManifestRefused(
            "manifest_value", f"{where}.embedding_build does not match chunking_profile",
        )
    return ReviewedScope(
        scope_id=text["scope_id"],
        identity=SetIdentity(
            map_sha256=map_sha256, snapshot_id=text["snapshot_id"],
            reviewed_content_key=text["reviewed_content_key"],
            embedding_build=text["embedding_build"], builder_version=text["builder_version"],
        ),
        chunking_profile=text["chunking_profile"],
        set_id=text["set_id"], set_sha256=set_sha256,
    )


def _scopes(value: Any) -> tuple[ReviewedScope, ...]:
    if not isinstance(value, list) or len(value) != len(SCOPES):
        raise PackManifestRefused("scope_count", f"scopes must hold exactly {len(SCOPES)}")
    scopes = tuple(_scope(item, index) for index, item in enumerate(value))
    ids = [scope.scope_id for scope in scopes]
    if len(set(ids)) != len(ids):
        raise PackManifestRefused("scope_id_duplicate", "a scope id repeats")
    if tuple(ids) != SCOPES:
        raise PackManifestRefused("scope_order", f"scopes must be ordered {','.join(SCOPES)}")
    if len({scope.identity.map_sha256 for scope in scopes}) != len(scopes):
        raise PackManifestRefused("scope_map_duplicate", "two scopes share one map SHA-256")
    if len({scope.set_id for scope in scopes}) != len(scopes):
        raise PackManifestRefused("scope_set_duplicate", "two scopes share one retrieval set")
    return scopes


def parse_manifest(data: bytes) -> ParsedPackManifest:
    """Validate sealed bytes into the pack and its review record, or raise ``PackManifestRefused``.

    Exactly the refusals ``TrustedPackRegistry.select_beta`` would make at the first group start
    are made here too, so a manifest that loads is a manifest the registry will accept.
    """
    if len(data) > MAX_MANIFEST_BYTES:
        raise PackManifestRefused("manifest_too_large", f"more than {MAX_MANIFEST_BYTES} bytes")
    try:
        document = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_refuse_duplicate_keys, parse_constant=_refuse_constant,
        )
    except PackManifestRefused:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise PackManifestRefused("manifest_not_json", "not UTF-8 JSON") from None
    root = _object(document, "manifest", _ROOT_KEYS)
    if root["format"] != MANIFEST_FORMAT:
        raise PackManifestRefused("manifest_format", "unknown manifest format")
    sealed_digest = _sha256(root["pack_sha256"], "pack_sha256")
    pack = TrustedPack(
        analysis_profile_id=_text(root["analysis_profile_id"], "analysis_profile_id"),
        prompt_bundle_id=_text(root["prompt_bundle_id"], "prompt_bundle_id"),
        scopes=_scopes(root["scopes"]),
    )
    review = _review(root["review"])
    if pack.sha256 != sealed_digest:
        raise PackManifestRefused("pack_digest_mismatch", "pack_sha256 differs from the scopes")
    parsed = ParsedPackManifest(pack, review)
    try:
        parsed.registry.select_beta()
    except DomainError as exc:
        kind = exc.detail_fields.get("reference_kind") or exc.detail_fields.get("dependency")
        raise PackManifestRefused(
            "pack_refused", f"{exc.code.value}{f' ({kind})' if kind else ''}",
        ) from None
    except ValueError:
        raise PackManifestRefused("pack_refused", "pack identity is malformed") from None
    return parsed


def seal_manifest(pack: TrustedPack, review: ReviewAttestation) -> bytes:
    """Canonical manifest bytes. Refuses whatever ``parse_manifest`` would refuse."""
    document = {
        "format": MANIFEST_FORMAT,
        "analysis_profile_id": pack.analysis_profile_id,
        "prompt_bundle_id": pack.prompt_bundle_id,
        "pack_sha256": pack.sha256,
        "review": {
            "reviewer": review.reviewer, "capacity": review.capacity,
            "reviewed_at": review.reviewed_at, "decision_ref": review.decision_ref,
            "scope_statement": review.scope_statement,
        },
        "scopes": [
            {
                "scope_id": scope.scope_id,
                "map_sha256": scope.identity.map_sha256,
                "snapshot_id": scope.identity.snapshot_id,
                "reviewed_content_key": scope.identity.reviewed_content_key,
                "embedding_build": scope.identity.embedding_build,
                "builder_version": scope.identity.builder_version,
                "chunking_profile": scope.chunking_profile,
                "set_id": scope.set_id,
                "set_sha256": scope.set_sha256,
            }
            for scope in pack.scopes
        ],
    }
    data = json.dumps(
        document, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    parse_manifest(data)
    return data


def read_regular_file(path: str) -> bytes:
    """Read at most ``MAX_MANIFEST_BYTES`` from a regular file that is not itself a symlink.

    The open refuses a final-component symlink (a directory on the way may be one: a bind
    mount is) and never blocks on a FIFO; ``fstat`` on the opened descriptor, not a prior
    ``stat`` of the name, decides what it is, so the check and the read see one file.
    """
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        raise PackManifestRefused("manifest_missing", "no file at the configured path") from None
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise PackManifestRefused("manifest_not_regular_file", "a symbolic link") from None
        raise PackManifestRefused(
            "manifest_unreadable", errno.errorcode.get(exc.errno or 0, "OSError"),
        ) from None
    except ValueError:
        raise PackManifestRefused("manifest_unreadable", "invalid path") from None
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise PackManifestRefused("manifest_not_regular_file", "not a regular file")
        if info.st_size > MAX_MANIFEST_BYTES:
            raise PackManifestRefused(
                "manifest_too_large", f"more than {MAX_MANIFEST_BYTES} bytes",
            )
        chunks: list[bytes] = []
        total = 0
        while total <= MAX_MANIFEST_BYTES:
            chunk = os.read(descriptor, MAX_MANIFEST_BYTES + 1 - total)
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
        if total > MAX_MANIFEST_BYTES:
            raise PackManifestRefused(
                "manifest_too_large", f"more than {MAX_MANIFEST_BYTES} bytes",
            )
        return b"".join(chunks)
    except OSError as exc:
        raise PackManifestRefused(
            "manifest_unreadable", errno.errorcode.get(exc.errno or 0, "OSError"),
        ) from None
    finally:
        os.close(descriptor)


def load_manifest(path: str) -> ParsedPackManifest:
    return parse_manifest(read_regular_file(path))


def load_trusted_pack_registry(path: str | None) -> TrustedPackRegistry:
    """The registry a server process installs: empty without a path, one pack with a good one.

    ``None`` and a blank value mean "no pack installed" -- the same reading ``settings.py``
    gives every optional variable, and what a compose pass-through of an unset host variable
    yields. Any other value must name a manifest this module accepts, or the start is refused.
    """
    if path is None or not path.strip():
        return TrustedPackRegistry.empty()
    return load_manifest(path.strip()).registry


__all__ = [
    "MANIFEST_FORMAT",
    "MAX_MANIFEST_BYTES",
    "PACK_MANIFEST_ENV",
    "PackManifestRefused",
    "ParsedPackManifest",
    "ReviewAttestation",
    "load_manifest",
    "load_trusted_pack_registry",
    "parse_manifest",
    "read_regular_file",
    "seal_manifest",
]
