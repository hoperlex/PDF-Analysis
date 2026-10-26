#!/usr/bin/env bash
# `W54-STAND-COPY-01` -- the COPY KEY's forced command on the stand: the one-off copy
# (`R-88`, `R-93`), the test-data waiver (`R-109`, `R-110`, `W54-FREEZE-01` amendment 2) and
# the way back (`restore-db`, `resume`).
#
#   authorized_keys (the owner installs it; one line):
#     restrict,from="<development host>",command="ALPHA_CHECKOUT=/srv/auditmanager STAND_COPY_DIR=/srv/auditmanager-copy /srv/auditmanager/copy-serve/copy-serve.sh" ssh-ed25519 AAAA... w54-copy
#
# INSTALLED APART FROM THE CHECKOUT. The owner extracts this file, `capacity-probe.sh` and
# `lib/forced-command.sh` and, since `PROD-02`, `lib/proxy-listeners.sh` (the credential gate and the
# "withdraw 443" step `restore-db` ends with) from the candidate's git objects into
# `/srv/auditmanager/copy-serve/` (`DEPLOYMENT_RUNBOOK.md` §13). Everything it acts on comes from `ALPHA_CHECKOUT` -- the
# deployed checkout's compose file, environment and `git HEAD` -- and never from where this
# file lies, so the same script serves a stand whose checkout is an older tree.
#
# The account this key logs into can run `docker`, which is root-equivalent, so THIS SCRIPT
# IS THE BOUNDARY (`W54-PLAN.md` §3.5). It reads one thing from the client --
# `SSH_ORIGINAL_COMMAND` -- and admits exactly these verbs (`<STAMP>` is `YYYYMMDDTHHMMSSZ`):
#
#   capacity                    read-only: free disk per filesystem (Docker data root,
#                               staging, the copy directory, the MinIO volume), RAM, swap,
#                               load, pg_database_size, the MinIO volume's size,
#                               `docker system df`, and the bucket's object count and bytes
#   dump-db                     opens a copy: stops exactly the writers that are running
#                               (`web`, `api`, `worker` when deployed), records which, dumps
#                               PostgreSQL, takes the fingerprint; prints the new <STAMP>
#   inventory-s3 <STAMP>        lists every object in the bucket into the copy
#   fetch <STAMP> db|inventory|record
#                               writes that file to stdout, for `pull-copy.sh`
#   attest <STAMP> <dump-sha256> <restore-report-sha256> publish <sha>|import
#                               binds both digests and a purpose to the open copy; a full
#                               copy's first attestation writes the `real_data` marker
#   attest --test-data          `R-110`: no copy. Stops the writers, takes the fingerprint
#                               and opens a `test_data_waiver` record the importer accepts
#                               in place of a copy. Refused once the marker exists
#   verify-objects <N> [<seed>] reads back a seeded sample of N `available` Blobs against
#                               their recorded size and SHA-256
#   restore-db <STAMP> <sha256> the owner's way back: stops the writers again, checks the
#                               dump's digest, restores it, compares the fingerprint, raises
#                               every account's `token_epoch` (`R-52`, as `reset.sh --restore`
#                               does), asks the credential gate (`PROD-02`: is the published
#                               `admin`/`password` pair valid again?) and, unless it is clean,
#                               recreates the `proxy` WITHOUT the 443 overlay; leaves the
#                               writers stopped and the record open. <STAMP> is
#                               the record's, or -- while a newer dump-db has not completed
#                               -- the previous record's (`record.prev.json`)
#   resume <STAMP>              starts the stopped writers and closes the record, holding
#                               the importer's lock throughout; refused while the importer
#                               holds it
#   status                      read-only: the record, its age, the marker, the import lock,
#                               the deployed tree and this script's SHA-256
#
# CONFIGURATION is the environment the `command="..."` option sets (sshd passes a forced
# command no client environment beyond `AcceptEnv`, and `LC_ALL` is pinned below):
#
#   ALPHA_CHECKOUT               the deployed checkout (default /srv/auditmanager)
#   ALPHA_ENV_FILE               default $ALPHA_CHECKOUT/infra/deploy/env/alpha.env
#   STAND_COPY_DIR               absolute, owner-created, owned by this account, not group-
#                                or world-writable, outside the checkout (default
#                                /srv/auditmanager-copy). Holds `record.json`, while a new
#                                copy is incomplete `record.prev.json`, the marker
#                                `real_data`, `copy.lock` and `<STAMP>/{db.dump,inventory.tsv}`
#   BUNDLE_STAGING               the inbound key's staging; only its `import.lock` is used
#                                (default /srv/auditmanager-bundles)
#   STAND_COPY_MARGIN_BYTES      free space kept beyond the database's size (default 2 GiB)
#   STAND_COPY_WINDOW_SECONDS    how long a copy may stay open before it is attested, and how
#                                long a waiver lasts (default 43200, the importer's 12 h)
#
# THE RECORD (`record.json`, schema in `docs/program/W54-STAND-COPY-01.md` §3) is kept on
# the stand and never enters Git, a report or a chat. Only the latest copy is kept -- but
# only once it is whole: until a new `dump-db` has completed, the previous copy's record
# stays beside it as `record.prev.json`, and its dump stays restorable (`W54-JUDGE-A` F6).
#
# LOCKS (`lib/forced-command.sh`). Every verb that changes anything holds `copy.lock` for
# its whole run, and every rewrite of the record requires it -- the inbound key takes the
# same lock before it turns an open record into an import record. Every verb that could
# change what the importer stands on also holds `<BUNDLE_STAGING>/import.lock` for its
# whole run, so `resume` cannot start the writers under an import that started after its
# check, nor an import start while `resume` runs.
#
# Exit: 0 done; 3 refused (`REFUSED [<guard>]` names which). Guards sit between
# `# >>> guard: <name>` / `# <<< guard: <name>` markers;
# `tests/integration/composition/test_stand_copy_refusals.py` deletes each block from a copy
# of this file and shows the refusal goes with it, and fails when a marker has no case.

set -euo pipefail
export LC_ALL=C
umask 022

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FC_NAME=copy-serve.sh
# shellcheck source=infra/deploy/lib/forced-command.sh
. "$HERE/lib/forced-command.sh"

CHECKOUT="${ALPHA_CHECKOUT:-/srv/auditmanager}"
COMPOSE_FILE="$CHECKOUT/infra/deploy/compose.server.yml"
ENV_FILE="${ALPHA_ENV_FILE:-$CHECKOUT/infra/deploy/env/alpha.env}"
COPY_DIR="${STAND_COPY_DIR:-/srv/auditmanager-copy}"
STAGING="${BUNDLE_STAGING:-/srv/auditmanager-bundles}"
MARGIN_BYTES="${STAND_COPY_MARGIN_BYTES:-2147483648}"
WINDOW_SECONDS="${STAND_COPY_WINDOW_SECONDS:-43200}"

