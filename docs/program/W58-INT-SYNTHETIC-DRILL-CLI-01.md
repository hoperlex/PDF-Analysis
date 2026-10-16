# W58-INT-SYNTHETIC-DRILL-CLI-01 — isolated synthetic DB and Blob drill preparation

**Base:** published `origin/dev=5fa9473c54a5fb009ec8c0a6a45327a3a7f1dc15`.
**Status:** source preparation only. The real service drill below has **not run**.

## What is ready

`synthetic_drill_fixture.py` takes a PostgreSQL 17 custom dump, the exact
`stand-fingerprint-v1` table lines and one private nonempty Blob payload. It
derives the Blob ID and canonical object key through the public storage
surface, then builds an owner-private W54-shaped `record.json`, `db.dump`,
`inventory.tsv`, W58 `objects.json` and mirror. It runs the existing W58
offline preflight before returning. The inventory ETag is explicitly
`synthetic-local-*`; this is **not** a copy from source S3 and does not attest
source-writer quiescence or the dump's origin.

`synthetic_drill_runner.py` is opt-in. It parses a private target `.env` as
data, checks the 15 frozen names and coherent numeric loopback PG/S3 values,
requires a target-specific instance/database/bucket and PostgreSQL 17 CLI
tools, rechecks the copy, and refuses a nonempty target bucket before opening
the database Engine. It creates a short-lived private libpq passfile, wires
the existing guarded PG callback and W58 coordinator to the same target
bucket, and returns JSON only after exactly one target object and one Blob
were fully read back. The PG callback itself refuses a nonempty database,
wrong SQL identity/version and fingerprint. A failed run preserves the
disposable target for inspection; retry needs a fresh empty database/bucket.

The runner cannot prove that a loopback port is not a tunnel or that Docker
labels/volumes belong to the named lane. The operator proves those before
running it. The frozen W58 seal omits source S3 role, media type and custom
metadata. The target copy writes the sealed `content-sha256` needed for full
Blob streaming, but this synthetic drill is not complete source-S3 recovery
or W58/B6 acceptance. No production or alpha stand may be used here.

## Operator lane: exact synthetic sequence, **deferred until W55b gate releases**

Use a clean checkout containing this task, with its frozen runtime `.venv`
already available. Run as one operator with no concurrent source or target
writer. These six lane values are **candidates** and must be verified free
before use; change all references together if any is occupied:

| Resource | Source | Target |
| --- | --- | --- |
| `FOUNDATION_INSTANCE` / bucket | `auditmanager-w58-synthetic-source-01` | `auditmanager-w58-synthetic-target-01` |
| PostgreSQL port | `57581` | `57582` |
| S3 API / console | `61581` / `61582` | `61583` / `61584` |
| PostgreSQL database | `auditmanager_w58_source_01` | `auditmanager_w58_target_01` |

At each heavy step require `MemAvailable >= 6 GiB`, free disk on both the
Docker data filesystem and the private-copy filesystem at least
`max(6 GiB, 3 GiB + 4 × dump bytes + 3 × Blob bytes)`, and one-minute load
below 8. The 3 GiB reserve and 6 GiB available-RAM floor follow the W54
heavy-step rule; the additional Blob copies cover the synthetic source,
private mirror and target. Swap does not count. Check the actual Docker data
root, since measuring `/` alone is insufficient if Docker uses another mount.

```bash
set -euo pipefail
umask 077
test -x .venv/bin/python
test "$(git status --porcelain | wc -l)" -eq 0
PG17=/usr/lib/postgresql/17/bin
"$PG17/pg_dump" --version
"$PG17/pg_restore" --version
"$PG17/psql" --version
python3 - <<'PY'
import socket
for port in (57581, 57582, 61581, 61582, 61583, 61584):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', port))
print('candidate ports bind on loopback')
PY
DRILL_ROOT="$(pwd -P)/.local/w58-synthetic-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 700 "$DRILL_ROOT"
DOCKER_ROOT="$(docker info --format '{{.DockerRootDir}}')"
if [ "$(stat -c %d "$DOCKER_ROOT")" = "$(stat -c %d "$DRILL_ROOT")" ]; then
  infra/deploy/capacity-probe.sh --path shared="$DOCKER_ROOT" \
    --need shared=$(( 6 * 1073741824 )) --need-ram $(( 6 * 1073741824 ))
else
  infra/deploy/capacity-probe.sh --path docker="$DOCKER_ROOT" --path copy="$DRILL_ROOT" \
    --need docker=$(( 6 * 1073741824 )) --need copy=$(( 6 * 1073741824 )) \
    --need-ram $(( 6 * 1073741824 ))
fi
awk '{ if ($1 >= 8) exit 1 }' /proc/loadavg
```

