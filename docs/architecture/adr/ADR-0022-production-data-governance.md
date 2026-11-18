# ADR-0022: Production data governance: what is kept, how a project is erased, what leaves the host

- Status: accepted (the legal-hold authority is settled by `R-146aj`; the classification labels stay open by `R-146ak`)
- Date: 2026-10-26; revised 2026-11-18 (ADR-OPTIMISE-01)
- Basis: `PRODUCTION-ADR-PACK-01`; owner rulings `R-146b`, `R-146c`, `R-146f`, `R-146m`, `R-146n`, `R-146o`, `R-146aj`, `R-146ak`; `AD-06` confirmed by `R-146o`; `AD-07`, `AD-08`, `AD-09`, `AD-16` by `R-146w` as written at commit `83600aed`; fork note: `R-156f`, `R-156i`
- Amends: `ADR-0012` (erase exception, `R-146o`); supersedes nothing. Fills the retention and erasure half that `ADR-0014` and `contracts/domain/v1/identifiers.json` (`OPEN-RETENTION`, `U-04`) left open

## Context

The production release may receive real client documents from the day it is released, with no
precondition of provider terms or expert acceptance (`R-146f`). The owner chose no automatic retention
limit and a journalled operator operation that erases one project (`R-146c`), manual copies (`R-146b`),
a purge of the closed beta's test data (`R-146m`), and an offline copy of the secret key ring but
**not** any restriction of what the model provider may do with the text it receives (`R-146n`). Forces:
Blobs are content-addressed and shared (`R-76`); `audit_event` and `expert_decision_event` are
append-only by trigger; the frozen domain contract says "Erasing bytes never deletes decision, finding
or audit history" (`contracts/domain/v1/state-machines.json`).

## Decision

### 1. The data inventory

| Data | Client content | Removed by |
| --- | --- | --- |
| Source PDF, portal bundle, crops, extracted-text artifacts, price-list files (S3 objects, `blob` rows) | yes | project erase (section 3) |
| Project, document and file names | may identify the client | project erase |
| Findings, evidence quotes, expert comments and verdicts (`expert_decision_event`) | yes | project erase (`AD-06`) |
| Model-call records (`model_call`) | no text | project erase |
| Executor task payloads and answers (`executor_task`) | yes | 7 days after terminal, only when a runner polls; project erase |
| Run and execution journal (`audit_event`) | identities only | not by erase; by the 1.0 purge |
| Accounts and roles | personal data of staff | `purgeUser`; kept by every purge |
| Norm corpus | no (`NORM-Q04`) | untouched |
| Sealed connection secrets (`executor_secret`) | secrets, sealed | administrator |
| Session register (`web-sessions` volume) | credentials | expiry |
| Manual copies (`infra/deploy/dumps/`, the copy directory) | everything | the operator, by hand |
| Provider side (OpenRouter and its routes) | the document text of every call | not reachable (`A-2`) |

### 2. Retention (`R-146c`)

There is **no automatic retention limit** for client data: a project's data lives until an operator
erases the project. The seven-day clearing of executor payloads continues and is not a commitment. No
TTL value is declared anywhere, as `OPEN-RETENTION` requires before the owner's input (`R-146c`).
**Legal hold (`R-146aj`):** the product has no hold mechanism in 1.0; a hold is a rule of procedure, the
owner's word is the only ground on which the operator erases a project on which a hold is claimed, and
an erase never runs without the owner's permission (decision 3); the erase checks no hold.
Classification labels: none introduced or fixed (`R-146ak`); the question stays open.

### 3. The operator project erase (`R-146c`, `R-146o`)

`AD-06`, confirmed by `R-146o` in full: the erase of one project removes its documents, pages, files,
extracted text, crops, findings, evidence quotes, comments and expert decisions; what stays is the
record of the erasure itself (who, when, what, hashes). `AD-07` (the design below, including that the
identity-only run journal stays) is confirmed by `R-146w`.

**Tool and inputs.** `infra/deploy/erase-project.sh` (dry run by default) over
`scripts/recovery/project_erase.py`; procedure: `docs/program/DEPLOYMENT_RUNBOOK.md` section 17. The
tool refuses any role but the migrator's (`ADR-0021` `AD-02`). The project is named by identity
(`prj_<ULID>`), never by name; the actor is an active `admin`; the reason is one of `client_request`,
`end_of_engagement`, `test_data`, `other` (free text would put personal data into an append-only table);
`--owner-permission-ref` is **required to apply or resume** (`R-146aj`): one line saying where the
owner's permission is recorded, written into both journal events, never verified; an apply needs the
plan digest of a dry run.

