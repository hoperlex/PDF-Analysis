# Normative corpus embedding bake-off

Status: measured 2026-09-30 on the real corpus. Decision: **GO with
`bge-m3-dense-v1` for the later pgvector implementation slot**. This is an engineering
profile decision, not a corpus-search release acceptance.

## Reproducible inputs

- corpus content key:
  `2026-07-23..2026-08-20+17d.4b74348debf7`
- corpus shape: 674 documents, 348,777 canonical paragraphs and 55,702 current
  character chunks
- fixture: 24 human-authored Russian questions, one exact canonical paragraph anchor each
- candidate pool: relevant paragraphs plus 20 lexical hard negatives per query, then
  deterministic hash-ordered distractors to exactly 512 paragraphs
- fixture SHA-256:
  `0f3831e90448e85a7957ef0dbd3077efbf4534a189f14a7c5c8a2c7b9c9e3210`
- runner SHA-256:
  `9127e36eca3300ff82f5c6b280075513808d6fe0edd8ec568dcf1be7d427732c`
- raw machine results: `fixtures/evaluation/norms/results/{bge-m3,qwen3-embedding-0.6b,multilingual-e5-base}.json`

The fixture is source-grounded but not an expert relevance panel. It deliberately includes hard
cases whose relevant paragraph has a crude full-corpus lexical rank as low as 6,288. The metric
is rank of the one labelled paragraph (or any deterministic token window of it) among the
model-specific windows of the same candidate set.

## Models and runtime

