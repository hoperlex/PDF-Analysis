# Wave 56 — split: W56a AR-2 on text; W56b drawings, long documents and the critic

> **Development order, 2026-10-15:** `CODE-FIRST-TO-BETA.md` governs checks
> and publication for code-first work. W56a/W56b retain their functional scope
> and ownership boundaries; per-lane full gates, stand acceptance and `main`
> release tasks below are deferred. The stopped W56a gateway probe is not a
> passing model pin; use the recorded-only split described in the amendment
> before issuing code grants.

**Status:** revision 3 (final), 2026-10-06 — after the second judging round (`reviews/W56-PLAN-JUDGING.md`;
both judges ACCEPT-WITH-FIXES, no third round) and the owner's answer H-10 (the critic moves to W56b). Written by the planning session on local branch
`plan/roadmap-to-beta`. Two rounds at most (`R-V4`).
**Controlling answers:** `ROADMAP-TO-BETA.md` §10.1 (A-6…A-8), §10.13 (G-3, G-7, G-8, G-11) and §10.14
(H-1…H-10). Research: `reviews/W56-RESEARCH.md`. `W56A-RULE-01` records those answers as
`R-129`…`R-134` on its W55b candidate base; the integrator checks numbering again before merge.
**The wave is two waves (H-1).** Part A (W56a) is planned here in full and is dispatchable after
`W55B-INT-CLOSE`. Part B's original scope is retained below for history; `W56B-PLAN.md` (from the unadopted
2026-10-08 layer, `ROADMAP-TO-BETA.md` §10.16 K-4: preserved, not reviewed or adopted) is a draft of its
pre-freeze planning graph. It becomes dispatchable only after the W54/W55 vision probe,
W57b close and its own owner rulings/freeze.
**2026-10-14 owner amendment:** `W56A-RULE-01` may record the already-given decisions during
W55b acceptance. Freeze and implementation remain behind `W55B-INT-CLOSE`. `R-124` replaces
W56a's QA/two-judge/notes-judge sequence with one whole-wave judge and FIX; `R-126` defers
backend database suites to the final gate. `R-102` continues to put one full gate on the final
candidate, not on individual lanes. The task requirements below are read under these rulings.
**Releases:** W56a `v0.7.0`, W56b `v0.9.0`. *Amended 2026-10-07 (owner's answer I-12, `ROADMAP-TO-BETA.md`
§10.15):* W57a (`v0.8.0`) and W57b (`v0.8.1`) follow W56a, and W56b follows W57b; W56b's own plan bases on
W57b's close.
Normal main/tag releases consume actual deployed/tagged predecessor evidence and their own
exact-SHA validation under `ROADMAP-TO-BETA.md` §8.4. A code-only predecessor does not license
the next hard-coded note/version; bundled history needs an earlier owner-ratified amendment.
The same code-first exception permits W56a implementation on `origin/dev` with
focused-check and D-139/D-140 records, not a `v0.7.0` release verdict. W56b's
dedicated plan applies the same distinction after W57b.
**`contract_version` does not move in W56a** (W52: unchanged until the beta freeze); every addition is an
optional property or a new enum value.

---

## Part A — W56a: AR-2 on text (`v0.7.0`)

### A1. Objective

- **Profile АР v2** with seven categories: v1's two plus dimensions, layout, facade, roof and
  documentation, each asked as a question of **consistency and completeness, never of norm compliance**
  (H-2).
- **Severity** on five levels — the model **proposes**, the expert **decides** when accepting (H-3).
- **Deterministic `finding_merge`** (H-4). The critic is W56b's (H-10).
- **Recognised text** from W55b as marked context for pages without a text layer; citations stay
  text-layer only (H-7).
- **A quality gate on recorded responses** that refuses regression; beta thresholds are the owner's at W58
  (H-5); a seeded-corpus **generator** for the v2 categories (A12).
- **Model identity:** a live response from another model than the configured one is refused (H-6).
- The owner reviews v2's findings on the portal export in the product after the release (H-8).
- **Live spend ≤ $5** for the whole wave (`R-29`, H-9). A v2 run has **one paid stage**, so W53's
  single-call execution model (watchdog, resume rule) holds unchanged.

### A2. Where it starts

