#!/usr/bin/env bash
# `R-46` -- one command that answers "is this deployment safe to publish?": the default
# credential, TLS, plain HTTP, the provider mode, the cost ceiling, off-host backup.
#
#   infra/deploy/readiness.sh [--env-file <path>] [--provider-env-file <path>]
#
# `docs/program/dispatch/GO_PATH.md` names this command against steps 4, 5, 7 and 8, which
# are "a checklist somebody has to remember". `OWNER_RULINGS_2026-09-17.md` §3.16 `R-46`
# ruled what it does with what it finds, and it reads backwards on a first pass:
#
#   THIS COMMAND REPORTS AND REGISTERS. IT DOES NOT BLOCK A DEPLOY.
#
# `D-72`'s repair was correct and fail-closed and took the owner's stand down for a day,
# because a configuration that had always been wrong stopped being survivable the moment the
# code got strict. A readiness check that refuses is the same shape, and the owner chose the
# other side of it with that precedent in hand. So every finding below is a corpus entry --
# a register row requiring a ruling -- and `deploy.sh` never calls this script and never
# reads its exit status. Nothing in this repository treats a red line here as a refusal.
#
# EACH CHECK MUST BE SHOWN ABLE TO FAIL, ON A CONFIGURATION BUILT TO FAIL IT -- a command
# that is green on every input is the thing this programme has already paid to learn about
# (`W46-GUARD`, `X-1`/`X-2`). `tests/integration/composition/test_readiness_command.py`
# drives every one of the seven checks below to both a clean answer and a finding, and for the
# five that do not need a running stack, deletes the check's own marked block and shows the
# finding disappears -- the same mutation discipline `deploy.sh`'s guards are held to.
#
# CHECKS ARE DELIMITED BY MARKERS -- `# >>> check: <name>` / `# <<< check: <name>` -- the
# same convention `deploy.sh` uses for its guards, read the same way by the test suite.
#
# WHAT IS REUSED RATHER THAN RE-DERIVED, because `W47-GATE.md`'s brief is explicit that this
# is the point:
#
#   * `default-credential` runs `src/auditmanager/access/check.py` inside the api image,
#     exactly the way `deploy.sh`'s `migrations-at-head` guard runs `shared.db.check` --
#     and reads its own stable, already-existing sentinels
#     (`access-check OK no default credentials` / `access-check DEFAULT CREDENTIAL`)
#     rather than asking the question a second time;
#   * `provider-mode` and `cost-ceiling` both call
#     `auditmanager.bootstrap.settings.load()` -- the composition root's own validation,
#     the thing that actually decides whether the api container starts -- rather than
#     re-implementing "is AUDITMANAGER_PROVIDER_MODE one of the three declared modes" or
#     "does live/proxy mode have the credential it needs" in bash a second time.
#
# `off-host-backup` has no existing module to consult: nothing in this tree names an off-host
# destination, so it is read against the values `docs/program/DEPLOYMENT_RUNBOOK.md` §1 and §5
# already document.
#
# `tls` and `plain-http` were rewritten by `PROD-01-TLS-ACME-01` for the layout in which this stack
# terminates TLS itself (`ADR-0021` section 2). `tls` asks the proxy's own TLS listener what certificate
# it serves, through `infra/acme/check-served.sh` in a one-off container of the ACME image (the same
# question `verify-deployed.sh` asks, reported here and not enforced); `plain-http` asks the challenge
# listener on public port 80 whether it is what `R-146s` says it is -- a redirect and nothing else.
# Both are about a stack with `ALPHA_CERT_NAME` set; without one, `tls` reports that no terminator is
# part of the stack and `plain-http` keeps the bind-address reading it always had.
#
# THE HOST NEEDS NO PYTHON FOR FOUR OF THE SIX. `DEPLOYMENT_RUNBOOK.md` §1 promises this
# host only bash, docker, curl, sed and git. `default-credential` runs python inside the api
# image (docker required); `provider-mode` and `cost-ceiling` run this repository's own
# `.venv` (present on a development or CI host, not promised on the deploy target -- and
# reported UNKNOWN rather than guessed when it is missing, never silently OK).

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
COMPOSE_FILE="$HERE/compose.server.yml"
ENV_FILE="${ALPHA_ENV_FILE:-$HERE/env/alpha.env}"
PROVIDER_ENV_FILE="${ALPHA_PROVIDER_ENV_FILE:-$HERE/env/provider.env}"
PYTHON="$REPO/.venv/bin/python"

