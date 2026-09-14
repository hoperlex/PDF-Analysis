# P4 closure: what P4-RUN-01 reported, and what was done about each item

P4-RUN-01 ran the PC-02 corpus through the live proxy and reported three defects it did
not repair, one corpus observation, and one judgement call it declined to make on its own
authority. Each is ruled here. The session was right to leave all five alone: a session
that repairs the tree it is measuring cannot be cited for the measurement.

Dates are absolute. This file was written 2026-09-14.

## 1. Retry judgement — ACCEPTED, headline stands at 14/14

Three of seventeen attempts failed on `dependency_unavailable` at ~133 s and were
retried. The session offered the alternative headline (12/14 published, recall 7/9) in
case retrying was outside its brief.

Accepted, on four grounds, each checked against the artefacts rather than the report:

- **The failure is transport, not judgement.** `dependency_unavailable` is raised when
  the provider is unreachable. The model never answered, so no model output is being
  discarded and a retry cannot launder a bad answer into a good one.
- **The input is provably identical.** `run_baseline.py` gives only the *run* command's
  idempotency key an attempt suffix (`-a{N}`); the upload key is unchanged, so the retry
  reuses the version already published — same `version_uid`, same `sha256`, same profile,
  same prompt bundle. Read out of the harness source, not taken from the summary.
- **The failures are preserved, not swallowed.** Three attempt records are committed and
  the ledger carries `model_call_rows: 0` for each, so the alternative headline stays
  computable by anyone who disagrees with this ruling.
- **Accepting is the conservative reading.** Re-running a document the provider refused
  to answer for measures the model; abandoning it measures the proxy's uptime on one
  afternoon, which is not the question PC-02 asks.

## 2. Defect 1 — a failed stage published a null `error_code` — FIXED (`419a87b`)

The adapter read `stage.error["error_code"]`; the engine stores `code`. The comment above
the line names D4 as fixing exactly this, so the defect survived inside its own repair.
The consequence was not cosmetic: `dependency_unavailable` is **retryable**, so a run that
failed because the proxy was unreachable was published as an unclassified analysis
failure and an operator had no reason to retry it — during a run whose headline then
turned on whether retrying was legitimate.

Nothing caught it because no test drove a *failed* stage through the router, the same
blind spot that hid four C1 defects in the same method. `test_a_failed_stage_reports_its_code`
now pins the adapter against the engine's own dataclass and renders a real stored failure
through the API.

`artifacts/validation/PC-02/baseline/runs/attempts/PC02-S05.attempt1.json` is the field
evidence, preserved before the fix existed.

## 3. Defect 2 — `ledger_report.py` ignored the `cost_basis` column — FIXED (`419a87b`)

Migration `0004_cost_basis` recorded the discriminator; the tool went on deriving it by
comparing the stored figure against the rate card. That inference cannot work: the proxy
bills the published prices the rate card lists, so a genuinely **measured** cost equals
the estimate to the micro and was reported as `indeterminate`.

The tool now reads the column, keeps `cost_basis_stored` beside the derived label, and
probes `discriminator_column_exists` from the live schema instead of asserting `False` as
a literal — which it had gone on reporting after `0004` made it untrue.

While there: `--self-check` had been exiting 3 on 40 checks that described nothing.
`request_sha256` is not unique across recordings — the files under `variants/` are
deliberately the same request with a different response — so a dict keyed by checksum
kept one and a `*.json` glob never descended into `variants/` at all. Rows faithfully
replayed from a variant were reported as mismatches. Now exit 0, 421 checks, 0 failed.

## 4. Defect 3 — "a failed analysis records no `model_call` row" — NOT A DEFECT

The observation is true; the inference drawn from it is not, and the distinction matters
because the inference is the part that would justify a code change.

`src/auditmanager/analysis/text/stage.py` distinguishes two cases deliberately:

- `adapter.complete()` raised — **no response exists**, so there is nothing to record a
  row from. `model_calls=()` is correct, not lossy. These were the three failed attempts.
