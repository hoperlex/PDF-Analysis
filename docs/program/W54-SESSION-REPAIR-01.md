# W54-SESSION-REPAIR-01 — the 121 degenerate blocks re-read in session

**Date:** 2026-10-19. **Base:** `origin/dev` `ec41bb5881b2e677af7f22af62266818f37b2a61`
(dev66). **Task:** `tasks/W54-SESSION-REPAIR-01.md`. **Ruling:** `R-137`.

## Result

All 121 W54 blocks whose corpus text was the recognition model's own reasoning
now have a session transcription, judged by the unchanged `rerecognise()`
rule. The repair ledger holds **121 repairs: 121 applied, 0 unreliable,
121 unpriced attempts**. It names the frozen base snapshot
`2026-07-23..2026-08-20+17d.4b74348debf7` and the verified sums
`eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`. The
repaired snapshot key is `2026-07-23..2026-08-20+17d+121r.0a1bafe103ff`.
`corpus_source._validated_ledger` accepted every row against the real drop:
54 documents, 121 blocks, 325,883 replacement characters. No proxy call,
charge, credential, database or S3 object was used.

Ignored artifacts, under `/root/projects/PDF-Analysis/.local/norms/repairs/`:

| Artifact | SHA-256 |
| --- | --- |
| `session-20261019/session.json` (121 pages, 150 dpi) | `25c690b2537f801a47c1de23aa5b6c2dd98dd406b634a205badbae64c3c96e14` |
| `session-20261019/prompt.txt` (= `RECOGNITION_SYSTEM_PROMPT`) | `ab9d02375ae6a5f8011942a8ff72235e7170ff89e1d60f9554fc842508a5357e` |
| `session-20261019/ledger.json` | `9639ce91c1605db8c2b0e9bfe5ae0f1ee858a76481f2308aed1f087efcd3c833` |
| `session-20261019/answers.log` (121 judged reads) | `bdcd7f773c6b060fb257fbd7cc3e837d8973ae563c5b34e5b5ec63c2697eb342` |
| `session-20261019.brief.md` (the readers' operational brief) | `d8da1a304b5d292582080ac2b26f2f9046a79afc3f5221fa7d2158bf8ecee55e` |
| `session-20261019.batches.json` | `2a1693e4c7d8f4f2d0ff904bfbae9c8f53ad271ef9c55917f8eb3d621728aa66` |
| `session-20261019.qa-sample.json` | `c979124116ece01276923ea54bffd888d88e623aceb2eca3a607bd4be6c4f421` |
| `session-20261019.transcripts/SHA256SUMS` (14 subagent transcripts) | `e99dcaa26d2066c9bc949f1fb56064ee3c367fa645b4bf9edb4b649dad86f196` |

## How the text was produced

`repair session-prepare` checked the 121 crops against the sums, rendered
each at 150 dpi and wrote the pages, the prompt and `session.json`. Ten
Sonnet subagents read 12–13 pages each with the Read tool and wrote one
answer per page with the Write tool, under the fixed prompt plus the saved
brief. Two readers mis-copied one block id each and skipped it; two
single-page readers then read those blocks. One reader rewrote its own fresh
answer once, before hand-back and before any ledger run, to fix its own
Latin-script typo. Answers were written between 08:05 and 08:11 UTC. Every
assistant turn in the 12 reader transcripts reports `claude-sonnet-5-5`
(426 turns). No first answer was degenerate, so no second read was owed.

`repair session-ledger` re-checked the drop, sums, prompt, resolution, each
page image and a fresh rendering of each crop, then replayed the answers.
The final run logged all 121 judged answers in `answers.log`. A first ledger
run, made before the review fixes, produced byte-identical repairs.

## Independent checks

**Code review** (read-only subagent, commit `a47de562`) found no path that
yields repairs different from the rule's for the answers present. It found
seven weaker points, all fixed in `fa514ea3`. A changed answer could replace a
judged read between runs; `answers.log` now refuses that. The ledger step did
not bind the resolution or re-render crops. Symlinked answers and a
duplicated block were accepted. The model pattern was loose, a malformed
session crashed, and the task named a wrong test path. Each new guard was
shown failing under a quoted mutation: removed log check, log append,
re-render, dpi check, symlink check, ledger-side uniqueness, loose model
pattern and malformed-JSON handling each turned at least one test red.

**Transcription spot check.** Two Opus subagents compared 16 pages with their
images: 11 risk-weighted pages that readers had flagged, plus 5 random pages
(seed 137). The integrator confirmed both content findings on the images:

| Block | Page | Finding |
| --- | --- | --- |
| `blk_4da232ee4f874711be7c5f8dabd772e5` | СП 131.13330.2025, p. 292, map | label "Амдерма" transcribed as "Надым" |
| `blk_786d7fb926ed4dceabe7f983da1d0033` | СП 253.1325800.2016, p. 66 | printed "гидроскопичны" silently corrected to "гигроскопичны" |
| `blk_67a164266f7940d8b65f8a9cf44425ad` | СП 345.1325800.2017, p. 66 | first data row used as the markdown table header (values intact) |
| `blk_f03ef452f0b84e7e82b2c89ff0afdf38` | СП 131.13330.2025, p. 90 | the same header-row layout (values intact) |

The other 12 pages matched value by value, including a 23-column flange table,
a 12-row steel table rebuilt from misaligned spans and every formula checked.
The printed "оневым" was confirmed as printed. Formula notation varies by
reader (LaTeX or plain text with `_`); Latin/Cyrillic look-alikes could not
always be told apart. The rule has no outcome for an inaccurate but
non-degenerate answer, so both content findings stand as `REPAIRED`. Each
replaces the page text that was entirely the model's narration. Whether to
verify all 121 pages, and how a confirmed correction would be recorded, is
an owner decision; this task does not invent a correction path.

## Checks

- `tests/integration/norms/repair/test_session_repair.py` — **43 passed**.
- Focused norms suite, `-k "not postgres"`, without `custody/test_two_phase_custody.py`,
  `search/` and two environment-bound cases — **793 passed**. The excluded search
  windows and catalogue DB/S3 case need `DATABASE_URL`; the bake-off fixture
  needs the corpus symlinked into the worktree. They fail identically on dev66.
- `tests/contract/program` and `tests/contract/architecture/test_alr05_boundaries.py`
  — 29 passed, 1 failed: `CurrentStateTest` (the live state is 209 lines,
  limit 120). It fails identically on dev66; the integration task repairs it.
- `compileall`, `git diff --check`, task `governance_findings` = `[]`.
  `ruff` is not installed in any environment on this host and was not run.

## Contracts, limits and next steps

No API, domain, event, error or stage contract, migration, dependency,
composition root, global style, journal, pricing or ledger format changed.
The two `repair session-*` commands and `R-137` are the only additions.

The next W54 steps take this ledger unchanged: load the repaired snapshot
with `characters-v2:1200`, build and load the BGE-M3 embeddings, then export
and verify the bundle. They are blocked by host capacity, not code. On
2026-10-19 the host had **6.4 GB free disk** and **4.2 GB available RAM**,
against W54 §3.9's step increment plus 3 GiB reserve and 6 GiB RAM floor. The
`norms-worker` image has never been built; its BGE-M3 model files alone
are about 2.3 GB. Production import (`W55-PLAN.md` §A7) remains a separate
owner-scheduled operation.

Revert `a47de562` and `fa514ea3` to remove the commands. Delete the ignored
session directory to discard the transcription.
