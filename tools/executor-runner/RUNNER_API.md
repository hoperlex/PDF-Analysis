# RUNNER_API - the wire contract of the executor pull channel

Status: binding client-side specification, written ahead of the server slice `EXEC-PULL-01`
(owner ruling `R-144e`). The clients in this directory (`mcp_bridge.py`, `agent.py`, both
through `runner_client.py`) implement exactly this document. `EXEC-PULL-01` implements the
server side and may only change this file together with the clients and their tests in
`tests/unit/executor_runner/`.

A **runner** is a Claude Code session (through the stdio MCP bridge) or an unattended agent (bound to one connection, or, in
host mode, to a host: section 10).
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
  never writes it to disk or a log. The one exception is `redeemExecutorEnrollment` (section 9.1),
  whose bearer is a one-time enrollment secret that is exchanged for such a token.
- **Bodies.** Requests with a body use `Content-Type: application/json; charset=utf-8`.
  Responses with a body are `application/json`. Control request bodies are at most 1 MiB; a
  larger one is rejected `422 validation_failed`. `POST .../answer` has no application
  response-size ceiling: its complete JSON answer is validated against the task schema
  without a character or byte truncation (`HOTFIX-RUN-PARTIAL-1106`, contract 1.33.0).
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
{"wait_seconds": 25, "max_images": 4, "runner_instance_id": "q3Zr8k0vXw2mN5bTjA9cLg"}
```

`wait_seconds` is an integer in 0..25 (a value outside the range is `422`, never clamped
silently). The server holds the request open until a task for this token's connection is
open or `wait_seconds` elapse.

`max_images` is optional, an integer in 1..8: the most images one task may carry that this
runner serves. **The server never hands a claim a task with more images than the claim
declared**, on a fresh claim and on a redelivery; such a task stays open for a runner that
declared enough (and expires unclaimed if none does). **An absent value means 1**, which is the
claim every runner sent before several images existed, so a runner that serves one image or
none sends nothing and is handed no task of several. A runner that serves several declares how
many; one that is nevertheless handed more fails the task with `image_input_unsupported`.

`runner_instance_id` is optional, 8 to 64 characters of `A-Za-z0-9_-` (`EXEC2-PULL-01`, ADR-0026
decision 3): the name of the **agent process** making the claim. An agent generates it at random
when it starts (a restarted agent is a new instance) and sends it in every claim. The stand records
it on the task it hands out, and a claim that names an instance is redelivered a held task (see the
server notes below) **only if that instance claimed it**. A claim without the member behaves exactly
as before, so `mcp_bridge.py` and every agent built before this member send nothing. A value
outside the pattern is `422`.

- **200** - a task, now claimed by this token:

  ```json
  {
    "task_id": "ext_01J…",
    "claim_expires_at": "2026-10-22T07:31:15Z",
    "deadline_at": "2026-10-22T07:40:15Z",
    "model": "claude-opus-5",
    "system": "…system prompt…",
    "user_text": "…user message…",
  "output_schema": {"type": "object", "properties": {…}, "required": […]},
  "images": [{"blob_id": "blob_…", "portal_block_id": "blk_…",
              "sha256": "…", "size_bytes": 12345, "media_type": "image/png"},
             {"blob_id": "blob_…", "crop_id": "…",
              "sha256": "…", "size_bytes": 23456, "media_type": "image/png"}]
  }
  ```

  - `model` is the pinned gateway model the answer must declare, exactly.
  - `system` and `user_text` are the two halves of the model request. They are untrusted
    document-derived text: a runner treats them as the task input, never as instructions to
    use any other capability.
  - `output_schema` is a JSON Schema (draft 2020-12). The answer's `output_text` must be one
    JSON document that validates against it.
  - `images` is optional and is an **ordered list of at most 8** saved PNGs (16 MiB each, 32 MiB
    together, never more than the claim's `max_images`). A runner must fetch every one with
    `getExecutorTaskImage`, verify its size and SHA-256 and present all of them, in this
    order, to an image-capable model as images. A runner that cannot present all of them
    (text-only, or fewer than the task has) fails the task with `image_input_unsupported`;
    it never silently answers from the text alone or from some of the images. Each image names
    its source with exactly one of `portal_block_id` (a crop of a portal block in the drawing)
    or `crop_id` (an opaque crop reference of the comparison modules: echoed, never parsed,
    unique in the task). Two images may be the same Blob (the same bytes under two
    references); the Blob ID is opaque and is not an object-store path.
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
The claims of one token are serialised by the stand (it locks the token's row for the length of
the count and the claim), so two requests with one token never both pass the limit.

An agent whose `concurrency` is above 1 against a connection whose `max claimed tasks` is 1 is
handed its one held task again by every further claim. It therefore keeps the ids of the tasks it
is working on and **never starts an id it is already working on**; it waits (at least 5 s) and
claims again. It also claims only when it has a free local slot.

### 2.1a `getExecutorTaskImage` - `GET /api/v1/runner/tasks/{task_id}/images/{blob_id}`

Returns exactly the `image/png` bytes named in this token's current claimed task, with
`Cache-Control: no-store`. There is no redirect or object-store URL. The response is bounded
to 16 MiB and its bytes are checked against the task's digest and size. The runner repeats
that check before passing the PNG to a model. Unknown task, foreign connection or image is
`404`; a lost claim, expired deadline or ended Attempt is `409`. A revoked token is `401`.
The server makes the authorization check again after a slow Blob read.

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
`endpoint_failed`, `output_truncated`, `deadline_exceeded`, `agent_shutdown`,
`image_input_unsupported`, `image_delivery_failed`) optionally
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
- run **one agent process per token** (v1). Several worker threads of that process may work
  tasks at once, up to the connection's `max claimed tasks`; the process claims from one loop,
  so its claims never overlap. Two processes that present one token are not a supported
  topology: with `runner_instance_id` the stand does not redeliver one process's task to the
  other, but each process still counts against the same limit.

## 4. operationIds

| operationId | Method and path |
| --- | --- |
| `claimExecutorTask` | `POST /api/v1/runner/tasks/claim` |
| `getExecutorTaskImage` | `GET /api/v1/runner/tasks/{task_id}/images/{blob_id}` |
| `extendExecutorTaskClaim` | `POST /api/v1/runner/tasks/{task_id}/extend` |
| `submitExecutorTaskAnswer` | `POST /api/v1/runner/tasks/{task_id}/answer` |
| `failExecutorTask` | `POST /api/v1/runner/tasks/{task_id}/fail` |

All five use the runner token as their own principal type, never a user session, and are
not reachable with a user bearer token (and a runner token is refused on every other
operation). `task_id` is an identifier of the form `ext_<ULID>`; clients treat it as an
opaque string of `[A-Za-z0-9_-]{1,64}` and percent-encode it into the path.

## 5. Schemas (informative, JSON Schema 2020-12)

```json
{
  "ClaimRequest": {"type": "object", "additionalProperties": false,
    "properties": {"wait_seconds": {"type": "integer", "minimum": 0, "maximum": 25},
      "max_images": {"type": "integer", "minimum": 1, "maximum": 8},
      "runner_instance_id": {"type": "string", "pattern": "^[A-Za-z0-9_-]{8,64}$"}}},
  "ClaimedTask": {"type": "object", "additionalProperties": false,
    "required": ["task_id", "claim_expires_at", "deadline_at", "model", "system", "user_text", "output_schema"],
    "properties": {"task_id": {"type": "string"}, "claim_expires_at": {"type": "string", "format": "date-time"},
      "deadline_at": {"type": "string", "format": "date-time"}, "model": {"type": "string"},
      "system": {"type": "string"}, "user_text": {"type": "string"}, "output_schema": {"type": "object"},
      "images": {"type": "array", "maxItems": 8, "items": {"$ref": "#/RunnerImage"}}}},
  "RunnerImage": {"type": "object", "additionalProperties": false,
    "required": ["blob_id", "sha256", "size_bytes", "media_type"],
    "description": "exactly one of portal_block_id and crop_id",
    "properties": {"blob_id": {"type": "string"}, "portal_block_id": {"type": "string"},
      "crop_id": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"},
      "sha256": {"type": "string"}, "size_bytes": {"type": "integer", "maximum": 16777216},
      "media_type": {"const": "image/png"}}},
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

## 8. `EXEC2-PULL-01`: one process per token, and `runner_instance_id`

Nothing in sections 1 to 7 changed except the optional member of 2.1 and the sentence in section 3.
The stand (ADR-0026 decision 3) decided:

1. The claim locks the token's row (`SELECT … FROM executor_runner_token WHERE token_id = … FOR UPDATE`)
   as the first statement of its transaction, before it counts the token's held claims, so the count
   and the claim are one step per token. The order of locks is the token row, then task rows, nothing
   else.
2. The claimed task records the instance (`executor_task.claimed_by_instance_id`). It is set only
   while a token holds the claim and cleared when the lease lapses and the task returns to `open`.
3. At a limit of one, a claim that names an instance is redelivered only a task that instance claimed.
   A task held by another instance, or by a claim that named none, is not handed to it: its lease
   lapses and the task follows the re-open rule, so a restarted agent waits at most one lease for the
   task its predecessor held. A claim that names none is redelivered the held task as before, and the
   recorded instance is cleared. At a limit above one nothing is redelivered, as before.
4. The agent keeps the ids of the tasks in work and does not start an id twice (2.1). One token is
   served by one agent process; a multi-instance protocol for one token is a later decision.

## 9. `EXEC2-AGENT-01`: enrollment and health (contract 1.15.0)

Two operations outside `/api/v1/runner/tasks/`, added with the universal agent (ADR-0026 decisions 4 and 5). The
clients are `RunnerClient.redeem_enrollment` and `RunnerClient.report_health`; the stand's side is
`EXEC2-ENROLL-01`. Both follow section 1 (JSON bodies, `ErrorEnvelope`, no redirects, the credential never in a
URL or a log) and neither is reachable with a user session.

| operationId | Method and path | Bearer |
| --- | --- | --- |
| `redeemExecutorEnrollment` | `POST /api/v1/runner/enroll` | the enrollment secret |
| `reportRunnerHealth` | `POST /api/v1/runner/health` | the runner token |

### 9.1 `redeemExecutorEnrollment` - `POST /api/v1/runner/enroll`

An administrator issues a one-time **enrollment secret** for a `pull` connection (`issueExecutorEnrollment`). It is
shown once with the install command and is stored by the stand as a hash only. It has the shape
`ame_<8 lower-case alphanumerics>_<43 of A-Za-z0-9_->`, expires after **15 minutes**, is single use and is bound to
one connection. The agent exchanges it for a runner token:

```http
POST /api/v1/runner/enroll
Authorization: Bearer ame_k3j9x2mq_…
Content-Type: application/json; charset=utf-8

{"runner_instance_id": "Qx7…", "agent_version": "0.9.0"}
```

`runner_instance_id` (required, `^[A-Za-z0-9_-]{8,64}$`) names the install; `agent_version` is optional (the contract's
`^[0-9A-Za-z][0-9A-Za-z.+_-]{0,63}$`). The secret is the bearer of this call only: the four task operations and
`reportRunnerHealth` refuse it as they refuse any wrong token, and this operation refuses a runner token.

- **201** - `{"token": "amr_…", "runner_token": {…}}` (`IssuedRunnerToken`). `token` is 56 characters and is **shown
  once**; `runner_token` is the token's metadata (`RunnerTokenMetadata`, no secret). The runner stores the token and
  nothing else of the answer, and from then on uses it as in sections 1 to 8.
- **The repeat.** A repeat of the call with the **same `runner_instance_id` inside the 15-minute window** is
  idempotent for the runner that lost the answer: the stand **revokes the token it minted before and returns a fresh
  one**, so the runner stores only the newest. The stand never stores the secret's value.
- **409** `conflict` with `conflict_reason` `enrollment_redeemed` - the secret was redeemed by **another** instance, or
  this instance repeats **after the window**; `connection_archived` is refused the same way. The runner does not retry;
  a new enrollment is issued in the stand UI. (A host that already holds a working token keeps it.)
- **401** `authentication_required` - the secret is unknown, **expired** or **revoked** (the answer does not say
  which). Stop; do not retry.
- **422** `validation_failed` - a malformed body. 429 and 5xx as in section 1; the exchange may be repeated with the
  same `runner_instance_id` inside the window.

Client rules. The secret comes from the environment only (`AUDITMANAGER_ENROLLMENT_SECRET`), never an argument, a file
or a log line, and is removed from the process environment at once. The install keeps one `runner_instance_id` (a
random value stored beside the environment file) so that a rerun after a lost answer is the idempotent repeat above
and a command pasted on a second host is a different instance (409). The runner token is written to the environment
file (mode 0600) before the agent starts, and the secret is never written.

### 9.2 `reportRunnerHealth` - `POST /api/v1/runner/health`

The agent tells the stand what it is. Runner token as bearer. The report is stored on the calling token and is
returned in `RunnerTokenMetadata` (`agent_version`, `clis`, `concurrency`, `execution_profile`, `features`,
`health_reported_at`, and `online`, the freshness of `last_seen_at`). It is not an event: nothing is journalled. The
operation is throttled with the runner zones like the task operations.

```json
{"agent_version": "0.9.0",
 "clis": [{"cli": "claude", "installed": false, "auth_state": "unknown"},
          {"cli": "codex", "installed": true, "version": "0.46.0", "auth_state": "valid"}],
 "concurrency": 1, "execution_profile": "command", "features": [],
 "runner_instance_id": "Qx7…"}
```

`ReportRunnerHealthRequest`, `additionalProperties: false`:

| Member | Required | Values |
| --- | --- | --- |
| `agent_version` | yes | `^[0-9A-Za-z][0-9A-Za-z.+_-]{0,63}$` (`unversioned` when the agent runs from a checkout) |
| `clis` | yes | at most 8 `RunnerCliHealth` |
| `concurrency` | yes | integer 1..16 |
| `execution_profile` | yes | `command` or `endpoint` |
| `features` | yes | at most 8 of `images` (the agent serves tasks that carry images) |
| `runner_instance_id` | no | the process id of the claims (`^[A-Za-z0-9_-]{8,64}$`) |

`RunnerCliHealth` is `{"cli": "claude" | "codex", "installed": bool, "version"?: string, "auth_state": "valid" |
"login_required" | "unknown"}`; `version` matches `^[0-9A-Za-z][0-9A-Za-z._+-]{0,63}$`.

**Coherence rules** (the stand answers `422 validation_failed` to a report that breaks one, so a client never builds
one):

- a client named in `clis` appears once;
- a client with `installed: false` carries **no `version`** and `auth_state: "unknown"`;
- `auth_state` is read only through the client's own status command (`codex login status`, `claude auth status`) and
  is `unknown` when the client is absent, too old to ask, or the answer is not understood; it is never a credential, a
  path or an account name. Nothing else about the machine is sent: no path, no token, no document text.

- **200** - `{"recorded_at": "<RFC 3339>"}`.
- **401**, **422**, **429**, **5xx** as in section 1. A **401** ends the reporter and leaves the exit to the claim loop,
  which meets the same 401. A **404** (a stand without the operation) and a **422** are logged and the report is tried
  again only at the next interval.

Cadence. The agent reports at start, again whenever what it detects changes (it detects every 60 s), and otherwise
every 600 s. It reports from a thread of its own and never delays a claim. (A host agent, section 10, reports every 60 s.)

## 10. `HOSTS-AGENT-01`: host mode (one process, one host token)

Plan v3 (`executors-runs-rework-plan-2026-11-09`, section 5) and the owner's answers R-153d. A **host agent** is one process
that holds one **host token** (bound to a host, `exh_<ULID>`, not to a connection) and serves every model its machine can
reach: the `claude` and `codex` CLIs the service user is signed in to, and the API providers whose key is in the service's
key file. No model is chosen at install. Sections 1 to 9 hold unchanged, except where this section says otherwise; an agent
whose token is bound to a connection (a "single-model agent") speaks exactly the wire of sections 1 to 9 and nothing here
(section 10.9). `HOSTS-SEAL-1` writes the same text into the stand's contract; where the two differ, that is a defect in one
of them.

### 10.1 Enrollment (`redeemExecutorEnrollment`)

The request is the one of 9.1: the bearer is the one-time secret of a **host** enrollment and the body is
`{"runner_instance_id", "agent_version"}`. No model is sent or asked for. The `201` document is

```json
{"token": "amr_…", "host_id": "exh_01J…", "catalogue": [ … ], "runner_token": {…}}
```

`token` is the runner token bound to the host (the same 56 characters as in 9.1). `host_id` matches
`^exh_[0-9A-HJKMNP-TV-Z]{26}$`. `catalogue` is the array of 10.2. `runner_token` (the metadata of 9.1) is **optional** in a
host document. The agent stores the token and nothing else of the answer, prints the host id and goes on; it takes its
catalogue from the answers of 10.3, so a restart needs no stored copy. The repeat and `409` rules of 9.1 hold.

### 10.2 The catalogue

An array of objects, each `{"provider", "model_id", "efforts", "accepted_reported"}`:

| Member | Values |
| --- | --- |
| `provider` | `claude_code`, `codex`, `anthropic_api`, `openai_api`, `openrouter_api` |
| `model_id` | the id sent to the CLI or API, `^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$` (`/` and `:` are for OpenRouter ids) |
| `efforts` | non-empty array of lower-case words, the efforts a task may name for this model |
| `accepted_reported` | array of strings the provider may report for this model besides `model_id` itself (a dated id, an alias); may be empty |

The agent leaves out an entry that is not well formed (and logs which one, never its content): that model is simply not
served. A model that is in the catalogue but whose provider is absent from the host is not reported at all.

### 10.3 Health report (`reportRunnerHealth`)

The body of 9.2 gains two members; every member of 9.2 is still sent and means what it meant:

```json
{"agent_version": "0.21.0", "clis": [ … ], "concurrency": 3, "execution_profile": "command", "features": [],
 "runner_instance_id": "Qx7…",
 "providers": [
   {"provider": "claude_code", "access": "subscription", "cli_version": "2.1.310", "auth_state": "valid",
    "models": [{"model_id": "claude-opus-5-5", "state": "verified", "checked_at": "2026-11-09T12:00:00Z"},
               {"model_id": "claude-sonnet-5-5", "state": "failed", "checked_at": "2026-11-09T12:00:05Z",
                "failure_code": "quota_exceeded"}]},
   {"provider": "anthropic_api", "access": "api", "auth_state": "valid", "models": [ … ]}],
 "slots": {"claude_code": 1, "anthropic_api": 2}}
```

* `providers[]`: one entry for each provider **detected** on the host (a CLI that is installed, an API whose key is in the
  key file), in the order `claude_code`, `codex`, `anthropic_api`, `openai_api`, `openrouter_api`.
  * `access`: `subscription` or `api`. For a CLI it is read from the CLI's own status command (`claude auth status`,
    `codex login status`): a subscription login is `subscription`, a login with an API key is `api`. An API provider is
    always `api`. A CLI that is not signed in is reported `subscription` with `auth_state: login_required`; one signed in by a
    method the agent does not recognise is reported `api` with `auth_state: unknown` and **no verified model**.
  * `cli_path` (optional): the CLI's absolute path. **Omitted by default** (ADR-0026 decision 8: a path stays on the host);
    the operator can turn it on in `agent.toml`. `cli_version` (optional): the CLI's version, as in `clis`.
  * `auth_state`: `valid`, `login_required` or `unknown`. For a CLI it is the status command's answer; for an API provider
    it is `valid` once a model has been verified, `login_required` when the provider refused the key, else `unknown`.
  * `models[]`: one entry for each catalogue model of that provider: `model_id`; `state` `verified` (a minimal call of this
    model succeeded and the model that answered is the requested one or an accepted one), `not_verified` (not checked yet,
    or the provider cannot be used now) or `failed` (the last call failed); `checked_at` (RFC 3339 UTC, when the state was
    established); `failure_code` (only with `failed`, `^[a-z][a-z0-9_]{0,63}$`). The codes the agent uses are
    `quota_exceeded`, `auth_failed`, `model_not_found` (the host's access) and `claude_*`, `codex_*`, `api_*`,
    `reported_model_mismatch`, `timeout`, `probe_bad_answer` (anything else).
  * No key, token, account, path (unless opted in) or text of a provider's answer is in the report.
* `slots`: `{provider: integer ≥ 1}` for each provider in `providers`: the most calls of that provider the host runs at once.
  The default is 1 for `access: subscription` and 2 for `access: api`, overridden in `agent.toml`.
* `concurrency` is the sum of the slots, at most 16 (and at least 1). `execution_profile` is `command`. `features` is `[]`
  unless the operator turned images on.

**The answer** to an accepted report is `{"recorded_at": …, "catalogue": [ … ], "enabled": true}`: the current catalogue (10.2)
and the host's «Использовать» switch. A stand that leaves `catalogue` out leaves the agent with the one it has (none, at
start: nothing is checked and nothing is claimed); `enabled` is logged. **`enabled: false` does not stop claims**: the switch
keeps the stand from binding new runs to the host, and the runs already bound finish their work.

