# ADR-0028: Executor hosts, system-managed groups, and per-stage models frozen at dispatch

- Status: accepted
- Date: 2026-11-09; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: owner rulings `R-153a`…`R-153f` of 2026-11-09 (the plan was approved whole, `R-153c`); `R-149b`, `R-149c`, `R-149n`, `R-151c`, `R-143c`, `R-143g`, `R-133`, `R-29` as cited in the decisions; amendments `R-154b` (plan v3 is opt-in, default `v2`), `LIMITS-01` (`R-153n`…`R-153p`) and `R-155c`/`R-155h` (decision 9). Plan: `docs/program/dispatch/HOSTS-PLAN.md`. The product decisions are the owner's, the engineering choices inside them the planner's. Revisable by a dated addendum.
- Amends: `ADR-0026` decisions 1, 2, 3, 5, 8, 9, 10, 12–15 and 17 for runs that carry a `stage_plan` (table «What ADR-0028 changes in ADR-0026»); decision 16 is unchanged. `ADR-0026` keeps serving everything that does not start from a `stage_plan` (the comparison kinds while the layout is off, the SSH connection «kzSonnet»).
- Related: `ADR-0024`, `ADR-0025`, `ADR-0026`. Owner: repository owner / HOSTS integrator.

Every `HOSTS-*` task cites a decision of this ADR as «ADR-0028 decision n» instead of re-deciding it.

## Context

The owner's request of 2026-11-09 (`R-153a`) asks for four things at once:

1. a remote server (VPS) connected once that offers every AI agent installed on it, by subscription or by API, with availability recomputed continuously, the unavailable hidden from the UI;
2. a run started with one button, the servers configured in «Исполнители», with a switch to use or not use a server;
3. **different models with concrete settings for the concrete stages of a section analysis, as in the original** (`/root/projects/PDF-proverka`), and a modal window per stage;
4. a minimal UI: fewer concepts per screen is the priority for a while (`R-153f`).

The base had one connection per model (`pin_id`) and one agent process per runner token, one binding per attempt, a closed pin set (`R-143g`), waiting allowed only in `pending` (migration `0048`) and a deterministic merge, so «Свод» has no model. Reconciliation: `docs/program/dispatch/HOSTS-PLAN.md` section 2.

## Decision

### Hosts and system-managed objects

1. **Host and host token.** A host is `executor_host` (`exh_<ULID>`): one machine, one agent process, one **host token**. The token, the enrollment grant and the install session each carry a CHECK «exactly one of `connection_id` / `host_id`»; tokens of legacy `pull` connections keep working. The model is never asked at install: the agent reports the CLIs and keys it found and the models it verified (decision 16). The host has an administrator-owned «Использовать» switch (a journalled event, not a column edit); a new host is on (`R-149b`).
2. **System-managed pull connections.** For every discovered quadruple host · provider · access (`subscription` or `api`) · model the stand maintains a `pull` connection with `system_managed = true`: `pin_id` is that model, `billing` is `not_metered` for a subscription and `metered` for an API key. A revision changes only when the catalogue (decision 13) changes; slots live on the host. Users never see these connections: revise and archive refuse them, and the lists, the cut-over preview and the rule-target pickers filter them out.
3. **System groups.** One group per (model, access), composed of every non-archived system connection of that pair, in a new revision only when a host is connected or deleted. «Использовать», reachability and the model check decide **eligibility**, never composition. At most 16 hosts per pair. `ExecutorGroupMemberIssue` gains `host_disabled`, `model_not_verified` and `model_cooling_down`.

### Capacity

4. **Capacity unit and lock key.** The unit is the pair (run, `capacity_pool`), `capacity_pool` = host · provider. A run bound to a `stage_plan` holds one unit in each pool its cells use, from binding until the run ends; comparison calls count in the same pool. Slots per provider and host: subscription 1, API 2, changed by the administrator in the host's details; a host token's `max_claimed_tasks` is at least the sum of its slots. The advisory lock is taken on `capacity_pool`, not on `connection_id`, in all four places: the run claim, the dispatcher hint, the comparison call mirror and the cell binding. The lock order of `ADR-0026` decision 14 is amended accordingly (decision 15).

### Binding

