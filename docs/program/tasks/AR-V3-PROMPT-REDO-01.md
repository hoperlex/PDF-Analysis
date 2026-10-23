# Task AR-V3-PROMPT-REDO-01 — coherent AR v3 draft prompt

task_id: AR-V3-PROMPT-REDO-01

## Outcome

The AR v3 draft system prompt gives one coherent twelve-category policy: the
seven existing internal checks and five evidence-bound normative checks. It
does not include the v2-only sentences forbidding norm checks or limiting the
answer to seven categories. PDF/OCR/norm data and response shape stay bounded.

## Depends on

- `W57A-INT-V3-PROMPT-MATERIAL-PREP-01` — completed on `origin/dev`.
- `W57A-INT-V3-RESPONSE-PREP-01` — completed twelve-category schema.

## Frozen inputs

- `origin/dev=3bc7dae1a62ccd871ed42fc364ffa139cc2313f3` at start;
- contract `1.0.0`, API 87 paths / 99 operations / 284 schemas, 27 errors;
- migration head `0031_executor_pull_channel`;
- v2 reviewed prompt content SHA-256
  `01bee01f8c7f1c59227ff6c17398f1034f5094c9c3b8e26fc66ab5130a4ca610`;
- W57 plan A3.1/A3.3 and existing v3 response schema.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: `render_v3_system_prompt()` currently appends all six v2 sections;
  `role.md` forbids external norm checks and `finding_categories.md` says
  exactly seven categories, contradicting v3's five normative categories.

### P-01 — v2-only rules in v3's source sections

- captured_at: 2026-10-23
- command: `rg -n 'Не проверяй соответствие внешним нормам|Допустимы ровно семь категорий|for section in reviewed_sections' src/auditmanager/analysis/profiles/ar_v2/role.md src/auditmanager/analysis/profiles/ar_v2/finding_categories.md src/auditmanager/analysis/profiles/ar_v3/prompt_material.py`
- captured_output:
  ```text
  src/auditmanager/analysis/profiles/ar_v2/role.md:10:Не проверяй соответствие внешним нормам и не выноси решение за эксперта.
  src/auditmanager/analysis/profiles/ar_v2/finding_categories.md:6:Допустимы ровно семь категорий:
  src/auditmanager/analysis/profiles/ar_v3/prompt_material.py:95:    for section in reviewed_sections():
  ```
- interpretation: the draft v3 renderer must replace the first two v2-only
  instructions while retaining the four common reviewed sections.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v3/prompt_material.py`
- `tests/integration/analysis/test_ar_v3_prompt_material.py`
- `docs/program/tasks/AR-V3-PROMPT-REDO-01.md`
- `docs/program/AR-V3-PROMPT-REDO-01.md`

## Forbidden hotspots

`contracts/**`, migrations, v1/v2 source, root dependencies/locks,
composition root, provider, served Run/API/profile registry, norms, UI/global
styles, corpus, release refs/tags and deployment host.

## Non-goals

No model call, map/source qualification, v3 activation, 128,000-character cap,
$1.50 run ceiling, contract reseal, expert judgement or `origin/main` push.

## Deliverables and checks

Coherent prompt, tests for categories/provenance/bounds and this task/report.
Run focused AR v3 prompt/request/response tests, program-contract tests,
compile, whitespace and allowed-path proof. Under R-135 this intermediate
development candidate does not run the final beta `make gate`.

## Integration contract

The renderer remains pure and unserved. Future profile ownership must review
and seal these exact prompt bytes with a qualified Run-pinned set; the existing
request candidate binds actual system/user/schema text in its SHA. Existing v2
prompt material is unchanged. No model proposal becomes a canonical finding.

## Rollback / feature flag

Revert the bounded prompt packet; no served behavior or flag changes.
