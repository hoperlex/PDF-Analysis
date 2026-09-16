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

### Batch 3 — `exports/**`

| id | rule mutated | mutation (line read back) | result |
|----|--------------|---------------------------|--------|
| E01 | the seventeen frozen columns, **in order** | columns 7 and 8 swapped in `COLUMNS` | **GREEN(broad)** — 302 passed |
| E02 | `CONTENT_TYPE` is `text/csv; charset=utf-8` | `application/octet-stream` | green(fast), **red(broad)** — 1 failed in `p02_journey` |
| E03 | the header is written even when there are no rows | `if rows: writer.writerow(COLUMNS)` | **GREEN(broad)** — 302 passed |
| E04 | `SORT_KEY` names the frozen three-part key | `("finding_observation_id",)` | **GREEN(broad)** — 302 passed |
| E05 | a null projection column is the empty string | `return "null"` | **red** — 2 failed |
| E06 | a state absent from the mapping does not export | `.get(state, True)` | **red** — 6 failed |
| E07 | a terminal that omits `publishes_result` does not export | `body.get("publishes_result", True)` | **GREEN(broad)** — 302 passed |
| E08 | the refusal is `state_transition_not_allowed` | `PARTIAL_RESULT_NOT_PUBLISHABLE` | **red** — 6 failed |
| E09 | the export is scoped to one run | `WHERE (o.run_id = :run_id OR TRUE)` | **red** — 10 failed |
| E10 | `LEFT JOIN finding_current_verdict` | `JOIN` | **GREEN(broad)** — 319 passed |
| E11 | CRLF line endings | `_LINE_TERMINATOR = "\n"` | **red** — 1 failed |
| E12 | `_FILENAME_TEMPLATE` is `audit_run_{run_id}.csv` | `export-{run_id}.txt` | **GREEN(broad)** — 319 passed |
| E13 | `MACHINE` is `audit_run` | `document_version` | **red** — 24 failed |

**E02 is the reason step 2 of the method is not optional.** It is invisible to
`tests/integration/{findings,exports,decisions}` and reddens only in
`p02_journey/test_journey_figures.py`. A sweep that had screened on the owned suites alone
would have filed it as a finding and written a guard for something already guarded.

Four of the five greens are **unreddenable by construction** or a dead constant; one is the
wave-9 mistake still live in the tree.

* **E01 — the frozen column list had no literal pin in Python.** The export contract test
  asserts `header == list(COLUMNS)`, which moves with the mutation, and its `_parse` helper
  builds every row dict by zipping the file's **own** header against its own cells — so
  `row["finding_uid"]` follows a reordered header and every later assertion keeps passing.
  The same file pins `BOM` against a literal, with a comment saying mutation M1 caught
  exactly this phrasing for the BOM; the lesson was applied to the BOM and not to the
  columns. Guard written.
* **E03 — reachable and unguarded.** `render_csv` is a pure exported function; `render_csv(())`
  is one call. Guard written.
* **E04 — `SORT_KEY` has no consumer.** `render_csv` deliberately does not sort, and the
  order is fixed by the `ORDER BY` in `exports/query.py`. Nothing in `src/`, `tests/` or
  `web/` reads the constant. Guarded by a literal pin plus a behavioural check that real
  rows are ascending on the key it names — the pin alone would be a tautology.
* **E07 — unreddenable by construction.** The default in
  `bool(body.get("publishes_result", False))` can only fire for a terminal that declares no
  `publishes_result` key. All four terminals of `audit_run` in
  `contracts/domain/v1/state-machines.json` declare it explicitly, and the contract is
  frozen. No input reaches the default. **No test written.**
* **E10 — unreddenable by construction.** `finding_current_verdict` is defined in
  `0002_pc01_schema` as `FROM finding f LEFT JOIN LATERAL (...)`, so every `finding` row
  produces exactly one view row. `LEFT JOIN cv ON cv.finding_uid = f.finding_uid` therefore
  matches for every `f` the outer query already joined, and `LEFT JOIN` and `JOIN` are
  indistinguishable. Making it observable would need the *view* changed, which is
  `db/migrations`' tree. **No test written.**
