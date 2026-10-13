# W55B-BUDGET-01 — report (the analysis input budget)

- Task: `dispatch/W55-PLAN.md` §B3.3 (G-11), §B4 Stage B 2 `W55B-BUDGET-01`, §B5, §C2 (stop: "no input budget admitting the 30-page АР set"), §C6; owner ruling R-118.
- Branch `agent/w55b`, worktree `.local/worktrees/w55b-exec`, base `5af010b5` (INGEST report; below it STREAM `588773e9`, FIXTURES `461411b6`, SEAL `85fd99f0`).
- Written by one writer (Claude Opus 5.5 delegate of the wave executor). Nothing is pushed, merged or tagged.

## 0. Status (living; updated at every commit)

| Step | State |
| --- | --- |
| calibration (pypdfium2 against pdfplumber, tokens against characters) | done, section 3 |
| `analysis/text/budget.py` + export + container-free tests | done (`072311ec`) |
| `runs/commands.py` (`start_audit_run`, `reaudit_run`) | done (`90b11da2`) |
| `bootstrap/{settings,composition,adapters}.py` and the composition tests | done (`90b11da2`, `22450ef2`) |
| `tests/integration/runs/test_input_budget*.py` on the lane stack | done (`a5a12cd6`, `b1f7b017`) |
| light acceptance (all suites named in the brief), section 2 | done, section 2 |
| mutation proofs (thirteen, each restored byte for byte) | done, section 2.2 |
| final report sections 2 and 4 to 6, stack teardown | done (this commit) |

## 1. Design decisions (made while writing; each is open to the integrator's veto)

1. **The figure is derived from cost, not from the model's context.** The binding constraint is the per-run cost ceiling (`cost.py` halts the run
   after a call that took the meter past it, and publishes nothing). The pinned model's 1M-token context is eight times the input a $1 ceiling pays
   for, so it never binds at the default. `ModelPin` carries no context and `analysis/text/lock.py` is outside the grant, so context is not modelled
   (section 5, risk 1).
2. **The run must be able to finish, not merely start.** The worst case is priced in: the stage's output cap (`MAX_OUTPUT_TOKENS`, 16 000 tokens, adaptive thinking
   counts against it) is subtracted from the ceiling at the model's pinned output rate before any input is bought. One model call per run (PC-01), so
   one cap; if W56 adds calls the arithmetic must be revisited (section 5, risk 2).
3. **The prompt's own text is part of the arithmetic.** The system prompt and the response schema are sent with every request; their lengths come from
   `prompt.py` itself, so an edit to either moves the budget instead of silently outgrowing it.
4. **Only the character count exists at the check**, not the page count, so the per-page framing the prompt adds (`=== Страница N ===`, blank lines) is
   reserved once for the envelope's largest document (500 pages), a test binding the allowance to `ingest.MAX_PAGES`.

(Further decisions are appended below as they are made.)

## 2. Checks, and how each new test was shown to fail

