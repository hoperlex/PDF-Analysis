# W52-DEBT-CODE-128F7 — executor handoff

Task: `docs/program/tasks/W52-DEBT-CODE-128F7.md`. Exact dispatch base:
`f91883a04c047ca882744bd1b8a2a51729a88a90`. This repairs D-128 F-7 only.

The presentation model now keeps distinct `unknown` (missing) and `unrecognized`
(present but outside the frozen vocabulary) provider-mode states. The badge never gets
either as `live`. Run cost uses the same distinction for a reported cost basis. Run
progress and stage comparison show Russian labels for the unfamiliar states, including
machine-readable markers, without echoing the raw values. Valid modes and bases keep
their earlier display. The four affected model/screen tests pin both sides of the
distinction and inject the judge's unfamiliar values.

Changed files: `web/src/entities/audit-run/model/run-presentation.ts`, its public
`index.ts`, the two widgets under `web/src/widgets/{run-progress,stage-comparison}/ui/`,
four matching `web/tests/unit/{run,screens}/` tests, and this report. Focused Vitest:
136 passed across four files; `npm --prefix web run lint` passed; `git diff --check`
passed. No temporary stand, QA, typecheck or full gate was run; their evidence remains
D-139/D-140. The comparison verdict still compares the recorded raw values, while its
cells mark unrecognised values; this code does not invent a new comparison verdict.

No contract, migration, dependency/lock, backend, composition root or global style was
changed. D-128 remains open for F-1/F-2/F-10/F-11 and validation. Integrator may merge
this code preparation to `origin/dev` after exact ancestry and basic checks. Rollback is
the code commit's revert; no runtime feature flag.
