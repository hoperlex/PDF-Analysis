"""``AM001``, ``AM002`` and ``AM003`` become ``state_transition_not_allowed``.

Every refusal here is produced by a **real PostgreSQL trigger** firing on a real
statement. Nothing in this module raises a ``DBAPIError`` by hand: an exception
constructed in a test proves that the middleware can classify an object of that type,
which is not the claim. The claim is that when the database refuses what the contract
forbids, the caller receives the typed code -- and only a statement the database
actually refuses can show that.

The three SQLSTATEs stay distinct at the database so an operator can tell which
invariant fired, and converge on one catalog code at the edge because the caller's
answer is the same: you asked for something the contract forbids.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.api.routers import Router, dispatch
from auditmanager.api.routers.errors import error_code_for, to_domain_error
from auditmanager.api.routers.http import Request, Response, Route, Router as RawRouter
from auditmanager.documents import sqlstate_of
from auditmanager.shared.db.schema import SQLSTATE_TO_CATALOG_CODE

from .conftest import PublishedRun


def _refusal(session: Session, statement: str, params: dict[str, object]) -> DBAPIError:
    """Run a statement the schema refuses and return the driver error it raised.

    The savepoint keeps the enclosing transaction usable: a refused statement aborts
    the current one, and the fixtures still have work to do afterwards.
    """
    with pytest.raises(DBAPIError) as caught:
        with session.begin_nested():
            session.execute(text(statement), params)
    return caught.value


def _envelope(router_for: Router, error: DBAPIError) -> dict:
    """Send one real driver error through the middleware and read the envelope."""

    def handler(_: Request) -> Response:
        raise error

    router = RawRouter([Route("probe", "GET", "/probe", handler)])
    response = dispatch(router, Request.build("GET", "/probe"))
    assert response.status == 409, response.body
    return json.loads(response.body)


# ---------------------------------------------------------------------------
# The three refusals
# ---------------------------------------------------------------------------


def test_am001_a_non_initial_insert_becomes_the_typed_code(
    session: Session, router: Router
) -> None:
    """``AM001``: an aggregate inserted in a state that is not the declared initial one.

    ``blob``'s declared initial state is ``temporary``. Inserting one straight into
    ``available`` is the "created in a state the contract does not declare" case.
    """
    error = _refusal(
        session,
        "INSERT INTO blob (blob_id, state, sha256, size_bytes, media_type) VALUES "
        "('blob_01M2545JSD15ETSNNV904X991A', 'available', "
        "'" + "a" * 64 + "', 1024, 'application/pdf')",
        {},
    )
    assert sqlstate_of(error) == "AM001"

    body = _envelope(router, error)
    assert body["error_code"] == "state_transition_not_allowed"
    assert body["retryable"] is False


def test_am001_an_undeclared_edge_becomes_the_typed_code(
    session: Session, router: Router, published_run: PublishedRun
) -> None:
    """``AM001``: a state column moved along an edge the contract does not declare.

    ``created -> published`` is not a declared ``audit_run`` edge; the declared route
    passes through ``queued``, ``running`` and ``validating``. A terminal is never
    reached by assertion.
    """
    error = _refusal(
        session,
        "UPDATE audit_run SET state = 'published' WHERE run_id = :r",
        {"r": published_run.run_id},
    )
    assert sqlstate_of(error) == "AM001"
    assert _envelope(router, error)["error_code"] == "state_transition_not_allowed"


def test_am002_an_append_only_ledger_refuses_delete(
    session: Session, router: Router, published_run: PublishedRun
) -> None:
    """``AM002``: UPDATE or DELETE on an append-only ledger.

    The event deleted here was really appended: it went through
    ``auditmanager.decisions.record_decision`` against a really published finding.
    """
    from auditmanager.decisions import record_decision

    event = record_decision(
        session,
        finding_uid=published_run.finding_uid,
        finding_observation_id=published_run.finding_observation_id,
        event_type="accept",
    )

    error = _refusal(
        session,
        "DELETE FROM expert_decision_event WHERE decision_id = :d",
        {"d": event.decision_id},
    )
    assert sqlstate_of(error) == "AM002"
    assert _envelope(router, error)["error_code"] == "state_transition_not_allowed"

    updated = _refusal(
        session,
        "UPDATE expert_decision_event SET event_type = 'reject' WHERE decision_id = :d",
        {"d": event.decision_id},
    )
    assert sqlstate_of(updated) == "AM002"
    assert _envelope(router, updated)["error_code"] == "state_transition_not_allowed"


def test_am003_an_immutable_row_refuses_update(
    session: Session, router: Router, published_run: PublishedRun
) -> None:
    """``AM003``: UPDATE or DELETE on an immutable published row.

    ``document_version`` is immutable after insert: a corrected source file is a new
    ``version_uid``, never an edit. This is what makes ``getDocumentVersion`` safe to
    describe as "a published, immutable input state".
    """
    error = _refusal(
        session,
        "UPDATE document_version SET page_count = 29 WHERE version_uid = :v",
        {"v": published_run.version_uid},
    )
    assert sqlstate_of(error) == "AM003"
    assert _envelope(router, error)["error_code"] == "state_transition_not_allowed"


def test_am003_immutable_evidence_refuses_delete(
    session: Session, router: Router, published_run: PublishedRun
) -> None:
    """``AM003`` on emitted evidence: a rerun never rewrites an earlier observation."""
    error = _refusal(
        session,
        "DELETE FROM finding_observation WHERE finding_observation_id = :o",
        {"o": published_run.finding_observation_id},
    )
    assert sqlstate_of(error) == "AM003"
    assert _envelope(router, error)["error_code"] == "state_transition_not_allowed"


# ---------------------------------------------------------------------------
# The mapping itself
# ---------------------------------------------------------------------------


def test_all_three_sqlstates_are_covered_by_this_module(session: Session) -> None:
    """Every custom SQLSTATE in the shared map was produced by a real statement above.

    Read from ``SQLSTATE_TO_CATALOG_CODE`` rather than listed here, so a fourth custom
    SQLSTATE added to the head fails this test instead of quietly going unmapped at the
    edge.
    """
    exercised = {"AM001", "AM002", "AM003"}
    assert set(SQLSTATE_TO_CATALOG_CODE) == exercised, (
        "the migration head declares a custom SQLSTATE this suite does not exercise: "
        f"{sorted(set(SQLSTATE_TO_CATALOG_CODE) - exercised)}"
    )
    assert set(SQLSTATE_TO_CATALOG_CODE.values()) == {"state_transition_not_allowed"}


def test_the_middleware_maps_on_sqlstate_and_not_on_message_text(
    session: Session, router: Router
) -> None:
    """A refusal whose message says nothing recognisable still maps, by its SQLSTATE.

    The trigger messages all begin with the literal ``state_transition_not_allowed``,
    so a middleware that matched on text would pass every test above while being wrong.
    This raises the same SQLSTATE from a message with none of that vocabulary in it.
    """
    error = _refusal(
        session,
        "DO $$ BEGIN RAISE EXCEPTION 'нет' USING ERRCODE = 'AM002'; END $$",
        {},
    )
    assert sqlstate_of(error) == "AM002"
    assert "state_transition" not in str(error.orig)

    body = _envelope(router, error)
    assert body["error_code"] == "state_transition_not_allowed"


def test_an_ordinary_database_fault_is_not_a_contract_refusal(
    session: Session, router: Router
) -> None:
    """A refusal that is not one of the three is ``internal_error``, not a typed refusal.

    A unique violation is a genuine integrity fault. Reporting it as
    ``state_transition_not_allowed`` would tell a caller the contract forbids what it
    asked for, which is a different and wrong statement.
    """
    session.execute(text("INSERT INTO project (project_uid, name) VALUES (:p, 'x')"), {"p": "prj_01M2545JSD15ETSNNV904X991B"})
    error = _refusal(
        session,
        "INSERT INTO project (project_uid, name) VALUES (:p, 'y')",
        {"p": "prj_01M2545JSD15ETSNNV904X991B"},
    )
    assert sqlstate_of(error) == "23505"
    assert error_code_for(error) is None
    assert to_domain_error(error).code.value == "internal_error"


def test_the_driver_message_never_reaches_the_envelope(
    session: Session, router: Router, published_run: PublishedRun
) -> None:
    """The envelope carries the catalog summary, not the trigger's prose.

    A PostgreSQL message can carry a row value, a table name or a fragment of SQL. The
    trigger message here names the table; the envelope must not.
    """
    error = _refusal(
        session,
        "UPDATE document_version SET page_count = 29 WHERE version_uid = :v",
        {"v": published_run.version_uid},
    )
    driver_text = str(error.orig)
    assert "document_version" in driver_text

    body = _envelope(router, error)
    assert "document_version" not in json.dumps(body)
    assert published_run.version_uid not in json.dumps(body)
