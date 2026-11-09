#!/usr/bin/env bash
# `D-511` -- make the decision memory FORGET cases: the content of a case (text, evidence, norm references, crops, the expert's comment) and
# every crop Blob only it references. What stays is the case, its decisions (verdict, severity, author, time -- no words of the expert) and one
# tombstone per case.
#
#   infra/deploy/memory-forget.sh --database <name> --bucket <name> --origin-project prj_<ULID>             # the dry run
#   infra/deploy/memory-forget.sh --database <name> --bucket <name> --case dmc_<ULID> [--case dmc_<ULID> ...]
#   infra/deploy/memory-forget.sh --database <name> --bucket <name> --all
#   infra/deploy/memory-forget.sh --database <name> --bucket <name> <the same selector> --apply \
#         --actor <admin login> --reason <capture_defect|wrong_decision|client_request|test_data|other> \
#         --owner-permission-ref "<where the owner's permission is recorded>" --plan-sha256 <the dry run's digest> [--stop-services]
#   infra/deploy/memory-forget.sh --database <name> --bucket <name> --resume era_<ULID> \
#         --actor <admin login> --owner-permission-ref "<...>" [--stop-services]
#
# THE DESIGN IS `DECISION-MEMORY-01` SECTION 4.5 AND `scripts/recovery/memory_forget.py`. This file is the operator's door to that module and
# nothing more, in the shape of `erase-project.sh`: it holds the guards that can be checked before a connection, runs the module inside the
# `api` image from the files it imports mounted read-only, makes the operator retype what is about to be forgotten, and says what to do when
# something stops half way. The scope, the plan, the transaction and the four phases are the module's, and so are its refusals (this file
# shows them and adds none of its own after a connection); read its header for them.
#
# WHAT IS THE SAME AS `erase-project.sh`, ON PURPOSE:
#
#   * NO `pg_dump` AND NO OBJECT MIRROR IS TAKEN FIRST. A dump would keep the very content the operator was asked to remove. The script writes
#     the two small files the module writes (`plan.json` and `manifest.json`, under `infra/deploy/dumps/forgets/<era_id>/`) and says in its
#     closing text that EVERY EXISTING DUMP, MIRROR AND COPY STILL HOLDS THE CONTENT (runbook section 21).
#   * IT IS A DRY RUN UNLESS TOLD OTHERWISE, and `--apply` needs the selector, the actor, the reason, the owner's permission reference and the
#     digest of the plan the operator read -- and then makes the operator RETYPE the number of cases and the digest.
#   * THE CONTAINER RUNS AS THE OPERATOR'S UID with a writable mount for the two files; IT HASHES `manifest.json` on the host afterwards and
#     compares it with the digest the module printed (and wrote into both journal events).
#   * THE PYTHON HALF CONNECTS AS THE OWNER (`PROD-04-DB-ROLES-01`): the one-off container gets `MIGRATOR_DATABASE_URL` as `DATABASE_URL`
#     through the environment of the `docker compose` process, and no `PG*` variable.
#   * THE TARGET IS ALWAYS THIS STACK, through `docker compose -f compose.server.yml` and the typed names. The stack must be UP.
#
# WHAT IS NEW: `api` AND `worker` SHOULD NOT BE RUNNING FOR AN APPLY OR A RESUME (`D-497` item 2). The module takes its locks in another order
# than a capture does, so a capture or a withdraw/restore that arrives during the run can make it deadlock or roll back (it fails safe: nothing
# is changed, and the run is repeated). `--stop-services` stops the ones of those two that are running, and starts exactly those again
# afterwards, whatever the result. The script does not check the state of the stack on its own: the module's own `could not lock` refusal is
# the signal, and the script then says to use the option.
#
# EXIT CODES: 0 done or nothing to do; 2 usage; 3 REFUSED (nothing was changed); 4 FAILED. A step that stops AFTER the commit exits 4 -- never
# 3, because 3 promises that nothing was changed -- and prints the forget id and the exact `--resume` command that finishes it.
#
# GUARDS ARE DELIMITED BY MARKERS -- `# >>> guard: <name>` / `# <<< guard: <name>`.
# `tests/integration/composition/test_memory_forget_script.py` reads those markers, deletes ONE guard block from a copy of this file and shows
# the copy no longer refuses. A guard that cannot be shown to fail is not evidence. Do not remove a marker without removing its test.

