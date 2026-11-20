#!/usr/bin/env bash
# `FIRST-INSTALL-01` -- the whole stack on a server that has never run it, from one command.
#
#   sudo infra/deploy/first-install.sh --email ADDRESS [--domain NAME] [--norms-bundle DIR] [--instance NAME] [--dry-run]
#
# Run it as root from a fresh clone. It is written for a person or a small AI agent that follows its literal output:
#
#   * every STOP is ONE line, `STOP [code]: <the exact next action>`, and a non-zero exit (the table below is the single source
#     of the codes; `--print-codes` prints it and `infra/deploy/FIRST-INSTALL-PROMPT.md` carries a checked copy);
#   * success ends with a line that begins `DONE:`;
#   * a rerun continues where the last run stopped: each stage looks at what is already done and skips it. A run killed in the
#     middle (an agent's tool timing out) is rerun with the same command.
#
# THE STAGES (`--dry-run` prints them with what each would do, and changes nothing):
#
#    1 preflight   root, tools, Docker and Compose, disk and memory against the runbook's figures, ports, a clean clone
#    2 env         infra/deploy/env/alpha.env and provider.env from the examples, every secret generated, mode 600
#    3 deploy      the first deploy.sh, without published HTTPS; it ends [default_credential] on a fresh database, on purpose
#    4 admin       the administrator's password changed and its profile completed through the loopback API; deploy.sh again
#    5 norms       (--norms-bundle) the norms bundle imported on this host, then made the current snapshot
#    6 https       (--domain) DNS checked, test certificate, real certificate, then ALPHA_PUBLISH_HTTPS=yes
#    7 executors   this server's own claude / codex subscriptions connected as «Этот сервер»
#    8 verify      infra/deploy/verify-deployed.sh must exit 0
#    9 github      what to paste into the repository's Actions settings, and a deploy key for the workflow
#   10 marker      /var/lib/<instance>/first-install.done; a second run then refuses
#
# WHAT IT NEVER DOES: delete data or volumes, run `git clean`, `git reset` or any command that edits a tracked file, write in the
# clone except the two git-ignored files under infra/deploy/env/, print a secret, or print a private key. The administrator's
# password and the deploy key's private half are written to root-only files OUTSIDE the clone; only their paths are printed.
#
# THE PASSWORD FILES AND KEYS ARE FOR THE OWNER. An agent running this script does not read them.
#
# EXIT: 0 done; 10 a STOP; 2 the command line was wrong (also a STOP); 70 an unexpected failure (STOP [unexpected]).
#
# THE ON-HOST NORMS PATH (stage 5) drives `receive-bundle.sh` and `copy-serve.sh` directly, through the `SSH_ORIGINAL_COMMAND` they
# read from an SSH forced command, as the root account that owns the directories they require. It changes neither script.

set -Eeuo pipefail
umask 077

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO="$(cd "$HERE/../.." && pwd -P)"
DEPLOY_DIR="$HERE"
ENV_DIR="$DEPLOY_DIR/env"
ENV_FILE="$ENV_DIR/alpha.env"
PROVIDER_FILE="$ENV_DIR/provider.env"
ENV_EXAMPLE="$ENV_DIR/alpha.env.example"
ENV_HELPER="$DEPLOY_DIR/lib/first_install_env.py"
API_HELPER="$DEPLOY_DIR/lib/first_install_api.py"
LISTENERS_LIB="$DEPLOY_DIR/lib/proxy-listeners.sh"
ACME_OVERLAY="$REPO/infra/acme/compose.acme.yml"
ACME_PIN="$REPO/infra/acme/client.pin"
COMPOSE_FILE="$DEPLOY_DIR/compose.server.yml"

# ------------------------------------------------------------------------------------------------ seams for the tests
# Honoured ONLY when FIRST_INSTALL_TEST_MODE=1; a real run reads none of them.
seam() { # seam NAME DEFAULT
    local override="FIRST_INSTALL_$1"
    if [ "${FIRST_INSTALL_TEST_MODE:-}" = 1 ] && [ -n "${!override:-}" ]; then
        printf '%s' "${!override}"
    else
        printf '%s' "$2"
    fi
}
TEST_MODE=no
[ "${FIRST_INSTALL_TEST_MODE:-}" != 1 ] || TEST_MODE=yes
STATE_ROOT="$(seam STATE_ROOT /var/lib)"
SECRET_DIR="$(seam SECRET_DIR /root)"
LOG_DIR="$(seam LOG_DIR /var/log)"
NORMS_COPY_DIR="$(seam COPY_DIR /srv/auditmanager-copy)"      # deploy.sh's defaults: STAND_COPY_RECORD's directory
NORMS_STAGING="$(seam STAGING /srv/auditmanager-bundles)"     # and BUNDLE_STAGING
PROC_NET="$(seam PROC_NET /proc/net)"
MEMINFO="$(seam MEMINFO /proc/meminfo)"
HOST_KEY_PUB="$(seam HOST_KEY_PUB /etc/ssh/ssh_host_ed25519_key.pub)"
POLL_SECONDS="$(seam POLL_SECONDS 30)"
CERT_WAIT_SECONDS="$(seam CERT_WAIT_SECONDS 900)"
ADMIN_WAIT_SECONDS="$(seam ADMIN_WAIT_SECONDS 180)"

# --------------------------------------------------------------------------------------------- figures from the runbook
# DEPLOYMENT_RUNBOOK.md section 1, "Disk": at least 8 GB free before the first deploy (the cache grows with each build).
MIN_FREE_GIB=8
# Section 1 and `deploy.sh`'s own build watch: below this much memory in total a build can thrash (the 2026-11-17 outage on 4 GB).
WARN_RAM_TOTAL_MIB=3500
STOP_RAM_AVAILABLE_MIB=1024
# STAND-NORMS-IMPORT-RUNBOOK-01.md section 0 item 4: "RAM available >= 2 GiB (importer peak 0.79 GiB + 1 GiB), swap excluded".
NORMS_RAM_AVAILABLE_MIB=2048
DEFAULT_INSTANCE=auditmanager
DEFAULT_HTTP_PORT=31500

