# W54-TRANSPORT-01 — the inbound key's forced command, its dispatcher and the push

**Executor:** lane `agent/w54-transport-01`, worktree `.local/worktrees/w54-transport`.
**Base:** `7ebf162` (`origin/dev`, `W54-FREEZE-01`). **Date:** 2026-10-12.
**Grant:** `W54-PLAN.md` §4 Stage A `W54-TRANSPORT-01`, without `infra/deploy/README.md`,
which may be edited only after SEAL's merge (§6). The README rows are in §5 below.
**Checks:** `R-102` light acceptance. Container-free: `docker` and `ssh` are stubbed on
`PATH`. No heavy step was run, and none is needed.

## 1. Changed files

| Path | What |
|---|---|
| `infra/deploy/lib/forced-command.sh` (new) | the one dispatcher (`fc_register`, `fc_dispatch`, `fc_refuse`), the bundle-name grammar, and the bundle-tree rule both ends apply (`fc_check_bundle_tree`) |
| `infra/deploy/receive-bundle.sh` (new, 0755) | the inbound key's forced command: `receive`, `status`, `import`, `report`, `requeue` |
| `infra/deploy/push-bundle.sh` (new, 0755) | this host's side: verify and re-hash the bundle, measure the deterministic tar, send `receive <KEY> <size>` |
| `tests/integration/composition/test_bundle_transport_refusals.py` (new) | 105 cases (§2) |
| `docs/program/DEPLOYMENT_RUNBOOK.md` | new §11: install, the verbs, reading a refusal, what it does not do |
| `docs/program/W54-TRANSPORT-01.md` (new) | this report |

## 2. Checks run and their results

All were run in the worktree on the lane's final tree.

| Command | Result |
|---|---|
| `git diff --cached --check` | no output (clean) |
| `bash -n` on each of the three scripts | OK ×3 |
| `shellcheck -x infra/deploy/receive-bundle.sh infra/deploy/push-bundle.sh infra/deploy/lib/forced-command.sh` (ShellCheck 0.9.0, installed) | no findings |
| `.venv/bin/python -m pytest -q tests/integration/composition/test_bundle_transport_refusals.py` | **105 passed** in 23.5 s |
| `.venv/bin/python -m pytest -q -rs tests/integration/composition/test_bundle_transport_refusals.py tests/integration/composition/test_deploy_script_refusals.py` | **153 passed** in 91.5 s, 0 skipped (the shellcheck case ran) |

What the 105 cases cover, against the plan's requirements:

- **A refusal for every guard (31 guards: 10 in the library, 16 in `receive-bundle.sh`, 5 in
  `push-bundle.sh`; count: `grep -cE '^[[:space:]]*# >>> guard: '` on each).** Each case exits 3 with `REFUSED [<guard>]` and
  makes no `docker` or `ssh` call. Each case is also run against a copy of the script with
  that one guard block deleted, and that copy no longer produces the refusal.
  `test_every_guard_has_a_case_here` compares the marker set across the three files with
  the case table, so a guard without a case fails the suite.
- **A refusal for every grammar violation of every inbound verb.** There are 27 violations
  across `receive`/`status`/`import`/`report`/`requeue`. Each is refused as `verb-grammar`
  with 0 stdin bytes read, no `docker` call and nothing written to staging.
  `test_every_verb_has_grammar_violation_cases` parses the `fc_register` table, so a verb
  added without cases fails. There are also 14 injection shapes (`;`, `&&`, `$( )`,
  backticks, `|`, newline, tab, `/`, `'`, unknown verbs, the empty command), and none of
  them executes anything.
- **The real repaired key is accepted.** Seven content-key forms are each received whole:
  the real base key `2026-07-23..2026-08-20+17d.4b74348debf7`; `+121r`; `+121r+3u`;
  `+0r+121u`; `undated`; `+seg-<profile>`; and a key minted by
  `auditmanager.norms.repaired_snapshot` over 121 applied and 3 degenerate repairs. That last
  key is produced by the code, not typed in the test, so when `W54-REPAIR` adds `+<m>u` the
  case exercises the new form without any edit here.
- **Size is refused before reading.** `size-within-limit`, `bundle-not-received`,
  `receive-lock-free` and `staging-has-room` each refuse with a stdin offset of 0.
- **A mismatching tar is removed inside staging only.** There are 10 parametrised kinds:
  short, garbage, a `../` member, an absolute member, a hardlink member, a foreign root, a
  digest mismatch, a tampered file, an extra file and a missing file. A tar longer than
  declared and a symlink member have their own cases. In every case `incoming/` ends empty and the bundle is not kept. Another bundle in
  staging, a sentinel in staging's root and a sentinel beside staging all survive
  byte-for-byte, and nothing named by a member appears anywhere.
