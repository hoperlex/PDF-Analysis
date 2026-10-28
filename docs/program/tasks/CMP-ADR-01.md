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
  - `docs/architecture/adr/ADR-0025-comparison-modules.md` (new; 27 numbered decisions, cited as «ADR-0025 decision n»)
  - `docs/architecture/ADR_INDEX.md` (one row)
  - `docs/program/tasks/CMP-ADR-01.md` (this section)
  - forbidden hotspots (contracts, migrations, code, tests, root locks, composition root, global styles): not touched; `git diff --name-only`
    lists the three files above only
- commands/results (worktree `.local/worktrees/cmp-adr-01`, tree `5867d704` plus the three files):
  - `git diff --check` — no output, exit 0
  - `/root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract -k "adr or prose or doc" -p no:cacheprovider` — `32 failed,
    245 passed, 1260 deselected, 7 errors, 15 subtests passed`. The base (the same command on the tree before the ADR was written) gave the
    identical figures and the identical set of 39 failing ids (compared with `diff`). The failures are pre-existing: the venv lacks
    `jsonschema` (three `test_validate_bootstrap` ADR-registry tests), `.venv/bootstrap/bin/python` is missing in the worktree, and
    `test_cp00_candidate.py::ArchitectureCoverageTests::test_adr_files_index_and_review_agree` asserts that the ADR set is exactly
    `ADR-0001`…`ADR-0018`, which `ADR-0019`…`ADR-0024` already broke; that test globs the ADR directory, so it reads the new file, and its
    verdict does not change. The ADR file set and the index rows agree (25 files, 25 rows, labels match targets), checked by a script
  - identity prefixes: `python3 -I -c "..."` of decision 2 prints `[]`
- known limits:
  - every value marked «decided by CMP-ADR-01, revisable by CMP-MEASURE-01» is unmeasured (RLIMIT_AS 768 MiB, CPU 300 s, wall 600 s,
    40 Mpx, 8 GiB per project, batch 8 GiB / 10 000 pages, 2 active batches, 11 GiB readiness finding, 8 images / 16 MiB / 32 MiB);
    throughput is not stated because nothing is measured yet
  - the plan names no prefix for the attempt rows of `comparison_work_attempt` and the rows of `comparison_model_call`, no members of the
    closed «Система» list (the plan gives them to `CMP-SEAL-C4`, the task file to the ADR; the ADR follows the plan) and no carrier of
    the module flag; they are listed under «Left to the named slice»
  - plan text read differently from its words: the pause reader is `execution/public.py:189`, not `jobs.public` (which exports only the
    setter); the spend union is in `dashboard/repository.py` `_SPEND` only (`R3-26`), although the `CMP-SPEND-01` row of plan section 4
    still lists `runs/repository.py`; `D-1` is withdrawn (`Q-CMP-10`), although the `CMP-STAGE-REPAIR-01` row still reads «never over an
    expert link (D-1)»; the plan's «about 180 code sites» is replaced by the measured 91 files / 123 lines; `adapter.py` `image_bytes` is
    line 44, not 43; `comparison_stage_review` appears in the work kinds of both `CMP-SEAL-C2` and `CMP-SEAL-C4`
- integration notes:
  - the integrator records `Q-CMP-1`…`Q-CMP-11` as rulings and replaces the ids in the ADR status line (plan `O-8`)
  - `CMP-SEAL-C0` must add the catalogue entries for the eighteen prefixes with their tables and name the two missing ones
  - fix the two plan rows named above (`CMP-SPEND-01` paths, `CMP-STAGE-REPAIR-01` text) when the C0/C4 task files are written
  - `CMP-MEASURE-01` revises the marked values only by a dated addendum to this ADR (decision 27)
