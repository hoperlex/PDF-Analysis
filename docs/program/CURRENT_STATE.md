# Current state

**Updated 2026-10-16 from published code-first development candidate 59
(`2b0a8a04a7ef2ce050e3ec3df9dd5414c68651be`), with dev60 W57b evidence
integrated in this tree.** W55b is
published on `origin/main` and tagged `v0.6.0`. Its exact-tree gate counts as
`GATE OK` under R-125; the deploy workflow selected that tree and the owner
subsequently ran `infra/deploy/verify-deployed.sh` on the host with a passing
image/tree comparison. The workflow's own verify command was skipped because
a child consumed its stdin. Its tested repair is on `origin/dev`; a separate
gate attempt on workflow-fix candidate `babab5b5` was invalidated when the
integrator deleted dependency directories used through worktree symlinks.
Those dependencies were restored from the frozen lockfiles, but that attempt
has no `GATE OK` and is not a product-code finding. Moving the repair to
main requires a fresh complete gate and direct exact-SHA owner publication
instruction. The owner explicitly waived five credentialed live W55b product checks for this
release; those journeys remain unverified. See `W55B-INT-TAG-01.md`,
`W55B-INT-MAIN-VERIFY-ADDENDUM-01.md` and `CFB-INT-DEV-PUBLISH-43.md`.

The development API surface is **48 paths / 55 operations / 131 schemas**,
the error catalogue has **25** codes, the migration head is
**`0023_norm_citations`**, and `VERSION` is **`0.6.0`**. These are checkout
facts; the release tree has its own frozen 47/54/123 surface and
`0021_portal_bundles` head. For the current deployment, run
`infra/deploy/verify-deployed.sh`; this document is no substitute for that
probe.

W54's 674-document, 31,619-file source has complete file checksums and a
restore-verified base dump with 348,777 paragraphs and 55,702 chunks.
The 121-page `claude-opus-5` repair still lacks a proxy credential. There is
no repaired qualified snapshot, complete embedding checkpoint or DB/S3
corpus publication. W54 export now checks the crop index, all 28,246 listed
crop paths and each deduplicated source's bytes; import checks PDF custody
slots, row semantics and the complete embedding-build digest before DB/S3.
These are offline guards, not a published bundle. The full-corpus elapsed
time of the added streaming build preflight has not been measured. W56b has
unserved Run/Attempt-fenced readers for saved text windows, geometry crops
and recognised-text regions; the OCR reader binds inner digests to the
Version manifest. A targeted acceptance test of that reader passed on an
isolated real PostgreSQL/S3 instance; it stopped before provider dispatch.
W57a has an unserved v3 request candidate and local response evaluator.
W57b has an unserved certified XLSX composition chain, a read-only verified
catalogue custody reader and an exact text-layer-to-reference-page bridge.
The reader passed one targeted test on isolated real 0023 PostgreSQL/S3 with
synthetic catalogue bytes, both confirmed bindings and current Attempt
fencing. The page bridge preserves Unicode offsets and marks empty pages as
unread in a pure pipeline test. Its independent LibreOffice probe failed
three bounded host attempts; B3.5 remains unverified. Served callers,
provider/effect provenance, qualified corpus, reviewed catalogue slugs,
approved W56b policy, W57a CAP-01 and W57b 0024 seal remain open. See
`CFB-INT-DEV-PUBLISH-45.md` through `CFB-INT-DEV-PUBLISH-60.md`. R-135
defers the complete beta gate to
the final code candidate. No beta acceptance is claimed.

**The following detailed snapshot is the state at dev39, before W55b's
main publication and later development candidates.** It is retained for
the decisions and evidence links from that point in time.

**Code-first dev39 / W55b candidate, 2026-10-16.** W58 synthetic DB/Blob
restore passed after a driver fix; W56/W57 added unserved evidence readers.
W55b `37393a97` counted `GATE OK` under R-125; main had not yet moved. See
`CFB-INT-DEV-PUBLISH-39.md`.

**Code-first development candidate 31, 2026-10-16.** W57a grounds v3 PDF
and normative proposals with separate N-labels for one paragraph; W56b
verifies supplied saved crop references and PNG bytes. Neither proves real
DB/S3 custody or activates served analysis. See `CFB-INT-DEV-PUBLISH-31.md`.

**Code-first development candidate 30, 2026-10-16.** W57a now has a pure,
unserved AR v3 response schema/parser. Five normative categories require
1–5 labelled citation proposals and two values; seven legacy categories
forbid those fields. The served verification reader remains typed 503 until
a registered v3 profile and CITE publisher exist. See
`CFB-INT-DEV-PUBLISH-30.md` and `W57A-INT-V3-RESPONSE-PREP-01.md`.

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

## Development boundary at dev39

The checked predecessor of this candidate is
`origin/dev=f6f19220fa5ae019daae07a3771846e2523ce55a`.
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
API/stage seal adds vocabulary and a refusing report read. The pure v3
proposal parser and grounding bridge add no runtime profile or canonical
result; prompt labels can name one paragraph through multiple map items.
No qualified
retrieval-set row or active CITE stage exists; the verified reader is unserved. W57b has XLSX
preparation, but its citation reader and route wait for verified W57a reader
and 0024 seal. W56b has unserved OCR-region and IMAGE crop-cohort candidates;
the byte verifier checks only supplied in-memory data. Real run-scoped
DB/S3 custody, Attempt fencing and an approved OCR citation policy remain
required. See
`W57-INT-SEAL-FREEZE-PROPOSAL-01.md`. W58 has read-only source-object mirror,
isolated target-copy and offline DB-plus-Blob drill code, including a guarded
PostgreSQL restore callback; it has not transferred a stand or proved
recovery. W59 has version-pair,
section-identity and unserved 15-choice review preparations; its section
seal waits for the required recovery-code close.

## Corpus and release boundaries at dev39

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
passed focused D-142 real-service checks; its new complete gate was running
after a host memory/load window. None of these candidates had yet been
published to `origin/main` at dev39. The remote main predecessor at the
preparation read was `23fd729dbb06c642be0588017f6b195305e2e53e`.
The owner confirmed alpha contained only generated test data on 2026-10-16;
that condition was rechecked before applying the R-110 copy waiver. Main
publication required a direct exact-SHA owner instruction and
`docs/program/MAIN_AUTODEPLOY_POLICY.md`. Deployment identity must be checked
with `infra/deploy/verify-deployed.sh`; it cannot be inferred from this file.

`R-135` defers the complete W56–W63 beta gate to the final code candidate;
intermediate dev tasks carry their focused evidence. At dev39 no W54 corpus,
W56–W59 runtime, W55b deployment or beta acceptance was claimed.

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
