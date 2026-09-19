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
RESTORE=""

refuse() {
    printf 'reset.sh: REFUSED: %s\n' "$1" >&2
    shift
    [ "$#" -eq 0 ] || printf '  %s\n' "$@" >&2
    exit 3
}

usage() {
    cat >&2 <<'USAGE'
usage: reset.sh --database <name> --bucket <name>
                (--dry-run | --yes-destroy-everything | --restore <dump directory>)

  --database <name>          the database this acts on. Must equal the configured one.
  --bucket <name>            the bucket this acts on. Must equal the configured one.
  --dry-run                  print what would be deleted. Touches nothing.
  --yes-destroy-everything   actually do it, after dumping and verifying the dump.
  --restore <dir>            put one of this script's own dumps back, both halves.
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
        --restore) RESTORE="${2:-}"; shift 2 ;;
        -h|--help) usage ;;
        *) refuse "unrecognised option: $1" \
                  "Nothing was read and nothing was touched. Run --help." ;;
    esac
done
# <<< guard: known-options

# >>> guard: destructive-flag
# Neither flag means no intent was expressed. The default of a wipe is to do nothing.
if [ "$DESTROY" = no ] && [ "$DRY_RUN" = no ] && [ -z "$RESTORE" ]; then
    refuse "no --yes-destroy-everything and no --dry-run." \
           "This script drops a schema and empties a bucket. It will not infer that from" \
           "an absent argument. Rehearse with --dry-run first."
fi
# <<< guard: destructive-flag

# >>> guard: one-mode
# Both flags at once is an operator who does not know which one they are getting.
modes=0
[ "$DESTROY" = yes ] && modes=$((modes + 1))
[ "$DRY_RUN" = yes ] && modes=$((modes + 1))
[ -n "$RESTORE" ] && modes=$((modes + 1))
if [ "$modes" -gt 1 ]; then
    refuse "--dry-run, --yes-destroy-everything and --restore were both given." \
           "They are three different things to do to one instance. Choose one."
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

if [ -n "$RESTORE" ]; then
# >>> guard: restore-complete
    # Both halves or neither. A restore that put the rows back and left the bytes behind
    # would leave an instance that lists a document and cannot serve it, which is worse
    # than one that is empty: it looks recovered.
    for required in "$RESTORE/database.dump" "$RESTORE/objects.attrs" "$RESTORE/objects"; do
        if [ ! -e "$required" ]; then
            refuse "$RESTORE is not one of this script's dumps." \
                   "  missing: $required" \
                   "A dump is a database dump, an object mirror and the object metadata" \
                   "that goes with it. Nothing has been changed."
        fi
    done
# <<< guard: restore-complete
    echo "reset.sh: restoring from $RESTORE"
    compose exec -T postgres pg_restore --clean --if-exists --no-owner \
        --username "$CONFIGURED_USER" --dbname "$DATABASE" < "$RESTORE/database.dump"
    # `mc mirror` alone is NOT a restore, and this was measured rather than assumed: the
    # bytes come back with no user metadata and `Content-Type: application/octet-stream`,
    # and the storage adapter then refuses the object with `validation_failed` on
    # `content-sha256` -- "recorded on every object this adapter publishes"
    # (`storage/s3.py`, `_META_SHA256`). An instance restored that way lists a document
    # and 422s on its bytes. So each object goes back with its attributes reattached.
    #
    # ALL FIVE of them (`D-17`). Until wave 18 this line reattached `content-sha256` and
    # `Content-Type` -- the two a READ consults -- and dropped `blob-id`, `blob-role` and
    # `content-size`. Wave 14 verified the restore by reading an object back, got its
    # bytes, and closed. `blob-role` is consulted only by a WRITE: `publish` compares the
    # recorded role and media type before accepting the same bytes again, so every later
    # upload of a restored document answered `409` / `BlobAttributeConflictError` while the
    # identical bytes on a clean stack gave `201`. A restore is proved by writing to the
    # restored instance, not by reading from it.
    restore_objects='
        while IFS="	" read -r key id role sha size ctype; do
            [ -n "$key" ] || continue
            mc --quiet cp --attr "blob-id=$id;blob-role=$role;content-sha256=$sha;content-size=$size;Content-Type=$ctype" \
                "/dump/objects/$key" "local/$S3_BUCKET/$key" >/dev/null
        done < /dump/objects.attrs
        echo "  reset.sh: restored $(wc -l < /dump/objects.attrs) objects"'
    mc_run -v "$RESTORE:/dump:ro" s3-init -c "$MC_ALIAS; $restore_objects"
    echo "reset.sh: restored. Verify with a read of one document version through the API."
    exit 0
