# Task W59-INT-SHEET-MATCH-SUGGESTIONS-02 — conservative sheet-pair candidates

task_id: W59-INT-SHEET-MATCH-SUGGESTIONS-02

## Outcome

A pure, unserved comparison function proposes a page pair only when complete
source and target page-text snapshots contain one identical nonblank page on
each side. It returns a digest-bound suggestion without creating or approving
a SheetLink. Addressable tests prove moved-page matching and abstention.

## Depends on

- `W59-INT-VERSION-PAIR-READ-01` — completed same-set ordered version reader.
- `W59-INT-VERSION-RAW-TEXT-PREP-01` — completed approved-link raw diff seam.
- `CODE-FIRST-SCOPE-01` — completed W59 comparison scope map.

## Frozen inputs

- base commit: `45d5772480f62006b430151d464a7f7200be511b`
- source: `origin/dev` development candidate 39;
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- domain identifiers SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalog SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- W58–W63 scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- ADR-0013 SHA-256: `a5d8a88e1a7b531ea00cd383a7aa00f691cada0a1c118e807b48c1949eaab410`;
- migration head: `0023_norm_citations`; roadmap C-2, R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the frozen comparison package can diff only caller-supplied approved
  links, while ADR-0013 calls for rebuildable automatic sheet suggestions.

### P-01 — comparison implementation at frozen base

- captured_at: 2026-10-16
- command: `git ls-tree -r --name-only HEAD src/auditmanager/comparison`
- captured_output:
  ```text
  src/auditmanager/comparison/README.md
  src/auditmanager/comparison/decision_carryover.py
  src/auditmanager/comparison/finding_match_suggestions.py
  src/auditmanager/comparison/raw_evidence_seal.py
  src/auditmanager/comparison/raw_text.py
  src/auditmanager/comparison/summary_input.py
  src/auditmanager/comparison/version_reader.py
  ```
- interpretation: there is no sheet-pair suggestion implementation; this
  inventory gives no grant to persist approved links or activate a route.

### P-02 — adopted comparison boundary

- captured_at: 2026-10-16
- command: `rg -n '^Automatic sheet matching|^\\| C-2 ' docs/architecture/adr/ADR-0013-comparison-evidence-layers.md docs/program/dispatch/ROADMAP-TO-BETA.md`
- captured_output:
  ```text
  docs/program/dispatch/ROADMAP-TO-BETA.md:449:| C-2 | depth for documents | **text + AI summary**: sheet pairing, deterministic text differences as evidence, AI classification and summary on top; AI never alters the raw differences |
  docs/architecture/adr/ADR-0013-comparison-evidence-layers.md:6:Automatic sheet matching produces rebuildable suggestions. User-approved links are owned state and survive recomputation. Deterministic text exclusions/diff and raw graphic evidence are immutable per comparison revision. AI review/synthesis is a derived artifact keyed by raw checksums. Repairs require proof, audit and undo.
  ```
- interpretation: suggestions are explicitly separate from owned approval;
  exact full-page equality is a conservative candidate policy, not acceptance.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/comparison/sheet_match_suggestions.py`
- `tests/integration/comparison/test_sheet_match_suggestions.py`
- `docs/program/tasks/W59-INT-SHEET-MATCH-SUGGESTIONS-02.md`
- `docs/program/W59-INT-SHEET-MATCH-SUGGESTIONS-02.md`

## Forbidden hotspots

`contracts/**`, migrations, existing comparison and section modules, router,
API/UI, analysis profiles, DB/S3 adapters, root dependency/lock files,
composition root, global styles, `CURRENT_STATE.md`, refs, tags and Docker.

## Non-goals

No OCR or graphic pairing, filename/title matching, fuzzy/AI matching,
automatic approval, SheetLink identity, persisted comparison, route, expert
decision, raw evidence mutation, live DB/S3 access, full gate or beta claim.

## Deliverables

One additive pure module, refusal tests, this task and a result report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/comparison/test_sheet_match_suggestions.py tests/integration/comparison/test_raw_text.py tests/integration/comparison/test_finding_match_suggestions.py` — pass;
- Python compilation, frozen SHA checks, `git diff --check`, exact allowed-path
  proof and direct task handoff — pass;
- no Docker, live DB/S3, network or complete gate under R-135.

## Integration contract

The W59 comparison owner loads the authoritative ordered version pair and
complete text of every page under a consistent snapshot. This function returns
rebuildable candidates only; it cannot prove the page-text custody or approve
a link. An expert must explicitly approve a pair and the owner persists its
SheetLink revision before passing that approved link to `diff_approved_pairs`.
The candidate digest binds both immutable PDF checksums and exact text bytes,
but is not an authorization token. Recomputing candidates must not remove
already approved links.

## Failure/idempotency/security cases

Invalid IDs, reversed versions, incomplete or oversized snapshots, invalid
UTF-8 and mismatched version facts refuse. Identical text repeated on either
side yields no candidate; changed or blank pages also yield none. Map order
does not change results; repeated exact inputs return identical digests.

## Rollback / feature flag

Remove the four additive paths before integration. No active behavior or data
changed, so no feature flag or data rollback is needed.

## Handoff

- changed files/checks/limits: accompanying result report;
- contracts: none;
- next: W59 comparison owner, after SECTION-SEAL, adds authoritative complete
  page reads, expert approved-link state and immutable raw evidence storage.
