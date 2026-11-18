# ADR-0024: Production analysis path and AI execution: the other sections come first

- Status: accepted (open: the `AD-18` choice after the `PROD-20` measurement, decision 5)
- Date: 2026-10-26; amended 2026-11-10 (`R-154a`, `R-154c`); revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: `PRODUCTION-ADR-PACK-01`; owner rulings `R-146e`, `R-146f`, `R-146g` (decision 1 replaced by `R-154a`), `R-146j`, `R-146l`, `R-146m`, `R-146q`, `R-146r`, `R-146u`, `R-146v`, `R-146w`, `R-146y`, `R-146af`, `R-146ag`, `R-154a`, `R-154c`; `AD-14` confirmed by `R-146u`, `AD-15` by `R-146v`, `AD-12` and `AD-13` by `R-146w` as written at commit `83600aed`; `AD-18` settled by `R-146y` as to what stands until the measurement
- Amends: supersedes nothing; states the model path `ADR-0011` left to the deployment. The six-Run narrowing of the served АР paths (`R-146g`, `BETA-STATIC-MATRIX-02.md` B3) was withdrawn on 2026-11-10 by `R-154a`

## Context

The owner chose, for the production version: АР v1 and v2 are removed, the text analysis of the other 14
sections stays and bringing them to full versions is the primary task before the beta (`R-146l`);
OpenRouter is the base model connection and `R-133` is unchanged (`R-146e`); real client documents are
allowed at the release with no precondition of provider terms or expert acceptance (`R-146f`); one
worker, no time promise (`R-146j`); the closed beta's data is purged at the release (`R-146m`). Forces:
the 14 profiles had only synthetic recorded cases (`D-178`, `D-183`); a failed model pin stopped
`W56A-MODEL-PIN-01`; no real client document has been analysed and `B3`, `B5`, `B10`, `B11` were
deferred unweakened (`R-141c`, `R-142a`); `R-146q` keeps `B3`, `B5`, `B10` as beta criteria.

## Decision

Open: the choice between raising the 900-second watchdog and a page limit below the 500-page ceiling,
after the `PROD-20` measurement (`AD-18`, decision 5).

### 1. АР runs the standard analysis, like every section (`R-154a`; replaces `R-146g`)

АР runs the same single-Run text analysis as every other section, with the text profile sourced from the
original application's AR files (`HOTFIX-AR-ORIGINAL-PROFILE-INT-20261030`). A version confirmed as АР
starts through `startRun` like any other, and its findings are proposals that the expert accepts or
rejects (`ADR-0012`). This decision first made the six-Run reviewed-pack group the only АР path
(`R-146g`); that group was removed on 2026-11-10 (`R-154a`, `R-154c`) and no ADR describes it.

### 2. Removal of АР v1 and v2 (`R-146l`, `R-146m`)

`AD-12`, confirmed by `R-146w` (an implementation decision within `R-146l`). The removal is done and
guarded by `tests/unit/analysis/test_ar_v1_v2_removal.py`.

**What goes.**

1. The АР v1 registration and the default `text_profile` of the run executor (a silent fallback,
   `AGENTS.md` section 4); `startRun` and `reauditRun` on an АР version then answered the existing
   `section_profile_unavailable`. **Superseded 2026-10-30 (`HOTFIX-AR-ORIGINAL-PROFILE-INT-20261030`):**
   АР is registered again, as a text profile sourced from the original application's AR files, and a
   start on an АР version resolves it (decision 1).
2. The recorded v2 path: its run, findings, recorded and merge modules and the `recorded_v2` branch of
   the run executor.
3. The contract text and enum that name them: `AnalysisProfileStatus.builtin`, the `builtin` sentence of
   `listAnalysisProfiles` and the АР v2 sentence of `info.description`.
4. The tests and recorded fixtures of those paths and the web files that name `builtin`.

