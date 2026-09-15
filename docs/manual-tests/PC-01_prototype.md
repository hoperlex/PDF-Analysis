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
A sentinel is the evidence, not the exit code: a checker that exits 0 without printing one is
refused by the command surface on purpose.

**Observe the migration head is `0005_truncated_call_status`**, not merely "a head".
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
measured spend of each call. A corpus run costs a few cents: `W5-CERT` measured USD 0.038225
and `W6-CERT` USD 0.038125, both against the USD 1.00 ceiling.

## 6. Evidence, decisions and export

**Observe:** three findings listed for the run; opening one shows its exact quotation with the
page it came from; accepting one and rejecting another each answer 201; a later comment
appended to the accepted finding **leaves the verdict and the earlier events intact** — the
ledger is append-only and the database refuses an UPDATE with SQLSTATE `AM002`.

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
across all sixteen tables are unchanged.

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

`W6-CERT` measured the five refusals rather than trusting the table, because the acceptance
suite pins only the error-code class and not which rule refused. All five answer **HTTP 422
`validation_failed`** with a distinct `details.constraint`: `pdf_magic_bytes`,
`not_encrypted`, `every_page_has_extractable_text`, `1 <= page_count <= 30` and `max_bytes`.
The unreachable provider fails the run at `terminal_reason dependency_unavailable` after
three attempts over ~10.4 s on the pinned `(2.0, 8.0)` ladder, publishing nothing.

**Two failures in §8 criterion 10 cannot be induced through the twelve operations**, and this
is a known limit rather than an untested path:

* **a checksum mismatch** is proved at the storage layer, where a corrupt upload is refused
  and nothing canonical is written — the API offers no way to hand the store bytes that
  disagree with their own declared digest;
* **an ungrounded model item** is unreachable by design. The analysis stage resolves each
  quotation against the text layer and drops what does not resolve *before* the grounding
  gate sees it, so no `grounded = false` row is ever written. The owner accepted this on
  2026-09-11; the gate was proved still load-bearing by mutation.

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
