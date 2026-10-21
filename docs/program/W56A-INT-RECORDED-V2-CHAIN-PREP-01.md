# W56A-INT-RECORDED-V2-CHAIN-PREP-01 — result

The additive `publish_recorded_v2_response` binds the existing AR v2 response
parser and PDF grounding gate to the deterministic merge plan and savepoint
publisher. It rejects a live context before processing. It returns the full
grounding diagnostics, merge artifact, response digest and publication result.
It does not select a provider, start or finish a run, or commit a transaction.

## Changed files

- `src/auditmanager/analysis/public.py` — exports the response pipeline and
  its typed inputs on the public analysis seam;
- `src/auditmanager/findings/v2_recorded.py` — recorded-only chain;
- `tests/integration/findings/test_v2_recorded_chain.py` — end-to-end recorded
  pipeline probes with a fake savepoint session;
- this report and `tasks/W56A-INT-RECORDED-V2-CHAIN-PREP-01.md`.

## Checks

- Focused chain, publisher, merge and response pipeline: **29 passed**.
- Python compilation and whitespace: passed.
- Direct task governance, frozen hash and exact owned-path checks: recorded at
  integration.
- PostgreSQL acceptance and complete `make gate` deferred under R-135.

## Contracts, limitations and integration

No contract, migration, provider lock, run executor, v1 publisher, root
dependency, composition root or global style changed. The caller must supply
the exact PDF text layer and an authorized recorded run, enforce run-level
idempotency, own the outer transaction and persist rejected diagnostics in a
later task. The fake session proves no write before the grounding/merge gate;
it does not prove database constraints. The run executor is not wired to this
module, so no runtime AR v2 behavior is activated. The integrator should
accept only the five owned paths on the frozen dev base. Rollback is removal
of the additive module and public exports before activation.