RECORD="$COPY_DIR/record.json"
PREV_RECORD="$COPY_DIR/record.prev.json"
MARKER="$COPY_DIR/real_data"

#: The services that write to PostgreSQL or the bucket on their own. `migrate` and
#: `release-notes` are one-shots that have exited; the proxy writes nothing.
WRITERS=(web api worker)

#: What `attest --test-data` records as the operator's statement (`R-109`).
WAIVER_STATEMENT="The stand holds only generated test data (R-109); no copy is taken (R-110)."

compose() { docker compose --env-file "$ENV_FILE" --file "$COMPOSE_FILE" "$@"; }

# Read the configured instance as DATA, never sourced: deploy.sh's reader.
configured() {
    sed -n "s/^[[:space:]]*\(export[[:space:]]\+\)\?$1=//p" "$ENV_FILE" | tail -1 \
        | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/"
}

# --- configuration guards -------------------------------------------------------------

DEPLOYED_TREE=""
INSTANCE=""
PG_USER=""
PG_DB=""
BUCKET=""

require_checkout() {
    # >>> guard: checkout-present
    case "$CHECKOUT" in
        /*) ;;
        *) fc_refuse checkout-present "ALPHA_CHECKOUT is '$CHECKOUT'; it must be an absolute path." ;;
    esac
    if [ ! -r "$COMPOSE_FILE" ] || ! DEPLOYED_TREE="$(git -C "$CHECKOUT" rev-parse --verify --quiet 'HEAD^{commit}' 2>/dev/null)"; then
        fc_refuse checkout-present "$CHECKOUT is not a deployed checkout: no readable compose file, or git cannot name its HEAD." \
            "ALPHA_CHECKOUT names the checkout deploy-auto deploys (default /srv/auditmanager)."
    fi
    # <<< guard: checkout-present

    # >>> guard: env-file-present
    if [ ! -r "$ENV_FILE" ]; then
        fc_refuse env-file-present "$ENV_FILE is missing or unreadable."
    fi
    # <<< guard: env-file-present

    INSTANCE="$(configured ALPHA_INSTANCE)"
    PG_USER="$(configured POSTGRES_USER)"
    PG_DB="$(configured POSTGRES_DB)"
    BUCKET="$(configured S3_BUCKET)"
    # >>> guard: instance-configured
    if [ -z "$INSTANCE" ] || [ -z "$PG_USER" ] || [ -z "$PG_DB" ] || [ -z "$BUCKET" ]; then
        fc_refuse instance-configured "$ENV_FILE does not name ALPHA_INSTANCE, POSTGRES_USER, POSTGRES_DB and S3_BUCKET."
    fi
    # <<< guard: instance-configured
}

require_copy_dir() {
    local mode
    # >>> guard: copy-dir-absolute
    case "$COPY_DIR" in
        /*) ;;
        *) fc_refuse copy-dir-absolute "STAND_COPY_DIR is '$COPY_DIR'; it must be an absolute path." ;;
    esac
    # <<< guard: copy-dir-absolute

    # >>> guard: copy-dir-directory
    if [ -L "$COPY_DIR" ] || [ ! -d "$COPY_DIR" ]; then
        fc_refuse copy-dir-directory "STAND_COPY_DIR $COPY_DIR is not an existing directory (the owner creates it)."
    fi
    # <<< guard: copy-dir-directory

    # >>> guard: copy-dir-owned
    mode="$(stat -c '%a' "$COPY_DIR")"
    if [ ! -O "$COPY_DIR" ] || [ $(( 8#$mode & 8#022 )) -ne 0 ]; then
        fc_refuse copy-dir-owned "$COPY_DIR must be owned by this account and not group- or world-writable (mode $mode)." \
            "It holds a dump of the client database."
    fi
    # <<< guard: copy-dir-owned

    # >>> guard: copy-dir-outside-checkout
    case "$(cd "$COPY_DIR" && pwd -P)/" in
        "$(cd "$CHECKOUT" 2>/dev/null && pwd -P)"/*)
            fc_refuse copy-dir-outside-checkout "$COPY_DIR is inside the checkout $CHECKOUT." \
                "deploy-auto refuses a checkout with untracked files, and a dump must never be near Git." ;;
    esac
    # <<< guard: copy-dir-outside-checkout
}

# One mutating verb at a time, and the record rewritten by no one else meanwhile: the
# lock is held until this process exits.
take_copy_lock() {
    # >>> guard: copy-lock-free
    if ! fc_take_record_lock "$RECORD"; then
        fc_refuse copy-lock-free "another copy verb, or the inbound key's receive or import, holds $COPY_DIR/copy.lock; nothing was done." \
            "status shows the record."
    fi
    # <<< guard: copy-lock-free
}

# HOLDS the importer's lock until this process exits (`W54-JUDGE-A` F3): a check alone
# would let an import start between it and the writers' start. No staging directory at
# all means no inbound key is installed -- receive-bundle.sh refuses every verb without
# one -- so there is no import and no lock to hold. A staging directory this account
# cannot open the lock in is refused, never passed.
hold_import_lock() {
    local lock="$STAGING/import.lock"
    [ -e "$STAGING" ] || [ -L "$STAGING" ] || return 0
    # >>> guard: import-lock-free
    if ! fc_take_lock "$lock"; then
        fc_refuse import-lock-free "the corpus importer holds $lock, or this account cannot open it; nothing was done." \
            "The writers stay stopped until the import has exited. The inbound key's status shows it."
    fi
    # <<< guard: import-lock-free
}

# --- the record -----------------------------------------------------------------------

#: The record `rec` and `rec_str` read: always `record.json`, except while `restore-db`
#: checks the previous record before it puts that record back in place.
READ_RECORD="$RECORD"

record_exists() { [ -e "$RECORD" ] || [ -L "$RECORD" ]; }
rec() { fc_record_value "$READ_RECORD" "$1"; }
rec_str() { fc_record_string "$READ_RECORD" "$1"; }

# previous_record_is <STAMP>: `record.prev.json` is a record this script wrote, of <STAMP>.
previous_record_is() {
    [ -e "$PREV_RECORD" ] && fc_record_valid "$PREV_RECORD" \
        && [ "$(fc_record_string "$PREV_RECORD" stamp)" = "$1" ]
}

require_record_readable() {
    local record="$RECORD"
    # >>> guard: record-readable
    if ! fc_record_valid "$record"; then
        fc_refuse record-readable "$record is not a copy record this script wrote (record_version 1, canonical layout)." \
            "Nothing was changed. The owner inspects it; this script never repairs it."
    fi
    # <<< guard: record-readable
}

# No copy and no waiver may be open when a new one opens.
require_no_open_record() {
    record_exists || return 0
    require_record_readable
    # >>> guard: record-closed
    if [ "$(rec_str state)" = open ]; then
        fc_refuse record-closed "the record $(rec_str stamp) ($(rec_str kind)) is still open." \
            "Finish it first: resume $(rec_str stamp)"
    fi
    # <<< guard: record-closed
}

# The open record, and it is <STAMP>.
require_open_record() {
    local stamp="$1"
    # >>> guard: record-open
    if ! record_exists; then
        fc_refuse record-open "there is no copy record at $RECORD." "A copy opens with dump-db; a waiver with attest --test-data."
    fi
    # <<< guard: record-open
    require_record_readable
    require_stamp "$stamp"
    # >>> guard: record-is-open
    if [ "$(rec_str state)" != open ]; then
        fc_refuse record-is-open "the record $stamp is closed (closed_at $(rec_str closed_at || echo '?'))." \
            "A closed copy is not reopened by this verb; take a new one with dump-db."
    fi
    # <<< guard: record-is-open
}

require_stamp() {
    local stamp="$1"
    # >>> guard: record-stamp-matches
    if [ "$(rec_str stamp)" != "$stamp" ]; then
        fc_refuse record-stamp-matches "$stamp is not the latest record; that is $(rec_str stamp)." \
            "Only the latest copy is kept; restore-db also takes the previous one while a newer dump-db is incomplete."
    fi
    # <<< guard: record-stamp-matches
}

# A full copy with its dump on disk -- never a waiver, which has none.
require_dump() {
    local stamp="$1" dump
    dump="$(rec dump)"
    # >>> guard: record-has-dump
    if [ "$(rec_str kind)" != copy ] || [ "$dump" = null ] || [ ! -f "$COPY_DIR/$stamp/db.dump" ]; then
        fc_refuse record-has-dump "the record $stamp has no dump on disk (kind $(rec_str kind))." \
            "A test_data_waiver carries no dump; a copy whose dump-db failed has none either."
    fi
    # <<< guard: record-has-dump
}

render_record() {
    # The whole record, in the canonical layout `fc_record_valid` reads. Every argument
    # is a value this script produced; `null` is written as null.
    local file="$1"
    shift
    {
        printf '{\n'
        printf '  "record_version": 1,\n'
        while [ "$#" -gt 2 ]; do
            printf '  "%s": %s,\n' "$1" "$2"
            shift 2
        done
        printf '  "%s": %s\n' "$1" "$2"
        printf '}\n'
    } > "$file.tmp.$$"
    if ! fc_record_install "$file.tmp.$$" "$file"; then
        fc_refuse record-readable "$file could not be written: this process does not hold copy.lock."
    fi
}

set_rec() {
    if ! fc_record_set "$RECORD" "$1" "$2"; then
        fc_refuse record-readable "$RECORD could not be rewritten at '$1'."
    fi
}

json_words() {
    local word out=""
    for word in "$@"; do
        out="$out${out:+, }\"$word\""
    done
    printf '[%s]' "$out"
}

# --- the stack ------------------------------------------------------------------------

declared() { grep -q "^  $1:[[:space:]]*\$" "$COMPOSE_FILE"; }

# is_running <service>: 0 running, 1 not. A docker that does not answer is a refusal, never
# "not running": a quiesce that could not look did not happen.
is_running() {
    local ids
    # >>> guard: docker-answers
    if ! ids="$(compose ps --quiet "$1" 2>/dev/null)"; then
        fc_refuse docker-answers "docker compose ps $1 failed, so whether $1 writes is unknown." \
            "Nothing further was done. Is the daemon up?"
    fi
    # <<< guard: docker-answers
    [ -n "$ids" ]
}

# The writers running now, into PRESENT. Never called inside `$(...)` or `<(...)`: a
# refusal there would end only the subshell and read as "nothing is running".
PRESENT=()
find_running_writers() {
    local writer
    PRESENT=()
    for writer in "${WRITERS[@]}"; do
        if declared "$writer" && is_running "$writer"; then
            PRESENT+=("$writer")
        fi
    done
}

# Stops <writers...> and proves none is running afterwards.
stop_writers() {
    local writer
    [ "$#" -gt 0 ] || return 0
    echo "copy-serve.sh: stopping $*" >&2
    compose stop "$@" >&2 || true
    # >>> guard: writers-stopped
    for writer in "$@"; do
        if is_running "$writer"; then
            fc_refuse writers-stopped "$writer is still running after docker compose stop." \
                "The record stays open. resume $(rec_str stamp 2>/dev/null || echo '<STAMP>') starts what was stopped."
        fi
    done
    # <<< guard: writers-stopped
}

# Every writer the deployed file declares is stopped now. Before inventory, attest and
# the import: a copy is only a copy of a database nobody was writing to.
require_writers_still_stopped() {
    local writer running=()
    for writer in "${WRITERS[@]}"; do
        if declared "$writer" && is_running "$writer"; then
            running+=("$writer")
        fi
    done
    # >>> guard: writers-still-stopped
    if [ "${#running[@]}" -gt 0 ]; then
        fc_refuse writers-still-stopped "${running[*]} is running again since the record was opened." \
            "The fingerprint no longer describes a quiesced database: resume $(rec_str stamp), then open a new copy."
    fi
    # <<< guard: writers-still-stopped
}

psql_stand() {
    compose exec -T postgres psql --quiet --no-align --tuples-only --no-psqlrc \
        --set ON_ERROR_STOP=1 --username "$PG_USER" --dbname "$PG_DB" "$@"
}

# db_scalar <SQL> <ERE the answer must match>
db_scalar() {
    local answer
    # >>> guard: database-answers
    if ! answer="$(psql_stand --command "$1" < /dev/null 2>&1)" || ! [[ $answer =~ ^$2$ ]]; then
        fc_refuse database-answers "PostgreSQL did not answer '$1' as expected." \
            "$(printf '%s' "$answer" | head -n 3)"
    fi
    # <<< guard: database-answers
    printf '%s\n' "$answer"
}

# The fingerprint (`W54-PLAN.md` §3.5): every base table's row count and the SHA-256 of
# its rows, outside the `norm*` and custody families; in `audit_event` and `command_record`
# only the rows whose type is outside `norm_custody.*`; in `blob` only the rows no custody
# admission names. `scripts/stand-copy/restore-test.sh` runs THIS text, extracted from this
# file between its markers, against the restored dump -- one query, two places.
fingerprint_sql() {
    cat <<'SQL'
-- >>> stand-fingerprint-v1
SET TimeZone = 'UTC';
SET DateStyle = 'ISO, YMD';
SET IntervalStyle = 'postgres';
SET extra_float_digits = 1;
SET bytea_output = 'hex';
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT format(
    'SELECT %L || ''|'' || count(*) || ''|'' || encode(sha256(convert_to(coalesce(string_agg(r.t, E''\n'' ORDER BY r.t COLLATE "C"), ''''), ''UTF8'')), ''hex'') FROM (SELECT x::text AS t FROM %I AS x %s) AS r',
    c.relname,
    c.relname,
    CASE
        WHEN c.relname = 'audit_event' THEN 'WHERE x.event_type NOT LIKE ''norm\_custody.%'''
        WHEN c.relname = 'command_record' THEN 'WHERE x.command_type NOT LIKE ''norm\_custody.%'''
        WHEN c.relname = 'blob' AND to_regclass('norm_custody_admission') IS NOT NULL
            THEN 'WHERE NOT EXISTS (SELECT 1 FROM norm_custody_admission AS a WHERE a.blob_id = x.blob_id)'
        ELSE ''
    END)
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = current_schema()
  AND c.relkind IN ('r', 'p')
  AND NOT c.relispartition
  AND c.relname NOT LIKE 'norm%'
ORDER BY c.relname COLLATE "C"
\gexec
COMMIT;
-- <<< stand-fingerprint-v1
SQL
}

FINGERPRINT_JSON=""
take_fingerprint() {
    local lines
    # >>> guard: fingerprint-read
    if ! lines="$(fingerprint_sql | psql_stand 2>&1)" || ! fc_fingerprint_lines_valid "$lines"; then
        fc_refuse fingerprint-read "the fingerprint query did not print one line per table." \
            "$(printf '%s' "$lines" | head -n 3)"
    fi
    # <<< guard: fingerprint-read
    FINGERPRINT_JSON="$(fc_fingerprint_json "$lines")"
}

new_stamp() {
    local stamp
    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    # Two opens in one second would share a stamp; the second waits for the next one.
    while [ -e "$COPY_DIR/$stamp" ] || [ "$(rec_str stamp 2>/dev/null || true)" = "$stamp" ]; do
        sleep 1
        stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    done
    printf '%s\n' "$stamp"
}

# `W54-JUDGE-A` F6: the record a new one is about to replace (closed, or the caller
# refused). A closed copy whose dump is on disk becomes `record.prev.json` and stays
# restorable until the new dump is whole. Any other record -- a waiver, a copy whose
# dump-db failed -- is simply replaced, and an earlier `record.prev.json` is kept.
keep_previous_record() {
    record_exists || return 0
    if [ "$(rec_str kind)" = copy ] && [ "$(rec dump)" != null ] && [ -f "$COPY_DIR/$(rec_str stamp)/db.dump" ]; then
        if ! fc_record_install "$RECORD" "$PREV_RECORD"; then
            fc_refuse record-readable "$RECORD could not be kept as $PREV_RECORD: this process does not hold copy.lock."
        fi
    fi
}

# Opens a record (copy or waiver) BEFORE anything is stopped, so a failure at any later
# step leaves an open record that `resume` can close and whose writers it can restart.
open_record() {
    local stamp="$1" kind="$2" purpose="$3" waiver="$4" present_json
    shift 4
    present_json="$(json_words "$@")"
    keep_previous_record
    render_record "$RECORD" \
        kind "\"$kind\"" \
        stamp "\"$stamp\"" \
        state '"open"' \
        purpose "\"$purpose\"" \
        target_sha null \
        instance "\"$INSTANCE\"" \
        deployed_tree "\"$DEPLOYED_TREE\"" \
        migration_head null \
        opened_at "\"$(fc_now)\"" \
        quiesced_at null \
        writers_present "$present_json" \
        writers_stopped "$present_json" \
        dump null \
        fingerprint null \
        rejected_blob_count null \
        inventory null \
        attestation null \
        waiver "$waiver" \
        real_data_marker "$([ -e "$MARKER" ] && echo true || echo false)" \
        restored_at null \
        closed_at null
}

# Stops the writers present, then fills in what a quiesced database says about itself.
quiesce_and_describe() {
    local present=("$@")
    local head rejected
    stop_writers "${present[@]}"
    set_rec quiesced_at "\"$(fc_now)\""
    # Standalone assignments: under `set -e` a refusal inside the substitution ends the
    # script with its status instead of leaving an empty value behind.
    head="$(db_scalar "SELECT string_agg(version_num, ',' ORDER BY version_num) FROM alembic_version" '[A-Za-z0-9_,]+')"
    rejected="$(db_scalar "SELECT count(*) FROM blob WHERE state = 'rejected'" '[0-9]+')"
    set_rec migration_head "\"$head\""
    set_rec rejected_blob_count "$rejected"
    take_fingerprint
    set_rec fingerprint "$FINGERPRINT_JSON"
}

window_open_since() {
    local since="$1" epoch
    epoch="$(fc_epoch "$since")" || return 1
    [ $(( $(date -u +%s) - epoch )) -le "$WINDOW_SECONDS" ]
}

sha256_of() { sha256sum < "$1" | cut -c1-64; }

free_bytes() { df -B1 --output=avail -- "$1" | tail -n 1 | tr -d ' '; }

# --- verbs ----------------------------------------------------------------------------

verb_capacity() {
    local root volume_avail volume_bytes
    require_checkout
    echo "copy-serve.sh capacity"
    root="$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || true)"
    bash "$HERE/capacity-probe.sh" \
        --path "docker_root=${root:-unknown}" --path "staging=$STAGING" --path "copy_dir=$COPY_DIR"
    echo "pg_database_size_bytes: $(psql_stand --command 'SELECT pg_database_size(current_database())' < /dev/null 2>/dev/null || echo unknown)"
    # The MinIO volume is under the Docker data root, which this account cannot traverse,
    # so the server container measures its own /data (busybox df -P: 1024-byte blocks).
    volume_avail="$(compose exec -T s3 df -P -k /data 2>/dev/null | awk 'NR == 2 { print $4 * 1024 }')"
    volume_bytes="$(compose exec -T s3 du -s -k /data 2>/dev/null | awk 'NR == 1 { print $1 * 1024 }')"
    echo "minio_volume_avail_bytes: ${volume_avail:-unknown}"
    echo "minio_volume_bytes: ${volume_bytes:-unknown}"
    if list_bucket; then
        echo "bucket_objects: $(printf '%s' "$BUCKET_LISTING" | grep -c . || true)"
        echo "bucket_bytes: $(printf '%s\n' "$BUCKET_LISTING" | awk -F'\t' '{ total += $2 } END { printf "%d\n", total }')"
    else
        echo "bucket_objects: unknown"
        echo "bucket_bytes: unknown"
    fi
    echo "docker_system_df:"
    docker system df 2>&1 | sed 's/^/  /'
    echo "need (W54-PLAN.md 3.9, P4): staging >= bundle + dump + 2 GiB; Docker volumes >= objects + db_growth_bytes + 2 GiB"
}

# The bucket, one object per line: `<key>\t<size>\t<etag>`, sorted, into BUCKET_LISTING.
# Read through the stack's own mc image on the stack's network; the credentials stay in
# its environment. Fails (BUCKET_ERROR says why) unless every line was a listed object.
BUCKET_LISTING=""
BUCKET_ERROR=""
list_bucket() {
    local raw
    BUCKET_LISTING=""
    # The program is a literal; the container's own environment supplies the values.
    # shellcheck disable=SC2016
    if ! raw="$(compose run --rm --no-deps -T --entrypoint sh s3-init -c \
            'mc --quiet alias set local http://s3:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null && mc --quiet ls --recursive --json "local/$S3_BUCKET"' \
            < /dev/null 2>&1)"; then
        BUCKET_ERROR="$(printf '%s' "$raw" | head -n 3)"
        return 1
    fi
    if ! BUCKET_LISTING="$(printf '%s\n' "$raw" | awk '
            function member(name, kind,    pattern, value) {
                pattern = kind == "s" ? "\"" name "\":\"[^\"]*\"" : "\"" name "\":[0-9]+"
                if (!match($0, pattern)) { bad = 1; return "" }
                value = substr($0, RSTART + length(name) + 3, RLENGTH - length(name) - 3)
                if (kind == "s") value = substr(value, 2, length(value) - 2)
                return value
            }
            /^[[:space:]]*$/ { next }
            /"status":"success"/ && /"type":"file"/ {
                key = member("key", "s"); size = member("size", "n"); etag = member("etag", "s")
                if (key !~ /^[A-Za-z0-9][A-Za-z0-9._\/-]*$/) bad = 1
                printf "%s\t%s\t%s\n", key, size, etag
                next
            }
            { bad = 1 }
            END { exit bad }' | sort)"; then
        BUCKET_ERROR="$(printf '%s\n' "$raw" | grep -v '"status":"success"' | head -n 3)"
        return 1
    fi
}

verb_dump_db() {
    local stamp present=() writer dump size sha avail need db_size old
    require_checkout
    require_copy_dir
    take_copy_lock
    hold_import_lock
    require_no_open_record

    db_size="$(db_scalar 'SELECT pg_database_size(current_database())' '[0-9]+')"
    # >>> guard: copy-dir-has-room
    avail="$(free_bytes "$COPY_DIR")"
    need=$(( db_size + MARGIN_BYTES ))
    if [ "$avail" -lt "$need" ]; then
        fc_refuse copy-dir-has-room "$COPY_DIR has $avail bytes free; a dump of a $db_size-byte database needs $need with the margin." \
            "Nothing was stopped. capacity shows every filesystem."
    fi
    # <<< guard: copy-dir-has-room

    find_running_writers
    present=("${PRESENT[@]}")

    stamp="$(new_stamp)"
    mkdir -m 700 -- "$COPY_DIR/$stamp"
    open_record "$stamp" copy none null "${present[@]}"
    echo "copy-serve.sh: opened copy $stamp; writers present: ${present[*]:-none}" >&2

    quiesce_and_describe "${present[@]}"

    dump="$COPY_DIR/$stamp/db.dump"
    compose exec -T postgres pg_dump --format=custom --no-owner --no-privileges \
        --username "$PG_USER" --dbname "$PG_DB" > "$dump.partial"
    # >>> guard: dump-readable
    if ! compose exec -T postgres pg_restore --list < "$dump.partial" > /dev/null 2>&1; then
        fc_refuse dump-readable "pg_restore --list cannot read the dump just written." \
            "The record stays open with no dump; resume $stamp restarts the writers."
    fi
    # <<< guard: dump-readable
    mv -f -- "$dump.partial" "$dump"
    chmod 0600 -- "$dump"
    size="$(stat -c '%s' "$dump")"
    sha="$(sha256_of "$dump")"
    set_rec dump "{\"file\": \"db.dump\", \"size_bytes\": $size, \"sha256\": \"$sha\"}"

    # Only the latest copy is kept, and only once the new one is whole: first the previous
    # record, so it never names a dump that is gone, then every older copy.
    rm -f -- "$PREV_RECORD"
    for old in "$COPY_DIR"/*; do
        old="${old##*/}"
        if [[ $old =~ ^${FC_STAMP_ERE}$ ]] && [ "$old" != "$stamp" ]; then
            rm -rf -- "${COPY_DIR:?}/$old"
        fi
    done

    printf 'stamp: %s\n' "$stamp"
    printf 'writers_stopped: %s\n' "${present[*]:-none}"
    printf 'dump_bytes: %s\ndump_sha256: %s\n' "$size" "$sha"
    printf 'fingerprint_sha256: %s\n' "$(fc_json_member "$(rec fingerprint)" sha256)"
    printf 'next: inventory-s3 %s\n' "$stamp"
}

