# CFB-INT-DEV-PUBLISH-31 — W57a grounding and W56b crop bytes on dev

The candidate builds on directly read
`origin/dev=f6f19220fa5ae019daae07a3771846e2523ce55a`. The completed
W57a source `5785a915aba0bd92eccd669e07e4039c61d6d59e` is an exact
fast-forward ancestor; completed W56b source
`3650dab5a8513d06b92f2d48e595809503c98e69` is cherry-picked as
`63ca82dc`. The W56b four-path patch is byte-for-byte identical: both
source and integrated `git diff` streams have SHA-256
`106de03ae84155826a59696c309b89b75e496ec3dafd77195d45e601e5371e21`.

## Checks and scope

- W57a source: **45** focused grounding/parser and ALR-05 checks passed.
  W56b source: **13** focused supplied-byte checks passed. Both completed
  task governance, compilation and exact path checks.
- Integrated norm citation, v3 proposal/grounding, saved crop byte and
  programme suites: **84 passed** with no PostgreSQL/S3 service.
- Direct integration-task governance returned `[]`; `git diff --check`
  passed. Source payload is exactly the seven W57a and four W56b granted
  paths. This integration adds only its task, this report and bounded
  `CURRENT_STATE.md`.
- API remains **48 paths / 55 operations / 131 schemas**, SHA-256
  `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
  stage registry SHA-256 remains
  `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`.
  Domain IDs, error catalogue and migration head `0023_norm_citations`
  match their frozen inputs.

No contract, migration, root dependency/lock, composition root, API route,
existing v1/v2 production profile, W58/W54 path, global style,
production DB/S3, `origin/main`, tag or deployment input changed.

## Limits and publication

W57a's pure grounding bridge resolves every PDF quote before normative
quotes/values and withholds the whole proposal on any refusal. Separate
prompt labels now allow two map items to cite one unique canonical norm
paragraph. The accepted result is still a candidate: the caller must prove
the exact Run-pinned verified retrieval-set bytes, snapshot/map identity
and custody before an atomic CITE writer may publish it.

W56b checks supplied saved stage references, JSON and PNG bytes, including
complete crop cohort, SHA-256, sizes and image dimensions. Its caller still
must read the row through a run-scoped repository query, read Blobs from
storage and prove immutable VersionUid/current Attempt authority with a
fence or recheck. In-memory tests do not prove real DB/S3 readback; the
current interface holds supplied PNGs in memory and needs a bounded served
adapter for large runs. No provider call, qualified corpus or runtime
analysis is claimed. R-135 defers the complete W56–W63 beta gate; W55b's
release gate is separate.

Publish only the clean exact checked SHA to `origin/dev` as a fast-forward
from the recorded predecessor, then directly read back the remote SHA into
ignored local evidence. This task has no `origin/main` authority.
