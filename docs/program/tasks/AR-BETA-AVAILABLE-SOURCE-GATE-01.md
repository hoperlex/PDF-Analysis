# Task AR-BETA-AVAILABLE-SOURCE-GATE-01 — bounded AR beta source policy

task_id: AR-BETA-AVAILABLE-SOURCE-GATE-01
status: active

## Outcome

The six AR scope groups expose an explicit, machine-checked beta source disposition for every C01–C22 topic. Only a source-qualified item can enter a normative request. All other topics remain visible as requiring expert review, with an exact reason and source trail. A missing or altered source policy refuses before a model request.

## Depends on

- `AR-NORM-MAP-APPROVAL-PREP-01` — completed decision sheet.
- `AR-SIX-RUN-SCOPE-BRIDGE-01` — completed scope identity boundary.

## Frozen inputs / contract versions

- Development base `54585633bbae7ff4b12f296afdb1c96be0e5f485`.
- Contract `1.0.0`; migration head `0031_executor_pull_channel`.
- Repaired snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74`; six-group composition `79396188486c430729213279fb7c1c8fca7c13ede3f3f13388d06d9f93bbb781`.
- Owner direction: use obtainable sources for a beta; preserve six separate Run provenance and the 22,000-character per-set cap. No unverified original-checklist number is approved by that direction.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `src/auditmanager/analysis/profiles/ar_v3/norm_map/beta_sources.json`
- enumerator_owner: `AR-BETA-AVAILABLE-SOURCE-GATE-01`
- totality_query: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract/norm_map`

## Captured premise evidence

- premise: no reviewed map or served v3 profile exists; the fixed six-group bridge and C01–C22 decision sheet do exist.

### P-01 — frozen development candidate

- captured_at: 2026-10-23
- command: `git rev-parse HEAD; rg -n 'Decision state|scope_membership' docs/program/AR-NORM-MAP-APPROVAL-PREP-01.md src/auditmanager/analysis/profiles/ar_v3/scope_partition.py`
- captured_output:
  ```text
  54585633bbae7ff4b12f296afdb1c96be0e5f485
  src/auditmanager/analysis/profiles/ar_v3/scope_partition.py:89:def scope_membership(scope_id: str) -> ScopeMembership:
  src/auditmanager/analysis/profiles/ar_v3/scope_partition.py:156:    "scope_membership",
  docs/program/AR-NORM-MAP-APPROVAL-PREP-01.md:3:**Task:** [AR-NORM-MAP-APPROVAL-PREP-01](tasks/AR-NORM-MAP-APPROVAL-PREP-01.md). **Frozen development base:** `b5e089b5c6a07a7bb53f6b60007c9f5041ebff8d`, 2026-10-23. **Decision state:** no C item is owner-approved; no reviewed `map_sha256`, qualified production `nrs_`, or served v3 profile exists in this tree.
  ```
- interpretation: source availability must be recorded separately from approval and served authority.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v3/norm_map/**`
- `tests/contract/norm_map/**`
- `docs/program/tasks/AR-BETA-AVAILABLE-SOURCE-GATE-01.md`
- `docs/program/AR-BETA-AVAILABLE-SOURCE-GATE-01.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependencies/locks, composition root, global styles, current section registry, provider transport, router/UI, corpus bytes, `origin/main`, tags and deployment host.

## Non-goals

No legal status or project applicability assertion from a registry card. No claim that this policy alone serves v3, publishes findings or completes the beta acceptance gate. No silent substitution of an official source by a developer draft.

## Deliverables

- Canonical item disposition file for C01–C22, each carrying source class, selected source links and the exact open decision.
- Parser/validator that requires complete six-scope coverage, valid identity, honest source grade and no duplicate item, and exposes only qualified topics to later map construction.
- Tests and a report with exact source limits and the next integration boundary.

## Checks

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/contract/norm_map tests/contract/program`
- `git diff --check`; staged allowed-path proof.

## Integration contract

`AR-NORM-MAP-01` may consume only `eligible` entries for candidate map bytes. Every deferred entry must be reported by C ID and reason; six-Run aggregation may never imply all 22 were checked when some were deferred. The downstream runtime must load the exact reviewed policy digest, then bind map/set/Attempt, and refuse if the policy or scope disagrees. A source acquisition changes the policy digest and requires fresh review.

## Rollback / feature flag

This policy is unserved. Revert its files before activation. After any future Run pin, retain that Run's immutable policy/map/set identity and deactivate only through a separately owned profile switch.
