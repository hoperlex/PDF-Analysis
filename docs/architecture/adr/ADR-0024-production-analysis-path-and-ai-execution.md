# ADR-0024: Production analysis path and AI execution: the other sections come first

- Status: accepted for production by the repository owner (`R-146e`, `R-146f`, `R-146g`, `R-146j`, `R-146l`, `R-146m`, `R-146q`, `R-146r`, `R-146u`, `R-146v`, `R-146w`, `R-146y`); `AD-14` is confirmed by `R-146u`, `AD-15` by `R-146v`, `AD-12` and `AD-13` by `R-146w` as written at commit `83600aed`; `AD-18` is settled by `R-146y` as to what stands until the measurement, and the choice it leaves is open. **Amended 2026-11-10 (`R-154a`, `R-154c`):** decision 1 is replaced and every passage that described the six-Run reviewed-pack group is withdrawn; that group was removed from the tree
- Date: 2026-10-26
- Owners: repository owner / `PRODUCTION-ADR-PACK-01`
- Supersedes: nothing; it states the model path `ADR-0011` left to the deployment. The narrowing of the served АР paths of `BETA-STATIC-MATRIX-02.md` (B3) to the six-Run group (`R-146g`) was withdrawn on 2026-11-10 (`R-154a`)
- Related principles: P-10, P-15, P-16, P-17

## Context

The owner chose, for the production version: АР v1
and v2 are removed and the profile-driven text analysis of the other 14 sections stays, and bringing
those sections to full versions is the primary development task until the beta (`R-146l`); OpenRouter
is the base model connection and `R-133` is unchanged (`R-146e`); real client documents are allowed at
the release with no precondition of provider terms or expert acceptance (`R-146f`); one worker and
no time promise (`R-146j`); the closed beta's data is purged at the release (`R-146m`). Facts read
from the tree at `4d7b7c38` on 2026-10-26:

- **Two АР paths were in the tree** (`BETA-STATIC-MATRIX-02.md` B3), besides a third one that was withdrawn on 2026-11-10
  (decision 1). *v1* was served: `startRun` routes a version by its
  expert-confirmed section through the text-profile registry, AR is registered from the v1 constants
  (`AR_TEXT_PROFILE`, two categories `internal_contradiction` and `explicit_placeholder`), and the live
  journey `tests/e2e/pc01/journey/journey.mjs` uploads an АР portal bundle and drives that run. *v2* is a
  recorded-only profile that no operation or screen can start; its read side is still served.
- **The v1 machinery is shared.** The registry loads each of the 14 other sections from
  `src/auditmanager/analysis/text/profiles/<code>/` and says: "categories, response schema, user preamble, page banner
  and token limits stay v1's" (`src/auditmanager/analysis/text/profile_registry.py`). All 14 are
  `status: draft` (PB is authored, with open questions); their recorded cases are synthetic; no expert has
  reviewed them and no field case exists (`D-178`, `D-183`). A section with no profile is refused with
  `section_profile_unavailable`, with no АР fallback.
- **The recorded v2 code is spread over many files.** Thirty source files name v2 (`grep -rlE "ar_v2|recorded_v2|AR_V2|v2_publication|v2_recorded|RecordedV2" src --include=*.py | wc -l`
  prints 30; 13 are inside `src/auditmanager/analysis/profiles/ar_v2/`). `AR_TEXT_PROFILE` is named in six source files, among them
  `src/auditmanager/runs/executor.py`, whose `execute_run` served v1 and recorded v2 in one function. The count is by name: v2 code that
  does not carry the string
  (for example `src/auditmanager/findings/recorded_saved_plan.py`, `src/auditmanager/findings/merge_publication_plan.py`,
  `src/auditmanager/analysis/stages/finding_merge.py`) is found by following imports, which was the first task of `PROD-10`.
