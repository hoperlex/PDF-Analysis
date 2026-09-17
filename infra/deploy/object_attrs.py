"""Turn `mc --json stat --recursive` into the TSV `reset.sh` restores objects from.

**Why a sidecar exists at all.** `mc mirror` copies bytes and drops S3 user metadata.
Measured, not assumed: an object mirrored out and back came home with
`Content-Type: application/octet-stream` and no `X-Amz-Meta-Content-Sha256`, and the
storage adapter then refused it -- `validation_failed`, `content-sha256`, "recorded on
every object this adapter publishes" (`src/auditmanager/storage/s3.py`, `_META_SHA256`).
The instance listed the document and 422'd on its bytes, which is worse than empty because
it looks recovered.

So a dump is three things: the database dump, the object bytes, and this file. `R-4` -- the
owner ruled that real client documents may be uploaded -- is why the difference matters.

It runs inside the API image, through `docker compose run --entrypoint python`, because
that image is the one thing this stack is guaranteed to have an interpreter in. The deploy
host is not assumed to have python, jq, or anything but docker.

One line per object: ``key<TAB>content-sha256<TAB>content-type``. Keys cannot contain a tab
-- they are `blobs/<two>/<two>/<ULID>` -- and the reader refuses one that does.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DUMP = Path(sys.argv[1] if len(sys.argv) > 1 else "/dump")
SHA_KEY = "x-amz-meta-content-sha256"


def main() -> int:
    rows: list[str] = []
    for line in (DUMP / "objects.stat.json").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        if record.get("status") != "success" or record.get("type") != "file":
            continue
        # `mc` reports the name as `<bucket>/<key>`; the bucket is the caller's own.
        name = record["name"].split("/", 1)[1]
        if "\t" in name or "\n" in name:
            print(f"object_attrs: refusing a key with a tab or newline: {name!r}", file=sys.stderr)
            return 1
        metadata = {k.lower(): v for k, v in (record.get("metadata") or {}).items()}
        rows.append(
            "\t".join(
                (
                    name,
                    metadata.get(SHA_KEY, ""),
                    metadata.get("content-type", "application/octet-stream"),
                )
            )
        )
    (DUMP / "objects.attrs").write_text(
        "".join(f"{row}\n" for row in rows), encoding="utf-8"
    )
    print(f"object_attrs: recorded {len(rows)} objects")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
