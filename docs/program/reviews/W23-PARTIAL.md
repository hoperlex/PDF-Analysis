# W23-PARTIAL — `partial` is inducible, and the reason it was not is a defect

**Session** `W23-PARTIAL` · base `origin/dev` = `5ed72cc` (contains `6e07b97`) · branch
`agent/w23-partial` · worktree `/root/w23partial` · lane instance `gate-w23b`
(PostgreSQL 55930, MinIO 59530/59531, database `audit_w23b`, bucket
`auditmanager-gate-w23b`). No image was built. `df -h /` on arrival: 12 GB free.

`PA-01` criterion 4 was recorded by `W21-CERT` as holding *with a named exception*:

> **Exception: `partial` is not inducible** — it needs a *truncated* provider call and
> nothing in the operator's surface picks a model or output ceiling.

**The mechanism half of that sentence is exactly right. The diagnosis is not.** On the
`proxy` transport — the one `W21-CERT` itself certified criterion 4 on — `partial` was
not a limit that nobody could reach. It was a **defect**: a reply cut short at the
output ceiling was not recognised as cut short at all, and published as a complete
analysis. With that repaired, a run through the public API origin reaches `partial`.

---

## 1. Base, measured before anything was touched

`make gate FOUNDATION_PYTHON=/usr/bin/python3.12` on `5ed72cc`, this lane:

```
battery   1865 passed, 5 skipped, 1 warning, 168 subtests passed in 219.37s
foundation 35 passed in 28.62s
frontend  Test Files 48 passed (48)   Tests 706 passed (706)
GATE OK: battery, foundation, frontend and whitespace all pass
GATE_EXIT=0                      <- from `$?`, not through a pipe
```

Identical to the brief's figures in every number.

**And at `51ddf1b`, this branch's head**, same lane, same command:

```
battery   1870 passed, 5 skipped, 1 warning, 168 subtests passed in 237.22s
foundation 35 passed in 28.95s
frontend  Test Files 48 passed (48)   Tests 706 passed (706)
GATE OK: battery, foundation, frontend and whitespace all pass
GATE_EXIT=0
```

`+5` on the battery and nothing else moved: the five guards in §8. Frontend and
foundation are untouched, as the diff says they should be — this branch changes
`src/auditmanager/analysis/text/proxy.py`, two test files under
`tests/integration/analysis_text/` and this document, and nothing else.

---

## 2. What produces `partial`, measured

One chain, and nothing else in the implementation reaches the terminal:

```
provider stop reason
  -> ModelResponse.truncated          adapter.py:84   stop_reason == "max_tokens"
  -> STATUS_PARTIAL                   stage.py:398    and >= 1 grounded observation
  -> stage_statuses["text_analysis"] == "partial"
  -> TerminalSelection(state="partial")  findings/terminal.py:123
```

Established rather than assumed:

* **`stage.py`'s own docstring is the authority and it is unambiguous** — from the stage
  registry's status policy and `P02_SEAMS.md` §4.7: *"`partial` — usable observations
  over a **strict subset** of pages, with a typed error. **Only a provider reply cut
  short at the output ceiling produces this.**"* An exhausted cost ceiling is `failed`,
  and so is an unavailable provider. So `AUDITMANAGER_RUN_COST_CEILING_USD`, the one
  operator-facing knob that sounds like a lever here, is not one.
* **A truncated reply that yields nothing usable is `failed`, not `partial`**
  (`stage.py:366`): `partial` is a strict *subset*, and none is not a subset.
* **The contract declares a second route and PC-01 does not implement it.**
  `contracts/domain/v1/state-machines.json` reaches `partial` through
  `optional_branch_policy.terminal_selection` as well. There is no occurrence of
  `optional` anywhere in `runs/executor.py`, `select_terminal` takes a flat
  `required_stages`, and no stage in PC-01 is an admitted optional branch. So that route
  exists on paper only, and the truncation route is the whole of the implementation.
* **`text_analysis` is the only stage that can report `partial`.** Grepped across
  `analysis/`, `runs/` and `findings/`: `STATUS_PARTIAL` is produced in exactly one place.

---

## 3. What stood between an operator and it — three answers, one per transport

### 3.1 `proxy` — a defect, not a limit. `W23PARTIAL-1`

`proxy.py:_stop_reason` translated OpenAI's `finish_reason: "length"` into the string
`"truncated"`. **That is a word from the wrong vocabulary.** There are two:

