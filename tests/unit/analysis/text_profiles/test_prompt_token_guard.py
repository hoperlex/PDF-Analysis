"""SECTION-PROMPT-TOKEN-GUARD-01 (D-224): every designation in a section prompt has a source.

The 14 ``system_prompt.md`` files under ``src/auditmanager/analysis/text/profiles/`` are edited by
hand. A section lane may add a sentence, and a later edit with a consistent recording rebuild
passes every other test, so nothing read the *content* of those sentences. This suite reads it:

* it extracts from each prompt every **whole token** that carries a digit, a letter outside
  Cyrillic (Latin, in practice), two or more capital letters (an abbreviation such as ``ИТР`` or a
  mixed-case one such as ``СНиП``) or is a hyphenated code (``Т-образный``);
* it requires that token to be a whole token of (a) the union of the section's five pinned
  legacy files, hash-verified at the commit ``profile.json`` names, or (b) the v1 prompt
  ``src/auditmanager/analysis/text/prompt.py``, or (c) ``prompt_token_allowlist.json``, which
  gives a reason, the lane report that disclosed it and, for anything that could be a class
  designation, a cable marking or a norm number, ``"class": "a"`` and a justification.

**Whole tokens, not substrings.** The audits the section lanes ran outside the repository
matched substrings: ``LS`` was found inside ``FRLS``, ``КМ`` inside ``КМ0–КМ5``. Here a token
is a maximal run of letters and digits, with a decimal comma or point between digits and a
hyphen between words kept inside the token (``Е0,5``, ``123-ФЗ``, ``PE-проводника``); an en or
em dash, a slash, a parenthesis and an underscore separate tokens. Matching is exact: case,
script (Cyrillic ``Е`` is not Latin ``E``) and every character count. A hyphen-joined token is one
token on both sides: ``LS`` is not sourced by ``нг-LS`` (decided by the lane: no current prompt
token needed the looser reading, and the looser one can only hide an invention).

The legacy repository is not on every host. The part that needs it skips with an explicit reason
string; the part that does not (tokenizer, class rules, allowlist hygiene, PB which has no
legacy source, the in-memory mutations) always runs, so the guard cannot go quiet by itself.
"""

from __future__ import annotations

import functools
import hashlib
import json
import os
import re
import subprocess
import unicodedata
from pathlib import Path
from typing import Any

import pytest

from auditmanager.analysis.text.prompt import SYSTEM_PROMPT

ROOT = Path(__file__).resolve().parents[4]
PROFILES = ROOT / "src/auditmanager/analysis/text/profiles"
DOCS = ROOT / "docs/program"
ALLOWLIST = Path(__file__).resolve().with_name("prompt_token_allowlist.json")
LEGACY = Path(os.environ.get("AUDITMANAGER_LEGACY_PROMPTS_REPO", "/root/projects/PDF-proverka"))

ALLOWLIST_FORMAT = "prompt-token-allowlist/1"
ENTRY_KEYS = frozenset({"section", "token", "reason", "disclosed_by"})
CLASS_A_KEYS = ENTRY_KEYS | {"class", "justification"}
#: Token classes that can be a class designation, a cable marking or a norm number.
CLASS_A_REQUIRED = frozenset({"digit", "latin", "hyphen-code"})
MIN_TEXT = 40  # characters of a reason / justification that are more than a shrug

# --- the tokenizer ------------------------------------------------------------------------

HYPHENS = "-\u2010\u2011"  # hyphen-minus, hyphen, non-breaking hyphen
#: A maximal run of letters and digits; an underscore is a separator (``___`` is no token).
_RUN = r"[^\W_]+"
#: A decimal comma or point between two digits stays inside the token (``0,000``, ``Е0,5``).
_WORD = rf"{_RUN}(?:(?<=\d)[.,](?=\d){_RUN})*"
TOKEN = re.compile(rf"{_WORD}(?:[{HYPHENS}]{_WORD})*")
HYPHEN_SPLIT = re.compile(f"[{HYPHENS}]")
CYRILLIC = re.compile(r"[\u0400-\u04ff]")
#: A part of a hyphenated token that is an ordinary word: optional capital, then lower case.
ORDINARY_WORD = re.compile(r"[А-ЯЁ]?[а-яё]{2,}")


def tokens(text: str) -> list[str]:
    """Every whole token of ``text`` in order (NFC, so a decomposed ``й`` does not split)."""
    return [match.group(0) for match in TOKEN.finditer(unicodedata.normalize("NFC", text))]


