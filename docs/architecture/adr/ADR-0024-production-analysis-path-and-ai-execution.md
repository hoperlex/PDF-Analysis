# ADR-0024: Production analysis path and AI execution: АР is v3 only, the other sections come first

- Status: accepted for production by the repository owner (`R-146e`, `R-146f`, `R-146g`, `R-146j`, `R-146l`, `R-146m`); the implementation choices marked `AD-` are the architect's, proposed and not yet confirmed
- Date: 2026-10-26
- Owners: repository owner / `PRODUCTION-ADR-PACK-01`
- Supersedes: nothing; it narrows the served АР paths of `BETA-STATIC-MATRIX-02.md` (B3) to one and states the model path `ADR-0011` left to the deployment
- Related principles: P-10, P-15, P-16, P-17

## Context

The owner chose, for the production version: АР is the six-Run reviewed-pack path only (`R-146g`); АР v1
and v2 are removed and the profile-driven text analysis of the other 14 sections stays, and bringing
those sections to full versions is the primary development task until the beta (`R-146l`); OpenRouter
is the base model connection and `R-133` is unchanged (`R-146e`); real client documents are allowed at
the release with no precondition of provider terms or expert acceptance (`R-146f`); one worker and
no time promise (`R-146j`); the closed beta's data is purged at the release (`R-146m`). Facts read
from the tree at `4d7b7c38` on 2026-10-26:

- **Three АР paths exist** (`BETA-STATIC-MATRIX-02.md` B3). *v1* is served: `startRun` routes a version by its
  expert-confirmed section through the text-profile registry, AR is registered from the v1 constants
  (`AR_TEXT_PROFILE`, two categories `internal_contradiction` and `explicit_placeholder`), and the live
  journey `tests/e2e/pc01/journey/journey.mjs` uploads an АР portal bundle and drives that run. *v2* is a
  recorded-only profile that no operation or screen can start; its read side is still served. *v3* is the six-Run
  group (`startArV3BetaGroup`, `getArV3BetaGroup`, `getArV3BetaGroupReview`, `getArV3BetaPackStatus`); it
  refuses every start while the reviewed-pack registry is empty, and filling it is data and expert review that no
  code supplies (`D-204`, `AR-V3-BETA-ACTIVATION-RUNBOOK-01.md`). Its output is review-only: provisional citations
  that need an expert's check, no numerical conclusion, and no canonical finding to decide
  (`CURRENT_STATE.md`).
- **The v1 machinery is shared.** The registry loads each of the 14 other sections from
  `src/auditmanager/analysis/text/profiles/<code>/` and says: "categories, response schema, user preamble, page banner
  and token limits stay v1's" (`src/auditmanager/analysis/text/profile_registry.py`). All 14 are
  `status: draft` (PB is authored, with open questions); their recorded cases are synthetic; no expert has
  reviewed them and no field case exists (`D-178`, `D-183`). A section with no profile is refused with
  `section_profile_unavailable`, with no АР fallback.
- **v3 stands on v2 code.** Thirty source files name v2 (`grep -rlE "ar_v2|recorded_v2|AR_V2|v2_publication|v2_recorded|RecordedV2" src --include=*.py | wc -l`
  prints 30; 13 are inside `src/auditmanager/analysis/profiles/ar_v2/`). Five modules of `src/auditmanager/analysis/profiles/ar_v3/`
  and `src/auditmanager/analysis/recognised/region_candidate.py` import `ar_v2.recognised_context`, `ar_v2.content`, `ar_v2.grounding`
  and `ar_v2.registered`. `AR_TEXT_PROFILE` is named in six source files, among them `src/auditmanager/runs/executor.py`, whose
  `execute_run` serves v1, recorded v2 and v3 in one function.
