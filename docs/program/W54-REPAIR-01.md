# W54-REPAIR-01 — hand-back report

- Task: `docs/program/tasks/W54-REPAIR-01.md`. Grant: `dispatch/W54-PLAN.md` §4 Stage B item 2,
  plus this file.
- Branch `agent/w54-repair-01`, worktree `.local/worktrees/w54-repair`. Base `5826e5f`
  (`integration/w54`: Stage A and CUSTODY merged). Implementation commit `92d17f7`; this report
  is the next commit.
- Checks follow `R-102` (light acceptance). **No container was started, and no provider was
  called.** No proxy key exists on this host. Every database-backed step is listed in §5 for the
  owner's window.

## 1. Changed files

`git diff --name-only 5826e5f..HEAD` lists 28 paths, plus this report:

- **The durable repair journal (new)** — `src/auditmanager/norms/repair_journal/`:
  - `__init__.py`;
  - `model.py`: call states, failure classifiers, the transport port, refusals;
  - `pricing.py`: the rate card and the unknown-outcome bound;
  - `file_journal.py`: the local fsynced file;
  - `repository.py`: `SqlCallStore`, the only writer of `norm_repair_call`;
  - `runner.py`: write order, reconciliation, tries, ceiling, sample, ledger replay.
- **Runner and ledger** — `norms/__main__.py`: `repair plan|sample|full|ledger|status` and
  `ProxyRepairTransport`. `norms/repair.py`: `CALL_FAILED`, `LEDGER_VERSION = "2"`, `unreliable`,
  and the `+<m>u` key. `norms/rerecognition.py`: `judge()` is factored out of `rerecognise()`;
  the rule is unchanged.
- **Export lines** — `norms/__init__.py` (`judge`); `norms/public.py` (`LEDGER_VERSION`,
  `RepairLedger`, `RepairOutcome`, `repaired_snapshot`); `analysis/public.py`
  (`ProxyDispatchError`).
- **Promotion database (new)** — `infra/promotion/compose.yml`;
  `scripts/promotion/{lib,stack,dump,verify-dump,restore}.sh`.
- **Tests:**
  - new `tests/integration/norms/repair/`: `conftest.py`, `support.py`, and the test files
    `test_durable_repair.py`, `test_local_journal.py`, `test_pricing.py`,
    `test_proxy_transport.py` and `test_promotion_scripts.py`;
  - `tests/integration/norms/test_rerecognition.py`: the inverted test, plus key and grammar
    cases;
  - `tests/integration/norms/test_repair_projection.py`: the unapplied-repair projection now
    carries `+0r+1u`;
  - `tests/integration/db/test_norms_corpus_migration.py`: ledger and key cases, and the
    norm-table set (see §4).

### What was built, case by case (plan §3.2, §3.3, §4 Stage B item 2)

