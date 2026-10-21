# Task W59-INT-SECTION-REVIEW-PREP-01 — prepare explicit section choices

task_id: W59-INT-SECTION-REVIEW-PREP-01

## Outcome

A pure, version-bound review packet lists every one of the 15 project sections,
including options with no filename or text match. It attaches the existing
ranked suggestion evidence to matching options and never preselects or
confirms a section. A reviewer can therefore choose PS or PB even when no
heuristic suggests them; no analysis route is activated.

## Depends on

- `W59-INT-SECTION-SUGGESTION-PREP-01` — completed 15-section catalogue.
- `W59-INT-CONFIRMATION-PREP-01` — completed explicit expert-choice policy.

## Frozen inputs

- base commit and `origin/dev`: `d416e185d3b42da55ba2e8bfdd02d7126da7f41e`;
- API SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- domain identifiers SHA-256: `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`;
- error catalogue SHA-256: `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256: `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- suggestion resource SHA-256: `ad6f9856212a7d4c8670a4f440a97f435ccad1b73de1a729a6fa8617b1a1d263`;
- migration head: `0022_findings_v2`; roadmap S-1–S-6 and R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the complete suggestion catalogue and confirmation policy exist,
  but there is no full choice projection that retains unmatched sections.

### P-01 — exact base and absent target

- captured_at: 2026-10-16
- command: `git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/sections tests/integration/sections`
- captured_output:
  ```text
  d416e185d3b42da55ba2e8bfdd02d7126da7f41e
  d416e185d3b42da55ba2e8bfdd02d7126da7f41e
  src/auditmanager/sections/__init__.py
  src/auditmanager/sections/confirmation.py
  src/auditmanager/sections/routing.py
  src/auditmanager/sections/suggestion.py
  src/auditmanager/sections/suggestion_patterns.json
  tests/integration/sections/test_confirmation.py
  tests/integration/sections/test_routing.py
  tests/integration/sections/test_suggestion.py
  ```
- interpretation: the two new review files are additive; the existing
  catalogue is a candidate UI input, not an API/DB seal or permission grant.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/sections/review.py`
- `tests/integration/sections/test_review.py`
- `docs/program/tasks/W59-INT-SECTION-REVIEW-PREP-01.md`
- `docs/program/W59-INT-SECTION-REVIEW-PREP-01.md`

## Forbidden hotspots

`contracts/**`, migrations, existing section files, API/router/UI/run code,
storage, profiles, provider lock, root dependencies/locks, composition root,
global styles, `CURRENT_STATE.md`, refs, tags and `origin/main`.

## Non-goals

No persisted stage or confirmation, actor authorization, selected/default
section, profile readiness or route, API/DB contract seal, provider call,
runtime wiring, complete gate or beta acceptance.

## Deliverables

One additive pure review projection, focused refusal/coverage tests, this
task and a result report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/sections/test_review.py tests/integration/sections/test_suggestion.py tests/integration/sections/test_confirmation.py` — pass;
- Python module compilation, direct task governance, frozen SHA readback,
  `git diff --check` and exact changed-path proof — pass;
- no Docker, DB/S3, network or full `make gate` during W55b's host lane.

## Integration contract

The future W59 UI adapter may show all fifteen options and their evidence for
one `VersionUid`. It must obtain the expert's explicit choice separately,
authenticate the actor, and persist it through the sealed version-bound
confirmation command. No score, option order or review packet can be passed
to `route_confirmed_section` as a confirmed decision. SECTION-SEAL remains a
separate owner task after W58-code close.

## Failure/idempotency/security cases

Invalid version identity and nonstring evidence refuse. A neutral or
ambiguous input still produces all fifteen unselected options. The exact
candidate catalogue must contain fifteen distinct section codes; a corrupted
candidate refuses. Repeated inputs return the same packet without I/O or
side effect. Filename and text never become identity or authority.

## Rollback / feature flag

Delete the additive module before runtime wiring. No database rollback or
feature flag is needed because this packet is not served.

## Handoff

- changed files/checks/limits: result report;
- contracts: none;
- next: W59 SECTION-SEAL owner wires an authenticated, persisted review and
  confirmation flow after its prerequisites; this module alone cannot route.
