"""The surface is exactly the twelve operations the frozen document declares.

Asserted **against the document**, never against a list written out here. A list in a
test is a second declaration that can drift from the first, and the whole reason
``contracts/api/v1/openapi.json`` is frozen is that ``A5`` generates the typed client
from it: a thirteenth operation in the router with no counterpart in the document is a
surface the frontend cannot see, and a missing one is a client call with no server.
"""

from __future__ import annotations

from typing import Any

import pytest

from w13_api_driver import Request, Surface, dispatch

_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")


def declared_operations(document: dict[str, Any]) -> set[tuple[str, str, str]]:
    """``(operationId, METHOD, template)`` for every operation in the document."""
    found: set[tuple[str, str, str]] = set()
    for path, item in document["paths"].items():
        for method, operation in item.items():
            if method in _METHODS:
                found.add((operation["operationId"], method.upper(), path))
    return found


def test_the_router_declares_exactly_the_frozen_operations(
    router: Surface, openapi_document: dict[str, Any]
) -> None:
    declared = declared_operations(openapi_document)
    implemented = set(router.signature())

    assert implemented == declared, (
        "the router and contracts/api/v1/openapi.json disagree.\n"
        f"declared but not implemented: {sorted(declared - implemented)}\n"
        f"implemented but not declared: {sorted(implemented - declared)}"
    )


def test_the_document_declares_twelve_and_the_router_implements_twelve(
    router: Surface, openapi_document: dict[str, Any]
) -> None:
    """The count is checked separately from the set.

    Equal sets with an unexpected size would mean the document itself had changed, and
    the document is frozen. This is the assertion that notices that.
    """
    assert len(declared_operations(openapi_document)) == 12
    assert len(router.routes) == 12


def test_every_declared_operation_is_reachable(
    router: Surface, openapi_document: dict[str, Any]
) -> None:
    """Every operation resolves to a handler for its own method.

    Reachability, not behaviour: each path template is filled with a syntactically
    valid identity and matched. A route that existed in the table but could never be
    matched -- a template typo, a placeholder that swallows a slash -- would pass the
    set comparison above and fail here.
    """
    samples = {
        "project_uid": "prj_01M2545JSD15ETSNNV904X991F",
        "version_uid": "ver_01M2545JSD15ETSNNV904X991J",
        "run_id": "run_01M2545JSD15ETSNNV904X991K",
        "finding_uid": "fnd_01M2545JSD15ETSNNV904X991M",
    }
    for operation_id, method, template in sorted(declared_operations(openapi_document)):
        path = template
        for name, value in samples.items():
            path = path.replace("{" + name + "}", value)
        assert "{" not in path, f"{operation_id}: unfilled placeholder in {template}"

        route, bound = router.match(Request.build(method, path))
        assert route.operation_id == operation_id, (
            f"{method} {path} resolved to {route.operation_id}, not {operation_id}"
        )
        for name in samples:
            if "{" + name + "}" in template:
                assert bound[name] == samples[name]


def test_no_thirteenth_operation_answers(router: Surface) -> None:
    """A path the document does not declare is not a resource.

    Includes a method the document does not declare on a path that *is* declared:
    ``DELETE /projects`` must not delete projects, and the answer is the same
    ``not_found`` a stranger's path gets, so the surface reveals nothing about which
    methods exist.
    """
    undeclared = (
        ("GET", "/exports"),
        ("POST", "/versions/ver_01M2545JSD15ETSNNV904X991J"),
        ("DELETE", "/projects"),
        ("PATCH", "/findings/fnd_01M2545JSD15ETSNNV904X991M"),
        ("GET", "/runs/run_01M2545JSD15ETSNNV904X991K/export.json"),
        ("GET", "/"),
    )
    for method, path in undeclared:
        response = dispatch(router, Request.build(method, path))
        assert response.status == 404, f"{method} {path} answered {response.status}"


def test_the_document_declares_no_operation_outside_the_twelve_capabilities(
    openapi_document: dict[str, Any],
) -> None:
    """No tenancy, WebSocket, export resource or polling endpoint, and no auth *endpoint*.

    The frozen document's own description says the surface deliberately has none of
    these. This asserts the absence rather than trusting the prose, so a later widening
    of the document is visible here too.

    Until the wave-13 reseal this also asserted that `components.securitySchemes` was
    absent, with the reason "PC-01 has no authentication and no role model". Owner
    ruling `R-3` of 2026-09-17 reversed the premise, so the assertion is inverted rather
    than deleted: the scheme must now be there, and `/auth`, `/login` and `/token` must
    still not be, because the seam is a header the deployment satisfies and never a
    thirteenth operation. `tests/contract/domain_p02/test_openapi_document.py` owns the
    shape of the scheme itself.
    """
    paths = set(openapi_document["paths"])
    forbidden = ("/auth", "/login", "/token", "/tenants", "/exports", "/jobs", "/imports")
    for fragment in forbidden:
        assert not any(path.startswith(fragment) for path in paths), (
            f"the document declares a path under {fragment}, which PC-01 excludes"
        )
    assert "components" in openapi_document
    assert list(openapi_document["components"]["securitySchemes"]) == ["bearerAuth"], (
        "the authorization seam is one bearer scheme declared once, per R-3"
    )
    assert len(paths) == 10 and sum(
        1
        for item in openapi_document["paths"].values()
        for method in item
        if method in {"get", "put", "post", "delete", "options", "head", "patch"}
    ) == 12, "the seam added an operation; it is a header, not a thirteenth endpoint"
