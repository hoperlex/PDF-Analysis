# W54-JUDGE-A — custody, bundle, copy record and stand tools (static)

**Reviewer:** a fresh-context subagent of the integrator `pdf-analysis-62`, 2026-10-12.
**Subject:** `integration/w54` @ `146bff9` (base `7ebf162`).
**Mode:** static review only. No test, container or network was used.

**Verdict: ACCEPT-WITH-FIXES.** No blocker was found. The importer has never run against
PostgreSQL and S3; that verification gap is closed in the window.

## Findings

| # | Severity | Finding | Where | Fix |
| --- | --- | --- | --- | --- |
| F1 | Major, plausible | `deploy.sh`'s stand guards pass silently when the deploy account cannot search the 0700 copy or staging directory: `-e` returns false and every guard passes | `infra/deploy/deploy.sh:165-190` | refuse when the parent directory exists but is not searchable, or assert ownership; add a refusal case |
| F2 | Minor | the custody `reconcile` verb has no caller, and `objects/` is discarded after a database-only `report` | `norms/custody/service.py:638`, `norms/bundle/stand.py:483`, `receive-bundle.sh:473-476` | run the reconciler as import step 5 (or inside `report`) and discard only after zero incidents |
| F3 | Minor, plausible | `resume` checks the import lock without holding it, so it can race `import` | `copy-serve.sh:879-904`, `receive-bundle.sh:429-438` | `resume` holds `import.lock`; `import` takes the lock before `require_record_admits_import` |
| F4 | Minor, plausible | `record.json` is rewritten under two different locks | `receive-bundle.sh:248-256`, `copy-serve.sh` `set_rec`, `lib/forced-command.sh:297-315` | every writer takes `copy.lock` |
| F5 | Minor | `StorageError` exits 1, which is also the report-mismatch code | `norms/bundle/cli.py:158-167` | map it to `EXIT_REFUSED` with a reason |
| F6 | Minor | a failed `dump-db` overwrites the previous closed record, so the previous copy can no longer be restored | `copy-serve.sh:577-605` | keep `record.prev.json` until the new dump completes |
| F7 | Minor, documented | `DROP SCHEMA public CASCADE` runs outside pg_restore's transaction, and may drop pgvector | `copy-serve.sh:861-863` | verify in the rehearsal; recreate extensions |
| F8 | Minor, plausible | `tmp/<nad>` objects of poisoned, never-requeued admissions remain | `norms/custody/service.py:339-340` | register as a debt row (the port has no `list`) |

**Traced and refuted:**

- double admission or binding;
- an `R-76` reuse bypass;
- a Blob rejected through custody;
- non-convergence at the five interruption points;
- a broken all-or-nothing import;
- a replay that writes;
- an importer that accepts a waiver after the marker, an expired or unattested record, a drifted fingerprint, the wrong head, or running writers;
- tar path, symlink or hardlink escape;
- forced-command injection;
- SQL interpolation in `verify-objects`.

## Not verifiable statically (window and rehearsal)

1. BUNDLE's 19 heavy cases plus the whole bundle suite. The Python fingerprint must equal the psql fingerprint byte for byte.
2. Whether deploy-auto's `VPS_USER` is the keys' account. This decides whether F1 is live.
3. `docker compose ps --quiet` with restarting or one-off containers.
4. `mc ls --json` field names, and busybox `df`/`du`.
5. The pgvector extension after `restore-db`.
6. GNU tar `h` entries for hardlinks.
7. `flock` available to `deploy.sh`.
8. The waiver, full-copy, marker-refusal and discard paths.

**Doc drift:** the STAND-COPY report §4 says the discard is not implemented, but BUNDLE
implemented it in `verb_report`.
