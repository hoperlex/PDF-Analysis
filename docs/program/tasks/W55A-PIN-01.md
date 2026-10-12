# Task W55A-PIN-01 — New runs and re-audits pin the current norms snapshot inside the run-creating transaction

## Outcome
New runs and re-audits pin the current norms snapshot (NULL when none) inside the run-creating transaction, `RunStatus.norms_snapshot_id` is served, and retries replay unchanged.

## Depends on
- `W55A-SEAL-01`, `W55A-CONTENT-01`, `W55A-SEARCH-01` (merged)

## Frozen inputs
- domain contract: after `W55A-SEAL-01`
- API contract: after `W55A-SEAL-01` (45 / 52 / 116)
- analysis/comparison/event contract: unchanged
- migration head: `0020_norms_search`
- base commit: the SEARCH merge

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- Exactly the `W55A-PIN-01` grant in `docs/program/dispatch/W55-PLAN.md` §A4 Stage B item 3, plus `tests/integration/api/test_query_surface.py` (drive the four norms query operations SEARCH left in `SEALED_STUB_QUERY_OPERATIONS`), plus `docs/program/W55A-PIN-01.md`.

## Forbidden hotspots
- any path outside the grant; contracts and migrations; `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand

## Non-goals
- any stage reading norms (W57).

## Deliverables
- Per plan §A3.3 and §A4 item 3 (R-82, R-113, CD-6): `startRun` and `reauditRun` read `norms.public.current_snapshot(session)` inside the run-creating transaction and write `audit_run.norms_snapshot_id` (NULL when none); `input_basis_digest` unchanged, stored `frozen_input_digest` = basis plus snapshot when not NULL; `start_run_fingerprint` takes the basis only so a retry after a designation change replays; a pre-W55 key replays; a re-audit pins the current snapshot and its retry replays; `RunStatusView.norms_snapshot_id` filled in the adapters.

## Required tests
- command: container-free now; DB-backed `tests/integration/runs/**` and the query-surface test on PostgreSQL `57240`, S3 `60840/60841` are window steps — list commands.
- expected: exit 0; each new behaviour has a test that fails without the change.

## Integration contract
The integrator merges after reading the diff and the report.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; no containers; never touch the stand, published refs or other worktrees.
