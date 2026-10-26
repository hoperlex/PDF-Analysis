# Task AR-V3-BETA-REVIEW-FIXES-03 — close judge J7's findings on the pack-set tool and the map builder, and the sibling `$`-anchored validators

task_id: AR-V3-BETA-REVIEW-FIXES-03
status: completed in development candidate (lane branch `agent/ar-v3-beta-review-fixes-03`; not merged, not pushed); one sub-part of F4 (the `non_identity.py` validators) is not done because its file is outside the lane's allowed paths: see "Integrator action"

## Outcome

Four findings of the independent judge J7 on `AR-V3-BETA-REVIEW-FIXES-02` are re-proved against the base tree, and each is closed with tests that are red before and green after and one quoted mutation:

- **F1 (medium-low).** `promote_cli.load_bundle` binds the designation label of every mapped document, not only item ids and spans: the label in `request.json designations[]` must equal the one designation the reviewed map's targets carry for that document (several targets of one document must agree; a map that disagrees with itself is `map_invalid`). New reason `request_designations_differ_from_map`, exit 2, no runner built, nothing written. `plan` now prints `designation: <document_id> "<label>"` for every mapped document after the item lines.
- **F2 (low).** The request's `snapshot_id` must be the map's `norms_snapshot_id` (`request_snapshot_differs_from_map`; a map without one is `map_invalid`). The module docstring says that the `synthetic` flag is a guard against accidents, not a control against forgery.
- **F3 (low).** `map_pack.write_pack` claims each output path before its exclusive create and marks it created after: an interrupt that lands between the create and the old bookkeeping no longer leaves an empty file behind that makes the next run say `output_exists`; a stranger's file is still never removed.
- **F4 (low).** `parse_blob_id`, `require_snapshot_id` and `ArtifactRef` (`blob_id`, `sha256`) match the whole string (`fullmatch`); `"<valid>\n"` is refused. The remaining sites of the same shape are listed in the report; the `non_identity.py` validators need an integrator action.

## Depends on

- `AR-V3-BETA-REVIEW-FIXES-02` — completed (the binding, `ids.py` and `write_pack` this task builds on).
- `AR-V3-BETA-SET-TOOL-01` — completed `promote_cli`.
- `AR-V3-BETA-MAP-TOOL-01` — completed `map_pack`.

## Frozen inputs

- domain contract: sealed; no reseal. The pattern texts `BLOB_ID_PATTERN`, `SNAPSHOT_ID_PATTERN` (mirrored by the `0012` CHECK and by the analysis contract) are unchanged; only the way they are applied changed.
- API contract: `1.5.0`; unchanged.
- analysis/comparison/event contract: unchanged.
- migration head: `0032_ar_v3_run_group`; no migration.
- base commit: `4e6b0b4d4eeb4fc93d5209db248ed773bf7c3318` (`integration/ar-close-1026`).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

The three new refusal reasons of `promote_cli` are strings in one file; no maintained enumeration lists them.

## Captured premise evidence

