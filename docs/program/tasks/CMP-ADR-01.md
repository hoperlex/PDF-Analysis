# Task CMP-ADR-01 — ADR-0025: the architecture of the comparison modules

## Outcome
`docs/architecture/adr/ADR-0025-comparison-modules.md` records, as accepted decisions with their owner answers and
rulings, the architecture of `COMPARE-MODULES-PLAN.md` §3 as amended by §3.2, and `docs/architecture/ADR_INDEX.md`
lists it.

## Depends on
- `COMPARE-MODULES-PLAN` revision 3 merged on `integration/compare-modules` (`cccdb6b8`)

## Frozen inputs
- domain contract: `contracts/domain/v1/identifiers.json` as at the base (read only)
- API contract: `contracts/api/v1/openapi.json` `1.8.0` as at the base (read only)
- analysis/comparison/event contract: not changed
- migration head: as at the base (read only)
- base commit: `cccdb6b8` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `docs/architecture/ADR_INDEX.md`
- enumerator_owner: CMP-ADR-01
- totality_query: `ls docs/architecture/adr/ | sort`

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
- `docs/architecture/adr/ADR-0025-comparison-modules.md`
- `docs/architecture/ADR_INDEX.md`
- `docs/program/tasks/CMP-ADR-01.md`

## Forbidden hotspots
- contracts, migrations, code, tests, root locks, composition root, global styles

## Non-goals
- no new decision beyond the plan and the owner's answers; where the plan leaves a choice to the ADR (identity
  prefixes, per-item memory ceiling default, byte caps, the handler registry shape, the closed «Система» list), the
  ADR states the choice and marks it «decided by CMP-ADR-01, revisable by the measurement of CMP-MEASURE-01»

## Deliverables
- the ADR in the form of `ADR-0024` (status, date, owners, supersedes, related principles, context with facts read
  from the tree, decisions numbered, consequences, rejected alternatives with reasons — including the shared `job`
  subject rejected for the comparison-local queue, the stage V3 pipeline rejected by `Q-CMP-1`, eviction rejected for
  refusal caps), with every owner answer `Q-CMP-1`…`Q-CMP-11` cited
- one line in `ADR_INDEX.md`

## Required tests
- command: `git diff --check && /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract -k "adr or prose or doc" -p no:cacheprovider`
- expected: no `git diff --check` output; the selected tests pass as on the base (state any pre-existing failure with its output on the base)

## Integration contract
Every CMP seal and lane cites ADR-0025 decision numbers instead of re-deciding.

## Failure/idempotency/security cases
- the ADR keeps the safety rules of the plan §3.2 verbatim in substance: the pre-call spend breadcrumb, CHANGED→SAME
  becomes UNCERTAIN, child-process compute under a kernel ceiling, server-side image gating by declared `max_images`,
  erase refusal during leased comparison work

## Rollback / feature flag
Not applicable (a document).

## Handoff
- changed files:
- commands/results:
- known limits:
- integration notes:
