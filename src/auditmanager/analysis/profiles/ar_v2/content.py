"""Load the six reviewed AR v2 prompt sections with fail-closed provenance.

The legacy files are evidence for vocabulary, not a normative rulebook. Only
the text between explicit prompt markers may reach a later prompt bundle.
The caller must bind ``reviewed_content_sha256`` into that bundle's identity.
This module does not select a profile or execute a model request.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Final


@dataclass(frozen=True, slots=True)
class ReviewedSource:
    filename: str
    legacy_path: str
    legacy_sha256: str
    resource_sha256: str


@dataclass(frozen=True, slots=True)
class ReviewedSection:
    source: ReviewedSource
    prompt_text: str


class ProfileContentError(ValueError):
    """A reviewed resource is missing, changed, or structurally invalid."""


REVIEWED_SOURCES: Final[tuple[ReviewedSource, ...]] = (
    ReviewedSource(
        "role.md",
        "prompts/disciplines/AR/role.md",
        "fda944f74c4a0bd7cd77339f2c2f8519f55d59e899be03da212f93d2ad432203",
        "a04fbbfc1c28946c81ec1b4156cd0ed42ef890e0f83b4e13b00cb9715ae8d620",
    ),
    ReviewedSource(
        "finding_categories.md",
        "prompts/disciplines/AR/finding_categories.md",
        "e0591c94b2f385a837872f37f5ef32eb057131265c32283e5f732b2c1fa236ce",
        "4c7c9dac924990eb06432834bdfc1a4a41eb3943e2191b06510c4570d09983de",
    ),
    ReviewedSource(
        "checklist.md",
        "prompts/disciplines/AR/checklist.md",
        "eccb7879023a126427fd61a0ed36237eb42bbebd4bec63c4009004247d7f3179",
        "eb0cd2846798c1f783d94d26f50a560643f26b1df5f4dbba6c7bc6e099647585",
    ),
    ReviewedSource(
        "drawing_types.md",
        "prompts/disciplines/AR/drawing_types.md",
        "38ef910c11c71d03819a37c258933bcf4c851ac2cce31bace2681d8fde8fa45e",
        "d07860a68c2fdacfd89ca62a36cabd65950a914c7cf9c5ad30f56b04a4442e70",
    ),
    ReviewedSource(
        "project_params.md",
        "prompts/disciplines/AR/project_params.md",
        "5d827feac80cf85760af4a1d3f8509e15defb0df771c09ea83e475e172a80f35",
        "f0b84f805788aebf6489b88b01191272164c4f8600f0e8e86649120334ed292d",
    ),
    ReviewedSource(
        "ar_checklist.md",
        "backend/app/data/discipline_checklists/AR.md",
        "1fbede99e35e8beadbb014538af76c33fdb54a7860e72616c4a4605ee28e17a9",
        "6ac2239576a569443cb55ac4e364416c51aacd4ae7057068fc3c34148cec3575",
    ),
)

_START: Final[str] = "<!-- prompt:start -->"
_END: Final[str] = "<!-- prompt:end -->"
_RESOURCE_DIR: Final[Path] = Path(__file__).parent


def _read_one(source: ReviewedSource) -> tuple[ReviewedSection, bytes]:
    try:
        raw = (_RESOURCE_DIR / source.filename).read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise ProfileContentError(f"unreadable reviewed AR source: {source.filename}") from exc

    if hashlib.sha256(raw).hexdigest() != source.resource_sha256:
        raise ProfileContentError(f"reviewed AR source digest mismatch: {source.filename}")
    path_header = f"<!-- legacy_path: {source.legacy_path} -->"
    digest_header = f"<!-- legacy_sha256: {source.legacy_sha256} -->"
    lines = text.splitlines()
    if path_header not in lines[:5] or digest_header not in lines[:5]:
        raise ProfileContentError(f"reviewed AR source provenance mismatch: {source.filename}")
    if text.count(_START) != 1 or text.count(_END) != 1:
        raise ProfileContentError(f"reviewed AR source markers invalid: {source.filename}")
    before, rest = text.split(_START, 1)
    prompt, after = rest.split(_END, 1)
    if not before or not after.strip() or not prompt.strip():
        raise ProfileContentError(f"reviewed AR source empty: {source.filename}")
    return ReviewedSection(source, prompt.strip()), raw


def reviewed_sections() -> tuple[ReviewedSection, ...]:
    """Return exact reviewed prompt text, excluding headers and review notes."""
    return tuple(_read_one(source)[0] for source in REVIEWED_SOURCES)


def reviewed_content_sha256() -> str:
    """Hash the full six-file corpus in manifest order, including review notes."""
    digest = hashlib.sha256()
    for source in REVIEWED_SOURCES:
        _, raw = _read_one(source)
        digest.update(source.filename.encode("ascii"))
        digest.update(b"\0")
        digest.update(raw)
        digest.update(b"\0")
    return digest.hexdigest()
