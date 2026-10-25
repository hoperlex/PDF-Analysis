# Task AR-V3-BETA-REVIEW-FIXES-02 — close the independent judges' findings on the pack loader, the set tool and the map builder

task_id: AR-V3-BETA-REVIEW-FIXES-02
status: completed in development candidate (lane branch `agent/ar-v3-beta-review-fixes-02`; not merged, not pushed)

## Outcome

Four findings of two independent judges are re-proved against the base tree and closed, each with a test that is red before and green after and one quoted mutation:

- **A (medium).** `promote_cli` binds the request to the reviewed map: `map.json` is parsed and, per item id, the `(norm_document_id, ordinal_first, ordinal_last)` spans of `request.json` must equal the map's exactly; a map flagged `synthetic`, and a map the binding cannot read, are refused. Same map bytes with spans widened by one paragraph used to give 8 prompt rows instead of 5 and a different set digest and was accepted.
- **B (low-medium).** An opaque id is the whole string: `ids.py` uses `fullmatch`, so `ndoc_<ULID>\n` and `nrs_<ULID>\n` no longer parse. `map_pack._ident` and the set tool's `set_id` check also refuse a line break without relying on the shared fix.
- **C (low).** The pack loader refuses a `builder_version` other than the retrieval-set builder constant (`builder_version_mismatch`) and any string or key that has no UTF-8 form (`manifest_string_encoding`), in the loader, in `seal_manifest` and in the seal scopes file.
- **D (low).** `map_pack write_pack` is all-or-nothing (a dangling symlink target is seen before anything is written; a failure or interrupt removes what the call created); a 5,000-digit integer, a 500,000-deep nesting, an unlistable bundle directory and a NUL byte in a path are typed refusals (exit 2) instead of tracebacks; the exit-status text of `promote_cli` is corrected.

## Depends on

- `AR-V3-BETA-PACK-INSTALL-01` — completed manifest loader and `v3_pack_cli`.
- `AR-V3-BETA-SET-TOOL-01` — completed `promote_cli`.
- `AR-V3-BETA-MAP-TOOL-01` — completed `map_pack`.

## Frozen inputs