verb_inventory_s3() {
    local stamp="$1" file count bytes sha
    require_checkout
    require_copy_dir
    take_copy_lock
    require_open_record "$stamp"
    require_dump "$stamp"
    require_writers_still_stopped

    # >>> guard: inventory-read
    if ! list_bucket; then
        fc_refuse inventory-read "the bucket listing could not be read whole; no inventory was written." \
            "$BUCKET_ERROR"
    fi
    # <<< guard: inventory-read
    file="$COPY_DIR/$stamp/inventory.tsv"
    printf '%s' "$BUCKET_LISTING" > "$file.partial"
    [ -z "$BUCKET_LISTING" ] || printf '\n' >> "$file.partial"
    mv -f -- "$file.partial" "$file"
    chmod 0600 -- "$file"
    count="$(grep -c . "$file" || true)"
    bytes="$(awk -F'\t' '{ total += $2 } END { printf "%d\n", total }' "$file")"
    sha="$(sha256_of "$file")"
    set_rec inventory "{\"file\": \"inventory.tsv\", \"count\": $count, \"bytes\": $bytes, \"sha256\": \"$sha\"}"
    printf 'objects: %s\nbytes: %s\ninventory_sha256: %s\n' "$count" "$bytes" "$sha"
    printf 'next: pull-copy.sh ... %s, then scripts/stand-copy/restore-test.sh, then attest\n' "$stamp"
}