**What stays.** The v1 **machinery** (`src/auditmanager/analysis/text/`), the nine stage ids and the
packages under `profiles/<code>/`; the 14 other sections run on it. The closed `FindingCategory` list
and its database `CHECK`s, **unchanged** (`AD-12`): narrowing needs a migration and a reseal and buys
nothing, because the old rows are purged at the release; the text profiles of the other sections emit
only v1's two categories. Migrations: history is immutable. АР project optimisation, norm search and the
specification reads import nothing from v1 or v2, but **they are not independent of the АР analysis
path** (correction of 2026-10-26, `PROD-10-AR-V2-EXTRACT-01` finding 2): the project match and the
section specification read the saved page text of the newest **published** Run of the version and answer
`analysis_missing` when there is none.

**Order (`AD-12`).** (1) Re-base the live journey and its manual protocol onto a section that stays. (2)
Withdrawn 2026-11-10 (`R-154a`): the move of the shared v2 modules served the six-Run group. (3) Remove,
reseal the contract (no path, operation or schema added or removed) and regenerate the client, in one
lane that owns the contract and the composition root for its wave.

**History (`R-146m`).** Existing v1 and v2 run data is not migrated: the 1.0 purge (`ADR-0022` decision
4) removes it; the removal ships first.

### 3. OpenRouter is the base connection; `R-133` stands (`R-146e`)

Production runs with `AUDITMANAGER_PROVIDER_MODE=live`, `AUDITMANAGER_PROVIDER_SOURCE=database` and the
OpenRouter connection imported from `PROXY_LLM_*` in `provider.env` and selected in «Назначения».

`AD-13`, confirmed by `R-146w`: **the pin is the exact string OpenRouter reports.** The connection
revision's gateway model name is the `model` string observed in a reply for that model, not the
requested slug, and a reply's `model` must equal it exactly (no prefix, alias or case folding), else
`model_identity_mismatch` (outcome unknown, not retry-safe: a mismatch is paid for and nothing is
published). No alias list is added to the run path. A reported variant name that changes over time makes
runs fail closed and cost money: the price of `R-133`, accepted by keeping it (`R-133` acts after the
text has been sent, `A-2`; the request side is what `R-146n` item 4 left out). Pinned identities and
rates: `docs/program/P02_LOCK.json`.

The successor to `W56A-MODEL-PIN-01` is the paid probe `PROD-13` (`PRODUCTION-READINESS-PLAN-01.md`;
`R-29`: spending above roughly $5 in a wave stops for the owner; tool
`PROD-13A-MODEL-IDENTITY-PROBE-TOOL-01.md`, run by the integrator at minimum cost, `R-146af`): per
pinned model it records the requested slug, the reported `model` string, the billed rate and the finish
reason, and writes `P02_LOCK.json` only if strings and rates match. That OpenRouter reports the
requested slug for each pinned model is an assumption until the probe has run.

### 4. Cost (`R-146e`, `ADR-0011`)

The per-run ceiling stays at its default of 1.00 USD (`AUDITMANAGER_RUN_COST_CEILING_USD`): a start over
a version too large for it is refused up front (`analysis_input_budget_exceeded`) and a run whose meter
passes it fails with `cost_budget_exceeded`. The cost basis is `measured` when the reply carries a cost
and `estimated` from the rate table otherwise. Proposed owner action (assumption: the provider's console
supports it): a spending limit on the OpenRouter key itself, so that a defect in the ceiling cannot
spend without bound.

`AD-14`, confirmed by `R-146u`: at the release an administrator sets `allow_client_documents` to true on
the OpenRouter connection as a recorded revision, and the flag **stays a label that nothing enforces**.
No code is written for it; no plan item builds a refusal. This is consistent with `A-2`.

### 5. One worker, one queue, and the 900-second attempt (`R-146j`)

The worker has one slot and there is no service-level objective. Jobs are served by priority, then in
arrival order, one at a time; everyone else waits. The levers are administrator operations
(`setJobPriority`, `setExecutionPaused`, `setWorkerIntake`, `cancelRun`). A killed worker is recovered
by lease expiry and the retry budget (3 attempts); nothing is promised about waiting time.

