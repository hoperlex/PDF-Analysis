# Task CFB-INT-DEV-PUBLISH-40 — publish W57/W59 pure slices and main evidence

task_id: CFB-INT-DEV-PUBLISH-40

## Outcome

Fast-forward `origin/dev` from dev39 to a clean candidate carrying the
reviewed, unserved W57 v3 set parser and W59 comparison preparation,
including the 500-page correction, plus the factual W55b main deployment
record. The remote SHA is read back. No main deployment is triggered.

## Depends on

- `CFB-INT-DEV-PUBLISH-39`, completed at `45d5772480f62006b430151d464a7f7200be511b`.
- `W57A-INT-SET-PROMPT-INPUT-PREP-01`, completed with local governance correction `1f647762b24f90a5cfde0856fccf841b33640f07`.
- `W59-INT-SHEET-MATCH-SUGGESTIONS-02`, completed at `4d9e4f5954a100d93daa33e8b6cc2b53558cfcfa`.
- `W59-INT-COMPARISON-500-PAGE-01`, completed at `5485232f053a5fb64b3447a581d7a7d308734821`.

## Frozen inputs

- base commit: `45d5772480f62006b430151d464a7f7200be511b`
- observed `origin/dev`: `45d5772480f62006b430151d464a7f7200be511b`;
- observed `origin/main`: `37393a979a430e490843d7f410e9eca9491a4ea1`;
- API 48 paths / 55 operations / 131 schemas, error catalog 25, migration head `0023_norm_citations` at dev39;
- source W57 parser `735ef8083dd7b4236e34449c611f72c78922208f` plus correction `1f647762b24f90a5cfde0856fccf841b33640f07`;
- source W59 suggestion `4d9e4f5954a100d93daa33e8b6cc2b53558cfcfa` plus 500-page fix `5485232f053a5fb64b3447a581d7a7d308734821`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the checked W57/W59 slices are absent from remote dev39, while W55b main is a separate deployed candidate whose host byte verification remains open.

### P-01 — remote refs before dev publication

- captured_at: 2026-10-16
- command: `git ls-remote origin refs/heads/dev refs/heads/main`
- captured_output:
  ```text
  45d5772480f62006b430151d464a7f7200be511b refs/heads/dev
  37393a979a430e490843d7f410e9eca9491a4ea1 refs/heads/main
  ```
- interpretation: dev can fast-forward from the frozen base; reread immediately before push.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W55B-INT-MAIN-01.md`
- `docs/program/tasks/W55B-INT-MAIN-01.md`
- `docs/program/W57A-INT-SET-PROMPT-INPUT-PREP-01.md`
- `docs/program/tasks/W57A-INT-SET-PROMPT-INPUT-PREP-01.md`
- `src/auditmanager/analysis/profiles/ar_v3/set_input.py`
- `tests/integration/analysis/test_ar_v3_set_input.py`
- `docs/program/W59-INT-SHEET-MATCH-SUGGESTIONS-02.md`
- `docs/program/tasks/W59-INT-SHEET-MATCH-SUGGESTIONS-02.md`
- `src/auditmanager/comparison/sheet_match_suggestions.py`
- `tests/integration/comparison/test_sheet_match_suggestions.py`
- `docs/program/W59-INT-COMPARISON-500-PAGE-01.md`
- `docs/program/tasks/W59-INT-COMPARISON-500-PAGE-01.md`
- `src/auditmanager/comparison/version_reader.py`
- `src/auditmanager/comparison/raw_evidence_seal.py`
- `src/auditmanager/comparison/finding_match_suggestions.py`
- `tests/integration/comparison/test_version_reader.py`
- `tests/integration/comparison/test_raw_evidence_seal.py`
- `tests/integration/comparison/test_finding_match_suggestions.py`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-40.md`
- `docs/program/CFB-INT-DEV-PUBLISH-40.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, served router/UI/worker paths, deployment workflow, source
corpus, production DB/S3, `origin/main` and tags.

## Non-goals

No v3 registration, model call, route activation, automatic expert approval,
raw-evidence revision activation, corpus DB/S3 import, complete beta gate,
main deployment repair or release acceptance.

## Deliverables

The exact cherry-picked W57/W59 slices, this task/report, combined focused
and governance checks, clean-tree handoff and direct dev ref readback.

## Required tests

- W57a offline suite, full `tests/integration/comparison`, task governance;
- frozen API/error/migration readback, exact changed paths and `git diff --check`;
- `.venv/bin/python scripts/task_handoff.py --task docs/program/tasks/CFB-INT-DEV-PUBLISH-40.md --worktree .` on clean committed candidate;
- fresh remote dev read, fast-forward proof, exact-SHA push and readback.
  R-135 defers the complete beta gate for these unserved slices.

## Integration contract

Only this task advances `origin/dev`. The parser accepts supplied canonical
set bytes but does not prove Run/Blob custody. W59 suggestions are rebuildable
and never approved SheetLinks; four comparison guards now accept 500-page
versions, while one raw diff revision still caps at 32 approved links. The
W55b main record truthfully leaves host byte verification incomplete.

## Failure/idempotency/security cases

Any changed remote ref, dirty tree, unowned path or failed focused check
stops the push. No force push. Secrets, ignored corpus files and gate logs
remain outside Git. Repeating an exact already-published dev SHA is a no-op.

## Rollback / feature flag

The added modules are unserved. Correct through a reviewed forward commit;
no runtime flag or data rollback is needed.

## Handoff

- changed paths: only this allowlist;
- contracts: unchanged;
- known limits: unserved W57/W59, 32-link raw comparison cap, W55b host verification open;
- forbidden hotspots remain untouched.
