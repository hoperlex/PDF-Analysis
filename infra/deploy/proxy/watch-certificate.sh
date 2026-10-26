#!/bin/sh
# THE TIMER -- `PROD-01-TLS-ACME-01`, `ADR-0021` section 2: *"The `proxy` re-reads the certificate on a
# timer (a `nginx -s reload` loop started by an executable in `/docker-entrypoint.d/`, the mechanism
# `enable-tls.sh` already uses), so no service needs the right to restart another."* Mounted by
# `infra/acme/compose.acme.yml` at `/docker-entrypoint.d/27-watch-certificate.sh`, after the switch (25) and
# the trust list (26), and before nginx starts.
#
# WHAT IT STARTS, in the background, once: a loop that every `CERT_WATCH_SECONDS` (60) compares a
# fingerprint of the certificate pair with the one nginx was last told about, and on a difference
#
#   1. runs the switch again (`25-enable-tls.sh`): it installs the TLS server block when a pair now exists,
#      and un-installs it when one no longer does -- the single place that asks "is there a certificate?";
#   2. TESTS the configuration (`nginx -t`) and reloads only if it passes. A pair that was caught half way
#      through a renewal (new key, old chain) or that does not load is therefore NEVER applied: the running
#      workers keep what they had, and the next tick looks again. A pair that still does not load is logged
#      once, loudly, and the TLS block this tick installed is removed again, so a restart of the container
#      starts on the plain listeners and not on a configuration nginx refuses (which would take the whole
#      published port down);
#   3. says what it did on the container's log, which is `docker compose logs proxy`.
#
# WHY A LOOP AND NOT A SIGNAL. The renewal happens in ANOTHER container. Telling nginx to reload would need
# either the Docker socket or a shared PID namespace, and each of those is the right to restart a service on
# the public path. A shared read-only volume and a timer need neither, and the cost is a delay of at most the
# interval between a renewal and the proxy serving it -- a renewal happens 30 days before expiry and the
# check of `verify-deployed.sh` fails at 14, so a minute is not a margin anybody spends.
#
# `CERT_WATCH_SOURCE_ONLY=1` makes a sourcing shell stop after the definitions, the path variables name the
# files, and `CERT_WATCH_STOP` names a file that ends the background loop; they exist so
# `tests/integration/composition/test_acme_client.py` can drive the loop against a stand-in `nginx`. The
# compose overlay sets none of them.
#
# POSIX `sh`, because the pinned image is `nginx:1.27-alpine` and there is no bash in it.

set -eu

CERT="${CERT_WATCH_CERT:-/etc/nginx/tls/fullchain.pem}"
KEY="${CERT_WATCH_KEY:-/etc/nginx/tls/privkey.pem}"
SWITCH="${CERT_WATCH_SWITCH:-/docker-entrypoint.d/25-enable-tls.sh}"
TLS_CONF="${CERT_WATCH_TLS_CONF:-/etc/nginx/conf.d/tls.conf}"
CHALLENGE_CONF="${CERT_WATCH_CHALLENGE_CONF:-/etc/nginx/conf.d/acme-challenge.conf}"
NGINX="${CERT_WATCH_NGINX:-nginx}"
INTERVAL="${CERT_WATCH_SECONDS:-60}"

say() { printf 'watch-certificate: %s\n' "$*" >&2; }

# The overlay mounts this file together with the challenge block. Without that block there is no ACME and
# nothing to watch; saying so is better than a loop that watches a directory nobody writes.
if [ ! -f "$CHALLENGE_CONF" ]; then
    say "no $CHALLENGE_CONF, so this stack is not configured for ACME; not watching."
    exit 0
fi

case "$INTERVAL" in ''|*[!0-9]*) say "CERT_WATCH_SECONDS is '$INTERVAL', not a number of seconds."; exit 2 ;; esac

fingerprint() {
    if [ -s "$CERT" ] && [ -s "$KEY" ]; then
        sha256sum "$CERT" "$KEY" 2>/dev/null | cut -d' ' -f1 | tr '\n' ' '
    else
        printf 'absent'
    fi
}

LAST="$(fingerprint)"
REFUSED=""

# One comparison. Returns 0 always: a failed tick is a line on the log and a retry, never an exit.
tick() {
    now="$(fingerprint)"
    [ "$now" != "$LAST" ] || return 0
    [ "$now" != "$REFUSED" ] || return 0
    say "the certificate pair changed; applying it."
    "$SWITCH" || true
    if ! out="$("$NGINX" -t 2>&1)"; then
        # Is it the pair? Take the TLS block out and ask again. If nginx still refuses, the fault is not
        # the pair (an upstream that is down for a moment makes `nginx -t` fail on `host not found`), the
        # block goes back and this tick is simply tried again; blaming a good pair would leave a host on
        # plain listeners until its next renewal.
        # >>> step: refuse-an-unloadable-pair
        rm -f "$TLS_CONF"
        if "$NGINX" -t >/dev/null 2>&1; then
            REFUSED="$now"
            say "REFUSED: nginx does not accept this pair, so it was NOT applied and the TLS block was taken out again."
            say "  The running workers keep their configuration. nginx said:"
            printf '%s\n' "$out" | sed 's/^/  /' >&2
        else
            "$SWITCH" || true
            say "nginx refuses the configuration with and without the TLS block, so the pair is not the cause; trying again next tick. nginx said:"
            printf '%s\n' "$out" | sed 's/^/  /' >&2
        fi
        # <<< step: refuse-an-unloadable-pair
        return 0
    fi
    if "$NGINX" -s reload; then
        LAST="$now"
        say "nginx reloaded; the proxy serves the pair that is on the volume now."
    else
        say "the reload failed; the pair stays unapplied and the next tick tries again."
    fi
    return 0
}

# A test sources this file with CERT_WATCH_SOURCE_ONLY=1 to get `tick` and the state it keeps, changes the
# files, and calls `tick` itself; nothing is started. The overlay sets no such variable.
if [ "${CERT_WATCH_SOURCE_ONLY:-}" = 1 ]; then
    return 0
fi

# Detached from this hook's stdin, so the entrypoint's pipeline does not wait on it, and writing to the
# stderr this hook inherited, which is the container's log. The first tick is one interval away: nginx is
# not up yet, and the switch has just run.
(
    # `CERT_WATCH_STOP` names a file whose existence ends the loop; the overlay sets none, and an empty name is
    # never an existing file. It is how a test stops a loop it started without signalling a process.
    while [ ! -e "${CERT_WATCH_STOP:-}" ] && sleep "$INTERVAL"; do
        tick
    done
) </dev/null &
say "watching $CERT every ${INTERVAL}s; a changed pair is tested and applied by nginx -s reload."
exit 0
