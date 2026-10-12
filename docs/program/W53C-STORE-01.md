# W53C-STORE-01 — artifact rejection, release read tolerance, rehearsal target guards

Branch `agent/w53c-store`, base `04de50c` (`W53-CLOSE-PLAN` on `integration/w53-close`).
Code commit `40b58ae`; this report is the commit after it. Findings C-12, C-13 and C-14
of `docs/program/dispatch/W53-CLOSE-PLAN.md` §2 all reproduced at base and are closed.

## 1. Changed files

- `src/auditmanager/ingest/reconciliation.py` — C-12. `UnboundAnalysisArtifact.rejection_eligible`
  is always `False`. `Reconciler.reject_unpublished(blob_id)` keeps the available-blob refusal
  (`machine=blob`) and the `legacy_unattributed` refusal, and refuses every blob an
  `analysis_artifact_publication` row names with `machine=analysis_artifact_publication`,
  `current_state=content_addressed_rerun_self_heals`. It changes no row on any branch. The W48
  eligibility ladder (`attempt_not_terminal`, `publication_not_stale`, object presence), its
  `FOR UPDATE` authority query, `_ATTEMPT_TERMINALS` and the now meaningless `older_than`
  argument are removed. There is no production caller.
- `src/auditmanager/releases/notes.py` — C-13. New `servable_content(content)` returns
  `(range_label, items)` or `None`, using the same item fields (`_ITEM_FIELDS`) and kinds
  (`_KINDS`) that `parse_note` accepts. `parse_note` now reads `_ITEM_FIELDS` too.
