# W59-INT-PROFILE-METADATA-PREP-01 — development result

The new read-only catalogue records category identifiers and sheet-type
labels for all 14 sections in the local legacy portal. It has 162 category
codes, 201 sheet types and SHA-256 digests for every source file in each
section directory. A one-time source comparison confirmed that all 14
directories' file digests and category codes match exactly. The bundled
resource is pinned by SHA-256
`ffc79739053944e8adc2546da0bf82a99c4a781ebbed28c9f4239b267cfa8490`;
the loader rejects a missing or changed resource.

## Checks

- Focused catalogue tests: 4 passed. Pytest emitted five cleanup warnings
  about pre-existing directories under `/tmp/pytest-of-root`; no test failed.
- Python compilation: passed. Direct task governance: `[]`.
- `git diff --check` and exact changed-path proof: passed at integration.
- Complete local gate and acceptance: deferred under R-135 and the owner's
  code-first instruction.

## Contracts and limitations

No contract, migration, active profile, provider, stage, route or database
behavior changes. The catalogue deliberately contains no role/checklist
instructions, norm clauses or proposed findings. Its identifiers are legacy
candidates, not approved categories for W59–W62. `PB` has no legacy source
and must be authored from scratch. No corpus-backed normative verification
has yet been run.

## Integration handoff

Each W59–W62 profile author can use this catalogue as vocabulary and trace
each candidate to its source SHA. The author must review instructions,
ground normative statements in an available snapshot, seal categories and
profile identity, and add recorded evaluation before runtime routing. `PS`
is the explanatory-note section; `PB` remains fire safety.

Changed paths are the new candidate package/resource, one test, this
task/report and the short current-state entry. Frozen contracts, migration
head, provider lock, existing runtime modules, composition, dependencies,
styles and `origin/main` were untouched.
