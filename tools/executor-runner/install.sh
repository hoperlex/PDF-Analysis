#!/usr/bin/env bash
# install.sh -- install, upgrade, repair or remove the PDF Analysis pull agent on Ubuntu LTS (EXEC2-AGENT-01 and
# HOSTS-AGENT-01, ADR-0026 decisions 6 and 8). The same script serves both install paths: the administrator pastes the
# copyable command (path B), or the stand's worker runs it over SSH with `sudo -n` (path A).
#
#   AUDITMANAGER_ENROLLMENT_SECRET=... AUDITMANAGER_STAND_ORIGIN=https://stand.example.org sudo \
#       --preserve-env=AUDITMANAGER_ENROLLMENT_SECRET,AUDITMANAGER_STAND_ORIGIN bash install.sh [options]
#   sudo bash install.sh --uninstall
#
# Run it from the directory the package was unpacked into. What it does, in this order:
#   1. refuses anything wrong before it changes the system (options, secret shape, package digest, Python);
#   2. creates the dedicated service user, or reuses it, and its home /var/lib/pdf-analysis-agent (0700) where
#      the CLI logins of that user live; it never copies a credential from any other account;
#   3. installs the agent under /opt/pdf-analysis-agent and writes /etc/pdf-analysis-agent/agent.toml (kept when it
#      already exists) and the 0600 environment file agent.env;
#   4. exchanges the one-time enrollment secret for a runner token by running `agent.py --enroll-only`
#      (the token goes into agent.env; the secret is never written anywhere);
#   5. installs the systemd unit and starts the service (restarts it only when something changed);
#   6. prints the steps left to the administrator: installing the CLIs for the service user if they are not there
#      and signing them in as that user, and the optional key file for direct API calls.
#
# HOST MODE (the default, no model). The agent is one process and one host token: it serves every model this host can
# reach -- the `claude` and `codex` CLIs the service user is signed in to (subscription or API login) and the API keys
# in /etc/pdf-analysis-agent/keys.env (ANTHROPIC_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY; the file must be mode 0600
# and owned by the service user, or it is ignored). No model is chosen at install: the stand's catalogue says which
# models matter, and the agent checks each with a minimal call and reports what it verified. The installer never
# creates keys.env, never reads it and never copies a key: the administrator puts the keys there, knowing that a
# document then goes to that API (a path out of the stand, D-291).
# A model given with --model (or AUDITMANAGER_AGENT_MODEL) installs the SINGLE-MODEL agent of EXEC2-AGENT-01 instead,
# bound to one connection: it declares that model, the CLI follows from it (claude-opus-5 and claude-sonnet-5 are
# answered by Claude Code, gpt-6-sol by Codex), and a model no answer command serves is refused (exit 64).
# --upgrade converts an installed single-model agent to host mode: it needs a NEW enrollment secret (the stand's
# "connect a server" command), keeps the service user, its home and every path, writes the host agent.toml (the old one is
# kept as agent.toml.pre-host), replaces the runner token only when the enrollment succeeded, and restarts the service.
#
# Inputs. The enrollment secret comes ONLY from the environment variable AUDITMANAGER_ENROLLMENT_SECRET: it is
# removed from this script's environment at once, never put on a command line, never echoed or logged, and
# reaches only the one process that exchanges it. Without it a rerun keeps the runner token already installed.
#   AUDITMANAGER_STAND_ORIGIN   the stand, https://host[:port] (or --origin); not needed on a rerun
#   AUDITMANAGER_AGENT_MODEL    single-model agent only: the model the connection pins (or --model)
#   AUDITMANAGER_AGENT_CLI      single-model agent only: claude | codex (or --cli): may only confirm what the model implies
# Options: --origin URL, --model ID, --cli NAME, --service-user NAME (default pdf-agent), --upgrade, --reconfigure
#   (write agent.toml again: host mode when no model is given and the kept file is not a single-model one, otherwise
#   the model given or the configured one), --package FILE --sha256 DIGEST (verify the archive before anything is
#   installed), --uninstall, --help.
#
# Rerun: idempotent. Files that are the same are left, an existing agent.toml and agent.env are kept (so the
# runner token and the configured mode keep working; a rerun without a model keeps the configured one, and a
# different model is applied only with --reconfigure), the service is restarted only after a change. A rerun with the same secret inside
# the 15-minute window is the stand's idempotent repeat: it revokes the token it minted before and returns a fresh
# one, and only the newest is stored (the exchange's instance id is kept in enroll-instance beside agent.env). With
# a secret the stand has already spent, or one redeemed from another host, the installed token is kept.
# --uninstall removes the service, unit, code, agent.toml and agent.env. It never touches an installed CLI or
# any login or keys.env, and leaves the service user and its home.
#
# Exit codes: 0 done; 64 usage; 65 package missing or its digest wrong; 66 a prerequisite is missing; 69 the stand
# could not be reached; 77 not root; 78 the secret or the origin is missing or refused; 1 anything else.
#
# Testing: AUDITMANAGER_INSTALL_ROOT=/some/dir puts every file under that directory, skips user, group, ownership
# and systemd work (except through stand-in commands found in AUDITMANAGER_INSTALL_SYSCMD_DIR) and honours
# AUDITMANAGER_PYTHON. It is never set on a real install.

