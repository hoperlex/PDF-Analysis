# Task W52-INT-C2-GRANT-01 — dispatch release prose and acceptance pack

task_id: W52-INT-C2-GRANT-01

## Outcome

The exclusive integrator grants the two disjoint W52 Stage-C2 lanes from
the exact published Stage-C development tree, with current paths, checks
and publication boundaries.

## Depends on

- `W52-INT-C-TRANSLATE-01`, published to `origin/dev` at
  `98a629fdf2ec1d40c234fc7d04b39ddb92ff8e97`.

## Frozen inputs

- Base and current `origin/dev`:
  `98a629fdf2ec1d40c234fc7d04b39ddb92ff8e97`.
- Product `VERSION=0.3.0`; API 30 paths / 37 operations / 83 schemas;
  23 error codes; domain revision 9 / 29 identities; migration head
  `0016_release_notes`; `contract_version=1.0.0-draft.1`.
- `dispatch/W52-PLAN.md` §§3.1, 3.4, Stage C2 and §5. D-137–D-140
  retain complete gate, QA and live/deployment acceptance.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: the two task files name disjoint owned path sets; no
  product enumerator changes in this docs-only grant

## Captured premise evidence

- premise: Stage C is published; the authored release entries are minimal,
  prose-test directories do not yet exist, and the acceptance pack's
  current readers are named.

### P-01 — Stage-C base and candidate files

- captured_at: 2026-10-08
- command: `git rev-parse HEAD; cat VERSION; rg --files release-notes tests/contract web/tests/unit docs/program | rg '(^release-notes/|release.notes|RELEASE_PROCESS|/RELEASES\\.md$|W52-RELNOTES|W52-ACCEPT)' | sort`
- captured_output:
  ```text
  98a629fdf2ec1d40c234fc7d04b39ddb92ff8e97
  0.3.0
  release-notes/0.2.0.json
  release-notes/0.3.0.json
  release-notes/schema.json
  ```
- interpretation: RELNOTES owns final authored texts and new prose
  checks; the sealed `schema.json` remains outside its grant.

### P-02 — acceptance-pack readers

- captured_at: 2026-10-08
- command: `rg --files scripts tests/e2e/pc01/journey tests/contract docs/manual-tests docs/program | rg '(manual-alpha-check\\.sh|verify-acceptance\\.mjs|test_alpha_acceptance_command\\.py|ALPHA_PUBLIC_ACCEPTANCE\\.md|ALPHA-MANUAL-01\\.md|W52-ACCEPT)' | sort`
- captured_output:
  ```text
  docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md
  docs/program/ALPHA-MANUAL-01.md
  docs/program/tasks/ALPHA-MANUAL-01.md
  scripts/manual-alpha-check.sh
  tests/contract/test_alpha_acceptance_command.py
  tests/e2e/pc01/journey/verify-acceptance.mjs
  ```
- interpretation: ACCEPT changes only the named command, verifier,
  test, Makefile target, English runbook sentence and its own report.
  The historical ALPHA-MANUAL record may receive a forward addendum,
  not a rewrite of its prior evidence.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W52-INT-C2-GRANT-01.md`,
  `docs/program/W52-INT-C2-GRANT-01.md` — this grant and report.
- `docs/program/tasks/W52-RELNOTES-01.md`,
  `docs/program/tasks/W52-ACCEPT-01.md` — executor grants only.
- `docs/program/CURRENT_STATE.md` — opening Stage-C2 status only.
- `docs/program/dispatch/W52-PLAN.md` — Stage-C2 status only.
- Clean `integration/w51` ref and fast-forward of `origin/dev` only.

## Forbidden hotspots

All product code and test implementations, `contracts/**`, migration
head, root dependencies/locks, composition root, global styles,
`origin/main`, tags and deployed services. This grant changes no
release note or acceptance script.

## Non-goals

No RELNOTES or ACCEPT implementation, Stage-D judgment, full gate,
QA, built-stand acceptance, release verdict, tag or deployment.

## Deliverables

- Two complete executor task files with disjoint hotspots and an exact
  published base, six-part integration report, clean `origin/dev`
  publication and SHA readback.

## Required checks

- Current-tree pin sweep and file/reader inventories; `git diff --check`;
  task-governance and relevant prose tests.
- Re-read `origin/dev` immediately before the checked fast-forward and
  read back the exact pushed SHA. No full `make gate` claim.

## Integration contract

RELNOTES and ACCEPT begin only from this grant's remote readback. Their
allowed paths do not overlap except their consumption of the frozen
released API and English runbook. Merge RELNOTES before ACCEPT, then
recheck the combined tree before a development close.

## Failure / idempotency / security

A stale remote ref, path conflict or failed governance check stops
publication. No credential or secret enters either task file.

## Rollback / feature flag

Revert a docs-only dispatch mistake with a new development commit;
do not rewrite published history. No runtime behavior or flag changes.

## Handoff

Return changed files, checks/results, contracts, risks, next integrator
step and forbidden-hotspot proof. No checkpoint or tag.
