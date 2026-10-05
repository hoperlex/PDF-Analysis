# W49-DECISIONS-01 — the decision event names its author's account

**Task:** `docs/program/tasks/W49-DECISIONS-01.md`. **Base:** `2417ee6` (`integration/w49`, the
ACCESS-01 merge plus the ruling commit). **Plan:** `W49-PLAN.md` §3.1 (the
`expert_decision_event.author_user_uid` bullet) and §4 `W49-DECISIONS-01`. **Branch:**
`agent/w49-decisions-01`. **Lane:** `gate-w49dec`, ports `56560`, `60160/60161`
(`PORT_REGISTRY.md`), checked free with `ss -ltn` before `make foundation`.

## Premise, re-measured first

`git grep -n 'author_label' -- src/auditmanager/decisions/ledger.py | head -3` at `2417ee6`:
the first line is `ledger.py:21:``author_label`` is ``OD-12``, and since `R-37` it is **the
display name of the reviewer` — as P-01 captured. `git grep -n author_user_uid -- src/auditmanager/decisions`
at the base: no match. The ledger wrote only the display label.

## What this lane delivers

- **Write paths** (`decisions/ledger.py`): `record_decision` and `append_decision_under_key`
  take `author_user_uid: str | None = None`, keyword-only, beside `author_label`, and the
  INSERT writes it. It is written **as given**: a malformed identity fails
  `ck_expert_decision_event_author_user_uid_format` and an unknown one fails
  `fk_expert_decision_event_author_user`, so either is a refused append (the ledger's existing
  `IntegrityError` branch, `conflict`) and neither becomes NULL.
- **Why `None` has a default.** The composition root (`bootstrap/adapters.py`,
  `DecisionAdapter.append_decision`) calls `append_decision_under_key` today with
  `author_label` only, and five test modules outside this lane's paths call
  `record_decision` the same way (`tests/integration/api/conftest.py`,
  `tests/integration/api/test_database_refusals.py`, `tests/integration/exports/test_verdict_columns.py`,
  `tests/integration/p02_journey/test_journey_figures.py`,
  `tests/integration/p02_journey/test_query_surface_over_the_corpus.py`). A required parameter
  would break those calls at run time, and wiring the subject is `W49-SEAL-01`'s. So `None` —
  "author account unknown", the same NULL a pre-`0015` row holds — is the default, documented in
  the module and both docstrings as **accepted only until `W49-SEAL-01` wires the subject**.
  Nothing here invents a value: no configured account, no lookup by label.
- **Idempotency** (`append_decision_under_key`): the account joins the payload fingerprint when
  it is given, so one key presented by two accounts sharing one display name is
  `idempotency_key_reuse`, not a replay that would answer the second account with the first
  one's event. With `None`, the payload is the six keys it always was, byte for byte, so a key
  claimed before this change still replays.
