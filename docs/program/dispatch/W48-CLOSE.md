# W48 closure — Stage C: rule, re-judge, repair the instruments, publish to `dev`

**Status:** amendment to `W48-PLAN.md`; Stage A and Stage B are executed but unpublished.
**Controlling rulings:** `R-49`; `R-53` (to be recorded by `W48-RULE-01`, see
`IDENTITY-WAVES.md` §4).
**Exit:** the merged W48 candidate on `origin/dev` with literal `GATE OK`, then — on the owner's
direct instruction naming that SHA — published to `origin/main`, deployed, accepted live and
tagged `alpha-w48` (§9, P-7).

## 1. Where W48 actually is (measured 2026-10-05 at `c11f1b6`)

| Fact | Measurement |
| --- | --- |
| `origin/dev` | `9b5219e` — the docs-only freeze/dispatch tip |
| `origin/main` | `608632a` — last auto-deploy publication, 2026-10-01 |
| main checkout branch | `agent/w47-close` at `c11f1b6`, one commit ahead of `origin/dev` (the audit report) |
| W48 work | 17 branches `agent/w48-*` in `.local/worktrees/`, **none pushed**; every worktree clean except `w48-freeze-6118e66` (untracked `.venv`, `web/node_modules`) |
| furthest tip | `agent/w48-durable-repair` = `411c6d0`, 46 commits ahead of `c11f1b6`, a linear descendant of `agent/w48-stage-a` = `03c04a1` |
| Stage A/B integration | `03c04a1` contains PROSE, GUARDS, FIX, PORTS, WEB, LIVE, GOV, JUDGE-X/Y, FIX-B merged |
| durable effects | `afc6fcb` (DURABLE-01), rejected by `b431850` (DURABLE-JUDGE), repaired by `0e88589`, reported by `411c6d0`; judge and repairer were the same agent |
| migration head on that tip | `0014_durable_analysis_effects`, edited in place by the repair |

Commands: `git worktree list`; `git log --oneline c11f1b6..agent/w48-durable-repair | wc -l`;
`git merge-base --is-ancestor agent/w48-stage-a agent/w48-durable-repair`;
`for w in .local/worktrees/w48-*; do git -C $w status --porcelain | wc -l; done`.

## 2. Findings this stage must dispose of

From the 2026-10-05 revision of the W48 branches (read-only, five independent reviewers; the
items marked ✓ were re-measured by the integrator on the tree).

**Durable effects (`agent/w48-durable-repair`)**

- DJ-R1 ✓ the migration grant exists only as a sentence inside `tasks/W48-DURABLE-01.md`;
  `W48-PLAN.md` §9 still says `db/migrations/**` is frozen with no owner; no ruling records it.
- DJ-R2 `src/auditmanager/analysis/text/__init__.py` was changed outside DURABLE-01's
  `allowed_paths` while its report claims full compliance.
- DJ-R3 `ingest/reconciliation.py` classifies runs older than `0014` (no publication rows) and
  live attempts as orphans/unpublished; the report has no age and no attempt state;
  `reject_unpublished` can reject a live `temporary` blob and burn its content identity.
- DJ-R4 effects have no settled state (`abandoned`/`resolved`); `is_clean` can never become
  true; `unresolved_provider_effects` replays all history at every start.
- DJ-R5 `norms/__main__.py` still calls the paid provider outside the journal.
- DJ-R6 the schema test checks `pg_get_constraintdef` text, not a refused INSERT; the transition
  trigger has no behavioural test; the downgrade refusal on occupied tables has no committed test.
- DJ-R7 the final report commit `411c6d0` has no gate of its own; `GATE OK` is recorded for
  `0e88589`.

**Guards (Stage A/B)**

- G-1 ✓ `web/tests/guards/screen-set.guard.test.ts` "can fail on a private screen-wide provider
  copy" asserts a string contains itself; the guard checks a hard-coded list of five files.
- G-2 `dashboard-invalidation.guard.test.ts` accepts any call carrying
  `queryKeys.dashboard.summary`, so `getQueryData(...)` in place of `invalidateQueries(...)`
  stays green; discovery sees only `features/*/model/use-*.ts` with a literal `useMutation(`.
