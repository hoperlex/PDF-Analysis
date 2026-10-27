#!/usr/bin/env bash
# Remote side of the `claude_code_headless` profile (EXEC-SSH-01, plan T-6/T-7/T-8).
#
# Install on the machine that runs Claude Code, for a dedicated low-privilege user, as the
# forced command of the stand's SSH key in that user's ~/.ssh/authorized_keys (one line):
#
#   restrict,command="/home/pdfa/bin/ssh-forced-command.sh" ssh-ed25519 AAAA... pdf-analysis-stand
#
# `restrict` switches off port, agent and X11 forwarding and the pty; `command=` makes sshd run
# this script whatever the client asks for. The stand sends ONE task JSON on stdin:
#
#   {"model": "claude-opus-5", "system": "...", "user_text": "...", ...}
#
# and reads the Claude Code JSON result from stdout. Extra task fields are ignored. The member
# "image" is the exception: it is one {"media_type", "data"} object, or a list of up to eight of
# them in the order the model sees them (32 MiB of PNG together); anything else is refused.
#
# What it guarantees:
#   * SSH_ORIGINAL_COMMAND (what the client typed) is ignored and unset; the client cannot choose
#     a command, only supply a task.
#   * Claude Code runs with NO built-in tool (`--tools ""`) and NO MCP tool (`--disallowedTools
#     "mcp__*"`, because `--tools` does not cover MCP), `--max-turns 1`, a system prompt that
#     replaces the default one, and no session saved to disk. A document that injects
#     instructions has nothing to call (plan T-7).
#   * Authentication is an API key (`--bare` reads no OAuth credential), metered at the pin's
#     rates (plan T-8; an owner's subscription must not back a product call). The key is read
#     from a protected file, never from the command line, the task or the client's environment.
#   * The payload (document text) goes through files in a private temporary directory that is
#     removed on exit, and never through argv or the environment.
#
# The model identity (R-133): the stand compares the model Claude Code reports with the pinned
# one. The JSON key that carries it is NOT spelled out in the Claude Code documentation read on
# 2026-10-22 (headless docs mention `total_cost_usd` and "a per-model cost breakdown"). EXEC-SSH-01
# Work 0 must capture `claude --version` and `claude -p "hi" --output-format json | python3 -c
# 'import json,sys; print(sorted(json.load(sys.stdin)))'` from the installed version, record the
# output, and write the stand's parser for exactly that key. If the output has no model key, switch
# this script to `--output-format stream-json --verbose` and read `system/init`. Never infer it.
#
# Requirements on the remote machine: bash, python3 (task parsing only), coreutils, and `claude`
# on PATH (this script adds ~/.local/bin and ~/.claude/local). Exit status is Claude Code's, or
# 64 for a bad task, 78 for a bad environment file, 127 when `claude` is missing.
set -euo pipefail
umask 077

# Whatever the client typed is not ours to run.
unset SSH_ORIGINAL_COMMAND

# 48 MiB: 32 MiB of PNG (the limit for all the images of a task) is about 43 MiB as base64; a task of
# one image of at most 16 MiB stayed inside the earlier 24 MiB.
MAX_TASK_BYTES="${PDF_ANALYSIS_MAX_TASK_BYTES:-50331648}"
ENV_FILE="${PDF_ANALYSIS_CLAUDE_ENV_FILE:-${HOME:?HOME is not set}/.config/pdf-analysis/claude.env}"
# Keep below the stand's 900 s Attempt watchdog; the stand also enforces its own timeout.
CLAUDE_TIMEOUT_SECONDS=840

fail() {
  printf 'pdf-analysis-forced-command: %s\n' "$1" >&2
  exit "$2"
}

export PATH="$HOME/.local/bin:$HOME/.claude/local:$PATH"
command -v python3 >/dev/null 2>&1 || fail "python3 is required to read the task" 127
command -v claude >/dev/null 2>&1 || fail "claude is not on PATH" 127

work="$(mktemp -d "${TMPDIR:-/tmp}/pdfa-claude.XXXXXX")" || fail "cannot create a temporary directory" 73
trap 'rm -rf "$work"' EXIT

