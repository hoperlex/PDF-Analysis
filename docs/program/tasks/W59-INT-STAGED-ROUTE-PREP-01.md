# Task W59-INT-STAGED-ROUTE-PREP-01 — bind a supplied section route to P/R stage

task_id: W59-INT-STAGED-ROUTE-PREP-01

## Outcome

An unserved pure guard produces one immutable version/stage/section/profile
route pin only when a supplied explicit P/R stage agrees with a supplied
expert section confirmation for that same `VersionUid`. A stage mismatch,
missing fact or unavailable profile refuses. Tiny tests check the refusal;
no caller may treat the pin as proof that either fact was persisted.

## Depends on

- `W59-INT-SECTION-ROUTE-PREP-01` — completed version-bound profile guard.
- `W59-INT-CONFIRMATION-PREP-01` — completed explicit expert P/R choice shape.
- `W59-SECTION-IDENTITY-DECISION-01` — completed version-stage identity ruling.

## Frozen inputs

- base commit: `69b923156ea3988dbad3cc378644b9799a6bdd23` (`origin/dev`);
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- domain identifiers SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- code-first scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- section identity decision SHA-256: `6b0e8abf399833b1339dbc99586941ee7bf758b22b6778b30c50ec0a2b2a1788`;
- current route SHA-256: `b8d3f9e92820769c69a014d40d9e6865edc05d5b4d568bae369605fe21950ba2`;
- confirmation policy SHA-256: `f51589a0304d2afb55bbc572ec6cd093aa915a63adaa798586d10ef1785902f1`;
- migration head: `0023_norm_citations`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: current pure routing accepts only `ConfirmedSection(version_uid,
  code)` and cannot check an explicit version P/R stage against the stage in
  `ExpertSectionConfirmation`; the accepted W59 identity decision requires
  these supplied facts to agree before a run starts.

### P-01 — exact section package at frozen base

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only 69b923156ea3988dbad3cc378644b9799a6bdd23 src/auditmanager/sections tests/integration/sections`
- captured_output:
  ```text
  src/auditmanager/sections/__init__.py
  src/auditmanager/sections/confirmation.py
  src/auditmanager/sections/review.py
  src/auditmanager/sections/routing.py
  src/auditmanager/sections/suggestion.py
  src/auditmanager/sections/suggestion_patterns.json
  tests/integration/sections/test_confirmation.py
  tests/integration/sections/test_review.py
  tests/integration/sections/test_routing.py
  tests/integration/sections/test_suggestion.py
  ```
- interpretation: there is no separate staged-route check; this list alone
  does not prove storage provenance or grant a runtime route.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/sections/staged_routing.py`
- `tests/integration/sections/test_staged_routing.py`
- `docs/program/tasks/W59-INT-STAGED-ROUTE-PREP-01.md`
- `docs/program/W59-INT-STAGED-ROUTE-PREP-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, existing section modules/resources,
`runs/**`, analysis profiles, API/router/UI, provider, root dependencies/locks,
composition root, global styles, `CURRENT_STATE.md`, remote refs and tags.

## Non-goals

No SECTION-SEAL, persisted stage/confirmation, actor authentication, Run pin
write, profile activation, cross-section analysis, provider call, corpus use,
DB/S3, full beta acceptance or legacy profile prompt.

## Deliverables

One additive pure staged-route guard, focused tests and paired report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/sections/test_staged_routing.py` — pass;
- Python compilation, direct task governance, frozen SHA-256 readback,
  `git diff --check` and exact changed-path proof — pass;
- no Docker/PG/S3/full suite while W55b gate owns the host.

## Integration contract

Only the future W59 section-seal owner may wire this guard. Its adapter must
load version membership, the explicit saved version stage and expert-confirmed
section in one authorized transaction, supply a sealed executable profile
map, and persist the returned route pin with the Run. The pure function
cannot establish that supplied values came from those reads. It must replace
the earlier section-only guard at run start rather than leaving a bypass.

## Failure/idempotency/security cases

Missing/unclassified/foreign stage or section, mismatch across P/R, invalid
confirmer identity and absent/invalid profile refuse without AR fallback.
Identical valid input returns an equal immutable pin, with no mutation or I/O.

## Rollback / feature flag

Remove the additive module and test before wiring. No DB rollback or feature
flag is needed.

## Handoff

- changed files/checks/limits: paired report;
- contracts: none;
- next: W58-code close, SECTION-SEAL and authoritative served integration.
