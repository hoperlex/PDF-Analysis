#!/usr/bin/env bash
# `FIRST-INSTALL-03` -- deploy this server's own checkout from its own origin, on this server, with no ssh: the pull-based twin of
# `.github/workflows/deploy-auto.yml`, for a fork whose server GitHub cannot reach.
#
#   sudo infra/deploy/deploy-local.sh [--sha SHA] [--if-moved] [--instance NAME | --deploy-path PATH] [--repository owner/name]
#
#   (no option)      deploy the tip of origin/main now. A person's command: it ignores the record of a failed SHA and retries.
#   --sha SHA        deploy that commit (it must be an ancestor of origin/main, as in the workflow).
#   --if-moved       a TIMER's run: deploy only when origin/main is not what this checkout already runs, never retry a SHA that
#                    failed until main moves, and when another deploy or the first install holds its lock, skip (exit 0).
#   --instance NAME  the deploy clone is /srv/NAME. --deploy-path PATH names it. Neither: the clone this script is in, when it holds
#                    an installation (infra/deploy/env/alpha.env); a script run from any other clone refuses.
#   --repository R   the repository this server accepts (owner/name). Default: the one recorded in /var/lib/<instance>/deploy-local.source
#                    when the installer enabled this mode (written from the clone's origin on first use if it is not there).
#
# WHAT IT RUNS IS THE WORKFLOW'S OWN REMOTE SCRIPT, VERBATIM, through `bash -s` as the workflow's ssh does: the origin owner/name
# binding (exit 4), the clean-tree check (exit 3), `git fetch --prune origin`, `git cat-file`, `git merge-base --is-ancestor <sha>
# origin/main`, `git checkout --detach`, `deploy.sh </dev/null`, `verify-deployed.sh </dev/null`, the final HEAD and clean checks and
# `DEPLOY OK: <sha>`. `tests/contract/test_deploy_auto_workflow.py` holds the heredoc below equal to the workflow's, so the two cannot
# drift. What this wrapper adds is outside that script: the SHA (the default is the tip of origin/main, read with `git ls-remote`, which
# writes nothing), an exclusive lock, a log, and the record of a failed SHA.
#
# LOCKS (`/var/lib/<instance>/`): `deploy-local.lock` (one deploy at a time) and `first-install.lock` (the installer's: a deploy never
# runs beside it, and the installer refuses to run beside a deploy). Both are `flock`ed without waiting.
# LOG: `/var/log/<instance>-deploy-local.log`, one block per deploy that was tried; a run that finds nothing to do prints and logs nothing.
# EXIT: the script's own (3 not clean, 4 foreign origin, 1 or deploy.sh's and verify-deployed.sh's); 2 usage; 75 busy (a person's run);
# 0 for a timer's skip. A failed SHA is written to /var/lib/<instance>/deploy-local.failed and a success removes it.

set -euo pipefail
umask 077

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
OWN_REPO="$(cd "$HERE/../.." && pwd -P)"
TEST_MODE=no
[ "${DEPLOY_LOCAL_TEST_MODE:-}" != 1 ] || TEST_MODE=yes
seam() { if [ "$TEST_MODE" = yes ] && [ -n "${!1:-}" ]; then printf '%s' "${!1}"; else printf '%s' "$2"; fi; }
STATE_ROOT="$(seam DEPLOY_LOCAL_STATE_ROOT /var/lib)"
LOG_DIR="$(seam DEPLOY_LOCAL_LOG_DIR /var/log)"
DEPLOY_ROOT="$(seam DEPLOY_LOCAL_DEPLOY_ROOT /srv)"

