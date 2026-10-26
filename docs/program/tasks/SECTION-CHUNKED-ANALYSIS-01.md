# Task SECTION-CHUNKED-ANALYSIS-01 — a section run above the one-call budget is analysed in whole-page windows

task_id: SECTION-CHUNKED-ANALYSIS-01

## Outcome

A non-АР section run on a volume above the one-call budget is analysed in whole-page windows: each window one model call under ONE run cost ceiling, with its own effect-journal entry and a saved reply so that a kill between windows resumes without paying for a finished window twice; quotes keep document-global offsets and bind back to the saved text exactly as today; the run states in its stage metrics that the windows were analysed independently; `analysis_input_budget_exceeded` is refused only above `MAX_ANALYSIS_WINDOWS` (12) windows' worth, with the same two integers; below the old budget the behaviour is byte-identical (one window is the existing single call and the existing recordings still bind).

## Depends on

- `W55B-BUDGET-01` — the one-call budget and the start-time refusal.
- `W56B-INT-CHUNK-PREFLIGHT-PREP-01` — whole-page partition with document-global offsets.
- `W56B-INT-WINDOW-ANCHOR-PREP-01` — quote resolution inside a saved window.
- `W56B-INT-WINDOW-COHORT-PREP-01` — binding of a complete reply cohort.
- `PROD-11-AR-V1-V2-REMOVAL-01` — the v1 machinery that the 14 sections run on.

## Frozen inputs

- domain contract: `contracts/domain/v1/error-codes.json`, SHA-256 `00cd90374851a32a799d1413ba80ad770fc4c40f1d203a4002bfd87d653123d5` (unchanged);
- API contract: `contracts/api/v1/openapi.json`, SHA-256 `f98c4704bf04bea5191d48d05f7248f3380675c95b257088213ae4254b793ff8` (unchanged);
- analysis contract: `contracts/analysis/v1/stage-registry.json` SHA-256 `a3fd9079c75829fe9bcae1f946b0c51fbf759124115b977c4346116746ffb92c`, `stage-result.schema.json` SHA-256 `8920c02807748a2f6f4a0a8ffa715c9ead5b962c1a1278a4ceb44e9bd065697a` (unchanged; `TEXT_STAGE_VERSION` stays `1.1.0`);
- migration head: `0033_ar_v3_cite_stage_id` (unchanged);
- base commit: `6075df889beef40084d337f03d2a072349fc9620` (tip of `integration/ar-close-1026` at launch).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

The lane adds no route, screen, error code, migration or stage id. The new `reason` values (`window_plan_over_limit`, `window_page_exceeds_limit`, `window_ceiling_unusable`, `window_text_layer_invalid`, `durable_window_custody_required`, the `window_call_*` and `window_reply_*` family) are values of the existing `reason` detail of `analysis_input_invalid`, not members of a maintained set.

## Captured premise evidence

- premise: the refusal, the unconsumed window primitives, the single call under one meter and one journal, the reclaim predicate, the schema's room for several calls per run, the shared helper with AR v3 and the wiring of the budget are as the brief says (and the one place the premise is richer than the brief: the budget is a cost figure, so windows do not raise the volume a fixed ceiling pays for)

