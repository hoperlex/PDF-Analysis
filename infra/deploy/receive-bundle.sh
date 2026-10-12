#!/usr/bin/env bash
# `W54-TRANSPORT-01` -- the INBOUND KEY's forced command on the stand.
#
#   authorized_keys (the owner installs it; one line):
#     restrict,from="<development host>",command="BUNDLE_STAGING=/srv/auditmanager-bundles /srv/auditmanager/infra/deploy/receive-bundle.sh" ssh-ed25519 AAAA... w54-inbound
#
# The account this key logs into can run `docker`, which is root-equivalent, so THIS SCRIPT
# IS THE BOUNDARY (`W54-PLAN.md` §3.5). It reads one thing from the client --
# `SSH_ORIGINAL_COMMAND` -- and admits exactly these verbs (`<KEY>` is the bundle name,
# grammar in `lib/forced-command.sh`):
#
#   receive <KEY> <size>   read exactly <size> bytes of tar from stdin into staging, check
#                          it, and keep the tree only if every rule holds
#   status                 read-only: staging, free space, the import lock, each bundle's
#                          state, the last lines of each import log, this script's SHA-256
#   import <KEY>           start the importer DETACHED under the import lock; re-entrant
#                          (run it again until it exits 0); `status` shows its progress
#   report <KEY>           the importer's read-only report, synchronously, exit passed on
#   requeue <KEY>          custody `requeue` of that bundle's poisoned admissions
#
# `import`, `report` and `requeue` each run ONE fixed command -- the api image's
# `python -m auditmanager.norms.bundle <action> /bundles/<KEY>` in a one-shot container --
# and nothing the client sends reaches it except the validated `<KEY>`.
#
# CONFIGURATION is the environment the `command="..."` option sets (sshd gives a forced
# command no client environment beyond what `AcceptEnv` admits, and `LC_ALL` is pinned
# below so an accepted `LC_*` changes nothing):
#
#   BUNDLE_STAGING               absolute, owner-created, owned by this account, not group-
#                                or world-writable, outside the checkout (default
#                                /srv/auditmanager-bundles)
#   STAND_COPY_RECORD            the open copy record `copy-serve.sh` keeps (default
#                                /srv/auditmanager-copy/record.json)
#   ALPHA_ENV_FILE               as for deploy.sh (default infra/deploy/env/alpha.env)
#   BUNDLE_MAX_BYTES             largest <size> accepted (default 12 GiB)
#   BUNDLE_STAGING_MARGIN_BYTES  free space kept on staging beyond 2 x <size> (default 2 GiB)
#
# STAGING LAYOUT (everything this script writes is under BUNDLE_STAGING):
#
#   incoming/<KEY>/      one receive in progress: bundle.tar, then tree/<KEY>/. Removed on
#                        any refusal or failure, and the tar removed after extraction
#   bundles/<KEY>/       a received bundle; it is here only if every rule held
#   logs/                <KEY>.received, <KEY>.import.{started,log,exit}
#   receive.lock         one receive at a time
#   import.lock          held for the whole of an import, report or requeue. `deploy.sh`
#                        (`W54-STAND-COPY-01`) refuses while it is held
#
# Exit: 0 done; 3 refused (`REFUSED [<guard>]` names which); anything else is the exit of
# the importer's own report or requeue, passed on. Guard markers: see the library.

set -euo pipefail
export LC_ALL=C
umask 022

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
FC_NAME=receive-bundle.sh
# shellcheck source=infra/deploy/lib/forced-command.sh
. "$HERE/lib/forced-command.sh"

COMPOSE_FILE="$HERE/compose.server.yml"
ENV_FILE="${ALPHA_ENV_FILE:-$HERE/env/alpha.env}"
STAGING="${BUNDLE_STAGING:-/srv/auditmanager-bundles}"
COPY_RECORD="${STAND_COPY_RECORD:-/srv/auditmanager-copy/record.json}"
MAX_BYTES="${BUNDLE_MAX_BYTES:-12884901888}"
MARGIN_BYTES="${BUNDLE_STAGING_MARGIN_BYTES:-2147483648}"

#: The only module `import`, `report` and `requeue` run, and where the bundle and the copy
#: record appear inside its container.
BUNDLE_MODULE=auditmanager.norms.bundle
RECORD_IN_CONTAINER=/run/copy-record.json

BUNDLES="$STAGING/bundles"
INCOMING="$STAGING/incoming"
LOGS="$STAGING/logs"

# --- guards every verb shares ---------------------------------------------------------

