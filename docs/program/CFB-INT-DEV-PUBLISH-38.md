# CFB-INT-DEV-PUBLISH-38 — W55b candidate gate evidence on dev

The two W55b main-preparation reports are integrated from their completed
source commits `d02b5ae4` and `9b83331d` after published
`origin/dev=f0580e089867ba6a9380a48dfca19a23e47f6788`. PREP-02 records
the earlier D-142 test-selector failure on `d3acd511`; it is not gate
evidence for release. PREP-03 records the exact clean W55b candidate
`37393a979a430e490843d7f410e9eca9491a4ea1` and its completed full
gate under owner ruling R-125.

The `37393a97` complete attempt passed frontend, contract and foundation
checks, then was voided by S3 `StorageUnavailableError` under host pressure.
On the same clean SHA and disposable stand, the whole failed `runs` directory
and unrun `shared_kernel` directory passed 210 tests and 244 subtests. The
canonical remainder passed 938 tests, skipped five and had one two-second
lease-timing failure; the whole `jobs` directory then passed 8/8. The exact
commands, log digests and failure lines are in PREP-03 and the ignored
candidate evidence ledger. This counts as `GATE OK` under R-125; no one
uninterrupted command printed the literal sentinel.

This publication adds only programme documentation. The W55b release
candidate stays `37393a97`, with production code byte-identical to W55b
development close. The development branch retains its later W56–W59 slices
and does not inherit the W55b gate. Contracts, migration, root dependencies,
composition root, global styles, application source, corpus and deployment
inputs are untouched by this integration.

`origin/main` remains `23fd729d` at the preparation read. The owner's
separate direct instruction naming `37393a97` is still required before
deployment. Immediately before any authorised push, `W55B-INT-MAIN-01` must
recheck the main ref and fast-forward, the R-110 generated-test-data condition
or stand copy, and the R-46 provider mode and run cost ceiling. Workflow,
same-SHA host verification and live acceptance follow the push.
