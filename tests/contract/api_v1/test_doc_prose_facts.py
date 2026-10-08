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

1. **Scope is a fixed, named set of live documents.** The sibling module discovers tracked
   runtime/deployment text through Git, while this module names the maintained state/roadmap/
   runbook documents whose present-tense facts it judges. Wave reports
   (`docs/program/W30-CERT3.md`, `W37-CERT4.md`, ...) are simply never in this set --
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

**Outstanding live claims are never normalised.** A previous task registered the stale
`docs/manual-tests/PC-01_prototype.md` migration head here because that runbook was outside
its write scope. `W47-CLOSE` owns the runbook, corrected the claim to the real head and
removed the exception. :data:`KNOWN_OUTSTANDING_CLAIMS` therefore remains an explicit empty
set: a future live mismatch fails the guard instead of inheriting a permanent allow-list.

"""

from __future__ import annotations

import ast
import json
import pathlib
import re
import subprocess
from dataclasses import dataclass, replace
from typing import Iterator

import pytest

from tests.support.expected_facts import FACTS, FACTS_PATH, ExpectedFacts, load_expected_facts

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

API_CONTRACT = REPO_ROOT / "contracts" / "api" / "v1" / "openapi.json"
ERROR_CATALOG = REPO_ROOT / "contracts" / "domain" / "v1" / "error-codes.json"
MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations" / "versions"

CURRENT_STATE = REPO_ROOT / "docs" / "program" / "CURRENT_STATE.md"
ALPHA_ROADMAP = REPO_ROOT / "docs" / "program" / "ALPHA_ROADMAP.md"
MANUAL_TESTS_DIR = REPO_ROOT / "docs" / "manual-tests"
PIN_REGISTRY = REPO_ROOT / "docs" / "program" / "CONTRACT_PIN_REGISTRY.md"

_PIN_REGISTRY_BLOCK = re.compile(r"```json\n(?P<body>\{.*?\})\n```", re.DOTALL)
_PIN_NAMES = frozenset({
    "FROZEN_OPERATION_COUNT", "FROZEN_SCHEMA_COUNT", "FROZEN_OPERATIONS",
    "FROZEN_SCHEMA_NAMES", "PATH_COUNT", "OPERATION_COUNT", "SCHEMA_COUNT",
})
_PIN_SUBJECT = re.compile(
    r"(?:router\.routes|router\.operation_ids|app\.router\.routes|"
    r"application\.router\.routes|client\.app\.router\.routes|"
    r"declared_operations\(|ERROR_CODES|raw\['codes'\]|_true_migration_head\()"
)

# TypeScript/TSX has independent contract tests too. Only literal symbolic pins and the exact
# generated-error-catalog length assertion are candidates: a derived `SCHEMA_COUNT =
# Object.keys(...).length`, HTTP status, fixture size or local enum count is not independent.
_TS_PIN_ASSIGNMENT = re.compile(
    r"^\s*const\s+(?:FROZEN_OPERATION_COUNT|FROZEN_SCHEMA_COUNT|FROZEN_OPERATIONS|"
    r"FROZEN_SCHEMA_NAMES|SEAM_OPERATIONS|SCHEMA_NAMES|PATH_COUNT|OPERATION_COUNT|"
    r"SCHEMA_COUNT)\s*(?::[^=]+)?=\s*(?:\d+;?|\[)",
    re.MULTILINE,
)
_TS_ERROR_COUNT_ASSERTION = re.compile(
    r"^\s*expect\((?:ERROR_CODE_VALUES|OPERATIONS|SCHEMA_NAMES|SEAM_OPERATIONS)\)"
    r"\.toHaveLength\(\d+\);?",
    re.MULTILINE,
)


def _mask_typescript_comments_and_strings(source: str) -> str:
    """Preserve code/newlines while making comments and string/template bodies invisible.

    This is a deliberately small lexical pass, not a TypeScript parser. The candidate grammar
    above needs only identifiers, punctuation and numeric literals; masking every quoted body is
    safer than letting a comment or test fixture string manufacture executable pin syntax.
    """
    output = list(source)
    index = 0
    state = "code"
    quote = ""
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if state == "code":
            if char == "/" and next_char == "/":
                output[index] = output[index + 1] = " "
                index += 2
                state = "line_comment"
                continue
            if char == "/" and next_char == "*":
                output[index] = output[index + 1] = " "
                index += 2
                state = "block_comment"
                continue
            if char in {"'", '"', "`"}:
                quote = char
                output[index] = " "
                index += 1
                state = "string"
                continue
        elif state == "line_comment":
            if char == "\n":
                state = "code"
            else:
                output[index] = " "
            index += 1
            continue
        elif state == "block_comment":
            if char == "*" and next_char == "/":
                output[index] = output[index + 1] = " "
                index += 2
                state = "code"
                continue
            if char != "\n":
                output[index] = " "
            index += 1
            continue
        else:
            if char == "\\":
                output[index] = " "
                if index + 1 < len(source):
                    if source[index + 1] != "\n":
                        output[index + 1] = " "
                    index += 2
                    continue
            if char == quote:
                output[index] = " "
                index += 1
                state = "code"
                continue
            if char != "\n":
                output[index] = " "
            index += 1
            continue
        index += 1
    return "".join(output)


def _typescript_pin_candidates(relative: str, source: str) -> list[tuple[str, str]]:
    masked = _mask_typescript_comments_and_strings(source)
    matches = [match.group(0).strip() for match in _TS_PIN_ASSIGNMENT.finditer(masked)]
    matches.extend(
        match.group(0).strip() for match in _TS_ERROR_COUNT_ASSERTION.finditer(masked)
    )
    return [(relative, match) for match in matches]


def _pin_registry() -> list[dict[str, str]]:
    match = _PIN_REGISTRY_BLOCK.search(PIN_REGISTRY.read_text(encoding="utf-8"))
    assert match, f"{PIN_REGISTRY}: one fenced JSON registry is required"
    document = json.loads(match.group("body"))
    assert document["registry_version"] == 1
    return document["pins"]


def _python_pin_candidates(relative: str, text: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    tree = ast.parse(text, filename=relative)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id in _PIN_NAMES for target in targets):
                value = node.value
                literal_collection = (
                    isinstance(value, ast.Call)
                    and isinstance(value.func, ast.Name)
                    and value.func.id in {"frozenset", "tuple", "set"}
                    and bool(value.args)
                    and isinstance(value.args[0], (ast.Tuple, ast.List, ast.Set))
                )
                if isinstance(value, (ast.Constant, ast.Tuple, ast.List, ast.Set)) or literal_collection:
                    snippet = ast.get_source_segment(text, node) or ""
                    found.append((relative, snippet.strip()))
        if not isinstance(node, ast.Assert):
            continue
        for comparison in (child for child in ast.walk(node.test) if isinstance(child, ast.Compare)):
            snippet = ast.get_source_segment(text, comparison) or ""
            independent = any(
                isinstance(child, ast.Constant)
                and (type(child.value) is int or (
                    isinstance(child.value, str) and "_true_migration_head(" in snippet
                ))
                for child in ast.walk(comparison)
            )
            subject = _PIN_SUBJECT.search(snippet) or (
                relative == "tests/integration/api/test_operation_surface.py"
                and "len(paths)" in snippet
            ) or (
                "_true_surface_triple(" in snippet and "SurfaceTriple(" in snippet
            )
            if independent and subject:
                found.append((relative, snippet.strip()))
    return found


def _discovered_independent_pins() -> list[tuple[str, str]]:
    """Find numeric expectations for contract-sized subjects outside the facts file.

    The subject grammar is fixed, but the number is not: an arbitrary new count must
    still fail. Python syntax parsing ignores comments and strings; TypeScript uses the
    masking pass above. Fixture data and the unrelated report-length assertion are out
    of scope by semantic subject, not by a shared numeric value.
    """
    found: list[tuple[str, str]] = []
    for path in sorted((REPO_ROOT / "tests").rglob("*.py")):
        relative = str(path.relative_to(REPO_ROOT))
        if relative.startswith("tests/contract/tools/fixtures/"):
            continue
        found.extend(_python_pin_candidates(relative, path.read_text(encoding="utf-8")))

    for path in sorted((REPO_ROOT / "web" / "tests").rglob("*")):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        relative = str(path.relative_to(REPO_ROOT))
        found.extend(
            _typescript_pin_candidates(relative, path.read_text(encoding="utf-8"))
        )

    return found


def _pin_needle_errors(
    pins: list[dict[str, str]], *, overrides: dict[str, str] | None = None
) -> list[str]:
    overrides = overrides or {}
    errors: list[str] = []
    for pin in pins:
        target = REPO_ROOT / pin["path"]
        text = overrides.get(pin["path"], target.read_text(encoding="utf-8"))
        occurrences = text.count(pin["needle"])
        if occurrences != 1:
            errors.append(
                f"{pin['pin_id']}: needle must identify exactly one live pin in "
                f"{pin['path']}, found {occurrences}"
            )
    return errors

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
    boundaries = list(_HISTORICAL_HEADING.finditer(masked))
    assert boundaries, "no historical-record heading found outside a code fence"
    boundary = boundaries[0]
    waves: list[int] = []
    for candidate_match in boundaries:
        candidate = candidate_match.group(0).strip()
        assert _GENUINE_HISTORICAL_HEADING_SHAPE.match(candidate), (
            "a historical-record marker outside a code fence does not look like "
            "this file's genuine heading (`## Previous release state -- wave N "
            f"(historical record)`): {candidate!r} -- a line that merely mentions the "
            "phrase must not silently become the live/historical boundary (F-5c's second "
            "hole, X-4)"
        )
        wave = re.search(r"\bwave\s+(\d+)\b", candidate, re.IGNORECASE)
        assert wave
        waves.append(int(wave.group(1)))
    assert len(waves) == len(set(waves)) and all(
        newer > older for newer, older in zip(waves, waves[1:])
    ), f"historical headings must be unique and newest-first; D-115 mutation: {waves}"
    return boundary


def _assert_boundary_matches_tag(full_text: str, tagged_tip: str) -> "re.Match[str]":
    """The first historical section is the latest tagged release, not the active wave."""
    boundary = _historical_boundary(full_text)
    actual = re.search(r"\bwave\s+(\d+)\b", boundary.group(0), re.IGNORECASE)
    expected = re.fullmatch(r"alpha-w(\d+)(?:\.\d+)?", tagged_tip)
    assert actual and expected
    assert int(actual.group(1)) == int(expected.group(1)), (
        "the first history heading does not name the tagged tip; a correctly shaped heading "
        "for the active wave was placed before live claims (D-115): "
        f"heading wave {actual.group(1)}, tagged tip {tagged_tip}"
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

#: `(file, exact matched phrase)` -- currently wrong live claims temporarily owned by a
#: different task. This set must normally be empty; a non-empty entry is a cited finding,
#: never a way to normalise stale prose.
KNOWN_OUTSTANDING_CLAIMS: frozenset[tuple[str, str]] = frozenset()


def _is_registered(file: str, matched_text: str, registry: frozenset[tuple[str, str]]) -> bool:
    return any(
        file == entry_file and matched_text.startswith(entry_text)
        for entry_file, entry_text in registry
    )


# ---------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------


def test_true_migration_head_is_a_real_single_head() -> None:
    assert _true_migration_head() == FACTS.migration_head


def test_true_surface_triple_matches_the_frozen_contract() -> None:
    """The hand-maintained facts file is the second opinion about the parsed document."""
    triple = _true_surface_triple()
    assert triple == SurfaceTriple(
        paths=FACTS.path_count,
        operations=FACTS.operation_count,
        schemas=FACTS.schema_count,
    )


def _current_fact_differences(facts: ExpectedFacts) -> set[str]:
    document = json.loads(API_CONTRACT.read_text(encoding="utf-8"))
    catalog = json.loads(ERROR_CATALOG.read_text(encoding="utf-8"))
    methods = {"get", "post", "put", "patch", "delete", "head", "options"}
    operations = {
        (method.upper(), path, operation["operationId"])
        for path, item in document["paths"].items()
        for method, operation in item.items()
        if method in methods
    }
    differences: set[str] = set()
    if len(document["paths"]) != facts.path_count or operations != set(facts.operations):
        differences.add("surface")
    if set(document["components"]["schemas"]) != facts.schema_names:
        differences.add("surface")
    if len(catalog["codes"]) != facts.api_error_codes:
        differences.add("error_catalog")
    if _true_migration_head() != facts.migration_head:
        differences.add("migration_head")
    if document["info"]["version"] != facts.contract_version or catalog["contract_version"] != facts.contract_version:
        differences.add("contract_version")
    return differences


def test_expected_facts_are_independent_and_current() -> None:
    assert not _current_fact_differences(FACTS)


@pytest.mark.parametrize("family", ["surface", "error_catalog", "migration_head", "contract_version"])
def test_current_fact_mutation_reddens_its_family(family: str) -> None:
    candidates = {
        "surface": replace(FACTS, path_count=FACTS.path_count + 1),
        "error_catalog": replace(FACTS, api_error_codes=FACTS.api_error_codes + 1),
        "migration_head": replace(FACTS, migration_head="9999_mutated"),
        "contract_version": replace(FACTS, contract_version="9.9.9-mutated"),
    }
    assert family in _current_fact_differences(candidates[family])


def test_true_tagged_tip_is_read_from_git_and_is_plausible() -> None:
    tip = _true_tagged_tip()
    assert re.fullmatch(r"alpha-w\d+(?:\.\d+)?", tip), tip


def test_contract_pin_registry_points_to_live_fact_consumers() -> None:
    """Every registered consumer remains present, with no second literal opinion."""
    pins = _pin_registry()
    assert pins
    assert {pin["family"] for pin in pins} == {
        "surface",
        "error_catalog",
        "migration_head",
        "history_boundary",
    }
    ids = [pin["pin_id"] for pin in pins]
    assert len(ids) == len(set(ids)), "pin_id values must be unique"

    for pin in pins:
        assert set(pin) == {"pin_id", "family", "path", "needle", "event"}, pin
        target = REPO_ROOT / pin["path"]
        assert target.is_file(), f"{pin['pin_id']}: missing {pin['path']}"
        if pin["family"] != "history_boundary":
            text = target.read_text(encoding="utf-8")
            assert "FACTS" in text or "expectedFacts" in text, pin["pin_id"]
    assert not _pin_needle_errors(pins)

    discovered = _discovered_independent_pins()
    assert not discovered, f"independent literals outside expected_facts.json: {discovered}"


def test_typescript_pin_discovery_reads_code_and_ignores_comments_and_strings() -> None:
    """`JA-03`: the same symbolic pin is evidence only when it is executable syntax."""
    relative = "web/tests/contract/judge-independent-pin.contract.test.ts"
    real = "const FROZEN_OPERATION_COUNT = 12;\n"
    decoys = (
        "// const FROZEN_OPERATION_COUNT = 12;\n"
        "/* const FROZEN_OPERATION_COUNT = 12; */\n"
        "const text = 'const FROZEN_OPERATION_COUNT = 12;';\n"
        "const template = `const FROZEN_OPERATION_COUNT = 12;`;\n"
    )
    assert _typescript_pin_candidates(relative, real) == [
        (relative, "const FROZEN_OPERATION_COUNT = 12;")
    ]
    assert _typescript_pin_candidates(relative, decoys) == []


def test_a_new_frontend_error_count_literal_is_discovered() -> None:
    relative = "web/tests/contract/new-count.contract.test.ts"
    needle = "expect(ERROR_CODE_VALUES).toHaveLength(999);"
    assert _typescript_pin_candidates(relative, needle) == [(relative, needle)]


def test_an_arbitrary_new_operation_literal_is_discovered_without_its_number_in_the_rule() -> None:
    relative = "tests/integration/other/test_future_surface.py"
    source = (
        "def test_new_pin(router):\n"
        "    assert len(router.routes) == 999\n"
        "    assert len(report) == 22\n"
        "    # assert len(router.routes) == 998\n"
    )
    assert _python_pin_candidates(relative, source) == [
        (relative, "len(router.routes) == 999")
    ]


def test_expected_facts_loader_refuses_a_duplicate_operation(tmp_path: pathlib.Path) -> None:
    raw = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    raw["surface"]["operations"].append(raw["surface"]["operations"][0])
    changed = tmp_path / "expected_facts.json"
    changed.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate expected operation"):
        load_expected_facts(changed)


@pytest.mark.parametrize(
    "pin_id",
    ["error-frontend-contract-enum-count", "error-frontend-failure-enum-count"],
)
def test_each_registered_frontend_pin_is_red_when_its_needle_moves(pin_id: str) -> None:
    pins = _pin_registry()
    pin = next(candidate for candidate in pins if candidate["pin_id"] == pin_id)
    target = REPO_ROOT / pin["path"]
    original = target.read_text(encoding="utf-8")
    mutated = original.replace(pin["needle"], f"MUTATED_{pin_id}", 1)
    assert mutated != original
    errors = _pin_needle_errors(pins, overrides={pin["path"]: mutated})
    assert any(error.startswith(f"{pin_id}:") for error in errors), errors


@pytest.mark.parametrize(
    "family",
    ["surface", "error_catalog", "migration_head", "history_boundary"],
)
def test_one_changed_pin_per_registry_family_is_red(family: str) -> None:
    """A registry entry cannot stay green after its independently maintained pin moves."""
    pins = _pin_registry()
    pin = next(candidate for candidate in pins if candidate["family"] == family)
    target = REPO_ROOT / pin["path"]
    original = target.read_text(encoding="utf-8")
    mutated = original.replace(pin["needle"], f"MUTATED_{pin['pin_id']}", 1)
    assert mutated != original
    errors = _pin_needle_errors(pins, overrides={pin["path"]: mutated})
    assert any(error.startswith(f"{pin['pin_id']}:") for error in errors), errors


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
    boundary = _assert_boundary_matches_tag(full_text, _true_tagged_tip())
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
    migration_claims = {m.group(0) for m in _migration_head_claims(scanned_text)}
    surface_claims = {m.group(0) for m in _surface_triple_claims(scanned_text)}
    assert migration_claims and surface_claims, (
        "the live section must retain both its migration-head and surface claims before the "
        "history boundary; one surviving family cannot hide another (D-115): "
        f"migration={migration_claims}, surface={surface_claims}"
    )
    assert "infra/deploy/verify-deployed.sh" in scanned_text, (
        "the command that replaces a perishable deployed-SHA/date assertion was truncated"
    )


def test_live_state_names_a_probe_not_a_deployed_sha_snapshot() -> None:
    """`D-104`: live prose points to verification and carries no present-tense SHA snapshot."""
    (live,) = (
        text for file, text in _scanned_documents() if file == "docs/program/CURRENT_STATE.md"
    )
    assert "infra/deploy/verify-deployed.sh" in live
    perishable = re.compile(
        r"\b(?:deployed|redeployed)\b[^\n]{0,100}?\b[0-9a-f]{7,40}\b",
        re.IGNORECASE,
    )
    assert not perishable.search(live), (
        "CURRENT_STATE live prose asserts a deployed SHA; name verify-deployed.sh instead"
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


def test_a_correctly_shaped_early_heading_cannot_hide_later_live_claims() -> None:
    """`D-115`: shape alone is insufficient when the genuine heading still exists later."""
    stale_head_sentence = "The migration head is `0010_run_terminal_detail`.\n\n"
    early = "## Previous release state -- wave 46 (historical record)\n\n"
    mutated = (
        _SYNTHETIC_LIVE_PREFIX
        + early
        + stale_head_sentence
        + _SYNTHETIC_GENUINE_HEADING
        + _SYNTHETIC_HISTORICAL_TAIL
    )
    with pytest.raises(AssertionError, match="does not name the tagged tip"):
        _assert_boundary_matches_tag(mutated, "alpha-w45")


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


def test_judge_ys_own_heading_after_the_first_claim_is_still_caught() -> None:
    """`W46-JUDGE-Y`'s cross-examination of `X-4` (`docs/program/reviews/W46-JUDGE-Y.md`,
    section "X-4 -- upheld, and broadened: no code fence is needed"): Y tried an
    ordinary Markdown heading where X used a fenced shell comment, and measured the
    code fence to be incidental -- *"any line starting with `#` that mentions the
    historical record, placed after the first claim, blinds everything below it."* Y's
    own table, reproduced literally here (the previous test already covers the same
    shape with wording of my own; this one is Y's exact heading, quoted, so nothing
    about the repair depends on a paraphrase happening to be caught too):

    - *"The migration head is `0010_run_terminal_detail`."* alone -- red (the control,
      covered by `test_a_stale_migration_head_claim_is_caught`'s premise elsewhere).
    - `### What the historical record below keeps`, then the same stale sentence --
      **`21 passed`** before this repair (Y's own measurement).
    - the stale sentence, then that heading -- a claim above the boundary is still
      read, so this direction already failed correctly.
    """
    false_heading = "### What the historical record below keeps\n\n"
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


def test_no_known_outstanding_live_claim_is_normalised() -> None:
    """A repaired finding leaves no permanent allow-list behind."""
    assert KNOWN_OUTSTANDING_CLAIMS == frozenset()
