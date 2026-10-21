# W58-INT-RELATIONS-PLACEHOLDER-FIX-01 — synthetic DB/Blob drill

## Defect and correction

The first real W58 synthetic run used isolated source
`auditmanager-w58-synthetic-source-01` and target
`auditmanager-w58-synthetic-target-01`. Source PostgreSQL 17 was migrated to
`0023_norm_citations`, seeded with one eight-page synthetic AR PDF Blob and
one `input_manifest_entry`, then quiesced. Its two stand fingerprints matched;
the PostgreSQL 17 custom dump passed `pg_restore --list`, and the private
W54-shaped copy passed offline restore preflight. The dump SHA-256 is
`c41002e405ab84e2b9c676321aea8b923f65f85723744cd9fc34fa691b448f91`
(293,537 bytes); payload SHA-256 is
`6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f`
(58,978 bytes). The sealed `record.json` SHA-256 is
`da1c03ba4524c0c93d35315ed9cabdf061b1cf57594a070f51550b0fde754c21`.
The copy stamp is `20261016T114326Z`, under the ignored, private
`.local/w58-synthetic-20261016/copy/` root.

The first target CLI refused before restore with `ProgrammingError`. A
read-only target catalog had zero public tables. The isolated callback's
`_RELATIONS` SQL used literal `%` in `LIKE` but sent it through
`exec_driver_sql`, where psycopg accepts only placeholder specifiers.
Direct read-only probing returned: `only '%s', '%b', '%t' are allowed as
placeholders, got '%'`. The minimal correction doubles those two literal
percent signs in the Python SQL string. Psycopg sends the original `LIKE`
patterns to PostgreSQL, so target emptiness semantics and restore ordering
are unchanged. The corrected query returned zero relations on target-01
without writing to it. The corrected script SHA-256 is
`12068923d6e0b88a1a07ad2b9a5587a342238d6bc762716519ca4ba5948c58af`.

Target-01 was stopped after inspection; its two volumes were retained.
Neither a restore nor an S3 object write was attempted after its failure.
The first offline fixture invocation also refused because the operator gave
a relative output path; it was rerun once with the required new absolute
private path before either target run.

## Successful fresh target-02 run

Fresh `auditmanager-w58-synthetic-target-02` used PostgreSQL port `57583`,
S3 ports `61585`/`61586`, database `auditmanager_w58_target_02` and a matching
private bucket. Before start, the required 6 GiB floor held: free bytes
`7,084,888,064`, available RAM `7,157,428,224` (swap excluded), load1
`1.52`; the distinct ports bound and no target-02 containers or volumes
existed. PostgreSQL/S3 health and bucket privacy checks passed. Its images
were PostgreSQL `sha256:4c34fc74b2e596ec32e40006f009025895afc520b083635e969c3526c48827f6`,
MinIO `sha256:0d80ac74ea3420cfa7dd718b82395433aa253a11a0cc1159eba8814cfeb9a593`,
and S3 init `sha256:606f8868af7aacb757b2a3bdddf5b14f879fe744f42a54f1f35c739b17d1751d`.
The named volumes are `auditmanager-w58-synthetic-target-02-postgres-data`
and `auditmanager-w58-synthetic-target-02-s3-data`.

The opt-in CLI restored the same sealed copy into that empty target and
returned:

```json
{"dump_sha256":"c41002e405ab84e2b9c676321aea8b923f65f85723744cd9fc34fa691b448f91","record_sha256":"da1c03ba4524c0c93d35315ed9cabdf061b1cf57594a070f51550b0fde754c21","source_manifest_entries":1,"synthetic_isolated_drill":true,"target_blob_bytes":58978,"target_blob_facts_sha256":"3e7326a8c6f0b42e0ed05b704e57c9cae2cb2e6c5bc697233c45437330ad56af","target_blobs":1,"target_object_bytes":58978,"target_objects":1}
```

The exact private result file SHA-256 is
`99fe949383ef62124498de751fbaf38f840f59b8868907b696dbe81b39cbc2ae`.
The CLI checked the restored fingerprint, one source manifest reference,
one target object and one target Blob with full 58,978-byte readback. A
separate read-only SQL check returned migration head `0023_norm_citations`,
one manifest row and one available Blob. Source, failed target-01 and
successful target-02 volumes remain isolated and named; no production or
alpha stand was used.

## Checks, limits and handoff

The existing isolated-postgres and synthetic-runner focused suites passed
**30 tests** after the correction. Python compilation, W58 frozen-input
digests, governance, whitespace and changed-path containment are checked
at commit handoff. No contract, migration, root lock, composition root,
global style or served product source changed.

This fixture's inventory ETag is explicitly synthetic-local; it did not
mirror the source S3 object or prove source-writer custody. The result is a
small positive synthetic DB/Blob recovery drill, not an attested stand copy,
real corpus publication, complete W58/B6 acceptance or beta gate. Keep the
private evidence and volumes until reviewed, then clean only these named
synthetic resources. Integrate the exact source and report through a later
code-first `origin/dev` task; `origin/main` is outside this task.
