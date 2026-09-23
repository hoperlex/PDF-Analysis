"""The surface is exactly the seventeen operations the frozen document declares.

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


def test_the_document_declares_seventeen_and_the_router_implements_seventeen(
    router: Surface, openapi_document: dict[str, Any]
) -> None:
    """The count is checked separately from the set.

    Equal sets with an unexpected size would mean the document itself had changed, and
    the document is sealed. This is the assertion that notices that.

    **Twelve until the `R-5` reseal of 2026-09-18**, which added `listDocuments`,
    `listVersions` and `listRuns`; **fifteen until `W34-CONTRACT`**, which added
    `issueToken`, the credential exchange; **sixteen until `W38-KB`**, which added
    `listDecisions` under `R-24`. The number moved because an owner ruling moved it;
    nothing else may move it.
    """
    assert len(declared_operations(openapi_document)) == 17
    assert len(router.routes) == 17


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
        "document_uid": "doc_01M2545JSD15ETSNNV904X991H",
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


def test_no_eighteenth_operation_answers(router: Surface) -> None:
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


def test_the_document_declares_no_operation_outside_the_declared_capabilities(
    openapi_document: dict[str, Any],
) -> None:
    """No tenancy, WebSocket, export resource or polling endpoint, and no auth *endpoint*.

    The frozen document's own description says the surface deliberately has none of
    these. This asserts the absence rather than trusting the prose, so a later widening
    of the document is visible here too.

    Until the wave-13 reseal this also asserted that `components.securitySchemes` was
    absent, with the reason "PC-01 has no authentication and no role model". Owner
    ruling `R-3` of 2026-09-17 reversed the premise, so the assertion is inverted rather
    than deleted: the scheme must now be there.

    **Wave 34 moved the line again, and by exactly one path.** `R-3`'s seam was a header
    the deployment satisfied, so `/auth` was forbidden outright. `W34-CONTRACT` declared
    the operation that hands that header's value out, which is the one endpoint the seam
    cannot be satisfied without -- so the rule is widened by a *register of exact paths*
    and not by dropping the fragment: `/auth/token` is admitted, `/auth/anything-else` is
    still a widening and still fails here, and `/login`, `/token` and the rest are
    untouched. `tests/contract/domain_p02/test_openapi_document.py` owns the shape of the
    scheme itself.

    **Wave 39 moved it again, by exactly one more path, and the register is the reason that
    is a small statement rather than a large one.** `W39-REVOKE` declared `/auth/password`,
    the operation that changes a password and revokes every credential minted under the old
    one. It is admitted by name. `/auth/users`, `/auth/register`, `/auth/roles` and
    everything else under the fragment are still a widening and still fail here -- which is
    precisely the property a rule of "anything under `/auth`" would have thrown away, and
    the reason `W34-CONTRACT` wrote a register instead of relaxing the fragment.
    """
    paths = set(openapi_document["paths"])
    #: The exact paths admitted under an otherwise forbidden fragment. Exact, because
    #: "anything under /auth" would readmit the user management this surface does not have.
    ADMITTED = {"/auth/token", "/auth/password"}
    forbidden = ("/auth", "/login", "/token", "/tenants", "/exports", "/jobs", "/imports")
    for fragment in forbidden:
        trespassers = sorted(
            path
            for path in paths
            if path.startswith(fragment) and path not in ADMITTED
        )
        assert not trespassers, (
            f"the document declares {trespassers} under {fragment}, which PC-01 excludes"
        )
    assert ADMITTED <= paths, (
        f"{sorted(ADMITTED - paths)} is registered as an admitted exception and is not in "
        "the document; a register that names a path nobody declares excuses nothing and "
        "hides the next one"
    )
    assert "components" in openapi_document
    assert list(openapi_document["components"]["securitySchemes"]) == ["bearerAuth"], (
        "the authorization seam is one bearer scheme declared once, per R-3"
    )
    assert len(paths) == 15 and sum(
        1
        for item in openapi_document["paths"].values()
        for method in item
        if method in {"get", "put", "post", "delete", "options", "head", "patch"}
    ) == 18, (
        "10 paths / 12 operations before the `R-5` reseal, 12 / 15 after it, 13 / 16 "
        "after `W34-CONTRACT` added the credential exchange, 14 / 17 after `W38-KB` added "
        "the decision journal under `R-24`, 15 / 18 after `W39-REVOKE` added the password "
        "change under `R-26`. The three operations `R-5` added are named in "
        "`REQUIRED_OPERATIONS`; the one wave 34 added is `issueToken`, and it is the only "
        "one this surface answers without a credential; the one wave 38 added is "
        "`listDecisions`, and it is the only listing with no parent in its path; the one "
        "wave 39 added is `changePassword`, and it is the only operation that invalidates "
        "the credential it was called with."
    )