- **The contract.** 92 paths, 104 operations, 300 schemas, contract `1.5.0`. No operation is specific to v1 or v2. The
  contract text names them in `listAnalysisProfiles` (the status `builtin`, which only the AR v1 profile
  carries) and in the schema `AnalysisProfileStatus`; `FindingCategory` is a closed list of twelve, of
  which two are v1's, five are v2's non-normative categories and five are the normative categories; the database
  `CHECK` constraints carry the same list (`db/migrations/versions/20260910_0002_pc01_schema.py`, widened later).
- **The model path.** The default provider mode in `alpha.env.example` is `recorded`. `EXEC-ENV-OPENROUTER-01`
  registers an OpenRouter-compatible HTTP connection from `PROXY_LLM_*` in `provider.env` under
  `AUDITMANAGER_PROVIDER_SOURCE=database`, after which an administrator selects it. On the run path the reply's
  `model` string must equal the connection revision's gateway name **exactly** (no prefix, no alias, no case
  folding): `src/auditmanager/analysis/text/stage.py::_identity_refusal` for the text stage and `src/auditmanager/runs/extended_review.py` for the extended review.
  `ProxySettings.model_aliases` exists but no configuration reader in `src/` ever sets it. The refusal is
  `model_identity_mismatch`, `outcome_unknown` and not retry-safe, so a mismatch is paid for and nothing is
  published. `W56A-MODEL-PIN-01` stopped: the stand's proxy gateway answered a request for one model with another
  (`W56A-MODEL-PIN-01.md`). Pinned identities and the rate table are in `P02_LOCK.json` (`claude-opus-5`, `claude-sonnet-5`,
  `gpt-6-sol`; `run_cost_ceiling_usd` 1.0, overridable by `AUDITMANAGER_RUN_COST_CEILING_USD`).
- **`allow_client_documents`.** Each executor connection revision carries this boolean; the imported OpenRouter
  connection is created with `false`, and the connection card shows «не отправляются». No code under `src/` reads
  it to refuse a call (a search finds only its storage, its schema and the import). The screen therefore
  says documents are not sent while an analysis through that connection sends them.
- **One worker.** The `worker` service has one slot. A job is claimed `FOR UPDATE SKIP LOCKED` by priority, then
  creation time. Lease 60 s, heartbeat 20 s, attempt watchdog 900 s, attempt budget 3, drain 270 s. A 500-page drawing
  set took 307 s plus 415 s in the two deterministic stages on a loaded host (`D-171`); a PDF with no drawing
  elements costs about 3.8 s a page (`D-175`).
- **What no one has done.** No real client document has been analysed (`R-141c`, `R-142a`); the recorded cases are
  synthetic (`D-183`); `B3`, `B5`, `B10` and `B11` of the beta criteria were deferred with their text unweakened
  (`R-141c`), and `R-146q` keeps `B3`, `B5` and `B10` as beta criteria.

## Decision

### 1. АР runs the standard analysis, like every section (`R-154a`; replaces `R-146g`)

АР runs the same single-Run text analysis as every other section. Its profile is the text profile sourced from the
original application's AR files (`HOTFIX-AR-ORIGINAL-PROFILE-INT-20261030`, `src/auditmanager/analysis/text/profile_registry.py`).
A version confirmed as АР starts through `startRun` like any other, and its findings are proposals that the expert accepts or rejects
(`ADR-0012`). This decision first made the six-Run reviewed-pack group the only АР path (`R-146g`). That group was removed from the tree
on 2026-11-10 (`R-154a`, `R-154c`), and no ADR describes it.

### 2. Removal of АР v1 and v2 (`R-146l`, `R-146m`)

`AD-12`, confirmed by `R-146w` as written at commit `83600aed` (an implementation decision within `R-146l`). Scope, derived from the greps above:

**What goes.**

1. The АР v1 registration: `AR_TEXT_PROFILE` as the AR entry of `load_text_profile_registry`, and the default `text_profile = AR_TEXT_PROFILE` in
   `src/auditmanager/runs/executor.py` (a silent fallback that `AGENTS.md` section 4 forbids once AR is no longer a profile). After it, `startRun` and `reauditRun` on a version
   classified `AR` answered the existing `section_profile_unavailable` (no new error code, the catalogue stayed at 27).
   **Superseded 2026-10-30 (`HOTFIX-AR-ORIGINAL-PROFILE-INT-20261030`):** АР is registered again, as a text profile sourced from the
   original application's AR files, and a start on an АР version resolves it (decision 1).
