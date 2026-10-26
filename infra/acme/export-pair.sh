#!/bin/sh
# THE EXPORT -- `PROD-01-TLS-ACME-01`. Copies the certificate pair of ONE lineage into the volume the
# `proxy` mounts read-only at `/etc/nginx/tls`, under the two names `enable-tls.sh` looks for. It is certbot's
# deploy hook (certbot sets RENEWED_LINEAGE to the lineage's `live/` directory) and it is also called by
# `entrypoint.sh` after every pass, so it must be safe to run any number of times.
#
#   * the account key and the rest of certbot's state are NOT exported: the proxy, which faces the public
#     network, sees the certificate and its key and nothing that could register or revoke as this account;
#   * each file is written beside its destination and renamed into place, so a reader sees the old file or
#     the new one, never half of one. Two files cannot be swapped together, so for a moment during a renewal
#     the key can be new while the chain is old: the proxy's watcher tests the configuration before it
#     reloads (`nginx -t` rejects a mismatched pair) and tries again on its next tick;
#   * a STAGING pair never replaces a production one: a host whose setting was lost (the default is
#     `ALPHA_ACME_STAGING=yes`) would otherwise swap a trusted certificate for one no browser accepts.
#
# Exit 0 exported (or already identical); 1 nothing exported, with the reason on stderr.

set -eu

log() { printf 'export-pair: %s\n' "$*" >&2; }

LIVE="${RENEWED_LINEAGE:-}"
EXPORT="${ACME_EXPORT:-/export}"
[ -n "$LIVE" ] || { log "RENEWED_LINEAGE is not set; there is no lineage to export."; exit 1; }
SRC_CERT="$LIVE/fullchain.pem"
SRC_KEY="$LIVE/privkey.pem"
if [ ! -s "$SRC_CERT" ] || [ ! -s "$SRC_KEY" ]; then
    log "$LIVE does not hold both fullchain.pem and privkey.pem; nothing was exported."
    exit 1
fi

# >>> step: no-staging-over-production
issuer_of() { openssl x509 -in "$1" -noout -issuer 2>/dev/null || true; }
if [ -s "$EXPORT/fullchain.pem" ]; then
    case "$(issuer_of "$SRC_CERT")" in
        *STAGING*)
            case "$(issuer_of "$EXPORT/fullchain.pem")" in
                *STAGING*) ;;
                *)
                    log "REFUSED: the exported certificate is a production one and $LIVE holds a STAGING one."
                    log "  Nothing was changed. If this host is meant to rehearse again, remove the exported pair first."
                    exit 1 ;;
            esac ;;
    esac
fi
# <<< step: no-staging-over-production

if cmp -s "$SRC_CERT" "$EXPORT/fullchain.pem" 2>/dev/null && cmp -s "$SRC_KEY" "$EXPORT/privkey.pem" 2>/dev/null; then
    log "the exported pair is already the one in $LIVE."
    exit 0
fi

umask 077
NEW_KEY="$EXPORT/.privkey.pem.new"
NEW_CERT="$EXPORT/.fullchain.pem.new"
cp -L "$SRC_KEY" "$NEW_KEY"
cp -L "$SRC_CERT" "$NEW_CERT"
chmod 600 "$NEW_KEY"
chmod 644 "$NEW_CERT"
mv -f "$NEW_KEY" "$EXPORT/privkey.pem"
mv -f "$NEW_CERT" "$EXPORT/fullchain.pem"
log "exported the pair of $LIVE to $EXPORT; the proxy picks it up on its next tick."
exit 0
