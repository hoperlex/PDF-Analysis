# EXEC-WEB-SSH-SERVED-01 — the web treats a command over SSH as a served kind

**Source base:** `3ce0f481` (`origin/main`). Web only; no contract, migration, `VERSION` or stand change.

## Found

On the production stand a «Команда по SSH» connection showed «не готово: этот вид подключения пока
не обслуживается», and could not be routed or chosen for a run. The stand's server serves the kind:
`ssh_command` is registered in `executors/kinds.py`, probed by `probe_ssh_command` in
`probe_runner.py`, and `usability.is_served` asks that registry. The web kept its own list,
`kindIsServed` in `entities/executor-connection/model/readiness.ts`, written when only `http_api` and
`pull` were served, and never updated when the SSH kinds were wired. Its test said so in a comment
(«a command over SSH is still a kind this release does not serve»). `routeBlocker`, which the
«Назначения» editor and the start control's «Исполнитель» select (`EXEC-PAR-WEB-01`) both use,
therefore refused every SSH connection with `kind_not_served`.

## Changed

| Path | Reason |
| --- | --- |
| `web/src/entities/executor-connection/model/readiness.ts` | `kindIsServed` also accepts `ssh_command`; the comment says why and that an unknown SSH profile is the stand's answer in the probe |
| `web/tests/unit/workers/executor-connections.test.ts` | two stale assertions replaced; one new test: a command over SSH is routable on its key and its probe (ready with a key and an `ok` probe, `secret_missing` without a key), and only a kind this release does not know is `kind_not_served` |

## Checks

| Check | Result |
| --- | --- |
| the new test with `ssh_command` removed from `kindIsServed` (mutation, restored) | 2 failed, 30 passed |
| `npm --prefix web run typecheck`, `lint --quiet` | no errors |
| the whole `vitest` battery on this tree | 199 files, 3022 tests passed |
| `tests/contract/program`, `test_doc_prose_facts.py` | 72 passed |

## Limits

- Not run: a browser, or the production stand. The fix removes the web's refusal; whether a real SSH
  connection reaches «готово» still depends on the key ring, the generated key, the `authorized_keys`
  line and the pinned host key on the stand's host.
- `kind_not_served` stays for the probe outcome and for a kind the web does not know.