def token_class(token: str) -> str | None:
    """Why a token is a designation, or ``None`` for an ordinary word or a bare number-less word."""
    if any(char.isdigit() for char in token):
        return "digit"
    if any(char.isalpha() and not CYRILLIC.match(char) for char in token):
        return "latin"
    if sum(char.isupper() for char in token) >= 2:
        return "abbreviation"
    parts = HYPHEN_SPLIT.split(token)
    if len(parts) > 1 and any(not ORDINARY_WORD.fullmatch(part) for part in parts):
        return "hyphen-code"
    return None


def designations(text: str) -> frozenset[str]:
    """The whole tokens of ``text`` that the guard requires a source for."""
    return frozenset(token for token in tokens(text) if token_class(token) is not None)


def universe(text: str) -> frozenset[str]:
    """Every whole token of ``text``: the set a prompt token has to be a member of."""
    return frozenset(tokens(text))


def unexplained(
    prompt: str,
    *,
    v1: frozenset[str],
    source: frozenset[str],
    allowed: frozenset[str],
) -> list[str]:
    """The designations of ``prompt`` that are in none of (a) source, (b) v1, (c) the allowlist."""
    return sorted(designations(prompt) - source - v1 - allowed)


# --- the data under test ------------------------------------------------------------------

V1 = universe(SYSTEM_PROMPT)
EXPECTED_SECTIONS = frozenset(
    {"AI", "PS", "POS", "TX", "KJ", "KM", "OV", "VK", "PT", "EOM", "SS", "ITP", "GP", "PB"}
)


def _sections() -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for directory in sorted(path for path in PROFILES.iterdir() if path.is_dir()):
        manifest = json.loads((directory / "profile.json").read_text("utf-8"))
        found[manifest["section_code"]] = {
            "manifest": manifest,
            "prompt": (directory / "system_prompt.md").read_text("utf-8"),
        }
    return found


SECTIONS = _sections()
SOURCED = sorted(code for code, data in SECTIONS.items() if data["manifest"]["source"] is not None)
UNSOURCED = sorted(set(SECTIONS) - set(SOURCED))


RAW_ALLOWLIST = json.loads(ALLOWLIST.read_text("utf-8"))
ENTRIES: list[dict[str, Any]] = RAW_ALLOWLIST["entries"]


def allowed_for(code: str, entries: list[dict[str, Any]] = ENTRIES) -> frozenset[str]:
    return frozenset(entry["token"] for entry in entries if entry["section"] == code)


def without(entry: dict[str, Any]) -> list[dict[str, Any]]:
    return [other for other in ENTRIES if other is not entry]


@functools.lru_cache(maxsize=None)
def _legacy_blob(commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(LEGACY), "show", f"{commit}:{path}"], check=True, capture_output=True
    ).stdout


def _legacy_skip_reason(commit: str) -> str | None:
    """Why the legacy-dependent part cannot run on this host, or ``None`` when it can."""
    if not (LEGACY / ".git").exists():
        return (
            f"legacy repository {LEGACY} is not on this host "
            "(set AUDITMANAGER_LEGACY_PROMPTS_REPO); the sourced-token check is skipped, "
            "allowlist hygiene and PB still run"
        )
    probe = subprocess.run(
        ["git", "-C", str(LEGACY), "cat-file", "-e", f"{commit}^{{commit}}"], capture_output=True
    )
    if probe.returncode != 0:
        return f"commit {commit} is not in {LEGACY}; the sourced-token check is skipped"
    return None


@functools.lru_cache(maxsize=None)
def source_universe(code: str) -> frozenset[str]:
    """The tokens of the section's five pinned legacy files, hash-verified; skips if absent."""
    source = SECTIONS[code]["manifest"]["source"]
    reason = _legacy_skip_reason(source["commit"])
    if reason is not None:
        pytest.skip(reason)
    found: set[str] = set()
    for entry in source["files"]:
        blob = _legacy_blob(source["commit"], entry["path"])
        assert hashlib.sha256(blob).hexdigest() == entry["sha256"], (
            f"{code}: {entry['path']} at {source['commit']} no longer matches the hash in profile.json"
        )
        found |= universe(blob.decode("utf-8"))
    return frozenset(found)


# =========================================================================================
# Part 1 — always runs: the tokenizer, the rules, the allowlist, PB, the in-memory mutations
# =========================================================================================


