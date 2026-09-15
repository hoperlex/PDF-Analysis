# `W6-CERT` — PC-01 re-certification after wave 6

**Verdict: PC-01 HOLDS at `c0d7daf`, with no exception that touches the ten criteria.**
All ten criteria of `PROTOTYPE_PROFILE.md` §8 were re-established and each was shown able to
fail. Both accepted criterion-10 limits were re-examined against the current tree and both
stand. Four defects are recorded and left unrepaired; none of them defeats a criterion.

Session `W6-CERT`. Authored none of wave 6. Repaired nothing.

---

## 0. Provisioning

`HEAD` on arrival, in the primary checkout `/root/projects/PDF-Analysis`:

```
04848450a84d0752d075e021a26fd7894558e4cf   (planning/prototype-roadmap)
```

This is base `c0d7dafab33a47e62050ba7c1c6916fae96ff98a` **plus one commit**, and
`git diff c0d7daf..HEAD --stat` touches only `docs/program/dispatch/W6-CERT.md` — this
brief being committed, which the brief itself names as harmless. So the base matched and no
re-checkout was needed. Work was done in a linked worktree `/root/w6cert` on branch
`agent/w6-cert`, created from `0484845`.

Instance `gate-w6`: `POSTGRES_PORT=55580`, `S3_API_PORT=59180`, `S3_CONSOLE_PORT=59181`,
`POSTGRES_DB=audit_w6`, bucket `auditmanager-gate-w6`. All three ports were confirmed free
before `make up`, and no `gate-w6` container existed. Nothing else ran in this wave.

## 1. Commands, with exit codes

| Command | Exit | What it showed |
|---|---|---|
| `git rev-parse HEAD` | 0 | `0484845` |
| `git fetch origin` | 0 | |
| `git worktree add /root/w6cert -b agent/w6-cert 0484845` | 0 | |
| `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` (1st) | 0 | `bootstrap OK` |
| `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` (2nd) | 0 | `bootstrap OK`, idempotent |
| `git status --porcelain` after both | 0 | empty — no tracked file changed |
| `make up` | 0 | three containers healthy |
| `psql ... "\dt"` on `audit_w6` before migrating | 0 | `Did not find any relations` — genuinely empty |
| `make foundation` | 0 | three `FOUNDATION-CHECK OK`, 35 passed |
| `alembic current` | 0 | `0005_truncated_call_status (head)`, 17 tables |
| `alembic downgrade -1`; `make check-db` | 0; **2** | `FOUNDATION-CHECK FAIL check-db` — criterion 2 red |
| `make migrate`; `make check-db` | 0; 0 | head restored, `FOUNDATION-CHECK OK` |
| `pytest -q tests --ignore=tests/contract --ignore=tests/checkpoint` | 0 | **803 passed, 5 skipped, 116 subtests** |
| `git diff --check` | 0 | |
| `python -m auditmanager.api.app` | 0 | `wired, provider_mode=proxy`, `operations=12` |
| same, `DATABASE_URL` unset | **2** | refusal naming `DATABASE_URL` |
| same, `S3_BUCKET` unset | **2** | refusal naming `S3_BUCKET` |
| `pytest -q tests/e2e/pc01` (recorded) | 0 | 49 passed, 5 skipped |
| `C2_PC01_LIVE=1 pytest -q tests/e2e/pc01/test_live_text_analysis.py` | 0 | **5 passed**, live |
| `make down` | 0 | |
| `make check-services` while down | **2** | `PostgreSQL refused an authenticated connection` |
| `make up`; `check-services`; `check-db`; `check-storage` | 0; 0; 0; 0 | three `FOUNDATION-CHECK OK` |
| `pytest -q tests ...` again, post-restart, populated DB | 0 | **803 passed, 5 skipped** |
| `alembic downgrade` 0004→0003 with a measured row | **1** | guard refused, by design |
| `alembic upgrade head`; measured row re-counted | 0 | head restored, measurement intact |

## 2. The wave-6 diff, checked rather than taken