fi

# THE ROW COUNTS ARE COUNTED, NOT ESTIMATED -- `D-24`, and it is the screen an operator
# reads BEFORE agreeing to destroy real client documents.
#
# Until this commit the column headed "rows" was `pg_stat_user_tables.n_live_tup`, which is
# an ASYNCHRONOUS ESTIMATE the statistics collector maintains, not a count. Measured on this
# stack at `313e753`, on a database holding five projects, a document, a version, a manifest
# entry and a blob:
#
#   * in one psql session, immediately after a committed INSERT: `count(*)` said 5 and
#     `n_live_tup` said 4 -- the shape `W21-CERT` reported as "(2 rows) where the truth
#     was 4";
#   * with the statistics not yet collected -- what a freshly written database is, and what
#     `pg_stat_reset()` and a crash-recovered server both reproduce exactly -- EVERY table
#     printed `(0 rows)` while all of that data was there.
#
# The bucket half of this same screen is exact, so the database half read as though it were
# too. An operator shown `(0 rows)` may reasonably conclude there is nothing to lose, and
# `R-4` says the thing they would be agreeing to destroy is real client documents.
#
# WHAT IT COSTS, MEASURED ON THIS STACK rather than reasoned about. `count(*)` is a scan per
# table and seventeen of them are not free. Three runs at each size, wall clock of the whole
# `docker exec` + psql round trip:
#
#   database                       exact            estimate
#   the pilot-sized one (34 rows)  0.16-0.19 s      0.16-0.17 s
#   one table at 1,000,000 rows    0.17-0.19 s      0.15-0.16 s
#   one table at 10,000,000 rows   0.32-0.47 s      0.15-0.17 s
#
# So it is linear in rows and, at every size a pilot will reach, the difference is smaller
# than the round trip that carries it. Ten million rows buys about two tenths of a second.
# That is the whole price of the screen telling the truth, and it is worth saying out loud
# rather than leaving the reader to assume either that it is free or that it is ruinous.
#
# `query_to_xml` is how one statement counts a table whose name it does not know until it
# reads it: `format(%I)` quotes the identifier, so a table name is never concatenated into
# SQL. The total line is the bucket half's `  total: N objects` in the other half's units --
# the two halves of the screen now answer in the same way and with the same authority.
COUNT_ROWS_SQL="
WITH counts AS (
    SELECT t.table_name AS name,
           (xpath('/row/c/text()', query_to_xml(
               format('SELECT count(*) AS c FROM %I.%I', t.table_schema, t.table_name),
               false, true, '')))[1]::text::bigint AS n
      FROM information_schema.tables t
     WHERE t.table_schema = 'public'
)
SELECT line FROM (
    SELECT 1 AS ord, name AS key, name || '  (' || n || ' rows)' AS line FROM counts
    UNION ALL
    SELECT 2, '', '  total: ' || COALESCE(sum(n), 0) || ' rows in ' || count(*) || ' tables'
      FROM counts
) ordered ORDER BY ord, key"

if [ "$DRY_RUN" = yes ]; then
    echo
    echo "reset.sh: --dry-run. NOTHING BELOW IS DELETED."
    echo
    echo "-- tables that would be dropped with schema public --"
    COUNTED="$(compose exec -T postgres psql --quiet --no-align --tuples-only \
        --username "$CONFIGURED_USER" --dbname "$DATABASE" \
        --command "$COUNT_ROWS_SQL" 2>&1 || true)"
# >>> guard: rehearsal-counted
    # A rehearsal that could not count does not get to exit 0. The old screen printed
    # "(could not read the schema; is the stack up?)", kept going and exited 0 -- and an
    # operator who has just read a list of tables with no numbers beside them, followed by
    # an exact bucket listing and a calm closing sentence, has been told the same untruth
    # `D-24` is about in a different costume. The total line is the evidence the count ran
    # to the end: a psql that died part way through prints rows and no total.
    if ! printf '%s\n' "$COUNTED" | grep -q '^  total: '; then
        printf '%s\n' "$COUNTED" >&2
        refuse "the rehearsal could not count what is in $DATABASE." \
               "Nothing was touched -- a rehearsal reads and never writes. But this screen" \
               "is what you would agree to a wipe on, so it refuses rather than showing you" \
               "a table list with no numbers beside it. Is the stack up?"
    fi
