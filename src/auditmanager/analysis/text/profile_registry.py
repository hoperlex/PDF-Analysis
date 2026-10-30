"""The section-keyed text-profile registry (`W59-SECTION-SEAL-01`).

Run start routes a version's **persisted, expert-confirmed** section to the analysis profile
registered here; the executor resolves the run's pinned profile through the same registry so
every v1-style text run executes with its own prompt bundle. A section with no entry is
refused at run start -- there is no AR fallback.

**АР is registered again** by `HOTFIX-AR-ORIGINAL-PROFILE-INT-20261030` as a new
text profile sourced from the original application's AR files. The previous six-Run
v3 group retains its distinct identity for already accepted Runs. A new ordinary
start for a version classified АР resolves this package.

One source: the **data packages** ``profiles/<code_lower>/{profile.json, system_prompt.md}`` in the format
  ``text-profile/1`` or ``text-profile/2``. ``profile.json`` holds exactly the
  keys ``format``, ``section_code``, ``analysis_profile_id`` (``ap_`` ULID),
  ``prompt_bundle_id`` (``pb_`` ULID), ``profile_version``, ``status`` (``draft`` or
  ``reviewed``), ``title_ru`` and ``source`` (``repository``, ``commit``, ``files`` of
  ``{path, sha256}``). ``system_prompt.md`` replaces v1's ``SYSTEM_PROMPT``; the
  request envelope, page banner and token limits stay in the common text pipeline.

**Format ``text-profile/2``** (`SECTION-CATEGORY-OCR-01`, `R-146ao`) is the same key set plus ``categories``:
the profile's own closed list, ``internal_contradiction``, ``explicit_placeholder`` and, for the sections
that may report a same-document omission, ``documentation`` (the existing contract value).
The original-source AR package declares its own document-grounded categories as well. The response
schema follows the list (:func:`~auditmanager.analysis.text.prompt.response_schema_for`): the two-category
list gives v1's schema object itself, so a ``text-profile/1`` package, which declares no list and gets the
v1 pair, builds exactly the profile it always built. A ``/2`` package may not declare the v1 pair alone (it
would be a ``/1`` package under another name) and may not declare a category this code has no shape for. Exactly **one**
  trailing ``"\\n"`` is stripped from the prompt file (an editor's final newline), so the
  bundle text has v1's convention of no trailing newline and its hash is deterministic.

A package whose ``section_code`` is outside the fifteen, duplicates another entry,
does not match its directory name, or reuses another entry's profile or bundle
identity refuses the **whole** load with :class:`TextProfileLoadError`; the composition root
turns that into a start-up failure rather than serving a partial registry. ``draft`` and
``reviewed`` are both executable: a draft profile's status is recorded, not hidden.

**Authored packages** (`PB-PROFILE-01`). A section with no legacy repository behind it has no
``source`` to declare. :data:`AUTHORED_SECTIONS` names those sections, and only for them is
``"source": null`` accepted, and required: the same key set, an explicit declaration, never an
absent key. An authored package carries a third file, ``open_questions.md``, the expert's open
questions for it, because nothing ported from a reviewed legacy prompt stands behind its
wording. A legacy section with ``source: null``, an authored section with a source, an authored
package without questions and a legacy package with them each refuse the whole load.
"""

from __future__ import annotations

import json
import hashlib
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final

from auditmanager.analysis.text.lock import STAGE_ID
from auditmanager.analysis.text.profile import AnalysisProfile
from auditmanager.analysis.text.prompt import (
    CATEGORIES,
    AR_TEXT_CATEGORIES,
    EFFORT,
    MAX_OUTPUT_TOKENS,
    OMISSION_CATEGORY,
    THINKING,
    PromptBundle,
    response_schema_for,
)
from auditmanager.shared.identity import AnalysisProfileId, IdentityError, PromptBundleId

__all__ = [
    "AUTHORED_SECTIONS",
    "PACKAGE_FORMAT",
    "PACKAGE_FORMAT_CATEGORIES",
    "PACKAGES_ROOT",
    "PROJECT_STRUCTURE_ORDER",
    "SECTION_CODES",
    "RegisteredTextProfile",
    "TextProfileLoadError",
    "TextProfileRegistry",
    "TextProfileSource",
    "TextProfileSourceFile",
    "TextProfileUnavailable",
    "load_text_profile_registry",
    "relaxed_profile_pair",
]

