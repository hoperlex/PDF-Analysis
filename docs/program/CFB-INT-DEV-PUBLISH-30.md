# CFB-INT-DEV-PUBLISH-30 — unserved AR v3 proposal input on dev

The candidate builds on directly read
`origin/dev=55977fd93414e70ef0deb210f2b7e0511abc7375` and cherry-picks
completed W57a source `14219bd29ab61cc22a6bf7f563396d9e3d63ef28`
as `e66cd22f`. The eight-path source patch is byte-for-byte identical:
parent-to-source and dev29-to-cherry-pick `git diff` streams both have
SHA-256 `0a413014a7cf7ec00422d0fb599388e6b759d7500f4f01ad7f3a3d39ceefd08c`.

## Checks and scope

- Source: **40** v3/v2 schema/parser tests, Python compilation, direct task
  governance and exact changed-path checks passed. A stale v2 test pin had
  expected seven categories to equal the now twelve-category API; source
  corrected that test only, leaving v2 production code unchanged.
- Integrated v3/v2 schema/parser and programme suites: **68 passed**.
- Direct integration-task governance returned `[]`; `git diff --check`
  passed. The source has exactly eight granted paths. This integration adds
  only its task, this report and bounded `CURRENT_STATE.md`.
- API remains **48 paths / 55 operations / 131 schemas**, SHA-256
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
  stage registry SHA-256 remains
  `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`.
  Domain IDs, error catalogue and migration head `0023_norm_citations`
  match their frozen inputs.

No contract, migration, root dependency/lock, composition root, existing
v1/v2 production profile, API route, global style, production DB/S3,
`origin/main`, tag or deployment input was changed.

## Limits and publication

The pure v3 parser accepts seven legacy and five normative categories.
Normative proposals require 1–5 labelled `{label, quote}` claims and both
values; nonnormative proposals forbid those properties. It rejects unknown,
duplicate, null or out-of-range fields and salvages only complete elements
under an explicit truncation signal. Parsed values remain untrusted model
output, with no finding or expert-decision authority.

The served `getRunNormVerification` route remains typed 503. Without a
registered v3 profile identity and CITE publisher, persisted set/stage/
partition rows cannot prove a Run is v3 or that an empty SELECT certifies
zero. Qualified corpus, real DB/S3 tests and v3 runtime acceptance remain
open. R-135 defers the complete W56–W63 beta gate; W55b's release gate is
separate.

Publish only the clean exact checked SHA to `origin/dev` as a fast-forward
from the recorded predecessor, then directly read back the remote SHA into
ignored local evidence. This task has no `origin/main` authority.