# 1. Read exactly one task, with a size cap (the cap is one byte over so that an oversized task is detected).
head -c "$((MAX_TASK_BYTES + 1))" >"$work/task.json"
size="$(wc -c <"$work/task.json" | tr -d ' ')"
[ "$size" -le "$MAX_TASK_BYTES" ] || fail "the task is larger than $MAX_TASK_BYTES bytes" 64

# 2. Split it into files. Error messages name a field, never content.
python3 - "$work" <<'PY' || fail "the task on stdin is not a valid task document" 64
import json
import re
import sys

work = sys.argv[1]
try:
    with open(work + "/task.json", encoding="utf-8") as handle:
        task = json.load(handle)
except (ValueError, UnicodeDecodeError) as error:
    sys.stderr.write("pdf-analysis-forced-command: stdin is not UTF-8 JSON (%s)\n" % type(error).__name__)
    raise SystemExit(1)
if not isinstance(task, dict):
    sys.stderr.write("pdf-analysis-forced-command: the task must be a JSON object\n")
    raise SystemExit(1)
for field in ("model", "system", "user_text"):
    if not isinstance(task.get(field), str) or not task[field]:
        sys.stderr.write("pdf-analysis-forced-command: task field %r must be a non-empty string\n" % field)
        raise SystemExit(1)
# The model becomes an argv element: it must not be able to look like an option or carry shell syntax.
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,99}", task["model"]):
    sys.stderr.write("pdf-analysis-forced-command: task field 'model' is not a plain model id\n")
    raise SystemExit(1)
with open(work + "/model", "w", encoding="utf-8") as out:
    out.write(task["model"])
with open(work + "/system.txt", "w", encoding="utf-8") as out:
    out.write(task["system"])
with open(work + "/user.txt", "w", encoding="utf-8") as out:
    out.write(task["user_text"])
schema = task.get("output_schema")
if schema is not None:
    if not isinstance(schema, dict) or schema.get("type") != "object":
        sys.stderr.write("pdf-analysis-forced-command: invalid output schema\n")
        raise SystemExit(1)
    encoded = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > 65536:
        sys.stderr.write("pdf-analysis-forced-command: output schema is too large\n")
        raise SystemExit(1)
    with open(work + "/schema.json", "w", encoding="utf-8") as out:
        out.write(encoded)
image = task.get("image")
if image is not None:
    import base64
    import binascii
    # One image is an object, the shape this command has always read. Several are a LIST of such
    # objects in the same member (at most 8, 32 MiB of PNG together, in the order the model sees
    # them): a command installed before that existed refuses a list, so it never answers from the
    # text alone or from one image of several.
    envelopes = image if isinstance(image, list) else [image]
    if not 1 <= len(envelopes) <= 8:
        sys.stderr.write("pdf-analysis-forced-command: invalid image envelope\n")
        raise SystemExit(1)
    blocks = []
    total = 0
    for envelope in envelopes:
        if not isinstance(envelope, dict) or set(envelope) != {"media_type", "data"} or envelope["media_type"] != "image/png":
            sys.stderr.write("pdf-analysis-forced-command: invalid image envelope\n")
            raise SystemExit(1)
        try:
            raw = base64.b64decode(envelope["data"], validate=True)
        except (binascii.Error, ValueError, TypeError):
            sys.stderr.write("pdf-analysis-forced-command: invalid image bytes\n")
            raise SystemExit(1)
        if not raw.startswith(b"\x89PNG\r\n\x1a\n") or not 1 <= len(raw) <= (16 << 20):
            sys.stderr.write("pdf-analysis-forced-command: invalid PNG\n")
            raise SystemExit(1)
        total += len(raw)
        blocks.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": envelope["data"]}})
    if total > (32 << 20):
        sys.stderr.write("pdf-analysis-forced-command: the images are larger than 32 MiB together\n")
        raise SystemExit(1)
    # Stream JSON carries real image blocks; a textual base64 or file path is not vision input.
    event = {"type": "user", "message": {"role": "user", "content": [
        {"type": "text", "text": task["user_text"]}, *blocks,
    ]}}
    with open(work + "/input.jsonl", "w", encoding="utf-8") as out:
        json.dump(event, out, ensure_ascii=False, separators=(",", ":"))
        out.write("\n")
PY
model="$(cat "$work/model")"