2. The recorded v2 path: `src/auditmanager/runs/recorded_v2_{merge,publication,sources,stage}.py`, `src/auditmanager/findings/v2_publication.py`,
   `src/auditmanager/findings/v2_recorded.py`, `src/auditmanager/findings/recorded_saved_plan.py`, the `recorded_v2` branch and `plan_recorded_v2_execution` of
   `src/auditmanager/runs/executor.py`, the v2 exports of `src/auditmanager/analysis/public.py`, and the recorded and merge modules of
   `src/auditmanager/analysis/profiles/ar_v2/`.
3. The contract text and enum that name them: `AnalysisProfileStatus.builtin`, the `builtin` sentence of `listAnalysisProfiles`
   and the АР v2 sentence of `info.description`; `listAnalysisProfiles` returns `profile: null` for АР.
4. The tests of those paths (65 test files: `grep -rlE 'ar_v2|recorded_v2|v2_publication|v2_recorded|AR_V2' tests --include=*.py | wc -l`
   prints 42 and the same search for `AR_TEXT_PROFILE` prints 27, with overlap), the recorded fixtures of v1
   (`fixtures/recorded/text_analysis`), and the seven web files that name `builtin`.

**What stays.**

- The v1 **machinery**: `src/auditmanager/analysis/text/prompt.py`, `stage.py`, `budget.py`, `proxy.py`, `profile_registry.py`, the
  nine stage ids and the packages under `src/auditmanager/analysis/text/profiles/<code>/`. The 14 other sections run on it.
- The closed `FindingCategory` list and its database `CHECK`s, **unchanged** (`AD-12`): narrowing the list needs a
  migration and a reseal and buys nothing, because the old rows are purged at the release. The seven non-normative categories stay
  declared; the text profiles of the other sections emit only v1's two.
- **What the six-Run group needed from v2.** Withdrawn 2026-11-10 (`R-154a`): the group is removed, and so is the extraction of the
  shared v2 modules that served it.
- Migrations: history is immutable (`0022_findings_v2`, `0023_norm_citations` stay).
- АР project optimisation, norm search and the specification reads: they import nothing from v1 or v2 (the importers
  are listed above). **Correction of 2026-10-26 (`PROD-10-AR-V2-EXTRACT-01`, finding 2):** they are not independent of the АР analysis path. `optimisation/project_match.py` (`_newest_published`) and `optimisation/section_specification.py` (`_read_source`) read the saved page text of the newest **published** Run of the version and answer `analysis_missing` when there is none.

**Order (`AD-12`).** (1) Re-base the live journey `journey.mjs`, `tests/e2e/pc01/` and the manual protocol onto a section that
stays; otherwise the complete gate goes red on a run the removal makes impossible (the frontend battery cannot see a broken
journey). (2) Withdrawn 2026-11-10 (`R-154a`): the move of the shared v2 modules served the six-Run group. (3) Remove, reseal the contract, regenerate the web client, fix the tests, in one lane
that owns the contract and the composition root for its wave.

**The contract consequence.** A reseal, owned by one slot in its wave (`AGENTS.md` section 3). No path, operation or schema is
added or removed, so the surface stays at 92 paths, 104 operations and 300 schemas; an enum member and prose change. The
version number is the reseal owner's under the versioning policy. `web/openapi/openapi.json`, the generated client
and `web/FRONTEND_LOCK.json` change with it.

**History (`R-146m`).** Existing v1 and v2 run data is not migrated: the 1.0 purge (`ADR-0022` section 4) removes all product
data. Rows of a v1 run are ordinary runs of a section and stay readable by the generic reads, which stay; rows of a v2 run cannot
exist outside tests, since no operation creates one. The removal ships before the purge and the purge follows it.

