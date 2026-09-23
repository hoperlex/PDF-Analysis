"""`D-78`. A decision is attributed to the reviewer who made it.

Until this wave ``auditmanager.decisions.ledger`` carried::

    CONFIGURED_AUTHOR_LABEL: Final[str] = "local-reviewer"

and every verdict by every reviewer went into ``expert_decision_event.author_label`` as
that one string. ``OD-18`` wants three to five named experts in the alpha and ``P04``
exists to learn *whose* judgement was whose, so a constant there is `P04` measuring
nothing it was built to measure.

**The rule that survives.** The label is still never taken from a request body -- a
client-supplied "who did this" would be a subject identity in all but name, and an
operation one reviewer could aim at another. What changed is where it comes from instead:
the verified ``Subject`` the authorization seam publishes, which
``auditmanager.api.security.CurrentSubject`` hands to the one handler that needs it.

**The rule that was false.** The module note said *"PC-01 has no authentication"*. It has
had since wave 34: ``security.py`` builds a ``Subject`` on every authenticated request.
What was missing was not the identity but a route that could see it.

**Two credentials, two logins, two rows.** The suite in ``conftest.py`` has exactly one
account, which cannot distinguish "the label follows the caller" from "the label is a
constant that happens to equal this caller's login". So this module wires its own
credential port over two accounts and drives the **shipped** ``DecisionAdapter``: a
fixture adapter that wrote the label would prove that the fixture writes it.
"""

from __future__ import annotations

import inspect
import uuid
from dataclasses import dataclass
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.api.routers import build_router
from auditmanager.api.security import API_TOKEN_VARIABLE, Subject, build_signer
from w13_api_driver import DEPLOYMENT_SECRET, Surface

from .conftest import (
    IngestDocumentAdapter,
    IngestProjectAdapter,
    PublishedRun,
    SeamExportAdapter,
    SeamRunAdapter,
)

_SIGNER = build_signer({API_TOKEN_VARIABLE: DEPLOYMENT_SECRET})
assert _SIGNER is not None, "this module's secret derives a signing key"


@dataclass(frozen=True, slots=True)
class _Account:
    """One reviewer this module's credential port knows about."""

    user_uid: str
    login: str
    epoch: int
    password: str


#: Two accounts with **different logins and different epochs**. Different epochs so that a
#: seam which ignored the credential's epoch could not pass by defaulting to a shared one,
#: which is the reason ``driver.py`` pins its own epoch away from 1.
ANNA = _Account("usr_01M2545JSD15ETSNNV904X991Q", "anna.petrova", 7, "anna-password")
BORIS = _Account("usr_01M2545JSD15ETSNNV904X992R", "boris.smirnov", 3, "boris-password")
ACCOUNTS = (ANNA, BORIS)


def credential_for(account: _Account) -> str:
    """A credential this deployment really minted for ``account``.

    Minted rather than written down, for ``driver.py``'s reason: a literal could not carry
    an expiry and would have to be re-minted by hand at every change to the format.
    """
    return _SIGNER.issue(
        Subject(
            user_uid=account.user_uid, login=account.login, token_epoch=account.epoch
        )
    ).token


class TwoAccountCredentialAdapter:
    """``CredentialPort`` over two accounts, in memory.

    Deliberately answers ``epoch_of`` for both and for nothing else: an account this
    deployment does not have is ``None``, which the seam reads as a refusal.
    """

    __slots__ = ()

    def issue(self, *, login: str, password: str) -> Any:
        for account in ACCOUNTS:
            if (login, password) == (account.login, account.password):
                return _SIGNER.issue(
                    Subject(
                        user_uid=account.user_uid,
                        login=account.login,
                        token_epoch=account.epoch,
                    )
                )
        return None

    def change_password(
        self, *, user_uid: str, current_password: str, new_password: str
    ) -> Any:  # pragma: no cover - this module drives no password change
        raise AssertionError("this module does not drive changePassword")

    def epoch_of(self, user_uid: str) -> int | None:
        for account in ACCOUNTS:
            if account.user_uid == user_uid:
                return account.epoch
        return None


