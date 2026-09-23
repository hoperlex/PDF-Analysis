"""`R-31` / `D-73`. The four documentation routes answer only to a caller with a credential.

``/openapi.json``, ``/docs``, ``/redoc`` and ``/docs/oauth2-redirect`` answered ``200`` with
no credential while every real operation answered ``401`` -- the doors locked and the
blueprint on the doorstep, with the full fifteen-path, fifty-one-schema description of the
surface on it, ``/auth/token``'s shape included. The owner ruled them closed over "leave
them open", which the SSH tunnel would have justified.

Why this file exists rather than four more cases in ``test_authorization.py``
------------------------------------------------------------------------------
**A test that drives the four paths passes the day somebody adds a fifth.** The brief that
dispatched this work says so, and the tree already carries the shape it is warning about:
``OPERATING_CONSTRAINTS.md`` §4.65's widened selector, which *"does not fail -- it passes
for the wrong reason, and keeps passing"*.

So the load-bearing case here is :class:`TestNoRouteEscapesTheSeam`, which asserts a
property of the **assembled application** and names no path at all. The four paths are
driven too, below it, because a structural property that nobody has confirmed produces a
``401`` on the wire is half an assertion.

What the repair actually had to be, and the measurement that decided it
------------------------------------------------------------------------
The obvious repair -- move ``dependencies=[...]`` from ``app.include_router(...)`` to the
``FastAPI(...)`` constructor -- **is a no-op for these four routes and leaves the suite
green.** ``FastAPI.setup()`` installs them with ``self.add_route(...)``, which is
Starlette's ``Router.add_route`` and builds a plain ``starlette.routing.Route``; a ``Route``
has no dependant tree, so no dependency mechanism reaches it. Measured on FastAPI 0.141.1
against a throwaway application whose single dependency raised: ``/thing`` 500, and all four
documentation routes ``200``.

``api/app.py`` therefore suppresses FastAPI's four and declares the same four paths itself
as ``APIRoute``s, which do carry ``app.router.dependencies``.
:func:`test_the_application_serves_no_route_the_seam_cannot_reach` is what would catch a
future editor putting that back.
"""

from __future__ import annotations

import json
from typing import Any, Iterator

import pytest
from fastapi.routing import APIRoute
from starlette.testclient import TestClient

from auditmanager.api.app import DOCUMENTATION_PATHS, OPENAPI_PATH, create_asgi_app
from auditmanager.api.security import (
    UNAUTHENTICATED_OPERATIONS,
    is_authorization_seam,
)
from w13_api_driver import DEPLOYMENT_SECRET, TEST_TOKEN, Surface


@pytest.fixture
def served(router: Surface) -> TestClient:
    """A client over the suite's fully wired application, refusing nothing by default."""
    return TestClient(router.app, raise_server_exceptions=False)


def _credentialed(client: TestClient, path: str) -> Any:
    return client.get(path, headers={"Authorization": f"Bearer {TEST_TOKEN}"})


# --- the structural half: no route escapes, and no path is named ----------------------


def _effective_routes(app: Any) -> Iterator[Any]:
    """Every route object the application will actually match, however it is stored.

    FastAPI 0.141 keeps an *included router* in ``app.routes`` as one lazy container that
    expands to the eighteen effective routes, so a naive ``isinstance(route, APIRoute)``
    walk would see one object it does not recognise and eighteen routes it never inspected.

    **An entry this function cannot read is a failure, never a skip.** That is the whole
    reason it is written out rather than inlined: a FastAPI upgrade that changes how routes
    are stored must redden this guard, not quietly empty it. A checker that classifies what
    it cannot read as "nothing to see" is the shape ``OPERATING_CONSTRAINTS.md`` §12 keeps
    finding, and it is the shape that would let `D-73` come back.
    """
    for entry in app.routes:
        if isinstance(entry, APIRoute):
            yield entry
            continue
        expand = getattr(entry, "effective_candidates", None)
        if callable(expand):
            yield from expand()
            continue
        raise AssertionError(
            f"{type(entry).__name__} at {getattr(entry, 'path', '<no path>')!r} is a route "
            "this guard cannot read, so it cannot say whether the authorization seam "
            "reaches it. Teach this function the new shape rather than excluding it: an "
            "unreadable route is exactly where `D-73` would come back."
        )


