# W57B-INT-XLSX-CERTIFIED-SOURCES-PREP-01 — citation partitions in XLSX

**Base:** published `origin/dev=95de4f6b4e10a8b60f57ae84ab66156917c7b96c`. **Status:** isolated, unserved XLSX source adapter; no route, model, DB/Blob operation or remote publication.

The adapter matches an exportable run/page source to the W57a reader's certified citation read by run, version and terminal state. It carries every canonical and member citation in order to the existing XLSX package, preserving repeats and explicit certified zero. The test assembles real XLSX bytes and reads `sheet2.xml`: the norm-document and quote cells contain both citations on separate lines, while a certified zero for a nonnormative `dimensions` finding leaves them blank. Missing finding data is refused by the existing package read, never inferred as zero.

The production adapter does not import `findings.citation_reader` internals across the bounded-context boundary. It checks the reader DTO structure supplied by a future owned public facade. A synthetic DTO can mimic the structure but proves no DB/corpus custody.

## Checks

- Focused XLSX source/package/preflight and W57a citation-reader tests: **70 passed**.
- Program governance: **16 passed**. Compilation, frozen SHA-256 and whitespace checks: passed; clean-tree technical handoff is generated after the local commit.
- Mutations cover foreign run/version/state/page version, count and ordinal mismatches, duplicate observation/finding, missing canonical and a missing finding entry.

## Integration

Cherry-pick after dev46. The later W57a public-reader and W57b API/seal owners must establish a registered v3 profile, real qualified set/corpus and CITE result, a consistent transaction, principal role/operation authorization, the CSV filename source and the independent `soffice` probe. Migration `0024_norm_references`, `exportRunXlsx` route and deployment are outside this task.

Changed files are exactly this report, its task, additive adapter and test. Contracts, migrations, existing XLSX/CSV and findings modules, W54/W56b, API/UI, composition, `CURRENT_STATE.md` and remote refs are untouched.
