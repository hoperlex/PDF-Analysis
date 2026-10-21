# Task CFB-INT-DEV-PUBLISH-35 — integrate W56b saved TEXT preflight

task_id: CFB-INT-DEV-PUBLISH-35

## Outcome

A clean fast-forward `origin/dev` candidate adds an unserved deterministic
whole-page TEXT window preflight with original global Unicode offsets.

## Depends on

- `CFB-INT-DEV-PUBLISH-34` — complete at `b9e26b0c154c1369742fe8124a91f3e5fdf986aa`;
- `W56B-INT-CHUNK-PREFLIGHT-PREP-01` — complete at `d05067f33a69bc7c822f302a5ec36e8c318fd6d4`.

## Frozen inputs

- base commit: `b9e26b0c154c1369742fe8124a91f3e5fdf986aa`
- source parent: `77d39efedd4d5c74582a02dbf5ea86acb4b054f7`;
- source patch SHA-256 `39fdd9b09cf98e0dbc39783aa31fbdba55b09ae5d6271f98e7d738a0ad5d3236`;
- API SHA-256 `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- stage registry SHA-256 `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain IDs SHA-256 `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256 `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head `0023_norm_citations`; `VERSION=0.6.0`; R-135.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: source is a dev33 sibling of dev34, changing four new disjoint
  task-owned paths; a clean cherry-pick preserves its exact patch.

### P-01 — source and integration patch equality

- captured_at: 2026-10-16
- command: `git show --format= --binary ffc66001 | sha256sum`
- captured_output:
  ```text
  39fdd9b09cf98e0dbc39783aa31fbdba55b09ae5d6271f98e7d738a0ad5d3236  -
  ```
- interpretation: the applied four-path patch equals source SHA-256; no
  source payload was edited while integrating.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/W56B-INT-CHUNK-PREFLIGHT-PREP-01.md`
- `docs/program/tasks/W56B-INT-CHUNK-PREFLIGHT-PREP-01.md`
- `src/auditmanager/analysis/text/chunk_preflight.py`
- `tests/integration/analysis_text/test_chunk_preflight.py`
- `docs/program/tasks/CFB-INT-DEV-PUBLISH-35.md`
- `docs/program/CFB-INT-DEV-PUBLISH-35.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

All other paths, especially contracts, migrations, existing analysis
consumers/producers, provider and pricing adapters, composition root, root
dependencies/locks, API/UI, global styles, production DB/S3, `origin/main`,
tags and deployment workflow.

## Non-goals

No model choice, cost ceiling, prompt, overlap, cross-window resolution,
multi-call effect journal, served W56b stage, W54 corpus, W55b deployment or
beta verdict. A character ceiling is caller-supplied, not a safe token budget.

## Deliverables

The exact four-path source patch, this task/report, bounded state update and
direct published-dev SHA readback.

## Required tests

- integrated TEXT preflight, existing grounding, W57a reader/writer and
  programme suites;
- compilation, direct task governance, frozen hashes, patch/path equality,
  whitespace, clean tree, fresh remote fast-forward and readback;
- no Docker/PG/S3 or full gate while W55b owns the host.

## Integration contract

Cherry-pick the exact source patch after dev34 and add only these integration
records. The future W56b caller must bind saved text to a current Run/Attempt,
reserve prompt/context/output capacity, price/journal every effect and define
cross-window citation behavior before activation. A moved remote stops push.

## Failure/idempotency/security cases

Malformed/blank layer, invalid ceiling and any oversized page refuse before
returning a partial plan. Source offsets are never rewritten. Replaying the
same layer and ceiling returns identical windows. No provider is invoked.

## Rollback / feature flag

Remove the additive module and test through a reviewed forward commit if
abandoned; no data rollback or flag applies while unserved.

## Handoff

- changed files: four source paths plus this task, report and state;
- contracts: none; forbidden hotspots unchanged;
- next: W56b freeze for budget/effects/cross-window policy and saved-input proof.