def _carries_the_seam(route: Any) -> bool:
    """Walk one route's solved dependant tree looking for the seam's own callable."""
    dependant = getattr(route, "dependant", None)
    if dependant is None:
        return False
    pending = [dependant]
    while pending:
        current = pending.pop()
        if is_authorization_seam(current.call):
            return True
        pending.extend(current.dependencies)
    return False


class TestNoRouteEscapesTheSeam:
    """The guard that has teeth. It names no path, so a fifth route cannot slip past it."""

    def test_the_application_serves_no_route_the_seam_cannot_reach(
        self, router: Surface
    ) -> None:
        naked = [
            f"{sorted(getattr(route, 'methods', None) or ['?'])} {route.path}"
            for route in _effective_routes(router.app)
            if not _carries_the_seam(route)
        ]
        assert naked == [], (
            "these routes are served by the application and carry no authorization seam:\n  "
            + "\n  ".join(naked)
            + "\n`D-73` is exactly this: the seam was attached to the included router, so it "
            "covered the eighteen operations and not the routes the application itself "
            "carried. Attach it to the application (`FastAPI(dependencies=[...])`), not to "
            "`include_router`."
        )

    def test_the_seam_is_attached_to_the_application_and_not_to_the_included_router(
        self, router: Surface
    ) -> None:
        """The positive half, and the one a returned ``dependencies=`` argument fails.

        ``app.router.dependencies`` is what ``add_api_route`` copies onto every route the
        application carries -- the included eighteen *and* the four declared beside them. A
        seam that reached the eighteen through ``include_router`` instead would satisfy
        nothing here, and the four would be open again.
        """
        assert any(
            is_authorization_seam(dependency)
            for dependency in router.app.router.dependencies
        ), (
            "the authorization seam is not among the application's own dependencies. It is "
            "either gone or back on the `include_router(...)` call, which is where `D-73` "
            "came from."
        )

    def test_the_four_routes_exist_and_are_the_ones_the_ruling_names(
        self, router: Surface
    ) -> None:
        """So that the guard above cannot be satisfied by deleting the routes.

        A documentation surface that no longer exists is a different decision from one that
        is closed behind a credential, and `R-31` took the second.
        """
        served_paths = {route.path for route in _effective_routes(router.app)}
        assert set(DOCUMENTATION_PATHS) <= served_paths, (
            f"{sorted(set(DOCUMENTATION_PATHS) - served_paths)} are not served at all. "
            "`R-31` closed these routes; it did not remove them."
        )
        assert set(DOCUMENTATION_PATHS) == {
            OPENAPI_PATH,
            "/docs",
            "/redoc",
            "/docs/oauth2-redirect",
        }

    def test_nothing_was_added_to_the_open_register(self) -> None:
        """The four are guarded by having no ``operationId``, not by an exemption.

        ``_operation_of`` answers ``None`` for a route with no ``operation_id``, ``None`` is
        in no register, and the seam's own rule is that an unreadable route is a closed
        route. If closing these had needed a register entry, the register would have grown
        -- and a register that grows is how the next open operation arrives.
        """
        assert UNAUTHENTICATED_OPERATIONS == frozenset({"issueToken"})

    def test_the_four_declare_no_operation_id(self, router: Surface) -> None:
        by_path = {route.path: route for route in _effective_routes(router.app)}
        for path in DOCUMENTATION_PATHS:
            assert getattr(by_path[path], "operation_id", None) is None, (
                f"{path} declares an operationId. The seam reads one and compares it "
                "against the open register; a documentation route that carried a name "
                "somebody later wrote into that register would reopen `D-73`."
            )


# --- the behavioural half: what a caller actually gets --------------------------------


