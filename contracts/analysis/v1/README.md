# Analysis package contract v1 — draft

The control plane schedules work by immutable package references. Engine returns a result package; control plane validates schema, checksums, fencing token/attempt ownership and required artifacts before publication.

The schemas here are a **minimal bootstrap boundary**, not the final list of stage-specific fields. Stage-specific artifact payloads get their own schemas/versioned roles as S03/S04 contracts are frozen.
