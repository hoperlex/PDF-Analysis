# Task W52-INT-RELNOTES-GATE-ENV-01 — use governance validator in prose test

task_id: W52-INT-RELNOTES-GATE-ENV-01

## Outcome

The release-notes form test runs under the repository's runtime Python
while validating the sealed JSON Schema through the pinned governance
interpreter, so it remains executable in the canonical gate environment.

## Depends on

- `W52-INT-C2-RELNOTES-01`, published at `a6ff1ff`.
- `W52-INT-C2-ACCEPT-01`, published at `a183dbf`.

## Frozen inputs

- Exact development base
  `a183dbf970aad4715a9cfad7010b024fd9d304ac`.
- `release-notes/schema.json` sealed; `requirements/validation.lock`
  pins governance `jsonschema`; runtime `uv.lock` has no such package.
- `VERSION=0.3.0`, API 30/37/83, 23 errors, domain revision 9 /
  29 identities, migration `0016_release_notes`, contract version
  `1.0.0-draft.1`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: the existing 19 named bad-form fixtures and two
  authored entries remain unchanged

## Captured premise evidence

- premise: the W52 RELNOTES suite directly imports `jsonschema`, but
  the runtime gate interpreter does not install it.

### P-01 — exact collection failure

- captured_at: 2026-10-08
- command: `/root/projects/PDF-Analysis/.venv/bin/python -m pytest -q
  tests/contract/release_notes/test_release_notes_form.py`
- captured_output:
  ```text
  ERROR collecting tests/contract/release_notes/test_release_notes_form.py
  tests/contract/release_notes/test_release_notes_form.py:12: in <module>
      import jsonschema
  E   ModuleNotFoundError: No module named 'jsonschema'
  ```
- interpretation: route only sealed-shape validation through the
  governance interpreter, as `tests/contract/api_v1/conftest.py` does.
  Keep all prose rules and their bad fixtures in runtime pytest.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `tests/contract/release_notes/test_release_notes_form.py`: replace
  the direct `jsonschema` import and calls with a strict subprocess to
  `.venv/bootstrap/bin/python` for the two sealed-shape assertions only.
- `docs/program/tasks/W52-INT-RELNOTES-GATE-ENV-01.md` and
  `docs/program/W52-INT-RELNOTES-GATE-ENV-01.md`: task/report.
- Ignored local environment for the pinned governance interpreter;
  local integration branch and later fast-forward `origin/dev` only.

## Forbidden hotspots

All other paths, including `release-notes/**`, sealed schema,
contracts, root dependency/lock files, bootstrap validator, API
runtime, generated client, composition root, global styles,
`origin/main`, tags and deployment.

## Non-goals

No new prose rule, release-note edit, loader change, independent judge,
full gate, QA, live acceptance or release publication.

## Deliverables

Same form-rule coverage under runtime Python, sealed-shape checks under
the pinned governance interpreter, six-part report and exact path audit.

## Required checks

- Runtime interpreter runs `tests/contract/release_notes` with pinned
  governance interpreter available; all named bad fixtures still pass.
- Explicit missing-governance-interpreter refusal; `git diff --check`
  and exact path audit. Full gate remains D-140.

## Integration contract

The correction is a test-environment bridge only. Commit it before
the W52 development-close report; the close checks must run on the
combined candidate. No root dependency or lockfile change is allowed.

## Failure / idempotency / security

An absent governance interpreter fails loudly rather than skipping the
schema check. The subprocess receives only authored JSON, no credential.

## Rollback / feature flag

Revert a dev-only mistake by a reviewed forward commit. No runtime flag.

## Handoff

Return changed files, checks, contracts, risks, next step and hotspot
proof. No checkpoint or tag.
