# W56B-INT-CROP-COHORT-PREP-01 — complete saved crop input

Base: published `origin/dev` at
`f468d20eaf46dba82908615b04f20090541b21df`.

The new pure `prepare_image_crop_cohort` joins W55b's
`geometry.portal_blocks` and `geometry.page_crops` documents for one exact
`VersionUid`. Every IMAGE block whose page geometry is `ok` must have exactly
one matching crop record in producer order. A missing, duplicate, unrelated
or region-mismatched record refuses the whole cohort. IMAGE blocks on pages
marked `geometry_mismatch` are returned separately as explicit skips. Each
accepted candidate carries the content-addressed `geometry.crop_image`
reference and exact page region. No PNG bytes are read.

## Checks

- Focused container-free suite: **19 passed**. It covers whole-cohort
  completeness, skipped blocks, wrong version, duplicate/phantom crops,
  geometry and region disagreement, Blob/size/profile refusal, oversized
  values and a document made by the existing pure W55b geometry producers.
- Python compilation: passed.
- Direct task governance: `[]`; frozen SHA-256 readback, staged whitespace
  check and exact four-path inspection: passed at commit.
- No Docker, PostgreSQL, S3, provider, network or full gate was used while
  W55b's gate owned the host. R-135 defers the complete beta gate.

## Contracts and limitations

No contract, migration, stage registry, existing producer/consumer, API/UI,
composition, dependency or runtime behavior changed. The selector checks
the supplied document shapes and their mutual completeness. It cannot prove
they came from the same saved Run or that a named Blob still has the recorded
PNG bytes; those checks belong to the future W56b artifact reader before a
provider call. It decides no model, cost limit, sampling policy, finding or
OCR citation. Geometry-mismatch blocks are visible as skipped input, not
silently promoted to model evidence.

Remove this additive module and test before wiring to roll back. No data
rollback or feature flag is needed.

Only these four paths changed:

- `src/auditmanager/analysis/geometry/crop_cohort.py`;
- `tests/integration/analysis/geometry/test_crop_cohort.py`;
- `docs/program/tasks/W56B-INT-CROP-COHORT-PREP-01.md`;
- this report.

The W56b owner may consume this cohort after W57b closure and the pending
vision/budget rulings. That owner must load checksum-verified same-run artifact
references, verify crop Blobs before transmitting image bytes, then establish
the served stage and its explicit failure/resume policy.
