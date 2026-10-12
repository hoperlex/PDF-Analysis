#!/usr/bin/env bash
# Restore the latest verified dump into an EMPTY promotion database (a lost volume).
#
#   scripts/promotion/restore.sh [<dump>]     default: the newest verified promotion-*.dump
#
# W54-PLAN.md 3.3: "a lost volume is restored from the latest dump and reconciled forward
# from the file". This is the first half; the second is the next `repair sample|full` start,
# whose reconciliation carries every call the dump does not hold forward from the local
# fsynced journal (R-98).
#
# Heavy step (3.9): refuses unless `df` shows 3 GiB + 3 GiB free and `free` shows 6 GiB
# available, measured now. Refuses a dump without its `.verified` marker or failing its
# SHA-256, and a database that holds any table: it never restores over data.

# shellcheck source=scripts/promotion/lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

promotion_load_env
promotion_pin_image

dump="${1:-}"
if [ -z "${dump}" ]; then
    dump="$(find "${PROMOTION_DUMPS}" -maxdepth 1 -name 'promotion-*.dump.verified' -type f 2>/dev/null \
        | sort | tail -n 1)"
    dump="${dump%.verified}"
fi
if [ -z "${dump}" ] || [ ! -f "${dump}" ]; then
    promotion_refuse "no verified dump to restore"
fi
[ -f "${dump}.verified" ] || promotion_refuse "${dump} was never restore-verified; run verify-dump.sh first"
expected_sha="$(cut -d' ' -f1 < "${dump}.sha256")"
actual_sha="$(sha256sum "${dump}" | cut -d' ' -f1)"
[ "${expected_sha}" = "${actual_sha}" ] || promotion_refuse "${dump} fails its SHA-256"

promotion_require_floor 3 "${PROMOTION_DUMPS}"

tables="$(promotion_compose exec -T postgres psql -X --no-align --tuples-only -v ON_ERROR_STOP=1 \
    --username="${POSTGRES_USER}" --dbname="${POSTGRES_DB}" \
    --command="SELECT count(*) FROM pg_tables WHERE schemaname = 'public'")" \
    || promotion_refuse "the promotion database did not answer; is it up?"
[ "${tables}" = "0" ] || promotion_refuse "the promotion database is not empty (${tables} tables); restore only into a fresh volume"

promotion_compose exec -T postgres pg_restore --exit-on-error --no-owner \
    --username="${POSTGRES_USER}" --dbname="${POSTGRES_DB}" < "${dump}" \
    || promotion_refuse "pg_restore failed for ${dump}"

restored="$(promotion_fingerprint_sql | promotion_compose exec -T postgres \
    psql -X --no-align --tuples-only -v ON_ERROR_STOP=1 \
    --username="${POSTGRES_USER}" --dbname="${POSTGRES_DB}")" \
    || promotion_refuse "the fingerprint query failed after the restore"
[ "${restored}" = "$(cat "${dump}.fingerprint")" ] \
    || promotion_refuse "the restored database does not reproduce ${dump}.fingerprint"

printf 'restored: %s\nnext: the next repair start reconciles the journal forward\n' "${dump}"