set -euo pipefail
# A shell trace must never show the enrollment secret: tracing is switched off before the secret is read.
{ set +x; set +v; } 2>/dev/null
umask 077

say() { printf 'install.sh: %s\n' "$*"; }
warn() { printf 'install.sh: %s\n' "$*" >&2; }
die() {
    local code="$1"
    shift
    printf 'install.sh: error: %s\n' "$*" >&2
    exit "$code"
}

usage() {
    sed -n '2,/^$/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

# ---------------------------------------------------------------------------------------- options

MODE=install
ORIGIN="${AUDITMANAGER_STAND_ORIGIN-}"
CLI="${AUDITMANAGER_AGENT_CLI-}"
MODEL="${AUDITMANAGER_AGENT_MODEL-}"
SERVICE_USER=pdf-agent
PACKAGE_FILE=""
PACKAGE_SHA256=""
RECONFIGURE=0
UPGRADE=0

while [ $# -gt 0 ]; do
    case "$1" in
        --uninstall) MODE=uninstall; shift ;;
        --reconfigure) RECONFIGURE=1; shift ;;
        --upgrade) UPGRADE=1; shift ;;
        --origin | --cli | --model | --service-user | --package | --sha256)
            [ $# -ge 2 ] || die 64 "$1 needs a value"
            case "$1" in
                --origin) ORIGIN="$2" ;;
                --cli) CLI="$2" ;;
                --model) MODEL="$2" ;;
                --service-user) SERVICE_USER="$2" ;;
                --package) PACKAGE_FILE="$2" ;;
                --sha256) PACKAGE_SHA256="$2" ;;
            esac
            shift 2
            ;;
        --secret | --secret=* | --token | --token=* | --enrollment-secret | --enrollment-secret=*)
            die 64 "the enrollment secret is read only from the environment variable AUDITMANAGER_ENROLLMENT_SECRET, never from an argument"
            ;;
        -h | --help) usage; exit 0 ;;
        -*) die 64 "unknown option ${1%%=*} (see --help)" ;;
        *) die 64 "unexpected argument (see --help)" ;;
    esac
done

# The secret leaves the environment here, before any other command can inherit it.
GRANT="${AUDITMANAGER_ENROLLMENT_SECRET-}"
unset AUDITMANAGER_ENROLLMENT_SECRET

[[ "$SERVICE_USER" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]] || die 64 "--service-user must be a lower-case account name"
case "$CLI" in
    "" | claude | codex) ;;
    *) die 64 "--cli must be claude or codex" ;;
