"""Helpers of the AI-job core's database tests and the **recorded-mode test support every C2 lane uses** (`CMP-AI-JOBS-01`).

Plain code, no pytest: the fixtures that hand it to a test are in ``conftest.py`` (a test never imports a ``conftest``), and a
lane's tests load this file by explicit path, as the spend suite's helpers are loaded::

    support = _load("cmp_ai_jobs_support", Path(__file__).resolve().parents[1] / "ai_jobs" / "ai_jobs_support.py")

What it gives a lane:

* :func:`new_world` -- a project with a document set: three versions, a matrix build, a series with its transition, two page
  profiles, a sheet pair with its result (every id a scope of the four methods needs);
* :func:`recorded_route` -- an executor connection with a current revision, **routed** to a method's work kind in «Назначения»
  (the append-only route event is written; the latest one wins), metered or not; no secret, no network, nothing live;
* :class:`FakeMethod` -- an :class:`~auditmanager.comparison.public.AiMethod` with counts and work items the test chooses; a lane
  uses it to test the core and its own method beside each other;
* :class:`ScriptedLiveAdapter` -- the model seam of a *live-mode* money test: it returns the reply the test chose (never calls
  anything) and says ``live`` so the spend wrapper applies its money rules; the answer to a question by digest is
  :class:`~auditmanager.comparison.public.RecordedAnswers`.

All of it writes through the connection it is given; with the ``db`` fixture that connection is rolled back at the end of the
test, so nothing of a test stays in the lane's database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from auditmanager.analysis.public import ModelPin, ModelRequest, ModelResponse, ProviderMode
from auditmanager.comparison.public import (
    AiCallGroup,
    AiCounts,
    AiEstimateRequest,
    AiJobRecord,
    AiMode,
    AiWorkItemSpec,
)
from auditmanager.shared.identity import DocumentUid, ProjectUid, VersionUid, new_ulid

ACTOR = "usr_01ARZ3NDEKTSV4RRFFQ69G5FAV"
SHA = "a" * 64
MODEL = "claude-opus-5"
GATEWAY = "anthropic/claude-opus-5"
#: The pinned rates of ``claude-opus-5`` in the lock: USD 5 per million input tokens, USD 25 per million output tokens.
PIN = ModelPin(model_id=MODEL, input_per_mtok_usd=5.0, output_per_mtok_usd=25.0)


def new_id(prefix: str) -> str:
    return f"{prefix}_{new_ulid()}"


def x(connection: Connection, sql: str, **values: Any) -> None:
    connection.execute(text(sql), values)


def new_world(connection: Connection, versions: int = 3) -> dict[str, Any]:
    """A project with a document of ``versions`` versions, a matrix build, a series with a transition, two page profiles and a
    sheet pair with its result. Keys: ``project``, ``document``, ``versions``, ``build``, ``series``, ``transition``, ``pair``,
    ``page_a``, ``page_b``."""
    ids: dict[str, Any] = {"project": str(ProjectUid.new()), "document": str(DocumentUid.new()), "versions": []}
    x(connection, "INSERT INTO project (project_uid, name) VALUES (:project, 'ai-jobs')", **ids)
    x(connection, "INSERT INTO document (document_uid, project_uid, display_title) VALUES (:document, :project, 'D')", **ids)
    for number in range(1, versions + 1):
        version = str(VersionUid.new())
        ids["versions"].append(version)
        x(connection, "INSERT INTO document_version (version_uid, document_uid, version_ordinal, media_type, byte_size, "
                      "sha256, page_count) VALUES (:v, :document, :n, 'application/pdf', 1, :sha, 5)",
          v=version, document=ids["document"], n=number, sha=SHA)
    ids["build"] = new_id("cmx")
    x(connection, "INSERT INTO comparison_matrix (comparison_matrix_id, project_uid, document_uid, build_no, profile_signature, "
                  "rules_version, algo_version, rows) VALUES (:m, :p, :d, 1, :s, 'v1.2', 'm1', '[]')",
      m=ids["build"], p=ids["project"], d=ids["document"], s=SHA)
    ids["series"], ids["transition"] = new_id("cser"), new_id("ctn")
    command = new_id("cmd")
    x(connection, "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint) "
                  "VALUES (:c, 'start_comparison_series', :k, :f)", c=command, k=new_id("k")[:20], f=SHA)
    x(connection, "INSERT INTO comparison_series (comparison_series_id, project_uid, document_uid, comparison_matrix_id, "
                  "matrix_edit_no, input_sha256, actor_user_uid, actor_label, command_id) "
                  "VALUES (:s, :p, :d, :m, 0, :sha, :a, 'A', :c)",
      s=ids["series"], p=ids["project"], d=ids["document"], m=ids["build"], sha=SHA, a=ACTOR, c=command)
    x(connection, "INSERT INTO comparison_transition (comparison_transition_id, comparison_series_id, transition_no, "
                  "source_version_uid, target_version_uid) VALUES (:t, :s, 1, :v1, :v2)",
      t=ids["transition"], s=ids["series"], v1=ids["versions"][0], v2=ids["versions"][1])
    ids["page_a"], ids["page_b"] = new_id("cpr"), new_id("cpr")
    for profile, version, key in ((ids["page_a"], ids["versions"][0], "1" * 64), (ids["page_b"], ids["versions"][1], "2" * 64)):
        x(connection, "INSERT INTO comparison_page_profile (comparison_page_profile_id, version_uid, page_number, content_key, "
                      "algo_version, status) VALUES (:i, :v, 1, :k, 'p1', 'ready')", i=profile, v=version, k=key)
    result, ids["pair"] = new_id("csp"), new_id("ctp")
    x(connection, "INSERT INTO comparison_sheet_pair_result (comparison_sheet_pair_result_id, project_uid, content_key, "
                  "algo_version, status, page_a_profile_id, page_b_profile_id) VALUES (:r, :p, :k, 'vc1', 'different', :a, :b)",
      r=result, p=ids["project"], k=SHA, a=ids["page_a"], b=ids["page_b"])
    x(connection, "INSERT INTO comparison_sheet_pair (comparison_sheet_pair_id, comparison_transition_id, pair_no, "
                  "page_a_profile_id, page_b_profile_id) VALUES (:x, :t, 1, :a, :b)",
      x=ids["pair"], t=ids["transition"], a=ids["page_a"], b=ids["page_b"])
    return ids


@dataclass(frozen=True, slots=True)
class RecordedRoute:
    """A routed connection: what ``recorded_route`` made."""

    work_kind: str
    connection_id: str
    revision_id: str
    pinned_model: str


def recorded_route(
    connection: Connection, work_kind: str, *, billing: str = "metered", pin_id: str = MODEL, gateway_model: str = GATEWAY,
) -> RecordedRoute:
    """Create an executor connection with one revision and route ``work_kind`` to it (a new, latest route event: the route
    table is append-only and its current row is the highest ``route_no`` of the kind). Nothing here can reach a provider."""
    connection_id, revision_id, event = new_id("exc"), new_id("excr"), new_id("ert")
    x(connection, "INSERT INTO executor_connection (connection_id, kind, display_name, created_by) "
                  "VALUES (:id, 'http_api', 'recorded', :a)", id=connection_id, a=ACTOR)
    x(connection, "INSERT INTO executor_connection_revision (revision_id, connection_id, revision_no, created_by, pin_id, "
                  "gateway_model, billing, allow_client_documents, timeout_seconds, api_flavour, base_url, transport) "
                  "VALUES (:r, :c, 1, :a, :pin, :gw, :billing, false, 60, 'openai_chat', 'https://recorded.test', 'direct')",
      r=revision_id, c=connection_id, a=ACTOR, pin=pin_id, gw=gateway_model, billing=billing)
    x(connection, "INSERT INTO executor_route_event (route_event_id, work_kind, route_no, primary_connection_id, set_by) "
                  "SELECT :e, :k, COALESCE(MAX(route_no), 0) + 1, :c, :a FROM executor_route_event WHERE work_kind = :k",
      e=event, k=work_kind, c=connection_id, a=ACTOR)
    return RecordedRoute(work_kind, connection_id, revision_id, pin_id)


def new_revision(connection: Connection, route: RecordedRoute, *, number: int = 2) -> str:
    """A further revision of the routed connection (the current revision moves; a job's consent names the old one)."""
    revision_id = new_id("excr")
    x(connection, "INSERT INTO executor_connection_revision (revision_id, connection_id, revision_no, created_by, pin_id, "
                  "gateway_model, billing, allow_client_documents, timeout_seconds, api_flavour, base_url, transport) "
                  "VALUES (:r, :c, :n, :a, :pin, :gw, 'metered', false, 60, 'openai_chat', 'https://recorded.test', 'direct')",
      r=revision_id, c=route.connection_id, n=number, a=ACTOR, pin=route.pinned_model, gw=GATEWAY)
    return revision_id


def default_groups(calls: int = 10) -> tuple[AiCallGroup, ...]:
    """``calls`` requests with two crops each: at the ``claude-opus-5`` pin one call is estimated at 4800 input tokens and
    1000 output tokens, USD 0.049, so ten calls are USD 0.49."""
    return (AiCallGroup(calls=calls, prompt_chars=4000, output_tokens=1000, images=2, image_bytes=200_000),)


@dataclass
class FakeMethod:
    """An :class:`AiMethod` with the counts and the work items the test chooses. ``units`` maps a mode to the unit keys a
    :meth:`work_items` call returns for it; ``counts_by_mode`` to the counts :meth:`counts` answers (``counts_default`` otherwise)."""

    method: str
    prompt_version: str = "fake-1"
    counts_default: AiCounts = field(default_factory=lambda: AiCounts(groups=default_groups(10), units=10))
    counts_by_mode: dict[AiMode, AiCounts] = field(default_factory=dict)
    units: dict[AiMode, list[str]] = field(default_factory=lambda: {
        AiMode.START: [f"u{i}" for i in range(3)], AiMode.LEFT: [], AiMode.FAILED: [],
    })
    seen_jobs: list[AiJobRecord] = field(default_factory=list)

    def counts(self, session: Any, request: AiEstimateRequest) -> AiCounts:
        return self.counts_by_mode.get(request.mode, self.counts_default)

    def work_items(self, session: Any, job: AiJobRecord, mode: AiMode) -> list[AiWorkItemSpec]:
        self.seen_jobs.append(job)
        return [AiWorkItemSpec(unit_key=key, payload={"unit": key}) for key in self.units.get(mode, [])]


@dataclass
class ScriptedLiveAdapter:
    """The model seam of a money test: says ``live`` (so the spend wrapper applies its rules), returns the reply the test chose
    and records what it was asked. It holds no client and calls nothing."""

    reply: ModelResponse
    requests: list[ModelRequest] = field(default_factory=list)

    @property
    def provider_mode(self) -> ProviderMode:
        return ProviderMode.LIVE

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        return self.reply


def live_reply(*, cost: float | None, tokens: tuple[int, int] = (1000, 200), model: str | None = GATEWAY) -> ModelResponse:
    return ModelResponse(
        output_text="{}", stop_reason="end_turn", input_tokens=tokens[0], output_tokens=tokens[1], latency_ms=10,
        reported_cost_usd=cost, model=model,
    )


def request_for(label: str) -> ModelRequest:
    return ModelRequest(model_id=MODEL, body={"model": MODEL, "messages": [{"role": "user", "content": label}]})


def conflict_reason(error: Any) -> str:
    """The registered reason of a ``409 conflict`` ``DomainError`` (``pytest.raises(...)`` info or the error itself)."""
    from auditmanager.shared.errors import ErrorCode

    value = getattr(error, "value", error)
    assert value.code is ErrorCode.CONFLICT, value.code
    return str(value.detail_fields["conflict_reason"])


def counts_for(calls: int, *, units: int | None = None, reused: int = 0, images: int = 2) -> AiCounts:
    """``calls`` requests of the default shape (see :func:`default_groups`), ``units`` units (``calls`` by default)."""
    return AiCounts(
        groups=(AiCallGroup(calls=calls, prompt_chars=4000, output_tokens=1000, images=images,
                            image_bytes=200_000 if images else 0),) if calls else (),
        units=calls if units is None else units, reused=reused,
    )


def insert_call(
    connection: Connection, item: Any, *, state: str = "completed", cost_micros: int = 0, estimate_micros: int = 0,
    revision_id: str | None = None, provider_mode: str = "live", input_tokens: int = 1, output_tokens: int = 1,
) -> str:
    """A row of the spend journal for a claimed item, in a given state, made the only way the database allows: inserted
    ``prepared`` then moved along the edges (``prepared -> sent -> completed | failed | unknown``)."""
    from auditmanager.shared.identity import ComparisonModelCallId

    call_id = str(ComparisonModelCallId.new())
    x(connection, "INSERT INTO comparison_model_call (comparison_model_call_id, comparison_work_id, comparison_work_attempt_id, "
                  "work_kind, provider_mode, model_identity, connection_revision_id, request_sha256, estimate_micros) "
                  "VALUES (:id, :w, :a, :k, :mode, :m, :r, :sha, :est)",
      id=call_id, w=item.work_id, a=item.attempt_id, k=item.kind, mode=provider_mode, m=MODEL, r=revision_id, sha=SHA,
      est=estimate_micros)
    if state in ("sent", "completed"):
        x(connection, "UPDATE comparison_model_call SET state = 'sent', sent_at = clock_timestamp() "
                      "WHERE comparison_model_call_id = :id", id=call_id)
    if state == "completed":
        x(connection, "UPDATE comparison_model_call SET state = 'completed', response_sha256 = :sha, input_tokens = :i, "
                      "output_tokens = :o, latency_ms = 1, cost_basis = 'measured', cost_micros = :cost, "
                      "terminal_at = clock_timestamp() WHERE comparison_model_call_id = :id",
          id=call_id, sha=SHA, i=input_tokens, o=output_tokens, cost=cost_micros)
    elif state == "failed":
        x(connection, "UPDATE comparison_model_call SET state = 'failed', error_code = 'provider_refused', "
                      "terminal_at = clock_timestamp() WHERE comparison_model_call_id = :id", id=call_id)
    elif state == "unknown":
        x(connection, "UPDATE comparison_model_call SET state = 'unknown', error_code = 'attempt_lost', "
                      "terminal_at = clock_timestamp() WHERE comparison_model_call_id = :id", id=call_id)
    return call_id
