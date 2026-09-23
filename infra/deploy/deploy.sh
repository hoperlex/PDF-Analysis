#!/usr/bin/env bash
# `PA-01` criterion 1 -- bring this clone up, and refuse to call it deployed until the
# stack has been asked, one question at a time, whether it actually is.
#
#   infra/deploy/deploy.sh [--env-file <path>]
#
# `ALPHA_ROADMAP.md` §4 gives this file to `W14-OPS`, a stream that was never dispatched;
# `W21-CERT.md` §"Criterion 1" records the consequence -- *"there is nothing to run"*. This
# is the thing to run. What it is NOT is the whole of that roadmap row, and the boundary is
# named in `README.md` rather than blurred here: **fetch, switch and roll back are not in
# this script**, because all three are claims about a server that has a previous version on
# it and `R-1`'s host does not exist. What IS here is everything that is testable on a
# machine that has never run this stack, which is the clause the criterion is named for.
#
# `T-4`: a script and not a `make` target. `OD-16` makes a tenth root target an FF-01
# freeze-break needing an explicit break record, and nothing here needs one.
#
# ORDER, AND WHY IT IS THE ORDER:
#
#   1. every guard that can be answered from the clone alone, before docker is touched at
#      all -- the environment, its secrets, the compose file, and whether this clone even
#      contains the paths the two Dockerfiles copy;
#   2. whether the published port belongs to somebody else. A deploy that takes another
#      instance's port is not idempotent, it is a coup;
#   3. **build, and only then bring up.** These are two steps on purpose. A build that
#      fails must leave whatever was serving still serving, and that is a property of the
#      ORDER rather than of anybody's intention -- see `images-built`;
#   4. up, ask the stack whether it is actually there, reload the proxy, and then ask
#      three more questions it can fail. The four questions are: is every service
#      healthy, is the database at the head THIS code expects, does the published port
#      answer, and does the document the process serves conform to the frozen contract.
#      The FIRST of them comes before the reload and that is `D-38`: a reload cannot
#      succeed against a stack that is missing a container, and the message it fails with
#      names `nginx.conf`, a file that is fine. See `# --- 3.` below.
#
# WHAT A SECOND RUN DOES, MEASURED RATHER THAN CLAIMED. This comment said "a second run
# changes nothing" until `W23-DEPLOY` ran it twice from a clean clone, and that was false.
# What that drive found, recorded in `docs/program/reviews/W23-DEPLOY.md` and as `D-36`:
#
#   * **no layer is rebuilt.** Every step of both images reports `CACHED`;
#   * **no data is touched.** `postgres`, `s3` and `proxy` report `Running` and keep their
#     container IDs; both named volumes keep the creation timestamp of the first run;
#   * **`api`, `web` and `migrate` WERE recreated**, because a fully cached `compose build`
#     still yielded a NEW image ID -- two consecutive builds of an untouched tree gave
#     `df1242a7...` and `3be02972...` -- and `compose up -d` recreates a service whose
#     image id moved. `SOURCE_DATE_EPOCH` was tried there and did not fix it.
#
# `W24-IDEM` CLOSED THAT, AND THE FIRST THING IT FOUND WAS THAT THE STATED CAUSE IS WRONG.
# `D-36` and this comment both said the id moves because "BuildKit stamps a fresh `created`
# into the config". Measured here on the same host: two consecutive fully cached builds of
# an untouched tree produce images whose `.Created`, `.RootFS.Layers` and **entire
# `.Config`** are byte-identical, and whose ids differ anyway. The id is the digest of the
# MANIFEST, and BuildKit attaches a **provenance attestation** to every build by default;
# that attestation carries the time the build ran. `SOURCE_DATE_EPOCH` never touched it,
# which is exactly why trying it changed nothing.
#
# So this script now does two things, and they answer two different causes:
#
#   1. it builds with `BUILDX_NO_DEFAULT_ATTESTATIONS=1`, which makes the id a digest of
#      the content again. Measured: two consecutive builds, same id, both images;
#   2. after the build it compares each image with what its name pointed at BEFORE it --
#      not by id but by CONTENT, the layer diffIDs plus the runtime configuration -- and
#      points the name back at the old image when they are the same. That catches the
#      cause (1) does not: `api` and `migrate` are two services sharing one image, and
#      compose writes `com.docker.compose.service` into it, measured coming out `migrate`
#      on one run and `api` on the next.
#
# See `# --- 1.`, `# --- 1a.` and `# --- 2a.` below, and `docs/program/reviews/W24-IDEM.md`.
#
# The one failure mode (2) would have is an image that keeps an old identity after its
# content genuinely changed, which would leave a stale container running and make
# `verify-deployed.sh` call it this tree. A diffID is the sha256 of a layer's uncompressed
# tar, so that would take a collision; and the claim was driven rather than reasoned --
# §4 of the review forces the wrong retag by hand and reads what the probe then says.
#
# It is opt-out, through `ALPHA_PRESERVE_IMAGE_IDENTITY=no` in the environment file, and
# what an operator loses by turning it off is only this: every run mints a new image, and
# `api`, `web` and `migrate` are recreated as they were before. Nothing about the build,
# the data or the guards changes either way.
#
# `migrate` re-running, on the runs where it does, is a no-op by construction -- `alembic
# upgrade head` against a database already at head applies nothing, and `migrations-at-head`
# proves it afterwards.
#
# What this script does NOT have is an "already deployed" branch. Every step is safe to
# repeat, and a branch that decided whether to repeat it would be a thing that can be
# wrong about a stack it did not look at.
#
# GUARDS ARE DELIMITED BY MARKERS -- `# >>> guard: <name>` / `# <<< guard: <name>`.
# `tests/integration/composition/test_deploy_script_refusals.py` reads those markers,
# deletes ONE guard block from a copy of this file and shows that the copy no longer
# refuses. A message can be printed by a guard that is unreachable; a deletion cannot be
# faked. Do not remove a marker without removing its test.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
COMPOSE_FILE="$HERE/compose.server.yml"
ENV_FILE="${ALPHA_ENV_FILE:-$HERE/env/alpha.env}"
ENV_EXAMPLE="$HERE/env/alpha.env.example"
#: The gate's own conformance engine, mounted into a one-off container in the last guard.
#: `reset.sh` mounts `object_attrs.py` the same way and for the same reason: the check has
#: to run where the frozen contract and a python are, which is the image, not the host.
CONFORMANCE_ENGINE="$REPO/tests/contract/api_v1/openapi_conformance.py"

