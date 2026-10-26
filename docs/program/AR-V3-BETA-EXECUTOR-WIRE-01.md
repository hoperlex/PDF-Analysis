# AR-V3-BETA-EXECUTOR-WIRE-01 — worker route to saved v3 review

The exact sealed AR v3 profile/bundle pair enters its own worker branch only with a server-installed reviewed six-set pack. The branch runs the three deterministic preparation stages, then either dispatches one saved-source and verified-set provider request or consumes the sole completed call of the same Job after recovery. It grounds the saved reply in CITE and closes Run/Job from the four persisted stages. A successful review publishes no canonical findings.

The API and worker composition roots still install `TrustedPackRegistry.empty()`. The new branch is therefore exercised by injected test registries but unavailable to production Run starts until a separately reviewed pack-activation task. Mixed v3/legacy profile identities refuse before Job creation; legacy profiles keep their existing route.

## Verification and handoff

- Task: [AR-V3-BETA-EXECUTOR-WIRE-01](tasks/AR-V3-BETA-EXECUTOR-WIRE-01.md), frozen from `24627767c5f69593c322654c31fda13aac9f21ac`.
- Focused worker, review terminal, guard, composition, provider journal, CITE and request tests: 73 passed.
- An expanded test run also passed 73 cases, then stopped at the PostgreSQL fixture in `test_durable_effect_boundaries.py` because this host has no reachable local PostgreSQL.
- Python compile and `git diff --check`: passed. Full `make gate` is deferred under R-135.
- No shared contract, migration, lockfile, global style, normative map, source/set record or product version changed.

## Integration boundary

The v3 result is review-only. A completed call is consumed without resolving a current provider secret or sending a second request. An uncertain or inconsistent prior effect refuses. The CITE StageResult and its call hashes are rechecked under current Attempt authority before terminalization; an existing finding row or unexpected legacy stage refuses publication. The final Run and Job changes share the caller's transaction.

The provider journal currently does not apply the legacy per-Run cost ceiling to the v3 call. A provider refusal before CITE retains the journal evidence, but the carrier's crash terminal records generic `analysis_failed`. Both must be addressed before activating a reviewed pack. Real PostgreSQL/S3/provider acceptance and the six approved maps/sets are still outstanding. The next integration task should own v3 cost fencing and error presentation; later activation must install identical reviewed pack bytes in both API and worker and verify them on the target stand.
