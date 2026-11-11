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

W56a added two CSV severity columns after the historical seventeen. Record 12
remains unchanged; a digest-checked in-memory projection adds two empty v1
cells per data row before applying the original O1 byte comparison.

`CMP-C2-GATE-W13-01` keeps the historical JSON records unchanged too. A
digest-pinned in-memory projection accounts only for the current contract
version in sixteen error envelopes and the portal upload kind in four version
responses; it does not suppress any other byte, status or header difference.

`LANE-W13-STARTED-BY-01` keeps the records unchanged a third time, for two more additive
contract properties, each behind a digest of the historical bytes and each with a value the
journey's own records give (never one copied from the server): `RunStatus.started_by_user_uid`
and `started_by_label` (`R-151v`, contract 1.21.0) on the six records that carry a run, and
`DocumentVersion.tags` (`R-151e`, contract 1.23.0) on the two listings that carry it. The
starter is pinned, not normalised away: the uid is the journey's own account by token, the
label a literal, so a run started by anyone else reddens the comparison.

`LANE-W13-COST-01` (`D-322`) adds the cost path -- the refused unconsented `startRun` (02c) and `estimateRunCost`
(02d) -- as the first records added since the seal. 02c names its `contract_version` by the journey's own
`{{contract_version}}` token (read from the frozen contract, so it does not move with the next bump and a body naming
any other version reddens), and the census of version-bearing records is updated deliberately
(`_contract_version_census`). 02d is the contract-correct `RunCostEstimate`: the route emitted six optional properties as
`null` until the fix that followed this lane (it now drops them), so the record is compared with the served body as it is.
"""

from __future__ import annotations

import base64
import csv
import dataclasses
import hashlib
import importlib.util
import io
import json
import re
import sys
from functools import cache
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

# Record 12 is immutable wave-13 evidence. W56a appended two CSV columns; the
# comparison below projects only those empty v1 cells in memory. These literals
# are deliberately independent of the current serializer and seam document.
_HISTORICAL_CSV_HEADER = (
    b"project_uid,document_uid,version_uid,run_id,run_state,provider_mode,"
    b"finding_uid,finding_observation_id,category,finding_text,"
    b"recommendation_text,evidence_page,evidence_quote,current_verdict,"
    b"latest_comment,latest_decision_id,decision_recorded_at"
)
_HISTORICAL_CSV_SHA256 = (
    "b5c11af33e6e1886ebbdb9ffe2bd58e0149b1b6206beba3d05704ab371ba9422"
)
_APPENDED_CSV_HEADER = b",severity,severity_proposed"


def _csv_compat_expected(expected: dict[str, Any]) -> dict[str, Any]:
    """Project record 12's old bytes to the current, empty-severity v1 CSV.

    The pinned source body remains untouched. A fixed digest and shape checks
    keep this narrow exception from masking a changed legacy CSV cell.
    """
    if expected.get("case") != "12-exportRunCsv.success":
        raise ValueError("CSV compatibility applies only to record 12")
    body = expected["response"]["body"]
    if body.get("kind") != "base64":
        raise ValueError("record 12 must contain base64 CSV bytes")
    if body.get("length") != 4409:
        raise ValueError("record 12 pre-token CSV length changed")
    raw = base64.b64decode(body["base64"], validate=True)
    if hashlib.sha256(raw).hexdigest() != _HISTORICAL_CSV_SHA256:
        raise ValueError("record 12 historical CSV bytes changed")
    if not raw.startswith(b"\xef\xbb\xbf") or not raw.endswith(b"\r\n"):
        raise ValueError("record 12 lost its BOM or final CRLF")
    lines = raw[3:].split(b"\r\n")
    if len(lines) != 7 or lines[-1] != b"" or lines[0] != _HISTORICAL_CSV_HEADER:
        raise ValueError("record 12 is not its pinned header and five data rows")
    parsed = list(csv.reader(io.StringIO(raw[3:].decode("utf-8"), newline="")))
    if len(parsed) != 6 or any(len(row) != 17 for row in parsed):
        raise ValueError("record 12 is not a 17-column, five-row CSV")

    projected = (
        b"\xef\xbb\xbf"
        + lines[0]
        + _APPENDED_CSV_HEADER
        + b"\r\n"
        + b"\r\n".join(line + b",," for line in lines[1:-1])
        + b"\r\n"
    )
    out = json.loads(json.dumps(expected))
    out["response"]["body"]["base64"] = base64.b64encode(projected).decode("ascii")
    # The record's length describes the original body before token substitution.
    out["response"]["body"]["length"] += len(projected) - len(raw)
    return out


# The W13 records are historical evidence, so these exact files stay untouched. The
# current error-envelope version and portal version kind are additive surface changes.
# Pin the complete bytes of all twenty affected records before projecting either field.
# Two of the four portal records (32 and 33) are the listings, which also carry the
# document's `tags` since contract 1.23.0; the same pin covers that third projection.
_ERROR_VERSION_CASES = frozenset({
    "05b-createProject.idempotency_key_reuse",
    "17-uploadDocument.refusal.pdf_magic_bytes",
    "18-uploadDocument.refusal.byte_size",
    "19-uploadDocument.refusal.not_encrypted",
    "20-uploadDocument.refusal.page_count",
    "21-uploadDocument.refusal.every_page_has_extractable_text",
    "22-uploadDocument.refusal.max_bytes",
    "23-createProject.refusal.additionalProperties",
    "24-startRun.refusal.additionalProperties",
    "25-appendDecision.refusal.additionalProperties",
    "26-uploadDocument.refusal.additionalProperties",
    "27-createProject.refusal.idempotency_key_required",
    "28-dispatch.no_route",
    "29-dispatch.method_not_allowed",
    "30-getRunStatus.not_found",
    "31-streamDocumentVersionContent.storage_credential_refused",
})
_PORTAL_KIND_CASES = frozenset({
    "02-uploadDocument.success",
    "13-getDocumentVersion.success",
    "32-listDocuments.success",
    "33-listVersions.success",
})
_COMPAT_CASES = _ERROR_VERSION_CASES | _PORTAL_KIND_CASES

# `UI-PARITY-P0H` (`R-151e`, contract 1.23.0, migration 0053): `DocumentVersion.tags`, "the document's free tags, on the
# reads that carry them (`listDocuments`, `listVersions` and the document commands)". Records 32 and 33 are the two
# listings; `uploadDocument` and `getDocumentVersion` (records 02 and 13) do not carry it and do not move. The journey sets
# no tags -- `setDocumentTags` is not one of the operations this corpus covers
# (:data:`SEVENTEEN_OPERATIONS`, asserted whole by `test_every_one_of_the_seventeen_operations_is_covered`) -- so the
# document's set is empty, and the property is the last one of the version object, after `classification`.
_TAGS_CASES = frozenset({"32-listDocuments.success", "33-listVersions.success"})
_TAGS_BEFORE = '"revision": 1}}], "page": {"next_cursor": null}}'
_TAGS_AFTER = '"revision": 1}, "tags": []}], "page": {"next_cursor": null}}'
_COMPAT_RECORDS_SHA256 = "6518c1253e1d269585b71c7f68c398bc0f33812abad0ef974653336fe3b436fd"


@cache
def _compat_source_bodies() -> dict[str, str]:
    digest = hashlib.sha256()
    bodies: dict[str, str] = {}
    for case in sorted(_COMPAT_CASES):
        raw = (journey.RECORDS / f"{case}.json").read_bytes()
        digest.update(case.encode("utf-8") + b"\0" + raw + b"\0")
        record = json.loads(raw)
        assert record["case"] == case and record["response"]["body"]["kind"] == "text"
        bodies[case] = record["response"]["body"]["text"]
    assert digest.hexdigest() == _COMPAT_RECORDS_SHA256, (
        "the twenty historical W13 compatibility records changed; review them before projecting"
    )
    return bodies


@cache
def _current_contract_version() -> str:
    path = Path(__file__).resolve().parents[3] / "contracts/api/v1/openapi.json"
    version = json.loads(path.read_text(encoding="utf-8"))["info"]["version"]
    assert isinstance(version, str) and version != "1.0.0"
    return version


def _schema_compat_expected(expected: dict[str, Any]) -> dict[str, Any]:
    case = expected["case"]
    if case not in _COMPAT_CASES:
        return expected
    body = expected["response"]["body"]
    original = _compat_source_bodies()[case]
    assert body["kind"] == "text" and body["text"] == original, (
        f"{case}: compatibility received a changed historical body"
    )
    if case in _ERROR_VERSION_CASES:
        before = '"contract_version": "1.0.0"'
        after = f'"contract_version": "{_current_contract_version()}"'
        assert original.count(before) == 1 and json.loads(original)["contract_version"] == "1.0.0"
    else:
        before = ', "display_title":'
        after = ', "upload_kind": "portal_bundle", "display_title":'
        assert original.count(before) == 1 and '"upload_kind"' not in original
    projected = original.replace(before, after, 1)
    if case in _TAGS_CASES:
        assert original.count(_TAGS_BEFORE) == 1 and '"tags"' not in original
        projected = projected.replace(_TAGS_BEFORE, _TAGS_AFTER, 1)
    out = json.loads(json.dumps(expected))
    out["response"]["body"]["text"] = projected
    out["response"]["body"]["length"] += len(projected.encode("utf-8")) - len(original.encode("utf-8"))
    return out

# `UI-PARITY-P0B` (contract 1.19.0): every `listProjects` item also carries `audit_counts`, the project's documents by
# audit state. Record 16 stays as it was captured (`R-10`, `D-16`); the in-memory projection below adds the one property
# the contract added, with the value the journey's own earlier records give (see
# `test_the_audit_counts_of_record_16_follow_from_the_records_before_it`), and nothing else. The record's bytes are
# pinned, so a changed record is refused before it is projected.
_AUDIT_COUNTS_CASE = "16-listProjects.success"
_AUDIT_COUNTS_RECORD_SHA256 = "8e5bcc3240fe659516fdf8f96a98e88b29432494db1cc6defe2632750641c24d"
_AUDIT_COUNTS_BEFORE = '"document_count": 1}'
_AUDIT_COUNTS_AFTER = (
    '"document_count": 1, "audit_counts": {"document_count": 1, "not_run": 0, "clean": 0, '
    '"awaiting_decision": 1, "checked": 0, "partial": 0, "no_expert_decision": 1}}'
)


def _audit_counts_expected(expected: dict[str, Any], *, value: str = _AUDIT_COUNTS_AFTER) -> dict[str, Any]:
    if expected["case"] != _AUDIT_COUNTS_CASE:
        return expected
    raw = (journey.RECORDS / f"{_AUDIT_COUNTS_CASE}.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == _AUDIT_COUNTS_RECORD_SHA256, (
        "the historical record of listProjects changed; review it before projecting"
    )
    body = expected["response"]["body"]
    original = body["text"]
    assert body["kind"] == "text" and original == json.loads(raw)["response"]["body"]["text"], (
        f"{_AUDIT_COUNTS_CASE}: the projection received a changed historical body"
    )
    assert original.count(_AUDIT_COUNTS_BEFORE) == 1 and '"audit_counts"' not in original
    projected = original.replace(_AUDIT_COUNTS_BEFORE, value, 1)
    out = json.loads(json.dumps(expected))
    out["response"]["body"]["text"] = projected
    out["response"]["body"]["length"] += len(projected.encode("utf-8")) - len(original.encode("utf-8"))
    return out


# `UI-PARITY-P0F` (`R-151v`, contract 1.21.0, migration 0051): a `RunStatus` also carries `started_by_user_uid`, the account
# whose `startRun` created the run, and `started_by_label`, that account's display label (both optional in the contract,
# absent for a run created before the migration -- which no run of this journey is). The six records that carry a run
# (03-07 and the listing 34) stay as they were captured, and an in-memory projection appends the two properties at the end of
# the run object, where the model emits them, after the body text of each record has been pinned by digest.
#
# *Why the fields are pinned and not normalised away.* A run's starter is an assertion about who acted. Treating the two names
# like a timestamp (a declared field whose value is erased) would let a run attributed to the wrong account, or to none,
# reproduce the record. So the expectation names the starter exactly: the uid is `{{user_uid}}`, the token the journey gives
# the one account it provisions and presents on every request (`journey.declare_run_starter`), which the live body only matches
# if the run names that account; the label is the literal the same account carries as the `author_label` of records 10 and 11.
# `test_the_run_starter_of_the_run_records_follows_from_the_records_before_it` derives both from those earlier records.
_RUN_STARTER_USER_TOKEN = "{{user_uid}}"
_RUN_STARTER_LABEL = "Сьютова Е."
#: The contract's `UserUid` pattern is `^usr_[0-9A-HJKMNP-TV-Z]{26}$`: the thirty bytes a token stands for in the raw body.
_USER_UID_LENGTH = len("usr_") + 26
#: SHA-256 of each historical record's body text (`response.body.text`, utf-8). 04-07 share a digest: two replays and two reads
#: of one finished run, the claim records 04 and 05 make. Taken from the committed files at `ce08af3d`.
_RUN_STARTER_BODIES_SHA256 = {
    "03-startRun.success": "5fb0c261a28e83c313496b0a1615a282654d044f8055494e5b22eddf73ada3fa",
    "04-startRun.replay": "f314e8f8df1b22cb09c2416bd7583b1f1e543cef329ec4c578556bb0636c0cbc",
    "05-startRun.replay_with_normalised_property": (
        "f314e8f8df1b22cb09c2416bd7583b1f1e543cef329ec4c578556bb0636c0cbc"
    ),
    "06-getRunStatus.success": "f314e8f8df1b22cb09c2416bd7583b1f1e543cef329ec4c578556bb0636c0cbc",
    "07-getRunStatus.correlation_supplied": "f314e8f8df1b22cb09c2416bd7583b1f1e543cef329ec4c578556bb0636c0cbc",
    "34-listRuns.success": "3a347f456138c9737a09526bf885a31d9f8673fda19e1f9ea4fa088c116c353a",
}
#: Where the run object ends in each body: (its last property as the record spells it, what follows it). The accepted run of
#: record 03 has no `terminal_at`; the finished runs end with it; record 34 wraps the one run in its page envelope.
_RUN_STARTER_ENDS = {
    "03-startRun.success": ('"diagnostic_observation_count": 0', "}"),
    "04-startRun.replay": ('"terminal_at": "{{ts_14}}"', "}"),
    "05-startRun.replay_with_normalised_property": ('"terminal_at": "{{ts_14}}"', "}"),
    "06-getRunStatus.success": ('"terminal_at": "{{ts_14}}"', "}"),
    "07-getRunStatus.correlation_supplied": ('"terminal_at": "{{ts_14}}"', "}"),
    "34-listRuns.success": ('"terminal_at": "{{ts_14}}"', '}], "page": {"next_cursor": null}}'),
}


def _run_starter_expected(
    expected: dict[str, Any],
    *,
    uid: str = _RUN_STARTER_USER_TOKEN,
    label: str = _RUN_STARTER_LABEL,
) -> dict[str, Any]:
    case = expected["case"]
    if case not in _RUN_STARTER_BODIES_SHA256:
        return expected
    body = expected["response"]["body"]
    original = body["text"]
    historical = json.loads((journey.RECORDS / f"{case}.json").read_text(encoding="utf-8"))["response"]["body"]["text"]
    assert body["kind"] == "text" and original == historical, (
        f"{case}: the run-starter projection received a changed historical body"
    )
    assert hashlib.sha256(historical.encode("utf-8")).hexdigest() == _RUN_STARTER_BODIES_SHA256[case], (
        f"the historical record of {case} changed; review it before projecting the run starter"
    )
    last_property, closing = _RUN_STARTER_ENDS[case]
    assert original.endswith(last_property + closing) and '"started_by_' not in original
    appended = f', "started_by_user_uid": "{uid}", "started_by_label": "{label}"'
    projected = original[: -len(closing)] + appended + closing
    out = json.loads(json.dumps(expected))
    out["response"]["body"]["text"] = projected
    # The record's length is of the raw body, before tokens: the token stands for a thirty-byte uid.
    raw_appended = appended.replace(_RUN_STARTER_USER_TOKEN, "u" * _USER_UID_LENGTH)
    out["response"]["body"]["length"] += len(raw_appended.encode("utf-8"))
    return out


# `LANE-W13-COST-01` (`D-322`): the cost estimate, record 02d. Its six optional properties (`connection_revision_id`,
# `preset_revision_id`, `executor_group_id`, `executor_group_revision_id`, `routing_rule_revision_id`, `pin_id`) are not
# nullable; the route rendered them as `null` until it dropped them, and the record was always the contract-correct form.
_ESTIMATE_CASE = "02d-estimateRunCost.success"
_ESTIMATE_OPTIONAL_PROPERTIES = (
    "connection_revision_id", "preset_revision_id", "executor_group_id", "executor_group_revision_id",
    "routing_rule_revision_id", "pin_id",
)


def _projected(expected: dict[str, Any]) -> dict[str, Any]:
    """A record as the comparison expects it: every digest-pinned in-memory projection, in the order the suite applies them."""
    if expected["case"] == "12-exportRunCsv.success":
        expected = _csv_compat_expected(expected)
    expected = _schema_compat_expected(expected)
    expected = _audit_counts_expected(expected)
    return _run_starter_expected(expected)


#: The operationIds this corpus covers, written out rather than read from the contract:
#: this suite's job is to notice a surface that changed, and an expectation computed from a
#: file the change could also touch would not.
#:
#: **`W18-SEAL` moved it from twelve to fifteen** under owner ruling `R-5`. Adding an
#: operation adds a case and a record; it is not a permitted *change* to any record and
#: carries no exception block. What changed here is the count, not the rule: every one of
#: the fifteen still has to be covered by at least one record.
#:
#: **`W59-SEAL-FOLLOWUP-01` moved it from fifteen to sixteen** with case 02b,
#: ``classifyDocumentVersion``: since `W59-SECTION-SEAL-01` (`R-139`) ``startRun`` refuses
#: a version no expert has classified, so the journey cannot reach case 03 without it. The
#: rule is W18-SEAL's: a new case and a new record, no exception block. The served surface
#: has more operations than these sixteen; the list is what this corpus records, and the
#: assertion is that every one of them is covered and nothing else is named.
#:
#: **`LANE-W13-COST-01` (`D-322`) moved it from sixteen to seventeen** with case 02d,
#: ``estimateRunCost``: the price the person confirms before ``startRun`` may spend
#: (`BETA-COST-PREFLIGHT-1030`). The rule is W18-SEAL's again: a new case and a new record, no exception block.
SEVENTEEN_OPERATIONS = (
    "appendDecision",
    "classifyDocumentVersion",
    "createProject",
    "estimateRunCost",
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


def test_every_one_of_the_seventeen_operations_is_covered() -> None:
    covered = set()
    for path in RECORD_FILES:
        operation = json.loads(path.read_text(encoding="utf-8"))["operation"]
        if operation is not None:
            covered.add(operation)
    assert covered == set(SEVENTEEN_OPERATIONS), (
        f"operations with no record: {sorted(set(SEVENTEEN_OPERATIONS) - covered)}; "
        f"records naming an operation the contract does not declare: "
        f"{sorted(covered - set(SEVENTEEN_OPERATIONS))}"
    )


#: The four non-terminal ``RunState`` values, written out rather than imported from the
#: contract or from ``auditmanager``: this file's job is to notice a surface that moved,
#: and an expectation read from something the change could also touch would not.
NON_TERMINAL_RUN_STATES = ("created", "queued", "running", "validating")

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
#:
#: **`W20-EXEC` added no entry and lengthened one.** `D-20` moved record 03 and no other:
#: `startRun` no longer executes the run, so its `202` carries the accepted state instead
#: of the terminal one. The count of marked records is **still seven**, which is the
#: assertion below, and record 03's tuple is now three debts long -- a record moved by a
#: third debt has to name a third. Records 04 and 05 are `startRun` replays and are
#: **not** marked by `D-20`: the journey waits for the run to finish before replaying, so
#: those bodies are the published shape they have always been. Three records that moved
#: together twice not moving together a third time is the reason `debt` is a list and the
#: reason this map is written out case by case.
#: **`W41-AUTHOR` added the eighth and ninth entries**, records 10 and 11, under `D-78`.
#: They are one change seen twice: ``author_label`` was the constant ``"local-reviewer"``
#: -- one string for every verdict by every reviewer -- and is now the verified reviewer's
#: **display label** (`R-37`, which replaced `D-78`'s login with the name other reviewers
#: read). **Neither record's bytes moved for `R-37`**, because ``w13-baseline`` has chosen
#: no display name and the label therefore falls back to its login -- which is what these
#: records already pinned. Their exception blocks say so; the distinction a record that did
#: not move cannot make is asserted in
#: ``tests/integration/api/test_decision_authorship.py`` instead. Record 10 is the ``appendDecision`` response
#: that writes the event; record 11 renders the same event back through
#: ``listDecisionHistory``. Two entries and not one, because a record moved is a record
#: named, and "the decision records" is not a countable thing.
#:
#: They cite **no ruling**, on `D-20`'s reading: nothing in ``contracts/**`` moved, no
#: property was added to any schema, and ``DecisionEvent.author_label`` is declared by the
#: seal with the same type and the same bounds. What moved is the value the server writes
#: into a field it has always written. The frozen document's *description* of that field
#: still calls it "one configured local reviewer label" and is now wrong; correcting it is
#: a reseal and the owner's, and `W41-AUTHOR` reported it rather than doing it.
#:
#: **`W49-SEAL-01` moved records 10 and 11 for the first time since `D-78`**, and by one
#: value: the account this journey provisions is now a complete ``expert`` account, so the
#: label it records is the name form ``Сьютова Е.`` instead of the login ``w13-baseline``
#: it fell back to. The debt is still `D-78`'s subject -- who a decision is attributed to --
#: and the two entries below did not change; what changed is each block's cited decision
#: (`2894951`) and its `permitted_change`, and
#: :func:`test_the_two_author_records_moved_by_the_label_and_nothing_else` asserts the move
#: is that label and nothing else.
#:
#: **`W59-SEAL-FOLLOWUP-01` added the tenth, eleventh and twelfth entries**, records 13, 32
#: and 33, under `D-181`. They are one change seen three times. Since `W59-SECTION-SEAL-01`
#: (`bd08e03c`, `R-139`), ``startRun`` refuses an unclassified version, so case 02b now
#: classifies the journey's version. Every read that returns a ``DocumentVersion`` projects
#: the stored classification, and these are the three records that read the version after
#: case 02b. Each body moved by one appended property, ``classification``, and nothing else,
#: and :func:`test_the_three_version_records_moved_by_the_classification_and_nothing_else`
#: asserts that by digest against the bodies as they stood at ``77aa55bd``.
#:
#: **The `W59-SEAL-FOLLOWUP-01` follow-up (finding F-1) lengthened four entries and added a
#: thirteenth**, at the integrator's instruction. Records 04-07 and 34 stopped reproducing
#: in the same measurement for a reason unrelated to the classification: `56efead4`
#: (`W57A-SEAL-01B`) moved the ``text_analysis`` ``stage_version`` to ``1.1.0``, and no run
#: of this corpus had read a finished run since. Each body moved by that one value.
#: :func:`test_the_five_run_records_moved_by_the_text_stage_version_and_nothing_else`
#: asserts it by digest. The debt named is `D-181`, the register row whose resolution this
#: performs; no row names the drift itself, and the blocks say so. Record 03 is an accepted
#: run with no stages and does not move.
PERMITTED_EXCEPTIONS = {
    "02b-classifyDocumentVersion.success": ("D-182",),
    "03-startRun.success": ("D-19", "D-21", "D-20"),
    "04-startRun.replay": ("D-19", "D-21", "D-181"),
    "05-startRun.replay_with_normalised_property": ("D-19", "D-21", "D-181"),
    "06-getRunStatus.success": ("D-19", "D-21", "D-181"),
    "07-getRunStatus.correlation_supplied": ("D-19", "D-21", "D-181"),
    "10-appendDecision.success": ("D-78",),
    "11-listDecisionHistory.success": ("D-78",),
    "13-getDocumentVersion.success": ("D-181", "D-182"),
    "16-listProjects.success": ("D-16",),
    "31-streamDocumentVersionContent.storage_credential_refused": ("D-7",),
    "32-listDocuments.success": ("D-181", "D-182"),
    "33-listVersions.success": ("D-181", "D-182"),
    "34-listRuns.success": ("D-181",),
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

    `D-20` is record 03 alone, and it needs no ruling at all: `startRun` stopped executing
    the run it accepts, so its `202` reports `queued` -- a state the frozen `RunState`
    enum has always declared and the frozen `audit_run` machine has always had an edge to
    -- instead of the terminal the inline executor had already reached. No property was
    added, so neither R-5's nor R-10's kind of authority is engaged.

    `D-78` is records 10 and 11, and needs no ruling for `D-20`'s reason: `author_label`
    is declared by the seal and has always been written, and what changed is the value the
    server puts in it -- the reviewer the seam verified, instead of one constant for every
    reviewer. The two records are the same event written and then read back.

    `R-37` then changed that value again, from the reviewer's login to their display label,
    and **moved neither record**: this journey's account has chosen no display name, so the
    label falls back to the login these records already pin. The exception blocks were
    amended rather than the records re-captured, because nothing about the bytes is
    different and a re-capture would have recorded that fact as a change.

    `W49-SEAL-01` then **did** move both, by the label alone: the journey's account became a
    complete profile, whose name form outranks its login (`R-55`). The blocks cite that
    decision and the move is asserted by digest in
    ``test_the_two_author_records_moved_by_the_label_and_nothing_else``.

    `D-181` is records 13, 32 and 33: the classification case 02b makes, projected onto
    every ``DocumentVersion`` read of that version (`W59-SECTION-SEAL-01`, under `R-139`,
    whose contract commit declared the property). The move is asserted by digest in
    ``test_the_three_version_records_moved_by_the_classification_and_nothing_else``.

    `D-181` is also the third debt of records 04-07 and the only one of record 34: the
    ``text_analysis`` ``stage_version`` `56efead4` moved to ``1.1.0``, first measured when
    `W59-SEAL-FOLLOWUP-01` brought the journey past case 03 again. Asserted by digest in
    ``test_the_five_run_records_moved_by_the_text_stage_version_and_nothing_else``.
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
    # And the three `D-181` records of the classification cite the window that froze the
    # seal that declared and filled `DocumentVersion.classification`; the five of the stage
    # version cite the commit that moved it.
    for case in _PRE_CLASSIFICATION_VERSION_BODIES:
        assert "R-139" in exceptions[case]["ruling"], case
    for case in _PRE_TEXT_STAGE_VERSION_BODIES:
        assert exceptions[case]["decided_by"] == "56efead4", case


#: `W49-SEAL-01`. The SHA-256 of records 10 and 11's body text as captured before the seal
#: (`7912504`), when the label was the login ``w13-baseline``. Read from the record files at
#: that commit, never from the files now: an expectation computed from the files it checks
#: could not report that something besides the label moved.
_PRE_SEAL_AUTHOR_BODIES = {
    "10-appendDecision.success": (
        "ec1ada99cfea1cc92697bf7d4687b150cf491e196a040c6dc22008c5ddc77172"
    ),
    "11-listDecisionHistory.success": (
        "b269ac56a19d2e9b90cc7f209c114704b588a88c2789aa935fa42f4200c28231"
    ),
}


def test_the_two_author_records_moved_by_the_label_and_nothing_else() -> None:
    """The re-capture asserted, not merely made: substitute the old label back and the
    bytes are the previous capture's, digest for digest.

    `MEMORY: characterization can freeze a defect` is why a re-capture is not evidence by
    itself -- a record rewritten wholesale would pin whatever the server said. This pins the
    *difference*: one value, the name form a complete profile records (`R-55`).
    """
    import hashlib

    for case, digest in _PRE_SEAL_AUTHOR_BODIES.items():
        record = json.loads((journey.RECORDS / f"{case}.json").read_text(encoding="utf-8"))
        text = record["response"]["body"]["text"]
        assert text.count('"author_label": "Сьютова Е."') == 1, case
        restored = text.replace('"author_label": "Сьютова Е."', '"author_label": "w13-baseline"')
        assert hashlib.sha256(restored.encode("utf-8")).hexdigest() == digest, (
            f"{case} moved by more than its author label"
        )
        assert "W49-SEAL-01" in record["exception"]["permitted_change"], case


#: `W59-SEAL-FOLLOWUP-01`. The SHA-256 of records 13, 32 and 33's body text as committed at
#: ``77aa55bd``, before case 02b classified the version. Read from the record files at that
#: commit (``git show 77aa55bd:<record>``), never from the files now: an expectation computed
#: from the files it checks could not report that something besides the classification moved.
#: 32 and 33 share a digest because their pages were already byte-identical: one row, the same
#: version, and an exhausted cursor.
_PRE_CLASSIFICATION_VERSION_BODIES = {
    "13-getDocumentVersion.success": (
        "57e3a695ec6c4e86166d7f16683a7a90f38a9cc6f65f7b2b74b3bdea9e389b6a"
    ),
    "32-listDocuments.success": (
        "fdbbe47e3c437cffd126b0721d7b5d8b71cfd35e23312d2ffc7c811a7ed41edf"
    ),
    "33-listVersions.success": (
        "fdbbe47e3c437cffd126b0721d7b5d8b71cfd35e23312d2ffc7c811a7ed41edf"
    ),
}

#: The one property each of the three bodies gained, exactly as a tokenised record spells it:
#: the classification case 02b asked for (stage ``P``, section ``KJ`` since
#: `PROD-11-AR-V1-V2-REMOVAL-01`, ``AR`` before), the version and the
#: confirmer by exact value, ``confirmed_at`` under its declared timestamp name and, since
#: `CLASSIFICATION-CORRECTION-01`, the ``revision`` (``1``: the original confirmation). It is
#: written out here and is not read from the journey or from case 02b's record.
_APPENDED_CLASSIFICATION = (
    ', "classification": {"version_uid": "{{version_uid}}", "project_stage": "P", '
    '"section_code": "KJ", "confirmed_by_user_uid": "{{user_uid}}", "confirmed_at": '
    '"{{ts_6}}", "revision": 1}'
)


def test_the_three_version_records_moved_by_the_classification_and_nothing_else() -> None:
    """The re-capture is asserted rather than just made. Take the appended classification
    out and each body is the previous capture's again, digest for digest.

    `W49-SEAL-01`'s method, and for its reason: a record rewritten wholesale pins whatever
    the server said. What this pins is the *difference*. It is one property appended where
    ``document_version_body`` emits it, after ``display_title``, and it must sit at the end
    of the version object, never somewhere inside it.
    """
    for case, digest in _PRE_CLASSIFICATION_VERSION_BODIES.items():
        record = json.loads((journey.RECORDS / f"{case}.json").read_text(encoding="utf-8"))
        text = record["response"]["body"]["text"]
        assert text.count(_APPENDED_CLASSIFICATION) == 1, case
        assert f'"display_title": "AR baseline"{_APPENDED_CLASSIFICATION}}}' in text, (
            f"{case}: the classification is not the last property of the version"
        )
        restored = text.replace(_APPENDED_CLASSIFICATION, "")
        assert hashlib.sha256(restored.encode("utf-8")).hexdigest() == digest, (
            f"{case} moved by more than its appended classification"
        )
        assert record["exception"]["debt"] == ["D-181", "D-182"], case
        assert "W59-SEAL-FOLLOWUP-01" in record["exception"]["permitted_change"], case
        for token in ("{{ts_6}}", "{{user_uid}}"):
            assert token in record["tokens"], (case, token)


#: `CLASSIFICATION-CORRECTION-01`. The SHA-256 of the four classification-bearing records' body
#: text as committed before the classification gained its ``revision`` (``git show
#: 4d5ae509:<record>``'s ``response.body.text``, i.e. the lane's tip before this move), never
#: read from the files now: an expectation computed from the files it checks could not report
#: that something besides the ``revision`` moved. 32 and 33 share a digest for the reason the
#: pre-classification ones do.
_PRE_REVISION_BODIES = {
    "02b-classifyDocumentVersion.success": (
        "297ce59b12330e1464511409789aed47acb408ba3b44ec0287514349eb666f9f"
    ),
    "13-getDocumentVersion.success": (
        "293c4564911d5d17cdb4e3b011f9bcd3788593c0bb2efebd81b72ed6ff89f3f5"
    ),
    "32-listDocuments.success": (
        "6bf20cc177c7f898852c9d3bf8e8d6b04aca39dfacdbdb37e297f90f84708497"
    ),
    "33-listVersions.success": (
        "6bf20cc177c7f898852c9d3bf8e8d6b04aca39dfacdbdb37e297f90f84708497"
    ),
}


def test_the_four_classification_records_moved_by_the_revision_and_nothing_else() -> None:
    """Take the one appended property out and each body is the previous capture's again.

    The method of the two digest tests above, and for their reason: a re-capture pins whatever
    the server said, so what is pinned is the *difference* -- ``, "revision": 1`` appended to
    the ``classification`` object, after ``confirmed_at``, where the model emits it last.
    """
    appended = ', "revision": 1'
    for case, digest in _PRE_REVISION_BODIES.items():
        record = json.loads((journey.RECORDS / f"{case}.json").read_text(encoding="utf-8"))
        text = record["response"]["body"]["text"]
        assert text.count(appended) == 1, case
        stamp = "{{ts_5}}" if case.startswith("02b") else "{{ts_6}}"
        assert '"confirmed_at": "' + stamp + '"' + appended + "}" in text, (
            f"{case}: the revision is not the last property of the classification"
        )
        # The digests are of the captures of `CLASSIFICATION-CORRECTION-01`, when the section was
        # AR; the section move is pinned by the test below, and undone here first.
        restored = text.replace(appended, "").replace('"section_code": "KJ"', '"section_code": "AR"')
        assert hashlib.sha256(restored.encode("utf-8")).hexdigest() == digest, (
            f"{case} moved by more than its revision"
        )
        assert "D-182" in record["exception"]["debt"], case
        assert "CLASSIFICATION-CORRECTION-01" in record["exception"]["permitted_change"], case
        assert record["exception"]["decided_by"] in ("f290f7b7", "bd08e03c"), case


#: `PROD-11-AR-V1-V2-REMOVAL-01`. The SHA-256 of the four classification-bearing records' body text
#: as committed at ``1c8d29fa``, the base of the task, when the journey's version was classified
#: ``AR``. Read from the record files at that commit (``git show 1c8d29fa:<record>``), never from the
#: files now. 32 and 33 share a digest for the reason the earlier ones do.
_PRE_SECTION_MOVE_BODIES = {
    "02b-classifyDocumentVersion.success": (
        "80ac0b36d4a1b056fe0a605eb619d395dee91233d18bf110c759a1adec7319f8"
    ),
    "13-getDocumentVersion.success": (
        "774f3761334e20ab346e59d35139ccd2c0e60d8bcf1bb0d1402414d7b1c5216d"
    ),
    "32-listDocuments.success": (
        "9a592cd68f0d175cbc83747cf95d2ce2320385c538293ac8054827d923da8a5b"
    ),
    "33-listVersions.success": (
        "9a592cd68f0d175cbc83747cf95d2ce2320385c538293ac8054827d923da8a5b"
    ),
}


def test_the_four_classification_records_moved_by_the_section_and_nothing_else() -> None:
    """Put `AR` back where the one section code is and each body is the base capture's again.

    `PROD-11-AR-V1-V2-REMOVAL-01` made the served `startRun` refuse a version classified `AR`, so the
    journey's version is classified `KJ` and the v1 reference profile is registered under `KJ`
    for this journey (``journey.build_apps``). It stays `KJ` after `HOTFIX-AR-ORIGINAL-PROFILE-INT-20261030`
    gave `AR` a text profile again: that profile has no synthetic recording to replay.
    What is pinned is the *difference*: one
    ``"section_code": "KJ"`` per body, where ``"AR"`` was, and no other byte. Every run record is
    unchanged, so none of them is marked.
    """
    for case, digest in _PRE_SECTION_MOVE_BODIES.items():
        record = json.loads((journey.RECORDS / f"{case}.json").read_text(encoding="utf-8"))
        text = record["response"]["body"]["text"]
        assert text.count('"section_code": "KJ"') == 1, case
        assert '"section_code": "AR"' not in text, case
        restored = text.replace('"section_code": "KJ"', '"section_code": "AR"')
        assert hashlib.sha256(restored.encode("utf-8")).hexdigest() == digest, (
            f"{case} moved by more than its section code"
        )
        assert "PROD-11-AR-V1-V2-REMOVAL-01" in record["exception"]["permitted_change"], case


#: `W59-SEAL-FOLLOWUP-01`, finding F-1. The SHA-256 of records 04-07 and 34's body text as
#: committed at ``77aa55bd`` (unchanged there since long before `56efead4`), read with
#: ``git show 77aa55bd:<record>`` and never from the files now. 04-07 share a digest: two
#: replays and two reads of the same finished run, which is the claim records 04 and 05 make.
_PRE_TEXT_STAGE_VERSION_BODIES = {
    "04-startRun.replay": (
        "5ce9a0f515ba8bb2c12ef486039dd2d4d6c00aacd32a36a915476764eadfa204"
    ),
    "05-startRun.replay_with_normalised_property": (
        "5ce9a0f515ba8bb2c12ef486039dd2d4d6c00aacd32a36a915476764eadfa204"
    ),
    "06-getRunStatus.success": (
        "5ce9a0f515ba8bb2c12ef486039dd2d4d6c00aacd32a36a915476764eadfa204"
    ),
    "07-getRunStatus.correlation_supplied": (
        "5ce9a0f515ba8bb2c12ef486039dd2d4d6c00aacd32a36a915476764eadfa204"
    ),
    "34-listRuns.success": (
        "046762b234806df848eb1f0bcb4a3e268023a84a275e85b8a0a52b248e8dbd94"
    ),
}

#: The one stage whose version moved, as a record spells it before and after. Written out;
#: not read from ``analysis/text/stage.py`` or from the stage registry.
_TEXT_STAGE_BEFORE = '"stage_id": "text_analysis", "status": "succeeded", "stage_version": "1.0.0"'
_TEXT_STAGE_AFTER = '"stage_id": "text_analysis", "status": "succeeded", "stage_version": "1.1.0"'


def test_the_five_run_records_moved_by_the_text_stage_version_and_nothing_else() -> None:
    """Restore ``1.0.0`` in the one ``text_analysis`` stage and each body is the
    ``77aa55bd`` capture again, digest for digest.

    The other three stages each still say ``1.0.0`` -- a re-capture that had moved one of
    them, or a second ``text_analysis`` entry, fails the count or the digest.
    """
    for case, digest in _PRE_TEXT_STAGE_VERSION_BODIES.items():
        record = json.loads((journey.RECORDS / f"{case}.json").read_text(encoding="utf-8"))
        text = record["response"]["body"]["text"]
        assert text.count(_TEXT_STAGE_AFTER) == 1, case
        assert _TEXT_STAGE_BEFORE not in text, case
        assert text.count('"stage_version": "1.0.0"') == 3, f"{case}: another stage moved"
        restored = text.replace(_TEXT_STAGE_AFTER, _TEXT_STAGE_BEFORE)
        assert hashlib.sha256(restored.encode("utf-8")).hexdigest() == digest, (
            f"{case} moved by more than the text stage's version"
        )
        assert record["exception"]["debt"][-1] == "D-181", case
        assert record["exception"]["decided_by"] == "56efead4", case
        assert "W59-SEAL-FOLLOWUP-01" in record["exception"]["permitted_change"], case


#: The four `RunStatus` records that report a **finished** run. Record 03 was the fifth
#: until `D-20`; see the test below for why it is now asserted separately and not dropped.
FINISHED_RUN_RECORDS = (
    "04-startRun.replay",
    "05-startRun.replay_with_normalised_property",
    "06-getRunStatus.success",
    "07-getRunStatus.correlation_supplied",
)


def _recorded_body(case: str) -> dict[str, Any]:
    """One record's response body, parsed.

    The tokens sit inside the body's own quoting, so the recorded text parses as JSON as
    it stands: `created_at` reads back as the string `{{ts_9}}`, and two fields sharing
    one instant read back as the *same* token.
    """
    record = json.loads((journey.RECORDS / f"{case}.json").read_text(encoding="utf-8"))
    return json.loads(record["response"]["body"]["text"])  # type: ignore[no-any-return]


def test_the_run_status_records_no_longer_pin_one_instant_for_the_whole_run() -> None:
    """The defect this corpus had frozen, asserted against the records themselves.

    `W15RUN-5` was readable in this directory before it was found in a browser: a run
    that took eleven seconds recorded the same token for the instant it was created and
    the instant it terminated. Re-capturing alone would have erased that without anyone
    having to say it had been there, so it is asserted here rather than left to a diff.

    **`W20-EXEC` narrowed the set and did not shrink the claim.** `D-20` made record 03 a
    record of an *accepted* run, which has no terminal instant to disagree with its
    creation -- so the assertion below cannot be made of it, and the next test makes the
    stronger one instead. Four records still carry a finished run and still have to show
    two different instants and per-stage timings.
    """
    for case in FINISHED_RUN_RECORDS:
        body = _recorded_body(case)
        assert body["created_at"] != body["terminal_at"], (
            f"{case} pins the same value for created_at and terminal_at, which is the "
            "D-19 defect recorded as the expectation"
        )
        assert body["stages"], f"{case} records a finished run with no stages"
        for stage in body["stages"]:
            assert "started_at" in stage and "finished_at" in stage, (case, stage)


def test_the_start_run_record_pins_an_accepted_run_and_not_a_finished_one() -> None:
    """`D-20`, asserted on the record rather than left to a diff.

    The reason this is a test and not a recapture: a corpus that simply took whatever
    `startRun` answered would go green again the day somebody put `execute_run` back on
    the request thread, and the only evidence would be a body that got longer. This states
    what the record must show -- a declared non-terminal state, nothing a run can only
    have after it has run -- so that reversal is a red test and not a quiet diff.

    Every absent property is one the frozen `RunStatus` declares as optional and
    `run_status_body` has always omitted when there is nothing to report. Nothing here
    asks for a property the contract does not declare, which is the other half of why
    `D-20` engaged no reseal.
    """
    body = _recorded_body("03-startRun.success")
    assert body["state"] in NON_TERMINAL_RUN_STATES, (
        f"startRun pins {body['state']!r}; a 202 that already carries a terminal is the "
        "whole of D-20 and means execution went back on the request thread"
    )
    assert body["state"] == "queued", body["state"]
    assert body["stages"] == [], "an accepted run reports stages it has not run"
    for absent in ("terminal_at", "terminal_reason", "cost_micros", "cost_basis",
                   "model_call_count"):
        assert absent not in body, (
            f"the accepted run reports {absent!r}, which only a run that has executed has"
        )
    # The identity and the frozen configuration are there from the first instant, because
    # they are what `startRun` established. A 202 a caller cannot address is `D-5`.
    for present in ("run_id", "project_uid", "version_uid", "provider_mode", "created_at",
                    "analysis_profile_id", "prompt_bundle_id", "degradation_set"):
        assert present in body, f"the accepted run does not report {present!r}"


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
    expected = _projected(json.loads(path.read_text(encoding="utf-8")))
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


@pytest.mark.parametrize("case", [
    "05b-createProject.idempotency_key_reuse",
    "02-uploadDocument.success",
])
def test_schema_compat_still_reddens_on_a_wrong_live_field(
    case: str, exchanges: dict[str, Any]
) -> None:
    record = json.loads((journey.RECORDS / f"{case}.json").read_text(encoding="utf-8"))
    expected = _schema_compat_expected(record)
    assert journey.differences(exchanges[case], expected) == []
    wrong = json.loads(json.dumps(expected))
    if case in _ERROR_VERSION_CASES:
        before = f'"contract_version": "{_current_contract_version()}"'
        after = '"contract_version": "0.0.0"'
    else:
        before = '"upload_kind": "portal_bundle"'
        after = '"upload_kind": "comparison_only"'
    assert wrong["response"]["body"]["text"].count(before) == 1
    wrong["response"]["body"]["text"] = wrong["response"]["body"]["text"].replace(
        before, after, 1
    )
    assert any("body:" in difference for difference in journey.differences(exchanges[case], wrong))


def test_the_audit_counts_of_record_16_follow_from_the_records_before_it() -> None:
    """The projected value is not copied from the server: it is what the journey's own earlier records say.

    By record 16 the project holds one document whose current version has a published run (record 06: state
    `published`, no degradation) with three findings, all pending when read (record 08), and the journey accepted one
    of them (record 10). A result run with an undecided finding is `awaiting_decision` (`R-150n` ... `R-150u`): one
    document, awaiting, `no_expert_decision` the same one. A projection that said `checked` or `clean` would be the
    frozen defect `characterization-can-freeze-a-defect` warns about, and fails here.
    """
    def load(case: str) -> dict[str, Any]:
        return json.loads((journey.RECORDS / f"{case}.json").read_text(encoding="utf-8"))

    run = json.loads(load("06-getRunStatus.success")["response"]["body"]["text"])
    findings = json.loads(load("08-listRunFindings.success")["response"]["body"]["text"])["items"]
    decision = json.loads(load("10-appendDecision.success")["response"]["body"]["text"])
    assert run["state"] == "published" and run["degradation_set"] == []
    assert len(findings) == 3 and {item["current_verdict"] for item in findings} == {"pending"}
    assert decision["current_verdict"] == "accepted"
    undecided = len(findings) - 1
    assert undecided >= 1, "every finding decided would make the document `checked`, and the projection wrong"
    text = _audit_counts_expected(load(_AUDIT_COUNTS_CASE))["response"]["body"]["text"]
    projected = json.loads(text)["items"][0]["audit_counts"]
    assert projected == {
        "document_count": 1, "not_run": 0, "clean": 0, "awaiting_decision": 1,
        "checked": 0, "partial": 0, "no_expert_decision": 1,
    }


def test_the_audit_counts_projection_reddens_on_a_wrong_value_and_refuses_a_changed_record(
    exchanges: dict[str, Any]
) -> None:
    """The comparison can fail: the right projection reproduces the live body, a wrong value is reported, and a
    record whose bytes are not the pinned ones is refused before it is projected."""
    record = json.loads((journey.RECORDS / f"{_AUDIT_COUNTS_CASE}.json").read_text(encoding="utf-8"))
    right = _audit_counts_expected(record)
    assert journey.differences(exchanges[_AUDIT_COUNTS_CASE], right) == []
    wrong = _audit_counts_expected(
        record, value=_AUDIT_COUNTS_AFTER.replace('"checked": 0', '"checked": 1').replace('"awaiting_decision": 1', '"awaiting_decision": 0')
    )
    assert any("body:" in difference for difference in journey.differences(exchanges[_AUDIT_COUNTS_CASE], wrong))
    changed = json.loads(json.dumps(record))
    changed["response"]["body"]["text"] += " "
    with pytest.raises(AssertionError, match="changed historical"):
        _audit_counts_expected(changed)


def _historical(case: str) -> dict[str, Any]:
    return json.loads((journey.RECORDS / f"{case}.json").read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _starter_of(case: str, text: str) -> dict[str, Any]:
    """The one run object of a projected body: record 34 wraps it in its page."""
    parsed = json.loads(text)
    return parsed["items"][0] if case.startswith("34") else parsed  # type: ignore[no-any-return]


def test_the_run_starter_of_the_run_records_follows_from_the_records_before_it() -> None:
    """The projected starter is what the journey's own earlier records say, not what the server said.

    The journey provisions one account and presents it on every request (`journey.presented_account_uid`), so the account
    that started the run is the account that confirmed the version's classification (record 13, token `{{user_uid}}`) and
    the one that decided the first finding (records 10 and 11, whose `author_label` is its display label). A projection that
    named no starter, another account or another label would be the frozen defect `characterization-can-freeze-a-defect`
    warns about, and fails here. Taking the two properties back out gives the historical body, digest for digest, and they
    are the last two of the run object (and the only bytes that moved).
    """
    decision = json.loads(_historical("10-appendDecision.success")["response"]["body"]["text"])["event"]
    history = json.loads(_historical("11-listDecisionHistory.success")["response"]["body"]["text"])["items"]
    classification = json.loads(_historical("13-getDocumentVersion.success")["response"]["body"]["text"])["classification"]
    assert [item["author_label"] for item in history] == [decision["author_label"]] == [_RUN_STARTER_LABEL]
    assert classification["confirmed_by_user_uid"] == _RUN_STARTER_USER_TOKEN
    appended = f', "started_by_user_uid": "{_RUN_STARTER_USER_TOKEN}", "started_by_label": "{_RUN_STARTER_LABEL}"'
    for case, digest in _RUN_STARTER_BODIES_SHA256.items():
        text = _run_starter_expected(_historical(case))["response"]["body"]["text"]
        run = _starter_of(case, text)
        assert run["started_by_user_uid"] == classification["confirmed_by_user_uid"], case
        assert run["started_by_label"] == decision["author_label"], case
        assert list(run)[-2:] == ["started_by_user_uid", "started_by_label"], case
        assert text.count(appended) == 1, case
        assert hashlib.sha256(text.replace(appended, "").encode("utf-8")).hexdigest() == digest, (
            f"{case} moved by more than the run starter"
        )


@pytest.mark.parametrize("case", tuple(_RUN_STARTER_BODIES_SHA256))
def test_the_run_starter_is_pinned_and_the_comparison_reddens_on_a_wrong_one(
    case: str, exchanges: dict[str, Any]
) -> None:
    """Right projection reproduces the live body; every way the starter can be wrong is reported.

    The live side is tampered, not only the expectation: a run attributed to another account, to another label or to nobody
    must redden, because "the starter fields are volatile" is the reading this corpus does not take.
    """
    import dataclasses

    record = _historical(case)
    exchange = exchanges[case]
    right = _run_starter_expected(record)
    assert journey.differences(exchange, right) == []
    assert right["response"]["body"]["length"] == len(exchange.body), "the projected length is not the raw body's"
    # Not vacuous: the committed record on its own does not match, so the two properties really are in the live body.
    assert any("body:" in line for line in journey.differences(exchange, record))

    uid = journey.presented_account_uid()
    live = exchange.body.decode("utf-8")
    assert live.count(f'"started_by_user_uid": "{uid}"') == 1 and live.count(f'"started_by_label": "{_RUN_STARTER_LABEL}"') == 1
    other_uid = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    assert other_uid != uid
    tampered = {
        "another account": live.replace(uid, other_uid),
        "another label": live.replace(f'"started_by_label": "{_RUN_STARTER_LABEL}"', '"started_by_label": "Иванов И."'),
        "no label": live.replace(f', "started_by_label": "{_RUN_STARTER_LABEL}"', ""),
        "no starter": live.replace(f', "started_by_user_uid": "{uid}", "started_by_label": "{_RUN_STARTER_LABEL}"', ""),
    }
    for what, body in tampered.items():
        assert body != live, what
        found = journey.differences(dataclasses.replace(exchange, body=body.encode("utf-8")), right)
        assert any("body:" in line for line in found), f"{case}: a run with {what} was not reported"
    # And an expectation naming the wrong starter does not match the true live body.
    for wrong in (
        _run_starter_expected(record, uid="usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"),
        _run_starter_expected(record, label="Иванов И."),
    ):
        assert any("body:" in line for line in journey.differences(exchange, wrong))


def test_the_run_starter_projection_refuses_a_changed_record(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both guards in front of the projection can fail: the body must be the committed one, and the committed one the pinned one."""
    case = "06-getRunStatus.success"
    changed = _historical(case)
    changed["response"]["body"]["text"] += " "
    with pytest.raises(AssertionError, match="changed historical body"):
        _run_starter_expected(changed)
    monkeypatch.setitem(_RUN_STARTER_BODIES_SHA256, case, "0" * 64)
    with pytest.raises(AssertionError, match="review it before projecting the run starter"):
        _run_starter_expected(_historical(case))
    monkeypatch.undo()
    already = _run_starter_expected(_historical(case))
    with pytest.raises(AssertionError, match="changed historical body"):
        _run_starter_expected(already)


