# Task NORM-ADR-01 — freeze the alpha normative-runtime topology

## Outcome

The architecture authority, normative decision register and active roadmaps agree on one alpha
topology: canonical normative text is stored in the existing PostgreSQL service, dense retrieval
is a rebuildable pgvector projection in that same service, source PDFs/crops are immutable private
S3 Blobs, and the local filesystem drop is never an alpha runtime dependency.

## Depends on

- `NORM-INT-01` — completed: canonical corpus foundation published
- `NORM-VECTOR-01` — completed: PostgreSQL/pgvector schema and repository published
- `NORM-CUSTODY-01` — completed: source PDF/crop custody design
- `MINIO-IMAGE-01` — completed: repository-owned MinIO image packaging restored

## Frozen inputs

- owner ruling 2026-10-01: for alpha use one PostgreSQL + pgvector; no separate distributed
  vector database; source PDF/crop bytes live only in MinIO
- API: 17 paths / 20 operations / 61 schemas; unchanged
- domain candidate revision 8 with 27 identities; unchanged
- migration head: `0013_norm_embeddings`; unchanged
- base commit: `3489378`

## Ownership

This task owns the new normative-runtime ADR and the programme prose needed to reconcile the
earlier P05-only plan with the already integrated alpha PostgreSQL/pgvector foundation. It owns no
runtime, migration, contract, dependency, composition or external-service slot.

## Allowed paths

- `docs/architecture/adr/ADR-0020-normative-corpus-alpha-runtime.md`
- `docs/architecture/ADR_INDEX.md`
- `docs/program/tasks/NORM-ADR-01.md`
- `docs/program/NORM_CORPUS_DECISION_BACKLOG.md`
- `docs/program/ROADMAP.md`
- `docs/program/ALPHA_ROADMAP.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

- `contracts/**`, `db/**`, root dependency/lock files and composition root
- source/runtime code, API/router/UI and global styles
- storage/MinIO implementation, object bytes, volumes, keys and credentials
- `.local/norms/corpus/**`
- accepted historical task handoffs and CP-00 review evidence

## Non-goals

- No corpus import, PDF/crop upload, provider call or vector generation.
- No selection of the exact database snapshot promotion/transport format.
- No search API/UI, runtime embedding worker or run-admission change.
- No assertion that the 121-page repair ledger or a complete embedding build exists.
- No external/distributed vector service.

## Deliverables

- ADR-0020 with authority layers, alpha deployment topology, bootstrap/runtime boundary and
  measurable revisit triggers
- indexed post-CP-00 status for the owner-approved ADR
- `NORM-Q09` owner decision recording the same alpha topology
- roadmap corrections for the pulled-forward pgvector foundation, canonical granularity and
  runtime exclusion of the filesystem drop
- current-state note naming the remaining promotion/repair/embedding/search work

## Required tests

- `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`
  - expected: no new violation relative to the frozen base; the base carries five known
    regex-like prose strings that the link scanner misclassifies as broken links
- `.venv/bin/pytest tests/contract/api_v1/test_doc_prose_facts.py -q`
  - expected: all live-prose guards pass
- `git diff --check`
  - expected: exit 0

## Integration contract

- alpha has no second vector network service: pgvector is installed in the existing PostgreSQL
  derivative and shares its backup/restore boundary
- `norms_snapshot`, `norm_document` and `norm_paragraph` are canonical; chunk and embedding rows
  are rebuildable and never cited as normative authority
- source PDF/crop bytes are private S3 objects referenced by opaque `blob_id`; no local path,
  filename, bucket or object key becomes identity
- `.local/norms/corpus/**` may be read by an offline/bootstrap producer, but is never copied into
  an alpha image, mounted as a serving dependency or configured in alpha env
- a later external/distributed vector service requires a superseding ADR and measured trigger

## Failure/idempotency/security cases

- absent canonical paragraph or snapshot is a typed failure; search never falls back to a file
- absent vector build is observable/not-ready; it never changes paragraph authority
- absent MinIO source binding prevents source-byte evidence/re-recognition, never invents it
- database restore restores canonical text and its pgvector projection together for alpha
- internal-use/licensing boundary remains unchanged; this ADR authorizes no corpus publication

## Rollback / feature flag

Documentation/decision task only. There is no behavior flag. Replacing the topology requires a
new superseding ADR; deleting this record would not roll back the already published database
schema and is not a valid recovery action.

## Handoff

- Changed files: ADR-0020, `ADR_INDEX.md`, `ROADMAP.md`, `ALPHA_ROADMAP.md`,
  `CURRENT_STATE.md`, `NORM_CORPUS_DECISION_BACKLOG.md` and this task record.
- Checks:
  - `.venv/bootstrap/bin/python scripts/validate_bootstrap.py` — the new tree is fully scanned
    (`161` JSON, `437` Markdown, `20` ADRs) and exits 1 on the same five pre-existing
    regex-like broken-link findings as a clean clone of base `3489378` (`161` JSON,
    `435` Markdown, `19` ADRs); no new finding;
  - `.venv/bin/pytest tests/contract/api_v1/test_doc_prose_facts.py -q` — `26 passed`;
  - `git diff --check` — exit 0.
- New/changed contracts: none. ADR-0020 and `NORM-Q09` freeze an operational topology but do
  not change API, domain, event, migration or environment contracts.
- Risks/known limitations: alpha still has no promoted corpus rows, complete embedding build,
  corpus search consumer or credentialed 121-page repair result. PostgreSQL and MinIO must both
  be backed up for complete evidence recovery even though vectors remain rebuildable.
- Integrator instruction: commit this seven-file documentation/decision slice on top of
  `3489378` and fast-forward `origin/main`; do not tag it as a release. Dispatch subsequent
  custody/promotion/search work against ADR-0020 and keep `.local/norms/corpus/**` outside the
  serving deployment.
- Forbidden-hotspot proof: the final status is limited to the seven allowed documentation paths.
  No `contracts/**`, migration, dependency/lock, composition, source/runtime, storage, UI,
  global-style or corpus file changed.
