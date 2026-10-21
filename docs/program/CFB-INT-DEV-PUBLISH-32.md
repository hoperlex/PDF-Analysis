# CFB-INT-DEV-PUBLISH-32 — W59 route and W58 Blob readback fix on dev

The completed W59 source `1f34b01cceb0688989d80b1977c1619ffb260166`
is an exact fast-forward child of published dev31
`69b923156ea3988dbad3cc378644b9799a6bdd23`. Its four task-owned paths
are integrated without editing their bytes. The W58 source
`844c7213916c69c10974ce2f02ff1495baee4a1b`, also based on dev31,
is cherry-picked with its five-path patch unchanged.
The source and integrated W58 recovery-code diff streams both have SHA-256
`0b82286f23cb9b8428c66c25418613f1fd8d58dbd5b7d85f55827a1814df062e`.

## Checks and scope

- W59 source completed 14 focused tests, compilation, direct task
  governance, frozen SHA-256 and exact path checks.
- W58 source completed a real BlobStore fake-client red/green regression,
  21 focused tests, 16 governance tests, compilation and exact paths.
- Integrated section, W58 recovery and programme suites: **112 passed**.
  The first run exposed the 120-line live-state limit; after shortening its
  summary, the same suites passed with no failing test.
- Direct task governance for this integration and both source tasks returned
  `[]`. Changed Python compilation, frozen contract/migration SHA-256
  readback and `git diff --check` passed. Exact candidate path, clean-tree
  and fresh-remote fast-forward checks precede publication.

No contract, migration, root dependency/lock, composition root, existing
production route/Run/profile code, W54/W55/W58 path, global style,
production DB/S3, `origin/main`, tag or deployment input changed. The one
W58 `scripts/recovery/target_object_restore.py` path changes only the
unactivated target copy helper.

## Limits and publication

The pure guard checks that supplied explicit P/R stage and same-version
expert confirmation agree, then pins section and available profile ID. It
does not prove those facts are saved or that the expert is authorized; no
served route uses it. SECTION-SEAL still needs an authorized DB read, sealed
profile map and Run pin write after W58-code close. W58's target copy now
stores the locally verified sealed SHA-256 as `content-sha256`, allowing the
normal BlobStore readback. The frozen seal has no full source S3 metadata;
role, media type and custom metadata restoration still need a policy and a
real isolated positive-Blob drill. R-135 defers the full
W56–W63 beta gate; W55b release gate is separate.

Publish only the clean exact checked SHA to `origin/dev` as a fast-forward
from the recorded predecessor, then directly read back the remote SHA. This
task has no `origin/main` authority.
