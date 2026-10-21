# Task W56A-INT-PROFILE-CONTENT-01 — prepare reviewed AR v2 prompt sources

## Outcome

Six provenance-bound legacy AR sources are reduced to a deterministic, loadable
text-consistency prompt corpus. Every legacy item is accounted for without
turning an external norm, a sample value or an absent sheet into a finding.
This is an offline preparation for `W56A-PROFILES-01`, not profile activation.

## Depends on

- `W56A-LEGACY-SOURCE-01` — complete at `5f742b22`;
- `W56A-INT-SEAL-01` — complete on `origin/dev`;
- `W56A-INT-GENERATOR-01` — complete on `origin/dev`.

## Frozen inputs

- base `origin/dev=ca8fcf61a1baaad8640a552b987a164e7a51edd9`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd` (read-only);
- migration head `0022_findings_v2`; R-129 and R-135/R-136;
  `W56-PLAN.md` §A3.2/§A3.4; six source digests in
  `W56A-LEGACY-SOURCE-01.md` §1.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: `contracts/analysis/v1/stage-registry.json` (read-only);
- enumerator_owner: `W56A-SEAL-01`;
- totality_query: focused seven-category assertion in
  `tests/integration/analysis/test_ar_v2_profile_content.py`.

## Captured premise evidence

- premise: six frozen legacy sources can be reviewed independently while
  model identity and runtime profile activation remain blocked.

### P-01 — independent content is available while MODEL-PIN is blocked

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && sha256sum contracts/api/v1/openapi.json contracts/domain/v1/error-codes.json contracts/analysis/v1/stage-registry.json docs/program/P02_LOCK.json`
- captured_output:
  ```text
  ca8fcf61a1baaad8640a552b987a164e7a51edd9
  ca8fcf61a1baaad8640a552b987a164e7a51edd9
  fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227  contracts/api/v1/openapi.json
  89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace  contracts/domain/v1/error-codes.json
  bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a  contracts/analysis/v1/stage-registry.json
  2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd  docs/program/P02_LOCK.json
  ```
- interpretation: this is the published, sealed development base. No
  gateway identity or live profile activation follows from it.

## Historical evidence

- correction_mode: none
- source_record: `docs/program/W56A-LEGACY-SOURCE-01.md` (read-only source inventory)
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/__init__.py` (new);
- `src/auditmanager/analysis/profiles/ar_v2/**` (new content only);
- `tests/integration/analysis/test_ar_v2_profile_content.py` (new);
- this task file, `docs/program/W56A-INT-PROFILE-CONTENT-01.md` (new report),
  `docs/program/CURRENT_STATE.md` (top development status only).

## Forbidden hotspots

`contracts/**`, migrations, `P02_LOCK.json`, existing runtime/analysis/run
modules, provider, recordings, root dependencies/locks, composition roots,
global styles, `VERSION`, `origin/main`, tags and stand state.

## Non-goals

No active profile ID, stage plan, response schema, prompt send, provider call,
norm validation, v2 finding publication, full local gate, acceptance or beta
claim. `W56A-PROFILES-01` still owns runtime wiring and response validation.

## Deliverables

Six reviewed resource files with path/digest/line provenance and guarded
prompt blocks; a pure loader exposing their exact text and combined hash;
focused tests; item-by-item exclusion report and dev read-back.

## Required tests

1. Recheck six legacy digests; assert source header and prompt markers for
   all six resources, and the seven frozen category names.
2. Focused tests prove repeatable content hash, tamper refusal and exclusion
   of numeric norm thresholds, example defaults and mandatory-sheet claims.
3. Compile the new module, run focused pytest, direct task governance,
   `git diff --check` and exact allowed-path diff. Do not run `make gate`.

## Integration contract

`W56A-PROFILES-01` may consume `reviewed_sections()` and its content hash,
but must bind the hash into the immutable prompt/profile identity, add the
v2 response schema and stage plan, and preserve v1 byte identity. The loader
never infers a compliance rule from this corpus. It raises on missing or
tampered resources; there is no silent fallback.

## Failure/idempotency/security cases

An altered header, missing marker or source digest mismatch raises before
any prompt is returned. Repeated reads yield the same bytes and hash. No
gateway route, credential, raw client content or paid response enters Git.

## Rollback / feature flag

Revert this additive package and report before runtime wiring; no flag or
data migration is needed. If later wired, correct forward under the profile
owner so a changed prompt gets a new content identity.

## Handoff

- changed files, commands/results and exclusions: report;
- contracts: none;
- known limit: resource corpus alone is not an executable v2 profile;
- next: `W56A-PROFILES-01` after MODEL-PIN/PROVIDER, or further disjoint
  offline code under separately frozen tasks.
