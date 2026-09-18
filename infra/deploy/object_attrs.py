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

**All five attributes, not the two that a read happens to consult.** Publication
(`S3BlobStore.publish`, `MetadataDirective="REPLACE"`) writes four user-metadata keys --
`blob-id`, `blob-role`, `content-sha256`, `content-size` -- and the `Content-Type` header.
This file used to carry `content-sha256` and `Content-Type` only, and that was chosen by
reading `read()`: those are the two a *read* validates. `blob-role` and `Content-Type` are
the two a *write* validates, in `publish`'s idempotency check, and `blob-role` was not
being carried. A restored object therefore read back byte-identical and answered
`409 conflict` -- `BlobAttributeConflictError` -- to every later upload of the same bytes,
because `_record_from_head` resolved its role to `""`. `D-17`, measured by `W15-RUN`
against a live stack twice.

`content-size` was lost the same way, and its loss is quieter rather than smaller:
`_record_from_head` only raises `SizeMismatchError` when `content-size` is present, so a
restore without it does not fail, it silently stops checking. `blob-id` is read by nothing
in `src/`; it is carried anyway, because a sidecar that records four of five keys is a
sidecar someone has to re-derive the rule for.

One line per object, six tab-separated fields:

``key<TAB>blob-id<TAB>blob-role<TAB>content-sha256<TAB>content-size<TAB>content-type``

Keys cannot contain a tab -- they are `blobs/<two>/<two>/<ULID>` -- and the reader refuses
one that does. A missing attribute is written as an EMPTY field rather than guessed at:
`reset.sh`'s `dump-verified` guard refuses a sidecar with any empty field, and that refusal
is the thing that must fire. A default invented here would hide it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DUMP = Path(sys.argv[1] if len(sys.argv) > 1 else "/dump")

#: The four user-metadata keys `_metadata_for` writes, in `s3.py`'s own order. `mc --json
#: stat` reports them with the `x-amz-meta-` prefix S3 adds; matched case-insensitively.
USER_META_KEYS = ("blob-id", "blob-role", "content-sha256", "content-size")


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
        fields = [name]
        fields.extend(metadata.get(f"x-amz-meta-{key}", "") for key in USER_META_KEYS)
        # `Content-Type` is a system header rather than user metadata, and it is every bit
        # as load-bearing: `_record_from_head` takes `media_type` from it, and `publish`
        # compares that too. No default -- see the module docstring.
        fields.append(metadata.get("content-type", ""))
        rows.append("\t".join(fields))
    (DUMP / "objects.attrs").write_text(
        "".join(f"{row}\n" for row in rows), encoding="utf-8"
    )
    print(f"object_attrs: recorded {len(rows)} objects")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
