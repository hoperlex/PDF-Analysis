# W55B-BUDGET-01 — report (the analysis input budget)

- Task: `dispatch/W55-PLAN.md` §B3.3 (G-11), §B4 Stage B 2 `W55B-BUDGET-01`, §B5, §C2 (stop: "no input budget admitting the 30-page АР set"), §C6; owner ruling R-118.
- Branch `agent/w55b`, worktree `.local/worktrees/w55b-exec`, base `5af010b5` (INGEST report; below it STREAM `588773e9`, FIXTURES `461411b6`, SEAL `85fd99f0`).
- Written by one writer (Claude Opus 5.5 delegate of the wave executor). Nothing is pushed, merged or tagged.

## 0. Status (living; updated at every commit)

| Step | State |
| --- | --- |
| calibration (pypdfium2 against pdfplumber, tokens against characters) | done, section 3 |
| `analysis/text/budget.py` + export + container-free tests | in progress |
| `runs/commands.py` (`start_audit_run`, `reaudit_run`) | next |
| `bootstrap/{settings,composition,adapters}.py` and the composition tests | next |
| `tests/integration/runs/test_input_budget*.py` on the lane stack | next |
| light acceptance, mutation proofs, containment | next |

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

See section 3 once written (the measurements are in hand: pypdfium2 counts 1.016 to 1.019 times pdfplumber's text length on the synthetic documents; the
live input tokens recorded for fifteen of them fit 1 808 + 0.4575 tokens per pypdfium2 character with a 26-token worst residual, and the densest document
costs 0.548 tokens per character).
