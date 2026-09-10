#!/bin/sh
# P1-INF-01 / Gate A session A2 - idempotent private-bucket initialization.
#
# Runs inside the pinned minio/mc container (FOUNDATION_S3_MC_IMAGE), on the lane network,
# against the `s3` service. Mounted read-only at /usr/local/lib/foundation/bucket-init.sh.
#
# IDEMPOTENT BY CONSTRUCTION. Every step is "make it so", never "create it":
#   - the bucket is created only when `mc stat` says it is absent;
#   - the anonymous policy is set to `none` unconditionally, which is a no-op when it is
#     already `none`;
#   - the result is verified before the script reports success.
# Running it a second time therefore creates nothing, changes nothing and exits 0. It is
# re-run automatically on every `make up` and can be re-run by hand with
#   docker compose --project-name "$FOUNDATION_INSTANCE" \
#     --file infra/local/docker-compose.yml exec s3-init \
#     /bin/sh /usr/local/lib/foundation/bucket-init.sh
#
# The bucket is PRIVATE. `mc anonymous set none` removes any bucket policy, so an
# unauthenticated caller can neither list, read nor write. Nothing here ever grants
# `download`, `upload` or `public`. check_services.py proves the denial with a real
# anonymous client rather than by reading this file.
#
# No credential is ever echoed: `mc alias set` is given the secret on its argument list
# and this script prints only names, never values.

set -eu

ALIAS=local
ENDPOINT=${S3_INTERNAL_ENDPOINT:-http://s3:9000}
BUCKET=${S3_BUCKET:?bucket-init: S3_BUCKET is unset; the frozen name must be provided}
: "${MINIO_ROOT_USER:?bucket-init: MINIO_ROOT_USER is unset}"
: "${MINIO_ROOT_PASSWORD:?bucket-init: MINIO_ROOT_PASSWORD is unset}"

fail() {
    printf 'bucket-init: %s\n' "$@" >&2
    exit 1
}

# `depends_on: service_healthy` already gates this, but a health check that has just
# flipped and a server that is accepting API calls are not the same instant. Retry the
# first authenticated call rather than failing the whole `up` on a race.
attempt=1
until mc --quiet alias set "$ALIAS" "$ENDPOINT" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" \
    >/dev/null 2>&1; do
    if [ "$attempt" -ge 30 ]; then
        fail "cannot authenticate to $ENDPOINT after $attempt attempts." \
             "The s3 service reported healthy, so this is a credential or network fault." \
             "Check MINIO_ROOT_USER / MINIO_ROOT_PASSWORD in .env."
    fi
    attempt=$((attempt + 1))
    sleep 1
done

# --- bucket ------------------------------------------------------------------------
if mc --quiet stat "$ALIAS/$BUCKET" >/dev/null 2>&1; then
    created=no
else
    # --ignore-existing keeps a lost race with a concurrent initializer from failing.
    mc --quiet mb --ignore-existing "$ALIAS/$BUCKET" >/dev/null \
        || fail "could not create bucket $BUCKET at $ENDPOINT."
    created=yes
fi

# --- privacy -----------------------------------------------------------------------
# Unconditional and idempotent: setting `none` when the policy is already `none` is a
# no-op. Because it is unconditional, a bucket that was opened by hand is closed again the
# next time this script RUNS.
#
# It runs when the s3-init container starts - so on the first `make up`, and on every
# `make up` after a `make down`. Compose does not restart a container that is already
# running, so `make up` against an already-running stack does NOT re-run it. This script
# therefore establishes privacy; it does not continuously enforce it. Detecting a bucket
# that was opened after initialization is check_services.py's job, and it fails loudly.
mc --quiet anonymous set none "$ALIAS/$BUCKET" >/dev/null \
    || fail "could not remove the anonymous policy from $BUCKET."

# --- verify ------------------------------------------------------------------------
mc --quiet stat "$ALIAS/$BUCKET" >/dev/null \
    || fail "bucket $BUCKET is not present after initialization."

# `mc anonymous get` reports the effective permission as a word, and this mc release
# spells "no anonymous policy" as `private` even though `set` spells it `none`. Both are
# accepted; every other value - download, upload, public, custom - is a bucket somebody
# has opened, and is refused here rather than reported as success.
policy=$(mc --quiet anonymous get "$ALIAS/$BUCKET" 2>/dev/null || true)
case "$policy" in
    *'is `none`'*|*'is `private`'*) ;;
    *) fail "bucket $BUCKET carries an anonymous policy after initialization." \
            "  reported: ${policy:-<no output>}" \
            "A public bucket is refused: the foundation bucket is private." ;;
esac

if [ "$created" = yes ]; then
    printf 'bucket-init: created private bucket %s at %s\n' "$BUCKET" "$ENDPOINT"
else
    printf 'bucket-init: bucket %s already present at %s - no-op\n' "$BUCKET" "$ENDPOINT"
fi
printf 'bucket-init: %s\n' "$policy"
printf 'bucket-init: OK\n'
