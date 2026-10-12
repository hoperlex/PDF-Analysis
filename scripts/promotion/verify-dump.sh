#!/usr/bin/env bash
# Restore-verify a promotion dump into a disposable instance, then keep only that dump.
#
#   scripts/promotion/verify-dump.sh [<dump>]     default: the newest promotion-*.dump
#
# Heavy step (W54-PLAN.md 3.9): refuses unless `df` shows 3 GiB + 3 GiB free and `free`
# shows 6 GiB available, measured now. The dump's SHA-256 is checked first. The disposable
# instance runs the same image with no network, no published port and no named volume; it is
# removed on every exit path, by its own name only. The restore must reproduce the fingerprint
# dump.sh recorded. On success the dump is marked `.verified` and every dump taken before it is removed,
# so one latest verified dump stays under the dumps directory.

# shellcheck source=scripts/promotion/lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

IMAGE="auditmanager-postgres:17.11-pgvector0.8.6-8ee86c9"

promotion_load_env

dump="${1:-}"
if [ -z "${dump}" ]; then
    dump="$(find "${PROMOTION_DUMPS}" -maxdepth 1 -name 'promotion-*.dump' -type f 2>/dev/null | sort | tail -n 1)"
fi
if [ -z "${dump}" ] || [ ! -f "${dump}" ]; then
    promotion_refuse "no dump to verify"
fi
[ -f "${dump}.sha256" ] || promotion_refuse "${dump} has no .sha256"
[ -f "${dump}.fingerprint" ] || promotion_refuse "${dump} has no .fingerprint"
expected_sha="$(cut -d' ' -f1 < "${dump}.sha256")"
actual_sha="$(sha256sum "${dump}" | cut -d' ' -f1)"
[ "${expected_sha}" = "${actual_sha}" ] || promotion_refuse "${dump} fails its SHA-256"

promotion_require_floor 3 "${PROMOTION_DUMPS}"
docker image inspect "${IMAGE}" >/dev/null 2>&1 \
    || promotion_refuse "the image ${IMAGE} is not built here; run scripts/promotion/stack.sh up first"

name="auditmanager-promotion-verify-$(date -u +%Y%m%d%H%M%S)-$$"
password="$(head -c 48 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 32)"
cleanup() {
    docker rm --force --volumes "${name}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker run --detach --name "${name}" --network none --memory 1g \
    --env POSTGRES_USER=verify --env POSTGRES_DB=verify --env "POSTGRES_PASSWORD=${password}" \
    "${IMAGE}" postgres -c shared_buffers=128MB >/dev/null

ready=0
for _ in $(seq 1 90); do
    if docker exec --env "PGPASSWORD=${password}" "${name}" \
        psql -X --quiet --host=127.0.0.1 --username=verify --dbname=verify \
        --command='SELECT 1' >/dev/null 2>&1; then
        ready=1
        break
    fi
    sleep 1
done
[ "${ready}" = 1 ] || promotion_refuse "the disposable instance did not become ready"

docker exec -i "${name}" pg_restore --exit-on-error --no-owner --username=verify --dbname=verify \
    < "${dump}" || promotion_refuse "pg_restore failed for ${dump}"

restored="$(promotion_fingerprint_sql | docker exec -i "${name}" \
    psql -X --no-align --tuples-only -v ON_ERROR_STOP=1 --username=verify --dbname=verify)" \
    || promotion_refuse "the fingerprint query failed on the restored copy"
if [ "${restored}" != "$(cat "${dump}.fingerprint")" ]; then
    promotion_refuse "the restored copy does not reproduce ${dump}.fingerprint"
fi

: > "${dump}.verified"
sync "${dump}.verified" "${PROMOTION_DUMPS}"
for older in "${PROMOTION_DUMPS}"/promotion-*.dump; do
    [ -e "${older}" ] || continue
    # Only dumps taken before this one: a newer, not yet verified dump is not touched.
    [[ "$(basename "${older}")" < "$(basename "${dump}")" ]] || continue
    rm -f "${older}" "${older}.sha256" "${older}.fingerprint" "${older}.verified"
done
printf 'verified: %s\n' "${dump}"