`git diff beaa7f7..c0d7daf -- src/ db/` is **87 lines across four files**, exactly as the
brief's table claims. I read all of it. The table's four mappings are accurate.

## 3. The ten criteria

Each row states the evidence and **what would have made it fail**. Nine reds are real: a
downgraded schema, an unset variable, stopped containers, or a mutation applied to an
**isolated copy** of `src/` at `/root/w6cert-mut/src` (symlinked `contracts/`, `docs/`,
`fixtures/`, `tests/`), run with `pytest -o pythonpath=/root/w6cert-mut/src`. The copy was
proved to be the imported one by printing `auditmanager.__file__` in the same process as
the assertions — `/root/w6cert-mut/src/auditmanager/__init__.py`. **No tracked file was
edited at any point;** `git status --porcelain` is empty apart from my own owned documents.

| # | Criterion | Evidence (green) | Shown red by |
|---|---|---|---|
| 1 | services and start | `make up` 0; three `FOUNDATION-CHECK OK`; `wired, provider_mode=proxy`, `operations=12` | (a) `DATABASE_URL` unset → **exit 2** naming it; `S3_BUCKET` likewise; (b) `make check-services` with containers stopped → **exit 2**, no sentinel; (c) mutation M1: `settings._require` returning a placeholder instead of raising → `test_c1_a_misconfigured_dependency_fails_at_construction_not_at_first_use` **FAILED** |
| 2 | migrate an empty database | database verified empty (`Did not find any relations`), then migrated to `0005_truncated_call_status`, 17 tables | `alembic downgrade -1` → `make check-db` **exit 2**, `FOUNDATION-CHECK FAIL check-db: the database is at 0004_cost_basis, expected head 0005` |
| 3 | immutable version + private object | `version_ordinal` 1, `sha256` `6d53674f…`, 58978 bytes streamed back identical | mutation M3b: the version view reporting a digest one nibble off → **4 tests FAILED** across c3 and c8 |
| 4 | deterministic path + live `text_analysis` | live run **published**, `provider_mode=live`, four stages `succeeded`, degradation set empty | mutation M4b: removing the adapter-level mode refusal (`bootstrap/adapters.py:221`) → `test_c4_a_caller_cannot_talk_a_recorded_deployment_into_reporting_live` **FAILED** |
| 5 | seeded issues + quotation grounding | **3 of 3** seeded issues located; every published quotation verified present on its declared page against the corpus's own extractor | mutation M5: attributing each resolved anchor to the next page → published findings collapse **3 → 0**. The grounding is load-bearing: it destroys findings rather than publishing misattributed ones |
| 6 | evidence, decisions, append-only history | accept 201, reject 201, later comment 201 appending without altering the verdict | (a) direct `UPDATE` on `expert_decision_event` → **SQLSTATE `AM002`**, `DELETE` likewise; ledger intact at 51 rows; (b) mutation M6: `decision_history` returning only the newest event → `test_c6_a_later_comment_appends_without_overwriting_the_history` **FAILED** |
| 7 | CSV resolving to exact aggregates | 17 columns, 5 rows, UTF-8 BOM, CRLF, 4251 bytes on a run with no decisions; two exports byte-identical | mutation M7: dropping `latest_comment` from the frozen column set → `test_c7_the_export_is_utf8_with_the_frozen_column_set` **FAILED** |
| 8 | restart preserves canonical state | real `make down` / `make up`. Row counts **identical** across it: runs 72, observations 148, decision events 51, measured model calls 1; the live run still `published` and readable through a **fresh composition root**; export byte-identical; stored object streams back at `sha256 6d53674f…` | (a) `make check-services` exit 2 while down; (b) mutation M3b → `test_c8_a_freshly_composed_application_reports_the_same_canonical_state` **FAILED** |
| 9 | idempotency creates no duplicates | replaying createProject, uploadDocument, startRun and appendDecision under identical keys created nothing new | mutation M9b: making the caller's key unique per call → **4 of the 5 c9 tests FAILED** |
| 10 | explicit failures, no fake success | five negative fixtures each **HTTP 422** with a **distinct** `details.constraint` (below); unreachable provider fails explicitly | mutation M10c: widening the envelope (`MAX_PAGES` 30→1000) → `too_many_pages.pdf` accepted, `test_c10_unsupported_input_is_refused_with_a_typed_code` **FAILED** |

