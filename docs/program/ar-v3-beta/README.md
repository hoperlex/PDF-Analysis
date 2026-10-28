# AR v3 beta activation inputs

Authored 2026-10-27 by lane AR-B (part 1, authoring), task [AR-V3-ACTIVATION-PREP-01](../tasks/AR-V3-ACTIVATION-PREP-01.md), report [AR-V3-ACTIVATION-PREP-01](../AR-V3-ACTIVATION-PREP-01.md). Base `b32c64f3`. **Brought up to date 2026-10-28 (`AR-V3-JUDGE-FIXES-01`):** the two placeholders below were filled by commits `4561f63f` (query vectors, digests in `decisions.json`) and `cb7a34d3` (six scope maps, digests in `scopes.json`); the promotions, the sealed custody-lane pack and the live-host steps are in [AR-V3-PROMOTE-01](../AR-V3-PROMOTE-01.md) and [AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01](../AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01.md). The sections that describe a step as pending say so no longer; each carries its state.

**Honest state.** These files were prepared by an AI lane for the integrator, under the owner's delegation `R-146ba` (accepted risks `A-10` and `A-11` in `PRODUCTION-READINESS-PLAN-01.md`). No subject-matter expert took part. No human compared any norm with its official edition. Nothing in these files says that an edition is current or that a branch applies to a real project, and none of them is an approval. The pack summary built from `decisions.json` stays `pending_expert`: the file has no `review` block, on purpose.

## Files

| File | What it is | State |
| --- | --- | --- |
| `spans.proposal.json` | the sheet's candidate spans (existing, unchanged) | input |
| `decisions.json` | the full decision file `ar-beta-map-decisions-v1` for C01 to C22, `synthetic: false`; the real `map_pack` tool builds six maps from it | **final** since `4561f63f`: the six query-vector digests are the real, distinct ones (rule in `vectors-provenance.json`); `AR_V3_DECISIONS_REQUIRE_FINAL=1` passes; no `review` block, by design |
| `query-texts.json` | the 22 query texts (Russian), their topic labels, scope, length and `query_text_sha256` | final as authored; the vectors were made from exactly these texts |
| `vectors-provenance.json` | how the 22 query vectors were made (hash-checked environment, self-check, differential check against the image-built batch), the per-scope digest rule, the per-item vector digests and the **measured token counts** (maximum 86, item C05, against the limit of 512); no vector is stored | final (`4561f63f`) |
| `scopes.json` | the input of `v3_pack_cli seal --scopes` | **final** since `cb7a34d3`: the six distinct `map_sha256` of the validated maps |
| `pack-summary.json` | the summary `map_pack` builds from the six maps; stays `pending_expert` | final (`cb7a34d3`) |
| `scope-definitions.json` | which items belong to which of the six scopes | final (fixed in code, not a decision) |
| `README.md` | this note | |

Checks: `tests/unit/analysis/ar_v3_norm_map/test_decisions_file_shape.py` (the shape of the JSON files, 14 provisional and 8 context-only, no currency claim, the final state of the digests and the marker, and a mutation case for every guard).

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
- **Designations:** the five «СП» labels of the sheet; for D6 the reader's label of the document, `Федеральный закон от 22.07.2008 N 123-ФЗ (ред. от 25.12.2023)`, not the short «123-ФЗ», because `map_pack validate` demands that a target's designation equals the designation of the exported rows, and the exporter writes the reader's label. This D6 string was first inferred; it is now **confirmed**: the paragraph export prints it (`export_paragraph_rows.py --measure`: 61 characters) and `map_pack validate` against the exported rows, which demands equality with the exporter's label, passed for all six maps (`cb7a34d3`); `AR-V3-PROMOTE-01` section 3(d) checked that the map, the request and the decision file carry one and the same designation per document. This lane did not re-run the exporter.

## The two placeholders — both filled (history)

