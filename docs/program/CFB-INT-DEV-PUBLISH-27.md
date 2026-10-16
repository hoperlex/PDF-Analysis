# CFB-INT-DEV-PUBLISH-27 — W56b OCR-region candidate on dev

The candidate builds on directly read
`origin/dev=4efd756c67b5160aeca3dbc58903f72df6c93636` and cherry-picks
completed W56b source `e770cb0fed2e6522ccc01a7d6e57575ab89b1de4`
as `28140e7d`. The four-path source patch is byte-for-byte identical:
parent-to-source and dev26-to-cherry-pick `git diff` streams both have
SHA-256 `c6be3377355a37029eacd9240f7d6917200b13d758e682e41fdc8cd2e692e2e8`.

## Checks and scope

- Source: **21 new** and **65 adjacent** container-free tests, compilation,
  direct task governance and changed-path checks passed.
- Integrated container-free recognised/portal and programme suite:
  **191 passed** after correcting one stale pre-existing guard. An initial
  too-broad directory run also collected DB-backed files and reported 22
  setup errors because this isolated worktree has no `DATABASE_URL`; it was
  not a DB acceptance run.
- The stale guard prohibited every stage input named
  `prepared.recognised_text`. W56a had already frozen it as optional marked
  context for `text_analysis`, with an explicit ban on using it as quotation
  evidence. The integration-owned test correction now asserts that exact
  optional relation and retains the guard against prompt-path imports.
- Direct integration-task governance returned `[]`; `git diff --check`
  passed. The source has exactly four granted paths. This integration adds
  only the corrected guard test, its task/report and bounded
  `CURRENT_STATE.md`.

API remains **48 paths / 55 operations / 131 schemas** with SHA-256
`7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
stage registry SHA-256 remains
`58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`.
Domain IDs, error catalogue and migration head `0023_norm_citations`
are unchanged. No contract, migration, root dependency/lock, composition
root, existing production module, global style, production DB/S3,
`origin/main`, tag or deployment input was changed.

## Limits and publication

The selector produces only an unserved immutable OCR-region candidate. It
does not prove same-run Blob custody or grant OCR finding/citation
publication; later W56b work must bind checksum-verified artifacts and an
approved citation policy. No provider or real PostgreSQL/S3 was used. R-135
defers the complete W56–W63 beta gate; W55b's main release gate is separate.

Publish only the clean exact checked SHA to `origin/dev` as a fast-forward
from the recorded predecessor, then directly read back the remote SHA into
ignored local evidence. This task has no `origin/main` authority.
