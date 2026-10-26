# ADR-0022: Production data governance: what is kept, how a project is erased, what leaves the host

- Status: accepted for production by the repository owner (`R-146b`, `R-146c`, `R-146f`, `R-146m`, `R-146n`); the implementation choices marked `AD-` are the architect's, proposed and not yet confirmed
- Date: 2026-10-26
- Owners: repository owner / `PRODUCTION-ADR-PACK-01`
- Supersedes: nothing; it fills the retention and erasure half that `ADR-0014` left open and that `contracts/domain/v1/identifiers.json` (`OPEN-RETENTION`, `U-04`) reserves
- Related principles: P-01, P-03, P-06, P-07, P-13, P-15, P-18

## Context

The production release may receive real client documents from the day it is released, with no
precondition of provider terms or expert acceptance (`R-146f`). The owner chose no automatic
retention limit and a journalled operator operation that erases one project (`R-146c`), manual
copies (`R-146b`), a purge of the closed beta's test data at the release (`R-146m`), and a package
that includes an offline copy of the secret key ring but **not** any restriction of what the model
provider may do with the text it receives (`R-146n`). The legal-hold authority and data
classification labels were not asked and stay open (`ADR-0014`).

Facts read from the tree at `4d7b7c38` on 2026-10-26:

- **Where client content sits.** Bytes are S3 objects addressed by `blob_id`; a `blob` row holds
  state, SHA-256, size and media type, and no key or bucket. A Blob is content-addressed and shared:
  `uq_blob_available_content` makes one object of equal bytes, and `R-76` lets a corpus admission and
  a project reuse it. The references to a Blob are a closed set (`blob_reference_audit._SOURCES`):
  `input_manifest_entry`, `analysis_artifact_publication`, `norm_custody_admission`,
  `norm_custody_binding`, `norm_retrieval_set` (two columns) and `price_list_revision`.
- **Client text in PostgreSQL.** `project.name`, `document.display_title` and
  `document_version.source_filename` can name the client; `finding_observation.finding_text` and
  `recommendation_text` (to 4000 characters), `finding_evidence.quote` (to 2000) and
  `expert_decision_event.comment` (to 4000) hold verbatim or derived document text and expert
  words; `executor_task.payload` and `answer_text` hold what a remote executor was sent and
  returned. `model_call` stores request and response checksums, tokens, latency and cost, never the
  prompt or the answer (its table comment). `audit_event` payloads are identities and controlled
  classifiers (`src/auditmanager/jobs/events.py` allow-lists the keys).
- **The only automatic retention in the code.** `executor_task.payload` and `answer_text` are set to
  `NULL` seven days after the task is terminal (`PAYLOAD_RETENTION_DAYS` in
  `src/auditmanager/executors/runner.py`); the housekeeping runs inside a runner's claim call, so a
  stand where no runner polls never runs it. It is not a retention policy and is not extended.
- **Append-only structures.** `audit_event` and `expert_decision_event` are append-only by trigger
  (`am_append_only`); published rows such as `document_version` and `finding_observation` are
  immutable by trigger (`am_immutable_row`). The frozen domain contract has an `ErasureRequest`
  identity (`era_`, "not allocated in PC-01"), a Blob state machine `available` to `erasure_pending`
  to `erased`, and the sentence "Erasing bytes never deletes decision, finding or audit history"
  (`contracts/domain/v1/state-machines.json`). No code implements erasure: `src/auditmanager/storage/README.md`
  says P01 "must not approximate" it.
- **Deletion tools that exist.** `scripts/recovery/product_purge.py` (wrapped by
  `infra/deploy/purge-product-data.sh`) removes **all** product data and keeps accounts, the norm
  corpus, executor configuration and release notes. It classifies every table as PRODUCT, KEEP or MIXED
  and refuses an unclassified one, takes a verified dump first, truncates the product tables, deletes the
  mixed tables' product rows after switching off `audit_event`'s one append-only trigger inside the
  transaction, and deletes objects by exact key after the commit. It needs the table owner. There
  is no project-scoped deletion. `purgeUser` (`DELETE /users/{user_uid}`) removes an account.
- **The key ring.** The private ring is `AUDITMANAGER_SECRETS_KEYS` in `provider.env`, read by the
  worker only, and "is not in PostgreSQL, S3 or any backup" (`DEPLOYMENT_RUNBOOK.md` section 14).
- **What a model call carries.** The text stage sends the system prompt and the whole recorded text
  layer of the document in one request; nothing identity-bearing (no run id, no file name, no project
  name) enters the body (`build_request` in `src/auditmanager/analysis/text/adapter.py`). A selected
  PNG crop can ride a request, but no run stage sends one until the vision policy is activated
  (`CURRENT_STATE.md`).

