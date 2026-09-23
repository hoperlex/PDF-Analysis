"""`D-67`, the half a sweep for ``404`` cannot see: an empty collection is still a ``200``.

``tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`` drives every
``GET`` of the composed surface with an identity that names nothing and requires
``404 not_found`` from the ten that address a parent. **That sweep is satisfied by an
implementation that has destroyed the distinction it exists to protect**: refusing every
empty collection with ``404`` would pass it, and a client would then be unable to tell
*"this run published no findings"* from *"there is no such run"* in the other direction.

So the rule has two halves and this file holds the second one, over parents that really
exist and really have no children:

* a run that published nothing answers a page with no items, not ``404``;
* a finding nobody has decided on answers a ledger with no events, not ``404``;
* a project with no documents answers a page with no items -- the control, because
  ``listDocuments`` already refused an absent parent before `D-67` and must not have
  started refusing an empty one.

The parents are real rows, published through the same fixtures the rest of this suite uses,
and the router is ``shipped_router`` -- the real ``FindingAdapter`` and ``DecisionAdapter``
-- because a fixture adapter that answers an empty page proves that the fixture answers one.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from w13_api_driver import Surface

from .conftest import PublishedRun

#: An identity of the right shape that this deployment has never minted.
ABSENT_RUN = "run_01ARZ3NDEKTSV4RRFFQ69G5FAV"
ABSENT_FINDING = "fnd_01ARZ3NDEKTSV4RRFFQ69G5FAV"
ABSENT_PROJECT = "prj_01ARZ3NDEKTSV4RRFFQ69G5FAV"


def _page(surface: Surface, target: str) -> Any:
    answer = surface.send("GET", target)
    assert answer.status == 200, (answer.status, answer.body)
    body = answer.json()
    assert isinstance(body.get("items"), list), body
    return body


def _refusal(surface: Surface, target: str) -> Any:
    answer = surface.send("GET", target)
    assert answer.status == 404, (answer.status, answer.body)
    body = answer.json()
    assert body["error_code"] == "not_found", body
    return body


def test_a_run_that_published_nothing_answers_an_empty_page(
    shipped_router: Surface, session: Session
) -> None:
    """The strongest form of the second half: a real run whose findings are genuinely none.

    ``PublishedRun`` with no observations writes the run row and publishes nothing, so this
    is not a filter answering nothing -- it is the collection itself being empty. A repair
    that refused every empty collection with ``404`` would redden here and nowhere in the
    composition sweep.
    """
    empty = PublishedRun(session, observations=[])
    body = _page(shipped_router, f"/runs/{empty.run_id}/findings")
    assert body["items"] == [], body


def test_a_finding_nobody_has_decided_on_answers_an_empty_ledger(
    shipped_router: Surface, published_run: Any
) -> None:
    """A real finding, a real empty history, and a ``200``.

    ``published_run`` appends no decision, so this finding's ledger is genuinely empty. Before
    `D-67` this answer and the answer for a finding that does not exist were the same bytes.
    """
    body = _page(
        shipped_router, f"/findings/{published_run.finding_uid}/decisions"
    )
    assert body["items"] == [], body


def test_a_finding_that_does_not_exist_is_refused(
    shipped_router: Surface, published_run: Any
) -> None:
    """The other half, on the same surface and in the same process as the case above.

    Together they are the whole of `D-67` for this operation: the two questions now have two
    answers. ``published_run`` is requested so that the two cases run against one database
    state and the difference cannot be a difference of fixtures.
    """
    _refusal(shipped_router, f"/findings/{ABSENT_FINDING}/decisions")


def test_a_run_that_does_not_exist_is_refused_by_its_findings_collection(
    shipped_router: Surface, published_run: Any
) -> None:
    _refusal(shipped_router, f"/runs/{ABSENT_RUN}/findings")


def test_a_run_that_exists_still_answers_its_findings(
    shipped_router: Surface, published_run: Any
) -> None:
    """The control for the case above: the repair must refuse the absent run and only it."""
    body = _page(shipped_router, f"/runs/{published_run.run_id}/findings")
    assert body["items"], "the published run answered no findings, so the case is vacuous"


def test_a_run_that_exists_answers_an_empty_page_for_a_filter_nothing_matches(
    shipped_router: Surface, published_run: Any
) -> None:
    """A page with no items, from a parent that exists. `D-67` must not collapse this to 404.

    The filter is the cheapest way to reach "this parent has no children of the kind you
    asked for" without a second published run, and it is the same answer shape.
    """
    absent = "explicit_placeholder"
    present = {item["category"] for item in _page(
        shipped_router, f"/runs/{published_run.run_id}/findings?limit=200"
    )["items"]}
    assert absent not in present, "pick a category this run really does not publish"
    body = _page(
        shipped_router, f"/runs/{published_run.run_id}/findings?category={absent}"
    )
    assert body["items"] == [], body


def test_a_project_with_no_documents_answers_an_empty_page(
    shipped_router: Surface,
) -> None:
    """The control that `D-67` changed nothing where nothing needed changing.

    ``listDocuments`` refused an absent parent before this wave and answers an empty page for
    a present one. Both are asserted here so that a later repair applied to the wrong six
    operations reddens.
    """
    created = shipped_router.send(
        "POST",
        "/projects",
        headers={
            "content-type": "application/json",
            "Idempotency-Key": f"d67-empty-{uuid.uuid4().hex[:16]}",
        },
        body=b'{"name": "\\u041f\\u0443\\u0441\\u0442\\u043e\\u0439 \\u043f\\u0440\\u043e\\u0435\\u043a\\u0442"}',
    )
    assert created.status == 201, created.body
    project_uid = created.json()["project_uid"]

    body = _page(shipped_router, f"/projects/{project_uid}/documents")
    assert body["items"] == [], body
    _refusal(shipped_router, f"/projects/{ABSENT_PROJECT}/documents")
