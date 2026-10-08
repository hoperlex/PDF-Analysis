# W52-INT-C-API-01 — release backend accepted, WEB and TRANSLATE granted

**Date:** 2026-10-08. **API candidate:** `81e5181a34dd6905814f1ecb02de305e2e99aabd`,
the direct child of the read-back Stage-C grant `3fc0dcfa1fbe59c2e00007fdbd7159e43c2d3551`.
At review, `origin/dev` was `3fc0dcf` and `origin/main` was `1e9bb13`.

## 1. Changed files and acceptance

The integrator reviewed the exact 25-path API diff and fast-forwarded it
into clean `integration/w51`. It contains the release context, shape
validator, transactional loader, API composition wiring, API image inputs,
one-shot deploy/reset sequencing, focused tests and its hand-back. The
five-line grant correction in `tasks/W52-RELEASES-API.md` is legitimate:
the Stage-B API test instantiated a zero-argument placeholder removed by
Stage C, and `tests/integration/api/test_release_routes.py` now exercises
the real adapter. No other path needed a correction.

This docs-only follow-up changes `tasks/W52-INT-C-API-01.md`,
`tasks/W52-RELEASES-WEB.md`, `tasks/W52-TRANSLATE-01.md`, this report,
`CURRENT_STATE.md`, `dispatch/W52-PLAN.md` and
`dispatch/PORT_REGISTRY.md`. It reserves free `56820`, `60420/60421`
ports for WEB if that lane needs local services. TRANSLATE needs none.

## 2. Checks and results

- Exact-parent, 25-path and `git diff --check` checks passed before the
  fast-forward; fresh remote read showed the expected `origin/dev` and
  unchanged `origin/main`. Current-tree table sweep exposed only the
  release backend's three deploy table paths among the Stage-C grant
  families; no WEB contract reseal is needed. The translation path sweep
  found six runbooks with Cyrillic text across 14 files, including the
  SEAL-updated `PC-01_prototype.md`; its reader inventory is in the task.
- On the merged tree and only `gate-w52r` PostgreSQL/S3: release/API tests
  **57 passed**. The 57 include schema parity, loader rules, rollback,
  account marks, `whats_new`, startup and deployment-order checks. The
  lane's local image/checkout build-ID parity and two-run loader checks
  remain recorded in `W52-RELEASES-API.md`.
- API/domain/ALR-05/governance contract group **336 passed**;
  deployment composition and release-order group **35 passed**.
  `npm --prefix web run api:verify` passed at 37 operations; frontend
  lint and typecheck both passed.
- The WEB and TRANSLATE grants are code-only Stage-C dispatch. No full
  `make gate`, `GATE OK`, independent QA, built-stand or manual acceptance
  is claimed. D-137–D-140 retain those obligations.

## 3. Contracts

No API/domain contract, error catalog, generated client, migration head or
`contract_version` changed in the API lane. The frozen surface remains
30 paths / 37 operations / 83 schemas, 23 error codes, domain revision 9 /
29 identities and head `0016_release_notes`. `release-notes/schema.json`
is a new authored-file shape; `VERSION=0.3.0` is the product-version source.
The docs follow-up changes no contract.

## 4. Risks and known limits

`release-notes/0.3.0.json` and the archive are minimal placeholders until
Stage C2 RELNOTES and NOTES-JUDGE ground the user-facing claims. API
`build_id` intentionally excludes Dockerfile-only and `serve.py`-only
changes under the adopted plan; release validation must account for this.
The W51/W52 exact-candidate gate, QA and live evidence are still open.
No W52 release verdict, tag or `origin/main` authority exists.

## 5. Integrator instruction

Commit the seven docs paths, run focused governance/prose and diff checks,
re-read `origin/dev`, then push only the proven fast-forward of the clean
checked SHA and read it back. RELEASES-WEB and TRANSLATE start from that
read-back SHA, WEB before TRANSLATE in the integration order. Re-sweep
the Stage-C merge before granting Stage C2. Do not push `origin/main`.

## 6. Forbidden-hotspot proof

`git diff --name-only 3fc0dcf..81e5181` lists exactly the 25 paths in
`W52-RELEASES-API.md` §1. Its one task/test grant correction precedes the
test edit. The docs follow-up is confined to the seven paths in §1.
It changes no `contracts/**`, migration, root dependency/lock, generated
client, web UI or global style. The API candidate's composition-root and
deploy edits are the named RELEASES-API grant. Neither candidate touches
`origin/main`, a tag or a deployed stand.