- G-3 `tests/contract/api_v1/test_surface_counts_in_prose.py` misses "twelve public operations"
  and "The API has twelve routes" — the W18 shape; `_historical_surface_values` reads `git log`
  and silently narrows in a shallow clone.
- G-4 `tests/contract/program/test_wave_governance.py` passes empty sections, an unread
  `enumerated_set_changed`, a one-character `captured_output`, and an `origin_main_authority`
  value of "separate direct owner instruction x".
- G-5 `scripts/manual-alpha-check.sh` / `tests/e2e/pc01/journey/verify-acceptance.mjs`:
  `--deployed-sha` is operator input; `providerLive=PASS` accepts `partial` with a failed text
  stage; `test_missing_origin_sha_and_credential_never_print_pass` asserts an exit code.
- G-6 `tests/contract/test_deploy_auto_workflow.py` is substring-based (see
  `IDENTITY-WAVES.md` §7).

**Audit tails**

- T-1 A-04 residue: fail-open lookups in `decision-history.tsx`, `verdict-badge.tsx`,
  `run-state-badge.tsx`, `stage-status-badge.tsx`, `run-progress.tsx`, `stage-comparison.tsx`,
  `export-panel.tsx`.
- T-2 `.am-history__comment` has no `overflow-wrap`/`min-width: 0`; hostile-text containment
  covers two selectors.
- T-3 ✓ D-52 is repaired by `web/NOTICE` and open in `DEBT_REGISTER.md` (rows 59 and 3683).
- T-4 `infra/deploy/proxy/nginx.conf` comment misquotes `api/app.py`.
- T-5 ✓ `W48-PLAN-01.md` cites `cf63d31` (unreachable) and "both observed workflow runs
  failed"; `W48-FREEZE-01.md` records the success. `CURRENT_STATE.md` says `origin/main`
  "remains unchanged" while it moved seven times after `alpha-w47`.
- T-6 A-03 (sixteen ALR-05 deep imports, twenty-two more through package `__init__`) — decided
  by P-8 on 2026-10-05: repaired in full here (`W48-PUBLIC-01`), no waiver.
- T-7 `infra/local/README.md` and `bucket-init.sh` still describe `FOUNDATION_S3_IMAGE` as live.

## 3. Entry conditions

| Condition | Evidence |
| --- | --- |
| every `agent/w48-*` branch has a backup ref and a bundle | `git for-each-ref refs/backup/w48-2026-10-05/`; `.local/backup/w48-2026-10-05.bundle` verified with `git bundle verify` |
| no gate is running in any W48 worktree | `ps -o pid,cmd -p <recorded pids>` empty; no pattern kills |
| `origin/dev` still equals `9b5219e` and `origin/main` still equals `608632a` | `git fetch origin && git rev-parse origin/dev origin/main` |
| the real corpus is attachable to the integration worktree | `test -d .local/norms/corpus` |

## 4. Tasks

Task files are generated from `docs/templates/TASK_TEMPLATE.md` by `W48-SAFE-01` with exact
SHAs. The fields below are the content those files must carry.

### `W48-SAFE-01` — backup, inventory, task files

- **Outcome:** no W48 work can be lost by a worktree or branch mishap; the integration line is
  named.
- **Allowed paths:** `refs/backup/**`, `.local/backup/**`, `docs/program/tasks/W48-SAFE-01.md`,
  `docs/program/tasks/W48-RULE-01.md`, `docs/program/tasks/W48-DURABLE-JUDGE-2.md`,
  `docs/program/tasks/W48-DURABLE-FIX-2.md`, `docs/program/tasks/W48-GUARDS-2.md`,
  `docs/program/tasks/W48-TAILS.md`, `docs/program/tasks/W48-JUDGE-Z.md`,
  `docs/program/tasks/W48-INT-CLOSE.md`, `docs/program/W48-SAFE-01.md`,
  `docs/program/dispatch/PORT_REGISTRY.md` (rows for the lanes below).
- **Deliverables:** backup refs and bundle; a table of every `agent/w48-*` tip with SHA and
  ancestry; task files; `integration/w48-close` branch created at `411c6d0` (no code change).
- **Required checks:** `git bundle verify`; every backup ref equals its branch tip;
  `git diff --check`.
- **Non-goals:** no merge, no gate, no code.

### `W48-RULE-01` — record `R-53` and `R-54`; amend the W48 ownership by addendum

