"""Gate-time prose rules for authored release notes; deployment checks shape only."""

from __future__ import annotations

import copy
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from auditmanager.releases.versioning import canonical_semver_sort_key


ROOT = Path(__file__).resolve().parents[3]
NOTES = ROOT / "release-notes"
KINDS = {"new": 0, "improved": 1, "fixed": 2}
CODE_TRACES = {
    "snake_case": re.compile(r"(?<!\w)[A-Za-zА-Яа-я0-9]+_[A-Za-zА-Яа-я0-9]+(?!\w)"),
    "camelCase": re.compile(r"(?<!\w)[a-zа-я]+[A-ZА-Я][A-Za-zА-Яа-я0-9]*(?!\w)"),
    "file_extension": re.compile(r"(?<!\w)[\w-]+\.[A-Za-z][A-Za-z0-9]{1,7}\b"),
    "api_path": re.compile(r"/api/", re.I),
}


def _read_entries() -> list[tuple[str, dict[str, Any]]]:
    entries = []
    for path in NOTES.iterdir():
        if path.name in {"schema.json", "dictionary.json"}:
            continue
        assert path.is_file() and path.suffix == ".json", f"unknown note file: {path.name}"
        entries.append((path.stem, json.loads(path.read_text(encoding="utf-8"))))
    return sorted(entries, key=lambda pair: canonical_semver_sort_key(pair[0]), reverse=True)


def _dictionary() -> list[str]:
    data = json.loads((NOTES / "dictionary.json").read_text(encoding="utf-8"))
    assert data.keys() == {"version", "terms"} and data["version"] == 1
    terms = data["terms"]
    assert isinstance(terms, list) and terms
    assert all(isinstance(term, str) and term.strip() == term and term for term in terms)
    assert len({term.casefold() for term in terms}) == len(terms)
    return terms


def _unquoted(text: str) -> str:
    return re.sub(r"«[^»]*»", "", text)


def form_failures(
    entries: list[tuple[str, dict[str, Any]]], *, version: str, terms: list[str]
) -> set[str]:
    """Return named rule failures so deliberate bad fixtures prove each guard."""
    failures: set[str] = set()
    keys: list[str] = []
    dates: list[date] = []
    versions: list[str] = []
    for filename, entry in entries:
        released = entry["version"]
        versions.append(released)
        try:
            key = canonical_semver_sort_key(released)
            canonical_semver_sort_key(filename)
        except ValueError:
            failures.add("canonical_version")
            key = ""
        keys.append(key)
        if filename != released:
            failures.add("filename_version")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["date"]) is None:
            failures.add("canonical_date")
        try:
            dates.append(date.fromisoformat(entry["date"]))
        except ValueError:
            failures.add("canonical_date")
        title = entry["title"]
        if not 3 <= len(title.split()) <= 9:
            failures.add("title_word_count")
        if title.endswith("."):
            failures.add("title_final_period")
        items = entry["items"]
        if not 1 <= len(items) <= 7:
            failures.add("item_count")
        if [KINDS[item["kind"]] for item in items] != sorted(KINDS[item["kind"]] for item in items):
            failures.add("kind_order")
        for text in [title, *(item["text"] for item in items)]:
            if '"' in text or "'" in text:
                failures.add("straight_quotes")
            unquoted = _unquoted(text)
            for trace_name, pattern in CODE_TRACES.items():
                if pattern.search(text):
                    failures.add(trace_name)
            if any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", unquoted, re.I) for term in terms):
                failures.add("dictionary_word")
        if any(len(item["text"]) > 400 for item in items):
            failures.add("text_length")
    if len(set(versions)) != len(versions):
        failures.add("unique_versions")
    if any(left <= right for left, right in zip(keys, keys[1:])):
        failures.add("descending_versions")
    if len(dates) == len(entries) and any(left <= right for left, right in zip(dates, dates[1:])):
        failures.add("descending_dates")
    if not versions or versions[0] != version or versions.count(version) != 1:
        failures.add("product_version")
    return failures


def test_authored_shape_and_form() -> None:
    entries = _read_entries()
    schema = json.loads((NOTES / "schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    for _, entry in entries:
        validator.validate(entry)
        assert entry["revision"] == 2
    assert form_failures(entries, version=(ROOT / "VERSION").read_text().strip(), terms=_dictionary()) == set()
    assert [entry["version"] for _, entry in entries] == ["0.3.0", "0.2.0"]
    archive = entries[-1][1]
    assert archive["is_archive"] is True
    assert archive["range_label"] == "0.1–0.2"
    assert len(archive["items"]) == 1


@pytest.mark.parametrize(
    "rule",
    [
        "canonical_version", "filename_version", "unique_versions", "descending_versions",
        "canonical_date", "descending_dates", "product_version", "title_word_count",
        "title_final_period", "item_count", "item_count_above", "kind_order", "text_length", "straight_quotes",
        "snake_case", "camelCase", "file_extension", "api_path", "dictionary_word",
    ],
)
def test_bad_fixture_fails_named_rule(rule: str) -> None:
    entries = copy.deepcopy(_read_entries())
    current = entries[0][1]
    archive = entries[1][1]
    item = current["items"][0]
    if rule == "canonical_version":
        current["version"] = "00.3.0"
    elif rule == "filename_version":
        entries[0] = ("0.3.1", current)
    elif rule == "unique_versions":
        archive["version"] = current["version"]
    elif rule == "descending_versions":
        entries.reverse()
    elif rule == "canonical_date":
        current["date"] = "2026-2-8"
    elif rule == "descending_dates":
        archive["date"] = current["date"]
    elif rule == "product_version":
        entries.pop(0)
    elif rule == "title_word_count":
        current["title"] = "Один два"
    elif rule == "title_final_period":
        current["title"] += "."
    elif rule == "item_count":
        current["items"] = []
    elif rule == "item_count_above":
        current["items"] = [copy.deepcopy(item) for _ in range(8)]
    elif rule == "kind_order":
        current["items"][0]["kind"] = "fixed"
    elif rule == "text_length":
        item["text"] = "а" * 401
    elif rule == "straight_quotes":
        item["text"] = 'Нажмите "История".'
    elif rule == "snake_case":
        item["text"] = "Виден release_note."
    elif rule == "camelCase":
        item["text"] = "Виден releaseNote."
    elif rule == "file_extension":
        item["text"] = "Откройте notes.json."
    elif rule == "api_path":
        item["text"] = "Откройте /api/releases."
    elif rule == "dictionary_word":
        item["text"] = "Новый коммит опубликован."
    expected = "item_count" if rule == "item_count_above" else rule
    assert expected in form_failures(entries, version="0.3.0", terms=_dictionary())


def test_dictionary_word_inside_guillemets_is_allowed() -> None:
    entries = copy.deepcopy(_read_entries())
    entries[0][1]["items"][0]["text"] = "Термин «коммит» приведён как цитата."
    assert "dictionary_word" not in form_failures(entries, version="0.3.0", terms=_dictionary())


def test_sealed_shape_rejects_unknown_fields() -> None:
    schema = json.loads((NOTES / "schema.json").read_text(encoding="utf-8"))
    entry = copy.deepcopy(_read_entries()[0][1])
    entry["unexpected"] = "not in the sealed shape"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(entry)
