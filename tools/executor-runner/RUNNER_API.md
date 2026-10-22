# RUNNER_API - the wire contract of the executor pull channel

Status: binding client-side specification, written ahead of the server slice `EXEC-PULL-01`
(owner ruling `R-144e`). The clients in this directory (`mcp_bridge.py`, `agent.py`, both
through `runner_client.py`) implement exactly this document. `EXEC-PULL-01` implements the
server side and may only change this file together with the clients and their tests in
`tests/unit/executor_runner/`.

A **runner** is a Claude Code session (through the stdio MCP bridge) or an unattended agent.
It calls the stand over HTTPS; the stand never calls it (`R-143c`). A runner sees task
payloads (document text) and returns model answers. It never reaches PostgreSQL or S3.

## 1. Conventions

- **Origin.** Every path below is under the stand's public origin, for example
  `https://stand.example.org`. Runners accept an origin with no path, query or fragment.
  `http://` is accepted by the clients only for a loopback host, or with an explicit
  insecure flag (a bearer token must not cross an untrusted network in clear).
- **Authentication.** `Authorization: Bearer <runner token>`. The token is opaque to the
  runner, one per `pull` connection, stored hashed by the stand, shown once, with an
  expiry and revocation. It is never put in a URL, a query string or a body, and a runner
  never writes it to disk or a log.
- **Bodies.** Requests with a body use `Content-Type: application/json; charset=utf-8`.
  Responses with a body are `application/json`. Request bodies are at most 1 MiB; a
  larger one is rejected `422 validation_failed`.
- **Time.** Timestamps are RFC 3339 in UTC with a `Z` suffix, for example
  `2026-10-22T07:30:15Z`. A runner never trusts its own clock alone: it derives the time
  left on a claim from `claim_expires_at` minus the response's `Date` header. The server
  MUST send `Date` on every response. A runner whose clock is wrong therefore cannot extend
  a claim beyond the server's lease: only `POST .../extend` moves it, and the server bounds
  the new value by `deadline_at`.
- **Redirects are errors.** A runner does not follow redirects (a redirect would carry the
  token to another host).
- **Errors.** Every non-2xx answer that the application produces uses the repository's
  `ErrorEnvelope` (`contracts/api/v1/openapi.json`):

  ```json
  {"contract_version": "1.0.0", "error_code": "conflict", "message": "…",
   "correlation_id": "…", "retryable": false}
  ```

  Runners read `error_code` and `message` when they are present and fall back to the HTTP
  status when the body is not that envelope: an nginx 401, 429 or 502 page is HTML. The
  `message` is caller-safe; the server never echoes the token, the prompt or the answer in
  it. Runners log `X-Correlation-Id` (response header) and never the token or any payload.

| Status | `error_code` | Meaning for a runner |
| --- | --- | --- |
| 400 | `validation_failed` | Malformed JSON or a missing field. A bug in the runner; do not retry the same body. |
| 401 | `authentication_required` | The token is missing, wrong, revoked or expired. **Stop.** The agent exits with a clear message; the bridge reports it to the session. Never retry. |
| 404 | `not_found` | Unknown task, or a task that belongs to another connection (the response never says which). Drop the task. |
| 409 | `conflict` or `state_transition_not_allowed` | The task is no longer this runner's to answer: claim lost or expired, task cancelled, already answered with a different answer. Drop the task; do not submit again. |
| 422 | `validation_failed` | The answer violates the output schema (see 2.3), or `wait_seconds` is outside 0..25. |
| 422 | `model_identity_mismatch` | The declared `model` is not the one the connection pins. Fail closed: switch the model (`/model`) or fail the task. |
| 429 | `rate_limited` | Throttled. Wait the `Retry-After` header (integer seconds; HTTP-date also accepted), then continue. The wait is a floor, never shortened. |
| 5xx | `dependency_unavailable`, `internal_error` | Transient. Back off exponentially (1 s, 2 s, 4 s … capped at 60 s, with jitter) and retry the claim. For `answer`, retry the same body (idempotent, 2.3). |