require_staging() {
    local mode
    # >>> guard: staging-absolute
    case "$STAGING" in
        /*) ;;
        *) fc_refuse staging-absolute "BUNDLE_STAGING is '$STAGING'; it must be an absolute path." ;;
    esac
    # <<< guard: staging-absolute

    # >>> guard: staging-directory
    if [ -L "$STAGING" ] || [ ! -d "$STAGING" ]; then
        fc_refuse staging-directory "BUNDLE_STAGING $STAGING is not an existing directory (the owner creates it)."
    fi
    # <<< guard: staging-directory

    # >>> guard: staging-owned
    mode="$(stat -c '%a' "$STAGING")"
    if [ ! -O "$STAGING" ] || [ $(( 8#$mode & 8#022 )) -ne 0 ]; then
        fc_refuse staging-owned "$STAGING must be owned by this account and not group- or world-writable (mode $mode)."
    fi
    # <<< guard: staging-owned

    # >>> guard: staging-outside-checkout
    case "$(cd "$STAGING" && pwd -P)/" in
        "$(cd "$REPO" && pwd -P)"/*)
            fc_refuse staging-outside-checkout "$STAGING is inside the checkout $REPO." \
                "deploy-auto refuses a checkout with untracked files; staging lives beside it." ;;
    esac
    # <<< guard: staging-outside-checkout
}

ensure_layout() {
    mkdir -p "$BUNDLES" "$INCOMING" "$LOGS"
}

require_bundle() {
    local key="$1"
    # >>> guard: bundle-received
    if [ -L "$BUNDLES/$key" ] || [ ! -d "$BUNDLES/$key" ]; then
        fc_refuse bundle-received "no received bundle $key in $BUNDLES." "send it first: receive <KEY> <size>"
    fi
    # <<< guard: bundle-received
}

require_stack() {
    # >>> guard: env-file-present
    if [ ! -r "$ENV_FILE" ]; then
        fc_refuse env-file-present "$ENV_FILE is missing or unreadable."
    fi
    # <<< guard: env-file-present

    # >>> guard: compose-file-present
    if [ ! -r "$COMPOSE_FILE" ]; then
        fc_refuse compose-file-present "$COMPOSE_FILE is missing."
    fi
    # <<< guard: compose-file-present
}

# The copy record's presence. `D-37`: a `--volume` source that does not exist is created
# by the daemon as an EMPTY DIRECTORY rather than refused, so the importer would be handed
# a directory where a record was promised. Whether the record is attested, open, recent
# and unchanged is the importer's refusal (`W54-BUNDLE-01`) and `W54-STAND-COPY-01`'s
# pre-check here; this guard only keeps the mount honest.
require_record() {
    # >>> guard: copy-record-present
    case "$COPY_RECORD" in
        /*) ;;
        *) fc_refuse copy-record-present "STAND_COPY_RECORD is '$COPY_RECORD'; it must be an absolute path." ;;
    esac
    if [ -L "$COPY_RECORD" ] || [ ! -f "$COPY_RECORD" ] || [ ! -r "$COPY_RECORD" ]; then
        fc_refuse copy-record-present "there is no copy record at $COPY_RECORD." \
            "the importer runs only after the one-off copy (R-88): dump-db, inventory-s3, fetch, attest."
    fi
    # <<< guard: copy-record-present
}

# Takes the import lock on fd 9 and keeps it until this process -- and every child that
# inherits fd 9, which is how the detached importer keeps it -- has exited.
take_import_lock() {
    exec 9>>"$STAGING/import.lock"
    # >>> guard: import-lock-free
    if ! flock --nonblock 9; then
        fc_refuse import-lock-free "an import, report or requeue is running; nothing was started." \
            "status shows which."
    fi
    # <<< guard: import-lock-free
}

# The ONE command shape `import`, `report` and `requeue` run, into MODULE_COMMAND.
# `<action>` is a literal at each call site; `<KEY>` has passed the grammar. Nothing else
# from the client is in it. The bundle is mounted read-only: the importer reads it.
MODULE_COMMAND=()
bundle_module() {
    local action="$1" key="$2"
    MODULE_COMMAND=(docker compose --env-file "$ENV_FILE" --file "$COMPOSE_FILE"
        run --rm --no-deps -T --entrypoint python
        --volume "$BUNDLES/$key:/bundles/$key:ro")
    case "$action" in
        import|report)
            MODULE_COMMAND+=(--volume "$COPY_RECORD:$RECORD_IN_CONTAINER:ro"
                api -m "$BUNDLE_MODULE" "$action" "/bundles/$key" --copy-record "$RECORD_IN_CONTAINER") ;;
        requeue)
            MODULE_COMMAND+=(api -m "$BUNDLE_MODULE" requeue "/bundles/$key") ;;
    esac
}

# --- verbs ----------------------------------------------------------------------------

#: The one receive's work directory, global so the EXIT trap still sees it after
#: `verb_receive` has returned. Always `$INCOMING/<KEY>`.
RECEIVE_WORK=""

verb_receive() {
    local key="$1" size="$2" avail need got extra work tree
    require_staging

    # >>> guard: size-within-limit
    if [ "$size" -gt "$MAX_BYTES" ]; then
        fc_refuse size-within-limit "$size bytes declared; at most $MAX_BYTES are accepted. Nothing was read."
    fi
    # <<< guard: size-within-limit

    # >>> guard: bundle-not-received
    if [ -e "$BUNDLES/$key" ] || [ -L "$BUNDLES/$key" ]; then
        fc_refuse bundle-not-received "$key is already received. Nothing was read." \
            "status shows it; an import of it is: import $key"
    fi
    # <<< guard: bundle-not-received

    ensure_layout
    exec 8>>"$STAGING/receive.lock"
    # >>> guard: receive-lock-free
    if ! flock --nonblock 8; then
        fc_refuse receive-lock-free "another receive is in progress. Nothing was read."
    fi
    # <<< guard: receive-lock-free

    # >>> guard: staging-has-room
    avail="$(df -B1 --output=avail -- "$STAGING" | tail -n 1 | tr -d ' ')"
    need=$(( 2 * size + MARGIN_BYTES ))
    if [ "$avail" -lt "$need" ]; then
        fc_refuse staging-has-room "$STAGING has $avail bytes free; this receive needs $need (the tar, its extraction, and $MARGIN_BYTES spare). Nothing was read."
    fi
    # <<< guard: staging-has-room

    # From here on bytes are read. Whatever happens, the work directory goes, and it is
    # always `$INCOMING/<KEY>` -- inside staging, named by a key the grammar admitted.
    work="$INCOMING/$key"
    tree="$work/tree"
    rm -rf -- "$work"
    RECEIVE_WORK="$work"
    trap 'if [ -n "$RECEIVE_WORK" ]; then rm -rf -- "$RECEIVE_WORK"; fi' EXIT
    mkdir -- "$work" "$tree"

    head -c "$size" > "$work/bundle.tar"
    got="$(stat -c '%s' "$work/bundle.tar")"
    extra="$(head -c 1 | wc -c)"
    # >>> guard: tar-length
    if [ "$got" -ne "$size" ] || [ "$extra" -ne 0 ]; then
        fc_refuse tar-length "$size bytes declared; $got arrived$([ "$extra" -eq 0 ] || printf ' and more followed'). The received bytes were removed."
    fi
    # <<< guard: tar-length

    tar_members_check "$key" "$work"

    tar --extract --no-same-owner --no-same-permissions --file "$work/bundle.tar" --directory "$tree"
    rm -f -- "$work/bundle.tar"

    fc_check_bundle_tree "$tree/$key" "$key"

    mv -T -- "$tree/$key" "$BUNDLES/$key"
    printf 'received_at=%s\nsize=%s\nfiles=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$size" \
        "$(grep -c . "$BUNDLES/$key/SHA256SUMS")" > "$LOGS/$key.received"
    echo "receive-bundle.sh: received $key ($size bytes, $(grep -c . "$BUNDLES/$key/SHA256SUMS") files verified)."
}

# The tar is listed, never trusted, before a byte of it is extracted: every member is a
# regular file or a directory, and every name is `<KEY>`, `<KEY>/` or `<KEY>/<path>` with
# the bundle path grammar -- so nothing can land outside `incoming/<KEY>/tree/<KEY>`.
tar_members_check() {
    local key="$1" work="$2" names types key_ere
    key_ere="${key//./\\.}"
    key_ere="${key_ere//+/\\+}"
    # >>> guard: tar-readable
    if ! names="$(tar --list --quoting-style=escape --file "$work/bundle.tar" 2>/dev/null)" \
        || ! types="$(tar --list --verbose --quoting-style=escape --file "$work/bundle.tar" 2>/dev/null | cut -c1)"; then
        fc_refuse tar-readable "the received bytes are not a readable tar archive. They were removed."
    fi
    # <<< guard: tar-readable

    # >>> guard: tar-members-safe
    if [ -z "$names" ] \
        || printf '%s\n' "$types" | grep -qv '^[-d]$' \
        || printf '%s\n' "$names" | grep -Evq "^${key_ere}(/|/${FC_BUNDLE_PATH_ERE}/?)?\$"; then
        fc_refuse tar-members-safe "the archive holds a member that is not a plain file or directory under $key/. It was removed unextracted."
    fi
    # <<< guard: tar-members-safe
}

verb_status() {
    local key free state started exitf
    require_staging
    printf 'receive-bundle.sh status\n'
    printf 'script: %s  lib: %s\n' "$(sha256sum < "${BASH_SOURCE[0]}" | cut -c1-64)" \
        "$(sha256sum < "$HERE/lib/forced-command.sh" | cut -c1-64)"
    free="$(df -B1 --output=avail -- "$STAGING" | tail -n 1 | tr -d ' ')"
    printf 'staging: %s  free_bytes: %s\n' "$STAGING" "$free"
    if [ ! -e "$STAGING/import.lock" ] || flock --nonblock "$STAGING/import.lock" true 2>/dev/null; then
        printf 'import_lock: free\n'
    else
        printf 'import_lock: held\n'
    fi
    if [ -d "$INCOMING" ]; then
        for key in "$INCOMING"/*; do
            [ -e "$key" ] || continue
            printf 'incoming: %s (a receive in progress or interrupted)\n' "${key##*/}"
        done
    fi
    [ -d "$BUNDLES" ] || { printf 'bundles: none\n'; return 0; }
    for key in "$BUNDLES"/*; do
        [ -d "$key" ] || continue
        key="${key##*/}"
        started="$LOGS/$key.import.started"
        exitf="$LOGS/$key.import.exit"
        if [ -f "$exitf" ]; then
            state="exited $(cat "$exitf")"
        elif [ -f "$started" ]; then
            state="running or ended without an exit status (started $(cat "$started"))"
        else
            state="not imported"
        fi
        printf 'bundle: %s  bytes: %s  import: %s\n' "$key" \
            "$(du -sb -- "$BUNDLES/$key" | cut -f1)" "$state"
        if [ -f "$LOGS/$key.import.log" ]; then
            tail -n 5 -- "$LOGS/$key.import.log" | sed 's/^/  | /'
        fi
    done
}

