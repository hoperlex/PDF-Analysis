# CFB-INT-DEV-PUBLISH-64 — unserved reference and source checks

The published development base is
`417123c729599cfa075d3461038c8dd15b86d4a3` (dev63). Three disjoint
source commits were reviewed and cherry-picked: W59 observation identity
`ea7436d26310e755877bdf8ddf38fd0e039a18fe`, W56b crop source digest
`3aa14a5bd181ac6ac89746dee22858ef414ab117`, and W57b Run reference
chain `49ed17238cd8bf729e6d51cae5aa86057bfdad76`.

## Result and checks

- The W57b read-only use case composes two existing current-Attempt saved
  readers, a PDF-text page bridge and the pure reference resolver under one
  caller-owned transaction. It requires explicit Run/Version/set/snapshot
  pins and an explicit unparsed-slug tuple, then rechecks the Attempt and Run
  pin. OCR-only pages remain unread PDF text.
- W56b's saved crop reader now checks the cohort's source block digest
  against the immutable Version manifest and repeats the Version fence after
  Blob reads. A self-consistent forged StageResult reference and Blob is
  refused.
- W59 finding match suggestions refuse one observation ID reused across
  source and target versions; distinct IDs keep the same exact match.
- Combined focused readers, matcher, ALR-05/stage facade and programme
  governance command: **189 passed**. Five pytest warnings concern shared
  `/tmp/pytest-of-root/garbage-*` cleanup; there were no test failures.
- Source checks: W57b **73 focused + 16 governance + 3 architecture**,
  W56b **57 focused + 16 governance**, W59 **40 focused + 16 governance**.
  Frozen hashes, owned Python compilation, documentation facts, exact 17-path
  diff, whitespace and direct handoff are checked before publication.
- Remote fast-forward and exact-SHA readback are recorded after this report
  is committed. R-135 defers the complete beta `make gate`.

## Boundaries

No contract, migration, root dependency, composition root, global style,
served API/UI, provider, production corpus/DB/S3, deployment workflow,
`origin/main` or tag changed. The W57b chain has no deterministic stage,
finding publication or served route, and cannot prove the explicit slug tuple
was reviewed. W56b's new digest check does not prove continued source Blob
availability. W59 has no authoritative comparison snapshot or approved
links. No live service or beta acceptance is claimed.

One agent's checkout command accidentally changed the local integration
branch name after dev63; the tree was clean, the W59 source cherry-pick was
preserved, and the integration branch was fast-forwarded back to that exact
commit before the other two cherry-picks. No remote ref or file content was
changed by that branch-name incident.

Only the task's 17 exact allowlist paths change. A reviewed forward commit
is the rollback route; no migration or runtime feature flag is involved.
