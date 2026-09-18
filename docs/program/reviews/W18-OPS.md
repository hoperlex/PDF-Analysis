# W18-OPS — the restore is proved by writing, not by reading

**Session** `W18-OPS` · **HEAD on arrival** `3df17a7` ("docs(register): D-19 closes, and the
baseline had been protecting half of it"), worktree `/root/w18ops` on `agent/w18-ops` off
`origin/dev`. Logs under `/root/w18ops-logs/`.

**Rows:** `D-17` (fix), `D-18` (measure only — the catalog is the owner's).

## 1. The key set, read from the adapter

Command:

```
grep -rn 'Metadata=\|ContentType\|MetadataDirective\|put_object\|copy_object\|upload_fileobj' \
    src/auditmanager/storage/
```

Publication is `S3BlobStore.publish` (`src/auditmanager/storage/s3.py`), one `copy_object`
with `MetadataDirective="REPLACE"`. It writes **four user-metadata keys** and **one system
header**:

| written on publication | source | read back by |
| --- | --- | --- |
| `blob-id` | `_metadata_for` | *nothing in `src/`* |
| `blob-role` | `_metadata_for` | `_record_from_head` -> `PublishedBlob.role` |
| `content-sha256` | `_metadata_for` | `read()` validation, `_record_from_head` |
| `content-size` | `_metadata_for` | `_record_from_head` size cross-check |
| `Content-Type` | `ContentType=verified.media_type` | `_record_from_head` -> `media_type` |

(in progress)
