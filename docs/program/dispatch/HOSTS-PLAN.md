# HOSTS — executor hosts, per-stage models, one-button run, run screen: wave plan

- Date: 2026-11-09
- Integrator: the planning session, after the owner's approval (`R-153c`). Executors never merge or push.
- Architecture: `docs/architecture/adr/ADR-0028-hosts-and-stage-models.md`. Tasks cite «ADR-0028 decision n». It amends `ADR-0026` (table in the ADR).
- Owner inputs: `R-153a`…`R-153f` (`OWNER_RULINGS_2026-09-17.md` §3.53). Debts: `D-498`, `D-499`, `D-540`, `D-541`; `D-291` (client documents) still applies.
- Base: `origin/dev` `8f76b4ed6daadad95f9c001e2c2c0dca717aad2d` — VERSION 0.20.0, API contract 1.44.0 with 280 paths / 308 operations / 744 schemas, migration head `0061_decision_memory_m2`.
- The original application: `/root/projects/PDF-proverka` at `dd974b2b`. Its sets are in `docs/claude_only_mode.md` and `docs/codex_only_mode.md`.
- The owner-facing Russian plan is a local file (`.local/reports/executors-runs-rework-plan-2026-11-09.md`) and is not part of the repository; this file and the ADR hold what the tasks need.

## 1. Owner inputs

### 1.1. Rulings

| Ruling | Substance |
|---|---|
| `R-153a` | The request: connect a VPS once and offer all its agents by subscription and API; recompute availability and hide the unavailable; rework the agent, keep install by terminal and by SSH, compact UI; a use / do-not-use switch per server; one-button run; minimal run screen with tabs and infographics, after the original; **different models with concrete settings for the stages of a section analysis**; a modal per stage |
| `R-153b` | Four new pins — `claude-opus-5-5`, `claude-sonnet-5-5`, `gpt-6.1-sol`, `gpt-6-astra` — «Да, все четыре»; lifts `R-143g` for this work |
| `R-153c` | The plan is approved whole: waves 0–3 to `origin/dev`; `origin/main` only on a separate instruction |
| `R-153d` | Direct API from the VPS: a key file on the VPS («Плюс файл ключей на VPS») — the `R-29` item 2 decision |
| `R-153e` | No reserve set when a quota runs out |
| `R-153f` | UI minimisation is the priority for a while |

### 1.2. Decided by the plan without a poll

1. Only an administrator changes the stage layout; an expert reads it; a viewer does not see it (`R-149b` default).
2. «Использовать» is per server; a new server is on, because the administrator who connected it made the mark.
3. The default set is chosen at the stand switch; the initial value is «Только Claude».
4. The ensemble on blocks is wave 2, and the layout is enabled on production only after it.
5. The stage layout is enabled by a database switch, not an environment flag (`ADR-0028` decision 14).

### 1.3. Slots

The UI-parity programme held the API contract and the migration head under `R-151w`. **Dated input, 2026-11-09 at about 15:00 (not a ruling):** the session pdf-analysis-f9, the UI-parity window-3 integrator, released the contract and migration slot to the HOSTS integrator session (pdf-analysis-d6). Contract `1.45.0` and migration `0062` (then `1.46.0` and `1.47.0`) are therefore this work's; each is still re-read against the tree before its task is dispatched. The overlap with the UI-parity programme (the run screen, the «Обзор» of «Исполнители») is agreed with its current integrator before wave 1.

## 2. Reconciliation with the code (read on `8f76b4ed6`)

