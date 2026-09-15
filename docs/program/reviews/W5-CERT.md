# `W5-CERT` — PC-01 re-certification (in progress)

Session `W5-CERT`. Started 2026-09-15T13:48Z. Base `beaa7f7` on `planning/prototype-roadmap`
(= `origin/dev`). Working branch `agent/w5-cert`, worktree `/root/w5cert`.

**HEAD on arrival: `beaa7f7`** — not `origin/main` (`6d3c0f3`, the parked PC-01 commit) and
not the brief's stated base `ef5b8bf`. `git diff ef5b8bf..beaa7f7 --stat` touches only
`docs/program/dispatch/W5-ADV.md` and `docs/program/dispatch/W5-CERT.md` (15 insertions,
11 deletions), which is the brief's own "harmless, carry on" case. Certification therefore
reports against `beaa7f7`; `src/`, `db/`, `tests/` and `contracts/` are byte-identical to
`ef5b8bf`.

## Environment

Instance `gate-w5`, `POSTGRES_PORT=55560`, `S3_API_PORT=59160`, `S3_CONSOLE_PORT=59161`,
`POSTGRES_DB=audit_w5`, bucket `auditmanager-gate-w5`. All three ports confirmed free before
`make up`. `.env` copied from `.env.example` and set to exactly this instance.
`.env.provider` is git-ignored and does **not** propagate into a new worktree; copied in
from the primary worktree, mode 600.

## Commands so far

| Command | Exit | Observed |
|---|---|---|
| `git rev-parse HEAD` | 0 | `beaa7f7` |
| `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` | 0 | `bootstrap OK` |
| `make bootstrap …` (second, deliberate) | 0 | `bootstrap OK`, `git status --porcelain` empty |
| `make up` | 0 | postgres, s3, s3-init all healthy |
| `make foundation` | 0 | 3 `FOUNDATION-CHECK OK` sentinels; 35 passed |
| `python -m auditmanager.api.app` | 0 | `wired, provider_mode=proxy`, `operations=12` |
| same, `DATABASE_URL` unset | 2 | refusal naming `DATABASE_URL` |
| same, `PROXY_LLM_TOKEN` unset | 2 | refusal naming `PROXY_LLM_TOKEN` |
| `pytest tests --ignore=tests/contract --ignore=tests/checkpoint` | 0 | **793 passed, 5 skipped, 116 subtests** |
| `git diff --check` | 0 | clean |
| `pytest tests/e2e/pc01` (recorded) | 0 | **49 passed, 5 skipped** |

Gate matches the brief exactly.

## The live run — criteria 4 and 5

**Blocked first by a defect, in a tree I do not own.** See DEF-1 below. The run was
then performed from a second, deeper checkout of the same commit, with the canonical
suite unmodified.

| Command | Exit | Observed |
|---|---|---|
| `C2_PC01_LIVE=1 pytest tests/e2e/pc01/test_live_text_analysis.py` (from `/root/w5cert`) | 1 | **5 errors**, `IndexError: 2` at `test_live_text_analysis.py:84` |
| same, from `/root/certrun/w5deep` (depth 3) | 0 | **5 passed** |

Figures, read from the database rather than from the suite's own output:

* run `run_01M2JNSEFQ4N9GFV5BYK4606E6`, state `published`, `provider_mode` **`live`**,
  `terminal_reason` null, `degradation_set` empty.
* `model_call` ledger row: provider `anthropic`, model identity **`claude-opus-5`**,
  status `succeeded`, `input_tokens` 3895, `output_tokens` 750, `latency_ms` 12229,
  `cost_micros` 38225, **`cost_basis` `measured`**.
* **Cost USD 0.038225 against the USD 1.00 `OD-03` ceiling** (`cost_ceiling_usd: 1.0`
  recorded in the stage metrics).
* **Seeded issues found: 3 of 3** (`SI-01`, `SI-02`, `SI-03`).
* **Near-miss controls flagged: 0 of 6.**
* Every published quotation verified present on its declared page, against the corpus's
  own extractor (`tools/fixtures/ar_corpus/pdfextract.py`), not the product's.
* `evidence_emitted` 5, `observations_emitted` 3, `evidence_unresolved` 0,
  `observations_dropped_unresolved` 0.
* Retry provenance on the stage: `attempts` 1, `attempt_budget` 3,
  `attempt_budget_exhausted` false, `retry_waited_seconds` 0.0,
  `retried_on_error_code` null.
* `output_tokens_source: "provider"` — the wave-2/3 change reaching the metrics, as the
  brief's map claimed.