- **Allowed paths:** `docs/program/OWNER_RULINGS_2026-09-17.md`, `docs/program/dispatch/W48-PLAN.md`
  (an addendum section only; §9 and §15 are not rewritten), `docs/program/W48-RULE-01.md`.
- **Deliverables:** `R-53`, `R-54` with their dates and sources (`R-54` names the commit on
  `plan/identity-waves` that removed the withdrawn W49 documents and says the number is reused);
  a W48-PLAN addendum "2026-10-05: migration slot owned by `W48-DURABLE-01` under `R-53`;
  successor plan is `IDENTITY-WAVES.md`; §15's W49 paragraph is superseded".
- **Required checks:** `.venv/bin/python -m pytest tests/contract/api_v1/test_doc_prose_facts.py -q`;
  `git diff --check`.
- **Stop:** if the owner does not confirm the ruling text, nothing else in this stage proceeds.

### `W48-DURABLE-JUDGE-2` — independent judge of `agent/w48-durable-repair`

- **Subject:** `411c6d0`. **Allowed path:** `docs/program/reviews/W48-DURABLE-JUDGE-2.md`.
- **Independence:** a fresh context that has not read `W48-DURABLE-REPAIR.md`,
  `reviews/W48-DURABLE-JUDGE.md` or §2 above before its own pass. It reads them afterwards and
  cross-examines each DJ-R item: upheld, narrowed or falsified, with a new measurement.
- **Required probes:** (a) kill after `adapter.complete` returns and before the checkpoint
  commit, against owned disposable services, prove what the journal holds; (b) kill after
  `put_blob` verification and before the stage commit, prove the reconciliation report names the
  blob and does not reject a live one; (c) a direct `INSERT` that must be refused by the composite
  FK and the transition trigger; (d) `alembic downgrade` on an occupied `0014` database must
  refuse; (e) fresh database upgrade to `0014`, then the full battery; (f) `git diff --name-only
  e3fedd0..411c6d0` against the two task files' `allowed_paths`.
- **Verdict shape:** release-blocking / must-fix-before-merge / register. Repairs nothing.

### `W48-DURABLE-FIX-2` — repair what the judge upheld

- **Allowed paths:** `src/auditmanager/jobs/**`, `src/auditmanager/runs/**`,
  `src/auditmanager/storage/**`, `src/auditmanager/ingest/reconciliation.py`,
  `src/auditmanager/analysis/text/**`, `src/auditmanager/norms/__main__.py`,
  `db/migrations/versions/20261002_0014_durable_analysis_effects.py` (only if the judge upholds a
  schema defect; otherwise frozen), `tests/integration/runs/**`, `tests/integration/db/**`,
  `tests/integration/storage/**`, `tests/integration/norms/**`, `docs/program/W48-DURABLE-FIX-2.md`,
  `docs/program/W48-DURABLE-01.md` (addendum for DJ-R2 only).
- **Expected content, if upheld:** a settled state for effects and a bounded sweep (DJ-R4); the
  reconciliation report carries attempt state and a pre-`0014` class so no live or legacy blob is
  classified as an orphan (DJ-R3); `norms/__main__.py` either journals the call or refuses live
  mode with a typed error (DJ-R5); behavioural tests for the FK, the trigger and the downgrade
  refusal (DJ-R6); an addendum acknowledging DJ-R2.
- **Required tests:** the judge's probes (a)–(e) re-run green; focused suites named by file;
  `make gate` on the task tip; `git diff --check`.

### `W48-GUARDS-2` — the W48 guards must be able to fail

- **Allowed paths:** `web/tests/guards/screen-set.guard.test.ts`,
  `web/tests/guards/dashboard-invalidation.guard.test.ts`,
  `tests/contract/api_v1/test_surface_counts_in_prose.py`,
  `tests/contract/program/test_wave_governance.py`, `tests/contract/test_alpha_acceptance_command.py`,
  `tests/contract/test_deploy_auto_workflow.py`, `tests/e2e/pc01/journey/verify-acceptance.mjs`,
  `scripts/manual-alpha-check.sh`, `docs/program/ALPHA_PUBLIC_ACCEPTANCE.md`,
  `docs/program/W48-GUARDS-2.md`.
