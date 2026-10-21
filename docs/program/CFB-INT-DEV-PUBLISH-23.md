# CFB-INT-DEV-PUBLISH-23 — W57A storage and custody seal

The candidate builds on directly read
`origin/dev=c3527fd969c4512441971d9a1f6e2c68a52b9a13`.
Completed W57A source `c71048f788e5d0bee39a312217dfd4c0912e5bc1`
was cherry-picked as `09e4e4dc` without payload edits. It adds the sole
`0023_norm_citations` migration, domain candidate revision 14, identity and
custody mirrors, focused real-PostgreSQL tests and its exact task/report.

## Checked behavior

The migration defines `nrs_` retrieval-set identity. A verified set needs
matching expected/observed digests, a nonempty complete chunk/vector build
and confirmed R-76 bindings for both set and catalogue Blobs. The Run pin is
immutable. A non-NULL observation citation count is a certified 0..5
partition checked at commit against immutable citation rows; NULL remains
legacy/unsealed. This schema supports a future CITE publisher and reader; it
does not activate either or qualify a real corpus.

The source lane passed **49 focused tests on real PostgreSQL**, including a
populated 0022→0023 upgrade, and **176 contract/offline tests**. Its
containers were stopped. The unchanged integrated source passed **204
container-free tests** across domain/custody and programme suites. Direct
governance for this integration task returned `[]`; source path and whitespace
checks passed. Migration head is `0023_norm_citations`. The API remains 47
paths / 54 operations / 124 schemas and the error catalogue remains 25 codes.
OpenAPI and analysis-stage SHA-256 remain
`fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`
and `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315b2c1239453ba3a`;
the P02 model lock and old 0022 migration bytes remain unchanged.

The source report records one predecessor limitation: an empty downgrade
through published 0022 toward 0021 fails when its `CREATE OR REPLACE VIEW`
tries to remove `decided_severity`. No old migration was changed. The 0023
populated downgrade refuses before data loss. W57A 01B owns the serial
API/stage/reader reseal, and later code must refuse absent or mismatched
certification instead of treating an empty query as certified zero.

## Scope and publication

The source cherry-pick changes exactly its 31 task-granted paths. This
integration commit changes only this report, its task and bounded
`CURRENT_STATE.md` edits. No old migration, API contract, generated client,
stage registry, composition root, root dependency or lock, global style,
production DB/S3, `origin/main`, tag or deployment input was changed.

Publish only the clean exact checked SHA to `origin/dev` as a fast-forward
from the recorded predecessor and directly read back the remote SHA into
ignored local evidence. This task has no `origin/main` authority. R-135
defers the complete W56–W63 beta gate; the separate W55b main candidate is
waiting for a resource window for its own complete gate.
