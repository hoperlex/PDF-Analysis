# Fork roadmap: the work after the first install

This file is the work queue of a **fork** of this repository: the product on its own server. Read it after `AGENTS.md` and before
`docs/program/CURRENT_STATE.md`, which describes the parent's state, not the fork's.

## Where the fork starts

- **Fork with all branches.** While the parent's `main` predates the installer (`R-158i`), uncheck «Copy the main branch only» when
  forking, `git checkout dev` in the clone, and install from there. The local deploy never moves the server backwards: it waits until
  the fork's `main` is moved past what runs.

- **The server:** 32 GB RAM, 12 CPU cores, no GPU, at least 200 GB SSD. The development clone and the production checkout
  (`/srv/<instance>`) share one disk (`R-156b`…`R-156e`).
- **The install is one command,** `infra/deploy/first-install.sh` (`infra/deploy/README.md`, `infra/deploy/FIRST-INSTALL-PROMPT.md`).
  - It brings up PostgreSQL 17.11 with pgvector 0.8.6, MinIO, api, worker, web, nginx and `norm-embed`.
  - It imports the norms bundle from the public release named in `infra/norms/bundle-release.lock` (`R-158g`).
  - It turns the semantic norm lookup on after its gates and connects «Этот сервер».
  - It sets up how the fork deploys: a timer on the server pulls `main` within five minutes (`--deploy-mode local`, the default,
    `R-158h`; the owner sets the repository variable `DEPLOY_MODE=local`); `--deploy-mode github` prints the GitHub values instead
    (`R-158f`; `DEPLOYMENT_RUNBOOK.md` section 3).
- **Decisions in force:**
  - `docs/program/OWNER_RULINGS_2026-09-17.md` sections 3.57–3.64: `R-156b`…`R-156o`, `R-157i`…`R-157l`, `R-158f`, `R-158g`;
  - the fork bullets of `ADR-0020` decision 7, `ADR-0021` section 11 and decision 1, `ADR-0022`, `ADR-0006`, and `ADR-0029`
    decisions 4, 8 and 14.
- **The embedding profile for the beta is `bge-m3-dense-v1`** (BGE-M3 F32, 1024 dimensions, `R-156o`). There is no new profile, no migration and no
  corpus rebuild. A larger model is a decision after the beta.

## The order

| Task | Outcome | Depends on |
|---|---|---|
| `FORK-L0-MEASURE` | Measured memory and CPU per service under a 500-page run; embedder p95 alone and beside LLM workers; final limits | the install |
| `FORK-LS3-OBJECT-STORAGE` | Objects move from MinIO to Yandex Object Storage | `FORK-L0-MEASURE` |
| `FORK-L5-PG-TUNING` | PostgreSQL tuned for 32 GB; memory limits from L0 | `FORK-L0-MEASURE` |
| `FORK-L8-PRECEDENT-SEARCH` | Exact precedent scan made cheap: `halfvec(1024)`, the 24-month window in SQL | `FORK-L0-MEASURE` |
| `FORK-L2-RESIDENT-EMBEDDER` | A resident BGE-M3 F32 embedder replaces `norm-embed` and the night encoder | `FORK-L0-MEASURE` |
| `FORK-L3-PRECEDENTS-ON-THE-FLY` | Precedent vectors at decision and run time; the night window removed; critic examples for every observation | `FORK-L2-RESIDENT-EMBEDDER`, `FORK-L8-PRECEDENT-SEARCH` |
| `FORK-L6-OFFDISK-BACKUPS` | Encrypted off-disk copies with a restore drill | the owner's decision; **due before the first client data** |

- LS3, L5 and L8 run in parallel. L8 owns the migration head during its wave.
- L3 comes after L8 because both touch `src/auditmanager/precedents/vectors/intents.py`.

## Memory budget (a thesis; FORK-L0-MEASURE replaces it with measured figures)

| Consumer | Limit |
|---|---|
| OS, docker, journald, sshd | 1.5 GB |
| PostgreSQL | 6 GB (`shared_buffers` 3 GB) |
| MinIO (until LS3) | 1 GB |
| api / worker | 1.5 GB / 2.5 GB |
| web + proxy | 0.75 GB |
| embedder (after L2) | 4 GB hard, at most 8 of 12 cores, `oom_score_adj` 1000 |
| image builds at deploy | 3 GB |
| development on the same host | 5 GB |
| page cache | the rest |

## Latency targets (FORK-L0-MEASURE checks them)

| Operation | Target |
|---|---|
| A norm query (up to 128 tokens) | p95 ≤ 0.5 s |
| A finding view (up to 512 tokens) | p95 ≤ 2 s |
| A run of 150 findings and 300 norm queries | ≤ 5 min, beside LLM workers |
| A precedent pass at 240,000 cases in one section | ≤ 30 s |

## Open decisions of the fork's owner (ask by poll, `AGENTS.md` section 7.2)

| Question | When |
|---|---|
| The Yandex region, bucket name and cloud account | at the start of `FORK-LS3-OBJECT-STORAGE` |
| The off-disk backup target | before the first client data (`R-156i`) |
| Who is the fork's release integrator for `main` | before the first `main` publication |
| The embedding model after the beta | after the beta |

## Rules that matter most here

- A push to `main` is a deployment.
- Secrets live only in `infra/deploy/env/*.env` on the server.
- Nothing is put by hand into `/srv/<instance>`.
- One heavy run at a time; measure disk and RAM first.
- Never stop processes by name; stop them by confirmed PID.
- A full `make gate` runs only on the owner's direct order.
