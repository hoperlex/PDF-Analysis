# Task W57A-INT-CITE-GROUNDING-CORE-01 — ground AR v3 proposals with distinct prompt labels

task_id: W57A-INT-CITE-GROUNDING-CORE-01

## Outcome

One pure, unserved bridge grounds a parsed AR v3 proposal's document evidence
before its normative quote/value claims. A single canonical norm paragraph
can be cited through two distinct prompt labels from different map items
without duplicating its paragraph identity or losing either label.

## Depends on

- `W57A-INT-V3-RESPONSE-PREP-01` — complete at `14219bd29ab61cc22a6bf7f563396d9e3d63ef28`;
- `CFB-INT-DEV-PUBLISH-30` — complete at `f6f19220fa5ae019daae07a3771846e2523ce55a`.

## Frozen inputs

- base commit: `f6f19220fa5ae019daae07a3771846e2523ce55a`;
- API v1 SHA-256: `7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`;
- analysis registry SHA-256: `58d9fa07a1a741e12e99bf2307d50a0d270fb95af957b641b47b18b1256e03d1`;
- domain identifiers SHA-256: `5b41a084d3e6a0e65bfa2dafb14177517b993c9af472ea9c80fdfae4898154b2`;
- error catalogue SHA-256: `918aae4ceb26cca53f35f22aa27b8eba86e590f5f1622a519efcf77d4ec0d9cc`;
- migration head: `0023_norm_citations`, SHA-256 `fd1da93e07d812819e05381b9956e6a288f1cc71f32132f44c78f7b94c5eaa7e`;
- W57 §A3.2–A3.5 and frozen response parser in dev30.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the retrieval set permits repeated canonical paragraphs under
  distinct map-item labels, but the existing grounding function assumes at
  most one label per paragraph.

### P-01 — retrieval selected-key cardinality

- captured_at: 2026-10-16
- command: `sed -n '280,287p' src/auditmanager/norms/retrieval/artifact.py`
- captured_output:
  ```text
    for index, row in enumerate(selection.rows, 1):
        source = by_id.get(row.paragraph_id)
        if row.label != f"N{index}" or source is None:
            raise ArtifactRefused("prompt label or paragraph is invalid")
        selected_key = (row.item_id, row.paragraph_id)
        order = (item_ids.index(row.item_id), row.designation, row.ordinal, row.document_id)
        if selected_key in selected_keys or (last_order is not None and order < last_order):
            raise ArtifactRefused("prompt rows are duplicated or out of order")
  ```
- interpretation: one paragraph can legally occur once per map item, with
  separate `N1`, `N2` labels. This does not assert any qualified live set.

### P-02 — old one-label shape

- captured_at: 2026-10-16
- command: `sed -n '34,39p' src/auditmanager/norms/citation_prep.py`
- captured_output:
  ```text
  class NormParagraph:
      paragraph_id: str
      document_id: str
      text: str
      label: str | None = None
      reliable: bool = True
  ```
- interpretation: the current DTO has only one label. The exact code review
  also showed duplicate paragraph IDs are refused; duplicating the row would
  violate that check. The task separates prompt-label bindings from unique
  canonical paragraph texts.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/W57A-INT-CITE-GROUNDING-CORE-01.md`
- `docs/program/W57A-INT-CITE-GROUNDING-CORE-01.md`
- `src/auditmanager/norms/citation_prep.py`
- `src/auditmanager/norms/public.py`
- `src/auditmanager/analysis/profiles/ar_v3/citation_grounding.py`
- `tests/integration/norms/test_citation_prep.py`
- `tests/integration/analysis/test_ar_v3_citation_grounding.py`

## Forbidden hotspots

- `contracts/**`, `db/migrations/**`, dependency/lock files;
- W56b geometry/crop modules and tests; W56 executor, v1/v2 response and
  publication paths; API routes/schemas, bootstrap composition;
- UI/global styles, `CURRENT_STATE.md`, stand services, remote refs and tags.

## Non-goals

No qualified retrieval set, artifact/custody validator, reviewed map,
registered v3 profile, served reader, DB citation writer, certified zero,
provider call, corpus publication or expert decision.

## Deliverables

Separate label-to-paragraph bindings for the pure norm gate; a pure v3
proposal bridge that first resolves every PDF quote and then invokes the
norm gate; focused failure and repeated-label tests; report.

## Required tests

- `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q tests/integration/norms/test_citation_prep.py tests/integration/analysis/test_ar_v3_citation_grounding.py tests/integration/analysis/test_ar_v3_response_parser.py`;
- `python3 -m py_compile` on changed Python modules; `git diff --check`;
- direct task governance findings `[]`;
- no Docker, PostgreSQL, S3 or full suite while W55b gate holds host resources.

## Integration contract

The caller must first prove its paragraph texts and label bindings came from
the exact pinned, verified retrieval-set bytes and that the Run uses that
set. This pure slice cannot do that DB/custody proof. Its accepted result is
only a candidate for the later atomic CITE publisher. An unresolved PDF quote
or any failed norm citation/value withholds the entire proposal, including
otherwise resolved anchors. A nonnormative accepted proposal has an empty
candidate citation tuple, not a persisted zero certificate.

## Failure/idempotency/security cases

Duplicate labels, duplicate paragraph identities, foreign label targets and
mixed inline/separate label sources refuse. PDF evidence failures precede
norm checks. Pure evaluation is deterministic and has no external effect.

## Rollback / feature flag

The bridge is unserved, so rollback is the bounded commit and no runtime flag
is needed. The old `ground_norm_observation` calling form stays compatible.

## Handoff

- changed files: exact allowlist above;
- commands/results: completion report;
- known limits: no live qualified set or service acceptance;
- integration notes: cherry-pick after dev30; do not serve or publish from this slice.