# 3. The API key, from a file only its owner can read.
[ -f "$ENV_FILE" ] || fail "environment file $ENV_FILE not found" 78
[ -O "$ENV_FILE" ] || fail "environment file $ENV_FILE must be owned by the user running this script" 78
mode="$(stat -c '%a' "$ENV_FILE" 2>/dev/null || stat -f '%Lp' "$ENV_FILE")"
if [ $((8#$mode & 8#077)) -ne 0 ]; then
  fail "environment file $ENV_FILE has mode $mode; it must not be accessible by group or others (chmod 600)" 78
fi
api_key="$(sed -n 's/^ANTHROPIC_API_KEY=//p' "$ENV_FILE" | head -n 1)"
api_key="${api_key%\"}"
api_key="${api_key#\"}"
api_key="${api_key%\'}"
api_key="${api_key#\'}"
case "$api_key" in
  "" | *[[:space:]]*) fail "environment file $ENV_FILE has no usable ANTHROPIC_API_KEY=... line" 78 ;;
esac

# 4. Run Claude Code. The cwd is the private temporary directory (it holds only the task files).
runner=()
timeout_bin="$(command -v timeout || command -v gtimeout || true)"
[ -z "$timeout_bin" ] || runner=("$timeout_bin" -k 10 "$CLAUDE_TIMEOUT_SECONDS")

cd "$work"
input_file="$work/user.txt"
input_args=()
if [ -f "$work/input.jsonl" ]; then
  input_file="$work/input.jsonl"
  input_args=(--input-format stream-json)
fi
schema_args=()
if [ -f "$work/schema.json" ]; then
  schema_args=(--json-schema "$(cat "$work/schema.json")")
fi
set +e
env -u CLAUDE_CODE_OAUTH_TOKEN -u ANTHROPIC_AUTH_TOKEN ANTHROPIC_API_KEY="$api_key" \
  ${runner[@]+"${runner[@]}"} claude -p --bare \
  --tools "" \
  --disallowedTools "mcp__*" \
  --output-format json \
  ${input_args[@]+"${input_args[@]}"} \
  ${schema_args[@]+"${schema_args[@]}"} \
  --max-turns 1 \
  --model "$model" \
  --system-prompt-file "$work/system.txt" \
  --no-session-persistence \
  <"$input_file" >"$work/result.json"
status=$?
set -e
[ "$status" -eq 0 ] || fail "claude exited without a successful answer" "$status"

# The model identity is reported by Claude Code's per-model usage object. Require exactly
# one entry and the exact requested gateway model; never infer identity from --model alone.
python3 - "$work" <<'PY' || fail "claude returned an incomplete answer" 65
import json
import math
import sys

work = sys.argv[1]
try:
    with open(work + "/result.json", encoding="utf-8") as handle:
        result = json.load(handle)
except (OSError, ValueError, UnicodeError):
    raise SystemExit(1)
models = result.get("modelUsage") if isinstance(result, dict) else None
if (not isinstance(models, dict) or len(models) != 1
        or result.get("is_error") is True or result.get("subtype") not in (None, "success")):
    raise SystemExit(1)
reported = next(iter(models))
if not isinstance(reported, str) or not reported:
    raise SystemExit(1)
if "structured_output" in result:
    if not isinstance(result["structured_output"], dict):
        raise SystemExit(1)
    answer = json.dumps(result["structured_output"], ensure_ascii=False, separators=(",", ":"))
else:
    answer = result.get("result")
if not isinstance(answer, str) or not answer:
    raise SystemExit(1)
usage = models[reported]
if not isinstance(usage, dict):
    raise SystemExit(1)
tokens_in = sum(usage.get(name, 0) for name in
                ("inputTokens", "cacheReadInputTokens", "cacheCreationInputTokens"))
tokens_out = usage.get("outputTokens")
cost = result.get("total_cost_usd")
if (type(tokens_in) is not int or tokens_in < 0 or type(tokens_out) is not int or tokens_out < 0
        or (cost is not None and (type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0))):
    raise SystemExit(1)
print(json.dumps({
    "model": reported, "output_text": answer, "stop_reason": "end_turn",
    "input_tokens": tokens_in, "output_tokens": tokens_out, "reported_cost_usd": cost,
}, ensure_ascii=False, separators=(",", ":")))
PY