esac
if [ -n "$ORIGIN" ]; then
    [[ "$ORIGIN" =~ ^https?://[A-Za-z0-9.-]+(:[0-9]{1,5})?$ ]] \
        || die 64 "the origin must be scheme://host[:port] with no path (https:// outside a closed test network)"
fi
NEW_SECRET=0  # whether a secret was given; the guard test reads every line that names the secret itself
if [ -n "$GRANT" ]; then
    if ! [[ "$GRANT" =~ ^ame_[0-9a-z]{8}_[A-Za-z0-9_-]{43}$ ]]; then
        GRANT=""
        die 78 "the value of AUDITMANAGER_ENROLLMENT_SECRET does not have the shape of an enrollment secret"
    fi
    NEW_SECRET=1
fi

# ----------------------------------------------------------------------------------- fixed paths
# Everything this script writes is under one of these. ROOT is empty on a real install.

ROOT="${AUDITMANAGER_INSTALL_ROOT-}"
ROOT="${ROOT%/}"
SYSCMD_DIR="${AUDITMANAGER_INSTALL_SYSCMD_DIR-}"
SERVICE_NAME=pdf-analysis-agent
SERVICE_HOME=/var/lib/pdf-analysis-agent
APP_REAL=/opt/pdf-analysis-agent
APP_DIR="$ROOT$APP_REAL"
CONF_DIR="$ROOT/etc/pdf-analysis-agent"
CONF_FILE="$CONF_DIR/agent.toml"
ENV_FILE="$CONF_DIR/agent.env"
UNIT_DIR="$ROOT/etc/systemd/system"
UNIT_FILE="$UNIT_DIR/$SERVICE_NAME.service"
STATE_DIR="$ROOT$SERVICE_HOME"
TOKEN_ENV=PDF_ANALYSIS_RUNNER_TOKEN
APP_FILES=(agent.py runner_client.py detect.py host_mode.py api_answer.py codex_answer.py claude_answer.py)
KEYS_REAL=/etc/pdf-analysis-agent/keys.env
KEYS_FILE="$ROOT$KEYS_REAL"
# The models the two answer commands serve in single-model mode (claude_answer.py ALLOWED_MODELS, codex_answer.py MODEL).
CLAUDE_MODELS=(claude-opus-5 claude-sonnet-5)
CODEX_MODELS=(gpt-6-sol)
PYTHON=/usr/bin/python3
if [ -n "$ROOT" ]; then PYTHON="${AUDITMANAGER_PYTHON:-$PYTHON}"; fi

CHANGED=0
staged=""
unit_staged=""
trap 'rm -f -- "$staged" "$unit_staged"' EXIT

# A command that changes the real system. Under a test root it runs only if a stand-in of that name is in
# AUDITMANAGER_INSTALL_SYSCMD_DIR; otherwise it is reported as skipped and counts as done.
sysrun() {
    local name="$1"
    shift
    if [ -z "$ROOT" ]; then
        "$name" "$@"
    elif [ -n "$SYSCMD_DIR" ] && [ -x "$SYSCMD_DIR/$name" ]; then
        "$SYSCMD_DIR/$name" "$@"
    else
        say "[test root] skipped: $name $*"
    fi
}

need_root() {
    if [ -z "$ROOT" ] && [ "$(id -u)" -ne 0 ]; then
        die 77 "run it as root, for example: sudo bash install.sh"
    fi
}

# ----------------------------------------------------------------------------------------- remove

do_uninstall() {
    need_root
    case "$APP_DIR" in
        */opt/pdf-analysis-agent) ;;
        *) die 1 "refusing to remove an unexpected directory" ;;
    esac
    say "removing the agent, its unit, its configuration and its environment file"
    if [ -e "$UNIT_FILE" ]; then
        sysrun systemctl disable --now "$SERVICE_NAME.service" || warn "the service could not be stopped cleanly; continuing"
        rm -f -- "$UNIT_FILE"
        sysrun systemctl daemon-reload || warn "systemctl daemon-reload failed"
    fi
    rm -f -- "$ENV_FILE" "$CONF_FILE" "$CONF_FILE.pre-host" "$CONF_DIR/enroll-instance"
    if [ -e "$KEYS_FILE" ]; then say "left in place on purpose: $KEYS_REAL (your API keys); delete it yourself if the keys are not wanted"; fi
    rmdir -- "$CONF_DIR" 2>/dev/null || warn "$CONF_DIR still holds files of yours and was left"
    rm -rf -- "$APP_DIR"
    say "left in place on purpose: every installed CLI and its login, the service user $SERVICE_USER and its home $SERVICE_HOME"
    say "revoke the runner token in the stand UI (the agent is gone but the token is still valid there)"
}

if [ "$MODE" = uninstall ]; then
    GRANT=""
    do_uninstall
    exit 0
fi

