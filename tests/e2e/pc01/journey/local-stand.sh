#!/bin/bash
# A throwaway local stand of THIS tree for the PC-01 browser journey (D-314, D-318).
#
#   npm --prefix web ci          # once; and `NEXT_PUBLIC_API_BASE_URL=/bff/v1 npm --prefix web run build` before the first stand
#   flock <the host's run lock> bash tests/e2e/pc01/journey/local-stand.sh [--hold-seconds N]
#   # in another shell, while it says STAND_READY:
#   . $LANE_STAND_DIR/stand.env && node tests/e2e/pc01/journey/journey.mjs --origin $ORIGIN --phase all --allow-spend --out <dir>
#   touch $LANE_STAND_DIR/stop   # or let the hold time run out
#
# Brings up tmpfs PostgreSQL + MinIO (containers am-lane-pc01-pg / am-lane-pc01-s3), migrates to head, loads the
# release notes, starts the API (EXECUTION_ROLE=api), a worker (EXECUTION_ROLE=worker, recorded provider) and
# `next start` of an already built web/ (`next build` first), takes the seeded administrator off the shipped
# password through the API, writes the journey's environment to $S/stand.env and waits for $S/stop (or the
# deadline). Everything is torn down by the trap: own PGIDs and own containers by name only.
set -u
WT=${WT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)}
S=${LANE_STAND_DIR:-${TMPDIR:-/tmp}/pc01-stand}
mkdir -p "$S"
PY=${PY:-$WT/.venv/bin/python}
HOLD=${1:-1500}
[ "${1:-}" = "--hold-seconds" ] && HOLD=${2:-1500}
PG=${LANE_PG_NAME:-am-lane-pc01-pg}; S3=${LANE_S3_NAME:-am-lane-pc01-s3}
PGPORT=${LANE_PG_PORT:-55701}; S3PORT=${LANE_S3_PORT:-55702}; APIPORT=${LANE_API_PORT:-55703}; HEALTHPORT=${LANE_HEALTH_PORT:-55704}; WEBPORT=${LANE_WEB_PORT:-55705}
DBNAME=am_lane_journey
RUN=$S/run; rm -rf "$RUN"; mkdir -p "$RUN"; rm -f "$S/stop" "$S/stand.env" "$S/stand.ready"
PIDS=()

avail() { free -m | awk '/^Mem:/ {print $7}'; }
if [ "$(avail)" -lt 3500 ]; then echo "REFUSED: only $(avail) MB available (<3500)"; exit 3; fi

teardown() {
  rm -f "$S/stand.ready"
  for pid in "${PIDS[@]}"; do kill -TERM -- "-$pid" 2>/dev/null; done
  sleep 3
  for pid in "${PIDS[@]}"; do kill -KILL -- "-$pid" 2>/dev/null; done
  docker stop "$PG" "$S3" >/dev/null 2>&1
  echo "STAND_STOPPED $(date -Is)"
}
trap teardown EXIT

# `setsid bash -c 'echo $$ > pidfile; exec ...'` so the recorded PID is the process group leader.
spawn() { # name, logfile, command...
  local name=$1 log=$2; shift 2
  setsid bash -c 'echo $$ > "$0"; exec "$@"' "$RUN/$name.pid" "$@" > "$log" 2>&1 < /dev/null &
  for _ in $(seq 1 50); do [ -s "$RUN/$name.pid" ] && break; sleep 0.1; done
  PIDS+=("$(cat "$RUN/$name.pid")")
  echo "started $name pid $(cat "$RUN/$name.pid")"
}

echo "stand start $(date -Is) available=$(avail) MB"
docker rm -f "$PG" "$S3" >/dev/null 2>&1   # only our own, by name; leftovers of an earlier session
docker run -d --rm --name "$S3" --tmpfs /data:rw,size=512m -p 127.0.0.1:$S3PORT:9000 \
  -e MINIO_ROOT_USER=lanevroot -e MINIO_ROOT_PASSWORD=lanevpassword1 \
  minio/minio:RELEASE.2025-09-07T16-13-09Z server /data >/dev/null || { echo S3_FAILED_START; exit 1; }
docker run -d --rm --name "$PG" --tmpfs /var/lib/postgresql/data:rw,size=2g -p 127.0.0.1:$PGPORT:5432 \
  -e POSTGRES_USER=am -e POSTGRES_PASSWORD=am -e POSTGRES_DB=$DBNAME \
  auditmanager-postgres:17.11-pgvector0.8.6-8ee86c9 postgres -c fsync=off -c synchronous_commit=off \
  -c full_page_writes=off -c max_connections=100 >/dev/null || { echo PG_FAILED_START; exit 1; }
