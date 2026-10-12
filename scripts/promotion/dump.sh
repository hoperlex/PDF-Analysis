#!/usr/bin/env bash
# A `pg_dump -Fc` of the promotion database, after each operator step (W54-PLAN.md 3.2).
#
#   scripts/promotion/dump.sh
#
# Heavy step (3.9): refuses unless `df` shows 1 GiB + 3 GiB free under the dumps directory
# and `free` shows 6 GiB available, measured now. The dump is written under a `.partial`
# name, synced, checksummed and only then renamed, beside its `.sha256` and the table
# fingerprint taken immediately before and after it (refused if the two differ: something
# wrote during the dump). It is not trusted until scripts/promotion/verify-dump.sh has
# restored it into a disposable instance and reproduced the fingerprint; that script keeps
# the one latest verified dump and removes the older ones.

# shellcheck source=scripts/promotion/lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

promotion_load_env
promotion_pin_image
promotion_require_floor 1 "${PROMOTION_DUMPS}"

fingerprint() {
    promotion_fingerprint_sql | promotion_compose exec -T postgres \
        psql -X --no-align --tuples-only -v ON_ERROR_STOP=1 \
        --username="${POSTGRES_USER}" --dbname="${POSTGRES_DB}"
}

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
final="${PROMOTION_DUMPS}/promotion-${stamp}.dump"
partial="${final}.partial"
[ ! -e "${final}" ] || promotion_refuse "a dump named ${final} already exists"

before="$(fingerprint)" || promotion_refuse "the promotion database did not answer the fingerprint query"
promotion_compose exec -T postgres pg_dump --format=custom --no-owner \
    --username="${POSTGRES_USER}" --dbname="${POSTGRES_DB}" > "${partial}" \
    || { rm -f "${partial}"; promotion_refuse "pg_dump failed; no dump was kept"; }
after="$(fingerprint)" || { rm -f "${partial}"; promotion_refuse "the fingerprint query failed after the dump"; }
if [ "${before}" != "${after}" ]; then
    rm -f "${partial}"
    promotion_refuse "the database changed while it was dumped; stop every writer and dump again"
fi
[ -s "${partial}" ] || { rm -f "${partial}"; promotion_refuse "pg_dump wrote nothing"; }

sync "${partial}"
sha="$(sha256sum "${partial}" | cut -d' ' -f1)"
mv "${partial}" "${final}"
printf '%s  %s\n' "${sha}" "$(basename "${final}")" > "${final}.sha256"
printf '%s\n' "${before}" > "${final}.fingerprint"
sync "${final}" "${final}.sha256" "${final}.fingerprint" "${PROMOTION_DUMPS}"

printf 'dump: %s\nsha256: %s\nnext: scripts/promotion/verify-dump.sh %s\n' "${final}" "${sha}" "${final}"
