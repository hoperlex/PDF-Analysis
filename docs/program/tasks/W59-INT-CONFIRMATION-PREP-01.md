# Task W59-INT-CONFIRMATION-PREP-01 — prepare version-bound expert section confirmation

task_id: W59-INT-CONFIRMATION-PREP-01

## Outcome

A pure domain command validates an expert's explicit choice of one of the 15
sections for a particular version with an explicit project stage П/Р. A repeat
of the same choice preserves the original confirmer; a conflicting choice or
unclassified stage refuses. Suggestions and legacy `document.section` cannot
be passed as confirmations. Focused tests prove these decisions.

## Depends on

- `W59-INT-SECTION-SUGGESTION-PREP-01` — completed 15-code candidate.
- `W59-INT-SECTION-ROUTE-PREP-01` — completed version-bound route guard.

## Frozen inputs

- base commit and local `origin/dev`: `5a51721a745a7bfc5c85cc4594625fa53cbce523`;
- API SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- domain identifiers SHA-256: `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`;
- error catalog SHA-256: `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256: `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- code-first scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- roadmap SHA-256: `e7e73b21996c1c6f37f7b3f5cb741b7d50054dcd7751b3a401ed7fba514a7be5`;
- migration head: `0022_findings_v2`; R-135 and roadmap §10.3 S-1–S-6.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the 15-code suggestion catalogue and fail-closed route guard exist,
  but there is no expert confirmation policy or stage value type; W59 runtime
  reseal depends on a W58-code close that is not recorded yet.

### P-01 — exact base and existing section package

- captured_at: 2026-10-15
- command: `git rev-parse HEAD origin/dev && git ls-tree -r --name-only HEAD src/auditmanager/sections tests/integration/sections`
- captured_output:
  ```text
  5a51721a745a7bfc5c85cc4594625fa53cbce523
  5a51721a745a7bfc5c85cc4594625fa53cbce523
  src/auditmanager/sections/__init__.py
  src/auditmanager/sections/routing.py
  src/auditmanager/sections/suggestion.py
  src/auditmanager/sections/suggestion_patterns.json
  tests/integration/sections/test_routing.py
  tests/integration/sections/test_suggestion.py
  ```
- interpretation: this task adds an isolated policy. It does not imply that
  the future API, migration or W58 prerequisite has been sealed.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/sections/confirmation.py`
- `tests/integration/sections/test_confirmation.py`
- `docs/program/tasks/W59-INT-CONFIRMATION-PREP-01.md`
- `docs/program/W59-INT-CONFIRMATION-PREP-01.md`

## Forbidden hotspots

`contracts/**`, migrations, existing section files, API/router/UI/run code,
storage, norms, comparison, provider lock, root dependencies/locks,
composition root, global styles, `CURRENT_STATE.md`, tags and `origin/main`.

## Non-goals

No persisted confirmation, stage column, permission source, contract reseal,
runtime route, active section profile, provider call, complete gate or beta
acceptance. `P`/`R` are provisional internal values for the future reseal.

## Deliverables

Pure confirmation policy, focused tests, task and result report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/sections/test_confirmation.py tests/integration/sections/test_routing.py tests/integration/sections/test_suggestion.py` — pass;
- Python module compilation, direct task governance, `git diff --check` and
  exact changed-path proof — pass;
- no `make gate` during the code-first series under R-135.

## Integration contract

The future W59 service must authenticate the actor and load the immutable
version's persisted stage and current confirmation in one transaction. It may
call this policy and insert only an `insert` plan with a uniqueness constraint
on `version_uid`. A repeat returns the original confirmation. A conflicting
choice requires a separately specified, auditable correction workflow. The
run loads the persisted row and uses `route_confirmed_section`; this policy's
returned value is never itself a routing authority.

## Failure/idempotency/security cases

Malformed identities, non-expert actors, unknown section/stage, foreign-version
confirmation and conflicts refuse. An exact repeat is a no-op preserving the
original expert; concurrent insertion must be guarded by the future unique
database key. No file name, title or display ordinal participates in identity.

## Rollback / feature flag

Delete the additive module before runtime wiring. There is no data rollback
or feature flag because this policy is not connected to the active app.

## Handoff

- changed files/checks/limits: result report;
- contracts: none;
- next: W58-code close, then a single W59 contract/migration owner reseals
  15 sections, stage and persisted confirmation before API/run wiring.
