# Reviewed AR v3 beta pack (operator-supplied, not tracked)

`compose.server.yml` mounts this directory read-only at `/run/ar-v3` in the `api` and `worker`
services. Put the sealed manifest here (for example `pack.json`) and set
`AR_V3_BETA_PACK_MANIFEST=/run/ar-v3/pack.json` in `alpha.env`.

The manifest is produced by `python -m auditmanager.runs.v3_pack_cli seal` from six verified
retrieval sets and carries the reviewer's attestation. It holds no secret, but it is specific to
one database, so it is ignored by git. Verify it before use with
`python -m auditmanager.runs.v3_pack_cli verify --manifest <file>`. The container user (uid
10001) must be able to read the file. See `docs/program/AR-V3-BETA-PACK-INSTALL-01.md`.
