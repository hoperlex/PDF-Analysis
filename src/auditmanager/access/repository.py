"""The only reader and writer of ``app_user``.

Shaped like the rest of the tree: explicit statements, no base repository, no generic
CRUD, and the :class:`~sqlalchemy.orm.Session` passed in by the caller rather than owned
here (``docs/program/P02_SEAMS.md`` section 3.5, and
:mod:`auditmanager.documents.repository` for the same decision written out).

Three properties are specific to this table.

**The credential columns are read in exactly two places, and both are named.**
``_SELECT_CREDENTIAL`` and ``_SELECT_CREDENTIAL_BY_UID`` are the only statements that
project ``password_algorithm``, ``password_iterations``, ``password_salt`` and
``password_hash``. The first serves :meth:`UserRepository.authenticate`, which is addressed
by login because that is what a sign-in form types; the second serves
:meth:`UserRepository.change_password`, which is addressed by ``user_uid`` because the
caller there has already been authenticated and holds an identity rather than a name. In
both, the value built (:class:`~auditmanager.access.passwords.StoredPassword`) is consumed
inside this module and never returned. Everything else projects ``_PUBLIC_COLUMNS``, which
does not contain them.

*This paragraph said "exactly one place" until wave 39, and the sentence was load-bearing:
it is the whole of the argument that a digest never leaves here.* Adding the second reader
without moving it would have left a true-sounding claim that no longer covered the code --
``OPERATING_CONSTRAINTS.md`` §4.7 inside the module that holds the credential, which is
exactly where the last one was found.

**Revocation is a column, and a password change is one statement.** ``token_epoch`` is the
generation of credentials the account accepts; the seam stamps it into every credential it
mints and refuses one that disagrees. :meth:`UserRepository.change_password` writes the new
digest, clears ``is_default_credential`` and raises ``token_epoch`` **in a single UPDATE**,
so there is no interleaving in which the password changed and the old credentials survived.
That is not an optimisation: a password change that leaves credentials minted under the old
password working is a password change in name only, and two statements are two chances for
only the first to land.

**Failing to find a user still costs a hash, and so does being locked out.** See
:func:`~auditmanager.access.passwords.spend_a_verification`. Without it the response
time answers "does this account exist?" for anybody with a stopwatch -- and `W40-LIMIT`
had to pay it a third time, on the path that refuses a blocked account. A cheap refusal
there would answer a *better* question than the original oracle: not merely "does this
account exist" but "is this account under attack right now", which is the same enumeration
with a progress bar. :class:`~auditmanager.access.ports.UserRepository` states the
obligation as *"comparable work on both paths"*; there are three paths now and the
sentence is unchanged.

**A rate limit and a lockout are two different things and this module keeps them apart.**
``failed_sign_ins`` with ``last_failed_sign_in_at`` is the rate limit: consecutive recent
refusals, which restart by themselves once the refusals stop being recent, and which on
their own refuse nothing. ``sign_in_blocked_until`` is the lockout: an instant before which
the password is not consulted at all, so that even the right one mints nothing.

**A lockout needs a way back**, because a lockout with no way back is a denial of service
anybody can aim at a named account -- and this installation has one account by default, so
that named account is the owner's. There are three, and all three are code:

1. **time.** The instant passes, and the first attempt afterwards starts a fresh allowance
   rather than re-tripping on the count that earned the last one. Without that clause one
   attempt per cooling-off period would hold an account shut for ever, which is a permanent
   lockout wearing a temporary one's clothes;
2. **a password change.** :meth:`UserRepository.change_password` clears all three columns in
   the UPDATE it already performs. An account that has just proved its current password is
   not the thing this brake exists to slow;
3. **the operator.** :mod:`auditmanager.access.unlock`, immediately, with no redeploy and no
   restart.

**Attempts made while an account is blocked are refused and not counted.** Counting them
would let an attacker who keeps knocking extend the block indefinitely, which converts a
bounded cooling-off into the permanent lockout the paragraph above refuses.

**A lockout does not touch a credential anybody already holds.** It refuses *minting*;
``token_epoch`` refuses *presenting*. Wiring the one to the other would let an
unauthenticated caller sign out a reviewer who is working, by typing a wrong password at
them -- and that is a caller who never had access taking it away from one who did.

**A default credential is loud.** Every successful authentication of a user whose
``is_default_credential`` is still true logs a warning naming the login. That is the
runtime half of the visibility the seeded ``admin`` account needs; the database half is
the column itself, and ``python -m auditmanager.access.check`` reports it without
anybody having to log in. The warning is not rate-limited and not suppressible: an
operator who is tired of reading it changes the password, which is the point.
"""

