#!/usr/bin/env bash
# `W54-STAND-COPY-01` -- bring one open copy from the stand to this host, through the copy
# key, and check every byte against the copy's own record before anything trusts it.
#
#   infra/deploy/pull-copy.sh --host <user@stand> --identity <private key>
#                             [--known-hosts <file>] <STAMP> <destination root>
#
# Runs HERE, on the development host. `<STAMP>` is what the copy key's `dump-db` printed.
# It writes `<destination root>/<STAMP>/` with three files, each fetched by the copy key's
# `fetch <STAMP> record|db|inventory`:
#
#   record.json    the copy record; its stamp must be <STAMP> and it must be a full copy
#                  with its dump and inventory taken
#   db.dump        must have the size and SHA-256 the record names
#   inventory.tsv  must have the count, bytes and SHA-256 the record names
#
# A file that does not match is removed, the directory with it, and the pull is refused:
# nothing half-checked is left beside a dump of the client database. Then
# `scripts/stand-copy/restore-test.sh <destination root>/<STAMP>` restores it here.
#
# THE DESTINATION holds client data (`R-88`): it must be outside every Git work tree or
# ignored by it, owned by this account, and not group- or world-readable. `.local/stand-copy`
# in this repository is ignored and is the expected place.
#
# Exit: 0 pulled and verified; 2 usage; 3 refused here (`REFUSED [<guard>]`); any other
# status is the stand's, passed on (3 there is a refusal on the stand).

set -euo pipefail
export LC_ALL=C
umask 077

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FC_NAME=pull-copy.sh
# shellcheck source=infra/deploy/lib/forced-command.sh
. "$HERE/lib/forced-command.sh"

HOST="${STAND_COPY_HOST:-}"
IDENTITY="${STAND_COPY_IDENTITY:-}"
KNOWN_HOSTS=""
ARGS=()
UNKNOWN=""

usage() {
    sed -n '5,6p' "${BASH_SOURCE[0]}" | sed 's/^#  *//' >&2
    exit 2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --host) HOST="${2:-}"; shift 2 || usage ;;
        --identity) IDENTITY="${2:-}"; shift 2 || usage ;;
        --known-hosts) KNOWN_HOSTS="${2:-}"; shift 2 || usage ;;
        -h|--help) usage ;;
        -*) UNKNOWN="${UNKNOWN:-$1}"; shift ;;
        *) ARGS+=("$1"); shift ;;
    esac
done

# >>> guard: known-options
if [ -n "$UNKNOWN" ] || [ "${#ARGS[@]}" -gt 2 ]; then
    fc_refuse known-options "unrecognised option or extra argument: ${UNKNOWN:-${ARGS[2]:-}}"
fi
# <<< guard: known-options

[ "${#ARGS[@]}" -eq 2 ] || usage
STAMP="${ARGS[0]}"
DEST_ROOT="${ARGS[1]}"

# >>> guard: stamp-grammar
if ! [[ $STAMP =~ ^${FC_STAMP_ERE}$ ]]; then
    fc_refuse stamp-grammar "'$STAMP' is not a copy stamp (YYYYMMDDTHHMMSSZ, as dump-db printed it)."
fi
# <<< guard: stamp-grammar

# >>> guard: host-configured
if [ -z "$HOST" ]; then
    fc_refuse host-configured "no stand named: --host <user@host> or STAND_COPY_HOST."
fi
# <<< guard: host-configured

# >>> guard: identity-present
if [ -z "$IDENTITY" ] || [ ! -r "$IDENTITY" ]; then
    fc_refuse identity-present "the copy key's private half is not readable: '${IDENTITY}'." \
        "--identity <file> or STAND_COPY_IDENTITY"
fi
# <<< guard: identity-present

