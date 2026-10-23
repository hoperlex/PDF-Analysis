# AR-V3-BETA-COST-REFUSAL-01 — v3 cost and terminal refusal boundary

The v3 worker now checks the configured per-Run ceiling against persisted opening spend before any new provider dispatch. It checks the sole canonical completed call again before CITE, including recovery and an already saved CITE stage. An over-ceiling call remains in the durable model journal but cannot produce a successful review terminal. A metered call with no recorded cost amount also refuses; an explicitly unmetered connection retains its zero-cost provenance.

The carrier now records an escaping typed `DomainError` as the terminal reason for the exact v3 profile/bundle pair. Legacy and mixed identities retain the existing generic crash reason. Terminal details still pass through the repository's catalogue screen.

## Verification and handoff

- Task: [AR-V3-BETA-COST-REFUSAL-01](tasks/AR-V3-BETA-COST-REFUSAL-01.md), frozen from `e4c3ae357e19205d62d7652660aefaa9d0ceecd2`.
- Focused v3 worker, cost/refusal, executor guard, terminal, composition, journal and CITE tests: 82 passed.
- Python compile and `git diff --check`: passed. Full `make gate` remains deferred under R-135; this host has no reachable local PostgreSQL.
- No shared contract, migration, root lockfile/dependency, composition root, global style, normative map or product version changed.

## Remaining integration work

The API and worker still install empty trusted-pack registries; v3 production starts remain closed until exact six-set review and activation. The cost ceiling is resolved from the worker's provider configuration for each execution, as with legacy Runs; it is not a frozen Run field. A controlled PostgreSQL/Blob/provider acceptance run must verify budget, lease recovery, reply readback and the failed terminal on the target stand. The review artifact still needs a user-visible read path and six-Run aggregation.