**The attempt has a hard limit.** `ATTEMPT_WATCHDOG_SECONDS` is 900; an attempt that runs longer is
failed. The deterministic stages alone of a 500-page drawing set take most of it (`D-171`; `D-175`
open), and `R-146f` allows documents up to the 500-page upload ceiling, so a large set can fail every
attempt, and an attempt that fails after the model call may have been paid for.

`AD-18`, settled by `R-146y`: **measure on the VPS first, then decide.** `PROD-20` measures the envelope
(pages per minute by document kind, the duration of each stage). Until the owner then chooses between
**raising the watchdog** (overall or per stage) and **a page limit below the 500-page ceiling**, the
watchdog stays 900 s and an input above the budget gets the typed refusal
`analysis_input_budget_exceeded`. That choice is not made by `R-146y`.

### 6. The quality bar (`R-146f`, `R-146q`, `R-146v`)

`R-146f` waives only the condition that an expert has accepted the product: expert acceptance and
provider terms are **not** preconditions of the production release. `R-146q` keeps `B3`, `B5` and `B10`
of `BETA-STATIC-MATRIX-02.md` as **beta** criteria. The release has the contract and guard tests and
synthetic recorded cases for every profile (`D-183`); no real client document analysed, no measured
precision or recall, no expert smoke session. The risk: wrong or incomplete findings on real documents;
mitigations: every finding is a proposal the expert accepts or rejects (`ADR-0012`), and a draft
profile's status is shown in «Настройки анализа».

**Accepted risk A-5 (`R-146v`).** When the 14 sections become «full» their output quality on real text
is unmeasured: a section leaves `draft` when an expert has reviewed its profile (as narrowed by
`R-146ag`, decision 7), no field case is required and the recorded cases stay synthetic. The owner chose
this against the recommended option. Reopen trigger: the first section whose real-text output an expert
rejects, or the first client complaint.

### 7. Priority and what «full» means (`R-146l`, `R-146r`, `R-146v`)

The primary development task until the beta is bringing the other sections to full versions (`R-146l`).
The beta is `1.0.0-beta.N` of the roadmap and the production release is `1.0.0`; the number `0.1.1` of
`R-146l` is not used (`R-146r`). Because `R-146q` keeps `B3`, `B5` and `B10`, the beta also needs the
production connection (`PROD-13`): "sections first" orders the development lanes, not the beta's gates.
`PROD-12` and `D-204` were withdrawn on 2026-11-10 (`R-154a`).

`AD-15`, confirmed by `R-146v` (not the recommended option): a section is **full** when an expert has
reviewed its profile — **narrowed by `R-146ag` (2026-10-26, accepted risk `A-7`): no expert and no owner
reviews it; a section is full when a lane has answered every open question of its record in writing and
the expectations line says `reviewed`.** `PROD-14` has four steps per section: the profile review; the
prompt edit with the re-recording of its synthetic case; the switch of `status` from `draft`; the guard
test that pins it. No field case is required. Who the experts are stays open (`OD-18`).

## Commitments and their mechanical checks