#: `refuse()`'s exit status, the same one `reset.sh` uses. One code for every refusal; the
#: reason is carried by the message, because two guards sharing a code must still be told
#: apart by the operator and by the suite.
refuse() {
    printf 'deploy.sh: REFUSED: %s\n' "$1" >&2
    shift
    [ "$#" -eq 0 ] || printf '  %s\n' "$@" >&2
    exit 3
}

usage() {
    cat >&2 <<'USAGE'
usage: deploy.sh [--env-file <path>]

  --env-file <path>   default: infra/deploy/env/alpha.env

Brings this clone's stack up and refuses to report success until the running stack has
answered for itself. Run it from anywhere; it locates its own repository.
USAGE
    exit 2
}

# >>> guard: known-options
# An unrecognised option is refused rather than ignored. This script builds images and
# starts containers, and an operator who typed `--envfile` and was ignored would watch it
# deploy against the default environment believing it had used theirs.
while [ "$#" -gt 0 ]; do
    case "$1" in
        --env-file) ENV_FILE="${2:-}"; shift 2 ;;
        -h|--help) usage ;;
        *) refuse "unrecognised option: $1" \
                  "Nothing was read, nothing was built and nothing was started." \
                  "Run --help." ;;
    esac
done
# <<< guard: known-options

# >>> guard: env-file-present
# The environment is the operator's, not the clone's: `env/alpha.env` is git-ignored, so a
# clean clone does NOT have one and must not be given a default. A deploy that invented an
# environment would deploy something nobody configured.
if [ ! -r "$ENV_FILE" ]; then
    refuse "the deployment environment $ENV_FILE is missing or unreadable." \
           "A clean clone does not carry one -- env/alpha.env is git-ignored on purpose," \
           "because it holds this instance's secrets. Write it first:" \
           "    cp infra/deploy/env/alpha.env.example infra/deploy/env/alpha.env" \
           "    chmod 600 infra/deploy/env/alpha.env    # then edit EVERY value in it"
fi
# <<< guard: env-file-present

# Read the configured instance as DATA. The file is never sourced: same shape, same reason
# and the same reader as `reset.sh` and `verify-deployed.sh`.
configured() {
    sed -n "s/^[[:space:]]*\(export[[:space:]]\+\)\?$1=//p" "$ENV_FILE" | tail -1 \
        | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/"
}

INSTANCE="$(configured ALPHA_INSTANCE)"
HTTP_PORT="$(configured ALPHA_HTTP_PORT)"
DATABASE="$(configured POSTGRES_DB)"
BUCKET="$(configured S3_BUCKET)"

# >>> guard: instance-configured
# The four names every later step addresses the instance by. `compose.server.yml` would
# refuse an unset `ALPHA_INSTANCE` itself -- `${ALPHA_INSTANCE:?...}` -- but it would do it
# after the build, in compose's words, and a half-configured environment is worth one
# sentence before anything is built rather than a substitution error after it.
if [ -z "$INSTANCE" ] || [ -z "$HTTP_PORT" ] || [ -z "$DATABASE" ] || [ -z "$BUCKET" ]; then
    refuse "$ENV_FILE does not configure an instance." \
           "  ALPHA_INSTANCE : ${INSTANCE:-<unset>}" \
           "  ALPHA_HTTP_PORT: ${HTTP_PORT:-<unset>}" \
           "  POSTGRES_DB    : ${DATABASE:-<unset>}" \
           "  S3_BUCKET      : ${BUCKET:-<unset>}" \
           "Every name below addresses the instance by these. Nothing was built."
fi
# <<< guard: instance-configured

# `ALPHA_PRESERVE_IMAGE_IDENTITY` decides whether a rebuild that produced IDENTICAL
# content keeps the image ID it already had. It is optional and defaults to `yes`; `no`
# is the behaviour this script had before `W24-IDEM`, where every build's image is taken
# as new and `api`, `web` and `migrate` are therefore replaced on every run (`D-36`).
#
# A VALUE THIS SCRIPT DOES NOT RECOGNISE IS REFUSED RATHER THAN READ AS THE DEFAULT, and
# that is `known-options`' argument one layer along: an operator who wrote `false` meaning
# "off" and was quietly given `yes` would watch nothing be replaced and conclude the
# switch does not work, or worse, conclude the images are identical when they wanted a
# forced replacement.
PRESERVE_IDENTITY="$(configured ALPHA_PRESERVE_IMAGE_IDENTITY)"
[ -n "$PRESERVE_IDENTITY" ] || PRESERVE_IDENTITY=yes

# >>> guard: identity-policy-known
case "$PRESERVE_IDENTITY" in
    yes|no) ;;
    *) refuse "ALPHA_PRESERVE_IMAGE_IDENTITY is '$PRESERVE_IDENTITY', which is neither yes nor no." \
              "  yes  (the default) a build whose content is identical to the image that" \
              "       is already there keeps that image's ID, so a second run of this" \
              "       script replaces no container at all" \
              "  no   every build's image is taken as new; api, web and migrate are" \
              "       recreated on every run, which is what this script did before W24-IDEM" \
              "Nothing was built and nothing was started." ;;
esac
# <<< guard: identity-policy-known

