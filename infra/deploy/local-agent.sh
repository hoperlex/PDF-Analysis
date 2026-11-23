#!/usr/bin/env bash
# `LOCAL-AGENT-01` -- connect the deploy server's OWN codex and claude subscription logins to the stand it serves.
#
#   sudo infra/deploy/local-agent.sh [--env-file PATH] [--login-user NAME] [--name NAME] [--actor LOGIN] [--reenroll] connect
#   sudo infra/deploy/local-agent.sh [--env-file PATH] [--login-user NAME] [--name NAME] status
#   sudo infra/deploy/local-agent.sh [--env-file PATH] disconnect
#
# THE OWNER'S DECISIONS (2026-11-20, by poll): no new screen -- the deploy server appears in «Исполнители» as an ordinary host card,
# ENABLED at once, and its existing «Использовать» switch is the checkbox; `deploy.sh` runs `connect` by itself after every deploy
# when `ALPHA_LOCAL_AGENT=auto` (see there); the agent runs as the account that OWNS the logins -- usually root, whose VS Code
# extensions carry the signed-in clients -- so nobody signs in again.
#
# WHAT `connect` DOES, IN ORDER (it is idempotent: a second run changes nothing but the agent's code when the stand's package moved):
#
#   1. finds the two clients of the login account (`local_agent_clis.py`): a binary inside a VS Code extension gets a wrapper in
#      /opt/pdf-analysis-cli/bin that always runs the newest one; a binary in the usual directories is used as it is;
#   2. asks the agent's own `detect.py --host`, AS THAT ACCOUNT, which of them is signed in. Only a SUBSCRIPTION login counts
#      (`access=subscription auth=valid`): with none, nothing is connected, the script says so and exits 0;
#   3. refuses (exit 3) when an agent of ANOTHER stand is installed on this machine: one machine, one agent, and this script does not
#      take over somebody else's (the adm1 case: its agent serves the production stand);
#   4. asks the stand, inside the running `api` container (`python -m auditmanager.bootstrap.local_host`), for its agent package
#      and -- only when no agent of this stand is installed yet, or with --reenroll -- for a one-time enrollment secret of the host
#      card (`--name`, default «Этот сервер»), issued in the name of an administrator (`--actor`, default the first one);
#   5. downloads that package from the stand over the loopback interface, checks its sha256, and runs its own `install.sh` with
#      `--login-user` and `--max-images 8` (a block task carries up to eight page crops). The agent talks to the stand at
#      http://127.0.0.1:<ALPHA_HTTP_PORT>: the stack's proxy on this machine, so nothing leaves it and no certificate is needed;
#   6. waits up to 90 seconds for the agent's first report and prints the models the stand now lists for the card.
#
# THE SECRET: it is read from the module's one-line answer into a variable, handed to `install.sh` only through its environment
# (as the copyable command of path B does), and never printed, logged or written. The stand keeps only its hash.
#
# A HOST REMOVED ON THE STAND IS NOT RESURRECTED. When the card is archived in «Исполнители», the stand refuses the agent's token
# and the service stops (exit 3 of the agent). A later `connect` sees an installed agent, does NOT enroll again, and says that
# `--reenroll` connects it anew. To stop the deploy from connecting at all: `ALPHA_LOCAL_AGENT=off` in the environment file.
#
# `disconnect` removes the agent (`install.sh --uninstall`) and the wrappers of ours -- only an agent of THIS stand: one installed for
# another stand is refused, as in `connect`; the card stays on the stand until it is archived there. `status` changes nothing.
#
# Settings, from the environment file (read as data, never sourced), each overridden by its option:
#   ALPHA_LOCAL_AGENT_USER   the account that holds the logins (default root)
#   ALPHA_LOCAL_AGENT_NAME   the name of the host card (default «Этот сервер»)
#   ALPHA_LOCAL_AGENT_ACTOR  the administrator the grant is issued in the name of (default: the first one)
#
# EXIT CODES: 0 done (connected, or nothing found to connect); 2 usage; 3 refused (nothing changed); 4 failed; 77 not root.

set -Eeuo pipefail
umask 022

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
COMPOSE_FILE="$HERE/compose.server.yml"
ENV_FILE="${ALPHA_ENV_FILE:-$HERE/env/alpha.env}"
DETECT="$REPO/tools/executor-runner/detect.py"
CLIS_HELPER="$HERE/local_agent_clis.py"
WRAPPER_DIR=/opt/pdf-analysis-cli/bin
AGENT_CONF=/etc/pdf-analysis-agent/agent.toml
AGENT_ENV=/etc/pdf-analysis-agent/agent.env
AGENT_INSTALLER=/opt/pdf-analysis-agent/install.sh
SERVICE=pdf-analysis-agent.service
MAX_IMAGES=8
REPORT_WAIT_SECONDS=90