### 3.1 Criterion 10, measured rather than assumed

The acceptance suite asserts only that the error code is one of three; it does **not** pin
which rule refused. I recorded the actual answers directly through the router:

| fixture | status | code | field | constraint |
|---|---|---|---|---|
| `not_a_pdf.txt` | 422 | `validation_failed` | `content` | `pdf_magic_bytes` |
| `encrypted.pdf` | 422 | `validation_failed` | `content` | `not_encrypted` |
| `image_only.pdf` | 422 | `validation_failed` | `page_text` | `every_page_has_extractable_text` |
| `too_many_pages.pdf` | 422 | `validation_failed` | `page_count` | `1 <= page_count <= 30` |
| `oversize.pdf` | 422 | `validation_failed` | `file` | `max_bytes` |

Five distinct constraints, as the runbook describes.

**The unavailable provider, measured through the journey** (10.44 s wall clock, the pinned
`(2.0, 8.0)` ladder):

* run `state = failed`, `terminal_reason = dependency_unavailable`, `degradation_set = ['text_analysis']`
* `text_analysis` **failed** with `error_code = dependency_unavailable`, `retryable: true`
* the three deterministic stages still `succeeded`
* **0 findings published**
* persisted stage metrics: `attempts 3`, `attempt_budget 3`, **`attempt_budget_exhausted true`**, `retried_on_error_code dependency_unavailable`, `retry_waited_seconds 10.0`

**`cost_budget_exceeded` is reachable, and now reachable the way the contract says.** See §5.

### 3.2 Two mutations that did *not* bite, and why that is a result

Two of my first attempts left the criterion green. I chased both rather than recording a
red I had not earned.

* **`PDF_MAGIC` emptied** — criterion 10 stayed green. The parser refuses `not_a_pdf.txt`
  independently, so the magic-byte rule is not the only guard. Defence in depth, and a
  demonstration that the suite's error-code-class assertion would not notice that rule
  being removed.
* **`CommandStore.begin`'s pre-read forced to `None`** — criterion 9 stayed green. The
  `UNIQUE (command_type, idempotency_key)` constraint raises, and the `IntegrityError`
  handler re-finds the winner and answers from it. **The database constraint, not the
  pre-read, is where criterion 9's safety actually lives.** Only making the key itself
  unique per call defeated both layers.

## 4. The two accepted limits — re-examined, not inherited

### 4.1 `checksum_mismatch` — **STILL NOT INDUCIBLE** through the twelve operations

My verdict, established twice over:

* **Enumerated all twelve operations** from `contracts/api/v1/openapi.json` (count = 12,
  matching `operations=12` at startup). Of the four write operations, **none** accepts a
  digest-shaped field anywhere in its request body: `CreateProjectRequest`,
  `UploadDocumentRequest`, `StartRunRequest` and `AppendDecisionRequest` all declare
  `additionalProperties: false`, and the routers independently reject unknown keys
  (`set(payload) - {...}`). A caller cannot declare a digest at all, so it cannot declare a
  wrong one.
* **The guard is real**, so this is "unreachable from the API", not "unimplemented". Against
  the live store, with the **green half first** so the reds are not a store that refuses
  everything: the true digest and true size **publish**; a false digest raises
  `ChecksumMismatchError`; a real digest belonging to *different* bytes also raises
  `ChecksumMismatchError`; a false declared size raises `SizeMismatchError`.

### 4.2 `ungrounded_model_item` — **STILL UNREACHABLE BY DESIGN**

Re-established by mutation against the isolated copy, driving full journeys through the
composed application and reading the database afterwards.

* **Baseline**: 122 `finding_observation` rows in `audit_w6`, **all `grounded = true`**,
  zero `grounded = false`. A fresh journey published 3 findings and added **0**
  `grounded = false` rows.