set -Eeuo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$HERE/compose.server.yml"
ENV_FILE="${ALPHA_ENV_FILE:-$HERE/env/alpha.env}"
DUMP_ROOT="${ALPHA_DUMP_ROOT:-$HERE/dumps}"
MODULE_DIR="${ALPHA_MEMORY_MODULE_DIR:-$HERE/../../scripts/recovery}"
# The files the module needs and nothing else: `memory_forget` imports `project_erase`, `product_purge`, `blob_reference_audit` and
# `schema_coverage` (tests/integration/composition/test_memory_forget_script.py holds this list to the module's own imports).
MODULES=(memory_forget project_erase product_purge schema_coverage blob_reference_audit)
# The services that write to the memory while it is running; a forget is safest with both stopped.
WRITERS=(api worker)

DATABASE=""
BUCKET=""
CASES=()
ORIGIN_PROJECT=""
ALL=no
DRY_RUN=no
APPLY=no
RESUME=""
ACTOR=""
REASON=""
PERMISSION_REF=""
PLAN_SHA_GIVEN=""
STOP_SERVICES=no

SELF="$0"

refuse() {
    printf 'memory-forget.sh: REFUSED: %s\n' "$1" >&2
    shift
    [ "$#" -eq 0 ] || printf '  %s\n' "$@" >&2
    exit 3
}

fail() {
    printf 'memory-forget.sh: FAILED: %s\n' "$1" >&2
    shift
    [ "$#" -eq 0 ] || printf '  %s\n' "$@" >&2
    exit 4
}

usage() {
    cat >&2 <<'USAGE'
usage: memory-forget.sh --database <name> --bucket <name> <selector> [--dry-run]
       memory-forget.sh --database <name> --bucket <name> <selector> --apply
                        --actor <admin login> --reason <code> --owner-permission-ref "<text>"
                        --plan-sha256 <digest> [--stop-services]
       memory-forget.sh --database <name> --bucket <name> --resume era_<ULID>
                        --actor <admin login> --owner-permission-ref "<text>" [--stop-services]

  <selector>                   exactly one of:  --case dmc_<ULID> (repeat for several)  |  --origin-project prj_<ULID>  |  --all
  --database <name>            the database this acts on. Must equal the configured one.
  --bucket <name>              the bucket this acts on. Must equal the configured one.
  --dry-run                    the default: print the plan and its sha256. Changes nothing.
  --apply                      forget. Needs everything below, and the operator retypes the number of cases and the digest.
  --resume era_<ULID>          finish a forget that committed and did not complete (the forget id was printed).
  --actor <login>              the administrator on whose account the forget is journalled.
  --reason <code>              one of: capture_defect, wrong_decision, client_request, test_data, other.
  --owner-permission-ref <t>   one line, at most 200 characters: where the OWNER's permission to forget these cases is recorded. An operator
                               never forgets without it (R-146aj). It is recorded as given and never verified.
  --plan-sha256 <digest>       the plan-sha256 the dry run printed.
  --stop-services              for the apply or the resume: stop `api` and `worker` (those of them that are running) and start them again
                               afterwards. For a refusal "could not lock the tables": a capture or a withdraw is the usual writer.
  --env-file <path>            default: infra/deploy/env/alpha.env

NO DUMP IS TAKEN, because a dump would keep the forgotten content. Every existing dump, mirror and copy still holds it.
USAGE
    exit 2
}

# `exit 4` for anything a command did not handle itself: a refusal is 3 and is spelled out.
on_error() {
    printf 'memory-forget.sh: FAILED: a step exited non-zero (line %s).\n' "$1" >&2
    exit 4
}
trap 'on_error $LINENO' ERR

# >>> guard: known-options
# An unrecognised option is refused rather than ignored, and so is one that has lost its value: `--reaason` silently ignored would run a
# forget the operator believed was reasoned, and a trailing `--case` would swallow the next word.
while [ "$#" -gt 0 ]; do
    case "$1" in
        --database|--bucket|--case|--origin-project|--resume|--actor|--reason|--owner-permission-ref|--plan-sha256|--env-file)
            [ "$#" -ge 2 ] || refuse "$1 needs a value." "Nothing was read and nothing was touched. Run --help." ;;
    esac
    case "$1" in
        --database) DATABASE="$2"; shift 2 ;;
        --bucket) BUCKET="$2"; shift 2 ;;
        --case) CASES+=("$2"); shift 2 ;;
        --origin-project) ORIGIN_PROJECT="$2"; shift 2 ;;
        --resume) RESUME="$2"; shift 2 ;;
        --actor) ACTOR="$2"; shift 2 ;;
        --reason) REASON="$2"; shift 2 ;;
        --owner-permission-ref) PERMISSION_REF="$2"; shift 2 ;;
        --plan-sha256) PLAN_SHA_GIVEN="$2"; shift 2 ;;
        --env-file) ENV_FILE="$2"; shift 2 ;;
        --all) ALL=yes; shift ;;
        --dry-run) DRY_RUN=yes; shift ;;
        --apply) APPLY=yes; shift ;;
        --stop-services) STOP_SERVICES=yes; shift ;;
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
           "They are different things to do to one selection. Choose one (no option at all is the dry run)."