def test_the_document_tags_of_records_32_and_33_are_none_because_the_journey_sets_none() -> None:
    """Both listings carry `"tags": []`, and nothing in the corpus could have given a document a tag.

    `setDocumentTags` is not among the operations the records cover, and the set of covered operations is asserted whole by
    `test_every_one_of_the_seventeen_operations_is_covered`; the listings are the two reads the contract says carry the property.
    The value follows from that, not from the live response; the projection places it last, after `classification`.
    """
    assert "setDocumentTags" not in SEVENTEEN_OPERATIONS
    covered = {_historical(path.stem)["operation"] for path in RECORD_FILES}
    assert "setDocumentTags" not in covered
    for case in sorted(_TAGS_CASES):
        text = _schema_compat_expected(_historical(case))["response"]["body"]["text"]
        item = json.loads(text)["items"][0]
        assert item["tags"] == [] and list(item)[-1] == "tags", case
        assert text.count('"tags": []') == 1, case
        assert text.replace(', "tags": []', "").replace(
            ', "upload_kind": "portal_bundle"', ""
        ) == _compat_source_bodies()[case], f"{case} moved by more than the portal kind and the tags"


@pytest.mark.parametrize("case", sorted(_TAGS_CASES))
def test_the_document_tags_projection_reddens_on_a_wrong_or_missing_tags(
    case: str, exchanges: dict[str, Any]
) -> None:
    expected = _schema_compat_expected(_historical(case))
    assert journey.differences(exchanges[case], expected) == []
    for what, replacement in (("a tag", '"tags": ["extra"]'), ("no tags property", None)):
        wrong = json.loads(json.dumps(expected))
        text = wrong["response"]["body"]["text"]
        assert text.count('"tags": []') == 1
        wrong["response"]["body"]["text"] = (
            text.replace('"tags": []', replacement) if replacement else text.replace(', "tags": []', "")
        )
        assert any("body:" in line for line in journey.differences(exchanges[case], wrong)), (
            f"{case}: {what} was not reported"
        )


