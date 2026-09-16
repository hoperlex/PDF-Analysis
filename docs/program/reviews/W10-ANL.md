# `W10-ANL` — mutation sweep of `src/auditmanager/analysis/**`

- Session `W10-ANL`, worktree `/root/w10anl`, branch `agent/w10-anl`.
- **HEAD on arrival: `e08da85`** (`docs: the wave 10 dispatch — five parallel sweeps of the
  rule surface`). The brief names base `fb30e96`; `e08da85` is one commit later on the same
  line, so the base premise holds.
- Worktree found already bootstrapped by the killed first attempt: `.venv`, `.env` (instance
  `gate-w10a`, ports 55590/59190/59191, db `audit_w10a`, bucket `auditmanager-gate-w10a`)
  and `web/node_modules` all present. Nothing committed by that attempt.
- Surface confirmed: 32 files, 5005 lines under `src/auditmanager/analysis/`.

## Sweep table

(appended per batch; see below)

## Baseline

`make gate` at `7fcd4d3` (= `e08da85` + this file): **816 passed, 5 skipped, 116 subtests
passed in 192.20s**, `GATE OK`. The brief's expected figure is exact.

### Harness

Mutations are applied to `/root/w10anl-mut/src`, a `cp -a` of the worktree `src/`, with
`contracts/`, `docs/` and `fixtures/` symlinked beside it. Runs go through
`pytest -p mutprobe -o pythonpath=/root/w10anl-mut/src`; `mutprobe` is a plugin whose
`pytest_configure` prints `auditmanager.__file__` and **aborts the run** unless it resolves
under `/root/w10anl-mut/src/`. Every result below is from a run that printed

    [PROBE] auditmanager.__file__ = /root/w10anl-mut/src/auditmanager/__init__.py

Every mutation is applied by a script that refuses a pattern matching other than exactly
once, refuses a no-op replacement, and **prints the mutated line back out of the file on
disk** before the suite runs — the `frozenset() or frozenset({...})` failure mode is
mechanically excluded.

Suite sets:

- `FAST` = `tests/integration/analysis_engine tests/integration/analysis_text` — 143 tests,
  5.8s green at baseline.
- `WIDE` = `FAST` + `tests/replay tests/integration/findings tests/integration/p02_journey
  tests/integration/exports tests/integration/composition tests/contract/analysis_packages`.

Anything green under `FAST` is re-run under `WIDE` before it is called unguarded.

**A measurement error worth recording:** running `tests/integration` wholesale *without*
`make foundation` first produces 11 failures in `foundation/test_idempotency.py`,
`foundation/test_restart_persistence.py` and `p02_journey/test_truncated_end_to_end.py`.
These are migration-state dependent, not a defect and not another session's interference —
`make gate` sequences `make foundation` ahead of the battery and they pass. `WIDE` therefore
excludes `tests/integration/foundation`.

## Sweep table

Screen suite = `tests/integration/analysis_engine tests/integration/analysis_text tests/replay`
(150 tests). Every GREEN row is re-run against the full battery before it is called a
finding; see "Confirmation" below.

### Batch 1 — `analysis/text/textlayer.py`

| id | rule mutated | result | reddened by |
|----|--------------|--------|-------------|
| TL-01 | `artifact_role_unexpected` refusal disabled | **GREEN** | — |
| TL-02 | `artifact_version_unsupported` refusal disabled | RED | `test_partial_and_status.py::test_a_text_layer_of_an_unexpected_version_fails_closed` |
| TL-03 | `normalization_undeclared` refusal disabled | **GREEN** | — |
| TL-04 | `text_layer_empty` refusal disabled | **GREEN** | — |
| TL-05 | `page_sequence_broken` refusal disabled | **GREEN** | — |
| TL-06 | `page_offsets_discontiguous` (per-page) disabled | **GREEN** | — |
| TL-07 | `page_span_length_mismatch` refusal disabled | **GREEN** | — |
| TL-08 | first page must start at zero — disabled | **GREEN** | — |
| TL-09 | `total_char_count_mismatch` refusal disabled | **GREEN** | — |
| TL-10 | `SUPPORTED_ARTIFACT_VERSION` `1.0.0` → `9.9.9` | RED | `test_corpus_acceptance.py::test_recorded_run_surfaces_every_seeded_issue` |
| TL-11 | `ARTIFACT_ROLE` value changed | RED | same |
| TL-12 | page concatenation separator `""` → `"\n"` | RED | same |
| TL-13 | `Page.contains` lower bound loosened by 1 | **GREEN** | — |
| TL-14 | `Page.contains` upper bound loosened by 1 | **GREEN** | — |
| TL-15 | `TextLayer.slice` start off-by-one | RED | same |

### Batch 2 — `analysis/text/anchors.py`

| id | rule mutated | result | reddened by |
|----|--------------|--------|-------------|
| AN-01 | `char_start = page.char_start + offset_in_page` **+1** | RED | `test_corpus_acceptance.py::test_recorded_run_surfaces_every_seeded_issue` |
| AN-02 | `char_end = char_start + len(candidate)` **+1** | RED | same |
| AN-03 | `char_end` **−1** | RED | same |
| AN-04 | `page.char_start` dropped (page-local offset emitted) | RED | same |
| AN-05 | slice-back belt-and-braces check disabled | **GREEN** | — |
| AN-06 | `page.contains` span-outside-page check disabled | **GREEN** | — |
| AN-07 | unknown page returns `DIFFERENT_PAGE` instead of `ABSENT` | **GREEN** | — |
| AN-08 | search whole document instead of the declared page | RED | same |
| AN-09 | a case-folded candidate added to the retry list | **GREEN** | — |
| AN-10 | `BlockIndex.containing` ambiguity returns a block instead of `None` | **GREEN** | — |
| AN-11 | `BlockIndex.containing` containment upper bound dropped | **GREEN** | — |
| AN-12 | `REASON_DIFFERENT_PAGE` vocabulary value changed | **GREEN** | — |
| AN-13 | `REASON_ABSENT` vocabulary value changed | **GREEN** | — |
| AN-14 | emitted `quote` is the raw quote, not the resolved candidate | RED | `test_offsets_and_grounding.py::test_surrounding_whitespace_is_trimmed_and_the_trimmed_literal_is_emitted` |
| AN-15 | `elsewhere` probe removed; always `ABSENT` | RED | `test_offsets_and_grounding.py::test_a_quotation_cited_on_the_wrong_page_does_not_resolve` |

**The brief is wrong about the off-by-one.** It says criterion 5's stable character offsets
are vulnerable to "the subtle one — an off-by-one, and nobody has tried it". Four separate
offset arithmetic mutations (AN-01 to AN-04) and the `TextLayer.slice` off-by-one (TL-15) all
redden, each caught by `test_recorded_run_surfaces_every_seeded_issue`, which resolves the
seeded quotations against the real corpus text layer. The offset arithmetic is guarded. What
is *not* guarded is the validation of the text layer the offsets are computed against
(batch 1) and the `ungrounded_reason` vocabulary (AN-12, AN-13).

### Batch 3 — `analysis/text/provenance.py` and `analysis/engine/runner.py`

