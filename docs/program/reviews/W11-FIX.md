# `W11-FIX` review record

Session `W11-FIX`, wave 11. Worktree `/root/w11fix`, branch `agent/w11-fix`.

**HEAD on arrival: `5d14921388a892f325520f9784708ca3598aaeab`** — `docs: the wave 11
dispatch — repair what wave 10 found`, the tip of `origin/dev`. The brief said "base
`30d129c` or later"; `5d14921` is one commit later and is that tip.

Started 2026-09-16T19:30:07+05:00. Logs in `/root/w11fix-logs/` (session-unique).
Instance `gate-w11b`: `POSTGRES_PORT=55640`, `S3_API_PORT=59240`,
`S3_CONSOLE_PORT=59241`, `POSTGRES_DB=audit_w11b`, bucket `auditmanager-gate-w11b`.

This file is appended to as the work proceeds, not written at the end.

---

## 1. Premises checked against the tree before any edit

Every premise in the brief was re-derived from the tree. Results below; the two that
were wrong are in §6.

### Defect 1 — two comments false in the dangerous direction — **CONFIRMED**

`src/auditmanager/api/routers/multipart.py:96` and
`src/auditmanager/api/schemas/projects.py:53` both say `details` values "are not
screened the way `message` is". `shared/errors/envelope.py:build` does screen them: a
string detail value is run through the same `_FORBIDDEN` tuple as a message and raises
`UnsafeDetailValue`. The screen is at `envelope.py:137-146`.

### Defect 2 — docstring undercounts the screen — **CONFIRMED, and the count is six**

Counted in the `_FORBIDDEN` tuple at `envelope.py:30-46`, not taken from the brief:

1. `a URL`, 2. `a filesystem path`, 3. `an S3-style object key`, 4. `a credential`,
5. `SQL`, 6. `a stack frame`. **Six.**

The module docstring says "paths, URLs, credentials, SQL, stack frames" — five, omitting
the S3-style object key. The brief's own account of its wave-10 predecessor saying
"seven" is therefore also confirmed as having been wrong.

### Defect 3 — `cost_basis` asymmetric — **CONFIRMED**

`analysis/text/stage.py`: the budget-overrun branch sets `"cost_basis"` in its metrics
(line 277); the success-path `metrics` dict (line 312) does not. Four returns share that
dict — truncated-with-no-observations, artifact-build failure, partial, and succeeded —
so all four lack it. `_record(..., cost_basis=...)` at line 300 does set it on the
`ModelCallRecord` for both paths, so the ledger row is fine and only the stage metrics
are asymmetric, exactly as stated.

`contracts/analysis/v1/stage-result.schema.json` admits
`number|integer|string|boolean|null` under `metrics`, so a string `cost_basis` conforms.

### Defect 4 — filename property with no consumer — **CONFIRMED (name in brief is wrong)**

`exports/service.py:30` defines `_FILENAME_TEMPLATE = "audit_run_{run_id}.csv"` and a
`filename` property at line 43. A repository-wide search for `.filename`,
`_FILENAME_TEMPLATE` and `ExportResult` finds no reader of either outside their own
definition. The sibling `byte_size` property on the same class **is** read
(`tests/integration/runs/test_corpus_measurement.py:67,75`), which is what makes the dead
one easy to miss.

The contract claim holds: `web/openapi/openapi.json`, `GET /runs/{run_id}/export.csv`,
200 response, header `Content-Disposition` — "Attachment with a display file name built
from opaque identifiers. The file name is presentation only and is never an identity."
No `enum`, no `pattern`, no `example`; schema is bare `{"type": "string"}`. The header
(`api/routers/export.py:_disposition` → `{run_id}.csv`) and the UI
(`web/src/shared/api/csv-columns.ts:csvFileName` → `{runId}-findings.csv`) differing is
permitted, and the UI already says so in its own docstring: "The server's
`Content-Disposition` wins if it sends one."

---

## 2. Baselines

| What | Result |
|---|---|
| `make gate`, arrival, before any edit | **1264 passed / 5 skipped / 116 subtests**, `GATE OK` — exactly the figure the brief predicted |
| `make mutation-copy MUT=/root/w11fix-mut`, then owned suites against the **unmutated** copy | **474 passed** |
| Same copy rebuilt from the repaired tree | **487 passed** (474 + 13 new) |

