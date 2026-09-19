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
from typing import Iterator

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
#: The two trees that describe the surface in prose. `W18-SEAL`'s sweep covered `src/`
#: only, so `infra/deploy/` kept four statements saying twelve operations -- including
#: `serve.py`'s module docstring, which is the first thing an operator reads about the
#: process. This guard found them on its first widening, which is the row's own point:
#: a claim a checker cannot read is a claim nobody is checking.
SCANNED_TREES = (
    REPO_ROOT / "src" / "auditmanager" / "api",
    REPO_ROOT / "infra" / "deploy",
    # `W22-WEB`, the fifth stale count. The BFF route handler forwards the whole surface
    # and describes its size in a JSDoc block; it is the only place in `web/` that makes
    # such a claim, and it was outside every tree this guard read. Widening here is the
    # cheap repair the row asks for: the sixth is caught rather than corrected by hand.
    REPO_ROOT / "web" / "src" / "app" / "bff",
)
API_SOURCE = SCANNED_TREES[0]
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

#: The nouns whose count is a claim about the size of something a document declares, and
#: the document key each one is checked against.
SURFACE_NOUNS: dict[str, str] = {
    "operation": "operations",
    "operations": "operations",
    "schema": "schemas",
    "schemas": "schemas",
    "path": "paths",
    "paths": "paths",
    "code": "codes",
    "codes": "codes",
    # A count of handlers is a count of operations: the BFF's docstring argued for a
    # catch-all by saying what a route-per-operation would cost, "not to twelve
    # handlers", and that number is a claim about the surface exactly as "twelve
    # operations" is. Without this the sentence was invisible to the guard while
    # carrying the same stale figure.
    "handler": "operations",
    "handlers": "operations",
}

_NUMBER = r"(?:\d{1,3}|" + "|".join(
    sorted((re.escape(w) for w in NUMBER_WORDS), key=len, reverse=True)
) + r")"
#: ``forty-six schemas``, ``46 schema names``, ``fifteen-operation surface``.
_CLAIM = re.compile(
    rf"\b(?P<number>{_NUMBER})[ -](?P<noun>operations?|schemas?|paths?|codes?|handlers?)\b",
    re.IGNORECASE,
)

#: Phrases that state a count of one of :data:`SURFACE_NOUNS` and deliberately do **not**
#: claim the size of the surface. Each is a statement about a subset or about a local
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
    }
)


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


def _api_source_files() -> list[pathlib.Path]:
    return sorted(
        path
        for tree in SCANNED_TREES
        for path in tree.rglob("*")
        if path.is_file()
        and path.suffix in {".py", ".md", ".ts", ".tsx"}
        and "__pycache__" not in path.parts
    )


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


def _claims(text: str) -> Iterator[tuple[str, str, int]]:
    """Every count-of-a-surface-noun claim in ``text`` that is not registered as local."""
    text = _unwrap(text)
    for match in _CLAIM.finditer(text):
        phrase = match.group(0).lower().replace("-", " ")
        number, noun = match.group("number").lower(), match.group("noun").lower()
        if phrase in LOCAL_COUNTS:
            continue
        # A registered local phrase may be the head of a longer one.
        if any(
            text[match.start() : match.start() + len(local)].lower().replace("-", " ")
            == local
            for local in LOCAL_COUNTS
        ):
            continue
        value = int(number) if number.isdigit() else NUMBER_WORDS[number]
        yield match.group(0), SURFACE_NOUNS[noun], value


def _sources() -> list[tuple[str, str]]:
    named = [
        (str(path.relative_to(REPO_ROOT)), path.read_text(encoding="utf-8"))
        for path in _api_source_files()
    ]
    named.append(("contracts/api/v1/openapi.json -> info", _contract_info_prose()))
    return named


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
    counts = _surface_counts()
    wrong: list[str] = []
    for name, text in _sources():
        for phrase, noun, value in _claims(text):
            if value != counts[noun]:
                wrong.append(
                    f"{name}: {phrase!r} states {value} {noun}, "
                    f"but the document declares {counts[noun]}"
                )
    assert not wrong, (
        "prose states a surface size the frozen document contradicts. The conformance "
        "engine cannot see this -- it drops description, summary and title as "
        "annotation -- so this guard is the only thing that can. Correct the prose by "
        "re-measuring it, never by find-and-replace (W18-SEAL), or register the phrase "
        "in LOCAL_COUNTS if it is a subset and not the surface:\n  "
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


# ---------------------------------------------------------------------------
# The guard, shown able to fail
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("prose", "noun"),
    [
        ("The twelve operations of the PC-01 surface.", "operations"),
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
        # A count of handlers is a count of operations.
        ("not to twelve handlers.", "operations"),
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
        assert not list(_CLAIM.finditer(wrapped)), "the raw text should not match"
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
    """`W22-WEB`. ``handlers`` was not a surface noun, so the claim was not read."""
    counts = _surface_counts()
    claims = list(_claims("not to twelve handlers"))
    assert claims == [("twelve handlers", "operations", 12)]
    assert 12 != counts["operations"]
    # And the true figure passes, so this is not simply always red.
    assert all(
        value == counts["operations"]
        for _, _, value in _claims(f"not to {counts['operations']} handlers")
    )


def test_a_registered_local_count_is_not_a_surface_claim() -> None:
    """`LOCAL_COUNTS` suppresses the phrase and nothing wider."""
    counts = _surface_counts()
    assert not list(_claims("the two schemas that only it referenced"))
    # The same number against an unregistered noun is still checked.
    stale = list(_claims("two operations"))
    assert stale and stale[0][2] != counts["operations"]
