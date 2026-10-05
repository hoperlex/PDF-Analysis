"""The values the ``access`` boundary hands out, and the login rule it enforces.

Two things are deliberate.

**No credential material in a returned record.** :class:`UserRecord` carries the
identity, the login, the timestamps and the default-credential flag. It carries no
digest, no salt and no iteration count, so there is no call path that returns a
credential to a caller who only asked who the user is. Verification happens inside the
repository, against columns that never leave it.

**The login is normalised before it is stored, not when it is read.** A stored
``Admin`` that is looked up case-insensitively would let one account be addressed by
many spellings, and uniqueness would then depend on every call site remembering to fold
the case. Instead the boundary folds once, the column holds the folded value, and the
database's own UNIQUE constraint is the guarantee. The CHECK in the migration repeats
the rule, so raw SQL cannot insert a spelling the boundary would have refused.

**A third thing since `R-37`: a login and a display name are different kinds of string
and this module keeps them apart.** A login is an address -- typed, folded, unique, ASCII,
sayable down a telephone. A display name is what other reviewers *read* on a decision
somebody else took: the reviewer's own name, in their own script, not unique, because two
people really can be called the same thing. They are normalised by two functions with two
rules for that reason, and the identity is neither of them -- it is ``user_uid``, which is
why a rename of either changes nothing about who somebody is.

**`W49-ACCESS-01` adds the account a person can hold** (`W49-PLAN.md` §3.1-§3.3):

* the login becomes an **e-mail address** -- trimmed, zero-width characters removed,
  lower-cased, ASCII, at most 254 characters (:func:`normalize_email`). A login written
  before migration ``0015`` keeps the narrow legacy shape (:data:`LOGIN_PATTERN`) until its
  account completes its profile, which rewrites it to an e-mail in the same UPDATE;
* **full names** (:func:`normalize_person_name`): last, first and an optional middle name,
  each at most 60 characters of letters, hyphen, apostrophe and space, and never a word
  that mixes Cyrillic and Latin letters (the ``technic`` rule);
* :func:`name_label` -- "Фамилия И. О.", at most 66 characters -- which
  :attr:`UserRecord.display_label` prefers to ``display_name`` and to the login (`R-55`);
* the **role vocabulary** :data:`ROLES`, a closed set read back from the database by
  :func:`parse_role`, which refuses an unknown value rather than dropping it;
* ``reg_<ULID>`` (:class:`RegistrationId`), minted exactly as ``usr_<ULID>`` is -- a local
  pattern outside the shared identity registry, for the reason :data:`USER_UID_PREFIX`
  gives. ``W49-SEAL-01a`` adds both prefixes to ``identifiers.json`` and to the registry in
  one commit; until then neither may enter the registry, because
  ``tests/contract/domain_p02/test_identifier_catalog.py`` asserts the registry equals the
  catalog.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.shared.identity.ulid import is_valid_ulid, new_ulid

__all__ = [
    "EMAIL_LOGIN_PATTERN",
    "LOGIN_PATTERN",
    "MAX_DISPLAY_NAME_LENGTH",
    "MAX_EMAIL_LENGTH",
    "MAX_LOGIN_LENGTH",
    "MAX_NAME_LABEL_LENGTH",
    "MAX_PERSON_NAME_LENGTH",
    "PERSON_NAME_PATTERN",
    "REGISTRATION_ID_PATTERN",
    "REGISTRATION_ID_PREFIX",
    "ROLES",
    "ROLE_ADMIN",
    "ROLE_EXPERT",
    "USER_UID_PATTERN",
    "USER_UID_PREFIX",
    "Account",
    "AccountStanding",
    "CredentialStanding",
    "RegistrationId",
    "UserRecord",
    "UserUid",
    "is_email_login",
    "is_user_uid",
    "name_label",
    "normalize_display_name",
    "normalize_email",
    "normalize_login",
    "normalize_person_name",
    "parse_role",
]

#: The prefix this boundary allocates its identities under.
#:
#: ``app_user`` is **not** in ``contracts/domain/v1/identifiers.json``: that catalog is
#: frozen and describes the PC-01 analysis domain, which has no user aggregate. So this
#: type deliberately does **not** subclass
#: :class:`auditmanager.shared.identity.OpaqueId` -- doing so would register ``usr`` in
#: the contract's global prefix registry and quietly add a twenty-sixth identity to a
#: catalog a contract test pins. It copies the catalog's *shape* (``<prefix>_<ULID>``,
#: opaque, no decoding of the body) so that when users are contracted, adopting the base
#: class is a renaming rather than a data migration.
USER_UID_PREFIX: Final[str] = "usr"

#: Same body alphabet and length as every other identity in this system.
USER_UID_PATTERN: Final[str] = r"^usr_[0-9A-HJKMNP-TV-Z]{26}$"

_USER_UID_RE: Final[re.Pattern[str]] = re.compile(USER_UID_PATTERN)

#: The login rule, restated in the migration as a CHECK.
#:
#: ASCII, already lower-cased, starting with a letter or a digit. Narrow on purpose: a
#: login is typed at a keyboard by someone who must be able to say it out loud to
#: support, and two logins that differ only by a Unicode confusable are an
#: impersonation, not a feature.
LOGIN_PATTERN: Final[str] = r"^[a-z0-9][a-z0-9._-]{0,99}$"

_LOGIN_RE: Final[re.Pattern[str]] = re.compile(LOGIN_PATTERN)

MAX_LOGIN_LENGTH: Final[int] = 100

#: `W49-PLAN.md` §3.1: the longest e-mail login, RFC 5321's path limit.
MAX_EMAIL_LENGTH: Final[int] = 254

#: The e-mail shape a login holds once its account's profile is complete, restated in
#: migration ``0015`` as ``ck_app_user_login_format`` and ``ck_registration_request_login``.
#:
#: **ASCII, on purpose**, for the reason :data:`LOGIN_PATTERN` is ASCII: a login is typed
#: and said down a telephone, and two logins that differ by a Unicode confusable are an
#: impersonation. An internationalised domain is typed in its ``xn--`` form. The local part
#: is RFC 5322's ``atext`` plus the dot, at most 64 characters; the domain is at least two
#: dot-separated labels of letters, digits and inner hyphens. The same text is a valid
#: PostgreSQL regular expression and a valid Python one, and a test compares the two
#: engines over the same samples.
EMAIL_LOGIN_PATTERN: Final[str] = (
    r"^[a-z0-9!#$%&'*+/=?^_`{|}~.-]{1,64}"
    r"@[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$"
)

_EMAIL_RE: Final[re.Pattern[str]] = re.compile(EMAIL_LOGIN_PATTERN)

#: Characters that are invisible and that a copy-paste carries along: zero-width space,
#: non-joiner and joiner, word joiner, the byte-order mark and the Mongolian vowel
#: separator. `W49-PLAN.md` §3.1 removes them from an e-mail; they are removed from a name
#: for the same reason -- two values that differ only by an invisible character are two
#: values nobody can tell apart.
_ZERO_WIDTH: Final[re.Pattern[str]] = re.compile("[\u200b\u200c\u200d\u2060\ufeff\u180e]")

#: The longest last, first or middle name (`W49-PLAN.md` §3.1).
MAX_PERSON_NAME_LENGTH: Final[int] = 60

#: The longest :func:`name_label`: a 60-character last name, a space, "И.", a space, "О.".
MAX_NAME_LABEL_LENGTH: Final[int] = MAX_PERSON_NAME_LENGTH + 6

_LATIN_LETTERS: Final[str] = "A-Za-z\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u00ff\u0100-\u024f"
_CYRILLIC_LETTERS: Final[str] = "\u0400-\u04ff"
_LETTER: Final[str] = f"[{_LATIN_LETTERS}{_CYRILLIC_LETTERS}]"

#: A name: letters separated by single spaces, hyphens or apostrophes (ASCII ``'`` and the
#: typographic ``’``), starting and ending with a letter. Restated in migration ``0015``
#: as a CHECK on every name column; the mixed-script rule below is enforced here only.
PERSON_NAME_PATTERN: Final[str] = f"^{_LETTER}+([ '\u2019-]{_LETTER}+)*$"

_PERSON_NAME_RE: Final[re.Pattern[str]] = re.compile(PERSON_NAME_PATTERN)
_LATIN_RE: Final[re.Pattern[str]] = re.compile(f"[{_LATIN_LETTERS}]")
_CYRILLIC_RE: Final[re.Pattern[str]] = re.compile(f"[{_CYRILLIC_LETTERS}]")

#: The role vocabulary (`W49-PLAN.md` §3.2, P-4): a set per account, never a hierarchy.
ROLE_EXPERT: Final[str] = "expert"
ROLE_ADMIN: Final[str] = "admin"
ROLES: Final[frozenset[str]] = frozenset({ROLE_EXPERT, ROLE_ADMIN})

#: ``reg_<ULID>``: a registration request's identity. Outside the shared registry for the
#: reason :data:`USER_UID_PREFIX` gives; ``W49-SEAL-01a`` moves both in one commit.
REGISTRATION_ID_PREFIX: Final[str] = "reg"
REGISTRATION_ID_PATTERN: Final[str] = r"^reg_[0-9A-HJKMNP-TV-Z]{26}$"
_REGISTRATION_ID_RE: Final[re.Pattern[str]] = re.compile(REGISTRATION_ID_PATTERN)

#: The longest display name this boundary stores, and the number is **not** this
#: boundary's own.
#:
#: It is ``DecisionEvent.author_label``'s ``maxLength`` in
#: ``contracts/api/v1/openapi.json``, which is the field a display name is eventually
#: written into (`R-37`). A column that allowed a longer one would let an account be given
#: a name that cannot be recorded against a decision -- discovered at the moment an expert
#: records a verdict, which is the worst moment for it. The bound therefore lives where the
#: value is *created*, and the reason it is 128 is written here rather than left to be
#: rediscovered. The migration restates it as a CHECK for the same reason the login pattern
#: is restated there: raw SQL must not be able to write what this boundary would refuse.
MAX_DISPLAY_NAME_LENGTH: Final[int] = 128

#: Anything in the C0 or C1 control range. A display name is rendered on a screen and
#: written into the CSV export, and a newline or a control byte in it is either a broken
#: row or an invisible difference between two names that look identical.
_CONTROL_CHARACTERS: Final[re.Pattern[str]] = re.compile(r"[\x00-\x1f\x7f-\x9f]")


@dataclass(frozen=True, slots=True)
class UserUid:
    """An opaque user identity: ``usr_`` and a ULID body.

    Immutable and compared by value. The body is never decoded: it carries no creation
    time a caller may read and no order a caller may sort on, for the same reason the
    contract's identities do not.
    """

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not _USER_UID_RE.match(self.value):
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message=f"a user identity must match {USER_UID_PATTERN}",
            )

    @classmethod
    def new(cls) -> "UserUid":
        """Allocate a fresh identity. Generated once; never reused, never re-issued."""
        return cls(f"{USER_UID_PREFIX}_{new_ulid()}")

    @classmethod
    def parse(cls, value: str) -> "UserUid":
        return cls(value)

    def __str__(self) -> str:
        return self.value


def _fold(raw: str) -> str:
    """Strip, remove invisible characters, lower-case. Shared by both login shapes."""
    return _ZERO_WIDTH.sub("", raw).strip().lower()


def is_email_login(value: object) -> bool:
    """True when ``value`` is already a stored-form e-mail login."""
    return (
        isinstance(value, str)
        and len(value) <= MAX_EMAIL_LENGTH
        and _EMAIL_RE.fullmatch(value) is not None
    )


def normalize_email(raw: str) -> str:
    """Fold ``raw`` to the stored form of an e-mail login, or refuse it.

    `W49-PLAN.md` §3.1: trimmed, zero-width characters removed, lower-cased, at most
    :data:`MAX_EMAIL_LENGTH` characters, and of the shape :data:`EMAIL_LOGIN_PATTERN`
    describes. A legacy login is **not** accepted here: this is the function a new login
    passes through -- a registration, a profile completion -- and every new login is an
    e-mail. A refusal is a :class:`DomainError`, never a repaired value.
    """
    if not isinstance(raw, str):
        raise DomainError(ErrorCode.VALIDATION_FAILED, message="the e-mail must be text")
    candidate = _fold(raw)
    if not is_email_login(candidate):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=(
                f"the e-mail must be an address of at most {MAX_EMAIL_LENGTH} ASCII "
                "characters, local@domain.tld"
            ),
        )
    return candidate


def normalize_login(raw: str) -> str:
    """Fold ``raw`` to its canonical stored form, or refuse it.

    Since `W49-ACCESS-01` a stored login has one of two shapes: an e-mail
    (:data:`EMAIL_LOGIN_PATTERN`), which every account has once its profile is complete,
    or the legacy shape (:data:`LOGIN_PATTERN`), which an account created before migration
    ``0015`` keeps until then. A lookup accepts either; a new login goes through
    :func:`normalize_email` instead.

    Surrounding whitespace and invisible characters are removed -- copy-paste artifacts,
    not part of a name -- and the result is lower-cased. Anything both patterns refuse is a
    :class:`DomainError`, never a silently repaired value: a login the caller did not type
    is a login they cannot type again.
    """
    if not isinstance(raw, str):
        raise DomainError(ErrorCode.VALIDATION_FAILED, message="the login must be text")
    candidate = _fold(raw)
    if is_email_login(candidate) or _LOGIN_RE.fullmatch(candidate):
        return candidate
    raise DomainError(
        ErrorCode.VALIDATION_FAILED,
        message=(
            "the login must be an e-mail address, or an account's legacy login of 1-100 "
            "characters of a-z, 0-9, dot, dash or underscore starting with a letter or "
            "a digit"
        ),
    )


def normalize_person_name(raw: str | None, *, field: str, required: bool) -> str | None:
    """Fold one of a person's names to its stored form, or refuse it.

    ``field`` names the name in the refusal (``last_name``, ``first_name``,
    ``middle_name``); ``required=False`` lets an absent or blank value mean "no such name",
    which is what an absent middle name is.

    Folding is limited to what cannot be a choice: surrounding whitespace and invisible
    characters are removed and the text is composed (NFC), so a letter typed as a base and a
    combining accent is the same letter as the precomposed one. **Nothing else changes** --
    no case folding, no transliteration -- because a name is read, not typed back.

    Refused: an empty required name; more than :data:`MAX_PERSON_NAME_LENGTH` characters;
    anything but letters separated by single spaces, hyphens or apostrophes; and a word --
    a run between spaces and hyphens -- that mixes Cyrillic and Latin letters, which is how
    "Иванов" with a Latin "о" impersonates "Иванов".
    """
    if raw is None:
        if required:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message=f"{field} is required",
                field=field,
            )
        return None
    if not isinstance(raw, str):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, message=f"{field} must be text", field=field
        )
    candidate = unicodedata.normalize("NFC", _ZERO_WIDTH.sub("", raw)).strip()
    if not candidate:
        if required:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message=f"{field} must not be empty",
                field=field,
            )
        return None
    if len(candidate) > MAX_PERSON_NAME_LENGTH:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=f"{field} must be at most {MAX_PERSON_NAME_LENGTH} characters",
            field=field,
        )
    if _PERSON_NAME_RE.fullmatch(candidate) is None:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=(
                f"{field} must be letters separated by single spaces, hyphens or "
                "apostrophes"
            ),
            field=field,
        )
    for word in re.split(r"[ -]", candidate):
        if _LATIN_RE.search(word) and _CYRILLIC_RE.search(word):
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message=f"{field} mixes Cyrillic and Latin letters inside one word",
                field=field,
            )
    return candidate


def name_label(last_name: str, first_name: str, middle_name: str | None) -> str:
    """"Фамилия И. О." -- the form a person's name is shown in (`W49-PLAN.md` §3.1).

    The last name in full, then the initial of the first name and of the middle name when
    there is one, each followed by a dot. At most :data:`MAX_NAME_LABEL_LENGTH` characters
    for names :func:`normalize_person_name` accepted, which is inside ``author_label``'s
    1..128 by construction.
    """
    label = f"{last_name} {first_name[0].upper()}."
    if middle_name:
        label = f"{label} {middle_name[0].upper()}."
    return label


def parse_role(value: object) -> str:
    """A role read from storage or a request, or a refusal.

    The vocabulary is closed (:data:`ROLES`). An unknown value is refused rather than
    dropped: a role set that silently lost a member it did not recognise would be a
    privilege decision made by a parser.
    """
    if isinstance(value, str) and value in ROLES:
        return value
    raise DomainError(
        ErrorCode.VALIDATION_FAILED,
        message=f"a role must be one of {sorted(ROLES)}",
        field="roles",
    )


@dataclass(frozen=True, slots=True)
class RegistrationId:
    """``reg_<ULID>``: one registration request. Opaque; minted like :class:`UserUid`."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not _REGISTRATION_ID_RE.match(self.value):
            raise DomainError(
                ErrorCode.VALIDATION_FAILED,
                message=f"a registration request identity must match {REGISTRATION_ID_PATTERN}",
            )

    @classmethod
    def new(cls) -> "RegistrationId":
        return cls(f"{REGISTRATION_ID_PREFIX}_{new_ulid()}")

    @classmethod
    def parse(cls, value: str) -> "RegistrationId":
        return cls(value)

    def __str__(self) -> str:
        return self.value


