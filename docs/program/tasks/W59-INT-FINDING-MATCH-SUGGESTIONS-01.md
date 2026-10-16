# Task W59-INT-FINDING-MATCH-SUGGESTIONS-01 — exact finding candidates across linked sheets

task_id: W59-INT-FINDING-MATCH-SUGGESTIONS-01

## Outcome

A pure function suggests cross-version finding pairs only when each issue's
category, text and grounded quotes match uniquely after an explicitly approved
sheet mapping. Ambiguous, changed or unlinked issues do not yield a suggestion.
No suggestion is an approved match or a carried expert verdict.

## Depends on

- `W59-INT-VERSION-PAIR-READ-01` — completed exact ordered version preflight;
- `W59-INT-VERSION-RAW-TEXT-PREP-01` — completed approved SheetLink value shape;
- `W59-INT-DECISION-CARRYOVER-PREP-01` — completed confirmation policy requiring an authoritative match;
- `W59-INT-RAW-EVIDENCE-SEAL-PREP-01` — completed raw evidence seal for a later distinct artifact.

## Frozen inputs

- base commit: `e61fc4570e49d0411b72e5363a2bafd5eeb5da97`;
- domain identifiers SHA-256: `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`;
- API SHA-256: `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256: `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256: `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315b2c1239453ba3a`;
- W58–W63 scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- roadmap SHA-256: `e7e73b21996c1c6f37f7b3f5cb741b7d50054dcd7751b3a401ed7fba514a7be5`;
- ADR-0013 SHA-256: `a5d8a88e1a7b531ea00cd383a7aa00f691cada0a1c118e807b48c1949eaab410`;
- migration head: `0022_findings_v2`; R-135; roadmap C-2/C-4.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: approved finding matching is still missing between raw comparison
  evidence and expert-confirmed carryover. The W59 source boundary has no
  finding suggestion module at the captured base.

### P-01 — current comparison modules

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only HEAD src/auditmanager/comparison`
- captured_output:
  ```text
  src/auditmanager/comparison/README.md
  src/auditmanager/comparison/decision_carryover.py
  src/auditmanager/comparison/raw_evidence_seal.py
  src/auditmanager/comparison/raw_text.py
  src/auditmanager/comparison/version_reader.py
  ```
- interpretation: pure order/raw/carryover pieces exist; there is no finding
  matching policy. This does not grant runtime or approval authority.

### P-02 — comparison and carryover decision

- captured_at: 2026-10-16
- command: `rg -n '^\| C-[24] ' docs/program/dispatch/ROADMAP-TO-BETA.md`
- captured_output:
  ```text
  449:| C-2 | depth for documents | **text + AI summary**: sheet pairing, deterministic text differences as evidence, AI classification and summary on top; AI never alters the raw differences |
  451:| C-4 | decision carryover | **with confirmation**: a matched finding is offered its previous decision marked «из версии N»; the expert confirms singly or in bulk; fixed findings are marked resolved |
  ```
- interpretation: C-4 requires matching before a confirmation offer, while
  leaving approved-match persistence, ambiguous cases and resolved-state
  semantics to the future comparison owner.

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
- `docs/program/tasks/W59-INT-FINDING-MATCH-SUGGESTIONS-01.md`
- `docs/program/W59-INT-FINDING-MATCH-SUGGESTIONS-01.md`

## Forbidden hotspots

`contracts/**`, migrations, existing comparison/decision/section files,
public boundaries, routers, API/UI, workers, analysis profiles, storage,
root dependencies/locks, composition root, global styles, `CURRENT_STATE.md`,
refs, tags and Docker.

## Non-goals

No fuzzy or AI matching, automatic approval, persisted match/revision, expert
authorization, verdict carryover, fixed/resolved inference, DB/Blob reads,
runtime wiring, full gate or beta claim. An absent suggestion is not proof
that an issue is fixed. The caller supplies published finding observations
from exactly one source run and one target run.

## Deliverables

One additive deterministic suggestion module, focused refusal tests, task and
result report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/comparison/test_finding_match_suggestions.py tests/integration/comparison/test_decision_carryover.py tests/integration/comparison/test_raw_evidence_seal.py` — pass;
- Python compilation, direct governance, frozen hashes, whitespace,
  `git diff --check` and exact owned-path proof — pass;
- no Docker, live DB, network or complete gate under R-135.

## Integration contract

The future W59 comparison owner loads a proved ordered pair, authoritative
approved SheetLinks and complete published findings/evidence of one specified
run per version under a consistent transaction. This pure function returns
rebuildable suggestions only. A separately authenticated expert approves a
match with revision/custody; only that authoritative persisted match may feed
`MatchedDecision` and its explicit carryover confirmation workflow. The
suggestion digest is provenance for the suggestion, not an authorization token.

## Failure/idempotency/security cases

Mixed run/version identities, duplicate finding or link identity, reused
page, invalid quote/page/text, oversized input or reversed pair refuse. A
non-unique normalized issue+quote key on either side yields no suggestion;
unlinked or changed issues also yield none. Reordered inputs produce the same
sorted result. The digest retains the exact source and target input strings.

## Rollback / feature flag

Remove the additive module before runtime wiring. No active behavior, data
migration or feature flag.

## Handoff

- changed paths/checks/limits: accompanying result report;
- contracts: none;
- next: W59 comparison owner adds approved-match state, expert authorization,
  transactional source reads and explicit fixed/resolved policy.