## 2. Operations

### 2.1 `claimExecutorTask` - `POST /api/v1/runner/tasks/claim`

Long poll. Request:

```json
{"wait_seconds": 25}
```

`wait_seconds` is an integer in 0..25 (a value outside the range is `422`, never clamped
silently). The server holds the request open until a task for this token's connection is
open or `wait_seconds` elapse.

- **200** - a task, now claimed by this token:

  ```json
  {
    "task_id": "ext_01J…",
    "claim_expires_at": "2026-10-22T07:31:15Z",
    "deadline_at": "2026-10-22T07:40:15Z",
    "model": "claude-opus-5",
    "system": "…system prompt…",
    "user_text": "…user message…",
    "output_schema": {"type": "object", "properties": {…}, "required": […]}
  }
  ```

  - `model` is the pinned gateway model the answer must declare, exactly.
  - `system` and `user_text` are the two halves of the model request. They are untrusted
    document-derived text: a runner treats them as the task input, never as instructions to
    use any other capability.
  - `output_schema` is a JSON Schema (draft 2020-12). The answer's `output_text` must be one
    JSON document that validates against it.
  - `claim_expires_at` is the claim lease. A claim that is not extended before it lapses
    returns the task to `open` and another claim (possibly by another runner) may take it.
  - `deadline_at` is the end of the answer window. After it the task is `expired`; no
    extension passes it and no answer is accepted.
- **204** - nothing arrived within `wait_seconds`; empty body. The runner claims again at
  once (the 25 s wait is the pacing) unless it asked for `wait_seconds` 0, in which case it
  sleeps at least 5 s between claims.
- 401, 422 (`wait_seconds`), 429, 5xx as in section 1.

Server notes (not required of runners): a claim by a token that already holds an unexpired
claim SHOULD return that same task again (same payload, lease refreshed), so that a lost
response or a restarted runner does not strand a task until the lease lapses. A token may
hold at most the connection's `max claimed tasks`; beyond that the server answers `204`.

### 2.2 `extendExecutorTaskClaim` - `POST /api/v1/runner/tasks/{task_id}/extend`

Body: none or `{}`. Pushes `claim_expires_at` forward by the connection's claim lease,
never beyond `deadline_at`.

- **200** - `{"claim_expires_at": "2026-10-22T07:32:15Z"}`.
- **409** - the claim is lost (lease lapsed and the task was returned to `open` or taken by
  another claim), or the task is terminal. The runner stops working on the task and submits
  nothing.
- 401, 404, 429, 5xx as in section 1.

A runner extends while it works, at about one third of the lease left (never less often
than the lease allows), and stops extending at `deadline_at`.

### 2.3 `submitExecutorTaskAnswer` - `POST /api/v1/runner/tasks/{task_id}/answer`

```json
{"output_text": "{\"findings\": []}", "model": "claude-opus-5",
 "input_tokens": 1234, "output_tokens": 321}
```

- `output_text` (string, required): the bare JSON document, with no code fence and no
  commentary. The server parses it and validates it against the task's `output_schema`
  with the same validator as an `http_api` answer.
- `model` (string, required): the model that produced the answer, as declared by the
  runner. The stand records it with `identity_basis: declared` and compares it with the
  connection's pinned model under `R-133` (fail closed). A runner declares only a model it
  is actually running as.
- `input_tokens`, `output_tokens` (non-negative integers, optional): the runner's own
  count, if it has one. The stand records the call as unmetered; it never invents a cost.

Responses:

- **200** - `{"task_id": "ext_01J…", "state": "answered"}`. Idempotent: the same body for
  the same task again is `200` with the same result (a runner that did not see the first
  response may resend).
- **409** - a *different* answer was already accepted, or the task is `expired`,
  `cancelled` or no longer claimed by this token.