- **The contract.** 92 paths, 104 operations, 300 schemas, contract `1.5.0`. No operation is specific to v1 or v2. The
  contract text names them in `listAnalysisProfiles` (the status `builtin`, which only the AR v1 profile
  carries) and in the schema `AnalysisProfileStatus`; `FindingCategory` is a closed list of twelve, of
  which two are v1's, five are v2's non-normative categories and five are v3's normative categories; the database
  `CHECK` constraints carry the same list (`db/migrations/versions/20260910_0002_pc01_schema.py`, widened later).
- **The model path.** The default provider mode in `alpha.env.example` is `recorded`. `EXEC-ENV-OPENROUTER-01`
  registers an OpenRouter-compatible HTTP connection from `PROXY_LLM_*` in `provider.env` under
  `AUDITMANAGER_PROVIDER_SOURCE=database`, after which an administrator selects it. On the run path the reply's
  `model` string must equal the connection revision's gateway name **exactly** (no prefix, no alias, no case
  folding): `src/auditmanager/analysis/text/stage.py::_identity_refusal` for the text stage and `src/auditmanager/runs/v3_provider_call.py` for v3.
  `ProxySettings.model_aliases` exists but no configuration reader in `src/` ever sets it. The refusal is
  `model_identity_mismatch`, `outcome_unknown` and not retry-safe, so a mismatch is paid for and nothing is
  published. `W56A-MODEL-PIN-01` stopped: the stand's proxy gateway ignored the requested model and answered with another
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
  (`R-141c`).

## Decision

### 1. АР in production is v3 only (`R-146g`)

What the user gets: a start control that creates one group of six Runs of an АР version (checks `F1`, `F2`, `A1`, `A2`, `S1`,
`S2`), a group review of six scope outcomes with provisional quotations marked as needing an expert's check, each linked to
the source PDF, and the pack status in «Настройки анализа». What the user does **not** get, stated plainly:

- no check for internal contradictions and no check for empty placeholders in АР documents (those are v1's two categories and
  v3 finds neither);
- no numerical conclusion about a norm until an expert decision and an edition check exist;
- no canonical АР finding list, no verdict entry for АР findings and no CSV or Excel export of АР findings;
- nothing at all until `D-204` is done: before a reviewed pack is installed every group start refuses with
  `dependency_unavailable`. `D-204` is on the critical path of 1.0 for АР (`R-146g`).

### 2. Removal of АР v1 and v2 (`R-146l`, `R-146m`)