| id | rule mutated | result | reddened by |
|----|--------------|--------|-------------|
| PV-01 | `ModelCallRecord` closed-status-vocabulary refusal disabled | **GREEN** | — |
| PV-02 | answered-status-must-carry-a-response-checksum refusal disabled | **GREEN** | — |
| PV-03 | negative-token refusal disabled | **GREEN** | — |
| PV-04 | `_STATUSES_THAT_ANSWERED` loses `truncated` | **GREEN** | — |
| PV-05 | `CALL_STATUSES` widened with a fourth member `"partial"` | **GREEN** | — |
| PV-06 | `CALL_TRUNCATED` literal `"truncated"` → `"cut_short"` | RED | `test_partial_and_status.py::test_the_truncated_call_is_recorded_as_truncated` |
| PV-07 | `assert_consistent_mode` refusal disabled | RED | `test_provider_modes.py::test_publishing_refuses_a_mode_that_disagrees_with_its_calls` |
| PV-08 | `cost_usd` rounded to 2dp instead of 8 | **GREEN** | — |
| PV-09 | `cost_basis` default `"estimated"` → `"reported"` | **GREEN** | — |
| RN-01 | `skip_not_allowed` refusal disabled | **GREEN** | — |
| RN-02 | `partial_not_allowed` refusal disabled | **GREEN** | — |
| RN-03 | missing-required-input branch disabled | RED | `test_fail_closed.py::test_a_missing_required_input_fails_before_the_stage_runs` |
| RN-04 | missing-required-output branch disabled | RED | `test_fail_closed.py::test_a_stage_that_omits_a_required_output_is_failed_not_succeeded` |
| RN-05 | handler-must-return-`StageProduction` refusal disabled | **GREEN** | — |
| RN-06 | *(mutation was semantically inert — see RN-06b, batch 4)* | n/a | n/a |
| RN-07 | `assert_status_allowed(...)` call removed from `_result_for` | **GREEN** | — |
| RN-08 | `reason="missing_required_input"` → `"inputs_incomplete"` | RED | `test_fail_closed.py::test_a_missing_required_input_fails_before_the_stage_runs` |
| RN-09 | missing-output code `ANALYSIS_FAILED` → `ANALYSIS_INPUT_INVALID` | RED | `test_fail_closed.py::test_a_stage_that_omits_a_required_output_is_failed_not_succeeded` |
| RN-10 | `_elapsed_ms` zero clamp removed | **GREEN** | — |

RN-08 and RN-09 are the good news the brief asked for: `test_fail_closed.py` asserts the
*rule* that refused, not merely that something refused. Changing the reason string or the
catalog code reddens it. That is the discipline wave 9 found missing elsewhere.

**RN-06 is a mutation that did not mutate**, the exact failure the brief warns about. I wrote
`artifacts=tuple(getattr(error, "_artifacts", ()) or ())` to make a failed result carry an
artifact; `DomainError` has no `_artifacts`, so it evaluates to `()` — the original value. The
readback showed the new line faithfully and the run was green, and the green meant nothing.
Caught by re-reading my own mutation for *semantics* after the readback confirmed its *text*.
Re-run as RN-06b.

### Batch 4 — `engine/registry.py`, `engine/result.py`, `text/config.py`, `text/lock.py`, `text/cost.py`, `text/profile.py`

| id | rule mutated | result | reddened by |
|----|--------------|--------|-------------|
| RN-06b | failed result carries an artifact — *mutation raised `NameError`, no `ArtifactRef` import* | invalid | re-run as RN-06c |
| RG-01 | `_EXPECTED_CONTRACT` identity refusal disabled | **GREEN** | — |
| RG-02 | unknown-stage refusal disabled | RED | `test_fail_closed.py::test_an_unknown_stage_is_refused_by_the_registry` |
| RG-03 | `reason="unknown_stage"` → `"stage_not_found"` | **GREEN** | — |
| RG-04 | `required_inputs` filter ignores the `required` flag | RED | `test_fail_closed.py` |
| RG-05 | `required_outputs` filter yields nothing | RED | `test_fail_closed.py` |
| RG-06 | `skip_allowed` default `False` → `True` | **GREEN** (by construction) | — |
| RG-07 | `partial_allowed` default `False` → `True` | **GREEN** (by construction) | — |
| RG-08 | `succeeded_requires_all_required_outputs` default `True` → `False` | **GREEN** (by construction) | — |
| RG-09 | `_EXPECTED_CONTRACT` literal changed | RED | collection-time refusal |
| RS-01 | `_METRIC_KEY` pattern → `^.*$` | **GREEN** | — |
| RS-02 | `_ARTIFACT_ROLE` pattern → `^.*$` | **GREEN** | — |
| RS-03 | `_SHA256` pattern → `^.*$` | **GREEN** | — |
| RS-04 | `_BLOB_ID` pattern → `^.*$` | **GREEN** | — |
| RS-05 | `size_bytes >= 0` refusal disabled | **GREEN** | — |
| RS-06 | `CONTRACT_VERSION` `1.0.0-draft.1` → `2.0.0` | **GREEN** | — |
| CF-01 | `DEFAULT_RUN_COST_CEILING_USD` 1.00 → 1000.00 | RED | `test_cost_ceiling.py::test_an_expensive_recording_halts_against_the_default_ceiling` |
| CF-02 | ceiling-must-be-positive refusal disabled | RED | `test_cost_ceiling.py::test_a_ceiling_that_is_not_a_positive_number_is_refused` |

**RG-06/07/08 are unreddenable by construction.** They are the `default` argument of
`policy.get(key, default)`. All nine stages in `contracts/analysis/v1/stage-registry.json`
declare all four `status_policy` keys explicitly — verified by reading the contract — so the
default is never taken and changing it changes nothing that runs. A test could only redden it
by constructing a synthetic registry document with the key omitted, which asserts a shape the
frozen contract does not have. I did not write one.

**RG-01 vs RG-09 is the asymmetry this wave is looking for.** Changing the constant reddens
(the real document stops matching, so the refusal fires everywhere). *Disabling the refusal*
reddens nothing, because no test ever hands `StageRegistry` a document with a wrong
`contract` field. The guard is reachable — `StageRegistry(document)` takes a mapping
directly — and unguarded.

### Independent authorities located for pinning

- `db/migrations/versions/20260911_0003_open_items.py` — `ck_model_call_status` CHECK:
  `status IN ('succeeded','failed','truncated')`.
- `db/migrations/versions/20260915_0005_truncated_call_status.py` —
  `ck_model_call_truncated_has_response`: `status <> 'truncated' OR response_sha256 IS NOT NULL`.
- `db/migrations/versions/20260910_0002_pc01_schema.py` — `ck_model_call_tokens`:
  `input_tokens >= 0 AND output_tokens >= 0`.
- `db/migrations/versions/20260911_0003_open_items.py` —
  `ck_finding_observation_ungrounded_reason`, the five-value vocabulary.
- `docs/program/P02_SEAMS.md` §5.1 line 484 — the same five values in prose.

`db/` is not my tree, which is exactly what makes these authorities independent of the module
under test.

## Guard 1 — `tests/integration/analysis/test_provider_lock_refusals.py`

14 tests. Answers the dispatch's first named question: **the `analysis.text.lock` unpinned-model
refusal is reachable, and before this file nothing asserted it at all** — not its firing, not
its reason.

Literals pinned, and the authority each is checked against:

| literal | value | authority |
|---------|-------|-----------|
| primary model id | `"claude-opus-5"` | `docs/program/P02_LOCK.json` → `models.primary.model_id` |
| cheaper tier id | `"claude-sonnet-5"` | same, `models.cheaper_tier.model_id` |
| primary input rate | `5.0` USD/Mtok | same, `models.primary.input_per_mtok_usd` |
| primary output rate | `25.0` USD/Mtok | same, `models.primary.output_per_mtok_usd` |
| cost of 1M in + 1M out | `30.0` USD | arithmetic on the two rates above, written out |
| refusal reason | `"model_not_pinned"` | the rule itself; asserted as a literal string |
| refusal stage id | `"text_analysis"` | contract stage identity |

`test_the_lock_document_still_says_what_this_file_pins` reads `P02_LOCK.json` and compares it
against the literals, so a lock edit that is not mirrored here reddens rather than passing
quietly. No constant is imported from the module under test and reused as an expected value.

Red/green, each mutation run against this file alone with the copy proven imported:

| mutation | this file |
|----------|-----------|
| LK-01 `ProviderLock.model` `except KeyError` branch disabled | RED — `test_an_unpinned_model_identity_is_refused_by_model_not_pinned` |
| LK-02 `reason="model_not_pinned"` → `"model_unknown"` | RED — same test |
| LK-03 no-primary-model refusal disabled | RED — `test_a_lock_declaring_no_primary_model_is_refused` |
| LK-04 `cost_usd` negative-token refusal disabled | RED — `test_a_negative_token_count_is_refused_by_cost_usd` |
| LK-05 rate divisor `1_000_000.0` → `1_000.0` | RED — `test_cost_is_the_pinned_rate_per_million_tokens` |
| LK-07 annotation-key skip disabled | RED — `test_the_loaded_lock_carries_exactly_the_two_pinned_identities` |
| LK-08 unreadable-lock message interpolates the path | RED — `test_an_unreadable_lock_document_names_no_path` |
| CF-04 `resolved_lock.model(model_id)` deleted from `load_provider_config` | RED — `test_configuration_refuses_an_unpinned_model_before_the_run_starts` |

LK-05 and LK-06 already reddened under the pre-existing suites; LK-05 is kept because it also
pins the rate arithmetic against the lock. LK-07 and LK-08 were green everywhere before.

## Guard 2 — `tests/integration/analysis/test_profile_identity_is_pinned.py`

11 tests. The profile and prompt-bundle lock the dispatch named.

**A pre-existing instance of the wave-9 defect, in a tree I do not own.**
`tests/integration/analysis_text/test_profile_and_artifact.py::test_the_profile_is_resolved_by_a_pinned_identity`
does not pin the identity:

```python
resolved = resolve_profile(AR_TEXT_PROFILE.analysis_profile_id)
assert resolved is AR_TEXT_PROFILE
assert str(AR_TEXT_PROFILE.analysis_profile_id).startswith("ap_")
```

It feeds the module's own constant back into the module and asserts the answer is the
module's own object — both sides move together — and `startswith("ap_")` holds for any ULID.
`test_the_identities_are_stable_across_resolutions` compares `resolve_profile()` with itself
and has the same property. Changing the pinned ULID (PR-01) is green across all three
suites. Left unrepaired; it belongs to whoever owns `tests/integration/analysis_text/`.

Literals pinned, and their authority:

| literal | value | authority |
|---------|-------|-----------|
| `ANALYSIS_PROFILE_ID` | `"ap_01M25P3TH08VVTTGJRXYBZZ7RP"` | **this file** — see below |
| `PROMPT_BUNDLE_ID` | `"pb_01M25P3TH0PDQYVKTRQFEM0CYS"` | **this file** |
| `PROFILE_VERSION` | `"1.0.0"` | this file |
| `DISCIPLINE` | `"AR"` | this file |
| `STAGE_ID` | `"text_analysis"` | `contracts/analysis/v1/stage-registry.json` |
| `CATEGORIES` | `("internal_contradiction", "explicit_placeholder")` | `db/migrations/versions/20260910_0002_pc01_schema.py` → `FINDING_CATEGORIES`, read and compared in `test_the_pinned_categories_are_the_migration_s_finding_categories` |

There is **no external authority for the two ULIDs**. `P02_SEAMS.md` §4.7 shows
`pb_01M2545JSD15ETSNNV904X991R`, which is an illustrative example in a document body and not
this bundle, and no fixture carries either identity. `ADR-0011` requires the identity to be
immutable, so the literal written in the test *is* the pin: the value may never change, and a
change to it must now be a deliberate edit to this file. That is stated in the file's
docstring rather than left implicit.

| mutation | this file |
|----------|-----------|
| PR-01 `ANALYSIS_PROFILE_ID` one character off | RED — `test_the_profile_identity_is_the_pinned_literal` |
| PR-02 `resolve_profile` unknown-identity refusal disabled | RED — `test_an_unregistered_profile_identity_is_refused` |
| PR-04 `PROFILE_VERSION` → `"2.0.0"` | RED — `test_the_profile_declares_the_pinned_version_discipline_and_stage` |
| PR-05 `DISCIPLINE` → `"XX"` | RED — same |
| PR-06 `PROMPT_BUNDLE_ID` one character off | RED — `test_the_prompt_bundle_identity_is_the_pinned_literal` |
| PR-07 `CATEGORIES` widened with a third member | RED — `test_the_profile_declares_exactly_the_two_pinned_categories` |
| PR-08 profile bound to `"block_analysis"` instead of `"text_analysis"` | RED — `test_the_profile_declares_the_pinned_version_discipline_and_stage` |

Writing the categories as a literal caught **my own** wrong guess: I wrote
`("internal_contradiction", "unsupported_claim")` from memory and the test failed. Had I
imported `CATEGORIES` from the module, it would have passed and checked nothing.

## Guard 3 — `tests/integration/analysis/test_model_call_record_rules.py`

22 tests. `ModelCallRecord.__post_init__` makes three refusals and its docstring explains why
duplicating the database's CHECKs at this layer earns its keep. **Nothing tested that any of
the three fires.** All five sweep rows were green everywhere.

This answers the dispatch's `truncated` question for the record layer. PV-04 is the sharp
case: dropping `truncated` out of `_STATUSES_THAT_ANSWERED` lets a truncated call be recorded
with no response checksum — precisely the row migration `0005` added
`ck_model_call_truncated_has_response` to forbid — and it was green.

Literals pinned, and the authority each is read against inside the file:

| literal | value | authority |
|---------|-------|-----------|
| `CALL_STATUSES` | `{"succeeded","truncated","failed"}` | `20260911_0003_open_items.py` → `ck_model_call_status`, parsed out of the SQL and compared |
| `STATUSES_THAT_ANSWERED` | `{"succeeded","truncated"}` | `20260915_0005_truncated_call_status.py` → `ck_model_call_truncated_has_response`, asserted as an exact SQL string |
| non-negative tokens | `>= 0` | `20260910_0002_pc01_schema.py` → `ck_model_call_tokens`, asserted as exact SQL strings |
| cost rendering | `0.00000123` stays `0.00000123` | 246 input tokens at the lock's 5.0 USD/Mtok; at 2dp it renders `0.0` and the call looks free |
| `cost_basis` default | `"estimated"` | the rule itself |

Each refusal is asserted by the text of *its own* message — `"succeeded|truncated|failed"`,
`"claims the provider answered but carries no"`, `"negative token count"` — so a test cannot
pass because a different one of the three checks fired.

| mutation | this file |
|----------|-----------|
| PV-01 closed-vocabulary refusal disabled | RED — `test_a_status_outside_the_closed_vocabulary_is_refused[partial]` |
| PV-02 answered-needs-checksum refusal disabled | RED — `...must_carry_a_response_checksum[succeeded]` |
| PV-03 negative-token refusal disabled | RED — `test_a_negative_token_count_is_refused[-1-200]` |
| PV-04 `truncated` dropped from `_STATUSES_THAT_ANSWERED` | RED — `...must_carry_a_response_checksum[truncated]` |
| PV-05 `CALL_STATUSES` widened with `"partial"` | RED — `...outside_the_closed_vocabulary_is_refused[partial]` |
| PV-05b `CALL_STATUSES` narrowed, dropping `truncated` | RED — `test_each_status_the_database_admits_is_constructible[truncated]` |
| PV-08 `round(cost, 8)` → `round(cost, 2)` | RED — `test_the_record_renders_cost_to_eight_decimal_places` |
| PV-09 `cost_basis` default → `"reported"` | RED — `test_cost_basis_defaults_to_estimated_not_reported` |
| PV-10 `as_dict` hard-codes `"succeeded"` | RED — `test_the_rendered_record_carries_the_status_verbatim` |

PV-05 and PV-05b redden in opposite directions — widening the vocabulary and narrowing it are
caught by different tests — so the set is pinned, not merely bounded on one side.

## A harness fault that produced two false greens, and how it was caught

Midway through I started a screening batch detached in the background and then ran guard
verifications in the foreground. **Both used the same mutation copy at
`/root/w10anl-mut/src`**, so one run's `reset` + mutate raced the other's pytest. Two rows
came back GREEN that are in fact RED: `TL-09` (`total_char_count_mismatch`) against my own
new test file, and — less visibly — the whole of the first `v3` provenance verification and
the first `b1`-against-guard-4 verification ran inside that window.

It was caught because `TL-09` *should* have reddened my own test and did not, and the
isolated re-run disagreed with the batch. A result that contradicts a result I could derive
by hand is the cheapest possible detector; had the corrupted row been one I had no
expectation about, it would have gone into the report as a finding.

**Fix:** `batch.py` now takes `MUT_COPY`, creates a per-run copy directory with its own
symlinks and its own `mutprobe.py`, and the probe asserts `auditmanager.__file__` starts with
*that run's* copy path (`MUT_EXPECT`) rather than a hard-coded one. Concurrent batches are
now isolated.

**Everything measured inside the overlap window was re-run in an isolated copy.** The
re-runs are what this report contains:

- `b1` vs guard 4 — 12 RED / 3 GREEN (`TL-09` flipped to RED).
- `v1` vs guard 1 — 8/8 RED.
- `v2` vs guard 2 — 7/7 RED.
- `v3` vs guard 3 — 9/9 RED.
- batch 5 — discarded and re-run from scratch.

This is worth recording beyond this wave: the mutation method's whole weight rests on the
copy being the thing under test, and two sessions sharing one copy breaks that silently,
with no error and a plausible-looking pass.

## Guard 4 — `tests/integration/analysis/test_text_layer_validation.py`

29 tests. `load_text_layer` makes nine refusals. Exactly one — `artifact_version_unsupported`
— could be reddened by any existing test.

Every document is built in the test; nothing is added to any frozen corpus. Literals pinned:
page one is `"Отчёт за год.\n"` at **14 code points / 24 UTF-8 bytes**, page two
`"Выручка выросла.\n"` at **17 / 31**, the document **31 code points / 55 bytes**. The
Russian text is deliberate: a byte-offset implementation misplaces every anchor while looking
plausible in English, and `55` is exactly the `total_char_count` a byte-counting producer
would write, so it is one of the parametrised refusal cases.

Writing the counts as literals caught **my own** arithmetic twice — I wrote 30 and 56, and
the tests failed until I computed 31 and 55. An implementation-derived expectation would have
agreed with itself.

| mutation | this file |
|----------|-----------|
| TL-01 `artifact_role_unexpected` disabled | RED |
| TL-02 `artifact_version_unsupported` disabled | RED |
| TL-03 `normalization_undeclared` disabled | RED |
| TL-04 `text_layer_empty` disabled | RED |
| TL-05 `page_sequence_broken` disabled | RED |
| TL-06 `page_offsets_discontiguous` (per-page) disabled | RED |
| TL-07 `page_span_length_mismatch` disabled | RED |
| TL-08 first-page-starts-at-zero disabled | **GREEN — dead code, see below** |
| TL-09 `total_char_count_mismatch` disabled | RED |
| TL-10 `SUPPORTED_ARTIFACT_VERSION` changed | RED |
| TL-11 `ARTIFACT_ROLE` changed | RED |
| TL-12 page separator `""` → `"\n"` | RED |
| TL-13 / TL-14 `Page.contains` bounds loosened | GREEN — guarded in guard 5 |
| TL-15 `TextLayer.slice` off-by-one | RED |

### Unreddenable by construction: `textlayer.py` first-page check

```python
if pages[0].char_start != 0:
    raise _invalid("page_offsets_discontiguous", "the first text layer page does not start at zero")
```

`expected_start` is initialised to `0` before the loop, so on the first iteration the in-loop
`if page.char_start != expected_start` **is** `if pages[0].char_start != 0` and has already
refused with the same `reason`. `raw_pages` is checked non-empty above, so the loop always
runs. The post-loop branch cannot execute. The *rule* is enforced and is tested; the *line*
is dead. Reported, not guarded — a test for it would have to claim to distinguish two lines
that produce the same refusal, which it cannot.

**Product note for the owner of `src/auditmanager/analysis/`:** the branch is harmless but
misleading, since it reads as the enforcement of a rule that is actually enforced ten lines
earlier. Left unrepaired.

## Guard 5 — `tests/integration/analysis/test_observations_artifact_rules.py`

23 tests. **The largest single finding of this sweep.** `analysis.text.artifact` is `B4`'s
only input — the grounding gate takes no model input of any other kind — and every one of the
seven refusals standing between the model and that gate was unreddenable:

| id | rule | screen |
|----|------|--------|
| AR-01 | `pages_analysed_unknown` | GREEN |
| AR-02 | `observation_without_evidence` | GREEN |
| AR-03 | `category_not_declared` | GREEN |
| AR-04 | `evidence_page_unknown` | GREEN |
| AR-05 | `evidence_span_length_mismatch` | GREEN |
| AR-06 | `evidence_span_outside_page` | GREEN |
| AR-07 | `evidence_quotation_mismatch` | GREEN |
| AR-08 | **`_validate_anchor(...)` call deleted outright** — removes four at once | GREEN |
| AR-10 | `block_id` written as `null` instead of omitted | GREEN |
| AR-11 | `pages_analysed` neither sorted nor deduplicated | GREEN |
| AR-09 | `ARTIFACT_ROLE` changed | RED |
| TL-13 / TL-14 | `Page.contains` bounds loosened | GREEN |

**Why the existing suites miss all of it.** They pass a well-formed run end to end and assert
the artifact that comes out. That exercises these checks' happy path only. The anchors
`resolve_anchor` produces are correct by construction, so no real run ever hands
`_validate_anchor` a bad one — which is precisely why deleting the call is invisible. The
guards are reached here by constructing `ResolvedAnchor` directly; it is a public frozen
dataclass, so no private surface is touched and no other tree is reached into.

Literals pinned — every offset is hand-checkable against the two page strings:

| literal | value |
|---------|-------|
| page one | `"Отчёт за год.\n"`, code points 0..14 |
| page two | `"Выручка выросла.\n"`, code points 14..31 |
| `"Отчёт"` | 5 code points at document-global 0..5 on page 1 |
| `"Выручка"` | 7 code points at document-global 14..21, on page **2** |
| artifact role / version | `"analysis.text_observations"` / `"1.0.0"` |

The page-boundary tests are the off-by-one the dispatch asked for, in the place where it is
actually unguarded. `"Выручка"` at 14..21 cited as page **one** is off the end of its declared
page by exactly the amount that matters; a span at 13..20 cited as page **two** begins one
code point inside page one. Those two cases pin `Page.contains` from both sides, and both
`TL-13` and `TL-14` now redden.

`test_the_four_anchor_refusals_are_distinguishable_from_one_another` exists because all four
`_validate_anchor` refusals share `ANALYSIS_INPUT_INVALID` and the same `stage_id`. It
asserts the four `reason` values form exactly the expected set, so no one of them can be
deleted and covered by another firing.

All 14 mutations RED against this file, each on the test that names the rule.

## Guard 6 — `tests/integration/analysis/test_status_policy_and_result_shape.py`

43 tests. Covers the dispatch's "fail-closed status mapping" question, the registry's
contract-identity refusal, and the `ArtifactRef` contract shape.

**The status mapping answer is split.** `test_fail_closed.py` covers the two mappings the
runner *produces* — a missing input and a missing output are both `failed` — and it asserts
the catalog code *and* the `reason`, so RN-03, RN-04, RN-08 and RN-09 all redden. That half
is in good order. What nothing covered is `assert_status_allowed`, which the runner's own
docstring says exists "so that anything that ever tries to is refused at the boundary rather
than trusted because the runner is believed not to". Disabling either branch, or deleting the
call from `_result_for` entirely, was green.

Literals pinned against `contracts/analysis/v1/stage-registry.json`, read in the file:
`contract` = `"auditmanager.analysis.stage_registry"`, `contract_version` =
`"1.0.0-draft.1"`, and the three preparation stages' `skip_allowed`/`partial_allowed` both
`false` while `text_analysis` is `partial_allowed: true`, `skip_allowed: false`.

That last asymmetry is load-bearing: `test_text_analysis_may_report_partial_but_still_may_not_be_skipped`
is what makes the two branches distinguishable. Two mutations that cross-wire them —
the skip branch reading `partial_allowed` (RN-01b) and the partial branch reading
`skip_allowed` (RN-02b) — are both caught by it, and neither is caught by a test that only
checks the three preparation stages, since those have both flags false.

| mutation | this file |
|----------|-----------|
| RN-01 skip branch disabled | RED |
| RN-02 partial branch disabled | RED |
| RN-01b skip branch reads `partial_allowed` | RED |
| RN-02b partial branch reads `skip_allowed` | RED |
| RN-01c `reason` → `"status_not_allowed"` | RED |
| RN-02c `reason` → `"status_not_allowed"` | RED |
| RN-11 guard also refuses `SUCCEEDED` | RED (the negative half) |
| RG-01 contract-identity refusal disabled | RED |
| RG-03 `reason="unknown_stage"` changed | RED |
| RS-02 artifact role pattern → `^.*$` | RED |
| RS-03 sha256 pattern → `^.*$` | RED |
| RS-04 blob id pattern → `^.*$` | RED |
| RS-05 `size_bytes >= 0` disabled | RED |
| RS-07 `to_document` grows a `bucket` field | RED |

RN-11 is there because a guard that refuses *everything* would also pass every
refusal-side test. The `SUCCEEDED`/`FAILED` cases pin the other side.

### Batch 5 — `text/artifact.py`, `text/response.py`, `text/stage.py`, `engine/runner.py`

Re-run in an isolated copy after the shared-copy fault. `analysis/text/response.py` results:

| id | rule mutated | result |
|----|--------------|--------|
| RP-01 | category-in-closed-set check disabled | **GREEN** |
| RP-02 | `finding_text` non-blank-string check disabled | **GREEN** |
| RP-03 | `recommendation_text` non-blank-string check disabled | **GREEN** |
| RP-04 | evidence-non-empty-list check disabled | **GREEN** |
| RP-05 | `page_number` int-and-not-bool check disabled | **GREEN** |
| RP-06 | `quote` non-empty-string check disabled | **GREEN** |
| RP-07 | unfinished tail appended as `{}` instead of discarded | **GREEN** |
| RP-08 | `salvaged = truncated` → `salvaged = False` | **GREEN** |
| RP-09 | `malformed += 1` removed | **GREEN** |
| RP-10 | non-dict coerced to `{}` | **GREEN — inert, see below** |

`analysis/text/stage.py`: ST-02, ST-03, ST-06, ST-07, ST-09, ST-10, ST-15 RED; ST-01, ST-04,
ST-05, ST-08, ST-11, ST-12, ST-13, ST-14 GREEN. `analysis/text/artifact.py`: see guard 5.
`RN-06c` (a failed result carrying an artifact, with the import added) RED.

## Guard 7 — `tests/integration/analysis/test_response_parsing_rules.py`

29 tests. **Not one rule in `analysis.text.response` could be reddened by anything.** All ten
sweep rows green.

This is the module that decides what survives a truncated reply. `RP-07` is the one that
matters most: making `_salvage_array` append `{}` for the tail it could not decode — the
closest thing to guessing at a half-written element — changed no test anywhere, and the
module's docstring is explicit that "a half-written contradiction reads exactly like a whole
one".

The existing `test_the_incomplete_tail_of_a_truncated_reply_is_discarded` replays one
recorded truncated variant end to end and asserts the stage's outcome. `parse_response` is a
pure function of a string and a flag, so this file reaches the rules directly with replies
built in the test. No recording is added to any frozen fixture directory.

`test_a_proposal_that_does_not_satisfy_the_shape_is_dropped_and_counted` is parametrised over
17 malformed shapes and asserts **both** halves — the proposal does not appear *and*
`malformed_count == 1`. A rule that dropped without counting passes a test that checks only
the first, which is why RP-09 is caught by the same case as RP-01.

`test_a_page_number_of_true_is_not_read_as_page_one` is stated separately because
`isinstance(True, int)` is `True` in Python: without the explicit bool exclusion, `True`
becomes page 1 and a proposal that named no page acquires one.

9 of 10 RED against this file. **RP-10 was a mutation that did not mutate** — the second one
I wrote this wave. Coercing a non-dict to `{}` leaves `raw.get("category")` returning `None`,
which fails the very next check, so the drop-and-count outcome is identical. Replaced with
two mutations that do change behaviour — deleting the `isinstance` guard outright (RP-10b)
and having it return a fabricated observation (RP-10c) — and both are RED.

## Guard 8 — `tests/integration/analysis/test_stage_status_and_cost_rules.py`

25 tests. The stage-level rules the recorded corpus cannot reach, and the cost meter's two
boundaries.

`test_partial_and_status.py` and `test_cost_ceiling.py` drive the stage through the recorded
adapter and its `variants/` directory, which covers whatever those recordings contain. The
rules below need replies the recordings do not have. This file uses a small scripted adapter
built in the test: `ModelAdapter` is a `runtime_checkable` `Protocol` on the public seam, the
dispatch names scripted adapters as in scope, and nothing is added to `fixtures/recorded/**`.

| mutation | this file |
|----------|-----------|
| ST-01 truncated-with-no-usable-observation branch disabled | RED |
| ST-04 strict-subset clamp disabled | RED |
| ST-05 frontier clamp removed (`analysed = list(pages)`) | RED |
| ST-08 `check_before_call()` moved after `adapter.complete()` | RED |
| ST-11 graph `artifact_role` refusal disabled | RED |
| ST-11b graph role `reason` changed | RED |
| ST-12 graph `artifact_version` refusal disabled | RED |
| ST-16 `_check_graph_version(...)` call deleted | RED |
| ST-14 `cost_basis` hard-coded to `"estimated"` | RED |
| CM-03 `check_before_call` `>=` → `>` | RED |
| CM-04 `charge` `>` → `>=` | RED |
| CM-07 spend checked before being recorded | RED |
| CM-06 `BUDGET_SCOPE_RUN` literal changed | RED |
| CF-01 `DEFAULT_RUN_COST_CEILING_USD` `1.00` → `2.00` | RED |

**CM-04 is the one the dispatch's cost-meter question was pointing at.** The two checks use
different comparisons on purpose — `check_before_call` halts at `>=`, `charge` halts at `>` —
and swapping either was green. The guard pins both directions: a meter charged *exactly* its
ceiling does not halt on that charge (the call is recorded, the run continues) and *does*
halt at the next `check_before_call`. Collapsing the two operators to the same one breaks one
or the other.

ST-08 is asserted by `adapter.calls == 0` — the adapter counts its own invocations — so
"issues no call" is measured rather than inferred from the outcome status.

### A defect found while writing this guard, left unrepaired

`run_text_analysis` puts `cost_basis` in the metrics dict it returns on the **budget-overrun**
path and omits it from the metrics dict it returns on the **success** path, where the basis
reaches the `ModelCallRecord` instead. The code comment beside the success-path `_record`
call says the author's "first attempt set it on the error path's own dict, which the executor
never reads — the figure reached the row and the provenance did not", so the record was fixed;
the metrics asymmetry was not. A consumer reading `metrics["cost_basis"]` gets a value on a
failed run and a `KeyError` on a successful one.

Owning tree: `src/auditmanager/analysis/text/stage.py`. Not repaired — `W10-ANL` writes tests.
`test_cost_basis_reaches_the_record_but_not_the_success_path_metrics` pins the behaviour as
found, so a change to it is deliberate.

## Guard 9 — `tests/integration/analysis/test_ungrounded_reason_vocabulary.py`

19 tests. The `ungrounded_reason` vocabulary and the unresolved-reason rules.

The offset arithmetic in `anchors.py` is well guarded. The **vocabulary is not**: `REASON_ABSENT`
and `REASON_DIFFERENT_PAGE` could be changed to any string at all and nothing noticed, even
though the module's docstring says they are "the `ungrounded_reason` vocabulary of
`P02_SEAMS.md` section 5.1, reused so a diagnostic written here reads the same as one written
by the grounding gate".

Authority: migration `0003_open_items`'s `ck_finding_observation_ungrounded_reason` CHECK,
parsed out of the SQL and compared against the pinned five-value literal set, plus the same
five values asserted present in `P02_SEAMS.md`. The migration's own comment records that the
field "declared a five-value vocabulary and enforced none of it" until that constraint was
added — so a reason string this module invents outside the set cannot be persisted.

| mutation | this file |
|----------|-----------|
| AN-05 slice-back check disabled | **GREEN — but see AN-09b** |
| AN-06 `page.contains` check disabled | **GREEN — by construction, below** |
| AN-07 unknown page → `DIFFERENT_PAGE` | RED |
| AN-09 case-folded candidate added to the retry list | **GREEN — inert, below** |
| AN-09b resolution made case-insensitive | RED |
| AN-09c NFKC normalization applied to model output | RED |
| AN-09d whitespace collapsed in the candidate | RED |
| AN-10 `BlockIndex` ambiguity returns a block | RED |
| AN-11 `BlockIndex` containment upper bound dropped | RED |
| AN-12 `REASON_DIFFERENT_PAGE` value changed | RED |
| AN-13 `REASON_ABSENT` value changed | RED |
| AN-16 `REASON_SPAN_OUTSIDE_PAGE` value changed | RED |
| AN-17 `REASON_LENGTH_MISMATCH` value changed | RED |
| AN-01, AN-02, AN-08, AN-14, AN-15 | RED (already guarded elsewhere too) |

**AN-09 was a third inert mutation of mine.** Adding `lowered = quote.strip().lower()` to the
candidate list yields nothing new for an already-lowercase quote, and for an upper-cased one
the lowered form still is not in the page text. Replaced with AN-09b/c/d, which change the
search itself; all three redden.

**AN-09b is why the file asserts the `reason` and not just "did not resolve".** A
case-insensitive `find` *does* locate the quotation — and is then caught by the slice-back
check, which returns `span_length_mismatch` rather than `quotation_absent`. Asserting only
`isinstance(outcome, UnresolvedAnchor)` passed under that mutation. Asserting
`reason == "quotation_absent"` distinguishes "never found it" from "found it and then
noticed", and that is the whole difference. **This also shows AN-05 is not dead code**: the
slice-back check is what stands between a loosened search and a fabricated anchor.

### Unreddenable by construction: `anchors.resolve_anchor`'s two post-find checks

```python
if text_layer.slice(char_start, char_end) != candidate:   # AN-05
    return UnresolvedAnchor(..., reason=REASON_LENGTH_MISMATCH)
if not page.contains(char_start, char_end):               # AN-06
    return UnresolvedAnchor(..., reason=REASON_SPAN_OUTSIDE_PAGE)
```

With the arithmetic *as written*, neither can fire. `offset_in_page = page.text.find(candidate)`
means the candidate sits at `page.char_start + offset_in_page` in the document-global
sequence, and `load_text_layer` has already proved the pages are contiguous, gapless,
zero-based and that each span's length equals its text's length in code points — so the slice
is the candidate and the interval is inside the page, necessarily.

They are reachable only by (a) breaking the arithmetic, which AN-01 to AN-04 and AN-09b
already redden, or (b) constructing a `TextLayer` directly with pages `load_text_layer` would
refuse. I did not write (b): it would assert behaviour over a shape the loader forbids, which
is the same category as the registry `status_policy` defaults. The checks earn their keep as
defence against a future edit to the arithmetic, and the mutations that represent that edit
are all red. Reported, not faked.

## Guards summary

| file | tests | rules guarded that nothing could redden before |
|------|-------|-----------------------------------------------|
| `test_provider_lock_refusals.py` | 14 | 8 |
| `test_profile_identity_is_pinned.py` | 11 | 7 |
| `test_model_call_record_rules.py` | 22 | 9 |
| `test_text_layer_validation.py` | 29 | 8 |
| `test_observations_artifact_rules.py` | 23 | 12 |
| `test_status_policy_and_result_shape.py` | 43 | 14 |
| `test_response_parsing_rules.py` | 29 | 11 |
| `test_stage_status_and_cost_rules.py` | 25 | 14 |
| `test_ungrounded_reason_vocabulary.py` | 19 | 11 |
| **total** | **215** | **94** |

Every one of the 94 was mutated red against its new guard and green at baseline, each run in
an isolated copy with `auditmanager.__file__` proved to resolve under that copy.

## Guard 10 — `tests/integration/analysis/test_normalization_and_serialization.py`

19 tests. Two pins that decide whether an offset means the same thing twice.

**EX-08 is the sharpest single finding after the `artifact.py` cluster.** Changing the
declared normalization from **NFC to NFKC** in `extraction.normalize` was green everywhere.
NFKC is a *compatibility* normalization: it rewrites ligatures, superscripts, non-breaking
spaces, Roman numerals and full-width forms, changing the code-point length of text NFC leaves
untouched. Every offset in the system indexes the sequence this function produces and `B4`
compares "after that one declared normalization and nothing else", so the swap moves anchors
while `normalization.id` still reads `nfc_v1`.

The corpus contains no character where NFC and NFKC differ, which is exactly why an
end-to-end run over it cannot detect the change. The five strings here are built in the test
— `ﬁ`, `²`, a non-breaking space, `Ⅱ`, `Ａ` — and each is compared against
`unicodedata.normalize("NFC", text)`, **the standard's own answer rather than the module's**,
so the two cannot agree by moving together.

Authorities: `P02_SEAMS.md` §4.3 for `nfc_v1`, `P02_LOCK.json` → `pins.pdfplumber` for the
extractor identity. All 9 mutations RED (EX-06, EX-07, EX-08, EX-09, SZ-01 to SZ-05).

### Batch 6 — the preparation stages and ports

`tests/integration/analysis_engine/test_preparation_stages.py` is thorough and most of this
tree reddens properly: EX-01, EX-02, EX-07, SP-01, SP-02, SP-03, SP-04, SP-06, SP-07, PG-02,
PG-04, PG-05, PG-06, PG-07, PG-08, PG-09 all RED.

Green, and all of them cross-checks over re-extraction consistency:

| id | rule | why it is green |
|----|------|-----------------|
| EX-03 | `page_count_disagreement` — pdfplumber vs the pypdf probe | the two libraries agree on every real PDF |
| EX-04 | `line_traversal_disagreement` — `extract_text_lines()` vs `extract_text()` | pdfplumber is self-consistent |
| EX-05 | `normalization_disagreement` — NFC applied to the join vs to the lines | NFC distributes over the join for this corpus |
| PG-01 | `text_layer_page_count_mismatch` | the geometry stage re-extracts the *same bytes* |
| PG-03 | `text_layer_text_mismatch` | same |
| PG-10 | `missing_source_reference` | the inventory always carries `source_blob_id` |
| SP-05 | `source_unreadable` catalog code | reached, but no test asserts *which* code |

EX-03, EX-04, EX-05, PG-01 and PG-03 are **unreddenable by construction through the stage
seam**: they compare two derivations of the same bytes by the same pinned libraries, and the
libraries do not disagree with themselves. This is the same shape as the wave-8 finding "a
cross-check the twelve operations cannot reach". Reaching them needs a stubbed extractor —
product code, or a fixture PDF chosen to break pdfplumber's internal consistency, which is a
bet on a library bug rather than a test of a rule. Reported, not faked.

`SP-05` is a real but narrow gap: `source_unreadable` is reached by
`test_fail_closed.py`, but nothing asserts the catalog code, so changing
`ANALYSIS_INPUT_INVALID` to `ANALYSIS_FAILED` is invisible. Recorded; not guarded, because the
path is already covered and the marginal value is low next to the rest of this sweep.

## A second self-inflicted fault: mutation runs share the instance with the gate

The first full gate after the guards landed came back **2 failed, 1029 passed, 5 skipped,
116 subtests**, failing:

- `tests/integration/ingest/test_negative_envelope.py::test_negative_fixture_is_refused_by_its_own_rule_and_publishes_nothing[image_only.pdf-page_text-every_page_has_extractable_text]`
- `tests/integration/ingest/test_publication.py::test_baseline_publishes_one_version_and_one_available_blob`

Neither is in my tree and neither is one of my tests. The cause is mine all the same: **batch
6 was running concurrently**, and although its *code* lives in an isolated copy, its *tests*
run against the same PostgreSQL and MinIO instance the gate uses — `gate-w10a`. Batch 6's
mutations included `SP-01` (`page.char_count == 0` refusal disabled) and `SP-03`
(`has_text_layer` forced false), which are precisely the rules
`test_negative_fixture_is_refused_by_its_own_rule_and_publishes_nothing[image_only.pdf-page_text-...]`
exercises. A mutated run that *accepted* `image_only.pdf` publishes rows the unmutated ingest
test then finds.

So the mutation harness isolates the source tree but **not the database**, and a mutation that
disables a refusal writes rows that should not exist. That is a different failure from the
shared-copy fault earlier and it needs a different fix: an isolated `src/` is not an isolated
run.

Per `OPERATING_CONSTRAINTS.md` §9 this is exactly the case §6 does *not* cover, and the way to
tell interference from an accumulated-population defect "costs one command: run your suite
alone against the same database". All mutation processes were killed and `make gate` was
re-run with nothing else touching the instance. **That result is the one recorded below**, and
it is the only gate figure in this report that was measured alone.

**Guidance for the next session running this method:** a mutation batch whose suites write to
PostgreSQL or S3 must not run concurrently with anything else on the same instance, including
your own gate. Offline batches — `analysis_text`, `replay`, and every guard in
`tests/integration/analysis` except none of them — are safe to parallelise; `analysis_engine`,
`ingest`, `foundation` and `p02_journey` are not.

## Product defects, precise and left unrepaired

`W10-ANL` writes tests. Each of these is reported to the tree that owns it.

### 1. `cost_basis` reaches the record on success but not the success-path metrics

**Tree:** `src/auditmanager/analysis/text/stage.py`.
`run_text_analysis` builds two metrics dicts. The budget-overrun path includes
`"cost_basis": ("measured" if response.reported_cost_usd is not None else "estimated")`; the
success path does not, and the basis reaches only the `ModelCallRecord`. A consumer reading
`metrics["cost_basis"]` gets a value on a failed run and a `KeyError` on a successful one.
The comment beside the success-path `_record` call shows the record half was deliberately
fixed after an earlier attempt put it only on the error path; the metrics asymmetry looks like
the other half of that same repair, not left undone on purpose.
Pinned as found by `test_cost_basis_reaches_the_record_but_not_the_success_path_metrics`.