The copy was confirmed to be the tree actually imported, not merely present:
`auditmanager.shared.errors.envelope.__file__` and `auditmanager.exports.service.__file__`
both resolved under `/root/w11fix-mut/src`. `src/` is `cp -a`'d by the target on every
run, so no `FULL=1` was needed: all four defects live in `src/`, and no contract or
fixture was mutated.

---

## 3. The four repairs, each with the guard shown red without it

Product code in `dc6ae78`, guards in `e29c355`. The path-derivation fix of §3.5 was
made after `e29c355` and is carried by `83f5aa9` — noted because a reader looking for it
in the test commit will not find it there.

### 3.1 The undercounted docstring (defect 2)

**Repaired.** `shared/errors/envelope.py`'s docstring now names all six shapes in
`_FORBIDDEN`'s own order and states the count, and says that string `details` values are
screened by the same six — the claim the two comments in §3.2 denied.

**Made executable rather than merely corrected.** Four new tests in
`tests/integration/api/test_envelope_screen_rules.py`, class
`TestTheScreenHasSixShapesAndTheDocstringSaysSo`:

- the screen carries exactly the six labels, in order, compared against a hand-written
  literal tuple;
- the docstring names every one of them;
- the docstring emphasises no other count;
- the existing `ONE_SHAPE_EACH` cases reach *exactly* those six, so a seventh shape added
  without a case reddens instead of going untested, and an unreachable shape reddens too.

| Mutation | Result |
|---|---|
| **M1** — docstring reverted verbatim to its five-shape sentence | **2 failed**, 485 passed: `test_the_module_docstring_names_every_shape_the_screen_carries`, `test_the_docstring_does_not_claim_a_count_other_than_six` |
| **M1b** — the `an S3-style object key` entry deleted from `_FORBIDDEN` (read back: 5 entries, label gone) | **3 failed**, 484 passed: `test_the_screen_carries_exactly_six_shapes_in_this_order` plus both `[s3_key]` cases |

M1 is the defect itself, restored and watched fail.

**One thing this caught in my own work.** The first version of the docstring test used a
naive substring check and reported `an S3-style object key` missing from a docstring that
names it — the phrase straddles a line break at the 90-column wrap. A false red is as
costly as a false green, because the next reader "repairs" it by unwrapping prose. The
test now collapses whitespace before matching, and says why.

### 3.2 The two false comments (defect 1)

**Repaired.** `api/routers/multipart.py` and `api/schemas/projects.py` no longer say
`details` values "are not screened the way `message` is". Both now state that the values
*are* screened by the same six `_FORBIDDEN` patterns, and give the real reason not to
echo: a part name or property name carrying a forbidden shape would turn the caller's
`422` into an unhandled `UnsafeDetailValue` at envelope construction, and one carrying no
forbidden shape would still be the caller's raw input reflected back. The refusals
themselves were already correct and were not touched.

**Made executable.** New class `TestNoCallSiteClaimsDetailsAreUnscreened`, in two halves
that only mean something together:

- the screen is demonstrably live at the exact text those sites decline to echo —
  `build(VALIDATION_FAILED, …, details={"field": "/etc/passwd"})` raises
  `UnsafeDetailValue` naming `a filesystem path`. `/etc/passwd` is `B6`'s own property
  name;
- no source file under `api/` asserts the negative.

| Mutation | Result |
|---|---|
| **M2** — both comments restored verbatim | **1 failed**, 486 passed: `test_no_api_source_file_claims_details_are_unscreened`, naming both files |

A phrase check is a blunt instrument, used here only because the claim *is* a phrase.
It is paired with the behavioural half so that the phrase is not the only thing asserted.

### 3.3 `cost_basis` on the wrong path (defect 3)

**Repaired.** `analysis/text/stage.py`'s success-path `metrics` dict now carries
`cost_basis`, by the same expression the overrun branch uses. Four returns share that
dict — truncated-with-no-observations, artifact-build failure, `partial` and `succeeded` —
so all four gain it, which is the correct scope: each of them is a run whose consumer
previously got a `KeyError`. The `ModelCallRecord` was already correct on both paths and
was not touched.

The comment beside `_record`, which recorded this as an unfinished repair, now records it
as finished rather than leaving a note pointing at a hole that is closed.

**Guard.** `tests/integration/analysis/test_stage_status_and_cost_rules.py` already held
`test_cost_basis_reaches_the_record_but_not_the_success_path_metrics`, which asserted
`"cost_basis" not in outcome.metrics` and said in its own docstring that it pinned the
behaviour "so that changing it is a deliberate act", reported "for the owner of
`src/auditmanager/analysis/`". This is that deliberate act: the test is renamed and its
assertion inverted. Both paths are asserted in one test on purpose — the failure being
guarded against is *a difference between two paths*, and two tests that each pass alone
cannot express it. Two tests added beside it:

