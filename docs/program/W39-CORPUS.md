# W39-CORPUS — `D-59` re-recognised, and the key that was not there

**Task `W39-CORPUS`, `D-59` under `R-19` and `R-27`.** Worktree `/root/w39corpus`, branch
`agent/w39-corpus`, based on `3fd5c17`. Gate lane `gate-w39b`. Logs under `/root/w39-logs/corpus-*`.

**What was spent: $0.00.** Not one model call was made, and the reason is the first section.
Everything else in this document is measured, and every figure carries the command that
produced it and the tree it ran on. The corpus was opened read-only; nothing was written into
`.local/`.

---

## 1. The credential `R-27` authorises does not exist on this host

`R-27` reads: *"`infra/deploy/env/provider.env` is on the host and already pays for live
runs."* **It does not.** The file holds a wave-37 certification lane:

| name in the file | what it holds | how that was established |
|---|---|---|
| `AUDITMANAGER_PROVIDER_MODE` | `proxy` | read from the file |
| `PROXY_LLM_BASE_URL` | **`http://:59990` — no host at all**, thirteen characters | `urllib.parse.urlparse(...)` → `hostname is None`, `port == 59990` |
| `PROXY_LLM_TOKEN` | **never read into any output**, here or anywhere | — |
| `PROXY_LLM_MODEL` | **`stub/w37cert4`** | read from the file |

Three independent confirmations, none of which required the token:

1. **Nothing listens on 59990.** `bash -c 'echo > /dev/tcp/127.0.0.1/59990'` → `Connection
   refused`. The only published port on this host is `127.0.0.1:31500`, the `auditmanager-w19a`
   application stand's nginx — `docker ps` shows five containers, all of that one stack, and
   **no LLM proxy at all**.
2. **The slug names a certification stub.** `W37-CERT4.md` §"provider outage" records
   *"`PROXY_LLM_BASE_URL` was pointed at `http://w37cert4-stub:59991`, a port nothing listens
   on inside the compose network"* — a **deliberately dead endpoint**, built to drive
   `dependency_unavailable` for `PA-01` criterion 9. The file's mtime is
   `2026-09-22 19:57:59`, which is that session's window.
3. **No other credential is reachable.** `ANTHROPIC_API_KEY`, `PROXY_LLM_*` and `OPENAI_*` are
   all unset in this process's environment, and `.local/handoff/` carries no key and no note
   about one.

**So the run stopped before it started, and that is `R-29`'s rule rather than a workaround of
it.** `R-29` stops at spending; `R-27` authorised spending *that key*; the key is a stub. Going
looking for a different credential would be substituting my own judgement for the owner's
authorisation, and the session did not.

**What the integrator has to do to unblock the 121 pages.** Put a real proxy base URL, token
and model into `infra/deploy/env/provider.env` on the host — the owner's own act, per
`OWNER_RULINGS_2026-09-17.md` §3 — and then one command spends it:

```
set -a; . infra/deploy/env/provider.env; set +a
PYTHONPATH=src .venv/bin/python -m auditmanager.norms \
    --corpus /root/projects/PDF-Analysis/.local/norms/corpus \
    --ledger /root/w39-logs/corpus-repairs.json \
    --snapshot-id 2026-07-23..2026-08-20+17d.4b74348debf7 \
    --ceiling-usd 5.00
```

It is resumable page by page, it refuses before the first call if the URL has no host, and it
stops on the first call the transport does not price. Against the file **as it stands today**
it refuses, and the refusal names no value:

```
refused: PROXY_LLM_BASE_URL names no host. A URL of the form 'http://:<port>' is accepted by
ProxySettings, which checks only the scheme, and then fails at call time as a transport error
that reads like a provider outage. It is a lane pointed at nothing, and a paid run does not
start against one.
```

### 1.1 A gap this uncovered in code I may not touch