### P-01 — the refusal, its figures and where the budget is derived
- captured_at: 2026-10-27
- command: `rg -n "analysis_input_budget_exceeded|152361|input_budget" src | head -30`
- captured_output:
  ```text
  src/auditmanager/analysis/public.py:105:from auditmanager.analysis.text.budget import REFERENCE_DOCUMENT_CHARACTERS, input_budget_characters
  src/auditmanager/analysis/public.py:224:    "input_budget_characters",
  src/auditmanager/bootstrap/settings.py:24:from auditmanager.analysis.public import REFERENCE_DOCUMENT_CHARACTERS, input_budget_characters
  src/auditmanager/bootstrap/settings.py:149:    #: ``analysis.public.input_budget_characters``. Never a literal and never read from the
  src/auditmanager/bootstrap/settings.py:153:    input_budget_characters: int
  src/auditmanager/bootstrap/settings.py:214:def _input_budget(model_id: str, ceiling_usd: float) -> int:
  src/auditmanager/bootstrap/settings.py:224:        budget = input_budget_characters(model_id, ceiling_usd)
  src/auditmanager/bootstrap/settings.py:410:    budget = _input_budget(model_id, ceiling)
  src/auditmanager/bootstrap/settings.py:426:        input_budget_characters=budget,
  src/auditmanager/bootstrap/providers.py:31:    input_budget_characters,
  src/auditmanager/bootstrap/providers.py:176:            input_budget_characters=input_budget_characters(frozen.pin_id, self._ceiling),
  src/auditmanager/bootstrap/adapters.py:224:        budget = self._runs.input_budget_characters
  src/auditmanager/bootstrap/adapters.py:244:                                 provider_mode=mode, input_budget_characters=budget,
  src/auditmanager/bootstrap/adapters.py:842:        input_budget_characters: int | None = None,
  src/auditmanager/bootstrap/adapters.py:883:        # (``AppSettings.input_budget_characters``) and handed to ``start_audit_run`` and,
  src/auditmanager/bootstrap/adapters.py:889:        self._input_budget_characters = input_budget_characters
  src/auditmanager/bootstrap/adapters.py:916:                input_budget_characters=self._input_budget_characters,
  src/auditmanager/bootstrap/adapters.py:1024:                input_budget_characters=self._input_budget_characters,
  src/auditmanager/bootstrap/adapters.py:1111:    def input_budget_characters(self) -> int | None:
  src/auditmanager/bootstrap/adapters.py:1117:        return self._input_budget_characters
  src/auditmanager/bootstrap/composition.py:348:        input_budget_characters=resolved.input_budget_characters,
  src/auditmanager/runs/provider.py:39:    input_budget_characters: int
  src/auditmanager/runs/commands.py:49:``text_character_count`` is **above** ``input_budget_characters`` with
  src/auditmanager/runs/commands.py:50:``analysis_input_budget_exceeded`` (``422``; ``character_count`` and ``budget_characters``).
  src/auditmanager/runs/commands.py:64:``input_budget_characters`` is a keyword that defaults to ``None`` so the many callers that
  src/auditmanager/runs/commands.py:397:def _checked_budget(input_budget_characters: int | None) -> int | None:
  src/auditmanager/runs/commands.py:405:    if input_budget_characters is None:
  src/auditmanager/runs/commands.py:408:        isinstance(input_budget_characters, bool)
  src/auditmanager/runs/commands.py:409:        or not isinstance(input_budget_characters, int)
  src/auditmanager/runs/commands.py:410:        or input_budget_characters < 0
  ```
- interpretation: The refusal is `runs/commands.py::_refuse_over_budget`, fed by `input_budget_characters` that `bootstrap/settings.py` (environment source) and `bootstrap/providers.py::_freeze` (database source) derive once from the model and the ceiling; `bootstrap/adapters.py` passes it to the two commands. No literal 152361 exists in `src`: the figure is computed (next block). `v3_group.py` shares `_checked_budget` and `_refuse_over_budget` (P-08).

### P-02 — the computed figures
- captured_at: 2026-10-27
- command: `PYTHONPATH=src python -c "from auditmanager.analysis.text.budget import input_budget_characters as b, REFERENCE_DOCUMENT_CHARACTERS as r; print(b('claude-opus-5',1.0), b('claude-sonnet-5',1.0), r)"`
- captured_output:
  ```text
  152361 572361 93690
  ```
- interpretation: The one-call budget is 152 361 pypdfium2 characters for the pinned primary model at the USD 1.00 ceiling, 572 361 for the cheaper tier, against the 93 690-character real set. It is a cost figure (`budget.py`, `D-162`): a full window costs about the whole ceiling, so windows bound the size of a call, not the spend.

### P-03 — the window primitives and who consumes them today
- captured_at: 2026-10-27
- command: `rg -ln "chunk_preflight|window_cohort|window_anchor|saved_window_custody" src tests`
- captured_output:
  ```text
  src/auditmanager/analysis/public.py
  src/auditmanager/analysis/text/source_bytes.py
  src/auditmanager/analysis/text/window_anchor.py
  src/auditmanager/analysis/text/window_cohort.py
  tests/integration/analysis_text/test_source_bytes.py
  tests/integration/analysis_text/test_chunk_preflight.py
  tests/integration/analysis_text/test_window_cohort.py
  tests/integration/analysis_text/test_window_anchor.py
  tests/integration/analysis_text/test_saved_window_custody.py
  ```
- interpretation: In `src` only `analysis/public.py` (re-exports), `source_bytes.py` (the partition) and the two window modules themselves name them; every other hit is a test. Next block: the call graph.

