# W48-INT-MAIN-01 — completion report

## Result

**DONE with one owner-ruled exception.** `23e0579a2009d320011a87b2f0a5b429f87920ab` (the W48
closure, `integration/w48-close`) is on `origin/dev` and `origin/main`, deployed by the auto-deploy
workflow, verified on the host by the workflow's own `verify-deployed.sh` step, and tagged
`alpha-w48`. The live-provider condition of `dispatch/W48-PLAN.md` §12 is **not** met: the stand
runs `provider_mode=recorded`, and the owner ruled `R-64` (tag now, `D-70` named as the
exception) and `R-65` (from W49 on, `proxy` counts as live). The manual A01–A12 pass was not run.

Integrator: session `pdf-analysis-48`, appointed exclusive integrator by the owner on 2026-10-06.
This report is committed on the W49 integration line after the tag and reaches `origin/dev` with
`W49-INT-CLOSE`; it is never a second push to `main`.

## Authority

- 2026-10-06 ~12:00 +05:00, direct poll: the owner named `23e0579` for `origin/dev` and
  `origin/main` and stated that the provider credential was on the host.
- 2026-10-06, direct polls after the acceptance: `R-64` and `R-65`
  (`OWNER_RULINGS_2026-09-17.md` §3.21).

## Before the push (`MAIN_AUTODEPLOY_POLICY.md`)

| Step | Evidence |
| --- | --- |
| refs re-read | `origin/dev` `9b5219e`, `origin/main` `608632a`; both ancestors of the candidate |
| clean tree | `git status --porcelain -uall` empty in `.local/worktrees/w48-close` |
| fresh full gate on the exact SHA | 2026-10-06 12:03:17–12:15:07 +05:00, `EXIT=0`, literal `GATE OK: battery, foundation, frontend lint/typecheck/tests and whitespace all pass`; foundation 35; backend 2733 passed / 5 skipped / 4 warnings / 297 subtests; frontend 83 files / 1195 tests — identical to the `W48-INT-CLOSE` gate recorded in `W49-RULE-01.md` |
| surface re-measured | API 17 paths / 20 operations / 61 schemas, `openapi.json` byte-identical to `608632a`; error catalog 22; migration head `20261002_0014_durable_analysis_effects` (`R-53`; `main` was at `0013`, so no earlier `0014` shape was ever deployed) |
| deployment inputs | against `608632a`: comment-only changes to `deploy.sh`, `alpha.env.example`, `proxy/nginx.conf`, `bucket-init.sh`; the new non-gate `make alpha-acceptance` target |

## Publication and deployment

- `origin/dev`: `9b5219e..23e0579`, verified with `git ls-remote`.
- `origin/main`: re-read as `608632a` immediately before; `608632a..23e0579` at
  2026-10-06T12:15:43+05:00, verified with `git ls-remote`.
- Workflow `deploy-auto`, run `37428566874`, attempt 1, event `push`, `head_sha` `23e0579…`,
  07:15:44Z–07:17:47Z, conclusion `success`; job `112153779347`, step "Deploy and verify exact
  commit" `success` — that step checks out `DEPLOY_SHA`, runs `infra/deploy/deploy.sh` and
  `infra/deploy/verify-deployed.sh` under `set -euo pipefail` and asserts `HEAD` equals
  `DEPLOY_SHA`. The raw job log needs a GitHub token and was not read.
- Public preflight from the clean candidate checkout, 07:19:41Z: `PREFLIGHT OK` (five PDFs,
  root `307` → `/projects`, `/login` `200`, unauthenticated `/api/v1/openapi.json` `401`).

## Acceptance

Run by the owner with an acceptance-assistant session (`pdf-analysis-18`) from
`.local/worktrees/w48-close`, evidence under `.local/manual-alpha/` there (not tracked).

| Run | Result |
| --- | --- |
| `20261006T075511Z-1035149` | `FAIL` at sign-in: the credential pair was refused; nothing walked, nothing created |
| `20261006T083425Z-1338396` | `FAIL` at start-run: `net::ERR_NETWORK_CHANGED` while another tenant's Docker bridge on this host dropped veths (08:36:09–08:36:19Z); no run created. A host flake; the journey has no retry for a transient navigation error — registered |
| `20261006T085651Z-1448500` | `ALPHA ACCEPTANCE FAIL` on one phase only. `candidateSha` = `deployedSha` = `23e0579…`; identity, sign-in, write 3/3, cold routes 16/16, width 780, refusals 6/6 all `PASS`; `providerLive` `FAIL` — the new run reached `published` in 1514 ms with `provider_mode` `recorded` |

The three server refusals carried their exact constraints (`not_encrypted`,
`every_page_has_extractable_text`, `1 <= page_count <= 30`); the client refused `oversize.pdf` as
`too_large` without a request. No run made a paid model call. Every `report.md`, log and
`automated-verdict.json` was checked for secrets and is clean; `journey.json` and
`refusals.json` hold raw headers by design and are never published.

Manual A01–A12: **not run** — the runbook starts it after an automated `PASS`, and A04/A05 need a
real model. Owed under `R-64`.

## Tag

`alpha-w48`, annotated, at `23e0579a2009d320011a87b2f0a5b429f87920ab`, created after the rulings
were recorded; its message names the `D-70` exception and `R-64`.

## Risks and known limitations

- `D-70` stays open: the stand serves recorded analysis until the owner switches it to `proxy`
  (`R-65`) and redeploys. A proxy run records `provider_mode` `live` (provenance, not transport),
  so the existing verifier passes it unchanged.
- The deployed proxy keeps a stale `nginx.conf` inode (`W49-JUDGE-X` B-1); harmless for W48,
  whose proxy changes were comments only, and repaired in `W49-FIX` before W49 reaches `main`.
- The acceptance journey has no retry for a transient browser network error.

## Forbidden-hotspot proof

One fast-forward of `origin/main` to the gated SHA, no force, no post-gate commit on the pushed
tip; no contract, migration, lock or workflow byte was changed by this task.
