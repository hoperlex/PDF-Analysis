#!/usr/bin/env bash
# `STAND-PURGE-TOOL-01` -- delete the stand's PRODUCT data, keep its accounts and its norm corpus.
#
#   infra/deploy/purge-product-data.sh --database <name> --bucket <name> --dry-run
#   infra/deploy/purge-product-data.sh --database <name> --bucket <name> --yes-purge-product-data
#   infra/deploy/purge-product-data.sh --database <name> --bucket <name> --finish-objects <dump dir>
#
# WHY THIS AND NOT `reset.sh`. `reset.sh` drops the schema and empties the bucket: the accounts
# (the administrator's changed password) and the imported normative corpus go with the test data.
# The owner asked for the test data to go and for those two to stay. A purge baked into a
# migration (`STAND-PURGE-0022-01`, `D-194`) was rejected: a permanent revision must never be
# able to empty a database. So this is an operator tool, run by a person, once, on purpose.
#
# WHAT GOES AND WHAT STAYS is decided in `scripts/recovery/product_purge.py` from
# `schema_coverage.py`'s declared tables: every base table is PRODUCT (truncated), KEEP (never
# written: accounts, registration requests, release notes, lookup data, the whole `norm*`
# corpus) or MIXED (`audit_event`, `command_record`, `blob`: product rows go, the custody
# ledger's and the account-side rows stay). A table nobody classified stops the tool, by name,
# before it touches anything. `--dry-run` prints the whole classification with exact counts.
#
# ORDER, AND WHY IT IS THE ORDER (the shape of `reset.sh`, minus the schema drop):
#
#   1. every guard, before any connection is opened;
#   2. a read-only preflight inside the api image: classification, quiescence (a running job or
#      run refuses unless `--allow-running`), the exact rows and object keys, and a SHA-256 of
#      that plan;
#   3. the worker is stopped (it writes on its own), and a fresh timestamped directory under
#      `infra/deploy/dumps/` gets `pg_dump`, the product objects' bytes and attributes in
#      `reset.sh`'s own layout, and `product-objects.tsv` (key, size, ...) next to them;
#   4. **the dump is verified** -- `pg_restore --list` reads it, `pg_restore` expands every data
#      block to a null sink, and the object mirror has the count and bytes the plan named. The
#      plan is recomputed and must still be the same SHA-256;
#   5. ONE transaction: lock, re-derive the plan, compare, truncate the product tables, delete
#      the product rows of the mixed tables, re-read the count and digest of every keep table
#      and every keep row, and ROLL BACK on any difference;
#   6. only after COMMIT, the product objects by exact key from the dumped list -- never a
#      prefix, never a key the norm custody ledger owns;
#   7. the worker is started again and a report is printed.
#
# THE PYTHON HALF CONNECTS AS THE OWNER (`PROD-04-DB-ROLES-01`, `AD-02`). `api` and `worker` run as an application
# role that cannot truncate and owns nothing, so the `api` image's own `DATABASE_URL` would make the tool's
# `owner-may-write` guard refuse -- and it should: the purge is the one operator act that needs write-everything. This
# wrapper hands the one-off container `MIGRATOR_DATABASE_URL` as `DATABASE_URL`, through the environment of the
# `docker compose` process (compose substitutes it into the `api` service's `environment:` and the password never
# appears in a command line), for these steps and no others; an environment without that url is `[migrator_url_unset]`.
#
# THE TARGET IS ALWAYS THIS STACK. Every step runs through `docker compose -f compose.server.yml`
# against the project `ALPHA_INSTANCE` names, so an exported `DATABASE_URL` pointing somewhere
# else cannot be reached from here. The typed names are the other half of that.
#
# EXIT CODES: 0 done or nothing to do; 2 usage; 3 REFUSED (nothing was changed); 4 FAILED
# (something broke -- the message says what state that leaves; after a COMMIT it is
# `--finish-objects`).
#
# GUARDS ARE DELIMITED BY MARKERS -- `# >>> guard: <name>` / `# <<< guard: <name>`.
# `tests/integration/composition/test_purge_product_data_script.py` reads those markers,
# deletes ONE guard block from a copy of this file and shows the copy no longer refuses. A guard
# that cannot be shown to fail is not evidence. Do not remove a marker without removing its test.

