# CFB-INT-DEV-PUBLISH-67 — W54 session repair commands

The published development predecessor is
`ec41bb5881b2e677af7f22af62266818f37b2a61` (dev66). One reviewed source task
is integrated: `W54-SESSION-REPAIR-01` (`a47de562`, `fa514ea3`, `50a26daf`).

## Result and checks

- `repair session-prepare` and `repair session-ledger` let the 121 degenerate
  W54 blocks be re-read in a Claude Code session under `R-137`. They keep the
  page set, crop custody, fixed prompt, two-read rule and version-2 ledger.
  The ignored ledger built with them holds 121 applied repairs and no
  unreliable block; see `W54-SESSION-REPAIR-01.md`.
- An independent read-only review found no path that changes the rule's
  outcome. Its seven weaker points were fixed, each new guard shown failing
  under a mutation.
- `test_session_repair.py` **43 passed**. The focused norms suite **793
  passed**; its excluded database, search-window and corpus-symlink cases
  need resources this lane lacks and fail identically on dev66.
- Prose facts, programme governance and ALR-05: **74 passed**. This includes
  `CurrentStateTest`, red on dev66 because the live state had grown to 209
  lines. The live state is now 97 lines, and the dev66 version is archived
  byte for byte at `history/CURRENT_STATE_2026-10-19_ec41bb58.md`.
- `compileall`, `git diff --check` and task governance passed; `ruff` is not
  installed on this host. R-135 defers the complete beta `make gate`.

## Boundaries

No contract, migration, root dependency, composition root, global style,
served API/UI, provider, production corpus, DB/S3, deployment workflow,
`origin/main` or tag changed. The repaired snapshot, embeddings, bundle and
any stand import have not run: host disk and RAM are below the W54 floors,
and the owner has still to decide how to treat the two single-word deviations the
spot check found. No beta or live service acceptance is claimed.