RELAXED_OUTPUT_TOKENS: Final[int] = 64_000
_ULID_ALPHABET: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _relaxed_id(value: str) -> str:
    """A stable, distinct identity for a changed immutable profile or bundle."""
    prefix = value.split("_", 1)[0]
    number = int.from_bytes(hashlib.sha256(f"section-relaxed-v1:{value}".encode()).digest()[:16], "big")
    body = "".join(_ULID_ALPHABET[(number >> shift) & 31] for shift in range(125, -1, -5))
    return f"{prefix}_{body}"


def relaxed_profile_pair(profile_id: str, bundle_id: str) -> tuple[str, str]:
    """The explicit 64k variant pair pinned by a raised-limit section Run."""
    return _relaxed_id(profile_id), _relaxed_id(bundle_id)

PACKAGE_FORMAT: Final[str] = "text-profile/1"
#: The format that adds the profile's own ``categories`` (`SECTION-CATEGORY-OCR-01`).
PACKAGE_FORMAT_CATEGORIES: Final[str] = "text-profile/2"
PACKAGES_ROOT: Final[Path] = Path(__file__).with_name("profiles")

#: The fifteen section codes. Restated, not imported: ``analysis`` does not depend on the
#: ``sections`` package, and ``tests/unit/analysis/test_text_profile_registry.py`` holds this
#: set equal to the sections catalogue and the contract's ``ProjectSection``.
SECTION_CODES: Final[frozenset[str]] = frozenset(
    {
        "AR", "AI", "KM", "KJ", "OV", "EOM", "VK", "PT", "PB", "SS", "ITP", "GP", "TX",
        "POS", "PS",
    }
)

#: Every section code in the project-structure order of poll answer ``S-5`` -- AR, then the
#: cheap profiles first -- the order «Настройки анализа» lists the registry in
#: (`W59-ANALYSIS-SETTINGS-01`). ``tests/integration/sections/test_section_recordings.py``
#: holds it equal to the web's ``PROJECT_STRUCTURE_ORDER``.
PROJECT_STRUCTURE_ORDER: Final[tuple[str, ...]] = (
    "AR", "AI", "PS", "POS", "TX", "KJ", "KM", "OV", "VK", "PT", "EOM", "SS", "ITP", "GP", "PB",
)
if len(PROJECT_STRUCTURE_ORDER) != len(SECTION_CODES) or set(PROJECT_STRUCTURE_ORDER) != SECTION_CODES:
    raise ValueError("project_structure_order_invalid")  # pragma: no cover - a literal

#: The sections whose profile is authored for this product because no legacy prompt material
#: exists for them (`PB-PROFILE-01`). ``PB`` is the one: the legacy registry has fourteen
#: disciplines and fire safety as a section of its own is not among them. A section joins this
#: set by a code change that a reviewer sees, never by a package declaring itself authored.
AUTHORED_SECTIONS: Final[frozenset[str]] = frozenset({"PB"})


# The original source is copied intact into this package, outside ``profiles/`` so
# it is not mistaken for another executable section. Refuse a missing or changed
# source file, a missing verbatim block, or an edited prompt under the same IDs.
_AR_SOURCE_ROOT: Final[Path] = Path(__file__).with_name("ar_original_source")
_AR_SOURCE_COMMIT: Final[str] = "3c99481719218b9cfa7560886529916646c61939"
_AR_SOURCE_NAMES: Final[tuple[str, ...]] = (
    "config.json", "role.md", "checklist.md", "triage_table.md", "project_params.md",
    "drawing_types.md", "finding_categories.md", "norms_reference.md", "compact_strategy.md",
)
_AR_PROMPT_SHA256: Final[str] = "4f5b9ffacf41fadd4490f02a02c2068ef63c8a521ac075ab9a168f873172d489"

_PROFILE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "format",
        "section_code",
        "analysis_profile_id",
        "prompt_bundle_id",
        "profile_version",
        "status",
        "title_ru",
        "source",
    }
)
#: ``text-profile/2`` adds exactly one key.
_PROFILE_KEYS_CATEGORIES: Final[frozenset[str]] = _PROFILE_KEYS | {"categories"}
#: The category lists a ``/2`` package may declare: the v1 pair plus the omission category.
_DECLARABLE_CATEGORIES: Final[tuple[str, ...]] = (*CATEGORIES, OMISSION_CATEGORY)
_SOURCE_KEYS: Final[frozenset[str]] = frozenset({"repository", "commit", "files"})
_FILE_KEYS: Final[frozenset[str]] = frozenset({"path", "sha256"})
_STATUSES: Final[frozenset[str]] = frozenset({"draft", "reviewed"})
_SEMVER = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
_SHA256 = re.compile(r"[0-9a-f]{64}")
#: The files a package directory holds, and nothing else.
_PACKAGE_FILES: Final[frozenset[str]] = frozenset({"profile.json", "system_prompt.md"})
#: The extra file an authored package carries, and only an authored one.
_QUESTIONS_FILE: Final[str] = "open_questions.md"
_AUTHORED_PACKAGE_FILES: Final[frozenset[str]] = _PACKAGE_FILES | {_QUESTIONS_FILE}