from __future__ import annotations

import logging
from typing import Final

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auditmanager.access.models import UserRecord, UserUid, normalize_login
from auditmanager.access.passwords import (
    StoredPassword,
    hash_password,
    is_the_same_password,
    spend_a_verification,
    verify_password,
)
from auditmanager.shared.errors import DomainError, ErrorCode

__all__ = [
    "ATTEMPT_WINDOW_SECONDS",
    "COOLING_OFF_SECONDS",
    "CREDENTIALS_REVOKED",
    "DEFAULT_CREDENTIAL_WARNING",
    "FAILED_SIGN_IN_ALLOWANCE",
    "SIGN_IN_BLOCKED",
    "UserRepository",
]

_log = logging.getLogger(__name__)

#: PostgreSQL's unique-violation SQLSTATE. Matched on the code, never on the message
#: text: a message is a diagnostic string a server upgrade or a locale may reword.
_UNIQUE_VIOLATION: Final[str] = "23505"

#: The prefix of the warning emitted when a default credential is used. Named here so a
#: test and a log-scraping operator can both match on something stable.
DEFAULT_CREDENTIAL_WARNING: Final[str] = "default credential in use"

#: The prefix of the warning emitted whenever an account's credentials are revoked, by a
#: password change or by an operator. Stable text, for the same two readers.
#:
#: It is a warning and not an info line on purpose. Revocation is rare, it is irreversible
#: for everyone holding a credential at that moment, and the one question an operator asks
#: afterwards -- "when did this happen, and to whom?" -- must be answerable from the
#: deployment log as well as from ``token_epoch_updated_at``.
CREDENTIALS_REVOKED: Final[str] = "credentials revoked"

#: The prefix of the warning emitted at the moment an account is shut out of signing in.
#: Stable text, for the same two readers -- and it is the operator's only live view of a
#: state that nothing else announces.
#:
#: It is emitted when the block is **set** and not on every attempt refused while it
#: stands. Not out of tidiness: an attempt made during a block does not move any column
#: (see the module docstring), so there is exactly one of these per cooling-off period, and
#: a line per refused attempt would hand the same attacker a way to fill a disk.
SIGN_IN_BLOCKED: Final[str] = "sign-in blocked"

#: How many consecutive recent failures an account may collect before it is shut.
#:
#: Five, and the reasoning is arithmetic rather than convention. A derivation costs about
#: 0.113 s on this lane's interpreter (see :data:`~auditmanager.access.passwords.ITERATIONS`),
#: so an unbraked attacker gets roughly nine guesses a second -- about 780 000 a day. Five
#: per cooling-off period is about 1 440 a day: five hundred times slower, against a cost to
#: a reviewer who mistypes of one wait.
#:
#: Raising it buys an attacker guesses linearly and buys a mistyping reviewer nothing they
#: will notice; lowering it walks a two-finger typist into a wait they did not earn.
FAILED_SIGN_IN_ALLOWANCE: Final[int] = 5

#: How long two failures may be apart and still count as consecutive, in seconds.
#:
#: Fifteen minutes. Without a window the count would mean "ever", and a reviewer who
#: mistypes twice in March and three times in June would be locked out in June for nothing
#: -- a brake that fires on a pattern no attacker produces and every human does.
ATTEMPT_WINDOW_SECONDS: Final[int] = 900

#: How long the door stays shut once the allowance is spent, in seconds.
#:
#: Five minutes, and it is deliberately the smallest of the three numbers. Under a
#: *sustained* attack the duration barely matters -- an attacker willing to spend five
#: requests every cooling-off period holds the account shut whatever it is set to -- while
#: for the reviewer who simply mistyped, the duration is the entire cost. A number that
#: changes one side and not the other should be set for the side it changes.
COOLING_OFF_SECONDS: Final[int] = 300

