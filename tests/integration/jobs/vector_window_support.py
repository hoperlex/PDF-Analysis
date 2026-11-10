"""Rows and a pretend host for the night-window suites (`EMBED-01`): a case with its text, the control row put back, and the host's side of the exchange.

Database only. Everything the pass does is done by the shipped ``VectorWindowPass``; what is written here is what the world gives it: cases of the
decision memory, the host's heartbeat, and the container's answer -- the REAL answer of ``embed-texts`` (the norms package's own function, over a fake
encoder), so what the pass imports is what the image would have produced and not a fixture the test wrote to agree with it.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.norms.embedding import texts as norms_texts
from auditmanager.norms.embedding import vectors as norms_vectors
from auditmanager.shared.identity import DecisionMemoryCaseId, FindingObservationId

#: A moment inside the default window (01:00-06:00 at Yekaterinburg, +05): 02:00 on 2026-11-11 local.
INSIDE = datetime.fromisoformat("2026-11-11T02:00:00+05:00")
#: A moment after it: 06:30 the same morning.
AFTER = datetime.fromisoformat("2026-11-11T06:30:00+05:00")
#: A moment well before the next night's window and after this one: noon.
NOON = datetime.fromisoformat("2026-11-11T12:00:00+05:00")


def reset_control(sessions: sessionmaker[Session]) -> None:
    """The control row as the migration seeds it: nothing paused, the window closed and not used by any night."""
    with sessions() as session:
        session.execute(text(
            "UPDATE vector_control SET paused = false, paused_since = NULL, window_state = 'closed', window_reason = NULL, "
            "window_changed_at = timestamptz '2000-01-01' WHERE control_key = 'default'"))
        session.commit()


def control(sessions: sessionmaker[Session]) -> dict[str, Any]:
    with sessions() as session:
        row = session.execute(text(
            "SELECT paused, window_state, window_reason FROM vector_control WHERE control_key = 'default'")).one()
        return {"paused": row[0], "state": row[1], "reason": row[2]}


def journal(sessions: sessionmaker[Session], *, since: int = 0) -> list[tuple[str, str | None]]:
    """``(kind, reason)`` of the control journal after event number ``since``, in order."""
    with sessions() as session:
        return [(str(kind), None if reason is None else str(reason)) for kind, reason in session.execute(text(
            "SELECT kind, reason FROM vector_control_event WHERE control_key = 'default' AND event_no > :since ORDER BY event_no"),
            {"since": since}).all()]


def last_event_no(sessions: sessionmaker[Session]) -> int:
    with sessions() as session:
        return int(session.execute(text("SELECT COALESCE(MAX(event_no), 0) FROM vector_control_event")).scalar_one())


def add_case(engine: Engine, *, finding: str, recommendation: str = "Привести в соответствие.", category: str = "dimensions") -> str:
    """One committed case with one revision of content and the text given. Every trigger is on."""
    case_id = DecisionMemoryCaseId.new().value
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO decision_memory_case (case_id, origin_observation_id, origin_finding_uid, origin_project_uid, origin_document_uid, "
            "origin_version_uid, origin_run_id, category, section_code, data_class, crop_state, capture_version, content_sha256) "
            "VALUES (:c, :o, 'fnd_01ARZ3NDEKTSV4RRFFQ69G5FAV', 'prj_01ARZ3NDEKTSV4RRFFQ69G5FAV', 'doc_01ARZ3NDEKTSV4RRFFQ69G5FAV', "
            "'ver_01ARZ3NDEKTSV4RRFFQ69G5FAV', 'run_01ARZ3NDEKTSV4RRFFQ69G5FAV', :cat, 'AR', 'test', 'none_available', 'dm-capture/1', :sha)"),
            {"c": case_id, "o": FindingObservationId.new().value, "cat": category, "sha": "a" * 64})
        connection.execute(text(
            "INSERT INTO decision_memory_content (case_id, revision, finding_text, recommendation_text, stage_id, analysis_profile_id, "
            "prompt_bundle_id, provider_mode) VALUES (:c, 1, :f, :r, 'text_analysis', 'ap_01ARZ3NDEKTSV4RRFFQ69G5FAV', "
            "'pb_01ARZ3NDEKTSV4RRFFQ69G5FAV', 'recorded')"), {"c": case_id, "f": finding, "r": recommendation})
    return case_id


def forget(engine: Engine, case_id: str) -> None:
    """What the operator's forget does to this case, in one transaction: the event, then the deletes it permits."""
    from auditmanager.shared.identity import DecisionMemoryStatusEventId

    with engine.begin() as connection:
        actor = connection.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one()
        connection.execute(text(
            "INSERT INTO decision_memory_status_event (status_event_id, case_id, kind, reason_code, actor_user_uid, owner_permission_ref, "
            "forgotten_content_sha256) VALUES (:id, :c, 'forget', 'other', :a, 'embed-01 test', :d)"),
            {"id": DecisionMemoryStatusEventId.new().value, "c": case_id, "a": actor, "d": "b" * 64})
        for table in ("decision_memory_embedding", "decision_memory_embedding_intent"):
            connection.execute(text(f"DELETE FROM {table} WHERE case_id = :c"), {"c": case_id})


