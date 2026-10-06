#!/usr/bin/env bash
# `D-27`, second face -- A REBUILD IS NOT FINISHED WHEN THE IMAGES ARE.
#
#   infra/deploy/reload-proxy.sh [--env-file <path>]
#
# `docker compose up -d --build` replaces the api and web containers, and each replacement
# gets a new address on the compose network. nginx resolves an upstream ONCE, at worker
# start-up, and holds it: the name `api` in `proxy_pass http://api:8000/` is looked up when
# the configuration is loaded and not again. So after a rebuild the proxy is pointing at
# containers that no longer exist, and **every path through it answers 502** while both new
# containers are healthy and the compose output says nothing is wrong.
#
# That was measured on this stack, not reasoned about, and it cost a session an afternoon of
# looking at the application for a fault that was in front of it.
#
# AND IT IS INTERMITTENT, WHICH IS WHY IT SURVIVED THREE WAVES. Driven on this host with a
# pinned nginx and a throwaway upstream: replacing the upstream container normally gives it
# back THE SAME address, and then the proxy carries on answering 200 and nothing looks
# wrong. Only when the replacement lands somewhere else does it break -- forced by moving
# the name to a different address, the proxy went on connecting to the old one and answered
# **502** with the DNS name already resolving elsewhere, and `nginx -s reload` put it back
# to 200 on the next request. So "the last rebuild was fine" is not evidence, and running
# this after every rebuild costs a second and removes a coin flip.
#
# `nginx -s reload` is enough FOR THE UPSTREAMS -- the workers restart and resolve the names
# again -- and it is preferred to restarting the container because it keeps the proxy's own
# uptime honest. If the configuration is broken the reload is refused and the OLD workers
# keep serving, so this tests the configuration first and says which happened.
#
# IT IS NOT ENOUGH FOR A CHANGED CONFIGURATION FILE, AND THAT IS `W49-FIX` / `B-1`.
# `compose.server.yml` bind-mounts `proxy/nginx.conf` as a SINGLE FILE, and a single-file
# bind mount is pinned to the inode the file had when the container started. `git checkout`
# does not rewrite a changed file in place: it writes a new file and renames it over the old
# one, so the path gets a NEW inode and the container keeps the old one. Measured by
# `W49-JUDGE-X` on the pinned image (`docs/program/reviews/W49-JUDGE-X.md` section 7.4):
# inode 2132108 -> 2132118 after the checkout, and both `nginx -t` and `nginx -s reload`
# inside the container read the OLD file -- so this script used to test the old
# configuration, reload the old configuration and report success, while every proxy change
# since the container was created stayed unserved (`W49-EDGE-01`'s throttle among them).
# Only a container restart re-resolves the mount.
#
# So before it reloads, this script asks the running proxy what it sees: for every
# single-file bind mount it compares the SHA-256 of the file at the host path with the
# SHA-256 of the file inside the container. If any differ, the checkout's configuration is
# first tested in a THROWAWAY container with the same image, network and mounts -- a broken
# file is refused there and the running proxy is not touched, which is the property the
# reload always had -- and only then is the proxy RESTARTED, once, and asked again. A proxy
# that still does not see the checkout after that is a failure, not a success.
#
# WHY A RESTART AND NOT A RECREATE OR A DIRECTORY MOUNT. `docker restart` re-resolves every
# bind mount by path and keeps everything else about the container: its id, its published
# ports and every mount it was created with -- including the TLS overlay's
# (`proxy/compose.tls.yml`), which this script does not know about and must not drop. A
# `compose up --force-recreate` from here would rebuild the container from
# `compose.server.yml` alone and silently lose that overlay. A directory mount would need
# `proxy/**` to change, and the overlay's own single-file mounts would still pin inodes.
#
# AN UNCHANGED CONFIGURATION RESTARTS NOTHING. The comparison is the only thing that decides
# a restart, so a second deploy of the same tree reloads and leaves the container's start
# time where it was (`W24-IDEM`'s rule, proved in
# `tests/integration/composition/test_proxy_config_follows_checkout.py`).
#
# This is deliberately its own script and not a flag on something else: the thing that goes
# wrong is that somebody stops after the build, and a step that has a name is a step that
# can appear in a runbook.
#
# Exit 0 the proxy reads this checkout's configuration and has reloaded it; 2 usage;
# 4 there is nothing to ask; 5 the configuration is not valid and nothing was changed;
# 6 the proxy does not read this checkout's configuration and this script could not make it.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERE_PHYSICAL="$(cd "$HERE" && pwd -P)"
COMPOSE_FILE="$HERE/compose.server.yml"
ENV_FILE="${ALPHA_ENV_FILE:-$HERE/env/alpha.env}"

