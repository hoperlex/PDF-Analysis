#!/usr/bin/env bash
# `D-511` -- show and change the installation settings of the decision memory: `data_class` (what the cases captured FROM NOW ON are, `test` or
# `real`) and `training_use` (whether the training export may run, `off` or `on`).
#
#   infra/deploy/memory-setting.sh --database <name> show
#   infra/deploy/memory-setting.sh --database <name> set data_class real --actor <admin login>
#   infra/deploy/memory-setting.sh --database <name> set training_use on --actor <admin login> \
#         --owner-permission-ref "<where the owner's permission is recorded>"
#
# THE DESIGN IS `DECISION-MEMORY-01` SECTION 8 (PHASE M2) AND `scripts/recovery/memory_setting.py`. This file is the operator's door to that module
# and nothing more, in the shape of `erase-project.sh`: it holds the guards that can be checked before a connection, runs the module inside the
# `api` image from the files it imports mounted read-only, makes the operator retype the new value, and checks the result by reading it back. The
# module's refusals are its own -- above all the one that matters here: a change of `data_class` is refused while the memory has not captured every
# decision of the ledger (`D-496`, no override) -- and this file shows them and adds none of its own after a connection.
#
# WHAT THIS SCRIPT READS (`D-517`): the module's `show --json`, ONE line of JSON, and nothing else of its output. The "nothing to do" short-circuit
# and the read-back decide from the members of that line, and the screen the operator sees (`in force now`, the record at the end) is printed
# from the same line, so what is shown and what is checked are one read. A line without every member of SHOW_MEMBERS is a failure, never a
# guess. `memory_setting.SHOW_JSON_KEYS` and SHOW_MEMBERS below are held to each other by tests/integration/composition/test_memory_setting_script.py.
#
# WHAT A `set` DOES, IN ORDER (three container runs, each one the module):
#
#   1. `show`: the settings in force now, printed -- the operator sees the value they are about to replace and the count of decisions the sweep
#      has not captured. A setting that already has the typed value is "nothing to do" and nothing is asked.
#   2. the operator RETYPES the new value. A value that was pasted into the command line is a value nobody looked at, and `data_class` cannot be
#      applied to the past: a case captured under the wrong class is withdrawn, not reclassified.
#   3. `set`, then `show` again: the settings in force are printed once more for the release record, and the value read back must be the typed
#      one. A setting that does not read back as written is a failure, not a success.
#
# THE PYTHON HALF CONNECTS AS THE OWNER (`PROD-04-DB-ROLES-01`): the one-off container gets `MIGRATOR_DATABASE_URL` as `DATABASE_URL` through the
# environment of the `docker compose` process (compose substitutes it into the `api` service's `environment:`; the password never appears in a
# command line), and no `PG*` variable. THE TARGET IS ALWAYS THIS STACK, through `docker compose -f compose.server.yml`; it must be UP (postgres).
#
# NO SERVICE IS STOPPED. The change is one short transaction that holds the ledger still for its own length; the worker has to be RUNNING for the
# sweep that empties the backlog the module counts.
#
# EXIT CODES: 0 done or nothing to do; 2 usage; 3 REFUSED (nothing was changed); 4 FAILED. A `set` that fails is 4 and says to run `show`: the
# write is one transaction, so the settings in force say which of the two it was.
#
# GUARDS ARE DELIMITED BY MARKERS -- `# >>> guard: <name>` / `# <<< guard: <name>`.
# `tests/integration/composition/test_memory_setting_script.py` reads those markers, deletes ONE guard block from a copy of this file and shows
# the copy no longer refuses. A guard that cannot be shown to fail is not evidence. Do not remove a marker without removing its test.

set -Eeuo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$HERE/compose.server.yml"
ENV_FILE="${ALPHA_ENV_FILE:-$HERE/env/alpha.env}"
MODULE_DIR="${ALPHA_MEMORY_MODULE_DIR:-$HERE/../../scripts/recovery}"
# The files the module needs and nothing else: `memory_setting` imports `project_erase` (which imports `product_purge`, `blob_reference_audit`
# and `schema_coverage`); tests/integration/composition/test_memory_setting_script.py holds this list to the module's own imports.
MODULES=(memory_setting project_erase product_purge schema_coverage blob_reference_audit)
# The members of the line `memory_setting show --json` prints (`memory_setting.SHOW_JSON_KEYS`): a value, a revision and a default for each of the
# two settings, then the count of decisions the sweep has not captured.
SHOW_MEMBERS=(data_class data_class_revision data_class_default training_use training_use_revision training_use_default uncaptured_decisions)

