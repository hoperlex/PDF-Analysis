# Task W55B-INT-MAIN-PREP-01 — prepare an exact W55b deployment candidate

task_id: W55B-INT-MAIN-PREP-01

## Outcome

An isolated, clean worktree at the W55b development close SHA is checked as a
fast-forward of the current `origin/main`, has reproducible locked test
environments, and has a complete gate result recorded for that exact SHA. The
result identifies every remaining prerequisite to a separate `W55B-INT-MAIN-01`
deployment decision. This task does not update a remote ref.

## Interim result

Three complete-gate attempts on the exact candidate exited without `GATE OK`.
The first and third hit composition worker-adapter waits; the second found a
persisted test project from the first attempt and a separate API 500 response.
Fresh disposable gate volumes removed the carried project, and targeted API
tests passed, but the worker-adapter wait recurred. Exact logs and digests are
recorded in the accompanying report. This task remains incomplete until a
complete run passes on the unchanged candidate or an explicitly owned repair
candidate passes its own complete gate. No `origin/main` instruction or
publication is inferred.

## Depends on

- `W55B-INT-CLOSE` — completed at `6d63802ab465a0317839c9b57abd5e90f3d91769`.

## Frozen inputs

- W55b candidate: `6d63802ab465a0317839c9b57abd5e90f3d91769`;
- remote `main`: `23fd729dbb06c642be0588017f6b195305e2e53e` at the preparation read;
- remote `dev`: `8069220909e40c39e2329d5f5cb9585a5a5714ec` at the preparation read;
- W55 plan SHA-256 `9f4e0f204284347bc3ead59423a5cff830bbc9298ceaa2d47e1412f640b92b64`;
- main auto-deploy policy SHA-256 `1be97f93e6a8573ff88bc58a75a4166403d0db8badf401dd8e4fe39972fbf818`;
- W55b close report SHA-256 `8354713829a671c68a6c77fad22dd055b7ea742e37542f4ede63c5e07fe4ace9`;
- candidate migration head `0021_portal_bundles`, `VERSION=0.6.0`;
- candidate API 47 paths / 54 operations / 123 schemas, error catalogue 24 codes.
- owner confirmation on 2026-10-16: the alpha still contains only generated
  test data, so the prior `R-110` stand-copy waiver applies to this candidate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W55b is already on `origin/dev`, while `origin/main` is the earlier
  `v0.5.0` release and current W56–W59 development slices have no full gate.

### P-01 — exact remote refs and predecessor

- captured_at: 2026-10-16
- command: `git ls-remote origin refs/heads/dev refs/heads/main`
- captured_output:
  ```text
  8069220909e40c39e2329d5f5cb9585a5a5714ec refs/heads/dev
  23fd729dbb06c642be0588017f6b195305e2e53e refs/heads/main
  ```
- interpretation: the candidate is an ancestor of current `origin/dev` and
  a fast-forward descendant of current `origin/main`; both remote refs must
  be reread before any future publication.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none; the owner requested candidate preparation, not
  publication of this exact SHA.

## Allowed paths

- `docs/program/tasks/W55B-INT-MAIN-PREP-01.md`;
- `docs/program/W55B-INT-MAIN-PREP-01.md`;
- ignored isolated `.local/worktrees/w55b-main-candidate/**` for checkout,
  locked test environments and gate evidence only.

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, application/runtime/test source, corpus source, production DB,
stand copy state, `origin/main`, `origin/dev`, tags and deployment workflow.

## Non-goals

No remote push, backup attestation, production migration, workflow launch,
live acceptance, tag, normative corpus publication or beta verdict. The
intermediate W56–W59 slices are not part of this W55b release candidate.

## Deliverables

An exact candidate worktree, a gate log and digest, this task and a result
report with remaining deployment conditions.

## Required tests

- exact remote SHA read and `git merge-base --is-ancestor origin/main <candidate>`;
- clean worktree, `make bootstrap`, `npm ci`, `make gate-preflight`;
- complete `make gate` on the unchanged candidate, requiring literal `GATE OK`;
- frozen contract and migration read-back, report governance and whitespace.

## Integration contract

`W55B-INT-MAIN-01` may act on `origin/main` only after a separate direct owner
instruction naming this exact gate-checked SHA, a fresh main ref and
fast-forward proof, confirmation that the test-data-only `R-110` condition
still holds at publication, and the main auto-deploy policy. A stand copy is
required if real/client data arrives before publication. The owner then must
await the workflow and verify the deployed same-SHA tree. A changed candidate
needs a new complete gate.

## Failure/idempotency/security cases

If gate fails or the host cannot provide its required resources, report a
failed or incomplete candidate without a deployment claim. Do not use the
old R-125 partial-rerun evidence as a literal `GATE OK` for this run. Ignored
`.env`, local database and gate logs remain outside Git; no secrets enter the
report. Repeating preparation does not alter either remote ref.

## Rollback / feature flag

Remove the isolated ignored worktree and revert these two documents if this
candidate is abandoned. No product behavior is changed by preparation.

## Handoff

- changed files: this task and its report only;
- contracts: none;
- next integration owner: `W55B-INT-MAIN-01` on an exact owner instruction;
- forbidden hotspots and remote refs remain untouched by this task.
