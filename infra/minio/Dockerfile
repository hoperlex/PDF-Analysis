# syntax=docker/dockerfile:1.7

# Repository-owned replacements for the withdrawn minio/minio and minio/mc registry images.
# Every base/source input has an immutable identity: both base images carry multi-arch index
# digests, and both official source archives carry a commit URL plus a BuildKit-enforced SHA-256.
# Go then checks the complete module graph against the upstream go.sum files in read-only mode.
FROM golang:1.24.8-bookworm@sha256:4ed690d6649d63c312b99a6120025ec79ce3b542968a37da53d6236c7c61a848 AS build

ARG TARGETOS
ARG TARGETARCH

ADD --checksum=sha256:45521908307306e925c98d629e1c17d78c8b72b6ee242b1bfb1409f7d8ee5841 \
    https://github.com/minio/minio/archive/9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a.tar.gz \
    /tmp/minio.tar.gz
ADD --checksum=sha256:95cd293c7119f16921a6dc515a1fb74a2227f19fd994b9c8b770a154e802ac44 \
    https://github.com/minio/mc/archive/7394ce0dd2a80935aded936b09fa12cbb3cb8096.tar.gz \
    /tmp/mc.tar.gz

RUN mkdir --parents /src/minio /src/mc /out \
    && tar --extract --gzip --file /tmp/minio.tar.gz --directory /src/minio --strip-components=1 \
    && tar --extract --gzip --file /tmp/mc.tar.gz --directory /src/mc --strip-components=1 \
    && test "$(sed -n 's/^toolchain go//p' /src/minio/go.mod)" = "1.24.8" \
    && test "$(sed -n 's/^toolchain go//p' /src/mc/go.mod)" = "1.23.10"

# Keep the release metadata that upstream's git-backed gen-ldflags.go would produce. Source
# archives deliberately contain no .git directory, so spelling the values from the frozen commit
# here is both more reproducible and easier to audit than manufacturing repository history.
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    test -n "${TARGETOS}" \
    && test -n "${TARGETARCH}" \
    && cd /src/minio \
    && CGO_ENABLED=0 GOTOOLCHAIN=local GOOS="${TARGETOS}" GOARCH="${TARGETARCH}" \
       go build -mod=readonly -buildvcs=false -tags kqueue -trimpath \
       -ldflags '-s -w \
         -X github.com/minio/minio/cmd.Version=2025-10-15T17:29:55Z \
         -X github.com/minio/minio/cmd.CopyrightYear=2025 \
         -X github.com/minio/minio/cmd.ReleaseTag=RELEASE.2025-10-15T17-29-55Z \
         -X github.com/minio/minio/cmd.CommitID=9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a \
         -X github.com/minio/minio/cmd.ShortCommitID=9e49d5e7a648 \
         -X github.com/minio/minio/cmd.GOPATH=/go \
         -X github.com/minio/minio/cmd.GOROOT=/usr/local/go' \
       -o /out/minio . \
    && cd /src/mc \
    && CGO_ENABLED=0 GOTOOLCHAIN=local GOOS="${TARGETOS}" GOARCH="${TARGETARCH}" \
       go build -mod=readonly -buildvcs=false -tags kqueue -trimpath \
       -ldflags '-s -w \
         -X github.com/minio/mc/cmd.Version=2025-08-13T08:35:41Z \
         -X github.com/minio/mc/cmd.CopyrightYear=2025 \
         -X github.com/minio/mc/cmd.ReleaseTag=RELEASE.2025-08-13T08-35-41Z \
         -X github.com/minio/mc/cmd.CommitID=7394ce0dd2a80935aded936b09fa12cbb3cb8096 \
         -X github.com/minio/mc/cmd.ShortCommitID=7394ce0dd2a8' \
       -o /out/mc . \
    && /out/minio --version | grep --fixed-strings 'RELEASE.2025-10-15T17-29-55Z' \
    && /out/mc --version | grep --fixed-strings 'RELEASE.2025-08-13T08-35-41Z'

FROM alpine:3.22.1@sha256:4bcff63911fcb4448bd4fdacec207030997caf25e9bea4045fa6c8c44de311d1 AS runtime

COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=build /src/minio/LICENSE /licenses/minio/LICENSE
COPY --from=build /src/mc/LICENSE /licenses/mc/LICENSE
COPY --from=build /src/mc/CREDITS /licenses/mc/CREDITS

LABEL org.opencontainers.image.source="https://github.com/hoperlex/PDF-Analysis" \
      org.opencontainers.image.licenses="AGPL-3.0-or-later" \
      io.auditmanager.minio.server-release="RELEASE.2025-10-15T17-29-55Z" \
      io.auditmanager.minio.server-commit="9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a" \
      io.auditmanager.minio.client-release="RELEASE.2025-08-13T08-35-41Z" \
      io.auditmanager.minio.client-commit="7394ce0dd2a80935aded936b09fa12cbb3cb8096"

FROM runtime AS server

COPY --from=build /out/minio /usr/local/bin/minio
COPY --from=build /out/mc /usr/local/bin/mc

EXPOSE 9000 9001
VOLUME ["/data"]
ENTRYPOINT ["/usr/local/bin/minio"]
CMD ["server", "/data"]

FROM runtime AS client

COPY --from=build /out/mc /usr/local/bin/mc

ENTRYPOINT ["/usr/local/bin/mc"]