The branch measures 6 GiB once on a shared filesystem, or independently on
both filesystems. Re-run the probe with the actual dump/Blob size formula before
starting the target. Verify no existing Docker project/volume has either
proposed instance label, and reserve the six ports in the operator lane.

Write the **source** foundation `.env` (only generated test credentials):

```bash
cat > .env <<'ENV'
FOUNDATION_INSTANCE=auditmanager-w58-synthetic-source-01
POSTGRES_DB=auditmanager_w58_source_01
POSTGRES_USER=w58_user
POSTGRES_PASSWORD=synthetic-password
POSTGRES_PORT=57581
DATABASE_URL=postgresql+psycopg://w58_user:synthetic-password@127.0.0.1:57581/auditmanager_w58_source_01
MINIO_ROOT_USER=synthetic-minio-user
MINIO_ROOT_PASSWORD=synthetic-minio-password
S3_ENDPOINT_URL=http://127.0.0.1:61581
S3_API_PORT=61581
S3_CONSOLE_PORT=61582
S3_REGION=us-east-1
S3_ACCESS_KEY_ID=synthetic-minio-user
S3_SECRET_ACCESS_KEY=synthetic-minio-password
S3_BUCKET=auditmanager-w58-synthetic-source-01
ENV
chmod 600 .env
cp .env "$DRILL_ROOT/source.env"
make up check-services migrate check-db
docker ps --filter label=com.docker.compose.project=auditmanager-w58-synthetic-source-01 \
  --format '{{.ID}} {{.Names}} {{.Ports}}'
docker volume ls --filter label=com.docker.compose.project=auditmanager-w58-synthetic-source-01
```

The source has only PostgreSQL and MinIO foundation services: no API, web or
worker writer. Use the existing eight-page synthetic AR baseline as the one
payload. Create one available Blob through the migration's declared
`temporary → verifying → available` transitions, then one project, document,
published version and `input_manifest_entry` whose declared facts match that
Blob. This gives the live W58 audit a nonzero reference to check. It is a
disposable SQL seed, not a product upload path. No source S3 object is
claimed. Keep all later source DB writes stopped.

```bash
PAYLOAD="$DRILL_ROOT/payload.bin"
printf '6d53674f688f9eecd9c7cf3a0eaa391ca2baa751008eeec23c65121ac94bd31f  fixtures/synthetic/ar/ar_baseline.pdf\n' \
  | sha256sum -c -
cp fixtures/synthetic/ar/ar_baseline.pdf "$PAYLOAD"
chmod 600 "$PAYLOAD"
SHA="$(sha256sum "$PAYLOAD" | cut -d' ' -f1)"
SIZE="$(stat -c %s "$PAYLOAD")"
BLOB_ID="$(PYTHONPATH=src:. .venv/bin/python - "$SHA" "$SIZE" <<'PY'
import sys
from auditmanager.storage.public import derive_blob_id
print(derive_blob_id(sha256=sys.argv[1], size=int(sys.argv[2])))
PY
)"
printf '127.0.0.1:57581:auditmanager_w58_source_01:w58_user:synthetic-password\n' \
  > "$DRILL_ROOT/source.pgpass"
chmod 600 "$DRILL_ROOT/source.pgpass"
PGPASSFILE="$DRILL_ROOT/source.pgpass" "$PG17/psql" --no-psqlrc \
  -h 127.0.0.1 -p 57581 -U w58_user -d auditmanager_w58_source_01 \
  -v ON_ERROR_STOP=1 -v blob_id="$BLOB_ID" -v sha="$SHA" -v size="$SIZE" <<'SQL'
BEGIN;
INSERT INTO public.blob (blob_id, state, sha256, size_bytes, media_type)
VALUES (:'blob_id', 'temporary', :'sha', :'size'::bigint, 'application/pdf');
UPDATE public.blob SET state = 'verifying' WHERE blob_id = :'blob_id';
UPDATE public.blob SET state = 'available' WHERE blob_id = :'blob_id';
INSERT INTO public.project (project_uid, name)
VALUES ('prj_00000000000000000000000000', 'W58 synthetic AR restore');
INSERT INTO public.document (document_uid, project_uid, display_title)
VALUES ('doc_00000000000000000000000000',
        'prj_00000000000000000000000000', 'Synthetic AR baseline');
INSERT INTO public.document_version
  (version_uid, document_uid, version_ordinal, source_filename,
   media_type, byte_size, sha256, page_count)
VALUES ('ver_00000000000000000000000000',
        'doc_00000000000000000000000000', 1, 'ar_baseline.pdf',
        'application/pdf', :'size'::bigint, :'sha', 8);
UPDATE public.document SET current_version_uid = 'ver_00000000000000000000000000'
WHERE document_uid = 'doc_00000000000000000000000000';
INSERT INTO public.input_manifest_entry
  (version_uid, role, blob_id, sha256, size_bytes, media_type)
VALUES ('ver_00000000000000000000000000', 'source.document', :'blob_id',
        :'sha', :'size'::bigint, 'application/pdf');
COMMIT;
SQL
```