| # | Commitment | Mechanical check |
| --- | --- | --- |
| 1 | After the removal an АР version cannot start a v1 run; superseded 2026-10-30: АР has a text profile again (decision 2 item 1) | `tests/integration/sections/test_routing.py`: an unknown section code never uses the АР profile |
| 2 | Withdrawn 2026-11-10 (`R-154a`): it bound the six-Run group to the v2 package | none |
| 3 | The contract no longer names `builtin` | the enum `AnalysisProfileStatus` in `contracts/api/v1/openapi.json` lists `draft` and `reviewed` only |
| 4 | No profile is silently an АР profile | `tests/unit/analysis/test_ar_v1_v2_removal.py`: `AR_TEXT_PROFILE` and the executor's default profile appear nowhere in `src` as code |
| 5 | A reply naming another model is a typed failure that keeps the usage | `tests/integration/analysis_text/test_model_identity.py` |
| 6 | The run ceiling is 1.00 USD | `P02_LOCK.json` `models.run_cost_ceiling_usd` is `1.0`; `readiness.sh` `cost-ceiling` is `OK` |
| 7 | Production is live on the database source (`PROD-13` sets the values) | `infra/deploy/readiness.sh` prints `readiness OK` for `provider-mode` and `executor-source` |
| 8 | The OpenRouter pin is a probe's reported string | the probe's report names, per pinned model, the requested slug and the reported `model`; only that task writes `P02_LOCK.json` |
| 9 | Every non-АР profile carries `reviewed` before the beta (`R-146v` as narrowed by `R-146ag`: **no human review**, `A-7`; the status proves a lane's written decisions, not a verification) | the 14 non-АР `profile.json` files under `src/auditmanager/analysis/text/profiles/` say `reviewed` (`D-178`; АР is `draft`), pinned by `tests/unit/analysis/text_profiles/test_section_profile_expectations.py` |
| 10 | Withdrawn 2026-11-10 (`R-154a`): it asked for the reviewed pack of the six-Run group | none |
| 11 | One worker slot | `ADR-0021` row 12 |

## Consequences

- Positive: one АР path to reason about; the 14 other sections become the reviewed core before the beta
  (status as the truth, `A-5` its limit); one model identity rule serves every connection kind.
- Cost: a strict `model_identity_mismatch` fails runs after payment; one worker makes the product slow
  under concurrent use, and a large document can exhaust its attempts at the 900-second limit until the
  owner's choice after `PROD-20` (`R-146y`); `A-5`: the reviewed sections are reviewed on prompts and
  synthetic cases, not on real text.

## Alternatives considered

1. Withdrawn 2026-11-10 (`R-154a`): it compared v1 for АР with the six-Run group.
2. **Keep the recorded v2 code for later live use** — rejected by `R-146l`; `git` history keeps it.
3. **Narrow the finding categories in the same reseal** — rejected (`AD-12`): a migration and a contract
   change for a list no registered profile exercises.
4. **An alias list on the run path for OpenRouter's variant names** — rejected (`AD-13`) for now;
   reopened if the probe shows variants.
5. **Enforce `allow_client_documents`** — declined by `R-146u`: the flag stays a label.

## Verification

The commitment rows and the tests they name; the paid probe of `PROD-13`, an expert's review of each
section profile (`PROD-14`) and the release rehearsal's run of one document per reviewed section through
the production connection (`PROD-17`).

## Revisit trigger

Replace this ADR when the first real АР documents have been reviewed, when an expert decides that the 14
sections need more than the text profile, when OpenRouter's reported names make the exact comparison
unworkable, when a second worker slot or a service-level objective is wanted, when the owner accepts
`R-146n` item 4, or when `A-5` reopens.

## History

- 2026-10-26 — accepted for production by the repository owner; the same day `R-146ag` narrowed `AD-15`
  (accepted risk `A-7`) and `PROD-10-AR-V2-EXTRACT-01` corrected decision 2 ("What stays").
- 2026-10-30 — `HOTFIX-AR-ORIGINAL-PROFILE-INT-20261030`: АР registered again as a text profile
  (decision 2 item 1, commitment 1).
- 2026-11-10 — amended (`R-154a`, `R-154c`): decision 1 replaced; the six-Run reviewed-pack group
  withdrawn (decision 2 order step 2, rows 2 and 10, alternative 1); `PROD-12` and `D-204` withdrawn.
- 2026-11-18 — compressed (ADR-OPTIMISE-01); the full earlier text: git show fb6c2203e:docs/architecture/adr/ADR-0024-production-analysis-path-and-ai-execution.md
- 2026-11-18 — status statements updated to dev fb6c2203e: the removal is done (`PROD-11`); commitments
  3, 4 and 9 restated (`D-178`); the probe tool exists (`PROD-13A`); the table's snapshot columns
  dropped.
