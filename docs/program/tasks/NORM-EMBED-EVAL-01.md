# Task NORM-EMBED-EVAL-01 — corpus-grounded embedding bake-off

## Outcome

A reproducible benchmark over the real Russian normative corpus measures candidate tokenizers
and embedding models, reports retrieval quality and CPU operating cost, and recommends one
fully pinned embedding profile. Oversized canonical paragraphs are assigned a lossless
row-aware/token-window policy; nothing is silently truncated or AI-summarised.

## Depends on

- `NORM-PERSIST-01` — completed in the working tree: canonical paragraphs are separate from
  rebuildable retrieval chunks
- `NORM-ID-01` — completed before any persisted retrieval projection references public
  canonical entities

## Frozen inputs

- owner ruling of 2026-09-30: split long material by table rows and deterministic token windows;
  no AI summary and no truncation
- real read-only corpus content key `2026-07-23..2026-08-20+17d.4b74348debf7`
- source corpus path `.local/norms/corpus/**` is read only and excluded from Git
- no embedding dependency or model is frozen before the measured bake-off
- no GPU is available in the evaluation environment

## Ownership

This task owns only the evaluation fixture, runner, report and embedding-profile recommendation.
It does not own root dependencies, a pgvector migration, production model downloads, API/UI,
provider credentials or persisted embeddings.

## Allowed paths

- `docs/program/tasks/NORM-EMBED-EVAL-01.md`
- `docs/program/NORM_EMBEDDING_BAKEOFF.md`
- `docs/program/NORM_CORPUS_DECISION_BACKLOG.md`
- `docs/program/CURRENT_STATE.md`
- `tools/norms/embedding_bakeoff.py`
- `fixtures/evaluation/norms/**`
- `tests/integration/norms/test_embedding_bakeoff_fixture.py`
- `/tmp/**` for an isolated evaluation environment and model cache

## Forbidden hotspots

- root dependency/lock files and production settings
- contracts, migrations, composition root and global styles
- source corpus `.local/norms/corpus/**`
- MinIO/storage/ingest code
- persisted pgvector data, search API or UI

## Non-goals

- No production dependency selection by public leaderboard alone.
- No synthetic claim that the benchmark is an expert relevance judgment.
- No LLM-generated canonical query labels or changes to normative text.
- No embedding of all corpus rows if bounded CPU/RAM makes that unsafe; sampling must be explicit.

## Deliverables

- source-grounded Russian query/relevance fixture with canonical source anchors
- runner that validates anchors, counts actual model tokens, embeds the same candidates, and
  computes recall@k, MRR, latency/throughput and vector storage estimates
- full-corpus tokenizer long-tail measurements for viable finalists
- report pinning model repository/revision, tokenizer, query instruction, pooling, dimensions,
  normalization, distance metric, limits and long-paragraph split policy
- an explicit GO/NO-GO recommendation for the later dependency/pgvector slot

## Required tests

- `.venv/bin/pytest tests/integration/norms/test_embedding_bakeoff_fixture.py -q`
- evaluation command recorded verbatim in the report
- `.venv/bin/pytest tests/integration/norms -q`
- `git diff --check`

Expected: fixture/tests pass; every reported number is machine-produced from the pinned fixture,
model revision and real corpus projection.

## Integration contract

- later pgvector work may consume only a profile marked recommended and fully pinned by this task
- every retrieval unit maps losslessly to one or more canonical paragraph identities/anchors
- token limits are enforced before model inference; no provider/library default truncation
- changing model revision, tokenizer, instruction, pooling, dimension or distance creates a new
  embedding profile and a complete rebuild, never an in-place semantic mutation

## Failure / idempotency / security cases

- missing corpus/model/cache fails loudly and does not fabricate metrics
- fixture anchor drift fails validation before scoring
- a text over the profile token limit is split deterministically with complete character coverage
- rerunning the same pinned inputs produces the same fixture membership and metric definitions
- source text remains local; the benchmark uses local models only unless a later task explicitly
  authorizes an external provider

## Rollback / feature flag

Evaluation-only: remove the recommendation/fixture/runner. No runtime behavior or stored vector
is changed. Model caches live under `/tmp` and are not project artifacts.

## Handoff

- changed files: pinned Russian retrieval fixture and three recorded result JSONs; exact
  tokenizer/window runner; fixture/result guards; `NORM_EMBEDDING_BAKEOFF.md`; decision backlog
  and current state
- commands/results: exact fixture/runner hashes are
  `0f3831e90448e85a7957ef0dbd3077efbf4534a189f14a7c5c8a2c7b9c9e3210` /
  `9127e36eca3300ff82f5c6b280075513808d6fe0edd8ec568dcf1be7d427732c`;
  targeted combined suite **122 passed**; `make gate` prints literal **`GATE OK`**
- contracts: no runtime/API/domain contract changed in this task; recommended profile
  `bge-m3-dense-v1` is an evaluation-to-integration contract for the next owned slot
- known limits: 24 single-relevant-paragraph judgments and a deterministic 512-paragraph
  candidate pool are not expert full-corpus acceptance; single-query serving latency, pgvector
  ANN recall/index overhead, hybrid retrieval and reranking remain unmeasured
- integration notes: consume only BGE-M3 revision
  `5617a9f61b028005a4858fdac845db406aefb181`, CLS/1024/float32/L2/inner-product,
  512 total tokens and 64 content-token overlap; any profile change means a complete rebuild
- forbidden-hotspot proof: no root dependency/lock, migration, composition, API/UI,
  source-corpus or MinIO/storage file changed; the evaluation environment/cache lived under
  `/tmp` and was removed after the raw JSON results were checked into the fixture directory