**Scope.** Every row reachable from `project` by foreign key (a closure, not a hand list), the project's
rows of `vendor_list_revision` and their entries, the idempotency receipts of the erased rows, and every
Blob that no other project and no KEEP table references, with its object. `worker`, the global vendor
list and everything account-side stay. A table in neither the closure nor an explicit keep list stops
the tool before it touches anything, so a migration that adds a table is a decision about that table
(`D-213`). **Kept:** accounts, roles, registrations, release notes, executor configuration, the norm
corpus; **the record of the erasure** (the `erasure.requested` and `erasure.completed` events and the
manifest file); **the project's run journal**, whose `audit_event` payloads are identities and
classifiers only (`R-146o` says only the record of the erasure stays; that this includes the journal is
part of `AD-07`); a Blob still referenced elsewhere, with its object.

**The exception (`R-146o`).** `ADR-0012` makes expert decisions append-only, and the frozen domain
contract says erasing bytes never deletes decision, finding or audit history. `R-146o` grants a
**deliberate exception** to both for this one operation (`ADR-0012` carries the addendum). The frozen
file is **not edited**: the sentence stays true of the Blob `erased` transition, which this operation
does not use; a clarifying edit is a contract-owner item (`PROD-22`, still open). It is the one place
where the append-only and immutable triggers are switched off: one named trigger at a time inside the
transaction, switched on again before commit, the state compared before and after; only the table owner
can do it, not the application role.

**Erased Blobs leave no row (`AD-07`).** The tool deletes the `blob` row with its object (a row left in
the terminal `erased` state would meet a byte-identical re-upload), so a later upload of the same bytes
declares a fresh row. What the owner's "hashes" need is kept in a manifest of the erased Blobs
(`blob_id`, SHA-256, size, media type) written next to the plan, whose SHA-256 is a field of the erasure
event; the operator keeps the manifest file with the release record, and the database keeps no
fingerprint of client content.

**Phases (`AD-07`).** Object deletion must not be a dual write (`AGENTS.md` section 4):

1. *Plan* (read-only, always first): guards, row counts, exclusive and shared Blobs, object keys and a
   plan SHA-256; nothing is journalled.
2. *Commit* (one transaction): re-derive and compare the plan, advisory lock, append
   `erasure.requested`, move every exclusive Blob to `erasure_pending`, delete the project's rows with
   the trigger switch, verify that every keep row is unchanged by count and digest and every trigger is
   restored.
3. *Objects*: delete each exclusive Blob's object by exact key (a 404 counts as done).
4. *Finish* (one transaction): delete those Blob rows, append `erasure.completed` with the manifest
   digest.

A crash after phase 2 leaves Blobs in `erasure_pending` and nothing referencing them; `--resume
era_<ULID>` completes phases 3 and 4. Re-running a finished erase exits 0 with "nothing to do"; a
project that never existed is a refusal.

**Guards and journal.** The tool refuses unless the project exists and is idle (a non-terminal run, job,
attempt or executor task refuses, a claimed remote task included: `D-215`), the role owns the tables,
the schema head equals the declared head, the classification is closed, no other erase or purge runs,
the actor is an active `admin` and the permission reference is present. Events `erasure.requested` and
`erasure.completed` (aggregate `ErasureRequest`, id `era_<ULID>`; no table is added) carry identities,
counts, digests and the permission reference only; `product_purge.py` keeps the `erasure.` prefix.

**What an erase does not reach** (the tool says so at the end; runbook section 17): every copy outside
the live service (dumps, mirrors, the `R-93` restore-test copy, provider snapshots), which the operator
ages out by hand and records; the model provider and its routes (`A-2`); a remote executor's local
copies; disk blocks, container logs and exports already downloaded; the legal-hold question (`R-146aj`).

### 4. The purge of the closed beta's data at the release (`R-146m`)

`AD-09`, confirmed by `R-146w`. At the 1.0 release the operator runs
`infra/deploy/purge-product-data.sh`. It has no selector for the removed AR v1 and v2 paths: it removes
**all** product data, test runs of every section included, and keeps accounts, the norm corpus, executor
configuration and release notes; the operator then reviews the account list and archives or purges the
test accounts. Preconditions: the owner confirms that the stand holds only test data (`R-141c`); the
tool's own verified dump is taken first and deleted by hand after the release is accepted; the rehearsal
runs it on a restored copy first. `KEEP_EVENT_PREFIXES` includes `access.` and `erasure.` (`ADR-0023`).

### 5. Egress to the model provider (`R-146e`, `R-146f`, `R-146n`)

OpenRouter is the base connection; `R-133` is unchanged. A call sends the system prompt of the profile
and the recorded text layer of the document analysed (all pages in one request for the text profiles)
and, once a stage that sends them is activated, selected PNG crops of pages. The source PDF is not sent;
no project, file or account name and no run identity is in the body. The destination is the
administrator-configured connection (`AUDITMANAGER_EXECUTOR_ALLOWED_HOSTS` optionally narrows it); any
other executor connection receives the same payload, so this statement covers the OpenRouter base only.

