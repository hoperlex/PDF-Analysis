#!/usr/bin/env bash
# `EMBED-01` (ADR-0029 decision 8, plan-v5 section 5) -- the HOST side of the night encoder: the first timer of this repository.
#
#   infra/deploy/embed-window.sh tick    [--env-file <path>]   one look at the exchange directory (what the timer runs, every minute)
#   infra/deploy/embed-window.sh install [--env-file <path>]   write the two units to /etc/systemd/system, enable the timer (root)
#   infra/deploy/embed-window.sh status  [--env-file <path>]   what the host sees: the timer, the image, the exchange
#   infra/deploy/embed-window.sh build-image [--env-file <path>]   the encoder's image, after a check of the disk (deploy.sh, ALPHA_EMBEDDER=yes)
#   infra/deploy/embed-window.sh verify  [--env-file <path>]   the image, the timer and the heartbeat (verify-deployed.sh, ALPHA_EMBEDDER=yes)
#
# WHAT IT IS, AND WHAT IT IS NOT. The container that encodes has no database and no network; the worker that has the database does not run docker.
# This script is the one place docker is run for the encoder, and it has no database either: it reads and writes FILES in the exchange directory
# (the named volume `<instance>-embed-exchange`, by its mountpoint), and `precedents/vectors/exchange.py` documents each of them.
#
#   * every tick writes `heartbeat` (`epoch=<n>`): the worker opens no window for a host whose timer is silent, so a timer that is off costs no
#     night of stopped runs (rollback of this feature is `systemctl disable --now auditmanager-embed-window.timer`, and the intents wait);
#   * a tick that finds `request.json` and no `result` runs the service `embedder` over it, with the HARD memory limit compose gives it
#     (`mem_limit` from ALPHA_MEM_LIMIT_EMBEDDER, no default), and watches it: at the `deadline` the worker wrote, or when `abort` appears, the
#     container is stopped (by its exact name: this script never kills by pattern);
#   * what the container says, on either stream, goes to `stderr.log` (its tail is kept); then it writes `result` (`exit_code=<n>`): 0 done, 124 stopped at the deadline, 130 stopped by `abort`, 137 killed (the kernel's memory limit
#     gives SIGKILL), 127 the image is not there, anything else the container's own status. The worker reads it, imports or skips LOUDLY.
#
# It removes nothing of the round: the worker clears the files after it has read them. A second tick while one runs does nothing (a lock).
#
# Settings read as DATA from the environment file (never sourced): ALPHA_INSTANCE, and ALPHA_EMBEDDER_BUILD_MIN_FREE_GB (free GiB the image's build
# needs on the docker root; default 12: the image is 5.5 GB and its rebuild took 9.5 GB, `docs/program/W54-EMBED-BUILD-01.md`). Overrides for a test:
# EMBED_DIR (the exchange directory, instead of the volume's mountpoint), EMBED_DOCKER (the docker command), EMBED_NOW (epoch seconds),
# EMBED_POLL_SECONDS (the watch interval, default 5), EMBED_FREE_GIB (the free space, instead of asking df).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$HERE/compose.server.yml"
ENV_FILE="${ALPHA_ENV_FILE:-$HERE/env/alpha.env}"
DOCKER="${EMBED_DOCKER:-docker}"
POLL="${EMBED_POLL_SECONDS:-5}"
CONTAINER_UID=10001
UNIT_NAME=auditmanager-embed-window
SYSTEMD_DIR="${EMBED_SYSTEMD_DIR:-/etc/systemd/system}"

refuse() {
    printf 'embed-window.sh: %s\n' "$1" >&2
    shift
    [ "$#" -eq 0 ] || printf '  %s\n' "$@" >&2
    exit 3
}