DATABASE=""
ACTOR=""
PERMISSION_REF=""
HAVE_REF=no
POS=()

SELF="$0"

refuse() {
    printf 'memory-setting.sh: REFUSED: %s\n' "$1" >&2
    shift
    [ "$#" -eq 0 ] || printf '  %s\n' "$@" >&2
    exit 3
}

fail() {
    printf 'memory-setting.sh: FAILED: %s\n' "$1" >&2
    shift
    [ "$#" -eq 0 ] || printf '  %s\n' "$@" >&2
    exit 4
}

usage() {
    cat >&2 <<'USAGE'
usage: memory-setting.sh --database <name> show
       memory-setting.sh --database <name> set data_class <test|real> --actor <admin login>
       memory-setting.sh --database <name> set training_use <off|on> --actor <admin login>
                         [--owner-permission-ref "<text>"]      (required for training_use on)

  show                         print the settings in force and the count of decisions the memory has not captured yet.
  set <setting> <value>        change one. The settings in force are printed, the operator retypes the new value, the module writes it,
                               and the settings are read back and printed again for the release record.
  --database <name>            the database this acts on. Must equal the configured one.
  --actor <login>              the administrator on whose account the change is journalled (set only).
  --owner-permission-ref <t>   one line, at most 200 characters: where the OWNER's permission is recorded. Required for training_use on
                               (it releases client-derived content off the host); optional for the others. Recorded, never verified.
  --env-file <path>            default: infra/deploy/env/alpha.env

  MEMORY_SETTING_LOCK_TIMEOUT  environment, optional: how long the change waits for the ledger lock, for example 30s (default 15s).
                               A positive number of ms, s or min; it is passed to the one-off container.

A change of data_class is refused by the module while the sweep has not captured every decision of the ledger. There is no override:
let the worker finish (show prints the count), then run it again.
USAGE
    exit 2
}

# `exit 4` for anything a command did not handle itself: a refusal is 3 and is spelled out.
on_error() {
    printf 'memory-setting.sh: FAILED: a step exited non-zero (line %s).\n' "$1" >&2
    exit 4
}
trap 'on_error $LINENO' ERR

# >>> guard: known-options
# An unrecognised option is refused rather than ignored, and so is one that has lost its value: `--actro` silently ignored would run a change the
# operator believed was attributed, and a trailing `--actor` would swallow the next word.
while [ "$#" -gt 0 ]; do
    case "$1" in
        --database|--actor|--owner-permission-ref|--env-file)
            [ "$#" -ge 2 ] || refuse "$1 needs a value." "Nothing was read and nothing was touched. Run --help." ;;
    esac
    case "$1" in
        --database) DATABASE="$2"; shift 2 ;;
        --actor) ACTOR="$2"; shift 2 ;;
        --owner-permission-ref) PERMISSION_REF="$2"; HAVE_REF=yes; shift 2 ;;
        --env-file) ENV_FILE="$2"; shift 2 ;;
        -h|--help) usage ;;
        -*) refuse "unrecognised option: $1" \
                   "Nothing was read and nothing was touched. Run --help." ;;
        *) POS+=("$1"); shift ;;
    esac
done
# <<< guard: known-options

COMMAND="${POS[0]:-}"
NAME="${POS[1]:-}"
VALUE="${POS[2]:-}"
# >>> guard: command-shape
# The first word is the command, and `set` takes exactly a setting and a value: a word too many is a typo the operator should hear about, not a
# value that is quietly ignored.
case "$COMMAND" in
    show) [ "${#POS[@]}" -eq 1 ] || refuse "show takes no further word." "  given: ${POS[*]}" "Nothing was read and nothing was touched." ;;
    set) [ "${#POS[@]}" -eq 3 ] || refuse "set takes a setting and a value: set <data_class|training_use> <value>." \
                                           "  given: ${POS[*]}" "Nothing was read and nothing was touched." ;;
    *) refuse "the command is show or set." "  given: ${COMMAND:-<none>}" "Nothing was read and nothing was touched. Run --help." ;;
