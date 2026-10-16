# W56A-INT-RECORDED-CALL-FACTS-01 — exact offline call facts

The W56a recorded replay now retains the one `ModelResponse` already returned
by `RecordedAdapter`. `build_recorded_call_facts` binds caller-allocated
model-call identity to that response, the pinned request and the verified
source binding. It returns token counts, latency, stop status, model and
checksums without reopening the recording. A removed recording after replay
does not change the facts; altered digests, mode, usage or reported cost fail.

## Changed files

- `src/auditmanager/analysis/profiles/ar_v2/recorded_response.py`;
- `src/auditmanager/analysis/profiles/ar_v2/recorded_call.py`;
- `tests/integration/analysis/test_ar_v2_recorded_call.py`;
- `docs/program/tasks/W56A-INT-RECORDED-CALL-FACTS-01.md`;
- this report.

## Checks

- Focused call, replay and artifact tests: **25 passed**.
- Python compilation: passed. Direct task governance: `[]`. Six frozen
  SHA-256 values match the task; `git diff --check` passed. Exact changed
  paths are the five task-owned paths.
- No DB, Docker, live provider, network or full gate under R-135.

## Contracts and limits

No HTTP/analysis contract, migration, provider lock, v1 call/stage, public
boundary, findings publisher, run executor, journal, dependency file,
composition root or global style changed. This is a pre-persistence value,
not a `ModelCallRecord`: the future durable stage must choose a truthful
provider and cost policy, persist the allocated call ID and match it to the
artifact in one authorized workflow. It does not change active v1 behavior.

The earlier deep AR v2 import in `findings/v2_publication.py` was already
removed by `W56A-INT-ANALYSIS-PUBLIC-BOUNDARY-01`; this task does not reopen
that boundary. The current checks cover offline replay and pure validation,
not a database transaction or beta acceptance.

## Integration instruction

Take only the five task-owned paths from this commit. Keep the recorded
response and facts on the analysis side until an owned stage/journal task
persists them. Do not use these facts to label a fixture as a live model call
or infer a monetary cost. Rollback is a source revert before runtime wiring.
