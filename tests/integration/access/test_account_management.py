"""Profile, standing, archive, restore, purge, reset and the §3.2 invariants -- no router.

`W49-ACCESS-01b`. Every test drives :class:`auditmanager.access.accounts.AccountRepository`
on a fresh database at head, exactly as the seal's routers will, and never builds an
application: `IDENTITY-WAVES.md` §5 requires each invariant to be proven by a test that
bypasses the router.
"""

from __future__ import annotations

import threading
import time

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from auditmanager.access.accounts import (
    LAST_ADMIN,
    SELF_ACTION,
    AccountInvariantViolation,
    AccountRepository,
)
from auditmanager.access.models import AccountStanding
from auditmanager.access.repository import UserRepository
from auditmanager.shared.errors import DomainError, ErrorCode

PASSWORD = "a-long-enough-password"  # noqa: S105 - a test literal
TEMPORARY = "temporary-password-1"  # noqa: S105 - a test literal

users = UserRepository()
accounts = AccountRepository()


def _create(
    session: Session,
    email: str,
    *,
    roles: tuple[str, ...] = ("expert",),
    names: tuple[str, str] | None = ("Петрова", "Анна"),
) -> str:
    record = users.create_user(session, email, PASSWORD)
    uid = str(record.user_uid)
    if names is not None:
        accounts.complete_profile(
            session, user_uid=uid, email=None, last_name=names[0], first_name=names[1]
        )
    for role in roles:
        accounts.grant_role(session, user_uid=uid, role=role, granted_by=None)
    session.commit()
    return uid


def _seed(session: Session) -> str:
    seed = users.find_by_login(session, "admin")
    assert seed is not None
    return str(seed.user_uid)


def _epoch(session: Session, uid: str) -> int:
    return int(
        session.execute(
            text("SELECT token_epoch FROM app_user WHERE user_uid = :u"), {"u": uid}
        ).scalar_one()
    )


# =======================================================================================
# The standing read.
# =======================================================================================


class TestTheStandingRead:
    def test_the_seed_after_0015(self, session: Session) -> None:
        standing = accounts.account_standing(session, _seed(session))
        assert standing == AccountStanding(
            token_epoch=1,
            is_default_credential=True,
            archived=False,
            profile_complete=False,
            roles=frozenset({"admin", "expert"}),
        )

    def test_an_account_with_no_role_answers_an_empty_set(self, session: Session) -> None:
        uid = _create(session, "anna@example.com", roles=())
        standing = accounts.account_standing(session, uid)
        assert standing is not None
        assert standing.roles == frozenset()
        assert standing.profile_complete is True
        assert standing.is_default_credential is False

    def test_archived_is_reported_and_purged_is_none(self, session: Session) -> None:
        seed = _seed(session)
        uid = _create(session, "anna@example.com")
        accounts.archive_account(session, actor_uid=seed, user_uid=uid)
        session.commit()
        standing = accounts.account_standing(session, uid)
        assert standing is not None and standing.archived is True
        assert users.credential_standing(session, uid) is None, (
            "the credential seam's read must give an archived account no standing"
        )
        accounts.purge_account(session, actor_uid=seed, user_uid=uid)
        session.commit()
        assert accounts.account_standing(session, uid) is None

    def test_an_unknown_role_in_storage_is_a_raise_not_a_dropped_member(
        self, session: Session
    ) -> None:
        uid = _create(session, "anna@example.com")
        session.execute(text("ALTER TABLE app_user_role DROP CONSTRAINT ck_app_user_role_role"))
        session.execute(
            text("INSERT INTO app_user_role (user_uid, role) VALUES (:u, 'superuser')"),
            {"u": uid},
        )
        with pytest.raises(DomainError) as caught:
            accounts.account_standing(session, uid)
        assert caught.value.code is ErrorCode.VALIDATION_FAILED

    def test_it_is_one_statement(self, session: Session, migrated_engine: Engine) -> None:
        """The read runs on every credentialed request; it must stay one round trip."""
        from sqlalchemy import event

        statements: list[str] = []

        def count(conn, cursor, statement, *args):  # noqa: ANN001
            statements.append(statement)

        uid = _seed(session)
        event.listen(migrated_engine, "before_cursor_execute", count)
        try:
            with Session(migrated_engine) as fresh:
                accounts.account_standing(fresh, uid)
        finally:
            event.remove(migrated_engine, "before_cursor_execute", count)
        selects = [s for s in statements if s.lstrip().upper().startswith("SELECT")]
        assert len(selects) == 1, statements


# =======================================================================================
# The profile.
# =======================================================================================


