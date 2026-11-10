# ADR-0028: Executor hosts, system-managed groups, and per-stage models frozen at dispatch

- Status: accepted by the repository owner on 2026-11-09 (`R-153a`…`R-153f`; the plan was approved whole, `R-153c`). The product decisions are the owner's; the engineering choices below are the planner's inside them. They are revisable by a dated addendum. **Amended 2026-11-10 (`LIMITS-01`, `R-153n`…`R-153p`):** decisions 5, 9 and 12 no longer carry an answer limit or a stored timeout per cell, and the agent's silence window is 600 s; see the addendum at the end.
- Date: 2026-11-09
- Owners: repository owner / HOSTS integrator (the planning session)
- Amends: `ADR-0026` decisions 1, 2, 3, 5, 8, 9, 10, 12–15 and 17 for runs that carry a `stage_plan` (table below). Decision 16 is unchanged. Nothing in `ADR-0026` is removed: the connections, groups, rules and the cut-over keep serving everything that does not start from a `stage_plan` (the five `comparison_*` kinds until `HOSTS-CMP-01`, AR v3, the SSH connection «kzSonnet»).
- Related ADRs: `ADR-0024` (AI execution), `ADR-0025` (comparison spend), `ADR-0026` (capacity, enrollment, groups)
- Plan: `docs/program/dispatch/HOSTS-PLAN.md`

Every `HOSTS-*` task cites a decision of this ADR as «ADR-0028 decision n» instead of re-deciding it.

## Context

The owner's request of 2026-11-09 (`R-153a`) asks for four things at once:

1. a remote server (VPS) that is connected once and offers every AI agent installed on it, by subscription or by API, with availability recomputed continuously and the unavailable hidden from the UI;
2. a run started with one button, the servers being configured in «Исполнители», with a switch to use or not use a server;
3. **different models with concrete settings for the concrete stages of a section analysis, as in the original** (`/root/projects/PDF-proverka`, tables of `docs/claude_only_mode.md` and `docs/codex_only_mode.md`), and a modal window per stage;
4. a minimal UI: fewer concepts per screen is the priority for a while (`R-153f`).

The code on `origin/dev` `8f76b4ed6` (VERSION 0.20.0, contract 1.44.0, migration head `0061`) has the following:

- one connection serves one model (`pin_id`); one agent process serves one runner token and one connection (`ADR-0026` decision 3); `install.sh` demands a model and `tools/executor-runner/claude_answer.py:44` allows only `claude-opus-5` and `claude-sonnet-5`;
- a run has one binding per attempt (`src/auditmanager/runs/executor.py:1297`, `_bind_provider`); `binding.config.model_id` is read at more than 17 places (`runs/extended_review.py`, `analysis/text/stage.py:390`, `analysis/text/windowed.py:325`, `runs/preflight.py:206`);
- `CallBinding` carries one `expected_model` (`bootstrap/composition.py:932`); consent and estimate assume one model (`analysis/text/cost.py`, `runs/cost_policy.py`, `runs/preflight.py`);
- the pin set is closed (`analysis/text/lock.py:133`, `pinned_models`); `R-143g` forbade new pins;
- effort and limits are code constants (the limits are gone since 2026-11-10, `R-153n`; see the addendum): effort `high` (`analysis/extended/workflow.py:95`, `analysis/text/prompt.py:304`) and answer limits of 16000 tokens (`analysis/text/prompt.py:230`), 6000 (`analysis/extended/workflow.py:93`, `core.py:258`, `cross_window_review.py:120`) and 12000 (`analysis/extended/workflow.py:143`);
- waiting is allowed only for `binding_state = 'pending'` (`db/migrations/versions/20261102_0048_dispatch_time_binding.py:308`, `ck_audit_run_wait_pending`), and three lost attempts are a dead letter (`jobs/repository.py:1006`);
- the extended review that runs by default is v3. Its merge is deterministic (`runs/extended_review.py:1061`, `analysis.public.deterministic_extended_merge`), so «Свод» has no model.

## Decision

### Hosts and system-managed objects

1. **Host and host token.**
   - A host is `executor_host` (`exh_<ULID>`): one machine, one agent process, one **host token**.
   - The token, the enrollment grant and the install session each carry a CHECK «exactly one of `connection_id` / `host_id`». Tokens of legacy `pull` connections keep working.
   - The model is never asked at install. The agent reports which CLIs and keys it found and which models it verified (decision 16).
   - The host has an administrator-owned «Использовать» switch (a journalled event, not a column edit). A new host is on: the administrator who connected it made the mark (`R-149b`).