# <<< guard: rehearsal-counted
    printf '%s\n' "$COUNTED"
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
# The bytes are only two thirds of an object. See object_attrs.py for the third.
mc_run s3-init -c "$MC_ALIAS; mc --json stat --recursive \"local/$BUCKET\"" \
    > "$DUMP_DIR/objects.stat.json"
compose run --rm --no-deps --user root \
    -v "$DUMP_DIR:/dump" -v "$HERE/object_attrs.py:/object_attrs.py:ro" \
    --entrypoint python api /object_attrs.py /dump

# --- 3. verify the dump BEFORE anything is destroyed --------------------------------
# >>> guard: dump-verified
if [ ! -s "$DUMP_DIR/database.dump" ]; then
    refuse "the dump at $DUMP_DIR/database.dump is empty." \
           "Nothing has been dropped. An empty file is not a backup."
fi
# Read back through the STACK'S OWN postgres image, not a host `pg_restore`: the host may
# have none, or a version too old for this dump's format, and "the tool was missing" must
# never be indistinguishable from "the dump is fine".
# `pg_restore --list` with NO filename, reading stdin. Not `--list /dev/stdin`: that is
# what this was written as first, and against a dump `file(1)` calls a valid "PostgreSQL
# custom database dump - v1.16-0" it answered "did not find magic string in file header"
# and refused a wipe that should have proceeded. A guard that refuses a good backup is
# still a bug, and it was found by running this, not by reading it.
if ! compose exec -T postgres pg_restore --list < "$DUMP_DIR/database.dump" >/dev/null 2>&1; then
    refuse "the dump at $DUMP_DIR/database.dump could not be read back." \
           "Nothing has been dropped. A dump nobody read is not a backup."
fi
RECORDED="$(grep -c . "$DUMP_DIR/objects.attrs" 2>/dev/null || echo 0)"
if [ "$RECORDED" != "${LIVE_OBJECTS:-x}" ]; then
    refuse "the object metadata sidecar is short." \
           "  objects in $BUCKET  : ${LIVE_OBJECTS:-<unknown>}" \
           "  attributes recorded : $RECORDED" \
           "Nothing has been purged. Bytes without their attributes restore into an" \
           "instance that lists a document and refuses to serve it."
fi
# Every row carries all six fields, none of them empty: the key, the four user-metadata
# keys `storage/s3.py` `_metadata_for` writes, and `Content-Type`. A row short of one of
# them is `D-17`: the object comes home readable and refuses the next upload of its own
# bytes with a `409`, which is the failure this whole guard exists to make impossible.
#
# THE TAB IS A LITERAL, and that is not a style choice. This test previously read
# `grep -q '^[^\t]*\t\t'`, which GNU grep -- the grep a deploy host has -- does not read as
# a tab at all: `\t` outside a bracket is just `t`, so the pattern looked for the letters
# `tt` and matched nothing. Measured at this commit with GNU grep 3.11 against a sidecar
# row whose digest field was empty: no match, no refusal. It appeared to work only on a
# host whose `grep` is ugrep. A guard written in a regex dialect the target does not speak
# is not a guard, and this one had never been shown able to fail.
TAB="$(printf '\t')"
if grep -qvE "^[^$TAB]+($TAB[^$TAB]+){5}\$" "$DUMP_DIR/objects.attrs" 2>/dev/null; then
    refuse "the object metadata sidecar is incomplete -- a row is missing an attribute." \
           "  expected per row    : key, blob-id, blob-role, content-sha256, content-size, content-type" \
           "  first bad row       : $(grep -nvE "^[^$TAB]+($TAB[^$TAB]+){5}\$" "$DUMP_DIR/objects.attrs" | head -1 | cat -A | head -c 300)" \
           "Nothing has been purged. A restore missing blob-role gives back an object that" \
           "reads correctly and answers 409 to the next upload of its own bytes (D-17)."
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
echo "reset.sh: put it back -- BOTH halves, with the object attributes -- with"
echo "  $0 --database $DATABASE --bucket $BUCKET --restore $DUMP_DIR"