# >>> guard: destination-private
mode="$(stat -c '%a' "$DEST_ROOT" 2>/dev/null || echo missing)"
if [[ $DEST_ROOT != /* ]] || [ -L "$DEST_ROOT" ] || [ ! -d "$DEST_ROOT" ] || [ ! -O "$DEST_ROOT" ] \
    || [ "$mode" = missing ] || [ $(( 8#$mode & 8#077 )) -ne 0 ]; then
    fc_refuse destination-private "$DEST_ROOT must be an absolute, existing directory owned by you with mode 700 (it is $mode)." \
        "A dump of the client database lands there."
fi
if git -C "$DEST_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
    && ! git -C "$DEST_ROOT" check-ignore -q "$DEST_ROOT/$STAMP"; then
    fc_refuse destination-private "$DEST_ROOT is inside a Git work tree and $STAMP there is not ignored." \
        "The copy never enters Git (W54-PLAN.md 3.5). Use .local/stand-copy in this repository."
fi
# <<< guard: destination-private

DEST="$DEST_ROOT/$STAMP"
# >>> guard: copy-not-pulled
if [ -e "$DEST" ] || [ -L "$DEST" ]; then
    fc_refuse copy-not-pulled "$DEST exists; this copy was pulled already." "Remove it to pull again."
fi
# <<< guard: copy-not-pulled

SSH=(ssh -T -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes
    -o ServerAliveInterval=15 -o ServerAliveCountMax=4 -i "$IDENTITY")
[ -z "$KNOWN_HOSTS" ] || SSH+=(-o "UserKnownHostsFile=$KNOWN_HOSTS")

PULLED=no
CREATED=no
cleanup() {
    if [ "$PULLED" = no ] && [ "$CREATED" = yes ]; then
        rm -rf -- "$DEST"
    fi
}
trap cleanup EXIT

mkdir -m 700 -- "$DEST"
CREATED=yes

fetch() {
    local what="$1" target="$2" status=0
    "${SSH[@]}" "$HOST" "fetch $STAMP $what" < /dev/null > "$target" || status=$?
    if [ "$status" -ne 0 ]; then
        printf 'pull-copy.sh: the stand refused or failed fetch %s %s (exit %s); its message is above.\n' \
            "$STAMP" "$what" "$status" >&2
        exit "$status"
    fi
}

fetch record "$DEST/record.json"
RECORD="$DEST/record.json"

# >>> guard: record-is-the-copy
if ! fc_record_valid "$RECORD" || [ "$(fc_record_string "$RECORD" stamp)" != "$STAMP" ] \
    || [ "$(fc_record_string "$RECORD" kind)" != copy ] \
    || [ "$(fc_record_value "$RECORD" dump)" = null ] || [ "$(fc_record_value "$RECORD" inventory)" = null ]; then
    fc_refuse record-is-the-copy "the record fetched is not the full copy $STAMP with its dump and inventory taken." \
        "Run dump-db and inventory-s3 on the stand first; a test_data_waiver has nothing to pull."
fi
# <<< guard: record-is-the-copy

DUMP="$(fc_record_value "$RECORD" dump)"
INVENTORY="$(fc_record_value "$RECORD" inventory)"

fetch db "$DEST/db.dump"
# >>> guard: dump-matches-record
if [ "$(stat -c '%s' "$DEST/db.dump")" != "$(fc_json_member "$DUMP" size_bytes)" ] \
    || [ "$(sha256sum < "$DEST/db.dump" | cut -c1-64)" != "$(fc_json_member "$DUMP" sha256)" ]; then
    fc_refuse dump-matches-record "the dump that arrived does not have the size and SHA-256 the record names. It was removed."
fi
# <<< guard: dump-matches-record

fetch inventory "$DEST/inventory.tsv"
# >>> guard: inventory-matches-record
if [ "$(sha256sum < "$DEST/inventory.tsv" | cut -c1-64)" != "$(fc_json_member "$INVENTORY" sha256)" ] \
    || [ "$(grep -c . "$DEST/inventory.tsv" || true)" != "$(fc_json_member "$INVENTORY" count)" ]; then
    fc_refuse inventory-matches-record "the inventory that arrived does not match the record. The copy was removed."
fi
# <<< guard: inventory-matches-record

PULLED=yes
printf 'pull-copy.sh: %s verified into %s\n' "$STAMP" "$DEST"
printf 'dump_sha256: %s\n' "$(fc_json_member "$DUMP" sha256)"
printf 'next: scripts/stand-copy/restore-test.sh %s\n' "$DEST"