fi
# <<< guard: one-mode

MODE=plan
[ "$APPLY" = yes ] && MODE=apply
[ -n "$RESUME" ] && MODE=resume

# >>> guard: stop-services-needs-a-write-mode
# A dry run changes nothing, so there is nothing to stop the services for; accepting the option and ignoring it would tell the operator they
# were stopped when they were not.
if [ "$STOP_SERVICES" = yes ] && [ "$MODE" = plan ]; then
    refuse "--stop-services belongs to --apply or --resume." \
           "A dry run changes nothing and does not stop anything. Nothing was read and nothing was touched."
fi
# <<< guard: stop-services-needs-a-write-mode

# >>> guard: options-match-the-mode
# An option that belongs to another mode is refused, not ignored: `--plan-sha256`, `--reason` and the rest of an apply given to a dry run would
# be read by the operator as a forget that was asked for, and a dry run is a different thing.
if [ "$MODE" = plan ] && { [ -n "$ACTOR" ] || [ -n "$REASON" ] || [ -n "$PERMISSION_REF" ] || [ -n "$PLAN_SHA_GIVEN" ]; }; then
    refuse "--actor, --reason, --owner-permission-ref and --plan-sha256 belong to --apply (or --resume), and no --apply was given." \
           "As given this is a dry run, which changes nothing. Add --apply to forget, or drop them. Nothing was read and nothing was touched."
fi
if [ "$MODE" = resume ] && { [ -n "$REASON" ] || [ -n "$PLAN_SHA_GIVEN" ]; }; then
    refuse "--reason and --plan-sha256 belong to --apply; a --resume finishes a forget that was already approved." \
           "Nothing was read and nothing was touched."
fi
# <<< guard: options-match-the-mode

# >>> guard: names-required
if [ -z "$DATABASE" ] || [ -z "$BUCKET" ]; then
    refuse "--database and --bucket are both required, even for the dry run." \
           "Typing the target is the point: it is what makes a forget in the wrong instance" \
           "a thing you have to do on purpose."
fi
# <<< guard: names-required

# >>> guard: one-selector
# Which cases is the whole question, and an omission must not mean "all of them". A resume names a forget (and through it the cases): a
# selector with it is a contradiction.
chosen=0
[ "${#CASES[@]}" -gt 0 ] && chosen=$((chosen + 1))
[ -n "$ORIGIN_PROJECT" ] && chosen=$((chosen + 1))
[ "$ALL" = yes ] && chosen=$((chosen + 1))
if [ "$MODE" = resume ]; then
    if [ "$chosen" -gt 0 ]; then
        refuse "--case, --origin-project and --all do not go with --resume." \
               "The forget id names the forget (and through it the cases). Nothing was read and nothing was touched."
    fi
elif [ "$chosen" -ne 1 ]; then
    refuse "name exactly one of --case (once or more), --origin-project or --all: which cases to forget." \
           "Nothing was read and nothing was touched."
fi
# <<< guard: one-selector

# >>> guard: selector-identity-shape
# A case or a project is addressed by its identity, never by its name or description: a name can carry personal data into a command line, a
# shell history and a journal.
for given in "${CASES[@]+"${CASES[@]}"}"; do
    if [[ ! "$given" =~ ^dmc_[0-9A-HJKMNP-TV-Z]{26}$ ]]; then
        refuse "--case must be a case identity (dmc_ and 26 characters), never a description." \
               "  given: $given" "Nothing was read and nothing was touched."
    fi
done
if [ -n "$ORIGIN_PROJECT" ] && [[ ! "$ORIGIN_PROJECT" =~ ^prj_[0-9A-HJKMNP-TV-Z]{26}$ ]]; then
    refuse "--origin-project must be a project identity (prj_ and 26 characters), never a name." \
           "  given: $ORIGIN_PROJECT" "Nothing was read and nothing was touched."
