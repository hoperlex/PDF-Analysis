# W30-CERT3 — PA-01 re-certified at `ac7c348`

- **Task:** `W30-CERT3`. Re-certify `PA-01` against the tree at `ac7c348`.
- **Record:** `artifacts/checkpoints/PA-01/certification-ac7c348.json`, superseding `certification-16d3503.json`.
- **Worktree:** `/root/w30cert3`, branch `agent/w30-cert3`, head on arrival `ac7c348`.
- **Logs:** `/root/w30-logs/cert3-*`. Harnesses: `/root/w30-logs/cert3-drive/`. Browser journals: `/root/w30-logs/cert3-browser/`.
- **This session wrote two files and no code.** It repaired nothing it found.

## 1. The answer

**Eight of ten hold, one of those with a named exception. Two cannot be established. None
failed.**

| | 16d3503 | ac7c348 | |
|---|---|---|---|
| 1 deploy from a clean clone + served schema conforms | cannot be established | **cannot be established** | R-1 |
| 2 TLS + no token refused by the application | cannot be established | **cannot be established** | R-1 |
| 3 project, upload, immutable version, private object | holds | **holds** | |
| 4 live run, provider mode + cost visible, four states | holds | **holds** | re-driven; the `failed` screen changed |
| 5 finding opens at its exact quotation beside its page | holds | **holds** | |
| 6 accept, reject, later comment, history shows all three | holds | **holds** | |
| 7 CSV through the browser, resolving back | holds | **holds** | |
| 8 restart and everything survives | holds w/ exception | **holds w/ exception** | **the exception's reason was false and is replaced** |
| 9 five typed refusals + a provider outage fails the run | holds | **holds** | **re-established against a narrowed category** |
| 10 reset dumps, wipes, re-initialises; the dump restores | holds w/ exception | **holds** | **exception repaired by W26-OPS** |

Criteria were read from `docs/program/ALPHA_ROADMAP.md` §5, not from the dispatch. Where the
brief and the roadmap could have disagreed they did not: criterion 1's second clause is the
**API schema** conforming to the frozen contract, exactly as the brief said and exactly as the
file says.

## 2. Two stacks, and which reading came from which

There is one alpha stand on this host and it is the owner's. It was never reset, wiped,
stopped, restarted or removed. What it received is additive product data — a project, a
document, runs, decisions — which is what driving it by hand produces anyway.

- **`auditmanager-w19a`, `http://127.0.0.1:31500`, the owner's stand.** Criterion 1's
  served-schema comparison, criterion 2's fifteen-operation probe, the certified live journey
  behind criteria 3–7, and criterion 9's five refusals.
- **`auditmanager-w30cert3`, `http://127.0.0.1:31560`, built by `deploy.sh` from
  `/root/w30cert3`.** Everything that changes provider configuration or destroys data:
  criterion 4's `partial`, criterion 8's container destruction, criterion 9's outage and its
  control, criterion 10's whole wipe-and-restore cycle.

`verify-deployed.sh` exits 0 on both: 141 `src/`, 9 `db/`, 34 `contracts/`, 223 `web/` and the
rest byte-identical to their trees.

## 3. The verdict that moved: criterion 10

`16d3503` recorded `holds with a named exception` — `W24CERT2-2`, the rehearsal's **total**
counting `finding_current_verdict`, a view, alongside the base tables. **That was repaired
before this commit**, by `W26-OPS`'s `a228e46`, with `4169a3e` adding the arithmetic test
against a real PostgreSQL. The rehearsal at `ac7c348` prints:

```
  total: 133 rows in 16 base tables (and 1 view listed above, projecting rows already in that number)
```

and the view is annotated inline as `(7 rows, view: these rows are counted above)`. The
sixteen base-table counts sum to exactly 133, checked by hand, and every per-table figure
equals the independent census taken through `psql`. The exception is gone.

The rest of the criterion was re-driven rather than inherited: five guard refusals each
exit 3 read from `$?` after a redirect (including a foreign-database refusal where the foreign
name used was `auditmanager_alpha`, **the owner's stand's database** — the guard refused it);
the destructive cycle dumping and verifying before dropping; the app **empty and working in
the same api process**, proved by an unchanged container id and `RestartCount=0` with
`StartedAt` 12:29:09Z against a wipe at 12:30:39Z; and a restore whose census is identical
byte for byte to the pre-wipe census, with a re-upload of the same bytes returning 201.