say() { printf 'deploy-local.sh: %s\n' "$*"; }
usage() {
    cat >&2 <<'USAGE'
usage: sudo infra/deploy/deploy-local.sh [--sha SHA] [--if-moved] [--instance NAME | --deploy-path PATH] [--repository owner/name]

  (no option)      deploy the tip of origin/main now (a person's run: it retries a SHA that failed before)
  --sha SHA        deploy that commit (an ancestor of origin/main)
  --if-moved       a timer's run: only when origin/main moved, never a failed SHA again, skip while another deploy or the install runs
  --instance NAME  the server's checkout is /srv/NAME      --deploy-path PATH  names it
  --repository R   the repository this server accepts (default: the one recorded when it was installed)
USAGE
    exit 2
}
die_usage() { printf 'deploy-local.sh: %s\n' "$1" >&2; usage; }

OPT_SHA="" OPT_IF_MOVED=no OPT_INSTANCE="" OPT_PATH="" OPT_REPOSITORY=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --sha|--instance|--deploy-path|--repository)
            if [ "$#" -lt 2 ] || [ -z "$2" ]; then die_usage "$1 needs a value"; fi
            case "$1" in
                --sha) OPT_SHA="$2" ;; --instance) OPT_INSTANCE="$2" ;; --deploy-path) OPT_PATH="$2" ;; --repository) OPT_REPOSITORY="$2" ;;
            esac
            shift 2 ;;
        --if-moved) OPT_IF_MOVED=yes; shift ;;
        -h|--help) usage ;;
        *) die_usage "unknown option: $1" ;;
    esac
done

# The remote script of `.github/workflows/deploy-auto.yml`, unchanged (the test compares the two byte for byte after the YAML's
# indentation is removed). It reads its three arguments the way the workflow passes them: the commit, the checkout, the repository.
run_workflow_script() { # run_workflow_script SHA CHECKOUT REPOSITORY
    bash -s -- "$1" "$2" "$3" 200>&- 201>&- <<'REMOTE'
set -euo pipefail

readonly DEPLOY_SHA="$1"
readonly REPOSITORY="$2"
readonly SOURCE_REPOSITORY="$3"

cd "$REPOSITORY"

echo "=== deployment source ==="
# A server deploys only the repository it was cloned from (owner ruling R-158f): a fork that
# holds this server's credentials still cannot roll it back to the fork point. The check reads
# owner/name from origin in any form (https, git@, ssh://, an ssh alias) and ignores case.
origin_url="$(git remote get-url origin)"
checkout_of="$(printf '%s\n' "$origin_url" | sed -E 's#/+$##; s#\.git$##; s#^.*[:/]([^:/]+)/([^:/]+)$#\1/\2#')"
printf '%s\n' "$SOURCE_REPOSITORY"
if [ "${checkout_of,,}" != "${SOURCE_REPOSITORY,,}" ]; then
  echo "REFUSED: $REPOSITORY is a checkout of '$checkout_of', but this deployment comes from '$SOURCE_REPOSITORY'." >&2
  echo "A server deploys only the repository it was cloned from; a fork names its own server in its own repository variables." >&2
  exit 4
fi

echo "=== requested revision ==="
printf '%s\n' "$DEPLOY_SHA"

echo "=== host before deployment ==="
git rev-parse HEAD
# The AR v3 removal (PR #55) deleted infra/deploy/ar-v3-pack/.gitignore, so the
# operator-installed pack files left on the host became untracked and refused run 95.
# They stay on the host and stay ignored, host-locally; nothing is deleted here.
if [ -d .git ]; then
  mkdir -p .git/info
  grep -qxF '/infra/deploy/ar-v3-pack/' .git/info/exclude 2>/dev/null \
    || printf '%s\n' '/infra/deploy/ar-v3-pack/' >> .git/info/exclude
fi
if [ -n "$(git status --porcelain --untracked-files=all)" ]; then
  echo "REFUSED: $REPOSITORY has tracked or untracked changes." >&2
  git status --short >&2
  exit 3
fi

echo "=== fetch publication authority ==="
GIT_TERMINAL_PROMPT=0 git fetch --prune origin

echo "=== verify requested revision ==="
git cat-file -e "${DEPLOY_SHA}^{commit}"
git merge-base --is-ancestor "$DEPLOY_SHA" origin/main

echo "=== select exact revision ==="
git checkout --detach "$DEPLOY_SHA"
test "$(git rev-parse HEAD)" = "$DEPLOY_SHA"
if [ -n "$(git status --porcelain --untracked-files=all)" ]; then
  echo "REFUSED: $DEPLOY_SHA leaves tracked or untracked changes in $REPOSITORY." >&2
  git status --short --untracked-files=all >&2
  exit 3
fi

echo "=== deploy ==="
# bash -s reads this script from stdin. Neither child may consume the
# remaining verification commands as its own input.
infra/deploy/deploy.sh </dev/null

echo "=== verify deployed tree ==="
infra/deploy/verify-deployed.sh </dev/null

test "$(git rev-parse HEAD)" = "$DEPLOY_SHA"
test -z "$(git status --porcelain --untracked-files=all)"

echo "DEPLOY OK: $DEPLOY_SHA"
REMOTE
}

