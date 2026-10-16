# Task W59-INT-FINDING-OBSERVATION-IDENTITY-01 — refuse reused observation identity

task_id: W59-INT-FINDING-OBSERVATION-IDENTITY-01

## Outcome

The unserved W59 exact finding matcher refuses a source and target finding
whose `finding_observation_id` is the same, even when their `finding_uid`s are
different. Distinct observation IDs retain the existing deterministic match.

## Depends on

- `W59-INT-FINDING-MATCH-SUGGESTIONS-01` — completed pure finding matcher.

## Frozen inputs

- base commit: `417123c729599cfa075d3461038c8dd15b86d4a3`
- source matcher SHA-256: `c3c90780796bf59000bf66a396f295dc2770e89c8ed982df83a4ea24dd1f1600`;
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- domain identifiers SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- code-first scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- migration head: `0023_norm_citations`; R-135 applies.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the matcher checks observation-ID uniqueness within each version,
  but checks only finding-ID intersection across versions.

### P-01 — missing cross-version observation check

- captured_at: 2026-10-16
- command: `rg -n -F -e 'seen_observations' -e 'finding_identity_crosses_versions' src/auditmanager/comparison/finding_match_suggestions.py`
- captured_output:
  ```text
  138:    seen_observations: set[str] = set()
  148:        if finding.finding_uid in seen_findings or finding.finding_observation_id in seen_observations:
  151:        seen_observations.add(finding.finding_observation_id)
  246:        raise FindingMatchSuggestionRefused("finding_identity_crosses_versions")
  ```
- interpretation: the two sets are individually checked, but observation
  identity is not checked across the ordered version pair. The exact source
  SHA above identifies the whole frozen file.

### P-02 — observation ID is globally unique in storage

- captured_at: 2026-10-16
- command: `rg -n -F 'finding_observation_id text PRIMARY KEY' db/migrations/versions/20260910_0002_pc01_schema.py`
- captured_output:
  ```text
  917:            finding_observation_id text PRIMARY KEY,
  ```
- interpretation: a reused ID cannot designate two separately persisted
  observations. This pure function is still unserved and does not read storage.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/comparison/finding_match_suggestions.py`
- `tests/integration/comparison/test_finding_match_suggestions.py`
- `docs/program/tasks/W59-INT-FINDING-OBSERVATION-IDENTITY-01.md`
- `docs/program/W59-INT-FINDING-OBSERVATION-IDENTITY-01.md`

## Forbidden hotspots

`contracts/**`, migrations, other comparison or section modules, served
routes/API/UI, analysis profiles, DB/S3 adapters, root dependencies/lock
files, composition root, global styles, `CURRENT_STATE.md`, refs, tags and
Docker.

## Non-goals

No new matching rule, fuzzy or AI matching, finding publication, approved
match state, expert decision, provider call, qualified corpus, runtime wiring,
complete gate, deployment or beta claim.

## Deliverables

A cross-version observation-ID guard after both sides are validated, a
failing-then-passing regression, a distinct-ID green case and this task/report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/comparison/test_finding_match_suggestions.py tests/integration/comparison/test_decision_carryover.py tests/integration/comparison/test_raw_evidence_seal.py` — pass;
- Python compilation, frozen SHA readback, direct task governance, exact
  allowed-path proof and `git diff --check` — pass;
- no full gate under R-135.

## Integration contract

The existing function returns the same suggestion and digest for distinct,
valid observation identities. It raises
`FindingMatchSuggestionRefused("finding_observation_identity_crosses_versions")`
before emitting any suggestion when the source and target sets intersect by
observation ID. This does not establish persisted-source custody.

## Failure/idempotency/security cases

Both version sets must first pass their existing identity, Run, page and
evidence checks. Any cross-version overlap then refuses for the whole call;
there is no partial output. Repetition and input reordering remain stable.

## Rollback / feature flag

Revert this source commit before runtime wiring. No served or persisted
behavior changes, so no flag or data rollback is needed.

## Handoff

- changed files/checks/risks: accompanying result report;
- contracts: unchanged;
- next: integrate only this pure correction, preserving the unserved status.
