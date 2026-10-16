# Task W59-INT-PROFILE-READINESS-GAP-01 — identify the pre-seal profile inputs

task_id: W59-INT-PROFILE-READINESS-GAP-01

## Outcome

A reviewable gap report names the exact evidence and approvals still needed
before W59 can implement AI, PS, POS and TX profiles. It does not create an
executable profile from the legacy vocabulary.

## Depends on

- `W59-INT-PROFILE-METADATA-PREP-01` — completed candidate catalogue.
- `W59-INT-CONFIRMATION-PREP-01` — completed pure expert-choice policy.
- `W59-INT-SECTION-ROUTE-PREP-01` — completed fail-closed route guard.

## Frozen inputs

- base commit: `a3d5c3aefba567d09a93ed2742d38fed7013c284`
- API SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- domain identifiers SHA-256: `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`;
- error catalogue SHA-256: `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis stage registry SHA-256: `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- candidate metadata SHA-256: `ffc79739053944e8adc2546da0bf82a99c4a781ebbed28c9f4239b267cfa8490`;
- code-first scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- fast-path plan SHA-256: `d9f194ad5bed7fbd7dd67713618cd4b8a7eb9c3549d4c8c2a991749f33bd2f00`;
- migration head: `0022_findings_v2`, as recorded by the completed W59 prep tasks.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: candidate metadata and the plan were insufficient to grant
  executable AI/PS/POS/TX profiles at this task's freeze.

### P-01 — candidate metadata is the only non-AR section profile package

- captured_at: 2026-10-15
- command: `git rev-parse HEAD && git ls-tree -r --name-only HEAD src/auditmanager/analysis/profiles`
- captured_output: `a3d5c3aefba567d09a93ed2742d38fed7013c284`; the listed package files are under `ar_v2/` and `section_candidates/` only.
- interpretation: this tree has no executable AI/PS/POS/TX profile package.

### P-02 — the plan explicitly gates profile implementation

- captured_at: 2026-10-15
- command: `sed -n '17,20p' docs/program/dispatch/CODE-FIRST-SCOPE-W58-W63.md; sed -n '88,95p' docs/program/dispatch/FAST-PATH-NORMS-SECTIONS.md`
- captured_output: W59 SECTION-SEAL follows W58 code close; PROFILES-A follows SECTION-SEAL and requires recorded cases, citation provenance and foreign-profile refusal. Section evidence requires source hashes/licence, named reviewer, independent positive/negative field set, denominators, norms availability and approved private storage. Early candidates need a measured public schema and do not count as accepted routes.
- interpretation: legacy metadata alone is insufficient to define a runnable profile.

### P-03 — retrospective file-list verification at the frozen base

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only a3d5c3aefba567d09a93ed2742d38fed7013c284 src/auditmanager/analysis/profiles`
- captured_output:
  ```text
  src/auditmanager/analysis/profiles/__init__.py
  src/auditmanager/analysis/profiles/ar_v2/__init__.py
  src/auditmanager/analysis/profiles/ar_v2/ar_checklist.md
  src/auditmanager/analysis/profiles/ar_v2/checklist.md
  src/auditmanager/analysis/profiles/ar_v2/content.py
  src/auditmanager/analysis/profiles/ar_v2/drawing_types.md
  src/auditmanager/analysis/profiles/ar_v2/finding_categories.md
  src/auditmanager/analysis/profiles/ar_v2/grounding.py
  src/auditmanager/analysis/profiles/ar_v2/merge_input.py
  src/auditmanager/analysis/profiles/ar_v2/project_params.md
  src/auditmanager/analysis/profiles/ar_v2/prompt_material.py
  src/auditmanager/analysis/profiles/ar_v2/proposal_grounding.py
  src/auditmanager/analysis/profiles/ar_v2/recognised_context.py
  src/auditmanager/analysis/profiles/ar_v2/recorded_request.py
  src/auditmanager/analysis/profiles/ar_v2/registered.py
  src/auditmanager/analysis/profiles/ar_v2/response.py
  src/auditmanager/analysis/profiles/ar_v2/response_pipeline.py
  src/auditmanager/analysis/profiles/ar_v2/response_schema.py
  src/auditmanager/analysis/profiles/ar_v2/role.md
  src/auditmanager/analysis/profiles/section_candidates/__init__.py
  src/auditmanager/analysis/profiles/section_candidates/metadata.json
  src/auditmanager/analysis/profiles/section_candidates/metadata.py
  ```
- interpretation: the historical frozen tree had AR v2 and candidate
  metadata only; this is no grant for non-AR executable profiles.

## Historical evidence

- correction_mode: addendum
- source_record: docs/program/tasks/W59-INT-PROFILE-READINESS-GAP-01.md at `e61fc457`
- addendum_path: docs/program/PROGRAM-GOVERNANCE-REPAIR-01.md

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W59-INT-PROFILE-READINESS-GAP-01.md`
- `docs/program/W59-INT-PROFILE-READINESS-GAP-01.md`

## Forbidden hotspots

`contracts/**`, migrations, source and test code, existing task/report files,
`CURRENT_STATE.md`, root dependencies/locks, composition root, global styles,
Docker, DB, S3 and remote refs.

## Non-goals

No new section code, prompt, profile, registry entry, test fixture, contract,
active route, provider call, publication or beta verdict.

## Deliverables

- One exact gap report with a path to a future bounded grant.

## Required tests

- `git diff --check` — pass;
- exact changed-path inspection — only the two allowed Markdown files;
- no pytest or heavy gate while the shared host is resource constrained.

## Integration contract

The report is planning evidence only. The W59 SECTION-SEAL owner must freeze
the identity/API/DB shape after W58 code close; each profile owner then gets a
separate approved profile source, evaluation set and identity before registry
or runtime changes.

## Failure/idempotency/security cases

The report contains no client project bytes or credentials. Re-reading it has
no side effects; changed frozen inputs require a fresh task rather than
silently treating this observation as a runtime authorization.

## Rollback / feature flag

Delete these two new Markdown files if superseded. No behavioral change, DB
rollback or feature flag.

## Handoff

- changed files: this task and its paired gap report;
- contracts: none;
- next: integrator decides when W58 code close, SECTION-SEAL and field evidence
  permit a specific PROFILES-A grant.
