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
RELEASE_LOCK="$REPO/infra/norms/bundle-release.lock"
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
OS_RELEASE="$(seam OS_RELEASE /etc/os-release)"
KEYRINGS_DIR="$(seam KEYRINGS_DIR /etc/apt/keyrings)"
APT_SOURCES_DIR="$(seam APT_SOURCES_DIR /etc/apt/sources.list.d)"
SAMPLE_SECONDS="$(seam SAMPLE_SECONDS 2)"
DOCKER_WAIT_SECONDS="$(seam DOCKER_WAIT_SECONDS 30)"
DEPLOY_ROOT="$(seam DEPLOY_ROOT /srv)"
RELEASE_BASE="$(seam RELEASE_BASE https://github.com)"             # where a public release's assets are downloaded from
RELEASE_API_BASE="$(seam RELEASE_API_BASE https://api.github.com)" # used only with a read token, for a private repository
RELEASE_RETRIES="$(seam RELEASE_RETRIES 3)"
RELEASE_RETRY_DELAY="$(seam RELEASE_RETRY_DELAY 5)"
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
# NORM-VECTOR-TEMP-01 rollout step 3: "available memory stays above 600 MB and swap does not grow".
SEMANTIC_MIN_AVAILABLE_MIB=600
SEMANTIC_URL=http://norm-embed:8080
SEMANTIC_WINDOWS=500
# Docker's own signing key, from https://download.docker.com/linux/{debian,ubuntu}/gpg (one file for both). The installer trusts the
# download only when its fingerprint is this one; read from the live key on 2026-11-20.
DOCKER_KEY_FPR=9DC858229FC7DD38854AE2D88D81803C0EBFCD88
DOCKER_PACKAGES=(docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin)
DEFAULT_INSTANCE=auditmanager
DEFAULT_HTTP_PORT=31500

