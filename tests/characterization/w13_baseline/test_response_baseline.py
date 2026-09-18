"""The response baseline, compared against the current implementation.

This suite is the wave's safety net. It re-drives every case in ``journey.py`` and
requires the response to reproduce the committed record in ``records/`` -- status, every
header, and the body byte for byte, with only the substitutions each record names.

Stage 2 (`W13-API`) rewrites ``src/auditmanager/api/**`` as FastAPI path operations. When
it does, this suite is the thing that says whether the rewrite changed the surface.
**Exactly one record may change**, the one carrying ``exception`` -- see
:data:`journey.EXCEPTION_D7`. Every other difference is a failure of the wave.

A record is only evidence if the comparison can fail, so
:func:`test_the_comparison_reddens_on_a_planted_difference` plants one of each kind and
requires each to be reported.

Two records declare **`O1`**: the *order* of the published findings is not compared,
because it is not something the system promises (`journey.UNORDERED_O1_WHY`). What is
compared instead is the sorted list of the sequence's byte slices -- a permutation, and
nothing else, is erased -- plus the ordering *rule* the system does promise, asserted
against the live response by :func:`test_the_published_findings_come_back_ascending_by_
finding_uid` and its CSV twin.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

_JOURNEY = "w13_baseline_journey"


def _load() -> Any:
    existing = sys.modules.get(_JOURNEY)
    if existing is not None:
        return existing
    path = Path(__file__).resolve().with_name("journey.py")
    spec = importlib.util.spec_from_file_location(_JOURNEY, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[_JOURNEY] = module
    spec.loader.exec_module(module)
    return module


journey = _load()

#: `T-6`. The credential every request in this corpus presents, written out here rather
#: than imported from ``journey`` for the same reason every other expectation in this file
#: is a literal: a check that reads its expectation from the thing it is checking cannot
#: tell you that the thing moved. ``OPERATING_CONSTRAINTS.md`` section 12.
STATIC_TOKEN = "w13-baseline-static-token"

RECORD_FILES = sorted(journey.RECORDS.glob("*.json"))

#: The frozen document's fifteen operationIds, written out rather than read from the
#: contract: this suite's job is to notice a surface that changed, and an expectation
#: computed from a file the change could also touch would not.
#:
#: **`W18-SEAL` moved it from twelve to fifteen** under owner ruling `R-5`. Adding an
#: operation adds a case and a record; it is not a permitted *change* to any record and
#: carries no exception block. What changed here is the count, not the rule: every one of
#: the fifteen still has to be covered by at least one record.
FIFTEEN_OPERATIONS = (
    "appendDecision",
    "createProject",
    "exportRunCsv",
    "getDocumentVersion",
    "getFinding",
    "getRunStatus",
    "listDecisionHistory",
    "listProjects",
    "listRunFindings",
    "startRun",
    "listDocuments",
    "listRuns",
    "listVersions",
    "streamDocumentVersionContent",
    "uploadDocument",
)


@pytest.fixture(scope="session")
def exchanges() -> dict[str, Any]:
    """One journey, driven once, indexed by case.

    ``AUDITMANAGER_PROVIDER_MODE`` is named out loud inside ``build_apps`` because the
    root ``conftest`` strips every provider-selecting variable for the whole session --
    a suite that wants a mode has to say so, and this one must never be able to spend.
    """
    good, refused = journey.build_apps()
    return {item.case: item for item in journey.run_journey(good, refused)}


def test_the_record_set_and_the_journey_agree(exchanges: dict[str, Any]) -> None:
    """No record without a case, and no case without a record."""
    recorded = {path.stem for path in RECORD_FILES}
    driven = set(exchanges)
    assert recorded == driven, (
        f"records with no case: {sorted(recorded - driven)}; "
        f"cases with no record: {sorted(driven - recorded)}"
    )
    assert recorded, "the baseline is empty"


def test_every_one_of_the_fifteen_operations_is_covered() -> None:
    covered = set()
    for path in RECORD_FILES:
        operation = json.loads(path.read_text(encoding="utf-8"))["operation"]
        if operation is not None:
            covered.add(operation)
    assert covered == set(FIFTEEN_OPERATIONS), (
        f"operations with no record: {sorted(set(FIFTEEN_OPERATIONS) - covered)}; "
        f"records naming an operation the contract does not declare: "
        f"{sorted(covered - set(FIFTEEN_OPERATIONS))}"
    )


#: The permitted-exception set, case by case with the debt that moved it. Written out as a
#: literal, never derived from the records: an expectation computed from the files it
#: checks cannot report that a sixth, seventh or eighth record quietly acquired a block.
#:
#: **`W17-VIEW` added the second entry**, and it is the second era of this guard exactly as
#: `W13-API` was the second era of `test_the_baseline_records_the_authenticated_era`. What
#: changed is the *count*, not the rule: every marked record still has to name a debt, cite
#: the commit that moved it, carry a `permitted_change` describing the whole of the move,
#: and be compared byte for byte against the new expectation like every other record.
#:
#: **`W18-SEAL` made the value a tuple**, because the five `RunStatus` records have now
#: been moved twice -- by `D-19`, then by `D-21` under owner ruling `R-5` -- and a record
#: moved by two debts has to name two. A comma inside a string would have kept the shape
#: and lost the property: a list of debts is countable and a sentence is not. The record's
#: own `debt` key is a list on all six for the same reason -- one spelling, not two.
#:
#: **`W19-API` added the seventh entry**, record 16, under owner ruling `R-10`: `D-16`'s
#: other half, `listProjects.document_count`. It is the first entry here for an operation
#: whose body changed while the contract did not -- the field was declared by the seal and
#: had no producer -- and `R-10` names that distinction in as many words. The rule is
#: still the rule: a named debt, a cited commit, a `permitted_change` describing the whole
#: of the move, and the same byte-for-byte comparison every unmarked record gets.
PERMITTED_EXCEPTIONS = {
    "03-startRun.success": ("D-19", "D-21"),
    "04-startRun.replay": ("D-19", "D-21"),
    "05-startRun.replay_with_normalised_property": ("D-19", "D-21"),
    "06-getRunStatus.success": ("D-19", "D-21"),
    "07-getRunStatus.correlation_supplied": ("D-19", "D-21"),
    "16-listProjects.success": ("D-16",),
    "31-streamDocumentVersionContent.storage_credential_refused": ("D-7",),
}


def test_exactly_the_named_records_are_marked_as_permitted_exceptions() -> None:
    """The D-7 path, the D-19 path and the D-16 path, and nothing else.

    A safety net with an unnamed exception is one somebody talks their way past at the
    end of a long wave. This is the assertion that makes the exceptions countable.

    `D-7` is record 31: the storage credential refusal got a code of its own at `e6d0a6a`
    under owner ruling `R-3`. `D-19` and `D-21` are the five records carrying a
    `RunStatus` body. `D-19`: a published run reported no stage timings, no finding count,
    and one instant for its creation and its terminal -- and **those five records had
    pinned the last of those as the expectation**, `created_at` and `terminal_at` sharing
    the token `{{ts_5}}` because substitution is by exact value and the two values were
    identical to the microsecond. A record that reproduces a defect byte for byte is
    protecting it. `D-21`: the same five bodies now carry `cost_micros`, `cost_basis` and
    `model_call_count`, the three properties owner ruling `R-5` added to `RunStatus`.

    `D-16` is record 16: every item of a `listProjects` page now carries the
    `document_count` the sealed `Project` has always declared, filled under owner ruling
    `R-10`. Nothing in `contracts/**` moved for it, which is exactly the distinction
    between `R-10` and the `R-5` reseal that declined this change.
    """
    marked = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))["exception"]
        for path in RECORD_FILES
    }
    exceptions = {case: value for case, value in marked.items() if value}
    assert sorted(exceptions) == sorted(PERMITTED_EXCEPTIONS), (
        f"the permitted-exception set is {sorted(exceptions)}"
    )
    for case, block in exceptions.items():
        assert tuple(block["debt"]) == PERMITTED_EXCEPTIONS[case], (case, block["debt"])
        assert block["permitted_change"], f"{case} is marked but describes no change"
        assert block["decided_by"], f"{case} cites no commit"
    assert "R-3" in exceptions[
        "31-streamDocumentVersionContent.storage_credential_refused"
    ]["ruling"]
    # The five `RunStatus` records cite the ruling that authorised the *contract* half of
    # their move. `D-19` needed none -- it repaired a declared field that had no producer
    # -- but `D-21` adds three properties, and adding a property is the owner's act.
    for case in PERMITTED_EXCEPTIONS:
        if "D-21" in PERMITTED_EXCEPTIONS[case]:
            assert "R-5" in exceptions[case]["ruling"], case
    # And record 16 cites the one that authorised *changing an existing operation's body*.
    # `R-5` explicitly did not, which is why `W18-SEAL` left this field unfilled; citing
    # it here would be citing an authority that was declined.
    assert "R-10" in exceptions["16-listProjects.success"]["ruling"]


def test_the_five_run_status_records_no_longer_pin_one_instant_for_the_whole_run() -> None:
    """The defect this corpus had frozen, asserted against the records themselves.

    `W15RUN-5` was readable in this directory before it was found in a browser: a run
    that took eleven seconds recorded the same token for the instant it was created and
    the instant it terminated. Re-capturing alone would have erased that without anyone
    having to say it had been there, so it is asserted here rather than left to a diff.
    """
    for case in (
        "03-startRun.success",
        "04-startRun.replay",
        "05-startRun.replay_with_normalised_property",
        "06-getRunStatus.success",
        "07-getRunStatus.correlation_supplied",
    ):
        record = json.loads(
            (journey.RECORDS / f"{case}.json").read_text(encoding="utf-8")
        )
        # The tokens sit inside the body's own quoting, so the recorded text parses as
        # JSON as it stands: `created_at` reads back as the string `{{ts_9}}`, and two
        # fields sharing one instant read back as the *same* token.
        body = json.loads(record["response"]["body"]["text"])
        assert body["created_at"] != body["terminal_at"], (
            f"{case} pins the same value for created_at and terminal_at, which is the "
            "D-19 defect recorded as the expectation"
        )
        for stage in body["stages"]:
            assert "started_at" in stage and "finished_at" in stage, (case, stage)


def _authorization_claims(record: dict[str, Any]) -> list[str]:
    """Every way a record could stop being a record of the authenticated era.

    One function, used by the guard and by the test that proves the guard can fail, so the
    proof exercises the rule rather than a second copy of it that could drift. The first
    version of the prover in this file re-implemented the rule, which proves only that a
    copy can fail.
    """
    found: list[str] = []
    if not record.get("pre_authorization"):
        found.append("no pre_authorization declaration")
    presented = [
        value
        for name, value in record["request"]["headers"]
        if name.lower() == "authorization"
    ]
    if presented != [f"Bearer {STATIC_TOKEN}"]:
        found.append(f"presents {presented!r} rather than the configured credential")
    if any(
        name.lower() == "proxy-authorization" for name, _ in record["request"]["headers"]
    ):
        found.append("the request carries Proxy-Authorization")
    # No case here exercises a caller's *rights*, and none omits the credential, so an
    # authorization answer in this corpus would mean the journey stopped doing what it
    # says it does. The seam's own refusals are asserted where they belong, in
    # `tests/integration/api/test_authorization.py`, which drives requests with no
    # credential and with a wrong one.
    if record["response"]["status"] in (401, 403):
        found.append(f"pins {record['response']['status']}, an authorization answer")
    return found


def test_the_baseline_records_the_authenticated_era() -> None:
    """Every record presents the credential, and none of them pins an authorization answer.

    **This test and the README paragraph beside it changed together, deliberately**, at the
    commit that put the `T-6` dependency in front of the twelve operations. `W13-SEAL`
    wrote the rule this replaces -- *the corpus makes no authorization claim* -- and said
    in its section 8.5 that it *"will go red the moment the journey authenticates, which it
    should. Change it and the README paragraph together, in the same commit, and say which
    era the records then belong to."* This is that change, and this is the era: authorized,
    with the credential presented on every request and the refusals asserted elsewhere.

    **The response bytes did not move.** The recapture that added the header to these files
    changed exactly three things per record -- ``captured_through``, ``pre_authorization``
    and the request's header list -- and nothing under ``response``. See
    ``docs/program/reviews/W13-API.md``.
    """
    offenders: list[str] = []
    for path in RECORD_FILES:
        record = json.loads(path.read_text(encoding="utf-8"))
        offenders.extend(f"{path.stem}: {claim}" for claim in _authorization_claims(record))
    assert offenders == [], (
        "the baseline has stopped being a record of the authenticated era:\n"
        + "\n".join(offenders)
    )


def test_the_authorization_era_check_can_fail() -> None:
    """The same rule, run against four planted records.

    A guard nobody has seen reject anything accepts anything -- the rule this corpus already
    applies to itself in :func:`test_the_comparison_reddens_on_a_planted_difference`.

    The plants are in-memory copies rather than rewritten files, because a test that edits
    `records/` would trip the gate's changed-during-the-run check.
    """
    clean = json.loads(RECORD_FILES[0].read_text(encoding="utf-8"))
    assert _authorization_claims(clean) == [], "the unperturbed record is already reported"

    anonymous = json.loads(json.dumps(clean))
    anonymous["request"]["headers"] = [
        pair for pair in clean["request"]["headers"] if pair[0].lower() != "authorization"
    ]
    assert _authorization_claims(anonymous) == [
        "presents [] rather than the configured credential"
    ]

    someone_elses = json.loads(json.dumps(clean))
    someone_elses["request"]["headers"] = [
        ["Authorization", "Bearer not-the-configured-token"] if pair[0] == "Authorization"
        else pair
        for pair in clean["request"]["headers"]
    ]
    assert _authorization_claims(someone_elses) == [
        "presents ['Bearer not-the-configured-token'] rather than the configured credential"
    ]

    refused = json.loads(json.dumps(clean))
    refused["response"]["status"] = 401
    assert _authorization_claims(refused) == ["pins 401, an authorization answer"]

    undeclared = json.loads(json.dumps(clean))
    del undeclared["pre_authorization"]
    assert _authorization_claims(undeclared) == ["no pre_authorization declaration"]


@pytest.mark.parametrize("path", RECORD_FILES, ids=lambda p: p.stem)
def test_the_response_reproduces_the_record(path: Path, exchanges: dict[str, Any]) -> None:
    expected = json.loads(path.read_text(encoding="utf-8"))
    exchange = exchanges[expected["case"]]
    found = journey.differences(exchange, expected)
    assert not found, (
        f"{expected['case']} no longer reproduces the recorded response.\n"
        + "\n".join(found)
        + (
            "\n\nThis record is the ONE path wave 13 may change, by D-7 / R-3. Cite the "
            "commit that decided it beside the new expectation."
            if expected["exception"]
            else "\n\nThis is not the permitted exception. Exactly one record may "
            "change in wave 13 and it is not this one."
        )
    )


def test_the_comparison_reddens_on_a_planted_difference(exchanges: dict[str, Any]) -> None:
    """Every kind of difference the comparison is supposed to catch, planted.

    A baseline nobody has seen reject anything is a baseline that will accept anything.
    """
    path = journey.RECORDS / "03-startRun.success.json"
    expected = json.loads(path.read_text(encoding="utf-8"))
    exchange = exchanges[expected["case"]]

    assert not journey.differences(exchange, expected), (
        "the unperturbed record must match before a planted difference means anything"
    )

    moved_status = json.loads(json.dumps(expected))
    moved_status["response"]["status"] = 200
    assert any(
        "status" in line for line in journey.differences(exchange, moved_status)
    ), "a moved status code was not reported"

    dropped_header = json.loads(json.dumps(expected))
    dropped_header["response"]["headers"] = [
        pair for pair in expected["response"]["headers"] if pair[0] != "X-Correlation-Id"
    ]
    assert journey.differences(exchange, dropped_header), (
        "a dropped X-Correlation-Id was not reported"
    )

    renamed_field = json.loads(json.dumps(expected))
    renamed_field["response"]["body"]["text"] = expected["response"]["body"][
        "text"
    ].replace('"provider_mode"', '"providerMode"')
    assert journey.differences(exchange, renamed_field), (
        "a renamed body property was not reported"
    )

    reordered = json.loads(json.dumps(expected))
    reordered["response"]["body"]["text"] = json.dumps(
        json.loads(
            expected["response"]["body"]["text"].replace("{{", "@@").replace("}}", "%%")
        ),
        sort_keys=True,
    ).replace("@@", "{{").replace("%%", "}}")
    assert journey.differences(exchange, reordered), (
        "a body whose keys were re-ordered and re-separated was not reported; this "
        "comparison is not byte-level"
    )

    csv_path = journey.RECORDS / "12-exportRunCsv.success.json"
    csv_expected = json.loads(csv_path.read_text(encoding="utf-8"))
    csv_exchange = exchanges[csv_expected["case"]]
    assert not journey.differences(csv_exchange, csv_expected)
    import base64

    no_bom = json.loads(json.dumps(csv_expected))
    no_bom["response"]["body"]["base64"] = base64.b64encode(
        base64.b64decode(csv_expected["response"]["body"]["base64"])[3:]
    ).decode("ascii")
    assert journey.differences(csv_exchange, no_bom), "a lost CSV BOM was not reported"

    lf_only = json.loads(json.dumps(csv_expected))
    lf_only["response"]["body"]["base64"] = base64.b64encode(
        base64.b64decode(csv_expected["response"]["body"]["base64"]).replace(
            b"\r\n", b"\n"
        )
    ).decode("ascii")
    assert journey.differences(csv_exchange, lf_only), (
        "a CSV with LF instead of CRLF was not reported"
    )

    pdf_path = journey.RECORDS / "14-streamDocumentVersionContent.success.json"
    pdf_expected = json.loads(pdf_path.read_text(encoding="utf-8"))
    pdf_exchange = exchanges[pdf_expected["case"]]
    assert not journey.differences(pdf_exchange, pdf_expected)
    wrong_length = json.loads(json.dumps(pdf_expected))
    wrong_length["response"]["body"]["sha256"] = "0" * 64
    assert journey.differences(pdf_exchange, wrong_length), (
        "a fixture that no longer matches its pinned digest was not reported"
    )


def test_a_content_length_that_does_not_describe_the_body_is_reported(
    exchanges: dict[str, Any],
) -> None:
    """The one header given a token unconditionally still has a rule behind it."""
    expected = json.loads(
        (journey.RECORDS / "01-createProject.success.json").read_text(encoding="utf-8")
    )
    exchange = exchanges[expected["case"]]
    tampered = journey.Exchange(
        case=exchange.case,
        operation=exchange.operation,
        purpose=exchange.purpose,
        method=exchange.method,
        target=exchange.target,
        request_headers=exchange.request_headers,
        request_body=exchange.request_body,
        request_body_note=exchange.request_body_note,
        status=exchange.status,
        headers=tuple(
            (name, "9999" if name == "Content-Length" else value)
            for name, value in exchange.headers
        ),
        body=exchange.body,
        tokens=exchange.tokens,
        body_kind=exchange.body_kind,
        body_note=exchange.body_note,
        exception=exchange.exception,
        unordered=exchange.unordered,
    )
    found = journey.differences(tampered, expected)
    assert any("Content-Length" in line for line in found), found


# --- O1: the declared order-insensitivity, and what it is still required to catch ----

UNORDERED_RECORDS = (
    "08-listRunFindings.success",
    "12-exportRunCsv.success",
)


def _body_bytes(expected: dict[str, Any]) -> bytes:
    import base64

    body = expected["response"]["body"]
    if body["kind"] == "base64":
        return base64.b64decode(body["base64"])
    return body["text"].encode("utf-8")


def _with_body(expected: dict[str, Any], raw: bytes) -> dict[str, Any]:
    import base64

    out = json.loads(json.dumps(expected))
    body = out["response"]["body"]
    if body["kind"] == "base64":
        body["base64"] = base64.b64encode(raw).decode("ascii")
    else:
        body["text"] = raw.decode("utf-8")
    return out


def _cut(expected: dict[str, Any]) -> tuple[bytes, bytes, list[bytes], bytes]:
    return journey.split_sequence(
        _body_bytes(expected), expected["unordered"]["sequence"]
    )


def _rebuilt(
    expected: dict[str, Any],
    elements: list[bytes],
    *,
    prefix: bytes | None = None,
    separator: bytes | None = None,
    suffix: bytes | None = None,
) -> dict[str, Any]:
    cut_prefix, cut_separator, _, cut_suffix = _cut(expected)
    return _with_body(
        expected,
        (prefix if prefix is not None else cut_prefix)
        + (separator if separator is not None else cut_separator).join(elements)
        + (suffix if suffix is not None else cut_suffix),
    )


def _load(case: str) -> dict[str, Any]:
    return json.loads(journey.record_path(case).read_text(encoding="utf-8"))


def _marked(element: bytes, sequence: str) -> bytes:
    """One changed element, in a way that stays valid UTF-8 for either body kind."""
    if sequence.startswith("json-array"):
        assert element.endswith(b"}")
        return element[:-1] + b', "planted": 1}'
    return element + b",planted"


def test_exactly_two_records_declare_an_unordered_sequence() -> None:
    """O1 is countable, the way the permitted exception is.

    An order-insensitive comparison nobody counted is one that spreads to a third record
    at the end of a long wave, which is how a byte-for-byte baseline stops being one.
    """
    declared = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))["unordered"]
        for path in RECORD_FILES
    }
    present = {case: value for case, value in declared.items() if value}
    assert sorted(present) == sorted(UNORDERED_RECORDS), (
        f"the order-insensitive set is {sorted(present)}"
    )
    for case, value in present.items():
        assert value["declared"] == "O1", case
        assert value["sequence"] in journey.SEQUENCE_SPLITTERS, (case, value["sequence"])
        for answer in ("what", "why", "cannot_hide", "still_pinned"):
            assert value[answer].strip(), f"{case} declares O1 without answering {answer}"


def test_the_declared_split_is_lossless_and_not_vacuous() -> None:
    """Both records really are cut into several elements, and the cut reassembles."""
    for case in UNORDERED_RECORDS:
        expected = _load(case)
        raw = _body_bytes(expected)
        prefix, separator, elements, suffix = _cut(expected)
        assert len(elements) == 3, (case, len(elements))
        assert prefix + separator.join(elements) + suffix == raw, case
        assert len({*elements}) == 3, f"{case}'s elements are not distinct"


@pytest.mark.parametrize("case", UNORDERED_RECORDS)
def test_every_permutation_of_the_sequence_is_invisible(
    case: str, exchanges: dict[str, Any]
) -> None:
    """The one thing O1 erases, erased -- and it is really the bytes that moved."""
    import itertools

    expected = _load(case)
    exchange = exchanges[expected["case"]]
    assert not journey.differences(exchange, expected), (
        "the unperturbed record must match before a permutation means anything"
    )
    _, _, elements, _ = _cut(expected)
    seen = set()
    for order in itertools.permutations(range(len(elements))):
        permuted = [elements[index] for index in order]
        record = _rebuilt(expected, permuted)
        seen.add(_body_bytes(record))
        assert not journey.differences(exchange, record), (
            f"{case}: the order {order} was reported, so O1 is not erasing the order"
        )
    assert len(seen) == 6, f"{case}: the permutations did not produce six distinct bodies"


@pytest.mark.parametrize("case", UNORDERED_RECORDS)
def test_a_changed_element_is_reported_under_every_permutation(
    case: str, exchanges: dict[str, Any]
) -> None:
    """Erasing the order must not erase a change *inside* an element, wherever it sits."""
    import itertools

    expected = _load(case)
    exchange = exchanges[expected["case"]]
    sequence = expected["unordered"]["sequence"]
    _, _, elements, _ = _cut(expected)
    for order in itertools.permutations(range(len(elements))):
        for position in range(len(elements)):
            permuted = [elements[index] for index in order]
            permuted[position] = _marked(permuted[position], sequence)
            assert journey.differences(exchange, _rebuilt(expected, permuted)), (
                f"{case}: a changed element at {position} of {order} was not reported"
            )


@pytest.mark.parametrize("case", UNORDERED_RECORDS)
def test_a_dropped_a_duplicated_and_a_repeated_element_are_reported(
    case: str, exchanges: dict[str, Any]
) -> None:
    """The three ways a multiset can differ without any single element changing.

    The duplicate is the one that decides whether this is a *sorted list* comparison or
    a set comparison: replacing one element by a copy of another leaves the set of
    distinct elements smaller but the count identical, and a set comparison would pass it.
    """
    expected = _load(case)
    exchange = exchanges[expected["case"]]
    _, _, elements, _ = _cut(expected)

    for index in range(len(elements)):
        dropped = [item for position, item in enumerate(elements) if position != index]
        assert journey.differences(exchange, _rebuilt(expected, dropped)), (
            f"{case}: dropping element {index} was not reported"
        )
        repeated = list(elements)
        repeated.insert(index, elements[index])
        assert journey.differences(exchange, _rebuilt(expected, repeated)), (
            f"{case}: repeating element {index} was not reported"
        )

    for index in range(len(elements)):
        for other in range(len(elements)):
            if index == other:
                continue
            duplicated = list(elements)
            duplicated[other] = elements[index]
            assert journey.differences(exchange, _rebuilt(expected, duplicated)), (
                f"{case}: element {other} replaced by a copy of {index} was not "
                "reported; the comparison is a set, not a sorted list"
            )


@pytest.mark.parametrize("case", UNORDERED_RECORDS)
def test_the_bytes_outside_the_sequence_are_still_compared(
    case: str, exchanges: dict[str, Any]
) -> None:
    """Prefix, separator and suffix keep their byte-for-byte comparison."""
    expected = _load(case)
    exchange = exchanges[expected["case"]]
    prefix, separator, elements, suffix = _cut(expected)

    assert journey.differences(
        exchange, _rebuilt(expected, elements, prefix=prefix + b" ")
    ), f"{case}: a changed byte before the sequence was not reported"
    assert journey.differences(
        exchange, _rebuilt(expected, elements, suffix=b" " + suffix)
    ), f"{case}: a changed byte after the sequence was not reported"
    assert journey.differences(
        exchange, _rebuilt(expected, elements, separator=separator + b" ")
    ), f"{case}: a changed sequence separator was not reported"


def test_the_findings_specific_differences_o1_must_still_catch(
    exchanges: dict[str, Any],
) -> None:
    """The differences named by hand, in the record the flake was found in.

    Each is applied to a record whose elements have also been rotated, so what is being
    shown is that the change is caught *through* the order-insensitivity rather than
    beside it.
    """
    expected = _load("08-listRunFindings.success")
    exchange = exchanges[expected["case"]]
    _, _, elements, _ = _cut(expected)
    rotated = elements[1:] + elements[:1]

    for before, after, what in (
        (b'"category": "explicit_placeholder"', b'"category": "text_gap"', "a category"),
        (b'"char_start": 3470', b'"char_start": 3471', "an evidence offset"),
        (b'"current_verdict": "pending"', b'"current_verdict": "accepted"', "a verdict"),
        (b'"page_number": 8', b'"page_number": 9', "an evidence page"),
        (b"\xd1\x83\xd1\x82\xd0\xbe\xd1\x87\xd0\xbd\xd0\xb8\xd1\x82\xd1\x8c", b"uto4nit", "a Russian quote"),
    ):
        changed = [element.replace(before, after) for element in rotated]
        assert changed != rotated, f"the {what} plant changed nothing; the probe is stale"
        assert journey.differences(exchange, _rebuilt(expected, changed)), (
            f"{what} changed inside a permuted findings array was not reported"
        )


# --- the ordering rule, which IS promised and IS pinned ------------------------------


def _csv_rows(raw: bytes) -> list[list[str]]:
    import csv
    import io

    text = raw.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text, newline=""), dialect="excel"))


def test_the_published_findings_come_back_ascending_by_finding_uid(
    exchanges: dict[str, Any],
) -> None:
    """What the system *does* promise, asserted against the live response.

    O1 stops the record pinning which finding is first. This is the assertion that keeps
    the `ORDER BY f.finding_uid COLLATE "C"` itself guarded: a rewrite that dropped it
    would leave the record green and fail here.
    """
    body = json.loads(
        exchanges["08-listRunFindings.success"].body.decode("utf-8")
    )
    uids = [item["finding_uid"] for item in body["items"]]
    assert len(uids) > 1, "one finding cannot demonstrate an ordering"
    assert journey.ascending_under_c_collation(uids), (
        f"listRunFindings returned {uids!r}, which is not strictly ascending under "
        'COLLATE "C" -- the order the listing promises'
    )


def test_the_csv_rows_come_back_ascending_by_finding_uid_then_observation_id(
    exchanges: dict[str, Any],
) -> None:
    rows = _csv_rows(exchanges["12-exportRunCsv.success"].body)
    header, data = rows[0], rows[1:]
    finding = header.index("finding_uid")
    observation = header.index("finding_observation_id")
    keys = [(row[finding], row[observation]) for row in data]
    assert len(keys) > 1, "one row cannot demonstrate an ordering"
    assert journey.non_descending_under_c_collation(keys), (
        f"exportRunCsv returned {keys!r}, which descends somewhere; the export promises "
        '(finding_uid, finding_observation_id) ascending under COLLATE "C"'
    )


def test_the_two_ordering_rules_can_fail() -> None:
    """Both guards, shown rejecting what they exist to reject.

    A guard nobody has seen refuse anything is a guard that refuses nothing.
    """
    assert journey.ascending_under_c_collation(["fnd_A", "fnd_B", "fnd_C"])
    assert not journey.ascending_under_c_collation(["fnd_A", "fnd_C", "fnd_B"])
    assert not journey.ascending_under_c_collation(["fnd_B", "fnd_A"])
    assert not journey.ascending_under_c_collation(["fnd_A", "fnd_A"]), (
        "the listing's key is unique, so equal neighbours are a duplicate row, not a tie"
    )
    # COLLATE "C" is byte order, and the ULID alphabet is uppercase: a rewrite that
    # compared case-insensitively or in a locale collation would order these differently.
    assert journey.ascending_under_c_collation(["fnd_Z", "fnd_a"])
    assert not journey.ascending_under_c_collation(["fnd_a", "fnd_Z"])

    assert journey.non_descending_under_c_collation([("a", "1"), ("a", "2"), ("b", "1")])
    assert journey.non_descending_under_c_collation([("a", "1"), ("a", "1")]), (
        "the CSV repeats a finding once per evidence quote, so equal rows are expected"
    )
    assert not journey.non_descending_under_c_collation([("a", "2"), ("a", "1")])
    assert not journey.non_descending_under_c_collation([("b", "1"), ("a", "9")])


def test_the_document_order_rank_refuses_a_tie() -> None:
    """The content-determined token index is asserted total, and can say so."""
    def finding(page: int, start: int) -> dict[str, Any]:
        return {
            "finding_uid": f"fnd_{page}{start}",
            "observation": {"evidence": [{"page_number": page, "char_start": start}]},
        }

    ranked = journey.publication_order([finding(6, 20), finding(2, 90), finding(2, 10)])
    assert [item["finding_uid"] for item in ranked] == ["fnd_210", "fnd_290", "fnd_620"]

    with pytest.raises(AssertionError, match="no longer total"):
        journey.publication_order([finding(2, 10), finding(2, 10)])
    with pytest.raises(AssertionError, match="no evidence"):
        journey.publication_order(
            [{"finding_uid": "fnd_x", "observation": {"evidence": []}}]
        )
