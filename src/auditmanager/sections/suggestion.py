"""Suggest a project section from the legacy patterns; never confirm one.

The filename and extracted text are evidence for a reviewer, not identities or
routing authority. The W59 workflow must persist an explicit expert choice
before starting an analysis. The bundled pattern file is a reviewed copy of
the legacy registry with the owner-retained PB entry added separately.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


_PATTERNS = Path(__file__).with_name("suggestion_patterns.json")
_WORD_BOUNDARY = r"(?<!\w){}(?!\w)"


@dataclass(frozen=True, slots=True)
class SectionSuggestion:
    code: str
    name: str
    score: int
    filename_patterns: tuple[str, ...]
    text_keywords: tuple[str, ...]
    name_in_text: bool


@dataclass(frozen=True, slots=True)
class _SectionPattern:
    code: str
    name: str
    filename_patterns: tuple[str, ...]
    text_keywords: tuple[str, ...]


def _normalise(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold().replace("_", " ")
    return " ".join(text.split())


def _contains(haystack: str, needle: str) -> bool:
    term = _normalise(needle.strip("-"))
    if not term:
        return False
    return re.search(_WORD_BOUNDARY.format(re.escape(term)), haystack) is not None


@lru_cache(maxsize=1)
def _catalogue() -> tuple[_SectionPattern, ...]:
    data: Any = json.loads(_PATTERNS.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("format_version") != "section-suggestions/1":
        raise ValueError("section_suggestion_catalogue_invalid")
    raw = data.get("sections")
    if not isinstance(raw, list) or len(raw) != 15:
        raise ValueError("section_suggestion_catalogue_invalid")
    sections: list[_SectionPattern] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("section_suggestion_catalogue_invalid")
        code, name = item.get("code"), item.get("name")
        filenames, keywords = item.get("folder_patterns"), item.get("text_keywords")
        if (
            not isinstance(code, str) or not re.fullmatch(r"[A-Z]{2,3}", code)
            or not isinstance(name, str) or not name.strip()
            or not isinstance(filenames, list) or not filenames
            or any(not isinstance(value, str) or not value.strip() for value in filenames)
            or not isinstance(keywords, list)
            or any(not isinstance(value, str) or not value.strip() for value in keywords)
        ):
            raise ValueError("section_suggestion_catalogue_invalid")
        sections.append(_SectionPattern(code, name, tuple(filenames), tuple(keywords)))
    if len({item.code for item in sections}) != 15:
        raise ValueError("section_suggestion_catalogue_invalid")
    return tuple(sections)


def suggest_sections(filename: str, extracted_text: str) -> tuple[SectionSuggestion, ...]:
    """Rank evidence-bearing suggestions without choosing or persisting one.

    The filename contributes at most four points per section, exact section
    title five, and at most four distinct text keywords one each. Substrings
    inside longer words do not match. Ties remain separate suggestions.
    """
    if not isinstance(filename, str) or not isinstance(extracted_text, str):
        raise TypeError("filename and extracted_text must be strings")
    file_text = _normalise(filename)
    body_text = _normalise(extracted_text)
    suggestions: list[SectionSuggestion] = []
    for section in _catalogue():
        filename_hits = tuple(
            pattern for pattern in section.filename_patterns if _contains(file_text, pattern)
        )
        keyword_hits = tuple(
            keyword for keyword in section.text_keywords if _contains(body_text, keyword)
        )
        name_hit = _contains(body_text, section.name)
        score = (4 if filename_hits else 0) + min(len(keyword_hits), 4) + (5 if name_hit else 0)
        if score:
            suggestions.append(
                SectionSuggestion(
                    code=section.code,
                    name=section.name,
                    score=score,
                    filename_patterns=filename_hits,
                    text_keywords=keyword_hits,
                    name_in_text=name_hit,
                )
            )
    return tuple(sorted(suggestions, key=lambda item: (-item.score, item.code)))