### P-04 — call graph of the primitives at the base
- captured_at: 2026-10-27
- command: `git grep -n -E "partition_text_layer|bind_window_claim_cohort|resolve_window_anchor|validate_window_plan|check_run_text_window_input|load_saved_text_windows|check_supplied_text_window_bytes" 6075df88 -- src`
- captured_output:
  ```text
  src/auditmanager/analysis/public.py:127:    check_run_text_window_input,
  src/auditmanager/analysis/public.py:234:    "check_run_text_window_input",
  src/auditmanager/analysis/text/chunk_preflight.py:75:def partition_text_layer(
  src/auditmanager/analysis/text/saved_window_custody.py:26:    check_supplied_text_window_bytes,
  src/auditmanager/analysis/text/saved_window_custody.py:104:def check_run_text_window_input(
  src/auditmanager/analysis/text/saved_window_custody.py:116:        source = check_supplied_text_window_bytes(
  src/auditmanager/analysis/text/source_bytes.py:22:from auditmanager.analysis.text.chunk_preflight import TextChunk, partition_text_layer
  src/auditmanager/analysis/text/source_bytes.py:138:def check_supplied_text_window_bytes(
  src/auditmanager/analysis/text/source_bytes.py:157:    windows = partition_text_layer(layer, max_chunk_characters=max_chunk_characters)
  src/auditmanager/analysis/text/window_anchor.py:22:def resolve_window_anchor(
  src/auditmanager/analysis/text/window_anchor.py:37:    validate_window_plan(layer, windows)
  src/auditmanager/analysis/text/window_anchor.py:49:def validate_window_plan(layer: TextLayer, windows: tuple[TextChunk, ...]) -> None:
  src/auditmanager/analysis/text/window_cohort.py:15:from auditmanager.analysis.text.window_anchor import WindowAnchorError, validate_window_plan
  src/auditmanager/analysis/text/window_cohort.py:36:def bind_window_claim_cohort(
  src/auditmanager/analysis/text/window_cohort.py:48:    validate_window_plan(layer, windows)
  src/auditmanager/runs/text_window_input.py:20:    check_run_text_window_input,
  src/auditmanager/runs/text_window_input.py:87:def load_saved_text_windows(
  src/auditmanager/runs/text_window_input.py:142:        checked = check_run_text_window_input(
  src/auditmanager/runs/text_window_input.py:165:__all__ = ["SavedTextWindowInput", "load_saved_text_windows"]
  ```
- interpretation: `partition_text_layer` is reached only through `source_bytes` -> `saved_window_custody` -> `runs/text_window_input.load_saved_text_windows`, which has no caller in `src`. `bind_window_claim_cohort` and `resolve_window_anchor` have no caller in `src` at all. So: chunk_preflight, window_anchor and window_cohort are consumed by this lane (the stage); saved_window_custody, source_bytes and text_window_input stay unconsumed (the stage already holds the text layer read by `read_artifact`).

### P-05 — how the stage calls the model once, and how the ceiling and the journal are held
- captured_at: 2026-10-27
- command: `git grep -n -E "run_text_analysis\(|cost_meter = |meter = CostMeter|class _DurableCallJournal|meter=cost_meter|ledger.record" 6075df88 -- src/auditmanager/runs/executor.py src/auditmanager/analysis/text/stage.py`
- captured_output:
  ```text
  src/auditmanager/analysis/text/stage.py:300:def run_text_analysis(
  src/auditmanager/analysis/text/stage.py:335:    cost_meter = meter or CostMeter(ceiling_usd=resolved_config.run_cost_ceiling_usd)
  src/auditmanager/runs/executor.py:264:class _DurableCallJournal(ModelCallJournal):
  src/auditmanager/runs/executor.py:543:        outcome = run_text_analysis(
  src/auditmanager/runs/executor.py:554:            meter=cost_meter,
  src/auditmanager/runs/executor.py:563:        ledger.record(
  src/auditmanager/runs/executor.py:1012:            ledger.record(status="succeeded", error=None, waited_seconds=0.0)
  ```
- interpretation: `stage.py::run_text_analysis` makes one call and takes a `meter`; the executor builds one `CostMeter` per run and hands it to every attempt (executor.py:543-554), and drives a durable journal (`_DurableCallJournal`: prepare, response_received, complete). A windowed stage can therefore share the meter and the journal unchanged.

