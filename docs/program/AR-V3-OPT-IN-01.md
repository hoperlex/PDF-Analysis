# AR-V3-OPT-IN-01 — AR v3 as an opt-in mode

**Status: design only.** Written 2026-11-07 by design lane A3 (`agent/lane-ar-v3-optin-01`), base `origin/dev`
`6ce57252a` (product `0.14.0`, API contract `1.36.0`, migration head `0056_optimisation_decisions`). This document changes
no contract, migration, product code, test, AR v3 file, pack, prompt, data or activation state, and ran no model call, stand
or script. Sections 4 to 7 are a proposal until the owner has answered section 9. Sources are cited as `path:line` at the
base commit; what was not verified is in section 10.

## 1. Goal and non-goals

Owner goal of 2026-11-07, item 1 (`docs/program/ROADMAP.md:252-254`): «AR v3 as an opt-in mode. The imported (current)
analysis stays the default; v3 is switched on per deployment or per run, never replacing the default silently.»

Outcomes, each checkable:

1. With no action by anyone, every deployment behaves as it does today: an АР version starts the ordinary text run, and
   nothing on any screen offers or mentions v3 as a way to start.
2. A deployment can **allow** v3 starts. The allowance is explicit, off by default, and separate from installing the pack.
3. Where it is allowed, the expert chooses v3 **per start**, on the start form, with the default pre-selected every time.
4. Every run says which analysis produced it, on the run, in the run list and on the run page. No view mixes the results
   of the two analyses, and no list or counter silently prefers one.
5. Allowance can be withdrawn without killing a run that already started.

Non-goals: activating v3 (pack, snapshot, attestation are `D-204`/`D-247`, owner-run by `scripts/ar-v3/activate-live.sh`,
`R-146be`); changing any v3 prompt, pack, map or data; v3 for a section other than АР; changing `startRun`'s request or the
default profile; an executor choice for v3 (its start takes none); a group rule for counters beyond 4.4 (Q3).

## 2. What exists today (premises)

### 2.1 What «imported» means: the default analysis

- A run's analysis is routed by the **version's persisted, expert-confirmed classification**, never by file name or a
  request field. `startRun` has no field that names a profile: its request carries `version_uid`, `provider_mode`,
  `executor_connection_id`, `preset_id`, `executor_group_id`, `relaxed_limits`, `cost_consent`
  (`contracts/api/v1/openapi.json:27496`, operation `:1866`). The route table is the sealed section-to-profile table the
  composition root loads (`src/auditmanager/runs/commands.py:79-100`, `src/auditmanager/bootstrap/composition.py:593`), read
  in the run-creating transaction by `route_classified_version` (`src/auditmanager/sections/classification.py:370`). No
  classification is `version_classification_required`, a section without a profile `section_profile_unavailable`; there is
  no fallback (`commands.py:85-87`).
- The table is the text-profile registry: 15 packages under `src/auditmanager/analysis/text/profiles/` (`ai ar eom gp itp kj
  km ov pb pos ps pt ss tx vk`), each `profile.json` + `system_prompt.md`, loaded once and immutable
  (`src/auditmanager/analysis/text/profile_registry.py:1-40, 225-285`). 14 of them are sourced from the original
  application: `source.repository` is `PDF-proverka`, with file hashes. `pb` is authored here (`source: null`).
- `status` is `draft` or `reviewed`, and **both are executable**; the status is recorded, not hidden
  (`profile_registry.py:36`). 14 sections are `reviewed`. **АР is `draft`**, profile `1.0.0`, `text-profile/2`, sourced from
  `PDF-proverka` commit `3c99481`, with 7 categories (`.../profiles/ar/profile.json:1-33`).