COMMAND="${1:-}"
[ -n "$COMMAND" ] || refuse "no command." "usage: embed-window.sh tick|install|status|build-image|verify [--env-file <path>]"
shift
while [ "$#" -gt 0 ]; do
    case "$1" in
        --env-file) ENV_FILE="${2:-}"; shift 2 ;;
        *) refuse "unrecognised option: $1" ;;
    esac
done

configured() {
    sed -n "s/^[[:space:]]*\(export[[:space:]]\+\)\?$1=//p" "$ENV_FILE" | tail -1 \
        | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/"
}

now() { printf '%s' "${EMBED_NOW:-$(date +%s)}"; }

atomic_write() {  # atomic_write <file> <content>
    printf '%s\n' "$2" >"$1.part"
    mv -f "$1.part" "$1"
}

instance() {
    [ -r "$ENV_FILE" ] || refuse "the deployment environment $ENV_FILE is missing or unreadable."
    local name
    name="$(configured ALPHA_INSTANCE)"
    [ -n "$name" ] || refuse "$ENV_FILE names no ALPHA_INSTANCE."
    printf '%s' "$name"
}

# The exchange directory: the volume's mountpoint on this host. A volume that does not exist yet means the stack was never brought up here: the
# timer has nothing to do and says so (exit 0: a timer that fails every minute before the first deploy is noise, not information).
exchange_dir() {
    if [ -n "${EMBED_DIR:-}" ]; then printf '%s' "$EMBED_DIR"; return 0; fi
    "$DOCKER" volume inspect --format '{{.Mountpoint}}' "$(instance)-embed-exchange" 2>/dev/null
}

tick() {
    local inst dir
    inst="$(instance)"
    dir="$(exchange_dir || true)"
    if [ -z "$dir" ] || [ ! -d "$dir" ]; then
        echo "embed-window.sh: the exchange volume of $inst does not exist yet; nothing to do."
        return 0
    fi
    exec 9>"$dir/.lock"
    if ! flock -n 9; then
        echo "embed-window.sh: another tick holds the exchange; nothing to do."
        return 0
    fi
    # The containers run as uid 10001 (the worker and the encoder image share it); the directory is theirs. Best effort: a non-root test is not.
    chown "$CONTAINER_UID:$CONTAINER_UID" "$dir" 2>/dev/null || true
    atomic_write "$dir/heartbeat" "epoch=$(now)"

    [ -f "$dir/request.json" ] || return 0
    [ ! -e "$dir/result" ] || return 0   # the worker has not read the last one yet
    if [ -f "$dir/response.json" ]; then
        # The container finished and this script did not get to say so: `response.json` is written whole or not at all.
        atomic_write "$dir/result" "$(printf 'exit_code=0\nfinished_epoch=%s' "$(now)")"
        return 0
    fi
    local deadline
    deadline="$(tr -dc '0-9' <"$dir/deadline" 2>/dev/null || true)"
    [ -n "$deadline" ] || { report "$dir" 2 "the request has no readable deadline"; return 0; }
    if [ "$(now)" -ge "$deadline" ]; then
        report "$dir" 124 "the window had ended before the encoder started"
        return 0
    fi
    if ! "$DOCKER" image inspect "$inst-embedder" >/dev/null 2>&1; then
        report "$dir" 127 "there is no image $inst-embedder on this host; deploy.sh builds it when ALPHA_EMBEDDER=yes"
        return 0
    fi

    local name="$inst-embedder-window" code=0 forced=""
    # A container of this exact name left by a crash is ours to remove; nothing else is touched.
    "$DOCKER" rm -f "$name" >/dev/null 2>&1 || true
    : >"$dir/stderr.log"
    "$DOCKER" compose --env-file "$ENV_FILE" --file "$COMPOSE_FILE" --profile embedder \
        run --rm --no-deps -T --name "$name" embedder >>"$dir/stderr.log" 2>&1 &
    local pid=$!
    while kill -0 "$pid" 2>/dev/null; do
        if [ -e "$dir/abort" ]; then forced=130; "$DOCKER" stop --time 10 "$name" >/dev/null 2>&1 || true; break; fi
        if [ "$(now)" -ge "$deadline" ]; then forced=124; "$DOCKER" stop --time 10 "$name" >/dev/null 2>&1 || true; break; fi
        atomic_write "$dir/heartbeat" "epoch=$(now)"
        sleep "$POLL"
    done
    wait "$pid" || code=$?
    [ -z "$forced" ] || code="$forced"
    report "$dir" "$code" "the container ended with status $code"
}