2. **System-managed pull connections.**
   - For every discovered quadruple host · provider · access (`subscription` or `api`) · model, the stand maintains a `pull` connection with `system_managed = true`: `pin_id` is that model; `billing` is `not_metered` for a subscription and `metered` for an API key.
   - A revision changes only when the catalogue (decision 13) changes. Slots live on the host, not in a revision.
   - Users never see these connections. `reviseExecutorConnection` and `archiveExecutorConnection` refuse them; the connection lists, the cut-over preview and the rule-target pickers filter them out.
3. **System groups.**
   - There is one group per (model, access). Its composition is every non-archived system connection of that pair, in a new revision only when a host is connected or deleted.
   - «Использовать», reachability and the model check decide **eligibility**, never composition. At most 16 hosts per pair (`executors/model.py` `GROUP_MEMBERS_MAX`).
   - `ExecutorGroupMemberIssue` (`api/schemas/models.py:5244`) gains `host_disabled`, `model_not_verified` and `model_cooling_down`, added by `HOSTS-SEAL-1`.

### Capacity

4. **Capacity unit and lock key.**
   - The unit is the pair (run, `capacity_pool`), where `capacity_pool` is host · provider. A run bound to a `stage_plan` holds one unit in each pool its cells use, from binding until the run ends; comparison calls count in the same pool.
   - Slots per provider and host: subscription 1, API 2; changed by the administrator in the host's details. A host token's `max_claimed_tasks` is at least the sum of its slots.
   - The advisory lock is taken on `capacity_pool` — not on `connection_id` — in all four places: the run claim, the dispatcher hint `_NEXT_JOB` (`jobs/repository.py:193`), the comparison call mirror (`comparison/spend/repository.py`) and the cell binding. The lock order of `ADR-0026` decision 14 is amended accordingly (decision 15 below).

### Binding

5. **Run binding source `stage_plan`; all cells bound at dispatch.**
   - A run started under the stage layout freezes `audit_run.stage_plan`: for every cell its model, effort and access. The run itself carries no group, connection or analysis preset. *(Amended 2026-11-10, `R-153n`/`R-153o`: the plan held an answer limit and a timeout per cell before; it holds neither now. A plan frozen before that is still read, and its two numbers are not.)*
   - A **cell** is «row · role»: `main`, `leg1`, `leg2` or `judge` (decision 11).
   - At dispatch, in the claim transaction, **every cell the run will call under its consent is bound at once**, each to a member of the system group of its (model, access). The result is written once to `audit_run_cell_binding (run_id, cell_key, group_revision_id, connection_revision_id)`; a trigger refuses any second write.
   - If any cell has no free eligible member the run stays in the existing `pending` state with the new wait reason `model_unavailable`, naming the cells and the cause, for example «Ждём Opus 5.5 — на серверах нет входа · с 14:02 до 14:32». After 30 minutes it ends with `no_executor_online` (`R-149c`). Nothing was executed, so nothing is lost. **No state is introduced in the middle of a run.**
   - Database: a new shape in `ck_audit_run_binding_shape`, `ck_audit_run_wait_pending` admitting such a `pending` run, branches in `_NEXT_JOB`, in the dispatcher hint and in `read_run_cost_policy`, and `trg_audit_run_frozen_guard` (function `am_guard_audit_run_frozen`) re-created once more.
   - `EnvironmentProviders` (`bootstrap/providers.py`) refuses a `stage_plan` run with a typed refusal; `DatabaseProviders` resolves it per cell. `ADR-0026` decision 16 holds: a member that fails in the middle of a run is handled as for any `bound` run, with no re-routing and no sending of `outcome_unknown` elsewhere.
   - **Distribution is per run, not per call.** A long run holds a subscription slot to its end. This is the price of having no mid-run waiting state (`D-499`).