class TestTheProfile:
    def test_a_legacy_account_completes_with_an_email_in_one_update(
        self, session: Session
    ) -> None:
        seed = _seed(session)
        record = accounts.update_my_profile(
            session,
            user_uid=seed,
            email="Owner@Example.com",
            last_name="Петрова",
            first_name="Анна",
            middle_name="Сергеевна",
        )
        session.commit()
        assert record.login == "owner@example.com"
        assert record.profile_complete
        assert record.display_label == "Петрова А. С."
        assert users.find_by_login(session, "admin") is None
        assert users.authenticate(session, "owner@example.com", "password") is not None

    def test_a_legacy_account_cannot_complete_without_an_email(self, session: Session) -> None:
        with pytest.raises(DomainError) as caught:
            accounts.update_my_profile(
                session, user_uid=_seed(session), last_name="Петрова", first_name="Анна"
            )
        assert caught.value.code is ErrorCode.VALIDATION_FAILED
        assert caught.value.detail_fields == {"field": "email"}

    def test_an_incomplete_account_with_an_email_login_completes_on_its_own_login(
        self, session: Session
    ) -> None:
        uid = _create(session, "anna@example.com", names=None)
        record = accounts.update_my_profile(
            session, user_uid=uid, last_name="Петрова", first_name="Анна"
        )
        assert record.login == "anna@example.com" and record.profile_complete

    def test_a_complete_profile_changes_names_but_never_its_login(
        self, session: Session
    ) -> None:
        uid = _create(session, "anna@example.com")
        renamed = accounts.update_my_profile(
            session,
            user_uid=uid,
            email="ANNA@example.com",
            last_name="Иванова",
            first_name="Анна",
        )
        assert renamed.display_label == "Иванова А."
        with pytest.raises(DomainError) as caught:
            accounts.update_my_profile(
                session,
                user_uid=uid,
                email="other@example.com",
                last_name="Иванова",
                first_name="Анна",
            )
        assert caught.value.detail_fields == {"field": "login"}

    def test_completing_onto_a_login_an_active_account_holds_is_login_taken(
        self, session: Session
    ) -> None:
        _create(session, "owner@example.com")
        with pytest.raises(DomainError) as caught:
            accounts.update_my_profile(
                session,
                user_uid=_seed(session),
                email="owner@example.com",
                last_name="Петрова",
                first_name="Анна",
            )
        assert caught.value.code is ErrorCode.CONFLICT
        assert caught.value.detail_fields == {"conflict_reason": "login_taken"}
        session.rollback()
        assert users.find_by_login(session, "admin") is not None

    def test_an_administrator_naming_a_legacy_account_leaves_it_legacy(
        self, session: Session
    ) -> None:
        record = accounts.update_names(
            session, user_uid=_seed(session), last_name="Петрова", first_name="Анна"
        )
        assert record.login == "admin"
        assert record.profile_complete is False
        assert record.display_label == "Петрова А."


# =======================================================================================
# Archive and restore.
# =======================================================================================