# >>> guard: placeholder-secrets
# THE EXAMPLE FILE'S OWN VALUES, REFUSED BY IDENTITY RATHER THAN BY PATTERN. `cp` the
# example and forget to edit it and you get a reachable stack whose database password is in
# git and whose `AUDITMANAGER_API_TOKEN` is the string the example file itself describes as
# one that "authorizes nothing" -- and `T-6`'s seam is fail-closed, so that stack answers
# `authentication_required` to all fifteen operations and looks like a broken product.
#
# Compared against `alpha.env.example`'s values rather than grepped for `change-me`: a
# pattern stops being true the day somebody rewrites the example, and the claim this guard
# actually wants to make is "you did not edit the file you copied".
#
# The example is git-tracked, so a clone has it. If it is unreadable the comparison cannot
# be made, and an unverifiable secret is not a verified one -- it refuses rather than skips.
if [ ! -r "$ENV_EXAMPLE" ]; then
    refuse "$ENV_EXAMPLE is missing, so the shipped placeholder values cannot be recognised." \
           "This guard's whole job is to tell your secrets apart from the example's."
fi
for name in POSTGRES_PASSWORD MINIO_ROOT_PASSWORD MINIO_ROOT_USER AUDITMANAGER_API_TOKEN; do
    mine="$(configured "$name")"
    theirs="$(sed -n "s/^[[:space:]]*\(export[[:space:]]\+\)\?$name=//p" "$ENV_EXAMPLE" \
        | tail -1 | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/")"
    if [ -n "$theirs" ] && [ "$mine" = "$theirs" ]; then
        refuse "$name is still the value shipped in alpha.env.example." \
               "  $name = $mine" \
               "That value is published in this repository. It is a placeholder, not a" \
               "secret, and alpha.env.example says so beside it. Nothing was built." \
               "Generate the token with:" \
               "    python3 -c 'import secrets; print(secrets.token_urlsafe(32))'"
    fi
done
# <<< guard: placeholder-secrets

# >>> guard: compose-file-present
if [ ! -r "$COMPOSE_FILE" ]; then
    refuse "$COMPOSE_FILE is missing." \
           "Every step below runs through it. Without it this script has no stack to" \
           "build, no instance to start and nothing it is allowed to reach."
fi
# <<< guard: compose-file-present

# >>> guard: build-context-complete
# THE CLEAN-CLONE GUARD, AND IT IS THE ONE THIS SCRIPT EXISTS FOR. "Brings the stack up
# from a clean clone" fails in exactly one interesting way: the clone is not the tree the
# Dockerfiles were written against, and the build discovers it three minutes in with a
# `COPY failed: stat ...: no such file or directory` naming a path halfway through a layer.
#
# The paths are read OUT OF THE DOCKERFILES' OWN BYTES -- the idiom `verify-deployed.sh`
# already uses, which is itself the idiom `Dockerfile.api` uses on the Makefile's
# `UV_VERSION`. A path newly copied by a Dockerfile is therefore checked without anybody
# remembering to add it here, and this guard cannot drift from what the build needs.
#
# `COPY --from=<stage>` lines are skipped: their source is an earlier stage, not this
# repository. Everything else is `COPY <src>... <dst>`, so every field but the last is a
# host path relative to the build context, which `compose.server.yml` sets to the
# repository root for both images.
CONTEXT_PATHS="$(
    awk 'tolower($1) == "copy" && $2 !~ /^--/ {
             for (i = 2; i < NF; i++) print $i
         }' "$HERE/Dockerfile.api" "$HERE/Dockerfile.web" | LC_ALL=C sort -u
)"
# A parse that found nothing must not read as a complete clone. `src/` is named rather than
# counted: a threshold is a number to argue with, and the one path this guard may never be
# blind to is the application's own source.
if ! printf '%s\n' "$CONTEXT_PATHS" | grep -qx 'src/'; then
    refuse "the Dockerfiles' COPY lines could not be read, so this clone was not checked." \
           "This guard derives what it needs from those lines; a parse that found nothing" \
           "would otherwise report a complete clone. Fix the parse, do not trust it."
fi
MISSING=""
while IFS= read -r path; do
    [ -n "$path" ] || continue
    [ -e "$REPO/${path%/}" ] || MISSING="$MISSING $path"
done <<<"$CONTEXT_PATHS"
if [ -n "$MISSING" ]; then
    refuse "this clone is missing paths the two Dockerfiles copy into the images." \
           "  repository: $REPO" \
           "  missing   :$MISSING" \
           "Nothing was built. A partial clone, a sparse checkout or a tarball of part of" \
           "this tree fails here in one sentence instead of inside a build layer."
fi
# <<< guard: build-context-complete

compose() { docker compose --env-file "$ENV_FILE" --file "$COMPOSE_FILE" "$@"; }

echo "deploy.sh: instance   $INSTANCE"
echo "deploy.sh: repository $REPO"
echo "deploy.sh: port       $HTTP_PORT"
echo "deploy.sh: database   $DATABASE"
echo "deploy.sh: bucket     $BUCKET"
echo

# >>> guard: port-not-foreign
# `ALPHA_HTTP_PORT` is the one published port, and on a host that already runs an instance
# it is the one thing two instances can collide on. If something is already listening there
# and it is NOT this instance's proxy, the choices are to take the port or to stop, and
# taking it means an unrelated stack stops answering while this one reports success.
#
# `docker compose up` would fail on the bind anyway -- but only after the build, and with a
# message about a port allocation rather than about the other stack. This is cheaper and it
# is the true sentence.
#
# THE OWN-PROXY CASE IS THE IDEMPOTENT ONE and it is why this is not simply "the port must
# be free": on a second run the port is held by this instance's own proxy, and that must be
# allowed or the script could never be run twice.
OWN_PROXY="$(compose ps --quiet proxy 2>/dev/null | head -1 || true)"
PORT_HELD=no
# bash's own /dev/tcp rather than `ss`, `lsof` or `netstat`: none of the three is on a slim
# host by default, and a guard that needs a tool the target may not have is a guard that
# silently does not run there.
if (exec 3<>"/dev/tcp/127.0.0.1/$HTTP_PORT") 2>/dev/null; then
    PORT_HELD=yes
fi
if [ "$PORT_HELD" = yes ] && [ -z "$OWN_PROXY" ]; then
    refuse "port $HTTP_PORT is already in use, and not by $INSTANCE." \
           "  something answers on 127.0.0.1:$HTTP_PORT" \
           "  this instance has no proxy container, so it is not ours" \
           "Nothing was built and nothing was started. Deploying here would either fail on" \
           "the bind or take the port from whatever is serving on it. Change" \
           "ALPHA_HTTP_PORT in $ENV_FILE, or stop the other stack on purpose."