# ----------------------------------------------------------------------------------------------------------- STOP codes
# THE SINGLE SOURCE. One line per code: `code|text`. The text is a printf format whose `%s` the stop call fills with the facts of
# this run. The text is the whole of the action: a line that begins `ASK THE OWNER` is for the owner and no one else; any other line
# is something the reader does itself, exactly as printed, and then runs the same command again. `--print-codes` prints this
# table; the prompt for a simple agent carries the same table and a test holds the two equal. A text may not hold `|`.
CODES_TABLE="$(cat <<'TABLE'
usage|Fix the command line as the lines above say (--help shows it), then run the same command again.
not_root|Run the same command with sudo (as root).
tool_missing|Install the missing tools (%s) with: apt-get install -y %s   then run the same command again.
docker_missing|ASK THE OWNER: Docker Engine with the compose plugin is not installed on this server. After the owner has installed it, run the same command again.
docker_down|Start Docker with: systemctl start docker   then run the same command again. If it does not start, ASK THE OWNER.
docker_old|ASK THE OWNER: %s Docker Engine 20 or newer with the compose v2 plugin is required.
checkout_wrong|Run the script from its own clone: cd %s   and then the same command again.
checkout_dirty|ASK THE OWNER: the clone has local changes (%s). Do not edit or clean it. Use a fresh clone of the repository and run the command there.
checkout_path|ASK THE OWNER: the clone path %s must use only letters, digits, '.', '_' and '-' (auto-deploy refuses other characters). Clone into such a path, for example /srv/auditmanager, and run the command there.
no_origin|ASK THE OWNER: this clone has no 'origin' remote and auto-deploy needs it. Use a fresh clone made with git clone.
deploy_user_invalid|ASK THE OWNER, who runs the printed command: %s
disk_low|Free disk space is %s GiB on %s and %s GiB are needed. Run: docker builder prune -af   (it removes build cache only) and run the same command again. If it stops here again, ASK THE OWNER for a larger disk.
ram_low|ASK THE OWNER: only %s MiB of memory are available and %s MiB are needed. Free memory or resize the server, then run the same command again.
http_port_busy|Port %s on this server is already in use. Run the same command again with --http-port set to another free port number (for example 31501).
public_port_busy|ASK THE OWNER: public port %s is held by %s. It must be free for the certificate (DEPLOYMENT_RUNBOOK.md section 6 step 4 for a host nginx). After it is free, run the same command again.
instance_invalid|Run again with --instance made of 3 to 40 lower-case letters, digits and '-', starting with a letter (for example auditmanager).
instance_mismatch|Run the same command again with --instance %s, or without --instance: the existing environment file already belongs to that instance.
domain_invalid|ASK THE OWNER for the server's public DNS name (%s). It is lower case, has a dot, no scheme and no port, for example audit.mycompany.ru.
email_required|ASK THE OWNER for an e-mail address. It becomes the administrator's login and the certificate contact. Then run the same command again with --email ADDRESS.
email_invalid|ASK THE OWNER for a plain e-mail address (letters, digits and . _ + - around one @); %s is not one. Then run the same command again with --email ADDRESS.
env_invalid|ASK THE OWNER: the environment file is not usable (%s). Do not edit it. The owner repairs or removes it.
already_running|An earlier run of this command is still working: do not start another. Wait five minutes, look at the end of %s with tail -n 30, and run the same command again only when that file has not changed for fifteen minutes.
already_installed|Nothing to do: this server was installed on %s (marker %s). To repeat one failed stage on purpose, the owner runs: sudo infra/deploy/first-install.sh --resume-stage N (same options).
deploy_refused|ASK THE OWNER: deploy.sh refused: %s
deploy_failed|Run the same command once more. If it stops here again, ASK THE OWNER and show the last 30 lines of output (deploy.sh ended with status %s).
host_overloaded|The server is overloaded. Wait five minutes, then run the same command again. If it stops here again, ASK THE OWNER.
acme_unpinned|ASK THE OWNER: the certificate client is not pinned in infra/acme/client.pin (DEPLOYMENT_RUNBOOK.md section 6 step 1). The owner commits the pin to the repository; then update this clone with git pull --ff-only and run the same command again.
dns_missing|ASK THE OWNER: the name %s has no DNS A record. Create an A record for it pointing to %s, wait a few minutes, then run the same command again.
dns_mismatch|ASK THE OWNER: the DNS A record of %s points to %s, not to this server (%s). Change the record, wait a few minutes, then run the same command again.
acme_staging_failed|ASK THE OWNER: the test certificate was not issued within %s seconds. Show the owner the output of: docker compose --env-file %s -f %s -f %s logs acme
acme_real_failed|ASK THE OWNER: the real certificate was not issued within %s seconds (a rate limit of the authority is the usual reason, DEPLOYMENT_RUNBOOK.md section 6 step 9). Show the owner the output of: docker compose --env-file %s -f %s -f %s logs acme
https_not_published|ASK THE OWNER: the deploy finished but public port 443 is not published (%s). Show the owner the last 30 lines of output.
admin_failed|ASK THE OWNER: the administrator account could not be finished (%s). Show the owner the last 30 lines of output. Never print the password file.
admin_unknown_password|ASK THE OWNER: the administrator's password is neither the published one nor the one stored in %s. The owner decides; do not guess.
norms_bundle_invalid|ASK THE OWNER: the norms bundle %s is not usable (%s).
norms_disk_low|Free disk space is too small for the norms import: %s GiB are free on %s and about %s GiB are needed. Run: docker builder prune -af   and run the same command again. If it stops here again, ASK THE OWNER for a larger disk.
norms_busy|ASK THE OWNER: another copy or import is open (%s). Do not touch it. After the owner has closed it, run the same command again.
norms_refused|ASK THE OWNER: the norms transfer or import was refused: %s
norms_import_failed|ASK THE OWNER: the norms import ended with status %s (2 is a refusal, 75 an unfinished admission). Its log is %s
norms_import_interrupted|ASK THE OWNER: the norms import of %s started and is neither running nor finished (the server may have restarted). The owner checks it with docker ps and decides (STAND-NORMS-IMPORT-RUNBOOK-01.md section 8).
norms_report_differs|ASK THE OWNER: the norms import finished but its report does not match (status %s). Do not designate anything. The owner decides before the writers are resumed; the report is %s
norms_designate_failed|ASK THE OWNER: the norms snapshot could not be made current (%s).
executors_login_needed|ASK THE OWNER to sign this server in to a subscription: as root run claude (and/or codex login) and finish the sign-in in the browser. Then run the same command again. If the owner does not want this server's own subscriptions, run the same command again with --skip-executors.
executors_not_connected|ASK THE OWNER: signed-in subscriptions were found but local-agent.sh could not connect them (status %s). Show the owner the last 30 lines of output.
verify_failed|ASK THE OWNER: verify-deployed.sh ended with status %s (0 is success). Show the owner the last 30 lines of output.
unexpected|ASK THE OWNER and show the last 30 lines of output (the script failed at line %s).
TABLE
)"

STOP_EXIT=10

code_template() { # code_template CODE -> the format of that code
    printf '%s\n' "$CODES_TABLE" | awk -F'|' -v c="$1" '$1 == c { sub(/^[^|]*\|/, ""); print; found = 1; exit } END { exit found ? 0 : 1 }'
}

# stop CODE [fact...]: print the one STOP line and leave. Never call it inside $(...): the exit would only end that subshell.
stop() {
    local code="$1" template text
    shift
    template="$(code_template "$code")" || template="ASK THE OWNER: unknown stop code ${code}."
    # shellcheck disable=SC2059  # the format is the table's own text; the facts are arguments
    text="$(printf -- "$template" "$@")"
    text="$(printf '%s' "$text" | tr '\r\n\t' '   ' | cut -c1-700)"
    printf 'STOP [%s]: %s\n' "$code" "$text"
    [ "$code" != usage ] || exit 2
    exit "$STOP_EXIT"
}

print_codes() { # print_codes [--markdown]
    if [ "${1:-}" = --markdown ]; then
        printf '| Code | What to do |\n| --- | --- |\n'
        printf '%s\n' "$CODES_TABLE" | awk -F'|' '{ code = $1; sub(/^[^|]*\|/, ""); gsub(/%s/, "<...>"); printf "| `%s` | %s |\n", code, $0 }'
    else
        printf '%s\n' "$CODES_TABLE" | awk -F'|' '{ code = $1; sub(/^[^|]*\|/, ""); gsub(/%s/, "<...>"); printf "%s\t%s\n", code, $0 }'
    fi
}

on_error() {
    local line="$1"
    # shellcheck disable=SC2059  # the format is the table's own text
    printf 'STOP [unexpected]: %s\n' "$(printf -- "$(code_template unexpected)" "$line")"
    exit 70
}
trap 'on_error $LINENO' ERR

say() { printf 'first-install: %s\n' "$*"; }
warn() { printf 'first-install: WARNING: %s\n' "$*"; }
stage_header() { printf '\nfirst-install: [%s/10] %s\n' "$1" "$2"; }

