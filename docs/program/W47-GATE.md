# W47-GATE — the deploy tells you what is unsafe, and stops lying about what it checked

**task_id:** `W47-GATE` · **wave:** 47 (GO), sub-stage A · **lane:** `gate-w47a`
**worktree:** `/root/w47gate` · **branch:** `agent/w47-gate`, based on `ce60f80`

Opened before the first gate-scale measurement, per discipline. Written as the work is found,
one step at a time, and committed after each step so a session restart loses nothing.

## 0. Base and baseline

Per `docs/program/dispatch/W47-DISPATCH.md`: base `alpha-w46` (`e47d657`), local. Baseline
already measured on `1196ca7` (the gated candidate; `e47d657` changes only docs): `GATE OK`,
battery 2516 passed / 5 skipped, foundation 35, frontend 1135 in 80 files
(`/root/w46-final-gate.log`). **Not re-taken here.** Final counts below are accounted against
these by test id / delta.

## 1. G3 — `D-103`: the placeholder guard reads four names, the secrets are written seven times

**Before.** `infra/deploy/deploy.sh`'s `placeholder-secrets` guard (line ~227 at dispatch)
compares exactly `POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD`, `MINIO_ROOT_USER` and
`AUDITMANAGER_API_TOKEN` against `alpha.env.example`'s own values. `alpha.env.example` embeds
three of those four a second time: inside `DATABASE_URL` (user + password), `S3_ACCESS_KEY_ID`
(= `MINIO_ROOT_USER`) and `S3_SECRET_ACCESS_KEY` (= `MINIO_ROOT_PASSWORD`). Rotating only the
four named guards passes `placeholder-secrets` clean, builds both images, brings the stack up,
and `api` then fails to authenticate against `postgres` (new password) using the OLD password
still embedded in `DATABASE_URL`.

**Repair.** New guard `derived-secrets-coherent`, added to `infra/deploy/deploy.sh` immediately
after `placeholder-secrets` and before `compose-file-present` — so it is one of the guards that
refuse **before docker is touched at all**. It parses `DATABASE_URL` with a bash regex (the
runbook promises this host only bash/docker/curl/sed/git, no python3, so no python is used here
unlike the `schema-conforms` guard, which runs *inside* the api image) and compares:

- `DATABASE_URL`'s user/password/database against `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB`
- `S3_ACCESS_KEY_ID` against `MINIO_ROOT_USER`
- `S3_SECRET_ACCESS_KEY` against `MINIO_ROOT_PASSWORD`

An unparseable `DATABASE_URL` is refused rather than skipped (`placeholder-secrets`'s own
principle: an unverifiable value is not a verified one). Mirrors `FF-01` §3's
`COHERENCE_PROBE` (`Makefile`), applied to the file that lacked an equivalent.

