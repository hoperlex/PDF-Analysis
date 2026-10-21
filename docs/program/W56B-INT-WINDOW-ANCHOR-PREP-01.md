# W56B-INT-WINDOW-ANCHOR-PREP-01 — saved TEXT window quote boundary

Base: `origin/dev` candidate 37 at
`f0580e089867ba6a9380a48dfca19a23e47f6788`.

An additive pure `resolve_window_anchor` check validates that the complete
window tuple covers the saved text layer once, in page order, with the saved
version, normalization ID, text and global Unicode offsets. It refuses a
proposal whose page lies outside the selected response window. An in-window
literal quote delegates to the existing page anchor resolver, so successful
evidence keeps the original document-global coordinates and absent quotes
keep the existing ungrounded result. This function has no served caller.

## Checks

- Focused TEXT window and chunk preflight suites: **24 passed**. They include
  Russian/emoji global offsets, blank pages, out-of-window citation refusal,
  missing quote, changed/omitted/duplicated windows and invalid indexes.
- Python compilation, direct task governance, frozen SHA-256 readback,
  whitespace and exact path proof: recorded at handoff.
- No Docker, PostgreSQL, S3, proxy, paid call or complete gate was run while
  the W55b release gate owns this host.

## Contracts and limits

No contract, migration, stage registry, existing analysis consumer/producer,
API/UI, composition, dependency or runtime behavior changes. This is a
neutral evidence check, not a choice of model, request budget, cross-window
contradiction rule, retry rule or effect journal. It does not establish saved
Run/Attempt custody or publish findings. Those require W56b freeze, owner
rulings and real saved-input acceptance before activation.

Rollback is removal of the additive module/test before wiring; no data
rollback or feature flag is needed.

Only these four paths change:

- `src/auditmanager/analysis/text/window_anchor.py`;
- `tests/integration/analysis_text/test_window_anchor.py`;
- `docs/program/tasks/W56B-INT-WINDOW-ANCHOR-PREP-01.md`;
- this report.

The integrator can cherry-pick the exact source commit as an unserved W56b
evidence preparation after checking the frozen surfaces and direct handoff.
The future stage must use the saved text layer and full partition from its
current Attempt and journal each provider call under a separately approved
budget/effect policy.