# ---------------------------------------------------------------------- check, before any change

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" && pwd)"
for needed in "${APP_FILES[@]}" install.sh pdf-analysis-agent.service agent.example.toml VERSION; do
    [ -f "$SRC_DIR/$needed" ] || die 65 "run install.sh from the directory the package was unpacked into ($needed is missing)"
done
PKG_VERSION="$(tr -d '[:space:]' < "$SRC_DIR/VERSION")"
[[ "$PKG_VERSION" =~ ^[0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,4}$ ]] || die 65 "the package's VERSION file is not a version number"

if [ -n "$PACKAGE_SHA256" ]; then
    [ -n "$PACKAGE_FILE" ] || die 64 "--sha256 needs --package FILE: the archive the digest is of"
    [[ "$PACKAGE_SHA256" =~ ^[0-9a-fA-F]{64}$ ]] || die 64 "--sha256 is not a sha256 digest"
    [ -f "$PACKAGE_FILE" ] || die 65 "the package file does not exist"
    got="$(sha256sum -- "$PACKAGE_FILE")"
    got="${got%% *}"
    want="$(printf '%s' "$PACKAGE_SHA256" | tr 'A-F' 'a-f')"
    [ "$got" = "$want" ] || die 65 "the package's sha256 is not the expected one; nothing was installed"
    say "package sha256 verified"
elif [ -n "$PACKAGE_FILE" ]; then
    die 64 "--package needs --sha256 DIGEST: an archive is not trusted without it"
fi

need_root
if [ -z "$ROOT" ]; then
    command -v systemctl > /dev/null 2>&1 || die 66 "systemd (systemctl) is required"
    if [ -r /etc/os-release ] && ! ( . /etc/os-release && [ "${ID:-}" = ubuntu ] ); then
        warn "this host is not Ubuntu; the installer is written and tested for Ubuntu LTS"
    fi
fi
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2> /dev/null \
    || die 66 "$PYTHON 3.11 or newer is required (Ubuntu 24.04 LTS has it)"

HAD_TOKEN=0
if [ -f "$ENV_FILE" ] && grep -q "^$TOKEN_ENV=." "$ENV_FILE"; then HAD_TOKEN=1; fi

EXISTING_ORIGIN=""
CONFIGURED_MODEL=""
EXISTING_MODE=""
if [ -f "$CONF_FILE" ]; then
    EXISTING_ORIGIN="$(sed -n 's/^origin = "\(.*\)"$/\1/p' "$CONF_FILE" | head -n 1)"
    CONFIGURED_MODEL="$(sed -n 's/^declared = "\(.*\)"$/\1/p' "$CONF_FILE" | head -n 1)"
    if grep -q '^mode = "host"$' "$CONF_FILE"; then EXISTING_MODE=host; else EXISTING_MODE=single; fi
fi

# Which agent: host mode (no model) or the single-model agent (a model given, or kept from an earlier install).
UPGRADE_CONVERT=0
if [ "$UPGRADE" -eq 1 ]; then
    [ -n "$EXISTING_MODE" ] || die 64 "--upgrade: no agent is installed here ($CONF_FILE is missing); run the install command instead"
    [ -z "$MODEL" ] || die 64 "--upgrade converts the agent to host mode, which takes no model (drop --model)"
    [ -z "$CLI" ] || die 64 "--upgrade converts the agent to host mode, which serves every CLI it finds (drop --cli)"
    AGENT_MODE=host
    if [ "$EXISTING_MODE" = single ]; then
        UPGRADE_CONVERT=1
        if [ "$NEW_SECRET" -eq 0 ]; then
            die 78 "--upgrade needs a NEW enrollment secret for the host: the installed token belongs to one connection. Issue it in the stand (connect a server) and set AUDITMANAGER_ENROLLMENT_SECRET; nothing was changed"
        fi
    fi
elif [ -f "$CONF_FILE" ] && [ "$RECONFIGURE" -eq 0 ]; then
    AGENT_MODE="$EXISTING_MODE"
elif [ -n "$MODEL" ] || [ "$EXISTING_MODE" = single ]; then
    AGENT_MODE=single
else
    AGENT_MODE=host
fi
if [ -z "$GRANT" ] && [ "$HAD_TOKEN" -eq 0 ]; then
    die 78 "nothing to enroll with: set AUDITMANAGER_ENROLLMENT_SECRET (the one-time secret from the stand) in the environment"
