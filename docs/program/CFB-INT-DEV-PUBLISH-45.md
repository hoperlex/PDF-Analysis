# CFB-INT-DEV-PUBLISH-45 — W54, W56b and W57a development candidate

The published development base is
`4c16ccd7ae975d5a32829e9bcdf975f8b12f66e1`. The three reviewed source
commits `e8b8f32d`, `cf4a9a96` and `9978ded4` were applied without conflict
as `f4f74d7b`, `997bd84a` and `0dc578c5`. Their twelve paths are disjoint;
this integration adds only its task and report.

W54 `bundle-export` metadata preflight now requires the exact snapshot ID and
reliability-aware chunking profile that export will use. A checkpoint for a
different snapshot or profile cannot make the target appear ready. The real
read-only check of the existing base snapshot refused because its build is
absent and available RAM was below the preflight floor; it did not access
DB/S3 or run the paid repair.

W56b selects one saved `prepared.text_layer` reference from a caller-supplied
successful, run-scoped stage envelope and binds supplied Blob bytes to that
reference before partitioning pages. The caller still must prove the DB
read, current Attempt and actual bounded Blob read. W57a now binds a
supplied set, map, snapshot and PDF version to deterministic unserved v3
system/user/schema material and a local digest. It exposes selected prompt
text only. The reviewed map, qualified corpus, CAP-01 and provider effect
remain open.

## Checks

- Combined W54, W56b, W57a and programme governance selection: **115 passed**.
- Frozen `contracts/api/v1/openapi.json` SHA-256:
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
  error catalogue and stage registry hashes also match the frozen tasks.
- Exact 14-path diff and `git diff --check`: pass. The clean-tree technical
  handoff and remote ref readback are recorded after this report is committed.
- R-135 defers the complete beta `make gate` for this intermediate candidate.

No public product contract, migration, root dependency, composition root,
global style, served provider/API/UI, production data, deployment workflow,
`origin/main` or tag changes are in this candidate. No corpus DB/S3
publication, beta acceptance or deployed v0.6.0 change is claimed.