verb_fetch() {
    local stamp="$1" what="$2" file
    require_copy_dir
    # >>> guard: fetch-record-present
    if ! fc_record_valid "$RECORD"; then
        fc_refuse fetch-record-present "there is no readable copy record at $RECORD."
    fi
    # <<< guard: fetch-record-present
    require_stamp "$stamp"
    case "$what" in
        db) file="$COPY_DIR/$stamp/db.dump" ;;
        inventory) file="$COPY_DIR/$stamp/inventory.tsv" ;;
        record) file="$RECORD" ;;
    esac
    # >>> guard: artifact-present
    if [ -L "$file" ] || [ ! -f "$file" ]; then
        fc_refuse artifact-present "$stamp has no $what yet." "dump-db writes db, inventory-s3 writes inventory."
    fi
    # <<< guard: artifact-present
    cat -- "$file"
}

verb_attest() {
    if [ "$1" = --test-data ]; then
        attest_test_data
        return
    fi
    local stamp="$1" dump_sha="$2" report_sha="$3" purpose="$4" target="${5:-}" first actual inventory
    require_checkout
    require_copy_dir
    take_copy_lock
    hold_import_lock
    require_open_record "$stamp"
    require_dump "$stamp"

    actual="$(sha256_of "$COPY_DIR/$stamp/db.dump")"
    # >>> guard: dump-digest-matches
    if [ "$dump_sha" != "$(fc_json_member "$(rec dump)" sha256)" ] || [ "$dump_sha" != "$actual" ]; then
        fc_refuse dump-digest-matches "the dump SHA-256 given is not the one recorded and on disk." \
            "given $dump_sha; recorded $(fc_json_member "$(rec dump)" sha256); on disk $actual"
    fi
    # <<< guard: dump-digest-matches

    inventory="$(rec inventory)"
    # >>> guard: inventory-taken
    if [ "$inventory" = null ] || [ ! -f "$COPY_DIR/$stamp/inventory.tsv" ] \
        || [ "$(sha256_of "$COPY_DIR/$stamp/inventory.tsv")" != "$(fc_json_member "$inventory" sha256)" ]; then
        fc_refuse inventory-taken "the copy $stamp has no inventory matching its record." "Run inventory-s3 $stamp first."
    fi
    # <<< guard: inventory-taken

    # >>> guard: import-record-stays-import
    if [ "$(rec_str purpose)" = import ] && [ "$purpose" = publish ]; then
        fc_refuse import-record-stays-import "the record $stamp is an import record; it is not rebound to a publication." \
            "resume $stamp, then take a new copy for the publication."
    fi
    # <<< guard: import-record-stays-import

    first=yes
    [ "$(rec attestation)" = null ] || first=no
    # The first attestation, and any import attestation, stands for a quiesced database
    # inside the window. Re-binding a publication (a forward fix after the deploy that
    # restarted the writers) needs neither.
    if [ "$first" = yes ] || [ "$purpose" = import ]; then
        # >>> guard: window-open
        if ! window_open_since "$(rec_str quiesced_at)"; then
            fc_refuse window-open "the copy $stamp was quiesced at $(rec_str quiesced_at || echo '?'), more than $WINDOW_SECONDS s ago." \
                "resume $stamp and take a new copy."
        fi
        # <<< guard: window-open
        require_writers_still_stopped
    fi

    set_rec attestation "{\"dump_sha256\": \"$dump_sha\", \"restore_report_sha256\": \"$report_sha\", \"attested_at\": \"$(fc_now)\"}"
    set_rec purpose "\"$purpose\""
    if [ "$purpose" = publish ]; then
        set_rec target_sha "\"$target\""
    else
        set_rec target_sha null
    fi
    # `W54-FREEZE-01` amendment 2: a full copy is taken because real client data is about
    # to arrive (`R-110`). From its attestation on, no waiver is accepted.
    if [ ! -e "$MARKER" ]; then
        printf 'stamp=%s\nwritten_at=%s\n' "$stamp" "$(fc_now)" > "$MARKER.tmp.$$"
        mv -f -- "$MARKER.tmp.$$" "$MARKER"
    fi
    set_rec real_data_marker true
    printf 'attested: %s purpose %s%s\n' "$stamp" "$purpose" "${target:+ $target}"
    printf 'real_data marker: %s (from now on attest --test-data is refused)\n' "$MARKER"
}