usage() {
    cat >&2 <<'USAGE'
usage: readiness.sh [--env-file <path>] [--provider-env-file <path>]

  --env-file <path>           default: infra/deploy/env/alpha.env
  --provider-env-file <path>  default: infra/deploy/env/provider.env

Reports on eight publication-readiness questions and registers each finding. Refuses nothing
and blocks no deploy (R-46). Exit 0: every check answered clean. Exit 1: at least one
finding. Exit 2: at least one check could not be answered (missing tooling, missing file --
never read as clean).
USAGE
    exit 2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --env-file) ENV_FILE="${2:-}"; shift 2 ;;
        --provider-env-file) PROVIDER_ENV_FILE="${2:-}"; shift 2 ;;
        -h|--help) usage ;;
        *) printf 'readiness.sh: unrecognised option: %s\n' "$1" >&2; usage ;;
    esac
done

# Read as DATA, never sourced -- the same idiom `deploy.sh`, `reset.sh` and
# `verify-deployed.sh` all use on this same file.
configured() {
    [ -r "$ENV_FILE" ] || return 0
    sed -n "s/^[[:space:]]*\(export[[:space:]]\+\)\?$1=//p" "$ENV_FILE" | tail -1 \
        | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/"
}
configured_provider() {
    [ -r "$PROVIDER_ENV_FILE" ] || return 0
    sed -n "s/^[[:space:]]*\(export[[:space:]]\+\)\?$1=//p" "$PROVIDER_ENV_FILE" | tail -1 \
        | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/"
}

FINDINGS=0
UNKNOWNS=0

ok() {
    printf 'readiness OK      %-18s %s\n' "$1" "$2"
}
finding() {
    printf 'readiness FINDING %-18s %s\n' "$1" "$2"
    FINDINGS=$((FINDINGS + 1))
}
unknown() {
    printf 'readiness UNKNOWN %-18s %s\n' "$1" "$2"
    UNKNOWNS=$((UNKNOWNS + 1))
}

echo "readiness.sh: R-46 -- this command REPORTS and REGISTERS. It refuses nothing and"
echo "readiness.sh: blocks no deploy; nothing in this repository reads its exit status."
echo "readiness.sh: env-file          $ENV_FILE"
echo "readiness.sh: provider-env-file $PROVIDER_ENV_FILE"
echo

# >>> check: default-credential
# Step 5, `R-46`/G2. `src/auditmanager/access/check.py` already answers "is the default
# admin password still live" with stable, grep-able sentinels; this consults it rather than
# re-deriving the question, run inside the api image against the deployed database exactly
# the way `deploy.sh`'s `migrations-at-head` guard runs `shared.db.check`.
if [ ! -r "$ENV_FILE" ]; then
    unknown default-credential "no $ENV_FILE to read DATABASE_URL from."
elif ! command -v docker >/dev/null 2>&1; then
    unknown default-credential "no docker on PATH; access-check runs inside the deployed api image."
else
    ACCESS_OUTPUT="$(docker compose --env-file "$ENV_FILE" --file "$COMPOSE_FILE" \
        run --rm --no-deps -T --entrypoint python api -m auditmanager.access.check 2>&1 || true)"
    if printf '%s\n' "$ACCESS_OUTPUT" | grep -q '^access-check OK no default credentials$'; then
        ok default-credential "no account is still on its seeded password."
    elif printf '%s\n' "$ACCESS_OUTPUT" | grep -q '^access-check DEFAULT CREDENTIAL'; then
        COUNT="$(printf '%s\n' "$ACCESS_OUTPUT" | grep -c '^access-check DEFAULT CREDENTIAL')"
        finding default-credential "$COUNT account(s) still on the password this system seeded them with -- step 5 is not done. access-check's own lines:"
        printf '%s\n' "$ACCESS_OUTPUT" | grep '^access-check DEFAULT CREDENTIAL' | sed 's/^/    /'
    else
        unknown default-credential "access-check answered neither the clean nor the finding sentinel; raw output:"
        printf '%s\n' "$ACCESS_OUTPUT" | sed 's/^/    /'
    fi
fi
echo
# <<< check: default-credential

