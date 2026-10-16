# Current state

**Code-first development candidate 20, 2026-10-16.** W54's metadata-only
preflight now has a pinned `repair-sample` check for the 121-page
`claude-opus-5` zero-call plan, source sums and restored base-dump marker. Its
actual read-only run matched the frozen metadata and refused only because
available RAM was 4.70 GiB below the 6 GiB floor. No proxy credential exists,
so no paid repair, embedding build or corpus DB/S3 publication has occurred.
See `CFB-INT-DEV-PUBLISH-20.md` and
`W54-CORPUS-REPAIR-SAMPLE-PREFLIGHT-01.md`.

**Code-first development candidate 19, 2026-10-16.** W58 now has an
unactivated helper that copies a sealed private object mirror to an isolated
S3 target, verifies complete target bytes and exact keys, and supports safe
partial retry. Its 107 recovery tests passed with a fake client; real MinIO
readback and a PostgreSQL-plus-Blob restore drill remain open. The separate
W55b `d3acd511` complete gate is still running. See
`CFB-INT-DEV-PUBLISH-19.md` and `W58-INT-ISOLATED-TARGET-OBJECT-RESTORE-01.md`.

**Code-first development candidate 18, 2026-10-16.** W54's metadata-only
preflight now accepts separate absolute source and promotion roots, so it sees
the checked source sums and restored base dump without treating them as a
qualified bundle. W56a has an explicit offline recorded executor bridge for a
persisted v2 Run with caller-supplied `fixture/<id>` and generation settings;
normal API/worker composition still selects v1. W57a has a docs-only 0023
citation/custody freeze with a certified zero-citation rule, not a migration.
The integrated focused suite passed 79 tests. The repaired W55b main candidate
`d3acd511` is still under its own complete gate. See
`CFB-INT-DEV-PUBLISH-18.md` and the three source task reports.

**Code-first development candidate 17, 2026-10-16.** The W56a recorded
publication gate and the W55b serving-carrier test deadline correction are
integrated for `origin/dev`. The W56a gate passed 15 focused tests on
an isolated PostgreSQL 17.11/MinIO lane at migration head `0022_findings_v2`;
its active executor call remains a separate task. The W55b test correction
addresses a measured 37.9-second pre-provider path that exceeded the former
30-second test wait. It changes no production code; the separate repaired
W55b candidate `d3acd511` still needs a complete `make gate`. See
`CFB-INT-DEV-PUBLISH-17.md`, `W56A-INT-RECORDED-PUBLICATION-GATE-01.md` and
`W55B-INT-GATE-TIMEOUT-01.md`.

## Current development boundary

The checked predecessor of this candidate is
`origin/dev=de3d81085f30301ddc2965f7f4bf927ea738c8b3`.
The development API surface is 47 paths / 54 operations / 124 schemas; the
error catalogue has 25 codes and the migration head is `0022_findings_v2`.
`VERSION` is `0.6.0`. These are checkout claims, not deployed-state evidence.
The code-first order and prerequisites are in
[`CODE-FIRST-TO-BETA.md`](dispatch/CODE-FIRST-TO-BETA.md).

W56a has a recorded-only AR v2 profile, source-bound saved request and call,
verified observation/merge artifacts, a deterministic finding plan and now an
transaction gate reached only through the explicit offline executor bridge.
The gate rechecks stage and call provenance, publishes findings and
terminalizes Run/Job/Attempt atomically. It does not make a live provider call. Its
caller must commit once or roll back the whole transaction. The measured
baseline, real model/price verification, served executor activation and complete beta
gate remain open.

W57a has pure retrieval, map, qualification and citation preparations, but no
verified retrieval set, citation custody relation or active CITE stage. W57b
has XLSX preparation, but its citation reader and route wait for serial
`0023`/`0024` contract and migration seals. See
`W57-INT-SEAL-FREEZE-PROPOSAL-01.md`. W58 has read-only source-object mirror,
isolated target-copy and offline restore preparations; it has not transferred
a stand or proved DB-plus-Blob recovery. W59 has version-pair and
section-identity preparations;
its section seal waits for the required recovery-code close.

## Corpus and release boundaries

W54's 674-document, 31,619-file source passed complete file checksums. Its
57,445,702-byte base dump passed a disposable PostgreSQL restore and all 12
tracked table fingerprints: 348,777 paragraphs and 55,702 chunks are present.
The 121-page `claude-opus-5` repair has a zero-call priced plan, but no proxy
credential file exists. Repaired snapshot, embeddings, qualified bundle and
DB/S3 corpus publication remain pending. See `W54-CORPUS-PROMOTION-01.md` and
`W54-CORPUS-REPAIR-PLAN-01.md`.

The old W55b `6d63802a` main candidate failed three complete-gate attempts;
read-only gate DB timing identified a brittle test deadline, and its successor
`d3acd511` is under a separate complete gate. Neither candidate has been
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
