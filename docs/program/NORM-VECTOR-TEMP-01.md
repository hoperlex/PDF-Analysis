# NORM-VECTOR-TEMP-01 — semantic norm candidates on the stand (TEMPORARY)

Status: **the service is built and deployable behind `ALPHA_NORM_EMBED`; the run-side code is merged and off.** Owner decisions of 2026-11-11: variant C (a quantized
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

## The embedder service

Owner decisions of 2026-11-11 (poll): deploy by this plan; quality thresholds 0.97 and 0.90; the stand's free disk is checked first.

1. **Image `infra/norm-embed/`** (its own `requirements.lock`; the root lock is not touched): the `python:3.12-slim-bookworm`
   digest `infra/deploy/Dockerfile.api` pins; `numpy` 2.2.1, `onnxruntime` 1.20.1 and `tokenizers` 0.21.0, hash-pinned,
   `--no-deps --only-binary=:all:`; `Xenova/bge-m3` at revision `4de13258303883538bd53b696b452bf8099f0858`,
   `onnx/model_int8.onnx` (568 456 694 bytes, sha256 `a206e10e…`) and `tokenizer.json` (sha256 `6710678b…`) by `ADD --checksum`;
   a self-check under `RUN --network=none`; `USER nobody`; standard-library HTTP: `POST /v1/embed {"texts": [text]}` (one text),
   `GET /healthz`; CLS pooling, L2-normalised, 512 tokens, 2 threads, the onnxruntime arena off.
2. **Measured on adm1, 2026-11-11** (the same wheels and model, outside docker): 841 MB resident after load, 917 MB after long
   texts, 0.45 s per 512-token text; a batch of sixteen long texts peaked at 2.3 GB -- hence one text per request. The self-check
   ranks «катет углового сварного шва» nearer to «минимальный катет сварного шва» (0.728) than to «лестница жилого дома» (0.316).
3. **Compose** (`infra/deploy/compose.server.yml`): service `norm-embed` IN THE PROFILE `norm-embed`, no published port, the stack's
   network, `mem_limit: ${ALPHA_MEM_LIMIT_NORM_EMBED:-0}` (the stack's rule; the plan's value 1200m), a health check on `/healthz`.
   `ALPHA_NORM_EMBED=yes` (default `no`) makes `deploy.sh` demand the limit, put the profile into every compose command (so the
   image is built with the others and `up -d` starts it) and judge its health in `services-healthy`; `verify-deployed.sh` checks it
   is running/healthy. With `no` nothing is downloaded and the stack is what it was. The worker gets
   `AUDITMANAGER_NORM_EMBED_URL` (empty by default: the lookup is off).
4. **Rollout** on the stand, in `/srv/auditmanager`:
   1. `df -h /` and `docker system df`: the build needs ~0.8 GB (the model and wheels; the base layers are the API image's);
   2. in `infra/deploy/env/alpha.env`: `ALPHA_NORM_EMBED=yes`, `ALPHA_MEM_LIMIT_NORM_EMBED=1200m`, `AUDITMANAGER_NORM_EMBED_URL` left
      empty; deploy (`infra/deploy/deploy.sh`, or the next main deploy);
   3. **memory gate**: `free -m` and `docker stats --no-stream` -- available memory stays above 600 MB and swap does not grow;
   4. **quality gate**: `docker compose --env-file infra/deploy/env/alpha.env -f infra/deploy/compose.server.yml exec -T worker
      python -m auditmanager.norms.semantic_check --url http://norm-embed:8080 --windows 500` -- PASS needs a mean inner product
      ≥ 0.97 against the stored full-precision vectors and self-recall@10 ≥ 0.90; FAIL means variant A (more memory and the
      full-precision model), not a lower bar;
   5. both pass: `AUDITMANAGER_NORM_EMBED_URL=http://norm-embed:8080`, restart the worker (`docker compose ... up -d worker`);
   6. one prod run; read `norm_status / norm_lookup_method` counts with the operator; then the release note.
5. **Rollback**: empty `AUDITMANAGER_NORM_EMBED_URL` and restart the worker (the word search alone, as before); `ALPHA_NORM_EMBED=no`
   and `docker compose --profile norm-embed rm -sf norm-embed` removes the service.

## Removal

This is a stop-gap. The permanent embedder for run-time text is a database-side decision still to be made; the precedents' night
encoder (`ADR-0029` decision 8) is the stand's sanctioned embedder today and cannot answer inside a run. When that decision lands,
`norms/semantic.py`, `infra/norm-embed/` and the compose service go, and `semantic_temporary` candidates stop.

## Open for the owner

- The stand's free disk (`df -h /`) before `ALPHA_NORM_EMBED=yes`.
