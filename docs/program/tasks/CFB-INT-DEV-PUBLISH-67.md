# Task CFB-INT-DEV-PUBLISH-67 — W54 session repair commands

task_id: CFB-INT-DEV-PUBLISH-67

## Outcome

Integrate the reviewed `W54-SESSION-REPAIR-01` commands and their records on
the exact published dev66 predecessor, shorten the live state to its
120-line limit with a verbatim archive, and publish the focused-checked
result as a fast-forward to `origin/dev`, with exact remote readback.

## Depends on

- `CFB-INT-DEV-PUBLISH-66` — completed at `ec41bb5881b2e677af7f22af62266818f37b2a61`.
- `W54-SESSION-REPAIR-01` — completed on this branch at `50a26daf`.

## Frozen inputs

- base commit: `ec41bb5881b2e677af7f22af62266818f37b2a61`
- API v1, stage registry, error catalogue and migration head
  `0023_norm_citations` as on the base; `VERSION=0.6.0`;
- `origin/main` and `v0.6.0` remain W55b `37393a979a430e490843d7f410e9eca9491a4ea1`;
- R-135: focused checks for intermediate development candidates; R-137.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the source task changes six paths on dev66 and no contract,
  migration, dependency or served route.

### P-01 — exact source paths

- captured_at: 2026-10-19
- command: `git diff --name-only ec41bb5881b2e677af7f22af62266818f37b2a61..50a26daf`
- captured_output:
  ```text
  docs/program/OWNER_RULINGS_2026-09-17.md
  docs/program/W54-SESSION-REPAIR-01.md
  docs/program/tasks/W54-SESSION-REPAIR-01.md
  src/auditmanager/norms/__main__.py
  src/auditmanager/norms/session_repair.py
  tests/integration/norms/repair/test_session_repair.py
  ```
- interpretation: this task adds only its four documentation paths below.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/CFB-INT-DEV-PUBLISH-67.md`;
- `docs/program/CFB-INT-DEV-PUBLISH-67.md`;
- `docs/program/CURRENT_STATE.md`;
- `docs/program/history/CURRENT_STATE_2026-10-19_ec41bb58.md` (verbatim dev66 state).

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition roots,
global styles, runtime code beyond the source task, production DB/S3,
corpus bytes, the stand, `origin/main` and tags.

## Non-goals

No repaired-snapshot load, embedding build, bundle, stand import, full gate,
deployment or beta verdict.

## Deliverables

The integrated branch, this task, its report and the shortened live state.

## Required tests

- `PYTHONPATH=src .venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/repair/test_session_repair.py`;
- the focused norms suite of `W54-SESSION-REPAIR-01`;
- `PYTHONPATH=src .venv/bin/python -m pytest -q -p no:cacheprovider tests/contract/api_v1/test_doc_prose_facts.py tests/contract/program tests/contract/architecture/test_alr05_boundaries.py`;
- archive byte equality with `git show ec41bb58:docs/program/CURRENT_STATE.md`;
- `git diff --check`, task `governance_findings` = `[]`, exact path proof,
  clean tree, remote fast-forward check and readback.

## Integration contract

`origin/dev` advances by fast-forward from `ec41bb58` to the checked commit
only. Nothing on `origin/main`, tags or the stand changes.

## Failure/idempotency/security cases

A moved `origin/dev`, a dirty tree or any failed listed check stops the push.
No credential is read or printed.

## Rollback / feature flag

A reviewed forward revert of the integrated commits; no data or flag.

## Handoff

- changed files: the allowed paths and the source task's six paths;
- contracts: none;
- next: W54 repaired-snapshot load after host capacity and the owner's
  decision on transcription verification;
- forbidden hotspots remain untouched.