- АР got this profile on 2026-10-30 (`HOTFIX-AR-ORIGINAL-PROFILE-INT-20261030`, development only); before it `startRun`
  refused АР and the web offered only the six checks (`docs/program/tasks/HOTFIX-AR-ORIGINAL-PROFILE-INT-20261030.md:5, 28`,
  `docs/program/history/CURRENT_STATE_2026-11-03_51183a75.md:196-199`). That reversed `R-146g` «Только v3»
  (`docs/program/OWNER_RULINGS_2026-09-17.md:1765`) in practice; the goal above restates it: imported is the default.
- A run pins its `(analysis_profile_id, prompt_bundle_id)` at creation; the executor resolves that pair, not the section
  (`profile_registry.py:285-292`; `executor.py:986`), and a known idempotency key replays the run with its pinned pair
  (`commands.py:729-740`). Presets are **not** analysis variants: `preset_id` names a saved executor choice (`openapi.json:1871`).

### 2.2 What AR v3 is

- **A different product, not a different prompt.** Six Runs per version (scopes `F1 F2 A1 A2 S1 S2`), each one model call
  over a reviewed norm-retrieval set, ending in a review-only citation stage `ar_v3_citation_review`
  (`src/auditmanager/runs/v3_group.py:45-46`; `src/auditmanager/runs/preflight.py:487` `calls=6`). Output: grounded
  provisional norm citations that an expert can record a verdict on (`R-146as`, `docs/program/OWNER_RULINGS_2026-09-17.md:1803`;
  `src/auditmanager/runs/v3_review_terminal.py:1-10`). It finds no internal contradictions or placeholders (`R-146g` text).
- **Identity.** One sealed pair, `AR_V3_BETA_PROFILE_ID`/`AR_V3_BETA_BUNDLE_ID`
  (`src/auditmanager/analysis/profiles/ar_v3/v3_profile.py:54-57`), in no registry file. The executor takes the v3 branch
  only for that exact pair (`executor.py:935-937, 1221`), and refuses it unless a server-installed pack exists
  (`executor.py:975-984`). A database trigger checks that the six members carry the group's pinned pair and a distinct set
  (`db/migrations/versions/20261023_0032_ar_v3_run_group.py:68-80`).
- **Own operations**, expert-only (`src/auditmanager/api/security.py:656-657`): `estimateArV3GroupCost`
  (`openapi.json:22252`), `startArV3BetaGroup` (`:8559`, body: `version_uid`, `relaxed_limits`, `cost_consent`, `:37541`),
  reads `getArV3BetaGroup`, `getArV3BetaGroupReview`, and `getArV3BetaPackStatus` (`:8764`, any role,
  `security.py:589`). Router: `src/auditmanager/api/routers/ar_v3_groups.py:18-100`.
- **Only АР.** The start refuses another section (`v3_group.py:267`, `preflight.py:458`). It needs the pack's norms snapshot
  to be the current, qualified one (`v3_group.py:290-296`).
- **Web.** The control `web/src/features/start-ar-v3-group` (relaxed-limits toggle, group cost approval, «Запустить шесть
  проверок АР v3»); `/analysis-settings` with map status, pack panel (attestation verbatim) and group review
  (`web/src/_pages/analysis-settings/ui/analysis-settings-page.tsx:33-48`); the run page branches on the pinned profile id
  (`web/src/widgets/run-progress/ui/run-progress.tsx:185, 456-457, 567-576`; `web/src/entities/audit-run/model/run-presentation.ts:51, 162-166`).
  **The run list has mounted no v3 control since 2026-10-30** (`web/src/widgets/run-list/ui/run-list.tsx:17-18`) and a test pins
  that (`web/tests/unit/analysis-settings/run-list-ar-v3-live.test.ts:1-15`): v3 is reachable by API only.
- **`SHOW_REVIEW_INDICATION`** (`web/src/shared/config/review-indication.ts`) is one `false` constant that hides the
  «not reviewed by a human» strings (`R-146ba`, `A-10`/`A-11`, `PRODUCTION-READINESS-PLAN-01.md:245-246`). Wording only.

### 2.3 What «activation» changes

