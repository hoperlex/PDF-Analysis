# Task CFB-INT-DEV-PUBLISH-42 — publish W54, W56b and W57a pure slices

task_id: CFB-INT-DEV-PUBLISH-42

## Outcome

Fast-forward `origin/dev` from dev41 to a clean candidate with canonical
W54 embedding-plan preflight, W56b supplied-text-byte verification and an
unserved W57a draft prompt renderer. Read back the exact remote SHA.

## Depends on

- `CFB-INT-DEV-PUBLISH-41`, completed at `6f1307412c94de45e67ffdeba71506dc5a0aa8fb`.
- `W54-CORPUS-BUILD-PLAN-PREFLIGHT-01`, completed at source `16b0bdfa0155644b7447c6439ffaf78efd138bf0`.
- `W56B-INT-TEXT-BYTES-PREP-01`, completed at source `99e3d55c993c676975500a0f4c30a8a746094a56`.
- `W57A-INT-V3-PROMPT-MATERIAL-PREP-01`, completed at source `4918087a2904d803b75ff32bfe5c3663ac034f6b`.

## Frozen inputs

- base commit: `6f1307412c94de45e67ffdeba71506dc5a0aa8fb`
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- API 48 paths / 55 operations / 131 schemas, errors 25, migration head `0023_norm_citations`;
- W54 embedding profile `bge-m3-dense-v1`, plan format `auditmanager-embedding-plan/1`;
- `origin/main` and `v0.6.0` target: `37393a979a430e490843d7f410e9eca9491a4ea1`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the three reviewed source commits change only their disjoint allowed paths on the published development base.

### P-01 — exact paths before this integration record

- captured_at: 2026-10-16
- command: `git diff 6f1307412c94de45e67ffdeba71506dc5a0aa8fb..HEAD --name-only`
- captured_output:
  ```text
  docs/program/W54-CORPUS-BUILD-PLAN-PREFLIGHT-01.md
  docs/program/W56B-INT-TEXT-BYTES-PREP-01.md
  docs/program/W57A-INT-V3-PROMPT-MATERIAL-PREP-01.md
  docs/program/tasks/W54-CORPUS-BUILD-PLAN-PREFLIGHT-01.md
  docs/program/tasks/W56B-INT-TEXT-BYTES-PREP-01.md
  docs/program/tasks/W57A-INT-V3-PROMPT-MATERIAL-PREP-01.md
  scripts/norms/corpus_preflight.py
  src/auditmanager/analysis/profiles/ar_v3/prompt_material.py
  src/auditmanager/analysis/text/source_bytes.py
  tests/integration/analysis/test_ar_v3_prompt_material.py
  tests/integration/analysis_text/test_source_bytes.py
  tests/integration/norms/test_corpus_preflight.py
  ```
- interpretation: the source slices are path-disjoint and touch no forbidden hotspot; this task adds only two records.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W54-CORPUS-BUILD-PLAN-PREFLIGHT-01.md`
- `docs/program/W56B-INT-TEXT-BYTES-PREP-01.md`
- `docs/program/W57A-INT-V3-PROMPT-MATERIAL-PREP-01.md`
- `docs/program/tasks/W54-CORPUS-BUILD-PLAN-PREFLIGHT-01.md`
- `docs/program/tasks/W56B-INT-TEXT-BYTES-PREP-01.md`
- `docs/program/tasks/W57A-INT-V3-PROMPT-MATERIAL-PREP-01.md`
- `scripts/norms/corpus_preflight.py`
- `src/auditmanager/analysis/profiles/ar_v3/prompt_material.py`
- `src/auditmanager/analysis/text/source_bytes.py`
- `tests/integration/analysis/test_ar_v3_prompt_material.py`
- `tests/integration/analysis_text/test_source_bytes.py`
- `tests/integration/norms/test_corpus_preflight.py`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-42.md`
- `docs/program/CFB-INT-DEV-PUBLISH-42.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, served routes/provider, registered prompt profile, original
corpus, production DB/S3, credentials, deployment workflow, `origin/main`
and tags.

## Non-goals

No source-byte rehash, completed embedding verification, corpus DB/S3
publication, W56b freeze/provider effect, qualified W57a snapshot/map,
v3 profile registration, CAP-01, model call, beta acceptance or deployment.

## Deliverables

Three clean cherry-picks, this task/report, combined focused and governance
checks, exact-path handoff, fast-forward dev publication and remote readback.

## Required tests

- Combined W54 preflight, W56b source/cohort/anchor/chunk, W57a prompt/set
  and governance suites: pass.
- Frozen API SHA, 48/55/131 count, exact paths, whitespace and clean tree.
- `.venv/bin/python scripts/task_handoff.py --task docs/program/tasks/CFB-INT-DEV-PUBLISH-42.md --worktree .` with explicit check argv.
- Fresh remote dev/main/tag read, fast-forward proof, exact-SHA dev push and
  readback. R-135 defers the complete beta gate for these unserved slices.

## Integration contract

Only this task advances `origin/dev`. W54 checks canonical plan identity
without reading vector payloads. W56b checks supplied bytes but grants no
Run/Attempt authority. W57a renders draft bytes from selected norm prompt
part but is not registered or called. No deployed v0.6.0 bytes change.

## Failure/idempotency/security cases

Stop if dev moves, tree is dirty, paths exceed the allowlist or tests fail.
Never force-push. Do not copy corpus text, credentials or private logs into
Git. Repeating this exact dev publication is a no-op.

## Rollback / feature flag

Offline and unserved code only. Correct with a forward commit; no runtime
flag or data rollback applies.

## Handoff

- changed files: fourteen exact allowed paths;
- contracts: unchanged;
- tests: combined focused and governance, handoff;
- limits: metadata-only W54, supplied W56b inputs, unregistered W57a draft;
- forbidden hotspots untouched.
