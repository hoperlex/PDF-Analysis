# W48-JUDGE-Z — independent judge of the merged W48 closure line

- task: `docs/program/tasks/W48-JUDGE-Z.md` (as dispatched at `b04ba95`)
- subject: `819b6bdd75b7dc0c62cf6280d426266140e46ea5` on `integration/w48-close`
- branch / base: `agent/w48-judge-z` from `b04ba95` (subject plus the task file only)
- judged on: 2026-10-05, report-only; nothing in the subject was repaired

Part A was written and committed before any author report (`docs/program/W48-*.md`),
`docs/program/dispatch/W48-CLOSE.md` §2 or prior review file was opened. Part B is the
cross-examination written afterwards.

## Environment

| item | value |
| --- | --- |
| judge worktree | `.local/worktrees/w48-judge-z` (`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`: `bootstrap OK`; `npm --prefix web ci`: exit 0, 184 packages) |
| mutation copy | `.local/worktrees/w48-judge-z-mut`, `git worktree add --detach … 819b6bd`; `.venv` and `web/node_modules` symlinked to the judge worktree; every probe restored with `git checkout`/`git clean`/`git reset --hard 819b6bd` and `git status --short` re-read as empty |
| corpus | `.local/norms/corpus` symlinked read-only to the real corpus |
| instance | `FOUNDATION_INSTANCE=gate-w48judgez`, `POSTGRES_DB=auditmanager_w48judgez`, `S3_BUCKET=auditmanager-w48judgez` |
| ports | `ss -ltn` before allocation: 56520, 60120, 60121, 58520, 58521, 53020, 4520 all free. PostgreSQL 56520, S3 API 60120, S3 console 60121, API 58520, health 58521, web 53020, geckodriver 4520 |
| processes started | API `serve.py` (PIDs 3007465, 3113806, 3125714 in turn), `next start` 3013928, `geckodriver` 3028154 — each stopped by its recorded PID only |
| browser | no Chromium on the host (see U-1); Firefox 157.0 headless through `/snap/bin/geckodriver` |

`.env` copied from the integrator's lane with only the instance, ports, database, bucket,
`DATABASE_URL` and `S3_ENDPOINT_URL` changed. No credential, cookie or provider body is in
this report.

## Part A — black-box pass

### A-1 Frozen inputs and ancestry

| check | command | result |
| --- | --- | --- |
| contracts and root locks | `git diff --stat 6118e66 819b6bd -- contracts uv.lock web/package-lock.json web/FRONTEND_LOCK.json` | empty (0 lines, exit 0) — **holds** |
| whitespace | `git diff --check 6118e66 819b6bd` | no output — holds |
| merge shape | `git log --oneline --merges -8 819b6bd` | `68cb5a2` DURABLE-FIX-2, `5d99b62` GUARDS-2, `3d5f322` TAILS, `819b6bd` PUBLIC-01 — matches the task |

### A-2 `W48-PUBLIC-01` changed only what it was granted

`git diff --name-status 3d5f322 819b6bd` lists 33 paths: 22 modified importers, 7 new
`public.py` (`storage`, `bootstrap`, `documents`, `findings`, `ingest`, `jobs`, `runs`) plus the
modified `analysis/public.py`, the new guard, `ARCHITECTURE_LINT_RULES.md` (one added line: the
enforcement sentence), `docs/program/W48-PUBLIC-01.md`, and `docs/program/tasks/W48-PUBLIC-01.md`
— the last one from the integrator's dispatch commit `b419f69`, not from the executor
(`git show --name-only b224bc7 f36d258`).

- `git diff -U0 3d5f322 819b6bd -- src ':!src/**/public.py'` shows only `from … import …`
  lines. **Holds.**
- Independent identity check (`.local/judge/identity.py`, run with `PYTHONPATH=src`): for
  every importer, the set of bound names is unchanged and each of the **101** rebound names
  resolves through the new public path to the *same object* (`is`) it resolved to through the
  old path — `changed bindings checked: 101 non-identical: 0`. No behaviour moved.
- `EXCEPTIONS.md` untouched (not in the name list). **Holds.**

### A-3 ALR-05 walk, run independently

