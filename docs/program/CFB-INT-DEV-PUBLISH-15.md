# CFB-INT-DEV-PUBLISH-15 — checked code-first development candidate

The candidate builds on `origin/dev=445efc5d` with three completed source
slices. W56a now has an unactivated durable merge stage that reads the saved
observation Blob, verifies its provenance, publishes a deterministic merge
Blob and binds the StageResult; it never replays the model. W57b has a
SELECT-only preflight for an exportable run's verified XLSX page labels, but
no role grant or route. W59 has a bounded changed-line input with a rechecked
raw evidence seal; it generates no AI summary or approval.

W54's 57,445,702-byte base dump passed a disposable PostgreSQL restore and
all 31,619 source files passed fresh SHA verification. The offline repair
plan selected `claude-opus-5`, found 121 pages and spent `$0`; the proxy
credential file is absent, so paid repair, embeddings and a DB/S3 bundle are
still ahead. The W55b main-preparation report is included solely as an
interim failed-gate record. Its candidate is a different SHA and has no
deployment authority; the first gate had three worker-adapter wait timeouts.
A complete retry was started on the same clean SHA, but this development
candidate makes no claim about its result.

## Checks and publication boundary

The integrated focused W56a/W57b/W59 and program-governance suite passed
**122 tests**. Each source task's own focused, frozen-input and path checks
passed. The W54 reports name the verified dump and offline plan digests.
This integration checks direct governance, exact staged paths, clean
fast-forward and remote SHA read-back. Full `make gate` for W56a–W63 remains
deferred under R-135; the W55b release candidate must pass its own complete
gate before any exact-SHA main-publication request.

## Contracts and remaining work

This integration commit changes only this report, its task and the leading
`CURRENT_STATE.md` paragraph. Source tasks change no shared contract,
migration, root lock, composition root or global style. Real PostgreSQL/S3
acceptance and executor activation remain for W56a; W57 needs citation and
operation seals; W59 needs authoritative approved links, derived artifact
custody and expert confirmation. W54 cannot proceed to paid repair without a
proxy credential file, and no corpus DB/S3 publication or beta verdict is
claimed.