#: Everything a caller may see. The four credential columns are absent by construction.
#:
#: ``token_epoch`` is here and not beside the digest: it is not credential material. It is
#: a counter the seam stamps into every credential it mints, so it travels on purpose, and
#: putting it behind the credential statement would mean the one value every request must
#: check could only be read by the one query that also reads the hash.
#: The three ``W40-LIMIT`` columns are here for the same reason and are not credential
#: material either: they say how often somebody has been wrong, never what the password is.
#: They are projected because the operator's two views of a lockout read them, and a
#: refusal state nobody can see is one nobody can answer for.
_PUBLIC_COLUMNS: Final[str] = (
    "user_uid, login, is_default_credential, created_at, password_updated_at, "
    "token_epoch, token_epoch_updated_at, "
    "failed_sign_ins, last_failed_sign_in_at, sign_in_blocked_until"
)

_INSERT_USER = text(
    f"""
    INSERT INTO app_user (
        user_uid, login, password_algorithm, password_iterations,
        password_salt, password_hash, is_default_credential
    ) VALUES (
        :user_uid, :login, :algorithm, :iterations,
        :salt, :digest, :is_default_credential
    )
    RETURNING {_PUBLIC_COLUMNS}
    """
)

_SELECT_BY_LOGIN = text(f"SELECT {_PUBLIC_COLUMNS} FROM app_user WHERE login = :login")

#: One of the two statements in this package that read credential material. Addressed by
#: login, because a sign-in form types a name and not an identity.
#:
#: It projects one more thing since `W40-LIMIT`, and the extra column is not credential
#: material: **whether this account is blocked from signing in at this instant**. It is
#: read here rather than by a statement of its own for two reasons. A second statement
#: addressed by the same login would be a second read of one row inside one decision, and
#: two reads of one row can disagree. And the answer is computed as a boolean **by the
#: database**, against the database's own ``now()``, so that the instant the lockout is
#: compared against and the instant it was written with come from one clock -- two clocks
#: that must agree are two ways to be wrong, and here one of the two would be on the
#: attacker's side of the comparison.
#:
#: ``COALESCE`` because ``NULL > now()`` is ``NULL``, and a NULL here means "nothing has
#: shut this account", which must read as ``false`` and never as a refusal.
_SELECT_CREDENTIAL = text(
    "SELECT password_algorithm, password_iterations, password_salt, password_hash, "
    "COALESCE(sign_in_blocked_until > now(), false) "
    "FROM app_user WHERE login = :login"
)

#: The other. Addressed by ``user_uid``, because its caller has already been authenticated
#: and holds the identity the seam published -- and because a login can be renamed while an
#: identity cannot, so a password change addressed by name could in principle be applied to
#: a different account than the one that proved itself.
_SELECT_CREDENTIAL_BY_UID = text(
    "SELECT password_algorithm, password_iterations, password_salt, password_hash "
    "FROM app_user WHERE user_uid = :user_uid"
)

#: The new digest, the cleared default flag, the raised epoch and the cleared sign-in
#: brake, in one statement. See the module docstring for why it is one and not four.
#:
#: The last three assignments are `W40-LIMIT`'s **second way back from a lockout**. An
#: account that has just proved its current password is not the thing the brake exists to
#: slow, and a reviewer who is shut out of the exchange but still holding a live credential
#: can open their own door with the operation they already have. It is in this statement
#: rather than in one of its own for the reason the rest of the statement is one statement:
#: an interleaving in which the password changed and the account stayed shut is a password
#: change that appears not to have worked.
_CHANGE_PASSWORD = text(
    f"""
    UPDATE app_user SET
        password_algorithm = :algorithm,
        password_iterations = :iterations,
        password_salt = :salt,
        password_hash = :digest,
        password_updated_at = now(),
        is_default_credential = false,
        token_epoch = token_epoch + 1,
        token_epoch_updated_at = now(),
        failed_sign_ins = 0,
        last_failed_sign_in_at = NULL,
        sign_in_blocked_until = NULL
    WHERE user_uid = :user_uid
    RETURNING {_PUBLIC_COLUMNS}
    """
)

#: Revocation, for one account. ``token_epoch + 1`` is computed by the database rather than
#: read and written back: two operators revoking at once must produce two increments, and a
#: read-modify-write in this process would let one overwrite the other with the same value
#: -- which reads as a successful revocation and is not one.
_REVOKE_ONE = text(
    f"""
    UPDATE app_user SET
        token_epoch = token_epoch + 1,
        token_epoch_updated_at = now()
    WHERE login = :login
    RETURNING {_PUBLIC_COLUMNS}
    """
)

