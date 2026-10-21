# Task W59-INT-CARRYOVER-BOUNDS-01 — bound pure carryover batches

task_id: W59-INT-CARRYOVER-BOUNDS-01

## Outcome

The unserved W59 carryover planner refuses more than 200 authoritative matches
or selected offers before validating or digesting individual entries. A valid
200-item batch and existing offer digests remain unchanged.

## Depends on

- `W59-INT-DECISION-CARRYOVER-PREP-01` — completed pure offer and confirmation.
- `W59-INT-FINDING-MATCH-SUGGESTIONS-01` — completed 200-findings-per-Run bound.

## Frozen inputs

- base commit: `a09721a5895a0aff93d08f203fe1bedbbffffb8a`
- base publication: `origin/dev` dev64;
- carryover source SHA-256: `d841a7abce0b1cb3466ea75920069fe2073c1a2552c11903d5ba1ad065c5db7b`;
- finding matcher SHA-256: `b2f27e65aca31e18d7d4c77b5b8a32e7ee8c03166cf97a0749e26195f40ed269`;
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- identifiers SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
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

- premise: the pure carryover policy accepts tuple/list batches without a
  count limit, while its upstream finding matcher limits each Run to 200
  findings. A one-to-one comparison can offer at most 200 matches.

### P-01 — unbounded carryover and bounded source

- captured_at: 2026-10-16
- command: `rg -n -F -e 'MAX_FINDINGS_PER_RUN' -e 'if not isinstance(matches, (tuple, list))' -e 'if not isinstance(selected_offer_sha256s, (tuple, list))' src/auditmanager/comparison/finding_match_suggestions.py src/auditmanager/comparison/decision_carryover.py`
- captured_output:
  ```text
  src/auditmanager/comparison/decision_carryover.py:133:    if not isinstance(matches, (tuple, list)):
  src/auditmanager/comparison/decision_carryover.py:185:    if not isinstance(selected_offer_sha256s, (tuple, list)) or not selected_offer_sha256s:
  src/auditmanager/comparison/finding_match_suggestions.py:29:MAX_FINDINGS_PER_RUN = 200
  src/auditmanager/comparison/finding_match_suggestions.py:135:    if not isinstance(findings, (tuple, list)) or len(findings) > MAX_FINDINGS_PER_RUN:
  ```
- interpretation: caller-constructed carryover input can exceed the upstream
  comparison ceiling. The function is unserved, so this is a preactivation
  boundedness correction, not evidence of production exposure.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/W59-INT-DECISION-CARRYOVER-PREP-01.md`
- addendum_path: `docs/program/W59-INT-CARRYOVER-BOUNDS-01.md`

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/comparison/decision_carryover.py`
- `tests/integration/comparison/test_decision_carryover.py`
- `docs/program/tasks/W59-INT-CARRYOVER-BOUNDS-01.md`
- `docs/program/W59-INT-CARRYOVER-BOUNDS-01.md`

## Forbidden hotspots

`contracts/**`, migrations, other comparison and section modules, served
routes/API/UI, findings ledger, storage, analysis profiles, DB/S3 adapters,
root dependency/lock files, composition root, global styles,
`CURRENT_STATE.md`, refs, tags and Docker.

## Non-goals

No new matching, expert authorization, persisted offer/decision, fixed finding
policy, runtime wiring, API or contract reseal, full gate, corpus or beta claim.

## Deliverables

Two count guards, over-limit and exact-limit regressions, this task and result
addendum.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/comparison/test_decision_carryover.py tests/integration/comparison/test_finding_match_suggestions.py` — pass;
- Python compilation, frozen SHA readback, direct task governance, exact
  allowed-path handoff and `git diff --check` — pass;
- no Docker, DB/S3, network, provider or full gate under R-135.

## Integration contract

`offer_decision_carryover` accepts at most 200 complete matches and
`confirm_decision_carryover` accepts at most 200 selected digests. An oversized
batch is refused before per-item work; within the bound, offer content, digest,
ordering, stale-selection and one-to-one rules are unchanged. The future
caller still must prove a complete authoritative current snapshot and append
only after transactional expert confirmation.

## Failure/idempotency/security cases

201 matches refuse with `matches_too_large`; 201 selected digests refuse with
`selection_too_large`. Empty and malformed batches retain their old reasons.
Exactly 200 distinct valid matches and selections work repeatably. No partial
plans escape on refusal.

## Rollback / feature flag

Revert this source commit before runtime wiring. No served or persisted
behavior, so no feature flag or data rollback is needed.

## Handoff

- changed files/checks/risks: accompanying result addendum;
- contracts: unchanged;
- next: integrate this pure preactivation bound, preserving the unserved
  carryover status and future authoritative-snapshot requirement.
