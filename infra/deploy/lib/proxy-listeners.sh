# shellcheck shell=bash
# `PROD-01-TLS-ACME-01` (`R-146a`, `R-146s`, `R-146aa`, `ADR-0021` section 2) -- THE ONE PLACE
# THAT DECIDES WHICH OF THE PROXY'S THREE LISTENERS EXIST.
#
# Sourced, never run. `deploy.sh`, `verify-deployed.sh`, `reset.sh` (`--restore`) and `copy-serve.sh`
# (`restore-db`) all source it, so the rule is written once and cannot drift between the scripts that
# apply it. The copy key's script is installed apart from the checkout (`DEPLOYMENT_RUNBOOK.md` section 13),
# so THIS FILE is one of the files the owner extracts there, beside `lib/forced-command.sh`: it sources
# `$HERE/lib/proxy-listeners.sh`, and `status` prints this file's SHA-256 (`PROD-02`).
#
# THE THREE LISTENERS, and the compose file each one needs:
#
#   plain application listener   127.0.0.1:${ALPHA_HTTP_PORT} -> container 8080
#                                ALWAYS. It is `compose.server.yml` itself.
#   challenge listener           public port 80 -> container 8081: the ACME webroot and a redirect to
#                                HTTPS, no application route. `infra/acme/compose.acme.yml`, whenever a
#                                certificate name is configured -- so issuance and renewal work while
#                                the seeded password is still the seeded one.
#   application listener (TLS)   public port 443 -> container 8443. `infra/deploy/proxy/compose.tls.yml`,
#                                only when BOTH the caller says the credential gate is satisfied AND a
#                                certificate pair already exists.
#
# WHAT THE CALLER SUPPLIES, and why these are arguments and not reads:
#
#   cert_name       `ALPHA_CERT_NAME`. Empty means "no ACME": the answer is the stack exactly as it was
#                   before this lane, with no overlay at all.
#   https_wanted    `yes` when the credential gate is satisfied. Since `PROD-02` that is
#                   `listeners_https_wanted`: the operator's setting `ALPHA_PUBLISH_HTTPS=yes` AND the
#                   verdict `clean` of `python -m auditmanager.access.check --gate` (the seeded
#                   `admin`/`password` pair is not valid). The setting alone no longer opens 443.
#   pair_present    `yes` when `fullchain.pem` and `privkey.pem` exist and are non-empty in the
#                   certificate volume. `unknown` is a third answer and is treated as "not yes": a pair
#                   nobody could confirm is not a pair.
#
# Taking the three as arguments keeps the rule a pure function of its inputs, so a test can drive every
# row of the table without a daemon, and so the caller -- not this file -- owns every side effect.

# A public DNS name that a certificate authority could issue for, and nothing else, because the value is
# pasted into a command line (`certbot -d`) and into a redirect. Lower-case LDH labels, at least two of
# them, each 1 to 63 characters, no leading or trailing hyphen, 253 characters at most, no wildcard, no
# trailing dot, and a last label that is not all digits (so an IP literal is not a name). Prints the
# reason on stdout and returns 1 when it is not.
listeners_name_problem() {
    local name="${1-}" label
    [ -n "$name" ] || { echo "it is empty"; return 1; }
    [ "${#name}" -le 253 ] || { echo "it is longer than 253 characters"; return 1; }
    case "$name" in
        *[!a-z0-9.-]*) echo "it holds a character other than a-z, 0-9, '.' and '-' (lower case only; no wildcard, no port, no scheme)"; return 1 ;;
        .*|*.) echo "it starts or ends with a dot"; return 1 ;;
        *..*) echo "it has an empty label"; return 1 ;;
        *.*) ;;
        *) echo "it is a single label, not a public DNS name"; return 1 ;;
    esac
    local IFS=.
    # shellcheck disable=SC2206  # splitting on the dots is the point
    local labels=($name)
    for label in "${labels[@]}"; do
        [ "${#label}" -le 63 ] || { echo "the label '$label' is longer than 63 characters"; return 1; }
        case "$label" in
            -*|*-) echo "the label '$label' starts or ends with a hyphen"; return 1 ;;
        esac
    done
    case "${labels[${#labels[@]}-1]}" in
        *[!0-9]*) ;;
        *) echo "its last label is all digits, so it is an IP address and not a name"; return 1 ;;
    esac
    # The reserved and documentation names a certificate authority refuses, and the shape the example
    # file ships. Refused by NAME rather than by comparing with the example's text, so a rewritten
    # example cannot make the guard stop recognising a placeholder.
    case "$name" in
        *.example|*.invalid|*.test|*.localhost|*.local|example.com|*.example.com|example.net|*.example.net|example.org|*.example.org)
            echo "it is a reserved or documentation name (the placeholder of alpha.env.example), not the host's own"
            return 1 ;;
    esac
    return 0
}

