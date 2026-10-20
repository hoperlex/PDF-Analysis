# CP-06 — Comparison deterministic core

## Preconditions

- Golden pair of document versions.
- Page preview/text representations available.

## Start record

Before testing record:

```text
candidate_commit:
contract_manifest:
migration_head:
backend_runtime:
frontend_runtime:
local_infra_versions:
tester:
started_at:
```

## Test cases

### MT06-01 — Create comparison

**Action**
Create pair and generate sheet-match suggestions.

**Expected**
Suggestion set versioned/rebuildable.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT06-02 — Approve link

**Action**
Approve one suggestion and manually alter another link.

**Expected**
Approved state has its own revision/actor.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT06-03 — Recompute suggestions

**Action**
Run recompute.

**Expected**
Approved/manual links and explicit unlinked state remain unchanged.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT06-04 — Deterministic exclusion/diff

**Action**
Run text exclusion + raw diff twice with same inputs/config.

**Expected**
Raw artifacts/checksums equal.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT06-05 — Source change

**Action**
Create a new source version/revision and rerun.

**Expected**
Old raw artifact remains immutable; new revision/source signature created.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT06-06 — Viewer/storage boundary

**Action**
Open side-by-side preview/diff and inspect network/API metadata.

**Expected**
No internal S3 object key/permanent public URL exposed.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

### MT06-07 — Upload a further version of one set

`W59-VERSION-UPLOAD-01` (`uploadDocumentVersion`).

**Action**
On a document screen (`/projects/{project_uid}/documents/{document_uid}`) choose a second
portal bundle under «Новая версия» and press «Загрузить новую версию». Repeat with a bare PDF,
then with a bundle over the envelope, then send the same accepted bundle twice in a row
(a double press).

**Expected**
The accepted bundle opens the new version at its stage-and-section panel: version number one
higher, no stage or section, the document's own title. The document screen lists both versions,
newest first; the project screen shows the new one as the document's current version; the older
version keeps its stage, section, runs and findings and can be compared with the new one once
both are classified and analysed. The bare PDF and the oversize bundle are refused with the same
messages as the first upload and publish nothing; the double press publishes one version.

**Record** `PASS / FAIL / BLOCKED`, actual result, safe evidence reference.

## Final acceptance checklist

- [ ] User-owned mappings survive recompute.
- [ ] Raw evidence deterministic per source/config.
- [ ] Derived page representations are rebuildable.

## Stop/cleanup

Stop the local stack using the documented command. Preserve only synthetic/anonymized evidence required by the checkpoint report. Remove temporary credentials/tokens and local fault-injection overrides.

## Result

A checkpoint cannot be tagged if any mandatory case is `FAIL` or unexplained `BLOCKED`. Open a blocking task; after fix, rerun affected case plus regression cases whose contracts/state were touched.
