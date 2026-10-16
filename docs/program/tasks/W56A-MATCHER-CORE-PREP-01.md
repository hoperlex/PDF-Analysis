# Task W56A-MATCHER-CORE-PREP-01 — pure recorded-evaluation matching

## Outcome

A deterministic, provider-free matcher scores the synthetic AR v2 manifest
against groups of finding observations. It reports seeded recall, control
false-positive pressure, per-category counts, unmatched groups and over-merge.
It creates no baseline or quality verdict.

## Depends on

- `W56A-INT-GENERATOR-01` — complete at `0d7d27bb`;
- `W56A-INT-MERGE-CORE-01` — complete on dev at `68b6f81f`.

## Frozen inputs and contracts

- base `origin/dev=68b6f81f241e00192b52bf0a2cc4351897f06c3c`;
- manifest SHA-256
  `95e07c2919d46a600cb9ffead41c883fd38d141699c6857a4700126d6dae6fb7`;
- `docs/program/validation/PC-02_PROTOCOL.md` §11's mechanical match rule;
- `W56-PLAN.md` §A3.6's any-member and over-merge rule. No API, domain,
  stage or model contract changes.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: `fixtures/evaluation/ar_v2/expected_issues.json` (read-only);
- enumerator_owner: `W56A-GENERATOR-PREP-01`;
- totality_query: `tests/contract/evaluation/test_matcher_core.py`.

## Captured premise evidence

- premise: recorded-only code can proceed while MODEL-PIN is blocked; this
  task owns a pure matcher subset of a later evaluation harness.

The code-first plan §4 allows independent code while MODEL-PIN is blocked.
This pure matcher is a sequential subset of later `W56A-HARNESS-01`, which
still owns the runner, recordings, baseline, live cap and gate thresholds.

- captured_at: 2026-10-16
- command: `sed -n '118,133p' docs/program/dispatch/CODE-FIRST-TO-BETA.md`
- captured_output:
  ```text
  slot согласует правдивую dev-историю и значение `VERSION`; контрактная версия
  меняется только в финальном beta seal. Отсутствие этой работы блокирует
  релизную упаковку, но не код независимых профилей и модулей.

  ## 4. Зависимости, которые нельзя замаскировать проверкой

  - W56a freeze на локальной `integration/w56a` уже **STOPPED**:
    `W56A-PROBE-01` получил от stand gateway другую модель и несогласованную
    цену, recording gateway не сконфигурирован. `W56A-MODEL-REQUIREMENT-REVIEW-01`
    предложил конкретное разделение: recorded-only `W56A-DEV-FREEZE-01`
    разрешает SEAL без `P02_LOCK.json` и подготовку GENERATOR; отдельный
    `W56A-MODEL-PIN-01` единолично владеет lock после успешных двух gateway
    probes; PROVIDER/live activation идут позже. Принять это разделение как
    кодовый маршрут, сохранив `R-133`: identity check должен fail closed,
    неподтверждённые `gateway_name` и тарифы не угадываются. Если gateway не
    удаётся подтвердить к концу кодовой серии, соответствующий live adapter
  ```
- interpretation: retrospective plan capture supports recorded-only separation;
  it does not supply a model identity or a baseline.

## Historical evidence

- correction_mode: addendum
- source_record: docs/program/tasks/W56A-MATCHER-CORE-PREP-01.md at `e61fc457`
- addendum_path: docs/program/PROGRAM-GOVERNANCE-REPAIR-01.md

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `tools/evaluation/__init__.py` and `tools/evaluation/matcher.py` (new);
- `tests/contract/evaluation/test_matcher_core.py` (new);
- this task and `docs/program/W56A-MATCHER-CORE-PREP-01.md` (new report).

## Forbidden hotspots

Existing fixtures and generator, `fixtures/evaluation/ar_v2/baseline.json`,
recordings, `contracts/**`, migrations, application and web code, root
dependencies/locks, `P02_LOCK.json`, composition root, global styles,
`CURRENT_STATE.md`, `VERSION`, refs, tags and stand state.

## Non-goals

No provider call, invented baseline, live spend, runtime activation,
acceptance, full local gate or beta verdict.

## Deliverables and checks

- mechanical match on same bundle/category/page and substring-compatible
  quote, across any group member, without using finding identity;
- distinct seeded/control denominators, per-category rates, unmatched groups
  and over-merge when one group hits two seeded issues;
- refuse empty/duplicated ground truth and malformed predictions rather than
  treating an empty manifest as a perfect score;
- tests with real synthetic manifest and planted cases for any-member,
  boundaries, over-merge, controls, empty prediction and vacuity;
- Python compilation, focused pytest, `git diff --check` and exact path
  proof. No full local gate under R-135.

## Integration contract and rollback

Later HARNESS adapts recorded run outputs to this pure input and owns measured
baseline and thresholds. If an upstream profile changes, recordings must be
remeasured; this module alone never establishes quality. Revert the new files
before use or correct forward after integration. The lane hands its commit to
a dedicated dev integration slot and pushes no ref.