## 4. The exception whose reason was false: criterion 8

`16d3503` said a host reboot was off the table because *"the host carries three alpha stacks
and other lanes' services"*. **`docker ps` now shows one alpha stand.** The other two were
removed under ruling `R-6`. The sentence on record no longer describes this host, and a
certification that repeats a false reason is worse than one that names the real limit.

The real limit, measured:

1. the host carries the owner's stand, which the owner drives by hand;
2. a second live session (`W30-LISTS`) and another lane's `gate-b0` containers were running
   throughout, and a reboot takes both down mid-measurement;
3. **the certifying session itself runs on this host.** A reboot terminates the process that
   would have to observe the result. A session cannot witness its own reboot.

(3) is structural. No scheduling removes it; a host reboot has to be driven by the owner, or
by an agent on a host it is not itself running on.

What *was* driven is stronger than what `16d3503` drove. Not a service restart: `docker
compose down` **without** `-v`, so all five containers were destroyed — zero remained, the two
named volumes survived — and then `deploy.sh` brought the stack back with five new container
ids. A 73-line census through PostgreSQL and MinIO, taken before and after, **diffs to
nothing**: 5 runs covering published/failed/partial and both provider modes, 5 versions, 9
decision events, 2 blobs, 30 objects, 133 rows in 16 tables. Every screen then loads cold in a
fresh browser process, 200 each, every `/bff/v1` call 200.

## 5. Criterion 9, which is the one the brief was right to send me at

### What a provider outage is at this commit

