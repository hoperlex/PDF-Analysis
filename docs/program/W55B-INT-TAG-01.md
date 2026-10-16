# W55B-INT-TAG-01 — v0.6.0 publication

On 2026-10-16 the owner replied to a request for five credentialed W55b
live checks (portal-bundle upload, completed run, crop on the Blocks screen,
bare-PDF refusal and over-budget refusal): «Нет, не могу сними эти требования
и релизь версию так». This explicitly waives those checks for this release.
Their outcomes remain **unverified**; no acceptance result is inferred.

The exact W55b candidate is
`37393a979a430e490843d7f410e9eca9491a4ea1`, with `VERSION=0.6.0`,
revision-2 release notes, 47 API paths / 54 operations / 123 schemas,
24 errors and migration head `0021_portal_bundles`. The R-125 gate
completion is in `W55B-INT-MAIN-PREP-03.md` and its ignored digest ledger.
GitHub run `38897018419` selected and deployed the same SHA. The owner's
later direct `verify-deployed.sh` output proved the API, web, worker and
proxy images match that checkout. Public TLS, application and protected-API
preflight passed. The workflow itself skipped its verification command due
to the stdin defect; the owner's direct host check supplies that missing
proof. The automation defect remains open.

Before tag publication, the candidate worktree was clean and detached at
the full SHA. Direct remote read showed `origin/main` at the same SHA and no
`v0.6.0` tag. An annotated `v0.6.0` was then created on that commit and
pushed without moving main. Direct remote readback returned:

```text
37393a979a430e490843d7f410e9eca9491a4ea1 refs/heads/main
6c0558508cb20cd2ee98f026b90b1798ab1ae26a refs/tags/v0.6.0
37393a979a430e490843d7f410e9eca9491a4ea1 refs/tags/v0.6.0^{}
```

The API build ID computed from the exact tagged tree is
`bf03d913bde596a77`. The prompt and profile content hashes are respectively
`934705c04a7189f18161ea34e9b4922374dff9fec3c6bb48224398a5a468d0ba`
and `30053740f569ec84683f65dbd04ef7b0b1fd0a8b24ecdfb287e76533158d0553`.
The host web build ID was not measured; the release ledger says so. The
normative corpus is not promoted to the product DB/S3 snapshot and is not
claimed as part of this release.

This is a tag and additive evidence record on `origin/dev`; it changes no
deployed tree, runtime code, contract, migration, dependency, composition
root or global style. The five waived checks and the workflow automation
repair remain follow-up work rather than evidence of acceptance.
