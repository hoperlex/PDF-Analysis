"""Accounts a person can hold: e-mail login, names, roles, archive, registration requests.

Revision ID: 0015_accounts_roles_registration
Revises: 0014_durable_analysis_effects

`W49-ACCESS-01a`, under `W49-PLAN.md` §3.1-§3.3 and rulings `R-55`, `R-56`, `R-59`, `R-60`,
`R-61`. What this revision creates, by table:

``app_user``
    * ``last_name``, ``first_name``, ``middle_name`` -- each NULL or 1..60 letters separated
      by single spaces, hyphens or apostrophes (the mixed-script rule is the boundary's);
    * ``profile_completed_at`` -- NULL for **every** account that exists at upgrade, so every
      such account is a legacy account until it completes its profile (`R-59`). No seed
      constant is hard-coded anywhere in this revision;
    * ``ck_app_user_login_format`` is replaced: a login is an e-mail, **or** the profile is
      incomplete and the login has the legacy shape ``0006`` enforced. The second arm keeps
      ``0006``'s guarantee that raw SQL cannot store ``Admin`` beside ``admin``; it is
      narrower than "or ``profile_completed_at IS NULL``" and never wider;
    * ``archived_at``/``archived_by`` (`R-61`) -- both or neither, never archived by itself;
    * ``uq_app_user_login`` becomes a **partial unique index** ``WHERE archived_at IS NULL``,
      so an archived account's login may be taken by a new one.

``app_user_role``
    The role set (P-4): ``(user_uid, role)`` primary key, ``role IN ('expert','admin')``.
    **Backfill**: every account gets ``expert``; the row whose login is ``admin`` -- the
    ``0006`` seed -- also gets ``admin``. When no such row exists the revision still
    succeeds and says so in the deployment log; ``python -m auditmanager.access.grant`` is
    then the way in.

``registration_request``
    One request per submission, ``reg_<ULID>``, ``pending`` until an administrator decides.
    The password is stored hashed (same columns and CHECKs as ``app_user``) **only until
    the decision**: the decision UPDATE nulls the four columns. The three sign-in-throttle
    columns of ``app_user`` are repeated here, because a status read is a password check
    and is braked like one. One ``pending`` row per login (partial unique index).
    ``trg_registration_request_guard`` permits exactly: throttle-only updates; the one
    decision ``pending -> approved | rejected`` with the password nulled; and the later
    nulling of ``created_user_uid`` **by the purge cascade only** (recognised by
    ``pg_trigger_depth()``). Everything else -- a second decision, a password write after
    the decision, a manual ``created_user_uid`` update, a DELETE -- is refused.

``expert_decision_event.author_user_uid``
    A nullable column with a RESTRICT foreign key, NULL for history. Its writer is
    ``W49-DECISIONS-01``; this revision adds the column only.

**The reference register.** Every foreign key to ``app_user(user_uid)`` this revision
creates is listed in ``auditmanager.access.references.ACCOUNT_REFERENCES`` with its delete
action, and ``tests/integration/db/test_accounts_migration.py`` asserts the schema's foreign
keys to ``app_user`` equal that register -- so a purge the register would allow and the
schema would not, or the reverse, is a red test and never a production surprise.

**Downgrade is forward-only in practice.** It refuses while ``app_user_role`` or
``registration_request`` hold a row, and after the backfill that is every real database:
the rollback of W49 is a database restore, not this function. It also refuses while any
row carries something the ``0014`` shape cannot hold -- a name, a completed profile, an
archive, an e-mail login, an authored decision -- for the reason ``0006`` refuses: those
values exist nowhere else. On a tree whose access rows are empty it runs, and a test
proves it.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0015_accounts_roles_registration"
down_revision: str | None = "0014_durable_analysis_effects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_log = logging.getLogger("alembic.migration.accounts_roles_registration")

#: The ``0006`` seed's login. The backfill grants it ``admin`` by this value and nothing
#: else; no other account, and no password, is assumed.
SEED_LOGIN = "admin"

#: Restated from ``auditmanager.access.models`` -- a migration never imports the boundary
#: it predates. ``test_accounts_migration.py`` compares each literal with its constant.
USER_UID_PATTERN = r"^usr_[0-9A-HJKMNP-TV-Z]{26}$"
REGISTRATION_ID_PATTERN = r"^reg_[0-9A-HJKMNP-TV-Z]{26}$"
LEGACY_LOGIN_PATTERN = r"^[a-z0-9][a-z0-9._-]{0,99}$"
EMAIL_LOGIN_PATTERN = (
    r"^[a-z0-9!#$%&'*+/=?^_`{|}~.-]{1,64}"
    r"@[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$"
)
MAX_EMAIL_LENGTH = 254
_LETTER = "[A-Za-zÀ-ÖØ-öø-ÿĀ-ɏЀ-ӿ]"
PERSON_NAME_PATTERN = f"^{_LETTER}+([ '’-]{_LETTER}+)*$"
MAX_PERSON_NAME_LENGTH = 60
MAX_REJECTION_REASON_LENGTH = 256
ROLES = ("expert", "admin")


def _literal(value: str) -> str:
    """A SQL string literal for a constant of this file (never for runtime input)."""
    return "'" + value.replace("'", "''") + "'"


def _email_check(column: str) -> str:
    return (
        f"(char_length({column}) <= {MAX_EMAIL_LENGTH} "
        f"AND {column} ~ {_literal(EMAIL_LOGIN_PATTERN)})"
    )


def _name_check(column: str, *, nullable: bool) -> str:
    shape = (
        f"(char_length({column}) BETWEEN 1 AND {MAX_PERSON_NAME_LENGTH} "
        f"AND {column} ~ {_literal(PERSON_NAME_PATTERN)})"
    )
    return f"({column} IS NULL OR {shape})" if nullable else shape


def _uid_check(column: str) -> str:
    return f"({column} IS NULL OR {column} ~ {_literal(USER_UID_PATTERN)})"


#: The four password columns, as ``0006`` constrains them on ``app_user``.
_PASSWORD_COLUMNS = (
    "password_algorithm",
    "password_iterations",
    "password_salt",
    "password_hash",
)

#: The throttle columns, named as ``0008`` names them on ``app_user``.
_THROTTLE_COLUMNS = ("failed_sign_ins", "last_failed_sign_in_at", "sign_in_blocked_until")


def upgrade() -> None:
    _extend_app_user()
    _create_app_user_role()
    _create_registration_request()
    _attach_registration_guard()
    _add_decision_author()
    _backfill_roles()


def _extend_app_user() -> None:
    op.execute(
        f"""
        ALTER TABLE app_user
            ADD COLUMN last_name            text NULL,
            ADD COLUMN first_name           text NULL,
            ADD COLUMN middle_name          text NULL,
            ADD COLUMN profile_completed_at timestamptz NULL,
            ADD COLUMN archived_at          timestamptz NULL,
            ADD COLUMN archived_by          text NULL,
            ADD CONSTRAINT fk_app_user_archived_by FOREIGN KEY (archived_by)
                REFERENCES app_user (user_uid) ON DELETE RESTRICT,
            ADD CONSTRAINT ck_app_user_archived_by_format
                CHECK ({_uid_check('archived_by')}),
            ADD CONSTRAINT ck_app_user_archive_pair
                CHECK ((archived_at IS NULL) = (archived_by IS NULL)),
            ADD CONSTRAINT ck_app_user_not_archived_by_self
                CHECK (archived_by IS NULL OR archived_by <> user_uid),
            ADD CONSTRAINT ck_app_user_last_name
                CHECK ({_name_check('last_name', nullable=True)}),
            ADD CONSTRAINT ck_app_user_first_name
                CHECK ({_name_check('first_name', nullable=True)}),
            ADD CONSTRAINT ck_app_user_middle_name
                CHECK ({_name_check('middle_name', nullable=True)}),
            ADD CONSTRAINT ck_app_user_complete_profile_has_names
                CHECK (profile_completed_at IS NULL
                       OR (last_name IS NOT NULL AND first_name IS NOT NULL));
        """
    )
    op.execute("ALTER TABLE app_user DROP CONSTRAINT ck_app_user_login_format;")
    op.execute(
        f"""
        ALTER TABLE app_user ADD CONSTRAINT ck_app_user_login_format CHECK (
            {_email_check('login')}
            OR (profile_completed_at IS NULL
                AND login ~ {_literal(LEGACY_LOGIN_PATTERN)})
        );
        """
    )
    op.execute("ALTER TABLE app_user DROP CONSTRAINT uq_app_user_login;")
    op.execute(
        "CREATE UNIQUE INDEX uq_app_user_login ON app_user (login) "
        "WHERE archived_at IS NULL;"
    )
    op.execute("CREATE INDEX ix_app_user_archived_by ON app_user (archived_by);")
    op.execute(
        "COMMENT ON COLUMN app_user.login IS "
        "'The sign-in identifier: since 0015 a normalised e-mail address (trimmed, "
        "zero-width characters removed, lower-cased, ASCII, at most 254 characters). An "
        "account that existed before 0015 keeps its legacy login until it completes its "
        "profile, which rewrites login, names and profile_completed_at in one UPDATE. "
        "Unique among accounts that are not archived. It is NOT the identity: user_uid "
        "is.';"
    )
    op.execute(
        "COMMENT ON COLUMN app_user.profile_completed_at IS "
        "'When this account gave its names and an e-mail login. NULL for every account "
        "that existed at 0015 (a legacy account): such an account reaches only its own "
        "profile and password until it completes. Complete it from the host with python "
        "-m auditmanager.access.profile.';"
    )
    op.execute(
        "COMMENT ON COLUMN app_user.archived_at IS "
        "'When an administrator archived this account. Archive is the normal removal: an "
        "archived account has no standing, cannot sign in, and every credential it held "
        "was revoked in the same UPDATE. It can be restored. Its login may be taken by a "
        "new account meanwhile, and restore then answers login_taken.';"
    )
    op.execute(
        "COMMENT ON COLUMN app_user.archived_by IS "
        "'The administrator who archived this account. A reference (ON DELETE "
        "RESTRICT): an administrator who archived anyone cannot be purged.';"
    )


def _create_app_user_role() -> None:
    roles = ", ".join(_literal(role) for role in ROLES)
    op.execute(
        f"""
        CREATE TABLE app_user_role (
            user_uid   text NOT NULL,
            role       text NOT NULL,
            granted_at timestamptz NOT NULL DEFAULT now(),
            granted_by text NULL,
            CONSTRAINT pk_app_user_role PRIMARY KEY (user_uid, role),
            CONSTRAINT fk_app_user_role_user FOREIGN KEY (user_uid)
                REFERENCES app_user (user_uid) ON DELETE CASCADE,
            CONSTRAINT fk_app_user_role_granted_by FOREIGN KEY (granted_by)
                REFERENCES app_user (user_uid) ON DELETE RESTRICT,
            CONSTRAINT ck_app_user_role_role CHECK (role IN ({roles})),
            CONSTRAINT ck_app_user_role_user_uid_format
                CHECK (user_uid ~ {_literal(USER_UID_PATTERN)}),
            CONSTRAINT ck_app_user_role_granted_by_format
                CHECK ({_uid_check('granted_by')})
        );
        """
    )
    op.execute("CREATE INDEX ix_app_user_role_granted_by ON app_user_role (granted_by);")
    op.execute("CREATE INDEX ix_app_user_role_role ON app_user_role (role);")
    op.execute(
        "COMMENT ON TABLE app_user_role IS "
        "'The roles an account holds, as a set: expert, admin, both or none. Enforced on "
        "the server by the operation register in api/security.py; no role travels in a "
        "credential. Every change raises app_user.token_epoch in the same transaction.';"
    )
    op.execute(
        "COMMENT ON COLUMN app_user_role.granted_by IS "
        "'The administrator who granted this role; NULL for the 0015 backfill and for the "
        "operator command. A reference (ON DELETE RESTRICT).';"
    )


def _create_registration_request() -> None:
    password_present = " AND ".join(f"{column} IS NOT NULL" for column in _PASSWORD_COLUMNS)
    password_absent = " AND ".join(f"{column} IS NULL" for column in _PASSWORD_COLUMNS)
    op.execute(
        f"""
        CREATE TABLE registration_request (
            request_id             text PRIMARY KEY,
            login                  text NOT NULL,
            last_name              text NOT NULL,
            first_name             text NOT NULL,
            middle_name            text NULL,
            password_algorithm     text NULL,
            password_iterations    integer NULL,
            password_salt          text NULL,
            password_hash          text NULL,
            status                 text NOT NULL DEFAULT 'pending',
            submitted_at           timestamptz NOT NULL DEFAULT now(),
            decided_at             timestamptz NULL,
            decided_by             text NULL,
            rejection_reason       text NULL,
            created_user_uid       text NULL,
            failed_sign_ins        integer NOT NULL DEFAULT 0,
            last_failed_sign_in_at timestamptz NULL,
            sign_in_blocked_until  timestamptz NULL,
            CONSTRAINT fk_registration_request_decided_by FOREIGN KEY (decided_by)
                REFERENCES app_user (user_uid) ON DELETE RESTRICT,
            CONSTRAINT fk_registration_request_created_user FOREIGN KEY (created_user_uid)
                REFERENCES app_user (user_uid) ON DELETE SET NULL,
            CONSTRAINT ck_registration_request_request_id_format
                CHECK (request_id ~ {_literal(REGISTRATION_ID_PATTERN)}),
            CONSTRAINT ck_registration_request_login CHECK ({_email_check('login')}),
            CONSTRAINT ck_registration_request_last_name
                CHECK ({_name_check('last_name', nullable=False)}),
            CONSTRAINT ck_registration_request_first_name
                CHECK ({_name_check('first_name', nullable=False)}),
            CONSTRAINT ck_registration_request_middle_name
                CHECK ({_name_check('middle_name', nullable=True)}),
            CONSTRAINT ck_registration_request_password_algorithm
                CHECK (password_algorithm IS NULL OR password_algorithm = 'pbkdf2_sha256'),
            CONSTRAINT ck_registration_request_password_iterations
                CHECK (password_iterations IS NULL OR password_iterations >= 100000),
            CONSTRAINT ck_registration_request_password_salt_format
                CHECK (password_salt IS NULL OR password_salt ~ '^[0-9a-f]{{32}}$'),
            CONSTRAINT ck_registration_request_password_hash_format
                CHECK (password_hash IS NULL OR password_hash ~ '^[0-9a-f]{{64}}$'),
            CONSTRAINT ck_registration_request_status
                CHECK (status IN ('pending', 'approved', 'rejected')),
            CONSTRAINT ck_registration_request_decided_by_format
                CHECK ({_uid_check('decided_by')}),
            CONSTRAINT ck_registration_request_created_user_uid_format
                CHECK ({_uid_check('created_user_uid')}),
            CONSTRAINT ck_registration_request_rejection_reason CHECK (
                rejection_reason IS NULL
                OR (char_length(rejection_reason) BETWEEN 1 AND {MAX_REJECTION_REASON_LENGTH}
                    AND btrim(rejection_reason) = rejection_reason)
            ),
            CONSTRAINT ck_registration_request_failed_sign_ins
                CHECK (failed_sign_ins >= 0),
            -- The lifecycle's shape. created_user_uid may be NULL on an approved row:
            -- the purge cascade nulls it, and the guard trigger permits nothing else to.
            CONSTRAINT ck_registration_request_decision_shape CHECK (
                (status = 'pending'
                    AND decided_at IS NULL AND decided_by IS NULL
                    AND rejection_reason IS NULL AND created_user_uid IS NULL
                    AND {password_present})
                OR (status = 'approved'
                    AND decided_at IS NOT NULL AND decided_by IS NOT NULL
                    AND rejection_reason IS NULL
                    AND {password_absent})
                OR (status = 'rejected'
                    AND decided_at IS NOT NULL AND decided_by IS NOT NULL
                    AND rejection_reason IS NOT NULL AND created_user_uid IS NULL
                    AND {password_absent})
            )
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_registration_request_pending_login "
        "ON registration_request (login) WHERE status = 'pending';"
    )
    op.execute(
        "CREATE INDEX ix_registration_request_status_submitted "
        "ON registration_request (status, submitted_at);"
    )
    op.execute(
        "CREATE INDEX ix_registration_request_login ON registration_request (login);"
    )
    op.execute(
        "CREATE INDEX ix_registration_request_decided_by "
        "ON registration_request (decided_by);"
    )
    op.execute(
        "CREATE INDEX ix_registration_request_created_user_uid "
        "ON registration_request (created_user_uid);"
    )
    op.execute(
        "COMMENT ON TABLE registration_request IS "
        "'A request for an account, submitted without a credential and decided by an "
        "administrator. No mail is sent (R-56): the applicant reads the status at "
        "sign-in. The password is held as a salted PBKDF2 digest until the decision, "
        "which nulls it; approval moves it to the new account in the same transaction. "
        "Rows are history and are never deleted.';"
    )
    op.execute(
        "COMMENT ON COLUMN registration_request.created_user_uid IS "
        "'The account approval created. History, not a reference: ON DELETE SET NULL, so "
        "purging that account leaves this row with NULL here. The guard trigger permits "
        "that nulling only from the cascade.';"
    )
    op.execute(
        "COMMENT ON COLUMN registration_request.rejection_reason IS "
        "'The administrator''s reason, 1-256 characters. Free text, so it travels in the "
        "status read and never as an error detail.';"
    )