usage() {
    cat <<'USAGE'
usage: sudo infra/deploy/first-install.sh --email ADDRESS [options]

  --email ADDRESS        the administrator's login and the certificate contact (required)
  --domain NAME          the server's public DNS name: also gets a certificate and public port 443
  --norms-bundle DIR     import this norms bundle directory on this host and make it the current snapshot
  --instance NAME        the name of this installation (default auditmanager)
  --http-port N          the loopback port of the application (default 31500)
  --deploy-user NAME     the account GitHub auto-deploy logs in as (default root)
  --set NAME=VALUE       one more setting for a NEW alpha.env (repeatable; the example file's names only)
  --no-ci-key            do not generate a deploy key for GitHub auto-deploy
  --skip-executors       do not require this server's own claude/codex subscriptions (the owner decides)
  --resume-stage N       run again from stage N (1-9), also after the installation is marked done
  --dry-run              print the stages and what each would do; change nothing
  --print-codes          print the STOP code table (add --markdown for the prompt's form)
  -h, --help             this text

Run it as root from a fresh clone. Every stop is one line, STOP [code]: <what to do>; success ends with DONE:.
USAGE
}

usage_error() { # usage_error MESSAGE: the message, the help, then the one STOP line
    printf 'first-install: %s\n' "$1"
    usage
    stop usage
}

# --------------------------------------------------------------------------------------------------------- arguments
OPT_EMAIL="" OPT_DOMAIN="" OPT_BUNDLE="" OPT_INSTANCE="" OPT_HTTP_PORT="" OPT_DEPLOY_USER=root
OPT_NO_CI_KEY=no OPT_SKIP_EXECUTORS=no OPT_RESUME="" OPT_DRY_RUN=no
OPT_SETS=()

parse_args() {
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --email|--domain|--norms-bundle|--instance|--http-port|--deploy-user|--set|--resume-stage)
                if [ "$#" -lt 2 ] || [ -z "$2" ]; then usage_error "$1 needs a value"; fi
                case "$1" in
                    --email) OPT_EMAIL="${2,,}" ;;
                    --domain) OPT_DOMAIN="${2,,}" ;;
                    --norms-bundle) OPT_BUNDLE="$2" ;;
                    --instance) OPT_INSTANCE="$2" ;;
                    --http-port) OPT_HTTP_PORT="$2" ;;
                    --deploy-user) OPT_DEPLOY_USER="$2" ;;
                    --set) OPT_SETS+=("$2") ;;
                    --resume-stage) OPT_RESUME="$2" ;;
                esac
                shift 2 ;;
            --no-ci-key) OPT_NO_CI_KEY=yes; shift ;;
            --skip-executors) OPT_SKIP_EXECUTORS=yes; shift ;;
            --dry-run) OPT_DRY_RUN=yes; shift ;;
            --print-codes) shift; print_codes "${1:-}"; exit 0 ;;
            -h|--help) usage; exit 0 ;;
            *) usage_error "unknown option: $1" ;;
        esac
    done
}

validate_args() {
    if [ -n "$OPT_INSTANCE" ] && ! [[ "$OPT_INSTANCE" =~ ^[a-z][a-z0-9-]{1,38}[a-z0-9]$ ]]; then stop instance_invalid; fi
    if [ -n "$OPT_HTTP_PORT" ]; then
        if ! [[ "$OPT_HTTP_PORT" =~ ^[0-9]{4,5}$ ]] || [ "$OPT_HTTP_PORT" -lt 1024 ] || [ "$OPT_HTTP_PORT" -gt 65535 ]; then
            usage_error "--http-port is a number from 1024 to 65535"
        fi
    fi
    if [ -n "$OPT_RESUME" ]; then
        [[ "$OPT_RESUME" =~ ^[1-9]$ ]] || usage_error "--resume-stage is a number from 1 to 9"
    fi
    [[ "$OPT_DEPLOY_USER" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]] || usage_error "--deploy-user is a lower-case account name"
    if [ -n "$OPT_EMAIL" ] && ! [[ "$OPT_EMAIL" =~ ^[A-Za-z0-9._+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; then stop email_invalid "$OPT_EMAIL"; fi
    if [ -n "$OPT_DOMAIN" ]; then
        # shellcheck source=infra/deploy/lib/proxy-listeners.sh
        . "$LISTENERS_LIB"
        local why
        why="$(listeners_name_problem "$OPT_DOMAIN")" || stop domain_invalid "$OPT_DOMAIN: $why"
    fi
    local setting
    for setting in ${OPT_SETS[@]+"${OPT_SETS[@]}"}; do
        [[ "$setting" =~ ^[A-Z][A-Z0-9_]*=[A-Za-z0-9._:/@,=+-]*$ ]] || usage_error "--set takes NAME=VALUE (letters, digits and ._:/@,=+- in the value)"
    done
    if [ -n "$OPT_BUNDLE" ] && [ ! -d "$OPT_BUNDLE" ]; then stop norms_bundle_invalid "$OPT_BUNDLE" "it is not a directory"; fi
    return 0
}

# ------------------------------------------------------------------------------------------------------------- state
INSTANCE="" STATE_DIR="" STATE_FILE="" MARKER="" LOG_FILE="" HTTP_PORT="" ALPHA_BASE=""

private_dir() { mkdir -p "$1" && chmod 700 "$1"; }

env_get() { python3 -I "$ENV_HELPER" get --env "$ENV_FILE" "$1"; }

resolve_instance() {
    INSTANCE="${OPT_INSTANCE:-$DEFAULT_INSTANCE}"
    # Without python3 the stop is the preflight's (tool_missing); the existing file is read then.
    if [ -f "$ENV_FILE" ] && command -v python3 >/dev/null 2>&1; then
        local existing
        existing="$(env_get ALPHA_INSTANCE)"
        if [ -n "$existing" ]; then
            [ -z "$OPT_INSTANCE" ] || [ "$OPT_INSTANCE" = "$existing" ] || stop instance_mismatch "$existing"
            INSTANCE="$existing"
        fi
        HTTP_PORT="$(env_get ALPHA_HTTP_PORT)"
    fi
    [ -n "$HTTP_PORT" ] || HTTP_PORT="${OPT_HTTP_PORT:-$DEFAULT_HTTP_PORT}"
    STATE_DIR="$STATE_ROOT/$INSTANCE"
    STATE_FILE="$STATE_DIR/first-install.state"
    MARKER="$STATE_DIR/first-install.done"
    LOG_FILE="$LOG_DIR/$INSTANCE-first-install.log"
    ALPHA_BASE="http://127.0.0.1:$HTTP_PORT/api/v1"
}

state_has() { [ -f "$STATE_FILE" ] && grep -qxF "$1=ok" "$STATE_FILE"; }
state_mark() {
    private_dir "$STATE_DIR"
    state_has "$1" || printf '%s=ok\n' "$1" >> "$STATE_FILE"
}
state_clear_from() { # forget every result of stage N and later (keys are s<N> and s<N>.<name>)
    [ -f "$STATE_FILE" ] || return 0
    local kept
    kept="$(awk -F'[.=]' -v from="$1" '{ n = $1; sub(/^s/, "", n); if (n + 0 < from + 0) print }' "$STATE_FILE")"
    printf '%s\n' "$kept" | sed '/^$/d' > "$STATE_FILE.tmp"
    mv -f "$STATE_FILE.tmp" "$STATE_FILE"
}

# ------------------------------------------------------------------------------------------------------ small probes
mem_field_mib() { awk -v f="$1:" '$1 == f { print int($2 / 1024); exit }' "$MEMINFO"; }
free_gib() { # free_gib PATH
    local bytes
    bytes="$(df -B1 --output=avail -- "$1" 2>/dev/null | tail -n 1 | tr -d ' ')"
    [[ "$bytes" =~ ^[0-9]+$ ]] || bytes=0
    echo $(( bytes / 1073741824 ))
}
port_listening() { # port_listening N: some socket listens on it, on any address (deploy.sh's own method)
    local hex file
    hex="$(printf '%04X' "$1")"
    for file in "$PROC_NET/tcp" "$PROC_NET/tcp6"; do
        [ -r "$file" ] || continue
        if awk -v p="$hex" 'NR > 1 && $4 == "0A" { n = split($2, a, ":"); if (a[n] == p) found = 1 } END { exit found ? 0 : 1 }' "$file"; then
            return 0
        fi
    done
    return 1
}
port_holder_is_ours() { # port_holder_is_ours N: a container of this instance publishes it
    docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep -E "^${INSTANCE}-" | grep -qE "(:|^|[^0-9])$1->" || return 1
}
local_ipv4s() {
    if command -v ip >/dev/null 2>&1; then
        ip -4 -o addr show 2>/dev/null | awk '{ sub(/\/.*/, "", $4); print $4 }'
    else
        hostname -I 2>/dev/null | tr ' ' '\n' | grep -E '^[0-9]+\.' || true
    fi
}
is_private_ipv4() {
    [[ "$1" =~ ^(10\.|127\.|169\.254\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.) ]]
}
public_ipv4() { # the first routable address of an interface, else what an outside echo service sees, else nothing
    local address
    while IFS= read -r address; do
        [ -n "$address" ] || continue
        if ! is_private_ipv4 "$address"; then printf '%s' "$address"; return 0; fi
    done < <(local_ipv4s)
    if [ "$TEST_MODE" = no ]; then
        address="$(curl -fsS --max-time 10 https://api.ipify.org 2>/dev/null || true)"
        if [[ "$address" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then printf '%s' "$address"; return 0; fi
    fi
    return 0
}
oneline() { printf '%s' "$1" | tr '\r\n\t' '   ' | cut -c1-"${2:-300}"; }
last_line() { printf '%s\n' "$1" | sed '/^$/d' | tail -n 1; }

# ----------------------------------------------------------------------------------------------------- 1 preflight
email_needed() {
    state_has s4 && { [ -z "$OPT_DOMAIN" ] || state_has s6; } && return 1
    return 0
}

stage_preflight() {
    local tool missing="" packages="" dep
    # root
    if [ "$(id -u)" -ne 0 ] && [ "$TEST_MODE" = no ]; then stop not_root; fi
    # inputs that are only needed when a stage will use them
    if email_needed && [ -z "$OPT_EMAIL" ]; then stop email_required; fi
    # tools (docker is judged on its own below)
    for tool in git curl sed awk flock tar sha256sum python3 ssh-keygen getent df stat; do
        command -v "$tool" >/dev/null 2>&1 && continue
        missing="$missing $tool"
        case "$tool" in
            flock) dep=util-linux ;; ssh-keygen) dep=openssh-client ;; getent) dep=libc-bin ;; sha256sum|df|stat) dep=coreutils ;;
            awk) dep=gawk ;; *) dep="$tool" ;;
        esac
        case " $packages " in *" $dep "*) ;; *) packages="$packages $dep" ;; esac
    done
    if [ -n "$missing" ]; then stop tool_missing "${missing# }" "${packages# }"; fi
    python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' || stop tool_missing "python3 (3.8 or newer)" "python3"
    # docker and compose
    command -v docker >/dev/null 2>&1 || stop docker_missing
    docker info >/dev/null 2>&1 || stop docker_down
    local server compose_version
    server="$(docker version --format '{{.Server.Version}}' 2>/dev/null || true)"
    if ! [[ "${server%%.*}" =~ ^[0-9]+$ ]] || [ "${server%%.*}" -lt 20 ]; then stop docker_old "Docker Engine ${server:-of unknown version} is installed."; fi
    compose_version="$(docker compose version --short 2>/dev/null || true)"
    compose_version="${compose_version#v}"
    if ! [[ "${compose_version%%.*}" =~ ^[0-9]+$ ]] || [ "${compose_version%%.*}" -lt 2 ]; then
        stop docker_old "The compose plugin is ${compose_version:-missing}."
    fi
    say "docker $server, compose $compose_version"
    # the clone
    local top status
    top="$(git -C "$REPO" rev-parse --show-toplevel 2>/dev/null || true)"
    if [ -z "$top" ] || [ "$(cd "$top" && pwd -P)" != "$REPO" ]; then stop checkout_wrong "$REPO"; fi
    [[ "$REPO" =~ ^(/[A-Za-z0-9_.-]+)+$ ]] || stop checkout_path "$REPO"
    git -C "$REPO" remote get-url origin >/dev/null 2>&1 || stop no_origin
    status="$(git -C "$REPO" status --porcelain --untracked-files=all 2>/dev/null || true)"
    if [ -n "$status" ]; then stop checkout_dirty "$(oneline "$(printf '%s' "$status" | head -n 3 | tr '\n' ';')" 160)"; fi
    say "clone $REPO at $(git -C "$REPO" rev-parse --short HEAD)"
    # who deploys
    if [ "$OPT_DEPLOY_USER" != root ]; then
        getent passwd "$OPT_DEPLOY_USER" >/dev/null || stop deploy_user_invalid "the account $OPT_DEPLOY_USER does not exist: create it with adduser $OPT_DEPLOY_USER   then run the same command again."
        id -nG "$OPT_DEPLOY_USER" | tr ' ' '\n' | grep -qx docker \
            || stop deploy_user_invalid "$OPT_DEPLOY_USER cannot use docker: run usermod -aG docker $OPT_DEPLOY_USER   then run the same command again."
        [ "$(stat -c %U "$REPO")" = "$OPT_DEPLOY_USER" ] \
            || stop deploy_user_invalid "the clone must belong to $OPT_DEPLOY_USER: run chown -R $OPT_DEPLOY_USER: $REPO   then run the same command again."
    fi
    # disk and memory, against the runbook's figures
    local root free total available
    root="$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || true)"
    [ -d "$root" ] || root="$REPO"
    free="$(free_gib "$root")"
    [ "$free" -ge "$MIN_FREE_GIB" ] || stop disk_low "$free" "$root" "$MIN_FREE_GIB"
    available="$(mem_field_mib MemAvailable)"
    total="$(mem_field_mib MemTotal)"
    [ "${available:-0}" -ge "$STOP_RAM_AVAILABLE_MIB" ] || stop ram_low "${available:-0}" "$STOP_RAM_AVAILABLE_MIB"
    say "disk free $free GiB on $root; memory ${available} MiB available of ${total} MiB"
    if [ "${total:-0}" -lt "$WARN_RAM_TOTAL_MIB" ]; then
        warn "this server has ${total} MiB of memory; the image build can be slow, and deploy.sh stops an overloaded build by itself (a STOP [host_overloaded] then says to wait and run again)"
    fi
    # ports
    if [ ! -f "$ENV_FILE" ] && port_listening "$HTTP_PORT"; then stop http_port_busy "$HTTP_PORT"; fi
    if [ -n "$OPT_DOMAIN" ]; then
        local port
        for port in 80 443; do
            if port_listening "$port" && ! port_holder_is_ours "$port"; then
                stop public_port_busy "$port" "another program (see: ss -ltnp 'sport = :$port')"
            fi
        done
    fi
    return 0
}

