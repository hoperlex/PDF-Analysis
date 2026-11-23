# Task FORK-L5-PG-TUNING — PostgreSQL and memory limits for a 32 GB server

## Outcome
Compose passes `postgres -c …` settings from env:

| Variable | Value |
|---|---|
| `ALPHA_PG_SHARED_BUFFERS` | 3GB |
| `ALPHA_PG_WORK_MEM` | 32MB |
| `ALPHA_PG_MAINTENANCE_WORK_MEM` | 1GB |
| `ALPHA_PG_EFFECTIVE_CACHE_SIZE` | 12GB |
| `ALPHA_PG_MAX_CONNECTIONS` | 100 |

The memory limits are set from the `FORK-L0-MEASURE` figures. Starting points: postgres 6g, s3 1g (until LS3), api 1536m, worker 2560m, web 640m, proxy 128m.

## Owner and paths
The fork's infra lane: `infra/deploy/compose.server.yml`, `infra/deploy/env/alpha.env.example`, `infra/deploy/lib/first_install_env.py` defaults, and the compose tests.

## Depends on
- `FORK-L0-MEASURE`.

## Checks
- `docker compose config`.
- The compose limit tests.
- A measurement under a run after the change.

## Integration and rollback
Unset variables keep PostgreSQL's defaults, so emptying them is the rollback.

## Enumerator ownership
- enumerated_set_changed: no

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none

## Publication authority
- development_target: origin/dev
- origin_main_authority: none; the fork's delegated release integrator publishes main