say() { printf 'local-agent.sh: %s\n' "$*"; }
refuse() {
    printf 'local-agent.sh: REFUSED: %s\n' "$1" >&2
    shift
    local line
    for line in "$@"; do printf '  %s\n' "$line" >&2; done
    exit 3
}
fail() {
    printf 'local-agent.sh: FAILED: %s\n' "$*" >&2
    exit 4
}
usage() { sed -n '2,/^$/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

COMMAND=""
OPT_USER=""
OPT_NAME=""
OPT_ACTOR=""
REENROLL=0
while [ $# -gt 0 ]; do
    case "$1" in
        --env-file | --login-user | --name | --actor)
            [ $# -ge 2 ] || { echo "local-agent.sh: $1 needs a value" >&2; exit 2; }
            case "$1" in
                --env-file) ENV_FILE="$2" ;;
                --login-user) OPT_USER="$2" ;;
                --name) OPT_NAME="$2" ;;
                --actor) OPT_ACTOR="$2" ;;
            esac
            shift 2 ;;
        --reenroll) REENROLL=1; shift ;;
        -h | --help) usage; exit 0 ;;
        connect | status | disconnect)
            [ -z "$COMMAND" ] || { echo "local-agent.sh: one command at a time" >&2; exit 2; }
            COMMAND="$1"; shift ;;
        *) echo "local-agent.sh: unknown argument ${1%%=*} (see --help)" >&2; exit 2 ;;
    esac
done
[ -n "$COMMAND" ] || { echo "local-agent.sh: name a command: connect, status or disconnect (see --help)" >&2; exit 2; }

if [ "$(id -u)" -ne 0 ]; then
    echo "local-agent.sh: run it as root (it installs a systemd service): sudo $0 $COMMAND" >&2
    exit 77
fi

# Read a setting of the environment file as DATA; the file is never sourced.
configured() {
    [ -r "$ENV_FILE" ] || return 0
    sed -n "s/^[[:space:]]*\(export[[:space:]]\+\)\?$1=//p" "$ENV_FILE" | tail -1 \
        | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/"
}

LOGIN_USER="${OPT_USER:-$(configured ALPHA_LOCAL_AGENT_USER)}"
LOGIN_USER="${LOGIN_USER:-root}"
HOST_NAME="${OPT_NAME:-$(configured ALPHA_LOCAL_AGENT_NAME)}"
HOST_NAME="${HOST_NAME:-Этот сервер}"
ACTOR="${OPT_ACTOR:-$(configured ALPHA_LOCAL_AGENT_ACTOR)}"

[[ "$LOGIN_USER" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]] || { echo "local-agent.sh: the login user must be a lower-case account name" >&2; exit 2; }
PASSWD="$(getent passwd "$LOGIN_USER" || true)"
[ -n "$PASSWD" ] || refuse "there is no account $LOGIN_USER on this machine (ALPHA_LOCAL_AGENT_USER / --login-user)."
LOGIN_HOME="$(printf '%s\n' "$PASSWD" | cut -d: -f6)"
CLI_DIRS="$WRAPPER_DIR:$LOGIN_HOME/.local/bin:$LOGIN_HOME/.npm-global/bin:/usr/local/bin:/usr/bin:/bin:/snap/bin"

installed_origin() { [ -r "$AGENT_CONF" ] && sed -n 's/^origin = "\(.*\)"$/\1/p' "$AGENT_CONF" | head -n 1 || true; }
has_token() { [ -r "$AGENT_ENV" ] && grep -q '^PDF_ANALYSIS_RUNNER_TOKEN=.' "$AGENT_ENV"; }

# The clients this account is signed in to, as the agent itself will see them (its `detect.py`, as the account, its HOME, the dirs).
signed_in() {
    runuser -u "$LOGIN_USER" -- /usr/bin/env -i "HOME=$LOGIN_HOME" LANG=C.UTF-8 "PDF_ANALYSIS_CLI_DIRS=$CLI_DIRS" \
        python3 -I "$DETECT" --host --key-file /nonexistent/pdf-analysis-local-agent.keys 2>/dev/null \
        | grep -E '^(claude_code|codex) ' || true
}

compose() { docker compose --env-file "$ENV_FILE" --file "$COMPOSE_FILE" "$@"; }
stand() { compose exec -T api python -m auditmanager.bootstrap.local_host "$@" </dev/null; }
member() {  # member NAME: the value of NAME in the JSON line on stdin (a string or a number), empty when absent
    python3 -I -c 'import json,sys; v=json.loads(sys.stdin.read() or "{}").get(sys.argv[1]); print("" if v is None else v)' "$1"
}

# ------------------------------------------------------------------------------------------------- status

