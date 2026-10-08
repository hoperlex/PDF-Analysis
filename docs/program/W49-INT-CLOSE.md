# W49-INT-CLOSE — completion report

## Result

**DONE on `origin/dev`.** W49 — accounts, a role set, registration requests and account
management under `R-55` … `R-61`, plus the owner rulings `R-62` … `R-65` taken during the wave —
is integrated on `integration/w49` and published to `origin/dev` as the commit that carries this
report. It is not tagged and not on `origin/main`: that needs a direct owner instruction naming
the exact SHA, the release acceptance (`R-65`) and the manual A01–A12 pass (`D-132`).

Integrator: session `pdf-analysis-48` (exclusive integrator from 2026-10-06). The lanes from
Stage E on were executed by session `pdf-analysis-56`, which integrated W49 up to `1b25955`
before the owner moved the integrator role.

## Integration line

| Step | Commit | Evidence |
| --- | --- | --- |
| `W49-RULE-01`, `W49-FREEZE-01` | `fdbae9e`, `dff1922` | `R-55` … `R-61` in `OWNER_RULINGS_2026-09-17.md` §3.19 |
| Stage A–D lanes: ACCESS, DECISIONS, SEAL, BFF, EDGE | merged `0dbb418`, `1c25657`, `2a31edf`, `4159555`, `1b25955` | each lane's own `GATE OK` at its SHA |
| integration gate on `1b25955` | — | 2026-10-06 11:45:45–12:02:00 +05:00, `EXIT=0`, literal `GATE OK`; foundation 35; backend 3066 passed / 5 skipped / 298 subtests; frontend 1278 in 86 files |
| `W49-QA-01` | `bcad663`, merged `8aa589a` | twelve items pass, no finding; 27 mutations red; Q-1 raised |
| `W49-JUDGE-X` | `c8ad73b`, merged `42c07e9` | PASS for the code; B-1 release-blocking (deploy) |
| `W49-JUDGE-Y` | `4eeb4ca`, merged `1e988c9` | PASS with F-1 must-fix-before-merge |
| `W49-FIX` dispatched; `R-62`, `R-63`; Part F for `R-65`, narrowed | `c4e94e5`, `631794c`, `e47b9ed`, `49f606c` | `docs/program/tasks/W49-FIX.md` |
| `W48-INT-MAIN-01` record; `R-64`, `R-65`; state moved to W49 | `a015d65`, `62eb0c9` | `W48-INT-MAIN-01.md`; the `alpha-w48` tag turned the D-115 prose guard red everywhere until `62eb0c9` |
| `W49-FIX` | `598d218` (code `49187a4`), merged `b8c8a66` | its own gate on `49187a4`: `GATE OK`, backend 3178 passed / 6 skipped / 298 subtests, frontend 1296, foundation 35 |
| `contracts/domain/v1/README.md` two sentences; register; state; ports | this commit | the executor's permission layer refused the README; the owner ruled by direct poll that the integrator edits it |

## Counts against the W49 freeze baseline

Baseline (the W48 closure gate, `W49-RULE-01.md`): backend 2733 passed / 5 skipped, frontend 1195
in 83 files, foundation 35. At `W49-FIX`'s code commit: backend **3178 / 6**, frontend **1296**,
foundation 35. The +445 backend tests are the lanes' (ACCESS, DECISIONS, SEAL, BFF, EDGE, QA and
FIX); the sixth skip is `W49-FIX`'s disposable-stand test, opt-in through
`AUDITMANAGER_PROXY_STAND=1` because it starts real containers; the +101 frontend tests are the lanes' web tests (18 files under `web/tests` changed since the freeze).

## Contracts

API **27 paths / 34 operations / 77 schemas** (sealed by `W49-SEAL-01` at `2a31edf`), error catalog
**23** (`rate_limited`, edge-only), domain candidate revision **9** with **29** opaque identities,
migration head **`0015_accounts_roles_registration`**. `W49-FIX` changed only the two
identifier-name enums of `identifiers.schema.json` and this commit only two README sentences.
`contracts/api/v1/openapi.json`, root locks and `web/FRONTEND_LOCK.json` are unchanged since
`2a31edf`.

## Rulings and debts

- `R-62` … `R-65`: `OWNER_RULINGS_2026-09-17.md` §3.20 and §3.21, each by direct poll.
- `DEBT_REGISTER.md`: `D-129` (judge and FIX register findings), `D-130` (the identity debts
  `W49-PLAN.md` §3 registers by design), `D-131` (acceptance journey retry), `D-132` (the
  `alpha-w48` manual pass) opened.

## Checks

- `tests/contract/program`, `test_doc_prose_facts.py`, `test_surface_counts_in_prose.py` green on
  this commit; `git diff --check` clean.
- The full `make gate` on the exact published SHA is recorded in `W50-FREEZE-01`, because a commit
  cannot carry its own gate result.

## Risks and known limitations

- The first production deploy with `W49-FIX`'s `reload-proxy.sh` restarts the proxy once (its
  configuration has lagged since the container was created); open connections drop then.
- `D-129`'s TLS-overlay question in `deploy.sh` is unverified against the stand.
- W50 must migrate the default-credential screens guard to the new sign-in form and W51 takes the
  form fields `login`, `password`, `confirm_password`, `last_name`, `first_name`,
  `middle_name` with initials from `displayLabel` (recorded at the BFF merge).

## Integrator instruction

Next: `W50-FREEZE-01` from the published `origin/dev` — it carries the `A-6` navigation amendment
as `R-66` (with the «Очередь» stub in Система), the `DEBT_REGISTER.md` owner line for
`W50-INT-CLOSE`, and this wave's gate record.

## Forbidden-hotspot proof

Contracts changed only within `W49-SEAL-01`'s and `W49-FIX`'s grants and the owner-ruled README
edit; no lock, workflow or migration byte outside the lanes' grants; `origin/main` and tags
untouched by this task.
