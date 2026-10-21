# Task W56A-INT-DECIDED-SEVERITY-01 — persist expert severity and fold the latest verdict

task_id: W56A-INT-DECIDED-SEVERITY-01

## Outcome

An expert accept on a canonical observation with a proposed severity may persist
one decided severity in the append-only ledger. A
reject or revocation clears the current decided severity, while a comment keeps
the prior verdict and severity. Decision history, journal and adapter responses
report only stored event severity; requests without severity retain their old
idempotency fingerprint and omit the optional wire property.

## Depends on

- `W56A-INT-SEAL-01` — complete on the development base; it integrated API
  severity fields, migration `0022_findings_v2` and the severity-aware view.

## Frozen inputs

- base commit: `960da9e1b7cfc5eda75fc3a1d52714bb66be8176` (`origin/dev` at task start);
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`; W56 plan §A3.2 and frozen domain revision 13.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the contract and database already accept severity on an `accept`
  event, but the decision adapter still refuses it before writing.

### P-01 — base and adapter refusal

- captured_at: 2026-10-15
- command: `git rev-parse HEAD && rg -n 'if severity is not None|v2_decision_ledger' src/auditmanager/bootstrap/adapters.py`
- captured_output:
  ```text
  960da9e1b7cfc5eda75fc3a1d52714bb66be8176
  1369:        if severity is not None:
  1372:                dependency="v2_decision_ledger",
  ```
- interpretation: this task owns the existing decision seam only. The separate
  CSV projection needs its own exact task. The integrator additionally assigned
  this task the existing finding read mapper before implementation.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/decisions/ledger.py`
- `src/auditmanager/decisions/projection.py`
- `src/auditmanager/decisions/journal.py`
- `src/auditmanager/findings/queries.py` — only if required for the decided-severity read
- `src/auditmanager/bootstrap/adapters.py` — `DecisionAdapter`, `_event_view`, `_record_view` and `_finding_view` only
- `src/auditmanager/api/schemas/decisions.py` — only if required
- `tests/integration/decisions/test_v2_severity*.py` (new)
- `docs/program/tasks/W56A-INT-DECIDED-SEVERITY-01.md`
- `docs/program/W56A-INT-DECIDED-SEVERITY-01.md` (new)

## Forbidden hotspots

`contracts/**`, migrations, `P02_LOCK.json`, root dependency/lock files,
composition root, exports, API routers, schema models,
public exports, global styles, `CURRENT_STATE.md`, provider/live calls,
stand, tags and `origin/main`.

## Non-goals

CSV columns and row policy, runtime AR v2
analysis, provider activation, corpus work, full gate and beta acceptance.

## Deliverables

Ledger write/replay and event reads, independent projection fold, finding
list/detail and decision adapter response mapping, focused tests and task
report; root integrator owns commit.

## Required tests

- focused severity tests, including DB view/fold agreement when the configured
  PostgreSQL database is available;
- Python compilation, direct task governance, `git diff --check` and exact
  allowed-path proof;
- no `make gate` under R-135.

## Integration contract

The router already passes `severity`; `DecisionAdapter` passes it into
`append_decision_under_key`, and the ledger persists it only for `accept`. A
non-null severity is part of the command fingerprint; absent severity leaves
the legacy fingerprint unchanged. A non-null severity requires a canonical
observation with a non-null `proposed_severity` before a command claim; this is
a safe current discriminator, not proof of an activated v2 profile. Event
history and journal expose event
severity, while `CurrentVerdict.decided_severity` mirrors the 0022 database view
and the independent fold. The finding mapper reports that view's decided
severity in list/detail. A later owned CSV task consumes the view.

## Failure/idempotency/security cases

Severity on reject/comment is refused before a write and by the database CHECK.
Severity on a legacy or non-canonical observation is refused before a command
claim. The profile-level runtime guard remains separate.
An unknown value is refused by the database CHECK and translated to a typed
validation failure, not coerced. Repeating a key with
the same payload replays one row; changing severity under that key is a reuse
error. The authenticated expert-only router remains the sole producer.

## Rollback / feature flag

Rollback reverts this code before external severity-bearing writes. Once such
events exist, retain the 0022 schema and reader compatibility; no flag is
needed for the already sealed optional request field.