| vocabulary | values | who writes it |
|---|---|---|
| provider **stop reason** — `ModelResponse.stop_reason` | `end_turn`, `max_tokens` | the provider; `live.py:84` passes it through untouched; every recording under `fixtures/recorded/text_analysis` is written in it |
| **call status** — `ModelCallRecord.status` | `succeeded`, `truncated`, `failed` | `stage.py:241`, *derived* from `ModelResponse.truncated` |

`ModelResponse.truncated` is `stop_reason == "max_tokens"`. Writing the derived word into
the field the derivation reads meant it was never `True`. Measured on `5ed72cc`:

```
ModelResponse(stop_reason='truncated').truncated            -> False
run_text_analysis, real ProxyAdapter, finish_reason='length'
  -> status 'succeeded', call_status 'succeeded', pages_analysed [1, 2, 3]
```

So the consequence was never only that `partial` went undriven. The call was recorded
`succeeded`; `_pages_analysed` returned **every** page, because its truncation clamp is
also gated on `response.truncated`; and the run published a cut-short analysis with a
full-coverage claim. A reader of that run could not tell it from a complete one.

**Why it survived.** The guard that covered this mapping asserted
`response.stop_reason == "truncated"` — the *string* — and never `response.truncated`,
the *decision* every consumer reads. The probe was on the wrong observable, so the
mapping was pinned in place by the test that was supposed to defend it.

The removed comment claimed the value was `"truncated"` *"which the migration 0003 CHECK
now admits"*. That is a third false premise: `stop_reason` is **never persisted** —
`ModelCallRecord` has no such field — and that CHECK constrains the `status` column,
which `stage.py` derives.

### 3.2 `recorded` — the corpus can answer, but only a test can ask it

`infra/deploy/env/alpha.env.example` sets `AUDITMANAGER_PROVIDER_MODE=recorded`, so this
is the alpha's default. A truncated recording already exists —
`fixtures/recorded/text_analysis/variants/truncated/6c208358….json`, `stop_reason:
"max_tokens"` — and `tests/integration/p02_journey/test_truncated_end_to_end.py` drives
it all the way to the CSV and the API body.

It is **filed under the baseline's own request checksum**, because a recording is keyed
by the request and the corpus, bundle and model are identical; the four answers to that
one question cannot share one directory. Reaching it means pointing an adapter at that
directory, which only the `variant_adapter("truncated")` test fixture does.
`bootstrap/composition.py:182` constructs `RecordedAdapter()` with **no argument**, so no
deployment can point it anywhere. That path is closed from outside, and closing it was
deliberate.

### 3.3 `live` — a genuine limit, and the brief's cheap route is not cheap

The ceiling is `MAX_OUTPUT_TOKENS = 16_000`, a literal in `prompt.py`. **Checked, because
the brief said exposing it might cost nothing:** there is no output-length name in
`bootstrap/settings.py` (which reads exactly `AUDITMANAGER_PROVIDER_MODE`,
`AUDITMANAGER_MODEL_ID`, `AUDITMANAGER_RUN_COST_CEILING_USD`, `ANTHROPIC_API_KEY`,
`AUDITMANAGER_API_TOKEN` and the three `PROXY_LLM_*`), none in
`infra/deploy/env/alpha.env.example`, and none in `provider.env.example`, which carries a
cost ceiling in **US dollars** and nothing in tokens. So it is a new name, not an exposed
one — and it would not be free:

`max_output_tokens` is hashed into `PromptBundle.content_sha256`, which is hashed into
`AnalysisProfile.content_sha256`, and `ADR-0011` requires published runs to reference an
**immutable** `AnalysisProfile` and `PromptBundle`. `profile.py` says what immutable means
here: *"the same identity resolves to the same content on every run and in every
process"*. A ceiling read from the environment makes `pb_01M25P3TH0PDQYVKTRQFEM0CYS`
resolve to different content in two deployments, and changes every key in
`fixtures/recorded/text_analysis` with it. **A configured output ceiling is a contract
change wearing an environment variable, and this session did not make one.**

---

## 4. The repair, and the run that reached `partial`

`_stop_reason` now maps `length -> "max_tokens"`, the stop-reason vocabulary the seam
reads. An unrecognised `finish_reason` is still passed through rather than guessed at, so
the repair cannot manufacture a `partial` out of a stop it does not know.