def test_the_guard_reads_exactly_the_fourteen_section_prompts() -> None:
    # Guard the guard: a parametrisation over an empty directory would pass vacuously.
    assert set(SECTIONS) == EXPECTED_SECTIONS
    assert len(SOURCED) == 13 and UNSOURCED == ["PB"]
    for code, data in SECTIONS.items():
        assert len(designations(data["prompt"])) > 20, f"{code}: the extraction found almost nothing"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("(FRLS/FR)", ["FRLS", "FR"]),
        ("нг(А)-LS", ["нг", "А", "LS"]),
        ("(Г1–Г4)", ["Г1", "Г4"]),
        ("КМ0–КМ5", ["КМ0", "КМ5"]),
        ("класс Е1, Е0,5", ["класс", "Е1", "Е0,5"]),
        ("±0,000 и 1.2.3", ["0,000", "и", "1.2.3"]),
        ("123-ФЗ", ["123-ФЗ"]),
        ("PE-проводника", ["PE-проводника"]),
        ("«___», «(?)», finding_text", ["finding", "text"]),
        ("5. Утверждения", ["5", "Утверждения"]),
        ("и\u0306", ["й"]),  # a decomposed й is one token after NFC
    ],
)
def test_the_tokenizer_returns_whole_tokens(text: str, expected: list[str]) -> None:
    assert tokens(text) == expected


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("Е0,5", "digit"),
        ("13130", "digit"),
        ("123-ФЗ", "digit"),
        ("FRLS", "latin"),
        ("Kvs", "latin"),
        ("PE-проводника", "latin"),
        ("Ε", "latin"),  # Greek capital epsilon: a letter outside Cyrillic is never a plain word
        ("ГПЗУ", "abbreviation"),
        ("СНиП", "abbreviation"),
        ("СанПиН", "abbreviation"),
        ("ТВ-выводов", "abbreviation"),
        ("А-А", "abbreviation"),
        ("Т-образный", "hyphen-code"),  # one capital letter alone as a part: a code, not a word
        ("Кабель-канал", None),
        ("тамбур-шлюзов", None),
        ("Утверждения", None),
        ("уточнить", None),
        ("И", None),
    ],
)
def test_the_token_classes(token: str, expected: str | None) -> None:
    assert token_class(token) == expected


def test_a_substring_of_a_sourced_token_is_not_sourced() -> None:
    """The failure of the earlier audits: ``LS`` in ``FRLS``, ``КМ`` in ``КМ0``, ``PE`` in ``PEN``."""
    none = frozenset()
    source = universe("кабель FRLS, отделка КМ0–КМ5 и КМ1, шина PEN, марка Ex d")
    assert unexplained("LS", v1=none, source=source, allowed=none) == ["LS"]
    assert unexplained("КМ", v1=none, source=source, allowed=none) == ["КМ"]
    assert unexplained("PE", v1=none, source=source, allowed=none) == ["PE"]
    assert unexplained("FRL", v1=none, source=source, allowed=none) == ["FRL"]
    # and the whole tokens themselves pass
    assert unexplained("FRLS КМ0 КМ5 КМ1 PEN", v1=none, source=source, allowed=none) == []


def test_matching_is_exact_in_case_script_and_characters() -> None:
    none = frozenset()
    source = universe("Ex d, Kvs, Е1, E0")  # Е1 is Cyrillic, E0 is Latin
    assert unexplained("Ex", v1=none, source=source, allowed=none) == []
    assert unexplained("EX", v1=none, source=source, allowed=none) == ["EX"]
    assert unexplained("KVS", v1=none, source=source, allowed=none) == ["KVS"]
    assert unexplained("Е1", v1=none, source=source, allowed=none) == []
    assert unexplained("E1", v1=none, source=source, allowed=none) == ["E1"]  # Latin E, Cyrillic Е1 in source
    assert unexplained("Е0", v1=none, source=source, allowed=none) == ["Е0"]  # Cyrillic Е, Latin E0 in source
    assert unexplained("0,5", v1=none, source=universe("Е0,5"), allowed=none) == ["0,5"]
    assert unexplained("Е0.5", v1=none, source=universe("Е0,5"), allowed=none) == ["Е0.5"]


def test_a_hyphen_joined_token_is_one_token_on_both_sides() -> None:
    none = frozenset()
    source = universe("шины PE-шины и нг-LS, Г1-Г4")
    # the whole compound is not in the source: only its first part is a word there
    assert unexplained("PE-проводника", v1=none, source=source, allowed=none) == ["PE-проводника"]
    assert unexplained("PE-шины", v1=none, source=source, allowed=none) == []
    # a part of a hyphen-joined source token does not source the part alone (and the reverse)
    assert unexplained("LS", v1=none, source=source, allowed=none) == ["LS"]
    assert unexplained("Г4 Г1", v1=none, source=source, allowed=none) == ["Г1", "Г4"]
    assert unexplained("Г1-Г4 нг-LS", v1=none, source=source, allowed=none) == []
    # an en dash range is two tokens, each needing its own source
    assert unexplained("Г1–Г9", v1=none, source=universe("Г1 Г9"), allowed=none) == []
    assert unexplained("Г1–Г9", v1=none, source=source, allowed=none) == ["Г1", "Г9"]