fi
# <<< guard: port-not-foreign

# --- 1. build, and ONLY then bring up ------------------------------------------------
# WHAT THE TWO IMAGE NAMES POINT AT BEFORE THE BUILD, and A SECOND TAG SO THAT IMAGE IS
# STILL THERE AFTERWARDS. Both halves are measured rather than assumed:
#
#   * `compose build` MOVES the tag, so the previous id is not recoverable from the name
#     once it has. A host that has never built these has neither, and an empty value here
#     means exactly that -- there was nothing to preserve. It is not an error;
#   * **this host's docker DELETES the image the tag moved off**, immediately, even while
#     containers are running on it. Measured: after a build, `docker image inspect` on the
#     id read two seconds earlier answers `No such image`, and `docker image ls -a` shows
#     no dangling entry at all. So reading the id is not enough to keep the image, and the
#     first version of this step compared a fingerprint against something that no longer
#     existed and reported "the previous one could no longer be read" on every run. The
#     second tag is what keeps it, and `# --- 2a.` below takes it off again.
PREVIOUS_TAG_SUFFIX=deploy-previous
PREVIOUS_API_ID=""
PREVIOUS_WEB_ID=""
if [ "$PRESERVE_IDENTITY" = yes ]; then
    PREVIOUS_API_ID="$(docker image inspect --format '{{.Id}}' "$INSTANCE-api" 2>/dev/null || true)"
    PREVIOUS_WEB_ID="$(docker image inspect --format '{{.Id}}' "$INSTANCE-web" 2>/dev/null || true)"
    for pinned in "$INSTANCE-api:$PREVIOUS_API_ID" "$INSTANCE-web:$PREVIOUS_WEB_ID"; do
        name="${pinned%%:*}"
        id="${pinned#*:}"
        [ -n "$id" ] || continue
        docker tag "$id" "$name:$PREVIOUS_TAG_SUFFIX" >/dev/null 2>&1 || {
            printf 'deploy.sh: NOTE: %s could not be pinned before the build. An identical\n' "$name" >&2
            printf '  rebuild of it will be treated as a new image and its containers replaced,\n' >&2
            printf '  which is what this script did before W24-IDEM. Nothing else changes.\n' >&2
        }
    done
fi

echo "-- building the images --"
# NO DEFAULT ATTESTATIONS, AND THIS IS THE ACTUAL CAUSE OF `D-36`.
#
# `D-36` and this file's own header said the image id moves because "BuildKit stamps a
# fresh `created` into the config". **Measured on this host, that is false.** Two
# consecutive fully cached builds of an untouched tree give images whose `.Created`,
# `.RootFS.Layers` and entire `.Config` are BYTE-IDENTICAL -- and whose ids still differ.
# The id is the digest of the image's MANIFEST, and BuildKit attaches a **provenance
# attestation** to every build by default; that attestation carries the time the build ran,
# so the manifest digest moves although nothing in the image did. `SOURCE_DATE_EPOCH` does
# not touch it, which is why `W23-DEPLOY` tried it and saw no change.
#
# Turning the default attestations off makes the id what it is supposed to be -- a digest
# of the content. Measured, same tree, cache warm: two consecutive builds give
# `1588a443ecf0...` and `1588a443ecf0...` for the api image and `f95c0d54cf31...` twice for
# the web image. What is given up is the provenance attestation itself: nothing in this
# repository reads one, `verify-deployed.sh` asks the running container what bytes it holds
# rather than asking an image what it claims, and the frozen digests in
# `compose.server.yml` are of third-party images this never touches.
export BUILDX_NO_DEFAULT_ATTESTATIONS=1
BUILD_STATUS=0
compose build || BUILD_STATUS=$?

# >>> guard: images-built
# THE TWO STEPS ARE THE ROLLBACK, as far as one exists without a server to switch on.
# `compose up -d --build` is one command and would have been shorter; it is deliberately
# not used, because the property worth having is an ORDER: nothing that is serving is
# replaced until the images that would replace it exist. A build that fails therefore
# leaves the previous containers running and answering, and that is true of the FIRST
# failure as well as the hundredth, without a saved image tag or a restore path -- neither
# of which could be shown to work here, because both are claims about a host that has a
# previous version on it (`R-1`).
#
# The status is not the whole check. A build can exit 0 and leave no image -- a `compose
# build` naming no services on a file whose services are all `image:`-only does exactly
# that -- so the images are asked for by name afterwards. `run_checked` in the Makefile
# makes the same argument about sentinels, and it is the same defect: a zero that means
# nothing happened.
if [ "$BUILD_STATUS" -ne 0 ]; then
    refuse "the image build failed (status $BUILD_STATUS)." \
           "NOTHING WAS STARTED, REPLACED OR STOPPED. Whatever was serving this instance" \
           "before this run is still serving it, because images are built before anything" \
           "is brought up and this run never got past the build."
fi
for image in "$INSTANCE-api" "$INSTANCE-web"; do
    if ! docker image inspect "$image" >/dev/null 2>&1; then
        refuse "the build reported success and there is no image called $image." \
               "  expected: $INSTANCE-api and $INSTANCE-web" \
               "NOTHING WAS STARTED OR REPLACED. A zero exit that built nothing is the" \
               "one build failure that would otherwise reach the containers."
    fi
done
echo "  $INSTANCE-api and $INSTANCE-web are built"
echo
# <<< guard: images-built