if [ "$COMMAND" = status ]; then
    say "account $LOGIN_USER (home $LOGIN_HOME); clients:"
    python3 -I "$CLIS_HELPER" --home "$LOGIN_HOME" --out "$WRAPPER_DIR" --dry-run | sed 's/^/  /'
    say "signed in, as the agent will see it:"
    found="$(signed_in)"
    printf '%s\n' "${found:-(nothing)}" | sed 's/^/  /'
    origin="$(installed_origin)"
    if [ -n "$origin" ]; then
        say "agent installed for $origin; token $(has_token && echo present || echo absent); service $(systemctl is-active "$SERVICE" 2>/dev/null || true)"
    else
        say "no agent installed on this machine"
    fi
    if [ -r "$ENV_FILE" ] && view="$(stand show --name "$HOST_NAME" 2>/dev/null)"; then
        say "the stand's card «$HOST_NAME»: $view"
    else
        say "the stand could not be asked (is the stack up? is $ENV_FILE the right environment file?)"
    fi
    exit 0
fi

# --------------------------------------------------------------------------------------------- disconnect

if [ "$COMMAND" = disconnect ]; then
    # Only THIS stand's agent is removed: an agent installed for another stand (adm1's serves production) is somebody else's.
    origin="$(installed_origin)"
    port="$(configured ALPHA_HTTP_PORT)"
    if [ -n "$origin" ] && [ "$origin" != "http://127.0.0.1:$port" ]; then
        refuse "the agent installed on this machine serves another stand ($origin), not this one (http://127.0.0.1:${port:-?})." \
               "local-agent.sh removes only the agent it connected. Pass the right --env-file, or remove that agent by hand."
    fi
    if [ -x "$AGENT_INSTALLER" ]; then
        bash "$AGENT_INSTALLER" --uninstall
    else
        say "no agent installed on this machine"
    fi
    python3 -I -B - "$WRAPPER_DIR" "$CLIS_HELPER" <<'PY'
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("local_agent_clis", sys.argv[2])
helper = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helper
spec.loader.exec_module(helper)
for name in helper.NAMES:
    target = Path(sys.argv[1]) / name
    if target.exists() and helper._ours(target):
        target.unlink()
        print(f"local-agent.sh: removed {target}")
PY
    say "the card «$HOST_NAME» stays on the stand until it is archived in «Исполнители»."
    say "set ALPHA_LOCAL_AGENT=off in $ENV_FILE, or the next deploy connects this machine again."
    exit 0
fi

# ------------------------------------------------------------------------------------------------ connect

[ -r "$ENV_FILE" ] || refuse "the environment file $ENV_FILE cannot be read." "Pass --env-file, as to deploy.sh."
[ -r "$DETECT" ] && [ -r "$CLIS_HELPER" ] || refuse "this checkout lacks $DETECT or $CLIS_HELPER."
command -v docker > /dev/null 2>&1 || refuse "docker is not installed here: the stand is asked through its api container."
command -v systemctl > /dev/null 2>&1 || refuse "systemd (systemctl) is required for the agent's service."
for tool in curl sha256sum tar runuser python3; do
    command -v "$tool" > /dev/null 2>&1 || refuse "$tool is required."
done

HTTP_PORT="$(configured ALPHA_HTTP_PORT)"
BIND="$(configured ALPHA_BIND_ADDRESS)"
[[ "$HTTP_PORT" =~ ^[0-9]{1,5}$ ]] || refuse "ALPHA_HTTP_PORT in $ENV_FILE is not a port number."
case "${BIND:-127.0.0.1}" in
    127.0.0.1 | 0.0.0.0 | localhost) ;;
    *) refuse "ALPHA_BIND_ADDRESS is $BIND: the stack's proxy does not listen on the loopback interface, which the local agent uses." ;;
esac
ORIGIN="http://127.0.0.1:$HTTP_PORT"

say "account $LOGIN_USER (home $LOGIN_HOME); looking for its codex and claude"
python3 -I "$CLIS_HELPER" --home "$LOGIN_HOME" --out "$WRAPPER_DIR" | sed 's/^/  /'
FOUND="$(signed_in)"
printf '%s\n' "${FOUND:-(no client found)}" | sed 's/^/  /'
SUBSCRIPTIONS="$(printf '%s\n' "$FOUND" | grep -E ' access=subscription auth=valid( |$)' || true)"
if [ -z "$SUBSCRIPTIONS" ]; then
    say "no codex or claude signed in with a SUBSCRIPTION for $LOGIN_USER on this machine: nothing to connect."
    if [ -n "$(installed_origin)" ]; then say "the agent already installed here is left as it is."; fi
    exit 0
fi