# ----------------------------------------------------------------------------------------------------------- STOP codes
# THE SINGLE SOURCE. One line per code: `code|text`. The text is a printf format whose `%s` the stop call fills with the facts of
# this run, and it is the whole of the action. THREE KINDS, told apart by how the text begins:
#
#   * no prefix: something the reader does itself, exactly as printed (a command, or "run the same command again"), because the
#     script could not do it for the reader. Most codes are of this kind.
#   * `ASK THE OWNER`: a fact only the owner holds -- an e-mail address, the domain, a record at the registrar, a sign-in to a
#     subscription, the provider's firewall, money. Never a technical question; the text says what is needed.
#   * `REPORT TO THE OWNER`: a failure with no safe automatic action. The reader shows the line (and the last 30 lines of output) and
#     stops; nothing is retried.
#
# `--print-codes` prints this table; the prompt for a simple agent carries the same table and a test holds the two equal. Another
# test holds the two prefixes to a short list of codes (OWNER_FACT_CODES and REPORT_CODES there). A text may not hold `|`.
CODES_TABLE="$(cat <<'TABLE'
usage|Fix the command line as the lines above say (--help shows it), then run the same command again.
not_root|Run the same command with sudo (as root).
tool_missing|Install the missing tools with this one command: %s   then run the same command again.
docker_missing|Install Docker Engine with its compose plugin with this one command: %s   then run the same command again.
docker_install_failed|Run the same command once more (a network error is the usual cause). What failed: %s
docker_key_mismatch|REPORT TO THE OWNER: the Docker package key from download.docker.com has the fingerprint %s, not the pinned %s. Nothing was installed. Do not retry: the download may have been tampered with.
docker_down|REPORT TO THE OWNER: Docker is installed but does not start even after systemctl enable --now docker. Show the owner the output of: journalctl -u docker --no-pager -n 40
docker_old|REPORT TO THE OWNER: %s Containers are running on this server and upgrading Docker restarts them, so it is not done automatically.
checkout_wrong|Run the script from its own clone: cd %s   and then the same command again.
checkout_dirty|The deploy clone %s has local changes (%s) and must not be edited or cleaned. Run this command (it makes a clean clone at a free path and works there): %s
deploy_path_unusable|%s cannot be the deploy clone: %s. Run this command (it uses a free path; nothing at the old path is touched): %s
deploy_clone_installed|REPORT TO THE OWNER: %s holds an installation's secrets but %s, so it cannot be used and must not be replaced.
no_origin|This clone has no 'origin' remote, which auto-deploy needs, but it has the remote %s. Run this command: git -C %s remote add origin %s   then run the same command again.
no_origin_url|ASK THE OWNER for the repository's clone URL: %s has no remote to read it from. Then run this command: git -C %s remote add origin URL   and run the same command again.
clone_needs_access|ASK THE OWNER to give this server read access to the repository %s: for a private repository a read-only deploy key (the repository's Settings, Deploy keys) or an https address with an access token. Then run the same command again.
clone_failed|Run the same command once more (a network error is the usual cause). What failed: %s
deploy_user_invalid|Run this command: %s   then run the same command again.
disk_low|Free disk space is %s GiB on %s and %s GiB are needed. Run this command: docker builder prune -af   (it removes build cache only) and then run the same command again.
disk_too_small|ASK THE OWNER for a larger disk: %s GiB are free on %s, %s GiB are needed, and clearing the build cache did not help. It costs money, so only the owner decides.
ram_low|Only %s MiB of memory are available and %s MiB are needed. Wait five minutes so that other work on the server can finish, then run the same command again.
ram_too_small|ASK THE OWNER for a server with more memory: %s MiB are available and %s MiB are needed, and waiting did not help. It costs money, so only the owner decides.
http_port_busy|Port %s on this server is already in use. Run the same command again with --http-port %s added (that port is free).
public_port_busy|ASK THE OWNER whether %s may be stopped: it holds public port %s, which the certificate needs, and it serves something else on this server. When the owner has stopped it, run the same command again.
instance_invalid|Run again with --instance made of 3 to 40 lower-case letters, digits and '-', starting with a letter (for example auditmanager).
instance_mismatch|Run the same command again with --instance %s, or without --instance: the existing environment file already belongs to that instance.
domain_invalid|ASK THE OWNER for the server's public DNS name: %s is not one. It is lower case, has a dot, no scheme and no port, for example audit.mycompany.ru.
email_required|ASK THE OWNER for an e-mail address. It becomes the administrator's login and the certificate contact. Then run the same command again with --email ADDRESS.
email_invalid|ASK THE OWNER for a plain e-mail address (letters, digits and . _ + - around one @): %s is not one. Then run the same command again with --email ADDRESS.
env_invalid|The environment file is not usable (%s) and nothing has been deployed from it. Run this command: %s   then run the same command again (it writes new files).
env_invalid_installed|REPORT TO THE OWNER: the environment file is not usable (%s) and this server already has an installation made from it, so it must not be replaced.
already_installed|Nothing to do: this server was installed on %s (marker %s). To add the norms bundle later run: sudo infra/deploy/first-install.sh --norms-bundle DIRECTORY
already_running|An earlier run of this command is still working: do not start another. Wait five minutes, look at the end of %s with tail -n 30, and run the same command again only when that file has not changed for fifteen minutes.
deploy_refused|REPORT TO THE OWNER: deploy.sh refused for a reason this installer does not know: %s
deploy_failed|Run the same command once more (deploy.sh ended with status %s; a network error during the build is the usual cause).
host_overloaded|The server is overloaded. Wait five minutes, then run the same command again.
acme_unpinned|The deploy clone predates the certificate client's pin. Run this command: git -C %s fetch origin && git -C %s checkout --detach origin/HEAD   then run the same command again.
dns_missing|ASK THE OWNER to create a DNS A record at the domain registrar: name %s, address %s. Then wait a few minutes and run the same command again.
dns_mismatch|ASK THE OWNER to change the DNS A record of %s at the domain registrar: it points to %s and must point to %s (this server). Then wait a few minutes and run the same command again.
acme_staging_failed|ASK THE OWNER to open public ports 80 and 443 in the server provider's firewall and to check the DNS record of %s: the test certificate was not issued within %s seconds. What the authority said: %s. Then run the same command again.
acme_real_failed|ASK THE OWNER: the real certificate was not issued within %s seconds. What the authority said: %s. A rate limit means waiting or choosing another name, which only the owner can do. Then run the same command again.
https_not_published|REPORT TO THE OWNER: the deploy finished but public port 443 is not published (%s).
admin_failed|REPORT TO THE OWNER: the administrator account could not be finished (%s). The password file is never printed.
admin_unknown_password|ASK THE OWNER to write the administrator's current login and password himself into %s as two lines, login=... and password=... (mode 600). Never ask for them in a message. Then run the same command again.
norms_bundle_invalid|ASK THE OWNER for the norms bundle directory: %s is not usable (%s).
norms_disk_low|Free disk space is too small for the norms import: %s GiB are free on %s and about %s GiB are needed. Run this command: docker builder prune -af   and then run the same command again.
norms_disk_too_small|ASK THE OWNER for a larger disk: %s GiB are free on %s, about %s GiB are needed for the norms import, and clearing the build cache did not help. It costs money, so only the owner decides.
norms_lock_invalid|REPORT TO THE OWNER: infra/norms/bundle-release.lock is not a lock this installer reads (%s). The owner publishes the bundle again with infra/norms/publish-bundle-release.sh and commits the lock file it writes.
norms_release_missing|REPORT TO THE OWNER: the norms release %s of the repository %s has no asset %s, or the release is gone. The owner publishes the bundle again with infra/norms/publish-bundle-release.sh and commits the lock file it writes.
norms_download_failed|The norms download did not finish (%s). Wait a few minutes, then run the same command again: it resumes where it stopped.
norms_download_corrupt|REPORT TO THE OWNER: the downloaded norms part %s has the sha256 %s but the lock file says %s, also after it was downloaded again. The release asset is not what was published; nothing was imported.
norms_busy|REPORT TO THE OWNER: another copy or import is open (%s) and was not touched.
norms_wait|Another copy or import step holds a lock (%s). Wait five minutes, then run the same command again.
norms_refused|REPORT TO THE OWNER: the norms transfer or import was refused: %s
norms_import_unfinished|The norms importer ended unfinished three times (status 75: the object store was unavailable). Wait ten minutes, then run the same command again; importing again is safe.
norms_import_failed|REPORT TO THE OWNER: the norms import ended with status %s (2 is a refusal, 1 a mismatch). Its log is %s
norms_report_differs|REPORT TO THE OWNER: the norms import finished but its report does not match (status %s). Nothing was designated and the writers stay stopped. The report is %s
norms_designate_failed|REPORT TO THE OWNER: the norms snapshot could not be made current (%s).
semantic_memory_low|Semantic norm lookup stays OFF, and the stack works on word search. The memory gate failed: %s. Wait ten minutes, then run the same command again; both gates are measured again.
semantic_quality_failed|REPORT TO THE OWNER: semantic norm lookup stays OFF (the stack works on word search; nothing is broken). The quality gate failed: %s. The lookup needs more memory and the full-precision model, which is the owner's decision. If the owner accepts word search only, run this command: %s
semantic_check_failed|The quality gate could not run (%s). Semantic norm lookup stays OFF and the stack works on word search. Run the same command once more.
semantic_worker_failed|The worker did not start with the embedder address, so the address was taken out again and the stack works on word search. Run the same command once more. What failed: %s
executors_login_needed|ASK THE OWNER to sign this server in to his subscription: as root run claude (and/or codex login) and finish the sign-in in the browser. Then run the same command again. If the owner does not want this server's own subscriptions, run the same command again with --skip-executors added.
executors_not_connected|REPORT TO THE OWNER: signed-in subscriptions were found but local-agent.sh could not connect them (status %s).
verify_failed|REPORT TO THE OWNER: verify-deployed.sh ended with status %s, also after the proxy was reloaded.
unexpected|REPORT TO THE OWNER: the script failed at line %s.
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
    text="$(printf '%s' "$text" | tr '\r\n\t' '   ')"
    # A STOP line is read as a command and run as printed, so it is never cut: an action too long to print
    # whole becomes a report instead of a truncated command that would run with a wrong path.
    if [ "${#text}" -gt 4000 ]; then
        text="REPORT TO THE OWNER: the action of this stop is longer than 4000 characters and is not printed, so that no cut command is run. Show the owner the last 30 lines of ${LOG_FILE:-the output above}."
    fi
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
STAGE_COUNT=11
stage_header() { printf '\nfirst-install: [%s/%s] %s\n' "$1" "$STAGE_COUNT" "$2"; }

usage() {
    cat <<'USAGE'
usage: sudo infra/deploy/first-install.sh --email ADDRESS [options]

  --email ADDRESS        the administrator's login and the certificate contact (required)
  --domain NAME          the server's public DNS name: also gets a certificate and public port 443
  --norms-bundle DIR     import this norms bundle directory on this host and make it the current snapshot
  --instance NAME        the name of this installation (default auditmanager)
  --http-port N          the loopback port of the application (default 31500)
  --deploy-user NAME     the account GitHub auto-deploy logs in as (default root)
  --deploy-path PATH     the server's own checkout, made by the installer from this clone's origin (default /srv/<instance>)
  --set NAME=VALUE       one more setting for a NEW alpha.env (repeatable; the example file's names only).
                         --set ALPHA_NORM_EMBED=no (the owner's choice) turns the semantic norm lookup off, also later
  --no-ci-key            do not generate a deploy key for GitHub auto-deploy
  --skip-executors       do not require this server's own claude/codex subscriptions (the owner decides)
  --resume-stage N       run again from stage N (1-10), also after the installation is marked done
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
OPT_EMAIL="" OPT_DOMAIN="" OPT_BUNDLE="" OPT_INSTANCE="" OPT_HTTP_PORT="" OPT_DEPLOY_USER=root OPT_DEPLOY_PATH=""
OPT_NO_CI_KEY=no OPT_SKIP_EXECUTORS=no OPT_RESUME="" OPT_DRY_RUN=no
OPT_SETS=()

parse_args() {
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --email|--domain|--norms-bundle|--instance|--http-port|--deploy-user|--deploy-path|--set|--resume-stage)
                if [ "$#" -lt 2 ] || [ -z "$2" ]; then usage_error "$1 needs a value"; fi
                case "$1" in
                    --email) OPT_EMAIL="${2,,}" ;;
                    --domain) OPT_DOMAIN="${2,,}" ;;
                    --norms-bundle) OPT_BUNDLE="$2" ;;
                    --instance) OPT_INSTANCE="$2" ;;
                    --http-port) OPT_HTTP_PORT="$2" ;;
                    --deploy-user) OPT_DEPLOY_USER="$2" ;;
                    --deploy-path) OPT_DEPLOY_PATH="$2" ;;
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
        [[ "$OPT_RESUME" =~ ^([1-9]|10)$ ]] || usage_error "--resume-stage is a number from 1 to 10"
    fi
    [[ "$OPT_DEPLOY_USER" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]] || usage_error "--deploy-user is a lower-case account name"
    if [ -n "$OPT_DEPLOY_PATH" ]; then
        # The same rule the auto-deploy workflow applies to DEPLOY_PATH.
        if ! [[ "$OPT_DEPLOY_PATH" =~ ^(/[A-Za-z0-9_.-]+)+$ ]] || [[ "$OPT_DEPLOY_PATH/" == */../* ]] || [[ "$OPT_DEPLOY_PATH/" == */./* ]]; then
            usage_error "--deploy-path is an absolute path of letters, digits, '.', '_' and '-' (no . or .. component)"
        fi
    fi
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

DEPLOY_PATH="" REPO_REAL="" DEPLOY_REAL=""
# Where the production checkout is: --deploy-path, else this clone when an installation was already made in it (it IS the deploy
# clone, and a second stack of the same name on this host would collide), else /srv/<instance>.
decide_deploy_path() {
    if [ -n "$OPT_DEPLOY_PATH" ]; then
        DEPLOY_PATH="$OPT_DEPLOY_PATH"
    elif [ -f "$ENV_FILE" ] && [[ "$REPO" =~ ^(/[A-Za-z0-9_.-]+)+$ ]]; then
        DEPLOY_PATH="$REPO"
    else
        DEPLOY_PATH="$DEPLOY_ROOT/$INSTANCE"
    fi
    REPO_REAL="$REPO"
    if [ -d "$DEPLOY_PATH" ]; then DEPLOY_REAL="$(cd "$DEPLOY_PATH" && pwd -P)"; else DEPLOY_REAL="$DEPLOY_PATH"; fi
}

state_has() { [ -f "$STATE_FILE" ] && grep -qxF "$1=ok" "$STATE_FILE"; }
state_mark() {
    private_dir "$STATE_DIR"
    state_has "$1" || printf '%s=ok\n' "$1" >> "$STATE_FILE"
}
state_unset() { [ ! -f "$STATE_FILE" ] || { grep -vxF "$1=ok" "$STATE_FILE" > "$STATE_FILE.tmp" || true; mv -f "$STATE_FILE.tmp" "$STATE_FILE"; }; }
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

# The installer's own command with the options as the reader gave them, for a printed instruction. A relative bundle path is made
# absolute, because the instruction may be run from another directory.
ORIG_ARGS=()
command_line() { # command_line [DEPLOY_PATH]: with a path, any --deploy-path of the reader is replaced by it
    local out="sudo infra/deploy/first-install.sh" arg previous="" skip=no
    for arg in ${ORIG_ARGS[@]+"${ORIG_ARGS[@]}"}; do
        if [ "$skip" = yes ]; then skip=no; previous="$arg"; continue; fi
        if [ -n "${1:-}" ] && [ "$arg" = --deploy-path ]; then skip=yes; previous="$arg"; continue; fi
        if [ "$previous" = --norms-bundle ] && [ -d "$arg" ]; then arg="$(cd "$arg" && pwd -P)"; fi
        out="$out $(printf '%q' "$arg")"
        previous="$arg"
    done
    if [ -n "${1:-}" ]; then out="$out --deploy-path $1"; fi
    printf '%s' "$out"
}

# A free path for a clone that cannot be used: /srv/<instance>-2, -3, ...
free_deploy_path() {
    local base="$DEPLOY_ROOT/$INSTANCE" candidate n=1
    candidate="$base"
    while [ -e "$candidate" ] || [ "$candidate" = "$REPO" ] || [ "$candidate" = "$DEPLOY_PATH" ]; do
        n=$(( n + 1 ))
        candidate="$base-$n"
    done
    printf '%s' "$candidate"
}
repo_slug() { # owner/name of a clone address in any form (https, git@, ssh://, a path), lower case, as deploy-auto reads it
    printf '%s\n' "$1" | sed -E 's#/+$##; s#\.git$##; s#^.*[:/]([^:/]+)/([^:/]+)$#\1/\2#' | tr '[:upper:]' '[:lower:]'
}

# escalate FIRST SECOND FACT...: the first time a shortage stops the run, FIRST says what to do about it and to run again; the same
# shortage again means that did not help, and SECOND is the owner's (it costs money). Cleared when the check passes.
escalate() {
    local first="$1" second="$2" key="${HINT_KEY:-$1}"
    shift 2
    if state_has "s1.hint_$key"; then stop "$second" "$@"; fi
    private_dir "$STATE_DIR"
    state_mark "s1.hint_$key"
    stop "$first" "$@"
}

# ---- the host's tools, and Docker: installed by the script where it can be done safely (Debian and Ubuntu), else one command ----
PKG_MANAGER=""
detect_package_manager() {
    local manager
    if [ "$TEST_MODE" = yes ] && [ -n "${FIRST_INSTALL_PKG_MANAGER:-}" ]; then PKG_MANAGER="$FIRST_INSTALL_PKG_MANAGER"; return 0; fi
    for manager in apt-get dnf yum zypper apk; do
        if command -v "$manager" >/dev/null 2>&1; then PKG_MANAGER="$manager"; return 0; fi
    done
    PKG_MANAGER=none
}
OS_ID="" OS_LIKE="" OS_CODENAME="" OS_UBUNTU_CODENAME=""
read_os_release() {
    [ -r "$OS_RELEASE" ] || return 0
    OS_ID="$(sed -n 's/^ID=//p' "$OS_RELEASE" | head -n 1 | tr -d '"' || true)"
    OS_LIKE="$(sed -n 's/^ID_LIKE=//p' "$OS_RELEASE" | head -n 1 | tr -d '"' || true)"
    OS_CODENAME="$(sed -n 's/^VERSION_CODENAME=//p' "$OS_RELEASE" | head -n 1 | tr -d '"' || true)"
    OS_UBUNTU_CODENAME="$(sed -n 's/^UBUNTU_CODENAME=//p' "$OS_RELEASE" | head -n 1 | tr -d '"' || true)"
}
# What download.docker.com has a repository for: debian or ubuntu (a derivative of Ubuntu names its Ubuntu base), else nothing.
docker_repo_distro() {
    read_os_release
    case "$OS_ID" in
        debian) [ -z "$OS_CODENAME" ] || { echo debian; return 0; } ;;
        ubuntu) [ -z "$OS_CODENAME" ] || { echo ubuntu; return 0; } ;;
    esac
    case " $OS_LIKE " in *" ubuntu "*) [ -z "$OS_UBUNTU_CODENAME" ] || { echo ubuntu; return 0; } ;; esac
    return 0
}
package_for() { # package_for TOOL: the package of that tool under the detected package manager
    case "$1:$PKG_MANAGER" in
        flock:*) echo util-linux ;;
        ssh-keygen:dnf|ssh-keygen:yum|ssh-keygen:zypper) echo openssh-clients ;;
        ssh-keygen:*) echo openssh-client ;;
        getent:apt-get) echo libc-bin ;;
        getent:dnf|getent:yum) echo glibc-common ;;
        getent:zypper) echo glibc ;;
        getent:apk) echo musl-utils ;;
        sha256sum:*|df:*|stat:*) echo coreutils ;;
        awk:*) echo gawk ;;
        *) echo "$1" ;;
    esac
}
install_command() { # install_command PACKAGES: the one command that installs them with the detected package manager
    case "$PKG_MANAGER" in
        apt-get) echo "apt-get update && apt-get install -y $1" ;;
        dnf) echo "dnf install -y $1" ;;
        yum) echo "yum install -y $1" ;;
        zypper) echo "zypper --non-interactive install $1" ;;
        apk) echo "apk add $1" ;;
        *) echo "install these packages with the system's package manager: $1" ;;
    esac
}
APT_UPDATED=no
apt_run() { # apt_run ARGS...: noninteractive apt-get, waiting for a lock a fresh server's own updater may hold
    if [ "$APT_UPDATED" = no ] && [ "$1" != update ]; then
        APT_UPDATED=yes
        DEBIAN_FRONTEND=noninteractive apt-get -o DPkg::Lock::Timeout=300 -q update
    fi
    DEBIAN_FRONTEND=noninteractive apt-get -o DPkg::Lock::Timeout=300 -q -y "$@"
}
tool_present() {
    if [ "$TEST_MODE" = yes ] && [[ " ${FIRST_INSTALL_FAKE_MISSING:-} " == *" $1 "* ]]; then return 1; fi
    command -v "$1" >/dev/null 2>&1
}
MISSING_TOOLS=""
find_missing_tools() {
    local tool
    MISSING_TOOLS=""
    for tool in git curl sed awk flock tar sha256sum python3 ssh-keygen getent df stat zstd; do
        tool_present "$tool" || MISSING_TOOLS="$MISSING_TOOLS $tool"
    done
    MISSING_TOOLS="${MISSING_TOOLS# }"
}
ensure_tools() {
    local tool packages="" package out
    local -a package_list
    find_missing_tools
    if [ -z "$MISSING_TOOLS" ]; then return 0; fi
    detect_package_manager
    for tool in $MISSING_TOOLS; do
        package="$(package_for "$tool")"
        case " $packages " in *" $package "*) ;; *) packages="$packages $package" ;; esac
    done
    packages="${packages# }"
    if [ "$PKG_MANAGER" = apt-get ]; then
        say "missing tools: $MISSING_TOOLS: installing $packages with apt-get"
        read -r -a package_list <<<"$packages"
        if ! out="$(apt_run install "${package_list[@]}" 2>&1)"; then printf '%s\n' "$out" | tail -n 5; fi
        find_missing_tools
        if [ -z "$MISSING_TOOLS" ]; then return 0; fi
    fi
    stop tool_missing "$(install_command "$packages")"
}
docker_manual_command() { printf '%s' "curl -fsSL https://get.docker.com -o /tmp/get-docker.sh && sh /tmp/get-docker.sh"; }

# install_docker_packages PACKAGES...: Docker's own apt repository, trusted only because the downloaded key has the pinned
# fingerprint. Chosen over the distribution's packages because those differ by release in the engine's version and in whether a
# compose v2 package exists at all (Ubuntu 24.04 has `docker-compose-v2`, measured on the development host; this installer is also
# for Debian and older Ubuntu), while Docker's repository gives the engine, buildx and compose v2 as one set on every release the
# installer supports -- the stack needs `docker compose` and its buildx. The price is trust in one key: its fingerprint is pinned
# above, was read from the live key of both distributions on 2026-11-20, and a different one stops the run (`docker_key_mismatch`).
docker_step_failed() { # docker_step_failed OUTPUT: show what the step printed, then stop
    printf '%s\n' "$1" | tail -n 8
    stop docker_install_failed "$(oneline "$(last_line "$1")" 200)"
}
install_docker_packages() {
    local distro codename key fingerprint list out
    read_os_release
    distro="$(docker_repo_distro)"
    if [ -z "$distro" ] || [ "$PKG_MANAGER" != apt-get ]; then stop docker_missing "$(docker_manual_command)"; fi
    if [ "$distro" = debian ]; then codename="$OS_CODENAME"; else codename="${OS_UBUNTU_CODENAME:-$OS_CODENAME}"; fi
    say "installing Docker from Docker's apt repository for $distro $codename"
    out="$(apt_run install ca-certificates curl gnupg 2>&1)" || docker_step_failed "$out"
    key="$(mktemp)"
    out="$(curl -fsSL --max-time 60 -o "$key" "https://download.docker.com/linux/$distro/gpg" 2>&1)" || { rm -f "$key"; docker_step_failed "$out"; }
    fingerprint="$(gpg --show-keys --with-colons "$key" 2>/dev/null | awk -F: '$1 == "fpr" { print $10; exit }' || true)"
    if [ "$fingerprint" != "$DOCKER_KEY_FPR" ]; then
        rm -f "$key"
        stop docker_key_mismatch "${fingerprint:-none}" "$DOCKER_KEY_FPR"
    fi
    install -d -m 0755 "$KEYRINGS_DIR"
    install -m 0644 "$key" "$KEYRINGS_DIR/docker.asc"
    rm -f "$key"
    list="$APT_SOURCES_DIR/docker.list"
    if [ ! -f "$list" ]; then
        printf 'deb [arch=%s signed-by=%s/docker.asc] https://download.docker.com/linux/%s %s stable\n' \
            "$(dpkg --print-architecture)" "$KEYRINGS_DIR" "$distro" "$codename" > "$list"
        chmod 644 "$list"
    fi
    APT_UPDATED=no
    out="$(apt_run install "$@" 2>&1)" || docker_step_failed "$out"
    systemctl enable --now docker >/dev/null 2>&1 || true
}
docker_major() { docker version --format '{{.Server.Version}}' 2>/dev/null | cut -d. -f1; }
compose_major() { docker compose version --short 2>/dev/null | sed 's/^v//' | cut -d. -f1; }
docker_answers() { docker info >/dev/null 2>&1; }
ensure_docker() {
    local waited=0 server compose
    detect_package_manager
    if ! tool_present docker; then
        install_docker_packages "${DOCKER_PACKAGES[@]}"
    fi
    if ! docker_answers; then
        say "Docker does not answer: starting it"
        systemctl enable --now docker >/dev/null 2>&1 || true
        while [ "$waited" -lt "$DOCKER_WAIT_SECONDS" ] && ! docker_answers; do sleep 2; waited=$(( waited + 2 )); done
        docker_answers || stop docker_down
    fi
    server="$(docker_major)"
    if ! [[ "$server" =~ ^[0-9]+$ ]] || [ "$server" -lt 20 ]; then
        if [ -n "$(docker ps -q 2>/dev/null | head -n 1)" ]; then stop docker_old "Docker Engine ${server:-of an unknown version} is installed (20 or newer is needed)."; fi
        say "Docker Engine ${server:-of an unknown version} is older than 20: upgrading it from Docker's apt repository"
        install_docker_packages "${DOCKER_PACKAGES[@]}"
        docker_answers || stop docker_down
    fi
    compose="$(compose_major)"
    if ! [[ "$compose" =~ ^[0-9]+$ ]] || [ "$compose" -lt 2 ]; then
        say "the compose v2 plugin is missing or old: installing docker-compose-plugin"
        install_docker_packages docker-compose-plugin
    fi
    server="$(docker_major)"
    compose="$(compose_major)"
    if ! [[ "$server" =~ ^[0-9]+$ ]] || [ "$server" -lt 20 ] || ! [[ "$compose" =~ ^[0-9]+$ ]] || [ "$compose" -lt 2 ]; then
        stop docker_install_failed "Docker ${server:-?} and compose ${compose:-?} after the installation (20 and 2 are needed)"
    fi
    say "docker $(docker version --format '{{.Server.Version}}' 2>/dev/null), compose $(docker compose version --short 2>/dev/null)"
}

# Stage 1 runs inside the deploy clone. Its problems are fixed by a clean clone at a free path, which the installer makes itself.
check_clone() {
    local top status files remote url
    top="$(git -C "$REPO" rev-parse --show-toplevel 2>/dev/null || true)"
    if [ -z "$top" ] || [ "$(cd "$top" && pwd -P)" != "$REPO" ]; then stop checkout_wrong "$REPO"; fi
    if ! git -C "$REPO" remote get-url origin >/dev/null 2>&1; then
        remote="$(git -C "$REPO" remote 2>/dev/null | head -n 1 || true)"
        url=""
        if [ -n "$remote" ]; then url="$(git -C "$REPO" remote get-url "$remote" 2>/dev/null || true)"; fi
        if [ -n "$url" ]; then stop no_origin "$remote" "$REPO" "$url"; fi
        stop no_origin_url "$REPO" "$REPO"
    fi
    status="$(git -C "$REPO" status --porcelain --untracked-files=all 2>/dev/null || true)"
    if [ -n "$status" ]; then
        files="$(oneline "$(printf '%s' "$status" | head -n 3 | tr '\n' ';')" 160)"
        if [ -f "$ENV_FILE" ]; then stop deploy_clone_installed "$REPO" "has local changes ($files)"; fi
        stop checkout_dirty "$REPO" "$files" "$(command_line "$(free_deploy_path)")"
    fi
    say "deploy clone $REPO at $(git -C "$REPO" rev-parse --short HEAD)"
}

# ---- the deploy clone: the clone the installer was started in is the owner's working copy and is never installed from ----
# Started anywhere but the deploy path, the installer makes the deploy clone (a clone of this clone's origin URL), puts it on the
# same commit, and runs itself again from there with the same arguments. The deploy clone is left DETACHED at that commit, which is
# exactly what every auto-deploy leaves (`git checkout --detach <sha>`, deploy-auto.yml), so the first auto-deploy finds nothing to
# change; a checked-out branch would only be switched away from. Nothing is written in the starting clone.
clone_failed_is_access() { # clone_failed_is_access OUTPUT
    case "$1" in
        *"could not read Username"*|*"Authentication failed"*|*"Permission denied"*|*"Repository not found"*|*"publickey"*) return 0 ;;
        *"terminal prompts disabled"*|*"returned error: 401"*|*"returned error: 403"*|*"The requested URL returned error: 404"*) return 0 ;;
    esac
    return 1
}
create_deploy_clone() { # create_deploy_clone URL SHA BRANCH
    local url="$1" sha="$2" branch="$3" out ref note=""
    mkdir -p "$(dirname "$DEPLOY_PATH")"
    say "making the deploy clone $DEPLOY_PATH from $url"
    if ! out="$( umask 022; GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new}" \
            git -c credential.interactive=never clone --quiet "$url" "$DEPLOY_PATH" 2>&1 )"; then
        printf '%s\n' "$out" | tail -n 5
        if clone_failed_is_access "$out"; then stop clone_needs_access "$url"; fi
        stop clone_failed "$(oneline "$(last_line "$out")" 200)"
    fi
    if git -C "$DEPLOY_PATH" cat-file -e "$sha^{commit}" 2>/dev/null; then
        ref="$sha"
    else
        # An unpublished commit cannot be deployed from anywhere but this machine; what is on origin is what auto-deploy knows.
        if [ -n "$branch" ] && git -C "$DEPLOY_PATH" rev-parse --verify -q "origin/$branch" >/dev/null; then ref="origin/$branch"; else ref="origin/HEAD"; fi
        note=" (the commit ${sha:0:8} of the starting clone is not on origin, so $ref is used)"
    fi
    git -C "$DEPLOY_PATH" -c advice.detachedHead=false checkout --quiet --detach "$ref" \
        || stop clone_failed "the commit $ref could not be checked out in $DEPLOY_PATH"
    say "the deploy clone is at $(git -C "$DEPLOY_PATH" rev-parse --short HEAD), detached$note"
}
reuse_deploy_clone() { # reuse_deploy_clone URL: an existing deploy path must be this repository, clean, with the installer in it
    local url="$1" top origin status installed=no reason="" files
    [ ! -f "$DEPLOY_PATH/infra/deploy/env/alpha.env" ] || installed=yes
    top="$(git -C "$DEPLOY_PATH" rev-parse --show-toplevel 2>/dev/null || true)"
    if [ -z "$top" ] || [ "$(cd "$top" && pwd -P)" != "$DEPLOY_REAL" ]; then
        reason="it is not empty and is not a clone of a repository"
    else
        origin="$(git -C "$DEPLOY_PATH" remote get-url origin 2>/dev/null || true)"
        status="$(git -C "$DEPLOY_PATH" status --porcelain --untracked-files=all 2>/dev/null || true)"
        if [ -z "$origin" ]; then
            reason="it has no origin"
        elif [ "$(repo_slug "$origin")" != "$(repo_slug "$url")" ]; then
            reason="its origin is $(repo_slug "$origin"), not $(repo_slug "$url")"
        elif [ -n "$status" ]; then
            files="$(oneline "$(printf '%s' "$status" | head -n 3 | tr '\n' ';')" 120)"
            reason="it has local changes ($files)"
        elif [ ! -x "$DEPLOY_PATH/infra/deploy/first-install.sh" ]; then
            reason="it has no infra/deploy/first-install.sh (an older commit)"
        fi
    fi
    if [ -n "$reason" ]; then
        if [ "$installed" = yes ]; then stop deploy_clone_installed "$DEPLOY_PATH" "$reason"; fi
        stop deploy_path_unusable "$DEPLOY_PATH" "$reason" "$(command_line "$(free_deploy_path)")"
    fi
    say "the deploy clone $DEPLOY_PATH exists, is clean and has the same origin: used as it is (at $(git -C "$DEPLOY_PATH" rev-parse --short HEAD))"
}
start_in_deploy_clone() {
    local url sha branch remote=""
    ensure_tools
    url="$(git -C "$REPO" remote get-url origin 2>/dev/null || true)"
    if [ -z "$url" ]; then
        remote="$(git -C "$REPO" remote 2>/dev/null | head -n 1 || true)"
        if [ -n "$remote" ]; then url="$(git -C "$REPO" remote get-url "$remote" 2>/dev/null || true)"; fi
        if [ -z "$url" ]; then stop no_origin_url "$REPO" "$REPO"; fi
        say "this clone has no 'origin': the address of its remote '$remote' is used"
    fi
    sha="$(git -C "$REPO" rev-parse HEAD 2>/dev/null || true)"
    [ -n "$sha" ] || stop checkout_wrong "$REPO"
    branch="$(git -C "$REPO" symbolic-ref --short -q HEAD 2>/dev/null || true)"
    if [ -e "$DEPLOY_PATH" ] && [ -n "$(ls -A "$DEPLOY_PATH" 2>/dev/null || true)" ]; then
        reuse_deploy_clone "$url"
    else
        create_deploy_clone "$url" "$sha" "$branch"
    fi
    say "this clone ($REPO) is only where the installer was started and is not touched; continuing in $DEPLOY_PATH"
}

next_free_port() { # next_free_port N: the first port after N that nothing listens on
    local port="$1" tries=0
    while [ "$tries" -lt 200 ]; do
        port=$(( port + 1 ))
        tries=$(( tries + 1 ))
        port_listening "$port" || { echo "$port"; return 0; }
    done
    echo "$port"
}
port_holder_name() { # a name for what holds a port, for the owner (ss is used when it is there; the tests have no listener to name)
    local line
    if [ "$TEST_MODE" = no ] && command -v ss >/dev/null 2>&1; then
        line="$(ss -ltnpH "sport = :$1" 2>/dev/null | head -n 1 | sed -n 's/.*users:(("\([^"]*\)".*/\1/p' || true)"
        if [ -n "$line" ]; then printf '%s' "$line"; return 0; fi
    fi
    printf 'another program'
}

stage_preflight() {
    # root
    if [ "$(id -u)" -ne 0 ] && [ "$TEST_MODE" = no ]; then stop not_root; fi
    # inputs that are only needed when a stage will use them
    if email_needed && [ -z "$OPT_EMAIL" ]; then stop email_required; fi
    ensure_tools
    python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' || { detect_package_manager; stop tool_missing "$(install_command python3)"; }
    check_clone
    ensure_docker
    # who deploys
    if [ "$OPT_DEPLOY_USER" != root ]; then
        getent passwd "$OPT_DEPLOY_USER" >/dev/null || stop deploy_user_invalid "adduser --disabled-password --gecos '' $OPT_DEPLOY_USER"
        id -nG "$OPT_DEPLOY_USER" | tr ' ' '\n' | grep -qx docker || stop deploy_user_invalid "usermod -aG docker $OPT_DEPLOY_USER"
        [ "$(stat -c %U "$REPO")" = "$OPT_DEPLOY_USER" ] || stop deploy_user_invalid "chown -R $OPT_DEPLOY_USER: $REPO"
    fi
    # disk and memory, against the runbook's figures
    local root free total available
    root="$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || true)"
    [ -d "$root" ] || root="$REPO"
    free="$(free_gib "$root")"
    if [ "$free" -lt "$MIN_FREE_GIB" ]; then escalate disk_low disk_too_small "$free" "$root" "$MIN_FREE_GIB"; fi
    state_unset s1.hint_disk_low
    available="$(mem_field_mib MemAvailable)"
    total="$(mem_field_mib MemTotal)"
    if [ "${available:-0}" -lt "$STOP_RAM_AVAILABLE_MIB" ]; then escalate ram_low ram_too_small "${available:-0}" "$STOP_RAM_AVAILABLE_MIB"; fi
    state_unset s1.hint_ram_low
    # A bundle that is downloaded from the release adds its parts to what the import needs: asked now, before the images are built.
    if [ -z "$OPT_BUNDLE" ] && [ -f "$RELEASE_LOCK" ] && ! state_has s5.designated; then
        read_release_lock
        norms_check_disk "$LOCK_TAR_BYTES" "$LOCK_TOTAL" "$MIN_FREE_GIB"
    fi
    say "disk free $free GiB on $root; memory ${available} MiB available of ${total} MiB"
    if [ "${total:-0}" -lt "$WARN_RAM_TOTAL_MIB" ]; then
        warn "this server has ${total} MiB of memory; the image build can be slow, and deploy.sh stops an overloaded build by itself (a STOP [host_overloaded] then says to wait and run again)"
    fi
    # ports
    if [ ! -f "$ENV_FILE" ] && port_listening "$HTTP_PORT"; then
        local free_port
        free_port="$(next_free_port "$HTTP_PORT")"
        if [ -n "$OPT_HTTP_PORT" ]; then stop http_port_busy "$HTTP_PORT" "$free_port"; fi
        say "port $HTTP_PORT is in use: the application will use port $free_port instead"
        HTTP_PORT="$free_port"
    fi
    if [ -n "$OPT_DOMAIN" ]; then
        local port
        for port in 80 443; do
            if port_listening "$port" && ! port_holder_is_ours "$port"; then
                stop public_port_busy "$(port_holder_name "$port")" "$port"
            fi
        done
    fi
    return 0
}

# ------------------------------------------------------------------------------------------------------------ 2 env
stack_has_data() { # an installation made from this environment exists: its database volume holds this file's passwords
    state_has s3 || docker volume inspect "$INSTANCE-postgres-data" >/dev/null 2>&1
}
env_problem_stop() { # env_problem_stop PROBLEMS: the one STOP for an environment file that does not check clean
    local text stamp command
    text="$(oneline "$(printf '%s' "$1" | tr '\n' ';')" 240)"
    if stack_has_data; then stop env_invalid_installed "$text"; fi
    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    command="mv $ENV_FILE $ENV_DIR/rejected-$stamp-alpha.env"
    if [ -f "$PROVIDER_FILE" ]; then command="$command && mv $PROVIDER_FILE $ENV_DIR/rejected-$stamp-provider.env"; fi
    stop env_invalid "$text" "$command"
}
# `--set ALPHA_NORM_EMBED=yes|no` is the one `--set` that is also applied to an environment file that already exists: it is the
# owner's switch for the semantic norm lookup, and turning it off must not need an edit by hand.
apply_norm_embed_choice() {
    local setting current rest=0
    for setting in ${OPT_SETS[@]+"${OPT_SETS[@]}"}; do
        case "$setting" in
            ALPHA_NORM_EMBED=yes|ALPHA_NORM_EMBED=no)
                current="$(env_get ALPHA_NORM_EMBED)"
                if [ "$current" != "${setting#*=}" ]; then
                    if [ "${setting#*=}" = no ]; then
                        python3 -I "$ENV_HELPER" set --env "$ENV_FILE" ALPHA_NORM_EMBED=no
                    else
                        python3 -I "$ENV_HELPER" set --env "$ENV_FILE" ALPHA_NORM_EMBED=yes ALPHA_MEM_LIMIT_NORM_EMBED=1200m
                    fi
                    say "the owner's choice $setting is applied to the existing alpha.env"
                    state_unset s10
                fi ;;
            *) rest=$(( rest + 1 )) ;;
        esac
    done
    if [ "$rest" -gt 0 ]; then warn "--set is used only for a NEW alpha.env (except ALPHA_NORM_EMBED); the existing one was not changed"; fi
}
stage_env() {
    local problems
    mkdir -p "$ENV_DIR"
    if [ ! -f "$ENV_FILE" ]; then
        local args=(create --env-dir "$ENV_DIR" --instance "$INSTANCE" --http-port "$HTTP_PORT") setting
        for setting in ${OPT_SETS[@]+"${OPT_SETS[@]}"}; do args+=(--set "$setting"); done
        if ! problems="$(python3 -I "$ENV_HELPER" "${args[@]}" 2>&1)"; then env_problem_stop "$problems"; fi
        say "$problems"
    else
        say "alpha.env already exists: kept as it is"
        apply_norm_embed_choice
    fi
    if ! problems="$(python3 -I "$ENV_HELPER" check --env "$ENV_FILE" --provider "$PROVIDER_FILE" --example "$ENV_EXAMPLE")"; then
        if printf '%s\n' "$problems" | grep -q 'must be 600'; then
            chmod 600 "$ENV_FILE"; [ ! -f "$PROVIDER_FILE" ] || chmod 600 "$PROVIDER_FILE"
            say "the environment files were readable by others: mode set to 600"
            problems="$(python3 -I "$ENV_HELPER" check --env "$ENV_FILE" --provider "$PROVIDER_FILE" --example "$ENV_EXAMPLE")" || env_problem_stop "$problems"
        else
            env_problem_stop "$problems"
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
        *"ACME client is not pinned"*) stop acme_unpinned "$REPO" "$REPO" ;;
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

