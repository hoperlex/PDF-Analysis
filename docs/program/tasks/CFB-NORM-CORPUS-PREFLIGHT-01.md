# Task CFB-NORM-CORPUS-PREFLIGHT-01 — read-only W54 corpus preflight

task_id: CFB-NORM-CORPUS-PREFLIGHT-01

## Outcome

An operator can run one fast CLI against the shared `.local/norms` root and receive an
explicit metadata/resource refusal before any heavy W54 corpus operation. The CLI never
opens source PDFs, a database, S3 or a provider; its `METADATA_READY` status is not a
source, build or bundle qualification.

## Depends on

- `W54-BUNDLE-01` — completed bundle layout and verifier;
- `W54-INT-CORPUS-READINESS-01` — completed source pin and operation sequence.

## Frozen inputs

- base commit: `5a51721a745a7bfc5c85cc4594625fa53cbce523`;
- W54 plan SHA-256: `b1b4acbf7ce02c4ef8b14533dedc8d7c9e64404b2f4cc0cc5c6342c9d7fdaf71`;
- W55 plan SHA-256: `9f4e0f204284347bc3ead59423a5cff830bbc9298ceaa2d47e1412f640b92b64`;
- corpus manifest SHA-256: `160fdc7ea261b44298757b3a066982fd167b389fde614fb119c4c1d0d72fbb3b`;
- source inventory: 674 document directories, 31,619 regular files;
- API contract SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256: `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256: `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- migration head: `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the pinned source metadata is present, while promotion artifacts
  and resource floors required for a bundle export are absent.

### P-01 — source and missing preparation artifacts

- captured_at: 2026-10-15
- command: `../../../.venv/bin/python scripts/norms/corpus_preflight.py --norms-root /root/projects/PDF-Analysis/.local/norms --next-step bundle-export`
- captured_output:
  ```text
  {
    "status": "REFUSED",
    "next_step": "bundle-export",
    "manifest_sha256": "160fdc7ea261b44298757b3a066982fd167b389fde614fb119c4c1d0d72fbb3b",
    "document_directories": 674,
    "regular_files": 31619,
    "source_sums": "absent",
    "restore_verified_dump": "absent",
    "build_checkpoint": "absent",
    "bundle_candidate": "absent",
    "capacity": {
      "disk_available_bytes": 562929664,
      "disk_required_bytes": 3865470567,
      "memory_available_bytes": 6154862592,
      "memory_required_bytes": 6442450944
    },
    "refusals": [
      "source_sums_unavailable",
      "restore_verified_dump_unavailable",
      "build_checkpoint_unavailable",
      "disk_floor",
      "memory_floor"
    ],
    "qualification": "metadata-only, not authorization to operate: run sha256sum -c for the source, restore-verify for the dump, embedding status/load for the build, and full bundle verify; stand capacity and P3 compatibility were not checked"
  }
  ```
- interpretation: this is metadata inventory only. The manifest has no per-file SHA proof and no corpus PDF, dump, vector or bundle payload was read.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/norms/corpus_preflight.py`
- `tests/integration/norms/test_corpus_preflight.py`
- `src/auditmanager/norms/bundle/cli.py`
- `docs/program/tasks/CFB-NORM-CORPUS-PREFLIGHT-01.md`
- `docs/program/CFB-NORM-CORPUS-PREFLIGHT-01.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root, global styles,
`CURRENT_STATE.md`, other tasks/reports, source corpus bytes and `.local/norms` outputs,
production stand, credentials, tags and published refs.

## Non-goals

No full `sha256sum -c`, load, dump, restore, paid repair, embedding, bundle export/verify,
DB/S3 import, stand capacity probe, P3 validation, gate or beta verdict. The CLI does not
replace any verifier named in W54/W55.

## Deliverables

Read-only JSON CLI with exact path-set comparison using W54's existing
`read_drop_sums` parser, explicit artifact states and W54 §3.9 host floors; focused
tests for positive metadata, missing/partial artifacts, count/digest mismatch and floor
refusals; report; one comment-only correction to the bundle CLI's outdated storage note.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/test_corpus_preflight.py tests/integration/norms/bundle/test_import_refusals_offline.py` — all pass;
- `../../../.venv/bin/python scripts/norms/corpus_preflight.py --norms-root /root/projects/PDF-Analysis/.local/norms --next-step bundle-export` — current corpus exits 2 with named missing artifacts and floor refusals;
- `../../../.venv/bin/python -m compileall -q scripts/norms/corpus_preflight.py tests/integration/norms/test_corpus_preflight.py`; `git diff --check` — clean.

## Integration contract

The operator supplies the absolute shared norms root, because this worktree has no
worktree-local corpus. `REFUSED` exits 2; `METADATA_READY` exits 0 and means only that
cheap structural prerequisites and the instant's disk/RAM thresholds passed. A future
operator must still run source `sha256sum -c`, promotion restore verification,
`embedding status/load`, full `bundle verify`, stand capacity and P3 compatibility in
the named window. No S3/DB publication follows from this CLI's output.

## Failure/idempotency/security cases

Wrong manifest digest/count, nonregular source entry, absent/ambiguous/malformed sums,
checksum listings of other paths,
missing dump proof, plan-only or partial build and under-floor resources refuse explicitly.
The command is read-only and can be rerun. It prints no credential, document text or
source path listing.

## Rollback / feature flag

Remove the standalone script, test and task/report; revert the comment-only CLI note.
No runtime feature flag or data rollback is needed.

## Handoff

- changed files/checks/limits: see `docs/program/CFB-NORM-CORPUS-PREFLIGHT-01.md`;
- contracts: none;
- next: integration review, then provision capacity before W54 step 0.
