# CFB-INT-AR-V2-PROFILE-06 — integration result

## Result

An immutable recorded-only AR v2 descriptor pins distinct `ap_` and `pb_`
identities to the six reviewed resources, response schema and prompt material.
The executor-side preflight resolves that descriptor through `analysis.public`
before comparing a persisted run's profile, bundle, mode and state. Well-formed
unregistered IDs and content drift are rejected before effects.

## Changed files

The four owned files of `W56A-INT-AR-V2-RECORDED-PROFILE-01`, five owned
files of `W56A-INT-RECORDED-PREFLIGHT-BIND-01`, this task/report and
`CURRENT_STATE.md`. The exact twelve paths are listed in the integration
task.

## Checks

- Descriptor, preflight and recorded chain: **25 passed**. Five pytest
  warnings concern stale `/tmp/pytest-of-root` cleanup, not test failures.
- Changed Python compilation, direct governance on three tasks, frozen hashes,
  whitespace and exact path proof: pass at integration.
- No DB acceptance, provider call or complete `make gate` under R-135.

## Contracts and remaining limits

No `contracts/**`, migration, provider lock, root dependency/lock file,
composition root, global style, active v1 path, historical recording,
corpus source or `origin/main` changed. Migration head remains
`0022_findings_v2`. The descriptor's `2.0.0-recorded` is an internal version,
not a contract or release version; its stage tuple is inert. It does not pin a
live model identity or price, create a recorded request/response artifact or
activate AR v2 in the run executor. Those remain concrete next coding tasks.

## Publication

Target: `origin/dev` only after exact checks and remote fast-forward proof.
No `origin/main` authority, release tag or complete `make gate` is claimed.