Create the source fingerprint with the **one frozen SQL block**, dump the
quiescent source using PostgreSQL 17 tools, verify the archive, and confirm
the fingerprint did not move while dumping:

```bash
SOURCE_PG=("$PG17/psql" --no-psqlrc --quiet --no-align --tuples-only
  --set ON_ERROR_STOP=1 -h 127.0.0.1 -p 57581 -U w58_user
  -d auditmanager_w58_source_01)
export PGPASSFILE="$DRILL_ROOT/source.pgpass"
sed -n '/^-- >>> stand-fingerprint-v1$/,/^-- <<< stand-fingerprint-v1$/p' \
  infra/deploy/copy-serve.sh | "${SOURCE_PG[@]}" > "$DRILL_ROOT/fingerprint.lines"
"$PG17/pg_dump" --format=custom --no-owner --no-privileges \
  -h 127.0.0.1 -p 57581 -U w58_user -d auditmanager_w58_source_01 \
  --file "$DRILL_ROOT/source.dump"
"$PG17/pg_restore" --list "$DRILL_ROOT/source.dump" > /dev/null
sed -n '/^-- >>> stand-fingerprint-v1$/,/^-- <<< stand-fingerprint-v1$/p' \
  infra/deploy/copy-serve.sh | "${SOURCE_PG[@]}" > "$DRILL_ROOT/fingerprint-again.lines"
cmp "$DRILL_ROOT/fingerprint.lines" "$DRILL_ROOT/fingerprint-again.lines"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
PYTHONPATH=src:. .venv/bin/python -m scripts.recovery.synthetic_drill_fixture \
  --dump "$DRILL_ROOT/source.dump" \
  --fingerprint-lines "$DRILL_ROOT/fingerprint.lines" \
  --payload "$PAYLOAD" --output-root "$DRILL_ROOT/copy" \
  --stamp "$STAMP" --instance auditmanager-w58-synthetic-source-01 \
  --tree-sha "$(git rev-parse HEAD)"
PYTHONPATH=src:. .venv/bin/python -m scripts.recovery.offline_restore_preflight \
  "$DRILL_ROOT/copy/$STAMP" "$DRILL_ROOT/copy/objects"
make down
```

`make down` keeps the source volumes for inspection. It does not delete
shared images or volumes. Before the target starts, measure its actual
increment `D = stat -c %s source.dump`, `B = stat -c %s payload.bin` and
run the capacity probe again with `max(6 GiB, 3 GiB + 4D + 3B)` free across
the Docker/copy filesystems, plus 6 GiB `MemAvailable` and load under 8.

```bash
D="$(stat -c %s "$DRILL_ROOT/source.dump")"
B="$(stat -c %s "$PAYLOAD")"
GIB=1073741824
NEED=$(( 3 * GIB + 4 * D + 3 * B ))
if [ "$NEED" -lt $(( 6 * GIB )) ]; then NEED=$(( 6 * GIB )); fi
if [ "$(stat -c %d "$DOCKER_ROOT")" = "$(stat -c %d "$DRILL_ROOT")" ]; then
  infra/deploy/capacity-probe.sh --path shared="$DOCKER_ROOT" \
    --need shared="$NEED" --need-ram $(( 6 * GIB ))
else
  infra/deploy/capacity-probe.sh --path docker="$DOCKER_ROOT" --path copy="$DRILL_ROOT" \
    --need docker="$NEED" --need copy="$NEED" --need-ram $(( 6 * GIB ))
fi
awk '{ if ($1 >= 8) exit 1 }' /proc/loadavg
```

