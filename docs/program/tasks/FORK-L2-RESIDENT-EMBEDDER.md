# Task FORK-L2-RESIDENT-EMBEDDER — a resident BGE-M3 F32 embedder

## Outcome
A compose service `embedder` serves the profile `bge-m3-dense-v1` in its exact runtime:
- model: BAAI/bge-m3 `5617a9f61b028005a4858fdac845db406aefb181`, fp32, CLS pooling, 1024 dimensions, 512 tokens with 64 overlap;
- runtime: the norms-worker image, `transformers` 4.53.3, `sentence-transformers` 5.0.0, `torch` 2.7.1 CPU;
- no database access and no external port; the worker writes the vectors;
- limits: `mem_limit` 4g, at most 8 of 12 cores, `oom_score_adj` 1000.

It replaces the temporary int8 `norm-embed` for run-time norm queries, so the corpus and the queries use the same model. It also replaces the night encoder.

## Owner and paths
The fork's embedding lane:
- `infra/deploy/compose.server.yml` and `infra/norms-worker/**`;
- `src/auditmanager/norms/semantic.py` and the embed client;
- `infra/deploy/lib/first_install_env.py` defaults;
- the tests.

## Depends on
- `FORK-L0-MEASURE`, for the limits and the p95.

## Env change
Add `ALPHA_MEM_LIMIT_EMBEDDER=4g`, `ALPHA_EMBEDDER_CPUS=8` and `AUDITMANAGER_EMBED_URL=http://embedder:8080`.
In the same change, remove `ALPHA_NORM_EMBED`, `ALPHA_MEM_LIMIT_NORM_EMBED`, `AUDITMANAGER_NORM_EMBED_URL`, `ALPHA_EMBEDDER` and the night-window timer.

## Inputs
`ADR-0020` decision 7 (fork bullet and the `R-156o` amendment); `ADR-0021` section 11.

## Checks
- `docker compose config`.
- The image self-check.
- The wiring tests.
- The `semantic_check` quality gate against the corpus, as `NORM-VECTOR-TEMP-01.md` gives it.
- The p95 from L0.

## Integration and rollback
Keep `norm-embed` deployable until L2 is verified on the server.

## Enumerator ownership
- enumerated_set_changed: no

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none

## Publication authority
- development_target: origin/dev
- origin_main_authority: none; the fork's delegated release integrator publishes main