6. **`binding_for(cell)`; the identity check stays mandatory.**
   - `binding_for(cell)` returns the member's adapter and one `CallBinding(expected_model)` **per call**. The single `CallBinding` of `composition.py:932` goes away for `stage_plan` runs.
   - `R-133` stays fail-closed: a call without a `CallBinding`, or whose reply names another model, is refused.
   - The three exact comparisons of the reported model — `runs/extended_review.py:142`, `executors/runner.py:606`, `analysis/text/stage.py:327` — move to `accepted_reported`, the exact list the catalogue (decision 13) names per model. No prefix match, no case folding; each has a test that fails on a model outside the list.
   - Semantic repair of a reply runs on the cell of the phase it repairs.
7. **Idempotency key.** The key of a model call is (source, phase, `request_sha256`, model). It contains neither the host nor the connection revision, so a retry served by another host after a move (`ADR-0026` decision 9) finds the saved reply instead of paying again. `stage_key` is written as a column of `model_call` and `provider_call_effect`, with `host_id` (not a foreign key) and `access`; older rows have none.
8. **Consent v2.**
   - `getRunStartReadiness` returns the estimate digest, the access per cell and the total. The consent stores the digest of the `stage_plan` and the map model → `rate_sha256` + access; `require_approved_model` checks membership. Older consents stay valid for runs without a `stage_plan`.
   - All cells by subscription: the estimate is 0 $ and pressing the button labelled «по подписке» is the consent (`{estimate_digest, ceiling_micros: 0, confirmed: true}`). At least one cell by API: one dialog with the estimate by model and the total. A batch is always one dialog (`R-151c`).
   - If access changed between the read and the start, the server refuses with the existing cost-preflight refusal, `reason: cost_estimate_binding_changed` (`ADR-0026` decision 18 addendum, still no new error code), and the UI re-reads readiness.
   - `ceiling_micros` is the human's choice; the process-wide `run_cost_ceiling_usd` is a separate notion.
9. **Pull liveness.** The cell's timeout travels in the task and bounds the response window by the watchdog's remainder minus a margin. The agent extends its claim only while the CLI produced output in the last 600 s, so a hung CLI is caught. The attempt ceiling of 7200 s is unchanged. *(Amended 2026-11-10: the window was 120 s, `R-153p`; 600 s is deliberately equal to the server's stall window of `jobs/lease.py`. The timeout that travels in the task is the constant of the cell's row or comparison kind, `R-153o`, no longer a number stored in the cell.)*

### Stage layout

10. **Model rows and code phases.** A row is what the owner sees; a phase is what the code runs. Every label comes from **one** phase dictionary for the whole application (today `web/src/widgets/extended-review/ui/batch-progress.tsx:13` says «Анализ изображений» where the row is «Анализ блоков»).

    | Row | Label | Code phases | Plan | Original key |
    |---|---|---|---|---|
    | `text` | Анализ текста | stage `text_analysis` (PC-01) | always | `text_analysis` |
    | `blocks` | Анализ блоков | `blocks:N`; with an ensemble `blocks:N:leg1`, `:leg2`, `:judge` | v2, v3 | `block_batch` |
    | `cross_check` | Комплексная сверка | `comprehensive_analysis` (windowed and cross-window), parameter passport | v2, v3 | none; valued by analogy with «Свод» |
    | `norms` | Нормы | `norm_verification:N` | v2, v3 | `norm_verify` / `norm_fix` |
    | `review` | Критик | `finding_review` | v3 | `findings_critic` (no model in the original) |
    | `correction` | Уточнение | `finding_correction` | v3 | `findings_corrector` (guard on absence) |

    Without a model: the three PC-01 preparation stages, the merge, the norm-citation check and the report. Their rail tiles show no model.
11. **Closed block schemes; ensemble identities.**
    - A block row is chosen from a **closed list of schemes**; the legs and the judge are not edited separately. A single Claude on blocks is not offered, even in a custom set (the original forbids it, `config.py:734-741`).
    - Cell identities are `blocks:N:leg1`, `blocks:N:leg2` and `blocks:N:judge` (parsing of `kind:bNNN` in `runs/extended_review.py:794-797` is widened). The call limit of the phase is the base batch count times the number of cells and enters the estimate and the consent.
    - A leg is retried 5 times at 30 s, as in the original, **only** for the classes `not_sent`, `rate_limited`, `proxy_unavailable` and `definite_refusal`. An `outcome_unknown` effect is never retried. A failed leg gives a partial block outcome in the artifact.
    - The judge's prompt is carried over from the original's `dual_review`. It changes `rules_sha256`, so a new consent is expected.
    - Delivered in wave 2 (`HOSTS-ENSEMBLE-01`). Until then the blocks row is a single model, and the Claude set is named «Только Claude (блоки без судьи)».
