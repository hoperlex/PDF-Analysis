# Task W59-INT-SECTION-ROUTE-PREP-01 — refuse analysis without a version-bound confirmed section

task_id: W59-INT-SECTION-ROUTE-PREP-01

## Outcome

A pure W59 routing guard returns the profile for a confirmed section of the
same document version. It refuses missing, foreign-version, unknown and
profile-unavailable sections. A filename suggestion cannot cause an AR
fallback or become a confirmation.

## Depends on

- `W59-INT-SECTION-SUGGESTION-PREP-01` — complete at `6336f29e`.

## Frozen inputs

- base commit: `83c6bcc585fbb6383427e42d3f7212e13b930576` (`origin/dev`);
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`; roadmap §10.3 S-1–S-6 and R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the completed suggestion registry cannot confirm or route a
  section, and the pure version-bound routing guard is absent.

### P-01 — exact base and absent target

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/sections/routing.py tests/integration/sections/test_routing.py`
- captured_output:
  ```text
  83c6bcc585fbb6383427e42d3f7212e13b930576
  83c6bcc585fbb6383427e42d3f7212e13b930576
  ```
- interpretation: this grant adds only pure route validation, after the
  completed suggestion code; no current API or DB field is inferred.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/sections/routing.py`
- `tests/integration/sections/test_routing.py`
- `docs/program/tasks/W59-INT-SECTION-ROUTE-PREP-01.md`
- `docs/program/W59-INT-SECTION-ROUTE-PREP-01.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

`contracts/**`, migrations, existing suggestion registry/resource, active
profiles, API/router/UI/run code, provider lock, root dependencies/locks,
composition root, global styles, production configuration, `VERSION`,
recordings, tags and `origin/main`.

## Non-goals

No persisted confirmation, permission check for the confirming actor, W59
contract reseal, stage П/Р, active profile registry, upload/UI wiring,
provider call, full local gate or beta acceptance.

## Deliverables

Pure route guard, focused tests, report and dev ref read-back.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/sections/test_routing.py tests/integration/sections/test_suggestion.py` — pass;
- module compilation, direct task governance, `git diff --check` and exact
  changed-path proof — pass;
- no `make gate` under R-135.

## Integration contract

The W59 framework must persist the expert-confirmed section against a
`VersionUid`, authenticate the expert and supply that confirmed row to this
guard. Suggestions are display evidence only. The caller supplies a sealed
mapping of currently executable section profiles; missing profiles refuse
the run. The W59 contract/migration owner separately adds `PS`, stage П/Р
and the confirmation state before any runtime wiring.

## Failure/idempotency/security cases

A missing confirmation, mismatch with the run's version, code outside the
15-section catalogue or missing/invalid `ap_` profile identity refuses
without silently selecting AR. This pure function has no I/O or side effect;
identical input gives identical output.

## Rollback / feature flag

Revert the additive module before runtime wiring. No data rollback or flag.

## Handoff

- changed files/checks/limits: report;
- contracts: none;
- next: W59 framework reseal and expert-confirmation workflow after earlier code blocks.
