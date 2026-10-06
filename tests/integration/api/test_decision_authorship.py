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

**What `W49-SEAL-01` changed.** Two things, both about the accounts and neither about the
rule. An event now names its author's **account** beside the label
(``expert_decision_event.author_user_uid``), so every account here is a real row this
module writes in the test's transaction -- the column is a foreign key. And an account
that has not completed its profile reaches only its own profile and password, so the
"no name" case is no longer a login written into the ledger: it is a refusal that writes
nothing (`W49-PLAN.md` section 3.1, "a decision event is written only by a complete
profile"). The two named reviewers are complete profiles, so their labels are the name form
"Фамилия И. О." -- at most 66 characters, inside ``author_label``'s 1..128 by construction.
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
from auditmanager.api.security import (
    API_TOKEN_VARIABLE,
    AccountStanding,
    Subject,
    build_signer,
)
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

    ``names`` are the person's (last, first, middle) once the profile is complete; ``None``
    means an incomplete profile -- a legacy login and no names -- the case
    :class:`TestTheAccountWithNoDisplayName` is about since `W49-SEAL-01`.
    """

    user_uid: str
    login: str
    epoch: int
    password: str
    names: tuple[str, str, str | None] | None

    @property
    def display_label(self) -> str:
        """The same resolution :attr:`UserRecord.display_label` performs, restated here.

        Restated and **not imported**, on purpose. ``OPERATING_CONSTRAINTS.md`` section 12:
        a test that built its expectation out of the thing under test could not see the
        thing under test being wrong. The assertions below go further and compare against
        the literals this module declares rather than against this property.
        """
        if self.names is None:
            return self.login
        last, first, middle = self.names
        label = f"{last} {first[0]}."
        return f"{label} {middle[0]}." if middle else label


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
    "anna.petrova@suite.invalid",
    7,
    "anna-password",
    ("Петрова", "Анна", None),
)
BORIS = _Account(
    "usr_01M2545JSD15ETSNNV904X992R",
    "boris.smirnov@suite.invalid",
    3,
    "boris-password",
    ("Смирнов", "Борис", "Игоревич"),
)
#: The empty case: a legacy login and no names -- an incomplete profile, which reaches no
#: product change since `W49-SEAL-01`.
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
        ),
        is_default_credential=False,
    ).token


class TwoAccountCredentialAdapter:
    """``CredentialPort`` over two accounts, in memory.

    Deliberately answers ``standing_of`` for both and for nothing else: an account this
    deployment does not have is ``None``, which the seam reads as a refusal. Both accounts
    answer ``is_default_credential=False``, because this module is about *whose* decision a
    row records and a default credential would refuse every operation it drives (`R-50`).
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
                    ),
                    is_default_credential=False,
                )
        return None

    def change_password(
        self, *, user_uid: str, current_password: str, new_password: str
    ) -> Any:  # pragma: no cover - this module drives no password change
        raise AssertionError("this module does not drive changePassword")

    def standing_of(self, user_uid: str) -> AccountStanding | None:
        for account in ACCOUNTS:
            if account.user_uid == user_uid:
                return AccountStanding(
                    token_epoch=account.epoch,
                    is_default_credential=False,
                    archived=False,
                    profile_complete=account.names is not None,
                    roles=frozenset({"expert"}),
                    login=account.login,
                    display_label=account.display_label,
                )
        return None


def _write_the_accounts(session: Session) -> None:
    """The three rows the credential port answers for, in this test's transaction.

    `W49-SEAL-01`: the ledger writes the author's ``user_uid`` into a ``RESTRICT`` foreign
    key, so an account this module only imagined would be a refused append. Rolled back
    with the test, like every row this suite writes.
    """
    from auditmanager.access.passwords import hash_password

    for account in ACCOUNTS:
        stored = hash_password(account.password)
        last, first, middle = account.names if account.names else (None, None, None)
        session.execute(
            text(
                "INSERT INTO app_user (user_uid, login, password_algorithm, "
                "password_iterations, password_salt, password_hash, is_default_credential, "
                "token_epoch, last_name, first_name, middle_name, profile_completed_at) "
                "VALUES (:uid, :login, :algorithm, :iterations, :salt, :digest, false, "
                ":epoch, :last, :first, :middle, "
                "CASE WHEN :complete THEN now() ELSE NULL END)"
            ),
            {
                "uid": account.user_uid,
                "login": account.login,
                "algorithm": stored.algorithm,
                "iterations": stored.iterations,
                "salt": stored.salt,
                "digest": stored.digest,
                "epoch": account.epoch,
                "last": last,
                "first": first,
                "middle": middle,
                "complete": account.names is not None,
            },
        )


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

    _write_the_accounts(session)
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