attest_test_data() {
    local stamp present=() writer waiver now
    require_checkout
    require_copy_dir
    take_copy_lock
    hold_import_lock
    # >>> guard: real-data-absent
    if [ -e "$MARKER" ] || [ -L "$MARKER" ]; then
        fc_refuse real-data-absent "the real_data marker exists ($MARKER): a full copy was attested, so R-88 and R-93 apply in full." \
            "A test-data waiver is refused from then on (W54-FREEZE-01 amendment 2). Take a copy: dump-db."
    fi
    # <<< guard: real-data-absent
    require_no_open_record

    find_running_writers
    present=("${PRESENT[@]}")

    stamp="$(new_stamp)"
    now="$(fc_now)"
    waiver="{\"statement\": \"$WAIVER_STATEMENT\", \"attested_at\": \"$now\", \"expires_at\": \"$(date -u -d "@$(( $(fc_epoch "$now") + WINDOW_SECONDS ))" +%Y-%m-%dT%H:%M:%SZ)\"}"
    open_record "$stamp" test_data_waiver import "$waiver" "${present[@]}"
    quiesce_and_describe "${present[@]}"
    printf 'stamp: %s\nkind: test_data_waiver\nwriters_stopped: %s\n' "$stamp" "${present[*]:-none}"
    printf 'fingerprint_sha256: %s\n' "$(fc_json_member "$(rec fingerprint)" sha256)"
    printf 'expires_at: %s\n' "$(fc_json_member "$waiver" expires_at)"
    printf 'next: the inbound key imports; then resume %s\n' "$stamp"
}

