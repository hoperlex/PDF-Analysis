# PROD-13A-MODEL-IDENTITY-PROBE-TOOL-01 — the operator-run model identity probe

Task: `docs/program/tasks/PROD-13A-MODEL-IDENTITY-PROBE-TOOL-01.md`. Branch `agent/prod-13a-model-probe-tool-01`, base `0e663fd0` (`integration/ar-close-1026`). Plan item `PROD-13` (the tool half) of `PRODUCTION-READINESS-PLAN-01.md`; owner rulings `R-146e`, `R-146af`, `AD-13` confirmed by `R-146w` as written at `83600aed`; `R-133`, `R-29`. **The lane made no network call, read no credential file and spent nothing**: every call in the tests goes to a stub that replaces the adapter's opener, and the "credential" in them is a made-up string.

## Result

`scripts/model_probe/probe.py` sends one minimal chat-completions request (`max_tokens` 16, the product's own `PROMPT`) per model pinned in `docs/program/P02_LOCK.json`, through `build_http_adapter(api_flavour="openai_chat", ...)` with the pinned destination layer (public addresses only), and writes one report block per model with `requested_slug:`, `reported_model:`, `verdict:` (the `R-133` comparison, `executors/identity.py:assess_identity`: exact string, no prefix, no case folding, no alias list), `verdict_reason:`, `adapter_outcome:`, the token counts, the finish reason, the cost the gateway reported, the cost at the lock's rates, the `rate_check:` and the cost the tool counted against the ceiling. A summary block ends the report: `all_identities_match:`, `lock_candidate:`, `stopped:`, `credential_guard:`, `exit_code:`. It never writes the lock: it reads it once, and `lock_candidate: yes` is a statement for the integrator, who writes `P02_LOCK.json` only if it is `yes`.

Premise: **holds, with four refinements, none a stop** (evidence P-01 to P-09 in the task file). (1) `http_adapter.py` compares nothing for `openai_chat`: the comparison is `ProxyAdapter.complete` (`proxy.py:319`) and, for the run path, `stage.py:283` / `v3_provider_call.py:279`; all exact, no alias is ever set in `src/`. (2) The typed refusal on a mismatch does **not** carry the reported name (it goes to the log), so the tool wraps the adapter's opener to see the reply body. (3) A lock `model_id` is a pin id (`claude-opus-5`), not a gateway name (`W56A-PROBE-01` used `anthropic/claude-opus-5`), so the tool never guesses a slug: each probed model needs an explicit `--slug PIN=SLUG`. (4) A probe already exists, `tools/provider/identity_probe.py` (W56a): one request, the primary model only, reads a `provider.env` path, bypasses `http_adapter.py`. It is not edited; `executors/identity.py` is its port and the new tool reuses that.

## Files changed

| File | Change |
|---|---|
| `scripts/model_probe/probe.py` | new, 580 lines; stdlib plus the product's adapter, identity and lock readers |
| `tests/unit/scripts/test_model_probe.py` | new, 53 cases; stub transport, no network, no credential file |
| `docs/program/tasks/PROD-13A-MODEL-IDENTITY-PROBE-TOOL-01.md`, this report | records |

Test location: `tests/unit/scripts/` mirrors `scripts/`, as `test_manual_scan.py` does (P-07); the gate's battery collects all of `tests`.

## How the operator (the integrator) runs it

```bash
cd /root/projects/PDF-Analysis            # the tree that holds the tool
export PROXY_LLM_BASE_URL=...  PROXY_LLM_TOKEN=...   # from the process environment only; nothing is read from a file
PYTHONPATH=src python3 -m scripts.model_probe.probe --confirm-paid --max-usd 0.50 \
  --slug claude-opus-5=anthropic/claude-opus-5 \
  --slug claude-sonnet-5=anthropic/claude-sonnet-5 \
  --slug gpt-6-sol=<the gateway name of that model> \
  --report /root/model-probe-<date>.txt        # outside the repository; must not exist
```

`--only claude-opus-5 --only claude-sonnet-5` (with only their `--slug`) leaves `gpt-6-sol` out, which the lock records for the owner's Codex subscription (`billing=not_metered`) and which OpenRouter may not serve. The slugs above are `W56A-PROBE-01`'s form for the two Anthropic models; they are the operator's choice, not the tool's. The report path is printed on the last line; without `--report` it is a new file in the temp directory, never in the repository.

Exit status: `0` every probed model answered with exactly the requested name; `1` a mismatch, no usable name or a failed call (the run still goes on to the other models); `2` refused before any call (nothing is created); `3` stopped at the ceiling; `5` the credential value was in what was about to be written and was redacted. A usage error exits `2` through `argparse`.

What the integrator does with the report (`AD-13`): for each model whose block says `verdict: match` and `rate_check: checked`, the connection revision's gateway model is the `reported_model:` string. For a `mismatch` the reported string is what to set it to, deliberately, as the price of `R-133`; the tool does not decide that. The lock is written only if `lock_candidate: yes`.

## What the tool refuses, and the ceiling

Refused before the first call (exit 2, no report file): no `--confirm-paid` (checked before the environment is touched); `PROXY_LLM_BASE_URL` or `PROXY_LLM_TOKEN` missing, blank or refused by the product adapter's own settings check; `--max-usd` not a positive finite number or above 5.00 (the `R-29` wave stop); a probed model without a `--slug`, with a gateway stub (`proxy`, `default`, `auto`, ...) or a malformed name as its slug, a duplicate or unknown one; a lock that cannot be read; a report path that exists (the report is created with `O_EXCL`, mode 0600, so it can never overwrite a file, the lock included); an adapter that no longer has the opener seam.

Ceiling (default 0.50 USD in total, which the three pins cannot reach: their worst case in total is about 0.003). Before each call the worst case of that call (a 256-token prompt bound plus `max_tokens` at the lock's rates) is added to what is counted, and a call that would pass the ceiling is not made (`stopped: projected_over_ceiling`). After each call the cost counted is, in this order: the gateway's `usage.cost`; else the lock's rates over the reported tokens (`estimated`); else the worst case (`bound`). A total over the ceiling ends the run (`stopped: ceiling_exceeded`). A failed call is counted at zero when the adapter proves nothing was billed (`not_sent`, `definite_refusal`, `rate_limited`) and at the worst case otherwise (`outcome_unknown` may have been billed). Nothing is retried. The tool does not know what the wave already spent; the `R-29` ledger is the integrator's.

## Test-file changes

No existing test file was modified. `tests/unit/scripts/test_model_probe.py` is new; the per-test before/after table is empty.

## Mutation table (every guard shown failing)

Each row is one uncommitted edit of `scripts/model_probe/probe.py`, applied alone, `tests/unit/scripts/test_model_probe.py` run in full (53 cases), the file restored with `git checkout -- scripts/model_probe/probe.py`, `git status --short` clean afterwards. The driver is not committed. Baseline 53 passed.

| # | Mutation | Result |
|---|---|---|
| M01 | `--confirm-paid` not required | 1 red (the no-flag refusal) |
| M02 | the environment is read before the confirmation | 1 red (the touched-environment check) |
| M03 | the 5.00 hard cap removed | 1 red |
| M04 | a zero or negative ceiling accepted | 1 red |
| M05 | default ceiling 1.50 instead of 0.50 | 2 red |
| M06 | a blank token accepted | 1 red |
| M07 | the adapter-builder's refusal not turned into a refusal | 1 red |
| M08 | a missing slug guessed from the pin id | 1 red |
| M09 | a gateway stub accepted as a slug | 1 red |
| M10 | a malformed slug accepted | 1 red |
| M11 | a duplicate slug accepted | 1 red |
| M12 | a slug for a model that is not probed accepted | 1 red |
| M13 | `--only` ignored | 2 red |
| M14 | the report opened with truncation, not exclusively | 3 red (exclusive create, lock never written, static guard) |
| M15 | report mode 0644 | 1 red |
| M16 | the default report path inside the repository | 1 red |
| M17 | the verdict ignores case | 1 red |
| M18 | the verdict accepts a prefix extension (an alias) | 2 red |
| M19 | no stop after a call over the ceiling | 1 red |
| M20 | the projected stop removed | 2 red |
| M21 | the projection ignores what is already spent | 1 red |
| M22 | an unknown-outcome gateway error counted as free | 1 red |
| M23 | a cost nobody reported counted as free | 1 red |
| M24 | the credential redaction removed | 1 red |
| M25 | a credential leak does not change the exit code | 1 red |
| M26 | the log-record scrub removed (the adapter logs the reported name) | 1 red |
| M27 | no report write after each model | 1 red |
| M28 | a bare `ProxyAdapter` instead of the product builder | 1 red |
| M29 | the opener tee not installed | 25 red |
| M30 | the tee keeps non-200 bodies | 2 red |
| M31 | the idempotency scope dropped | 1 red |
| M32 | `max_tokens` 4096 | 2 red |
| M33 | an exception's message put in the report | 1 red |
| M34 | `lock_candidate` ignores the rate check | 2 red |
| M35 | a subset can be a lock candidate | 1 red |
| M36 | an adapter without the opener seam accepted | 1 red |
| M37 | a mismatch exits 0 | 14 red |
| M38 | an unusable reported name printed raw | 3 red |
| M39 | an unreadable lock not turned into a refusal | 1 red |
| M40 | an existing report not mapped to its own refusal | **survived** in the first run (53 passed): the next handler maps the same error to a refusal too. The test now also asserts the message `never overwrites`; re-run: 1 red |
| M41 | the projection compares against twice the ceiling | 1 red |

The static guard `test_the_tool_reads_only_the_lock_and_the_environment` (no `open`, no write, no `read_text`, exactly one `read_bytes` of the lock and one `os.open` with `O_EXCL`, no mention of `provider.env`, `.env`, `dotenv`, `getenv` or `ANTHROPIC_API_KEY`) carries its own can-fail case, five additions each shown to change its findings (`test_a_check_that_cannot_fail_is_not_a_check`). A blank base URL is refused twice (by the tool and by the product adapter's settings check), so M07 mutates the conversion of the second into a refusal instead.

## Commands run

| Command | Result |
|---|---|
| `PYTHONPATH=src:$BS python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/scripts/test_model_probe.py` | 53 passed (also after every restore) |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` | 105 passed |
| governance one-liner on the task file | `[]` |
| `git diff --check` | exit 0 |
| `python -m scripts.model_probe.probe` (no flag), from the repository root | exit 2, `model probe refused before any call: --confirm-paid is required` |

## Integration notes

Merge `agent/prod-13a-model-probe-tool-01` onto `integration/ar-close-1026`; no dependency on another `PROD-*` item and no shared hotspot. The live run is the integrator's (`R-146af`): run the command above only if the process environment holds the credential, and do not search files for one. Read `lock_candidate:` and the `reported_model:` lines; write the lock only on `yes`. No `contracts/**`, migration, composition-root or lock change; the tool adds no contract.

## Known limits

- Nothing was run against a real gateway. What a real OpenRouter does with `max_tokens` 16 (a model that thinks may spend the 16 tokens before answering; a provider may refuse a small `max_tokens`) is untested. A refusal is a `no_verdict` block counted at zero; a truncated answer is a normal block (identity and usage are in the reply either way).
- The tool depends on one private slot of the adapter (`_opener`) to read the reported name, because the adapter's typed refusal does not carry it. If the slot disappears the tool refuses to run (a test), it does not probe blind. Reading it from the adapter's log was rejected: the log is not an interface.
- Only the `openai_chat` flavour. The pinned destination layer allows public addresses only and ignores `AUDITMANAGER_EXECUTOR_ALLOWED_HOSTS`; a gateway on a private address cannot be probed with this tool.
- `rate_check` uses the 20 % (at least USD 0.00002) tolerance of `executors/identity.py`, which was chosen by an earlier task, not by the owner. A reported cost outside it leaves `lock_candidate: no` and does not change the exit status; the integrator reads the numbers.
- `gpt-6-sol` is pinned for the Codex subscription through the pull agent. Whether OpenRouter serves it, and under which name, is unknown; the tool treats every probed model as metered.
- The ceiling is per run. It does not read the `R-29` wave ledger.
- During a run the tool installs a process-wide log-record factory (restored in `finally`) so that no log record of the adapter carries the credential.
- A gateway that echoes the credential somewhere other than the checked outputs (the report, the console, the log records of the run) is outside what the tool can see.

## Forbidden paths untouched

`git diff --name-only 0e663fd0..HEAD`:

```text
docs/program/PROD-13A-MODEL-IDENTITY-PROBE-TOOL-01.md
docs/program/tasks/PROD-13A-MODEL-IDENTITY-PROBE-TOOL-01.md
scripts/model_probe/probe.py
tests/unit/scripts/test_model_probe.py
```

No path under `src/`, `infra/`, `contracts/`, `db/`, `tools/`, `.github/`, no `P02_LOCK.json`, `Makefile`, lock file, `provider.env`, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, `PRODUCTION-READINESS-PLAN-01.md`, `OWNER_RULINGS_*` or ADR is in the list.