# Prints, one per line, the compose files that come AFTER `compose.server.yml` for the given decision,
# as absolute paths. Prints nothing when cert_name is empty. Returns 2 (and prints nothing) when a file
# it would name is not there: a half-installed clone must not produce a shorter list that looks fine.
#
#   listeners_overlay_files <deploy_dir> <cert_name> <https_wanted> <pair_present>
listeners_overlay_files() {
    local deploy_dir="${1:?deploy_dir}" cert_name="${2-}" https_wanted="${3-no}" pair_present="${4-no}"
    [ -n "$cert_name" ] || return 0
    local acme tls with_tls=no
    acme="$deploy_dir/../acme/compose.acme.yml"
    tls="$deploy_dir/proxy/compose.tls.yml"
    if [ "$https_wanted" = yes ] && [ "$pair_present" = yes ]; then
        with_tls=yes
    fi
    # Every file the answer would name is checked BEFORE any is printed, so a half-installed clone yields an
    # error and an empty list, never a prefix of the list that looks like a smaller, working one.
    [ -f "$acme" ] || return 2
    [ "$with_tls" = no ] || [ -f "$tls" ] || return 2
    echo "$(cd "$(dirname "$acme")" && pwd)/compose.acme.yml"
    if [ "$with_tls" = yes ]; then
        echo "$(cd "$(dirname "$tls")" && pwd)/compose.tls.yml"
    fi
    return 0
}

# One line: `published`, or `withheld: <reason>`. The reason is the FIRST thing that is false, in the order
# an operator can act on it. `withheld` is not an error: it is the state `R-146s` accepts on a host that
# has never been published, and after a restore that brings the default credential back.
#
#   listeners_https_verdict <cert_name> <https_wanted> <pair_present>
listeners_https_verdict() {
    local cert_name="${1-}" https_wanted="${2-no}" pair_present="${3-no}"
    if [ -z "$cert_name" ]; then
        echo "withheld: no certificate name is configured (ALPHA_CERT_NAME), so this stack does not terminate TLS"
    elif [ "$https_wanted" != yes ]; then
        echo "withheld: the credential gate is not satisfied (ALPHA_PUBLISH_HTTPS is not yes, or the published admin/password pair is still valid), so 443 stays closed"
    elif [ "$pair_present" != yes ]; then
        echo "withheld: no certificate pair exists yet ($pair_present), so there is nothing to serve on 443"
    else
        echo "published"
    fi
}

# --- THE CREDENTIAL GATE (`PROD-02-03-DEPLOY-GATES-01`; `R-146i`, `R-146s`, `R-146z`; ADR-0023 section 3) --------
#
# A deployment is not successful, and 443 is not published, while the PUBLISHED SEEDED PAIR (`admin` /
# `password`) is valid. The question is asked of the database by `auditmanager.access.check --gate` inside the
# `api` image (the host promises no python -- `DEPLOYMENT_RUNBOOK.md` section 1). A temporary password an
# administrator issued is a WARNING line of the same output and never moves the verdict (`R-146z`).
#
# Three scripts apply the answer and one restore path in each of two scripts closes the door on a finding
# (`deploy.sh`, `verify-deployed.sh`, `reset.sh --restore`, `copy-serve.sh restore-db`), so the sentinels, the
# classification and the "withdraw 443" step are written once, here.

LISTENERS_GATE_CLEAN='access-check GATE OK no published credential'
LISTENERS_GATE_FINDING='access-check GATE DEFAULT CREDENTIAL'
# shellcheck disable=SC2034  # read by the scripts that source this file, and by their tests
LISTENERS_GATE_WARNING='access-check GATE WARNING temporary password'

# One word on stdout: `clean`, `finding` or `unknown`. THE SENTINEL AND THE STATUS MUST AGREE, and anything
# else is `unknown`: a `run` that could not start (no image, no daemon, no database) exits non-zero and prints
# no sentinel, and "nothing could be asked" must never read as "no finding" -- the same argument `deploy.sh`'s
# `migrations-at-head` makes for its own sentinel (the evidence is the line, not the exit code).
#
#   listeners_gate_verdict <status> <output>
listeners_gate_verdict() {
    local status="${1-}" output="${2-}" clean=no finding=no
    if printf '%s\n' "$output" | grep -qxF "$LISTENERS_GATE_CLEAN"; then clean=yes; fi
    if printf '%s\n' "$output" | grep -qF "$LISTENERS_GATE_FINDING"; then finding=yes; fi
    if [ "$status" = 0 ] && [ "$clean" = yes ] && [ "$finding" = no ]; then
        echo clean
    elif [ "$status" = 1 ] && [ "$finding" = yes ] && [ "$clean" = no ]; then
        echo finding
    else
        echo unknown
    fi
}