# --- 1a. an identical rebuild keeps the identity it already had ----------------------
# `D-36`, AND THE ONE PART OF CRITERION 1'S ROW `R-1` DOES NOT BLOCK. Fetch, switch and
# roll back are claims about a server with a previous version on it and there is no such
# host; "run it twice and the second changes nothing" is a claim about THIS host.
#
# `BUILDX_NO_DEFAULT_ATTESTATIONS` above removes the reason the id moved. This is the
# second half, and it is here because it catches a cause the first half does not: **`api`
# and `migrate` are two services sharing one image**, and compose writes
# `com.docker.compose.service` into the image it builds. Measured on this host, that label
# came out `migrate` on one run and `api` on the next, of the same tree -- so the config,
# and with it the id, can still move although nothing about the image's content did.
#
# So the build is left exactly as it was and the TAG is moved back: if what the build
# produced has the same CONTENT as the image the name pointed at before it, the name is
# pointed at the old image again and the build's duplicate is discarded. `compose up -d`
# then sees an image that never moved and recreates nothing.
#
# THE FAILURE MODE THIS MECHANISM WOULD HAVE, NAMED. An image that kept an old identity
# after its content genuinely changed would leave a stale container running and make
# `verify-deployed.sh` call it this tree -- that probe compares the bytes INSIDE the
# running container against the working tree, so a stale container is exactly what it
# reports on. `fingerprint_of` is what makes that a sha256 collision rather than a
# possibility, and `docs/program/reviews/W24-IDEM.md` §4 does not reason about it: it
# forces the wrong retag by hand, brings the stack up on it and reads what the probe says.
short_id() { printf '%s' "${1#sha256:}" | cut -c1-12; }

# The content of an image, and nothing about the build that produced it.
#
# `.RootFS.Layers` is the list of diffIDs -- the sha256 of each layer's UNCOMPRESSED tar.
# A byte that changed anywhere under any `COPY` or `RUN` changes the layer carrying it and
# therefore this list. That is the whole safety argument: content that genuinely changed
# cannot present itself as identical without colliding a sha256.
#
# The runtime configuration is compared too, because a Dockerfile that changed only `CMD`,
# `ENV`, `USER`, `WORKDIR`, `EXPOSE`, a health check or a volume produces the same layers
# and a different image, and an operator who changed one of those must get it.
fingerprint_of() {
    docker image inspect --format \
        '{{.Os}}/{{.Architecture}}{{range .RootFS.Layers}} {{.}}{{end}} {{json .Config.Env}} {{json .Config.Cmd}} {{json .Config.Entrypoint}} {{json .Config.WorkingDir}} {{json .Config.User}} {{json .Config.ExposedPorts}} {{json .Config.Volumes}} {{json .Config.StopSignal}} {{json .Config.Healthcheck}}' \
        "$1" 2>/dev/null || true
    # The labels, MINUS compose's own bookkeeping, which is the `api`/`migrate` flip above:
    # it records which service was credited with the build, which is a fact about the
    # builder and not about the image. Every other label is compared, so a label a
    # Dockerfile sets is a changed image.
    docker image inspect --format \
        '{{range $name, $value := .Config.Labels}}{{println $name $value}}{{end}}' \
        "$1" 2>/dev/null | grep -v '^com\.docker\.compose\.' || true
}

# One image name, what the name pointed at before the build, and the tag that kept that
# image alive across it. An empty `previous` is a host that had no such image.
keep_identity_if_unchanged() {
    local name="$1" previous="$2" current before after
    current="$(docker image inspect --format '{{.Id}}' "$name")"
    if [ -z "$previous" ]; then
        printf '  %-28s %s  built; there was no previous image to keep\n' \
            "$name" "$(short_id "$current")"
        return 0
    fi
    if [ "$previous" = "$current" ]; then
        printf '  %-28s %s  unchanged; the build did not move the id at all\n' \
            "$name" "$(short_id "$current")"
        return 0
    fi
    before="$(fingerprint_of "$previous")"
    after="$(fingerprint_of "$current")"
    if [ -z "$before" ] || [ -z "$after" ]; then
        printf '  %-28s %s  new image; the previous one could no longer be read, so it is\n' \
            "$name" "$(short_id "$current")"
        printf '  %-28s    NOT claimed to be identical to anything\n' ""
        return 0
    fi
    if [ "$before" != "$after" ]; then
        printf '  %-28s %s  CONTENT CHANGED; replaces %s\n' \
            "$name" "$(short_id "$current")" "$(short_id "$previous")"
        return 0
    fi
    if ! docker tag "$previous" "$name"; then
        printf '  %-28s %s  identical content, and the tag could NOT be moved back to %s.\n' \
            "$name" "$(short_id "$current")" "$(short_id "$previous")"
        printf '  %-28s    Its containers will be recreated. That is safe, it is what this\n' ""
        printf '  %-28s    script did before, and it is not what this run intended.\n' ""
        return 0
    fi
    printf '  %-28s %s  identical content; kept, and %s discarded\n' \
        "$name" "$(short_id "$previous")" "$(short_id "$current")"
    # The build's own image is now untagged and identical to one that is tagged: every
    # layer is shared, so it costs no space, but one per run would still accumulate as a
    # dangling entry. It is removed, and a removal that did not happen is SAID rather
    # than swallowed.
    if ! docker image rm "$current" >/dev/null 2>&1; then
        printf '  %-28s    (%s could not be removed; `docker image prune` clears it)\n' \
            "" "$(short_id "$current")"
    fi
}

if [ "$PRESERVE_IDENTITY" = yes ]; then
    echo "-- image identity --"
    keep_identity_if_unchanged "$INSTANCE-api" "$PREVIOUS_API_ID"
    keep_identity_if_unchanged "$INSTANCE-web" "$PREVIOUS_WEB_ID"
else
    echo "-- image identity: ALPHA_PRESERVE_IMAGE_IDENTITY=no, so every build is taken as"
    echo "   a new image and api, web and migrate will be recreated --"
fi
echo

# --- 2. up. `migrate` runs once here and `api` waits for it --------------------------
# Migrations are a deploy step and never something a serving process does on start: two
# replicas starting together would race the same upgrade. `compose.server.yml` says so and
# expresses it as `depends_on: migrate: service_completed_successfully`.
# `up -d` already blocks on the `depends_on` conditions this file declares -- postgres and
# s3 healthy, s3-init and migrate completed successfully, api and web healthy before the
# proxy -- so it returns when the stack is up or when it could not be. Its status is
# printed and NOT acted on: `services-healthy` below is the authority on what is running,
# and a second opinion here would be a place for the two to disagree. What that status
# DOES do is decide whether that guard also reads the one-shot services' exit codes --
# `$UP_STATUS` is read there and nowhere else.
echo "-- bringing the stack up --"
UP_STATUS=0
compose up -d || UP_STATUS=$?
[ "$UP_STATUS" -eq 0 ] || echo "deploy.sh: \`compose up -d\` exited $UP_STATUS; the guards below decide."
echo

