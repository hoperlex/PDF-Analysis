#!/usr/bin/env bash
# `T-5` -- the wipe, and it dumps before it drops.
#
# `R-4` is why this is load-bearing rather than tidy: the owner ruled on 2026-09-17 that
# **real client documents may be uploaded and must be wiped at the end of the pilot**. So
# this script destroys real data on purpose, and every line of it is written on the
# assumption that the person running it is tired.
#
#   infra/deploy/reset.sh --database <name> --bucket <name> --dry-run
#   infra/deploy/reset.sh --database <name> --bucket <name> --yes-destroy-everything
#
# `T-4`: this is a script and not a `make` target. `OD-16` makes a tenth root target an
# FF-01 freeze-break needing an explicit break record, and nothing here needs one.
#
# ORDER, AND WHY IT IS THE ORDER:
#
#   1. every guard, before any connection is opened;
#   2. `pg_dump` and a full bucket mirror into a fresh timestamped directory;
#   3. **the dump is verified** -- `pg_restore --list` must read it and the mirror must
#      have the object count the live bucket had. A dump that was never read back is not a
#      backup, it is a file;
#   4. only then: drop and recreate the schema, re-run the migrations, purge the bucket and
#      re-initialise it private.
#
# THE TARGET IS ALWAYS THIS STACK. Every destructive step runs through
# `docker compose -f compose.server.yml`, against the project `ALPHA_INSTANCE` names, so a
# `DATABASE_URL` pointing somewhere else cannot be reached from here even if one is
# exported. That is the second half of "a stale environment cannot point it at something
# else"; the typed names below are the first.
#
# GUARDS ARE DELIMITED BY MARKERS -- `# >>> guard: <name>` / `# <<< guard: <name>`.
# `tests/integration/composition/test_reset_script_refusals.py` reads those markers,
# deletes ONE guard block from a copy of this file and shows that the copy no longer
# refuses. A guard that cannot be shown to fail is not evidence, and on a wipe it is an
# expensive kind of nothing. Do not remove a marker without removing its test.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$HERE/compose.server.yml"
ENV_FILE="${ALPHA_ENV_FILE:-$HERE/env/alpha.env}"
DUMP_ROOT="${ALPHA_DUMP_ROOT:-$HERE/dumps}"

DATABASE=""
BUCKET=""
DESTROY=no
DRY_RUN=no

refuse() {
    printf 'reset.sh: REFUSED: %s\n' "$1" >&2
    shift
    [ "$#" -eq 0 ] || printf '  %s\n' "$@" >&2
    exit 3
}

usage() {
    cat >&2 <<'USAGE'
usage: reset.sh --database <name> --bucket <name> (--dry-run | --yes-destroy-everything)

  --database <name>          the database this wipe is FOR. Must equal the configured one.
  --bucket <name>            the bucket this wipe is FOR. Must equal the configured one.
  --dry-run                  print what would be deleted. Touches nothing.
  --yes-destroy-everything   actually do it, after dumping and verifying the dump.
  --env-file <path>          default: infra/deploy/env/alpha.env
USAGE
    exit 2
}

# >>> guard: known-options
# An unrecognised option is refused rather than ignored. `--dryrun` silently ignored would
# run the destructive path with the operator believing they had asked for a rehearsal.
while [ "$#" -gt 0 ]; do
    case "$1" in
        --database) DATABASE="${2:-}"; shift 2 ;;
        --bucket) BUCKET="${2:-}"; shift 2 ;;
        --env-file) ENV_FILE="${2:-}"; shift 2 ;;
        --dry-run) DRY_RUN=yes; shift ;;
        --yes-destroy-everything) DESTROY=yes; shift ;;
        -h|--help) usage ;;
        *) refuse "unrecognised option: $1" \
                  "Nothing was read and nothing was touched. Run --help." ;;
    esac
done
# <<< guard: known-options

