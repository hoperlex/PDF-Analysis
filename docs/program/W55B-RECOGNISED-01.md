# W55B-RECOGNISED-01 — report (the portal's recognised text)

- Task: `dispatch/W55-PLAN.md` §B3.5 (the text-layer-or-block rule), §B3.6, §B4 Stage B 3 `W55B-RECOGNISED-01`, §B5; `P02_SEAMS.md` §4.1, §4.2, §4.8 (sealed, read only); owner rulings R-116, R-117.
- Branch `agent/w55b`, worktree `.local/worktrees/w55b-exec`, base `19ea1525` (BUDGET report; below it INGEST, STREAM, FIXTURES, SEAL).
- Written by one writer (Claude Opus 5.5 delegate of the wave executor). Nothing is pushed, merged or tagged.
- Lane stack (when up): `FOUNDATION_INSTANCE=auditmanager-w55b-recognised`, PostgreSQL `57450`, S3 `61050/61051`.

## 0. Status (living; updated at every commit)

| Step | State |
| --- | --- |
| living report (this file) | started |
| `analysis/recognised/` (parser, flags, artifact) + container-free tests | pending |
| `extract_document` path form; `source_preparation` (temporary file, text-layer-or-block rule, `prepared.recognised_text`) | pending |
| `runs/executor.py` wiring (outside the grant, pre-authorised) | pending |
| DB/S3 tests on the lane stack | pending |
| precision measurement on the owner's export (counts only, scratch script) | pending |
| mutation proofs | pending |
| light acceptance | pending |
| final report sections 2 to 6, stack teardown | pending |

## 1. Design decisions (made while writing; each is open to the integrator's veto)

Each decision names the alternative rejected.

1. **Manifest roles are the dotted contract roles.** The brief says the manifest spells the two bundle roles with an underscore; the tree says
   otherwise: `documents.models.MANIFEST_ROLE_MARKDOWN` and `MANIFEST_ROLE_STRUCTURED_COMPANION` are read from the stage registry and are
   `source.markdown` and `source.structured_companion`. The underscore spelling (`source_markdown`, `source_structured_companion`) is the
   **blob** role on the object. The executor therefore looks the entries up by the contract role, exactly as it already does for
   `source.document`.

(Further decisions are appended below as they are made.)

## 2. Checks, and how each new test was shown to fail

Pending.

## 3. Contracts

Pending.

## 4. Risks and limitations

Pending.

## 5. Integrator instructions

Pending.

## 6. Containment

Pending.