`ProxySettings.__post_init__` validates only that the base URL *starts with* `http://` or
`https://`. `http://:59990` passes it, and the failure then arrives at call time as
`DEPENDENCY_UNAVAILABLE` — **`retryable: true`** — for a lane that is pointed at nothing and
that no retry can fix. That is the `D-7` shape the register already knows in two other places,
and `src/auditmanager/analysis/text/` is a forbidden hotspot for this lane, so it is reported
rather than fixed. **A register row is warranted.** The one-line repair is a `urlparse`
hostname check in `ProxySettings`, and `test_a_proxy_url_with_no_host_is_refused` in this
wave's suite is the case, written against my own runner.

---

## 2. The defect, re-measured — and `R-19`'s scope is 65 % of it

### 2.1 The 79 reproduce exactly

`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /root/w39-logs/corpus-scratch/population.py`,
run at `ab95510`, reading `/root/projects/PDF-Analysis/.local/norms/corpus`:

| measured | value |
|---|---:|
| documents | 674 |
| blocks | 28 249 |
| blocks containing `The user wants me to` | **79** |
| documents carrying them | **34** |
| characters in those 79 | **1 563 561** |
| median / max / min | **12 660 / 62 359 / 330** |

Every figure in the brief's opening paragraph is exact. `79 / 28 249 = 0.28 %`;
`1 563 561 / 74 642 798 = 2.09 %`.

### 2.2 The 79 is a count of one phrase, and the defect is larger

The brief asks for the check *"looking for the model's own reasoning"*. Asked as four
independent families rather than as one phrase — `src/auditmanager/norms/degeneracy.py`, and
§4 is the calibration — the corpus answers:

| | blocks | documents | characters |
|---|---:|---:|---:|
| text no source wrote | **121** | **54** | **1 820 150** |
| of which, `R-19`'s 79 | 79 | 34 | 1 563 561 |
| **beyond `R-19`'s scope** | **42** | 34 | **256 589** |

**Every one of the 79 is inside the 121. None was missed.** The 42 beyond it split in two:

| | blocks | documents | characters |
|---|---:|---:|---:|
| the model's own narration or plan | **96** | 41 | **1 725 329** |
| — of which `R-19`'s 79 | 79 | 34 | 1 563 561 |
| — **beyond `R-19`** | **17** | — | **161 768** |
| the pipeline's serialised envelope | **25** | 20 | **94 821** |


**Seventeen more blocks of the same defect**, which the `D-59` grep could not see because they
carry no first-person pronoun:

| characters | document | page | found by |
|---:|---|---:|---|
| **50 989** | `СП_28.13330.2017` | 73 | *"The document is a technical table from a Russian engineering standard…"* |
| **38 436** | `СП_21.13330.2012` | 48 | *"The document is a technical table…"* |
| **37 199** | `СП_14.13330.2018` | 112 | *"The document is a page from a Russian technical standard…"* |
| 4 881 | `СП_70.13330.2012` | 184 | *"I will transcribe the table exactly as it appears"* |
| 4 733 | `СП_32.13330.2018` | 18 | *"I will use HTML tags like…"* |
| 4 085 | `Приказ_МЧС…_N_628` | 40 | *"**Transcription Strategy:** … I must ensure…"* |
| 3 967 | `СП_249.1325800.2016` | 51 | *"I must ensure…"* |
| 3 134 | `СП_35.13330.2011` | 197 | *"I will now transcribe the table data accurately."* |
| 2 834 | `СП_28.13330.2017` | 109 | *"I will transcribe…"* |
| 2 237 | `ГОСТ_IEC_60947-2-2021` | 185 | *"I will transcribe each row accurately"* |
| 2 110 | `СНиП_3.05.05-84` | 23 | *"**Table Structure Analysis:** … I will transcribe"* |
| 1 653 | `СП_333.1325800.2020` | 199 | *"I will extract the table content as follows:"* |
| 1 507 | `ГОСТ_Р_56943-2016` | 87 | *"The document is a page from a Russian technical standard…"* |
| 1 370 | `СП_345.1325800.2017` | 66 | *"The document is a technical table…"* |
| 1 238 | `ГОСТ_Р_55142-2025` | 40 | *"The image shows a mechanical assembly for shearing tests."* |
| 906 | `ГОСТ_Р_2.106-2019` | 27 | *"The width of the table is divided into segments: 20, 6, 6, 8…"* |
| 489 | `СП_45.13330.2017` | 126 | *"**Transcription strategy:** - I will use HTML tags like"* |