#: Revocation, for every account. "The pilot has ended" is one statement.
_REVOKE_EVERY = text(
    f"""
    UPDATE app_user SET
        token_epoch = token_epoch + 1,
        token_epoch_updated_at = now()
    RETURNING {_PUBLIC_COLUMNS}
    """
)

#: The epoch check the seam runs on every authorized request. A primary-key lookup
#: projecting one integer, and deliberately nothing else: this runs on every request on the
#: surface, and a statement that also returned a login would invite a caller to read
#: identity out of the credential check.
_SELECT_TOKEN_EPOCH = text("SELECT token_epoch FROM app_user WHERE user_uid = :user_uid")

#: What this failure makes the count, computed by the **database** from the row as it
#: stands at the moment of the write -- never from a number this process read a moment ago.
#: Two simultaneous failures must produce two increments, exactly as two simultaneous
#: revocations must produce two epochs; a read-modify-write here would let one attempt
#: overwrite the other with the same value, and an attacker who can issue requests in
#: parallel would collect the difference for free.
#:
#: Three of the four branches restart the count at one, and the first of them is the one
#: worth reading twice. **A block that has been served is spent**: the first failure after
#: ``sign_in_blocked_until`` has passed starts a fresh allowance rather than adding to the
#: count that earned the last one. Without that clause a single attempt per cooling-off
#: period would re-trip the block for ever, which is a permanent lockout wearing a
#: temporary one's clothes -- and a permanent lockout an unauthenticated caller can aim at
#: a named account is a denial of service, not a guard.
_NEXT_FAILED_SIGN_INS: Final[str] = (
    "CASE "
    "WHEN sign_in_blocked_until IS NOT NULL AND sign_in_blocked_until <= now() THEN 1 "
    "WHEN last_failed_sign_in_at IS NULL THEN 1 "
    "WHEN last_failed_sign_in_at <= now() - (:window * interval '1 second') THEN 1 "
    "ELSE failed_sign_ins + 1 "
    "END"
)

#: One refused attempt, recorded. The expression above appears twice because both columns
#: are decided by it and SQL has nowhere to name it; it is written once, in Python, so
#: there is one source for the rule even though there are two occurrences of the text.
#: Every assignment in a ``SET`` sees the row's values *before* the statement, so the two
#: occurrences cannot disagree.
#:
#: This statement is never reached for an account that is blocked right now --
#: :meth:`UserRepository.authenticate` refuses before it gets here -- which is what makes
#: knocking on a shut door free of charge to the account behind it and is why
#: ``sign_in_blocked_until`` being non-NULL in the returned row means *this attempt shut
#: it*, rather than *it was already shut*.
_NOTE_A_FAILED_SIGN_IN = text(
    f"""
    UPDATE app_user SET
        failed_sign_ins = {_NEXT_FAILED_SIGN_INS},
        last_failed_sign_in_at = now(),
        sign_in_blocked_until = CASE
            WHEN ({_NEXT_FAILED_SIGN_INS}) >= :allowance
                THEN now() + (:cooling * interval '1 second')
            WHEN sign_in_blocked_until IS NOT NULL AND sign_in_blocked_until <= now()
                THEN NULL
            ELSE sign_in_blocked_until
        END
    WHERE login = :login
    RETURNING {_PUBLIC_COLUMNS}
    """
)

#: The brake released, for one account. The predicate is what keeps a clean sign-in from
#: writing a row: the overwhelmingly common case is an account with nothing to clear, and
#: an UPDATE that matched it would put a new row version on the hot path of every sign-in
#: for no change in value.
#:
#: It is also what lets the operator command tell *"there was nothing to release"* from
#: *"that released something"* without a second question.
_CLEAR_ONE = text(
    f"""
    UPDATE app_user SET
        failed_sign_ins = 0,
        last_failed_sign_in_at = NULL,
        sign_in_blocked_until = NULL
    WHERE login = :login
      AND (failed_sign_ins <> 0
           OR last_failed_sign_in_at IS NOT NULL
           OR sign_in_blocked_until IS NOT NULL)
    RETURNING {_PUBLIC_COLUMNS}
    """
)

