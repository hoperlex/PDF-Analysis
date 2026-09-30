# W47-CLOSE — wave 47 release-candidate closeout

**task_id:** `W47-CLOSE` · **base:** `b0e5ae5` · **date:** 2026-09-30

## Result

Wave 47's runtime/product candidate is unchanged. The canonical gate now includes frontend
lint, the tree is lint-clean, the stale PC-01 migration/count claims and their allow-list entry
are gone, and the live state/debt register agree with the gated candidate.

This is the closeout task, not the integration task: it creates no tag and changes no remote
ref. A following `W47-INT-CLOSE` may publish only the accepted closeout tip.

## Changes

- `Makefile`: `run_frontend` runs lint before typecheck and tests; any lint failure prevents the
  final `GATE OK` sentinel.
- `web/tests/guards/query-key-shape.guard.test.ts`: the existing command-surface guard pins all
  three frontend checks and their fail-fast order.
- `web/tests/guards/dashboard-invalidation.guard.test.ts`: two U+200B characters in comments
  were replaced with ordinary `<feature>` prose; no test/runtime logic changed.
- `docs/manual-tests/PC-01_prototype.md`: live migration head is `0011_document_section` and
  live operation references are 20.
- `tests/contract/api_v1/test_doc_prose_facts.py`: `KNOWN_OUTSTANDING_CLAIMS` is empty and a
  test pins that absence.
- `docs/program/DEBT_REGISTER.md`: D-76, D-101, D-103 and D-118 are closed; the already-fixed
  D-80 and D-102 statuses are reconciled. Owner-held and wave-48 rows remain open.
- `docs/program/CURRENT_STATE.md`: wave 47 is the live closeout candidate; wave 46 moved behind
  the historical boundary.

## Non-vacuous lint proof

The `run_frontend` function was exercised with an isolated fake `npm` which returns non-zero
only for `--prefix web run lint`. The function returned non-zero and the trace contained exactly
that one call: neither typecheck nor tests ran. The repository was not mutated for this proof.

The static companion is the 11-test `query-key-shape.guard.test.ts` run: it reads the real
Makefile, requires lint/typecheck/tests, and requires their order.

## Verification

| Check | Result |
|---|---|
| `npm --prefix web run lint` | exit 0, 0 errors |
| `npm --prefix web test -- --run tests/guards/query-key-shape.guard.test.ts` | 11 passed |
| documentary prose guards | 47 passed |
| `git diff --check` | exit 0 |
| isolated fake-npm lint refusal | refused at lint; 0 later calls |
| serial `make gate` | `GATE OK`; foundation 35; battery 2604 passed / 5 skipped / 4 warnings / 169 subtests; frontend 1162 passed in 82 files |

Full gate log: `/root/w47-close-gate.log`.

## Frozen contracts

- API: 17 paths / 20 operations / 61 schemas;
- API SHA-256: `f043eb6c3a5bbba3cb95fff59039fff42582c79ae0dc8ff2ba261e2cb4583585`;
- domain error catalog: 22 codes;
- migration head: `0011_document_section`.

No contract, generated consumer, migration, dependency/lock file, runtime source, composition
root, deployment script or global style is changed by this task.

## Changed files

- `Makefile`
- `web/tests/guards/dashboard-invalidation.guard.test.ts`
- `web/tests/guards/query-key-shape.guard.test.ts`
- `docs/manual-tests/PC-01_prototype.md`
- `tests/contract/api_v1/test_doc_prose_facts.py`
- `docs/program/DEBT_REGISTER.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/dispatch/W47-CLOSE.md`
- `docs/program/W47-CLOSE.md`

## Risks and known limitations

- This closeout does not repeat the live browser journey because no runtime path changed. The
  retained wave-47 evidence is 3/3 writes, 16/16 routes, 0 auth failures and 0 console failures.
- D-70 remains a deployment precondition: the hostless stub provider URL cannot start the API.
  The development stand needs a reachable provider endpoint and real credential.
- Owner-held product decisions and D-104 through D-117 remain open as recorded. In particular,
  the live journey is still not part of `make gate` (D-108).
- No claim is made here about what is currently deployed; `infra/deploy/verify-deployed.sh`
  measures that external state.

## Integrator handoff

1. Confirm the worktree is clean and the accepted commit contains only the nine paths above.
2. Re-read the literal `GATE OK` line in `/root/w47-close-gate.log` and the frozen values above.
3. Open a separate `W47-INT-CLOSE` task before creating `alpha-w47` or moving remote refs.
4. Fast-forward the intended integration refs, including `main`, to the exact accepted tip; do
   not merge a later runtime change into the tag.
5. Treat development deployment as a following operator action after D-70's endpoint/credential
   precondition is supplied, then run the publication-readiness and deployed-tree checks.

Rollback is one closeout commit, but it deliberately reopens D-76 and D-118 and is not a valid
release candidate. There is no feature flag because runtime behaviour is unchanged.
