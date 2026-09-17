# PC-01 — manual acceptance runbook

Executed from a clean clone by a reviewer who authored none of the slices. Every step names
what to observe, not merely what to run: a command that exits 0 while showing the wrong thing
is the failure this programme has caught ten times.

Roughly forty minutes, of which about ten is waiting on container images.

## Before you start

* Docker with Compose, Node 22, and CPython 3.12 on the host.
* **The working tree must not be under `/tmp`.** Docker here is a snap package that cannot
  see it, and `make up` fails with a `/var/lib/snapd/void/...` path error.
* A proxy token for the live step. Without it every step except 5 still runs; step 5 is then
  reported as not exercised rather than skipped silently.

## 1. Services and migration

```bash
cp .env.example .env          # give this instance unique ports, database and bucket
make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12
make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12     # twice, deliberately
git status --porcelain                                    # must be empty
make foundation
```

**Observe:** both bootstraps exit 0 and the second changes no tracked file; `make foundation`
exits 0 and prints three `FOUNDATION-CHECK OK` sentinels — services, database, storage.

**`check-db` is the only thing that holds the migration head**, and it is worth knowing that
before you rely on anything else. The acceptance suite's
`test_c2_the_application_is_serving_against_the_migrated_head` asserts that `listProjects`
answers 200 with a list — which it does against **any** head from `0002` onwards, measured.
`check-db` compares the head and exits 2 on a mismatch, naming both the current revision and
the expected one.
A sentinel is the evidence, not the exit code: a checker that exits 0 without printing one is
refused by the command surface on purpose.

**Observe the migration head is `0005_truncated_call_status`**, not merely "a head".
Measured at `e6eae1e` from `information_schema`: **16 `BASE TABLE`s** — fifteen domain tables plus
`alembic_version` — and **one `VIEW`**, `finding_current_verdict`. An earlier record said "17
tables" and §8 below said "sixteen"; both were counting, neither said what. Count the two kinds
separately or the number means nothing.
It was `0003_open_items` when PC-01 was first accepted; migrations `0004_cost_basis` and
`0005_truncated_call_status` landed in waves 2 and 3.

## 2. The application composes, or refuses to

```bash
set -a; . ./.env; . ./.env.provider; set +a
PYTHONPATH=src .venv/bin/python -m auditmanager.api.app
```

**Observe:** `wired, provider_mode=proxy` and `operations=12`.

> **From a dispatched worktree, `./.env.provider` is not there.** The credential is
> git-ignored, so it lives in the checkout the worktree was created from, not in the
> worktree. Source it from there instead:
>
> ```bash
> set -a; . ./.env; . "$(dirname "$(git rev-parse --git-common-dir)")/.env.provider"; set +a
> ```
>
> Step 5 needs no such help: `_provider_file` asks `git rev-parse --git-common-dir` itself
> and finds the credential from any linked worktree. `W6-CERT` was the first session to
> exercise that and it resolved correctly from `/root/w6cert`. This note covers only the
> manual step, which does not go through that code.

Now break it deliberately:

```bash
( unset DATABASE_URL; PYTHONPATH=src .venv/bin/python -m auditmanager.api.app ); echo $?
```

**Observe:** exit 2 and a sentence naming `DATABASE_URL`. This is the composition root's one
contract — a missing dependency fails at construction, not at the first request. A process
that starts can serve.

## 3. The journey, on the recorded adapter

```bash
env -u AUDITMANAGER_PROVIDER_MODE PYTHONPATH=src .venv/bin/pytest -q tests/e2e/pc01
```

**Observe:** 49 passed, 5 skipped. The five skips are the live steps and are the subject of
step 5.

This suite drives the **composed application** through its router — request in, response out
— rather than importing modules directly. That distinction is not stylistic: four defects
lived in the adapters between the modules and the router until something drove a request
through the front door, and every one answered 500.

## 4. The four stages and the explicit states

From the same session, through the router:

**Observe** in order: a project created, one upload answering 201 with `version_ordinal` 1
and `sha256` beginning `6d53674f`, a run answering 202 with state `published`, **four stages
`succeeded`**, and a `run_id` present in the body.

**Observe `provider_mode` on the run.** A recorded run reports `recorded`; a proxied or
direct one reports `live`. It cannot be set by the caller: a run declaring a mode its adapter
does not provide is refused before any stage writes.

## 5. The live run — the one that answers the product question

```bash
set -a; . ./.env; . ./.env.provider; set +a
C2_PC01_LIVE=1 PYTHONPATH=src .venv/bin/pytest -q tests/e2e/pc01/test_live_text_analysis.py
```

