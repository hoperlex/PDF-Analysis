# Task CFB-INT-DEV-PUBLISH-20 — integrate W54 repair-sample preflight

task_id: CFB-INT-DEV-PUBLISH-20

## Outcome

A clean `origin/dev` fast-forward carries the completed W54 metadata-only
`repair-sample` preflight. It binds the zero-call plan to frozen source and
restore evidence and refuses insufficient resources; it does not authorize
paid repair or qualified corpus publication.

## Depends on

- `CFB-INT-DEV-PUBLISH-19` — completed at `de3d81085f30301ddc2965f7f4bf927ea738c8b3`;
- `W54-CORPUS-REPAIR-SAMPLE-PREFLIGHT-01` — completed at `30839f09542feea98dadab26fddb057e1877fea7`.

## Frozen inputs

- integration base and directly read `origin/dev`: `de3d81085f30301ddc2965f7f4bf927ea738c8b3`;
- directly read `origin/main`: `23fd729dbb06c642be0588017f6b195305e2e53e`;
- exact source commit: `30839f09542feea98dadab26fddb057e1877fea7`;
- source task pins: source sums digest `eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`, base dump digest `e1280373ffd7fa3deaa0716429def1844d7e858e79bae7fbad5ade6d516ff74d`, repair plan digest `045f8b636ccae1aa2503015c305575e0a9beb3349055c0aaa365b4474e573365`;
- API/domain/error/stage SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`, `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`, `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`, `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315b2c1239453ba3a`;
- migration head `0022_findings_v2`; R-135 defers the complete beta gate;
- no proxy credential exists; the owner selected `claude-opus-5`, and the real local preflight refused only `memory_floor` at 4.70 GiB available versus 6 GiB required.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the source is complete on the current dev base and changes only
  the corpus preflight, its test, task and report.

### P-01 — exact source payload

- captured_at: 2026-10-16
- command: `git show --format='%H%n%s' --name-only --no-renames 30839f09542feea98dadab26fddb057e1877fea7`
- captured_output:
  ```text
  30839f09542feea98dadab26fddb057e1877fea7
  feat(norms): preflight pinned W54 repair sample plan

  docs/program/W54-CORPUS-REPAIR-SAMPLE-PREFLIGHT-01.md
  docs/program/tasks/W54-CORPUS-REPAIR-SAMPLE-PREFLIGHT-01.md
  scripts/norms/corpus_preflight.py
  tests/integration/norms/test_corpus_preflight.py
  ```
- interpretation: only these four source paths may be applied; remote dev
  must be reread before publication.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/CFB-INT-DEV-PUBLISH-20.md`
- `docs/program/CFB-INT-DEV-PUBLISH-20.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/W54-CORPUS-REPAIR-SAMPLE-PREFLIGHT-01.md`
- `docs/program/tasks/W54-CORPUS-REPAIR-SAMPLE-PREFLIGHT-01.md`
- `scripts/norms/corpus_preflight.py`
- `tests/integration/norms/test_corpus_preflight.py`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, other application/test source, corpus source and dump bytes,
credentials, production DB/S3, `origin/main`, tags and deployment workflow.

## Non-goals

No source rehash, PDF repair, provider/proxy call, embedding build, qualified
bundle, DB/S3 corpus import, W55b main deployment or beta verdict.

## Deliverables

Exact source payload, a bounded current-state update, this task, integration
report and direct remote read-back of the checked SHA.

## Required tests

- focused `corpus_preflight` tests and program governance;
- frozen contracts/migration, source exact-path, whitespace and clean-tree
  checks; fresh remote predecessor and fast-forward proof;
- complete beta `make gate` deferred under R-135; W55b has its own separate
  main-candidate gate.

## Integration contract

Only this task publishes its exact checked SHA to `origin/dev` after applying
the completed W54 source without payload edits. `repair-sample` is a
metadata-only refusal screen; an operator must still verify complete source
bytes and restore evidence immediately before a future paid call, install a
credential privately, obey the durable journal and sample/budget rules, then
build embeddings and qualify DB/S3 publication. A moved remote dev ref stops
the integration; never force-push.

## Failure/idempotency/security cases

No secrets, ignored plans, corpus bytes or Docker data enter Git. Do not
start services or hash the corpus while W55b owns the host gate lane. A
retry rereads the remote and no-ops if already equal. Failures do not create
an acceptance marker or deployment claim.

## Rollback / feature flag

The CLI behavior is not wired into runtime. A correction uses a reviewed
forward commit; no feature flag or deployment rollback applies.

## Handoff

- integration files: this task, its report and the bounded state update;
- source files: only the four exact W54 source paths;
- contracts: none; next: credential/window-gated sample and qualification;
- forbidden hotspots and `origin/main` remain untouched.
