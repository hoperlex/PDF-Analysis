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

## 3.9 — `R-16`, `R-17`, `R-18`, ruled 2026-09-21 in conversation

**These three were given to a different session than the one holding this file**, which drafted
them at `.local/handoff/R-16-DRAFT.md` (git-ignored, so invisible to anyone reading the tree)
and **deliberately did not land them**, on the grounds that this file has one owner per wave and
that owner was mid-wave. That was the right call and it is why they are here rather than lost.
Landed by the integrator 2026-09-21 at the close of wave 30. **The draft's measurements are
reproduced below with the commands that produced them; where a figure is quoted it is the
draft's, taken on the trees it names, not re-measured here.**

### `R-16` — the corpus is vectorised, both projections, norms first

**Ruled: option C, beginning with B, and not as one task.**

An index of similar cases over expert decisions (`ADR-0012`) and an index over the normative
corpus are **two different projections** answering two different questions — *"how did we decide
this before"* and *"what do the norms say"*. Both are built; the corpus is built first.

**Why the corpus first, and this is the part worth keeping.** An index over decisions is empty at
the start and only gets more expensive as verdicts accumulate. An index over norms is useful on
day one. And an expert's verdict citing a clause of a norm **produces a labelled case↔norm pair as
a by-product of the work** — so corpus-first does not merely pay off sooner, it manufactures the
labelling the decisions index later feeds on. The reverse order throws that source away.

The layout lands on four ADRs already taken and needs no new one: source PDFs and crops in
private S3 by `blob_id` (`ADR-0006`), chunk text and metadata in PostgreSQL (`ADR-0005`), vectors
in PostgreSQL via pgvector (`ADR-0005`), and the similar-case index as a **rebuildable projection,
never a source of truth** (`ADR-0012`).

**Anchoring is by page, not by fragment, and the reason is measured rather than chosen.** Across
all 28 249 corpus blocks, `coords_norm` is `[0,0,1,1]` for **28 249 of 28 249**, `polygon_points`
is `null` for every one, and there is **one block per page** across 28 251 pages. The
"crop region" *is* the whole page; there is no geometric layer in the corpus to anchor to.

*(Integrator's note on the arithmetic, because a later session will trip on it: 28 249 blocks
across 28 251 pages is not "exactly one per page" — **two pages carry no block at all**, and
they are a known corpus quality flag recorded in `.local/norms/corpus/MANIFEST.json`, in
`ГОСТ_Р_50030_2-2010`. The two figures agree once that is said. It changes nothing about the
ruling: page-level anchoring is forced by `coords_norm` being `[0,0,1,1]` for all 28 249, not
by the block-to-page ratio.)* So the
anchor is `document + page + offset in the recognised text`, and the expert is shown the whole
page crop. **Explicitly not to be done:** re-segmenting page images to recover paragraph geometry.
That is a separate recognition project, costs a multiple of everything else here, and neither
search nor suggestion needs it — only fragment highlighting would.

Measured scope, from parsing all 674 `results.md` on `f3cd244`: 74.6M characters, 455 907
paragraph candidates, **136 177 (29%) discarded** as running heads and offcuts, **319 730
substantive paragraphs** averaging 192 characters, of which 71 934 are numbered clauses;
**58 021 chunks** at ~1200 characters, **~15.6M tokens** to embed once, **0.11 GB** of vectors as
`halfvec` 1024 (0.33 GB as float32 1536), ~62 MB of text in the database, and 4.04 GB of crops
plus 712 MB of source PDFs in S3.

**Segmentation is a markdown parse, not an ML task** — the text in `results.md` already carries
the structure. ConsultantPlus running heads are noise and are discarded at segmentation,
confirmed by the owner. **That disposes of the noise, not of the rights question**, which `R-17`
takes up and does not close either.

### `R-17` — the corpus's provenance is a footnote in an appendix, with no per-document versions

**Ruled**, closing the point `R-16` left open.

Provenance is stated as a **text footnote in an appendix** naming the source and the date the
corpus was drawn from the ConsultantPlus base. **The footnote appears in the release version —
not in alpha and not in beta.** Individual documents are **not** pinned to versions and their
revisions are not qualified: the corpus is dated as a whole.

**The draw date is a window, not a day**, measured from the `Дата сохранения` field across all
674 documents: 395 on 23.07.2026, 256 on 24.07.2026, 6 on 20.08.2026, and **17 carrying no such
field at all**. So the correct footnote is *"as at 20.08.2026"* or the window
*"23.07–20.08.2026"*; **any single date is wrong for part of the corpus.** The same 17 documents
carry no ConsultantPlus marker in any form — among them `ГОСТ_379-2025`, `ГОСТ_6133-2026`,
`ГОСТ_Р_72509-2026`, `ПЭУ_7_Изд`, `СП_112.13330.2011` — so a blanket *"source: ConsultantPlus"*
is inaccurate for them. Whether to qualify the footnote or check those seventeen is a question
for the moment the appendix is written, not for now.

