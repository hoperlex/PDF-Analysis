# HOTFIX-SSH-IMAGES-1030 — source handoff

2026-10-30. `tools/executor-runner/claude_answer.py` now accepts the existing SSH task `image` object or ordered list and passes verified PNGs directly as Claude CLI user image content. Root alone integrates Git and owns any separately authorised update of the configured installed helper. No installed `/opt` file or real executor/model was touched.

## Protocol and behavior

For images, command adds `--input-format stream-json`; stdin is one newline-terminated envelope:

```json
{"type":"user","message":{"role":"user","content":[{"type":"image","source":{"type":"base64","media_type":"image/png","data":"…"}},{"type":"text","text":"{\"system\":\"…\",\"user_text\":\"…\"}"}]},"parent_tool_use_id":null}
```

Image order is preserved. The CLI gets actual base64 content without reading local image paths or using a tool. `--tools ''`, strict MCP configuration, isolated temporary working directory, pinned model/usage verification, schema flags, effort and secret-stripped environment remain. Text-only stdin bytes and flags remain identical. Pull task image refusal remains.

The protocol is supported by the official [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference) (`--input-format stream-json`) and [streaming input example](https://code.claude.com/docs/en/agent-sdk/streaming-vs-single-mode) (user content with image/base64/image/png blocks). This is documentation-backed source implementation; no live CLI compatibility or model result is claimed.

## Validation and limits

SSH input stays bounded: single/no-image task24MiB; multiple-image task48MiB, matching the existing adapter; at most8 images, each16MiB raw, total32MiB raw. Envelope must have exactly `media_type,data`; only PNG and strict base64 are accepted. Unknown/local-path channel shapes fail explicitly.

Command-side PNG checks are independent of the caller's existing descriptor/digest verification: signature, chunk bounds/order/CRC, legal IHDR, required/valid indexed palette, terminal IEND, complete bounded zlib stream, exact inflated scanline length and filter bytes. Adam7 and legal PNG colour/depth variants are supported. Limits add16384 pixels per dimension,40million pixels and160MiB inflated data per image to bound CPU/memory. Invalid or excessive input is refused before CLI launch, without falling back to text. The ordered `image` task has no source descriptor fields; source identity/digest binding remains the caller's existing responsibility.

The asynchronous pipe writer/reader and existing heartbeat30s/stall600s/SSH hard cap7140s remain. Large image stdin uses the same writer thread, so monitoring remains active while writing.

## Checks

- `.venv/bin/python -m pytest tests/unit/executor_runner/test_claude_answer.py tests/unit/executor_runner/test_claude_answer_images.py tests/unit/executor_runner/test_claude_answer_stream.py -q --tb=short`: **104 passed in10.61s**.
- Final independent-review palette strictness adjustment: `test_claude_answer_images.py`: **18 passed in0.16s**; helper `py_compile` PASS.
- Fake CLI decodes and byte-compares ordered0/1/2/8 image content, validates native user envelope and empty tools, and checks exact previous text-only stdin bytes. Cases reject malformed envelope/MIME/base64, signature-only/truncated/CRC-broken PNG, trailing data, invalid compressed stream/filter, inflation bomb, excessive dimensions/count/per-image/total bytes, and illegal palettes; legal Adam7 and indexed palette pass. Existing result, pinned model, heartbeat, stall, hard-cap and effort cases pass.
- Independent read-only review by `c4_seal_plan`: no blocker for normal crop PNG; palette corner tightened and targeted cases passed.
- No browser, full gate/build, SSH connection, installed-file write or real model/provider call.

## Changed files and integration

- `tools/executor-runner/claude_answer.py`.
- `tests/unit/executor_runner/test_claude_answer.py`: obsolete blanket SSH-image rejection assertion now requires invalid PNG refusal.
- `tests/unit/executor_runner/test_claude_answer_images.py`.
- This report and `docs/program/tasks/HOTFIX-SSH-IMAGES-1030.md`.

API/contracts/migrations, root dependencies, SSH adapter, V3 core and UI are unchanged by this task. The source helper is self-contained stdlib Python and ready for integrator review. Runtime may impose additional Claude/provider image limits; these were not exercised. The installed helper must be separately updated before its new image capability is available on that executor.
