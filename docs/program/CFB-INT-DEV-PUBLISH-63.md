# CFB-INT-DEV-PUBLISH-63 — corpus-independent corrections

The published development base is
`7b56cb451946d250b1030f61150a4979dbcfc157` (dev62). Three disjoint
source commits were reviewed and cherry-picked: W59 sheet bounds
`02ffcd0484e0478f5ade407d15e4947252cf191e`, W56a evaluation identity
`62b934834b679a9573f8d0b34126100593d5940d`, and W58 target retry
metadata `430359325da4530098ac7d8bfe65809e51e4f9ef`.

## Result and checks

- W56a recorded evaluation now rejects a `finding_uid` or
  `finding_observation_id` repeated in another seeded Run. The test keeps a
  globally unique series green and proves both collision cases red before the
  fix.
- W58's target object restore checks `content-sha256` metadata on every
  existing-object retry and final readback, along with exact bytes. The
  synthetic drill fixture now preserves that metadata.
- W59 sheet suggestions enforce the per-page and aggregate character caps
  before UTF-8 encoding. Frozen boundary digests are unchanged.
- Combined focused comparison, evaluation, recovery and programme governance
  command: **304 passed**. Five pytest warnings concern cleanup of shared
  `/tmp/pytest-of-root/garbage-*` directories; there were no failures.
- Source handoffs passed: W59 **99 comparison + 16 governance**, W56a **24
  bridge/matcher**, W58 **165 recovery + 16 governance**. Owned Python
  compilation, frozen input hashes, 16-path diff, whitespace and direct
  integration handoff are checked before publication.
- Remote fast-forward and exact-SHA readback are recorded after this report
  is committed. R-135 defers the complete beta `make gate`.

## Boundaries

No contract, migration, root dependency, composition root, global style,
served API/UI, provider, production corpus/DB/S3, deployment workflow,
`origin/main` or tag changed. The three corrections are offline/unserved. The
W58 seal still does not retain other source-S3 metadata and no real-service
drill ran. W59 raw diff still caps one comparison revision at 32 pairs and a
2,000,000-character budget. W56a source custody and measured recorded
baseline remain separate. No beta or corpus-publication acceptance is claimed.

Only the task's 16 exact allowlist paths change. A reviewed forward commit
is the rollback route; no migration or runtime feature flag is involved.
