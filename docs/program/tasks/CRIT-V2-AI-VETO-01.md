# Task CRIT-V2-AI-VETO-01 — the plan v2 AI critic vetoes «снять»

## Outcome
The precedent pass reads the records of the plan v2 AI critic pass as AI records, so `accept` and `needs_human` veto «Рекомендовано снять», as in v3 (`R-157l`, `ADR-0029` decision 14). The deterministic critic of plan v2 keeps counting as «reviewed» and never vetoes.

Owner: any precedents lane; one writer of `src/auditmanager/precedents/run_pass/critic_input.py` at a time.

## Depends on
- none; the ruling is `R-157l` (`docs/program/OWNER_RULINGS_2026-09-17.md` section 3.61), recorded on `origin/dev`.

## Due
Before any section's refusal marks (decision 6) are switched on. While every section's marks are off (the default), the gap shows nothing.

## Today
`read_critic_plan` treats a marked v2 run (`original_review: deterministic-v1`) as `deterministic_plan=True`. `_decision_of` then returns `DECISION_DETERMINISTIC` for every reviewed record, including the AI pass's records.
- An AI-pass record has `mode: substantive`, `model_called: true` and `llm_decision`, written by `analysis/extended/substantive_review.py` `parse_substantive_reply` and stored by `runs/v2_quality.py`.
- The deterministic record is moved to `structural_critic` by the AI pass.

## Change
- **Allowed paths:** `src/auditmanager/precedents/run_pass/critic_input.py` and `tests/unit/precedents/test_critic_input.py`.
- **The rule:** in a marked v2 run, a reviewed record is read by its own kind.
  - An AI record (`model_called` is `true` and `mode` is not `deterministic`) maps `llm_decision` exactly as v3 does, with an unreadable decision counting as `needs_human`.
  - A deterministic record stays `DECISION_DETERMINISTIC`.
- **Not reviewed:** the AI pass's placeholder (`model_called: false`, `review_status: not_reviewed`) stays not reviewed.
- **`CriticPlan.kind`:** choose a value that does not mislabel a run whose AI pass ran, and update the docstring to state the rule.
- **No change to:** the core (`precedents/votes.py`, `hints.py`), contracts, migrations, the deterministic critic, or the v3 path.

## Checks
- `tests/unit/precedents/test_critic_input.py`, with new cases:
  - a v2 AI `accept` vetoes;
  - `needs_human` vetoes;
  - an unreadable decision vetoes;
  - `reject` does not veto;
  - a deterministic-only v2 record never vetoes;
  - an unreached placeholder is not reviewed;
  - v3 is unchanged.
- Run the remaining `tests/unit/precedents` and `tests/integration/precedents` files that import `critic_input`.

## Integration and rollback
A behaviour change behind the per-section refusal-mark switches, which are off by default. Publish to `origin/dev` after the focused checks.
- A release note is needed only if the change ships while some section's refusal marks are on.
- Rollback is a revert of the commit.

## Status
**Done 2026-11-19** by the fork-storage session (`pdf-analysis-16`, earlier `pdf-analysis-ba`/`-df`) on the owner's poll answer «Сделай сейчас».

- **The change:** `_decision_of` reads a v2 record as the AI pass's only when `model_called` is `true` and `mode` is not `deterministic`; such a record maps `llm_decision` as v3 does. `read_critic_plan` reports `kind: ai` for a marked v2 run whose AI pass left a record.
- **Checks:**
  - `tests/unit/precedents/test_critic_input.py`: 56 passed, 11 of them new. Against the previous module the 6 new veto cases fail and the counter-cases pass.
  - `tests/unit/precedents` together with the two `tests/unit/analysis_extended` files that reference the module: 414 passed, 1 failed. The failure, `test_advice.py::test_the_core_imports_no_other_bounded_context`, fails the same way on the base `12d1055f9` (imports of `candidate_context.py`).
- **Not run:** `tests/integration/precedents/test_precedent_pass.py`, which needs a real PostgreSQL. Its v2 cases use only deterministic records, whose reading is unchanged.
