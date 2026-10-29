"""The profiles of the sections for the client report: each section by its own features (`CMP-VC-REPORT-01`).

A port of the original's ``md_report/disciplines.py`` at ``23f379fd`` (65 lines). A profile is the section's name, the priorities of the
selection (text that goes into the model's task) and the features of an «important» fact (the ★ of the packet and the coverage check). The
section is found by the title, then by the cipher; when neither names one the profile is the neutral one, without any section's priorities
(``known`` false). The 37 priorities and the registry are the original's files, copied unchanged to ``disciplines/`` (``prompts/
client_disciplines/`` there; ``_registry.json`` schema ``client-disciplines/1``).
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

__all__ = ["DIR", "IMPORTANT_KEYS", "by_key", "describe", "resolve", "suffix"]

DIR: Final[Path] = Path(__file__).resolve().parent / "disciplines"
IMPORTANT_KEYS: Final[tuple[str, ...]] = ("req", "mark", "size", "rating")


@lru_cache(maxsize=1)
def _registry() -> tuple[dict[str, Any], ...]:
    data = json.loads((DIR / "_registry.json").read_text(encoding="utf-8"))
    out = []
    for entry in data["disciplines"]:
        out.append(entry | {
            "_match": [re.compile(p) for p in entry.get("match") or []],
            "_title": re.compile(entry["title"], re.I) if entry.get("title") else None,
        })
    return tuple(out)


def suffix(code: str | None) -> str:
    """The cipher of the section after the last «-»: «133/23-ГК-ОВ2.1» → «ОВ2.1» (disciplines.py:29-31)."""
    return re.split(r"\s+", (code or "").strip())[0].rsplit("-", 1)[-1] if code else ""


def _profile(entry: dict[str, Any] | None) -> dict[str, Any]:
    if entry is None:
        return {
            "key": "_neutral", "name": "", "known": False,
            "priorities": (DIR / "_neutral.md").read_text(encoding="utf-8").strip(), "important": {},
        }
    important = {
        k: re.compile(v, re.I) for k, v in (entry.get("important") or {}).items() if k in IMPORTANT_KEYS and v
    }
    return {
        "key": entry["key"], "name": entry["name"], "known": True,
        "priorities": (DIR / f"{entry['key']}.md").read_text(encoding="utf-8").strip(), "important": important,
    }


def by_key(key: str) -> dict[str, Any]:
    """The profile by the key written into a report; an unknown key is the neutral profile."""
    entry = next((x for x in _registry() if x["key"] == key), None)
    return _profile(entry) | {"by": "report" if entry else "none"}


def resolve(code: str | None, title_text: str = "") -> dict[str, Any]:
    """The profile of a section: by the title, else by the cipher, else the neutral one (disciplines.py:49-60)."""
    text = re.sub(r"\s+", " ", title_text or "")
    if text:
        for entry in _registry():
            if entry["_title"] and entry["_title"].search(text):
                return _profile(entry) | {"by": "title"}
    tail = suffix(code)
    for entry in _registry():
        if any(p.fullmatch(tail) for p in entry["_match"]):
            return _profile(entry) | {"by": "code"}
    return _profile(None) | {"by": "none"}


def describe(profile: dict[str, Any]) -> dict[str, Any]:
    """What a report records of the profile (no regular expressions)."""
    return {k: profile.get(k) for k in ("key", "name", "known", "by")}
