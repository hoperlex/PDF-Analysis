"""The section-keyed text-profile registry (`W59-SECTION-SEAL-01`).

Run start routes a version's **persisted, expert-confirmed** section to the analysis profile
registered here; the executor resolves the run's pinned profile through the same registry so
every v1-style text run executes with its own prompt bundle. A section with no entry is
refused at run start -- there is no AR fallback.

Two sources, and only two:

* **AR** is registered from the existing v1 constants (:data:`.profile.AR_TEXT_PROFILE`),
  unchanged: same identities, same prompt, same content hash, so every historical AR run
  resolves exactly as before. There is no ``profiles/ar/`` package and one would be refused.
* **Data packages** ``profiles/<code_lower>/{profile.json, system_prompt.md}`` in the format
  ``text-profile/1`` (integration contract of the task). ``profile.json`` holds exactly the
  keys ``format``, ``section_code``, ``analysis_profile_id`` (``ap_`` ULID),
  ``prompt_bundle_id`` (``pb_`` ULID), ``profile_version``, ``status`` (``draft`` or
  ``reviewed``), ``title_ru`` and ``source`` (``repository``, ``commit``, ``files`` of
  ``{path, sha256}``). ``system_prompt.md`` replaces v1's ``SYSTEM_PROMPT``; categories,
  response schema, user preamble, page banner and token limits stay v1's. Exactly **one**
  trailing ``"\\n"`` is stripped from the prompt file (an editor's final newline), so the
  bundle text has v1's convention of no trailing newline and its hash is deterministic.

A package whose ``section_code`` is outside the fifteen, duplicates another entry (AR
included), does not match its directory name, or reuses another entry's profile or bundle
identity refuses the **whole** load with :class:`TextProfileLoadError`; the composition root
turns that into a start-up failure rather than serving a partial registry. ``draft`` and
``reviewed`` are both executable: a draft profile's status is recorded, not hidden.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final

from auditmanager.analysis.text.lock import STAGE_ID
from auditmanager.analysis.text.profile import AR_TEXT_PROFILE, AnalysisProfile
from auditmanager.analysis.text.prompt import (
    CATEGORIES,
    EFFORT,
    MAX_OUTPUT_TOKENS,
    RESPONSE_SCHEMA,
    THINKING,
    PromptBundle,
)
from auditmanager.shared.identity import AnalysisProfileId, IdentityError, PromptBundleId

__all__ = [
    "PACKAGE_FORMAT",
    "PACKAGES_ROOT",
    "SECTION_CODES",
    "RegisteredTextProfile",
    "TextProfileLoadError",
    "TextProfileRegistry",
    "TextProfileSource",
    "TextProfileSourceFile",
    "TextProfileUnavailable",
    "load_text_profile_registry",
]

PACKAGE_FORMAT: Final[str] = "text-profile/1"
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
_SOURCE_KEYS: Final[frozenset[str]] = frozenset({"repository", "commit", "files"})
_FILE_KEYS: Final[frozenset[str]] = frozenset({"path", "sha256"})
_STATUSES: Final[frozenset[str]] = frozenset({"draft", "reviewed"})
_SEMVER = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
_SHA256 = re.compile(r"[0-9a-f]{64}")
#: The files a package directory holds, and nothing else.
_PACKAGE_FILES: Final[frozenset[str]] = frozenset({"profile.json", "system_prompt.md"})


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
    #: ``builtin`` for AR's v1 constants; otherwise the package's ``draft``/``reviewed``.
    status: str
    title_ru: str
    #: The package directory relative to :data:`PACKAGES_ROOT`, or ``None`` for builtin AR.
    package: str | None
    #: The package's validated ``source`` block, or ``None`` for builtin AR (whose prompt
    #: was written in this repository, not ported). `W59-ANALYSIS-SETTINGS-01` lists it.
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


def _builtin_ar() -> RegisteredTextProfile:
    return RegisteredTextProfile(
        section_code="AR",
        profile=AR_TEXT_PROFILE,
        status="builtin",
        title_ru="Архитектурные решения",
        package=None,
    )


def load_text_profile_registry(root: Path = PACKAGES_ROOT) -> TextProfileRegistry:
    """AR from the v1 constants plus every package under ``root``, or refuse the whole load.

    A missing ``root`` registers AR alone. Entries whose names start with ``_`` or ``.``
    (``__pycache__``, a stray dot-file) and plain files are not packages and are ignored;
    every other directory must be a valid package.
    """
    entries: list[RegisteredTextProfile] = [_builtin_ar()]
    if root.is_dir():
        for directory in sorted(root.iterdir(), key=lambda item: item.name):
            if directory.name.startswith(("_", ".")) or not directory.is_dir():
                continue
            entries.append(_load_package(directory, root))
    return TextProfileRegistry(entries)


def _load_package(directory: Path, root: Path) -> RegisteredTextProfile:
    name = directory.name
    present = {item.name for item in directory.iterdir() if not item.name.startswith(".")}
    if present != _PACKAGE_FILES:
        raise TextProfileLoadError(f"package_files_invalid: {name}: {sorted(present)}")
    try:
        data: Any = json.loads((directory / "profile.json").read_text(encoding="utf-8"))
        prompt = (directory / "system_prompt.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TextProfileLoadError(f"package_unreadable: {name}") from exc
    if not isinstance(data, dict) or set(data) != _PROFILE_KEYS:
        raise TextProfileLoadError(f"profile_keys_invalid: {name}")
    if data["format"] != PACKAGE_FORMAT:
        raise TextProfileLoadError(f"format_invalid: {name}")
    code = data["section_code"]
    if not isinstance(code, str) or code not in SECTION_CODES:
        raise TextProfileLoadError(f"section_code_unknown: {name}")
    if name != code.lower():
        raise TextProfileLoadError(f"package_directory_mismatch: {name} holds {code}")
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
    source = _check_source(data["source"], name)
    # Exactly one trailing newline is the file's, not the prompt's (see the module note).
    text = prompt[:-1] if prompt.endswith("\n") else prompt
    if not text.strip():
        raise TextProfileLoadError(f"system_prompt_empty: {name}")
    bundle = PromptBundle(
        prompt_bundle_id=bundle_id,
        system_prompt=text,
        response_schema=RESPONSE_SCHEMA,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        effort=EFFORT,
        thinking=THINKING,
    )
    profile = AnalysisProfile(
        analysis_profile_id=profile_id,
        profile_version=version,
        stage_id=STAGE_ID,
        discipline=code,
        categories=CATEGORIES,
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
