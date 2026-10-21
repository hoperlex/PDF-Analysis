# CFB-INT-DEV-PUBLISH-25 — W58 isolated restore drill code on dev

The candidate builds on directly read
`origin/dev=7d522a598c173bb4090c8f9f3e1e548c6c89a738` and cherry-picks
the completed W58 source commit
`81208e721b296692fde005a95f6383e7a04ab609` as `6a258fce`. Its six
source paths are unchanged. The new offline coordinator preflights a private
copy, checks restored PostgreSQL fingerprints and Blob references, then
copies and reads back an isolated object target. The operator still has to
supply and prove the isolated restore and storage lane.

## Checks and scope

- Source: **33 focused** and **140 recovery/governance** tests passed; no
  PostgreSQL/S3 service was started for this source task.
- Integrated tree: **152 recovery/programme tests passed** with
  `PYTHONPATH=src:. .venv/bin/python -m pytest -q tests/integration/recovery
  tests/contract/program -p no:cacheprovider`.
- Direct task governance returned `[]`; `git diff --check` passed. The source
  payload is exactly the six paths in the W58 task. This integration adds
  only its task, this report and bounded `CURRENT_STATE.md`.
- API remains 47 paths / 54 operations / 124 schemas, error catalogue 25,
  domain candidate revision 14, migration head `0023_norm_citations`.
  Frozen API/stage contracts remain unchanged.

No `contracts/**`, migration, root dependency or lock, composition root,
global style, production DB/S3, `origin/main`, tag or deployment input was
changed. The W55b main candidate has a separate complete `make gate` run.
R-135 defers the complete W56–W63 beta gate; these focused checks do not
constitute recovery, corpus-publication or beta acceptance.

## Publication and next step

Publish only the clean exact checked SHA to `origin/dev` as a fast-forward
from the recorded predecessor, then directly read back the remote ref into
ignored local evidence. This task has no `origin/main` authority. Run a real
W58 drill only after an operator proves an empty isolated PostgreSQL target,
atomic `pg_restore`, the pinned fingerprint, a read-only repeatable-read
Session and a single isolated disposable bucket for both object clients.
