# Task W53C-EXEC-01 — The execution queue never destroys a run it did not claim

## Outcome
The execution queue never destroys a run it did not claim, a re-audit records the configuration it actually runs (`R-82`), provider responses of any shape are classified, and W48/W53 execution prose is true again (C-01…C-06).

## Depends on
- `W53-CLOSE-PLAN` (this wave's plan commit on `integration/w53-close`)

## Frozen inputs
- domain contract: `contracts/domain/v1` at base, unchanged
- API contract: `contracts/api/v1/openapi.json` at base (SHA-256 `008a7932ac0b6aa6d44076dc6b394b25af38865edea6cb66083a0811bc96f193`), unchanged
- analysis/comparison/event contract: unchanged
- migration head: `0017_execution_queue`
- base commit: the `W53-CLOSE-PLAN` commit on `integration/w53-close`, itself on `origin/dev` `872266038a83568b56f6302f01b97771b9aaf281`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: none

The findings come from the 2026-10-12 static review of `872266038a83568b56f6302f01b97771b9aaf281`; `docs/program/dispatch/W53-CLOSE-PLAN.md` §2 lists them. Re-read each cited location before changing it and report any finding that no longer reproduces instead of changing code for it.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

The lane commits only on `agent/w53c-exec`; the integrator merges and publishes.

## Allowed paths
- `src/auditmanager/runs/**`
- `src/auditmanager/jobs/**`
- `src/auditmanager/execution/**`
- `src/auditmanager/analysis/text/proxy.py`, `src/auditmanager/analysis/text/stage.py`, `src/auditmanager/analysis/text/adapter.py`
- `src/auditmanager/bootstrap/adapters.py` — only `ExecutionAdapter`, `RunAdapter` and `_run_status_view`
- `src/auditmanager/bootstrap/composition.py` — only the execution/re-audit wiring lines, if `R-82` needs the current configuration passed in
- `tests/integration/runs/**` except `test_durable_effect_boundaries.py`
- `tests/integration/analysis_text/**`
- new files under `tests/integration/qa_w53/` (existing files there are independent QA and stay unchanged)
- `docs/program/W53C-EXEC-01.md` (hand-back report)

## Forbidden hotspots
- `contracts/**` (no API, domain, event or error-catalog change in this wave)
- `db/migrations/**` (head stays `0017_execution_queue`)
- root dependency and lock files (`pyproject.toml`, `uv.lock`, `requirements/**`, `web/package.json`, `web/package-lock.json`)
- `Makefile`, `tests/support/**`, every `conftest.py`, global styles (`web/src/app/globals.css`)
- `VERSION`, `release-notes/**`, `docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`
- any path owned by another `W53C-*` lane (see `docs/program/dispatch/W53-CLOSE-PLAN.md` §4)

## Non-goals
- the heartbeat-vs-final-transaction design (deferred to W54); cursor snapshot semantics; global pause in the public journal (Y-04)
- any API field, migration or error code; the queue UI

## Deliverables
- C-01: in `runs/carrier.py` a refusal raised **before** this process holds authority (the pause `CONFLICT` from `start_execution`, and any equivalent not-claimed refusal) leaves the run and Job queued and is logged, never `_record_crash`. Add a carrier-level test that pauses between hint and claim and asserts the run is still `queued` with no Attempt.
- C-02 (`R-82`): `reaudit_run` stamps the **current** deployment's analysis profile, prompt bundle, frozen-input digest and provider mode on the new run (the way `start_run` does), never the source's; the source is linked only by `reaudit_of_run_id`. A test asserts the new run's recorded profile/bundle/mode equal the current configuration when the source differs.
- C-03: `RunRow`/`RunRepository` expose `reaudit_of_run_id`; `_run_status_view` reads it from the row; remove the raw `text(...)` query.
- C-04: in `analysis/text/proxy.py` every failure after an HTTP response was received (non-object JSON, non-object `choices[0]`, empty `choices`, non-integer usage) becomes a typed refusal that the call journal records as response-received/`outcome_unknown` with usage when present; no bare `AttributeError`/`TypeError` escapes. Unit tests for each shape.
- C-05: in recorded (replay) mode no provider effect is journalled as a possibly-paid `outcome_unknown`; a recorded failure is classified so that resume after a crash is allowed. Test it.
- C-06: correct `runs/scope.py` `ABSENT_CAPABILITIES` (cancel exists), the `runs/__init__.py` and `runs/executor.py` docstrings about heartbeat/failover/resume; remove dead `LEASE_SECONDS` or make the SQL use it; fix `finish_execution`'s return annotation.

## Required tests
- command: `git diff --check`; `.venv/bin/ruff check` on changed Python; `.venv/bin/python -m compileall -q` on changed modules; for web, `npm --prefix web run lint`, `npm --prefix web run typecheck` and `npx --prefix web vitest run <touched test files>`; for backend, the touched test modules (DB-backed ones on the private ports below, one run at a time)
- expected: all exit 0; every new behaviour has a test that fails without the change (state how you showed it)
- private ports: PostgreSQL `57020`, S3 `60620/60621`, instance `gate-w53c-exec`

## Integration contract
The integrator merges `agent/w53c-exec` as is after reading the diff and the report. Everything outside the allowed paths is unchanged; no contract, migration, dependency or published ref moves.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; kill only PIDs you started. Never touch the working stand, another lane's ports or containers, the main checkout or any published ref.
- Remove your private containers and volumes before handing back; prove containment with `git status --porcelain -uall` and `git diff --name-only <base>..HEAD`.
