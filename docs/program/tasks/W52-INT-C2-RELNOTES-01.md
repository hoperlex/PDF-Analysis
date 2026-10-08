# Task W52-INT-C2-RELNOTES-01 — integrate authored notes and repair revision test

task_id: W52-INT-C2-RELNOTES-01

## Outcome

The exact RELNOTES lane is accepted on the development line. Its revision-2
files remain compatible with the database loader's integration tests, without
changing loader behavior. The resulting clean SHA is published to `origin/dev`.

## Depends on

- `W52-INT-C2-GRANT-01`, published at
  `3fcdb3ee5a08b12d9145f29da02de358bdbd57f7`.
- `W52-RELNOTES-01`, complete on clean lane commit
  `6dc7dcfff78e3de68cad3c9021c77a7950b613c5`.

## Frozen inputs

- Integration base and `origin/dev` at start:
  `3fcdb3ee5a08b12d9145f29da02de358bdbd57f7`; RELNOTES is its
  direct child and has been fast-forwarded locally for this task.
- `VERSION=0.3.0`; API 30 paths / 37 operations / 83 schemas; 23 error
  codes; domain revision 9 / 29 identities; migration head
  `0016_release_notes`; `contract_version=1.0.0-draft.1`.
- Sealed `release-notes/schema.json`; W52 plan §3.4 and Stage C2;
  `docs/program/W52-RELNOTES-01.md` claim/check evidence.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: `git diff --name-only 3fcdb3e..6dc7dcf` is the
  lane's eight-path inventory; the loader test is the only added code path

## Captured premise evidence

- premise: the database loader tests read repository-authored notes, then
  assume their initial revision is 1 and their next revision is 2.

### P-01 — stale loader-test literals

- captured_at: 2026-10-08
- command: `rg -n 'revision=1|revision=2|0\.2\.0", 1|0\.3\.0", 1' tests/integration/releases/test_release_loader.py`
- captured_output:
  ```text
  89:    assert _revisions(migrated_engine) == [("0.2.0", 1), ("0.3.0", 1)]
  91:    changed = _changed(notes["0.3.0"], revision=2, title="Новая редакция истории")
  95:        ("0.2.0", 1), ("0.3.0", 1), ("0.3.0", 2)
  120:            **notes, "0.3.0": _changed(notes["0.3.0"], revision=1, title="Изменено без ревизии")
  124:            **notes, "0.3.0": _changed(notes["0.3.0"], revision=2, title=notes["0.3.0"].title)
  200:            notes["0.3.0"], revision=2, title="Уточнённая история изменений"
  ```
- interpretation: after `W52-RELNOTES-01` raises both authored files to
  revision 2, those test expectations must derive their baseline from the
  parsed notes and ask for baseline plus one. This is a test-fixture repair,
  not an added loader rule.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- Exact eight paths of `3fcdb3e..6dc7dcf`, listed in
  `docs/program/W52-RELNOTES-01.md` §1, for fast-forward integration only.
- `tests/integration/releases/test_release_loader.py`: revise only
  initial/next revision assumptions tied to `_notes()`; retain all loader
  behavior assertions and unknown/missing-history cases.
- `docs/program/tasks/W52-INT-C2-RELNOTES-01.md`,
  `docs/program/W52-INT-C2-RELNOTES-01.md`: task and report.
- `docs/program/CURRENT_STATE.md` opening W52 status and
  `docs/program/dispatch/W52-PLAN.md` Stage C2 status only.
- Local `integration/w51` branch/worktree, ignored test environment,
  and fast-forward `origin/dev` only.

## Forbidden hotspots

All other paths, especially `contracts/**`, migrations, root
dependencies/locks, release loader/runtime, generated client, web UI,
screen registry, composition root, global styles, `origin/main`, tags and
deployment.

## Non-goals

No ACCEPT implementation, independent NOTES-JUDGE verdict, full `make gate`,
QA, live acceptance, release row, tag or deployment.

## Deliverables

- Reviewed exact lane diff, dynamic revision test expectations, focused
  merged checks, six-part report and clean `origin/dev` SHA readback.

## Required checks

- Exact parent/path audit and `git diff --check`.
- Python form/schema tests, current-only screen Vitest, web lint/typecheck,
  and loader-test collection plus database execution where available.
- Re-read `origin/dev` immediately before push and after publication.
  Record any deferred service-backed or full-gate checks.

## Integration contract

Keep the lane's fast-forward merge. Commit only the test correction and
named docs follow-up after focused checks; publish the exact clean checked
SHA to `origin/dev` if its remote base is unchanged. `W52-ACCEPT-01` starts
from the read-back result and requires a fresh task base correction because
its grant names the earlier Stage C2 base.

## Failure / idempotency / security

Unexpected paths, a stale remote ref or a failed applicable check stop
publication. The loader's append/refusal/rollback semantics remain covered.
No credentials or live deployment input enters these files.

## Rollback / feature flag

A dev-only correction is a new reviewed revert commit. Published note files
are not removed after reaching `main`; a later content correction increments
the authored revision. No runtime feature flag changes.

## Handoff

Return changed files, checks/results, contracts, risks, next integration
step and forbidden-hotspot proof. No checkpoint or tag.
