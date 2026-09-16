# Wave 9 closure: sweeping a surface instead of guessing at it

Written 2026-09-16 by the integrator. Convergence at `8b034c7`, base `1708a01`.
**`make gate` → `GATE OK`**: foundation 35, battery **816 passed** / 5 skipped / 116
subtests, frontend 289, whitespace clean. 811 → 816.

## 1. The observation that turned out not to be a defect

`W6-CERT` noted that emptying `PDF_MAGIC` left criterion 10 green. I checked it before
building anything, and **it is not a gap**: `tests/integration/ingest` reddens on both of
its cases, and the e2e suite staying green is the division of labour working — the journey
test checks the journey, the rule test checks the rule.

Recorded because the check cost two minutes and would otherwise have become a wave spent
guarding something already guarded.

## 2. What the question was actually worth asking of

The right move was to ask it of *every* rule rather than that one. Each constant and branch
in `ingest/envelope.py` was mutated in turn against both suites. **Three survived with
nothing red:**

| Mutation | Before |
|---|---|
| `MIN_PAGES` 1 → 0 | green — no test offered a document with no pages |
| `MAX_SOURCE_FILENAME` 255 → 100000 | green — no test offered an over-long name |
| delete the `non_empty` name check | green — no test offered a blank name |

All three sit on the criterion-10 surface, which `PROTOTYPE_PROFILE.md` §8 certifies as
unsupported input "shown explicitly with no fallback", and all three are reachable through
the twelve operations: a file name is a caller-supplied string, and a PDF with no pages is
311 bytes.

The zero-page document is built in the test rather than committed as a fixture. Both corpora
are frozen evidence and `build_pc02_corpus.py` fixes the negative set at 2–4 documents;
adding bytes to either would invalidate a measurement already taken. A test can make its own
bytes.

## 3. My first attempt was five green tests over three rules it could not check

The tests imported `MIN_PAGES` and `MAX_SOURCE_FILENAME` and built the expected constraint
from them. **Both sides of every comparison then moved together under mutation:** raising
`MAX_SOURCE_FILENAME` to 100000 also lengthened the name the test sent, so the upload was
still refused, with the new limit in the message, and the test still passed.

This is the programme's oldest failure in a new dress. The standing formulation is "the test
asserted a property of the fixture rather than of the code"; here the assertion was
*computed from the implementation under test*, which is the same thing arriving by import
rather than by fixture.

The expected values are literals now, pinned against the independent authority the module's
own comment cites — `ck_document_version_page_count CHECK (page_count BETWEEN 1 AND 30)`. A
constant that drifts away from the migration is now a red test instead of a quiet agreement
between a module and itself.

**Only the mutation sweep found this.** The five tests passed, read correctly, named their
scenarios correctly and used real fixtures. This is the second wave running in which the
discipline caught tests that would otherwise have been committed green over an unguarded
branch — wave 8 §2 was the first.

## 4. Why the name rules could hide

`test_traversal_shaped_file_names_are_refused_without_being_echoed` asserted
`details["field"] == "source_filename"` and stopped there, so it passed whichever of the
three name rules fired. Its parameters already include a blank name — and with `non_empty`
deleted, a blank name still reaches `plain_base_name`, because the pattern requires at least
one character. Field is not reason.

Each case now names the rule that must refuse it, so `M19` reddens there too, independently
of the new file.

## 5. Mutations, after the fix

| Mutation | Result |
|---|---|
| M17 `MIN_PAGES` 1 → 0 | **RED** — the zero-page test |
| M18 `MAX_SOURCE_FILENAME` → 100000 | **RED** — the over-long-name test |
| M19 delete `non_empty` | **RED** ×2 — the blank-name test and the traversal case it used to slip past |
| M20 `MAX_PAGES` 30 → 9999 | **RED** ×2 — the pinned constraint string catches it in two places |

Each reddens exactly the test that claims it. Two boundary tests bracket the file-name rule
from both sides — one character over is refused, exactly 255 is accepted — so the rule is a
limit rather than a prohibition, which a single negative case cannot establish.

## 6. Version fixation

`origin/dev` advances to the wave-9 merge. **`origin/main` stays at `8f418e9`.**

Wave 9 changed **no `src/` or `db/` code at all** — only `tests/`. So `W6-CERT`'s
certification of `c0d7daf` still describes this tree's behaviour exactly, and `main` can
advance to carry it whenever the owner chooses. Pending across four waves now, blocking
nothing.

## 7. Still owner-blocked

- **`OD-18`** — three to five named experts with committed slots. `P4-BHV-01` waits on this
  alone.
- **`OD-17`** — the next corpus shape; PC-02's precision evidence is saturated.
- **The 21st error code.**
- **Whether `origin/main` advances** to `c0d7daf` or later.
