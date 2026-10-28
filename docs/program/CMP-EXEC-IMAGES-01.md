# CMP-EXEC-IMAGES-01 — up to eight images per executor task, gated on the server by the claim's `max_images`

Lane of wave C0 (`docs/program/dispatch/CMP-WAVE-C0.md`), branch `agent/cmp-exec-images-01`, base `cc3dd36b` on
`integration/compare-modules`. ADR-0025 decision 18. Task file: `docs/program/tasks/CMP-EXEC-IMAGES-01.md`.
No contract, no migration, no dependency change (the wire models already carried `RunnerImage.crop_id`,
`ClaimedExecutorTask.images` up to 8 and `ClaimExecutorTaskRequest.max_images` after `CMP-SEAL-C0`).

## 1. Result

* A model request carries an **ordered list of up to 8 images** (16 MiB each, 32 MiB in all). Each is a descriptor
  `{blob_id, sha256, size_bytes, media_type}` plus **exactly one** identity: `portal_block_id` (the one-image
  portal-block crop of the section runs, unchanged) or `crop_id` (an opaque crop reference of the comparison
  modules, pattern `^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$`, echoed and never parsed, unique in the request).
* Every served channel carries every image, in order: direct HTTP and VPN (OpenAI Chat `image_url` blocks,
  Anthropic Messages `image` blocks), SSH tunnel (the same HTTP adapters), SSH command (stdin `image` member), and
  the pull channel (task payload, `getExecutorTaskImage` per blob) for the three runner tools: the agent's command
  mode (`local_images`, `codex_answer.py` with one `--image` each), the agent's local-endpoint mode and the MCP session.
* **The server never hands a task to a claim whose declared `max_images` is smaller than the task's image count; an
  absent value means 1.** The gate is one SQL condition in the two statements that hand a task out (`claim_next`,
  `redeliver`). A task too wide for a claim is skipped, not waited on, so it does not block the tasks behind it; it stays
  open for a runner that declared enough and expires unclaimed (`no_executor_online`) if none does.
* A runner tool that cannot serve all the images **refuses the whole task** (`image_input_unsupported`, or
  `image_delivery_failed` when one image cannot be fetched or verified) and never answers on a subset.
* The one-image portal-block path is unchanged: every test that existed before this lane passes unmodified except
  three stand-in ports that gained the `max_images=None` keyword (section 7).

## 2. The API for comparison callers

Import from `auditmanager.executors.public` (no deep import):

```python
from auditmanager.analysis.public import ModelRequest
from auditmanager.executors.public import CropImage, attach_images, image_load, MAX_IMAGES

base = ModelRequest(model_id=..., body={... the system, messages, output_config as for any request ...})
request = attach_images(base, [
    CropImage(crop_id="a-1", data=png_bytes_of_crop_from_sheet_a),
    CropImage(crop_id="b-1", data=png_bytes_of_crop_from_sheet_b),
])                                  # 1..8 crops, in the order the model must see them
load = image_load(request)          # ImageLoad(count=2, total_bytes=...): what the estimate counts (decision 18)
response = adapter.complete(request)  # any adapter of any served channel
```

* `attach_images` returns a **new** `ModelRequest` whose `body["images"]` holds one descriptor per crop (blob id
  derived from the digest and size, so two crops with identical bytes are one Blob under two references) and whose
  `images_bytes` holds the bytes. `request.request_sha256` covers the descriptors, so the digest binds every crop's
  bytes, its `crop_id` and its **place in the list**; the bytes themselves never enter the body or the call journal.
* It checks every limit at once and raises `ProxyDispatchError` (`analysis_input_invalid`, `dispatch_class="not_sent"`,
  `retry_safe=False`; the message names a fixed reason word) for: more than 8 crops, a crop above 16 MiB, more than
  32 MiB in all, a `crop_id` outside the pattern, a `crop_id` twice, bytes that are not a PNG, a request that already
  carries an image. No crops returns the request unchanged.
