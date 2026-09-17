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

RECORD_FILES = sorted(journey.RECORDS.glob("*.json"))

#: The frozen document's twelve operationIds, written out rather than read from the
#: contract: this suite's job is to notice a surface that changed, and an expectation
#: computed from a file the change could also touch would not.
TWELVE_OPERATIONS = (
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


def test_every_one_of_the_twelve_operations_is_covered() -> None:
    covered = set()
    for path in RECORD_FILES:
        operation = json.loads(path.read_text(encoding="utf-8"))["operation"]
        if operation is not None:
            covered.add(operation)
    assert covered == set(TWELVE_OPERATIONS), (
        f"operations with no record: {sorted(set(TWELVE_OPERATIONS) - covered)}; "
        f"records naming an operation the contract does not declare: "
        f"{sorted(covered - set(TWELVE_OPERATIONS))}"
    )


def test_exactly_one_record_is_marked_as_the_permitted_exception() -> None:
    """The D-7 path, and nothing else.

    A safety net with an unnamed exception is one somebody talks their way past at the
    end of a long wave. This is the assertion that makes the exception countable.
    """
    marked = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))["exception"]
        for path in RECORD_FILES
    }
    exceptions = {case: value for case, value in marked.items() if value}
    assert list(exceptions) == [
        "31-streamDocumentVersionContent.storage_credential_refused"
    ], f"the permitted-exception set is {sorted(exceptions)}"
    only = next(iter(exceptions.values()))
    assert only["debt"] == "D-7"
    assert "R-3" in only["ruling"]


def _authorization_claims(record: dict[str, Any]) -> list[str]:
    """Every way a record could start saying something about authorization.

    One function, used by the guard and by the test that proves the guard can fail, so
    the proof exercises the rule rather than a second copy of it that could drift.
    """
    found: list[str] = []
    if not record.get("pre_authorization"):
        found.append("no pre_authorization declaration")
    for name, _value in record["request"]["headers"]:
        if name.lower() in ("authorization", "proxy-authorization"):
            found.append(f"the request carries {name}")
    # 401 is unreachable before the dependency exists; a 403 in this corpus would have
    # to mean a caller's rights, and no case here exercises any.
    if record["response"]["status"] in (401, 403):
        found.append(f"pins {record['response']['status']}, an authorization answer")
    return found


def test_the_baseline_makes_no_authorization_claim() -> None:
    """The corpus must stay unreadable as an authorization expectation.

    `W13-SEAL` added the contract half of `T-6` at `a5f4001`: the document now declares a
    bearer scheme at its root and `401`/`403` on all twelve operations. The
    implementation half is stage 2's, so every request here is still unauthenticated and
    still answered -- and 33 records of exactly that is a thing a later reader can
    mistake for the surface's intended unauthenticated behaviour.

    `README.md` says the baseline has nothing to say about authorization. This is the
    test that keeps that sentence true instead of merely old.

    If stage 2 makes the journey authenticate, this test and that paragraph are changed
    together, deliberately -- which is the point of writing it down.
    """
    offenders: list[str] = []
    for path in RECORD_FILES:
        record = json.loads(path.read_text(encoding="utf-8"))
        offenders.extend(f"{path.stem}: {claim}" for claim in _authorization_claims(record))
    assert offenders == [], (
        "the baseline has started making an authorization claim:\n" + "\n".join(offenders)
    )


def test_the_no_authorization_claim_check_can_fail() -> None:
    """The same rule, run against three planted records.

    A guard nobody has seen reject anything accepts anything -- the rule this corpus
    already applies to itself in
    :func:`test_the_comparison_reddens_on_a_planted_difference`.

    The plants are in-memory copies rather than rewritten files, because a test that
    edits `records/` would trip the gate's changed-during-the-run check.
    """
    clean = json.loads(RECORD_FILES[0].read_text(encoding="utf-8"))
    assert _authorization_claims(clean) == [], "the unperturbed record is already reported"

    authenticated = json.loads(json.dumps(clean))
    authenticated["request"]["headers"].append(["Authorization", "Bearer w13-static"])
    assert _authorization_claims(authenticated) == ["the request carries Authorization"]

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
    )
    found = journey.differences(tampered, expected)
    assert any("Content-Length" in line for line in found), found