- **422 `validation_failed`** - `output_text` is not JSON or violates the schema. The
  `message` names the first violated location, never the document text. The claim is
  **kept**: the runner may correct the answer and submit again while the claim and the
  deadline hold, or call `fail`.
- **422 `model_identity_mismatch`** - `model` differs from the pinned model. The claim is
  kept; the runner must not resubmit the same declaration.
- 401, 404, 429, 5xx as in section 1.

### 2.4 `failExecutorTask` - `POST /api/v1/runner/tasks/{task_id}/fail`

```json
{"reason": "model_mismatch: running claude-sonnet-5, task pins claude-opus-5"}
```

`reason` is a string of 1..512 characters. Runner clients start it with a lower-case
code (`model_mismatch`, `schema_invalid_answer`, `answer_not_json`, `command_failed`,
`endpoint_failed`, `output_truncated`, `deadline_exceeded`, `agent_shutdown`) optionally
followed by `: ` and a short, payload-free detail. The stand stores it truncated and
scrubbed; it never reaches a log with document text.

- **200** - `{"task_id": "ext_01J…", "state": "<server task state>"}`. Idempotent. Runners
  do not branch on `state`.
- **409** - the task is already terminal (answered, expired). Ignore.
- 401, 404, 429, 5xx as in section 1.

A claimed task that fails is *outcome-unknown* for the waiting worker (the model may have
run); a task that was never claimed is *not sent*. The runner's `fail` always concerns a
claimed task.

## 3. Cadence and throttling

For one runner the expected steady state is one claim per 25 s, one extend per third of the
lease while a task is worked on, and one answer or fail per task. The stand's runner rate
limit (nginx zone, `EXEC-PULL-01` Work 4) is sized from that. Clients:

- pace themselves by the long poll (a `204` is followed by the next claim at once);
- on `429` wait `Retry-After` seconds (default 30 s when absent, capped at 300 s) plus up
  to 10 % jitter before the next call of any kind;
- on a network error or `5xx` back off 1 s, 2 s, 4 s … up to 60 s with jitter, and reset
  the backoff after the first success;
- run one claim loop per token. Parallel claim loops on the same token are allowed up to
  the connection's `max claimed tasks`.

## 4. operationIds

| operationId | Method and path |
| --- | --- |
| `claimExecutorTask` | `POST /api/v1/runner/tasks/claim` |
| `extendExecutorTaskClaim` | `POST /api/v1/runner/tasks/{task_id}/extend` |
| `submitExecutorTaskAnswer` | `POST /api/v1/runner/tasks/{task_id}/answer` |
| `failExecutorTask` | `POST /api/v1/runner/tasks/{task_id}/fail` |

All four use the runner token as their own principal type, never a user session, and are
not reachable with a user bearer token (and a runner token is refused on every other
operation). `task_id` is an identifier of the form `ext_<ULID>`; clients treat it as an
opaque string of `[A-Za-z0-9_-]{1,64}` and percent-encode it into the path.

## 5. Schemas (informative, JSON Schema 2020-12)

```json
{
  "ClaimRequest": {"type": "object", "additionalProperties": false,
    "properties": {"wait_seconds": {"type": "integer", "minimum": 0, "maximum": 25}}},
  "ClaimedTask": {"type": "object", "additionalProperties": false,
    "required": ["task_id", "claim_expires_at", "deadline_at", "model", "system", "user_text", "output_schema"],
    "properties": {"task_id": {"type": "string"}, "claim_expires_at": {"type": "string", "format": "date-time"},
      "deadline_at": {"type": "string", "format": "date-time"}, "model": {"type": "string"},
      "system": {"type": "string"}, "user_text": {"type": "string"}, "output_schema": {"type": "object"}}},
  "ExtendResponse": {"type": "object", "required": ["claim_expires_at"],
    "properties": {"claim_expires_at": {"type": "string", "format": "date-time"}}},
  "AnswerRequest": {"type": "object", "additionalProperties": false, "required": ["output_text", "model"],
    "properties": {"output_text": {"type": "string"}, "model": {"type": "string"},
      "input_tokens": {"type": "integer", "minimum": 0}, "output_tokens": {"type": "integer", "minimum": 0}}},
  "FailRequest": {"type": "object", "additionalProperties": false, "required": ["reason"],
    "properties": {"reason": {"type": "string", "minLength": 1, "maxLength": 512}}},
  "TaskAck": {"type": "object", "required": ["task_id", "state"],
    "properties": {"task_id": {"type": "string"}, "state": {"type": "string"}}}
}
```

