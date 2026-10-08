"""`D-23`: the prose that states how big the surface is, checked against the surface.

The conformance engine drops ``description``, ``summary`` and ``title`` as annotation
(`N4`), so it verifies the whole *surface* of ``contracts/api/v1/openapi.json`` and none
of the prose either document carries. `W18-SEAL` swept `src/` after the `R-5` reseal and
found **thirty-five statements across twelve files** still saying the surface had twelve
operations and 43 schemas, after it had become fifteen and 46 -- six in ``api/app.py``
alone, and one of them, ``_DESCRIPTION``, is **served to every caller** on
``/openapi.json``. It corrected all thirty-five. Nothing stopped the thirty-sixth.

This is the guard that stops it, and the rule it enforces is:

    A number that claims the size of this surface must equal the size of this surface.

**Every count here is read out of the documents, never written down.** A literal would
have to be edited at the next reseal, which is exactly the failure mode `D-23` names --
`OPERATING_CONSTRAINTS.md` section 12. The operation count is the (path, method) pairs of
the frozen document, the schema count is ``len(components.schemas)``, the path count is
``len(paths)``, and the code count is ``len(codes)`` of the domain error catalog, which is
what ``info.description`` means by *"the twenty-two-code catalog"*.

**What is deliberately not flagged.** Not every ``<n> operations`` in this tree claims the
size of the surface: ``"the two schemas that only it referenced"`` and ``"the four
operations that declare none"`` are true statements about subsets, and a guard that
reddened on them would be teaching sessions to write worse prose. :data:`LOCAL_COUNTS`
registers those, and it is a set of **phrases, not of counts**: resealing the surface
never touches it. Adding to it is how a session says out loud *"this number is not the
surface"*, which is the declaration `D-22` exists to demand.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
from dataclasses import dataclass
from functools import cache
from typing import Iterator

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
#: Git's tracked text is live by default. These are role exclusions, not the directory allow-list
#: `JA-02` defeated: test/fixture material deliberately carries stale probes, contracts and their
#: generated mirror are checked structurally, documentation is governed by the live/history
#: scanner beside this module, and migration source is immutable history. A new top-level runtime,
#: operator or generator directory therefore enters without changing this file.
NON_LIVE_PATH_PARTS = frozenset({"artifacts", "contracts", "docs", "fixtures", "tests"})
NON_LIVE_PREFIXES = ("db/migrations/", "web/openapi/")
NON_LIVE_FILES = frozenset({"web/FRONTEND_LOCK.json"})
#: P02_SEAMS is a maintained implementation input, not a wave/history report, so it is the one
#: documentation role explicitly admitted after the role exclusions above (`D-100`).
LIVE_SURFACE_DOCUMENTS = frozenset({"docs/program/P02_SEAMS.md"})
API_CONTRACT = REPO_ROOT / "contracts" / "api" / "v1" / "openapi.json"
ERROR_CATALOG = REPO_ROOT / "contracts" / "domain" / "v1" / "error-codes.json"

#: The HTTP methods an OpenAPI path item may carry. Anything else under a path item --
#: ``parameters``, ``summary``, a ``$ref`` -- is not an operation.
_METHODS = frozenset(
    {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
)

_UNITS = (
    "zero one two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen"
).split()
_TENS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


def _number_words() -> dict[str, int]:
    """Every English spelling of 0..99, built rather than listed."""
    words = {word: value for value, word in enumerate(_UNITS)}
    for tens_word, tens_value in _TENS.items():
        words[tens_word] = tens_value
        for unit_value, unit_word in enumerate(_UNITS[1:10], start=1):
            words[f"{tens_word}-{unit_word}"] = tens_value + unit_value
            words[f"{tens_word} {unit_word}"] = tens_value + unit_value
    return words


NUMBER_WORDS = _number_words()

_NUMBER = r"(?:\d{1,2}|" + "|".join(
    sorted((re.escape(w) for w in NUMBER_WORDS), key=len, reverse=True)
) + r")"
#: A quantified noun phrase, without an allow-list of nouns. The old pattern knew only
#: operation/schema/path/code/handler; declarations, models, copies and places walked straight
#: through it (`D-98`). The *subject* is established independently by `_SURFACE_SUBJECT`, then
#: any count-bearing phrase in that subject is inspected. Up to three words are retained so a
#: local exception is an exact phrase, not an exemption for a number everywhere.
_QUANTIFIED_PHRASE = re.compile(
    rf"(?<![\w-])(?P<number>{_NUMBER})[ -]"
    r"(?:(?:public)[ -])?"
    r"(?P<label>[A-Za-z][A-Za-z-]*)\b",
    re.IGNORECASE,
)

#: These words identify prose whose subject is the API contract. They do not classify the noun
#: after a number, so `the API surface has nineteen widgets` is still a claim and still fails.
#: The anchors describe repository concepts, not a growing synonym list for count labels.
_SURFACE_SUBJECT = re.compile(
    r"\b(?:api[ \t]+(?:surface|has)|openapi[ \t]+surface|"
    r"served[ \t]+document|frozen[ \t]+document|"
    r"contract[ \t]+declares|document[ \t]+declares|surface[ \t]+(?:is|has|contains))\b",
    re.IGNORECASE,
)

#: A totality statement is a whole-surface assertion even when it invents both a new subject and
#: a new noun. `JA-01` used "The complete HTTP interface exposes twelve endpoints" and showed
#: that adding aliases to `_SURFACE_SUBJECT` merely moves the next false green. The totality word
#: and an assertion verb must both lead into the number; bare phrases such as "all 18 PASS" or
#: "the full run took ten minutes" are not surface-size grammar.
_TOTALITY_ASSERTION_PREFIX = re.compile(
    r"\b(?:all|complete|entire|full|total|whole)\b"
    r"(?:(?![.!?;\n]).){0,96}\b(?:comprises|contains|declares|exposes|has|includes|numbers|totals)\s*$",
    re.IGNORECASE,
)

#: Only the four canonical contract vocabulary words get a dimension-specific expectation.
#: They are derived from `_surface_counts()`'s keys. Every other noun is checked against the
#: complete set of current surface values, which is enough to reject an unseen synonym carrying
#: an old/arbitrary surface count without pretending to understand natural language.
_SINGULAR = {"operations": "operation", "schemas": "schema", "paths": "path", "codes": "code"}
_NON_NOUN_LABELS = frozenset(
    {
        "after",
        "against",
        "and",
        "as",
        "at",
        "before",
        "below",
        "cannot",
        "for",
        "from",
        "in",
        "into",
        "is",
        "of",
        "on",
        "out",
        "plus",
        "that",
        "the",
        "this",
        "to",
        "was",
        "were",
        "with",
        "would",
    }
)

#: Phrases that carry a canonical surface word and deliberately do **not** claim the size
#: of the whole surface. Each is a statement about a subset or about a local
#: mechanism, and each is true. This register is about PROSE: a reseal that changes the
#: surface counts requires no edit here, which is what keeps it from becoming the literal
#: `D-23` is a row about.
LOCAL_COUNTS: frozenset[str] = frozenset(
    {
        # app.py: FastAPI's injected 422 and the two component schemas only it referenced.
        "two schemas",
        # README.md and app.py: the operations that declare no 422 of their own.
        "four operations",
        # declarations.py, handlers.py, models.py: a single addressed thing.
        "one operation",
        "one schema",
        "one path",
        # routers/__init__.py: the duplicate-operationId refusal compares a pair.
        "two routes",
        # models.py: one schema per model, in serialization mode.
        "one schema per model",
        # README.md: the two codes one envelope test pins, not the size of the catalog.
        "two codes",
        # openapi.json info: "gains one code" -- the R-8 addition, not the catalog size.
        "one code",
        # app.py: current subsets of the operation surface, explained in the same paragraph.
        "fourteen of the",
        "six operation joined",
        # deployment/source comments whose subject shares an API word but whose count is local.
        "four middlewares",
        "four documentation routes",
    }
)

#: True local counts exposed by widening from three hand-listed source prefixes to every tracked
#: live-text role. Path qualification prevents, for example, "three operations" from becoming a
#: repository-wide exemption for a future stale surface. These phrases are deliberately facts
#: about a local port/model/branch, not the frozen HTTP surface or error catalog.
PATH_LOCAL_COUNTS: frozenset[tuple[str, str]] = frozenset(
    {
        ("src/auditmanager/access/__init__.py", "three operations"),
        ("src/auditmanager/access/passwords.py", "two paths"),
        ("src/auditmanager/access/ports.py", "three operations"),
        ("src/auditmanager/access/ports.py", "two operations"),
        ("src/auditmanager/access/repository.py", "three paths"),
        ("src/auditmanager/access/repository.py", "two paths"),
        ("src/auditmanager/analysis/engine/result.py", "two schema"),
        ("src/auditmanager/documents/models.py", "fourteen codes"),
        ("src/auditmanager/documents/repository.py", "fourteen codes"),
        ("tools/validation/ledger_report.py", "twenty code"),
        ("tools/validation/ledger_report.py", "1 code"),
    }
)

#: Exact historical records inside an otherwise live specification. Path qualification matters:
#: the same phrase in runtime/deployment prose remains a failure. The record is retained rather
#: than rewritten, and the test below proves the registration cannot outlive its sentence.
KNOWN_HISTORICAL_SURFACE_CLAIMS: frozenset[tuple[str, str]] = frozenset(
    {
        ("docs/program/P02_SEAMS.md", "Fifteen operations"),
        # An explicitly past-tense account of the pre-W15 deployment, retained in the live
        # environment example so the BFF setting explains why it exists.
        ("web/.env.example", "twelve operations"),
    }
)


@dataclass(frozen=True)
class TrackedText:
    path: pathlib.Path
    relative: str
    text: str | None
    classification: str


def _tracked_inventory() -> list[TrackedText]:
    """Classify every tracked path as UTF-8 text, binary or unreadable.

    Git, not a suffix list, owns file discovery. A new `.conf`, Dockerfile or extensionless
    script therefore enters the inventory automatically. Binary/unparseable paths are explicit
    results rather than silent skips; none may appear in the live-surface families.
    """
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    )
    entries: list[TrackedText] = []
    for raw_name in completed.stdout.split(b"\0"):
        if not raw_name:
            continue
        relative = raw_name.decode("utf-8")
        path = REPO_ROOT / relative
        try:
            payload = path.read_bytes()
        except OSError:
            entries.append(TrackedText(path, relative, None, "unreadable"))
            continue
        if b"\0" in payload:
            entries.append(TrackedText(path, relative, None, "binary"))
            continue
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            entries.append(TrackedText(path, relative, None, "non-utf8"))
            continue
        entries.append(TrackedText(path, relative, text, "utf8-text"))
    return entries


def _surface_counts() -> dict[str, int]:
    """What the two frozen documents actually declare. Nothing here is written down."""
    document = json.loads(API_CONTRACT.read_text(encoding="utf-8"))
    catalog = json.loads(ERROR_CATALOG.read_text(encoding="utf-8"))
    operations = sum(
        1
        for item in document["paths"].values()
        for method in item
        if method.lower() in _METHODS
    )
    return {
        "operations": operations,
        "schemas": len(document["components"]["schemas"]),
        "paths": len(document["paths"]),
        "codes": len(catalog["codes"]),
    }


_DOCUMENTED_SURFACE_TRIPLE = re.compile(
    r"(?P<paths>\d{1,2})\s+paths?\s*/\s*"
    r"(?P<operations>\d{1,2})\s+operations?\s*/\s*"
    r"(?P<schemas>\d{1,3})\s+schemas?",
    re.IGNORECASE,
)


@cache
def _documented_surface_values() -> frozenset[int]:
    """Surface values retained in the repository, independent of clone depth.

    Historical reports remain tracked even in a shallow clone. Their complete numeric triples
    are a durable source for deciding whether an unfamiliar noun carries an old surface value;
    unlike ``git log`` this source cannot silently shrink with the clone's object history.
    """
    values = set(_surface_counts().values())
    for path in sorted((REPO_ROOT / "docs").rglob("*.md")):
        for match in _DOCUMENTED_SURFACE_TRIPLE.finditer(_unwrap(path.read_text(encoding="utf-8"))):
            values.update(int(match.group(name)) for name in ("paths", "operations", "schemas"))
    return frozenset(values)


def _api_source_files() -> list[pathlib.Path]:
    return [entry.path for entry in _surface_inventory() if entry.text is not None]


def _is_live_surface_entry(entry: TrackedText) -> bool:
    """Whether tracked text belongs to a live source/configuration role.

    Default-allow is the load-bearing property: a new path such as ``scripts/*.toml`` enters
    without teaching this guard its parent or suffix. Exclusions name repository roles whose
    stale counts are intentional inputs/evidence and are guarded by their own instruments.
    """
    if entry.relative in LIVE_SURFACE_DOCUMENTS:
        return True
    if entry.relative in NON_LIVE_FILES or entry.relative.startswith(NON_LIVE_PREFIXES):
        return False
    return not NON_LIVE_PATH_PARTS.intersection(entry.relative.split("/"))


def _surface_inventory() -> list[TrackedText]:
    return [entry for entry in _tracked_inventory() if _is_live_surface_entry(entry)]


def _contract_info_prose() -> str:
    """The contract's own ``info`` block -- title, summary and description.

    `W18-SEAL` section 10.5: the served document is *not* this block, because ``app.py``
    builds it with its own ``_TITLE`` and ``_DESCRIPTION``. Both are unguarded copies and
    both are checked -- ``app.py`` as a source file above, this block here.
    """
    info = json.loads(API_CONTRACT.read_text(encoding="utf-8"))["info"]
    return "\n".join(
        str(info.get(key, "")) for key in ("title", "summary", "description")
    )


#: A line break inside a comment, with whatever continuation marker the language uses.
#: JSDoc and Python both wrap prose across lines and both put the break *between* the
#: number and its noun as readily as anywhere else.
_WRAP = re.compile(r"\n[ \t]*(?:\*(?!/)|#)?[ \t]*")


def _unwrap(text: str) -> str:
    """Join wrapped comment lines so a claim split across two of them is still one claim.

    Measured, not guessed. ``web/src/app/bff/v1/[...path]/route.ts`` said:

        * **Why every operation and not a route per operation.** `T-6` says the same twelve
        * operations must keep working when the alpha's static token is replaced [...]

    The number ended one line and the noun began the next, behind a ``*`` continuation
    marker, so the pattern matched nothing at all. Widening the scanned trees without this
    would have added the file and still missed the defect in it -- the guard would have
    reported the one claim in that docstring that is **correct** ("twelve paths") and
    stayed silent on the two that are stale. `D-27`'s lesson, one level down: a claim the
    checker cannot read is not a claim it is checking.

    The replacement is a single space, so an offset into the unwrapped text is not an
    offset into the file; nothing here reports positions, only phrases.
    """
    return _WRAP.sub(" ", text)


def _claims(text: str) -> Iterator[tuple[str, str | None, int]]:
    """Every quantified phrase in prose whose surrounding subject is the API surface.

    Canonical operation/path/schema/code nouns get a dimension-specific expectation. An unknown
    noun is considered only inside an explicit API-surface/document assertion. It is compared
    with the current dimensions without consulting Git history, so a shallow clone cannot make
    an old or arbitrary count invisible. Exact local-count exemptions remain visible and
    mutation-testable.
    """
    text = _unwrap(text)
    for match in _QUANTIFIED_PHRASE.finditer(text):
        phrase = match.group(0).lower().replace("-", " ")
        if any(phrase.startswith(local) for local in LOCAL_COUNTS):
            continue
        number = match.group("number").lower()
        value = int(number) if number.isdigit() else NUMBER_WORDS[number]
        first_label = match.group("label").lower().rstrip("s")
        if first_label in _NON_NOUN_LABELS:
            continue
        tail = text[match.end() : match.end() + 12]
        if first_label == "code" and re.match(r"[ -]+(?:unit|point)s?\b", tail, re.IGNORECASE):
            continue
        dimension = next(
            (plural for plural, singular in _SINGULAR.items() if first_label == singular),
            None,
        )
        if dimension is None:
            clause_start = max(text.rfind(mark, 0, match.start()) for mark in ".!?;\n") + 1
            following = [text.find(mark, match.end()) for mark in ".!?;\n"]
            clause_end = min(position for position in following if position >= 0) if any(
                position >= 0 for position in following
            ) else len(text)
            clause = text[clause_start:clause_end]
            before_count = text[clause_start : match.start()]
            if not (
                _SURFACE_SUBJECT.search(clause)
                or _TOTALITY_ASSERTION_PREFIX.search(before_count)
            ):
                continue
            if value not in _documented_surface_values():
                continue
        yield match.group(0), dimension, value


def _sources() -> list[tuple[str, str]]:
    named = [
        (entry.relative, entry.text)
        for entry in _surface_inventory()
        if entry.text is not None
    ]
    named.append(("contracts/api/v1/openapi.json -> info", _contract_info_prose()))
    return named


def _wrong_surface_claims(name: str, text: str) -> list[str]:
    counts = _surface_counts()
    wrong: list[str] = []
    for phrase, dimension, value in _claims(text):
        if (name, phrase) in KNOWN_HISTORICAL_SURFACE_CLAIMS:
            continue
        normalised_phrase = phrase.lower().replace("-", " ")
        if (name, normalised_phrase) in PATH_LOCAL_COUNTS:
            continue
        expected = counts[dimension] if dimension is not None else set(counts.values())
        disagrees = value != expected if isinstance(expected, int) else value not in expected
        if disagrees:
            wrong.append(
                f"{name}: {phrase!r} states {value} for "
                f"{dimension or 'an unlisted surface noun'}, expected {expected}"
            )
    return wrong


# ---------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------


def test_the_counts_are_read_from_the_documents_and_are_plausible() -> None:
    """The expectation comes from the documents, so a reseal moves it by itself.

    Asserted rather than assumed: a guard whose expected value silently became ``0``
    would pass over prose it was meant to police.
    """
    counts = _surface_counts()
    assert set(counts) == {"operations", "schemas", "paths", "codes"}
    assert all(value > 0 for value in counts.values()), counts
    assert counts["operations"] >= counts["paths"]


def test_the_api_prose_states_the_surface_this_document_declares() -> None:
    """`D-23`. Every claim about the size of the surface agrees with the surface."""
    wrong: list[str] = []
    for name, text in _sources():
        wrong.extend(_wrong_surface_claims(name, text))
    assert not wrong, (
        "prose states a surface size the frozen document contradicts. The conformance "
        "engine cannot see this -- it drops description, summary and title as "
        "annotation -- so this guard is the only thing that can. Correct the prose by "
        "re-measuring it, never by find-and-replace (W18-SEAL), or register the phrase "
        "in the path-qualified local-count registry if it is a subset and not the surface:\n  "
        + "\n  ".join(wrong)
    )


def test_the_guard_actually_reaches_the_files_that_carried_the_defect() -> None:
    """A guard that scanned nothing would pass. `app.py` carried six of the thirty-five."""
    scanned = {path.name for path in _api_source_files()}
    for name in ("app.py", "security.py", "declarations.py", "README.md"):
        assert name in scanned, f"{name} is not being scanned"
    assert len(scanned) >= 10, sorted(scanned)
    # ...and it finds claims in them, rather than matching nothing at all.
    found = sum(len(list(_claims(text))) for _, text in _sources())
    assert found >= 10, f"the claim pattern matched {found} statements; it is not working"


def test_tracked_file_discovery_has_no_suffix_blind_spot() -> None:
    """`D-99`/`D-100`: Git inventory reaches old blind extensions and the seam spec."""
    inventory = _tracked_inventory()
    assert len(inventory) == len({entry.relative for entry in inventory})
    assert all(entry.classification in {"utf8-text", "binary", "non-utf8", "unreadable"} for entry in inventory)

    surface = {entry.relative: entry for entry in _surface_inventory()}
    for relative in (
        "infra/deploy/Dockerfile.api",
        "infra/deploy/compose.server.yml",
        "infra/deploy/proxy/nginx.conf",
        "infra/deploy/env/alpha.env.example",
        "infra/deploy/deploy.sh",
        "docs/program/P02_SEAMS.md",
    ):
        assert relative in surface, f"tracked live prose escaped discovery: {relative}"
        assert surface[relative].classification == "utf8-text", surface[relative]

    opaque = [entry for entry in surface.values() if entry.classification != "utf8-text"]
    assert not opaque, "live surface file is binary/unreadable and needs an explicit parser or exclusion"


def test_a_new_top_level_live_path_is_in_scope_without_a_path_or_suffix_edit() -> None:
    """`JA-02`: default-allow reaches a new scripts/TOML source; test evidence stays out."""
    relative = "scripts/judge-surface.toml"
    prose = "The API surface has twelve facets."
    live = TrackedText(REPO_ROOT / relative, relative, prose, "utf8-text")
    assert _is_live_surface_entry(live)
    assert any("'twelve facets' states 12" in item for item in _wrong_surface_claims(relative, prose))

    fixture_relative = "web/tests/fixtures/judge-surface.toml"
    fixture = TrackedText(
        REPO_ROOT / fixture_relative, fixture_relative, prose, "utf8-text"
    )
    assert not _is_live_surface_entry(fixture)


def test_a_whole_surface_claim_needs_no_registered_subject_or_noun_alias() -> None:
    """`JA-01`: totality, not a list containing HTTP/interface/endpoint, makes this a claim."""
    counts = _surface_counts()
    for prose in (
        "The complete HTTP interface exposes twelve endpoints.",
        "The entire RPC facade exposes twelve facets.",
    ):
        claims = list(_claims(prose))
        assert len(claims) == 1 and claims[0][1:] == (None, 12), claims
        assert claims[0][2] not in set(counts.values())


def test_historical_surface_values_do_not_depend_on_git_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _documented_surface_values.cache_clear()

    def refuse_git(*args: object, **kwargs: object) -> None:
        raise AssertionError("documented surface history must not invoke git")

    monkeypatch.setattr(subprocess, "run", refuse_git)
    assert 12 in _documented_surface_values()
    _documented_surface_values.cache_clear()


def test_p02_seam_makes_a_current_claim_the_guard_reads() -> None:
    counts = _surface_counts()
    seam = (REPO_ROOT / "docs/program/P02_SEAMS.md").read_text(encoding="utf-8")
    claims = list(_claims(seam))
    assert any(dimension == "operations" and value == counts["operations"] for _, dimension, value in claims)


def test_historical_surface_claim_registry_is_exact_and_live() -> None:
    current = _surface_counts()
    for relative, phrase in KNOWN_HISTORICAL_SURFACE_CLAIMS:
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        matches = [claim for claim in _claims(text) if claim[0] == phrase]
        assert len(matches) == 1, (relative, phrase, matches)
        _, dimension, value = matches[0]
        assert dimension is not None and value != current[dimension]


def test_a_stale_claim_in_a_previously_excluded_conf_file_is_red() -> None:
    """`D-99`: mutate the real extensionless scanner input in memory; `.conf` is not skipped."""
    relative = "infra/deploy/proxy/nginx.conf"
    text = (REPO_ROOT / relative).read_text(encoding="utf-8")
    mutated = text.replace("the thirty paths", "the twenty-nine paths", 1)
    assert mutated != text
    wrong = _wrong_surface_claims(relative, mutated)
    assert any("'twenty-nine paths' states 29" in item for item in wrong), wrong


def test_a_stale_current_claim_in_p02_seams_is_red() -> None:
    """`D-100`: the once-unscanned live seam document is mutation-tested by path."""
    relative = "docs/program/P02_SEAMS.md"
    text = (REPO_ROOT / relative).read_text(encoding="utf-8")
    mutated = text.replace("Thirty-seven operations, sealed.", "Thirty-six operations, sealed.", 1)
    assert mutated != text
    wrong = _wrong_surface_claims(relative, mutated)
    assert any("'Thirty-six operations' states 36" in item for item in wrong), wrong


def test_the_guard_reaches_the_bff_route_handler() -> None:
    """`W22-WEB`: the fifth stale count was in a tree this guard did not read.

    Named by path, not by count: the assertion is that this specific file is in the scan,
    because "some TypeScript file is scanned" would pass over a rename of it.
    """
    scanned = {str(path.relative_to(REPO_ROOT)) for path in _api_source_files()}
    assert "web/src/app/bff/v1/[...path]/route.ts" in scanned, sorted(
        name for name in scanned if name.startswith("web/")
    )


def test_the_bff_handler_still_makes_a_claim_this_guard_can_read() -> None:
    """The file is scanned *and* something in it is being checked.

    A handler that stopped describing the surface would make the widening above a scan of
    prose with no claims in it, which passes while checking nothing -- `D-27`'s shape.
    """
    route = REPO_ROOT / "web" / "src" / "app" / "bff" / "v1" / "[...path]" / "route.ts"
    claims = list(_claims(route.read_text(encoding="utf-8")))
    nouns = {noun for _, noun, _ in claims}
    assert "operations" in nouns and "paths" in nouns, claims


def test_the_guard_reaches_the_shared_api_client() -> None:
    """`D-41`: both stale comments sat in a tree this guard did not read.

    Named by path for the same reason as the check above it: "some file under `web/src`
    is scanned" would pass over a move of exactly these two.
    """
    scanned = {str(path.relative_to(REPO_ROOT)) for path in _api_source_files()}
    for name in (
        "web/src/shared/api/errors.ts",
        "web/src/shared/api/authorization.ts",
    ):
        assert name in scanned, sorted(
            found for found in scanned if found.startswith("web/")
        )


def test_the_shared_api_client_still_makes_a_claim_this_guard_can_read() -> None:
    """Scanned *and* checked. `W22-WEB`'s shape, one directory over.

    `errors.ts` states the size of the catalog and `authorization.ts` the size of the
    operation set. If either stopped saying so, the widening above would be a scan of
    prose with no claims in it -- green while checking nothing.
    """
    shared = REPO_ROOT / "web" / "src" / "shared" / "api"
    errors = list(_claims((shared / "errors.ts").read_text(encoding="utf-8")))
    assert any(noun == "codes" for _, noun, _ in errors), errors
    authorization = list(
        _claims((shared / "authorization.ts").read_text(encoding="utf-8"))
    )
    assert any(noun == "operations" for _, noun, _ in authorization), authorization


# ---------------------------------------------------------------------------
# The guard, shown able to fail
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("prose", "noun"),
    [
        ("The twelve operations of the PC-01 surface.", "operations"),
        ("twelve public operations", "operations"),
        ("The API has twelve routes", None),
        ("guards all twelve operations", "operations"),
        ("The 43 schema names are generated from the models.", "schemas"),
        ("the ten paths of this surface", "paths"),
        # Pre-`R-3`, when the catalog had twenty. "twenty-one" is NOT used here: it
        # is the current count, so it would assert a claim that has become true. `R-8`
        # would have made it stale again and was reverted by the owner -- see `D-18`.
        ("its error_code drawn from the twenty-code catalog", "codes"),
        # `W22-WEB`: the two spellings that were invisible before the widening.
        # A claim wrapped across a JSDoc continuation line, exactly as route.ts had it.
        ("`T-6` says the same twelve\n * operations must keep working", "operations"),
        # An unlisted noun inside an explicit surface assertion is still read.
        ("the API surface has twelve widgets.", None),
        # `JA-01`: neither the subject nor the noun is a registered API alias. The semantic
        # totality assertion is enough.
        ("The complete HTTP interface exposes twelve endpoints.", None),
        ("The entire RPC facade exposes twelve facets.", None),
    ],
)
def test_a_stale_count_is_caught(prose: str, noun: str) -> None:
    """The exact wordings `W18-SEAL` had to correct, each shown to redden.

    These are the pre-`R-5` and pre-`R-3` spellings. If the surface ever really does have
    twelve operations again this test says so, rather than enforcing a claim that has
    become true.
    """
    counts = _surface_counts()
    claims = list(_claims(prose))
    assert claims, f"the pattern did not even match {prose!r}"
    if noun is None:
        assert any(value not in set(counts.values()) for _, _, value in claims)
    else:
        assert any(
            value != counts[noun] for _, found_noun, value in claims if found_noun == noun
        ), f"{prose!r} no longer disagrees with the document; the counts are {counts}"


def test_a_current_count_is_not_caught() -> None:
    """The other direction: correct prose passes, so the guard is not simply always red."""
    counts = _surface_counts()
    prose = (
        f"The {counts['operations']} operations of the PC-01 surface, "
        f"{counts['paths']} paths and {counts['schemas']} schemas."
    )
    assert [(noun, value) for _, noun, value in _claims(prose)] == [
        ("operations", counts["operations"]),
        ("paths", counts["paths"]),
        ("schemas", counts["schemas"]),
    ]


def test_a_claim_wrapped_across_a_comment_line_is_still_one_claim() -> None:
    """`W22-WEB`. The gap that made the fifth stale count invisible, shown closed.

    Before ``_unwrap`` the pattern matched *nothing* in the text below, so widening the
    scan to `web/` would have added the file and reported only the one figure in it that
    was correct. Both marker styles are covered: JSDoc's ``*`` and Python's ``#``.
    """
    counts = _surface_counts()
    for wrapped in (
        "says the same twelve\n * operations must keep working",
        "says the same twelve\n# operations must keep working",
        "says the same twelve\n    operations must keep working",
    ):
        assert not list(_QUANTIFIED_PHRASE.finditer(wrapped)), "the raw text should not match"
        claims = list(_claims(wrapped))
        assert claims, f"_unwrap did not join {wrapped!r}"
        assert claims[0][1] == "operations" and claims[0][2] == 12
        assert claims[0][2] != counts["operations"]


def test_unwrapping_does_not_invent_a_claim_across_a_blank_line() -> None:
    """The other direction: a number ending a paragraph is not joined to the next one.

    A normalizer that collapsed everything would manufacture claims out of unrelated
    sentences, and a guard that reddens on prose nobody wrote is worse than no guard.
    """
    assert not list(_claims("there are twelve.\n\n * Operations are forwarded verbatim."))
    # A `*/` that closes a comment is not a continuation marker either.
    assert not list(_claims("the same twelve\n */\nconst operations = 1;"))


def test_a_handler_count_is_checked_as_an_operation_count() -> None:
    """`W22-WEB`. An unlisted noun is checked from its API-surface context."""
    counts = _surface_counts()
    claims = list(_claims("the API surface would need twelve handlers"))
    assert claims == [("twelve handlers", None, 12)]
    assert 12 not in set(counts.values())
    # And the true figure passes, so this is not simply always red.
    assert all(
        value in set(counts.values())
        for _, _, value in _claims(
            f"the API surface would need {counts['operations']} handlers"
        )
    )


def test_a_number_inside_a_hyphenated_token_is_not_a_count() -> None:
    """`W27-WEB`. The first thing the widening to `web/src` reported was an encoding.

    `entities/finding-observation/model/quotation.ts` says *"counts UTF-16 code units"*,
    and the pattern read the `16` of `UTF-16` as a count of catalog codes. A phrase in
    `LOCAL_COUNTS` would have suppressed that exact number and let `UTF-32` through.
    """
    assert not list(
        _claims("`String.prototype.length` counts UTF-16 code units, so a quotation")
    )
    assert not list(_claims("a UTF-8 code point"))
    # The same number written as a count is still read, so this excludes a token and not
    # a number: nothing here is registered against the value 16.
    assert list(_claims("16 codes")) == [("16 codes", "codes", 16)]


def test_code_units_and_code_points_are_not_catalog_codes() -> None:
    """A unit of text is not an entry in the error catalog, whatever the number is."""
    for text in ("a span of 12 code units", "twelve code points", "two code units"):
        assert not list(_claims(text)), text
    # ...and the bare noun is still a claim, so the lookahead excludes the units and not
    # the word `code`.
    counts = _surface_counts()
    claims = list(_claims("twelve codes"))
    assert claims == [("twelve codes", "codes", 12)]
    assert 12 != counts["codes"]


def test_a_registered_local_count_is_not_a_surface_claim() -> None:
    """`LOCAL_COUNTS` suppresses the phrase and nothing wider."""
    counts = _surface_counts()
    assert not list(_claims("the two schemas that only it referenced"))
    # The same number against an unregistered noun is still checked.
    stale = list(_claims("two operations"))
    assert stale and stale[0][2] != counts["operations"]
