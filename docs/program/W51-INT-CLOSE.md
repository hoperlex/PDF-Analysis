# W51-INT-CLOSE — accelerated development implementation closure

**Date:** 2026-10-08. **Verdict:** W51 implementation is closed on the development
line under the owner's accelerated-close direction. This is a code and documentation
milestone, not a QA, release, deployed-state or `origin/main` verdict. D-137 and
D-138 remain open and release-blocking. This report is part of the close commit,
so its exact SHA and `origin/dev` read-back belong in the integrator handoff.

## Accepted lineage

| Stage | Accepted commit | Result |
| --- | --- | --- |
| W50 frozen base | `75dd708` | W51 entered with the existing identity contract set and migration head |
| W51 Stage A | `bc5d443` | Route placeholders, registry and shared route/API exports |
| W51 Stage B AUTH | `ebe614d` | Sign-in, registration, account and password screens |
| W51 Stage B ADMIN-USERS | `c88e794` | User list, detail and account administration |
| W51 Stage B ADMIN-REQUESTS | `4442921` | Registration queue and decision screens |
| W51 Stage C | `4400e81` | PC-01 identity journey code and manual A13–A20 pack |
| Later W51 web correction | `2c2e7d8` | `W52-INT-HOTFIX-BACKPORT-01` carried the correction onto `dev`; it does not supply QA or gate evidence |
| Pre-close development base | `5a25e07956459f510addf1f142ec8a4c26591111` | Clean published `origin/dev`, including separate W52 code preparations not attributed to W51 |

The W51 implementation and acceptance *code* are present. The browser/API
identity journey and human manual steps have not been accepted on a built stand.
The Stage-B lane reports retain the red rendered-language branch-coverage
observation; the later hotfix has its own focused green result. Historical
reports are not rewritten by this closure.

## Checks and validation boundary

The clean pre-close code candidate `5a25e07` passed:

| Command | Result |
| --- | --- |
| `npm --prefix web run lint -- --quiet` | pass |
| `npm --prefix web run typecheck` | pass |
| `npm --prefix web test -- --run` | 109 files, 1712 tests passed |
| `.venv/bin/pytest -q tests/e2e/test_pc01_journey_conformance.py tests/contract/program/test_wave_governance.py tests/contract/api_v1/test_doc_prose_facts.py` | 142 passed |
| `.venv/bin/pytest -q tests/contract/test_domain_identifiers_schema.py tests/contract/domain_p02/test_contract_vocabulary.py tests/contract/domain_p02/test_openapi_document.py tests/contract/api_v1/test_openapi_conformance.py` | 165 passed |
| `bash -n scripts/manual-alpha-check.sh`; `shellcheck scripts/manual-alpha-check.sh` | pass |

The first Vitest attempt in the restricted sandbox had six guard failures caused
by nested `eslint`/`tsc` `spawnSync ... EPERM`; 1706 other tests passed. Repeating
the same command with permitted subprocess execution passed all 1712 tests.
That first result is an environment restriction, not acceptance evidence for a
product failure. The clean docs-only close commit receives a repeat of basic
checks and an exact changed-path review before publication; the handoff records
its SHA and results.

No temporary stand was started. `W51-QA-01`, independent X/Y review, their
cross-examination, built-stand PC-01, human A13–A20, release acceptance and a
full `make gate` were deferred by the owner. The earlier diagnostic
`W52-INT-VALIDATE-01` full gate on `e2cfea92` did not produce `GATE OK`;
later basic green checks do not close that obligation.

| Debt | Still required before a W51 release verdict |
| --- | --- |
| D-137 | QA, independent review, built-stand identity journey and human/manual acceptance on a named exact candidate, then disposition and correction of findings |
| D-138 | Complete `make gate` with literal `GATE OK` on the exact clean release candidate after correction |

W52's own deferred evidence remains under D-139/D-140; this W51 closure does not
freeze W52 or waive any W52 entry condition.

## Contract and publication boundary

The frozen domain candidate remains `1.0.0-draft.1`, revision 9 with 29 opaque
identities; API 27 paths / 34 operations / 77 schemas; error catalog 23;
migration head `0015_accounts_roles_registration`. The protected-path check
`git diff --name-only 75dd708 HEAD -- contracts db/migrations` was empty on the
pre-close development base. This documentation close has no contract, migration,
dependency, lockfile, composition-root, global-style or product-code change.

Only the exact clean docs-only close commit may be fast-forwarded to `origin/dev`
after basic checks, remote-ref re-read and ancestor proof. No tag or `origin/main`
push is authorized. Future release publication needs a separate direct owner
instruction and the exact-candidate validation above.

## Risks, rollback and integrator instruction

D-137/D-138 are the known release blockers. A future validation wave may find
new defects and require correction before the gate. Revert the close
documentation commit if its development status is wrong; there is no feature
flag or product behavior to roll back.

**Changed files:** `docs/program/tasks/W51-INT-CLOSE.md`, this report,
`docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`, and
`docs/program/dispatch/W51-PLAN.md`. **New/changed contracts:** none.
**Integrator instruction:** check the exact clean close commit, publish only
that SHA to `origin/dev` by fast-forward, read it back, and record SHA/checks
in the ignored integrator handoff. **Forbidden-hotspot proof:** the close
commit's path diff against `5a25e07` must be exactly a subset of those five
documentation files; protected contract/migration diff remains empty.