**One consequence the integrator records as following from the ruling rather than arguing against
it.** Dropping per-document versions is accepted and it simplifies the work. But it makes the
**snapshot date the only anchor of provenance**, and it therefore has to live as a **field in the
data** — a corpus-snapshot identifier on chunk rows — not only as prose in an appendix. Expert
verdicts will cite clauses of norms; when the corpus is refreshed, GOSTs are superseded and SPs
reissued, and if the snapshot is not recorded as data **nobody will be able to say which revision
a past decision was taken against.** The accumulated verdict register would lose its
interpretability at exactly the moment the corpus is first updated. This is `ADR-0010`'s existing
move — durable identity lives in the data, the displayed thing is presentation only — and one
snapshot field per corpus, rather than a version per document, sits inside the owner's ruling and
costs almost nothing.

**Scope of the footnote.** It settles **attribution**: it names a source and a date. The question
of **rights to use a particular edition is a separate question and the footnote does not close
it.** The owner is aware; the decision is recorded in this form as taken.

Check: `grep -c "Дата сохранения" .local/norms/corpus/*/results.md`.

### `R-18` — the alpha is shown in a finished design, in Russian

**Ruled. This amends `ALPHA_ROADMAP.md` §1**, where interface presentation was explicitly out of
scope for the alpha.

**The alpha must have a fully finished interface. Manual testing happens on something close to the
release version. A stripped skeleton with layout artefacts is not the state in which the system is
shown to an expert.** The owner's qualification: **some sections and routes may be closed off with
stubs. The priority is the Russian version with the final design, not completeness of function
behind every door.** The rule, in one line: **breadth of finish beats depth of function.**

**Why this is not a matter of taste.** `ALPHA_ROADMAP.md` §10 risk 3 already names the interface
as the least-tested surface, and `P4` exists to establish the **professional usefulness of the
findings**. An expert shown a prototype skeleton will report on interface friction rather than on
finding quality — the measurement is spoiled in precisely the variable it was run for. `PC-01`
recorded that the usefulness question is **not established** by it.

**The scope, measured on `ca16a18` rather than estimated:** **zero** styling or UI packages among
thirteen dependencies; **one** CSS file in the whole application, `src/app/globals.css`, with
**35 rules**; **zero** `*.module.css` collocated modules, though that file's own comment promises
them; 42 `.tsx` and 94 `.ts` modules; **64** distinguishable user-visible strings; **zero** UI
source files containing Cyrillic; **no localisation mechanism at all**; and
`<html lang="en">` at `src/app/layout.tsx:20`.

**What those numbers mean.** The application's entire visual layer is thirty-five CSS rules. The
styling architecture is described in a comment — a slice with its own collocated module consuming
tokens — and **is not built**: there are zero such modules. And Russian localisation is not a
translator's pass: there is no Cyrillic in the UI sources at all, no localisation mechanism, and
the document declares itself English. **This is introducing a mechanism that does not exist, not
editing strings.**

Check: `find web/src -name '*.module.css' | wc -l`,
`grep -rl '[а-яА-Я]' web/src --include=*.tsx --include=*.ts | wc -l`,
`grep -n 'lang=' web/src/app/layout.tsx`.

**The stub boundary, proposed by the drafting session and adopted here, because "stubs are
allowed" without a criterion is a way of doing nothing:** a stub is permitted where an expert's
task does not pass through it. **On the path `upload → run → finding at its quotation → verdict →
export` there are no stubs.** A stub looks like a finished section carrying an honest line about
unavailability — not an empty screen and not an error.

**Defects a manual test must not be allowed to meet**, taken from the deployed stand on
2026-09-21 and kept at `.local/handoff/ui-screenshots/`: mixed language (finding content in
Russian, labels in English — `Review`, `Decision`, `Export`, `Append a comment`,
`No decisions yet`); identifiers such as `prj_01M2WW60H9BH688V7X54VVESYW` set in body text beside
content; layout collisions on the review screen, where the `page 2`/`page 6` tabs overlap the word
`recorded` and `Append a comment` covers its own input; the seventeen CSV columns printed to the
user as a list, which is documentation standing where an interface should be; an unreadable page
thumbnail; and the footer *"Local prototype. One reviewer, no authentication, no tenancy"* on
every page.

**What `R-18` does to the plan.**

- **`ALPHA_ROADMAP.md` §1 needs amending** — presentation moves from *"not on this road"* to a
  condition of accepting the alpha. No ADR conflicts: none prescribed an unfinished interface, and
  `ADR-0009` fixes only the stack. The roadmap is a draft and loses to an ADR, but here there is
  nothing to lose to.
- **`R-15` is neither cancelled nor in conflict.** Debts and host readiness live in `infra/`; the
  design line lives in `web/src`. The trees do not intersect and the lanes can run in parallel.
- **`web/src` gets one owner per wave** (`AGENTS.md` §3), and the wave will be large.
- **A frontend reseal is likely.** `R-13` has just paid one; a design wave touches
  `web/FRONTEND_LOCK.json`, and that is to be planned from the start rather than discovered at
  the end.
- **This is not one wave.** Introducing localisation, building the styling layer, and finishing
  six screens are different pieces of work with different evidence.