* **The caller's prompt must say what each image is** (by position or by `crop_id`): the transports attach the images
  after the user text in list order and add no labels of their own. The pull tools additionally name each image in
  their own instruction (`codex_answer.py` prompt; the MCP result's `image_references`).
* Every adapter re-verifies descriptors against bytes (`checked_pngs`) before a key, prompt or image leaves the
  process; a count mismatch, a swapped order, a changed byte or a list outside the limits is refused `not_sent`.
* A pull call (`PullAdapter`) writes the descriptors only; the runner fetches the bytes by blob id from the stand
  (`getExecutorTaskImage`, which serves a crop exactly as it serves a portal-block crop, bound to the current claim and
  Attempt, re-checked after the Blob read). The bytes must therefore be in the store under the descriptor's blob id
  when the task is claimed; this lane does not store them (the comparison stage that saves the crop does).
* `ModelRequest.image_bytes` (one) still works exactly as before; `image_bytes` and `images_bytes` are exclusive.
* A runner that refuses the images makes `PullAdapter.complete` raise `ProxyDispatchError` with
  `dependency: executor_image_input_unsupported` (class `outcome_unknown`, as for every failure after a claim: only the
  runner can say no model ran; `CMP-SPEND-01` owns what that means for a comparison call's journal).

## 3. The gate on the server

`POST /runner/tasks/claim` body `{"wait_seconds": n, "max_images": k}`; `max_images` 1..8, absent = 1 (the contract's
description). Path: router `claim_executor_task` (`body.max_images`) -> `RunnerPort.claim_task(max_images=)` ->
`RunnerAdapter` -> `executors.public.claim_task` -> `executors.runner.claim_task` (`None` -> `DEFAULT_CLAIM_IMAGES` = 1)
-> `RunnerRepository.redeliver` and `claim_next`, both with `AND <image count of the payload> <= :max_images`.

* The image count is read from the payload's `images` member: absent = 0; a JSON array = its length; **anything else
  (an object, a string, a number, JSON null) counts as 9**, so a malformed payload is never handed to any claim (the gate
  fails closed and never reads a malformed list as an empty one).
* A claim that re-claims while it holds a multi-image task with a narrower declaration is **not** redelivered it; its
  lease lapses and the task returns to `open` for a claim that declared enough.
* `RunnerRepository` refuses (`ValueError`) a `max_images` outside 1..8 before any statement; the wire model refuses it
  with `422` first (`0`, `9`, `-1`, `1.5`, `null`). Note: pydantic's lax mode coerces `"2"` and `true` to integers
  (`true` -> 1), which is the sealed model's behaviour and harmless here.

## 4. Per channel

| Channel | How the images travel | Refusal of what cannot be served |
| --- | --- | --- |
| `http_api` direct/VPN, OpenAI Chat | one `image_url` data-URL block per image after the text, in order (`add_openai_images`) | `checked_pngs` before the key is read |
| `http_api` direct/VPN, Anthropic Messages | one `image` base64 block per image, in order (`add_anthropic_images`) | same |
| `http_api` SSH tunnel | the HTTP adapters through the pinned forward | `checked_pngs` before the tunnel opens |
| `ssh_command` | stdin task `image`: **one object for one image (unchanged)**, a **list of objects** for 2..8; the task cap is 24 MiB for at most one image and 48 MiB for several | `checked_pngs` before the network; a remote command that predates several images checks `image` for an object and **refuses a list** (`invalid image envelope`, exit 64): proven against the script the repository had before (`tests/unit/executor_runner/frozen_ssh_forced_command_one_image.sh`). A list is never sent under a new member name, which that command would ignore and answer from the text alone |
| `pull` + agent, command mode | the claim's images fetched (once per distinct blob), verified, written to private files, listed in `local_images` in order, removed when the command ends | `max_images` declared from `[command]`; more images than declared, or `accept_images` false: `image_input_unsupported` before any fetch; any image that fails: `image_delivery_failed`, command never runs |
| `pull` + agent, endpoint mode | one `image_url` block per image in order (it used to send the **last** image only) | `[endpoint] max_images`, `accept_images`; same refusals |
| `pull` + `codex_answer.py` | one `codex exec --image` per image, in order; the prompt names each (`portal block` or `crop`) and says to use all of them | `read_task` refuses > 8, > 32 MiB, a descriptor with no or two identities, a local copy that differs, a missing copy |
| `pull` + MCP bridge `--accept-images [--max-images N]` | all images as MCP image content after the text; `image_references` lists them; `image_notice` tells the session to answer only if it sees all and otherwise `report_failure image_input_unsupported` | declares `N` (default 1); a task wider than `N`, or any failing image: failed whole |
| `pull` + `claude_answer.py` | unchanged: refuses every image (the CLI runs with no tool) | `image_input_unsupported` |

`runner_client.py` sends `max_images` **only above 1**, so a runner that serves one image or none speaks exactly the
wire it always spoke (a stand older than `1.9.0` would refuse the new member), and checks every claimed task's `images`
(at most 8, exactly one identity each, no identity twice, 16 MiB each, 32 MiB in all) as a malformed-task refusal.

## 5. What changed (40 files against `cc3dd36b`)

Source: `analysis/text/adapter.py` (`ModelRequest.images_bytes`), `executors/image_input.py` (rewritten: limits,
`checked_descriptors`, `checked_pngs`, `checked_png`, `CropImage`, `crop_descriptor`, `attach_images`, `image_load`,
`add_*_images`), `executors/pull.py` (payload from the shared check, the named refusal), `executors/http_adapter.py`,
`executors/ssh_adapter.py`, `executors/ssh_tunnel_adapter.py`, `executors/runner_repository.py` (the gate),
`executors/runner.py`, `executors/public.py` (the caller API), `bootstrap/runner.py`, `api/routers/runner.py`,
`api/routers/ports.py` (`max_images` carried to the SQL).

Tools: `runner_client.py`, `agent.py`, `mcp_bridge.py`, `codex_answer.py`, `ssh-forced-command.sh`,
`agent.example.toml`, `RUNNER_API.md`, `README.md`.

Tests: new `tests/integration/executors/test_claim_image_gating.py`, `tests/unit/executors/test_claim_image_declaration.py`,
`tests/unit/executors/crop_support.py`, `tests/unit/executor_runner/frozen_ssh_forced_command_one_image.sh`; extended
`test_image_input`, `test_http_adapter`, `test_ssh_adapter`, `test_ssh_tunnel_adapter`, `test_pull_images`,
`test_pull_adapter`, `test_runner_seam`, and the runner suites (`_support`, `test_agent`, `test_mcp_bridge`,
`test_runner_client`, `test_codex_answer`, `test_ssh_forced_command`).

## 6. New or changed contracts

None. `contracts/**` untouched (`git diff cc3dd36b HEAD --stat -- contracts` is empty; contract `1.9.0`, 115 / 130 / 351,
head `0038_comparison_foundation`). The wire contract of the runner is `tools/executor-runner/RUNNER_API.md`, which this
lane updated together with the clients and their tests (as that file requires): `max_images` in the claim, `images` as an
ordered list of at most 8, `crop_id` beside `portal_block_id`, the two new failure codes `image_input_unsupported` and
`image_delivery_failed` in the list of `fail` reasons.

## 7. Checks

Environment: `.venv` of `cmp-seal-c0` (symlink), `PYTHONPATH=$PWD/src`, `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent`;
own containers `auditmanager-cmp-exec-images-01` (PostgreSQL 57740, MinIO 61740 / 61741, database
`auditmanager_cmp_exec_images_01`, bucket `auditmanager-cmp-exec-images-01`), `make up`, `make migrate` to
`0038_comparison_foundation`, `make down` at the end. `df -h /` before the start: 3.3 GiB free (above the 1.5 GiB
stop line); 2.7 GiB at the end of the longest run. Premise printed first (`P-01` of the task file): contract `1.9.0`,
115 / 130 / 351, 27 error codes, head `0038_comparison_foundation`, `VERSION 0.9.0`: equal, no STOP.

| Command (from the worktree root) | Result |
| --- | --- |
| `git diff --check` | clean |
| `python -m pytest -q tests/unit/executors tests/unit/executor_runner` | **897 passed** in 89 s (before this lane's tests: 623 + 172 = 795, so 102 are new) |
| `python -m pytest -q tests/integration/executors` (lane PostgreSQL and MinIO) | **248 passed, 16 skipped** in 188 s (the 16 are the opt-in local sshd tests: `EXEC_SSHD_PORT` and `EXEC_LOCAL_SSHD` are not set); 20 of the passed are new (`test_claim_image_gating.py` 19, `test_runner_seam.py` 1) |
| `python -m pytest -q tests/contract` minus `test_cp00_candidate.py`, `test_validate_bootstrap.py`, `test_cp00_final_state.py` (the three `D-220` files) | **1307 passed**, 19283 subtests passed, 182 s |
| the 38 quoted mutations of section 8 | **38 of 38 red**; the tree was proven byte-identical to `HEAD` after each (`git diff --quiet`) |

Existing tests edited (all mechanical): the three stand-in ports `_Port.claim_task` (`test_runner_long_poll_cap.py`),
`StubRunner.claim_task` (`test_runner_seam.py`) and `DeliveringRunner.claim_task` (`test_runner_client_wire.py`) gained
`max_images=None`, because the router now passes the keyword; `FakeStore.failed` in `test_pull_adapter.py` gained an
optional reason. No assertion was weakened or removed.

One load-sensitive flake, in a test that sends no image and is not caused by this lane:
`test_mcp_bridge.py::test_the_token_never_appears_in_results_stdout_or_stderr` saw the bridge exit with `-6` (an abort at
interpreter shutdown while a daemon thread writes to stderr: the test revokes the token, so the claim keeper logs a refused
extension as the process ends) twice: once in a run of the file and once in the last confirmation run of 1,049 tests on the final
tree (`1 failed, 1048 passed`, the failing test being that one). Measured to place it: on a copy of the **base** `tools/` and
`tests/unit/executor_runner` the file failed once in 28 runs, on this tree alone 0 of 16 runs failed, and the test passes alone
every time. Whoever gates this should expect it under load and rerun the file.

## 8. Mutation proofs (every guard shown failing, then restored)

Each row: the text was replaced as quoted in the appendix, the named files were run, the file was restored and the tree
compared with `HEAD`. `u/` is `tests/unit/`, `i/` is `tests/integration/`.

| # | Guard | File | Run | Files |
| --- | --- | --- | --- | --- |
| M01 | claim_next ignores max_images (the ADR row 11 mutation) | `src/auditmanager/executors/runner_repository.py` | 9 failed, 10 passed | i/executors/test_claim_image_gating.py |
| M02 | redeliver ignores max_images | `src/auditmanager/executors/runner_repository.py` | 1 failed, 18 passed | i/executors/test_claim_image_gating.py |
| M03 | an absent max_images means eight, not one | `src/auditmanager/executors/runner_repository.py` | 4 failed, 27 passed | i/executors/test_claim_image_gating.py, u/executors/test_claim_image_declaration.py |
| M04 | the router drops the claim's max_images | `src/auditmanager/api/routers/runner.py` | 8 failed, 39 passed | i/executors/test_claim_image_gating.py, i/executors/test_runner_seam.py |
| M05 | the adapter drops the claim's max_images | `src/auditmanager/bootstrap/runner.py` | 7 failed, 12 passed | i/executors/test_claim_image_gating.py |
| M06 | a malformed images member counts as none | `src/auditmanager/executors/runner_repository.py` | 5 failed, 26 passed | i/executors/test_claim_image_gating.py, u/executors/test_claim_image_declaration.py |
| M07 | the claim loop passes the default to the fresh claim, not the declared value | `src/auditmanager/executors/runner.py` | 12 failed, 19 passed | i/executors/test_claim_image_gating.py, u/executors/test_claim_image_declaration.py |
| M08 | a ninth image is allowed | `src/auditmanager/executors/image_input.py` | 3 failed, 34 passed | u/executors/test_image_input.py, u/executors/test_pull_images.py |
| M09 | the 32 MiB total is not checked | `src/auditmanager/executors/image_input.py` | 2 failed, 35 passed | u/executors/test_image_input.py, u/executors/test_pull_images.py |
| M10 | the 16 MiB per image is not checked | `src/auditmanager/executors/image_input.py` | 3 failed, 34 passed | u/executors/test_image_input.py, u/executors/test_pull_images.py |
| M11 | a crop reference may repeat | `src/auditmanager/executors/image_input.py` | 2 failed, 35 passed | u/executors/test_image_input.py, u/executors/test_pull_images.py |
| M12 | a descriptor may carry both identities | `src/auditmanager/executors/image_input.py` | 2 failed, 35 passed | u/executors/test_image_input.py, u/executors/test_pull_images.py |
| M13 | the number of byte strings need not match the number of descriptors | `src/auditmanager/executors/image_input.py` | 5 failed, 52 passed | u/executors/test_image_input.py, u/executors/test_http_adapter.py, u/executors/test_ssh_adapter.py |
| M14 | the digest of each image is not checked against its descriptor | `src/auditmanager/executors/image_input.py` | 3 failed, 44 passed | u/executors/test_image_input.py, u/executors/test_http_adapter.py |
| M15 | the opaque crop reference pattern is not enforced | `src/auditmanager/executors/image_input.py` | 1 failed, 17 passed | u/executors/test_image_input.py |
| M16 | the pull task keeps only the first reference | `src/auditmanager/executors/pull.py` | 2 failed, 36 passed | u/executors/test_pull_images.py, i/executors/test_claim_image_gating.py |
| M17 | OpenAI Chat is sent the first image only (a silent subset) | `src/auditmanager/executors/image_input.py` | 3 failed, 38 passed | u/executors/test_http_adapter.py, u/executors/test_ssh_tunnel_adapter.py |
| M18 | Anthropic Messages is sent the images in reverse order | `src/auditmanager/executors/image_input.py` | 2 failed, 27 passed | u/executors/test_http_adapter.py |
| M19 | SSH command sends several images under a new member name (an old command would ignore it) | `src/auditmanager/executors/ssh_adapter.py` | 2 failed, 8 passed | u/executors/test_ssh_adapter.py |
| M20 | SSH command sends only the first of several images | `src/auditmanager/executors/ssh_adapter.py` | 3 failed, 7 passed | u/executors/test_ssh_adapter.py |
| M21 | SSH command keeps the one-image task cap for several images | `src/auditmanager/executors/ssh_adapter.py` | 1 failed, 9 passed | u/executors/test_ssh_adapter.py |
| M22 | a runner's refusal of the images is not named | `src/auditmanager/executors/pull.py` | 3 failed, 40 passed | u/executors/test_pull_adapter.py, i/executors/test_claim_image_gating.py |
| M23 | the client takes a ninth image | `tools/executor-runner/runner_client.py` | 2 failed, 37 passed | u/executor_runner/test_runner_client.py |
| M24 | the client does not check the 32 MiB total | `tools/executor-runner/runner_client.py` | 1 failed, 38 passed | u/executor_runner/test_runner_client.py |
| M25 | a runner serves a task with more images than it declared | `tools/executor-runner/runner_client.py` | 5 failed, 104 passed | u/executor_runner/test_agent.py, u/executor_runner/test_mcp_bridge.py, u/executor_runner/test_runner_client.py |
| M26 | the claim never declares the count (an agent that serves eight claims as one) | `tools/executor-runner/runner_client.py` | 5 failed, 104 passed | u/executor_runner/test_agent.py, u/executor_runner/test_mcp_bridge.py, u/executor_runner/test_runner_client.py |
| M27 | the endpoint is sent the last image only (the one-image loop it had) | `tools/executor-runner/agent.py` | 1 failed, 39 passed | u/executor_runner/test_agent.py |
| M28 | the command gets only the first image | `tools/executor-runner/agent.py` | 2 failed, 38 passed | u/executor_runner/test_agent.py |
| M29 | a failed image delivery is skipped | `tools/executor-runner/agent.py` | 2 failed, 38 passed | u/executor_runner/test_agent.py |
| M30 | the agent declares one whatever it is configured with | `tools/executor-runner/agent.py` | 6 failed, 34 passed | u/executor_runner/test_agent.py |
| M31 | the bridge returns only the first image | `tools/executor-runner/mcp_bridge.py` | 1 failed, 29 passed | u/executor_runner/test_mcp_bridge.py |
| M32 | the bridge serves a task wider than it declared | `tools/executor-runner/mcp_bridge.py` | 1 failed, 29 passed | u/executor_runner/test_mcp_bridge.py |
| M33 | codex gets the prompt marker after the image flags | `tools/executor-runner/codex_answer.py` | 1 failed, 13 passed | u/executor_runner/test_codex_answer.py |
| M34 | codex accepts a ninth image | `tools/executor-runner/codex_answer.py` | 1 failed, 13 passed | u/executor_runner/test_codex_answer.py |
| M35 | codex does not require a local copy for every image | `tools/executor-runner/codex_answer.py` | 1 failed, 13 passed | u/executor_runner/test_codex_answer.py |
| M36 | the forced command does not check the 32 MiB total | `tools/executor-runner/ssh-forced-command.sh` | 1 failed, 55 passed | u/executor_runner/test_ssh_forced_command.py |
| M37 | the forced command takes a ninth image | `tools/executor-runner/ssh-forced-command.sh` | 1 failed, 55 passed | u/executor_runner/test_ssh_forced_command.py |
| M38 | the forced command passes only the first image to claude | `tools/executor-runner/ssh-forced-command.sh` | 2 failed, 54 passed | u/executor_runner/test_ssh_forced_command.py |

The ADR's own mutation (verification row 11, "ignore `max_images`") is M01. For the gate, M01 turns 9 of the 19 tests of
`test_claim_image_gating.py` red: the old-shape claim is handed a multi-image task, a smaller count is handed it, a wide
task is handed ahead of a narrow one, a held claim is redelivered to a narrower claim, the four malformed payloads are
handed out, and the end-to-end comparison request reaches a runner of the old shape.

## 9. Risks and known limits

1. **The real Codex CLI was not available on this host** (`which codex` is empty). `codex_answer.py` now puts the prompt
   marker `-` **before** the `--image` flags, because `--image` takes a list of files and would take a trailing `-` as one more
   file; that reading of the CLI is from its documented option shape and is tested against a fake only (M33 shows the order is
   asserted). A real probe with two images is an operator step before a comparison route is switched on. The same reorder
   applies to the one-image path, which is otherwise unchanged.
2. **MCP sessions are a poor carrier for many crops.** Claude Code limits one MCP tool result (25,000 tokens by default;
   text above 50,000 characters is saved to a file), and this lane could not measure how it counts images. The bridge defaults
   to `--max-images 1`; the README sends large multi-image work to the agent.
3. **A remote `ssh_command` host must be updated to serve several images.** The updated `ssh-forced-command.sh` raises its
   default task cap to 48 MiB (`PDF_ANALYSIS_MAX_TASK_BYTES`); an older installed script fails closed on a list (exit 64) and
   on a task above its own 24 MiB. `claude_answer.py --ssh-envelope` serves no image at all, as before.
4. **No early signal when no runner can serve a task.** The stand does not record a runner's declared `max_images` (no schema
   for it, and none may be added here), so a multi-image task whose connection has only old-shape runners is never claimed and
   ends as `no_executor_online` (`not_sent`) after its answer window. A comparison stage should expect that outcome for
   an unprepared connection; an operator-facing "this connection serves at most k images" would need a column or a read of
   recent claims, a decision for the wave's FIX slot or a later lane.
5. **Over-declaring is the runner's own risk:** a runner that declares more than it can serve fails the task
   (`image_input_unsupported`), which the worker reads as `outcome_unknown` (see section 2). Whether a comparison call treats that
   as spent is `CMP-SPEND-01`'s decision.
6. **Transfer time is unmeasured.** A task may need up to 32 MiB of PNG fetched one image at a time (30 s each at most in the
   agent) while the claim's lease is extended in the background; no real network was used. The deadline of the pull task is the
   revision's answer deadline, unchanged.
7. **The stand does not check that a crop's Blob exists when the task is written**, only when a runner fetches it (the
   fetch answers `dependency_unavailable` or `analysis_input_invalid`). The comparison stage that saves its crops owns that order.
8. Not run: a complete `make gate` (not owed by this lane under `R-135`/`AGENTS.md` section 8: no contract, migration,
   dependency, `infra/**` or composition-root change); no web check (no web change); no live provider, model or runner call.

## 10. For the integrator

* **Merge position:** after `CMP-SPEND-01`, before `CMP-INGEST-ZIP-01` (brief section 3). No wiring enumerators move:
  `claimExecutorTask` and `getExecutorTaskImage` were already served (`getExecutorTaskImage` is in `RUNNER_ADDRESSED` of
  `test_an_absent_parent_is_not_an_empty_page.py`); neither is a sealed stub, so there is nothing to remove from
  `SEALED_STUB_GETS`, `SEALED_STUB_ADDRESSED` or `EXPECTED_ADDRESSED`.
* **Hunks outside the brief's explicit own paths, each the claim path of the sealed operation and nothing else** (brief
  section 1 rule 4 gives the lane that implements a sealed operation its router file and port rows; the task file lists them
  as allowed): `src/auditmanager/executors/runner.py` (`claim_task`, `_poll`: the `max_images` parameter and its default),
  `src/auditmanager/executors/public.py` (seven names appended for the comparison callers), `src/auditmanager/bootstrap/runner.py`
  (one keyword), `src/auditmanager/api/routers/runner.py` (one line), `src/auditmanager/api/routers/ports.py` (one signature),
  and `tests/unit/executor_runner/**` (the tests of `tools/executor-runner/**`). `executors/runner_repository.py` is also
  `CMP-SPEND-01`'s file (it adds the `comparison_call` origin to `insert_task`): this lane's hunks are the module header
  constants and the two claim statements, textually apart from `insert_task`.
