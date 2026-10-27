# AR-V3-JUDGE-FIXES-01 — the findings of the independent read of the AR v3 publication and the activation records

**Task:** [AR-V3-JUDGE-FIXES-01](tasks/AR-V3-JUDGE-FIXES-01.md). **Lane:** fix lane B. **Base:** `93bc5037` (tip of `integration/ar-close-1026`). **Branch:** `agent/ar-v3-judge-fixes-01`, not pushed, not tagged. **Date:** 2026-10-28. A read-only judge (J3) reviewed the AR v3 publication and the activation records at `93bc5037`; this lane fixes what it found. Nothing here is an expert review, and nothing was run on a live host.

## 1. Status per finding

| # | Finding | Status | Where |
| --- | --- | --- | --- |
| 1 | The beta classification used the model's label, not the paragraph the citation was grounded to | **Fixed** with a rule that can only withhold more; see the decisions in section 3 | `src/auditmanager/runs/v3_citations.py`, `src/auditmanager/runs/v3_review_artifact.py` |
| 2 | `exportRunXlsx` was closed for every AR v3 beta Run | **Fixed**; the portal-companion condition that remains is typed and unchanged (section 6) | `src/auditmanager/bootstrap/adapters.py` |
| 3 | Owner steps 10b/11 could not run as written on the live stand | **Rewritten** in the container form, checked against `compose.server.yml`, `Dockerfile.api`, the runbook and the two scripts that already do this; **not run** | `AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01.md` |
| 4 | Rollback was incomplete | **Fixed**: queued/running Runs die (with the code that does it), published findings and verdicts stay readable and decidable, `restart` re-reads no environment | same file |
| 5 | «числовые выводы недоступны» in the sealed attestation | **Reworded** in the live seal values (`AR-V3-PROMOTE-01.md` section 6a) and in the owner steps; the custody-lane record (section 6) keeps what that file was sealed with | `AR-V3-PROMOTE-01.md`, owner steps |
| 6 | «карт, векторов и сводных значений» overstated the independent check | **Reworded** the same way: «проверено соответствие байтов и дайджестов, векторы заново не считались» | same |
| 7 | `ar-v3-beta/README.md` stale | **Updated**: states, step list, D6, seal values now point to `AR-V3-PROMOTE-01.md` section 6a as the single source; `query-texts.json` token sentence corrected | `README.md`, `query-texts.json` |
| 8 | The 10b loops did not stop on the first refusal | **Fixed**: both loops run in a `set -euo pipefail` subshell and grep the expected output line | owner steps |

## 2. Files (13: the 12 of `git diff --name-only 93bc5037..HEAD` before this report, and this report)

Code (3): `src/auditmanager/runs/v3_citations.py`, `src/auditmanager/runs/v3_review_artifact.py`, `src/auditmanager/bootstrap/adapters.py` (the export reader seam only: a new module-level `_read_citations_for_export`, and the `read_citations=` argument).
Tests (4): `tests/unit/runs/test_v3_rebound_classification.py` (new, 23 tests), `tests/integration/runs/test_v3_review_artifact.py` (modified, 17), `tests/unit/exports/test_xlsx_v3_citation_stage.py` (new, 2), `tests/integration/exports/test_xlsx_v3_run.py` (new, 12, private database).
Documents (6): `AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01.md`, `AR-V3-PROMOTE-01.md`, `ar-v3-beta/README.md`, `ar-v3-beta/query-texts.json` (one documentation string, `length_rule.estimate_method`, not data: the stale sentence was there and not in the `comment` field the brief named), `tasks/AR-V3-JUDGE-FIXES-01.md` and this report.

## 3. Finding 1 — the rule, and what each case does

The brief's repro is reproduced (task file P-04): `ground_norm_observation` with label `N1` bound to paragraph A and a quote from paragraph B of the same document returns `[('N1', 'npar_B', 'rebound')]`. The set's `rebinding_paragraphs` is every reliable paragraph of the mapped documents, so the target can be a paragraph a context-only topic sends, one that no item sent, or another topic's. The planner (`plan_v3_beta_citation_review`) and the artifact builder (`build_v3_beta_review_artifact`) now share one function, `grounded_citations_are_provisional`; the terminal rebuilds the review through the same planner and compares bytes with the sealed artifact, so it needs no change and cannot disagree.

