# CFB-INT-DEV-PUBLISH-19 — isolated target-object restore preparation

The candidate builds on directly read `origin/dev=c157ee0d4601f2bf81c68708ebf556b95b87acd5`.
Completed W58 source `822a4b3bf01ad6e5d1512044e473ffeb618ba8d4`
was cherry-picked as `b2cc131d` without a payload edit. Its four new files
add `restore_sealed_objects`, fake-client tests, a formal task and a result
report. The helper verifies a private sealed mirror, conditionally uploads
missing objects to a caller-designated isolated S3 target, reads every target
byte and checks the exact paginated key set. It is not connected to runtime.

## Checks

- The integrated recovery suite passed **107 tests**; program contract and
  governance suite passed **28 tests**. The new integration task's direct
  `governance_findings` result was `[]`.
- The source task reported 13 focused, 107 recovery and 16 governance tests,
  Python compilation, whitespace and exact four-path containment green.
- The API/domain/error/stage digests stayed at the task-pinned values;
  migration head remained `0022_findings_v2`, API 47 paths / 54 operations /
  124 schemas, error catalogue 25 codes, `VERSION=0.6.0`.
- The W55b `d3acd511` release candidate remains an ancestor of this dev
  graph, but its separate complete gate is not evidence for W58. A clean
  exact dev tip, fresh remote read and fast-forward proof are required before
  publishing this candidate to `origin/dev`.

The integration commit adds only this report, its task and the bounded
`CURRENT_STATE.md` edit. The cherry-pick adds only the four W58 source paths.
No shared contract, migration, root lock/dependency, composition root,
global style, provider secret, deployment input, `origin/main` or tag is
changed. The source and target objects, DB and Blob have not been restored
on a real service. Source quiescence, endpoint isolation, real MinIO readback
and PostgreSQL-plus-Blob recovery remain separate acceptance work. The
complete beta gate is deferred under R-135; no beta or deployed state is
claimed.

## Publication handoff

Publish only the clean exact checked dev SHA as a fast-forward from the
recorded predecessor. Read back the remote ref into ignored local evidence.
If it moved, stop for review; never force-push. This task grants no
`origin/main` authority. The next owner should run an isolated real MinIO and
PostgreSQL recovery drill before calling W58 accepted.
