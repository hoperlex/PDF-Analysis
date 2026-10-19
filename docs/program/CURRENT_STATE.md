# Current state

**Updated 2026-10-20 for the night window under `R-139` (functional slices:
sections, norms, storage structure), after development candidate 67 added
the `R-137` W54 session repair to published candidate 66
(`ec41bb5881b2e677af7f22af62266818f37b2a61`).** W55b is published on
`origin/main` and tagged `v0.6.0`. Its exact-tree gate counts as `GATE OK`
under R-125; the deploy workflow selected that tree and the owner then ran
`infra/deploy/verify-deployed.sh` on the host with a passing image/tree
comparison. The workflow's own verify step was skipped because a child
consumed its stdin; the tested repair is on `origin/dev`, and moving it to
main needs a fresh complete gate and a direct exact-SHA owner instruction.
The owner waived five credentialed live W55b product checks for that release;
those journeys remain unverified. See `W55B-INT-TAG-01.md`,
`W55B-INT-MAIN-VERIFY-ADDENDUM-01.md` and `CFB-INT-DEV-PUBLISH-43.md`.

The development API surface is **50 paths / 57 operations / 137 schemas**,
the error catalogue has **25** codes, the migration head is
**`0024_version_classification`**, and `VERSION` is `0.6.0`. These are checkout
facts; the release tree has its own frozen 47/54/123 surface and
`0021_portal_bundles` head. For the current deployment, run
`infra/deploy/verify-deployed.sh`; this document is no substitute for that
probe.

## Normative corpus (W54)

The 674-document, 31,619-file source drop has complete file checksums and a
restore-verified base dump with 348,777 paragraphs and 55,702 chunks
(`W54-CORPUS-OPERATE-01`, `W54-CORPUS-PROMOTION-01`).

Under `R-137` the 121 blocks whose text was the recognition model's own
reasoning were re-read by Sonnet subagents of a Claude Code session, not by
the paid proxy run. The answers passed the unchanged two-read rule. The
ignored ledger holds 121 applied repairs, 0 unreliable blocks and no charge,
and the real drop's ledger validation accepted it. The repaired key is
`2026-07-23..2026-08-20+17d+121r.0a1bafe103ff`. A 16-page spot check found
two single-word deviations from print (a map label and a silently corrected
printed typo) and two table-layout notes; under `R-138` the owner accepted
the ledger as it is. See `W54-SESSION-REPAIR-01.md`.

The repaired snapshot `ns_01M59N8QNBVN91ACA2HCE6VE74` (674 documents,
350,194 paragraphs, 55,855 chunks) is loaded in the local promotion database
with a complete BGE-M3 embedding build (61,573 windows, set digest
`e7fac64c…`), dumped and restore-verified, and exported as a verified bundle
with `build: present` (`W54-SNAPSHOT-LOAD-01`, `W54-EMBED-BUILD-01`,
`W54-BUNDLE-EXPORT-01`). The stand import, its copy record and the admin's
designation of a current snapshot have not run; they need an owner window.

## Code-first series (R-135)

The plan is [`CODE-FIRST-TO-BETA.md`](dispatch/CODE-FIRST-TO-BETA.md);
`R-135` defers the complete beta gate to the final code candidate, and each
development candidate carries only its focused evidence. Every slice below
is unserved, and no beta acceptance is claimed.

- **W56a.** A recorded-only AR v2 profile, a source-bound saved request and
  call, verified observations and merge, and a deterministic finding plan.
  A transaction gate is reached only through the explicit offline executor
  bridge. A bounded Run-to-Version-to-PDF attestation binds local seeded
  evaluation bundles. Real model and price verification
  (`W56A-MODEL-PIN-01` is stopped), a measured baseline and served
  activation remain open.
- **W57a.** Retrieval, map, qualification and citation preparations; the
  0023 storage seal; a v3 request candidate, response parser, grounding
  bridge and local evaluator. A qualified retrieval set, an active CITE
  stage and CAP-01 remain open.
- **W57b.** A certified XLSX composition chain, a verified catalogue custody
  reader, a current-Attempt saved text-layer reader, a page bridge and a
  bounded explicit slug chain. A reviewed slug source, the 0024 seal and the
  served route remain open.
- **W56b.** Run/Attempt-fenced readers for saved text windows, crops and
  recognised-text regions. An approved vision/region/budget policy remains
  open.
- **W58.** Read-only source mirror, isolated target copy and a DB-plus-Blob
  drill with a guarded restore; a synthetic restore passed. A real recovery
  drill has not run.
- **W59 (served, night window `R-139`).** An expert confirms a version's
  project stage (П/Р) and one of 15 sections (`classifyDocumentVersion`,
  `getVersionSectionReview`, migration 0024); run start and re-audit route
  by the confirmed section through a text-profile registry — AR plus 13
  draft legacy-ported profiles, none for ПБ — and refuse an unclassified
  version or a section without a profile; the project screen groups
  documents by confirmed section. Served comparison and expert review of
  the draft profiles remain open.

Detailed evidence is in `CFB-INT-DEV-PUBLISH-17.md` through
`CFB-INT-DEV-PUBLISH-67.md`.

## Pointers and history

Read the assigned task, completed `depends_on`, frozen contracts and allowed
paths before editing. `docs/program/DEBT_REGISTER.md` tracks open work. The
complete state at candidate 66 is preserved verbatim in
[the 2026-10-19 state archive](history/CURRENT_STATE_2026-10-19_ec41bb58.md),
and the 320-line state before candidate 17 in
[the 2026-10-16 state archive](history/CURRENT_STATE_2026-10-16_71373417.md).

## Previous release state — wave 48 (historical record)

The full previous release state, including the older CP-00 history, is stored
verbatim in [the dated archive](history/CURRENT_STATE_2026-10-15_ccfb9735.md).
That archive is a point-in-time record of the base tree, not live status.
