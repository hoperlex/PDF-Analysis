# W52-INT-C2-GRANT-01 — Stage C2 execution grants

**Date:** 2026-10-08. **Base:** published Stage-C readback
`98a629fdf2ec1d40c234fc7d04b39ddb92ff8e97` on `origin/dev`.
`origin/main` remains the independent deployment ref. This is a
docs-only dispatch, not Stage-C2 implementation or validation.

## 1. Changed files and result

The integrator re-read the W52 frozen contracts, ran the current-tree
pin sweep, and inspected the release-note and acceptance-pack surfaces.
`W52-RELNOTES-01` owns the two authored entries, dictionary, prose tests
and technical release docs. `W52-ACCEPT-01` owns the alpha command,
verifier, contract test, target and English runbook sentence. Their
owned implementation paths do not overlap. The latter must keep the
historical `ALPHA-MANUAL-01.md` evidence intact and put any correction
in a forward addendum.

Exact changed paths:

```text
docs/program/tasks/W52-INT-C2-GRANT-01.md
docs/program/tasks/W52-RELNOTES-01.md
docs/program/tasks/W52-ACCEPT-01.md
docs/program/W52-INT-C2-GRANT-01.md
docs/program/CURRENT_STATE.md
docs/program/dispatch/W52-PLAN.md
```

## 2. Checks

The base is `98a629f`, with `VERSION=0.3.0`. The file sweep found
only `release-notes/{0.2.0.json,0.3.0.json,schema.json}`: no dictionary,
prose tests or technical ledger yet. The acceptance sweep found its
existing shell entry, Node verifier, contract test, English runbook and
historical ALPHA-MANUAL record. The complete `pin_sweep.py table`
reported existing migration, deployment and live-claim readers but no
additional Stage-C2 owner path. Governance and API prose/count checks
passed **93 tests**; the six-path audit and `git diff --check` passed.
No full `make gate`,
independent QA or live acceptance is claimed.

## 3. Contracts

No API/domain contract, generated client, error catalog, migration or
`contract_version` changed. Stage C2 consumes the frozen 30 paths /
37 operations / 83 schemas, 23 error codes, domain revision 9 /
29 identities and head `0016_release_notes`. RELNOTES may raise
authored revisions; it may not edit sealed `schema.json` or the loader.
ACCEPT measures the existing `GET /system/version` response.

## 4. Risks and limits

The current release JSON files are minimal revision-1 placeholders.
Any changed content must raise the authored revision to avoid an
equal-revision loader refusal on a prior local load. The acceptance
pack presently has SHA attestation but no independently measured
candidate build parity. Both lanes still need implementation and
focused checks; Stage-D judgment, full gate and live evidence remain
D-137–D-140. No release verdict, tag or `origin/main` authority exists.

## 5. Integrator instruction

Commit this exact six-path docs grant, re-read `origin/dev`, then
publish only the checked fast-forward to `origin/dev` and read back its
SHA. RELNOTES and ACCEPT must start from that readback, hand back clean
branches, and merge in that order. Re-sweep their combined tree before
any development close. Do not push `origin/main`.

## 6. Forbidden-hotspot proof

This grant changes only the six documentation paths in §1. It touches
no release entry, acceptance script, contract, migration, root
dependency/lock, generated client, composition root, global style,
`origin/main`, tag or deployed stand. No checkpoint was created.
