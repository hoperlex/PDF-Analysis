"""Explicit local synthetic C4 worker. Never imports or binds a live model adapter.

This is a fixture generator/adapter, not a model recording or engineering acceptance.
Every answer binds the actual request/source digest and actual source IDs. Receipts
record image hashes/counts so the browser walk cannot claim an image was sent merely
because a preflight estimate mentioned it. Importing this module starts nothing.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import urlparse


def synthetic_response(request):
    from auditmanager.analysis.public import ModelResponse
    messages = request.body["messages"]
    content = messages[-1]["content"]
    text = content if isinstance(content, str) else "\n".join(p.get("text", "") for p in content if p.get("type") == "text")
    source = json.loads(text.split("\nINPUT\n", 1)[1])
    properties = request.body["output_config"]["format"]["schema"]["properties"]
    answer = {"group_id": source["group_id"], "source_sha256": source["source_sha256"], "context_requests": []}
    if "decisions" in properties:
        left = sorted({f for item in source["items"] for f in item["left_fragment_ids"]})
        right = sorted({f for item in source["items"] for f in item["right_fragment_ids"]})
        answer |= {"chunk_id": source["chunk_id"], "decisions": [{
            "left_fragment_ids": left, "right_fragment_ids": right, "status": "UNCERTAIN",
            "confidence": "low", "summary": "Синтетический ответ требует проверки.",
            "reason": "Тестовый ответ не является инженерным заключением.", "actual_right_profile_ids": []}]}
    elif "cards" in properties:
        answer["cards"] = [{"class": "REVIEW", "category": "uncertain", "system": "unknown",
            "title": "Синтетический ответ требует проверки", "evidence_ids": [e["evidence_id"]],
            "materiality": "unknown", "importance": "unknown", "detail_increased": False}
            for e in source["atomic_evidence"]]
    elif "decision" in properties:
        answer |= {"evidence_ids": [e["evidence_id"] for e in source["atomic_evidence"]],
            "decision": "INSUFFICIENT_CONTEXT", "type": "UNRESOLVED_HIGH_LEVEL_CHANGE",
            "title": "Требуется экспертная проверка", "reason": "Синтетический ответ не является инженерным заключением."}
    else:
        raise ValueError("recording_missing: unsupported non-C4 request; no fallback")
    # The shared wire validator still checks this exact synthetic answer.
    return ModelResponse(output_text=json.dumps(answer, ensure_ascii=False), stop_reason="end_turn",
                         input_tokens=100, output_tokens=100, latency_ms=1), source


class SyntheticRoutes:
    def __init__(self, receipts: Path):
        self.receipts = receipts

    def route_for(self, session, job):
        from auditmanager.analysis.public import ProviderMode
        from auditmanager.comparison.spend.model import CallRoute
        owner = self
        class Adapter:
            provider_mode = ProviderMode.RECORDED
            def complete(self, request):
                response, source = synthetic_response(request)
                content = request.body["messages"][-1]["content"]
                images = [p for p in content if p.get("type") in {"image", "image_url"}] if isinstance(content, list) else []
                hashes = []
                data_items = list(request.images_bytes)
                if not data_items:
                    for image in images:
                        encoded = image.get("source", {}).get("data") or image.get("image_url", {}).get("url", "").split(",", 1)[-1]
                        data_items.append(base64.b64decode(encoded, validate=True))
                for data in data_items:
                    if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) > 2 * 1024 * 1024:
                        raise ValueError("synthetic fixture received an invalid source PNG")
                    hashes.append(hashlib.sha256(data).hexdigest())
                if request.body.get("images"):
                    if len(request.body["images"]) != len(hashes):
                        raise ValueError("image descriptors and actual PNG bytes disagree")
                    for descriptor, sha in zip(request.body["images"], hashes, strict=True):
                        if descriptor.get("sha256") != sha:
                            raise ValueError("source image digest mismatch")
                if source.get("graphic") and not 1 <= len(hashes) <= 8:
                    raise ValueError("GRAPHIC request carries no actual bounded source images")
                receipt = {"fixture": "synthetic-c4/1", "provider_mode": "recorded",
                    "run_id": job.scope.stage_chain_run_id, "request_sha256": request.request_sha256,
                    "group_id": source["group_id"], "source_sha256": source["source_sha256"],
                    "images": len(hashes), "png_sha256": hashes, "answer_sha256": hashlib.sha256(response.output_text.encode()).hexdigest()}
                owner.receipts.parent.mkdir(parents=True, exist_ok=True)
                with owner.receipts.open("a", encoding="utf-8") as output:
                    output.write(json.dumps(receipt, sort_keys=True) + "\n")
                return response
        return CallRoute(Adapter(), job.pinned_model, connection_revision_id=job.connection_revision_id,
                         expected_model=None, check_identity=False, unmetered=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-synthetic-only", action="store_true", required=True)
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--seed-route", action="store_true")
    args = parser.parse_args()
    if os.environ.get("AUDITMANAGER_PROVIDER_MODE") != "recorded":
        parser.error("AUDITMANAGER_PROVIDER_MODE must explicitly be recorded")
    for name in ("DATABASE_URL", "S3_ENDPOINT_URL"):
        if urlparse(os.environ.get(name, "")).hostname not in {"127.0.0.1", "localhost", "::1"}:
            parser.error(f"{name} must name this isolated local fixture stand")
    from sqlalchemy import text
    from auditmanager.shared.db import get_session_factory, get_engine, session_scope
    from auditmanager.shared.identity import new_ulid
    from auditmanager.storage.public import S3BlobStore, S3StorageSettings
    from auditmanager.comparison.public import HANDLER_FACTORIES, SPEND_SETTLERS, ComparisonWorkRepository, ComparisonWorkRunner, HandlerRegistry, WorkDependencies
    from auditmanager.ingest.comparison_batch.public import BATCH_HANDLER_FACTORIES
    from auditmanager.workers.public import WorkerRegistry
    sessions, engine = get_session_factory(), get_engine()
    if args.seed_route:
        with session_scope(sessions) as session:
            actor = session.execute(text("SELECT user_uid FROM app_user ORDER BY created_at LIMIT 1")).scalar_one()
            connection, revision, event = (f"{p}_{new_ulid()}" for p in ("exc", "excr", "ert"))
            session.execute(text("INSERT INTO executor_connection(connection_id,kind,display_name,created_by) VALUES(:id,'http_api','Synthetic C4 journey fixture',:actor)"), {"id": connection, "actor": actor})
            session.execute(text("INSERT INTO executor_connection_revision(revision_id,connection_id,revision_no,created_by,pin_id,gateway_model,billing,allow_client_documents,timeout_seconds,api_flavour,base_url,transport) VALUES(:id,:connection,1,:actor,'claude-opus-5','anthropic/claude-opus-5','not_metered',false,60,'openai_chat','https://recorded.invalid','direct')"), {"id": revision, "connection": connection, "actor": actor})
            session.execute(text("INSERT INTO executor_route_event(route_event_id,work_kind,route_no,primary_connection_id,set_by) SELECT :id,'comparison_stage_review',coalesce(max(route_no),0)+1,:connection,:actor FROM executor_route_event WHERE work_kind='comparison_stage_review'"), {"id": event, "connection": connection, "actor": actor})
    work = ComparisonWorkRepository()
    store = S3BlobStore(S3StorageSettings.from_env())
    # The fixture owns stage AI only. Shared deterministic intake/profile work may
    # use the versions module, but older version-AI recordings have their own worker.
    names = {"page_profile_handler", "pair_result_handler", "stage_chain_handler",
             "stage_chain_batch_handler", "stage_text_recompute_handler"}
    factories = tuple(factory for factory in HANDLER_FACTORIES if factory.__name__ in names)
    if {factory.__name__ for factory in factories} != names:
        raise RuntimeError("C4 fixture handler contract changed")
    registry = HandlerRegistry.build((*factories, *BATCH_HANDLER_FACTORIES),
        WorkDependencies(engine, sessions, store, work, routes=SyntheticRoutes(args.receipts)))
    runner = ComparisonWorkRunner(sessions, registry=registry, modules=frozenset({"versions", "stages"}), repository=work, spend_settlers=SPEND_SETTLERS)
    with session_scope(sessions) as session:
        worker = WorkerRegistry().register(session, version="synthetic-c4-journey", slots=1)
    try:
        while True:
            with session_scope(sessions) as session:
                WorkerRegistry().heartbeat(session, worker)
            item = runner.claim(worker)
            if item is None:
                time.sleep(0.25)
            else:
                runner.execute(item)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