## Decision

### 1. The data inventory

| Data | Where | Client content | Removed by |
| --- | --- | --- | --- |
| Source PDF, portal bundle, crops, extracted-text artifacts, price-list files | S3 objects; `blob` rows; bound by `input_manifest_entry`, `analysis_artifact_publication`, `price_list_revision` | yes | project erase (section 3) |
| Project, document and file names | `project`, `document`, `document_version` | may identify the client | project erase |
| Findings, evidence quotes, expert comments and verdicts | `finding`, `finding_observation`, `finding_evidence`, `expert_decision_event` | yes | project erase (`AD-06`) |
| Model-call records | `model_call` | no text | project erase |
| Executor task payloads and answers | `executor_task` | yes | 7 days after terminal, only when a runner polls; project erase |
| Run and execution journal | `audit_event` | identities only | not removed by erase; removed by the 1.0 purge |
| Accounts and roles | `app_user`, `app_user_role`, `registration_request` | personal data of staff | `purgeUser`; kept by every purge |
| Norm corpus | `norm*` tables, S3 objects | no (licensing `NORM-Q04`) | untouched |
| Sealed connection secrets | `executor_secret` | secrets, sealed | administrator |
| Session register | the `web-sessions` volume | credentials, not documents | expiry |
| Manual copies | `infra/deploy/dumps/`, the copy directory | everything | the operator, by hand |
| Provider side | OpenRouter and whatever it routes to | the document text of every call | not reachable (`A-2`) |

### 2. Retention (`R-146c`)

There is **no automatic retention limit** for client data. A project's data lives until an operator
erases the project. The seven-day clearing of executor payloads continues as it is and is not a
commitment. No TTL value is declared anywhere; this satisfies the rule of `OPEN-RETENTION` that no lane
declares one before the owner's input, which `R-146c` now gives. The legal-hold authority is **open**:
the product has no hold concept, an erase does not check one, and the operator is responsible for not
erasing a project that is subject to a hold. Data classification labels are open.

### 3. The operator project erase (`R-146c`)