**The top three are the point.** They are the **second, third and fourth largest degenerate
blocks in the entire corpus** — 126 624 characters between them, more than the 62 359-character
block `D-59` was written around — and every sentence of them is English narration of a page
that was never transcribed. `D-59`'s grep is for *"The user wants me to"*; these say *"The
document is a"*, and no pronoun appears anywhere in them. `OPERATING_CONSTRAINTS.md` §12: the
query shared an assumption with its subject, so it could not see the subject being wrong.

**And twenty-five blocks of a different leak, in twenty documents.** Not the model — the
**pipeline's own JSON envelope**, written into the body where the page's text belongs:

```
[{"text": "\"СП 47.13330.2016. Свод правил. Инженерные изыскания для строительства…\"",
  "text": "Документ предоставлен КонсультантПлюс"}]
```

`СП_163.1325800.2014` page 5 is 14 924 characters of it; `СП_47.13330.2016` page 34 is 13 963.
It is not `D-59` and it is not covered by any ruling, and its consequence is identical: an
index built on this corpus returns a serialisation artefact to an expert asking what a norm
says. **It is a register row, not a scope extension.** The count is **25 blocks in 20 documents,
94 821 characters**, with the command above.

### 2.3 "55 of the 79 carry no Russian at all" is false. It is **47**

Measured as Cyrillic code points in the block body:

| | blocks of the 79 |
|---|---:|
| **zero Cyrillic characters** | **47** |
| fewer than 10 | 49 |
| fewer than 100 | 54 |
| Cyrillic share of letters below 5 % | 54 |
| **any Cyrillic at all** | **32** |

**`55` does not reproduce under any threshold I could find**; the nearest is 54, twice. The
complementary claim — *"24 mix Russian normative text with English reasoning"* — is therefore
**32**, a third more than `R-20` is sized for. `R-20`'s ruling is unaffected in substance (the
mixed blocks stay and are marked) and its **quantity** is understated by eight blocks.

### 2.4 `recognized` is confirmed for all 121, which strengthens `R-19` rather than weakening it

Read from each document's `blocks.json` rather than from `results.md`, so the check does not
share a source with the thing it measures
(`.venv/bin/python /root/w39-logs/corpus-scratch/verify.py`): **121 matched, 0 unmatched,
`{'recognized': 121}`.** The corpus's three `failed` blocks are elsewhere. So `R-19`'s
central argument — *"there is nothing to filter on but the text itself"* — holds not only for
the 79 it was written about but for every block the wider check finds.

---

## 3. Does a re-recognition move the snapshot identifier? **Yes, and `R-17`'s identifier as
built cannot notice**

The brief says `R-17`'s snapshot identifier *"already models exactly this problem"*. It models
the problem and **is blind to this instance of it, by construction.** That is worth stating
precisely, because the two readings lead to opposite implementations.

`CorpusSnapshot.content_digest` is SHA-256 over `(slug, source document id,
sha256(results.md))` for all 674 documents. A repair does not rewrite `results.md` — `.local/`
is read-only, the drop is the evidence, and a corpus mutated in place cannot be compared with
the one every earlier figure was taken against. **So the base digest is unchanged by
construction, while the text that gets segmented, chunked, embedded and cited is different
text.**

That is exactly the failure `R-17`'s recorded consequence exists to prevent, read the other way
round. The ruling's case was *"a refresh silently reissues a ГОСТ under an unchanged save date,
and verdicts taken against the old text claim to have been taken against the new"*. A repair is
the same divergence **with our own hand on it**: two chunk sets, one identifier, and nothing on
a verdict row able to say which text an expert actually read.