**Observe:** 5 passed, and in the run:

* **at least two of the three seeded issues found** — a fire-resistance contradiction across
  pages 2 and 6, an evacuation-exit contradiction across pages 3 and 7, and a literal
  `уточнить` placeholder on page 8;
* **every published quotation present on its declared page**, verified against the corpus's
  own extractor;
* **none of the six near-miss controls flagged** — a third fire-resistance value belonging to
  a separate gatehouse, a sentence carrying the stem of the placeholder word without being
  one, storey heights that differ legitimately, and the rest.

The second and third observations matter as much as the first. Finding the seeded issues
while also flagging the controls would be a model that says yes to everything, which is not
an audit tool.

**A run finding fewer than two is a result, not a broken gate.** It is the outcome
`PROTOTYPE_PROFILE.md` risk 1 names in advance, and it redirects P04 rather than stopping it.
Record what happened and move on.

**Observe the cost.** The per-run ceiling is USD 1.00 under `OD-03` and the proxy reports the
measured spend of each call. A corpus run costs a few cents: `W5-CERT` measured USD 0.038225,
`W6-CERT` USD 0.038125 and `W12-CERT` USD 0.0387, all against the USD 1.00 ceiling.

**Read the spend out of the database, not out of the test's print.** A run that had silently fallen
back to the recorded adapter would print a plausible number and leave no row: the evidence is
exactly one `model_call` with `provider_mode = 'live'` and `cost_basis = 'measured'`. At
`e6eae1e` that row also carries `cost_micros = 38700`, and the `text_analysis` stage's own
`metrics` carry `cost_basis` on the **success** path — before wave 11 that key appeared only on
the branch where the budget overran, so it answered on the run that failed and raised `KeyError`
on the run that succeeded.

## 6. Evidence, decisions and export

**Observe:** three findings listed for the run; opening one shows its exact quotation with the
page it came from; accepting one and rejecting another each answer 201; a later comment
appended to the accepted finding **leaves the verdict and the earlier events intact** — the
ledger is append-only and the database refuses an UPDATE with SQLSTATE `AM002`.

**Run the UPDATE and the DELETE yourself.** The acceptance suite's
`test_c6_the_decision_ledger_admits_no_update_or_delete` asserts that no `PUT`, `PATCH` or
`DELETE` route exists on `/findings/{finding_uid}/decisions` — a real property, and not the
one its name promises: it would pass unchanged against a table carrying no trigger. The
guarantee itself is held by `tests/integration/decisions/**`, which the gate runs. From a
`psql` session, `UPDATE expert_decision_event SET comment = 'tampered'` and
`DELETE FROM expert_decision_event` are each refused with **SQLSTATE `AM002`**, and the row
count is unchanged before and after.

**Observe the CSV:** 17 columns, one row per evidence item, UTF-8 with a byte-order mark,
CRLF. For this corpus: **5 rows**, and **4251 bytes on a run carrying no decisions**
— the byte count moves with the verdicts recorded, and is 4525 once an accept and a reject
are in the ledger, so compare the row and column counts first and the byte count only
against a run in the same decision state. Export twice and compare bytes — they must be
identical.

## 7. Restart

```bash
make down && make up && make check-services && make check-db && make check-storage
```

**Observe:** all exit 0, the migrated state and the published object survive, and the run,
its findings and its decisions are all still readable through the API.

## 8. Idempotency

**Observe:** repeating the upload and the run under the same idempotency keys creates no
second version, no second run, no second observation and no second decision. Row counts
across all fifteen domain tables are unchanged.

## 9. Explicit failures

**Observe** each of these answers with a typed code and creates nothing:

| Input | Refused by |
|---|---|
| `negative/not_a_pdf.txt` | PDF magic bytes |
| `negative/encrypted.pdf` | detected as encrypted, before any page is read |
| `negative/image_only.pdf` | no extractable text on a page; OCR is never substituted |
| `negative/too_many_pages.pdf` | 31 pages against the 30-page envelope |
| `negative/oversize.pdf` | 26 MiB against the 25 MiB envelope |
| provider unreachable | `dependency_unavailable`, **retryable**, with the run failing rather than publishing |