### 3. OpenRouter is the base connection; `R-133` stands (`R-146e`)

Production runs with `AUDITMANAGER_PROVIDER_MODE=live`, `AUDITMANAGER_PROVIDER_SOURCE=database` and the OpenRouter connection
imported from `PROXY_LLM_*` in `provider.env` and selected in «Назначения»; `readiness.sh` `provider-mode` and
`executor-source` report the first two.

`AD-13`, confirmed by `R-146w` as written at commit `83600aed`: **the pin is the exact string OpenRouter reports.** The connection revision's gateway model
name is set to the `model` string observed in a reply for that model, not to the slug that was requested. No alias list is added
to the run path (it would change the executors settings and the contract; `ProxySettings.model_aliases` stays unused). If
OpenRouter reports a dated or provider-specific variant that changes over time, runs fail closed with `model_identity_mismatch` and cost
money; that is the price of `R-133` and is accepted by keeping it. What `R-146n` item 4 left out is on the request side
(no routing restriction, no ban on substitution); `R-133` is the product's only defence on the reply side, and it acts after
the text has been sent (`A-2`, `ADR-0022`).

The successor to `W56A-MODEL-PIN-01` is `PROD-13` of the plan: a paid probe, under `R-29` (spending above roughly $5 in a wave
stops for the owner) and the preflight that task wrote down (a route, a credential in protected configuration, a concrete model name,
operator evidence that the model is selectable), that sends one explicit request per pinned model through the production connection and
records, for each, the requested slug, the reported `model` string, the billed rate against `P02_LOCK.json` and the finish reason. It writes
`P02_LOCK.json` only if the reported strings and rates match, and it supersedes nothing of the failed `W56A-PROBE-01` evidence. Whether OpenRouter reports the requested slug for each
pinned model is an assumption until that probe has run.

### 4. Cost (`R-146e`, `ADR-0011`)

The per-run ceiling stays at its default of 1.00 USD (`AUDITMANAGER_RUN_COST_CEILING_USD`): a start over a version too large for it is
refused up front (`analysis_input_budget_exceeded`) and a run whose meter passes it fails with `cost_budget_exceeded`;
`readiness.sh` `cost-ceiling` reads it. The cost basis is `measured` when the reply carries a cost and
`estimated` from the rate table otherwise. Proposed owner action (assumption: the provider's console supports it,
which the tree cannot show): a spending limit on the OpenRouter key itself, so that a defect in the ceiling cannot spend without bound.

`AD-14`, confirmed by `R-146u`: at the release an administrator sets `allow_client_documents` to true on the OpenRouter connection as a recorded
revision, and the flag **stays a label that nothing enforces**. No code is written for it; no plan item builds a refusal. This is consistent with `A-2`.

### 5. One worker, one queue, and the 900-second attempt (`R-146j`)

The worker has one slot and there is no service-level objective. Jobs are served by priority, then in arrival order, one at
a time, and everyone else waits. The levers that exist are administrator operations:
`setJobPriority`, `setExecutionPaused`, `setWorkerIntake`, `cancelRun`. A killed worker is recovered by lease expiry and the retry
budget (3 attempts); nothing is promised about waiting time, and the queue screen «Очередь» is the only visibility.

**The attempt has a hard limit.** `ATTEMPT_WATCHDOG_SECONDS` is 900 (`src/auditmanager/jobs/lease.py`); an attempt that runs longer is failed.
The two deterministic stages alone of a 500-page drawing set took 307 s plus 415 s, 722 s, about 80 % of that limit before any model call (`D-171`),
and a PDF with no drawing elements costs about 3.8 s a page in the worker's pdfplumber, which reaches 900 s at about 237 pages (`D-175`, open;
the page figure is arithmetic on the measured rate). `R-146f` allows real client documents of up to the 500-page upload ceiling, so a large
set can fail every attempt, and an attempt that fails after the model call may have been paid for. The earlier sentence of this ADR that a 500-page analysis
holds the slot "for the better part of an hour" was wrong: it is failed at fifteen minutes.