**Cadence and recount.** The agent runs *cheap detection* every 60 s (the CLIs' presence, version and login, and the key file;
no model is called) and sends a report with every cycle: a heartbeat, which the stand reads as the host's pulse (older than
120 s is no pulse). The report is built from a snapshot that is rebuilt **only when something in it changed** (detection, a
check's result, the catalogue), so consecutive heartbeats carry the same body, and a change is sent at once instead of waiting
for the next cycle. A *minimal model call* for each catalogue model of a provider is made when that provider is new or its
login, key, CLI version or access changed (the models go back to `not_verified` until it passes), when the model is new in
the catalogue, every **6 hours** for a verified model (configurable) and every **15 minutes** for a failed one. A check runs
inside the provider's slot, so it never exceeds the slots; the effort used is the lowest the model has. A real call that
fails for a reason about the host's access (`quota_exceeded`, `auth_failed`, `model_not_found`) puts that model to `failed`
at once, so that the next report tells the stand.

### 10.4 Claim (`claimExecutorTask`)

Called with the host token, with the body of 2.1. The agent claims only while at least one model is `verified` and a slot is
free behind one. The task gains these members, all present or none (`LIMITS-01`, contract 1.49.0: the six below; a stand older than that
also sent `max_output_tokens`, which this agent never reads -- no answer cap reaches a model, owner ruling `R-153n`):

| Member | Values |
| --- | --- |
| `provider`, `access` | as in 10.3 |
| `model_id` | the catalogue's id; `model` (section 2.1) is the same string |
| `effort` | one of that model's catalogue `efforts` |
| `timeout_seconds` | integer, the time the call may take: the stand's constant of the stage row or comparison kind (the original's, `R-153o`) cut to what the attempt watchdog leaves (the agent also stops at `deadline_at`) |
| `cell_key` | opaque string naming the stage cell the task is for; logged, otherwise echoed nowhere |