### P-06 — what a lost attempt's live effects do to a resume
- captured_at: 2026-10-27
- command: `git grep -n -B1 -A6 "ambiguous = bool" 6075df88 -- src/auditmanager/jobs/repository.py`
- captured_output:
  ```text
  src/auditmanager/jobs/repository.py-679-                )
  src/auditmanager/jobs/repository.py:680:            ambiguous = bool(session.execute(text(
  src/auditmanager/jobs/repository.py-681-                "SELECT EXISTS (SELECT 1 FROM provider_call_effect "
  src/auditmanager/jobs/repository.py-682-                "WHERE attempt_id = :attempt_id AND state <> 'not_processed' "
  src/auditmanager/jobs/repository.py-683-                "AND provider_mode <> 'recorded')"
  src/auditmanager/jobs/repository.py-684-            ), {"attempt_id": candidate["attempt_id"]}).scalar_one())
  src/auditmanager/jobs/repository.py-685-            count = int(session.execute(text(
  src/auditmanager/jobs/repository.py-686-                "SELECT count(*) FROM attempt WHERE job_id = :job_id"
  ```
- interpretation: At the base any live effect of the lost Attempt that is not `not_processed` (so a `completed` one too) makes the Attempt ambiguous and fails the run `provider_outcome_unknown`. A run killed between two windows could therefore never resume; this is the predicate the lane narrows to a completed effect that carries a saved window reply.

### P-07 — the schema allows several calls per run in the text stage
- captured_at: 2026-10-27
- command: `git grep -n -E "uq_model_call|CONSTRAINT ck_provider_effect_stage_id|PRIMARY KEY|UNIQUE" 6075df88 -- db/migrations/versions/20261002_0014_durable_analysis_effects.py`
- captured_output:
  ```text
  db/migrations/versions/20261002_0014_durable_analysis_effects.py:139:            job_id             text PRIMARY KEY,
  db/migrations/versions/20261002_0014_durable_analysis_effects.py:159:            CONSTRAINT uq_job_run_id UNIQUE (run_id),
  db/migrations/versions/20261002_0014_durable_analysis_effects.py:160:            CONSTRAINT uq_job_run_job UNIQUE (run_id, job_id),
  db/migrations/versions/20261002_0014_durable_analysis_effects.py:161:            CONSTRAINT uq_job_current_attempt UNIQUE (current_attempt_id)
  db/migrations/versions/20261002_0014_durable_analysis_effects.py:168:            attempt_id      text PRIMARY KEY,
  db/migrations/versions/20261002_0014_durable_analysis_effects.py:190:            CONSTRAINT uq_attempt_execution_token UNIQUE (execution_token),
  db/migrations/versions/20261002_0014_durable_analysis_effects.py:191:            CONSTRAINT uq_attempt_job_attempt UNIQUE (job_id, attempt_id)
  db/migrations/versions/20261002_0014_durable_analysis_effects.py:209:            lease_id    text PRIMARY KEY,
  db/migrations/versions/20261002_0014_durable_analysis_effects.py:217:            CONSTRAINT uq_lease_attempt_id UNIQUE (attempt_id),
  db/migrations/versions/20261002_0014_durable_analysis_effects.py:233:        "ALTER TABLE model_call ADD CONSTRAINT uq_model_call_run_call "
  db/migrations/versions/20261002_0014_durable_analysis_effects.py:234:        "UNIQUE (run_id, model_call_id);"
  db/migrations/versions/20261002_0014_durable_analysis_effects.py:239:            model_call_id       text PRIMARY KEY,
  db/migrations/versions/20261002_0014_durable_analysis_effects.py:267:            CONSTRAINT ck_provider_effect_stage_id CHECK (stage_id = 'text_analysis'),
  db/migrations/versions/20261002_0014_durable_analysis_effects.py:348:                PRIMARY KEY (attempt_id, stage_id, blob_id, blob_role),
  db/migrations/versions/20261002_0014_durable_analysis_effects.py:368:            CONSTRAINT uq_analysis_artifact_upload_token UNIQUE (upload_token),
  db/migrations/versions/20261002_0014_durable_analysis_effects.py:501:    op.execute("ALTER TABLE model_call DROP CONSTRAINT uq_model_call_run_call;")
  ```
- interpretation: `provider_call_effect` is keyed by `model_call_id` only (the stage id is constant `text_analysis`) and `model_call` is unique on `(run_id, model_call_id)`: any number of calls per run and stage is admitted. No migration is needed. `parameters` is free-form jsonb on both tables (`ar_v3_*` keys already ride there).