def test_schema_compat_refuses_a_changed_historical_record() -> None:
    case = "02-uploadDocument.success"
    changed = json.loads((journey.RECORDS / f"{case}.json").read_text(encoding="utf-8"))
    changed["response"]["body"]["text"] += " "
    with pytest.raises(AssertionError, match="changed historical body"):
        _schema_compat_expected(changed)


def test_the_comparison_reddens_on_a_planted_difference(exchanges: dict[str, Any]) -> None:
    """Every kind of difference the comparison is supposed to catch, planted.

    A baseline nobody has seen reject anything is a baseline that will accept anything.
    """
    path = journey.RECORDS / "03-startRun.success.json"
    expected = _run_starter_expected(json.loads(path.read_text(encoding="utf-8")))
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
    csv_expected = _csv_compat_expected(json.loads(csv_path.read_text(encoding="utf-8")))
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
    expected = json.loads(journey.record_path(case).read_text(encoding="utf-8"))
    if case == "12-exportRunCsv.success":
        return _csv_compat_expected(expected)
    return expected


def test_csv_compat_projection_preserves_legacy_bytes_and_reddens_on_mutations() -> None:
    historical = json.loads(
        journey.record_path("12-exportRunCsv.success").read_text(encoding="utf-8")
    )
    original = json.loads(json.dumps(historical))
    current = _csv_compat_expected(historical)
    old = _body_bytes(historical)
    new = _body_bytes(current)
    old_lines = old.split(b"\r\n")
    new_lines = new.split(b"\r\n")

    assert historical == original, "the historical record was mutated in memory"
    assert current["response"]["body"]["length"] == 4446
    assert len(new) - len(old) == 37
    assert new_lines[0] == old_lines[0] + _APPENDED_CSV_HEADER
    assert len(old_lines) == len(new_lines) == 7
    assert new_lines[1:-1] == [line + b",," for line in old_lines[1:-1]]
    assert new_lines[-1] == old_lines[-1] == b""
    parsed = list(csv.reader(io.StringIO(new.decode("utf-8-sig"), newline="")))
    assert [len(row) for row in parsed] == [19] * 6
    assert all(row[-2:] == ["", ""] for row in parsed[1:])

    declaration = current["unordered"]
    assert not journey._unordered_differences(new, new, declaration)
    assert b"accepted" in new
    assert b",,\r\n" in new
    for changed in (
        new[3:],  # missing BOM
        new.replace(b"\r\n", b"\n"),
        new.replace(b"accepted", b"rejected", 1),
        new.replace(b",,\r\n", b",critical,\r\n", 1),
        new.replace(b",,\r\n", b",,critical\r\n", 1),
        new.replace(b",,\r\n", b",,,\r\n", 1),
        old,  # silently omitting both new columns
    ):
        assert journey._unordered_differences(new, changed, declaration), (
            "CSV compatibility comparison hid a changed byte"
        )