**Identical to PC-01 on both product numbers: 3 of 3 and 0 of 6.** Cost is lower
(0.0382 against the accepted report's 0.1147).

What would have made this fail: the suite pins `PROXY_LLM_MODEL` to
`anthropic/claude-opus-5` rather than reading it from the file, and asserts
`settings.proxy_model == LIVE_MODEL` before spending, so a run routed to the proxy's
small default model fails at the fixture. `page_texts` pins the extractor against the
manifest's `page_text_sha256` before any quotation is compared, so a quotation check
cannot pass by measuring the extractor. `provider_mode` is asserted to read `live`, and
`cost_basis` reads `measured` rather than `estimated` — an unreached provider could
produce neither.

## Criterion 2 — migration from empty, re-proved

The path PC-01 certified is not the path that exists. Head is now
**`0005_truncated_call_status`**, two migrations past the `0003_open_items` the accepted
report and the runbook both name.

Proved on a pristine database (`audit_w5_empty`, created empty, 0 tables) rather than on
the one `make up` had already migrated:

| Command | Exit | Observed |
|---|---|---|
| `alembic upgrade head` on an empty database | 0 | all five migrations in sequence, `0001` → `0005` |
| table count after | — | 17 (`alembic_version` + the 16 domain tables) |
| `alembic downgrade -1` | 0 | back to `0004_cost_basis` |
| `make check-db` against the downgraded database | **2** | **`FOUNDATION-CHECK FAIL check-db`**, naming `0004_cost_basis` against expected `0005_truncated_call_status` |

**What would have made it fail:** it did fail, on demand. `check-db` compares the code's
declared head against the database's and prints `FOUNDATION-CHECK FAIL` with both values;
downgrading one migration turned the same command red (exit 5, `make` exit 2). The sentinel,
not the exit code, is the evidence — as the runbook insists.

A first attempt at this red test tripped a *different* guard: changing only `DATABASE_URL`
was refused by the `.env` coherence check (`P1-INT-00: the service side and the application
side of .env disagree`). That guard is also real.

## Criterion 10 — explicit failures, including the retry-exhausted path

### The retry-exhausted path, reached from outside

Driven through the router with `PROXY_LLM_BASE_URL` pointed at `http://127.0.0.1:59199`,
where nothing listens. Nothing imported `execute_run`; every fact below is from a response
or from the database after it.

Run `run_01M2JNYQZ95TDCJ45BMX76QBKC`:

* `start_run` answered **202** with state **`failed`**;
* **`terminal_reason` = `dependency_unavailable`** — not the generic `analysis_failed` the
  accepted PC-01 report recorded;
* `degradation_set` = `["text_analysis"]`; the three deterministic stages `succeeded`;
* **`GET /runs/{id}/findings` returned `{"items": []}` — nothing published**;
* stage metrics: **`attempts` 3, `attempt_budget` 3, `attempt_budget_exhausted` true,
  `retry_waited_seconds` 10.0, `retried_on_error_code` `dependency_unavailable`**;
* stage error: `{"code": "dependency_unavailable", "message": "the model proxy could not
  be reached", "retryable": true}`;
* **wall clock 10.41 s**, against the pinned ladder `BACKOFF_SECONDS = (2.0, 8.0)` — the
  backoffs were really taken, not merely declared;
* `model_call` rows for the run: **0**. The provider was never reached, so there is no
  response to record. The attempt count survives as scalar provenance on the stage row,
  which is what `retry.py`'s docstring says it will do.

**Verdict on the brief's open question.** The new retry behaviour is **better** conformance
to §8 criterion 10, not a violation. It does not convert a hard failure into a success: the
run fails explicitly, publishes nothing, and now names the transport cause instead of
hiding it behind `analysis_failed`. The distinction is structural, not a comment —
`RetryPolicy.__post_init__` refuses to construct over any code the frozen catalog does not
mark `retryable`, and `analysis_failed` is `retryable: false`, so a policy that retries a
model's bad answer is not expressible without editing a frozen contract.

**What would have made it fail:** a run that published, a `terminal_reason` of
`analysis_failed`, `attempts` of 1, or an elapsed time under 10 s would each have
contradicted a specific assertion above. The 10.41 s is the load-bearing one: it is the
only figure that could not be produced by a run that skipped the retries and reported them.

### `OD-03`'s ceiling across attempts — confirmed, and a defect found while confirming it

Structurally the ceiling is a property of the run: `executor.py:546` builds one `CostMeter`
above the attempt loop and hands the same object to every attempt, with the comment that
building it inside "would give every attempt a fresh USD 1.00".

Empirically, the ceiling is load-bearing. With
`AUDITMANAGER_RUN_COST_CEILING_USD=0.01` **in the process environment**, run
`run_01M2JP3R2SGJVK0E1JG0TGFQNK` reached state `failed`, `terminal_reason`
**`cost_budget_exceeded`**, and published nothing.

But the same value supplied through `create_app(environ=…)` was **ignored** — see DEF-2.
