# Task CODE-FIRST-SCOPE-01 — разложить W58–W63 на кодовые срезы

## Outcome

На `origin/dev` есть проверяемая карта будущих кодовых срезов W58–W63:
результат, граница владения, вход и адресная проверка каждого среза. Карта
не выдаёт права менять код до freeze от актуального dev-кандидата.

## Depends on

- `CODE-FIRST-INT-01` — завершена на `d600fe69`;
- `W56A-DEV-FREEZE-01` — завершена на `88c83b22`.

## Frozen inputs

- base commit: `88c83b224f415f58ba16359f45d7b4fec08c887c` (`origin/dev`);
- domain contract: candidate revision 12;
- API contract SHA-256: `8e1d0b23d2b3715934436a1b5dfc13172f57938df0accfa5b44fe06e2a4bd482`;
- analysis stage registry SHA-256: `845b8f6dbba6b8220aaeee78e5780ed6aa432b3171432e91e8962f40a4e054e5`;
- migration head: `0021_portal_bundles`;
- scope sources: `dispatch/CODE-FIRST-TO-BETA.md` §§1–4,
  `dispatch/ROADMAP-TO-BETA.md` §§4, 9, 10 and R-135/R-136.

Future implementation freezes remeasure all pins after predecessor merges.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W58–W63 remain draft implementation lanes, while the code-first
  plan adopts their functional scope and requires later per-block freezes

### P-01 — planning status and order

- captured_at: 2026-10-15
- command: `rg -n 'Unadopted \(2026-10-08|^\| \*\*W5[89]|^\| \*\*W6[0-3]|^## 2\. Остаток кода' docs/program/dispatch/ROADMAP-TO-BETA.md docs/program/dispatch/CODE-FIRST-TO-BETA.md`
- captured_output:
  ```text
  docs/program/dispatch/CODE-FIRST-TO-BETA.md:67:## 2. Остаток кода и порядок
  docs/program/dispatch/ROADMAP-TO-BETA.md:109:| **W58** | debts of W53–W57; real АР rehearsal with named experts; exposure review; backup/restore drill; candidate contract audit | — | M | development close; no beta claim (*unadopted, K-4*) |
  docs/program/dispatch/ROADMAP-TO-BETA.md:110:| **W59** | S0 framework: 15 sections, stage attribute П/Р, section suggestion + confirmation, run routed by confirmed section, profile registry from legacy (§10.3); **АИ, ПЗ, ПОС, ТХ** | comparison-1: versions of one set, finding matching, decision carryover with confirmation (§10.4) | L+ | development close |
  docs/program/dispatch/ROADMAP-TO-BETA.md:111:| **W60** | **КЖ, КМ, ОВ, ВК, ПТ** | **Оптимизация проекта** on АР (§10.1) | L+ | development close |
  docs/program/dispatch/ROADMAP-TO-BETA.md:112:| **W61** | debts + expert validation of W59–W60 | — | M | — |
  docs/program/dispatch/ROADMAP-TO-BETA.md:113:| **W62** | **ЭОМ, СС, ИТП, ГП, ПБ** | comparison-2: stages П/Р; **Диспетчер** (§10.5) | L+ | development close |
  docs/program/dispatch/ROADMAP-TO-BETA.md:114:| **W63** | **Оптимизация разделов** + Оптимизация проекта for the remaining sections; repeat B1–B12 on the complete menu/full-АР candidate | — | L+ (remeasure) | earliest `v1.0.0-beta.1` (*unadopted, K-4*) |
  docs/program/dispatch/ROADMAP-TO-BETA.md:350:*Unadopted (2026-10-08 layer, §10.16 K-4): the W58–W64 route and the beta move to W63 below are preserved, not reviewed or adopted.*
  ```
- interpretation: future slices may be specified now, but implementation
  paths and predecessor task IDs cannot yet be frozen.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

The older roadmap remains historical context; this task adds a forward map.

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/CODE-FIRST-SCOPE-01.md`;
- `docs/program/dispatch/CODE-FIRST-SCOPE-W58-W63.md`;
- `docs/program/dispatch/CODE-FIRST-TO-BETA.md` — one pointer.

## Forbidden hotspots

- `contracts/**`, migrations, root dependencies/locks, composition roots,
  global styles, runtime/UI/test code, `P02_LOCK.json`;
- `CURRENT_STATE.md`, owner rulings, debt register, `VERSION`, release notes;
- `origin/main`, tags, deployed stand and credentials.

## Non-goals

- no W58–W63 code grant, contract/migration seal or invented dependency close;
- no full local gate, live acceptance, beta verdict or main push;
- no change to B1–B12 or model-identity refusal.

## Deliverables

- scope map with per-slice exit evidence and freeze triggers;
- pointer from the adopted code-first plan.

## Required tests

- `git diff --check` and exact allowed-path proof;
- focused prose/governance tests for these documentation changes;
- remote `origin/dev` read-back before and after a normal fast-forward push.

## Integration contract

Each map row becomes an implementation task only after its predecessor code
is merged, current contracts and migration head are rechecked, exact
`allowed_paths` are granted, and shared hotspots have one owner. Row names
are candidate lanes, not dispatched task IDs. Focused checks apply during
development; the complete gate is after all code.

## Failure/idempotency/security cases

- A moved dev ref or changed frozen input requires refresh before publication.
- A future path overlap stops dispatch until ownership is split.
- No customer data or provider response is copied into this map.

## Rollback / feature flag

Documentation only; revert these three files by a forward commit on dev.
No runtime flag or data rollback.

## Handoff

- changed files: the three Allowed paths;
- checks/results: recorded in the integration response;
- known limits: future grants depend on completed predecessor code;
- next: start W56a SEAL/GENERATOR; issue later tasks from the current dev tree.