def test_csv_compat_refuses_a_changed_historical_record() -> None:
    historical = json.loads(
        journey.record_path("12-exportRunCsv.success").read_text(encoding="utf-8")
    )
    old = _body_bytes(historical)
    with pytest.raises(ValueError, match="only to record 12"):
        _csv_compat_expected({**historical, "case": "08-listRunFindings.success"})
    with pytest.raises(ValueError, match="historical CSV bytes changed"):
        _csv_compat_expected(
            _with_body(historical, old.replace(b"accepted", b"rejected", 1))
        )
    with pytest.raises(ValueError, match="historical CSV bytes changed"):
        _csv_compat_expected(
            _with_body(historical, old.replace(b"\r\n", b"\n", 1))
        )
    with pytest.raises(ValueError, match="pre-token CSV length changed"):
        _csv_compat_expected(_csv_compat_expected(historical))


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


#: `BETA-CONTRACT-SEAL-01`. The SHA-256 of the body text of the sixteen error records that carry
#: ``contract_version``, as committed at ``c7d5f483`` (the tree the seal started from), when the
#: version was ``1.0.0-draft.1``. Read from the record files at that commit
#: (``git show c7d5f483:<record>``), never from the files now: an expectation computed from the
#: files it checks could not report that something besides the version moved. The digests repeat
#: where bodies are the same bytes (records 23-25 are one error, 28 and 29 another).
_PRE_SEAL_CONTRACT_VERSION_BODIES = {
    "05b-createProject.idempotency_key_reuse": "fae9a4f5d7b4cd7c5105407760570538afdba33b5b631a3a9678e8d71fabfa27",
    "17-uploadDocument.refusal.pdf_magic_bytes": "ebdff1b5d02bfb29f571e1c2057d54a92f2aa28183edfdf4391ef4539d8ce492",
    "18-uploadDocument.refusal.byte_size": "410fc87aa23228360505644a7e0d1138ad969576fa8d014d3391af201aaf5aae",
    "19-uploadDocument.refusal.not_encrypted": "cd3eb516133fdd81688f01473cd695d28aa7e9ff619ad667723a882bf845d912",
    "20-uploadDocument.refusal.page_count": "d6cd88acf6df179cb8271a731607f0dff1bb2345b3063587660e56d21a8a4c60",
    "21-uploadDocument.refusal.every_page_has_extractable_text": "7e56da146d00d631f3a798bfc3b218b2257cc5dc8e85aa7f77a955ee04deef08",
    "22-uploadDocument.refusal.max_bytes": "a88fcbdd024d8677c8f98dec64096caf2f3c4fca4f64e58fa003c1a053ebc848",
    "23-createProject.refusal.additionalProperties": "4409a35e63cfb593fc8298cd5f1c8d7471f21c4beb3680639a4d2a97b87dc263",
    "24-startRun.refusal.additionalProperties": "4409a35e63cfb593fc8298cd5f1c8d7471f21c4beb3680639a4d2a97b87dc263",
    "25-appendDecision.refusal.additionalProperties": "4409a35e63cfb593fc8298cd5f1c8d7471f21c4beb3680639a4d2a97b87dc263",
    "26-uploadDocument.refusal.additionalProperties": "4b3ba78113b802ca03ec93170fa1799442d5acddecaaa5409b741370f71ff18f",
    "27-createProject.refusal.idempotency_key_required": "db9f1a80fc2f41734a37e8b963d682d75dd82014fe2121f892efa7adeb7f8bbe",
    "28-dispatch.no_route": "869206a64c628aef85e4a5ec76475e05925e488e4870a276e1c50b8b682b4c3f",
    "29-dispatch.method_not_allowed": "869206a64c628aef85e4a5ec76475e05925e488e4870a276e1c50b8b682b4c3f",
    "30-getRunStatus.not_found": "eb853fb3b18a9b196f68ff75fa5548450bb796902bd91cac4df6d23216f719e0",
    "31-streamDocumentVersionContent.storage_credential_refused": "bd96ee08e56661527df7418fe47878d4b265e81e1774b547b16b77217a76fdd3",
}