| Fact | Source |
| --- | --- |
| 9 stages declared; handlers for the 3 deterministic ones; text analysis bound in the executor with `profile=AR_TEXT_PROFILE`; `PC01_STAGES` holds 4 and is pinned by contract tests; the grounding gate reads `analysis.text_observations` directly; the DB already accepts all 9 stage ids | `stage-registry.json`; `analysis/stages/__init__.py:29-49`; `runs/executor.py:484, 530-576, 708-831`; `runs/repository.py:53-58`; `test_narrow_sets_against_contracts.py:102-127`; `0002:102-112` |
| `finding_merge` outputs `findings.merged`, is `central_only`, not model-routed, "partial" without block observations, and `depends_on` includes `block_analysis` (pinned by `run-presentation.ts:241`, `stage-vocabulary.guard.test.ts:124-133`) | `stage-registry.json:494-535` |
| a `finding` table; `finding_observation.finding_uid` already allows many observations per finding, with `grounded = (finding_uid IS NOT NULL)`; queries count observations, return the newest observation by uid, and admit a decision on any observation of the finding; observation ids are allocated in publication | `0002:887-960`; `findings/queries.py:22-40, 75-81, 205-259`; `findings/publication.py:157` |
| the verdict projection is the DB view `finding_current_verdict`, and Python must not hold a second copy | `0002:1198-1235`; `decisions/projection.py:1-20` |
| profile v1 and bundle ids pinned in 58 files; `resolve_profile` refuses any other id; recordings keyed by request checksum, read from `fixtures/recorded/text_analysis` only | `analysis/text/profile.py:30-85`; `text/recorded.py:52-56` |
| categories: two values in the contract, two DB CHECKs, `models.py`, `CATEGORY_LABELS: Record<FindingCategory,string>` in the expert-decision entity, the knowledge-base page's category filter, the finding list, and the rendered-language guard's seeds | `0002:899, 945`; `web/src/entities/expert-decision/model/category-labels.ts:20`; `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx:60-62`; `finding-list.tsx:44-52`; `rendered-language.guard.test.ts:1359-1367, 1704-1724` |
| decisions: `appendDecision` (`event_type`, `finding_observation_id`, `comment`); no severity anywhere | `openapi.json`; `api/routers/decisions.py:88-99`; `bootstrap/adapters.py:708` |
| CSV: 17 frozen columns pinned in eleven places (§A4 DECIDE) | `P02_SEAMS.md` §6; research; grants judge |
| the proxy response's model is not read (`_from_openai_response`; `ModelResponse` has no model); `PROXY_LLM_MODEL` defaults to the stub `proxy`; the stand uses the agent gateway (`W48-PROXY-01`, `63cb3ca`) whose default model is not Claude | `text/proxy.py:20-48, 203-223`; `text/adapter.py:52-66`; `bootstrap/settings.py:167-176` |
| seeded corpora: АР baseline and PC-02 (9 seeded, 64 controls); PC-02 measured 9/9 recall, 1/64 controls, $0.013–0.019 per call (≈ 2.5k tokens) | `fixtures/validation/PC-02/`; `artifacts/validation/PC-02/baseline/ledger.json` |
| the gate recipe is pinned literally (`gate: foundation`) | `Makefile:1040`; `tests/contract/test_alpha_acceptance_command.py:36` |

### A3. Design

