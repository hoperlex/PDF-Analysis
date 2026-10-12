#!/usr/bin/env bash
# `W54-STAND-COPY-01` -- prove a pulled copy restores, here, into the database it was taken
# from: restore the dump into a DISPOSABLE local PostgreSQL, run the stand's own
# fingerprint query against it, compare with the record, check the inventory, and write
# the report whose SHA-256 the copy key's `attest` binds.
#
#   scripts/stand-copy/restore-test.sh <copy directory>
#
# `<copy directory>` is what `infra/deploy/pull-copy.sh` wrote: `<root>/<STAMP>/` holding
# `record.json`, `db.dump` and `inventory.tsv`.
#
# THIS IS A HEAVY STEP (`W54-PLAN.md` §3.9, `W54-FREEZE-01`): it runs one container and
# restores a whole database, so it runs only inside an owner-designated window, one heavy
# step at a time, and it refuses unless `infra/deploy/capacity-probe.sh` finds the Docker
# data root's filesystem with four times the dump plus 3 GiB free and at least 6 GiB of
# RAM available (`STAND_COPY_RESTORE_NEED_RAM` / `STAND_COPY_RESTORE_NEED_DISK` override
# the two figures; nothing else does).
#
# THE CONTAINER is this script's own: named `stand-copy-restore-<STAMP>-<pid>`, started
# with `--rm --network none` from `STAND_COPY_RESTORE_IMAGE` (default the local stack's
# `auditmanager-postgres:17.11-pgvector0.8.6-8ee86c9`, the stand's PostgreSQL 17.11 and
# pgvector 0.8.6), and removed by that exact name on every exit. No port is published.
#
# THE FINGERPRINT QUERY IS NOT COPIED HERE. It is read out of `infra/deploy/copy-serve.sh`
# between its `stand-fingerprint-v1` markers, so the stand and this host run one text.
#
# Output: `<copy directory>/restore-report.txt` (no client data: stamps, digests, counts)
# and the exact `attest` line to send with the copy key.
#
# Exit: 0 reproduced; 2 usage; 3 refused (`REFUSED [<guard>]`).

set -euo pipefail
export LC_ALL=C
umask 077

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
FC_NAME=restore-test.sh
# shellcheck source=infra/deploy/lib/forced-command.sh
. "$REPO/infra/deploy/lib/forced-command.sh"

IMAGE="${STAND_COPY_RESTORE_IMAGE:-auditmanager-postgres:17.11-pgvector0.8.6-8ee86c9}"
NEED_RAM="${STAND_COPY_RESTORE_NEED_RAM:-6442450944}"
READY_SECONDS="${STAND_COPY_RESTORE_READY_SECONDS:-180}"
COPY_SERVE="$REPO/infra/deploy/copy-serve.sh"

usage() {
    sed -n '7p' "${BASH_SOURCE[0]}" | sed 's/^#  *//' >&2
    exit 2
}

# >>> guard: known-options
case "${1:-}" in
    -h|--help|'') usage ;;
    -*) fc_refuse known-options "unrecognised option: $1" ;;
esac
if [ "$#" -ne 1 ]; then
    fc_refuse known-options "exactly one copy directory is taken; got $#."
fi
# <<< guard: known-options

DIR=""
if [ -d "$1" ]; then
    DIR="$(cd "$1" && pwd -P)"
fi
STAMP="${DIR##*/}"
RECORD="$DIR/record.json"
DUMP="$DIR/db.dump"
INVENTORY="$DIR/inventory.tsv"

# >>> guard: copy-present
if [ -z "$DIR" ] || [ ! -f "$RECORD" ] || [ ! -f "$DUMP" ] || [ ! -f "$INVENTORY" ]; then
    fc_refuse copy-present "'$1' is not a pulled copy: record.json, db.dump and inventory.tsv are required." \
        "infra/deploy/pull-copy.sh writes them."
fi
# <<< guard: copy-present

# >>> guard: record-is-the-copy
if ! fc_record_valid "$RECORD" || [ "$(fc_record_string "$RECORD" stamp)" != "$STAMP" ] \
    || [ "$(fc_record_string "$RECORD" kind)" != copy ] || [ "$(fc_record_value "$RECORD" fingerprint)" = null ] \
    || [ "$(fc_record_value "$RECORD" dump)" = null ] || [ "$(fc_record_value "$RECORD" inventory)" = null ]; then
    fc_refuse record-is-the-copy "$RECORD is not the full copy $STAMP (fingerprint, dump and inventory)."