Activation is **data and host configuration, not a code switch** (`D-204`, `docs/program/DEBT_REGISTER.md:121`;
`docs/program/AR-V3-BETA-ACTIVATION-RUNBOOK-01.md:3-6`). It is: the qualified norms snapshot imported and designated
current; six reviewed maps promoted to six verified retrieval sets; `v3_pack_cli seal` writing a manifest with the
attestation; the manifest mounted read-only and named by `AR_V3_BETA_PACK_MANIFEST` in `alpha.env`; `up -d` for `api` and
`worker` (`docs/program/AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01.md:88-118`). No DB row, profile status or registry entry is
flipped. The variable is read at start-up (`composition.py:160-186, 403, 576`); a bad file refuses start, an absent one
means no pack. Per the register at base no deployment has a pack (`D-204`, `D-247`); not verified on any host.

### 2.4 What is switchable now

| Level | Mechanism | What it controls | Anchor |
| --- | --- | --- | --- |
| Deployment | `AR_V3_BETA_PACK_MANIFEST` | the **capability** (pack installed) and, as a side effect, the **permission** to start | `composition.py:160-186`, `compose.server.yml:291, 384` |
| Deployment | none | whether starting is *allowed* | gap |
| Run request | none | `startRun` cannot name an analysis; v3 is a different operation; profile `status` is recorded only | `openapi.json:27496`, `profile_registry.py:36` |

### 2.5 What can silently change the default once a pack is installed

Today nothing does, only because no pack is installed and no screen calls the v3 start. The code has these exposures, in
order of weight:

- **F1. «Newest published run» ignores the analysis.** The audit state of a document (dashboard counters, document chip)
  takes `DISTINCT ON (version_uid) ... ORDER BY created_at DESC, run_id DESC` over every `published`/`partial` run
  (`src/auditmanager/dashboard/audit_state.py:123-130`); the schedule repeats the rule (`src/auditmanager/schedule/service.py:109-112`);
  version comparison and optimisation take the newest published run unless the caller names one
  (`src/auditmanager/comparison/service.py:15, 596-606`; `src/auditmanager/optimisation/project_match.py:211-219`;
  `src/auditmanager/optimisation/section_specification.py:529`), reading every run of the version
  (`src/auditmanager/bootstrap/adapters.py:4262-4269`). One published v3 member run would replace the default run as «the
  result» of the version in all four. The group rule is deliberately undecided (`audit_state.py:26-28`; `R-150t`, `Q-MD-9`, `D-303`).
- **F2. `reauditRun` of a v3 member starts a standard run.** It re-routes by the section now, not by the source's profile
  (`commands.py:1130-1135`), so «repeat this run» on a v3 member silently becomes the other analysis. The queue offers the
  button for any terminal job (`web/src/entities/execution/model/presentation.ts:21-23`).
- **F3. The starter is not recorded for v3 members:** the group start's `runs.create` passes no `started_by_user_uid`
  (`v3_group.py:366-373`; the ordinary start does, `commands.py:880`, `R-151v`), so «кто запустил» is empty.
- **F4. The pack is the only brake on starting,** and withdrawing it kills in-flight v3 runs (the worker refuses them,
  `AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01.md:124-125`): new starts cannot be stopped while running ones are kept.
- **F5. Nothing on a standard run or in the run list names the analysis;** only the v3 page branches on the id
  (`run-table.tsx:1-35`; `run-progress.tsx:185`).

Not an exposure, checked: the default path cannot produce a v3 run. `startRun`/`reauditRun` route through the registry,
which has no v3 entry, and `startArV3BetaGroup` is a separate command type (`v3_group.py:45`) with its own key namespace.

## 3. The gap to the goal

Default stays imported: true for the start, but F1 and F2 can displace its *result* once v3 runs exist. On per deployment:
the pack variable fuses capability and permission, with no way to stop starts and keep running work (F4). On per run: API
only, no UI since 2026-10-30. Never silently: no analysis label on any run (F5) and no starter on v3 runs (F3).

