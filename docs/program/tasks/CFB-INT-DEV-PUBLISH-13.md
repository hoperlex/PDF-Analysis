# Task CFB-INT-DEV-PUBLISH-13 — publish the next checked code-first candidate

task_id: CFB-INT-DEV-PUBLISH-13

## Outcome

One clean fast-forward `origin/dev` candidate contains the completed W56a,
W57a, W58 and W59 preparations and repairs the program task-governance
failure. The exact published SHA is read back; no runtime or deployment
acceptance is inferred from this code-first publication.

## Depends on

- `CFB-INT-DEV-PUBLISH-12` — completed prior dev publication at `8f113f6b`;
- `W56A-INT-RECORDED-CALL-FACTS-01` — completed recorded call facts;
- `W56A-INT-RECORDED-STAGE-RESULT-01` — completed bounded StageResult seal;
- `W57A-INT-QUALIFICATION-READ-01` — completed stored build facts;
- `W57A-INT-QUALIFICATION-DECISION-PREP-01` — completed digest comparison;
- `W58-INT-TARGET-BLOB-READBACK-PREP-01` — completed target payload readback;
- `W59-INT-RAW-EVIDENCE-SEAL-PREP-01` — completed immutable raw seal;
- `W59-INT-FINDING-MATCH-SUGGESTIONS-01` — completed exact suggestions;
- `PROGRAM-GOVERNANCE-REPAIR-01` — completed historical task correction.

## Frozen inputs

- code base: `b882dda9a3134b32ee927dcb4e657fc81f1cd83e`;
- remote `dev`: `8f113f6b8987f2fb702872435f61999e143bdc50` at preparation read;
- remote `main`: `23fd729dbb06c642be0588017f6b195305e2e53e` at preparation read;
- code-first plan SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
- W58–W63 scope SHA-256 `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- migration head `0022_findings_v2`; W55b main candidate remains `6d63802a`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: eight completed local source/correction commits are ahead of the
  exact dev predecessor, and the focused suite is green while the full beta
  gate remains deferred under R-135.

### P-01 — current remote predecessor

- captured_at: 2026-10-16
- command: `git ls-remote origin refs/heads/dev refs/heads/main`
- captured_output:
  ```text
  8f113f6b8987f2fb702872435f61999e143bdc50 refs/heads/dev
  23fd729dbb06c642be0588017f6b195305e2e53e refs/heads/main
  ```
- interpretation: the new dev tip must descend from this exact predecessor;
  reread the remote ref and refuse a moved branch before publication.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/CURRENT_STATE.md` — one leading paragraph;
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-13.md`;
- `docs/program/CFB-INT-DEV-PUBLISH-13.md`;
- exact fast-forward update of `origin/dev` after checks.

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, application/runtime/test source in this integration commit,
corpus bytes, production DB/S3, `origin/main`, tags and deployment workflow.

## Non-goals

No W55b main deployment, W54 restore, live model call, active AR v2, verified
retrieval set, approved version comparison, W58 drill, full beta gate or beta
verdict. The eight source commits are preparations, not runtime activation.

## Deliverables

The leading state entry, this task, an integration report and exact pushed
`origin/dev` SHA read-back.

## Required tests

- combined focused W56a/W57a/W58/W59 and program-governance tests;
- direct task governance, frozen SHA values, exact staged paths and whitespace;
- clean tree, fresh remote ref, fast-forward proof and exact push read-back;
- complete `make gate` deferred by R-135; the separate W55b release candidate
  owns its complete gate at its own SHA.

## Integration contract

Only this integration task publishes the exact checked candidate to
`origin/dev`. A moved remote ref or dirty candidate stops the push. The code
remains unactivated. The W55b candidate for `origin/main` is a different tree
and requires its own exact-SHA instruction, complete gate and deployment task.

## Failure/idempotency/security cases

Do not include the untracked W55b main-preparation documents or local
promotion/secret artefacts. Never force-push. A retry reads the remote SHA and
does nothing if it already equals this candidate. No secrets enter Git.

## Rollback / feature flag

No runtime behavior is switched on. Corrections use a reviewed forward
commit; no history rewrite, force push or data rollback.

## Handoff

- changed files: exactly the three documentation paths above;
- contracts: none;
- next: continue W56–W63 code-first slices and W54 restore verification;
- forbidden hotspots stay untouched in this integration commit.