class TestArchiveAndRestore:
    def test_archive_names_the_administrator_revokes_and_shuts_sign_in(
        self, session: Session
    ) -> None:
        seed = _seed(session)
        uid = _create(session, "anna@example.com")
        before = _epoch(session, uid)
        record = accounts.archive_account(session, actor_uid=seed, user_uid=uid)
        session.commit()
        assert record.archived and record.archived_by == seed
        assert _epoch(session, uid) == before + 1
        assert users.find_by_login(session, "anna@example.com") is None
        assert users.authenticate(session, "anna@example.com", PASSWORD) is None

    def test_an_archived_account_signs_in_exactly_like_an_unknown_one(
        self, session: Session, monkeypatch
    ) -> None:
        """Same answer and the same work: one derivation each, no row written."""
        from auditmanager.access import passwords

        seed = _seed(session)
        uid = _create(session, "anna@example.com")
        accounts.archive_account(session, actor_uid=seed, user_uid=uid)
        session.commit()
        calls: list[int] = []
        original = passwords._derive
        monkeypatch.setattr(
            passwords, "_derive", lambda *a, **k: (calls.append(1), original(*a, **k))[1]
        )
        assert users.authenticate(session, "anna@example.com", PASSWORD) is None
        archived_calls = len(calls)
        calls.clear()
        assert users.authenticate(session, "nobody@example.com", PASSWORD) is None
        assert archived_calls == len(calls) == 1
        failed = session.execute(
            text("SELECT failed_sign_ins FROM app_user WHERE user_uid = :u"), {"u": uid}
        ).scalar_one()
        assert failed == 0, "an attempt on an archived account was counted against it"

    def test_an_account_cannot_archive_itself(self, session: Session) -> None:
        seed = _seed(session)
        with pytest.raises(AccountInvariantViolation) as caught:
            accounts.archive_account(session, actor_uid=seed, user_uid=seed)
        assert caught.value.invariant == SELF_ACTION
        assert caught.value.code is ErrorCode.PERMISSION_DENIED

    def test_the_last_active_administrator_cannot_be_archived(self, session: Session) -> None:
        seed = _seed(session)
        other = _create(session, "anna@example.com", roles=("expert",))
        with pytest.raises(AccountInvariantViolation) as caught:
            accounts.archive_account(session, actor_uid=other, user_uid=seed)
        assert caught.value.invariant == LAST_ADMIN
        assert caught.value.code is ErrorCode.CONFLICT
        session.rollback()
        second_admin = _create(session, "boris@example.com", roles=("admin",))
        accounts.archive_account(session, actor_uid=second_admin, user_uid=seed)
        session.commit()

    def test_an_archived_administrator_does_not_count_as_another(self, session: Session) -> None:
        seed = _seed(session)
        second = _create(session, "boris@example.com", roles=("admin",))
        third = _create(session, "clara@example.com", roles=("admin",))
        accounts.archive_account(session, actor_uid=seed, user_uid=second)
        accounts.archive_account(session, actor_uid=seed, user_uid=third)
        session.commit()
        with pytest.raises(AccountInvariantViolation) as caught:
            accounts.archive_account(session, actor_uid=third, user_uid=seed)
        assert caught.value.invariant == LAST_ADMIN

    def test_archiving_twice_is_a_transition_the_machine_does_not_have(
        self, session: Session
    ) -> None:
        seed = _seed(session)
        uid = _create(session, "anna@example.com")
        accounts.archive_account(session, actor_uid=seed, user_uid=uid)
        with pytest.raises(DomainError) as caught:
            accounts.archive_account(session, actor_uid=seed, user_uid=uid)
        assert caught.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED
        assert caught.value.detail_fields == {
            "machine": "app_user",
            "current_state": "archived",
            "requested_state": "archived",
        }

    def test_an_archived_login_may_be_taken_and_restore_then_answers_login_taken(
        self, session: Session
    ) -> None:
        seed = _seed(session)
        first = _create(session, "anna@example.com")
        accounts.archive_account(session, actor_uid=seed, user_uid=first)
        session.commit()
        second = _create(session, "anna@example.com")
        with pytest.raises(DomainError) as caught:
            accounts.restore_account(session, actor_uid=seed, user_uid=first)
        assert caught.value.detail_fields == {"conflict_reason": "login_taken"}
        session.rollback()
        accounts.archive_account(session, actor_uid=seed, user_uid=second)
        before = _epoch(session, first)
        restored = accounts.restore_account(session, actor_uid=seed, user_uid=first)
        session.commit()
        assert not restored.archived and restored.archived_by is None
        assert _epoch(session, first) == before + 1
        assert users.authenticate(session, "anna@example.com", PASSWORD) is not None

    def test_restoring_an_active_account_is_refused(self, session: Session) -> None:
        uid = _create(session, "anna@example.com")
        with pytest.raises(DomainError) as caught:
            accounts.restore_account(session, actor_uid=_seed(session), user_uid=uid)
        assert caught.value.code is ErrorCode.STATE_TRANSITION_NOT_ALLOWED

    def test_two_concurrent_archives_of_the_last_two_administrators_leave_one(
        self, migrated_engine: Engine
    ) -> None:
        """The race the last-administrator rule exists for, with two real sessions.

        Two administrators, A and B, remain (the seed is archived away first). Two *other*
        accounts, X and Y, archive them at the same instant: X archives B, Y archives A.
        The actors are deliberately neither A nor B -- if A archived B and B archived A,
        each UPDATE's foreign-key check on ``archived_by`` would lock the other's row and
        serialise the two by accident, and the test would pass without the administrator
        set ever being locked (measured: mutation M01b-3 survived that version). Here
        nothing but :data:`_LOCK_ACTIVE_ADMINS` makes the second wait, and when it does it
        recounts after the first commits and is refused.
        """
        with Session(migrated_engine) as setup:
            seed = _seed(setup)
            a = _create(setup, "anna@example.com", roles=("admin",))
            b = _create(setup, "boris@example.com", roles=("admin",))
            x = _create(setup, "xenia@example.com", roles=("expert",))
            y = _create(setup, "yuri@example.com", roles=("expert",))
            accounts.archive_account(setup, actor_uid=a, user_uid=seed)
            setup.commit()

        outcome: dict[str, object] = {}
        first = Session(migrated_engine)
        accounts.archive_account(first, actor_uid=x, user_uid=b)  # holds the locks

        def second() -> None:
            with Session(migrated_engine) as other:
                other.execute(text("SET lock_timeout = '20s'"))
                try:
                    accounts.archive_account(other, actor_uid=y, user_uid=a)
                    other.commit()
                    outcome["second"] = "archived"
                except AccountInvariantViolation as exc:
                    outcome["second"] = exc.invariant

        worker = threading.Thread(target=second)
        worker.start()
        waiting = 0
        deadline = time.monotonic() + 5
        # A fresh connection per probe: pg_stat_activity is a per-transaction snapshot
        # (stats_fetch_consistency = cache), so one connection polling inside one transaction
        # would read the first answer for ever.
        while time.monotonic() < deadline and not outcome:
            with migrated_engine.connect() as probe:
                waiting = probe.execute(
                    text(
                        "SELECT count(*) FROM pg_stat_activity "
                        "WHERE datname = current_database() AND wait_event_type = 'Lock'"
                    )
                ).scalar_one()
            if waiting:
                break
            time.sleep(0.05)
        first.commit()
        first.close()
        worker.join(30)
        with Session(migrated_engine) as check:
            active_admins = check.execute(
                text(
                    "SELECT count(*) FROM app_user u JOIN app_user_role r USING (user_uid) "
                    "WHERE r.role = 'admin' AND u.archived_at IS NULL"
                )
            ).scalar_one()
        assert active_admins == 1, "both administrators were archived"
        assert outcome == {"second": LAST_ADMIN}
        assert waiting, "the second archive never waited on the first one's lock"


