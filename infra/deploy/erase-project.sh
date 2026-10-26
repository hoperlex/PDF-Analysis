#!/usr/bin/env bash
# `ERASE-WRAP-01` (`PROD-07`, second half) -- erase ONE project: its documents, pages, text, crops, findings, evidence
# quotes, comments and expert decisions, and every Blob only it references. What stays is the record of the erasure.
#
#   infra/deploy/erase-project.sh --database <name> --bucket <name> --project prj_<ULID>             # the dry run
#   infra/deploy/erase-project.sh --database <name> --bucket <name> --project prj_<ULID> --apply \
#         --actor <admin login> --reason <client_request|end_of_engagement|test_data|other> \
#         --owner-permission-ref "<where the owner's permission is recorded>" --plan-sha256 <the dry run's digest>
#   infra/deploy/erase-project.sh --database <name> --bucket <name> --resume era_<ULID> \
#         --actor <admin login> --owner-permission-ref "<...>"
#
# THE DESIGN IS `ADR-0022` SECTION 3 AND `scripts/recovery/project_erase.py` (`PROD-07A-PROJECT-ERASE-CORE-01`). This file
# is the operator's door to that module and nothing more: it holds the guards that can be checked before a connection,
# runs the module inside the `api` image the way `purge-product-data.sh` runs the purge, makes the operator retype what
# is about to be erased, and says what to do when something stops half way. The scope, the plan, the transaction and
# the four phases are the module's; read its header for them.
#
# WHAT IS DIFFERENT FROM `purge-product-data.sh`, ON PURPOSE:
#
#   * NO `pg_dump` AND NO OBJECT MIRROR IS TAKEN FIRST. The purge dumps because it can be put back with `reset.sh
#     --restore`; an erase that took a dump would keep the very data it was asked to remove. So this script writes
#     exactly two small files (`plan.json` and `manifest.json`, under `infra/deploy/dumps/erasures/<era_id>/`), which are
#     the only record of what was erased, and it says in its closing text that EVERY EXISTING DUMP, MIRROR AND COPY
#     STILL HOLDS THE PROJECT. Removing those is the operator's, by hand (runbook section 17).
#   * IT IS A DRY RUN UNLESS TOLD OTHERWISE. `--apply` needs the project id, the actor, the reason, the owner's
#     permission reference and the digest of the plan the operator read -- and then makes the operator RETYPE the
#     project id and the digest. A digest passed on the command line proves only that someone copied it.
#   * THE CONTAINER RUNS AS THE OPERATOR'S UID, not as root, and the dump directory is a writable mount: the module
#     writes the two files 0600 in a directory 0700, so a root-owned result would be unreadable to the operator, and
#     the manifest holds a fingerprint of every erased document (kept out of the database on purpose).
#   * IT CHECKS ITS OWN RESULT. After a successful erase it hashes `manifest.json` on the host and compares the digest
#     with the one the tool printed (and wrote into both journal events). A file that does not hash to what the database
#     holds is not a record.
#
# THE PYTHON HALF CONNECTS AS THE OWNER (`PROD-04-DB-ROLES-01`, `AD-02`). `api` runs as an application role that owns
# nothing and cannot switch a trigger off, so the module refuses its own `DATABASE_URL`. This script hands the one-off
# container `MIGRATOR_DATABASE_URL` as `DATABASE_URL`, through the environment of the `docker compose` process (compose
# substitutes it into the `api` service's `environment:`; the password never appears in a command line), exactly as
# `purge-product-data.sh` does. No `PG*` variable is passed: the module refuses a run in which libpq has another idea of
# the target.
#
# THE TARGET IS ALWAYS THIS STACK, through `docker compose -f compose.server.yml` and the typed names, as in the purge.
# The stack must be UP (postgres and s3): the one-off container is started with `--no-deps`.
#
# EXIT CODES: 0 done or nothing to do; 2 usage; 3 REFUSED (nothing was changed); 4 FAILED. A step that stops AFTER the
# commit exits 4 -- never 3, because 3 promises that nothing was changed -- and prints the erase id and the exact
# `--resume` command that finishes it.
#
# GUARDS ARE DELIMITED BY MARKERS -- `# >>> guard: <name>` / `# <<< guard: <name>`.
# `tests/integration/composition/test_erase_project_script.py` reads those markers, deletes ONE guard block from a copy of
# this file and shows the copy no longer refuses. A guard that cannot be shown to fail is not evidence. Do not remove a
# marker without removing its test.

