# Owner rulings, 2026-09-17

Recorded by the integrator the day they were given, against the tree at `431d753`. Four
answered by direct poll, three given in conversation before it.

`ALPHA_ROADMAP.md` is a **draft and a recommendation**; the ADRs and the architecture corpus
are the primary source of truth. That is itself one of the rulings below and it governs how
every other one is read.

## Given in conversation

| # | Ruling |
|---|---|
| **A** | **The ADRs are the primary source of truth.** A roadmap is a draft and a recommendation. |
| **B** | **FastAPI is core stack and its refusal was unjustified.** `ADR-0002`, `TECHNOLOGY_BASELINE.md`, `ARCHITECTURE_BIBLE.md` P-05 and `PROTOTYPE_PROFILE.md` §2 all name it. `api/README.md`'s "there is no HTTP framework, and that is deliberate" justified an absence from a lane-level pin set; corrected at `8805659`. |
| **C** | **The destination is a public application requiring HTTPS and authorization tokens**, not a single-operator localhost tool. |

## Answered by poll

| # | Question | Ruling |
|---|---|---|
| **R-1** | where it runs, and who reaches it | **The owner's own VPS host.** So TLS, DNS and hosting are in scope. |
| **R-2** | the FastAPI pin set | **Full set, with a licence named beside each pin.** §2 below is that diff, measured. |
| **R-3** | the contract reseal | **Tokens *and* the storage code.** `D-7`'s collision is settled at the reseal rather than left. |
| **R-4** | real client documents | **Permitted, wiped at the end of the pilot.** |

## 2. The R-2 pin set, measured rather than recalled

Licences read from each wheel's own `METADATA`, not from memory. Versions are today's latest;
the pin commit fixes them exactly.

**The addition is smaller than "a web framework" sounds**, because `anthropic` already pulled
FastAPI's and Starlette's cores into the closure.

| Distribution | Version | Licence | Status |
|---|---|---|---|
| `fastapi` | 0.141.1 | **MIT** | new |
| `starlette` | 1.6.0 | **BSD-3-Clause** | new |
| `uvicorn` | 0.53.0 | **BSD-3-Clause** | new |
| `click` | 8.5.0 | **BSD-3-Clause** | new — `uvicorn`'s only unmet requirement |
| `python-multipart` | 0.0.32 | **Apache-2.0** | new |

**Already satisfied by the existing closure**, so not additions: `pydantic` 2.13.5 (fastapi
needs ≥2.9.0), `typing_extensions` 4.16.0 (≥4.8.0), `anyio` 4.15.1 (starlette needs <5,≥3.6.2),
`h11` 0.16.0 (uvicorn needs ≥0.8).

**Five distributions. All permissive, none copyleft.**

### The test client is a sixth pin, and this needs the owner's eye

`starlette.testclient` does `import httpx`. **`httpx` is not importable in this venv** — what
is installed is `httpx2` 2.12.0, a *different distribution* providing a different module. So a
test client is not free:

| Option | Cost |
|---|---|
| pin `httpx` 0.28.1 (**BSD-3-Clause**) | one more distribution, plus `certifi` and `httpcore` if absent. Gives `TestClient` and `ASGITransport`, so the transport seam gets automated tests |
| drive the ASGI app directly over `anyio` | **zero new pins**, more test code, and the tests exercise the app rather than a client's view of it |

**Recommendation: pin `httpx`.** `D-5` is a 500 on the transport seam that only a socket
exposed, and the argument for pinning is that the seam gets automated coverage rather than
another manual harness outside the tree. But it is a sixth licence on a list the owner asked to
see, so it is named here rather than folded in.

## 3. What each ruling unblocks, and what it still needs

- **R-1** unblocks the deploy wave once the host details exist. **Still needed from the owner:**
  host name or address, who holds root, which ports may be opened, whether the provider proxy
  is reachable from it, and when access appears. **No secret belongs in a chat message** — the
  credential goes on that host's disk, by the owner, as `LIVE_RUN_INSTRUCTIONS.md` §2 already
  says for this repository.
- **R-2** unblocks the pin commit — a single-owner task under `FF-01` §2.8. The diff above is
  ready; the sixth-pin question is the only open part.
- **R-3** unblocks the reseal: a security scheme across all twelve operations, and a code for
  the storage refusal so one 403 stops meaning two things. `D-8` matters here — the catalog
  declares `"frozen": false, "status": "draft_candidate"`, so this is **an addition to a draft
  candidate, not a freeze-break**.
- **R-4** unblocks real-document sessions. **Still needed:** who uploads, and what event counts
  as "the end of the pilot" and therefore triggers the wipe. Nothing in this repository may hold
  such a document under any of the answers.

## 3.5 — `R-5` and `R-6`, ruled 2026-09-18 after the first live browser journey

### `R-5` — one reseal, carrying the list operations **and** cost visibility

