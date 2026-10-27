#!/usr/bin/env bash
# `D-27` -- one command that answers "is the stack in front of me this tree?"
#
#   infra/deploy/verify-deployed.sh [--env-file <path>] [--repo <path>] [--acme-rehearsal]
#
# Exit 0: the deployed stack is this working tree. Exit 6: it is not. Exit 4: the question
# could not be answered. Exit 7: the stack is this tree and the certificate it serves is not
# acceptable (`PROD-01-TLS-ACME-01`, below). Exit 8: the stack is this tree and the published
# seeded pair (`admin` / `password`) is valid (`PROD-02`, section 5 below). Exit 9: the stack is this tree, the
# certificate is acceptable, and the answer served on the name lacks the transport hardening the
# configuration promises -- HSTS, the four security headers, a `Secure` session cookie, no version in
# the `Server` banner (`HARDEN-01`, `EXPOSURE-REVIEW-02` `F-17`, section 4b below). **All failures are failures.** The row this closes is not "the
# stack drifted" -- it is that three waves running, nothing noticed, because there was no
# check to be red. A probe that skips when it is unsure is the same nothing with a nicer
# face, so there is no path through this script that reports success without having
# compared bytes.
#
# WHY THIS COMPARES FILE BYTES AND NOT THE SERVED DOCUMENT.
#
# `D-27` suggests comparing the served `/openapi.json` -- "the served document's digest, or
# simply the commit the image was built from" -- to `HEAD`. Both were tried against the
# running alpha stack before this was written, and neither answers the question:
#
#  1. **The served document is not the frozen one and cannot be.** `api/app.py` generates it
#     at run time and `contracts/api/v1/openapi.json` is frozen by hand. Measured on the
#     alpha stack at `313e753`: the two differ, and they still differ after dropping
#     `description`, `summary` and `title` -- in `paths`, `components`, `info` AND
#     `security`. That is not drift; it is why `tests/contract/api_v1/openapi_conformance.py`
#     is a conformance engine rather than a digest comparison. There is no digest to compare.
#
#  2. **Even a correct comparison of the two documents is blind to the drift this row was
#     created by.** `W20-EXEC`'s `src/auditmanager/runs/carrier.py` was missing from the
#     deployed image. Measured: the document this tree's code generates is
#     `083b296e09d5a420...`, and it is still `083b296e09d5a420...` -- byte for byte -- with a
#     line appended to `carrier.py`. The API surface is a few dozen of the image's 191 files.
#     A probe that watches the surface would have been GREEN on the exact defect that made
#     this row, and green is what a session would then have certified.
#
#  3. **A commit label is the builder's claim, not the image's contents.** It says what
#     somebody meant to build. It also needs a rebuild before it can say anything at all,
#     so it cannot answer the question about the stack that is already running -- which is
#     the only stack anyone ever needs to ask about.
#
# So this asks the image what it contains. The Dockerfiles declare exactly which paths of
# this repository enter each image; this reads those `COPY` lines OUT OF THE DOCKERFILES'
# OWN BYTES -- the idiom `Dockerfile.api` already uses on the Makefile's `UV_VERSION` -- and
# for every git-tracked file under them compares the bytes in the working tree to the bytes
# inside the running container. On the stale `auditmanager-w15b` stack this prints, by name:
# `src/auditmanager/runs/carrier.py  MISSING FROM THE IMAGE`.
#
# AND IT CHECKS THE PROXY FIRST, which is the second face of the same row. After
# `docker compose up --build` replaced the api and web containers, nginx held the dead
# upstream's address and **everything through the proxy answered 502** while both new
# containers were healthy. A rebuild is not finished when the images are. `reload-proxy.sh`
# is the repair; this is what tells you that you need it, because a stack whose images are
# perfect and whose proxy answers 502 is not a deployed stack.
#
# AND IT ASKS THE PROXY WHAT CONFIGURATION IT READS, which is `W49-FIX` / `B-1`. The proxy's
# configuration is not in an image: `compose.server.yml` bind-mounts `proxy/nginx.conf` as a
# single file, and a single-file bind mount keeps the inode the file had when the container
# started. `git checkout` replaces a changed file with a new inode, so after a deploy the
# running proxy went on reading -- and `nginx -s reload` went on re-reading -- the OLD file,
# while this script, which then compared only the images, called the stack this tree.
# Measured by `W49-JUDGE-X` (`docs/program/reviews/W49-JUDGE-X.md` section 7.4); the
# registration throttle of `W49-EDGE-01` would have been absent behind a green deploy. So
# every bind mount of the running proxy is read from the container itself, mapped back to
# the tree, and compared by SHA-256 inside the container, exactly as the image files are.
#
# IT SENDS NO REQUEST BURST. Whether the throttle answers 429 is a property of the
# configuration this section compares; proving it by flooding the registration endpoints
# would be a side effect on the live stand, and this script runs on every production
# deploy. The burst is driven against a disposable stand instead, in
# `tests/integration/composition/test_proxy_config_follows_checkout.py`.
#
# WHAT IT COMPARES AGAINST is the WORKING TREE, not `HEAD`. "Is the deployed stack the
# repository in front of me" is the question an operator actually has, and a dirty tree is
# itself a reason the answer is no. `HEAD` and the dirty state are printed for the record.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$HERE/compose.server.yml"
ENV_FILE="${ALPHA_ENV_FILE:-$HERE/env/alpha.env}"
REPO="$(cd "$HERE/../.." && pwd)"