**The agent refuses any task whose model it does not currently report as verified for that provider and access**, and a
task whose `effort` is not one of the model's: it calls `failExecutorTask` with `model_not_available: …` or
`effort_not_allowed: …` before anything runs. A task with none of the members above is failed `host_task_incomplete`; one that
carries images the host does not take (or that the provider's command cannot take: Claude Code) is failed
`image_input_unsupported`.

### 10.5 Extension (`extendExecutorTaskClaim`)

Sent as in 2.2, but **only while the call has produced output** in the last 600 s (configurable; `R-153p`, it was 120 s -- deliberately equal to the
stand's stall window of 600 s): bytes on the CLI's stdout or
stderr, or a streamed chunk or keep-alive of an API response. A hung CLI or API call therefore lets its claim lapse: the agent
stops extending, stops the call, frees its slot, and submits nothing and fails nothing (the stand's lease rule takes the task
back). A call that is only waiting for a free slot counts as silent for this purpose.

### 10.6 Answer (`submitExecutorTaskAnswer`)

```json
{"output_text": "{…}", "model": "claude-opus-5-5", "provider": "claude_code", "access": "subscription",
 "reported_model": "claude-opus-5-5-20261001", "usage": {"input_tokens": 1234, "output_tokens": 321}}
```

`model` is the task's `model_id`. `reported_model` is the **exact string the CLI or API reported** (for the Claude Code CLI the
one key of `modelUsage`; for the APIs the model of the stream; for Codex, whose events name none, the model asked for, and a
`model.rerouted` event fails the call); the agent itself refuses a reported model that is neither `model_id` nor in the
catalogue's `accepted_reported`, and the stand checks the same (`R-133`). `provider` and `access` repeat the task's. `usage` is
sent when the provider gave a count; `input_tokens` and `output_tokens` are **not** sent at the top level by a host agent.

A call that cannot be answered is failed with a reason `<code>: <detail>` (section 2.4): `model_not_available`,
`effort_not_allowed`, `host_task_incomplete`, `image_input_unsupported`, `quota_exceeded`, `auth_failed`, `model_not_found`
(the host's access: the model also leaves service, 10.3), or a fixed word of the answerer (`claude_turn_failed`,
`codex_timeout`, `api_unavailable`, `output_truncated`, `answer_not_json`, `reported_model_mismatch`, `timeout` …). No detail
holds text of the document, of the provider's answer or a key.

### 10.7 Slots

Within a provider the agent never runs more concurrent calls (tasks and checks together) than that provider's `slots`; a task
claimed for a provider whose slots are full waits for one (its claim is not extended while it waits, 10.5).

### 10.8 The key file and the direct APIs

`/etc/pdf-analysis-agent/keys.env` (path configurable): lines `NAME=value` with `NAME` one of `ANTHROPIC_API_KEY`,
`OPENAI_API_KEY`, `OPENROUTER_API_KEY` (an optional `export `, optional quotes; every other line is not read). It is read only
when it is a regular file (not a link), **mode 0600 and owned by the user running the agent**; otherwise it is ignored and the
journal says why (`mode_is_not_0600`, `not_owned_by_the_service_user`, `not_a_regular_file`, `unreadable`, `too_large`). A key
gives the provider `anthropic_api`, `openai_api` or `openrouter_api`, `access: api`. It is read afresh for each call (a rotated
key is used at once and its models are checked again), goes into one request header of one HTTPS request to the provider
(Anthropic Messages, OpenAI Responses, OpenRouter chat completions, each streamed) and nowhere else: not in a report, a log,
an answer or the environment of any child process. **A call through a key sends the document text to that provider** (a path
out of the stand, `D-291`).

### 10.9 Compatibility

A token bound to a connection keeps the earlier wire: `reportRunnerHealth` without `providers` and `slots`, the claim without
the host members, `submitExecutorTaskAnswer` with `model` and the top-level token counts. `agent.py` keeps that code path for
`[executor] mode = "command"` and `"endpoint"`; the host path is `mode = "host"`. `install.sh --upgrade` converts an installed
single-model agent to host mode with a new enrollment secret.

### 10.10 What the stand's side must match (the points beyond the plain list)

1. A host task carries `model` equal to `model_id` (the earlier tooling reads `model`); the agent also accepts a task that has
   `model_id` only.
2. A host enrollment document may omit `runner_token`; it must carry `host_id` and the token.
3. The report keeps `clis`, `concurrency` (sum of slots), `execution_profile: command`, `features`; the agent does not send a
   new `execution_profile` value.
4. `access` of a CLI that is not signed in is `subscription`; of one signed in unrecognisably, `api` with `auth_state: unknown`.
5. `failure_code` is free-form within `^[a-z][a-z0-9_]{0,63}$`; the stand may group the three access codes of 10.3.
6. `cli_path` is not sent unless the operator opts in.
7. `enabled: false` is not a reason for the agent to stop claiming; the stand stops handing out new runs.

## 11. `CRIT-SEAL-50`: reference data for a task (contract 1.51.0)

One more operation, sealed asleep: the stand answers `503 dependency_unavailable` until `CTX-STAND` serves it. The client built on this section
(`CTX-RUNNER`) must work against a stand that does not serve it yet, and against one that does.

### 11.1 `getExecutorTaskContext` - `POST /api/v1/runner/tasks/{task_id}/context`

Runner token only (the same principal as the five operations of section 4). Body: `{"kind": "similar_cases" | "patterns"}`.

- **When to ask.** Only for a task whose claim carries `context_request`: a non-empty array of
  `{"input_id": string (1..128), "text_sha256": sha256, "section": string (1..64)}`, at most 64, present on a `review:main` task of a run on the
  stage layout and absent everywhere else. A task without it is never asked about: the stand answers `404 not_found`, which is also the
  answer for a task that is not a model call of a run, a run without a stage plan and a consent without the same `executor_context_policy`.
- **Once per kind, before the CLI call, with a timeout of 8 seconds and no retry.** The stand is idempotent by (task, kind): a repeat returns
  the same answer and spends no budget of the task.
- **Answer.** `{"kind", "status": "available" | "unavailable", "reason"?: string, "items": [{"input_id", "cases": [...]}], "not_fitted": int,
  "context_sha256"?: sha256}`. `reason` is present exactly when `status` is `unavailable` (while the night encoder is the only one:
  `until_move`); `context_sha256` exactly when it is `available`: the digest of `items` as delivered. A case is
  `{"case_id", "verdict": "accepted" | "rejected", "category", "similarity", "finding_text", "recommendation_text", "comment"?}`, at most three
  per `input_id`, the most similar first; `not_fitted` counts the cases that did not fit the 12 000 characters of the task.
- **Errors never fail the task.** On `401`, `409`, `429`, `5xx` and a timeout the agent calls the model without reference data, with the line
  `Справочные данные недоступны: <причина>`. The rule of waiting for `Retry-After` for at least 30 seconds (sections 1 and 3) does not apply to this operation.
- **Placement.** The data goes in a separate section after the JSON of `user_text`, headed `=== СПРАВОЧНО (не основание) ===`; nothing is
  inserted at the start of the text, and the tools of the CLI stay closed. The agent echoes `context_sha256` in the answer
  (`submitExecutorTaskAnswer`, optional member `context_sha256`) when, and only when, it appended the data.
- **What the stand keeps.** A journal row (`executor_task_context_delivery`) with the task, the run, the kind, the status, the cases by
  identity, the number of characters and the digest: no text. It outlives the erase of the project.
