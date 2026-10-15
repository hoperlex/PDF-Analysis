# W56A-INT-MERGE-INPUT-PREP-01 — development result

The pure `prepare_merge` adapter converts only accepted PDF-grounded AR v2
proposals into `MergeObservation`s. It assigns dense ordinals after filtering,
retains the parser proposal ordinal at each position, and delegates grouping
to the existing deterministic `finding_merge` rule. It refuses a malformed
accepted/rejected partition or incomplete accepted evidence.

## Checks

- Grounding, adapter and merge-core tests: **23 passed**. The regression has
  one rejected proposal sharing a valid quote with accepted proposals; it is
  absent from every merge group. All-rejected input produces an empty group set.
- Compilation of the new module: passed.
- Direct governance check of this task file: `[]`.
- Repository-wide governance test remains red on six pre-existing W56a task
  files whose four new governance sections are absent or malformed. The new
  task file is not among its findings; no unrelated task file was changed.
- `git diff --check` and exact changed-path proof: recorded at integration.
- Full local gate and acceptance: deferred under R-135.

## Contracts, limitations and integration

No contract, migration, provider lock, existing merge rule, runtime stage,
database or UI behavior changed. The adapter is not wired into the executor.
`source_proposal_ordinals[n]` maps merge observation `n` to a structurally
accepted parser proposal; the latter is diagnostic provenance, not a finding
identity. Publication of findings and diagnostics needs a later grant. The
gateway model identity remains unverified, so live AR v2 stays inactive.

The next integrator may consume this adapter in the AR v2 stage only after
the corresponding task freeze, and must preserve the complete-proposal
rejection rule. Rollback is a revert of this additive module and its test;
there is no data rollback or feature flag.

The exact changed paths are the adapter, its test, this report, its task file
and the short current-state entry. `contracts/**`, migrations, provider lock,
root dependencies/locks, composition root, global styles and `origin/main`
are untouched.
