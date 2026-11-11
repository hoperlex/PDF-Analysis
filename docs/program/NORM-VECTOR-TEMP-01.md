# NORM-VECTOR-TEMP-01 — semantic norm candidates on the stand (TEMPORARY)

Status: **plan for the deployment; the run-side code is merged and off.** Owner decisions of 2026-11-11: variant C (a quantized
BGE-M3 on the stand), marked temporary until the database side gets its own embedder decision; deployment of the embedder is planned
first, the run-side code ships as a hotfix.

## Why

Prod runs of 2026-11-11 (section КМ) showed the norm verification's reach:

| Run | Observations | Asked a norm question | Got candidates | Without a question |
|---|---|---|---|---|
| `run_01M74MFHN6H5M4NVBQA31HWRDN` (before NORM-ANY-WORDS-01) | 36 | 10 | 0 | 26 |
| `run_01M74QBEJZ42TEVSG43XPZDV59` (after it) | 37 | 14 | 14 | 23 |

The word search now serves every observation that asks a question. The ones that ask none -- above all the primary text findings,
whose stage never names norms -- get no norm check at all. The corpus already carries vectors; a run cannot make the vector of its
own text, so it cannot use them.

## What is already on the stand (owner's read, 2026-11-11)

- `pgvector` 0.8.6; `norm_embedding` holds 61 573 windows of profile `bge-m3-dense-v1` for snapshot
  `ns_01M59N8QNBVN91ACA2HCE6VE74`; index `ix_norm_embedding_hnsw_ip` (`hnsw`, `vector_ip_ops`, m 16, ef_construction 64).
- `NormEmbeddingRepository.nearest()` (W54-EMBED-01) answers the nearest windows for a unit query vector.
- Memory: 3 914 MB total, ~2 033 MB available, swap 523 MB in use. No norms-worker image on the host.

## What is merged (run side, off)

- `src/auditmanager/norms/semantic.py`: `embed_text` (HTTP client), `semantic_norm_candidates` (vector → `nearest()` → the longest
  reliable paragraph of each window, in the word search's candidate shape, `candidate_not_verified`).
- `runs/extended_review._norms`: after the word search, observations left without a paragraph (`not_found`, or `query_not_proposed`)
  are looked up by meaning; they carry `norm_lookup_method: semantic_temporary`, and the norm review judges every candidate.
- Off unless the worker has `AUDITMANAGER_NORM_EMBED_URL`. A failure is never quiet: each affected observation becomes
  `unavailable / semantic_lookup_failed` (a gap, so «Нормы» is partial and says why), the run warns `norm_semantic_lookup_failed`,
  and the worker logs the traceback. More than 60 lookups in a run: `semantic_lookup_window_exhausted`, the same way.

## The embedder service — the plan

1. **Image `infra/norm-embed/`** (its own `requirements.lock`; the root lock is not touched):
   - base: the `python:3.12-slim-bookworm` digest `infra/deploy/Dockerfile.api` already pins;
   - wheels: `onnxruntime`, `tokenizers`, `numpy`, hash-pinned, `--only-binary=:all:`;
   - model: `Xenova/bge-m3` at a pinned revision, `onnx/model_int8.onnx` (568 456 694 bytes) and `tokenizer.json`, fetched by
     literal URL with `ADD --checksum`; the self-check runs under `RUN --network=none`; the image runs offline;
   - server: standard-library HTTP; `POST /v1/embed {"texts": [...]}` → `{"vectors": [[1024 floats]]}`; `GET /healthz`; CLS pooling,
     L2-normalised, 512 tokens, 2 threads; batch of at most 16 texts.
2. **Compose** (`infra/deploy/compose.server.yml`): service `norm-embed`, no published port, the stack's internal network,
   `mem_limit` 1400m, `restart: unless-stopped`, a health check on `/healthz`; the worker gets
   `AUDITMANAGER_NORM_EMBED_URL=http://norm-embed:8080`. Turning it off is removing that variable.
3. **Quality gate before the variable is set** (the int8 model is compared against fp32 corpus vectors): a one-off job on the stand
   embeds 500 corpus windows' own texts with the service and measures (a) the inner product with each stored vector -- mean ≥ 0.97 --
   and (b) self-recall@10 through the HNSW index -- ≥ 0.90. Below either: do not enable; fall back to variant A (more memory and the
   full-precision norms-worker model).
4. **Memory gate:** `free -m` and the worker's RSS before and after the service starts and during one run; the service is expected at
   0.9–1.1 GB. If available memory drops under 600 MB or swap grows during a run: stop the service and take variant A.
5. **Rollout:** deploy the image and service with the variable unset → quality gate → memory gate → set the variable → one prod run →
   read `norm_status / norm_lookup_method` counts with the operator → release note.
6. **Rollback:** unset the variable (the run side goes back to the word search alone); remove the service.

## Removal

This is a stop-gap. The permanent embedder for run-time text is a database-side decision still to be made; the precedents' night
encoder (`ADR-0029` decision 8) is the stand's sanctioned embedder today and cannot answer inside a run. When that decision lands,
`norms/semantic.py`, `infra/norm-embed/` and the compose service go, and `semantic_temporary` candidates stop.

## Open for the owner

- Build on the stand: the image downloads ~570 MB at build time; the host's free disk must be checked first.
- Whether the quality gate's thresholds (0.97 / 0.90) are the right bar.