**Reproduction, driven manually before committing** (env: the four names rotated,
`DATABASE_URL`/`S3_ACCESS_KEY_ID`/`S3_SECRET_ACCESS_KEY` left at the example's placeholder
values — exactly D-103's scenario):

- *Before* (`deploy.sh` at `ce60f80`, guard absent): guard-less script proceeds straight past
  `placeholder-secrets`, calls `docker compose ... build` and `docker compose ... up -d`
  unrefused (confirmed via a docker stub that logs every call — `build` and `up` both appear in
  the call log before any refusal).
- *After* (repaired): refuses immediately, **zero docker calls logged**, naming exactly the
  three derived values:
  ```
  deploy.sh: REFUSED: DATABASE_URL, S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY must carry the same
    secrets as POSTGRES_* and MINIO_ROOT_*, and at least one does not:
      DATABASE_URL's password does not match POSTGRES_PASSWORD
      S3_ACCESS_KEY_ID does not match MINIO_ROOT_USER
      S3_SECRET_ACCESS_KEY does not match MINIO_ROOT_PASSWORD
  ```

**Also added** (G3's second half): the `"DATA, NOT CODE"` warning to `alpha.env.example` itself
(it previously lived only in the root `.env.example`, per `W45-JUDGE-X`'s finding), plus a
paragraph naming the new guard and the three derived values, next to the secrets themselves.

**Tests.** `tests/integration/composition/test_deploy_script_refusals.py`:
- `_env_text()` now derives `DATABASE_URL`/`S3_ACCESS_KEY_ID`/`S3_SECRET_ACCESS_KEY` from
  whatever secrets dict it is given (`coherent=True` default), so every pre-existing case stays
  coherent under the new guard without being rewritten by hand.
- New fixture `_d103_env_text()` — the exact reproduction (four rotated, three left stale).
- New guard `derived-secrets-coherent` added to `BEFORE_DOCKER`, picked up automatically by the
  generic "refuses and says why" / "deleting the guard removes the refusal" parametrized tests.
- New class `TestD103TheThreeDerivedValues` — the reproduction spelled out explicitly: refuses
  before any build, names all three derived mismatches, a fully-edited env is not caught
  (control), and the guard is shown able to fail (delete it, the mutant reaches `build`).
- `test_every_guard_in_the_script_has_a_case_here`: count 13 → 14.
- `tests/integration/composition/test_deploy_image_identity.py`'s own independent `_env_text()`
  (not shared with the file above — that suite says so explicitly) needed the same
  `POSTGRES_USER` + derived-values fix, or every one of its cases would now be refused by the
  new guard before reaching what it actually tests (`identity-policy-known`, the retag
  mechanism).

Run: `.venv/bin/python -m pytest tests/integration/composition/test_deploy_script_refusals.py
tests/integration/composition/test_deploy_image_identity.py -q` → **48 passed** + **23 passed**.

**Forbidden hotspots not touched**: `git diff --stat` for this step touches only
`infra/deploy/deploy.sh`, `infra/deploy/env/alpha.env.example`, and the two composition test
files — no `contracts/**`, no `db/migrations/**`, no `Makefile`, no `src/auditmanager/access/**`
other than (not yet) `check.py`, no `src/auditmanager/api/**`, no `web/**`.

## 2. G1/G2 — the publication-readiness command

New `infra/deploy/readiness.sh`. **`R-46`: it REPORTS and REGISTERS; it does not block a
deploy.** `deploy.sh` never calls it, and nothing else in this repository reads its exit
status — the only thing consuming its output is an operator (or `docs/program/
DEPLOYMENT_RUNBOOK.md` §9, which now documents it) reading a corpus of `readiness OK` /
`readiness FINDING` / `readiness UNKNOWN` lines.

**Six checks, marked `# >>> check: <name>` / `# <<< check: <name>` the same way `deploy.sh`
marks its guards**, none re-deriving a question this tree already answers:

1. **`default-credential`** (step 5, G2). Runs `src/auditmanager/access/check.py` **inside
   the deployed api image**, exactly the way `deploy.sh`'s `migrations-at-head` guard runs
   `shared.db.check`, and reads its already-existing stable sentinels
   (`access-check OK no default credentials` / `access-check DEFAULT CREDENTIAL`) rather
   than asking the question a second time. `check.py` itself was **not** modified — its
   sentinels already sufficed.
2. **`tls`** — is a non-empty certificate pair on disk at `proxy/tls/`, the same test
   `enable-tls.sh` itself uses (`[ -s "$CERT" ]`).
3. **`plain-http`** — is the plain port published off this host (`ALPHA_BIND_ADDRESS`,
   `D-49`)? Reports honestly rather than claiming a "closed" state this tree cannot
   produce: `DEPLOYMENT_RUNBOOK.md` §6 says in its own words *"there is deliberately no
   redirect ... the plain port keeps serving in both cases"*, because `deploy.sh`'s own
   `proxy-answers` guard requires 200 on that exact port.
4. **`provider-mode`** and **5. `cost-ceiling`** — both call
   `auditmanager.bootstrap.settings.load()`, the composition root's own validation (the
   thing that actually decides whether `api` starts), fed the values `alpha.env` and
   `provider.env` actually configure, rather than a second copy of its rules in bash.
   `recorded` mode is reported as a **finding** (step 7 not done, the owner's — GO_PATH row
   7), not an error; `live`/`proxy` without the credential they need surfaces
   `AppSettings.load()`'s own `ConfigurationError` text verbatim.
6. **`off-host-backup`** — always a finding: nothing in this tree gives `reset.sh`'s dumps a
   destination off this host (`DEPLOYMENT_RUNBOOK.md` §5's own words), and GO_PATH row 8
   names the destination as the owner's. No env var was invented to let this check claim
   `OK` — that would be the silent fallback `AGENTS.md` §4 forbids, in the one place this
   command exists to prevent it.

**Robustness fix found while testing**: the first draft of the `provider-mode`/`cost-ceiling`
driver did `sys.path.insert(0, "src")`, a path relative to the *caller's* working directory,
and separately shelled out to a bare `python3` to turn the two env files into JSON —
`docs/program/DEPLOYMENT_RUNBOOK.md` §1 promises this host bash/docker/curl/sed/git and
explicitly does **not** promise python3. Fixed: one process only, this repository's own
`.venv` (`$REPO/.venv/bin/python`, never a bare interpreter), reading both files itself and
resolving `auditmanager` via `PYTHONPATH="$REPO/src"` (absolute), so the script behaves the
same regardless of the caller's `cwd`. Verified by running it from `/tmp`.

**Each check shown able to fail AND able to pass**, driven manually before the test suite was
written:

```
readiness FINDING plain-http   ALPHA_BIND_ADDRESS is 0.0.0.0, publishing plain HTTP off this host. ...
readiness OK      plain-http   ALPHA_BIND_ADDRESS is 127.0.0.1; plain HTTP is not reachable off this host...
readiness FINDING provider-mode  AUDITMANAGER_PROVIDER_MODE is live but ANTHROPIC_API_KEY is unset; ...
readiness FINDING cost-ceiling   AUDITMANAGER_RUN_COST_CEILING_USD is not a number. A ceiling that cannot be parsed...
readiness OK      cost-ceiling   the run cost ceiling resolves to $1.0.
readiness OK      tls   a certificate pair is present at .../proxy/tls; enable-tls.sh installs the TLS server block on next start.
```

**Tests.** New `tests/integration/composition/test_readiness_command.py`, 29 cases: every
check driven to both `OK` and `FINDING` (`UNKNOWN` too, for the two checks that need
tooling that might be missing); for the five checks that need no running stack, a
mutation-deletion case proves the finding/OK came from that check's own marked block, the
same discipline `test_deploy_script_refusals.py` holds `deploy.sh`'s guards to.
`default-credential` is driven with a stubbed `docker` on `PATH` (records the call, answers
with canned `access.py`-shaped text, reaches no daemon) rather than a real database, and its
"no docker" case strips only the directory `docker` resolves from off `PATH` — not `PATH`
entirely — so the case is honestly about that one check and not about the script failing to
run at all. Also: the summary/exit-status contract, the header always naming R-46, and a
check that the script never writes into `infra/deploy/env/` (the owner's read-only
directory) during a normal run.

Run: `.venv/bin/python -m pytest tests/integration/composition/test_readiness_command.py -q`
→ **29 passed**. Full composition regression alongside G3's two files and the pre-existing
`test_reset_script_refusals.py` / `test_deployed_stack_probe.py`: **154 passed**.

**`docs/program/DEPLOYMENT_RUNBOOK.md`**: new `## 9. Is it safe to publish? — the readiness
command`, between the existing `PA-01` section and "When it goes wrong" (renumbered 9 → 10,
with its one internal cross-reference, `§9` → `§10`, fixed; checked the rest of the tree for
other numeric references to this file's sections — none found for the old §9).

**Forbidden hotspots not touched**: this step's `git diff --stat` touches only
`infra/deploy/readiness.sh` (new), `tests/integration/composition/test_readiness_command.py`
(new) and `docs/program/DEPLOYMENT_RUNBOOK.md` — no `contracts/**`, no `db/migrations/**`, no
`Makefile`, no `src/auditmanager/access/**` (not even `check.py` this time), no
`src/auditmanager/api/**`, no `web/**`.

## 3. Final gate

Before running: `free -g` — 11 GB total, 5 GB available; `ps`/`pgrep` scan for any `make`
process whose `cwd` resolves under `/root/w4*` — none found. Ran once, from this worktree,
at sha `26cd836` (the tip after both steps above), lane `gate-w47a` (PostgreSQL `56410`, S3
`60010/60011`):

```
make gate > /root/w47a-gate.log 2>&1
```

Exited 0. Verdict line:

```
GATE OK: battery, foundation, frontend and whitespace all pass
```

Counts, accounted against the dispatch baseline (`GATE OK`, battery 2516 passed / 5
skipped, foundation 35, frontend 1135 in 80 files, `/root/w46-final-gate.log`, taken on
`1196ca7`):

| | baseline | this gate | delta |
|---|---|---|---|
| foundation | 35 | **35 passed** | 0 |
| battery | 2516 passed / 5 skipped | **2550 passed / 5 skipped**, 169 subtests | **+34** |
| frontend | 1135 in 80 files | **1135 in 80 files** | 0 |

**The +34 is accounted for by test id, not merely by count**: `test_deploy_script_
refusals.py` gained 5 (the `derived-secrets-coherent` guard picked up by the two generic
parametrized tests, `+2`, plus `TestD103TheThreeDerivedValues`'s three cases, `+3`) and
`test_readiness_command.py` is new at 29. `5 + 29 = 34`. No other file's count moved:
`check.py` was not touched, `test_deploy_image_identity.py`'s fixture fix changed no test
count (23 before, 23 after), frontend is untouched (`web/**` is `W47-PASS`'s).

`git status --short` at the sha this gate ran against: clean. No commit follows this entry.

## 4. Summary against `AGENTS.md` §5

1. **Changed files**: `infra/deploy/deploy.sh`, `infra/deploy/env/alpha.env.example`,
   `infra/deploy/readiness.sh` (new), `tests/integration/composition/
   test_deploy_script_refusals.py`, `tests/integration/composition/
   test_deploy_image_identity.py`, `tests/integration/composition/
   test_readiness_command.py` (new), `docs/program/DEPLOYMENT_RUNBOOK.md`,
   `docs/program/W47-GATE.md` (new, this file).
2. **Checks run and results**: see §§1–3 above — `pytest` on the four touched/new
   composition test files (154 passed, no regressions) and one final `make gate`
   (`GATE OK`, counts above).
3. **New/changed contracts**: none. `contracts/**` was not touched; G3's repair only makes
   an existing FF-01 §3-style coherence check apply to a second file, and G1/G2's readiness
   command is additive and consulted by nobody.
4. **Risks / known limitations**:
   - `off-host-backup` is, by design, a permanent finding — nothing in this tree can make
     it read `OK` today, and none was invented to let it. The destination remains the
     owner's (GO_PATH row 8).
   - `plain-http` cannot report a genuinely "closed" state even with TLS on, because no
     redirect mechanism exists anywhere in this tree (`DEPLOYMENT_RUNBOOK.md` §6); it
     reports the one true thing instead, `ALPHA_BIND_ADDRESS`'s exposure.
   - `provider-mode`/`cost-ceiling` need this repository's own `.venv` on the host running
     `readiness.sh`; `default-credential` needs `docker`. Both report `UNKNOWN`, never
     `OK`, when their tooling is missing — verified by test.
   - `derived-secrets-coherent`'s `DATABASE_URL` parser is a bash regex covering the
     unescaped case (`postgresql+psycopg://user:password@host:port/db`); a password
     containing `@`, `/` or `:` would not parse and is refused rather than silently
     accepted — the same fail-closed choice `placeholder-secrets` already makes about an
     unverifiable value.
5. **Instruction to the integrator**: merge at `26cd836dddf25ccff00b6ac9e25256a64b33480b`.
   No tag, no push performed by this stream. `infra/deploy/env/*.env` (the owner's stand)
   was never written, moved or deleted, and no secret it holds was printed anywhere in this
   file or in any commit message.
6. **Forbidden hotspots**: not touched by either step — see the per-step notes in §§1–2
   above. `git diff --stat ce60f80..26cd836` (quoted in full in this branch's history)
   names only `docs/program/DEPLOYMENT_RUNBOOK.md`, `docs/program/W47-GATE.md`,
   `infra/deploy/deploy.sh`, `infra/deploy/env/alpha.env.example`,
   `infra/deploy/readiness.sh`, and three files under
   `tests/integration/composition/**`.
