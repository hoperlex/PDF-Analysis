# W52-INT-RELNOTES-GATE-ENV-01 — release-note form test environment corrected

**Base:** published Stage-C2 development SHA
`a183dbf970aad4715a9cfad7010b024fd9d304ac`.
The correction follows the locally committed `W52-INT-CLOSE` grant and
will be included in its combined development candidate. No deployment
or release action is implied.

## 1. Files and result

The release-note form test no longer imports `jsonschema` in runtime
pytest. Only its sealed-shape assertions invoke Draft 2020-12 validation
through `.venv/bootstrap/bin/python`, the repository's pinned governance
interpreter. All prose rules, bad fixtures, authored entries and loader
behavior remain unchanged.

Changed paths:

```text
docs/program/tasks/W52-INT-RELNOTES-GATE-ENV-01.md
tests/contract/release_notes/test_release_notes_form.py
docs/program/W52-INT-RELNOTES-GATE-ENV-01.md
```

## 2. Checks

- The root runtime interpreter initially failed during collection with
  `ModuleNotFoundError: jsonschema`; that is the captured P-01 defect,
  not a passing test.
- With the pinned governance interpreter available at the project path,
  the same root runtime interpreter passed **23 release-note form tests**.
  The added case proves an absent governance interpreter raises
  `FileNotFoundError` rather than silently skipping shape validation.
- `git diff --check` and three-path audit passed. Combined close checks
  follow under `W52-INT-CLOSE`; full gate remains D-140.

## 3. Contracts

No schema, authored note, API/domain contract, migration, loader,
dependency/lock or `contract_version` changed. The schema validator
is the same pinned package already used by the repository's API
contract suite.

## 4. Risks and limits

The governance interpreter is required for this test. A checkout that
has not provisioned `.venv/bootstrap` fails loudly; canonical gate
setup is responsible for provisioning it. This correction adds no
new runtime dependency or deployment behavior.

## 5. Integrator instruction

Keep this narrow correction on the W52 development-close candidate,
rerun release-note, loader and acceptance checks with the standard
runtime/governance environments, then publish only the clean checked
SHA to `origin/dev`. D-137–D-140 remain open.

## 6. Forbidden-hotspot proof

The three paths in §1 are exactly the integration grant. No
`release-notes/**`, `contracts/**`, migration, root dependency/lock,
bootstrap validator, API runtime, generated client, composition root,
global style, `origin/main`, tag or deployed service was changed.
