# W55A-PIN-01 — hand-back report

- Task: `docs/program/tasks/W55A-PIN-01.md`. Grant: `dispatch/W55-PLAN.md` §A4 Stage B
  item 3, plus `tests/integration/api/test_query_surface.py` and this file. Design: §A3.3;
  rulings R-82, R-113; CD-6.
- Branch `agent/w55a-pin-01`, worktree `.local/worktrees/w55a-pin`. Base `08259ba` (local
  `integration/w54`: W54 plus the W55a SEAL, CONTENT, SEARCH and WEB-NORMS merges; head
  `0020_norms_search`).
- Commits: `fe414c7` (implementation and tests). This report is the last commit.
- Checks follow `R-102`/`R-111`: light and container-free. **No container was started and no
  database was reached.** The database-backed cases are written; the window commands are in §5.

## 0. What was built

| Plan item (§A3.3, §A4 item 3) | Where |
| --- | --- |
| `startRun` and `reauditRun` read the current snapshot through `norms.public.current_snapshot(session)` **inside the run-creating transaction** and write `audit_run.norms_snapshot_id`; NULL while none is current. | `runs/commands.py`: `current_norms_snapshot`, the default `norms_snapshot` reader of `start_audit_run` and `reaudit_run`. The read happens after the command ledger accepts the key, so a replay reads nothing and pins nothing new. |
| PIN replaces W53's carry-over of the source's snapshot. | `reaudit_run` pins the current snapshot, never `source.norms_snapshot_id`. |
| `input_basis_digest` is today's computation and never holds the snapshot. | `input_basis_digest(...)`: the pre-W55 canonical document, byte for byte. |
| The stored `frozen_input_digest` is the basis plus the snapshot when not NULL. | `frozen_input_digest(..., norms_snapshot_id)`: the same canonical document with `norms_snapshot_id` added only when a snapshot is pinned. A NULL run's digest is byte-identical to its basis. The argument has no default, so a caller cannot silently store a digest that claims no pin. |
| `start_run_fingerprint` takes the basis only. Both fingerprints are unchanged. | The parameter is now `input_basis_digest_value`. It is still hashed under the key `frozen_input_digest`, so a pre-W55 `command_record` matches. The re-audit fingerprint is still the source run and the source's stored digest. |
| `RunStatus` gains an optional `norms_snapshot_id`. | `bootstrap/adapters.py` `_run_status_view` fills `RunStatusView.norms_snapshot_id` from the row. SEAL's `run_status_body` renders it only when it is present. |
| The `OD-24` scope note. | `runs/scope.py`: the NormsSnapshot clause now says that runs pin the current snapshot, and that a NULL pin is admitted until W57. |
| The query-surface guard (task grant). | `test_query_surface.py`: `SEALED_STUB_QUERY_OPERATIONS` is emptied. `searchNorms`, `listNormParagraphs`, `listNormSnapshots` and `listNormSnapshotEvents` are driven like every other listing, over the shipped `NormsSearchAdapter`. Every parameter must change the answer: `limit`, `cursor`, `q` (another query gives another answer) and `norms_snapshot_id` (a once-current snapshot moves the scope). |

`bootstrap/composition.py` needed no change. The reader is the commands' own default, so
every caller pins, including scripts and tests that call the commands directly. Wiring it in
composition would have added a second place where that rule could be forgotten.

## 1. Changed files

`git diff --name-only 08259ba..HEAD`:

```
docs/program/W55A-PIN-01.md
src/auditmanager/bootstrap/adapters.py
src/auditmanager/runs/__init__.py
src/auditmanager/runs/commands.py
src/auditmanager/runs/repository.py
src/auditmanager/runs/scope.py
tests/integration/api/test_query_surface.py
tests/integration/runs/test_full_chain.py
tests/integration/runs/test_idempotency_and_topology.py
tests/integration/runs/test_w53_execution.py
tests/integration/runs/test_w53c_exec_closure.py
tests/integration/runs/test_w55a_pin_offline.py   (new)
tests/integration/runs/test_w55a_pin_window.py    (new)
```

The `adapters.py` changes are limited to these:

- `_run_status_view` gains one field;
- two comments: `RunAdapter.start_run` and `ExecutionAdapter.reaudit_run`.

`repository.py` changes only the `create` docstring.

Existing tests changed:

| Test | Change |
| --- | --- |
| `test_w53_execution.py` | The carry-over test becomes `test_reaudit_pins_the_current_snapshot_not_the_sources_and_replays_once`. |
| `test_w53c_exec_closure.py` | Passes the child's pin to `frozen_input_digest`. |
| `test_idempotency_and_topology.py` | Uses `input_basis_digest` / `input_basis_digest_value`. |
| `test_full_chain.py` | Asserts that the pin equals the current snapshot, not that it is "always NULL". |

## 2. Checks run

All of these ran in the worktree. The contract battery ran on the committed tree at `fe414c7`.

