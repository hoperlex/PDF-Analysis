#!/bin/sh
# THE SWITCH. Mounted by `compose.tls.yml` at `/docker-entrypoint.d/25-enable-tls.sh`,
# where the official nginx image's entrypoint runs every executable `*.sh` -- `find
# /docker-entrypoint.d/ -follow -type f | sort -V` -- BEFORE the master process starts and
# therefore before the parse that would refuse a missing certificate.
#
# WHAT IT DECIDES, and it is one question: are `/etc/nginx/tls/fullchain.pem` and
# `/etc/nginx/tls/privkey.pem` both there and non-empty?
#
#   yes -> copy `/etc/nginx/tls-server.conf` to `/etc/nginx/conf.d/tls.conf`. nginx loads
#          it, the container listens on 8443, and `compose.tls.yml` publishes it as 443.
#   no  -> install nothing, REMOVE any `conf.d/tls.conf` left from an earlier start, and
#          say so on the container log. nginx serves the plain port exactly as it does
#          without this file, and the stack stays up.
#
# THE `no` BRANCH IS NOT A SILENT FALLBACK. It prints the path it looked at, what it found
# there and the sentence `TLS IS OFF`, every start, on stderr, which is the container log.
# An operator who mounted the wrong directory reads the path they did not mean to mount.
# `docs/program/DEPLOYMENT_RUNBOOK.md` section 6 makes reading that line the step.
#
# THE `rm -f` MATTERS AND IS NOT TIDINESS. A restarted container keeps its writable layer,
# so a `conf.d/tls.conf` written by an earlier start would still be there after the
# certificate was taken away -- and then nginx would refuse to start and the site would go
# dark for a file that was deliberately removed. The disabled branch therefore un-installs.
#
# `D-37`, CARRIED: a `-v` source is resolved by the DAEMON, and docker invents an empty
# directory rather than refusing. So a mis-resolved certificate mount does not fail loudly;
# it arrives as an empty `/etc/nginx/tls`, which is exactly the `no` branch -- the stack
# stays up on the plain port and the log names the directory it found empty. That is the
# behaviour this script was shaped around rather than one it happens to have.
#
# POSIX `sh`, because the pinned image is `nginx:1.27-alpine` and there is no bash in it.

set -eu

CERT=/etc/nginx/tls/fullchain.pem
KEY=/etc/nginx/tls/privkey.pem
SRC=/etc/nginx/tls-server.conf
DST=/etc/nginx/conf.d/tls.conf

say() { printf 'enable-tls: %s\n' "$*" >&2; }

off() {
    # Un-install before announcing, so the announcement is true when it is printed.
    rm -f "$DST"
    say "$1"
    say "  certificate: $CERT"
    say "  private key: $KEY"
    say "TLS IS OFF. The stack serves plain HTTP on the published port and nothing else."
    say "See docs/program/DEPLOYMENT_RUNBOOK.md section 6."
    exit 0
}

[ -f "$SRC" ] || off "no TLS server block is mounted at $SRC."

if [ ! -s "$CERT" ] || [ ! -s "$KEY" ]; then
    off "no usable certificate pair (a missing or empty file is not a certificate)."
fi

# The key's mode is the owner's business on the host, but a world-readable private key
# inside the container is worth one line rather than none. This does not refuse: the mount
# is read-only and the container cannot fix it, and refusing would take the site down over
# a permission the operator can change without a deploy.
if [ -r "$KEY" ]; then
    MODE="$(stat -c '%a' "$KEY" 2>/dev/null || echo '???')"
    case "$MODE" in
        600|400|640|440|???) ;;
        *) say "WARNING: the private key is mode $MODE inside the container. 600 on the host." ;;
    esac
fi

cp "$SRC" "$DST"
say "a certificate pair is present; $DST installed."
if command -v openssl >/dev/null 2>&1; then
    say "  $(openssl x509 -in "$CERT" -noout -subject -enddate 2>/dev/null | tr '\n' ' ')"
fi
say "TLS IS ON. nginx will listen on 8443 in this container; see compose.tls.yml for the"
say "published port. The configuration is tested by nginx itself on the next line."
exit 0