def test_each_source_is_checked_separately_v1_and_allowlist_only_cover_their_own() -> None:
    none = frozenset()
    assert unexplained("ИТР", v1=none, source=none, allowed=none) == ["ИТР"]
    assert unexplained("ИТР", v1=none, source=none, allowed=frozenset({"ИТР"})) == []
    assert unexplained("ИТР", v1=frozenset({"ИТР"}), source=none, allowed=none) == []
    assert unexplained("ИТР", v1=none, source=frozenset({"ИТР"}), allowed=none) == []
    # the allowlist is per token: allowing ``ИТР`` does not allow ``ГПЗУ``
    assert unexplained("ИТР ГПЗУ", v1=none, source=none, allowed=frozenset({"ИТР"})) == ["ГПЗУ"]


def test_every_prompt_character_is_visible_so_a_token_cannot_be_split_unseen() -> None:
    for code, data in SECTIONS.items():
        for char in data["prompt"]:
            if char == "\n":
                continue
            category = unicodedata.category(char)
            assert category[0] != "C", f"{code}: control or format character {char!r} splits tokens unseen"
            assert not (category == "Zs" and char != " "), f"{code}: space character {char!r}"


# --- the allowlist ------------------------------------------------------------------------


def test_the_allowlist_has_the_documented_shape() -> None:
    assert set(RAW_ALLOWLIST) == {"format", "task", "entries"}, sorted(RAW_ALLOWLIST)
    assert RAW_ALLOWLIST["format"] == ALLOWLIST_FORMAT
    assert RAW_ALLOWLIST["task"] == "SECTION-PROMPT-TOKEN-GUARD-01"
    assert ENTRIES, "the allowlist is seeded from the findings of the audit; an empty one is a regression"
    seen: set[tuple[str, str]] = set()
    for entry in ENTRIES:
        keys = set(entry)
        assert keys in (ENTRY_KEYS, CLASS_A_KEYS), (entry.get("section"), entry.get("token"), sorted(keys))
        assert entry["section"] in SECTIONS, entry
        identity = (entry["section"], entry["token"])
        assert identity not in seen, f"duplicate allowlist entry {identity}"
        seen.add(identity)
        assert entry["token"] == unicodedata.normalize("NFC", entry["token"]), identity
        assert len(tokens(entry["token"])) == 1 and tokens(entry["token"])[0] == entry["token"], (
            f"{identity}: an entry is exactly one whole token"
        )
        assert len(entry["reason"].strip()) >= MIN_TEXT, f"{identity}: the reason is empty or a shrug"
        assert re.fullmatch(r"SECTION-(?:[A-Z]+-FULL|WIDEN-G[0-9]+)-01\.md", entry["disclosed_by"]), identity


def test_every_entry_names_a_report_that_contains_its_token() -> None:
    for entry in ENTRIES:
        report = DOCS / entry["disclosed_by"]
        identity = (entry["section"], entry["token"])
        assert report.is_file(), f"{identity}: {entry['disclosed_by']} does not exist"
        assert entry["token"] in unicodedata.normalize("NFC", report.read_text("utf-8")), (
            f"{identity}: {entry['disclosed_by']} never mentions the token it is said to disclose"
        )


def test_every_entry_still_appears_in_its_prompt_and_is_not_covered_by_v1() -> None:
    for entry in ENTRIES:
        identity = (entry["section"], entry["token"])
        found = designations(SECTIONS[entry["section"]]["prompt"])
        assert entry["token"] in found, f"{identity}: no longer in the prompt as a designation; delete the entry"
        assert entry["token"] not in V1, f"{identity}: v1's prompt already covers it; delete the entry"


def test_a_designation_like_entry_carries_class_a_and_a_justification() -> None:
    """No class designation, cable marking or norm number is allowed on a reason alone."""
    for entry in ENTRIES:
        identity = (entry["section"], entry["token"])
        kind = token_class(entry["token"])
        if kind in CLASS_A_REQUIRED:
            assert entry.get("class") == "a", f"{identity}: a {kind} token needs ``class: a``"
        if "class" in entry:
            assert entry["class"] == "a", identity
            assert len(entry["justification"].strip()) >= MIN_TEXT, f"{identity}: justification missing"


# --- PB has no legacy source: its whole audit always runs ---------------------------------


def test_pb_designations_are_all_in_v1_or_the_allowlist() -> None:
    prompt = SECTIONS["PB"]["prompt"]
    assert unexplained(prompt, v1=V1, source=frozenset(), allowed=allowed_for("PB")) == []


