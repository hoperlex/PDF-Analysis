#!/bin/bash
# A throwaway PostgreSQL on tmpfs, migrated to head, ONE driver of this directory run against it, the container stopped by its own name.
#
#   flock <the host's run lock> tools/measure/perf/perf_stand.sh [--label NAME] [--driver perf_main.py] [--smoke]
#
#   --label   the run's name; the results go to $PERF_RESULTS/run-NAME (default: the driver's name and the UTC time)
#   --driver  any perf_*.py of this directory (default perf_main.py); it gets DATABASE_URL, PYTHONPATH=src, PERF_OUT, PERF_TREE
#   --smoke   a small volume (12 + 8 documents, passes of 20..40 proposals, memory to 150 and 400 cases, 2 warm runs): seconds, not minutes
#   --dry-run print what would run (driver, container, port, results directory) and exit 0: no docker, no directory, no memory check
#
# Environment (all optional): PY (the interpreter, default <repo>/.venv/bin/python), PERF_RESULTS (default <repo>/.local/perf, git-ignored),
# PERF_TMPFS_MB (the data directory, default 2500: the 700-document volume plus the memory to 100,000 cases needs about 2.3 GB),
# PERF_TIMEOUT (seconds for the driver, default 1100), PERF_BASE (for perf_base_compare.py), LANE_PG_NAME / LANE_PG_PORT (default
# am-lane-perf-pg / 55731; change both when two stands must coexist, never under one host lock), and any PERF_* scale variable of perf_seed.py.
#
# The server runs on its own defaults (shared_buffers 128 MB, work_mem 4 MB, JIT on: infra/deploy/compose.server.yml sets no option); only the
# three write-speed switches (fsync, synchronous_commit, full_page_writes) are off. Every trigger of the schema stays on in the seed.
# Nothing is killed by pattern or by PID: the container is stopped BY NAME. It refuses to start under 2500 MB of available memory.
set -u
LABEL=""; DRIVER=perf_main.py; MODE=full; DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --label) LABEL=$2; shift 2 ;;
    --driver) DRIVER=$2; shift 2 ;;
    --smoke) MODE=smoke; shift ;;
    --dry-run) DRY=1; shift ;;
    *) echo "usage: $0 [--label NAME] [--driver perf_X.py] [--smoke] [--dry-run]" >&2; exit 2 ;;
  esac
done
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
WT=$(cd "$HERE/../../.." && pwd)
[ -f "$HERE/$DRIVER" ] || { echo "no such driver in $HERE: $DRIVER" >&2; exit 2; }
PY=${PY:-$WT/.venv/bin/python}
PG=${LANE_PG_NAME:-am-lane-perf-pg}
PGPORT=${LANE_PG_PORT:-55731}
DB=am_perf
LABEL=${LABEL:-${DRIVER%.py}-$(date -u +%Y%m%dT%H%M%SZ)}
OUT=${PERF_RESULTS:-$WT/.local/perf}/run-$LABEL
if [ "$DRY" = 1 ]; then echo "dry-run: driver=$DRIVER mode=$MODE container=$PG port=$PGPORT out=$OUT"; exit 0; fi
mkdir -p "$OUT"

avail=$(free -m | awk '/^Mem:/ {print $7}')
if [ "$avail" -lt 2500 ]; then echo "REFUSED: only ${avail} MB available (<2500)" >&2; exit 3; fi

cd "$WT" || exit 2
trap 'docker stop "$PG" >/dev/null 2>&1; echo "STAND_STOPPED $(date -Is)"' EXIT
docker rm -f "$PG" >/dev/null 2>&1   # only our own, by name; a leftover of an earlier run of this script
docker run -d --rm --name "$PG" --tmpfs /var/lib/postgresql/data:rw,size=${PERF_TMPFS_MB:-2500}m -p 127.0.0.1:$PGPORT:5432 \
  -e POSTGRES_USER=am -e POSTGRES_PASSWORD=am -e POSTGRES_DB=$DB \
  auditmanager-postgres:17.11-pgvector0.8.6-8ee86c9 postgres -c fsync=off -c synchronous_commit=off -c full_page_writes=off >/dev/null \
  || { echo PG_FAILED_START; exit 1; }
for _ in $(seq 1 90); do docker exec "$PG" pg_isready -h 127.0.0.1 -U am -d $DB >/dev/null 2>&1 && break; sleep 1; done
sleep 2

export DATABASE_URL=postgresql+psycopg://am:am@127.0.0.1:$PGPORT/$DB PYTHONPATH=src PERF_OUT=$OUT PERF_DB=$DB PYTHONDONTWRITEBYTECODE=1
export PERF_TREE="$(git rev-parse --short HEAD) dirty=$(git status --porcelain | wc -l)"
if [ "$MODE" = smoke ]; then
  export PERF_P1_DOCS=12 PERF_P2_DOCS=8 PERF_PASS_SIZES=20,30,40 PERF_OLD_PASS_SIZE=25 PERF_P2_PASS_SIZE=10 PERF_MEMORY_STEPS=150,400 PERF_RUNS=2
fi
echo "start $(date -Is) tree=$PERF_TREE available=${avail} MB mode=$MODE driver=$DRIVER out=$OUT"
"$PY" -m alembic -c db/migrations/alembic.ini upgrade head > "$OUT/alembic.log" 2>&1 || { echo ALEMBIC_FAILED; tail -10 "$OUT/alembic.log"; exit 1; }
echo "head: $("$PY" -m alembic -c db/migrations/alembic.ini current 2>/dev/null | tail -1)"
timeout "${PERF_TIMEOUT:-1100}" "$PY" "$HERE/$DRIVER" > "$OUT/main.log" 2> "$OUT/main.err"
status=$?
echo "driver exit $status $(date -Is)"
tail -25 "$OUT/main.err"
echo "df tmpfs: $(docker exec "$PG" df -h /var/lib/postgresql/data | tail -1)"
exit $status
