# W19-RUN — the run screen says what the run did

**Session:** `W19-RUN`  **Branch:** `agent/w19-run`  **Worktree:** `/root/w19run`

## HEAD on arrival

```
d3520b0af02861c56896cf504bb94f435674e966
d3520b0 merge(W19-API): the count the contract promised, and the mutation that passed first
```

Provisioned from `origin/dev` after the integrator pushed. On my first attempt `origin/dev`
was `653152f`, eighteen commits behind, and I stopped at STEP 0 rather than branch from an
unpushed local ref. Recorded here because the stop is part of this session's history.

## The brief's framing, corrected against the tree

The brief lists six fields that "no screen renders". That is true of three of them and
false of three. Before writing anything I read what the run screen already does.

| field | brief says | the tree says |
|---|---|---|
| stage `started_at` / `finished_at` | never read back | **already rendered.** `stage-table.tsx:44-45,58-63` has Started and Finished columns, fed by `stageRows` (`run-presentation.ts:198-199`) |
| `published_finding_count` | not rendered | **already rendered.** `run-presentation.ts:137` reads it, `run-progress.tsx:70-71` prints it |
| `diagnostic_observation_count` | not rendered | correct — no reference anywhere in `web/src/` |
| `cost_micros` | not rendered | correct |
| `cost_basis` | not rendered | correct |
| `model_call_count` | not rendered | correct |

**Why the user saw what they saw.** `formatInstant` (`format-instant.ts:9-14`) returns
`'—'` for `null`, `undefined` and `''`. "Started — Finished —" is therefore not a screen
that ignores the columns; it is a screen faithfully reporting that the reading carried no
stage timings. Likewise "Published findings: not reported" is the `findingCount === null`
branch at `run-progress.tsx:71` firing because the field was absent from that response.

This matters for what the work is. The defect is not uniformly "the screen drops fields".
For three fields it is "the screen has no place for them at all", and for the other three
it is a data question that belongs to whoever owns the response. I verified the data
question before assuming either: `bootstrap/adapters.py:352-358` populates all five run
fields and `:379-380` populates the stage timings, so a fresh run does carry them. The
brief's "everything you need is already in the response body" holds.

## Base gate figures

Integrator's figures, measured on the merged tip `d3520b0`: battery 1785 / 5 skipped /
168 subtests, foundation 35, frontend 633 (46 files), exit 0. My own measurement is
recorded in the gate section below.

## Status

Opened before the first edit. Sections below are filled as the work lands.
