#!/bin/sh
# THE TRUST LIST -- `REAL-IP-EDGE-01`, `D-144` / `D-191` `E-3`. Mounted by `compose.server.yml`
# at `/docker-entrypoint.d/26-trusted-proxies.sh`, where the official nginx image's entrypoint
# runs every executable `*.sh` BEFORE the master process starts (see `enable-tls.sh`, which
# uses the same hook, for the mechanism and for why it is the only place that can ask).
#
# WHAT IT DECIDES, and it is one question: which peers may tell this proxy who the client is?
# `nginx.conf` already says HOW a trusted peer does it (`real_ip_header X-Forwarded-For;
# real_ip_recursive on;`, at http level, so the plain and the TLS server block both inherit
# it). What it cannot say is WHO, because that is a fact about one host's network and not about
# this repository. This script turns the operator's `ALPHA_TRUSTED_PROXY_CIDRS` into the only
# `set_real_ip_from` lines the configuration will ever have:
#
#   empty  -> install nothing and REMOVE any file an earlier start left. No peer is trusted,
#             `X-Forwarded-For` is never read, and the container behaves exactly as it did
#             before this script existed. THAT IS THE DEFAULT, and it is the safe value: a
#             request can only be counted under the address of the TCP peer it came from.
#   a list -> write `conf.d/trusted-proxies.conf`, one `set_real_ip_from <cidr>;` per entry,
#             which the image's own `include /etc/nginx/conf.d/*.conf;` loads beside
#             `default.conf` (and beside `tls.conf` when TLS is on).
#   bad    -> REFUSE, exit 2, with the entry named. The entrypoint stops, so the container does
#             not start. It is not read as "empty": an operator who mistyped a CIDR and got the
#             shared bucket back would conclude that the switch does not work. `deploy.sh` runs
#             `--check` on the same value first, so a deploy normally never gets this far.
#
# THE VALUE IS TEXT PASTED INTO A CONFIGURATION FILE, so it is validated rather than quoted.
# An entry is an IPv4 address or an IPv6 address, optionally followed by `/<prefix length>`
# (1..32, 1..128). Nothing else: no host name (resolved at start-up, to whatever DNS says that
# day), no `all`, no `unix:`, no `;`, no `$`, no quote, no space inside an entry. A prefix
# length of 0 is refused by name because it is `0.0.0.0/0` -- "trust the whole internet" --
# which would let any client write its own address and is the hole this file exists to close.
# Entries are separated by commas and/or white space. An IPv6 entry must not carry a dotted
# IPv4 tail (`::ffff:1.2.3.4`); write the hex groups. `nginx -t` is the final judge of an IPv6
# literal; this check is what makes injection impossible.
#
# `--check` validates `$ALPHA_TRUSTED_PROXY_CIDRS` and writes nothing (that is how `deploy.sh`
# uses it, on the host, before anything is built). `TRUSTED_PROXIES_CONF` names the output file
# for a test; in the container it is never set.
#
# POSIX `sh`, because the pinned image is `nginx:1.27-alpine` and there is no bash in it.

set -eu

DST="${TRUSTED_PROXIES_CONF:-/etc/nginx/conf.d/trusted-proxies.conf}"
CHECK=no
case "${1:-}" in
    "") ;;
    --check) CHECK=yes ;;
    *) printf 'trusted-proxies: unrecognised argument: %s\n' "$1" >&2; exit 2 ;;
esac

say() { printf 'trusted-proxies: %s\n' "$*" >&2; }

# A decimal number without a sign, and without a leading zero (`010` is not `10` to every tool).
number() {
    case "$1" in
        0|[1-9]|[1-9][0-9]|[1-9][0-9][0-9]) return 0 ;;
        *) return 1 ;;
    esac
}

ipv4() {
    case "$1" in
        ''|*[!0-9.]*|.*|*.|*..*) return 1 ;;
    esac
    _ifs=$IFS
    IFS=.
    set -- $1
    IFS=$_ifs
    [ "$#" -eq 4 ] || return 1
    for _octet in "$1" "$2" "$3" "$4"; do
        number "$_octet" || return 1
        [ "$_octet" -le 255 ] || return 1
    done
}