DRIFT=6
UNANSWERABLE=4
CERTIFICATE=7
CREDENTIAL=8
HEADERS=9
REHEARSAL=no

while [ "$#" -gt 0 ]; do
    case "$1" in
        --env-file) ENV_FILE="${2:-}"; shift 2 ;;
        --repo) REPO="${2:-}"; shift 2 ;;
        --acme-rehearsal) REHEARSAL=yes; shift ;;
        -h|--help)
            sed -n '2,4p' "${BASH_SOURCE[0]}" >&2
            exit 2 ;;
        *)
            printf 'verify-deployed.sh: unrecognised option: %s\n' "$1" >&2
            exit 2 ;;
    esac
done

fail() {
    local status="$1"; shift
    printf '\nverify-deployed.sh: %s\n' "$1" >&2
    shift
    [ "$#" -eq 0 ] || printf '  %s\n' "$@" >&2
    exit "$status"
}

[ -r "$ENV_FILE" ] || fail "$UNANSWERABLE" \
    "the deployment environment $ENV_FILE is missing or unreadable." \
    "Without it there is no instance to ask about. See env/alpha.env.example."
[ -r "$COMPOSE_FILE" ] || fail "$UNANSWERABLE" "$COMPOSE_FILE is missing."
command -v git >/dev/null || fail "$UNANSWERABLE" "no git: the tree side cannot be read."

configured() {
    sed -n "s/^[[:space:]]*\(export[[:space:]]\+\)\?$1=//p" "$ENV_FILE" | tail -1 \
        | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/"
}

INSTANCE="$(configured ALPHA_INSTANCE)"
HTTP_PORT="$(configured ALPHA_HTTP_PORT)"
[ -n "$INSTANCE" ] || fail "$UNANSWERABLE" "$ENV_FILE names no ALPHA_INSTANCE."
[ -n "$HTTP_PORT" ] || fail "$UNANSWERABLE" "$ENV_FILE names no ALPHA_HTTP_PORT."

HEAD_SHA="$(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo '<not a git tree>')"
if [ -n "$(git -C "$REPO" status --porcelain 2>/dev/null)" ]; then
    DIRTY=" (working tree has uncommitted changes)"
else
    DIRTY=""
fi

echo "verify-deployed.sh: instance   $INSTANCE"
echo "verify-deployed.sh: repository $REPO at $HEAD_SHA$DIRTY"
echo "verify-deployed.sh: proxy      http://127.0.0.1:$HTTP_PORT"
echo

# --- 1. the proxy, before anything else ---------------------------------------------
# A rebuild replaces the api and web containers and nginx keeps the address it resolved at
# start-up. Measured: both new containers healthy, every path through the proxy 502.
echo "-- the proxy answers --"
command -v curl >/dev/null || fail "$UNANSWERABLE" "no curl: the proxy cannot be asked."
# `|| true` and not `|| echo 000`: curl PRINTS `000` and ALSO exits non-zero when it cannot
# connect, so the fallback ran too and the refusal read "the proxy answered 000000", which
# is a confusing message in a script whose whole job is not to be confusing.
PROXY_CODE="$(curl -s -o /dev/null -m 20 -w '%{http_code}' \
    "http://127.0.0.1:$HTTP_PORT/api/v1/openapi.json" || true)"
[ -n "$PROXY_CODE" ] || PROXY_CODE=000
if [ "$PROXY_CODE" = 502 ] || [ "$PROXY_CODE" = 503 ] || [ "$PROXY_CODE" = 504 ]; then
    fail "$DRIFT" "the proxy answered $PROXY_CODE on /api/v1/openapi.json." \
        "That is nginx holding an upstream that is no longer there -- the shape a rebuild" \
        "leaves behind when only the images were replaced. The images may be perfect and" \
        "this stack still serves nothing. Repair it with:" \
        "    infra/deploy/reload-proxy.sh"
fi
# `R-31` closed this path behind a credential, so the answer that proves life is 401.
# A 401 can only come from the application authorization seam; nginx holding a dead
# upstream answers 502, 503 or 504, which the branch above already names. A 200 means the
# four documentation routes are open again and is refused on its own terms.
if [ "$PROXY_CODE" = 200 ]; then
    fail "$DRIFT" "/api/v1/openapi.json answered 200 with no credential." \
        "R-31 closed the four documentation routes and this stack serves the full API" \
        "description to any caller that reaches the port. Nothing was compared."
fi
[ "$PROXY_CODE" = 401 ] || fail "$UNANSWERABLE" \
    "the proxy answered $PROXY_CODE on /api/v1/openapi.json, not 401." \
    "Nothing was compared. Is the stack up, and is ALPHA_HTTP_PORT right?"
echo "  401 on /api/v1/openapi.json -- the API answered and D-73 is closed here"
echo

