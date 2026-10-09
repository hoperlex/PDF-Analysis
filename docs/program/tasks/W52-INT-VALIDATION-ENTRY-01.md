# Task W52-INT-VALIDATION-ENTRY-01 — open W51/W52 release validation

task_id: W52-INT-VALIDATION-ENTRY-01

## Outcome

The integrator freezes one exact development readback for the deferred W51/W52
validation, records the separate main-line evidence and test delta, and issues
an executable validation order. The task is complete when its report and this
grant are checked and published to `origin/dev`; D-137–D-140 remain open.

## Depends on

- `W52-INT-CLOSE`, completed on `origin/dev` at
  `aeed8e35f3b12c5f2f506fdc9dd0585058b04385`.

## Frozen inputs

- Clean development readback:
  `aeed8e35f3b12c5f2f506fdc9dd0585058b04385`. This is the
  implementation subject, not a validated release candidate.
- Separately published main readback:
  `21eba6eb44bfcea91348a021fa5ae84c9ab26fca`; common ancestor
  `3fc0dcfa1fbe59c2e00007fdbd7159e43c2d3551`. Main's gate report and
  workflow are evidence about that line only.
- `VERSION=0.3.0`; API 30 paths / 37 operations / 83 schemas; 23 API error
  codes; domain candidate revision 9 / 29 opaque identities; migration head
  `0016_release_notes`; `contract_version=1.0.0-draft.1`.
- `docs/program/dispatch/W52-PLAN.md` §§4–5 and
  `docs/program/MAIN_AUTODEPLOY_POLICY.md`; D-137–D-140 in the register.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: `tests/support/expected_facts.json` and the current OpenAPI,
  domain and migration checks; this task changes no member.

## Captured premise evidence

- premise: the development tree is clean and both remote refs still name the
  handoff commits, but their histories have diverged.

### P-01 — local clean base and ancestry

- captured_at: 2026-10-09
- command: `git status --porcelain=v1 && git rev-parse HEAD && git rev-parse origin/dev && git rev-parse origin/main && git merge-base origin/dev origin/main && git rev-list --left-right --count origin/main...origin/dev`
- captured_output:
  ```text
  aeed8e35f3b12c5f2f506fdc9dd0585058b04385
  aeed8e35f3b12c5f2f506fdc9dd0585058b04385
  21eba6eb44bfcea91348a021fa5ae84c9ab26fca
  3fc0dcfa1fbe59c2e00007fdbd7159e43c2d3551
  8	20
  ```
- interpretation: the empty first status is clean; the 8/20 counts are
  main-only/dev-only commits after the common ancestor, not a merge verdict.

### P-02 — remote readback

- captured_at: 2026-10-09
- command: `git ls-remote origin refs/heads/main refs/heads/dev refs/tags/alpha-w48.1`
- captured_output:
  ```text
  aeed8e35f3b12c5f2f506fdc9dd0585058b04385	refs/heads/dev
  21eba6eb44bfcea91348a021fa5ae84c9ab26fca	refs/heads/main
  b94e0af020169f5fc121d9295b46156a33dd56d9	refs/tags/alpha-w48.1
  ```
- interpretation: the tag ref is annotated; its dereferenced commit remains
  `3a54108ba8dbcd9723cdeb7c6ad1fb0c0209b801`. No later release tag is
  claimed.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/W52-INT-CLOSE.md` and main's
  `docs/program/W52-INT-MAIN-SEAL-01.md`
- addendum_path: `docs/program/W52-INT-VALIDATION-ENTRY-01.md`

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W52-INT-VALIDATION-ENTRY-01.md`
- `docs/program/W52-INT-VALIDATION-ENTRY-01.md`
- Ignored integrator handoff/card under `.local/`, if needed.
- A docs-only commit on the clean integration worktree and a proved
  fast-forward of that commit to `origin/dev`.

## Forbidden hotspots

Every other tracked path, especially `contracts/**`, migration head, root
dependency and lock files, composition root, global styles, runtime, tests,
the owner root worktree, `origin/main`, tags and the owner's live stand.
Read-only inspection of main's test delta grants no right to merge it.

## Non-goals

No QA, built-stand attack, manual acceptance, debt closure, full `make gate`,
`GATE OK`, release verdict, code correction, tag or deployment claim. No
reconciliation of main-only test changes without a later exact-path grant.

## Deliverables

- This task and a six-part report with remote refs, main workflow/public-probe
  observations and the main-only test-delta inventory.
- Validation order: fresh-context `W52-AUDIT-01` and disposable-stand
  `W52-ATTACK-01`; triage and exact-path correction grants; Stage-D
  `W52-QA-01`, `W52-JUDGE-X`, `W52-JUDGE-Y`, `W52-NOTES-JUDGE` and cross-examination;
  `W52-FIX`, notes re-run and full exact-candidate gate. Record W51 identity
  checks and human A01–A20 as applicable to the candidate.
- Separate main/dev reconciliation review before any eventual release
  candidate. In particular, main's Stage-B 503 test expectations must be
  assessed against dev's implemented Stage-C release storage.

## Required checks

- Re-read remote `dev` and `main`; require clean local base and fast-forward
  proof before development publication.
- Match `VERSION`, `tests/support/expected_facts.json`, the domain identity
  catalogue and migration head on the exact base.
- Focused documentation governance/prose checks and `git diff --check` for
  this docs-only entry. Record their exact results in the report.
- Later validation: focused tests for every correction; isolated services and
  built stand; `make alpha-acceptance` with measured build and human A01–A20;
  final `make gate` with literal `GATE OK` on one clean exact SHA. The gate slot
  must be coordinated with stand owners before starting services.

## Integration contract

This entry grants planning and evidence only. Each audit, attack, QA, judge or
correction receives its own task and disjoint `allowed_paths` from the exact
readback; no release-blocking finding is fixed outside its grant. The
integrator accepts or rejects those results, reconciles main-only test fixes
semantically, then runs the full gate after all fixes. A green development
candidate may advance on `origin/dev`. `origin/main` requires a separate direct
owner instruction naming the later exact verified candidate and a distinct
integration task whose contract names that ref.

## Failure / idempotency / security

A changed ref, dirty tree, unexpected path or failed docs check stops this
entry's publication. No public probe establishes the current deployed Git SHA.
Do not record credentials or direct QA at the owner's stand. Repeating a
read-only observation adds no acceptance evidence for a different SHA.

## Rollback / feature flag

Revert the docs-only entry with a new reviewed development commit if its
premise is wrong. No product behavior or feature flag changes.

## Handoff

The paired report records changed files, checks/results, contracts, risks,
next integration steps and forbidden-hotspot proof. No checkpoint or tag.
