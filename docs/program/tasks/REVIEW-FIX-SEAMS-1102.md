# Task REVIEW-FIX-SEAMS-1102 — web build, unbounded test, rollback flags, recovery head

## Outcome
The dev web build typechecks; no test iterates up to the database integer maximum; every
documented rollback flag of paid behaviour reaches the containers that read it; project erase,
product purge and restore auditing accept a database at migration head `0044_section_stats_uncapped`.

## Depends on
- SECTION-STATS-UNCAPPED-1030 (completed)
- CMP-SEAL-C4 (completed)
- BLOCK11-INT-1030 (completed)

## Frozen inputs
- domain contract: unchanged
- API contract: `contracts/api/v1/openapi.json` 1.14.0, unchanged
- analysis/comparison/event contract: unchanged
- migration head: `0044_section_stats_uncapped`
- base commit: `4ab295607806d030cf8066c2f21ab1cac45003e1`
- owner instruction, 2026-11-02: run P0 and P1 of `.local/reports/code-review-2026-11-02.md`; mandatory checks may be skipped
- findings: S3-01, S2-blocks-4-9-03, S9-02, S3-02, S1-sprints-02, S8-02, S5-02 in `.local/reports/code-review-2026-11-02/*.findings.md`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: three seams are broken at the base

### P-01 — web typecheck error
- captured_at: 2026-11-02
- command: `web/node_modules/.bin/tsc --noEmit --incremental false -p web/tsconfig.json`
- captured_output:
  ```text
  src/widgets/stage-comparison/model/saved-results.ts(199,29): error TS18047: 'right.findings' is possibly 'null'.
  ```
- interpretation: `web/next.config` has `ignoreBuildErrors: false`, so the web image does not build.

### P-02 — recovery head
- captured_at: 2026-11-02
- command: `grep -n -E 'HEAD *=' scripts/recovery/schema_coverage.py`
- captured_output:
  ```text
  41:HEAD = "0041_comparison_stage_core"
  ```
- interpretation: migrations run to `0044_section_stats_uncapped`; erase and purge refuse the tip schema.

### P-03 — unbounded test range
- captured_at: 2026-11-02
- command: `grep -n 'range(1, MAX_VERSION_PAGES + 1)' tests/integration/comparison/test_sheet_match_suggestions.py`
- captured_output:
  ```text
  68:              for number in range(1, MAX_VERSION_PAGES + 1)}
  70:              for number in range(1, MAX_VERSION_PAGES + 1)}
  ```
- interpretation: with `MAX_VERSION_PAGES = 2**31 - 1` the test builds a two-billion-entry dict.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `web/src/widgets/stage-comparison/model/saved-results.ts`
- `tests/integration/comparison/test_sheet_match_suggestions.py`
- `tests/integration/comparison/test_version_reader.py`
- `infra/deploy/compose.server.yml`
- `infra/deploy/env/alpha.env.example`
- `scripts/recovery/schema_coverage.py`
- `scripts/recovery/grant_classification.py`
- `tests/integration/recovery/**`
- `tests/contract/test_compose_flag_forwarding.py`
- `tests/contract/test_recovery_schema_head.py`

## Forbidden hotspots
- contracts, migrations, composition root, root dependency/lock files, global styles
- every path owned by REVIEW-FIX-BOUNDS-1102 (it changes `comparison/version_reader.py` to 500 in parallel)

## Non-goals
- Lifting any limit; changing which flags exist or their code defaults.

## Deliverables
- `saved-results.ts`: bind `left.findings` / `right.findings` to local constants after the null check and use them inside the closures.
- The two comparison tests use a local `LEGACY_PAGES = 500` instead of `MAX_VERSION_PAGES`.
- `compose.server.yml` forwards to `api` (and to `worker` where the worker reads it) every `AUDITMANAGER_*` name read in `src/auditmanager/runs/preflight.py` and `src/auditmanager/comparison/stage_v3/policy.py` (or wherever `AUDITMANAGER_STAGE_V3_PLAN` is read), plus `AUDITMANAGER_INTAKE_RELAXED` (default `0`, read by REVIEW-FIX-BOUNDS-1102). Each line is `NAME: ${NAME:-<the code default>}`; the same names with comments in `alpha.env.example`.
- `tests/contract/test_compose_flag_forwarding.py`: fails when a name read by those modules is missing from the `api` environment.
- `schema_coverage.py` re-pinned to `0044_section_stats_uncapped` with the 0042 tables, triggers, constraints and sequences (and anything 0043/0044 changed); the hand patch in `grant_classification.py` replaced by the derived classes.
- `tests/contract/test_recovery_schema_head.py`: fails when the newest file in `db/migrations/versions/` is not `schema_coverage.HEAD`.

## Verification
- Optional per owner instruction. Proof checks if run: the `tsc` command of P-01; `.venv/bin/pytest -q tests/contract/test_compose_flag_forwarding.py tests/contract/test_recovery_schema_head.py`.

## Integration contract
- The lane does not run git. The integrator commits exactly the allowed paths it changed.

## Rollback / feature flag
- Configuration only; reverting the commit restores the previous compose file.