My own walk (`.local/judge/alr05_walk.py`, written without copying the task's one-liner; it also
resolves relative imports, `from auditmanager import x`, and flags string `import_module`):

```text
subject 819b6bd                : JUDGE-COUNTS deep=0 package-root=0 dynamic=0
calibration, base 3d5f322 (src): JUDGE-COUNTS deep=18 package-root=24 dynamic=0
```

The calibration reproduces the task's captured `COUNTS 18 24`, so a zero on the subject is
not a blind walk.

Guard mutations in the copy (`jobs/repository.py:23`), each run as
`.venv/bin/python -m pytest tests/contract/architecture/test_alr05_boundaries.py -q`:

| mutation | result | reason printed |
| --- | --- | --- |
| baseline | `1 passed` | — |
| `from auditmanager.storage.models import …` (deep) | **`1 failed`** | `deep src/auditmanager/jobs/repository.py:23 auditmanager.storage.models` |
| `from auditmanager.storage import …` (package-root) | **`1 failed`** | `package-root src/auditmanager/jobs/repository.py:23 auditmanager.storage` |
| `from ..storage.models import …` (relative, judge extra) | **`1 failed`** | `deep … auditmanager.storage.models` |
| `importlib.import_module("auditmanager.storage.models")` (judge extra) | `1 passed` | not seen — see F-6 |

### A-4 `W48-GUARDS-2` mutations, re-run independently

Every mutation was applied to a real tracked file of the copy (or a new file in the scanned
directory), never to an in-test string. Script-file mutations for `test_alpha_acceptance_command.py`
were committed as throw-away detached commits in the copy and reset afterwards, because that
test refuses a dirty checkout (`FAIL: checkout содержит незакоммиченные изменения`) and a red for
that reason would prove nothing. Logs: `.local/judge/g*.log` (not committed).

| id | mutation | result | stated reason reached? |
| --- | --- | --- | --- |
| G-1a | new `web/tests/guards/sixth-screen.ts` mounting `AppRouterContext.Provider` | **red** (1 failed / 10) | yes: `…sixth-screen.ts must consume renderScreen from the shared harness`, `…privately mounts AppRouterContext` |
| G-1b | same file under `web/tests/unit/styles/` | **red** | yes, same two findings |
| G-1c (extra) | same file under `web/tests/unit/screens/` | green (11 passed) | no — see F-1 |
| G-2a | `use-create-project.ts:42` `invalidateQueries(dashboard)` → `getQueryData(...)` | **red** (3 failed) | yes: `expected invalidatesDashboard() to be true, got false` |
| G-2b | new `features/archive-project/model/use-archive-project.tsx` with `RQ.useMutation` | **red** | yes: `a mutation hook exists that this map does not name` |
| G-2c (extra) | same hook in `model/archive.ts` | green | no — see F-2 |
| G-3a | `# This application serves twelve public operations.` in `src/auditmanager/api/app.py` | **red** | yes: `states 12 for operations, expected 20` |
| G-3b | `// The API has twelve routes.` in the BFF route handler | **red** | yes: `states 12 for an unlisted surface noun, expected {17, 20, 61, 22}` |
| G-4a | empty `## Enumerator ownership` body in `tasks/W48-PUBLIC-01.md` | **red** | yes: `ENUMERATOR_CHANGE_DECLARATION_REQUIRED` |
| G-4b | `captured_output` block reduced to `x` | **red** | yes: `PREMISE_OUTPUT_SUBSTANTIVE_REQUIRED` |
| G-4c1 | `origin_main_authority: separate direct owner instruction x`, target left `none` | green | no — see F-3 |
| G-4c2 | same, with `development_target: origin/main` | **red** | yes: `MAIN_DIRECT_AUTHORITY_REFERENCE_REQUIRED` |
| G-4d (extra) | target `origin/main`, reference `xxxxxxx` | green | no — see F-3 |
| G-5a | `verify-acceptance.mjs:191` drop `!failedTextAnalysis &&` | **red** | yes: `test_partial_with_failed_text_analysis_is_not_provider_live_pass` — verifier printed `acceptance verdict: PASS`, test expected exit 1 |
| G-5b | report label `attested_deployed_sha` → `proven_deployed_sha` + "proves" | **red** | yes: `assert '- attested_deployed_sha: …' in report` |
| G-5b2 (extra) | keep both attested lines, add `deployed_sha_proof: this report proves the served revision` | green (16 passed) | no — see F-4 |
| G-5c | delete the `--candidate-sha` guard line of `manual-alpha-check.sh` | **red** | yes: expected `ALPHA ACCEPTANCE BLOCKED: укажите --candidate-sha`, got `…--deployed-sha` (the fired-guard set is asserted) |
| G-6a | `pull_request_target:` added to `deploy-auto.yml` | **red** | yes: `DEPLOY_TRIGGER_SET` |
| G-6b | top-level `contents: write` | **red** | yes: `TOP_LEVEL_PERMISSIONS` |
| G-6c | first host's key blob changed under the same fingerprint comment | **red** | yes: `PINNED_HOST_KEY_BLOB` |
| G-6d (extra) | job-level `permissions: contents: write` under `jobs.deploy` | green (7 passed) | no — see F-5 |
| G-6e (extra) | a third `known_hosts` line for a foreign host | green | no — see F-5 |

