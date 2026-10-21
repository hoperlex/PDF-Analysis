# W56A-INT-RECORDED-SOURCE-READ-01 — durable source read

## Result

`load_recorded_v2_input` now reads an existing recorded AR v2 run, its immutable
version and the persisted `source_preparation` stage result. It resolves the
registered profile independently of the run row, requires a running recorded
run and a successful source stage, and rejects duplicate or unexpected
artifact roles. It reads the exact text-layer and, for a portal version, the
marked OCR Blob through `read_artifact`. The existing binder checks their read
digests, declared references and version identity before constructing the
offline request. The loader also checks the text layer's page count against
the saved version. The output retains separate request and source-binding
SHA-256 values.

The operation performs only repository SELECTs and verified Blob reads. It
does not call the adapter, journal a model call, mutate a run, publish an
artifact or write a finding. The active `execute_run` path is unchanged and
continues to use the v1 profile and terminal selection.

## Changed files

- `src/auditmanager/runs/recorded_v2_sources.py` — read-only integration seam;
- `src/auditmanager/analysis/public.py` — only three exports of the existing
  AR v2 input binder and settings under this task's sole integration slot;
- `tests/integration/runs/test_recorded_v2_sources.py` — fake repository and
  Blob refusal tests;
- this report and `tasks/W56A-INT-RECORDED-SOURCE-READ-01.md`.

## Checks

- Focused source, existing preflight and input binder suites: **35 passed**.
- Python compilation of new reader and tests: passed.
- Frozen W56 plan, code-first order, API, error catalog, stage registry and
  provider-lock SHA-256 values: matched the task.
- Whitespace and exact changed-path checks: passed before handoff.
- PostgreSQL/S3 acceptance and complete `make gate`: deferred under R-135;
  this task did not start isolated services under the host's resource limit.

## Contracts and limits

No contract, migration, provider lock, root dependency/lock file, composition
root, global style, recording, corpus, `CURRENT_STATE.md` or Git ref changed.
The public-boundary slot adds imports and `__all__` names only. The read is
safe to repeat, but it is not an execution authority or run-level
idempotency mechanism. Its fake tests do not establish PostgreSQL or S3
behavior. No recorded v2 observation/merge artifact payload and stage-result
producer has been sealed, and the current executor still uses v1's fixed
stage tuple. The gateway model identity/price and measured recorded baseline
also remain unverified. These gaps prevent calling this a recorded v2
activation or beta acceptance.

## Integration instruction

Stage only the five owned paths from the exact task base. Keep the new reader
unconnected until a separately owned executor slice defines durable model-call
provenance, v2 artifact/stage results, finding publication, terminal selection
and run-level idempotency, then proves them against PostgreSQL/S3. The caller
must hold Job/Attempt authority before any replay or write and source the
version/stage references from the saved run, as this reader does.
