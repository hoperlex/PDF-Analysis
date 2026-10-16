# W55B-INT-MAIN-VERIFY-ADDENDUM-01 — manual host verification of W55b

`W55B-INT-MAIN-01.md` correctly reported that workflow run
[`38897018419`](https://github.com/hoperlex/PDF-Analysis/actions/runs/38897018419)
ended after `deploy.sh` without executing the later verification lines of
its remote stdin script. Its green status by itself remains insufficient
evidence. The owner then ran, on the deployment host, on 2026-10-16:

```text
cd /srv/auditmanager && infra/deploy/verify-deployed.sh
```

The returned output identified `auditmanager-prod` at checkout
`37393a97`, loopback proxy `127.0.0.1:8080`, and the protected API's 401.
It compared all repository inputs in the API image (including 277 `src/`
files, 25 `db/` files, 36 contract files, `VERSION` and `uv.lock`), 564
`web/` files, the analogous worker image inputs and one proxy configuration
file; every group was `identical`. Its final line was:

```text
verify-deployed.sh: the deployed stack IS this tree (37393a97).
```

That line is the script's last command and is reached only after its drift
and unanswerable branches have been passed. It establishes a zero exit on
this command's successful path. The owner did not supply a separate numeric
`echo $?`; this conclusion follows from the script's control flow. The
directly read `origin/main` and workflow head SHA are both
`37393a979a430e490843d7f410e9eca9491a4ea1`, binding the host's short
form to the exact published tree. Public TLS and application-boundary
preflight had already passed on that candidate.

The W55b **main deployment is now verified for the exact tree**. The
workflow's skipped verification remains a real automation defect, with an
isolated repair candidate under separate gate; do not cite its green job
alone as host proof. The owner's credentialed W55b in-product journey and
release tag remain open. This addendum changes no code, host, `origin/main`
or corpus data.