set -Eeuo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$HERE/compose.server.yml"
ENV_FILE="${ALPHA_ENV_FILE:-$HERE/env/alpha.env}"
DUMP_ROOT="${ALPHA_DUMP_ROOT:-$HERE/dumps}"
MODULE_DIR="${ALPHA_PURGE_MODULE_DIR:-$HERE/../../scripts/recovery}"

DATABASE=""
BUCKET=""
PURGE=no
DRY_RUN=no
ALLOW_RUNNING=no
FINISH=""

refuse() {
    printf 'purge-product-data.sh: REFUSED: %s\n' "$1" >&2
    shift
    [ "$#" -eq 0 ] || printf '  %s\n' "$@" >&2
    exit 3
}

fail() {
    printf 'purge-product-data.sh: FAILED: %s\n' "$1" >&2
    shift
    [ "$#" -eq 0 ] || printf '  %s\n' "$@" >&2
    exit 4
}

usage() {
    cat >&2 <<'USAGE'
usage: purge-product-data.sh --database <name> --bucket <name>
                (--dry-run | --yes-purge-product-data | --finish-objects <dump directory>)

  --database <name>            the database this acts on. Must equal the configured one.
  --bucket <name>              the bucket this acts on. Must equal the configured one.
  --dry-run                    print what would go: tables with counts, objects and bytes.
                               Touches nothing.
  --yes-purge-product-data     actually do it, after dumping and verifying the dump.
  --finish-objects <dir>       after a run that committed the database part and could not
                               delete every object: delete the rest, from that run's dumped list.
  --allow-running              purge although a run or a job is executing (it is discarded
                               from under the worker). Default: refuse.
  --env-file <path>            default: infra/deploy/env/alpha.env
USAGE
    exit 2
}

# `exit 4` for anything a command did not handle itself: a refusal is 3 and is spelled out.
on_error() {
    printf 'purge-product-data.sh: FAILED: a step exited non-zero (line %s).\n' "$1" >&2
    exit 4
}
trap 'on_error $LINENO' ERR

# >>> guard: known-options
# An unrecognised option is refused rather than ignored. `--dryrun` silently ignored would run
# the destructive path with the operator believing they had asked for a rehearsal.
while [ "$#" -gt 0 ]; do
    case "$1" in
        --database) DATABASE="${2:-}"; shift 2 ;;
        --bucket) BUCKET="${2:-}"; shift 2 ;;
        --env-file) ENV_FILE="${2:-}"; shift 2 ;;
        --dry-run) DRY_RUN=yes; shift ;;
        --yes-purge-product-data) PURGE=yes; shift ;;
        --allow-running) ALLOW_RUNNING=yes; shift ;;
        --finish-objects) FINISH="${2:-}"; shift 2 ;;
        -h|--help) usage ;;
        *) refuse "unrecognised option: $1" \
                  "Nothing was read and nothing was touched. Run --help." ;;
    esac
done
# <<< guard: known-options

# >>> guard: destructive-flag
# No mode means no intent was expressed. The default of a purge is to do nothing.
if [ "$PURGE" = no ] && [ "$DRY_RUN" = no ] && [ -z "$FINISH" ]; then
    refuse "no --yes-purge-product-data and no --dry-run." \
           "This script truncates the product tables and deletes bucket objects. It will not" \
           "infer that from an absent argument. Rehearse with --dry-run first."
fi
# <<< guard: destructive-flag

# >>> guard: one-mode
modes=0
[ "$PURGE" = yes ] && modes=$((modes + 1))
[ "$DRY_RUN" = yes ] && modes=$((modes + 1))
[ -n "$FINISH" ] && modes=$((modes + 1))
if [ "$modes" -gt 1 ]; then
    refuse "--dry-run, --yes-purge-product-data and --finish-objects were more than one." \
           "They are different things to do to one instance. Choose one."
fi
# <<< guard: one-mode

# >>> guard: names-required
if [ -z "$DATABASE" ] || [ -z "$BUCKET" ]; then
    refuse "--database and --bucket are both required, even for --dry-run." \
           "Typing the target is the point: it is what makes a purge of the wrong instance" \
           "a thing you have to do on purpose."
fi
# <<< guard: names-required

# >>> guard: env-file-present
if [ ! -r "$ENV_FILE" ]; then
    refuse "the deployment environment $ENV_FILE is missing or unreadable." \
           "Without it there is no configured instance to compare the typed names against," \
           "and an unverifiable target is not a target. See env/alpha.env.example."
fi
# <<< guard: env-file-present