Light acceptance (`R-102`), on the lane stack (PostgreSQL 57440, S3 61040/61041), one invocation at a time. The DB was recreated once during the lane
(`make down`, the lane's two volumes removed, `make up`, `make migrate`) because a reused DB made one unrelated durable-effect test state-dependent; the
suites below ran on the fresh one. Exit codes were read directly (`rc=$?`), never behind a pipe.

| Check | Result |
| --- | --- |
| `git diff --check 5af010b5..HEAD` | exit 0 |
| `python -m compileall -q` of `src/auditmanager`, `tools` and the three touched test directories | exit 0 |
| `tests/contract` without `test_cp00_candidate.py`, `test_cp00_final_state.py`, `test_validate_bootstrap.py` (clean committed tree, so `test_alpha_acceptance_command.py` is in) | exit 0, 752 passed, 18 927 subtests |
| `tests/integration/analysis_text` | 223 passed |
| `tests/integration/runs` | 200 passed (fresh DB) |
| `tests/integration/api` | 569 passed (fresh DB) |
| `tests/integration/composition` | 750 passed, 2 skipped (the opt-in proxy stand and the `W54_STAND_COPY_WINDOW` heavy step, both off by design) |
| `tests/unit`, `tests/characterization`, `tests/integration/p02_journey`, `tests/e2e` (no browser) | 1, 61, 59, 163 passed (5 skipped: the opt-in live-model cases) |
| web: `npm run lint`, `npm run typecheck` | exit 0 both |
| web: Vitest in two parts (everything but `query-key-shape.guard`, then that file) | 1 963 and 14 passed (the web tree is untouched by this lane) |
| a full `make gate` | **not run** (not this lane's: light acceptance, `R-102`; the integrator owes it, section 5) |

New tests, by file (each passes on the final tree): `test_input_budget_arithmetic.py` 26, `test_input_budget_calibration.py` 10,
`test_input_budget.py` 26, `test_input_budget_over_http.py` 7, `test_the_served_application_always_passes_a_budget.py` 10, plus the cases added to
`test_settings_defaults.py`.

### 2.1 What the new tests assert

* **Refused above, accepted at**: a version of `budget + 1` characters is refused with `analysis_input_budget_exceeded`, `details` of exactly
  `character_count` and `budget_characters` (both `int`), HTTP 422, `retryable: false`; a version of exactly `budget` is accepted (202, one job submitted).
  Both for `startRun` and for `reauditRun`, and over the real router, the shipped adapters and the real ASGI app.
* **Up front**: a refused request leaves no run and no command record, and submits no job; with the same idempotency key, against a deployment whose
  ceiling was raised, the request is a fresh start. A key the ledger already knows replays whatever the budget is now (the check sits behind the replay lookup).
* **NULL accepted**: a version with no recorded count (uploaded before `0021`) is not refused, whatever the budget.
* **The re-audit uses today's budget**, not the source run's.
* **The figure** (`budget.py`): equals an independent re-computation at the pinned rates; monotone in the ceiling; never negative; falls with `reserved_characters`;
  an unpinned model is refused (`model_not_pinned`); a negative reservation, a non-finite or negative ceiling are `ValueError`. The calibration test re-derives
  section 3 from the committed PDFs and the recorded ledgers, so a constant that stops covering a measured document turns it red.
* **The served application always passes a budget**: the real `build_application` wires a `RunAdapter` and an `ExecutionAdapter` whose budget is the derived
  figure, and a start-up whose ceiling leaves less than the 93 690-character reference document refuses with the settings' own error.

### 2.2 Mutation proofs

Each row: one edit, applied to the committed file, the named test files run (`-x` for T1 to T13), the file restored from the in-memory original and its SHA-256
compared with the digest taken before the edit (all matched; `git status --porcelain -uall` was empty afterwards). T1 to T9 ran `test_input_budget.py` or
`test_input_budget_arithmetic.py` only, T10 to T13 the composition files, as the first-failing-test column shows. The scripts are scratch.

| # | Mutation | First failing test |
| --- | --- | --- |
| T1 | `if character_count > budget` becomes `> budget + 10**9` (nothing is refused) | `test_input_budget.py::test_a_start_above_the_budget_is_refused_with_both_figures` |
| T2 | `>` becomes `>=` (a version exactly at the budget is refused) | `test_input_budget.py::test_a_start_exactly_at_the_budget_is_accepted` |
| T3 | a `None` count is read as an astronomical one | `test_input_budget.py::test_a_start_over_a_version_with_no_recorded_count_is_accepted` |
| T4 | the start check in `start_audit_run` replaced by `pass` (only the re-audit still checks) | `test_input_budget.py::test_a_start_above_the_budget_is_refused_with_both_figures` |
| T5 | `reaudit_run` never checks | `test_input_budget.py::test_a_reaudit_above_the_budget_is_refused_with_both_figures` |
| T6 | the `find(...) is None` guard removed from the start check (a key the ledger knows is refused instead of replayed) | `test_input_budget.py::test_a_key_the_ledger_knows_replays_even_when_the_budget_has_since_fallen` |
| T7 | the output cap not priced in | `test_input_budget_arithmetic.py::TestTheDefaultConfiguration::test_the_figure_matches_an_independent_…` |
| T8 | `reserved_characters` not subtracted | `test_input_budget_arithmetic.py::TestMonotoneAndNeverNegative::test_a_larger_reservation_never_raises` |
| T9 | the fixed prompt not taken off | `test_input_budget_arithmetic.py::TestTheDefaultConfiguration::test_the_figure_matches_an_independent_…` |
| T10 | the start-up refusal (`budget < REFERENCE_DOCUMENT_CHARACTERS`) neutered | `test_the_served_application_always_passes_a_budget.py::TestTheFigureIsPartOfTheSettingsAndTheStartUp::…` |
| T11 | `RunAdapter` stops passing the budget to `start_audit_run` | `test_the_served_application_always_passes_a_budget.py::TestTheRealCompositionPassesTheDerivedBudget::…` |
| T12 | `ExecutionAdapter` stops passing the budget to `reaudit_run` | same class |
| T13 | `composition.py` passes `None` | same class |

All thirteen red. Two further mutations move the check, not remove it (same method, run after T1 to T13; the script is scratch):

| # | Mutation | First failing tests |
| --- | --- | --- |
| U1 | `start_audit_run` refuses only **after** the key is claimed (the check moves below `assert isinstance(claimed, CommandStarted)`) | `test_input_budget.py::test_a_refused_start_creates_nothing_at_all`, `…::test_the_same_key_after_the_budget_is_raised_is_a_fresh_start_not_a_replayed_refusal` |
| U2 | `reaudit_run` refuses only **after** the key is claimed | `test_input_budget.py::test_a_refused_reaudit_creates_nothing_at_all`, `…::test_the_same_reaudit_key_after_the_budget_is_raised_is_a_fresh_re_audit` |

So the up-front position is held by tests, not only the refusal itself. The over-HTTP module proves the wire and the shipped adapters; the command-level module
proves the command; T11 to T13 prove the adapters pass the budget at all.

## 3. Calibration

### 3.1 What was measured, and what was not

**The "recorded" token counts under `fixtures/recorded/text_analysis` are authored, not measured** (that directory's README says so in its honesty
note: 2 180 input tokens for the AR baseline, against 3 895 measured live). They calibrate nothing and are not used. The repository's only **measured**
model usage (`cost_basis: measured`, `provider_mode: live`, `claude-opus-5` through the proxy) is:

* the fourteen documents of the PC-02 baseline (`artifacts/validation/PC-02/baseline/ledger.json`, 2026-09-14; the PDFs are
  `fixtures/validation/PC-02/documents/*.pdf`);
* the synthetic AR baseline (`fixtures/synthetic/ar/ar_baseline.pdf`) in the three PC-01 re-certifications
  (`artifacts/checkpoints/PC-01/recertification-*.json`, 2026-09-15): 3 895 input tokens each, so tokenisation is deterministic.

`prompt.py` has not changed since 2026-09-10, so those counts are for today's prompt. Fifteen documents, 5 to 10 pages each, 1 550 to 3 810 pypdfium2
characters. **No real client file was read**; the real 30-page АР set enters only as the figure `W55B-INGEST-01` section 2.1 recorded (93 690 pypdfium2
characters, 3 123 per page) and is the reference `REFERENCE_DOCUMENT_CHARACTERS`.

### 3.2 Method

Run from the worktree root on this tree (the same computations are committed as
`tests/integration/analysis_text/test_input_budget_calibration.py`, which re-derives them on every run):

```text
PYTHONPATH=src .venv/bin/python <script>        # scratch, not committed; the test file is its committed form
  pypdfium2 count   = sum(inspect_pdf(bytes, require_text=False).page_characters)      # ingest.envelope, the product's own count
  pdfplumber text   = sum(len(page.text) for page in extract_document(bytes).pages)    # analysis.stages.extraction
  rendered prompt   = len(render_document(load_text_layer(_build_text_layer(document)))) # analysis.text.prompt
  request characters = len(SYSTEM_PROMPT) + len(canonical_json(RESPONSE_SCHEMA)) + rendered   # 3 012 + 627 + rendered
```

| document | pages | pypdfium2 | pdfplumber | rendered prompt | live input tokens | pypdfium2 / pdfplumber | request characters per token |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `PC02-C01` | 5 | 1550 | 1524 | 1707 | 2514 | 1.0171 | 2.126 |
| `PC02-C02` | 6 | 1871 | 1840 | 2044 | 2668 | 1.0168 | 2.130 |
| `PC02-C03` | 6 | 1897 | 1866 | 2070 | 2670 | 1.0166 | 2.138 |
| `PC02-C04` | 7 | 2213 | 2177 | 2402 | 2846 | 1.0165 | 2.123 |
| `PC02-C05` | 6 | 1885 | 1854 | 2058 | 2659 | 1.0167 | 2.143 |
| `PC02-C06` | 5 | 1594 | 1568 | 1751 | 2523 | 1.0166 | 2.136 |
| `PC02-C07` | 5 | 1613 | 1587 | 1770 | 2550 | 1.0164 | 2.121 |
| `PC02-C08` | 8 | 2559 | 2518 | 2764 | 2971 | 1.0163 | 2.155 |
| `PC02-C09` | 7 | 2245 | 2209 | 2434 | 2828 | 1.0163 | 2.147 |
| `PC02-S01` | 7 | 2486 | 2446 | 2671 | 2941 | 1.0164 | 2.146 |
| `PC02-S02` | 6 | 2033 | 1999 | 2203 | 2757 | 1.0170 | 2.119 |
| `PC02-S03` | 7 | 2272 | 2235 | 2460 | 2849 | 1.0166 | 2.141 |
| `PC02-S04` | 9 | 2939 | 2892 | 3159 | 3177 | 1.0163 | 2.140 |
| `PC02-S05` | 10 | 3203 | 3151 | 3441 | 3250 | 1.0165 | 2.178 |
| `ar_baseline` | 8 | 3810 | 3740 | 3986 | 3895 | 1.0187 | **1.958** |

### 3.3 Findings

* **(a) pypdfium2 against pdfplumber.** pypdfium2 counts **1.0163 to 1.0187** times pdfplumber's text length on all fifteen documents: it never counts
  fewer, because it spells a generated line break with two characters where pdfplumber joins with one. The budget treats the two as equal, which is the
  safe side while the pypdfium2 figure is the larger; on a real document with much shorter or longer lines the ratio moves toward or away from 1.0, and the
  40 % margin below is what absorbs that (a test asserts only `1.0 <= ratio <= 1.05` on the fifteen, so a document pypdfium2 under-counts turns it red).
* **(b) tokens per character.** A request's characters (system prompt, schema, rendered document) per input token: **2.119 to 2.178** for the fourteen
  PC-02 documents (mean 2.139) and **1.958** for the AR baseline, the densest and the nearest to real architectural text. A least-squares line through
  the fourteen is 1 808 tokens of fixed prompt plus 0.4575 tokens per pypdfium2 character with a 26-token worst residual, so the density is stable across
  the PC-02 documents; the AR baseline is 9 % denser than the PC-02 mean per request character (20 % denser per character of its own text) and is why the constant is set from it and not from the mean.
* **(c) the page framing.** `render_document` adds a preamble and `=== Страница N ===` with blank lines around every page: 29 to 37 characters per page on
  the measured documents, **11 472 characters for 500 empty pages** (the upload envelope's maximum, `ingest.MAX_PAGES`).
* **(d) what a real run spends.** Replies were 10 to 546 output tokens (PC-02), $0.013 to $0.030 a run; the single most expensive thing a run can do is
  spend the 16 000-token output cap ($0.40 at the pinned $25 per million), which the budget prices in.

### 3.4 The constants, the margin and the resulting figure

| Constant | Value | Why |
| --- | --- | --- |
| `CHARACTERS_PER_TOKEN` | **1.4** (exact `7/5`) | assumes **40 % more tokens per character** than the densest measured request (1.958 / 1.4) and 53 % more than the PC-02 mean (2.139 / 1.4) |
| `PAGE_FRAMING_ALLOWANCE_CHARACTERS` | **12 000** | covers the measured 11 472 for 500 pages; a test fails if the envelope's page limit or the rendering outgrows it |
| fixed prompt | **3 639** characters (3 012 + 627), read from `prompt.py` | sent with every request; moves with a prompt edit instead of silently outgrowing the budget |
| output cap | **16 000** tokens, read from the prompt bundle | priced at the pinned output rate, in full |
| `REFERENCE_DOCUMENT_CHARACTERS` | **93 690** | the real 30-page АР set (INGEST section 2.1) |

For the **configured model `claude-opus-5` (pins: $5.00 in, $25.00 out per million tokens) and the **$1.00 ceiling** (OD-03):

```text
output cap        = 16 000 tokens x $25 / 1 000 000          = $0.40
input the rest    = ($1.00 - $0.40) / ($5 / 1 000 000)       = 120 000 tokens
characters        = 120 000 x 1.4                             = 168 000
budget            = 168 000 - 3 639 (prompt) - 12 000 (framing) = 152 361 pypdfium2 characters
```

**152 361 characters, about 49 pages at the real АР set's 3 123 characters a page (the plan's "≈ 50 pages", ≈ 150 000), 1.63 times the 93 690-character
АР set.** For `claude-sonnet-5` at the same ceiling the figure is 572 361. The primary model's ceiling floor, the lowest one at which the start-up refusal
lets the application start, is **$0.79 + 0.0005** (the budget reaches 93 690 between $0.79 and $0.80); below it `settings.load` raises.

*Does the run finish under the ceiling?* A document exactly at the budget costs, at the densest density actually measured (1.958), (3 639 + 152 361 +
12 000) / 1.958 = 85 800 tokens = **$0.43** of input plus at most **$0.40** of output = **$0.83**: 17 % under the ceiling even if the model spends its whole
output cap. At the constant's own density the same document lands on $1.00 to within a character. The committed test re-derives both.

## 4. Contracts

**None changed.** The sealed surface is as `W55B-SEAL-01` left it: 47 paths, 54 operations, 123 schemas; the error catalog is 24 entries, and
`analysis_input_budget_exceeded` (HTTP 422, not retryable, `details` of `character_count` and `budget_characters`) was already registered and is now
*raised*; domain candidate revision 12; migration head `0021_portal_bundles`. No lock file, no `contracts/**` file, no migration was touched.

Public-surface additions (code, not contract):

* `auditmanager.analysis.public.input_budget_characters` and `REFERENCE_DOCUMENT_CHARACTERS` (the plan's one export line); `CHARACTERS_PER_TOKEN` and `PAGE_FRAMING_ALLOWANCE_CHARACTERS` stay inside `analysis.text.budget`.
* `start_audit_run(..., input_budget_characters: int | None = None)` and `reaudit_run(..., input_budget_characters: int | None = None)`; `None` checks nothing and is reachable only from tests.
* `AppSettings.input_budget_characters: int`, derived once at start-up from the configured model and `AUDITMANAGER_RUN_COST_CEILING_USD`; `RunAdapter.input_budget_characters` (read by `ExecutionAdapter`).
* Locks: `PDFIUM_LOCK` is not taken by anything here (no pypdfium2 call is made; the count is read from the version row).

## 5. Risks and known limitations

1. **The context window is not modelled** (`ModelPin` carries none and `analysis/text/lock.py` is outside the grant). At the default ceiling the cost binds with a factor of eight to spare; a ceiling above about $5.50 for the primary model would let the window bind, and the provider would refuse that request itself, loudly. Revisit when `ModelPin` gains the field.
2. **One model call per run.** W56 adds block analysis and a critic; the arithmetic reserves one output cap and must be revisited then. `reserved_characters` already exists for W57's norms context (`CAP-01`).
3. **The constant rests on fifteen short documents** (5 to 10 pages, all synthetic or PC-02 scans). The 40 % margin over the densest measured request is the judgement; the real 30-page АР set was *not* tokenised (no live call was made, F-7). A first live run of the real set is the measurement that would confirm or shrink the margin; the recorded figure is the integrator's to take at REHEARSAL on the stand.
4. **A ceiling below about $0.79 now refuses to start the application** (`settings.load` raises). This is the plan's stop condition made executable, but it is an operating change: the integrator must read `AUDITMANAGER_RUN_COST_CEILING_USD` in the stand's environment (`infra/deploy/env/provider.env.example` leaves it empty, i.e. the $1.00 default) before the candidate is published. Two existing composition cases carried a ceiling of 0.01 and 0.25; they were moved to 0.95 and 0.90 (section 6, outside the grant).
5. **The pypdfium2 count is the unit** and it never counts fewer than pdfplumber on the fifteen (1.016 to 1.019 times); on a document with very short lines the ratio could move, which the margin absorbs, and which a test bounds at 1.05 on the measured set.
6. **Idempotency semantics.** A key that has not been seen is checked and refused *without being recorded*; the client may retry the same key after the operator raises the ceiling and it is a fresh start. A key the ledger already knows replays regardless of today's budget, so a client that retries an accepted start is told what happened and not that its version has since become too large. The plan does not fix this; it is the writer's reading of "refuse up front", and open to the integrator's veto.
7. **A state-dependent older test**: `tests/integration/runs/test_durable_effect_boundaries.py::test_provider_effect_settlement_is_bounded_and_resumable` failed once on a *reused* lane DB and passed alone and on a freshly recreated one. It does not exercise this lane's code (no budget is configured in it), but the lane's files were **not** reverted to prove that; recorded as observed, not fixed.

## 6. Integrator instructions

1. Merge `agent/w55b` at the lane tip (the commit that carries this report). BUDGET adds no migration, no dependency and no contract; the merge with the previous lanes is a fast-forward of the series.
2. **Heavy steps owed: none of this lane's own.** The plan marks BUDGET "full gate"; per `R-102` the one full `make gate` runs once, on the merged candidate, after the executor's last lane. The mutation table above is the lane's proof.
3. Before publishing: read the stand's `AUDITMANAGER_RUN_COST_CEILING_USD` (risk 4) and confirm it is empty or at least `0.80`.
4. At REHEARSAL, run the real 30-page АР set once with the live model and write down its measured input tokens next to 93 690 pypdfium2 characters; compare with the section 3.4 estimate (about 50 000 tokens at 1.958 characters per token) to judge the margin.
5. Questions for the owner: none. The figure (152 361 characters at $1.00) is the plan's "about 50 pages".

### 6.1 Containment proof

`git diff --name-only 5af010b5..HEAD` (fifteen files):

```text
docs/program/W55B-BUDGET-01.md
src/auditmanager/analysis/public.py
src/auditmanager/analysis/text/budget.py
src/auditmanager/bootstrap/adapters.py
src/auditmanager/bootstrap/composition.py
src/auditmanager/bootstrap/settings.py
src/auditmanager/runs/commands.py
tests/integration/analysis_text/test_input_budget_arithmetic.py
tests/integration/analysis_text/test_input_budget_calibration.py
tests/integration/composition/test_composition_root.py
tests/integration/composition/test_settings_defaults.py
tests/integration/composition/test_the_served_application_always_passes_a_budget.py
tests/integration/runs/test_input_budget.py
tests/integration/runs/test_input_budget_over_http.py
tests/integration/runs/test_w53c_exec_closure.py
```

Inside the grant of `W55-PLAN.md` §B4 stage B 2: `budget.py`, `analysis/public.py`, `runs/commands.py`, `bootstrap/{settings,composition,adapters}.py`, `test_settings_defaults.py`,
`test_input_budget*.py`, the report. **Outside the named list, five files, each forced or implied, flagged here:**

* `tests/integration/analysis_text/test_input_budget_{arithmetic,calibration}.py` and `tests/integration/composition/test_the_served_application_always_passes_a_budget.py`: new files in the directories the grant's own requirements ("a composition test proving the served application always passes a budget", tests of the figure) land in.
* `tests/integration/composition/test_composition_root.py`: two cases used ceilings of 0.01 and 0.25, which the new start-up refusal rejects; the case's point (a value the process does not carry) is kept at 0.95 and 0.90.
* `tests/integration/runs/test_w53c_exec_closure.py`: the stub that stands in for `RunAdapter` gained the one attribute `ExecutionAdapter` now reads (`input_budget_characters = None`).

No `contracts/**`, migration, lock file, composition-root *shape* beyond the one argument, global style or web file was touched. `git status --porcelain -uall` is empty.