fi
# <<< guard: selector-identity-shape

# >>> guard: forget-identity-shape
if [ "$MODE" = resume ] && [[ ! "$RESUME" =~ ^era_[0-9A-HJKMNP-TV-Z]{26}$ ]]; then
    refuse "--resume must be a forget identity (era_ and 26 characters)." \
           "  given: $RESUME" \
           "It is printed on the line 'forget-id:' of the run that stopped. Nothing was read and nothing was touched."
fi
# <<< guard: forget-identity-shape

# >>> guard: actor-required
# The forget is journalled on an administrator's account. The module checks that the account exists and holds `admin`; here the value must at
# least be one word that is not an option, so that an empty string, a sentence or a swallowed `--apply` is refused before a connection.
if [ "$MODE" != plan ]; then
    if [ -z "$ACTOR" ] || [[ "$ACTOR" =~ [[:space:][:cntrl:]] ]] || [ "${#ACTOR}" -gt 254 ] || [[ "$ACTOR" == -* ]]; then
        refuse "--actor must be the login of an administrator (one word)." \
               "  given: ${ACTOR:-<none>}" \
               "Nothing was read and nothing was touched."
    fi
fi
# <<< guard: actor-required

# >>> guard: reason-closed-list
# Free text is refused: it would put personal data into an append-only table. The list is the module's (`STATUS_REASON_CODES`).
if [ "$MODE" = apply ]; then
    case "$REASON" in
        capture_defect|wrong_decision|client_request|test_data|other) ;;
        *) refuse "--reason must be one of: capture_defect, wrong_decision, client_request, test_data, other." \
                  "  given: ${REASON:-<none>}" \
                  "Free text is refused because it would be written into the append-only journal. Nothing was touched." ;;
    esac
fi
# <<< guard: reason-closed-list

