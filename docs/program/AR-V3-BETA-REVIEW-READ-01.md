# AR-V3-BETA-REVIEW-READ-01 — verified historical review reader

The new read-only Runs service accepts a terminal exact-v3 Run and returns its saved review only after checking the unique successful CITE stage, its bounded available Blob, canonical JSON bytes, stage metrics, six-member group pins and absence of canonical findings. It rereads the Run, stage, Blob metadata and group after the external Blob read, so changed saved facts refuse. Historical reads do not depend on a currently installed trusted pack.

The reader keeps context-only topics visible as `requires_expert_review` but refuses to place them in provisional citations. It returns a review-only document; it does not reconstruct raw model output or issue a legal/numerical verdict.

## Verification and handoff

- Task: [AR-V3-BETA-REVIEW-READ-01](tasks/AR-V3-BETA-REVIEW-READ-01.md), frozen from `0d0626111ad969dda525677fae45d4387b360ebd`.
- Reader tests: 14 passed, including missing stage, Blob mismatch, noncanonical JSON, group/digest mismatch, context-only citation and changed Run after Blob I/O.
- Python compile and `git diff --check`: passed. Full `make gate` remains deferred under R-135; no reachable local PostgreSQL for live integration.
- No shared contract, migration, dependency/lockfile, composition root, router, React or global style changed.

## Next integration boundary

A new contract owner should add a distinct review-only API response and screen, backed by this reader. `getRunNormVerification` has a frozen canonical-finding partition shape and must retain that meaning. The API should project only user-facing topic status and provisional citation evidence, excluding Blob IDs, model payloads and internal hashes. Six-Run aggregation should retain each scope and failure rather than showing one merged result. Production v3 starts remain closed until six reviewed maps and sets are installed; target-stand PostgreSQL/Blob/provider acceptance remains open.
