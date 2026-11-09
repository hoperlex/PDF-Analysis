# HOSTS-CUTOVER — moving the production stand to executor hosts and per-stage models

Operator guide for the production stand. Task `HOSTS-CUTOVER-01`, `ADR-0028` (decisions 1–5, 12, 14, 19), owner rulings
`R-153a`…`R-153e`, plan `docs/program/dispatch/HOSTS-PLAN.md`. It is done by an **administrator, once, by hand**. A deploy alone
switches nothing: no host exists until one is connected, and the layout switch is a database row that is **off** until an
administrator turns it on (`ADR-0028` decision 14, "Consequences").

All runs in this guide use **test data** (`D-291`: the stand does not check whether a server may receive a client's documents).

**Status of this guide.** It was written from the tree (`integration/hosts-1`, 35701fa99) and the owner's records, without access
to production or to `adm1.hlab.kz`. Server commands and installer messages are quoted from `tools/executor-runner/install.sh`
and its README. Screen words of the server and layout screens are quoted from `web/src` at that base; the readiness line and
the stages window of a run (wave 2) are quoted from the plan and **may differ in detail** from the deployed screen: where they
do, record it as a deviation, not as a failure. This is the first execution of the transition on a real stand.

## What to know before starting

- **Two ways to the Claude subscription on `adm1.hlab.kz` will coexist during the transition, and they do not touch each other.**

  | | «kzSonnet» (today) | The host agent (new) |
  |---|---|---|
  | Channel | the stand connects **out** over SSH and runs a forced command | the agent on the host calls the stand over **HTTPS** and pulls tasks |
  | Account on the host | `root`, with root's Claude login | the service user `pdf-agent`, with **its own** Claude login |
  | Files on the host | `/opt/pdf-analysis/claude_answer.py`, one line of `/root/.ssh/authorized_keys` | `/opt/pdf-analysis-agent/`, `/etc/pdf-analysis-agent/`, `/var/lib/pdf-analysis-agent/`, the unit `pdf-analysis-agent.service` |
  | In the capacity pool | no (`D-540`) | yes (slots per provider and host) |

  The installer writes only into the right-hand column and never reads or changes `/opt/pdf-analysis/` or any `authorized_keys`
  on the terminal path (the SSH path adds one line to the **SSH user's** `authorized_keys` and removes only that line, section 2.3).
- **The host brings its models itself.** Nothing in this guide types a model name. The agent reports which CLIs and keys it found
  and which models it verified; the stand's catalogue says which models matter (`ADR-0028` decisions 1, 13).
- **Until the layout switch is on, runs follow the old route** (the Primary/Standby or the rules of `ADR-0026`, whichever mode the
  stand is in). Connecting a host does not change a single run. Only runs **started after** the switch use the set; runs already
  started keep the plan they froze.
- **Reversibility.** The behaviour of sections 2–6 can be undone (section 8); the rows the migration's tables keep cannot be removed
  (8.4). Section 7 (archiving «kzSonnet») is one-way, so it comes last, after the new path has run well.
- **Decisions this guide leaves to the owner** (each is marked **Owner decision** where it arises):

  | # | Decision | Where | The guide's default |
  |---|---|---|---|
  | O1 | Sign the same Claude account in a second time on the host, as the service user | 2.1, 2.5 | needed: there is no other way to give the agent a login |
  | O2 | The optional API key file (`R-153d`): a new path by which a document's text leaves the stand | 2.6 | skip |
  | O3 | Take a database copy before the migrating release although the stand holds only test data (`R-110`) | 1.4 | take it |
  | O4 | Prepare a set before the block ensemble exists | 4 | prepare, **do not enable** |
  | O5 | Turn the layout on for production, and when (`ADR-0028` decision 12: after the ensemble) | 5 | wait for the ensemble |
  | O6 | Archive «kzSonnet», and thereby give up the one-switch rollback (section 7.2) | 7 | after the new path has run well |

## 1. Preconditions

Record the first block of the protocol (the last section) before anything else.

**1.1 Role.** You are signed in as an administrator (`admin`). An expert only reads the screens of this guide; a viewer sees
none of them.

**1.2 The release is deployed and verified.** On the host of the stand, in the deployed checkout (`/srv/auditmanager` in the
runbook's examples):

```text
infra/deploy/verify-deployed.sh; echo "exit=$?"
python3 -c "import json; print(json.load(open('contracts/api/v1/openapi.json'))['info']['version'])"
ls db/migrations/versions | sort | tail -1
```

**Expect.** `exit=0` (the stack is this tree; every other code is a stop: `DEPLOYMENT_RUNBOOK.md` §4). The contract version is
**1.45.0 or later**. The last migration file is `20261109_0062_hosts_stage_models.py` or later. Which release each section needs:

| Section | Needs | How to tell |
|---|---|---|
| 2, 3 | the release with `HOSTS-INT-1` (host agent, «Серверы») | the tab «Серверы» and the button «Подключить сервер» exist on «Исполнители» |
| 4, 5 | the same, plus `HOSTS-ENSEMBLE-01` for the full set | the row «Анализ блоков» has two cells (section 4) |
| 5, 6 | `RUN-START-ONE-01` (the readiness line under «Запустить») | the line exists under the button |
| 7 | `HOSTS-CMP-01`: comparisons leave the legacy route (`D-541` closed) | `git grep -n "system_managed\|stage_plan" -- src/auditmanager/comparison \| head -3` prints lines (the register's own check: it prints nothing while `D-541` is open) |

**1.3 Provider source is `database`.** The layout switch refuses to turn on otherwise (`provider_source_not_database`).

```text
grep -n '^AUDITMANAGER_PROVIDER_SOURCE=' infra/deploy/env/alpha.env
infra/deploy/readiness.sh 2>&1 | grep executor-source
```

**Expect.** `AUDITMANAGER_PROVIDER_SOURCE=database`, and a line starting `readiness OK      executor-source` that says the source is
`'database'`. Print nothing else of `alpha.env`: it holds secrets.

**1.4 A database copy exists from before migration 0062 was applied** (**Owner decision O3**). Migration 0062 cannot be
downgraded once any host, layout or planned-run row exists (section 8.4), so the copy is the only way back to the earlier
schema. The runbook's name for it is **the one-off copy**, taken through the copy key's forced command by `dump-db`
(`pg_dump --format=custom --no-owner --no-privileges`, checked with `pg_restore --list`) and recorded with its fingerprint and
migration. Follow `DEPLOYMENT_RUNBOOK.md` §13 ("The order — with real client data on the stand", "A migrating deploy needs a fresh
receipt"); this guide does not restate that order. In short:

- Check which case you are in: `ssh -i <copy key> -o IdentitiesOnly=yes <user@stand> status`. If the `real_data` marker exists,
  the copy is **mandatory** and `deploy.sh` refuses without a receipt (`stand_copy_fresh`): `dump-db`, `inventory-s3`, `pull-copy.sh`,
  `restore-test.sh`, `attest <STAMP> … publish <candidate sha>`, deploy **within 24 hours of the dump**, then `resume <STAMP>`.
- If the stand holds only generated test data (`R-110`), the runbook asks for no copy and the waiver applies. The guide still
  recommends one, because the downgrade is refused: `dump-db`, then `resume <STAMP>` after the deploy (the record, left open, would
  block later deploys). It stops the writers (`web`, `api`, `worker`) for the length of the dump.
- Write `<STAMP>` and the dump's sha256 into the protocol. If the release was already deployed with no copy taken before it,
  write that down as a known risk: section 8.4 then has no restore point from before the migration.

**1.5 «kzSonnet» is healthy now.** «Исполнители» → «Расширенные ▸» → «Подключения» → «kzSonnet» (`exc_01M5WBXWFGP9X3NGRVHQZ844E2`):
the last probe on the current revision is `ok`. **Expect** `ok`. If it is not, fix it first, so that a later failure cannot be
blamed on the transition. Note the mode of the stand (`legacy` Primary/Standby or `rules`) in the protocol.

**1.6 `adm1.hlab.kz` can take the agent.** As `root` on the host:

```text
. /etc/os-release; echo "$PRETTY_NAME"
systemctl --version | head -1
python3 --version
command -v sudo
curl -sS -o /dev/null -w '%{http_code}\n' https://<stand>/
command -v claude; claude --version
ls -l /opt/pdf-analysis/claude_answer.py
grep -c ' auditmanager:exc_01M5WBXWFGP9X3NGRVHQZ844E2$' /root/.ssh/authorized_keys
```

**Expect.** An Ubuntu LTS name; a `systemd` version; Python **3.11 or newer**; the path of `sudo`; a three-digit HTTP code from
the stand (any answer; `000` means the host cannot reach the stand, and the one-liner would fail at its first download); the
path and version of the **existing** Claude CLI (the version must be 2.1.268 or newer, or `claude auth status` — which the
agent depends on — is not available and the login is reported `unknown`); the forced-command script is there; `1`.
Note where `claude` lives: a CLI under `/root` or `/home` cannot be seen by the agent's service (its unit sets `ProtectHome=true`),
see 2.5.

**1.7 Quiet time is not required.** Nothing in sections 2–4 touches a running run; section 5 affects only runs started after it.

**Record.** `PASS / FAIL / BLOCKED` for 1.1–1.6 with the values above.

## 2. Connect the server

Choose **one** path for `adm1.hlab.kz`. The terminal path (2.2) has the fewest moving parts. The SSH path (2.3) is the alternative.
Do not run both: every command or install session creates its own server row the moment it is made (the list shows it off line until
its agent reports), so a second attempt on the same machine leaves a row that never reports; delete that row.

Both paths need the stand's public origin configured (`AUDITMANAGER_PUBLIC_ORIGIN`); without it the window answers
`503 dependency_unavailable` (`public_origin`) and creates nothing.

### 2.1 The service user and the Claude login (**Owner decision O1**)

- The installer creates a system user **`pdf-agent`** (home `/var/lib/pdf-analysis-agent`, mode 0700, shell `nologin`) and runs
  the agent as it. It is not a choice in the one-liner.
- **`--service-user root` is not supported.** `install.sh` refuses before it changes anything: exit 66, `root is root; the agent
  needs an account of its own` (the message names the account given). Another account name is accepted only if it does not exist
  or already has the home `/var/lib/pdf-analysis-agent`; the stand's command does not pass one, and this guide does not use it.
- **What root's existing Claude login means to the agent: nothing.** The agent runs as `pdf-agent` with
  `HOME=/var/lib/pdf-analysis-agent`, its unit hides `/root` and `/home` (`ProtectHome=true`), and the installer never copies a
  credential from another account. A CLI signed in only as root is reported `login_required` («нужно войти на сервере»). Root's login keeps serving
  «kzSonnet», unchanged.
- **So the owner must sign `claude` in once as `pdf-agent`** (2.5), with the subscription account, not an API key. It is the
  second login of the same account on the same machine: both logins draw on the one subscription and its limits, which is `D-540`
  in practice. Whether a second login is acceptable under the vendor's terms is the owner's call; the project's rule is only
  that subscriptions are used through the official CLI under the owner's own login (`R-149b`).

### 2.2 Terminal path

1. **On the stand.** «Исполнители» → «Серверы» → «Подключить сервер» → tab «Командой в терминале». Type «Название сервера»:
   `adm1.hlab.kz`. Press «Получить команду».
   **Expect.** The field «Команда для терминала сервера» holds one line; the window says it is shown once, valid 15 minutes and
   single use; the status reads «ждём сервер…». The line «Не для клиентских документов…» (`D-291`) is shown. Copy the line; do not
   close the window. A second press of «Новая команда» replaces the first command.
2. **On `adm1.hlab.kz`**, as `root` (or any user with `sudo`), paste the line. Its shape, for reference only (the stand fills in
   the values; the model is not part of it):

   ```text
   cd "$(mktemp -d)" && curl -fsSL -o agent.tar.gz https://<stand>/api/v1/runner/agent-package/<version> \
     && echo '<sha256>  agent.tar.gz' | sha256sum -c - && tar -xzf agent.tar.gz \
     && AUDITMANAGER_ENROLLMENT_SECRET=<secret> AUDITMANAGER_STAND_ORIGIN=https://<stand> \
        sudo --preserve-env=AUDITMANAGER_ENROLLMENT_SECRET,AUDITMANAGER_STAND_ORIGIN bash install.sh
   ```

   **Expect.** Exit 0 and, in this order, lines such as `creating the service user pdf-agent`, `agent <version> installed in
   /opt/pdf-analysis-agent`, `wrote /etc/pdf-analysis-agent/agent.toml: host mode (every model this host can reach), no model
   declared`, `started the service`, `done: agent <version> runs as the service pdf-analysis-agent under the user pdf-agent, as a
   host agent (no model declared)`, then the state of the CLIs for `pdf-agent` and the steps that are yours (2.5, 2.6). The secret
   is never printed.

   | Exit | Meaning | What to do |
   |---|---|---|
   | 65 | package missing or its sha256 wrong | run the command again from the start; if it repeats, stop and report (nothing was installed) |
   | 66 | a prerequisite is missing (Python < 3.11, no `systemd`, the account is root) | fix it, run the same command again within 15 minutes |
   | 69 | the stand could not be reached | run the same command again within 15 minutes |
   | 77 | not root | run it as root or with `sudo` |
   | 78 | the secret or the origin is missing, spent or refused | press «Новая команда» and run the new one |

3. **On the stand.** The window's status becomes «сервер на связи, моделей пока нет: агент ещё проверяет клиентов» as soon as the agent
   reports, and **«найдено: Opus 5.5, Sonnet 5.5»** after the login of 2.5 and the agent's model checks. Leave the window open until then.

### 2.3 SSH path (the alternative)

Use it when pasting a command on the host is not wanted. The stand's worker connects to the host, so it needs an SSH user with
**passwordless `sudo -n`**, a POSIX login shell, `bash`, `tar` and `sha256sum` on the host, and the host's address must be one the
stand may connect to (it already reaches `adm1.hlab.kz` for «kzSonnet»). An install session lasts **30 minutes**.

1. **Back up the SSH user's `authorized_keys`** (if the SSH user is `root`, this is the same file that carries «kzSonnet»'s line):

   ```text
   cp -p ~<ssh user>/.ssh/authorized_keys ~<ssh user>/.ssh/authorized_keys.bak-hosts-cutover-$(date +%Y%m%dT%H%M%S)
   ```
2. **On the stand.** «Подключить сервер» → tab «По SSH». «Узел SSH» `adm1.hlab.kz`, «Пользователь SSH» the user above; the port
   (22) and the generated key are under «Дополнительно». Press «Начать установку».
   **Expect.** The window shows «Строка для authorized_keys» (`restrict ssh-ed25519 AAAA… auditmanager-install:<id>`) and the three
   steps «Читаем отпечаток сервера» → «Подтвердите отпечаток» → «Ставим агента».
3. **On the host**, append that line to the SSH user's `authorized_keys` (an editor, or `cat >> …`; do not replace the file).
4. **Compare the fingerprint.** On the host: `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`. The window shows «Отпечаток ключа
   сервера» (`SHA256:…`). They must be identical. Tick «Я сверил отпечаток с сервером» and press «Подтвердить отпечаток».
   **If they differ, stop**: someone may be in the middle; nothing is trusted on first use.
5. **Expect.** The third step becomes `✓` («готово»), and the status reads «найдено: …» after the login of 2.5. The stand removes its
   own line (the one ending `auditmanager-install:<id>`) when the install ends, whatever the outcome. Check on the host:

   ```text
   grep -c 'auditmanager-install:' ~<ssh user>/.ssh/authorized_keys
   grep -c ' auditmanager:exc_01M5WBXWFGP9X3NGRVHQZ844E2$' /root/.ssh/authorized_keys
   ```

   **Expect** `0` and `1`: the install line is gone and «kzSonnet»'s line is untouched. If the first count is not 0 (an
   `AuthorizedKeysFile` elsewhere, or a failed removal), delete that one line by hand; the private half of the key is destroyed
   either way.
6. The install runs the same `install.sh` as the terminal path (same service user, same files). Continue with 2.4.

### 2.4 The agent runs and nothing of «kzSonnet» moved

On `adm1.hlab.kz`:

```text
systemctl is-active pdf-analysis-agent
journalctl -u pdf-analysis-agent -n 40 --no-pager
ls -l /opt/pdf-analysis/claude_answer.py
grep -c ' auditmanager:exc_01M5WBXWFGP9X3NGRVHQZ844E2$' /root/.ssh/authorized_keys
```

**Expect.** `active`; a journal with no token and no document text (it holds task ids and timings); the forced-command script with its
earlier time; `1`. Exit 2 or 3 of the agent (bad configuration, refused token) is not restarted by systemd: read the journal, then
use a new command. On the stand, «kzSonnet» still probes `ok`.

### 2.5 Sign the CLI in as `pdf-agent`

```text
sudo -u pdf-agent -H python3 /opt/pdf-analysis-agent/detect.py --host --key-file /etc/pdf-analysis-agent/keys.env
```

**Expect** one of: a line `claude_code access=subscription auth=login_required version=2.1.…` (the CLI is there, not signed in);
no `claude_code` line (the CLI is **not installed for `pdf-agent`**); then a line `keys file=… state=…`.

- **No CLI for `pdf-agent`.** Install Claude Code **for that user** with the vendor's documented installer, run as `pdf-agent`
  (the vendor's page is outside this repository; check it, since the command changes with their releases — at the time of writing
  it is `sudo -u pdf-agent -H bash -c 'curl -fsSL https://claude.ai/install.sh | bash'`), or install it system-wide under
  `/usr/local/bin`. The agent searches `/usr/local/bin`, `/usr/bin`, `/bin`, `/snap/bin` and the service user's
  `~/.local/bin` and `~/.npm-global/bin`, i.e. `/var/lib/pdf-analysis-agent/…`. **A copy under `/root` or `/home` is invisible to the service.**
- **Sign in** (follow the CLI's prompts: it prints a URL to open in your browser and asks for the code):

  ```text
  sudo -u pdf-agent -H /var/lib/pdf-analysis-agent/.local/bin/claude auth login
  sudo -u pdf-agent -H /var/lib/pdf-analysis-agent/.local/bin/claude auth status
  ```

  (use `claude` instead of the full path if it is on `sudo`'s `PATH`). Sign in with the **claude.ai subscription account**. A login
  with an API key is reported as access `api` (paid, metered), which is not what this step wants. Do not paste the status output
  anywhere: it may name the account.
- **Expect**, within about one to three minutes: `detect.py --host` prints `claude_code access=subscription auth=valid version=…`; the
  agent's journal shows its model checks (`probe:`); the window of 2.2 or 2.3 says «найдено: Opus 5.5, Sonnet 5.5». The agent
  recounts every 60 s and checks each catalogue model with one minimal call on a change, so no restart is needed.

If the models do not appear, open «Подробнее» (section 3): it names the reason per model.

### 2.6 The key file (optional, **Owner decision O2**, `R-153d`)

**Default: skip it.** The subscription path is the default (`R-149b`). A key in this file makes the host serve the provider **by
API, paid**, and **every document sent through it goes to that provider**, a new outward path (`R-143c`, `D-291`). Put a key here
only for that purpose and only after the owner has said so.

```text
sudo install -m 0600 -o pdf-agent -g pdf-agent /dev/null /etc/pdf-analysis-agent/keys.env
sudo -u pdf-agent -H nano /etc/pdf-analysis-agent/keys.env
ls -l /etc/pdf-analysis-agent/keys.env
sudo -u pdf-agent -H python3 /opt/pdf-analysis-agent/detect.py --host --key-file /etc/pdf-analysis-agent/keys.env
```

One `NAME=value` per line: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY` (other lines are not read). Use an editor that
writes **in place**.

**Expect.** `ls -l` shows `-rw------- 1 pdf-agent pdf-agent`. The agent reads the file **only** when it is a regular file of mode
0600 owned by `pdf-agent`; otherwise it ignores it and the journal says why (`mode_is_not_0600`, `not_owned_by_the_service_user`,
`not_a_regular_file`, `unreadable`, `too_large`). `detect.py` prints `keys file=… state=…`; within about a minute the server row
gains models marked «API». A key never reaches the stand, a log, a report or a child CLI's environment. To withdraw the path:
`sudo rm /etc/pdf-analysis-agent/keys.env`; the agent drops the provider at its next recount (60 s).

**Record.** `PASS / FAIL / BLOCKED` for 2.2 or 2.3, 2.4, 2.5 (and 2.6 if taken); the path chosen; the host id (`exh_…`) from the
stand; the CLI version.

## 3. Verify

On the stand, «Исполнители» → «Серверы».

1. **The row.** **Expect:** the summary «На связи 1 из 1 · свободно N из N»; a row `● adm1.hlab.kz`, the switch «Использовать» **on**
   (a new server is on: the administrator who connected it made the mark, `R-149b`), the model chips «Opus 5.5» and «Sonnet 5.5»
   (no «API» mark unless 2.6 was done), and a load such as `0/1`. The «Не для клиентских документов…» line is above the list.
   No «Claude · подписка» label is drawn on the row: the subscription is named in «Подробнее».
2. **«Подробнее».** Menu «⋮» → «Подробнее». **Expect:** «Места» lists the Claude Code subscription slots (the default is **1**
   on a subscription login, 2 on an API login or key); «Клиенты и модели» reads «Claude Code · по подписке · вход выполнен · версия
   …» with «Opus 5.5 — доступна» and «Sonnet 5.5 — доступна»; «Сейчас на сервере ничего не выполняется.»
3. **«Проверить сейчас».** Press it. **Expect:** the state is read again and does not change; no error. (The agent itself
   re-checks on a change and every few hours; the stand does not call a model for this button.)
4. **«Использовать» works.** Turn it off, wait about 10 s (the screen polls every 10 s), open «Подробнее». **Expect:** the models are
   not available and the reason is «сервер выключен переключателем «Использовать»»; the row says «нет доступных моделей». Turn it
   on again; the chips return. Each change is a journalled event.
5. **Reasons you may meet:** «нужно войти на сервере» (2.5 not done, or the CLI is under `/root`), «вход не определён» (the CLI is
   older than 2.1.268, or signed in by a method the agent cannot name), «агент сервера ещё не подтвердил эту модель» (wait a minute,
   or the account has no access to that model: the agent's journal gives the failure word), «сервер временно снял модель после
   отказа» (a real refusal — quota, access, "no model" — takes a model off for 15 minutes), «сервер не на связи» (no pulse for
   120 s: `systemctl status pdf-analysis-agent`).

If a Claude model never becomes available, **stop**: sections 4–6 need both Opus 5.5 and Sonnet 5.5 (the editor offers a set only when
every model it names is served by some server now).

**Record.** `PASS / FAIL / BLOCKED` for 3.1–3.4, with what «Подробнее» showed.

## 4. Choose the set (**Owner decision O4**: prepare, do not enable)

«Исполнители» → tab «Модели по этапам» → «Изменить» (administrator). Choose the segment **«Только Claude»**, check the table, press
«Сохранить набор». The plan calls this set «Только Claude (блоки без судьи)» until the block ensemble exists; the screen says «Только Claude».

**Expect, before the ensemble** (the row «Анализ блоков» is one cell), after saving, the table reads «Строка — Модель · усилие»:

| Строка | Модель · усилие |
|---|---|
| Анализ текста | Sonnet 5.5 · среднее |
| Анализ блоков | Opus 5.5 · среднее |
| Комплексная сверка | Sonnet 5.5 · среднее |
| Нормы | Sonnet 5.5 · среднее |
| Критик | Sonnet 5.5 · среднее |
| Уточнение | Sonnet 5.5 · среднее |

and the note «Набор не применяется: он выключен, прогоны идут по прежним правилам. Включает его администратор в «Расширенных».» No
row carries «⚠ нет на серверах». Efforts are the catalogue's «среднее» for every cell; «Дополнительно» holds the answer tokens and
timeout of each cell (today's constants), which this guide leaves as they are.

**After the ensemble lands** (`HOSTS-ENSEMBLE-01`), «Анализ блоков» has two cells, «первая ветка» (Opus 5.5 · среднее) and «судья»
(Sonnet 5.5 · среднее). That is the complete «Только Claude».

**Prepare, do not enable.** `ADR-0028` decision 12 and the plan (1.2 item 4) say the layout is enabled on production only after the
ensemble, because a set without the judge is not the original's «Только Claude». Saving a revision changes nothing for any run:
the switch (section 5) is separate. Enabling now, before the ensemble, is an **owner decision**: record the ruling id in the protocol.

The revision is kept with its author and time under «Расширенные ▸» → «Модели по этапам» («Прежние версии набора»).

**Record.** `PASS / FAIL / BLOCKED`; the table as read; the revision number.

## 5. Enable (**Owner decision O5**)

Only after the owner has decided (section 4) and `HOSTS-ENSEMBLE-01` is in the release, or with the owner's explicit ruling.

«Исполнители» → «Расширенные ▸» → the section «Модели по этапам» → the switch **«Модели по этапам: включены»**.

**Expect.** The switch turns on and «Журнал переключателя» gains «Включён · <time>». The table of section 4 now says «Набор
применяется к прогонам, которые начинаются сейчас.» The readiness line under «Запустить» shows the set and the access:
**«Только Claude · по подписке · Модели по этапам ▸»** (before the switch it read «Маршрут: прежний»).

**Refusals.**

| Refusal | Cause | What to do |
|---|---|---|
| the switch is disabled, «Включить нельзя: набор моделей ещё не сохранён.» | no saved revision (`no_layout_revision`) | do section 4 |
| «Переключатель не изменён»: «Включить нельзя: стенд берёт исполнителей не из базы данных…» (`provider_source_not_database`) | the stand's provider source is not `database` | section 1.3; it is a deployment setting, not a screen setting |
| «Переключатель не изменён» for another reason | the screen shows the correlation id | record it, stop |

Runs **already started** are not affected by the switch in either direction (their plan is frozen). From now on a run bound to
the set holds one capacity unit per provider pool of its cells (`adm1.hlab.kz` · Claude Code) **from binding to the end of the run**
(`D-499`).

**Record.** `PASS / FAIL / BLOCKED`; the journal entry; the readiness line as read.

## 6. One test run

On a **test section** with a synthetic document (`D-291`):

1. Open the section and read the line under «Запустить». **Expect:** «Только Claude · по подписке · Модели по этапам ▸». The estimate is
   0 $ and pressing the button labelled «по подписке» **is** the consent (consent v2, `ADR-0028` decision 8): no dialog about money.
2. Press «Запустить». **Expect:** the run starts; it does not sit in a waiting state «Ждём Opus 5.5 …» (if it does, the line names
   the model that has no server: go back to section 3).
3. Open «Модели по этапам ▸» (the stage window) on the run. **Expect:** one row per stage with its model and the server: Opus 5.5 on
   «Анализ блоков», Sonnet 5.5 on the others, the server `adm1.hlab.kz`, and, while a stage runs, a live line such as «Сейчас: Анализ
   блоков · окно 2 из 5 · Opus 5.5 · adm1.hlab.kz · 12 мин». The stages without a model (the three preparation stages, the merge,
   the norm-citation check, the report) show no model. The journal names the server as «adm1.hlab.kz · Claude · подписка».
4. On «Серверы» → «Подробнее» of the host, while the run is going. **Expect:** «Сейчас на сервере» lists the run, its stage and the model,
   and the load reads `1/1`.
5. **Expect at the end:** the run finishes; no refusal about a model identity (the stand fails a reply whose reported model is not the
   requested one or one the catalogue accepts, `R-133`); a run that was already going when the switch was turned on, if there was one, finished on its old route.
6. *Optional, to see the hidden reason:* turn «Использовать» off, open the same section. **Expect:** the start button is inactive and says why
   (a model has no server). Turn the switch on again.

**Record.** `PASS / FAIL / BLOCKED` per point; the run id; any `correlation_id` of a refusal.

## 7. «kzSonnet» — keep, then archive and close its door

**Keep it** while comparisons still use the legacy route (until `HOSTS-CMP-01`, `D-541`); the host agent does not serve the five
`comparison_*` kinds before that. **Archive it only on a release that has `HOSTS-CMP-01`** (1.2), after the new path has run
well, and only if nothing else depends on it.

### 7.1 Who depends on «kzSonnet» (**Owner decision O6**)

«Расширенные ▸» → «Подключения» → «kzSonnet», then «Назначения» (legacy mode: Primary/Standby per kind of work), «Правила» and «Группы»
(rules mode: a rule's group, a group's members). **Expect:** no route, rule or group names it. Otherwise: archiving a connection
that a route names is refused (`409`, `connection_routed`); a connection that is a group member archives, but the group member is
then ineligible (`connection_archived`) and, if a rule still names that group, the work of that kind stalls. Change the route, or
make a new group revision without it, first.

**AR v3 keeps its own path** (`ADR-0028` decision 19), and this guide does not know whether it is configured through «kzSonnet».
If it is, or if anything else uses the connection, **stop here and keep it**.

### 7.2 Know the cost of the rollback first

Archiving is one-way. Rollback A (8.1) returns runs to **the old route**; if that route ran through «kzSonnet», it then has no
executor and runs wait and end `no_executor_online`. After 7.3 the old route has to be rebuilt (a new connection and key line,
`tools/executor-runner/README.md` section F) before the switch can be turned off again.

### 7.3 Archive on the stand

«Подключения» → «kzSonnet» → «Архивировать» and confirm («Его нельзя будет проверить, назначить или дополнить»). **Expect:** the connection
leaves the active list; the journal has `executor.connection_archived`. Refusal `409 connection_routed` («Подключение назначено на
работу. Сначала уберите его из назначений.»): see 7.1.

### 7.4 Close the door on the host

On `adm1.hlab.kz`, as root. **Back up first**, then remove exactly one line, the one that ends with
`auditmanager:exc_01M5WBXWFGP9X3NGRVHQZ844E2`. No `sed`: a filtered copy replaces the contents in place, which keeps the owner and mode.

```text
cd /root/.ssh
cp -p authorized_keys authorized_keys.bak-hosts-cutover-$(date +%Y%m%dT%H%M%S)
grep -n ' auditmanager:exc_01M5WBXWFGP9X3NGRVHQZ844E2$' authorized_keys
grep -c '' authorized_keys
```

**Expect.** Exactly **one** line is printed, beginning `restrict,command="/usr/bin/python3 /opt/pdf-analysis/claude_answer.py
--ssh-envelope --model claude-sonnet-5 …` (the path of `claude` after it differs) and ending with the comment; note the line count
`N`. If none is printed (trailing blanks, a different comment) or more than one: **stop**, do not guess. Lines for other
`auditmanager:exc_…` connections, if any, are not part of this guide.

```text
grep -v ' auditmanager:exc_01M5WBXWFGP9X3NGRVHQZ844E2$' authorized_keys > authorized_keys.new
grep -c '' authorized_keys.new
cat authorized_keys.new > authorized_keys
rm authorized_keys.new
ls -l authorized_keys
grep -c 'auditmanager:exc_01M5WBXWFGP9X3NGRVHQZ844E2' authorized_keys
```

**Expect.** The second command prints `N-1`; `ls -l` shows the same owner and mode as before (normally `-rw------- root root`); the
last command prints `0`. The backup stays (it holds public keys only). From now on the stand cannot reach the forced command, even
with the connection's key. `/opt/pdf-analysis/claude_answer.py` and root's Claude login are not needed any more and are not
touched by this guide; remove or sign them out later if the owner wants, with no effect on the agent.

### 7.5 Prove the new path alone

Run one test run (section 6) **and one comparison on test data**. **Expect:** both finish through `adm1.hlab.kz` (the comparison's
screen names the group and the model, then the connection used); nothing mentions «kzSonnet». `D-540` is closed by this section;
the integrator records it in the debt register with the date and the protocol.

**Record.** `PASS / FAIL / BLOCKED` for 7.1–7.5; the archive time; the backup file name (not its content).

## 8. Rollback

Do the levels **in this order**; each is enough for what it says. All are administrator acts.

### 8.1 A. Turn the layout switch off (back to the old routing; data stays)

«Расширенные ▸» → «Модели по этапам» → untick «Модели по этапам: включены».

**Expect.** «Журнал переключателя» gains «Выключен · <time>»; the table says «Набор не применяется: он выключен, прогоны идут по прежним
правилам»; the line under «Запустить» reads «Маршрут: прежний». **Runs started after this follow the old route; runs already
started keep their frozen plan and finish; nothing is deleted** (revisions, the journal, hosts, their system connections and groups,
and the cell bindings of past runs stay).
**Caution:** it is a complete rollback only while the old route still has a live executor. After section 7 it does not (7.2). The
plan also removes this switch once production is switched (`ADR-0028` decision 14); until that task lands the switch exists.

### 8.2 B. Disable the host

«Серверы» → the switch «Использовать» of `adm1.hlab.kz` off. **Expect:** no new run binds to it; runs already bound finish; the
journal records the change. Alone it is **not** a rollback of the layout: with the switch still on and the only host off, a new run
waits («Ждём Opus 5.5 …») and ends `no_executor_online` after 30 minutes (`R-149c`). Do 8.1 first.

### 8.3 C. Uninstall the agent

On `adm1.hlab.kz`, as root:

```text
sudo bash /opt/pdf-analysis-agent/install.sh --uninstall
systemctl status pdf-analysis-agent --no-pager
```

**Expect.** `removing the agent, its unit, its configuration and its environment file`, then `left in place on purpose: every installed CLI
and its login, the service user pdf-agent and its home /var/lib/pdf-analysis-agent`, and `revoke the runner token in the stand UI`.
`systemctl status` says the unit is not found. It never touches `keys.env`, a CLI or any login: delete `keys.env` by hand if the
keys are not wanted, and `sudo -u pdf-agent -H claude auth logout` if the login is not wanted. «kzSonnet» (if still there) is not
touched and still probes `ok`.

Then on the stand: «Серверы» → «⋮» → «Удалить» → «Удалить сервер». It revokes the host's key; runs already bound to it finish. «Удалить»
**archives** the server: its rows stay (see 8.4).

### 8.4 D. What the migration's downgrade refuses, and what that means

`0062_hosts_stage_models` refuses to downgrade while **any** of these exists, and says so: `refusing to downgrade 0062_hosts_stage_models
with retained host, layout or planned-run data (…); restore a database backup instead`.

- a row in `executor_host`, `executor_host_report`, `executor_model_cooldown`, `stage_layout_revision`, `stage_layout_switch_event`
  or `audit_run_cell_binding`;
- an `audit_run` with a `stage_plan`;
- a system-managed or host-bound `executor_connection`, or a system-managed `executor_group`;
- a runner token, enrollment, agent install or secret bound to a host;
- a `model_call` or `provider_call_effect` row with `stage_key`, `host_id` or `access`.

**In practice:** the first connected server (section 2) creates rows of the first kinds, the first saved set and switch of the next
ones, and the first run under the set of the last ones. Turning the switch off, disabling or deleting the server does not remove
them (a deleted server is archived). **So from section 2 on the schema cannot be walked back with a downgrade**, and the stand does
not need it: with the switch off and the host disabled or uninstalled the old behaviour is back while the new tables sit unused
(`ADR-0028`, "Consequences"). The only way to the earlier schema is the owner-ordered `restore-db <STAMP> <dump-sha256>` of the
copy in 1.4 (it loses everything written after the copy, runs included), then a reviewed revert of the release under
`MAIN_AUTODEPLOY_POLICY.md` (a revert alone fails `migrations-at-head`); see `DEPLOYMENT_RUNBOOK.md` §13, "On failure after the push".
A forward fix is the normal choice.

**Record.** `PASS / FAIL / BLOCKED` for any level executed, with the expected lines.

## 9. Known limits

| Debt | What it means while this guide is in use |
|---|---|
| `D-498` | **No reserve set.** If the Claude subscription's quota runs out, nothing switches to another set (`R-153e`): a run whose cell has no available model waits 30 minutes and ends `no_executor_online`; the screen offers «Запустить снова». The quota resets on the provider's schedule. |
| `D-499` | **Runs are distributed per run, not per call.** A run binds every cell at start and holds the host's subscription slot (default 1 per provider) to its end, so a long run on `adm1.hlab.kz` makes other runs that need Claude queue behind it. Raising the slots in «Подробнее» raises the load on the **one** subscription, not its limit. |
| `D-540` | **«kzSonnet» shares the `adm1.hlab.kz` subscription outside the capacity pool** until section 7: the stand does not count its calls in the host's slots, so both can use the subscription at once beyond the slot; and the two logins (root's, `pdf-agent`'s) draw on one quota. |
| `D-541` | **Comparisons stay on the legacy route** until `HOSTS-CMP-01`: the host agent does not serve the five `comparison_*` kinds, which is why «kzSonnet» must stay until then. |
| `D-291` | **Client documents.** `allow_client_documents` is stored and checked nowhere (`R-149a`): the warning «Не для клиентских документов» stays on «Серверы», in «Подключить сервер» and on the start line. Use test data only. A key file (2.6) adds a path by which a document's text leaves the stand for a third party. |

Also true here: before the ensemble the set has no judge on «Анализ блоков» (section 4); the reasons a model is unavailable are shown
only in «Подробнее» of a server, in a run's waiting line and next to a blocked button, never in lists (`R-149n`); AR v3 and
optimisation are outside this transition (`ADR-0028` decision 19).

## Closing

Record: the state at the end of the run, what changed on the stand and on `adm1.hlab.kz`, the deviations (including any wave-2 wording
that differed), and the `correlation_id` of each refusal. **Never record** the enrollment secret, a runner token, the content of
`keys.env`, the output of `claude auth status`, an `authorized_keys` line or any document.

```text
candidate_commit:
VERSION:
contract_version:
schema_revision:                 # last file of db/migrations/versions in the deployed checkout
stand_mode_before:               # legacy | rules
provider_source:                 # database
copy_stamp:                      # <STAMP> of the copy of 1.4, and its dump sha256, or "none: <reason>"
tester:
started_at:

host_id:                         # exh_…
path:                            # terminal | ssh
agent_version:
claude_cli_version:
models_verified:                 # e.g. Opus 5.5, Sonnet 5.5
key_file_used:                   # no | yes (owner ruling id)
layout_revision:                 # slr_… , kit
layout_switch:                   # off | on at <time> (ruling id if enabled before the ensemble)
test_run_id:
kzSonnet:                        # kept | archived at <time>; authorized_keys backup file name
rollback_executed:               # none | A | A+B | A+B+C
deviations:
finished_at:
```
