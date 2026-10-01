# syntax=docker/dockerfile:1.7

# Repository-owned PostgreSQL derivative. The base stays the exact FF-01 image; pgvector is
# compiled from one official source commit whose archive checksum is verified by BuildKit before
# the first RUN executes. A bad or replaced archive therefore cannot reach the compiler.
ARG POSTGRES_BASE_IMAGE=postgres:17.11-trixie@sha256:67f41722b7a8cbdb868a44a4995c846eddfdc2973bccb291ce937dce88ad5675

FROM ${POSTGRES_BASE_IMAGE} AS pgvector-build

ARG PG_MAJOR=17
ARG PGVECTOR_VERSION=0.8.6
ARG PGVECTOR_COMMIT=8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c

ADD --checksum=sha256:d076a3098010905fd60256649327809651f6288327db6413f0938305f62ea299 \
    https://github.com/pgvector/pgvector/archive/8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c.tar.gz \
    /tmp/pgvector.tar.gz

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        build-essential \
        postgresql-server-dev-${PG_MAJOR} \
    && mkdir --parents /tmp/pgvector-src /tmp/pgvector-root \
    && tar --extract --gzip --file /tmp/pgvector.tar.gz \
        --directory /tmp/pgvector-src --strip-components=1 \
    && make --directory /tmp/pgvector-src clean \
    && make --directory /tmp/pgvector-src \
        PG_CONFIG=/usr/lib/postgresql/${PG_MAJOR}/bin/pg_config OPTFLAGS="" \
    && make --directory /tmp/pgvector-src install \
        PG_CONFIG=/usr/lib/postgresql/${PG_MAJOR}/bin/pg_config \
        DESTDIR=/tmp/pgvector-root \
    && install --directory /tmp/pgvector-root/usr/share/doc/pgvector \
    && install --mode=0644 /tmp/pgvector-src/LICENSE \
        /tmp/pgvector-root/usr/share/doc/pgvector/LICENSE \
    && grep --fixed-strings --line-regexp \
        "default_version = '${PGVECTOR_VERSION}'" \
        /tmp/pgvector-root/usr/share/postgresql/${PG_MAJOR}/extension/vector.control

FROM ${POSTGRES_BASE_IMAGE}

ARG PG_MAJOR=17
ARG PGVECTOR_VERSION=0.8.6
ARG PGVECTOR_COMMIT=8ee86c96f0fd72390f890aa8a336fda6d3ab4c6c

COPY --from=pgvector-build /tmp/pgvector-root/ /

LABEL org.opencontainers.image.title="AuditManager PostgreSQL with pgvector" \
      org.opencontainers.image.base.name="postgres:17.11-trixie" \
      org.opencontainers.image.source="https://github.com/hoperlex/PDF-Analysis" \
      io.auditmanager.postgresql.major="${PG_MAJOR}" \
      io.auditmanager.pgvector.version="${PGVECTOR_VERSION}" \
      io.auditmanager.pgvector.commit="${PGVECTOR_COMMIT}" \
      io.auditmanager.pgvector.source-sha256="d076a3098010905fd60256649327809651f6288327db6413f0938305f62ea299"

RUN test -f /usr/lib/postgresql/${PG_MAJOR}/lib/vector.so \
    && grep --fixed-strings --line-regexp \
        "default_version = '${PGVECTOR_VERSION}'" \
        /usr/share/postgresql/${PG_MAJOR}/extension/vector.control \
    && test -f /usr/share/doc/pgvector/LICENSE