5. **Run binding source `stage_plan`; all cells bound at dispatch.** A run started under the stage layout freezes `audit_run.stage_plan`: for every cell its model, effort and access, and nothing about the length of an answer or a timeout (`R-153n`/`R-153o`; a plan frozen earlier is still read and its two numbers are not). The run carries no group, connection or analysis preset. A **cell** is «row · role»: `main`, `leg1`, `leg2` or `judge` (decision 11). At dispatch, in the claim transaction, **every cell the run will call under its consent is bound at once**, each to a member of the system group of its (model, access); the result is written once to `audit_run_cell_binding`, and a trigger refuses a second write. If any cell has no free eligible member the run stays in the existing `pending` state with the new wait reason `model_unavailable`, naming the cells and the cause; after 30 minutes it ends `no_executor_online` (`R-149c`). Nothing was executed, so nothing is lost: **no state is introduced in the middle of a run**. The environment provider source refuses a `stage_plan` run with a typed refusal; the database source resolves it per cell. `ADR-0026` decision 16 holds: a member that fails mid-run is handled as for any `bound` run, with no re-routing. **Distribution is per run, not per call.** A long run holds a subscription slot to its end: the price of having no mid-run waiting state (`D-499`).

   **No answer cap reaches any model (`R-153n`)**, restoring the owner's instruction of 2026-11-06 (`docs/program/HOTFIX-RUN-PARTIAL-1106.md`). A layout cell carries a model and an effort and no answer limit, anywhere (layout request, reads, frozen plan, `payload.host`). No provider call carries an output-token cap (the agent removes an inherited `CLAUDE_CODE_MAX_OUTPUT_TOKENS` from the child's environment); Anthropic Messages requires `max_tokens` and gets the model's maximum (128000). A `max_tokens` figure in a server request body is what the cost estimate prices the call at, never a cap; the availability probe keeps its own 4096-token ceiling. Contract `1.49.0` removed `max_output_tokens` and `timeout_seconds` from the cells (`timeout_seconds` stays on `payload.host`, from the row constant); the new agent ignores an older stand's cap, so it can be installed first.