- **Required mutations, each must fail for its stated reason:** G-1 a sixth screen file with a
  private `AppRouterContext.Provider`; G-2 `invalidateQueries` replaced by `getQueryData`, and a
  `.tsx` hook using `RQ.useMutation`; G-3 "twelve public operations", "The API has twelve routes";
  G-4 an empty `Enumerator ownership` body, `captured_output: x`, `origin_main_authority:
  separate direct owner instruction x`; G-5 `partial` with a failed text stage must not be
  `providerLive=PASS`; the acceptance report says **attested** deployed SHA, never "proves";
  the exit-code test asserts the path set of guards that fired; G-6 `pull_request_target:` added,
  `permissions: contents: write`, a key blob changed under the same fingerprint comment — each
  red.
- **Required tests:** `npm --prefix web test -- --run tests/guards`; `.venv/bin/python -m pytest
  tests/contract -q`; `git diff --check`.
- **Non-goals:** no version endpoint; no workflow change.

### `W48-TAILS` — audit tails, by addendum where history is involved

- **Allowed paths:** `web/src/widgets/**`, `web/src/entities/**`, `web/src/app/globals.css`
  (one global-style slot: `.am-history__comment`, `.am-history__event` containment),
  `web/tests/unit/**`, `infra/deploy/proxy/nginx.conf` (comment only), `infra/local/README.md`,
  `infra/local/bucket-init.sh` (comment only), `docs/program/DEBT_REGISTER.md` (D-52 close
  addendum and the A-03 row only), `docs/program/W48-PLAN-01.md` (addendum only),
  `docs/program/CURRENT_STATE.md` (the `origin/main` sentence only), `docs/program/W48-TAILS.md`.
- **Deliverables:** typed faults for the nine T-1 sites with a test per site that injects an
  unknown value; T-2 containment with a style test; D-52 close addendum pointing at
  `web/NOTICE` and `4a602ba`; A-03 debt row with the AST command and the two counts (16 / 22);
  T-4, T-5, T-7 corrections.
- **Required tests:** `npm --prefix web test -- --run`; `npm --prefix web run lint -- --quiet`;
  `npm --prefix web run typecheck`; `.venv/bin/python -m pytest tests/contract/api_v1 -q`;
  `git diff --check`.

### `W48-PUBLIC-01` — every cross-context import goes through a public module

- **Why here:** P-8. `W48-AUDIT` A-03 measured sixteen deep imports; the 2026-10-05 revision
  re-ran the AST walk at `c11f1b6` and counted 16 module-level plus 22 through a package
  `__init__`. ALR-05 (`docs/architecture/ARCHITECTURE_LINT_RULES.md`) admits only
  `auditmanager.<context>.public`; `shared` and importers under `bootstrap` are the exceptions.
  Today only `src/auditmanager/analysis/public.py` exists.
- **Allowed paths:** `src/auditmanager/<context>/public.py` for every context another context
  imports (at least `storage`, `bootstrap`, `documents`, `findings`, `analysis`, `access`,
  `runs`); the **import lines only** of every importing module the AST walk lists (the task's
  report carries the list with the command); `src/auditmanager/api/composition.py` (its two
  `bootstrap` imports move to `bootstrap.public`; this task is the composition-root owner of its
  stage); `tests/contract/architecture/test_alr05_boundaries.py` (new);
  `docs/architecture/ARCHITECTURE_LINT_RULES.md` (only to name the guard as the enforcement);
  `docs/program/W48-PUBLIC-01.md`.
- **Deliverables:** public modules that re-export exactly what is imported today, no new
  behaviour; the AST walk reads **0 / 0**; the guard fails on a reintroduced deep import and on a
  reintroduced package-root import (both mutations recorded); `docs/architecture/EXCEPTIONS.md`
  is not touched — no waiver.
- **Required tests:** the new guard; `.venv/bin/python -m pytest tests/contract -q`;
  `make gate`; `git diff --check`; a diff that changes only import lines, new `public.py` files,
  the guard and the two documents.
- **Sequence:** after `W48-DURABLE-FIX-2` and `W48-TAILS` are merged, because it rewrites import
  lines in `runs`, `storage`, `analysis`, `ingest` and `norms/__main__.py`.

### `W48-JUDGE-Z` — judge of the merged closure line

- **Subject:** `integration/w48-close` after DURABLE-FIX-2, GUARDS-2 and TAILS are merged.
  **Allowed path:** `docs/program/reviews/W48-JUDGE-Z.md`.
