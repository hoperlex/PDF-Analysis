#!/usr/bin/env bash
# Run the embedder's encode phase inside the norms-worker image, with no network.
#
# HEAVY STEP (W54-FREEZE-01, W54-PLAN.md §3.9): an embedding build window. About 3.2 GiB RSS
# and 1.25 windows/s on 8 threads -- the full corpus is about 14 h, spread over night windows.
# Run it only inside an owner-designated window, after `free` shows at least 6 GiB available.
#
#   infra/norms-worker/run-build.sh IMAGE CHECKPOINT_DIR SNAPSHOT_ID CHUNKING_PROFILE [MAX_BATCHES]
#
# CHECKPOINT_DIR is the build directory `python -m auditmanager.norms.embedding prepare` wrote
# on the host (it must hold plan.json); it is the only mount, and the only thing written. The
# container has no network and no database: it reads the plan's inputs and writes one verified
# checkpoint per batch, skipping every batch already verified, so killing it at any moment
# costs at most the batch in flight. MAX_BATCHES ends this window's share cleanly.
#
# Exit status is the embedder's: 0 every batch verified (run `load` next), 75 batches remain
# (run this again in the next window), 2 refused.
set -euo pipefail

if [ "$#" -lt 4 ] || [ "$#" -gt 5 ]; then
  echo "usage: $0 IMAGE CHECKPOINT_DIR SNAPSHOT_ID CHUNKING_PROFILE [MAX_BATCHES]" >&2
  exit 2
fi

image=$1
snapshot=$3
profile=$4
max_batches=${5:-}
if [ ! -d "$2" ]; then
  echo "refused: the checkpoint directory $2 does not exist; run prepare first" >&2
  exit 2
fi
checkpoint=$(cd -- "$2" && pwd -P)
if [ ! -f "$checkpoint/plan.json" ]; then
  echo "refused: $checkpoint holds no plan.json; run prepare first" >&2
  exit 2
fi
case "$checkpoint/" in
  */.local/norms/corpus/*)
    echo "refused: the checkpoint directory $checkpoint lies inside the corpus drop" >&2
    exit 2
    ;;
esac
if ! [[ "$snapshot" =~ ^ns_[0-9A-HJKMNP-TV-Z]{26}$ ]]; then
  echo "refused: $snapshot is not a norms snapshot id" >&2
  exit 2
fi
if [ -n "$max_batches" ] && ! [[ "$max_batches" =~ ^[0-9]+$ ]]; then
  echo "refused: MAX_BATCHES $max_batches is not a count" >&2
  exit 2
fi

limit=()
if [ -n "$max_batches" ]; then
  limit=(--max-batches "$max_batches")
fi

status=0
docker run --rm --pull never --network none --memory 5g --memory-swap 5g \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp \
  --mount "type=bind,source=$checkpoint,target=/checkpoint" \
  "$image" \
  python -m auditmanager.norms.embedding build \
    --snapshot "$snapshot" \
    --chunking-profile "$profile" \
    --checkpoint /checkpoint \
    "${limit[@]}" || status=$?
exit "$status"
