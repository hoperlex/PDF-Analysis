# Task W47-CLOSE — close the gated wave-47 candidate without changing its product surface

**task_id:** `W47-CLOSE` · **wave:** 47 closeout · **base:** `b0e5ae5` ·
**branch:** `agent/w47-close`

## Outcome

The canonical `make gate` runs the already-declared frontend linter, the two lint errors it
previously ignored are gone, `D-76` has no stale migration-head exemption, and the live state
and debt register describe the gated wave-47 tree. A user can verify the result with one clean
`make gate` and the closeout report.

## Depends on

- `W47-GATE` — complete and merged at `9a9f8c5`.
- `W47-PASS` — complete and merged at `45d784f`.
- `W47-LOCK` — complete and merged at `44937fe`.
- `W47-FIX` — complete and merged at `88757dc`.
- `W47-JUDGE-X` and `W47-JUDGE-Y` — complete and merged at `9ec50a9`.

## Frozen inputs

- domain error catalog: 22 codes, unchanged;
- API contract: 17 paths / 20 operations / 61 schemas,
  SHA-256 `f043eb6c3a5bbba3cb95fff59039fff42582c79ae0dc8ff2ba261e2cb4583585`;
- migration head: `0011_document_section`;
- base commit: `b0e5ae52ebe98372d5d91dd34c999e9939c308c4`;
- measured base gate: `/root/w47-final-gate.log`, `GATE OK`, battery 2604 passed / 5
  skipped, foundation 35, frontend 1162 in 82 files.

## Allowed paths

- `Makefile` — this task is the sole owner of the root command surface for the closeout;
- `web/tests/guards/dashboard-invalidation.guard.test.ts`;
- `web/tests/guards/query-key-shape.guard.test.ts`;
- `docs/manual-tests/PC-01_prototype.md`;
- `tests/contract/api_v1/test_doc_prose_facts.py`;
- `docs/program/DEBT_REGISTER.md`;
- `docs/program/CURRENT_STATE.md`;
- `docs/program/dispatch/W47-CLOSE.md`;
- `docs/program/W47-CLOSE.md`.

## Forbidden hotspots

- `contracts/**` and every generated contract consumer;
- `db/migrations/**` and the migration head;
- root dependency and lock files;
- application composition root, `src/auditmanager/**`, `web/src/**`, and global styles;
- deployment scripts and environment files;
- existing wave and judge reports;
- tags, checkpoints and pushes — those belong to a following `W47-INT-CLOSE` task after this
  task is accepted.

## Non-goals

- Product behaviour, API or schema changes.
- Running the browser journey again: this task changes no screen or runtime path; wave 47's
  16/16-route, 3/3-write journey remains the behavioural evidence.
- Closing the independent wave-48 audit rows or owner-held deployment prerequisites.
- Deployment, publication, tag creation or remote ref changes.

## Deliverables

- lint as an explicit fail-closed step of `make gate`;
- removal of the two irregular-whitespace lint failures;
- current migration-head prose and removal of `D-76`'s exception;
- reconciled debt register and `CURRENT_STATE.md`;
- `docs/program/W47-CLOSE.md` with commands, counts and handoff.

## Required tests

- `npm --prefix web run lint` — exit 0;
- `npm --prefix web run test -- --run web/tests/guards/query-key-shape.guard.test.ts`
  (or the repository-relative Vitest path) — proves the command-surface guard;
- `.venv/bin/python -m pytest tests/contract/api_v1/test_doc_prose_facts.py
  tests/contract/api_v1/test_surface_counts_in_prose.py -q` — no registered `D-76`
  exception and all live prose agrees;
- `git diff --check` — exit 0;
- one serial `make gate`, read from its literal `GATE OK` line, with counts recorded by suite.

Every new or strengthened assertion must be shown able to fail. For the lint step, run the
gate's frontend function with an isolated fake `npm` that fails only on `run lint`, and prove
the function stops before typecheck/tests. Do not mutate the working tree to demonstrate it.

## Integration contract

The following integrator may rely on `make gate` meaning all of: foundation, canonical Python
battery, frontend lint, TypeScript typecheck, complete frontend tests and `git diff --check`.
The API contract, error catalog, migration head and runtime behaviour are byte-identical to
`b0e5ae5` outside the documentation/test/command-surface paths listed above.

## Failure/idempotency/security cases

- Missing `npm` or missing `web/node_modules` still refuses; lint never silently skips.
- A lint failure stops the gate before typecheck/tests and prevents `GATE OK`.
- A stale migration-head sentence is no longer allow-listed.
- Re-running lint, the documentary guards and the gate changes no tracked file.
- No credential or ignored environment file is read or changed.

## Rollback / feature flag

No feature flag: this changes verification and programme records, not runtime behaviour.
Rollback is one commit, but would deliberately reopen `D-118`/`D-76` and therefore is not a
valid release candidate.

## Handoff

- changed files: recorded in `docs/program/W47-CLOSE.md`;
- commands/results: recorded there from literal output;
- known limits: only the owner-held and wave-48 rows retained in the debt register;
- integration notes: a following `W47-INT-CLOSE` may tag/push only this accepted commit or a
  documentation-only state commit verified by the two prose guards and `git diff --check`.