fi

CONFIG_KEPT=0
if [ -f "$CONF_FILE" ] && [ "$RECONFIGURE" -eq 0 ] && [ "$UPGRADE_CONVERT" -eq 0 ]; then CONFIG_KEPT=1; fi
if [ "$CONFIG_KEPT" -eq 1 ] || [ "$UPGRADE" -eq 1 ]; then
    if [ -n "$ORIGIN" ] && [ "$ORIGIN" != "$EXISTING_ORIGIN" ]; then
        die 78 "$CONF_FILE has another origin; pass --reconfigure to rewrite it for $ORIGIN"
    fi
    ORIGIN="$EXISTING_ORIGIN"
fi
[ -n "$ORIGIN" ] || die 78 "the stand's origin is not known: set AUDITMANAGER_STAND_ORIGIN (https://host[:port]) or pass --origin"

# The model, and the CLI that follows from it (single-model agent only). No default: the agent declares exactly the
# model its connection pins. Host mode declares none.
in_list() {
    local needle="$1" item
    shift
    for item in "$@"; do
        if [ "$item" = "$needle" ]; then return 0; fi
    done
    return 1
}
derive_cli() {  # derive_cli MODEL strict|lenient: sets DERIVED_CLI; strict refuses a model no command serves
    local model="$1"
    DERIVED_CLI=""
    if in_list "$model" "${CLAUDE_MODELS[@]}"; then
        DERIVED_CLI=claude
    elif in_list "$model" "${CODEX_MODELS[@]}"; then
        DERIVED_CLI=codex
    elif [ "$2" = strict ]; then
        if ! [[ "$model" =~ ^[A-Za-z0-9._-]{1,64}$ ]]; then die 64 "the model is not a model id"; fi
        case "$model" in
            claude-*) die 64 "claude_answer.py serves ${CLAUDE_MODELS[*]}, not $model" ;;
            *) die 64 "$model is not a model this agent can answer as (${CLAUDE_MODELS[*]} ${CODEX_MODELS[*]})" ;;
        esac
    fi
}

CONFIRM_CLI=""
TARGET_MODEL=""
ACTIVE_CLI=""
if [ "$AGENT_MODE" = host ]; then
    [ -z "$CLI" ] || die 64 "--cli belongs to a single-model agent: a host agent serves every CLI it finds (give a model, or drop --cli)"
    if [ "$CONFIG_KEPT" -eq 1 ] && [ -n "$MODEL" ]; then
        warn "the kept $CONF_FILE is a host agent: the model '$MODEL' was ignored; pass --reconfigure to install the single-model agent"
    fi
else
    if [ -n "$MODEL" ]; then
        derive_cli "$MODEL" strict  # a model that is given is checked whether or not it is going to be written
        CONFIRM_CLI="$DERIVED_CLI"
    fi
    if [ "$CONFIG_KEPT" -eq 1 ]; then
        TARGET_MODEL="$CONFIGURED_MODEL"
        derive_cli "$TARGET_MODEL" lenient  # an administrator may have put another model in a kept file
        if [ -n "$MODEL" ] && [ "$MODEL" != "$CONFIGURED_MODEL" ]; then
            warn "the kept $CONF_FILE declares the model '$CONFIGURED_MODEL' but this run asks for '$MODEL': the file was NOT changed; pass --reconfigure to declare '$MODEL'"
        fi
    else
        TARGET_MODEL="${MODEL:-$CONFIGURED_MODEL}"
        [ -n "$TARGET_MODEL" ] || die 64 "no model for the single-model agent: set AUDITMANAGER_AGENT_MODEL or pass --model (or install the host agent: give no model at all)"
        derive_cli "$TARGET_MODEL" strict
    fi
    ACTIVE_CLI="$DERIVED_CLI"
    if [ -n "$CLI" ]; then
        if [ -z "$CONFIRM_CLI" ]; then CONFIRM_CLI="$ACTIVE_CLI"; fi
        [ "$CLI" = "$CONFIRM_CLI" ] || die 64 "--cli $CLI contradicts the model: ${MODEL:-$TARGET_MODEL} is answered by ${CONFIRM_CLI:-no known command}"
    fi
fi

# ----------------------------------------------------------------------------- the service user

