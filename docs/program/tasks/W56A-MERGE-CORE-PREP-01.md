# Task W56A-MERGE-CORE-PREP-01 — deterministic grounded-observation grouping

## Outcome

A pure function groups already grounded observations into `findings.merged`
with stable canonical ordinals under W56 §A3.3. It has no provider, database,
runtime wiring or publication side effect, so it can progress while model
identity remains blocked.

## Depends on

- `W56A-INT-SEAL-01` — complete at `da355eda`;
- `W56A-INT-GENERATOR-01` — complete on `origin/dev` at `0d7d27bb`.

## Frozen inputs and contracts

- exact base `origin/dev=0d7d27bb50ba35350b0287073e7e3f3f99978e5f`;
- analysis registry SHA-256
  `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- `P02_SEAMS.md` §4.11 and `W56-PLAN.md` §A3.3; migration head
  `0022_findings_v2`. `P02_LOCK.json` remains read-only.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: `contracts/analysis/v1/stage-registry.json` (read-only);
- enumerator_owner: `W56A-SEAL-01`;
- totality_query: focused rule tests in `test_v2_merge_core.py`.

## Captured premise evidence

- premise: recorded-only code can proceed while MODEL-PIN is blocked; this
  task owns a pure merge subset without publication or runtime wiring.

The code-first plan §4 permits independent code while the two gateway identity
proofs remain unavailable. This task grants only the pure core of the later
`W56A-MERGE-01`; that task still owns gate ordering, finding identity, database
publication, queries and API activation. No predecessor of the blocked
`W56A-PROVIDER-01` is represented as complete.

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
  it does not authorize provider use or finding publication.

## Historical evidence

- correction_mode: addendum
- source_record: docs/program/tasks/W56A-MERGE-CORE-PREP-01.md at `e61fc457`
- addendum_path: docs/program/PROGRAM-GOVERNANCE-REPAIR-01.md

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/stages/finding_merge.py` (new, pure only);
- `tests/integration/findings/test_v2_merge_core.py` (new, no DB fixture);
- this task file and `docs/program/W56A-MERGE-CORE-PREP-01.md` (new report).

## Forbidden hotspots

`contracts/**`, migrations, `P02_LOCK.json`, existing analysis/run/finding
modules, executor, composition root, root dependencies/locks, global styles,
`VERSION`, `CURRENT_STATE.md`, recordings, `origin/dev`, `origin/main`, tags
and stand state.

## Non-goals

No model selection, text stage, grounding gate, provider call, finding UID,
publication, decision, UI, full local gate or beta claim.

## Deliverables and checks

- a deterministic algorithm over ordinals and evidence spans: same-category
  same-page half-open overlap or equal NFC/case-folded/whitespace-collapsed
  quote of at least 20 characters; connected components; canonical earliest
  page/span then ordinal; stable output order and rule version;
- explicit refusal of malformed ordinals, empty evidence and bad spans;
- focused tests for overlap/touching, quote threshold/normalisation, page
  and category boundaries, transitive chain, canonical tie, permutation,
  empty input and malformed input;
- `python -m compileall`, focused pytest, `git diff --check` and exact
  allowed-path proof. No full local gate under R-135.

## Integration contract and rollback

`W56A-MERGE-01` later adapts grounded observations to these immutable inputs,
calls this pure function after the gate, and owns publication/queries. It may
extend the module sequentially after this task merges; it must not reassign
model identity or suppress an ungrounded diagnostic. Before use, revert this
new module; after use, apply a forward correction. No ref may be pushed by
this lane; hand SHA to a dedicated integrator slot.