## 4. Design

### 4.1 Principles

1. **Two layers, default off.** Capability (pack, unchanged) and permission (new allow switch). Both needed to start;
   only the pack is needed to execute, read or review.
2. **The choice is an operation, not a flag on the default.** v3 stays its own operation. `startRun` and `reauditRun`
   gain no field and no code path to v3, so the default path cannot be changed by a client mistake or a default.
3. **The choice is never remembered.** The form opens on the standard analysis for every version and visit; nothing is
   stored per user, project or browser; one start sends exactly one analysis's operation.
4. **No fallback in either direction.** A refused v3 start is never retried as a standard one, nor the reverse
   (`AGENTS.md` section 4; the existing control already says so, `start-ar-v3-group-control.tsx:12-14`).

### 4.2 The deployment switch

`AR_V3_BETA_START_ALLOWED`, read by the composition root next to the pack (`composition.py:160-186`), **api only**.

| Value | Meaning |
| --- | --- |
| absent, blank, `0` | v3 starts and estimates are refused. **The default.** |
| `1` | allowed, if a pack is also installed |
| anything else | `ConfigurationError` at start-up (strict parse, like `settings.py` `_worker_slots`); never read as «on» |

Rules: `1` without a pack changes nothing visible; the pack alone no longer allows a start. The `worker` service does not
read the variable, so it executes what was accepted (`compose.server.yml:299, 386`; `executor.py:975-984` gates on the pack
only). The value is logged once at start-up, with the pack state.

Why an environment variable first: the pack already lives there, it needs no migration or admin screen, and the owner's
chosen live path edits `alpha.env` (`R-146be`). The runtime alternative (an admin operation with a journal; precedent
`setExecutorRoutingMode`, `openapi.json:7498`, `db/migrations/versions/20261102_0047_executor_groups_rules.py:47-53`) is
phase 5 and question Q2. No per-project or per-user allowance: the owner said «per deployment or per run».

### 4.3 The per-run choice

Shown **only** when all hold: the version is classified АР (`sectionCode === 'AR'`, already passed to the list,
`run-list.tsx:46, 70`), the version is not comparison-only, and `getArV3BetaPackStatus` reads `state: installed` with
`start_allowed: true` (section 5). Otherwise the form is byte-for-byte today's form: no radio, no sentence, no link.

The form gains a radio «Анализ»:

| Option | Default | Sends | Form below |
| --- | --- | --- | --- |
| «Стандартный» (АР profile from the original application) | selected on every open | `startRun` as today | today's executor/preset/group choices, estimate, consent |
| «АР v3: шесть проверок по нормам (бета)» | never | `startArV3BetaGroup` | v3 block: relaxed-limits toggle, group estimate, consent, button |

Choosing v3 **hides** the executor, preset and group selectors: the group start takes none and runs on the global route
(`StartArV3BetaGroupRequest`, `openapi.json:37541`; `v3_group.py:214-226`), so showing them would promise a choice the
server ignores. The sentence under the button says what v3 returns (six separate runs, norm citations, no numerical
conclusions, current wording in `start-ar-v3-group-control.tsx`) and that the standard result is a different one which this
start does not replace. Changing the radio clears the other branch's estimate, consent and failure. The idempotency key
stays per intent, and the two analyses are different command types, so a retry cannot flip the analysis
(`v3_group.py:45, 173-186`). The v3 control is reused as is (`useArV3GroupStartIntent`, `useArV3CostApproval`); the run list
mounts it again, only inside the allowed branch, and the 2026-10-30 pin test is replaced deliberately (section 6).

### 4.4 Provenance: a result always says which analysis produced it

On the run: already stored are the pinned pair, `norms_snapshot_id`, `norm_retrieval_set_id` (`openapi.json:27627`), and in
the group row `pack_sha256`, `composition_sha256`, `policy_sha256`, `provider_mode` (`v3_group.py:325-340`). Proposed:

1. **Record the starter** on v3 members: pass `started_by_user_uid` in the group start (`v3_group.py:366-373`; the router
   already holds `subject.user_uid` and passes it as the cost actor, `ar_v3_groups.py:42-47`). No migration: the column exists (`R-151v`).
2. **`RunStatus` gains three optional, additive fields:** `analysis_kind` (`standard` | `ar_v3_beta`, derived by the adapter
   from the pinned pair, the one definition already in `providers.py:104-109`), and for members `ar_v3_group_id`,
   `ar_v3_scope_id` (read from `ar_v3_run_group_member`). The client stops comparing profile ids by hand
   (`run-presentation.ts:51`).
3. **One definition of «the result of a version».** The newest published/partial run **of the standard analysis**
   (pinned pair is not the sealed v3 pair): in the two SQL statements (`audit_state.py:125-129`,
   `schedule/service.py:109-112`) and in the adapters behind `runs_newest_first` that serve comparison and optimisation
   (`adapters.py:4262, 4438, 5771`). One predicate, four consumers, a test per consumer (section 6). This is the proposed answer to `Q-MD-9` for counters; the alternative is owner question Q3.
4. **Comparison and carry-over:** a run **named by the caller** that is a v3 member is refused as a comparison refusal
   `analysis_not_comparable` (a new member of the response enum `ComparisonRefusal.reason`, with its side;
   `models.py:3270-3290`, `openapi.json:25795-25810`, web sentence table `web/src/entities/document-version/model/comparison.ts:49`),
   because the findings of the two analyses are not the same kind of object. It sits beside the existing `run_not_published`
   refusal (`comparison/service.py:596-604`); carry-over recomputes the comparison, so it inherits it (to confirm in P1).
   Owner question Q5.
5. **`reauditRun` of a v3 member** is refused with `409 conflict` (`ar_v3_member_not_repeatable`) before the key is claimed;
   the repeat of v3 is a new group start from the form. Owner question Q4. Nothing else about `reauditRun` changes.

### 4.5 Consent and cost

AR v3 is six paid calls, one per scope (`preflight.py:487`, `calls=6`; `D-225`). Nothing new is invented:

- The gate stays (`require_cost_consent=True`, `composition.py:595`, pinned by
  `tests/unit/bootstrap/test_composition_pins_the_cost_consent_gate.py`). The group start uses the same estimate-then-consent
  protocol: `estimateArV3GroupCost`, `RunCostConsent` with a ceiling shared among the six runs (`v3_group.py:342-363`, `adapters.py:1306`).
- A consent is bound to the estimate's digest, and the group estimate's `scope` is `ar_v3_group`, the single run's `run`
  (`preflight.py:428, 487, 93-94`), so a consent given for the standard estimate is refused by the v3 start
  (`409 conflict / run_cost_estimate_stale`); the form also clears it when the radio changes.
- While v3 is chosen the form shows only the **group** figure and says «шесть платных вызовов». The allowance is not
  consent: allowed means offered, never pre-approved, and no ceiling is stored per deployment. `estimateArV3GroupCost` is
  refused like the start when the allowance is off.

### 4.6 What the web shows

| Where | Allowance off (default) | Allowance on |
| --- | --- | --- |
| Start form of an АР version | today's form, unchanged | + radio «Анализ» (4.3) |
| Run list (`run-table.tsx`) | unchanged | + chip in the state cell: «Стандартный» or «АР v3 · F1» (from `analysis_kind`); a v3 row links the group review |
| Run page | unchanged for standard; v3 page as today | + a line «Анализ:» on both kinds, from the same field |
| `/analysis-settings` pack panel | pack state, attestation (as today) | + one line «Запуск АР v3: разрешён / не разрешён на этом сервере» for every role (read-only) |