def _stored_accounts(session: Session, finding_uid: str) -> list[str | None]:
    """The author accounts the database really holds, in append order (`W49-SEAL-01`)."""
    rows = session.execute(
        text(
            "SELECT author_user_uid FROM expert_decision_event "
            "WHERE finding_uid = :f ORDER BY sequence_no"
        ),
        {"f": finding_uid},
    ).scalars()
    return list(rows)


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

        assert first.json()["event"]["author_label"] == "Петрова А."
        assert second.json()["event"]["author_label"] == "Смирнов Б. И."
        assert _stored_labels(session, published_run.finding_uid) == [
            "Петрова А.",
            "Смирнов Б. И.",
        ]
        # `R-37`: the *name* and not the login. Stated as its own assertion rather than
        # left implicit in the two above, because "two labels differ" was already true
        # under `D-78` and is not what this ruling changed.
        assert _stored_labels(session, published_run.finding_uid) != [
            "anna.petrova@suite.invalid",
            "boris.smirnov@suite.invalid",
        ]
        # `W49-SEAL-01`: and each event names its author's ACCOUNT, the identity a label
        # cannot be -- two reviewers may share a name form, never a `user_uid`.
        assert _stored_accounts(session, published_run.finding_uid) == [
            ANNA.user_uid,
            BORIS.user_uid,
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
        assert labels == ["Смирнов Б. И.", "Петрова А."]


class TestTheAccountWithNoDisplayName:
    """`R-37`'s empty case, as `W49-SEAL-01` decides it: **an account with no names writes
    no decision at all.**

    Until this wave the empty case recorded the login. An account without names is now an
    incomplete profile, and the seam refuses it every operation but its own profile and
    password (``permission_denied``, ``required_capability: profile_completed``), so the
    ledger only ever receives the name form a complete profile has -- which is what makes
    "``author_label`` is never empty and never longer than 128" true by construction even
    for an account whose login is a 254-character e-mail address.
    """

    def test_it_is_refused_and_writes_nothing(
        self, two_reviewer_router: Surface, published_run: PublishedRun, session: Session
    ) -> None:
        answer = _append(
            two_reviewer_router, published_run, credential=credential_for(CLARA)
        )
        assert answer.status == 403, (answer.status, answer.body)
        envelope = answer.json()
        assert envelope["error_code"] == "permission_denied"
        assert envelope["details"] == {"required_capability": "profile_completed"}
        assert _stored_labels(session, published_run.finding_uid) == []

    def test_a_complete_label_is_the_name_form_and_fits_the_ledger(self) -> None:
        """The bound, restated: 60 + 6 characters at most, inside 1..128."""
        for account in (ANNA, BORIS):
            assert 1 <= len(account.display_label) <= 66, account.display_label
            assert account.display_label != account.login

    def test_the_named_reviewer_still_writes_beside_the_refused_one(
        self, two_reviewer_router: Surface, published_run: PublishedRun, session: Session
    ) -> None:
        """The refusal of one account does not touch another's decision."""
        _append(two_reviewer_router, published_run, credential=credential_for(ANNA))
        refused = _append(
            two_reviewer_router,
            published_run,
            credential=credential_for(CLARA),
            event="reject",
        )
        assert refused.status == 403, refused.body
        assert _stored_labels(session, published_run.finding_uid) == ["Петрова А."]

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
        assert payload["name"] == "Петрова А.", payload
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
        """Genuinely signed, and still refused: ``standing_of`` answers ``None`` for it.

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
            ),
            is_default_credential=False,
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
        """Neither the label nor -- since `W49-SEAL-01` -- the account has a default.

        ``author_user_uid`` defaulted to ``None`` between `W49-DECISIONS-01` and the seal,
        while the router did not yet pass the subject; with the default gone a call that
        forgets the account is a ``TypeError`` and never a silently NULL author.
        """
        from auditmanager.decisions import append_decision_under_key, record_decision

        for function in (record_decision, append_decision_under_key):
            for name in ("author_label", "author_user_uid"):
                parameter = inspect.signature(function).parameters[name]
                assert parameter.default is inspect.Parameter.empty, (
                    f"{function.__name__} gives `{name}` the default "
                    f"{parameter.default!r}. A decision with no named author must be a "
                    "refusal, not a row attributed to a configuration constant."
                )
                assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, (function, name)

    def test_the_router_passes_the_subjects_account(self) -> None:
        """The other half: the one caller names the account from the verified subject."""
        import auditmanager.api.routers.decisions as module

        source = inspect.getsource(module)
        assert "author_user_uid=subject.user_uid" in source, (
            "the decisions router no longer passes the verified subject's account; every "
            "event appended through the API would name no author account"
        )

    def test_the_configured_label_constant_is_gone(self) -> None:
        import auditmanager.decisions as package
        import auditmanager.decisions.ledger as ledger

        assert not hasattr(ledger, "CONFIGURED_AUTHOR_LABEL"), (
            "the one-label constant is back. Every verdict by every reviewer would be "
            "attributed identically again, which is what `D-78` is."
        )
        assert "CONFIGURED_AUTHOR_LABEL" not in package.__all__
