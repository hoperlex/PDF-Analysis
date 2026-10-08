# Task W52-ACCEPT-01 — measure candidate build in alpha acceptance

task_id: W52-ACCEPT-01

## Outcome

The public-alpha acceptance pack reads `getProductVersion` with the
reviewer's credential, independently computes the candidate API
`build_id` from the exact candidate tree, and fails if the served or
attested build differs. Its evidence records a measured build value.

## Depends on

- `W52-INT-C-TRANSLATE-01`, published on `origin/dev`.
- `W52-INT-C2-GRANT-01`, published on `origin/dev`.

## Frozen inputs

- Start from the exact `origin/dev` SHA read back by
  `W52-INT-C2-GRANT-01`; record it in the lane report.
- API `GET /system/version` is sealed at 30 paths / 37 operations /
  83 schemas; `VERSION=0.3.0`; 23 error codes; domain revision 9 /
  29 identities; head `0016_release_notes`;
  `contract_version=1.0.0-draft.1`.
- `dispatch/W52-PLAN.md` §§3.1, 3.4, Stage C2 and §5; translated
  `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md` from Stage C.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: existing 27-route journey and six refusal sets retain
  their members; the measured-build check adds a verdict condition only

## Captured premise evidence

- premise: the current acceptance pack records candidate and attested
  deployed SHA but has no measured API build-ID parity.

### P-01 — current acceptance-pack files

- captured_at: 2026-10-08
- command: `rg --files scripts tests/e2e/pc01/journey tests/contract docs/manual-tests docs/program | rg '(manual-alpha-check\\.sh|verify-acceptance\\.mjs|test_alpha_acceptance_command\\.py|ALPHA_PUBLIC_ACCEPTANCE\\.md|ALPHA-MANUAL-01\\.md|W52-ACCEPT)' | sort`
- captured_output:
  ```text
  docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md
  docs/program/ALPHA-MANUAL-01.md
  docs/program/tasks/ALPHA-MANUAL-01.md
  scripts/manual-alpha-check.sh
  tests/contract/test_alpha_acceptance_command.py
  tests/e2e/pc01/journey/verify-acceptance.mjs
  ```
- interpretation: the existing shell entry, Node verdict and
  contract test are the owned change surface. The historical
  ALPHA-MANUAL record is not rewritten.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/ALPHA-MANUAL-01.md`
- addendum_path: `docs/program/W52-ACCEPT-01.md`

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `scripts/manual-alpha-check.sh` — candidate hash, served version
  probe and safe evidence, without changing existing release modes.
- `tests/e2e/pc01/journey/verify-acceptance.mjs` — independent
  build parity and verdict check.
- `tests/contract/test_alpha_acceptance_command.py` — adversarial
  mismatch, missing response and secret-redaction coverage.
- `Makefile` — `alpha-acceptance` target only.
- `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md` — new English
  operator sentences only; existing A01–A20 IDs, paths, commands,
  figures and Russian UI quotations remain.
- `docs/program/ALPHA-MANUAL-01.md` — a forward pointer/addendum
  only, no historical evidence rewrite.
- `docs/program/W52-ACCEPT-01.md` — six-part report and addendum.
- Local `agent/w52-accept-01` branch/worktree and ignored environment.

## Forbidden hotspots

Every other path, including `contracts/**`, migrations, API server,
release loader, generated client, root dependency/lock, composition
root, global styles, journey route manifest, `origin/dev`,
`origin/main`, tags and deployment. Any new test path requires an
integrator grant correction before editing.

## Non-goals

No new API operation, release-note prose, product UI, automated live
acceptance run, independent QA, full gate, tag or publication.

## Deliverables

- The acceptance command measures the candidate API build from the
  checkout by its own §3.1 implementation, deriving the input roots
  from `Dockerfile.api` `COPY` lines at run time as
  `verify-deployed.sh` does.
- With the reviewer credential, it reads served `getProductVersion`,
  compares product version, candidate SHA, attested deployed SHA and
  measured build, and records a safe, machine-readable verdict.
- The shell and Node implementations agree on the same candidate tree;
  a mismatch fails rather than passing or guessing.

## Required checks

- `shellcheck scripts/manual-alpha-check.sh`; `bash -n` for the
  same file; `node --check tests/e2e/pc01/journey/verify-acceptance.mjs`.
- `.venv/bin/python -m pytest -q
  tests/contract/test_alpha_acceptance_command.py`, including a
  clean-checkout passing case and deliberate build mismatch refusal.
- Independent tree-hash parity, `git diff --check`, exact path audit.
  Report any unrun check. Full gate and live stand remain D-139/D-140.

## Integration contract

Consume the sealed version response and the existing journey session;
never echo the reviewer credential, cookie or Authorization header.
The acceptance verdict may pass only if the served build equals the
independently measured candidate build. Merge after RELNOTES so the
English runbook and release text are final for Stage C2.

## Failure / idempotency / security

Missing authentication, malformed version response, missing Dockerfile
roots, hash mismatch or unavailable service is a typed failure or
blocked result, never silent success. Rerunning the pack in a new
evidence directory does not mutate release metadata.

## Rollback / feature flag

Revert the dev-only candidate with a reviewed commit if needed. A failed
measurement prevents acceptance; no runtime feature flag is added.

## Handoff

Return changed files, checks/results, contracts, risks, integrator
steps and forbidden-hotspot proof. No checkpoint or tag.