def _attach_registration_guard() -> None:
    decision_columns = (
        "status",
        "decided_at",
        "decided_by",
        "rejection_reason",
        "created_user_uid",
        *_PASSWORD_COLUMNS,
        *_THROTTLE_COLUMNS,
    )
    decision_array = ", ".join(_literal(column) for column in decision_columns)
    throttle_array = ", ".join(_literal(column) for column in _THROTTLE_COLUMNS)
    password_absent = " AND ".join(f"NEW.{column} IS NULL" for column in _PASSWORD_COLUMNS)
    op.execute(
        f"""
        CREATE FUNCTION am_guard_registration_request() RETURNS trigger
        LANGUAGE plpgsql AS $fn$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: registration_request rows are history '
                    'and are never deleted'
                    USING ERRCODE = 'AM003';
            END IF;

            IF TG_OP = 'INSERT' THEN
                IF NEW.status IS DISTINCT FROM 'pending' THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: registration_request may not be '
                        'created in state %', NEW.status
                        USING ERRCODE = 'AM001',
                              DETAIL = 'machine=registration_request, '
                                       || 'current_state=<none>, requested_state='
                                       || coalesce(NEW.status, '<null>');
                END IF;
                RETURN NEW;
            END IF;

            -- 1. The brake on status reads may move in any state, and nothing else with it.
            IF (to_jsonb(OLD) - ARRAY[{throttle_array}])
               IS NOT DISTINCT FROM (to_jsonb(NEW) - ARRAY[{throttle_array}]) THEN
                RETURN NEW;
            END IF;

            -- 2. The one decision: pending -> approved | rejected, the password nulled, the
            --    request's own columns untouched.
            IF OLD.status = 'pending' AND NEW.status IN ('approved', 'rejected') THEN
                IF NOT ({password_absent}) THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: a decision must null the request''s '
                        'password columns'
                        USING ERRCODE = 'AM003';
                END IF;
                IF NEW.status = 'approved' AND NEW.created_user_uid IS NULL THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: an approval names the account it '
                        'created'
                        USING ERRCODE = 'AM003';
                END IF;
                IF (to_jsonb(OLD) - ARRAY[{decision_array}])
                   IS DISTINCT FROM (to_jsonb(NEW) - ARRAY[{decision_array}]) THEN
                    RAISE EXCEPTION
                        'state_transition_not_allowed: a decision may not rewrite the '
                        'request it decides'
                        USING ERRCODE = 'AM003';
                END IF;
                RETURN NEW;
            END IF;

            -- 3. The purge cascade (ON DELETE SET NULL) nulling created_user_uid on a decided
            --    request. Recognised by depth: the referential action runs inside the
            --    foreign key's own trigger, so it reaches here at depth 2; a manual UPDATE
            --    of the same column reaches here at depth 1 and is refused below.
            IF OLD.status <> 'pending' AND OLD.status = NEW.status
               AND OLD.created_user_uid IS NOT NULL AND NEW.created_user_uid IS NULL
               AND pg_trigger_depth() > 1
               AND (to_jsonb(OLD) - 'created_user_uid')
                   IS NOT DISTINCT FROM (to_jsonb(NEW) - 'created_user_uid') THEN
                RETURN NEW;
            END IF;

            IF OLD.status IS DISTINCT FROM NEW.status THEN
                RAISE EXCEPTION
                    'state_transition_not_allowed: registration_request has no transition '
                    '% -> %', OLD.status, NEW.status
                    USING ERRCODE = 'AM001',
                          DETAIL = 'machine=registration_request, current_state='
                                   || OLD.status || ', requested_state='
                                   || coalesce(NEW.status, '<null>');
            END IF;
            RAISE EXCEPTION
                'state_transition_not_allowed: registration_request is immutable apart '
                'from its one decision'
                USING ERRCODE = 'AM003';
        END
        $fn$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_registration_request_guard
            BEFORE INSERT OR UPDATE OR DELETE ON registration_request
            FOR EACH ROW EXECUTE FUNCTION am_guard_registration_request();
        """
    )