| Required case | Where it is proved |
| --- | --- |
| **Write order.** The intent is fsynced to `journal.jsonl`, then the row is committed, then the call is dispatched. The body is written beside the journal and then the row moves to `response_received`, both *before* parsing; the file line follows. The settlement is committed to the database first, then appended to the file. | `test_the_intent_is_on_disk_and_the_row_committed_before_the_dispatch`; `test_the_body_is_checkpointed_before_the_adapter_parses_it` (the W53 parser runs only after the checkpoint) |
| **A kill after acceptance and before the ledger write does not re-pay.** The same holds for a kill at each of the nine durable steps. | `test_a_kill_at_any_durable_step_never_pays_twice[*]`; `test_a_kill_between_the_two_reads_resumes_with_the_second_read_only` |
| **Both reconcile directions.** An intent in the file but not in the database becomes `outcome_unknown` at its bound. A call in the database but not in the file refuses the start with `intent_missing_from_file`. Differing settlements refuse. | `test_an_intent_in_the_file_but_not_in_the_database_becomes_unknown_at_its_bound`; `test_a_call_in_the_database_but_not_in_the_file_refuses_the_start`; `test_a_database_settlement_the_file_disagrees_with_refuses_the_start` |
| **A lost volume reconciled.** The database is restored from the dump taken after page 1, or from no dump at all, and is carried forward from the file with equal charges and ledger and no dispatch. | `test_a_lost_volume_is_carried_forward_from_the_file`; `test_a_lost_volume_without_any_dump_is_rebuilt_from_the_file`; `restore.sh` |
| **`R-79`.** At most three tries, 2 s and 8 s apart. `Retry-After` wins and is capped at 60 s. Only `not_sent` and 429 are retried. There is no fourth try, even after a restart. | `test_a_retry_safe_failure_is_tried_three_times_with_r79_delays`; `test_retry_after_wins_over_the_delay_up_to_sixty_seconds`; `test_a_fourth_try_is_never_made` |
| **503 is ambiguous (`R-85`/D-153).** It ends `outcome_unknown` at its bound and is never retried, including through the real `ProxyRepairTransport`. A 400/401/403/413 is `not_processed`, unpaid, and stops the run. | `test_a_503_is_outcome_unknown_at_its_bound_and_never_retried`; `test_a_503_through_the_real_transport_is_paid_at_most_once`; `test_a_definite_refusal_*` |
| **The cumulative $10 ceiling.** The ceiling is the sum of `charged_usd` over every row in the database. Before each call it is checked against the charge so far plus that call's bound, so an unknown outcome cannot cross it. After each call it is checked again against the actual charge. | `test_the_ceiling_is_cumulative_across_restarts`; `test_the_pre_check_counts_the_bound_so_an_unknown_cannot_cross_the_ceiling`; `test_an_owner_decision_lets_a_stopped_sample_proceed_under_the_hard_ceiling` |
| **The sample stop (`R-95`).** The sample is the three largest crops by area. The run proceeds only if mean × pages × 1.25 ≤ $10. Otherwise it exits 3 with `sample_projects_above_ceiling`, and the verdict is kept in the journal. `full` refuses without a `proceed` verdict or a recorded `--owner-decision R-<n>`. Sampled pages are replayed, not re-paid. | `test_a_sample_under_the_ceiling_proceeds_and_is_not_paid_again`; `test_a_sample_above_the_ceiling_stops_for_the_owner`; `test_the_full_run_needs_a_sample_verdict` |
| **A model mismatch is refused (H-6).** The answer's own `model` is compared with `PROXY_LLM_MODEL` exactly. A mismatched answer is charged, refused (`UNUSABLE`, never applied), and stops the run. An unpriced answer is charged at its bound and stops the run. | `test_an_answer_from_another_model_is_charged_refused_and_stops_the_run`; `test_an_unpriced_answer_is_charged_at_its_bound_and_stops_the_run` |
| **The local fsynced journal (`R-98`).** Every line is fsynced and hash-chained. A torn last line is dropped and truncated; any other damage refuses. There is one writer, enforced by `flock`. A journal under `/var/lib/docker` is refused. Response bytes are never overwritten. | `test_local_journal.py` (12 cases) |
| **The `+<m>u` key and the inverted test.** The key is `<window>+<d>d+<n>r+<m>u.<12 hex>` whenever `m > 0` (with `+0r+<m>u` when `n = 0`). Only an empty ledger returns the base. A repaired-only ledger keeps the W39 digest byte for byte. Every form matches TRANSPORT's ERE, read from `forced-command.sh`. The database CHECK accepts each form and refuses the two contradictions. | `test_a_ledger_that_applied_nothing_moves_the_key_by_its_unreliable_blocks` (inverted); `test_a_ledger_without_unreliable_blocks_keeps_the_w39_key`; `test_every_repaired_key_form_matches_the_transport_grammar`; `test_every_repaired_key_form_is_accepted_with_its_counts`; `test_the_raw_key_check_refuses_a_key_that_disagrees_with_its_counts` |
| **Zero live calls.** An autouse guard replaces `urlopen` and socket connect for the whole repair suite, and one test proves that the guard bites. The legacy flat live form still refuses with `durable_call_journal_required`. | `test_the_suite_cannot_open_a_connection`; `test_live_command_refuses_before_transport_or_ledger_write` (unchanged) |
| **Promotion database (§3.2).** It has its own project and named volume, `mem_limit: 1g`, `shared_buffers=128MB`, and a loopback port with no default. The dump is atomic, carries a SHA-256, and is refused if the fingerprint drifted during the dump. Restore-verify uses a disposable instance with `--network none`, removed by name. One latest verified dump is kept, and the §3.9 floors are enforced before any docker call. | `test_promotion_scripts.py` (17 cases, with `docker`/`df`/`free` stubbed); `shellcheck -x` clean; `docker compose config --quiet` OK |