* **E12 — see the product defect below.** `_FILENAME_TEMPLATE` and `CsvExport.filename` have
  no consumer, and the live download name disagrees with them.

## Guards written

All nine mutations below were applied to a copy of `src/` outside the worktree, with
`contracts/`, `docs/`, `fixtures/`, `tools/` and `db/` symlinked in, and every run printed
`auditmanager.__file__` resolving under the copy before the result was read.

`tests/integration/findings/test_gate_rules_are_load_bearing.py` — 10 tests

| rule | mutation | red | literal pinned | authority |
|------|----------|-----|----------------|-----------|
| `ObservationVerdict.reason` is the first failing item's, in evidence order | `for verdict in reversed(self.evidence_verdicts)` | 1 failed | `"span_length_mismatch"` / `"span_outside_page"`, asserted for both orderings of the same two items | P02 §5.1 |
| `failing_evidence_ordinal` is the first failing item's | same, on the other property | 1 failed | `failing_evidence_ordinal == 0` with both items failing; `== 1` with the first item resolving | P02 §5.1 |
| `EvidenceVerdict` is resolved exactly when it carries no reason | `__post_init__` body → `return` | 2 failed | the message string, written out | the migration's `grounded = (ungrounded_reason IS NULL)` CHECK |
| an omitted `block_index` still fails check 3 closed | `BlockIndex.empty()` → an index admitting every block | 1 failed, both controls green | `reason_counts() == {"span_outside_block": 1}` | P02 §5.1 fail-closed |

`tests/integration/findings/test_terminal_rules_are_load_bearing.py` — 7 tests

| rule | mutation | red | literal pinned | authority |
|------|----------|-----|----------------|-----------|
| `TERMINALS_FROM_VALIDATING` names the three terminals PC-01 can reach | `{"published", "cancelled"}` | 3 failed | `{"published", "partial", "failed"}` | `contracts/domain/v1/state-machines.json`, read from the test's own path, plus all 128 status combinations of `select_terminal` |
| `codes.discard(None)` — a silent stage does not veto a reported code | `codes.discard(None)` → `pass` | 2 failed | `"dependency_unavailable"` | the error catalog's retryable/not-retryable split, which is the stated reason for the line |

`tests/integration/findings/test_ungrounded_vocabulary_is_enforced.py` — 8 tests

| rule | mutation | red | literal pinned | authority |
|------|----------|-----|----------------|-----------|
| the gate's vocabulary is the migration's vocabulary | a sixth enum value | 1 failed | the five strings | the `IN (...)` list of `ck_finding_observation_ungrounded_reason` in `0003_open_items`, parsed from the migration |
| the database refuses a value outside it | *(see below)* | — | the constraint **name** in the refusal, not merely `IntegrityError` | the constraint itself |

The database half cannot be reddened by mutating `src/`, so it was shown to discriminate
directly: with the constraint installed the row is refused and the refusal names
`ck_finding_observation_ungrounded_reason`; with the constraint dropped inside a
rolled-back transaction the **identical** row is accepted. Nothing was committed and the
constraint was verified present afterwards. A first attempt at that probe was itself
refused — by the `finding_observation_id` format check, because the probe used a
hand-written identifier. That is the "field is not reason" trap in miniature, and it is why
the guard asserts the constraint's name.

`tests/integration/exports/test_frozen_column_list.py` — 8 tests

| rule | mutation | red | literal pinned | authority |
|------|----------|-----|----------------|-----------|
| the seventeen columns, in order | columns 7 and 8 swapped | 4 failed | all 17 names, and the header line as one string | `P02_SEAMS.md` §6 table, parsed; `web/src/shared/api/csv-columns.ts`, parsed |
| the header is written for an empty row list | `if rows:` around `writer.writerow` | 1 failed | `BOM + header + b"\r\n"`, whole | `render_csv`'s stated reason |
| `SORT_KEY` names the frozen three-part key | `("evidence_ordinal",)` | 2 failed | the three names | `P02_SEAMS.md` §6 "Sort key", plus a behavioural check that real rows ascend on it |

## Rules unreddenable *by construction* — reported, not faked