* **Mutation A — nothing resolves.** Every quotation forced unresolvable. Published findings
  **3 → 0**; observation rows **125 → 125**, i.e. *no observation row was written at all*;
  **0** `grounded = false` rows. The drop-before-the-gate holds.
* **Mutation B — the drop removed as well**, so unresolvable quotations are carried forward
  as evidence and the gate must judge them. The run **failed** with
  `terminal_reason = analysis_input_invalid`, `text_analysis` **failed**, **0** findings
  published, and still **0** `grounded = false` rows.

So the gate is load-bearing — it fails the run rather than admitting ungrounded evidence —
and no `grounded = false` row is writable through the journey.

**A stale premise in my brief, and the second time it has been carried.** The brief says
"`stage.py` and `provenance.py` both moved, and the second limit is a claim about exactly
that code." Against the certified baseline `beaa7f7` **neither file moved at all** — wave 6
touched four files and neither is among them. Against the older `6d3c0f3` they did move,
but `_ground` — the drop the limit is actually about — is **byte-identical to `6d3c0f3`**,
and `findings/grounding.py` is unchanged. `W5-CERT` recorded this same correction about its
own brief; the premise was carried forward into mine unaltered.

## 5. The behaviour wave 6 changed, judged rather than accepted

`attempt_budget_exhausted` is the field wave 6 flipped, and `W2-QA` had pinned the defective
value as its expectation. So I did not take the new tests as evidence.

**`attempt_budget_exhausted` appears nowhere in `contracts/`.** It is an internal stage
metric, so there is no frozen document to appeal to and the question has to be argued.

I probed the property directly rather than reading the docstring:

| case | `budget_exhausted` |
|---|---|
| not attempted (0 of 3) | False |
| 1 of 3, succeeded | False |
| **3 of 3, succeeded on the last attempt** | **False** ← the wave-6 change |
| 3 of 3, failed on the last attempt | True |
| 2 of 3, failed on a non-retryable code | False |
| 3 of 3, last attempt `partial` | False |
| 1 of 1, failed | True |
| `RetryPolicy(attempt_budget=0)` | refused: `a stage gets at least one attempt` |

**My verdict: the new value is correct, and the argument is not the docstring's.** Under the
old definition the field was exactly `attempts >= attempt_budget` — a pure function of two
scalars **already persisted on the same row**. It therefore carried no information at all,
while actively poisoning any query counting exhausted budgets with runs that had published.
Under the new definition it encodes the last attempt's outcome, which is *not* recoverable
from the row: `retried_on_error_code` names the error that caused a retry, not the final
outcome. The new definition is the only one under which persisting the field is justified.
Wave 6 is right and `W2-QA` was wrong.

The one edge worth naming: with `attempt_budget == 1` any failure reports `true` although no
retry was ever available. It is unreachable in practice — the budget is pinned at
`ATTEMPT_BUDGET = 3` — and it is unchanged from the old behaviour, so it is an observation,
not a defect.

**The genuine-exhaustion case still reports `true`**, measured end to end through the journey
(§3.1). The change is narrow and did not cost the field its purpose.

### 5.1 `W5CERT-DEF-2` is genuinely fixed, proved behaviourally

The wave-6 test asserts that `app.settings` and `app.provider_config` agree at composition
time, and guards itself by asserting the process environment does not carry the ceiling.
That is well built, but it is an agreement check. The defect's original evidence was
behavioural — a run that **published** having spent 0.038775 under an injected ceiling of
0.01 — so I reproduced it behaviourally, with the green half first:

* `AUDITMANAGER_RUN_COST_CEILING_USD` **absent from the process environment**, so only the
  injected mapping could carry it;
* injected ceiling `1.00` → wired ceiling `1.0`, run **published**;
* injected ceiling `0.000001` → wired ceiling `1e-06`, run **failed**,
  `terminal_reason = cost_budget_exceeded`, **0 findings**.

The ceiling a caller sets is now the ceiling the run obeys.