# ------------------------------------------------------------------------------------------------------------ 2 env
stage_env() {
    local problems
    mkdir -p "$ENV_DIR"
    if [ ! -f "$ENV_FILE" ]; then
        local args=(create --env-dir "$ENV_DIR" --instance "$INSTANCE" --http-port "$HTTP_PORT") setting
        for setting in ${OPT_SETS[@]+"${OPT_SETS[@]}"}; do args+=(--set "$setting"); done
        if ! problems="$(python3 -I "$ENV_HELPER" "${args[@]}" 2>&1)"; then stop env_invalid "$(oneline "$problems" 200)"; fi
        say "$problems"
    else
        say "alpha.env already exists: kept as it is"
        if [ "${#OPT_SETS[@]}" -gt 0 ]; then warn "--set is used only for a NEW alpha.env; the existing one was not changed"; fi
    fi
    if ! problems="$(python3 -I "$ENV_HELPER" check --env "$ENV_FILE" --provider "$PROVIDER_FILE" --example "$ENV_EXAMPLE")"; then
        if printf '%s\n' "$problems" | grep -q 'must be 600'; then
            chmod 600 "$ENV_FILE"; [ ! -f "$PROVIDER_FILE" ] || chmod 600 "$PROVIDER_FILE"
            say "the environment files were readable by others: mode set to 600"
            problems="$(python3 -I "$ENV_HELPER" check --env "$ENV_FILE" --provider "$PROVIDER_FILE" --example "$ENV_EXAMPLE")" || stop env_invalid "$(oneline "$(printf '%s' "$problems" | tr '\n' ';')" 240)"
        else
            stop env_invalid "$(oneline "$(printf '%s' "$problems" | tr '\n' ';')" 240)"
        fi
    fi
    INSTANCE="$(env_get ALPHA_INSTANCE)"
    HTTP_PORT="$(env_get ALPHA_HTTP_PORT)"
    ALPHA_BASE="http://127.0.0.1:$HTTP_PORT/api/v1"
    say "environment is complete: instance $INSTANCE, application port $HTTP_PORT (loopback)"
}

# --------------------------------------------------------------------------------------------------------- 3 deploy
DEPLOY_LOG="" DEPLOY_STATUS=0

run_deploy() { # run_deploy LABEL: deploy.sh into DEPLOY_STATUS and a log outside the clone
    private_dir "$STATE_DIR"
    DEPLOY_LOG="$STATE_DIR/deploy-$1.log"
    say "running deploy.sh ($1): the first build takes ten minutes or more; do not interrupt it"
    DEPLOY_STATUS=0
    "$DEPLOY_DIR/deploy.sh" --env-file "$ENV_FILE" </dev/null 2>&1 | tee "$DEPLOY_LOG" || DEPLOY_STATUS="${PIPESTATUS[0]}"
}