# >>> check: db-roles
# `PROD-04-DB-ROLES-01`, `R-146n` item 1, `ADR-0021` section 3 and row 7. Which database role do `api` and `worker`
# connect as, and is it the restricted application role -- one that cannot change the schema, cannot truncate and owns
# nothing -- and not the owner (a superuser)? Three questions, each asked of the thing that knows:
#
#   1. the RUNNING `api` and `worker` containers, for the user of the `DATABASE_URL` they were started with (only the
#      user is read and printed; the password never leaves the container);
#   2. the database, for the facts `ADR-0021` row 7 names: not a superuser, no CREATE on schema public, no DELETE and
#      an INSERT on audit_event -- `f|f|f|t`;
#   3. `apply-grants.sh --check`, which compares every table, view and sequence with the grant classification.
#
# Reported, not enforced (`R-46`): `deploy.sh` is what refuses a stack whose roles are not configured.
DB_ROLE="$(configured ALPHA_APP_DB_USER)"
DB_OWNER="$(configured POSTGRES_USER)"
DB_NAME="$(configured POSTGRES_DB)"
if [ ! -r "$ENV_FILE" ]; then
    unknown db-roles "no $ENV_FILE to read the roles from."
elif ! command -v docker >/dev/null 2>&1; then
    unknown db-roles "no docker on PATH; the roles are asked of the running containers and of the database."
elif [[ ! "$DB_ROLE" =~ ^[a-z_][a-z0-9_]{2,62}$ ]]; then
    finding db-roles "ALPHA_APP_DB_USER is '${DB_ROLE:-<unset>}' in $ENV_FILE: no application role is configured, so api and worker can only be connecting as the owner (PROD-04). Set it, choose the second password and deploy (DEPLOYMENT_RUNBOOK.md section 16)."
