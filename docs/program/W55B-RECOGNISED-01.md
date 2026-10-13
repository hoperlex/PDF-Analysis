# W55B-RECOGNISED-01 — report (the portal's recognised text)

- Task: `dispatch/W55-PLAN.md` §B3.5 (the text-layer-or-block rule), §B3.6, §B4 Stage B 3 `W55B-RECOGNISED-01`, §B5; `P02_SEAMS.md` §4.1, §4.2, §4.8 (sealed, read only); owner rulings R-116, R-117.
- Branch `agent/w55b`, worktree `.local/worktrees/w55b-exec`, base `19ea1525` (BUDGET report; below it INGEST, STREAM, FIXTURES, SEAL).
- Written by one writer (Claude Opus 5.5 delegate of the wave executor). Nothing is pushed, merged or tagged.
- Lane stack (when up): `FOUNDATION_INSTANCE=auditmanager-w55b-recognised`, PostgreSQL `57450`, S3 `61050/61051`.

## 0. Status (living; updated at every commit)

| Step | State |
| --- | --- |
| living report (this file) | started (`39ea5132`) |
| `analysis/recognised/` (parser, flags, artifact), role constants, export lines, `norms.public` line | done (`d9bea309`); tests pending |
| `extract_document` path form; `source_preparation` (temporary file, text-layer-or-block rule, `prepared.recognised_text`) | done (`a3e63adf`); tests pending |
| `runs/executor.py` wiring (outside the grant, pre-authorised) | done (`48a5797d`); DB test pending |
| DB/S3 tests on the lane stack | pending |
| precision measurement on the owner's export (counts only, scratch script) | done; recorded in section 4 at the end; heuristics tuned twice (decisions 7, 8) |
| mutation proofs | pending |
| light acceptance | pending |
| final report sections 2 to 6, stack teardown | pending |

## 1. Design decisions (made while writing; each is open to the integrator's veto)

Each decision names the alternative rejected.

1. **Manifest roles are the dotted contract roles.** The brief says the manifest spells the two bundle roles with an underscore; the tree says
   otherwise: `documents.models.MANIFEST_ROLE_MARKDOWN` and `MANIFEST_ROLE_STRUCTURED_COMPANION` are read from the stage registry and are
   `source.markdown` and `source.structured_companion`. The underscore spelling (`source_markdown`, `source_structured_companion`) is the
   **blob** role on the object. The executor therefore looks the entries up by the contract role, exactly as it already does for
   `source.document`.

2. **An own markdown reader, held equal to INGEST's by a test.** `analysis/recognised/markdown.py` restates the grammar INGEST counts
   `recognised_character_count` by (the block header, the `## Page N` heading, the `> **Key:**` quote lines, the trimming of blank lines, a
   trailing carriage return dropped per line). Rejected: importing `ingest.bundle_envelope` (a deep import across bounded contexts, ALR-05) and
   exporting INGEST's private parser through `ingest.public` (outside the grant, and it would bind analysis to ingest's internals). A test
   runs both over every committed bundle and requires the same character count per block.
3. **The stage re-checks the two members cheaply, and only what it reads.** The block list: strict UTF-8 JSON, a `pages` list as long as the
   PDF's page count, and per block a `blk_<32hex>` id (unique), a type of the three and a page index on a page of the PDF. The markdown: UTF-8,
   and the both-way agreement INGEST enforces at upload. Each refusal is `analysis_input_invalid` with its own `reason`
   (`portal_blocks_invalid`, `portal_blocks_page_mismatch`, `recognised_markdown_invalid`, `recognised_markdown_mismatch`). Rejected:
   re-running the whole pinned block-list schema (INGEST's at upload; the boxes and polygons are GEOMETRY's to normalise).
4. **Both members or neither.** A markdown without a block list, or the reverse, is refused (`portal_inputs_incomplete`); a member the store
   cannot hand back is `portal_input_unreadable`. Rejected: applying the text-layer-or-block rule from the block list alone and skipping the
   artifact (a silent half-bundle).
5. **The flag vocabulary** (open, lowercase snake_case, in this order): `mixed_script`, `homoglyph`, `cjk`, `doubled_list_marker`,
   `degenerate_instruction_echo`, `degenerate_first_person_plan`, `degenerate_page_narration`, `degenerate_serialised_payload`, `empty_text`.
   Definitions are in `flags.py`'s docstring. Flags are computed on an NFC copy; the stored text is not normalised.
