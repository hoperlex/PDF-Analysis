# W52-INT-B2C-01 — SEAL accepted and Stage C backend granted

**Date:** 2026-10-08. **Code candidate:** `0dd3f7b20623e51d7927dd0fc14a1fb12292b062`
on clean `integration/w51`. At review, `origin/dev` was `fd78ad8` and
`origin/main` was `1e9bb13`.

## 1. Changed files and acceptance

The integrator reviewed SEAL's 47-path diff against the exact Stage-B grant,
including the one-line grant correction for
`web/src/shared/api/authorization.ts`, and fast-forwarded the clean SEAL
commit into `integration/w51`. The docs-only follow-up changes
`tasks/W52-INT-B2C-01.md`, `tasks/W52-RELEASES-API.md`, this report,
`CURRENT_STATE.md`, `dispatch/W52-PLAN.md` and
`dispatch/PORT_REGISTRY.md`. It reserves free local ports `56800`,
`60400/60401` for the backend lane.

## 2. Checks and results

- Fresh `pin_sweep.py reseal-surface migration table --check` on the merged
  SEAL grant: exit 0. `pin_sweep.py table` was reviewed for Stage C; no new
  table or route is granted there.
- Merged tree: API/domain contract **318 passed**; generated web client
  verification passed at 37 operations; frontend lint and typecheck passed;
  full Vitest **1715 passed in 109 files**.
- Exact SEAL tree with only its `gate-w52s` PostgreSQL/S3 services:
  release routes, release migration, role register and composition root
  **50 passed**. The services were stopped after the run.
- Docs-only grant: governance/prose/pin-sweep **67 passed**. The initial
  governance run found missing task premise/history sections and an annotated
  publication field; both task files were corrected before the passing run.
- An unqualified DB run from the integration worktree used its stale `.env`
  pointing at stopped `56381`; sandboxed reruns could not access local
  sockets. The permitted run on the exact SEAL tree and isolated `56790`
  passed. The broad PC-01 file was also attempted from the stale environment
  and produced four failures and 40 connection/setup errors; its five
  container-free cases passed. This is not acceptance evidence for the live
  PC-01 journey, which remains D-139.
- SEAL's required full Python contract command remains red as recorded in
  `W52-SEAL-01.md`: 664 passed, 70 failed, 126 errors, 452 subtests. Historical
  CP-00 assertions and a linked-worktree `.git` assumption dominate the
  result. No full `make gate`, `GATE OK` or release verdict is claimed; D-140
  owns exact-candidate gate evidence.

## 3. Contracts

The accepted SEAL changed the API to 30 paths / 37 operations / 83 schemas,
added `getProductVersion`, `listReleases` and `markReleaseNotesRead`,
and installed sole migration head `0016_release_notes`. The domain candidate,
23 error codes and `contract_version=1.0.0-draft.1` remain fixed. This
docs-only grant adds no contract or migration change.

## 4. Risks and known limits

The new routes still return `dependency_unavailable` for authorized users
until `W52-RELEASES-API` installs the release context. Stage C must prove
loader atomicity, rollback visibility, server-side `whats_new`, startup
version refusal and image/checkout build-ID parity. D-137–D-140 remain open.
No release, tag, `origin/main` update or stand deployment is authorized.

## 5. Integrator instruction

Commit the six docs paths, re-run their checks, prove fast-forward against the
fresh `origin/dev` ref, publish only that clean SHA there and read it back.
Then start `W52-RELEASES-API` from the read-back grant SHA on an isolated
branch, rechecking the reserved ports. Merge API before WEB and TRANSLATE;
grant Stage C2 only after the Stage-C merge.

## 6. Forbidden-hotspot proof

`git diff --name-only 0dd3f7b..HEAD` must show only the six docs paths in
§1. This follow-up changes no contract, migration, product code, generated
client, root dependency/lock, composition root, global style or deployment
script. The SEAL code diff's 47 paths are individually listed and grant
checked in `W52-SEAL-01.md`. Neither candidate touches `origin/main` or a
tag.