# Write the account of the container: the tail of what it said, then `result` (the worker reads `result` last).
report() {  # report <dir> <code> <message>
    local dir="$1" code="$2" message="$3"
    printf 'embed-window.sh: %s\n' "$message" >>"$dir/stderr.log"
    tail -c 8192 "$dir/stderr.log" >"$dir/stderr.log.part" && mv -f "$dir/stderr.log.part" "$dir/stderr.log"
    atomic_write "$dir/result" "$(printf 'exit_code=%s\nfinished_epoch=%s' "$code" "$(now)")"
    echo "embed-window.sh: $message"
}

install_units() {
    [ "$(id -u)" -eq 0 ] || [ -n "${EMBED_SYSTEMD_DIR:-}" ] || refuse "install writes to $SYSTEMD_DIR and enables a timer: run it as root."
    local repo env unit
    repo="$(cd "$HERE/../.." && pwd)"
    env="$(cd "$(dirname "$ENV_FILE")" && pwd)/$(basename "$ENV_FILE")"
    mkdir -p "$SYSTEMD_DIR"
    for unit in "$UNIT_NAME.service" "$UNIT_NAME.timer"; do
        [ -r "$HERE/systemd/$unit" ] || refuse "$HERE/systemd/$unit is missing."
        sed -e "s|@REPO@|$repo|g" -e "s|@ENV_FILE@|$env|g" "$HERE/systemd/$unit" >"$SYSTEMD_DIR/$unit"
        echo "embed-window.sh: wrote $SYSTEMD_DIR/$unit"
    done
    if [ -z "${EMBED_SYSTEMD_DIR:-}" ]; then
        systemctl daemon-reload
        systemctl enable --now "$UNIT_NAME.timer"
        echo "embed-window.sh: the timer is enabled. To stop the night encoder: systemctl disable --now $UNIT_NAME.timer (the intents wait)."
    fi
}

status() {
    local inst dir
    inst="$(instance)"
    echo "instance      $inst"
    echo "timer         enabled=$(systemctl is-enabled "$UNIT_NAME.timer" 2>/dev/null || echo no) active=$(systemctl is-active "$UNIT_NAME.timer" 2>/dev/null || echo no)"
    echo "image         $("$DOCKER" image inspect --format '{{.Id}}' "$inst-embedder" 2>/dev/null || echo 'absent')"
    dir="$(exchange_dir || true)"
    echo "exchange      ${dir:-<no volume>}"
    if [ -n "$dir" ] && [ -f "$dir/heartbeat" ]; then echo "heartbeat     $(cat "$dir/heartbeat")"; else echo "heartbeat     none"; fi
}

#: The image costs 5.5 GB and its rebuild took 9.5 GB: a build is refused before it starts when the disk could not hold it.
MIN_FREE_DEFAULT_GIB=12

free_gib() {
    if [ -n "${EMBED_FREE_GIB:-}" ]; then printf '%s' "$EMBED_FREE_GIB"; return 0; fi
    local root
    root="$("$DOCKER" info --format '{{.DockerRootDir}}' 2>/dev/null || true)"
    [ -n "$root" ] && [ -d "$root" ] || root=/
    df -Pk "$root" | awk 'NR == 2 { print int($4 / 1048576) }'
}