importer_container_running() { docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${INSTANCE}-api-run-"; }
NORMS_EXIT="" NORMS_INTERRUPTED=no
norms_wait_for_import() { # norms_wait_for_import KEY: returns with NORMS_EXIT (the importer's status) or NORMS_INTERRUPTED=yes
    local key="$1" state waited=0
    NORMS_EXIT="" NORMS_INTERRUPTED=no
    while :; do
        norms_status
        state="$(norms_import_state "$key")"
        case "$state" in
            exited\ *) NORMS_EXIT="${state#exited }"; return 0 ;;
            running*)
                # Started, the lock is free and no importer container runs: the server restarted under it
                # (STAND-NORMS-IMPORT-RUNBOOK-01 section 8). `import` is re-entrant, so the stage simply starts it again.
                if printf '%s\n' "$NORMS_STATUS_OUT" | grep -q '^import_lock: free$' && [ "$waited" -ge $(( POLL_SECONDS * 2 )) ] \
                    && ! importer_container_running; then
                    NORMS_INTERRUPTED=yes
                    return 0
                fi ;;
            *) NORMS_INTERRUPTED=yes; return 0 ;;
        esac
        if [ $(( waited % 300 )) -eq 0 ]; then
            say "importing $key ($(( waited / 60 )) min so far): $(printf '%s\n' "$NORMS_STATUS_OUT" | awk -v k="$key" '$1 == "bundle:" && $2 == k { f = 1; next } f && /^  \|/ { l = $0 } END { print l }' | cut -c1-160)"
        fi
        sleep "$POLL_SECONDS"
        waited=$(( waited + POLL_SECONDS ))
    done
}