Wording: nothing says the standard analysis is replaced, superseded or discouraged; the label «АР v3 (бета)» says nothing
about human review, so it does not collide with `SHOW_REVIEW_INDICATION = false` (`R-146ba`); a new «not reviewed /
provisional» string goes behind that constant (`web/tests/guards/review-indication.guard.test.ts`). Question Q6.

### 4.7 Turning it off safely

Procedure for the operator: set `AR_V3_BETA_START_ALLOWED` blank or `0` in `alpha.env`, then `up -d --no-deps api`
(`restart` re-reads no environment, `AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01.md:118`).

| Thing | After the switch is off |
| --- | --- |
| New `startArV3BetaGroup` / `estimateArV3GroupCost` | `409 conflict / ar_v3_start_not_enabled`; no command, run, group or Job written |
| A retry of an **accepted** key | replays the existing group, as it already does after pack withdrawal (`v3_group.py:234-245`); the new check sits after that branch |
| Runs queued or running on the worker | **finish**: the worker does not read the variable, the executor gates on the pack only (`executor.py:975-984`) |
| Group review, findings, verdicts, exports | unchanged (they read the database); the form loses the radio at the next status read |

Recreating only `api` leaves the worker's runs alone because the compose `api` claims nothing (`EXECUTION_ROLE: api`,
`compose.server.yml:299`; `carrier.py:387-396`). Where `EXECUTION_ROLE=all` the api process executes runs itself, so
recreating it interrupts them as any restart does; the runbook must say so. **Withdrawing the pack stays a separate, heavier
act** with its caveat unchanged (it ends in-flight v3 runs); the runbook's rollback section is rewritten to say «to stop v3,
switch the allowance off; withdraw the pack only when no v3 run is in flight».

### 4.8 What must never happen, and what holds it

| Never | Mechanism |
| --- | --- |
| A default, preset, batch dialog, re-audit or script starts v3 | v3 is only `startArV3BetaGroup`; `startRun`/`reauditRun` gain no path to it; test: the default start, pack installed and allowed, pins the registry АР pair |
| v3 starts because a pack was installed | the separate switch, default off; test: pack installed, switch absent -> 409, nothing written |
| The default's result displaced by a v3 run | one «result run» predicate restricted to the standard analysis (4.4.3), a test per consumer |
| One run holding two analyses; a silent switch on retry | the pair is pinned at creation and checked by the DB trigger (`0032:68-80`); different command types; `reauditRun` of a member refused (4.4.5) |
| A consent for one price funds another | digest- and scope-bound consent (4.5) |
| A remembered choice, a v3 default for a person, a fallback either way | nothing stored (4.1.3); test: remount -> standard; the existing v3 control offers no single-run substitute |
| Switching off kills a running v3 run | the worker is independent of the switch (4.7) |

## 5. Contract slice, migration, composition

One contract-owner slot, **minor bump to `1.37.0`**, additive only; no new operation, no new status code (both v3
operations already declare 409, `ar_v3_groups.py:18-47`).

| Item | Change | Anchor |
| --- | --- | --- |
| `ArV3BetaPackStatus` | optional `start_allowed: boolean`, present exactly when `state` is `installed` (the schema already omits all else when not installed) | `openapi.json:37871`, `api/schemas/models.py:1637-1644`, `adapters.py:1345-1361` |
| `RunStatus` | optional `analysis_kind` (`standard`, `ar_v3_beta`); optional `ar_v3_group_id`, `ar_v3_scope_id` (members only) | `openapi.json:27627` |
| `startArV3BetaGroup`, `estimateArV3GroupCost` | text: refusal `409 conflict` with `conflict_reason` `ar_v3_start_not_enabled` | `openapi.json:8559, 22252` |
| `reauditRun` | text: `409 conflict` with `conflict_reason` `ar_v3_member_not_repeatable` (409 already declared) | `openapi.json:3727` |
| comparison read | response enum `ComparisonRefusal.reason` gains `analysis_not_comparable`; the web's exhaustive sentence table gains one line | `openapi.json:25795-25810` |
| `contracts/domain/v1/error-codes.json` | the two conflict reasons in the `conflict` code's prose (the catalogue lists reasons in prose); no new code | `error-codes.json:205-210` |
| Generated client and lock | regenerate; `npm --prefix web run api:verify` | `web/openapi/openapi.json`, `web/FRONTEND_LOCK.json` |

