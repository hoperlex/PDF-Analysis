# W52-DEBT-GUARDS-128F2 — executor handoff

Task: `docs/program/tasks/W52-DEBT-GUARDS-128F2.md`. Exact dispatch base:
`2943fdc2152136383b3608dfcd239f970c8f2fc1`. This repairs D-128 F-2 only.

The dashboard invalidation guard now scans TypeScript sources throughout each feature's
`model` directory and identifies executable `useMutation` calls by AST. It no longer
requires a `use-` filename. The existing explicit map of nine hooks and its invalidation
assertions are unchanged. A focused regression case covers `model/archive.ts` and `.tsx`,
while excluding a non-model path, another bounded context, comments and string literals.
Changing the new discovery predicate back to `model/use-*` makes that case fail.

Changed files: `web/tests/guards/dashboard-invalidation.guard.test.ts` and this handoff.
The focused Vitest file passed 15 tests; `npm --prefix web run lint` and `git diff --check`
passed. No temporary stand, QA or full gate was run under D-139/D-140. The guard reads
syntax, so dynamically generated or aliased mutation calls that do not spell
`useMutation` remain outside this particular detection rule.

No contract, migration, dependency/lock, runtime code, composition root or global style
changed. D-128 remains open for F-1/F-10/F-11 and validation. The integrator may merge
this clean code preparation to `origin/dev` after exact ancestry and basic checks.
Rollback is the guard commit's revert; no runtime feature flag.