- **`import`/`report`/`requeue` invoke only the fixed module command.** The `docker` call
  log equals the exact argv. `import` detaches and holds the lock: while it runs, a second
  `import`, a `report` and a `requeue` are refused, and `status` shows `held`. Its exit
  status lands in `logs/<KEY>.import.exit`. A failed run (exit 4) can be re-run. For
  `report` and `requeue` the module's exit status (5) is passed on.
- **`set -euo pipefail`, quoting and no eval.** Each script starts with the shebang and
  `set -euo pipefail` and is executable. No code line contains `eval` or `source`.
  `SSH_ORIGINAL_COMMAND` is read on exactly one line, `fc_dispatch "${SSH_ORIGINAL_COMMAND-}"`.
  The only `bash -c` is the literal import runner, which receives its command as positional
  parameters.
- **Push.** A round trip through the stubbed `ssh` into the staged `receive-bundle.sh` keeps
  exactly the sent files, and the `ssh` options are asserted. A stand-side refusal is passed
  on. A tampered, unlisted or misnamed bundle is refused here before `ssh` is called.

## 3. New contracts (frozen here, as the plan's §3.5 says: "the grammar, staging and refusal rules are frozen in TRANSPORT's task file")

The task file does not spell these out, so they are fixed here and in the scripts. The
integrator should confirm them or rule otherwise before `W54-BUNDLE-01` and
`W54-STAND-COPY-01` are dispatched.

1. **Bundle name `<KEY>`** = `<content_key>+<bundle digest>`
   (`FC_BUNDLE_KEY_ERE` in `lib/forced-command.sh`):
   - `<content_key>` = `<window>+<d>d[+<n>r[+<m>u] | +0r+<m>u].<12 hex>[+seg-<profile>]`;
   - `<window>` is `YYYY-MM-DD..YYYY-MM-DD` or `undated`;
   - counts have at most 6 digits and no leading zero;
   - `+0r` alone is refused, because it is not a key (`ck_norms_snapshot_raw_key`);
   - `<profile>` is `[a-z0-9]+(-[a-z0-9]+)*`.
2. **Bundle digest** = 64 lowercase hex, the SHA-256 of the bundle's `SHA256SUMS`. That file
   is in GNU `sha256sum` text form (`<hex>␠␠<path>`). It lists every other regular file
   exactly once, and its paths are ASCII components `[A-Za-z0-9_+=-][A-Za-z0-9._+=-]*`: no
   leading dot, at most 8 deep. The tree holds nothing else apart from directories.
   **`W54-BUNDLE-01`'s exporter must write `SHA256SUMS` and name the directory this way.**
   File names must be ASCII; content-addressed names satisfy that.
3. **Verbs** (anchored EREs; size `[1-9][0-9]{0,11}`): `^receive (<KEY>) <size>$`,
   `^status$`, `^import (<KEY>)$`, `^report (<KEY>)$`, `^requeue (<KEY>)$`. The command
   string is at most 512 bytes, in the charset `[A-Za-z0-9._+ -]`.
4. **Transfer**: a stdin tar of exactly `<size>` bytes whose members are only `<KEY>/…`
   regular files and directories. `push-bundle.sh` produces it with GNU tar
   `--format=gnu --sort=name --owner=0 --group=0 --numeric-owner --mtime=@0
   --hard-dereference`.
5. **Staging layout** under `BUNDLE_STAGING`: `incoming/<KEY>/`, `bundles/<KEY>/`,
   `logs/<KEY>.{received,import.started,import.log,import.exit}`, `receive.lock`, and
   **`import.lock`**. The import lock is a `flock(2)` lock held for the whole of an
   import, report or requeue. `W54-STAND-COPY-01`'s `deploy.sh` guard
   (`stand_import_locked`) should test it with `flock --nonblock <staging>/import.lock true`.
6. **The fixed module command** (for `W54-BUNDLE-01`):
   ```
   docker compose --env-file <env> --file infra/deploy/compose.server.yml run --rm --no-deps -T \
     --entrypoint python --volume <staging>/bundles/<KEY>:/bundles/<KEY>:ro \
     [--volume <record>:/run/copy-record.json:ro] \
     api -m auditmanager.norms.bundle {import|report} /bundles/<KEY> --copy-record /run/copy-record.json
   ... api -m auditmanager.norms.bundle requeue /bundles/<KEY>
   ```
   So `auditmanager.norms.bundle` must accept `import <dir> --copy-record <path>`,
   `report <dir> --copy-record <path>` and `requeue <dir>`. The last of these is the custody
   requeue of that bundle's poisoned admissions, run through the bundle module so that one
   module stays the only entry point.