### P-08 — the stored vocabulary does not hold the budget code
- captured_at: 2026-10-27
- command: `git show 6075df88:contracts/domain/v1/error-codes.json | grep -n -A18 '"analysis_input_budget_exceeded"'`
- captured_output:
  ```text
  443:    "analysis_input_budget_exceeded": {
  444-      "http": 422,
  445-      "retryable": false,
  446-      "category": "policy",
  447-      "summary": "The document version's text is larger than the analysis input budget derived from the configured model and the per-run cost ceiling. The run was refused up front: no run exists and nothing was sent to a model
  448-      "safe_detail_keys": [
  449-        "character_count",
  450-        "budget_characters"
  451-      ],
  452-      "evidence": [
  453-        "W55-PLAN.md section B3.3",
  454-        "R-118"
  455-      ],
  456-      "notes": [
  457-        "Answered by startRun and reauditRun, before the run is created, when the version's recorded text_character_count (pypdfium2's count over the whole document) exceeds the budget. character_count is that count and budget
  458-        "It is answered before any run or job exists, so no row carries it. Migration 0022 widens the four stored-error CHECKs for model_identity_mismatch; this pre-run refusal and the edge-only rate_limited code remain outsid
  459-      ]
  460-    },
  461-    "model_identity_mismatch": {
  ```
- interpretation: The code is answered before any run exists and is never stored (the contract note on the code), with exactly the safe detail keys `character_count` and `budget_characters`. A refusal at execution time therefore uses `analysis_input_invalid` with a `reason`; the start-time keys and integers are unchanged by this lane.

### P-09 — the budget helper is shared with the AR v3 group
- captured_at: 2026-10-27
- command: `git grep -n -E "_refuse_over_budget|_checked_budget" 6075df88 -- src`
- captured_output:
  ```text
  src/auditmanager/runs/commands.py:397:def _checked_budget(input_budget_characters: int | None) -> int | None:
  src/auditmanager/runs/commands.py:416:def _refuse_over_budget(
  src/auditmanager/runs/commands.py:532:    budget = _checked_budget(input_budget_characters)
  src/auditmanager/runs/commands.py:575:        _refuse_over_budget(_version.text_character_count, budget)
  src/auditmanager/runs/commands.py:799:    budget = _checked_budget(input_budget_characters)
  src/auditmanager/runs/commands.py:824:            _refuse_over_budget(source_version.text_character_count, budget)
  src/auditmanager/runs/v3_group.py:27:from auditmanager.runs.commands import _checked_budget, _refuse_over_budget, frozen_input_digest
  src/auditmanager/runs/v3_group.py:251:    budget = _checked_budget(
  src/auditmanager/runs/v3_group.py:254:    _refuse_over_budget(version.text_character_count, budget)
  ```
- interpretation: `_refuse_over_budget` is imported by `runs/v3_group.py`. The lane leaves it untouched and gives the two section-run commands a new helper, so the AR v3 path keeps the one-call refusal (held by a test).

### P-10 — where the budget reaches the commands
- captured_at: 2026-10-27
- command: `git grep -n "input_budget_characters" 6075df88 -- src/auditmanager/bootstrap`
- captured_output:
  ```text
  src/auditmanager/bootstrap/adapters.py:224:        budget = self._runs.input_budget_characters
  src/auditmanager/bootstrap/adapters.py:244:                                 provider_mode=mode, input_budget_characters=budget,
  src/auditmanager/bootstrap/adapters.py:842:        input_budget_characters: int | None = None,
  src/auditmanager/bootstrap/adapters.py:883:        # (``AppSettings.input_budget_characters``) and handed to ``start_audit_run`` and,
  src/auditmanager/bootstrap/adapters.py:889:        self._input_budget_characters = input_budget_characters
  src/auditmanager/bootstrap/adapters.py:916:                input_budget_characters=self._input_budget_characters,
  src/auditmanager/bootstrap/adapters.py:1024:                input_budget_characters=self._input_budget_characters,
  src/auditmanager/bootstrap/adapters.py:1111:    def input_budget_characters(self) -> int | None:
  src/auditmanager/bootstrap/adapters.py:1117:        return self._input_budget_characters
  src/auditmanager/bootstrap/composition.py:348:        input_budget_characters=resolved.input_budget_characters,
  src/auditmanager/bootstrap/providers.py:31:    input_budget_characters,
  src/auditmanager/bootstrap/providers.py:176:            input_budget_characters=input_budget_characters(frozen.pin_id, self._ceiling),
  src/auditmanager/bootstrap/settings.py:24:from auditmanager.analysis.public import REFERENCE_DOCUMENT_CHARACTERS, input_budget_characters
  src/auditmanager/bootstrap/settings.py:149:    #: ``analysis.public.input_budget_characters``. Never a literal and never read from the
  src/auditmanager/bootstrap/settings.py:153:    input_budget_characters: int
  src/auditmanager/bootstrap/settings.py:224:        budget = input_budget_characters(model_id, ceiling_usd)
  src/auditmanager/bootstrap/settings.py:426:        input_budget_characters=budget,
  ```
