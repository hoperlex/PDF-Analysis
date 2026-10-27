#!/bin/sh
# THE ACME LOOP -- `PROD-01-TLS-ACME-01`, `ADR-0021` section 2, `R-146aa`. POSIX `sh` (busybox in the
# image). It never exits on a failed attempt: a certificate authority that is unreachable, a name that does
# not resolve yet or a rate limit are all reasons to try again LATER, and a container that exited would be
# restarted by compose at once and ask again at once -- which is how a rate limit becomes a ban.
#
#   1. wait until the proxy actually serves the webroot (a probe file written here, fetched through the
#      proxy's challenge listener), so the first request to the authority is not wasted on a proxy that has
#      not finished starting;
#   2. `certbot certonly --webroot --keep-until-expiring`: issues when there is no certificate for the
#      lineage, renews when it is within certbot's own renewal window (30 days), does nothing otherwise.
#      One command for all three, so there is one path to reason about;
#   3. `export-pair.sh` copies the pair into the volume the proxy reads. Called after EVERY pass, not only
#      from certbot's deploy hook, so a lost export volume heals on the next pass;
#   4. sleep, and again.
#
# THE LINEAGE NAME. Staging and production are different lineages (`<name>-staging` and `<name>`), so the
# rehearsal never occupies the production name and the switch is a change of one setting, not an overwrite
# (certbot would otherwise ask whether to replace). `export-pair.sh` refuses to put a staging pair over a
# production one.
#
# WHAT NEVER HAPPENS HERE: no Docker socket, no signal to another container, no write outside the three
# volumes. The setting names are validated again because they reach a command line.
#
# The `ACME_*` path variables and `ACME_ONCE` exist so `tests/integration/composition/test_acme_client.py`
# can drive this loop against a stand-in `certbot`; the compose overlay sets only the three the operator
# controls.

set -eu

log() { printf 'acme: %s\n' "$*" >&2; }
die() { log "REFUSED: $*"; exit 2; }

NAME="${ACME_NAME:-}"
EMAIL="${ACME_EMAIL:-}"
STAGING="${ACME_STAGING:-yes}"
WEBROOT="${ACME_WEBROOT:-/var/www/acme}"
CONFIG="${ACME_CONFIG_DIR:-/etc/letsencrypt}"
WORKDIR="${ACME_WORK_DIR:-/var/lib/letsencrypt}"
LOGS="${ACME_LOGS_DIR:-/var/log/letsencrypt}"
CERTBOT="${ACME_CERTBOT:-certbot}"
EXPORT_PAIR="${ACME_EXPORT_PAIR:-/usr/local/bin/export-pair.sh}"
PROBE_BASE="${ACME_PROBE_BASE:-http://proxy:8081}"
PASS_SECONDS="${ACME_PASS_SECONDS:-43200}"
PROBE_TRIES="${ACME_PROBE_TRIES:-40}"

# --- the settings, validated -----------------------------------------------------------------------
[ -n "$NAME" ] || die "ACME_NAME is empty; the overlay passes ALPHA_CERT_NAME and refuses to start without it."
case "$NAME" in
    *[!a-z0-9.-]*|.*|*.|*..*|-*|*-) die "ACME_NAME is not a lower-case DNS name." ;;
    *.*) ;;
    *) die "ACME_NAME is a single label, not a public DNS name." ;;
esac
case "$STAGING" in
    yes) LINEAGE="$NAME-staging" ;;
    no) LINEAGE="$NAME" ;;
    *) die "ACME_STAGING is '$STAGING', which is neither yes nor no." ;;
esac
case "$EMAIL" in
    '') ;;
    *[!A-Za-z0-9@._+-]*) die "ACME_EMAIL holds a character an address does not need." ;;
    *@*.*) ;;
    *) die "ACME_EMAIL is not an address." ;;
esac

if [ "$STAGING" = yes ]; then
    log "STAGING: certificates come from the authority's test endpoint, are trusted by no browser and are"
    log "  for the rehearsal only (ALPHA_ACME_STAGING=no is the production issuance)."
else
    log "PRODUCTION: certificates come from the authority's real endpoint and count against its rate limits."
fi
log "name $NAME, lineage $LINEAGE."

# --- one pass --------------------------------------------------------------------------------------
webroot_is_served() {
    probe_dir="$WEBROOT/.well-known/acme-challenge"
    probe_file="$probe_dir/probe-$$"
    mkdir -p "$probe_dir"
    printf 'ok\n' > "$probe_file"
    tries=0
    until wget -q -T 3 -O - "$PROBE_BASE/.well-known/acme-challenge/probe-$$" 2>/dev/null | grep -q '^ok$'; do
        tries=$((tries + 1))
        if [ "$tries" -ge "$PROBE_TRIES" ]; then
            rm -f "$probe_file"
            return 1
        fi
        sleep 3
    done
    rm -f "$probe_file"
    return 0
}

obtain() {
    set -- certonly --non-interactive --agree-tos --webroot -w "$WEBROOT" -d "$NAME" \
        --cert-name "$LINEAGE" --keep-until-expiring \
        --config-dir "$CONFIG" --work-dir "$WORKDIR" --logs-dir "$LOGS" \
        --deploy-hook "$EXPORT_PAIR"
    if [ "$STAGING" = yes ]; then
        set -- "$@" --staging
    fi
    if [ -n "$EMAIL" ]; then
        set -- "$@" -m "$EMAIL"
    else
        set -- "$@" --register-unsafely-without-email
    fi
    "$CERTBOT" "$@"
}

export_pair() {
    RENEWED_LINEAGE="$CONFIG/live/$LINEAGE" "$EXPORT_PAIR"
}

attempt=0
while :; do
    if ! webroot_is_served; then
        log "the proxy did not serve the webroot in time (is the proxy up, and is the challenge listener loaded?). Asking the authority anyway would only spend an attempt."
        ok=no
    elif obtain && export_pair; then
        ok=yes
    else
        ok=no
    fi
    if [ "$ok" = yes ]; then
        attempt=0
        log "the certificate for $NAME is in place and exported; next pass in ${PASS_SECONDS}s."
        pause="$PASS_SECONDS"
    else
        attempt=$((attempt + 1))
        # 1 minute, 5, 15, then hourly: four tries inside the first hour stays under the authority's
        # failed-validation limit (five per hostname per hour), and it still recovers from a proxy that was
        # slow to start without waiting an hour for it.
        case "$attempt" in
            1) pause=60 ;;
            2) pause=300 ;;
            3) pause=900 ;;
            *) pause=3600 ;;
        esac
        log "no certificate yet (attempt $attempt). The reasons are in the lines above and in $LOGS. Trying again in ${pause}s."
    fi
    if [ "${ACME_ONCE:-}" = 1 ]; then
        [ "$ok" = yes ] && exit 0
        exit 1
    fi
    sleep "$pause"
done