_DRAFT_VERSION_KEY = '"contract_version": "1.0.0-draft.1"'
_SEALED_VERSION_KEY = '"contract_version": "1.0.0"'

#: `LANE-W13-COST-01` (`D-322`). The records added after the seal whose body names a contract version, and the only way
#: they may: as the journey's own `{{contract_version}}` token (`journey.declare_contract_version`), which stands for the
#: version the frozen contract declares for every `ErrorEnvelope` and for nothing else. A literal would be edited at every
#: contract bump without telling anyone anything; a pattern or a skipped field name would accept a wrong version. The
#: sixteen above are historical and stay literal (`1.0.0`, projected to the current version by the comparison behind a
#: digest); a record is admitted to this table by a commit that says why, like a row of `PERMITTED_EXCEPTIONS`.
_TOKENISED_CONTRACT_VERSION_CASES = frozenset({"02c-startRun.refusal.cost_consent_required"})
_TOKENISED_VERSION_KEY = '"contract_version": "{{contract_version}}"'
_VERSION_TOKEN = "{{contract_version}}"


def _contract_version_census(texts: dict[str, str]) -> list[str]:
    """Every way the records that name a contract version stop being accounted for, as one list.

    One function, used by the guard and by the test that proves the guard can fail, so the proof exercises the rule rather
    than a copy of it. ``texts`` maps a case to its response body text.
    """
    historical = set(_PRE_SEAL_CONTRACT_VERSION_BODIES)
    tokenised = set(_TOKENISED_CONTRACT_VERSION_CASES)
    carrying = {case for case, text in texts.items() if "contract_version" in text}
    found = [
        f"{case}: names a contract version and is in neither table (an unexamined literal)"
        for case in sorted(carrying - historical - tokenised)
    ]
    found += [f"{case}: is in a table and names no contract version" for case in sorted((historical | tokenised) - carrying)]
    for case in sorted(tokenised & carrying):
        text = texts[case]
        if text.count(_TOKENISED_VERSION_KEY) != 1:
            found.append(f"{case}: does not carry exactly one {_VERSION_TOKEN}")
        if re.search(r'"contract_version": "[0-9]', text):
            found.append(f"{case}: carries a literal contract version")
    found += [f"{case}: a historical record carries {_VERSION_TOKEN}" for case in sorted(historical & carrying) if _VERSION_TOKEN in texts[case]]
    return found


