# Task W57A-INT-QUALIFICATION-DECISION-PREP-01 — pure W57a digest comparison

task_id: W57A-INT-QUALIFICATION-DECISION-PREP-01

## Outcome

One pure component checks complete stored snapshot/chunk/embedding counts and
independent source/embedding digest inputs against a W57a candidate. It emits
an exact set/catalogue digest comparison with each mismatch named. Incomplete
builds and unbound identities refuse before any matched or rejected result.

## Depends on

- `W57A-INT-RETRIEVAL-CANDIDATE-01` — completed pure set/catalogue candidate at `6d2ef67f`.
- `W57A-INT-QUALIFICATION-READ-01` — completed SELECT-only facts at `5e71a8c7`.

## Frozen inputs

- base commit: `5e71a8c7451862cd0419722375a2c932c9b3928a`.
- W57 plan SHA-256 `587297ccacef41574543a788d2526c79de157eda0212dd663e392494529debc1`, §A3.2.
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`.
- analysis contract `contracts/analysis/v1/stage-registry.json` SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`.
- migration head `0022_findings_v2`; `SnapshotBuildFacts`, `RetrievalCandidate`, `SetIdentity` on base.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the completed candidate and stored-fact reader expose distinct inputs, while W57a requires complete BGE build facts and a comparison against independently committed digests before a verified row.

### P-01 — exact component entry points

- captured_at: 2026-10-16
- command: `rg -n '^def (assemble_retrieval_candidate|read_snapshot_build_facts)' src/auditmanager/norms/retrieval/candidate.py src/auditmanager/norms/retrieval/qualification_reader.py`
- captured_output:
  ```text
  src/auditmanager/norms/retrieval/candidate.py:126:def assemble_retrieval_candidate(
  src/auditmanager/norms/retrieval/qualification_reader.py:115:def read_snapshot_build_facts(
  ```
- interpretation: the two completed source modules produce a candidate and stored scalar facts. Neither establishes independent source/embedding proof, expected artifact digests, custody or a verified row.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/retrieval/qualification_decision.py`
- `tests/integration/norms/retrieval/test_qualification_decision.py`
- `docs/program/tasks/W57A-INT-QUALIFICATION-DECISION-PREP-01.md`
- `docs/program/W57A-INT-QUALIFICATION-DECISION-PREP-01.md`

## Forbidden hotspots

`contracts/**`, migrations, existing retrieval modules, norms repository,
provider lock, public API, composition root, root dependencies, global styles,
corpus source, `CURRENT_STATE.md`, runner, stand, tags and Git refs.

## Non-goals

No independent proof generator, map approval, BGE stream recomputation,
verified/rejected DB row, custody admission, S3 publication, profile switch,
runtime API, paid provider call or beta acceptance.

## Deliverables

One pure decision module, focused tests and result report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/norms/retrieval/test_qualification_decision.py` — pass;
- Python compilation, direct task governance, whitespace and exact allowed-path proof — pass;
- complete `make gate` deferred under R-135.

## Integration contract

The caller first verifies the source bytes and complete embedding stream by an
independent process, and obtains owner-reviewed map identity and committed
expected set/catalogue SHA-256 values without deriving them from this candidate.
It passes those digests, the SELECT facts and the candidate into
`compare_retrieval_candidate`. The function refuses incomplete declared/stored
document, PDF-custody, chunk, embedded-chunk and window counts, identity or
digest drift and noncanonical candidate bytes. Only then it returns `matched`
or `rejected`, with expected/observed artifact digests and ordered mismatch
names. `matched` is not a `verified` database row and must not be pinnable.

## Failure/idempotency/security cases

Missing build, incomplete counts, unbound source or embedding digest, changed
candidate identity/bytes and malformed digest refuse. Expected set/catalogue
digest drift returns `rejected`, never an admission. Identical inputs yield
identical output. Proof provenance remains caller-owned; no corpus text or
credentials enter Git.

## Rollback / feature flag

Remove the additive pure module before runtime wiring; no data rollback or flag.

## Handoff

- changed files: four exact allowed paths.
- commands/results: focused checks in result report.
- known limits: no independent evidence producer or verified-row transaction.
- integration notes: stage only the four owned paths; do not publish on `matched` alone.