@pytest.fixture
def two_reviewer_router(
    ingest: Any, session: Session, session_factory: sessionmaker[Session]
) -> Surface:
    """The surface over the **shipped** decision adapter and two accounts.

    ``DecisionAdapter`` and ``FindingAdapter`` are
    ``auditmanager.bootstrap.adapters``' own, on this suite's savepoint-joined factory, for
    the reason ``shipped_router`` gives: a fixture adapter that carried the label would
    prove only that the fixture carries it.
    """
    from auditmanager.bootstrap.adapters import DecisionAdapter, FindingAdapter

    return Surface(
        build_router(
            projects=IngestProjectAdapter(ingest),
            documents=IngestDocumentAdapter(ingest, session),
            runs=SeamRunAdapter(session),
            findings=FindingAdapter(session_factory),
            decisions=DecisionAdapter(session_factory),
            exports=SeamExportAdapter(session),
            credentials=TwoAccountCredentialAdapter(),
        )
    )


def _append(
    surface: Surface, published_run: PublishedRun, *, credential: str, event: str = "accept"
) -> Any:
    """One ``appendDecision``, presented with ``credential``."""
    import json

    body = json.dumps(
        {
            "finding_observation_id": published_run.finding_observation_id,
            "event_type": event,
            "comment": "Проверено.",
        }
    ).encode("utf-8")
    return surface.send(
        "POST",
        f"/findings/{published_run.finding_uid}/decisions",
        headers={
            "Content-Type": "application/json",
            "Idempotency-Key": f"w41-author-{uuid.uuid4()}",
        },
        body=body,
        credential=credential,
    )


def _stored_labels(session: Session, finding_uid: str) -> list[str]:
    """The labels the database really holds, read back rather than taken from a response."""
    rows = session.execute(
        text(
            "SELECT author_label FROM expert_decision_event "
            "WHERE finding_uid = :f ORDER BY sequence_no"
        ),
        {"f": finding_uid},
    ).scalars()
    return list(rows)


class TestTwoReviewersAreTwoAuthors:
    def test_two_credentials_record_two_distinguishable_authors(
        self, two_reviewer_router: Surface, published_run: PublishedRun, session: Session
    ) -> None:
        """The acceptance for `D-78`, and the one a single account cannot state.

        Two different credentials, two appended events, two different labels -- **and the
        labels are the two logins**, asserted against the literals this module declares
        rather than against anything the ledger exports. A test that imported the value it
        expects from the module under test is exactly what kept `W12-DEC`'s `M21` green.
        """
        first = _append(
            two_reviewer_router, published_run, credential=credential_for(ANNA)
        )
        assert first.status == 201, first.body
        second = _append(
            two_reviewer_router,
            published_run,
            credential=credential_for(BORIS),
            event="reject",
        )
        assert second.status == 201, second.body

        assert first.json()["event"]["author_label"] == "anna.petrova"
        assert second.json()["event"]["author_label"] == "boris.smirnov"
        assert _stored_labels(session, published_run.finding_uid) == [
            "anna.petrova",
            "boris.smirnov",
        ]

    def test_the_history_carries_who_said_what(
        self, two_reviewer_router: Surface, published_run: PublishedRun
    ) -> None:
        """`P04` reads the ledger through the API, so the distinction has to survive it."""
        _append(two_reviewer_router, published_run, credential=credential_for(BORIS))
        _append(
            two_reviewer_router,
            published_run,
            credential=credential_for(ANNA),
            event="reject",
        )
        answer = two_reviewer_router.send(
            "GET",
            f"/findings/{published_run.finding_uid}/decisions",
            credential=credential_for(ANNA),
        )
        assert answer.status == 200, answer.body
        labels = [item["author_label"] for item in answer.json()["items"]]
        assert labels == ["boris.smirnov", "anna.petrova"]


