# Task W54-EMBED-BUILD-01 — the BGE-M3 embedding build of the repaired snapshot

task_id: W54-EMBED-BUILD-01

## Outcome

The repaired snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74` carries a complete
`bge-m3-dense-v1` embedding build in the promotion database: every one of its 55,855
`characters-v2:1200` chunks has its full window set, the stored set digest equals the
checkpoints' digest, and a `pg_dump` of the database is restore-verified. This is W54
step 3's second half; the bundle export is the next task.

## Depends on

- `W54-SNAPSHOT-LOAD-01` — completed repaired-snapshot load and its verified dump;
- `W54-EMBED-01` and `W54-BGE-IMAGE` — the embedder and the norms-worker image definition.

## Frozen inputs

- code base: `origin/dev` `f942ca1ce0dff227c85b74a90e6de2faa989046e`, worktree
  `.local/worktrees/w54-session-repair`; no source file is changed here;
- snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74`, content key
  `2026-07-23..2026-08-20+17d+121r.0a1bafe103ff`, chunk profile `characters-v2:1200`;
- profile `bge-m3-dense-v1`: BAAI/bge-m3 revision
  `5617a9f61b028005a4858fdac845db406aefb181`, CLS pooling, 1024 float32 dimensions,
  512 tokens with 64 overlap;
- image `auditmanager-norms-worker:bge-m3-dense-v1-5617a9f`, built from
  `infra/norms-worker/Dockerfile` and its hashed wheel lock, run with `--network none`;
- owner direction (2026-10-19, direct polls in this session): the 6 GiB available-RAM
  floor of `W54-PLAN.md` §3.9 is waived for the image build and the encode windows; the
  night-window rule is not separately ruled on, and the disk floors are kept. The owner
  also approved removing the unmounted `estimat_test_*` Docker volumes to restore disk.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: before this task the promotion database held the embedding profile row and no
  embedding build and no embedding, so the build is created whole rather than extended.

### P-01 — embedding tables before the build

- captured_at: 2026-10-19
- command: `sed -n 49,52p docs/program/W54-SNAPSHOT-LOAD-01.md`
- captured_output:
  ```text
  - fingerprint rows: `norms_snapshot` 2, `norm_document` 1,348, `norm_paragraph` 698,971,
    `norm_chunk_build` 2, `norm_chunk` 111,557 (each exactly base plus repaired),
    `norm_embedding_profile` 1, and `norm_embedding_build`, `norm_embedding`,
    `norm_repair_call`, `norm_custody_*` all 0;
  ```
- interpretation: the verified dump of the previous task records one profile row and zero
  build and window rows; the table fingerprint of the new dump differs only there.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W54-EMBED-BUILD-01.md`;
- `docs/program/W54-EMBED-BUILD-01.md`;
- the promotion database and its volume `auditmanager-promotion-data` (the embedding
  `load` only);
- the local Docker image `auditmanager-norms-worker:bge-m3-dense-v1-5617a9f` (built, then
  removed) and its BuildKit cache;
- `.local/worktrees/code-first-entry/.local/norms/promotion-dumps/**` (the new dump and
  sidecars; `verify-dump.sh` prunes the older one);
- ignored `/root/projects/PDF-Analysis/.local/norms/builds/**` and
  `/root/projects/PDF-Analysis/.local/norms/promotion-records/20261019/**`;
- Docker volumes named `estimat_test_*`, unmounted, older than a day, removed only by the
  owner's poll answer, listed in `.local/cleanup/2026-10-19/estimat-test-volumes-removed.log`.

## Forbidden hotspots

`contracts/**`, migration files, root dependencies/locks, composition root, global styles,
the embedder, the image definition and its lock, the loader, source corpus bytes, the
ledger, the production stand, S3, `CURRENT_STATE.md`, remote `origin/main` and tags. Other
projects' processes, images, containers and volumes are not touched, except the owner-approved
`estimat_test_*` volumes above.

## Non-goals

No bundle export, no stand import, no deployment, no full gate, no search surface, no
retrieval-quality measurement on real vectors.

## Deliverables

- `embedding prepare` plan: 219 batches, plan SHA-256 recorded;
- the encode of all 219 batches to verified checkpoints (`embedding status`: 219 verified,
  0 missing, 0 invalid);
- `embedding load`: one transaction, completion row, stored digest equal to the checkpoints';
- a restore-verified dump;
- the image removed after the build, the promotion database stopped;
- measured throughput and memory, and the result report.

## Required checks

- `embedding status` over the checkpoint directory: 219 verified, 0 missing, 0 invalid;
- `embedding load` result: `created` true, 55,855 chunks, the digest of the last checkpoint
  line, which the repository recomputes from the stored rows;
- the dump's fingerprint shows `norm_embedding_build` 1 and `norm_embedding` equal to the
  window count, and the restore reproduces it (`.verified`);
- `git diff --check` and direct task `governance_findings` = `[]`.

## Integration contract

The recorded snapshot id, embedding-set digest and the verified dump are inputs of
`bundle export` (the build travels with the bundle) and of any later stand import. Nothing
here changes a contract or a runtime path.

## Failure/idempotency/security cases

`build` skips verified batches, so a kill costs at most the batch in flight and the run is
resumable under any supervisor. A checkpoint is written to a temporary name, fsynced and
renamed before its checksum sidecar; a full disk fails a write and leaves no accepted
checkpoint. `load` is one transaction and an exact replay is idempotent. The container has no
network and no database. Only this task's own PIDs, container and image are stopped; no
process is killed by pattern.

## Rollback / feature flag

Delete the embedding build rows of the snapshot, or restore the previous dump copy kept in
`promotion-dumps-keep/20261015-base/` (base snapshot only) and re-run the snapshot load.
Revert the two documentation files. No runtime, contract or deployed change.

## Handoff

- changed files: the allowed paths above;
- contracts: none;
- next: `bundle export` and `bundle verify` (`W54-BUNDLE-EXPORT-01`);
- forbidden hotspots remain untouched.