class TextProfileLoadError(ValueError):
    """A package, or the set of packages, cannot be registered. Nothing is registered."""


class TextProfileUnavailable(LookupError):
    """No registered profile carries the requested identity pair."""


@dataclass(frozen=True, slots=True)
class TextProfileSourceFile:
    """One legacy file a package's prompt was ported from, with its SHA-256."""

    path: str
    sha256: str


@dataclass(frozen=True, slots=True)
class TextProfileSource:
    """The package's ``source`` block, kept as read: legacy repository, commit and files."""

    repository: str
    commit: str
    files: tuple[TextProfileSourceFile, ...]


@dataclass(frozen=True, slots=True)
class RegisteredTextProfile:
    """One executable text profile and where it came from."""

    section_code: str
    profile: AnalysisProfile
    #: The package's ``draft``/``reviewed``.
    status: str
    title_ru: str
    #: The package directory relative to :data:`PACKAGES_ROOT`.
    package: str
    #: The package's validated ``source`` block, or ``None`` for an authored section (``PB``),
    #: whose prompt was written in this repository, not ported. `W59-ANALYSIS-SETTINGS-01` lists it.
    source: TextProfileSource | None = None

    @property
    def analysis_profile_id(self) -> str:
        return str(self.profile.analysis_profile_id)

    @property
    def prompt_bundle_id(self) -> str:
        return str(self.profile.prompt_bundle.prompt_bundle_id)


class TextProfileRegistry:
    """The sealed section → profile table. Immutable once built."""

    __slots__ = ("_by_section", "_by_profile")

    def __init__(self, entries: Iterable[RegisteredTextProfile]) -> None:
        by_section: dict[str, RegisteredTextProfile] = {}
        by_profile: dict[str, RegisteredTextProfile] = {}
        bundles: set[str] = set()
        for entry in entries:
            if entry.section_code not in SECTION_CODES:
                raise TextProfileLoadError(f"section_code_unknown: {entry.section_code}")
            if entry.section_code in by_section:
                raise TextProfileLoadError(f"section_code_duplicate: {entry.section_code}")
            if entry.analysis_profile_id in by_profile:
                raise TextProfileLoadError(
                    f"analysis_profile_id_duplicate: {entry.analysis_profile_id}"
                )
            if entry.prompt_bundle_id in bundles:
                raise TextProfileLoadError(f"prompt_bundle_id_duplicate: {entry.prompt_bundle_id}")
            by_section[entry.section_code] = entry
            by_profile[entry.analysis_profile_id] = entry
            bundles.add(entry.prompt_bundle_id)
            relaxed_profile_id, relaxed_bundle_id = relaxed_profile_pair(
                entry.analysis_profile_id, entry.prompt_bundle_id
            )
            if relaxed_profile_id in by_profile or relaxed_bundle_id in bundles:
                raise TextProfileLoadError("relaxed_profile_identity_duplicate")
            relaxed_bundle = replace(
                entry.profile.prompt_bundle,
                prompt_bundle_id=PromptBundleId.parse(relaxed_bundle_id),
                max_output_tokens=RELAXED_OUTPUT_TOKENS,
            )
            relaxed_profile = replace(
                entry.profile,
                analysis_profile_id=AnalysisProfileId.parse(relaxed_profile_id),
                prompt_bundle=relaxed_bundle,
            )
            by_profile[relaxed_profile_id] = replace(entry, profile=relaxed_profile)
            bundles.add(relaxed_bundle_id)
        self._by_section: Mapping[str, RegisteredTextProfile] = MappingProxyType(by_section)
        self._by_profile: Mapping[str, RegisteredTextProfile] = MappingProxyType(by_profile)

    @property
    def entries(self) -> Mapping[str, RegisteredTextProfile]:
        """Every registered entry by section code."""
        return self._by_section

    def section_profiles(self) -> Mapping[str, tuple[str, str]]:
        """Section code → ``(analysis_profile_id, prompt_bundle_id)``: run start's route table."""
        return MappingProxyType(
            {
                code: (entry.analysis_profile_id, entry.prompt_bundle_id)
                for code, entry in self._by_section.items()
            }
        )

    def executable_sections(self) -> frozenset[str]:
        return frozenset(self._by_section)

    def resolve(self, analysis_profile_id: str, prompt_bundle_id: str) -> AnalysisProfile:
        """The profile a run pinned, by its exact identity pair, or :class:`TextProfileUnavailable`.

        Both identities must match one registered entry: a run whose bundle is not the
        bundle its profile binds is not executed under either one.
        """
        entry = self._by_profile.get(str(analysis_profile_id))
        if entry is None or entry.prompt_bundle_id != str(prompt_bundle_id):
            raise TextProfileUnavailable("no registered text profile carries that identity pair")
        return entry.profile


