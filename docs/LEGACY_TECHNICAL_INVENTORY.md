# Legacy technical inventory snapshot

This snapshot was taken from the supplied working archive while preparing the greenfield plan. It is evidence for **why not to reproduce legacy decomposition**, not a target metric.

## Size / concentration

- `frontend/static/js/app.js`: 16,192 lines.
- `frontend/index.html`: 6,576 lines.
- `backend/app/pipeline/manager.py`: 7,546 lines.
- `backend/app/main.py`: 493 lines.
- FastAPI router decorators found under `backend/app`: 324.
- files matching `test_*.py` in the supplied tree: 409.

## Pipeline stage directories observed

`block_analysis`, `block_context`, `block_grounding`, `critic_v2_triage`, `crop_blocks`, `debt_control`, `decision_carryover`, `findings_merge`, `findings_review`, `findings_verify`, `gemma_enrichment`, `norms`, `optimization`, `prepare`, `provider_selfcheck`, `report`, `text_analysis`.

The working documentation also describes production sequencing in multiple places. The new application therefore treats a **single versioned stage registry** as a contract, rather than reconstructing order from service code, logs or folder names.

## Architectural implication

The greenfield plan intentionally avoids translating router-for-router, service-for-service or stage-manager-for-stage-manager. It reconstructs vertical business capabilities through contracts, bounded contexts and evidence.
