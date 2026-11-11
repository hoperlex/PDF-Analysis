"""The written register of every column that may name an account (`R-61`, P-12).

`W49-PLAN.md` §3.1. Purging an account is irreversible, so "nothing references it" cannot
be a judgement made at the call site: it is this register, and every entry is a real
foreign key to ``app_user(user_uid)`` created by migration ``0015`` or a later one
(``0024_version_classification`` adds the classification's confirmer;
``0025_work_assignments`` adds an assignment's first assignee and creator, and each of its
events' actor and new assignee; ``0026_price_lists`` adds a price list's uploader and a
vendor-list revision's author; ``0027_optimisation_proposals`` adds the expert who started an
optimisation pass and the expert who decided an optimisation proposal;
``0028_classification_corrections`` adds the expert who corrected a version's classification).

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

**Columns that name an account and are deliberately NOT here: no foreign key**
(``DECISION-MEMORY-01`` section 3.3, ``ADR-0027``). The decision memory outlives its source,
so the one account column it copies -- ``decision_memory_decision.author_user_uid``, written
since phase M1 from the deciding ledger event's author -- is an opaque ``usr_...`` identity
with **no** foreign key to ``app_user`` (open question Q7): ``purgeUser`` stays possible, and
the id then becomes an orphan the memory never resolves. The account that *acts on* the memory
is different: ``decision_memory_status_event.actor_user_uid`` (who withdrew, restored or forgot a case; a
tombstone must keep a resolvable actor) and ``decision_memory_setting_event.actor_user_uid`` (who changed an
installation setting) have a ``RESTRICT`` key since ``0061_decision_memory_m2`` (``D-393``), and are register
entries below. The «Прецеденты» seals add two more memory columns without a key: ``decision_memory_comment.author_user_uid``
(an expert's comment copied from the ledger, ``0064``) and the view column ``decision_memory_pattern_current.status_actor_user_uid``
(``0066``, read from the keyed ``decision_memory_pattern_status_event.actor_user_uid``). Such a
column is not a register entry (it is not a foreign key, so ``purge_account`` cannot see it and
the register-equals-schema test above does not list it); it is named in this header instead, and
``test_every_memory_column_that_names_an_account_without_a_foreign_key_is_named_in_this_header``
fails when a ``decision_memory_*`` column of that kind exists and is not named here.
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
    AccountReference("stage_chain_batch", "actor_user_uid", "RESTRICT", "this account started a stage comparison batch (CMP-SEAL-C4)"),
    AccountReference("stage_link_repair_event", "actor_user_uid", "RESTRICT", "this account recorded or reverted a stage link repair (CMP-SEAL-C4)"),
    AccountReference("stage_card_verdict", "actor_user_uid", "RESTRICT", "this account decided a stage change card (CMP-SEAL-C4)"),
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
        "document_version_classification_correction",
        "corrected_by_user_uid",
        "RESTRICT",
        "this account corrected a version's project stage or section (CLASSIFICATION-CORRECTION-01)",
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
        "schedule_setting_event",
        "actor_user_uid",
        "RESTRICT",
        "this account changed the schedule's default plan or time zone (R-152b, migration 0055)",
    ),
    AccountReference(
        "schedule_plan_event",
        "engineer_user_uid",
        "RESTRICT",
        "this account was given a monthly plan (R-151x, migration 0055)",
    ),
    AccountReference(
        "schedule_plan_event",
        "actor_user_uid",
        "RESTRICT",
        "this account set a monthly plan (R-151x, migration 0055)",
    ),
    AccountReference(
        "work_calendar_event",
        "actor_user_uid",
        "RESTRICT",
        "this account changed the work calendar (R-152d, migration 0055)",
    ),
    AccountReference(
        "engineer_absence_event",
        "engineer_user_uid",
        "RESTRICT",
        "this account was marked absent (R-152d, migration 0055)",
    ),
    AccountReference(
        "engineer_absence_event",
        "actor_user_uid",
        "RESTRICT",
        "this account marked an absence (R-152d, migration 0055)",
    ),
    AccountReference(
        "work_assignment_schedule_event",
        "actor_user_uid",
        "RESTRICT",
        "this account planned an assignment's date (R-152h, migration 0055)",
    ),
    AccountReference(
        "decision_memory_status_event",
        "actor_user_uid",
        "RESTRICT",
        "this account withdrew, restored or forgot a decision-memory case (DECISION-MEMORY-01 phase M2, migration 0061)",
    ),
    AccountReference(
        "decision_memory_setting_event",
        "actor_user_uid",
        "RESTRICT",
        "this account changed an installation setting of the decision memory (DECISION-MEMORY-01 phase M2, migration 0061)",
    ),
    AccountReference(
        "precedent_setting_event",
        "actor_user_uid",
        "RESTRICT",
        "this account changed a switch or a setting of the «Прецеденты» programme (ADR-0029, migration 0064)",
    ),
    AccountReference(
        "vector_control_event",
        "actor_user_uid",
        "RESTRICT",
        "this account paused or resumed the vectors' night window (ADR-0029, migration 0064)",
    ),
    AccountReference(
        "decision_memory_pattern_status_event",
        "actor_user_uid",
        "RESTRICT",
        "this account approved, rejected or suspended a refusal pattern (ADR-0029, migration 0066)",
    ),
    AccountReference(
        "finding_execution_status",
        "set_by_user_uid",
        "RESTRICT",
        "this account set a finding's execution status (R-151g, migration 0054)",
    ),
    AccountReference(
        "document_tag",
        "created_by_user_uid",
        "RESTRICT",
        "this account tagged a document (R-151e, migration 0053)",
    ),
    AccountReference(
        "document",
        "archived_by_user_uid",
        "RESTRICT",
        "this account archived a document (R-151a, migration 0052)",
    ),
    AccountReference(
        "audit_run",
        "started_by_user_uid",
        "RESTRICT",
        "this account started an audit run (R-151v, migration 0051)",
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
