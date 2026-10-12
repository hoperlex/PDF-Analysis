# Task W55A-SEAL-01 — The W55a contract seal: seven norms operations as refusing stubs, migration 0020_norms_search, streaming wire response, RunStatus.norms_snapshot_id

## Outcome
The W55a contract seal: seven norms operations as refusing stubs, migration `0020_norms_search`, `StreamingWireResponse`, `RunStatus.norms_snapshot_id`, the ports and the reseal with every pin swept.

## Depends on
- `W55A-RULE-01`, `W55A-FREEZE-01`

## Frozen inputs
- domain contract: `contracts/domain/v1` at the freeze commit
- API contract: `contracts/api/v1/openapi.json` at the freeze commit (38 paths / 45 operations / 96 schemas after W54)
- analysis/comparison/event contract: unchanged
- migration head: `0019_execution_workers`
- base commit: the `W55A-FREEZE-01` commit

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: contracts/api/v1/openapi.json
- enumerator_owner: W55A-SEAL-01
- totality_query: `.venv/bin/python tools/plan/pin_sweep.py --help` (run reseal-surface, migration, table, route and error-code sweeps; grant every printed path)

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
- Exactly the `W55A-SEAL-01` grant in `docs/program/dispatch/W55-PLAN.md` §A4 Stage A, plus every path `tools/plan/pin_sweep.py` prints, plus `docs/program/W55A-SEAL-01.md`.

## Forbidden hotspots
- any path outside the grant; `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand

## Non-goals
- Operation bodies (CONTENT, SEARCH, PIN), screens (WEB-NORMS).

## Deliverables
- Per plan §A3.2–§A3.6 and §A4 `W55A-SEAL-01`: the seven operations with refusing stubs and roles (`R-80` any-role reads; admin for events and set-current), `RunStatus.norms_snapshot_id`, `0020` (`norm_current_snapshot`, `norm_current_snapshot_event` with immutability triggers, `norm_paragraph.text_tsv` generated with a partial GIN index on reliable rows, `norm_designation_tokens(text)` IMMUTABLE with explicit translate tables, `norm_document.designation_tokens`), the error-register values (no new code; CD-19), `NormsSearchPort`, `NormContentPort`, chunked `DocumentPort.stream_content`, `StreamingWireResponse`, guards' literals, the four-document reseal, the facts file.

## Required tests
- command: container-free now (`tests/contract` without the three environmental cp00/bootstrap modules; web lint, typecheck, Vitest). DB-backed (fresh upgrade; upgrade from `0019` with norms rows, generated columns filled, declared-column digest unchanged; refused downgrade with retained data) are window steps on PostgreSQL `57210`, S3 `60810/60811` — write them and list the commands.
- expected: exit 0; each new behaviour has a test that fails without the change.

## Integration contract
The integrator merges after reading the diff and the report.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; no containers; never touch the stand, published refs or other worktrees.
