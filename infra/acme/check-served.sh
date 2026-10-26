#!/bin/sh
# THE SERVED CERTIFICATE, ASKED THE WAY A CLIENT WOULD -- `PROD-01-TLS-ACME-01`, `ADR-0021` rows 2 and 5.
# Runs inside the ACME image (it has `openssl` and the CA bundle), on the compose network, against the
# proxy's own TLS listener (`proxy:8443`), so `verify-deployed.sh` and `readiness.sh` need nothing on the
# host but docker -- the host promises no `openssl` (`DEPLOYMENT_RUNBOOK.md` section 1).
#
#   check-served.sh <name> <host:port> <minimum days> <production|staging>
#
# It asks the TLS listener for `<name>` (SNI) and checks three things, in this order, and names the first
# that fails:
#
#   10  nothing was served: no TLS answer, or no certificate in it;
#   13  the wrong kind: a STAGING certificate where production is expected, or the reverse;
#   12  production only: the chain does not verify against the CA bundle, or the name does not match;
#   11  the certificate expires within <minimum days>.
#
# `staging` replaces the chain check with its positive form -- the issuer must be the authority's STAGING
# one -- because a staging certificate is untrusted by design and a rehearsal needs to know it got the one
# it asked for. Exit 0 prints one `served-certificate: OK` line with the issuer and the expiry.

set -eu

NAME="${1:?name}"
TARGET="${2:?host:port}"
DAYS="${3:?minimum days}"
MODE="${4:?production|staging}"
case "$MODE" in production|staging) ;; *) echo "served-certificate: usage: mode is production or staging, not '$MODE'" >&2; exit 2 ;; esac
case "$DAYS" in ''|*[!0-9]*) echo "served-certificate: usage: minimum days is a number, not '$DAYS'" >&2; exit 2 ;; esac
SECONDS_LEFT=$((DAYS * 86400))

PEM="$(echo | openssl s_client -connect "$TARGET" -servername "$NAME" 2>/dev/null | openssl x509 2>/dev/null || true)"
if [ -z "$PEM" ]; then
    echo "served-certificate: NOT SERVED -- no certificate came back from $TARGET for $NAME (TLS is off, the pair is not exported yet, or the proxy has not loaded it)."
    exit 10
fi
ISSUER="$(printf '%s\n' "$PEM" | openssl x509 -noout -issuer 2>/dev/null | sed 's/^issuer=//')"
ENDS="$(printf '%s\n' "$PEM" | openssl x509 -noout -enddate 2>/dev/null | sed 's/^notAfter=//')"

case "$ISSUER" in
    *STAGING*) IS_STAGING=yes ;;
    *) IS_STAGING=no ;;
esac
if [ "$MODE" = production ] && [ "$IS_STAGING" = yes ]; then
    echo "served-certificate: STAGING CERTIFICATE -- $NAME is served a certificate from the authority's test endpoint (issuer: $ISSUER); no browser trusts it. ALPHA_ACME_STAGING=no and a deploy replace it."
    exit 13
fi
if [ "$MODE" = staging ] && [ "$IS_STAGING" = no ]; then
    echo "served-certificate: NOT A STAGING CERTIFICATE -- the rehearsal expected the authority's test endpoint and the issuer is: $ISSUER"
    exit 13
fi

if [ "$MODE" = production ]; then
    SESSION="$(echo | openssl s_client -connect "$TARGET" -servername "$NAME" -verify_return_error -verify_hostname "$NAME" 2>&1 || true)"
    if ! printf '%s\n' "$SESSION" | grep -q 'Verify return code: 0 (ok)'; then
        WHY="$(printf '%s\n' "$SESSION" | grep -m1 -i 'verif' || echo 'no verification result')"
        echo "served-certificate: NOT TRUSTED -- the certificate served for $NAME does not verify against the CA bundle for that name ($WHY)."
        exit 12
    fi
fi

if ! printf '%s\n' "$PEM" | openssl x509 -noout -checkend "$SECONDS_LEFT" >/dev/null 2>&1; then
    echo "served-certificate: EXPIRING -- the certificate served for $NAME ends $ENDS, within $DAYS days (issuer: $ISSUER). Renewal has not happened; read the acme service's log."
    exit 11
fi
echo "served-certificate: OK name=$NAME mode=$MODE notAfter=\"$ENDS\" issuer=\"$ISSUER\" valid-for-at-least-days=$DAYS"
exit 0
