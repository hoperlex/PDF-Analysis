# AR original prompt and database citations — implementation map

**Task:** `AR-ORIGINAL-CITATIONS-PLAN-01`. **Read at:** local `origin/dev` `7a2270fa` on 2026-10-22. This is a planning record, not a released AR profile or a citation verdict.

## Facts that fix the scope

1. The original is the six-file AR source in `/root/projects/PDF-proverka`, identified and hashed by `W56A-LEGACY-SOURCE-01`. Its role asks an architect to review residential AR, including layout, facades, roof, fire, accessibility, light, acoustic and thermal topics. Its checklist embeds numbers and clause names that have **not** been verified against the present normative corpus. Those values cannot become product rules by copying the file.
2. The served section registry still maps AR to the narrow v1 text-consistency profile (`analysis/text/profile_registry.py`). The reviewed original topics exist in six `analysis/profiles/ar_v2/*.md` files, but v2 is recorded only and v3's prompt, response and grounding modules are draft/unserved. Changing the v1 prompt in place would change its content hash and invalidate historical recordings; the live successor needs a new profile and bundle identity.
3. The Run pins `norms_snapshot_id`; migration 0023 also added nullable `norm_retrieval_set_id`, canonical citation tables and custody constraints. The Run creation path does not bind a retrieval set, and `runs/executor.py` does not consume one. `norms/retrieval/**` supplies pure candidate, ranking, qualification and evidence readers but no served promotion/selection workflow. A normative quotation is therefore not yet sent to the model from this database path.
4. The existing W57a design (`dispatch/W57-PLAN.md` §A3) requires a reviewed map, qualified set, request budget and local citation grounding. The current stand corpus import and snapshot designation remain separate operational prerequisites.

## Ordered code slices

| Slice | Result and owner | Exact acceptance boundary |
| --- | --- | --- |
| `AR-NORM-MAP-01` | A reviewed map from the original AR checklist's *topics* to canonical DB paragraph identities and editions; one owner for the map and its review record. Reuse `norms/retrieval/{targets,source_reader,qualification_reader,qualification_decision}.py`. | Every included item has a quoted source topic, current corpus document/paragraph identity and applicability note; every original threshold or absent corpus document is excluded explicitly. No model call. |
| `AR-SET-PROMOTION-01` | One owner for the Run/set persistence and `norms/public.py` cross-context read port. Build and custody-verify a retrieval set for the pinned snapshot, persist its canonical bytes and Blob binding, and bind its id to a Run **before** dispatch. | DB and Blob evidence agree; mismatched snapshot, map, build or digest refuses before any external effect; exact replay is idempotent. No router SQL or dual write. |
| `AR-PROMPT-RUNTIME-01` | One owner for `analysis/profiles/ar_v3/**`, `analysis/text/profile_registry.py`, the Run executor and composition wiring. Register new AR profile/bundle IDs; render the reviewed original topics and only labelled canonical paragraphs of the Run's verified set into a bounded request. The same request payload reaches HTTP, pull and SSH executors. | A recorded model adapter captures the exact system/user payload and its digest; changing document, snapshot or set changes the request; an old v1 Run still resolves its old bundle; missing set refuses, never falls back to v1. No unverified number is an instruction. |
| `AR-CITE-PUBLISH-01` | One owner for local grounding and the existing 0023 citation publisher/read model. Compare the model's proposed label, quote and values to the exact canonical paragraph and PDF text, then write only accepted observations. | A wrong label, quote, value, edition or scope withholds the whole normative observation with a counted reason; raw deterministic comparison evidence is unchanged; expert decision remains an expert event. `getRunNormVerification` stops answering a placeholder only after a verified reader exists. |
| `AR-RELEASE-ACCEPT-01` | Integration owner freezes one candidate and runs its complete gate, recorded/DB/S3 journey and paid live samples only with the owner's provider window. | Exact `GATE OK`, a built-stand AR journey with a real pinned snapshot, citation opened back to its canonical paragraph and source PDF, and cost/model identity evidence; no release claim from a unit recording alone. |

Each code task must be frozen from the fresh integrated tree after the currently in-flight PDF, EXEC and edge branches. The contract/migration, composition-root and profile identity slots are assigned to exactly one task at a time; the table does not grant them. `AR-NORM-MAP-01` and `AR-SET-PROMOTION-01` precede `AR-PROMPT-RUNTIME-01`; publication follows runtime and grounding. The current `R-135` development cadence permits bounded lane tests, while any `origin/main` update still follows `AGENTS.md` §6 and `MAIN_AUTODEPLOY_POLICY.md` for an exact gated SHA.

## Integration risks

- The original checklist's named norms and numerical thresholds are source history, not verified legal requirements. A model may propose an observation from the supplied current paragraphs; only deterministic grounding can make its citation publishable.
- Stand import and designation of the 674-document snapshot have not run; without them, a stand cannot pass the AR normative journey.
- The `1.1.0` contract label attempt is parked with red seal tests. Runtime work must keep the currently frozen `1.0.0` contract or get an explicit reseal owner; no opportunistic label edit.
- The current executor candidate 2 adds migration 0031 and overlaps `infra` with edge. Re-freeze all counts and migration head after their integration; do not reuse this report's base numbers as future task inputs.

## Checks and hotspot proof

Read-only inspection covered the original source, the six reviewed resources, served profile registry, Run creation/executor, migration 0023, `norms/retrieval/**` and W57a plan. Only this report and its task file are written. No contract, migration, runtime, dependency, composition root, style, ref or stand is changed by this slice.