- the `estimated` case on the success path, so hard-coding `"measured"` cannot satisfy
  the first test;
- every value the success metrics dict emits is one of the scalar types
  `contracts/analysis/v1/stage-result.schema.json` admits — written as literals, not read
  from the schema, so a loosened schema cannot loosen the test.

| Mutation | Result |
|---|---|
| **M3** — `cost_basis` removed from the success metrics dict (read back: absent from that dict, still present on the overrun dict and on `_record`) | **2 failed**, 485 passed, the first with `KeyError: 'cost_basis'` — the exact failure a consumer hit |
| **M3b** — success-path value hard-coded to `"measured"` | **1 failed**: `test_cost_basis_in_the_metrics_says_estimated_when_the_transport_reported_nothing` |

### 3.4 The dead filename property (defect 4)

**Removed, and I judge removal correct.** `_FILENAME_TEMPLATE` and `CsvExport.filename`
are gone. The argument for keeping it would have to name something that would read it;
nothing does, and nothing plausibly would, because serving a download name is a transport
concern and the transport already does it. The value object is computed from canonical
data and is explicitly "a value, not a record of anything" — a name on it is not a
narrower version of the header, it is a second answer to a question that already has one.

I did **not** reconcile the header with the frontend, per the brief and per the contract:
`openapi.json` pins no value for `Content-Disposition` and says the name "is presentation
only and is never an identity". The frontend's `csvFileName` already says in its own
docstring that the server's header wins. Making them agree would be inventing a contract
nobody wrote.

**A reader can now tell which name the system serves.** New file
`tests/integration/exports/test_the_download_name_has_one_source.py`, which states the
three-answer situation and its resolution in prose *and* holds it:

- `CsvExport` exposes no download name under `filename`, `file_name`, `download_name` or
  `attachment_name` — the defect is "the value object answers the filename question", and
  it would be the same defect under another spelling;
- its sibling `byte_size`, which *is* read, is still there — otherwise the test above
  would pass on a class stripped by accident. That sibling is why the dead property beside
  it was easy to miss;
- the dead template appears nowhere in the source tree;
- exactly one source file builds an `attachment;` name, and it is the router;
- that file serves the run identity and a suffix, as a literal.

No database is needed: every assertion is about the shape of the source tree and of a
value object, which is exactly the kind of claim that otherwise lives in a comment. The
bytes on the wire over a real run stay asserted where they were, by
`tests/integration/api/test_no_internal_identifiers.py::test_an_export_disposition_names_only_the_opaque_run_identity`.

