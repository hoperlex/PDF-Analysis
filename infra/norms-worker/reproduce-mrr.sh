#!/usr/bin/env bash
# Reproduce the recorded bge-m3 bake-off inside the norms-worker image, with no network.
#
# HEAVY STEP (W54-FREEZE-01, W54-PLAN.md §3.9): about 450 s of passage encoding plus the
# corpus read and tokenizer statistics, about 3.2 GiB peak RSS. Run it only inside an
# owner-designated window, after `free` shows at least 6 GiB available.
#
#   infra/norms-worker/reproduce-mrr.sh IMAGE CORPUS_DIR OUTPUT_DIR
#
# IMAGE is the locally built image (never pulled); CORPUS_DIR is the normative corpus drop,
# mounted read-only; OUTPUT_DIR is new or empty and receives bge-m3.json and run.log. The
# repository checkout holding this script is mounted read-only as /work, so the runner and
# fixture are the tracked bytes whose SHA-256 the recorded result names. The last line is
#   norms-worker MRR reproduced: 0.848611 (24 queries, 563 windows)
# and any differing deterministic field exits non-zero (compare_bakeoff.py).
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
  --env PYTHONPATH=/work/src \
  --mount "type=bind,source=$repo,target=/work,readonly" \
  --mount "type=bind,source=$corpus,target=/corpus,readonly" \
  --mount "type=bind,source=$output,target=/out" \
  --workdir /work \
  "$image" \
  python /work/tools/norms/embedding_bakeoff.py \
    --corpus /corpus \
    --fixture /work/fixtures/evaluation/norms/retrieval_queries.v1.json \
    --model bge-m3 \
    --output /out/bge-m3.json \
    --threads 8 \
  > "$output/run.log"

python3 "$repo/infra/norms-worker/compare_bakeoff.py" \
  --recorded "$repo/fixtures/evaluation/norms/results/bge-m3.json" \
  --measured "$output/bge-m3.json"