class TestTheBodyCannotNameAnAuthor:
    """The rule that survives the repair, asserted rather than assumed.

    ``AppendDecisionRequest`` is closed (``extra="forbid"``), so a body naming an author is
    a ``422`` and never reaches the ledger. This was true before the repair and has to stay
    true after it: the whole point of deriving the label from the credential is that the
    client does not get to choose it.
    """

    def test_a_body_naming_an_author_is_refused(
        self, two_reviewer_router: Surface, published_run: PublishedRun, session: Session
    ) -> None:
        import json

        body = json.dumps(
            {
                "finding_observation_id": published_run.finding_observation_id,
                "event_type": "accept",
                "author_label": "somebody-else",
            }
        ).encode("utf-8")
        answer = two_reviewer_router.send(
            "POST",
            f"/findings/{published_run.finding_uid}/decisions",
            headers={
                "Content-Type": "application/json",
                "Idempotency-Key": f"w41-author-{uuid.uuid4()}",
            },
            body=body,
            credential=credential_for(ANNA),
        )
        assert answer.status == 422, (answer.status, answer.body)
        envelope = answer.json()
        assert envelope["error_code"] == "validation_failed"
        assert envelope["details"]["constraint"] == "additionalProperties"
        assert _stored_labels(session, published_run.finding_uid) == []

    def test_an_author_in_the_body_cannot_shadow_the_credential(
        self, two_reviewer_router: Surface, published_run: PublishedRun, session: Session
    ) -> None:
        """The second half: the handler reads no such field even if one arrived.

        Asserted at the handler's signature rather than over the wire, because the wire
        already refuses the body -- and a refusal upstream is exactly the thing that would
        hide a handler which *had* started trusting a body field.
        """
        import auditmanager.api.routers.decisions as module

        source = inspect.getsource(module)
        assert "body.author_label" not in source, (
            "the handler reads an author off the request body; the label is server-derived "
            "and a client-supplied one is a subject identity in all but name"
        )
        assert "author_label=subject.login" in source, (
            "the handler no longer derives the label from the verified subject"
        )


class TestFailClosed:
    def test_a_decision_with_no_authenticated_subject_is_refused(
        self, two_reviewer_router: Surface, published_run: PublishedRun, session: Session
    ) -> None:
        """Not an anonymous row. `D-66`'s shape is a default nothing holds; there is none."""
        answer = _append(two_reviewer_router, published_run, credential=None)
        assert answer.status == 401, (answer.status, answer.body)
        assert _stored_labels(session, published_run.finding_uid) == []

    def test_a_credential_this_deployment_never_minted_records_nothing(
        self, two_reviewer_router: Surface, published_run: PublishedRun, session: Session
    ) -> None:
        answer = _append(two_reviewer_router, published_run, credential="am1.not.a.credential")
        assert answer.status == 401, (answer.status, answer.body)
        assert _stored_labels(session, published_run.finding_uid) == []

    def test_a_credential_for_an_account_this_deployment_has_not_got_records_nothing(
        self, two_reviewer_router: Surface, published_run: PublishedRun, session: Session
    ) -> None:
        """Genuinely signed, and still refused: ``epoch_of`` answers ``None`` for it.

        The interesting half of fail-closed. The signature is this deployment's, so the
        credential is not forged; what it names is an account the deployment does not have,
        and a ledger row attributed to it would be attributed to nobody.
        """
        ghost = _SIGNER.issue(
            Subject(
                user_uid="usr_01M2545JSD15ETSNNV904X993S",
                login="ghost.reviewer",
                token_epoch=1,
            )
        ).token
        answer = _append(two_reviewer_router, published_run, credential=ghost)
        assert answer.status == 401, (answer.status, answer.body)
        assert _stored_labels(session, published_run.finding_uid) == []


class TestThereIsNoConfiguredDefaultToFallBackInto:
    """`D-66`'s shape, kept out by construction rather than by care.

    A default on ``author_label`` would mean a caller that forgot to attribute a decision
    still wrote a row, attributed to whatever the default said. These two guards are the
    reason the repair cannot quietly grow one back.
    """

    def test_the_ledger_declares_no_default_author(self) -> None:
        from auditmanager.decisions import append_decision_under_key, record_decision

        for function in (record_decision, append_decision_under_key):
            parameter = inspect.signature(function).parameters["author_label"]
            assert parameter.default is inspect.Parameter.empty, (
                f"{function.__name__} gives `author_label` the default "
                f"{parameter.default!r}. A decision with no named author must be a refusal, "
                "not a row attributed to a configuration constant."
            )

    def test_the_configured_label_constant_is_gone(self) -> None:
        import auditmanager.decisions as package
        import auditmanager.decisions.ledger as ledger

        assert not hasattr(ledger, "CONFIGURED_AUTHOR_LABEL"), (
            "the one-label constant is back. Every verdict by every reviewer would be "
            "attributed identically again, which is what `D-78` is."
        )
        assert "CONFIGURED_AUTHOR_LABEL" not in package.__all__