esac
# <<< guard: command-shape

# >>> guard: setting-and-value
# The module's closed lists (`SETTING_VALUES`), refused here first so that a typo is a sentence and not a connection.
if [ "$COMMAND" = set ]; then
    case "$NAME:$VALUE" in
        data_class:test|data_class:real|training_use:off|training_use:on) ;;
        *) refuse "data_class admits test and real; training_use admits off and on." \
                  "  given: $NAME $VALUE" "Nothing was read and nothing was touched." ;;
    esac
fi
# <<< guard: setting-and-value

# >>> guard: options-match-the-command
# `show` changes nothing and journals nothing: an actor or a permission given to it would be read by the operator as a change that was asked for.
if [ "$COMMAND" = show ] && { [ -n "$ACTOR" ] || [ "$HAVE_REF" = yes ]; }; then
    refuse "--actor and --owner-permission-ref belong to set, and the command is show." \
           "show changes nothing. Use set to change a setting, or drop them. Nothing was read and nothing was touched."
fi
# <<< guard: options-match-the-command

# >>> guard: names-required
if [ -z "$DATABASE" ]; then
    refuse "--database is required, even for show." \
           "Typing the target is the point: it is what makes a change in the wrong instance" \
           "a thing you have to do on purpose."
fi
# <<< guard: names-required

# >>> guard: actor-required
# The change is journalled on an administrator's account. The module checks that the account exists and holds `admin`; here the value must at
# least be one word that is not an option, so that an empty string, a sentence or a swallowed option is refused before a connection.
if [ "$COMMAND" = set ]; then
    if [ -z "$ACTOR" ] || [[ "$ACTOR" =~ [[:space:][:cntrl:]] ]] || [ "${#ACTOR}" -gt 254 ] || [[ "$ACTOR" == -* ]]; then
        refuse "--actor must be the login of an administrator (one word)." \
               "  given: ${ACTOR:-<none>}" \
               "Nothing was read and nothing was touched."
    fi
fi
# <<< guard: actor-required

# >>> guard: permission-ref-shape
# When a reference is given it is one line of a sensible length, whatever the setting: it is written into an append-only table.
if [ "$HAVE_REF" = yes ]; then
    ref="$PERMISSION_REF"
    ref="${ref#"${ref%%[![:space:]]*}"}"
    ref="${ref%"${ref##*[![:space:]]}"}"
    if [ -z "$ref" ] || [ "${#ref}" -gt 200 ] || [[ "$PERMISSION_REF" =~ [[:cntrl:]] ]]; then
        refuse "--owner-permission-ref must be one line of at most 200 characters saying where the owner's permission is recorded." \
               "It is recorded as given and never verified. Nothing was read and nothing was touched."
    fi
    if [[ "$ref" == -* ]]; then
        refuse "--owner-permission-ref must not begin with '-': the module would read it as an option and refuse it late." \
               "  given: $ref" \
               "Say in words where the permission is recorded (for example: owner mail of 2026-11-09). Nothing was read and nothing was touched."
    fi
    PERMISSION_REF="$ref"
fi
# <<< guard: permission-ref-shape

# >>> guard: training-needs-permission
# `training_use = on` releases client-derived content off the host (`ADR-0022` section 4): the owner's permission, recorded, is the only ground.
if [ "$COMMAND" = set ] && [ "$NAME" = training_use ] && [ "$VALUE" = on ] && [ "$HAVE_REF" != yes ]; then
    refuse "training_use on releases client-derived content off the host: --owner-permission-ref is required" \
           "(where the owner's permission is recorded; it is recorded, not verified). Nothing was read and nothing was touched."
fi
# <<< guard: training-needs-permission

# >>> guard: lock-timeout-shape
# `D-515`: how long the module waits for the ledger lock is the operator's to set (`MEMORY_SETTING_LOCK_TIMEOUT`, default `15s` in the module).
# It is handed to the one-off container as it is, so it must be a plain positive duration: a typo is a sentence here and not a database
# error after the connection, and `0` (wait for ever) is not a timeout.
# PostgreSQL takes at most 2147483647 ms (about 35791 min) for `lock_timeout`: a longer duration is a sentence here too, not an error 22023
# after the connection (`F3` of the 2026-11-10 judge report).
if [ "${MEMORY_SETTING_LOCK_TIMEOUT+set}" = set ]; then
    lock_ms=0
    if [[ "$MEMORY_SETTING_LOCK_TIMEOUT" =~ ^([1-9][0-9]{0,5})(ms|s|min)$ ]]; then
        case "${BASH_REMATCH[2]}" in
            ms) lock_ms=$(( ${BASH_REMATCH[1]} )) ;;
            s) lock_ms=$(( ${BASH_REMATCH[1]} * 1000 )) ;;
            min) lock_ms=$(( ${BASH_REMATCH[1]} * 60000 )) ;;
        esac
    fi
    if [ "$lock_ms" -lt 1 ] || [ "$lock_ms" -gt 2147483647 ]; then
        refuse "MEMORY_SETTING_LOCK_TIMEOUT must be a positive number of ms, s or min (for example 30s)." \
               "It is at most 2147483647 ms (about 35791 min): the largest lock_timeout PostgreSQL takes." \
               "  given: ${MEMORY_SETTING_LOCK_TIMEOUT:-<empty>}" \
               "Unset it for the module's own 15s. Nothing was read and nothing was touched."
    fi