### 2. Dead branch in `textlayer.load_text_layer`

**Tree:** `src/auditmanager/analysis/text/textlayer.py`.
```python
if pages[0].char_start != 0:
    raise _invalid("page_offsets_discontiguous", "the first text layer page does not start at zero")
```
`expected_start` is `0` before the loop, so the in-loop `page.char_start != expected_start`
already refuses this with the same `reason`, and `raw_pages` is checked non-empty first. The
branch cannot execute. Harmless, but it reads as the enforcement of a rule that is enforced
ten lines earlier — a later reader deleting the loop check would find this one "covering" it
and be wrong about why.

### 3. `config.py` says the lock records no ceiling; the lock records one

**Tree:** `src/auditmanager/analysis/text/config.py`.
```python
#: ``OD-03`` owns the figure and has not recorded a machine-readable number in either
#: lock, so this is a deliberately conservative stand-in and not the owner's decision
DEFAULT_RUN_COST_CEILING_USD: Final[float] = 1.00
```
`docs/program/P02_LOCK.json` → `models.run_cost_ceiling_usd` is `1.0`. The two agree today, so
nothing is wrong at run time, but the comment is false and it is the reason the constant is
not read from the lock the way every rate is. Pinned by
`test_the_default_ceiling_matches_the_figure_the_lock_records`, so a future edit to either one
without the other reddens.

### 4. A test that does not test what it is named for

**Tree:** `tests/integration/analysis_text/` — not mine.
`test_profile_and_artifact.py::test_the_profile_is_resolved_by_a_pinned_identity` pins no
identity: it passes `AR_TEXT_PROFILE.analysis_profile_id` into `resolve_profile` and asserts
the result is `AR_TEXT_PROFILE`, so both sides move together, and `startswith("ap_")` holds
for any ULID. `test_the_identities_are_stable_across_resolutions` compares `resolve_profile()`
with itself. Changing the pinned ULID is green across every suite. This is the wave-9 failure
mode already in the tree, found by mutation rather than by reading.
Guard 2 covers the rule; the misleading test is left as found.

## Rules unreddenable by construction, with the argument

1. **`registry._definition_from` `status_policy` defaults** (RG-06, RG-07, RG-08) — all nine
   stages in the frozen contract declare all four keys, so `policy.get(key, default)` never
   takes the default. Verified by reading `contracts/analysis/v1/stage-registry.json`.
2. **`textlayer.load_text_layer` first-page branch** (TL-08) — dead, argument above.
3. **`anchors.resolve_anchor`'s two post-find checks** (AN-05, AN-06) — with the arithmetic
   as written, `page.text.find` plus `load_text_layer`'s contiguity and length invariants make
   both conditions necessarily false. They are live defence against a *future* edit to the
   arithmetic, and every mutation representing such an edit (AN-01 to AN-04, AN-09b) is red.
4. **`extraction` and `page_geometry_extraction` re-extraction cross-checks** (EX-03, EX-04,
   EX-05, PG-01, PG-03) — each compares two derivations of the same bytes by the same pinned
   libraries. Reaching them needs a stubbed extractor (product code) or a fixture chosen to
   break pdfplumber's self-consistency (a bet on a library bug, not a test of a rule).
5. **`response._coerce` non-dict early return** as I first mutated it (RP-10) — coercing to
   `{}` is caught by the very next check. The *guard itself* is reachable and is now guarded;
   only that particular mutation was inert.

Nothing in this list was given a test that would have had to misdescribe what it checks.

## What the brief got wrong

1. **"stable character offsets … the subtle one is an off-by-one, and nobody has tried it."**
   False. Five offset mutations — `char_start +1`, `char_end +1`, `char_end -1`, dropping the
   page base, and `TextLayer.slice` off by one — all redden
   `test_corpus_acceptance.py::test_recorded_run_surfaces_every_seeded_issue`. The offset
   *arithmetic* is among the best-guarded code in the tree. The unguarded off-by-one is one
   layer up, in `Page.contains` and the `artifact.py` span checks that use it (guard 5).
2. **"`tests/integration/analysis/**` — create it; there is no such directory today, which is
   itself worth noting."** Literally true and misleading as framing. There is no directory of
   that exact name, but `tests/integration/analysis_engine/` (47 tests) and
   `tests/integration/analysis_text/` (96 tests) both exist and cover this tree substantially.
   The absence of the directory is not evidence of absent coverage, and reading it that way
   would misdirect a sweep.
3. **"the fail-closed status mapping … is every status now mapped by something that would
   notice a changed mapping?"** Half right. The mappings the runner *produces* are well
   guarded, `reason` and catalog code included. The boundary guard behind them
   (`assert_status_allowed`) was guarded by nothing.
4. **Base commit.** The brief names `fb30e96`; the worktree arrived at `e08da85`, one commit
   later on the same line. Not an error, but the dispatch's own provisioning block would have
   had me re-create a worktree that was already correct.

Everything else in the brief checked out: the instance and ports were free and correct, the
`816 passed / 5 skipped / 116 subtests` figure was exact, `analysis.text.lock` really does
resolve `P02_LOCK.json` from `parents[4]` so the copy needs `docs/` symlinked, 5005 lines
across 32 files is right, and no live provider was needed.

### Why the guard verifications are unaffected by the instance-sharing fault

Several per-guard red/green verifications ran while a screening batch was in flight. They are
sound anyway, and the reason is checkable rather than asserted: **every one of the ten guard
files is pure in-process Python.** None of them imports a blob store, an S3 client, a database
session or either suite `conftest`; they exercise `load_text_layer`, `parse_response`,
`resolve_anchor`, `build_text_observations`, `ModelCallRecord`, `ProviderLock`,
`assert_status_allowed`, `ArtifactRef`, `CostMeter`, `normalize` and `canonical_bytes`
directly, and drive the stage with a scripted adapter. Shared PostgreSQL or MinIO state cannot
change their outcome.

After the harness fix each verification also ran in its own `MUT_COPY`, so source isolation
holds too. The screening batches that *do* touch infrastructure — `analysis_engine` in batches
5 and 6 — are the ones whose concurrent results were discarded and re-run.

## Close

`make gate`, run **alone** against `gate-w10a` with no other process touching the instance:

    35 passed in 29.45s                                   (foundation)
    1050 passed, 5 skipped, 116 subtests passed in 206.00s (battery)
    Test Files  24 passed (24) / Tests 289 passed (289)    (frontend)
    GATE OK: battery, foundation, frontend and whitespace all pass

Baseline was **816 passed / 5 skipped / 116 subtests**; this wave adds **234 tests** and
816 + 234 = 1050. Skips and subtests are unchanged, so nothing was turned off to get here.
The B5 corpus run inside the battery reports the same 3 findings, 0 ungrounded diagnostics
and 4251 CSV bytes as at baseline — the guards observe the surface and do not move it.

`git diff --name-status e08da85..HEAD` is 12 files, all additions, all inside the two paths
this session owns. `git diff --check` clean. No tag, no push, no merge.

Elapsed wall-clock: **48 minutes**.
