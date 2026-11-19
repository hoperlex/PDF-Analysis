# Task LOCAL-AGENT-01 — the deploy server's own Codex and Claude subscriptions serve its stand

## Outcome
On a deploy server that is signed in to Codex and/or Claude with a subscription, `deploy.sh` (with `ALPHA_LOCAL_AGENT=auto`) ends by
installing the host agent under the account that holds the logins, and the stand shows the card «Этот сервер» in «Диспетчер»,
enabled, with the models of those subscriptions. No new screen: «Использовать» is the switch (owner rulings `R-158a`..`R-158e`).

## Depends on
- HOSTS-AGENT-01, HOSTS-BACKEND-01 (the host agent, its enrollment and the host card) — on `origin/dev`.

## Frozen inputs
- API contract: unchanged (no operation, no schema); the module calls `HostsService.issue_enrollment` / `list_hosts` in process.
- migration head: `0071_run_restart`, unchanged.
- base commit: `origin/dev` `555a67c2b`.

## Scope
- new: `infra/deploy/local-agent.sh` (connect / status / disconnect), `infra/deploy/local_agent_clis.py` (finds the clients, writes
  the wrappers in `/opt/pdf-analysis-cli/bin`), `src/auditmanager/bootstrap/local_host.py` (the stand's half, run in the `api`
  container);
- changed: `tools/executor-runner/install.sh` (`--login-user`, `--max-images`), `infra/deploy/deploy.sh` (a last, non-failing step),
  `infra/deploy/env/alpha.env.example` (`ALPHA_LOCAL_AGENT=auto` and three optional settings), the two READMEs, release note 0.33.0.
- not touched: contracts, migrations, web, the agent's protocol, the composition root.

## Checks
- `bash -n` and `shellcheck -S warning` on `local-agent.sh`, `install.sh`, `deploy.sh`;
- `tests/unit/executor_runner/test_login_user_install.py`, `test_local_agent_clis.py`; `tests/unit/bootstrap/test_local_host.py`;
- `tests/integration/executors/test_local_host_db.py` on a throwaway PostgreSQL migrated to head;
- the existing installer suites (`test_host_install.py`, `test_agent_install.py`, `test_agent_package.py`) and the release-note form;
- `local-agent.sh status` and the another-stand refusal of `connect` on adm1, which must leave its production agent untouched.

Not provable on the development host: a real `connect` end to end (adm1's one agent serves the production stand, and the shared venv
cannot run the application). The first real run is on the fork's server.

## Rollback
`ALPHA_LOCAL_AGENT=off` (or no line) stops the deploy step; `sudo infra/deploy/local-agent.sh disconnect` removes the agent and the
wrappers; the card is archived in «Диспетчер». Reverting the commit restores `install.sh` and `deploy.sh`.

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none

## Publication authority
- development_target: origin/dev
- origin_main_authority: none; R-158d publishes to dev only