**Ruled: do both in a single reseal.** Asked because `W15-RUN` drove a real browser through the
deployed stack and found that **after a page reload no screen can reach anything** — the twelve
operations have no `listDocuments`, no `listVersions`, no `listRuns`. Every row, object, run,
finding and decision survives in PostgreSQL and the store; the app can only see what the current
session created. `DEBT_REGISTER.md` **D-16**.

The owner was offered three shapes — both, lists only, or neither — and took **both**, on the
reasoning that a second reseal later costs more than carrying cost visibility now. So the same
reseal also closes **D-21**: `model_call.cost_micros` is recorded and appears on no operation, in
no CSV column and on no screen (`grep -c cost` over the frozen contract returns **1**, and that one
is `cost_budget_exceeded`).

**Why this is a ruling and not a lane decision.** The contract is the primary artefact below the
ADRs, and `R-3` set the precedent that a reseal is the owner's act. This one is larger than `R-3`:
it adds operations rather than a scheme and a code.

**What it unblocks.** `PA-01` criterion 8 — *"the server is rebooted and every canonical row,
object and decision survives"* — is currently **unverifiable through the browser**, because nothing
can display the survivors. Criterion 4's cost clause is unsatisfiable for the same reason. Both
become reachable with this reseal and neither can be reached without it.

**What it does not settle:** whether `execute_run` stops running inline (**D-20**), which is an
architecture question and not a contract one.

### `R-6` — reclaim the abandoned test stands

**Ruled: remove them.** Four wave-13 gate lanes (`gate-w13a/c/d/e`) held containers and volumes
whose worktrees were deleted waves ago. Removed 2026-09-18; the host went **8.4 GB → 11 GB free**.
The two alpha stacks on 31480 and 31490 and every active lane were left untouched.

Recorded because it is a destructive act on shared infrastructure, and because wave 14 lost time to
a full disk and `W15-RUN` and `W16-WEB` both flagged the same thing independently.

## 3.6 — `R-7` … `R-10`, ruled 2026-09-18 by direct poll

### `R-7` — `main` advances to the gated tip, not only to the certified one

**Ruled: fast-forward to `9291db6` and tag it.** Done: `alpha-w18`, 337 commits, from
`8f418e9`. The owner was offered the certified commit `e6eae1e` instead and took the tip.

**What the tag says, and what it deliberately does not.** It records the gate — 1778 / 5 /
168, foundation 35, frontend 595, exit 0 — and states in its own body that **this is a gated
tip and not a certification**. The last certification is `W12-CERT`'s at `e6eae1e`, whose one
named exception `D-1.5` closed on 2026-09-18, so that certification now holds without a
caveat. A certification *of this commit* is separate work and has not been done.

The tag also names what is open at it: no screen renders the three new list operations, so a
browser still cannot reach its own data after a reload; execution is inline so no `running`
state exists; and the deployed stack is wave 15's build until rebuilt.

### `R-8` — `D-18` gets a second code, not a wider key set

**Ruled: add a code to the catalog.** `BlobAttributeConflictError` (*stop — the instance was
restored wrong*) and `TemporaryBlobLostError` (*retry the upload*) currently produce
**byte-identical envelopes** differing only in `correlation_id`.

The owner was offered a widened `safe_detail_keys` instead and rejected it, and the reason is
in the option as put: **a detail key cannot fix `retryable`.** That flag is a property of the
code, it is correct for one of these two and arguably wrong for the other, and only a separate
code carries a separate value. Widening the keys would have left half the defect standing.

Precedent: `R-3` split exactly this shape with `dependency_credential_refused`. The catalog
declares `"frozen": false, "status": "draft_candidate"`, so this is an **addition to a draft
candidate, not a freeze-break** — `D-8`.

### `R-9` — the corpus waits for the screens and a manual pass

**Ruled: after the screens and manual testing, not in parallel and not as a pilot first.**

The re-measurement that prompted the question matters: `D-9` said the corpus's text and
geometry were unjoined and the content remote. **Both are false.** 674 documents, ~15 500
blocks, and in a random 25-document sample **1106 of 1106 blocks have a local
`crops/<block_id>.pdf`** yielding extractable text — no remote dependency. The real work is
**segmentation inside a block**, because a block is a region of several paragraphs.

The owner's reasoning, and it is the argument against my own instinct to start early:
**manual testing will say what granularity the norms actually need.** Segmenting before that
is segmenting blind, and 674 documents is an expensive thing to segment twice.

### `R-10` — `listProjects.document_count` is populated in the screens wave

**Ruled: populate it.** The field is already declared in the contract and simply unfilled, so
a project list reads `documents —`. The alternative was a screen calling `listDocuments` once
per project in a list.

It changes an existing operation's body and moves a seventh characterization record, which
`R-5` did not authorise — hence the question. This ruling authorises exactly that and nothing
wider.

## 3.7 — `R-11`, ruled 2026-09-19

### `R-11` — revert `R-8` rather than pay its unpriced cost now

