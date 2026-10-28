#!/usr/bin/env bash
# `PROD-04-DB-ROLES-01` (`R-146n` item 1, `AD-02`, `ADR-0021` section 3) -- give the APPLICATION role exactly
# the rights the classification says, and nothing else. One idempotent step; every path that makes or
# replaces the schema ends in it.
#
#   infra/deploy/apply-grants.sh [--env-file <path>]            apply, then verify what was applied
#   infra/deploy/apply-grants.sh [--env-file <path>] --check    verify only; changes nothing
#   infra/deploy/apply-grants.sh [--env-file <path>] --config-only
#                                                               judge the settings only; touches no docker
#   infra/deploy/apply-grants.sh --env-file <path> --compose-file <path>
#                                                               for a copy installed apart from the checkout
#                                                               (`copy-serve.sh`): the compose file is the checkout's
#
# WHY A STEP AND NOT A MIGRATION. The dump tools run `pg_dump --no-owner --no-privileges` (`reset.sh`,
# `purge-product-data.sh`, `copy-serve.sh`) and restore with `--no-owner`; `copy-serve.sh restore-db` first runs
# `DROP SCHEMA public CASCADE; CREATE SCHEMA public`. A privilege granted by a revision would be lost by every
# restore, and the `migrate` that follows applies nothing because the head has not moved: the application would
# answer "permission denied". A role also needs a password, and a password cannot live in an Alembic revision.
# So the rights are re-applied after EVERY `migrate` and EVERY restore, by this one script, and it is safe to
# run any number of times (the second run changes nothing but the stored form of the password).
#
# THE TWO ROLES. `POSTGRES_USER` is the MIGRATOR: it owns every object, runs `migrate` and `release-notes`, and
# is the role the operator tools that need write-everything connect as (`MIGRATOR_DATABASE_URL`). It is the
# postgres image's bootstrap role, which is a SUPERUSER, and it stays one: migration `0013` runs `CREATE
# EXTENSION vector`, and the pgvector build in this stack is `superuser = true, trusted = false`, so no plain
# owner role can migrate a fresh database (`tests/integration/db/test_application_role_grants.py`
# `test_a_plain_owner_cannot_migrate_a_fresh_database` pins that premise; if it goes red the decision is open
# again). `ALPHA_APP_DB_USER` is the APPLICATION role: `api` and `worker` connect as it (`DATABASE_URL`). It can
# log in, is not a superuser, cannot create a database, a role, a schema or any object, owns nothing, is a
# member of nothing, holds no TRUNCATE, and gets SELECT/INSERT/UPDATE/DELETE, SELECT/INSERT or SELECT per table
# by `scripts/recovery/grant_classification.py`, which is also where the SQL below is generated from.
# Its password is `ALPHA_APP_DB_PASSWORD`, the second password: the owner writes it on the host, the repository
# holds no value for it, and an unset one is a refusal here and in `deploy.sh`, never a fall-back to the owner.
#
# FAIL CLOSED. A table, view or sequence the classification does not name gets NO rights and stops the step
# with `[grants_unclassified]` (exit 3) before any right is granted; there is no `ALTER DEFAULT PRIVILEGES`. A
# migration that adds a table is red in `tests/integration/recovery/test_grant_classification.py` until the
# table is classified, and `python -m scripts.recovery.grant_classification --write-script
# infra/deploy/apply-grants.sh` regenerates the two blocks below.
#
# THE PASSWORD NEVER APPEARS IN A COMMAND LINE. It is read from the environment file as data (never sourced),
# restricted to characters that need no quoting, and written to `psql`'s standard input; `docker compose exec -T`
# carries stdin into the container. Nothing is echoed back.
#
# EXIT CODES: 0 applied and verified (or, with --check, nothing differs); 1 --check found a difference;
# 2 usage; 3 REFUSED (a setting is missing or malformed, or the schema holds a relation with no classification;
# nothing was granted); 4 FAILED (docker or psql could not do it; the message says which).
#
# GUARDS ARE DELIMITED BY MARKERS -- `# >>> guard: <name>` / `# <<< guard: <name>`.
# `tests/integration/composition/test_apply_grants_script.py` deletes ONE guard block from a copy of this file and
# shows the copy no longer refuses. Do not remove a marker without removing its test.
#
# This script is installed beside `copy-serve.sh` (`DEPLOYMENT_RUNBOOK.md` section 13) because `restore-db` runs it.

set -Eeuo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$HERE/compose.server.yml"
ENV_FILE="${ALPHA_ENV_FILE:-$HERE/env/alpha.env}"
MODE=apply

refuse() {
    printf 'apply-grants.sh: REFUSED: %s\n' "$1" >&2
    shift
    [ "$#" -eq 0 ] || printf '  %s\n' "$@" >&2
    exit 3
}

fail() {
    printf 'apply-grants.sh: FAILED: %s\n' "$1" >&2
    shift
    [ "$#" -eq 0 ] || printf '  %s\n' "$@" >&2
    exit 4
}