def load_text_profile_registry(root: Path = PACKAGES_ROOT) -> TextProfileRegistry:
    """Every package under ``root``, or refuse the whole load.

    A missing ``root`` registers nothing. Entries whose names start with ``_`` or ``.``
    (``__pycache__``, a stray dot-file) and plain files are not packages and are ignored;
    every other directory must be a valid package.
    """
    entries: list[RegisteredTextProfile] = []
    if root.is_dir():
        for directory in sorted(root.iterdir(), key=lambda item: item.name):
            if directory.name.startswith(("_", ".")) or not directory.is_dir():
                continue
            entries.append(_load_package(directory, root))
    return TextProfileRegistry(entries)


def _load_package(directory: Path, root: Path) -> RegisteredTextProfile:
    name = directory.name
    present = {item.name for item in directory.iterdir() if not item.name.startswith(".")}
    if present not in (_PACKAGE_FILES, _AUTHORED_PACKAGE_FILES):
        raise TextProfileLoadError(f"package_files_invalid: {name}: {sorted(present)}")
    try:
        data: Any = json.loads((directory / "profile.json").read_text(encoding="utf-8"))
        prompt = (directory / "system_prompt.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TextProfileLoadError(f"package_unreadable: {name}") from exc
    # The key set follows the format: `/1` is the original eight keys, `/2` adds `categories`; any other
    # format string is judged against the original set and then refused by its name.
    expected_keys = (
        _PROFILE_KEYS_CATEGORIES
        if isinstance(data, dict) and data.get("format") == PACKAGE_FORMAT_CATEGORIES
        else _PROFILE_KEYS
    )
    if not isinstance(data, dict) or set(data) != expected_keys:
        raise TextProfileLoadError(f"profile_keys_invalid: {name}")
    if data["format"] not in (PACKAGE_FORMAT, PACKAGE_FORMAT_CATEGORIES):
        raise TextProfileLoadError(f"format_invalid: {name}")
    categories = _declared_categories(data, name)
    code = data["section_code"]
    if not isinstance(code, str) or code not in SECTION_CODES:
        raise TextProfileLoadError(f"section_code_unknown: {name}")
    if name != code.lower():
        raise TextProfileLoadError(f"package_directory_mismatch: {name} holds {code}")
    authored = code in AUTHORED_SECTIONS
    if not authored and _QUESTIONS_FILE in present:
        raise TextProfileLoadError(f"package_files_invalid: {name}: {sorted(present)}")
    if authored and _QUESTIONS_FILE not in present:
        raise TextProfileLoadError(f"open_questions_missing: {name}")
    try:
        profile_id = AnalysisProfileId.parse(data["analysis_profile_id"])
        bundle_id = PromptBundleId.parse(data["prompt_bundle_id"])
    except (IdentityError, TypeError, ValueError):
        raise TextProfileLoadError(f"identity_invalid: {name}") from None
    version = data["profile_version"]
    if not isinstance(version, str) or _SEMVER.fullmatch(version) is None:
        raise TextProfileLoadError(f"profile_version_invalid: {name}")
    status = data["status"]
    if status not in _STATUSES:
        raise TextProfileLoadError(f"status_invalid: {name}")
    title = data["title_ru"]
    if not isinstance(title, str) or not title.strip():
        raise TextProfileLoadError(f"title_invalid: {name}")
    source: TextProfileSource | None
    if authored:
        if data["source"] is not None:
            raise TextProfileLoadError(f"source_declared_for_authored_section: {name}")
        source = None
        try:
            questions = (directory / _QUESTIONS_FILE).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise TextProfileLoadError(f"package_unreadable: {name}") from exc
        if not questions.strip():
            raise TextProfileLoadError(f"open_questions_empty: {name}")
    else:
        source = _check_source(data["source"], name)
    # Exactly one trailing newline is the file's, not the prompt's (see the module note).
    text = prompt[:-1] if prompt.endswith("\n") else prompt
    if not text.strip():
        raise TextProfileLoadError(f"system_prompt_empty: {name}")
    if code == "AR":
        assert source is not None
        _verify_original_ar(source, text)
    bundle = PromptBundle(
        prompt_bundle_id=bundle_id,
        system_prompt=text,
        response_schema=response_schema_for(categories),
        max_output_tokens=MAX_OUTPUT_TOKENS,
        effort=EFFORT,
        thinking=THINKING,
    )
    profile = AnalysisProfile(
        analysis_profile_id=profile_id,
        profile_version=version,
        stage_id=STAGE_ID,
        discipline=code,
        categories=categories,
        prompt_bundle=bundle,
    )
    return RegisteredTextProfile(
        section_code=code,
        profile=profile,
        status=status,
        title_ru=title,
        package=directory.relative_to(root).as_posix(),
        source=source,
    )


def _declared_categories(data: dict[str, Any], name: str) -> tuple[str, ...]:
    """The profile's categories: the v1 pair for ``/1``, the declared list for ``/2``."""
    if data["format"] == PACKAGE_FORMAT:
        return CATEGORIES
    declared = data["categories"]
    # `/2` exists to add a category; the v1 pair alone belongs in a `/1` package, and no other list has a shape.
    allowed = (_DECLARABLE_CATEGORIES, AR_TEXT_CATEGORIES) if name == "ar" else (_DECLARABLE_CATEGORIES,)
    if not isinstance(declared, list) or tuple(declared) not in allowed:
        raise TextProfileLoadError(f"categories_invalid: {name}")
    return tuple(declared)


def _verify_original_ar(source: TextProfileSource, prompt: str) -> None:
    expected_paths = tuple(f"prompts/disciplines/AR/{name}" for name in _AR_SOURCE_NAMES)
    if (source.repository != "PDF-proverka" or source.commit != _AR_SOURCE_COMMIT
            or tuple(item.path for item in source.files) != expected_paths):
        raise TextProfileLoadError("ar_original_source_identity_invalid")
    for item, name in zip(source.files, _AR_SOURCE_NAMES, strict=True):
        try:
            raw = (_AR_SOURCE_ROOT / name).read_bytes()
            original_text = raw.decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise TextProfileLoadError(f"ar_original_source_unavailable: {name}") from exc
        if hashlib.sha256(raw).hexdigest() != item.sha256:
            raise TextProfileLoadError(f"ar_original_source_digest_mismatch: {name}")
        if name.endswith(".md") and prompt.count(original_text) != 1:
            raise TextProfileLoadError(f"ar_original_prompt_block_mismatch: {name}")
    if hashlib.sha256(prompt.encode("utf-8")).hexdigest() != _AR_PROMPT_SHA256:
        raise TextProfileLoadError("ar_original_prompt_digest_mismatch")


def _check_source(source: Any, name: str) -> TextProfileSource:
    if not isinstance(source, dict) or set(source) != _SOURCE_KEYS:
        raise TextProfileLoadError(f"source_invalid: {name}")
    if not all(isinstance(source[key], str) and source[key].strip() for key in ("repository", "commit")):
        raise TextProfileLoadError(f"source_invalid: {name}")
    files = source["files"]
    if not isinstance(files, list) or not files:
        raise TextProfileLoadError(f"source_files_invalid: {name}")
    for item in files:
        if (
            not isinstance(item, dict)
            or set(item) != _FILE_KEYS
            or not isinstance(item["path"], str)
            or not item["path"].strip()
            or not isinstance(item["sha256"], str)
            or _SHA256.fullmatch(item["sha256"]) is None
        ):
            raise TextProfileLoadError(f"source_files_invalid: {name}")
    return TextProfileSource(
        repository=source["repository"],
        commit=source["commit"],
        files=tuple(TextProfileSourceFile(path=item["path"], sha256=item["sha256"]) for item in files),
    )