| Mutation | Result |
|---|---|
| **M4** — `_FILENAME_TEMPLATE` and the property restored (read back: `CsvExport.filename` → `audit_run_run_ABC.csv`, from the copy's own `service.py`) | **2 failed**, 485 passed |
| **M4b** — the router changed to serve `{run_id}-findings.csv` (read back: `_disposition('run_ABC')` → `attachment; filename="run_ABC-findings.csv"`) | **2 failed**: my literal test and the existing real-run disposition test |

M4b is worth noting: it shows the source-text assertion and the behavioural assertion
redden **together**, so the new file is not a second way for the same fact to drift.

### 3.5 A defect in my own guards, found by the mutation copy

Both source-scanning guards were first written as
`Path(__file__).resolve().parents[3] / "src/auditmanager/…"`. Under M2 that read
`/root/w11fix/src` — the pristine checkout — and the guard stayed **green against a tree
that still carried the defect**. The `make mutation-copy` notice says this in as many
words: anything reaching a directory by a path not derived from `auditmanager.__file__`
reads the pristine tree.

Both now derive the tree from `Path(auditmanager.__file__).resolve().parent`, and say why
in a comment. M2 and M4 were re-run after the change and are the reds recorded above.
This is the one failure mode a source-text guard has, and it is silent.

---

## 4. What an operator or a stored row observes differently

**One behaviour change, additive.** `run_text_analysis` now returns one extra key in the
metrics mapping on four of its return paths: `cost_basis`, a string, `"measured"` or
`"estimated"`.

- **A stored row:** the `model_call` row is **unchanged** — `cost_basis` already reached
  it on every path, by `_record`, and `_record` was not touched. The stage-result metrics
  are what changes, wherever the executor persists or reports them: a succeeded, partial
  or truncated run now carries the basis beside `cost_usd` where it previously carried
  none.
- **An operator** reading a run report can now tell, on a run that **succeeded**, whether
  the cost figure is a number the provider reported or one computed from the lock's
  per-token pins. Previously that was legible only on a run that blew its budget. The
  figure itself does not move; only its provenance becomes readable.
- **A consumer** that was defensively catching `KeyError` on `metrics["cost_basis"]` will
  stop catching it. Nothing in this tree does — the repair adds a key, removes none, and
  changes no existing value.
- **The CSV download is byte-identical and its header is unchanged.** The removed property
  was never served. No operator observes anything about defect 4; the change is legible
  only to a reader of the source, which is the whole point of it.
- **Defects 1 and 2 change no behaviour at all.** No API response, no stored row and no
  refusal differs. They change what a reader of the source is told.

**Public-surface note for re-certification.** `CsvExport.filename` was a public attribute
on a class exported from `auditmanager.exports`. Removing it is a source-compatible break
for any caller outside this repository; there is none, and the repository is a prototype,
but it is the one removal in this wave rather than an addition.

---

## 5. What I did not repair

- **The header and the frontend spelling the download name differently.** Permitted by
  the frozen contract, which pins no value; the brief says so and the tree agrees. Not a
  defect, and reconciling it would create a constraint the contract does not impose.
- **`api/routers/export.py` and `web/src/shared/api/csv-columns.ts`** are outside my owned
  paths in any case. I read both; neither needs a change.
- **`_record`'s `cost_basis: str = "estimated"` default.** A defaulted provenance field is
  arguably a smell — a call site that forgets it records "estimated" silently rather than
  failing. There is exactly one call site and it passes the value explicitly, so this is
  latent, not live. Flagging rather than changing it: it is a behaviour change with no
  defect behind it, and this wave's rule is to keep changes minimal.

## 6. What was false in the brief

Both are small; neither changed the work.

1. **The class is named `CsvExport`, not `ExportResult`.** Both the dispatch
   (`docs/program/dispatch/W11-FIX.md`, defect 4) and the orchestrator's summary say
   "an `ExportResult.filename` property". There is no `ExportResult` anywhere in the tree;
   `grep -rn ExportResult` returns nothing. The property was `CsvExport.filename`, and the
   rest of the description of it was accurate.
2. **Line numbers for defect 3 have drifted.** The brief cites the overrun branch at
   "~line 278" and the success metrics "around line 338"; they were at 277 and 312 on
   arrival. The `~` makes this approximate and the description was precise enough to
   locate unambiguously. Recorded only because this programme tracks stale premises.

Everything else checked out. In particular the brief was **right to tell me to count**:
`_FORBIDDEN` has six entries, the docstring named five, and the wave-10 brief's "seven"
was wrong — three different numbers for one tuple, which is a good argument for the
executable count now in the suite.

**I do not certify my own repair.** I make no claim about whether PC-01 still holds. What
I changed and what I proved is above; a later session re-certifies against it.


---

## 7. Final gate and elapsed time

`make gate` on the finished tree: **1277 passed / 5 skipped / 116 subtests**,
`GATE OK: battery, foundation, frontend and whitespace all pass`. Arrival was
1264 / 5 / 116; the thirteen added are the guards in §3, and **no pre-existing test
changed its result** — the one test that had to change was rewritten by me, deliberately,
and is described in §3.3.

| | |
|---|---|
| Arrival | 2026-09-16T19:30:07+05:00, HEAD `5d14921` |
| Finish | 2026-09-16T19:49:24+05:00 |
| Elapsed wall-clock | see the two stamps above — a little over an hour, of which ~10 minutes is the two full gate runs at ~3m20s of battery each plus foundation and frontend |

Four commits on `agent/w11-fix`, worktree clean:

```
0a8e9d7 docs(w11-fix): open the review record; premises checked against the tree
dc6ae78 fix(w11-fix): four defects — two false comments, an undercounted docstring, cost_basis, a dead filename property
e29c355 test(w11-fix): a guard for each of the four repairs
83f5aa9 docs(w11-fix): the four repairs, their mutations, and what changed for an operator
```

No tag, no push, no merge to `main`. No root dependency added; no bytes added to
`fixtures/synthetic/ar/**` or `fixtures/validation/PC-02/**` — neither was touched. Every
edit is inside the owned paths. `tests/contract` and `tests/checkpoint` were not run and
not modified.
