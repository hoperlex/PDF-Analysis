# Wave 10 — convergence notes, written as the streams land

Integrator's running record. Committed as each stream reports rather than at the end: the
first attempt at this wave lost four sessions to a restart, and only committed work survived.

**Two of five streams landed. `W10-API` and `W10-RUN` still running. Nothing merged yet** —
convergence is one act, and the gate run has to be done alone.

## Verified by me, against the tree, not taken from the reports

A subagent's report is a claim like any other. These two are the consequential ones and both
hold.

### `W10-FND`'s headline: the CSV column order is unguarded

`tests/integration/exports/test_csv_contract.py`:

- line 82 — `assert header == list(COLUMNS)`. Both sides move together if `COLUMNS` is
  reordered.
- line 69 — `dict(zip(header, row))`. Every row dict is keyed by the **file's own** header,
  so `row["finding_uid"]` follows the mutation and every later assertion keeps passing.

Swapping two entries in `COLUMNS` therefore changes the emitted header, the expected header
and the row keys consistently, and nothing notices. That is `OD-11`'s frozen column order,
on **criterion 7's surface**, which PC-01 has certified twice.

The sharpest part of the finding is one the report makes and I confirm: the same file pins
`BOM` against a literal, with a comment recording that this exact phrasing once let the BOM
be deleted. **The lesson was applied to one constant and not to the one beside it.**

### `W10-ANL`'s defect 4: a test named for a pin that pins nothing

`tests/integration/analysis_text/test_profile_and_artifact.py:38`:

```python
resolved = resolve_profile(AR_TEXT_PROFILE.analysis_profile_id)
assert resolved is AR_TEXT_PROFILE
assert str(AR_TEXT_PROFILE.analysis_profile_id).startswith("ap_")
```

It feeds `resolve_profile` the module's own constant and asserts the result is that same
constant. If the profile ULID changed, the test passes unchanged. The name promises a pinned
identity; nothing is pinned.

Wave 9's failure mode, already in the tree, found by mutation rather than by reading.

## A defect in my own brief, corrected mid-flight

`W10-FND` established that the mutation-copy recipe every brief carries — symlink
`contracts/`, `docs/`, `fixtures/` — is **incomplete**. `tools/` and `db/` are also resolved
from the copy's root, and without `tools/` four `p02_journey` tests fail against an
**unmutated** copy.

That is worse than a stale premise: it manufactures reds. A sweep that went straight to
mutating would have filed four guards over a tree it never broke.

I have written to `W10-API` and `W10-RUN` mid-run with the correction and with the
instruction that matters more than the symlink list: **run the clean copy against your
suites and confirm it is green before trusting any red.** Both were asked to report whether
their copy carried `tools/` and `db/` and whether they established that baseline, and to say
plainly if they did not rather than silently re-running.

This recipe has been in every brief since wave 3 and in my own harness throughout. It has not
produced a wrong result that I know of, because the suites I ran happened not to include the
four affected tests — which is luck, not method.

## Self-reported faults, and why they are worth more than clean reports

Both landed streams reported faults of their own that nothing would have caught:

- `W10-ANL` ran a background batch and a foreground verification against **one shared
  mutation copy**, producing at least one false green; it discarded everything measured in
  the overlap window and re-ran isolated. It also wrote three mutations that did not mutate —
  the failure my own stream hit — and caught each by re-reading for semantics after the
  textual readback passed.
- `W10-FND` miscounted its own summary three times, and recorded each correction as a
  separate commit rather than a quiet amendment. It also caused its only two gate failures
  itself, by killing an orphaned run that stranded a temporary object.

A stream that reports none of this is not necessarily cleaner.