`AD-18`, settled by `R-146y`: **measure on the VPS first, then decide.** `PROD-20` measures the envelope (pages per minute by document kind, the duration of each
stage). Until the owner then chooses between **raising the watchdog** (overall or per stage) and **a page limit below the 500-page ceiling**, the watchdog stays 900 s
and an input above the budget gets the typed refusal `analysis_input_budget_exceeded`. That choice is not made by `R-146y`; it stays an open decision after the measurement.

### 6. The quality bar (`R-146f`, `R-146q`, `R-146v`)

`R-146f` waives only the condition that an expert has accepted the product: expert acceptance and provider terms are **not** preconditions of the
production release. `R-146q` keeps `B3`, `B5` and `B10` of `BETA-STATIC-MATRIX-02.md` as **beta** criteria; they are not waived for the beta. The evidence
the release has: the contract and guard tests, synthetic recorded cases for every profile (`D-183`), and whatever the owner and the experts review before they decide. The evidence it does not have: any real
client document analysed, any measured precision or recall, any expert smoke session. The risk, stated plainly: the product may publish findings that are
wrong or incomplete on real documents, and the first people to find out will be the users. Mitigations that exist: every finding is a proposal the expert accepts
or rejects (`ADR-0012`); a draft profile's status is shown in «Настройки анализа».