- interpretation: `settings.py` and `providers.py::_freeze` derive the per-call figure, `composition.py` and `adapters.py` carry it to `start_audit_run` / `reaudit_run` as the existing keyword. Because the window multiple is applied inside the commands, none of these `bootstrap/**` files needs an edit and the composition-root tests that pin `settings.input_budget_characters == input_budget_characters(...)` stay green.

### P-11 — the attempt watchdog and the per-call ceiling
- captured_at: 2026-10-27
- command: `git grep -n -E "ATTEMPT_WATCHDOG_SECONDS = |_TIMEOUT_SECONDS: Final" 6075df88 -- src`
- captured_output:
  ```text
  src/auditmanager/analysis/text/proxy.py:85:_TIMEOUT_SECONDS: Final[int] = 200  # the proxy's own deadline is ~190s
  src/auditmanager/executors/operations.py:75:_DEFAULT_TIMEOUT_SECONDS: Final[int] = 200  # the proxy's own deadline is ~190 s
  src/auditmanager/jobs/lease.py:21:ATTEMPT_WATCHDOG_SECONDS = 900
  ```
- interpretation: One Attempt has 900 s (`jobs/lease.py`); one proxy call at most 200 s. Twelve windows are three Attempts of four windows at the worst per-call time, which is where `MAX_ANALYSIS_WINDOWS = 12` comes from (the budget module states the arithmetic). A window in flight when the watchdog fires is an ambiguous effect (a limit, section 8 of the report).

### P-12 — sibling decision records
- captured_at: 2026-10-27
- command: `git grep -n -E "D-162|G-11|AD-18" 6075df88 -- docs/program/DEBT_REGISTER.md docs/program/dispatch/ROADMAP-TO-BETA.md docs/program/PRODUCTION-ADR-PACK-01.md`
- captured_output:
  ```text
  docs/program/DEBT_REGISTER.md:79:| **D-162** | the input budget models cost, not the model's context window, and the token constant was never measured on a live run of the real set (Y-5, `W55B-BUDGET-01` §5) | a live run with a key; `ModelPin` gains the context |
  docs/program/DEBT_REGISTER.md:321:### D-162 — the input budget is cost-only and its token constant is unmeasured on the real set
  docs/program/dispatch/ROADMAP-TO-BETA.md:106:| **W55b** | AR-1a: portal bundles only (G-4, G-10), up to 500 pages / 250 MiB streamed end to end (G-2), the analysis input budget (G-11), recognised text marked, portal blocks, crops cut locally, **Блоки** made real (`W55-PLAN.md` Part B) | — | L+ | `v0.6.1` (portal bundles, blocks) |
  docs/program/dispatch/ROADMAP-TO-BETA.md:110:| **W56b** | `block_analysis` over the W55b crops (G-8), **region evidence**, recognised-text citations, **chunked text analysis** (G-11), **the critic** (H-10), multi-call resume, **Настройки анализа** (presets, A-8); **after W57b (I-12)**; dedicated pre-freeze graph in `W56B-PLAN.md`, gated by the W54/W55 vision probe and owner decisions | — | L+ | `v0.9.0` (drawings, critic, presets) |
  docs/program/dispatch/ROADMAP-TO-BETA.md:579:| G-11 | 500 pages vs a text analysis that sends the whole text in one call | **accept up to 500 pages; analysis up to an input budget** (≈ 50 pages of text, the number fixed at the freeze from the model and the $1 ceiling), refused up front with a clear reason; chunked analysis in W56 |
  docs/program/PRODUCTION-ADR-PACK-01.md:47:| `AD-18` | `R-146y` | measure on the VPS first (`PROD-20`); the watchdog stays 900 s and an over-budget input gets the typed refusal until the owner chooses; **that choice stays open** |
  docs/program/PRODUCTION-ADR-PACK-01.md:56:| `AD-18` (the choice) | `ADR-0024` section 5 | After the `PROD-20` measurement: raise the 900-second watchdog (overall or per stage), or set a page limit below the 500-page ceiling? |
  docs/program/PRODUCTION-ADR-PACK-01.md:135:| 8 (MED, capacity) | fixed; path corrected | `ADR-0024` section 5, `ADR-0021` section 4, new `AD-18` and `PROD-20`. The watchdog is `src/auditmanager/jobs/lease.py:21` (the judge wrote runs/lease.py; the finding stands). The "better part of an hour" sentence was wrong |
  docs/program/PRODUCTION-ADR-PACK-01.md:152:- Every `AD-` status line, the four index rows and the plan's intro now carry the true s
  ```
