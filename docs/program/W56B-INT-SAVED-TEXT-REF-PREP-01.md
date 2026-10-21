# W56B-INT-SAVED-TEXT-REF-PREP-01 — supplied Run source reference

Base: `origin/dev` candidate 44 at
`4c16ccd7ae975d5a32829e9bcdf975f8b12f66e1`.

The new pure `select_run_text_layer_ref` check validates a supplied
run-scoped successful `source_preparation` stage envelope against the frozen
registry version. It requires page inventory and exactly one text-layer
reference, permits only the optional recognised-text reference, and refuses
duplicate roles/Blob IDs and malformed references. The selector gives a
future calling service the exact Blob ID, SHA and size to read under its
current Attempt.

`check_run_text_window_input` then binds supplied bytes to that selected
reference using the existing W56b source-byte checker and returns complete
page windows with original Unicode offsets. An oversized page retains the
existing explicit page-number refusal.

## Checks

- Focused saved-text reference, source-byte and reply-cohort suites:
  **37 passed**.
- Python compilation, frozen SHA-256 readback, direct task governance,
  whitespace and exact four-path proof: passed at handoff.
- No Docker, PostgreSQL, S3, proxy, paid call or complete gate was run.

## Contracts and limits

No contract, migration, registry, W54/W57 path, provider, API/UI,
composition, dependency or served runtime change. The stage wrapper is a
caller-supplied value; constructing it does not prove a DB read, current
Attempt authority or a bounded Blob read. The future service must prove those
facts before and after its external read, and obtain the approved W56b
budget/effect/response policy before calling a model.

Rollback is removal of this additive module/test before wiring; no data
migration or runtime flag is needed.

Only these four paths change:

- `src/auditmanager/analysis/text/saved_window_custody.py`;
- `tests/integration/analysis_text/test_saved_window_custody.py`;
- `docs/program/tasks/W56B-INT-SAVED-TEXT-REF-PREP-01.md`;
- this report.

The integrator can cherry-pick the exact local commit after checking frozen
surfaces and direct handoff. The next W56b calling-service task must own the
authoritative Run/StageResult query, Attempt fencing and Blob read explicitly.
