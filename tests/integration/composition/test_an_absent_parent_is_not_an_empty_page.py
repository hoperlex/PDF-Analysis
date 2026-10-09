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
EXPECTED_ADDRESSED = 12
EXPECTED_UNADDRESSED = 8

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

# These GETs are neither a page of projects nor the account itself. Their own
# response shapes are checked below after the Stage-C release adapter is wired.
RELEASE_OPERATIONS = frozenset({"getProductVersion", "listReleases"})


def _prefixes() -> dict[str, str]:
    catalog = json.loads(_CATALOG.read_text(encoding="utf-8"))
    return dict(catalog["identifiers"])


def _absent_identity(parameter: str) -> str:
    prefixes = _prefixes()
    if parameter not in prefixes:
        raise AssertionError(
            f"the catalog declares no prefix for the path parameter {parameter!r}; "
            "filling it with a guess would produce a refusal for the wrong reason"
        )
    return f"{prefixes[parameter]}_{_ABSENT_ULID}"


class Composed:
    __slots__ = ("application", "client")

    def __init__(self, application: Any, client: TestClient) -> None:
        self.application = application
        self.client = client


@pytest.fixture(scope="module")
def app() -> Composed:
    assert os.environ.get("DATABASE_URL"), "this suite needs the lane's .env loaded"
    environ = dict(os.environ) | {API_TOKEN_VARIABLE: DEPLOYMENT_SECRET}
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
    return tuple((op, path) for op, path in routes if "{" in path)


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
        path = re.sub(r"\{(\w+)\}", lambda m: _absent_identity(m.group(1)), template)
        status, body = _get(app, path)
        code = body.get("error_code") if isinstance(body, dict) else None
        if (status, code) != (404, "not_found"):
            disagreements.append((operation_id, path, status, code))
    assert disagreements == [], (
        "these operations answered something other than 404 not_found for an identity "
        f"that names nothing: {disagreements}"
    )


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
    for operation_id, template in _unaddressed(_get_routes(app)):
        if (
            operation_id in AGGREGATE_OPERATIONS
            or operation_id in SELF_OPERATIONS
            or operation_id in RELEASE_OPERATIONS
        ):
            continue
        status, body = _get(app, template)
        assert status == 200, f"{operation_id} answered {status}: {body}"
        assert isinstance(body, dict) and isinstance(body.get("items"), list), (
            f"{operation_id} answered 200 without a page: {body}"
        )


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
