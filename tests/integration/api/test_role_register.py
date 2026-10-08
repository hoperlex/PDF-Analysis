"""`W49-SEAL-01b` -- the seam's registers, swept against the served application.

`W49-PLAN.md` section 3.2: three registers and one map in ``auditmanager.api.security`` say
what an account may reach, and a request meets them in a fixed order -- signature and expiry,
the standing (archived or stale is ``authentication_required``), the default credential, the
incomplete profile, the role set. This module is the sweep the plan requires: **for every
guarded operation x every role set in {none, expert, admin, expert+admin} x {complete,
incomplete} x {default, changed}, the served application's answer equals what the registers
say.**

Three properties keep the sweep from being a tautology:

* **the registers themselves are pinned as literals** (:data:`EXPECTED_ROLES` and the three
  sets in :func:`test_the_registers_are_the_ruled_ones`), written from `R-60`'s groups and
  never read back out of the module under test, so a register that drifted fails here even
  though the seam and the sweep would still agree with each other;
* **the expected answer is computed by this module, from the plan's order**, not by calling
  the seam: :func:`_expected` is a second, independent statement of section 3.2;
* **the observed answer is classified by the envelope the seam writes** -- ``403``,
  ``permission_denied``, ``required_capability`` -- and every port behind the operations
  answers a refusal of another kind (``driver.SuiteAccountAdapter``), so a ``403`` here is
  the seam's and nothing else's.
"""

from __future__ import annotations

import itertools
import json

import pytest

from auditmanager.api.security import (
    OPERATION_ROLES,
    OPERATIONS_A_DEFAULT_CREDENTIAL_REACHES,
    OPERATIONS_AN_INCOMPLETE_PROFILE_REACHES,
    ROLES_OF_A_ROUTE_WITHOUT_AN_OPERATION,
    UNAUTHENTICATED_OPERATIONS,
)
from w13_api_driver import Request, Surface, dispatch

#: One request per guarded operation, shaped so that whatever the seam lets through is
#: refused by the operation itself (its body model, or a stand-in port) and never by a 403.
SAMPLES: dict[str, tuple[str, str]] = {
    "createProject": ("POST", "/projects"),
    "listProjects": ("GET", "/projects"),
    "uploadDocument": ("POST", "/projects/prj_01M2545JSD15ETSNNV904X991F/documents"),
    "listDocuments": ("GET", "/projects/prj_01M2545JSD15ETSNNV904X991F/documents"),
    "getDocumentVersion": ("GET", "/versions/ver_01M2545JSD15ETSNNV904X991J"),
    "streamDocumentVersionContent": ("GET", "/versions/ver_01M2545JSD15ETSNNV904X991J/content"),
    "getVersionBlocks": ("GET", "/versions/ver_01M2545JSD15ETSNNV904X991J/blocks"),
    "listRuns": ("GET", "/versions/ver_01M2545JSD15ETSNNV904X991J/runs"),
    "listVersions": ("GET", "/documents/doc_01M2545JSD15ETSNNV904X991H/versions"),
    "startRun": ("POST", "/runs"),
    "getRunStatus": ("GET", "/runs/run_01M2545JSD15ETSNNV904X991K"),
    "listRunFindings": ("GET", "/runs/run_01M2545JSD15ETSNNV904X991K/findings"),
    "exportRunCsv": ("GET", "/runs/run_01M2545JSD15ETSNNV904X991K/export.csv"),
    "getFinding": ("GET", "/findings/fnd_01M2545JSD15ETSNNV904X991M"),
    "appendDecision": ("POST", "/findings/fnd_01M2545JSD15ETSNNV904X991M/decisions"),
    "listDecisionHistory": ("GET", "/findings/fnd_01M2545JSD15ETSNNV904X991M/decisions"),
    "listDecisions": ("GET", "/decisions"),
    "getDashboardSummary": ("GET", "/dashboard"),
    "getProductVersion": ("GET", "/system/version"),
    "listReleases": ("GET", "/releases"),
    "markReleaseNotesRead": ("PUT", "/me/release-notes"),
    "changePassword": ("POST", "/auth/password"),
    "getMe": ("GET", "/me"),
    "updateMyProfile": ("PATCH", "/me"),
    "listRegistrations": ("GET", "/registrations"),
    "approveRegistration": ("POST", "/registrations/reg_01M2545JSD15ETSNNV904X991R/approve"),
    "rejectRegistration": ("POST", "/registrations/reg_01M2545JSD15ETSNNV904X991R/reject"),
    "listUsers": ("GET", "/users"),
    "getUser": ("GET", "/users/usr_01M2545JSD15ETSNNV904X991S"),
    "updateUser": ("PATCH", "/users/usr_01M2545JSD15ETSNNV904X991S"),
    "archiveUser": ("POST", "/users/usr_01M2545JSD15ETSNNV904X991S/archive"),
    "restoreUser": ("POST", "/users/usr_01M2545JSD15ETSNNV904X991S/restore"),
    "purgeUser": ("DELETE", "/users/usr_01M2545JSD15ETSNNV904X991S"),
    "resetUserPassword": ("POST", "/users/usr_01M2545JSD15ETSNNV904X991S/password"),
}

