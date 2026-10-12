#!/usr/bin/env bash
# `W54-STAND-COPY-01` -- what a host has room for, measured, and optionally a refusal when
# it has too little. Read-only; it never calls docker.
#
#   capacity-probe.sh [--path <label>=<absolute path>]... [--need <label>=<bytes>]... \
#                     [--need-ram <bytes>]
#
# Two callers, one measurement:
#
#   * the copy key's `capacity` verb on the stand (`copy-serve.sh`) prints the Docker data
#     root, staging and the copy directory through it, beside what only docker can say;
#   * this host's heavy-step stop rule (`W54-PLAN.md` §3.9, `W54-FREEZE-01`): a heavy step
#     starts only if its filesystem has its increment + 3 GiB free and at least 6 GiB of RAM
#     is available, swap not counted, both measured just before it starts:
#
#       infra/deploy/capacity-probe.sh --path root=/ --need root=$(( (2 + 3) * 1073741824 )) \
#           --need-ram $(( 6 * 1073741824 ))
#
# Output, one fact per line:
#
#   path <label>: <path> filesystem=<device> mount=<mount point> avail_bytes=<n> size_bytes=<n>
#   path <label>: <path> absent
#   ram_available_bytes: <n>          MemAvailable; swap is never added to it
#   swap_total_bytes: <n>
#   swap_free_bytes: <n>
#   load: <1 min> <5 min> <15 min>
#   need <mount point>: <bytes> of <avail> (<labels>)
#
# NEEDS ARE SUMMED PER FILESYSTEM. Two labels on one filesystem (staging and the copy
# directory, say) share its free space, and §3.9's "bundle + dump + 2 GiB" is exactly that
# sum. A need on a label whose path is absent or unmeasured is refused, never skipped.
#
# Exit: 0 measured (and every need met); 2 usage; 3 refused (`REFUSED [<guard>]`).

set -euo pipefail
export LC_ALL=C

refuse() {
    local guard="$1"
    shift
    printf 'capacity-probe.sh: REFUSED [%s]: %s\n' "$guard" "$1" >&2
    shift
    [ "$#" -eq 0 ] || printf '  %s\n' "$@" >&2
    exit 3
}

usage() {
    sed -n '5,6p' "${BASH_SOURCE[0]}" | sed 's/^# //' >&2
    exit 2
}

LABELS=()
PATHS=()
NEED_LABELS=()
NEED_BYTES=()
NEED_RAM=""

# >>> guard: known-options
while [ "$#" -gt 0 ]; do
    case "$1" in
        --path)
            [[ ${2:-} =~ ^([a-z_]+)=(.+)$ ]] || refuse known-options "--path takes <label>=<path>, got '${2:-}'."
            LABELS+=("${BASH_REMATCH[1]}")
            PATHS+=("${BASH_REMATCH[2]}")
            shift 2 ;;
        --need)
            [[ ${2:-} =~ ^([a-z_]+)=([0-9]+)$ ]] || refuse known-options "--need takes <label>=<bytes>, got '${2:-}'."
            NEED_LABELS+=("${BASH_REMATCH[1]}")
            NEED_BYTES+=("${BASH_REMATCH[2]}")
            shift 2 ;;
        --need-ram)
            [[ ${2:-} =~ ^[0-9]+$ ]] || refuse known-options "--need-ram takes a byte count, got '${2:-}'."
            NEED_RAM="$2"
            shift 2 ;;
        -h|--help) usage ;;
        *) refuse known-options "unrecognised option: $1" "Nothing was measured." ;;
    esac
done
# <<< guard: known-options

meminfo() {
    awk -v name="$1:" '$1 == name { printf "%d\n", $2 * 1024; found = 1 } END { exit !found }' /proc/meminfo
}

declare -A MOUNT_OF=()
declare -A AVAIL_OF=()
for index in "${!LABELS[@]}"; do
    label="${LABELS[$index]}"
    path="${PATHS[$index]}"
    if [ -e "$path" ] && line="$(df -B1 --output=source,target,avail,size -- "$path" 2>/dev/null | tail -n 1)"; then
        read -r device target avail size <<< "$line"
        MOUNT_OF[$label]="$target"
        AVAIL_OF[$target]="$avail"
        printf 'path %s: %s filesystem=%s mount=%s avail_bytes=%s size_bytes=%s\n' \
            "$label" "$path" "$device" "$target" "$avail" "$size"
    else
        printf 'path %s: %s absent\n' "$label" "$path"
    fi
done

RAM_AVAILABLE="$(meminfo MemAvailable)"
printf 'ram_available_bytes: %s\n' "$RAM_AVAILABLE"
printf 'swap_total_bytes: %s\n' "$(meminfo SwapTotal)"
printf 'swap_free_bytes: %s\n' "$(meminfo SwapFree)"
printf 'load: %s\n' "$(cut -d' ' -f1-3 /proc/loadavg)"

declare -A NEED_ON=()
declare -A NAMES_ON=()
for index in "${!NEED_LABELS[@]}"; do
    label="${NEED_LABELS[$index]}"
    # >>> guard: need-measured
    if [ -z "${MOUNT_OF[$label]:-}" ]; then
        refuse need-measured "a need was given for '$label', whose path is absent or was not named with --path."
    fi
    # <<< guard: need-measured
    mount="${MOUNT_OF[$label]}"
    NEED_ON[$mount]=$(( ${NEED_ON[$mount]:-0} + NEED_BYTES[index] ))
    NAMES_ON[$mount]="${NAMES_ON[$mount]:+${NAMES_ON[$mount]} }$label"
done

short=()
for mount in "${!NEED_ON[@]}"; do
    printf 'need %s: %s of %s (%s)\n' "$mount" "${NEED_ON[$mount]}" "${AVAIL_OF[$mount]}" "${NAMES_ON[$mount]}"
    if [ "${AVAIL_OF[$mount]}" -lt "${NEED_ON[$mount]}" ]; then
        short+=("$mount needs ${NEED_ON[$mount]} bytes for ${NAMES_ON[$mount]} and has ${AVAIL_OF[$mount]}")
    fi
done
# >>> guard: disk-has-room
if [ "${#short[@]}" -gt 0 ]; then
    refuse disk-has-room "a filesystem has less free space than the step needs." "${short[@]}"
fi
# <<< guard: disk-has-room

# >>> guard: ram-available
if [ -n "$NEED_RAM" ] && [ "$RAM_AVAILABLE" -lt "$NEED_RAM" ]; then
    refuse ram-available "$RAM_AVAILABLE bytes of RAM are available; the step needs $NEED_RAM (swap does not count)."
fi
# <<< guard: ram-available