class TestWithoutACredential:
    @pytest.mark.parametrize("path", DOCUMENTATION_PATHS)
    def test_the_route_refuses(self, served: TestClient, path: str) -> None:
        answer = served.get(path)
        assert answer.status_code == 401, (path, answer.status_code, answer.content[:200])
        assert json.loads(answer.content)["error_code"] == "authentication_required"

    def test_the_surface_description_does_not_leak(self, served: TestClient) -> None:
        """The specific harm `D-73` names, asserted on the bytes.

        Not merely "not 200": the measurement that opened the row was that
        ``/openapi.json`` handed out the whole description **including the shape of
        ``/auth/token``**, which is the one operation an unauthenticated caller can reach.
        """
        body = served.get(OPENAPI_PATH).content
        assert b"/auth/token" not in body
        assert b"IssueTokenRequest" not in body
        assert b"components" not in body


class TestTheDoorWithAHandleOnTheInside:
    def test_the_exchange_is_still_reachable_without_a_credential(
        self, served: TestClient
    ) -> None:
        """`R-31` closes the documentation, not the way in.

        A wrong pair is ``401`` and a right one is ``200``; both prove the request reached
        the operation rather than the seam, but only the ``200`` proves a caller holding
        nothing can still obtain a credential, which is the property that must not break.
        """
        from w13_api_driver import SUITE_LOGIN, SUITE_PASSWORD

        refused = served.post(
            "/auth/token", json={"login": SUITE_LOGIN, "password": "not-the-password"}
        )
        assert refused.status_code == 401, refused.content[:200]

        accepted = served.post(
            "/auth/token", json={"login": SUITE_LOGIN, "password": SUITE_PASSWORD}
        )
        assert accepted.status_code == 200, accepted.content[:200]
        assert json.loads(accepted.content)["token"]


class TestWithACredential:
    """The second thing that must not break: the four serve normally to a caller who has one."""

    @pytest.mark.parametrize("path", DOCUMENTATION_PATHS)
    def test_the_route_answers(self, served: TestClient, path: str) -> None:
        answer = _credentialed(served, path)
        assert answer.status_code == 200, (path, answer.status_code, answer.content[:200])

    def test_the_document_is_the_whole_surface_again(
        self, served: TestClient, router: Surface
    ) -> None:
        """Byte-for-byte what ``app.openapi()`` builds -- closing them changed no content."""
        answer = _credentialed(served, OPENAPI_PATH)
        assert json.loads(answer.content) == router.app.openapi()

    def test_the_three_pages_are_html_and_reference_the_document(
        self, served: TestClient
    ) -> None:
        for path in ("/docs", "/redoc"):
            answer = _credentialed(served, path)
            assert answer.headers["content-type"].startswith("text/html"), path
            assert OPENAPI_PATH.encode() in answer.content, path
        redirect = _credentialed(served, "/docs/oauth2-redirect")
        assert redirect.headers["content-type"].startswith("text/html")


class TestTheDocumentationApplicationIsClosedToo:
    """``create_documentation_app`` has no credential port, so it refuses everything.

    It exists to be read by the conformance gate through ``.openapi()``, never served, and
    a build with nothing behind its ports must not become the one copy of this surface that
    hands the description out.
    """

    @pytest.mark.parametrize("path", DOCUMENTATION_PATHS)
    def test_it_refuses_even_a_genuine_credential(self, path: str) -> None:
        from auditmanager.api.app import create_documentation_app

        client = TestClient(
            create_documentation_app({"AUDITMANAGER_API_TOKEN": DEPLOYMENT_SECRET}),
            raise_server_exceptions=False,
        )
        assert client.get(path).status_code == 401, path
        assert (
            client.get(path, headers={"Authorization": f"Bearer {TEST_TOKEN}"}).status_code
            == 401
        ), path


def test_create_asgi_app_is_the_one_assembly_this_suite_drives() -> None:
    """The guards above are worth what the object under them is worth.

    ``Surface.app`` calls ``create_asgi_app``, which is what the deployment's process calls.
    A suite that assembled its own ``FastAPI`` would be proving something about the suite.
    """
    import inspect

    from w13_api_driver import Surface as DriverSurface

    assert "create_asgi_app" in inspect.getsource(DriverSurface)
    assert callable(create_asgi_app)