**Every mutation the GUARDS-2 task names is red for its stated reason on the subject.** The
greens are the judge's own extra probes, recorded as F-1…F-5.

### A-5 `W48-TAILS` closed-vocabulary sites: one unknown value each

Independent inventory: `rg -n 'LABELS\[|_LABEL\[|as ProviderMode' web/src/widgets web/src/entities web/src/shared/ui`
plus the server-fed values each label site reads. A disposable vitest file
(`.local/judge/judge-z-injection.test.ts`, copied into the copy as
`web/tests/unit/judge-z-injection.test.ts`, deleted afterwards) rendered each site with the
value `zz_judge_unknown` and recorded the fault marker, whether the raw value leaked, and the
visible text. Run: `npm --prefix web test -- --run tests/unit/judge-z-injection.test.ts`.

| site | injected field | outcome |
| --- | --- | --- |
| `VerdictBadge` | verdict | typed fault `role=alert` "Неизвестный вердикт" |
| `RunStateBadge` | state / providerMode | typed fault `role=alert` |
| `StageStatusBadge` | status | typed fault `role=alert` |
| `StageTable` | stageId / status / dependsOn | `data-stage-table-fault="closed-vocabulary"` |
| `DecisionHistory` | event_type / verdict | `data-history-fault="closed-vocabulary"` |
| `KnowledgeBase` | category / event_type / current_verdict / verdict | `data-knowledge-base-fault="closed-vocabulary"` |
| `ExportPanel` | runState | `data-export-fault="closed-vocabulary"`; providerMode → badge fault |
| `RunProgress` | state / degradation_set / stage_id / stage status | `data-run-progress-fault="closed-vocabulary"` |
| `StageComparison` | state / stage_id / stage status | `data-stage-comparison-fault="closed-vocabulary"` |
| `VerdictsPanel`, `RunActivityPanel` | verdict row / by_state / cost_basis | `data-panel-fault="incomplete"` |
| `StageTable`, `RunProgress` | stage `error_code` | raw code printed verbatim — not a label lookup; cannot miss |
| `RunProgress`, `StageComparison` | `terminal_reason` | raw code printed with "У этого экрана нет описания для такой причины" — explicit, cannot miss |
| `RunProgress` | `provider_mode` | **no fault**: renders "режим провайдера: не сообщён. Это показание не несёт режима провайдера" — F-7 |
| `RunProgress` | `cost_basis` | **no fault**: renders "Основание не указано. Это показание не несёт основания стоимости" — F-7 |
| `StageComparison` | `provider_mode` | **no fault**: "не сообщён", comparison `differs` — F-7 |
| `StageComparison` | `cost_basis` | **no fault**: "—", comparison `one_sided` — F-7 |

No site produced an empty label. Four sites cannot miss because they normalise first
(`run-presentation.ts:48` `providerModeLabel`, `:403` `runCost`), but the normalisation turns
an *unrecognised* value into the *absent* reading and then states that the reading carries no
value — F-7.