norms_refusal() { # norms_refusal OUTPUT: a lock held by another step is a wait; anything else is for the owner to see
    local line
    line="$(oneline "$(last_line "$1")" 300)"
    case "$1" in *lock-free*) stop norms_wait "$line" ;; esac
    stop norms_refused "$line"
}

norms_start_import() { # norms_start_import KEY: the test-data waiver (a new one when the open one has too little window left), then the importer
    local key="$1" out
    norms_record
    if [ "$NORMS_REC_STATE" = open ] && [ "$NORMS_REC_KIND" = test_data_waiver ] && [ "$NORMS_REC_AGE" -gt $(( NORMS_REC_WINDOW - 7200 )) ]; then
        say "the open waiver $NORMS_REC_STAMP has too little of its window left: closing it and opening a new one"
        out="$(copy resume "$NORMS_REC_STAMP" 2>&1)" || norms_refusal "$out"
        norms_record
    fi
    case "$NORMS_REC_STATE:$NORMS_REC_KIND" in
        none:*|closed:*)
            out="$(copy attest --test-data 2>&1)" || norms_refusal "$out"
            printf '%s\n' "$out"
            norms_record ;;
        open:test_data_waiver) say "the open waiver $NORMS_REC_STAMP is used" ;;
        *) stop norms_busy "record $NORMS_REC_STAMP, kind $NORMS_REC_KIND" ;;
    esac
    out="$(inbound import "$key" 2>&1)" || norms_refusal "$out"
    printf '%s\n' "$out"
}

