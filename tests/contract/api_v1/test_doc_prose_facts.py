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
#:
#: Deliberately loose (any `#+` line, any level): `test_a_too_early_heading_outside_a_
#: fence_is_still_caught` below depends on a heading this loose still being *found* as
#: the (wrong) candidate boundary, so :func:`_historical_boundary`'s shape check has
#: something to catch it with. Tightening this pattern itself would make that mutation
#: invisible rather than caught (see that test's docstring).
_HISTORICAL_HEADING = re.compile(r"^#+.*historical record.*$", re.IGNORECASE | re.MULTILINE)

#: A fenced code block, ``` or ~~~, of three or more of the same character, closed by a
#: line starting with at least that many of the same character. `F-5c`'s first hole
#: (`X-4`): `_HISTORICAL_HEADING` is a bare line match with no notion of Markdown
#: structure, so a shell comment inside a fence -- `# the historical record below is
#: kept verbatim; do not edit it` -- is indistinguishable from a real heading to it.
_FENCED_CODE_BLOCK = re.compile(
    r"^([ \t]*)(`{3,}|~{3,})[^\n]*\n.*?^\1\2[ \t]*$", re.MULTILINE | re.DOTALL
)

#: What a *genuine* historical-record section heading looks like in this file, every
#: time it has been written so far: ``## Previous release state -- wave <N> (historical
#: record)``. `F-5c`'s second hole (`X-4`): a boundary chosen by `_HISTORICAL_HEADING`
#: alone can be *any* line that merely mentions the phrase, in a code fence or as a
#: subsection heading placed early on purpose -- and the old non-vacuity check ("at
#: least one claim survives") only catches this when the false boundary precedes every
#: claim, not when it falls after the first one and hides the rest. This is the shape
#: check that closes it: whichever line `_HISTORICAL_HEADING` finds first must also look
#: like this file's own convention for the real heading, or the guard refuses to use it
#: as a boundary at all -- deliberately loose on wording (`.*` between the fixed anchors)
#: so a phrasing change does not itself require an edit here, and deliberately strict on
#: shape (level two, "Previous release state", a wave number, "(historical record)" at
#: the end) so a heading that merely contains the marker phrase cannot pass as this one.
_GENUINE_HISTORICAL_HEADING_SHAPE = re.compile(
    r"^##\s+Previous release state\b.*\bwave\s+\d+.*\(historical record\)\s*$",
    re.IGNORECASE,
)


def _mask_fenced_code_blocks(text: str) -> str:
    """Every character inside a fenced code block, replaced with a non-heading filler.

    Length- and newline-preserving, so every offset :func:`_historical_boundary` reports
    is still a valid index into the *original*, unmasked text -- the same text
    :func:`_scanned_documents` slices.
    """

    def _mask(match: "re.Match[str]") -> str:
        return re.sub(r"[^\n]", "x", match.group(0))

    return _FENCED_CODE_BLOCK.sub(_mask, text)


def _historical_boundary(full_text: str) -> "re.Match[str]":
    """The one real historical-record heading this file's own convention writes.

    Two independent checks, for the two independent ways `F-5c` was found blind
    (`X-4`): the candidate is found outside every fenced code block
    (:func:`_mask_fenced_code_blocks`), and the candidate that is found must have the
    shape a genuine heading of this file always has
    (:data:`_GENUINE_HISTORICAL_HEADING_SHAPE`) -- not merely contain the marker
    phrase. Either check alone leaves the other hole open: fence-masking alone still
    lets a bare, early, non-fenced heading like judge A's through; the shape check
    alone, applied to an unmasked search, would just skip a fenced false match and land
    on the real heading anyway, silently -- which hides that the input was malformed
    rather than failing on it.
    """
    masked = _mask_fenced_code_blocks(full_text)
    boundary = _HISTORICAL_HEADING.search(masked)
    assert boundary, "no historical-record heading found outside a code fence"
    candidate = boundary.group(0).strip()
    assert _GENUINE_HISTORICAL_HEADING_SHAPE.match(candidate), (
        "the first historical-record marker outside a code fence does not look like "
        "this file's genuine heading (`## Previous release state -- wave N "
        f"(historical record)`): {candidate!r} -- a line that merely mentions the "
        "phrase must not silently become the live/historical boundary (F-5c's second "
        "hole, X-4)"
    )
    return boundary

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
            boundary = _historical_boundary(text)
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
    assert _true_migration_head() == "0011_document_section"


