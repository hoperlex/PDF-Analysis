# Task W54-CORPUS-REPAIR-PLAN-01 — offline priced-repair plan

task_id: W54-CORPUS-REPAIR-PLAN-01

## Outcome

An offline, zero-call plan for the restore-verified W54 base identifies the
exact suspect pages, selected priced model and base snapshot. The plan is
retained outside Git and checked against the expected 121-page population.
No proxy credential, database or paid request is used.

## Depends on

- `W54-CORPUS-PROMOTION-01` — completed base dump restore verification at
  `ecde692842f3771e4f253ea880a0bb81651825e9`;
- `W54-REPAIR-01` — completed durable repair machinery;
- `W54-INT-CORPUS-READINESS-01` — completed operator sequence.

## Frozen inputs

- code base: `ecde692842f3771e4f253ea880a0bb81651825e9`;
- source drop: `/root/projects/PDF-Analysis/.local/norms/corpus` (read-only);
- source SHA256SUMS: `/root/projects/PDF-Analysis/.local/norms/corpus-sums/2026-10-15/SHA256SUMS`, SHA-256 `eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`;
- verified base dump SHA-256 `e1280373ffd7fa3deaa0716429def1844d7e858e79bae7fbad5ade6d516ff74d` and `.verified` marker;
- pricing module SHA-256 `355a21ade3a983aca202ba73c79147e79427c98ae6bcb15ac33d8ed38fdffd1c`;
- owner-selected rate-card model: `claude-opus-5` (2026-10-16);
- migration head `0022_findings_v2`; no database access in this task.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the base dump is restore-verified, but the 121-page repair plan has
  not been run with the owner's selected model.

### P-01 — base dump identity and verification marker

- captured_at: 2026-10-16
- command: `sha256sum .local/norms/promotion-dumps/promotion-20261015T134454Z.dump`
- captured_output:
  ```text
  e1280373ffd7fa3deaa0716429def1844d7e858e79bae7fbad5ade6d516ff74d  .local/norms/promotion-dumps/promotion-20261015T134454Z.dump
  ```
- interpretation: the adjacent `.verified` marker and completed promotion
  report permit an offline repair plan from this unchanged source.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W54-CORPUS-REPAIR-PLAN-01.md`;
- `docs/program/W54-CORPUS-REPAIR-PLAN-01.md`;
- ignored `.local/norms/repairs/plan-20261016.json` and adjacent local log.

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root,
global styles, runtime code, source corpus/sums bytes, promotion database or
volume, paid journal, proxy credential, production stand, S3, `CURRENT_STATE.md`,
remote refs and tags.

## Non-goals

No priced sample or full repair, proxy call, new dump, snapshot, embeddings,
bundle, DB/S3 publication, deployment, full gate or beta verdict.

## Deliverables

Exact ignored plan JSON and digest, this task and a result report identifying
the next credential-gated operation.

## Required tests

- exact frozen source/dump/pricing SHA read-back and `.verified` marker;
- `PYTHONPATH=src .venv/bin/python -m auditmanager.norms repair plan --corpus /root/projects/PDF-Analysis/.local/norms/corpus --model claude-opus-5` — exit 0, exactly 121 pages;
- no database/proxy settings in the command; direct task governance,
  whitespace and exact changed-path proof.

## Integration contract

The later paid sample receives this plan's exact base snapshot, the verified
source sums, selected `claude-opus-5` rate and a credential file outside Git.
It must still enforce the three-largest-crop projection and cumulative $10
ceiling. Without a credential file, no paid operation starts.

## Failure/idempotency/security cases

An unpriced model, changed source, unexpected page count or missing verified
base stops the chain. Repeating the deterministic plan replaces only its
ignored output after comparing the digest. Never log or commit a credential.

## Rollback / feature flag

Remove the ignored plan output if this candidate is abandoned; no data or
runtime behavior changes and no flag is needed.

## Handoff

- changed files: task and result report only;
- contracts: none;
- next: paid-sample owner once a proxy credential file exists;
- forbidden hotspots remain untouched.
