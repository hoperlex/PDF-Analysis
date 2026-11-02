# Task REVIEW-FIX-BOUNDS-1102 — restore the intake sandbox; lifted quotas only in relaxed mode

## Outcome
Every PDF, ZIP, bundle and comparison upload is again processed inside finite process and archive
bounds (reader address space and time, ZIP compression ratio and per-member size, free-disk
reservation, proxy body limit and timeouts). The numeric quotas that `af581631` lifted apply again
by default: section-run bounds (sources ≤ 1000, windows ≤ 63, text pages ≤ 500, request ≤ 900 000
bytes) unless the run itself asks for `relaxed_limits`, and the ADR-0025 intake table unless the
deployment sets `AUDITMANAGER_INTAKE_RELAXED=1`. Comparison versions are capped at 500 pages again
(the comparison tables still check 500; REVIEW-FIX-CMP-SPEC-1102 lifts that later).

## Depends on
- SECTION-STATS-UNCAPPED-1030 (completed, `af581631`)

## Frozen inputs
- domain contract: `contracts/domain/v1/**` at the base, error names unchanged
- API contract: `contracts/api/v1/openapi.json` 1.14.0, unchanged (transport stays unbounded; bounds are enforced in domain code)
- analysis/comparison/event contract: unchanged
- migration head: `0044_section_stats_uncapped`
- base commit: `4ab295607806d030cf8066c2f21ab1cac45003e1`
- owner decision, direct poll 2026-11-02: "Защиту вернуть, квоты только в relaxed"; the uncapped money ceiling of statistics mode stays as is
- review: `.local/reports/code-review-2026-11-02.md` D2; findings S8-01, S9-01, S6-01, S1-sprints-01, S4-02 in `.local/reports/code-review-2026-11-02/*.findings.md`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the section-run upper bounds were removed unconditionally

### P-01 — core.py drops the bounds for every run
- captured_at: 2026-11-02
- command: `git show af581631 -- src/auditmanager/analysis/extended/core.py`
- captured_output:
  ```text
  -        return (type(maximum) is int and 1 <= maximum <= 1000 and policy.get("window_size") == 16
  -            and type(policy.get("window_size")) is int and type(windows) is int and 1 <= windows <= 63
  -            and type(text_pages) is int and 1 <= text_pages <= 500
  +        return (type(maximum) is int and 1 <= maximum <= 2**31 - 1 and policy.get("window_size") == 16
  +            and type(policy.get("window_size")) is int and type(windows) is int and windows >= 1
  +            and type(text_pages) is int and 1 <= text_pages <= 2**31 - 1
  ```
- interpretation: the lift is not gated by `relaxed_limits`; the task's own Outcome scoped it to relaxed runs.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/analysis/extended/**`
- `src/auditmanager/analysis/stages/pdf_precheck.py`
- `src/auditmanager/runs/preflight.py`
- `src/auditmanager/runs/cost_policy.py`
- `src/auditmanager/runs/extended_review.py`
- `src/auditmanager/ingest/**`
- `src/auditmanager/comparison/stage/**`
- `src/auditmanager/comparison/version_reader.py`
- `src/auditmanager/comparison/finding_match_suggestions.py`
- `src/auditmanager/comparison/raw_evidence_seal.py`
- `src/auditmanager/api/routers/comparison_uploads.py`
- `src/auditmanager/api/routers/comparison_stage_uploads.py`
- `src/auditmanager/api/routers/multipart.py`
- `src/auditmanager/bootstrap/adapters.py`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/proxy/tls-server.conf`
- `contracts/domain/v1/error-codes.json`
- `tests/unit/ingest/**`
- `tests/unit/comparison/stage/**`
- `tests/unit/analysis/**`
- `tests/unit/runs/**`
- `tests/integration/composition/test_proxy_tls_path.py`

## Forbidden hotspots
- `contracts/api/**`, `contracts/analysis/**`, `api/schemas/models.py`, generated web client
- `infra/deploy/compose.server.yml` and `infra/deploy/env/**` (owned by REVIEW-FIX-SEAMS-1102)
- migrations, `scripts/recovery/**`, `bootstrap/composition.py`, root dependency/lock files, global styles
- `tests/integration/comparison/**` (do not run them: REVIEW-FIX-SEAMS-1102 defuses an unbounded test there)

## Non-goals
- The money ceiling of statistics mode (owner kept it uncapped).
- Web client-side limits (the server stays the authority).
- Lifting the 500-page CHECK in the comparison tables.

## Deliverables
- Finite sandbox values always: reader address space and CPU/wall time, PDF precheck child limits, ZIP compression ratio, per-member decompressed size, total uncompressed size, the `comparison_zip_temporary_space` free-disk check, proxy `client_max_body_size` and timeouts (restore the pre-`af581631` values).
- Section-run quotas back to 1000 / 63 / 500 / 900 000 unless the run's `relaxed_limits` is true.
- ADR-0025 intake table and the bundle/portal limits back by default; `AUDITMANAGER_INTAKE_RELAXED=1` (read through one settings function, default `0`) raises them to the current lifted values. The sandbox values do not move under the flag.
- `MAX_VERSION_PAGES = 500` with the clean up-front refusal; give `finding_match_suggestions` and `raw_evidence_seal` their own explicit size limits instead of reusing the page constant.
- Refusal tests for: ZIP ratio, member size, reader time-out, default section-run bound, and the relaxed path still passing.
- Prose of the affected constraint descriptions in `contracts/domain/v1/error-codes.json` corrected (numbers per ADR, the flag named); no structural contract change.

## Verification
- Optional per owner instruction (2026-11-02). One proof check if run: `.venv/bin/pytest -q tests/unit/ingest tests/unit/comparison/stage tests/unit/runs`.

## Integration contract
- The lane does not run git. The integrator commits exactly the allowed paths it changed.
- REVIEW-FIX-SEAMS-1102 forwards `AUDITMANAGER_INTAKE_RELAXED` (default `0`) to the `api` and `worker` services.

## Rollback / feature flag
- `AUDITMANAGER_INTAKE_RELAXED=1` restores today's lifted intake quotas; per-run `relaxed_limits` keeps the section-run lift.
