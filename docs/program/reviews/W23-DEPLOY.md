# `W23-DEPLOY` — `infra/deploy/deploy.sh`, and which half of `PA-01` criterion 1 it closes

**Session** `W23-DEPLOY`. **Base** `5ed72cc` (`origin/dev`), which contains `6e07b97`.
**Branch** `agent/w23-deploy`.

This file is opened before the first edit and appended to as the work happens, because a
plan that points at a scratchpad is a dead reference the moment the session restarts.

## 0. The premise I checked first, and it was false

The brief quotes `PA-01` criterion 1 as:

> `deploy.sh` brings the stack up from a clean clone on a machine that has never run it,
> and **the schema the migrations produce is the one the application expects**.

`docs/program/ALPHA_ROADMAP.md:313` does not say that. It says:

> `deploy.sh` brings the stack up from a clean clone on a machine that has never run it,
> and **the schema the running app serves conforms to the frozen
> `contracts/api/v1/openapi.json`** — the same check the gate runs, re-run against the
> deployed process rather than against a build artifact;

The second clause is about the **API schema**, not the database schema. The brief's STEP 2
item 3 therefore sends me at `make check-db` and `tests/integration/db`, which bear on a
different claim. Both are answered below, and which one the criterion actually asks for is
stated rather than blurred.

## 1. Work log

(appended as it happens)