* **E07 — the `publishes_result` default.** `publishes_result_by_state()` reads
  `bool(body.get("publishes_result", False))`. The default can only fire for a terminal of
  `audit_run` that declares no `publishes_result` key. All four terminals in
  `contracts/domain/v1/state-machines.json` declare it, and the contract is frozen, so no
  input reaches the default. Flipping it to `True` changes nothing observable. Guarding it
  would mean asserting the behaviour of an unreachable branch.

* **E10 — `LEFT JOIN finding_current_verdict` versus `JOIN`.** The view is defined in
  `0002_pc01_schema` as `FROM finding f LEFT JOIN LATERAL (...)`, so it emits exactly one
  row per `finding` row and never fewer. `_EXPORT_ROWS` has already inner-joined `finding`,
  so `cv` matches for every row that reaches the clause. The two joins are
  indistinguishable from outside the database. Making the difference observable would
  require changing the view, which is `db/migrations`' tree, not a test's.

* **E04 / T02 — `SORT_KEY` and `TERMINALS_FROM_VALIDATING` have no consumer.** No
  behavioural mutation can redden a constant that nothing reads. These are *not* the same
  as E07 and E10: the constants are public, exported, and describe rules that really do
  hold elsewhere, so a cross-check against an outside authority is meaningful and both got
  one. Recorded here so the distinction is not lost — an unread constant is guardable, an
  unreachable branch is not.

## Product defects, precise and left unrepaired

**1. Three download-name rules, all different, none of them agreeing.** Naming the owning
trees; no repair attempted.

| where | value | consumer |
|---|---|---|
| `src/auditmanager/exports/service.py` — `_FILENAME_TEMPLATE`, surfaced as `CsvExport.filename` | `audit_run_{run_id}.csv` | **none anywhere** in `src/`, `tests/` or `web/` |
| `src/auditmanager/api/routers/export.py` — `_disposition()` | `attachment; filename="{run_id}.csv"` | the live `Content-Disposition` header |
| `web/src/shared/api/csv-columns.ts` — `csvFileName()` | `{runId}-findings.csv` | the download panel |

`CsvExport.filename` is documented as "what a browser should call the downloaded file",
and it is not what any browser is told to call it. Mutating `_FILENAME_TEMPLATE` to
`export-{run_id}.txt` left all 319 tests green, which is how three answers to one question
have coexisted. Owning trees: `src/auditmanager/exports/` (`P2-EXP-01`),
`src/auditmanager/api/routers/` (`P2-API-01`), `web/` (`P3-WEB-04`). A test in this
session's tree can only pin one of the three, so pinning it would assert a value the system
does not use; the disagreement is reported instead and `CsvExport.filename` is left
unasserted.

**2. `TERMINALS_FROM_VALIDATING` and `SORT_KEY` are exported public surface with no
reader.** Both are in `__all__`. `SORT_KEY` in particular restates, in
`exports/serializer.py`, an order that is actually fixed by the `ORDER BY` in
`exports/query.py` — two places for one rule, with nothing making them agree until the
guard added here. Owning trees: `src/auditmanager/findings/`, `src/auditmanager/exports/`.
Not repaired: deleting or wiring up a public constant is a product change.

## Corrected in this session's own tree

`tests/integration/findings/test_grounding_gate.py`,
`TestTheUngroundedVocabularyIsClosed`, carried a docstring stating that
`finding_observation.ungrounded_reason` "carries **no CHECK constraint**" and that "the
database accepts any string, including `'looked_wrong'`". Migration `0003_open_items`
added `ck_finding_observation_ungrounded_reason` and the database refuses that exact
string — verified directly. The claim was true when written and has been false since
`0003`. The docstring is corrected in place, and the correction is backed by a test rather
than asserted in prose. This is a comment in a path this session owns; no assertion in that
class was touched.

### Batch 4 — `findings/publication.py`, `findings/queries.py`, `decisions/**`

| id | rule mutated | mutation (line read back) | result |
|----|--------------|---------------------------|--------|
| PUB01 | `finding_uid` is fresh per published observation (§5.2) | one uid allocated before the loop and reused for every grounded observation | **red** — 25 failed, 36 errors |
| PUB02 | evidence rows are written only for a grounded observation | `if verdict.grounded:` → `if True:` | **red** — 3 failed, 31 errors |
| Q01 | `finding_by_uid` filters on `o.grounded` | `AND o.grounded` → `AND TRUE` | **GREEN(broad)** — 335 passed |
| Q02 | `diagnostics()` selects only `finding_uid IS NULL` rows | the predicate dropped | **red** — 2 failed |

