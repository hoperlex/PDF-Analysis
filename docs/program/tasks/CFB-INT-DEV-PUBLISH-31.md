# Task CFB-INT-DEV-PUBLISH-31 — integrate W57a grounding and W56b crop bytes

task_id: CFB-INT-DEV-PUBLISH-31

## Outcome

A clean fast-forward `origin/dev` candidate carries two unserved pure
checks: W57a grounds AR v3 PDF/norm quote proposals with separate prompt
label bindings, and W56b verifies supplied saved crop references and PNG
bytes. Neither check proves real persisted custody or activates a stage.

## Depends on

- `CFB-INT-DEV-PUBLISH-30` — complete at
  `f6f19220fa5ae019daae07a3771846e2523ce55a`;
- `W57A-INT-CITE-GROUNDING-CORE-01` — complete at
  `5785a915aba0bd92eccd669e07e4039c61d6d59e`;
- `W56B-INT-SAVED-CROP-CUSTODY-PREP-01` — complete at
  `3650dab5a8513d06b92f2d48e595809503c98e69`.

## Frozen inputs

- integration base and directly read `origin/dev`:
  `f6f19220fa5ae019daae07a3771846e2523ce55a`;
- directly read `origin/main`: `23fd729dbb06c642be0588017f6b195305e2e53e`;
- both source parents equal the integration base; W57a source
  `5785a915aba0bd92eccd669e07e4039c61d6d59e` changes seven paths,
  45 focused/ALR-05 checks; W56b source
  `3650dab5a8513d06b92f2d48e595809503c98e69` changes four paths,
  13 focused offline checks;
- API 48 paths / 55 operations / 131 schemas, SHA-256
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
  stage SHA-256
  `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
  domain IDs SHA-256
  `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`,
  error catalogue SHA-256
  `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`,
  migration head `0023_norm_citations`;
- R-135 defers complete beta gate; W55b release gate is separate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the completed source tasks have disjoint seven/four-path grants.
  W57a repairs a real label/paragraph cardinality seam; W56b checks only
  supplied bytes and references, not repository provenance.

### P-01 — exact source path sets

- captured_at: 2026-10-16
- command: `git show --format= --name-only 5785a915aba0bd92eccd669e07e4039c61d6d59e; git show --format= --name-only 3650dab5a8513d06b92f2d48e595809503c98e69`
- captured_output:
  ```text
  docs/program/W57A-INT-CITE-GROUNDING-CORE-01.md
  docs/program/tasks/W57A-INT-CITE-GROUNDING-CORE-01.md
  src/auditmanager/analysis/profiles/ar_v3/citation_grounding.py
  src/auditmanager/norms/citation_prep.py
  src/auditmanager/norms/public.py
  tests/integration/analysis/test_ar_v3_citation_grounding.py
  tests/integration/norms/test_citation_prep.py
  docs/program/W56B-INT-SAVED-CROP-CUSTODY-PREP-01.md
  docs/program/tasks/W56B-INT-SAVED-CROP-CUSTODY-PREP-01.md
  src/auditmanager/analysis/geometry/saved_crop_custody.py
  tests/integration/analysis/geometry/test_saved_crop_custody.py
  ```
- interpretation: accept each source commit's exact bytes; no contract or
  migration writer overlaps.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W57A-INT-CITE-GROUNDING-CORE-01.md`;
- `docs/program/tasks/W57A-INT-CITE-GROUNDING-CORE-01.md`;
- `src/auditmanager/analysis/profiles/ar_v3/citation_grounding.py`;
- `src/auditmanager/norms/citation_prep.py`;
- `src/auditmanager/norms/public.py`;
- `tests/integration/analysis/test_ar_v3_citation_grounding.py`;
- `tests/integration/norms/test_citation_prep.py`;
- `docs/program/W56B-INT-SAVED-CROP-CUSTODY-PREP-01.md`;
- `docs/program/tasks/W56B-INT-SAVED-CROP-CUSTODY-PREP-01.md`;
- `src/auditmanager/analysis/geometry/saved_crop_custody.py`;
- `tests/integration/analysis/geometry/test_saved_crop_custody.py`;
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-31.md`;
- `docs/program/CFB-INT-DEV-PUBLISH-31.md`;
- `docs/program/CURRENT_STATE.md`;
- ignored `.venv` link to the existing Python environment for focused tests.

## Forbidden hotspots

All other paths, especially `contracts/**`, migrations, root dependencies
and locks, composition root, existing v1/v2 production profile/executor,
API routes, W58/W54 files, global styles, production DB/S3,
`origin/main`, tags and deployment workflow.

## Non-goals

No qualified retrieval-set proof, atomic CITE writer, registered v3 Run,
served report reader, real run-scoped DB/Blob readback, Attempt fence,
provider choice/budget, corpus publication, W55b deployment or beta
acceptance.

## Deliverables

Exact eleven-path source payload, bounded state update, this task/report
and direct published-dev SHA readback.

## Required tests

- integrated W57a grounding/parser, W56b supplied-crop byte and programme
  suites, direct task governance;
- exact patch/path and frozen contract checks, whitespace, clean-tree,
  fresh remote fast-forward and post-push readback;
- real DB/S3 custody and complete beta gate deferred by host lane/R-135;
  W55b release gate separate.

## Integration contract

Fast-forward the exact W57a source commit, then cherry-pick W56b exact
source patch without editing payload. W57a caller must prove exact Run pin,
verified set bytes, map/snapshot identity and custody before CITE can write.
W56b caller must obtain a run-scoped StageResult row, BlobStore bytes and
current Attempt authority, then fence/recheck mutable state; this pure
check does none of those external reads. A moved ref or changed source
stops publication; never force-push.

## Failure/idempotency/security cases

W57a withholds whole proposal on PDF/norm grounding failure and refuses
duplicate/foreign label bindings. W56b refuses corrupt/foreign/extra/missing
supplied refs or bytes. Both pure checks have no external effect. No
credential, norm corpus text or PNG bytes enter Git.

## Rollback / feature flag

No served behavior is wired. Revert eleven source paths and these three
integration documents through a reviewed forward commit if abandoned.

## Handoff

- source files: exact seven W57a and four W56b task paths;
- integration files: this task, report and bounded state update;
- contracts: none; real custody/runtime acceptance remains open;
- forbidden hotspots and `origin/main` remain untouched.
