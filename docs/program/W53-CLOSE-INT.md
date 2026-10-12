# W53-CLOSE-INT — integration record of the debt and findings closure wave

**Integrator:** session `pdf-analysis-62`, 2026-10-12. **Authority:** owner rulings `R-80`…`R-84`
(`OWNER_RULINGS_2026-09-17.md` §3.28). **Plan:** `dispatch/W53-CLOSE-PLAN.md`, commit `04de50c` on
`integration/w53-close`, which was cut from `origin/dev` `872266038a83568b56f6302f01b97771b9aaf281`.

## 1. Lanes and merges

| Lane task | Agent tip | Merge | Findings |
|---|---|---|---|
| `W53C-WEB-OPS-01` | `f79b196` | `fbc00a5` | C-26…C-30 closed. C-30 was narrower than reported: only a reused page could record a stale count. |
| `W53C-STORE-01` | `f35db90` | `40145f6` | C-12…C-14 closed. C-12 was reproduced end to end on the base. |
| `W53C-EXEC-01` | `d4d641d` | `ebbd01d` | C-01…C-04 and C-06 closed. C-05 is partial and continues as `D-150`. |
| `W53C-EDGE-01` | `184007c` | `9d2e210` | C-15…C-19 closed. The integrator sent C-19 back once: a failed `getMe` after editing another account now keeps the session. |
| `W53C-IDENTITY-01` | `13cabae` | `874d480` | C-07 (API half) and C-08…C-11 closed. |
| `W53C-WEB-ID-01` | `6ac2a97` | `8dd3f9e` | C-07 (screen half) and C-20…C-25 closed. |

Before each merge the integrator read `git diff --name-only 04de50c <agent tip>` against the
task's allowed paths. Every changed path was inside them, or was a test or guard pinning a file
the lane owned. Each lane's report is `docs/program/W53C-*.md` and carries the six `AGENTS.md`
§5 items. The only shared file was `src/auditmanager/bootstrap/adapters.py`, split by class;
it merged without conflict.

## 2. Behaviour changes the owner should know

- `R-80`: an account without roles gets `403 permission_denied` (`required_capability:
  role:admin|expert`) on all 15 product reads. The screen registry gains `'any-role'`, and a
  role-less account sees only the home page, its own account screens and release history.
- C-10 reverses a deliberate W40-LIMIT behaviour. A wrong current password in `changePassword`
  now counts against the per-account brake. A locked account can no longer reopen itself by
  changing its password: it waits up to 300 s or an operator runs `access.unlock`. Restoring
  the old behaviour would need a ruling.
- C-17: the BFF no longer reads `AUDITMANAGER_API_TOKEN` for the three open operations.
  Removing the variable from the web container is a later compose change.
- C-18: the edge sends `nosniff`, `X-Frame-Options: DENY`, `frame-ancestors 'none'` and
  `Referrer-Policy: same-origin`. `tls-server.conf` adds HSTS for one year.

## 3. Light acceptance (`R-84`) on the merged tree `8dd3f9e`

| Check | Result |
|---|---|
| `npm --prefix web run lint` | exit 0 |
| `npm --prefix web run typecheck` | exit 0 |
| `cd web && npx vitest run` | **123 files, 1850 tests passed** |
| `pytest tests/contract tests/e2e/test_pc01_journey_conformance.py`, without the three `cp00`/bootstrap modules | **636 passed**, 50 subtests |
| private lane `gate-w53c-int` (PostgreSQL 57010, S3 60610/60611), migrated to `0017_execution_queue`: `pytest tests/integration/{access,auth,api,runs,analysis_text,ingest,releases,qa_w53,composition}` | **1681 passed, 1 skipped, 1 failed** in 600 s |
| the failed module rerun alone, same lane | **13 passed** |

The one failure is
`test_serving_lifespan_dispatches_an_ordinary_run_adapter_submission`. It is order-sensitive to
queued Jobs that earlier suites leave behind (`D-152`). `W53C-EXEC-01` observed the same
failure and the same rerun result.

Three modules were left out of the container-free run: `test_cp00_candidate.py`,
`test_cp00_final_state.py` and `test_validate_bootstrap.py`. They fail in any linked worktree
for environmental reasons: `.git` is a file there, and the bootstrap interpreter has no
`jsonschema`. Lanes measured the same 70 failures and 126 errors on the base `04de50c`, so
these are not regressions. Their verdict belongs to the next full `make gate`.

**No full `make gate` was run.** `R-84` waives it for this `origin/dev` publication.
`R-70`'s full gate is still required before `origin/main`, and this candidate changes
`infra/deploy/proxy/**`. The private lane's containers and volumes were removed after the run.

## 4. Deferred

`D-141` … `D-152` in `DEBT_REGISTER.md`. Still open from W53: `W53-EXEC-STOP-01`,
`W53-EXEC-STOP-02`, Y-04 and `W53-RELNOTES-STOP-01`. The release and validation obligations
`D-137` … `D-140` remain open as well.

## 5. Publication

Target: `origin/dev`, as a fast-forward from `8722660`. There is no `origin/main` authority,
no tag and no `VERSION` change.
