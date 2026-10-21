"""Pure W54 record-to-W58 object-seal binding for a copied inventory.

The caller must separately run ``object_copy.verify_manifest`` against the
mirrored payloads. Neither check proves a live bucket or database restore.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from scripts.recovery.object_copy import ObjectCopyRefused, manifest_bytes, parse_inventory

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SHA1 = re.compile(r"[0-9a-f]{40}\Z")
_STAMP = re.compile(r"[0-9]{8}T[0-9]{6}Z\Z")
_UTC = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
_TABLE = re.compile(r"[a-z_][a-z0-9_]*\Z")
_RECORD_LINE = re.compile(rb'  "[a-z0-9_]+": [^ ].*\Z')
_RECORD_KEYS = frozenset(
    (
        "record_version", "kind", "stamp", "state", "purpose", "target_sha",
        "instance", "deployed_tree", "migration_head", "opened_at", "quiesced_at",
        "writers_present", "writers_stopped", "dump", "fingerprint",
        "rejected_blob_count", "inventory", "attestation", "waiver",
        "real_data_marker", "restored_at", "closed_at",
    )
)


class CopyRecordBindingRefused(ValueError):
    """The three offline artifacts cannot describe one W54 object copy."""


def _object(value: Any, label: str, keys: frozenset[str]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise CopyRecordBindingRefused(f"{label} has unknown or missing fields")
    return value


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise CopyRecordBindingRefused(f"{label} must be a nonnegative integer")
    return value


def _matches(value: Any, pattern: re.Pattern[str], label: str) -> str:
    if type(value) is not str or not pattern.fullmatch(value):
        raise CopyRecordBindingRefused(f"{label} has an invalid value")
    return value


def _optional_utc(value: Any, label: str) -> None:
    if value is not None:
        _matches(value, _UTC, label)


def _pairs_unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CopyRecordBindingRefused(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _json(data: bytes, label: str) -> Any:
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_pairs_unique)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CopyRecordBindingRefused(f"{label} is not valid JSON") from exc


def _record(data: bytes) -> dict[str, Any]:
    # The stand's line-oriented reader accepts this v1 layout, not arbitrary JSON.
    lines = data.split(b"\n")
    if b"\r" in data or b"\\" in data or len(lines) < 4 or lines[-1] != b"" \
            or lines[0] != b"{" or lines[-2] != b"}":
        raise CopyRecordBindingRefused("record is not in W54 canonical layout")
    body = lines[1:-2]
    if not body or any(
        not _RECORD_LINE.fullmatch(line) or line.endswith(b",") != (i < len(body) - 1)
        for i, line in enumerate(body)
    ):
        raise CopyRecordBindingRefused("record is not in W54 canonical layout")
    record = _object(_json(data, "record"), "record", _RECORD_KEYS)
    if type(record["record_version"]) is not int or record["record_version"] != 1 \
            or record["kind"] != "copy" or record["state"] not in ("open", "closed"):
        raise CopyRecordBindingRefused("record is not a W54 v1 copy")
    _matches(record["stamp"], _STAMP, "record stamp")
    if record["purpose"] not in ("none", "publish", "import"):
        raise CopyRecordBindingRefused("record purpose is unknown")
    if record["purpose"] == "publish":
        _matches(record["target_sha"], _SHA1, "record target SHA")
    elif record["target_sha"] is not None:
        raise CopyRecordBindingRefused("record target SHA has no publication")
    if type(record["instance"]) is not str or not record["instance"]:
        raise CopyRecordBindingRefused("record instance is missing")
    _matches(record["deployed_tree"], _SHA1, "record deployed tree")
    if record["migration_head"] is not None and type(record["migration_head"]) is not str:
        raise CopyRecordBindingRefused("record migration head has an invalid value")
    _matches(record["opened_at"], _UTC, "record open time")
    _matches(record["quiesced_at"], _UTC, "record quiesce time")
    for name in ("writers_present", "writers_stopped"):
        writers = record[name]
        if type(writers) is not list or len(writers) != len(set(map(str, writers))) \
                or any(type(item) is not str or item not in ("web", "api", "worker") for item in writers):
            raise CopyRecordBindingRefused(f"record {name} has invalid writers")
    _nonnegative(record["rejected_blob_count"], "rejected Blob count")
    if type(record["real_data_marker"]) is not bool or record["waiver"] is not None:
        raise CopyRecordBindingRefused("record is not a full copy")
    _optional_utc(record["restored_at"], "record restore time")
    _optional_utc(record["closed_at"], "record close time")

    dump = _object(record["dump"], "record dump", frozenset(("file", "size_bytes", "sha256")))
    if dump["file"] != "db.dump":
        raise CopyRecordBindingRefused("record dump filename differs")
    _nonnegative(dump["size_bytes"], "record dump size")
    _matches(dump["sha256"], _SHA256, "record dump SHA-256")

    fingerprint = _object(
        record["fingerprint"], "record fingerprint", frozenset(("algorithm", "sha256", "tables"))
    )
    if fingerprint["algorithm"] != "stand-fingerprint-v1":
        raise CopyRecordBindingRefused("record fingerprint algorithm differs")
    _matches(fingerprint["sha256"], _SHA256, "record fingerprint SHA-256")
    tables = fingerprint["tables"]
    if type(tables) is not dict or not tables:
        raise CopyRecordBindingRefused("record fingerprint tables are missing")
    for table, value in tables.items():
        _matches(table, _TABLE, "fingerprint table")
        entry = _object(value, "fingerprint table", frozenset(("rows", "sha256")))
        _nonnegative(entry["rows"], "fingerprint rows")
        _matches(entry["sha256"], _SHA256, "fingerprint table SHA-256")

    attestation = record["attestation"]
    if attestation is not None:
        attestation = _object(
            attestation, "record attestation",
            frozenset(("dump_sha256", "restore_report_sha256", "attested_at")),
        )
        if attestation["dump_sha256"] != dump["sha256"]:
            raise CopyRecordBindingRefused("record attestation names another dump")
        _matches(attestation["restore_report_sha256"], _SHA256, "record restore report SHA-256")
        _matches(attestation["attested_at"], _UTC, "record attestation time")
    return record


def verify_copy_record_binding(record_data: bytes, inventory_data: bytes, sealed_data: bytes) -> None:
    """Refuse unless W54 record, inventory and W58 seal describe identical rows."""
    record = _record(record_data)
    try:
        rows = parse_inventory(inventory_data)
    except ObjectCopyRefused as exc:
        raise CopyRecordBindingRefused(f"inventory is invalid: {exc}") from exc
    inventory = _object(
        record["inventory"], "record inventory", frozenset(("file", "count", "bytes", "sha256"))
    )
    if inventory["file"] != "inventory.tsv":
        raise CopyRecordBindingRefused("record inventory filename differs")
    count = _nonnegative(inventory["count"], "record inventory count")
    total = _nonnegative(inventory["bytes"], "record inventory bytes")
    digest = _matches(inventory["sha256"], _SHA256, "record inventory SHA-256")
    if (count, total, digest) != (
        len(rows), sum(size for _, size, _ in rows), hashlib.sha256(inventory_data).hexdigest()
    ):
        raise CopyRecordBindingRefused("inventory does not match W54 record")

    seal = _object(
        _json(sealed_data, "seal"), "seal",
        frozenset(("format", "inventory_sha256", "count", "bytes", "objects")),
    )
    if seal["format"] != "offline-object-copy-v1" or sealed_data != manifest_bytes(seal):
        raise CopyRecordBindingRefused("seal is not the canonical W58 format")
    if (seal["inventory_sha256"], seal["count"], seal["bytes"]) != (digest, count, total) \
            or type(seal["count"]) is not int or type(seal["bytes"]) is not int:
        raise CopyRecordBindingRefused("seal totals differ from W54 record")
    objects = seal["objects"]
    if type(objects) is not list or len(objects) != count:
        raise CopyRecordBindingRefused("seal object count differs from inventory")
    for (key, size, etag), value in zip(rows, objects, strict=True):
        entry = _object(value, "seal object", frozenset(("key", "size_bytes", "etag", "sha256")))
        if (entry["key"], entry["size_bytes"], entry["etag"]) != (key, size, etag) \
                or type(entry["size_bytes"]) is not int:
            raise CopyRecordBindingRefused("seal object differs from inventory row")
        _matches(entry["sha256"], _SHA256, "sealed object SHA-256")
