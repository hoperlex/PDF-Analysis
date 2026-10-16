# CFB-INT-DEV-PUBLISH-33 — W56b, W57a and W58 code on dev

The completed W56b source `79c726ad2d427f3e55c00093213c9b20987cff28`
is an exact fast-forward child of published dev32
`5fa9473c54a5fb009ec8c0a6a45327a3a7f1dc15`. Its five task-owned paths
are integrated without editing their bytes. W57a source
`5da5f98f96feb113c3a5f45d2ece4b0b92ef4c7c` and corrected W58 source
`283cb1ce7602267fe8e60d1c2f94ac854b7ab843`, both based on dev32,
are cherry-picked with their disjoint four- and six-path patches unchanged.
W57a source/integrated patch streams both hash to
`8926c945e5a019250b14a47004fdebd33c1f65d87d4cac36e8b75940c337afc4`;
W58 source/integrated streams both hash to
`cb08d86875a06c7c59ea261b89cb635302ce365f02e8c7f2e60c8f4a0d084ebe`.

## Checks and scope

- W56b source: **21** focused offline tests, Python compilation, frozen
  hashes, task-handoff governance and exact path checks passed.
- W57a source: **36** focused CITE/grounding/ALR-05 checks; W58 source:
  **12** synthetic CLI checks and six runbook Bash blocks parsed. Both
  source tasks passed compilation and task governance without services.
- Integrated W56b crop read, W57a CITE/grounding, W58 recovery and programme
  suites: **135 passed**. No service or paid provider was invoked.
- Direct integration and all three source task governance findings: `[]`.
  API/stage/domain/error/crop schema and migration 0023 hashes match the
  frozen inputs; compile, whitespace, exact path and clean-tree checks are
  completed before publication. Fresh remote fast-forward/readback follow.

No contract, migration, root dependency/lock, composition root, existing
Runs/Jobs/storage adapter, API/UI, global style, production DB/S3,
`origin/main`, tag or deployment input changed.

## Limits and publication

The unserved W56b adapter reads saved geometry StageResult and only its declared
portal, crop manifest and PNG Blobs for one current Run/Attempt. It checks a
caller-supplied aggregate byte ceiling, passes those bytes to the existing
pure crop verifier and rechecks Attempt, Run and stage before returning.
The API has no caller yet. Offline fakes do not prove PostgreSQL/S3 readback;
the later provider call needs a fresh authority check and effect journal.
Row locks remain held while Blob bytes stream, so callers must bound this
transaction.

The W57a writer checks current Run/Attempt, completed call/effect, the
verified set and supplied set bytes before inserting an accepted normative
finding and its 1–5 citation rows in the caller's transaction. It is not
wired to the served CITE stage; a real PostgreSQL commit must exercise 0023
deferred constraints and the caller must obtain the set through custody.

W58 adds an opt-in private fixture builder and isolated target CLI. The
documented synthetic source has one available Blob referenced by an
`input_manifest_entry`; the CLI will require that row and one full target
Blob readback. No source-S3 mirror provenance or complete metadata is
claimed. It must not run without an isolated target and capacity/identity
proof. R-135 defers the full W56–W63 beta gate; W55b release gate is separate.

Publish only the clean exact checked SHA to `origin/dev` as a fast-forward
from dev32, then directly read back the remote SHA. This task has no
`origin/main` authority.
