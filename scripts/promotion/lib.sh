#!/usr/bin/env bash
# Shared by scripts/promotion/{stack,dump,verify-dump}.sh (W54-REPAIR-01, W54-PLAN.md 3.2, 3.9).
#
# Sourced, never run. Every refusal exits non-zero BEFORE any docker call, names what is
# missing, and never prints a credential.

set -euo pipefail

PROMOTION_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROMOTION_PROJECT="auditmanager-promotion"
PROMOTION_COMPOSE="${PROMOTION_ROOT}/infra/promotion/compose.yml"
PROMOTION_ENV="${PROMOTION_ENV:-${PROMOTION_ROOT}/.local/promotion/promotion.env}"
PROMOTION_DUMPS="${PROMOTION_DUMPS:-${PROMOTION_ROOT}/.local/norms/promotion-dumps}"
#: Tables whose row counts and digests a dump must reproduce after a restore.
PROMOTION_FINGERPRINT_TABLES=(
    alembic_version norms_snapshot norm_document norm_paragraph norm_chunk_build norm_chunk
    norm_embedding_profile norm_embedding_build norm_embedding norm_repair_call
    norm_custody_admission norm_custody_binding
)
GIB=$((1024 * 1024 * 1024))

promotion_refuse() {
    printf 'promotion: REFUSED: %s\n' "$*" >&2
    exit 3
}

promotion_load_env() {
    [ -f "${PROMOTION_ENV}" ] || promotion_refuse \
        "no env file at ${PROMOTION_ENV}; it holds POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD and PROMOTION_POSTGRES_PORT (from PORT_REGISTRY.md)"
    set -a
    # shellcheck disable=SC1090
    . "${PROMOTION_ENV}"
    set +a
    local name
    for name in POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD PROMOTION_POSTGRES_PORT; do
        [ -n "${!name:-}" ] || promotion_refuse "${name} is unset in the env file"
    done
    [[ "${PROMOTION_POSTGRES_PORT}" =~ ^[1-9][0-9]{3,4}$ ]] \
        || promotion_refuse "PROMOTION_POSTGRES_PORT is not a port number"
    [[ "${POSTGRES_DB}" =~ ^[a-z][a-z0-9_]{0,62}$ ]] \
        || promotion_refuse "POSTGRES_DB must match ^[a-z][a-z0-9_]{0,62}$"
    [[ "${POSTGRES_USER}" =~ ^[a-z][a-z0-9_]{0,62}$ ]] \
        || promotion_refuse "POSTGRES_USER must match ^[a-z][a-z0-9_]{0,62}$"
    # URL-safe, so DATABASE_URL needs no escaping and is never echoed to build it.
    [[ "${POSTGRES_PASSWORD}" =~ ^[A-Za-z0-9_-]{16,128}$ ]] \
        || promotion_refuse "POSTGRES_PASSWORD must be 16-128 characters of [A-Za-z0-9_-]"
}

promotion_pin_image() {
    local pin
    pin="$(sed -n 's/^override FOUNDATION_POSTGRES_IMAGE := //p' "${PROMOTION_ROOT}/Makefile")"
    [[ "${pin}" =~ ^postgres:[0-9.]+-[a-z]+@sha256:[0-9a-f]{64}$ ]] \
        || promotion_refuse "the Makefile carries no digest-pinned FOUNDATION_POSTGRES_IMAGE"
    export FOUNDATION_POSTGRES_IMAGE="${pin}"
}

promotion_compose() {
    docker compose --project-name "${PROMOTION_PROJECT}" --file "${PROMOTION_COMPOSE}" "$@"
}

promotion_database_url() {
    printf 'postgresql+psycopg://%s:%s@127.0.0.1:%s/%s' \
        "${POSTGRES_USER}" "${POSTGRES_PASSWORD}" "${PROMOTION_POSTGRES_PORT}" "${POSTGRES_DB}"
}

# promotion_require_floor <increment GiB> <path on the target filesystem>
#
# W54-PLAN.md 3.9's stop rule, measured at this step: free disk >= increment + 3 GiB, and
# available RAM >= 6 GiB (swap does not count). Provisioning is the owner's decision.
promotion_require_floor() {
    local increment_gib="$1" path="$2" free_bytes available_bytes
    mkdir -p "${path}"
    free_bytes="$(df -B1 --output=avail "${path}" | tail -n 1 | tr -d ' ')"
    available_bytes="$(free -b | awk '/^Mem:/ {print $7}')"
    [[ "${free_bytes}" =~ ^[0-9]+$ && "${available_bytes}" =~ ^[0-9]+$ ]] \
        || promotion_refuse "could not measure df/free"
    if (( free_bytes < (increment_gib + 3) * GIB )); then
        promotion_refuse "disk floor: ${free_bytes} bytes free, this step needs $(( (increment_gib + 3) * GIB )) (increment ${increment_gib} GiB + 3 GiB)"
    fi
    if (( available_bytes < 6 * GIB )); then
        promotion_refuse "memory floor: ${available_bytes} bytes available, a heavy step needs $(( 6 * GIB ))"
    fi
}

# promotion_fingerprint_sql
#
# One line per table: name, row count, and an md5 over the md5 of every row, in md5 order
# (canonical, and bounded in memory even for norm_embedding). The same query runs against the source and the restored copy; equal output is the
# restore-verify.
promotion_fingerprint_sql() {
    local table
    for table in "${PROMOTION_FINGERPRINT_TABLES[@]}"; do
        printf "SELECT '%s', count(*), coalesce(md5(string_agg(md5(t::text), '' ORDER BY md5(t::text))), '-') FROM %s t;\n" \
            "${table}" "${table}"
    done
}