usage() {
    cat >&2 <<'USAGE'
usage: apply-grants.sh [--env-file <path>] [--compose-file <path>] [--check | --config-only]

  --env-file <path>      default: infra/deploy/env/alpha.env
  --compose-file <path>  default: compose.server.yml beside this script
  --check             verify the application role's rights against the classification; change nothing.
                      Exit 0: nothing differs. Exit 1: a difference (printed, one per line).
  --config-only       judge ALPHA_APP_DB_USER, ALPHA_APP_DB_PASSWORD and the two database URLs only.
                      Touches no docker and no database. Exit 0 or 3.
USAGE
    exit 2
}

# >>> guard: known-options
# An unrecognised option is refused rather than ignored: `--chek` silently ignored would APPLY grants while the
# operator believed they were only looking.
while [ "$#" -gt 0 ]; do
    case "$1" in
        --env-file) ENV_FILE="${2:-}"; shift 2 ;;
        --compose-file) COMPOSE_FILE="${2:-}"; shift 2 ;;
        --check) MODE=check; shift ;;
        --config-only) MODE=config; shift ;;
        -h|--help) usage ;;
        *) refuse "unrecognised option: $1" "Nothing was read and nothing was touched. Run --help." ;;
    esac
done
# <<< guard: known-options

# >>> guard: env-file-present
if [ ! -r "$ENV_FILE" ]; then
    refuse "the deployment environment $ENV_FILE is missing or unreadable." \
           "Without it there is no instance, database or role to act on. See env/alpha.env.example."
fi
# <<< guard: env-file-present

# Read as DATA. The file is never sourced.
configured() {
    sed -n "s/^[[:space:]]*\(export[[:space:]]\+\)\?$1=//p" "$ENV_FILE" | tail -1 \
        | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/"
}

PG_USER="$(configured POSTGRES_USER)"
PG_PASSWORD="$(configured POSTGRES_PASSWORD)"
PG_DB="$(configured POSTGRES_DB)"
APP_ROLE="$(configured ALPHA_APP_DB_USER)"
APP_PASSWORD="$(configured ALPHA_APP_DB_PASSWORD)"

# >>> guard: owner-configured
if [ -z "$PG_USER" ] || [ -z "$PG_DB" ] || [ -z "$PG_PASSWORD" ]; then
    refuse "$ENV_FILE names no POSTGRES_USER, POSTGRES_PASSWORD or POSTGRES_DB." \
           "  POSTGRES_USER    : ${PG_USER:-<unset>}" \
           "  POSTGRES_DB      : ${PG_DB:-<unset>}" \
           "The owner (migrator) role is the one that applies the rights; a half-configured environment has none."
fi
# <<< guard: owner-configured

# >>> guard: app-role-well-formed
# The role name is written into SQL as an identifier and into a URL; keep it to lower-case letters, digits and
# underscores, and never in the `pg_` namespace PostgreSQL reserves for its own roles.
if [[ ! "$APP_ROLE" =~ ^[a-z_][a-z0-9_]{2,62}$ ]] || [[ "$APP_ROLE" == pg_* ]]; then
    refuse "[app_db_role_invalid] ALPHA_APP_DB_USER in $ENV_FILE is '${APP_ROLE:-<unset>}'." \
           "It names the role api and worker connect as: 3 to 63 characters from a-z, 0-9 and _, not starting with a" \
           "digit or with pg_. Nothing was changed."
fi
# <<< guard: app-role-well-formed

# >>> guard: app-role-not-owner
# THE POINT OF THE WHOLE ITEM: the application is not the owner. An environment that names the owner as the
# application role would run every statement the application sends with the right to drop the schema, and it
# would look configured. There is no fall-back to the owner role anywhere.
if [ "$APP_ROLE" = "$PG_USER" ]; then
    refuse "[app_db_role_is_owner] ALPHA_APP_DB_USER is the owner role ($PG_USER)." \
           "api and worker must connect as a role that owns nothing and cannot change the schema." \
           "Choose another name for ALPHA_APP_DB_USER. Nothing was changed."
fi
# <<< guard: app-role-not-owner

# >>> guard: app-password-set
# THE SECOND PASSWORD is the owner's to write on the host; the repository never holds one. Unset is a refusal and
# not a quiet use of the owner's password for the application.
if [ -z "$APP_PASSWORD" ]; then
    refuse "[app_db_password_unset] ALPHA_APP_DB_PASSWORD is not set in $ENV_FILE." \
           "It is the password of the application role '$APP_ROLE' and it is yours to choose on the host:" \
           "    head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \\n'; echo" \
           "Put it in ALPHA_APP_DB_PASSWORD and inside DATABASE_URL. The repository holds no value for it." \
           "Nothing was changed."
fi
# <<< guard: app-password-set

