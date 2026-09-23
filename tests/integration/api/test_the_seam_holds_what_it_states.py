"""`D-66` -- the two properties `auditmanager.api.security` states in prose and nothing held.

`W37-CERT4` swept the authorization seam with six mutations. Four reddened. **Two did not**,
and both of them are properties the module writes down as properties:

* ``_operation_of``: *"An unreadable route is a closed route."* Inverting the default -- so
  that a route the seam cannot identify is exempted rather than guarded -- left
  ``test_authorization.py``, ``tests/integration/auth`` and
  ``test_api_token_channel.py`` at **77 passed**. Every route on the built application
  carries an ``operationId`` today, so the claim is true and untested, and the day it stops
  being true is the only day the default decides anything.
* ``TokenSigner.verify``: *"a short-circuiting one leaks its length and its prefix to a
  caller who can time it."* Replacing :func:`hmac.compare_digest` with ``!=`` changed no
  answer this surface gives, so nothing reddened.

**What the two halves of this file prove is not the same kind of thing, and the difference
is stated rather than left to be assumed.**

The fail-closed half is **behavioural**: it builds a real surface carrying a route with no
``operationId``, drives it through the real application, and asserts the seam refuses it.
Nothing about the source is read.

The comparison half is narrower and says so. A constant-time comparison and a
short-circuiting one return the same answers -- that is the entire point of the property --
so no assertion over answers can separate them, and a timing measurement inside a gate is a
flaky test rather than a guard. What these two tests prove is that the seam **calls**
:func:`hmac.compare_digest` on the tag and **branches on what it returns**: the second one
makes the function say yes to a forged tag and requires the credential to be accepted, so a
re-implementation that compares with ``==`` or ``!=`` -- with or without the call left
beside it -- fails here. **It does not prove the comparison is constant-time**; that
property is `hmac`'s, and this file takes it from the standard library rather than
re-measuring it. `D-61` is what this file is being careful not to be: a guard that matches a
name instead of a behaviour.
"""

from __future__ import annotations

import base64
import hmac
from typing import Any

import pytest

from auditmanager.api.routers import Router
from auditmanager.api.security import (
    API_TOKEN_VARIABLE,
    UNAUTHENTICATED_OPERATIONS,
    _operation_of,
    build_signer,
)
from w13_api_driver import (
    DEPLOYMENT_SECRET,
    TEST_SUBJECT,
    TEST_TOKEN,
    Surface,
    SuiteCredentialAdapter,
)

#: The catalog's summary for the code the seam answers with. A literal, as everywhere else
#: in this suite: derived from the enum it would move with the thing under test.
AUTHENTICATION_REQUIRED = "authentication_required"

#: The path of the route with no ``operationId``. Not one the contract declares, and it must
#: not be: the point is a route the *document* has never heard of.
UNIDENTIFIABLE = "/a-route-with-no-operation-id"


def _a_surface_carrying_an_unidentifiable_route() -> Surface:
    """A real `Router`, a real credential port, and one route registered without an id.

    ``Router`` rather than a bare ``APIRouter`` for the reason ``probe_surface`` gives: the
    seam reads the account's credential generation through the port the router carries, and
    a router with none refuses everything -- which would make every assertion below pass for
    the wrong reason.
    """
    router = Router(credentials=SuiteCredentialAdapter())

    @router.get(UNIDENTIFIABLE, tags=["unidentifiable"])
    def handler() -> Any:
        return {"the seam let this through": True}

    return Surface(router)


def _the_unidentifiable_route(surface: Surface) -> Any:
    for route in surface.router.routes:
        if getattr(route, "path", None) == UNIDENTIFIABLE:
            return route
    raise AssertionError(f"the fixture registered no route at {UNIDENTIFIABLE}")


# --- the fail-closed default -------------------------------------------------------


def test_the_fixtures_route_really_carries_no_operation_id() -> None:
    """The anti-vacuity of everything below it.

    If FastAPI assigned an ``operationId`` to a route declared without one, the three cases
    that follow would be asserting the ordinary guarded path and the default they exist for
    would stay untested. They would still pass. So this reads the attribute the seam reads,
    through the function the seam calls, and requires the answer to be ``None``.
    """
    route = _the_unidentifiable_route(_a_surface_carrying_an_unidentifiable_route())
    assert getattr(route, "operation_id", None) is None, (
        "the route under test carries an operationId, so it does not exercise the default"
    )
    assert None not in UNAUTHENTICATED_OPERATIONS, (
        "the register contains None, so an unreadable route is exempt by membership"
    )


def test_a_route_the_seam_cannot_identify_is_refused_without_a_credential() -> None:
    """`W37CERT4-5`. The mutation that used to leave three suites at 77 green.

    The seam's own words: *"Everything else -- including a request whose route the seam
    could not identify -- must present a credential this deployment's key produced."*
    """
    surface = _a_surface_carrying_an_unidentifiable_route()
    answer = surface.send("GET", UNIDENTIFIABLE, credential=None)
    assert answer.status == 401, answer.body
    assert answer.json()["error_code"] == AUTHENTICATION_REQUIRED


