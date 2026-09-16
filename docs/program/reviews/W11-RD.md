# `W11-RD` — the read path does not verify what the manifest promised

Session `W11-RD`, worktree `/root/w11rd`, branch `agent/w11-rd`.

`HEAD` on arrival: **`5d14921`** ("docs: the wave 11 dispatch — repair what wave 10 found"),
which is `origin/dev`. The brief says base `30d129c` "or later"; `5d14921` is that commit plus
two docs-only commits.

Instance `gate-w11a`: `POSTGRES_PORT=55630`, `S3_API_PORT=59230`, `S3_CONSOLE_PORT=59231`,
`POSTGRES_DB=audit_w11a`, bucket `auditmanager-gate-w11a`. Logs in `/root/w11rd-logs/`.

## Baseline

`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`, `npm --prefix web ci`, then `make gate`
at `5d14921` before any change:

```
1264 passed, 5 skipped, 116 subtests passed in 191.55s
GATE OK: battery, foundation, frontend and whitespace all pass
```

The brief's expected counts are exact. (`/root/w11rd-logs/gate-baseline.log`)

## What the tree actually does — before the repair

Three facts, read off the tree rather than off the brief:

1. `IngestService.read_source_bytes` (`src/auditmanager/ingest/service.py`) resolves
   `entry = self.require_source_entry(version_uid)` — which carries `entry.sha256` and
   `entry.size_bytes` — and returns `self._store.read(entry.blob_id)`. It uses `entry.sha256`
   in exactly one place: as a *detail* on the `storage_integrity_error` it raises when the
   object is **absent**. It never compares it to the bytes. Confirmed.
2. `S3BlobStore.read` (`src/auditmanager/storage/s3.py`) re-hashes what it read and compares
   it to `_metadata_value(response, _META_SHA256)` — the **object's own** recorded digest —
   under `if recorded is not None and recorded != actual`. An object carrying no
   `content-sha256` user metadata is returned with no check at all, from a method whose
   parameter is named `verify` and defaults to `True`. Confirmed.
3. `Reconciler.verify_version` (`src/auditmanager/ingest/reconciliation.py`) does hold a
   manifest comparison — `if published.sha256 != entry.sha256 or published.size !=
   entry.size_bytes` — but `published` comes from `self._store.inspect(...)`, which is a
   `head_object`. It compares the manifest against the object's **recorded metadata**, and
   never against bytes. The brief said to check `verify_version` first in case it already held
   the comparison the read path needs: it does not. It holds a comparison of two *declarations*.
   Nothing in the tree hashes stored bytes and compares the result to the manifest.