12. **Sets (presets), model · effort exactly.** The word «пресет» is taken by analysis presets, so the UI says «набор моделей».

    | Row | «Только Claude» | «Только Codex» |
    |---|---|---|
    | Анализ текста | Sonnet 5.5 · medium | gpt-6.1-sol · medium |
    | Анализ блоков | leg Opus 5.5 · medium + judge Sonnet 5.5 · medium, with search for omissions | legs gpt-6-astra · medium + gpt-6-sol · medium, judge gpt-6.1-sol · medium |
    | Комплексная сверка | Sonnet 5.5 · medium | gpt-6-sol · medium |
    | Нормы | Sonnet 5.5 · medium | gpt-6-astra · medium |
    | Критик | Sonnet 5.5 · medium | gpt-6-sol · medium |
    | Уточнение | Sonnet 5.5 · medium | gpt-6.1-sol · medium |

    - Before the ensemble, «Только Codex» runs blocks on one gpt-6-astra · medium (the original allows it); the Claude set is the single Opus 5.5 · medium. **Enabling the layout on production waits for the ensemble.**
    - «Свой набор» is any administrator edit. The default set is chosen by the administrator when the stand is switched; the initial value is «Только Claude», because the servers now serve Claude.
    - The user sees «модель · усилие». *(Amended 2026-11-10, `R-153n`/`R-153o`: the «Дополнительно» block with the answer tokens and the timeout is removed; answer tokens do not exist and the timeout is a code constant.)* Parallelism is not shown; calls are sequential.