| Claim | Code | Plan consequence |
|---|---|---|
| One connection, one model; one process per token | `ADR-0026` decision 3; `tools/executor-runner/claude_answer.py:44` allows two models; `install.sh` demands a model | Host entity and host token; model-free install (`ADR-0028` decisions 1, 2) |
| One binding per attempt | `src/auditmanager/runs/executor.py:1297` `_bind_provider`; `binding.config.model_id` read at more than 17 sites | `stage_plan` source, `binding_for(cell)` (decisions 5, 6) |
| One `CallBinding` | `src/auditmanager/bootstrap/composition.py:932` | One per call (decision 6) |
| The reported model is compared as a string in three places | `runs/extended_review.py:142`, `executors/runner.py:606`, `analysis/text/stage.py:327` | `accepted_reported` per catalogue |
| The pin set is closed | `analysis/text/lock.py:133` `pinned_models`; `tests/unit/executors/test_model.py:44`; `tests/integration/analysis/test_provider_lock_refusals.py` | `HOSTS-PIN-01` moves the lock and both tests |
| Waiting only before start | `db/migrations/versions/20261102_0048_dispatch_time_binding.py:308`; dead letter at `jobs/repository.py:1006` | All cells bound at dispatch; wait reason `model_unavailable` in `pending` |
| Effort and limits are constants | effort `high` at `analysis/extended/workflow.py:95` and `analysis/text/prompt.py:304`; 16000 at `analysis/text/prompt.py:230`; 6000 at `workflow.py:93`, `core.py:258`, `cross_window_review.py:120`; 12000 at `workflow.py:143` | Per-cell settings in the `stage_plan` |
| «Свод» has no model | `deterministic_extended_merge` called at `runs/extended_review.py:1061` | Six rows, «Свод» a tile without a model |
| `ExecutorGroupMemberIssue` has six reasons | `api/schemas/models.py:5244` | Three added in `HOSTS-SEAL-1` |
| The phase labels disagree | `web/src/widgets/extended-review/ui/batch-progress.tsx:13` says «Анализ изображений» | One phase dictionary (`RUN-SCREEN-01`) |
| The build id is a content hash | `src/auditmanager/releases/build_id.py:21` hashes `P02_LOCK.json`; no tree file stores its value | Nothing is recomputed: it is a content hash computed at start, with no stored value to move |

## 3. Waves and tasks

Task files are `docs/program/tasks/HOSTS-*.md`. The six of waves 0–1 are written with this plan; the integrator writes the task files of waves 2 and 3 from the tree after the previous integration, with premises re-captured. Estimates are executor hours, **extrapolated** from the `EXEC2-PLAN.md` table by size, not measured.

### Wave 0 — decisions, pins, contract

| Task | Outcome | Depends on | Estimate |
|---|---|---|---|
| `HOSTS-ADR-01` | `ADR-0028`, `R-153a`…`R-153f`, this plan, the six task files, debts `D-498`, `D-499`, `D-540`, `D-541` | owner answers (`R-153*`) | 2 h |
| `HOSTS-PIN-01` | The four pins in `docs/program/P02_LOCK.json` with rates from the providers' price lists; closed-set tests moved | `HOSTS-ADR-01` | 1 h |
| `HOSTS-SEAL-1` | Contract 1.45.0, migration 0062, models and client, pins, inventories, stub modules; the catalogue file | `HOSTS-ADR-01`, `HOSTS-PIN-01` | 5 h |

### Wave 1 — four lanes

