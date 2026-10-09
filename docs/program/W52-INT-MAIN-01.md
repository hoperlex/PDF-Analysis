# W52-INT-MAIN-01 — pre-publication reconciliation

On 2026-10-08, the owner directly instructed publication of the current
`origin/dev` version to `origin/main` and clarified that this is direct
main-publication authority. At the remote read, dev was `fd78ad8c76f21e034d81c0b1af0e8c2d1d75b022`
and main was `1e9bb1308b7b97cd75eef28e206b23c569871b68`.

The first merge candidate, `91292fe40cd01bc05f286557a88c09f58b7a5156`,
had exactly those two parents. Its product files matched dev; it additionally
retained main's W51 hotfix task and introduced the current publication task.
The only content merge conflict was the rendered-language guard. The accepted
dev blob won, retaining both the backported W51 correction and later D-128
coverage. A production Next.js build on this candidate passed, including its
type check.

The first complete gate attempt had no `GATE OK`. Foundation passed 35 tests;
the Python battery exposed two inherited integration defects and a task-record
failure before the interrupted diagnostic run: 1,989 passed, one failed and
170 setup errors. `migrated_database_factory` and its template were not
re-exported to access and W49 API QA suites after W52-GATE-01 changed the DB
fixture. W13 characterization left `AUDITMANAGER_PROVIDER_MODE` in the process
environment, which PC-01 correctly refused. The current governance guard also
requires the main-only W51 task to name a commit reference and the new task to
carry its four required sections.

The integration correction is limited to those fixture exports, removal of the
unnecessary environment assignment, and task-record metadata. It changes no
contract, migration, dependency, composition root, global style, deployment
input or product runtime. The correction must pass focused checks and a fresh
complete gate on one clean SHA before either remote ref is updated. The exact
candidate, workflow run and host verification are reported after publication;
no post-gate documentation commit is made to `main`.
