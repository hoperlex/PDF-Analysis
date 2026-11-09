#!/bin/bash
# Runs ONE command against a throwaway PostgreSQL + MinIO (tmpfs, the project's own pinned images) and tears both down.
#
#   flock <the host's run lock> timeout 1200 tools/measure/with_throwaway_stand.sh <command> [args...]
#
# The stand lives exactly as long as the command: the two containers are started under fixed names (am-lane-t2-pg,
# am-lane-t2-s3) on fixed loopback ports, the database is migrated to head, the bucket is created, the FF-01 names
# (DATABASE_URL, S3_*) are exported to the command, and the containers are stopped BY THEIR OWN NAMES on exit.
# Nothing is killed by pattern or by PID. The command runs from the repository root; PYTHONPATH=src is set.
#
# Override the names/ports with LANE_PG_NAME / LANE_S3_NAME / LANE_PG_PORT / LANE_S3_PORT when two stands must coexist
# (never under one host lock). It refuses to start under 2500 MB of available memory.
set -u
[ "$#" -ge 1 ] || { echo "usage: $0 <command> [args...]" >&2; exit 2; }
WT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
PY=${PY:-$WT/.venv/bin/python}
PG=${LANE_PG_NAME:-am-lane-t2-pg}
S3=${LANE_S3_NAME:-am-lane-t2-s3}
PGPORT=${LANE_PG_PORT:-55711}
S3PORT=${LANE_S3_PORT:-55712}
DBNAME=am_lane_blocks

avail=$(free -m | awk '/^Mem:/ {print $7}')
if [ "$avail" -lt 2500 ]; then echo "REFUSED: only ${avail} MB available (<2500)" >&2; exit 3; fi

teardown() {
  docker stop "$PG" "$S3" >/dev/null 2>&1
  echo "STAND_STOPPED $(date -Is)"
}
trap teardown EXIT

echo "STAND_START $(date -Is) available=${avail}MB"
docker rm -f "$PG" "$S3" >/dev/null 2>&1   # only our own, by name; leftovers of an earlier run of this script
docker run -d --rm --name "$S3" --tmpfs /data:rw,size=512m -p 127.0.0.1:$S3PORT:9000 \
  -e MINIO_ROOT_USER=lanetroot -e MINIO_ROOT_PASSWORD=lanetpassword1 \
  minio/minio:RELEASE.2025-09-07T16-13-09Z server /data >/dev/null || { echo S3_FAILED_START; exit 1; }
docker run -d --rm --name "$PG" --tmpfs /var/lib/postgresql/data:rw,size=1g -p 127.0.0.1:$PGPORT:5432 \
  -e POSTGRES_USER=am -e POSTGRES_PASSWORD=am -e POSTGRES_DB=$DBNAME \
  auditmanager-postgres:17.11-pgvector0.8.6-8ee86c9 postgres -c fsync=off -c synchronous_commit=off \
  -c full_page_writes=off -c max_connections=50 >/dev/null || { echo PG_FAILED_START; exit 1; }
for _ in $(seq 1 90); do docker exec "$PG" pg_isready -h 127.0.0.1 -U am -d $DBNAME >/dev/null 2>&1 && break; sleep 1; done
sleep 2

cd "$WT" || exit 2
export DATABASE_URL=postgresql+psycopg://am:am@127.0.0.1:$PGPORT/$DBNAME PYTHONPATH=src
export S3_ENDPOINT_URL=http://127.0.0.1:$S3PORT S3_REGION=us-east-1 S3_ACCESS_KEY_ID=lanetroot \
  S3_SECRET_ACCESS_KEY=lanetpassword1 S3_BUCKET=am-lane-t2
for _ in $(seq 1 60); do
  "$PY" - >/dev/null 2>&1 <<'PYEOF' && { echo S3_READY; break; }
import boto3, os
c = boto3.client('s3', endpoint_url=os.environ['S3_ENDPOINT_URL'], aws_access_key_id=os.environ['S3_ACCESS_KEY_ID'],
                 aws_secret_access_key=os.environ['S3_SECRET_ACCESS_KEY'], region_name='us-east-1')
c.create_bucket(Bucket=os.environ['S3_BUCKET'])
PYEOF
  sleep 1
done
"$PY" -m alembic -c db/migrations/alembic.ini upgrade head > "${TMPDIR:-/tmp}/lane-t2-alembic.log" 2>&1 \
  || { echo ALEMBIC_FAILED; tail -20 "${TMPDIR:-/tmp}/lane-t2-alembic.log"; exit 1; }
echo "HEAD $(docker exec "$PG" psql -U am -d $DBNAME -tAc 'select version_num from alembic_version')"

"$@"
status=$?
echo "COMMAND_EXIT $status"
exit $status
