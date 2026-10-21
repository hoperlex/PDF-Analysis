# W57B-INT-SAVED-TEXT-DB-S3-ACCEPT-01 — result

**Status:** passed on isolated real PostgreSQL 0023 and private S3, against
published dev61 `8c0dc0e708332e73bd3dc5defdae9fa97665f4ac`.
This is an unserved acceptance test, not beta or normative-corpus publication.

## Changed files

- `tests/integration/runs/test_reference_text_input_db_s3_accept.py` — one
  production-executor test of saved source custody, W57b text read, reference
  page mapping and forged Attempt refusal.
- `docs/program/tasks/W57B-INT-SAVED-TEXT-DB-S3-ACCEPT-01.md` — task freeze.
- `docs/program/W57B-INT-SAVED-TEXT-DB-S3-ACCEPT-01.md` — this report.

## Checks and evidence

- `make up` and `make migrate` passed for only
  `auditmanager-w57b-text-accept-01`, ports 55462/59064/59065, database
  `auditmanager_w57b_text_accept_01` and bucket
  `auditmanager-w57b-text-accept-01`; migration reached 0023.
- Targeted real-service test: **1 passed in 1.15 s** on its final run.
  The fixture is committed `image_only_with_block.zip`, published through
  public Document and Blob ports. Production `execute_run` saved and bound
  `prepared.text_layer` under `source_preparation`; a query found exactly one
  bound publication row for the current Attempt and Blob.
- `load_saved_reference_text` read that Blob under its exact saved size cap;
  the Version/page check returned two empty PDF text pages. The W57b bridge
  returned two unread references (`text=None`) despite two nonempty OCR
  markdown blocks. A forged execution token returned
  `EXECUTION_TOKEN_INVALID` while `open_stream` was patched to fail if
  called. No model call, provider effect or finding was persisted.
- Programme governance: **16 passed**, with five unrelated pytest warnings
  while removing other workers' shared `/tmp/pytest-of-root/garbage-*` paths.
- Owned Python compiled; `git diff --check`, exact three-path delta and all
  seven frozen input hashes matched. No full `make gate` under R-135's
  intermediate code-candidate rule.
- `make down` removed this instance's containers/network; its two exact
  disposable Docker volumes were removed. No other lane's services or data
  were touched.

## Integration contract and limits

The test proves a real persisted Run/Attempt and private Blob roundtrip for
the **unserved** saved PDF text reader, and that the pure bridge leaves OCR-only
pages unread. It does not prove a served reference caller, a later effect
authorization, a complete B3.5 export, qualified normative-corpus DB/S3
publication or beta acceptance. The interception intentionally stops before
provider dispatch; no paid model was used.

No contract, migration, runtime, lockfile, composition root, global style,
API route, remote ref or tag changed. Revert the three owned paths to remove
this acceptance evidence; there is no product-state rollback or feature flag.

## Integrator note

Review the three-path source commit and run the focused test against an
isolated 0023 pair if independent replay is needed. This task grants no
`origin/dev` or `origin/main` publication authority.