# =======================================================================================
# Purge, against the register.
# =======================================================================================


class TestPurge:
    def test_an_archived_unreferenced_account_is_deleted_and_its_login_freed(
        self, session: Session
    ) -> None:
        seed = _seed(session)
        uid = _create(session, "anna@example.com")
        session.execute(
            text(
                "INSERT INTO registration_request (request_id, login, last_name, first_name, "
                "password_algorithm, password_iterations, password_salt, password_hash) "
                "VALUES ('reg_01ARZ3NDEKTSV4RRFFQ69G5FAA', 'anna@example.com', 'Петрова', "
                "'Анна', 'pbkdf2_sha256', 600000, :s, :d)"
            ),
            {"s": "0" * 32, "d": "0" * 64},
        )
        session.execute(
            text(
                "UPDATE registration_request SET status = 'approved', decided_at = now(), "
                "decided_by = :seed, created_user_uid = :uid, password_algorithm = NULL, "
                "password_iterations = NULL, password_salt = NULL, password_hash = NULL"
            ),
            {"seed": seed, "uid": uid},
        )
        accounts.archive_account(session, actor_uid=seed, user_uid=uid)
        session.commit()

        accounts.purge_account(session, actor_uid=seed, user_uid=uid)
        session.commit()
        assert accounts.get_account(session, uid) is None
        assert session.execute(
            text("SELECT count(*) FROM app_user_role WHERE user_uid = :u"), {"u": uid}
        ).scalar_one() == 0
        request = session.execute(
            text("SELECT status, created_user_uid FROM registration_request")
        ).one()
        assert tuple(request) == ("approved", None), "the creating request is history"
        _create(session, "anna@example.com")

    def test_a_non_archived_account_is_refused_against_the_machine(
        self, session: Session
    ) -> None:
        uid = _create(session, "anna@example.com")
        with pytest.raises(DomainError) as caught:
            accounts.purge_account(session, actor_uid=_seed(session), user_uid=uid)
        assert caught.value.detail_fields == {
            "machine": "app_user",
            "current_state": "active",
            "requested_state": "purged",
        }

    def test_an_account_cannot_purge_itself(self, session: Session) -> None:
        seed = _seed(session)
        with pytest.raises(AccountInvariantViolation) as caught:
            accounts.purge_account(session, actor_uid=seed, user_uid=seed)
        assert caught.value.invariant == SELF_ACTION

    @pytest.mark.parametrize(
        "reference", ["archived_by", "granted_by", "decided_by", "author_user_uid"]
    )
    def test_a_referenced_account_stays_archived(self, session: Session, reference: str) -> None:
        """Each RESTRICT entry of the register, alone, refuses the purge."""
        seed = _seed(session)
        subject = _create(session, "anna@example.com", roles=("admin",))
        bystander = _create(session, "boris@example.com", roles=())
        if reference == "archived_by":
            accounts.archive_account(session, actor_uid=subject, user_uid=bystander)
        elif reference == "granted_by":
            accounts.grant_role(session, user_uid=bystander, role="expert", granted_by=subject)
        elif reference == "decided_by":
            session.execute(
                text(
                    "INSERT INTO registration_request (request_id, login, last_name, "
                    "first_name, password_algorithm, password_iterations, password_salt, "
                    "password_hash) VALUES ('reg_01ARZ3NDEKTSV4RRFFQ69G5FAB', "
                    "'clara@example.com', 'Петрова', 'Анна', 'pbkdf2_sha256', 600000, :s, :d)"
                ),
                {"s": "0" * 32, "d": "0" * 64},
            )
            session.execute(
                text(
                    "UPDATE registration_request SET status = 'rejected', decided_at = now(), "
                    "decided_by = :by, rejection_reason = 'нет', password_algorithm = NULL, "
                    "password_iterations = NULL, password_salt = NULL, password_hash = NULL"
                ),
                {"by": subject},
            )
        else:
            session.execute(text("SET LOCAL session_replication_role = replica"))
            session.execute(
                text(
                    "INSERT INTO expert_decision_event (decision_id, finding_uid, "
                    "finding_observation_id, event_type, verdict, author_label, "
                    "author_user_uid) VALUES ('dec_01ARZ3NDEKTSV4RRFFQ69G5FAA', "
                    "'fnd_01ARZ3NDEKTSV4RRFFQ69G5FAA', 'fobs_01ARZ3NDEKTSV4RRFFQ69G5FAA', "
                    "'accept', 'accepted', 'Петрова А.', :uid)"
                ),
                {"uid": subject},
            )
        session.commit()
        accounts.archive_account(session, actor_uid=seed, user_uid=subject)
        session.commit()

        assert accounts.references_to(session, subject)
        with pytest.raises(DomainError) as caught:
            accounts.purge_account(session, actor_uid=seed, user_uid=subject)
        assert caught.value.code is ErrorCode.CONFLICT
        assert caught.value.detail_fields == {"conflict_reason": "account_referenced"}
        session.rollback()
        assert accounts.get_account(session, subject).record.archived