fi
# <<< guard: lock-timeout-shape

# >>> guard: env-file-present
if [ ! -r "$ENV_FILE" ]; then
    refuse "the deployment environment $ENV_FILE is missing or unreadable." \
           "Without it there is no configured instance to compare the typed name against," \
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
# The settings journal is written by the table owner only (the application role has SELECT). An environment with no owner url has nothing to hand
# the tool but the application's, which cannot write it; say so before any connection is made.
if [[ ! "$MIGRATOR_URL" =~ ^postgresql\+psycopg://[^:@/]+:[^@/]+@[^:@/]+:[0-9]+/[^?]+$ ]]; then
    refuse "[migrator_url_unset] MIGRATOR_DATABASE_URL in $ENV_FILE is unset or is not a postgresql+psycopg:// url." \
           "The settings are written by the owner role (POSTGRES_USER); api's DATABASE_URL is the application role's" \
           "and cannot write them. Nothing was read and nothing was touched." \
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

# >>> guard: compose-file-present
if [ ! -r "$COMPOSE_FILE" ]; then
    refuse "$COMPOSE_FILE is missing." \
           "Every step runs through it; without it this script has no target it is allowed" \
           "to reach."
fi
# <<< guard: compose-file-present

# >>> guard: modules-present
# The module and everything it imports live in scripts/recovery/. The api image does not carry that directory, so the five files are mounted
# from this checkout; a checkout without one of them cannot run the module.
MISSING=()
for module in "${MODULES[@]}"; do
    [ -r "$MODULE_DIR/$module.py" ] || MISSING+=("$module.py")
done
if [ "${#MISSING[@]}" -gt 0 ]; then
    refuse "scripts/recovery/ lacks ${MISSING[*]} under $MODULE_DIR." \
           "The module reads the migration head from schema_coverage.py and the actor's rules from project_erase.py; it will not guess."
fi
# <<< guard: modules-present

MODULE_DIR="$(cd "$MODULE_DIR" && pwd)"

compose() { docker compose --env-file "$ENV_FILE" --file "$COMPOSE_FILE" "$@"; }

# `D-515`: the lock timeout the operator set, and only that one, goes into the container (the shape was checked above). None set: nothing is
# passed and the module's own default applies.
LOCK_TIMEOUT_ENV=()
[ "${MEMORY_SETTING_LOCK_TIMEOUT+set}" != set ] || LOCK_TIMEOUT_ENV=(-e "MEMORY_SETTING_LOCK_TIMEOUT=$MEMORY_SETTING_LOCK_TIMEOUT")

# THE PYTHON HALF RUNS INSIDE THE `api` IMAGE, from five files mounted read-only. The container runs as the operator's uid, as the erase's does;
# stdin is /dev/null so that `docker compose run` cannot swallow the answer the operator is about to type (it forwards stdin otherwise).
ERR_FILE="$(mktemp)"
setting_python() {
    local mounts=() module
    for module in "${MODULES[@]}"; do
        mounts+=(-v "$MODULE_DIR/$module.py:/purge/scripts/recovery/$module.py:ro")
    done
    DATABASE_URL="$MIGRATOR_URL" compose run --rm --no-deps -T --user "$(id -u):$(id -g)" \
        -e PYTHONPATH=/app/src:/purge "${LOCK_TIMEOUT_ENV[@]+"${LOCK_TIMEOUT_ENV[@]}"}" "${mounts[@]}" \
        --entrypoint python api -m scripts.recovery.memory_setting --database "$DATABASE" "$@" </dev/null
}

# Runs one step and leaves its stdout in OUT, its status in STATUS and its stderr in ERR (also shown, after the step).
run_tool() {
    STATUS=0
    OUT="$(setting_python "$@" 2>"$ERR_FILE")" || STATUS=$?
    ERR="$(cat "$ERR_FILE")"
    [ -z "$ERR" ] || printf '%s\n' "$ERR" >&2
}

cleanup() {
    local status=$?
    trap - ERR
    rm -f "$ERR_FILE"
    exit "$status"
}
trap cleanup EXIT

# What a stopped step means, said once. `$1` names the step; `$2` is `writing` for the step that changes the setting.
after_step() {
    local what="$1" writing="${2:-no}"
    [ "$STATUS" -ne 0 ] || return 0
    if [ "$STATUS" -eq 3 ]; then
        refuse "the $what was refused (reason above)." "Nothing was changed."
    fi
    if [ "$writing" = writing ]; then
        fail "the $what failed (status $STATUS)." \
             "The change is one transaction, so the settings in force say whether it was made. Look:" \
             "  $SELF --database $(printf '%q' "$DATABASE") show"
    fi
    fail "the $what failed (status $STATUS)." "Nothing was changed. Is the stack up (postgres)?"
}

# `D-517`: the settings in force are the members of ONE line of JSON, flat, printed by `memory_setting show --json`: strings of `[a-z_]` and
# non-negative integers, `"name": value` with one space after the colon (`json.dumps`). `json_member <line> <name>` prints the value of a member
# (without quotes), or nothing when there is no such member; it always succeeds, so that an absent member is a failure the caller names and not an
# unexplained exit of the error trap.
json_member() {
    local line="$1" name="$2" ere value
    ere="\"$name\": (\"[a-z_]+\"|[0-9]+)[,}]"
    if [[ "$line" =~ $ere ]]; then
        value="${BASH_REMATCH[1]}"
        printf '%s\n' "${value//\"/}"
    fi
}

# The value of a setting that the line says is in force: `{"data_class": "real", ...}` -> `real`.
setting_value() { json_member "$2" "$1"; }

# A line is understood when it is ONE line and has every member of SHOW_MEMBERS in its shape. Anything else (the old text screen, an error, a
# line of a newer module) is not a line this script can decide from, and guessing from it would be the untruth the read-back exists to prevent.
settings_understood() {
    local line="$1" member value
    [[ "$line" != *$'\n'* ]] || return 1
    for member in "${SHOW_MEMBERS[@]}"; do
        value="$(json_member "$line" "$member")"
        case "$member" in
            *_revision|uncaptured_decisions) [[ "$value" =~ ^[0-9]+$ ]] || return 1 ;;
            *) [[ "$value" =~ ^[a-z_]+$ ]] || return 1 ;;
        esac
    done
}

