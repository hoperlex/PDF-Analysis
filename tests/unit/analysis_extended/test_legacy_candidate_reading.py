"""Legacy ensemble links are a read projection; raw artifacts and expert state stay untouched."""
from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace as NS
import json

from auditmanager.runs import extended_review as runtime
from tests.unit.analysis_extended.test_v2_quality import linked_inputs


def test_a_terminal_legacy_read_reconstructs_links_without_rewriting_the_artifact(monkeypatch):
    observations, batches = linked_inputs()
    result = {"workflow_version": "extended-review-v2", "version_uid": "v",
        "observations": observations, "sources": [{"source_id": "s1", "kind": "image"}],
        "block_ensemble": {"batches": batches}}
    original = deepcopy(result)
    raw = json.dumps({"artifact_role": runtime.EXTENDED_REVIEW_ROLE, "run_id": "r", "version_uid": "v",
        "status": "partial", "result": result}).encode()
    ref = {"role": runtime.EXTENDED_REVIEW_ROLE, "blob_id": "saved", "size_bytes": len(raw), "sha256": sha256(raw).hexdigest()}
    monkeypatch.setattr(runtime, "RunRepository", lambda: NS(get=lambda *_: NS(state="partial", version_uid="v"),
        stage_results=lambda *_: [NS(stage_id="text_analysis", artifacts=[ref])]))
    monkeypatch.setattr(runtime, "parse_blob_id", lambda value: value)

    class Context:
        def __enter__(self): return None
        def __exit__(self, *_): pass

    class ReadOnlyStore:
        def read(self, blob_id, *, verify):
            assert blob_id == "saved" and verify
            return raw

    value = runtime.read_extended_review(Context, ReadOnlyStore(), "r")["result"]
    assert value["consolidation"]["group_count"] == 1
    assert value["consolidation"]["version"] == "ensemble-linked-v1"
    assert value["observations"] == original["observations"] and result == original
    assert value["consolidated_observations"][0]["origin_count"] == 2
