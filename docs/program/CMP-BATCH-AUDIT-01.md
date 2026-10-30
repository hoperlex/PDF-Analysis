# CMP-BATCH-AUDIT-01 — D-263 batch act journal

Completed 2026-10-30 under the root's exact `ingest/comparison_batch/service.py` grant. API/migrations/shared registry are unchanged; root owns debt-register closure and integration.

Each successful exclude/retry/pause/resume/cancel appends its `comparison.upload_set_excluded`, `comparison.upload_set_retried`, `comparison.upload_paused`, `comparison.upload_resumed` or `comparison.upload_cancelled` event on the caller's session, after the act and before command success. A replay exits before the append. An append failure propagates and rolls back the state change and command receipt together.

The aggregate is ComparisonUploadSet (set ID) or ComparisonUpload (upload ID). Payload fields are only typed `comparison_upload_id`, `project_uid`, `actor_uid`, `command_id`, plus `set_id` for set acts. No display name, filename, document text, actor label, provider data or idempotency key is included.

The C2 seal's D-263 analysis found no shared event-type schema registry: events/v1 admits a free event string, the database admits these names and recovery already classifies the comparison prefix. `comparison/audit.py` is a legacy Comparison-aggregate-specific writer, not an ingest boundary for these acts. This implementation therefore keeps its five-entry closed map and typed identity checks local and adds no deep import or generic journal abstraction.

Focused validation: **6 actual-service/DB tests passed in 2.75 s**. All five acts have exactly one event on successful keyed replay, the correct aggregate/actor and a succeeded command reference. A forced journal failure rolls back the set act and command; retrying the same key after recovery succeeds once. Fixtures seed valid metadata transitions so this focused journal test has no multipart/PDF dependency; the existing INGEST-02 upload tests are unchanged. The first broader fixture preparation hit the local MinIO low-free-space refusal before reaching an act (767 MiB free), which is not reported as a writer failure or hidden by a skip.

`git diff --check` clean. Authored files: exact batch service, `tests/integration/ingest/comparison_batch/test_audit.py`, this report and its task. No full gate/build, live model, deploy or remote-ref update. Root may merge the local commit and close D-263's implementation debt; tomorrow's broader windows remain deferred.