def _body_texts() -> dict[str, str]:
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8"))["response"]["body"].get("text", "")
        for path in RECORD_FILES
    }


def test_the_sixteen_error_records_moved_by_the_contract_version_and_nothing_else() -> None:
    """The re-capture asserted, not merely made: put the draft version back and each body is
    the previous capture's again, digest for digest, and its declared length is eight shorter.

    `MEMORY: characterization can freeze a defect` is why a re-capture is not evidence by
    itself. What this pins is the *difference*: one property value, ``contract_version``,
    ``1.0.0-draft.1`` -> ``1.0.0``, which is thirteen characters becoming five. The set is also
    asserted whole: every record whose body names a contract version is in the table, so a
    seventeenth cannot carry the literal unexamined. No record gains an exception block: this
    is not a debt of one operation but the one literal every error body shares.

    `D-322`: records added after the seal are the second table, `_TOKENISED_CONTRACT_VERSION_CASES`; the
    census (`_contract_version_census`) requires each of them to carry the journey's token and no literal.
    """
    # `D-322`: the set is still asserted whole, now in two tables -- the sixteen historical literals below and the
    # tokenised records above -- so a record that names a version in any other way is reported.
    assert _contract_version_census(_body_texts()) == []
    for case, digest in _PRE_SEAL_CONTRACT_VERSION_BODIES.items():
        record = json.loads((journey.RECORDS / f"{case}.json").read_text(encoding="utf-8"))
        body = record["response"]["body"]
        text = body["text"]
        assert text.count(_SEALED_VERSION_KEY) == 1, case
        assert "draft" not in text, case
        restored = text.replace(_SEALED_VERSION_KEY, _DRAFT_VERSION_KEY)
        assert hashlib.sha256(restored.encode("utf-8")).hexdigest() == digest, (
            f"{case} moved by more than its contract version"
        )
        # `length` describes the body before token substitution, so it exceeds the tokenised
        # text by what its one `{{correlation_id}}` token hides (a 36-character id behind an
        # 18-character token). That slack was 18 before the seal and is 18 after it: the length
        # moved by exactly the eight characters the version string lost, and by nothing else.
        assert body["length"] - len(text.encode("utf-8")) == 18, case
        assert body["length"] + 8 - len(restored.encode("utf-8")) == 18, case


