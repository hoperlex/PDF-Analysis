"""Helpers of the AI pair check's database tests (`CMP-VC-AIPAIR-01`): a document set with page profiles and stored previews, a matrix
build with the rows a test chooses, and a rig that runs the work handler against :class:`RecordedAnswers` -- recorded mode, so
no test makes a live call and a question with no recorded answer fails loudly instead of reaching anything.

Plain code, no pytest; ``conftest.py`` loads it by path (a test never imports a ``conftest``).
"""

from __future__ import annotations

import hashlib
import io
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from PIL import Image
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.analysis.public import ModelRequest
from auditmanager.comparison.ai_pairs.handler import PairCheckHandler
from auditmanager.comparison.ai_pairs.method import PairCheckMethod, load_snapshot, plan_context
from auditmanager.comparison.ai_pairs.model import Question
from auditmanager.comparison.ai_pairs.plans import CallPlan, forward_plan, reverse_plan
from auditmanager.comparison.ai_pairs.prompt import build_request, crop_ids
from auditmanager.comparison.ai_pairs.repository import AiPairRepository
from auditmanager.comparison.ai_pairs.service import ComparisonAiPairService
from auditmanager.comparison.matrix import settings as matrix_settings
from auditmanager.comparison.matrix.inputs import profile_digest
from auditmanager.comparison.matrix.repository import MatrixRepository
from auditmanager.comparison.profile.limits import ALGO_VERSION as PAGE_PROFILE_ALGO_VERSION
from auditmanager.comparison.public import (
    AiJobRecord,
    CallRoute,
    Completed,
    ComparisonWorkRepository,
    RecordedAnswers,
    WorkDependencies,
)
from auditmanager.executors.public import CropImage, attach_images
from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid, new_ulid
from auditmanager.storage.public import derive_blob_id

ACTOR = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
KIND = "comparison_pair_check"
PAGES = 12


def new_id(prefix: str) -> str:
    return f"{prefix}_{new_ulid()}"


def png_bytes(version_index: int, page: int) -> bytes:
    """A small PNG that is different for every page, so that every page is its own blob."""
    image = Image.new("RGB", (16 + page, 12 + version_index), ((version_index * 40) % 256, (page * 20) % 256, 128))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class FakeBlobStore:
    """The part of the blob port the preview reader uses: ``read(blob_id, verify=True)``."""

    def __init__(self) -> None:
        self.blobs: dict[str, bytes] = {}
        self.reads: list[str] = []

    def read(self, blob_id: Any, *, verify: bool = True) -> bytes:
        self.reads.append(str(blob_id))
        return self.blobs[str(blob_id)]


@dataclass
class World:
    """A document set: ``versions`` (ids, oldest first), a profile id and a PNG for every page, the stand-in blob store."""

    project: str
    document: str
    versions: list[str]
    profiles: dict[tuple[int, int], str]
    pngs: dict[tuple[int, int], bytes]
    blob_ids: dict[tuple[int, int], str]
    store: FakeBlobStore
    matrix_id: str | None = None
    titles: dict[tuple[int, int], str] = field(default_factory=dict)

    def version(self, index: int) -> str:
        return self.versions[index - 1]

    def profile(self, index: int, page: int) -> str:
        return self.profiles[(index, page)]


def x(connection: Connection, sql: str, **values: Any) -> None:
    connection.execute(text(sql), values)


