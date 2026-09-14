# Task P4-RUN-01 — the PC-02 baseline run

> **Status: delivered.** Run by session `P4-RUN-01` on branch `agent/p4-run-01` from base
> commit `f91858a`. All fourteen measurable documents reached `published`; all four
> negative-envelope documents were refused. The baseline artifact
> `artifacts/validation/PC-02/baseline/baseline.json` is emitted and its shape is frozen
> by this task's acceptance, because `P4-BHV-01` hands it to experts and `P4-INT-01`
> reports from it. See **Handoff record** at the end of this file.

## Outcome

A live baseline run of the composed application over the whole PC-02 corpus, with every
published finding classified against ground truth mechanically, every published quotation
verified by an extractor the product does not share, and measured cost and latency
recorded per document — the findings that `P4-BHV-01` books domain experts to label, and
which nothing else in the P04 graph produces.

## Depends on

- `P4-QA-01` — the PC-02 corpus, its manifest, its checker and `PC-02_PROTOCOL.md`
- `P3-INT-01` — `PC-01` accepted; the application composes and answers
- owner decisions `OD-02` (operated LLM proxy), `OD-03` (USD 1.00 per-run ceiling),
  `OD-17` (synthetic corpus)

## Frozen inputs

- corpus: `fixtures/validation/PC-02/corpus_manifest.json`, `pc02-validation-corpus/1`
- matching rule: `docs/program/validation/PC-02_PROTOCOL.md` §11, `PC-02_PROTOCOL/1`
- document order: `PC-02_PROTOCOL.md` §4, pre-registered, not chosen here
- API contract: `contracts/api/v1/openapi.json`, twelve operations
- migration head: `0004_cost_basis`; not touched
- base commit: `f91858a`
- provider: `AUDITMANAGER_PROVIDER_MODE=proxy`, `PROXY_LLM_MODEL=anthropic/claude-opus-5`

## Allowed paths

- `artifacts/validation/PC-02/baseline/**`
- `docs/program/tasks/P4-RUN-01.md`

## Forbidden hotspots

`src/**`, `fixtures/**`, `tools/**`, `contracts/**`, `tests/**`, the `Makefile` and the
root locks are all outside this task. Nothing in them was edited. Three defects were
found in them and are reported below **unrepaired**, each naming its owning tree.

## Non-goals

- Any adjustment to the prompt, the analysis profile, a threshold or a matching rule in
  response to a result. The matching rule and the whitespace decision were both fixed
  before the corpus was scored; a rule adjusted after seeing findings measures the
  adjustment, and every number after it would be uncitable.
- Expert labelling. This task produces the finding lists; `P4-BHV-01` labels them.
- Inter-moderator agreement, κ, review time and navigation friction — those come from
  session records, not from a run.

## Deliverables

| Path | What it is |
| --- | --- |
| `baseline.json` | the artifact: per document and in aggregate |
| `run_baseline.py` | drives `create_app()` and its `Router`; twelve operations, no direct module import |
| `match_findings.py` | the §11 matcher and its three self-proofs |
| `verify_grounding.py` | independent quotation verification |
| `read_ledger.py` | measured cost and latency, read from `model_call` |
| `emit_baseline.py` | assembles the artifact; recomputes nothing |
| `runs/*.json` | what the application answered, per document |
| `runs/attempts/*.json` | the three run attempts that failed on a transient provider outage |

## Required tests

| Command | Exit | Result |
| --- | --- | --- |
| `.venv/bin/python tools/validation/corpus_check.py fixtures/validation/PC-02/corpus_manifest.json` | 0 | 14 documents, 9 seeded issues, 64 controls, 86 ground-truth quotations resolved |
| `PYTHONPATH=src .venv/bin/python artifacts/validation/PC-02/baseline/run_baseline.py` | 0 | 14/14 `published`, 4/4 negatives refused |
| `PYTHONPATH=src .venv/bin/python artifacts/validation/PC-02/baseline/match_findings.py` | 0 | self-proofs pass; recall 9/9 |
| `PYTHONPATH=src .venv/bin/python artifacts/validation/PC-02/baseline/verify_grounding.py` | 0 | 16 quotations verified, 0 failures |
| `PYTHONPATH=src .venv/bin/python artifacts/validation/PC-02/baseline/emit_baseline.py` | 0 | artifact emitted |
| `make foundation` | 0 | 35 passed |
| `git diff --check` | 0 | clean |
| `git diff --name-only f91858a..HEAD` | 0 | owned paths only |