**What `R-18` does not mean.** `ALPHA_ROADMAP.md` §1's exclusions stand: multi-tenancy, roles,
user management, retention, legal hold, HA, DR, backup rotation, the job/attempt framework, remote
workers and OCR remain out of scope. The requirement is about **the finish and the language of
what is shown**, not about widening function.

## 3.10 — `R-19` … `R-22`, ruled 2026-09-22 by direct poll, on `D-59`

### `R-19` — the leaked model reasoning is repaired at the source: re-recognise

**Ruled.** Not classified, not filtered — **re-recognised.**

**Scope reconciled from two answers that differ.** Asked where the marker should live, the owner
chose *"re-recognise the 34 documents"*; asked what an expert should see for the 55 pages with no
norm text, they chose *"re-recognise only these 79 pages"*. **The narrower answer is the one
carried out**, because it is a strict subset and it is the later, more specific of the two: the
unit of failure is the page, and 28 170 of the 28 249 pages in those documents are fine. If the
owner meant every page of all 34 documents, that is a superset and they can say so.

**What made classification the wrong answer, and it is measured:** the pipeline marked **every
one of the 79 blocks `recognized`**. The corpus's own vocabulary has no state for *"the model
looped and emitted its plan"*, so there is nothing to filter on but the text itself — and the
text is what is wrong. Repairing the source removes the question instead of encoding it.

### `R-20` — the 24 mixed blocks stay, marked

**Ruled.** Where Russian normative text and English reasoning share one block, **nothing is cut**
and the chunk carries a mark. The owner accepted the stated cost: the reasoning enters the
vector and influences retrieval even where no screen shows it. `R-19` reduces this to whatever
re-recognition does not fix.

### `R-21` — the corpus is embedded first, the 79 pages repaired after

**Ruled**, with an instruction attached: **price the token volume against the limits before
committing**, and move the work to an external tool if it is too expensive. §1 below is that
pricing.

The contaminated text is **2.1% of the corpus by characters** — 1.55M of 74.6M — so a single
pass embeds about **0.5M tokens of model output as though it were a norm**. The owner judged
that acceptable against the delay of blocking the whole corpus on 79 pages.

### `R-22` — measured before spending: the volume, the limits, and who charges for it

**The single most consequential fact, verified rather than assumed: Anthropic does not offer an
embedding model.** Its own documentation says so and points at Voyage AI. **So the embedding job
was never an Anthropic-API cost** — it is an external provider either way, which settles the
owner's question about moving it to an external tool: it is already there.

| | |
|---|---|
| corpus | **74 642 798 characters**, 63.1% Cyrillic, 6.4% Latin |
| tokens, one pass | **18.7M–29.9M** at 3.99–2.5 chars/token; **~25M** at the likely Cyrillic rate |
| `R-16`'s estimate | ~15.6M — **too low**, because 3.99 chars/token is a *Latin* ratio (`D-60`) |
| contamination | 1.55M characters ≈ **0.5M tokens, 2.1%** |
| dimensions | `voyage-4` defaults to **1024** — exactly what `R-16` assumed, so its 0.11 GB vector figure stands |

**The limit that actually bites is context, not cost.** `voyage-4`'s input context is **32 000
tokens**, and the longest chunk in the corpus is the 62 359-character paragraph of `D-59` —
**21–25 thousand tokens. It fits, and barely.** `D-60`'s long-tail question (3 666 chunks over
1200 characters) is therefore not academic: a chunker that merged two such paragraphs would
exceed the limit and the request would be refused, not truncated.

**Re-recognising the 79 pages is cheap and the estimate is robust to its own uncertainty.**
At 1 500–3 000 input tokens per page image and ~2 516 characters of output per page, it is
**$2.58–$3.17 on Claude Opus 5** ($5/$25 per MTok). Wrong by 3× it is still under $10. **Cost is
not a reason to defer `R-19`.**

*(The token figures above are arithmetic over measured character counts, not a tokeniser
reading: no tokeniser is installed in this tree and no API credential is available to this
session, and `tiktoken` is explicitly wrong for both Claude and Voyage. **The first act of the
embedding stream is to count with the real tokeniser before spending** — `D-60`.)*

## 3.11 — `R-23` … `R-25`, ruled 2026-09-22 on the six legacy screens

**Given to `pdf-analysis-79` and drafted at `.local/handoff/R-23-DRAFT.md`; landed here by the
integrator.** The mechanism that carried them is the one `owner-rulings-arrive-via-peer-sessions`
describes: a ruling reaches whichever session the owner is talking to, and `.local/` is invisible
to git.

### `R-23` — the six screens, sorted

| screen | ruled |
|---|---|
| **knowledge base** | **required, and must work inside the alpha** |
| **stage comparison** | very important; a stub skeleton now, the real thing during the alpha |
| **dashboard** | wanted on the front end even partly working — an important visual instrument |
| **dispatcher** | wanted, with the work on rights, users, actions and a personal account |
| **queue** | waits for a full vertical |
| **work schedule** | important, deferrable to later alpha releases |