while [ "$#" -gt 0 ]; do
    case "$1" in
        --env-file) ENV_FILE="${2:-}"; shift 2 ;;
        -h|--help) sed -n '3p' "${BASH_SOURCE[0]}" >&2; exit 2 ;;
        *) printf 'reload-proxy.sh: unrecognised option: %s\n' "$1" >&2; exit 2 ;;
    esac
done

[ -r "$ENV_FILE" ] || { printf 'reload-proxy.sh: %s is missing.\n' "$ENV_FILE" >&2; exit 4; }
[ -r "$COMPOSE_FILE" ] || { printf 'reload-proxy.sh: %s is missing.\n' "$COMPOSE_FILE" >&2; exit 4; }

compose() { docker compose --env-file "$ENV_FILE" --file "$COMPOSE_FILE" "$@"; }

PROXY="$(compose ps --quiet proxy 2>/dev/null | head -1)"
if [ -z "$PROXY" ]; then
    printf 'reload-proxy.sh: no running proxy container for this instance.\n' >&2
    printf '  There is nothing to reload. Bring the stack up first.\n' >&2
    exit 4
fi

drifted() {
    printf '\nreload-proxy.sh: %s\n' "$1" >&2
    shift
    [ "$#" -eq 0 ] || printf '  %s\n' "$@" >&2
    exit 6
}

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# Is a bind-mount source this checkout's proxy configuration? Both spellings of this
# directory are accepted: compose passes the path it was given, and a clone reached through
# a symlink has two.
own_source() {
    case "$1" in
        "$HERE"/proxy/*|"$HERE_PHYSICAL"/proxy/*) return 0 ;;
        *) return 1 ;;
    esac
}

# --- what the running proxy has mounted, and whether it is this checkout's --------------
# Read from the container, not from the compose file: the container is what serves, and it
# may have been created with an overlay this script never names.
read_mounts() {
    docker inspect --format \
        '{{range .Mounts}}{{if eq .Type "bind"}}{{.Source}}{{"\t"}}{{.Destination}}{{"\n"}}{{end}}{{end}}' \
        "$PROXY" > "$WORK/mounts" 2>/dev/null || {
        printf 'reload-proxy.sh: the proxy container %s could not be inspected.\n' "$PROXY" >&2
        exit 4
    }
}

read_mounts
FOREIGN=""
SAW_NGINX_CONF=no
while IFS=$'\t' read -r source destination; do
    [ -n "$source" ] || continue
    if ! own_source "$source"; then
        FOREIGN="$FOREIGN$destination  mounted from $source"$'\n'
        continue
    fi
    case "$source" in
        "$HERE"/proxy/nginx.conf|"$HERE_PHYSICAL"/proxy/nginx.conf) SAW_NGINX_CONF=yes ;;
    esac
    if [ ! -e "$source" ]; then
        FOREIGN="$FOREIGN$destination  mounted from $source, which no longer exists"$'\n'
    fi
done < "$WORK/mounts"
[ "$SAW_NGINX_CONF" = yes ] || \
    FOREIGN="${FOREIGN}no mount of $HERE/proxy/nginx.conf at all"$'\n'
if [ -n "$FOREIGN" ]; then
    # A restart re-reads the SAME paths, so it cannot fix this one; saying so is better than
    # restarting and then reporting that it did not help.
    drifted "the running proxy was not created from this checkout's proxy configuration." \
        "$(printf '%s' "$FOREIGN" | sed 's/^/  /')" \
        "Nothing was reloaded or restarted. Recreate it from this checkout, with the same" \
        "-f files it was created with (add proxy/compose.tls.yml if TLS is on):" \
        "    docker compose --env-file $ENV_FILE -f $COMPOSE_FILE up -d --force-recreate proxy"
fi

# Every single-file bind mount whose bytes inside the container differ from the bytes at its
# host path. A directory mount follows its directory and is not affected; it is not asked.
# Prints one line per stale file and nothing when the proxy sees the checkout.
stale_files() {
    : > "$WORK/expected"
    : > "$WORK/wanted"
    while IFS=$'\t' read -r source destination; do
        [ -f "$source" ] || continue
        printf '%s\n' "$destination" >> "$WORK/wanted"
        printf '%s  %s\n' "$(sha256sum "$source" | cut -d' ' -f1)" "$destination" \
            >> "$WORK/expected"
    done < "$WORK/mounts"
    tr '\n' '\0' < "$WORK/wanted" > "$WORK/wanted.z"
    docker exec -i "$PROXY" sh -c 'xargs -0 -r sha256sum 2>/dev/null || true' \
        < "$WORK/wanted.z" > "$WORK/actual" || true
    LC_ALL=C sort -k2 "$WORK/expected" > "$WORK/expected.s"
    LC_ALL=C sort -k2 "$WORK/actual" > "$WORK/actual.s"
    LC_ALL=C join -j 2 -v 1 -o 0 "$WORK/expected.s" "$WORK/actual.s" \
        | sed 's/$/  not readable inside the proxy/'
    LC_ALL=C join -j 2 -o 0,1.1,2.1 "$WORK/expected.s" "$WORK/actual.s" \
        | awk '$2 != $3 { print $1 "  the proxy reads other bytes than the checkout holds" }'
}

STALE="$(stale_files)"
RESTARTED=no
if [ -n "$STALE" ]; then
    printf 'reload-proxy.sh: the running proxy is not reading this checkout'"'"'s configuration:\n'
    printf '%s\n' "$STALE" | sed 's/^/  /'
    printf '  (a single-file bind mount keeps the inode it was started with; a reload re-reads\n'
    printf '   that old file, so the proxy is restarted once the new configuration is tested)\n'

    # The checkout's configuration, tested where the running proxy cannot be hurt: a
    # throwaway container from the SAME image, on the SAME network -- so `api` and `web`
    # resolve exactly as they will after the restart -- with the SAME mounts, read-only, and
    # the image's own entrypoint, so the start-up hooks a restart would run (the TLS switch
    # among them) run here first.
    IMAGE="$(docker inspect --format '{{.Image}}' "$PROXY")"
    NETWORK="$(docker inspect --format \
        '{{range $name, $value := .NetworkSettings.Networks}}{{$name}}{{"\n"}}{{end}}' "$PROXY" \
        | head -1)"
    CANDIDATE=(docker run --rm)
    [ -z "$NETWORK" ] || CANDIDATE+=(--network "$NETWORK")
    while IFS=$'\t' read -r source destination; do
        [ -n "$source" ] || continue
        CANDIDATE+=(-v "$source:$destination:ro")
    done < "$WORK/mounts"
    CANDIDATE+=("$IMAGE" nginx -t)
    if ! "${CANDIDATE[@]}"; then
        printf '\nreload-proxy.sh: the checkout'"'"'s proxy configuration is not valid.\n' >&2
        printf '  It was tested in a throwaway container. The running proxy was NOT restarted\n' >&2
        printf '  and still serves the configuration it started with. Fix proxy/nginx.conf.\n' >&2
        exit 5
    fi

    # >>> step: restart-on-stale
    # THE REPAIR. A restart re-resolves every bind mount by path; nothing else does.
    docker restart "$PROXY" >/dev/null
    RESTARTED=yes
    echo "reload-proxy.sh: the proxy was restarted so that it reads this checkout's files."
    # <<< step: restart-on-stale

    STALE="$(stale_files)"
    if [ -n "$STALE" ]; then
        drifted "the proxy still does not read this checkout's configuration." \
            "$(printf '%s' "$STALE" | sed 's/^/  /')" \
            "A reload would re-read the old file and report success, so nothing is claimed." \
            "Restart it by hand and run this again:  docker restart $PROXY"
    fi
fi
echo "reload-proxy.sh: the proxy reads this checkout's configuration" \
     "($(grep -c . "$WORK/expected" || true) mounted file(s), byte for byte)."

# A reload with a broken configuration is refused and the old workers keep serving, which
# is the safe behaviour and also the confusing one: the command "succeeds" at leaving the
# 502 in place. So the configuration is tested first and a failure here is a failure.
if ! docker exec "$PROXY" nginx -t; then
    printf '\nreload-proxy.sh: the proxy configuration is not valid.\n' >&2
    printf '  Nothing was reloaded and the old workers are still serving. Fix\n' >&2
    printf '  proxy/nginx.conf; a reload would have been refused anyway.\n' >&2
    exit 5
fi

if [ "$RESTARTED" = yes ]; then
    # A restarted nginx needs a moment before it has a master to signal. Asked until it
    # answers, and bounded: a proxy that never comes back is a failure, said in words.
    tries=0
    until docker exec "$PROXY" nginx -s reload 2>/dev/null; do
        tries=$((tries + 1))
        [ "$tries" -lt 30 ] || drifted "the proxy was restarted and its nginx did not come back." \
            "Logs:  docker logs $PROXY"
        sleep 1
    done
else
    docker exec "$PROXY" nginx -s reload
fi
echo "reload-proxy.sh: the proxy re-resolved its upstreams."
echo "reload-proxy.sh: confirm with  infra/deploy/verify-deployed.sh"
