# Task W59-INT-COMPARISON-500-PAGE-01 — align comparison preflight with W55b

task_id: W59-INT-COMPARISON-500-PAGE-01

## Outcome

The unserved W59 version reader and its three pure comparison guards accept
published W55b versions with up to 500 pages, while refusing 501. A complete
page-text suggestion snapshot accepts W55b's per-page and per-document text
ceilings, including a 500-page text-rich case, and refuses an over-budget one.

## Depends on

- `W59-INT-SHEET-MATCH-SUGGESTIONS-02` — completed exact full-page candidate at
  base `4d9e4f5954a100d93daa33e8b6cc2b53558cfcfa`.
- `W59-INT-VERSION-PAIR-READ-01` — completed same-set SELECT reader.
- `W59-INT-RAW-EVIDENCE-SEAL-PREP-01` — completed raw comparison seal.
- `W59-INT-FINDING-MATCH-SUGGESTIONS-01` — completed linked-sheet finding candidates.

## Frozen inputs

- base commit: `4d9e4f5954a100d93daa33e8b6cc2b53558cfcfa`
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- domain identifiers SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalog SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- W58–W63 scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- ADR-0013 SHA-256: `a5d8a88e1a7b531ea00cd383a7aa00f691cada0a1c118e807b48c1949eaab410`;
- migration 0021 SHA-256: `3d39234e504032f9c39de3a5dbd1c9e99c1eae80d4cb24a78e68dca9b25ebb33`;
- W55b ingest envelope SHA-256: `7907994c10a297c1f9410e205dea00a667d85df29d1321ae728dbb49c623fe8b`;
- migration head: `0023_norm_citations`; R-135; roadmap C-2/C-4.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: W55b admits 500 pages and up to 200,000 characters per page and
  20,000,000 per document. Four W59 guards retained a 30-page limit, while
  the full-snapshot candidate retained a 2 MB per-version input ceiling.

### P-01 — frozen W55b page and character bounds

- captured_at: 2026-10-16
- command: `python3 -c 'import json; d=json.load(open("contracts/api/v1/openapi.json")); print(d["components"]["schemas"]["DocumentVersion"]["properties"]["page_count"])'`
- captured_output:
  ```text
  {'type': 'integer', 'minimum': 1, 'maximum': 500}
  ```
- interpretation: the frozen public DocumentVersion bound is 500 pages.

### P-02 — W55b text envelope

- captured_at: 2026-10-16
- command: `rg -n '^MAX_PAGES:|^PAGE_CHARACTERS_MAX:|^DOCUMENT_CHARACTERS_MAX:' src/auditmanager/ingest/envelope.py`
- captured_output:
  ```text
  139:MAX_PAGES: Final[int] = 500
  176:PAGE_CHARACTERS_MAX: Final[int] = 200_000
  185:DOCUMENT_CHARACTERS_MAX: Final[int] = 20_000_000
  ```
- interpretation: comparison snapshot budgets can align with these active
  admission bounds without changing the contract or migration.

### P-03 — stale 30-page refusals at exact base

- captured_at: 2026-10-16
- command: `git grep -n -e 'page_count <= 30' -e 'page_count <=30' 4d9e4f5954a100d93daa33e8b6cc2b53558cfcfa -- src/auditmanager/comparison`
- captured_output:
  ```text
  4d9e4f5954a100d93daa33e8b6cc2b53558cfcfa:src/auditmanager/comparison/finding_match_suggestions.py:221:        or not 1 <= source.page_count <= 30
  4d9e4f5954a100d93daa33e8b6cc2b53558cfcfa:src/auditmanager/comparison/finding_match_suggestions.py:222:        or not 1 <= target.page_count <= 30
  4d9e4f5954a100d93daa33e8b6cc2b53558cfcfa:src/auditmanager/comparison/raw_evidence_seal.py:107:        or not 1 <= source.page_count <= 30
  4d9e4f5954a100d93daa33e8b6cc2b53558cfcfa:src/auditmanager/comparison/raw_evidence_seal.py:108:        or not 1 <= target.page_count <= 30
  4d9e4f5954a100d93daa33e8b6cc2b53558cfcfa:src/auditmanager/comparison/sheet_match_suggestions.py:62:        or type(facts.page_count) is not int or not 1 <= facts.page_count <= 30
  4d9e4f5954a100d93daa33e8b6cc2b53558cfcfa:src/auditmanager/comparison/version_reader.py:97:    if type(page_count) is not int or not 1 <= page_count <= 30:
  ```
- interpretation: changing only the reader and page candidate would leave
  raw evidence and finding matching inconsistent for 500-page versions.

## Historical evidence

- correction_mode: addendum
- source_record: docs/program/tasks/W59-INT-SHEET-MATCH-SUGGESTIONS-02.md at `4d9e4f5954a100d93daa33e8b6cc2b53558cfcfa`
- addendum_path: docs/program/W59-INT-COMPARISON-500-PAGE-01.md

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/comparison/version_reader.py`
- `src/auditmanager/comparison/sheet_match_suggestions.py`
- `src/auditmanager/comparison/raw_evidence_seal.py`
- `src/auditmanager/comparison/finding_match_suggestions.py`
- `tests/integration/comparison/test_version_reader.py`
- `tests/integration/comparison/test_sheet_match_suggestions.py`
- `tests/integration/comparison/test_raw_evidence_seal.py`
- `tests/integration/comparison/test_finding_match_suggestions.py`
- `docs/program/tasks/W59-INT-COMPARISON-500-PAGE-01.md`
- `docs/program/W59-INT-COMPARISON-500-PAGE-01.md`

## Forbidden hotspots

`contracts/**`, migrations, other comparison or section modules, served
routes/API/UI, analysis profiles, DB/S3 adapters, root dependency/lock files,
composition root, global styles, `CURRENT_STATE.md`, refs, tags and Docker.

## Non-goals

No comparison route, live data read, page-text custody, 500 approved links,
larger deterministic raw-diff budget, automatic approval, AI summary,
contract reseal, migration, full gate, deployment or beta claim.

## Deliverables

Four aligned comparison guards, addressed boundary tests, this task and
result addendum. The raw matching and raw-evidence algorithms do not change.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/comparison` — pass;
- Python compilation, frozen checksums, `git diff --check`, exact owned-path
  proof and direct task handoff — pass;
- no Docker, live DB/S3, network or complete gate under R-135.

## Integration contract

The comparison owner can rely on `read_ordered_version_pair` to return
W55b-valid 500-page facts and on the pure suggestion/seal/match guards to
accept page 500. The full text snapshot still requires complete authoritative
page maps and rejects more than 200,000 characters on one page or 20,000,000
per version; UTF-8 hashing encodes only one bounded page at a time. The owner
must obtain consistent version, text and approved-link state transactionally.
This task grants no public comparison behavior or approval authority.

## Failure/idempotency/security cases

501 pages, noninteger counts, missing page text and character overruns refuse.
One page's exact bytes determine its candidate text digest. A repeated call
with equal complete snapshots returns identical ordered suggestions. The
500-page W55b case stays within snapshot bounds even though its UTF-8 bytes
exceed the old 2 MB budget.

## Rollback / feature flag

Revert this one commit to restore the previous preflight behavior. No data,
served behavior or migration changed; no feature flag is needed.

## Handoff

- changed files/checks/risks: accompanying result addendum;
- contracts: unchanged;
- next: comparison owner needs approved-link persistence and a deliberate
  policy for `MAX_PAIRS=32` if a 500-page comparison must cover every page.