### 5.2 Migration `0004`'s new `downgrade()` guard, shown both ways

* **Refuses** against `audit_w6`, which holds 1 measured row: exit 1,
  `refusing to drop model_call.cost_basis: 1 row(s) record a measured cost and dropping the
  column loses that permanently`, with the `HINT` intact. Head restored to `0005`; the
  measured row survived.
* **Allows** on a scratch database migrated to head with **0** measured rows: the downgrade
  `0004 → 0003` succeeded and `cost_basis` was actually dropped (column count 0).

So the guard is conditional, not a blanket refusal. The **upgrade** path is unaffected —
proved by migrating the scratch database from empty to head — so criterion 2 is unharmed,
which the brief asked me to verify rather than assume.

## 6. The live run

* **Credential resolution: the wave-6 fix WORKS, and I am the first to exercise it.** From
  `/root/w6cert` — a worktree directly under `/root/`, the exact layout that made `W5-CERT`
  *error* — with `C2_PC01_PROVIDER_ENV` unset and `.env.provider` never sourced, the suite
  printed `live provider configuration read from /root/projects/PDF-Analysis/.env.provider`.
  `_provider_file` resolved it through `git rev-parse --git-common-dir`. No credential was
  printed at any point in this session. **`W5CERT-DEF-1` is fixed.**

| | |
|---|---|
| model | `anthropic/claude-opus-5` (pinned by the suite, never read from the credential file) |
| provider | operated LLM proxy, mode **`proxy`** (`OD-02` revised 2026-09-14) |
| run id | `run_01M2JYF182K234A50AFEMMTT9E` |
| state | **published**, `provider_mode = live`, degradation set empty, four stages `succeeded` |
| **seeded issues found** | **3 of 3** — `SI-01`, `SI-02`, `SI-03` |
| **controls flagged** | **0 of 6** |
| quotation grounding | every published quotation verified present on its declared page |
| **measured spend** | **USD 0.038125** against the **USD 1.00** `OD-03` ceiling (3.8%) |
| cost basis | `measured`, 1 live call, 3895 input / 746 output tokens, 10490 ms |
| attempts | 1 |

Identical to the accepted record on both product numbers — **3 of 3 and 0 of 6** — and the
cost is within a whisker of the 0.038225 recorded at `beaa7f7`.

**The spend is verified, not assumed.** The database holds exactly one row with
`provider_mode = 'live'` and `cost_basis = 'measured'`, `cost_micros = 38125`. A run that had
silently fallen back to the recorded adapter would have left no such row.

**One caution on the controls number.** `test_live_the_near_miss_controls_are_reported`
asserts only `isinstance(flagged, list)` — deliberately, and its docstring says so, because a
flagged control is a precision result rather than a gate. So "0 of 6" rests on a printed
value, not an assertion. I confirmed it from the published evidence rather than taking the
print on trust.

## 7. Defects found, all left unrepaired

| id | owning tree | what |
|---|---|---|
| `W6CERT-DEF-1` | `tests/` | `tests/e2e/pc01/test_acceptance.py`, `test_c10_an_unavailable_provider_fails_the_run_explicitly`. Its docstring records "two observations": that the failed `text_analysis` stage carries `error_code: null` and that the run's `terminal_reason` is `analysis_failed`, concluding "The failure is explicit; what it was is not." **Both statements are now false.** Measured at `c0d7daf`: `error_code = dependency_unavailable`, `retryable: true`, and `terminal_reason = dependency_unavailable`. The behaviour was corrected in an earlier wave and the docstring was never updated. Because the test *records* rather than asserts these, nothing could catch the drift — the same shape of failure as `W2-QA` pinning the wrong value, in the opposite direction |
| `W6CERT-DEF-2` | `tests/` | The same test's export assertion, `assert ",live," in text or text.count("live") >= 1`, is satisfied by the substring `live` appearing anywhere in the CSV — inside a quotation, say. The first disjunct is the real check; the second can only weaken it and should not be there |
| `W6CERT-DEF-3` | `tests/` | `tests/contract/**` and `tests/checkpoint/**` cannot be run from a **linked git worktree**: they `copytree` the working tree and fail with `NotADirectoryError: /root/w6cert/.git`, because `.git` is a *file* in a linked worktree, not a directory. The same class as `W5CERT-DEF-1`. Scoped to CP-00 material and excluded from the PC-01 gate, so **no PC-01 criterion is affected** |
| `W6CERT-DEF-4` | `tests/` / provisioning | Neither provisioned interpreter can run those two directories in any case: the runtime `.venv` lacks `jsonschema` and the validation `.venv/bootstrap` lacks `pytest`. Again CP-00 material, outside PC-01 |