**So the identifier must move, and it must move visibly rather than merely differ.**
`repair.repaired_snapshot` derives it:

```
2026-07-23..2026-08-20+17d.4b74348debf7   →   2026-07-23..2026-08-20+17d+79r.<digest12>
```

- **The window does not move.** A repair says nothing about when the corpus was drawn, and a
  window that drifted because we re-read a page would be a false statement about the draw.
  `test_the_window_does_not_move_when_a_page_is_repaired`.
- **The undated count does not move**, for the same reason.
- **The digest folds in every applied replacement**, sorted by `(slug, block_id)` before a byte
  is hashed — structure, then compute, then write the value, the same rule `snapshot.derive`
  already follows because a filesystem walk has no order and the corpus has no commit name.
- **A new `+<n>r` term says how many pages were repaired.** A reader who sees `+79r` asks which
  79, exactly as `R-17`'s `+17d` was meant to make them ask which seventeen. Without it the
  repaired identifier is a different opaque string and a reader cannot tell a repair from a
  re-draw.
- **A ledger that applied nothing returns the base snapshot unchanged**, object for object. An
  empty repair pass is not a new corpus, and an identifier that moved for it would be a record
  of effort rather than of content. `test_a_ledger_that_applied_nothing_returns_the_base_unchanged`.
- **A ledger is refused against a corpus it was not taken from.** Replaying one against a
  re-drawn corpus would apply a page's old transcription to a document that has since changed.

**What this asks of the owner of the schema slot.** `norm_chunk.corpus_snapshot_id` should
carry the **repaired** identifier for a repaired corpus, and `corpus_snapshot` needs one more
column — `repaired_pages integer NOT NULL DEFAULT 0` — or the `+79r` in the id is the only
place the fact lives and a query has to parse a string to find it. That is the same argument
`W33-CORPUS` made for `undated_documents`. No migration is proposed here and `db/` was not
touched.

---

## 4. The guard, and every mutation red

### 4.1 What the check is, and what it deliberately is not

`src/auditmanager/norms/degeneracy.py` asks one question — *does this text speak about the page
instead of transcribing it* — in four families. Every phrase in it was taken from a block in
the drop and none was invented.

| family | what it catches | blocks in the corpus |
|---|---|---:|
| `INSTRUCTION_ECHO` | the recognition prompt read back as content | 66 |
| `FIRST_PERSON_PLAN` | the model speaking as itself about the task | 89 |
| `PAGE_NARRATION` | English description of the page in place of the page | 21 |
| `SERIALISED_PAYLOAD` | the pipeline's own JSON envelope in the body | 25 |

**Two families were measured and left out**, and this is the part that would otherwise be
invented rather than derived:

- **Token repetition**, the obvious signal for *"the model looped"*. It does catch
  `СП_131.13330.2025` page 280, where `Vladikavkaz` is **98 %** of the tokens over 30 529
  characters. But `ГОСТ_9544-2015`'s seal-tightness tables sit at **0.72–0.86** on `PN` across
  **19 blocks** and are entirely legitimate, and `ГОСТ_33259-2015` page 23 reaches **0.90** on a
  real flange table. Above 0.8 there are 14 blocks, above 0.9 there are 2, above 0.95 there is
  1. **One loop above the noise and 27 legitimate blocks inside it**: the margin is too thin to
  assert on, and a guard that reddens on a real table is a guard that gets deleted.
- **Ascending enumeration runs.** Of the three blocks in the corpus with 40 or more consecutive
  ascending integers, **two are the real symbol table of `ГОСТ_2.304-81`** (pages 17 and 18 —
  `1 2 3 4 5 6 7 8 9 | 10 11 12 …`, which is what that standard *is*) and one is narration.
  **Two false positives out of three is not a guard.**

Both are real defects in the drop and neither is *this* defect. The repetition loop at
`СП_131.13330.2025` page 280 in particular is 30 529 characters of one city name and belongs in
the register beside the serialised payloads.

