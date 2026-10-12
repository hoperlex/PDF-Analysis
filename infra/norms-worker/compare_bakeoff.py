#!/usr/bin/env python3
"""Compare a norms-worker bake-off run with the recorded ``bge-m3`` result, exactly.

``reproduce-mrr.sh`` runs ``tools/norms/embedding_bakeoff.py`` inside the image with no network
and hands its JSON here, beside ``fixtures/evaluation/norms/results/bge-m3.json``. Every
deterministic field must be equal: the fixture, runner and corpus identities, the model and
pinned runtime, the tokenizer statistics, the 24 ranks, MRR and recalls, and the vector shape.
Only timings, peak RSS and the host description (Python patch level, kernel) may differ; they
are printed, never compared. Standard library only, so it runs on the host after the container
has exited.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


#: Fields that describe the host or the clock rather than the model's behaviour.
NON_DETERMINISTIC = frozenset(
    {
        "inference.model_load_seconds",
        "inference.query_seconds",
        "inference.passage_seconds",
        "inference.passages_per_second",
        "inference.max_rss_mib",
        "runtime.python",
        "runtime.platform",
        "tokenization.tokenizer_load_seconds",
        "tokenization.canonical_paragraphs.seconds",
        "tokenization.character_chunks.seconds",
    }
)


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        flat: dict[str, Any] = {}
        for key, item in value.items():
            flat.update(_flatten(item, f"{prefix}.{key}" if prefix else str(key)))
        return flat
    return {prefix: value}


def differences(recorded: dict[str, Any], measured: dict[str, Any]) -> list[str]:
    """Every deterministic field whose value differs, or that only one side has."""
    left = _flatten(recorded)
    right = _flatten(measured)
    found: list[str] = []
    for key in sorted(set(left) | set(right)):
        if key in NON_DETERMINISTIC:
            continue
        if key not in left:
            found.append(f"{key}: not recorded, measured {right[key]!r}")
        elif key not in right:
            found.append(f"{key}: recorded {left[key]!r}, absent from the run")
        elif left[key] != right[key]:
            found.append(f"{key}: recorded {left[key]!r}, measured {right[key]!r}")
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recorded", type=Path, required=True)
    parser.add_argument("--measured", type=Path, required=True)
    args = parser.parse_args(argv)
    recorded = json.loads(args.recorded.read_text(encoding="utf-8"))
    measured = json.loads(args.measured.read_text(encoding="utf-8"))

    found = differences(recorded, measured)
    benchmark = measured.get("benchmark", {})
    runtime = measured.get("runtime", {})
    inference = measured.get("inference", {})
    print(
        "norms-worker run: python {python}, {platform}; passages {seconds} s; "
        "peak RSS {rss} MiB".format(
            python=runtime.get("python"),
            platform=runtime.get("platform"),
            seconds=inference.get("passage_seconds"),
            rss=inference.get("max_rss_mib"),
        )
    )
    if found:
        for line in found:
            print(f"MISMATCH {line}", file=sys.stderr)
        print(
            f"norms-worker MRR NOT reproduced: {benchmark.get('mrr')!r} "
            f"(recorded {recorded['benchmark']['mrr']!r}); {len(found)} field(s) differ",
            file=sys.stderr,
        )
        return 1
    print(
        f"norms-worker MRR reproduced: {benchmark['mrr']:.6f} "
        f"({benchmark['queries']} queries, {benchmark['candidate_windows']} windows)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