# Read the configured instance as DATA. The file is never sourced.
configured() {
    sed -n "s/^[[:space:]]*\(export[[:space:]]\+\)\?$1=//p" "$ENV_FILE" | tail -1 \
        | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/"
}

CONFIGURED_DB="$(configured POSTGRES_DB)"
CONFIGURED_BUCKET="$(configured S3_BUCKET)"
CONFIGURED_INSTANCE="$(configured ALPHA_INSTANCE)"
CONFIGURED_USER="$(configured POSTGRES_USER)"
MIGRATOR_URL="$(configured MIGRATOR_DATABASE_URL)"

# >>> guard: instance-configured
if [ -z "$CONFIGURED_INSTANCE" ] || [ -z "$CONFIGURED_DB" ] || [ -z "$CONFIGURED_BUCKET" ]; then
    refuse "$ENV_FILE names no ALPHA_INSTANCE, POSTGRES_DB or S3_BUCKET." \
           "  ALPHA_INSTANCE: ${CONFIGURED_INSTANCE:-<unset>}" \
           "  POSTGRES_DB   : ${CONFIGURED_DB:-<unset>}" \
           "  S3_BUCKET     : ${CONFIGURED_BUCKET:-<unset>}" \
           "A half-configured environment is not the alpha instance."
fi
# <<< guard: instance-configured