# ---- where the bundle comes from: --norms-bundle DIRECTORY (it wins), else the release the repository's lock file names ----
norms_wanted() { [ -n "$OPT_BUNDLE" ] || [ -f "$RELEASE_LOCK" ]; }
existing_dir() { # the nearest directory of PATH that exists (the staging directory may not be made yet, in the preflight)
    local dir="$1"
    while [ ! -d "$dir" ] && [ "$dir" != / ]; do dir="$(dirname "$dir")"; done
    printf '%s' "$dir"
}
# norms_check_disk TAR_BYTES DOWNLOAD_BYTES BASE_GIB: STAND-NORMS-IMPORT-RUNBOOK-01.md section 0 item 4. Staging holds the tar and
# its extraction (2 x size + 2 GiB) and, from a release, the downloaded parts; Docker's volumes grow by the objects (size),
# PostgreSQL with its WAL (2.5 GB) and 2 GiB, each +25 %, and BASE_GIB more where the images are not built yet.
norms_check_disk() {
    local size="$1" download="$2" base="${3:-0}" gib=1073741824 staging_free docker_root docker_free need_staging need_docker staging_dir
    need_staging=$(( (2 * size + 2 * gib + download) / gib + 1 ))
    need_docker=$(( ((size + 5 * gib / 2 + 2 * gib) * 5 / 4) / gib + 1 + base ))
    staging_dir="$(existing_dir "$NORMS_STAGING")"
    staging_free="$(free_gib "$staging_dir")"
    docker_root="$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || true)"
    [ -d "$docker_root" ] || docker_root="$REPO"
    docker_free="$(free_gib "$docker_root")"
    if [ "$(stat -c %d "$staging_dir")" = "$(stat -c %d "$docker_root")" ]; then
        if [ "$staging_free" -lt $(( need_staging + need_docker )) ]; then
            escalate norms_disk_low norms_disk_too_small "$staging_free" "$NORMS_STAGING" $(( need_staging + need_docker ))
        fi
    else
        if [ "$staging_free" -lt "$need_staging" ]; then escalate norms_disk_low norms_disk_too_small "$staging_free" "$NORMS_STAGING" "$need_staging"; fi
        if [ "$docker_free" -lt "$need_docker" ]; then escalate norms_disk_low norms_disk_too_small "$docker_free" "$docker_root" "$need_docker"; fi
    fi
    state_unset s1.hint_norms_disk_low
}