# >>> guard: app-password-shape
# The password is written into a URL and into a psql command without quoting, so it is restricted to characters
# that need none, and it must be long enough to be a password.
if [[ ! "$APP_PASSWORD" =~ ^[A-Za-z0-9._~-]{20,128}$ ]]; then
    refuse "[app_db_password_shape] ALPHA_APP_DB_PASSWORD is not 20 to 128 characters from A-Z a-z 0-9 . _ ~ -." \
           "Those are the characters a URL and a command line carry unchanged. The value is not printed." \
           "Nothing was changed."
fi
# <<< guard: app-password-shape

# >>> guard: app-password-differs
if [ "$APP_PASSWORD" = "$PG_PASSWORD" ]; then
    refuse "[app_db_password_is_owner_password] ALPHA_APP_DB_PASSWORD equals POSTGRES_PASSWORD." \
           "Two roles with one password are one credential: whoever has the application's can become the owner." \
           "Nothing was changed."
fi
# <<< guard: app-password-differs

# >>> guard: database-urls-coherent
# `DATABASE_URL` is the APPLICATION's, `MIGRATOR_DATABASE_URL` the owner's, and each embeds its password a second
# time (`D-103`'s lesson). Both are read as data and compared with the names that are meant to be their source,
# so a URL that still carries the owner role (the state of every stack before this item) is a sentence here and
# not an api that connects as the owner while this script reports the application role set up.
URL_RE='^postgresql\+psycopg://([^:@/]+):([^@/]+)@([^:@/]+):([0-9]+)/([^?]+)$'
URL_PROBLEMS=()
if [[ "$(configured DATABASE_URL)" =~ $URL_RE ]]; then
    [ "${BASH_REMATCH[1]}" = "$APP_ROLE" ] || URL_PROBLEMS+=(
        "  DATABASE_URL's user is '${BASH_REMATCH[1]}' but ALPHA_APP_DB_USER is '$APP_ROLE'")
    [ "${BASH_REMATCH[2]}" = "$APP_PASSWORD" ] || URL_PROBLEMS+=(
        "  DATABASE_URL's password does not match ALPHA_APP_DB_PASSWORD")
    [ "${BASH_REMATCH[5]}" = "$PG_DB" ] || URL_PROBLEMS+=(
        "  DATABASE_URL's database is '${BASH_REMATCH[5]}' but POSTGRES_DB is '$PG_DB'")
else
    URL_PROBLEMS+=("  DATABASE_URL does not parse as postgresql+psycopg://user:password@host:port/db")
fi
if [[ "$(configured MIGRATOR_DATABASE_URL)" =~ $URL_RE ]]; then
    [ "${BASH_REMATCH[1]}" = "$PG_USER" ] || URL_PROBLEMS+=(
        "  MIGRATOR_DATABASE_URL's user is '${BASH_REMATCH[1]}' but POSTGRES_USER is '$PG_USER'")
    [ "${BASH_REMATCH[2]}" = "$PG_PASSWORD" ] || URL_PROBLEMS+=(
        "  MIGRATOR_DATABASE_URL's password does not match POSTGRES_PASSWORD")
    [ "${BASH_REMATCH[5]}" = "$PG_DB" ] || URL_PROBLEMS+=(
        "  MIGRATOR_DATABASE_URL's database is '${BASH_REMATCH[5]}' but POSTGRES_DB is '$PG_DB'")
else
    URL_PROBLEMS+=("  MIGRATOR_DATABASE_URL is unset or does not parse as postgresql+psycopg://user:password@host:port/db")
fi
if [ "${#URL_PROBLEMS[@]}" -gt 0 ]; then
    refuse "[database_urls_incoherent] DATABASE_URL (the application's) and MIGRATOR_DATABASE_URL (the owner's) must" \
           "carry the roles and passwords this file names, and at least one does not:" \
           "${URL_PROBLEMS[@]}" \
           "Nothing was changed."
fi
# <<< guard: database-urls-coherent

if [ "$MODE" = config ]; then
    echo "apply-grants.sh: the settings are coherent: the application role '$APP_ROLE' is not the owner '$PG_USER'."
    exit 0
fi

# >>> guard: compose-file-present
if [ ! -r "$COMPOSE_FILE" ]; then
    refuse "$COMPOSE_FILE is missing." \
           "Every step runs through it; without it this script has no database it is allowed to reach."
fi
# <<< guard: compose-file-present

compose() { docker compose --env-file "$ENV_FILE" --file "$COMPOSE_FILE" "$@"; }