def _add_decision_author() -> None:
    # The ledger is append-only (am_append_only, BEFORE UPDATE OR DELETE). ALTER TABLE
    # fires no row trigger, and the CHECK validates every existing row as NULL.
    op.execute(
        f"""
        ALTER TABLE expert_decision_event
            ADD COLUMN author_user_uid text NULL,
            ADD CONSTRAINT fk_expert_decision_event_author_user
                FOREIGN KEY (author_user_uid) REFERENCES app_user (user_uid)
                ON DELETE RESTRICT,
            ADD CONSTRAINT ck_expert_decision_event_author_user_uid_format
                CHECK ({_uid_check('author_user_uid')});
        """
    )
    op.execute(
        "CREATE INDEX ix_expert_decision_event_author_user_uid "
        "ON expert_decision_event (author_user_uid) WHERE author_user_uid IS NOT NULL;"
    )
    op.execute(
        "COMMENT ON COLUMN expert_decision_event.author_user_uid IS "
        "'The account that recorded this decision. NULL for every event written before "
        "0015, read as author account unknown and never as a fault. author_label is the "
        "display string; this is the identity. A reference (ON DELETE RESTRICT): an "
        "expert who decided anything cannot be purged.';"
    )


def _backfill_roles() -> None:
    bind = op.get_bind()
    bind.execute(
        text("INSERT INTO app_user_role (user_uid, role) SELECT user_uid, 'expert' FROM app_user")
    )
    administrators = bind.execute(
        text(
            "INSERT INTO app_user_role (user_uid, role) "
            "SELECT user_uid, 'admin' FROM app_user WHERE login = :seed "
            "RETURNING user_uid"
        ),
        {"seed": SEED_LOGIN},
    ).all()
    accounts = bind.execute(text("SELECT count(*) FROM app_user")).scalar_one()
    _log.warning(
        "0015_accounts_roles_registration: %d existing account(s) now hold the role "
        "'expert', and every one of them is a legacy account until it completes its "
        "profile (names and an e-mail login): python -m auditmanager.access.profile "
        "--login <login> --email <e-mail> --last-name <...> --first-name <...>.",
        accounts,
    )
    if administrators:
        _log.warning(
            "0015_accounts_roles_registration: the account %r also holds the role 'admin'.",
            SEED_LOGIN,
        )
    else:
        _log.warning(
            "0015_accounts_roles_registration: NO ACCOUNT HOLDS THE ROLE 'admin' -- no "
            "account has the login %r. Nobody can approve a registration or manage "
            "accounts until an operator runs python -m auditmanager.access.grant --login "
            "<login> --role admin.",
            SEED_LOGIN,
        )


