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

## 4. Still open, and still the owner's

- **`OD-18`** — three to five named experts with committed slots; `P4-BHV-01` waits on it alone.
- **`OD-17`** — the next corpus shape. **`R-16` and `R-17` bear on this but do not close it**:
  they settle how the *normative* corpus is vectorised, dated and attributed, not what the next
  evidence corpus should be.
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