ORIGIN_NOW="$(installed_origin)"
if [ -n "$ORIGIN_NOW" ] && [ "$ORIGIN_NOW" != "$ORIGIN" ]; then
    refuse "an agent of another stand is installed on this machine ($ORIGIN_NOW)." \
           "One machine runs one agent, and this script does not take another stand's agent over." \
           "Remove it first (sudo bash $AGENT_INSTALLER --uninstall) if this machine is to serve $ORIGIN instead."
fi

PACKAGE_LINE="$(stand package)" || fail "the stand did not describe its agent package (is the stack up? see the line above)."
VERSION="$(printf '%s' "$PACKAGE_LINE" | member package_version)"
SHA256="$(printf '%s' "$PACKAGE_LINE" | member package_sha256)"
[[ "$VERSION" =~ ^[0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,4}$ ]] && [[ "$SHA256" =~ ^[0-9a-f]{64}$ ]] \
    || fail "the stand's package answer is not a version and a sha256."

GRANT=""
if [ -z "$ORIGIN_NOW" ] || ! has_token || [ "$REENROLL" -eq 1 ]; then
    say "issuing a one-time enrollment of the card «$HOST_NAME» on the stand"
    enroll=(enroll --name "$HOST_NAME" --origin "$ORIGIN")
    if [ -n "$ACTOR" ]; then enroll+=(--actor "$ACTOR"); fi
    ENROLL_LINE="$(stand "${enroll[@]}")" || fail "the stand did not issue the enrollment (its reason is the line above)."
    GRANT="$(printf '%s' "$ENROLL_LINE" | member secret)"
    say "issued for the card $(printf '%s' "$ENROLL_LINE" | member host_id), in the name of $(printf '%s' "$ENROLL_LINE" | member actor_login)"
    ENROLL_LINE=""
    [ -n "$GRANT" ] || fail "the stand's enrollment answer carries no secret."
else
    say "an agent of this stand is installed: its token is kept and only its code follows the stand's package"
fi

WORK="$(mktemp -d)"
trap 'rm -rf -- "$WORK"' EXIT
curl -fsS --max-time 60 -o "$WORK/agent.tar.gz" "$ORIGIN/api/v1/runner/agent-package/$VERSION" \
    || fail "the package $VERSION could not be downloaded from $ORIGIN."
printf '%s  %s\n' "$SHA256" "$WORK/agent.tar.gz" | sha256sum -c --quiet - || fail "the downloaded package does not have the stand's sha256."
mkdir "$WORK/pkg"
tar -xzf "$WORK/agent.tar.gz" -C "$WORK/pkg"

INSTALL_STATUS=0
(
    cd "$WORK/pkg"
    if [ -n "$GRANT" ]; then
        AUDITMANAGER_ENROLLMENT_SECRET="$GRANT" AUDITMANAGER_STAND_ORIGIN="$ORIGIN" \
            bash install.sh --login-user "$LOGIN_USER" --max-images "$MAX_IMAGES"
    else
        bash install.sh --login-user "$LOGIN_USER" --max-images "$MAX_IMAGES"
    fi
) || INSTALL_STATUS=$?
GRANT=""
if [ "$INSTALL_STATUS" -ne 0 ]; then
    if [ -n "$ORIGIN_NOW" ] && [ "$REENROLL" -eq 0 ]; then
        fail "install.sh ended with $INSTALL_STATUS. If the stand refused the agent's token (the card was removed in «Исполнители»)," \
             "connect it anew with: sudo $0 --env-file $ENV_FILE --reenroll connect"
    fi
    fail "install.sh ended with $INSTALL_STATUS (its reason is above)."
fi

say "waiting for the agent's first report (up to $REPORT_WAIT_SECONDS s)"
deadline=$(( $(date +%s) + REPORT_WAIT_SECONDS ))
VIEW=""
while [ "$(date +%s)" -lt "$deadline" ]; do
    VIEW="$(stand show --name "$HOST_NAME" 2>/dev/null || true)"
    if printf '%s' "$VIEW" | python3 -I -c 'import json,sys; h=json.loads(sys.stdin.read() or "{}").get("host") or {}; sys.exit(0 if h.get("models") else 1)'; then
        break
    fi
    sleep 5
done
printf '%s' "$VIEW" | python3 -I -c '
import json, sys
host = (json.loads(sys.stdin.read() or "{}") or {}).get("host")
if not host:
    print("local-agent.sh: the card is not on the stand yet; it appears once the agent has reported")
    sys.exit(0)
state = "enabled" if host.get("enabled") else "switched off («Использовать»)"
models = ", ".join(sorted("%s (%s)" % (m["model_id"], m["provider"]) for m in host.get("models", []))) or "none usable yet (the agent checks each model with a minimal call; give it a few minutes)"
print("local-agent.sh: card «%s» %s, %s; models: %s" % (host.get("display_name"), host.get("state"), state, models))
'
say "connected: the deploy server's own subscriptions serve the stand at $ORIGIN"
