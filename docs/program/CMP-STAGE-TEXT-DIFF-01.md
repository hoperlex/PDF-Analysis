# CMP-STAGE-TEXT-DIFF-01 — raw differences and cross-sheet hints

Task: [`CMP-STAGE-TEXT-DIFF-01`](tasks/CMP-STAGE-TEXT-DIFF-01.md). Base `35782bdf55c1394821ab9e771b94186e8573e666` is the completed pure evidence core. This branch owns no served route, schema, queue or remote ref.

## Implemented

- `build_raw_differences` first computes the conservative exact exclusion set against the complete profile-key manifest. It removes only proven fragments. It then considers changed pairs only within confirmed links, demands a mutually unique candidate, and leaves ambiguous or weak matches as separate `removed`/`added` rows. It pairs a numeric value change only when the rest of a sufficiently long line has the same skeleton; different room numbers are not paired. Exact text withheld by proof cannot return as a fuzzy `changed` pair.
- Candidate work is bounded to 32 links, 4,000 fragments, 10,000 candidate pairs and 512 characters for fuzzy comparison. An over-budget comparison refuses before output. Raw rows reference fragment content keys and thereby retain their original box anchors through fragment storage.
- `find_cross_sheet_hints` looks for a unique, exact, non-repeated left fragment on an unexpected right sheet. It returns only a recommendation; neither map links nor exact exclusions nor raw differences change. The sealed hint table's source/target scope is left/right, so the reverse direction awaits a contract decision.

## Evidence and limits

- Scoped Stage Text tests: **17 passed**. New cases cover numeric change, exact exclusion isolation, ambiguous changed candidates, weak similarity, room-number guard, candidate budget, unique cross-sheet recommendation, repeated text and incomplete manifest. Python package compile and `git diff --check` passed.
- This remains pure code. The served adapter still returns 503, and no fragments, differences or hints are persisted. The full `CMP-STAGE-TEXT-01` includes a durable recomputation request, masks, second-pass UI and staleness checks; those are future integration work. This branch does not claim them.
- No contract, migration, root dependency/lock, composition root, global style, C2 runtime, C3 pair/link service or remote ref changed.

## Integration instruction

The later storage/worker slice must derive complete manifests from the pinned immutable profiles, use only confirmed link items from the selected map revision, persist exact exclusions separately from the raw difference rows, and keep hints nonbinding. A refused or incomplete computation must not publish a partial result.