- interpretation: `G-11` (owner): accept up to 500 pages, analyse up to a budget, chunked analysis later; `D-162`: the budget models cost, not the context window; `AD-18` / `R-146y`: the watchdog stays 900 s and an over-budget input gets the typed refusal until the owner chooses between raising the watchdog and a page limit. This lane moves the typed refusal from one call to twelve windows by the integrator's brief (`PRODUCTION-WAVE-PW4.md` section 3); the owner's `AD-18` choice stays open and is touched by section 8 of the report.

### P-13 — the tests that pin the old threshold (base)
- captured_at: 2026-10-27
- command: `git grep -l -E "input_budget_characters|analysis_input_budget_exceeded|ANALYSIS_INPUT_BUDGET_EXCEEDED" 6075df88 -- tests`
- captured_output:
  ```text
  tests/contract/api_v1/test_w55b_portal_bundle_seal.py
  tests/contract/domain_p02/test_contract_vocabulary.py
  tests/contract/shared_kernel/test_error_kernel.py
  tests/integration/analysis_text/test_input_budget_arithmetic.py
  tests/integration/analysis_text/test_input_budget_calibration.py
  tests/integration/composition/test_settings_defaults.py
  tests/integration/composition/test_the_served_application_always_passes_a_budget.py
  tests/integration/db/test_ar_v3_run_group.py
  tests/integration/db/test_durable_analysis_effects.py
  tests/integration/db/test_routing_refusal_codes_migration.py
  tests/integration/executors/test_explicit_executor.py
  tests/integration/qa_w55b/test_p3_input_budget.py
  tests/integration/recovery/test_product_purge_run_group.py
  tests/integration/runs/test_input_budget.py
  tests/integration/runs/test_input_budget_over_http.py
  tests/integration/runs/test_v3_saved_text_layer_probe.py
  tests/integration/runs/test_w53c_exec_closure.py
  tests/unit/runs/test_executor_choice.py
  ```
- interpretation: Of these, `tests/integration/runs/test_input_budget.py` and `test_input_budget_over_http.py` pin the one-call threshold and are updated in this lane (before/after in the report); `tests/integration/qa_w55b/test_p3_input_budget.py` also pins it and is outside the lane's paths (report, integration notes). The composition, executor and contract tests hand a budget through or read the text and are unaffected (run, report section 4).

### P-14 — baseline test results before the first edit
- captured_at: 2026-10-27
- command: `pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis tests/integration/analysis_text`
- captured_output:
  ```text
  542 passed in 20.43s
  ```