def test_true_surface_triple_matches_the_frozen_contract() -> None:
    """A PINNED literal, deliberately, and every reseal must move it.

    Deriving this from the contract would make it a tautology: `_true_surface_triple()`
    already parses that document, so comparing its answer to the same document would
    check nothing (`OPERATING_CONSTRAINTS.md` §12 — a query that shares an assumption
    with its subject is not a measurement). The pin is what makes this an independent
    second opinion about the parse.

    **The cost is that it goes stale exactly once per reseal, and it did.** `W45-BLOCKS`
    moved the surface to 16/19/53 and this literal stayed at 15/18/51, so the guard built
    to catch stale counts was itself the stale count -- red on the merged tip, and the
    integrator reported "contract suites green" from a scope that did not include this
    file. `D-102`.

    So: **this literal is a reseal document.** It moves with `openapi.json`, the generated
    client, the mirror and `web/FRONTEND_LOCK.json`, and a reseal that leaves it behind is
    an incomplete reseal.

    **`W46-SEAL` moved it to 17/20/61** (`R-40`'s `section` field and `ProjectSection`
    enum, `R-44`'s `getDashboardSummary` and its seven response schemas -- eight schemas
    in total). Also: this brief named this pin's location as
    `tests/contract/api_v1/test_doc_prose_facts.py:290`; it is no longer there, because
    the docstring above grew when `D-102` was written up. Reported in
    `docs/program/W46-SEAL.md` section 4 as a false premise found and corrected, not
    silently followed.
    """
    triple = _true_surface_triple()
    assert triple == SurfaceTriple(paths=17, operations=20, schemas=61)


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
    """`CURRENT_STATE.md`'s own historical record is read by nobody's regex here.

    **Structural, not dated.** An earlier version of this control pinned four literals
    tied to one wave -- a commit short sha, the exact heading text "wave 43 (historical
    record)", and the live section's own claim "closed as `alpha-w44`" -- and every one
    of those moves on a trigger nobody thinks of as one: writing a heading. It went red
    within a day of being written, caught by its own author closing wave 45, and again
    at `W46-SEAL` closing wave 46 -- the same shape `D-105` lists three of, found here as
    a fourth. This version derives its expectation from the marker
    :func:`_historical_boundary` itself finds in the file *as it stands*, so it proves
    the same mechanism -- a real boundary exists, everything after it is cut, everything
    before it survives -- without carrying a fact about which wave is currently live.
    """
    full_text = CURRENT_STATE.read_text(encoding="utf-8")
    boundary = _historical_boundary(full_text)
    (scanned_text,) = (
        text for file, text in _scanned_documents() if file == "docs/program/CURRENT_STATE.md"
    )
    # Exactly the live prefix -- not merely "shorter", which a truncation at the wrong
    # point could also satisfy.
    assert scanned_text == full_text[: boundary.start()]
    # A real boundary, not a no-op: content actually follows the marker. A heading at
    # the very end of the file would make "is a prefix" true vacuously, and this line is
    # what keeps that from passing silently.
    assert boundary.end() < len(full_text), (
        "the historical heading is the last thing in the file; truncation would remove "
        "nothing here even if _scanned_documents stopped truncating at all"
    )
    # The marker's own text -- whatever wave it currently names -- sits inside the part
    # cut away and nowhere in the part kept. Derived from the match rather than typed in
    # twice, where the two copies could disagree with each other or with the file.
    marker_text = boundary.group(0)
    assert marker_text not in scanned_text
    assert full_text.count(marker_text) >= 1
    # `F-5c` (`docs/program/reviews/W46-JUDGE-A.md` section 6): the half `ff686b1`'s
    # rewrite lost. `scanned_text == full_text[: boundary.start()]` above is satisfied by
    # **any** prefix, including the empty one -- a heading placed too early blinds the
    # scan and every assertion above still passes. Measured: one heading
    # ("### A note on how the historical record is kept") added directly under the live
    # section's own, before any of its content, truncates the live section down to
    # nothing and this control stayed green. The repair is non-vacuity: the live section
    # must still make a claim this guard's own extractors can read -- the same move
    # `test_the_bff_handler_still_makes_a_claim_this_guard_can_read` already makes for
    # the BFF route handler.
    #
    # **`X-4` (`docs/program/reviews/W46-JUDGE-X.md`, `F-5c`): non-vacuity alone is not
    # enough.** "At least one claim survives" holds for a boundary placed anywhere
    # before the *last* claim, not only one placed before *every* claim -- a mutation
    # that plants its false heading after the surface-triple paragraph but before a
    # stale migration-head sentence leaves the union non-empty (the surface triple
    # survives) while the stale head is silently cut away and never checked. `X-4` also
    # found the false heading did not even need to be a real heading: `_HISTORICAL_
    # HEADING` is a bare line match, so a shell comment inside a fenced code block
    # matches it too. `_historical_boundary` closes both: the candidate is searched for
    # outside every fenced code block, and whichever line is found first must have the
    # shape this file's genuine heading always has (`_GENUINE_HISTORICAL_HEADING_
    # SHAPE`) or the guard refuses to treat it as a boundary at all, rather than silently
    # using it or silently skipping past it. See `test_a_historical_heading_inside_a_
    # code_fence_is_not_a_boundary`, `test_a_too_early_heading_outside_a_fence_is_still_
    # caught` and `test_the_genuine_heading_is_still_found_as_the_boundary` below for all
    # three shown on synthetic prose.
    #
    # **Not narrowed to `TAGGED_TIP_CLAIM` alone**, though that is the literal the report
    # names. Measured against this tree rather than assumed: the live section, dated
    # 2026-09-28, says wave 46 is "merged, not yet gated" and deliberately makes no
    # `closed as \`alpha-wNN\`` claim -- correctly, since it has not closed yet. Pinning
    # this assertion to that one extractor would redden this control against a live
    # section that is telling the truth, in a file this task's `allowed_paths` does not
    # cover (`docs/program/CURRENT_STATE.md` is the integrator's -- see
    # `docs/program/W46-SPEND.md`). The union of all three extractors this file already
    # derives from the tree -- migration head, surface triple, tagged tip -- stays as a
    # second, independent line of defence: the shape check above refuses judge A's
    # heading (it does not say "Previous release state") and X's fenced one (masked
    # away before the search even runs), but neither check reads the heading's
    # *position* relative to the claims -- only its shape. Non-vacuity is what would
    # still catch the one case that has the right shape *and* the wrong position: the
    # genuine heading text itself, copied verbatim and placed early by hand.
    live_claims = (
        {m.group(0) for m in _migration_head_claims(scanned_text)}
        | {m.group(0) for m in _surface_triple_claims(scanned_text)}
        | {m.group(0) for m in _tagged_tip_claims(scanned_text)}
    )
    assert live_claims, (
        "the live section survives truncation but makes no claim this guard can read -- "
        "the non-vacuity half of the control (F-5c) is failing"
    )


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


