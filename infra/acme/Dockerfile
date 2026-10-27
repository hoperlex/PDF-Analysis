# syntax=docker/dockerfile:1.7

# THE ACME CLIENT -- `PROD-01-TLS-ACME-01`, `ADR-0021` section 2, `R-146aa`.
#
# A service of the same compose project (`infra/acme/compose.acme.yml`): it asks a certificate authority
# for a certificate over HTTP-01, through a webroot the `proxy` serves, and writes the pair it gets into a
# named volume the `proxy` mounts READ-ONLY. It publishes no port, mounts no Docker socket, holds no
# application secret, and runs as an unprivileged user. It does not reload or restart anything: the proxy
# notices the new pair on its own timer (`infra/deploy/proxy/watch-certificate.sh`).
#
# Built on the host like the other repository-owned images. The base is pinned by digest (the same Alpine
# the MinIO image uses); the client by exact package version in `client.pin`. See that file for what is and
# is not pinned, and why the value in it is `UNRESOLVED` until someone with network access resolves it.
FROM alpine:3.22.1@sha256:4bcff63911fcb4448bd4fdacec207030997caf25e9bea4045fa6c8c44de311d1

COPY client.pin /etc/acme/client.pin

# `openssl` is the tool `check-served.sh` asks the served certificate with; it is named here rather than
# left to arrive as a dependency of something else. The build REFUSES without a resolved, well-formed
# version, and then proves the installed client reports that version.
RUN set -eu; \
    version="$(sed -n 's/^ACME_CLIENT_APK_VERSION=//p' /etc/acme/client.pin | tail -1)"; \
    case "$version" in \
        ''|UNRESOLVED) echo "infra/acme/client.pin does not name a client version (ACME_CLIENT_APK_VERSION=$version); resolve it first." >&2; exit 1 ;; \
    esac; \
    printf '%s\n' "$version" | grep -Eq '^[0-9][0-9A-Za-z._+~]*-r[0-9]+$' \
        || { echo "ACME_CLIENT_APK_VERSION=$version is not an apk package version (<version>-r<release>)." >&2; exit 1; }; \
    apk add --no-cache "certbot=$version" openssl ca-certificates; \
    certbot --version 2>&1 | grep -F "${version%-r*}"

RUN adduser -D -H -u 10002 acme \
    && mkdir -p /etc/letsencrypt /var/lib/letsencrypt /var/log/letsencrypt /var/www/acme /export \
    && chown -R acme:acme /etc/letsencrypt /var/lib/letsencrypt /var/log/letsencrypt /var/www/acme /export

COPY entrypoint.sh export-pair.sh check-served.sh /usr/local/bin/
RUN chmod 0755 /usr/local/bin/entrypoint.sh /usr/local/bin/export-pair.sh /usr/local/bin/check-served.sh

USER acme
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
