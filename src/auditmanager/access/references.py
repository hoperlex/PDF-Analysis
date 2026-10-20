"""The written register of every column that may name an account (`R-61`, P-12).

`W49-PLAN.md` §3.1. Purging an account is irreversible, so "nothing references it" cannot
be a judgement made at the call site: it is this register, and every entry is a real
foreign key to ``app_user(user_uid)`` created by migration ``0015`` or a later one
(``0024_version_classification`` adds the classification's confirmer;
``0025_work_assignments`` adds an assignment's first assignee and creator, and each of its
events' actor and new assignee; ``0026_price_lists`` adds a price list's uploader and a
vendor-list revision's author; ``0027_optimisation_proposals`` adds the expert who started an
optimisation pass and the expert who decided an optimisation proposal).

Three kinds of entry, by what the database does when the account row is deleted:

* ``RESTRICT`` -- a **reference**. The account archived someone, granted a role, decided a
  request or authored a decision; deleting it would leave history pointing at nobody, so
  the database refuses and :meth:`AccountRepository.purge_account` answers
  ``conflict`` with ``conflict_reason: account_referenced`` before it gets that far;
* ``SET NULL`` -- **history, not a reference**: the request that created the account keeps
  its row, with the creator's identity removed by the cascade (and only by the cascade --
  ``trg_registration_request_guard``);
* ``CASCADE`` -- the account's **own** rows, which go with it.

``tests/integration/db/test_accounts_migration.py`` enumerates the schema's foreign keys to
``app_user`` from ``pg_constraint`` and asserts they equal this register, entry for entry
and action for action. So a new column naming an account that is not registered here is a
red test, and the database refuses a purge that this register would have allowed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

__all__ = [
    "ACCOUNT_REFERENCES",
    "AccountReference",
    "restricting_references",
]

OnDelete = Literal["RESTRICT", "SET NULL", "CASCADE"]


@dataclass(frozen=True, slots=True)
class AccountReference:
    """One column that holds a ``user_uid``, and what deleting that account does to it."""

    table: str
    column: str
    on_delete: OnDelete
    #: Why the column exists, for the operator who meets a refused purge.
    meaning: str


ACCOUNT_REFERENCES: Final[tuple[AccountReference, ...]] = (
    AccountReference(
        "app_user", "archived_by", "RESTRICT", "this account archived another account"
    ),
    AccountReference(
        "app_user_role", "granted_by", "RESTRICT", "this account granted a role"
    ),
    AccountReference(
        "registration_request",
        "decided_by",
        "RESTRICT",
        "this account decided a registration request",
    ),
    AccountReference(
        "expert_decision_event",
        "author_user_uid",
        "RESTRICT",
        "this account recorded an expert decision",
    ),
    AccountReference(
        "document_version_classification",
        "confirmed_by_user_uid",
        "RESTRICT",
        "this account confirmed a version's project stage and section (W59-SECTION-SEAL-01)",
    ),
    AccountReference(
        "work_assignment",
        "assignee_user_uid",
        "RESTRICT",
        "this account was given a piece of work (W61-DISPATCHER-01)",
    ),
    AccountReference(
        "work_assignment",
        "created_by_user_uid",
        "RESTRICT",
        "this account assigned a piece of work (W61-DISPATCHER-01)",
    ),
    AccountReference(
        "work_assignment_event",
        "actor_user_uid",
        "RESTRICT",
        "this account moved an assignment along its history (W61-DISPATCHER-01)",
    ),
    AccountReference(
        "work_assignment_event",
        "new_assignee_user_uid",
        "RESTRICT",
        "this account was given a piece of work by reassignment (W61-DISPATCHER-01)",
    ),
    AccountReference(
        "price_list_revision",
        "uploaded_by_user_uid",
        "RESTRICT",
        "this account uploaded a project price list (W60-PRICE-LIST-01)",
    ),
    AccountReference(
        "vendor_list_revision",
        "set_by_user_uid",
        "RESTRICT",
        "this account changed a vendor list (W60-PRICE-LIST-01)",
    ),
    AccountReference(
        "optimisation_pass",
        "started_by_user_uid",
        "RESTRICT",
        "this account started an optimisation pass (W60-OPT-PROPOSALS-01)",
    ),
    AccountReference(
        "optimisation_proposal_decision",
        "actor_user_uid",
        "RESTRICT",
        "this account decided an optimisation proposal (W60-OPT-PROPOSALS-01)",
    ),
    AccountReference(
        "registration_request",
        "created_user_uid",
        "SET NULL",
        "this account was created by approving a request (history, not a reference)",
    ),
    AccountReference(
        "app_user_role", "user_uid", "CASCADE", "the roles this account holds (its own rows)"
    ),
    AccountReference(
        "account_release_mark", "user_uid", "CASCADE", "the account's own release read mark"
    ),
)


def restricting_references() -> tuple[AccountReference, ...]:
    """The entries that make an account unpurgeable while any row names it."""
    return tuple(entry for entry in ACCOUNT_REFERENCES if entry.on_delete == "RESTRICT")