`W29-RETRY` moved the boundary, so the category was established from the tree rather than
assumed. Searching **both spellings** (`DEPENDENCY_UNAVAILABLE` and `dependency_unavailable`,
§12's own rule), the code survives on the provider path in exactly four places, all in
`src/auditmanager/analysis/text/`:

| Site | Condition |
|---|---|
| `proxy.py` `URLError` branch | the model proxy could not be reached |
| `proxy.py` 429/503 | saturated; the call was not made |
| `proxy.py` 504 | the proxy exceeded its deadline |
| `live.py` `_map_provider_failure` | the SDK failed on the wire |

All four are real transport conditions where a second attempt can answer differently — which
is what `runs/retry.py` says the code means. What `W29-RETRY` **removed** is two deterministic
local conditions: an absent recording file and an unimportable pinned SDK.

### Both halves, driven two minutes apart on the same stack

| | outage | control |
|---|---|---|
| how | `PROXY_LLM_BASE_URL` → `127.0.0.1:59999` inside the api container | `recorded` mode, a document with no recording |
| run | `run_01M31YS6395T63STZDSQ7BCAZ7` | `run_01M31YXSTXK7VQF4C9F4FWFTJ6` |
| badge | queued → running → **failed** at 16.6 s | running → **failed** at 2.2 s |
| terminal reason | `dependency_unavailable` | `analysis_input_invalid` |
| `text_analysis` took | **10.0 s** — three attempts and both pinned backoffs | **9 ms** — no ladder |

Nothing was published in either case; the review pane reads *"There is nothing to review."*
Before `W29-RETRY` the right-hand column would have reported the left-hand column's code and
bought the left-hand column's ten seconds. The repair reaches the deployed screen, and
criterion 9's second clause is now about a narrower and truer category than it was.

### What `W29-SAY` changed in that reading

The failed screen no longer stops at the identifier. Beneath `Terminal reason:
dependency_unavailable` it renders the sentence from
`web/src/entities/audit-run/model/terminal-reason.ts`, read verbatim out of the browser — and
the load-bearing part is what it refuses to say: *"this reading does not record which of them
it was — so on its own it is not evidence that the model provider is down."* Which is exactly
right for the control above, where the provider was healthy and the file was missing. The
`analysis_input_invalid` run renders its own different sentence.

### The five refusals

Five fixtures, five **distinct** constraints, `curl` through the owner's stand's nginx origin:
`pdf_magic_bytes`, `not_encrypted`, `every_page_has_extractable_text`,
`1 <= page_count <= 30`, `max_bytes`. Each a 422 with the application's typed envelope, its own
correlation id and `retryable: false`. Afterwards the project they were uploaded to lists
**zero** documents: nothing half-created survived a refusal.

## 6. Criteria 1 and 2 — one line each, as instructed

- **1** — blocked on `R-1`: no machine here has never run this stack, and there is no previous
  version on a server to roll back to. Its second clause **holds**: frozen ops 15, served ops
  15, **0 differences**, over HTTP against the running process, with a planted difference
  proving the comparison can fail.
- **2** — blocked on `R-1`: `nginx.conf` has one `listen 8080;`, `infra/deploy/proxy/tls/` is
  empty, so `W26-HOST`'s TLS path is present and inert. Its second clause **holds**: 15 of 15
  operations answer `401 authentication_required` on both an absent and a wrong credential,
  from the application — proved by the typed envelope, the minted correlation id, and the
  identical refusal reached with the proxy bypassed **inside** the api container.

## 7. Findings — proposed register rows

The register is the integrator's file and a forbidden hotspot here. These are proposals, each
with the command a later session re-runs.

### `W30CERT3-1` — the published origin has a second, credential-free path to all fifteen operations

`/api/v1` is behind the token. `/bff/v1` is in front of it: `web/src/app/bff/v1/[...path]/route.ts`
is a catch-all that holds `T-6`'s credential server-side and forwards every operation, and
nginx routes `/bff/v1` to it under `location /`. Measured on this session's own stack:

```
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:31560/bff/v1/projects \
  -H 'Content-Type: application/json' -H "Idempotency-Key: probe-$(date +%s)" \
  -d '{"name":"no credential"}'
-> 201
```

**This is the designed posture**, not a bug: the browser must carry no credential, both stacks
bind to `127.0.0.1`, and every screen says *"Local prototype. One reviewer, no authentication,
no tenancy."* It does not make criterion 2 fail — criterion 2's clause is about the
application's refusal, and that holds. It is recorded because the criterion's **stated
purpose** is *"the dependency is proved to be in front of all twelve rather than in front of
the one that was tried"*, and on the published origin the dependency is in front of `/api/v1`
and not in front of `/bff/v1`. `16d3503` probed `/api/v1` only and called the clause *"wider
than the criterion asks"*. The day `R-1`'s host makes this origin public, this becomes an
unauthenticated public write surface that can spend provider money.

**Check:** the curl above, and `grep -n "location" infra/deploy/proxy/nginx.conf`.

### `W30CERT3-2` — a character range printed for a reviewer that no second tool can resolve

The review screen prints `page 2, characters 707–746 of the whole document, not of page 2`.
The offsets are internally consistent — `746-707 = 39` and the quotation is 39 characters;
`2658-2618 = 40` and the second is 40 — but `pdfminer` puts the same strings at 726 and 2700.
The drift is 19 after one page boundary and 82 after five, i.e. it grows with boundaries
crossed: per-page whitespace differing between two extractors, not an error in either.

The consequence is the finding. `W21-CERT`'s repair fixed the coordinate **confusion** — it
stopped printing a document-global offset beside a page number as though they shared a system —
and left the coordinate **system** unnamed. A reviewer told *"characters 707–746 of the whole
document"* has no tool that can check it. The criterion is unaffected: the quotation is exact
and occurs exactly once, on the page named, both confirmed with an extractor the application
does not use.

**Check:** `/root/w30-logs/cert3-drive/quote_check.py` against the version bytes, and
`/root/w30-logs/cert3-offsets.log`.

### `W30CERT3-3` — criterion 8 cannot reach a host reboot from inside the host

Not a code defect; a standing certification limit, recorded because the reason previously on
record was false. See §4.

**Check:** `docker ps --format '{{.Names}}'` — one alpha stand, not three.

### `W30CERT3-4` — `CURRENT_STATE.md` does not survive contact with the tree it points at

`AGENTS.md` §1.1 makes it the first thing every agent reads, and the integrator asked for this
check explicitly. Three statements in the 2026-09-21 block are wrong at `ac7c348`:

1. *"Criterion 10's is replaced by a smaller one — the rehearsal's … total counts a view"*.
   Repaired by `a228e46`, which is **inside** the range the document describes.
2. *"`verify-deployed.sh` exits 0 and prints 'the deployed stack IS this tree (ac7c348)'"*.
   It prints `(2fdb12c)` — see §8. The file-by-file figures beside it are exactly right.
3. The `PA-01` section heads with `certification-0f9989a.json` and only mentions the
   superseding `16d3503` record in the following paragraph.

The correction it *did* make — eight criteria to ten, by counting the record's keys — is right,
and the count is right.

**Check:** `git log --oneline 16d3503..ac7c348 -- infra/deploy/reset.sh` shows `a228e46`; and
`infra/deploy/verify-deployed.sh --env-file <the alpha env> --repo /root/projects/PDF-Analysis`.

## 8. Premises in the dispatch brief that I measured and found false

**1. "The mechanism the previous certification used to induce an outage may no longer induce
one." — FALSE, and it is the brief's headline.** It still induces one. `W29-RETRY` changed
`recorded.py` and `live.py`; the previous certification's mechanism — an unreachable
`PROXY_LLM_BASE_URL` — goes through `proxy.py`'s `URLError` branch, which `W29-RETRY` did not
touch and which still raises `dependency_unavailable`. Driven: badge `failed`, terminal reason
`dependency_unavailable`, `text_analysis` 10.0 s.

The brief's *instruction* was still the right one. Establishing what an outage is produced the
control reading in §5, and criterion 9 is worth more at `ac7c348` than it was at `16d3503`
because of it.

**2. "`verify-deployed.sh` exits 0 with `the deployed stack IS this tree (ac7c348)`." — FALSE
as stated.** It exits 0 and prints `(2fdb12c)`. The script names the repository's current
**working tree**, which its own header says is what it compares against, and the integrator's
line has moved past `ac7c348`. The substance survives: `git diff --stat ac7c348 2fdb12c` is
seven files, **all under `docs/program/`**, so every directory the script compares is
byte-identical between the two. **The script is not at fault** — it prints the sha "for the
record", as line 55 says. The brief read a parenthesised sha as a verification target, and it
inherited that sentence from `CURRENT_STATE.md` (`W30CERT3-4`).

**3. The brief assigned a log prefix and no gate lane. — INCOMPLETE**, corrected by the
integrator mid-session. `.env` is git-ignored, so this worktree had none, and `.env.example`
carries the `FOUNDATION_INSTANCE`, ports and database that the concurrently live `W30-LISTS`
session and the `gate-b0` containers were already using. The lane `gate-w30a` / 56060 / 59660 /
59661 / `audit_w30a` was set before anything measured.

**4. One of my own probes was wrong, and saying so is the point.** I tried to reproduce
`deploy.sh`'s placeholder-secret refusal by setting `AUDITMANAGER_API_TOKEN=changeme`, and the
script deployed. That is the **guard working**: it compares against `alpha.env.example`'s
actual values rather than grepping for a `change-me` pattern, "because a pattern stops being
true the day somebody rewrites the example". Feeding it the example unedited refuses correctly,
exit 3, naming `POSTGRES_PASSWORD`, with zero docker lines in the log.

**What the brief got right, checked rather than assumed:** ten criteria and not eight, with
exactly the verdicts it listed; 12 paths / 15 operations / 46 schemas; 22 codes, `frozen:
false`, `candidate_revision: 7`; migration head `0005_truncated_call_status`; criterion 1's
second clause being the API schema; and one alpha stand on the host — which is what makes
criterion 8's recorded reason stale.

## 9. Anti-vacuity

No criterion here is certified by a unit test, so there is nothing to mutate for most of them —
each was driven through the published port with `curl` or through a real Chromium process. The
one comparison **engine** used is the conformance surface, and it was shown able to fail in the
same run that produced its green: a planted `operationId` yields exactly one difference,
`paths./projects.post.operationId: the contract has "createProject", the generated document has
"plantedDifference"`. `deploy.sh`'s own twelfth guard reproduces the same 15/15/0 independently.

Two readings act as controls rather than assertions, and both are in §5: the recorded-miss run
against the outage run, and the stub-driven `partial` against the live `published`.

## 10. Costs and limits

Two paid provider calls, **USD 0.071025** against a ceiling of 1.00 — `cost_micros` 37675 on
the owner's stand and 33350 on this session's stack, both `cost_basis: measured`, one call
each. The `partial` run's 41200 micros is the **stub's** reported figure and is not money. The
outage, recorded-miss and recorded-published runs made no paid call, and the screen says so in
words rather than printing a zero.

Not driven, and stated rather than folded into a verdict: TLS and a machine that has never run
this stack (both `R-1`); a host reboot (§4); a fresh `git clone` for criterion 1's first clause
— `deploy.sh` was driven from a worktree that had never carried a stack, both of its pre-docker
refusals reproduce, and the host is at 89% disk; real documents (`R-4`); and the `/bff/v1`
probe, which was run on this session's stack only.

## 11. Gate

Run once at the end, from a committed-clean tree, on lane `gate-w30a`, with the exit code read
from `$?` after a redirect and never through a pipe.

```
make gate > /root/w30-logs/cert3-gate.log 2>&1; echo "EXIT=$?" >> /root/w30-logs/cert3-gate.log
```

| | |
|---|---|
| commit | `46dfbf1` — the record and this report |
| battery | **2001 passed**, 5 skipped, 1 warning, **169 subtests** in 496.09 s |
| foundation | 35 passed in 31.64 s |
| frontend | **764 passed** across 52 files in 15.62 s |
| whitespace | clean |
| result | `GATE OK: battery, foundation, frontend and whitespace all pass` |
| exit | **0** |

**Identical, figure for figure, to the numbers the dispatch carries** — battery 2001, frontend
764 — which is what a session that adds no test and touches no `src/`, `web/`, `contracts/`,
`db/`, `tests/`, `infra/` or `Makefile` file should produce. 17:40:36 → 17:50:07 +05.

## 12. For the integrator

- Two files changed, both inside `allowed_paths`:
  `artifacts/checkpoints/PA-01/certification-ac7c348.json` and `docs/program/W30-CERT3.md`.
  `git diff --stat ac7c348..HEAD` shows those two and nothing else.
- **No contract touched.** `contracts/**`, `db/**`, `src/**`, `web/src/**`, `tests/**`,
  `infra/**`, `DEBT_REGISTER.md`, `CURRENT_STATE.md`, `Makefile` and the root
  dependency/lock files are untouched.
- Two git-ignored, untracked files were written outside version control because the
  deployment needs them and `.env`-class files are how this repository carries them:
  `/root/w30cert3/.env` (the `gate-w30a` lane the integrator supplied) and
  `/root/w30cert3/infra/deploy/env/provider.env` (a copy of the stand's, repointed during
  criterion 9 and restored). `git status --porcelain` is empty at every commit.
- **Four proposed register rows**, §7, each with its check command. `W30CERT3-4` is against
  `CURRENT_STATE.md` and is the one worth acting on first, because it is mandatory reading.
- **This session's own stack, `auditmanager-w30cert3` on 31560, is still running** and holds
  the restored census. Tear it down with
  `docker compose --env-file /root/w30-logs/cert3-drive/alpha.env -f infra/deploy/compose.server.yml down -v`
  and `docker rm -f w30cert3-stub`, plus `docker rmi auditmanager-w30cert3-api
  auditmanager-w30cert3-web` to give the host back its disk. It was left up deliberately so the
  evidence can be re-read.
- **The owner's stand on 31500 is as it was**, plus one project, one document, one live run,
  three decisions and one refusals project with zero documents. Never reset, wiped, stopped,
  restarted or removed. **One exception to "as it was", stated rather than glossed:** the
  anonymous-bucket probe for criterion 3 was copied into the stand's api container as
  `/tmp/anon_probe.py` and could not be removed afterwards — the container runs as a non-root
  user. It is a fifteen-line read-only script in a container's `/tmp` and it disappears the
  next time that container is recreated.