else
    ROLES_ARGS=(--env-file "$ENV_FILE" --file "$COMPOSE_FILE")
    ROLES_FINDINGS=()
    ROLES_UNKNOWNS=()
    ROLES_SEEN=()
    for service in api worker; do
        SERVICE_URL="$(docker compose "${ROLES_ARGS[@]}" exec -T "$service" sh -c 'printf %s "$DATABASE_URL"' 2>/dev/null || true)"
        SERVICE_USER="$(printf '%s' "$SERVICE_URL" | sed -n 's#^[A-Za-z0-9+]*://\([^:@/]*\):.*#\1#p')"
        if [ -z "$SERVICE_USER" ]; then
            ROLES_UNKNOWNS+=("$service is not running or has no DATABASE_URL, so the role it connects as is unknown")
        elif [ "$SERVICE_USER" = "$DB_OWNER" ]; then
            ROLES_FINDINGS+=("$service connects as the OWNER role '$SERVICE_USER' (a superuser that owns every object): its DATABASE_URL is still the pre-PROD-04 one")
        elif [ "$SERVICE_USER" != "$DB_ROLE" ]; then
            ROLES_FINDINGS+=("$service connects as '$SERVICE_USER', not as ALPHA_APP_DB_USER '$DB_ROLE'")
        else
            ROLES_SEEN+=("$service=$SERVICE_USER")
        fi
    done
    ROLE_FACTS="$(docker compose "${ROLES_ARGS[@]}" exec -T postgres psql --no-psqlrc --username "$DB_OWNER" --dbname "$DB_NAME" -Atc \
        "select rolsuper, has_schema_privilege(rolname,'public','CREATE'), has_table_privilege(rolname,'public.audit_event','DELETE'), has_table_privilege(rolname,'public.audit_event','INSERT') from pg_roles where rolname='$DB_ROLE'" 2>/dev/null </dev/null || true)"
    case "$ROLE_FACTS" in
        "f|f|f|t") ;;
        "") ROLES_FINDINGS+=("the database has no role '$DB_ROLE' (or could not be asked): nothing has run apply-grants.sh") ;;
        *) ROLES_FINDINGS+=("the role '$DB_ROLE' is (superuser|CREATE on public|DELETE on audit_event|INSERT on audit_event) = $ROLE_FACTS, not f|f|f|t") ;;
    esac
    GRANTS_STATUS=0
    GRANTS_OUTPUT="$("$HERE/apply-grants.sh" --env-file "$ENV_FILE" --check 2>&1 </dev/null)" || GRANTS_STATUS=$?
    case "$GRANTS_STATUS" in
        0) ;;
        1) ROLES_FINDINGS+=("apply-grants.sh --check: the rights differ from the classification (run it, or deploy): $(printf '%s\n' "$GRANTS_OUTPUT" | sed -n '2,4p' | tr -s ' \n' ' ')") ;;
        *) ROLES_UNKNOWNS+=("apply-grants.sh --check could not be run (status $GRANTS_STATUS): $(printf '%s\n' "$GRANTS_OUTPUT" | head -2 | tr -s ' \n' ' ')") ;;
    esac
    if [ "${#ROLES_FINDINGS[@]}" -gt 0 ]; then
        finding db-roles "${ROLES_FINDINGS[0]}$([ "${#ROLES_FINDINGS[@]}" -gt 1 ] && printf ' (+%s more: %s)' "$((${#ROLES_FINDINGS[@]} - 1))" "$(printf '%s; ' "${ROLES_FINDINGS[@]:1}")")"
    elif [ "${#ROLES_UNKNOWNS[@]}" -gt 0 ]; then
        unknown db-roles "${ROLES_UNKNOWNS[0]}$([ "${#ROLES_UNKNOWNS[@]}" -gt 1 ] && printf ' (+%s more: %s)' "$((${#ROLES_UNKNOWNS[@]} - 1))" "$(printf '%s; ' "${ROLES_UNKNOWNS[@]:1}")")"
    else
        ok db-roles "${ROLES_SEEN[*]} -- the application role '$DB_ROLE' is not a superuser, cannot create in schema public, cannot delete from audit_event and can insert into it ($ROLE_FACTS); apply-grants.sh --check: its rights match the classification."
    fi
fi
echo
# <<< check: db-roles

# >>> check: tls
# `PROD-01-TLS-ACME-01`. Is the certificate the proxy SERVES one a client can use? Asked of the proxy's own
# TLS listener (`proxy:8443`, on the compose network) by `infra/acme/check-served.sh` in a one-off container
# of the ACME image, so it needs docker and nothing else on the host, and it is about what is served and not
# about whether a file exists somewhere: a pair on a volume that nginx has not loaded serves nothing.
#
# Reported, not enforced (`R-46`): `verify-deployed.sh` is the command that fails a deploy on the same
# facts. Four answers: no `ALPHA_CERT_NAME` (no terminator is part of this stack, which is a finding for a
# deployment meant to be published); a name that is not usable; the TEST endpoint selected; or the served
# certificate judged by `check-served.sh` -- production kind, chain and name verified, at least 14 days left.
CERT_NAME="$(configured ALPHA_CERT_NAME)"
CERT_STAGING="$(configured ALPHA_ACME_STAGING)"
[ -n "$CERT_STAGING" ] || CERT_STAGING=yes
LISTENERS_LIB="$HERE/lib/proxy-listeners.sh"
if [ -z "$CERT_NAME" ]; then
    finding tls "ALPHA_CERT_NAME is not set in $ENV_FILE, so this stack obtains and serves no certificate: TLS, if there is any, is a terminator outside this repository whose configuration and renewal nothing here can read (D-191). Set the name to move the terminator into the stack (DEPLOYMENT_RUNBOOK.md section 6)."
elif [ ! -r "$LISTENERS_LIB" ]; then
    unknown tls "no $LISTENERS_LIB to judge ALPHA_CERT_NAME with."
elif ! CERT_WHY="$(. "$LISTENERS_LIB" && listeners_name_problem "$CERT_NAME")"; then
    finding tls "ALPHA_CERT_NAME '$CERT_NAME' in $ENV_FILE is not a usable name: $CERT_WHY."
elif [ "$CERT_STAGING" != yes ] && [ "$CERT_STAGING" != no ]; then
    finding tls "ALPHA_ACME_STAGING in $ENV_FILE is '$CERT_STAGING', which is neither yes nor no."
elif [ "$CERT_STAGING" = yes ]; then
    finding tls "ALPHA_ACME_STAGING is yes: $CERT_NAME gets the authority's TEST certificate, which no browser trusts. It is the setting for the rehearsal; production is ALPHA_ACME_STAGING=no (DEPLOYMENT_RUNBOOK.md section 6)."
elif ! command -v docker >/dev/null 2>&1; then
    unknown tls "no docker on PATH; the served certificate is asked of the acme image."
else
    CERT_ARGS=(--env-file "$ENV_FILE" --file "$COMPOSE_FILE")
    while IFS= read -r overlay; do
        [ -z "$overlay" ] || CERT_ARGS+=(--file "$overlay")
    done < <(. "$LISTENERS_LIB" && listeners_overlay_files "$HERE" "$CERT_NAME" no no)
    CERT_STATUS=0
    CERT_OUTPUT="$(docker compose "${CERT_ARGS[@]}" run --rm --no-deps -T \
        --entrypoint /usr/local/bin/check-served.sh acme "$CERT_NAME" proxy:8443 14 production 2>&1)" || CERT_STATUS=$?
    case "$CERT_STATUS" in
        0) ok tls "$(printf '%s\n' "$CERT_OUTPUT" | grep '^served-certificate:' | tail -1)" ;;
        10|11|12|13)
            finding tls "the certificate served for $CERT_NAME is not acceptable (exit $CERT_STATUS). check-served.sh's own line:"
            printf '%s\n' "$CERT_OUTPUT" | grep '^served-certificate:' | sed 's/^/    /' ;;
        *)
            unknown tls "the served certificate could not be asked (exit $CERT_STATUS); raw output:"
            printf '%s\n' "$CERT_OUTPUT" | sed 's/^/    /' ;;
    esac
