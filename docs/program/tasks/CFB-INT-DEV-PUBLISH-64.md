# Task CFB-INT-DEV-PUBLISH-64 — unserved Run source and comparison checks

task_id: CFB-INT-DEV-PUBLISH-64

## Outcome

Integrate an unserved W57b Run reference read chain, bind W56b crop evidence to its immutable Version source, and reject W59 observation identities reused across versions. Publish the exact checked result to `origin/dev`.

## Depends on

- `CFB-INT-DEV-PUBLISH-63` — completed at `417123c729599cfa075d3461038c8dd15b86d4a3`.
- `W56B-INT-CROP-SOURCE-DIGEST-01` — completed source `3aa14a5bd181ac6ac89746dee22858ef414ab117`.
- `W57B-INT-RUN-REFERENCE-CHAIN-01` — completed source `49ed17238cd8bf729e6d51cae5aa86057bfdad76`.
- `W59-INT-FINDING-OBSERVATION-IDENTITY-01` — completed source `ea7436d26310e755877bdf8ddf38fd0e039a18fe`.

## Frozen inputs

- base commit: `417123c729599cfa075d3461038c8dd15b86d4a3`
- API v1 SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256 `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- error catalogue SHA-256 `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations`, SHA-256 `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- `VERSION=0.6.0`; `origin/main` and `v0.6.0` remain W55b `37393a979a430e490843d7f410e9eca9491a4ea1`;
- R-135 focused checks for intermediate development candidates.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: source tasks change disjoint runtime paths and no frozen contract, migration, root dependency or deployment path.

### P-01 — exact source paths

- captured_at: 2026-10-16
- command: `git diff --name-only 417123c729599cfa075d3461038c8dd15b86d4a3..1f2ed37a80a5de8cc0542611c9531913dac86fad`
- captured_output:
  ```text
  docs/program/W56B-INT-CROP-SOURCE-DIGEST-01.md
  docs/program/W57B-INT-RUN-REFERENCE-CHAIN-01.md
  docs/program/W59-INT-FINDING-OBSERVATION-IDENTITY-01.md
  docs/program/tasks/W56B-INT-CROP-SOURCE-DIGEST-01.md
  docs/program/tasks/W57B-INT-RUN-REFERENCE-CHAIN-01.md
  docs/program/tasks/W59-INT-FINDING-OBSERVATION-IDENTITY-01.md
  src/auditmanager/comparison/finding_match_suggestions.py
  src/auditmanager/norms/public.py
  src/auditmanager/runs/geometry_crop_input.py
  src/auditmanager/runs/public.py
  src/auditmanager/runs/reference_pipeline.py
  tests/integration/comparison/test_finding_match_suggestions.py
  tests/integration/runs/test_geometry_crop_input.py
  tests/integration/runs/test_reference_pipeline.py
  ```
- interpretation: the 14 source paths are disjoint; this path proof does not establish live DB/S3 or beta acceptance.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W56B-INT-CROP-SOURCE-DIGEST-01.md`
- `docs/program/W57B-INT-RUN-REFERENCE-CHAIN-01.md`
- `docs/program/W59-INT-FINDING-OBSERVATION-IDENTITY-01.md`
- `docs/program/tasks/W56B-INT-CROP-SOURCE-DIGEST-01.md`
- `docs/program/tasks/W57B-INT-RUN-REFERENCE-CHAIN-01.md`
- `docs/program/tasks/W59-INT-FINDING-OBSERVATION-IDENTITY-01.md`
- `src/auditmanager/comparison/finding_match_suggestions.py`
- `src/auditmanager/norms/public.py`
- `src/auditmanager/runs/geometry_crop_input.py`
- `src/auditmanager/runs/public.py`
- `src/auditmanager/runs/reference_pipeline.py`
- `tests/integration/comparison/test_finding_match_suggestions.py`
- `tests/integration/runs/test_geometry_crop_input.py`
- `tests/integration/runs/test_reference_pipeline.py`
- `docs/program/CURRENT_STATE.md`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-64.md`
- `docs/program/CFB-INT-DEV-PUBLISH-64.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root, global styles, served API/UI, provider and finding publication, production corpus/DB/S3, credentials, deployment workflow, `origin/main` and tags.

## Non-goals

No W54 qualified corpus, W57b deterministic stage/0024 seal or report route, W56b OCR citation policy/model call, W59 section seal/public comparison, real service drill, complete beta gate or deployment.

## Deliverables

Three reviewed source cherry-picks, first-read state update, this task/report, combined focused tests, clean-tree handoff, dev fast-forward and exact remote readback.

## Required tests

- Combined W56b crop/OCR, W57b saved reference, W59 finding match, ALR-05/stage facade and programme governance suites: pass.
- Current-state documentation facts, Python compilation, frozen SHA checks, exact 17-path diff, `git diff --check` and direct task handoff: pass.
- Fresh remote refs, fast-forward proof, exact-SHA dev push and readback: pass. No intermediate full beta `make gate` under R-135.

## Integration contract

The new W57b use case reads current-Attempt saved text and a verified catalogue under one caller-owned transaction, uses an explicit unparsed-slug tuple and returns an unserved report with pins. W56b crop checks the Version manifest source digest. W59 finding matcher refuses observation IDs shared between versions. No result is published by these functions.

## Failure/idempotency/security cases

Stop on dirty tree, expanded paths, moved dev or failed check. A changed local branch name is not publication evidence: re-establish exact HEAD and clean tree before push. Never force push. Correct through a reviewed forward commit.

## Rollback / feature flag

Unserved, read-only or pure changes. Revert before activation; no data rollback or runtime feature flag applies.

## Handoff

- changed files: 17 exact allowed paths;
- contracts: none;
- checks and limitations: paired report;
- forbidden hotspots untouched.
