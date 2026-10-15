# W56A-INT-PROPOSAL-GROUNDING-PREP-01 — development result

`ground_proposals` joins the sealed AR v2 response parser with the PDF-only
quote resolver. It attempts every quoted item, retains each ungrounded reason,
and excludes an entire proposal whenever any item fails. Accepted proposals
retain their parsed ordinal, texts, proposed severity and PDF code-point
anchors. A rejected proposal exposes diagnostics only: the resolved subset
cannot be mistaken for publishable evidence.

## Checks

- Focused parser/resolver/new-adapter pytest: 23 passed.
- Python module compilation: passed.
- Direct task-governance: `[]`; `git diff --check`: passed.
- Complete local gate, paid provider calls and acceptance: deferred under
  R-135 and the owner's code-first instruction.

## Contracts and limitations

No contract, migration, profile identity, provider, executor or database
behavior changes. The adapter is pure and unused by runtime. Parser output
does not preserve positions of malformed raw-array elements, so
`proposal_ordinal` is a position among structurally accepted proposals; the
later artifact must allocate its own ordinals after this filter. Diagnostics
are not yet persisted. MODEL-PIN remains blocked, and this task makes no
live AR v2 or beta claim.

## Integration handoff

`W56A-PROFILES-01` may wire this adapter only after a fresh grant. It must
persist or otherwise retain rejected diagnostics, allocate artifact ordinals
only for accepted proposals, then route accepted PDF anchors through the
existing grounding gate. `W56A-MERGE-01` must merge only grounded artifact
observations. The provider and profile identity still need MODEL-PIN.

Changed paths are limited to the new task/report, the new pure module and
focused test, and the short current-state entry. Frozen contracts, migration
head, provider lock, composition, root dependencies, styles and `origin/main`
were untouched.
