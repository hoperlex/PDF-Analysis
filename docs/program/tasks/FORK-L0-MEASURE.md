# Task FORK-L0-MEASURE — measure the fork server before relying on its limits

## Outcome
Measured figures replace the thesis numbers of `docs/program/FORK_ROADMAP.md`. Each figure is recorded with its command and the tree it ran on:
- RSS and CPU of every service under a 500-page run;
- the embedder's single-request p95, alone and while LLM workers run: a norm query up to 128 tokens, and a finding view up to 512 tokens;
- the batch latency of 20 finding views;
- the resulting `ALPHA_MEM_LIMIT_*` values and `AUDITMANAGER_WORKER_SLOTS`.

## Owner and paths
The fork's measurement lane. It records into `docs/program/` (a measurement note) and changes `infra/deploy/env/alpha.env` on the server only through the documented variables.

## Depends on
- The first install (`infra/deploy/first-install.sh`) finished with `DONE`.

## Inputs
- `R-156o`: «Задержки p95 и производительность при одновременной работе LLM-воркеров ещё необходимо проверить».
- `ADR-0021` section 11; the `AD-04` measurement.
- The bake-off for comparison: BGE-M3 F32 peak RSS 3,177.9 MiB at batch 16; 1.252 windows/s on 8 threads (`docs/program/NORM_EMBEDDING_BAKEOFF.md`).

## Checks
- Each figure carries its command, the date, the SHA of the tree and the output.
- `infra/deploy/verify-deployed.sh` passes after the limits change.

## Integration and rollback
New limits ship as env values. Rolling back means restoring the previous values and running `deploy.sh`.

## Enumerator ownership
- enumerated_set_changed: no

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none

## Publication authority
- development_target: origin/dev
- origin_main_authority: none; the fork's delegated release integrator publishes main
