# W52-INT-129REVOKE-01 — operator revoke prose corrected

`access.revoke` still described the pre-W49 system as having no roles and no
use of `permission_denied`. The current API has both. Its module docstring now
states the current boundary: bulk credential revocation is a host-operator
command; an HTTP operation would need an explicit contract and authorization
rule. No executable revocation code or role policy changed.

Changed files: `src/auditmanager/access/revoke.py`,
`docs/program/CURRENT_STATE.md`, `docs/program/DEBT_REGISTER.md`,
`docs/program/tasks/W52-INT-129REVOKE-01.md` and this report.

Python compilation, governance/prose tests, frontend lint and
`git diff --check` passed. Database, stand, QA and full gate were not run under
the owner's deferral; D-139/D-140 retain them. No contract, migration,
dependency, composition root, global style or runtime statement changed.
Publish only to `origin/dev` after exact remote-ref and fast-forward checks.
Revert this one commit if rolled back; no feature flag is needed.
