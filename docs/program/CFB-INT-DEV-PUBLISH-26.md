# CFB-INT-DEV-PUBLISH-26 — W57a API/stage seal on dev

The candidate builds on directly read
`origin/dev=3d131d2966e0efeea7b53d9662785f253165a9a4` and cherry-picks
the completed W57a 01B source
`c08182cab78bed70afbc777019d43de6c0bd2e18` as `56efead4`.
The 51-path source patch is byte-for-byte identical: both parent-to-source
and dev25-to-cherry-pick `git diff` streams have SHA-256
`5a2f8ba8b19022c4963134bd047bd6db3540e74bbd9f7e7f76090d7935a17381`.

## Checks and scope

- Integrated `tests/contract/api_v1`, `tests/contract/program`, W57a route
  and stage compatibility tests: **325 passed**. The initial attempt had
  seven JSON Schema setup errors because this isolated worktree lacked the
  ignored `.venv/bootstrap` link; after linking the existing pinned Python
  environment, the same entire selection passed. No product code was fixed
  to conceal the environment error.
- `npm --prefix web run api:verify`: **OK**, 55 operations and API SHA-256
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`.
  `npm --prefix web run typecheck`: **passed** using a read-only link to the
  existing pinned `node_modules` tree; no install or lockfile change.
- Source evidence includes served OpenAPI conformance **1/1**, stage
  compatibility **60/60**, v1 text-stage/provider **81/81**, prose guards
  **33/33** and static citation/route checks **7/7**.
- Direct integration-task governance returned `[]`; `git diff --check`
  passed. The source diff is exactly its 51 granted paths. This integration
  adds only its task, this report and bounded `CURRENT_STATE.md`.

The integrated API is **48 paths / 55 operations / 131 schemas**; stage
registry SHA-256 is
`58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`.
Domain IDs, error catalog and migration 0023 match their frozen 01A hashes;
the error catalogue still has 25 codes and the migration head is
`0023_norm_citations`. The task-owning source deliberately changed API/stage
contracts and generated client; the integration did not edit those bytes.
The source proves its deployment/BFF/composition prose changes do not change
executable directives or route behavior there.

## Limits and publication

The new route is role guarded but returns a typed 503 until a verified
reader proves its stored partition, stage, snapshot and retrieval-set pin.
No qualified set, active CITE stage, report read, corpus publication or v3
runtime acceptance is claimed. PostgreSQL/S3 API integration tests were
deferred while the separate W55b full gate owned the service lane. R-135
defers the complete W56–W63 beta gate. The separate W55b main candidate is
not changed by this development integration.

Publish only the clean exact checked SHA to `origin/dev` as a fast-forward
from the recorded predecessor, then directly read back the remote SHA into
ignored local evidence. This task has no `origin/main` authority. Later W57a
CITE work must supply the verified reader and run the real service tests
before activating the route's answer.
