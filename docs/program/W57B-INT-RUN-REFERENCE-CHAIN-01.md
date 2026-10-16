# W57B-INT-RUN-REFERENCE-CHAIN-01 — current Run reference chain result

**Status:** completed as an unserved read-only source slice on dev63 `417123c729599cfa075d3461038c8dd15b86d4a3`; local source commit only.

## Changed files

- `src/auditmanager/runs/reference_pipeline.py` — one caller-transaction-owned Run reader that checks explicit Run/Version/set/snapshot pins before and after the composed read, and rechecks current Attempt authority.
- `src/auditmanager/runs/public.py` — public Run facade for the use case and immutable result/pin types.
- `src/auditmanager/norms/public.py` — public catalogue reader, pure pipeline and lazy text-page bridge exports. The bridge is lazy to avoid the existing analysis/norms facade import cycle.
- `tests/integration/runs/test_reference_pipeline.py` — pure pipeline through monkeypatched saved readers, exact pin/refusal, stale Attempt, drift and empty PDF text-page cases.
- `docs/program/tasks/W57B-INT-RUN-REFERENCE-CHAIN-01.md` — exact task freeze.
- `docs/program/W57B-INT-RUN-REFERENCE-CHAIN-01.md` — this result.

## Checks

- Focused composed and predecessor readers/pipeline/bridge suites: **73 passed**.
- ALR-05 cross-context boundaries and analysis public stage-version contracts: **3 passed**; the new public facade imports satisfy the architecture guard.
- Task governance: **16 passed**, with five pytest warnings about removal of unrelated shared `/tmp/pytest-of-root/garbage-*` directories.
- Owned Python compilation and `git diff --check`: passed.
- Frozen API, stage registry, domain identifiers, errors and migration SHA-256 values matched the task; only the six allowed paths changed.
- No full `make gate` under R-135 for this intermediate candidate. No DB/S3 live test, model call or W54 corpus step ran.

## Integration contract and limits

`read_run_references` requires the authorized caller's short consistent transaction, current `AttemptAuthority`, `BlobStore`, an explicit `ReferenceRunPins` tuple, an explicit reviewed unparsed-slug tuple and two positive byte caps. It checks the Run pin before reading; both existing saved readers check their own custody and current Attempt; the use case compares their Version, Run, set and snapshot identities, maps only saved PDF text to pages, runs the existing pure reference pipeline, then repeats Attempt and Run-pin checks. It returns the exact pin tuple, catalogue digest and the report/newer candidates. An empty PDF text page stays unread even if other recognized content might exist.

This source adds no route, deterministic stage, rule observation, finding, provider call, DB/S3 write or publication authority. It does not qualify the W54 corpus or assert that the explicit unparsed-slug tuple was reviewed; the future served caller must establish those prerequisites and recheck authority before any effect. The complete B3.5 export and 0024 seal remain open.

## Integrator note

Review the six-path source commit and repeat the focused checks on the integration candidate. Keep it unserved until the W57b stage/contract seal and publication transaction are assigned. Revert this scoped commit for rollback; no persisted state or runtime flag applies. No forbidden hotspot, remote ref, checkpoint or tag changed.