### A-6 DJ-R fixes reverted in the copy

Baseline on the copy, with the lane `.env` exported:
`pytest tests/integration/db/test_durable_analysis_effects.py tests/integration/runs/test_durable_effect_boundaries.py tests/integration/ingest/test_reconciliation.py tests/integration/ingest/test_reconciliation_rules_with_no_guard.py tests/integration/norms/test_rerecognition.py -q`
→ `63 passed in 42.34s`, exit 0. (A first attempt without the exported `.env` errored at setup
with `DATABASE_URL is not set` — recorded, not counted.)

| item | revert in the copy | named test(s) | result |
| --- | --- | --- | --- |
| DJ-R3 | `ingest/reconciliation.py` ← `a8ba8d2^` | the four DJ-R3 regressions | **4 red**: two behavioural (`assert (OrphanObject…,) == ()` — a pre-0014 / unattributed blob is again an orphan), two by signature (`report() got an unexpected keyword argument 'unbound_artifact_age'`, `reject_unpublished() … 'older_than'`) |
| DJ-R3 (targeted) | remove `if not authorities: refuse("legacy_unattributed")` | `test_a_legacy_unattributed_blob_cannot_be_rejected_without_attempt_authority` | **red**: `DID NOT RAISE DomainError` |
| DJ-R3 (targeted) | remove the `attempt_not_terminal` refusal (`reconciliation.py:595-596`) | `test_only_stale_terminal_analysis_publication_without_bytes_can_be_rejected` | green — F-8 |
| DJ-R3 (targeted) | remove the `publication_not_stale` refusal (`:597-598`) | same | green — F-8 |
| DJ-R3 (targeted) | remove both, run `tests/integration/ingest tests/integration/runs tests/integration/storage` | 268 tests | **268 passed** — F-8 |
| DJ-R4 | `settled = ()` instead of `settle_terminal_provider_effects(...)` | `test_live_response_lost_before_checkpoint_is_diagnosable_and_never_replayed`, `test_provider_effect_settlement_is_bounded_and_resumable` | **2 red**: `unresolved_provider_effects` not empty |
| DJ-R4 | drop `LIMIT :batch_size` | bounded test | **red**: `assert 5 == 1` |
| DJ-R4 (extra) | drop the run/job/attempt terminality predicates (`jobs/repository.py:173-179`) | `tests/integration/runs tests/integration/db tests/integration/ingest` | **401 passed** — F-9 |
| DJ-R4 (extra) | drop the age predicate (`:180`) | `tests/integration/runs` | **114 passed** — F-9 |
| DJ-R5 | `norms/__main__.py` ← `a8ba8d2^` | `test_live_command_refuses_before_transport_or_ledger_write` | **red**: `live refusal must precede provider transport construction` |
| DJ-R6 FK | delete `fk_provider_effect_final_call_belongs_to_run` from 0014 | `test_cross_run_final_model_call_insert_is_refused_by_the_composite_fk` | **red**: `DID NOT RAISE DBAPIError` |
| DJ-R6 trigger | `BEFORE INSERT OR UPDATE` → `BEFORE UPDATE` on `job` and `attempt` | `test_invalid_initial_job_and_attempt_states_are_refused_by_the_trigger` | **red**: `DID NOT RAISE DBAPIError` |
| DJ-R6 downgrade | `if any(occupied.values()):` → `if False:` | `test_occupied_0014_downgrade_refuses_without_moving_the_head` | **red**: downgrade exit 0 where non-zero was required |

Every named DJ-R test goes red when its fix is reverted. Two safety predicates inside the
fixes are not pinned by any test (F-8, F-9).

### A-7 Migration head on a fresh database

```text
alembic current (empty database)  -> (no revision)
alembic upgrade head              -> … 0013_norm_embeddings -> 0014_durable_analysis_effects, exit 0
alembic current / heads           -> 0014_durable_analysis_effects (head) / 0014_durable_analysis_effects (head)
SELECT version_num FROM alembic_version -> 0014_durable_analysis_effects
```

Repeated twice more on a dropped-and-recreated database for the browser stand: same head.

