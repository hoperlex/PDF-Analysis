# CFB-NORM-CORPUS-PREFLIGHT-01 — corpus metadata and capacity preflight

**Task:** `tasks/CFB-NORM-CORPUS-PREFLIGHT-01.md`. **Base:** `5a51721a`.
**Measured:** 2026-10-15 UTC. This is development preparation, not a DB/S3
publication or a corpus qualification.

## Result

`scripts/norms/corpus_preflight.py` accepts an explicit shared norms root and one of
`source-sums`, `base-load`, `restore-verify`, `bundle-export`. It checks the digest and
document count of the 1.9 MiB source manifest, the 674 top-level document directories
and 31,619 regular file entries by metadata only, compares the checksum listing's
exact relative path set through W54's canonical parser, and reports the presence/shape of
source sums, the latest dump's restore marker, batch checkpoint files and a bundle
candidate with declared build. The status `METADATA_READY` means only that these
structural checks and the instant's W54 §3.9 floors passed. It never certifies the
source file contents, dump bytes, vectors or complete bundle bytes. It never reads
normative text, PDFs, credentials, database, S3 or provider endpoints.

For `bundle-export`, the measured host has **570,220,544 bytes disk available** versus
**3,865,470,567 bytes required** (0.6 GiB increment plus 3 GiB reserve), and
**4,641,525,760 bytes RAM available** versus **6,442,450,944 bytes required**.
The actual drop's manifest digest matches
`160fdc7ea261b44298757b3a066982fd167b389fde614fb119c4c1d0d72fbb3b`;
the inventory matches 674/31,619. The CLI exits 2 with
`source_sums_unavailable`, `restore_verified_dump_unavailable`,
`build_checkpoint_unavailable`, `disk_floor`, `memory_floor`.
`bundle_candidate` is absent. The measured headroom is transient and cannot authorize
a later heavy run; a subsequent reading found RAM above 6 GiB while disk stayed below
its floor.

The bundle CLI's `blob_store_from_environment` docstring now says the public
`S3BlobStore` and `S3StorageSettings` exports already exist. This is comment-only;
the import refusal and S3 behavior are unchanged.

## Checks

- `pytest -q -p no:cacheprovider tests/integration/norms/test_corpus_preflight.py`:
  **7 passed**. It covers a structural positive without reading fake PDF/dump bytes,
  wrong manifest, missing artifacts, plan-only build, incomplete bundle build,
  duplicate/ambiguous sums, a same-count listing of unrelated paths and both
  capacity floors. A plan without every batch vector and sidecar is classified
  as partial, not a finished embedding build.
- `pytest -q -p no:cacheprovider tests/integration/norms/test_corpus_preflight.py tests/integration/norms/bundle/test_import_refusals_offline.py`:
  **21 passed** after the last edit.
- Real read-only preflight against `/root/projects/PDF-Analysis/.local/norms`:
  exit **2**, explicit artifact and floor refusals above.
- `compileall` for the new script/test and `git diff --check`: exit **0**.
- `ruff` was unavailable in this worktree's virtualenv; this task adds no
  dependency solely for linting.

No heavy source hashing, database/S3 test, paid call, image build or complete gate ran
under R-135. Python/pytest printed unrelated stale `/tmp/pytest-of-root` cleanup
warnings; no assertion was affected.

## Integration and limits

The integrator may merge only the five task paths. No `contracts/**`, migration,
dependency/lock, composition root, global style, `CURRENT_STATE.md`, source corpus,
published ref, tag or production stand was touched. There are no new or changed
product contracts. No feature flag is needed: this is a standalone operator script.

Before W54 step 0, provision disk and remeasure free disk and available RAM in the
night window. Before each later step, repeat W54's own floor check and run its
own full verifier: source `sha256sum -c`, promotion restore verification,
embedding status/load and bundle verify. W55 production import additionally needs
stand capacity, P3 compatibility, copy/restore evidence and the owner's exact
bundle/downtime instruction. The script's metadata-only output is never import
authority.