#: The brake released, for every account. "Whatever is going on, let everybody in" is one
#: statement, exactly as "the pilot has ended" is.
_CLEAR_EVERY = text(
    f"""
    UPDATE app_user SET
        failed_sign_ins = 0,
        last_failed_sign_in_at = NULL,
        sign_in_blocked_until = NULL
    WHERE failed_sign_ins <> 0
       OR last_failed_sign_in_at IS NOT NULL
       OR sign_in_blocked_until IS NOT NULL
    RETURNING {_PUBLIC_COLUMNS}
    """
)

#: Who is shut out **at this instant**, for the operator's view. The comparison is the
#: database's ``now()`` and not this process's clock, for the reason
#: :data:`_SELECT_CREDENTIAL` gives.
_SELECT_BLOCKED = text(
    f"SELECT {_PUBLIC_COLUMNS} FROM app_user "
    "WHERE sign_in_blocked_until IS NOT NULL AND sign_in_blocked_until > now() "
    "ORDER BY login"
)

_SELECT_DEFAULT_CREDENTIALS = text(
    f"SELECT {_PUBLIC_COLUMNS} FROM app_user "
    "WHERE is_default_credential IS TRUE ORDER BY login"
)


def _record(row: object) -> UserRecord:
    (
        user_uid,
        login,
        is_default_credential,
        created_at,
        password_updated_at,
        token_epoch,
        token_epoch_updated_at,
        failed_sign_ins,
        last_failed_sign_in_at,
        sign_in_blocked_until,
    ) = row  # type: ignore[misc]
    return UserRecord(
        user_uid=UserUid.parse(user_uid),
        login=login,
        is_default_credential=bool(is_default_credential),
        created_at=created_at,
        password_updated_at=password_updated_at,
        token_epoch=int(token_epoch),
        token_epoch_updated_at=token_epoch_updated_at,
        failed_sign_ins=int(failed_sign_ins),
        last_failed_sign_in_at=last_failed_sign_in_at,
        sign_in_blocked_until=sign_in_blocked_until,
    )


