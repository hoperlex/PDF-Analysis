# CFB-INT-RECORDED-REQUEST-07 — integration result

## Result

The AR v2 offline builder resolves the pinned recorded profile, requires an
explicit `fixture/` model identity and generation settings, and hashes the
reviewed prompt, response schema, exact PDF text pages and marked OCR into a
`ModelRequest`. A focused test writes an exact-key recording, replays it with
the existing adapter and passes its answer through PDF grounding and merge;
a changed PDF text produces `recording_missing`.

`RecordedAdapter` now verifies `recording.model_id` against the request in
addition to the key. A different or absent model field produces the existing
nonretryable recorded-input error with reason `recording_model_mismatch`.

## Changed files

The four owned files of `W56A-INT-AR-V2-RECORDED-REQUEST-01`, four owned
files of `W56A-INT-RECORDING-MODEL-BIND-01`, this task/report and
`CURRENT_STATE.md`. The exact eleven paths are listed in the integration
task.

## Checks

- AR v2 request, recorded adapter and v1 offline replay: **39 passed**. Five
  pytest warnings concern stale `/tmp/pytest-of-root` cleanup.
- Changed Python compilation, direct governance on three tasks, frozen hashes,
  whitespace and exact path proof: pass at integration.
- No provider call, DB acceptance or complete `make gate` under R-135.

## Contracts and remaining limits

No `contracts/**`, migration, provider lock, root dependency/lock file,
composition root, global style, active run executor, historical recording,
corpus source or `origin/main` changed. Migration head remains
`0022_findings_v2`. The `fixture/` model namespace is offline only and is not
a gateway identity or price pin. AR v2 still lacks active durable
request/response/artifact wiring and a measured recorded model baseline.
The normative verified set and beta gates remain outstanding.

## Publication

Target: `origin/dev` only after exact checks and remote fast-forward proof.
No `origin/main` authority, release tag or complete `make gate` is claimed.