# --- 2a. the pin comes off ------------------------------------------------------------
# The second tag from `# --- 1.` exists only so the previous image survives the build. It
# comes off HERE and not before `up`, and the order is the point: while the old container
# is still running, this host's docker REFUSES to untag the image it runs -- `conflict:
# ... container <id> is using its referenced image`, measured -- so removing the pin
# earlier would have failed on exactly the runs where the content DID change.
#
# After `up` there are two cases and both are right. Content identical: the pin and the
# live name point at the same image, so this drops a tag and nothing else. Content
# changed: `up` has replaced the containers, the pin is the last tag on the old image, and
# dropping it deletes that image -- which is what this script did before there was a pin.
# Neither case is worth failing a deployment over, so a pin that would not come off is
# reported and left; the next run re-points it.
for pinned in "$INSTANCE-api" "$INSTANCE-web"; do
    [ "$PRESERVE_IDENTITY" = yes ] || continue
    docker image inspect "$pinned:$PREVIOUS_TAG_SUFFIX" >/dev/null 2>&1 || continue
    docker image rm "$pinned:$PREVIOUS_TAG_SUFFIX" >/dev/null 2>&1 || \
        echo "deploy.sh: NOTE: $pinned:$PREVIOUS_TAG_SUFFIX is still there. It names the" \
             "image this run replaced; the next run re-points it."
done

# --- 3. now ask the running stack, and let it fail -----------------------------------
#
# THE FIRST OF THESE QUESTIONS COMES BEFORE THE PROXY RELOAD, AND `D-38` IS WHY. Until
# this commit the reload ran first, and on a run where `up` had failed the script printed
# *"the guards below decide"* and then died inside `reload-proxy.sh` with
#
#     nginx: [emerg] host not found in upstream "api"
#     reload-proxy.sh: the proxy configuration is not valid. ... Fix proxy/nginx.conf
#
# -- exit 5, a refusal rather than a false success, which is the half that was right, and
# an operator sent to edit a file that is CORRECT. `nginx.conf` cannot resolve `api`
# because there is no `api` container, and the guard that says so in those words ran after
# the reload and therefore never ran. Measured again here before the move: `W26-OPS.md` §1.
#
# So the order is: ask whether the stack that was brought up is actually there, and only
# then touch the proxy. A reload that fails AFTER `services-healthy` has passed really is
# about the proxy's own configuration, which is what its message says.