fi
# <<< guard: record-is-the-copy

DUMP_RECORD="$(fc_record_value "$RECORD" dump)"
INVENTORY_RECORD="$(fc_record_value "$RECORD" inventory)"
FINGERPRINT_RECORD="$(fc_record_value "$RECORD" fingerprint)"
DUMP_SHA="$(sha256sum < "$DUMP" | cut -c1-64)"
DUMP_SIZE="$(stat -c '%s' "$DUMP")"

# >>> guard: dump-matches-record
if [ "$DUMP_SHA" != "$(fc_json_member "$DUMP_RECORD" sha256)" ] || [ "$DUMP_SIZE" != "$(fc_json_member "$DUMP_RECORD" size_bytes)" ]; then
    fc_refuse dump-matches-record "db.dump is not the dump the record names (size or SHA-256)."
fi
# <<< guard: dump-matches-record

INVENTORY_SHA="$(sha256sum < "$INVENTORY" | cut -c1-64)"
INVENTORY_COUNT="$(grep -c . "$INVENTORY" || true)"
INVENTORY_BYTES="$(awk -F'\t' '{ total += $2 } END { printf "%d\n", total }' "$INVENTORY")"
# >>> guard: inventory-matches-record
if [ "$INVENTORY_SHA" != "$(fc_json_member "$INVENTORY_RECORD" sha256)" ] \
    || [ "$INVENTORY_COUNT" != "$(fc_json_member "$INVENTORY_RECORD" count)" ] \
    || [ "$INVENTORY_BYTES" != "$(fc_json_member "$INVENTORY_RECORD" bytes)" ] \
    || grep -Evq "$(printf '^[A-Za-z0-9][A-Za-z0-9._/-]*\t(0|[1-9][0-9]*)\t[^\t]*$')" "$INVENTORY"; then
    fc_refuse inventory-matches-record "inventory.tsv does not parse, or its count, bytes or SHA-256 differ from the record." \
        "parsed $INVENTORY_COUNT objects, $INVENTORY_BYTES bytes, sha256 $INVENTORY_SHA"
fi
# <<< guard: inventory-matches-record

# >>> guard: image-present
if ! docker image inspect "$IMAGE" > /dev/null 2>&1; then
    fc_refuse image-present "the restore image $IMAGE is not on this host." \
        "It is the local stack's PostgreSQL image (make up builds it); STAND_COPY_RESTORE_IMAGE names another."
fi
# <<< guard: image-present

DOCKER_ROOT="$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || true)"
NEED_DISK="${STAND_COPY_RESTORE_NEED_DISK:-$(( 4 * DUMP_SIZE + 3221225472 ))}"
# >>> guard: host-has-room
if ! bash "$REPO/infra/deploy/capacity-probe.sh" --path "docker_root=${DOCKER_ROOT:-/}" \
        --need "docker_root=$NEED_DISK" --need-ram "$NEED_RAM" >&2; then
    fc_refuse host-has-room "this host is below the heavy-step floor (W54-PLAN.md 3.9); nothing was started."
fi
# <<< guard: host-has-room

NAME="stand-copy-restore-$STAMP-$$"
STARTED=no
cleanup() {
    if [ "$STARTED" = yes ]; then
        docker rm --force "$NAME" > /dev/null 2>&1 || true
    fi
}
trap cleanup EXIT

PASSWORD="$(head -c 24 /dev/urandom | sha256sum | cut -c1-32)"
STARTED=yes
docker run --detach --rm --name "$NAME" --network none \
    --env POSTGRES_USER=restore --env POSTGRES_DB=restore --env "POSTGRES_PASSWORD=$PASSWORD" \
    "$IMAGE" > /dev/null

# The image's entrypoint runs a socket-only server while it initializes; TCP on the
# container's own loopback answers only once the real server is up.
waited=0
READY=no
while [ "$waited" -le "$READY_SECONDS" ]; do
    if docker exec "$NAME" pg_isready --quiet --host 127.0.0.1 --username restore --dbname restore 2>/dev/null; then
        READY=yes
        break
    fi
    sleep 1
    waited=$(( waited + 1 ))