6. **One flag per degeneracy signal**, `degenerate_<signal value>`, derived from `norms.public.DegeneracySignal` so a signal the norms context
   adds becomes a flag instead of a crash (a test pins today's four). Rejected: a single `degenerate` flag (it loses which of four different
   failures it was). `norms.public` gained one import line (`DegeneracySignal`, `inspect as inspect_degeneracy`) and its two `__all__` names.
7. **`homoglyph` reads within a word both ways, and a whole word one way.** Within a word: the minority script's letters are all look-alikes
   of the other script (`Уровeнь`; the reverse, `Systеm`). A whole word: a Latin word whose letters are all look-alikes, between Cyrillic words
   on its line (`c` for `с`, `600x600`). The mirror whole-word rule (a Cyrillic look-alike word between Latin words) was written, measured on
   the owner's export, raised 7 flags that were all false (the PDF's own text layer held each word) and nothing true, and was removed.
8. **The designation exemption is one pinned pattern (`flags.DESIGNATION`), narrowed by measurement.** It matches `1.A`, `B25`, `A500C`,
   `REI 150`, `СП 7-АР` and their kind (its docstring lists what it matches and deliberately does not). The first version also matched one
   capital and one digit (`C0`, `B1`); on the owner's export that hid 16 words, none of which the PDF's text layer holds (hazard classes written
   with a Latin look-alike: real substitutions), and suppressed no false flag. A single capital now needs a number of two digits or more.
   Rejected: dropping the exemption (the brief requires it) and widening it to every capital-and-digit code.
9. **An empty body is an entry with `text: ""`**; a TEXT one carries `empty_text`. Section 4.8 says one entry per TEXT or IMAGE block the
   markdown holds, so the block is not dropped. The wire's `PortalRecognisedText.text` and `portal_description` are `minLength: 1`, so the
   joiner (GEOMETRY / the blocks adapter) must leave the member out for an empty entry: recorded for the integrator (section 5).
10. **The PDF goes to a temporary file through `open_stream`.** `inspect()` gives the recorded SHA-256 and size; `open_stream(...)` (a whole
    read) hashes while it streams and withholds the last chunk unless the digest is the recorded one -- the comparison `read(verify=True)`
    made. The file is `tempfile.mkstemp` in the process's temporary directory, removed in `finally` (success or failure). Rejected: `read()`
    then write (the bytes would still be whole in memory) and `NamedTemporaryFile(delete=True)` (the extractor reopens the file by its path).
11. **`extract_document` takes bytes or a path (`PdfSource`).** For a path, `pypdf` gets an open file object (given a path, `PdfReader` would
    read the whole file into memory) and `pdfplumber` opens the path itself. Neither is `pypdfium2` (pdfplumber imports it only for
    `to_image()`, which nothing here calls), so `PDFIUM_LOCK` is not taken; a test proves no PDFium document is opened during the stage.
    The bytes form is unchanged for its callers (`page_geometry_extraction` and four tests).
12. **Metrics.** Three new names, emitted only for a bundle: `recognised_entry_count`, `recognised_flagged_entry_count`,
    `pages_without_text_layer`. No existing metric is renamed. Rejected: emitting zeros for a version without a bundle (zero entries and no
    bundle would read the same).
13. **The refusal keeps its field and constraint** (`page_number`, `every page must carry extractable embedded text`); the message gains
    "and no portal block". `has_text_layer` is `char_count > 0`.
14. **The executor** seeds `outputs.refs` with every manifest entry whose role is `source.markdown` or `source.structured_companion` and adds
    both roles to `source_preparation`'s tuple (absent roles are simply not supplied). `page_geometry_extraction` is not wired (GEOMETRY's).
15. **`analysis.public`** exports `ROLE_RECOGNISED_TEXT`, `ROLE_SOURCE_MARKDOWN`, `ROLE_SOURCE_STRUCTURED_COMPANION` (in the existing
    `ports.artifacts` import) and `KIND_RECOGNISED_TEXT`, `KIND_PORTAL_DESCRIPTION`, `QUOTE_SOURCE_RECOGNISED` (one line after BUDGET's); nothing
    reordered.

(Further decisions are appended below as they are made.)

## 2. Checks, and how each new test was shown to fail

Pending.

## 3. Contracts

Pending.

## 4. Risks and limitations

Pending.

## 5. Integrator instructions

Pending.

## 6. Containment

Pending.
