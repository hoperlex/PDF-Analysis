# HOTFIX-SSH-IMAGES-1030

## Outcome
Existing SSH PNG envelopes reach the tool-free Claude CLI as actual bounded stream-json image content instead of being refused or silently omitted.

## Depends on
- AR-V3-LIVENESS-PIPE-01
- CMP-EXEC-IMAGES-01

## Frozen inputs
- Existing SSH task `image` is one `{media_type,data}` object or an ordered list, already descriptor-verified by the caller.
- Up to8 PNGs;16MiB per PNG/32MiB raw total, single task24MiB/multiple48MiB. Existing text, schema, model/effort, heartbeat/stall/hard-cap semantics remain.
- API1.14/migration0043 unchanged. Shared `cmp-int`; root is sole integrator/Git writer.

## Allowed paths
- tools/executor-runner/claude_answer.py
- tests/unit/executor_runner/**
- docs/program/tasks/HOTFIX-SSH-IMAGES-1030.md
- docs/program/HOTFIX-SSH-IMAGES-1030.md

## Forbidden hotspots
- Installed `/opt` helper, SSH adapter, contracts, migrations, bootstrap, dependencies/locks, V3 core and UI.

## Non-goals
- No installed-host mutation, real CLI/model invocation, full gate, new deployment or filesystem Read-tool workaround.

## Deliverables
- Bounded verified PNG channel using CLI `--input-format stream-json`, source report and fake-CLI proof.

## Required tests
- `.venv/bin/python -m pytest tests/unit/executor_runner/test_claude_answer*.py -q --tb=short`
- Compile helper; no actual model/provider/SSH calls.

## Integration contract
Root may review/copy this self-contained helper to the live executor only through its separate authorised installation process. Text-only stdin bytes remain unchanged. Image requests use one newline-terminated user envelope with base64 image blocks and text. Tool list stays empty.

## Failure/idempotency/security cases
- Invalid MIME/envelope/base64/PNG, excessive count/bytes/dimensions are explicit refusals before CLI starts. No fallback to text-only. Asynchronous stdin writer, stream reader and frozen liveness remain.

## Rollback / feature flag
- Revert helper update for new calls; old helper explicitly refuses image tasks. No persisted schema/state change.

## Handoff
- Source ready; root alone commits/publishes. Installed helper unchanged.
- Changed helper +old assertion +new image test file +task/report; exact paths and integration limits in `docs/program/HOTFIX-SSH-IMAGES-1030.md`.
- 104 focused fake-CLI/liveness cases passed; final palette adjustment18 targeted cases and py_compile passed. No full gate/build/real model/SSH/installed writes.
- No contract/migration/dependency/adapter/V3/UI changes. Root must separately authorise/install the configured executor helper to expose the new image channel there.