user_field() {  # user_field N: field N of the passwd entry of the service user, empty when it does not exist
    local line=""
    if [ -z "$ROOT" ]; then
        line="$(getent passwd "$SERVICE_USER" || true)"
    elif [ -n "$SYSCMD_DIR" ] && [ -x "$SYSCMD_DIR/getent" ]; then
        line="$("$SYSCMD_DIR/getent" passwd "$SERVICE_USER" || true)"
    fi
    if [ -n "$line" ]; then printf '%s\n' "$line" | cut -d: -f"$1"; fi
}

if [ -n "$(user_field 1)" ]; then
    [ "$(user_field 3)" != 0 ] || die 66 "$SERVICE_USER is root; the agent needs an account of its own"
    [ "$(user_field 6)" = "$SERVICE_HOME" ] || die 66 "the account $SERVICE_USER exists with another home directory than $SERVICE_HOME: pick another --service-user, or fix the account"
    say "reusing the service user $SERVICE_USER"
else
    say "creating the service user $SERVICE_USER"
    sysrun useradd --system --user-group --create-home --home-dir "$SERVICE_HOME" --shell /usr/sbin/nologin "$SERVICE_USER"
fi
install -d -m 0700 -- "$STATE_DIR"
chmod 0700 -- "$STATE_DIR"  # useradd may have made the home 0750; the CLI logins inside are the user's alone
if [ -z "$ROOT" ]; then chown "$SERVICE_USER:" -- "$STATE_DIR"; fi

# ------------------------------------------------------------------------------------- the files

put() {  # put MODE SOURCE DESTINATION: install a file; note a change
    local mode="$1" src="$2" dst="$3"
    if [ "$src" -ef "$dst" ]; then return 0; fi
    if [ ! -f "$dst" ] || ! cmp -s -- "$src" "$dst"; then CHANGED=1; fi
    install -m "$mode" -- "$src" "$dst"
}

install -d -m 0755 -- "$APP_DIR" "$CONF_DIR" "$UNIT_DIR"
for file in "${APP_FILES[@]}"; do put 0644 "$SRC_DIR/$file" "$APP_DIR/$file"; done
put 0644 "$SRC_DIR/VERSION" "$APP_DIR/VERSION"
put 0755 "$SRC_DIR/install.sh" "$APP_DIR/install.sh"
say "agent $PKG_VERSION installed in $APP_REAL"

if [ -e "$ENV_FILE" ]; then chmod 0600 -- "$ENV_FILE"; else install -m 0600 /dev/null "$ENV_FILE"; fi

detected_clis() {  # the lines `detect.py` prints, as the service user (its own HOME, never another account's)
    local flag=()
    if [ "$AGENT_MODE" = host ]; then flag=(--host --key-file "$KEYS_REAL"); fi
    sysrun runuser -u "$SERVICE_USER" -- /usr/bin/env -i "HOME=$SERVICE_HOME" LANG=C.UTF-8 "$PYTHON" "$APP_REAL/detect.py" ${flag[@]+"${flag[@]}"} || true
}

STAGED_CONFIG=0
if [ "$CONFIG_KEPT" -eq 1 ]; then
    say "kept the existing $CONF_FILE (pass --reconfigure to write it again)"
else
    staged="$(mktemp "$CONF_DIR/.agent.toml.XXXXXX")"
    if [ "$AGENT_MODE" = host ]; then
        cat > "$staged" << EOF
# Written by install.sh (package $PKG_VERSION): the HOST agent. Edit it and restart the service; running install.sh again
# keeps this file unless --reconfigure is given. Secrets never go here: the runner token is in agent.env (mode 0600).
# No model is declared: the stand's catalogue says which models matter, and the agent verifies each with a minimal call.

[runner]
origin = "$ORIGIN"
token_env = "$TOKEN_ENV"
wait_seconds = 25
drain_seconds = 60

[executor]
mode = "host"

[host]
# API keys for direct calls (ANTHROPIC_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY, one NAME=value per line). The file
# must be mode 0600 and owned by the service user, or it is ignored. Absent: no API provider, only the signed-in CLIs.
key_file = "$KEYS_REAL"
# accept_images = false