### 4.2 The sweep: twenty-two mutations, twenty-two reds

Copy built with `make mutation-copy MUT=/root/w39corpus-mut`
(`/root/w39-logs/corpus-mutation-copy.log`, exit 0). **Baselined unmutated first** —
`.venv/bin/pytest tests/integration/norms -o pythonpath=/root/w39corpus-mut/src -q` →
`62 passed` — and the copy proved to be the imported tree:

```
IMPORTED /root/w39corpus-mut/src/auditmanager/norms/degeneracy.py
IMPORTED /root/w39corpus-mut/src/auditmanager/norms/repair.py
IMPORTED /root/w39corpus-mut/src/auditmanager/norms/rerecognition.py
```

Sweep: `.venv/bin/python /root/w39-logs/corpus-scratch/mutate.py` →
`/root/w39-logs/corpus-mutations.log`. `PYTHONDONTWRITEBYTECODE=1` throughout and `__pycache__`
purged between cases, per §10.2 — the trap `W33-CORPUS` found in this same lane.

| | mutation | red, verbatim |
|---|---|---|
| M1 | `degeneracy`: drop `"the user wants"` from the first-person family | `E AssertionError: assert <DegeneracySignal.FIRST_PERSON_PLAN: 'first_person_plan'> in (<DegeneracySignal.INSTRUCTION_ECHO: 'instruction_echo'>,)` |
| M2 | the narration family leaves the check | `E AssertionError: assert False` on `verdict.is_degenerate` for `СП_28.13330.2017` p73 |
| M3 | the envelope regex can never match | `E AssertionError: clean` |
| M4 | the check stops case-folding | `E assert False` on the upper-case spelling |
| M5 | the echo family leaves the check | `E AssertionError: assert <DegeneracySignal.INSTRUCTION_ECHO…> in (…FIRST_PERSON_PLAN…)` |
| M6 | **a narration phrase widened onto legitimate ISO citations** | `E AssertionError: page_narration: 'iso '` |
| M7 | `rerecognise`: a degenerate replacement is applied anyway | `E AssertionError: assert <RepairOutcome.REPAIRED…> is <RepairOutcome.STILL_DEGENERATE…>` |
| M8 | `MAX_ATTEMPTS` 2 → 1: a degenerate page is never re-read | `E assert 1 == 2` |
| M9 | the truncation and empty checks are removed | `E AssertionError: assert <RepairOutcome.REPAIRED…> is <RepairOutcome.UNUSABLE…>` |
| M10 | `MINIMUM_REPLACEMENT_CHARACTERS` 16 → 0 | `E AssertionError: assert <RepairOutcome.REPAIRED…> is <RepairOutcome.UNUSABLE…>` |
| M11 | **an unpriced call is recorded as a free one** (`cost_usd or 0.0`) | `E assert 0 == 1` on `unpriced_attempts` |
| M12 | the repair digest is taken in ledger order | `E AssertionError: assert '…+1d+3r.a1…' == '…+1d+3r.7f…'` |
| M13 | the identifier drops the repair count | `E AssertionError: assert '+1r.' in '2026-07-23..2026-08-20+1d.…'` |
| M14 | an empty repair pass is given a new identifier | `E AssertionError: assert CorpusSnapshot(snapshot_id='…+1d+0r.…') == CorpusSnapshot(snapshot_id='…+1d.…')` |
| M15 | the digest ignores what the replacement says | `E AssertionError: assert '…' != '…'` on one changed character |
| M16 | a ledger from another corpus is accepted | `E Failed: DID NOT RAISE ValueError` |
| M17 | an unapplied replacement stays reachable | `E Failed: DID NOT RAISE ValueError` |
| M18 | two repairs for one block are accepted | `E Failed: DID NOT RAISE ValueError` |
| M19 | a ledger of an unknown version is read anyway | `E Failed: DID NOT RAISE ValueError` |
| M20 | a repair moves the draw window | `E AssertionError: assert None == '2026-08-20'` |
| M21 | **the hostless proxy URL is accepted** | `E Failed: DID NOT RAISE RunRefused` |
| M22 | **the refusal prints the configured value** | `E AssertionError: assert 'example.invalid' not in 'the provide…a file here.'` |