* **Verify after the merge:** `tests/unit/executors`, `tests/unit/executor_runner`, `tests/integration/executors` (lane
  database, head `0038`), `tests/contract` minus the `D-220` files.
* **`CURRENT_STATE.md` sentence (the integrator's file):** "`CMP-EXEC-IMAGES-01`: a request carries up to eight images
  (16 MiB each, 32 MiB in all) with opaque crop references on every served executor channel; the server never hands a task to
  a claim whose declared `max_images` is smaller than the task's image count (absent means 1); the runner tools declare their
  count, send every image and refuse rather than answer on a subset. Nothing creates a multi-image task yet."
* **Operators:** to serve several images a pull runner sets `[command]`/`[endpoint] max_images` (agent) or `--max-images`
  (MCP bridge) and an `ssh_command` host installs the new `ssh-forced-command.sh`; nothing changes for a runner that is left alone.
* **For the comparison lanes:** the API of section 2. For `CMP-SPEND-01`: the named dependency
  `executor_image_input_unsupported` and the `outcome_unknown` class of section 2.

## 11. Forbidden hotspots

`git diff --name-only cc3dd36b HEAD | grep -E '^(contracts/|db/migrations/|pyproject.toml$|uv.lock$|web/|src/auditmanager/bootstrap/(composition|adapters)|src/auditmanager/api/schemas/|src/auditmanager/comparison/|src/auditmanager/executors/model.py|scripts/|infra/)'`
prints nothing (exit 1) on the final tree. No migration, contract, root lock, composition root, adapter module, wire model or
global style was touched. `python3 scripts/task_handoff.py --task docs/program/tasks/CMP-EXEC-IMAGES-01.md --output .local/...`
on `c4a9a0aa` reports `Path check: PASS` (every changed file is inside the task's allowed paths) and `Whitespace check: PASS`; its
`Check status` is `INCOMPLETE` because no command checks were passed to it (the checks of section 7 were run by hand). Nothing was
pushed or merged; no tag was made.

## Appendix: the quoted mutations

Each replaced the `-` text with the `+` text, once, in the named file.

**M01** `src/auditmanager/executors/runner_repository.py`
```diff
- f"AND {_image_count('p')} <= :max_images "
+ (line removed)
```

**M02** `src/auditmanager/executors/runner_repository.py`
```diff
- f"AND {_image_count()} <= :max_images "
+ (line removed)
```

**M03** `src/auditmanager/executors/runner_repository.py`
```diff
- DEFAULT_CLAIM_IMAGES: Final[int] = 1
+ DEFAULT_CLAIM_IMAGES: Final[int] = 8
```

**M04** `src/auditmanager/api/routers/runner.py`
```diff
- max_images=body.max_images,
+ (line removed)
```

**M05** `src/auditmanager/bootstrap/runner.py`
```diff
- wait_seconds=wait_seconds,
- max_images=max_images)
+ wait_seconds=wait_seconds)
```

**M06** `src/auditmanager/executors/runner_repository.py`
```diff
- ELSE {MAX_CLAIM_IMAGES + 1} END
+ ELSE 0 END
```

**M07** `src/auditmanager/executors/runner.py`
```diff
- token_id=principal.token_id, lease_seconds=CLAIM_LEASE_SECONDS,
- max_images=max_images)
+ token_id=principal.token_id, lease_seconds=CLAIM_LEASE_SECONDS)
```

**M08** `src/auditmanager/executors/image_input.py`
```diff
- MAX_IMAGES: Final[int] = 8
+ MAX_IMAGES: Final[int] = 9
```

**M09** `src/auditmanager/executors/image_input.py`
```diff
- if total > MAX_TOTAL_IMAGE_BYTES:
- raise ImageReferenceError("total_too_large")
+ (line removed)
```

**M10** `src/auditmanager/executors/image_input.py`
```diff
- if not 1 <= size <= MAX_IMAGE_BYTES:
- raise ImageReferenceError("image_too_large")
+ (line removed)
```

**M11** `src/auditmanager/executors/image_input.py`
```diff
- if (kind, identity) in identities:
- raise ImageReferenceError("duplicate_identity")
+ (line removed)
```

**M12** `src/auditmanager/executors/image_input.py`
```diff
- elif keys == _BY_CROP:
- kind, pattern = "crop_id", _CROP
+ elif keys == _BY_CROP or keys == _BY_CROP | {"portal_block_id"}:
+ kind, pattern = "crop_id", _CROP
```

**M13** `src/auditmanager/executors/image_input.py`
```diff
- if len(descriptors) != len(raws):
- raise _invalid("count_mismatch")
+ (line removed)
```

**M14** `src/auditmanager/executors/image_input.py`
```diff
- or hashlib.sha256(raw).hexdigest() != descriptor["sha256"]):
+ ):
```

**M15** `src/auditmanager/executors/image_input.py`
```diff
- _CROP = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
+ _CROP = re.compile(r".*\Z", re.S)
```

**M16** `src/auditmanager/executors/pull.py`
```diff
- checked_images = [dict(item) for item in checked_descriptors(body.get("images", ()))]
+ checked_images = [dict(item) for item in checked_descriptors(body.get("images", ()))][:1]
```

**M17** `src/auditmanager/executors/image_input.py`
```diff
- {"type": "image_url", "image_url": {"url": png_data_url(raw)}} for raw in raws])
+ {"type": "image_url", "image_url": {"url": png_data_url(raw)}} for raw in list(raws)[:1]])
```

**M18** `src/auditmanager/executors/image_input.py`
```diff
- } for raw in raws])
-
-
- def add_openai_images
+ } for raw in reversed(list(raws))])
+
+
+ def add_openai_images
```

**M19** `src/auditmanager/executors/ssh_adapter.py`
```diff
- elif envelopes:
- task["image"] = envelopes
+ elif envelopes:
+ task["images"] = envelopes
```

**M20** `src/auditmanager/executors/ssh_adapter.py`
```diff
- if len(envelopes) == 1:
- task["image"] = envelopes[0]
+ if envelopes:
+ task["image"] = envelopes[0]
```

**M21** `src/auditmanager/executors/ssh_adapter.py`
```diff
- (MAX_TASK_BYTES if len(images) <= 1 else MAX_MULTI_IMAGE_TASK_BYTES)
+ MAX_TASK_BYTES
```

**M22** `src/auditmanager/executors/pull.py`
```diff
- if (task.fail_reason or "").split(":", 1)[0].strip() == _IMAGE_REFUSAL:
+ if False:
```

**M23** `tools/executor-runner/runner_client.py`
```diff
- MAX_IMAGES = 8
+ MAX_IMAGES = 9
```

**M24** `tools/executor-runner/runner_client.py`
```diff
- return total <= MAX_TOTAL_IMAGE_BYTES
+ return True
```

**M25** `tools/executor-runner/runner_client.py`
```diff
- return len(task.get("images") or []) <= declared
+ return True
```

**M26** `tools/executor-runner/runner_client.py`
```diff
- if max_images > 1:
- body["max_images"] = max_images
+ (line removed)
```

**M27** `tools/executor-runner/agent.py`
```diff
- images = [raw for _, raw in self._fetch_images(task, budget, should_stop)]
+ images = [raw for _, raw in self._fetch_images(task, budget, should_stop)][-1:]
```

**M28** `tools/executor-runner/agent.py`
```diff
- for image, raw in self._fetch_images(task, budget, should_stop):
+ for image, raw in self._fetch_images(task, budget, should_stop)[:1]:
```

**M29** `tools/executor-runner/agent.py`
```diff
- fetched[image["blob_id"]] = self.client.image(
- task["task_id"], image, timeout=max(1.0, min(30.0, budget)))
+ try:
+ fetched[image["blob_id"]] = self.client.image(
+ task["task_id"], image, timeout=max(1.0, min(30.0, budget)))
+ except Exception:
+ continue
```

**M30** `tools/executor-runner/agent.py`
```diff
- return self.command_max_images if self.mode == "command" else self.endpoint_max_images
+ return 1
```

**M31** `tools/executor-runner/mcp_bridge.py`
```diff
- for raw in blobs:
+ for raw in blobs[:1]:
```

**M32** `tools/executor-runner/mcp_bridge.py`
```diff
- if images and not (self._accept_images and serves_images(task, self._max_images)):
+ if images and not self._accept_images:
```

**M33** `tools/executor-runner/codex_answer.py`
```diff
- "--output-last-message", str(answer_path), "-", *image_args,
+ "--output-last-message", str(answer_path), *image_args, "-",
```

**M34** `tools/executor-runner/codex_answer.py`
```diff
- MAX_IMAGES = 8
+ MAX_IMAGES = 9
```

**M35** `tools/executor-runner/codex_answer.py`
```diff
- or len(images) > MAX_IMAGES or len(images) != len(local)):
+ or len(images) > MAX_IMAGES):
```

**M36** `tools/executor-runner/ssh-forced-command.sh`
```diff
- if total > (32 << 20):
+ if False:
```

**M37** `tools/executor-runner/ssh-forced-command.sh`
```diff
- if not 1 <= len(envelopes) <= 8:
+ if not 1 <= len(envelopes) <= 9:
```

**M38** `tools/executor-runner/ssh-forced-command.sh`
```diff
- {"type": "text", "text": task["user_text"]}, *blocks,
+ {"type": "text", "text": task["user_text"]}, *blocks[:1],
```