_ANY: frozenset[str] = frozenset()
_EXPERT = frozenset({"expert"})
_ADMIN = frozenset({"admin"})

#: `R-60`, written out from the ruling's three sentences and **not** read from the seam:
#: product reads need any complete account, product changes `expert`, account and request
#: management `admin`; the account's own three operations need any complete account.
EXPECTED_ROLES: dict[str, frozenset[str]] = {
    "listProjects": _ANY,
    "listDocuments": _ANY,
    "getDocumentVersion": _ANY,
    "streamDocumentVersionContent": _ANY,
    "getVersionBlocks": _ANY,
    "listVersions": _ANY,
    "listRuns": _ANY,
    "getRunStatus": _ANY,
    "listRunFindings": _ANY,
    "getFinding": _ANY,
    "listDecisionHistory": _ANY,
    "listDecisions": _ANY,
    "getDashboardSummary": _ANY,
    "getProductVersion": _ANY,
    "listReleases": _ANY,
    "markReleaseNotesRead": _ANY,
    "getMe": _ANY,
    "updateMyProfile": _ANY,
    "changePassword": _ANY,
    "createProject": _EXPERT,
    "uploadDocument": _EXPERT,
    "startRun": _EXPERT,
    "appendDecision": _EXPERT,
    "exportRunCsv": _EXPERT,
    "listRegistrations": _ADMIN,
    "approveRegistration": _ADMIN,
    "rejectRegistration": _ADMIN,
    "listUsers": _ADMIN,
    "getUser": _ADMIN,
    "updateUser": _ADMIN,
    "archiveUser": _ADMIN,
    "restoreUser": _ADMIN,
    "purgeUser": _ADMIN,
    "resetUserPassword": _ADMIN,
}

ROLE_SETS: tuple[frozenset[str], ...] = (
    frozenset(),
    frozenset({"expert"}),
    frozenset({"admin"}),
    frozenset({"expert", "admin"}),
)


def _expected(
    operation: str, *, roles: frozenset[str], complete: bool, default: bool
) -> str | None:
    """Section 3.2, restated: the capability the seam must name, or ``None`` for served."""
    if default and operation not in {"issueToken", "changePassword", "getMe"}:
        return "password_changed"
    if not complete and operation not in {"getMe", "updateMyProfile", "changePassword"}:
        return "profile_completed"
    required = EXPECTED_ROLES[operation]
    if required and not (required & roles):
        return "role:" + "|".join(sorted(required))
    return None


def _observed(router: Surface, operation: str) -> str | None:
    """The capability the served application refused with, or ``None`` when it served.

    A ``401`` is an assertion failure here, not a classification: every request in the
    sweep carries a credential the standing accepts, so a ``401`` would mean the sweep
    measured something other than the registers.
    """
    method, path = SAMPLES[operation]
    answer = dispatch(
        router,
        Request.build(method, path, headers={"Content-Type": "application/json"}, body=b"{}"),
    )
    assert answer.status != 401, (operation, answer.status, answer.body)
    if answer.status != 403:
        return None
    body = json.loads(answer.body)
    assert body["error_code"] == "permission_denied", (operation, body)
    return body["details"]["required_capability"]


def test_the_registers_are_the_ruled_ones() -> None:
    """The literal pin: each register equals what `R-59`, `R-60` and section 3.2 say."""
    assert UNAUTHENTICATED_OPERATIONS == {
        "issueToken",
        "submitRegistration",
        "readRegistrationStatus",
    }
    assert OPERATIONS_A_DEFAULT_CREDENTIAL_REACHES == {"issueToken", "changePassword", "getMe"}
    assert OPERATIONS_AN_INCOMPLETE_PROFILE_REACHES == {
        "getMe",
        "updateMyProfile",
        "changePassword",
    }
    assert dict(OPERATION_ROLES) == EXPECTED_ROLES
    assert ROLES_OF_A_ROUTE_WITHOUT_AN_OPERATION == frozenset()


def test_every_guarded_operation_is_in_the_role_register(router: Surface) -> None:
    """Totality: the served operations minus the open ones are exactly the map's keys.

    An operation with no line is refused to everyone -- closed by default -- and this is
    what reports it rather than letting it sit closed unnoticed.
    """
    assert set(OPERATION_ROLES) == router.operation_ids - UNAUTHENTICATED_OPERATIONS
    assert set(SAMPLES) == set(OPERATION_ROLES)