13. **The catalogue file.**
    - `contracts/analysis/v1/model-catalogue.json`, with a `contract_version` and a schema beside it as its siblings have, describes **lock pins only**: provider, allowed efforts, access kinds and `accepted_reported`. Rates and identity stay in `docs/program/P02_LOCK.json`; a catalogue entry without a lock pin fails a test.
    - Efforts: Opus `medium`, `high`; Sonnet and Codex `low`, `medium`, `high`. Haiku, `xhigh`, `max` and Opus `low` are not offered (the original's owner forbids them).
    - The lock gains `claude-opus-5-5`, `claude-sonnet-5-5`, `gpt-6.1-sol` and `gpt-6-astra` in `HOSTS-PIN-01` (`R-153b`, lifting `R-143g` for this work). The Claude 5 pins stay for reading past runs.
14. **Layout storage, rules and the DB switch.**
    - The layout is stored as revisions `slr_<ULID>` with a journal naming the author. Only an administrator changes it (`R-149b`, default); an expert reads it; a viewer does not see it.
    - **All three start commands** — `startRun`, `reauditRun`, `startRunFromStage` — work from the `stage_plan` and consent v2 while the layout is enabled. «С этапа» takes today's `stage_plan`; only PC-01 stages without a model are reused. Explicit executor selectors answer `validation_failed`.
    - **The switch is a row in the database**, set by an administrator under «Расширенные», journalled, read only when a run starts, and valid only with `AUDITMANAGER_PROVIDER_SOURCE=database`. Runs already started are not affected by switching it off. After production is switched the switch is removed. While it is off, the one button follows the legacy automatic route.
15. **Lock order and what else changes.** The lock order of `ADR-0026` decision 14 becomes: worker intake → `capacity_pool` locks in ascending pool key → control → run → job. Cell binding happens in the claim transaction; model I/O starts after commit, as before.

### Agent, keys and availability

16. **Availability.**
    - A model on a host is available when the host is enabled, its heartbeat is at most 120 s old, a login is present, the model is verified, and the pair is not under a passive cooldown. «Занято» means available with every slot taken.
    - Reasons for unavailability are stored and journalled. **Lists do not show them**; they are visible in a run's waiting line and in a disabled button (`R-149n`), and to the administrator in the host's details.
    - The state is computed on read from stored facts: the report snapshot (written only on change), append-only change events, the cooldowns (`executor_model_cooldown`) and the switch.
    - The agent recomputes every 60 s (CLI, version, login — no model call) and makes a minimal call per model on change and every 6 h. After a real refusal (access, quota, «no model») the pair is off availability for 15 minutes. The web polls every 10 s while the screen is open.
17. **Direct-API key file on the VPS (`R-153d`).**
    - The agent also reads a key file of its service: mode 0600, owned by the service user, holding `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` and `OPENROUTER_API_KEY`. The agent package gains API responders for the three providers (`HOSTS-AGENT-01`). Models so served are access `api`, `metered`.
    - **Keys never reach the stand, a database, a log or the environment of a child CLI**; an allowlist test proves the last. Discovery uses only explicit sources: `claude --version` and `claude auth status`, `codex login status`, and this file.
    - This is a new path by which a document's text leaves the stand to a third party. It is the credential-reach decision `R-29` item 2 requires from the owner, recorded as `R-153d`, and it falls under `R-143c` and `D-291`: the warning «не для клиентских документов» stays on the servers screen, in the connect window and as a short mark on the start line while `D-291` is open. A subscription path remains the default (`R-149b`).

### Departures from the original and the first cut

18. **Explicit departures from the original PDF-proverka.**
    - The original sends a *capability* and each worker maps it by its local policy. Here the agent receives the exact `model_id` and `effort` from the catalogue; the stand decides, the host only executes.
    - The original distributes work per call; here distribution is per run (decision 5).
    - The original has no «Комплексная сверка» row; it is valued by analogy with its «Свод».
19. **Out of scope of this ADR.** The five `comparison_*` kinds stay on legacy routing until `HOSTS-CMP-01` (`D-541`), AR v3 keeps its own path, and optimisation calls no model. `--upgrade` of a pull agent whose connection is used by rules or comparisons is refused until `HOSTS-CMP-01`. The SSH connection «kzSonnet» on production is untouched; during the transition it shares the `adm1.hlab.kz` Claude subscription outside the capacity pool (`D-540`). There is no reserve set when a quota runs out (`R-153e`, `D-498`).

## What ADR-0028 changes in ADR-0026

| `ADR-0026` decision | Change here |
|---|---|
| 1. One capacity unit | The unit is (run, `capacity_pool`); a bound run holds one unit per pool of its cells until it ends (decision 4) |
| 2. Coupled limits | For a host token `max_claimed_tasks` ≥ the sum of its slots |
| 3. Per-token claims, one process per token | One process per host |
| 5. Agent health on the token | Health on the host token is the source of availability (decision 16) |
| 8. Four CLI statuses | The integration mark is set by the host's «Использовать» |
| 9. Moving an agent | A move is a new enrollment for the host |
| 10. Immutable homogeneous group revision | System groups per (model, access), created and revised by the stand (decision 3) |
| 12. Binding state | Source `stage_plan`; `pending` → `bound` for all cells at once (decision 5) |
| 13. Admission freezes intent | The frozen intent is the `stage_plan` and consent v2 (decisions 5, 8) |
| 14. Dispatch in the claim transaction | The lock is per `capacity_pool`; the order changes (decisions 4, 15) |
| 15. Durable waiting | New wait reason `model_unavailable` listing cells, in the existing `pending` state |
| 16. No re-routing after binding | **Unchanged** |
| 17. Cut-over | Mode `rules` / `legacy` does not touch runs from a `stage_plan` |

## Consequences

- Default behaviour is unchanged while the layout switch is off: capacity, groups and rules of `ADR-0026` serve as before, and a run uses the legacy route.
- The pin set grows by four, and every closed-set test of pins moves (`HOSTS-PIN-01`).
- About 17 sites read `binding.config.model_id`, and three compare the reported model by string; each must be driven by the cell (`HOSTS-LAYOUT-01`).
- The agent becomes a host agent: model-free install, discovery, API responders and a key file. The agent package and `PACKAGE_FILES` change.
- The stand gains a layout store, host and cooldown tables and a write-once cell binding table; the migration, the contract and the hand-kept inventories move in one slot (`HOSTS-SEAL-1`).
- Without database runs in the lanes, races in cell binding and the pool lock are first exercised on a throwaway database with the slot holder's consent (plan, checks).

## Addendum 2026-11-10: no answer cap, timeouts as code constants, a 600 s silence window (`LIMITS-01`)

The owner decided three things by direct poll on 2026-11-10 (`R-153n`, `R-153o`, `R-153p`, `docs/program/OWNER_RULINGS_2026-09-17.md` section 3.53). The first restores his instruction of 2026-11-06 (`docs/program/HOTFIX-RUN-PARTIAL-1106.md`: «remove response-size limits and UI mentions»), which this ADR had reverted by naming the limits «constants of the code» and putting them into «Дополнительно».

- **No answer cap reaches any model (`R-153n`).** A layout cell carries a model and an effort, and nothing about the length of an answer: not in the layout write request, not in the layout and stage reads, not in the frozen plan, not in `payload.host`. The Claude Code command runs without `CLAUDE_CODE_MAX_OUTPUT_TOKENS`, and the agent removes it from the child's environment if it inherited one; Codex has no cap; OpenAI Responses and OpenRouter get no output-token parameter; Anthropic Messages requires `max_tokens` and gets the model's maximum (128000, the output maximum of every Claude model in the catalogue). A `max_tokens` figure in a server request body is the number the cost estimate prices the call at, never a cap: `analysis/text/cell_settings.py` names it `ROW_ESTIMATE_OUTPUT_TOKENS`, and the comparison calls are priced at their module's own figure. The availability probe keeps its own 4096-token ceiling on an API call (it is not an analysis answer).
- **Timeouts are code constants (`R-153o`).** The call window of a cell is the constant of its row, from the original (`PDF-proverka/backend/app/core/config.py`): text 1800 s, blocks 1800 s (a leg and the judge take the row's value), cross-check 3600 s (the original raised it after the merge was killed twice at 1801 s with its work lost), norms 600 s, critic 600 s, refinement 600 s; the four comparison kinds keep the original's 900, 1800, 900 and 2400 s. A number stored in an older layout revision or a frozen plan is not read. Each window is still cut to what the attempt watchdog leaves (`executors/pull.py` `answer_window`); the 7200 s hard cap of an attempt is unchanged.
- **The agent's silence window is 600 s (`R-153p`).** It was 120 s. It equals the server's stall window (`ATTEMPT_STALL_SECONDS`) on purpose: Codex prints its events when an item completes, so a long silent reasoning must not be stopped by the agent while the stand would still wait.
- **Compatibility.** Contract `1.49.0` removes `max_output_tokens` and `timeout_seconds` from the layout cell, the comparison cell and the stage cell, and `max_output_tokens` from `payload.host` (`timeout_seconds` stays, from the row constant). The database needs nothing (migration `0062` checks only the key and the model of a cell). The new agent reads an older stand's task and ignores its cap, so it can be installed first.
- **Consequence of the 600 s windows for the short rows.** Norms, critic and refinement calls, which the original ran one per step, are here calls over a window of work; 600 s is the original's figure and is not a promise that a large window fits.

## Alternatives considered

- **Per-call routing (choose a server for each call).** Rejected: waiting at a stage boundary needs a new mid-run state, but waiting is allowed only in `pending` before start (`0048:308`), and three lost attempts are a dead letter (`jobs/repository.py:1006`), so a run could lose work already paid for. Binding all cells at dispatch needs no new state.
- **An environment flag for the stage layout.** Rejected: it needs a restart, leaves no journal, and the administrator who must flip it cannot see it. A database row is journalled and read at run start.
- **Mixed-billing groups.** Still not approved (`ADR-0026` decision 10); a (model, access) pair keeps billing and rates identical.
- **Merging «Комплексная сверка» into another row.** Rejected: its calls are separate phases with their own limits.
- **A reserve set when a quota runs out.** Not needed for now (`R-153e`); recorded as `D-498`.
- **Models from the catalogue without a lock pin.** Rejected: price and identity have one owner, the lock.

## Verification

Checks are proportional (`AGENTS.md` §8, `docs/program/dispatch/HOSTS-PLAN.md`): focused unit and contract tests per task, one narrow throwaway-database run for the migration, the host-token claim and the cell binding, and a read-only review of the claim, binding and consent diff at each integration. A live check on `adm1.hlab.kz` is an owner act. Every guard added has a test that can fail.

## Revisit trigger

Any of these reopens this ADR:

- the first use with real client documents (`D-291`, decision 17);
- parallel model calls inside one run (decision 4);
- distribution per call, or a mid-run waiting state (decision 5);
- a catalogue model that is not a lock pin (decision 13);
- mixed-billing groups (`ADR-0026` decision 10).