deploy_gate_expected() { [ "$DEPLOY_STATUS" -eq 3 ] && grep -q '\[default_credential\]' "$DEPLOY_LOG"; }

stop_for_deploy() { # the one STOP for a deploy.sh that did not end well
    local refused
    refused="$(grep -m1 'REFUSED' "$DEPLOY_LOG" 2>/dev/null | sed 's/^deploy\.sh: REFUSED: //' || true)"
    if [ -z "$refused" ]; then stop deploy_failed "$DEPLOY_STATUS"; fi
    case "$refused" in
        *"public port"*"already in use"*) stop public_port_busy "$(printf '%s' "$refused" | sed -n 's/.*public port \([0-9]*\).*/\1/p')" "another program" ;;
        "port "*"already in use, and not by"*) stop http_port_busy "$HTTP_PORT" ;;
        *build_overload*|*overloaded*) stop host_overloaded ;;
        *"ACME client is not pinned"*) stop acme_unpinned ;;
        *"[default_credential]"*) stop admin_failed "deploy.sh still finds the published admin password valid" ;;
        *) stop deploy_refused "$(oneline "$refused" 380)" ;;
    esac
}

stage_deploy() {
    run_deploy first
    if [ "$DEPLOY_STATUS" -eq 0 ]; then
        say "the first deploy finished"
    elif deploy_gate_expected; then
        say "the first deploy ended [default_credential], which is expected on a fresh database: the next stage changes the administrator's password"
    else
        stop_for_deploy
    fi
}

# --------------------------------------------------------------------------------------------------------- 4 admin
password_file() { printf '%s/%s-admin-password.txt' "$SECRET_DIR" "$INSTANCE"; }

stage_admin() {
    local pfile output status
    pfile="$(password_file)"
    if ! state_has s4.admin_set; then
        python3 -I "$API_HELPER" wait --base "$ALPHA_BASE" --seconds "$ADMIN_WAIT_SECONDS" \
            || stop admin_failed "the stack did not answer on 127.0.0.1:$HTTP_PORT within $ADMIN_WAIT_SECONDS seconds"
        status=0
        output="$(python3 -I "$API_HELPER" admin --base "$ALPHA_BASE" --password-file "$pfile" --email "$OPT_EMAIL" 2>&1)" || status=$?
        printf '%s\n' "$output"
        case "$status" in
            0) ;;
            21) stop admin_unknown_password "$pfile" ;;
            *) stop admin_failed "$(oneline "$(last_line "$output")" 300)" ;;
        esac
        state_mark s4.admin_set
    else
        say "the administrator's account was finished by an earlier run"
    fi
    run_deploy second
    if [ "$DEPLOY_STATUS" -ne 0 ]; then stop_for_deploy; fi
    say "the credential gate is clean; the stack is deployed"
}

# --------------------------------------------------------------------------------------------------------- 5 norms
# fd 200 is this script's run lock; the detached importer `receive-bundle.sh import` starts must not keep it after this script ends.
inbound() { SSH_ORIGINAL_COMMAND="$*" BUNDLE_STAGING="$NORMS_STAGING" STAND_COPY_RECORD="$NORMS_COPY_DIR/record.json" \
    ALPHA_ENV_FILE="$ENV_FILE" "$DEPLOY_DIR/receive-bundle.sh" 200>&-; }
copy() { SSH_ORIGINAL_COMMAND="$*" ALPHA_CHECKOUT="$REPO" ALPHA_ENV_FILE="$ENV_FILE" STAND_COPY_DIR="$NORMS_COPY_DIR" \
    BUNDLE_STAGING="$NORMS_STAGING" "$DEPLOY_DIR/copy-serve.sh" 200>&-; }

# The tar push-bundle.sh sends, byte for byte (`bundle_tar` there; a test holds the two command lines equal).
bundle_tar() { # bundle_tar PARENT KEY
    tar --create --format=gnu --sort=name --owner=0 --group=0 --numeric-owner --mtime=@0 \
        --hard-dereference --mode='u+rwX,go+rX,go-w' --directory "$1" -- "$2"
}

NORMS_STATUS_OUT=""
norms_status() { # fills NORMS_STATUS_OUT from the inbound `status` verb
    NORMS_STATUS_OUT="$(inbound status 2>&1)" || stop norms_refused "$(oneline "$(last_line "$NORMS_STATUS_OUT")" 300)"
}
norms_import_state() { # the text after `import: ` of the bundle's line, or `absent`
    local line
    line="$(printf '%s\n' "$NORMS_STATUS_OUT" | awk -v k="$1" '$1 == "bundle:" && $2 == k { sub(/^.*  import: /, ""); print; exit }')"
    printf '%s' "${line:-absent}"
}
NORMS_REC_STAMP="" NORMS_REC_KIND="" NORMS_REC_STATE="" NORMS_REC_AGE=0 NORMS_REC_WINDOW=43200
norms_record() { # fills NORMS_REC_* from the copy key's `status`
    local out
    out="$(copy status 2>&1)" || stop norms_refused "$(oneline "$(last_line "$out")" 300)"
    NORMS_REC_STAMP="" NORMS_REC_KIND="none" NORMS_REC_STATE="none" NORMS_REC_AGE=0
    local line
    line="$(printf '%s\n' "$out" | awk '$1 == "record:" && $2 != "none" { print; exit }')"
    if [ -n "$line" ]; then
        NORMS_REC_STAMP="$(printf '%s\n' "$line" | awk '{ print $2 }')"
        NORMS_REC_KIND="$(printf '%s\n' "$line" | awk '{ print $4 }')"
        NORMS_REC_STATE="$(printf '%s\n' "$line" | awk '{ print $6 }')"
        NORMS_REC_AGE="$(printf '%s\n' "$out" | sed -n 's/^quiesced_at: .*age_seconds: \([0-9]*\).*/\1/p' | head -n 1)"
        NORMS_REC_WINDOW="$(printf '%s\n' "$out" | sed -n 's/^quiesced_at: .*window_seconds: \([0-9]*\).*/\1/p' | head -n 1)"
        NORMS_REC_AGE="${NORMS_REC_AGE:-0}"
        NORMS_REC_WINDOW="${NORMS_REC_WINDOW:-43200}"
    fi
}

norms_ensure_dirs() {
    local dir mode=700
    [ "$OPT_DEPLOY_USER" = root ] || mode=755   # deploy.sh's guards, run as that account, must be able to search both
    for dir in "$NORMS_COPY_DIR" "$NORMS_STAGING"; do
        [ -d "$dir" ] || mkdir -m "$mode" -- "$dir"
    done
}

norms_wait_for_import() { # norms_wait_for_import KEY -> returns when the import has an exit status; sets NORMS_EXIT
    local key="$1" state waited=0
    while :; do
        norms_status
        state="$(norms_import_state "$key")"
        case "$state" in
            exited\ *) NORMS_EXIT="${state#exited }"; return 0 ;;
            running*)
                if printf '%s\n' "$NORMS_STATUS_OUT" | grep -q '^import_lock: free$' && [ "$waited" -ge $(( POLL_SECONDS * 2 )) ]; then
                    stop norms_import_interrupted "$key"
                fi ;;
            *) stop norms_import_interrupted "$key" ;;
        esac
        if [ $(( waited % 300 )) -eq 0 ]; then
            say "importing $key ($(( waited / 60 )) min so far): $(printf '%s\n' "$NORMS_STATUS_OUT" | awk -v k="$key" '$1 == "bundle:" && $2 == k { f = 1; next } f && /^  \|/ { l = $0 } END { print l }' | cut -c1-160)"
        fi
        sleep "$POLL_SECONDS"
        waited=$(( waited + POLL_SECONDS ))
    done
}

