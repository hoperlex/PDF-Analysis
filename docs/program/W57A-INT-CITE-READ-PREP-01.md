# W57A-INT-CITE-READ-PREP-01 — persisted citation read preparation

**Base:** exact published dev33
`77d39efedd4d5c74582a02dbf5ea86acb4b054f7`.
**Status:** isolated, unserved source candidate. No database, object store,
provider or remote publication operation was used.

## Result

`findings/citation_reader.py` selects one terminal Run under an exact Version
and caller-supplied profile identity. It verifies the frozen snapshot/set pair,
the reviewed content key, both exact available set/catalogue custody bindings
and a succeeded CITE stage before reading findings. It then reads every
canonical and member observation for the Run, checks the persisted 0023 count
including explicit zero, and compares every citation's Run, snapshot, set,
document, paragraph, reliable raw quote span, source PDF binding and source
attribution. It returns immutable DTOs for a later report assembler and does
not commit or change state.

The reader refuses old v1/v2 partitions with a NULL certificate, mismatched
Run/Version/profile, forged source rows and absent canonical observations.
An empty citation query is never interpreted as zero without the persisted
`norm_citation_count=0` certificate. SQL joins do not use slug, filename or
display designation as identity.

## Evidence

- Focused offline reader and existing writer probes: **42 passed**.
- Programme governance suite: **28 passed**. Python compilation, frozen
  contract/migration SHA-256 comparison and direct task governance findings
  `[]`: **passed**. Staged whitespace check is recorded at commit.
- The tests exercise a valid attributed citation, certified zero and refusals
  for stale version/profile/Run/set, failed CITE, changed content key,
  unconfirmed custody, wrong document/paragraph, unreliable source, bad raw
  span, noncontiguous ordinal and missing or excess citation count.

## Limits and integration

The profile argument is an exact equality guard only. No v3 profile identity
is registered yet, so this adapter must remain unserved. The caller must
supply the registered identity, authorization and one consistent read
transaction; the current tests use fake result rows. PostgreSQL readback and
constraint/commit behavior need an isolated real DB lane after the W55b gate.
The reader does not read PDF bytes or prove S3 availability beyond the
persisted available Blob and confirmed binding facts.

This slice returns verified finding citation partitions, not the full
`NormVerificationReport`: withheld counts, textless-page context, partial CITE
error rendering, a public facade and API wiring still require an owned follow-up.
The served endpoint remains its typed refusal. No qualified W54 set or beta
acceptance is claimed.

Changed paths are exactly this report, its formal task, the additive adapter
and its offline test. `contracts/**`, migrations, root dependencies/locks,
composition, existing readers/writers, API, UI, `CURRENT_STATE.md`, remote
refs and tags are untouched. The integrator may cherry-pick the source commit
after dev33. Rollback is that bounded commit; no feature flag or data rollback
applies before activation.
