# Task W54-BUNDLE-EXPORT-01 — export and verify the promotion bundle of the repaired snapshot

task_id: W54-BUNDLE-EXPORT-01

## Outcome

The repaired snapshot, its complete embedding build, its custody slots and every source PDF
and crop are written once as a content-addressed bundle under
`/root/projects/PDF-Analysis/.local/norms/bundles/`, and `bundle verify` re-hashes every file
of it and accepts it. This is W54 step 4. The bundle is the input of the separate stand
import (`W55-PLAN.md` §A7); nothing is imported or deployed here.

## Depends on

- `W54-EMBED-BUILD-01` — completed embedding build and its verified dump;
- `W54-SNAPSHOT-LOAD-01` and `W54-SESSION-REPAIR-01` — the repaired snapshot and ledger.

## Frozen inputs

- code base: `origin/dev` `f942ca1ce0dff227c85b74a90e6de2faa989046e`; no source file is changed;
- snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74`, `characters-v2:1200`, row digest
  `a3111764c9fb01796444880a979fa50530948f93d9fedde194cecb3c873ff7ac`, embedding-set digest
  `e7fac64c90b96381ceeb41d2707c222d1ba81240ff8b4eff47fecb3293ffc5df`;
- source drop `/root/projects/PDF-Analysis/.local/norms/corpus`, sums
  `/root/projects/PDF-Analysis/.local/norms/corpus-sums/2026-10-15/SHA256SUMS`
  (SHA-256 `eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`);
- ledger `/root/projects/PDF-Analysis/.local/norms/repairs/session-20261019/ledger.json`
  (SHA-256 `9639ce91c1605db8c2b0e9bfe5ae0f1ee858a76481f2308aed1f087efcd3c833`);
- the promotion database in the state of the verified dump
  `promotion-20261019T195011Z.dump` (SHA-256 `59548d129cdc89faf4367d6ec3f8d1eaed85d38ea56534af9ccda80d72d7c865`).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: after the export the bundles directory holds exactly one entry, the bundle of this
  task, so no other bundle of this content key exists beside it.

### P-01 — the bundles directory after the export

- captured_at: 2026-10-20
- command: `ls /root/projects/PDF-Analysis/.local/norms/bundles`
- captured_output:
  ```text
  2026-07-23..2026-08-20+17d+121r.0a1bafe103ff+7792e307e39b2c1c92a852d64033b9840b48b118160768e3f02e925428815245
  ```
- interpretation: one entry, named `<content_key>+<bundle_digest>` as the report records; the
  `incomplete-*` staging directory `export` writes into was renamed on success and is gone.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W54-BUNDLE-EXPORT-01.md`;
- `docs/program/W54-BUNDLE-EXPORT-01.md`;
- the promotion database (read only) and its container (started and stopped);
- ignored `/root/projects/PDF-Analysis/.local/norms/bundles/**` (hardlinks into the drop,
  not copies) and `/root/projects/PDF-Analysis/.local/norms/promotion-records/20261019/**`.

## Forbidden hotspots

`contracts/**`, migration files, root dependencies/locks, composition root, global styles,
the bundle, loader and embedder code, source corpus and sums bytes (the objects are
hardlinks: nothing writes through them), the ledger, the production stand, S3,
`CURRENT_STATE.md`, remote `origin/main` and tags.

## Non-goals

No stand import, no copy to the stand, no `report`, no deployment, no compatibility check
against the deployed migration head, no full gate. `--copy-objects` and `--without-build`
are not used.

## Deliverables

- the bundle directory and its `manifest.json` with a `build` block;
- `bundle verify` accepting it, with the file count;
- the bundle's name, manifest and `SHA256SUMS` hashes, counts and `db_growth_bytes`;
- the promotion database stopped;
- the result report.

## Required checks

- `bundle export` exits 0 and prints the row digest and build digest recorded above;
- `bundle verify` exits 0 (`every byte re-hashed`);
- no regular file under `objects/` has a link count of 1 (all are hardlinks into the drop);
- `git diff --check` and direct task `governance_findings` = `[]`.

## Integration contract

The bundle name is `<content_key>+<bundle_digest>`. It is the input of
`W55-PLAN.md` §A7 (copy, attest, import) and of nothing else in this task. The owner names
the bundle key and digest directly for that operation.

## Failure/idempotency/security cases

`export` writes into an `incomplete-*` directory and names it only after success, so a failed
export leaves no bundle. `verify` refuses any changed, missing or extra file. The drop is read
and hard-linked, never written. No credential is printed.

## Rollback / feature flag

Delete the bundle directory (the objects are hardlinks, so the drop is unaffected) and revert
the two documentation files. No runtime, contract or deployed change.

## Handoff

- changed files: the allowed paths above;
- contracts: none;
- next: the stand import under `W55-PLAN.md` §A7, a separate production operation that needs
  the owner's window and the deployed-SHA and migration-compatibility evidence;
- forbidden hotspots remain untouched.
