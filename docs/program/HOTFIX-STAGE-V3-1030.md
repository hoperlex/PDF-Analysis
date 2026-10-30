# HOTFIX-STAGE-V3-1030 — backend handoff

2026-10-30. Separate `v3_native_text_experimental` engine implements original-source Mapper → Miner → unmatched review → lossless Dedupe → independent parameter verification → preliminary REVIEW cards. It uses existing C3 native text and existing durable stage AI units/jobs/call receipts. Classic stays the default; this is not full original V3 parity.

## Provenance and scope

`src/auditmanager/comparison/stage_v3/original/SOURCE.json` records original repository, commit `3c99481719218b9cfa7560886529916646c61939`, and SHA256 of six byte-identical algorithm modules and five byte-identical prompts. `schemas.py` contains selected pure source excerpts from original `contracts.py`, excluding its runtime imports. New adaptation code performs no original provider/store/job imports. The copied optional environment switch in `dedupe.py` is not consulted: adaptation explicitly selects lossless merging.

The adapter constructs source records from every pinned native TEXT fragment, including fragments excluded as exact matches and unpaired pages. Document/page identities retain original profile/version references; physical ordinals are per-side addressing only. No recognised Markdown, raster, complete table recognition, norms or original filesystem state is claimed.

Hard bounds: 16 source pages total, 80,000 normalised source characters, 400 fragments, eight mapped semantic regions, 64 proposed changes and changed parameters, at most four supplemental and eight verification batches. Out-of-bound or empty native source is refused without truncation. Existing 20,000-character before/after card limits still apply. Meaningful unmatched pages without lexical counterpart remain explicitly pending/partial rather than acquiring invented counterparts.

## Runtime and integration seams

- API1.14 root owns `engine` in start/batch requests and estimate query. `StageChainService.start/estimate` and `StageChainBatchService.start` accept it; previous commands with no engine read as classic. Nonclassic command fingerprints, run input hash, unit source and prompt/consent identity bind engine and copied-source bundle. Batch children inherit persisted batch choice.
- `StageAiRuntime` selects `V3Method` internally; existing factory/registry/work kind remains unchanged. Source/profile/blob/version checks, authority/cancellation checks, current job pin, paid-result persistence, unknown-effect and safe-technical-retry fences remain in the existing caller/runtime. No DDL, migration, new API queue or bootstrap kind is required.
- Start consent estimates one conservative Mapper request. Each additional request requires a fresh explicit LEFT estimate and consent, using existing `overrun` pause/resume. This is one request per consent revision, not an estimate of the complete experiment. At most one dispatch occurs per durable work yield. Accepted replies are reused; a normal procedure boundary never silently sends the next request.
- Existing durable steps 1–3 preserve deterministic source/raw evidence; AI containers 4/5/6 hold Mapper, Miner+unmatched, and Dedupe+verification. Step7 materialises REVIEW cards. Experimental mode does not invoke automatic classic link repair.
- `ChainRun.engine` and `experimental_progress` are dataclass attributes consumed by root API adapter. Progress has `engine`, `source_version`, `procedure`, `status` (`running/completed/partial`), `procedures[{name,state}]`, `coverage`, `limitations`. Names: Mapper, Miner, Разбор непарных страниц, Dedupe, Проверка параметров, Карточки V3. States: queued/running/completed/failed.
- `StageChangeCard.experimental` contains event/source provenance, full engineering subject/summary, `parameters`, quality and coverage, `norms_status=not_checked`, `native_text_only=true`. Each parameter keeps Miner values and independent `verification` verdict/readings. CONFIRMED must agree with Miner values; corrected readings are in `verification.old_value/new_value/unit`. Observations retain unresolved evidence. Shared-source events are explicitly merged with all event/parameter metadata retained.
- Classic artifact reader DTOs remain schema-valid: Mapper never emits fake SAME/MOVED decisions; experimental originals remain available under `model_identity.experimental`. Final REVIEW projection supplies source fragment anchors and never substitutes synthetic raw differences. Expert decisions remain separate; no previous classic decision is automatically carried into experimental materialisation.

## Changed backend paths

- `src/auditmanager/comparison/stage_v3/**`: isolated provenance, copied procedures/schemas/prompts, bounded planner/parser, engine persistence lookup/progress, durable and public-reader adapters.
- `src/auditmanager/comparison/stage_ai/repository.py`: persisted engine lookup and sealed experimental reader envelopes.
- `src/auditmanager/comparison/stage_ai/runtime.py`: engine-specific estimates, plans, parsing and one-request consent window.
- `src/auditmanager/comparison/stage_run/service.py`: engine choice, command/input binding and run projection.
- `src/auditmanager/comparison/stage_run/batch.py`: persisted batch engine propagation.
- `src/auditmanager/comparison/stage_run/handler.py`: preserve experimental map/raw source by avoiding classic automatic link repair.
- `src/auditmanager/comparison/stage_review/cards.py`: explicit opt-out of classic uncovered-raw fallback.
- `src/auditmanager/comparison/stage_review/service.py`: fragment-backed experimental cards and metadata projection.
- `tests/unit/stage_v3/{recorded_fixture.py,test_procedures.py,test_lifecycle.py,db_smoke.py}`.
- This report and the task handoff section. No API, contracts, locks, bootstrap, migration or UI file was edited by this backend lane. Root/other granted owners edit their separate paths in the shared tree.

## Checks and remaining evidence

` .venv/bin/python -m pytest tests/unit/stage_v3 tests/unit/comparison/stage_ai tests/unit/comparison/stage_review/test_cards_and_writers.py -q --tb=short `: **95 passed in1.75s**. This includes original four-call source-bound synthetic pipeline, actual runtime branch with four calls/three fresh consent windows and saved replay, actual unmatched supplemental batches, copied-byte hashes, source/ref/quotation/verification rejection, unchanged raw evidence, classic runtime/graphic/recovery behavior and Pydantic validation of all three public artifact envelopes. Compile checks of the four changed comparison packages passed earlier; final scope is compiled again by integrator if desired.

`recorded_fixture.synthetic_response(request)` is reusable by an explicitly synthetic demo helper, has no I/O/network/provider selection, and fails on unknown procedure. It returns valid copied schemas based on supplied source blocks; synthetic labels explicitly deny an engineering conclusion. It is not a real model benchmark.

The explicitly invoked `db_smoke.py` uses the existing assigned58060 database, an outer transaction and nested savepoint sessions. First run exposed and fixed START-versus-LEFT estimate drift. A subsequent run was refused by automatic approval review with the exact reason:

> The prior run already showed persistent account/profile and role mutations despite the claimed rollback, including credential refusal; rerunning the same smoke script against the shared PostgreSQL instance risks repeating irreversible database side effects that the user did not specifically authorize.

Read-only SELECT then proved both the exact synthetic actor and smoke-login row counts were zero; the helper source confirms it does not commit itself. After that evidence the reviewer allowed one retry. It stopped before model dispatch because the test Adapter lacked `provider_mode`; that fixture was corrected to explicit RECORDED but not rerun, following integrator direction. Consequently **no PostgreSQL end-to-end PASS is claimed**. The shared58060/62060/62061 slot was released. No full gate/build/browser/real-model call was run by this lane. Live-provider behavior, semantic accuracy, full original V3 coverage, raster/table handling and subject-matter verification remain unmeasured.

Root alone integrates/commits/publishes development. UI belongs to its separately assigned owner. Disable the experimental selector for new runs to roll back exposure; retained engine/source/receipt metadata permits reading existing experimental runs without relabelling them classic.