7. **Configuration** comes only from the `command=` string: `BUNDLE_STAGING`,
   `STAND_COPY_RECORD`, `ALPHA_ENV_FILE`, `BUNDLE_MAX_BYTES` (12 GiB) and
   `BUNDLE_STAGING_MARGIN_BYTES` (2 GiB). `LC_ALL=C` is pinned.

No API, domain, analysis or event contract changed, and there is no migration.

## 4. Risks and known limitations

- **Staging needs 2 × size + margin while receiving**, because it holds the tar and its
  extraction at the same time; the tar is deleted after extraction. `W54-PLAN.md` §3.9 gives
  staging `bundle + dump + 2 GiB`. If the receive peak overlaps a dump on the same
  filesystem, the true need is larger. P4 runs `receive` before `dump-db` (CD-16), which
  keeps the two apart. `capacity` (`STAND-COPY`) should say so.
- **The bundle is mounted read-only.** The importer's step 5 (§3.5: delete the objects after
  `report` matches) cannot be done through this mount. `BUNDLE` and `STAND-COPY` must
  choose: a later verb, or a writable mount. The container's user is uid 10001. Received
  files are 0644 and directories 0755 (`umask 022`), so the container can read them but not
  delete them.
- **The copy record is mounted read-only and only its presence is checked**
  (`copy-record-present`, which closes `D-37`'s empty-directory trap). Attestation, openness,
  age, fingerprint and the "a receive or import converts the record" rule are the
  importer's and `STAND-COPY`'s record pre-check, which their grant puts in this script. The
  record must be readable by uid 10001.
- **Detached import.** The lock is held by the detached runner and the `docker` client it
  starts. If that client is killed, the lock is released while the one-off container may
  still be running. A hung importer is an owner act (§3.10) and is rehearsed in `W54-REHEARSAL`.
- `status` probes the lock with a momentary `flock`. An `import` that starts in the same
  instant can be refused once, harmlessly, as `import-lock-free`.
- Nothing deletes a staged bundle. Removal is an owner act.
- The forced command keeps no audit log of accepted commands. sshd's own log is the record.
- The scripts assume GNU coreutils, GNU tar ≥ 1.28 (`--sort`) and util-linux
  `flock`/`setsid` on the stand. These are standard on the Ubuntu stand, but they were not
  checked there, because no stand access was allowed.

## 5. Instructions for the integrator

1. Merge after SEAL and BGE-IMAGE, rebased on SEAL's merge (`W54-FREEZE-01`). There are no
   overlapping paths except `docs/program/DEPLOYMENT_RUNBOOK.md`, which SEAL is not granted.
2. **README rows** for `infra/deploy/README.md`'s "What is here" table. TRANSPORT edits that
   table after SEAL (§6); add them during the rebase:

   ```
   | `receive-bundle.sh` | `W54-TRANSPORT-01` — the inbound key's forced command on the stand: `receive`, `status`, `import`, `report`, `requeue`; the boundary for an account that can run `docker` |
   | `push-bundle.sh` | `W54-TRANSPORT-01` — this host's side: re-hash a bundle, send it as `receive <KEY> <size>` |
   | `lib/forced-command.sh` | the one verb dispatcher every forced-command key uses, the bundle-name grammar and the bundle-tree rule both ends apply |
   ```

3. Confirm or rule on the contracts in §3, especially items 2 and 6, before dispatching
   `W54-BUNDLE-01`, and item 5 before dispatching `W54-STAND-COPY-01`.
4. Heavy steps still needed: **none**. Nothing here builds, runs a container or touches the
   stand. The stand install is the owner's act (runbook §11), at P2/P4 per §3.10.
5. Re-run `.venv/bin/python -m pytest -q tests/integration/composition/test_bundle_transport_refusals.py`
   after the rebase. It does not depend on SEAL's files.

## 6. Containment

- Commands: `git diff --name-only 7ebf162..HEAD` and `git status --porcelain -uall`, run on
  the commit that adds this report. The first lists exactly the six paths in §1. The second
  prints nothing.
- Untouched: `infra/deploy/README.md`, `deploy.sh`, compose files, `DEBT_REGISTER.md`,
  `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, `contracts/**`, migrations, lock files, refs and
  tags. Nothing was pushed, merged or tagged, no other worktree was touched, no process was
  killed, and there was no stand access.