done
# >>> guard: database-ready
if [ "$READY" != yes ]; then
    fc_refuse database-ready "the disposable PostgreSQL did not become ready in $READY_SECONDS s."
fi
# <<< guard: database-ready

# >>> guard: dump-restored
if ! docker exec -i "$NAME" pg_restore --no-owner --no-privileges --exit-on-error --single-transaction \
        --username restore --dbname restore < "$DUMP" >&2; then
    fc_refuse dump-restored "pg_restore did not restore the dump whole into a fresh database."
fi
# <<< guard: dump-restored

SQL="$(sed -n '/^-- >>> stand-fingerprint-v1$/,/^-- <<< stand-fingerprint-v1$/p' "$COPY_SERVE")"
# >>> guard: fingerprint-read
if [ -z "$SQL" ] \
    || ! LINES="$(printf '%s\n' "$SQL" | docker exec -i "$NAME" psql --quiet --no-align --tuples-only --no-psqlrc \
            --set ON_ERROR_STOP=1 --username restore --dbname restore 2>&1)" \
    || ! fc_fingerprint_lines_valid "$LINES"; then
    fc_refuse fingerprint-read "the fingerprint query did not print one line per table." "$(printf '%s' "${LINES:-}" | head -n 3)"
fi
# <<< guard: fingerprint-read

REPRODUCED="$(fc_fingerprint_json "$LINES")"
# >>> guard: fingerprint-reproduced
if [ "$REPRODUCED" != "$FINGERPRINT_RECORD" ]; then
    fc_refuse fingerprint-reproduced "the restored dump's fingerprint is not the stand's: the copy does not describe the database it was taken from." \
        "stand: $(fc_json_member "$FINGERPRINT_RECORD" sha256)" "here:  $(fc_json_member "$REPRODUCED" sha256)" \
        "tables that differ: $(diff <(printf '%s\n' "$FINGERPRINT_RECORD" | grep -oE '"[a-z_0-9]+": \{[^}]*\}') \
                                    <(printf '%s\n' "$REPRODUCED" | grep -oE '"[a-z_0-9]+": \{[^}]*\}') \
                               | grep -E '^[<>]' | cut -d'"' -f2 | sort -u | tr '\n' ' ' || true)"
fi
# <<< guard: fingerprint-reproduced

REPORT="$DIR/restore-report.txt"
{
    printf 'stand-copy restore report v1\n'
    printf 'stamp: %s\n' "$STAMP"
    printf 'instance: %s\n' "$(fc_record_string "$RECORD" instance)"
    printf 'deployed_tree: %s\n' "$(fc_record_string "$RECORD" deployed_tree)"
    printf 'migration_head: %s\n' "$(fc_record_string "$RECORD" migration_head)"
    printf 'dump_sha256: %s\n' "$DUMP_SHA"
    printf 'dump_bytes: %s\n' "$DUMP_SIZE"
    printf 'restore_image: %s\n' "$IMAGE"
    printf 'restore_image_id: %s\n' "$(docker image inspect --format '{{.Id}}' "$IMAGE" 2>/dev/null || echo unknown)"
    printf 'fingerprint_sha256: %s (reproduced)\n' "$(fc_json_member "$REPRODUCED" sha256)"
    printf 'fingerprint_tables: %s\n' "$(printf '%s\n' "$LINES" | grep -c .)"
    printf 'inventory_sha256: %s\n' "$INVENTORY_SHA"
    printf 'inventory_objects: %s\n' "$INVENTORY_COUNT"
    printf 'inventory_bytes: %s\n' "$INVENTORY_BYTES"
    printf 'restored_at: %s\n' "$(fc_now)"
} > "$REPORT"
REPORT_SHA="$(sha256sum < "$REPORT" | cut -c1-64)"

printf 'restore-test.sh: %s restored here and its fingerprint reproduced.\n' "$STAMP"
printf 'report: %s\nreport_sha256: %s\n' "$REPORT" "$REPORT_SHA"
printf 'attest with the copy key, for a publication or for the import:\n'
printf '  attest %s %s %s publish <40-hex target sha>\n' "$STAMP" "$DUMP_SHA" "$REPORT_SHA"
printf '  attest %s %s %s import\n' "$STAMP" "$DUMP_SHA" "$REPORT_SHA"
