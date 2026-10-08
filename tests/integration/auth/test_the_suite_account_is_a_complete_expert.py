"""`W49-SEAL-01c` -- the one helper every suite account comes from, over real rows.

``tests/support/accounts.py``'s ``complete_expert_account`` is what seven suites mint their
credentials from. Those suites are long-lived against a shared lane, so an account an
earlier run created is returned as it is -- which means a helper that stopped granting
``expert`` or completing the profile would stay green in every one of them until the lane
was rebuilt. This module asks the helper for an account that cannot already exist and
asserts what the row then holds, inside a session that is rolled back and never committed.
"""

from __future__ import annotations

import secrets

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from am_test_accounts import SUITE_DISPLAY_LABEL, complete_expert_account, suite_login


def test_a_new_suite_account_is_a_complete_expert_with_an_email_login(
    session_factory: sessionmaker[Session],
) -> None:
    label = f"w49-suite-helper-{secrets.token_hex(5)}"
    with session_factory() as session:
        try:
            record = complete_expert_account(session, label)
            assert record.login == f"{label}@suite.invalid" == suite_login(label)
            assert record.profile_complete is True
            assert record.display_label == SUITE_DISPLAY_LABEL == "Сьютова Е."
            roles = set(
                session.execute(
                    text("SELECT role FROM app_user_role WHERE user_uid = :u"),
                    {"u": str(record.user_uid)},
                ).scalars()
            )
            assert roles == {"expert"}
            # The grant raised the epoch; the record handed back is the one read after it,
            # so a credential minted from it is accepted by the very next request.
            epoch = session.execute(
                text("SELECT token_epoch FROM app_user WHERE user_uid = :u"),
                {"u": str(record.user_uid)},
            ).scalar_one()
            assert record.token_epoch == int(epoch)
            # Idempotent: asked again, the same row and nothing new.
            again = complete_expert_account(session, label)
            assert again.user_uid == record.user_uid
            assert again.token_epoch == record.token_epoch
        finally:
            session.rollback()
