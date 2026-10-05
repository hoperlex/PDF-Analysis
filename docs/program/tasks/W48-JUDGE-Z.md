# Task W48-JUDGE-Z — judge the merged W48 closure line

## Outcome

An author-independent, report-only verdict establishes whether the merged W48 closure candidate
may be published to `origin/dev`, and lists any release-blocking finding with its smallest repair
grant.

## Depends on

- `W48-PUBLIC-01` — merged into `integration/w48-close` at `819b6bd`
- `W48-DURABLE-FIX-2`, `W48-GUARDS-2`, `W48-TAILS` — merged at `68cb5a2`, `5d99b62`, `3d5f322`
- the integrator's full gate on the subject — see `Captured premise evidence`

## Frozen inputs

- domain contract: W48 revision 8, unchanged since `6118e66`
- API contract: 17 / 20 / 61, unchanged since `6118e66`
- analysis/comparison/event contract: unchanged
- migration head: `0014_durable_analysis_effects` (edited in place under `R-53`)
- base commit and subject: `819b6bdd75b7dc0c62cf6280d426266140e46ea5` on `integration/w48-close`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the subject is the merged closure candidate and passed a full gate at its exact SHA

### P-01 — subject and ancestry

- captured_at: 2026-10-05
- command: `git rev-parse integration/w48-close && git merge-base --is-ancestor agent/w48-public-01 integration/w48-close && echo merged`
- captured_output:
  ```text
  819b6bdd75b7dc0c62cf6280d426266140e46ea5
  merged
  ```
- interpretation: the subject contains every W48 closure lane; acceptance is not implied.

### P-02 — integrator gate on the subject

- captured_at: 2026-10-05
- command: `make gate` in `.local/worktrees/w48-close` at `819b6bdd75b7dc0c62cf6280d426266140e46ea5`
- captured_output:
  ```text
  foundation: 35 passed
backend: 2729 passed, 5 skipped, 4 warnings, 297 subtests passed
frontend: 83 files / 1195 tests passed
GATE OK: battery, foundation, frontend lint/typecheck/tests and whitespace all pass
EXIT=0 (19:19:01 to 19:36:51 +05:00)
  ```
- interpretation: the battery is green on this tree; a judge measures what the battery cannot.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/reviews/W48-DURABLE-JUDGE-2.md`
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/reviews/W48-JUDGE-Z.md`

## Forbidden hotspots

- every other tracked path, every ref, tag and deployment action

## Non-goals

- no repair, merge, ruling or debt-register edit

## Deliverables

- report with subject/environment/commands/statuses, findings, mutations, untested questions and
  verdict; the black-box pass precedes reading any author report or `W48-CLOSE.md` §2

## Required tests

- re-run, independently, every mutation `tasks/W48-GUARDS-2.md` requires: each must fail for its
  stated reason on the subject
- inject one unknown closed-vocabulary value into each fail-open site `W48-TAILS` classified; each
  renders a typed fault or the report records why the lookup cannot miss
- for `DJ-R3`, `DJ-R4`, `DJ-R5` and the three `DJ-R6` refusals: revert the fix in a disposable
  copy and show the named test red, then restore
- run the ALR-05 AST walk independently (expect 0 deep / 0 package-root), reintroduce one deep
  import and one package-root import in a disposable copy, and show
  `tests/contract/architecture/test_alr05_boundaries.py` red for each
- `git diff --stat 6118e66 819b6bdd75b7dc0c62cf6280d426266140e46ea5 -- contracts uv.lock web/package-lock.json web/FRONTEND_LOCK.json`
  is empty
- `W48-PUBLIC-01` changed only import lines, new `public.py` modules, the guard and two documents
- fresh database: `alembic upgrade head` reports `0014_durable_analysis_effects`;
  `tests/contract/api_v1/test_doc_prose_facts.py` derives the head from the tree rather than a literal
- in a built stand at 780 × 900: a 200-character project name and a 400-character unbroken comment
  in the decision history do not widen the document; record the measured widths
- final `git diff --name-only 819b6bdd75b7dc0c62cf6280d426266140e46ea5..HEAD` names only the report

## Integration contract

Each finding is classified release-blocking, must-fix-before-merge or register. The integrator
opens a bounded `W48-FIX-C` grant only for release-blocking findings; otherwise `W48-INT-CLOSE`
proceeds on the same subject.

## Failure/idempotency/security cases

- owned disposable services and unique ports only (take a free range with `ss -ltn` and record it);
  no credential, provider body or cookie in evidence; all probes restored; never kill a process
  by pattern

## Rollback / feature flag

Report-only; revert the report commit if the judging procedure is invalid.

## Handoff

- changed files: the one report
- commands/results: included verbatim with exit status
- known limits: list untested questions
- integration notes: hand back branch `agent/w48-judge-z` at a recorded SHA