**Accepted risk A-2 (`R-146f`, `R-146n` item 4 not accepted).** The tree holds no provider terms, data
processing agreement, consent or data-handling policy, and the product asks OpenRouter for no routing
restriction, no ban on retention or training and no ban on model substitution (`R-133` turns a different
reported model into a typed failure, but after the text has been sent). Document text therefore reaches
OpenRouter and whichever provider it routes to, which may retain or train on it; the owner bears this
risk and nothing in the product mitigates it. Reopen trigger (`AD-16`, confirmed by `R-146w`): the first
client who asks for data-handling terms, any contract that promises confidentiality, or the owner's
decision to accept `R-146n` item 4.

### 6. Key-ring custody (`R-146n` item 7)

The ring (`AUDITMANAGER_SECRETS_KEYS` in `provider.env`, read by the worker only, in no database, bucket
or backup) alone opens a sealed connection secret; a restore onto another host leaves the connections
`secret_unreadable` until it is installed. `AD-08`, confirmed by `R-146w`: after the ring is generated,
the operator makes one encrypted copy of `provider.env` on a medium that is neither the VPS, nor the
repository, nor the dump directory, with the passphrase or recipient key held by different means than
the copy; the copy is verified on a second machine by decrypting it and comparing the SHA-256 of the
ring line there and on the VPS, and redone after every rotation; the release record carries the date,
the key ids and that SHA-256. The ring is never put in a dump, in the repository, in a message or in the
output of `docker compose config` (`DEPLOYMENT_RUNBOOK.md` section 18).

### 7. Manual copies and their limits (`R-146b`)

A manual copy is a `pg_dump` (all client text, the password hashes, the sealed secrets) and optionally a
bucket mirror (every document). It is not encrypted, sits on the host's disk and lacks the key ring. It
contains erased data until deleted (section 3); a restore brings back accounts and credentials as they
were, so every credential is revoked and default passwords are reported (`R-52`, `ADR-0023`); schedule
and recovery point: `A-1`, `ADR-0021`.

**Fork (`R-156f`, `R-156i`).** After the fork's bucket lane the documents' bytes are held by the
object-storage provider in the region the owner chooses: one more place where data leaves the host. Copies
stay as above until the off-disk backup decision (`R-156i`); that decision states the copies' retention
period, until which erased data lives in them.

## Consequences

- Positive: a client's data, expert decisions included, can be removed on request by a tested,
  dry-runnable, journalled, repeatable script.
- Cost: the erase is the one place the append-only contract is overridden (`R-146o`) and is reversible
  only from a copy; erased data survives in every copy, at the provider (`A-2`) and on disk blocks
  ("erased" means "removed from the live service"); a lost manifest file proves nothing about what was
  erased.

## Alternatives considered

1. **Delete bytes only and keep findings and decisions** — rejected by `R-146o`: quoted client text
   stays in the database.
2. **Keep the `blob` row of an erased document in the frozen `erased` state** — rejected: a
   byte-identical re-upload would meet a terminal row.
3. **An automatic TTL** — declined by `R-146c`.
4. **An erase through the API** — rejected for 1.0: it needs a contract reseal and a trigger-disabling
   path behind the application role.
5. **Restrict routing to providers that do not retain or train, and ban substitution** — not accepted by
   the owner (`R-146n` item 4); `A-2`.

## Verification

`tests/integration/recovery/test_project_erase.py`, `test_project_erase_shapes.py`,
`tests/unit/recovery/test_project_erase_pure.py`: each guard shown able to fail, keep rows and triggers
unchanged after a run, a second `--apply` exits 0, `--resume` after a crash between the phases
completes, a shared Blob keeps its object, a byte-identical upload after an erase creates a fresh `blob`
row (`AD-07`). At rest: no `blob` row in `erasure_pending`; the erased `project_uid` counts `0` and an
`erasure.completed` event names it. Operational: an erase rehearsal on a restored copy (`PROD-17`).

## Revisit trigger

Replace this ADR when the owner gives the product a legal-hold mechanism (`R-146aj`: a rule of procedure
for 1.0) or decides the classification labels (`R-146ak`), when a client contract imposes a retention
period or an erasure deadline, when an off-host copy is introduced, when the owner rules on provider
terms (`A-2`), or when multi-organisation access is added (`ADR-0023`).

## History

- 2026-10-26 — accepted for production by the repository owner; the `AD-` confirmations in Basis came by
  `R-146o` and `R-146w`.
- 2026-11-18 — compressed (ADR-OPTIMISE-01); the full earlier text: git show fb6c2203e:docs/architecture/adr/ADR-0022-production-data-governance.md
- 2026-11-18 — status statements updated to dev fb6c2203e: the erase tool, wrapper and tests exist
  (`PROD-07A-PROJECT-ERASE-CORE-01`); `--owner-permission-ref` is required (`R-146aj`); the legal-hold
  authority is settled by `R-146aj`, the classification labels stay open (`R-146ak`); `PROD-22` is still
  open.
- 2026-11-18 — fork note (`R-156f`, `R-156i`): the bucket provider holds the fork's documents; copies wait for the backup decision.