**`R-23`'s same-day addendum — four more screens, and the rule they made general.** Ruled the
same day and landed 2026-09-23, on **blocks, optimisation, logs and workers**: all four are
wanted, each is wired up as its vertical lands, and **the front-end preparation may be done
now.** Out of that and the six above the owner's drafting session extracted a rule worth stating
once instead of per screen:

> **The front end carries the structure before the back end does, with honest stubs.**
> A section that does not exist yet looks like a finished section saying it is unavailable —
> not missing, and not pretending to work.

This is `R-18` (*breadth of finish over depth of function*) applied to the whole of navigation,
and it has already run on the fourteen project sections: thirteen stubs, one working, and the
screen saying plainly that sections are navigation.

**Preparation means four things, none of which touches the contract:** a place in the navigation;
a `RoutePlaceholder` carrying a `promise` — what will be here, not *"not implemented"*; the data
shape written down and checked against the contract, so a future reseal is seen now rather than
at the end of a wave; and **no invented numbers** — an empty screen is more honest than a
plausible one.

**And what preparation does not buy, stated plainly because a stub reads like progress:** none
of the four verticals moves.

> **Corrected 2026-09-24 by `W43-PREP`, which was told to verify these four rather than copy
> them and found three of them wrong. The gloss was the integrator's, not the owner's; the
> ruling itself is untouched.**
>
> - **Blocks — the original sentence was materially false.** It said *"no block geometry in the
>   data… no vector graph to draw"*, inferring the application from the corpus. The corpus half
>   is right and was re-measured over all 674 `blocks.json`: `coords_norm` is `[0,0,1,1]` on all
>   **28 249** blocks and `polygon_points` is **`null`, not empty**. But **this application
>   produces real geometry** — `analysis/stages/page_geometry_extraction.py:226` writes a
>   `bbox {x0,y0,x1,y1}` in points, top-left origin, one per text line, with `bbox_unit` and
>   `bbox_origin` beside it. What is missing is **an operation that returns it**: the only
>   block-shaped field on the surface is `Evidence.block_id`, which the contract itself calls
>   *"Not a contract identifier"*. **So blocks is a reseal, not an impossibility.**
> - **Optimisation** — right in substance. Four stages are scheduled and visible in
>   `RunStatus.stages`; exactly **one** (`text_analysis`) is an analysis stage, out of nine
>   canonical ids. Legacy's seventeen are *stage directories observed*, not a declared pipeline.
>   `StartRunRequest` has two properties under `additionalProperties: false`, so **nothing is
>   settable**: a read-only view is buildable today, anything settable is a **reseal**.
> - **Logs** — *"exist on the server"* needed qualifying. **The `audit_event` table is never
>   written by `src/`; its only writers in this repository are tests.** What exists is
>   `stage_result`, `model_call`, `contract_state_transition`, `command_record` and stdout. Still
>   **a reseal**, plus a decision on what is safe to publish.
> - **Workers — `deferred`, not `excluded`, and the word matters.** `PROTOTYPE_PROFILE.md` §7.2
>   lists *"remote/distributed workers"* under **Deferred**. Nobody ruled against them, so a
>   screen promising them promises something nobody has decided either way — which is why that
>   screen carries **no promise** at all. **No reseal: it is blocked by a decision not taken.**
>
> **Three reseals are now on paper rather than discovered at the end of the wave that tries to
> build them**, which is what `P3` was for and what `R-11` cost a whole wave.

### `R-24` — the knowledge base gets a listing operation in the contract

**Ruled against the drafting session's recommendation, and the owner took the expensive option
deliberately.** A client-side walk over the decision journal is cheaper and lives only as long as
the alpha; a listing operation costs a reseal and outlives it.

**So a second contract reseal is due after wave 34's**, and the integrator's note is that it
should be **batched**: `D-56`'s per-section verdict aggregation and `D-63`'s dashboard counts are
both reseals nobody has taken, and `R-11` reverted an entire wave once over a reseal discovered
at the end rather than planned at the start.

### `R-25` — the dashboard counts what exists, and shows the rest without numbers

Real numbers for projects, runs and verdicts; **the section structure rendered without counts**,
because the data has no section field — `Project` is `{project_uid, name, created_at,
document_count}` and `D-56` measured that there is none anywhere.

**And the thirteen sections are ordered by how textual they are — ПОС, ТХ, ПБ first.** The
reason is measured rather than aesthetic: the AR vertical is **5 148 lines plus a
content-hashed prompt bundle plus 16 fixtures**, and the sections whose answers live in
*drawings* cannot reuse any of it. Ordering by textuality puts the sections that can reuse the
existing vertical first.

**The dashboard itself stays deferred by the owner's separate instruction the same day** —
*"важно, но не в этой волне"* — and is `D-63`.

## 3.12 — `R-26` … `R-29`, ruled 2026-09-23 by direct poll

### `R-26` — all four account guards land in the alpha

**Ruled: rate limit, lockout, password change AND revocation, all inside the alpha.** The
integrator had recommended revocation alone; the owner took the wider option.