# Detached, locked, re-entrant. The lock is taken HERE, synchronously, so a second
# `import` is refused in words rather than queued; the detached runner inherits fd 9 and
# holds the lock until the importer exits. Its exit status lands in logs/<KEY>.import.exit.
verb_import() {
    local key="$1"
    require_staging
    require_bundle "$key"
    require_stack
    require_record
    ensure_layout
    take_import_lock
    bundle_module import "$key"

    rm -f -- "$LOGS/$key.import.exit"
    date -u +%Y-%m-%dT%H:%M:%SZ > "$LOGS/$key.import.started"
    # The runner text is a literal; the command reaches it as positional parameters.
    # shellcheck disable=SC2016
    setsid bash -c 'exit_file="$1"; shift; status=0; "$@" || status=$?
        printf "%s\n" "$status" > "$exit_file.tmp" && mv -f "$exit_file.tmp" "$exit_file"
        exit "$status"' import-runner "$LOGS/$key.import.exit" "${MODULE_COMMAND[@]}" \
        < /dev/null > "$LOGS/$key.import.log" 2>&1 &
    echo "receive-bundle.sh: import of $key started (detached, pid $!). Follow it with: status"
}

verb_report() {
    local key="$1"
    require_staging
    require_bundle "$key"
    require_stack
    require_record
    take_import_lock
    bundle_module report "$key"
    "${MODULE_COMMAND[@]}" < /dev/null
}

verb_requeue() {
    local key="$1"
    require_staging
    require_bundle "$key"
    require_stack
    take_import_lock
    bundle_module requeue "$key"
    "${MODULE_COMMAND[@]}" < /dev/null
}

# --- the verb table -------------------------------------------------------------------
# One line per verb. A verb added here needs its refusal case in
# tests/integration/composition/test_bundle_transport_refusals.py, or that suite is red.

fc_register receive "^receive (${FC_BUNDLE_KEY_ERE}) [1-9][0-9]{0,11}\$" verb_receive
fc_register status '^status$' verb_status
fc_register import "^import (${FC_BUNDLE_KEY_ERE})\$" verb_import
fc_register report "^report (${FC_BUNDLE_KEY_ERE})\$" verb_report
fc_register requeue "^requeue (${FC_BUNDLE_KEY_ERE})\$" verb_requeue

fc_dispatch "${SSH_ORIGINAL_COMMAND-}"