Interpreter: `/root/p4run-scratch/.venv/bin/python` (CPython 3.12.3), built by
`make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12`. `PYTHONPATH=src` is set
explicitly on every invocation: `pyproject.toml`'s `pythonpath = ["src"]` is pytest
configuration and does nothing for a plain script, and `auditmanager` is not installed
into the environment.

## The result

**Recall: 9 of 9.** Every seeded issue was found, including the two the corpus built to
be awkward — the categorical seed `PC02-S03-I1` (roof type, flat against pitched, no
number to compare) and `PC02-S05-I2`, the placeholder that carries no placeholder word at
all ("Назначение помещения 1.12 — не определено.").

**Precision: no control was flagged as a defect.** The nine control documents published
**zero** findings between them. One control matches the §11 rule mechanically —
`PC02-S02-K6`, archetype `notation_variant` — and the mechanical count is reported as 1
of 64 because that is what the rule says. The reading is the opposite of a false
positive: the quotation is cited as *corroborating* evidence on the correct side of a
true contradiction, and the finding's own text groups it with the page-2 value
("4 812,5 м² (стр. 2 и 4)") against the different page-5 value. The model read the
notation variant exactly as the control intends. Both the count and the reading are in
the artifact; the count alone would misreport it.

**The third group is empty.** Nine findings were published and all nine match a seeded
issue. No finding matched neither. That is a clean result and also a limit: this run
produces **no evidence at all** about failure modes the corpus did not anticipate,
because the model produced nothing outside ground truth to examine. §12 of the protocol
already says the 64 controls bound precision only against the twelve archetypes they
cover; this run does not narrow that gap, and `P4-BHV-01` should not read an empty third
group as evidence that the gap is small.

**Grounding: 16 of 16.** Every published quotation exists on the page it declares.

**Cost: USD 0.28254 measured**, 14 model calls, every one `cost_basis = measured`. The
dearest run was `PC02-S05` at USD 0.029775 — 3.0% of the OD-03 per-run ceiling. No run
approached the ceiling and none halted on it.

## Integration contract

`P4-BHV-01` and `P4-INT-01` may rely on `baseline.json`, schema `pc02-baseline-run/1`:

- `documents[]` — one entry per measurable document, carrying `run_id`, `state`,
  `stages[]` with `stage_id`/`status`/`error_code`, `findings[]` each with its `group`
  (`seeded_issue` | `declared_control` | `neither`), `cost` and `latency`, `grounding`.
- `aggregate` — `recall`, `false_positive_pressure` (with `by_archetype`), `grounding`,
  `cost`, `latency`, `group_counts`.
- `seed_status` / `control_status` — every one of the 9 seeds and 64 controls, each with
  `found` / `flagged`, so a reader never has to infer absence from omission.
- `third_group` — findings matching neither, in full, with quotations. Empty in this run.
- `matcher_self_proofs` — the three proofs, re-run on every scoring.
- `negative_envelope` — the four refusals verbatim, excluded from every finding
  denominator.
- `provider_reliability` — the three failed attempts and the ledger's blind spot.

A finding's `finding_uid` is **not** stable across runs and must not be used to pair
findings between this baseline and any later one; pair by document, category and
evidence quotation, as §11 says.

## Failure / idempotency / security cases