The argument for revocation stands and is now the argument for finishing the set on the same
pass: the other three make an account weak **now** and are fixed by adding them later;
revocation makes an **already issued** credential permanent, and no later work reaches
backwards to a token in someone's browser. With `R-4` putting real client documents on the
pilot server, *"the pilot has ended"* is a claim the system cannot currently make true.

**This is roughly two waves.** Revocation and password change need contract operations, a
migration, and a revocation check on every authenticated request; rate limit and lockout are
state around the token endpoint. `D-65` carries the measurement.

### `R-27` — the corpus re-recognition uses the stand's own provider key

**Ruled.** `infra/deploy/env/provider.env` is on the host and already pays for live runs. The
integrator had declined to spend it without a word, because re-recognising 79 pages is not
pilot work; the owner authorised it.

Priced at **$2.58–$3.17** for 79 page crops, which is inside the $5-per-wave ceiling `R-29`
sets. **The key is read from that file and never printed** — not into a log, not into a report,
not into a commit. `D-42` measured that `docker compose config` prints it in clear, so the same
care applies.

### `R-28` — `R-1`'s host is not here yet, and may be here today

**Ruled: plan without it.** With one qualification the owner added and it changes sequencing:
**the host is expected later today, so a plan whose horizon runs past about six hours may
assume it.**

So `PA-01` criteria 1 and 2 stay `cannot be established` in the near waves and a **later** wave
may be written against a real machine. `W26-HOST` already prepared everything that can exist
without one — the TLS block inert until a certificate appears, and the runbook — so what
remains when the machine arrives is configuration, not authorship.

### `R-29` — autonomy: everything except security decisions and spending

**Ruled.** The integrator runs waves without asking: contract reseals, migrations, screens,
guards, advancing `origin/main`, tagging. **It stops at two things:**

1. **spending above roughly $5 in a wave**, and
2. **anything that changes who can reach the system, or exposes something that was not
   exposed** — a port binding, a credential's reach, a default account, a published surface.

**One distinction the integrator records rather than assumes.** `R-26` is a security *ruling*,
and building what it rules is **execution, not a new decision** — so wave 39 does not stop to
ask again. What would stop it is a choice the ruling did not make: if revocation turns out to
need the stand published, or a default changed, that is a new exposure and it comes back here.

## 4. Still open, and still the owner's

- **`OD-18`** — three to five named experts with committed slots; `P4-BHV-01` waits on it alone.
- **`OD-17`** — the next corpus shape. **`R-16` and `R-17` bear on this but do not close it**:
  they settle how the *normative* corpus is vectorised, dated and attributed, not what the next
  evidence corpus should be.
- **`D-9`, the norms corpus** — `R-9` placed it after the owner's own manual pass, and that
  pass has not happened. The stand is current, Russian, and reachable over a tunnel, so nothing
  on this side is in the way. **This is the only open row waiting on the owner doing something
  rather than deciding something.**
- **`R-4`'s two halves** — who uploads a real document, and what event counts as *"the end of the
  pilot"* and therefore triggers the wipe. **`D-17` now bears on this**: the restore is broken for
  writing, so the mechanism the wipe depends on is not yet sound.
- ~~`D-18`~~ **Settled by `R-13`**: reinstate, and pay the frontend reseal.
- ~~Whether `origin/main` advances.~~ **Settled by `R-7`.** `main` is at `f96c23a`, tagged
  `alpha-w30`, as of 2026-09-21. (This line said `9291db6`/`alpha-w18` for twelve waves while
  `main` advanced three times beneath it — once, to `7535a17`, without a tag at all.)
