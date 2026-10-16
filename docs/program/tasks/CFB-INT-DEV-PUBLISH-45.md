# Task CFB-INT-DEV-PUBLISH-45 — integrate W54, W56b and W57a code-first slices

task_id: CFB-INT-DEV-PUBLISH-45

## Outcome

Publish a clean development candidate with W54 bundle-target preflight,
W56b saved text reference selection and W57a unserved request-candidate
assembly. Read back the exact `origin/dev` SHA after a fast-forward push.

## Depends on

- `CFB-INT-CURRENT-STATE-44`, completed at `4c16ccd7ae975d5a32829e9bcdf975f8b12f66e1`.
- `W54-CORPUS-BUILD-TARGET-PREFLIGHT-01`, completed at source `e8b8f32dcbd466908c49f2390cc329ce90152300`.
- `W56B-INT-SAVED-TEXT-REF-PREP-01`, completed at source `cf4a9a967c68d7c7ee892a934ef8ed8f7d3d5b3a`.
- `W57A-INT-V3-REQUEST-CANDIDATE-PREP-01`, completed at source `9978ded43b3ac42aa5327dcf552f11097e15ddd2`.

## Frozen inputs

- base commit: `4c16ccd7ae975d5a32829e9bcdf975f8b12f66e1`
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- development API 48 paths / 55 operations / 131 schemas, errors 25, migration head `0023_norm_citations`;
- `origin/main` and `v0.6.0`: `37393a979a430e490843d7f410e9eca9491a4ea1`;
- R-135: focused checks on intermediate dev candidates, final complete beta gate later.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: three finished source tasks are based on this published development
  SHA and have disjoint four-path allowlists.

### P-01 — source task paths and dependency boundary

- captured_at: 2026-10-16
- command: `git diff 4c16ccd7ae975d5a32829e9bcdf975f8b12f66e1..0dc578c5 --name-only`
- captured_output:
  ```text
  docs/program/W54-CORPUS-BUILD-TARGET-PREFLIGHT-01.md
  docs/program/W56B-INT-SAVED-TEXT-REF-PREP-01.md
  docs/program/W57A-INT-V3-REQUEST-CANDIDATE-PREP-01.md
  docs/program/tasks/CFB-INT-DEV-PUBLISH-45.md
  docs/program/tasks/W54-CORPUS-BUILD-TARGET-PREFLIGHT-01.md
  docs/program/tasks/W56B-INT-SAVED-TEXT-REF-PREP-01.md
  docs/program/tasks/W57A-INT-V3-REQUEST-CANDIDATE-PREP-01.md
  scripts/norms/corpus_preflight.py
  src/auditmanager/analysis/profiles/ar_v3/request_candidate.py
  src/auditmanager/analysis/text/saved_window_custody.py
  tests/integration/analysis/test_ar_v3_request_candidate.py
  tests/integration/analysis_text/test_saved_window_custody.py
  tests/integration/norms/test_corpus_preflight.py
  ```
- interpretation: integration can cherry-pick those source commits without
  assigning two writers to a shared hotspot. No served runtime or product
  contract is changed by these source tasks.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `scripts/norms/corpus_preflight.py`
- `tests/integration/norms/test_corpus_preflight.py`
- `docs/program/tasks/W54-CORPUS-BUILD-TARGET-PREFLIGHT-01.md`
- `docs/program/W54-CORPUS-BUILD-TARGET-PREFLIGHT-01.md`
- `src/auditmanager/analysis/text/saved_window_custody.py`
- `tests/integration/analysis_text/test_saved_window_custody.py`
- `docs/program/tasks/W56B-INT-SAVED-TEXT-REF-PREP-01.md`
- `docs/program/W56B-INT-SAVED-TEXT-REF-PREP-01.md`
- `src/auditmanager/analysis/profiles/ar_v3/request_candidate.py`
- `tests/integration/analysis/test_ar_v3_request_candidate.py`
- `docs/program/tasks/W57A-INT-V3-REQUEST-CANDIDATE-PREP-01.md`
- `docs/program/W57A-INT-V3-REQUEST-CANDIDATE-PREP-01.md`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-45.md`
- `docs/program/CFB-INT-DEV-PUBLISH-45.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, stage registry, served provider/API/UI paths, original corpus,
production DB/S3, credentials, deployment workflow, `origin/main` and tags.

## Non-goals

No 121-page paid repair, embedding completion, qualified bundle or DB/S3
publication; no W56b Attempt authority or served stage; no W57a registered
profile, model call, canonical finding or beta acceptance; no deployment.

## Deliverables

Three scoped cherry-picks, this task/report, combined focused and governance
checks, exact-path handoff, dev fast-forward and remote readback.

## Required tests

- Combined W54 preflight, W56b saved-text/source-byte/window and W57a
  request/prompt/set suites; programme governance and frozen API hash: pass.
- Exact 14-path diff, whitespace, clean tree and `scripts/task_handoff.py`
  with explicit check argv: pass.
- Fresh remote dev/main/tag read, fast-forward proof, exact-SHA dev push and
  readback. The full `make gate` remains deferred under R-135.

## Integration contract

W54 preflight now names the intended snapshot/profile but cannot prove the
checkpoint payload or repaired corpus. W56b validates a caller-supplied
saved stage envelope and bytes; authoritative DB read, Attempt fencing and
Blob read remain for the future caller. W57a composes unserved draft v3
material from supplied inputs; custody, CAP-01, prompt seal and activation
remain separate. Only this integration task advances `origin/dev`.

## Failure/idempotency/security cases

Stop if dev moves, the tree is dirty, paths expand or checks fail. Never
force-push or copy corpus text, credentials or private logs into Git. An
already-present exact dev SHA is a publication no-op.

## Rollback / feature flag

Offline/unserved code only. Correct any problem by a reviewed forward commit;
no runtime flag or data rollback is needed.

## Handoff

- changed files: fourteen exact allowed paths;
- contracts: no public product contract changes;
- checks and limits: paired report;
- forbidden hotspots untouched.