repo_slug() { # owner/name of a clone address in any form, as the workflow's script reads it
    printf '%s\n' "$1" | sed -E 's#/+$##; s#\.git$##; s#^.*[:/]([^:/]+)/([^:/]+)$#\1/\2#'
}

main() {
    local deploy_path instance state_dir log_file source_file failed_file env_file origin_url checkout_of source head tip sha status=0 mode

    # --- which checkout, which instance -------------------------------------------------------------------------------------
    if [ -n "$OPT_PATH" ]; then
        deploy_path="$OPT_PATH"
    elif [ -n "$OPT_INSTANCE" ]; then
        deploy_path="$DEPLOY_ROOT/$OPT_INSTANCE"
    elif [ -f "$OWN_REPO/infra/deploy/env/alpha.env" ]; then
        deploy_path="$OWN_REPO"
    else
        die_usage "this clone holds no installation: name the server's checkout with --instance NAME or --deploy-path PATH"
    fi
    # The same rule the workflow applies to DEPLOY_PATH.
    if ! [[ "$deploy_path" =~ ^(/[A-Za-z0-9_.-]+)+$ ]] || [[ "$deploy_path/" == */../* ]] || [[ "$deploy_path/" == */./* ]]; then
        die_usage "the deploy path is an absolute path of letters, digits, '.', '_' and '-' (no . or .. component)"
    fi
    [ -d "$deploy_path/.git" ] || { say "REFUSED: $deploy_path is not a git clone" >&2; return 2; }
    env_file="$deploy_path/infra/deploy/env/alpha.env"
    instance=""
    if [ -r "$env_file" ]; then
        instance="$(sed -n 's/^[[:space:]]*\(export[[:space:]]\+\)\?ALPHA_INSTANCE=//p' "$env_file" | tail -n 1 | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/")"
    fi
    [ -n "$instance" ] || instance="${OPT_INSTANCE:-$(basename "$deploy_path")}"
    [[ "$instance" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,60}$ ]] || { say "REFUSED: '$instance' is not an instance name" >&2; return 2; }
    [ "$(id -u)" -eq 0 ] || [ "$TEST_MODE" = yes ] || { say "REFUSED: run it as root: sudo $0" >&2; return 2; }
    state_dir="$STATE_ROOT/$instance"
    log_file="$LOG_DIR/$instance-deploy-local.log"
    source_file="$state_dir/deploy-local.source"
    failed_file="$state_dir/deploy-local.failed"
    mkdir -p "$state_dir" "$LOG_DIR"
    chmod 700 "$state_dir"
    if [ "$OPT_IF_MOVED" = yes ]; then mode=timer; else mode=manual; fi

    # --- locks: one deploy at a time, and never beside the first install -----------------------------------------------------
    exec 200>"$state_dir/deploy-local.lock"
    exec 201>>"$state_dir/first-install.lock"
    if ! flock -n 200; then
        if [ "$mode" = timer ]; then say "skipped: another deploy-local.sh is running"; return 0; fi
        say "busy: another deploy-local.sh is running (its output is in $log_file)" >&2; return 75
    fi
    if ! flock -n 201; then
        if [ "$mode" = timer ]; then say "skipped: first-install.sh is running"; return 0; fi
        say "busy: first-install.sh is running (its output is in $LOG_DIR/$instance-first-install.log)" >&2; return 75
    fi

    # --- the repository this server accepts: the binding the workflow's script applies, checked before anything is read from origin ---
    origin_url="$(git -C "$deploy_path" remote get-url origin 2>/dev/null || true)"
    [ -n "$origin_url" ] || { say "REFUSED: $deploy_path has no origin" >&2; return 4; }
    checkout_of="$(repo_slug "$origin_url")"
    if [ -n "$OPT_REPOSITORY" ]; then
        source="$OPT_REPOSITORY"
    elif [ -r "$source_file" ]; then
        source="$(head -n 1 "$source_file")"
    else
        source="$checkout_of"
        printf '%s\n' "$source" > "$source_file"
        say "recorded $source as the repository this server accepts ($source_file)"
    fi
    [[ "$source" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || { say "REFUSED: '$source' is not owner/name" >&2; return 2; }
    if [ "${checkout_of,,}" != "${source,,}" ]; then
        say "REFUSED: $deploy_path is a checkout of '$checkout_of', but this server accepts '$source'." >&2
        say "A server deploys only the repository it was cloned from; to move it, run: git -C $deploy_path remote set-url origin <the new address> and delete $source_file" >&2
        return 4
    fi

    # --- which commit ----------------------------------------------------------------------------------------------------------
    if [ -n "$OPT_SHA" ]; then
        [[ "$OPT_SHA" =~ ^[0-9a-f]{40}$ ]] || die_usage "--sha is 40 lower-case hex digits"
        sha="$OPT_SHA"
    else
        # `git ls-remote` reads the tip of main and writes nothing; the script then fetches and checks that this commit is on main.
        tip="$(GIT_TERMINAL_PROMPT=0 git -C "$deploy_path" ls-remote origin refs/heads/main 2>/dev/null | awk '{ print $1; exit }' || true)"
        if ! [[ "$tip" =~ ^[0-9a-f]{40}$ ]]; then
            if [ "$mode" = timer ]; then say "skipped: origin did not answer for refs/heads/main (the next run asks again)"; return 0; fi
            say "FAILED: origin did not answer for refs/heads/main" >&2; return 3
        fi
        sha="$tip"
    fi
    head="$(git -C "$deploy_path" rev-parse HEAD 2>/dev/null || true)"
    if [ "$mode" = timer ]; then
        # The failure comes first: the script checks the commit out BEFORE it deploys, so after a failed deploy HEAD is that commit
        # and "this checkout already runs it" would be false comfort.
        if [ -r "$failed_file" ] && [ "$(awk '{ print $1; exit }' "$failed_file")" = "$sha" ]; then
            say "skipped: ${sha:0:12} failed before ($(cut -d' ' -f2- "$failed_file")) and origin/main has not moved; run deploy-local.sh by hand to try again"
            return 0
        fi
        if [ "$head" = "$sha" ]; then say "nothing to do: this checkout already runs ${sha:0:12}"; return 0; fi
    fi

    # --- the deploy: the workflow's script, logged ----------------------------------------------------------------------------------
    {
        printf '=== deploy-local.sh %s: %s of %s in %s (%s run) ===\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$sha" "$source" "$deploy_path" "$mode"
    } | tee -a "$log_file"
    run_workflow_script "$sha" "$deploy_path" "$source" </dev/null 2>&1 | tee -a "$log_file" || status="${PIPESTATUS[0]}"
    if [ "$status" -eq 0 ]; then
        rm -f "$failed_file"
        say "DEPLOYED ${sha:0:12} (log: $log_file)"
    else
        printf '%s %s status=%s\n' "$sha" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$status" > "$failed_file"
        say "FAILED with status $status for ${sha:0:12}; it is not retried by the timer until origin/main moves (log: $log_file)" >&2
    fi
    return "$status"
}

main "$@"; exit $?
