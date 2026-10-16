# W56B-INT-RECOGNISED-REGION-DB-S3-ACCEPT-01 — persisted OCR reader acceptance

Base: development candidate
`ef802c112cd2b61de5ee9aa701739b04eb2d7f36`.

The new test uses the committed synthetic `image_only_with_block.zip` bundle,
the existing real PostgreSQL/S3 run fixtures and a recorded AR v2 Run. The
production executor saves and binds source preparation and portal geometry
under a current Attempt. At the next stage's entry point, the test reads one
OCR quote and region through `load_saved_recognised_region`, checks the saved
artifact references and source digests, and verifies that a forged Attempt
token refuses. A test sentinel stops execution before the next stage and any
provider effect. Database rows roll back through the existing harness;
content-addressed synthetic S3 objects may remain.

## Checks

- Python compilation, import, task governance, frozen SHA-256 readback and
  whitespace: passed.
- Targeted real PostgreSQL/S3 test on an isolated, migrated `0023_norm_citations`
  instance: **1 passed in 1.32s**.
- Two setup attempts before the isolated instance existed failed before any
  test body: first because the sandbox denied loopback sockets, then because
  the inherited root `.env` addressed a stopped PostgreSQL port. They are not
  counted as test passes or product failures.
- The test instance was stopped with `make down`; its two disposable volumes,
  temporary `.env` and `.venv` link were removed. Other instances were not
  touched.
- No proxy, paid call or full gate is part of this task.

## Contracts and limits

No product code, contract, migration, registry, W54/W57/W58 path, provider
policy, API/UI, composition root or dependency changed. This tests the
unserved reader only. It does not test a served OCR citation, finding
publication, real corpus or beta acceptance. The forged token test is not a
cross-process lease-expiry drill.

Only three tracked paths change: the test,
`docs/program/tasks/W56B-INT-RECOGNISED-REGION-DB-S3-ACCEPT-01.md` and this
report. Rollback is removing those files. The integrator may cherry-pick the
exact local commit after clean-tree handoff.
