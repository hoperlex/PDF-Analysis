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

## The two accepted limits — re-examined, not inherited

### `checksum_mismatch` — **still not inducible. My own verdict, not an inheritance.**

Two independent checks.

*Is there any way in?* All twelve operations were enumerated from
`contracts/api/v1/openapi.json` (and the count agrees with the composition root's
`operations=12`). Four are writes: `createProject`, `uploadDocument`, `startRun`,
`appendDecision`. **No request body of any of them carries a `sha256`, `checksum`,
`digest`, `etag` or `content_md5` field.** A caller cannot declare a digest, so a caller
cannot declare one that disagrees. Nothing in waves 2–3 changed this: the only API-surface
change was read-only query parameters on the findings listing (`ports.py`).

*Is the guard real where the limit says it is proved?* Handed directly to `S3BlobStore`:

| Probe | Result |
|---|---|
| bytes with a false digest (`0`×64) | **refused** — `ChecksumMismatchError`, `storage_integrity_error`, "Nothing was published" |
| bytes with a false size (55 declared as 56) | **refused** — `SizeMismatchError`, `storage_integrity_error` |
| the same bytes with their true digest and size | **accepted** — `PublishedBlob` |

The limit stands, on both halves.

### `ungrounded_model_item` — **still unreachable by design. My own verdict, and the dispatch's premise about it is wrong.**

**The dispatch expected this limit's subject to have moved. It did not.** `stage.py` and
`provenance.py` did change, so the instruction to re-check was right — but `_ground`, the
drop-before-the-gate that the limit is actually a claim about, is **byte-identical** to
`6d3c0f3` (zero changed lines in the diff touch grounding). `findings/grounding.py` is
unchanged, and migrations `0002`/`0003`, which define the `grounded` column and its
`ck_finding_observation_ungrounded_reason` constraint, are unchanged. The wave 2–3 edits to
those two files are additive provenance — `cost_basis`, token counts, `call_status`, and a
new `ModelCallRecord.__post_init__`.

That is an argument from reading, so I did not stop there. Against an isolated copy of
`src/` outside the worktree — proved to be the imported one by printing
`auditmanager.__file__ = /root/w5cert-mutate/src/auditmanager/__init__.py` before trusting
any result, with `contracts/`, `docs/`, `fixtures/` and `tools/` symlinked so
`analysis.text.lock` could still reach `P02_LOCK.json` from `parents[4]`:

| Run | Mutation | Result |
|---|---|---|
| baseline | none | `published`, **3 findings** — the copy behaves like the tree |
| **A** | every quotation forced unresolvable, drop **intact** | `published`, **0 findings**; `observations_proposed` 3, `observations_emitted` 0, `observations_dropped_unresolved` 3, `evidence_unresolved` 5; **0 observation rows written** |
| **B** | unresolvable **and** the drop removed | **`failed`**, `terminal_reason` `analysis_input_invalid`, **0 findings published** |

Across all three, and across a database then holding **89 observation rows**, the count of
`grounded = false` rows was **0**.

So: the drop is real and load-bearing (A turns 3 findings into 0), and removing it does not
open a path to an ungrounded row — it sends the run to `failed`, which is what the accepted
report claimed and what I have now re-established rather than taken on trust. **The limit
stands.**

## The remaining criteria

**Criterion 1.** Three `FOUNDATION-CHECK OK` sentinels; 35 foundation tests. Red: the
composition root exits **2** naming `DATABASE_URL` when it is unset, and naming
`PROXY_LLM_TOKEN` when the mode is `proxy` and the token is absent.

**Criterion 3.** `uploadDocument` → 201, `version_ordinal` 1, `sha256` `6d53674f…` — which
I recomputed from the corpus bytes myself rather than reading back what the API said.
`streamDocumentVersionContent` returned 58978 bytes identical to the file. Red: a non-PDF
through the same operation → 422 `validation_failed`, `constraint: pdf header`.

**Criterion 4.** Four stages `succeeded`; the run reports `provider_mode` `live` and the
ledger row `cost_basis` `measured`. Red: the composition refuses a mode it cannot provide,
and a run whose stage never reaches the provider records `attempts` 3 and no `model_call`
row at all.

**Criterion 6.** Evidence page 2, chars 712–746, quotation verified present on page 2 by the
corpus's own extractor **and verified absent from a different page** — the control that
makes the check non-vacuous. `accept` 201, `reject` 201, later `comment` 201; history went
1 → 2 events with the earlier event unchanged as a prefix, and the verdict stayed
`accepted` across the comment. Red: a direct `UPDATE` on `expert_decision_event` is refused
by the database — `state_transition_not_allowed: expert_decision_event is an append-only
ledger; UPDATE is refused`, raised `USING ERRCODE = 'AM002'`.

**Criterion 7.** 17 columns, 5 data rows, UTF-8 BOM, CRLF, `text/csv; charset=utf-8`, two
exports byte-identical. Row 1 carries this exact project, version and run uid and the
current verdict. Red: a second run over the same version exports different bytes, so the
export is a function of the run and not of the corpus. **The accepted report's 4251 bytes
reproduced exactly** on a run with no decisions; the same run with an accept and a reject
recorded exports 4525, which the runbook did not say and now does.

**Criterion 8.** A real `make down` (network and containers removed) then `make up`; all
three service checks exit 0. Through a **fresh composition root**: run `published`, 3
findings, verdict `accepted`, 2 decision events, `version_ordinal` 1, and the published S3
object streamed back byte-identical to the original upload.