- `src/auditmanager/releases/repository.py` — C-13. `list_for_account` reads every revision,
  newest first per release, and serves the newest one `servable_content` accepts. It logs a
  warning for each skipped revision and leaves out a release with no servable revision. It never
  raises on content. `first_loaded` (what's-new) is still the minimum `loaded_at` over all
  revisions.
- `scripts/rehearsal/w53/process_recovery.py` — C-14. `require_disposable_database(raw_url)`
  refuses with `SystemExit` unless `DATABASE_URL` parses, names a loopback host
  (`127.0.0.1`/`localhost`/`::1`) and a database whose name starts with `w53_rehearsal`. It never
  echoes the URL. `_engine()` calls it before it creates the engine, and `parent()` calls it
  before it spawns. Every `assert` is now `require(...)` (explicit `SystemExit`) or an explicit
  `if … raise`.
- `scripts/rehearsal/w53/minio_upgrade.py` — C-14. The four preflight checks (old image, new
  image, existing container, clashing volumes) are explicit `if …: raise SystemExit(...)` with
  messages. The other verification asserts are `require(...)`, which `-O` cannot strip.
- `tests/integration/runs/test_durable_effect_boundaries.py` — the test that pinned C-12 as
  correct is replaced by
  `test_a_stale_terminal_analysis_publication_is_refused_and_a_rerun_publishes_it`. The F-8
  pair is now `test_a_live_attempts_blob_is_refused_as_content_addressed` and
  `test_a_terminal_publication_is_refused_however_old_it_is`. The process-loss test asserts the
  new reason. `_interrupted_publication` also returns `seeded`. A pre-existing unused import
  (`reconcile_interrupted_runs`, F401) is removed.
- `tests/integration/ingest/test_reconciliation.py` — the legacy refusal drops `older_than` and
  asserts `legacy_unattributed`.
- `tests/integration/releases/test_release_loader.py` — two new tests. The first,
  `test_a_newer_images_revision_falls_back_to_the_newest_servable_one`, is parametrised
  three ways: unknown kind, unknown field, items not a list. The second is
  `test_a_release_with_no_servable_revision_is_omitted_not_fatal`.
- `tests/contract/rehearsal/test_w53_rehearsal_target_guards.py` — new static test with
  15 cases.
- `docs/program/W53C-STORE-01.md` — this report.

## 2. Checks and results

Private lane `gate-w53c-store` (PostgreSQL 57040, S3 60640/60641). Its `.env` was derived
from `.env.example` with both sides consistent. Then `make up` (exit 0) and `make migrate`
(exit 0, head `0017_execution_queue`). Preflight: `free -g` showed 5 GB available and
`uptime` load was 2.38. Each pytest ran with `set -a; . ./.env; set +a` and
`.venv/bin/python -m pytest -q -p no:cacheprovider`, one at a time:

| Command (on `40b58ae` content) | Result |
|---|---|
| `tests/integration/runs/test_durable_effect_boundaries.py` (fresh database) | 18 passed |
| `tests/integration/ingest/test_reconciliation*.py` | 20 passed |
| `tests/integration/releases` | 59 passed |
| `tests/contract/rehearsal` | 15 passed |
| `tests/contract` (whole, clean tree at `40b58ae`) | 705 passed, 70 failed, 126 errors — all failures and errors in `test_cp00_candidate.py`, `test_cp00_final_state.py`, `test_validate_bootstrap.py`; identical counts (70 failed, 126 errors) on detached base `04de50c` in this worktree. Causes are environmental: `.git` is a file in a worktree (`NotADirectoryError`), `jsonschema` is absent from the shared bootstrap venv, and the `v0.0.1-architecture` tag lookup fails here |
| `git diff --check` | exit 0 |
| `.venv/bin/python -m compileall -q <9 changed .py>` | exit 0 |
| ruff | not installed in the shared `.venv` or on the host. Ruff 0.17.0 from a PyPI wheel unpacked into the session scratchpad (no venv change): `ruff check --isolated --select E4,E7,E9,F <9 files>` gives `All checks passed!`. Its broader default set reports only findings already present at base (import sort, `__all__`/`__slots__` order, TRY004, UP0xx, BLE001), and none are new |

**How each new test fails without the fix** (base files restored temporarily, then restored
back, with the tree verified):

- C-12, reproduced end to end first. A probe on base code ran the old eligibility, so
  `reject_unpublished(..., older_than="0 seconds")` set the blob to `rejected`. A new run of the
  same version then ended `failed`, and its `source_preparation` stage_result error was
  `state_transition_not_allowed: blob 'rejected' is terminal; it is never reopened`. That is
  the finding. With base `reconciliation.py`, the new tests fail on
  `assert True is False` (`rejection_eligible`) and on `'attempt_not_terminal'` /
  `'publication_not_stale'` ≠ `'content_addressed_rerun_self_heals'`. The rerun assertion fails as
  `'failed' == 'published'`. The probe left a `rejected` blob that poisons every later run, so the
  lane database was dropped and re-created before the passing run above.
- C-13: with base `repository.py` and `notes.py`, all 4 new cases fail. The unknown-kind and
  unknown-field cases serve the newer revision (`(3, 'From a newer image')`), which the
  transport's closed `ReleaseNoteKind`/extra-forbidding `ReleaseNoteItem` would turn into a 500.
  The items-not-a-list case raises `RuntimeError: release content has no items`. The omitted
  release appears (`['0.3.0', '0.2.5', '0.2.0']`).
- C-14: with base scripts, all 15 cases fail. There are 10 errors because
  `require_disposable_database` does not exist and 5 failures: no guard before
  `create_database_engine`, `assert` present in both scripts, no explicit preflight
  `SystemExit`, no `require`.

## 3. Contracts

None new or changed. The C-12 refusal uses `state_transition_not_allowed` with only the
catalog's safe detail keys (`machine`, `current_state`, `requested_state`). No migration
(head `0017_execution_queue`) and no API, domain, event or error-catalog change.

## 4. Risks and known limitations

- C-12 is the no-migration fix. Unbound intents stay `prepared` forever and remain listed in
  `unbound_analysis_artifacts`; the settlement state and the rejection redesign are deferred to
  W54 custody (plan §3). Blobs already `rejected` in a database by the old code are not
  repaired. No production caller existed, so none is expected. `reject_unpublished` lost its
  `older_than` keyword. The only callers were tests.
- C-13 serves the newest servable revision. It does not drop unknown items inside a newer
  revision. A release with no servable revision is omitted from `listReleases`, and
  `markReleaseNotesRead` still accepts it (unchanged). Skips are logged at WARNING, so they are
  not silent.
- C-14 guards the database only. `crash_process` still seeds into whatever `S3_*` names, and
  `proxy_faults.py` (not in the finding) still uses `assert` and has no target guard. Future
  `process_recovery` runs need a database named `w53_rehearsal*` on loopback.
- `test_provider_effect_settlement_is_bounded_and_resumable` fails when the runs module is run
  a second time on the same database, because its global `reconcile` sees earlier leftovers. This
  is pre-existing and reproduced with base code and the base test file. Run it on a fresh
  database.

## 5. Integrator instructions

Merge `agent/w53c-store` as is. For acceptance, run `tests/contract/rehearsal`,
`tests/integration/releases`, `tests/integration/ingest` and
`tests/integration/runs/test_durable_effect_boundaries.py` on a **freshly migrated** private
database. The runs module is not re-runnable on one database; see §4. No overlap with other
lanes: this lane did not touch `bootstrap/adapters.py`. The C-13 test only imports
`ReleasesAdapter` to exercise the `listReleases` data path.

## 6. Containment

`git diff --name-only 04de50c..HEAD` lists exactly the nine files of §1 plus this report, all
inside `allowed_paths`. No `contracts/**`, `db/migrations/**`, lock or dependency file,
`Makefile`, `tests/support/**`, `conftest.py`, `bootstrap/adapters.py`, `CURRENT_STATE.md` or
`DEBT_REGISTER.md` changed. `git status --porcelain -uall` is empty after the report commit.
Private containers, the network and both volumes (`gate-w53c-store-postgres-data`,
`gate-w53c-store-s3-data`) are removed. The listing read back 0 containers, 0 volumes and 0
networks matching `w53c-store`. `.env` is deleted. No kill by pattern, push, merge, tag or
worktree creation happened.
