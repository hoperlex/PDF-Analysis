# Task W59-INT-SHEET-SNAPSHOT-BOUNDS-03 — bound sheet text before UTF-8 encoding

task_id: W59-INT-SHEET-SNAPSHOT-BOUNDS-03

## Outcome

The unserved W59 exact sheet suggestion refuses an over-budget page or
aggregate snapshot before encoding that page. Valid pages at the W55b
character ceilings retain their exact prior digests and candidate order.

## Depends on

- `W59-INT-SHEET-MATCH-SUGGESTIONS-02` — completed exact full-page candidates.
- `W59-INT-COMPARISON-500-PAGE-01` — completed 500-page and W55b text bounds.

## Frozen inputs

- base commit: `7b56cb451946d250b1030f61150a4979dbcfc157`
- API SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- domain identifiers SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- stage registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- W55b ingest envelope SHA-256: `7907994c10a297c1f9410e205dea00a667d85df29d1321ae728dbb49c623fe8b`;
- W58–W63 scope SHA-256: `81cc57b54e519caa9b284e48565dda5642ecaf228f3b7237ab7e9f7e22c62dee`;
- ADR-0013 SHA-256: `a5d8a88e1a7b531ea00cd383a7aa00f691cada0a1c118e807b48c1949eaab410`;
- migration head: `0023_norm_citations`; R-135; roadmap C-2.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: `_page_digests` encodes each page before applying either character
  ceiling, so an oversized supplied page can allocate an unbounded temporary
  UTF-8 buffer even though the previous task describes an 800 KB maximum.

### P-01 — encode precedes both bounds at the exact base

- captured_at: 2026-10-16
- command: `rg -n -F -e 'encoded = value.encode("utf-8")' -e 'if len(value) > MAX_SNAPSHOT_PAGE_CHARACTERS:' -e 'if total_characters > MAX_SNAPSHOT_CHARACTERS:' src/auditmanager/comparison/sheet_match_suggestions.py`
- captured_output:
  ```text
  92:            encoded = value.encode("utf-8")
  95:        if len(value) > MAX_SNAPSHOT_PAGE_CHARACTERS:
  98:        if total_characters > MAX_SNAPSHOT_CHARACTERS:
  ```
- interpretation: both limits are checked too late for the UTF-8 scratch
  allocation; this does not establish a runtime exposure because the function
  is not served.

### P-02 — frozen scratch-buffer claim

- captured_at: 2026-10-16
- command: `rg -n -F 'hashing scratch buffer' src/auditmanager/comparison/sheet_match_suggestions.py`
- captured_output:
  ```text
  32:# hashing scratch buffer is at most 800k bytes. The caller retains the maps.
  ```
- interpretation: enforcing both character limits before encoding makes the
  claimed bound true for ordinary Unicode strings.

## Historical evidence

- correction_mode: addendum
- source_record: `docs/program/W59-INT-COMPARISON-500-PAGE-01.md` at base commit
- addendum_path: `docs/program/W59-INT-SHEET-SNAPSHOT-BOUNDS-03.md`

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/comparison/sheet_match_suggestions.py`
- `tests/integration/comparison/test_sheet_match_suggestions.py`
- `docs/program/tasks/W59-INT-SHEET-SNAPSHOT-BOUNDS-03.md`
- `docs/program/W59-INT-SHEET-SNAPSHOT-BOUNDS-03.md`

## Forbidden hotspots

`contracts/**`, migrations, other comparison or section modules, served
routes/API/UI, analysis profiles, DB/S3 adapters, root dependency/lock files,
composition root, global styles, `CURRENT_STATE.md`, refs, tags and Docker.

## Non-goals

No new text ceiling, candidate matching algorithm, page-text custody,
approval persistence, raw diff budget, section seal, runtime wiring, full
gate, deployment or beta claim.

## Deliverables

An order-of-check fix, focused regression that proves no encode on refusal,
boundary digest stability tests, this task and result addendum.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/comparison` — pass;
- Python compilation, frozen SHA readback, direct task governance, exact
  owned-path proof and `git diff --check` — pass;
- no Docker, live DB/S3, network or complete gate under R-135.

## Integration contract

The same complete authoritative page maps and ordered version pair yield the
same suggestions and digests as before when within the W55b limits. Each
page's character and aggregate budget are checked before UTF-8 encoding.
Invalid UTF-8 within bounds still refuses. This grants no SheetLink approval
or served comparison behavior.

## Failure/idempotency/security cases

An over-limit source or target page refuses before encoding; an aggregate
overrun refuses before encoding the page that crosses the total. Exact-limit
valid Unicode is encoded, hashed and repeatable. Incomplete maps, invalid
Unicode, ambiguous duplicates and nonblank matching semantics remain as before.

## Rollback / feature flag

Revert this source commit to restore the earlier check order. No persisted or
served behavior changes, so no feature flag or data rollback is needed.

## Handoff

- changed files/checks/risks: accompanying result addendum;
- contracts: unchanged;
- next: integrate after completed W59 comparison preflight; preserve its
  unserved status and separate approved-link policy.