A proposal is provisional only if, for **every** citation: the labelled item is `provisional_citation`; the grounded paragraph is one of the **labelled item's own rows** in the set's prompt part; and, if the citation is `rebound`, no context-only item sends that paragraph either. Anything else is withheld with the existing `context_only_or_mixed_source` disposition (no wire value is added). An unknown label, a label that differs between the proposal and its grounding, and an unknown grounding state are refusals.

| Case | Outcome |
| --- | --- |
| verified in the labelled provisional item's own row | provisional (unchanged) |
| rebound to another row of the **same** provisional item | provisional (unchanged: the text is in that topic's own span) |
| rebound to a paragraph of a context-only item | **withheld** (the judge's case) |
| rebound to a reliable paragraph that no item sent (outside every decided span) | **withheld** (the judge's case) |
| rebound to a paragraph of **another provisional** item | **withheld** — the decision asked for: the label names the topic, the quote does not ground it, and the system does not re-attribute a finding to another topic |
| rebound into a row that the labelled item and a context-only item both send | **withheld** |
| one bad citation among several | the whole proposal is withheld |
| labelled item context-only, or mixed labels | withheld (unchanged) |
| **verified** in a row that a context-only item also sends | **provisional by its label** — a deliberate limit, below |

**The limit, stated plainly.** The judge asked to withhold when the paragraph is in a context-only item; this lane did that for rebound citations only. A verified citation is the very row the model was shown under its provisional label, so the map's pairing decides. The first version of this fix withheld that case too, and it withheld the F2 finding of the recorded-group worlds (`test_v3_decisions_over_http.py`, `test_v3_recorded_group_over_http.py`), because their synthetic sets send **one paragraph under every item of a scope**. The real beta maps share no row between a provisional and a context-only item (`decisions.json` spans are disjoint, F2 and A2 sets carry target rows only because one window per item exceeds the 22,000-character cap: `AR-V3-PROMOTE-01.md` section 4), so the stricter rule changes nothing on the real data. If the owner wants it, it is one clause (`any(modes.get(carrier) != PROVISIONAL_MODE ...)` for verified citations too) plus a change of those synthetic worlds. The set bytes do not say which rows of an item are reviewed targets and which are retrieved windows, so "the item's span" is the item's rows as the model saw them; this is the same status that a verified citation of a window row has today.

## 4. Finding 2 — the export

`read_verified_citations` takes the certifying stage as an argument and defaults to `norm_verification`; its header query is an inner join on that stage. The Excel export is handed the reader by the composition root and calls it with `run_id`, `version_uid` and `profile_id` only (`exports/xlsx/certified_package.py` lives under `exports/`, not `findings/`), so the choice is made where the reader is handed over: `_read_citations_for_export` picks `ar_v3_citation_review` for the AR v3 beta profile and `norm_verification` for every other. No public signature changed; the export context still imports nothing from `findings`.

`required_value` / `stated_value` stay unserved: nothing under `src/auditmanager/exports` mentions either (task file P-07), and the integration test asserts that no cell of either sheet equals either stored value and that the workbook has the same eleven columns.

## 5. Mutation table

Method: a throw-away harness (kept in the session scratchpad, not in the repository) replaces one text anchor of a committed file, runs the named tests, writes the original text back and prints `git diff` against `HEAD`, which was empty after every row. «red» is the number of failing tests; the first row of each block is the unmutated baseline.

**Finding 1** — tests: `test_v3_rebound_classification.py`, `test_v3_review_artifact.py`, `test_v3_corpus_citation_bridge.py` (baseline 53 passed).

| id | mutation | red |
| --- | --- | ---: |
| M1-1 | classification by the label only (the previous behaviour) | 15 |
| M1-2 | the labelled item need not own the grounded paragraph | 7 |
| M1-3 | a rebound citation may land where a context-only item also sends | 3 |
| M1-4 | the labelled item's mode ignored | 8 |
| M1-5 | the unknown-state refusal removed | 1 |
| M1-6 | the labels/grounding length check removed | 1 |
| M1-7 | the label comparison removed | 1 |
| M1-8 | a duplicate label accepted by the row index | 1 |
| M1-9 | a prompt row without a paragraph id accepted | 1 |
| M1-10 | the planner back to label-only (the builder still checks) | 7 |
| M1-11 | the builder back to the label-only check | 3 |
| M1-12 | the builder turns the rule's refusal into success | 2 |

Two mutations survived their first run and led to a change. In the first draft of the rule a separate clause «the paragraph is carried by at least one item» was green when removed, because for a rebound citation it is subsumed by «the labelled item carries it»; it was folded into that clause, and a rule-level test for the only case left (a *verified* citation on a paragraph no row carries: inconsistent input) now fails under M1-2. M1-12 survived until the builder's `except` was given its own reason (`review_citation_grounding_invalid`) and two cases (unknown state; label differs between proposal and grounding) were added to the refusal table.

**Finding 2** — tests: `test_xlsx_v3_citation_stage.py`, `test_xlsx_v3_run.py` (baseline 14 passed).

| id | mutation | red |
| --- | --- | ---: |
| M2-1 | the adapter always reads `norm_verification` (the previous behaviour) | 10 |
| M2-2 | the adapter always reads the v3 stage | 1 |
| M2-3 | the profile condition inverted | 11 |
| M2-4 | the workbook cell for the norm document carries `required_value` | 6 |
| M2-5 | the use case is handed `read_verified_citations` directly | 1 |

**Failing first.** The classification tests were run before the code and 13 of 18 were red for the stated reason (`((0,), ()) != ((), (0,))`: the rebound proposal was provisional); the five that passed are the controls. The export unit test was red with `'norm_verification' != 'ar_v3_citation_review'`. The integration test `test_the_reader_with_the_v1_v2_stage_does_not_certify_a_v3_run_and_the_export_is_closed` pins the defect itself on a real published v3 Run: the stage-blind reader answers `required_norm_unavailable`.

## 6. What the Excel export still needs

The workbook labels sheets and pages from the version's **portal companion** (`source.structured_companion`) for every Run, v1/v2 included. A version without one — the synthetic bare PDFs of the recorded-group worlds — is refused, typed: `storage_integrity_error` with `role: source.structured_companion`. That is unchanged and a test pins it (`test_without_a_verified_portal_companion_the_v3_export_is_still_refused_and_typed`). The first export attempt on such a version therefore fails with the companion error before the citation reader is reached, which is also why the defect of finding 2 was not seen on the synthetic Runs (`AR-V3-DECISIONS-01.md`, integration note 7).

## 7. Before / after of every modified test

`tests/integration/runs/test_v3_review_artifact.py` is the only modified test. Nothing was removed or loosened.

| Test | Before | After |
| --- | --- | --- |
| helper `_accepted` | one hard-coded paragraph for every label | the paragraph of the label's row (`PARAGRAPH`), optional `paragraph` and `state` |
| fixture `_value()` | prompt rows `{label, item_id}` | rows also carry `norm_paragraph_id` (the builder now reads it) |
| `test_canonical_artifact_has_all_topics_and_only_provisional_grounded_quotes` | same assertions | same assertions (it failed with the old fixture, `review_label_map_invalid`, which is why the fixture was extended) |
| `test_mismatched_or_incomplete_review_refuses` | 8 cases, each asserted only the error code `analysis_input_invalid` (with the old fixture all 8 would have passed for the wrong reason, `review_label_map_invalid`) | the same 8 cases **plus** `REFUSALS[change]`: each case asserts its own reason; 5 cases added (`rebound_into_context`, `rebound_into_unsent`, `rebound_into_shared_context_paragraph`, `unknown_grounding_state`, `grounded_label_differs_from_proposed`) |
| `test_artifact_cap_refuses` | same | same |
| new | — | `test_a_rebound_citation_inside_the_labelled_provisional_row_set_is_sealed`, `test_a_verified_citation_in_a_row_a_context_only_item_also_sends_is_sealed_by_its_label` |

## 8. Commands and counts

All with `.env` copied untracked from `.local/worktrees/ar-close-1026/`, `PYTHONPATH=src:$BS`, one pytest at a time, `--basetemp` in the session scratchpad (removed afterwards); the private databases were created and dropped by the suites' own fixtures (checked afterwards: none left); no docker, no network.

| Command | Result |
| --- | --- |
| `pytest tests/unit/runs tests/unit/findings tests/unit/exports tests/integration/runs tests/integration/findings tests/integration/exports` (on `1bb15e4d`, the last code commit) | **1,508 passed, 2 skipped**, 166 s, exit 0 |
| the four new/modified test files | 23 + 17 + 2 + 12 passed |
| `pytest tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` (committed tree) | **105 passed** |
| `pytest tests/contract/architecture tests/integration/composition/test_composition_root.py test_v3_pack_install.py test_v3_worker_registry.py` | 48 passed |
| `pytest tests/unit/analysis/ar_v3_norm_map/test_decisions_file_shape.py` | 54 passed, 1 skipped; with `AR_V3_DECISIONS_REQUIRE_FINAL=1`: **55 passed** |
| governance one-liner on the task file | `[]` |
| `git diff --check` | clean |

Not run, by the brief: the full gate, the whole `tests/integration`, the web suite, any live provider call.

## 9. Integration notes

1. **Merge:** six commits on `agent/ar-v3-judge-fixes-01` (`git log --reverse --format='%h %s' 93bc5037..HEAD`); no contract, migration, `infra/**`, `web/**` or root file is touched. `bootstrap/adapters.py` is a composition-root file (`AGENTS.md` section 8, case 3): the integrator decides whether the once-per-lane gate applies; the change there is one function and one argument.
2. **Sealed artifacts:** a Run sealed under the previous rule could differ from its rebuild under the new one (the terminal compares bytes). No Run exists on any stand (no pack is installed anywhere), so none is affected.
3. **Seal values:** the next live seal must use `AR-V3-PROMOTE-01.md` section 6a. `AR-V3-ACTIVATION-FEASIBILITY-01.md` section 6 still holds the original proposal and was not edited (outside the grant, history). `.local/ar-v3-draft/pack.json` still carries the custody-lane statement and is not installable; it was not edited.
4. **The owner steps** are written for the live compose stack and are **unverified there** (the list is at the end of that file): the application role's grants for `promote_cli`, whether the deployed image holds the two tools, whether the checkout holds `scopes.json`, and rollback behaviour with the pack removed were read from code, not run.
5. **Candidate follow-ups (not done, outside the grant):** the stricter rule for verified citations (section 3); `web/` copy that tells a user why a version without a portal companion cannot be exported.

## 10. Limits

- The classification of a verified citation in a row shared with a context-only item is the label's (section 3).
- "The item's span" is the item's prompt rows; targets and retrieved windows are not distinguished in the set bytes.
- The export fix is proved at the reader seam (unit, with the adapter), and at the database with the reader the adapter now hands over; the adapter's own `export_run_xlsx` was not driven against the database: it opens its own session, which cannot see the portal-companion row that the test adds inside a rolled-back transaction (the table refuses UPDATE and DELETE, so a committed companion would stay for every later test of the module).
- Disk during the lane: 2.7 GiB free at the end of the last run; the lane left no large files.

## 11. Forbidden paths are untouched

`git diff --name-only 93bc5037..HEAD` lists the files of section 2. None is under `contracts/`, `db/migrations/`, `web/`, `infra/`, a section, comparison or access package, `src/auditmanager/findings/`, `src/auditmanager/exports/`, a root dependency or lock file, `CURRENT_STATE.md`, `DEBT_REGISTER.md`, a ruling or an ADR; `.local/ar-v3-draft/pack.json` was not opened for writing. The command that proves it (prints nothing):

```
git diff --name-only 93bc5037..HEAD | grep -E '^(contracts/|db/migrations/|web/|infra/|src/auditmanager/(findings|exports|comparison|access|optimisation|analysis/text)/|pyproject\.toml|uv\.lock|docs/program/(CURRENT_STATE|DEBT_REGISTER)|docs/adr)'
```
