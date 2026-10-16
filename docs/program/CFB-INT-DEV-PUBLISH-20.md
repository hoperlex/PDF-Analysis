# CFB-INT-DEV-PUBLISH-20 — pinned W54 repair-sample preflight

The candidate builds on directly read `origin/dev=de3d81085f30301ddc2965f7f4bf927ea738c8b3`.
Completed W54 source `30839f09542feea98dadab26fddb057e1877fea7`
was cherry-picked as `0635d273` without a payload edit. Its four granted
paths add a metadata-only `repair-sample` choice to `corpus_preflight.py`,
focused tests, a task and a source report.

The check binds the frozen source-sums digest, base-dump sidecar and restore
marker to the exact zero-call plan for 121 `claude-opus-5` page repairs. It
refuses malformed or escaping paths, changed plan identity and less than
6 GiB available disk or RAM. It does not rehash PDF/dump bytes, call a model,
create embeddings or certify a DB/S3 bundle. The source task's real
read-only run matched the metadata and refused only `memory_floor`:
4,696,215,552 bytes available versus 6,442,450,944 required. The missing
proxy credential remains a separate hard stop for paid repair.

## Checks and scope

- The integrated `test_corpus_preflight.py` suite passed **12 tests**;
  `tests/contract/program` passed **28 tests**, and the new task's direct
  `governance_findings` result was `[]`.
- The source task also proved Python compilation, CLI help, exact four-path
  containment and whitespace checks; the integration reread the frozen
  API/domain/error/stage digests and migration head `0022_findings_v2`.
- The candidate keeps `VERSION=0.6.0`, API 47 paths / 54 operations /
  124 schemas and 25 error codes. W55b's separate full gate does not
  qualify this W54 development slice; R-135 defers the beta gate.

The integration commit changes only this report, its task and the leading
`CURRENT_STATE.md` paragraph plus the predecessor pointer. The source
cherry-pick changes only its four task-granted paths. No shared contract,
migration, root dependency/lock, composition root, global style, corpus
source/dump, credential, stand DB/S3, `origin/main`, tag or deployment input
was changed.

## Publication and next step

Publish only the clean exact checked SHA to `origin/dev` after a fresh remote
read and fast-forward proof, then read it back into ignored local evidence.
No `origin/main` authority is granted. Once a private proxy credential and
resource window exist, the W54 operator must still fully reverify the source
and dump evidence, run the bounded sample under the durable journal, inspect
the result, complete repair and embeddings, then qualify a corpus bundle for
DB/S3. This preflight is neither approval for a paid call nor publication.
