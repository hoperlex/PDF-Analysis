# Task W57A-INT-CITE-READ-PREP-01 — unserved verified citation read

task_id: W57A-INT-CITE-READ-PREP-01

## Outcome

A read-only adapter returns report-ready canonical and member citation partitions
only for a terminal Run with the caller's exact Version and registered v3 profile,
the frozen verified retrieval set, succeeded CITE stage, certified observation
counts, reliable paragraph spans and source attribution. Focused offline tests
prove refusal on mismatched persisted facts.

## Depends on

- `W57A-SEAL-01A` — completed at `c71048f788e5d0bee39a312217dfd4c0912e5bc1`.
- `W57A-SEAL-01B` — completed at `c08182cab78bed70afbc777019d43de6c0bd2e18`.
- `W57A-INT-CITE-TXN-PREP-01` — completed in `CFB-INT-DEV-PUBLISH-33`.
- `CFB-INT-DEV-PUBLISH-33` — completed at `77d39efedd4d5c74582a02dbf5ea86acb4b054f7`.

## Frozen inputs

- base commit: `77d39efedd4d5c74582a02dbf5ea86acb4b054f7`;
- API v1 SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- analysis stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain identifiers SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head: `0023_norm_citations`, SHA-256 `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- `W57-PLAN.md` A3.4–A3.6, R-76, R-80 and R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: dev33 has a 0023 citation writer and a refusing report route, but no
  persisted verified citation reader.

### P-01 — exact base and reader absence

- captured_at: 2026-10-16
- command: `git rev-parse HEAD; git ls-tree -r --name-only HEAD src/auditmanager/findings/citation_reader.py; rg -n 'def get_norm_verification|dependency_unavailable' src/auditmanager/bootstrap/adapters.py`
- captured_output:
  ```text
  77d39efedd4d5c74582a02dbf5ea86acb4b054f7
  769:    def get_norm_verification(self, *, run_id: str) -> models.NormVerificationReport:
  1029:    # stubs answering `503 dependency_unavailable`.
  ```
- interpretation: the exact base has no reader path; the existing API seam is
  separate and still refuses. The method body itself is outside this grep.

### P-02 — persisted partition certificate

- captured_at: 2026-10-16
- command: `rg -n 'ADD COLUMN norm_retrieval_set_id|ADD COLUMN norm_citation_count|CREATE TABLE finding_observation_norm_citation|CREATE CONSTRAINT TRIGGER trg_finding_observation_partition' db/migrations/versions/20261016_0023_norm_citations.py`
- captured_output:
  ```text
  279:        "ALTER TABLE audit_run ADD COLUMN norm_retrieval_set_id text NULL "
  328:            ADD COLUMN norm_citation_count integer NULL;
  355:        CREATE TABLE finding_observation_norm_citation (
  468:        CREATE CONSTRAINT TRIGGER trg_finding_observation_partition
  ```
- interpretation: the Run pin, observation count and deferred relation check
  are persisted; this anchor inventory is not a real DB acceptance proof.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/findings/citation_reader.py`
- `tests/integration/findings/test_w57a_citation_reader_offline.py`
- `docs/program/tasks/W57A-INT-CITE-READ-PREP-01.md`
- `docs/program/W57A-INT-CITE-READ-PREP-01.md`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, root dependencies and locks;
- API routes/schemas, `src/auditmanager/bootstrap/**`, composition root;
- existing finding writers/readers and public facades;
- `CURRENT_STATE.md`, UI/global styles, remote refs, tags and stand services.

## Non-goals

No served report, role authorization, registered v3 profile, Run writer, CITE
stage activation, withheld diagnostic aggregation, textless-page projection,
partial-stage error policy, source PDF byte readback, real DB acceptance,
qualified W54 set or beta claim. This adapter needs a later owned integration
slot before any route calls it.

## Deliverables

One additive SELECT-only adapter, focused offline refusal tests, task and
result report. It returns citation partitions for later report assembly.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/findings/test_w57a_citation_reader_offline.py tests/integration/findings/test_w57a_citation_publication_offline.py`;
- `python3 -m py_compile src/auditmanager/findings/citation_reader.py tests/integration/findings/test_w57a_citation_reader_offline.py`;
- `git diff --check`, frozen SHA-256 and direct task governance findings `[]`;
- no PostgreSQL, S3, Docker or full gate while W55b holds the host.

## Integration contract

The caller supplies a **registered** v3 profile ID, Run ID, exact Version ID,
authorization and a repeatable-read transaction. The adapter refuses a
nonterminal or mismatched Run, nonverified set/custody, failed CITE stage,
unmatched canonical/member observation, missing certified count, noncontiguous
citation ordinals, foreign snapshot/set/document/paragraph, untrusted source
attribution, missing available PDF binding or quote outside the reliable raw
paragraph. `None` is never converted into a certified zero.

## Failure/idempotency/security cases

Every fault raises `CitationReadRefused` without a write. The selected profile
parameter is an exact equality guard, not a v3 registry by itself. A caller
must not turn this DTO into a served report until a separate task defines
withheld counts, partial CITE errors, textless pages and route ownership.

## Rollback / feature flag

Unserved additive source only. Revert the bounded commit before activation;
no runtime feature flag or data rollback applies.

## Handoff

- changed files: the four exact allowed paths;
- commands/results: accompanying result report;
- known limits: offline proof only and no served report;
- integration notes: cherry-pick after dev33, then prove real DB readback in
  an isolated lane after W55b gate releases the host.