6. **`binding_for(cell)`; the identity check stays mandatory.** `binding_for(cell)` returns the member's adapter and one `CallBinding(expected_model)` **per call**; the single `CallBinding` goes away for `stage_plan` runs. `R-133` stays fail-closed: a call without a `CallBinding`, or whose reply names another model, is refused. The three exact comparisons of the reported model move to `accepted_reported`, the exact list the catalogue (decision 13) names per model: no prefix match, no case folding, a test that fails on a model outside the list. Semantic repair of a reply runs on the cell of the phase it repairs.
7. **Idempotency key.** The key of a model call is (source, phase, `request_sha256`, model); it contains neither the host nor the connection revision, so a retry served by another host after a move (`ADR-0026` decision 9) finds the saved reply instead of paying again. `stage_key`, `host_id` (not a foreign key) and `access` are recorded on the call and its effect.
8. **Consent v2.** The readiness read returns the estimate digest, the access per cell and the total. The consent stores the digest of the `stage_plan` and the map model → `rate_sha256` + access, and a call's model must be in that map (`require_approved_model`); older consents stay valid for runs without a `stage_plan`. All cells by subscription: the estimate is 0 $ and pressing the button labelled «по подписке» is the consent (`{estimate_digest, ceiling_micros: 0, confirmed: true}`). At least one cell by API: one dialog with the estimate by model and the total; a batch is always one dialog (`R-151c`). If access changed between the read and the start, the server refuses with `reason: cost_estimate_binding_changed` (`ADR-0026` decision 18, no new error code) and the UI re-reads readiness. `ceiling_micros` is the human's choice; the process-wide `run_cost_ceiling_usd` is a separate notion.
9. **Pull liveness.** **Timeouts are code constants (`R-153o`).** The call window is the constant of its row, from the original: text 1800 s, blocks 1800 s (a leg and the judge take the row's value), cross-check 3600 s, norms 600 s, critic 600 s, refinement 600 s; the four comparison kinds keep the original's 900, 1800, 900 and 2400 s. A number stored in an older layout revision or a frozen plan is not read. **The window is the call's whole window** (`R-155c`/`R-155h`, 2026-11-17; no longer cut to the 600 s silence window): a live Attempt has no age ceiling (the 7200 s ceiling is lifted); an Attempt with no sign of life yet keeps the watchdog's remainder minus a margin. Local work between calls is bounded by a 30-minute silence watchdog that ends the run `failed` with `interrupted_reason = attempt_stalled`. **The agent's silence window is 600 s** (`R-153p`; it was 120 s): the agent extends its claim only while the CLI produced output in the last 600 s, so a hung CLI is caught; it equals the server's stall window on purpose.

### Stage layout

10. **Model rows and code phases.** A row is what the owner sees; a phase is what the code runs. Every label comes from **one** phase dictionary for the whole application.

    | Row | Label | Code phases | Plan | Original key |
    |---|---|---|---|---|
    | `text` | Анализ текста | stage `text_analysis` (PC-01) | always | `text_analysis` |
    | `blocks` | Анализ блоков | `blocks:N`; with an ensemble `blocks:N:leg1`, `:leg2`, `:judge` | v2, v3 | `block_batch` |
    | `cross_check` | Комплексная сверка | `comprehensive_analysis` (windowed and cross-window), parameter passport | v2, v3 | none; valued by analogy with «Свод» |
    | `norms` | Нормы | `norm_verification:N` | v2, v3 | `norm_verify` / `norm_fix` |
    | `review` | Критик | `finding_review` | v3 (opt-in) | `findings_critic` (no model in the original) |
    | `correction` | Уточнение | `finding_correction` | v3 (opt-in) | `findings_corrector` (guard on absence) |

    The default extended-review plan is `v2`; `AUDITMANAGER_EXTENDED_ANALYSIS_PLAN=v3` opts in (`R-154b`), with no UI switch. Plan v3 adds the cross-window check, the parameter passport, the critic and the correction. Under `v2` the layout freezes the rows `text`, `blocks`, `cross_check` and `norms`: the `review` and `correction` cells are not bound and take no server slot, and the original's deterministic critic and corrector (`docs/program/V2-ORIGINAL-REVIEW-01.md`) call no model. «Модели по этапам» still lists all six rows. Without a model: the three PC-01 preparation stages, the merge, the norm-citation check and the report.
11. **Closed block schemes; ensemble identities.** A block row is chosen from a **closed list of schemes** (`BLOCK_SCHEMES`); the legs and the judge are not edited separately. A single Claude on blocks is not offered, even in a custom set (the original forbids it); a single gpt-6-astra stays on the list (the original allows it). Cell identities are `blocks:N:leg1`, `blocks:N:leg2` and `blocks:N:judge`; the call limit of the phase is the base batch count times the number of cells and enters the estimate and the consent. A leg is retried 5 times at 30 s, as in the original, **only** for `not_sent`, `rate_limited`, `proxy_unavailable` and `definite_refusal`; an `outcome_unknown` effect is never retried; a failed leg gives a partial block outcome in the artifact. The judge's prompt is carried over from the original's `dual_review`; it changes `rules_sha256`, so a new consent is expected. Delivered by `HOSTS-ENSEMBLE-01`; the Claude set is named «Только Claude».
12. **Sets (presets), model · effort exactly.** The word «пресет» is taken by analysis presets, so the UI says «набор моделей».

    | Row | «Только Claude» | «Только Codex» |
    |---|---|---|
    | Анализ текста | Sonnet 5.5 · medium | gpt-6.1-sol · medium |
    | Анализ блоков | leg Opus 5.5 · medium + judge Sonnet 5.5 · medium, with search for omissions | legs gpt-6-astra · medium + gpt-6-sol · medium, judge gpt-6.1-sol · medium |
    | Комплексная сверка | Sonnet 5.5 · medium | gpt-6-sol · medium |
    | Нормы | Sonnet 5.5 · medium | gpt-6-astra · medium |
    | Критик | Sonnet 5.5 · medium | gpt-6-sol · medium |
    | Уточнение | Sonnet 5.5 · medium | gpt-6.1-sol · medium |

    «Свой набор» is any administrator edit. The default set is chosen by the administrator when the stand is switched; the initial value is «Только Claude». Enabling the layout on production waited for the ensemble, which is delivered (decision 11). The user sees «модель · усилие»; the «Дополнительно» block with answer tokens and timeout is removed (`R-153n`/`R-153o`). Parallelism is not shown; calls are sequential.
13. **The catalogue file.** `contracts/analysis/v1/model-catalogue.json`, with a `contract_version` and a schema beside it as its siblings have, describes **lock pins only**: provider, allowed efforts, access kinds and `accepted_reported`. Rates and identity stay in `docs/program/P02_LOCK.json`; a catalogue entry without a lock pin fails a test. Efforts: Opus `medium`, `high`; Sonnet and Codex `low`, `medium`, `high`; Haiku, `xhigh`, `max` and Opus `low` are not offered. The lock gains `claude-opus-5-5`, `claude-sonnet-5-5`, `gpt-6.1-sol` and `gpt-6-astra` (`HOSTS-PIN-01`, `R-153b`, lifting `R-143g` for this work); the Claude 5 pins stay for reading past runs.
14. **Layout storage, rules and the DB switch.** The layout is stored as revisions (`slr_<ULID>`) with a journal naming the author. Only an administrator changes it (`R-149b`, default); an expert reads it; a viewer does not see it. **All three start commands** — `startRun`, `reauditRun`, `startRunFromStage` — work from the `stage_plan` and consent v2 while the layout is enabled; «С этапа» takes today's `stage_plan` and reuses only PC-01 stages without a model; explicit executor selectors answer `validation_failed`. **The switch is a row in the database**, set by an administrator, journalled, read only when a run starts, valid only with `AUDITMANAGER_PROVIDER_SOURCE=database`; runs already started are not affected by switching it off. After production is switched the switch is removed. While it is off, the one button follows the legacy automatic route.
15. **Lock order and what else changes.** The lock order of `ADR-0026` decision 14 becomes: worker intake → `capacity_pool` locks in ascending pool key → control → run → job. Cell binding happens in the claim transaction; model I/O starts after commit, as before.

### Agent, keys and availability

16. **Availability.** A model on a host is available when the host is enabled, its heartbeat is at most 120 s old, a login is present, the model is verified and the pair is not under a passive cooldown; «Занято» means available with every slot taken. Reasons for unavailability are stored and journalled; **lists do not show them**: they are visible in a run's waiting line and in a disabled button (`R-149n`) and to the administrator in the host's details. The state is computed on read from stored facts (the report snapshot, append-only change events, the cooldowns, the switch). The agent recomputes every 60 s (no model call) and makes a minimal call per model on change and every 6 h; after a real refusal (access, quota, «no model») the pair is off availability for 15 minutes; the web polls every 10 s while the screen is open.
17. **Direct-API key file on the VPS (`R-153d`).** The agent also reads a key file of its service: mode 0600, owned by the service user, holding `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` and `OPENROUTER_API_KEY`; the agent package gains API responders for the three providers (`HOSTS-AGENT-01`); models so served are access `api`, `metered`. **Keys never reach the stand, a database, a log or the environment of a child CLI** (an allowlist test proves the last). Discovery uses only explicit sources (the CLIs' version and login commands, and this file). This is a new path by which a document's text leaves the stand to a third party: the credential-reach decision `R-29` item 2 requires from the owner, recorded as `R-153d`; it falls under `R-143c` and `D-291`, so the warning «не для клиентских документов» stays on the servers screen, the connect window and the start line while `D-291` is open. A subscription path remains the default (`R-149b`).

### Departures from the original and the first cut

18. **Explicit departures from the original PDF-proverka.** The agent receives the exact `model_id` and `effort` from the catalogue (the original sends a capability that each worker maps); the stand decides, the host only executes. Work is distributed per run, not per call as in the original (decision 5). The original has no «Комплексная сверка» row; it is valued by analogy with its «Свод».
19. **Out of scope of this ADR.** The five `comparison_*` kinds stayed on legacy routing until `HOSTS-CMP-01` (`D-541`); it is delivered (`f57d03753`, contract 1.47.0): with the layout on, four kinds take their cell `<kind>:main` from the layout, are routed to the system group of (model, access) and freeze the cell in the job; `comparison_stage_review` has no handler and stays out (`CMP-SEAL-C4`); with the layout off they route as before. Optimisation calls no model. `--upgrade` of a pull agent whose connection is used by rules or comparisons is refused (`D-540`; the guard still refuses after `HOSTS-CMP-01`). The SSH connection «kzSonnet» on production is untouched; it shares the `adm1.hlab.kz` Claude subscription outside the capacity pool during the transition (`D-540`). There is no reserve set when a quota runs out (`R-153e`, `D-498`).

## What ADR-0028 changes in ADR-0026

| `ADR-0026` decision | Change here |
|---|---|
| 1. One capacity unit | The unit is (run, `capacity_pool`) (decision 4) |
| 2. Coupled limits | For a host token `max_claimed_tasks` ≥ the sum of its slots |
| 3. Per-token claims, one process per token | One process per host |
| 5. Agent health on the token | Health on the host token is the source of availability (decision 16) |
| 8. Four CLI statuses | The integration mark is set by the host's «Использовать» |
| 9. Moving an agent | A move is a new enrollment for the host |
| 10. Immutable homogeneous group revision | System groups per (model, access), created and revised by the stand (decision 3) |
| 12. Binding state | Source `stage_plan`; all cells bound at once (decision 5) |
| 13. Admission freezes intent | The frozen intent is the `stage_plan` and consent v2 (decisions 5, 8) |
| 14. Dispatch in the claim transaction | The lock is per `capacity_pool`; the order changes (decisions 4, 15) |
| 15. Durable waiting | New wait reason `model_unavailable` listing cells, in the existing `pending` state |
| 16. No re-routing after binding | **Unchanged** |
| 17. Cut-over | Mode `rules` / `legacy` does not touch runs from a `stage_plan` |

## Consequences

- Positive: default behaviour is unchanged while the layout switch is off (`ADR-0026` serves as before, a run uses the legacy route).
- Cost: the pin set grows by four; the readers of the bound model and three string comparisons of the reported model are driven by the cell (`HOSTS-LAYOUT-01`).
- Cost: the agent becomes a host agent (model-free install, discovery, API responders, a key file) and the stand gains layout, host, cooldown and write-once cell-binding tables (`HOSTS-SEAL-1`).
- Cost: norms, critic and refinement calls run over a window of work; their 600 s window is the original's figure, not a promise that a large window fits.

## Alternatives considered

- **Per-call routing** — rejected: waiting at a stage boundary needs a mid-run state, and a run could lose work already paid for.
- **An environment flag for the stage layout** — rejected: it needs a restart and leaves no journal.
- **Mixed-billing groups** — not approved (`ADR-0026` decision 10).
- **A reserve set when a quota runs out** — not needed for now (`R-153e`, `D-498`).
- **Merging «Комплексная сверка» into another row** — rejected: its calls are separate phases.
- **Models from the catalogue without a lock pin** — rejected: price and identity have one owner, the lock.

## Verification

Proportional checks (`AGENTS.md` §8, `docs/program/dispatch/HOSTS-PLAN.md`): focused tests per task, one narrow throwaway-database run for the migration, the host-token claim and the cell binding, and a read-only review of the claim, binding and consent diff at each integration; a live check on `adm1.hlab.kz` is an owner act. Every guard has a test that can fail.

## Revisit trigger

The first use with real client documents (`D-291`, decision 17); parallel model calls inside one run (decision 4); distribution per call, or a mid-run waiting state (decision 5); a catalogue model that is not a lock pin (decision 13); mixed-billing groups (`ADR-0026` decision 10).

## History

- 2026-11-09 — accepted on the owner's rulings `R-153a`…`R-153f`; the plan was approved whole (`R-153c`).
- 2026-11-10 — amendment `R-154b`: plan v3 is opt-in, default `v2`; folded into decision 10.
- 2026-11-10 — addendum `LIMITS-01` (`R-153n`, `R-153o`, `R-153p`; `docs/program/OWNER_RULINGS_2026-09-17.md` section 3.53): no answer cap, timeouts as code constants, a 600 s agent silence window, contract `1.49.0`; folded into decisions 5, 9 and 12.
- 2026-11-17 — amendment `R-155c`/`R-155h`: the 7200 s attempt ceiling is lifted, the call window is the whole window; folded into decision 9.
- 2026-11-18 — compressed (ADR-OPTIMISE-01); the full earlier text: git show fb6c2203e:docs/architecture/adr/ADR-0028-hosts-and-stage-models.md
- 2026-11-18 — status statements updated to dev fb6c2203e: `HOSTS-ENSEMBLE-01` is delivered (`33fe14dae`…`2aaef3d4a`; `BLOCKS_ENSEMBLE_LANDED = True` in `src/auditmanager/runs/stage_layout.py`), so both named sets run blocks as an ensemble and the Claude set is «Только Claude»; `HOSTS-CMP-01` is delivered and `D-541` closed (`f57d03753`, `e03a294c7`; `docs/program/DEBT_REGISTER.md`); plan `v2` has the deterministic critic (`docs/program/V2-ORIGINAL-REVIEW-01.md`).
