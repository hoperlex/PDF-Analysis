"""Two things `T-1` and `T-3` leave that no other suite is the home of.

* **the served document is the one the gate compares.** ``W13-CONF``'s conformance gate
  reads ``create_documentation_app().openapi()``, which builds the eighteen operations with
  nothing behind the ports so that a document can be read on any checkout, without a
  database, an object store or a credential. That is only worth anything if it is the
  *same* document the wired application serves. Asserted here, because the gate cannot
  assert it -- ``tests/contract/api_v1/**`` is tests-only and has no wired application.
* **the health plane of `T-3` is a different application.** Liveness and readiness answer
  on a second port, never under ``/api/v1``, and **outside the authorized surface** so a
  health check needs no credential. `W13-SEAL` section 8.3: *if it inherits an app-wide
  dependency it stops answering and wave 14 discovers that in a deployment.*
"""

from __future__ import annotations

from tests.support.expected_facts import FACTS

import json
from pathlib import Path
from typing import Any

from starlette.testclient import TestClient

from auditmanager.api.app import create_documentation_app
from auditmanager.api.health import LIVENESS_PATH, READINESS_PATH, build_health_app
from w13_api_driver import Surface

OPENAPI = Path(__file__).resolve().parents[3] / "contracts/api/v1/openapi.json"

#: The three figures, as literals. ``OPERATING_CONSTRAINTS.md`` section 12: a count read
#: from the document it is counting cannot tell you the document shrank.
OPENAPI_VERSION = "3.1.0"
BASE_PATH = "/api/v1"
PATH_COUNT = FACTS.path_count
OPERATION_COUNT = FACTS.operation_count
SCHEMA_COUNT = FACTS.schema_count


