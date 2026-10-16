# Task CFB-INT-DEV-PUBLISH-21 — integrate explicit W59 section review

task_id: CFB-INT-DEV-PUBLISH-21

## Outcome

A clean fast-forward `origin/dev` candidate carries an unserved W59
projection that shows all 15 section choices and suggestion evidence for one
version without selecting or confirming a section.

## Depends on

- `CFB-INT-DEV-PUBLISH-20` — completed at `d416e185d3b42da55ba2e8bfdd02d7126da7f41e`;
- `W59-INT-SECTION-REVIEW-PREP-01` — completed at `d7342f4e959f61bef8f9a96e3187c13a54da082a`.

## Frozen inputs

- integration base and directly read `origin/dev`: `d416e185d3b42da55ba2e8bfdd02d7126da7f41e`;
- directly read `origin/main`: `23fd729dbb06c642be0588017f6b195305e2e53e`;
- exact source commit: `d7342f4e959f61bef8f9a96e3187c13a54da082a`;
- source task's 15-option catalogue, frozen suggestion/confirmation boundaries and focused test evidence;
- API/domain/error/stage SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`, `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`, `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`, `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315b2c1239453ba3a`;
- migration head `0022_findings_v2`; SECTION-SEAL and W58-code close remain open;
- R-135 defers the complete beta gate; W55b main candidate failed its separate full gate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the completed source changes only a new pure section-review
  module, its tests, task and report on the current published dev base.

### P-01 — exact source payload

- captured_at: 2026-10-16
- command: `git show --format='%H%n%s' --name-only --no-renames d7342f4e959f61bef8f9a96e3187c13a54da082a`
- captured_output:
  ```text
  d7342f4e959f61bef8f9a96e3187c13a54da082a
  feat(sections): prepare explicit review choices for W59

  docs/program/W59-INT-SECTION-REVIEW-PREP-01.md
  docs/program/tasks/W59-INT-SECTION-REVIEW-PREP-01.md
  src/auditmanager/sections/review.py
  tests/integration/sections/test_review.py
  ```
- interpretation: only these four source paths may be cherry-picked; a fresh
  remote read and clean fast-forward proof are required before publication.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/CFB-INT-DEV-PUBLISH-21.md`
- `docs/program/CFB-INT-DEV-PUBLISH-21.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/W59-INT-SECTION-REVIEW-PREP-01.md`
- `docs/program/tasks/W59-INT-SECTION-REVIEW-PREP-01.md`
- `src/auditmanager/sections/review.py`
- `tests/integration/sections/test_review.py`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root,
global styles, existing section/API/UI code, W57 citation/custody seal,
production DB/S3, `origin/main`, tags and deployment workflow.

## Non-goals

No served route, expert authentication, persisted section confirmation,
profile activation, W58 recovery-code close, W55b deployment or beta verdict.

## Deliverables

Exact W59 source payload, bounded current-state update, this task, integration
report and direct read-back of the published SHA.

## Required tests

- focused W59 section review/suggestion/confirmation suite and program
  governance;
- frozen contracts/migration, exact-path, whitespace, clean-tree,
  fast-forward and remote read-back checks;
- full beta `make gate` deferred by R-135; W55b's failed release gate cannot
  be reused as W59 evidence.

## Integration contract

Only this task may publish its exact checked SHA to `origin/dev`. It applies
the W59 source unchanged. The packet is a pure display projection with no
selected or confirmed field; a later SECTION-SEAL owner must bind a real
VersionUid, authenticate an expert, persist an explicit decision and route
only from that confirmed identity. A moved dev ref or changed source stops
publication; never force-push.

## Failure/idempotency/security cases

Malformed version/catalogue/evidence inputs refuse; the source tests cover
neutral and ambiguous suggestions. No secrets, ignored logs or fixtures
enter Git. No services run while W55b evidence is being diagnosed. Retry
rereads remote and no-ops if already equal.

## Rollback / feature flag

The projection is unserved, so no runtime flag or deployment rollback is
needed. Corrections use reviewed forward commits.

## Handoff

- integration files: this task, its report and bounded state update;
- source files: only the four exact W59 source paths;
- contracts: none; next owner: W59 SECTION-SEAL after W58-code close;
- forbidden hotspots and `origin/main` remain untouched.