# The lock file (`infra/norms/bundle-release.lock`, written by infra/norms/publish-bundle-release.sh): read as data, never sourced.
LOCK_REPO="" LOCK_TAG="" LOCK_BUNDLE="" LOCK_DIGEST="" LOCK_TAR_BYTES="" LOCK_TOTAL=""
LOCK_NAMES=() LOCK_SIZES=() LOCK_SHAS=() LOCK_IDS=()
lock_value() { sed -n "s/^$1=//p" "$RELEASE_LOCK" | tail -n 1; }
read_release_lock() {
    local line name size sha id sum=0 count
    [ -r "$RELEASE_LOCK" ] || stop norms_lock_invalid "it cannot be read"
    # shellcheck source=infra/deploy/lib/forced-command.sh
    . "$DEPLOY_DIR/lib/forced-command.sh"
    [ "$(lock_value lock_version)" = 1 ] || stop norms_lock_invalid "its lock_version is not 1"
    LOCK_REPO="$(lock_value repo)"; LOCK_TAG="$(lock_value tag)"; LOCK_BUNDLE="$(lock_value bundle)"
    LOCK_DIGEST="$(lock_value bundle_sums_sha256)"; LOCK_TAR_BYTES="$(lock_value tar_bytes)"; LOCK_TOTAL="$(lock_value total_bytes)"
    [[ "$LOCK_REPO" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || stop norms_lock_invalid "repo is not owner/name"
    [[ "$LOCK_TAG" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$ ]] || stop norms_lock_invalid "tag is not a release tag"
    [[ "$LOCK_BUNDLE" =~ ^${FC_BUNDLE_KEY_ERE}$ ]] || stop norms_lock_invalid "bundle is not a bundle directory name"
    if ! [[ "$LOCK_DIGEST" =~ ^[0-9a-f]{64}$ ]] || [ "$LOCK_DIGEST" != "${LOCK_BUNDLE##*+}" ]; then
        stop norms_lock_invalid "bundle_sums_sha256 is not the digest the bundle's name ends with"
    fi
    [[ "$LOCK_TAR_BYTES" =~ ^[1-9][0-9]{0,11}$ ]] || stop norms_lock_invalid "tar_bytes is not a byte count"
    LOCK_NAMES=() LOCK_SIZES=() LOCK_SHAS=() LOCK_IDS=()
    while IFS= read -r line; do
        read -r name size sha id <<<"$line"
        if ! [[ "$name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || ! [[ "$size" =~ ^[1-9][0-9]{0,11}$ ]] \
            || ! [[ "$sha" =~ ^[0-9a-f]{64}$ ]] || ! [[ "$id" =~ ^[0-9]{1,20}$ ]]; then
            stop norms_lock_invalid "a part= line is not <name> <size> <sha256> <asset id>"
        fi
        LOCK_NAMES+=("$name"); LOCK_SIZES+=("$size"); LOCK_SHAS+=("$sha"); LOCK_IDS+=("$id")
        sum=$(( sum + size ))
    done < <(sed -n 's/^part=//p' "$RELEASE_LOCK")
    count="${#LOCK_NAMES[@]}"
    if [ "$count" -lt 1 ] || [ "$(lock_value part_count)" != "$count" ]; then stop norms_lock_invalid "part_count is not the number of part= lines"; fi
    [ "$LOCK_TOTAL" = "$sum" ] || stop norms_lock_invalid "total_bytes is not the sum of the parts"
}

release_dir() { printf '%s/download/%s' "$NORMS_STAGING" "$LOCK_TAG"; }
release_url() { # release_url INDEX: public download URL; with a read token (a private repository) the API's asset endpoint
    if [ -n "${FIRST_INSTALL_NORMS_READ_TOKEN_FILE:-}" ]; then
        printf '%s/repos/%s/releases/assets/%s' "$RELEASE_API_BASE" "$LOCK_REPO" "${LOCK_IDS[$1]}"
    else
        printf '%s/%s/releases/download/%s/%s' "$RELEASE_BASE" "$LOCK_REPO" "$LOCK_TAG" "${LOCK_NAMES[$1]}"
    fi
}
file_size() { stat -c %s "$1" 2>/dev/null || echo 0; }
file_sha() { sha256sum "$1" | cut -c1-64; }

# One part: present, complete and the right sha256 -- or downloaded (resuming a partial file with curl -C -) until it is. The token,
# when there is one, goes to curl through a header FILE, never an argument.
RELEASE_CURL=()
release_curl_setup() {
    RELEASE_CURL=(--silent --show-error --location --connect-timeout 30 --speed-limit 10000 --speed-time 120)
    RELEASE_HEADER=""
    if [ -n "${FIRST_INSTALL_NORMS_READ_TOKEN_FILE:-}" ]; then
        [ -r "$FIRST_INSTALL_NORMS_READ_TOKEN_FILE" ] || stop norms_download_failed "the read token file named by FIRST_INSTALL_NORMS_READ_TOKEN_FILE cannot be read"
        RELEASE_HEADER="$(mktemp)"
        printf 'Authorization: Bearer %s\nAccept: application/octet-stream\n' "$(tr -d '[:space:]' < "$FIRST_INSTALL_NORMS_READ_TOKEN_FILE")" > "$RELEASE_HEADER"
        RELEASE_CURL+=(-H "@$RELEASE_HEADER")
    fi
}
release_curl_done() { [ -z "$RELEASE_HEADER" ] || rm -f "$RELEASE_HEADER"; RELEASE_HEADER=""; }
download_part() { # download_part INDEX
    local index="$1" file name size sha url code status attempt got try
    name="${LOCK_NAMES[$index]}"; size="${LOCK_SIZES[$index]}"; sha="${LOCK_SHAS[$index]}"
    file="$(release_dir)/$name"
    url="$(release_url "$index")"
    for attempt in 1 2; do
        got="$(file_size "$file")"
        if [ "$got" -gt "$size" ]; then rm -f "$file"; got=0; fi
        if [ "$got" -lt "$size" ]; then
            # Is the asset there at all? A one-byte range answers 206 (or 200) for an asset, 404 for a missing one.
            code="$(curl "${RELEASE_CURL[@]}" --max-time 60 -r 0-0 -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || true)"
            case "$code" in
                200|206) ;;
                404) release_curl_done; stop norms_release_missing "$LOCK_TAG" "$LOCK_REPO" "$name" ;;
                *) release_curl_done; stop norms_download_failed "the answer for $name was ${code:-none}" ;;
            esac
            say "downloading part $((index + 1)) of ${#LOCK_NAMES[@]}, $name ($(( (size - got) / 1048576 )) MiB to go)"
            # Each try resumes at what the file already holds (curl's own --retry would start the transfer again from the first byte).
            for try in $(seq 1 "$RELEASE_RETRIES"); do
                status=0
                curl "${RELEASE_CURL[@]}" --fail --continue-at - -o "$file" "$url" || status=$?
                [ "$status" -ne 0 ] || break
                [ "$try" -ge "$RELEASE_RETRIES" ] || sleep "$RELEASE_RETRY_DELAY"
            done
            if [ "$status" -ne 0 ]; then release_curl_done; stop norms_download_failed "curl ended with status $status for $name"; fi
            got="$(file_size "$file")"
            if [ "$got" -ne "$size" ]; then
                if [ "$got" -gt "$size" ]; then rm -f "$file"; continue; fi
                release_curl_done; stop norms_download_failed "$name has $got of $size bytes"
            fi
        fi
        if [ "$(file_sha "$file")" = "$sha" ]; then return 0; fi
        say "part $name does not have the sha256 of the lock: downloading it again"
        got="$(file_sha "$file")"
        rm -f "$file"
    done
    release_curl_done
    stop norms_download_corrupt "$name" "${got:-unknown}" "$sha"
}

norms_receive_directory() { # norms_receive_directory BUNDLE KEY: verified here (push-bundle.sh --dry-run), then streamed into `receive`
    local bundle="$1" key="$2" parent size out status
    parent="${bundle%/*}"
    norms_status
    if [ "$(norms_import_state "$key")" = absent ]; then
        out="$("$DEPLOY_DIR/push-bundle.sh" --dry-run "$bundle" 2>&1)" \
            || stop norms_bundle_invalid "$bundle" "$(oneline "$(last_line "$out")" 200)"
        size="$(printf '%s\n' "$out" | sed -n 's/.*would send \([0-9][0-9]*\) bytes as.*/\1/p' | tail -n 1)"
        [[ "$size" =~ ^[0-9]+$ ]] || stop norms_bundle_invalid "$bundle" "its size could not be read"
        norms_check_disk "$size" 0 0
        say "sending $key ($size bytes) into the on-host receive; this takes minutes"
        status=0
        out="$(mktemp)"
        bundle_tar "$parent" "$key" | inbound receive "$key" "$size" 2>&1 | tee "$out" || status="${PIPESTATUS[1]}"
        if [ "$status" -ne 0 ]; then
            local refusal
            refusal="$(cat "$out")"
            rm -f "$out"
            norms_refusal "$refusal"
        fi
        rm -f "$out"
    else
        say "the bundle $key is already received"
    fi
}

# From the release: the parts are downloaded and checked, and then `cat parts | zstd -dc` is the tar that `receive <KEY> <bytes>`
# takes on its standard input -- the very stream the directory path sends. Nothing is extracted a second time: `receive` writes the
# tar into staging, checks the members, extracts, and re-hashes every file against SHA256SUMS, whose digest is the directory name's.
norms_receive_release() {
    local key="$LOCK_BUNDLE" dir index have remaining=0 out refusal sums
    local -a files=() codes=()
    norms_status
    if [ "$(norms_import_state "$key")" != absent ]; then say "the bundle $key is already received"; return 0; fi
    dir="$(release_dir)"
    mkdir -p "$dir"
    for index in "${!LOCK_NAMES[@]}"; do
        have="$(file_size "$dir/${LOCK_NAMES[$index]}")"
        [ "$have" -ge "${LOCK_SIZES[$index]}" ] || remaining=$(( remaining + LOCK_SIZES[index] - have ))
    done
    norms_check_disk "$LOCK_TAR_BYTES" "$remaining" 0
    release_curl_setup
    for index in "${!LOCK_NAMES[@]}"; do download_part "$index"; files+=("$dir/${LOCK_NAMES[$index]}"); done
    release_curl_done
    say "the ${#files[@]} parts of $LOCK_TAG are downloaded and match the lock; streaming them into the on-host receive ($LOCK_TAR_BYTES bytes); this takes minutes"
    out="$(mktemp)"
    cat "${files[@]}" | zstd -dc | inbound receive "$key" "$LOCK_TAR_BYTES" 2>&1 | tee "$out" || codes=("${PIPESTATUS[@]}")
    refusal="$(cat "$out")"
    rm -f "$out"
    if [ "${codes[1]:-0}" -ne 0 ]; then stop norms_refused "the downloaded archive does not decompress (zstd status ${codes[1]}); the parts match the lock, so the published archive is damaged"; fi
    if [ "${#codes[@]}" -gt 0 ]; then norms_refusal "$refusal"; fi
    sums="$(file_sha "$NORMS_STAGING/bundles/$key/SHA256SUMS")"
    if [ "$sums" != "$LOCK_DIGEST" ] || [ "$sums" != "${key##*+}" ]; then
        stop norms_refused "the received bundle's SHA256SUMS has the digest $sums, not the lock's or the name's"
    fi
    say "received $key: the digest of its SHA256SUMS is the lock's and the directory name's"
}
norms_remove_parts() { # after the import succeeded: the downloaded parts, and only those the lock names
    local index part_file
    [ -z "$OPT_BUNDLE" ] && [ -n "$LOCK_TAG" ] || return 0
    for index in "${!LOCK_NAMES[@]}"; do
        part_file="$(release_dir)/${LOCK_NAMES[$index]}"
        if [ -f "$part_file" ]; then rm -f "$part_file"; fi
    done
    rmdir "$(release_dir)" 2>/dev/null || true
}

stage_norms() {
    local key bundle out status stamp
    if state_has s5.designated; then say "the norms snapshot was designated by an earlier run"; return 0; fi
    if [ -n "$OPT_BUNDLE" ]; then
        bundle="$(cd "$OPT_BUNDLE" && pwd -P)"
        key="${bundle##*/}"
        say "norms: the bundle directory $bundle (--norms-bundle)"
    else
        read_release_lock
        key="$LOCK_BUNDLE"
        say "norms: the release $LOCK_TAG of $LOCK_REPO, as infra/norms/bundle-release.lock names it"
    fi
    norms_ensure_dirs
    local available
    available="$(mem_field_mib MemAvailable)"
    if [ "${available:-0}" -lt "$NORMS_RAM_AVAILABLE_MIB" ]; then
        HINT_KEY=norms_ram escalate ram_low ram_too_small "${available:-0}" "$NORMS_RAM_AVAILABLE_MIB"
    fi
    state_unset s1.hint_norms_ram

    # An open record that is not a test-data waiver is somebody's copy or import. `receive` would turn it into an import record
    # (its design: `W54-PLAN.md` section 3.5), so the stage looks first and touches nothing of another kind.
    norms_record
    if [ "$NORMS_REC_STATE" = open ] && [ "$NORMS_REC_KIND" != test_data_waiver ]; then
        stop norms_busy "record $NORMS_REC_STAMP, kind $NORMS_REC_KIND"
    fi

    # 1. the bundle into staging
    if [ -n "$OPT_BUNDLE" ]; then norms_receive_directory "$bundle" "$key"; else norms_receive_release; fi

    # 2. the waiver and the importer, started again (it is re-entrant) when it ended unfinished or was interrupted
    local import_state attempt=0 restart=no
    while :; do
        attempt=$(( attempt + 1 ))
        norms_status
        import_state="$(norms_import_state "$key")"
        if [ "$restart" = yes ] || [ "$import_state" = "not imported" ] || [ "$import_state" = "exited 75" ]; then
            norms_start_import "$key"
        elif [ "$import_state" = absent ]; then
            stop norms_refused "the bundle $key is not in the staging directory after the receive"
        fi
        restart=no
        norms_wait_for_import "$key"
        if [ "$NORMS_INTERRUPTED" = yes ] || [ "$NORMS_EXIT" = 75 ]; then
            if [ "$attempt" -ge 3 ]; then stop norms_import_unfinished; fi
            say "the importer did not finish (interrupted, or status 75): importing again, which is safe"
            restart=yes
            continue
        fi
        break
    done
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
        out="$(copy resume "$stamp" 2>&1)" || norms_refusal "$out"
        printf '%s\n' "$out"
    fi
    "$DEPLOY_DIR/reload-proxy.sh" --env-file "$ENV_FILE" || warn "reload-proxy.sh ended with a non-zero status; verify-deployed.sh decides"

    # 4. the snapshot becomes the current one
    local content_key="${key%+*}"
    status=0
    out="$(python3 -I "$API_HELPER" designate --base "$ALPHA_BASE" --password-file "$(password_file)" --content-key "$content_key" 2>&1)" || status=$?
    printf '%s\n' "$out"
    [ "$status" -eq 0 ] || stop norms_designate_failed "$(oneline "$(last_line "$out")" 300)"
    norms_remove_parts
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
    if [ -z "$pin" ] || [ "$pin" = UNRESOLVED ]; then stop acme_unpinned "$REPO" "$REPO"; fi

    local verify=("$DEPLOY_DIR/verify-deployed.sh" --env-file "$ENV_FILE")
    if ! state_has s6.staging; then
        python3 -I "$ENV_HELPER" set --env "$ENV_FILE" "ALPHA_CERT_NAME=$OPT_DOMAIN" "ALPHA_ACME_EMAIL=$OPT_EMAIL" ALPHA_ACME_STAGING=yes
        run_deploy https-staging
        if [ "$DEPLOY_STATUS" -ne 0 ]; then stop_for_deploy; fi
        wait_for_certificate "${verify[@]}" --acme-rehearsal || stop acme_staging_failed "$OPT_DOMAIN" "$CERT_WAIT_SECONDS" "$(acme_reason)"
        state_mark s6.staging
    fi
    if ! state_has s6.real; then
        python3 -I "$ENV_HELPER" set --env "$ENV_FILE" ALPHA_ACME_STAGING=no
        run_deploy https-real
        if [ "$DEPLOY_STATUS" -ne 0 ]; then stop_for_deploy; fi
        wait_for_certificate "${verify[@]}" || stop acme_real_failed "$CERT_WAIT_SECONDS" "$(acme_reason)"
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

acme_reason() { # what the authority said, from the ACME service's own log (it holds no secret)
    local words
    words="$(docker compose --env-file "$ENV_FILE" --file "$COMPOSE_FILE" --file "$ACME_OVERLAY" logs --no-color --tail 80 acme 2>&1 \
        | grep -iE 'rate limit|too many|unauthorized|timeout|connection|refused|dns|problem|error|fail' | tail -n 2 | tr '\n' ' ' || true)"
    printf '%s' "$(oneline "${words:-the log of the acme service names no reason}" 220)"
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
    if [ "$status" -ne 0 ]; then
        # DEPLOYMENT_RUNBOOK.md section 4: a proxy that holds a replaced container's address answers 502, and reload-proxy.sh is the repair.
        say "verify-deployed.sh ended with status $status: reloading the proxy once, as the runbook says, and asking again"
        "$DEPLOY_DIR/reload-proxy.sh" --env-file "$ENV_FILE" </dev/null || true
        status=0
        "$DEPLOY_DIR/verify-deployed.sh" --env-file "$ENV_FILE" </dev/null || status=$?
    fi
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
    printf '  variable DEPLOY_HOST=%s\n' "$GITHUB_HOST"
    printf '  variable DEPLOY_PATH=%s   (the installer made this checkout and works in it; the clone it was started in is not used)\n' "$REPO"
    if [ -r "$HOST_KEY_PUB" ]; then
        key_line="$(awk -v h="$GITHUB_HOST" '{ print h " " $1 " " $2; exit }' "$HOST_KEY_PUB")"
        fingerprint="$(ssh-keygen -lf "$HOST_KEY_PUB" 2>/dev/null | awk '{ print $2 }' || true)"
        printf '  variable DEPLOY_KNOWN_HOSTS=%s\n' "$key_line"
        printf '    the key fingerprint is %s ; compare it with: ssh-keyscan -t ed25519 %s | ssh-keygen -lf -\n' "${fingerprint:-unknown}" "$GITHUB_HOST"
    else
        warn "$HOST_KEY_PUB does not exist: take the host key line for DEPLOY_KNOWN_HOSTS from another key type of this server (ssh-keygen -lf /etc/ssh/ssh_host_*_key.pub)"
    fi
    printf '  secret   VPS_USER=%s\n' "$OPT_DEPLOY_USER"
    CI_KEY_FILE="$SECRET_DIR/$INSTANCE-deploy-key"
    if [ "$OPT_NO_CI_KEY" = yes ]; then
        printf '  secret   VPS_SSH_KEY=the private key of an account that may log in as %s (no key was generated: --no-ci-key)\n' "$OPT_DEPLOY_USER"
    else
        ensure_ci_key
        printf '  secret   VPS_SSH_KEY=the whole content of the file %s (root-only; the owner copies it and then deletes the file)\n' "$CI_KEY_FILE"
    fi
    if [ "$OPT_DEPLOY_USER" != root ]; then
        printf '  sudoers  (visudo -f /etc/sudoers.d/%s-local-agent)   %s ALL=(root) NOPASSWD: %s/infra/deploy/local-agent.sh\n' \
            "$INSTANCE" "$OPT_DEPLOY_USER" "$REPO"
    fi
    printf '  the server deploys only the repository it was cloned from: %s\n' "$repo_name"
    if [ "$(env_get ALPHA_NORM_EMBED)" = yes ] && ! state_has s5.designated; then
        printf '  note     the norms are not imported and the semantic norm lookup is not on yet: this repository publishes no norms bundle (no infra/norms/bundle-release.lock). It turns on by itself when the installer is run again with --norms-bundle DIRECTORY, or without it once the repository carries the lock file (sudo infra/deploy/first-install.sh)\n'
    fi
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

# -------------------------------------------------------------------------------------------------------- 10 semantic
# The semantic norm lookup (`NORM-VECTOR-TEMP-01`, docs/program/NORM-VECTOR-TEMP-01.md, owner 2026-11-20: always on). The embedder
# is built and started by deploy.sh (`ALPHA_NORM_EMBED=yes`, the address EMPTY: rollout step 2). Once a norms snapshot is current
# the two gates of rollout steps 3 and 4 are run exactly as the document gives them; only when both pass is the worker pointed at the
# embedder (step 5). A failed gate leaves the address EMPTY, which is the document's rollback state: the stack works on word search.
# The stage is last but one on purpose: a gate that fails stops the run only after everything else is installed.
SEM_REASON=""
semantic_compose() { # docker compose with the profile deploy.sh puts in every compose command when ALPHA_NORM_EMBED=yes
    local profiles="${COMPOSE_PROFILES:+$COMPOSE_PROFILES,}norm-embed"
    COMPOSE_PROFILES="$profiles" docker compose --env-file "$ENV_FILE" --file "$COMPOSE_FILE" "$@"
}
swap_used_mib() {
    local total free
    total="$(awk '$1 == "SwapTotal:" { print $2; exit }' "$MEMINFO")"
    free="$(awk '$1 == "SwapFree:" { print $2; exit }' "$MEMINFO")"
    echo $(( (${total:-0} - ${free:-0}) / 1024 ))
}
set_embed_url() { python3 -I "$ENV_HELPER" set --env "$ENV_FILE" "AUDITMANAGER_NORM_EMBED_URL=$1" >/dev/null; }
restart_worker() { # `docker compose ... up -d worker` (step 5), then wait until the worker runs; 0 when it does
    local out id waited=0
    out="$(semantic_compose up -d --no-deps worker 2>&1)" || { SEM_REASON="$(oneline "$(last_line "$out")" 200)"; return 1; }
    while [ "$waited" -lt 60 ]; do
        id="$(semantic_compose ps --quiet worker 2>/dev/null | head -n 1 || true)"
        if [ -n "$id" ] && [ "$(docker inspect --format '{{.State.Status}}' "$id" 2>/dev/null || true)" = running ]; then return 0; fi
        sleep 2
        waited=$(( waited + 2 ))
    done
    SEM_REASON="the worker is not running 60 seconds after up -d worker"
    return 1
}
keep_semantic_off() { # the rollback state: the address empty and the worker restarted on it, when it had been set
    local url
    url="$(env_get AUDITMANAGER_NORM_EMBED_URL)"
    if [ -n "$url" ]; then
        set_embed_url ""
        restart_worker || warn "the worker could not be restarted after the address was taken out: $SEM_REASON"
    fi
}
# parse the one JSON line semantic_check prints: "VERDICT MEAN RECALL WINDOWS", or nothing
semantic_json() {
    printf '%s\n' "$1" | python3 -I -c '
import json, sys
for line in reversed(sys.stdin.read().splitlines()):
    line = line.strip()
    if line.startswith("{"):
        try:
            data = json.loads(line)
        except ValueError:
            continue
        print(data.get("verdict", ""), data.get("mean_inner_product", ""), data.get("self_recall_at_10", ""), data.get("windows", ""))
        break
'
}
# Returns 0 both gates pass, 10 the memory gate failed, 11 the quality gate failed, 12 the quality gate could not run.
semantic_gates() {
    local available swap_before swap_after samples sampler minimum out status=0 parsed verdict mean recall windows stats
    available="$(mem_field_mib MemAvailable)"
    swap_before="$(swap_used_mib)"
    stats="$(docker stats --no-stream --format '{{.Name}} {{.MemUsage}}' 2>/dev/null | tr '\n' ';' | cut -c1-240 || true)"
    say "memory gate, at rest: ${available} MiB available, swap in use ${swap_before} MiB; ${stats:-no container figures}"
    if [ "${available:-0}" -le "$SEMANTIC_MIN_AVAILABLE_MIB" ]; then
        SEM_REASON="only ${available:-0} MiB of memory are available at rest (it must stay above $SEMANTIC_MIN_AVAILABLE_MIB MiB)"
        return 10
    fi
    say "quality gate: semantic_check on $SEMANTIC_WINDOWS windows of the current snapshot (about five minutes); memory is watched meanwhile"
    samples="$(mktemp)"
    ( while :; do mem_field_mib MemAvailable >> "$samples"; sleep "$SAMPLE_SECONDS"; done ) &
    sampler=$!
    out="$(semantic_compose exec -T worker python -m auditmanager.norms.semantic_check --url "$SEMANTIC_URL" --windows "$SEMANTIC_WINDOWS" 2>&1)" || status=$?
    kill "$sampler" 2>/dev/null || true
    wait "$sampler" 2>/dev/null || true
    minimum="$(sort -n "$samples" | head -n 1 || true)"
    rm -f "$samples"
    swap_after="$(swap_used_mib)"
    printf '%s\n' "$out" | tail -n 3 | cut -c1-300
    say "memory gate, under load: at least ${minimum:-$available} MiB were available, swap in use ${swap_after} MiB (it was ${swap_before} MiB)"
    if [ "${minimum:-$available}" -le "$SEMANTIC_MIN_AVAILABLE_MIB" ]; then
        SEM_REASON="available memory fell to ${minimum} MiB while the embedder worked (it must stay above $SEMANTIC_MIN_AVAILABLE_MIB MiB)"
        return 10
    fi
    if [ "$swap_after" -gt "$swap_before" ]; then
        SEM_REASON="swap grew from ${swap_before} MiB to ${swap_after} MiB while the embedder worked (it must not grow)"
        return 10
    fi
    parsed="$(semantic_json "$out")"
    if [ -z "$parsed" ]; then
        SEM_REASON="$(oneline "$(last_line "$out")" 200) (status $status)"
        return 12
    fi
    read -r verdict mean recall windows <<<"$parsed"
    if [ "$verdict" != PASS ] || [ "$status" -ne 0 ]; then
        SEM_REASON="mean inner product $mean (it must be 0.97 or more) and self-recall@10 $recall (0.90 or more) on $windows windows"
        return 11
    fi
    say "quality gate: PASS (mean inner product $mean, self-recall@10 $recall, $windows windows)"
    return 0
}
stage_semantic() {
    local embed url status=0
    embed="$(env_get ALPHA_NORM_EMBED)"
    url="$(env_get AUDITMANAGER_NORM_EMBED_URL)"
    if [ "${embed:-no}" != yes ]; then
        # The owner's choice (--set ALPHA_NORM_EMBED=no): the document's rollback, step 5 of "Rollback".
        say "semantic norm lookup is off: ALPHA_NORM_EMBED is ${embed:-no} in alpha.env (the owner's choice); the stack works on word search"
        keep_semantic_off
        if [ -n "$(semantic_compose ps --quiet norm-embed 2>/dev/null | head -n 1 || true)" ]; then
            semantic_compose rm -sf norm-embed >/dev/null 2>&1 || warn "the norm-embed service could not be removed"
        fi
        return 0
    fi
    if ! state_has s5.designated; then
        STAGE_DONE=no
        say "semantic norm lookup stays off for now: there is no norms snapshot, so the gates cannot run. The stack works on word search."
        say "it turns on by itself when the installer is run again with --norms-bundle DIRECTORY, or without it once the repository carries infra/norms/bundle-release.lock"
        return 0
    fi
    semantic_gates || status=$?
    case "$status" in
        0) ;;
        10) keep_semantic_off; stop semantic_memory_low "$SEM_REASON" ;;
        11) keep_semantic_off; stop semantic_quality_failed "$SEM_REASON" "$(command_line) --set ALPHA_NORM_EMBED=no" ;;
        *) keep_semantic_off; stop semantic_check_failed "$SEM_REASON" ;;
    esac
    set_embed_url "$SEMANTIC_URL"
    if ! restart_worker; then
        set_embed_url ""
        restart_worker || true
        stop semantic_worker_failed "$SEM_REASON"
    fi
    say "both gates passed: AUDITMANAGER_NORM_EMBED_URL is $SEMANTIC_URL and the worker was restarted; semantic norm lookup is on"
}
semantic_summary() { # one phrase for the DONE line, from the environment as it is now
    if [ -n "$(env_get AUDITMANAGER_NORM_EMBED_URL)" ]; then printf 'on'
    elif [ "$(env_get ALPHA_NORM_EMBED)" != yes ]; then printf "off (the owner's choice)"
    else printf 'off until the installer is run again with the norms bundle (word search works)'
    fi
}