class UserRepository:
    """Find a user, prove a password, create a user, change a password, revoke credentials,
    and slow down whoever is guessing.

    Conforms to :class:`auditmanager.access.ports.UserRepository`. Three methods here are
    **not** on that port and each is deliberate: ``users_on_default_credentials``,
    ``clear_failed_sign_ins`` and ``accounts_blocked_from_signing_in``. They are the
    operator's views and the operator's lever, and the only caller outside this boundary is
    the API's credential adapter, which must not be able to reach any of the three.
    """

    __slots__ = ()

    def find_by_login(self, session: Session, login: str) -> UserRecord | None:
        """The user with this login, or ``None``.

        A malformed login raises rather than returning ``None``: "this is not a login"
        and "no such user" are different facts, and collapsing them would make a typo in
        a caller look like a missing account.
        """
        row = session.execute(_SELECT_BY_LOGIN, {"login": normalize_login(login)}).first()
        return None if row is None else _record(row)

    def authenticate(self, session: Session, login: str, password: str) -> UserRecord | None:
        """The user when the password is theirs, ``None`` in every other case.

        ``None`` covers an unknown login, a wrong password, a login this boundary would
        never have stored, and -- since `W40-LIMIT` -- **an account that is shut right
        now, whatever password was offered**. The four are deliberately indistinguishable
        to the caller and cost comparable time.

        **The fourth is the one that is a design decision rather than a mechanism.** A
        caller who could tell "that is not the password" from "this account is shut" would
        be told that the account exists *and* that somebody is currently attacking it,
        which is the enumeration oracle the first three exist to close, with a progress bar
        attached. So it is the same answer, spending the same work.

        **This method now writes**, which it did not before. A refused attempt records
        itself and a successful one clears what earlier refusals recorded; the caller owns
        the transaction, so the caller must commit for either to survive -- see
        :class:`auditmanager.bootstrap.adapters.CredentialAdapter`, which was a read and is
        a write for exactly this reason.
        """
        try:
            normalized = normalize_login(login)
        except DomainError:
            # A login that could not have been stored still costs a derivation: a cheap
            # refusal here would tell a prober which shapes exist in the table.
            spend_a_verification(password)
            return None

        credential = session.execute(_SELECT_CREDENTIAL, {"login": normalized}).first()
        if credential is None:
            spend_a_verification(password)
            return None

        algorithm, iterations, salt, digest, blocked_now = credential
        if blocked_now:
            # The password is NOT consulted. That is the whole of what a lockout is: a
            # lockout a correct password defeats does not stop guessing, because a guess
            # that succeeds is exactly a correct password. The availability that costs is
            # the price of the confidentiality it buys, and it is bounded by
            # `COOLING_OFF_SECONDS` and by the three ways back in the module docstring.
            #
            # Nothing is written. An attempt made against a shut door does not extend the
            # block -- see `_NOTE_A_FAILED_SIGN_IN` -- so an attacker who keeps knocking
            # cannot hold an account shut beyond the cooling-off period they earned.
            spend_a_verification(password)
            _log.info(
                "%s: an attempt on %r was refused without consulting the password, "
                "because this account is inside its cooling-off period.",
                SIGN_IN_BLOCKED,
                normalized,
            )
            return None

        stored = StoredPassword(
            algorithm=algorithm,
            iterations=int(iterations),
            salt=salt,
            digest=digest,
        )
        try:
            matched = verify_password(stored, password)
        except DomainError as exc:
            if exc.code is ErrorCode.VALIDATION_FAILED:
                # An empty or over-long candidate is a failed attempt, not a server
                # fault. An unsupported algorithm or a corrupt column is neither, and
                # propagates: reporting it as a wrong password would hide a real defect
                # behind a plausible one.
                #
                # It is a failed attempt, so it is counted like one. A candidate the
                # mechanical bounds refuse could not have matched any stored digest, which
                # is exactly what every other refused attempt has in common with it -- and
                # an uncounted refusal is an attempt shape a guesser would find and use.
                self._note_a_failed_sign_in(session, normalized)
                return None
            raise
        if not matched:
            self._note_a_failed_sign_in(session, normalized)
            return None

        # The password was this account's, so whatever earlier attempts recorded is spent.
        # This runs before the row is read back, so the record handed out carries the
        # cleared values rather than the ones a successful sign-in has just made false.
        session.execute(_CLEAR_ONE, {"login": normalized})

        row = session.execute(_SELECT_BY_LOGIN, {"login": normalized}).first()
        if row is None:  # pragma: no cover - the row was read microseconds ago
            return None
        record = _record(row)
        if record.is_default_credential:
            _log.warning(
                "%s: user %r signed in with the password this system was seeded with. "
                "Change it; until then anyone who has read the deployment notes can "
                "sign in as this user.",
                DEFAULT_CREDENTIAL_WARNING,
                record.login,
            )
        return record

    def _note_a_failed_sign_in(self, session: Session, login: str) -> None:
        """Record one refused attempt, and shut the account when that spends the allowance.

        Private, and it stays private. It is not on
        :class:`auditmanager.access.ports.UserRepository` because nobody outside this
        module may decide that an attempt failed: the only thing that knows is the
        comparison two lines above, and a port method called "note a failure" is a port
        method somebody eventually calls for a reason of their own.

        The row is never read first. Everything the decision needs is computed inside the
        statement, from the row as the write finds it -- see
        :data:`_NEXT_FAILED_SIGN_INS`.
        """
        row = session.execute(
            _NOTE_A_FAILED_SIGN_IN,
            {
                "login": login,
                "window": ATTEMPT_WINDOW_SECONDS,
                "allowance": FAILED_SIGN_IN_ALLOWANCE,
                "cooling": COOLING_OFF_SECONDS,
            },
        ).first()
        if row is None:  # pragma: no cover - the row was read microseconds ago
            return
        record = _record(row)
        if record.sign_in_blocked_until is None:
            return
        # Non-NULL here means *this attempt shut it*: a live block is refused before this
        # statement runs, and a spent one is set to NULL by it. So there is exactly one of
        # these per cooling-off period, however hard anybody knocks.
        _log.warning(
            "%s: %r has been refused %d times in a row and is now shut until %s. No "
            "password is consulted until then, including the right one. Credentials "
            "already minted for this account are NOT affected. To open it now: "
            "python -m auditmanager.access.unlock --login %s",
            SIGN_IN_BLOCKED,
            record.login,
            record.failed_sign_ins,
            record.sign_in_blocked_until.isoformat(),
            record.login,
        )

    def create_user(
        self,
        session: Session,
        login: str,
        password: str,
        *,
        is_default_credential: bool = False,
    ) -> UserRecord:
        """Create a user and return them. The digest is written and forgotten.

        ``is_default_credential`` exists so the one account that *is* seeded with a
        known password can say so in its own row. It defaults to false, so an ordinary
        creation cannot set the flag by omission.
        """
        normalized = normalize_login(login)
        stored = hash_password(password)
        try:
            row = session.execute(
                _INSERT_USER,
                {
                    "user_uid": str(UserUid.new()),
                    "login": normalized,
                    "algorithm": stored.algorithm,
                    "iterations": stored.iterations,
                    "salt": stored.salt,
                    "digest": stored.digest,
                    "is_default_credential": is_default_credential,
                },
            ).one()
        except DBAPIError as exc:
            sqlstate = str(getattr(exc.orig, "sqlstate", "") or "")
            if sqlstate == _UNIQUE_VIOLATION:
                raise DomainError(
                    ErrorCode.CONFLICT,
                    message="a user with this login already exists",
                ) from exc
            raise
        return _record(row)

    def change_password(
        self,
        session: Session,
        *,
        user_uid: str,
        current_password: str,
        new_password: str,
    ) -> UserRecord | None:
        """Replace this account's password, and revoke every credential minted under the old one.

        ``None`` when the current password is not this account's, and when there is no such
        account. One answer for both, for the same reason :meth:`authenticate` gives one:
        the caller holding a credential for a deleted account learns nothing from being told
        which it was.

        **The order of the four steps is the security property, not house style.**

        1. the current password is proved first, so nothing about the *new* one -- not even
           that it was malformed -- is reported to somebody who has not shown they may
           change it;
        2. the new password is refused when it is the current one, because an operation
           called "change password" that changes nothing would tell a reviewer their
           password had changed when it had not;
        3. the new digest is derived, which is where the mechanical bounds in
           :mod:`~auditmanager.access.passwords` apply and raise;
        4. one UPDATE writes the digest, clears ``is_default_credential`` and raises
           ``token_epoch``.

        The returned record carries the **new** epoch, so the caller can mint a credential
        that the very next request will accept. A caller that minted before reading it would
        mint under the old epoch and hand out a credential already dead on arrival.
        """
        credential = session.execute(
            _SELECT_CREDENTIAL_BY_UID, {"user_uid": user_uid}
        ).first()
        if credential is None:
            # The same derivation an unknown login costs in `authenticate`. The caller here
            # already holds a credential, so this is not an enumeration oracle in the same
            # sense -- but the two paths through this method should still cost the same,
            # and a cheap refusal would say "that account is gone" in the timing.
            spend_a_verification(current_password)
            return None

        algorithm, iterations, salt, digest = credential
        stored = StoredPassword(
            algorithm=algorithm,
            iterations=int(iterations),
            salt=salt,
            digest=digest,
        )
        try:
            matched = verify_password(stored, current_password)
        except DomainError as exc:
            if exc.code is ErrorCode.VALIDATION_FAILED:
                # An empty or over-long *current* password is a failed attempt, exactly as
                # in `authenticate`. Anything else -- an unreadable stored credential -- is
                # a real fault and propagates rather than being reported as a wrong password.
                return None
            raise
        if not matched:
            return None

        if is_the_same_password(current_password, new_password):
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message=(
                    "the new password must differ from the current one; a password change "
                    "that changes nothing is not a password change"
                ),
            )

        # Raises `VALIDATION_FAILED` for an empty or over-long new password, before any
        # write. Nothing has been changed at this point, so a refusal here leaves the
        # account exactly as it was.
        replacement = hash_password(new_password)

        row = session.execute(
            _CHANGE_PASSWORD,
            {
                "user_uid": user_uid,
                "algorithm": replacement.algorithm,
                "iterations": replacement.iterations,
                "salt": replacement.salt,
                "digest": replacement.digest,
            },
        ).first()
        if row is None:  # pragma: no cover - the row was read microseconds ago
            return None
        record = _record(row)
        _log.warning(
            "%s: user %r changed their password; every credential minted for them before "
            "this moment is refused from now on (token_epoch is now %d).",
            CREDENTIALS_REVOKED,
            record.login,
            record.token_epoch,
        )
        return record

    def revoke_credentials(
        self, session: Session, *, login: str | None = None
    ) -> tuple[UserRecord, ...]:
        """Raise the credential epoch, for one account or for every account.

        ``login=None`` means **every** account, and it is spelled as an explicit default
        rather than as an overload, because the two are one statement apart and the caller
        must say which it meant. The operator entry point
        (:mod:`auditmanager.access.revoke`) refuses to run without one of the two, so
        "revoke" typed with no argument does nothing rather than revoking the installation.

        The returned records carry the **new** epochs. An empty tuple means nothing matched
        -- an unknown login, or an empty table -- and is not an error: the caller decides
        whether "nothing to revoke" is a problem, and the CLI reports it as one.
        """
        if login is None:
            rows = session.execute(_REVOKE_EVERY).all()
        else:
            rows = session.execute(_REVOKE_ONE, {"login": normalize_login(login)}).all()
        records = tuple(sorted((_record(row) for row in rows), key=lambda r: r.login))
        for record in records:
            _log.warning(
                "%s: every credential held by %r is refused from now on "
                "(token_epoch is now %d).",
                CREDENTIALS_REVOKED,
                record.login,
                record.token_epoch,
            )
        return records

    def token_epoch(self, session: Session, user_uid: str) -> int | None:
        """The generation of credentials this account currently accepts, or ``None``.

        ``None`` means there is no such account, and the seam treats it as a refusal -- so
        deleting a row revokes that account's credentials for free, which is the answer to
        "what happens to the credential of an account that no longer exists". Before this
        column it kept working until it expired.

        This is the statement that runs on **every** authorized request. It is a primary-key
        lookup returning one integer, and it is deliberately not cached: a cache would give
        revocation a delay, and a revocation that takes effect in a little while is the
        thing this whole mechanism exists to replace.
        """
        row = session.execute(_SELECT_TOKEN_EPOCH, {"user_uid": user_uid}).first()
        return None if row is None else int(row[0])

    def clear_failed_sign_ins(
        self, session: Session, *, login: str | None = None
    ) -> tuple[UserRecord, ...]:
        """Release the sign-in brake, for one account or for every account.

        **This is the way back from a lockout that does not require waiting**, and it is
        why the lockout is a column rather than a counter in the API process's memory: an
        operator whose owner cannot sign in has to be able to open the door *now*, and
        "restart something and hope that was the process holding it" is not a way back.

        ``login=None`` means every account, spelled as an explicit default for the same
        reason :meth:`revoke_credentials` spells it that way: the two are one predicate
        apart and the caller must say which it meant.

        Returns the records that **changed**. An account with nothing to release is not in
        the answer, which is how :mod:`auditmanager.access.unlock` tells "that opened
        something" from "there was nothing shut" without asking a second question. Empty is
        a fact and not an error.
        """
        if login is None:
            rows = session.execute(_CLEAR_EVERY).all()
        else:
            rows = session.execute(_CLEAR_ONE, {"login": normalize_login(login)}).all()
        records = tuple(sorted((_record(row) for row in rows), key=lambda r: r.login))
        for record in records:
            _log.warning(
                "%s: the sign-in brake on %r was released by an operator. The count and "
                "any cooling-off period it had earned are gone.",
                SIGN_IN_BLOCKED,
                record.login,
            )
        return records

    def accounts_blocked_from_signing_in(
        self, session: Session
    ) -> tuple[UserRecord, ...]:
        """Every account that is inside a cooling-off period **at this instant**.

        A query rather than a boolean, so the answer names the accounts, and reading it
        costs no login -- the same shape and the same reason as
        :meth:`users_on_default_credentials`. The state it reports is temporary by
        construction, which is precisely why somebody has to be able to see it: the one
        question a lockout ever produces is "why can the owner not sign in", and it is
        asked by a person who cannot sign in to find out.
        """
        rows = session.execute(_SELECT_BLOCKED).all()
        return tuple(_record(row) for row in rows)

    def users_on_default_credentials(self, session: Session) -> tuple[UserRecord, ...]:
        """Every user whose password is still the one the system seeded them with.

        The state this reports is meant to be temporary. It is a query rather than a
        boolean so the answer names the accounts, and reading it costs no login.
        """
        rows = session.execute(_SELECT_DEFAULT_CREDENTIALS).all()
        return tuple(_record(row) for row in rows)