fi
echo
# <<< check: tls

# >>> check: plain-http
# `R-146s`: three listeners, and the one that must never carry the application in clear text is public.
# `ALPHA_BIND_ADDRESS` (`D-49`) governs the plain APPLICATION listener and its safe default is loopback;
# publishing it is checkable from the env file.
#
# With a certificate name the second question is the challenge listener on public port 80: it must answer
# with a redirect to HTTPS and with nothing from the application. The probe asks it for an application path;
# `301` to an `https://` address is the right answer, `401` (the application's own answer, which
# `deploy.sh`'s `proxy-answers` guard looks for on the LOOPBACK port) means port 80 reaches the application,
# and nothing answering means this command cannot say. Without a name there is no challenge listener, and the
# reading is the one this check always had: whether the published port is off this host, and the honest
# statement that nothing here closes plain HTTP once it is published (`nginx.conf` carries no redirect, and the
# `proxy-answers` guard wants `401` on that port).
BIND="$(configured ALPHA_BIND_ADDRESS)"
[ -n "$BIND" ] || BIND=127.0.0.1
case "$BIND" in
    127.0.0.1|::1|localhost) BIND_PUBLIC=no ;;
    *) BIND_PUBLIC=yes ;;
esac
CHALLENGE_PORT="$(configured ALPHA_ACME_HTTP_PORT)"
[ -n "$CHALLENGE_PORT" ] || CHALLENGE_PORT=80
if [ "$BIND_PUBLIC" = yes ]; then
    finding plain-http "ALPHA_BIND_ADDRESS is $BIND, publishing the plain APPLICATION listener off this host. With a certificate name deploy.sh refuses this; without one, nothing in this repository closes plain HTTP once published -- publish only behind a firewall you have verified reaches Docker's chains (D-49), serving TLS."
elif [ -z "$CERT_NAME" ]; then
    ok plain-http "ALPHA_BIND_ADDRESS is $BIND; plain HTTP is not reachable off this host, so there is nothing published to close."
elif ! command -v curl >/dev/null 2>&1; then
    unknown plain-http "no curl on PATH; the challenge listener cannot be asked."
else
    CHALLENGE_ANSWER="$(curl -s -o /dev/null -m 10 -w '%{http_code} %{redirect_url}' \
        "http://127.0.0.1:$CHALLENGE_PORT/api/v1/openapi.json" || true)"
    case "$CHALLENGE_ANSWER" in
        "301 https://"*)
            ok plain-http "ALPHA_BIND_ADDRESS is $BIND, and the challenge listener on port $CHALLENGE_PORT answers an application path with a redirect to HTTPS ($CHALLENGE_ANSWER)." ;;
        "000"*|"")
            unknown plain-http "nothing answered on 127.0.0.1:$CHALLENGE_PORT, the challenge listener; is the stack up with its ACME overlay? It cannot be judged." ;;
        *)
            finding plain-http "the challenge listener on port $CHALLENGE_PORT answered an application path with '$CHALLENGE_ANSWER', not a redirect to HTTPS. Port 80 must serve the ACME webroot and a redirect and reach no application route (R-146s)." ;;
    esac
fi
echo
# <<< check: plain-http