* **PUB01 answers the brief's question directly.** "`finding_uid` allocation — fresh per
  publication. What notices if it is not?" The `finding` table's primary key notices first,
  on the second `INSERT INTO finding`, and the suite reddens in 25 places besides. Nothing
  needs to be added. The first attempt at this mutation referenced an undefined name and
  reddened by `NameError`, which would have been a worthless green-to-red: the faithful
  two-line version, allocating one real uid before the loop, is what the row above records.

* **Q01 — unreddenable by construction, and the module's own docstring overstates it.**
  `finding_by_uid`'s docstring says the `grounded` predicate "is the same one
  `published_findings` applies, so a diagnostic observation is unreachable here". But
  `_FINDING_BY_UID` also reads `JOIN finding f ON f.finding_uid = o.finding_uid`, and the
  migration's CHECK pins `grounded = (finding_uid IS NOT NULL)`. Any row surviving that join
  has a non-null `finding_uid`, so the CHECK makes `grounded` true for it; the predicate can
  never exclude a row the join admits. This is the same over-determination
  `exports/query.py` already documents for its own joins, and it is worth recording in the
  same terms: a reviewer should not read `AND o.grounded` as the point of enforcement. **No
  test written** — making the predicate observable would require violating the CHECK, which
  is `db/migrations`' tree.

**The decisions ledger and projection were swept by reading, not by mutation, and here is
why.** The brief names the ledger and the projection among the places to look first, and
puts `src/auditmanager/decisions/**` in the read scope — but the owned write paths are
`tests/integration/findings/**` and `tests/integration/exports/**` only.
`tests/integration/decisions/**` is **not** owned, so a guard for a ledger rule has no home
in this session. That is an ownership gap in the dispatch, not a licence to widen scope.

What reading establishes: the brief asks "Is the projection's *agreement with the stream*
asserted, or only its shape?" — it is asserted.
`tests/integration/decisions/test_decision_ledger.py:157`
(`test_the_rebuild_from_the_ledger_equals_the_stored_projection`) and `:304` both compare
`rebuild_current_verdict(...).comparable()` against the view's own row, and
`rebuild_current_verdict` folds `expert_decision_event` while the view is computed by
PostgreSQL, so the comparison cannot pass by comparing a cache with itself. The ledger's
refusing branches — `revoke`, an event type outside the journey, a comment with no comment,
an empty `author_label`, an unknown finding, an observation that is not the finding's own —
each have a named test. Those names are evidence of intent, not of load-bearingness; the
mutation that would settle it belongs to whoever owns `tests/integration/decisions/**`.

## What in the brief turned out to be false or incomplete

**1. The symlink list is incomplete, and the omission manufactures false reds.** The method
says to symlink `contracts/`, `docs/` and `fixtures/` into the copy. Two more root
directories are resolved from the copy's own tree:

* **`tools/`** — `tests/integration/p02_journey/test_truncated_end_to_end.py` resolves
  `tools/validation/ledger_report.py` relative to `auditmanager.__file__`. Without the
  symlink, **4 tests fail on an unmutated copy**.
* **`db/`** — `src/auditmanager/shared/db/migrations.py` takes the repository root from
  `parents[4]` of its own module file.

Both were found by running the unmutated copy against the wider suites before trusting a
single result, which is the only reason they did not read as mutation kills. A sweep that
symlinked the three named directories and went straight to mutating would have reported four
guards that do not guard, in a tree it never broke. The brief is right that `docs/` is needed
for `analysis.text.lock`; it is the completeness of the list that is wrong.

**2. `OPERATING_CONSTRAINTS.md` is not at the repository root.** The brief cites it twice as
a bare filename. It lives at `docs/program/dispatch/OPERATING_CONSTRAINTS.md`; there is no
copy at the root. Minor, but it cost a search at the one moment the document was needed —
deciding whether two storage failures were interference.