# >>> guard: destructive-flag
# Neither flag means no intent was expressed. The default of a wipe is to do nothing.
if [ "$DESTROY" = no ] && [ "$DRY_RUN" = no ]; then
    refuse "no --yes-destroy-everything and no --dry-run." \
           "This script drops a schema and empties a bucket. It will not infer that from" \
           "an absent argument. Rehearse with --dry-run first."
fi
# <<< guard: destructive-flag

# >>> guard: one-mode
# Both flags at once is an operator who does not know which one they are getting.
if [ "$DESTROY" = yes ] && [ "$DRY_RUN" = yes ]; then
    refuse "--dry-run and --yes-destroy-everything were both given." \
           "One of them is a rehearsal and one of them is not. Choose."
fi
# <<< guard: one-mode

# >>> guard: names-required
if [ -z "$DATABASE" ] || [ -z "$BUCKET" ]; then
    refuse "--database and --bucket are both required, even for --dry-run." \
           "Typing the target is the point: it is what makes a wipe of the wrong instance" \
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

# Read the configured instance as DATA. The file is never sourced: it is the same shape the
# Makefile refuses to execute, and for the same reason.
configured() {
    sed -n "s/^[[:space:]]*\(export[[:space:]]\+\)\?$1=//p" "$ENV_FILE" | tail -1 \
        | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/"
}

CONFIGURED_DB="$(configured POSTGRES_DB)"
CONFIGURED_BUCKET="$(configured S3_BUCKET)"
CONFIGURED_INSTANCE="$(configured ALPHA_INSTANCE)"
CONFIGURED_USER="$(configured POSTGRES_USER)"

# >>> guard: instance-configured
if [ -z "$CONFIGURED_INSTANCE" ] || [ -z "$CONFIGURED_DB" ] || [ -z "$CONFIGURED_BUCKET" ]; then
    refuse "$ENV_FILE names no ALPHA_INSTANCE, POSTGRES_DB or S3_BUCKET." \
           "  ALPHA_INSTANCE: ${CONFIGURED_INSTANCE:-<unset>}" \
           "  POSTGRES_DB   : ${CONFIGURED_DB:-<unset>}" \
           "  S3_BUCKET     : ${CONFIGURED_BUCKET:-<unset>}" \
           "A half-configured environment is not the alpha instance."
fi
# <<< guard: instance-configured

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
           "script will not wipe one against the other's configuration."
fi
# <<< guard: bucket-matches

# >>> guard: compose-file-present
if [ ! -r "$COMPOSE_FILE" ]; then
    refuse "$COMPOSE_FILE is missing." \
           "Every destructive step runs through it; without it this script has no target" \
           "it is allowed to reach."
fi
# <<< guard: compose-file-present

compose() { docker compose --env-file "$ENV_FILE" --file "$COMPOSE_FILE" "$@"; }

mc_run() {
    # A one-off mc container on the stack's own network. `--entrypoint sh` because the
    # s3-init service's entrypoint runs bucket-init.sh and exits.
    compose run --rm --no-deps --entrypoint sh "$@"
}

MC_ALIAS='mc --quiet alias set local http://s3:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null'

echo "reset.sh: instance   $CONFIGURED_INSTANCE"
echo "reset.sh: database   $DATABASE"
echo "reset.sh: bucket     $BUCKET"

if [ "$DRY_RUN" = yes ]; then
    echo
    echo "reset.sh: --dry-run. NOTHING BELOW IS DELETED."
    echo
    echo "-- tables that would be dropped with schema public --"
    compose exec -T postgres psql --quiet --no-align --tuples-only \
        --username "$CONFIGURED_USER" --dbname "$DATABASE" \
        --command "SELECT table_name || '  (' || COALESCE((SELECT n_live_tup FROM pg_stat_user_tables s WHERE s.relname = t.table_name), 0) || ' rows)' FROM information_schema.tables t WHERE table_schema = 'public' ORDER BY table_name" \
        || echo "  (could not read the schema; is the stack up?)"
    echo
    echo "-- objects that would be purged from the bucket --"
    mc_run s3-init -c "$MC_ALIAS; mc --quiet ls --recursive \"local/$BUCKET\" | tail -n 40; echo \"  total: \$(mc --quiet ls --recursive \"local/$BUCKET\" | wc -l) objects\"" \
        || echo "  (could not read the bucket; is the stack up?)"
    echo
    echo "reset.sh: a real run would first write a dump under $DUMP_ROOT,"
    echo "reset.sh: verify it, and only then drop and purge."
    exit 0
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DUMP_DIR="$DUMP_ROOT/$CONFIGURED_INSTANCE-$STAMP"
mkdir -p "$DUMP_DIR/objects"
echo "reset.sh: dumping into $DUMP_DIR"