- interpretation: Measured on `6075df88` plus the design note (no source edit yet), with the integrator's lane stack `.env`; `tests/integration/runs` on the same tree exited 0 (all passed; the quiet flag hid the count, recounted in the report as the difference).

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/SECTION-CHUNKED-ANALYSIS-01.md`
- `docs/program/tasks/SECTION-CHUNKED-ANALYSIS-01.md`
- `src/auditmanager/analysis/text/**`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/jobs/**`
- `src/auditmanager/runs/**`
- `tests/unit/analysis/**`
- `tests/integration/analysis_text/**`
- `tests/integration/runs/**`

Explanations (outside the machine-checked list): the brief names `analysis/text/**` (not `profiles/**`), `runs/**`, `jobs/**`, `bootstrap/providers.py` and the test directories. `src/auditmanager/analysis/public.py` is added because the context boundary (`tests/contract/architecture/test_alr05_boundaries.py`) lets `runs` import `analysis` only through it: additive exports only (nine new names and eight parameter-name aliases), no existing line changed. `bootstrap/providers.py` is allowed by the brief and **not edited** (P-10). `tests/integration/sections` and `tests/unit/runs` are allowed by the brief and needed no edit.

## Lane resources

The integrator's lane stack, shared and already up (`/root/projects/PDF-Analysis/.local/worktrees/ar-close-1026/.env`, copied untracked into the worktree). No instance of the lane's own. Tests that create rows with committed transactions (the kill cases) use fresh identities; the full `tests/integration/runs` directory was also run on a private database `lane_ch_private_01` created and dropped by the lane, so that residue of mutation experiments in the shared database could not colour the result.

## Forbidden hotspots

- `contracts/**`, `web/**`, `db/migrations/**`, `infra/**`
- `src/auditmanager/analysis/text/profiles/**`, `src/auditmanager/optimisation/**`
- `fixtures/recorded/sections/**` (no recording was needed: the window cases use scripted adapters, no new fixture directory)
- the AR v3 path (`runs/v3_*`, `analysis/profiles/ar_v3/**`, `_refuse_over_budget`, `v3_group.py`)
- root dependency/lock files, `bootstrap/**` other than `providers.py`, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, rulings, ADRs

## Non-goals

- A contract change, a migration, a new category, a norm, a severity, a prompt edit of any section profile.
- Cross-window findings (a finding that needs two windows is not found; the run says so).
- Yielding at a window boundary when the 900-second watchdog fires (a window in flight then is ambiguous, as a single call is).
- A pre-flight cost estimate of the whole plan (the ceiling is enforced on measured spend at window boundaries).
- OCR text, norms, facets or the critic in the windows.

## Deliverables

- `analysis/text/windows.py` (policy, plan, request, key, custody seam), `analysis/text/windowed.py` (the stage), `budget.py` (`MAX_ANALYSIS_WINDOWS`, `windowed_budget_characters`), `adapter.py` (`user_content`), exports.
- `jobs/repository.py` (`completed_window_calls`, the narrowed reclaim predicate), `runs/window_reply_custody.py`, `runs/executor.py` (wiring), `runs/commands.py` (the window-aware start-time refusal).
- Tests: `tests/unit/analysis/test_text_windows.py`, `tests/integration/analysis_text/test_text_windowed_stage.py`, `tests/integration/runs/test_text_windows_executor.py`, `test_window_reply_custody.py`, `test_completed_window_calls.py`; `test_input_budget.py` and `test_input_budget_over_http.py` updated.
- `docs/program/SECTION-CHUNKED-ANALYSIS-01.md` (design, files, mutation table, before/after, commands, limits, integration notes).

## Required tests

- command: `pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/analysis tests/integration/analysis_text tests/integration/sections tests/contract/analysis_packages tests/contract/architecture`
- expected: all pass (833 on the lane tree)
- command: the same with `DATABASE_URL` set to a migrated private database: `... tests/integration/runs`
- expected: all pass (860 on the lane tree)
- command: `pytest ... tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` and `git diff --check`
- expected: pass

## Integration contract

- Provider side: `analysis.public.run_text_analysis_windows`, `text_window_policy`, `WindowCustody`, `WindowIdentity`, `RecoveredWindow`, `WindowPolicy`, `MAX_ANALYSIS_WINDOWS`, `windowed_budget_characters`; `jobs.public.CompletedWindowCall` and `JobRepository.completed_window_calls`.
- Consumer side: `runs/executor.py::_run_text_analysis_stage` chooses the windowed stage exactly when the version's recorded count is above the per-call budget; `start_audit_run` / `reaudit_run` refuse above `budget x MAX_ANALYSIS_WINDOWS` with `character_count` and `budget_characters` (the latter now that limit).
- Persisted: one `model_call` and one `provider_call_effect` per window (existing tables); `model_call.parameters` carries `text_window_*` keys; a private blob of role `analysis_text_window_reply` per fresh window; the text stage's `stage_result.metrics` gains the `windows_*` scalars.
- Reclaim: a `completed` live effect whose `model_call` carries `text_window_reply_blob_id` no longer makes a lost Attempt ambiguous; nothing else about the reclaim changed.

## Failure/idempotency/security cases

- Replaying a finished window needs its key (text digest, range, profile, model, request), its call/effect pair to agree, its blob to match the digest, size, envelope and call: each refusal is shown (report, mutation table).
- A saved reply is untrusted text and takes the same parse and grounding as a fresh one; a quote on a page outside its window is dropped and counted.
- A window in flight at a kill, or an answer received and not completed, stays an ambiguous effect: the run fails `provider_outcome_unknown` and no second call is made.
- A failed or stopped run publishes none of the observations of the windows that did finish.
- No secret, no path and no provider text in an error message; messages name the window by number and pages only.

## Rollback / feature flag

`MAX_ANALYSIS_WINDOWS = 1` in `analysis/text/budget.py` restores the one-call behaviour exactly: the start-time limit equals the per-call budget and `text_window_policy` never returns a policy. Held by `test_one_window_as_the_limit_restores_the_one_call_refusal` and `test_one_window_as_the_limit_is_the_rollback_and_never_windows`. Nothing to migrate back: windowed runs leave ordinary `model_call` rows and unbound reply blobs.

## Handoff

- changed files: see `docs/program/SECTION-CHUNKED-ANALYSIS-01.md` section 2.
- commands/results: see the same file, section 7.
- known limits: section 8 of the report (the 900-second watchdog with a window in flight; no pre-flight cost estimate; the contract prose of the budget refusal; one out-of-lane test pins the old threshold).
- integration notes: section 9 of the report.