`W6-CERT` and `W12-CERT` each measured the five refusals rather than trusting the table,
because the acceptance suite still pins only the error-code class — and a three-way class at
that (`validation_failed`, `analysis_input_invalid`, `storage_integrity_error`) — and asserts
nothing about which rule refused. Measure `details.constraint` and check that you get **five
distinct values from five fixtures**; five refusals sharing one constraint would satisfy the
suite and would mean four of the five rules were not exercised. All five answer **HTTP 422
`validation_failed`** with a distinct `details.constraint`: `pdf_magic_bytes`,
`not_encrypted`, `every_page_has_extractable_text`, `1 <= page_count <= 30` and `max_bytes`.
The unreachable provider fails the run at `terminal_reason dependency_unavailable` after
three attempts over ~10.4 s on the pinned `(2.0, 8.0)` ladder, publishing nothing.

**Two failures in §8 criterion 10 cannot be induced through the twelve operations**, and this
is a known limit rather than an untested path:

* **a checksum mismatch** is proved at the storage layer, where a corrupt upload is refused
  and nothing canonical is written — the API offers no way to hand the store bytes that
  disagree with their own declared digest. Check that for yourself rather than taking it:
  expand every operation's request surface out of `contracts/api/v1/openapi.json`, following
  each `$ref` through `components`. At `e6eae1e` the twelve accept **thirteen distinct input
  names** in total and **none is digest-shaped**. Then try to inject one — an extra multipart
  part named `sha256`, or an extra `"sha256"` property on `startRun` — and observe **422
  `validation_failed`** with `details.constraint = additionalProperties`.

  **Since wave 11 the limit is narrower than it was, and it is worth seeing why.** The failure
  is still not *inducible*, but it is now *detected*. Replace a published object's bytes out of
  band with a body of the **same length**, copying its recorded metadata verbatim — the one
  case that used to slip through both checks — and then call the twelve again:
  `streamDocumentVersionContent` answers **422 `storage_integrity_error`**, while
  `getDocumentVersion` still answers 200 with the declared digest, because that is a
  declaration and not the bytes. `Reconciler.verify_version` gives the same verdict over the
  same row, with the **body's** digest as `actual_sha256`; an object recording no digest at all
  is `validation_failed`, not an integrity verdict, so an operator is never sent to restore a
  backup they do not need. Restore the bytes and the same call returns 200 again;
* **an ungrounded model item** is unreachable by design. The analysis stage resolves each
  quotation against the text layer and drops what does not resolve *before* the grounding
  gate sees it, so no `grounded = false` row is ever written. The owner accepted this on
  2026-09-11; the gate has been proved still load-bearing by mutation at every certification
  since, and the proof has two halves rather than one. Make nothing resolve: the run publishes
  **0** findings and `finding_observation` gains **no row at all**, so the drop happens before
  anything reaches the database. Then remove the drop as well, so evidence-free observations
  must reach the gate: the run **fails** with `terminal_reason analysis_input_invalid` and
  there are still **no** `grounded = false` rows. The second half is the one that matters — it
  shows the gate refuses the run rather than recording a diagnostic.

## 10. What this runbook does not establish

* **One version per document.** Every upload creates a new document, so `version_ordinal` is
  always 1 and no operation in the frozen twelve adds a version to an existing document.
  Version isolation is therefore proved between documents, not within one.
* **The intermediate run states.** Execution is synchronous inside `startRun`, so `queued`,
  `running` and `validating` are never observable from outside; criterion 4's six-state
  distinction reduces to `published` and `failed` through the API.
* **Professional usefulness.** The findings are grounded and the controls are clean. Whether
  a practising reviewer would have raised them is the question P04 asks, and nothing here
  answers it.

## 11. What this runbook does not reach, as of `e6eae1e`

Added by `W12-CERT`, because a reviewer following §1–§9 will believe they have exercised the
UI and they will not have.

**Every step above drives the API.** Criterion 4 in `PROTOTYPE_PROFILE.md` §8 asks for more
than that: *"while the UI distinguishes the contract run states … and the live or recorded
provider mode"*. At `e6eae1e`, **34 of the 110 modules under `web/src` — 1352 of 7604 lines —
are imported by no test**, and that set includes every screen this runbook's journey would be
driven through if it were driven through a browser: the run progress widget, the upload form,
the create-project form, the start-run control, the project list, the upload panel and the
project-detail page.

`widgets/run-progress/ui/run-progress.tsx` is the one to know about: it is the **only place in
the application where `terminal_reason` is rendered**, and `W12-WEB` showed that line can be
made to print a constant with all 440 frontend tests green.

What *is* guarded, and well, is the presentation mapping underneath it — `run-presentation.ts`
and `run-state.ts`, where the run-state vocabulary, the provider-mode narrowing and the
terminal and interrupted rules all redden under mutation. So the rules are held; the rendering
of them is not.

Reproduce the figure from `web/` with the import-closure script in
`docs/program/reviews/W12-WEB.md` §11; it prints `110 76 34`.
