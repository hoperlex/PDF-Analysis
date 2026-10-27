# AR v3 beta activation inputs

Authored 2026-10-27 by lane AR-B (part 1, authoring), task [AR-V3-ACTIVATION-PREP-01](../tasks/AR-V3-ACTIVATION-PREP-01.md), report [AR-V3-ACTIVATION-PREP-01](../AR-V3-ACTIVATION-PREP-01.md). Base `b32c64f3`.

**Honest state.** These files were prepared by an AI lane for the integrator, under the owner's delegation `R-146ba` (accepted risks `A-10` and `A-11` in `PRODUCTION-READINESS-PLAN-01.md`). No subject-matter expert took part. No human compared any norm with its official edition. Nothing in these files says that an edition is current or that a branch applies to a real project, and none of them is an approval. The pack summary built from `decisions.json` stays `pending_expert`: the file has no `review` block, on purpose.

## Files

| File | What it is | State |
| --- | --- | --- |
| `spans.proposal.json` | the sheet's candidate spans (existing, unchanged) | input |
| `decisions.json` | the full decision file `ar-beta-map-decisions-v1` for C01 to C22, `synthetic: false`; the real `map_pack` tool builds six maps from it | **not final**: the six query-vector digests are the placeholder (64 zeros) |
| `query-texts.json` | the 22 query texts (Russian), their topic labels, scope, length and `query_text_sha256` | final as authored |
| `scopes.json` | the skeleton of `v3_pack_cli seal --scopes` | **not final**: the six `map_sha256` values are placeholders |
| `scope-definitions.json` | which items belong to which of the six scopes | final (fixed in code, not a decision) |
| `README.md` | this note | |

Checks: `tests/unit/analysis/ar_v3_norm_map/test_decisions_file_shape.py` (the shape of all four JSON files, 14 provisional and 8 context-only, no currency claim, placeholder state, and a mutation case for every guard).

## «Exclude» does not mean «not sent»

The map tool has **no exclude state**. It needs all 22 items and every item needs at least one target. The owner's «include / revise / exclude» therefore maps like this:

| Owner's word | State in the tool | What the model sees |
| --- | --- | --- |
| include | `provisional_citation` on the proposed span | the span's text, and a citation of it may be shown as a preliminary citation |
| revise | another span (ids from the database; the exporter's `--measure` prints them) | the other span's text |
| exclude | `context_only` | **the span's text is still rendered into the prompt part.** `context_only` only forbids a citation of the span; it does not remove the text from the model's context |

So for the eight policy items (C05 C06 C08 C09 C10 C15 C21 C22) the norm text is sent to the model, as context only. Anyone who reads «exclude» as «not sent» is wrong. The same sentence is in the `comment` of `decisions.json`. Counted by the measure of `AR-V3-BETA-SPANS-MEASURE-01`, the eight context-only items put 2,895 characters of source text (C05, C06, C08, C09, C10, C15: 479 + 713 + 311 + 680 + 268 + 444) and twice 9,205 (C21 and C22) into the prompt parts.

## What was decided here, and the evidence

Every choice, its evidence and what an expert would still have to check is in the [report](../AR-V3-ACTIVATION-PREP-01.md). In short:

- **Modes:** the beta policy of `beta_sources.json` exactly: the eight items above `context_only`, the other fourteen `provisional_citation`. The tool refuses to upgrade the eight; the shape test also pins the other fourteen as `provisional_citation`; changing one means editing the test and recording the reason.
- **Spans:** those of `spans.proposal.json` with the paragraph ids and digests of `AR-V3-BETA-SPANS-MEASURE-01`. C13 and C20 stay separate items on the spans of C12 and C19. **C22 takes D5 ordinals 289 to 300** (a judgement, not a legal fact; the reason is in the report).
- **Edition label:** `редакция локального корпуса (ConsultantPlus), изменения не сверены с официальной редакцией` on every target. `edition_evidence` is empty on all fourteen provisional items: no official page was fetched or compared.
- **Branch:** `N` (new residential construction). The project date is stated as «не задана: бета на синтетических документах (R-146bb)».
- **Designations:** the five «СП» labels of the sheet; for D6 the reader's label of the document, `Федеральный закон от 22.07.2008 N 123-ФЗ (ред. от 25.12.2023)`, not the short «123-ФЗ», because `map_pack validate` demands that a target's designation equals the designation of the exported rows, and the exporter writes the reader's label. This D6 string is **inferred** (see check b below).

## The two placeholders

1. **`decisions.json`, `query_vectors.sha256_by_scope`: 64 zeros for each of F1 F2 A1 A2 S1 S2.** The real tool **accepts** them (it checks only that a digest is 64 lowercase hex characters), so a file with the placeholder left in would build, validate and promote. Two guards stand against that: the `comment` carries the word `PLACEHOLDER` exactly while the zeros are there (the shape test fails if the marker and the state disagree, or if the six digests are partly replaced), and `AR_V3_DECISIONS_REQUIRE_FINAL=1` makes the shape test demand real, distinct digests in `decisions.json` and real map digests in `scopes.json`. Run it before sealing; it fails today, as it should.
   - **Rule proposed for the per-scope digest** (the tool states none; it records the value and never reads it): `sha256_by_scope[S]` is the SHA-256 of the UTF-8 text made of one line `"<item_id> <vector_sha256>\n"` for every item of scope `S` in item order, with `vector_sha256` from the `embed-texts` response. Write the rule into `provenance.json` next to the vectors. The integrator may choose another rule; it must then be written there.
   - When the digests are replaced, also replace the sentence that begins `PLACEHOLDER:` in `comment`, or the shape test fails.
2. **`scopes.json`, six `map_sha256` values** are the text `PLACEHOLDER-NOT-A-DIGEST: ...`, not hex, so `seal` refuses the skeleton (`v3-pack REFUSED spec_value`, verified) instead of looking up sets for invented digests. Replace each with `sha256sum scope-<ID>.map.json` of the pack that `map_pack build` writes. The skeleton holds no set ids: `seal` reads them from the database. `analysis_profile_id` and `prompt_bundle_id` are the constants of `v3_profile.py` (checked by the shape test); `builder_version` is `norm-retrieval-set-prep-v1`, `chunking_profile` is `characters-v2:1200`.

## Making the query vectors from `query-texts.json`

One request per scope (the 512-token limit is checked by `embed-texts`, which refuses and never truncates):

```text
python3 - <<'EOF'
import json
d = json.load(open("docs/program/ar-v3-beta/query-texts.json", encoding="utf-8"))
for scope in ("F1", "F2", "A1", "A2", "S1", "S2"):
    texts = [{"id": q["item_id"], "text": q["text"]} for q in d["queries"] if q["scope_id"] == scope]
    request = {"format": "auditmanager-embed-texts-request/1", "texts": texts}
    open(f".local/ar-v3-draft/embed-{scope}.request.json", "x", encoding="utf-8").write(json.dumps(request, ensure_ascii=False))
EOF
```

Then `python -m auditmanager.norms.embedding embed-texts --in embed-<S>.request.json --out embed-<S>.response.json` in the hash-checked environment. Each response entry's `input_sha256` must equal the item's `query_text_sha256` in `query-texts.json` (the texts are NFC, so the two digests are the same bytes); a difference means the text was altered. The query texts contain no digit, no norm number and no clause number; the longest has 314 characters, the shortest 230 (the length rule and its estimate method are in the file).

## Checks to run right after the paragraph export (before `map_pack build`)

a. **Spans file:** use the 20 distinct triples of `spans.proposal.json`, as in `AR-V3-BETA-SPANS-MEASURE-01`, not the 19 of `decisions.json` (the second C22 candidate, ordinals 301 to 308, is not used here). The extra eight paragraphs do no harm to `build`, and the export then reproduces the recorded 88 rows and the file digest `ca560dc93a074dae5328d8b50591743e52c9e893bdf4ad004fe8667bb0fd99dc`, which is the only available comparison with the earlier read.
b. **Designations:** `export_paragraph_rows.py --measure` prints each document's designation. D1 to D5 must read `СП 1.13130.2020`, `СП 54.13330.2022`, `СП 59.13330.2020`, `СП 50.13330.2024`, `СП 51.13330.2011`. For D6 the string here is inferred from the unit test of `reader_designation` and the measured length (61 characters); if `--measure` prints another string, change the `designation` of the three D6 targets (C05, C08, C10) to it, a text-only change, and rerun the shape test. A wrong label is refused by `map_pack` as `target_designation_mismatch`.
c. **Text digests:** compare the exported spans with the `text_sha256` table of `AR-V3-BETA-SPANS-MEASURE-01`; a difference means the snapshot or its repair state is not the one the ids were taken from.

## The attestation for `seal`

The manifest `review` is five non-empty fields; the screen «Настройки анализа» shows them verbatim with a fixed sentence that the record is attached at installation and is not checked by the system. The honest values (Russian, because users read them), from the feasibility report, section 6:

| Field | Value |
| --- | --- |
| `--reviewer` | `ИИ-интегратор (Claude Code), сессия integration/ar-close-1026` |
| `--capacity` | `ИИ-интегратор по поручению владельца (R-146ba); не эксперт предметной области` |
| `--reviewed-at` | the date the decision file is frozen (`YYYY-MM-DD`) |
| `--decision-ref` | `R-146ba (A-10, A-11); decisions sha256 <digest of the frozen decisions.json>; map digests <first 12 hex of each of the six>` |
| `--scope-statement` | `Подготовлено ИИ-интегратором по поручению владельца; эксперт предметной области не участвовал; нормы не сверены с официальной редакцией человеком. Охват: шесть областей АР v3 (F1 F2 A1 A2 S1 S2), 22 темы C01-C22, 14 тем как предварительная цитата и 8 только как контекст (C05 C06 C08 C09 C10 C15 C21 C22); числовые выводы недоступны.` |

Before sealing, check that the counts in the scope statement still equal the frozen file (14 and 8; the shape test asserts them). The independent two-person check of `promote_cli` is AI to AI here and must not be called expert review. Neither `pack_sha256` nor the loader authenticates the record; file custody is the control (`D-212`). The map-level `review` block of `map_pack` is **not** supplied: no expert reviewed the maps, and `attestation_recorded` would read as the opposite.

```text
DATABASE_URL=... PYTHONPATH=src python -m auditmanager.runs.v3_pack_cli seal \
  --scopes .local/ar-v3-draft/scopes.final.json \
  --reviewer 'ИИ-интегратор (Claude Code), сессия integration/ar-close-1026' \
  --capacity 'ИИ-интегратор по поручению владельца (R-146ba); не эксперт предметной области' \
  --reviewed-at YYYY-MM-DD --decision-ref '<as in the table>' \
  --scope-statement '<as in the table>' --out .local/ar-v3-draft/pack.json
python -m auditmanager.runs.v3_pack_cli verify --manifest .local/ar-v3-draft/pack.json
```

## The order of the remaining steps

Numbers are those of section 8 of [AR-V3-ACTIVATION-FEASIBILITY-01](../AR-V3-ACTIVATION-FEASIBILITY-01.md); step 3 is this directory.

1. **Make room** (at least 1.3 GB, prefer 2.5 GB), record `df -B1 /` before and after.
2. Recapture the premises (`docker ps -a`, `df`, `free`, `git status`) and confirm nobody else started the custody lane.
3. Authoring: **done here**; the two placeholders above are the only open fields.
4. Start `auditmanager-ar-beta-custody-postgres-1`; export the paragraph rows of the 20 spans into `.local/ar-v3-draft/paragraphs.json`; run checks a to c above; stop the container.
5. Optional: fetch and hash the three fetchable evidence PDFs. Until then `edition_evidence` stays empty and `pack-summary.json` lists the fourteen provisional items under `edition_evidence_missing`.
6. Vectors: hash-checked environment, self-check, differential batch check, `embed-texts` per scope (above), `provenance.json`, then delete the weights and the environment.
7. Put the six vector digests into `decisions.json` (and edit the `PLACEHOLDER` sentence); run the shape test with `AR_V3_DECISIONS_REQUIRE_FINAL=1` after also filling `scopes.json`; `map_pack build` (no `review` block) then `validate` with the paragraph file; expect exit 0 and six distinct digests; commit `decisions.json` and `pack-summary.json` (no corpus text).
8. Rehearsal on the custody lane: per scope `promote_cli new-id`, bundle, `plan`; a second, separate AI lane recomputes the digests; `promote`, then the replay.
9. `seal` against the custody lane with the values above, then `verify`; keep `pack.json` under `.local/` (not in git).
10. Owner or administrator, live host: confirm or import and designate the snapshot; repeat `promote` with the same bundles; `plan` must end `verdict: matched`.
11. Owner: `seal` on the live database, install, restart, `verify`, check the status panel.
12. `AR-V3-BETA-ACCEPT-01`.