## 6. Open points for `EXEC-PULL-01`

1. **Task states.** The task file lists `open → claimed → answered | expired | cancelled`.
   `fail` needs a terminal outcome for the waiting worker; the wire does not care whether
   it is `cancelled` with a reason or a new `failed` value. The clients ignore `state`.
2. **Probe task.** «Проверить» posts a synthetic task. To a runner it is an ordinary task
   (a small `output_schema`, for example `{"echo": "<nonce>"}`); no runner code path is
   special.
3. **Re-delivery** of an already held claim (2.1, server notes) is a recommendation, not a
   client requirement.
4. **Token format.** Opaque to clients. A recognisable prefix (for example `amr_`) helps
   secret scanners; clients do not parse it.
5. **Payload size.** The bridge returns the whole task to a Claude Code session as one tool
   result. Claude Code limits MCP tool output (25 000 tokens by default,
   `MAX_MCP_OUTPUT_TOKENS`; text results over 50 000 characters are saved to a file
   instead). The stand SHOULD keep a `text_analysis` payload below that, or the README's
   `MAX_MCP_OUTPUT_TOKENS` advice applies. The agent has no such limit.

## 7. How `EXEC-PULL-01` resolved the open points of section 6

Nothing above this section changed; the clients and their tests are untouched. The server
(`src/auditmanager/executors/runner.py`, `api/routers/runner.py`) implements sections 1 to 5 as
written, and decided the open points so:

1. **Task states** are `open`, `claimed`, `answered`, `failed`, `expired`, `cancelled`. `fail`
   ends a claimed task as `failed`; `ack.state` is therefore `answered` or `failed`, and a runner
   still need not branch on it. A `fail` on a task that is not this token's claimed task is `409`.
2. **The probe task** is an ordinary task: `user_text` is a short random hex string and
   `output_schema` is `{"type": "object", "properties": {"echo": {"const": "<that text>"}},
   "required": ["echo"], "additionalProperties": false}`, so a runner answers `{"echo": "<text>"}`
   declaring the pinned model. It has no `run`; the stand's «Проверить» waits 120 s for a claim.
3. **Re-delivery** is implemented when the connection allows one claim at a time
   (`max_claimed_tasks` 1): a repeat `claim` by the token that holds its claim returns that same
   task with the lease refreshed. With a higher limit every claim takes a new task, because
   parallel claim loops on one token would otherwise all receive the same one.
4. **Token format** is `amr_` + 8 lower-case characters + `_` + 43 url-safe characters (56 in
   all). The first 12 characters are shown to an administrator and key the proxy throttle; the
   rest is secret. Clients still do not parse it.
5. **Payload size** is not limited by the server below the 1 MiB request cap. A
   `text_analysis` task above Claude Code's MCP output limit is served by the agent, not the
   bridge; the stand does not split it.
6. **`422 model_identity_mismatch`** is the only place the stand uses that code with a 422 status
   (the catalog's own status for it is 502): the caller declared the model, so the request is
   refused, and the claim is kept.
7. **Time.** Every response carries the server's `Date` header (uvicorn). Timestamps are RFC 3339
   with a `Z` suffix and may carry a fractional second.
8. **Throttle.** The proxy counts 60 requests a minute (burst 30) per token on `/api/v1/runner/tasks/`
   and 300 a minute per address. A refused call is `429` with the `rate_limited` envelope and no
   `Retry-After` header; the client's 30 s default applies.