stage_norms() {
    local bundle key parent size out status stamp
    bundle="$(cd "$OPT_BUNDLE" && pwd -P)"
    key="${bundle##*/}"
    parent="${bundle%/*}"
    if state_has s5.designated; then say "the norms snapshot was designated by an earlier run"; return 0; fi
    norms_ensure_dirs
    local available
    available="$(mem_field_mib MemAvailable)"
    [ "${available:-0}" -ge "$NORMS_RAM_AVAILABLE_MIB" ] || stop ram_low "${available:-0}" "$NORMS_RAM_AVAILABLE_MIB"

    # An open record that is not a test-data waiver is somebody's copy or import. `receive` would turn it into an import record
    # (its design: `W54-PLAN.md` section 3.5), so the stage looks first and touches nothing of another kind.
    norms_record
    if [ "$NORMS_REC_STATE" = open ] && [ "$NORMS_REC_KIND" != test_data_waiver ]; then
        stop norms_busy "record $NORMS_REC_STAMP, kind $NORMS_REC_KIND"
    fi

    # 1. the bundle: verified here (push-bundle.sh --dry-run applies the one bundle rule), then streamed into `receive`
    norms_status
    if [ "$(norms_import_state "$key")" = absent ]; then
        out="$("$DEPLOY_DIR/push-bundle.sh" --dry-run "$bundle" 2>&1)" \
            || stop norms_bundle_invalid "$bundle" "$(oneline "$(last_line "$out")" 200)"
        size="$(printf '%s\n' "$out" | sed -n 's/.*would send \([0-9][0-9]*\) bytes as.*/\1/p' | tail -n 1)"
        [[ "$size" =~ ^[0-9]+$ ]] || stop norms_bundle_invalid "$bundle" "its size could not be read"
        # STAND-NORMS-IMPORT-RUNBOOK-01.md section 0 item 4: staging holds the tar and its extraction (2 x size + 2 GiB);
        # Docker's volumes grow by the objects (size), PostgreSQL with its WAL (2.5 GB) and 2 GiB, each +25 %.
        local gib=1073741824 staging_free docker_root docker_free need_staging need_docker
        need_staging=$(( (2 * size + 2 * gib) / gib + 1 ))
        need_docker=$(( ((size + 5 * gib / 2 + 2 * gib) * 5 / 4) / gib + 1 ))
        staging_free="$(free_gib "$NORMS_STAGING")"
        docker_root="$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || true)"
        [ -d "$docker_root" ] || docker_root="$REPO"
        docker_free="$(free_gib "$docker_root")"
        if [ "$(stat -c %d "$NORMS_STAGING")" = "$(stat -c %d "$docker_root")" ]; then
            [ "$staging_free" -ge $(( need_staging + need_docker )) ] || stop norms_disk_low "$staging_free" "$NORMS_STAGING" $(( need_staging + need_docker ))
        else
            [ "$staging_free" -ge "$need_staging" ] || stop norms_disk_low "$staging_free" "$NORMS_STAGING" "$need_staging"
            [ "$docker_free" -ge "$need_docker" ] || stop norms_disk_low "$docker_free" "$docker_root" "$need_docker"
        fi
        say "sending $key ($size bytes) into the on-host receive; this takes minutes"
        status=0
        bundle_tar "$parent" "$key" | inbound receive "$key" "$size" || status=$?
        if [ "$status" -ne 0 ]; then
            stop norms_refused "receive ended with status $status; its REFUSED [guard] line is above"
        fi
    else
        say "the bundle $key is already received"
    fi

    # 2. the waiver and the importer
    norms_status
    local import_state
    import_state="$(norms_import_state "$key")"
    if [ "$import_state" = "not imported" ] || [ "${import_state#exited }" = 75 ]; then
        norms_record
        if [ "$NORMS_REC_STATE" = open ] && [ "$NORMS_REC_KIND" = test_data_waiver ] \
            && [ "$NORMS_REC_AGE" -gt $(( NORMS_REC_WINDOW - 7200 )) ] && [ "$import_state" = "not imported" ]; then
            say "the open waiver $NORMS_REC_STAMP has too little of its window left: closing it and opening a new one"
            copy resume "$NORMS_REC_STAMP" >/dev/null || stop norms_refused "resume of the old waiver was refused"
            norms_record
        fi
        case "$NORMS_REC_STATE:$NORMS_REC_KIND" in
            none:*|closed:*)
                out="$(copy attest --test-data 2>&1)" || stop norms_refused "$(oneline "$(last_line "$out")" 300)"
                printf '%s\n' "$out"
                norms_record ;;
            open:test_data_waiver) say "the open waiver $NORMS_REC_STAMP is used" ;;
            *) stop norms_busy "record $NORMS_REC_STAMP, kind $NORMS_REC_KIND" ;;
        esac
        out="$(inbound import "$key" 2>&1)" || stop norms_refused "$(oneline "$(last_line "$out")" 300)"
        printf '%s\n' "$out"
    elif [ "$import_state" = absent ]; then
        stop norms_refused "the bundle $key is not in the staging directory after the receive"
    fi
    norms_wait_for_import "$key"
    case "$NORMS_EXIT" in
        0) say "the importer finished" ;;
        *) stop norms_import_failed "$NORMS_EXIT" "$NORMS_STAGING/logs/$key.import.log" ;;
    esac

    # 3. the report (the record must still be open), then the writers back
    norms_record
    if [ "$NORMS_REC_STATE" = open ]; then
        stamp="$NORMS_REC_STAMP"
        if ! state_has s5.reported; then
            status=0
            inbound report "$key" || status=$?
            [ "$status" -eq 0 ] || stop norms_report_differs "$status" "$NORMS_STAGING/logs/$key.report"
            state_mark s5.reported
        fi
        out="$(copy resume "$stamp" 2>&1)" || stop norms_refused "$(oneline "$(last_line "$out")" 300)"
        printf '%s\n' "$out"
    fi
    "$DEPLOY_DIR/reload-proxy.sh" --env-file "$ENV_FILE" || warn "reload-proxy.sh ended with a non-zero status; verify-deployed.sh decides"

    # 4. the snapshot becomes the current one
    local content_key="${key%+*}"
    status=0
    out="$(python3 -I "$API_HELPER" designate --base "$ALPHA_BASE" --password-file "$(password_file)" --content-key "$content_key" 2>&1)" || status=$?
    printf '%s\n' "$out"
    [ "$status" -eq 0 ] || stop norms_designate_failed "$(oneline "$(last_line "$out")" 300)"
    state_mark s5.designated
}

# --------------------------------------------------------------------------------------------------------- 6 https
resolve_a_records() { getent ahostsv4 "$1" 2>/dev/null | awk '{ print $1 }' | sort -u; }

stage_https() {
    local records here public record matched=no
    records="$(resolve_a_records "$OPT_DOMAIN" || true)"
    public="$(public_ipv4)"
    if [ -z "$records" ]; then stop dns_missing "$OPT_DOMAIN" "${public:-the public IPv4 address of this server}"; fi
    here="$(local_ipv4s)"
    while IFS= read -r record; do
        [ -n "$record" ] || continue
        if [ "$record" = "$public" ] || printf '%s\n' "$here" | grep -qxF "$record"; then matched=yes; fi
    done <<<"$records"
    [ "$matched" = yes ] || stop dns_mismatch "$OPT_DOMAIN" "$(printf '%s' "$records" | tr '\n' ' ')" "${public:-an address this script could not determine}"
    say "DNS: $OPT_DOMAIN resolves to this server"

    local pin
    pin="$(sed -n 's/^ACME_CLIENT_APK_VERSION=//p' "$ACME_PIN" 2>/dev/null | tail -n 1)"
    if [ -z "$pin" ] || [ "$pin" = UNRESOLVED ]; then stop acme_unpinned; fi

    local verify=("$DEPLOY_DIR/verify-deployed.sh" --env-file "$ENV_FILE")
    if ! state_has s6.staging; then
        python3 -I "$ENV_HELPER" set --env "$ENV_FILE" "ALPHA_CERT_NAME=$OPT_DOMAIN" "ALPHA_ACME_EMAIL=$OPT_EMAIL" ALPHA_ACME_STAGING=yes
        run_deploy https-staging
        if [ "$DEPLOY_STATUS" -ne 0 ]; then stop_for_deploy; fi
        wait_for_certificate "${verify[@]}" --acme-rehearsal || stop acme_staging_failed "$CERT_WAIT_SECONDS" "$ENV_FILE" "$COMPOSE_FILE" "$ACME_OVERLAY"
        state_mark s6.staging
    fi
    if ! state_has s6.real; then
        python3 -I "$ENV_HELPER" set --env "$ENV_FILE" ALPHA_ACME_STAGING=no
        run_deploy https-real
        if [ "$DEPLOY_STATUS" -ne 0 ]; then stop_for_deploy; fi
        wait_for_certificate "${verify[@]}" || stop acme_real_failed "$CERT_WAIT_SECONDS" "$ENV_FILE" "$COMPOSE_FILE" "$ACME_OVERLAY"
        state_mark s6.real
    fi
    if ! state_has s6.published; then
        python3 -I "$ENV_HELPER" set --env "$ENV_FILE" ALPHA_PUBLISH_HTTPS=yes
        for _ in 1 2; do
            run_deploy https-publish
            if [ "$DEPLOY_STATUS" -ne 0 ]; then stop_for_deploy; fi
            if grep -q 'published on port' "$DEPLOY_LOG" && ! grep -q 'NOT published' "$DEPLOY_LOG"; then break; fi
            say "the deploy did not publish port 443 yet (the pair may have been exported just now): running it once more"
        done
        grep -q 'published on port' "$DEPLOY_LOG" || stop https_not_published "$(oneline "$(grep -m1 'TLS for\|443' "$DEPLOY_LOG" || echo 'no publication line')" 160)"
        state_mark s6.published
    fi
    say "HTTPS: https://$OPT_DOMAIN is published on port 443"
}

