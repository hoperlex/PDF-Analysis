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
# drives every one of the six checks below to both a clean answer and a finding, and for the
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
# `tls`, `plain-http` and `off-host-backup` have no existing module to consult: nothing in
# this tree validates a certificate pair, a bind address, or an off-host destination today,
# so those three are read directly against the files and values `docs/program/
# DEPLOYMENT_RUNBOOK.md` §1 and §6 and `infra/deploy/proxy/enable-tls.sh` already document.
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
#: Overridable the same way, for the same reason: `tests/integration/composition/
#: test_readiness_command.py` drives the `tls` check to both answers without ever writing
#: into this clone's own `proxy/tls/`.
TLS_DIR="${ALPHA_TLS_DIR:-$HERE/proxy/tls}"
PYTHON="$REPO/.venv/bin/python"

usage() {
    cat >&2 <<'USAGE'
usage: readiness.sh [--env-file <path>] [--provider-env-file <path>] [--tls-dir <path>]

  --env-file <path>           default: infra/deploy/env/alpha.env
  --provider-env-file <path>  default: infra/deploy/env/provider.env
  --tls-dir <path>            default: infra/deploy/proxy/tls

Reports on six publication-readiness questions and registers each finding. Refuses nothing
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
        --tls-dir) TLS_DIR="${2:-}"; shift 2 ;;
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

# >>> check: tls
# Step 4's software half. `infra/deploy/proxy/enable-tls.sh` installs the TLS server block
# only when both files are present AND non-empty (`[ -s "$CERT" ]`); this asks the same
# question the same way, from the host, before anything is brought up. The domain and the
# certificate itself are the owner's -- GO_PATH row 4 -- this only reports whether the pair
# that would activate TLS is on disk.
CERT="$TLS_DIR/fullchain.pem"
KEY="$TLS_DIR/privkey.pem"
if [ -s "$CERT" ] && [ -s "$KEY" ]; then
    ok tls "a certificate pair is present at $TLS_DIR; enable-tls.sh installs the TLS server block on next start."
else
    finding tls "no usable certificate pair at $TLS_DIR ($CERT / $KEY missing or empty). The domain and certificate are the owner's (GO_PATH row 4); until they are there, enable-tls.sh installs nothing and the stack serves plain HTTP only."
fi
echo
# <<< check: tls

# >>> check: plain-http
# Step 4's other half, "close plain HTTP" -- and the honest answer this repository can give.
# `ALPHA_BIND_ADDRESS` (`D-49`) is what makes the published port reachable off this host at
# all; its safe default is loopback. Publishing it is checkable; CLOSING plain HTTP once
# published is not something anything in this tree can do -- `DEPLOYMENT_RUNBOOK.md` §6
# says so in its own words: "there is deliberately no redirect ... the plain port keeps
# serving in both cases", because `deploy.sh`'s own `proxy-answers` guard requires **401**
# on that port and a redirect's `301` is not 401. So this reports the one thing that is
# true either way, rather than a "closed" this codebase cannot produce.
#
# `Y2`: this line said **200** until 2026-09-29, and it is the one assertion in this file
# about another file's behaviour rather than a reading of the tree. `R-31` closed the four
# documentation routes behind a credential and moved the guard with them; a 200 there is
# now a refusal in `deploy.sh`'s own words. The conclusion survived its false premise -- a
# 301 is not 401 either -- so the operator was misled about the number and not into a
# wrong action. Read it off the guard: `sed -n '751,772p' infra/deploy/deploy.sh`.
BIND="$(configured ALPHA_BIND_ADDRESS)"
[ -n "$BIND" ] || BIND=127.0.0.1
case "$BIND" in
    127.0.0.1|::1|localhost)
        ok plain-http "ALPHA_BIND_ADDRESS is $BIND; plain HTTP is not reachable off this host, so there is nothing published to close." ;;
    *)
        finding plain-http "ALPHA_BIND_ADDRESS is $BIND, publishing plain HTTP off this host. No mechanism in this repository closes it once published -- nginx.conf carries no redirect, and deploy.sh's own proxy-answers guard requires 401 on this exact port and refuses a 200 there (DEPLOYMENT_RUNBOOK.md section 6). 'Close plain HTTP' cannot be satisfied by configuration alone; publish only behind a firewall you have verified reaches Docker's chains (D-49), serving TLS." ;;
esac
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
    "AUDITMANAGER_PROVIDER_MODE",
)
PROVIDER_NAMES = (
    "AUDITMANAGER_RUN_COST_CEILING_USD", "AUDITMANAGER_MODEL_ID", "ANTHROPIC_API_KEY",
    "PROXY_LLM_BASE_URL", "PROXY_LLM_TOKEN", "PROXY_LLM_MODEL",
)


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
try:
    settings = load(env)
except ConfigurationError as exc:
    print("CONFIG-ERROR: %s" % exc)
    sys.exit(1)
print("MODE=%s" % settings.provider_mode)
print("CEILING=%s" % settings.run_cost_ceiling_usd)
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

echo "readiness.sh: $FINDINGS finding(s), $UNKNOWNS unknown, 6 checks."
echo "readiness.sh: this is a report, not a gate (R-46). Each finding is a register row for the owner's ruling."

if [ "$UNKNOWNS" -gt 0 ]; then
    exit 2
elif [ "$FINDINGS" -gt 0 ]; then
    exit 1
fi
exit 0