**3. The brief is right about the CHECK, and the tree contradicted it.** "`ungrounded_reason`
has a CHECK since migration `0003` and a five-value vocabulary" is **true**. The stale claim
was in the tree, not the brief: `TestTheUngroundedVocabularyIsClosed` asserted the opposite
in its docstring. Corrected, with a test.

**4. Two of the "where to look first" questions already have answers in the tree.**

* "Is the projection's *agreement with the stream* asserted, or only its shape?" — asserted,
  twice, and in a form that cannot compare a cache with itself.
* "`finding_uid` allocation — fresh per publication. What notices if it is not?" — the
  `finding` primary key, plus 25 tests. Both are covered; neither needed a guard.

**5. An ownership gap.** `src/auditmanager/decisions/**` is in the read scope and the ledger
is named as a place to look first, but `tests/integration/decisions/**` is not in the write
scope. A ledger rule found unguarded would have had nowhere to go.

**Not re-verified, and recorded as such:** the brief's claim that wave 5 found the CSV
tiebreaker reddenable only at 20 tied rows and not at two. That measurement was not repeated
here and nothing in this sweep bears on it.

**A gap in this session's own method, not the brief's.** The baseline gate was never run
*before* the new tests were added; the worktree arrived already bootstrapped from the killed
attempt and the first full gate ran with all 33 new tests present. The 816 figure is
therefore **inferred**, not measured here: the final gate reports 849 passed, and 849 − 33
new tests = 816, which agrees with the brief. A directly measured baseline would have been
better and cost four minutes.

## Summary

**37 rules mutated across `findings/**`, `decisions/**` and `exports/**`. 24 reddened. 13
did not.** Of the thirteen: **9 were unreddenable and reachable and now have guards**, **3
are unreddenable by construction** and were reported with the argument rather than given a
test, and **1** is a green that is really a product defect (E12, the download name) and is
deliberately left unguarded because a test here could only pin a value the system does not
use.

| module | mutated | reddened | green | guarded now | by construction | reported as defect |
|---|---|---|---|---|---|---|
| `findings/grounding.py` | 17 | 13 | 4 | 4 | — | — |
| `findings/terminal.py` | 3 | 1 | 2 | 2 | — | — |
| `findings/publication.py` | 2 | 2 | 0 | — | — | — |
| `findings/queries.py` | 2 | 1 | 1 | — | 1 (Q01) | — |
| `exports/**` | 13 | 7 | 6 | 3 | 2 (E07, E10) | 1 (E12) |
| `decisions/**` | 0 — read only; no owned write path | — | — | — | — | — |
| **total** | **37** | **24** | **13** | **9** | **3** | **1** |

A tenth guard was added that no mutation produced: nothing asserted that the **database**
refuses a reason outside the five-value vocabulary, or that the gate's vocabulary and the
migration's CHECK still agree. That came from reading, and from the stale docstring that
claimed the constraint did not exist.

**33 tests added** across four files, every one of them mutated red and green, with expected
values written as literals and cross-checked against an authority outside the module under
test: the frozen state-machine contract, `P02_SEAMS.md` §6, migration `0003`'s CHECK, and
the frontend's own column list.

The single most consequential finding is **E01**. The seventeen-column CSV is the deliverable
`OD-11` freezes and `B8` downloads, and its column *order* had no literal pin anywhere in the
Python tree. The assertion meant to hold it — `header == list(COLUMNS)` — is the exact wave-9
failure mode, in the file whose own comment records that the same phrasing once let the BOM
be deleted. The lesson had been learned for one constant in that file and not applied to the
one next to it.

The second is that **the grounding gate itself is in good shape**. Thirteen of its seventeen
rules redden, most of them on a single named test, and the four that did not are about the
*determinism of the diagnostic* and the *default block index* rather than about whether an
ungrounded row can be written. `W5-CERT` and `W6-CERT` were right about the conclusion they
drew; what they could not say is now said rule by rule.

**A correction made in the course of writing this.** The first version of this summary said
27 mutations, 18 red, and credited `exports/**` with 9 reds. Recounting from the batch tables
above gives 37, 24 and 7. The figures here are derived from the per-batch rows and not from
memory; the earlier ones were written from memory and were wrong in three places. Recorded
rather than quietly amended, because a wave that files a number it did not recount is the
thing this programme keeps finding.
