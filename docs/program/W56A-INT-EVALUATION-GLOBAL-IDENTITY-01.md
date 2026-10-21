# W56A-INT-EVALUATION-GLOBAL-IDENTITY-01 — result

The offline seeded AR v2 bridge now tracks published finding and observation
IDs over the complete run series. A duplicate in another bundle raises the
existing `publication_identity_invalid` error. A complete series with unique
published IDs preserves 21/21 seeded issue recall and zero control hits.

## Changed files

- `tools/evaluation/bridge.py` — shared ID sets for all supplied publication results;
- `tests/contract/evaluation/test_bridge.py` — globally unique synthetic IDs,
  complete-series positive case and separate cross-run collision mutations;
- `docs/program/tasks/W56A-INT-EVALUATION-GLOBAL-IDENTITY-01.md` — task grant;
- this report.

## Checks

- Before the bridge correction, both cross-run collision tests failed because
  no `ValueError` was raised: **2 failed, 7 passed** in the bridge module.
- Focused bridge and matcher suites after correction: **24 passed** in 0.55 s.
- Python compilation of the two changed code/test files: passed.
- Direct task governance `governance_findings`: `[]`.
- Frozen W56 plan, seeded manifest, API, error catalogue, stage registry and
  provider lock hashes matched the task; migration head is `0023_norm_citations`.
- `git diff --check` and exact four-path allowlist: passed at source commit.

## Contracts and limits

No contract, migration, source fixture, baseline, recording, runtime publisher,
provider lock or root dependency changed. The bridge still scores a plan when
its optional publication result is absent; the caller must independently
establish real Run/source custody and actual recorded execution before making
a quality claim. This task did not run a provider or a real database/S3 lane.
The full beta gate remains deferred under R-135.

## Integration instruction

Cherry-pick only the four owned paths from the source commit. Run the focused
bridge/matcher suite on the integration tree. Preserve the separate W56a
recorded baseline, source-byte binding, model identity and beta gates.