for _ in $(seq 1 90); do docker exec "$PG" pg_isready -h 127.0.0.1 -U am -d $DBNAME >/dev/null 2>&1 && break; sleep 1; done
sleep 2

cd "$WT" || exit 2
export DATABASE_URL=postgresql+psycopg://am:am@127.0.0.1:$PGPORT/$DBNAME PYTHONPATH=src
export S3_ENDPOINT_URL=http://127.0.0.1:$S3PORT S3_REGION=us-east-1 S3_ACCESS_KEY_ID=lanevroot \
  S3_SECRET_ACCESS_KEY=lanevpassword1 S3_BUCKET=am-lane-pc01
for _ in $(seq 1 60); do
  $PY - >/dev/null 2>&1 <<'PYEOF' && { echo S3_READY; break; }
import boto3, os
c = boto3.client('s3', endpoint_url=os.environ['S3_ENDPOINT_URL'], aws_access_key_id=os.environ['S3_ACCESS_KEY_ID'],
                 aws_secret_access_key=os.environ['S3_SECRET_ACCESS_KEY'], region_name='us-east-1')
c.create_bucket(Bucket=os.environ['S3_BUCKET'])
PYEOF
  sleep 1
done
$PY -m alembic -c db/migrations/alembic.ini upgrade head > "$S/alembic.log" 2>&1 || { echo ALEMBIC_FAILED; tail -20 "$S/alembic.log"; exit 1; }
echo "HEAD $(docker exec "$PG" psql -U am -d $DBNAME -tAc 'select version_num from alembic_version')"
# The norms snapshots the night window's steps designate (README, "What the stack needs"): by SQL, refuses a database
# whose name lacks `journey` or `lane`, and stores the bytes its bindings name in the lane's own bucket first.
$PY tests/e2e/pc01/journey/seed_norms.py > "$S/seed-norms.log" 2>&1 || { echo SEED_NORMS_FAILED; tail -10 "$S/seed-norms.log"; exit 1; }
$PY -m auditmanager.releases.load > "$S/releases.log" 2>&1 || { echo RELEASES_FAILED; tail -10 "$S/releases.log"; exit 1; }

export AUDITMANAGER_API_TOKEN=lane-v-throwaway-token-authorizes-nothing-real
export AUDITMANAGER_PROVIDER_MODE=recorded AUDITMANAGER_PROVIDER_SOURCE=environment
# AUDITMANAGER_EXTENDED_ANALYSIS=0: the committed recordings answer the PLAIN analysis only; the shipped default
# (the extended review, v3 plan) asks dozens of further model calls per window that no recording holds, so a
# recorded run under it fails `text_analysis` with `recording_missing` (tests/support/run_consent.py,
# `plain_analysis_pricing`). The API reads it when it prices the estimate and starts the run.
export AUDITMANAGER_COMPARISON_MODULES=versions,stages AUDITMANAGER_EXTENDED_ANALYSIS=0
export AUDITMANAGER_PUBLIC_ORIGIN=http://127.0.0.1:$WEBPORT
mkdir -p "$RUN/worker-state"
spawn api "$S/api.log" env EXECUTION_ROLE=api AUDITMANAGER_API_PORT=$APIPORT AUDITMANAGER_HEALTH_PORT=$HEALTHPORT \
  AUDITMANAGER_BIND_HOST=127.0.0.1 $PY infra/deploy/serve.py
# the worker holds no deployment secret and refuses to start with it
# LANE_C4=1: the C4 stage steps (README, "CMP-JOURNEY-C4-01") need the test-owned synthetic worker to claim the recorded
# comparison items, so the ordinary worker must not compete for them: it runs Run work with the comparison modules off.
WORKER_MODULES=versions,stages
[ "${LANE_C4:-0}" = "1" ] && WORKER_MODULES=none
spawn worker "$S/worker.log" env -u AUDITMANAGER_API_TOKEN EXECUTION_ROLE=worker AUDITMANAGER_COMPARISON_MODULES=$WORKER_MODULES \
  AUDITMANAGER_WORKER_STATE_DIR="$RUN/worker-state" AUDITMANAGER_WORKER_SLOTS=1 $PY -m auditmanager.workers serve
if [ "${LANE_C4:-0}" = "1" ]; then
  : > "$S/c4-receipts.jsonl"
  spawn c4worker "$S/c4worker.log" env AUDITMANAGER_PROVIDER_MODE=recorded AUDITMANAGER_COMPARISON_MODULES=versions,stages \
    $PY tests/e2e/pc01/journey/c4_recorded_worker.py --local-synthetic-only --seed-route --receipts "$S/c4-receipts.jsonl"