- **Read paths:** `DecisionEvent` (the ledger's domain read model) and `JournalEntry` carry
  `author_user_uid: str | None`, without a default; `decision_history`, the command replay and
  `decision_journal` select it. `None` is listed like any other row — not a fault, not a
  refusal. The journal does not join `app_user`, so history is never dropped by a join.
- **No wire change.** `api/schemas` and `bootstrap/adapters.py` are untouched; the adapter maps
  `DecisionEventView` and `DecisionRecordView` field by field, so the new domain field does not
  reach the wire. The contract suites in the run below are green.
- **Docs:** the ledger module docstring, `JournalEntry`'s docstring and
  `src/auditmanager/decisions/README.md` state the identity/label split and the NULL reading.
- **Tests:** `tests/integration/decisions/test_decision_author_account.py` (new, 25 cases).

## 1. Changed files

`git diff --name-only 2417ee6..HEAD`:

```text
docs/program/W49-DECISIONS-01.md                            (this report)
src/auditmanager/decisions/README.md
src/auditmanager/decisions/journal.py
src/auditmanager/decisions/ledger.py
tests/integration/decisions/test_decision_author_account.py (new)
```

All five lie inside `allowed_paths` (`src/auditmanager/decisions/**`,
`tests/integration/decisions/**`, `docs/program/W49-DECISIONS-01.md`).

## 2. Checks run

Environment: `set -a; . ./.env; set +a` in the lane worktree, foundation up (`make foundation`,
`35 passed`, `foundation sequence complete`), database at `0015_accounts_roles_registration`.

| Command | Tree | Result |
| --- | --- | --- |
| `.venv/bin/python -m pytest tests/integration/decisions -q -p no:cacheprovider` | `2417ee6` (baseline) | `44 passed, 4 subtests passed in 1.38s`, exit 0 |
| same | `542d4e3` code (run on the working tree before the README paragraph was added) | `69 passed, 4 subtests passed in 2.39s`, exit 0 |
| `.venv/bin/python -m pytest tests/integration/api tests/integration/exports tests/integration/p02_journey tests/integration/access tests/integration/db tests/contract/architecture tests/contract/api_v1 -q -p no:cacheprovider` | same | `1109 passed, 1 warning in 657.64s`, exit 0 |
| `git diff --check` | `542d4e3` | clean |
| `make gate` | the final SHA of this branch | **recorded in the hand-back against that SHA** — a gate is tied to the SHA it measured, and recording its lines here would need a commit after it |

The second row's suites cover every caller of the ledger outside `decisions/**` (found with
`git grep -n -E 'record_decision\(|append_decision_under_key\(|decision_journal\(|decision_history\(|DecisionEvent\(|JournalEntry\(' -- src tests tools ':!src/auditmanager/decisions'`,
90 lines in 15 files, read in full rather than through `head`), the ALR-05 boundary test and the
API contract shape tests.

### Mutations

Copy: `make mutation-copy MUT=/root/w49dec-788b07cb-mut` at `542d4e3` (`MUTATION-COPY OK
/root/w49dec-788b07cb-mut/src/auditmanager/__init__.py`). Each case: both source files restored
from the tree, `__pycache__` removed, `PYTHONDONTWRITEBYTECODE=1`, the mutated module's
`__file__` printed and shown under the copy, then
`./.venv/bin/pytest tests/integration/decisions -q -rf --tb=line -o pythonpath=/root/w49dec-788b07cb-mut/src`
from the copy. Unmutated baseline: `69 passed, 4 subtests passed`. After the sweep the copy's
`src/` was diffed against the tree: no difference.

| id | mutation | red (first) | evidence | summary |
| --- | --- | --- | --- | --- |
| M1 | INSERT omits `author_user_uid` | `test_record_decision_writes_the_account[accept]` | `assert None == 'usr_01M4703N…'` | 17 failed, 52 passed |
| M2 | history read maps `author_user_uid=None` | `test_both_read_paths_report_the_stored_account` | `assert None == 'usr_01M4703V…'` | 5 failed, 64 passed |
| M3 | history read raises on a NULL account ("a fault") | `test_the_history_lists_it_beside_a_row_that_has_an_account` | `DomainError: no author account` | 9 failed, 60 passed |
| M4 | history query adds `AND author_user_uid IS NOT NULL` | same | `assert [('dec_01M470…')] == [('dec_01M470…')]` — one pair listed where two were expected | 6 failed, 63 passed |
| M5 | journal adds `JOIN app_user u ON u.user_uid = e.author_user_uid` | `test_the_journal_lists_it` | `the journal dropped an event whose account is unknown` | 1 failed, 68 passed |
| M6 | journal maps `author_user_uid=None` | `test_both_read_paths_report_the_stored_account` | `assert None == 'usr_01M4704E…'` | 1 failed, 68 passed |
| M7 | write coerces `author_user_uid or None` | `test_a_malformed_identity_is_refused_not_nulled[empty]` | `DID NOT RAISE DomainError` | 1 failed, 68 passed |
| M8 | fingerprint omits the account | `test_one_key_two_accounts_one_label_is_a_reused_key` | `DID NOT RAISE DomainError` | 1 failed, 68 passed |
| M9 | fingerprint always carries the account (as `None`) | `test_without_an_account_the_fingerprint_is_the_pre_0015_one` | `assert 'cd0ceac2…' == 'ca001b26…'` | 1 failed, 68 passed |
| M10 | keyed append does not pass the account to `record_decision` | `test_the_keyed_append_writes_the_account[accept]` | `assert None == 'usr_01M47050…'` | 5 failed, 64 passed |
| M11 | `record_decision` returns `author_user_uid=None` while storing it | `test_record_decision_writes_the_account[accept]` | `assert None == 'usr_01M47054…'` | 6 failed, 63 passed |
| M12 | `record_decision` defaults to a configured account | `test_the_account_is_keyword_only_and_defaults_to_no_constant[record_decision]` | ``record_decision defaults `author_user_uid` to 'usr_01ARZ3NDEKTSV4RRFFQ69G5FAV'`` | 22 failed, 47 passed |
| M13 | `JournalEntry.author_user_uid` gets a default `None` | `test_the_read_models_carry_the_account_without_a_default[JournalEntry]` | `assert None is <dataclasses._MISSING_TYPE …>` | 1 failed, 68 passed |

