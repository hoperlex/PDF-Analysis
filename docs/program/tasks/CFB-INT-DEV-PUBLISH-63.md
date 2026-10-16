# Task CFB-INT-DEV-PUBLISH-63 — corpus-independent code corrections

task_id: CFB-INT-DEV-PUBLISH-63

## Outcome

Integrate and publish three independently checked corrections on `origin/dev`: global W56a evaluation identities, W58 target Blob metadata on retry, and W59 page bounds before encoding. Refresh the first-read state and read back the exact published SHA.

## Depends on

- `CFB-INT-DEV-PUBLISH-62` — completed at `7b56cb451946d250b1030f61150a4979dbcfc157`.
- `W56A-INT-EVALUATION-GLOBAL-IDENTITY-01` — completed source `62b934834b679a9573f8d0b34126100593d5940d`.
- `W58-INT-TARGET-RETRY-METADATA-01` — completed source `430359325da4530098ac7d8bfe65809e51e4f9ef`.
- `W59-INT-SHEET-SNAPSHOT-BOUNDS-03` — completed source `02ffcd0484e0478f5ade407d15e4947252cf191e`.

## Frozen inputs

- base commit: `7b56cb451946d250b1030f61150a4979dbcfc157`
- API v1 SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- error catalogue SHA-256 `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations`, SHA-256 `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- `VERSION=0.6.0`; `origin/main` and `v0.6.0` remain W55b `37393a979a430e490843d7f410e9eca9491a4ea1`;
- R-135 permits focused checks for intermediate development candidates.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the three completed source tasks are disjoint, and their only runtime edits are the evaluation bridge, target object reader and sheet suggestion budget check.

### P-01 — exact source deltas

- captured_at: 2026-10-16
- command: `git diff --name-only 7b56cb451946d250b1030f61150a4979dbcfc157..a85346d784cd497656bc3a3a88b2a0bd62427288`
- captured_output:
  ```text
  docs/program/W56A-INT-EVALUATION-GLOBAL-IDENTITY-01.md
  docs/program/W58-INT-TARGET-RETRY-METADATA-01.md
  docs/program/W59-INT-SHEET-SNAPSHOT-BOUNDS-03.md
  docs/program/tasks/W56A-INT-EVALUATION-GLOBAL-IDENTITY-01.md
  docs/program/tasks/W58-INT-TARGET-RETRY-METADATA-01.md
  docs/program/tasks/W59-INT-SHEET-SNAPSHOT-BOUNDS-03.md
  scripts/recovery/target_object_restore.py
  src/auditmanager/comparison/sheet_match_suggestions.py
  tests/contract/evaluation/test_bridge.py
  tests/integration/comparison/test_sheet_match_suggestions.py
  tests/integration/recovery/test_isolated_restore_drill.py
  tests/integration/recovery/test_target_object_restore.py
  tools/evaluation/bridge.py
  ```
- interpretation: the 13 source paths are disjoint and contain no frozen contract, migration, composition root or deployment path. This does not prove production behaviour.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W56A-INT-EVALUATION-GLOBAL-IDENTITY-01.md`
- `docs/program/W58-INT-TARGET-RETRY-METADATA-01.md`
- `docs/program/W59-INT-SHEET-SNAPSHOT-BOUNDS-03.md`
- `docs/program/tasks/W56A-INT-EVALUATION-GLOBAL-IDENTITY-01.md`
- `docs/program/tasks/W58-INT-TARGET-RETRY-METADATA-01.md`
- `docs/program/tasks/W59-INT-SHEET-SNAPSHOT-BOUNDS-03.md`
- `scripts/recovery/target_object_restore.py`
- `src/auditmanager/comparison/sheet_match_suggestions.py`
- `tests/contract/evaluation/test_bridge.py`
- `tests/integration/comparison/test_sheet_match_suggestions.py`
- `tests/integration/recovery/test_isolated_restore_drill.py`
- `tests/integration/recovery/test_target_object_restore.py`
- `tools/evaluation/bridge.py`
- `docs/program/CURRENT_STATE.md`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-63.md`
- `docs/program/CFB-INT-DEV-PUBLISH-63.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies and lockfiles, composition root, global styles, served API/UI, provider dispatch, production corpus/DB/S3, credentials, deployment workflow, `origin/main` and tags.

## Non-goals

No W54 repair/publication, W56a live provider or measured baseline, W58 real service drill, W59 section seal/public comparison, full beta gate or deployment.

## Deliverables

Three reviewed source cherry-picks, first-read state update, this task/report, focused combined checks, clean-tree handoff, dev fast-forward and exact remote readback.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/comparison tests/contract/evaluation/test_bridge.py tests/contract/evaluation/test_matcher_core.py tests/integration/recovery tests/contract/program/test_wave_governance.py` — pass;
- compile changed Python, frozen SHA checks, exact 16-path diff, `git diff --check`, direct task handoff — pass;
- fresh remote ref, fast-forward proof, exact-SHA dev push and readback — pass. No intermediate `make gate` under R-135.

## Integration contract

The evaluation bridge rejects finding and observation IDs reused across recorded runs. W58 retry/readback requires sealed `content-sha256` metadata as well as bytes. W59 snapshot limits are checked before UTF-8 allocation; valid digests stay stable. All changes remain unserved/offline.

## Failure/idempotency/security cases

Stop on dirty tree, expanded path set, moved dev or a failed check. Never force push or overwrite an object lacking required metadata. Repeating the exact published SHA is a no-op.

## Rollback / feature flag

Correct through a reviewed forward commit. These unserved fixes have no migration or runtime flag.

## Handoff

- changed files: 16 exact allowed paths;
- contracts: unchanged;
- checks and limits: paired integration report;
- forbidden hotspots untouched.
