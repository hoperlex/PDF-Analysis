# Task FORK-L3-PRECEDENTS-ON-THE-FLY — precedent vectors at decision and run time

## Outcome
- **At capture:** the resident embedder encodes a case when the expert decides it.
- **At probe time:** the flow's observations are encoded once, in one batch, before the critic stage and outside the locked section (`R-157k`).
  - The vectors are kept as the run's probes, and the precedent pass reuses them.
  - `candidate_context.py` takes the probe vector, so the critic gets examples for every observation, not only for word-for-word repeats.
  - An embedder failure gives `query_vector_unavailable` with its reason, and the critic runs without examples.
- **The night window is removed:** the code, the timer, the exchange volume and the UI texts. The «Векторы» pause stays.

## Owner and paths
The fork's precedents lane: `src/auditmanager/precedents/**`, `src/auditmanager/runs/extended_review.py` (the flow before the critic), `src/auditmanager/decision_memory/**` capture hooks, the web texts of the pause, and the tests.

## Depends on
- `FORK-L2-RESIDENT-EMBEDDER`.
- `FORK-L8-PRECEDENT-SEARCH`: both touch `precedents/vectors/intents.py`.

## Inputs
`ADR-0029` decisions 8 and 14 (the fork bullets and the amendments of 2026-11-19); `R-157k`, `R-157l`.

## Checks
- The precedents and runs tests.
- The web unit tests and `tsc` for the changed texts.
- A run on the server whose critic shows examples for new texts.

## Integration and rollback
The switch `critic_context` stays off by default. If the embedder is down, the stack keeps working without vectors.

## Enumerator ownership
- enumerated_set_changed: no

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none

## Publication authority
- development_target: origin/dev
- origin_main_authority: none; the fork's delegated release integrator publishes main
