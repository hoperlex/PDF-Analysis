# CFB-INT-DEV-PUBLISH-13 — code-first dev candidate

The checked candidate builds on `origin/dev=8f113f6b` with eight completed
source/correction commits through `b882dda9`. W56a retains one recorded
response's usage and builds a complete, source-bound `StageResult` value
without activating the executor. W57a reads stored build facts and compares
independently supplied digests with a retrieval candidate; no verified row is
written. W58 checks target Blob payloads through the public storage port in
an isolated future drill. W59 seals raw version diffs and proposes only exact,
unambiguous finding matches, leaving expert approval separate. A docs-only
correction restores the full program task-governance test to green.

## Checks and publication boundary

The combined focused source/governance suite passed **241 tests** on the
integrated code base. The governance file alone passed 16 tests. Direct
governance on this task, exact staged paths, clean candidate, frozen inputs,
remote predecessor and pushed SHA are checked before/after publication.
Full `make gate` for W56–W63 remains deferred under R-135. This dev
publication does not trigger the `origin/main` auto-deploy workflow and does
not qualify W54 corpus or prove beta acceptance.

## Contracts and remaining work

This integration commit changes only this report, its task and the leading
`CURRENT_STATE.md` paragraph. Source tasks add no shared contract, migration,
root lock, composition root or global style change. The W54 base dump still
needs restore verification, priced repair and embedding build; W57 needs
independent proof/approved map/custody; W58 needs a real DB/S3 restore drill;
W59 needs authoritative approved SheetLinks, persistence and expert-confirmed
carryover. W55b's separate main candidate is `6d63802a` and is not included
in this development publication.