# The one subprocess both `provider-mode` and `cost-ceiling` read: `AppSettings.load()`
# itself, the composition root's own validation, fed the values these two files actually
# configure. Computed once, outside either check's marker block, so each block can be
# deleted independently without disturbing the other's evidence.
#
# ONE python, this repository's own `.venv` -- never a bare `python3`. `DEPLOYMENT_RUNBOOK.md`
# section 1 promises this host bash/docker/curl/sed/git and explicitly does not promise
# python3; the driver below therefore does its own small NAME=VALUE read of the two env
# files (the same shape `configured()` above reads, in python rather than sed, because it
# needs a dict to hand `load()`) rather than shelling out to a second interpreter.
PROVIDER_UNREADABLE=""
PROVIDER_OUTPUT=""
if [ ! -x "$PYTHON" ]; then
    PROVIDER_UNREADABLE="no $PYTHON; run make bootstrap first. Neither the provider mode nor the cost ceiling could be read the way the application itself reads them."
elif [ ! -r "$ENV_FILE" ]; then
    PROVIDER_UNREADABLE="no $ENV_FILE to read."
else
    SETTINGS_DRIVER='
import re, sys
from auditmanager.bootstrap.settings import load, ConfigurationError

PATTERN = re.compile(r"^[ \t]*(?:export[ \t]+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
#: chr(34)/chr(39) rather than a literal quote character: this whole driver is embedded in
#: a single-quoted bash string, and a literal `'"'"'` would end it.
QUOTE_CHARS = (chr(34), chr(39))
NAMES = (
    "DATABASE_URL", "S3_ENDPOINT_URL", "S3_REGION", "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY", "S3_BUCKET", "AUDITMANAGER_API_TOKEN",
    "AUDITMANAGER_PROVIDER_MODE", "AUDITMANAGER_PROVIDER_SOURCE",
    "AUDITMANAGER_SECRETS_PUBLIC_KEYS", "AUDITMANAGER_SECRETS_ACTIVE_KID",
)
PROVIDER_NAMES = (
    "AUDITMANAGER_RUN_COST_CEILING_USD", "AUDITMANAGER_MODEL_ID", "ANTHROPIC_API_KEY",
    "PROXY_LLM_BASE_URL", "PROXY_LLM_TOKEN", "PROXY_LLM_MODEL", "AUDITMANAGER_SECRETS_KEYS",
)
STUBS = ("", "proxy", "default", "auto")


def read(path, wanted):
    found = {}
    try:
        handle = open(path, encoding="utf-8")
    except OSError:
        return found
    with handle:
        for line in handle:
            m = PATTERN.match(line.rstrip("\n"))
            if not m or m.group(1) not in wanted:
                continue
            value = m.group(2).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in QUOTE_CHARS:
                value = value[1:-1]
            found[m.group(1)] = value
    return found


env = {}
env.update(read(sys.argv[1], NAMES))
env.update(read(sys.argv[2], PROVIDER_NAMES))
# This check models the worker, the only process that reads provider.env. The API token is
# checked separately and never reaches that process.
env.pop("AUDITMANAGER_API_TOKEN", None)
env["EXECUTION_ROLE"] = "worker"
try:
    settings = load(env)
except ConfigurationError as exc:
    print("CONFIG-ERROR: %s" % exc)
    sys.exit(1)
print("MODE=%s" % settings.provider_mode)
print("CEILING=%s" % settings.run_cost_ceiling_usd)
# `EXEC-HTTP-01` (R-143): the provider source, the key ring and the public keys, read the way the
# application reads them -- the ring is never printed, only whether the pieces agree.
print("SOURCE=%s" % settings.provider_source)
private = settings.secrets_private_ring
public = settings.secrets_public_ring
if settings.provider_source == "database":
    if env.get("PROXY_LLM_BASE_URL", "").strip() and env.get("PROXY_LLM_MODEL", "").strip().lower() in STUBS:
        print("EXECUTOR-FINDING: the baseline PROXY_LLM_MODEL is a gateway stub; set the explicit model the gateway reports before worker startup")
    if private is None:
        print("EXECUTOR-FINDING: the source is database but the worker holds no private ring (AUDITMANAGER_SECRETS_KEYS in provider.env); no key can be opened")
    if public is None:
        print("EXECUTOR-FINDING: the source is database but the api holds no public key (AUDITMANAGER_SECRETS_PUBLIC_KEYS and AUDITMANAGER_SECRETS_ACTIVE_KID in alpha.env); no key can be set")
    if private is not None and public is not None:
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        for kid, key in public.keys.items():
            mine = private.keys.get(kid)
            same = mine is not None and mine.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw) == key.public_bytes(Encoding.Raw, PublicFormat.Raw)
            if not same:
                print("EXECUTOR-FINDING: public key %s has no matching private key in the worker ring; keys sealed to it cannot be opened" % kid)
        if public.active_kid not in private.keys:
            print("EXECUTOR-FINDING: the active key id %s is not in the worker ring" % public.active_kid)