def downgrade() -> None:
    """Refuse while anything here holds a value the ``0014`` shape cannot; else undo.

    See the module docstring: after the backfill every real database refuses, and the
    rollback of W49 is a restore. The counts are named so an operator sees what blocks.
    """
    bind = op.get_bind()
    occupied = {
        name: int(bind.execute(text(query)).scalar_one())
        for name, query in (
            ("app_user_role", "SELECT count(*) FROM app_user_role"),
            ("registration_request", "SELECT count(*) FROM registration_request"),
            (
                "app_user with names or a completed profile",
                "SELECT count(*) FROM app_user WHERE last_name IS NOT NULL "
                "OR first_name IS NOT NULL OR middle_name IS NOT NULL "
                "OR profile_completed_at IS NOT NULL",
            ),
            ("archived app_user", "SELECT count(*) FROM app_user WHERE archived_at IS NOT NULL"),
            (
                "app_user with an e-mail login",
                "SELECT count(*) FROM app_user WHERE login !~ "
                + _literal(LEGACY_LOGIN_PATTERN),
            ),
            (
                "expert_decision_event with an author account",
                "SELECT count(*) FROM expert_decision_event WHERE author_user_uid IS NOT NULL",
            ),
        )
    }
    if any(occupied.values()):
        rendered = ", ".join(f"{name}={count}" for name, count in occupied.items() if count)
        raise RuntimeError(
            "refusing to downgrade 0015_accounts_roles_registration: it would discard "
            f"account data that exists nowhere else ({rendered}). 0015 is forward-only on "
            "a real database; the rollback is a database restore."
        )

    op.execute("DROP INDEX ix_expert_decision_event_author_user_uid;")
    op.execute(
        "ALTER TABLE expert_decision_event "
        "DROP CONSTRAINT ck_expert_decision_event_author_user_uid_format, "
        "DROP CONSTRAINT fk_expert_decision_event_author_user, "
        "DROP COLUMN author_user_uid;"
    )
    op.execute("DROP TABLE registration_request;")
    op.execute("DROP FUNCTION am_guard_registration_request();")
    op.execute("DROP TABLE app_user_role;")
    op.execute("DROP INDEX uq_app_user_login;")
    op.execute("DROP INDEX ix_app_user_archived_by;")
    op.execute("ALTER TABLE app_user DROP CONSTRAINT ck_app_user_login_format;")
    op.execute(
        "ALTER TABLE app_user "
        "DROP CONSTRAINT ck_app_user_complete_profile_has_names, "
        "DROP CONSTRAINT ck_app_user_middle_name, "
        "DROP CONSTRAINT ck_app_user_first_name, "
        "DROP CONSTRAINT ck_app_user_last_name, "
        "DROP CONSTRAINT ck_app_user_not_archived_by_self, "
        "DROP CONSTRAINT ck_app_user_archive_pair, "
        "DROP CONSTRAINT ck_app_user_archived_by_format, "
        "DROP CONSTRAINT fk_app_user_archived_by, "
        "DROP COLUMN archived_by, "
        "DROP COLUMN archived_at, "
        "DROP COLUMN profile_completed_at, "
        "DROP COLUMN middle_name, "
        "DROP COLUMN first_name, "
        "DROP COLUMN last_name;"
    )
    op.execute(
        "ALTER TABLE app_user ADD CONSTRAINT uq_app_user_login UNIQUE (login);"
    )
    op.execute(
        "ALTER TABLE app_user ADD CONSTRAINT ck_app_user_login_format "
        f"CHECK (login ~ {_literal(LEGACY_LOGIN_PATTERN)});"
    )
    op.execute(
        "COMMENT ON COLUMN app_user.login IS "
        "'The name typed at the sign-in form, stored already lower-cased and stripped. "
        "It is UNIQUE and it is a natural key for lookup, but it is NOT the identity: "
        "user_uid is, and a login that is renamed later must not take the identity with "
        "it.';"
    )