**M6 is the one that matters most and it is the easiest to leave out.** Every other case proves
the check can *stop* firing. M6 proves it can *start* firing on text that is fine: it adds
`"iso "` to the narration family, and `test_the_norms_own_text_is_left_alone` reddens on a
fixture holding `ISO 5167-2:2003` and `IEC 60947-2:2016` — real citations from real norms in
this corpus. A degeneracy check without that direction proved is a check that will eventually
be widened until it eats clause text, and nothing will say so.

### 4.3 The two that first reddened nothing — one weak guard, one insufficient mutation

Rule 7 asks which was which. It was one of each, the same split `W33-CORPUS` reported.

- **M12 — the guard was weak, and it was weak in exactly the `§12` way.**
  `test_the_identifier_does_not_depend_on_the_order_repairs_were_taken_in` built both of its
  ledgers through `ledger_of`, **which sorts**. So both sides of the comparison arrived already
  sorted and the test could not see the sort inside `repaired_snapshot` at all: removing it
  changed nothing. **The query shared an assumption with its subject.** It matters because
  `RepairLedger.from_document` does **not** sort — an externally written or partially completed
  ledger file is genuinely unsorted, which is the case the guard exists for. The test now
  constructs `RepairLedger` directly, and M12 reddens with two different identifiers.
- **M5 — the mutation was insufficient.** It replaced the *first* phrase in
  `INSTRUCTION_ECHO_PHRASES`, and the fixture — a real block from `СП_63.13330.2018` page 15 —
  also contains *"extract only visible text"*, which the family still matched. The corrected
  mutation removes the family from `_FAMILIES` entirely and reddens.

---

## 5. What is in the tree, and what it does

Nothing here calls a model on its own, nothing imports another bounded context except the
runner, and no dependency was added. `pdfplumber` is the repository's pinned PDF library
(`OD-01`) and it already carries the rasteriser.

| module | holds |
|---|---|
| `degeneracy.py` | the four families, the verdict and its evidence |
| `repair.py` | `PageRepair`, `RepairAttempt`, `RepairLedger`, and `repaired_snapshot` |
| `rerecognition.py` | the `PageRecogniser` port, the prompt, the two-attempt rule |
| `__main__.py` | the runner: the **only** file in `norms` that knows a provider exists |
| `corpus_source.py` | `+ crop_path`, `read_crop`, `degenerate_pages` |
| `segmentation.py` | `+ blocks()`, the public form of the parse |
| `model.py` | `+ BlockBody` |

**The result is data, not a rewrite of the corpus.** The ledger is keyed by
`(document_slug, block_id)` — never by page, because `results.md` prints no heading for a page
with no block and two blocks can share a page, and never by path, because `AGENTS.md` §4
forbids it. Each row carries the original's SHA-256 and length, the crop's SHA-256, the
outcome, and one record per attempt with the model, the stop reason, both token counts, the
**reported** cost and the degeneracy signals found. A segmenter consults
`ledger.replacement_for(slug, block_id)` and gets `None` — *use what the corpus says* — for
every page that was not repaired.

**Three rules the code enforces rather than documents:**

1. **A replacement that is still degenerate is never applied.** It is recorded with its
   signals; the corpus text stands. Swapping one unusable page for another would count as a
   repair in every summary while changing nothing a reader can use — `AGENTS.md` §4's silent
   fallback, with a bill attached. `PageRepair.__post_init__` refuses to construct the
   combination at all.
2. **A truncated or near-empty answer is never applied.** Half a clause read as the whole of it
   is worse than the text it would replace, because nothing downstream can see that it is half.
   `R-20`'s *nothing is cut* is the same instinct.