# The screen, printed from the line that was read (the same words as the module's own `show` prints for an operator who runs the module by hand).
settings_screen() {
    local line="$1" name revision origin
    for name in data_class training_use; do
        revision="$(json_member "$line" "${name}_revision")"
        if [ "$revision" = 0 ]; then origin=default; else origin="revision $revision"; fi
        printf '%s: %s (%s; default %s)\n' "$name" "$(json_member "$line" "$name")" "$origin" "$(json_member "$line" "${name}_default")"
    done
    printf 'uncaptured-decisions: %s (ledger accept/reject events with no memory decision; a data_class change is refused until this is 0)\n' \
        "$(json_member "$line" uncaptured_decisions)"
}

# One look at the settings in force: the module's `show --json`, checked, left in LOOK. `$1` names the step; `$2` is `writing` for the look that
# follows a write, which cannot promise that nothing was changed.
look() {
    local what="$1" writing="${2:-no}"
    run_tool show --json
    after_step "$what" "$writing"
    if ! settings_understood "$OUT"; then
        if [ "$writing" = writing ]; then
            fail "the $what did not print the settings in the form this script reads (one line of JSON)." \
                 "  printed: $OUT" \
                 "The change may have been made: the settings in force say whether it was. Look:" \
                 "  $SELF --database $(printf '%q' "$DATABASE") show"
        fi
        fail "the $what did not print the settings in the form this script reads (one line of JSON)." \
             "  printed: $OUT" "Nothing was changed."
    fi
    LOOK="$OUT"
}