| Task | Outcome | Depends on | Estimate |
|---|---|---|---|
| `HOSTS-AGENT-01` | Host mode, model-free install, discovery, catalogue, recompute, passive cooldown, responders including the API key file, `PACKAGE_FILES` (`tools/executor-runner/**`) | `HOSTS-SEAL-1` | 6 h |
| `HOSTS-BACKEND-01` | Host, host token, system connections and groups, availability, «Использовать», slots, cooldowns, `capacity_pool`, lock, cell binding at dispatch, wait `model_unavailable`, pull liveness (`executors/**`, `jobs/**`, `bootstrap/hosts_*`) | `HOSTS-SEAL-1` | 10 h |
| `HOSTS-LAYOUT-01` | Layout store and sets, catalogue, `stage_plan` freezing, `binding_for(cell)`, per-call `CallBinding`, idempotency key, consent v2 in three commands, readiness, per-cell settings at every hard-coded value, `accepted_reported` (`runs/**`, `analysis/text/**`, `analysis/extended/**`, `bootstrap/stage_plan_*`) | `HOSTS-SEAL-1` | 12 h |
| `HOSTS-WEB-01` | «Серверы», «Подключить сервер», «Модели по этапам», «Расширенные ▸», analysis presets moved there | `HOSTS-SEAL-1` | 7 h |
| `HOSTS-INT-1` | Merge in the order BACKEND, LAYOUT, AGENT, WEB; hotspot wiring; read-only seam review (claim, binding, consent); release note 0.21.0 and `VERSION` with pins (`AGENTS.md` §6.1); `CURRENT_STATE`; `origin/dev` | wave 1 | 3 h |

### Wave 2 — run screen, one button, ensemble

| Task | Outcome | Depends on | Estimate |
|---|---|---|---|
| `HOSTS-SEAL-2` | Contract 1.46.0: `getRunStages`, ensemble cell identities | `HOSTS-INT-1` | 2 h |
| `RUN-STAGES-01` | `getRunStages` in `runs/stage_facts.py`; system connections shown in the journal as «adm1.hlab.kz · Claude · подписка» | `HOSTS-SEAL-2` | 4 h |
| `RUN-START-ONE-01` | One button, readiness line, API dialog, «▾», `reaudit-run`, `start-run-from-stage` | `HOSTS-INT-1` | 4 h |
| `RUN-SCREEN-01` | Header, rail of 8 tiles, two tabs, the stages window, the transition table, one phase dictionary | `HOSTS-SEAL-2` | 6 h |
| `HOSTS-ENSEMBLE-01` | Closed block schemes, `blocks:N:leg1/leg2/judge`, retries, partial outcome, the judge prompt (`runs/extended_review.py` blocks region only, after `HOSTS-LAYOUT-01` is merged; `analysis/extended/**`) | `HOSTS-SEAL-2` | 6 h |
| `HOSTS-INT-2` | Merge, release note 0.21.x, `origin/dev` | wave 2 | 3 h |

### Wave 3 — comparisons and the cut-over

| Task | Outcome | Depends on | Estimate |
|---|---|---|---|
| `HOSTS-SEAL-3` | Contract 1.47.0: comparison rows in the layout | `HOSTS-INT-2` | 2 h |
| `HOSTS-CMP-01` | The five `comparison_*` kinds through the system groups and comparison rows; closes `D-541` | `HOSTS-SEAL-3` | 6 h |
| `HOSTS-CUTOVER-01` | Operator guide: host agent on `adm1.hlab.kz`, the set, the switch, «kzSonnet» archived; closes `D-540` | `HOSTS-CMP-01` | 3 h |
| `HOSTS-INT-3` | Merge, `origin/dev` | wave 3 | 3 h |

## 4. Hotspot ownership

| Hotspot | Wave 0 | Wave 1 | Wave 2 | Wave 3 |
|---|---|---|---|---|
| `contracts/**`, generated models and client, version and path-count pins | `HOSTS-SEAL-1` | frozen | `HOSTS-SEAL-2` | `HOSTS-SEAL-3` |
| Migration head | `HOSTS-SEAL-1` (0062) | frozen | none planned | `HOSTS-SEAL-3` only if needed |
| `api/security.py`, `api/app.py`, `api/routers/__init__.py` | `HOSTS-SEAL-1` | integrator | `HOSTS-SEAL-2` | `HOSTS-SEAL-3` |
| `src/auditmanager/bootstrap/providers.py`, `composition.py`, `adapters.py`, `api/routers/ports.py` | **integrator** (stubs only, wired at merge) | **integrator** | **integrator** | **integrator** |
| `src/auditmanager/jobs/repository.py` | `HOSTS-SEAL-1`: the `prepare_provider_call` signature and the two call-journal INSERTs only | `HOSTS-BACKEND-01` wholly, from the merge of SEAL-1 | — | `HOSTS-CMP-01` |
| `src/auditmanager/runs/extended_review.py` | — | `HOSTS-LAYOUT-01` | `HOSTS-ENSEMBLE-01` (blocks region, after the merge of LAYOUT) | — |
| `tools/executor-runner/**` | — | `HOSTS-AGENT-01` | — | — |
| `web/src/shared/config/screen-registry.ts` | — | `HOSTS-WEB-01` (rows for the new route only) | `RUN-SCREEN-01` | — |
| `src/auditmanager/shared/errors/**`, root dependency/lock files, global styles | untouched | untouched | untouched | untouched |

