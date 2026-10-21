# W58-INT-TARGET-LIST-BOUNDS-01 — bounded target listing addendum

Base: published dev65 `8c39b9e0dfd63da7d32d1a848e609ae2dd437a01`.

The unactivated isolated target restore now passes the sealed object count
into every target listing. A page whose rows would exceed that count refuses
before iterating over them. A target that keeps returning unique continuation
tokens without completing the listing refuses after at most count+1 requests.
The existing unique-token and exact target key/size checks remain in place;
ordinary one-key pages and retries still work.

## Changed files

- `scripts/recovery/target_object_restore.py` — count and page bounds for
  initial and both final target listings;
- `tests/integration/recovery/test_target_object_restore.py` — unique empty
  continuation, oversized page and unchanged valid pagination regressions;
- `docs/program/tasks/W58-INT-TARGET-LIST-BOUNDS-01.md` — exact task grant;
- this addendum.

## Checks

- Before the fix, the oversized-page regression failed with the old generic
  extra-key refusal rather than refusing at the listing size preflight. The
  unique-empty-token case was not run unbounded against the old code.
- Target restore, source mirror and object copy suites: **53 passed**.
- Complete recovery and programme governance suites: **185 passed**.
  Owned Python compilation and `git diff --check` passed. Five pytest
  warnings concern stale shared `/tmp/pytest-of-root/garbage-*` cleanup.
  Frozen SHA readback and exact-path committed handoff are checked before
  integration.
- No Docker, PostgreSQL/S3, provider or full beta gate under R-135.

## Contracts and limitations

No API, migration, stage registry, error catalogue, target object format,
served route or data state changed. A legitimate target endpoint returning
more than count+1 pages, including repeated empty truncated pages, now
refuses; the operator can retry after investigating the endpoint. The bound
does not make the bucket snapshot atomic, prove isolation or replace the
later real recovery drill. Failed transfers may still leave a verified
partial prefix in the disposable target.

Only the task's four paths change. The integration owner may cherry-pick the
source commit into a later `origin/dev` slot after review. A source revert
before drill activation is the rollback route; no data rollback or flag.