wait_for_certificate() { # wait_for_certificate VERIFY-COMMAND...: polls verify-deployed.sh until 0 or the time is up
    local waited=0 status
    while :; do
        status=0
        "$@" </dev/null >/dev/null 2>&1 || status=$?
        [ "$status" -ne 0 ] || return 0
        [ "$waited" -lt "$CERT_WAIT_SECONDS" ] || return 1
        say "waiting for the certificate (verify-deployed.sh status $status; ${waited}s of ${CERT_WAIT_SECONDS}s)"
        sleep "$POLL_SECONDS"
        waited=$(( waited + POLL_SECONDS ))
    done
}

# ---------------------------------------------------------------------------------------------------- 7 executors
stage_executors() {
    local status out
    status=0
    out="$("$DEPLOY_DIR/local-agent.sh" --env-file "$ENV_FILE" status 2>&1)" || status=$?
    printf '%s\n' "$out" | sed 's/^/  /'
    if ! printf '%s\n' "$out" | grep -q 'access=subscription auth=valid'; then stop executors_login_needed; fi
    status=0
    out="$("$DEPLOY_DIR/local-agent.sh" --env-file "$ENV_FILE" connect 2>&1)" || status=$?
    printf '%s\n' "$out" | sed 's/^/  /'
    [ "$status" -eq 0 ] || stop executors_not_connected "$status"
    say "this server's own subscriptions are connected as «Этот сервер»"
}

# ------------------------------------------------------------------------------------------------------- 8 verify
stage_verify() {
    local status=0
    "$DEPLOY_DIR/verify-deployed.sh" --env-file "$ENV_FILE" </dev/null || status=$?
    [ "$status" -eq 0 ] || stop verify_failed "$status"
    say "verify-deployed.sh: the running stack is this tree"
}

# ------------------------------------------------------------------------------------------------------- 9 github
GITHUB_HOST="" CI_KEY_FILE=""

stage_github() {
    local repo_name fingerprint key_line host
    repo_name="$(git -C "$REPO" remote get-url origin | sed -E 's#/+$##; s#\.git$##; s#^.*[:/]([^:/]+)/([^:/]+)$#\1/\2#')"
    host="${OPT_DOMAIN:-$(public_ipv4)}"
    GITHUB_HOST="${host:-<the public IPv4 address of this server>}"
    printf '\nfirst-install: ---- for the owner: connect GitHub auto-deploy (Settings > Secrets and variables > Actions of %s) ----\n' "$repo_name"
    printf '  variable DEPLOY_HOST        %s\n' "$GITHUB_HOST"
    printf '  variable DEPLOY_PATH        %s\n' "$REPO"
    if [ -r "$HOST_KEY_PUB" ]; then
        key_line="$(awk -v h="$GITHUB_HOST" '{ print h " " $1 " " $2; exit }' "$HOST_KEY_PUB")"
        fingerprint="$(ssh-keygen -lf "$HOST_KEY_PUB" 2>/dev/null | awk '{ print $2 }' || true)"
        printf '  variable DEPLOY_KNOWN_HOSTS %s\n' "$key_line"
        printf '    the key fingerprint is %s ; compare it with: ssh-keyscan -t ed25519 %s | ssh-keygen -lf -\n' "${fingerprint:-unknown}" "$GITHUB_HOST"
    else
        warn "$HOST_KEY_PUB does not exist: take the host key line for DEPLOY_KNOWN_HOSTS from another key type of this server (ssh-keygen -lf /etc/ssh/ssh_host_*_key.pub)"
    fi
    printf '  secret   VPS_USER           %s\n' "$OPT_DEPLOY_USER"
    CI_KEY_FILE="$SECRET_DIR/$INSTANCE-deploy-key"
    if [ "$OPT_NO_CI_KEY" = yes ]; then
        printf '  secret   VPS_SSH_KEY        the private key of an account that may log in as %s (no key was generated: --no-ci-key)\n' "$OPT_DEPLOY_USER"
    else
        ensure_ci_key
        printf '  secret   VPS_SSH_KEY        the whole content of the file %s (root-only; the owner copies it and then deletes the file)\n' "$CI_KEY_FILE"
    fi
    if [ "$OPT_DEPLOY_USER" != root ]; then
        printf '  sudoers  (visudo -f /etc/sudoers.d/%s-local-agent)   %s ALL=(root) NOPASSWD: %s/infra/deploy/local-agent.sh\n' \
            "$INSTANCE" "$OPT_DEPLOY_USER" "$REPO"
    fi
    printf '  the server deploys only the repository it was cloned from: %s\n' "$repo_name"
}

ensure_ci_key() {
    local public home auth
    if [ ! -e "$CI_KEY_FILE" ]; then
        ssh-keygen -q -t ed25519 -N '' -C "$INSTANCE-first-install" -f "$CI_KEY_FILE" >/dev/null
        chmod 600 "$CI_KEY_FILE"
        say "a deploy key was generated: $CI_KEY_FILE (private, root-only; its content is never printed)"
    fi
    public="$(awk '{ print $1 " " $2 }' "$CI_KEY_FILE.pub")"
    if [ "$TEST_MODE" = yes ] && [ -n "${FIRST_INSTALL_AUTH_HOME:-}" ]; then
        home="$FIRST_INSTALL_AUTH_HOME"
    else
        home="$(getent passwd "$OPT_DEPLOY_USER" | cut -d: -f6)"
    fi
    auth="$home/.ssh/authorized_keys"
    if [ -f "$auth" ] && grep -qF "$public" "$auth"; then
        return 0
    fi
    [ -d "$home/.ssh" ] || private_dir "$home/.ssh"
    printf '%s\n' "$(cat "$CI_KEY_FILE.pub")" >> "$auth"
    chmod 600 "$auth"
    if [ "$OPT_DEPLOY_USER" != root ] && [ "$TEST_MODE" = no ]; then chown -R "$OPT_DEPLOY_USER": "$home/.ssh"; fi
    say "the deploy key's public half is authorized for $OPT_DEPLOY_USER"
}

# ------------------------------------------------------------------------------------------------------- 10 marker
stage_marker() {
    local when sha
    when="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    sha="$(git -C "$REPO" rev-parse HEAD)"
    private_dir "$STATE_DIR"
    {
        printf 'first-install: done\n'
        printf 'date=%s\ninstance=%s\nsha=%s\nrepo=%s\n' "$when" "$INSTANCE" "$sha" "$REPO"
        printf 'domain=%s\nadmin_login=%s\n' "${OPT_DOMAIN:-none}" "$(admin_login)"
        printf 'stage_1_preflight=ok\nstage_2_env=ok\nstage_3_deploy=ok\nstage_4_admin=ok\n'
        printf 'stage_5_norms=%s\n' "$([ -n "$OPT_BUNDLE" ] && echo ok || echo skipped)"
        printf 'stage_6_https=%s\n' "$([ -n "$OPT_DOMAIN" ] && echo ok || echo skipped)"
        printf 'stage_7_executors=%s\n' "$([ "$OPT_SKIP_EXECUTORS" = yes ] && echo skipped || echo ok)"
        printf 'stage_8_verify=ok\nstage_9_github=printed\n'
    } > "$MARKER.tmp"
    mv -f "$MARKER.tmp" "$MARKER"
    say "marker written: $MARKER"
}