fi
for _ in $(seq 1 90); do curl -fsS "http://127.0.0.1:$HEALTHPORT/readyz" >/dev/null 2>&1 && { echo API_READY; break; }; sleep 1; done
curl -fsS "http://127.0.0.1:$HEALTHPORT/readyz" >/dev/null 2>&1 || { echo API_NOT_READY; tail -20 "$S/api.log"; exit 1; }

cd "$WT/web" || exit 2
spawn web "$S/web.log" env NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 \
  AUDITMANAGER_API_UPSTREAM=http://127.0.0.1:$APIPORT AUDITMANAGER_SESSION_STORE="$RUN/register.json" \
  NEXT_PUBLIC_API_BASE_URL=/bff/v1 NEXT_PUBLIC_INSTANCE_LABEL=alpha \
  ./node_modules/.bin/next start -p $WEBPORT -H 127.0.0.1
for _ in $(seq 1 60); do curl -fsS -o /dev/null "http://127.0.0.1:$WEBPORT/login" && { echo WEB_READY; break; }; sleep 1; done
curl -fsS -o /dev/null "http://127.0.0.1:$WEBPORT/login" || { echo WEB_NOT_READY; tail -20 "$S/web.log"; exit 1; }
cd "$WT" || exit 2

# R-50: take the seeded administrator off the shipped password, against the API directly (README, "Taking the
# seeded administrator off the shipped password"). The new login is the e-mail the profile then carries.
ADMIN_LOGIN="journey-admin@example.test"
ADMIN_PASSWORD="Lv$(head -c 12 /dev/urandom | od -An -tx1 | tr -d ' \n')!x"
API=http://127.0.0.1:$APIPORT ADMIN_LOGIN=$ADMIN_LOGIN ADMIN_PASSWORD=$ADMIN_PASSWORD $PY - <<'PYEOF' || { echo ADMIN_SETUP_FAILED; exit 1; }
import json, os, urllib.request
api = os.environ['API']
def call(method, path, body=None, token=None):
    req = urllib.request.Request(api + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={'content-type': 'application/json', **({'authorization': 'Bearer ' + token} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
st, tok = call('POST', '/auth/token', {'login': 'admin', 'password': 'password'})
assert st == 200, ('seeded token', st, tok)
t = tok['access_token'] if 'access_token' in tok else tok['token']
st, body = call('POST', '/auth/password', {'current_password': 'password', 'new_password': os.environ['ADMIN_PASSWORD']}, t)
assert st in (200, 204), ('password', st, body)
st, tok = call('POST', '/auth/token', {'login': 'admin', 'password': os.environ['ADMIN_PASSWORD']})
assert st == 200, ('new token', st, tok)
t = tok['access_token'] if 'access_token' in tok else tok['token']
st, body = call('PATCH', '/me', {'last_name': 'Журнал', 'first_name': 'Администратор', 'middle_name': 'Стенд', 'email': os.environ['ADMIN_LOGIN']}, t)
assert st == 200, ('profile', st, body)
print('ADMIN_READY', os.environ['ADMIN_LOGIN'])
PYEOF

cat > "$S/stand.env" <<EOF
export ORIGIN=http://127.0.0.1:$WEBPORT
export E2E_PC01_LOGIN='$ADMIN_LOGIN'
export E2E_PC01_PASSWORD='$ADMIN_PASSWORD'
export E2E_PC01_CHROME=${E2E_PC01_CHROME:-/root/.cache/chrome-for-testing/chrome-headless-shell/linux-156.0.8078.47/chrome-headless-shell-linux64/chrome-headless-shell}
export E2E_PC01_SESSION_STORE_PATH='$RUN/register.json'
export DATABASE_URL='$DATABASE_URL'
export S3_ENDPOINT_URL='$S3_ENDPOINT_URL' S3_REGION=us-east-1 S3_ACCESS_KEY_ID=lanevroot S3_SECRET_ACCESS_KEY=lanevpassword1 S3_BUCKET=am-lane-pc01
export PYTHONPATH=src
$([ "${LANE_C4:-0}" = "1" ] && echo "export E2E_C4_RECORDED_RECEIPTS='$S/c4-receipts.jsonl'")
EOF
chmod 600 "$S/stand.env"
touch "$S/stand.ready"
echo "STAND_READY $(date -Is) available=$(avail) MB; hold ${HOLD}s or touch $S/stop"
DEADLINE=$((SECONDS + HOLD))
MIN=$(avail)
while [ $SECONDS -lt $DEADLINE ] && [ ! -e "$S/stop" ]; do
  a=$(avail); echo "$(date +%T) $a" >> "$S/stand-mem.log"
  sleep 5
done
echo "stand ending $(date -Is) (stop file: $([ -e "$S/stop" ] && echo yes || echo no))"