# THE SQL. Generated from `scripts/recovery/grant_classification.py`; `test_apply_grants_script.py` fails when it
# is stale. `python -m scripts.recovery.grant_classification --write-script infra/deploy/apply-grants.sh` rewrites it.
# >>> generated: apply-sql
APPLY_SQL="$(cat <<'AM_GRANTS_SQL'
-- generated by scripts/recovery/grant_classification.py; do not edit by hand
\set ON_ERROR_STOP on
BEGIN;
SELECT set_config('statement_timeout', '120s', true);
CREATE TEMP TABLE am_class (name text PRIMARY KEY, kind text NOT NULL, privs text NOT NULL, lock_only boolean NOT NULL) ON COMMIT DROP;
INSERT INTO am_class (name, kind, privs, lock_only) VALUES
  ('account_release_mark', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('alembic_version', 'table', 'SELECT', false),
  ('analysis_artifact_publication', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('analysis_preset_revision', 'table', 'SELECT, INSERT', false),
  ('app_user', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('app_user_role', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('ar_v3_run_group', 'table', 'SELECT, INSERT', false),
  ('ar_v3_run_group_member', 'table', 'SELECT, INSERT', false),
  ('attempt', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('audit_event', 'table', 'SELECT, INSERT', false),
  ('audit_run', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('blob', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('command_record', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_ai_job', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_ai_link', 'table', 'SELECT, INSERT', false),
  ('comparison_ai_pair_answer', 'table', 'SELECT, INSERT', false),
  ('comparison_ai_pair_question', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_ai_sheet_item', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_launch_entry', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_launch_queue', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_matrix', 'table', 'SELECT, INSERT', false),
  ('comparison_matrix_edit', 'table', 'SELECT, INSERT', false),
  ('comparison_model_call', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_page_profile', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_report', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_report_artifact', 'table', 'SELECT, INSERT', false),
  ('comparison_report_part', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_series', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_sheet_description', 'table', 'SELECT, INSERT', false),
  ('comparison_sheet_link', 'table', 'SELECT, INSERT', false),
  ('comparison_sheet_pair', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_sheet_pair_result', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_spec_comparison', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_spec_extraction', 'table', 'SELECT, INSERT', false),
  ('comparison_summary', 'table', 'SELECT, INSERT', false),
  ('comparison_transition', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_upload', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_upload_file', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_upload_part', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_upload_set', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_version_order', 'table', 'SELECT, INSERT', false),
  ('comparison_work', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_work_attempt', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('contract_state_transition', 'table', 'SELECT', false),
  ('document', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('document_version', 'table', 'SELECT, INSERT', false),
  ('document_version_classification', 'table', 'SELECT, INSERT', true),
  ('document_version_classification_correction', 'table', 'SELECT, INSERT', false),
  ('execution_control', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('executor_connection', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('executor_connection_revision', 'table', 'SELECT, INSERT', false),
  ('executor_probe', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('executor_route_event', 'table', 'SELECT, INSERT', false),
  ('executor_runner_token', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('executor_secret', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('executor_task', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('expert_decision_event', 'table', 'SELECT, INSERT', false),
  ('finding', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('finding_evidence', 'table', 'SELECT, INSERT', false),
  ('finding_observation', 'table', 'SELECT, INSERT', false),
  ('finding_observation_norm_citation', 'table', 'SELECT, INSERT', false),
  ('input_manifest_entry', 'table', 'SELECT, INSERT', false),
  ('job', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('lease', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('model_call', 'table', 'SELECT, INSERT', false),
  ('norm_chunk', 'table', 'SELECT, INSERT', false),
  ('norm_chunk_build', 'table', 'SELECT, INSERT', false),
  ('norm_current_snapshot', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('norm_current_snapshot_event', 'table', 'SELECT, INSERT', false),
  ('norm_custody_admission', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('norm_custody_binding', 'table', 'SELECT, INSERT', false),
  ('norm_document', 'table', 'SELECT, INSERT', false),
  ('norm_embedding', 'table', 'SELECT, INSERT', false),
  ('norm_embedding_build', 'table', 'SELECT, INSERT', false),
  ('norm_embedding_profile', 'table', 'SELECT', false),
  ('norm_paragraph', 'table', 'SELECT, INSERT', false),
  ('norm_repair_call', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('norm_retrieval_set', 'table', 'SELECT, INSERT', false),
  ('norms_snapshot', 'table', 'SELECT, INSERT', false),
  ('optimisation_pass', 'table', 'SELECT, INSERT', false),
  ('optimisation_proposal', 'table', 'SELECT, INSERT', false),
  ('optimisation_proposal_decision', 'table', 'SELECT, INSERT', false),
  ('price_list_position', 'table', 'SELECT, INSERT', false),
  ('price_list_revision', 'table', 'SELECT, INSERT', false),
  ('project', 'table', 'SELECT, INSERT', false),
  ('provider_call_effect', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('registration_request', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('release', 'table', 'SELECT, INSERT', false),
  ('release_revision', 'table', 'SELECT, INSERT', false),
  ('stage_result', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('vendor_list_entry', 'table', 'SELECT, INSERT', false),
  ('vendor_list_revision', 'table', 'SELECT, INSERT', false),
  ('work_assignment', 'table', 'SELECT, INSERT', true),
  ('work_assignment_event', 'table', 'SELECT, INSERT', false),
  ('worker', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('executor_route_current', 'view', 'SELECT', false),
  ('finding_current_verdict', 'view', 'SELECT', false),
  ('version_classification_current', 'view', 'SELECT', false),
  ('version_classification_revision', 'view', 'SELECT', false),
  ('work_assignment_current', 'view', 'SELECT', false);
CREATE TEMP TABLE am_callable (name text PRIMARY KEY) ON COMMIT DROP;
INSERT INTO am_callable (name) VALUES
  ('am_is_ascending_page_list'),
  ('norm_designation_tokens');
-- 0. fail closed: a relation the classification does not name is refused before any right is granted.
DO $am$
DECLARE unknown text;
BEGIN
  SELECT string_agg(format('%s %I.%I', CASE c.relkind WHEN 'S' THEN 'sequence' WHEN 'v' THEN 'view' ELSE 'table' END,
                           n.nspname, c.relname), ', ' ORDER BY n.nspname, c.relname)
    INTO unknown
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname <> 'information_schema' AND n.nspname !~ '^pg_'
     AND c.relkind IN ('r', 'p', 'v', 'm', 'f', 'S')
     AND NOT (n.nspname = 'public' AND (
           (c.relkind IN ('r', 'p') AND EXISTS (SELECT 1 FROM am_class k WHERE k.name = c.relname AND k.kind = 'table'))
        OR (c.relkind = 'v' AND EXISTS (SELECT 1 FROM am_class k WHERE k.name = c.relname AND k.kind = 'view'))
        OR (c.relkind = 'S' AND EXISTS (
              SELECT 1 FROM pg_depend d JOIN pg_class t ON t.oid = d.refobjid
                JOIN am_class k ON k.name = t.relname AND k.kind = 'table'
               WHERE d.classid = 'pg_class'::regclass AND d.objid = c.oid AND d.refclassid = 'pg_class'::regclass
                 AND d.deptype IN ('a', 'i') AND t.relnamespace = 'public'::regnamespace))));
  IF unknown IS NOT NULL THEN
    RAISE EXCEPTION '[grants_unclassified] no grant classification for: %', unknown
      USING HINT = 'add it to scripts/recovery/grant_classification.py and regenerate infra/deploy/apply-grants.sh';
  END IF;
END
$am$;
-- 1. the role: created if absent, its attributes and password set every time (a rotated password lands here).
SELECT format('CREATE ROLE %I', :'app_role') WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_role') \gexec
ALTER ROLE :"app_role" WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD :'app_password';
SELECT format('REVOKE %s FROM %I', m.roleid::regrole, :'app_role')
  FROM pg_auth_members m JOIN pg_roles r ON r.oid = m.member WHERE r.rolname = :'app_role' ORDER BY m.roleid::regrole::text \gexec
-- 2. the database and the schema: connect and look, never create.
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'app_role') \gexec
SELECT format('REVOKE CREATE ON DATABASE %I FROM %I', current_database(), :'app_role') \gexec
GRANT USAGE ON SCHEMA public TO :"app_role";
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM :"app_role";
-- 3. a clean slate, then exactly the classification.
SELECT format('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM %I', :'app_role') \gexec
SELECT format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM %I', :'app_role') \gexec
SELECT format('GRANT %s ON TABLE public.%I TO %I', k.privs, k.name, :'app_role')
  FROM am_class k WHERE k.privs <> '' AND to_regclass(format('public.%I', k.name)) IS NOT NULL ORDER BY k.name \gexec
SELECT format('GRANT UPDATE (%I) ON TABLE public.%I TO %I', a.attname, k.name, :'app_role')
  FROM am_class k
  JOIN pg_index i ON i.indrelid = to_regclass(format('public.%I', k.name)) AND i.indisprimary
  JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = i.indkey[0]
 WHERE k.lock_only ORDER BY k.name \gexec
SELECT format('GRANT USAGE ON SEQUENCE public.%I TO %I', s.relname, :'app_role')
  FROM pg_class s
  JOIN pg_depend d ON d.classid = 'pg_class'::regclass AND d.objid = s.oid AND d.refclassid = 'pg_class'::regclass AND d.deptype IN ('a', 'i')
  JOIN pg_class t ON t.oid = d.refobjid AND t.relnamespace = 'public'::regnamespace
  JOIN am_class k ON k.name = t.relname AND k.kind = 'table'
 WHERE s.relkind = 'S' AND s.relnamespace = 'public'::regnamespace AND k.privs LIKE '%INSERT%' ORDER BY s.relname \gexec
SELECT format('GRANT EXECUTE ON FUNCTION %s TO %I', p.oid::regprocedure, :'app_role')
  FROM pg_proc p JOIN am_callable f ON f.name = p.proname
 WHERE p.pronamespace = 'public'::regnamespace AND p.prokind = 'f' ORDER BY p.proname \gexec
COMMIT;
AM_GRANTS_SQL
)"
# <<< generated: apply-sql
# >>> generated: check-sql
CHECK_SQL="$(cat <<'AM_GRANTS_SQL'
-- generated by scripts/recovery/grant_classification.py; do not edit by hand
\set ON_ERROR_STOP on
WITH
cls (name, kind, privs, lock_only) AS (VALUES
  ('account_release_mark', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('alembic_version', 'table', 'SELECT', false),
  ('analysis_artifact_publication', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('analysis_preset_revision', 'table', 'SELECT, INSERT', false),
  ('app_user', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('app_user_role', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('ar_v3_run_group', 'table', 'SELECT, INSERT', false),
  ('ar_v3_run_group_member', 'table', 'SELECT, INSERT', false),
  ('attempt', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('audit_event', 'table', 'SELECT, INSERT', false),
  ('audit_run', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('blob', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('command_record', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_ai_job', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_ai_link', 'table', 'SELECT, INSERT', false),
  ('comparison_ai_pair_answer', 'table', 'SELECT, INSERT', false),
  ('comparison_ai_pair_question', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_ai_sheet_item', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_launch_entry', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_launch_queue', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_matrix', 'table', 'SELECT, INSERT', false),
  ('comparison_matrix_edit', 'table', 'SELECT, INSERT', false),
  ('comparison_model_call', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_page_profile', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_report', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_report_artifact', 'table', 'SELECT, INSERT', false),
  ('comparison_report_part', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_series', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_sheet_description', 'table', 'SELECT, INSERT', false),
  ('comparison_sheet_link', 'table', 'SELECT, INSERT', false),
  ('comparison_sheet_pair', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_sheet_pair_result', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_spec_comparison', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_spec_extraction', 'table', 'SELECT, INSERT', false),
  ('comparison_summary', 'table', 'SELECT, INSERT', false),
  ('comparison_transition', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_upload', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_upload_file', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_upload_part', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_upload_set', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_version_order', 'table', 'SELECT, INSERT', false),
  ('comparison_work', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('comparison_work_attempt', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('contract_state_transition', 'table', 'SELECT', false),
  ('document', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('document_version', 'table', 'SELECT, INSERT', false),
  ('document_version_classification', 'table', 'SELECT, INSERT', true),
  ('document_version_classification_correction', 'table', 'SELECT, INSERT', false),
  ('execution_control', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('executor_connection', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('executor_connection_revision', 'table', 'SELECT, INSERT', false),
  ('executor_probe', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('executor_route_event', 'table', 'SELECT, INSERT', false),
  ('executor_runner_token', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('executor_secret', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('executor_task', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('expert_decision_event', 'table', 'SELECT, INSERT', false),
  ('finding', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('finding_evidence', 'table', 'SELECT, INSERT', false),
  ('finding_observation', 'table', 'SELECT, INSERT', false),
  ('finding_observation_norm_citation', 'table', 'SELECT, INSERT', false),
  ('input_manifest_entry', 'table', 'SELECT, INSERT', false),
  ('job', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('lease', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('model_call', 'table', 'SELECT, INSERT', false),
  ('norm_chunk', 'table', 'SELECT, INSERT', false),
  ('norm_chunk_build', 'table', 'SELECT, INSERT', false),
  ('norm_current_snapshot', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('norm_current_snapshot_event', 'table', 'SELECT, INSERT', false),
  ('norm_custody_admission', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('norm_custody_binding', 'table', 'SELECT, INSERT', false),
  ('norm_document', 'table', 'SELECT, INSERT', false),
  ('norm_embedding', 'table', 'SELECT, INSERT', false),
  ('norm_embedding_build', 'table', 'SELECT, INSERT', false),
  ('norm_embedding_profile', 'table', 'SELECT', false),
  ('norm_paragraph', 'table', 'SELECT, INSERT', false),
  ('norm_repair_call', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('norm_retrieval_set', 'table', 'SELECT, INSERT', false),
  ('norms_snapshot', 'table', 'SELECT, INSERT', false),
  ('optimisation_pass', 'table', 'SELECT, INSERT', false),
  ('optimisation_proposal', 'table', 'SELECT, INSERT', false),
  ('optimisation_proposal_decision', 'table', 'SELECT, INSERT', false),
  ('price_list_position', 'table', 'SELECT, INSERT', false),
  ('price_list_revision', 'table', 'SELECT, INSERT', false),
  ('project', 'table', 'SELECT, INSERT', false),
  ('provider_call_effect', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('registration_request', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('release', 'table', 'SELECT, INSERT', false),
  ('release_revision', 'table', 'SELECT, INSERT', false),
  ('stage_result', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('vendor_list_entry', 'table', 'SELECT, INSERT', false),
  ('vendor_list_revision', 'table', 'SELECT, INSERT', false),
  ('work_assignment', 'table', 'SELECT, INSERT', true),
  ('work_assignment_event', 'table', 'SELECT, INSERT', false),
  ('worker', 'table', 'SELECT, INSERT, UPDATE, DELETE', false),
  ('executor_route_current', 'view', 'SELECT', false),
  ('finding_current_verdict', 'view', 'SELECT', false),
  ('version_classification_current', 'view', 'SELECT', false),
  ('version_classification_revision', 'view', 'SELECT', false),
  ('work_assignment_current', 'view', 'SELECT', false)),
callable (name) AS (VALUES
  ('am_is_ascending_page_list'),
  ('norm_designation_tokens')),
role AS (SELECT oid, rolname FROM pg_roles WHERE rolname = :'app_role'),
privileges (privilege) AS (VALUES ('SELECT'), ('INSERT'), ('UPDATE'), ('DELETE'), ('TRUNCATE'), ('REFERENCES'), ('TRIGGER'), ('MAINTAIN')),
problems (object, detail) AS (
  SELECT 'role', 'does not exist' WHERE NOT EXISTS (SELECT 1 FROM role)
  UNION ALL SELECT 'role', 'has an attribute it must not have (superuser, createdb, createrole, replication, bypassrls) or cannot log in'
    FROM pg_roles r WHERE r.rolname = :'app_role'
     AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls OR NOT r.rolcanlogin)
  UNION ALL SELECT 'role', 'is a member of ' || m.roleid::regrole::text
    FROM pg_auth_members m JOIN role ON role.oid = m.member
  UNION ALL SELECT 'schema public', 'the role can CREATE in it'
    FROM role WHERE has_schema_privilege(role.oid, 'public', 'CREATE')
  UNION ALL SELECT 'schema public', 'the role cannot USAGE it'
    FROM role WHERE NOT has_schema_privilege(role.oid, 'public', 'USAGE')
  UNION ALL SELECT 'database ' || current_database(), 'the role can CREATE in it'
    FROM role WHERE has_database_privilege(role.oid, current_database(), 'CREATE')
  UNION ALL SELECT 'database ' || current_database(), 'the role cannot CONNECT'
    FROM role WHERE NOT has_database_privilege(role.oid, current_database(), 'CONNECT')
  UNION ALL SELECT 'owner', format('the role owns %s %s', CASE c.relkind WHEN 'S' THEN 'sequence' WHEN 'v' THEN 'view' ELSE 'table' END, c.relname)
    FROM pg_class c JOIN role ON role.oid = c.relowner
  UNION ALL SELECT 'owner', 'the role owns function ' || p.proname FROM pg_proc p JOIN role ON role.oid = p.proowner
  UNION ALL SELECT 'owner', 'the role owns schema ' || n.nspname FROM pg_namespace n JOIN role ON role.oid = n.nspowner
  UNION ALL SELECT 'owner', 'the role owns database ' || d.datname FROM pg_database d JOIN role ON role.oid = d.datdba
  UNION ALL SELECT 'relation ' || n.nspname || '.' || c.relname, 'has no grant classification'
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname <> 'information_schema' AND n.nspname !~ '^pg_' AND c.relkind IN ('r', 'p', 'v', 'm', 'f', 'S')
     AND NOT (n.nspname = 'public' AND (
           (c.relkind IN ('r', 'p') AND EXISTS (SELECT 1 FROM cls k WHERE k.name = c.relname AND k.kind = 'table'))
        OR (c.relkind = 'v' AND EXISTS (SELECT 1 FROM cls k WHERE k.name = c.relname AND k.kind = 'view'))
        OR (c.relkind = 'S' AND EXISTS (
              SELECT 1 FROM pg_depend d JOIN pg_class t ON t.oid = d.refobjid JOIN cls k ON k.name = t.relname AND k.kind = 'table'
               WHERE d.classid = 'pg_class'::regclass AND d.objid = c.oid AND d.refclassid = 'pg_class'::regclass
                 AND d.deptype IN ('a', 'i') AND t.relnamespace = 'public'::regnamespace))))
  UNION ALL SELECT k.kind || ' ' || k.name,
         CASE WHEN want THEN 'the role lacks ' ELSE 'the role holds ' END || p.privilege
    FROM (SELECT cls.*, to_regclass(format('public.%I', cls.name)) AS rel FROM cls) k
    CROSS JOIN privileges p CROSS JOIN role
    CROSS JOIN LATERAL (SELECT strpos(' ' || replace(k.privs, ',', ' ') || ' ', ' ' || p.privilege || ' ') > 0 AS want) w
   WHERE k.rel IS NOT NULL
     AND has_table_privilege(role.oid, k.rel, p.privilege) <> w.want
  UNION ALL SELECT 'table ' || k.name, 'the role has no UPDATE on its lock column ' || a.attname
    FROM (SELECT cls.*, to_regclass(format('public.%I', cls.name)) AS rel FROM cls) k
    JOIN pg_index i ON i.indrelid = k.rel AND i.indisprimary
    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = i.indkey[0] CROSS JOIN role
   WHERE k.lock_only AND NOT has_column_privilege(role.oid, k.rel, a.attname, 'UPDATE')
  UNION ALL SELECT 'table ' || k.name, 'the role can UPDATE ' || a.attname || ', which is not its lock column'
    FROM (SELECT cls.*, to_regclass(format('public.%I', cls.name)) AS rel FROM cls) k
    JOIN pg_attribute a ON a.attrelid = k.rel AND a.attnum > 0 AND NOT a.attisdropped CROSS JOIN role
   WHERE k.lock_only AND has_column_privilege(role.oid, k.rel, a.attname, 'UPDATE')
     AND a.attnum <> (SELECT i.indkey[0] FROM pg_index i WHERE i.indrelid = k.rel AND i.indisprimary)
  UNION ALL SELECT 'sequence ' || s.relname,
         CASE WHEN k.privs LIKE '%INSERT%' THEN 'the role cannot USAGE it' ELSE 'the role can USAGE it' END
    FROM pg_class s
    JOIN pg_depend d ON d.classid = 'pg_class'::regclass AND d.objid = s.oid AND d.refclassid = 'pg_class'::regclass AND d.deptype IN ('a', 'i')
    JOIN pg_class t ON t.oid = d.refobjid AND t.relnamespace = 'public'::regnamespace
    JOIN cls k ON k.name = t.relname AND k.kind = 'table' CROSS JOIN role
   WHERE s.relkind = 'S' AND s.relnamespace = 'public'::regnamespace
     AND has_sequence_privilege(role.oid, s.oid, 'USAGE') <> (k.privs LIKE '%INSERT%')
  UNION ALL SELECT 'sequence ' || s.relname, 'the role holds ' || p.privilege
    FROM pg_class s CROSS JOIN (VALUES ('SELECT'), ('UPDATE')) p (privilege) CROSS JOIN role
   WHERE s.relkind = 'S' AND s.relnamespace = 'public'::regnamespace
     AND has_sequence_privilege(role.oid, s.oid, p.privilege)
  UNION ALL SELECT 'function ' || p.proname, 'the role cannot EXECUTE it'
    FROM pg_proc p JOIN callable f ON f.name = p.proname CROSS JOIN role
   WHERE p.pronamespace = 'public'::regnamespace AND p.prokind = 'f' AND NOT has_function_privilege(role.oid, p.oid, 'EXECUTE')
)
SELECT object || ': ' || detail FROM problems ORDER BY object, detail;
AM_GRANTS_SQL
)"
# <<< generated: check-sql

# The owner role runs everything, by the unix socket inside the container (no password on a command line).
# `-v app_role=...` is a name and not a secret; the password goes in on stdin.
psql_owner() {
    compose exec -T postgres psql --no-psqlrc --quiet --no-align --tuples-only \
        --username "$PG_USER" --dbname "$PG_DB" -v ON_ERROR_STOP=1 -v "app_role=$APP_ROLE"
}

# The statements go to `psql` from a file, not a pipe: a `docker` that exits before reading its input (a stub, a
# daemon that refused) would otherwise hand this script a SIGPIPE in the middle of a write. The file holds the
# password for the length of the run, so it is created private and removed on every exit.
umask 077
SQL_ERR="$(mktemp)"
SQL_IN="$(mktemp)"
trap 'rm -f "$SQL_ERR" "$SQL_IN"' EXIT

verify() {
    local out status=0
    printf '%s\n' "$CHECK_SQL" > "$SQL_IN"
    out="$(psql_owner < "$SQL_IN" 2>"$SQL_ERR")" || status=$?
    if [ "$status" -ne 0 ]; then
        cat "$SQL_ERR" >&2
        fail "the verification could not be run (status $status)." \
             "Is the postgres service of the stack running? docker compose --env-file $ENV_FILE --file $COMPOSE_FILE ps postgres"
    fi
    if [ -n "$out" ]; then
        printf 'apply-grants.sh: [grants_drift] the application role %s differs from the classification:\n' "$APP_ROLE" >&2
        printf '%s\n' "$out" | sed 's/^/  /' >&2
        return 1
    fi
    return 0
}

if [ "$MODE" = check ]; then
    verify || exit 1
    echo "grants-ok: $APP_ROLE on $PG_DB matches the classification"
    exit 0
fi

echo "apply-grants.sh: applying the grant classification to $PG_DB for the application role '$APP_ROLE' (owner: $PG_USER)"
{
    printf '\\set app_password '"'"'%s'"'"'\n' "$APP_PASSWORD"
    printf '%s\n' "$APPLY_SQL"
} > "$SQL_IN"
STATUS=0
psql_owner < "$SQL_IN" >/dev/null 2>"$SQL_ERR" || STATUS=$?
if [ "$STATUS" -ne 0 ]; then
    # The SQL may quote nothing secret on failure, but a server message can echo a statement: print only the
    # lines that name the reason, never the whole stream.
    if grep -q '\[grants_unclassified\]' "$SQL_ERR"; then
        refuse "$(grep -m1 '\[grants_unclassified\]' "$SQL_ERR" | sed 's/^.*\(\[grants_unclassified\]\)/\1/')" \
               "The schema holds a relation scripts/recovery/grant_classification.py does not name, so the application role" \
               "was given nothing and the transaction was rolled back. Classify it, regenerate this script, deploy again."
    fi
    grep -v -i 'password' "$SQL_ERR" >&2 || true
    fail "the grants could not be applied (status $STATUS); the transaction was rolled back."
fi
verify || fail "the rights were applied and the verification found a difference (above)."
echo "grants-ok: $APP_ROLE on $PG_DB matches the classification"