def new_world(
    connection: Connection, *, versions: int = 3, pages: int = PAGES, titles: dict[tuple[int, int], str] | None = None,
    designations: dict[tuple[int, int], str] | None = None, previews: bool = True, project: str | None = None,
) -> World:
    """A project with a document of ``versions`` versions of ``pages`` pages. Every page has a ready profile whose stamp says
    ``sheet_number`` = its number and ``sheet_name`` = ``titles`` (default «План N»); with ``previews`` every page has a stored
    preview (a blob row and the bytes in the stand-in store)."""
    world = World(
        project=project or str(ProjectUid.new()), document=str(DocumentUid.new()), versions=[], profiles={}, pngs={}, blob_ids={},
        store=FakeBlobStore(), titles=titles or {},
    )
    if project is None:
        x(connection, "INSERT INTO project (project_uid, name) VALUES (:p, 'ai-pairs')", p=world.project)
    x(connection, "INSERT INTO document (document_uid, project_uid, display_title) VALUES (:d, :p, '133/23-ГК-ЭО')",
      d=world.document, p=world.project)
    for index in range(1, versions + 1):
        version = str(VersionUid.new())
        world.versions.append(version)
        x(connection, "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, sha256, "
                      "page_count) VALUES (:v, :d, :n, 'application/pdf', 1, :sha, :pages)",
          v=version, d=world.document, n=index, sha=hashlib.sha256(version.encode()).hexdigest(), pages=pages)
        for page in range(1, pages + 1):
            profile = new_id("cpr")
            world.profiles[(index, page)] = profile
            blob_id = None
            if previews:
                data = png_bytes(index, page)
                digest = hashlib.sha256(data).hexdigest()
                blob_id = str(derive_blob_id(sha256=digest, size=len(data)))
                world.pngs[(index, page)] = data
                world.blob_ids[(index, page)] = blob_id
                world.store.blobs[blob_id] = data
                exists = connection.execute(text("SELECT 1 FROM blob WHERE blob_id = :b"), {"b": blob_id}).first()
                if exists is None:  # a blob is made temporary, verified, then available (the table's own edges)
                    x(connection, "INSERT INTO blob (blob_id) VALUES (:b)", b=blob_id)
                    x(connection, "UPDATE blob SET state = 'verifying' WHERE blob_id = :b", b=blob_id)
                    x(connection, "UPDATE blob SET state = 'available', sha256 = :s, size_bytes = :n, media_type = 'image/png' "
                                  "WHERE blob_id = :b", b=blob_id, s=digest, n=len(data))
            stamp = {
                "sheet_number": str(page), "sheet_name": (titles or {}).get((index, page), f"План {page}"),
                "designation": (designations or {}).get((index, page), "133/23-ГК-ЭО"),
            }
            x(connection, "INSERT INTO comparison_page_profile (comparison_page_profile_id, version_uid, page_number, content_key, "
                          "algo_version, status, profile, preview_blob_id) VALUES (:i, :v, :n, :k, :algo, 'ready', "
                          "CAST(:profile AS jsonb), :blob)",
              i=profile, v=version, n=page, k=hashlib.sha256(f"{version}:{page}".encode()).hexdigest(), algo=PAGE_PROFILE_ALGO_VERSION,
              profile=json.dumps({"stamp": stamp}), blob=blob_id)
    return world


# -- the stored cells of a matrix build ---------------------------------------------------------------------------------------


def matched(world: World, index: int, page: int, confidence: str | None = None, flags: Sequence[str] = ()) -> dict[str, Any]:
    cell: dict[str, Any] = {
        "version_uid": world.version(index), "state": "matched", "page_number": page,
        "page_profile_id": world.profile(index, page), "flags": list(flags),
    }
    if confidence:
        cell["confidence"] = confidence
        cell["score"] = 0.5
    return cell


def unmatched(world: World, index: int, candidates: Sequence[int], ref: int) -> dict[str, Any]:
    return {
        "version_uid": world.version(index), "state": "unmatched", "reason": "candidates_left",
        "ref_version_uid": world.version(ref),
        "candidates": [{"page_number": n, "page_profile_id": world.profile(index, n), "score": 0.4} for n in candidates],
    }


def absent(world: World, index: int) -> dict[str, Any]:
    return {"version_uid": world.version(index), "state": "absent", "reason": "no_candidates"}