# >>> guard: owner-permission-ref
# `R-146aj`: an operator never removes the memory's content without the owner's permission. Nothing here can verify a permission; what the
# script can do is refuse to run without a statement of where it is recorded, so that the journal carries it.
if [ "$MODE" != plan ]; then
    ref="$PERMISSION_REF"
    ref="${ref#"${ref%%[![:space:]]*}"}"
    ref="${ref%"${ref##*[![:space:]]}"}"
    if [ -z "$ref" ] || [ "${#ref}" -gt 200 ] || [[ "$PERMISSION_REF" =~ [[:cntrl:]] ]]; then
        refuse "--owner-permission-ref is required: one line of at most 200 characters saying where the owner's" \
               "permission to forget these cases is recorded (R-146aj: never without it)." \
               "It is recorded as given and never verified. Nothing was read and nothing was touched."
    fi
    PERMISSION_REF="$ref"
fi
# <<< guard: owner-permission-ref

# >>> guard: plan-digest-shape
# The digest of the plan the operator READ. Without one the apply would be a forget of whatever the selection is now.
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
# The forget deletes rows the application role cannot delete (the guard of migration 0061 admits a delete only from the owner's session). An
# environment with no owner url has nothing to hand the tool but the application's, which the tool refuses after the connection is made; say
# so before any is.
if [[ ! "$MIGRATOR_URL" =~ ^postgresql\+psycopg://[^:@/]+:[^@/]+@[^:@/]+:[0-9]+/[^?]+$ ]]; then
    refuse "[migrator_url_unset] MIGRATOR_DATABASE_URL in $ENV_FILE is unset or is not a postgresql+psycopg:// url." \
           "The forget deletes rows only the owner role (POSTGRES_USER) may delete; api's DATABASE_URL is" \
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
           "script will not forget in one against the other's configuration."
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
# The module and everything it imports live in scripts/recovery/. The api image does not carry that directory, so the five files are mounted
# from this checkout; a checkout without one of them cannot forget.
MISSING=()
for module in "${MODULES[@]}"; do
    [ -r "$MODULE_DIR/$module.py" ] || MISSING+=("$module.py")
done
if [ "${#MISSING[@]}" -gt 0 ]; then
    refuse "scripts/recovery/ lacks ${MISSING[*]} under $MODULE_DIR." \
           "The tool classifies the Blob references from blob_reference_audit.py and imports the erase's helpers; it will not guess."
fi
# <<< guard: modules-present

MODULE_DIR="$(cd "$MODULE_DIR" && pwd)"

# The two small files of a forget (`<era_id>/plan.json`, `manifest.json`) are written under FORGET_ROOT, as the operator, in a directory 0700. A
# dry run writes nothing and mounts nothing: it creates no directory either.
FORGET_ROOT="$DUMP_ROOT/forgets"
DUMP_MOUNT=()

# >>> guard: dump-dir-writable
# The module writes the plan and the manifest BEFORE the commit that makes them the only record, and it runs as the operator's uid. A directory
# it cannot write would be found out after the lock, so it is found out here.
if [ "$MODE" != plan ]; then
    ( umask 077; mkdir -p "$FORGET_ROOT" ) 2>/dev/null || true
    if [ ! -d "$FORGET_ROOT" ] || [ ! -w "$FORGET_ROOT" ]; then
        refuse "$FORGET_ROOT is not a writable directory of this operator's." \
               "The plan and the manifest of the forget are written there, and they are the only record of what was forgotten." \
               "Create it (install -d -m 700 $FORGET_ROOT) or point ALPHA_DUMP_ROOT at a directory you can write." \
               "Nothing was read and nothing was touched."
    fi
    FORGET_ROOT="$(cd "$FORGET_ROOT" && pwd)"
    DUMP_MOUNT=(-v "$FORGET_ROOT:/dump")
fi
# <<< guard: dump-dir-writable

compose() { docker compose --env-file "$ENV_FILE" --file "$COMPOSE_FILE" "$@"; }

# THE PYTHON HALF RUNS INSIDE THE `api` IMAGE, from five files mounted read-only. The container runs as the operator's uid so that what it
# writes under /dump is the operator's; stdin is /dev/null so that `docker compose run` cannot swallow the answers the operator is about to
# type (it forwards stdin to the container otherwise).
ERR_FILE="$(mktemp)"
forget_python() {
    local mounts=() module
    for module in "${MODULES[@]}"; do
        mounts+=(-v "$MODULE_DIR/$module.py:/purge/scripts/recovery/$module.py:ro")
    done
    DATABASE_URL="$MIGRATOR_URL" compose run --rm --no-deps -T --user "$(id -u):$(id -g)" \
        -e PYTHONPATH=/app/src:/purge "${mounts[@]}" "${DUMP_MOUNT[@]+"${DUMP_MOUNT[@]}"}" \
        --entrypoint python api -m scripts.recovery.memory_forget "$@" </dev/null
}

# Runs one step and leaves its stdout in OUT, its status in STATUS and its stderr in ERR (also shown, after the step).
run_tool() {
    STATUS=0
    OUT="$(forget_python "$@" 2>"$ERR_FILE")" || STATUS=$?
    ERR="$(cat "$ERR_FILE")"
    [ -z "$ERR" ] || printf '%s\n' "$ERR" >&2
}

# The module's paths are the container's (/dump/...); the operator's are the host's.
host_paths() {
    local text="$1"
    printf '%s\n' "${text//\/dump\//"$FORGET_ROOT/"}"
}

# `printf` of a captured block, because it holds the screen the operator reads and the lines the script parses, and both must come from the
# same text.
parse() { printf '%s\n' "$2" | sed -n "s/^$1: //p" | tail -1; }

# The command that finishes a forget, exactly as the operator can run it (real values are shell-quoted; a value not yet known is shown as a
# <placeholder>).
resume_command() {
    local login ref env=""
    if [ -n "$ACTOR" ]; then login="$(printf '%q' "$ACTOR")"; else login="<admin login>"; fi
    if [ -n "$PERMISSION_REF" ]; then ref="$(printf '%q' "$PERMISSION_REF")"; else ref='"<where the owner'"'"'s permission is recorded>"'; fi
    [ -z "${ALPHA_DUMP_ROOT:-}" ] || env="ALPHA_DUMP_ROOT=$(printf '%q' "$ALPHA_DUMP_ROOT") "
    printf '%s%s --database %s --bucket %s --resume %s --actor %s --owner-permission-ref %s' \
        "$env" "$SELF" "$(printf '%q' "$DATABASE")" "$(printf '%q' "$BUCKET")" "$1" "$login" "$ref"
}

# `api` and `worker`: stopped for the write and started again afterwards, those that were running and no others, so that the stand is left as
# it was found (a service the operator had stopped on purpose stays stopped). The list comes from `docker compose ps`, not from the compose
# file: a service that is declared and down is not ours to start.
STOPPED=()
start_services() {
    [ "${#STOPPED[@]}" -gt 0 ] || return 0
    echo "memory-forget.sh: starting ${STOPPED[*]} again"
    compose up -d --no-deps "${STOPPED[@]}"
    STOPPED=()
}
# Whatever happens after the services were stopped -- a refusal, a failure, success -- they are started again. The exit status is the step's,
# not the restart's.
cleanup() {
    local status=$?
    trap - ERR
    rm -f "$ERR_FILE"
    if [ "${#STOPPED[@]}" -gt 0 ]; then
        start_services || printf 'memory-forget.sh: !! %s could not be restarted; run:\n  docker compose --env-file %s --file %s up -d --no-deps %s\n' \
            "${STOPPED[*]}" "$ENV_FILE" "$COMPOSE_FILE" "${STOPPED[*]}" >&2
    fi
    exit "$status"
}
trap cleanup EXIT

stop_services_if_asked() {
    [ "$STOP_SERVICES" = yes ] || return 0
    local running writer
    if ! running="$(compose ps --status running --services)"; then
        fail "could not list the running services of the stack." "Nothing was changed. Is the stack up?"
    fi
    local to_stop=()
    for writer in "${WRITERS[@]}"; do
        if printf '%s\n' "$running" | grep -qx "$writer"; then to_stop+=("$writer"); fi
    done
    if [ "${#to_stop[@]}" -gt 0 ]; then
        echo "memory-forget.sh: stopping ${to_stop[*]}"
        compose stop "${to_stop[@]}"
        STOPPED=("${to_stop[@]}")
    else
        echo "memory-forget.sh: neither api nor worker is running; nothing to stop"
    fi
}

echo "memory-forget.sh: instance   $CONFIGURED_INSTANCE"
echo "memory-forget.sh: database   $DATABASE"
echo "memory-forget.sh: bucket     $BUCKET"

# What a stopped step means, said once. `$1` names the step in the sentence. The module's stdout is shown here unless the caller already showed
# it (OUT_SHOWN).
OUT_SHOWN=no
after_step() {
    local what="$1" committed forget_id
    forget_id="$(parse forget-id "$OUT")"
    committed=no
    if [[ "$forget_id" =~ ^era_[0-9A-HJKMNP-TV-Z]{26}$ ]]; then committed=yes; fi
    [ "$STATUS" -ne 0 ] || return 0
    [ "$OUT_SHOWN" = yes ] || printf '%s\n' "$(host_paths "$OUT")"
    if [ "$committed" = yes ]; then
        # The module prints the forget id right after its commit. 3 would promise "nothing was changed", which is false once the database part
        # is committed, so a stop after it is a failure whatever status the module chose.
        fail "THE DATABASE PART OF THE FORGET IS COMMITTED ($forget_id) but the $what did not finish (status $STATUS)." \
             "Finish it (it completes the objects and the final record, and is safe to repeat):" \
             "  $(resume_command "$forget_id")" \
             "The plan and the manifest are in $FORGET_ROOT/$forget_id/ (keep them with the release record)." \
             "Every existing dump, mirror and copy still holds the content."
    fi
    if [ "$STATUS" -eq 3 ]; then
        if printf '%s' "$ERR" | grep -q 'erasure_pending'; then
            refuse "the $what was refused (reason above): an earlier erase or forget committed and did not finish." \
                   "Nothing was changed. Finish that one first: its id is in the event that began it (erasure.requested for a" \
                   "project erase, memory.forget_requested for a forget); runbook section 21, 'When it stops'."
        fi
        if printf '%s' "$ERR" | grep -q 'could not lock'; then
            if [ "$STOP_SERVICES" = yes ]; then
                refuse "the $what was refused (reason above): something besides api and worker is still writing." \
                       "Nothing was changed. The worker and api were stopped for this run; look for another writer (a second operator session, a restore)."
            fi
            refuse "the $what was refused (reason above): something is still writing to the memory's tables." \
                   "Nothing was changed. A capture, a withdraw or a restore from api or the worker is the usual writer." \
                   "Stop them for the run and have this script start them again afterwards: run the same command with --stop-services."
        fi
        refuse "the $what was refused (reason above)." "Nothing was changed."
    fi
    fail "the $what failed (status $STATUS)." \
         "No forget-id was printed, so the database part did not commit (the dry run still finding the cases confirms it)." \
         "Is the stack up?"
}

# What an operator is told after a finished forget: the file to keep, the queries that prove the rest state, and the copies this script did
# not and could not reach.
finish_report() {
    local manifest_host manifest_sha forget_id
    manifest_sha="$(parse manifest-sha256 "$OUT")"
    manifest_host="$(parse manifest "$OUT")"
    manifest_host="${manifest_host/\/dump\//"$FORGET_ROOT"/}"
    forget_id="$(printf '%s\n' "$OUT" | sed -n 's/^memory-forget: [0-9]* case(s) forgotten as \(era_[0-9A-HJKMNP-TV-Z]\{26\}\)\.$/\1/p' | tail -1)"
    # >>> guard: manifest-verified
    # The manifest file is byte-deterministic: `sha256sum manifest.json` IS the digest both journal events carry. A file that hashes to something
    # else (or is not there) is not the record of this forget, and the operator is about to be told to keep it as one.
    local actual=""
    if [[ "$manifest_sha" =~ ^[0-9a-f]{64}$ ]] && [ -r "$manifest_host" ]; then
        actual="$(sha256sum "$manifest_host" | cut -d' ' -f1)"
    fi
    if [ -z "$actual" ] || [ "$actual" != "$manifest_sha" ]; then
        fail "THE FORGET COMPLETED but the manifest on disk is not the one the database holds." \
             "  file        : ${manifest_host:-<none>}" \
             "  sha256(file): ${actual:-<unreadable>}" \
             "  journalled  : ${manifest_sha:-<none>}" \
             "Do not discard anything. The digest above is in both journal events (memory.forget_requested, memory.forget_completed)."
    fi
    # <<< guard: manifest-verified
    echo
    echo "memory-forget.sh: done${forget_id:+. The forget is $forget_id}."
    echo "memory-forget.sh: keep $FORGET_ROOT/${forget_id:-<forget id>}/plan.json and manifest.json WITH THE RELEASE RECORD:"
    echo "memory-forget.sh: the database holds only their digests, and the manifest is the only proof that a known"
    echo "memory-forget.sh: crop was forgotten. manifest-sha256 $manifest_sha (verified against the file)."
    echo "memory-forget.sh: NO DUMP WAS TAKEN. Every existing dump, mirror and copy of this host still holds the content:"
    echo "memory-forget.sh: infra/deploy/dumps/, the copy directory, the copy fetched for an R-93 restore test, the VPS"
    echo "memory-forget.sh: provider's snapshots, and any training export already made. Remove or age them by hand and record that."
    echo "memory-forget.sh: the rest state. Run these; the first two print 0 and the third prints 1:"
    echo "  DC=\"docker compose --env-file $ENV_FILE --file $COMPOSE_FILE\""
    echo "  \$DC exec -T postgres psql -U $CONFIGURED_USER -d $DATABASE -Atc \"select count(*) from blob where state = 'erasure_pending'\""
    echo "  \$DC exec -T postgres psql -U $CONFIGURED_USER -d $DATABASE -Atc \"select count(*) from decision_memory_content c where exists (select 1 from decision_memory_status_event e where e.case_id = c.case_id and e.kind = 'forget')\""
    echo "  \$DC exec -T postgres psql -U $CONFIGURED_USER -d $DATABASE -Atc \"select count(*) from audit_event where event_type = 'memory.forget_completed' and aggregate_id = '${forget_id:-<forget id>}'\""
}

# --- --resume: the database part is committed, the objects or the final record are not --------------------------
if [ "$MODE" = resume ]; then
    echo "memory-forget.sh: resuming $RESUME (objects, then the final record; nothing is deleted that the forget did not already claim)"
    stop_services_if_asked
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
SELECTOR=()
if [ "${#CASES[@]}" -gt 0 ]; then
    for given in "${CASES[@]}"; do SELECTOR+=(--case "$given"); done
elif [ -n "$ORIGIN_PROJECT" ]; then
    SELECTOR=(--origin-project "$ORIGIN_PROJECT")
else
    SELECTOR=(--all)
fi
run_tool --database "$DATABASE" --bucket "$BUCKET" "${SELECTOR[@]}"
printf '%s\n' "$OUT"
OUT_SHOWN=yes
PLAN_SHA="$(parse plan-sha256 "$OUT")"
PLAN_CASES="$(parse cases "$OUT")"
# >>> guard: preflight-ran
# A plan that refused or could not read does not get to continue, and a plan with no digest or no case count is not a plan an operator can
# approve (`reset.sh` `rehearsal-counted`: a screen with no numbers is the untruth `D-24` is about). A selection with nothing left to forget
# answers "nothing to do", and that is a success, said once.
if [ "$STATUS" -ne 0 ]; then
    after_step "plan"
fi
if printf '%s\n' "$OUT" | grep -q 'nothing to do'; then
    echo
    echo "memory-forget.sh: nothing to do. Nothing was changed."
    exit 0
fi
if ! printf '%s' "$PLAN_SHA" | grep -Eq '^[0-9a-f]{64}$' || ! printf '%s' "$PLAN_CASES" | grep -Eq '^[1-9][0-9]*$'; then
    fail "the plan printed no digest or no number of cases." "Nothing was changed."
fi
# <<< guard: preflight-ran
OUT_SHOWN=no

if [ "$MODE" = plan ]; then
    echo
    echo "memory-forget.sh: dry run. NOTHING ABOVE WAS CHANGED. To forget these cases, show the plan to the owner, get the"
    echo "memory-forget.sh: permission in writing (R-146aj), then run the same command with"
    echo "memory-forget.sh:   --apply --actor <admin login> --reason <code> --owner-permission-ref \"<where it is recorded>\" \\"
    echo "memory-forget.sh:   --plan-sha256 $PLAN_SHA --stop-services"
    echo "memory-forget.sh: api and worker should not be running for the apply: --stop-services stops them and starts them again."
    echo "memory-forget.sh: NO DUMP WILL BE TAKEN (it would keep the forgotten content); take care of the copies yourself first."
    exit 0
fi

# --- --apply: the plan above must be the plan that was approved, and the operator must retype what it is ---------------
# >>> guard: plan-approved
# The digest on the command line is the plan someone READ. The memory may have changed since (a case captured, a crop shared): the plan above is
# then not the one that was approved, and the answer is to read the new one, not to forget on the strength of the old.
if [ "$PLAN_SHA" != "$PLAN_SHA_GIVEN" ]; then
    refuse "the plan the memory has now is not the plan you approved." \
           "  approved (--plan-sha256): $PLAN_SHA_GIVEN" \
           "  plan above              : $PLAN_SHA" \
           "Read the plan above, get the owner's permission for it, and run again with its digest. Nothing was changed."
fi
# <<< guard: plan-approved

echo
echo "memory-forget.sh: THIS FORGETS THE CONTENT OF THE $PLAN_CASES CASE(S) ABOVE. It cannot be undone, and NO DUMP is taken first."
echo "memory-forget.sh: actor $ACTOR, reason $REASON, owner's permission: $PERMISSION_REF"
if [ "$STOP_SERVICES" != yes ]; then
    echo "memory-forget.sh: api and worker are NOT being stopped (no --stop-services). A capture or a withdraw that arrives during the run"
    echo "memory-forget.sh: can make it deadlock or roll back; nothing is changed then, and you run it again."
fi
printf 'memory-forget.sh: retype the number of cases to go on: '
IFS= read -r TYPED_CASES || TYPED_CASES=""
printf 'memory-forget.sh: retype the plan digest to go on: '
IFS= read -r TYPED_DIGEST || TYPED_DIGEST=""
echo
# >>> guard: retyped-confirmation
# Both come from the keyboard, not from the command line: a value that was pasted into the command is a value nobody has looked at. An end of
# input (a script feeding the apply, a closed terminal) is no answer.
if [ "$TYPED_CASES" != "$PLAN_CASES" ] || [ "$TYPED_DIGEST" != "$PLAN_SHA" ]; then
    refuse "what was retyped is not the number of cases and the plan above." \
           "  cases      : ${TYPED_CASES:-<nothing>}" \
           "  plan digest: ${TYPED_DIGEST:-<nothing>}" \
           "Nothing was changed."
fi
# <<< guard: retyped-confirmation

# --- the forget -------------------------------------------------------------------------------------------------
stop_services_if_asked
echo "memory-forget.sh: forgetting (one transaction, then the objects, then the final record)"
run_tool --database "$DATABASE" --bucket "$BUCKET" "${SELECTOR[@]}" --apply --plan-sha256 "$PLAN_SHA_GIVEN" \
    --actor "$ACTOR" --reason "$REASON" --owner-permission-ref "$PERMISSION_REF" --dump-dir /dump
after_step "forget"
printf '%s\n' "$(host_paths "$OUT")"
if printf '%s\n' "$OUT" | grep -q 'nothing to do'; then
    echo
    echo "memory-forget.sh: nothing to do. Nothing was changed."
    exit 0
fi
if [ -n "$(parse manifest-sha256 "$OUT")" ]; then
    finish_report
else
    fail "the forget printed no manifest digest." \
         "The tool exited 0, so the database part is done, but the record of it is not here. Read the output above before doing anything else."
fi
exit 0