**A3.1 Profiles and stage plans.**
- A minimal **profile registry** (`src/auditmanager/analysis/profiles/**`, the seed of W59's S0): v1 and
  v2, each with id, prompt bundle, response schema, category set and **stage plan**. v1's plan is
  `PC01_STAGES`, unchanged; v2's is the three deterministic stages, `text_analysis`, `finding_merge`.
- **Which profile a new run uses** is the setting `AUDITMANAGER_ANALYSIS_PROFILE_ID`, read by `startRun`
  and, under `R-82`, by `reauditRun`; the run row records the profile (already in `frozen_input_digest`), and the executor takes
  the stage plan **from the run row**, never from the setting. Its documented default for development and
  tests is v1, so the suite, its recordings and the characterization records stay unchanged
  (`tests/conftest.py` scrubs the name like the provider settings); the stand's `readiness.sh` refuses it
  unset and `INT-MAIN` sets v2. The setting is declared in `bootstrap/settings.py` and delivered through
  **one channel only**, `infra/deploy/env/provider.env.example` (the `api` service's `env_file`); compose's
  `environment:` block does not name it, so nothing shadows it. `bootstrap/composition.py` resolves it
  where it resolves the profile today. *Amended 2026-10-12 (`R-82`):* a re-audit runs on the
  **current** profile, prompt bundle and provider mode, and records the configuration it actually used;
  the source run is linked only by `reaudit_of_run_id` (`reviews/W54-W57-CHAIN-REVIEW.md` CD-6). The
  earlier rule — "a re-audit keeps the source run's profile (the same frozen inputs)" — is withdrawn,
  and `W56A-PROFILES-01`'s grant takes the re-audit path in `runs/commands.py` (re-swept at the freeze).
  W56b's presets replace the setting (A-8); the model, absent from the digest today, enters with them.

**A3.2 Categories and severity (H-2, H-3).**
- `FindingCategory` gains `dimensions`, `layout`, `facade`, `roof`, `documentation` (names final at the
  seal; Russian labels from legacy); 0022 widens the two CHECKs by `ALTER` and leaves `0002` untouched.
  The v2 prompt asks only about agreement between sheets, tables and notes, missing or contradictory data
  and drawing-set completeness; checklist items that need a norm are excluded and listed for W57.
- `Severity` ∈ `critical`, `economic`, `operational`, `recommendation`, `check_adjacent`.
  `FindingObservation.proposed_severity` (v2 only); a finding's proposed severity is its canonical
  observation's.
- `AppendDecisionRequest.severity` is accepted only with an `accept` event (DB CHECK
  `severity IS NULL OR event_type = 'accept'`). **Decided severity** = the severity of the latest
  verdict-bearing event when that event is `accept`, otherwise null — so an accepted-then-rejected finding
  shows none. 0022 redefines the `finding_current_verdict` view; the fold `rebuild_current_verdict` follows.
  `Finding.decided_severity`, `DecisionEvent.severity`, `DecisionRecord.severity` and the `FindingDetail`
  restatements are optional. The decision panel **never pre-selects** the proposed value.
- **v1 byte-identity:** every new property is **absent, never null**, on v1 findings, events and records;
  characterization records 03–11 do not change.
- **CSV (OD-11 amended):** `severity` (decided) and `severity_proposed` appended; one row per evidence item
  of the **canonical** observation (merged members are visible in the product; members in the export are
  registered for W57's Excel export).

**A3.3 Deterministic merge (H-4).**
- v2 order: `text_analysis` → the grounding gate (unchanged; ungrounded observations are never merged or
  published) → `finding_merge` → publication.
- **Rule**, over the grounded observations' ordinals in the run's artefact (ids do not exist before
  publication): observations *a* and *b* are **linked** when they share a category **and** either some
  evidence span of *a* overlaps some evidence span of *b* on the same page, or some normalised quote of *a*
  equals one of *b* on the same page with at least 20 characters (normalisation: NFC, case folded,
  whitespace collapsed). **Groups are the connected components** of the links (union-find). The canonical
  member has the smallest (page, `char_start`) over its evidence items, then the smallest ordinal. Output
  `findings.merged` (the existing role): groups of ordinals and the rule's version.
- **Publication:** members carry the group's `finding_uid` (the existing column); 0022 adds a **nullable**
  `finding.canonical_observation_id` with a composite foreign key (`finding_uid`, `canonical_observation_id`)
  against a new UNIQUE pair on `finding_observation`, so the canonical belongs to its finding; the backfill
  asserts exactly one grounded observation per existing finding and sets it. Publication inserts the
  finding, then its observations, then sets the canonical by an `UPDATE` in the same savepoint (until MERGE
  merges, the column stays NULL on new findings and nothing reads it). Counts are distinct findings;
  `getFinding` and the finding list return the canonical observation; `Finding.merged_observations`
  (optional) lists the others; a decision naming a non-canonical observation is refused with
  `validation_failed`, constraint `canonical_observation_required` (today's `not_found` would be false for a
  member).
- The registry's "partial without block observations" applies only when the run's stage plan contains
  `block_analysis`; `finding_merge.depends_on` is not changed.

**A3.4 Profile v2 content.**
- Ported legacy data (A8) — `prompts/disciplines/AR/{finding_categories,checklist,role,drawing_types,project_params}.md`
  and `backend/app/data/discipline_checklists/AR.md` (22.8 KB) — as reviewed files under
  `src/auditmanager/analysis/profiles/ar_v2/` with a provenance header (legacy path and SHA-256); the lane
  report reviews them item by item and lists every excluded norm item.
- Response schema: category (7), finding text, recommendation, `proposed_severity`, evidence
  `[{page_number, quote}]` — quotes verbatim from the text layer.
- **Recognised text (H-7)** goes into the prompt **only for pages without a usable text layer** — the
  version's `textless_pages`, decided once at upload by W55b's per-page pypdfium2 count against the
  threshold W55b's freeze pins, so the budget and the prompt select the same pages — under a marked section («распознанный текст — не цитировать») with its quality flags; portal descriptions never
  (G-7). A quote found only in recognised text is ungrounded with a new reason
  `quote_in_recognised_text`, counted in the evaluation.
- **Input budget:** v2's budget counts text-layer characters, the recognised characters of text-less pages
  (stored at upload by W55b — §A9) and the prompt's overhead; a NULL recognised count is 0 only for a
  version without a recognised artefact (a pre-W55b upload).

**A3.5 Model identity and provider errors (H-6).**
- The adapter reads the response's `model` field (the field is pinned at the freeze) into `ModelResponse`.
  The gateway's name for each locked model is a field inside its `models.<tier>` entry of `P02_LOCK.json`,
  so the model set its tests pin is unchanged; `analysis/text/lock.py` stays the only reader. A response in
  **proxy mode** (`AUDITMANAGER_PROVIDER_MODE=proxy`) whose model does not match is a typed stage failure
  `model_identity_mismatch`; nothing is published. Recorded responses are already bound to the request
  body, model included, by `request_sha256`.
- Proxy mode refuses at start-up a stub `PROXY_LLM_MODEL`, and any `PROXY_LLM_MODEL` that is not the gateway
  name pinned for `AUDITMANAGER_MODEL_ID` (otherwise every call would be paid and then refused).
- **The freeze's identity probe** runs on each gateway (the recording one here and the stand's), two calls
  each: (1) the configured model — the reported name must equal its pinned gateway name **and** the
  reported `usage.cost` per token must match the model's pinned rates (opus $5/$25, sonnet $2/$10 per MTok)
  within a tolerance the freeze states; (2) the stub or the gateway's default — the reported name must be a
  concrete model that is neither the stub nor the configured name. An echo fails the price in (1) or fails
  (2); either is a stop for that gateway. Both signals are recorded per gateway.
- `D-133`, if still open at the freeze: proxy non-answers (403, 402, 404, 5xx) get their own failure class;
  the stage's typed error message appears in `RunStatus` and on the run page; the proxy's error body is
  logged server-side, bounded and redacted, never stored where the API serves it.

**A3.6 Generator, quality gate, live mode (A12, A9, H-5).**
- **Generator** `tools/fixtures/seeded/**` (new): parameterised by profile, category and control archetype,
  reusing `tools/fixtures/ar_corpus/` primitives and W55b's bundle writer; emits PDF, portal bundle and
  `expected_issues.json`. The **v2 corpus** (`fixtures/evaluation/ar_v2/`): ≥ 3 seeded issues per category
  and near-miss controls per category over ≈ 10 documents; byte-stable regeneration. The PC-02 and
  АР-baseline builders stay (registered for consolidation).
- **Matcher** promoted into `tools/evaluation/**`: protocol §11 rules, vacuity self-proofs; a seeded issue is
  found if **any member** of a group matches; over-merge (one group matching two seeded issues) reported;
  per-category recall, control false-positive rate, severity confusion (reported, not gated).
- **The gate:** a pytest module collected by `run_battery` (`tests/integration/evaluation/test_ar_v2_no_regression.py`,
  under `tests/integration/` for its database fixtures, with the module-level `sys.path` insert for `tools`
  that `tests/contract/fixtures_ar/test_determinism.py` uses), so the `Makefile` is untouched: the corpus through the pipeline in recorded mode against
  `fixtures/evaluation/ar_v2/baseline.json`; aggregate recall below, or the control false-positive rate
  above, the baseline fails; per-category figures are reported. Its time is measured and budgeted (≤ 2 min).
- A prompt or profile change needs new recordings and a live re-measure gated on **aggregate** recall with
  a tolerance fixed at the freeze; per-category figures are reported (three seeded issues per category
  move in thirds). Beta thresholds are the owner's at W58.
- **Live mode** `python -m tools.evaluation.live` by command only, with a hard dollar cap and the ledger.
- v2 recordings live in `fixtures/recorded/text_analysis/ar_v2/`, read by the recorded adapter per profile;
  v1's recordings stay byte-identical.

**A3.7 The owner's review (H-8).** At `W56A-INT-MAIN-01` the owner's portal export is analysed with v2 on the
stand; the owner marks each finding in the product. `tools/evaluation/precision_from_decisions.py` reads the
run's findings and their decisions through the API (`listRunFindings` with the verdict — `listDecisions` has
no run filter), **run by the owner** (or under a dedicated expert account, never by an agent holding the
owner's credential), and reports precision per category and severity agreement; the figure is recorded at W56b's freeze. It gates nothing.

**A3.8 Spend (H-9).** Derived from measured tokens: a PC-02-sized call costs $0.013–0.019 at ≈ 2.5k tokens; v2
adds ≈ 5k prompt tokens (22.8 KB, ≈ 2.2 characters per token); with 1.5–3k output tokens under adaptive
thinking a small document costs ≈ $0.08–0.115. Identity probes (two gateways, 4 calls) ≈ $0.04; **one** v2
corpus pass (≈ 10 documents) ≈ $0.8–1.15; PC-02 under v2 once, for the v1 comparison, ≈ $1.1–1.6; the
live acceptance and the stand's identity check at INT-MAIN ≈ $0.1; the owner's export ≈ $0.75; a reserve of
$1.0 for a second corpus pass or a re-record after FIX — **≈ $3.8–4.65**. The rehearsal runs recorded only.
The ledger re-projects after the corpus pass and before PC-02. The ledger `docs/program/reviews/W56A-SPEND.md` records every live batch with
its projection; a projection above $5 stops for the owner (`R-29`).

**A3.9 Screens.** Finding list and detail: the seven category labels; the proposed severity marked
«предложено моделью» and the decided one; merged observations as «также найдено»; the decision panel's
severity choice on accepting, empty by default. Run page: the profile; a stage's typed error message if
`D-133` is open. Knowledge base and decision history: the decided severity. Export: the two columns.

### A4. Tasks

**`W56A-RULE-01`** (integrator): `R-129` v2 categories without norm compliance (H-2);
`R-130` severity proposed by the model, decided by the expert, and the CSV's two appended
columns (H-3, OD-11); `R-131` the deterministic merge rule (H-4); `R-132` the no-regression
gate on recorded responses, beta thresholds later (H-5); `R-133` a model identity mismatch
refuses (H-6); `R-134` recognised text as marked context for text-less pages only, the split,
the critic in W56b, the owner's in-product review and the live budget within `R-29`
(H-1, H-7…H-10). It also applies `R-124` and `R-126` to this plan and `AGENTS.md` §8.

**`W56A-FREEZE-01`** (integrator): standard form, plus — the per-gateway identity probe (§A3.5; a stop
per gateway); `W48-PROXY-01` merged forward; `D-133`'s state; migration `0022_findings_v2` (the number
follows W55b's head); `pin_sweep.py` for `reseal-surface migration table error-code`; the v2 corpus
specification; the legacy source files with their digests; the gateway model names; the re-measure
tolerance; the spend ledger opened; `git grep -n` for the predecessor version read from the actual `VERSION` (`R-86`) in `tests web/tests`; ports.

**Stage A** (from the freeze SHA; every lane runs alone on this host):
- **`W56A-SEAL-01`** — the contract (`FindingCategory` values; `Severity`; `FindingObservation.proposed_severity`;
  `AppendDecisionRequest.severity`; `DecisionEvent.severity`; `DecisionRecord.severity`; `Finding` and
  `FindingDetail` `decided_severity` and `merged_observations`; error codes `model_identity_mismatch`, the
  severity refusal, and `D-133`'s class and `RunStatus` message if open); the stage registry
  (`findings.merged` schema, the merge sentence, `text_analysis`'s optional `prepared.recognised_text`
  input, profile stage plans; no `StageStatus` member and no `depends_on` change); migration `0022`
  (category CHECKs and the `ungrounded_reason` CHECK widened by `ALTER`; `finding_observation.proposed_severity`;
  `expert_decision_event.severity` with its CHECK; the `finding_current_verdict` view redefined;
  `finding.canonical_observation_id` backfilled; the four error-code CHECKs — `ck_command_record_error_code`,
  `ck_audit_run_terminal_reason`, `ck_model_call_error_code`, `ck_provider_effect_error_code` — widened for
  each new stored code); one entry per new code in `src/auditmanager/shared/errors/{codes,catalog}.py`,
  `web/src/shared/api/catalog-message.ts`, `web/src/entities/audit-run/model/terminal-reason.ts`; the label
  records — `web/src/entities/expert-decision/model/category-labels.ts` (`CATEGORY_LABELS`;
  SEAL owns the exhaustive enum-to-label map, not the knowledge-base filter),
  `web/src/widgets/finding-list/ui/finding-list.tsx`, a new `web/src/entities/finding/model/severity-labels.ts`
  — and the `CACHE_STATES` seeds in `web/tests/guards/rendered-language.guard.test.ts`; `P02_LOCK.json`
  (gateway model names); `P02_SEAMS.md` §4 subsections for `findings.merged` and the recognised input;
  every port signature the lanes need. Allowed: `W55B-SEAL-01`'s list with `<date>_0022_findings_v2.py`,
  **minus** W55b-only items (`pyproject.toml`, `uv.lock`, `PROTOTYPE_PROFILE.md`, `PROTOTYPE_EXECUTION_PLAN.md`,
  the upload contract-text tests), `tests/contract/fixtures_ar/**`, `tests/characterization/w13_baseline/**`
  and the CSV assertions of `tests/e2e/pc01/test_acceptance.py` and the CSV row of
  `tests/contract/domain_p02/test_seam_register.py` (DECIDE's); plus the files named here, the database-side
  ungrounded-reason pins (`tests/integration/db/test_open_items_migration.py`,
  `tests/integration/analysis/test_ungrounded_reason_vocabulary.py` pointed at the head constraint instead of
  `0003`), `P02_SEAMS.md` §5.1 (the reason list) and the new `findings.merged` row in its artefact-role table
  (its producer cell in the register's designator form, `test_seam_register.py:17,130`),
  `docs/program/W56A-SEAL-01.md` and every path `pin_sweep.py` prints. Required: fresh upgrade; upgrade from W55b's head with rows (canonical
  backfill checked); refused downgrade; v1 responses byte-identical (records 03–11 unchanged, new
  properties absent). Under `R-102`/`R-126`, this lane authors the upgrade and backfill
  tests but does not run a database suite or a per-lane `make gate`; the final merged-candidate
  gate runs them.
- **`W56A-GENERATOR-01`** (§A3.6, after SEAL) — `tools/fixtures/seeded/**` (new), `fixtures/evaluation/ar_v2/**`
  (new; corpus and manifests), `tests/contract/fixtures_seeded/**` (new), `docs/program/W56A-GENERATOR-01.md`.
  Required: byte-stable regeneration; a mutation self-test per seeded issue and control.

**Stage B** — sequential; each lane from the previous lane's merge:
1. **`W56A-PROVIDER-01`** (§A3.5) — `src/auditmanager/analysis/text/{proxy,live,adapter,config,lock}.py`,
   `src/auditmanager/bootstrap/settings.py` (the stub and name refusals),
   `tests/integration/composition/{test_composition_root,test_settings_defaults}.py`,
   `tests/integration/analysis/test_provider_lock_refusals.py`, `src/auditmanager/runs/{executor,public}.py`
   (the stage error message only, if `D-133` is open), `src/auditmanager/bootstrap/adapters.py` (run
   status), `tests/integration/analysis_text/**`, `tests/replay/text_analysis/**`,
   `tests/integration/runs/test_stage_error*.py` (new), `docs/program/W56A-PROVIDER-01.md`. Required: a
   mismatch refused with its effect; the stub refused in live mode; each `D-133` item by a test; v1
   recordings untouched; the probe's comparison logic tested on recorded responses.
2. **`W56A-PROFILES-01`** (§A3.1, §A3.4) — `src/auditmanager/analysis/profiles/**` (new),
   `src/auditmanager/analysis/text/{profile,prompt,response,stage,provenance,artifact,recorded,__init__}.py`,
   `src/auditmanager/analysis/{public,__init__}.py` (export lines), `src/auditmanager/runs/{repository,commands,scope,__init__,public}.py`,
   `src/auditmanager/runs/executor.py` (the profile from the run row, the recognised input),
   `src/auditmanager/findings/grounding.py` (`quote_in_recognised_text`) with
   `tests/integration/findings/test_ungrounded_vocabulary_is_enforced.py` (six values, read from `0003`
   and `0022`) and the file holding `TestTheUngroundedVocabularyIsClosed` (named by the freeze),
   `src/auditmanager/bootstrap/{adapters,settings,composition}.py` (`composition.py` resolves the setting),
   `tests/conftest.py` (the scrub), `infra/deploy/env/provider.env.example`, `infra/deploy/readiness.sh`
   (unset refused on the stand) with `tests/integration/composition/test_readiness_command.py`,
   `tests/integration/analysis/profiles/**` (new), `docs/program/W56A-PROFILES-01.md`. Required: v1 runs
   byte-identical (the suite unchanged); `PC01_STAGES` unchanged; an unknown setting refuses start-up; the
   v2 stage plan from the run row; recognised text only for text-less pages; the new ungrounded reason;
   `proposed_severity` in the artefact; every excluded norm item listed.
3. **`W56A-MERGE-01`** (§A3.3) — `src/auditmanager/analysis/stages/finding_merge.py` (new),
   `src/auditmanager/analysis/stages/__init__.py`, `src/auditmanager/analysis/{public,__init__}.py` (export
   lines), `src/auditmanager/runs/executor.py` (gate → merge → publish by plan; `select_terminal` over the
   run's plan), `src/auditmanager/findings/{publication,queries,artifacts,public,__init__}.py`,
   `src/auditmanager/bootstrap/adapters.py` (`FindingAdapter`), `tests/integration/findings/**`,
   `tests/integration/runs/test_v2_stage_plan*.py` (new), `docs/program/W56A-MERGE-01.md`. Required: the
   rule's cases (overlap, equal quote under and over 20 characters, different category, a chain of three
   joined transitively, disjoint); canonical choice; no observation dropped; distinct-finding counts; a
   non-canonical decision refused; `proposed_severity` published; a v1 run unchanged; not partial without
   drawings.
4. **`W56A-DECIDE-01`** (§A3.2 decisions, CSV) — `src/auditmanager/decisions/**` (the fold),
   `src/auditmanager/api/routers/decisions.py` (body), `src/auditmanager/bootstrap/adapters.py`
   (`DecisionAdapter`, `_finding_view`, `_record_view`), `src/auditmanager/findings/queries.py` (decided
   severity read from the view), `src/auditmanager/exports/**`, and **the CSV pins**:
   `docs/program/P02_SEAMS.md` §6, `web/src/shared/api/csv-columns.ts`,
   `tests/integration/exports/{test_frozen_column_list,test_csv_contract}.py`,
   `tests/contract/domain_p02/test_seam_register.py` (the CSV row), `web/tests/contract/csv-columns.contract.test.ts`,
   `web/tests/unit/export/export-panel.test.ts`, `web/tests/guards/rendered-language.guard.test.ts` (the
   column count), `tests/e2e/pc01/test_acceptance.py` (the CSV assertions), `tests/integration/p02_journey/test_journey_figures.py`,
   `tests/e2e/p02/test_journey_figures_pinned.py`, `tests/characterization/w13_baseline/` record 12 with
   `journey.py` and `test_response_baseline.py` (`PERMITTED_EXCEPTIONS`), `docs/manual-tests/PC-01_prototype.md`,
   `docs/program/ALPHA_ROADMAP.md` (the column sentence), the column-count sentences in
   `src/auditmanager/api/routers/ports.py` (docstring) and `web/src/widgets/export-panel/ui/export-panel.tsx`
   (docstring); `tests/integration/decisions/**`,
   `docs/program/W56A-DECIDE-01.md`. Required: severity only with `accept`; reject after accept clears the
   decided severity; an expert-only action under `R-60`; the two columns appended; CSV rows for the canonical observation only; v1 events unchanged.
5. **`W56A-HARNESS-01`** (§A3.6; live recording inside the ledger) — `tools/evaluation/**` (new),
   `tests/integration/evaluation/**` (new, with its own `conftest.py` if the shared fixtures do not reach it), `fixtures/recorded/text_analysis/ar_v2/**` (new), `fixtures/evaluation/ar_v2/baseline.json`,
   `tests/contract/evaluation/**` (new), `docs/program/reviews/W56A-SPEND.md`, `docs/program/W56A-HARNESS-01.md`.
   Required: the matcher's vacuity proofs; the gate red on a doctored recording that loses one seeded issue;
   any-member matching and the over-merge report; the live mode's cap honoured; gate time measured; spend
   recorded.
6. **`W56A-WEB-01`** (§A3.9) — `web/src/widgets/{finding-list,decision-panel,decision-history,knowledge-base,run-progress}/**`,
   `web/src/entities/{finding,finding-observation,expert-decision,audit-run}/**` except
   `web/src/entities/expert-decision/model/category-labels.ts` (SEAL's label map),
   `web/src/features/record-verdict/**`,
   `web/src/_pages/{review,run,knowledge-base}/**` (including the knowledge-base category filter
   in `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx`, consuming SEAL's label map),
   `web/tests/unit/{review,run,decisions,widgets}/**`,
   `web/tests/unit/screens/knowledge-base.test.ts`, `web/tests/guards/{prepared-sections,rendered-language}.guard.test.ts`
   (entries), `web/tests/unit/styles/screens.ts`, `tests/e2e/pc01/journey/manifest.json` (entries),
   `docs/program/W56A-WEB-01.md`.

**Stage C:** **`W56A-REHEARSAL-01`** (night window, recorded only): a disposable stand here with v2 set; the
corpus and the PC-02 documents through the pipeline; findings, merge groups and severities on the screens.
Allowed: `scripts/rehearsal/w56a/**` (no surface-count phrases), `docs/program/W56A-REHEARSAL-01.md`.
**`W56A-RELNOTES-01`:** `release-notes/0.7.0.json`, `release-notes/dictionary.json`, `VERSION`, the
freeze's predecessor-version hits (`R-86`), `docs/program/W56A-RELNOTES-01.md`.

**Stage D (`R-124`):** one `W56A-JUDGE-01` reads the merged whole-wave diff after the last
lane and challenges prompt injection from document and recognised text; severity by a non-expert
or with a non-accept event; a decision on a non-canonical observation; the profile setting; a
doctored recording; lineage observation → group → finding → decision; ALR-05 for
`analysis.profiles` and `tools.evaluation`; v1 byte-identity; and the gate's vacuity.
`W56A-FIX` addresses that judge's findings. There is no W56a QA lane, second judge,
cross-examination, notes judge or recheck round. Release notes still receive the required
contract and product checks in their own lane; the periodic debt-and-quality wave retains the
independent review set of `R-124`.

**`W56A-INT-CLOSE`** — register: norm checklist items for W57 (consumer `W57A-MAP-01`; insolation items marked after beta, K-2); consolidation of the corpus builders; merged
members in the export (W57); the memory-peak summary (G-12). **`W56A-INT-MAIN-01`** on the owner's
instruction naming the SHA, in the order of `reviews/W54-W57-CHAIN-REVIEW.md` CD-16 (*amended 2026-10-12*):
the exact-SHA gate; inside an agreed window (K-5) the one-off copy for migration `0022` (K-6: W54's
`dump-db` → `inventory-s3` → `fetch` → test restore here at W55b's head → `attest … publish <sha>` with the candidate SHA); `origin/main`;
workflow and `verify-deployed.sh`; `resume`; never during a corpus import (P4) or a retrieval-set build
(W57 P5b). The switch to v2 is an **owner act** (CD-17): the host-owned `provider.env` entry and an api
restart, checked on a new run's recorded profile; rollback is the same act back to v1. Then a live
identity check on the stand's gateway; live acceptance (a synthetic bundle: findings, severities,
merge); the owner's export analysed for the owner's review (§A3.7); tag `v0.7.0` only under the
release rule (`R-86`, §8.4), its predecessor read from the actual `VERSION`, not a literal.

### A5. Ownership (W56a)

| Hotspot / path family | Owner | Parallel writer |
| --- | --- | --- |
| `contracts/**`, migration `0022`, `api/**` but router bodies and `app.py`, generated client, facts file, error-code entries, label records including `web/src/entities/expert-decision/model/category-labels.ts`, `P02_LOCK.json` | SEAL (A) | none |
| `tools/fixtures/seeded/**`, `fixtures/evaluation/ar_v2/**` (corpus) | GENERATOR (A) | none |
| `analysis/text/{proxy,live,adapter,config,lock}.py` | PROVIDER (B1) | none |
| `analysis/profiles/**`, other `analysis/text/*`, `runs/{repository,commands,scope}.py`, `provider.env.example`, readiness | PROFILES (B2) | none |
| `runs/executor.py` | PROVIDER (message) → PROFILES → MERGE | none at once |
| `analysis/{public,__init__}.py` | PROFILES → MERGE | none at once |
| `runs/public.py` | PROVIDER → PROFILES | none at once |
| `runs/__init__.py` | PROFILES | none |
| `findings/**` | PROFILES (grounding and its vocabulary test) → MERGE → DECIDE (queries) | none at once |
| `bootstrap/settings.py` | PROVIDER → PROFILES | none at once |
| `bootstrap/composition.py` | SEAL → PROFILES | none at once |
| the named files in `tests/integration/composition/` | PROVIDER (composition root, settings defaults) → PROFILES (readiness) | none at once |
| `bootstrap/adapters.py` | SEAL → PROVIDER → PROFILES → MERGE → DECIDE | none at once |
| `exports/**`, the CSV pins, record 12 | DECIDE (B4) | none |
| `rendered-language.guard.test.ts` | SEAL (seeds) → DECIDE (column count) → WEB (entries) | none at once |
| `tools/evaluation/**`, `tests/evaluation/**`, v2 recordings, baseline, spend ledger | HARNESS (B5) | none |
| web files of §A3.9 except SEAL's `web/src/entities/expert-decision/model/category-labels.ts` | WEB (B6) | none |
| `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx` category filter (consumes SEAL's `CATEGORY_LABELS`) | WEB (B6) | none |
| integrator-only files, refs, tags, the stand, `.local/**` | integrator | none |

### A6. Estimate (W56a)

This is the pre-`R-124` estimate; `W56A-FREEZE-01` re-estimates the revised review and check
sequence instead of silently carrying this figure forward. Freeze 2.5 (two-gateway probe); SEAL 5.5; GENERATOR 5.0; PROVIDER 3.5; PROFILES 6.5; MERGE 5.5; DECIDE 4.0;
HARNESS with recording 5.0; WEB 4.5; merges 5.0; rehearsal 1.5; release notes 0.5; judging 2.5; FIX 4.0;
gate 0.5; close with the memory summary 1.5 — 57.5 h, plus **a contingency of 4.5 h** shown on its own (W55
grew from 51 to 87 h through judging) — **≈ 62 h**, P50 ≈ 11.75 working days; **plan on P80 ≈ 15.75**.

### A7. Stop conditions

`W48-PLAN.md` §14, plus: a gateway that echoes or ignores the model (H-6), per gateway; a projected spend
above $5 (`R-29`); v1 runs not byte-identical after PROFILES; v2's live aggregate recall on PC-02 below v1's;
an excluded norm item that cannot be separated from a v2 category.

### A8. Non-goals

The critic (W56b, H-10); norm categories and norm verification (W57); drawings, region evidence, OCR
citations, chunked analysis, presets (W56b); a model-routed merge; absolute quality thresholds (W58);
merged members in the CSV (W57).

### A9. Amendment to W55b requested by this plan

W55b stores, beside `text_character_count`, `document_version.textless_pages` (the pages whose pypdfium2
character count is below the threshold its freeze pins) and `document_version.recognised_character_count`
(the recognised characters on those pages, from `_results.md`), both at upload. `W55-PLAN.md` §B3.2 carries the sentence (handed to the integrator
with this plan).

---

## Part B — W56b: drawings, long documents and the critic (`v0.9.0`, after W57b) — original scope

A draft successor design, conditional grants, beta preset matrix and W57 normative drawing/chunk
handoff are in `W56B-PLAN.md` (unadopted 2026-10-08 layer, K-4: preserved, not reviewed or adopted). The paragraph below remains the source scope, not a task grant.

**In:** `block_analysis` over W55b's crops (one crop per call, as legacy); region evidence end to end (the
`Evidence` union, `finding_evidence` region columns, grounding, the CSV region columns, the crop-and-box
viewer, crop serving by run or evidence); recognised-text citations marked as such (H-7); chunked text
analysis lifting W55b's input budget (G-11); merge of block, chunk and text observations (the region-versus-
span link and the canonical choice across evidence kinds); **the critic** (`finding_review`, H-4, H-10) over
text and block findings, annotate-only, its failure semantics against FS-04 (`partial` unless the owner
amends it); **W53's resume rule and watchdog for multi-call stages** — completed effects reused, unknown ones
counted at their maximum (as W54's repair journal), the watchdog sized by the run's stage plan;
**«Настройки анализа»** — presets kept by an administrator, picked by an expert per run, recorded by the run
(A-8), with model choices constrained by the per-gateway identity pins, replacing
`AUDITMANAGER_ANALYSIS_PROFILE_ID`.

**Inputs before its plan:** the W54 vision probe (image acceptance, model, price per crop); the owner's
drawing-analysis budget (G-3); an owner poll on region granularity (whole block, model-proposed box,
text-layer words where present — 18 of 47 АР blocks have them), the vision ceiling mechanism and model,
cross-chunk contradictions (legacy's summary-sheet skeleton or a new consistency stage), the critic's
failure semantics, presets per stage and the setting's retirement, and the live-spend exception its
rehearsals need; a seeded drawing corpus and the matcher's rule for region evidence; the owner's precision
figure from §A3.7.

**Size, extrapolated:** ≈ 75 h (block analysis ≈ 15, region evidence ≈ 15, chunking ≈ 8, the critic ≈ 7,
multi-call resume ≈ 6, presets ≈ 12, overhead ≈ 12). If its plan confirms that size, where the presets go is the owner's question at that planning (W57 now
precedes W56b, I-12, so its second track is no longer available). Its plan is written once the probe report exists and is judged in two rounds.
