"""Capture the response baseline. Run from the repository root::

    .venv/bin/python tests/characterization/w13_baseline/capture.py

It rewrites every file under ``records/``. It is committed so the baseline can be
re-measured deliberately -- and so a reader can see exactly how it was produced -- but
re-running it is a decision, not a routine step: the records in git are the expectation
the FastAPI rewrite must reproduce, and regenerating them against a changed
implementation would make the comparison vacuous.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import journey  # noqa: E402


def main() -> int:
    good, refused = journey.build_apps()
    exchanges = journey.run_journey(good, refused)
    written = journey.write_records(exchanges)
    for path in written:
        print(path.relative_to(journey.REPOSITORY_ROOT))
    print(f"{len(written)} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
