# Task W50-FIX — close the shell wave's accepted integration obligations

## Outcome

The W50 shell's recorded prose matches its implemented routes, the contrast census is pinned to
the accepted merged tree, and `make light-acceptance BASE=<sha>` executes the R-70 checks selected
from an explicit last-full-gate base. The existing `make gate` keeps its full behavior.

This task closes obligations assigned before the judges by `W50-PLAN.md` (integrator rulings
at the REGISTRY and Stage-C merges) and the owner's R-70. Both judges found **no upheld
release-blocking finding**; their register-only findings are for the integrator's debt register,
not product changes in this task.

## Depends on

- `W50-QA-01`, `W50-JUDGE-X`, `W50-JUDGE-Y` — completed and merged at `256e24e`.

## Frozen inputs

- Base subject: `256e24e1d1eff61dabd3a244cef0b89d12019b41` on `integration/w50` and
  `origin/dev` when dispatched.
- Last tree proven by a complete integration gate: `eb1539a` (Stage-C merge); the new target
  must take its base explicitly and may not silently assume this SHA for future waves.
- API: 27 paths / 34 operations / 77 schemas; error catalog: 23; domain revision 9 / 29 opaque
  identities; migration head: `0015_accounts_roles_registration`. All frozen.
- R-70: `AGENTS.md` §8 and `OWNER_RULINGS_2026-09-17.md` §3.25.
- W50-PLAN integrator rulings at REGISTRY merge item 5 and Stage-C merge item 1.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the merged census exceeds its old pin, and the command surface has no R-70 target

### P-01 — accepted merged census is above its guard's old pin

- captured_at: 2026-10-07
- command: `rg -n 'const BASELINE' web/tests/guards/lazy-boundary.guard.test.ts`
- captured_output:
  ```text
  448:const BASELINE = { screens: 80, pairsLight: 150, pairsDark: 150 } as const;
  ```
- interpretation: the guard still pins the pre-wrapper floor. `W50-JUDGE-Y.md` independently
  measured 90 screens / 171 light / 171 dark on the merged subject; Stage-C ruling accepts the
  one removed bar-only pair. Re-measure before changing the pin.

### P-02 — the command surface has no light target

- captured_at: 2026-10-07
- command: `rg -n '^light-acceptance:|^\.PHONY:' Makefile`
- captured_output:
  ```text
  141:.PHONY: bootstrap up down check-services migrate check-db check-storage test-foundation gate mutation-copy foundation alpha-acceptance
  ```
- interpretation: `R-70` requires a new target; the full gate is present and must remain intact.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/dispatch/W50-PLAN.md`
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `Makefile` — add only the R-70 light-acceptance command; preserve `gate` and all frozen targets
- `scripts/light_acceptance.py` (new, if needed for exact diff classification)
- `tests/contract/test_light_acceptance_command.py` (new)
- `web/tests/guards/lazy-boundary.guard.test.ts` — raise the measured census floor only
- `web/src/shared/lib/routes.ts` — stale route comment only
- `tests/e2e/pc01/journey/journey.mjs` — stale redirect comment only
- `tests/e2e/pc01/journey/README.md` — stale route/count/landing prose only
- `web/src/app/bff/session/store.ts` — stale legacy `openSession` docstring only
- `tests/e2e/pc01/journey/fixtures/redden-write.manifest.json` — stale `$comment` and root read expectation only
- `tests/e2e/pc01/journey/fixtures/redden-write-bound.manifest.json` — root read expectation
  and its adjacent stale `$comment` describing `/` as a redirect to `/projects` only
- `web/tests/guards/prepared-sections.guard.test.ts` — stale title/comment count only
- `docs/program/W50-FIX.md` — completion report

## Forbidden hotspots

- Everything else, especially `contracts/**`, `db/migrations/**`, `infra/**`, dependency/lock
  files, composition roots, global styles, product behavior, registered addresses, actual
  deterministic evidence, planning branches, refs, tags, and deployment.

## Non-goals

- No behavior change, API change, new route, UI copy change, or repair of register-only judge
  findings. Do not remove any historical evidence; correct only live descriptions granted above.
- Do not weaken, rename, or bypass `make gate` or its `GATE OK` sentinel.

## Deliverables

- `make light-acceptance BASE=<full ancestor SHA>` runs `git diff --check`, frontend lint,
  typecheck and full tests, canonical contract tests (the three historical CP-00/bootstrap files
  remain excluded exactly as in `run_battery`), and static PC01/prose guards. It derives changed
  backend contexts and changed rendered screens from `BASE..HEAD`; a backend context invokes its
  exercising integration directory, and a changed screen invokes the live PC01 journey on the
  lane's own stand. It must fail clearly if a required stand, suite or mapping is unavailable.
  A touched R-70 risk path must explicitly require a complete `make gate` and may not be silently
  accepted by this target. Reject missing/non-ancestor base and a dirty measured tree.
- Tests prove the selector with synthetic diffs: docs-only, backend context, screen, risk path,
  and unknown context/screen; they prove no silent skip and no substitution for the full gate.
- Raise `BASELINE` only to the measured merged count, with a one-count-down mutation going red.
- Correct the exact stale prose in W50-PLAN's REGISTRY ruling item 5 without changing the
  negative fixture's purpose; verify the fixture remains a deliberate red control.
- A report with changed files, commands and exact results, mutations, contract state, known
  limitations, and forbidden-hotspot proof.

## Required tests

- `git diff --check <base>..HEAD`; targeted tests for new command and changed guards/fixtures.
- `make light-acceptance BASE=eb1539a` on a committed clean lane tree, including its selected
  checks; if the target says the current Makefile requires a complete gate, that signal is
  expected and the required gate below supplies the acceptance.
- Because this task touches `Makefile`, one complete `make gate` on the lane's final exact tree,
  with literal `GATE OK`; the integrator will repeat light acceptance after merge.

## Integration contract

Hand back a clean `agent/w50-fix` branch and exact SHA. The integrator grant-checks every file,
merges without semantic conflict, verifies the Makefile's full gate on the lane SHA, runs
post-merge R-70 acceptance, and alone may advance `origin/dev`. Any needed path outside this
grant is a finding to the integrator, never a silent edit.

## Failure/idempotency/security cases

- Dedicated lane `gate-w50fix`: PostgreSQL `56750`, MinIO `60350/60351`, unique database and
  bucket; check every port free immediately before use. `PORT_REGISTRY.md` reserves this row.
- One full gate on the shared host at a time. Check available memory (at least 3 GB) and no
  other gate before build/gate. Do not edit the measured tree while a suite runs.
- Use only the executor's disposable lane; stop only confirmed-own PIDs and remove only its
  containers, volumes, temporary credentials and clones. No secrets in reports.
- An environment failure is recorded as void, not a product pass. No test command may return a
  false green when it ran nothing.

## Rollback / feature flag

Revert the commit; this is command/instrument/prose correction, with no product flag.

## Handoff

- changed files and grant-check output
- commands/results, including exact `GATE OK` line and mutations
- new/changed contracts: none expected
- known limits and integration instructions
