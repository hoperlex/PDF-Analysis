# W54-FIX-SHELL — lane report

**Task:** `docs/program/tasks/W54-FIX-SHELL.md`. **Findings:** `docs/program/reviews/W54-JUDGE-A.md`
F1, F3, F4, F6. **Base:** `92569d5` on `integration/w54`. **Branch:** `agent/w54-fix-shell`.
**Executor:** a subagent of the integrator, 2026-10-12. Container-free throughout: no docker
daemon, SSH, network or stand was used.

## 0. The four findings

| Finding | Fix | Case that proves it |
|---|---|---|
| F1 — `deploy.sh`'s stand guards pass silently when the deploy account cannot search the 0700 copy or staging directory | new guard `stand-dirs-searchable`, typed word `stand_dir_unsearchable`. It runs first among the stand guards and before any `docker` call. For the record's directory and the import lock's directory, if it exists and `( cd -- <dir> )` fails, `deploy.sh` refuses. The kernel is asked rather than the mode bits, so the answer is the one `-e` would get | `TestNoDeployWhileACopyOrAnImportIsOpen::…[stand-dirs-searchable]` (refusal, before docker); its guard-deletion mutant, which also shows the silent pass (the open unattested record is no longer seen); `test_an_unsearchable_staging_directory_is_refused_too` (held lock inside); control `test_a_searchable_directory_without_read_access_is_not_refused` (mode `0111`: search is enough) |
| F3 — `resume` checks `import.lock` without holding it; `import` takes it after the record check | `copy-serve.sh`: `require_import_lock_free` becomes `hold_import_lock`, which takes `flock -n` on the same `<BUNDLE_STAGING>/import.lock` with `fc_take_lock` and keeps it until the verb exits. `resume` therefore holds it through `compose start` and the record's close. `dump-db`, both `attest` forms and `restore-db` hold it too, because they called the same check. `receive-bundle.sh import`: `take_import_lock` now comes before `require_record_admits_import` | `test_no_import_starts_while_resume_starts_the_writers[as-shipped]`: resume is paused inside `compose start`, and the real `receive-bundle.sh import` is refused `import-lock-free`; no importer runs. `test_resume_is_refused_while_the_importer_runs_and_succeeds_after`: the real detached importer runs, resume is refused, and it succeeds after the importer exits. `test_import_takes_the_import_lock_before_it_reads_the_record` (bundle suite) |
| F4 — `record.json` rewritten under two different locks | `lib/forced-command.sh`: `fc_take_lock`, `fc_drop_lock`, `fc_take_record_lock`, `fc_drop_record_lock`, `fc_record_locked` and `fc_record_install`. Every rename onto the record (`fc_record_set`, `copy-serve.sh`'s `render_record`, the `record.prev.json` moves) goes through `fc_record_install`, which fails unless this process holds `copy.lock` beside that record. `copy-serve.sh`'s `take_copy_lock` (guard `copy-lock-free`) now uses `fc_take_record_lock`. `receive-bundle.sh` takes the lock in a new guard `copy-lock-free`: `receive` takes it before a byte is read and holds it to the end; `import` holds it from the record check through the conversion and drops it before `setsid`, so the importer does not inherit it. A rewrite that fails is refused (`copy-record-readable`), never a silent `set -e` exit | `test_the_record_is_rewritten_only_under_the_copy_lock_beside_it` (no lock, another directory's lock, a lock held elsewhere: refused and unchanged); bundle suite `copy-lock-free` guard case and its mutant; `test_a_receive_under_a_running_copy_verb_is_refused_before_reading` (0 bytes consumed); `test_an_import_converts_the_record_under_the_copy_lock_and_lets_it_go`; the `receive` half of the F3 race case |
| F6 — a failed `dump-db` overwrites the previous closed record | `keep_previous_record`, called by `open_record` for both `dump-db` and `attest --test-data`. A closed copy whose dump is on disk becomes `record.prev.json`. Any other record (a waiver, a copy whose dump failed) is replaced, and an earlier `record.prev.json` is kept. A completed `dump-db` removes `record.prev.json` before it removes the older copy directories. `restore-db <STAMP>` accepts the previous record's stamp: it checks that record's dump and digest exactly as for the latest, then puts it back as `record.json`. The writers the replaced open record had stopped are carried into `writers_stopped`. `status` prints `previous_record:` | `test_a_failed_dump_keeps_the_previous_copy_restorable` (prev kept; wrong stamp and wrong digest refused without moving anything; restore of the prev stamp; resume); `test_a_waiver_replaces_the_record_and_keeps_the_previous_copy`; `test_only_the_latest_copy_is_kept` (no prev after a whole dump; the old stamp is refused) |

**Lock order.** `copy-serve.sh` takes `copy.lock` and then `import.lock`. `receive-bundle.sh import`
takes `import.lock` and then `copy.lock`. Both are non-blocking, so crossing orders produce a
refusal in words and never a deadlock. The F3 mutant case shows the two locks are independent
defences. Without `resume`'s hold, an import arriving during `resume` is still refused, by
`copy-lock-free`, and no importer starts.

## 1. Changed files

```
docs/program/DEPLOYMENT_RUNBOOK.md                       §11 only
docs/program/W54-FIX-SHELL.md                            this report
infra/deploy/copy-serve.sh
infra/deploy/deploy.sh
infra/deploy/lib/forced-command.sh
infra/deploy/receive-bundle.sh
tests/integration/composition/test_bundle_transport_refusals.py
tests/integration/composition/test_deploy_script_refusals.py
tests/integration/composition/test_stand_copy_refusals.py
```

## 2. Checks and results (this worktree, at the code commit)

| Command | Result |
|---|---|
| `git diff --check 92569d5..HEAD` | clean |
| `bash -n` on the four scripts | clean |
| `shellcheck -x infra/deploy/copy-serve.sh infra/deploy/receive-bundle.sh infra/deploy/lib/forced-command.sh` | exit 0 |
| `shellcheck -x infra/deploy/deploy.sh` | exit 1 on one **pre-existing** `SC2016` *info* (the `docker image prune` printf, base line 745, now line 762). Byte-identical at `92569d5`, not touched here. `-S warning` exits 0 |
| `.venv/bin/python -m pytest -q tests/integration/composition/test_deploy_script_refusals.py tests/integration/composition/test_stand_copy_refusals.py tests/integration/composition/test_bundle_transport_refusals.py` | **345 passed, 1 skipped** in 140 s (base `92569d5`: 331 passed, 1 skipped). The skip is the pre-existing heavy `test_a_dump_restored_here_reproduces_the_fingerprint` (`W54_STAND_COPY_WINDOW=1`) |
| neighbours that read these scripts: `tests/integration/norms/bundle/{test_copy_record,test_discard_after_report,test_layout}.py`, `tests/integration/composition/{test_deploy_image_identity,test_session_register_volume}.py`, `tests/contract/test_deploy_auto_workflow.py`, `tests/contract/api_v1/test_surface_counts_in_prose.py` | 114 passed |

**Each new guard is shown able to fail.** The suites' block-deletion mutants run for
`deploy.sh` `stand-dirs-searchable` and `receive-bundle.sh` `copy-lock-free`. Both are in the
345, and the suites' marker-coverage tests require a case for each.

**Each non-guard fix is shown able to fail.** Each mutation below was applied to the committed
tree, the named case was run, and the file was restored with `git checkout --` (the script was
kept in the session scratchpad, outside the tree). Every mutant was killed:

| Mutation | Case | Result |
|---|---|---|
| `hold_import_lock` back to the check-only `fc_lock_held` (F3) | `test_no_import_starts_while_resume_starts_the_writers` | 1 failed (`as-shipped`), 1 passed (`without-the-hold`, as designed) |
| `import` locks after `require_record_admits_import` (F3) | `test_import_takes_the_import_lock_before_it_reads_the_record` | failed |
| `fc_record_install` without its lock check (F4) | `test_the_record_is_rewritten_only_under_the_copy_lock_beside_it` | failed |
| `receive` without `take_record_lock` (F4) | `test_a_receive_under_a_running_copy_verb_is_refused_before_reading` | failed |
| `import` without `fc_drop_record_lock` (F4) | `test_an_import_converts_the_record_under_the_copy_lock_and_lets_it_go` | failed |
| `open_record` without `keep_previous_record` (F6) | the two F6 cases | 2 failed |
| `restore-db` without the previous-record branch (F6) | `test_a_failed_dump_keeps_the_previous_copy_restorable` | failed |
| a whole `dump-db` keeps `record.prev.json` (F6) | `test_only_the_latest_copy_is_kept` | failed |

The F1 case runs as root on this host. The permission bits apply to it because `setpriv
--bounding-set=-dac_override,-dac_read_search` drops those two capabilities, so a mode-000
directory is unsearchable to it as it is to any other account. As a non-root user it runs
without the prefix. If `setpriv` is missing under root, the case fails; it is never skipped.

## 3. Contracts (new or changed; no API, domain, event or migration contract)

* **`deploy.sh` typed word** `stand_dir_unsearchable` (guard `stand-dirs-searchable`). The guard
  count goes from 20 to 21.
* **`receive-bundle.sh` guard** `copy-lock-free` (exit 3). Order of `import`: staging, bundle,
  stack, record present, layout, **import lock**, **copy lock**, record admission, conversion,
  copy lock dropped, detached importer. `receive` takes the copy lock before a byte is read.
* **`copy-serve.sh`.** `import-lock-free` now *holds* the lock for the verb's run, in `dump-db`,
  `attest` (both forms), `restore-db` and `resume`. `restore-db` accepts the previous record's
  stamp. `status` prints `previous_record: <STAMP>` while one is kept.
* **Copy directory layout.** `record.prev.json` sits in the canonical record layout beside
  `record.json` while a new copy is incomplete. The importer never reads it, because only
  `record.json` is mounted.
* **`lib/forced-command.sh`.** Every rewrite of a record requires `copy.lock` beside it. New
  helpers are listed in §0. `fc_record_set` keeps its signature and fails without the lock.

## 4. Risks and known limitations

* **F1 may now refuse every deploy on the stand.** It will if deploy-auto's `VPS_USER` is not
  the keys' account and the directories stay `0700` (JUDGE-A "not verifiable statically" item 2).
  That refusal is the intended fail-closed outcome, and runbook §11 now says how to grant
  search (same account, or a group and mode `710`). The owner must settle it before the first
  deploy that follows this change; it cannot be decided from here.
* Only the **immediate** parent is checked. If `/srv` itself is unsearchable, `-e` on the
  directory is false and the guard sees no directory. That configuration would also break
  the keys and is not a plausible stand state.
* `receive` holds `copy.lock` for the whole transfer, so copy-key verbs refuse
  `copy-lock-free` during a receive. The P4 order runs no copy verb during a transfer.
* `copy-serve.sh`'s `hold_import_lock` treats an *absent* staging directory as "no inbound key
  installed, no lock" (`receive-bundle.sh` refuses every verb without one). A staging
  directory whose lock this account cannot open is refused.
* `record.prev.json` keeps only one previous copy. A waiver never becomes a previous record,
  because it has no dump. A failed dump never becomes one either. `fetch`, `inventory-s3`
  and `attest` still take only the latest stamp.
* **Doc drift, recorded and not edited here.** The STAND-COPY report
  (`docs/program/W54-STAND-COPY-01.md`) §4 says the delete step (importer step 5) is "proposal,
  not implemented". That is **superseded**: `W54-BUNDLE-01` implemented it inside
  `receive-bundle.sh`'s `verb_report`. After a `report` that exits 0 following an `import`
  that exited 0, it removes `bundles/<KEY>/objects/` under the import lock and writes
  `logs/<KEY>.report` and `logs/<KEY>.discarded`, as runbook §11 already describes. No
  separate `discard` verb exists or is needed. Other lane reports are not edited by this lane.
* §3.2 and §3.6 of the STAND-COPY report do not mention `record.prev.json`,
  `stand_dir_unsearchable` or the held locks. This report and the script headers are the
  current description.

## 5. Instructions for the integrator

1. Read the diff (`git diff 92569d5..agent/w54-fix-shell`) and this report, then merge. No
   contract, migration, lockfile or composition root is touched.
2. Light acceptance: the three suites above (about 2.5 minutes), `bash -n`, and `shellcheck -x`
   on the three scripts. `deploy.sh`'s single `SC2016` info is pre-existing.
3. **Window step (DB- and S3-backed; not run here).** Nothing in this lane adds a heavy case.
   The existing window commands stay as their owners list them:
   `W54_STAND_COPY_WINDOW=1 .venv/bin/python -m pytest -q tests/integration/composition/test_stand_copy_refusals.py::test_a_dump_restored_here_reproduces_the_fingerprint`
   and BUNDLE's postgres-backed `tests/integration/norms/bundle/` cases. The rehearsal
   (`W54-REHEARSAL-01`) should exercise `restore-db <previous stamp>` after a deliberately failed
   `dump-db`, and `resume` racing `import`, on the real stand tools.
4. **Owner decision before the next stand deploy:** whether deploy-auto's account searches
   `/srv/auditmanager-copy` and `/srv/auditmanager-bundles` (runbook §11, step 1). Without
   that, deploys refuse `stand_dir_unsearchable`.
5. Rollback: revert the lane's commits. No state migration; a `record.prev.json` left on a stand
   is ignored by the old scripts.

## 6. Containment

* `git diff --name-only 92569d5..HEAD` lists exactly the nine paths in §1. Each is inside the
  grant: `infra/deploy/{deploy,copy-serve,receive-bundle}.sh`, `infra/deploy/lib/forced-command.sh`,
  the three suites, `DEPLOYMENT_RUNBOOK.md` (only §11 hunks: install step 1, the `receive` and
  `import` rows, the refusal table, "What it does not do") and this report.
* Forbidden hotspots untouched: no `contracts/**`, migration, `DEBT_REGISTER.md`,
  `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, `CURRENT_STATE.md`, lockfile, other lane reports,
  `.local/norms/corpus/**`, ref or tag. No push, merge, tag, stash or worktree was created; no
  container, SSH or network.
* `git status --porcelain -uall` is empty after the report commit.