Lanes write their code into the stub modules `HOSTS-SEAL-1` creates under exact names: `bootstrap/hosts_adapter.py`, `bootstrap/hosts_dispatch.py`, `bootstrap/stage_plan_adapter.py`, `bootstrap/stage_plan_providers.py` and `runs/stage_facts.py`. The new port Protocols are declared in a new `api/routers/hosts_ports.py`, so `ports.py` stays untouched until the merge. **The integrator wires `ports.py`, `adapters.py`, `composition.py` and `bootstrap/providers.py` at merge time:** the port re-exports, the adapter wrappers of `ExecutorEnrollmentAdapter` and `ExecutorGroupAdapter` and the runner authentication for a host token, the `executor_hosts=` and `stage_layout=` adapters, the `stage_plan` branch of `DatabaseProviders` with the typed refusal in `EnvironmentProviders`, the call site of the single `CallBinding` at `composition.py:932`, and the swap of the reported-model comparison at `executors/runner.py:606` to `accepted_reported` (the function `HOSTS-LAYOUT-01` exports; the file is `HOSTS-BACKEND-01`'s).

## 5. Dispatch rules

1. Lanes run on Sonnet; data gathering on Haiku. At most four lanes at once; they report a five-minute heartbeat; none runs git — the integrator commits exactly the allowed paths.
2. **Push before dispatching dependents.** Wave 1 is dispatched from the `HOSTS-SEAL-1` tip once merged; wave 2 from the `HOSTS-INT-1` tip once it is on `origin/dev`.
3. The integrator re-runs every premise command of a task on the actual base before dispatch and corrects line numbers; a premise that no longer holds stops the dispatch. Allowed paths are listed from the tree, never from memory.
4. A process is stopped only by its own confirmed PID, never by a name pattern. The host is shared (`docs/program/dispatch/OPERATING_CONSTRAINTS.md`); one heavy run at a time, with the consent of the run-slot holder (`R-149h`).
5. No full `make gate`. Checks are focused (section 6).

## 6. Checks (`AGENTS.md` §8)

| Change | Checks |
|---|---|
| Contract and migration | upgrade → downgrade → upgrade; downgrade refused while rows exist; each trigger (frozen `stage_plan`, write-once cell binding) has a test that fails without it; `tests/contract/**`; the role register; grants and the schema inventory |
| Backend | availability for each reason; member choice and the pool lock (two calls cannot take one subscription slot); a run waits when one cell has no member and spends no attempt; `R-133` (another model refused; no `CallBinding` refused; `accepted_reported` exact); a retry served by another host finds the saved reply; consent v2 (another model and a changed access refused); `EnvironmentProviders` refuses a `stage_plan` run; system objects cannot be edited |
| One narrow database run | a single throwaway PostgreSQL, with the slot holder's consent: the migration, a claim with a host token, cell binding |
| Agent | fake CLIs; a report only on change; keys never reach child CLI environments; the claim extended only while the CLI outputs; `PACKAGE_FILES` |
| Web | vitest of the touched widgets, lint and typecheck, the style census |
| Live (owner) | the agent on `adm1.hlab.kz`; the layout on a test stand; a section run by «Только Claude (блоки без судьи)»; repeated after the ensemble |

## 7. Risks and limits

| # | Risk | Measure |
|---|---|---|
| H1 | Subscriptions are used only through the official CLIs under the owner's login (`R-149b`) | Probe calls are rare (every 6 h per model); no credential copying |
| H2 | Distribution per run holds a subscription slot to the end of a long run | Accepted; `D-499`; no new mid-run state |
| H3 | A direct-API key file is a new outward path of a document's text | `R-153d`; keys never leave the VPS file; `D-291` warning shown; the subscription path is the default |
| H4 | «kzSonnet» shares the `adm1.hlab.kz` subscription outside the pool during the transition | `D-540`; `--upgrade` refused for such an agent until `HOSTS-CMP-01`; archived by `HOSTS-CUTOVER-01` |
| H5 | The comparison kinds stay on legacy routing until wave 3 | `D-541` |
| H6 | No reserve set when a quota ends | `R-153e`; `D-498`; the run waits 30 minutes then «Запустить снова» |
| H7 | A new pin or model with wrong rates changes every estimate | `HOSTS-PIN-01` cites the price page and the date in the lock's `$comment`; the estimate tests move with it |
| H8 | A missed literal pin turns a guard red after the reseal (about 20 were missed in EXEC-2) | `HOSTS-SEAL-1` lists 83 test files and the prose files from a tree census |
| H9 | Races in cell binding and the pool lock go unseen without a database | One narrow throwaway-database run; integration review of the claim diff |
| H10 | UI overlap with the UI-parity programme | Agreed with its integrator before wave 1; the `screen-registry.ts` rows are disjoint |
| — | Outside this work | AR v3 keeps its own path; optimisation calls no model |

## 8. Estimate

- Scope: about 20 tasks, 1.5 to 2 times `EXEC-2`; `HOSTS-LAYOUT-01` is about twice `EXEC2-GROUP-RUN-01`. The per-task figures above sum to roughly 90 executor hours; they are extrapolated.
- **Measured anchor:** `EXEC-2` was planned at P50 four days and took about 22 hours from the first wave to `dev` (`origin/dev` `27fb952e` on 2026-11-02 17:35 to `51183a75` on 2026-11-03 15:20), without a stand check.
- Waves 0–2: 2 to 3 days to `origin/dev`. Wave 3: about one more day. Range 3 to 6 days.
- Not included: the live check, stand checks and the owner's acts on production.

## 9. Concepts a screen shows, before and after (`R-153f`)

| Screen | Now | After |
|---|---|---|
| «Исполнители»: tabs | 6 | 2, plus a quiet link «Расширенные ▸» for an administrator |
| «Исполнители»: concepts | about 17 | 4: server, «Использовать», models, load |
| Menu «⋮» of a server | — | 2 items: «Подробнее», «Удалить» |
| «Модели по этапам»: controls for an expert | — | 0 (read only) |
| Run start: controls before the button | 5–7 | one button (plus «▾») |
| Run screen: tabs | none, one column of about 14 blocks | 2 |
| Run screen: summary tiles | 4 totals and 2 columns | 2 |
| Places that show stage state | 5 | 2: the rail and the window |

## 10. Owner acts

1. Agree the contract and migration slot with its holder before `HOSTS-SEAL-1` (the integrator does this; the owner only rules on a conflict).
2. Optional: provide the key file contents on the VPS if a direct-API path is wanted (`R-153d`); without it the agent serves the subscriptions only.
3. After wave 1: install the host agent on `adm1.hlab.kz` and confirm the discovered models on the stand.
4. After wave 2: enable the stage layout on the test stand and run a section by «Только Claude (блоки без судьи)»; repeat after the ensemble.
5. Production: enable the layout only after the ensemble; `origin/main` only on a separate instruction (`R-153c`).