admin_login() { # the login line of the password file, which is not a secret (the password is on the next line)
    sed -n 's/^login=//p' "$(password_file)" 2>/dev/null | head -n 1 || true
}

# ----------------------------------------------------------------------------------------------------------- runner
STAGE_TITLES=(
    "preflight: root, tools, Docker, disk, memory, ports, a clean clone"
    "env: alpha.env and provider.env from the examples, every secret generated (mode 600)"
    "deploy: the first deploy.sh, without published HTTPS"
    "admin: the administrator's password and profile through the loopback API; deploy.sh again"
    "norms: import the norms bundle on this host and make it the current snapshot"
    "https: DNS, test certificate, real certificate, public port 443"
    "executors: connect this server's own claude / codex subscriptions"
    "verify: verify-deployed.sh must exit 0"
    "github: what to paste into GitHub, and the deploy key"
    "marker: write the done marker; a second run refuses"
)

run_stage() { # run_stage N FUNCTION
    local n="$1" fn="$2"
    stage_header "$n" "${STAGE_TITLES[$((n - 1))]}"
    # Stages 1 and 2 are cheap and always run: the server and the environment file may have changed since the last run.
    if [ "$n" -gt 2 ] && [ "$n" -lt 9 ] && state_has "s$n"; then
        say "done before: skipped"
        return 0
    fi
    "$fn"
    if [ "$n" -lt 9 ]; then state_mark "s$n"; fi
    return 0
}

run_all() {
    run_stage 1 stage_preflight
    run_stage 2 stage_env
    run_stage 3 stage_deploy
    run_stage 4 stage_admin
    if [ -n "$OPT_BUNDLE" ]; then run_stage 5 stage_norms; else stage_header 5 "${STAGE_TITLES[4]}"; say "skipped: no --norms-bundle"; fi
    if [ -n "$OPT_DOMAIN" ]; then run_stage 6 stage_https; else stage_header 6 "${STAGE_TITLES[5]}"; say "skipped: no --domain (the stack answers on 127.0.0.1:$HTTP_PORT; reach it with: ssh -L $HTTP_PORT:127.0.0.1:$HTTP_PORT <this server>)"; fi
    if [ "$OPT_SKIP_EXECUTORS" = no ]; then run_stage 7 stage_executors; else stage_header 7 "${STAGE_TITLES[6]}"; say "skipped: --skip-executors"; fi
    run_stage 8 stage_verify
    run_stage 9 stage_github
    run_stage 10 stage_marker
    local login
    login="$(admin_login)"
    printf '\n'
    printf 'DONE: %s is installed at %s (%s). Administrator login %s; its password is in %s (owner only, do not read it).%s Full output: %s\n' \
        "$INSTANCE" "$REPO" "$(git -C "$REPO" rev-parse --short HEAD)" "${login:-unknown}" "$(password_file)" \
        "$([ -n "$OPT_DOMAIN" ] && echo " Open https://$OPT_DOMAIN." || echo " Open it through: ssh -L $HTTP_PORT:127.0.0.1:$HTTP_PORT <this server> then http://127.0.0.1:$HTTP_PORT.")" \
        "$LOG_FILE"
}

# --------------------------------------------------------------------------------------------------------- dry run
print_plan() {
    local n done_text
    printf 'first-install: DRY RUN -- nothing below is done; nothing on this server is changed.\n'
    printf '  instance         %s\n  clone            %s\n  environment      %s\n' "$INSTANCE" "$REPO" "$ENV_FILE"
    printf '  application port %s (loopback only)\n  domain           %s\n  administrator    %s\n' "$HTTP_PORT" "${OPT_DOMAIN:-none (no HTTPS)}" "${OPT_EMAIL:-<--email is required>}"
    printf '  norms bundle     %s\n  deploy user      %s\n' "${OPT_BUNDLE:-none}" "$OPT_DEPLOY_USER"
    printf '  state            %s\n  marker           %s\n  password file    %s\n  transcript       %s\n' "$STATE_FILE" "$MARKER" "$(password_file)" "$LOG_FILE"
    if [ -f "$MARKER" ] && [ -z "$OPT_RESUME" ]; then printf '  NOTE: the marker exists: a real run would stop with STOP [already_installed].\n'; fi
    local would=(
        "check that this is root, that git curl flock tar python3 ssh-keygen are present, that Docker 20+ and compose v2 answer, that at least $MIN_FREE_GIB GiB of disk and $STOP_RAM_AVAILABLE_MIB MiB of memory are free, that the clone is clean, and (with --domain) that ports 80 and 443 are free"
        "create $ENV_FILE and $PROVIDER_FILE from the examples if they are absent (mode 600; every secret generated, in every place it is written; an existing file is never changed)"
        "run infra/deploy/deploy.sh; on a fresh database it ends [default_credential], which is expected"
        "generate the administrator's password into $(password_file) (mode 600), change it through the API, complete the profile with ${OPT_EMAIL:-the --email address}, run deploy.sh again"
        "$([ -n "$OPT_BUNDLE" ] && echo "verify $OPT_BUNDLE, stream it into receive-bundle.sh on this host, open a test-data waiver with copy-serve.sh, import, report, resume, designate the snapshot" || echo "skipped (no --norms-bundle)")"
        "$([ -n "$OPT_DOMAIN" ] && echo "check that DNS $OPT_DOMAIN points here; set the name; deploy with the test certificate, then the real one, then ALPHA_PUBLISH_HTTPS=yes" || echo "skipped (no --domain)")"
        "$([ "$OPT_SKIP_EXECUTORS" = no ] && echo "connect the claude / codex subscriptions of this server through local-agent.sh; stop with a printed instruction when none is signed in" || echo "skipped (--skip-executors)")"
        "run infra/deploy/verify-deployed.sh; it must exit 0"
        "print DEPLOY_HOST, DEPLOY_KNOWN_HOSTS (with the host key fingerprint) and DEPLOY_PATH$([ "$OPT_NO_CI_KEY" = no ] && echo ", generate $SECRET_DIR/$INSTANCE-deploy-key and authorize it for $OPT_DEPLOY_USER (the private key is never printed)")"
        "write the marker $MARKER and print the DONE line"
    )
    for n in $(seq 1 10); do
        done_text=""
        if [ "$n" -eq 2 ] && [ -f "$ENV_FILE" ]; then done_text=" [already there: kept]"; fi
        if [ "$n" -gt 2 ] && [ "$n" -lt 9 ] && state_has "s$n"; then done_text=" [done before: would be skipped]"; fi
        printf '\n[%s/10] %s%s\n      would: %s\n' "$n" "${STAGE_TITLES[$((n - 1))]%%:*}" "$done_text" "${would[$((n - 1))]}"
    done
    printf '\nfirst-install: end of the dry run.\n'
}

main() {
    parse_args "$@"
    validate_args
    resolve_instance
    if [ "$OPT_DRY_RUN" = yes ]; then
        print_plan
        exit 0
    fi
    if [ -f "$MARKER" ] && [ -z "$OPT_RESUME" ]; then
        stop already_installed "$(sed -n 's/^date=//p' "$MARKER" | head -n 1)" "$MARKER"
    fi
    [ "$(id -u)" -eq 0 ] || [ "$TEST_MODE" = yes ] || stop not_root
    mkdir -p "$LOG_DIR"
    # One run at a time: an agent whose tool timed out may start the command again while the first still works.
    private_dir "$STATE_DIR"
    exec 200>"$STATE_DIR/first-install.lock"
    flock -n 200 || stop already_running "$LOG_FILE"
    if [ -n "$OPT_RESUME" ]; then
        state_clear_from "$OPT_RESUME"
    fi
    local rc=0
    { run_all; } 2>&1 | tee -a "$LOG_FILE" || rc="${PIPESTATUS[0]}"
    exit "$rc"
}

# Sourced by the tests: the functions are there and nothing runs.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi
