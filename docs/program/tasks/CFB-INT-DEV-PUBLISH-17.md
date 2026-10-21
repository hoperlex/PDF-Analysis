# Task CFB-INT-DEV-PUBLISH-17 — integrate recorded publication gate

task_id: CFB-INT-DEV-PUBLISH-17

## Outcome

One clean fast-forward `origin/dev` candidate includes the completed, unactivated
W56a durable publication gate and the W55b serving-carrier test deadline repair.
The live state entry is brought back within its
120-line contract, with its prior full text archived verbatim. The exact remote
SHA is read back. No runtime activation or deployment follows.

## Depends on

- `CFB-INT-DEV-PUBLISH-16` — completed at `da6dff620140d1c74b5cead1f4c4c7e222d822d7`;
- `W56A-INT-RECORDED-PUBLICATION-GATE-01` — completed at `ca3727487605932b43b7458ee564276aae06f017`.
- `W55B-INT-GATE-TIMEOUT-01` — completed at `d3acd511c608dbff94d448b95ebb826cf5437c75`.

## Frozen inputs

- integration base and `origin/dev` at preparation read: `da6dff620140d1c74b5cead1f4c4c7e222d822d7`;
- `origin/main` at preparation read: `23fd729dbb06c642be0588017f6b195305e2e53e`;
- W56a gate source commits: `4abc555e`, `30000ad6`, `ca372748`, cherry-picked without content edits;
- W55b test repair source commit: `d3acd511`, cherry-picked without content edits;
- pre-compaction state tree: `71373417`; the archive copies its 320-line `CURRENT_STATE.md` byte-for-byte;
- migration head `0022_findings_v2`; API/domain/stage contracts unchanged from dev 16;
- W54 repair model `claude-opus-5`, proxy credential file absent;
- old W55b candidate `6d63802ab465a0317839c9b57abd5e90f3d91769` has no `GATE OK` after three attempts; repaired `d3acd511` needs its own full gate.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W56a gate and W55b test repair are completed locally but absent from `origin/dev`; the
  320-line live state violates `CurrentStateTest`'s 120-line bound.

### P-01 — exact remote predecessor

- captured_at: 2026-10-16
- command: `git ls-remote origin refs/heads/dev refs/heads/main`
- captured_output:
  ```text
  da6dff620140d1c74b5cead1f4c4c7e222d822d7 refs/heads/dev
  23fd729dbb06c642be0588017f6b195305e2e53e refs/heads/main
  ```
- interpretation: reread both refs before publication; a moved dev predecessor
  stops this integration.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/CURRENT_STATE.md`;
- `docs/program/history/CURRENT_STATE_2026-10-16_71373417.md`;
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-17.md`;
- `docs/program/CFB-INT-DEV-PUBLISH-17.md`;
- exact fast-forward update of `origin/dev` after checks.

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, new application/runtime/test source in the integration commit,
production DB/S3, proxy credential, `origin/main`, tags and deployment workflow.
The W56a and W55b source commits retain their own exact path grants.

## Non-goals

No W55b `origin/main` deployment, W54 paid repair or corpus DB/S3 import,
W56a executor activation, W57 seal, W58 stand transfer, W59 section migration,
complete beta gate or beta verdict.

## Deliverables

The W56a and W55b source commits, a verbatim current-state archive, a short live state,
this task, an integration report and an exact pushed `origin/dev` SHA read-back.

## Required tests

- focused W56a saved-plan/publication tests, W55b test collection and program governance;
- `CurrentStateTest`, exact archive comparison, frozen contract/migration
  read-back, exact changed-path proof, whitespace and clean tree;
- fresh remote refs and fast-forward proof before publication;
- complete beta `make gate` deferred under R-135.

## Integration contract

Only this integration task publishes the exact checked candidate to
`origin/dev`. It preserves the W56a and W55b source payloads, archives the previous
state exactly, records the gate as unactivated, then publishes from a clean
tree after rereading the remote. The W55b failed-gate report is evidence only;
this task grants no `origin/main` authority.

## Failure/idempotency/security cases

No ignored logs, credentials, corpus bytes or Docker data enter Git. Never
force-push. If remote dev moved, stop and reintegrate. An already equal remote
is a no-op. The W56a gate requires one caller-owned commit or a whole rollback;
its green focused checks do not authorize activation.

## Rollback / feature flag

The gate is not active. Corrections use reviewed forward commits; no history
rewrite or deployment rollback is needed.

## Handoff

- changed integration files: exactly the four documentation paths above;
- contracts: none;
- next: W56a executor activation, W57 serial seals, W58 recovery, W59 section
  seal after its prerequisites, and W54 credential-gated repair;
- forbidden hotspots remain untouched by this integration commit.