- premise: each of the four findings reproduces on the base tree with a real snippet (the snippets are under "Premise scripts"; they were run with `git archive 4e6b0b4d src contracts` extracted into a scratch directory as the only code on the path, with the repository's `tests/fixtures/ar_v3_map_pack` as input). Judge J7's scripts (`t_bind.py`, `t_bundle.py`, `t_write.py`, `t_ids.py`) were read and their relevant cases re-created in these snippets.

### P-01 — F1 and F2: the label and the snapshot are not bound to the reviewed map

- captured_at: 2026-10-26
- command: `SCR=<scratch> LANE=<lane dir> python -I -c "import sys,runpy; sys.path.insert(0,'<base>/src'); runpy.run_path('premise_f1_f2.py', run_name='__main__')"`
- captured_output:
  ```text
  map synthetic flag: False | snapshot: ns_00000000000000000000SYNTH1
  map target designations: ['SYNTH-D1']
  F1 control: request designations = the map's                           ACCEPTED
  F1: request designations[].designation = 'FAKE-LABEL 1.2.3'            ACCEPTED
  F2: synthetic flag edited to false, request snapshot differs from the map's ACCEPTED
  F2: synthetic flag edited to false, same snapshot (policy snapshot not loaded) ACCEPTED
  ```
- interpretation: the F1 map of the synthetic fixture with its `synthetic` flag edited to `false` (and re-canonicalised, so the same map bytes and `map_sha256` as the request's `nrs_` identity) is accepted by `load_bundle` with a request whose `designations[0].designation` is `FAKE-LABEL 1.2.3` while the map's targets all say `SYNTH-D1`. That label is printed in every prompt row of the document and is a sort key, so the same map bytes would cite another norm. A request naming another snapshot than the map is accepted as well (the library compares them, but only after the database read of `plan`/`promote`). The last line is the residual of F2: `promote_cli` does not load the beta policy snapshot, so an edited synthetic map with its own consistent snapshot id still loads; that is what the docstring now states and the library (identity check, database read of the snapshot) and the reviewer's digests hold. At the lane tip the third and fourth lines read `REFUSED [request_designations_differ_from_map]` and `REFUSED [request_snapshot_differs_from_map]`; the control and the last line stay `ACCEPTED`.

### P-02 — F3: an interrupt right after the exclusive create leaves a file the rollback does not know

- captured_at: 2026-10-26
- command: `SCR=<scratch> LANE=<lane dir> python -I -c "import sys,runpy; sys.path.insert(0,'<base>/src'); runpy.run_path('premise_f3.py', run_name='__main__')"`
- captured_output:
  ```text
  interrupt right after create #1: raised KeyboardInterrupt; left in --out: ['scope-F1.map.json']
     re-run: REFUSED output_exists
  interrupt right after create #3: raised KeyboardInterrupt; left in --out: ['scope-A1.map.json']
     re-run: REFUSED output_exists
  interrupt right after create #7: raised KeyboardInterrupt; left in --out: ['pack-summary.json']
     re-run: REFUSED output_exists
  ```
- interpretation: with `Path.open` patched to create the real file and then raise `KeyboardInterrupt`, the file of that create (the only one the rollback has not heard of) stays and the next run is refused. The interrupt is injected inside `Path.open`, which leaves the same state as one that lands between its return and `created.append` (the file exists, the claim does not): it is a deterministic stand-in for a timing window, not a measured occurrence of one. At the lane tip all three print `left in --out: ABSENT` and `re-run: OK`.

### P-03 — F4: `$`-anchored validators accept one trailing newline

- captured_at: 2026-10-26
- command: `python -I -c "import sys,runpy; sys.path.insert(0,'<base>/src'); runpy.run_path('premise_f4.py', run_name='__main__')"`
- captured_output:
  ```text
  parse_blob_id('blob_<ULID>\n')                   ACCEPTED
  require_snapshot_id('ns_<ULID>\n')               ACCEPTED
  ArtifactRef(blob_id='blob_<ULID>\n')             ACCEPTED
  ArtifactRef(sha256='<hex>\n')                    ACCEPTED
  ArtifactRef(role='norm_source\n')  [listed, not changed] ACCEPTED
  CorrelationId.parse('abc-123\n')  [outside the lane] ACCEPTED
  Sha256.parse('<hex>\n')  [outside the lane]      ACCEPTED
  ```
- interpretation: `re.match` with a `$`-anchored pattern accepts one trailing newline. At the lane tip the first four lines read `refused`; the `role` line, which is listed and not changed (a role name is neither an identity nor a digest), and the two `non_identity.py` lines (outside the lane's paths) stay `ACCEPTED`. Pydantic `Field(pattern=...)` in `api/schemas/models.py` was measured too: its Rust regex refuses `blob_<ULID>\n`, so the API schemas are not affected. The brief's path `src/auditmanager/analysis/engine/non_identity.py` does not exist; the module it means is `src/auditmanager/shared/identity/non_identity.py` (see "Integrator action").

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

The reports of earlier tasks are immutable here. Statements in them that this task makes stale are listed in the report `AR-V3-BETA-REVIEW-FIXES-03.md` for the integrator.

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/norms/retrieval/promote_cli.py`
- `src/auditmanager/analysis/profiles/ar_v3/norm_map/map_pack.py`
- `src/auditmanager/storage/models.py`
- `src/auditmanager/norms/embedding/profile.py`
- `src/auditmanager/analysis/engine/result.py`
- `tests/integration/norms/retrieval/test_promote_cli.py`
- `tests/integration/norms/custody/test_promote_cli_db.py`
- `tests/contract/norm_map/test_map_pack.py`
- `tests/unit/shared/**`
- `tests/unit/storage/**`
- `tests/unit/norms/**`
- `tests/unit/analysis/**`
- `docs/program/tasks/AR-V3-BETA-REVIEW-FIXES-03.md`
- `docs/program/AR-V3-BETA-REVIEW-FIXES-03.md`

The lane brief also lists `src/auditmanager/analysis/engine/non_identity.py`; that file does not exist in the tree (the module is `src/auditmanager/shared/identity/non_identity.py`, which no brief path covers), so it is not listed above and was not created or edited. No other path was needed; the two existing test files that pin the map shape (`test_promote_cli.py`, `test_promote_cli_db.py`) and `test_map_pack.py` are in the list above and carry the fixture changes the new binding requires.

## Forbidden hotspots

`contracts/**`, `db/**`, `infra/**`, `Makefile`, root dependency and lock files, `src/auditmanager/bootstrap/**`, the rest of `src/**` (including `src/auditmanager/shared/identity/**`), `web/**`, `docs/program/DEBT_REGISTER.md`, `docs/program/CURRENT_STATE.md`, `docs/program/AR-V3-BETA-SET-TOOL-01.md` (the operator runbook), `origin/main`, tags, and the deployment host.

## Non-goals

- Importing the analysis profile (the beta policy snapshot) into the norms context to make `promote_cli` reject an edited synthetic map by snapshot: the boundary rule forbids it; the consistency check and the stated limit replace it.
- Any library change: `candidate.py`, `evidence_bridge.py` and `promotion.py` are untouched.
- Changing the sibling validators that are not an opaque identity or a digest (a role name, a metric key, header and line parsers): listed in the report only.
- Editing the operator runbook `AR-V3-BETA-SET-TOOL-01.md` (outside the allowed paths): the one-line change is described in the report.
- A directory-level atomic rename for `map_pack`, or survival of a SIGKILL in the middle of a write.

## Deliverables

- The fixes in the five source files above.
- New tests: `tests/unit/storage/test_blob_id_exactness.py`, `tests/unit/norms/test_snapshot_id_exactness.py`, `tests/unit/analysis/test_artifact_ref_exactness.py`; new cases in `test_promote_cli.py`, `test_promote_cli_db.py` and `test_map_pack.py`, whose map fixtures now carry `norms_snapshot_id` and a `designation` on every target (the shape `map_pack` writes).
- This task file and the report `docs/program/AR-V3-BETA-REVIEW-FIXES-03.md`.

## Required tests

All with `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <files>` from the lane directory (the repository `.venv` and `.env` linked in; DB files with the `.env` variables exported). The counts are in the report.

- `tests/integration/norms/retrieval/test_promote_cli.py`, `tests/contract/norm_map`, `tests/unit/shared`, `tests/unit/storage`, `tests/unit/norms`, `tests/unit/analysis`, `tests/contract/architecture`.
- Against the running integration stack only: `tests/integration/norms/custody/test_promote_cli_db.py`, `tests/integration/db/test_ar_v3_pack_seal.py`, `tests/integration/storage`, the whole `tests/integration/norms`, and the 30 integration/unit files that use `parse_blob_id`, `BLOB_ID_PATTERN` or `ArtifactRef`.
- The whole `tests/contract` once on the committed tree. The governance check of this file: `PYTHONPATH=src .venv/bin/python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/AR-V3-BETA-REVIEW-FIXES-03.md',encoding='utf-8').read())))"` prints `[]`.

## Integration contract

- `load_bundle` (and with it `plan` and `promote`) refuses with exit 2, nothing written and no runner built, these new reasons: `request_designations_differ_from_map` (the request's labels are not the map's designations for the mapped documents; the message gives counts, never a label or a document id), `request_snapshot_differs_from_map`. `map_invalid` now also covers a map without a `norms_snapshot_id`, a target without a text `designation`, a document with two different designations, and `mapped_document_ids` that are not the sorted documents of the targets (the shape `map_pack` writes).
- A bundle whose map was hand-made without these fields is no longer promotable. Every map `map_pack` writes has them.
- `plan` output gains `designation: <document_id> "<label>"` lines (JSON-quoted, so a label cannot start a line of the report), one per mapped document, sorted by document id, after the `item:` lines. Existing lines are unchanged.
- `map_pack.write_pack`: unchanged on success and on every earlier failure mode; an interrupt between a create and its bookkeeping now leaves the output directory as it was found.
- `parse_blob_id`, `require_snapshot_id`, `ArtifactRef.__post_init__`: a value with a trailing line break is refused (`InvalidBlobIdError`, `ValueError`, `ValueError`).

## Failure/idempotency/security cases

Every new refusal asserts its own reason, and the refusing path never builds a runner, opens a database or writes. Messages carry item ids or counts only. A map-pack failure or interrupt removes only what that call created: a stranger's file at an output name survives whether the create reported `FileExistsError` (even if the file is empty) or the interrupt came before the create (any non-empty file). Re-running any refused command after the cause is fixed behaves as a first run.

The one case the rollback cannot tell apart is a stranger's **empty regular file** that appears at one output name in the instant between the existence check and the create, together with an interrupt in that same instant: it is then removed as if it were the call's own unwritten leftover. This is stated in the `write_pack` docstring.

## Rollback / feature flag

Forward-revert the three commits of the lane; no data, migration or flag is involved.

## Handoff

- changed files: five source files, three edited and three new test files, this task and the report; the exact list is in the report.
- commands/results: see "Required tests"; mutation tables in the report.
- known limits: the `non_identity.py` integrator action below; the F3 ambiguity above; the `synthetic` flag is not a forgery control.
- integration notes: merge after `integration/ar-close-1026`; on a database lane re-run `test_promote_cli_db.py`.

## Integrator action — `non_identity.py` (outside this lane's paths)

`src/auditmanager/shared/identity/non_identity.py` line 43: `_PatternValue.__init__` validates `CorrelationId`, `IdempotencyKey`, `Sha256` and `PayloadFingerprint` with `type(self)._regex.match(value)` against `$`-anchored patterns that `contracts/domain/v1/identifiers.json` pins, so a value with one trailing newline constructs (measured in P-03). The pattern constants must not change; only the application does:

```diff
--- a/src/auditmanager/shared/identity/non_identity.py
+++ b/src/auditmanager/shared/identity/non_identity.py
@@ -40,7 +40,7 @@
     def __init__(self, value: str) -> None:
-        if not isinstance(value, str) or not type(self)._regex.match(value):
+        if not isinstance(value, str) or not type(self)._regex.fullmatch(value):
```

The patch was applied to a scratch copy of the module (not to the tree) and the four types then refuse `"<valid>\n"` and accept `"<valid>"`. The test to add with it (`tests/unit/shared/test_non_identity_exactness.py`, inside `tests/unit/shared/**`; it is not in this lane's commits because it would be red without the patch):

```python
import pytest

from auditmanager.shared.identity import IdentifierFormatError
from auditmanager.shared.identity.non_identity import (
    CorrelationId, IdempotencyKey, PayloadFingerprint, Sha256,
)


@pytest.mark.parametrize("value_type, plain", [
    (CorrelationId, "abc-123"), (IdempotencyKey, "abc-123"),
    (Sha256, "a" * 64), (PayloadFingerprint, "a" * 64),
])
def test_a_non_identity_value_is_the_whole_string(value_type: type, plain: str) -> None:
    assert value_type.parse(plain).value == plain
    for decorated in (plain + "\n", plain + "\r\n", "\n" + plain, plain + " "):
        with pytest.raises(IdentifierFormatError):
            value_type.parse(decorated)
```

Mutation for it: put `.match(value)` back; the `+ "\n"` case of all four parameters goes red.

## Premise scripts

`premise_f1_f2.py` (needs `LANE` = a checkout with `tests/fixtures/ar_v3_map_pack` and `SCR` = a scratch directory):

```python
import json, shutil, tempfile, os
from pathlib import Path
W = Path(os.environ["LANE"])
from auditmanager.analysis.profiles.ar_v3.norm_map import map_pack as mp
from auditmanager.norms.retrieval import promote_cli as pc
from auditmanager.norms.embedding import vectors
from auditmanager.shared.identity import NormRetrievalSetId

dec = mp.parse_decisions((W/"tests/fixtures/ar_v3_map_pack/synthetic-decisions.json").read_bytes())
maps = mp.build_scope_maps(dec, allow_synthetic=True)
vals = [0.0]*vectors.DIMENSIONS; vals[0] = 1.0
packed = vectors.pack(vals); b64 = vectors.to_base64(packed); vsha = vectors.sha256(packed)

def flip(entry, synthetic=False):
    m = json.loads(entry.data); m["synthetic"] = synthetic
    return mp.canonical_bytes(m)

def request_for(mapbytes, label=None, snapshot=None):
    m = json.loads(mapbytes)
    ident = {t["norm_document_id"]: t["designation"] for it in m["items"] for t in it["targets"]}
    items = [{"item_id": it["id"], "query_vector_base64": b64,
              "provenance": {"query_text_sha256": "a"*64, "query_vector_sha256": vsha},
              "targets": [{"document_id": t["norm_document_id"], "ordinal_first": t["ordinal_first"],
                           "ordinal_last": t["ordinal_last"]} for t in it["targets"]]} for it in m["items"]]
    return {"format": pc.REQUEST_FORMAT, "set_id": str(NormRetrievalSetId.new()),
            "snapshot_id": snapshot or m["norms_snapshot_id"], "reviewed_content_key": m["reviewed_content_key"],
            "embedding_build": m["embedding_build"], "chunking_profile": "characters-v1",
            "independently_checked_source_digest": "b"*64, "independently_checked_embedding_digest": "c"*64,
            "designations": [{"document_id": d, "slug": "s", "designation": label or ident[d]}
                             for d in m["mapped_document_ids"]],
            "items": items}

def run(label, mapbytes, req):
    d = Path(tempfile.mkdtemp(dir=os.environ["SCR"]))
    (d/"map.json").write_bytes(mapbytes)
    (d/"request.json").write_bytes(json.dumps(req, ensure_ascii=False).encode())
    try:
        pc.load_bundle(d, require_expected=False); got = "ACCEPTED"
    except pc.CliRefused as e:
        got = "REFUSED [" + e.reason + "]"
    print(f"{label:70s} {got}")
    shutil.rmtree(d)

mb = flip(maps.maps[0]); m = json.loads(mb)
print("map synthetic flag:", m["synthetic"], "| snapshot:", m["norms_snapshot_id"])
print("map target designations:", sorted({t["designation"] for it in m["items"] for t in it["targets"]}))
run("F1 control: request designations = the map's", mb, request_for(mb))
run("F1: request designations[].designation = 'FAKE-LABEL 1.2.3'", mb, request_for(mb, label="FAKE-LABEL 1.2.3"))
run("F2: synthetic flag edited to false, request snapshot differs from the map's", mb,
    request_for(mb, snapshot="ns_" + "0"*25 + "1"))
run("F2: synthetic flag edited to false, same snapshot (policy snapshot not loaded)", mb, request_for(mb))
```

`premise_f3.py`:

```python
import os, tempfile, shutil
from pathlib import Path
from unittest import mock
from auditmanager.analysis.profiles.ar_v3.norm_map import map_pack as mp
W = Path(os.environ["LANE"])
dec = mp.parse_decisions((W/"tests/fixtures/ar_v3_map_pack/synthetic-decisions.json").read_bytes())
maps = mp.build_scope_maps(dec, allow_synthetic=True)
base = Path(tempfile.mkdtemp(dir=os.environ["SCR"]))
real = Path.open
def interrupt_after(n):
    seen = {"i": 0}
    def patched(self, mode="r", *a, **k):
        handle = real(self, mode, *a, **k)
        if "x" in mode:
            seen["i"] += 1
            if seen["i"] == n:
                raise KeyboardInterrupt
        return handle
    return patched
for n in (1, 3, 7):
    d = base / f"n{n}"
    with mock.patch.object(Path, "open", interrupt_after(n)):
        try:
            mp.write_pack(d, maps, {"x": 1}); r = "OK"
        except BaseException as e:
            r = type(e).__name__
    left = sorted(p.name for p in d.iterdir()) if d.exists() else "ABSENT"
    print(f"interrupt right after create #{n}: raised {r}; left in --out: {left}")
    try:
        mp.write_pack(d, maps, {"x": 1}); print("   re-run: OK")
    except mp.MapPackRefused as e:
        print("   re-run: REFUSED", e)
shutil.rmtree(base)
```

`premise_f4.py`:

```python
from auditmanager.storage.models import parse_blob_id
from auditmanager.norms.embedding.profile import require_snapshot_id
from auditmanager.analysis.engine.result import ArtifactRef
from auditmanager.shared.identity import non_identity as ni

ULID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"

def probe(label, call):
    try:
        call()
        print(f"{label:48s} ACCEPTED")
    except Exception as exc:
        print(f"{label:48s} refused ({type(exc).__name__})")

good = dict(role="norm_source", blob_id="blob_" + ULID, sha256="a" * 64, size_bytes=1, media_type="application/pdf")
probe("parse_blob_id('blob_<ULID>\\n')", lambda: parse_blob_id("blob_" + ULID + "\n"))
probe("require_snapshot_id('ns_<ULID>\\n')", lambda: require_snapshot_id("ns_" + ULID + "\n"))
probe("ArtifactRef(blob_id='blob_<ULID>\\n')", lambda: ArtifactRef(**{**good, "blob_id": "blob_" + ULID + "\n"}))
probe("ArtifactRef(sha256='<hex>\\n')", lambda: ArtifactRef(**{**good, "sha256": "a" * 64 + "\n"}))
probe("ArtifactRef(role='norm_source\\n')  [listed, not changed]", lambda: ArtifactRef(**{**good, "role": "norm_source\n"}))
probe("CorrelationId.parse('abc-123\\n')  [outside the lane]", lambda: ni.CorrelationId.parse("abc-123\n"))
probe("Sha256.parse('<hex>\\n')  [outside the lane]", lambda: ni.Sha256.parse("a" * 64 + "\n"))
```
