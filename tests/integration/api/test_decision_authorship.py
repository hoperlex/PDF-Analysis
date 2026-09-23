"""`D-78`, and `R-37`: a decision is attributed to the reviewer who made it, **by name**.

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

**What `R-37` changed, and why `D-78` was not enough.** Wave 41 wrote the reviewer's
**login**. A login is an address: folded, ASCII, unique, chosen to be typed at a keyboard
and said down a telephone. ``author_label`` is read by *people* -- it is what another
reviewer sees on a decision somebody else took -- so the owner ruled for a display name.
The rule that did not change is the one that matters most and is asserted again below: the
label is **never taken from a request body**. It is server-derived or nothing.

**Three credentials, three labels, and one of them has no name at all.** The suite in
``conftest.py`` has exactly one account, which cannot distinguish "the label follows the
caller" from "the label is a constant that happens to equal this caller's login". So this
module wires its own credential port over three accounts -- two named, one not -- and
drives the **shipped** ``DecisionAdapter``: a fixture adapter that wrote the label would
prove that the fixture writes it. The third account is `R-37`'s empty case, which the
ruling left to be decided and which :class:`TestTheAccountWithNoDisplayName` states.
"""

from __future__ import annotations

import base64
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
    """One reviewer this module's credential port knows about.

    ``display_name`` is what the reviewer chose; ``None`` means they chose nothing, and the
    label then falls back to the login -- the case `R-37` made this module decide, and the
    one :class:`TestTheAccountWithNoDisplayName` is about.
    """

    user_uid: str
    login: str
    epoch: int
    password: str
    display_name: str | None

    @property
    def display_label(self) -> str:
        """The same resolution :attr:`UserRecord.display_label` performs, restated here.

        Restated and **not imported**, on purpose. ``OPERATING_CONSTRAINTS.md`` section 12:
        a test that built its expectation out of the thing under test could not see the
        thing under test being wrong. The assertions below go further and compare against
        the literals this module declares rather than against this property.
        """
        return self.display_name or self.login


#: Two accounts with **different logins and different epochs**. Different epochs so that a
#: seam which ignored the credential's epoch could not pass by defaulting to a shared one,
#: which is the reason ``driver.py`` pins its own epoch away from 1.
#:
#: **Since `R-37` they also have different display names, and `CLARA` has none** -- so this
#: module can state all three of the things that ruling decided: two named reviewers are
#: two distinguishable authors, the label is the *name* and not the login, and an account
#: that chose no name writes its login rather than a blank or something invented.
ANNA = _Account(
    "usr_01M2545JSD15ETSNNV904X991Q",
    "anna.petrova",
    7,
    "anna-password",
    "Анна Петрова",
)
BORIS = _Account(
    "usr_01M2545JSD15ETSNNV904X992R",
    "boris.smirnov",
    3,
    "boris-password",
    "Борис Смирнов",
)
#: The empty case. No display name, so the ledger must record ``clara.jones`` -- which is a
#: real string this reviewer typed, is unique, and is 1..100 characters by
#: ``ck_app_user_login_format``, i.e. inside ``author_label``'s 1..128 by construction.
CLARA = _Account(
    "usr_01M2545JSD15ETSNNV904X993T",
    "clara.jones",
    5,
    "clara-password",
    None,
)
ACCOUNTS = (ANNA, BORIS, CLARA)


