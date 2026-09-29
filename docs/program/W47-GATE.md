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