# The image of the service `embedder`: built when it is absent, after the check of the disk, and left alone when it is there (a rebuild is a
# decision: ALPHA_EMBEDDER_REBUILD=yes in the environment of this call). deploy.sh runs it only when ALPHA_EMBEDDER=yes.
build_image() {
    local inst image minimum free
    inst="$(instance)"
    image="$inst-embedder"
    if "$DOCKER" image inspect "$image" >/dev/null 2>&1 && [ "${ALPHA_EMBEDDER_REBUILD:-no}" != yes ]; then
        echo "embed-window.sh: the image $image is present and is not rebuilt (ALPHA_EMBEDDER_REBUILD=yes rebuilds it)."
        return 0
    fi
    minimum="$(configured ALPHA_EMBEDDER_BUILD_MIN_FREE_GB)"
    [ -n "$minimum" ] || minimum="$MIN_FREE_DEFAULT_GIB"
    case "$minimum" in ''|*[!0-9]*) refuse "ALPHA_EMBEDDER_BUILD_MIN_FREE_GB is '$minimum', which is not a whole number of GiB." ;; esac
    free="$(free_gib)"
    if [ "$free" -lt "$minimum" ]; then
        refuse "the disk cannot hold the encoder's image: $free GiB free, $minimum GiB needed." \
               "The image is 5.5 GB and its rebuild took 9.5 GB (docs/program/W54-EMBED-BUILD-01.md)." \
               "Free space, or set ALPHA_EMBEDDER=no to leave the night encoder off. Nothing was built."
    fi
    echo "embed-window.sh: building $image ($free GiB free, $minimum GiB needed)"
    BUILDX_NO_DEFAULT_ATTESTATIONS=1 "$DOCKER" compose --env-file "$ENV_FILE" --file "$COMPOSE_FILE" --profile embedder build embedder \
        || refuse "the build of the encoder's image failed."
    "$DOCKER" image inspect "$image" >/dev/null 2>&1 || refuse "the build reported success and there is no image $image."
    echo "embed-window.sh: $image is built"
}

# What the stand needs for the night encoder to run: the image, the timer enabled and active, and a heartbeat from the timer (it ran within the
# last ten minutes). Each is a refusal that says which; nothing is claimed that was not asked.
verify() {
    local inst dir age beat
    inst="$(instance)"
    "$DOCKER" image inspect "$inst-embedder" >/dev/null 2>&1 \
        || refuse "the encoder's image $inst-embedder is not on this host." "Run deploy.sh with ALPHA_EMBEDDER=yes."
    systemctl is-enabled "$UNIT_NAME.timer" >/dev/null 2>&1 \
        || refuse "the timer $UNIT_NAME.timer is not enabled." "Run infra/deploy/embed-window.sh install (as root)."
    systemctl is-active "$UNIT_NAME.timer" >/dev/null 2>&1 \
        || refuse "the timer $UNIT_NAME.timer is not active." "systemctl start $UNIT_NAME.timer"
    dir="$(exchange_dir || true)"
    if [ -z "$dir" ] || [ ! -f "$dir/heartbeat" ]; then
        refuse "the timer has never written a heartbeat in the exchange." "Is the stack up, and has the timer run?"
    fi
    beat="$(sed -n 's/^epoch=//p' "$dir/heartbeat" | tail -1)"
    case "$beat" in ''|*[!0-9]*) refuse "the heartbeat in $dir is not epoch=<n>." ;; esac
    age=$(( $(now) - beat ))
    [ "$age" -le 600 ] || refuse "the timer's last heartbeat is $age s old (more than 600)." "The worker opens no window for a host that is silent."
    echo "embed-window.sh: the image, the timer and the heartbeat ($age s old) are in place."
}

case "$COMMAND" in
    build-image) build_image ;;
    verify) verify ;;
    tick) tick ;;
    install) install_units ;;
    status) status ;;
    *) refuse "unknown command: $COMMAND" "usage: embed-window.sh tick|install|status|build-image|verify [--env-file <path>]" ;;
esac