- **Brief:** re-run every mutation listed under GUARDS-2 independently; inject one unknown value
  into each T-1 site; confirm each DJ-R item upheld by JUDGE-2 is closed by a test that fails
  when the fix is reverted; run the ALR-05 AST walk independently and reintroduce one deep import
  to prove the new guard red; verify `contracts/**` and root locks are byte-identical to
  `6118e66` and that `W48-PUBLIC-01` changed nothing but imports, public modules, the guard and
  two documents; verify migration head is `0014_durable_analysis_effects` on a fresh database.
- Judges own report files only.

### `W48-INT-CLOSE` — gate, register, publish to `dev`

- **Allowed paths:** `integration/w48-close` merges, `docs/program/CURRENT_STATE.md`,
  `docs/program/DEBT_REGISTER.md`, `docs/program/dispatch/PORT_REGISTRY.md`,
  `docs/program/W48-INT-CLOSE.md`, `origin/dev`.
- **Steps:** merge in the order of §5; full `make gate` on the exact candidate with the real
  corpus attached; register the debts of `IDENTITY-WAVES.md` §7 with their check commands;
  rewrite the live section of `CURRENT_STATE.md` (W48 closed on `dev`, W49 withdrawn, next is
  `IDENTITY-WAVES.md`, migration head named by command not by sentence where the guard allows);
  release the W48 port rows; fast-forward `origin/dev`; remove the merged worktrees only after
  the push is verified (`git ls-remote origin dev` equals the candidate); keep the backup refs
  until `alpha-w48` or the owner's say-so.
- **Required evidence:** literal `GATE OK` tied to the SHA; counts by test id against the
  `W48-FREEZE-01` baseline (backend 2641 / 5 skipped, frontend 1162 in 82 files) with every delta
  explained; `git status --porcelain` empty; `git diff --check`.
- **Stops here** and hands over to `W48-MAIN-01`.

### `W48-MAIN-01` — publication to `origin/main`, auto-deploy, live acceptance, `alpha-w48`

- **Preconditions, each proven before the first step:** `W48-INT-CLOSE` done and `origin/dev`
  equals the candidate; the owner's **direct instruction naming the exact candidate SHA** for
  `origin/main` (P-7 is the intent; this task asks for the instruction quoting the SHA and does
  not proceed on "continue"); the provider credential placed by the owner in the host's
  `provider.env` (`D-70`) — the executor never sees, copies or records it; `origin/main` re-read
  and still `608632a`, the candidate its fast-forward descendant; `make gate` evidence for the
  exact SHA; `MAIN_AUTODEPLOY_POLICY.md` read in full.
- **Steps:** `W48-PLAN.md` §12 items 5–8 exactly: fast-forward `origin/main`; wait for the
  serialised workflow run and require success; host-side `infra/deploy/verify-deployed.sh` for
  the triggering SHA; public preflight, PC-01 browser journey and refusals, manual A01–A12 with
  `provider_mode=live`, 3/3 writes, 16/16 routes, no auth/console failures, no unexplained
  `BLOCKED`; only then the annotated tag `alpha-w48` at that exact commit.
- **Allowed paths:** `origin/main` (one fast-forward), the tag, `docs/program/W48-MAIN-01.md`,
  `docs/program/CURRENT_STATE.md` (the "last closed release" sentence), `docs/program/CHECKPOINT_REGISTRY.md`,
  `docs/program/dispatch/PORT_REGISTRY.md` (release of the integration lane).
- **Stop conditions:** the workflow fails or the host verification disagrees → no tag, no
  follow-up push; the repair is a new gated candidate through `dev`. Any manual step `FAIL` or
  unexplained `BLOCKED` → no tag. The instruction names a different SHA than the gated candidate
  → stop and ask.
- **Evidence:** workflow run id and attempt, exact SHA, host verification output, the
  acceptance report path, the tag object. No credential, cookie or provider body in any of it.

## 5. Integration order

1. `W48-SAFE-01`, then `W48-RULE-01` (owner confirmation of `R-53`/`R-54` text is the gate).
2. `W48-DURABLE-JUDGE-2` on `411c6d0`.
3. `W48-DURABLE-FIX-2` from `411c6d0`; in parallel `W48-GUARDS-2` and `W48-TAILS` from
   `03c04a1` (`agent/w48-stage-a`), because their paths are disjoint from the durable slot.
   `W48-TAILS` owns the only `globals.css` edit of this stage.
