"""Load digest-pinned legacy category and sheet vocabulary, never prompt prose.

The 14 entries here are candidates for authored profiles. A code in this
resource does not make it an active route, a normative rule, or a decision.
PB has no legacy source and must be authored separately.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Final


METADATA_RESOURCE_SHA256: Final[str] = (
    "ffc79739053944e8adc2546da0bf82a99c4a781ebbed28c9f4239b267cfa8490"
)
LEGACY_REGISTRY_SHA256: Final[str] = (
    "0263e34ed60dd025a191230217832580bddefcdf10b7841f326784f8f8b08970"
)
_RESOURCE: Final[Path] = Path(__file__).with_name("metadata.json")
_REQUIRED_SOURCES: Final[frozenset[str]] = frozenset({
    "finding_categories.md", "drawing_types.md", "role.md", "checklist.md",
    "project_params.md",
})


class CandidateMetadataError(ValueError):
    """The bundled candidate vocabulary is missing or has changed."""


@dataclass(frozen=True, slots=True)
class SheetTypeCandidate:
    code: str
    label: str


@dataclass(frozen=True, slots=True)
class ProfileCandidate:
    code: str
    name: str
    categories: tuple[str, ...]
    sheet_types: tuple[SheetTypeCandidate, ...]
    source_sha256: tuple[tuple[str, str], ...]


def _read_catalogue(path: Path) -> tuple[ProfileCandidate, ...]:
    try:
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != METADATA_RESOURCE_SHA256:
            raise CandidateMetadataError("section_candidate_resource_digest_mismatch")
        data: Any = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CandidateMetadataError("section_candidate_resource_unreadable") from exc
    if (
        not isinstance(data, dict)
        or data.get("format_version") != "legacy-section-profile-metadata/1"
        or data.get("legacy_registry_sha256") != LEGACY_REGISTRY_SHA256
        or not isinstance(data.get("sections"), list)
        or len(data["sections"]) != 14
    ):
        raise CandidateMetadataError("section_candidate_resource_invalid")

    candidates: list[ProfileCandidate] = []
    for item in data["sections"]:
        if not isinstance(item, dict) or set(item) != {
            "code", "name", "categories", "sheet_types", "source_sha256"
        }:
            raise CandidateMetadataError("section_candidate_resource_invalid")
        code, name = item["code"], item["name"]
        categories, sheets, sources = (
            item["categories"], item["sheet_types"], item["source_sha256"]
        )
        if (
            not isinstance(code, str) or not re.fullmatch(r"[A-Z]{2,3}", code)
            or code == "PB"
            or not isinstance(name, str) or not name.strip()
            or not isinstance(categories, list) or not categories
            or any(not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", value) for value in categories)
            or len(set(categories)) != len(categories)
            or not isinstance(sheets, list) or not sheets
            or not isinstance(sources, dict) or not _REQUIRED_SOURCES <= set(sources)
            or any(not isinstance(key, str) or not isinstance(value, str)
                   or not re.fullmatch(r"[0-9a-f]{64}", value)
                   for key, value in sources.items())
        ):
            raise CandidateMetadataError("section_candidate_resource_invalid")
        typed_sheets: list[SheetTypeCandidate] = []
        for sheet in sheets:
            if (
                not isinstance(sheet, dict) or set(sheet) != {"code", "label"}
                or not isinstance(sheet["code"], str)
                or not re.fullmatch(r"[a-z][a-z0-9_]*", sheet["code"])
                or not isinstance(sheet["label"], str)
                or not sheet["label"].strip()
            ):
                raise CandidateMetadataError("section_candidate_resource_invalid")
            typed_sheets.append(SheetTypeCandidate(sheet["code"], sheet["label"]))
        if len({sheet.code for sheet in typed_sheets}) != len(typed_sheets):
            raise CandidateMetadataError("section_candidate_resource_invalid")
        candidates.append(ProfileCandidate(
            code=code,
            name=name,
            categories=tuple(categories),
            sheet_types=tuple(typed_sheets),
            source_sha256=tuple(sorted(sources.items())),
        ))
    if len({item.code for item in candidates}) != 14:
        raise CandidateMetadataError("section_candidate_resource_invalid")
    return tuple(candidates)


@lru_cache(maxsize=1)
def load_candidates() -> tuple[ProfileCandidate, ...]:
    """Return the immutable, digest-pinned candidate vocabulary."""
    return _read_catalogue(_RESOURCE)