**Migration: none.** Head stays `0056`. The starter column and the member table exist. (Phase 5 would add one.)

**Composition and ops** (shared hotspots: contract, composition root, compose; one owner per wave, `AGENTS.md` section 3):
`composition.py` (read and log the variable, pass `start_allowed` on); `adapters.py` (group start/estimate/status and the
three `runs_newest_first`); `v3_group.py` (a `start_allowed` argument checked after the replay branch; the starter);
`preflight.py:453` (estimate refusal); `infra/deploy/compose.server.yml` (variable on `api` only, near `:291`);
`infra/deploy/env/alpha.env.example` (beside `:307-315`, default blank); the rollback section of
`AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01.md`.

## 6. Tests

Each guard has a mutation case that turns it red (as `test_composition_pins_the_cost_consent_gate.py` does).

- **Unit:** strict parse (absent/blank/`0` off; `1` on; `true`, `2`, ` 1x` -> `ConfigurationError`); the «newest standard
  result» predicate; `analysis_kind` from the pinned pair.
- **Integration, real database** (fakes missed real breakage before, `D-225`): pack + switch off -> `409` and zero rows in
  `command`, `audit_run`, `ar_v3_run_group`, no Job; switch on -> `202`, six queued runs with the starter; an accepted key
  replays with the switch off; `startRun` for an АР version is identical in both states; a published v3 member does not
  change the counters, the schedule, the default comparison pick or the optimisation pick of a version with a published
  standard run (one test per consumer); `reauditRun` of a member -> `409`, nothing written; a consent from
  `estimateRunCost` is refused by `startArV3BetaGroup`; the worker executes an accepted group with the switch off.
- **Contract:** the seal tests for `1.37.0` (`tests/contract/api_v1/test_contract_seal.py` family); the reasons in the
  catalogue prose; `start_allowed` absent when not installed.
- **Web:** `start_allowed` false -> no radio and no v3 string in the markup; true -> standard preselected, choosing v3
  swaps button and cost block and clears consent, remount returns to standard, no storage write; chip and run-page line
  from `analysis_kind`; the settings line for a viewer; the review-indication guard stays green. The 2026-10-30 pin becomes
  «the run list mounts the v3 control only when the status allows it», with its mutation case.
- **Journey (recorded mode, throwaway stand):** off -> no choice; on -> v3 -> six runs -> default run and counters intact
  -> switch off with a group in flight -> it finishes. The live provider call stays in `AR-V3-BETA-ACCEPT-01`.

## 7. Phases and sizes

| Phase | Content | Size | Depends on |
| --- | --- | --- | --- |
| P1 | Keep the default's results the default: the one «result run» predicate (4.4.3) in four consumers; starter on members; `reauditRun`/named-run refusals (4.4.4-5). Needs Q3-Q5. Visible only once v3 runs exist, so safe to land first | M | answers Q3-Q5 |
| P2 | Deployment switch and contract `1.37.0`: variable, refusals, `start_allowed`, `RunStatus` fields, compose/env/runbook, settings line | S | P1 not required; shares `adapters.py` with P1, so one lane or sequential |
| P3 | Web: the radio and reuse of the v3 control, chip and run-page line, pin-test replacement | M | P2 (client regeneration) |
| P4 | Acceptance: the journey above on a throwaway stand; live acceptance stays with the activation wave | S | P1-P3; live part also `D-204` |
| P5 (optional) | Runtime admin toggle: operation, event journal, migration `0057+`, admin control; replaces the variable as the source | M | Q2 |