# The read-back program, run in the api image with the stack's own storage settings. Each
# input line is `<blob_id> <size_bytes> <sha256>`; each output line is `ok <blob_id>` or
# `<fault> <blob_id> ...`, then one `verified <n> mismatched <m>`. It reads through the
# storage adapter's public surface, so the object-key layout stays the adapter's secret.
verify_objects_program() {
    cat <<'PY'
# >>> verify-objects.py
import hashlib
import sys

from auditmanager.storage import BlobId, S3BlobStore, S3StorageSettings

store = S3BlobStore(S3StorageSettings.from_env())
checked = mismatched = 0
for line in sys.stdin:
    fields = line.split()
    if not fields:
        continue
    blob_id, size, sha256 = fields[0], int(fields[1]), fields[2]
    checked += 1
    try:
        data = store.read(BlobId(blob_id), verify=False)
    except Exception as error:  # every failure to read back is a finding, never a skip
        print(f"unreadable {blob_id} {type(error).__name__}")
        mismatched += 1
        continue
    if len(data) != size:
        print(f"size-mismatch {blob_id} recorded {size} read {len(data)}")
        mismatched += 1
    elif hashlib.sha256(data).hexdigest() != sha256:
        print(f"sha256-mismatch {blob_id}")
        mismatched += 1
    else:
        print(f"ok {blob_id}")
print(f"verified {checked} mismatched {mismatched}")
sys.exit(1 if mismatched or not checked else 0)
# <<< verify-objects.py
PY
}

verb_verify_objects() {
    local count="$1" seed="${2:-}" sample result status=0
    require_checkout
    [ -n "$seed" ] || seed="$(date -u +%Y%m%dt%H%M%S)"
    # >>> guard: sample-read
    if ! sample="$(psql_stand --field-separator ' ' --command \
            "SELECT blob_id, size_bytes, sha256 FROM blob WHERE state = 'available' ORDER BY md5(blob_id || '$seed'), blob_id LIMIT $count" \
            < /dev/null 2>&1)" \
        || printf '%s\n' "$sample" | grep -v '^$' | grep -Evq '^blob_[0-9A-Za-z]+ (0|[1-9][0-9]*) [0-9a-f]{64}$'; then
        fc_refuse sample-read "the Blob sample could not be read from PostgreSQL." "$(printf '%s' "$sample" | head -n 3)"
    fi
    # <<< guard: sample-read
    printf 'seed: %s\nsampled: %s\n' "$seed" "$(printf '%s' "$sample" | grep -c . || true)"
    result="$(printf '%s\n' "$sample" | compose run --rm --no-deps -T --entrypoint python api -c "$(verify_objects_program)" 2>&1)" || status=$?
    printf '%s\n' "$result"
    # >>> guard: objects-match
    if [ "$status" -ne 0 ] || ! printf '%s\n' "$result" | grep -Eq '^verified [1-9][0-9]* mismatched 0$'; then
        fc_refuse objects-match "a sampled object did not read back as recorded (or nothing was sampled)." \
            "$(printf '%s\n' "$result" | grep -Ev '^(ok|verified) ' | head -n 5)"
    fi
    # <<< guard: objects-match
}

