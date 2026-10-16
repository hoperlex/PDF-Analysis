# CFB-INT-DEV-PUBLISH-18 — corpus and recorded executor bridges

The candidate builds on exact `origin/dev=b9f1c149f004851de89a2fcc615618068e794bde`.
Three completed source commits were applied without content edits:

- W54 `a49c8649` → `57ef0029`: the read-only corpus preflight now accepts
  separate absolute source and promotion roots. It finds the source sums and
  restored base dump in their actual workspaces and refuses bundle export
  while the embedding build is absent. It neither repairs PDFs nor certifies
  publication readiness.
- W56a `538b3576` → `c1c84adb`: the persisted AR v2 Run can use an explicit
  offline `fixture/<id>` and generation settings through the existing durable
  recorded stage, saved merge and transaction gate. A normal API/worker call
  still has no fixture selection or served v2 composition. V1 remains on its
  earlier route; live/paid mode fails closed.
- W57a `33a4d456` → `459300c4`: a docs-only freeze records the sole-owner
  `0023` citation/custody seal, a 124-path pin inventory and the requirement
  for a certified zero-citation partition. It grants no contract, migration,
  role or runtime edit. W56a code close and W54 qualification remain pending.

A no-content merge `bb5d8564` also joins exact W55b test-repair candidate
`d3acd511c608dbff94d448b95ebb826cf5437c75` as an ancestor of the dev
graph. Dev 17 had already cherry-picked the same three-file test payload;
`git diff bb5d8564^1..bb5d8564` is empty. This retains a fast-forward path
from a separately approved W55b main release to later dev work.

## Checks and limits

The integrated W54 preflight, W56a recorded executor and program-governance
suite passed **79 tests**. W54's source task passed nine focused tests and
read the two real roots; W56a's source task passed 58 container-free checks;
W57a's docs/prose task passed 93 checks and recorded a `pin_sweep` digest
`5412fa5a43a348c22cdaa9b99395d9ad2555d3c22210ffe680f37d1647f3ae47`.
The frozen API/domain/stage hashes and migration head remain those of dev 17.
The complete W56–W63 beta gate is deferred under R-135. W56a's new explicit
executor path still needs a persisted-run PostgreSQL/MinIO acceptance after
the separate W55b gate releases the service lane.

The integration commit changes only this report, its task and the leading
`CURRENT_STATE.md` paragraph plus the minimal correction of its active W56a
description. The three source commits keep their exact path grants. No shared
contract, migration, root dependency/lock, composition root, global style,
provider secret or deployment input changed in the integration commit. The
qualified W54 corpus, paid repair, DB/S3 publication, served W56a switch,
W57 seal, W55b main deployment and beta verdict remain open.

Before publication, reread `origin/dev`, require a clean fast-forward tree and
verify exact changed paths; after push, read back the remote SHA into ignored
local evidence and the final integration result. This task has no
`origin/main` authority.
