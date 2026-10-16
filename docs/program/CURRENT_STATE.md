# Current state

**Code-first development candidate 29, 2026-10-16.** W56b has a pure
complete IMAGE-crop cohort preflight: every checked IMAGE block needs one
matching crop, while geometry-mismatch blocks are explicit skips. It does
not read Blob bytes or call a model. See `CFB-INT-DEV-PUBLISH-29.md` and
`W56B-INT-CROP-COHORT-PREP-01.md`.

**Code-first development candidate 28, 2026-10-16.** W58 has an unactivated
guarded PostgreSQL restore callback for its offline DB-plus-Blob coordinator;
the operator still must prove an empty isolated target and matching bucket.
W54 embedding-build replay now re-reads stored window metadata before
certifying a completed build. No real recovery drill or corpus publication
has run. See `CFB-INT-DEV-PUBLISH-28.md`.

**Code-first development candidate 27, 2026-10-16.** W56b has a pure,
unserved OCR-region candidate that binds an exact recognised-text quote to
a TEXT portal block and checked region on an explicitly textless page. It
does not publish a finding or assert a PDF text-layer citation. See
`CFB-INT-DEV-PUBLISH-27.md` and `W56B-INT-RECOGNISED-REGION-PREP-01.md`.

**Code-first development candidate 26, 2026-10-16.** W57a API/stage seal
publishes the 0023 citation vocabulary and a role-guarded, typed 503 report
route until a verified reader exists. The API has 48 paths / 55 operations /
131 schemas; `text_analysis` stage identity is 1.1.0 for v1 and recorded v2.
No qualified retrieval set or served v3 writer/reader is active. See
`CFB-INT-DEV-PUBLISH-26.md` and `W57A-SEAL-01B.md`.

**Code-first development candidate 25, 2026-10-16.** W58 now has an
unactivated offline coordinator for an isolated PostgreSQL-plus-Blob restore
drill. Its closed DB audit includes both retrieval-set Blob references from
0023; it orders preflight, restored DB proof, target copy and full Blob
readback. The source passed 140 recovery/governance checks; no real drill
has run. Separate W55b `37393a97` is under its complete gate. See
`CFB-INT-DEV-PUBLISH-25.md` and `W58-INT-ISOLATED-DB-BLOB-DRILL-CODE-01.md`.

## Current development boundary

The checked predecessor of this candidate is
`origin/dev=f468d20eaf46dba82908615b04f20090541b21df`.
The development API surface is 48 paths / 55 operations / 131 schemas; the
error catalogue has 25 codes and the migration head is `0023_norm_citations`.
`VERSION` is `0.6.0`. These are checkout claims, not deployed-state evidence.
The code-first order and prerequisites are in
[`CODE-FIRST-TO-BETA.md`](dispatch/CODE-FIRST-TO-BETA.md).

W56a has a recorded-only AR v2 profile, source-bound saved request and call,
verified observation/merge artifacts, a deterministic finding plan and a
transaction gate reached only through the explicit offline executor bridge.
The gate rechecks stage and call provenance, publishes findings and
terminalizes Run/Job/Attempt atomically. It does not make a live provider call. Its
caller must commit once or roll back the whole transaction. The explicit
executor path passed real persisted-run and Blob acceptance on an isolated
lane. The measured baseline, real model/price verification, served executor
activation and complete beta gate remain open.

W57a has pure retrieval, map, qualification and citation preparations. The
0023 storage seal supplies verified-set constraints, confirmed custody
bindings, a frozen Run pin and a certified citation-count relation. The
API/stage seal adds vocabulary and a refusing report read. No qualified
retrieval-set row, verified reader or active CITE stage exists. W57b has XLSX
preparation, but its citation reader and route wait for verified W57a reader
and 0024 seal. W56b has unserved OCR-region and IMAGE crop-cohort candidates;
saved-artifact custody, Blob readback and an approved OCR citation policy
are still required. See
`W57-INT-SEAL-FREEZE-PROPOSAL-01.md`. W58 has read-only source-object mirror,
isolated target-copy and offline DB-plus-Blob drill code, including a guarded
PostgreSQL restore callback; it has not transferred a stand or proved
recovery. W59 has version-pair,
section-identity and unserved 15-choice review preparations; its section
seal waits for the required recovery-code close.

## Corpus and release boundaries

W54's 674-document, 31,619-file source passed complete file checksums. Its
57,445,702-byte base dump passed a disposable PostgreSQL restore and all 12
tracked table fingerprints: 348,777 paragraphs and 55,702 chunks are present.
The 121-page `claude-opus-5` repair has a zero-call priced plan, but no proxy
credential file exists. Repaired snapshot, embeddings, qualified bundle and
DB/S3 corpus publication remain pending. See `W54-CORPUS-PROMOTION-01.md` and
`W54-CORPUS-REPAIR-PLAN-01.md`. Embedding-build replay now checks persisted
window metadata, but a real build and qualified bundle remain absent.

The old W55b `6d63802a` main candidate failed three complete-gate attempts;
its successor `d3acd511` passed the earlier brittle test position but failed
the fourth full gate at D-142 after 4,168 passes. Read-only gate DB evidence
showed two valid Attempt-scoped publication rows; the test helper's
Run/Blob `.one()` query was too broad. Test-only successor `37393a97`
passed focused D-142 real-service checks; its new complete gate is running
after a host memory/load window. None of these candidates has been
published to `origin/main`. The remote main predecessor at the preparation
read was `23fd729dbb06c642be0588017f6b195305e2e53e`. The owner confirmed
alpha still contains only generated test data on 2026-10-16; that condition
must be rechecked before applying the R-110 copy waiver. Main publication
requires a direct exact-SHA owner instruction and
`docs/program/MAIN_AUTODEPLOY_POLICY.md`. Deployment identity must be checked
with `infra/deploy/verify-deployed.sh`; it cannot be inferred from this file.

`R-135` defers the complete W56–W63 beta gate to the final code candidate;
intermediate dev tasks carry their focused evidence. No current W54 corpus,
W56–W59 runtime, W55b deployment or beta acceptance is claimed.

## Pointers and history

Read the assigned task, completed `depends_on`, frozen contracts and allowed
paths before editing. `docs/program/DEBT_REGISTER.md` tracks open work. The
full 320-line state immediately before candidate 17 is preserved verbatim in
[the 2026-10-16 state archive](history/CURRENT_STATE_2026-10-16_71373417.md);
its dated integration reports carry the detailed checks and limitations.

## Previous release state — wave 48 (historical record)

The full previous release state, including the older CP-00 history, is stored
verbatim in [the dated archive](history/CURRENT_STATE_2026-10-15_ccfb9735.md).
That archive is a point-in-time record of the base tree, not live status.
