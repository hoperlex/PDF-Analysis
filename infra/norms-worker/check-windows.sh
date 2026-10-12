#!/usr/bin/env bash
# Check, in the rebuilt norms-worker image and with no network, that the baked embedder's
# windows equal the bake-off runner's on the real BAAI/bge-m3 tokenizer, over the synthetic
# set and every paragraph and chunk of the corpus drop; record the real tokenizer's answers
# over the synthetic set for the container-free replay test.
#
# HEAVY STEP (W54-FREEZE-01): the corpus read and about 400 000 tokenizations, a few minutes,
# under 1 GiB. Run it only inside an owner-designated window.
#
#   infra/norms-worker/check-windows.sh IMAGE CORPUS_DIR OUTPUT_DIR
#
# The checkout is mounted read-only at /work (the runner is its tracked bytes), the corpus
# read-only at /corpus; OUTPUT_DIR is new or empty and receives check.log and
# bge-m3-5617a9f.v1.json. The last line is
#   norms-worker windows equal: <n> texts, <w> windows
set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "usage: $0 IMAGE CORPUS_DIR OUTPUT_DIR" >&2
  exit 2
fi

image=$1
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
corpus=$(readlink -f -- "$2") || { echo "refused: corpus $2 does not resolve" >&2; exit 2; }
if [ ! -f "$corpus/MANIFEST.json" ]; then
  echo "refused: $corpus is not a corpus drop (no MANIFEST.json)" >&2
  exit 2
fi
mkdir -p -- "$3"
output=$(cd -- "$3" && pwd -P)
case "$output/" in
  "$corpus/"*)
    echo "refused: the output directory $output lies inside the corpus drop" >&2
    exit 2
    ;;
esac
if [ -n "$(ls -A -- "$output")" ]; then
  echo "refused: the output directory $output is not empty" >&2
  exit 2
fi

docker run --rm --pull never --network none \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp \
  --mount "type=bind,source=$repo,target=/work,readonly" \
  --mount "type=bind,source=$corpus,target=/corpus,readonly" \
  --mount "type=bind,source=$output,target=/out" \
  --workdir /work \
  "$image" \
  python /work/infra/norms-worker/check_windows.py \
    --corpus /corpus \
    --record /out/bge-m3-5617a9f.v1.json \
  2>&1 | tee "$output/check.log"
