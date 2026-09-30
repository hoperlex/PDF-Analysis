# Task NORM-LEDGER-01 — repaired corpus text reaches the deterministic projection

## Outcome

A repair ledger produced by `auditmanager.norms` changes the paragraphs and retrieval chunks
emitted for exactly the repaired blocks, under the repaired corpus snapshot identifier. A
ledger from another snapshot, a repair naming no source block, or repair metadata that does not
match the source is refused before any projected row is yielded.

## Depends on

- `W33-CORPUS` — completed: deterministic segmentation, chunking and base snapshot derivation
- `W39-CORPUS` — completed: repair ledger, repaired snapshot identity and re-recognition runner

## Frozen inputs

- domain contracts: `contracts/domain/v1/**` at `acc6463`, read only
- API contract: 17 paths / 20 operations / 61 schemas at `acc6463`, read only
- repair ledger format: `auditmanager.norms.repair.LEDGER_VERSION == "1"`
- migration head: `0011_document_section`, not touched
- base commit: `acc6463` (`alpha-w47`)

## Allowed paths

- `src/auditmanager/norms/segmentation.py`
- `src/auditmanager/norms/corpus_source.py`
- `src/auditmanager/norms/README.md`
- `tests/integration/norms/**`
- `docs/program/tasks/NORM-LEDGER-01.md`

## Forbidden hotspots

- `contracts/**`, `db/**`, `infra/**`, `web/**`
- root dependency and lock files
- composition root and global styles
- `.local/norms/corpus/**` — read only and not needed by the task's tests

## Non-goals

- No corpus persistence schema, migration or loader.
- No MinIO/S3 custody work.
- No embedding provider, tokenizer, pgvector extension or model call.
- No actual re-recognition of the 121 known degenerate blocks.
- No change to the repair-ledger file format or to the raw corpus drop.

## Deliverables

- repair-aware segmentation whose character offsets resolve against the effective repaired text
- repair-aware whole-corpus projection carrying the repaired snapshot identifier
- fail-closed validation of ledger snapshot, block key, page, original length and original digest
- tests proving repaired, unrepaired and invalid-ledger branches
- context README updated to describe the consumer seam that now exists

## Required tests

- Command: `.venv/bin/pytest tests/integration/norms -q`
  Expected: exit `0`; all norms tests pass.
- Command: `.venv/bin/pytest tests/integration/norms/test_repair_projection.py -q`
  Expected: exit `0`; every repair-projection branch passes independently.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

Callers derive the raw snapshot from the corpus, derive the effective snapshot with
`repaired_snapshot` when a ledger exists, and pass that effective identifier to
`segment_corpus`. The function validates the identifier and ledger against the source before
yielding the first document. Chunks always carry the identifier of the text they actually
contain.

## Failure/idempotency/security cases

- Re-running the same corpus and ledger emits byte-identical paragraphs and chunks.
- An unapplied repair leaves the raw block text and the base snapshot unchanged.
- A ledger for a different base snapshot is refused.
- An applied repair with an unknown block, wrong page, wrong original length or wrong original
  SHA-256 is refused rather than ignored or applied heuristically.
- No provider credential, corpus text or source bytes are logged.

## Rollback / feature flag

Additive internal seam with no public contract or migration. Reverting this task restores the
pre-existing raw-only projection; no stored state is created by this task.

## Handoff

- changed files: `src/auditmanager/norms/segmentation.py`, `src/auditmanager/norms/corpus_source.py`, `src/auditmanager/norms/README.md`, `tests/integration/norms/test_repair_projection.py`, `docs/program/tasks/NORM-LEDGER-01.md`.
- commands/results: targeted repair projection — `11 passed`; all norms tests — `73 passed`; real-corpus read-only check — 674 documents, 28,249 blocks, 55,702 chunks, base snapshot `2026-07-23..2026-08-20+17d.4b74348debf7`.
- full gate: `GATE OK` — backend `2615 passed, 5 skipped, 4 warnings, 169 subtests passed`; foundation `35 passed`; frontend lint/typecheck and `1162` tests passed.
- new/changed contracts: none; API schemas, frozen identifiers and migration head remain unchanged.
- known limits/integration: no real repaired ledger exists until provider credentials are available; persistence is still absent; callers must pass the ledger-derived effective snapshot ID together with the ledger; the future persistence task must resolve opaque entity identity versus content-derived snapshot keys and canonical paragraphs versus rebuildable chunks.
- forbidden-hotspot proof: final `git status --short` contains only the five allowed paths above; `contracts/**`, migrations, root dependencies/locks, composition root, global styles, infrastructure, web UI and `.local/norms/corpus/**` were not changed.