# --- 2. dump -----------------------------------------------------------------------
compose exec -T postgres pg_dump --format=custom --no-owner --no-privileges \
    --username "$CONFIGURED_USER" --dbname "$DATABASE" > "$DUMP_DIR/database.dump"

LIVE_OBJECTS="$(mc_run s3-init -c "$MC_ALIAS; mc --quiet ls --recursive \"local/$BUCKET\" | wc -l" | tr -d '\r[:space:]')"
mc_run -v "$DUMP_DIR/objects:/out" s3-init \
    -c "$MC_ALIAS; mc --quiet mirror --overwrite \"local/$BUCKET\" /out >/dev/null; chmod -R a+rX /out" \
    >/dev/null

# --- 3. verify the dump BEFORE anything is destroyed --------------------------------
# >>> guard: dump-verified
if [ ! -s "$DUMP_DIR/database.dump" ]; then
    refuse "the dump at $DUMP_DIR/database.dump is empty." \
           "Nothing has been dropped. An empty file is not a backup."
fi
# Read back through the STACK'S OWN postgres image, not a host `pg_restore`: the host may
# have none, or a version too old for this dump's format, and "the tool was missing" must
# never be indistinguishable from "the dump is fine".
if ! compose exec -T postgres pg_restore --list /dev/stdin < "$DUMP_DIR/database.dump" >/dev/null 2>&1; then
    refuse "the dump at $DUMP_DIR/database.dump could not be read back." \
           "Nothing has been dropped. A dump nobody read is not a backup."
fi
MIRRORED="$(find "$DUMP_DIR/objects" -type f | wc -l | tr -d '[:space:]')"
if [ "${LIVE_OBJECTS:-x}" != "$MIRRORED" ]; then
    refuse "the bucket mirror is incomplete." \
           "  objects in $BUCKET : ${LIVE_OBJECTS:-<unknown>}" \
           "  files mirrored     : $MIRRORED" \
           "Nothing has been purged. R-4 says these may be real client documents."
fi
echo "reset.sh: dump verified -- database.dump readable, $MIRRORED/$LIVE_OBJECTS objects mirrored"
# <<< guard: dump-verified

# --- 4. and only now, destroy -------------------------------------------------------
echo "reset.sh: dropping and recreating schema public in $DATABASE"
compose exec -T postgres psql --quiet --username "$CONFIGURED_USER" --dbname "$DATABASE" \
    --command "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO \"$CONFIGURED_USER\";"

echo "reset.sh: re-running migrations to head"
compose run --rm migrate >/dev/null

echo "reset.sh: purging and re-initialising bucket $BUCKET"
mc_run s3-init -c "$MC_ALIAS; mc --quiet rm --recursive --force \"local/$BUCKET\" >/dev/null 2>&1 || true" >/dev/null
# Re-initialise through the SAME script the stack initialises with, so a reset instance and
# a fresh one are the same instance. In particular the bucket is private again.
compose run --rm s3-init

echo
echo "reset.sh: done. The dump is at $DUMP_DIR"
echo "reset.sh: restore with"
echo "  docker compose --env-file $ENV_FILE --file $COMPOSE_FILE exec -T postgres \\"
echo "    pg_restore --clean --if-exists --no-owner --username $CONFIGURED_USER \\"
echo "    --dbname $DATABASE < $DUMP_DIR/database.dump"