def intents_of(sessions: sessionmaker[Session], case_ids: Sequence[str]) -> dict[str, dict[str, Any]]:
    with sessions() as session:
        rows = session.execute(text(
            "SELECT case_id, state, attempts, poison_reason, input_sha256 FROM decision_memory_embedding_intent WHERE case_id = ANY(:ids)"),
            {"ids": list(case_ids)}).all()
    return {str(r[0]): {"state": r[1], "attempts": r[2], "reason": r[3], "digest": r[4]} for r in rows}


def embeddings_of(sessions: sessionmaker[Session], case_ids: Sequence[str]) -> dict[str, dict[str, Any]]:
    with sessions() as session:
        rows = session.execute(text(
            "SELECT case_id, input_sha256, embedding_sha256, model_revision, vector_dims(embedding), vector_norm(embedding) "
            "FROM decision_memory_embedding WHERE case_id = ANY(:ids)"), {"ids": list(case_ids)}).all()
    return {str(r[0]): {"digest": r[1], "vector_digest": r[2], "model": r[3], "dims": r[4], "norm": float(r[5])} for r in rows}


# -- the host's side of the exchange -----------------------------------------------------------------------------------------


class FakeEncoder:
    """The ``TextEncoder`` protocol: a token is a word, a vector is a function of the text, and every vector is a real unit vector."""

    def count_tokens(self, text_: str) -> int:
        return len(text_.split()) + 2

    def encode(self, texts: Sequence[str]) -> list[bytes]:
        out = []
        for value in texts:
            seed = int(hashlib.sha256(value.encode()).hexdigest()[:6], 16)
            raw = [math.sin(seed * 3.0 + index * 0.017) for index in range(1024)]
            norm = math.sqrt(sum(item * item for item in raw))
            out.append(norms_vectors.pack([item / norm for item in raw]))
        return out


def heartbeat(directory: Path, at: datetime, *, age_seconds: int = 30) -> None:
    (directory / "heartbeat").write_text(f"epoch={int(at.timestamp()) - age_seconds}\n", encoding="utf-8")


def request_of(directory: Path) -> dict[str, Any]:
    return json.loads((directory / "request.json").read_text(encoding="utf-8"))


def host_answers(directory: Path, *, exit_code: int = 0, over_limit: Sequence[str] = (), tamper: Any = None, stderr: str = "") -> None:
    """The container ran over ``request.json`` and the host reports it. ``over_limit`` are ids the in-image entry sets aside; ``tamper`` may
    change the response before it is written (to play an encoder that moved a frozen fact)."""
    request = request_of(directory)
    kept = [item for item in request["texts"] if item["id"] not in over_limit]
    if exit_code == 0:
        response = norms_texts.embed_texts(FakeEncoder(), {"format": request["format"], "texts": kept}) if kept else {
            "format": norms_texts.RESPONSE_FORMAT, "embedding_profile": "bge-m3-dense-v1", "model_repository": "BAAI/bge-m3",
            "model_revision": "5617a9f61b028005a4858fdac845db406aefb181", "dimensions": 1024, "dtype": "float32", "byte_order": "big", "vectors": []}
        if tamper is not None:
            tamper(response)
        (directory / "response.json").write_text(json.dumps(response), encoding="utf-8")
        (directory / "over_limit.json").write_text(json.dumps({
            "format": "auditmanager-embed-over-limit/1", "limit": 512,
            "entries": [{"id": identifier, "token_count": 700} for identifier in over_limit]}), encoding="utf-8")
    (directory / "stderr.log").write_text(stderr, encoding="utf-8")
    (directory / "result").write_text(f"exit_code={exit_code}\nfinished_epoch=1\n", encoding="utf-8")
