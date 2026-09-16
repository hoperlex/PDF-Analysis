# `W10-FND` — mutation sweep of findings, decisions and exports

Session `W10-FND`, worktree `/root/w10fnd`, branch `agent/w10-fnd`.

**`HEAD` on arrival: `e08da85`** (`docs: the wave 10 dispatch — five parallel sweeps of the
rule surface`). The brief names the base as `fb30e96`; `e08da85` is one commit later on the
same line — the dispatch commit itself — so the base matched with a dispatch doc on top.

This is a **restart**. An earlier attempt was killed with nothing committed. This file is
appended to and committed after every batch of mutations, so a second kill loses one batch
rather than a wave.

## Method

Every mutation is applied to a copy of `src/` outside the worktree, with `contracts/`,
`docs/` and `fixtures/` symlinked in, and run with `pytest -o pythonpath=<copy>/src`. Every
run prints `auditmanager.__file__` and the result is discarded unless it resolves under the
copy. Every mutated line is read back after the edit and quoted in the table below, so a
mutation that does not mutate is visible rather than assumed.

## Sweep table

_(appended per batch)_

### Batch 1 — `findings/grounding.py`, the grounding gate

Screen suite (`fast`) = `tests/integration/{findings,exports,decisions}` — 112 tests.
Escalation suite (`broad`) = fast + `tests/integration/{api,p02_journey,composition}` — 302 tests.
Every row's mutated line was read back and is quoted.

| id | rule mutated | mutation (line read back) | result |
|----|--------------|---------------------------|--------|
| G01 | length check refuses a span whose width is not the quote's length | `if False:` at L165 | **red** — 4 failed |
| G02 | `len()` counts code points, not bytes | `len(quote.encode("utf-8"))` | **red** — 30 failed, 36 errors |
| G03 | check 1: interval lies inside the declared page | `if page is None:` (containment dropped) | **red** — 3 failed |
| G04 | check 1: a page number the document does not have | `if page is not None and not page.contains(...)` | **red** — 1 failed |
| G05 | check 2: the slice equals the quote exactly | `if False:` at L187 | **red** — 8 failed, 31 errors |
| G06 | the wrong-page diagnostic requires the declared page *not* to hold the quote | `if pages_with_quote:` | **red** — 1 failed |
| G07 | the wrong-page diagnostic requires *some* page to hold the quote | `if item.page_number not in pages_with_quote:` | **red** — 5 failed |
| G08 | check 3 runs whenever `block_id` is present | `if False:` at L207 | **red** — 4 failed |
| G09 | an unknown `block_id` fails **closed** | `if block is not None and not block.contains(...)` | **red** — 1 failed |
| G10 | check 3: interval lies inside the named block | `if block is None:` | **red** — 3 failed |
| G11 | an observation is grounded only when **every** item resolved | `all(...)` → `any(...)` | **red** — 1 failed |
| G12 | `ObservationVerdict.reason` is the **first** failing item's reason, in evidence order | `for verdict in reversed(self.evidence_verdicts):` L101 | **GREEN(broad)** — 302 passed |
| G13 | `failing_evidence_ordinal` is the **first** failing item's ordinal | `for verdict in reversed(self.evidence_verdicts):` L108 | **GREEN(broad)** — 302 passed |
| G14 | `EvidenceVerdict` pairing: resolved exactly when it carries no reason | `__post_init__` body → `return` L77 | **GREEN(broad)** — 302 passed |

Eleven of fourteen reddened, several of them on a single test — the reason vocabulary is
genuinely load-bearing per rule, which is what `W5-CERT` and `W6-CERT` could not say.

Three did not:

* **G12 / G13 — the diagnostic is documented as deterministic and nothing checks it.**
  `ObservationVerdict.reason`'s docstring says "the reason of the first item that failed,
  in evidence order: a deterministic choice, so two runs over the same artifact record the
  same diagnostic". Every existing perturbation test builds an observation with **one**
  failing evidence item, where first and last coincide. Reachable: an observation whose two
  items fail for two *different* reasons distinguishes them.
* **G14 — an asymmetry with `terminal.py`.** The identical constructor invariant on
  `TerminalSelection.__post_init__` **is** covered, by
  `test_an_incoherent_selection_cannot_be_constructed`. The one on `EvidenceVerdict` is not,
  although `EvidenceVerdict` is exported from `auditmanager.findings`.

All three are unreddenable-and-reachable → guards written in batch 4.

### Batch 2 — the vocabulary, and `findings/terminal.py`

| id | rule mutated | mutation (line read back) | result |
|----|--------------|---------------------------|--------|
| G15 | `UNGROUNDED_REASONS` is exactly the five declared values | a sixth value `"quotation_hallucinated"` added | **red** — 3 failed |
| G16 | each reason's wire value | `QUOTATION_ABSENT = "quotation_missing"` | **red** — 5 failed, 31 errors |
| G17 | omitting `block_index` does **not** disable check 3 | `run_grounding_gate` returns all-resolved when `block_index is None` | **GREEN(broad)** — 302 passed |
| T01 | `STAGE_STATUSES` is exactly the four declared statuses | two extra statuses added | **red** — 1 failed |
| T02 | `TERMINALS_FROM_VALIDATING` names the reachable terminals | `{"published", "cancelled"}` | **GREEN(broad)** — 302 passed |
| T03 | `codes.discard(None)` — a stage with no code does not veto a shared one | `codes.discard(None)` → `pass` | **GREEN(broad)** — 302 passed |

* **G15 / G16 reddened on a literal pin already present.**
  `test_the_enum_is_exactly_the_five_declared_reasons` writes the five strings out rather
  than deriving them from the enum, which is why renaming a value reddens. That is the
  wave-9 lesson already applied correctly here.
* **G17 — no test calls `run_grounding_gate` without a `block_index`.** Every one of the
  21 call sites in `tests/` and `src/` passes one. The fail-closed behaviour §5.1 requires
  of an omitted index is therefore asserted nowhere. Reachable: the parameter is optional
  on the public function.
* **T02 — `TERMINALS_FROM_VALIDATING` has no consumer.** It is defined in `terminal.py`,
  re-exported from `findings/__init__.py`, and read by nothing in `src/`, `tests/` or
  `web/`. No behavioural mutation can redden a constant nothing reads; a guard pinning it
  against `contracts/domain/v1/state-machines.json` is the only thing that can.
* **T03 — the correction `_reason_for` was written for is undefended.** Its docstring says
  the generic `analysis_failed` hid the difference between "a model that answered badly"
  and "a provider that never answered". `codes.discard(None)` is what lets a *shared* code
  survive when one of the failing stages reported no code at all; without it
  `codes == {None, "dependency_unavailable"}`, `len(codes) != 1`, and the run falls back to
  `analysis_failed`. Every existing case in `TestTheReasonNamesTheCause` supplies a code for
  **every** failing stage, so `None` is never in the set and `discard` never does anything.

