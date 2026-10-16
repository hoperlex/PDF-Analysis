# W54-CORPUS-REPAIR-PLAN-01 — offline plan for the verified base

The restore-verified base dump
`promotion-20261015T134454Z.dump` has SHA-256
`e1280373ffd7fa3deaa0716429def1844d7e858e79bae7fbad5ade6d516ff74d`
and an adjacent `.verified` marker. On 2026-10-16 the unchanged source sums
file retained SHA-256
`eb5fae5cdd8d47873b23a125ebd68d5b507fda301088d2cc8651b06fd81897e5`;
`sha256sum --check --quiet` from the corpus root exited 0 for all **31,619**
listed files. The pricing module retained SHA-256
`355a21ade3a983aca202ba73c79147e79427c98ae6bcb15ac33d8ed38fdffd1c`.

The exact offline command
`PYTHONPATH=src .venv/bin/python -m auditmanager.norms repair plan --corpus
/root/projects/PDF-Analysis/.local/norms/corpus --model claude-opus-5`
exited 0 and wrote the ignored
`.local/norms/repairs/plan-20261016.json` (364 bytes, SHA-256
`045f8b636ccae1aa2503015c305575e0a9beb3349055c0aaa365b4474e573365`).
It reports `dry_run: true`, model `claude-opus-5`, **121 pages**,
base snapshot content key `2026-07-23..2026-08-20+17d.4b74348debf7`,
cumulative ceiling `$10`, maximum per-call bound `$0.224515` and
`spent_usd: 0`. Its three largest-crop sample blocks are:

1. `blk_8ef449fbee9e49d59b5ff62836ec8715`
2. `blk_5e9552f60b8c4e22bb0df238d9595223`
3. `blk_b7d1e9cd457944f3b9bd6834b15c38b9`

No database, proxy, credential or paid operation was used by this plan. The
owner selected the model, but the proxy credential file is absent on this
host. The next operation is the priced sample through the durable journal
after that file exists; it must check the sample projection and cumulative
ceiling before any full repair. The plan does not prove that 121 calls fit
inside `$10`, and it does not qualify a repaired snapshot or a DB/S3 bundle.

## Checks and ownership

The exact command exited 0, JSON parsed with the expected fields and 121-page
count, and the source-sums recheck exited 0. Direct task governance returned
`[]`; whitespace and exact path checks are recorded at the integration commit.
Only this report and its task file are tracked changes. Contracts, migration
head, application code, source corpus, promotion database/volume, paid
journal, production DB/S3, refs and tags are untouched. Repeating this
offline plan is safe against the same frozen source and model; discarding its
ignored JSON is the rollback.