`tests/contract/api_v1/test_doc_prose_facts.py`: `_true_migration_head()` (`:371`) reads
`revision`/`down_revision` from every file and returns the single non-parent; the inventory at
`:206` now keys on `_true_migration_head()` instead of the old `"0013` literal. One deliberate,
registered literal pin remains at `:543`. Probe: adding
`db/migrations/versions/20261005_0015_judge_probe.py` (`down_revision = "0014_…"`) to the copy
turns **two** tests red — the pin, and
`test_the_scanned_docs_state_the_migration_head_this_tree_has`
(`CURRENT_STATE.md: … names head 0014, tree has 0015_judge_probe`). The prose guard derives the
head from the tree. **Holds.**

### A-8 Hostile strings at 780 × 900 in a built stand

Stand: subject API (`infra/deploy/serve.py`, recorded provider mode) on 58520, `next build`
with `NEXT_PUBLIC_API_BASE_URL=/bff/v1` then `next start` on 53020, against the lane's own
PostgreSQL/MinIO. Driver: `.local/judge/hostile-width.mjs` — WebDriver (geckodriver) for the
browser, and the repository's own `tests/e2e/pc01/journey/width.mjs` (`MEASUREMENT`,
`widthFindings`) and `manifest.json` `viewport` (780 × 900), imported unchanged. Data made
through the app's BFF in the signed-in browser: sign-in with the migration's documented seed,
password rotated (new value never printed), project named with **200** unbroken characters
(`Ш`×100 + `W`×100), `ar_baseline.pdf` uploaded, run `published`, a `comment` decision with
**400** unbroken characters (`Щ`×200 + `M`×200).

| route | hostile string rendered | scrollWidth | innerWidth | clientWidth | width findings |
| --- | --- | --- | --- | --- | --- |
| `/projects` | name: yes — carrier `<a>` left 66, right 711, width 645 | 780 | 780 | 780 | 0 |
| `/projects/prj_…` | name not shown (identifier page) | 768 | 780 | 768 | 0 |
| `/projects/prj_…/versions/ver_…` | not shown | 768 | 780 | 768 | 0 |
| `/projects/prj_…/documents/doc_…` | not shown | 780 | 780 | 780 | 0 |
| `/projects/prj_…/runs/run_…` | not shown | 768 | 780 | 768 | 0 (13 elements of the stage table reach right 812 inside a scroll container; the document does not widen) |
| `/projects/prj_…/runs/run_…/review` | comment: yes — `p.am-history__comment` left 83, right 719, width 636, scrollWidth 636 = clientWidth 636, height 195 | 768 | 780 | 768 | 0 |
| `/knowledge-base` | comment: yes — `p.am-kb__comment` right 731, width 664 | 780 | 780 | 780 | 0 |
| `/dashboard` | name: yes — carrier `<a>` right 696, width 630 | 768 | 780 | 768 | 0 |

Non-vacuity on the same stand and page: appending a 1400 px box made the same expression read
`scrollWidth 1400` and `widthFindings` return one finding. Measured viewport `[780, 900]` equals
the manifest's. **Neither hostile string widens any document at 780 px; the decision-history
comment wraps inside its column (636 px).**

### A-9 Black-box findings

