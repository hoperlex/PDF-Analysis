# Task FORK-L8-PRECEDENT-SEARCH — keep the precedent scan exact and make it cheap

## Outcome
`R-157i` and `R-157j` are implemented as written in `ADR-0029` decision 8 (the fork amendment of 2026-11-19):
- `decision_memory_embedding.embedding` and `decision_memory_probe.embedding` are `halfvec(1024)`, with a unit-norm CHECK of 5e-4 on those columns;
- the encoder still runs fp32, and the worker rounds values only when it writes them;
- the distance stays cosine `<=>`; never `<#>` on half vectors;
- the run pass's `_SCAN` (`src/auditmanager/precedents/run_pass/reads.py`) reads only cases with `current_decided_at` inside the 24-month window, which is a superset of the cases that vote;
- the counter `EXCLUDED_OUTSIDE_WINDOW` stays truthful;
- `candidate_context.py` keeps reading all active cases, with no window;
- an index serves selecting a section's cases (section, data class, status, latest decision);
- `EXPLAIN (ANALYZE, BUFFERS)` shows each section's vectors read once per pass; TOAST is checked, using `SET STORAGE PLAIN` if needed.

## Owner and paths
The fork's precedents lane:
- `db/migrations/**` (this lane owns the migration head during its wave);
- `src/auditmanager/precedents/run_pass/reads.py`, `precedents/candidate_context.py`, `precedents/vectors/intents.py` (literals and casts);
- their tests.

## Depends on
- `FORK-L0-MEASURE`.

## Inputs
- Measured on the 61,573 fp32 vectors of the norms bundle: the cosine error after half rounding is ≤ 6.3e-5, and 0 of 1,298 pairs near the thresholds cross them.
- The inner product on half vectors erred by up to 1.16e-4 and crossed 0.85 twice.
- Thresholds 0.85 / 0.75 / 0.92 are unchanged.
- Volume: at most about 240,000 cases in the window, about 0.5 GB of half vectors (`R-157j`).

## Checks
- Migration upgrade and downgrade on a throwaway database.
- The precedents tests: votes, card, P5, critic input.
- A synthetic run: 240,000 unit vectors in one section and 150 findings; the pass takes ≤ 30 s.

## Integration and rollback
The downgrade migration returns the columns to `vector(1024)`. Approximate search (HNSW or a prefilter) stays rejected unless the owner decides otherwise, with a recall check on the replay.

## Enumerator ownership
- enumerated_set_changed: no

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none

## Publication authority
- development_target: origin/dev
- origin_main_authority: none; the fork's delegated release integrator publishes main