| Command | Result |
| --- | --- |
| `git diff --check 08259ba..HEAD` | clean |
| `.venv/bin/python -m compileall -q src/auditmanager/runs src/auditmanager/bootstrap tests/integration/runs tests/integration/api/test_query_surface.py` | exit 0 |
| `.venv/bin/python -m pytest -q tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py` | **619 passed**, 50 subtests (same count as SEARCH's report). `test_alpha_acceptance_command.py` refuses a dirty checkout, so this has to run on a committed tree. |
| `pytest -q tests/integration/runs/test_w55a_pin_offline.py` | **18 passed** |
| `pytest -q` over SEARCH's three offline norms modules and `tests/integration/api/test_streaming_wire_response.py`, together with the module above | 91 passed |
| `pytest -q tests/integration/composition/test_every_port_implementation_is_whole.py` | 18 passed (2 min 20 s) |
| `env -u DATABASE_URL pytest --co tests/integration/runs tests/integration/api/test_query_surface.py` | 196 collected, 0 errors |

**Each new behaviour fails without its change.** Ten mutations were applied one at a time
by a scratch script, each restored afterwards, with the tree verified clean. All ten turned
`test_w55a_pin_offline.py` **red**:

- the re-audit carries the source's snapshot;
- start pins nothing;
- start's digest ignores the pin;
- the fingerprint takes the stored digest;
- a NULL pin writes a `null` key;
- start reads the snapshot before the claim;
- the re-audit reads the snapshot before the claim;
- `_run_status_view` drops the pin;
- the fingerprint key is renamed;
- the scope note is reverted.

The offline module pins three literals that were captured on the base `08259ba` before any
change:

- the pre-W55 digest;
- the pre-W55 fingerprint;
- the pinned digest, which is also re-derived independently in the test.

**Not run.** These need PostgreSQL and S3 (§5):

- the reader's SQL against `0020`;
- `fk_audit_run_norms_snapshot`;
- replays across real `command_record` rows;
- the shipped `RunAdapter.start_run` → `RunStatus`;
- the norms query drive.

## 3. Contracts

None changed: no `contracts/**`, no migration (head `0020_norms_search`), no OpenAPI, no
error catalog, no surface count. `RunStatus.norms_snapshot_id` was sealed by
`W55A-SEAL-01`; this lane only fills it.

The in-process interfaces did change (`runs/commands.py`, re-exported from `auditmanager.runs`):

- new: `input_basis_digest(...)`, `current_norms_snapshot(session)` and `NormsSnapshotReader`;
- `frozen_input_digest(...)` takes the keyword `norms_snapshot_id`, which is required;
- `start_run_fingerprint(...)` renamed `frozen_input_digest_value` to `input_basis_digest_value`.
  The value is the same and the hashed key is the same;
- `start_audit_run` and `reaudit_run` take an optional `norms_snapshot` reader, which defaults
  to `current_norms_snapshot`.

The production callers are the two adapters, and they are unchanged.

## 4. Risks and known limitations

1. **No SQL has been executed.** The new SQL is test seeding only: the snapshot, the
   documents, the paragraphs and the designation rows. It mirrors the columns and
   constraints of `0012`, `0018` and `0020`, and SEAL's migration test, column for column.
2. **"None current" cannot be arranged in a test.** `0020` has no unset. Two window tests
   need a lane database where nothing has committed a designation, and they fail loudly
   otherwise:
   - `test_a_new_run_with_none_current_pins_null_and_stores_its_basis`;
   - `test_a_reaudit_with_none_current_pins_null_whatever_the_source_pinned`.

   Every other test designates inside its own rolled-back transaction.
3. **Designation in tests is plain SQL, not `set_current_snapshot`.** The setter requires a
   complete BGE build and confirmed custody bindings. The test rows satisfy `0020`'s guard
   exactly as the setter writes them. SEARCH's window suite proves the setter itself.
4. **The reader takes no lock (SEARCH's design).** A designation committed concurrently with
   a start is either seen or not, and the run pins whichever snapshot was current when the
   statement ran. The FK holds either way.
5. **The query-surface search runs with `timeout_ms=600000`.** The search's `SET LOCAL
   statement_timeout` outlives its savepoint inside that suite's single outer transaction.
6. **Stale prose outside the grant.**
   - `docs/program/P02_SEAMS.md` §9.2 still says "PC-01 pins no norms snapshot".
   - The `CONTRACT_PIN_REGISTRY.md` row and the SEAL report mention `SEALED_STUB_QUERY_OPERATIONS`.
     That set still exists and is now empty.

   This is for the integrator or QA.

## 5. Integrator instructions

1. Read the diff and this report, then merge `agent/w55a-pin-01`. This closes Stage B's hold
   on `bootstrap/{adapters,composition}.py`.
2. **Window (D-157).** Use this lane's stack: PostgreSQL `57240`, S3 `60840/60841`, a lane
   `.env` naming them, and a **freshly migrated** database at `0020_norms_search`. Run from
   the worktree, one pytest at a time:

   ```sh
   set -a; . ./.env; set +a
   .venv/bin/python -m pytest -q tests/integration/runs/test_w55a_pin_window.py
   .venv/bin/python -m pytest -q tests/integration/runs
   .venv/bin/python -m pytest -q tests/integration/api/test_query_surface.py
   .venv/bin/python -m pytest -q tests/integration/qa_w53 \
       tests/integration/composition/test_the_run_leaves_the_request_thread.py
   ```

   Expected: everything green.
   - The first command covers the seven §A4 item 3 cases.
   - The second covers the changed W53 re-audit tests and the full chain.
   - The third covers the four norms query operations.
   - The fourth covers the other `startRun`/`reauditRun` callers.

   Every test writes inside a rolled-back transaction.
3. Stop the lane stack by its own compose project. Kill nothing by pattern.

## 6. Containment

`git diff --name-only 08259ba..HEAD` is the 13 paths in §1. Each one is inside the grant:

- `runs/{commands,repository,scope,__init__}.py`;
- `bootstrap/adapters.py` (run status and comments);
- `tests/integration/runs/**`;
- `tests/integration/api/test_query_surface.py`;
- this report.

Not touched:

- `contracts/**`, migrations, `api/**`, `bootstrap/composition.py`, `bootstrap/settings.py`;
- `norms/**`;
- `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, `CURRENT_STATE.md`;
- root dependency and lock files, `.venv`, `web/**`;
- refs, tags, the stand, other worktrees.

No container, push, merge, tag or stash. No process was killed. `git status --porcelain -uall`
is empty after this commit.