# =======================================================================================
# The administrator's reset.
# =======================================================================================


class TestReset:
    def test_a_reset_sets_must_change_revokes_and_clears_the_brake(
        self, session: Session
    ) -> None:
        seed = _seed(session)
        uid = _create(session, "anna@example.com")
        session.execute(
            text(
                "UPDATE app_user SET failed_sign_ins = 5, sign_in_blocked_until = "
                "now() + interval '5 minutes' WHERE user_uid = :u"
            ),
            {"u": uid},
        )
        before = _epoch(session, uid)
        record = accounts.reset_password(
            session, actor_uid=seed, user_uid=uid, temporary_password=TEMPORARY
        )
        session.commit()
        assert record.is_default_credential is True
        assert record.token_epoch == before + 1
        assert record.sign_in_blocked_until is None and record.failed_sign_ins == 0
        assert users.authenticate(session, "anna@example.com", PASSWORD) is None
        assert users.authenticate(session, "anna@example.com", TEMPORARY) is not None

    def test_an_account_cannot_reset_itself(self, session: Session) -> None:
        seed = _seed(session)
        with pytest.raises(AccountInvariantViolation) as caught:
            accounts.reset_password(
                session, actor_uid=seed, user_uid=seed, temporary_password=TEMPORARY
            )
        assert caught.value.invariant == SELF_ACTION

    @pytest.mark.parametrize("temporary", ["short", "anna@example.com", "Password"])
    def test_the_temporary_password_meets_the_policy(self, session: Session, temporary) -> None:
        uid = _create(session, "anna@example.com")
        with pytest.raises(DomainError) as caught:
            accounts.reset_password(
                session, actor_uid=_seed(session), user_uid=uid, temporary_password=temporary
            )
        assert caught.value.code is ErrorCode.VALIDATION_FAILED


def test_list_accounts_hides_the_archived_unless_asked(session: Session) -> None:
    seed = _seed(session)
    uid = _create(session, "anna@example.com")
    accounts.archive_account(session, actor_uid=seed, user_uid=uid)
    session.commit()
    active = {str(a.record.user_uid) for a in accounts.list_accounts(session)}
    every = {str(a.record.user_uid) for a in accounts.list_accounts(session, include_archived=True)}
    assert active == {seed}
    assert every == {seed, uid}
    listed = {str(a.record.user_uid): a.roles for a in accounts.list_accounts(session)}
    assert listed[seed] == frozenset({"admin", "expert"})