4. Merge into `integration/w48-close`: DURABLE-FIX-2, GUARDS-2, TAILS. No semantic resolution
   inside merge commits.
5. `W48-PUBLIC-01` from the merged SHA; merge.
6. `W48-JUDGE-Z`. Upheld release-blocking findings reopen one bounded `W48-FIX-C` slot with an
   explicit path grant; otherwise proceed.
7. `W48-INT-CLOSE` — exits at `origin/dev`.
8. `W48-MAIN-01` — only on the owner's direct instruction naming the exact SHA.

## 6. Ownership matrix

| Hotspot / path family | Owner | Parallel writer |
| --- | --- | --- |
| `db/migrations/versions/20261002_0014_*` | `W48-DURABLE-FIX-2` only if JUDGE-2 upholds a schema defect | none |
| `contracts/**`, root locks, composition | frozen | none |
| `web/src/app/globals.css` | `W48-TAILS` | none |
| `web/tests/guards/**` named files | `W48-GUARDS-2` | none |
| `web/src/widgets/**`, `web/src/entities/**`, `web/tests/unit/**` | `W48-TAILS` | none |
| `tests/contract/**` named files, `scripts/manual-alpha-check.sh`, `tests/e2e/pc01/journey/verify-acceptance.mjs` | `W48-GUARDS-2` | none |
| `src/auditmanager/{jobs,runs,storage}/**`, `ingest/reconciliation.py`, `analysis/text/**`, `norms/__main__.py` | `W48-DURABLE-FIX-2` | none |
| `OWNER_RULINGS_2026-09-17.md`, W48-PLAN addendum | `W48-RULE-01` | none |
| `src/auditmanager/*/public.py`, import lines of every cross-context importer, `api/composition.py`, the ALR-05 guard | `W48-PUBLIC-01` (after step 4 of §5) | none |
| `CURRENT_STATE.md` (one sentence) | `W48-TAILS`; the live section rewrite is `W48-INT-CLOSE` after TAILS merged | sequential |
| `DEBT_REGISTER.md` | `W48-TAILS` (D-52, A-03 rows), then `W48-INT-CLOSE` | sequential |
| `origin/dev` | `W48-INT-CLOSE` | none |
| `origin/main`, `alpha-w48`, `CHECKPOINT_REGISTRY.md` | `W48-MAIN-01`, only after the owner's direct instruction naming the exact SHA | none |

## 7. Stop conditions

Those of `W48-PLAN.md` §14, plus:

- the owner does not confirm `R-53`;
- `W48-DURABLE-JUDGE-2` finds that a crash still loses a paid attempt or an object with no
  reconciliation path — then DURABLE-FIX-2 widens only by an explicit new grant;
- a repair needs a contract, error-code or `0014` schema change the judge did not uphold;
- any backup ref disagrees with its branch tip;
- a gate is observed running in a worktree this stage does not own.

## 8. Judging and evidence

Two judges: `W48-DURABLE-JUDGE-2` before the repair, `W48-JUDGE-Z` after the merge. Each is a
fresh context; neither is an author of what it judges. Reports carry subject SHA, environment,
commands with exit status, findings with path/line/consequence/reproduction, mutation results,
untested questions, verdict, and `git diff --name-only <subject>..HEAD` proving report-only.

## 9. `alpha-w48` and `origin/main`

P-7 (2026-10-05): the owner will supply the provider credential and the direct `origin/main`
instruction, so the tag is in scope and `W48-MAIN-01` owns it. Two things stay true regardless:
the instruction must name the exact gated SHA and arrives after `W48-INT-CLOSE` has produced it
(`AGENTS.md` §6: "continue" and "close the wave" are not that instruction); and the credential
lives only on the host. If either does not materialise, the stage still exits complete at
`origin/dev` and `W48-MAIN-01` waits — nothing in §4 before it depends on it.

## 10. Non-goals

No new product behaviour; no normative corpus work; no version endpoint; no workflow or deploy
script change; no `origin/main` publication outside `W48-MAIN-01`; no change to the frozen
`6118e66` contract set.
