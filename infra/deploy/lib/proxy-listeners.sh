# shellcheck shell=bash
# `PROD-01-TLS-ACME-01` (`R-146a`, `R-146s`, `R-146aa`, `ADR-0021` section 2) -- THE ONE PLACE
# THAT DECIDES WHICH OF THE PROXY'S THREE LISTENERS EXIST.
#
# Sourced, never run. `deploy.sh` and `verify-deployed.sh` source it today; `PROD-02` makes
# `reset.sh --restore` and `copy-serve.sh restore-db` call the same two functions after a restore, so
# the rule is written once and cannot drift between the scripts that apply it. (The copy key's script
# is installed apart from the checkout -- `DEPLOYMENT_RUNBOOK.md` section 13 -- so the owner repeats that
# install when `PROD-02` wires it in; nothing in this lane changes `copy-serve.sh`.)
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
#   https_wanted    `yes` when the credential gate is satisfied. In THIS lane that is the explicit
#                   setting `ALPHA_PUBLISH_HTTPS=yes`; `PROD-02` replaces the caller's computation of
#                   this one word by the exit status of `python -m auditmanager.access.check` and
#                   changes nothing here.
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
        echo "withheld: the credential gate is not satisfied (ALPHA_PUBLISH_HTTPS is not yes), so 443 stays closed"
    elif [ "$pair_present" != yes ]; then
        echo "withheld: no certificate pair exists yet ($pair_present), so there is nothing to serve on 443"
    else
        echo "published"
    fi
}
