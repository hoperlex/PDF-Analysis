# W56B-INT-RUN-TEXT-READ-01 — saved TEXT read under current Attempt

Base: completed W56b pure seam
`cf4a9a967c68d7c7ee892a934ef8ed8f7d3d5b3a`.

The unserved `load_saved_text_windows` service accepts a caller-owned SQLAlchemy
transaction and `AttemptAuthority`. It checks authority, loads the exact
running Run, its frozen Version and one successful saved
`source_preparation` StageResult, then uses the W56b analysis public seam to
select the precise `prepared.text_layer` Blob reference. It refuses a Blob
larger than the explicit byte ceiling before opening storage. The full
stream is checked against its saved SHA-256 and size, then the existing W56b
pure verifier checks the source JSON and complete page windows.

Before returning, the service checks the Attempt again and rereads Run,
Version and StageResult; any changed value refuses. The caller's transaction
holds the repository locks during the object read. Returned windows do not
reserve authority for a later provider effect.

## Checks

- Saved TEXT service and existing W56b custody/source suites: **41 passed**.
  Cases include exact Blob reference, both Attempt fences, changed Run,
  Version or StageResult/reference, duplicate/failed stage, foreign project,
  oversized/corrupt Blob and an oversized later page.
- Python compilation, frozen SHA-256 readback, direct task governance,
  whitespace and exact five-path proof: passed at handoff.
- No Docker, PostgreSQL, S3, proxy, paid call or complete gate was run.

## Contracts and limits

No contract, migration, registry, W54/W57 path, provider, API/UI,
composition, dependency or served runtime change. `analysis/public.py` adds
only the W56b pure exports used by this service. The byte ceiling and
document-text character ceiling are supplied explicitly. Their budget
derivation, an effect journal and any model invocation require a later W56b
policy/freeze and separate task. This service makes no DB or S3 write.

The focused tests use fake Run, Version, Job and Blob ports; they establish
call order and fail-closed behavior but are not a real persisted DB/S3
acceptance. The caller must keep the transaction open through the read and
reacquire authority before any later effect.

Rollback is removal of the additive service/test and public exports before
wiring; no data migration or runtime flag is needed.

Only these five paths change:

- `src/auditmanager/analysis/public.py`;
- `src/auditmanager/runs/text_window_input.py`;
- `tests/integration/runs/test_text_window_input.py`;
- `docs/program/tasks/W56B-INT-RUN-TEXT-READ-01.md`;
- this report.

The integrator can cherry-pick the exact local commit after checking the
frozen surfaces and direct handoff. It remains unserved until W56b policy,
effects and real DB/S3 acceptance are ready.
