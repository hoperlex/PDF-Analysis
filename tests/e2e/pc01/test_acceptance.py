"""PC-01 acceptance: the ten criteria of ``docs/program/PROTOTYPE_PROFILE.md`` section 8,
measured against the **composed application** through its own front door.

Twenty sessions built this system and each verified its own segment. Session ``C1`` wired
the composition root and mounted the twelve routes. Nothing had driven the assembled thing
request-in / response-out, and that is the gap this suite exists to close: every fact below
is learned from a ``Response``, never from a session, an engine, a blob store or a module
the router calls.

**This suite is red at base e35a88a, and that is its finding.** Three view mappers in
``src/auditmanager/bootstrap/adapters.py`` cannot render what their routers ask them for,
so ``uploadDocument``, ``startRun`` and ``getRunStatus`` each answer ``500 internal_error``
and the journey stops at the second operation. The defects are described in
:func:`journey`'s failure message and in this session's report; they are owned by the
bootstrap/adapters tree and are deliberately not worked around here. Working around them
by importing ``IngestService`` would have produced a green suite certifying an application
that cannot accept a document.

It goes green with no edit once the owning tree is corrected. That was checked rather than
hoped: the suite was run against a scratch copy of ``src/`` carrying only those
corrections, and every test below passed there.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

_DRIVER_NAME = "c2_pc01_driver"


def _load_driver() -> Any:
    """The driver beside this file, by explicit path and under one shared name.

    ``--import-mode=importlib`` is in the root ``addopts``, so a bare ``from driver import
    ...`` does not resolve; and reusing ``sys.modules`` rather than loading a second copy
    is what keeps ``SESSION_TAG`` -- and therefore every idempotency key -- one value
    across the conftest and this module.
    """
    existing = sys.modules.get(_DRIVER_NAME)
    if existing is not None:
        return existing
    path = Path(__file__).resolve().with_name("driver.py")
    spec = importlib.util.spec_from_file_location(_DRIVER_NAME, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[_DRIVER_NAME] = module
    spec.loader.exec_module(module)
    return module


driver = _load_driver()

Answer = driver.Answer
Client = driver.Client
build_client = driver.build_client
key = driver.key
BASELINE_PDF = driver.BASELINE_PDF
NEGATIVE = driver.NEGATIVE
OPENAPI = driver.OPENAPI

#: The figures measured before this session, reproduced rather than assumed.
EXPECTED_BYTE_SIZE = 58978
EXPECTED_SHA256 = "6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f"
EXPECTED_PAGE_COUNT = 8
EXPECTED_FINDING_COUNT = 3
EXPECTED_CSV_ROWS = 5
EXPECTED_CSV_COLUMNS = 17
EXPECTED_STAGES = frozenset(
    {
        "document_context_build",
        "page_geometry_extraction",
        "source_preparation",
        "text_analysis",
    }
)


def _blocked(operation: str, answer: Answer, owning_tree: str, detail: str) -> str:
    return (
        f"{operation} could not be reached through the router: it answered "
        f"{answer.status} {answer.error_code!r}. {detail} "
        f"Owned by {owning_tree}. This suite does not work around it: reaching past the "
        "router to make the step succeed would certify an application that cannot serve."
    )


@dataclass
class Journey:
    """Every identity the journey allocated, and every answer it is asserted against."""

    project: Mapping[str, Any]
    version: Mapping[str, Any]
    version_read: Mapping[str, Any]
    content: bytes
    ranged: Answer
    started: Mapping[str, Any]
    status: Mapping[str, Any]
    findings: Sequence[Mapping[str, Any]]
    detail: Mapping[str, Any]
    accepted: Mapping[str, Any]
    rejected: Mapping[str, Any]
    commented: Mapping[str, Any]
    history: Sequence[Mapping[str, Any]]
    csv_bytes: bytes
    csv_repeat: bytes
    replays: dict[str, Any] = field(default_factory=dict)

    @property
    def project_uid(self) -> str:
        return str(self.project["project_uid"])

    @property
    def version_uid(self) -> str:
        return str(self.version["version_uid"])

    @property
    def run_id(self) -> str:
        return str(self.started["run_id"])


@pytest.fixture(scope="session")
def journey(client: Client) -> Journey:
    """Drive the whole PC-01 journey once, through the router, and keep every answer.

    Session-scoped because the journey is the expensive thing and re-running it per test
    would say nothing extra: each test below asserts a different property of one
    composition.
    """
    answer = client.create_project(name=f"C2 PC-01 {key('project')}", key=key("project"))
    assert answer.status == 201, _blocked(
        "createProject",
        answer,
        "src/auditmanager/bootstrap/",
        "The composition root's project adapter refused the very first request.",
    )
    project = answer.json

    answer = client.upload_document(
        project_uid=project["project_uid"],
        content=BASELINE_PDF.read_bytes(),
        key=key("upload"),
    )
    assert answer.status == 201, _blocked(
        "uploadDocument",
        answer,
        "src/auditmanager/bootstrap/adapters.py",
        "_version_view() builds a DocumentVersionView without the `sha256` the frozen "
        "DocumentVersion schema requires, so every upload raises TypeError inside the "
        "adapter and the edge renders it as an unclassified internal_error. "
        "DocumentVersionRecord carries both `sha256` and `display_title`; the mapper "
        "passes neither.",
    )
    version = answer.json

    answer = client.get_version(version["version_uid"])
    assert answer.status == 200, _blocked(
        "getDocumentVersion", answer, "src/auditmanager/bootstrap/adapters.py", ""
    )
    version_read = answer.json

    answer = client.stream_content(version["version_uid"])
    assert answer.status == 200, _blocked(
        "streamDocumentVersionContent", answer, "src/auditmanager/bootstrap/adapters.py", ""
    )
    content = answer.body
    ranged = client.stream_content(version["version_uid"], byte_range="bytes=0-1023")

    answer = client.start_run(version_uid=version["version_uid"], key=key("run"))
    assert answer.status == 202, _blocked(
        "startRun",
        answer,
        "src/auditmanager/bootstrap/adapters.py",
        "RunAdapter.start_run returns _StartedRunView, which carries only run_id and "
        "replayed, while the router renders it with run_status_body() and needs the whole "
        "frozen RunStatus. The run itself executes first, so POST /runs performs the "
        "analysis, writes the rows and *then* answers 500 with no run_id.",
    )
    started = answer.json
    # `D-20`. The `202` is the acceptance, not the result: every criterion below reads a
    # finished run, so the journey waits for the carrier here, once, on the real futures.
    assert started["state"] == "queued", (
        "startRun answered with a state that is not the accepted one; `D-20` put "
        "execution on a carrier and the 202 reports what was accepted"
    )
    client.await_runs()

    answer = client.run_status(started["run_id"])
    assert answer.status == 200, _blocked(
        "getRunStatus",
        answer,
        "src/auditmanager/bootstrap/adapters.py and src/auditmanager/runs/",
        "RunAdapter.get_run_status reads run.created_at, and RunRow projects no such "
        "field -- audit_run.created_at exists in the schema but the repository does not "
        "select it, so a required RunStatus property has no producer. The same method "
        "reads run.stages through getattr(..., ()), and RunRow has no stages either, so "
        "even a corrected created_at leaves RunStatus.stages permanently empty; the rows "
        "are behind RunRepository.stage_results().",
    )
    status = answer.json

    answer = client.run_findings(started["run_id"])
    assert answer.status == 200, _blocked(
        "listRunFindings", answer, "src/auditmanager/bootstrap/adapters.py", ""
    )
    findings = answer.json["items"]
    assert len(findings) >= 2, (
        f"the journey needs at least two findings to accept one and reject another; "
        f"the run published {len(findings)}"
    )

    answer = client.finding(findings[0]["finding_uid"])
    assert answer.status == 200, _blocked(
        "getFinding", answer, "src/auditmanager/bootstrap/adapters.py", ""
    )
    detail = answer.json

    answer = client.append_decision(
        finding_uid=findings[0]["finding_uid"],
        observation_id=findings[0]["observation"]["finding_observation_id"],
        event_type="accept",
        key=key("accept"),
    )
    assert answer.status == 201, _blocked(
        "appendDecision(accept)", answer, "src/auditmanager/bootstrap/adapters.py", ""
    )
    accepted = answer.json

    answer = client.append_decision(
        finding_uid=findings[1]["finding_uid"],
        observation_id=findings[1]["observation"]["finding_observation_id"],
        event_type="reject",
        key=key("reject"),
    )
    assert answer.status == 201, _blocked(
        "appendDecision(reject)", answer, "src/auditmanager/bootstrap/adapters.py", ""
    )
    rejected = answer.json

    answer = client.append_decision(
        finding_uid=findings[0]["finding_uid"],
        observation_id=findings[0]["observation"]["finding_observation_id"],
        event_type="comment",
        comment="C2 acceptance: a later remark, appended after the accept.",
        key=key("comment"),
    )
    assert answer.status == 201, _blocked(
        "appendDecision(comment)", answer, "src/auditmanager/bootstrap/adapters.py", ""
    )
    commented = answer.json

    answer = client.decision_history(findings[0]["finding_uid"])
    assert answer.status == 200, _blocked(
        "listDecisionHistory", answer, "src/auditmanager/bootstrap/adapters.py", ""
    )
    history = answer.json["items"]

    answer = client.export_csv(started["run_id"])
    assert answer.status == 200, _blocked(
        "exportRunCsv", answer, "src/auditmanager/bootstrap/adapters.py", ""
    )
    csv_bytes = answer.body
    csv_repeat = client.export_csv(started["run_id"]).body

    return Journey(
        project=project,
        version=version,
        version_read=version_read,
        content=content,
        ranged=ranged,
        started=started,
        status=status,
        findings=findings,
        detail=detail,
        accepted=accepted,
        rejected=rejected,
        commented=commented,
        history=history,
        csv_bytes=csv_bytes,
        csv_repeat=csv_repeat,
    )


# ======================================================================================
# Criterion 1 -- start the app, PostgreSQL and private S3 storage with documented commands
# ======================================================================================


def test_c1_the_application_composes_from_the_environment_and_answers(client: Client) -> None:
    """The process entry point builds, and the thing it builds serves a real request.

    ``make foundation`` proves the services; this proves the *application* on top of them.
    A composition test that only asserted ``create_app()`` returned an object would pass
    against a root that wired nothing, which is why this issues a request that has to
    reach PostgreSQL before it can answer.
    """
    assert len(client.app.router.routes) == 19
    answer = client.list_projects()
    assert answer.status == 200, answer.body
    assert "items" in answer.json


def test_c1_a_misconfigured_dependency_fails_at_construction_not_at_first_use() -> None:
    """The composition root's whole contract, stated as a test.

    A root that deferred the failure would build happily here and die on the first upload,
    in production, after a document had been accepted.
    """
    from auditmanager.api.composition import ConfigurationError

    with pytest.raises(ConfigurationError):
        build_client(DATABASE_URL="")


def test_c1_the_twelve_operations_are_exactly_the_frozen_contract(client: Client) -> None:
    """Asserted against the document, never against a list written out here.

    A list restated in a test is a second place to be wrong, and it would quietly agree
    with a router that had lost an operation.
    """
    document = json.loads(OPENAPI.read_text("utf-8"))
    declared = {
        (operation["operationId"], method.upper(), path)
        for path, operations in document["paths"].items()
        for method, operation in operations.items()
        if method in {"get", "post", "put", "patch", "delete"}
    }
    # ``(operationId, METHOD, path)`` read off the ``APIRoute`` table. One route carries a
    # *set* of methods, so each pair is one row here and an operation that quietly gained
    # a second method changes the set.
    implemented = {
        (route.operation_id, method, route.path)
        for route in client.app.router.routes
        for method in sorted(route.methods)
        if getattr(route, "operation_id", None)
    }
    assert implemented == declared


# ======================================================================================
# Criterion 2 -- migrate an empty database
# ======================================================================================


def test_c2_the_application_is_serving_against_the_migrated_head(client: Client) -> None:
    """A request that can only be answered by a database carrying the P02 head.

    ``make migrate`` and ``make check-db`` assert the head itself. What this adds is that
    the *application* is talking to that database: ``listProjects`` selects from a table
    only the migration creates, so an unmigrated database cannot produce a 200 here.
    """
    answer = client.list_projects()
    assert answer.status == 200, answer.body
    assert isinstance(answer.json["items"], list)


# ======================================================================================
# Criterion 3 -- a project, and an upload landing as an immutable version + private object
# ======================================================================================


def test_c3_the_upload_publishes_the_corpus_baseline_with_its_declared_bytes(
    journey: Journey,
) -> None:
    """The figures measured before this session, reproduced through the front door."""
    version = journey.version
    assert version["byte_size"] == EXPECTED_BYTE_SIZE
    assert version["sha256"] == EXPECTED_SHA256
    assert version["page_count"] == EXPECTED_PAGE_COUNT
    assert version["media_type"] == "application/pdf"
    assert version["version_ordinal"] == 1


def test_c3_the_streamed_bytes_are_the_bytes_that_were_uploaded(journey: Journey) -> None:
    """The object round-trips through storage without the server rewriting it.

    Hashing the streamed bytes rather than comparing lengths: a store that re-encoded the
    PDF would keep a plausible length and change the digest, and a length check would
    certify it.
    """
    assert hashlib.sha256(journey.content).hexdigest() == EXPECTED_SHA256
    assert journey.content == BASELINE_PDF.read_bytes()


def test_c3_a_ranged_read_serves_a_window_of_the_same_object(journey: Journey) -> None:
    assert journey.ranged.status == 206
    assert journey.ranged.header("Content-Range") == f"bytes 0-1023/{EXPECTED_BYTE_SIZE}"
    assert journey.ranged.body == BASELINE_PDF.read_bytes()[:1024]


def test_c3_no_response_ever_discloses_a_bucket_a_key_or_a_storage_url(
    journey: Journey,
) -> None:
    """The private object stays private in the only sense the API can be held to.

    ``make check-storage`` proves the bucket denies anonymous access. What the front door
    must add is that it never hands a caller the internal address either -- no presigned
    link, no endpoint, no bucket name -- because such a URL outlives the request that
    authorised it.
    """
    import os

    bucket = os.environ["S3_BUCKET"]
    endpoint = os.environ["S3_ENDPOINT_URL"]
    rendered = json.dumps([journey.version, journey.version_read, journey.status])
    for forbidden in (bucket, endpoint, "s3://", "X-Amz-Signature", "presigned"):
        assert forbidden not in rendered, (
            f"a response disclosed {forbidden!r}; the internal address of an object is "
            "never part of this surface"
        )


def test_c3_the_manifest_records_the_source_document_under_its_contract_role(
    journey: Journey,
) -> None:
    entries = journey.version["input_manifest"]
    assert [e["role"] for e in entries] == ["source.document"]
    assert entries[0]["sha256"] == EXPECTED_SHA256
    assert entries[0]["size_bytes"] == EXPECTED_BYTE_SIZE


def test_c3_the_surface_declares_no_operation_that_can_mutate_a_version(
    journey: Journey, client: Client
) -> None:
    """Immutability, as the front door can be held to it.

    The database refuses UPDATE and DELETE on ``document_version`` with SQLSTATE AM003.
    The API's own half of that promise is that it offers no way to ask: a caller that
    wanted to edit a published version would have to find a route, and there is none.
    """
    mutating = {
        route.operation_id
        for route in client.app.router.routes
        if route.methods & {"PUT", "PATCH", "DELETE"}
    }
    assert mutating == set(), mutating
    # Addressed at the version that really exists, so a 404 here can only mean "no such
    # route" and never "no such resource" -- which is the whole point of the assertion.
    assert client.get_version(journey.version_uid).status == 200
    for method in ("PUT", "PATCH", "DELETE"):
        answer = client.request(method, f"/versions/{journey.version_uid}")
        assert answer.status == 404, (
            f"{method} on an existing version answered {answer.status}; the surface must "
            "not admit a mutating method on an immutable aggregate"
        )


def test_c3_a_second_upload_publishes_a_new_identity_and_leaves_the_first_untouched(
    journey: Journey, client: Client
) -> None:
    """A re-upload is a new immutable identity, never a mutation of the old one.

    Re-uploading under a *different* idempotency key is a different command, so it must
    mint a new identity -- and the first must come back unchanged afterwards. Re-reading
    the first version after the second upload is the half that matters: without it this
    would prove only that two identities were minted, not that the earlier one survived.

    Measured, not assumed: ``uploadDocument`` creates a **new document** each time, so the
    second upload is version 1 of a second document rather than version 2 of the first.
    ``version_ordinal`` is therefore always 1 on this surface -- no operation in the frozen
    twelve can add a version to an existing document -- and that is reported as an
    observation rather than asserted away here.
    """
    answer = client.upload_document(
        project_uid=journey.project_uid,
        content=BASELINE_PDF.read_bytes(),
        key=key("upload-second"),
    )
    assert answer.status == 201, answer.body
    second = answer.json
    assert second["version_uid"] != journey.version_uid
    assert second["document_uid"] != journey.version["document_uid"]
    assert second["project_uid"] == journey.project_uid
    assert second["sha256"] == EXPECTED_SHA256
    assert second["version_ordinal"] == 1

    reread = client.get_version(journey.version_uid)
    assert reread.status == 200
    assert reread.json == journey.version_read, (
        "publishing a second version changed the first one"
    )


# ======================================================================================
# Criterion 4 -- the deterministic path and text_analysis, with the states distinguishable
# ======================================================================================


def test_c4_the_run_reaches_published_with_an_empty_degradation_set(
    journey: Journey,
) -> None:
    """``published`` is the success terminal of an AuditRun.

    ``succeeded`` is a StageResult status on a different aggregate and is never a run
    state; the two are asserted separately below for exactly that reason.
    """
    assert journey.status["state"] == "published", journey.status
    assert journey.status["degradation_set"] == []


def test_c4_all_four_pc01_stages_are_reported_succeeded_through_the_api(
    journey: Journey,
) -> None:
    """The stage states a reviewer can actually see.

    This is the assertion that catches a RunStatus whose ``stages`` is permanently empty:
    an empty list is falsy and a membership test over it would pass vacuously, so the
    stage-id set is compared for equality against the frozen four.
    """
    stages = journey.status.get("stages", [])
    observed = {stage["stage_id"]: stage["status"] for stage in stages}
    assert set(observed) == EXPECTED_STAGES, (
        f"the API reported stages {sorted(observed)}; PC-01 declares "
        f"{sorted(EXPECTED_STAGES)}. A RunStatus that carries no stage states cannot "
        "distinguish a deterministic-path failure from an analysis failure."
    )
    assert set(observed.values()) == {"succeeded"}, observed


def test_c4_the_run_states_the_ui_must_distinguish_are_the_frozen_enum(
    client: Client,
) -> None:
    """The vocabulary itself, asserted against the contract rather than restated."""
    document = json.loads(OPENAPI.read_text("utf-8"))
    schemas = document["components"]["schemas"]
    # RunStatus.state is a $ref; following it rather than restating the target's name is
    # what keeps this test honest if the document ever inlines or renames the enum.
    ref = schemas["RunStatus"]["properties"]["state"]["$ref"]
    assert ref.startswith("#/components/schemas/"), ref
    declared = set(schemas[ref.rsplit("/", 1)[1]]["enum"])
    required = {"queued", "running", "validating", "published", "partial", "failed"}
    assert required <= declared, declared
    assert "succeeded" not in declared, (
        "succeeded is a StageResult status; a run that could report it would make the "
        "two aggregates indistinguishable to a reviewer"
    )


def test_c4_the_run_reports_the_provider_mode_it_actually_used(journey: Journey) -> None:
    """A recorded run must present itself as recorded.

    The composition root translates the ``proxy`` transport to the ``live`` provenance,
    and this is the assertion that would catch that translation reaching ``recorded``.
    """
    assert journey.status["provider_mode"] == "recorded"
    assert journey.status["analysis_profile_id"].startswith("ap_")
    assert journey.status["prompt_bundle_id"].startswith("pb_")


def test_c4_a_caller_cannot_talk_a_recorded_deployment_into_reporting_live(
    journey: Journey, client: Client
) -> None:
    """Asking for a mode the deployment does not provide is refused, never substituted.

    Silently substituting would publish a recorded run under a live badge, which is the
    failure one level down that ``B-III`` found.
    """
    answer = client.start_run(
        version_uid=journey.version_uid, key=key("run-live", unique=True), provider_mode="live"
    )
    assert answer.status == 422, answer.body
    assert answer.error_code == "validation_failed", answer.body


# ======================================================================================
# Criterion 5 -- seeded issues found, and every published quotation on its declared page
# ======================================================================================


def test_c5_the_run_publishes_the_findings_the_corpus_seeds(journey: Journey) -> None:
    assert len(journey.findings) == EXPECTED_FINDING_COUNT, (
        f"expected {EXPECTED_FINDING_COUNT} published findings, got "
        f"{len(journey.findings)}: {[f['category'] for f in journey.findings]}"
    )
    categories = sorted(f["category"] for f in journey.findings)
    assert categories == ["explicit_placeholder", "internal_contradiction", "internal_contradiction"]


def test_c5_every_published_quotation_exists_on_its_declared_page(
    journey: Journey, page_texts: tuple[str, ...]
) -> None:
    """The acceptance oracle, checked against the file bytes rather than against the run.

    ``page_texts`` is pinned to the manifest's ``page_text_sha256`` in the fixture, so a
    quotation that resolves here resolves in the corpus and not merely in whatever the
    extractor produced today. The count is asserted too: a run that published no evidence
    at all would satisfy a bare "every quotation resolves" loop vacuously.
    """
    checked = 0
    for finding in journey.findings:
        evidence = finding["observation"]["evidence"]
        assert evidence, f"finding {finding['finding_uid']} published no evidence"
        for item in evidence:
            page = item["page_number"]
            assert 1 <= page <= len(page_texts), f"page {page} is outside the document"
            quote = item["quote"]
            assert quote, "a published evidence item carries an empty quotation"
            assert quote in page_texts[page - 1], (
                f"finding {finding['finding_uid']} evidence {item['evidence_ordinal']} "
                f"quotes {quote!r} as page {page}, and that page's text does not contain it"
            )
            checked += 1
    assert checked >= 2, f"only {checked} quotations were checked"


def test_c5_the_findings_name_pages_the_corpus_seeds_issues_on(
    journey: Journey, manifest: Mapping[str, Any]
) -> None:
    """At least two seeded issues are actually located, not merely counted.

    Matching on the *pages* the manifest declares rather than on free text: a run that
    published three findings about the wrong pages would pass a bare count.
    """
    seeded_pages = {
        issue["id"]: set(issue["pages"]) for issue in manifest["seeded_issues"]
    }
    published_pages = {
        item["page_number"]
        for finding in journey.findings
        for item in finding["observation"]["evidence"]
    }
    located = {
        issue_id
        for issue_id, pages in seeded_pages.items()
        if pages & published_pages
    }
    assert len(located) >= 2, (
        f"the run's evidence pages {sorted(published_pages)} locate only {sorted(located)} "
        f"of the seeded issues {sorted(seeded_pages)}"
    )


def test_c5_the_evidence_offsets_are_consistent_with_the_quotations_they_anchor(
    journey: Journey,
) -> None:
    """``char_start``/``char_end`` are checked, not merely carried.

    The frozen ``Evidence`` schema says these index *the document-global character
    sequence of the prepared text layer*, not the page text, so they cannot be resolved
    against the corpus extractor. Two properties are checkable from outside and both
    catch a real class of defect: the span has to be exactly as long as the quotation it
    claims to anchor, and a document-global sequence has to run in page order.

    The second is what makes this more than arithmetic. Offsets that had been computed
    per page, or against a text layer assembled in the wrong order, would still satisfy
    the length check and would show up here as pages out of sequence.
    """
    anchors = [
        (item["char_start"], item["char_end"], item["page_number"], item["quote"])
        for finding in journey.findings
        for item in finding["observation"]["evidence"]
    ]
    assert len(anchors) >= 2, f"only {len(anchors)} anchors to check"
    for start, end, page, quote in anchors:
        assert 0 <= start < end, (start, end)
        assert end - start == len(quote), (
            f"the anchor {start}:{end} spans {end - start} characters and the quotation "
            f"it carries is {len(quote)} long: {quote!r}"
        )
    ordered = sorted(anchors)
    pages = [page for _, _, page, _ in ordered]
    assert pages == sorted(pages), (
        f"document-global offsets run {pages} against page order; the text layer these "
        "anchors index is not assembled in page sequence"
    )
    starts = [start for start, _, _, _ in ordered]
    assert len(set(starts)) == len(starts), "two anchors claim the same start offset"


# ======================================================================================
# Criterion 6 -- open the page from a finding, accept one, reject another, comment later
# ======================================================================================


def test_c6_a_finding_leads_to_the_page_it_cites(journey: Journey, client: Client) -> None:
    """The reviewer's move: from a finding to the bytes of the page it quotes.

    The API addresses content by version, not by page, so "opening the page" is the
    version's content plus the finding's page number. Asserting the streamed bytes are the
    published object keeps the two ends tied together.
    """
    finding = journey.findings[0]
    evidence = finding["observation"]["evidence"][0]
    assert finding["version_uid"] == journey.version_uid
    answer = client.stream_content(finding["version_uid"])
    assert answer.status == 200
    assert hashlib.sha256(answer.body).hexdigest() == journey.version["sha256"]
    assert 1 <= evidence["page_number"] <= journey.version["page_count"]


def test_c6_the_detail_view_carries_the_exact_quotation(journey: Journey) -> None:
    listed = journey.findings[0]["observation"]["evidence"]
    detailed = journey.detail["observation"]["evidence"]
    assert [e["quote"] for e in detailed] == [e["quote"] for e in listed]
    assert [e["page_number"] for e in detailed] == [e["page_number"] for e in listed]


def test_c6_one_finding_is_accepted_and_another_rejected(journey: Journey) -> None:
    assert journey.accepted["current_verdict"] == "accepted"
    assert journey.accepted["event"]["event_type"] == "accept"
    assert journey.rejected["current_verdict"] == "rejected"
    assert journey.rejected["event"]["event_type"] == "reject"
    assert (
        journey.accepted["event"]["finding_uid"] != journey.rejected["event"]["finding_uid"]
    )


def test_c6_a_later_comment_appends_without_overwriting_the_history(
    journey: Journey,
) -> None:
    """The ledger keeps both events, in order, and the accept still stands.

    The trap this avoids: asserting only that the history has two rows. A store that
    replaced the accept with the comment and kept a stale copy would still show two, so
    the assertion is on the *sequence* of event types and on the verdict the accept
    established surviving the comment.
    """
    types = [event["event_type"] for event in journey.history]
    assert types == ["accept", "comment"], types
    assert journey.history[0]["decision_id"] == journey.accepted["event"]["decision_id"]
    assert journey.history[1]["decision_id"] == journey.commented["event"]["decision_id"]
    assert journey.history[0]["recorded_at"] <= journey.history[1]["recorded_at"]
    assert journey.commented["current_verdict"] == "accepted", (
        "a comment changed the verdict; a comment is not a verdict event"
    )
    assert journey.history[1]["comment"], "the appended comment lost its text"


def test_c6_the_decision_ledger_admits_no_update_or_delete(client: Client) -> None:
    """There is no route that could overwrite history, and that is checked as a set."""
    routes = {
        (method, route.path)
        for route in client.app.router.routes
        for method in route.methods
    }
    assert ("POST", "/findings/{finding_uid}/decisions") in routes
    for method in ("PUT", "PATCH", "DELETE"):
        assert (method, "/findings/{finding_uid}/decisions") not in routes


# ======================================================================================
# Criterion 7 -- a UTF-8 CSV whose rows resolve to the exact aggregates
# ======================================================================================


def _csv_rows(payload: bytes) -> list[dict[str, str]]:
    text = payload.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def test_c7_the_export_is_utf8_with_the_frozen_column_set(journey: Journey) -> None:
    assert journey.csv_bytes.startswith(b"\xef\xbb\xbf"), "the CSV carries no UTF-8 BOM"
    decoded = journey.csv_bytes.decode("utf-8-sig")
    header = next(csv.reader(io.StringIO(decoded)))
    assert len(header) == EXPECTED_CSV_COLUMNS, header
    assert header[:6] == [
        "project_uid",
        "document_uid",
        "version_uid",
        "run_id",
        "run_state",
        "provider_mode",
    ]


def test_c7_the_export_has_one_row_per_published_evidence_item(journey: Journey) -> None:
    rows = _csv_rows(journey.csv_bytes)
    assert len(rows) == EXPECTED_CSV_ROWS, len(rows)
    evidence_count = sum(
        len(f["observation"]["evidence"]) for f in journey.findings
    )
    assert len(rows) == evidence_count, (
        f"{len(rows)} CSV rows against {evidence_count} published evidence items"
    )


def test_c7_every_row_resolves_to_the_exact_aggregates_it_names(journey: Journey) -> None:
    """Each row is matched back to the objects the router returned, field by field.

    Comparing against the router's own answers rather than against a re-read of the
    database: the claim is that a reviewer holding this CSV can resolve it through the
    API, and that is only proved by resolving it through the API.
    """
    rows = _csv_rows(journey.csv_bytes)
    by_observation = {
        f["observation"]["finding_observation_id"]: f for f in journey.findings
    }
    quotes_seen: set[tuple[str, str]] = set()
    for row in rows:
        assert row["project_uid"] == journey.project_uid
        assert row["version_uid"] == journey.version_uid
        assert row["run_id"] == journey.run_id
        assert row["run_state"] == journey.status["state"]
        assert row["provider_mode"] == journey.status["provider_mode"]
        finding = by_observation[row["finding_observation_id"]]
        assert row["finding_uid"] == finding["finding_uid"]
        assert row["category"] == finding["category"]
        quotes = {e["quote"] for e in finding["observation"]["evidence"]}
        assert row["evidence_quote"] in quotes, row["evidence_quote"]
        quotes_seen.add((row["finding_uid"], row["evidence_quote"]))
    assert len(quotes_seen) == EXPECTED_CSV_ROWS, (
        "two rows carried the same finding and quotation; the export is not one row per "
        "evidence item"
    )


def test_c7_the_verdict_column_carries_the_current_verdict(
    journey: Journey, client: Client
) -> None:
    """The CSV's verdict is compared against a *fresh* read, not against the journey's.

    A CSV rendered from a stale snapshot would agree with the verdicts the journey
    recorded and disagree with the ones the API reports now.
    """
    answer = client.run_findings(journey.run_id)
    assert answer.status == 200
    current = {f["finding_uid"]: f["current_verdict"] for f in answer.json["items"]}
    assert set(current.values()) >= {"accepted", "rejected"}, current
    for row in _csv_rows(journey.csv_bytes):
        assert row["current_verdict"] == current[row["finding_uid"]], row


def test_c7_two_exports_of_one_run_are_byte_identical(journey: Journey) -> None:
    assert journey.csv_bytes == journey.csv_repeat


def test_c7_a_non_ascii_quotation_survives_the_round_trip(journey: Journey) -> None:
    """The corpus is Russian; a CSV that mangled it would still have the right shape.

    Asserting that at least one row carries a character outside ASCII is what stops this
    from passing against an export that had silently transliterated or dropped the text.
    """
    rows = _csv_rows(journey.csv_bytes)
    non_ascii = [r for r in rows if any(ord(c) > 127 for c in r["evidence_quote"])]
    assert non_ascii, "no exported quotation carried a non-ASCII character"
    for row in non_ascii:
        finding = next(
            f
            for f in journey.findings
            if f["observation"]["finding_observation_id"] == row["finding_observation_id"]
        )
        assert row["evidence_quote"] in {
            e["quote"] for e in finding["observation"]["evidence"]
        }


# ======================================================================================
# Criterion 8 -- restart without losing canonical state
# ======================================================================================


def test_c8_a_freshly_composed_application_reports_the_same_canonical_state(
    journey: Journey, client: Client
) -> None:
    """A second composition root: new engine, new sessions, new adapters, new router.

    This is the closest thing to a process restart a test can perform in-process, and it
    is a real one -- the identity checks below are what make it so. Without them this
    would be a second look at the same objects, and a store that kept everything in a
    session identity map would pass.
    """
    restarted = build_client(AUDITMANAGER_PROVIDER_MODE="recorded")
    assert restarted.app is not client.app
    assert restarted.app.router is not client.app.router
    assert restarted.app.session_factory is not client.app.session_factory

    status = restarted.run_status(journey.run_id)
    assert status.status == 200, status.body
    assert status.json["state"] == journey.status["state"]
    assert status.json["run_id"] == journey.run_id

    version = restarted.get_version(journey.version_uid)
    assert version.status == 200
    assert version.json["sha256"] == EXPECTED_SHA256

    findings = restarted.run_findings(journey.run_id)
    assert findings.status == 200
    assert [f["finding_uid"] for f in findings.json["items"]] == [
        f["finding_uid"] for f in journey.findings
    ]

    history = restarted.decision_history(journey.findings[0]["finding_uid"])
    assert history.status == 200
    assert [e["decision_id"] for e in history.json["items"]] == [
        e["decision_id"] for e in journey.history
    ]

    export = restarted.export_csv(journey.run_id)
    assert export.status == 200
    assert export.body == journey.csv_bytes, (
        "the export after a restart differs from the export before it"
    )


def test_c8_the_stored_object_survives_a_restart_byte_for_byte(journey: Journey) -> None:
    restarted = build_client(AUDITMANAGER_PROVIDER_MODE="recorded")
    answer = restarted.stream_content(journey.version_uid)
    assert answer.status == 200
    assert answer.body == journey.content
    assert hashlib.sha256(answer.body).hexdigest() == EXPECTED_SHA256


# ======================================================================================
# Criterion 9 -- the same commands under the same idempotency keys create no duplicates
# ======================================================================================


def test_c9_a_write_without_an_idempotency_key_is_refused(
    journey: Journey, client: Client
) -> None:
    """The header is required, and the router never invents one.

    A generated key would make every retry a fresh command, silently -- which is exactly
    the failure the header exists to prevent.
    """
    answer = client.request(
        "POST",
        "/projects",
        headers={"Content-Type": "application/json"},
        body=json.dumps({"name": "no key"}).encode("utf-8"),
    )
    assert answer.status == 422
    assert answer.error_code == "validation_failed"


def test_c9_replaying_the_project_command_returns_the_same_project(
    journey: Journey, client: Client
) -> None:
    before = client.list_projects("?limit=200")
    answer = client.create_project(
        name=f"C2 PC-01 {key('project')}", key=key("project")
    )
    assert answer.status in (200, 201), answer.body
    assert answer.json["project_uid"] == journey.project_uid, (
        "the same Idempotency-Key produced a second project identity"
    )
    after = client.list_projects("?limit=200")
    assert _uids(after, "project_uid") == _uids(before, "project_uid")


def _uids(answer: Answer, field_name: str) -> list[str]:
    return [item[field_name] for item in answer.json["items"]]


def test_c9_replaying_the_upload_command_publishes_no_second_version(
    journey: Journey, client: Client
) -> None:
    """The same key and the same bytes resolve to the version already published.

    Distinct from ``test_c3_a_second_upload...`` on purpose: that one uses a *different*
    key and must create a second version. The pair is what shows the key is doing the
    work rather than the content digest.
    """
    answer = client.upload_document(
        project_uid=journey.project_uid,
        content=BASELINE_PDF.read_bytes(),
        key=key("upload"),
    )
    assert answer.status in (200, 201), answer.body
    assert answer.json["version_uid"] == journey.version_uid
    assert answer.json["version_ordinal"] == journey.version["version_ordinal"]


def test_c9_replaying_the_run_command_creates_no_second_run(
    journey: Journey, client: Client
) -> None:
    answer = client.start_run(version_uid=journey.version_uid, key=key("run"))
    assert answer.status in (200, 202), answer.body
    assert answer.json["run_id"] == journey.run_id
    findings = client.run_findings(journey.run_id)
    assert len(findings.json["items"]) == EXPECTED_FINDING_COUNT, (
        "a replayed run re-published its findings"
    )


def test_c9_replaying_the_decision_command_appends_no_second_event(
    journey: Journey, client: Client
) -> None:
    finding = journey.findings[0]
    answer = client.append_decision(
        finding_uid=finding["finding_uid"],
        observation_id=finding["observation"]["finding_observation_id"],
        event_type="accept",
        key=key("accept"),
    )
    assert answer.status in (200, 201), answer.body
    assert answer.json["event"]["decision_id"] == journey.accepted["event"]["decision_id"]
    history = client.decision_history(finding["finding_uid"])
    assert [e["decision_id"] for e in history.json["items"]] == [
        e["decision_id"] for e in journey.history
    ], "a replayed decision lengthened the ledger"


def test_c9_a_reused_key_carrying_a_different_payload_is_refused(
    journey: Journey, client: Client
) -> None:
    """Idempotency is a promise about one command, not a cache keyed on a header.

    Without this, a key that replayed *any* body would look identical to a correct
    implementation in every test above.
    """
    answer = client.create_project(name="a different name entirely", key=key("project"))
    assert answer.status == 409, answer.body
    assert answer.error_code in {
        "idempotency_key_reuse",
        "idempotency_key_stale",
        "conflict",
    }, answer.body


# ======================================================================================
# Criterion 10 -- explicit failures, no filesystem fallback, no fake success
# ======================================================================================


@pytest.mark.parametrize(
    ("fixture_name", "filename"),
    [
        ("not_a_pdf.txt", "notes.txt"),
        ("encrypted.pdf", "encrypted.pdf"),
        ("image_only.pdf", "image_only.pdf"),
        ("too_many_pages.pdf", "too_many_pages.pdf"),
        ("companion_archive.zip", "companion.zip"),
    ],
)
def test_c10_unsupported_input_is_refused_with_a_typed_code(
    journey: Journey, client: Client, fixture_name: str, filename: str
) -> None:
    """Each negative fixture is refused, and nothing canonical is left behind.

    The second half is the one that matters: a refusal that had already published a
    version would still produce the right status code.
    """
    before = client.request("GET", f"/versions/{journey.version_uid}")
    answer = client.upload_document(
        project_uid=journey.project_uid,
        content=(NEGATIVE / fixture_name).read_bytes(),
        key=key(f"neg-{fixture_name}", unique=True),
        filename=filename,
    )
    assert answer.status >= 400, (
        f"{fixture_name} was accepted; the envelope rules it out"
    )
    assert answer.status != 500, (
        f"{fixture_name} produced an unclassified internal_error rather than an explicit "
        f"refusal: {answer.body!r}"
    )
    assert answer.error_code in {
        "validation_failed",
        "analysis_input_invalid",
        "storage_integrity_error",
    }, answer.body
    assert answer.header("X-Correlation-Id"), "a refusal carried no correlation id"
    after = client.request("GET", f"/versions/{journey.version_uid}")
    assert after.json == before.json, "a refused upload disturbed the published version"


def test_c10_an_oversize_upload_is_refused_rather_than_truncated(
    journey: Journey, client: Client
) -> None:
    """Separated from the parametrised cases because the refusal is a size rule.

    A server that accepted and truncated would publish a version, which is why the
    assertion is on the absence of a new identity and not only on the status.
    """
    answer = client.upload_document(
        project_uid=journey.project_uid,
        content=(NEGATIVE / "oversize.pdf").read_bytes(),
        key=key("neg-oversize", unique=True),
        filename="oversize.pdf",
    )
    assert answer.status >= 400, answer.body
    assert answer.status != 500, answer.body
    assert "version_uid" not in answer.body.decode("utf-8", "replace")


def test_c10_an_unavailable_provider_fails_the_run_explicitly(journey: Journey) -> None:
    """A model that cannot be reached is a typed failure, never a quiet recorded answer.

    The deployment is composed against a proxy address with nothing listening. The
    assertions that matter are the negative ones: the run must not reach ``published``,
    and it must publish nothing, because a published finding that no model produced is
    the fake success criterion 10 forbids.

    This docstring used to record two observations rather than assert them, because
    correcting them belonged to the owning trees: the failed stage carried
    ``error_code: null`` and the run's ``terminal_reason`` was ``analysis_failed``, so an
    unreachable provider -- which the catalog calls ``dependency_unavailable`` and marks
    retryable -- was reported as a non-retryable analysis failure.

    **Wave 3 fixed both, and this text went on describing the defect for three waves.**
    `W6-CERT` found it. A recorded observation drifts silently in whichever direction the
    code moves; the same shape as `W2-QA` pinning a stale value, pointing the other way.
    So the observations are now assertions. They cannot go stale again without failing.
    """
    unavailable = build_client(
        AUDITMANAGER_PROVIDER_MODE="proxy",
        PROXY_LLM_BASE_URL="http://127.0.0.1:1",
        PROXY_LLM_TOKEN="c2-acceptance-not-a-real-token",
        PROXY_LLM_MODEL="anthropic/claude-opus-5",
    )
    answer = unavailable.start_run(
        version_uid=journey.version_uid,
        key=key("run-unavailable", unique=True),
        provider_mode="live",
    )
    if answer.status not in (200, 202):
        assert answer.error_code in {"dependency_unavailable", "analysis_failed"}, answer.body
        return

    run_id = answer.json["run_id"]
    # `D-20`. The provider is unreachable and the retry budget is spent on a carrier
    # thread, so the terminal this criterion reads only exists once that thread is done.
    unavailable.await_runs()
    status = unavailable.run_status(run_id)
    assert status.status == 200, status.body
    state = status.json["state"]
    assert state != "published", (
        "a run whose provider was unreachable reported itself published"
    )
    assert state == "failed", state
    assert status.json["degradation_set"] == ["text_analysis"], status.json

    stages = {s["stage_id"]: s["status"] for s in status.json["stages"]}
    assert stages["text_analysis"] == "failed", stages
    # The deterministic path still ran and is still reported as having run. A failure
    # that erased the successful stages would make a provider outage indistinguishable
    # from a document the pipeline could not read at all.
    assert stages["source_preparation"] == "succeeded", stages
    assert stages["page_geometry_extraction"] == "succeeded", stages
    assert stages["document_context_build"] == "succeeded", stages

    findings = unavailable.run_findings(run_id)
    assert findings.status == 200
    assert findings.json["items"] == [], (
        "a run that could not reach a model published findings anyway"
    )

    # What the failure *was*, not merely that there was one. The catalog marks
    # `analysis_failed` not retryable and `dependency_unavailable` retryable, so an
    # operator reading this run has to be able to tell a model that answered badly from a
    # provider that never answered -- and here nothing was listening on port 1.
    assert status.json["terminal_reason"] == "dependency_unavailable", (
        "the provider was unreachable, so reporting a generic analysis failure tells an "
        f"operator the run is not worth retrying when it is: {status.json['terminal_reason']!r}"
    )
    # `StageState.error_code` in the frozen document: "The typed reason a non-succeeded
    # stage carries. Null exactly when the status is `succeeded`." So a failed stage with
    # a null code is a contract violation, not a display preference.
    stage_codes = {s["stage_id"]: s.get("error_code") for s in status.json["stages"]}
    assert stage_codes.get("text_analysis") == "dependency_unavailable", (
        "the failed stage must name its own cause; the frozen document says error_code is "
        f"null exactly when the status is succeeded: {stage_codes!r}"
    )


def test_c10_a_missing_credential_refuses_to_start_rather_than_fail_later() -> None:
    """No fake success at the other end either: the process will not come up half-wired.

    A deployment that started without a credential would accept an upload and only then
    discover it could not analyse anything -- after a document had been stored and a run
    row written.
    """
    from auditmanager.api.composition import ConfigurationError

    with pytest.raises(ConfigurationError):
        build_client(AUDITMANAGER_PROVIDER_MODE="live", ANTHROPIC_API_KEY="")
    with pytest.raises(ConfigurationError):
        build_client(
            AUDITMANAGER_PROVIDER_MODE="proxy",
            PROXY_LLM_BASE_URL="https://example.invalid",
            PROXY_LLM_TOKEN="",
        )


def test_c10_an_unknown_identity_is_not_found_and_discloses_nothing(
    client: Client,
) -> None:
    """A malformed identity and a well-formed absent one answer alike.

    Answering 422 for a bad prefix and 404 for a good one would let a caller use the API
    as an oracle for which identifier shapes are real.
    """
    malformed = client.run_status("not-an-identity")
    absent = client.run_status("run_01M2FEV82PYPTDNKF5N58PQAJZ")
    assert malformed.status == absent.status == 404
    assert malformed.error_code == absent.error_code == "not_found"
    for answer in (malformed, absent):
        body = answer.body.decode("utf-8")
        assert "Traceback" not in body and "SELECT" not in body and "psycopg" not in body


def test_c10_every_failure_leaves_the_edge_as_one_typed_envelope(client: Client) -> None:
    """There is no route out of the edge that returns an untyped body.

    Four different shapes of failure are driven -- no route, wrong method, malformed
    body, unknown resource -- because a middleware that typed only the paths its author
    remembered would pass a test that drove one of them.
    """
    cases = [
        client.request("GET", "/no-such-operation"),
        client.request("DELETE", "/projects"),
        client.request(
            "POST",
            "/projects",
            headers={"Idempotency-Key": key("bad-body", unique=True)},
            body=b"{not json",
        ),
        client.finding("fnd_01M2FEV8HSHVWKY6EQY3W8ZJRZ"),
    ]
    for answer in cases:
        assert answer.status >= 400, answer.body
        payload = answer.json
        assert set(payload) >= {
            "contract_version",
            "error_code",
            "message",
            "correlation_id",
            "retryable",
        }, payload
        assert payload["contract_version"] == "1.0.0-draft.1"
        assert isinstance(payload["retryable"], bool)
        assert answer.header("X-Correlation-Id") == payload["correlation_id"]