| id | class | finding |
| --- | --- | --- |
| F-1 | register | `web/tests/guards/screen-set.guard.test.ts:92-93,99` — the D-97 case "keeps the provider implementation in the shared harness only" discovers consumers only under `tests/guards` and `tests/unit/styles`. Five tracked files under `web/tests/unit/screens/` mount `AppRouterContext.Provider` privately today (`cold-load.test.ts:113`, `forms-and-pages.test.ts:141`, `stage-comparison.test.ts:60`, `run-cache-shape.test.ts:91,123`, `project-sections.test.ts:59`). Repro: G-1c stays green. The named G-1 mutation is red; the case's title over-claims its scope. |
| F-2 | register | `web/tests/guards/dashboard-invalidation.guard.test.ts:172-174` — discovery is `features/**/model/use-*.ts(x)`; a `useMutation` hook in `model/archive.ts` is invisible. Repro: G-2c green. |
| F-3 | register | `tests/contract/program/test_wave_governance.py:100,104` — `origin_main_authority` is validated only when `development_target == origin/main`, and only by length (≥ 7 chars). Repro: G-4c1 (`…instruction x` with target `none`) and G-4d (`xxxxxxx` with target `origin/main`) green. |
| F-4 | register | "never proves" is not executable: `tests/contract/test_alpha_acceptance_command.py:287-288` asserts the presence of the attestation lines, nothing asserts the absence of a proof claim. Repro: G-5b2 green. |
| F-5 | register | `tests/contract/test_deploy_auto_workflow.py:43,49` — only top-level `permissions` and the count of the two pinned lines are checked; a job-level `contents: write` and an extra `known_hosts` entry pass. Repro: G-6d, G-6e green. The shipped workflow is correct today. |
| F-6 | register | `tests/contract/architecture/test_alr05_boundaries.py:51` reads only `import`/`from` statements; a string `importlib.import_module("auditmanager.storage.models")` passes. None exists today (my walk: `dynamic=0`). |
| F-7 | register | Unknown `provider_mode` / `cost_basis` are normalised to absent and then described as absent: `web/src/entities/audit-run/model/run-presentation.ts:48,110` ("Это показание не несёт режима провайдера"), `:403,427` ("…не несёт основания стоимости"); `stage-comparison.tsx:205` "не сообщён". The reading *did* carry a value the client cannot read. Nothing misstates `live` or `measured`, so it fails safe, but it is the silent-fallback shape `AGENTS.md` §4 names. |
| F-8 | register | `src/auditmanager/ingest/reconciliation.py:595-598` — the `attempt_not_terminal` and `publication_not_stale` refusals of `reject_unpublished` are not pinned: removing both leaves 268 ingest/runs/storage integration tests green (the only negative test refuses for `temporary_object_present` / the running Attempt at the same time). `reject_unpublished` has no production caller (`grep -rn reject_unpublished src infra scripts` → none), so the live-Attempt protection is correct but unguarded. |
| F-9 | register | `src/auditmanager/jobs/repository.py:173-180` — the provider-effect sweep's run/job/attempt terminality predicates and its age predicate are not pinned: removing the three terminality predicates leaves 401 runs/db/ingest tests green; removing the age predicate leaves 114 runs tests green. The sweep runs in every API start (`api/app.py:295-297` → `reconcile_at_startup`). Behaviour today is correct; a regression that abandoned a live Attempt's effect would ship green. |
| F-10 | register | `src/auditmanager/ingest/reconciliation.py:298,369,436` — after DJ-R3, `Reconciler.report()` never populates `orphan_objects` or `unpublished_records`; every blob row without a manifest or analysis intent (including a post-0014 *document upload* interrupted between publish and commit) is reported as `legacy_unattributed_blobs` ("may pre-date migration 0014"), and `reject_unpublished` refuses it. Conservative, but two report fields are now dead and the module docstring (`:24-26`) still describes `unpublished_records` as a live category. |
| F-11 | register | `src/auditmanager/analysis/public.py:64,90` exports the text stage's version as the context-wide name `STAGE_VERSION`; importers alias it (`runs/executor.py` → `TEXT_STAGE_VERSION`). Naming only. |

No release-blocking or must-fix-before-merge finding in the black-box pass.

### A-10 Untested questions

- **U-1.** The repository's own journey (`npm --prefix web run e2e:pc01`, `cdp.mjs`) cannot run on
  this host: `node -e "import('./tests/e2e/pc01/journey/cdp.mjs').then(m=>m.findChrome())"` →
  `No Chromium binary found. The journey drives a real browser and will not skip. Looked at:
  /root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome, …/chromium-1228/…, /usr/bin/chromium,
  /usr/bin/chromium-browser, /usr/bin/google-chrome`. The width figures above come from the
  journey's own measurement module driven through Firefox 157 — not from Chromium, and not
  from the journey's cold-browser walk.
- **U-2.** No live provider call was made; the stand ran `recorded`.
- **U-3.** The full battery was not re-run by the judge; the integrator's gate (P-02) is
  accepted as the battery's statement, and the judge ran only focused suites.
