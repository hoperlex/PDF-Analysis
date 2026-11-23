# Task FORK-L6-OFFDISK-BACKUPS — encrypted copies off the server's disk

## Outcome
Copies of the database and objects leave the server's disk, encrypted on the client side, with a monthly restore drill.
Until this lands, losing the disk means losing the database. While it holds only the norms corpus, re-installing is the recovery path (`R-156i`).

## Owner and paths
The fork's operations lane: `infra/deploy/backup.sh` (new), its systemd timer, the `ALPHA_BACKUP_*` env names and `DEPLOYMENT_RUNBOOK.md`.

## Depends on
- **The owner's decision on the off-disk target (poll).** It is due before the first client data.

## Shape (the plan; build after the decision)
- `backup.sh` takes the `reset.sh` format (`database.dump`, `objects.attrs`, `objects/`) without the destructive step, and passes it to restic with client-side encryption, sending it to the off-disk target.
- It runs nightly and before every migrating deploy.
- A monthly restore drill runs in a throwaway compose project.
- Env: `ALPHA_BACKUP_REPOSITORY`, `ALPHA_BACKUP_KEEP_{DAILY,WEEKLY,MONTHLY}`, `ALPHA_BACKUP_SCHEDULE`. The restic password and the target's keys live only in the env file on the server.
- `ADR-0022` section 7: an erased project lives on in copies until their retention ends. This is accepted together with the decision.

## Checks
- A backup followed by a restore into a throwaway project.
- The restore drill's record.

## Integration and rollback
The timer can be disabled; the copies are kept by their retention.

## Enumerator ownership
- enumerated_set_changed: no

## Captured premise evidence
- premise: none

## Historical evidence
- correction_mode: none

## Publication authority
- development_target: origin/dev
- origin_main_authority: none; the fork's delegated release integrator publishes main
