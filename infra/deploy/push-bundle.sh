#!/usr/bin/env bash
# `W54-TRANSPORT-01` -- send one verified bundle to the stand through the inbound key.
#
#   infra/deploy/push-bundle.sh --host <user@stand> --identity <private key>
#                               [--known-hosts <file>] [--dry-run] <bundle directory>
#
# Runs HERE, on the development host. `<bundle directory>` is what
# `python -m auditmanager.norms.bundle export` wrote: a directory named `<KEY>` --
# `<content_key>+<bundle digest>` -- holding `SHA256SUMS` and the files it lists.
#
# What it does, in order:
#
#   1. checks the name against the inbound key's grammar (`lib/forced-command.sh`) and the
#      tree against the one bundle rule both ends apply (`fc_check_bundle_tree`): the
#      SHA256SUMS digest is the name's, the files are exactly the listed ones, and every
#      file is RE-HASHED now (`W54-PLAN.md` §3.5: "re-hashed at export and at push");
#   2. measures the tar it is about to send. The tar is deterministic (sorted names, owner
#      0, mtime 0, hardlinks stored as files), so the bytes counted are the bytes sent and
#      no copy of the bundle is written to disk -- the objects are hardlinks of the drop and
#      a temporary tar would cost their whole size again;
#   3. sends `receive <KEY> <size>` with that tar on stdin. The stand checks the length,
#      the members and the same tree rule again, and keeps nothing that fails.
#
# The other inbound verbs need no wrapper; with the same key:
#   ssh -i <key> -o IdentitiesOnly=yes <user@stand> status | import <KEY> | report <KEY> | requeue <KEY>
#
# Exit: 0 the stand kept the bundle; 2 usage; 3 refused here (`REFUSED [<guard>]`); any
# other status is the stand's, passed on (3 there is a refusal on the stand).

set -euo pipefail
export LC_ALL=C

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FC_NAME=push-bundle.sh
# shellcheck source=infra/deploy/lib/forced-command.sh
. "$HERE/lib/forced-command.sh"

HOST="${STAND_INBOUND_HOST:-}"
IDENTITY="${STAND_INBOUND_IDENTITY:-}"
KNOWN_HOSTS=""
DRY_RUN=no
BUNDLE=""
UNKNOWN=""

usage() {
    sed -n '4,5p' "${BASH_SOURCE[0]}" | sed 's/^#  *//' >&2
    exit 2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --host) HOST="${2:-}"; shift 2 || usage ;;
        --identity) IDENTITY="${2:-}"; shift 2 || usage ;;
        --known-hosts) KNOWN_HOSTS="${2:-}"; shift 2 || usage ;;
        --dry-run) DRY_RUN=yes; shift ;;
        -h|--help) usage ;;
        -*) UNKNOWN="${UNKNOWN:-$1}"; shift ;;
        *)
            [ -z "$BUNDLE" ] || UNKNOWN="${UNKNOWN:-$1}"
            BUNDLE="$1"; shift ;;
    esac
done

# >>> guard: known-options
if [ -n "${UNKNOWN:-}" ]; then
    fc_refuse known-options "unrecognised option or a second bundle directory: $UNKNOWN"
fi
# <<< guard: known-options

[ -n "$BUNDLE" ] || usage

# >>> guard: bundle-dir-present
if [ -L "$BUNDLE" ] || [ ! -d "$BUNDLE" ]; then
    fc_refuse bundle-dir-present "$BUNDLE is not a directory."
fi
# <<< guard: bundle-dir-present

BUNDLE="$(cd "$BUNDLE" && pwd -P)"
KEY="${BUNDLE##*/}"
PARENT="${BUNDLE%/*}"
[ -n "$PARENT" ] || PARENT=/

# >>> guard: bundle-name-grammar
if ! [[ $KEY =~ ^${FC_BUNDLE_KEY_ERE}$ ]]; then
    fc_refuse bundle-name-grammar "'$KEY' is not a bundle name the inbound key admits." \
        "<content_key>+<SHA-256 of SHA256SUMS>; grammar in infra/deploy/lib/forced-command.sh"
fi
# <<< guard: bundle-name-grammar

# >>> guard: host-configured
if [ -z "$HOST" ] && [ "$DRY_RUN" = no ]; then
    fc_refuse host-configured "no stand named: --host <user@host> or STAND_INBOUND_HOST."
fi
# <<< guard: host-configured

# >>> guard: identity-present
if [ "$DRY_RUN" = no ] && { [ -z "$IDENTITY" ] || [ ! -r "$IDENTITY" ]; }; then
    fc_refuse identity-present "the inbound key's private half is not readable: '${IDENTITY}'." \
        "--identity <file> or STAND_INBOUND_IDENTITY"
fi
# <<< guard: identity-present

fc_check_bundle_tree "$BUNDLE" "$KEY"
echo "push-bundle.sh: $KEY verified here ($(grep -c . "$BUNDLE/SHA256SUMS") files re-hashed)."

# The one tar both passes produce. GNU tar; `--hard-dereference` stores a file with several
# links as a regular file every time, because the stand refuses link members.
bundle_tar() {
    tar --create --format=gnu --sort=name --owner=0 --group=0 --numeric-owner --mtime=@0 \
        --hard-dereference --mode='u+rwX,go+rX,go-w' --directory "$PARENT" -- "$KEY"
}

SIZE="$(bundle_tar | wc -c)"
REMOTE="receive $KEY $SIZE"

SSH=(ssh -T -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes
    -o ServerAliveInterval=15 -o ServerAliveCountMax=4)
[ -z "$IDENTITY" ] || SSH+=(-i "$IDENTITY")
[ -z "$KNOWN_HOSTS" ] || SSH+=(-o "UserKnownHostsFile=$KNOWN_HOSTS")

if [ "$DRY_RUN" = yes ]; then
    echo "push-bundle.sh: dry run; would send $SIZE bytes as: $REMOTE"
    exit 0
fi

echo "push-bundle.sh: sending $SIZE bytes: $REMOTE"
status=0
bundle_tar | "${SSH[@]}" "$HOST" "$REMOTE" || status=$?
if [ "$status" -ne 0 ]; then
    printf 'push-bundle.sh: the stand did not keep %s (exit %s); its message is above.\n' "$KEY" "$status" >&2
    exit "$status"
fi
echo "push-bundle.sh: the stand kept $KEY. Next: ssh ... status"