3. **A page is read twice and no more.** *"This page re-recognises degenerate twice"* is the
   finding the owner asked for; an unbounded retry converts that finding into an invoice.

**The prompt is a constant in the tree**, not a parameter, so two runs are comparable. It is
deliberately short: the drop's degenerate pages **are, in substance, the original recognition
prompt** — a long numbered ruleset the model enumerated back instead of following, which is why
`СП_45.13330.2017` page 124 ends `…995. 996. 997.` The replacement states its prohibitions in
terms of the output and offers no numbered list to continue.

---

## 6. What I could not do, stated in the conclusion and not in a footnote

**Not one of the 121 pages was re-recognised, because no credential exists to do it with.**
Everything in §2 is a measurement of the defect; nothing in this wave is a measurement of the
repair. Specifically, all of the following are **unverified**:

- whether the proxy's upstream model accepts an image content part at all;
- whether a re-recognised page comes back clean — the guard is proved against fixtures and
  against the corpus's own degenerate blocks, never against a fresh transcription;
- **how many of the 121 come back degenerate twice**, which is the number `R-19` most wants;
- the real cost per page, and therefore whether `R-22`'s `$2.58–$3.17` is near. It cannot be
  predicted from that figure in any case: `R-22` priced **Claude Opus 5 at $5/$25 per MTok**
  and `provider.env` is in **`proxy` mode**, where the model is the proxy operator's choice and
  the rate table does not apply. The only honest number will be the one the proxy reports, and
  the ledger carries it per call for that reason.
- the price of the **121**, which is 53 % more pages than the 79 `R-22` costed.

`OPERATING_CONSTRAINTS.md` §12: *a caveat is not a control*. This is the blocker, not a
footnote to carry forward.

---

## 7. Every premise of the brief I measured and found false

**1. `R-27`'s key does not pay for anything.** `infra/deploy/env/provider.env` holds
`PROXY_LLM_BASE_URL=http://:59990` — no host — and `PROXY_LLM_MODEL=stub/w37cert4`, the
wave-37 certification stub. Nothing listens on that port, no LLM proxy runs on this host, and
the file's mtime is inside `W37-CERT4`'s window. **§1.**

**2. The 79 is a count of one phrase, not of the defect. It is 121 blocks in 54 documents.**
Forty-two more blocks carry text no source wrote, including the **second, third and fourth
largest degenerate blocks in the corpus** — 50 989, 38 436 and 37 199 characters of English
narration with no first-person pronoun anywhere in them, which is why the `D-59` grep could not
see them. **§2.2.**

**3. "55 of the 79 carry no Russian at all" is wrong: it is 47.** And so "24 mix" is **32**.
`55` reproduces under no threshold I could find. `R-20` is unaffected in substance and
understated by eight blocks in quantity. **§2.3.**

**4. `R-17`'s identifier does not "already model exactly this problem" — it is blind to it by
construction.** The digest is over `results.md` bytes, and a repair changes what is segmented
without changing those bytes, so the raw corpus and the repaired one share an identifier
unless something is added. `repaired_snapshot` is that something. **§3.**

**5. A twentieth of the corpus's leaked text is not the model at all.** Twenty-five blocks in
**twenty** documents, **94 821 characters**, carry the **pipeline's own JSON envelope** —
`[{"text": "…"` — as body content. No ruling covers it and its consequence is identical to
`D-59`'s. **§2.2.**

**6. The brief's "one example repeats the same sentence dozens of times" understates the worst
case, and the worst case is outside the 79.** `СП_131.13330.2025` page 280 is **30 529
characters in which `Vladikavkaz` is 98 % of the tokens**. It contains no phrase from the
`D-59` grep and no first-person pronoun.

**7. `ProxySettings` accepts a base URL with no host**, and the resulting failure is mapped to
`dependency_unavailable`, which is `retryable: true`. A lane pointed at nothing is reported as
a transient outage. **§1.1.**