**No defect was found in `src/` or `db/`.** The four wave-6 changes are, in my judgement,
correct, and two of them repair real defects in ways I verified behaviourally rather than by
reading their tests.

## 8. Things in the brief that are false

1. **"`origin/main` is deliberately still at `6d3c0f3` — it has not moved."** False.
   `origin/main` is `8f418e9`, six commits on from `6d3c0f3`, and it already carries the
   `W5-CERT` certification (`ba0eccb`) and the owner's ruling that main advances to
   `1a3f5d9`. Harmless here — my `HEAD` was checked, not assumed, and the outer dispatch
   states the corrected position — but the brief's provisioning section reasons from a
   world that no longer exists.
2. **"Gate at that commit: 793 passed / 5 skipped / 116 subtests."** The gate at `c0d7daf`
   is **803 passed**, 5 skipped, 116 subtests. 793 is the figure measured at `beaa7f7` and
   recorded in `recertification-beaa7f7.json`; wave 6 added test files across eight paths,
   and the number was carried forward without being re-measured. The skip and subtest counts
   are right.
3. **"`stage.py` and `provenance.py` both moved."** False against `beaa7f7`; see §4.2. This
   is the third stale premise of the class this programme keeps recording, and the second
   time this particular one has been carried into a certification brief.
4. Minor: the runbook's step 2 instructs `. ./.env.provider`, which does not exist in a
   dispatched worktree — the credential lives in the main checkout. The *pytest* path now
   resolves it by asking git; the manual step does not. Corrected in the runbook, which I own.

The brief's diff table (87 lines, four files, and all four mappings) was accurate, as was the
$0.038 cost estimate and the `proxy`-not-`live` mode instruction.

## 9. What this does not establish

Unchanged from the accepted report and re-confirmed: one version per document is proved
between documents, not within one; the intermediate run states `queued`, `running` and
`validating` are not observable from outside because execution is synchronous inside
`startRun`; and professional usefulness is a P04 question that nothing here answers.

Newly named: the executor's own run/adapter provider-mode cross-check
(`runs/executor.py:566`) is **not** the guard criterion 4 exercises. Removing it leaves the
whole c4 suite green, because the refusal fires earlier, at `bootstrap/adapters.py:221`, and
answers `validation_failed` rather than the executor's `analysis_input_invalid`. The
executor's comment claiming "this is the only place that holds both the run row and the
adapter" overstates its role. It is defence in depth, not a defect — but it is not certified
by this journey, because nothing in the twelve operations reaches it.

## 10. Verdict

**PC-01 holds at `c0d7daf`.**

Ten criteria of `PROTOTYPE_PROFILE.md` §8, each demonstrated green and each demonstrated
able to fail. Both accepted criterion-10 limits re-established against the current tree
rather than inherited. A live run at USD 0.038125 against a USD 1.00 ceiling finding 3 of 3
seeded issues and flagging 0 of 6 controls — identical to the accepted record on both
product numbers. The two `W5-CERT` defects are both genuinely fixed, each verified
behaviourally rather than through the tests that claim them. The four defects I found are
all in `tests/`, all documentation or environment, and none defeats a criterion.

**No tag was created. Nothing was pushed. `main` was not touched.** Whether `main` advances
to carry this re-certification is the owner's decision.

Elapsed wall clock: approximately 40 minutes.