class TestTheDocumentedAndTheWiredApplicationAgree:
    def test_the_documented_and_the_wired_app_agree(self, router: Surface) -> None:
        """The same bytes, from an application with ports and one without.

        If these ever diverged, the conformance gate would be comparing the frozen
        contract against a document nothing serves -- which is the most expensive kind of
        green this programme has a name for.
        """
        wired = router.app.openapi()
        documented = create_documentation_app().openapi()
        assert json.dumps(wired, sort_keys=True) == json.dumps(documented, sort_keys=True)

    def test_the_served_document_is_the_shape_the_contract_is(self) -> None:
        document = create_documentation_app().openapi()
        assert document["openapi"] == OPENAPI_VERSION
        assert [server["url"] for server in document["servers"]] == [BASE_PATH]
        assert len(document["paths"]) == PATH_COUNT
        operations = [
            operation["operationId"]
            for path_item in document["paths"].values()
            for method, operation in path_item.items()
            if method in ("get", "post", "put", "patch", "delete")
        ]
        assert len(operations) == OPERATION_COUNT
        assert len(set(operations)) == OPERATION_COUNT, "an operationId is declared twice"
        assert len(document["components"]["schemas"]) == SCHEMA_COUNT

    def test_the_two_schemas_fastapi_would_have_added_are_not_in_it(self) -> None:
        """``HTTPValidationError`` and ``ValidationError``, and the 422 that referenced them.

        FastAPI injects a ``422`` for an operation with parameters that declares none of
        its own. The pinned set below names every operation that declares the catalog's
        validation envelope, including W53's query reads and commands. An operation
        outside that set must not acquire FastAPI's own validation schema.

        The three `R-5` listings are in the first group: each declares ``cursor`` and
        ``limit``, and a cursor that is not a continuation token from this API is
        ``validation_failed``. `W39-REVOKE`'s ``changePassword`` is too: it takes a body,
        and a body that is not the declared object is ``validation_failed``.

        **This docstring was the only correct statement of that figure in the tree.**
        ``api/app.py`` said *"Twelve of the seventeen"* for two reseals -- a number whose own
        arithmetic never summed to the surface, since twelve plus four is sixteen. It was
        repaired alongside this line rather than left to be found a third time.
        """
        document = create_documentation_app().openapi()
        schemas = document["components"]["schemas"]
        assert "HTTPValidationError" not in schemas
        assert "ValidationError" not in schemas
        rendered = json.dumps(document)
        assert "HTTPValidationError" not in rendered, "a dangling $ref was left behind"

        declared_422 = {
            operation["operationId"]
            for path_item in document["paths"].values()
            for method, operation in path_item.items()
            if method in ("get", "post", "put", "patch", "delete")
            and "422" in operation["responses"]
        }
        # Measured against `contracts/api/v1/openapi.json` 1.16.0 (`EXEC2-FIX-CMP-INVENTORY`): 185 of the 277 operations declare
        # the `422` envelope. Written out one by one, sorted, and not read back from the document under test. The earlier
        # literal held 142; the 43 it lacked are the operations of contracts 1.13.0 to 1.16.0 (the stage review, the executor
        # enrollment, install, group and routing operations, the cost estimates, the ZIP import and the technical report).
        # An operation is added here only when its contract declares the `422`; an operation that does not is still refused
        # FastAPI's own validation schema by the assertions above. Contract 1.17.0 (`UI-PARITY-P0A`) adds one, `getDashboardSummary`,
        # whose optional `project_uid` query parameter can be refused: 186. Contracts 1.22.0 to 1.27.0 (`UI-PARITY-P0G` to
        # `P0L`) add six: `setDocumentArchived`, `renameDocument`, `setDocumentTags`, `setFindingExecutionStatus`,
        # `listProposalDecisionJournal` and `importRunDecisions`: 192 of 285; 1.29.0 adds `getProject`: 193 of 286; 1.30.0 adds `listVersionSheetLabels`: 194 of 287; 1.31.0 adds the seven of «График работ»: 201 of 294; 1.32.0 adds `listKnowledgeBaseEntries`: 202 of 295; 1.35.0 adds `listAcceptedOptimisationProposals` and `importOptimisationProposalDecisions`: 204 of 298; 1.36.0 adds `endUserSessions` (the required `Idempotency-Key`) and `listAuthEvents` (the cursor and the limit): 206 of 300; 1.37.0 adds `carryOverProposalDecisions` (the required `Idempotency-Key` and the body): 207 of 301; 1.41.0 adds `listRunFindingBlocks`: 208 of 302; 1.42.0 adds `startRunFromStage`: 209 of 303; 1.44.0 adds the five of the decision memory, four of which can refuse a parameter or a body (`getDecisionMemoryStatus` takes none): 213 of 308.
        assert declared_422 == {
            "appendComparisonVersionOrder",
            "appendDecision",
            "applyComparisonMatrixEdits",
            "applyStageCardVerdicts",
            "applyStageSheetMap",
            "approveRegistration",
            "approveSheetPairing",
            "archiveAnalysisPreset",
            "archiveExecutorConnection",
            "archiveExecutorGroup",
            "cancelRun",
            "cancelStageChainBatch",
            "carryOverDecision",
            "carryOverProposalDecisions",
            "changePassword",
            "claimExecutorTask",
            "classifyDocumentVersion",
            "compareDocumentVersions",
            "completeComparisonUploadFile",
            "completeStageUploadFile",
            "confirmComparisonUploadSet",
            "confirmExecutorAgentInstallHostKey",
            "confirmStagePair",
            "confirmStageUploadCandidate",
            "continueComparisonReport",
            "correctVersionClassification",
            "createAnalysisPreset",
            "createAssignment",
            "createComparisonReport",
            "createComparisonUpload",
            "createExecutorAgentInstall",
            "createExecutorConnection",
            "createExecutorGroup",
            "createProject",
            "createStageAssembly",
            "createStageReviewCard",
            "createStageUpload",
            "decideOptimisationProposal",
            "downloadAgentPackage",
            "endUserSessions",
            "enqueueComparisonLaunch",
            "estimateComparisonAiSheetChanges",
            "estimateRunCost",
            "estimateStageChainRun",
            "exportRunXlsx",
            "extendExecutorTaskClaim",
            "failExecutorTask",
            "generateComparisonSummary",
            "generateExecutorSshKey",
            "getDashboardSummary",
            "getDecisionMemoryCase",
            "getEffectiveVendorLists",
            "getExecutorAgentInstall",
            "getExecutorConnection",
            "getExecutorGroup",
            "getExecutorGroupCapacity",
            "getExecutorTaskImage",
            "getProject",
            "getSectionSpecification",
            "getSpecificationPrices",
            "getStageAssembly",
            "getStageChainBatch",
            "getStageChangeCard",
            "getStageChangeJournal",
            "getStageProfileText",
            "getStageSynthesis",
            "getWorkSchedule",
            "getWorkScheduleReserve",
            "importComparisonZip",
            "importOptimisationProposalDecisions",
            "importRunDecisions",
            "issueExecutorEnrollment",
            "issueRunnerToken",
            "issueToken",
            "listAcceptedOptimisationProposals",
            "listAssignments",
            "listAuthEvents",
            "listComparisonAiLinks",
            "listComparisonAiPairHints",
            "listComparisonMatrixEdits",
            "listComparisonReports",
            "listComparisonReviewSheets",
            "listComparisonSeries",
            "listComparisonSheetDescriptionHistory",
            "listComparisonSheetPairs",
            "listComparisonSpecificationChanges",
            "listComparisonSpecifications",
            "listComparisonUploads",
            "listComparisonVersionOrders",
            "listDecisionHistory",
            "listDecisionMemoryCases",
            "listDecisions",
            "listDocuments",
            "listExecutionJournal",
            "listExecutionQueue",
            "listKnowledgeBaseEntries",
            "listNormDocuments",
            "listNormParagraphs",
            "listNormSnapshotEvents",
            "listNormSnapshots",
            "listOptimisationPasses",
            "listOptimisationProposals",
            "listPriceListPositions",
            "listPriceListRevisions",
            "listProjects",
            "listProposalDecisionJournal",
            "listRegistrations",
            "listRunFindingBlocks",
            "listRunFindings",
            "listRuns",
            "listStageAiReviews",
            "listStageCardVerdicts",
            "listStageChainRuns",
            "listStageChangeCards",
            "listStageClassifications",
            "listStageGraphicEvidence",
            "listStageLinkRepairs",
            "listStagePairSuggestions",
            "listStagePairs",
            "listStageRawDifferences",
            "listStageSheetMapHistory",
            "listStageSheetPassports",
            "listStageSheetSuggestions",
            "listStageTextExclusions",
            "listStageTextFragments",
            "listStageTextHints",
            "listStageUploads",
            "listUsers",
            "listVersionPageProfiles",
            "listVersionPortalBlocks",
            "listVersionSheetLabels",
            "listVersions",
            "listWorkers",
            "markReleaseNotesRead",
            "pauseStageChainBatch",
            "prepareComparisonClientReport",
            "readRegistrationStatus",
            "reauditRun",
            "recomputeStageTextEvidence",
            "redeemExecutorEnrollment",
            "rejectRegistration",
            "renameDocument",
            "reportRunnerHealth",
            "requestExecutorProbe",
            "resetUserPassword",
            "restoreDecisionMemoryCase",
            "resumeComparisonAiPairCheck",
            "resumeComparisonAiSheetChanges",
            "resumeStageChainBatch",
            "resumeStageChainRun",
            "retryComparisonAiSheetChanges",
            "reviseAnalysisPreset",
            "reviseExecutorConnection",
            "reviseExecutorGroup",
            "reviseStageAssembly",
            "revokeRunnerToken",
            "scheduleAssignments",
            "searchNorms",
            "setCurrentNormSnapshot",
            "setDocumentArchived",
            "setDocumentTags",
            "setEngineerAbsences",
            "setExecutionPaused",
            "setExecutorIntegrationAuthorisation",
            "setExecutorRoute",
            "setExecutorRoutingMode",
            "setExecutorRoutingRule",
            "setExecutorSecret",
            "setFindingExecutionStatus",
            "setGlobalVendorList",
            "setJobPriority",
            "setProjectVendorList",
            "setStagePairCompleteness",
            "setWorkCalendarDays",
            "setWorkSchedulePlans",
            "setWorkScheduleSettings",
            "setWorkerIntake",
            "startComparisonAiPairCheck",
            "startComparisonAiSheetChanges",
            "startComparisonReport",
            "startComparisonSeries",
            "startComparisonSheetDescription",
            "startComparisonSpecification",
            "startOptimisationPass",
            "startRun",
            "startRunFromStage",
            "startStageChainBatch",
            "startStageChainRun",
            "streamComparisonPairTile",
            "streamComparisonTechnicalReport",
            "streamDocumentVersionContent",
            "streamNormDocumentContent",
            "streamStageChangeJournalHtml",
            "streamStageChangeJournalPdf",
            "streamStageChangeJournalXlsx",
            "streamVersionPageTile",
            "submitExecutorTaskAnswer",
            "submitRegistration",
            "transitionAssignment",
            "undoComparisonMatrixEdit",
            "undoStageLinkRepair",
            "updateMyProfile",
            "updateUser",
            "uploadComparisonReportSource",
            "uploadComparisonUploadPart",
            "uploadDocument",
            "uploadDocumentVersion",
            "uploadPriceList",
            "uploadStageUploadPart",
            "withdrawDecisionMemoryCase",
            "withdrawSheetPairing",
        }, declared_422

    #: The only properties of the sealed contract (1.16.0) that declare a ``default``, with the value. Written out and not read back
    #: from the document under test. Each is a real server-side default and none is ``null``: `CMP-SEAL-C4` (commit 558f8cc5)
    #: gave the chain batch ``with_ai`` (``true``), the resume request ``retry_failed`` and the card evidence ``absence_proven``
    #: (``false``) and the change card ``carryover`` (``none``); the stage chain's ``engine`` (``classic``, beside
    #: ``v3_native_text_experimental``) came with the stage-V3 integration (commit af8c69f7, `HOTFIX-STAGE-V3-1030`). A new
    #: default, or a changed value, is a contract change and fails here until the seal that makes it writes it into this
    #: register.
    DECLARED_DEFAULTS = {
        ("ResumeStageChainRunRequest", "retry_failed"): False,
        ("StageCardEvidence", "absence_proven"): False,
        ("StageChainRun", "engine"): "classic",
        ("StageChangeCard", "carryover"): "none",
        ("StartStageChainBatchRequest", "engine"): "classic",
        ("StartStageChainBatchRequest", "with_ai"): True,
        ("StartStageChainRunRequest", "engine"): "classic",
    }

    def test_no_schema_property_declares_a_default(self) -> None:
        """The contract declares ``default`` on no property but the seven in :data:`DECLARED_DEFAULTS`, and none is ``null``.

        ``default: null`` on an optional property says the server substitutes ``null``,
        which is not what an absent property means here -- and the conformance gate
        compares ``default``. ``models.optional_property`` is the declaration of that
        intent; this is the property itself, pinned where a change in how FastAPI chooses
        to generate a schema would be caught whether or not that helper is still there.
        The register is the exact set the sealed contract carries, so the next default
        that appears -- in the contract or only in the served document -- is a failure.
        """
        def defaults(schemas: dict[str, Any]) -> dict[tuple[str, str], Any]:
            return {
                (name, prop): sub["default"]
                for name, schema in schemas.items()
                for prop, sub in (schema.get("properties") or {}).items()
                if "default" in sub
            }

        contract = defaults(json.loads(OPENAPI.read_text(encoding="utf-8"))["components"]["schemas"])
        assert contract == self.DECLARED_DEFAULTS, (
            f"the contract declares {sorted(set(contract) - set(self.DECLARED_DEFAULTS))} beyond the register, "
            f"and lacks {sorted(set(self.DECLARED_DEFAULTS) - set(contract))}"
        )
        assert None not in contract.values(), "a `default: null` says the server substitutes null"

        served = defaults(create_documentation_app().openapi()["components"]["schemas"])
        assert served == contract, (
            f"the served document differs from the contract in its defaults: "
            f"{sorted(set(served) ^ set(contract))}"
        )

    def test_a_declared_422_is_the_contracts_and_is_never_removed(self) -> None:
        """The removal is narrow, and this is what says so.

        It fires only when the response object is byte-for-byte FastAPI's injected one.
        The eight below declare ``ErrorEnvelope``, which is a different object, and every
        one of them survives.
        """
        contract = json.loads(OPENAPI.read_text(encoding="utf-8"))
        document = create_documentation_app().openapi()
        for path, path_item in contract["paths"].items():
            for method, operation in path_item.items():
                if (
                    method not in ("get", "post", "put", "patch", "delete")
                    or "422" not in operation["responses"]
                ):
                    continue
                served = document["paths"][path][method]["responses"]["422"]
                schema = served["content"]["application/json"]["schema"]
                assert schema == {"$ref": "#/components/schemas/ErrorEnvelope"}, (
                    operation["operationId"],
                    schema,
                )