- a response arrived and something later failed — the call **is** recorded. The cost-
  ceiling path is the worked example: it returns `status=failed` carrying
  `model_calls=(_record(...),)`, with a comment stating the intent ("the spend that broke
  the budget is still recorded").

So the report's second sentence — "a run that failed *after* a call completed would leave
its spend unrecorded the same way" — does not hold against this code. The property is
already guarded: `tests/integration/analysis_text/test_cost_ceiling.py` asserts exactly
one `model_call` whose cost exceeds the ceiling on a failed outcome, and
`test_partial_and_status.py` asserts the empty tuple on the fail-closed path. Both
directions are pinned, so a regression would turn one of them red.

What survives is a **limit**, not a defect: when the provider is unreachable the client
has no response to read usage from, so any tokens the proxy consumed upstream are
invisible and total spend is a lower bound. That cannot be fixed from inside the
executor. `ledger.json` already states it in `failed_attempt_note`, unprompted and
correctly, which also closes the open item asking for it to be recorded.

No code change. `executor.py` is left as it is.

## 5. Corpus observation — `ENV-SIZE` is not exercised by its own guard — for P4-QA-01

`PC02-N03` is 27 303 351 bytes, over **both** the envelope's 25 MiB `ENV-SIZE` limit
(`src/auditmanager/ingest/envelope.py:153`) and the transport's 26 MiB multipart body
limit (`src/auditmanager/api/routers/multipart.py:30`). The transport guard is outermost
and refuses first, so the response carries `constraint: max_bytes` rather than
`byte_size <= 26214400`.

The document is refused for being too large, which is what the rule states, so the
negative result is honest. But the run never reaches `ENV-SIZE`, so the corpus does not
demonstrate that guard — it demonstrates the transport's. The two are independently
breakable, and a regression in `ENV-SIZE` would leave this corpus green.

**Action for P4-QA-01** (`fixtures/validation/PC-02/`): add a fixture between 25 MiB and
26 MiB — 26 000 000 bytes sits cleanly inside the window. That one document reaches
`ENV-SIZE` with the transport guard satisfied, and the existing `PC02-N03` should stay,
since the outermost guard is worth a case of its own. Not a product defect and nothing in
`src/` should move for it.

## 6. Recommendations the session recorded and did not apply

Left unapplied here too, and repeated so they are not lost with the task file:

- PC-02's precision evidence is **saturated**: zero findings across nine controls and an
  empty third group. Further runs against this corpus cannot discover a new failure mode.
  Precision evidence that generalises needs documents of a different *shape* — tables,
  drawings, multi-column text, genuinely borderline cases — not more near-miss statements
  of the anticipated twelve archetypes. This is the strongest input available to the P05
  corpus decision and should be read beside `OD-17`.
- `PC02-C01` and `PC02-C07` returned after 10 output tokens; `PC02-C09` reasoned for 530
  and still published nothing. If a later checkpoint wants to know whether a clean
  document was actually *read*, output-token count is a cheap proxy worth recording
  beside the finding count.
- A retry policy for `dependency_unavailable` belongs in the run executor, not in each
  caller. Three failures in seventeen attempts at 133 s each is an 18% attempt-failure
  rate that every future caller would otherwise re-implement. Ruling 1 above accepts a
  retry performed by hand; that is not a licence for every caller to invent its own.

## Still open, and owned by the customer

- **`OD-17`** — synthetic-only or anonymized real documents for the next corpus. Item 6's
  saturation finding is the evidence this decision was waiting on.
- **`OD-18`** — 3–5 named experts, at least 2 independent of the build team, with
  committed slots, required before `P4-BHV-01` can label anything.
- **The 21st code.** The catalog is a frozen 20-member enum and has no code for "usable
  output over a strict subset of the input". Raised in `GATE_B1_CLOSURE` §4 item 6 and
  still unanswered; adding a member to a frozen catalog is an owner decision, not an
  integrator one.
