# CFB-INT-DEV-PUBLISH-28 — W58 restore callback and W54 replay integrity on dev

The candidate builds on directly read
`origin/dev=746311c9ac5760b1658b6862f629471fa0cf15b4`. It cherry-picks the
completed W58 PostgreSQL adapter
`559bddd9b3af353cd9cd87f0e96a3fde5a824b6a` as `270118ac` and the
completed W54 embedding replay check
`26edea8607ebb9ff845f547dff872bedd14ccd58` as `dad5d557`.
Each four-path source patch is byte-for-byte identical after cherry-pick:
the two W58 `git diff` streams have SHA-256
`517dc827bfca562f6ffd9f9c2b41dfc05faedb0b01607414824c4a17cde46546`;
the two W54 streams have SHA-256
`3db4c346db48ade0ee5e539c2e4d934917a6e340ff7827fb121d14def255f025`.

## Checks and scope

- W58 source: **24** fake-engine/runner focused tests, task governance and
  compilation passed. W54 source: **13** offline repository tests passed;
  its new regression failed before the fix and passed after it.
- Integrated W58 recovery, W54 embedding repository and programme suites:
  **189 passed** with no PostgreSQL/S3 service.
- Direct integration-task governance returned `[]`; `git diff --check`
  passed. The source has exactly its eight disjoint granted paths. This
  integration adds only its task, this report and bounded
  `CURRENT_STATE.md`.
- API remains **48 paths / 55 operations / 131 schemas**, SHA-256
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
  stage registry SHA-256 remains
  `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`.
  Domain IDs, error catalogue and migration head `0023_norm_citations`
  match their frozen inputs.

No contract, migration, root dependency/lock, composition root, global
style, production DB/S3, `origin/main`, tag or deployment input changed.
The W58 adapter is unactivated; the W54 check changes only an exact
embedding-build replay, which now streams stored window metadata before
returning `created=False`.

## Limits and publication

The W58 callback refuses a nonempty or visibly unsafe PostgreSQL target,
restores atomically, computes the pinned stand fingerprint and yields a
read-only repeatable-read Session. Fake tests do not prove the target is
isolated: a loopback port can still be a tunnel, an external writer can
race, and the operator must prove the Blob bucket matches. No real DB/S3
drill, timing/RPO or B6 recovery verdict is claimed.

The W54 replay check detects missing/changed/extra persisted window
metadata. It does not rehash vector bytes or qualify the real 674-document
corpus. Repair of 121 pages, complete embeddings, bundle and DB/S3
publication remain pending. R-135 defers the complete W56–W63 beta gate;
W55b's main release gate is separate.

Publish only the clean exact checked SHA to `origin/dev` as a fast-forward
from the recorded predecessor, then directly read back the remote SHA into
ignored local evidence. This task has no `origin/main` authority.