elif settings.provider_mode == "proxy" and env.get("PROXY_LLM_MODEL", "").strip().lower() in STUBS:
    print("EXECUTOR-FINDING: PROXY_LLM_MODEL is unset or a gateway stub; since EXEC-HTTP-01 every run fails closed (R-133) until the explicit model name the gateway reports is set")
'
    # `PYTHONPATH` carries the repository ROOT's `src/`, absolute -- not the relative "src"
    # `check.py`'s own docstring uses, which only resolves from the repository root.
    # `readiness.sh`, unlike `deploy.sh`, is not documented as run-from-root only, so this
    # does not depend on the caller's working directory.
    PROVIDER_OUTPUT="$(
        PYTHONPATH="$REPO/src" "$PYTHON" -c "$SETTINGS_DRIVER" "$ENV_FILE" "$PROVIDER_ENV_FILE" 2>&1 || true
    )"
fi

# >>> check: provider-mode
# `AUDITMANAGER_PROVIDER_MODE` reused, not re-derived: `AppSettings.load()` IS the check
# that decides whether the api container starts. `recorded` (the shipped default) plays
# fixtures and never spends money or calls a model, which is right for every stack this
# programme has driven so far -- and is exactly step 7, "connect a real provider", the
# owner's (GO_PATH row 7), left undone.
if [ -n "$PROVIDER_UNREADABLE" ]; then
    unknown provider-mode "$PROVIDER_UNREADABLE"
elif printf '%s\n' "$PROVIDER_OUTPUT" | grep -q '^CONFIG-ERROR:.*AUDITMANAGER_PROVIDER_MODE'; then
    finding provider-mode "$(printf '%s\n' "$PROVIDER_OUTPUT" | grep '^CONFIG-ERROR:' | head -1 | sed 's/^CONFIG-ERROR: //')"
elif printf '%s\n' "$PROVIDER_OUTPUT" | grep -q '^MODE='; then
    MODE="$(printf '%s\n' "$PROVIDER_OUTPUT" | sed -n 's/^MODE=//p')"
    if [ "$MODE" = recorded ]; then
        finding provider-mode "AUDITMANAGER_PROVIDER_MODE is 'recorded': fixtures only, no real model call is made and none can be. Connecting a real provider is step 7 and it is the owner's (GO_PATH row 7)."
    else
        ok provider-mode "AUDITMANAGER_PROVIDER_MODE is '$MODE' and the composition root's own settings loader accepted the credential it needs."
    fi
elif printf '%s\n' "$PROVIDER_OUTPUT" | grep -q '^CONFIG-ERROR:'; then
    unknown provider-mode "the settings loader refused to start for an unrelated reason before AUDITMANAGER_PROVIDER_MODE could be confirmed: $(printf '%s\n' "$PROVIDER_OUTPUT" | grep '^CONFIG-ERROR:' | head -1)"
else
    unknown provider-mode "the settings loader's output matched neither MODE= nor a CONFIG-ERROR; raw output:"
    printf '%s\n' "$PROVIDER_OUTPUT" | sed 's/^/    /'
fi
echo
# <<< check: provider-mode

# >>> check: cost-ceiling
# `AUDITMANAGER_RUN_COST_CEILING_USD` reused the same way, from the same call. `OD-03`'s
# default is USD 1.00 when unset -- `AppSettings.load()`'s own default, quoted here rather
# than repeated as a second literal.
if [ -n "$PROVIDER_UNREADABLE" ]; then
    unknown cost-ceiling "$PROVIDER_UNREADABLE"
elif printf '%s\n' "$PROVIDER_OUTPUT" | grep -q '^CONFIG-ERROR:.*AUDITMANAGER_RUN_COST_CEILING_USD'; then
    finding cost-ceiling "$(printf '%s\n' "$PROVIDER_OUTPUT" | grep '^CONFIG-ERROR:' | head -1 | sed 's/^CONFIG-ERROR: //')"
elif printf '%s\n' "$PROVIDER_OUTPUT" | grep -q '^CEILING='; then
    CEILING="$(printf '%s\n' "$PROVIDER_OUTPUT" | sed -n 's/^CEILING=//p')"
    ok cost-ceiling "the run cost ceiling resolves to \$$CEILING."