SEAL's note is honoured. `norm_repair_call` stores only `response_sha256`. The bytes live at
`<journal-dir>/responses/<nrc>.body`, written under a temporary name, fsynced, renamed, and the
directory fsynced.

## 2. Checks run, with commands and results

All of these ran on the committed tree `92d17f7`. `git status --porcelain -uall` was empty.

| Command | Result |
| --- | --- |
| `git diff --check 5826e5f..HEAD` | clean |
| `.venv/bin/python -m compileall -q src/auditmanager/norms src/auditmanager/analysis/public.py tests/integration/norms tests/integration/db/test_norms_corpus_migration.py` | exit 0 |
| `ruff 0.17.0 check --no-cache` over every changed Python file | clean except 3 findings that are identical on the base `5826e5f` (`analysis/public.py` I001/RUF022, `norms/__init__.py` RUF022, `test_norms_corpus_migration.py` SIM117 at the existing test) |
| `shellcheck -x scripts/promotion/*.sh` | clean |
| `docker compose --project-name auditmanager-promotion --file infra/promotion/compose.yml config --quiet` (dummy env; parses only, starts nothing) | OK |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/repair -k "not postgres"` | **99 passed**, 37 deselected (the `postgres` cases) |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms -k "not postgres" --ignore=tests/integration/norms/custody/test_two_phase_custody.py` | **215 passed** |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis_text/test_proxy_adapter.py tests/integration/composition/test_bundle_transport_refusals.py` | **194 passed** (TRANSPORT's real-key case now mints `+3u` and still passes) |
| `.venv/bin/python -m pytest -q -p no:cacheprovider tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py` | **554 passed**, 50 subtests (ALR-05 included: `test_alr05_boundaries.py` 2 passed) |
| Mutation check, each reverted at once (scratch copies, tree restored and byte-compared) | each made the suite red: no body recovery (1 failed); row before intent (2); unknown retried (5); no ceiling pre-check (3); no model check (1); sample margin ignored (2); no `+u` term (6); foreign rows allowed (1); no forward of the file's settlement (2); four tries (1) |

**Not run (heavy, window only):** the 37 `postgres` cases in `tests/integration/norms/repair`
and `tests/integration/db/test_norms_corpus_migration.py` (11 tests, 5 new). Their commands are
in §5. Without `DATABASE_URL` the `postgres` cases **fail** rather than skip.

## 3. Contracts

- **No contract, migration, error code or API change.** `0018`'s `norm_repair_call`,
  `ck_norms_snapshot_raw_key` and `unreliable_count` were sufficient as sealed. Rows are written
  only through `trg_norm_repair_call_guard`'s permitted moves.
- **The repair-ledger format is now `"2"`.** It adds the `call_failed` outcome. Unreliable means
  "not `REPAIRED`". No version-1 ledger was ever written by a paid run, because live mode was
  refused until now. `NORM-LEDGER-01`'s frozen `"1"` is historical.
- **The content key** gains `+<m>u` exactly as TRANSPORT's grammar anticipated
  (`infra/deploy/lib/forced-command.sh:50-60`).
- **Cross-context surface.** `analysis.public.ProxyDispatchError` is now exported. It is
  imported only by `norms/__main__.py`, the composition point. `norms/repair_journal` knows no
  provider.
- **Journal file format** `norm-repair-journal/1`. Each line is
  `{seq, kind, at, body, prev, digest}`. The kinds are `header`, `intent`, `response`,
  `settled`, `sample_verdict` and `owner_decision`. The header binds the journal to one base
  snapshot, one model and the ceiling.
- **Failure classifiers** written to `norm_repair_call.failure`:
  - retry-safe: `not_sent`, `rate_limited`;
  - unpaid, and the run stops: `credential_refused`, `request_refused`;
  - outcome unknown: `proxy_outcome_unknown`, `no_answer_body`, `journal_reconciled`;
  - completed but refused: `model_mismatch`, `unpriced_response`, `unreadable_answer`.

### Readings where the plan was silent (conservative choices)

1. **One row per provider try.** `attempt_number` is the per-block sequence over both
   `R-19`'s two reads and `R-79`'s three tries. The file records `ordinal` and `try_number`.
2. **Three `outcome_unknown` in a row stop the run** (`proxy_unavailable`). Each one is charged
   at its bound, and an unreachable proxy would otherwise spend the ceiling on nothing.
3. **Any definite refusal stops the run.** This covers 400 and 413 as well as 401/403. Plan §7
   lists "the proxy refuses image parts" as a stop. A refusal costs nothing.
4. **The rate card restates `P02_LOCK.json`** (opus-5 $5/$25, sonnet-5 $2/$10), because ALR-05
   forbids reading `analysis.text.lock`. A test pins it to the lock file.
   - The bound is `8000 × output rate + (pixels/750 + 2000) × input rate`. That is $0.2145 on
     opus-5 and $0.0858 on sonnet-5 for an A4 crop at 150 dpi.
   - A vendor-prefixed gateway name such as `anthropic/claude-opus-5` takes the bare model's
     rate. The answer must still name the configured model exactly.
5. **An intent killed before its row was committed** is still charged at its bound, as the plan
   orders. The file cannot prove that the call was not dispatched.
6. **`restore.sh` was added** under `scripts/promotion/**`. The plan restores a lost volume
   "from the latest dump", and that step needed a tool. It refuses a dump that was never
   verified and a database that is not empty.
7. **`repair full --owner-decision R-<n>` records the owner's ruling** in the journal. It
   unlocks a stopped sample (K-8) while the $10 ceiling stays the hard stop. Without it, `full`
   refuses.

## 4. Risks and known limitations

- **`W54-SNAPSHOT-01` must write `unreliable_count` and `text_reliability`.**
  `corpus_source.py`, `repository.py` and `loader.py` are outside this grant, and today they
  write only `repair_count`.
  - **Consequence:** loading a ledger that has unreliable blocks either breaks
    `ck_norms_snapshot_raw_key` (when `n = 0`) or stores `unreliable_count = 0`.
  - **What SNAPSHOT needs:** `ledger.unreliable_count` gives the number. The blocks to mark are
    those in `ledger.unreliable`, by `(document_slug, block_id)`.
  - **When it matters:** operator step (3), loading the repaired snapshot, needs SNAPSHOT
    merged first. The paid run itself (step 2) does not.
- **No database ran.** The SQL store is exercised only by the 37 `postgres` cases (window).
- **The gateway's model name is unverified.** The first answer whose `model` differs from
  `PROXY_LLM_MODEL` is charged (≈ $0.2 at most) and stops the run. The sample is where this
  shows. Setting `PROXY_LLM_MODEL` to the exact name the gateway reports is the operator's job.
- **`tests/integration/db/test_norms_corpus_migration.py`'s norm-table set** had not been
  updated for `0018` (three new `norm%` tables). It would have been red at head. It is updated
  here, inside this lane's grant for that file.
- **One writer is enforced by `flock` on the journal directory.** Two journals over one
  database refuse each other only once rows exist. The operator runs one runner.
- **The promotion port is not registered.** `PORT_REGISTRY.md` is the integrator's. The
  compose file has no default port.
- `ProxyPageRecogniser` (unjournaled) is kept for the `rerecognise` seam. The paid path never
  uses it.

## 5. Integrator instructions

1. Read the diff and this report. Merge after CUSTODY, before SNAPSHOT (plan §5). The shared
   paths are only the export lines of `norms/{public,__init__}.py` and
   `test_norms_corpus_migration.py`, which SNAPSHOT edits next.
2. **Heavy step, owner window only.** Measure first: `free` ≥ 6 GiB available and `df` ≥
   increment + 3 GiB. Bring up the lane stack on PostgreSQL `57140` and S3 `60740/60741` with a
   lane `.env`. Then, from the worktree:

   ```sh
   set -a; . ./.env; set +a
   .venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/repair -k postgres
   .venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/db/test_norms_corpus_migration.py
   .venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/repair tests/integration/norms/test_rerecognition.py tests/integration/norms/test_repair_projection.py
   ```

   Expected: 37 + 11 passed, and the full repair directory 136 passed. Stop the lane stack by its
   own compose project; kill nothing by pattern.
3. **Register a promotion port** in `PORT_REGISTRY.md`. Then write
   `.local/promotion/promotion.env` with `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
   (16–128 characters of `[A-Za-z0-9_-]`) and `PROMOTION_POSTGRES_PORT`.

### The paid run (`W54-CORPUS-OPERATE-01`, step 2), exact operator sequence

Steps 0 and 1 come first:
- step 0: `SHA256SUMS` over the drop under `.local/norms/corpus-sums/<date>/`;
- step 1: the base snapshot loaded, dumped and restore-verified.

Run the following from the checkout root, in a window, under §3.9's floors. The proxy credential
is sourced from its file outside the repository into this shell only, never echoed.

```sh
set -a; . <proxy credential file>; set +a    # PROXY_LLM_BASE_URL, PROXY_LLM_TOKEN, PROXY_LLM_MODEL
CORPUS=.local/norms/corpus
SUMS=.local/norms/corpus-sums/<date>/SHA256SUMS
REPAIR="env PYTHONPATH=src .venv/bin/python -m auditmanager.norms repair"

# a. Offline: no call, no database. Expect "pages": 121; note "base_snapshot".
PYTHONPATH=src .venv/bin/python -m auditmanager.norms repair plan --corpus "$CORPUS" --model "$PROXY_LLM_MODEL"
KEY='<base_snapshot printed above>'

# b. Start and migrate the promotion database.
free -b; df -B1 /
scripts/promotion/stack.sh up
scripts/promotion/stack.sh migrate

# c. The priced sample (R-95): the three largest crops, live.
scripts/promotion/stack.sh run -- $REPAIR sample --corpus "$CORPUS" --sums "$SUMS" \
    --journal-dir .local/norms/repairs --base-snapshot "$KEY"
#    exit 0, verdict.decision "proceed"            -> continue to d
#    exit 3, "sample_projects_above_ceiling"       -> STOP: poll the owner (K-8). If approved, d
#                                                     with --owner-decision R-<n>
#    exit 3 with any other reason, or exit 2       -> STOP and report (credential, model
#                                                     mismatch, unpriced, proxy unavailable)

# d. The stop check, then the full run (the sample's pages are replayed, not re-paid).
scripts/promotion/stack.sh run -- $REPAIR status --journal-dir .local/norms/repairs
scripts/promotion/stack.sh run -- $REPAIR full --corpus "$CORPUS" --sums "$SUMS" \
    --journal-dir .local/norms/repairs --base-snapshot "$KEY"
#    exit 0 -> .local/norms/repairs/ledger.json written
#    exit 3 "ceiling_reached" -> the pages it left are NOT_ATTEMPTED (unreliable); ledger written
#    a crash or kill at any point: rerun the same command (it reconciles and pays nothing twice)

# e. Export, dump, verify, stop.
mkdir -p .local/norms/repairs/<date>
cp -a .local/norms/repairs/journal.jsonl .local/norms/repairs/ledger.json \
      .local/norms/repairs/responses .local/norms/repairs/<date>/
scripts/promotion/stack.sh run -- $REPAIR status --journal-dir .local/norms/repairs \
    > .local/norms/repairs/<date>/status.json
scripts/promotion/dump.sh
scripts/promotion/verify-dump.sh
scripts/promotion/stack.sh stop
```

**If the volume is lost**, restore and let the next start reconcile:
1. `scripts/promotion/stack.sh up` on a fresh volume;
2. `scripts/promotion/stack.sh migrate` is not needed, because the dump carries the schema;
3. `scripts/promotion/restore.sh`;
4. rerun the same `sample` or `full` command. Its reconciliation carries the journal forward.

## 6. Containment

- `git diff --name-only 5826e5f..HEAD` lists the 28 paths of §1 plus this report. All of them
  are inside the grant:
  - `norms/{__main__,rerecognition,repair}.py`;
  - the export lines of `norms/{public,__init__}.py`;
  - `norms/repair_journal/**`;
  - the `ProxyDispatchError` line of `analysis/public.py`;
  - `infra/promotion/**` and `scripts/promotion/**`;
  - `tests/integration/norms/{test_rerecognition,test_repair_projection}.py`;
  - `tests/integration/norms/repair/**`;
  - `tests/integration/db/test_norms_corpus_migration.py`;
  - this file.
- **Not touched:**
  - contracts and migrations;
  - `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md` and `PORT_REGISTRY.md`;
  - root dependency and lock files;
  - refs and tags;
  - the stand, `.local/norms/**` (read only, and only for the corpus layout) and other
    worktrees.
- No container was started (only `docker compose config`, which parses). There was no provider
  call, no push, no merge and no tag. `git status --porcelain -uall` is empty after this commit.