#: A minimal but structurally faithful `CURRENT_STATE.md`: an H1 title, a live
#: `## Where the programme is` section carrying one claim, then the genuine historical
#: heading, then one historical claim. Every `_historical_boundary` mutation test below
#: builds on this rather than the real file, per this section's own header -- no real
#: document is mutated to prove the guard can fail.
_SYNTHETIC_LIVE_PREFIX = (
    "# Current state\n\n"
    "## Where the programme is, 2026-09-28 -- wave 46 merged, not yet gated\n\n"
    "The contract surface this tree has is 17 paths / 20 operations / 61 schemas.\n\n"
)
_SYNTHETIC_GENUINE_HEADING = "## Previous release state -- wave 45 (historical record)\n\n"
_SYNTHETIC_HISTORICAL_TAIL = "Migration head is unchanged at `0010_run_terminal_detail`.\n"
_SYNTHETIC_HONEST_DOCUMENT = (
    _SYNTHETIC_LIVE_PREFIX + _SYNTHETIC_GENUINE_HEADING + _SYNTHETIC_HISTORICAL_TAIL
)


def test_the_genuine_heading_is_still_found_as_the_boundary() -> None:
    """The control: an honest document, boundary exactly where the real heading starts."""
    boundary = _historical_boundary(_SYNTHETIC_HONEST_DOCUMENT)
    assert boundary.start() == len(_SYNTHETIC_LIVE_PREFIX)
    assert _SYNTHETIC_HONEST_DOCUMENT[: boundary.start()] == _SYNTHETIC_LIVE_PREFIX