set -Eeuo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$HERE/compose.server.yml"
ENV_FILE="${ALPHA_ENV_FILE:-$HERE/env/alpha.env}"
DUMP_ROOT="${ALPHA_DUMP_ROOT:-$HERE/dumps}"
MODULE_DIR="${ALPHA_ERASE_MODULE_DIR:-$HERE/../../scripts/recovery}"
# The four files the module needs and nothing else (`project_erase` imports the other three; `PROD-07A` section 8).
MODULES=(project_erase product_purge schema_coverage blob_reference_audit)

DATABASE=""
BUCKET=""
PROJECT=""
DRY_RUN=no
APPLY=no
RESUME=""
ACTOR=""
REASON=""
PERMISSION_REF=""
PLAN_SHA_GIVEN=""
STOP_WORKER=no
HAVE_PROJECT=no

SELF="$0"

refuse() {
    printf 'erase-project.sh: REFUSED: %s\n' "$1" >&2
    shift
    [ "$#" -eq 0 ] || printf '  %s\n' "$@" >&2
    exit 3
}

fail() {
    printf 'erase-project.sh: FAILED: %s\n' "$1" >&2
    shift
    [ "$#" -eq 0 ] || printf '  %s\n' "$@" >&2
    exit 4
}

usage() {
    cat >&2 <<'USAGE'
usage: erase-project.sh --database <name> --bucket <name> --project prj_<ULID> [--dry-run]
       erase-project.sh --database <name> --bucket <name> --project prj_<ULID> --apply
                        --actor <admin login> --reason <code> --owner-permission-ref "<text>"
                        --plan-sha256 <digest> [--stop-worker]
       erase-project.sh --database <name> --bucket <name> --resume era_<ULID>
                        --actor <admin login> --owner-permission-ref "<text>" [--stop-worker]

  --database <name>            the database this acts on. Must equal the configured one.
  --bucket <name>              the bucket this acts on. Must equal the configured one.
  --project prj_<ULID>         the project, by identity. Never a name.
  --dry-run                    the default: print the plan and its sha256. Changes nothing.
  --apply                      erase. Needs everything below, and the operator retypes the project id and the digest.
  --resume era_<ULID>          finish an erase that committed and did not complete (the erase id was printed).
  --actor <login>              the administrator on whose account the erase is journalled.
  --reason <code>              one of: client_request, end_of_engagement, test_data, other.
  --owner-permission-ref <t>   one line, at most 200 characters: where the OWNER's permission to erase this project is
                               recorded. An operator never erases a project without it (R-146aj). It is recorded as
                               given and never verified.
  --plan-sha256 <digest>       the plan-sha256 the dry run printed.
  --stop-worker                stop the worker for the apply or the resume and start it again afterwards. For a refusal
                               "could not lock the tables": the worker's heartbeat is the usual writer.
  --env-file <path>            default: infra/deploy/env/alpha.env

NO DUMP IS TAKEN, because a dump would keep the erased data. Every existing dump, mirror and copy still holds the project.
USAGE
    exit 2
}

# `exit 4` for anything a command did not handle itself: a refusal is 3 and is spelled out.
on_error() {
    printf 'erase-project.sh: FAILED: a step exited non-zero (line %s).\n' "$1" >&2
    exit 4
}
trap 'on_error $LINENO' ERR

# >>> guard: known-options
# An unrecognised option is refused rather than ignored, and so is one that has lost its value: `--reaason` silently
# ignored would run an erase the operator believed was reasoned, and a trailing `--project` would swallow the next word.
while [ "$#" -gt 0 ]; do
    case "$1" in
        --database|--bucket|--project|--resume|--actor|--reason|--owner-permission-ref|--plan-sha256|--env-file)
            [ "$#" -ge 2 ] || refuse "$1 needs a value." "Nothing was read and nothing was touched. Run --help." ;;
    esac
    case "$1" in
        --database) DATABASE="$2"; shift 2 ;;
        --bucket) BUCKET="$2"; shift 2 ;;
        --project) PROJECT="$2"; HAVE_PROJECT=yes; shift 2 ;;
        --resume) RESUME="$2"; shift 2 ;;
        --actor) ACTOR="$2"; shift 2 ;;
        --reason) REASON="$2"; shift 2 ;;
        --owner-permission-ref) PERMISSION_REF="$2"; shift 2 ;;
        --plan-sha256) PLAN_SHA_GIVEN="$2"; shift 2 ;;
        --env-file) ENV_FILE="$2"; shift 2 ;;
        --dry-run) DRY_RUN=yes; shift ;;
        --apply) APPLY=yes; shift ;;
        --stop-worker) STOP_WORKER=yes; shift ;;
        -h|--help) usage ;;
        *) refuse "unrecognised option: $1" \
                  "Nothing was read and nothing was touched. Run --help." ;;
    esac
done
# <<< guard: known-options

