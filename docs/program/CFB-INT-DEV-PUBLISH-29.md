# CFB-INT-DEV-PUBLISH-29 — W56b complete crop cohort on dev

The candidate builds on directly read
`origin/dev=f468d20eaf46dba82908615b04f20090541b21df` and fast-forwards
to the exact completed W56b source commit
`81ca174112dc1d8d97e9b8e3c0a1da0c9d2c6518` before the integration
documents. The source payload is exactly four additive task-owned paths;
its parent is the published dev28 SHA.

## Checks and scope

- Source: **19 focused** container-free tests, compilation, direct task
  governance, frozen-input and four-path checks passed.
- Integrated geometry cohort/layout/maths and programme suites:
  **161 passed**. An initial broader selection also collected seven
  PostgreSQL-backed portal-integrity cases and reported setup errors because
  this isolated worktree has no `DATABASE_URL`; it was not a real-service
  acceptance run. The 161-case container-free selection passed unchanged.
- Direct integration-task governance returned `[]`; `git diff --check`
  passed. This integration adds only its task, this report and bounded
  `CURRENT_STATE.md`.
- API remains **48 paths / 55 operations / 131 schemas**, SHA-256
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
  stage registry SHA-256 remains
  `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`.
  Domain IDs, error catalogue and migration head `0023_norm_citations`
  match the frozen inputs.

No contract, migration, root dependency/lock, composition root, existing
geometry/recognised producer, global style, production DB/S3,
`origin/main`, tag or deployment input was changed.

## Limits and publication

The new pure selector requires exactly one checked PNG crop per checked
IMAGE block, refuses missing/phantom/duplicate/wrong-region records and
returns geometry-mismatch IMAGE blocks as explicit skips. It does not read
Blob bytes or prove that the two documents came from the same saved Run.
W56b must later verify saved artifact and crop Blob custody, choose a
provider and budget, and seal execution before using the cohort. R-135
defers the complete W56–W63 beta gate; W55b's release gate is separate.

Publish only the clean exact checked SHA to `origin/dev` as a fast-forward
from the recorded predecessor, then directly read back the remote SHA into
ignored local evidence. This task has no `origin/main` authority.
