"""The newest release note that quotes profile versions may not quote a range that leaves a profile out.

Item 3 of ``release-notes/0.9.0.json`` said the 14 section profiles were at «1.1.0 или 1.2.0» when
five of them (AI, EOM, ITP, SS, TX) had moved to 1.3.0 (`ACCESS-COMPARE-JUDGE-FIXES-01`, finding 6).
A reader of the screen «Настройки анализа» sees the real version, so a note that lists others says
something untrue. This test reads every ``profile.json`` ``profile_version`` of the text profiles and
the newest note that quotes them together. Until 0.10.0 that was always the note of the current
``VERSION``; the 0.10.0 and 0.11.0 notes do not talk about the profiles, so the judged note is the
newest one that does (0.9.0 on that tree), and a later note that quotes them takes its place.

How a note quotes versions, and what each form covers (``x`` stands for any patch number):

* one exact version, ``1.2.0``, covers that version;
* a range, «с 1.1.0 по 1.3.x» or «от 1.1.0 до 1.3.x», covers every version from the first to the last,
  both ends included;
* a list, «1.1.0 или 1.2.0» or «1.1.0, 1.2.0», covers exactly the versions it names.

An item that talks about the profiles (the word «профил») and quotes at least one version must cover
every ``profile_version`` of the packages. An item that quotes no version is not judged here.

One section may be left out by name. `HOTFIX-AR-ORIGINAL-PROFILE-INT-20261030` added a fifteenth package, the
draft АР text profile at 1.0.0, beside the fourteen reviewed ones, and the note says «14 разделов, кроме АР».
An item that writes «кроме АР» (the section code after «кроме», see ``SECTION_NAMES``) states a version range
for the other profiles only, so the excluded one is not required to be inside that range. The exclusion names
sections, never versions: any other profile the range leaves out is still reported.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROFILES = ROOT / "src" / "auditmanager" / "analysis" / "text" / "profiles"

VERSION = r"\d+\.\d+\.(?:\d+|x)"
RANGE = re.compile(rf"(?:с|от)\s+(?P<low>{VERSION})\s+(?:по|до)\s+(?P<high>{VERSION})")
TOKEN = re.compile(VERSION)
INFINITY = 10**9
#: «кроме АР»: how an item names the section it leaves out of the versions it quotes.
EXCEPT = re.compile(r"кроме\s+(?P<name>[А-ЯЁ]{2,4})(?![А-Яа-яЁё])")
#: The Cyrillic spelling a note uses for the section codes of the packages (the directory name, upper-cased).
#: Only the sections a note has a reason to leave out are listed; a section missing here cannot be excluded.
SECTION_NAMES = {"AR": "АР"}


def parse(token: str, *, upper: bool) -> tuple[int, int, int]:
    major, minor, patch = token.split(".")
    if patch == "x":
        return int(major), int(minor), INFINITY if upper else 0
    return int(major), int(minor), int(patch)


def covered(text: str, version: str) -> bool:
    """Whether the quoted versions and ranges of ``text`` include ``version``."""
    target = parse(version, upper=False)
    ranges = list(RANGE.finditer(text))
    for found in ranges:
        if parse(found.group("low"), upper=False) <= target <= parse(found.group("high"), upper=True):
            return True
    outside = text
    for found in reversed(ranges):
        outside = outside[: found.start()] + " " + outside[found.end():]
    for token in TOKEN.findall(outside):
        if parse(token, upper=False) <= target <= parse(token, upper=True):
            return True
    return False


def quotes_a_version(text: str) -> bool:
    return TOKEN.search(text) is not None


def profile_versions() -> dict[str, str]:
    return {
        path.parent.name: json.loads(path.read_text(encoding="utf-8"))["profile_version"]
        for path in sorted(PROFILES.glob("*/profile.json"))
    }


def excluded(text: str) -> set[str]:
    """The upper-cased section codes an item leaves out by name («кроме АР»)."""
    named = {found.group("name") for found in EXCEPT.finditer(text)}
    return {code for code, name in SECTION_NAMES.items() if name in named}


def uncovered(items: list[dict], versions: dict[str, str]) -> list[tuple[int, str]]:
    """``(item number, section)`` for every profile left out of an item that quotes versions."""
    missing: list[tuple[int, str]] = []
    for number, item in enumerate(items, start=1):
        text = item["text"]
        if "профил" not in text.lower() or not quotes_a_version(text):
            continue
        left_out = excluded(text)
        missing.extend(
            (number, code)
            for code, version in versions.items()
            if code.upper() not in left_out and not covered(text, version)
        )
    return missing


def quoting_items(note: dict) -> list[dict]:
    return [i for i in note["items"] if "профил" in i["text"].lower() and quotes_a_version(i["text"])]


def current_note() -> dict:
    """The newest note at or below ``VERSION`` whose items quote profile versions."""
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    ceiling = tuple(int(part) for part in version.split("."))
    notes = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (ROOT / "release-notes").glob("*.json")
        if path.name not in {"schema.json", "dictionary.json"}
    ]
    notes.sort(key=lambda note: tuple(int(part) for part in note["version"].split(".")), reverse=True)
    for note in notes:
        if tuple(int(part) for part in note["version"].split(".")) <= ceiling and quoting_items(note):
            return note
    raise AssertionError("no release note quotes the profile versions; this test has nothing to judge")


def test_there_are_fifteen_profiles_each_with_a_version() -> None:
    versions = profile_versions()
    # fourteen reviewed sections, plus the draft АР profile `HOTFIX-AR-ORIGINAL-PROFILE-INT-20261030` added
    assert len(versions) == 15, sorted(versions)
    assert "ar" in versions, sorted(versions)
    assert all(re.fullmatch(r"\d+\.\d+\.\d+", v) for v in versions.values()), versions


def test_the_current_note_quotes_a_range_that_holds_every_profile_version() -> None:
    note = current_note()
    versions = profile_versions()
    quoting = quoting_items(note)
    assert quoting, "no item of the current note quotes the profile versions; this test has nothing to judge"
    assert uncovered(note["items"], versions) == [], (
        f"release note {note['version']} quotes profile versions that leave a profile out; "
        f"the packages are at {sorted(set(versions.values()))}"
    )


def test_the_check_can_fail() -> None:
    versions = {"AI": "1.3.0", "KJ": "1.2.0", "PB": "1.1.0"}
    old = "У профилей анализа 14 разделов версия 1.1.0 или 1.2.0 и состояние «проверен»."
    assert covered(old, "1.1.0") and covered(old, "1.2.0") and not covered(old, "1.3.0")
    assert uncovered([{"text": old}], versions) == [(1, "AI")]
    # the repaired wording, and a patch release inside the last minor
    new = "У профилей анализа 14 разделов версии с 1.1.0 по 1.3.x и состояние «проверен»."
    assert uncovered([{"text": new}], versions) == []
    assert uncovered([{"text": new}], {**versions, "AI": "1.3.1", "TX": "1.3.12"}) == []
    # a range that stops early, or starts late, leaves a profile out
    assert uncovered([{"text": "У профилей версии с 1.1.0 по 1.2.x."}], versions) == [(1, "AI")]
    assert uncovered([{"text": "У профилей версии от 1.2.0 до 1.3.x."}], versions) == [(1, "PB")]
    assert uncovered([{"text": "У профилей версии от 1.1.0 до 1.3.0."}], {**versions, "AI": "1.3.1"}) == [(1, "AI")]
    # a list covers exactly what it names, and a lone exact version covers only itself
    assert uncovered([{"text": "У профилей версии 1.1.0, 1.2.0 и 1.3.0."}], versions) == []
    assert uncovered([{"text": "Профиль АР версии 1.2.0."}], versions) == [(1, "AI"), (1, "PB")]
    # an item that is not about profiles, or quotes no version, is not judged
    assert uncovered([{"text": "Кнопка версии 9.9.9 появилась."}], versions) == []
    assert uncovered([{"text": "У профилей новое состояние."}], versions) == []
    # a range covers its middle and both ends, and nothing beyond them
    closed = "У профилей версии с 1.1.0 по 1.3.0."
    assert [covered(closed, v) for v in ("1.1.0", "1.2.0", "1.3.0", "1.3.1", "1.0.9")] == [
        True, True, True, False, False,
    ]
    # one section may be left out by name, and only the one named
    with_ar = {**versions, "ar": "1.0.0"}
    excluding = "У профилей анализа 14 разделов, кроме АР, версии с 1.1.0 по 1.3.x."
    assert uncovered([{"text": excluding}], with_ar) == []
    assert uncovered([{"text": "У профилей анализа 14 разделов версии с 1.1.0 по 1.3.x."}], with_ar) == [(1, "ar")]
    assert uncovered([{"text": "У профилей анализа, кроме АР, версии с 1.2.0 по 1.3.x."}], with_ar) == [(1, "PB")]
    assert uncovered([{"text": "У профилей, кроме АРХ, версии с 1.1.0 по 1.3.x."}], with_ar) == [(1, "ar")]
    # a section code `SECTION_NAMES` does not list cannot be excluded: the item still has to cover it
    assert uncovered([{"text": "У профилей, кроме КЖ, версии с 1.1.0 по 1.1.x."}], versions) == [(1, "AI"), (1, "KJ")]
    # the exclusion is read from the item's own words
    assert excluded(excluding) == {"AR"} and excluded("У профилей версии с 1.1.0 по 1.3.x.") == set()