def test_the_contract_version_move_test_can_fail() -> None:
    """The digest test above, shown rejecting a change of anything but the version."""
    case = "30-getRunStatus.not_found"
    record = json.loads((journey.RECORDS / f"{case}.json").read_text(encoding="utf-8"))
    text = record["response"]["body"]["text"]
    restored = text.replace(_SEALED_VERSION_KEY, _DRAFT_VERSION_KEY)
    assert hashlib.sha256(restored.encode("utf-8")).hexdigest() == _PRE_SEAL_CONTRACT_VERSION_BODIES[case]
    for mutated in (
        restored.replace("not_found", "conflict", 1),
        restored.replace("1.0.0-draft.1", "1.0.0-draft.2", 1),
        text,
    ):
        assert hashlib.sha256(mutated.encode("utf-8")).hexdigest() != _PRE_SEAL_CONTRACT_VERSION_BODIES[case]


def test_the_contract_version_census_can_fail() -> None:
    """The census above, shown reporting each way a version-bearing record could escape it (`D-322`).

    The plants are in-memory copies of the real bodies: a test that edits ``records/`` would trip the gate's
    changed-during-the-run check.
    """
    texts = _body_texts()
    assert _contract_version_census(texts) == [], "the unperturbed records are already reported"
    tokenised = "02c-startRun.refusal.cost_consent_required"
    historical = "30-getRunStatus.not_found"

    def plant(**changes: str | None) -> list[str]:
        planted = dict(texts)
        for case, text in changes.items():
            if text is None:
                planted.pop(case)
            else:
                planted[case] = text
        return _contract_version_census(planted)

    # A new record that names the version as a literal, and one that names it as the token but is in no table.
    literal = plant(new_record=texts[historical])
    assert literal == ["new_record: names a contract version and is in neither table (an unexamined literal)"], literal
    unlisted = plant(new_record=texts[tokenised])
    assert unlisted == ["new_record: names a contract version and is in neither table (an unexamined literal)"], unlisted
    # A tokenised record that carries a literal instead of the token, or two properties, or loses the property.
    assert plant(**{tokenised: texts[tokenised].replace(_VERSION_TOKEN, "1.33.0")}) == [
        f"{tokenised}: does not carry exactly one {_VERSION_TOKEN}",
        f"{tokenised}: carries a literal contract version",
    ]
    assert plant(**{tokenised: texts[tokenised].replace(_TOKENISED_VERSION_KEY, _TOKENISED_VERSION_KEY * 2)}) == [
        f"{tokenised}: does not carry exactly one {_VERSION_TOKEN}"
    ]
    assert plant(**{tokenised: texts[tokenised].replace('"contract_version"', '"version"')}) == [
        f"{tokenised}: does not carry exactly one {_VERSION_TOKEN}"
    ]
    # A historical record that was tokenised, or a table row whose record is gone.
    assert plant(**{historical: texts[historical].replace('"1.0.0"', '"{{contract_version}}"')}) == [
        f"{historical}: a historical record carries {_VERSION_TOKEN}"
    ]
    assert plant(**{historical: None}) == [f"{historical}: is in a table and names no contract version"]


def _contract_schemas() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[3] / "contracts/api/v1/openapi.json"
    return json.loads(path.read_text(encoding="utf-8"))["components"]["schemas"]  # type: ignore[no-any-return]


def _is_type(value: Any, name: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
        "array": isinstance(value, list),
    }[name]


