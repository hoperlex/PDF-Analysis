# Task CFB-INT-DEV-PUBLISH-46 — integrate W56b read and W57a replay

task_id: CFB-INT-DEV-PUBLISH-46

## Outcome

Publish a clean development candidate adding an unserved W56b saved TEXT
read service with Attempt fences and an unserved W57a local response replay.
Read back the exact `origin/dev` SHA after a fast-forward push.

## Depends on

- `CFB-INT-DEV-PUBLISH-45`, completed at `acb24b5fadeb819978b4636aef0ef3f708cdaac3`.
- `W56B-INT-RUN-TEXT-READ-01`, completed at source `79e988f56793770ca5725e4815c716ccf00d3272`.
- `W57A-INT-V3-LOCAL-EVALUATION-PREP-01`, completed at source `75240c33d30a2f153ec22f50f1681fae4b50222d`.

## Frozen inputs

- base commit: `acb24b5fadeb819978b4636aef0ef3f708cdaac3`
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- development API 48 paths / 55 operations / 131 schemas, errors 25, migration head `0023_norm_citations`;
- `origin/main` and `v0.6.0`: `37393a979a430e490843d7f410e9eca9491a4ea1`;
- R-135: focused checks on intermediate dev candidates, final complete beta gate later.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W56b and W57a source tasks depend on the pure modules integrated
  in dev45. Their new path sets are disjoint, and the sole existing source
  change is the assigned `analysis/public.py` export slot.

### P-01 — exact development predecessor

- captured_at: 2026-10-16
- command: `git rev-parse acb24b5fadeb819978b4636aef0ef3f708cdaac3; git show --format= --name-only 79e988f56793770ca5725e4815c716ccf00d3272 75240c33d30a2f153ec22f50f1681fae4b50222d`
- captured_output:
  ```text
  acb24b5fadeb819978b4636aef0ef3f708cdaac3
  docs/program/W56B-INT-RUN-TEXT-READ-01.md
  docs/program/tasks/W56B-INT-RUN-TEXT-READ-01.md
  src/auditmanager/analysis/public.py
  src/auditmanager/runs/text_window_input.py
  tests/integration/runs/test_text_window_input.py
  docs/program/W57A-INT-V3-LOCAL-EVALUATION-PREP-01.md
  docs/program/tasks/W57A-INT-V3-LOCAL-EVALUATION-PREP-01.md
  src/auditmanager/analysis/profiles/ar_v3/local_evaluation.py
  tests/integration/analysis/test_ar_v3_local_evaluation.py
  ```
- interpretation: the two source commits touch nine disjoint task paths;
  integration adds its two records. The public export has an explicit single
  owner for this wave.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W56B-INT-RUN-TEXT-READ-01.md`
- `docs/program/tasks/W56B-INT-RUN-TEXT-READ-01.md`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/runs/text_window_input.py`
- `tests/integration/runs/test_text_window_input.py`
- `docs/program/W57A-INT-V3-LOCAL-EVALUATION-PREP-01.md`
- `docs/program/tasks/W57A-INT-V3-LOCAL-EVALUATION-PREP-01.md`
- `src/auditmanager/analysis/profiles/ar_v3/local_evaluation.py`
- `tests/integration/analysis/test_ar_v3_local_evaluation.py`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-46.md`
- `docs/program/CFB-INT-DEV-PUBLISH-46.md`

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, stage registry, served provider/API/UI, W54 paths, original
corpus, production DB/S3, credentials, deployment workflow, `origin/main`
and tags.

## Non-goals

No W56b model/effect/policy or runtime activation; no W57a provider call,
canonical finding, qualified corpus custody, CAP-01 or profile seal; no
real DB/S3 acceptance, beta claim, complete gate or deployment.

## Deliverables

Two scoped cherry-picks, this task/report, focused and architecture checks,
exact-path handoff, dev fast-forward and remote readback.

## Required tests

- W56b read/reference/source tests, W57a replay/request/parser/grounding
  tests, programme governance and relevant architecture tests: pass.
- Exact 11-path diff, frozen API hash, whitespace, clean tree and
  `scripts/task_handoff.py` with explicit check argv: pass.
- Fresh remote dev/main/tag read, fast-forward proof, exact-SHA dev push and
  readback. No intermediate full gate under R-135.

## Integration contract

The W56b service reads checked windows under a caller-owned transaction but
does not journal or authorize a later provider effect; ceilings come from a
future approved policy. W57a replays a supplied response against the draft
request and local grounding inputs, producing only diagnostics, not a
canonical decision. Only this integration task advances `origin/dev`.

## Failure/idempotency/security cases

Stop on moved dev, dirty tree, path expansion or failed check. No force push,
credential, corpus payload or private log enters Git. Repeating the exact
published SHA is a no-op.

## Rollback / feature flag

Unserved code only; correct by a reviewed forward commit. No runtime flag or
data rollback is needed.

## Handoff

- changed files: eleven exact allowed paths;
- contracts: no public product contract changes;
- checks and limits: paired report;
- forbidden hotspots untouched.