def normalize_display_name(raw: str) -> str:
    """Fold ``raw`` to its stored form, or refuse it.

    Surrounding whitespace is stripped, as on a login: it is a copy-paste artifact and not
    part of a name. **Nothing else is changed** -- no case folding, no transliteration, no
    ASCII restriction. A login is typed at a keyboard and has to be sayable to support,
    which is why :data:`LOGIN_PATTERN` is as narrow as it is; a display name is *read* and
    is the reviewer's own name, so "Анна Петрова" is the ordinary case rather than an
    exception.

    Three refusals, each because the alternative is a defect rather than an inconvenience:

    * **empty or blank** -- ``author_label`` is ``minLength: 1`` and the ledger refuses an
      empty label, so a blank stored here is a refused write at the moment an expert
      records a verdict;
    * **longer than** :data:`MAX_DISPLAY_NAME_LENGTH` -- same reason, from the other end;
    * **a control character** -- see :data:`_CONTROL_CHARACTERS`.

    A refusal is a :class:`DomainError` and never a silently repaired value, for the reason
    :func:`normalize_login` gives: a name the caller did not type is a name they cannot
    type again.
    """
    if not isinstance(raw, str):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, message="the display name must be text"
        )
    candidate = raw.strip()
    if not candidate:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="the display name must not be empty",
        )
    if len(candidate) > MAX_DISPLAY_NAME_LENGTH:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message=(
                f"the display name must be at most {MAX_DISPLAY_NAME_LENGTH} characters"
            ),
        )
    if _CONTROL_CHARACTERS.search(candidate):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED,
            message="the display name must not contain control characters",
        )
    return candidate


