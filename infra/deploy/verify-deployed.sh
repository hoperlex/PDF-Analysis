#!/usr/bin/env bash
# `D-27` -- one command that answers "is the stack in front of me this tree?"
#
#   infra/deploy/verify-deployed.sh [--env-file <path>] [--repo <path>]
#
# Exit 0: the deployed stack is this working tree. Exit 6: it is not. Exit 4: the question
# could not be answered. **Both failures are failures.** The row this closes is not "the
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

while [ "$#" -gt 0 ]; do
    case "$1" in
        --env-file) ENV_FILE="${2:-}"; shift 2 ;;
        --repo) REPO="${2:-}"; shift 2 ;;
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
# what serves, and it may carry an overlay (`proxy/compose.tls.yml`) this script never names.
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
        "same -f files it was created with (add proxy/compose.tls.yml if TLS is on):" \
        "    docker compose --env-file $ENV_FILE -f $COMPOSE_FILE up -d --force-recreate proxy" \
        "Until then, no claim about this stack is a claim about $HEAD_SHA."
fi
echo "verify-deployed.sh: the deployed stack IS this tree ($HEAD_SHA$DIRTY)."
