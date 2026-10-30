# CMP-STAGE-GRAPHIC-01 — stage profile GRAPHIC bridge

Completed 2026-10-30 on `agent/cmp-stage-graphic-01`, base `646a9e17`. Root alone integrates/wires/publishes. Full gates and heavy windows are deferred by the owner's 2026-10-30 instruction.

## Result and interface

`from auditmanager.comparison.stage_graphic import StageGraphicService, GraphicCrop`

- `StageGraphicService(sessions, *, blob_store, runner=None, material=None)` assigns dependencies without constructor I/O.
- `advance(item, run_id) -> dict[str,int] | Yielded | Failed` processes at most one effective-map link. It returns Yielded until all links have immutable receipts, then counts `graphic_total`, `graphic_reliable`, `graphic_unreliable`, `graphic_not_checked`, `graphic_regions`.
- `page(run_id, after=None, limit=100) -> (tuple[dict], next_content_key)` returns frozen StageGraphicEvidence DTO dictionaries including explicit unchecked statuses.
- `evidence(run_id) -> tuple[dict]` returns reliable nonempty atomic sge evidence IDs, complete sorted raw regions and source profile identities.
- `crop_plan(run_id, evidence_id, after=None, limit=4) -> (tuple[dict], next_region_key)` pages at most four regions/eight source images. The cursor exposes remaining work; no region is silently discarded.
- `crop(run_id, evidence_id, region_key, side, long_side_px=1400) -> GraphicCrop` returns `evidence_id,region_key,side,profile_id,box,data,sha256`. `data` is PNG; `box` is native displayed-page points from the top-left corner.

The existing public `compare_sheet_pair` accepts profile identities directly. It produces a real cached `comparison_sheet_pair_result_id`; no ComparisonSheetPairId, transition or fabricated identity is required. Existing engine publication owns mask/blob custody; the stage transaction adds only a database reference and raw region projection. A crash after engine publication leaves a reusable valid cache result.

Only degree-one ready paired links with unambiguous mapping reach the engine. One-sided links, many-to-many links, uncertain links and unavailable profiles get explicit `not_checked` receipts. Render refusal, unreliable/partial registration, partial coverage and unchecked geometry/color never yield reliable graphic evidence. Text-only regions are not relabelled as graphics. A checked result with zero non-text regions is explicitly `graphics_compared_no_regions`.

Raw region records preserve `region_class`, `layer`, `raw_difference`, `left_box`, `right_box`, clipping flags and registration proof: actual result ID/content key/algorithm/profile sources, transform, its B→A direction, coordinate frame, channels and engine refusal reasons. Right crops use the inverse transform to the native right profile, not the left canvas box. The engine's content cache may belong to equivalent page profiles in the same project; the expected engine content key is verified before using its row.

Every stage publication proves the live work lease, project, stages module, closed `stage_chain` kind, payload run identity, full/running state and current effective map/version pins. Existing pair-map advisory locks fence map changes only in short DB transactions. Replays bind run/link/profile content/degree/confidence/engine version and never rerun a completed link. AI interpretation is neither called nor stored as raw evidence.

Source crops reuse `ProfileMaterial` and `PageProfileReader` tile-pyramid seams. The caller chooses only a persisted region/side, never an arbitrary profile/path/box. Crops are bounded to 128..1950 pixels on the long side and 2 MiB PNG; unavailable/budget-exceeding images refuse explicitly.

## Focused evidence

- Unit geometry/policy suite: **12 passed** (inverse rotation/translation, singular transform, exact source frames, deterministic region identities, reliable-empty versus unrun, alignment/render/degree/link refusals).
- C4 database service tests: **2 passed** (one-link yielding, durable unchecked records, foreign work refusal, real engine-result FK, replay, exact source crop lookup and scope). The API page/pagination followup uses the same two tests.
- Actual engine smoke: **1 passed in 4.79 s**. Two single-page extracts of synthetic VS-1 E02 V2→V3 were published and profiled by the real children, compared by the real engine, materialized as reliable nonempty GRAPHIC evidence, and cropped from both source profiles. A second advance did not start a child.
- Assigned local PostgreSQL 58040 / S3 62040 only; no live model call, whole battery, build, gate, deployment or remote ref update.
- `git diff --check` clean. No shared wiring, public registry, schema, migration or lock file authored here.

## Integration and limits

Root wires advance into chain step3 and preserves Yielded until every link is recorded. The AI lane consumes the evidence/crop seam and keeps the frozen maximum of eight attached images per request. Existing engine caps remain (2000 raw regions and its child CPU/wall/memory limits); this bridge caps 1024 links. Bad source registration produces explicit status, not an empty positive result. Root separately assigned `CMP-STAGE-REVIEW-GRAPHIC-01` to bind review digests/anchors to stable engine evidence across runs; that is not claimed by this bridge commit.

Authored files are this report/task, `comparison/stage_graphic/{__init__,evidence,service}.py`, its pure unit test and `tests/integration/comparison/stage_graphic/{conftest,test_service,test_actual_engine}.py`. Root can integrate this local provider now and perform the deferred broader checks tomorrow.

## Repair-revision followup

The AI/crop evidence read now joins each graphic receipt's link item to the run's current effective revision (original when absent). Repair leaves old receipts in the history page, while AI/crop plans and review consume only the new map. A focused actual-0042 test switches the effective map, verifies old/current receipt isolation and source crop refusal for the previous revision, then verifies review receives only the current graphic ID.