| Candidate | Exact revision | License | Query mode | Pooling | Batch |
|---|---|---|---|---|---:|
| [BGE-M3](https://huggingface.co/BAAI/bge-m3) | `5617a9f61b028005a4858fdac845db406aefb181` | MIT | plain | CLS | 16 |
| [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) | `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3` | Apache-2.0 | bundled `query` prompt | last token | 8 |
| [multilingual-e5-base](https://huggingface.co/intfloat/multilingual-e5-base) | `d128750597153bb5987e10b1c3493a34e5a4502a` | MIT | `query: ` / `passage: ` | mean | 16 |

The isolated, non-production environment used Python 3.12.3,
`torch==2.7.1+cpu`, `transformers==4.53.3`,
`sentence-transformers==5.0.0`, `tokenizers==0.21.4` and `numpy==2.5.3`.
The host exposed 8 cores of an AMD EPYC 9655 and no GPU. Model files were warm in
`/tmp/norm-embed-hf-cache`; model-load times are therefore not cold-start measurements.
No project dependency or lock file was changed.

Reproduction, once the isolated environment contains those exact packages:

```bash
HF_HOME=/tmp/norm-embed-hf-cache TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
  /tmp/norm-embed-eval-env/bin/python tools/norms/embedding_bakeoff.py \
  --corpus .local/norms/corpus \
  --fixture fixtures/evaluation/norms/retrieval_queries.v1.json \
  --model bge-m3 \
  --output /tmp/norm-embed-bge-final.json \
  --threads 8
```

Repeat with model keys `qwen3-embedding-0.6b` and `multilingual-e5-base`.
The JSON result includes the fixture/runner hashes, runtime versions, all ranks and full-corpus
token statistics.

## Measured result

| Model | MRR | R@1 | R@5 | R@10 | Candidate windows | 24-query batch | Passage windows/s | Peak RSS | Dim | float32 storage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **BGE-M3** | **0.848611** | **0.750000** | **0.958333** | 1.000000 | 563 | 4.866 s | 1.252 | 3,177.9 MiB | 1024 | 243.46 MiB |
| Qwen3 0.6B | 0.768849 | 0.625000 | 0.916667 | 1.000000 | 576 | 86.355 s | 0.650 | 4,124.2 MiB | 1024 | 262.28 MiB |
| multilingual-E5-base | 0.782407 | 0.666667 | 0.875000 | 1.000000 | 563 | **3.300 s** | **1.630** | **2,285.6 MiB** | 768 | **182.82 MiB** |

`float32 storage` is the raw vector payload for the model-specific lossless windows of the
55,702 current character chunks. It excludes PostgreSQL row, index and alignment overhead.
The 24-query value is one batched run and must not be divided by 24 or presented as interactive
single-query latency.

BGE wins the domain-grounded quality test: it places 23/24 answers in top 5 and 18/24 at rank
one. E5 is the CPU/storage winner but places only 21/24 in top 5. Qwen is worse than BGE on
quality and materially worse on every measured operating-cost dimension. The local result,
not a public leaderboard, determines the recommendation.

## Actual tokenizer long tail

All counts below are inference-ready counts: model special tokens and any required passage
prefix are included. `windows` is the exact number after 512-total-token windows with
64-content-token overlap.

| Model | Projection | Total content tokens | Max inference tokens | p50 / p95 / p99 | Rows >512 | Windows |
|---|---|---:|---:|---:|---:|---:|
| BGE | canonical paragraphs | 18,225,890 | 18,306 | 32 / 134 / 509 | 3,453 | 354,474 |
| BGE | current character chunks | 18,225,890 | 18,306 | 285 / 605 / 1,116 | 4,379 | 62,325 |
| Qwen | canonical paragraphs | 24,229,893 | 16,620 | 44 / 176 / 598 | 4,331 | 356,939 |
| Qwen | current character chunks | 24,294,375 | 16,620 | 391 / 713 / 1,386 | 7,606 | 67,143 |
| E5 | canonical paragraphs | 18,225,890 | 18,308 | 34 / 136 / 511 | 3,482 | 354,530 |
| E5 | current character chunks | 18,225,890 | 18,308 | 287 / 607 / 1,118 | 4,428 | 62,401 |

These measured values supersede the W33 token estimate. Tokenizer warnings while counting a
long paragraph are diagnostic only: no over-limit value is passed to a model.

## Frozen recommended profile

`bge-m3-dense-v1` means exactly:

- repository `BAAI/bge-m3`, revision
  `5617a9f61b028005a4858fdac845db406aefb181`;
- tokenizer from that same revision, `transformers==4.53.3` and
  `sentence-transformers==5.0.0`;
- plain query and passage text, no instruction; bundled CLS pooling;
- 1024-dimensional float32 vector, L2-normalized before persistence;
- pgvector `vector(1024)`, inner-product operator class over normalized vectors
  (cosine-equivalent ordering);
- total inference limit 512 tokens, including two special tokens; 64 content-token overlap;
- no half precision, quantization or dimension reduction until separately measured;
- every model/tokenizer/pooling/dimension/normalization/distance change creates a new profile
  and complete rebuild.

The retrieval projection is rebuilt from canonical paragraphs and never becomes normative
evidence. It does not cross a document boundary. Existing canonical table rows are boundaries;
whole consecutive paragraphs may be packed while the prepared input stays within 512 tokens.
If one paragraph is too long, fast-tokenizer character offsets produce deterministic substrings
whose prepared inputs are each at most 512 tokens and whose 64-token overlaps cover the source
from first through last character. Every window records its canonical paragraph IDs and source
character spans. There is no public chunk ID, truncation or AI summary.

## GO boundary and remaining acceptance work

GO means the next owned slot may add a pgvector-capable PostgreSQL image, migration, embedding
projection and idempotent rebuild worker using only the profile above. It does not authorize a
search API/UI contract or claim production search quality.

Before release, the next slots still must measure:

- single-query warm/cold latency in the production serving runtime;
- exact pgvector scan/HNSW recall and index/storage overhead on all 62,325 BGE windows;
- expert multi-relevance judgments, failure queries and full-corpus search rather than a
  512-candidate model bake-off;
- hybrid lexical+dense retrieval and optional reranking as separate, measured profiles.

The current pinned PostgreSQL image does not expose the `vector` extension. Choosing a
supply-chain path for pgvector is therefore an explicit owner decision, not an implicit change
inside this evaluation task.