1. **`decisions.json`, `query_vectors.sha256_by_scope`**: the 64 zeros were replaced by `4561f63f` with the six real digests, and the `PLACEHOLDER:` sentence of `comment` was replaced with the sentence that names `vectors-provenance.json`; the shape test and `AR_V3_DECISIONS_REQUIRE_FINAL=1` pass. The rule that was proposed here for the per-scope digest was adopted and is recorded as `per_scope_digest_rule` in `vectors-provenance.json`: `sha256_by_scope[S]` is the SHA-256 of the UTF-8 text made of one line `"<item_id> <vector_sha256>\n"` for every item of scope `S` in item order, with `vector_sha256` from the `embed-texts` response. The real tool never reads the value (it only checks 64 lowercase hex characters), which is why the two guards (the marker and the REQUIRE_FINAL switch) existed.
2. **`scopes.json`, the six `map_sha256`**: the `PLACEHOLDER-NOT-A-DIGEST: ...` texts were replaced by `cb7a34d3` with `sha256sum scope-<ID>.map.json` of the pack that `map_pack build` wrote (F1 `6ef3303ad6b3…`, F2 `56ee1c26e79c…`, A1 `4b7c2f9d490f…`, A2 `5e97bcc69091…`, S1 `4502cb676a47…`, S2 `547aea97e556…`). The skeleton holds no set ids: `seal` reads them from the database. `analysis_profile_id` and `prompt_bundle_id` are the constants of `v3_profile.py` (checked by the shape test); `builder_version` is `norm-retrieval-set-prep-v1`, `chunking_profile` is `characters-v2:1200`.

## Making the query vectors from `query-texts.json` (done 2026-10-27; the procedure, for a repeat)

The vectors exist (record: `vectors-provenance.json`; weights and environment were deleted after use). One request per scope (the 512-token limit is checked by `embed-texts`, which refuses and never truncates):

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

Then `python -m auditmanager.norms.embedding embed-texts --in embed-<S>.request.json --out embed-<S>.response.json` in the hash-checked environment. Each response entry's `input_sha256` must equal the item's `query_text_sha256` in `query-texts.json` (the texts are NFC, so the two digests are the same bytes); a difference means the text was altered. The query texts contain no digit, no norm number and no clause number; the longest has 314 characters, the shortest 230 (the length rule is in the file). The tokens were estimated from the characters when the texts were authored and **measured** in the vector run: `token_count_by_item` in `vectors-provenance.json`, maximum 86 (C05).

## Checks that followed the paragraph export (before `map_pack build`; done 2026-10-27, `cb7a34d3`)

They are kept as the procedure for a repeat. The recorded outcome: 88 rows, file digest `ca560dc9…99dc` equal to the earlier read; `map_pack validate` exit 0 with six distinct map digests.

a. **Spans file:** use the 20 distinct triples of `spans.proposal.json`, as in `AR-V3-BETA-SPANS-MEASURE-01`, not the 19 of `decisions.json` (the second C22 candidate, ordinals 301 to 308, is not used here). The extra eight paragraphs do no harm to `build`, and the export then reproduces the recorded 88 rows and the file digest `ca560dc93a074dae5328d8b50591743e52c9e893bdf4ad004fe8667bb0fd99dc`, which is the only available comparison with the earlier read.
b. **Designations:** `export_paragraph_rows.py --measure` prints each document's designation. D1 to D5 must read `СП 1.13130.2020`, `СП 54.13330.2022`, `СП 59.13330.2020`, `СП 50.13330.2024`, `СП 51.13330.2011`. D6 reads `Федеральный закон от 22.07.2008 N 123-ФЗ (ред. от 25.12.2023)` (61 characters; it was inferred from the unit test of `reader_designation` before the export and is confirmed by it); if a repeat prints another string, change the `designation` of the three D6 targets (C05, C08, C10) to it, a text-only change, and rerun the shape test. A wrong label is refused by `map_pack` as `target_designation_mismatch`.
c. **Text digests:** compare the exported spans with the `text_sha256` table of `AR-V3-BETA-SPANS-MEASURE-01`; a difference means the snapshot or its repair state is not the one the ids were taken from.

## The attestation for `seal`