# ------------------------------------------------------------------------------------------------------- 11 marker
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
        printf 'stage_5_norms=%s\n' "$(state_has s5.designated && echo ok || echo skipped)"
        printf 'stage_6_https=%s\n' "$([ -n "$OPT_DOMAIN" ] && echo ok || echo skipped)"
        printf 'stage_7_executors=%s\n' "$([ "$OPT_SKIP_EXECUTORS" = yes ] && echo skipped || echo ok)"
        printf 'stage_8_verify=ok\nstage_9_github=printed\n'
        printf 'stage_10_semantic=%s\n' "$(semantic_summary)"
    } > "$MARKER.tmp"
    mv -f "$MARKER.tmp" "$MARKER"
    say "marker written: $MARKER"
}

admin_login() { # the login line of the password file, which is not a secret (the password is on the next line)
    sed -n 's/^login=//p' "$(password_file)" 2>/dev/null | head -n 1 || true
}

# ----------------------------------------------------------------------------------------------------------- runner
STAGE_TITLES=(
    "preflight: root, tools, Docker, the deploy clone, disk, memory, ports"
    "env: alpha.env and provider.env from the examples, every secret generated (mode 600)"
    "deploy: the first deploy.sh, without published HTTPS"
    "admin: the administrator's password and profile through the loopback API; deploy.sh again"
    "norms: get the norms bundle (a directory, or the release the repository names), import it, make it the current snapshot"
    "https: DNS, test certificate, real certificate, public port 443"
    "executors: connect this server's own claude / codex subscriptions"
    "verify: verify-deployed.sh must exit 0"
    "github: what to paste into GitHub, and the deploy key"
    "semantic: the memory and quality gates, then the embedder address for the worker"
    "marker: write the done marker; a second run refuses"
)

