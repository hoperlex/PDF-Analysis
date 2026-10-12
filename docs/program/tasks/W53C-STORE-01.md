# Task W53C-STORE-01 — Reconciliation can no longer ban a document version's analysis by rejecting an artifact

## Outcome
Reconciliation can no longer ban a document version's analysis by rejecting an artifact, release history survives an image rollback, and rehearsal scripts refuse a non-disposable target (C-12…C-14).

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

The lane commits only on `agent/w53c-store`; the integrator merges and publishes.

## Allowed paths
- `src/auditmanager/ingest/reconciliation.py`
- `src/auditmanager/storage/**` (only if C-12 needs a storage-side refusal)
- `src/auditmanager/releases/**`
- `scripts/rehearsal/w53/**`
- `tests/integration/ingest/**`, `tests/integration/releases/**`
- `tests/integration/runs/test_durable_effect_boundaries.py` (the test that pins C-12 as correct)
- new static tests under `tests/contract/rehearsal/`
- `docs/program/W53C-STORE-01.md` (hand-back report)

## Forbidden hotspots
- `contracts/**` (no API, domain, event or error-catalog change in this wave)
- `db/migrations/**` (head stays `0017_execution_queue`)
- root dependency and lock files (`pyproject.toml`, `uv.lock`, `requirements/**`, `web/package.json`, `web/package-lock.json`)
- `Makefile`, `tests/support/**`, every `conftest.py`, global styles (`web/src/app/globals.css`)
- `VERSION`, `release-notes/**`, `docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`
- any path owned by another `W53C-*` lane (see `docs/program/dispatch/W53-CLOSE-PLAN.md` §4)

## Non-goals
- a settlement state for artifact intents or any blob-topology change (needs a migration; W54 custody)
- release loader semantics other than read tolerance

## Deliverables
- C-12: an analysis-artifact publication intent whose blob is content-addressed is never reported `rejection_eligible`, and `reject_unpublished` refuses such a blob with a typed refusal explaining that a rerun self-heals it. Rewrite `test_only_stale_terminal_analysis_publication_without_bytes_can_be_rejected` so it asserts the refusal, and add a test that a new run of the same version is not blocked.
- C-13: release reads tolerate revisions written by a newer image: when a revision's items contain a kind or field this image does not know, serve the newest revision this image can parse (or drop only the unknown items with the revision still shown) — never 500. A test writes an unknown-kind revision directly and asserts `listReleases`' data path still answers.
- C-14: `process_recovery.py` refuses to run unless the target database name/instance is a disposable rehearsal target (explicit check, clear message); `minio_upgrade.py`'s safety checks become explicit `if …: raise SystemExit(...)` instead of `assert`. A static test proves both refusals exist.

## Required tests
- command: `git diff --check`; `.venv/bin/ruff check` on changed Python; `.venv/bin/python -m compileall -q` on changed modules; for web, `npm --prefix web run lint`, `npm --prefix web run typecheck` and `npx --prefix web vitest run <touched test files>`; for backend, the touched test modules (DB-backed ones on the private ports below, one run at a time)
- expected: all exit 0; every new behaviour has a test that fails without the change (state how you showed it)
- private ports: PostgreSQL `57040`, S3 `60640/60641`, instance `gate-w53c-store`

## Integration contract
The integrator merges `agent/w53c-store` as is after reading the diff and the report. Everything outside the allowed paths is unchanged; no contract, migration, dependency or published ref moves.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; kill only PIDs you started. Never touch the working stand, another lane's ports or containers, the main checkout or any published ref.
- Remove your private containers and volumes before handing back; prove containment with `git status --porcelain -uall` and `git diff --name-only <base>..HEAD`.
