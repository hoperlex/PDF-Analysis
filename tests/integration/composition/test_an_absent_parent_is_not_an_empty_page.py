"""`D-67` -- one answer for an identity in a path that names nothing, across the surface.

`W37-CERT4` drove nine requests at the owner's stand with a well-formed 26-character ULID
that names nothing and found the surface answering two ways. Seven refused with
``404 not_found``; ``listRunFindings`` and the decision listing under a finding answered
``200`` with an empty page. **Neither answer is wrong on its own and having both is**: a
client reading an empty page cannot tell *"this run published no findings"* from *"there is
no such run"* on those two, and can everywhere else. `D-16` is what that costs on a screen.

**The rule, and it is the contract's rather than this session's.**

    A collection whose path carries a parent identity answers ``404 not_found`` when that
    identity names nothing. A collection whose path carries none answers ``200`` with the
    page it has, which may be empty.

The frozen document already says exactly this and says it operation by operation: every
one of the six ``GET`` collections with a placeholder in its path declares ``404``, and the
two with no placeholder -- ``listProjects`` and ``listDecisions`` -- declare none.
``listRunFindings`` and ``listDecisionHistory`` **declare a 404 they never produced**, so
what changed for them is conformance to a contract that was already frozen, not the
contract.

**Both halves are asserted here, because one alone is satisfiable by a wrong
implementation.** A surface that answered ``404`` for every empty collection would pass a
sweep that only looked for ``404``, and would destroy the distinction from the other side.
So the absent parent must refuse *and* the present-but-childless parent must answer an
empty page -- the second half in ``tests/integration/api``, where a run and a finding can
be published; this file holds the sweep, over the application the composition root builds.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from auditmanager.api.app import create_app, create_asgi_app
from auditmanager.api.security import API_TOKEN_VARIABLE
from auditmanager.runs.public import PACK_MANIFEST_ENV

#: This lane's deployment secret for this suite. A literal, as in every sibling suite.
DEPLOYMENT_SECRET = "absent-parent-sweep-token"

#: ``{parameter name: contract prefix}``, read from the frozen catalog rather than written
#: out here. A path parameter this file cannot resolve is an error and never a default:
#: filling ``{document_uid}`` with a ``prj_`` identity produces ``422 validation_failed``,
#: which is a refusal for the wrong reason and would read as agreement with the rule.
_CATALOG = Path(__file__).resolve().parents[3] / "contracts/domain/v1/identifiers.json"
_VERSION = Path(__file__).resolve().parents[3] / "VERSION"

#: A syntactically valid ULID. Crockford base32, 26 characters, and this deployment has
#: never minted it.
_ABSENT_ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"

#: The ``GET`` operations of the frozen surface: eleven addressing a parent identity, three
#: addressing none. A literal so that an operation added later cannot join the surface
#: without somebody deciding which half of the rule it belongs to. `W45-BLOCKS`'s
#: ``getVersionBlocks`` is the eleventh addressed one: it addresses ``version_uid`` and
#: answers ``404 not_found`` for one that names nothing, the same as every other addressed
#: `GET`. `W46-SEAL`'s ``getDashboardSummary`` is the third unaddressed one, and it is
#: **not** a third collection: see :data:`AGGREGATE_OPERATIONS` below for why this module's
#: rule -- "no parent identity means a page" -- does not extend to it.
#:
#: `W49-SEAL-01` added one addressed ``GET`` (``getUser``) and three unaddressed ones: two
#: collections (``listRegistrations``, ``listUsers``) and ``getMe``, which is neither a
#: collection nor an aggregate -- see :data:`SELF_OPERATIONS`.
#: `W52-SEAL-01` added two unaddressed GETs: ``getProductVersion`` and
#: ``listReleases``. Stage C now serves both from the release adapter.
# `W53-SEAL-01` added the two execution collection reads, both unaddressed.
# `W54-SEAL-01` added ``listWorkers``, an unaddressed collection (its intake switch is a PUT).
# `W55A-SEAL-01` added three addressed GETs (``getNormDocument``, ``listNormParagraphs``,
# ``streamNormDocumentContent``, all on ``norm_document_id``) and three unaddressed ones
# (``searchNorms``, ``listNormSnapshots``, ``listNormSnapshotEvents``).
# `W55B-SEAL-01` added two addressed GETs on `version_uid` (``listVersionPortalBlocks`` and
# ``streamVersionPortalBlockCrop``), sealed stubs until `W55B-GEOMETRY-01` served them.
# `W57A-SEAL-01B` added ``getRunNormVerification`` on ``run_id``, a sealed stub (see
# :data:`SEALED_STUB_ADDRESSED`; this register missed it until `W59-SECTION-SEAL-01`).
# `W59-SECTION-SEAL-01` added ``getVersionSectionReview``, addressed through its version's
# document and project, which answers ``404 not_found`` for any link that names nothing.
# `W59-VERSION-COMPARE-01` added ``compareDocumentVersions`` the same way; its required
# ``target_version_uid`` is supplied by :data:`REQUIRED_QUERY`, so the answer is about the path.
# `W57B-NORMS-CATALOGUE-XLSX-01` added ``exportRunXlsx`` on ``run_id``: an absent run is
# ``404 not_found``, as for ``exportRunCsv``.
# `W61-DISPATCHER-01` added ``getAssignment`` on ``assignment_uid`` (``404`` for an identity that
# names nothing, or an assignment the caller may not read) and ``listAssignments``, an
# unaddressed collection.
# `W60-PRICE-LIST-01` added three: ``listPriceListRevisions`` and ``getEffectiveVendorLists``
# on ``project_uid`` and ``listPriceListPositions`` on ``price_list_id``.
# With both, the addressed half is twenty-five.
# `W60-OPT-MATCH-01` added ``getSpecificationPrices``, addressed through its document set's
# project: an absent project or a set outside it is ``404 not_found``. Twenty-six.
# `W60-OPT-PROPOSALS-01` added four: ``listOptimisationPasses`` on ``project_uid``, and
# ``listOptimisationProposals``, ``listProposalDecisions`` and ``exportOptimisationProposalsCsv``
# on a pass or a proposal identity. With all of them, the addressed half is thirty.
# `NORM-REFS-RUN-01` added ``getRunNormReferences`` on ``run_id``: an absent run is
# ``404 not_found`` (``AuditRun``), as for ``getRunStatus``. Thirty-one.
# Four more were never counted here: `EXEC-SEAL-01`'s ``getExecutorConnection`` on
# ``connection_id`` (an absent connection is ``404 not_found``, administrators only);
# `AR-V3-BETA-SIX-RUN-02`'s ``getArV3BetaGroup`` and `AR-V3-BETA-GROUP-API-SEAL-01`'s
# ``getArV3BetaGroupReview``, both on ``group_id``; and `EXEC-IMAGE-DELIVERY-01`'s
# ``getExecutorTaskImage`` on ``task_id`` and ``blob_id``, a runner-token read swept by
# :data:`RUNNER_ADDRESSED`. With all four, the addressed half is thirty-five.
# `CMP-SEAL-C0` adds nine: the two project-scoped listings, the batch and its proposal, the
# version-order listing, the page-profile listing and the four page reads. Forty-four.
# `CMP-SEAL-C1` adds nine: the matrix, its edit history and the accepted AI links, the series of a document set and
# one series, the sheet pairs of a transition and one sheet pair with its tile, and the overview of a project (the
# queue read names no parent). Fifty-three.
# `CMP-SEAL-C2` adds twenty-two: the AI check of a document set (its estimate, the latest check, the hints), the AI
# description of a series (the estimate and the progress), of a sheet pair (the description, its history, its estimate and
# its MD) and the sheets to review of a transition, the positions of a specification page and of a sheet pair, the
# specifications of a series and the specification of a transition (with its changes and estimate), the launch queue of a
# project, and the MD summary, the reports and one report of a series with its PDF and source. The installation's AI queue
# names no parent. Seventy-five.
EXPECTED_ADDRESSED = 75

#: Addressed ``GET`` operations with a required query parameter, and a well-formed value for
#: it naming nothing. Without it the bare path would be ``422`` for the missing parameter --
#: a true answer, but about the query and not about the path this sweep judges.
REQUIRED_QUERY: dict[str, str] = {
    "compareDocumentVersions": "?target_version_uid=ver_01M2545JSD15ETSNNV904X991K",
    # `CMP-SEAL-C0`: the tile is addressed by query; `CMP-PROFILE-01` serves it: an absent profile is `404`.
    "streamVersionPageTile": "?level=0&column=0&row=0",
    # `CMP-SEAL-C1`: the pair tile is addressed by query too; `CMP-VIEWER-01` serves it: an absent pair is `404`.
    "streamComparisonPairTile": "?mode=a&level=0&column=0&row=0",
}
# `W59-ANALYSIS-SETTINGS-01` added ``listAnalysisProfiles``, unaddressed: the registry's
# fifteen rows, answered as ``items`` like a collection with no parent identity.
# `W57B-NORMS-CATALOGUE-XLSX-01` added ``listNormDocuments``, unaddressed: see
# :data:`CURRENT_SNAPSHOT_COLLECTIONS`.
# With ``listAssignments`` (`W61-DISPATCHER-01`) and ``listNormDocuments`` the unaddressed half is
# seventeen.
# Three more were never counted here: `EXEC-SEAL-01`'s ``listExecutorConnections`` and
# ``listExecutorRoutes`` (collections) and `AR-V3-BETA-PACK-STATUS-API-01`'s
# ``getArV3BetaPackStatus`` (a server singleton, see :data:`SERVER_STATUS_OPERATIONS`).
# With all three, the unaddressed half is twenty.
# `ANALYSIS-PRESETS-01`'s ``listAnalysisPresets`` is a collection like ``listExecutorConnections``
# (every preset, no parent), so the unaddressed half is twenty-one. `CMP-SEAL-C1` adds the comparison queue read
# (``getComparisonQueueSummary``, the installation's queue, no parent): twenty-two. `CMP-SEAL-C2` adds the installation's
# AI queue (``getComparisonAiQueue``, no parent): twenty-three.
EXPECTED_UNADDRESSED = 23

#: Unaddressed `GET` operations that are not collections and are exempt from
#: ``test_a_collection_that_names_no_parent_answers_a_page``'s page-shape assertion.
#:
#: `D-67`'s rule is about a *collection*: a path with no parent identity answers `200`
#: with the page it has, because there is no identity to be missing. `getDashboardSummary`
#: has no parent identity for the same structural reason `listProjects` and
#: `listDecisions` do not -- it addresses nothing -- but it is not a listing of anything
#: and was deliberately built not to page (`R-44`; see `DashboardPort` and
#: `docs/program/W46-SEAL.md` section 3): a caller cannot supply `cursor` or `limit` and
#: the frozen `DashboardSummary` declares no `items` and no `page`. Extending this
#: module's collection rule to it would assert a shape the contract does not declare,
#: which is the reverse of what this file exists to catch.
AGGREGATE_OPERATIONS = frozenset({"getDashboardSummary"})

#: `W49-SEAL-01`. Unaddressed ``GET`` operations that read **the caller's own** resource:
#: ``getMe`` addresses the account the credential names, so it has no parent identity to be
#: missing and nothing to page. Exempt from the page check, and checked for its own shape by
#: :func:`test_the_callers_own_account_answers_its_own_shape`.
SELF_OPERATIONS = frozenset({"getMe"})

#: `AR-V3-BETA-PACK-STATUS-API-01`. ``getArV3BetaPackStatus`` reads **the server's** one
#: reviewed-pack status: no parent identity and nothing to page, so it is a singleton and not a
#: collection. Exempt from the page check, and checked for its own shape by
#: :func:`test_the_server_pack_status_answers_its_own_shape`.
SERVER_STATUS_OPERATIONS = frozenset({"getArV3BetaPackStatus"})

#: `EXEC-IMAGE-DELIVERY-01`. Addressed ``GET`` operations a *runner token* calls: a user's
#: credential, this sweep's included, is not a runner token, so the answer to it is the
#: seam's ``401`` and never a ``404`` -- exempt from the ``404`` sweep (an identity that
#: names nothing is not what is being refused) and asserted to be exactly that refusal
#: instead (:func:`test_a_runner_token_read_is_not_answered_to_a_users_credential`). The
#: runner's own answers: ``tests/integration/executors/test_runner_seam.py`` covers the ``200``
#: and the ``401``; the ``404`` and claim-loss refusals are covered at adapter level in
#: ``tests/unit/executors/test_pull_images.py``.
RUNNER_ADDRESSED = frozenset({"getExecutorTaskImage"})

# These GETs are neither a page of projects nor the account itself. Their own
# response shapes are checked below after the Stage-C release adapter is wired.
RELEASE_OPERATIONS = frozenset({"getProductVersion", "listReleases"})

# W53 adds two unaddressed collection reads. They stay in the page-shape sweep;
# neither may be mistaken for a read of a missing parent.
EXECUTION_COLLECTIONS = frozenset({"listExecutionQueue", "listExecutionJournal"})

#: `W54-SEAL-01`. Unaddressed collections whose port is a sealed stub, exempt from the
#: page-shape assertion and asserted to be exactly that stub instead
#: (:func:`test_a_sealed_stub_collection_answers_unavailable_and_never_an_empty_page`).
#: `W54-WORKER-01` emptied it: ``listWorkers`` reads the registry and joins the page-shape
#: sweep as an ordinary collection (an empty registry is a page with no items, which is a
#: true statement about a deployment with no worker).
#: `W55A-SEAL-01` filled it again with the two norms snapshot listings; `W55A-SEARCH-01`
#: serves them and empties it, so both join the page-shape sweep: no snapshot loaded is a
#: page with no items, and so is a history with no designation. The sweep's account holds
#: ``admin``, so the administrator's history answers its page rather than the seam's ``403``.
#: `CMP-SEAL-C1`: ``getComparisonQueueSummary`` names no parent and is not a page (the read of the comparison queue by
#: state and kind); it answers `503 dependency_unavailable` until `CMP-VC-OVERVIEW-01` serves it, and then joins
#: the aggregate operations above, which are objects and not pages.
#: `CMP-VC-OVERVIEW-01` serves it and empties this set: it joins :data:`COMPARISON_QUEUE_OPERATIONS`.
#: `CMP-SEAL-C2`: ``getComparisonAiQueue`` names no parent and is not a page (the AI jobs of the installation with their
#: counts); it answers `503 dependency_unavailable` until `CMP-VC-QUEUE-01` serves it, and then it leaves this set.
SEALED_STUB_COLLECTIONS: frozenset[str] = frozenset({"getComparisonAiQueue"})

#: `CMP-VC-OVERVIEW-01`. ``getComparisonQueueSummary`` is an aggregate of the whole installation, not a page and not a
#: dashboard: the module set, the pause, the items by state and by kind. Exempt from the page check, and checked for its
#: own shape by :func:`test_the_comparison_queue_summary_answers_its_own_fixed_shape`.
COMPARISON_QUEUE_OPERATIONS = frozenset({"getComparisonQueueSummary"})

#: `W55A-SEAL-01`. Addressed ``GET`` operations whose port is a sealed stub: they cannot
#: answer ``404`` for an absent identity until something reads the identity, so they are
#: exempt from the ``404`` sweep and asserted to be exactly the stub instead
#: (:func:`test_a_sealed_stub_get_with_a_parent_answers_unavailable`). `W55A-SEARCH-01`
#: emptied it and the three joined the sweep: an absent ``ndoc_`` is ``404 not_found`` --
#: the document, its paragraphs and its PDF alike.
#: `W55B-SEAL-01` filled it again with the two portal-block reads; `W55B-GEOMETRY-01` serves
#: them and empties it, and an absent `ver_` is now `404 not_found` for both.
#: `W57A-SEAL-01B` sealed ``getRunNormVerification`` as a refusing stub (``503``,
#: ``dependency: norm_verification_reader``) until the CITE reader. `AR-V3-DECISIONS-01`
#: (`R-146at`) serves it and empties this set again: an absent ``run_`` is now ``404
#: not_found``, swept with the other addressed reads.
#: `CMP-SEAL-C0` (ADR-0025 decision 25) filled it with the nine comparison reads whose ports are
#: sealed stubs; `CMP-INGEST-01`, `CMP-INGEST-02` and `CMP-PROFILE-01` remove the ones they wire,
#: and each then joins the `404` sweep. Two of them list under a project, so they are addressed.
#: `CMP-INGEST-01` serves ``getComparisonUpload``, ``getComparisonUploadProposal`` and
#: ``listComparisonVersionOrders`` and removes them: each joins the `404` sweep (an absent `cbt_` is `404
#: not_found`, and so is an absent project or document of the version-order listing). `CMP-INGEST-02` serves
#: ``listComparisonUploads`` and empties this set: an absent project is `404 not_found`, never an empty page.
#: `CMP-SEAL-C1` fills it with the nine reads of the version comparison core that name a parent; `CMP-MATRIX-01`,
#: `CMP-SERIES-01`, `CMP-VIEWER-01` and `CMP-VC-OVERVIEW-01` remove the ones they wire, and each then joins the `404`
#: sweep (an absent project, document, series, transition or sheet pair is `404 not_found`).
#: `CMP-MATRIX-01` serves ``getComparisonMatrix``, ``listComparisonMatrixEdits`` and ``listComparisonAiLinks`` and
#: removes them: each joins the `404` sweep.
#: `CMP-SERIES-01` serves ``listComparisonSeries``, ``getComparisonSeries``, ``listComparisonSheetPairs`` and
#: ``getComparisonSheetPair`` and removes them: each joins the `404` sweep. The count of addressed operations
#: (:data:`EXPECTED_ADDRESSED`) does not change: they are addressed whether stubbed or served.
#: `CMP-VC-OVERVIEW-01` serves ``getComparisonOverview`` and empties this set: an absent project is `404 not_found`,
#: never an empty overview.
#: `CMP-SEAL-C2` fills it with the twenty-two reads of the version comparison AI, specifications, launch queue and reports
#: that name a parent; `CMP-VC-AIPAIR-01`, `CMP-VC-AISHEET-01`, `CMP-VC-SPEC-01`, `CMP-VC-QUEUE-01` and `CMP-VC-REPORT-01`
#: remove the ones they wire, and each then joins the `404` sweep (an absent project, document, series, transition,
#: sheet pair, page profile or report is `404 not_found`).
#: `CMP-VC-AISHEET-01` wires seven reads that name a parent. They keep the module-flag refusal first (`A-12`), so in this sweep, where the
#: versions module is off, each answers `503 comparison_modules` and not `404`; they are swept apart, with the module on, by
#: :func:`test_the_wired_sheet_reads_are_404_for_an_absent_parent_once_the_module_is_on` below.
MODULE_GATED_ADDRESSED: frozenset[str] = frozenset({
    "estimateComparisonAiSheetChanges",
    "getComparisonAiSheetChanges",
    "getComparisonSheetDescription",
    "listComparisonSheetDescriptionHistory",
    "estimateComparisonSheetDescription",
    "streamComparisonSheetDescriptionMd",
    "listComparisonReviewSheets",
})
SEALED_STUB_ADDRESSED: frozenset[str] = frozenset({
    "estimateComparisonAiPairCheck",
    "getComparisonAiPairCheck",
    "listComparisonAiPairHints",
    "getVersionPageSpecPositions",
    "getComparisonSheetPairSpecPositions",
    "listComparisonSpecifications",
    "getComparisonSpecification",
    "listComparisonSpecificationChanges",
    "estimateComparisonSpecification",
    "getComparisonLaunchQueue",
    "streamComparisonSeriesSummary",
    "listComparisonReports",
    "getComparisonReport",
    "streamComparisonReportPdf",
    "streamComparisonReportSourceMd",
})

#: `W55A-SEAL-01`. ``searchNorms`` addresses no parent but is not a listing of everything:
#: its ``q`` is required, so the bare path is ``422 validation_failed`` on ``q`` and never a
#: page. Exempt from the page check and checked for that refusal instead
#: (:func:`test_a_query_without_its_text_is_refused_and_never_a_page`).
QUERY_OPERATIONS = frozenset({"searchNorms"})

#: `W57B-NORMS-CATALOGUE-XLSX-01`. Collections scoped to the current norms snapshot: with
#: none designated the answer is ``422 required_norm_unavailable`` (``reference_kind:
#: norms_snapshot``), exactly as ``searchNorms`` answers, never an empty page; with one it is
#: a page. Swept for one of those two answers and nothing else.
CURRENT_SNAPSHOT_COLLECTIONS = frozenset({"listNormDocuments"})


#: `W63-SECTION-FORM7-01`. ``getSectionSpecification`` is addressed by a *closed code*, not by a
#: parent identity: ``{section_code}`` is one of the fifteen sections, a filter over every
#: project's current versions, so there is no parent to be missing and the empty section is a
#: true answer (``200``, no projects). It joins neither half of the rule above; it is swept for
#: its own two refusals by :func:`test_a_section_filter_answers_the_section_and_refuses_what_names_nothing`:
#: a ``project_uid`` filter that names nothing is ``404 not_found`` (``Project``), and a code
#: outside the fifteen is ``404 not_found`` (``SectionSpecification``).
SECTION_FILTER_OPERATIONS = frozenset({"getSectionSpecification"})


#: Path parameters whose name is not the catalog's key for the identity they carry. Written out
#: rather than guessed: ``group_id`` is ``ar_v3_run_group_id`` (``arg_``, `AR-V3-BETA-SIX-RUN-02`), and
#: `EXEC-SEAL-01` / `EXEC-PULL-01` name an executor connection ``connection_id`` (``executor_connection_id``,
#: ``exc_``) and a runner's task ``task_id`` (``executor_task_id``, ``ext_``). A parameter in
#: neither the catalog nor this table is still an error.
_CATALOG_KEY: dict[str, str] = {
    "group_id": "ar_v3_run_group_id",
    "connection_id": "executor_connection_id",
    "task_id": "executor_task_id",
    # `ANALYSIS-PRESETS-01`: a preset is identified by the audit event written with its first
    # revision (``evt_``), so its path parameter takes that catalogue key.
    "preset_id": "audit_event_id",
}


def _prefixes() -> dict[str, str]:
    catalog = json.loads(_CATALOG.read_text(encoding="utf-8"))
    return dict(catalog["identifiers"])


def _absent_identity(parameter: str) -> str:
    external = json.loads(_CATALOG.read_text(encoding="utf-8")).get("external_identifiers", {})
    if parameter in external:
        # `W55B-SEAL-01`: an external identifier is not a prefix-ULID, so it is filled with the
        # catalog's own pattern's shape (`blk_` and 32 hexadecimal digits), never a ULID.
        return f"{external[parameter]['prefix']}_" + "0" * 32
    prefixes = _prefixes()
    key = _CATALOG_KEY.get(parameter, parameter)
    if key not in prefixes:
        raise AssertionError(
            f"the catalog declares no prefix for the path parameter {parameter!r}; "
            "filling it with a guess would produce a refusal for the wrong reason"
        )
    return f"{prefixes[key]}_{_ABSENT_ULID}"


class Composed:
    __slots__ = ("application", "client")

    def __init__(self, application: Any, client: TestClient) -> None:
        self.application = application
        self.client = client


@pytest.fixture(scope="module")
def app() -> Composed:
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    # No reviewed pack is installed in this suite, whatever the process environment names:
    # `test_the_server_pack_status_answers_its_own_shape` asserts that state.
    environ = {k: v for k, v in os.environ.items() if k != PACK_MANIFEST_ENV} | {
        API_TOKEN_VARIABLE: DEPLOYMENT_SECRET
    }
    application = create_app(environ=environ)
    asgi = create_asgi_app(environ=environ, application=application)
    return Composed(application, TestClient(asgi, raise_server_exceptions=False))


def _credential() -> str:
    """The sweep's account, holding ``admin`` beside ``expert`` (`W49-SEAL-01`).

    The sweep asks every ``GET`` what it answers an identity that names nothing, and an
    administrator's ``GET`` (``getUser``) answers a non-administrator the seam's ``403``
    before it can answer ``404``. The grant is this module's own account's, idempotent, and
    made through the access boundary; the credential is minted after it, because a grant
    that changes the role set raises the epoch.
    """
    from am_test_accounts import database_url, provisioned_credential, provisioned_record
    from sqlalchemy.orm import Session

    from auditmanager.access.accounts import AccountRepository
    from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
    from auditmanager.shared.db.engine import create_database_engine

    record = provisioned_record("absent-parent-sweep")
    engine = create_database_engine(DatabaseSettings(url=parse_database_url(database_url())))
    try:
        with Session(engine) as session:
            AccountRepository().grant_role(
                session, user_uid=str(record.user_uid), role="admin", granted_by=None
            )
            session.commit()
    finally:
        engine.dispose()
    return provisioned_credential(DEPLOYMENT_SECRET, "absent-parent-sweep")


def _get(app: Composed, path: str) -> tuple[int, Any]:
    response = app.client.get(path, headers={"Authorization": f"Bearer {_credential()}"})
    try:
        body = json.loads(response.content) if response.content else None
    except ValueError:
        body = response.content
    return response.status_code, body


def _get_routes(app: Composed) -> tuple[tuple[str, str], ...]:
    """``(operationId, path template)`` for every ``GET`` the composed router serves.

    Read off the built application rather than off the frozen document, because what this
    file measures is what the application *answers* and a document cannot answer.
    """
    found = []
    for route in app.application.router.routes:
        operation_id = getattr(route, "operation_id", None)
        if not operation_id or "GET" not in getattr(route, "methods", ()):
            continue
        found.append((operation_id, getattr(route, "path", "")))
    return tuple(sorted(found))


def _addressed(routes: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    return tuple(
        (op, path) for op, path in routes if "{" in path and op not in SECTION_FILTER_OPERATIONS
    )


def _section_filtered(routes: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    return tuple((op, path) for op, path in routes if op in SECTION_FILTER_OPERATIONS)


def _unaddressed(routes: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    return tuple((op, path) for op, path in routes if "{" not in path)


def test_the_surface_partitions_into_the_two_halves_of_the_rule(app: Composed) -> None:
    """The sweep's own anti-vacuity, and the thing that makes it survive a new operation.

    A sweep that silently covered nothing would pass. A sweep that stopped covering an
    operation added next month would pass too, and that is the more likely failure: the
    counts are literals so that either one is a red naming the operation.
    """
    routes = _get_routes(app)
    addressed = _addressed(routes)
    unaddressed = _unaddressed(routes)
    assert len(addressed) == EXPECTED_ADDRESSED, (
        f"the surface now has {len(addressed)} GET operations addressing a parent "
        f"identity, not {EXPECTED_ADDRESSED}: {addressed}"
    )
    assert len(unaddressed) == EXPECTED_UNADDRESSED, (
        f"the surface now has {len(unaddressed)} GET operations addressing no parent "
        f"identity, not {EXPECTED_UNADDRESSED}: {unaddressed}"
    )


def test_every_get_that_names_a_parent_refuses_an_identity_that_names_nothing(
    app: Composed,
) -> None:
    """`D-67`. Every one of them, not the two the row named.

    Swept rather than listed, for the reason ``test_router_answers.py`` gives about its own
    sweep: a list stops covering whatever is added after it is written, and this rule's
    whole content is that the answer is the *same* everywhere.
    """
    disagreements = []
    for operation_id, template in _addressed(_get_routes(app)):
        if operation_id in SEALED_STUB_ADDRESSED or operation_id in RUNNER_ADDRESSED or operation_id in MODULE_GATED_ADDRESSED:
            continue
        path = re.sub(r"\{(\w+)\}", lambda m: _absent_identity(m.group(1)), template)
        status, body = _get(app, path + REQUIRED_QUERY.get(operation_id, ""))
        code = body.get("error_code") if isinstance(body, dict) else None
        if (status, code) != (404, "not_found"):
            disagreements.append((operation_id, path, status, code))
    assert disagreements == [], (
        "these operations answered something other than 404 not_found for an identity "
        f"that names nothing: {disagreements}"
    )


def test_the_wired_sheet_reads_are_404_for_an_absent_parent_once_the_module_is_on(app: Composed) -> None:
    """`CMP-VC-AISHEET-01`: the seven reads of the sheet descriptions, with the versions module on, answer `404 not_found` for an identity
    that names nothing (never an empty description or an empty list); with it off, they refuse first."""
    on_environ = {k: v for k, v in os.environ.items() if k != PACK_MANIFEST_ENV} | {
        API_TOKEN_VARIABLE: DEPLOYMENT_SECRET, "AUDITMANAGER_COMPARISON_MODULES": "versions",
    }
    application = create_app(environ=on_environ)
    on = Composed(application, TestClient(create_asgi_app(environ=on_environ, application=application), raise_server_exceptions=False))
    swept = [(op, path) for op, path in _addressed(_get_routes(app)) if op in MODULE_GATED_ADDRESSED]
    assert {op for op, _ in swept} == MODULE_GATED_ADDRESSED
    for operation_id, template in swept:
        path = re.sub(r"\{(\w+)\}", lambda m: _absent_identity(m.group(1)), template) + REQUIRED_QUERY.get(operation_id, "")
        status, body = _get(on, path)
        assert (status, body.get("error_code")) == (404, "not_found"), (operation_id, status, body)
        status, body = _get(app, path)
        assert (status, body.get("error_code"), body["details"]["dependency"]) == (503, "dependency_unavailable", "comparison_modules"), operation_id


def test_a_section_filter_answers_the_section_and_refuses_what_names_nothing(app: Composed) -> None:
    """`W63-SECTION-FORM7-01`. The third kind of ``GET``: addressed by a code, not an identity.

    Every code of the fifteen answers ``200`` -- an empty section is an answer, never a
    ``404`` -- with the read's own shape (a state, its projects and the page of rows, or the
    bound that stopped it); an unknown ``project_uid`` filter and a code outside the fifteen
    are ``404 not_found`` naming the aggregate each addressed.
    """
    filtered = _section_filtered(_get_routes(app))
    assert {operation_id for operation_id, _ in filtered} == SECTION_FILTER_OPERATIONS
    for operation_id, template in filtered:
        for code in ("AR", "PS"):
            status, body = _get(app, template.replace("{section_code}", code))
            assert status == 200, f"{operation_id} answered {status} for {code}: {body}"
            assert isinstance(body, dict) and isinstance(body.get("projects"), list), body
            assert body["section_code"] == code and body["state"] in ("ready", "section_too_large")
            assert "items" not in body and "page" not in body, body
        bare = template.replace("{section_code}", "AR")
        status, body = _get(app, f"{bare}?project_uid={_absent_identity('project_uid')}")
        assert (status, body.get("error_code")) == (404, "not_found"), (status, body)
        assert body.get("details") == {"aggregate_type": "Project"}, body
        status, body = _get(app, template.replace("{section_code}", "XX"))
        assert (status, body.get("error_code")) == (404, "not_found"), (status, body)
        assert body.get("details") == {"aggregate_type": "SectionSpecification"}, body


def test_a_collection_that_names_no_parent_answers_a_page(app: Composed) -> None:
    """The other half at the surface level: there is no identity to be missing.

    ``listProjects`` and ``listDecisions`` address a collection and not a child of
    anything, so ``404`` would be an answer to a question nobody asked. The frozen document
    declares no ``404`` on either. The page itself may hold anything -- this lane's database
    is long-lived and shared -- so what is asserted is the status and the shape.

    ``getDashboardSummary`` is unaddressed too and is excluded here by name -- see
    :data:`AGGREGATE_OPERATIONS` -- and checked by
    :func:`test_the_one_unaddressed_aggregate_answers_its_own_fixed_shape` instead, so
    "excluded from this page check" is not the same claim as "unchecked".
    """
    unaddressed = _unaddressed(_get_routes(app))
    assert {operation_id for operation_id, _ in unaddressed} >= EXECUTION_COLLECTIONS
    # `W54-WORKER-01`: the registry is served, so it is swept like the other collections.
    assert "listWorkers" in {operation_id for operation_id, _ in unaddressed}
    for operation_id, template in unaddressed:
        if (
            operation_id in AGGREGATE_OPERATIONS
            or operation_id in SELF_OPERATIONS
            or operation_id in SERVER_STATUS_OPERATIONS
            or operation_id in RELEASE_OPERATIONS
            or operation_id in SEALED_STUB_COLLECTIONS
            or operation_id in COMPARISON_QUEUE_OPERATIONS
            or operation_id in QUERY_OPERATIONS
        ):
            continue
        status, body = _get(app, template)
        if operation_id in CURRENT_SNAPSHOT_COLLECTIONS and status == 422:
            assert isinstance(body, dict) and body.get("error_code") == "required_norm_unavailable"
            assert body.get("details") == {"reference_kind": "norms_snapshot"}, body
            continue
        assert status == 200, f"{operation_id} answered {status}: {body}"
        assert isinstance(body, dict) and isinstance(body.get("items"), list), (
            f"{operation_id} answered 200 without a page: {body}"
        )


def test_a_sealed_stub_collection_answers_unavailable_and_never_an_empty_page(
    app: Composed,
) -> None:
    """`W54-SEAL-01`. The exemption above is narrow: the stub fails explicitly.

    An empty page would read as "no worker is registered", which is a claim about the
    deployment the stub cannot make; ``503 dependency_unavailable`` says the registry is
    not served yet.
    """
    unaddressed = _unaddressed(_get_routes(app))
    stubs = [(op, path) for op, path in unaddressed if op in SEALED_STUB_COLLECTIONS]
    assert {op for op, _ in stubs} == SEALED_STUB_COLLECTIONS
    for operation_id, template in stubs:
        status, body = _get(app, template)
        assert status == 503, f"{operation_id} answered {status}: {body}"
        assert isinstance(body, dict) and body.get("error_code") == "dependency_unavailable", body
        assert "items" not in body, body


def test_a_sealed_stub_get_with_a_parent_answers_unavailable(app: Composed) -> None:
    """`W55A-SEAL-01`. The addressed exemption is as narrow as the unaddressed one.

    A sealed norms read cannot tell an absent ``ndoc_`` from a present one -- nothing reads
    it yet -- so it must not answer either ``404`` or a page: ``503 dependency_unavailable``
    says the norms reads are not served yet.
    """
    addressed = _addressed(_get_routes(app))
    stubs = [(op, path) for op, path in addressed if op in SEALED_STUB_ADDRESSED]
    assert {op for op, _ in stubs} == SEALED_STUB_ADDRESSED
    for operation_id, template in stubs:
        path = re.sub(r"\{(\w+)\}", lambda m: _absent_identity(m.group(1)), template)
        status, body = _get(app, path + REQUIRED_QUERY.get(operation_id, ""))
        assert status == 503, f"{operation_id} answered {status}: {body}"
        assert isinstance(body, dict) and body.get("error_code") == "dependency_unavailable", body
        assert "items" not in body, body


def test_a_query_without_its_text_is_refused_and_never_a_page(app: Composed) -> None:
    """`W55A-SEAL-01`. ``searchNorms`` with no ``q`` is a malformed request, not a page.

    With a ``q`` it reaches its port (`W55A-SEARCH-01`): while no snapshot is current it
    refuses ``required_norm_unavailable`` (``reference_kind: norms_snapshot``) -- never an
    empty page, which would read as "nothing in the corpus matches" -- and once one is, it
    answers a page. It is never the sealed stub's ``503`` again.
    """
    unaddressed = _unaddressed(_get_routes(app))
    queries = [(op, path) for op, path in unaddressed if op in QUERY_OPERATIONS]
    assert {op for op, _ in queries} == QUERY_OPERATIONS
    for operation_id, template in queries:
        status, body = _get(app, template)
        assert status == 422, f"{operation_id} answered {status}: {body}"
        assert body.get("error_code") == "validation_failed", body
        status, body = _get(app, f"{template}?q=%D0%93%D0%9E%D0%A1%D0%A2%2010140")
        assert status in (200, 422), f"{operation_id} answered {status}: {body}"
        assert isinstance(body, dict), body
        if status == 422:
            assert "items" not in body, body
            assert body.get("error_code") == "required_norm_unavailable", body
            assert body.get("details") == {"reference_kind": "norms_snapshot"}, body
        else:
            assert isinstance(body.get("items"), list), body


def test_release_gets_serve_the_running_version_and_history(app: Composed) -> None:
    releases = tuple(
        (operation_id, path)
        for operation_id, path in _unaddressed(_get_routes(app))
        if operation_id in RELEASE_OPERATIONS
    )
    assert {operation_id for operation_id, _path in releases} == RELEASE_OPERATIONS
    for operation_id, path in releases:
        status, body = _get(app, path)
        assert status == 200, f"{operation_id} answered {status}: {body}"
        assert isinstance(body, dict), f"{operation_id} answered a non-object: {body}"
        if operation_id == "getProductVersion":
            assert body["product_version"] == _VERSION.read_text(encoding="utf-8").strip()
            assert body["contract_version"]
            assert body["build_id"]
        else:
            assert isinstance(body["items"], list)
            assert isinstance(body["whats_new"], list)


def test_the_one_unaddressed_aggregate_answers_its_own_fixed_shape(app: Composed) -> None:
    """``getDashboardSummary``, the operation :data:`AGGREGATE_OPERATIONS` excuses above.

    Not a page -- no ``items``, no ``page`` -- and not empty either: `R-44`'s four panels,
    every one of them present. This is the other half of the rule the excuse above states:
    exempt from *paging*, not exempt from *shape*.
    """
    unaddressed = _unaddressed(_get_routes(app))
    aggregates = [(op, path) for op, path in unaddressed if op in AGGREGATE_OPERATIONS]
    assert aggregates, "no unaddressed operation is registered in AGGREGATE_OPERATIONS"
    for operation_id, template in aggregates:
        status, body = _get(app, template)
        assert status == 200, f"{operation_id} answered {status}: {body}"
        assert isinstance(body, dict), f"{operation_id} answered a non-object body: {body}"
        assert "items" not in body and "page" not in body, (
            f"{operation_id} answered a page shape; it is registered as an aggregate, "
            "not a collection"
        )
        for panel in (
            "documents_by_project",
            "findings_by_verdict",
            "run_activity",
            "section_breakdown",
        ):
            assert panel in body, f"{operation_id} answered with no {panel!r} panel: {body}"


def test_the_comparison_queue_summary_answers_its_own_fixed_shape(app: Composed) -> None:
    """``getComparisonQueueSummary``, the operation :data:`COMPARISON_QUEUE_OPERATIONS` excuses from the page check.

    Not a page and not empty: the module set, the pause, the nine counts and the kinds -- exempt from *paging*, not from
    *shape*."""
    unaddressed = _unaddressed(_get_routes(app))
    reads = [(op, path) for op, path in unaddressed if op in COMPARISON_QUEUE_OPERATIONS]
    assert {op for op, _ in reads} == COMPARISON_QUEUE_OPERATIONS
    for operation_id, template in reads:
        status, body = _get(app, template)
        assert status == 200, f"{operation_id} answered {status}: {body}"
        assert isinstance(body, dict) and "items" not in body and "page" not in body, body
        for key in ("modules", "paused", "counts", "kinds"):
            assert key in body, f"{operation_id} answered without {key!r}: {body}"
        assert set(body["counts"]) == {
            "queued", "leased", "running", "retry_wait", "paused", "spend_unknown", "succeeded", "failed", "cancelled",
        }, body


def test_the_callers_own_account_answers_its_own_shape(app: Composed) -> None:
    """``getMe``, the operation :data:`SELF_OPERATIONS` excuses from the page check.

    Not a page and not empty: the account the credential names, every required property
    present -- exempt from *paging*, not from *shape*.
    """
    unaddressed = _unaddressed(_get_routes(app))
    own = [(op, path) for op, path in unaddressed if op in SELF_OPERATIONS]
    assert own, "no unaddressed operation is registered in SELF_OPERATIONS"
    for operation_id, template in own:
        status, body = _get(app, template)
        assert status == 200, f"{operation_id} answered {status}: {body}"
        assert isinstance(body, dict) and "items" not in body, body
        for key in ("user_uid", "login", "display_label", "roles", "profile_complete"):
            assert key in body, f"{operation_id} answered without {key!r}: {body}"


def test_the_server_pack_status_answers_its_own_shape(app: Composed) -> None:
    """``getArV3BetaPackStatus``, the operation :data:`SERVER_STATUS_OPERATIONS` excuses.

    Not a page and not a read of a parent: what the server holds, which with no reviewed pack
    installed is exactly ``{"state": "not_installed"}`` -- every other property is absent, never
    null (the installed shape, with its attestation, is covered by the pack-status API tests).
    Exempt from *paging*, not from *shape*.
    """
    unaddressed = _unaddressed(_get_routes(app))
    status_reads = [(op, path) for op, path in unaddressed if op in SERVER_STATUS_OPERATIONS]
    assert {op for op, _ in status_reads} == SERVER_STATUS_OPERATIONS
    for operation_id, template in status_reads:
        status, body = _get(app, template)
        assert status == 200, f"{operation_id} answered {status}: {body}"
        assert body == {"state": "not_installed"}, (
            f"{operation_id} answered {body!r} with no reviewed pack installed"
        )


def test_a_runner_token_read_is_not_answered_to_a_users_credential(app: Composed) -> None:
    """``getExecutorTaskImage``, the operation :data:`RUNNER_ADDRESSED` excuses from the ``404`` sweep.

    The caller here is an administrator with a valid user credential, and still the answer is the
    seam's ``401 authentication_required`` -- neither ``404`` (the identities do name nothing, but a
    user's credential does not get as far as asking) nor ``403`` (the credential is not a known
    principal of this operation at all), so the read reveals nothing about which tasks exist.
    """
    addressed = _addressed(_get_routes(app))
    reads = [(op, path) for op, path in addressed if op in RUNNER_ADDRESSED]
    assert {op for op, _ in reads} == RUNNER_ADDRESSED
    for operation_id, template in reads:
        path = re.sub(r"\{(\w+)\}", lambda m: _absent_identity(m.group(1)), template)
        status, body = _get(app, path)
        assert status == 401, f"{operation_id} answered {status}: {body}"
        assert isinstance(body, dict) and body.get("error_code") == "authentication_required", body
