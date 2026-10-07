# W50-FIX — light acceptance and accepted shell corrections

**Subject:** `256e24e1d1eff61dabd3a244cef0b89d12019b41` (the merged W50 shell and judges).
**Lane:** `agent/w50-fix`, disposable `gate-w50fix` services. **Date:** 2026-10-07.
**Verdict:** Complete. The final committed tree passed the full gate with its literal `GATE OK` sentinel. The exact commit SHA and cleanup confirmation accompany the handoff.

## Changed files

| Path | Change |
| --- | --- |
| `Makefile` | Added only the R-70 `light-acceptance` target and its phony name; the existing `gate` recipe is byte-identical. |
| `scripts/light_acceptance.py` | Requires an explicit full ancestor `BASE`, a clean measured tree, and a classified `BASE..HEAD` diff. It runs common checks, impacted integration directories, and the live journey when selected; it refuses risk and unknown paths. |
| `tests/contract/test_light_acceptance_command.py` | Synthetic committed diffs cover docs-only, backend, screen, Makefile risk, and unknown backend/screen paths, plus missing/non-ancestor/dirty bases. |
| `web/tests/guards/lazy-boundary.guard.test.ts` | Raised the census floor from 80/150/150 to the measured merged 90/171/171. |
| `web/src/shared/lib/routes.ts`; `tests/e2e/pc01/journey/journey.mjs`; `tests/e2e/pc01/journey/README.md`; `web/src/app/bff/session/store.ts`; `web/tests/guards/prepared-sections.guard.test.ts` | Corrected the granted live comments, route/landing/count prose and guard titles only. |
| `tests/e2e/pc01/journey/fixtures/redden-write.manifest.json`; `tests/e2e/pc01/journey/fixtures/redden-write-bound.manifest.json` | Aligned root read expectations with the real home screen while keeping deliberate negative write controls. The bound fixture's neighboring stale root `$comment` was authorized by the integrator's task-grant correction `a21a0df`. |
| `docs/program/W50-FIX.md` | This evidence and handoff report. |

## Checks and results

- `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`: exit 0, `bootstrap OK`; pinned runtime and validation environments. The first sandboxed attempt could not reach the package index, so the same command was run with the needed network permission.
- `npm --prefix web ci`: exit 0, 184 pinned packages. The first sandboxed attempt could not spawn esbuild (`EPERM`); the exact retry with execution permission passed.
- `npm --prefix web test -- --run tests/guards/lazy-boundary.guard.test.ts`: exit 0, 24 passed; a temporary measurement line printed `screens=90 light=171 dark=171` and was removed. With a temporary one-count reduction of `counts.screens`, the same command exited 1: `expected 89 to be greater than or equal to 90`; restored before handoff.
- `npm --prefix web test -- --run tests/guards/lazy-boundary.guard.test.ts tests/guards/prepared-sections.guard.test.ts`: exit 0, 42 passed.
- `.venv/bin/python -m pytest -q tests/contract/test_light_acceptance_command.py`: exit 0, 9 passed, including BFF screen-lock and sign-in route diffs.
- `.venv/bin/python -m pytest -q tests/e2e/test_pc01_journey_conformance.py tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`: exit 0, 148 passed.
- `npm --prefix web run lint -- --quiet`: exit 0. `npm --prefix web run typecheck`: exit 0.
- The two fixture root `expects_api` and `optional_api` arrays equal the production manifest's root arrays exactly (Python JSON assertion, exit 0).
- `make up`, `make migrate`, `make check-db`, `make check-services`: exit 0 on instance `gate-w50fix`, database `auditmanager_w50fix`, bucket `gate-w50fix`, ports 56750/60350/60351. Database head was `0015_accounts_roles_registration`; check sentinels were present. Host `ss -ltn` showed all reserved ports free immediately before use. `flock ... npm --prefix web run build` exited 0 with 22 UI routes. The API and web production processes used checked loopback ports 56850/56851/31350 and were stopped by their verified PIDs after the fixture probes.
- Live `e2e:pc01 --phase write` against each negative fixture on that production stand: both signed in. `redden-write` exited 1 with six intended create-project findings (wrong status, undeclared call, impossible rendered sentence, etc.); `redden-write-bound` reached all three steps and exited 1 with four intended start-run findings, including the 1 ms terminal bound and wrong status/state. An initial relative-manifest invocation and a second invocation without an explicit Chrome path stopped before the fixture and were discarded as setup failures. Temporary credential and journey artifacts were removed.
- `git diff --check 86659c6..HEAD`: exit 0. The task's shorthand `make light-acceptance BASE=eb1539a` exited 2 because the command requires a full SHA. `make light-acceptance BASE=eb1539abb69d38a5f1fce2a8ee5369ae1f0fc3b1` then exited 2 with the explicit `complete make gate required` refusal for the changed `Makefile`, as R-70 requires.
- A pre-final gate on `2e7e497` was cancelled at 20% of the battery (exit 143, no `GATE OK`) after review found that BFF redirects were omitted from screen selection. It was stopped by its verified PIDs, with no child left running, before this correction. The first gate on `f2098c4` exited 2 after 3,200 passing battery tests, six skips and one environment failure: the exact real corpus was absent at `.local/norms/corpus` in this linked worktree. The shared root corpus existed; an ignored symlink in this disposable lane exposed those exact bytes, without changing the tracked tree. The failed test alone then passed (`1 passed in 4.24s`). Neither incomplete run supplied `GATE OK`.
- `make gate` on the final clean tree: exit 0; last line `GATE OK: battery, foundation, frontend lint/typecheck/tests and whitespace all pass`.

## Contracts, risks, and integration

No API, domain, migration or persisted contract changed. The frozen API remains 27 paths / 34 operations / 77 schemas, error catalog 23, domain revision 9 with 29 opaque identities, and migration head `0015_accounts_roles_registration`. Product behavior is unchanged.

The selector intentionally refuses a new backend context, an unknown `web/src` layer, or a missing/empty required suite until the mapping is reviewed. It conservatively treats known screen-affecting frontend source, including the BFF session guard and sign-in redirect route, as requiring the live PC01 journey. The live journey requires an explicit loopback origin and credentials for the lane's own stand; a caller must still operate that stand. The fixture browser probes exercised their write phases; the root read expectations were checked structurally against the production manifest and are also covered by the static journey conformance suite.

The full gate's norms fixture requires the exact local real corpus at `.local/norms/corpus`; a fresh linked worktree needs access to that external input. No tiny fixture or silent skip was used.

The integrator may grant-check this branch against `W50-FIX` plus task-grant correction `a21a0df`, merge without a semantic conflict, and run post-merge R-70 acceptance. This lane owns no publication, tag or deployment. Rollback is a revert of the W50-FIX commit. No checkpoint was created.

The grant proof is `git diff --name-only 86659c6..HEAD`: it names only the paths in the table above. In particular `contracts/**`, `db/migrations/**`, `infra/**`, dependency/lock files, composition roots, global styles, other worktrees and deployment refs were not changed. The only R-70 full-gate risk path changed is the task-granted `Makefile`; its original `gate` recipe was preserved.