verb_restore_db() {
    local stamp="$1" sha="$2" actual present=() writer stopped recorded restored previous=no carried=()
    local revoke_status=0 door_state
    require_checkout
    require_copy_dir
    take_copy_lock
    hold_import_lock
    # `PROD-02`. Checked BEFORE anything is stopped or restored: a restore that cannot ask the gate afterwards
    # would leave the published pair able to sign in on a site whose door nothing can shut.
    # >>> guard: listeners-library-present
    if [ ! -r "$HERE/lib/proxy-listeners.sh" ]; then
        fc_refuse listeners-library-present "$HERE/lib/proxy-listeners.sh is not installed beside this script." \
            "restore-db ends by asking whether the published admin/password pair came back and by closing public" \
            "port 443 if it did (R-146s). The owner extracts that file too (DEPLOYMENT_RUNBOOK.md section 13). Nothing was stopped."
    fi
    # <<< guard: listeners-library-present
    # shellcheck source=infra/deploy/lib/proxy-listeners.sh
    . "$HERE/lib/proxy-listeners.sh"
    # >>> guard: restore-record-present
    if ! record_exists; then
        fc_refuse restore-record-present "there is no copy record, so there is no dump to restore."
    fi
    # <<< guard: restore-record-present
    require_record_readable
    # `W54-JUDGE-A` F6: the previous copy, while the dump-db that replaced its record has
    # not completed. It is checked here exactly as the latest one is, and put back in place
    # only once the digest matches.
    if [ "$(rec_str stamp)" != "$stamp" ] && previous_record_is "$stamp"; then
        previous=yes
        READ_RECORD="$PREV_RECORD"
    fi
    require_stamp "$stamp"
    require_dump "$stamp"
    actual="$(sha256_of "$COPY_DIR/$stamp/db.dump")"
    # >>> guard: dump-digest-matches-restore
    if [ "$sha" != "$(fc_json_member "$(rec dump)" sha256)" ] || [ "$sha" != "$actual" ]; then
        fc_refuse dump-digest-matches-restore "the dump's SHA-256 is not the one given and recorded; nothing was stopped or restored." \
            "given $sha; recorded $(fc_json_member "$(rec dump)" sha256); on disk $actual"
    fi
    # <<< guard: dump-digest-matches-restore

    # The previous record goes back in place, and it inherits every writer the record it
    # replaces had stopped -- a failed dump-db stops them all and starts none.
    if [ "$previous" = yes ]; then
        if [ "$(fc_record_string "$RECORD" state)" = open ]; then
            while IFS= read -r writer; do
                [ -n "$writer" ] && carried+=("$writer")
            done < <(fc_json_words "$(fc_record_value "$RECORD" writers_stopped)")
        fi
        if ! fc_record_install "$PREV_RECORD" "$RECORD"; then
            fc_refuse record-readable "$PREV_RECORD could not be put back as $RECORD: this process does not hold copy.lock."
        fi
        READ_RECORD="$RECORD"
        echo "copy-serve.sh: the previous record $stamp is the record again" >&2
    fi

    # Quiesce AGAIN: a deploy since the copy restarted the writers. The record reopens and
    # remembers every writer it has stopped, so `resume` restarts them all.
    find_running_writers
    present=("${PRESENT[@]}")
    stopped="$(fc_json_words "$(rec writers_stopped)" | tr '\n' ' ')"
    for writer in "${carried[@]}" "${present[@]}"; do
        case " $stopped " in *" $writer "*) ;; *) stopped="$stopped $writer" ;; esac
    done
    # shellcheck disable=SC2086  # the words are writer names this script wrote
    set_rec writers_stopped "$(json_words $stopped)"
    set_rec state '"open"'
    set_rec closed_at null
    stop_writers "${present[@]}"

    echo "copy-serve.sh: restoring $stamp into $PG_DB" >&2
    psql_stand --command "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO \"$PG_USER\";" < /dev/null >&2
    compose exec -T postgres pg_restore --no-owner --no-privileges --exit-on-error --single-transaction \
        --username "$PG_USER" --dbname "$PG_DB" < "$COPY_DIR/$stamp/db.dump" >&2
    set_rec restored_at "\"$(fc_now)\""

    take_fingerprint
    recorded="$(fc_json_member "$(rec fingerprint)" sha256)"
    restored="$(fc_json_member "$FINGERPRINT_JSON" sha256)"
    # >>> guard: fingerprint-restored
    if [ "$restored" != "$recorded" ]; then
        fc_refuse fingerprint-restored "the restored database's fingerprint $restored is not the copy's $recorded." \
            "The writers stay stopped and the record open. The owner decides; do not resume blind."
    fi
    # <<< guard: fingerprint-restored

    # --- `PROD-02`: THE RESTORE TAKES BACK WHAT IT PUT BACK, AND ASKS THE SAME GATE AS A DEPLOY (`R-52`, `R-146s`).
    # AFTER the fingerprint comparison, because raising `token_epoch` changes `app_user` and the comparison is
    # about the database as the dump left it. `pg_restore` brings `app_user` back entire -- password digests,
    # `token_epoch` and `is_default_credential` -- so a dump taken before the forced password change puts the
    # published `admin`/`password` pair back, and a dump taken before a `revoke --everyone` un-revokes. Same
    # statuses as `reset.sh --restore`: 0 revoked something, 1 matched nothing (a dump with no accounts), 2 could
    # not reach the database. The third is a refusal HERE and not a report, because the writers are still
    # stopped: nothing is exposed until `resume`, and `resume` must not follow a restore whose credentials are live.
    compose run --rm --no-deps -T --entrypoint python api \
        -m auditmanager.access.revoke --everyone < /dev/null >&2 || revoke_status=$?
    # >>> guard: credentials-revoked
    if [ "$revoke_status" -ge 2 ]; then
        fc_refuse credentials-revoked "the restored credentials were not revoked (access.revoke --everyone exited $revoke_status)." \
            "The writers stay stopped and the record open. Run it yourself, then resume $stamp:" \
            "docker compose --env-file $ENV_FILE --file $COMPOSE_FILE run --rm --no-deps -T --entrypoint python api -m auditmanager.access.revoke --everyone"
    fi
    # <<< guard: credentials-revoked

    # THE GATE. A finding -- or an answer that could not be had, which after a restore is not "fine" -- recreates
    # ONLY the proxy without the 443 overlay: the site is unreachable from outside until an administrator changes
    # the password through the loopback port (the consequence `R-146s` accepts). A restore never OPENS 443; only a
    # deploy does, after a clean gate.
    listeners_gate_run compose
    printf '%s\n' "$LISTENERS_GATE_OUTPUT" | sed 's/^/gate: /' >&2
    door_state="unchanged (the gate is clean; a restore never opens 443, the next deploy decides)"
    if [ "$LISTENERS_GATE_VERDICT" != clean ]; then
        # >>> guard: https-withheld
        if ! listeners_withhold_https compose "$CHECKOUT/infra/deploy" "$ENV_FILE" "$(configured ALPHA_CERT_NAME)"; then
            fc_refuse https-withheld "the credential gate said $LISTENERS_GATE_VERDICT and public port 443 could not be withdrawn." \
                "The writers stay stopped and the record open. Close it by hand, then resume $stamp:" \
                "docker compose --env-file $ENV_FILE --file $COMPOSE_FILE up -d --force-recreate --no-deps proxy"
        fi
        # <<< guard: https-withheld
        door_state="not published (the gate said $LISTENERS_GATE_VERDICT; the proxy runs without the 443 overlay)"
    fi
    printf 'restored: %s\nfingerprint_sha256: %s (matches the copy)\nwriters_stopped: %s\n' "$stamp" "$restored" "$stopped"
    printf 'token_epoch: raised on every account (access.revoke exited %s)\n' "$revoke_status"
    printf 'credential_gate: %s%s\n' "$LISTENERS_GATE_VERDICT" \
        "$([ "$LISTENERS_GATE_VERDICT" = finding ] && printf ' (%s)' "$(listeners_gate_logins "$LISTENERS_GATE_OUTPUT" | paste -sd, -)")"
    printf 'https_443: %s\n' "$door_state"
    printf 'next: a reviewed revert (re-attest publish <sha> to bind it), its deploy, then resume %s\n' "$stamp"
}