**The run.** `infra/deploy/serve.py` — the repository's own entry point, the one
`Dockerfile.api` runs — under this worktree's `.venv`, `AUDITMANAGER_PROVIDER_MODE=proxy`,
API on `127.0.0.1:58930`, health on `58931`, this lane's PostgreSQL and MinIO. The proxy
it was pointed at is a local stub of the proxy's own documented OpenAI-compatible
contract, answering `finish_reason: "length"` with one observation grounded in the seeded
`SI-01` contradiction on pages 2 and 6 of the eight-page `ar_baseline.pdf`. **Nothing
about the application is stubbed** — the real `ProxyAdapter` really opened a socket, and
`cost_basis: measured` below is that stub's reported figure travelling the real path.

`POST /projects` → `POST /projects/{uid}/documents` → `POST /runs` → `GET /runs/{id}`:

```
run_01M2X7XHFFVQJ9X7Y00ZYCYSVX   state: partial   provider_mode: live
  degradation_set        ["text_analysis"]
  text_analysis          partial, error_code partial_result_not_publishable
  the other three stages succeeded
  published_finding_count 1        diagnostic_observation_count 0
  cost_micros 41200, basis measured, model_call_count 1
  created 16:27:45.515Z   terminal 16:27:45.879Z
```

`model_call`, read from the database rather than from the envelope:

```
status | provider_mode | error_code | output_tokens | cost_micros | basis    | call_status | max_tokens
-------+---------------+------------+---------------+-------------+----------+-------------+-----------
truncated | live       | (null)     | 16000         | 41200       | measured | truncated   | 16000
```

`status='truncated'` with **no** `error_code`, which is what
`ck_model_call_truncated_has_no_error_code` requires. The CSV's `run_state` column reads
`partial`. The finding published from a cut-short reply carries its real evidence:
`page 2, chars 712–746, block b_000019`, quotation
`Степень огнестойкости здания — II.`

**The terminal was not proved by sleeping.** The poll bounded itself on the app's own
`state` field with a 120 s ceiling, and the bound was a finding rather than a skip. It was
not approached: the run was terminal on the **first** poll, 22 ms after `startRun`
returned, because `31500`-class in-process execution finishes on the request thread.

**The before half.** The same stub against the unrepaired code returns `published` with an
empty degradation set and `text_analysis: succeeded` — measured twice: as the two reds in
`241e496`, and accidentally on the real HTTP origin (see §7).

---

## 5. What this closes, and what it does not

**Closed.** The `partial` terminal is reachable end to end on the transport the deployment
uses, through the public API origin, with a real truncated provider call, a truthful
`model_call` row, a degradation set, a published finding and a `partial` CSV. `W21-CERT`'s
sentence *"there is no request an operator can make that provokes one"* is no longer the
operative obstacle; the obstacle was that the application could not **see** one.

**Not closed, and stated plainly.**

* **The UI badge was not driven by this session.** `W23-DEPLOY` is live in `infra/` and
  the brief forbids `web/`, so no browser was opened and no `next build` was run. What is
  established instead: `web/tests/unit/screens/run-progress.test.ts` renders
  `data-run-state="partial"`, the literal word `partial` in the badge, and
  `data-run-outcome="partial"` with a `data-degraded-stage` row per degraded stage — over
  the same envelope shape the run above produced, and it is green in the 706. That is a
  strong inference, not an observation, and it is recorded as the former.
* **No *end-user* lever produces `partial`.** Every route above is an operator of the
  *deployment*: who the proxy is, and what it answers. Inside the product journey — create
  project, upload PDF, start run — nothing chooses a model, a prompt or an output ceiling,
  and §3.3 says why exposing one is not a free act. If criterion 4 is read as requiring a
  lever inside the journey, that reading is still open and needs the ruling in §6.

---

## 6. The ruling that is still needed, phrased for a yes or no

> **Does `PA-01` criterion 4 require `partial` to be provoked from inside the operator's
> journey (create project, upload, run), or is it satisfied by `partial` being reached on
> the deployed path by a real truncated provider call, as §4 measures?**
>
> If the former is required, the follow-up is: **may `fixtures/recorded/text_analysis`
> carry a second canonical recording, keyed by a second acceptance document, whose
> `stop_reason` is `max_tokens`** — so that uploading that document induces `partial` with
> no new configuration at all?

The second question is the only route that puts the lever inside the journey without a
contract change, because a recording is keyed by the request and **the document is the one
part of the request an operator chooses**. This session did not take it: it needs a new
synthetic PDF under `fixtures/synthetic/ar/`, a `tools/fixtures/build_ar_corpus.py` change,
a `SHA256SUMS` and `expected_issues.json` entry and the contract tests that enumerate them
— none of which this session owns. `R-5` resealed this contract and a reseal is the
owner's act, not a session's.

