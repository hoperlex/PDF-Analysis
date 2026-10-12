#!/usr/bin/env bash
# The promotion database's lifecycle (W54-REPAIR-01, W54-PLAN.md 3.2).
#
#   scripts/promotion/stack.sh up                 build if needed, start, wait for health
#   scripts/promotion/stack.sh stop               stop between operator steps (volume kept)
#   scripts/promotion/stack.sh status             the compose project's state
#   scripts/promotion/stack.sh migrate            alembic upgrade head against it
#   scripts/promotion/stack.sh run -- <cmd...>    run <cmd> with DATABASE_URL set for it
#
# The env file (.local/promotion/promotion.env, or $PROMOTION_ENV) holds POSTGRES_DB,
# POSTGRES_USER, POSTGRES_PASSWORD and PROMOTION_POSTGRES_PORT. No verb prints the password:
# `run` hands DATABASE_URL to the one command it starts instead of echoing it.
# No verb removes the volume. A lost volume is restored from the latest verified dump.

# shellcheck source=scripts/promotion/lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

verb="${1:-}"
[ "$#" -gt 0 ] && shift

case "${verb}" in
    up)
        promotion_load_env
        promotion_pin_image
        promotion_compose up --detach --wait postgres
        ;;
    stop)
        promotion_load_env
        promotion_pin_image
        promotion_compose stop postgres
        ;;
    status)
        promotion_load_env
        promotion_pin_image
        promotion_compose ps --all
        ;;
    migrate)
        promotion_load_env
        cd "${PROMOTION_ROOT}"
        DATABASE_URL="$(promotion_database_url)" PYTHONPATH=src \
            "${PROMOTION_ROOT}/.venv/bin/python" -m alembic --config db/migrations/alembic.ini \
            upgrade head
        ;;
    run)
        promotion_load_env
        [ "${1:-}" = "--" ] || promotion_refuse "usage: stack.sh run -- <command...>"
        shift
        [ "$#" -gt 0 ] || promotion_refuse "usage: stack.sh run -- <command...>"
        DATABASE_URL="$(promotion_database_url)"
        export DATABASE_URL
        exec "$@"
        ;;
    *)
        printf 'usage: %s up|stop|status|migrate|run -- <command...>\n' "$0" >&2
        exit 2
        ;;
esac
