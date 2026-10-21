# Task W56A-INT-CSV-CHARACTERIZATION-COMPAT-01 — compare historical CSV against additive columns

task_id: W56A-INT-CSV-CHARACTERIZATION-COMPAT-01

## Outcome

The wave-13 characterization still detects every changed legacy CSV byte while
accepting only W56a's two appended, empty severity cells in record 12. The
committed historical record is unchanged.

## Depends on

- `W56A-INT-CSV-SEVERITY-01` — completed additive exporter.
- `W56A-INT-CSV-PINS-SYNC-01` — completed current 19-column pins.
- `CFB-INT-PINS-AND-PLANS-02` — completed integration at this task's base.

## Frozen inputs

- base commit: `3a9b64c0796e6d61ad33a6c9f87ff842525712f6`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`, §A3.2 and §A4 DECIDE;
- API SHA-256 `fad81bc0355e4a5e6e4fdabf320fda2948a3c22b1254133862e0891bac1d1227`;
- error catalog SHA-256 `89e155fc3cc5330ba40c3696f0f6c0bcef6a670c14528c30812e588190c31ace`;
- analysis registry SHA-256 `bd1e5b91b350dd3a383eb92da48b2f7775cc8dd6315f5be515b2c1239453ba3a`;
- provider lock SHA-256 `2d99142445f5c3ee969b85de8ad0c8625a7a378dd4abfcc7fee4b5142d3a8cbd`;
- migration head `0022_findings_v2`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: record 12 holds tokenized historical 17-column bytes with five data
  rows; its stored `length` describes the pre-token capture and must not be
  confused with the decoded tokenized byte count.

### P-01 — record 12 shape on the exact base

- captured_at: 2026-10-15
- command: `../../../.venv/bin/python -c 'import base64,csv,hashlib,io,json,pathlib; r=json.loads(pathlib.Path("tests/characterization/w13_baseline/records/12-exportRunCsv.success.json").read_text()); b=base64.b64decode(r["response"]["body"]["base64"]); rows=list(csv.reader(io.StringIO(b.decode("utf-8-sig"),newline=""))); print(json.dumps({"case":r["case"],"tokenized_bytes":len(b),"pre_token_bytes":r["response"]["body"]["length"],"sha256":hashlib.sha256(b).hexdigest(),"widths":[len(row) for row in rows],"header":rows[0],"crlf":b.endswith(b"\r\n")},ensure_ascii=False))'`
- captured_output:
  ```text
  {"case": "12-exportRunCsv.success", "tokenized_bytes": 3973, "pre_token_bytes": 4409, "sha256": "b5c11af33e6e1886ebbdb9ffe2bd58e0149b1b6206beba3d05704ab371ba9422", "widths": [17, 17, 17, 17, 17, 17], "header": ["project_uid", "document_uid", "version_uid", "run_id", "run_state", "provider_mode", "finding_uid", "finding_observation_id", "category", "finding_text", "recommendation_text", "evidence_page", "evidence_quote", "current_verdict", "latest_comment", "latest_decision_id", "decision_recorded_at"], "crlf": true}
  ```
- interpretation: a narrow compatibility projection can add 27 header bytes
  and two delimiters per data row, 37 bytes total; this does not prove the
  live PostgreSQL journey's new body is byte-identical.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

Record 12 is read as immutable evidence. The in-memory comparator expectation
is an explicit, tested compatibility projection, not a record rewrite.

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `tests/characterization/w13_baseline/test_response_baseline.py`
- `docs/program/tasks/W56A-INT-CSV-CHARACTERIZATION-COMPAT-01.md`
- `docs/program/W56A-INT-CSV-CHARACTERIZATION-COMPAT-01.md`

## Forbidden hotspots

`tests/characterization/w13_baseline/records/**`, `journey.py`, runtime,
`contracts/**`, migrations, root dependencies and lock files, composition
root, global styles, `CURRENT_STATE.md`, Git refs, tags.

## Non-goals

No historical rebaseline, CSV serializer change, DB fixture change, live
acceptance claim or full gate.

## Deliverables

An explicit record-12-only in-memory compatibility expectation; pure tests
that reject malformed source shape and mutations to legacy bytes, BOM, CRLF
and appended cells; task result report.

## Required tests

- `../../../.venv/bin/python -m pytest -q tests/characterization/w13_baseline/test_response_baseline.py -k csv_compat` — pure no-DB compatibility probes;
- direct `governance_findings` check for this task;
- `../../../.venv/bin/python -m compileall -q tests/characterization/w13_baseline/test_response_baseline.py`;
- `git diff --check` and exact allowed-path proof;
- the full characterization suite on isolated PostgreSQL, deferred until DB available under `R-135`.

## Integration contract

Only record 12's expected body is projected from 17 to 19 columns in memory.
Every original byte remains in the same order and each of five rows gains
exactly `,,`; the header gains exactly `,severity,severity_proposed`. Header,
status, token substitution and O1 group comparison retain their existing
checks. The source record's pre-token `length` gains 37 for the projected
current body.

## Failure/idempotency/security cases

The projection refuses a changed case, header, body kind, BOM, CRLF shape,
row count or 17-column source row. Repeated projection of an already adapted
body refuses its 19-column header. The new severity cells must be empty for
the v1 journey; a nonempty value is reported as a byte difference.

## Rollback / feature flag

Revert this test-only compatibility projection if the additive CSV behavior
is reverted. No runtime feature flag applies.

## Handoff

- changed files: filled in result report
- commands/results: filled in result report
- known limits: live DB confirmation pending
- integration notes: keep historical record 12 unchanged
