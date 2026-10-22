#!/bin/sh
# The test forced command. It reads ONE JSON object on stdin and answers on stdout.
#
# Optional fields of that object (anything else is just echoed back):
#   stderr_text   written to stderr first
#   sleep_s       whole seconds to sleep before answering (a command that outlives its timeout)
#   stdout_bytes  answer with that many 'x' bytes instead (output over the bound)
#   claude_model  answer like `claude -p --output-format json`, with that one model in modelUsage
#   exit_status   exit with this status after answering
#
# The default answer is {"ok":true,"echo":<stdin>,"ssh_original_command":"<SSH_ORIGINAL_COMMAND>"},
# which shows what the client typed (nothing) and proves it is not what runs.
set -u

input="$(cat)"
if ! printf '%s' "$input" | jq -e 'type == "object"' >/dev/null 2>&1; then
  printf 'forced-command: stdin is not a JSON object\n' >&2
  exit 64
fi
get() { printf '%s' "$input" | jq -r "$1"; }

stderr_text="$(get '.stderr_text // ""')"
sleep_s="$(get '.sleep_s // 0')"
stdout_bytes="$(get '.stdout_bytes // 0')"
claude_model="$(get '.claude_model // ""')"
exit_status="$(get '.exit_status // 0')"

[ -z "$stderr_text" ] || printf '%s\n' "$stderr_text" >&2
[ "$sleep_s" = 0 ] || sleep "$sleep_s"

if [ "$stdout_bytes" != 0 ]; then
  head -c "$stdout_bytes" /dev/zero | tr '\0' 'x'
elif [ -n "$claude_model" ]; then
  jq -n -c --arg m "$claude_model" \
    '{type:"result",subtype:"success",is_error:false,num_turns:1,result:"stub answer",modelUsage:{($m):{inputTokens:1,outputTokens:1,costUSD:0}}}'
else
  printf '%s' "$input" | jq -c --arg o "${SSH_ORIGINAL_COMMAND:-}" '{ok:true,echo:.,ssh_original_command:$o}'
fi
exit "$exit_status"