`AD-06`, `AD-07` (architect's implementation decisions within `R-146c`, to be confirmed).

**Entry points.** A new `infra/deploy/erase-project.sh` (guards, dry run by default, runs inside the
`api` image like `purge-product-data.sh`) and a new `scripts/recovery/project_erase.py` modelled on
`product_purge.py`. It connects as the migrator role (`ADR-0021` `AD-02`) and refuses any other.

**Inputs.** `--project prj_<ULID>` (an identity, never a name); `--actor <login>`, which must be an
active account holding `admin` and is resolved to its `usr_` identity; `--reason`, one of a closed list
(`client_request`, `end_of_engagement`, `test_data`, `other`; free text is refused because it would
put personal data into an append-only table); `--dry-run` (the default) or `--apply --plan-sha256
<hex>`; `--resume era_<ULID>`.

**Scope: what it removes.** Every row reachable from `project` by foreign key, which is the
project-scoped subset of the `PRODUCT_TABLES` of `product_purge.py`, found by a foreign-key closure
from `project` and not by a hand list, plus the `project_uid IS NOT NULL` rows of
`vendor_list_revision` and their entries; the idempotency receipts (`command_record`) of the erased
rows; and the bytes of every Blob that no other project and no KEEP table references. `worker`, the
global vendor list (`project_uid IS NULL`) and everything account-side are not project-scoped and stay.
A table that is in neither the closure nor an explicit keep list stops the tool before it touches
anything, as in `product_purge.py`; a migration that adds a table is therefore a decision about that
table (`D-213`).

**What it must keep.**

- Accounts, roles, registrations, release notes, executor configuration, the norm corpus.
- **Every `audit_event` row**, including the project's run journal: the payloads are identities
  and classifiers only, and "an audit entry that a cascade could delete is not an audit trail"
  (the comment on `audit_event.aggregate_id`). The erase appends its own events (below).
- **The `blob` row of an erased Blob**, moved through the frozen state machine to `erased` with its
  SHA-256, size and media type, because the domain contract says metadata and checksums are
  retained (`AD-06`: the alternative is to delete the row, which contradicts that text).
- A Blob still referenced elsewhere, with its object. A shared Blob loses only this project's
  bindings.

**The ledger question (`AD-06`).** `ADR-0012` makes expert decisions append-only: a verdict change is a
new event and nothing rewrites a human event. Erasing a project does not change a verdict; it removes
the aggregate, and it is the one operation allowed to do so, only through this tool, only as the
table owner. The database triggers that refuse `DELETE` on the project's immutable and append-only
tables are switched off one named trigger at a time inside the transaction and switched on again
before it commits, with the trigger state compared before and after, exactly as `product_purge.py`
does for `audit_event`; the application role has no privilege to do this (`ADR-0021` `AD-02`). The
domain contract's "never deletes decision, finding or audit history" describes what erasing
**bytes** means for a Blob and the Blob rows here follow it; the decision and finding rows of the erased
project are removed because they carry verbatim client text (evidence quotes to 2000 characters,
comments to 4000). This is the point the owner is asked to confirm; if the answer is "keep them", the
text columns cannot be cleared (the rows are immutable) and the erase degrades to deleting bytes only.

**Phases (`AD-07`).** The external side effect (object deletion) must not be a dual write
(`AGENTS.md` section 4):

1. *Plan* (read-only, always run first): guards, per-table row counts, the Blob list classified
   exclusive or shared, the object keys, and a plan SHA-256. Nothing is journalled.
2. *Commit* (one transaction): re-derive and compare the plan, take an advisory lock, append
   `erasure.requested`, move every exclusive Blob to `erasure_pending`, delete the project's rows with
   the trigger switch, verify that every keep row is unchanged by count and digest and every trigger is
   restored, commit.
3. *Objects*: delete each exclusive Blob's object by exact key (a 404 counts as done).
4. *Finish* (one transaction): move those Blobs to `erased`, append `erasure.completed`.

A crash after phase 2 leaves Blobs in `erasure_pending` and nothing referencing them; the same command
with `--resume era_<ULID>` completes phases 3 and 4. Re-running a finished erase finds
`erasure.completed` for the project and exits 0 with "nothing to do". A project that never existed is
a refusal.

**Guards.** The project exists and no run, job, attempt or executor task of it is non-terminal (a
claimed remote task counts: `D-215` is the cautionary case); the connected role owns the tables; the
schema head equals the declared head and the classification is closed; another erase or purge holds no
lock; the actor is an active `admin`.

**Journal.** Event types `erasure.requested` and `erasure.completed`; aggregate type `ErasureRequest`;
aggregate id `era_<ULID>` (the identity the frozen domain contract reserves; no table is added). Payload
keys, identities and counts only: `project_uid`, `actor_uid`, `reason_code`, `plan_sha256`,
`rows_deleted`, `blobs_exclusive`, `blobs_shared`, `objects_deleted`, `objects_missing`, `outcome`.
`product_purge.py` must keep the `erasure.` prefix (it stops on an event type nobody classified).

**What an erase does not reach**, and the operator is told so by the tool's closing message:

- manual dumps, mirrors and copies on the host (`infra/deploy/dumps/`, the copy directory), the VPS
  provider's snapshots, and any copy outside the host: the operator removes or ages them by hand
  and records that in the release record;
- the model provider and anything OpenRouter routed the text to (`A-2`), and the local copies of a remote
  executor;
- the disk blocks of a deleted object (there is no secure wipe), container logs, and exports a user
  already downloaded;
- the legal-hold question.

### 4. The purge of the closed beta's data at the release (`R-146m`)

`AD-09` (to be confirmed). At the 1.0 release the operator runs `infra/deploy/purge-product-data.sh`.
The tool has no selector for the removed AR v1 and v2 paths: it removes **all** product data, which is
the stated intent ("the production stand starts clean"), including the v3 beta runs and every other
section's test runs. It keeps accounts, the norm corpus, executor configuration and release notes, so
the operator reviews the account list afterwards and archives or purges the test accounts
(`archiveUser`, `purgeUser`). Preconditions: the owner confirms that the stand holds only test data
(`R-141c`: no real client document is uploaded to the closed beta); the tool's own verified dump is
taken first and is deleted by hand after the release is accepted; the rehearsal runs it on a restored
copy first. `KEEP_EVENT_PREFIXES` gains `access.` and `erasure.` in the same lane that introduces
those events (`ADR-0023`).

### 5. Egress to the model provider (`R-146e`, `R-146f`, `R-146n`)

OpenRouter is the base connection; `R-133` is unchanged. What leaves the host on a call: the system
prompt of the profile and the recorded text layer of the document being analysed (all pages in one
request for the text profiles; the target-only prompt parts and the retrieved norm text for an AR v3
check), and, once a stage is activated that sends them, selected PNG crops of pages. The source PDF is
not sent. No project name, file name, account name or run identity is in the body. The destination
is the administrator-configured connection; `AUDITMANAGER_EXECUTOR_ALLOWED_HOSTS` narrows it and stays
optional. Any other executor connection an administrator configures (a pull-channel runner, an SSH
host) receives the same payload; this ADR's statement covers the OpenRouter base only.

**Accepted risk A-2 (`R-146f`, `R-146n` item 4 not accepted).** The tree holds no provider terms, data
processing agreement, consent or data-handling policy. The product asks OpenRouter for no routing
restriction, no ban on retention or training, and no ban on model substitution (the last is caught
after the fact by `R-133`, which turns a different reported model into a typed failure, but the text
has already been sent). Document text therefore reaches OpenRouter and whichever provider it routes to,
which may retain or train on it. The owner bears this risk; it is not mitigated by anything in the
product. Proposed reopen trigger (`AD-16`, the architect's, to be confirmed): the first client who asks for
data-handling terms, any contract that promises confidentiality, or the owner's decision to accept
`R-146n` item 4.

### 6. Key-ring custody (`R-146n` item 7)

The ring is the only thing that lets the worker open a sealed connection secret (the OpenRouter key
under the `database` source). A restore of the database onto another host brings the connections back
as `secret_unreadable` until the ring is installed.

`AD-08` (to be confirmed): after the ring is generated, the operator makes one encrypted copy of
`provider.env` on a medium that is neither the VPS, nor the repository, nor the dump directory; the tool
for the encryption is the operator's, and the passphrase or recipient key is held by a different
means than the copy. The release record carries the date, the key ids and the SHA-256 of the ring line.
The copy is verified on a second machine by decrypting it and comparing
`sed -n 's/^AUDITMANAGER_SECRETS_KEYS=//p' provider.env | sha256sum` there and on the VPS. The copy is
redone after every rotation (`DEPLOYMENT_RUNBOOK.md` section 14). The ring is never put in a dump, in the
repository, in a message or in the output of `docker compose config`.

### 7. Manual copies and their limits (`R-146b`)

A manual copy is a `pg_dump` (everything in PostgreSQL: all client text, the password hashes, the
sealed secrets) and optionally a bucket mirror (every document). It is not encrypted, it sits on the
host's disk, and it does not contain the key ring. Consequences the operator must know: a copy
contains erased data until it is deleted (section 3); a restore brings back accounts and credentials
as they were, so every credential is revoked and default passwords are reported (`R-52`,
`ADR-0023`); there is no schedule and no recovery point (`A-1`, `ADR-0021`).

## Consequences

### Positive

- A client's data can be removed on request by a script that is tested, dry-runnable, journalled and
  safe to repeat.
- The erase reuses the classification and refusal discipline of the purge, so a new table cannot be
  forgotten silently.
- Nothing in the audit trail is rewritten or deleted by an erase.

### Negative / cost

- The erase is a destructive operator path that switches database guards off; a defect in it
  is a defect in the one place the append-only contract is overridden. It needs the mutation proofs
  the purge has.
- Erased data survives in every copy, in the provider's systems and on the disk blocks; "erased" in a
  client conversation means "removed from the live service", and the operator must say so.
- Keeping the SHA-256 of an erased document in a `blob` row lets anyone with the database confirm that a
  known file once existed (`AD-06`).
- The product asks the provider for nothing: whatever the provider does with the text is outside the
  product's reach (`A-2`).

## Alternatives considered

1. **Delete bytes only and keep findings and decisions** (the literal reading of the domain contract):
   leaves quoted client text in the database; rejected as the default, offered as the fallback.
2. **Delete the `blob` rows too.** Contradicts "metadata and checksums are retained"; not chosen,
   offered to the owner.
3. **An automatic TTL.** Declined by `R-146c`.
4. **An erase through the API (an administrator operation).** Needs a contract reseal and puts a
   trigger-disabling path behind the application role; rejected for 1.0, an operator script keeps the
   power on the host.
5. **Restrict routing to providers that do not retain or train, and ban substitution.** The package
   item the owner did not accept (`R-146n` item 4); recorded as `A-2`.

## Verification

- automated check/test (delivered by `PROD-07`, none exists today): `tests/integration/recovery/` tests
  that drive the tool on a populated lane database and prove, for each guard, that deleting its marked
  block makes the refusal disappear (the discipline of `tests/integration/recovery/test_product_purge.py`);
  a test that the keep rows are byte-identical by count and digest; a test that the trigger state is
  identical after a failed run; a test that a second `--apply` exits 0 and a `--resume` after a forced
  crash between the phases completes; a test that a shared Blob keeps its object
- mechanical checks at rest: `select count(*) from blob where state = 'erasure_pending'` is `0`;
  `select count(*) from project where project_uid = '<erased id>'` is `0` and an `erasure.completed`
  event names it
- manual/operational evidence: an erase rehearsal on a restored copy before the release (`PROD-17`)

## Revisit trigger

Replace this ADR when the legal-hold authority or the classification labels are decided, when a client
contract imposes a retention period or an erasure deadline, when an off-host copy is introduced
(erase must then reach it), when the owner accepts or rules on provider terms (`A-2`), or when
multi-organisation access is added (an erase would then need an organisation boundary, `ADR-0023`).
