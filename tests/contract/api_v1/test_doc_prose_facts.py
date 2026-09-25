"""`D-79`: three facts this programme's live prose states about the tree, checked against it.

`test_surface_counts_in_prose.py` answers "does prose in `src/`, `infra/deploy/` and
`web/src` agree with the surface `contracts/api/v1/openapi.json` declares" and does not
read `docs/` at all -- so `docs/program/CURRENT_STATE.md` went stale **six waves**, once
inside the very note written to record that it had already happened once (`D-79`). This
module is the second half of that row: it reads the documents `AGENTS.md` makes every
session's first stop, or that a reviewer runs by hand, and checks three facts a session
reading only its own brief has no other way to catch:

* the **migration head** a prose sentence names, against the real revision graph in
  ``db/migrations/versions/``;
* the **contract surface triple** (`N paths / N operations / N schemas`) a prose sentence
  states together, against the frozen OpenAPI document;
* the **tagged tip** a prose sentence says a wave closed as, against the `alpha-w*` tags
  this repository actually carries.

**A record is not a claim, and a guard that cannot tell them apart would force this
programme to falsify its own history.** `docs/program/W30-CERT3.md` correctly names
migration head `0005` at commit `ac7c348` -- that was the head *then*. Two structural
rules keep this guard off wave reports and off a live document's own history section,
neither of which is "does this file mention an old date":

1. **Scope is a fixed, named set of documents**, exactly as `SCANNED_TREES` in the sibling
   module is a fixed set of trees rather than "everything under `src/`". Wave reports
   (`docs/program/W30-CERT3.md`, `W37-CERT4.md`, ...) are simply never in it --
   :func:`test_wave_reports_are_never_scanned` asserts that by name, not by pattern, so a
   new report file does not have to be excluded by guessing its shape.
2. **`CURRENT_STATE.md` marks its own history.** Its "Where the programme is" section is
   the live claim; everything from `## Previous release state -- wave 43 (historical
   record)` onward is the file's own record of a past wave, in the file's own words. This
   guard reads only the prefix before that heading -- :func:`_scanned_documents` truncates
   there, and :func:`test_the_historical_section_is_excluded_from_the_live_scan` proves it
   with content unique to each side.

`ALPHA_ROADMAP.md` has no such heading; instead its one correction note narrates an old,
superseded triple in the same paragraph as the current one ("The surface is 13 paths / 16
operations / 48 schemas after wave 34's reseal ... so it is 15 paths / 18 operations / 51
schemas"). That old triple is registered in :data:`KNOWN_HISTORICAL_TRIPLES` by its exact
text and file, the same mechanism `LOCAL_COUNTS` uses next door for a true-but-not-the-
surface phrase -- never a heuristic about tense or nearby words, because a heuristic is
exactly the kind of query that can share an assumption with what it is checking
(`OPERATING_CONSTRAINTS.md` §12).

**One exception is registered and it is a finding, not a fix.** `docs/manual-tests/PC-
01_prototype.md` -- a runbook a reviewer runs today, not a wave report -- states "Observe
the migration head is `0008_sign_in_throttle`", which is stale: the tree's head has been
`0010_run_terminal_detail` since wave 42. This is the exact defect class `D-79` names,
found live rather than injected, and `docs/manual-tests/**` is not in this task's
`allowed_paths` -- so it is registered in :data:`KNOWN_OUTSTANDING_CLAIMS` with a citation
rather than silently passed over or silently edited, and reported to the integrator.
Removing the entry is the acceptance test for whoever owns that file next.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
from dataclasses import dataclass
from typing import Iterator

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

API_CONTRACT = REPO_ROOT / "contracts" / "api" / "v1" / "openapi.json"
ERROR_CATALOG = REPO_ROOT / "contracts" / "domain" / "v1" / "error-codes.json"
MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations" / "versions"

CURRENT_STATE = REPO_ROOT / "docs" / "program" / "CURRENT_STATE.md"
ALPHA_ROADMAP = REPO_ROOT / "docs" / "program" / "ALPHA_ROADMAP.md"
MANUAL_TESTS_DIR = REPO_ROOT / "docs" / "manual-tests"

#: The exact heading `CURRENT_STATE.md` uses to mark its own history. Matched by the
#: literal phrase the file's own prose uses ("historical record"), not by a wave number,
#: so the boundary moves with the file rather than needing an edit every close-out.
_HISTORICAL_HEADING = re.compile(r"^#+.*historical record.*$", re.IGNORECASE | re.MULTILINE)

_METHODS = frozenset({"get", "put", "post", "delete", "options", "head", "patch", "trace"})

#: A line break inside prose, with an optional list/quote/comment continuation marker.
#: `>` is added to the sibling module's `_WRAP` because these documents wrap inside
#: blockquotes, and an unstripped `>` would sit between a number and its noun exactly
#: the way an unstripped `*` did there -- silently breaking the very claim it should
#: catch, for a reason that has nothing to do with the claim being true.
_WRAP = re.compile(r"\n[ \t]*(?:>[ \t]*)?(?:\*(?!/)|#)?[ \t]*")


def _unwrap(text: str) -> str:
    return _WRAP.sub(" ", text)


# ---------------------------------------------------------------------------
# Ground truth -- each computed from a source that shares no assumption with the
# regexes below it, per OPERATING_CONSTRAINTS.md §12.
# ---------------------------------------------------------------------------


def _true_migration_head() -> str:
    """The one revision id that is nobody's `down_revision`.

    Read from `db/migrations/versions/*.py` by the same two fields Alembic itself
    resolves the graph from, not from a count of files or a filename sort -- a branch
    would make either of those wrong silently.
    """
    revisions: dict[str, str | None] = {}
    for path in sorted(MIGRATIONS_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        # The type annotation varies across this history ("revision: str = ...", plain
        # "revision = ..." in the earliest files) -- skipped as arbitrary non-`=` text
        # rather than pinned to one spelling, so a future annotation style does not
        # silently stop matching.
        revision = re.search(r'^revision\s*(?::[^=\n]+)?=\s*"([^"]+)"', text, re.MULTILINE)
        down = re.search(
            r'^down_revision\s*(?::[^=\n]+)?=\s*(None|"([^"]+)")', text, re.MULTILINE
        )
        assert revision, f"{path}: no `revision = \"...\"` found"
        assert down, f"{path}: no `down_revision = ...` found"
        revisions[revision.group(1)] = down.group(2)
    children = set(revisions.values())
    heads = [rev for rev in revisions if rev not in children]
    assert len(heads) == 1, f"expected exactly one migration head, found {heads}"
    return heads[0]


@dataclass(frozen=True)
class SurfaceTriple:
    paths: int
    operations: int
    schemas: int


def _true_surface_triple() -> SurfaceTriple:
    document = json.loads(API_CONTRACT.read_text(encoding="utf-8"))
    operations = sum(
        1
        for item in document["paths"].values()
        for method in item
        if method.lower() in _METHODS
    )
    return SurfaceTriple(
        paths=len(document["paths"]),
        operations=operations,
        schemas=len(document["components"]["schemas"]),
    )


def _true_tagged_tip() -> str:
    """The highest `alpha-w<N>[.<M>]` tag this repository carries, by wave number.

    Read from git, never from a document -- a tag is the one thing in this row that is
    not itself prose. `alpha-w43` and `alpha-w43.1` both exist (`CURRENT_STATE.md`: "a
    tag is a record; moving it would have erased the fact"); the `.1` sorts after.
    """
    completed = subprocess.run(
        ["git", "tag", "--list", "alpha-w*"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, f"git tag --list failed: {completed.stderr}"
    tags = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    assert tags, "no alpha-w* tags found at all -- the ground truth itself is broken"

    def sort_key(tag: str) -> tuple[int, int]:
        match = re.fullmatch(r"alpha-w(\d+)(?:\.(\d+))?", tag)
        assert match, f"tag {tag!r} does not fit the alpha-w<N>[.<M>] shape this reads"
        return (int(match.group(1)), int(match.group(2) or 0))

    return max(tags, key=sort_key)


# ---------------------------------------------------------------------------
# Claim extraction
# ---------------------------------------------------------------------------

#: `Migration head: \`0010_run_terminal_detail\`.`, `confirmed migration head
#: \`0010_run_terminal_detail\`,`, `the migration head remains **0010**`, `Observe the
#: migration head is \`0008_sign_in_throttle\``. Anchored on the phrase "migration head"
#: with no connector word required between it and the value, because the connector
#: varies ("is", ":", "remains", or nothing at all across a line wrap) and the anchor
#: phrase is what actually marks this as a claim about the head.
MIGRATION_HEAD_CLAIM = re.compile(
    r"migration head[^\n]{0,15}?`?(?P<value>[0-9]{4})(?:_[a-z0-9]+)?`?", re.IGNORECASE
)

#: `15 paths / 18 operations / 51 schemas`. The one idiom both live documents use to
#: state the triple together; a bare `18 operations` alone is `D-23`'s guard's subject
#: in code, not this one's in docs.
SURFACE_TRIPLE_CLAIM = re.compile(
    r"(?P<paths>\d{1,3})\s*paths?\s*/\s*(?P<operations>\d{1,3})\s*operations?\s*/\s*"
    r"(?P<schemas>\d{1,3})\s*schemas?",
    re.IGNORECASE,
)

#: `Wave 44 is closed as \`alpha-w44\`.` Deliberately narrow: the top-of-file correction
#: block in `CURRENT_STATE.md` also contains `tagged \`alpha-w30\`` and `tagged
#: \`alpha-w40\`` in the course of narrating that the file once wrongly named the first as
#: current -- both true statements about the past, neither a claim about now. "closed as"
#: is the one phrase this programme uses to assert the current tip; "tagged" alone is used
#: for both the record and the claim and is not a safe anchor.
TAGGED_TIP_CLAIM = re.compile(r"closed as `(?P<tag>alpha-w[0-9.]+)`", re.IGNORECASE)


def _migration_head_claims(text: str) -> Iterator[re.Match[str]]:
    yield from MIGRATION_HEAD_CLAIM.finditer(_unwrap(text))


def _surface_triple_claims(text: str) -> Iterator[re.Match[str]]:
    yield from SURFACE_TRIPLE_CLAIM.finditer(_unwrap(text))


def _tagged_tip_claims(text: str) -> Iterator[re.Match[str]]:
    yield from TAGGED_TIP_CLAIM.finditer(_unwrap(text))


# ---------------------------------------------------------------------------
# Scope -- a fixed, named set of documents. `docs/program/W30-CERT3.md` and every other
# wave report is never in it: nothing below discovers files by globbing `docs/program/`,
# which is what would have to change for a report to enter scope by accident.
# ---------------------------------------------------------------------------


def _scanned_documents() -> list[tuple[str, str]]:
    """`(path relative to repo root, text this guard actually reads)` pairs."""
    named = [CURRENT_STATE, ALPHA_ROADMAP, *sorted(MANUAL_TESTS_DIR.rglob("*.md"))]
    out: list[tuple[str, str]] = []
    for path in named:
        text = path.read_text(encoding="utf-8")
        if path == CURRENT_STATE:
            boundary = _HISTORICAL_HEADING.search(text)
            assert boundary, "CURRENT_STATE.md no longer carries its historical-record heading"
            text = text[: boundary.start()]
        out.append((str(path.relative_to(REPO_ROOT)), text))
    return out


#: `(file, exact matched phrase)` -- a superseded triple narrated inside a correction
#: note, never the current one. The same mechanism as `LOCAL_COUNTS` next door: a phrase
#: registry, not a rule about tense, so registering it is a decision a person makes and
#: this docstring is where they explain it.
KNOWN_HISTORICAL_TRIPLES: frozenset[tuple[str, str]] = frozenset(
    {
        # ALPHA_ROADMAP.md's 2026-09-22 correction note: "The surface is 13 paths / 16
        # operations / 48 schemas after wave 34's reseal" -- the pre-wave-38/39 value,
        # two sentences before the note gives the current one ("so it is 15 paths / 18
        # operations / 51 schemas", which IS checked and currently agrees).
        ("docs/program/ALPHA_ROADMAP.md", "13 paths / 16 operations / 48 schemas"),
    }
)

#: `(file, exact matched phrase)` -- claims this guard would otherwise catch that ARE
#: currently wrong and are NOT fixed here, because the file is outside this task's
#: `allowed_paths`. Registering one is a report, not a silent fallback: each entry names
#: the row it belongs to, and the guard goes back to red on this file the moment the
#: entry is removed without the prose being corrected -- so it cannot be forgotten twice.
KNOWN_OUTSTANDING_CLAIMS: frozenset[tuple[str, str]] = frozenset(
    {
        # docs/manual-tests/PC-01_prototype.md:39, "Observe the migration head is
        # `0008_sign_in_throttle`" -- true head is 0010_run_terminal_detail since wave
        # 42. Found by W45-READY re-measuring D-79's premise; docs/manual-tests/** is
        # not in W45-READY's allowed_paths, so this is reported to the integrator, not
        # repaired here. Remove this entry when PC-01_prototype.md §1 is corrected.
        ("docs/manual-tests/PC-01_prototype.md", "migration head is `0008"),
    }
)


def _is_registered(file: str, matched_text: str, registry: frozenset[tuple[str, str]]) -> bool:
    return any(
        file == entry_file and matched_text.startswith(entry_text)
        for entry_file, entry_text in registry
    )


# ---------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------


def test_true_migration_head_is_a_real_single_head() -> None:
    assert _true_migration_head() == "0010_run_terminal_detail"


def test_true_surface_triple_matches_the_frozen_contract() -> None:
    triple = _true_surface_triple()
    assert triple == SurfaceTriple(paths=15, operations=18, schemas=51)


def test_true_tagged_tip_is_read_from_git_and_is_plausible() -> None:
    tip = _true_tagged_tip()
    assert re.fullmatch(r"alpha-w\d+(?:\.\d+)?", tip), tip


def test_the_guard_reaches_the_three_named_documents() -> None:
    scanned = {file for file, _ in _scanned_documents()}
    assert "docs/program/CURRENT_STATE.md" in scanned
    assert "docs/program/ALPHA_ROADMAP.md" in scanned
    assert "docs/manual-tests/PC-01_prototype.md" in scanned
    manual_test_files = [f for f in scanned if f.startswith("docs/manual-tests/")]
    assert len(manual_test_files) >= 10, sorted(manual_test_files)


def test_wave_reports_are_never_scanned() -> None:
    """`D-79`'s point, made structural: a record is out of scope by not being named."""
    scanned = {file for file, _ in _scanned_documents()}
    for report in ("docs/program/W30-CERT3.md", "docs/program/W37-CERT4.md"):
        assert (REPO_ROOT / report).exists(), f"{report} moved; re-pick a wave report to prove this with"
        assert report not in scanned


def test_the_historical_section_is_excluded_from_the_live_scan() -> None:
    """`CURRENT_STATE.md`'s own record of wave 43 is read by nobody's regex here."""
    full_text = CURRENT_STATE.read_text(encoding="utf-8")
    (scanned_text,) = (text for file, text in _scanned_documents() if file == "docs/program/CURRENT_STATE.md")
    assert len(scanned_text) < len(full_text)
    # Content that exists ONLY in the historical section:
    assert "c455848" in full_text and "c455848" not in scanned_text
    assert "wave 43 (historical record)" in full_text
    assert "wave 43 (historical record)" not in scanned_text
    # The live section's own claim survives the truncation:
    assert "closed as `alpha-w44`" in scanned_text


def test_the_scanned_docs_state_the_migration_head_this_tree_has() -> None:
    true_head = _true_migration_head()
    wrong: list[str] = []
    for file, text in _scanned_documents():
        for match in _migration_head_claims(text):
            if _is_registered(file, match.group(0), KNOWN_HISTORICAL_TRIPLES | KNOWN_OUTSTANDING_CLAIMS):
                continue
            if not true_head.startswith(match.group("value")):
                wrong.append(f"{file}: {match.group(0)!r} names head {match.group('value')}, tree has {true_head}")
    assert not wrong, (
        "prose states a migration head this tree does not have. Correct it by "
        "re-measuring db/migrations/versions/, or register it in "
        "KNOWN_HISTORICAL_TRIPLES / KNOWN_OUTSTANDING_CLAIMS with a citation if it is a "
        "record rather than a claim:\n  " + "\n  ".join(wrong)
    )


def test_the_scanned_docs_state_the_contract_surface_this_tree_has() -> None:
    truth = _true_surface_triple()
    wrong: list[str] = []
    for file, text in _scanned_documents():
        for match in _surface_triple_claims(text):
            if _is_registered(file, match.group(0), KNOWN_HISTORICAL_TRIPLES | KNOWN_OUTSTANDING_CLAIMS):
                continue
            claimed = SurfaceTriple(
                paths=int(match.group("paths")),
                operations=int(match.group("operations")),
                schemas=int(match.group("schemas")),
            )
            if claimed != truth:
                wrong.append(f"{file}: {match.group(0)!r} states {claimed}, tree has {truth}")
    assert not wrong, (
        "prose states a contract surface triple this tree does not have:\n  " + "\n  ".join(wrong)
    )


def test_the_scanned_docs_state_the_tagged_tip_this_tree_has() -> None:
    true_tip = _true_tagged_tip()
    wrong: list[str] = []
    for file, text in _scanned_documents():
        for match in _tagged_tip_claims(text):
            if _is_registered(file, match.group(0), KNOWN_HISTORICAL_TRIPLES | KNOWN_OUTSTANDING_CLAIMS):
                continue
            if match.group("tag") != true_tip:
                wrong.append(f"{file}: {match.group(0)!r} names {match.group('tag')}, tip is {true_tip}")
    assert not wrong, (
        "prose says a wave closed as a tag that is not the tagged tip:\n  " + "\n  ".join(wrong)
    )


def test_every_registered_claim_still_exists_and_is_still_wrong_or_historical() -> None:
    """A registry entry nobody checks is `D-76`'s shape: recorded and then forgotten.

    Each entry must still be found by the extractor (the sentence has not moved or been
    reworded out from under it) so a stale registration cannot silently stop meaning
    anything.
    """
    for file, text in _scanned_documents():
        found = (
            {m.group(0) for m in _migration_head_claims(text)}
            | {m.group(0) for m in _surface_triple_claims(text)}
            | {m.group(0) for m in _tagged_tip_claims(text)}
        )
        for entry_file, entry_text in KNOWN_HISTORICAL_TRIPLES | KNOWN_OUTSTANDING_CLAIMS:
            if entry_file != file:
                continue
            assert any(candidate.startswith(entry_text) for candidate in found), (
                f"{entry_file}: registered phrase {entry_text!r} was not found by any "
                "extractor any more -- remove the stale registry entry"
            )


# ---------------------------------------------------------------------------
# The guard, shown able to fail -- mirrors `test_surface_counts_in_prose.py`'s own
# red/green parametrization, on synthetic prose so no real document is mutated to prove
# it.
# ---------------------------------------------------------------------------


def test_a_stale_migration_head_claim_is_caught() -> None:
    true_head = _true_migration_head()
    claims = list(_migration_head_claims("Migration head: `0009_reviewer_display_name`."))
    assert claims and not true_head.startswith(claims[0].group("value"))


def test_the_current_migration_head_claim_is_not_caught() -> None:
    true_head = _true_migration_head()
    claims = list(_migration_head_claims(f"Migration head: `{true_head}`."))
    assert claims and true_head.startswith(claims[0].group("value"))


def test_a_stale_surface_triple_claim_is_caught() -> None:
    truth = _true_surface_triple()
    claims = list(_surface_triple_claims("The contract surface is 10 paths / 10 operations / 10 schemas."))
    assert claims
    claimed = SurfaceTriple(
        paths=int(claims[0].group("paths")),
        operations=int(claims[0].group("operations")),
        schemas=int(claims[0].group("schemas")),
    )
    assert claimed != truth


def test_the_current_surface_triple_claim_is_not_caught() -> None:
    truth = _true_surface_triple()
    prose = f"The contract surface is {truth.paths} paths / {truth.operations} operations / {truth.schemas} schemas."
    claims = list(_surface_triple_claims(prose))
    assert claims
    claimed = SurfaceTriple(
        paths=int(claims[0].group("paths")),
        operations=int(claims[0].group("operations")),
        schemas=int(claims[0].group("schemas")),
    )
    assert claimed == truth


def test_a_stale_tagged_tip_claim_is_caught() -> None:
    true_tip = _true_tagged_tip()
    claims = list(_tagged_tip_claims("Wave 30 is closed as `alpha-w30`."))
    assert claims and claims[0].group("tag") != true_tip


def test_the_current_tagged_tip_claim_is_not_caught() -> None:
    true_tip = _true_tagged_tip()
    claims = list(_tagged_tip_claims(f"Wave N is closed as `{true_tip}`."))
    assert claims and claims[0].group("tag") == true_tip


def test_a_tagged_tip_mention_that_is_not_the_closed_as_idiom_is_not_a_claim() -> None:
    """The exact case this guard must NOT read as current: a record narrating an old tag."""
    record = "it named `origin/main` as `f96c23a` tagged `alpha-w30` when the tip was `6aeda82` tagged `alpha-w40`"
    assert not list(_tagged_tip_claims(record))


def test_a_wrapped_migration_head_claim_across_a_line_break_is_still_one_claim() -> None:
    wrapped = "confirmed migration head\n`0010_run_terminal_detail`, received 401"
    assert not list(MIGRATION_HEAD_CLAIM.finditer(wrapped)), "the raw text should not match"
    claims = list(_migration_head_claims(wrapped))
    assert claims and claims[0].group("value") == "0010"


def test_a_wrapped_surface_triple_claim_inside_a_blockquote_is_still_one_claim() -> None:
    """The exact shape found live in `ALPHA_ROADMAP.md`'s blockquote correction note."""
    wrapped = "The surface is **13 paths / 16\n> operations / 48 schemas** after wave 34's reseal"
    assert not list(SURFACE_TRIPLE_CLAIM.finditer(wrapped)), "the raw text should not match"
    claims = list(_surface_triple_claims(wrapped))
    assert claims and claims[0].group("operations") == "16"


def test_the_known_historical_triple_is_registered_and_not_flagged() -> None:
    file, phrase = next(iter(KNOWN_HISTORICAL_TRIPLES))
    assert _is_registered(file, phrase, KNOWN_HISTORICAL_TRIPLES)
    assert not _is_registered(file, phrase, frozenset())


def test_the_known_outstanding_claim_is_registered_and_not_silently_absent() -> None:
    """The exception exists, is documented, and is a real defect -- not swept away."""
    file, phrase = next(iter(KNOWN_OUTSTANDING_CLAIMS))
    assert file == "docs/manual-tests/PC-01_prototype.md"
    true_head = _true_migration_head()
    # The registered claim really does disagree with the truth -- proving the exception
    # is suppressing a live defect, not a dead one that stopped mattering.
    match = MIGRATION_HEAD_CLAIM.search(phrase)
    assert match and not true_head.startswith(match.group("value"))