About three lanes (P1+P2, P3, P4); none activates v3. The roadmap puts the owner goals after the beta-bound work
(`ROADMAP.md:247-250`); P1 is a defect-in-waiting more than a feature.

## 8. Risks

1. **The analyses are not comparable results.** The standard one finds internal contradictions and placeholders; v3 cites
   norms and finds neither (`R-146g`). A person may read «v3» as «better»: labels and the radio sentence say they differ.
2. **Counters hide v3 work** (the price of 4.4.3): a document whose only result is a v3 group shows `not_run`; the
   alternative is the group rule of Q3, a design of its own.
3. **The pack is tied to one snapshot.** A new snapshot designated current makes every v3 start refuse until a new pack is
   sealed (`v3_group.py:290-296`), so an allowed switch can show a control that fails; the form already words the refusal
   (`start-failure.ts`), and the status could say so too (not designed).
4. **The environment switch needs an operator** and `up -d`; Q2/P5 is the mitigation.
5. **Activation data is still owed** (`D-204`; expert attestation under `A-10`/`A-11`); P1-P3 do not remove that, and live
   acceptance would be on synthetic documents (`R-146bb`).
6. **The v3 start takes no executor selector** and runs on the global route (`v3_group.py:214-226`); a deployment that
   routes by rules or groups (`EXEC-2`) cannot send the six runs to a chosen executor. Out of scope here.
7. **Hotspots** (contract, composition root, compose file) are shared; P1 and P2 both touch `adapters.py`.

## 9. Questions only the owner can decide

Each has a recommendation; the design is built on the first option unless stated.

- **Q1. What does «per deployment» mean?** (a) the deployment **allows** v3 and each start chooses (recommended); (b) it may
  also **declare v3 the default** for АР so the form opens on v3 (a third value of the variable: an explicit, labelled
  replacement on that server only, which «never silently» permits, but P1's rules would then run the other way round).
- **Q2. Where does the switch live?** (a) an environment variable edited on the host, applied by `up -d --no-deps api`
  (recommended first: no migration, no screen); (b) an admin toggle in the product with a journal (phase 5: a migration,
  one operation, one control; no host edit).
- **Q3. Counters (`Q-MD-9`, `D-303`).** (a) dashboard, schedule, comparison and optimisation consider only the standard
  analysis (recommended); (b) a v3 group counts as one unit by a rule to be designed; (c) the newest of any kind (today).
- **Q4. `reauditRun` of a v3 member.** (a) refuse, repeat by a new group start (recommended); (b) start a new group;
  (c) keep today's behaviour (a standard run).
- **Q5. Comparison and carry-over across analyses.** (a) refuse a v3 member as a named run (recommended); (b) allow it
  with a visible label.
- **Q6. Wording.** May the v3 label be «АР v3 (бета)» with no human-review wording while `SHOW_REVIEW_INDICATION` stays
  `false` (`R-146ba`), or should the radio carry the «требует проверки эксперта» sentence from the start?
- **Q7. When.** Build P1-P3 now, switched off, so that activation (`D-204`) is later only data; or after the beta-bound
  work, as the roadmap orders (`ROADMAP.md:247-250`).

## 10. Not verified

- Nothing was run (no test, stand, container, model call or script); all behaviour is read from code at the base commit.
- That recreating `api` alone leaves worker runs untouched in a deployed compose project is read from the compose file and
  the executor gate, not exercised (the runbook states the same limit for its own cases, `OWNER-STEPS-01.md:143`).
- The four «newest run» consumers come from grepping `DISTINCT ON`, `ORDER BY created_at DESC` and `runs_newest_first`;
  another reader of `list_for_version` may exist. P1 starts by repeating the search. Which of the six members the current
  rule would pick (all share one accepting transaction) was not executed.
- No host's pack state, `alpha.env` or snapshot was read; «no pack anywhere» is the register's statement. Phase sizes are
  by analogy with neighbouring lanes, not measured.