verb_resume() {
    local stamp="$1" stopped=() writer start=() skipped=()
    require_checkout
    require_copy_dir
    take_copy_lock
    hold_import_lock
    require_open_record "$stamp"
    while IFS= read -r writer; do
        [ -n "$writer" ] && stopped+=("$writer")
    done < <(fc_json_words "$(rec writers_stopped)")
    for writer in "${stopped[@]}"; do
        if declared "$writer"; then start+=("$writer"); else skipped+=("$writer"); fi
    done
    if [ "${#start[@]}" -gt 0 ]; then
        compose start "${start[@]}" >&2 || true
    fi
    # >>> guard: writers-resumed
    for writer in "${start[@]}"; do
        if ! is_running "$writer"; then
            fc_refuse writers-resumed "$writer did not start; the record $stamp stays open." \
                "docker compose logs $writer; then resume $stamp again."
        fi
    done
    # <<< guard: writers-resumed
    set_rec state '"closed"'
    set_rec closed_at "\"$(fc_now)\""
    printf 'resumed: %s\nstarted: %s\n' "$stamp" "${start[*]:-none}"
    [ "${#skipped[@]}" -eq 0 ] || printf 'not in the deployed compose file any more: %s\n' "${skipped[*]}"
}

verb_status() {
    local age=""
    printf 'copy-serve.sh status\n'
    printf 'script: %s  lib: %s  probe: %s  listeners: %s\n' "$(sha256_of "${BASH_SOURCE[0]}")" \
        "$(sha256_of "$HERE/lib/forced-command.sh")" \
        "$( [ -r "$HERE/capacity-probe.sh" ] && sha256_of "$HERE/capacity-probe.sh" || echo absent)" \
        "$( [ -r "$HERE/lib/proxy-listeners.sh" ] && sha256_of "$HERE/lib/proxy-listeners.sh" || echo absent)"
    printf 'checkout: %s  deployed_tree: %s\n' "$CHECKOUT" \
        "$(git -C "$CHECKOUT" rev-parse --verify --quiet 'HEAD^{commit}' 2>/dev/null || echo unknown)"
    printf 'copy_dir: %s\n' "$COPY_DIR"
    if fc_lock_held "$STAGING/import.lock"; then
        printf 'import_lock: held\n'
    else
        printf 'import_lock: free\n'
    fi
    if [ -e "$MARKER" ]; then
        printf 'real_data_marker: present (%s)\n' "$(tr '\n' ' ' < "$MARKER")"
    else
        printf 'real_data_marker: absent\n'
    fi
    if [ -e "$PREV_RECORD" ] && fc_record_valid "$PREV_RECORD"; then
        printf 'previous_record: %s (restorable until a new dump-db completes)\n' "$(fc_record_string "$PREV_RECORD" stamp)"
    fi
    if ! record_exists; then
        printf 'record: none\n'
        return 0
    fi
    if ! fc_record_valid "$RECORD"; then
        printf 'record: unreadable (%s)\n' "$RECORD"
        return 0
    fi
    if [ "$(rec quiesced_at)" != null ]; then
        age="$(( $(date -u +%s) - $(fc_epoch "$(rec_str quiesced_at)") ))"
    fi
    printf 'record: %s  kind: %s  state: %s  purpose: %s  target: %s\n' \
        "$(rec_str stamp)" "$(rec_str kind)" "$(rec_str state)" "$(rec_str purpose)" "$(rec target_sha)"
    printf 'quiesced_at: %s  age_seconds: %s  window_seconds: %s\n' "$(rec quiesced_at)" "${age:-n/a}" "$WINDOW_SECONDS"
    printf 'writers_stopped: %s\n' "$(rec writers_stopped)"
    printf 'attested: %s  waiver: %s\n' \
        "$([ "$(rec attestation)" = null ] && echo no || echo yes)" \
        "$([ "$(rec waiver)" = null ] && echo no || echo yes)"
}

# --- the verb table -------------------------------------------------------------------
# One line per verb. A verb added here needs its grammar cases and a refusal case per new
# guard in tests/integration/composition/test_stand_copy_refusals.py, or that suite is red.

fc_register capacity '^capacity$' verb_capacity
fc_register dump-db '^dump-db$' verb_dump_db
fc_register inventory-s3 "^inventory-s3 ${FC_STAMP_ERE}\$" verb_inventory_s3
fc_register fetch "^fetch ${FC_STAMP_ERE} (db|inventory|record)\$" verb_fetch
fc_register attest "^attest (${FC_STAMP_ERE} [0-9a-f]{64} [0-9a-f]{64} (publish [0-9a-f]{40}|import)|--test-data)\$" verb_attest
fc_register verify-objects '^verify-objects [1-9][0-9]{0,3}( [0-9a-z]{1,32})?$' verb_verify_objects
fc_register restore-db "^restore-db ${FC_STAMP_ERE} [0-9a-f]{64}\$" verb_restore_db
fc_register resume "^resume ${FC_STAMP_ERE}\$" verb_resume
fc_register status '^status$' verb_status

fc_dispatch "${SSH_ORIGINAL_COMMAND-}"