STAGE_DONE=yes
run_stage() { # run_stage N FUNCTION
    local n="$1" fn="$2"
    stage_header "$n" "${STAGE_TITLES[$((n - 1))]}"
    # Stages 1 and 2 are cheap and always run: the server and the environment file may have changed since the last run. Stage 9
    # (the values for GitHub) and 11 (the marker) are printed or written again each time.
    if [ "$n" -gt 2 ] && [ "$n" -ne 9 ] && [ "$n" -ne 11 ] && state_has "s$n"; then
        say "done before: skipped"
        return 0
    fi
    STAGE_DONE=yes
    "$fn"
    if [ "$n" -ne 9 ] && [ "$n" -ne 11 ] && [ "$STAGE_DONE" = yes ]; then state_mark "s$n"; fi
    return 0
}

run_all() {
    run_stage 1 stage_preflight
    run_stage 2 stage_env
    run_stage 3 stage_deploy
    run_stage 4 stage_admin
    if norms_wanted; then run_stage 5 stage_norms; else stage_header 5 "${STAGE_TITLES[4]}"; say "skipped: no --norms-bundle, and the repository publishes none (no infra/norms/bundle-release.lock)"; fi
    if [ -n "$OPT_DOMAIN" ]; then run_stage 6 stage_https; else stage_header 6 "${STAGE_TITLES[5]}"; say "skipped: no --domain (the stack answers on 127.0.0.1:$HTTP_PORT; reach it with: ssh -L $HTTP_PORT:127.0.0.1:$HTTP_PORT <this server>)"; fi
    if [ "$OPT_SKIP_EXECUTORS" = no ]; then run_stage 7 stage_executors; else stage_header 7 "${STAGE_TITLES[6]}"; say "skipped: --skip-executors"; fi
    run_stage 8 stage_verify
    run_stage 9 stage_github
    run_stage 10 stage_semantic
    run_stage 11 stage_marker
    local login
    login="$(admin_login)"
    printf '\n'
    printf 'DONE: %s is installed at %s (%s). Administrator login %s; its password is in %s (owner only, do not read it). Semantic norm lookup: %s.%s Full output: %s\n' \
        "$INSTANCE" "$REPO" "$(git -C "$REPO" rev-parse --short HEAD)" "${login:-unknown}" "$(password_file)" "$(semantic_summary)" \
        "$([ -n "$OPT_DOMAIN" ] && echo " Open https://$OPT_DOMAIN." || echo " Open it through: ssh -L $HTTP_PORT:127.0.0.1:$HTTP_PORT <this server> then http://127.0.0.1:$HTTP_PORT.")" \
        "$LOG_FILE"
}

# --------------------------------------------------------------------------------------------------------- dry run
norms_plan_text() {
    if [ -n "$OPT_BUNDLE" ]; then
        echo "verify $OPT_BUNDLE, stream it into receive-bundle.sh on this host, open a test-data waiver with copy-serve.sh, import, report, resume, designate the snapshot"
    elif [ -f "$RELEASE_LOCK" ]; then
        echo "download the parts of the release infra/norms/bundle-release.lock names (curl, resumable, sha256 checked), stream them through zstd into receive-bundle.sh, open a test-data waiver, import, report, resume, designate the snapshot, delete the parts"
    else
        echo "skipped (no --norms-bundle, and the repository publishes none)"
    fi
}
print_plan() {
    local n done_text deploy_text
    if [ "$REPO_REAL" = "$DEPLOY_REAL" ]; then
        deploy_text="this clone is the deploy clone"
    elif [ -e "$DEPLOY_PATH" ] && [ -n "$(ls -A "$DEPLOY_PATH" 2>/dev/null || true)" ]; then
        deploy_text="$DEPLOY_PATH exists: it would be checked (this repository, clean) and used; this clone is only where it was started"
    else
        deploy_text="$DEPLOY_PATH would be made from the origin of this clone at its commit, and the installer would continue there; this clone is not touched"
    fi
    printf 'first-install: DRY RUN -- nothing below is done; nothing on this server is changed.\n'
    printf '  instance         %s\n  started in       %s\n  deploy clone     %s\n  environment      %s/infra/deploy/env/alpha.env\n' "$INSTANCE" "$REPO" "$deploy_text" "$DEPLOY_PATH"
    printf '  application port %s (loopback only)\n  domain           %s\n  administrator    %s\n' "$HTTP_PORT" "${OPT_DOMAIN:-none (no HTTPS)}" "${OPT_EMAIL:-<--email is required>}"
    printf '  norms bundle     %s\n  deploy user      %s\n' "${OPT_BUNDLE:-none}" "$OPT_DEPLOY_USER"
    printf '  state            %s\n  marker           %s\n  password file    %s\n  transcript       %s\n' "$STATE_FILE" "$MARKER" "$(password_file)" "$LOG_FILE"
    if [ -f "$MARKER" ] && [ -z "$OPT_RESUME" ]; then printf '  NOTE: the marker exists: a real run would stop with STOP [already_installed].\n'; fi
    local would=(
        "check that this is root, that git curl flock tar python3 ssh-keygen are present (installed with apt-get on Debian and Ubuntu if not), that Docker 20+ and compose v2 answer (installed from Docker's apt repository, key fingerprint pinned, if not), that at least $MIN_FREE_GIB GiB of disk and $STOP_RAM_AVAILABLE_MIB MiB of memory are free, that the deploy clone is clean, and (with --domain) that ports 80 and 443 are free"
        "create $DEPLOY_PATH/infra/deploy/env/alpha.env and provider.env from the examples if they are absent (mode 600; every secret generated, in every place it is written; ALPHA_NORM_EMBED=yes with its address empty; an existing file is never changed)"
        "run infra/deploy/deploy.sh; on a fresh database it ends [default_credential], which is expected"
        "generate the administrator's password into $(password_file) (mode 600), change it through the API, complete the profile with ${OPT_EMAIL:-the --email address}, run deploy.sh again"
        "$(norms_plan_text)"
        "$([ -n "$OPT_DOMAIN" ] && echo "check that DNS $OPT_DOMAIN points here; set the name; deploy with the test certificate, then the real one, then ALPHA_PUBLISH_HTTPS=yes" || echo "skipped (no --domain)")"
        "$([ "$OPT_SKIP_EXECUTORS" = no ] && echo "connect the claude / codex subscriptions of this server through local-agent.sh; stop with a printed instruction when none is signed in" || echo "skipped (--skip-executors)")"
        "run infra/deploy/verify-deployed.sh; it must exit 0 (the proxy is reloaded once and it is asked again if it does not)"
        "print DEPLOY_HOST, DEPLOY_KNOWN_HOSTS (with the host key fingerprint) and DEPLOY_PATH=$DEPLOY_PATH$([ "$OPT_NO_CI_KEY" = no ] && echo ", generate $SECRET_DIR/$INSTANCE-deploy-key and authorize it for $OPT_DEPLOY_USER (the private key is never printed)")"
        "$(norms_wanted && echo "run the two gates of NORM-VECTOR-TEMP-01 (memory above $SEMANTIC_MIN_AVAILABLE_MIB MiB with swap not growing; semantic_check on $SEMANTIC_WINDOWS windows); when both pass set AUDITMANAGER_NORM_EMBED_URL=$SEMANTIC_URL and restart the worker; otherwise leave it empty" || echo "not yet: the gates need the norms corpus (run again with --norms-bundle); the address stays empty and word search works")"
        "write the marker $MARKER and print the DONE line"
    )
    for n in $(seq 1 "$STAGE_COUNT"); do
        done_text=""
        if [ "$n" -eq 2 ] && [ -f "$DEPLOY_PATH/infra/deploy/env/alpha.env" ]; then done_text=" [already there: kept]"; fi
        if [ "$n" -gt 2 ] && [ "$n" -ne 9 ] && [ "$n" -ne 11 ] && state_has "s$n"; then done_text=" [done before: would be skipped]"; fi
        printf '\n[%s/%s] %s%s\n      would: %s\n' "$n" "$STAGE_COUNT" "${STAGE_TITLES[$((n - 1))]%%:*}" "$done_text" "${would[$((n - 1))]}"
    done
    printf '\nfirst-install: end of the dry run.\n'
}

main() {
    ORIG_ARGS=("$@")
    parse_args "$@"
    validate_args
    resolve_instance
    decide_deploy_path
    if [ -z "$OPT_DOMAIN" ] && state_has s6 && [ -f "$ENV_FILE" ]; then OPT_DOMAIN="$(env_get ALPHA_CERT_NAME)"; fi
    if [ "$OPT_DRY_RUN" = yes ]; then
        print_plan
        exit 0
    fi
    if [ -f "$MARKER" ] && [ -z "$OPT_RESUME" ]; then
        # An installation made without a norms bundle is finished by running the installer again with one.
        if norms_wanted && ! state_has s5.designated && ! state_has s10; then
            say "this server was installed without the norms: adding them, and then the semantic norm lookup"
        else
            stop already_installed "$(sed -n 's/^date=//p' "$MARKER" | head -n 1)" "$MARKER"
        fi
    fi
    [ "$(id -u)" -eq 0 ] || [ "$TEST_MODE" = yes ] || stop not_root
    mkdir -p "$LOG_DIR"
    # One run at a time: an agent whose tool timed out may start the command again while the first still works. A run started in
    # another clone holds the lock across its `exec` into the deploy clone and says so in the environment.
    private_dir "$STATE_DIR"
    if [ "${FIRST_INSTALL_LOCK_HELD:-}" = 1 ] && [ -e "/proc/$$/fd/200" ]; then
        :
    else
        exec 200>"$STATE_DIR/first-install.lock"
        flock -n 200 || stop already_running "$LOG_FILE"
    fi
    unset FIRST_INSTALL_LOCK_HELD
    local rc=0
    if [ "$REPO_REAL" != "$DEPLOY_REAL" ]; then
        # Started in the owner's working copy: make (or check) the deploy clone and continue in it with the same arguments.
        [ "${FIRST_INSTALL_REEXEC:-}" != 1 ] || stop unexpected "the deploy clone $DEPLOY_PATH is not where the script runs ($REPO)"
        { start_in_deploy_clone; } 2>&1 | tee -a "$LOG_FILE" || rc="${PIPESTATUS[0]}"
        [ "$rc" -eq 0 ] || exit "$rc"
        export FIRST_INSTALL_LOCK_HELD=1 FIRST_INSTALL_REEXEC=1
        exec "$DEPLOY_PATH/infra/deploy/first-install.sh" "${ORIG_ARGS[@]}"
    fi
    if [ -n "$OPT_RESUME" ]; then
        state_clear_from "$OPT_RESUME"
    fi
    { run_all; } 2>&1 | tee -a "$LOG_FILE" || rc="${PIPESTATUS[0]}"
    exit "$rc"
}

# Sourced by the tests: the functions are there and nothing runs.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi
