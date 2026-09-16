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
