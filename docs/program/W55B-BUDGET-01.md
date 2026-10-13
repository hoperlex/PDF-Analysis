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
| light acceptance (all suites named in the brief), mutation proofs, final report sections 2 and 4 to 6, stack teardown | next |

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

