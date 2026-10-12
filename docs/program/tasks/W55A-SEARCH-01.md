# Task W55A-SEARCH-01 — Text search over the current norms snapshot, the current-snapshot command with its history, and the norm document reads answer for real

## Outcome
Text search over the current norms snapshot, the current-snapshot command with its history, and the norm document reads answer for real.

## Depends on
- `W55A-SEAL-01`, `W55A-CONTENT-01` (merged)

## Frozen inputs
- domain contract: after `W55A-SEAL-01`
- API contract: after `W55A-SEAL-01` (45 / 52 / 116)
- analysis/comparison/event contract: unchanged
- migration head: `0020_norms_search`
- base commit: the CONTENT merge

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
- Exactly the `W55A-SEARCH-01` grant in `docs/program/dispatch/W55-PLAN.md` §A4 Stage B item 2, plus `docs/program/W55A-SEARCH-01.md`.

## Forbidden hotspots
- any path outside the grant; contracts and migrations; `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, refs, tags, the stand

## Non-goals
- other W55a lanes' paths (plan §A5).

## Deliverables
- Per plan §A3.2, §A3.4, §A3.6 and §A4 item 2, on SEAL's stubs and CONTENT's `open_stream`: empty `SEALED_STUB_*` sets; morphology; designation and clause lookup (`СП 54` ≠ `СП 542`); homoglyphs; unreliable paragraphs absent; cursor refused across queries; the window cap 1000; the timeout refusal (`validation_failed`, `norms_search_too_broad`; default 3000 ms from `W55A-FREEZE-01`); the scope rule; both qualification conditions and `listNormSnapshots.qualified` agreeing with the setter; the `expected_current` conflict; one history row per change; events admin-only; role-less refused on all seven; the PDF only through a confirmed binding (CONTENT's recipe in `docs/program/W55A-CONTENT-01.md`).

## Required tests
- command: container-free now; DB/S3-backed cases on PostgreSQL `57230`, S3 `60830/60831` are window steps — list commands.
- expected: exit 0; each new behaviour has a test that fails without the change.

## Integration contract
The integrator merges after reading the diff and the report.

## Failure/idempotency/security cases
- Never `pkill`/`killall`; no containers; never touch the stand, published refs or other worktrees.
