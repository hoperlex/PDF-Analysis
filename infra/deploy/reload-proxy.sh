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
# `nginx -s reload` is enough -- the workers restart and resolve the names again -- and it
# is preferred to restarting the container because it keeps the proxy's own uptime honest.
# If the configuration is broken the reload is refused and the OLD workers keep serving, so
# this tests the configuration first and says which happened.
#
# This is deliberately its own script and not a flag on something else: the thing that goes
# wrong is that somebody stops after the build, and a step that has a name is a step that
# can appear in a runbook.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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

# A reload with a broken configuration is refused and the old workers keep serving, which
# is the safe behaviour and also the confusing one: the command "succeeds" at leaving the
# 502 in place. So the configuration is tested first and a failure here is a failure.
if ! docker exec "$PROXY" nginx -t; then
    printf '\nreload-proxy.sh: the proxy configuration is not valid.\n' >&2
    printf '  Nothing was reloaded and the old workers are still serving. Fix\n' >&2
    printf '  proxy/nginx.conf; a reload would have been refused anyway.\n' >&2
    exit 5
fi

docker exec "$PROXY" nginx -s reload
echo "reload-proxy.sh: the proxy re-resolved its upstreams."
echo "reload-proxy.sh: confirm with  infra/deploy/verify-deployed.sh"
