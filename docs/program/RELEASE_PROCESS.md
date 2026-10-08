# Release process

This file describes the product release record. `VERSION` is the one-line
canonical SemVer product version; package and project metadata versions do not
move with it. The highest non-archive entry under `release-notes/` must equal
`VERSION`. A release is an owner-authorized deployment of a user-visible change
from `origin/main`, followed by a `v<VERSION>` tag. Development publication to
`origin/dev` does not create a release.

## Authors and review

The assigned release-notes author writes `release-notes/<version>.json` in
Russian, validates it against the sealed shape and the gate-time prose rules,
and records one commit or test for every product claim in the task hand-back.
The author increments `revision` for every content correction, including an
edit to title or date. The independent `W52-NOTES-JUDGE` checks each claim
against the diff and the tree; the judge runs again on the final candidate
after fixes. From W53 onward, the release integration task includes that
independent judgment. The integration owner checks the form tests and verdict
before publication.

`screen` and `where` are authored display history. The current `VERSION` entry
must point to today's screen registry and begin with the current group and
screen labels. Older entries retain their release-time paths even if the
navigation later changes. The loader checks the sealed JSON shape at deploy;
prose and dictionary checks run in the gate so a later dictionary change cannot
make a historical deployment fail.

## Version move and publication

Move `VERSION` only with a new, highest non-archive release-notes entry and a
reviewed user-visible change. Keep previous entries in the image. A file that
reached `main` is never deleted or rewritten at the same authored revision:
the loader appends a higher revision, refuses a changed equal revision, and
retains historical rows on rollback. A correction or withdrawal is expressed
by another revision of that version. The API serves the highest revision no
higher than the running `VERSION`.

The integration owner first publishes the checked development candidate to
`origin/dev`. Release validation supplies independent review, the exact
candidate's full `make gate` with literal `GATE OK`, and the required live and
manual acceptance. `origin/main` triggers deployment and requires the owner's
separate direct instruction naming that exact SHA. Follow
[`MAIN_AUTODEPLOY_POLICY.md`](MAIN_AUTODEPLOY_POLICY.md): re-read `main`, prove a
fast-forward, publish the verified SHA without a later fix, then confirm the
workflow and `infra/deploy/verify-deployed.sh` on the deployment host. The
release task tags `v<VERSION>` only after the deployment evidence is complete
and fills one measured row of `RELEASES.md`.

## Hotfix and rollback

Create a hotfix branch from the affected release tag. Make the bounded fix and
release-note revision, run the full gate on its exact candidate, obtain the
owner's exact-SHA `main` instruction, and fast-forward `main` through the same
deployment verification. Merge the hotfix back to `dev` so the development
line retains it. A rollback is a reviewed forward revert with a fresh gate and
deployment verification; never force-push or move `main` backward. An older
image may hide database releases above its `VERSION`, but published note files
remain part of the repository history and image input set.