# Concurrent calls per provider. Default: 1 on a subscription login, 2 on an API login or key. A provider is one of
# claude_code, codex, anthropic_api, openai_api, openrouter_api.
# [slots]
# claude_code = 1
EOF
        say "wrote $CONF_FILE: host mode (every model this host can reach), no model declared"
    else
        if [ "$ACTIVE_CLI" = codex ]; then
            argv="[\"/usr/bin/python3\", \"$APP_REAL/codex_answer.py\"]"
        else
            argv="[\"/usr/bin/python3\", \"$APP_REAL/claude_answer.py\", \"--model\", \"$TARGET_MODEL\"]"
        fi
        cat > "$staged" << EOF
# Written by install.sh (package $PKG_VERSION). Edit it and restart the service; running install.sh again keeps
# this file unless --reconfigure is given. Secrets never go here: the runner token is in agent.env (mode 0600).

[runner]
origin = "$ORIGIN"
token_env = "$TOKEN_ENV"
wait_seconds = 25
# One task at a time. Raising it is an explicit act of the administrator (README, section B).
concurrency = 1
drain_seconds = 60

[model]
# The exact pinned model id this agent answers as: the model the connection pins on the stand.
declared = "$TARGET_MODEL"

[executor]
mode = "command"

[command]
argv = $argv
timeout_seconds = 540
accept_images = false
EOF
        say "wrote $CONF_FILE: $ACTIVE_CLI, answering as $TARGET_MODEL, concurrency = 1"
    fi
    if [ "$UPGRADE_CONVERT" -eq 1 ]; then
        STAGED_CONFIG=1  # put in place only once the enrollment has succeeded: the old token is of a connection, not of a host
    else
        put 0644 "$staged" "$CONF_FILE"
        rm -f -- "$staged"
    fi
fi

# --------------------------------------------------------------------------------- enrollment

ENROLLED=0
if [ -n "$GRANT" ]; then
    rc=0
    ENROLL_CONFIG="$CONF_FILE"
    if [ "$STAGED_CONFIG" -eq 1 ]; then ENROLL_CONFIG="$staged"; fi
    AUDITMANAGER_ENROLLMENT_SECRET="$GRANT" "$PYTHON" "$APP_DIR/agent.py" \
        --config "$ENROLL_CONFIG" --env-file "$ENV_FILE" --enroll-only || rc=$?
    GRANT=""
    if [ "$rc" -eq 0 ]; then
        ENROLLED=1
    elif [ "$UPGRADE_CONVERT" -eq 1 ]; then
        case "$rc" in
            3) die 78 "the stand refused the enrollment secret (see above); the single-model agent was left as it was (the files of the package were updated, its configuration and token were not)" ;;
            75) die 69 "the stand could not be reached (see above); run the same command again within 15 minutes; the single-model agent was left as it was" ;;
            *) die 1 "the enrollment failed (agent.py exit $rc); the single-model agent was left as it was" ;;
        esac
    elif [ "$HAD_TOKEN" -eq 1 ]; then
        warn "the enrollment secret was not accepted (exit $rc); the runner token already installed was kept"
    else
        case "$rc" in
            3) die 78 "the stand refused the enrollment secret (see above); nothing was started" ;;
            75) die 69 "the stand could not be reached (see above); run the same command again within 15 minutes" ;;
            *) die 1 "the enrollment failed (agent.py exit $rc); nothing was started" ;;
        esac
    fi
fi
if [ "$STAGED_CONFIG" -eq 1 ]; then
    cp -p -- "$CONF_FILE" "$CONF_FILE.pre-host"
    put 0644 "$staged" "$CONF_FILE"
    rm -f -- "$staged"
    say "converted the single-model agent to host mode; the old configuration is kept as $CONF_FILE.pre-host"
fi

# ------------------------------------------------------------------------------------ the service

unit_staged="$(mktemp "$UNIT_DIR/.$SERVICE_NAME.service.XXXXXX")"
sed -e "s/^User=pdf-agent\$/User=$SERVICE_USER/" -e "s/^Group=pdf-agent\$/Group=$SERVICE_USER/" \
    "$SRC_DIR/pdf-analysis-agent.service" > "$unit_staged"
put 0644 "$unit_staged" "$UNIT_FILE"
rm -f -- "$unit_staged"