def credential_for(account: _Account) -> str:
    """A credential this deployment really minted for ``account``.

    Minted rather than written down, for ``driver.py``'s reason: a literal could not carry
    an expiry and would have to be re-minted by hand at every change to the format.
    """
    return _SIGNER.issue(
        Subject(
            user_uid=account.user_uid,
            login=account.login,
            token_epoch=account.epoch,
            display_label=account.display_label,
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
                        display_label=account.display_label,
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

        assert first.json()["event"]["author_label"] == "Анна Петрова"
        assert second.json()["event"]["author_label"] == "Борис Смирнов"
        assert _stored_labels(session, published_run.finding_uid) == [
            "Анна Петрова",
            "Борис Смирнов",
        ]
        # `R-37`: the *name* and not the login. Stated as its own assertion rather than
        # left implicit in the two above, because "two labels differ" was already true
        # under `D-78` and is not what this ruling changed.
        assert _stored_labels(session, published_run.finding_uid) != [
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
        assert labels == ["Борис Смирнов", "Анна Петрова"]


class TestTheAccountWithNoDisplayName:
    """`R-37`'s empty case, decided and then asserted.

    An account that has chosen no display name records **its login**. The two alternatives
    were refused and the refusals are what this class holds in place:

    * **a blank** -- ``author_label`` is ``minLength: 1`` in the frozen contract and the
      ledger refuses an empty label outright, so a blank stored upstream is a refused write
      at the exact moment an expert records a verdict;
    * **an invented name** -- "Reviewer 3", a prefix of the opaque identity, a mail-address
      local part. In an append-only ledger a fabricated name is, a year later,
      indistinguishable from one a person chose, and `P04` exists to learn whose judgement
      was whose.

    The login is not a compromise between those two. It is a real string the reviewer
    typed, it is unique, and ``ck_app_user_login_format`` bounds it at 1..100 characters --
    inside ``author_label``'s 1..128 **by construction**, which is what makes "this label
    can never be empty and can never be too long" a proof rather than a hope.
    """

    def test_it_records_the_login_and_not_a_blank(
        self, two_reviewer_router: Surface, published_run: PublishedRun, session: Session
    ) -> None:
        answer = _append(
            two_reviewer_router, published_run, credential=credential_for(CLARA)
        )
        assert answer.status == 201, answer.body
        assert answer.json()["event"]["author_label"] == "clara.jones"
        assert _stored_labels(session, published_run.finding_uid) == ["clara.jones"]

    def test_it_records_nothing_that_looks_invented(
        self, two_reviewer_router: Surface, published_run: PublishedRun, session: Session
    ) -> None:
        """The label is one of the account's own two strings and nothing else.

        Stated as an exclusion because the defect this guards against is not "the wrong
        name" but "a name from nowhere", and a positive assertion against one literal would
        not notice a second fallback being introduced beside the first.
        """
        _append(two_reviewer_router, published_run, credential=credential_for(CLARA))
        (label,) = _stored_labels(session, published_run.finding_uid)
        assert label == CLARA.login
        assert label not in {"", " ", "local-reviewer", CLARA.user_uid}
        assert CLARA.user_uid not in label, (
            "the opaque identity has leaked into a field every reviewer reads"
        )

    def test_the_named_and_the_unnamed_are_still_two_authors(
        self, two_reviewer_router: Surface, published_run: PublishedRun, session: Session
    ) -> None:
        """The fallback does not collapse anybody together, which is `D-78`'s whole point."""
        _append(two_reviewer_router, published_run, credential=credential_for(ANNA))
        _append(
            two_reviewer_router,
            published_run,
            credential=credential_for(CLARA),
            event="reject",
        )
        assert _stored_labels(session, published_run.finding_uid) == [
            "Анна Петрова",
            "clara.jones",
        ]

    def test_a_credential_carrying_an_empty_label_is_refused_and_writes_nothing(
        self, two_reviewer_router: Surface, published_run: PublishedRun, session: Session
    ) -> None:
        """The seam refuses rather than falling back, which is where a second fallback would go.

        A credential minted with an empty ``name`` is the shape a caller would produce if
        the resolution above were ever skipped. The seam answers ``401`` -- the same refusal
        a forged credential gets -- rather than quietly substituting the login, because a
        fallback inside the seam is a fallback nobody can see. The *account's* fallback is
        visible: it is a NULL column and a line in ``access-check``.
        """
        import json as _json

        genuine = credential_for(ANNA)
        version, body, _tag = genuine.split(".")
        payload = _json.loads(
            base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)).decode("utf-8")
        )
        assert payload["name"] == "Анна Петрова", payload
        payload["name"] = ""
        forged = _resign(version, payload)
        assert forged != genuine
        assert _SIGNER.verify(forged) is None, (
            "this case is only a case if the seam really refuses the credential -- a "
            "credential it accepted would be testing the router instead"
        )

        answer = _append(two_reviewer_router, published_run, credential=forged)
        assert answer.status == 401, (answer.status, answer.body)
        assert _stored_labels(session, published_run.finding_uid) == []


def _resign(version: str, payload: dict[str, Any]) -> str:
    """Re-sign ``payload`` with this suite's own key, so only the payload is under test.

    ``version`` is taken from a credential the signer just minted rather than written down,
    so this helper does not pin the format tag and does not have to be edited when it moves.

    The tag is recomputed with the deployment's key on purpose: the case above is about a
    credential this deployment **really signed** whose payload the seam must still refuse.
    A credential with a broken tag would be refused one check earlier and would prove
    nothing about the payload rule.
    """
    import hashlib
    import hmac
    import json as _json

    from auditmanager.api.security import derive_signing_key

    body = (
        base64.urlsafe_b64encode(
            _json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        .decode("ascii")
        .rstrip("=")
    )
    signed = f"{version}.{body}"
    tag = hmac.new(
        derive_signing_key(DEPLOYMENT_SECRET), signed.encode("utf-8"), hashlib.sha256
    ).digest()
    return f"{signed}.{base64.urlsafe_b64encode(tag).decode('ascii').rstrip('=')}"


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
        assert "author_label=subject.display_label" in source, (
            "the handler no longer derives the label from the verified subject. `R-37`: it "
            "is `subject.display_label` -- the reviewer's chosen name, or their login when "
            "they have chosen none, resolved once on the account's own record."
        )
        assert "author_label=subject.login" not in source, (
            "the handler is back on `D-78`'s login. `R-37` ruled for the display name, "
            "which is what another reviewer reads on a decision somebody else took."
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
                display_label="Ghost Reviewer",
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