Replace `.env` with the **separate target** instance, then start services
without `make migrate`. The image creates an empty `POSTGRES_DB`; the W58
callback independently rejects any user relation before `pg_restore`.

```bash
cat > .env <<'ENV'
FOUNDATION_INSTANCE=auditmanager-w58-synthetic-target-01
POSTGRES_DB=auditmanager_w58_target_01
POSTGRES_USER=w58_user
POSTGRES_PASSWORD=synthetic-password
POSTGRES_PORT=57582
DATABASE_URL=postgresql+psycopg://w58_user:synthetic-password@127.0.0.1:57582/auditmanager_w58_target_01
MINIO_ROOT_USER=synthetic-minio-user
MINIO_ROOT_PASSWORD=synthetic-minio-password
S3_ENDPOINT_URL=http://127.0.0.1:61583
S3_API_PORT=61583
S3_CONSOLE_PORT=61584
S3_REGION=us-east-1
S3_ACCESS_KEY_ID=synthetic-minio-user
S3_SECRET_ACCESS_KEY=synthetic-minio-password
S3_BUCKET=auditmanager-w58-synthetic-target-01
ENV
chmod 600 .env
cp .env "$DRILL_ROOT/target.env"
make up check-services
docker ps --filter label=com.docker.compose.project=auditmanager-w58-synthetic-target-01 \
  --format '{{.ID}} {{.Names}} {{.Ports}}'
docker volume ls --filter label=com.docker.compose.project=auditmanager-w58-synthetic-target-01
PYTHONPATH=src:. .venv/bin/python -m scripts.recovery.synthetic_drill_runner \
  --copy-dir "$DRILL_ROOT/copy/$STAMP" \
  --objects-root "$DRILL_ROOT/copy/objects" \
  --target-env "$DRILL_ROOT/target.env" --pg17-bin "$PG17" \
  > "$DRILL_ROOT/result.json"
cat "$DRILL_ROOT/result.json"
make down
```

The expected JSON has `source_manifest_entries=1`, `target_objects=1`, `target_blobs=1`, equal positive
byte counts, and record/dump/facts SHA-256 values. The runner additionally
requires restored `input_manifest_entry` count 1. It tests target
bucket emptiness before constructing the Engine; the PG adapter tests empty
target relations before `pg_restore`; the coordinator tests the restored
fingerprint and DB-to-sealed-Blob facts before target write, then full target
object and Blob readback. Preserve the private source, copy, result and both
Docker volumes if any step refuses. Do not retry against a partially restored
database. The operator records exact image IDs, project labels, volume names,
port bindings, resource readings, command status and elapsed time in the
separate real drill report.

## Source-task checks and limits

- New fixture/runner tests: **12 passed** in 0.42 s with injected fake
  boundary objects; no service or network request. Tests cover canonical
  private copy, bad fingerprint, unsafe input, strict target `.env`, loopback,
  wrong tool version, nonempty bucket before Engine, callback wiring and
  refusal when positive Blob or source manifest-reference evidence is absent.
- Host PG17 binary check, Python compile and programme governance tests
  (**16 passed**) passed. `git diff --check` and six-path containment are
  checked at commit handoff. Full `make gate` and live DB/S3 remain deferred.
- The offline builder checks a custom-dump header only. `pg_restore --list`
  and then the actual PG17 target restore are the real archive checks. Its
  fingerprint input is operator-supplied; only the target comparison binds
  it to the dump. A forged source record remains possible, so the synthetic
  fixture is never a W54 stand attestation.
- The runner pins the PostgreSQL binary directory. On this host ambient
  `pg_dump`/`pg_restore` are 16.15, while explicit
  `/usr/lib/postgresql/17/bin` tools are 17.11. Without that prefix a PG17
  source/target drill is not reliable.

No API/domain/stage/storage public contract, migration, root lock,
composition or served route changed. Exactly the six task-owned paths named
in the formal task changed. Revert those paths to remove the opt-in tooling.