No survivor. M12's other 21 reds are the existing suite's calls hitting the foreign key with
the configured value — the database refusing a constant author, which is the point.

## 3. Contracts

None changed: no file under `contracts/**`, `api/**` or `web/**`. The ledger's **Python**
signature gained `author_user_uid` (the integration contract the task names), and the two
domain read models gained one field each. `DecisionEvent` and `DecisionRecord` on the wire are
unchanged.

## 4. Risks and known limitations

- **Transitional default.** Until `W49-SEAL-01` passes `Subject.user_uid`, every event appended
  through the API stores NULL, indistinguishable from history. Those rows stay NULL for ever:
  the table is append-only, and recovering an account from a label is the display-string
  identity this column exists to stop. The window is the time between this merge and SEAL's.
- **A key claimed without an account and replayed with one** (across the SEAL wiring) has a
  different fingerprint and answers `idempotency_key_reuse` instead of a replay. Only a retry
  that straddles the deployment of SEAL can meet it.
- **A malformed or unknown identity answers `conflict`** ("the ledger refused the appended
  event"), through the ledger's pre-existing `IntegrityError` branch, not `validation_failed`.
  It is reachable only by a caller passing something other than a verified subject's
  `user_uid`; the seam already answers `401` for a credential naming no account.
- **`test_the_ledger_declares_no_default_author`** (`tests/integration/api/test_decision_authorship.py`,
  SEAL's path) guards `author_label` only. When the default is removed it should cover
  `author_user_uid` too.
- **Purge.** Once SEAL wires the subject, every expert who decides anything becomes
  unpurgeable (`RESTRICT`); `R-61` says so and `ACCOUNT_REFERENCES` already lists the column.

## 5. Instructions to the integrator

- `W49-SEAL-01c` passes `author_user_uid=subject.user_uid` from `routers/decisions.py` through
  the `append_decision` port (`routers/ports.py`), `DecisionAdapter.append_decision`
  (`bootstrap/adapters.py`) and the suite's seam adapter (`tests/integration/api/conftest.py`)
  into `append_decision_under_key`.
- After that, the `= None` default should be removed from `record_decision` and
  `append_decision_under_key` (and the five test modules listed above, plus this lane's older `tests/integration/decisions` modules, updated). **That edit is
  in `src/auditmanager/decisions/**`, which `W49-SEAL-01`'s `allowed_paths` do not name** — see
  the open questions.
- `tests/integration/decisions/test_decision_author_account.py` is written to survive that
  removal: it passes `author_user_uid=None` explicitly where it means NULL, and its signature
  test admits "no default" as well as `None`.

## 6. Forbidden hotspots

`git diff --name-only 2417ee6..HEAD` is the list in §1: no `contracts/**`, migration, router,
`bootstrap/**`, `web/**`, lock file, `CURRENT_STATE.md`, `DEBT_REGISTER.md`,
`OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`; no ref pushed, no merge, no tag. The worktree is
`.local/worktrees/w49-dec` as the dispatch named it (the executor prompt's generic form is
`.local/worktrees/<TASK_ID>`).