def _schema_problems(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """What the contract's JSON Schema subset says is wrong with ``value``, one line per problem.

    Only the keywords the two schemas of the cost path use -- ``$ref``, ``type``, ``const``, ``enum``, ``pattern``,
    ``minimum``, ``minLength``, ``maxLength``, ``required``, ``properties``, ``additionalProperties`` -- and it refuses
    any other keyword it meets rather than ignoring it, so it cannot pass a body on a rule it does not read. (``jsonschema``
    is not a dependency of this environment.)
    """
    known = {
        "$ref", "type", "const", "enum", "pattern", "minimum", "maximum", "minLength", "maxLength", "required",
        "properties", "additionalProperties", "propertyNames", "maxProperties",
        "description", "title", "examples",  # annotations: they constrain nothing
    }
    unread = set(schema) - known
    assert not unread, f"{path}: the contract uses a keyword this check does not read: {sorted(unread)}"
    if "$ref" in schema:
        return _schema_problems(value, _contract_schemas()[schema["$ref"].rsplit("/", 1)[1]], path)
    found: list[str] = []
    if "const" in schema and value != schema["const"]:
        found.append(f"{path}: {value!r} is not the const {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        found.append(f"{path}: {value!r} is not one of {schema['enum']}")
    kinds = schema.get("type")
    kinds = [kinds] if isinstance(kinds, str) else list(kinds or [])
    if kinds and not any(_is_type(value, kind) for kind in kinds):
        return found + [f"{path}: {value!r} is not of type {'/'.join(kinds)}"]
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            found.append(f"{path}: {value!r} does not match {schema['pattern']}")
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", 10**9):
            found.append(f"{path}: length {len(value)} is outside the declared bounds")
    if isinstance(value, int) and not isinstance(value, bool):
        if value < schema.get("minimum", value) or value > schema.get("maximum", value):
            found.append(f"{path}: {value} is outside the declared bounds")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        if len(value) > schema.get("maxProperties", len(value)):
            found.append(f"{path}: {len(value)} properties exceed maxProperties")
        names = schema.get("propertyNames", {}).get("pattern")
        found += [f"{path}.{name}: a name that does not match {names}" for name in value if names and not re.search(names, name)]
        found += [f"{path}.{name}: required and absent" for name in schema.get("required", []) if name not in value]
        extra = schema.get("additionalProperties")
        for name, item in value.items():
            if name in properties:
                found += _schema_problems(item, properties[name], f"{path}.{name}")
            elif extra is False:
                found.append(f"{path}.{name}: not declared (additionalProperties is false)")
            elif isinstance(extra, dict):
                found += _schema_problems(item, extra, f"{path}.{name}")
    return found


#: Stand-ins for the tokens of the two cost-path records, shaped as the contract says the values are.
_STAND_INS = {
    "{{contract_version}}": None,  # the contract's own const, filled in by the caller
    "{{correlation_id}}": "cid-" + "0" * 32,
    "{{estimate_digest}}": "a" * 64,
    "{{version_uid}}": "ver_" + "0" * 26,
}


def _record_as_contract_value(case: str) -> Any:
    text = _historical(case)["response"]["body"]["text"]
    for token, stand_in in _STAND_INS.items():
        text = text.replace(token, stand_in if stand_in is not None else journey.contract_envelope_version())
    assert "{{" not in text, f"{case}: a token without a stand-in: {text}"
    return json.loads(text)


def test_the_cost_path_records_are_what_the_contract_declares() -> None:
    """02c is an `ErrorEnvelope` and 02d a `RunCostEstimate`, validated against `contracts/api/v1/openapi.json` (`D-322`).

    The status of each is the one the operation declares (`startRun`: 422, `RunInputInvalid`; `estimateRunCost`: 200).
    The checker is shown able to fail below, so a body that satisfied it is evidence and not an absence of checking.
    """
    refusal = _historical("02c-startRun.refusal.cost_consent_required")
    assert refusal["response"]["status"] == 422 and refusal["operation"] == "startRun"
    assert _schema_problems(_record_as_contract_value(refusal["case"]), {"$ref": "#/components/schemas/ErrorEnvelope"}) == []
    estimate = _historical(_ESTIMATE_CASE)
    assert estimate["response"]["status"] == 200 and estimate["operation"] == "estimateRunCost"
    assert _schema_problems(_record_as_contract_value(_ESTIMATE_CASE), {"$ref": "#/components/schemas/RunCostEstimate"}) == []
    # The refusal's code, retryability and details are the ones the contract's family allows: validation_failed is
    # 422 and not retryable; `field` / `constraint` are free-form detail keys (the catalog names them safe).
    envelope = _record_as_contract_value(refusal["case"])
    assert (envelope["error_code"], envelope["retryable"]) == ("validation_failed", False)
    assert envelope["details"] == {"field": "cost_consent", "constraint": "confirmation_required"}


def test_the_contract_check_can_fail() -> None:
    estimate = _record_as_contract_value(_ESTIMATE_CASE)
    refusal = _record_as_contract_value("02c-startRun.refusal.cost_consent_required")
    estimate_schema = {"$ref": "#/components/schemas/RunCostEstimate"}
    envelope_schema = {"$ref": "#/components/schemas/ErrorEnvelope"}
    assert _schema_problems(estimate, estimate_schema) == []
    assert _schema_problems(refusal, envelope_schema) == []

    def with_(value: dict[str, Any], **changes: Any) -> dict[str, Any]:
        return {**value, **changes}

    assert _schema_problems(with_(estimate, extra=1), estimate_schema) == ["$.extra: not declared (additionalProperties is false)"]
    assert _schema_problems({k: v for k, v in estimate.items() if k != "calls"}, estimate_schema) == ["$.calls: required and absent"]
    assert _schema_problems(with_(estimate, currency="EUR"), estimate_schema) == ["$.currency: 'EUR' is not the const 'USD'"]
    assert _schema_problems(with_(estimate, windows=0), estimate_schema) == ["$.windows: 0 is outside the declared bounds"]
    assert _schema_problems(with_(estimate, estimate_digest="A" * 64), estimate_schema) == [
        f"$.estimate_digest: {'A' * 64!r} does not match ^[0-9a-f]{{64}}$"
    ]
    assert _schema_problems(with_(estimate, scope="batch"), estimate_schema) == ["$.scope: 'batch' is not the const 'run'"]
    # The shape the product serves today: a null where the contract says a string. This is the deviation.
    assert _schema_problems(with_(estimate, pin_id=None), estimate_schema) == ["$.pin_id: None is not of type string"]
    assert _schema_problems(with_(refusal, contract_version="1.0.0"), envelope_schema) == [
        f"$.contract_version: '1.0.0' is not the const {journey.contract_envelope_version()!r}"
    ]
    assert _schema_problems(with_(refusal, error_code="no_such_code"), envelope_schema)
    with pytest.raises(AssertionError, match="keyword this check does not read"):
        _schema_problems(1, {"type": "integer", "multipleOf": 2})


def test_the_served_estimate_has_no_null_property_and_meets_its_schema(exchanges: dict[str, Any]) -> None:
    """`D-322`, fixed: the route drops an optional property it did not set instead of rendering it as `null`.

    It rendered the six optional, non-nullable properties of `RunCostEstimate` as `null` until 2026-11-06; record 02d was
    always the contract-correct form, and now the served body is that form too. A `null` coming back reddens here.
    """
    live = json.loads(exchanges[_ESTIMATE_CASE].body.decode("utf-8"))
    assert [name for name, value in live.items() if value is None] == []
    assert _schema_problems(live, {"$ref": "#/components/schemas/RunCostEstimate"}) == []
    assert not set(_ESTIMATE_OPTIONAL_PROPERTIES) & set(live), "this journey's version sets none of the six"


def _tampered(exchange: Any, mutate: Any) -> Any:
    """The exchange with its body rewritten by ``mutate(bytes) -> bytes`` and a Content-Length that still describes it."""
    body = mutate(exchange.body)
    assert body != exchange.body, "the plant changed nothing"
    headers = tuple((name, str(len(body)) if name == "Content-Length" else value) for name, value in exchange.headers)
    return dataclasses.replace(exchange, body=body, headers=headers)


def _json_plant(change: Any) -> Any:
    """A body mutation that parses the live JSON, changes it and renders it the way the surface does (`encode_json`)."""
    def mutate(raw: bytes) -> bytes:
        parsed = json.loads(raw.decode("utf-8"))
        assert json.dumps(parsed, ensure_ascii=False).encode("utf-8") == raw, "the plant would re-render the body"
        change(parsed)
        return json.dumps(parsed, ensure_ascii=False).encode("utf-8")
    return mutate


def test_the_cost_path_records_redden_on_a_planted_difference(exchanges: dict[str, Any]) -> None:
    """Each kind of difference the comparison must catch, planted in the live answer of 02c and of 02d (`D-322`)."""
    refusal_case = "02c-startRun.refusal.cost_consent_required"
    refusal = exchanges[refusal_case]
    refusal_expected = _projected(_historical(refusal_case))
    assert journey.differences(refusal, refusal_expected) == []

    def set_(name: str, value: Any) -> Any:
        return _json_plant(lambda body: body.__setitem__(name, value))

    def set_detail(name: str, value: Any) -> Any:
        return _json_plant(lambda body: body["details"].__setitem__(name, value))

    plants = {
        "an older contract version": set_("contract_version", "1.0.0"),
        "a newer contract version": set_("contract_version", "99.0.0"),
        "an empty contract version": set_("contract_version", ""),
        "a retryable refusal": set_("retryable", True),
        "another code": set_("error_code", "conflict"),
        "another message": set_("message", "Cost consent is required."),
        "another field": set_detail("field", "ceiling_micros"),
        "another constraint": set_detail("constraint", "below_estimate"),
        "no details": _json_plant(lambda body: body.pop("details")),
        "no contract version": _json_plant(lambda body: body.pop("contract_version")),
    }
    for what, mutate in plants.items():
        assert any("body:" in line for line in journey.differences(_tampered(refusal, mutate), refusal_expected)), (
            f"{refusal_case}: {what} was not reported"
        )
    assert any("status" in line for line in journey.differences(dataclasses.replace(refusal, status=409), refusal_expected))
    assert journey.differences(
        dataclasses.replace(refusal, headers=tuple(h for h in refusal.headers if h[0] != "X-Correlation-Id")), refusal_expected
    )

    estimate = exchanges[_ESTIMATE_CASE]
    estimate_expected = _projected(_historical(_ESTIMATE_CASE))
    assert journey.differences(estimate, estimate_expected) == []
    live = json.loads(estimate.body.decode("utf-8"))
    figure_plants = {
        "a dearer estimate": set_("estimated_cost_micros", live["estimated_cost_micros"] + 1),
        "a lower recommended ceiling": set_("recommended_ceiling_micros", live["recommended_ceiling_micros"] - 1),
        "more input tokens": set_("input_tokens", live["input_tokens"] + 1),
        "another model": set_("model_id", "another-model"),
        "another page count": set_("page_count", live["page_count"] + 1),
        "another window count": set_("windows", live["windows"] + 1),
        "the relaxed output allowance": set_("output_tokens", 64000),
        "another currency": set_("currency", "EUR"),
        "another scope": set_("scope", "batch"),
        "a metered route that is unmetered": set_("billing", "unmetered"),
        "a missing figure": _json_plant(lambda body: body.pop("calls")),
        "a digest that is not the one the journey read": set_("estimate_digest", "0" * 64),
        # The route no longer renders unset optional properties (`D-322`, fixed): one coming back as `null`, or set, is reported.
        "an optional property back as null": _json_plant(lambda body: body.__setitem__("pin_id", None)),
        "an optional property set": _json_plant(lambda body: body.__setitem__("preset_revision_id", "apr_x")),
    }
    for what, mutate in figure_plants.items():
        assert any("body:" in line for line in journey.differences(_tampered(estimate, mutate), estimate_expected)), (
            f"{_ESTIMATE_CASE}: {what} was not reported"
        )
    assert any("status" in line for line in journey.differences(dataclasses.replace(estimate, status=202), estimate_expected))


def test_the_contract_version_token_is_the_contracts_and_refuses_a_contract_that_disagrees(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`journey.contract_envelope_version` is the const of the envelope, equal to the document's `info.version` (`D-322`)."""
    assert journey.contract_envelope_version() == _current_contract_version()
    record = _historical("02c-startRun.refusal.cost_consent_required")
    assert "{{contract_version}}" in record["tokens"]
    assert "contract_version" in record["response"]["body"]["text"]
    document = json.loads((Path(__file__).resolve().parents[3] / "contracts/api/v1/openapi.json").read_text(encoding="utf-8"))
    document["components"]["schemas"]["ErrorEnvelope"]["properties"]["contract_version"]["const"] = "0.0.1"
    drifted = tmp_path / "openapi.json"
    drifted.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(journey, "CONTRACT_DOCUMENT", drifted)
    with pytest.raises(AssertionError, match="no longer says that the envelope's version is the document's version"):
        journey.contract_envelope_version()


def test_the_estimate_digest_must_be_a_sha256_before_it_is_tokenised() -> None:
    tokens = journey.Tokens()
    for bad in ("", "A" * 64, "a" * 63, "a" * 65, "g" * 64, "a" * 64 + "\n", None, 7):
        with pytest.raises(AssertionError, match="not the pinned Sha256 format"):
            journey.declare_estimate_digest(tokens, bad)
    assert tokens.values() == {}
    journey.declare_estimate_digest(tokens, "0123456789abcdef" * 4)
    assert tokens.values() == {"{{estimate_digest}}": "0123456789abcdef" * 4}


def test_the_consented_start_carries_the_consent_the_estimate_record_gives() -> None:
    """Records 03-05 are the consented start; the estimate record is where their consent comes from (`D-322`).

    The start records keep the request side as lengths only. Rebuild the three request bodies from record 02d -- the
    version uid and the digest at their fixed contract widths, the ceiling as the recommended one -- and the lengths
    the start records declare are exactly those: the consent is the estimate's digest and its recommended ceiling, and
    that ceiling is sufficient, since record 03 answered 202 to it (the contract: "a sufficient explicit ceiling").
    Records 02c and 02d send the bare `version_uid`.
    """
    estimate = _record_as_contract_value(_ESTIMATE_CASE)
    assert estimate["recommended_ceiling_micros"] >= estimate["estimated_cost_micros"] > 0
    version, digest = "ver_" + "0" * 26, "a" * 64
    consent = {"estimate_digest": digest, "ceiling_micros": estimate["recommended_ceiling_micros"], "confirmed": True}
    expected_lengths = {
        "03-startRun.success": len(json.dumps({"version_uid": version, "cost_consent": consent})),
        "04-startRun.replay": len(json.dumps({"version_uid": version, "cost_consent": consent})),
        "05-startRun.replay_with_normalised_property": len(
            json.dumps({"version_uid": version, "provider_mode": "recorded", "cost_consent": consent})
        ),
        "02c-startRun.refusal.cost_consent_required": len(json.dumps({"version_uid": version})),
        _ESTIMATE_CASE: len(json.dumps({"version_uid": version})),
    }
    for case, length in expected_lengths.items():
        assert _historical(case)["request"]["body_length"] == length, case
    assert _historical("03-startRun.success")["response"]["status"] == 202
    # The estimate is the one of the version the start was made over, in the mode the run reports.
    assert estimate["provider_mode"] == json.loads(_historical("03-startRun.success")["response"]["body"]["text"])["provider_mode"]
    assert '"version_uid": "{{version_uid}}"' in _historical(_ESTIMATE_CASE)["response"]["body"]["text"]


def test_the_estimate_follows_from_the_records_around_it() -> None:
    """The figures the contract or an earlier record determines, derived and not copied from the server (`D-322`).

    What is derived: `page_count` is the version's (record 13); `output_tokens` is `windows` times the 16 000 the contract
    gives for `relaxed_limits: false` ("False requests up to 16,000 output tokens", `StartRunRequest.relaxed_limits`);
    `calls` equals `windows` for the plain analysis the journey prices; `relaxed_limits` is the request's default.
    What is only pinned, and moves with the fixture text, the pinned prompt bundle and the pinned price table by design:
    `text_characters`, `input_tokens`, `estimated_cost_micros`, `recommended_ceiling_micros`, `model_id` and `billing`.
    """
    estimate = _record_as_contract_value(_ESTIMATE_CASE)
    version = json.loads(_historical("13-getDocumentVersion.success")["response"]["body"]["text"])
    assert estimate["page_count"] == version["page_count"] == 8
    assert estimate["output_tokens"] == estimate["windows"] * 16000
    assert estimate["calls"] == estimate["windows"] == 1
    assert estimate["relaxed_limits"] is False and estimate["scope"] == "run" and estimate["currency"] == "USD"
    assert not set(_ESTIMATE_OPTIONAL_PROPERTIES) & set(estimate), "the record is the contract-correct form"


def test_the_refused_unconsented_start_left_no_run_behind() -> None:
    """Record 34 lists the project's runs after the whole journey: one, the consented start's (`D-322`).

    Record 02c's refusal precedes the idempotency key's claim ("Nothing was created"), so it must not appear as a run.
    """
    items = json.loads(_historical("34-listRuns.success")["response"]["body"]["text"])["items"]
    assert [item["run_id"] for item in items] == ["{{run_id}}"]
    refusal = _historical("02c-startRun.refusal.cost_consent_required")
    keys = {
        case: dict(map(tuple, _historical(case)["request"]["headers"]))["Idempotency-Key"]
        for case in (refusal["case"], "03-startRun.success")
    }
    assert keys[refusal["case"]] != keys["03-startRun.success"], "the refusal and the start must not share a key"
