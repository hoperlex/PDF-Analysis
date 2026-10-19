# Task W59-SEAL-FOLLOWUP-01 — suites the section seal could not reach classify before they run

task_id: W59-SEAL-FOLLOWUP-01

## Outcome

The characterization baseline and the W55b QA suites start runs the way the product
now requires — the version is classified (stage and section) before `startRun` — and
pass again on their own containers, so `D-181`'s suite half is closed and the deferred
complete gate does not go red for a known reason.

## Depends on

- `W59-SECTION-SEAL-01` — completed, merged.

## Frozen inputs

- base commit: `979632af8a8a68d59841ffcb7131d3a1bb65f37a` (`integration/night-1020`);
- migration head `0024_version_classification`; API 50/57/137;
- rulings: `R-135`, `R-139`; seal report `docs/program/W59-SECTION-SEAL-01.md` §5.4.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `tests/characterization/**`
- `tests/integration/qa_w55b/**`
- `docs/program/W59-SEAL-FOLLOWUP-01.md`
- `docs/program/tasks/W59-SEAL-FOLLOWUP-01.md`

## Lane resources

- foundation_instance: `auditmanager-w59-seal-followup`
- postgres_port: `57540`
- s3_api_port: `61140`
- s3_console_port: `61141`
- postgres_db: `auditmanager_w59_seal_followup`
- s3_bucket: `auditmanager-w59-seal-followup`

## Forbidden hotspots

Every `src/**`, `contracts/**`, migrations, `tests/support/**`, any `conftest.py` outside
the two allowed directories, web, dependency files, `CURRENT_STATE.md`, refs, tags.

## Non-goals

No product change; a characterization record is re-captured only where the classify
step legitimately adds a request, and every other byte of the record must stay equal
(assert, do not blindly re-capture).

## Deliverables

Updated suites and report `docs/program/W59-SEAL-FOLLOWUP-01.md` with the before/after
failure lists.

## Required tests

The two suites on the lane's own containers, before and after. No full gate.

## Integration contract

Merge as a follow-up of the W59 sections slice.

## Failure/idempotency/security cases

A characterization diff beyond the added classify exchange is a finding to report, not
to absorb.

## Rollback / feature flag

Revert the merge.