The manifest `review` is five non-empty fields; the screen «Настройки анализа» shows them verbatim with a fixed sentence that the record is attached at installation and is not checked by the system. **The values are in one place: [AR-V3-PROMOTE-01](../AR-V3-PROMOTE-01.md) section 6a «Seal values for the live host»** (Russian, because users read them). This file no longer repeats them: the first draft of the scope statement said «числовые выводы недоступны» (the system withholds only `required_value` and `stated_value`; the model's sentences and the norm quote are served and may carry figures) and «независимая проверка карт, векторов и сводных значений» (the vectors were not re-derived), and it lacked the clause that the independent check was AI to AI («ИИ проверяет ИИ»); section 6a has all three corrected. The independent two-person check of `promote_cli` is AI to AI here and must not be called expert review. Neither `pack_sha256` nor the loader authenticates the record; file custody is the control (`D-212`). The map-level `review` block of `map_pack` is **not** supplied: no expert reviewed the maps, and `attestation_recorded` would read as the opposite.

Before sealing, check that the counts in the scope statement still equal the frozen file (14 and 8; the shape test asserts them). On the live host the command runs inside a one-off `api` container, not from a checkout: see [AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01](../AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01.md) «Where the commands of steps 10b and 11 run». On a development host with the database reachable the form is:

```text
DATABASE_URL=... PYTHONPATH=src python -m auditmanager.runs.v3_pack_cli seal \
  --scopes docs/program/ar-v3-beta/scopes.json \
  --reviewer '<section 6a>' --capacity '<section 6a>' \
  --reviewed-at YYYY-MM-DD --decision-ref '<section 6a>' \
  --scope-statement '<section 6a>' --out .local/ar-v3-draft/pack.json
python -m auditmanager.runs.v3_pack_cli verify --manifest .local/ar-v3-draft/pack.json
```

## The order of the steps and where each stands

Numbers are those of section 8 of [AR-V3-ACTIVATION-FEASIBILITY-01](../AR-V3-ACTIVATION-FEASIBILITY-01.md); step 3 is this directory.

1. **Make room** (at least 1.3 GB, prefer 2.5 GB), record `df -B1 /` before and after. *Preparation of the development host; the steps after it ran (`DEBT_REGISTER.md` D-247).*
2. Recapture the premises (`docker ps -a`, `df`, `free`, `git status`) and confirm nobody else started the custody lane. *Preparation; superseded by the runs that followed.*
3. Authoring: **done** (this directory).
4. Start `auditmanager-ar-beta-custody-postgres-1`; export the paragraph rows of the 20 spans into `.local/ar-v3-draft/paragraphs.json`; run checks a to c above; stop the container. *Done (`cb7a34d3`).*
5. Optional: fetch and hash the three fetchable evidence PDFs. *Not done:* `edition_evidence` stays empty and `pack-summary.json` lists the fourteen provisional items under `edition_evidence_missing`.
6. Vectors: hash-checked environment, self-check, differential batch check, `embed-texts` per scope (above), the provenance record, then delete the weights and the environment. *Done (`4561f63f`, `vectors-provenance.json`).*
7. Put the six vector digests into `decisions.json`; run the shape test with `AR_V3_DECISIONS_REQUIRE_FINAL=1`; `map_pack build` (no `review` block) then `validate` with the paragraph file; commit `decisions.json` and `pack-summary.json` (no corpus text). *Done.*
8. Rehearsal on the custody lane: per scope `promote_cli new-id`, bundle, `plan`; a second, separate AI lane recomputes the digests; `promote`, then the replay. *Done (`AR-V3-PROMOTE-REHEARSAL-01`, `AR-V3-PROMOTE-01`).*
9. `seal` against the custody lane, then `verify`; keep `pack.json` under `.local/` (not in git). *Done; that file names the custody lane's sets and is not installable.*
10. Owner or administrator, live host: confirm or import and designate the snapshot; repeat `promote` with the same bundles; `plan` must end `verdict: matched`. **Pending**: [AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01](../AR-V3-LIVE-ACTIVATION-OWNER-STEPS-01.md), steps 10a and 10b.
11. Owner: `seal` on the live database with the values of [AR-V3-PROMOTE-01](../AR-V3-PROMOTE-01.md) section 6a, install, apply (`up -d`, not `restart`), `verify`, check the status panel. **Pending**: the same file, step 11 and its rollback.
12. `AR-V3-BETA-ACCEPT-01`. **Pending.**