elif printf '%s\n' "$PROVIDER_OUTPUT" | grep -q '^CONFIG-ERROR:'; then
    unknown cost-ceiling "the settings loader refused to start for an unrelated reason before the ceiling could be confirmed: $(printf '%s\n' "$PROVIDER_OUTPUT" | grep '^CONFIG-ERROR:' | head -1)"
else
    unknown cost-ceiling "the settings loader's output matched neither CEILING= nor a CONFIG-ERROR; raw output:"
    printf '%s\n' "$PROVIDER_OUTPUT" | sed 's/^/    /'
fi
echo
# <<< check: cost-ceiling

# >>> check: executor-source
# `EXEC-HTTP-01` (R-143): where a run's model adapter comes from, and whether the key ring that
# seals a connection's key is whole. Reuses `AppSettings.load()` like the two checks above. Under
# `environment` it asks the one thing that changed for the stand: `PROXY_LLM_MODEL` must name the
# model the gateway reports (R-133), or every run fails closed. Under `database` it asks that the
# api holds a public key, the worker holds the private ring and the two agree.
if [ -n "$PROVIDER_UNREADABLE" ]; then
    unknown executor-source "$PROVIDER_UNREADABLE"
elif printf '%s\n' "$PROVIDER_OUTPUT" | grep -q '^CONFIG-ERROR:.*\(AUDITMANAGER_PROVIDER_SOURCE\|AUDITMANAGER_SECRETS\)'; then
    finding executor-source "$(printf '%s\n' "$PROVIDER_OUTPUT" | grep '^CONFIG-ERROR:' | head -1 | sed 's/^CONFIG-ERROR: //')"
elif printf '%s\n' "$PROVIDER_OUTPUT" | grep -q '^EXECUTOR-FINDING:'; then
    finding executor-source "$(printf '%s\n' "$PROVIDER_OUTPUT" | grep '^EXECUTOR-FINDING:' | head -1 | sed 's/^EXECUTOR-FINDING: //')"
elif printf '%s\n' "$PROVIDER_OUTPUT" | grep -q '^SOURCE='; then
    SOURCE="$(printf '%s\n' "$PROVIDER_OUTPUT" | sed -n 's/^SOURCE=//p')"
    ok executor-source "AUDITMANAGER_PROVIDER_SOURCE is '$SOURCE' and the settings loader accepted the key ring it needs."
elif printf '%s\n' "$PROVIDER_OUTPUT" | grep -q '^CONFIG-ERROR:'; then
    unknown executor-source "the settings loader refused to start for an unrelated reason before the provider source could be confirmed: $(printf '%s\n' "$PROVIDER_OUTPUT" | grep '^CONFIG-ERROR:' | head -1)"
else
    unknown executor-source "the settings loader's output matched neither SOURCE= nor a CONFIG-ERROR; raw output:"
    printf '%s\n' "$PROVIDER_OUTPUT" | sed 's/^/    /'
fi
echo
# <<< check: executor-source

# >>> check: off-host-backup
# Step 8's off-host half. `infra/deploy/reset.sh` dumps and verifies the dump before it
# drops anything, but the dump lands under `$ALPHA_DUMP_ROOT` on THIS host's own disk.
# Moving a copy off this host is not automated anywhere in this tree --
# `DEPLOYMENT_RUNBOOK.md` section 5 says so in its own words ("no off-host backup target
# ... not automated here") -- and GO_PATH row 8 names the destination as the owner's. This
# always reports the finding rather than inventing a variable this tree cannot act on: a
# check that could be made to say OK by setting an unread name would be the silent fallback
# AGENTS.md section 4 forbids, in the one place this command exists to prevent it.
finding off-host-backup "no destination exists in this repository. reset.sh's dumps land under \$ALPHA_DUMP_ROOT on this host's own disk (default: $HERE/dumps); getting a copy off this host is not automated (DEPLOYMENT_RUNBOOK.md section 5). The destination is the owner's (GO_PATH row 8)."
echo
# <<< check: off-host-backup

echo "readiness.sh: $FINDINGS finding(s), $UNKNOWNS unknown, 8 checks."
echo "readiness.sh: this is a report, not a gate (R-46). Each finding is a register row for the owner's ruling."

if [ "$UNKNOWNS" -gt 0 ]; then
    exit 2
elif [ "$FINDINGS" -gt 0 ]; then
    exit 1
fi
exit 0
