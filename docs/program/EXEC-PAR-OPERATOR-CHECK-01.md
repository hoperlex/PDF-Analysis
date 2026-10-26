# EXEC-PAR-OPERATOR-CHECK-01 — the operator's check of parallel runs on a stand

Written 2026-10-26 for `EXEC-PAR-START-01`, `EXEC-PAR-QUEUE-01` and `EXEC-PAR-WEB-01`. It is the
operator's order for the host; nothing here is run by the deploy and no lane may run it. The
mechanism is in `DEPLOYMENT_RUNBOOK.md` §14 and `src/auditmanager/executors/README.md`; this file
only orders the steps for this one check and says what must be seen.

## What the check proves

Two runs over two different documents are in progress at the same moment, each on the executor its
starter chose in the start control, and a second run for a busy executor waits in the queue and is
labelled as waiting. The automated tests prove the claim, the freezing and the interface; none of
them has run on a real stand with two real executors.

## Before you start

* An administrator account, two published document versions whose sections are confirmed and have
  an analysis profile, and a host where `infra/deploy/readiness.sh` is green.
* **Two connections in «Исполнители → Подключения», each probed «готово».** Examples already in the
  tree: «OpenRouter (из окружения)»; the Opus subscription over SSH
  (`tools/executor-runner/README.md` §F); the Codex subscription over an outbound forward (§D).
  Each must pin a model for which the stand has a pin (`claude-opus-5`, `claude-sonnet-5` or
  `gpt-6-sol`).
* The key ring and the database source (runbook §14): `AUDITMANAGER_SECRETS_PUBLIC_KEYS`,
  `AUDITMANAGER_SECRETS_ACTIVE_KID` for both services, `AUDITMANAGER_SECRETS_KEYS` for the worker.
* **`AUDITMANAGER_PROVIDER_SOURCE=database` and `AUDITMANAGER_PROVIDER_MODE=live` in `alpha.env`.**
  With the source `environment` a named executor is refused by design (no silent fallback), so
  the check cannot pass on the old source. Follow runbook §14 "Importing today's variables, and the
  switch" in its order, including the one run through the connection before the switch and the
  `executor-source` line of `readiness.sh` after it.

## Steps

1. **Take a manual copy** of the database (`R-146b` keeps copies manual). This change has no
   migration, but the source switch changes how runs are frozen and is not undone by a redeploy.
2. **Raise the slots.** In `alpha.env` set `AUDITMANAGER_WORKER_SLOTS=2`. Two is enough for this
   check; four (the owner's chosen value) is for after it. Redeploy or restart `worker`: it drains
   its runs first (at most 270 s). The setting is a whole number from 1 to 16; anything else stops
   the worker with a message.
3. **Open one version, choose executor A** in «Исполнитель», press «Запустить прогон».
4. **Open the other version at once, choose executor B**, press «Запустить прогон».
5. **Read both runs.** Each shows its executor and pinned model. Both should be «выполняется» at
   the same time. Write down the start and finish time of each: the overlap is the proof.
6. **Queue.** Start a third run on executor A while the first is still running. It must say
   «Ждёт исполнителя «…»» and start only after the first run on A has ended, while B is unaffected.
7. **Refusal.** Choose a connection, archive it in «Подключения», then press «Запустить прогон»:
   the start is refused with a message in Russian that the chosen executor cannot serve now, no
   run is created, and no other executor is offered.
8. **Repeat.** Repeat a finished run that named an executor: it must stay on that executor.

## What to record

The two executors and their models, the start and finish time of each run, the third run's waiting
label, the refusal text, and `docker compose ... logs worker` for the window. Note the host's CPU and disk during the overlap: the stand is
one VPS (`R-146a`).

## What can go wrong, and what it means

| Seen | Meaning |
| --- | --- |
| The start is refused for every choice | the source is still `environment`, or the connection is not probed «готово» |
| Both runs go one after the other | `AUDITMANAGER_WORKER_SLOTS` is still `1`, or both runs were frozen to the same connection |
| A run waits although its executor is free | report it with the run ids: the claim's per-connection check is wrong |
| The second run is slow while the first extracts the PDF | PDF reading serialises on one lock per process; the overlap is in the model wait, and a second worker process is the remedy, not more slots |

## Rollback

`AUDITMANAGER_WORKER_SLOTS=1` and restart `worker`: one run at a time again. Full rollback of the
source is runbook §14: `AUDITMANAGER_PROVIDER_SOURCE=environment` with the variables back in
`provider.env`. A run that froze a connection and is served after the switch back is refused, not
quietly served by the wrong source.