ipv6() {
    _addr=$1
    case "$_addr" in
        ''|*[!0-9a-fA-F:]*|*:::*|*::*::*|:[!:]*|*[!:]:) return 1 ;;
        *:*:*) ;;
        *) return 1 ;;
    esac
    case "$_addr" in
        *::*) _head=${_addr%%::*}; _tail=${_addr#*::}; _squeezed=yes ;;
        *) _head=$_addr; _tail=""; _squeezed=no ;;
    esac
    _groups=0
    _ifs=$IFS
    for _part in "$_head" "$_tail"; do
        [ -n "$_part" ] || continue
        IFS=:
        for _group in $_part; do
            case "$_group" in
                ''|?????*) IFS=$_ifs; return 1 ;;
            esac
            _groups=$((_groups + 1))
        done
        IFS=$_ifs
    done
    if [ "$_squeezed" = yes ]; then
        [ "$_groups" -le 7 ]
    else
        [ "$_groups" -eq 8 ]
    fi
}

# Prints nothing; returns 0 for an acceptable entry and 1 for a refused one, with the reason in
# `$WHY`.
acceptable() {
    WHY=""
    _entry=$1
    case "$_entry" in
        */*/*) WHY="more than one '/'"; return 1 ;;
        */*) _address=${_entry%/*}; _length=${_entry#*/}; _has_length=yes ;;
        *) _address=$_entry; _length=""; _has_length=no ;;
    esac
    case "$_address" in
        *:*) _family=6; _max=128; ipv6 "$_address" || { WHY="not an IPv6 address"; return 1; } ;;
        *) _family=4; _max=32; ipv4 "$_address" || { WHY="not an IPv4 address (a host name is not accepted)"; return 1; } ;;
    esac
    if [ "$_has_length" = yes ]; then
        number "$_length" || { WHY="the prefix length is not a plain decimal number"; return 1; }
        if [ "$_length" -eq 0 ]; then
            WHY="a prefix length of 0 trusts every address on the internet"
            return 1
        fi
        if [ "$_length" -gt "$_max" ]; then
            WHY="the prefix length is above $_max"
            return 1
        fi
    fi
    return 0
}

ENTRIES="$(printf '%s' "${ALPHA_TRUSTED_PROXY_CIDRS:-}" | tr ',\t\r\n' '    ')"
set -f
OUT=""
COUNT=0
LISTED=""
for entry in $ENTRIES; do
    if ! acceptable "$entry"; then
        [ "$CHECK" = yes ] || rm -f "$DST"
        say "ALPHA_TRUSTED_PROXY_CIDRS holds '$entry', which is refused: $WHY."
        say "  An entry is an IPv4 or IPv6 address, optionally '/<prefix length>' (not 0); entries are"
        say "  separated by commas or spaces. See infra/deploy/README.md, 'The client address'."
        exit 2
    fi
    OUT="${OUT}set_real_ip_from ${entry};
"
    COUNT=$((COUNT + 1))
    LISTED="${LISTED:+$LISTED, }$entry"
done
set +f

[ "$CHECK" = no ] || exit 0

if [ "$COUNT" -eq 0 ]; then
    rm -f "$DST"
    say "ALPHA_TRUSTED_PROXY_CIDRS is empty: no peer is trusted to name the client, so"
    say "  X-Forwarded-For is ignored and every request is counted under its TCP peer's address."
    exit 0
fi

{
    printf '# Written by trusted-proxies.sh at container start from ALPHA_TRUSTED_PROXY_CIDRS.\n'
    printf '# Do not edit: the next start replaces it. nginx.conf says what these lines mean.\n'
    printf '%s' "$OUT"
} > "$DST"
say "$COUNT peer(s) trusted to name the client through X-Forwarded-For: $LISTED."
say "  Any other peer's X-Forwarded-For is ignored."
exit 0
