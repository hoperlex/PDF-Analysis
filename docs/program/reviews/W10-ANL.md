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