echo "memory-setting.sh: instance   $CONFIGURED_INSTANCE"
echo "memory-setting.sh: database   $DATABASE"

# --- show -------------------------------------------------------------------------------------------------------
if [ "$COMMAND" = show ]; then
    look "show"
    settings_screen "$LOOK"
    exit 0
fi

# --- set: look first, ask, write, look again -------------------------------------------------------------------
look "show before the change"
BEFORE="$LOOK"
CURRENT="$(setting_value "$NAME" "$BEFORE")"
echo
echo "memory-setting.sh: in force now:"
settings_screen "$BEFORE"
if [ "$CURRENT" = "$VALUE" ]; then
    echo
    echo "memory-setting.sh: $NAME is already $VALUE; nothing to do. Nothing was changed."
    exit 0
fi

echo
case "$NAME" in
    data_class)
        echo "memory-setting.sh: THIS CHANGES data_class FROM $CURRENT TO $VALUE for every case captured from now on."
        echo "memory-setting.sh: Cases already captured keep their class (the column is immutable); a case captured under the wrong class is"
        echo "memory-setting.sh: withdrawn and decided again, not reclassified. The module refuses while uncaptured-decisions above is not 0." ;;
    *)
        echo "memory-setting.sh: THIS CHANGES $NAME FROM $CURRENT TO $VALUE."
        echo "memory-setting.sh: on lets the training export release client-derived content off this host (ADR-0022 section 4)." ;;
esac
if [ "$HAVE_REF" = yes ]; then
    echo "memory-setting.sh: actor $ACTOR, owner's permission: $PERMISSION_REF"
else
    echo "memory-setting.sh: actor $ACTOR"
fi
printf 'memory-setting.sh: retype the new value of %s to go on: ' "$NAME"
IFS= read -r TYPED_VALUE || TYPED_VALUE=""
echo
# >>> guard: retyped-confirmation
# The answer comes from the keyboard, not from the command line: a value that was pasted into the command is a value nobody has looked at. An end
# of input (a script feeding the change, a closed terminal) is no answer.
if [ "$TYPED_VALUE" != "$VALUE" ]; then
    refuse "what was retyped is not the new value of $NAME." \
           "  new value: $VALUE" \
           "  retyped  : ${TYPED_VALUE:-<nothing>}" \
           "Nothing was changed."
fi
# <<< guard: retyped-confirmation

SET_ARGS=(set "$NAME" "$VALUE" --actor "$ACTOR")
[ "$HAVE_REF" != yes ] || SET_ARGS+=(--owner-permission-ref "$PERMISSION_REF")
echo "memory-setting.sh: changing $NAME to $VALUE"
run_tool "${SET_ARGS[@]}"
after_step "change" writing
printf '%s\n' "$OUT"

look "show after the change" writing
AFTER="$LOOK"
# >>> guard: readback-verified
# The module said it wrote the value. The settings in force are the proof, and they are what goes into the release record: a value that does not
# read back as written is not a change the operator is allowed to record as made.
if [ "$(setting_value "$NAME" "$AFTER")" != "$VALUE" ]; then
    fail "THE CHANGE WAS REPORTED DONE but the settings in force do not say $NAME is $VALUE." \
         "  settings read back:" "$(settings_screen "$AFTER" | sed 's/^/    /')" \
         "Do not record the change as made. Look again:  $SELF --database $(printf '%q' "$DATABASE") show"
fi
# <<< guard: readback-verified
echo
echo "memory-setting.sh: done. $NAME is now $VALUE. Write the settings below and today's date in the release record:"
settings_screen "$AFTER"
exit 0