# >>> guard: one-mode
# No mode at all is the dry run: the safe thing is what an omission means. Two modes are a contradiction.
modes=0
[ "$DRY_RUN" = yes ] && modes=$((modes + 1))
[ "$APPLY" = yes ] && modes=$((modes + 1))
[ -n "$RESUME" ] && modes=$((modes + 1))
if [ "$modes" -gt 1 ]; then
    refuse "--dry-run, --apply and --resume were more than one." \
           "They are different things to do to one project. Choose one (no option at all is the dry run)."
fi
# <<< guard: one-mode

MODE=plan
[ "$APPLY" = yes ] && MODE=apply
[ -n "$RESUME" ] && MODE=resume

# >>> guard: stop-worker-needs-a-write-mode
# A dry run changes nothing, so there is nothing to stop the worker for; accepting the option and ignoring it would
# tell the operator the worker was stopped when it was not.
if [ "$STOP_WORKER" = yes ] && [ "$MODE" = plan ]; then
    refuse "--stop-worker belongs to --apply or --resume." \
           "A dry run changes nothing and does not stop anything. Nothing was read and nothing was touched."
fi
# <<< guard: stop-worker-needs-a-write-mode

# >>> guard: options-match-the-mode
# An option that belongs to another mode is refused, not ignored: `--plan-sha256`, `--reason` and the rest of an apply
# given to a dry run would be read by the operator as an erase that was asked for, and a dry run is a different thing.
if [ "$MODE" = plan ] && { [ -n "$ACTOR" ] || [ -n "$REASON" ] || [ -n "$PERMISSION_REF" ] || [ -n "$PLAN_SHA_GIVEN" ]; }; then
    refuse "--actor, --reason, --owner-permission-ref and --plan-sha256 belong to --apply (or --resume), and no --apply was given." \
           "As given this is a dry run, which changes nothing. Add --apply to erase, or drop them. Nothing was read and nothing was touched."
fi
if [ "$MODE" = resume ] && { [ -n "$REASON" ] || [ -n "$PLAN_SHA_GIVEN" ]; }; then
    refuse "--reason and --plan-sha256 belong to --apply; a --resume finishes an erase that was already approved." \
           "Nothing was read and nothing was touched."
fi
# <<< guard: options-match-the-mode

# >>> guard: names-required
if [ -z "$DATABASE" ] || [ -z "$BUCKET" ]; then
    refuse "--database and --bucket are both required, even for the dry run." \
           "Typing the target is the point: it is what makes an erase in the wrong instance" \
           "a thing you have to do on purpose."
fi
# <<< guard: names-required

# >>> guard: project-identity-shape
# A project is addressed by its identity, never by its name: two projects may share one, and a name can carry personal
# data into a command line, a shell history and a journal. `--resume` names an erase, and a project with it is a
# contradiction (which target would win?).
if [ "$MODE" = resume ]; then
    if [ "$HAVE_PROJECT" = yes ]; then
        refuse "--project does not go with --resume." \
               "The erase id names the erase (and through it the project). Nothing was read and nothing was touched."
    fi
elif [[ ! "$PROJECT" =~ ^prj_[0-9A-HJKMNP-TV-Z]{26}$ ]]; then
    refuse "--project must be a project identity (prj_ and 26 characters), never a name." \
           "  given: ${PROJECT:-<none>}" \
           "Nothing was read and nothing was touched."
fi
# <<< guard: project-identity-shape

# >>> guard: erase-identity-shape
if [ "$MODE" = resume ] && [[ ! "$RESUME" =~ ^era_[0-9A-HJKMNP-TV-Z]{26}$ ]]; then
    refuse "--resume must be an erase identity (era_ and 26 characters)." \
           "  given: $RESUME" \
           "It is printed on the line 'erase-id:' of the run that stopped. Nothing was read and nothing was touched."
fi
# <<< guard: erase-identity-shape

# >>> guard: actor-required
# The erase is journalled on an administrator's account. The module checks that the account exists and holds `admin`;
# here the value must at least be one word, so that an empty string or a sentence is refused before a connection.
if [ "$MODE" != plan ]; then
    if [ -z "$ACTOR" ] || [[ "$ACTOR" =~ [[:space:][:cntrl:]] ]] || [ "${#ACTOR}" -gt 254 ]; then
        refuse "--actor must be the login of an administrator (one word)." \
               "  given: ${ACTOR:-<none>}" \
               "Nothing was read and nothing was touched."
    fi
fi
# <<< guard: actor-required