@pytest.mark.parametrize("entry", [e for e in ENTRIES if e["section"] == "PB"], ids=lambda e: e["token"])
def test_removing_a_pb_allowlist_entry_turns_the_audit_red(entry: dict[str, Any]) -> None:
    prompt = SECTIONS["PB"]["prompt"]
    reduced = allowed_for("PB", without(entry))
    assert unexplained(prompt, v1=V1, source=frozenset(), allowed=reduced) == [entry["token"]]


#: What a lane could paste into a prompt: a class designation, a cable marking, a norm number.
INSERTIONS = {
    "class designation": ("\nПри этом (класс Г9) указан. ", {"Г9"}),
    "cable marking": ("\nКабель ПвБШнг(А)-FRHFX уточнить. ", {"ПвБШнг", "FRHFX"}),
    "norm number": ("\nСмотри СП 999.1325800.2099 и ГОСТ 99999-2099. ", {"999.1325800.2099", "99999-2099"}),
}


@pytest.mark.parametrize("kind", sorted(INSERTIONS))
def test_inserting_an_invented_designation_into_the_pb_prompt_turns_the_audit_red(kind: str) -> None:
    sentence, expected = INSERTIONS[kind]
    assert not expected & (V1 | allowed_for("PB")), "the inserted tokens must be new for the test to prove anything"
    mutated = SECTIONS["PB"]["prompt"] + sentence
    assert set(unexplained(mutated, v1=V1, source=frozenset(), allowed=allowed_for("PB"))) == expected


# =========================================================================================
# Part 2 — needs the pinned legacy repository; skips with a reason when it is absent
# =========================================================================================


@pytest.mark.parametrize("code", SOURCED)
def test_every_designation_is_in_the_pinned_source_in_v1_or_the_allowlist(code: str) -> None:
    left = unexplained(
        SECTIONS[code]["prompt"], v1=V1, source=source_universe(code), allowed=allowed_for(code)
    )
    assert left == [], (
        f"{code}: designation(s) {left} are whole tokens of none of the five pinned legacy files, "
        "of v1's prompt, or of prompt_token_allowlist.json. Remove them from the prompt, or add an "
        "allowlist entry with a reason and the report that disclosed it (the integrator decides)."
    )


@pytest.mark.parametrize("entry", [e for e in ENTRIES if e["section"] != "PB"], ids=lambda e: f"{e['section']}-{e['token']}")
def test_no_allowlist_entry_is_already_sourced(entry: dict[str, Any]) -> None:
    source = source_universe(entry["section"])
    assert entry["token"] not in source, (
        f"{entry['section']}: {entry['token']!r} is a whole token of the pinned source now; delete the entry"
    )


@pytest.mark.parametrize("entry", [e for e in ENTRIES if e["section"] != "PB"], ids=lambda e: f"{e['section']}-{e['token']}")
def test_removing_an_allowlist_entry_turns_the_audit_red(entry: dict[str, Any]) -> None:
    code = entry["section"]
    left = unexplained(
        SECTIONS[code]["prompt"], v1=V1, source=source_universe(code), allowed=allowed_for(code, without(entry))
    )
    assert left == [entry["token"]]


@pytest.mark.parametrize("code", SOURCED)
@pytest.mark.parametrize("kind", sorted(INSERTIONS))
def test_inserting_an_invented_designation_turns_the_audit_red(code: str, kind: str) -> None:
    sentence, expected = INSERTIONS[kind]
    source = source_universe(code)
    assert not expected & (source | V1 | allowed_for(code)), "the inserted tokens must be new here"
    mutated = SECTIONS[code]["prompt"] + sentence
    assert set(unexplained(mutated, v1=V1, source=source, allowed=allowed_for(code))) == expected


def test_the_ai_km_case_is_a_substring_that_is_not_a_whole_token() -> None:
    """The real case that showed the earlier audits wrong: ``КМ`` is in the AI source only as ``КМ0``."""
    source = SECTIONS["AI"]["manifest"]["source"]
    reason = _legacy_skip_reason(source["commit"])
    if reason is not None:
        pytest.skip(reason)
    text = "".join(_legacy_blob(source["commit"], entry["path"]).decode("utf-8") for entry in source["files"])
    assert "КМ" in text, "a substring audit finds КМ in the source"
    assert "КМ" not in source_universe("AI"), "a whole-token audit does not"
    assert {"КМ0", "КМ5", "КМ1", "КМ2"} <= source_universe("AI")
    assert ("AI", "КМ") in {(entry["section"], entry["token"]) for entry in ENTRIES}