def place_matrix(
    connection: Connection, world: World, rows: Sequence[Sequence[dict[str, Any]]], *, pages: int = PAGES, signature: str | None = None,
) -> str:
    """Insert a matrix build holding ``rows`` (each a list of stored cells, one per version) that reads as ``ready``: its profile
    signature is the digest of the profiles it read, computed by the matrix's own function (``signature`` overrides it: a build
    made of other profiles than the ones now stored, which reads as stale)."""
    matrix_id = new_id("cmx")
    sessions = sessionmaker(bind=connection, expire_on_commit=False, future=True)
    with sessions() as session:
        facts = MatrixRepository().profile_facts(session, world.versions, PAGE_PROFILE_ALGO_VERSION)
    summary = {"order": world.versions, "page_counts": {v: pages for v in world.versions}}
    number = connection.execute(
        text("SELECT coalesce(max(build_no), 0) + 1 FROM comparison_matrix WHERE document_uid = :d"), {"d": world.document},
    ).scalar_one()
    x(connection, "INSERT INTO comparison_matrix (comparison_matrix_id, project_uid, document_uid, build_no, profile_signature, "
                  "rules_version, algo_version, rows, summary) VALUES (:m, :p, :d, :n, :sig, :rules, :algo, CAST(:rows AS jsonb), "
                  "CAST(:summary AS jsonb))",
      m=matrix_id, p=world.project, d=world.document, n=number, sig=signature or profile_digest(facts), rules=matrix_settings.RULES_VERSION,
      algo=matrix_settings.ALGO_VERSION, rows=json.dumps([{"cells": list(cells)} for cells in rows]), summary=json.dumps(summary))
    world.matrix_id = matrix_id
    return matrix_id


# -- the rig: the service, the handler and the recorded adapter ---------------------------------------------------------------


