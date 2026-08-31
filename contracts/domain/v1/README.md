# Domain contract v1

Draft primitives for CP-00. The JSON files are coordination artifacts, not runtime configuration by default. Runtime types/schemas may be generated or mirrored only with contract tests proving equivalence.

Important bootstrap distinctions:

- `finding_uid` != `finding_observation_id`;
- `run_id` != `job_id` != `attempt_id`;
- path/file name/S3 key/display ordinal never substitutes an ID;
- state transitions belong to one authoritative definition and are tested.