@dataclass(frozen=True, slots=True)
class CredentialStanding:
    """The two facts the authorization seam re-reads about an account on every request.

    `R-50`. It is a **second, much narrower projection of the same row** as
    :class:`UserRecord`, and it exists because the statement behind it runs on every
    authorized request: it reads two columns of one row by primary key and returns nothing
    a caller could read an identity out of. ``UserRecord`` carries eleven fields including
    a login, and a per-request statement that returned one would invite exactly that.

    **Two facts and not two statements.** Before `R-50` the seam read ``token_epoch``
    alone. The alternative to widening this record was a second lookup beside it, and the
    argument against is the one :data:`~auditmanager.access.repository._SELECT_CREDENTIAL`
    already makes in this package about the lockout column: a second statement addressed
    at the same row inside one decision is two reads of one row that can disagree -- and
    here the disagreement would be between "this credential is still current" and "this
    account is still on its seeded password", which are the two halves of one refusal.

    Neither field is credential material. ``token_epoch`` is a counter the seam stamps
    into every credential it mints, and ``is_default_credential`` says whether a password
    has ever been changed, never what it is.
    """

    #: The generation of credentials this account accepts right now.
    token_epoch: int
    #: Whether this account is still on the password the deployment seeded it with.
    is_default_credential: bool