- domain contract: sealed; no reseal.
- API contract: `1.5.0`, 92 paths / 104 operations / 300 schemas; unchanged. The status route's answer is unchanged; only manifests it could never have served safely are now refused at load.
- analysis/comparison/event contract: unchanged.
- migration head: `0032_ar_v3_run_group`; no migration.
- base commit: `809d5c733a92e62a6979103c5771b546d1217c03` (`integration/ar-close-1026`).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: each of the four findings reproduces on the base tree with a real snippet (the snippets are under "Premise scripts"; they were run against `git archive 809d5c73 src contracts` extracted into a scratch directory, with the repository's `tests/` on the working directory).

### P-01 — A: the request's spans are not bound to the reviewed map

- captured_at: 2026-10-26
- command: `PYTHONPATH=$BASE/src .venv/bin/python premise_a.py`
- captured_output:
  ```text
  widen=False: load_bundle ACCEPTED; map_sha256=b3b675f6a15d prompt rows=5 set_sha256=20ed9ee757e2
  widen=True: load_bundle ACCEPTED; map_sha256=b3b675f6a15d prompt rows=8 set_sha256=3dd347dbbc8e
  ```
- interpretation: the same `map.json` bytes (same `map_sha256`, hence the same `nrs_` identity inputs) with spans widened by one paragraph is accepted by `load_bundle` and builds a different set (8 rows, another digest) through the real `select_prompt_part` and `build_retrieval_set`. `candidate.py` compares only the set of document ids and the item ids. The judge's numbers (5 and 8) are reproduced exactly. At the lane tip the same script prints `REFUSED [map_synthetic]` for both lines because it uses the repository's synthetic fixture; the non-synthetic case is `test_the_set_tool_refuses_the_same_map_bytes_with_spans_widened_by_one_paragraph`.

### P-02 — B: a trailing newline parses as an opaque id

- captured_at: 2026-10-26
- command: `PYTHONPATH=$BASE/src .venv/bin/python premise_b.py`
- captured_output:
  ```text
  NormDocumentId NormDocumentId('ndoc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B\n')
  NormRetrievalSetId NormRetrievalSetId('nrs_01J9ZQ8K7NHVXW3T2R5M6P4Q8B\n')
  _ident -> 'ndoc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B\n'
  ```
- interpretation: `OpaqueId` anchors with `^...$` and matches with `re.match`, so one trailing newline passes; `map_pack._ident` returns it as acceptable. `evidence_bridge` (`\Z`) and `custody/roles.py` (`fullmatch`) refuse the same text, so a tool could say "acceptable" for an id the real path refuses.

### P-03 — C: an unselectable builder loads; a lone surrogate escapes untyped

- captured_at: 2026-10-26
- command: `PYTHONPATH=$BASE/src .venv/bin/python premise_c.py`
- captured_output:
  ```text
  1. builder_version=totally-wrong-builder loads; select_beta -> TrustedPack
     but every group start refuses it: invalid verified-set selection identity
  2. lone surrogate in a hashed field -> UnicodeEncodeError (not PackManifestRefused)
  3. lone surrogate in the attestation loads; reviewer = 'x\ud800'
     the status route's encode_json would raise: UnicodeEncodeError
  ```
- interpretation: `_scope` pre-checks `embedding_build` but not `builder_version`, which `select_verified_retrieval_set` refuses at every start, so the status read would say `installed` for a pack that can never start a group. `json.loads` turns an escaped lone surrogate into a `str` with no UTF-8 form: `TrustedPack.sha256` then raises `UnicodeEncodeError` (the composition root prints a raw traceback instead of its `ConfigurationError`), and in the unhashed attestation fields the manifest loads and the status route's `encode_json` fails.

### P-04 — D: partial output, and tracebacks instead of typed refusals

- captured_at: 2026-10-26
- command: `PYTHONPATH=$BASE/src .venv/bin/python premise_d.py`
- captured_output:
  ```text
  REFUSED: output_unwritable
  REFUSED: output_exists
  D1 first run rc 2 files: ['pack-summary.json', 'scope-A1.map.json', 'scope-A2.map.json', 'scope-F1.map.json', 'scope-F2.map.json', 'scope-S1.map.json', 'scope-S2.map.json']
  D1 re-run rc 2
  D3 traceback escapes: ValueError Exceeds the limit (4300 digits) for integer string conversion: value h
  D2 deep nesting escapes: RecursionError
  D2 listdir OSError escapes: PermissionError
  ```
- interpretation: with a dangling symlink `pack-summary.json` in `--out`, `write_pack` wrote the six maps, then refused `output_unwritable`; the re-run hit `output_exists` (the listing shows the symlink plus the six maps). A 5,000-digit integer escapes `map_pack` as a plain `ValueError`, a 500,000-deep `[` escapes `promote_cli` as `RecursionError`, and an `OSError` from `os.listdir` escapes it untyped: each ends in a traceback and exit 1 instead of a typed refusal and exit 2. At the lane tip the same script prints `REFUSED: output_exists` twice, `REFUSED: decisions_json_invalid`, `plan: REFUSED [request_invalid]` and `plan: REFUSED [bundle_unreadable]`, with exit 2 each and only the symlink left in `--out`.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

The three completed reports (`AR-V3-BETA-PACK-INSTALL-01.md`, `AR-V3-BETA-SET-TOOL-01.md`, `AR-V3-BETA-MAP-TOOL-01.md`) are immutable here. Statements in them that this task makes stale are listed in the report `AR-V3-BETA-REVIEW-FIXES-02.md` for the integrator.

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/runs/v3_pack_manifest.py`
- `src/auditmanager/runs/v3_pack_cli.py`
- `src/auditmanager/shared/identity/ids.py`
- `src/auditmanager/norms/retrieval/promote_cli.py`
- `src/auditmanager/norms/public.py`
- `src/auditmanager/analysis/profiles/ar_v3/norm_map/map_pack.py`
- `tests/integration/runs/test_v3_pack_manifest.py`
- `tests/integration/norms/retrieval/test_promote_cli.py`
- `tests/integration/norms/custody/test_promote_cli_db.py`
- `tests/contract/norm_map/test_map_pack.py`
- `tests/fixtures/ar_v3_map_pack/**`
- `tests/unit/shared/**`
- `tests/contract/identity/**`
- `docs/program/tasks/AR-V3-BETA-REVIEW-FIXES-02.md`
- `docs/program/AR-V3-BETA-REVIEW-FIXES-02.md`
- `tests/integration/api/test_ar_v3_pack_status_route.py`

The last path is the one extra path the lane brief allows for an existing test that pins the old behaviour: that test sealed a pack with `builder_version="synthetic-builder-9"`, which the loader now refuses; it uses the real builder constant instead (two lines). No other existing test pinned the old behaviour.

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, `infra/**`, `Makefile`, root dependency and lock files, `src/auditmanager/bootstrap/**`, `src/auditmanager/norms/retrieval/candidate.py`, `promotion.py` and the rest of the norms library, `web/**`, `docs/program/DEBT_REGISTER.md`, `docs/program/CURRENT_STATE.md`, `origin/main`, tags, and the deployment host.

## Non-goals

- The foreign-admission race between the guard and `dispatch()` and the attestation not being covered by `pack_sha256` (known limits `D-208`/`D-212`).
- Any library change: `candidate.py` still compares only the set of document ids; the binding lives in the tool, which is the only caller.
- Turning SIGTERM into an interrupt in `promote_cli`; the exit-status text is corrected instead.
- A directory-level atomic rename for `map_pack`; the all-or-nothing rollback does not cover a SIGKILL in the middle of a write (a partial pack then needs a manual removal; a re-run says `output_exists`).
- Promoting a real set, sealing a real pack, or any map content.

## Deliverables

- The fixes in the nine source files above (one new export, `SET_BUILDER_VERSION`, in `norms/public.py`).
- New tests and the changed fixtures of the existing tests in the five test files above, plus `tests/unit/shared/test_opaque_id_exactness.py`.
- This task file and the report `docs/program/AR-V3-BETA-REVIEW-FIXES-02.md`.

## Required tests

All with `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider <files>` from the lane directory (the repository `.venv` linked into it).

- `tests/unit/shared/test_opaque_id_exactness.py`: 4 passed.
- `tests/integration/runs/test_v3_pack_manifest.py`: 112 passed (base 97; the refusal table has 45 rows, base 42).
- `tests/integration/norms/retrieval/test_promote_cli.py`: 107 passed (base 61).
- `tests/contract/norm_map`: 117 passed (base 102).
- `tests/integration/composition/test_v3_pack_install.py` and `test_v3_worker_registry.py`, `tests/integration/api/test_ar_v3_pack_status_route.py`, `tests/contract/architecture`: passed.
- Against the running integration stack only (throwaway database and bucket per test): `tests/integration/norms/custody/test_promote_cli_db.py` 12 passed (11 + the new spans test), `tests/integration/db/test_ar_v3_pack_seal.py` 3 passed, `tests/integration/db/test_ar_v3_run_group.py` 5 passed.
- Every non-database test file that imports `shared.identity` (120 files outside `tests/integration/db`): the only failures are database/object-store set-up errors (no `DATABASE_URL` or `S3_*`) and two `test_v2_recorded_durable_stage.py` cases that fail identically on the base `ids.py` (a stale fake session in `jobs/repository.py`, unrelated).
- The whole `tests/contract` once at the end: 1,295 passed; the 82 failures and 126 errors are all in `test_cp00_candidate.py`, `test_validate_bootstrap.py` and `test_cp00_final_state.py` and are identical on a detached checkout of the base `809d5c73` (worktree `.git` file, missing `jsonschema` in a subprocess). `git diff --check` is clean; the governance check of this file prints `[]`.

## Integration contract

- `load_bundle` (and with it `plan` and `promote`) refuses with exit 2, nothing written and no runner built, these new reasons: `map_invalid` (not canonical JSON, not an object, no boolean `synthetic` flag, no items, an item without a unique id or without targets, a target that is not a document span), `map_synthetic`, `request_items_differ_from_map` (the request's item ids are not the map's, or repeat), `request_targets_differ_from_map` (a differing item is named, spans are not echoed). The order of one item's spans in the request is not a difference; their number and values are. A bundle whose map is not in the shape `map_pack` writes (items with `targets`, a boolean `synthetic`) is no longer promotable; the old reason for a non-canonical map (`promotion_refused`) is now `map_invalid`, still exit 2.
- The pack loader (`parse_manifest`, `load_manifest`, `seal_manifest`, the server start, `verify`, `seal`) adds the reasons `builder_version_mismatch` and `manifest_string_encoding`; the seal scopes file adds nothing new (`spec_value`). A manifest that loaded before only because nothing looked at its builder or its text encoding is now refused at start.
- `map_pack`: `write_pack` leaves the output directory as it was found when it fails; `output_exists` now also covers a dangling symlink; a JSON file that fails on a huge integer is the file's own `*_json_invalid` code.
- `shared.identity`: `parse` of any identity with a trailing line break raises `IdentifierFormatError`. `pattern_for` and the strings the migrations use are unchanged.
- `norms.public` exports one more name, `SET_BUILDER_VERSION`.

## Failure/idempotency/security cases

Every new refusal asserts its own reason, and the refusing path never builds a runner, never opens a database or the object store and never writes. A refusal message names the differing item ids and never a span, a document id or a manifest value. A map-pack failure removes only what that call created: a file that a stranger created between the check and the create is not removed. Re-running any refused command after the cause is fixed behaves as a first run.

## Rollback / feature flag

Forward-revert the five commits of the lane; no data, migration or flag is involved. The reverted tools return to the base behaviour listed in the premise evidence.

## Handoff

- changed files: nine source files, six test files (five edited, one new), this task and the report; the exact list is in the report.
- commands/results: see "Required tests"; mutation table in the report.
- known limits: the three listed under Non-goals; the tool-level binding does not check query vectors (they carry their own digest against the reviewer's recomputation, runbook step 4).
- integration notes: merge after `integration/ar-close-1026`; on a database lane re-run `test_promote_cli_db.py`, `test_ar_v3_pack_seal.py`, `test_ar_v3_run_group.py`. The reports of the three earlier tasks carry statements this task makes stale (listed in the report).

## Premise scripts

Each script is run from the repository root, with `BASE` a directory holding `git archive 809d5c73 src contracts`, so it reads the base code and the repository's current `tests/` helpers (which only build fixtures).

`premise_a.py`

```python
"""Finding A: the request's targets are not bound to the reviewed map."""
import hashlib, json, sys, tempfile, copy
from array import array
from pathlib import Path
sys.path.insert(0, "tests/contract/norm_map")
import test_map_pack as m
from auditmanager.norms.retrieval import promote_cli
from auditmanager.norms.retrieval.artifact import SetIdentity, SnapshotBinding, SourceParagraph, build_retrieval_set
from auditmanager.norms.retrieval.ranking import RetrievalItem, RetrievalParagraph, TargetSpan, select_prompt_part
from auditmanager.norms.embedding import vectors
from auditmanager.norms.embedding.profile import DIMENSIONS
from auditmanager.shared.identity import NormRetrievalSetId

maps = m._build()
paragraphs = m._paragraphs()
entry = maps.maps[0]          # F1
mapping = json.loads(entry.data)
packed = vectors.pack([1.0] + [0.0] * (DIMENSIONS - 1))

def request(widen):
    items = []
    for item in mapping["items"]:
        targets = []
        for t in item["targets"]:
            last = t["ordinal_last"]
            targets.append({"document_id": t["norm_document_id"], "ordinal_first": t["ordinal_first"],
                            "ordinal_last": last + (1 if widen else 0)})
        items.append({"item_id": item["id"], "query_vector_base64": vectors.to_base64(packed),
                      "provenance": {"query_text_sha256": "3" * 64, "query_vector_sha256": vectors.sha256(packed)},
                      "targets": targets})
    return {"format": promote_cli.REQUEST_FORMAT, "set_id": str(NormRetrievalSetId.new()),
            "snapshot_id": mapping["norms_snapshot_id"], "reviewed_content_key": mapping["reviewed_content_key"],
            "embedding_build": mapping["embedding_build"], "chunking_profile": "characters-v2:1000",
            "independently_checked_source_digest": "1" * 64, "independently_checked_embedding_digest": "2" * 64,
            "designations": [{"document_id": d, "slug": "s", "designation": "D"} for d in mapping["mapped_document_ids"]],
            "items": items}

rows_by = {}
for widen in (False, True):
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "bundle"; d.mkdir()
        (d / "map.json").write_bytes(entry.data)
        (d / "request.json").write_text(json.dumps(request(widen)), encoding="utf-8")
        try:
            loaded = promote_cli.load_bundle(d, require_expected=False)
        except promote_cli.CliRefused as exc:
            print(f"widen={widen}: load_bundle REFUSED [{exc.reason}] {exc.message}")
            continue
        mapped = set(mapping["mapped_document_ids"])
        rows = tuple(RetrievalParagraph(p.document_id, p.paragraph_id, p.designation, p.title, p.ordinal,
                                         p.clause_number, p.page_label, p.text, p.reliable)
                     for p in paragraphs.rows if p.document_id in mapped)
        sel = select_prompt_part(loaded.request.items, rows, ())
        blob = build_retrieval_set(
            identity=loaded.request.identity, map_bytes=entry.data,
            snapshot=SnapshotBinding(mapping["norms_snapshot_id"], mapping["reviewed_content_key"], "a"*64, mapping["embedding_build"], len(mapped)),
            selection=sel,
            paragraphs=tuple(SourceParagraph(r, hashlib.sha256(r.text.encode()).hexdigest()) for r in rows))
        n = len(json.loads(sel.prompt_part)["paragraphs"])
        print(f"widen={widen}: load_bundle ACCEPTED; map_sha256={entry.sha256[:12]} prompt rows={n} set_sha256={blob.sha256[:12]}")
```

`premise_b.py`

```python
from auditmanager.shared.identity import NormDocumentId, NormRetrievalSetId, NormsSnapshotId
from auditmanager.analysis.profiles.ar_v3.norm_map import map_pack
ulid = "01J9ZQ8K7NHVXW3T2R5M6P4Q8B"
for cls, prefix in ((NormDocumentId, "ndoc"), (NormRetrievalSetId, "nrs")):
    try:
        print(cls.__name__, repr(cls.parse(f"{prefix}_{ulid}\n")))
    except Exception as exc:
        print(cls.__name__, "refused", type(exc).__name__)
try:
    print("_ident ->", repr(map_pack._ident(f"ndoc_{ulid}\n", NormDocumentId, "bad")))
except Exception as exc:
    print("_ident refused", exc)
```

`premise_c.py`

```python
"""Finding C, three probes: wrong builder_version; lone surrogate in a hashed field; in an unhashed one."""
import json, sys
sys.path.insert(0, "tests/integration/runs")
import test_v3_pack_manifest as t
from auditmanager.norms.public import PromotionRefused, select_verified_retrieval_set
from auditmanager.runs.public import parse_manifest

doc = t._resigned({**t._document(), "scopes": [dict(s, builder_version="totally-wrong-builder") if i == 0 else s
                                                for i, s in enumerate(t._document()["scopes"])]})
parsed = parse_manifest(t._dump(doc))
print("1. builder_version=totally-wrong-builder loads; select_beta ->", type(parsed.registry.select_beta()).__name__)
try:
    select_verified_retrieval_set(None, identity=parsed.pack.scopes[0].identity,
                                  chunking_profile=parsed.pack.scopes[0].chunking_profile)
except PromotionRefused as exc:
    print("   but every group start refuses it:", exc)

doc = t._document()
doc["scopes"][0]["reviewed_content_key"] = "x\ud800"
try:
    parse_manifest(json.dumps(doc).encode("ascii"))
except Exception as exc:
    print("2. lone surrogate in a hashed field ->", type(exc).__name__, "(not PackManifestRefused)")

doc = t._document()
doc["review"]["reviewer"] = "x\ud800"
parsed = parse_manifest(json.dumps(doc).encode("ascii"))
print("3. lone surrogate in the attestation loads; reviewer =", ascii(parsed.review.reviewer))
try:
    json.dumps({"reviewer": parsed.review.reviewer}, ensure_ascii=False).encode("utf-8")
except UnicodeEncodeError as exc:
    print("   the status route's encode_json would raise:", type(exc).__name__)
```

`premise_d.py`

```python
import os, sys, tempfile, json
from pathlib import Path
from unittest import mock
from auditmanager.analysis.profiles.ar_v3.norm_map import map_pack
from auditmanager.norms.retrieval import promote_cli

FIX = Path("tests/fixtures/ar_v3_map_pack")
# D1: dangling symlink pack-summary.json in --out
with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "pack"; out.mkdir()
    os.symlink(Path(tmp) / "nowhere", out / "pack-summary.json")
    args = ["build", "--decisions", str(FIX / "synthetic-decisions.json"),
            "--paragraphs", str(FIX / "synthetic-paragraphs.json"), "--out", str(out), "--allow-synthetic"]
    rc1 = map_pack.main(args)
    print("D1 first run rc", rc1, "files:", sorted(p.name for p in out.iterdir()))
    rc2 = map_pack.main(args)
    print("D1 re-run rc", rc2)

# D3: 5000-digit integer
with tempfile.TemporaryDirectory() as tmp:
    big = Path(tmp) / "d.json"
    big.write_text('{"decision_version": ' + "1" * 5000 + "}")
    try:
        rc = map_pack.main(["build", "--decisions", str(big), "--paragraphs", str(big), "--out", str(Path(tmp) / "o")])
        print("D3 rc", rc)
    except BaseException as exc:
        print("D3 traceback escapes:", type(exc).__name__, str(exc)[:70])

# D2: promote_cli deep nesting and listdir
with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp) / "b"; d.mkdir()
    (d / "map.json").write_bytes(b'{"a":1}')
    (d / "request.json").write_bytes(b"[" * 500000)
    try:
        print("D2 deep rc", promote_cli.main(["plan", str(d)]))
    except BaseException as exc:
        print("D2 deep nesting escapes:", type(exc).__name__)
    with mock.patch.object(promote_cli.os, "listdir", side_effect=PermissionError(13, "denied")):
        try:
            print("D2 listdir rc", promote_cli.main(["plan", str(d)]))
        except BaseException as exc:
            print("D2 listdir OSError escapes:", type(exc).__name__)
```