# >>> guard: reason-closed-list
# Free text is refused: it would put personal data into an append-only table.
if [ "$MODE" = apply ]; then
    case "$REASON" in
        client_request|end_of_engagement|test_data|other) ;;
        *) refuse "--reason must be one of: client_request, end_of_engagement, test_data, other." \
                  "  given: ${REASON:-<none>}" \
                  "Free text is refused because it would be written into the append-only journal. Nothing was touched." ;;
    esac
fi
# <<< guard: reason-closed-list

# >>> guard: owner-permission-ref
# `R-146aj`: an operator never erases a project without the owner's permission. Nothing here can verify a permission;
# what the script can do is refuse to run without a statement of where it is recorded, so that the journal carries it.
if [ "$MODE" != plan ]; then
    ref="$PERMISSION_REF"
    ref="${ref#"${ref%%[![:space:]]*}"}"
    ref="${ref%"${ref##*[![:space:]]}"}"
    if [ -z "$ref" ] || [ "${#ref}" -gt 200 ] || [[ "$PERMISSION_REF" =~ [[:cntrl:]] ]]; then
        refuse "--owner-permission-ref is required: one line of at most 200 characters saying where the owner's" \
               "permission to erase this project is recorded (R-146aj: never without it)." \
               "It is recorded as given and never verified. Nothing was read and nothing was touched."
    fi
    PERMISSION_REF="$ref"
fi
# <<< guard: owner-permission-ref

# >>> guard: plan-digest-shape
# The digest of the plan the operator READ. Without one the apply would be an erase of whatever the project is now.
if [ "$MODE" = apply ] && [[ ! "$PLAN_SHA_GIVEN" =~ ^[0-9a-f]{64}$ ]]; then
    refuse "--apply needs --plan-sha256 <the 64-hex digest the dry run printed>: an apply refuses a plan nobody approved." \
           "  given: ${PLAN_SHA_GIVEN:-<none>}" \
           "Run the dry run first (no mode option). Nothing was read and nothing was touched."
fi
# <<< guard: plan-digest-shape

# >>> guard: env-file-present
if [ ! -r "$ENV_FILE" ]; then
    refuse "the deployment environment $ENV_FILE is missing or unreadable." \
           "Without it there is no configured instance to compare the typed names against," \
           "and an unverifiable target is not a target. See env/alpha.env.example."
fi
# <<< guard: env-file-present

# Read the configured instance as DATA. The file is never sourced.
configured() {
    sed -n "s/^[[:space:]]*\(export[[:space:]]\+\)\?$1=//p" "$ENV_FILE" | tail -1 \
        | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/"
}

CONFIGURED_DB="$(configured POSTGRES_DB)"
CONFIGURED_BUCKET="$(configured S3_BUCKET)"
CONFIGURED_INSTANCE="$(configured ALPHA_INSTANCE)"
CONFIGURED_USER="$(configured POSTGRES_USER)"
MIGRATOR_URL="$(configured MIGRATOR_DATABASE_URL)"

# >>> guard: instance-configured
if [ -z "$CONFIGURED_INSTANCE" ] || [ -z "$CONFIGURED_DB" ] || [ -z "$CONFIGURED_BUCKET" ]; then
    refuse "$ENV_FILE names no ALPHA_INSTANCE, POSTGRES_DB or S3_BUCKET." \
           "  ALPHA_INSTANCE: ${CONFIGURED_INSTANCE:-<unset>}" \
           "  POSTGRES_DB   : ${CONFIGURED_DB:-<unset>}" \
           "  S3_BUCKET     : ${CONFIGURED_BUCKET:-<unset>}" \
           "A half-configured environment is not the alpha instance."
fi
# <<< guard: instance-configured

# >>> guard: migrator-url-configured
# The erase switches triggers off and deletes append-only rows, which only the owner role may do. An environment with
# no owner url has nothing to hand the tool but the application's, which the tool refuses after the connection is made;
# say so before any is.
if [[ ! "$MIGRATOR_URL" =~ ^postgresql\+psycopg://[^:@/]+:[^@/]+@[^:@/]+:[0-9]+/[^?]+$ ]]; then
    refuse "[migrator_url_unset] MIGRATOR_DATABASE_URL in $ENV_FILE is unset or is not a postgresql+psycopg:// url." \
           "The erase deletes append-only rows, which only the owner role (POSTGRES_USER) may do; api's DATABASE_URL is" \
           "the application role's and would be refused. Nothing was read and nothing was touched." \
           "See env/alpha.env.example."
fi
# <<< guard: migrator-url-configured

# >>> guard: database-matches
if [ "$DATABASE" != "$CONFIGURED_DB" ]; then
    refuse "the typed database is not the configured alpha database." \
           "  typed     : $DATABASE" \
           "  configured: $CONFIGURED_DB   (POSTGRES_DB in $ENV_FILE)" \
           "Either the environment is stale or this is the wrong instance. Both are" \
           "reasons to stop rather than to guess."
fi
# <<< guard: database-matches

# >>> guard: bucket-matches
if [ "$BUCKET" != "$CONFIGURED_BUCKET" ]; then
    refuse "the typed bucket is not the configured alpha bucket." \
           "  typed     : $BUCKET" \
           "  configured: $CONFIGURED_BUCKET   (S3_BUCKET in $ENV_FILE)" \
           "The database and the bucket are two halves of one instance's state and this" \
           "script will not erase in one against the other's configuration."
fi
# <<< guard: bucket-matches

# >>> guard: compose-file-present
if [ ! -r "$COMPOSE_FILE" ]; then
    refuse "$COMPOSE_FILE is missing." \
           "Every step runs through it; without it this script has no target it is allowed" \
           "to reach."
fi
# <<< guard: compose-file-present

# >>> guard: modules-present
# The module and everything it imports live in scripts/recovery/. The api image does not carry that directory, so the
# four files are mounted from this checkout; a checkout without one of them cannot erase.
MISSING=()
for module in "${MODULES[@]}"; do
    [ -r "$MODULE_DIR/$module.py" ] || MISSING+=("$module.py")
done
if [ "${#MISSING[@]}" -gt 0 ]; then
    refuse "scripts/recovery/ lacks ${MISSING[*]} under $MODULE_DIR." \
           "The tool classifies every table from schema_coverage.py and imports the purge's classification; it will not guess."
fi
# <<< guard: modules-present

MODULE_DIR="$(cd "$MODULE_DIR" && pwd)"

# The two small files of an erase (`<era_id>/plan.json`, `manifest.json`) are written under ERASE_ROOT, as the operator,
# in a directory 0700. A dry run writes nothing and mounts nothing: it creates no directory either.
ERASE_ROOT="$DUMP_ROOT/erasures"
DUMP_MOUNT=()

# >>> guard: dump-dir-writable
# The module writes the plan and the manifest BEFORE the commit that makes them the only record, and it runs as the
# operator's uid. A directory it cannot write would be found out after the lock, so it is found out here.
if [ "$MODE" != plan ]; then
    ( umask 077; mkdir -p "$ERASE_ROOT" ) 2>/dev/null || true
    if [ ! -d "$ERASE_ROOT" ] || [ ! -w "$ERASE_ROOT" ]; then
        refuse "$ERASE_ROOT is not a writable directory of this operator's." \
               "The plan and the manifest of the erase are written there, and they are the only record of what was erased." \
               "Create it (install -d -m 700 $ERASE_ROOT) or point ALPHA_DUMP_ROOT at a directory you can write." \
               "Nothing was read and nothing was touched."
    fi
    ERASE_ROOT="$(cd "$ERASE_ROOT" && pwd)"
    DUMP_MOUNT=(-v "$ERASE_ROOT:/dump")
fi
# <<< guard: dump-dir-writable

compose() { docker compose --env-file "$ENV_FILE" --file "$COMPOSE_FILE" "$@"; }

# THE PYTHON HALF RUNS INSIDE THE `api` IMAGE, from four files mounted read-only. The container runs as the operator's
# uid so that what it writes under /dump is the operator's; stdin is /dev/null so that `docker compose run` cannot
# swallow the answers the operator is about to type (it forwards stdin to the container otherwise).
ERR_FILE="$(mktemp)"
erase_python() {
    local mounts=() module
    for module in "${MODULES[@]}"; do
        mounts+=(-v "$MODULE_DIR/$module.py:/purge/scripts/recovery/$module.py:ro")
    done
    DATABASE_URL="$MIGRATOR_URL" compose run --rm --no-deps -T --user "$(id -u):$(id -g)" \
        -e PYTHONPATH=/app/src:/purge "${mounts[@]}" "${DUMP_MOUNT[@]+"${DUMP_MOUNT[@]}"}" \
        --entrypoint python api -m scripts.recovery.project_erase "$@" </dev/null
}

# Runs one step and leaves its stdout in OUT, its status in STATUS and its stderr in ERR (also shown, after the step).
run_tool() {
    STATUS=0
    OUT="$(erase_python "$@" 2>"$ERR_FILE")" || STATUS=$?
    ERR="$(cat "$ERR_FILE")"
    [ -z "$ERR" ] || printf '%s\n' "$ERR" >&2
}

# The module's paths are the container's (/dump/...); the operator's are the host's.
host_paths() {
    local text="$1"
    printf '%s\n' "${text//\/dump\//"$ERASE_ROOT/"}"
}

# `printf` of a captured block, because it holds the screen the operator reads and the lines the script parses, and
# both must come from the same text.
parse() { printf '%s\n' "$2" | sed -n "s/^$1: //p" | tail -1; }

# The command that finishes an erase, exactly as the operator can run it (real values are shell-quoted; a value not yet
# known is shown as a <placeholder>).
resume_command() {
    local login ref env=""
    if [ -n "$ACTOR" ]; then login="$(printf '%q' "$ACTOR")"; else login="<admin login>"; fi
    if [ -n "$PERMISSION_REF" ]; then ref="$(printf '%q' "$PERMISSION_REF")"; else ref='"<where the owner'"'"'s permission is recorded>"'; fi
    [ -z "${ALPHA_DUMP_ROOT:-}" ] || env="ALPHA_DUMP_ROOT=$(printf '%q' "$ALPHA_DUMP_ROOT") "
    printf '%s%s --database %s --bucket %s --resume %s --actor %s --owner-permission-ref %s' \
        "$env" "$SELF" "$(printf '%q' "$DATABASE")" "$(printf '%q' "$BUCKET")" "$1" "$login" "$ref"
}

# Same discovery as `reset.sh` and `purge-product-data.sh`: a compose file without a worker service has none.
WORKER_DECLARED=no
if grep -q '^  worker:[[:space:]]*$' "$COMPOSE_FILE"; then
    WORKER_DECLARED=yes
fi
WORKER_STOPPED=no
start_worker() {
    [ "$WORKER_STOPPED" = yes ] || return 0
    echo "erase-project.sh: starting the worker service again"
    compose up -d --no-deps worker
    WORKER_STOPPED=no
}
# Whatever happens after the worker was stopped -- a refusal, a failure, success -- it is started again: the stand is
# left as it was found. The exit status is the step's, not the restart's.
cleanup() {
    local status=$?
    trap - ERR
    rm -f "$ERR_FILE"
    if [ "$WORKER_STOPPED" = yes ]; then
        start_worker || printf 'erase-project.sh: !! the worker could not be restarted; run:\n  docker compose --env-file %s --file %s up -d --no-deps worker\n' "$ENV_FILE" "$COMPOSE_FILE" >&2
    fi
    exit "$status"
}
trap cleanup EXIT

echo "erase-project.sh: instance   $CONFIGURED_INSTANCE"
echo "erase-project.sh: database   $DATABASE"
echo "erase-project.sh: bucket     $BUCKET"

# What a stopped step means, said once. `$1` names the step in the sentence. The module's stdout is shown here unless the
# caller already showed it (OUT_SHOWN).
OUT_SHOWN=no
after_step() {
    local what="$1" committed erase_id resume_id
    erase_id="$(parse erase-id "$OUT")"
    committed=no
    if [[ "$erase_id" =~ ^era_[0-9A-HJKMNP-TV-Z]{26}$ ]]; then committed=yes; fi
    [ "$STATUS" -ne 0 ] || return 0
    [ "$OUT_SHOWN" = yes ] || printf '%s\n' "$(host_paths "$OUT")"
    if [ "$committed" = yes ]; then
        # The module prints the erase id right after its commit. 3 would promise "nothing was changed", which is false
        # once the database part is committed, so a stop after it is a failure whatever status the module chose.
        fail "THE DATABASE PART OF THE ERASE IS COMMITTED ($erase_id) but the $what did not finish (status $STATUS)." \
             "Finish it (it completes the objects and the final record, and is safe to repeat):" \
             "  $(resume_command "$erase_id")" \
             "The plan and the manifest are in $ERASE_ROOT/$erase_id/ (keep them with the release record)." \
             "Every existing dump, mirror and copy still holds the project's data."
    fi
    if [ "$STATUS" -eq 3 ]; then
        resume_id="$(printf '%s\n' "$ERR" | sed -n 's/.*--resume \(era_[0-9A-HJKMNP-TV-Z]\{26\}\).*/\1/p' | tail -1)"
        if [ -n "$resume_id" ]; then
            refuse "the $what was refused (reason above): an earlier erase of this project did not finish." \
                   "Finish that one:" "  $(resume_command "$resume_id")"
        fi
        if printf '%s' "$ERR" | grep -q 'could not lock'; then
            if [ "$STOP_WORKER" = yes ]; then
                refuse "the $what was refused (reason above): something besides the worker is still writing." \
                       "Nothing was changed. Stop api and web for the run as well, and start them again afterwards:" \
                       "  docker compose --env-file $ENV_FILE --file $COMPOSE_FILE stop api web" \
                       "  docker compose --env-file $ENV_FILE --file $COMPOSE_FILE up -d --no-deps api web"
            fi
            refuse "the $what was refused (reason above): something is still writing to the tables." \
                   "Nothing was changed. The worker's heartbeat is the usual writer. Stop it for the run and have this" \
                   "script start it again afterwards: run the same command with --stop-worker."
        fi
        refuse "the $what was refused (reason above)." "Nothing was changed."
    fi
    fail "the $what failed (status $STATUS)." \
         "No erase-id was printed, so the database part did not commit (the dry run still finding the project confirms it)." \
         "Is the stack up?"
}

stop_worker_if_asked() {
    if [ "$STOP_WORKER" = yes ] && [ "$WORKER_DECLARED" = yes ]; then
        echo "erase-project.sh: stopping the worker service"
        compose stop worker
        WORKER_STOPPED=yes
    fi
}

# What an operator is told after a finished erase: the file to keep, the two queries that prove the rest state, and the
# copies this script did not and could not reach.
finish_report() {
    local manifest_host manifest_sha project_id erase_id
    manifest_sha="$(parse manifest-sha256 "$OUT")"
    manifest_host="$(parse manifest "$OUT")"
    manifest_host="${manifest_host/\/dump\//"$ERASE_ROOT"/}"
    erase_id="$(printf '%s\n' "$OUT" | sed -n 's/^erase-project: \(prj_[0-9A-HJKMNP-TV-Z]\{26\}\) erased as \(era_[0-9A-HJKMNP-TV-Z]\{26\}\)\.$/\2/p' | tail -1)"
    project_id="$(printf '%s\n' "$OUT" | sed -n 's/^erase-project: \(prj_[0-9A-HJKMNP-TV-Z]\{26\}\) erased as \(era_[0-9A-HJKMNP-TV-Z]\{26\}\)\.$/\1/p' | tail -1)"
    # >>> guard: manifest-verified
    # The manifest file is byte-deterministic: `sha256sum manifest.json` IS the digest both journal events carry. A file
    # that hashes to something else (or is not there) is not the record of this erase, and the operator is about to be
    # told to keep it as one.
    local actual=""
    if [[ "$manifest_sha" =~ ^[0-9a-f]{64}$ ]] && [ -r "$manifest_host" ]; then
        actual="$(sha256sum "$manifest_host" | cut -d' ' -f1)"
    fi
    if [ -z "$actual" ] || [ "$actual" != "$manifest_sha" ]; then
        fail "THE ERASE COMPLETED but the manifest on disk is not the one the database holds." \
             "  file        : ${manifest_host:-<none>}" \
             "  sha256(file): ${actual:-<unreadable>}" \
             "  journalled  : ${manifest_sha:-<none>}" \
             "Do not discard anything. The digest above is in both journal events (erasure.requested, erasure.completed)."
    fi
    # <<< guard: manifest-verified
    echo
    echo "erase-project.sh: done. $project_id was erased as $erase_id."
    echo "erase-project.sh: keep $ERASE_ROOT/$erase_id/plan.json and manifest.json WITH THE RELEASE RECORD:"
    echo "erase-project.sh: the database holds only their digests, and the manifest is the only proof that a known"
    echo "erase-project.sh: document was erased. manifest-sha256 $manifest_sha (verified against the file)."
    echo "erase-project.sh: NO DUMP WAS TAKEN. Every existing dump, mirror and copy of this host still holds the project:"
    echo "erase-project.sh: infra/deploy/dumps/, the copy directory, the copy fetched for an R-93 restore test, the VPS"
    echo "erase-project.sh: provider's snapshots. Remove or age them by hand and record that in the release record."
    echo "erase-project.sh: the rest state (ADR-0022 section 3). Run these; the first two print 0 and the third prints 1:"
    echo "  DC=\"docker compose --env-file $ENV_FILE --file $COMPOSE_FILE\""
    echo "  \$DC exec -T postgres psql -U $CONFIGURED_USER -d $DATABASE -Atc \"select count(*) from blob where state = 'erasure_pending'\""
    echo "  \$DC exec -T postgres psql -U $CONFIGURED_USER -d $DATABASE -Atc \"select count(*) from project where project_uid = '$project_id'\""
    echo "  \$DC exec -T postgres psql -U $CONFIGURED_USER -d $DATABASE -Atc \"select count(*) from audit_event where event_type = 'erasure.completed' and aggregate_id = '$erase_id'\""
}

# --- --resume: the database part is committed, the objects or the final record are not --------------------------
if [ "$MODE" = resume ]; then
    echo "erase-project.sh: resuming $RESUME (objects, then the final record; nothing is deleted that the erase did not already claim)"
    stop_worker_if_asked
    run_tool --database "$DATABASE" --bucket "$BUCKET" --resume "$RESUME" --actor "$ACTOR" \
        --owner-permission-ref "$PERMISSION_REF" --dump-dir /dump
    after_step "resume"
    printf '%s\n' "$(host_paths "$OUT")"
    if [ -n "$(parse manifest-sha256 "$OUT")" ]; then
        finish_report
    fi
    exit 0
fi

# --- the plan: read-only, inside the api image ------------------------------------------------------------------
run_tool --database "$DATABASE" --bucket "$BUCKET" --project "$PROJECT"
printf '%s\n' "$OUT"
OUT_SHOWN=yes
PLAN_SHA="$(parse plan-sha256 "$OUT")"
# >>> guard: preflight-ran
# A plan that refused or could not read does not get to continue, and a plan with no digest is not a plan an operator
# can approve (`reset.sh` `rehearsal-counted`: a screen with no numbers is the untruth `D-24` is about). A finished
# erase answers "nothing to do" with no plan, and that is a success, said once.
if [ "$STATUS" -ne 0 ]; then
    after_step "plan"
fi
if ! printf '%s' "$PLAN_SHA" | grep -Eq '^[0-9a-f]{64}$'; then
    if printf '%s\n' "$OUT" | grep -q 'nothing to do'; then
        echo
        echo "erase-project.sh: nothing to do. Nothing was changed."
        exit 0
    fi
    fail "the plan printed no digest." "Nothing was changed."
fi
# <<< guard: preflight-ran
OUT_SHOWN=no

if [ "$MODE" = plan ]; then
    echo
    echo "erase-project.sh: dry run. NOTHING ABOVE WAS CHANGED. To erase this project, show the plan to the owner, get the"
    echo "erase-project.sh: permission in writing (R-146aj), then run the same command with"
    echo "erase-project.sh:   --apply --actor <admin login> --reason <code> --owner-permission-ref \"<where it is recorded>\" \\"
    echo "erase-project.sh:   --plan-sha256 $PLAN_SHA"
    echo "erase-project.sh: NO DUMP WILL BE TAKEN (it would keep the erased data); take care of the copies yourself first."
    exit 0
fi

# --- --apply: the plan above must be the plan that was approved, and the operator must retype what it is -------------
# >>> guard: plan-approved
# The digest on the command line is the plan someone READ. The project may have changed since (a document uploaded, a
# run finished): the plan above is then not the one that was approved, and the answer is to read the new one, not to
# erase on the strength of the old.
if [ "$PLAN_SHA" != "$PLAN_SHA_GIVEN" ]; then
    refuse "the plan the project has now is not the plan you approved." \
           "  approved (--plan-sha256): $PLAN_SHA_GIVEN" \
           "  plan above              : $PLAN_SHA" \
           "Read the plan above, get the owner's permission for it, and run again with its digest. Nothing was changed."
fi
# <<< guard: plan-approved

echo
echo "erase-project.sh: THIS ERASES THE PROJECT ABOVE. It cannot be undone, and NO DUMP is taken first."
echo "erase-project.sh: actor $ACTOR, reason $REASON, owner's permission: $PERMISSION_REF"
printf 'erase-project.sh: retype the project id to go on: '
IFS= read -r TYPED_PROJECT || TYPED_PROJECT=""
printf 'erase-project.sh: retype the plan digest to go on: '
IFS= read -r TYPED_DIGEST || TYPED_DIGEST=""
echo
# >>> guard: retyped-confirmation
# Both come from the keyboard, not from the command line: a value that was pasted into the command is a value nobody has
# looked at. An end of input (a script feeding the apply, a closed terminal) is no answer.
if [ "$TYPED_PROJECT" != "$PROJECT" ] || [ "$TYPED_DIGEST" != "$PLAN_SHA" ]; then
    refuse "what was retyped is not the project and the plan above." \
           "  project id : ${TYPED_PROJECT:-<nothing>}" \
           "  plan digest: ${TYPED_DIGEST:-<nothing>}" \
           "Nothing was changed."
fi
# <<< guard: retyped-confirmation

# --- the erase ---------------------------------------------------------------------------------------------------
stop_worker_if_asked
echo "erase-project.sh: erasing (one transaction, then the objects, then the final record)"
run_tool --database "$DATABASE" --bucket "$BUCKET" --project "$PROJECT" --apply --plan-sha256 "$PLAN_SHA_GIVEN" \
    --actor "$ACTOR" --reason "$REASON" --owner-permission-ref "$PERMISSION_REF" --dump-dir /dump
after_step "erase"
printf '%s\n' "$(host_paths "$OUT")"
if [ -n "$(parse manifest-sha256 "$OUT")" ]; then
    finish_report
fi
exit 0
