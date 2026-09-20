# `W24-CERT2` — `PA-01` re-certified at `16d3503`

**Session** `W24-CERT2`. **Base** `16d3503` (`origin/dev` on arrival). **Branch**
`agent/w24-cert2`. **Worktree** `/root/w24cert2`. **Lane** `gate-w24a`.

This file is opened before the first measurement, per the dispatch, and filled as each
verdict is produced. Nothing below is written before the command that produced it has run.

## 0. Status

OPEN — measurements in progress.

## 1. The criteria, quoted from the file

`docs/program/ALPHA_ROADMAP.md` §5, lines 307–331, quoted rather than paraphrased. The
preamble matters as much as the ten items, because it is where *"on the server"* and *"from
a clean clone"* are said:

> Executed **on the server**, from a clean clone, by an independent session, and recorded in
> `artifacts/checkpoints/PA-01/report.json` with the commit, the image digests and the
> migration head:
>
> 1. `deploy.sh` brings the stack up from a clean clone on a machine that has never run it,
>    and the schema the running app serves conforms to the frozen
>    `contracts/api/v1/openapi.json` — the same check the gate runs, re-run against the
>    deployed process rather than against a build artifact;
> 2. the browser reaches the app over TLS, and a request carrying no token is refused with
>    `authentication_required` **from the application**, not by the proxy — shown for an
>    operation of each kind, so the dependency is proved to be in front of all twelve rather
>    than in front of the one that was tried;
> 3. a project is created and a real AR PDF is uploaded through the browser, producing an
>    immutable version and a verified private object;
> 4. a live `text_analysis` run completes, with its provider mode and cost visible, and the
>    UI distinguishes running, published, partial and failed — criterion 4's UI clause,
>    which the `e6eae1e` certification explicitly did not establish;
> 5. a finding opens at its exact quotation beside the page it came from;
> 6. an accept, a reject and a later comment are recorded, and the history shows all three;
> 7. the CSV downloads through the browser with its seventeen columns, its BOM and its CRLF
>    intact, and resolves back to the same version and run;
> 8. the server is rebooted and every canonical row, object and decision survives;
> 9. each of the five refusals answers with its own typed code **through HTTP**, and a
>    provider outage fails the run rather than publishing it;
> 10. `reset.sh` dumps, wipes and re-initialises; the app comes back empty and working; the
>     dump restores the wiped state.

**The frozen inputs, checked rather than inherited.** `contracts/api/v1/openapi.json` —
12 paths, 15 operations, 46 schemas, read out of the document itself.
`contracts/domain/v1/error-codes.json` — 21 codes, `frozen: false`,
`status: draft_candidate`. Both as the dispatch states them.

## 2. Base gate

`make gate FOUNDATION_PYTHON=/usr/bin/python3.12` on the committed, clean tree at
`2126598` (this review's opening commit; `16d3503` plus this file), lane `gate-w24a`,
`POSTGRES_PORT=55940`, `S3_API_PORT=59540`/`59541`, `POSTGRES_DB=audit_w24a`, bucket
`auditmanager-gate-w24a`. Exit code from `$?` after a redirect, never through `| tail`.

```
foundation  35 passed in 28.97s
battery     1909 passed, 5 skipped, 1 warning, 168 subtests passed in 236.63s
frontend    Test Files 48 passed (48)   Tests 706 passed (706)
GATE OK: battery, foundation, frontend and whitespace all pass
GATE_EXIT=0
```

**Identical to the dispatch's figures in every number.** Provisioning was
`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` (exit 0) and `npm --prefix web ci`
(exit 0, 184 packages); without the second the gate exits 2 at the frontend.

## 3. The stack driven

## 4. The ten verdicts

## 5. Diff against `certification-0f9989a.json`

## 6. Proposed register rows

## 7. False premises in the dispatch

## 8. Limits, spend and elapsed