@dataclass
class Rig:
    """Everything a test drives: the pair service (the operations), the work handler, the recorded adapter and the queue."""

    connection: Connection
    sessions: "sessionmaker[Session]"
    world: World
    service: ComparisonAiPairService
    handler: PairCheckHandler
    answers: RecordedAnswers
    work: ComparisonWorkRepository
    worker: str
    routes: list[CallRoute] = field(default_factory=list)

    # -- recording answers ---------------------------------------------------------------------------
    def job(self, job_id: str) -> AiJobRecord:
        with self.sessions() as session:
            return self.service.jobs.job(session, job_id)

    def questions(self, job: AiJobRecord) -> list[Question]:
        with self.sessions() as session:
            snapshot = load_snapshot(
                session, MatrixRepository(), AiPairRepository(), project_uid=job.project_uid, document_uid=job.document_uid,
                matrix_id=job.matrix_id, latest_only=False,
            )
            return snapshot.questions()

    def context(self, job: AiJobRecord) -> Any:
        with self.sessions() as session:
            snapshot = load_snapshot(
                session, MatrixRepository(), AiPairRepository(), project_uid=job.project_uid, document_uid=job.document_uid,
                matrix_id=job.matrix_id, latest_only=False,
            )
            return plan_context(snapshot, project_uid=job.project_uid, model_identity=job.pinned_model, provider_mode=job.provider_mode)

    def request_of(self, job: AiJobRecord, plan: CallPlan) -> ModelRequest:
        """The request the handler sends for ``plan`` -- rebuilt the way the handler builds it, from the page bytes of the world."""
        crops = []
        for crop_id, page in zip(crop_ids(len(plan.pages) - 1), plan.pages, strict=True):
            key = next(k for k, v in self.world.profiles.items() if v == page.page_profile_id)
            crops.append(CropImage(crop_id=crop_id, data=self.world.pngs[key]))
        return attach_images(build_request(model_id=job.pinned_model, prompt=plan.prompt), crops)

    def forward(self, job: AiJobRecord, question: Question) -> CallPlan:
        return forward_plan(question, self.context(job))

    def reverse(self, job: AiJobRecord, question: Question, b_page: int) -> CallPlan | None:
        return reverse_plan(question, b_page, self.context(job))

    def say(self, job: AiJobRecord, plan: CallPlan, choice_page: int, confidence: str = "high", reason: str = "тот же лист") -> str:
        """Record the answer of the model to ``plan``: the candidate with page ``choice_page`` (0: none)."""
        number = 0 if choice_page == 0 else plan.cands.index(choice_page) + 1
        return self.answers.record(
            self.request_of(job, plan),
            json.dumps({"choice": number, "page": choice_page, "confidence": confidence, "reason": reason}, ensure_ascii=False),
        )

    # -- running the queue ---------------------------------------------------------------------------
    def run_next(self, *, kind: str = KIND) -> Any:
        """Claim one item the way the worker does, run the handler and end the item with its outcome; ``None`` when nothing is
        claimable."""
        with self.sessions() as session:
            item = self.work.claim(session, worker_id=self.worker, modules=frozenset({"versions"}), kinds=frozenset({kind}))
            session.commit()
        if item is None:
            return None
        outcome = self.handler.run(item)
        with self.sessions() as session:
            state = self.work.finish(session, item.authority, outcome)
            session.commit()
        return item, outcome, state

    def drain(self, *, limit: int = 200, until_close: bool = True) -> list[tuple[str, Any, str]]:
        """Run items until none is claimable (an item that yields with a delay is not claimable until the delay has passed, so
        the closing item is made due first when ``until_close``)."""
        done: list[tuple[str, Any, str]] = []
        for _ in range(limit):
            if until_close:  # a yield and a retry wait for a delay: make everything queued due
                self.connection.execute(text(
                    "UPDATE comparison_work SET not_before = clock_timestamp() - interval '1 second' "
                    "WHERE kind = :k AND state = 'queued'"), {"k": KIND})
            ran = self.run_next()
            if ran is None:
                break
            item, outcome, state = ran
            done.append((str(item.payload.get("step")), outcome, state))
            if isinstance(outcome, Completed) and str(item.payload.get("step")) == "close":
                break
        return done

    def rows(self, sql: str, **values: Any) -> list[dict[str, Any]]:
        return [dict(row) for row in self.connection.execute(text(sql), values).mappings()]

    def scalar(self, sql: str, **values: Any) -> Any:
        return self.connection.execute(text(sql), values).scalar_one()


def make_rig(
    connection: Connection, sessions: "sessionmaker[Session]", world: World, *, modules: str = "versions", live_binder: Any = None,
    engine: Any = None, provider_mode: str = "recorded", route_reader: Any = None,
) -> Rig:
    from auditmanager.workers.public import WorkerRegistry

    answers = RecordedAnswers()
    work = ComparisonWorkRepository()
    extra = {} if route_reader is None else {"route_reader": route_reader}
    service = ComparisonAiPairService(
        sessions, blob_store=world.store, comparison_modules=modules, provider_mode=provider_mode, **extra,
    )
    dependencies = WorkDependencies(engine=engine, session_factory=sessions, blob_store=world.store, work=work)  # type: ignore[arg-type]
    rig_routes: list[CallRoute] = []

    def binder(session: Session, job: AiJobRecord) -> CallRoute:
        route = CallRoute(
            adapter=answers, model_identity=job.pinned_model, connection_revision_id=job.connection_revision_id,
            expected_model=None, check_identity=False,
        )
        rig_routes.append(route)
        return route

    handler = PairCheckHandler(dependencies, binder=live_binder or binder, jobs=service.jobs)
    with sessions() as session:
        worker = WorkerRegistry().register(session, version="cmp-vc-aipair-01-test", slots=1)
        session.commit()
    return Rig(
        connection=connection, sessions=sessions, world=world, service=service, handler=handler, answers=answers, work=work,
        worker=worker, routes=rig_routes,
    )
