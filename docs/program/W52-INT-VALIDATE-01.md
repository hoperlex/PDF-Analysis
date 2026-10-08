# W52-INT-VALIDATE-01 — deferred validation baseline

Measured on 2026-10-08 from clean `integration/w51` HEAD and matching `origin/dev`
`e2cfea92e0ba8b7481156ee8eceeefee582ee562`. This report records an attempted
validation, not W51/W52 closure or a release candidate. No tracked source file changed
during measurement.

## Checks and observations

| Check | Result |
| --- | --- |
| First `make gate` | **FAIL** after 35 foundation tests and 3,244 Python passes: the real-corpus fixture was absent at this worktree's ignored `.local/norms/corpus` path. |
| Real-corpus fixture test after linking the existing 674-document corpus | **1 passed**; no substitute fixture was used. |
| Second `make gate` on the same SHA | Foundation **35 passed**; canonical battery **3,245 passed, 6 skipped, 298 subtests passed**; frontend lint **passed**; TypeScript typecheck **failed** with two TS2375 errors. The gate stopped before Vitest and emitted no `GATE OK`. |
| Frontend Vitest, permitted child processes | **1,705 passed, 7 failed** across 109 files. The earlier sandbox-only `EPERM` results are excluded. |
| `git diff --check` and tracked status at measured SHA | Passed; tracked tree clean. |

The two TS2375 errors are at `web/src/_pages/account/ui/account-page.tsx:40`
(`next` may be `undefined` while the recipient's optional prop excludes it) and
`web/src/_pages/register/ui/register-page.tsx:11` (`refusal` has the same mismatch).
They were already recorded against the W52 FACTS dispatch base in D-140; this run
reproduces them on the combined `origin/dev` candidate.

The seven Vitest failures are one `query-key-shape` typecheck assertion reflecting those
two TS errors; one `query-key-shape` assertion finding an explicit type argument in
`web/src/features/manage-user/model/use-manage-user.ts`; one rendered-language guard
finding **17** W51 branch labels without matrix states; and four `login-route` tests whose
expected props omit the now-rendered `unknownRefusal: false`. The real assertion listing
all 17 labels and all seven failure traces is in the local Vitest log.

Logs, preserved under ignored `.local/validation/w52-int-validate-01/`:

- `w51-validation-gate-e2cfea92.log` (first environment failure), SHA-256
  `915a4626ea27e1502d96a42cff8d366ae1148a3f010f77c40694d99c283d6da5`;
- `w51-validation-gate-e2cfea92-corpus.log` (second gate), SHA-256
  `871d333a6368b4256a9178c2e156ae4f14b4a61d20e318f6ab8fa39a3b104294`;
- `w51-validation-vitest-e2cfea92-escalated.log` (authoritative Vitest diagnostic),
  SHA-256 `78fc38ffe8968efc299c6ede3bc0256a8cd4657dc202f6637a0f9f710eac76d8`.

The unique foundation instance `auditmanager-validation-e2cfea92` was stopped with
`make down`; its PostgreSQL and S3 volumes were then removed by exact names. The
ignored `.env` and corpus link remain available for a later local re-run. No temporary
product stand, deployment or live origin was used.

## Deferred-debt status

| Debt | This run proves | Still needed to close |
| --- | --- | --- |
| D-137 | The combined Python battery and frontend lint ran; the W51 language guard is red. | W51-QA-01, independent X/Y reviews, correction, built-stand identity journey, isolated `last_admin` fixture, and human A13–A20 results on one exact candidate. |
| D-138 | Full gate was attempted twice on the W51-containing candidate. | Correct the two type errors, seven frontend failures and any later findings; run a new full gate to literal `GATE OK` on the final clean SHA. |
| D-139 | The W52-containing combined candidate received DB/foundation, corpus and frontend diagnostics. | Inventory each accumulated code-only candidate/acceptance pack; perform independent QA/review and applicable browser/manual/live checks, or record a specific owner disposition for each item. |
| D-140 | A full gate attempt exposed concrete blockers. | Literal `GATE OK` after corrections on the exact candidate proposed for release. |

The PC-01 identity continuation is a separate command from `make alpha-acceptance`; no
identity browser envelope exists from this run. `make alpha-acceptance` needs a writable,
authorized origin, session credentials and matching deployment evidence, and A13–A20 need
human observations. A green hermetic gate alone cannot stand in for those artifacts.

## Handoff

Changed tracked files: `docs/program/tasks/W52-INT-VALIDATE-01.md`, this report,
`docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`. No contract, migration,
dependency/lock, runtime, test, composition-root or global-style path changed. The
integration step may publish this docs-only evidence to `origin/dev` after the
governance/prose checks and exact fast-forward check. It must not label D-137–D-140
closed, tag a release, or update `origin/main`.
