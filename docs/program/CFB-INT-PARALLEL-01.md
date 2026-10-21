# CFB-INT-PARALLEL-01 — development integration record

## Integrated result

Five independent code-first preparations were reviewed together on base
`960da9e1b7cfc5eda75fc3a1d52714bb66be8176`:

1. W56a appends and projects expert decided severity; optional severity on a
   legacy observation is refused before a command claim.
2. W56a CSV keeps the first seventeen OD-11 columns and appends `severity`
   and `severity_proposed`, reading canonical evidence when an identity exists.
3. W57a emits deterministic retrieval set and catalogue bytes with digests.
4. W57b parses references and resolves five outcomes against a pinned
   caller-supplied catalogue, retaining unread pages and raw spans.
5. W57b emits deterministic two-sheet XLSX bytes from typed finding rows.

## Verification

- Combined pure/recorded focused checks: **38 passed, 1 DB test deselected**.
- Four independent no-DB CSV column/serializer pins: passed.
- Python compilation: passed for changed modules/tests.
- Direct governance on all six new task files: `[]`; whitespace check: passed.
- Frozen API, error, analysis and provider-lock digests and migration head
  match the task's inputs. No forbidden hotspot changed.
- DB severity and CSV integration tests could not run because `DATABASE_URL`
  is absent. The existing contract composition tests could not run because
  `.venv/bootstrap/bin/python` is absent from this worktree. The `soffice`
  conversion probe exited with code 1 before producing an ODS; ZIP/XML tests
  passed, but application opening is unconfirmed. Full `make gate` is
  deferred under R-135.

## Contracts, risks and next integration work

No frozen contract, migration, provider lock, composition root, root
dependency/lock file or global style changed. The work contains pure
preparations plus the already sealed W56a optional severity projection;
there is no v2/v3 runtime switch, corpus promotion, verified retrieval set,
W57b stage or `exportRunXlsx` API. `origin/main` remains unchanged.

Before activation, run the deferred DB tests on isolated migrated PostgreSQL,
prove the XLSX in LibreOffice, publish a qualified corpus snapshot and
owner-reviewed W57a map/set with custody, and complete the separate W57b
contract/migration/route seal. A final beta candidate still requires the
code-first B1–B12 coverage matrix and full gate on one exact clean SHA.

## Ownership proof

The staged path list for this integration must be a subset of
`tasks/CFB-INT-PARALLEL-01.md`'s explicit `Allowed paths`. The five local
task reports enumerate each slice's own files and checks. No checkpoint,
release tag, stand operation or `origin/main` publication is part of this
record.