# The logins named by the finding lines, one per line, NAMES ONLY (the gate prints no secret, and neither does
# this).
#
#   listeners_gate_logins <output>
listeners_gate_logins() {
    printf '%s\n' "${1-}" | sed -n "s/^${LISTENERS_GATE_FINDING}: login=\([^ ]*\).*/\1/p"
}

# Runs the gate through the caller's own `compose` function (every script wraps `docker compose --env-file ...
# --file ...` its own way, and the gate needs no file but the base one) and sets three globals instead of
# printing, so the caller keeps its own stdout: LISTENERS_GATE_STATUS, LISTENERS_GATE_OUTPUT (stdout and stderr
# together, as the operator should read them) and LISTENERS_GATE_VERDICT.
#
#   listeners_gate_run <compose-function>
# shellcheck disable=SC2034  # set here, read by the scripts that source this file
LISTENERS_GATE_STATUS=0
LISTENERS_GATE_OUTPUT=""
LISTENERS_GATE_VERDICT=unknown
listeners_gate_run() {
    local compose_fn="${1:?compose function}"
    LISTENERS_GATE_STATUS=0
    LISTENERS_GATE_OUTPUT="$("$compose_fn" run --rm --no-deps -T --entrypoint python api \
        -m auditmanager.access.check --gate 2>&1 </dev/null)" || LISTENERS_GATE_STATUS=$?
    # shellcheck disable=SC2034  # read by the caller
    LISTENERS_GATE_VERDICT="$(listeners_gate_verdict "$LISTENERS_GATE_STATUS" "$LISTENERS_GATE_OUTPUT")"
}

# `yes` only when the operator asked for HTTPS (`ALPHA_PUBLISH_HTTPS=yes`) AND the gate is `clean`. This is
# the whole of what replaced PROD-01's computation: the setting is necessary, never sufficient.
#
#   listeners_https_wanted <publish_setting> <gate_verdict>
listeners_https_wanted() {
    if [ "${1-}" = yes ] && [ "${2-}" = clean ]; then echo yes; else echo no; fi
}

# 0 when the proxy container publishes its TLS port (8443 inside) on the host, 1 when it does not or when there
# is no proxy container. It asks docker about the container by its published container port and not "does a
# proxy exist" (`deploy.sh`'s `public-ports-free` argument): a proxy that exists WITHOUT the port is the case
# that matters.
#
#   listeners_https_published <compose-function>
listeners_https_published() {
    local compose_fn="${1:?compose function}" cid
    cid="$("$compose_fn" ps --quiet proxy 2>/dev/null | head -1 || true)"
    [ -n "$cid" ] || return 1
    docker port "$cid" 8443/tcp 2>/dev/null | grep -q .
}

# Recreates ONLY the proxy (`--no-deps`: not the api, the web or the worker) with exactly the compose files the
# decision names, which is how the 443 overlay is added or taken away: compose recreates a service whose
# definition changed and leaves one whose definition did not, so a decision that matches the running proxy
# restarts nothing. No certificate name means no terminator and nothing to apply. Returns 2 when a file the
# decision names is not there, and `up`'s own status otherwise.
#
#   listeners_apply_https <deploy_dir> <env_file> <cert_name> <https_wanted> <pair_present>
listeners_apply_https() {
    local deploy_dir="${1:?deploy_dir}" env_file="${2:?env_file}" cert_name="${3-}" wanted="${4-no}" pair="${5-no}"
    local overlays overlay files=()
    [ -n "$cert_name" ] || return 0
    overlays="$(listeners_overlay_files "$deploy_dir" "$cert_name" "$wanted" "$pair")" || return 2
    while IFS= read -r overlay; do
        [ -z "$overlay" ] || files+=(--file "$overlay")
    done <<<"$overlays"
    docker compose --env-file "$env_file" --file "$deploy_dir/compose.server.yml" "${files[@]}" up -d --no-deps proxy
}

# THE RESTORE PATHS' STEP (`reset.sh --restore`, `copy-serve.sh restore-db`): on a finding the proxy is
# recreated WITHOUT the 443 overlay, so the site is unreachable from outside until an administrator changes the
# password (the consequence `R-146s` accepts). Returns 0 when, afterwards, 8443 is not published (including
# "it never was"); 1 when it could not be withdrawn or is still published. The stack keeps running; only the
# published mapping goes.
#
#   listeners_withhold_https <compose-function> <deploy_dir> <env_file> <cert_name>
listeners_withhold_https() {
    local compose_fn="${1:?compose function}" deploy_dir="${2:?deploy_dir}" env_file="${3:?env_file}" cert_name="${4-}"
    listeners_https_published "$compose_fn" || return 0
    listeners_apply_https "$deploy_dir" "$env_file" "$cert_name" no no || return 1
    if listeners_https_published "$compose_fn"; then return 1; fi
    return 0
}
