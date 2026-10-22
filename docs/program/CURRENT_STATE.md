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

The development API surface is **81 paths / 93 operations / 272 schemas**, the error
catalogue has **27** codes, the migration head is **`0030_executor_connections`**,
`VERSION` is `0.7.0`, the contract is sealed at `1.0.0` with the `R-143` executor connections
added under `R-144` (`EXEC-CANDIDATE-1.md`; the `1.1.0` label is a separate reseal). `origin/main` carries `0.7.0` since the owner's merge of pull request
#3 (`48c8e34c`, no gate; `RELEASES.md` has the row and the record); host verification and the
`v0.7.0` tag are owed, the last tag is `v0.6.0`. Run `infra/deploy/verify-deployed.sh` for the
current deployment; this document is no substitute for that probe.

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
`W54-BUNDLE-EXPORT-01`). `W54-LOCAL-IMPORT-01` imported that bundle into an
isolated local stack and served search, document, paragraphs and ranged PDF
from it; «Нормы» now also has a catalogue (`listNormDocuments`) with
derived display designations, and a run's findings download as Excel
(`exportRunXlsx`). The stand import, its copy record and the admin's
designation of a current snapshot have not run; they need an owner window.

## Code-first series (R-135)

The plan is [`CODE-FIRST-TO-BETA.md`](dispatch/CODE-FIRST-TO-BETA.md);
`R-135` defers the complete beta gate to the final code candidate, and each
development candidate carries only its focused evidence. No beta acceptance
is claimed. Detailed evidence: `CFB-INT-DEV-PUBLISH-17.md` … `-67.md` and,
for the `R-139` night window of 2026-10-20, `NIGHT-1020-INT-01.md`.

- **Unserved preparations.** W56a (recorded-only AR v2 profile, source-bound
  request, observations, merge, finding plan; real model/price verification
  `W56A-MODEL-PIN-01` stopped), W57a (retrieval, map, qualification and
  citation preparations, v3 request/parser/grounding; qualified set, CITE
  stage and CAP-01 open), W57b (certified XLSX chain, catalogue custody and
  saved-text readers, slug chain; reviewed slug source and 0024 seal open),
  W56b (Attempt-fenced readers for text windows, crops, regions; vision
  policy open) and W58 (source mirror, isolated DB-plus-Blob restore drill,
  synthetic restore passed, real drill not run).
- **W59 sections (served).** An expert confirms a version's stage (П/Р) and
  one of 15 sections (`classifyDocumentVersion`, `getVersionSectionReview`,
  migration 0024); run start and re-audit route by the confirmed section
  through a text-profile registry — AR plus 13 draft legacy-ported
  profiles, none for ПБ — and refuse an unclassified version or a section
  without a profile; the project screen groups documents by section.
  «Настройки анализа» lists the profiles (`listAnalysisProfiles`); АИ, ПЗ,
  ПОС and ТХ are proven in recorded mode with synthetic recordings only.
- **Run references.** A stopped run's page ends with «Нормативные ссылки»
  (`getRunNormReferences`): the standards cited in the run's saved text, each
  resolved against the snapshot the run pinned into five outcomes; no finding,
  no model call, no migration.
- **Versions.** An expert corrects a confirmed classification by an append-only
  revision with a reason (`correctVersionClassification`, migration 0028); the
  original confirmation is never changed. `uploadDocumentVersion` adds the next version to a set;
  `compareDocumentVersions` serves the deterministic comparison (same stage
  and section) and the W62 П→Р comparison; `carryOverDecision` carries an
  expert decision onto an `unchanged` matched finding as a new event.
- **Work and money.** «Диспетчер» (W61 code, migration 0025): an administrator
  assigns a project or document set to an expert who works it through «Мои
  задачи»; every change is an append-only event. The «Оптимизация» tab (W60,
  migration 0026) stores price lists (CSV/XLSX, immutable revisions with a
  parse report) and vendor lists per section; no money figure exists without
  a price-list position. «Спецификация и цены» (`getSpecificationPrices`)
  reads the AR specification rows from a version's saved text and matches
  them to the current price list; amounts and per-currency totals only for
  matched same-unit rows with a numeric quantity. «Предложения» (migration
  0027): an expert starts a pass for an AR set and gets deterministic
  `cheaper_analog` proposals from the price list and the effective vendor
  list, decides each (accept / reject / revise) in an append-only history, and
  downloads a formula-escaped CSV; a saving exists only when both prices and a
  quantity do. «Оптимизация разделов» (`getSectionSpecification`) shows a
  section's Form-7 specification across projects whose current version is
  confirmed in it — rows never merged across projects, each priced from its
  own project's list, per-project totals only. No menu item is a stub any
  more. Expert review of the draft profiles remains open.

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