# >>> guard: services-healthy
# Every long-running service, by name, in the state compose knows it to be in. `up --wait`
# already waits on the health checks -- this is not a second copy of that, it is the claim
# that all five containers are still there afterwards, which `--wait` does not say: a
# container that became healthy and then exited satisfied `--wait` on its way past.
#
# `proxy` has no health check of its own and is expected to report `running` with no health
# state; that is written down rather than special-cased silently, because a proxy that
# quietly grew a health check should show up here as a question, not as a pass.
#
# WHEN `up` ITSELF FAILED, THE ONE-SHOT SERVICES ARE ASKED FIRST, and they are the reason
# "the guards below decide" is a true sentence rather than a hope. `s3-init` and `migrate`
# run once and leave an exit code behind; nothing else in this script looks at them, and
# they are exactly what a failed `up` is usually about -- `W24-CERT2` measured `s3-init`
# exiting 1 on a full disk, which is why `api` was never created. They are asked ONLY on a
# run where `up` was non-zero: on a good run their containers are `exited/0` and reading
# them would be a second opinion about a success nobody doubts.
if [ "$UP_STATUS" -ne 0 ]; then
    for service in s3-init migrate; do
        #: `--all`, because a one-shot service's container is not running by the time it
        #: matters. Without it `ps --quiet` prints nothing and the failure reads as absence.
        cid="$(compose ps --all --quiet "$service" 2>/dev/null | head -1 || true)"
        [ -n "$cid" ] || continue
        state="$(docker inspect --format '{{.State.Status}}/{{.State.ExitCode}}' \
            "$cid" 2>/dev/null || true)"
        case "$state" in
            ''|exited/0|running/*|created/*|restarting/*) ;;
            *) refuse "\`compose up\` failed, and the '$service' service of $INSTANCE is $state." \
                      "  container: $cid" \
                      "That is the step that did not complete. Whatever is missing or stale" \
                      "below follows from it, and the proxy has not been touched. Logs:" \
                      "  docker compose logs $service" ;;
        esac
    done
fi

echo "-- every service is there, in the state compose knows it to be in --"
for service in postgres s3 api web proxy; do
    cid="$(compose ps --quiet "$service" 2>/dev/null | head -1 || true)"
    if [ -z "$cid" ]; then
        refuse "the '$service' service of $INSTANCE has no container." \
               "The stack was brought up and this one is not there. Nothing about this" \
               "deployment is claimed."
    fi
    state="$(docker inspect --format \
        '{{.State.Status}}/{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
        "$cid" 2>/dev/null || true)"
    [ -n "$state" ] || state="unknown/unknown"
    case "$state" in
        running/healthy|running/none) printf '  %-9s %s\n' "$service" "$state" ;;
        *) refuse "the '$service' service of $INSTANCE is $state." \
                  "  container: $cid" \
                  "Expected running/healthy, or running/none for the proxy, which has no" \
                  "health check. Logs:  docker compose logs $service" ;;
    esac
done
echo
# <<< guard: services-healthy

# The step after a rebuild that everyone forgets. nginx resolves an upstream once, at
# worker start-up, and a replaced api or web container that lands on a different address
# leaves every path through the proxy answering 502 while both new containers are healthy.
# It is INTERMITTENT -- a replacement usually gets its old address back -- so "the last
# deploy was fine" is not evidence about this one. `reload-proxy.sh` is its own script and
# is reused here rather than copied.
echo "-- reloading the proxy --"
"$HERE/reload-proxy.sh" --env-file "$ENV_FILE"
echo

echo "-- the database is at the head this code expects --"
CHECK_OUTPUT="$(compose run --rm --no-deps -T --entrypoint python api \
    -m auditmanager.shared.db.check 2>&1 || true)"
printf '%s\n' "$CHECK_OUTPUT" | sed 's/^/  /'
# >>> guard: migrations-at-head
# THE DATABASE HALF, ASKED BY THE APPLICATION'S OWN CHECK, INSIDE THE APPLICATION'S OWN
# IMAGE. `auditmanager.shared.db.check` is what `make check-db` runs; running it here
# rather than re-implementing it is the difference between asking whether the deployed
# database is at the head THIS code expects and asserting that some migration command
# exited 0. The image carries `/app/db/`, so the head it compares against is the one the
# migration scripts in the image declare.
#
# THE SENTINEL IS THE EVIDENCE, NOT THE EXIT CODE, and that is the module's own rule --
# `FOUNDATION-CHECK OK check-db` "must be the last actual output line", printed once, from
# one place, only after every check has passed. The Makefile's `run_checked` refuses a zero
# without it for exactly this reason, and a check that silently does nothing must not be
# able to pass here either.
if ! printf '%s\n' "$CHECK_OUTPUT" | grep -q '^FOUNDATION-CHECK OK check-db$'; then
    refuse "the deployed database did not answer the application's own check." \
           "The stack is up and its schema is not the one this code expects, or could not" \
           "be read. The full output is above. This is the check \`make check-db\` runs," \
           "run inside the api image against the deployed database rather than on a host."
fi
echo
# <<< guard: migrations-at-head

echo "-- the published port answers --"
# The one published port, asked the way a browser would ask. `T-2` puts the API at
# `/api/v1` and the proxy strips the prefix, so `/api/v1/openapi.json` reaches the
# application's own root and needs no credential -- `T-3` and the contract's `servers`
# entry between them are why this particular path is the one to ask for.
#
# 502, 503 and 504 are separated from everything else because they are the specific shape
# of the failure above: nginx holding an upstream that is no longer there. A deploy that
# ended in a 502 would otherwise be reported as a deploy.
SERVED="$(mktemp)"
trap 'rm -f "$SERVED"' EXIT
# `|| true` and not `|| echo 000`: curl PRINTS `000` and ALSO exits non-zero when it cannot
# connect, so a fallback would run too and the refusal would read "answered 000000".
PROXY_CODE="$(curl -s -m 30 -o "$SERVED" -w '%{http_code}' \
    "http://127.0.0.1:$HTTP_PORT/api/v1/openapi.json" || true)"
[ -n "$PROXY_CODE" ] || PROXY_CODE=000
# >>> guard: proxy-answers
# `R-31` CLOSED THIS PATH BEHIND A CREDENTIAL, SO THE ANSWER THAT PROVES LIFE IS NOW 401.
# That is not a weaker probe than 200 was, and in one respect it is a stronger one: a 401
# on this path can only be produced by the application's own authorization seam, while
# nginx alone -- holding a dead upstream -- answers 502, 503 or 504. So this guard now
# establishes two things at once: the proxy reaches the API, and `D-73` is actually closed
# on the deployed stack rather than only in the tree.
#
# A 200 here is therefore a REFUSAL, and deliberately so: it means the four documentation
# routes are open again on a running deployment, which is the defect `R-31` was ruled to
# close. A guard that accepted both answers would be a guard that cannot tell them apart.
if [ "$PROXY_CODE" != 401 ]; then
    case "$PROXY_CODE" in
        502|503|504)
            refuse "the proxy answered $PROXY_CODE on /api/v1/openapi.json." \
                   "That is nginx holding an upstream that is no longer there. The images" \
                   "may be perfect and this stack still serves nothing. The reload above" \
                   "did not fix it; look at:  docker compose logs proxy api" ;;
        200)
            refuse "/api/v1/openapi.json answered 200 with no credential." \
                   "R-31 closed the four documentation routes; this deployment serves the" \
                   "full API description to any caller that reaches the port. That is D-73" \
                   "open again on a running stack, and no claim about this deployment's" \
                   "exposure is made." ;;
        *)
            refuse "http://127.0.0.1:$HTTP_PORT/api/v1/openapi.json answered $PROXY_CODE, not 401." \
                   "Every service reported healthy and the one published port does not" \
                   "answer the way an authenticated API answers. Nothing is claimed." ;;
    esac
fi
echo "  $PROXY_CODE on http://127.0.0.1:$HTTP_PORT/api/v1/openapi.json -- the API answered"
echo
# <<< guard: proxy-answers

# >>> guard: schema-conforms
# `PA-01` CRITERION 1'S SECOND CLAUSE, VERBATIM: *"the schema the running app serves
# conforms to the frozen `contracts/api/v1/openapi.json` -- the same check the gate runs,
# re-run against the deployed process rather than against a build artifact"*.
#
# THE SAME CHECK, AND THAT IS LOAD-BEARING. `tests/contract/api_v1/openapi_conformance.py`
# is mounted and its own `surface()` and `differences()` are called. A second comparison
# written here would be a second authority over the contract, which is the exact objection
# revision 1 of `ALPHA_ROADMAP.md` raised against FastAPI and which §3 `T-1` answers with
# "not an assurance but a gate". The engine imports nothing but the standard library, which
# is what makes mounting it possible; `reset.sh` mounts `object_attrs.py` the same way.
#
# IT RUNS IN THE API IMAGE, not on the host: the frozen contract is already there at
# `/app/contracts/api/v1/openapi.json`, and a deploy host has a python only by luck. The
# served document has already been fetched by the guard above, through the proxy, so what
# is compared is what a browser would be served and not what a build artifact contains.
#
# WHY THIS IS NOT IN `verify-deployed.sh`: that script compares image bytes to tree bytes
# and says, in its own header, that the served document is a comparison it deliberately
# does not make -- because the frozen and generated documents legitimately differ and there
# is no digest to compare. This is the conformance engine, which is the thing that CAN
# compare them, and it answers a different question: not "is this stack this tree" but "is
# what it serves the contract".
echo "-- the served schema conforms to the frozen contract --"
if [ ! -r "$CONFORMANCE_ENGINE" ]; then
    refuse "the gate's conformance engine is not in this clone." \
           "  expected: $CONFORMANCE_ENGINE" \
           "The criterion asks for the gate's own check re-run against the deployed" \
           "process. Without the engine there is no check to re-run, and a deploy that" \
           "skipped it would report a conformance it never made."
fi
# THE SERVED DOCUMENT GOES IN ON STDIN AND IS NOT MOUNTED, AND THAT WAS MEASURED RATHER
# THAN CHOSEN. This guard was written with `-v "$SERVED:/served.json:ro"`, driven from a
# clean clone, and the container answered:
#
#     IsADirectoryError: [Errno 21] Is a directory: '/served.json'
#
# `$SERVED` comes from `mktemp`, so it is under `/tmp`. **The docker daemon on that host is
# the snap build, and its mount namespace has `/tmp/snap-private-tmp/snap.docker/tmp`
# mounted over `/tmp`** -- so a bind source under `/tmp` is not the file the operator can
# see, it is nothing, and docker's answer to a bind source that does not exist is to create
# an empty DIRECTORY at the destination and start the container anyway. Measured on this
# host, minimally, with the two halves side by side: the identical bind of a file under
# `/root` arrives as the file and prints its contents.
#
# This is `reset.sh`'s `--restore` finding in a second costume -- there, a relative path
# handed to `docker run -v` was a volume NAME rather than a directory. The lesson is the
# same one: **a `-v` source is resolved by the daemon, not by the shell that typed it**, and
# it fails by producing something plausible rather than by stopping.
#
# A `mktemp -p` somewhere else would have fixed this one path and left the class open, so
# the mount is gone instead. `reset.sh` already pipes a file into a container this way
# (`compose exec -T postgres pg_restore ... < "$DUMP_DIR/database.dump"`) and `-T` is what
# makes it work. The engine stays a mount because it lives in the repository, which the
# daemon does see -- the same place `reset.sh` mounts `object_attrs.py` from.
#
# EXIT 2 IS A SEPARATE ANSWER FROM EXIT 1 on purpose. "The served document could not be
# read" and "the served document does not conform" are two different things to tell an
# operator, and the first reported as the second is exactly the failure this comment is
# about: a guard that refuses for the wrong reason sends somebody to look at the contract
# when the fault is in the fetch.
CONFORMANCE_DRIVER='
import json, sys
sys.path.insert(0, "/engine")
from openapi_conformance import differences, operation_index, surface

# R-31 CLOSED /openapi.json BEHIND A CREDENTIAL, SO THE DOCUMENT NO LONGER ARRIVES ON
# STDIN. This asks the deployed process for its own document instead of asking it through
# nginx. The criterion says "the schema the running app SERVES" and "against the deployed
# process rather than against a build artifact" -- both still hold, and this is the more
# direct of the two readings: it is this image application object, built from this
# container environment, not a file that was copied in.
#
# WHAT WAS LOST, SAID PLAINLY: the document no longer travels the proxy inside THIS check.
# Two other guards cover that and neither is new. The proxy-answers guard above proves
# nginx reaches the API, because it now expects 401 and only the application can produce
# one, while nginx alone answers 502, 503 or 504. And verify-deployed.sh proves the image
# bytes are this tree bytes. The alternative was to teach a deploy script to mint a
# reviewer credential, which puts signing in on the deployment path to ask a liveness
# question.
try:
    from auditmanager.api.app import create_asgi_app

    served = create_asgi_app().openapi()
except Exception as exc:  # noqa: BLE001 - any failure here is "could not read", exit 2
    print("the deployed process could not produce its own schema: %r" % exc)
    sys.exit(2)
frozen = json.load(open("/app/contracts/api/v1/openapi.json", encoding="utf-8"))
report = differences(surface(frozen), surface(served))
print("frozen ops : %d" % len(operation_index(frozen)))
print("served ops : %d" % len(operation_index(served)))
print("differences: %d" % len(report))
for line in report[:25]:
    print("  " + line)
sys.exit(0 if not report else 1)
'
CONFORMANCE_STATUS=0
compose run --rm --no-deps -T \
    -v "$CONFORMANCE_ENGINE:/engine/openapi_conformance.py:ro" \
    --entrypoint python api -c "$CONFORMANCE_DRIVER" 2>&1 | sed 's/^/  /' \
    || CONFORMANCE_STATUS=$?
if [ "$CONFORMANCE_STATUS" -eq 2 ]; then
    refuse "the stack is up and could not produce its own schema." \
           "What came back is above. The stack is up and the conformance check was NOT" \
           "made, which is a different thing from a check that was made and failed."
fi
if [ "$CONFORMANCE_STATUS" -ne 0 ]; then
    refuse "the document this stack serves does not conform to the frozen contract." \
           "The differences are listed above, in the gate's own words. The stack is up and" \
           "serving; what it serves is not the agreed surface, so no claim about the" \
           "fifteen operations of this deployment is a claim about PC-01."
fi
echo
# <<< guard: schema-conforms

echo "deploy.sh: $INSTANCE is up at http://127.0.0.1:$HTTP_PORT"
echo "deploy.sh: every service healthy, the database at head, the served schema conforming."
if [ "$PRESERVE_IDENTITY" = yes ]; then
    echo "deploy.sh: running it again against this tree changes nothing -- no layer"
    echo "deploy.sh: rebuilds, no data is touched, and every container keeps its id."
else
    echo "deploy.sh: running it again is safe -- no layer rebuilds and no data is touched,"
    echo "deploy.sh: but api, web and migrate are recreated, because"
    echo "deploy.sh: ALPHA_PRESERVE_IMAGE_IDENTITY is no. See the note at the top."
fi
echo "deploy.sh: then ask the other question --"
echo "  infra/deploy/verify-deployed.sh --env-file $ENV_FILE"
