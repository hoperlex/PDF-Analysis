# Task W52-INT-MAIN-DEV-RECONCILE-01 — reconcile main test repairs onto dev

task_id: W52-INT-MAIN-DEV-RECONCILE-01

## Outcome

Create a local integration candidate descending from both current `origin/main` and the
W52 development line. Preserve main's valid test repairs and update any Stage-B-only
expectation that Stage C made false. Publish to `origin/dev` only after QA and a complete
`make gate` on the exact clean candidate; this task has no `origin/main` authority.

## Depends on

- `W52-INT-VALIDATION-ENTRY-01`, completed at `d0bcb258bdc1c0d10b3fb753622128421dc1c89d`.

## Frozen inputs and contracts

- Local development integration start: `d483bc8` (docs-only validation grant on
  `origin/dev=d0bcb258bdc1c0d10b3fb753622128421dc1c89d`).
- `origin/main=21eba6eb44bfcea91348a021fa5ae84c9ab26fca`; common ancestor
  `3fc0dcfa1fbe59c2e00007fdbd7159e43c2d3551`.
- `VERSION=0.3.0`; API 30/37/83, error catalog 23, domain revision 9 / 29
  identities, migration head `0016_release_notes`, contract version
  `1.0.0-draft.1`.
- The eight main-only test paths listed in `W52-INT-VALIDATION-ENTRY-01` §2 and
  the release behavior implemented on development Stage C.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: `tests/support/expected_facts.json` and the eight-path diff;
  no public contract member is changed.

## Captured premise evidence

- premise: main has eight test-only repairs after the common ancestor; its Stage-B
  release 503 expectations are stale against the development Stage-C adapter.

### P-01 — main-only path inventory

- captured_at: 2026-10-09
- command: `git diff --name-status 3fc0dcf..origin/main`
- captured_output:
  ```text
  A docs/program/W52-INT-MAIN-01.md
  A docs/program/W52-INT-MAIN-SEAL-01.md
  A docs/program/tasks/W51-INT-HOTFIX-01.md
  A docs/program/tasks/W52-INT-MAIN-01.md
  A docs/program/tasks/W52-INT-MAIN-SEAL-01.md
  M tests/characterization/w13_baseline/journey.py
  M tests/integration/access/conftest.py
  M tests/integration/api/identity_surface.py
  M tests/integration/api/qa_w49/conftest.py
  M tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py
  M tests/integration/composition/test_every_port_implementation_is_whole.py
  M tests/integration/composition/test_router_answers.py
  M tests/integration/db/test_fixture_template.py
  ```
- interpretation: the eight tests need semantic review; inherited records remain
  historical evidence about the main publication.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/W52-INT-MAIN-SEAL-01.md`
- addendum_path: `docs/program/W52-INT-MAIN-DEV-RECONCILE-01.md`

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- A local merge of the exact frozen main SHA into the integration branch.
- `tests/characterization/w13_baseline/journey.py`
- `tests/integration/access/conftest.py`
- `tests/integration/api/identity_surface.py`
- `tests/integration/api/qa_w49/conftest.py`
- `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`
- `tests/integration/composition/test_every_port_implementation_is_whole.py`
- `tests/integration/composition/test_router_answers.py`
- `tests/integration/db/test_fixture_template.py`
- This task and `docs/program/W52-INT-MAIN-DEV-RECONCILE-01.md`.
- Ignored local dependency environments, isolated `.env` and gate logs under
  `.local/validation/w52-release/**`.

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root, global styles,
runtime code, generated clients, release notes, owner stand, tags and `origin/main`.
Main's already committed integration task/report documents are inherited by the merge,
not authored here.

## Non-goals

No contract reseal, new application behavior, deployment, release tag or debt closure.
No replacement of the W51/W52 QA, independent judges or human A01–A20 acceptance.

## Deliverables and checks

- Ancestry and exact path inventory of both parents.
- Semantic comparison and focused checks for the eight test files.
- QA/gate handoff for the combined candidate, with literal `GATE OK` required before
  publication to `origin/dev`.
- Six-part report, `git diff --check`, contract/head checks and clean tracked status.

## Integration contract

Main's tests are read and merged as evidence-bearing code, then reconciled against the
Stage-C implementation. The combined candidate must be a descendant of both refs.
Any publication to dev requires unchanged remote dev, a clean tree, QA and the complete
gate on the exact committed SHA. Main publication belongs to a later `W52-INT-MAIN-01`
task after the owner names that exact candidate.

## Failure, rollback and feature flag

If the merge reveals a runtime/contract conflict or a test needs changes outside the
eight named paths, stop and issue a separate grant. A red focused check or gate blocks
publication. Correct a bad local merge with a new reviewed commit. No runtime feature
flag or data rollback applies.
