# Legacy technical inventory snapshot

This inventory was recomputed from the immutable Git tree of the canonical legacy
snapshot recorded in `SOURCE_TRACEABILITY.md`:

```text
resolved_ref: refs/heads/main
commit: 32b9d903792b30506048a1d42b0e6b2d07aee403
commit_date: 2026-08-22T10:37:15+03:00
inventory_date: 2026-08-31
```

Working-tree and untracked files are excluded. The snapshot is evidence for **why
not to reproduce legacy decomposition**, not a target metric.

## Size / concentration

- `frontend/static/js/app.js`: 16,149 lines.
- `frontend/index.html`: 6,421 lines.
- `backend/app/pipeline/manager.py`: 7,541 lines.
- `backend/app/main.py`: 493 lines.
- FastAPI HTTP/WebSocket router decorators found under `backend/app`: 325.
- files matching `test_*.py` in the committed tree: 389.

## Pipeline stage directories observed

`block_analysis`, `block_context`, `block_grounding`, `critic_v2_triage`, `crop_blocks`, `debt_control`, `decision_carryover`, `findings_merge`, `findings_review`, `findings_verify`, `gemma_enrichment`, `norms`, `optimization`, `prepare`, `provider_selfcheck`, `report`, `text_analysis`.

The working documentation also describes production sequencing in multiple places. The new application therefore treats a **single versioned stage registry** as a contract, rather than reconstructing order from service code, logs or folder names.

## Architectural implication

The greenfield plan intentionally avoids translating router-for-router, service-for-service or stage-manager-for-stage-manager. It reconstructs vertical business capabilities through contracts, bounded contexts and evidence.