@dataclass(frozen=True, slots=True)
class AccountStanding:
    """What the authorization seam needs about an account on every request, in one read.

    `W49-PLAN.md` §3.2. ``W49-SEAL-01`` widens ``api.security.AccountStanding`` and the
    adapter's ``standing_of`` with the last three fields; this is the row read it wires.
    The order of evaluation stays the seam's: ``archived`` (or a stale epoch) is
    ``authentication_required``, then the default credential, then the incomplete profile,
    then the roles. Nothing here is credential material, and no role travels in a token.
    """

    token_epoch: int
    is_default_credential: bool
    archived: bool
    profile_complete: bool
    roles: frozenset[str]


@dataclass(frozen=True, slots=True)
class Account:
    """One account as an administrator manages it: the record and its role set."""

    record: UserRecord
    roles: frozenset[str]


@dataclass(frozen=True, slots=True)
class UserRecord:
    """One user, as anything outside the repository is allowed to see them.

    ``token_epoch`` is the generation of credentials this account currently accepts. It is
    on the public record and not beside the digest, because it is not credential material:
    it is a small integer that says nothing about the password and is *meant* to travel --
    the seam stamps it into every credential it mints and compares it on every request.
    Reading it tells an attacker how many times this account has been revoked and nothing
    else, and hiding it would mean the one value the seam must check on every request could
    only be reached through the one statement that also reads the digest.

    **The last three are `W40-LIMIT`'s and they are two things, not one.**
    ``failed_sign_ins`` with ``last_failed_sign_in_at`` is the **rate limit** -- how many
    consecutive recent attempts have been refused, and when the last one was. On its own it
    refuses nothing. ``sign_in_blocked_until`` is the **lockout** -- the instant before
    which this account's password is not consulted at all, so that even the right one mints
    nothing. ``None`` means this account may be tried now, and a ``None`` here is **never**
    read as a refusal: a nullable field whose absence closed the door would be one restart
    away from shutting an installation out of itself.

    None of the three is credential material either -- they say how often somebody has been
    wrong, never what the password is -- and none of them travels: no operation returns a
    record, and the one thing this boundary hands the API is a credential. They are on the
    record because the operator's two views of the state
    (:mod:`auditmanager.access.check` and :mod:`auditmanager.access.unlock`) read them, and
    an operator who cannot see a lockout cannot answer the only question a lockout ever
    produces.
    """

    user_uid: UserUid
    login: str
    is_default_credential: bool
    created_at: datetime
    password_updated_at: datetime
    token_epoch: int
    token_epoch_updated_at: datetime
    failed_sign_ins: int
    last_failed_sign_in_at: datetime | None
    sign_in_blocked_until: datetime | None
    #: `R-37`. **The name this reviewer chose, or ``None`` because they have not chosen
    #: one.** It is not credential material and it does not travel by itself: what travels
    #: is :attr:`display_label`.
    #:
    #: **Nullable on purpose, and this is the decision `R-37` left open.** The column could
    #: have been ``NOT NULL`` and backfilled from ``login``, which would have been simpler
    #: and would have destroyed -- in data, on the first upgrade, irreversibly -- the
    #: difference between *an account that has not chosen a name* and *an account whose
    #: reviewer chose their own login*. That difference is the only thing that makes the
    #: fallback below visible, and a fallback nobody can see is the silent fallback
    #: ``AGENTS.md`` §4 forbids. Keeping the ``NULL`` makes the state a query --
    #: ``SELECT login FROM app_user WHERE display_name IS NULL`` -- which is exactly what
    #: ``is_default_credential`` does for the seeded password.
    display_name: str | None
    #: `W49-ACCESS-01`. The person's names, ``None`` until somebody gives them; and when the
    #: profile was completed, ``None`` while the account is still a legacy one that reaches
    #: only the operations an incomplete profile reaches (`W49-PLAN.md` §3.2).
    last_name: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    profile_completed_at: datetime | None = None
    #: `R-61`. Archive is the normal removal: an archived account has no standing, so it
    #: cannot sign in and no credential of it is served. ``archived_by`` is the
    #: administrator's identity, a reference that makes that administrator unpurgeable.
    archived_at: datetime | None = None
    archived_by: str | None = None

    @property
    def profile_complete(self) -> bool:
        return self.profile_completed_at is not None

    @property
    def archived(self) -> bool:
        return self.archived_at is not None

    @property
    def display_label(self) -> str:
        """The name to show for this account. **Never empty, by construction.**

        `R-55` sets the precedence, and it is applied **here and nowhere else in the tree**:

        1. the name form "Фамилия И. О." (:func:`name_label`) when the account has a last and
           a first name -- at most 66 characters;
        2. else the ``display_name`` an operator chose (`R-37`, retired after this
           programme) -- at most 128;
        3. else the login.

        The fallback is one expression on the record, so no call site can invent a second
        answer. A blank is impossible: every branch is a non-empty stored value.

        *The bound.* ``author_label`` is 1..128. The first two branches are inside it by
        construction. The third is too for every legacy login (1..100), but an e-mail login
        may be 254 characters -- which is why `W49-PLAN.md` §3.2 lets only a **complete**
        profile write a decision event, and a complete profile always has names, so the
        ledger only ever receives the first branch. That rule is enforced by the
        authorization registers (`W49-SEAL-01`), not by this property.

        *It is not silent.* ``python -m auditmanager.access.check`` names every account
        without a display name, and an account without names is an incomplete profile,
        which the registers refuse everything but its own profile and password.
        """
        if self.last_name and self.first_name:
            return name_label(self.last_name, self.first_name, self.middle_name)
        return self.display_name or self.login


def is_user_uid(value: object) -> bool:
    """True when ``value`` is a syntactically valid user identity."""
    return (
        isinstance(value, str)
        and value.startswith(f"{USER_UID_PREFIX}_")
        and is_valid_ulid(value[len(USER_UID_PREFIX) + 1 :])
    )