**Ruled: revert.** `W20-CODE` carried out `R-8` in full — `staged_upload_lost`, 503,
`retryable: true`, proved over a real socket to make the two blob faults distinguishable where
they had been byte-identical apart from `correlation_id`.

**It did not land, and the reason is a cost `R-8` did not price.** A domain-catalog addition
forces one enum member into `contracts/api/v1/openapi.json`. No path, operation or schema
moved — the surface stayed 12 / 15 / 46 — but the contract's sha256 is recorded in
`web/FRONTEND_LOCK.json`, a hand-maintained file with no generator. **So a catalog addition is
also a frontend reseal**: regenerate the client, rewrite six digests, move two literals.

The session was blocked from that file twice over — its brief said *"No `web/`"*, and the
harness's permission classifier refused every write to it — and it stopped rather than work
around either. It offered the integrator the four mechanical steps; the integrator declined to
perform an action a delegated session had been refused, and put the choice here.

**The owner was offered three options and took the revert.** The alternative was authorising
the frontend reseal inside a wave that had not planned for one.

**What is kept:** everything in that wave that does not depend on the code — `D-23`'s guard,
the four stale counts it found (including the process entry point's own docstring), and
`D-1.6`'s erratum. **What is lost:** nothing measured. The evidence is in
`docs/program/reviews/W20-CODE.md` and reinstating it is `git cherry-pick b437616 271ba42`
plus the four steps in its §1.6.

**The general finding outlives the row**, and `D-18` now carries it: `R-3` and `R-5` both paid
this cost inside a wave that was already resealing the API contract, so it never showed. Any
future catalog change should be planned as a two-document change from the start.

## 3.8 — `R-12` … `R-15`, ruled 2026-09-21 by direct poll

### `R-12` — criterion 4 is satisfied; `partial` need not come from a user's journey

**Ruled: yes, the deployed path is enough.** `W24-CERT2` drove `partial` **in a browser** —
badge `queued → running → partial` at 2334 ms, `degradation_set ["text_analysis"]`,
`model_call.status = truncated` with 16 000 output tokens and no error code — against a stub
of the proxy's own documented contract on the stack's own network, with **nothing in the
application stubbed**.

The criterion asks that *the UI distinguish `running`, `published`, `partial` and `failed`*,
and it does. **`D-35` closes with no further work**, and the alternative — a second canonical
recording keyed by a second acceptance document — is **not** taken. That alternative would
have cost a new PDF, a corpus-builder change, `SHA256SUMS`, `expected_issues.json` and the
contract tests that enumerate them, for a lever no criterion asks for.

### `R-13` — restore `R-8`, and pay the frontend reseal

**Ruled: reinstate.** `R-8`'s code was built, proved over a real socket and reverted by
`R-11` when the cost appeared. The owner has now accepted that cost.

Two blob failures demanding **opposite** operator responses — *stop, the instance was restored
wrong* against *retry the upload* — still produce **byte-identical envelopes** apart from
`correlation_id`, and `retryable: false` is right for one and wrong for the other. A detail key
cannot fix `retryable`; only a separate code carries a separate value.

The work is `git cherry-pick b437616 271ba42` plus the four mechanical steps in
`docs/program/reviews/W20-CODE.md` §1.6, whose six digest values are already computed. **This
ruling authorises the `web/FRONTEND_LOCK.json` change those steps require** — the thing that
stopped `W20-CODE` twice over.

### `R-14` — `metrics["cost_basis"]` says `estimated` if any attempt was

**Ruled: the conservative rule.** `D-15` measured that `metrics["cost_usd"]` sums across retry
attempts while `metrics["cost_basis"]` describes only the last response, so a run whose first
attempt replayed and whose second reported a cost published a two-attempt sum wearing one
attempt's provenance.

The rule chosen is the one **`W18-SEAL` already applied to `RunStatus.cost_basis`**:
`measured` only when **every** contributing call reported a cost. The two places begin saying
the same thing, which is worth more than either wording alone. The alternative — dropping the
key — was rejected: it changes what an existing consumer reads.

### `R-15` — the wave after this one is debts and host readiness

**Ruled.** `D-38` and `D-39`, then everything that can be prepared **before** a VPS exists: a
TLS block that activates when a certificate appears, the deployment runbook, and the disk
headroom figure. The corpus (`D-9`) stays where `R-9` put it — after manual testing.

## 4. Still open, and still the owner's

- **`OD-18`** — three to five named experts with committed slots; `P4-BHV-01` waits on it alone.
- **`OD-17`** — the next corpus shape.
- **`R-4`'s two halves** — who uploads a real document, and what event counts as *"the end of the
  pilot"* and therefore triggers the wipe. **`D-17` now bears on this**: the restore is broken for
  writing, so the mechanism the wipe depends on is not yet sound.
- ~~`D-18`~~ **Settled by `R-13`**: reinstate, and pay the frontend reseal.
- ~~Whether `origin/main` advances.~~ **Settled by `R-7`**: `main` is at `9291db6`, tagged
  `alpha-w18`.