---

## 7. What was false in the brief, and what I got wrong

**In the brief.**

1. *"If output length is already configurable anywhere in the deployment environment,
   exposing it costs nothing new. Check `bootstrap/settings.py` and
   `infra/deploy/env/alpha.env.example`."* — checked, and it is configurable in neither,
   nor in `provider.env.example`. §3.3 also shows the exposure would not be free.
2. *"the profile defers operator-facing model selection"* — `PROTOTYPE_PROFILE.md` §7.2's
   Deferred list says no such thing. What it does say, on the other side, is that
   *"explicit unsupported/failed/**partial** states"* are **included** scope, and §8.4
   requires the UI to distinguish `partial` among six states. `partial` is in scope; only
   the way to reach it was missing.
3. *"nothing in the operator's surface picks a model"* (`W21-CERT`, carried into the
   brief) — `AUDITMANAGER_MODEL_ID` does, `PROXY_LLM_MODEL` does, and
   `StartRunRequest.provider_mode` lets a client pick live or recorded per run. None of
   them picks an output ceiling, which is what the argument needed, so the conclusion
   survives its premise.
4. *"`runs/executor.py` selects terminals"* — it does not, and says so twice: *"The
   executor never selects a terminal."* `findings/terminal.py:select_terminal` does.
   Nothing under `src/auditmanager/runs/**` was edited.

**Mine, and it is worse than any of those.** My first attempt to serve the app wrote
`cd /root/w23partial && nohup … &`, which backgrounds the `cd` with the command. The
foreground shell never left `/root/projects/PDF-Analysis`, so `. ./.env` sourced **lane
`gate-b0`'s** environment and `infra/deploy/serve.py` resolved to the **main checkout's
unrepaired code**. One API process therefore ran for about three minutes against
`audit_b0` on port 55460 and bucket `audit-b0`, and added to that lane: two projects
(`prj_01M2X7R9WSKP7FCSTMPP8HWRHH` "probe" and `prj_01M2X7RKHJ0XSX88XQ2NYE2D5P`
"W23-PARTIAL induction"), one document version (`ver_01M2X7RKX80CZEYXJA29A8PG3W`) with its
document and blob, and one run (`run_01M2X7RKZ22ZZPJY2F72AR3APS`, state `published`) —
counted by a read-only query against `audit_b0`, not estimated. Additive only: nothing was
deleted, edited or migrated, and no row of that lane's existing data was touched. **I have
not cleaned it up**: deleting rows from a lane I do not own is a larger violation than the
one I committed. Whoever owns `gate-b0` should drop those rows, or ignore them.

It was caught by reading `/proc/<pid>/environ` when the run came back `published`, and the
run that §4 reports was re-driven from absolute paths against `audit_w23b` with the
process environment verified from `/proc` before the journey started. It is also, by
accident, the cleanest possible **before** measurement: the identical stub, the identical
journey, the identical public origin, the unrepaired code — `published`, empty degradation
set, `text_analysis: succeeded`.

Every process this session started was stopped by the PID it recorded. Nothing was killed
by name. The three `/app/serve.py` alpha processes and every other lane's services were
left running and untouched.

---

## 8. Guards, each shown able to fail

Red first in `241e496`, green in `d4af6b9`:

| guard | what reddened it |
|---|---|
| `test_a_length_stop_makes_the_response_report_itself_truncated` | `assert False is True` — the decision, on the property itself |
| `test_a_proxied_length_stop_makes_the_stage_partial` | `'succeeded' == 'partial'` through the real adapter and the real stage |
| `test_a_proxied_normal_stop_is_still_a_complete_success` | anti-vacuity: an adapter reporting every call truncated would pass the first two |
| `test_an_unrecognised_finish_reason_is_passed_through_not_guessed` | anti-vacuity the other way: `content_filter` must not become `max_tokens` and manufacture a `partial` |
| `test_a_length_stop_becomes_the_max_tokens_stop_reason` | the pre-existing guard, corrected; it asserted the string that *was* the defect |

**No characterization record moved, and no `permitted_change` was written.** The 36
records are journey responses captured against the **recorded** adapter; the proxy appears
in none of them. `tests/characterization` is 60 passed, unchanged, and
`PERMITTED_EXCEPTIONS` keeps its seven entries. A change that did not happen does not get
a note saying it did.
