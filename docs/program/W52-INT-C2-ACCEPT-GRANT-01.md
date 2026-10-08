# W52-INT-C2-ACCEPT-GRANT-01 — refreshed ACCEPT dispatch

**Date:** 2026-10-08. `W52-INT-C2-RELNOTES-01` is published and read back
on `origin/dev` at `a6ff1ff6ea8bf5c21ed125f3a07c9cb613a85a89`.
`origin/main` remains `9d5b0105334f2f54d80d1f3ee0109b59fb6d8b7c`.

## 1. Files and result

`W52-ACCEPT-01` now depends on the completed RELNOTES integration and
starts from this grant's eventual development readback. Its allowed
implementation paths, behavior, checks and no-main boundary are unchanged.
This grant changes exactly:

```text
docs/program/tasks/W52-INT-C2-ACCEPT-GRANT-01.md
docs/program/tasks/W52-ACCEPT-01.md
docs/program/W52-INT-C2-ACCEPT-GRANT-01.md
```

## 2. Checks

Review the three-path diff, `git diff --check`, wave-governance and
prose/count checks on the clean commit. The SHA and remote readback are in
the final integrator handoff. No acceptance or full-gate check is claimed.

## 3. Contracts

No contract, migration, generated client, product version, authored note,
loader or acceptance behavior changes. The frozen API remains 30/37/83
with 23 errors and migration head `0016_release_notes`.

## 4. Risks and limits

ACCEPT still needs its own implementation and local checks. D-137–D-140
retain QA, independent review, live acceptance and full gate. This grant
does not authorize `origin/main`.

## 5. Integrator instruction

Publish the clean docs candidate only to `origin/dev`, read back its SHA,
then start `agent/w52-accept-01` from that exact value. Merge ACCEPT only
after its task checks and path audit.

## 6. Forbidden-hotspot proof

The three paths in §1 are granted by the task. No acceptance script,
release JSON, contract, migration, root dependency/lock, composition
root, global style, tag, main ref or deployed service is changed.
