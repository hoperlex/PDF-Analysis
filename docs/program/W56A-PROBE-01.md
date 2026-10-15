# W56A-PROBE-01 — model identity probe

**Status: STOPPED after the first call.** Base `integration/w56a` `7bf6a816`;
task: `docs/program/tasks/W56A-PROBE-01.md`. `W56A-FREEZE-01` remains
STOPPED and grants no implementation lane.

## Gateway results

| Gateway role | Explicit model | Default/stub | Rate check | Verdict |
| --- | --- | --- | --- | --- |
| stand | requested `anthropic/claude-opus-5`; response `meta/muse-spark-1.3-contributor` | not called after explicit-model failure | $0.0000046 reported versus $0.00047 expected for 14 input / 16 output tokens at the locked $5/$25 rates; exceeds the precommitted tolerance | FAIL: requested model was ignored or routed elsewhere |
| recording | access pending | not called | not measured | STOP: separate gateway configuration absent |

The stand request went through the same `/agent/v1/chat/completions` route
that the current `ProxyAdapter` builds from the stand's `provider.env`. Its
JSON body named the explicit model, contained a short synthetic Russian
prompt and set `max_tokens=16`; it carried unique request and idempotency
IDs. The HTTP response was 200 with one choice. The script printed only
`status`, reported `model`, usage counts and `usage.cost`; it did not print
the endpoint, token, prompt or answer. The exact transport command was
`ssh … 'python3 - anthropic/claude-opus-5' < /tmp/w56a_probe.py` using the
owner-provided SSH account. The script read the host-owned credential in
memory and wrote no file on the stand.

The reported model is not the requested model and the cost is around 1% of
the lock-derived estimate. Either signal independently violates
`W56-PLAN.md` §A3.5. The planned default/stub call was therefore withheld;
repeating it would spend money without clearing the stop. This result does
not prove that the upstream lacks Opus; it proves that this request path did
not select it. The owner must provide a working selection route or correct
the stand gateway, and identify the distinct recording gateway before the
freeze can finish.

## Checks, contracts and handoff

The probe changes no API, domain, analysis contract, migration or product
behavior. Only the three task/report/ledger documents are allowed. Actual
spend and the remaining wave ceiling are in `reviews/W56A-SPEND.md`.
No secret or gateway host is recorded. The result is a refusal to grant SEAL,
not an acceptance of a fallback model.

The focused governance and prose suite passed **93 tests** on this document
candidate. Its first run found that the new task lacked four required
governance sections; those sections were added and the same suite then passed.
The temporary SSH control session was closed after the failed identity
signal. No product stand file, credential, contract, migration, dependency,
composition root or global style was changed. The final changed-path and
`git diff --check` proof accompany this task's commit.