- **`R-18`'s stub boundary** — the rule *"no stubs on `upload → run → finding → verdict →
  export`"* was proposed by the drafting session and adopted by the integrator. **It has not been
  put to the owner in those words.** If the owner wants a different line, this is the sentence to
  change.

## 3.13 — `R-30` … `R-37`, ruled 2026-09-23 by direct poll after wave 41

**Asked because wave 41's own repairs produced two of them**, and because the owner said to
resolve by poll whatever a poll can resolve and to name explicitly, in the next report, what it
cannot.

### `R-30` — the stand runs in `recorded` mode until a provider key arrives

`D-72`'s repair made a host-less proxy URL a **startup** refusal, and the stand's certification
stub is exactly that, so wave 41's redeploy took the API down (`D-70`). The owner chose
`recorded` over the two cheaper restorations.

**It is the better answer and the reason is not cost.** A hostname on the stub would have
restored the interface and left every run failing; `recorded` replays real recorded responses,
so **the whole journey is drivable without a key** — upload, run, findings, a verdict, the CSV.
A document with no recording says so, which is `D-46`'s open question and not a lie.

Applied the same hour. The effective setting is **`infra/deploy/env/alpha.env:15`**, not
`provider.env` — compose's `environment:` overrides the service's `env_file:`, and the first
attempt edited the file that loses. Verified: `/api/v1/openapi.json` **200**,
`verify-deployed.sh` reports the deployed stack IS the tree.

### `R-31` — the four documentation routes close behind a credential

`/openapi.json`, `/docs`, `/redoc`, `/docs/oauth2-redirect` answered `200` with no credential
while every real operation answered `401` — the doors locked and the blueprint on the doorstep.
`D-73` closes: the authorization dependency moves from the router to the application.

**Ruled over "leave them open", which the tunnel would have justified.** The owner took the
narrower reading.

### `R-32` — the published account stays; the tunnel is the boundary

`D-75` — one account, its login printed in programme documents, and a lockout an
unauthenticated caller could aim at it — is **accepted as a risk, not repaired**, because the
stand is bound to `127.0.0.1` and reachable only through the owner's SSH tunnel. Without the
tunnel the sign-in form cannot be reached at all; with it, the caller is the owner.

**Reopens the moment there is a host with a public name**, which is `R-1`. The row stays in the
register carrying this reasoning rather than being closed.

### `R-33` — every border rises to 3:1, not only the load-bearing ones

`D-81`: `--am-line` on `--am-paper` measures **1.36:1** light and **1.30:1** dark against WCAG
1.4.11's 3:1, and it is the only boundary under every finding row. The owner chose the
product-wide change over the targeted one — the option `W32-CONTRAST` §3 and `W33-THEME` had
each declined.

**So the visual change is intended, not a side effect**, and the wave implementing it does not
need to protect the old look.

### `R-34` — `R-19` widens to all 96 blocks of that nature

The extra **17** are the same defect spelled differently — the model narrating a page with no
first-person pronoun, which `D-59`'s grep could not see — and they include the corpus's
**second, third and fourth largest** degenerate blocks at 50 989, 38 436 and 37 199 characters.

### `R-35` — the 25 JSON-envelope blocks are re-recognised with the rest

A different defect nobody had ruled on: the pipeline's own `[{"text": …` envelope written into
the document body, 20 documents, 94 821 characters.

**Recorded with the trade the owner accepted, because it is the integrator's job to say it
once.** These 25 have a strict machine-made shape and a parser could unwrap them for nothing,
deterministically and checkably; re-recognition pays a model to redo what a parser can do and
substitutes a probabilistic result for a deterministic one. The owner chose one pass over all
121 for operational simplicity. **The price is measured before anything is spent and `R-29`'s
$5 ceiling still stops the wave** — and none of it can run at all until `D-70` clears, because
re-recognition needs a provider and the stand has none.

### `R-36` — the run cost ceiling is decided after the first live run

It is **1.00 USD** by default today and an empty value does not disable it; measured runs are
**0.1147** synthetic and **0.018305** live. The owner declined to tune a number against no
measurement of a real 30-page document. **Nothing changes**, and the first live run answers it
for free.

### `R-37` — a decision shows a display name, not a login

Wave 41 made `author_label` the authenticated reviewer's **login** (`D-78`), which reaches every
other reviewer through `listDecisionHistory`, `listDecisions` and two screens. The owner ruled
for a **display name** instead.

**This is a migration plus a contract reseal**, and it therefore joins the batch already forming:
`D-46`'s `terminal_detail` and `D-86`'s now-false description of this very field. One reseal,
one owner, per `R-24`'s note and `R-11`'s cost.

## 3.14 — `R-38` and `R-39`, ruled 2026-09-24

### `R-38` — wave 45 runs entirely on Sonnet and closes today

Wave 44's two cross-judges both terminated on the **Opus weekly limit**, which resets
2026-09-26 23:00. Their work had already reached the tree, so wave 44 closed intact — but wave
45 in the same shape (two streams and three judges on Opus) cannot run before then.

**The owner chose speed over model quality, deliberately and with the cost stated.** The cost is
specific and worth writing down rather than implying: wave 44's cross-judges found **five false
greens inside the integrator's own repairs**, including a credential guard that still admitted a
fallback written on the next line, and a capability guard that caught one wording rather than the
claim. **Judging is exactly where model quality shows, because a judge that finds nothing is
indistinguishable from a judge with nothing to find.**

**So the structure does not relax.** Streams, a judge closing each sub-stage, and two judges
cross-judging before the final testing — all of it stands; only the model changes. Every judge
brief says what to measure and how, rather than asking for an opinion, and the falsifications are
fixed in advance so a judge that skips one is visible.

### `R-39` — a screen may explain why it is empty, in the language of the subject

`D-91`: three prepared screens tell a reviewer *why* they are empty — *«не отдаёт ни одна
операция договора»* — while the comparison screen refuses to and carries a test enforcing the
refusal. Two streams drew `R-18`'s line in different places inside one wave, and both argued it.

**Ruled: a screen may say what the system cannot do yet, in the words of the subject.** An expert
is better served by a reason than by *«раздел недоступен»*.

**The prohibition that stays** is the one `D-58` closed by deletion and `R-18` is actually about:
**no operation ids, no field names, no transport.** *«Эта проверка пока не делается»* is for a
reviewer; *«операция `listRuns` не отдаёт X»* is for an author and belongs in a comment.

**Consequence for wave 45, which is why this was asked now:** `W45-POS` builds a vertical that
**cannot be shown to work until `D-70` clears**, so whatever it puts on screen will be saying why
for some time. It may now say it plainly.

## 3.15 — `R-40` … `R-43`, ruled 2026-09-25 by direct poll

**Given to `pdf-analysis-d6` and drafted at `.local/handoff/R-30-DRAFT.md`; landed here by the
integrator.** The draft numbered them `R-30.1`–`R-30.4`; **`R-30` is taken** — it is the ruling
that put the stand in `recorded` mode two days earlier, which is why the alpha is drivable at all
without a provider key. Renumbered on landing.

### `R-40` — the section field is created together with its aggregation

**Ruled against the recommendation the owner was given.** The drafting session recommended the
cheaper half — the field now, the counters later, so data accumulates from day one without
paying for read paths. **The owner took both, deliberately.** Recorded as recommended-and-declined
rather than as chosen, because the next person to price this wave will want to know the cheap
option existed.

So the reseal carries **the field and the read operations**, which is more than `D-56`'s row
supposed. One reseal owner for the whole wave, as in wave 34.

**And the consequence worth more than the ruling: this unblocks `D-63`.** The dashboard was not
deferred by preference — it was deferred because cross-project counts needed a reseal nobody had
authorised. **That reseal is now authorised, so the row's stated reason has lapsed.** `D-63` is
to be re-read, not carried forward as deferred. *A row whose reason has lapsed and which is still
listed as blocked is the same defect as a row whose reason was never checked.*

**Two corrections to the draft's batching, both measured:**

- **`D-46` is already closed** and must not be batched. `W42-SEAL` closed it 2026-09-23 under
  `R-29`: `RunStatus` gained an optional `terminal_detail`, restricted to the reported code's own
  `safe_detail_keys` and declared inline exactly as `ErrorEnvelope.details` is. No component
  schema, no error code; the catalog stays at twenty-two and frozen. So the batch is **three**
  things, not four.
- **The log-read operation's own premise needs checking before it is briefed.** `W43-PREP`
  measured it: **`audit_event` is never written by `src/`** — its only writers in this repository
  are tests. What exists is `stage_result`, `model_call`, `contract_state_transition` and
  `command_record`. *"Add a read operation" is a decision about what is safe to publish before it
  is a schema.*

### `R-41` — the pilot ends by the owner's explicit instruction

**No date and no observable event** — not "the last expert filed their report", not a deadline.
The wipe runs only when the owner says so.

**The caveat was put to the owner and accepted:** there is no automatic end, so *"the pilot is
over"* remains a sentence **only he can make true**.

### `R-42` — the owner performs the wipe personally

He runs the command on the server himself and decides the fate of the dump the mechanism takes
before deleting.

**With `R-41` this is coherent and that is the point: one person declares, the same person acts.**
No ambiguity about who or when survives. **The runbook records it as his decision to do it
himself, not as a role** — this programme has no role vocabulary and `T-6` forbids inventing one
here, so writing it as a role would invent the thing the decision avoided.

### `R-43` — the character range leaves the screen and stays in the data

The review screen keeps **the quotation and the page number** — what an expert checks by eye and
what `PA-01` criterion 5 tests, so **the criterion is untouched**. The offsets remain anchors
inside the system and keep working at the binding seam.

**The reason is `D-50`'s measurement.** *"Characters 707–746 of the whole document"* is true only
in the coordinate system of the extractor that produced it, that system is named nowhere a reader
can see, and a second extractor disagrees by a drift that grows at every page boundary. **The
number invites a check that fails for the wrong reason** — and an expert who tries it concludes
not that the coordinates differ but that the system lies.

**Scope:** one sentence in `anchorLabel`, `web/src/entities/finding-observation/model/quotation.ts`,
plus the tests asserting the current caption. **Not taken when it was offered:** wave 45's
`W45-BLOCKS` holds `web/src/**` while it runs, and two sessions writing that tree in parallel is
the collision `D-89` already cost this programme once.

### `R-44` — the dashboard is all four panels, in wave 46, without waiting for the deploy

**Ruled 2026-09-25 by direct poll, given to `pdf-analysis-d6` with the options priced from the
tree.** The owner selected **every** candidate — per-section breakdown, findings by verdict, run
activity and spend, documents per project — and on timing chose wave 46 **explicitly against
waiting for `R-1`**. His reasoning: the reseal opens under `R-40` either way, and **doing it once
is cheaper than doing it twice.**

**So `D-63` is not a minimal panel**, and the row that called it a deferred nice-to-have is now
two waves out of date in the other direction.

**One correction to `D-63`'s own text, measured before briefing.** It says *"runs, findings and
verdicts have no aggregate operation at all"* — true when written and **it predates `listDecisions`**,
so read literally it overstates the cost. **Only one of the four panels actually needs `R-40`:**

| panel | source today |
|---|---|
| documents per project | `listProjects` → `Project.document_count` **exists** |
| findings by verdict | `listDecisions` (`R-24`) with `category` and `verdict` parameters **exists** |
| run activity and spend | `listRuns` (`R-5`); `RunStatus` carries `cost_micros`, `cost_basis`, `model_call_count` **exists** |
| **per-section breakdown** | **nothing — this is the panel `R-40`'s field is for** |

*(All four verified against `contracts/api/v1/openapi.json` before this was written.)*

**The integrator's decision on shape, since `R-29` puts the reseal here, and it follows the
drafting session's recommendation against the cheaper path:** the reseal carries **one aggregate
read serving all four panels**, not three client-side page-walks over the existing listings.

**The argument that decides it is `R-24`'s own.** `R-24` was ruled **for** a listing operation and
**against** a client-side walk, deliberately and against the recommendation the owner was given
at the time. **Founding the dashboard on walks over the very operation that exists to prevent
walks would be an odd inheritance** — and three page-walks built now are three page-walks a later
aggregate read deletes. The reseal is open regardless; the marginal cost of doing it right is the
smallest it will ever be.

## 3.16 — `R-45` … `R-48`, ruled 2026-09-25 on the path to GO

The owner supplied a ten-step *minimal path to GO* and asked for a wave from it, for what could
be excluded, and for the forks to be settled by poll. `docs/program/dispatch/GO_PATH.md` marks
all ten against the tree: **three were already done, four cannot be waved at all** — they need a
machine, a domain, a certificate and an API key — **and three are buildable now.**

### `R-45` — wave 46 is the dashboard; the GO path is wave 47

`R-44` had already placed the dashboard in wave 46 and the GO list arrived pointing at the same
wave. **The owner kept `R-44` and moved GO to 47.** Defensible on its own terms: four of the ten
GO steps end at the owner regardless, so a GO wave run now would stop at him on the same four —
whereas the dashboard's reseal is open under `R-40` and pays for itself once.

### `R-46` — the publication-readiness command reports; it does not block

Steps 4–8 are a checklist somebody has to remember. One command answers *"is this deployment safe
to publish?"* — default credential, TLS, plain HTTP, provider mode, cost ceiling, backup.

**Ruled: it records the corpus of problems it finds and raises them as register rows requiring the
owner's decision, considered in wave 47.** It does **not** refuse a deploy.

**The precedent behind that is two days old and expensive.** `D-72`'s repair was correct and
fail-closed, and it took the owner's stand down for a day, because a configuration that had always
been wrong stopped being survivable the moment the code got strict. **A readiness check that
refuses is the same shape**, and the owner has now chosen the other side of it deliberately.

### `R-47` — the durable session register enters the GO wave

`D-65`'s one remaining live item. The BFF holds sessions in the Node process's memory, so **a
web-container restart signs every reviewer out — on every deploy, not on a rare crash.** With
three to five pilot experts that is a support incident per deployment, and deployments during a
pilot are certain.

### `R-48` — the password policy, settled in detail by a second poll

The owner took the general shape first and then said the specifics were mine to ask, not to
assume. Asked, and answered:

| | ruled |
|---|---|
| minimum length | **8** — NIST SP 800-63B's floor; the lockout already makes guessing impractical, so length is defending against a leaked hash rather than against a guesser |
| blocklist | **contextual only** — the account's login, the product name, the current password. **Nothing stored, nothing to license, nothing to go stale** |
| the seeded account | **sign-in works and leads straight to the change screen.** No other screen opens until the password is changed, so the default cannot be left in place by forgetting |
| expiry | **none.** Periodic rotation drives people to predictable iterations; revocation already exists and acts immediately |

**One consequence the integrator owes out loud, because the combination permits it.** With a
contextual-only list and an 8-character floor, the literal string `password` **is itself a legal
password** — it is exactly 8 characters, it is not the login, and it is not the product name.
It is refused at the one moment that matters, the forced first change, because it is then the
*current* password. **Afterwards nothing refuses it.**

**Recommended, and easy to decline:** add the **shipped default credential value** to the
contextual list. That is still context about this deployment rather than a stored corpus — the
system already knows it, `access-check DEFAULT CREDENTIAL` is built on knowing it — so it costs
no file, no dependency and no licence. **Not done unless the owner says so;** recorded here so
the next reader does not discover the gap and assume nobody looked.

### `R-49` — wave 48 is correction, debt closure and a code audit

Ruled 2026-09-25 while wave 45 was closing. **Cadence and content agree for once:** 45 built, 46
is the dashboard, 47 is GO — and four of GO's ten steps end at the owner, so 48 arrives at
exactly the point where a wave that can only wait would otherwise be scheduled.

**What it carries, named now so it is not invented at the end:** `D-98`, `D-99` and `D-100` —
the surface guard's three blind spots, which are one repair — plus `D-76`'s third instance,
`D-87`, `D-89`'s rule, `D-96`'s discipline, `D-97`'s six renderer copies, `D-74`, and whatever
46 and 47 leave.

**And a code audit, which this programme has never run as its own subject.** Every audit so far
has been a judge inside a wave, auditing that wave's work. `W48` reads the tree as a whole —
which is how `D-99`'s eight sentences stayed wrong since wave 34 without anybody's brief ever
pointing at them.