`AD-12` (architect's implementation decision within `R-146l`, to be confirmed). Scope, derived from the greps above:

**What goes.**

1. The АР v1 registration: `AR_TEXT_PROFILE` as the AR entry of `load_text_profile_registry`, and the default `text_profile = AR_TEXT_PROFILE` in
   `src/auditmanager/runs/executor.py` (a silent fallback that `AGENTS.md` section 4 forbids once AR is no longer a profile). After it, `startRun` and `reauditRun` on a version
   classified `AR` answer the existing `section_profile_unavailable` (no new error code, the catalogue stays at 27), and
   the web start control sends an АР version to the v3 control instead.
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
  migration and a reseal and buys nothing, because the old rows are purged at the release. Five v2 categories remain declared
  and no registered profile emits them; that is recorded as a debt row, not removed.
- The shared v2 modules that v3 imports (`recognised_context`, `content`, `grounding`, `registered`): they **move first**, under
  the v3 package or a neutral one, in a lane of their own before any deletion.
- Migrations: history is immutable (`0022_findings_v2`, `0023_norm_citations` stay).
- АР project optimisation, norm search and the specification reads: they import nothing from v1 or v2 (the importers
  are listed above) and are not part of the АР analysis path.

**Order (`AD-12`).** (1) Re-base the live journey `journey.mjs`, `tests/e2e/pc01/` and the manual protocol onto a section that
stays; otherwise the complete gate goes red on a run the removal makes impossible (the frontend battery cannot see a broken
journey). (2) Move the shared v2 modules. (3) Remove, reseal the contract, regenerate the web client, fix the tests, in one lane
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

`AD-13` (to be confirmed): **the pin is the exact string OpenRouter reports.** The connection revision's gateway model
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
`estimated` from the rate table otherwise. A v3 group is six Runs, each under the ceiling. Proposed owner action (assumption: the provider's console supports it,
which the tree cannot show): a spending limit on the OpenRouter key itself, so that a defect in the ceiling cannot spend without bound.

`AD-14` (to be confirmed): at the release an administrator sets `allow_client_documents` to true on the OpenRouter connection, as a recorded
revision, because `R-146f` permits client documents and the screen must not say otherwise. The flag is not enforced anywhere; whether it
should become a refusal is a separate decision, not taken here.

### 5. One worker, one queue (`R-146j`)

The worker has one slot and there is no service-level objective. Jobs are served by priority, then in arrival order, one at
a time; a 500-page analysis occupies the slot for the better part of an hour in the worst measured case (`D-171`, `D-175`), and a v3 group
is six jobs in a row. Everyone else waits. The levers that exist are administrator operations: `setJobPriority`, `setExecutionPaused`,
`setWorkerIntake`, `cancelRun`. A killed worker is recovered by lease expiry and the retry budget; an attempt past the 900-second
watchdog is failed. Nothing is promised about waiting time, and the queue screen «Очередь» is the only visibility.

### 6. The quality bar (`R-146f`)

Expert acceptance and provider terms are **not** preconditions of the production release (`R-146f`). The evidence the release has: the contract and
guard tests, synthetic recorded cases for every profile (`D-183`), the v3 pack's sealed manifest and the reviewer's attestation recorded in it (a record, not a
signature: `D-212`), and whatever the owner and the experts review before they decide. The evidence it does not have: any real client document analysed, any measured
precision or recall, any expert smoke session (`B3`, `B5`, `B10` unmet, `B11` open). The risk, stated plainly: the product may
publish findings and provisional citations that are wrong or incomplete on real documents, and the first people to find out will
be the users. Mitigations that exist: every v3 quotation is marked as needing an expert's check; every finding of the other
sections is a proposal the expert accepts or rejects (`ADR-0012`); a draft profile's status is shown in «Настройки анализа». Whether `R-146f` also waives
`B3`, `B5` and `B10` as beta criteria is not stated in the ruling and is listed as open in the plan.

### 7. Priority (`R-146l`)

The primary development task until the beta is bringing the other sections to full versions. `AD-15` (to be confirmed) gives the term a
measurable meaning, per section: (a) the profile is reviewed by a named expert and its status becomes `reviewed` in the registry
(`D-178`); (b) at least one positive and one negative case run on a document that is not synthetic and not a client document
(`R-141c` binds the closed beta), recorded and replayable (`D-183`); (c) an expert accepts the outputs of those runs. Whether "full" also means
more categories or norm checks of the kind v3 adds is the owner's question; this ADR does not assume it. How the owner's «бета 0.1.1» maps to the
roadmap's `1.0.0-beta.N` tags is not stated in `R-146l` and is for the integrator to reconcile. The order of the plan: section work and the
removal of v1/v2 first, in parallel with the infrastructure items; `D-204` proceeds in parallel as owner and expert work and does not use code lanes.

## Commitments and their mechanical checks

| # | Commitment | Mechanical check | Exists | Delivered by |
| --- | --- | --- | --- | --- |
| 1 | After the removal an АР version cannot start a v1 run | an integration test: `startRun` on a version confirmed as `AR` answers `422 section_profile_unavailable`; `pytest -q tests/integration/sections/test_routing.py` keeps its test that an unknown code never uses the АР profile | the routing test yes, the 422 test is new | `PROD-11` |
| 2 | v3 no longer imports v2 | `grep -rn "profiles.ar_v2" src` prints nothing | no (30 files name v2 today) | `PROD-10`, `PROD-11` |
| 3 | The contract no longer names `builtin` | `python3 -I -c "import json;print('builtin' in json.dumps(json.load(open('contracts/api/v1/openapi.json'))))"` prints `False` | no (it prints `True`) | `PROD-11` |
| 4 | No profile is silently an АР profile | `grep -rn "AR_TEXT_PROFILE" src` prints nothing | no (six files) | `PROD-11` |
| 5 | A reply naming another model is a typed failure that keeps the usage | `pytest -q tests/integration/analysis_text/test_model_identity.py` | yes | none |
| 6 | The run ceiling is 1.00 USD | `python3 -I -c "import json;print(json.load(open('docs/program/P02_LOCK.json'))['models']['run_cost_ceiling_usd'])"` prints `1.0`; `readiness.sh` `cost-ceiling` is `OK` | yes | none |
| 7 | Production is live on the database source | `infra/deploy/readiness.sh \| grep -E 'readiness OK +(provider-mode\|executor-source)'` prints both lines | yes (the command) | `PROD-13` sets the values |
| 8 | The OpenRouter pin is a probe's reported string | the probe's report names, per pinned model, the requested slug and the reported `model`; `P02_LOCK.json` is written only by that task | no | `PROD-13` |
| 9 | Every non-АР profile is reviewed before the beta | `python3 -I -c "import json,glob;print(sorted(json.load(open(f))['status'] for f in glob.glob('src/auditmanager/analysis/text/profiles/*/profile.json')))"` prints fourteen `reviewed` | no (it prints fourteen `draft`) | `PROD-14` |
| 10 | The АР v3 pack is installed | `python -m auditmanager.runs.v3_pack_cli verify --manifest infra/deploy/ar-v3-pack/<file>` exits 0, and `startArV3BetaGroup` stops answering `dependency_unavailable` | no | `PROD-12` |
| 11 | One worker slot | `ADR-0021` row 12 | yes | none |

## Consequences

### Positive

- One АР path to reason about, test and explain; the recorded v2 code, which nothing can start, stops costing review time.
- The 14 other sections become the product's reviewed core before the beta, and a profile's status says the truth.
- The model identity check keeps one rule for every connection kind.

### Negative / cost

- АР analysis does not exist until `D-204` is finished by people outside the code: until then the production АР product is the empty pack status.
- The product stops detecting internal contradictions and empty placeholders in АР documents.
- The removal touches the contract, `src/auditmanager/runs/executor.py`, 65 test files and the web, and the live journey must change first.
- A strict `model_identity_mismatch` on a provider that reports variant names fails runs after payment.
- A single worker makes the product slow under any concurrent use, with no promise.

## Alternatives considered

1. **Keep v1 for АР beside v3.** Rejected by `R-146g`.
2. **Keep the recorded v2 code as the foundation for later live use.** Rejected by `R-146l`; `git` history keeps it.
3. **Narrow the finding categories in the same reseal.** Rejected (`AD-12`): a migration and a contract change for a list that no registered profile exercises.
4. **An alias list on the run path for OpenRouter's variant names.** Rejected (`AD-13`) for now: it changes the executors settings; reopened if the probe shows variants.
5. **Enforce `allow_client_documents`.** Not decided here (`AD-14`).

## Verification

- automated check/test: the eleven rows above; on the removal lane the tests named in `PROD-11`, with a mutation proof for every new guard
- manual/operational evidence: the paid probe of `PROD-13` (owner-approved), an expert's review of each section profile (`PROD-14`), the reviewer's attestation and
  the pack verification of `D-204`, and the release rehearsal's run of one document per reviewed section through the production connection (`PROD-17`)

## Revisit trigger

Replace this ADR when `D-204` completes and the first real АР documents have been reviewed, when an expert decides that the 14 sections need more than the text
profile, when OpenRouter's reported names make the exact comparison unworkable, when a second worker slot or a service-level objective is wanted, or when the
owner decides to enforce `allow_client_documents` or to accept `R-146n` item 4.