class TestTheHealthPlaneIsOffTheContract:
    def test_it_answers_without_a_credential(self) -> None:
        """No ``Authorization`` header anywhere in this test. That is the whole point."""
        client = TestClient(build_health_app(object()))
        for path in (LIVENESS_PATH, READINESS_PATH):
            response = client.get(path)
            assert response.status_code == 200, (path, response.content)
            assert json.loads(response.content)["status"] == "ok"

    def test_it_is_not_a_route_on_the_api_application(self) -> None:
        """The contract declares twelve operations and these are not two of them."""
        document = create_documentation_app().openapi()
        assert LIVENESS_PATH not in document["paths"]
        assert READINESS_PATH not in document["paths"]
        assert not any(path.startswith("/health") for path in document["paths"])

    def test_it_publishes_no_document_of_its_own(self) -> None:
        """There is nothing here a client generates code from.

        A second OpenAPI document served by this deployment is a second thing a reader can
        mistake for the contract.
        """
        client = TestClient(build_health_app(None), raise_server_exceptions=False)
        for path in ("/openapi.json", "/docs", "/redoc"):
            assert client.get(path).status_code == 404, path

    def test_readiness_reports_whether_an_application_was_wired(self) -> None:
        """Not a constant. A readiness probe that returns ``ok`` unconditionally is a
        readiness probe that says nothing."""
        wired = TestClient(build_health_app(object())).get(READINESS_PATH)
        bare = TestClient(build_health_app(None)).get(READINESS_PATH)
        assert json.loads(wired.content)["wired"] is True
        assert json.loads(bare.content)["wired"] is False

    def test_the_two_paths_are_the_ones_the_deploy_script_will_poll(self) -> None:
        """Literals: wave 14's proxy configuration will carry these strings."""
        assert LIVENESS_PATH == "/healthz"
        assert READINESS_PATH == "/readyz"
