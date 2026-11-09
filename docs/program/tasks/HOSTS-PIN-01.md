# Task HOSTS-PIN-01 — four new model pins in the provider lock

## Outcome
`docs/program/P02_LOCK.json` pins `claude-opus-5-5`, `claude-sonnet-5-5`, `gpt-6.1-sol` and `gpt-6-astra` next to the three existing models, each with its rates and a cited source. `pinned_models()` returns seven pins; the two tests that held the closed set of three move with it. Nothing else changes: no catalogue, no code, no contract.

## Depends on
- HOSTS-ADR-01

## Frozen inputs
- domain contract: 1.44.0, unchanged
- API contract: 1.44.0, unchanged
- analysis/comparison/event contract: 1.44.0, unchanged
- migration head: `0061_decision_memory_m2`, unchanged
- base commit: `8f76b4ed6daadad95f9c001e2c2c0dca717aad2d`
- architecture: `docs/architecture/adr/ADR-0028-hosts-and-stage-models.md` decision 13; ruling `R-153b` (lifts `R-143g` for this work; for this change the lock is edited by this task)
- the lock's structure: `models` is a dict of tier name → `{model_id, input_per_mtok_usd, output_per_mtok_usd}` read by `load_provider_lock` in `src/auditmanager/analysis/text/lock.py` (an entry without `model_id` is skipped as an annotation; the tier named `primary` is the primary model). This task adds **four new tier keys** and keeps the existing three (`primary`, `cheaper_tier`, `codex_subscription`) unchanged. The file is hashed into the build identity (`src/auditmanager/releases/build_id.py:21`), a content hash computed at start; no tree file stores its value, so nothing is recomputed or moved.
- rates and facts handed over by the coordinator (Anthropic's model table, the claude-api reference, cached 2026-10-06):
  - `claude-opus-5-5`: 4.00 USD input / 20.00 USD output per million tokens; cache read 0.20 USD; 1M context; 128K maximum output; effort low to max with default medium. Thinking cannot be disabled: `{type: "disabled"}` or `budget_tokens` return 400. Our request bodies use `{"type": "adaptive"}` (`src/auditmanager/analysis/extended/core.py:260`, `workflow.py:94`, `analysis/text/adapter.py:155`), which is fine.
  - `claude-sonnet-5-5`: 2.00 USD input / 10.00 USD output per million tokens; 1M context; 128K maximum output; effort default high with recalibrated levels; `{type: "disabled"}` returns 400.
  - `gpt-6.1-sol` and `gpt-6-astra`: take the rates from `https://developers.openai.com/api/docs/models/gpt-6.1-sol` and `https://developers.openai.com/api/docs/models/gpt-6-astra`, in the same form as the existing `gpt-6-sol` entry. They are reference only: calls through a subscription are `billing = not_metered`.
- the executor must re-check the two Claude rates against the live pricing page and cite the page and the date in the entry's `$comment`, as the existing `codex_subscription` entry does.

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `docs/program/P02_LOCK.json` (`models`)
- enumerator_owner: HOSTS-PIN-01
- totality_query: `python3 -c "import json; print(sorted(v['model_id'] for v in json.load(open('docs/program/P02_LOCK.json'))['models'].values() if isinstance(v, dict) and 'model_id' in v))"`

## Captured premise evidence
- premise: the lock holds three models and two tests assert that closed set

### P-01 — the pins now
- captured_at: 2026-11-09
- command: `python3 -c "import json; print(sorted(v['model_id'] for v in json.load(open('docs/program/P02_LOCK.json'))['models'].values() if isinstance(v, dict) and 'model_id' in v))"`
- captured_output:
  ```text
  ['claude-opus-5', 'claude-sonnet-5', 'gpt-6-sol']
  ```
- interpretation: seven are expected after this task; the three above stay.

### P-02 — the closed-set assertions
- captured_at: 2026-11-09
- command: `git grep -n "PINNED_MODEL_IDS = \|assert PINS == " -- tests`
- captured_output:
  ```text
  tests/integration/analysis/test_provider_lock_refusals.py:40:PINNED_MODEL_IDS = {PRIMARY_MODEL_ID, CHEAPER_MODEL_ID, CODEX_MODEL_ID}
  tests/unit/executors/test_model.py:44:    assert PINS == {"claude-opus-5", "claude-sonnet-5", "gpt-6-sol"}
  ```
- interpretation: these two lines move. Any further hit of the same sweep is reported to the integrator, not edited (it is outside the allowed paths).

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `docs/program/P02_LOCK.json`
- `tests/unit/executors/test_model.py`
- `tests/integration/analysis/test_provider_lock_refusals.py`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`
- `src/auditmanager/analysis/text/lock.py` and every other source file: the loader already accepts any tier key
- `scripts/model_probe/probe.py`: it iterates every pin (`probe.py:551`) and is not run by this task
- root dependency/lock files (`uv.lock`, `pyproject.toml`), global styles

## Non-goals
- no catalogue file (`HOSTS-SEAL-1`), no efforts, no `accepted_reported`
- no change of the existing three entries or of `provider_configuration`
- no model call and no live probe of the new identities

## Deliverables
- four new `models` entries; the Claude entries cite the pricing page and its date in `$comment`; the two OpenAI entries cite their model page in the form of the `codex_subscription` entry
- the two test files expect seven pins; the new ids are literals there, so a lock edit not mirrored is a red test
- a note in the handoff of the rate source and the check date

## Required tests
- command: the project's Python (the venv named by `FOUNDATION_PYTHON` in the `Makefile`), `-m pytest tests/unit/executors/test_model.py tests/integration/analysis/test_provider_lock_refusals.py -q`
- expected: pass; a test that removes one new pin from a copy of the lock fails on the closed-set assertion

## Integration contract
`HOSTS-SEAL-1` builds the catalogue over these seven pins and relies on `pinned_models()` returning them in the lock's order. Every estimate that names a new model reads its rates from here.

## Failure/idempotency/security cases
- no model id appears under two tiers: the totality query above must list seven distinct ids
- a rate is a positive number; the cost tests of the existing pins keep passing

## Rollback / feature flag
Revert the commit. No data refers to the new pins before `HOSTS-SEAL-1`.

## Handoff
- changed files: the lane lists them; it does not run git, and the integrator commits exactly the allowed paths it changed
- commands/results: the two test files, the totality query, and `git diff --check`
- known limits: the Claude rates come from a cache of 2026-10-06 until the executor re-checks the live page
- integration notes: the build identity changes with the lock by design; it is a content hash, so nothing is recomputed
