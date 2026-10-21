# Task W56A-INT-RECORDED-CALL-FACTS-01 — retain exact replay call facts

task_id: W56A-INT-RECORDED-CALL-FACTS-01

## Outcome

One offline AR v2 replay retains the exact adapter response. A pure builder
checks its request, source binding, response digest, mode, usage and stop reason
and returns call facts with a caller-allocated model-call ID. The later durable
stage can use these facts without reading a mutable recording a second time.

## Depends on

- `W56A-INT-RECORDED-RESPONSE-BRIDGE-01` — completed exact-key offline replay.
- `W56A-INT-AR-V2-RECORDED-INPUT-01` — completed verified source binding.
- `W56A-INT-RECORDED-ARTIFACT-PREP-01` — completed observation bytes and provenance checks.
- `W56A-INT-ANALYSIS-PUBLIC-BOUNDARY-01` — completed findings-to-analysis boundary; the former deep import is already removed.

## Frozen inputs

- base commit: `6b84b4d5fbbd289fb956ee74490569aed71404de`;
- `origin/dev` at task read: `8f113f6b8987f2fb702872435f61999e143bdc50`;
- W56 plan SHA-256 `18a5a0c3615c513ac7e682f85ae29b16f70f901bf5a53581e90ba24ecd6e4694`;
- code-first order SHA-256 `5abd8574736ae4a8cf618f2aae7d7ac758ffeba7e11c59c6a602ea4fbf13898c`;
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

- premise: the replay's result kept hashes and parsed output but discarded the
  adapter's token and latency facts; the publisher's old deep import was
  already fixed, so a narrow replay facts bridge is the remaining independent slice.

### P-01 — replay loses usage and findings uses the public boundary

- captured_at: 2026-10-16
- command: `git show HEAD:src/auditmanager/analysis/profiles/ar_v2/recorded_response.py | sed -n '25,38p' && git show HEAD:src/auditmanager/findings/v2_publication.py | rg -n '^from auditmanager.analysis' && git ls-tree -r --name-only HEAD src/auditmanager/analysis/profiles/ar_v2/recorded_call.py tests/integration/analysis/test_ar_v2_recorded_call.py docs/program/tasks/W56A-INT-RECORDED-CALL-FACTS-01.md docs/program/W56A-INT-RECORDED-CALL-FACTS-01.md`
- captured_output:
  ```text
  @dataclass(frozen=True, slots=True)
  class RecordedReplayResult:
      model_id: str
      provider_mode: ProviderMode
      request_sha256: str
      source_binding_sha256: str
      response_sha256: str
      finished: FinishedV2Response


  def replay_recorded_response(
      *,
  19:from auditmanager.analysis.public import AR_V2_CATEGORIES, AR_V2_SEVERITIES, RejectedProposal
  ```
- interpretation: usage was unavailable after replay without another read;
  this task can add a pure facts builder without changing findings or the public seam.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/analysis/profiles/ar_v2/recorded_response.py`
- `src/auditmanager/analysis/profiles/ar_v2/recorded_call.py`
- `tests/integration/analysis/test_ar_v2_recorded_call.py`
- `docs/program/tasks/W56A-INT-RECORDED-CALL-FACTS-01.md`
- `docs/program/W56A-INT-RECORDED-CALL-FACTS-01.md`

## Forbidden hotspots

`contracts/**`, migrations, provider lock, existing v1 call/stage, analysis
public boundary, findings, run executor, journal/repository, API, recordings,
root dependencies/locks, composition root, global styles, `CURRENT_STATE.md`,
Git refs, tags and remote branches.

## Non-goals

No provider call, second recording read, monetary cost claim, DB/journal write,
StageResult, finding publication, live mode, runtime activation, full gate or
beta acceptance. These facts are not a complete `ModelCallRecord` because the
durable stage must set provider and cost policy.

## Deliverables

Retained replay response, pure checked facts builder, focused replay and
refusal tests, this task and result report.

## Required tests

- `../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/analysis/test_ar_v2_recorded_call.py tests/integration/analysis/test_ar_v2_recorded_response.py tests/integration/analysis/test_ar_v2_recorded_artifact.py` — pass;
- Python compilation, direct governance, frozen hashes, `git diff --check`
  and exact allowed-path proof — pass;
- full `make gate` deferred under R-135 and the parallel W55b release gate.

## Integration contract

`replay_recorded_response` makes exactly one `RecordedAdapter.complete` call
and retains its `ModelResponse`. `build_recorded_call_facts` accepts the
verified request/replay and a caller-allocated `ModelCallId`; it rechecks
response/source/request hashes, recorded mode and usage before returning
immutable call facts. The later stage must persist the same ID with the call
journal and artifact, decide provider/cost fields from approved policy, and
enforce run-level idempotency.

## Failure/idempotency/security cases

Wrong call identity, mode, model, request/source digest, response digest,
stop reason, negative or non-integer usage, or an unexpected reported cost
fails before facts are returned. Request parameters omit prompt text. The
function performs no side effect; repeating it with the same inputs is stable.

## Rollback / feature flag

Revert these five paths before runtime wiring. No data rollback or flag is
needed because no active behavior or schema changes.

## Handoff

- changed paths, checks and limitations: accompanying report;
- contracts: none;
- next: integrate only the five owned paths; durable call/StageResult work
  requires a separately owned task.