# >>> guard: migrator-url-configured
# The purge truncates, which only the owner role may do. An environment with no owner url has nothing to hand the tool
# but the application's, which the tool refuses after the connection is made; say so before any is.
if [[ ! "$MIGRATOR_URL" =~ ^postgresql\+psycopg://[^:@/]+:[^@/]+@[^:@/]+:[0-9]+/[^?]+$ ]]; then
    refuse "[migrator_url_unset] MIGRATOR_DATABASE_URL in $ENV_FILE is unset or is not a postgresql+psycopg:// url." \
           "The purge truncates tables, which only the owner role (POSTGRES_USER) may do; api's DATABASE_URL is the" \
           "application role's and would be refused. Nothing was read and nothing was touched." \
           "See env/alpha.env.example."
fi
# <<< guard: migrator-url-configured

# >>> guard: database-matches
if [ "$DATABASE" != "$CONFIGURED_DB" ]; then
    refuse "the typed database is not the configured alpha database." \
           "  typed     : $DATABASE" \
           "  configured: $CONFIGURED_DB   (POSTGRES_DB in $ENV_FILE)" \
           "Either the environment is stale or this is the wrong instance. Both are" \
           "reasons to stop rather than to guess."
fi
# <<< guard: database-matches

# >>> guard: bucket-matches
if [ "$BUCKET" != "$CONFIGURED_BUCKET" ]; then
    refuse "the typed bucket is not the configured alpha bucket." \
           "  typed     : $BUCKET" \
           "  configured: $CONFIGURED_BUCKET   (S3_BUCKET in $ENV_FILE)" \
           "The database and the bucket are two halves of one instance's state and this" \
           "script will not purge one against the other's configuration."
fi
# <<< guard: bucket-matches

# >>> guard: compose-file-present
if [ ! -r "$COMPOSE_FILE" ]; then
    refuse "$COMPOSE_FILE is missing." \
           "Every step runs through it; without it this script has no target it is allowed" \
           "to reach."
fi
# <<< guard: compose-file-present

# >>> guard: module-present
# The classification and the transaction live in scripts/recovery/. The api image does not carry
# that directory, so it is mounted from this checkout; a checkout without it cannot purge.
if [ ! -r "$MODULE_DIR/product_purge.py" ] || [ ! -r "$MODULE_DIR/schema_coverage.py" ]; then
    refuse "scripts/recovery/product_purge.py or schema_coverage.py is missing under $MODULE_DIR." \
           "The tool classifies every table from schema_coverage.py; it will not guess."
fi
# <<< guard: module-present

MODULE_DIR="$(cd "$MODULE_DIR" && pwd)"

compose() { docker compose --env-file "$ENV_FILE" --file "$COMPOSE_FILE" "$@"; }

# THE PYTHON HALF RUNS INSIDE THE `api` IMAGE -- the idiom `reset.sh` and `readiness.sh` use, and
# the only one that works on a host promised bash/docker/curl/sed/git and no `.venv`. The image
# carries `src/` but not `scripts/`, so the module directory is mounted read-only. `--user root`
# so it can write into a dump directory the host user owns; it writes nothing else.
api_python() {
    DATABASE_URL="$MIGRATOR_URL" compose run --rm --no-deps -T --user root -e PYTHONPATH=/app/src:/purge \
        -v "$MODULE_DIR:/purge/scripts/recovery:ro" \
        --entrypoint python api -m scripts.recovery.product_purge "$@"
}
api_python_dump() {
    local dir="$1"; shift
    DATABASE_URL="$MIGRATOR_URL" compose run --rm --no-deps -T --user root -e PYTHONPATH=/app/src:/purge \
        -v "$MODULE_DIR:/purge/scripts/recovery:ro" -v "$dir:/dump" \
        --entrypoint python api -m scripts.recovery.product_purge "$@"
}

# Same discovery as reset.sh: a compose file without a worker service (the W53 rollback) has none.
WORKER_DECLARED=no
if grep -q '^  worker:[[:space:]]*$' "$COMPOSE_FILE"; then
    WORKER_DECLARED=yes
fi
WORKER_STOPPED=no
start_worker() {
    [ "$WORKER_STOPPED" = yes ] || return 0
    echo "purge-product-data.sh: starting the worker service again"
    compose up -d --no-deps worker
    WORKER_STOPPED=no
}
# Whatever happens after the worker was stopped -- a refusal, a failure, success -- it is started
# again: the stand is left as it was found. The exit status is the step's, not the restart's.
cleanup() {
    local status=$?
    trap - ERR
    if [ "$WORKER_STOPPED" = yes ]; then
        start_worker || printf 'purge-product-data.sh: !! the worker could not be restarted; run:\n  docker compose --env-file %s --file %s up -d --no-deps worker\n' "$ENV_FILE" "$COMPOSE_FILE" >&2
    fi
    exit "$status"
}
trap cleanup EXIT

echo "purge-product-data.sh: instance   $CONFIGURED_INSTANCE"
echo "purge-product-data.sh: database   $DATABASE"
echo "purge-product-data.sh: bucket     $BUCKET"

FLAGS=()
[ "$ALLOW_RUNNING" = yes ] && FLAGS+=(--allow-running)
DRY_FLAG=()
[ "$DRY_RUN" = yes ] && DRY_FLAG+=(--dry-run)

# `printf` of a captured block, because it holds the screen the operator reads and the lines the
# script parses, and both must come from the same text.
parse() { printf '%s\n' "$2" | sed -n "s/^$1: //p" | tail -1; }

# --- --finish-objects: the database part is done, the objects are not ---------------------
if [ -n "$FINISH" ]; then
# >>> guard: finish-dir-valid
    if [ ! -d "$FINISH" ] || [ ! -r "$FINISH/product-objects.tsv" ] || [ ! -r "$FINISH/objects.sha256" ]; then
        refuse "$FINISH is not one of this script's dump directories." \
               "  missing: product-objects.tsv or objects.sha256" \
               "Nothing was deleted."
    fi
# <<< guard: finish-dir-valid
    FINISH="$(cd "$FINISH" && pwd)"
    LISTED_SHA="$(tr -d '[:space:]' < "$FINISH/objects.sha256")"
    STATUS=0
    OUT="$(api_python_dump "$FINISH" delete-objects --database "$DATABASE" --bucket "$BUCKET" \
        --objects-file /dump/product-objects.tsv --objects-sha256 "$LISTED_SHA")" || STATUS=$?
    printf '%s\n' "$OUT"
    [ "$STATUS" -ne 3 ] || refuse "the object deletion was refused (reason above). Nothing was deleted."
    [ "$STATUS" -eq 0 ] || fail "the object deletion failed (status $STATUS); run --finish-objects again."
    echo "purge-product-data.sh: done."
    exit 0
fi

# --- 2. the preflight: read-only, inside the api image ----------------------------------
STATUS=0
PLAN_OUT="$(api_python plan --database "$DATABASE" --bucket "$BUCKET" "${FLAGS[@]+"${FLAGS[@]}"}" \
    "${DRY_FLAG[@]+"${DRY_FLAG[@]}"}")" || STATUS=$?
printf '%s\n' "$PLAN_OUT"
PLAN_SHA="$(parse plan-sha256 "$PLAN_OUT")"
NOTHING="$(parse nothing-to-purge "$PLAN_OUT")"
DB_BYTES="$(parse database-bytes "$PLAN_OUT")"
OBJ_BYTES="$(parse product-object-bytes "$PLAN_OUT")"
# >>> guard: preflight-ran
# A preflight that refused or could not read does not get to continue, and a dry run that could
# not count does not get to exit 0 (reset.sh `rehearsal-counted`: a screen with no numbers is the
# untruth `D-24` is about, in a different costume).
if [ "$STATUS" -eq 3 ]; then
    refuse "the preflight refused (reason above)." "Nothing was changed."
fi
if [ "$STATUS" -ne 0 ]; then
    fail "the preflight could not complete (status $STATUS)." "Nothing was changed. Is the stack up?"
fi
if ! printf '%s' "$PLAN_SHA" | grep -Eq '^[0-9a-f]{64}$' || { [ "$NOTHING" != yes ] && [ "$NOTHING" != no ]; }; then
    fail "the preflight printed no plan digest." "Nothing was changed."
fi
# <<< guard: preflight-ran

if [ "$DRY_RUN" = yes ]; then
    echo
    echo "purge-product-data.sh: --dry-run. NOTHING ABOVE WAS CHANGED."
    echo "purge-product-data.sh: a real run would stop the worker, write a verified dump (database,"
    echo "purge-product-data.sh: product objects' bytes and attributes, product-objects.tsv) under"
    echo "purge-product-data.sh: $DUMP_ROOT, and only then purge."
    exit 0
fi

# Idempotent: a second run finds nothing, says so, and writes nothing -- not even a dump.
if [ "$NOTHING" = yes ]; then
    echo
    echo "purge-product-data.sh: nothing to purge. Nothing was dumped and nothing was changed."
    exit 0
fi

# --- 3. the dump -------------------------------------------------------------------------
mkdir -p "$DUMP_ROOT"
DUMP_ROOT="$(cd "$DUMP_ROOT" && pwd)"

# >>> guard: dump-has-room
# The dump is a full `pg_dump` (the corpus rides along, so `reset.sh --restore` of it is whole)
# plus the product objects. It is smaller than the database, so the database's size plus the
# objects' bytes plus a margin is the safe side of "will it fit".
AVAIL_KB="$(df -Pk "$DUMP_ROOT" | awk 'NR==2 {print $4}')"
NEED_KB=$(( (DB_BYTES + OBJ_BYTES) / 1024 + 262144 ))
if [ "${AVAIL_KB:-0}" -lt "$NEED_KB" ]; then
    refuse "$DUMP_ROOT has ${AVAIL_KB:-0} KiB free; the dump may need up to $NEED_KB KiB." \
           "  database ${DB_BYTES} bytes + product objects ${OBJ_BYTES} bytes + 256 MiB margin" \
           "Free space or point ALPHA_DUMP_ROOT at a larger volume. Nothing was changed."
fi
# <<< guard: dump-has-room

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DUMP_DIR="$DUMP_ROOT/$CONFIGURED_INSTANCE-purge-$STAMP"
mkdir -p "$DUMP_DIR"
echo "purge-product-data.sh: dumping into $DUMP_DIR"

# The worker writes on its own (registry heartbeat, claims). It is stopped before the dump so the
# dump, the plan and the purge describe one state, and started again by `cleanup` whatever happens.
if [ "$WORKER_DECLARED" = yes ]; then
    echo "purge-product-data.sh: stopping the worker service"
    compose stop worker
    WORKER_STOPPED=yes
fi

compose exec -T postgres pg_dump --format=custom --no-owner --no-privileges \
    --username "$CONFIGURED_USER" --dbname "$DATABASE" > "$DUMP_DIR/database.dump"
printf '%s\n' "$PLAN_OUT" > "$DUMP_DIR/plan.txt"

SNAP_STATUS=0
SNAP_OUT="$(api_python_dump "$DUMP_DIR" snapshot-objects --database "$DATABASE" --bucket "$BUCKET" \
    --dump-dir /dump "${FLAGS[@]+"${FLAGS[@]}"}")" || SNAP_STATUS=$?
printf '%s\n' "$SNAP_OUT"
[ "$SNAP_STATUS" -ne 3 ] || refuse "the object copy was refused (reason above)." "Nothing was changed."
[ "$SNAP_STATUS" -eq 0 ] || fail "the object copy failed (status $SNAP_STATUS)." "Nothing was changed."
SNAP_PLAN="$(parse plan-sha256 "$SNAP_OUT")"
OBJECTS_SHA="$(parse objects-sha256 "$SNAP_OUT")"

# --- 4. verify the dump BEFORE anything is destroyed -------------------------------------
# >>> guard: dump-verified
if [ ! -s "$DUMP_DIR/database.dump" ]; then
    refuse "the dump at $DUMP_DIR/database.dump is empty." \
           "Nothing was changed. An empty file is not a backup."
fi
# Read back through the STACK'S OWN postgres image, not a host `pg_restore`.
# `--list` reads only the archive's table of contents. A custom dump cut short can pass it and
# fail on expansion (measured by the cancelled cleanup branch: a final byte removed gave
# `--list` exit 0), so the second read expands every data block to a null sink.
if ! compose exec -T postgres pg_restore --list < "$DUMP_DIR/database.dump" >/dev/null 2>&1; then
    refuse "the dump at $DUMP_DIR/database.dump could not be read back." \
           "Nothing was changed. A dump nobody read is not a backup."
fi
if ! compose exec -T postgres pg_restore --file=- < "$DUMP_DIR/database.dump" >/dev/null 2>&1; then
    refuse "the dump at $DUMP_DIR/database.dump lists but does not expand (truncated?)." \
           "Nothing was changed."
fi
for required in "$DUMP_DIR/objects.attrs" "$DUMP_DIR/objects" "$DUMP_DIR/product-objects.tsv"; do
    if [ ! -e "$required" ]; then
        refuse "the dump is missing $required." "Nothing was changed."
    fi
done
echo "purge-product-data.sh: dump verified -- database.dump listed and expanded, objects copied"
# <<< guard: dump-verified

# >>> guard: plan-unchanged
# The plan the operator read, the plan the dump was taken for and the plan the object copy saw are
# one SHA-256, or something wrote in between and the dump is not of what is about to be purged.
if [ "$SNAP_PLAN" != "$PLAN_SHA" ]; then
    refuse "the product data changed while the dump was taken." \
           "  preflight plan : $PLAN_SHA" \
           "  after the dump : ${SNAP_PLAN:-<none>}" \
           "Nothing was changed. Stop api/web/worker and run it again."
fi
# <<< guard: plan-unchanged
printf '%s\n' "$OBJECTS_SHA" > "$DUMP_DIR/objects.sha256"

# --- 5. the transaction ------------------------------------------------------------------
echo "purge-product-data.sh: purging in one transaction"
APPLY_STATUS=0
APPLY_OUT="$(api_python_dump "$DUMP_DIR" apply --database "$DATABASE" --bucket "$BUCKET" \
    --expect-plan "$PLAN_SHA" --objects-file /dump/product-objects.tsv \
    "${FLAGS[@]+"${FLAGS[@]}"}")" || APPLY_STATUS=$?
printf '%s\n' "$APPLY_OUT"
[ "$APPLY_STATUS" -ne 3 ] || refuse "the purge was refused and rolled back (reason above)." \
    "Nothing was changed. The dump at $DUMP_DIR is harmless to keep."
[ "$APPLY_STATUS" -eq 0 ] || fail "the purge transaction failed (status $APPLY_STATUS) and was rolled back." \
    "Nothing was changed. The dump at $DUMP_DIR is harmless to keep."

# --- 6. only after COMMIT: the objects, by exact key from the dumped list -----------------
echo "purge-product-data.sh: the database part is committed; deleting the product objects"
DEL_STATUS=0
DEL_OUT="$(api_python_dump "$DUMP_DIR" delete-objects --database "$DATABASE" --bucket "$BUCKET" \
    --objects-file /dump/product-objects.tsv --objects-sha256 "$OBJECTS_SHA")" || DEL_STATUS=$?
printf '%s\n' "$DEL_OUT"
if [ "$DEL_STATUS" -ne 0 ]; then
    fail "THE DATABASE PART IS COMMITTED but the objects were not all deleted (status $DEL_STATUS)." \
         "Finish with: $0 --database $DATABASE --bucket $BUCKET --finish-objects $DUMP_DIR" \
         "The dump is at $DUMP_DIR"
fi

echo
echo "purge-product-data.sh: done. The dump is at $DUMP_DIR"
echo "purge-product-data.sh: put it back -- BOTH halves, with the object attributes -- with"
echo "  $HERE/reset.sh --database $DATABASE --bucket $BUCKET --restore $DUMP_DIR"
echo "purge-product-data.sh: that restore replaces EVERY table with the dump's copy (accounts and"
echo "purge-product-data.sh: norm corpus as of the dump, too), re-attaches the product objects, raises"
echo "purge-product-data.sh: token_epoch on every account and names any account on a default password."
echo "purge-product-data.sh: run it again to check: it reports nothing to purge."