- **Provider outage.** Three of seventeen run attempts ended `failed` /
  `analysis_failed`, each with `dependency_unavailable` ("the model proxy could not be
  reached") after ~133 s. `PC02-S05` failed twice and published on the third attempt in
  9.1 s; `PC02-C07` failed once and published on the second in 3.3 s. The same document,
  prompt, profile and model were used every time — only the run command's idempotency key
  changed, because replaying a run key returns the original failed run rather than
  retrying. Nothing was tuned.
- **Idempotency.** Upload keys are reused deliberately across attempts so a retry replays
  to the same `version_uid` and publishes no second version; only the run key varies.
- **Security.** `.env` and `.env.provider` are git-ignored and were not committed. No
  token appears in any artifact. The corpus is synthetic under `OD-17`.

## Rollback / feature flag

Not applicable. This task adds no code to the product and changes no behaviour; it writes
measurement artifacts under `artifacts/` only.

## Defects found, left unrepaired

Each names the tree that owns it. None was repaired: this task owns neither.

1. **A failed stage publishes a null `error_code` through the API.** Owning tree
   `src/auditmanager/bootstrap/adapters.py:302`. The adapter reads
   `(stage.error or {}).get("error_code")`, but the persisted value is a `StageError`
   whose field is `code` (`src/auditmanager/analysis/engine/result.py:102`, stored as
   jsonb `{"code": ..., "message": ..., "retryable": ...}`). `.get("error_code")`
   therefore returns `None` for every failed stage. The comment directly above that line
   records D4 — "a stage that failed because the provider was unreachable carried a null
   `error_code` … the code is in the stage's own error" — so this is a fix that reads the
   wrong key and leaves the reported defect in place. Observed on all three failed runs:
   the database holds `dependency_unavailable` and `getRunStatus` published
   `"error_code": null`.

2. **`ledger_report.py` ignores the `cost_basis` column.** Owning tree
   `tools/validation/ledger_report.py` (`P4-OPS-01`). It derives the basis by comparing
   the stored cost against a rate table and reported `"cost_basis": "indeterminate"` with
   the reason *"the schema records no measured-or-estimated discriminator"* — which
   migration `0004_cost_basis` made untrue. The column reads `measured` for all 14 calls.
   Anything citing the tool rather than the column will understate the provenance of
   every proxy-mode cost figure.

3. **A failed analysis records no `model_call` row.** Owning tree
   `src/auditmanager/runs/executor.py`. The three failed attempts wrote no row at all, so
   whatever they consumed upstream is invisible to the cost ledger. Total spend is
   therefore a lower bound. It is a very small one here — the failures were connection
   failures, so probably nothing was billed — but a run that failed *after* a call
   completed would leave its spend unrecorded the same way.

Additionally, **`ENV-SIZE` is not exercised by its own guard**. `PC02-N03` is 27 303 351
bytes, over both the envelope's 25 MiB `ENV-SIZE` limit
(`src/auditmanager/ingest/envelope.py:153`) and the transport's 26 MiB multipart body
limit (`src/auditmanager/api/routers/multipart.py:30`). The transport guard is outermost
and refuses first, so the response carries `constraint: max_bytes` rather than
`byte_size <= 26214400`. The file is refused for being too large, which is what the rule
states, but this run does not reach the envelope's own `ENV-SIZE` check. A fixture
between 25 and 26 MiB would. This is a corpus observation for `P4-QA-01`
(`fixtures/validation/PC-02/`), not a product defect.

## Recommendations (not applied)

The rule that no result may be tuned for applies to this session, so these are written
here and the code is untouched.

- The corpus's precision evidence is now saturated: zero findings on nine control
  documents, and an empty third group. Further runs against PC-02 will not discover a
  new failure mode. If P05 wants precision evidence that generalises, it needs documents
  with a *different* shape — tables, drawings, multi-column text, or genuinely borderline
  cases — not more near-miss statements of the anticipated twelve archetypes.
- `PC02-C01` and `PC02-C07` returned after 10 output tokens; `PC02-C09` reasoned for 530
  output tokens and still published nothing. If a later checkpoint wants to know whether
  a clean document was actually *read*, output-token count is a cheap proxy worth
  recording beside the finding count.
- A retry policy for `dependency_unavailable` belongs in the run executor rather than in
  each caller. Three failures in seventeen attempts, each costing 133 s, is an 18%
  attempt-failure rate; `P4-BHV-01` runs documents in front of a waiting expert and
  cannot absorb that.

## Handoff record

- **Changed files:** `artifacts/validation/PC-02/baseline/**` (31 files) and this file.
  `git diff --name-only f91858a..HEAD` lists nothing else.
- **Commands and results:** see *Required tests*. Every listed command exited 0.
- **Known limits:** one run per document, so nothing here bounds run-to-run variance.
  The corpus is synthetic (`OD-17`) and single-discipline, single-language. An empty
  third group is not evidence that unanticipated failure modes are rare. The `useful` /
  `incorrect` / `unclear` rates and the F5 rate are **not** in this artifact and cannot
  be derived from it; they come from `P4-BHV-01`'s session records.
- **Integration notes:** `baseline.json` is the interface. Re-running
  `run_baseline.py` skips documents already recorded, so the artifact is resumable; to
  re-measure from scratch, remove `runs/` first and use a fresh `P4RUN_TAG`.