def test_a_route_the_seam_cannot_identify_refuses_another_deployments_credential() -> None:
    """The same default, against a credential that is well-formed and not this deployment's.

    Separate from the case above because "no credential at all" is refused by the
    ``credentials is None`` arm, and this one has to reach ``verify``. An exemption would
    skip both.
    """
    signer = build_signer({API_TOKEN_VARIABLE: "some-other-deployments-secret"})
    assert signer is not None
    surface = _a_surface_carrying_an_unidentifiable_route()
    answer = surface.send(
        "GET", UNIDENTIFIABLE, credential=signer.issue(TEST_SUBJECT).token
    )
    assert answer.status == 401, answer.body
    assert answer.json()["error_code"] == AUTHENTICATION_REQUIRED


def test_the_unidentifiable_route_is_reachable_with_a_credential_this_deployment_minted() -> None:
    """The control, and it is not decoration.

    Without it, both refusals above would pass against a surface where the route simply did
    not exist, or where every request to it failed for some reason that has nothing to do
    with the seam. *Guarded* means "refused without a credential and served with one", and
    only the pair says that.
    """
    surface = _a_surface_carrying_an_unidentifiable_route()
    answer = surface.send("GET", UNIDENTIFIABLE, credential=TEST_TOKEN)
    assert answer.status == 200, answer.body
    assert answer.json() == {"the seam let this through": True}


def test_an_operation_id_that_is_not_a_string_reads_as_unidentifiable() -> None:
    """``_operation_of`` narrows to ``str`` and the narrowing is part of the default.

    A route object whose ``operation_id`` is some other object -- which is what a wrapper, a
    mock or a generator that got it wrong would leave there -- must read as ``None`` and be
    guarded, not be passed to a set membership test that answers ``False`` for a different
    reason and happens to land on the same behaviour.
    """

    class _Request:
        def __init__(self, route: Any) -> None:
            self.scope = {"route": route}

    class _Route:
        def __init__(self, operation_id: Any) -> None:
            self.operation_id = operation_id

    assert _operation_of(_Request(_Route(7))) is None  # type: ignore[arg-type]
    assert _operation_of(_Request(_Route(None))) is None  # type: ignore[arg-type]
    assert _operation_of(_Request(None)) is None  # type: ignore[arg-type]
    assert _operation_of(_Request(_Route("issueToken"))) == "issueToken"  # type: ignore[arg-type]


# --- the timing-safe comparison ----------------------------------------------------


def _signer() -> Any:
    signer = build_signer({API_TOKEN_VARIABLE: DEPLOYMENT_SECRET})
    assert signer is not None, "this suite's own secret derives a signing key"
    return signer


def _with_a_forged_tag(credential: str) -> str:
    """The same credential with a tag this deployment's key did not produce.

    Well-formed in every other way -- three parts, the format version, a payload that
    decodes -- so that the tag comparison is the only thing that can refuse it.
    """
    version, body, tag = credential.split(".")
    forged = base64.urlsafe_b64encode(b"not this deployment's tag").decode("ascii").rstrip("=")
    assert forged != tag
    return f"{version}.{body}.{forged}"


def test_the_tag_comparison_goes_through_hmac_compare_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The call site, observed at run time rather than grepped out of the source.

    A test that read ``compare_digest`` out of ``security.py`` would pass against a module
    that imported it and compared with ``==`` two lines later. This one records the calls
    the standard library function actually receives while a genuine credential is verified,
    and requires the presented tag and the recomputed one to be among them.
    """
    signer = _signer()
    credential = signer.issue(TEST_SUBJECT).token

    seen: list[tuple[bytes, bytes]] = []
    real = hmac.compare_digest

    def spy(left: Any, right: Any) -> bool:
        seen.append((bytes(left), bytes(right)))
        return real(left, right)

    monkeypatch.setattr(hmac, "compare_digest", spy)
    assert signer.verify(credential) is not None, "the control credential must verify"

    assert seen, "verify() compared the tag without calling hmac.compare_digest"
    presented = base64.urlsafe_b64decode(
        credential.split(".")[2] + "=" * (-len(credential.split(".")[2]) % 4)
    )
    assert any(presented in pair for pair in seen), (
        f"hmac.compare_digest was called, but never on the presented tag: {seen}"
    )


def test_the_seam_branches_on_what_that_comparison_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`W37CERT4-6`. The case that separates a call from a decision.

    `D-34` is the shape this avoids: a guard that asserted the string beside the value the
    code branched on, and so pinned a defect instead of catching it. Here the comparison is
    made to answer **yes** for a tag this deployment did not produce. If
    :func:`hmac.compare_digest` is what decides, the forged credential is accepted; if the
    decision is taken by an ``==`` or a ``!=`` -- whether or not the call is still there
    beside it -- the forgery is refused and this fails.

    It is still not a measurement of constant time. Nothing in a gate can be. What it
    forecloses is every re-implementation that reaches the same answers by comparing the
    bytes itself, which is the one `W37-CERT4`'s mutation wrote.
    """
    signer = _signer()
    forged = _with_a_forged_tag(signer.issue(TEST_SUBJECT).token)

    assert signer.verify(forged) is None, (
        "the control failed: a forged tag was accepted by the real comparison"
    )

    monkeypatch.setattr(hmac, "compare_digest", lambda left, right: True)
    assert signer.verify(forged) is not None, (
        "hmac.compare_digest answered yes and the credential was still refused, so "
        "something other than that call decides whether the tag matches"
    )