@pytest.mark.parametrize(
    ("roles", "complete", "default"),
    list(itertools.product(ROLE_SETS, (True, False), (False, True))),
    ids=lambda value: (
        ("+".join(sorted(value)) or "no-role")
        if isinstance(value, frozenset)
        else str(value)
    ),
)
def test_the_served_application_answers_what_the_registers_say(
    router: Surface, roles: frozenset[str], complete: bool, default: bool
) -> None:
    """Every guarded operation, for one standing; the whole matrix is the parametrisation."""
    credentials = router.router.credentials
    credentials.roles = roles
    credentials.profile_complete = complete
    credentials.is_default_credential = default
    mismatches = []
    for operation in sorted(SAMPLES):
        expected = _expected(operation, roles=roles, complete=complete, default=default)
        observed = _observed(router, operation)
        if expected != observed:
            mismatches.append((operation, expected, observed))
    assert mismatches == [], (
        "the served application and the registers disagree, as (operation, expected, "
        f"observed): {mismatches}"
    )


def test_an_archived_account_is_refused_as_unauthenticated_everywhere(
    router: Surface,
) -> None:
    """`R-61`: an archived account has no standing; one answer for every guarded operation."""
    credentials = router.router.credentials
    credentials.roles = frozenset({"expert", "admin"})
    credentials.archived = True
    for operation, (method, path) in sorted(SAMPLES.items()):
        answer = dispatch(router, Request.build(method, path))
        assert answer.status == 401, (operation, answer.status, answer.body)
        assert json.loads(answer.body)["error_code"] == "authentication_required", operation


def test_the_open_operations_read_no_standing(router: Surface) -> None:
    """The three open operations answer the same whatever the account's state would be.

    An archived, roleless, incomplete account on a default credential: none of it is read
    for an operation that takes no credential, so each answers its own validation refusal.
    """
    credentials = router.router.credentials
    credentials.roles = frozenset()
    credentials.archived = True
    credentials.profile_complete = False
    credentials.is_default_credential = True
    for method, path in (
        ("POST", "/auth/token"),
        ("POST", "/registrations"),
        ("POST", "/registrations/status"),
    ):
        answer = dispatch(
            router,
            Request.build(method, path, headers={"Content-Type": "application/json"}, body=b"{}"),
            credential=None,
        )
        assert answer.status == 422, (path, answer.status, answer.body)


def test_a_role_refusal_names_the_role_and_nothing_else(router: Surface) -> None:
    """The envelope's whole detail: the one safe key the catalog declares, with `role:<x>`."""
    credentials = router.router.credentials
    credentials.roles = frozenset({"expert"})
    method, path = SAMPLES["listUsers"]
    answer = dispatch(router, Request.build(method, path))
    assert answer.status == 403, answer.body
    body = json.loads(answer.body)
    assert body["details"] == {"required_capability": "role:admin"}, body
    assert body["retryable"] is False, body


def test_the_subject_carries_the_label_the_row_holds_now(router: Surface) -> None:
    """A profile completed or renamed after the credential was minted is visible at once.

    The credential still names the label it was minted with; the account's row now holds
    another. The subject a handler receives -- and the decision ledger writes
    ``author_label`` from -- carries the row's, because the seam publishes the standing's
    login and label (`W49-SEAL-01`).
    """
    from starlette.testclient import TestClient

    from w13_api_driver import TEST_DISPLAY_LABEL, TEST_TOKEN

    seen: list = []
    app = router.app

    @app.middleware("http")
    async def _capture(request, call_next):  # pragma: no cover - exercised below
        response = await call_next(request)
        seen.append(getattr(request.state, "subject", None))
        return response

    router.router.credentials.display_label = "Переименованная А. И."
    client = TestClient(app, raise_server_exceptions=False)
    answer = client.get("/projects", headers={"Authorization": f"Bearer {TEST_TOKEN}"})
    assert answer.status_code == 200, answer.content
    assert seen and seen[0] is not None, seen
    assert seen[0].display_label == "Переименованная А. И.", seen[0]
    assert seen[0].display_label != TEST_DISPLAY_LABEL


def test_an_operation_the_register_does_not_name_is_refused_to_everyone() -> None:
    """Closed by default: a guarded ``operationId`` with no line in the map is a 403 for
    every role set, carrying no capability, because nothing would open it."""
    from w13_api_driver import SuiteCredentialAdapter

    from auditmanager.api.routers import Router

    credentials = SuiteCredentialAdapter(roles=frozenset({"expert", "admin"}))
    router = Router(credentials=credentials)

    @router.get("/unregistered", operation_id="anOperationNobodyRegistered", tags=["probe"])
    def unregistered() -> dict[str, str]:  # pragma: no cover - must never run
        raise AssertionError("the seam let an unregistered operation through")

    surface = Surface(router)
    answer = dispatch(surface, Request.build("GET", "/unregistered"))
    assert answer.status == 403, (answer.status, answer.body)
    body = json.loads(answer.body)
    assert body["error_code"] == "permission_denied", body
    assert "details" not in body, body
