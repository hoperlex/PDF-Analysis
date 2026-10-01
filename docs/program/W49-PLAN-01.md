# W49-PLAN-01 — completion report

## Result

**DONE.** W49 is queued as a verified normative-corpus promotion wave behind `alpha-w48`. It
resolves storage and Blob-identity authority before implementation, keeps all alpha mutations in
one closeout slot, and requires custody, repair, canonical load, embedding build and restore
evidence before `alpha-w49`.

The scope deliberately stops before normative retrieval. Search/citation contracts, UI and
audit-run snapshot consumption are assigned no implicit semantics and move to W50 or later.

## Changed files

- `docs/program/tasks/W49-PLAN-01.md`;
- `docs/program/dispatch/W49-PLAN.md`;
- `docs/program/dispatch/W49-JUDGES.md`;
- `docs/program/W49-PLAN-01.md`;
- `docs/program/CURRENT_STATE.md` — queued-wave orientation only;
- `docs/program/dispatch/W48-PLAN.md` — successor boundary only.

## Checks

- `.venv/bin/python -m pytest tests/contract/api_v1/test_doc_prose_facts.py
  tests/contract/api_v1/test_surface_counts_in_prose.py -q` — **47 passed**;
- decision/debt coverage review — D-59/D-71 map to the 121-row repair gate, D-70 to the live
  provider gate, D-119 to the owner/storage gate, and `NORM-Q01..Q09` to contract, custody,
  retention, topology and public-release boundaries;
- ownership review — contract/migration, storage, norms tooling, judges and mutable alpha state
  each have one owner; parallel writers are disjoint;
- `git diff --check` — exit 0; separate whitespace scan of the new untracked W49 files is clean.

## Contracts

This planning task changes none. It exposes one existing incompatibility for owner resolution:
content-derived/deduplicated product `blob_id` semantics versus the independent per-admission
`blob_id` required by `NORM-Q05`. W49 implementation cannot begin until `W49-DECIDE-01` selects
one model and `W49-CUSTODY-SEAL` updates all affected contract consumers atomically.

## Risks and known limitations

- W49 cannot freeze until `alpha-w48` exists and its deployed/manual evidence is accepted.
- D-70 still blocks the real repair run; D-119 blocks custody writes until the storage lifecycle
  choice is made.
- Base counts 348,777 / 55,702 / 62,325 cannot be promised after repair; W49 records new measured
  counts and digests.
- The BGE worker still needs target-like cold/warm, resource, full-index and no-network packaging
  measurements.
- `NORM-Q04` keeps the corpus internal-only, so the public alpha gains no search endpoint in W49.

## Integrator handoff

After `W48-INT-CLOSE`, open only `W49-FREEZE-01`. Then obtain `W49-DECIDE-01`; do not dispatch a
storage, migration, provider or embedding lane around it. The final `W49-INT-CLOSE` alone may
push refs, trigger auto-deploy, use alpha/provider credentials, mutate alpha data and create the
tag.

## Forbidden-hotspot proof

Only the six documentation paths listed above belong to this task. Contracts, migrations,
runtime/storage/norms code, raw corpus, dependencies/locks, composition, API/UI/global styles,
workflows, external state and Git refs are untouched.