**8. "No new dependency" is easier to break here than it looks.** `pypdfium2` and `pillow` are
**installed in the venv and absent from `pyproject.toml`** — they arrive as `pdfplumber`'s
transitive closure. Importing either from `src/` compiles, runs and looks free, and it is a new
direct dependency on a distribution the lock does not name. The rasteriser is reached through
`pdfplumber`, which is pinned.

**9. The register's own summary line for `D-59` carries the `55`/`24` split**, so closing this
row means correcting two numbers there as well as adding the 42.

**10. The gate baseline in the brief is exact to the test**, and that is worth saying after
`W33-CORPUS` found its own base commit red. **§8.**

### One I nearly filed, and did not, because the second measurement contradicted the first

I recorded `pdftoppm` failing on a crop with `I/O Error: … File name too long` and had it
written down as a host trap. **It was my own path.** The corpus's slugs are truncated at 96
bytes — `СП_63_13330_2018__Свод_правил__Бетонные_и_железобетонные_ко`, cut mid-word — and I had
typed out the document's full title as though it were the directory name, 318 bytes. Re-run
against the real path, `pdftoppm` exits 0. The corpus property is real and worth one line —
**a slug cannot be reconstructed from a document's title, because it is truncated** — and the
defect I was about to report was not.

---

## 8. Verification

`git status --porcelain` clean before the gate. `make gate` from a committed-clean tree at
`ab95510`, lane `gate-w39b`:

```
make gate > /root/w39-logs/corpus-gate.log 2>&1
```

| component | baseline in the brief | this run | |
|---|---|---|---|
| foundation | 35 | **35 passed in 42.41s** | ✅ |
| battery | 2207 / 5 / 169 | **2239 passed, 5 skipped, 169 subtests, 585.03s** | ✅ |
| frontend | 988 in 71 files | **988 passed, 71 files** | ✅ |
| `git diff --check` | clean | whitespace pass | ✅ |

```
/root/w39-logs/corpus-gate.log:233:GATE OK: battery, foundation, frontend and whitespace all pass
```

**`2239 − 2207 = 32`, and this branch adds exactly 32 tests** —
`.venv/bin/pytest tests/integration/norms/test_degeneracy.py tests/integration/norms/test_rerecognition.py -q`
→ `32 passed`. Every one of the 32 passes and nothing that was passing at `3fd5c17` changed.
The whole `norms` suite is `62 passed in 0.47s`.

**The literal `GATE OK` line was read out of the log; no exit code a wrapper handed over was
asserted on** (`OPERATING_CONSTRAINTS.md` §4.6). The `EXIT=0` written after the redirect agrees
with it, which is the second measurement rather than the first.

**One measurement at a time.** The gate ran against a committed-clean tree with nothing else in
this lane touching it; the corpus sweeps in §2 and §4 ran before it and after it, never during.

---

## 9. Rollback

Additive. Five commits, three new modules, two new test files, three small additions to
existing `norms` modules. Nothing imports `auditmanager.norms` outside its own package, no
composition root, no contract, no migration, no dependency.

| drop | to lose |
|---|---|
| the last commit | the order guard's strengthening |
| all five | the whole repair facility; the tree returns to `3fd5c17` exactly |

`git rm src/auditmanager/norms/{degeneracy,repair,rerecognition,__main__}.py` plus the two test
files removes every trace, and the three additions to `model.py`, `segmentation.py` and
`corpus_source.py` revert independently.

## 10. What is deliberately not here

- **No spend.** §1, §6.
- **No change to `.local/`.** It was opened read-only; every output is under `/root/w39-logs/corpus-*`.
- **No migration and no schema change.** `db/` untouched. §3's column is a proposal.
- **No embeddings and no tokeniser.** `D-60` says the token count comes first and that is not
  this wave.
- **No repair of the 42 blocks beyond `R-19`'s scope.** They are measured, listed and named;
  extending the ruling is the owner's, not mine.
- **No change to `analysis/text/`.** §1.1 is reported, not fixed.