**Criterion 9 — the one the dispatch said to look hardest at.** Replaying
`createProject`, `uploadDocument` and `startRun` under **identical** keys returned the same
`project_uid`, `version_uid` and `run_id`, and changed **no row count in any of the sixteen
tables**. The CSV was byte-identical across the replay and the decision history and verdict
were unchanged. The first pass is the control that proves the counter moves at all: it
created rows in 12 of the 16 tables. The new retry module does not disturb this — it never
issues a second command and the run's idempotency key never changes.

## Defects found, left unrepaired

### `W5CERT-DEF-1` — owning tree `tests/`

`tests/e2e/pc01/test_live_text_analysis.py:84`:

```python
candidates.append(driver.REPOSITORY_ROOT.parents[2] / ".env.provider")
```

Unguarded index. Any checkout two or fewer levels below `/` raises `IndexError: 2` during
fixture setup, so all five live tests **ERROR** — they do not run and they do not skip.
`/root/w5cert` and `/root/w5adv` are both such paths, and this dispatch instructs sessions
to work under `/root/`. Where it does not crash it resolves to `/`, not to the parent
checkout its own comment says it is reaching for, so that fallback has never worked
anywhere. Criterion 4's live requirement is unreachable from a dispatched worktree at the
depth the dispatch prescribes. Worked around by running from a second checkout of the same
commit at depth 3, suite unmodified.

### `W5CERT-DEF-2` — owning tree `src/`

`src/auditmanager/bootstrap/composition.py:153`:

```python
config = load_provider_config(
    dict(os.environ) | {"AUDITMANAGER_PROVIDER_MODE": _provenance_mode(settings.provider_mode)}
)
```

It builds from `dict(os.environ)`, not from the `environ` mapping `create_app` was given,
overriding only the provider mode. Consequently **`AppSettings.run_cost_ceiling_usd` is
written at `settings.py:139` and read nowhere** — `grep -rn run_cost_ceiling_usd src/`
shows the only consumer is `ProviderConfig`'s own field, populated by a second, independent
read of the environment. Two resolutions of one `OD-03` ceiling, which can disagree:

| How the ceiling was supplied | `settings` reported | stage recorded | Outcome |
|---|---|---|---|
| `create_app(environ=…)`, 0.01 | 0.01 | `cost_ceiling_usd` **1.0** | **`published`**, having spent 0.038775 |
| process environment, 0.01 | 0.01 | — | **`failed`**, `cost_budget_exceeded`, nothing published |

Not a journey-level violation in a normal deployment, where one environment feeds both
paths — which is why the verdict below is not withheld on it. But it breaks the composition
root's stated contract that `create_app(environ=…)` composes from that mapping, and any
future test that set the ceiling through `build_client` would be **silently vacuous** —
the exact failure shape this programme keeps catching. `tests/conftest.py:30` strips the
name for the whole session, so nothing in the suite would have caught it.

## Premises in the dispatch that were false

1. **"`bootstrap/settings.py:33`"** — the `OD-02` revision date is on line **34**.
2. **"Credentials are already on disk in `.env.provider`."** True only in the primary
   worktree. `.env.provider` matches `.gitignore` line 2 and therefore does **not** exist
   in a worktree created by the dispatch's own provisioning commands. Copied in by hand.
3. **"One run … costs roughly $0.20."** It cost **$0.038**. The accepted report's own
   figure was $0.1147. Not harmful, but the ceiling headroom is five times what was stated.
4. **"`docs/manual-tests/PC-01_prototype.md` … is current."** Its step 1 still expected
   migration head `0003_open_items`, two migrations stale. Corrected, as a path I own.
5. **"The second limit is a claim about exactly that code [that moved]."** The files moved;
   the code the claim is about did not. See above. The instruction to re-check was still
   right, and the re-check was worth doing.
6. **Base commit.** The dispatch names `ef5b8bf`; `origin/dev` is `beaa7f7`, two commits
   ahead, touching only `docs/program/dispatch/**` — the case the dispatch itself says is
   harmless.

Everything else in the dispatch checked out: the gate figures (793/5/116, 35), the 915-line
change surface, the instance ports, the `proxy` mode, `operations=12`, the `/tmp` warning,
and every row of the criterion map.

## Verdict

**PC-01 holds at `beaa7f7`, with two named defects, neither of which invalidates a
criterion.**

All ten criteria of `PROTOTYPE_PROFILE.md` §8 are satisfied, and each was shown able to
fail. The product numbers are unchanged from the accepted report: **3 of 3 seeded issues
found, 0 of 6 near-miss controls flagged.** Both accepted criterion-10 limits were
re-established by my own probes rather than inherited, and both still hold.

Criterion 10 is **stronger** than at `6d3c0f3`, not weaker. The new retry does not launder a
failure into a success: an unreachable provider costs three bounded attempts and then fails
the run explicitly, publishing nothing, and the run row now names `dependency_unavailable`
where it used to say `analysis_failed`. That is better conformance to §8's "shown explicitly
with no fallback".

`W5CERT-DEF-1` blocks criterion 4's live step from a dispatched worktree and must be fixed
before the next session is asked to reproduce this. `W5CERT-DEF-2` is a latent vacuity risk
rather than a live failure. Neither was repaired here.

**I have not tagged, pushed or merged to `main`.** `main` remains at `6d3c0f3`. Whether it
advances to carry this re-certification is the owner's decision.
