# W48-INT-MAIN-02 — the `alpha-w48.1` hotfix release

## Result

**DONE.** `3a54108ba8dbcd9723cdeb7c6ad1fb0c0209b801` (`integration/w48-1`: `alpha-w48` plus
`W48-PROXY-01`) is on `origin/main`, deployed by the auto-deploy workflow, accepted with a live
provider, and tagged `alpha-w48.1` (tag object `b94e0af`). The stand reaches a real model for the
first time. The hotfix line is merged forward into `integration/w50` (`fc64ef6`), so the deployed
tip is an ancestor of the development line again.

## Authority

- `R-67`: hotfix in code, through the agent gateway (`OWNER_RULINGS_2026-09-17.md` §3.23).
- Direct poll ~18:30 +05:00 2026-10-06: publish `3a54108` to `origin/main` if and only if the
  literal `GATE OK` holds on that SHA.
- `R-68`: the owner's attestation is the manual record.

## Line and gate

| Step | Commit | Evidence |
| --- | --- | --- |
| hotfix base: task file, the line's live state, ports | `fb5ba44` | `docs/program/tasks/W48-PROXY-01.md` |
| `W48-PROXY-01` (executor `pdf-analysis-61`, later `-31`) | `63cb3ca` code, `ed2c4fa` report | targeted 54 passed; three mutations red; no lane gate (host contention, integrator's call) |
| merge | `3a54108` | four granted paths |
| gate run 1 | — | void: `test_embedding_bakeoff_fixture` needs `.local/norms/corpus`, absent from the fresh worktree (environment, not code) |
| gate run 2 on `3a54108`, `.local/worktrees/w48-1-int`, 2026-10-06 18:56:20–19:10:07 +05:00 | — | literal `GATE OK`, exit 0; foundation 35; backend 2742 passed / 5 skipped / 297 subtests; frontend 1195 in 83 files |

## Publication and deployment

- `origin/main` re-read as `23e0579`, fast-forward proven, pushed `23e0579..3a54108` at
  2026-10-06T19:10:26+05:00, verified with `git ls-remote`.
- Workflow `deploy-auto` run `37476743497`, attempt 1, event `push`, `head_sha` `3a54108…`,
  14:10:28Z–14:11:04Z, `success`; job `112314008659`, step "Deploy and verify exact commit"
  `success` (it runs `infra/deploy/verify-deployed.sh` on the host and asserts `HEAD` equals the
  SHA).
- Public preflight 14:12:12Z: `PREFLIGHT OK`.

## Acceptance

- Automated, 2026-10-07 06:36:59Z, from the clean candidate checkout
  `.local/worktrees/w48-1-int` (evidence `.local/manual-alpha/20261007T063659Z-444377` there,
  untracked): `ALPHA ACCEPTANCE PASS`; `candidateSha` = `deployedSha` = `3a54108…`; identity,
  sign-in, writes 3/3, cold routes 16/16, width 780, refusals 6/6, `providerLive` observed `live`.
- The live run `run_01M4AHC903YDHQQGY2BCN7GDV2`: `published` in 26.2 s, four stages succeeded, no
  degradation, three findings — exactly the three planted issues SI-01, SI-02, SI-03, no false
  positive; every quote checked literally on its page; one model call, USD 0.000552 measured.
- `PROXY_LLM_MODEL` on the stand: not stated by the owner.
- Manual A01–A12: the owner's attestation (`R-68`); no scripted per-item report exists.
- Secrets: the evidence was checked by the acceptance session; `journey.json` and
  `refusals.json` hold raw headers by design and are never published.

## Register

`D-70` closed (a live run on the stand); `D-132` closed (`R-68`); `D-133` opened (the proxy error
mapping found on the way).

## Forbidden-hotspot proof

One fast-forward of `origin/main` to the gated SHA, no force, no post-gate commit on the pushed tip;
no contract, migration, lock or workflow byte changed by the hotfix.