# --- 2. what the Dockerfiles say goes into each image -------------------------------
# One row per path this repository contributes to an image:
#
#   <service> <container> <host source> <container destination> <extras-checked>
#
# `extras-checked` is whether a file present in the image under that root but absent from
# the tree is an error. It is `yes` everywhere except `/web`, because the web image's
# runtime stage is `COPY --from=build /web /web` and that directory also holds
# `node_modules` and `.next`, which are build products and were never in the tree. Saying
# so here is better than a check that quietly excludes them.
MAPPINGS="$(
    # Dockerfile.api: the RUNTIME stage's own COPY lines. `--from=build` brings the virtual
    # environment, which comes from `uv.lock` rather than from a tracked path, and the build
    # stage's own COPYs never reach the shipped image.
    awk '
        tolower($1) == "from" { stage++ }
        stage == 2 && tolower($1) == "copy" && $2 !~ /^--/ && NF == 3 {
            print "api\tapi\t" $2 "\t" $3 "\tyes"
        }
    ' "$HERE/Dockerfile.api"
    # Dockerfile.web: its runtime stage copies the BUILD stage wholesale, so the tracked
    # path that reaches the image is the build stage's `COPY web/ ./` under `WORKDIR /web`.
    # The line above it, `COPY web/package.json web/package-lock.json ./`, is a subset of it
    # and needs no row of its own.
    awk '
        tolower($1) == "copy" && $2 == "web/" { found = 1 }
        END { if (found) print "web\tweb\tweb/\t/web\tno" }
    ' "$HERE/Dockerfile.web"
)"

# A parse that found nothing must not read as a stack with nothing wrong with it. `src/` is
# named rather than a count: a threshold would be a number to argue with, and the one thing
# this probe may never be blind to is the application's own source.
grep -q "^api	api	src/	" <<<"$MAPPINGS" || fail "$UNANSWERABLE" \
    "Dockerfile.api's runtime COPY of src/ could not be read." \
    "This probe derives what it checks from those lines; a parse that found nothing would" \
    "otherwise report a perfect stack. Fix the parse, do not trust this green."
grep -q '^web	' <<<"$MAPPINGS" || fail "$UNANSWERABLE" \
    "Dockerfile.web no longer copies web/ into the image, so this probe does not know" \
    "what the web image is made of."

# `R-105`, `W54-WORKER-01`. The worker service runs the API's image, so its container is
# compared against the same lines as the API's. It is a separate container and is only
# replaced when compose recreates it, so a worker left on an older image is drift even
# while the API is current. Asked only when the compose file declares a worker service:
# the W53 rollback (`EXECUTION_ROLE: all`, no worker) has none to ask about.
if grep -q '^  worker:[[:space:]]*$' "$COMPOSE_FILE"; then
    MAPPINGS="$MAPPINGS
$(grep '^api	' <<<"$MAPPINGS" | sed 's/^api	api	/worker	worker	/')"
fi