**Accepted risk A-5 (`R-146v`).** When the 14 sections become «full», the quality of their output on real text is unmeasured: a section leaves `draft` when an expert
has reviewed its profile, no non-synthetic field case is required, and the recorded cases stay synthetic. The owner chose this against the recommended option.
Reopen trigger (given with the ruling's application): the first section whose real-text output an expert rejects, or the first client complaint.

### 7. Priority and what «full» means (`R-146l`, `R-146r`, `R-146v`)

The primary development task until the beta is bringing the other sections to full versions (`R-146l`). The beta is `1.0.0-beta.N` of the roadmap and the production
release is `1.0.0`; the number `0.1.1` written in `R-146l` is not used (`R-146r`).

`AD-15`, confirmed by `R-146v` (not the recommended option): a section is **full** when an expert has reviewed its profile — **narrowed by `R-146ag` (2026-10-26, accepted risk `A-7`): no expert and no owner reviews it; a section is full when a lane has answered every open question of its record in writing and the expectations line says `reviewed`.** Per section, `PROD-14` therefore has
four steps: the expert's review of the profile; the edit of the prompt with the re-recording of its synthetic case (editing a prompt orphans its recording); the switch
of `status` from `draft` in the profile package; and the guard test that pins the new state. No field case is required. Who the experts are stays open (`OD-18`).

The order of the plan (`PRODUCTION-READINESS-PLAN-01.md` section 4): section work starts in the first code wave and runs through the others; the removal of v1/v2
follows its prerequisite (waves `PW3` and `PW4`). Because `R-146q` keeps `B3`, `B5` and
`B10`, the beta also needs the production connection (`PROD-13`); "sections first" orders the development lanes, not the beta's gates. The AR pack item `PROD-12` and `D-204`
were withdrawn on 2026-11-10 (`R-154a`).

## Commitments and their mechanical checks

| # | Commitment | Mechanical check | Exists | Delivered by |
| --- | --- | --- | --- | --- |
| 1 | After the removal an АР version cannot start a v1 run | an integration test: `startRun` on a version confirmed as `AR` answers `422 section_profile_unavailable`; `pytest -q tests/integration/sections/test_routing.py` keeps its test that an unknown code never uses the АР profile | the routing test yes, the 422 test is new; superseded 2026-10-30, see decision 2 item 1 | `PROD-11` |
| 2 | Withdrawn 2026-11-10 (`R-154a`): it bound the six-Run group to the v2 package | none | none | none |
| 3 | The contract no longer names `builtin` | `python3 -I -c "import json;print('builtin' in json.dumps(json.load(open('contracts/api/v1/openapi.json'))))"` prints `False` | no (it prints `True`) | `PROD-11` |
| 4 | No profile is silently an АР profile | `grep -rn "AR_TEXT_PROFILE" src` prints nothing | no (six files) | `PROD-11` |
| 5 | A reply naming another model is a typed failure that keeps the usage | `pytest -q tests/integration/analysis_text/test_model_identity.py` | yes | none |
| 6 | The run ceiling is 1.00 USD | `python3 -I -c "import json;print(json.load(open('docs/program/P02_LOCK.json'))['models']['run_cost_ceiling_usd'])"` prints `1.0`; `readiness.sh` `cost-ceiling` is `OK` | yes | none |
| 7 | Production is live on the database source | `infra/deploy/readiness.sh \| grep -E 'readiness OK +(provider-mode\|executor-source)'` prints both lines | yes (the command) | `PROD-13` sets the values |
| 8 | The OpenRouter pin is a probe's reported string | the probe's report names, per pinned model, the requested slug and the reported `model`; `P02_LOCK.json` is written only by that task | no | `PROD-13` |
| 9 | Every non-АР profile carries the status `reviewed` before the beta (`R-146v` as narrowed by `R-146ag`: **no human review**, `A-7`; the status proves a lane's written decisions, not a verification) | `python3 -I -c "import json,glob;print(sorted(json.load(open(f))['status'] for f in glob.glob('src/auditmanager/analysis/text/profiles/*/profile.json')))"` prints fourteen `reviewed` | no (it prints fourteen `draft`) | `PROD-14` |
| 10 | Withdrawn 2026-11-10 (`R-154a`): it asked for the reviewed pack of the six-Run group | none | none | none |
| 11 | One worker slot | `ADR-0021` row 12 | yes | none |

## Consequences

### Positive

- One АР path to reason about, test and explain; the recorded v2 code, which nothing can start, stops costing review time.
- The 14 other sections become the product's reviewed core before the beta, and a profile's status says the truth (with `A-5` as the stated limit of that truth).
- The model identity check keeps one rule for every connection kind.

### Negative / cost

- Withdrawn 2026-11-10 (`R-154a`): two costs that belonged to the six-Run group, namely no АР analysis before its reviewed pack existed, and no detection of internal contradictions and empty placeholders in АР. АР has a text profile again (decision 1).
- The removal touches the contract, `src/auditmanager/runs/executor.py`, 65 test files and the web, and the live journey must change first.
- A strict `model_identity_mismatch` on a provider that reports variant names fails runs after payment.
- A single worker makes the product slow under any concurrent use, with no promise, and a large document can exhaust its attempts at the 900-second limit until the owner's choice after the `PROD-20` measurement (`R-146y`).
- `A-5`: the reviewed sections are reviewed on prompts and synthetic cases, not on real text.

## Alternatives considered

1. Withdrawn 2026-11-10 (`R-154a`): it compared v1 for АР with the six-Run group.
2. **Keep the recorded v2 code as the foundation for later live use.** Rejected by `R-146l`; `git` history keeps it.
3. **Narrow the finding categories in the same reseal.** Rejected (`AD-12`): a migration and a contract change for a list that no registered profile exercises.
4. **An alias list on the run path for OpenRouter's variant names.** Rejected (`AD-13`) for now: it changes the executors settings; reopened if the probe shows variants.
5. **Enforce `allow_client_documents`.** Declined by `R-146u`: the flag stays a label.

## Verification

- automated check/test: the eleven rows above; on the removal lane the tests named in `PROD-11`, with a mutation proof for every new guard
- manual/operational evidence: the paid probe of `PROD-13` (owner-approved), an expert's review of each section profile (`PROD-14`), and the release rehearsal's run of one
  document per reviewed section through the production connection (`PROD-17`)

## Revisit trigger

Replace this ADR when the first real АР documents have been reviewed, when an expert decides that the 14 sections need more than the text
profile, when OpenRouter's reported names make the exact comparison unworkable, when a second worker slot or a service-level objective is wanted, or when the
owner decides to accept `R-146n` item 4, or when `A-5` reopens.