sysrun systemctl daemon-reload
if sysrun systemctl is-active --quiet "$SERVICE_NAME.service"; then
    if [ "$CHANGED" -eq 1 ] || [ "$ENROLLED" -eq 1 ]; then
        sysrun systemctl restart "$SERVICE_NAME.service"
        say "restarted the service"
    else
        say "the service is running and nothing changed"
    fi
else
    sysrun systemctl enable --now "$SERVICE_NAME.service"
    say "started the service"
fi
if [ -z "$ROOT" ]; then sleep 3; fi
if ! sysrun systemctl is-active --quiet "$SERVICE_NAME.service"; then
    warn "the service is not running; its last log lines follow"
    sysrun journalctl -u "$SERVICE_NAME.service" -n 15 --no-pager >&2 || true
    die 1 "the agent did not stay up (exit status 2 or 3 of the agent means a bad configuration or a refused token: it is not restarted)"
fi

# --------------------------------------------------------------------------------------- finish

if [ "$AGENT_MODE" = host ]; then
    say "done: agent $PKG_VERSION runs as the service $SERVICE_NAME under the user $SERVICE_USER, as a host agent (no model declared)"
else
    say "done: agent $PKG_VERSION runs as the service $SERVICE_NAME under the user $SERVICE_USER, one task at a time"
fi
say "state of the CLIs for $SERVICE_USER (the stand shows the same once the agent has reported):"
found="$(detected_clis)"
printf '%s\n' "$found"

CLI_INSTALLED=0
case $'\n'"$found" in *$'\n'"$ACTIVE_CLI installed=yes"*) CLI_INSTALLED=1 ;; esac
CLAUDE_STEP="sudo -u $SERVICE_USER -H claude auth login           check: sudo -u $SERVICE_USER -H claude auth status"
CODEX_STEP="sudo -u $SERVICE_USER -H codex login --device-auth    check: sudo -u $SERVICE_USER -H codex login status"
case "$ACTIVE_CLI" in
    claude) LABEL="Claude Code"; STEPS="  $CLAUDE_STEP" ;;
    codex) LABEL="Codex"; STEPS="  $CODEX_STEP" ;;
    *) LABEL="the CLI"; STEPS="  Claude Code:  $CLAUDE_STEP"$'\n'"  Codex:        $CODEX_STEP" ;;
esac
echo
if [ "$AGENT_MODE" = host ]; then
    cat << EOF
The steps left are yours, and the installer never does them for you. The agent serves what it finds, so do the ones you want:

  sign a CLI in AS THE SERVICE USER (a subscription login, or an API-key login of the CLI itself):
$STEPS

  direct API calls (optional): put the keys in $KEYS_REAL, mode 0600, owned by $SERVICE_USER, one NAME=value per line
  (ANTHROPIC_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY); a file with any other mode or owner is ignored, and a key
  is never put in an environment, a report or a log. A call through a key sends the document text to that API:
    sudo install -m 0600 -o $SERVICE_USER -g $SERVICE_USER /dev/null $KEYS_REAL    then edit it (the agent notices within a minute)

No credential is ever copied from another account, and a CLI signed in under another account (yours, root) is not
used: it is reported as login_required. The host appears in the stand's executor screen once it has reported; check
this machine meanwhile with: sudo -u $SERVICE_USER -H python3 $APP_REAL/detect.py --host --key-file $KEYS_REAL
To remove the agent later: sudo bash $APP_REAL/install.sh --uninstall
EOF
    exit 0
fi
if [ -n "$ACTIVE_CLI" ] && [ "$CLI_INSTALLED" -eq 0 ]; then
    cat << EOF
$LABEL, which answers as $TARGET_MODEL, is NOT installed for $SERVICE_USER. The agent is running and reports it to
the stand as not installed, so it answers nothing yet. Install it for that user -- the vendor's documented
installer run as $SERVICE_USER, or system-wide under /usr/local/bin -- and then sign it in.
EOF
else
    echo "The step left is yours, and the installer never does it for you: sign $LABEL in AS THE SERVICE USER."
fi
cat << EOF
No credential is ever copied from another account, and a CLI signed in under another account (yours, root) is not
used: it is reported as login_required.

$STEPS

Then mark the connection «authorised for this integration» in the stand's executor screen. To remove the agent
later: sudo bash $APP_REAL/install.sh --uninstall
EOF