compose() { docker compose --env-file "$ENV_FILE" --file "$COMPOSE_FILE" "$@"; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

PROBLEMS=0
LAST_SERVICE=""

while IFS=$'\t' read -r service svc_name host_src container_dst extras; do
    [ -n "$service" ] || continue
    if [ "$service" != "$LAST_SERVICE" ]; then
        [ -z "$LAST_SERVICE" ] || echo
        echo "-- the $service image against the tree --"
        LAST_SERVICE="$service"
        CONTAINER="$(compose ps --quiet "$svc_name" 2>/dev/null | head -1)"
        [ -n "$CONTAINER" ] || fail "$UNANSWERABLE" \
            "no running container for the '$svc_name' service of $INSTANCE." \
            "Nothing was compared."
    fi

    : > "$WORK/expected"
    : > "$WORK/wanted"
    if [ "${host_src%/}" != "$host_src" ]; then
        # A directory. Every git-tracked file under it, at the same relative path inside.
        base="${container_dst%/}"
        while IFS= read -r tracked; do
            [ -n "$tracked" ] || continue
            [ -f "$REPO/$tracked" ] || fail "$UNANSWERABLE" \
                "$tracked is tracked but not in the working tree." \
                "The tree side of this comparison is incomplete, so nothing is concluded."
            rel="${tracked#"$host_src"}"
            printf '%s\n' "$base/$rel" >> "$WORK/wanted"
            printf '%s  %s\n' "$(sha256sum "$REPO/$tracked" | cut -d' ' -f1)" "$base/$rel" \
                >> "$WORK/expected"
        done < <(git -C "$REPO" ls-files -- "$host_src")
    else
        [ -f "$REPO/$host_src" ] || fail "$UNANSWERABLE" "$host_src is not in the tree."
        printf '%s\n' "$container_dst" >> "$WORK/wanted"
        printf '%s  %s\n' "$(sha256sum "$REPO/$host_src" | cut -d' ' -f1)" "$container_dst" \
            >> "$WORK/expected"
    fi

    tr '\n' '\0' < "$WORK/wanted" > "$WORK/wanted.z"
    # `sha256sum` prints "<digest>  <path>" for a file it read and an error to stderr for
    # one it did not, so a file the image does not have simply has no line -- which is the
    # `carrier.py` case, and it is reported by name rather than as a count.
    docker exec -i "$CONTAINER" sh -c 'xargs -0 -r sha256sum 2>/dev/null || true' \
        < "$WORK/wanted.z" > "$WORK/actual" || true

    # Joined on the path rather than searched file by file: no path this repository tracks
    # contains a space, which is checked rather than hoped -- `git ls-files | grep " "` is
    # empty, and `tests/integration/composition/test_deployed_stack_probe.py` keeps it so.
    LC_ALL=C sort -k2 "$WORK/expected" > "$WORK/expected.s"
    LC_ALL=C sort -k2 "$WORK/actual" > "$WORK/actual.s"

    LC_ALL=C join -j 2 -v 1 -o 0 "$WORK/expected.s" "$WORK/actual.s" > "$WORK/missing"
    LC_ALL=C join -j 2 -o 0,1.1,2.1 "$WORK/expected.s" "$WORK/actual.s" \
        | awk '$2 != $3 { print }' > "$WORK/changed"

    missing="$(grep -c . "$WORK/missing" || true)"
    changed="$(grep -c . "$WORK/changed" || true)"
    sed 's/^/  /; s/$/  MISSING FROM THE IMAGE/' "$WORK/missing"
    awk '{ printf "  %s  DIFFERENT BYTES\n      tree  %s\n      image %s\n", $1, $2, $3 }' \
        "$WORK/changed"

    extra=0
    if [ "$extras" = yes ]; then
        # `__pycache__` is excluded and the reason is measured, not assumed: there is no
        # `.dockerignore` in this repository, so `COPY src/` carries whatever bytecode the
        # build host had lying about. 253 such files are in the alpha api image today. They
        # are build-host litter, not a claim about the source.
        docker exec "$CONTAINER" sh -c \
            "find '${container_dst%/}' -type f -not -path '*/__pycache__/*' 2>/dev/null" \
            | LC_ALL=C sort > "$WORK/present" || true
        LC_ALL=C sort "$WORK/wanted" > "$WORK/wanted.s"
        while IFS= read -r path; do
            [ -n "$path" ] || continue
            printf '  %s  IN THE IMAGE AND NOT IN THE TREE\n' "$path"
            extra=$((extra + 1))
        done < <(LC_ALL=C comm -23 "$WORK/present" "$WORK/wanted.s")
    fi

    total="$(grep -c . "$WORK/wanted")"
    if [ "$((missing + changed + extra))" -eq 0 ]; then
        printf '  %-34s %4s files, identical\n' "$host_src" "$total"
    else
        printf '  %-34s %4s files: %s missing, %s different, %s unexpected\n' \
            "$host_src" "$total" "$missing" "$changed" "$extra"
        PROBLEMS=$((PROBLEMS + missing + changed + extra))
    fi
done <<<"$MAPPINGS"

echo

# --- 3. what the running proxy reads, against the tree ------------------------------
# `B-1`. The mounts are read from the container, not from the compose file: the container is
# what serves, and it may carry overlays (`infra/acme/compose.acme.yml`, `proxy/compose.tls.yml`) this
# script's proxy comparison never names.
# Each bind-mount source must be this checkout's `infra/deploy/proxy/` -- a mount from
# anywhere else is a proxy that is not serving this tree, whatever its bytes are -- and every
# tracked file under each source is compared inside the container. `proxy/nginx.conf` is
# named rather than counted, for the reason `src/` is above: the one file this section may
# never be blind to is the configuration the proxy actually serves.
echo "-- the proxy's configuration against the tree --"
PROXY_CONTAINER="$(compose ps --quiet proxy 2>/dev/null | head -1)"
[ -n "$PROXY_CONTAINER" ] || fail "$UNANSWERABLE" \
    "no running container for the 'proxy' service of $INSTANCE." \
    "What the proxy serves was not compared."
docker inspect --format \
    '{{range .Mounts}}{{if eq .Type "bind"}}{{.Source}}{{"\t"}}{{.Destination}}{{"\n"}}{{end}}{{end}}' \
    "$PROXY_CONTAINER" > "$WORK/proxy-mounts" 2>/dev/null || fail "$UNANSWERABLE" \
    "the proxy container $PROXY_CONTAINER could not be inspected." \
    "What the proxy serves was not compared."
HERE_PHYSICAL="$(cd "$HERE" && pwd -P)"
: > "$WORK/proxy-expected"
: > "$WORK/proxy-wanted"
PROXY_PROBLEMS=0
SAW_NGINX_CONF=no
while IFS=$'\t' read -r source destination; do
    [ -n "$source" ] || continue
    case "$source" in
        "$HERE"/proxy/*) rel="${source#"$HERE"/}" ;;
        "$HERE_PHYSICAL"/proxy/*) rel="${source#"$HERE_PHYSICAL"/}" ;;
        *)
            printf '  %s  MOUNTED FROM %s, NOT FROM THIS CHECKOUT\n' "$destination" "$source"
            PROXY_PROBLEMS=$((PROXY_PROBLEMS + 1))
            continue ;;
    esac
    tree="infra/deploy/$rel"
    [ "$tree" != infra/deploy/proxy/nginx.conf ] || SAW_NGINX_CONF=yes
    tracked="$(git -C "$REPO" ls-files -- "$tree")"
    if [ -z "$tracked" ]; then
        printf '  %s  MOUNTED FROM %s, WHICH THE TREE DOES NOT TRACK\n' "$destination" "$tree"
        PROXY_PROBLEMS=$((PROXY_PROBLEMS + 1))
        continue
    fi
    while IFS= read -r file; do
        [ -n "$file" ] || continue
        [ -f "$REPO/$file" ] || fail "$UNANSWERABLE" \
            "$file is tracked but not in the working tree." \
            "The tree side of this comparison is incomplete, so nothing is concluded."
        if [ "$file" = "$tree" ]; then
            inside="$destination"
        else
            inside="${destination%/}/${file#"$tree"/}"
        fi
        printf '%s\n' "$inside" >> "$WORK/proxy-wanted"
        printf '%s  %s\n' "$(sha256sum "$REPO/$file" | cut -d' ' -f1)" "$inside" \
            >> "$WORK/proxy-expected"
    done <<<"$tracked"
done < "$WORK/proxy-mounts"
if [ "$SAW_NGINX_CONF" = no ]; then
    printf '  infra/deploy/proxy/nginx.conf  NOT MOUNTED BY THE RUNNING PROXY\n'
    PROXY_PROBLEMS=$((PROXY_PROBLEMS + 1))
fi

tr '\n' '\0' < "$WORK/proxy-wanted" > "$WORK/proxy-wanted.z"
docker exec -i "$PROXY_CONTAINER" sh -c 'xargs -0 -r sha256sum 2>/dev/null || true' \
    < "$WORK/proxy-wanted.z" > "$WORK/proxy-actual" || true
LC_ALL=C sort -k2 "$WORK/proxy-expected" > "$WORK/proxy-expected.s"
LC_ALL=C sort -k2 "$WORK/proxy-actual" > "$WORK/proxy-actual.s"
LC_ALL=C join -j 2 -v 1 -o 0 "$WORK/proxy-expected.s" "$WORK/proxy-actual.s" \
    > "$WORK/proxy-missing"
LC_ALL=C join -j 2 -o 0,1.1,2.1 "$WORK/proxy-expected.s" "$WORK/proxy-actual.s" \
    | awk '$2 != $3 { print }' > "$WORK/proxy-changed"
sed 's/^/  /; s/$/  MISSING FROM THE PROXY/' "$WORK/proxy-missing"
awk '{ printf "  %s  DIFFERENT BYTES\n      tree  %s\n      proxy %s\n", $1, $2, $3 }' \
    "$WORK/proxy-changed"
PROXY_PROBLEMS=$((PROXY_PROBLEMS + $(grep -c . "$WORK/proxy-missing" || true) \
    + $(grep -c . "$WORK/proxy-changed" || true)))
proxy_total="$(grep -c . "$WORK/proxy-wanted" || true)"
if [ "$PROXY_PROBLEMS" -eq 0 ]; then
    printf '  %-34s %4s files, identical\n' "infra/deploy/proxy/" "$proxy_total"
else
    printf '  %-34s %4s files compared, %s disagreement(s)\n' \
        "infra/deploy/proxy/" "$proxy_total" "$PROXY_PROBLEMS"
fi

echo
if [ "$PROBLEMS" -ne 0 ]; then
    if [ "$PROXY_PROBLEMS" -ne 0 ]; then
        PROXY_NOTE="The proxy's configuration disagrees too: $PROXY_PROBLEMS file(s), listed above."
    else
        PROXY_NOTE="The proxy's configuration is this tree's."
    fi
    fail "$DRIFT" "the deployed stack is NOT this tree -- $PROBLEMS file(s) disagree." \
        "Rebuild it, and reload the proxy afterwards:" \
        "    docker compose --env-file $ENV_FILE -f $COMPOSE_FILE up -d --build" \
        "    infra/deploy/reload-proxy.sh" \
        "$PROXY_NOTE" \
        "Until then, no claim about this stack is a claim about $HEAD_SHA."
fi
if [ "$PROXY_PROBLEMS" -ne 0 ]; then
    fail "$DRIFT" \
        "the running proxy is NOT serving this tree's configuration -- $PROXY_PROBLEMS file(s) disagree." \
        "A single-file bind mount keeps the inode it was started with, and a checkout replaces" \
        "the file with a new one, so neither nginx -t nor nginx -s reload inside the container" \
        "reads it. reload-proxy.sh restarts the proxy when a mounted file changed:" \
        "    infra/deploy/reload-proxy.sh" \
        "A proxy mounted from another checkout has to be recreated from this one, with the" \
        "same -f files it was created with (add infra/acme/compose.acme.yml if ALPHA_CERT_NAME is set, and proxy/compose.tls.yml if 443 is published):" \
        "    docker compose --env-file $ENV_FILE -f $COMPOSE_FILE up -d --force-recreate proxy" \
        "Until then, no claim about this stack is a claim about $HEAD_SHA."
fi
# --- 4. the certificate the proxy serves (`PROD-01-TLS-ACME-01`, `ADR-0021` rows 2 and 5) -----------
# Only on a stack that terminates TLS itself (`ALPHA_CERT_NAME` set); without a name this section does not
# exist and the script is what it was. The question is asked of the proxy's own TLS listener, on the compose
# network, by a one-off container of the ACME image (it has `openssl` and the CA bundle; the host promises
# neither -- `DEPLOYMENT_RUNBOOK.md` section 1), so what is judged is what a client would be served, whether
# or not port 443 is published yet. Judged, in the script's order of importance:
#
#   * a certificate is served at all (a deploy is not successful while the name has none);
#   * it is the right KIND: a staging certificate on a production name is a failure, and the default for
#     `ALPHA_ACME_STAGING` is `yes`, so a host that lost its setting is caught here and not by a customer;
#   * it chains to the CA bundle and names the host (production only);
#   * it has at least 14 days left. The 14 is the architect's number (`ADR-0021` row 5); renewal starts at 30,
#     so a certificate this close is a renewal that has been failing for two weeks.
#
# `--acme-rehearsal` is the one explicit way to accept a STAGING certificate: the staging rehearsal of the
# runbook is a deploy that is meant to serve one, and that run states it. Everything else about the check is
# unchanged by it, and a production certificate is a failure under it.
CERT_NAME="$(configured ALPHA_CERT_NAME)"
if [ -n "$CERT_NAME" ]; then
    echo "-- the certificate the proxy serves --"
    LISTENERS_LIB="$HERE/lib/proxy-listeners.sh"
    [ -r "$LISTENERS_LIB" ] || fail "$UNANSWERABLE" "$LISTENERS_LIB is missing, so ALPHA_CERT_NAME cannot be judged."
    # shellcheck source=lib/proxy-listeners.sh
    . "$LISTENERS_LIB"
    if ! NAME_WHY="$(listeners_name_problem "$CERT_NAME")"; then
        fail "$UNANSWERABLE" "ALPHA_CERT_NAME '$CERT_NAME' in $ENV_FILE is not a usable name: $NAME_WHY."
    fi
    CERT_STAGING="$(configured ALPHA_ACME_STAGING)"
    [ -n "$CERT_STAGING" ] || CERT_STAGING=yes
    case "$CERT_STAGING" in
        yes|no) ;;
        *) fail "$UNANSWERABLE" "ALPHA_ACME_STAGING in $ENV_FILE is '$CERT_STAGING', which is neither yes nor no." ;;
    esac
    # >>> step: staging-certificate-is-a-failure
    if [ "$CERT_STAGING" = yes ] && [ "$REHEARSAL" = no ]; then
        fail "$CERTIFICATE" "ALPHA_ACME_STAGING is yes in $ENV_FILE: this stack is set to the authority's TEST endpoint." \
            "A staging certificate is trusted by no browser, so this deployment is not one a user can use." \
            "For production set ALPHA_ACME_STAGING=no and deploy. For the rehearsal of the runbook, say so:" \
            "    infra/deploy/verify-deployed.sh --env-file $ENV_FILE --acme-rehearsal"
    fi
    # <<< step: staging-certificate-is-a-failure
    CERT_MODE=production
    [ "$CERT_STAGING" = no ] || CERT_MODE=staging
    [ "$REHEARSAL" = no ] || [ "$CERT_STAGING" = yes ] || fail "$CERTIFICATE" \
        "--acme-rehearsal was given and ALPHA_ACME_STAGING is no: a rehearsal expects the TEST endpoint."
    CERT_ARGS=(--env-file "$ENV_FILE" --file "$COMPOSE_FILE")
    while IFS= read -r overlay; do
        [ -z "$overlay" ] || CERT_ARGS+=(--file "$overlay")
    done < <(listeners_overlay_files "$HERE" "$CERT_NAME" no no)
    CERT_STATUS=0
    CERT_OUTPUT="$(docker compose "${CERT_ARGS[@]}" run --rm --no-deps -T \
        --entrypoint /usr/local/bin/check-served.sh acme "$CERT_NAME" proxy:8443 14 "$CERT_MODE" \
        2>"$WORK/cert-stderr")" || CERT_STATUS=$?
    printf '%s\n' "$CERT_OUTPUT" | sed 's/^/  /'
    case "$CERT_STATUS" in
        0) ;;
        10|11|12|13)
            fail "$CERTIFICATE" "the certificate this stack serves for $CERT_NAME is not acceptable (check-served.sh exit $CERT_STATUS)." \
                "What it found is above. The images and the proxy's configuration are this tree's;" \
                "the public name is not ready to be used." ;;
        *)
            fail "$UNANSWERABLE" "the certificate could not be asked (exit $CERT_STATUS)." \
                "$(sed 's/^/  /' "$WORK/cert-stderr" | head -5)" \
                "Is the acme service built (deploy.sh) and the proxy up? Nothing is claimed about the certificate." ;;
    esac
    echo

    # --- 4b. what the proxy answers on that name (`HARDEN-01`, `EXPOSURE-REVIEW-02` `F-17`) --------------------
    # The certificate says who answers; this says what the answer promises. `E-2` found HSTS, the `Secure` flag
    # of the session cookie and the four security headers only in the CONFIGURATION, and the static tests read
    # the configuration, not the answer: a proxy that lost a header, or a web tier that stopped believing
    # `X-Forwarded-Proto`, would have stayed green. So one request is sent to the proxy's own TLS listener, with
    # the name as SNI and as `Host`, by the same one-off container of the ACME image (it has `openssl`; the host
    # promises none), and the RAW HEADERS that come back are judged here:
    #
    #   * `Strict-Transport-Security` with `max-age` of at least 31536000 and neither `includeSubDomains` nor
    #     `preload` (`ADR-0021`: a year, and no promise about other names);
    #   * the four security headers of `C-18`, with their values;
    #   * `Server` without a version (`F-16`: `server_tokens off`);
    #   * the session cookie with the `Secure` attribute.
    #
    # THE COOKIE needs no credential. `GET /bff/v1/me` with a session cookie that is well-formed and names no
    # session is answered by the web tier with `401` and a CLEARED `am_session` cookie, and that cookie takes its
    # `Secure` attribute from the same decision (`requestIsSecure`, from `X-Forwarded-Proto`) as the cookie a
    # sign-in sets -- so this observes the live behaviour of the whole chain (proxy header, web tier) without
    # signing anybody in and without a password in this script. If the answer is not that (the web tier is down,
    # the route moved) there is no cookie to judge and the check says so with exit 4: "no finding" must not be
    # reported for a property that was not observed.
    echo "-- the headers and the session cookie the proxy serves --"
    HEADERS_PROBE="$(cat <<'PROBE'
name=$1; target=$2; session=$3
printf 'GET /bff/v1/me HTTP/1.1\r\nHost: %s\r\nCookie: am_session=%s\r\nAccept: application/json\r\nConnection: close\r\n\r\n' "$name" "$session" \
    | timeout 20 openssl s_client -connect "$target" -servername "$name" -quiet -ign_eof 2>/dev/null
PROBE
)"
    # Sixty-four hex digits are the shape of a session identifier (`SESSION_ID_PATTERN`); all zeros names none.
    STALE_SESSION="$(printf '0%.0s' $(seq 1 64))"
    HEADERS_STATUS=0
    HEADERS_RAW="$(docker compose "${CERT_ARGS[@]}" run --rm --no-deps -T \
        --entrypoint sh acme -c "$HEADERS_PROBE" served-headers-probe "$CERT_NAME" proxy:8443 "$STALE_SESSION" \
        2>"$WORK/headers-stderr" </dev/null)" || HEADERS_STATUS=$?
    # The header block only: CRs removed, everything from the first blank line on (the body) dropped.
    printf '%s\n' "$HEADERS_RAW" | tr -d '\r' | awk 'NR == 1 { print; next } /^$/ { exit } { print }' \
        > "$WORK/served-headers"
    HEADERS_FIRST="$(head -n 1 "$WORK/served-headers")"
    if ! [[ "$HEADERS_FIRST" =~ ^HTTP/[0-9.]+\ [0-9]{3} ]]; then
        fail "$UNANSWERABLE" "the proxy's answer on $CERT_NAME could not be read (probe exit $HEADERS_STATUS; first line: '${HEADERS_FIRST}')." \
            "$(sed 's/^/  /' "$WORK/headers-stderr" | head -5)" \
            "Is the proxy up and serving TLS? Nothing is claimed about its headers or its cookie."
    fi
    # The values of every header of one name, case-insensitively, one per line.
    served_header() {
        awk -v want="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" '
            NR > 1 {
                i = index($0, ":"); if (i == 0) next
                if (tolower(substr($0, 1, i - 1)) != want) next
                v = substr($0, i + 1); sub(/^[ \t]+/, "", v); sub(/[ \t]+$/, "", v); print v
            }' "$WORK/served-headers"
    }
    HEADER_PROBLEMS=()
    # >>> step: served-hsts
    HSTS="$(served_header Strict-Transport-Security)"
    HSTS_AGE="$(printf '%s' "$HSTS" | sed -n 's/.*[Mm][Aa][Xx]-[Aa][Gg][Ee]=\([0-9][0-9]*\).*/\1/p' | head -n 1)"
    if [ -z "$HSTS" ]; then
        HEADER_PROBLEMS+=("Strict-Transport-Security is absent: a browser that met this name once is not held to HTTPS.")
    elif [ -z "$HSTS_AGE" ] || [ "$HSTS_AGE" -lt 31536000 ]; then
        HEADER_PROBLEMS+=("Strict-Transport-Security is '$HSTS': max-age must be at least 31536000 (a year).")
    elif printf '%s' "$HSTS" | grep -Eiq 'includeSubDomains|preload'; then
        HEADER_PROBLEMS+=("Strict-Transport-Security is '$HSTS': neither includeSubDomains nor preload is promised for this name (ADR-0021).")
    fi
    # <<< step: served-hsts
    # >>> step: served-security-headers
    while IFS='|' read -r want_name want_value; do
        got="$(served_header "$want_name")"
        if [ -z "$got" ]; then
            HEADER_PROBLEMS+=("$want_name is absent (expected '$want_value').")
        elif [ "$got" != "$want_value" ]; then
            HEADER_PROBLEMS+=("$want_name is '$got' (expected '$want_value').")
        fi
    done <<'WANTED'
X-Content-Type-Options|nosniff
X-Frame-Options|DENY
Content-Security-Policy|frame-ancestors 'none'
Referrer-Policy|same-origin
WANTED
    # <<< step: served-security-headers
    # >>> step: served-no-version
    SERVER_BANNER="$(served_header Server | head -n 1)"
    if printf '%s' "$SERVER_BANNER" | grep -q '[0-9]'; then
        HEADER_PROBLEMS+=("Server is '$SERVER_BANNER': the banner names a version (server_tokens off is not in force).")
    fi
    # <<< step: served-no-version
    # >>> step: served-secure-cookie
    SESSION_COOKIES="$(served_header Set-Cookie | grep -i '^am_session=' || true)"
    if [ -z "$SESSION_COOKIES" ]; then
        fail "$UNANSWERABLE" "the answer on $CERT_NAME carried no am_session cookie to judge ($HEADERS_FIRST)." \
            "The probe expects 401 and a cleared session cookie for a session that does not exist; whether the" \
            "cookie is Secure is NOT known, so nothing is claimed about it."
    fi
    while IFS= read -r cookie; do
        [ -n "$cookie" ] || continue
        if ! printf '%s' "$cookie" | grep -Eiq ';[[:space:]]*Secure[[:space:]]*(;|$)'; then
            HEADER_PROBLEMS+=("the session cookie is not Secure ('$cookie'): the browser would send it over plain HTTP.")
        fi
    done <<<"$SESSION_COOKIES"
    # <<< step: served-secure-cookie
    if [ "${#HEADER_PROBLEMS[@]}" -ne 0 ]; then
        printf '  %s\n' "$HEADERS_FIRST"
        fail "$HEADERS" "the answer served on $CERT_NAME lacks what the proxy's configuration promises (${#HEADER_PROBLEMS[@]} finding(s))." \
            "${HEADER_PROBLEMS[@]}" \
            "The images and the certificate are this tree's; the proxy is not serving this tree's configuration, or the" \
            "web tier is not told the transport (X-Forwarded-Proto). Run infra/deploy/reload-proxy.sh, then this check again."
    fi
    printf '  %s: HSTS max-age=%s, the four security headers, no version in Server, the session cookie is Secure.\n' \
        "$HEADERS_FIRST" "$HSTS_AGE"
    echo
fi

# --- 5. the published default credential (`PROD-02`, `R-146i`, `R-146s`, `R-146z`; ADR-0023 section 3) -----------
# A deployment is not successful while the PUBLISHED seeded pair (`admin` / `password`) is valid. Asked of the
# database by `python -m auditmanager.access.check --gate` in the api image (the host has no python), after the
# stack has been shown to be this tree, so the bytes that answer are the bytes of this checkout. A temporary
# password an administrator issued is a WARNING line of that output and not a failure (`R-146z`). `unknown` (the
# check could not run, or printed neither sentinel) is exit 4: it is not an answer, and "no finding" is an answer.
echo "-- the published default credential is not valid --"
LISTENERS_LIB="$HERE/lib/proxy-listeners.sh"
[ -r "$LISTENERS_LIB" ] || fail "$UNANSWERABLE" "$LISTENERS_LIB is missing, so the credential gate cannot be asked."
# shellcheck source=lib/proxy-listeners.sh
. "$LISTENERS_LIB"
# >>> step: default-credential-gate
listeners_gate_run compose
printf '%s\n' "$LISTENERS_GATE_OUTPUT" | sed 's/^/  /'
case "$LISTENERS_GATE_VERDICT" in
    clean) ;;
    finding)
        if listeners_https_published compose; then
            PUBLISHED_NOTE="PUBLIC PORT 443 IS PUBLISHED while the pair is valid: withdraw it now (deploy.sh does, on its next run)."
        else
            PUBLISHED_NOTE="Public port 443 is not published, as it must not be while the pair is valid."
        fi
        fail "$CREDENTIAL" "the published admin/password pair is valid: $(listeners_gate_logins "$LISTENERS_GATE_OUTPUT" | paste -sd, -) still accepts the published password." \
            "$PUBLISHED_NOTE" \
            "The deployment is not successful (R-146i). Sign in through an SSH tunnel to the loopback port," \
            "change the password, and deploy again." ;;
    *)
        fail "$UNANSWERABLE" "the credential gate could not be answered (access.check --gate exited $LISTENERS_GATE_STATUS and printed neither sentinel)." \
            "What it printed is above. Whether the published pair is valid is NOT known, so nothing is claimed." ;;
esac
# <<< step: default-credential-gate
echo "  no account accepts the published password; temporary passwords, if any, are warned about above."
echo

echo "verify-deployed.sh: the deployed stack IS this tree ($HEAD_SHA$DIRTY)."