def test_a_historical_heading_inside_a_code_fence_is_not_a_boundary() -> None:
    """`X-4`'s own mutation, on synthetic prose: a shell comment in a fenced code block,
    reading `# the historical record below is kept verbatim; do not edit it`, followed
    by a stale migration-head sentence, both placed between the live claim and the
    genuine heading.

    Before this repair, `_HISTORICAL_HEADING.search()` matched the commented line
    inside the fence -- a bare `^#+.*historical record.*$` has no notion of Markdown
    structure -- and truncated there, hiding the stale sentence from every test that
    would otherwise have caught it (`test_the_scanned_docs_state_the_migration_head_
    this_tree_has` on the real file). Masking fenced code blocks before searching
    restores the genuine heading as the boundary, and the stale sentence is back inside
    the scanned prefix where a head-checking test can see it.
    """
    fenced_false_heading = (
        "```bash\n"
        "# the historical record below is kept verbatim; do not edit it\n"
        "```\n\n"
    )
    stale_head_sentence = "The migration head is `0010_run_terminal_detail`.\n\n"
    mutated = (
        _SYNTHETIC_LIVE_PREFIX
        + fenced_false_heading
        + stale_head_sentence
        + _SYNTHETIC_GENUINE_HEADING
        + _SYNTHETIC_HISTORICAL_TAIL
    )

    boundary = _historical_boundary(mutated)

    # The boundary is the genuine heading, not the fenced comment: the fenced comment
    # sits well before it and is not where the scan is cut.
    expected_start = len(_SYNTHETIC_LIVE_PREFIX + fenced_false_heading + stale_head_sentence)
    assert boundary.start() == expected_start
    assert boundary.group(0).strip() == _SYNTHETIC_GENUINE_HEADING.strip()
    # The point of the fix: the stale sentence the fence used to hide is now inside the
    # scanned prefix, where a real head-checking test would see it.
    assert stale_head_sentence.strip() in mutated[: boundary.start()]


def test_a_too_early_heading_outside_a_fence_is_still_caught() -> None:
    """Judge A's mutation (`F-5`, `docs/program/reviews/W46-JUDGE-A.md` section 6): a
    real, non-fenced `### A note on how the historical record is kept` heading, placed
    directly under the live heading before any of its content.

    Not fenced, so masking alone would not stop `_HISTORICAL_HEADING` from matching it
    -- and it is the first match in the file, so it is still the boundary
    `_HISTORICAL_HEADING` finds first. What refuses it is the shape check: this line
    does not read "Previous release state -- wave N (historical record)", so
    `_historical_boundary` raises rather than silently truncating the live section down
    to nothing.
    """
    mutated = (
        "# Current state\n\n"
        "## Where the programme is, 2026-09-28 -- wave 46 merged, not yet gated\n\n"
        "### A note on how the historical record is kept\n\n"
        "The contract surface this tree has is 17 paths / 20 operations / 61 schemas.\n\n"
        + _SYNTHETIC_GENUINE_HEADING
        + _SYNTHETIC_HISTORICAL_TAIL
    )
    with pytest.raises(AssertionError, match="does not look like this file's genuine heading"):
        _historical_boundary(mutated)


def test_a_too_early_heading_after_the_first_claim_is_still_caught() -> None:
    """A mutation of my own, not X's or judge A's: `F-5c`'s second hole (`X-4`)
    reproduced *without* a code fence at all.

    X's own reproduction combines two defects in one mutation (a false match that is
    both fenced *and* placed after the first live claim), so fixing fence-blindness
    alone would already make that specific mutation pass again -- without proving the
    positional hole (a boundary placed after the first claim, hiding every claim behind
    it) is closed on its own. This mutation isolates it: a real, unfenced, level-two
    heading -- `## Note: keeping the historical record separate` -- placed after the
    live surface-triple claim but before a stale migration-head sentence and the
    genuine heading. It has the right *level* (two `#`) but not this file's genuine
    *shape* ("Previous release state -- wave N"), so the shape check refuses it exactly
    as it refuses judge A's, and the stale sentence stays where a head-checking test can
    reach it rather than being silently cut away.
    """
    false_heading = "## Note: keeping the historical record separate\n\n"
    stale_head_sentence = "The migration head is `0010_run_terminal_detail`.\n\n"
    mutated = (
        _SYNTHETIC_LIVE_PREFIX
        + false_heading
        + stale_head_sentence
        + _SYNTHETIC_GENUINE_HEADING
        + _SYNTHETIC_HISTORICAL_TAIL
    )
    with pytest.raises(AssertionError, match="does not look like this file's genuine heading"):
        _historical_boundary(mutated)


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
