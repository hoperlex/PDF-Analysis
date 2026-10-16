# Task CFB-INT-DEV-PUBLISH-18 — integrate corpus and recorded executor bridges

task_id: CFB-INT-DEV-PUBLISH-18

## Outcome

One clean fast-forward `origin/dev` candidate carries the completed W54
split-root corpus preflight, the explicit offline-only W56a recorded executor
bridge and a W57a docs-only citation/custody freeze. The W55b repaired test
commit is joined as an exact ancestor with no additional content change, so a
future W55b main release remains in the dev history. The source task payloads
are unchanged, focused checks pass,
and the exact remote SHA is read back. No served v2 activation, corpus
publication, deployment or beta claim follows.

## Depends on

- `CFB-INT-DEV-PUBLISH-17` — completed at `b9f1c149f004851de89a2fcc615618068e794bde`;
- `W54-CORPUS-SPLIT-ROOT-PREFLIGHT-01` — completed at `a49c86492626e6414d5d89033b3e75f2132fdab5`;
- `W56A-INT-RECORDED-ACTIVATION-01` — completed at `538b3576604982c38236c53a57929341eb4d7a36`.
- `W57A-INT-RULE-FREEZE-01` — completed at `33a4d45647adea7e4f94f2fa0b94f75737eb89b5`.

## Frozen inputs

- integration base and `origin/dev` at preparation read: `b9f1c149f004851de89a2fcc615618068e794bde`;
- `origin/main` at preparation read: `23fd729dbb06c642be0588017f6b195305e2e53e`;
- source commits: `a49c86492626e6414d5d89033b3e75f2132fdab5`, `538b3576604982c38236c53a57929341eb4d7a36` and `33a4d45647adea7e4f94f2fa0b94f75737eb89b5`;
- W57a `pin_sweep` stdout SHA-256 `5412fa5a43a348c22cdaa9b99395d9ad2555d3c22210ffe680f37d1647f3ae47`;
- migration head `0022_findings_v2`; API/domain/stage contract SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`, `c017864a3e18e2efb9589949547d5ad96475831686c63067a70273d3f4113b50`, `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315b2c1239453ba3a`;
- W54 source and promotion roots are separate; paid repair proxy credential is absent;
- W55b repaired main candidate is `d3acd511c608dbff94d448b95ebb826cf5437c75`, under its own full gate.
- the W55b test content was already cherry-picked into dev 17 as `28bec0c1`; the ancestry join may not alter its files.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: all three source commits are completed on isolated branches from the
  published dev 17 predecessor; the source and promotion roots are different.

### P-01 — exact remote predecessor

- captured_at: 2026-10-16
- command: `git ls-remote origin refs/heads/dev refs/heads/main`
- captured_output:
  ```text
  b9f1c149f004851de89a2fcc615618068e794bde refs/heads/dev
  23fd729dbb06c642be0588017f6b195305e2e53e refs/heads/main
  ```
- interpretation: reread both refs before publication; a moved dev ref stops
  this integration.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/CURRENT_STATE.md` — a concise new leading state paragraph and current W56a boundary correction;
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-18.md`;
- `docs/program/CFB-INT-DEV-PUBLISH-18.md`;
- a content-identical merge of exact `d3acd511c608dbff94d448b95ebb826cf5437c75` into the development graph;
- exact fast-forward update of `origin/dev` after checks.

## Forbidden hotspots

`contracts/**`, migrations, root dependency/lock files, composition root,
global styles, new application/runtime/test source in the integration commit,
production DB/S3, proxy credential, `origin/main`, tags and deployment
workflow. The source commits retain their own exact path grants.

## Non-goals

No paid W54 repair, embedding build, qualified bundle or DB/S3 import; no
served W56a profile, fixture selection, live model or provider call; no W57
contract/migration seal, W58 stand recovery, W59 section seal, main deployment
or beta verdict.

## Deliverables

The three source commits, a short live-state update, this task, an integration
report and exact pushed `origin/dev` SHA read-back.

## Required tests

- focused W54 split-root preflight and W56a recorded executor bridge suites,
  plus W57a docs/governance and pin-sweep evidence;
- program governance, frozen contracts/migration, exact changed paths,
  whitespace, clean tree and `d3acd511` ancestor proof;
- fresh remote refs and fast-forward proof before publication;
- complete beta `make gate` deferred under R-135; the separate W55b full
  gate cannot be borrowed as W56 acceptance.

## Integration contract

Only this integration task may publish its exact checked SHA to `origin/dev`.
It cherry-picks the three completed source commits without changing their
payloads, joins the already integrated W55b test commit as a no-content merge,
and records that all new W54/W56/W57 slices remain preparation. A served W56a switch needs
a later sole-owner composition/config grant and model-pin decision. W54
preflight is metadata-only and cannot authorize corpus import. W57a's freeze
is docs-only and grants no migration/contract write itself.

## Failure/idempotency/security cases

Do not include ignored logs, corpus bytes, credentials or Docker data in Git.
Never force-push. Retry reads the remote and does nothing if already equal.
A moved dev ref or dirty tree stops publication. No external W54 operation or
W55b main deployment is inferred from focused tests.

## Rollback / feature flag

No served behavior is activated. Corrections use reviewed forward commits;
no history rewrite, deployment rollback or feature flag is needed.

## Handoff

- integration commit changes only its report, task and the named live-state edits;
- contracts: none;
- next: W54 credential-gated repair/build, W56a real persisted-run acceptance
  and composition slot, serial W57 seals, W58 recovery and W59 section seal;
- forbidden hotspots remain untouched by this integration commit.
