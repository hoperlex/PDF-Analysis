# SPRINT3-VERSIONS-1030

Unverified source candidate. The owner explicitly deferred every execution/check for this implementation window.

## Result

Fresh analytic version reports use planning revision `md-chunks-v1` / prompt revision `cmp-analytic/chunked-1`. An editable MD transition is transmitted in actual contiguous line chunks instead of the former single400k-character request/refusal. The target is80,000 characters per chunk, an individual line may be at most150,000 characters, and one transition may have at most256 chunks. Each chunk binds its real MD range and SHA-256. Every source line belongs to one transmission chunk, with no prefix truncation. A line or chunk count beyond these bounds is an explicit unavailable/failed part; input is not silently shortened.

The analyst and verifier operate on each real chunk through the existing routed comparison spend caller. Verification receives the actual complete chunk (below its150k source ceiling), bounded genuine related-source context and the checked analyst output. Closed reply shape, unique claim identity, exact verifier claim partition and shown source ranges are enforced. Every raw paid reply is saved before parsing or handling an overrun pause. Accepted analysis, verification, actual facts and warnings are persisted per chunk. Aggregate transition analysis/verification marks become `done` only after all known chunks finish.

## Cost and paid recovery

The estimate enumerates the actual chunk prompts and reserves the original two-attempt maximum separately for analyst and verifier: at most4 calls per chunk,8,000 output tokens per call. Verifier input reserves its actual300,000-character hard request ceiling; corrective feedback is bounded. Existing route/model consent, before-call ceilings and1.2x overrun behavior remain in the shared caller. The existing10USD/job hard ceiling is unchanged: a large metered estimate can be refused before start. Unmetered/recorded routes do not acquire a fabricated monetary amount.

Stable reply slots bind chunk identity, stage and attempt. Replaying a saved raw answer validates the request SHA and actual response SHA without another dispatch. A bounded job-wide journal query stops new work while another call is prepared/sent, refuses unknown effects, and refuses a completed/paid matching request whose response custody was lost. The caller-to-custody crash gap is therefore an explicit recovery refusal, not a blind paid resend. Proven unprocessed provider refusals retain the existing shared semantics. The source key binds the whole immutable MD, actual fact registry/records, chunk bounds, project/model/profile and new prompt revision. Existing client report keys and behavior remain unchanged.

Old analytic answers keep their stored content keys and replies. A queued/resumed old analytic part whose key does not match the new plan safely refuses before new spending; it is not rewritten into a larger authority. A fresh estimate/consent and report are required. New compatible completed parts can still be reused without a model call.

## Planned assembly

Assembly mode is selected from the actual source plan before consent. More than one editable chunk, more than eight transitions, or a hard-line chunk above80k selects `deterministic_chunk_sections`: zero composer-model calls and full programmatic assembly of every verified chunk. This avoids paying for all chunks and discovering only afterwards that one global composer prompt cannot contain them. A single bounded chunk may use the existing composer, with its full300k input ceiling and two-attempt maximum reserved; its paid replies also receive durable custody.

The deterministic document preserves every cleaned verifier result in its text artifact and displays all claims, verdicts, evidence ranges, assessment notes, candidates, questions and input problems in a genuine PDF appendix. The concise transition table is not a prefix selection of claims. It explicitly states that a global model ranking was not performed; an empty ranked list is not described as an absence of significant changes. Real source passports for all cited MD ranges are retained. Chunk range/hash and N/M character coverage are recorded in the report text and PDF, without asserting original-PDF verification or an expert decision.

The root-owned shared service adds the explicit `ReportAiMethod.can_run_without_model` opt-in for a genuine cached nonempty deterministic plan without refused units. This allows free assembly of reused/programmatic results with no invented model-call count. Other methods retain their previous zero-call refusal.

## Existing frozen surface

No API or migration changes. `ComparisonReportPart.facts` remains the existing four fact counts; warnings remain actual validation warnings. They are not reinterpreted as chunk counters. Exact chunk metadata is in internal `part.facts` and the existing generated report text/PDF. A new public detailed-progress read would require a later seal; the current UI can show only actual aggregate transition marks. `source_md` remains the original immutable input.

Internal metadata:

- `planning_revision`, `chunks`, `paid_replies`, `chunk_coverage` on report-part facts.
- Each chunk records stable ID/index, line range, real source SHA/chars, analysis/verification marks and checked results.
- `chunk_coverage`: total/analysed/verified chunks, total/verified characters, complete flag and actual range statuses.
- Generated report: `composition_mode`, `chunk_coverage`, `verified_chunk_sections`, `chunk_assembly_complete`.

## Changed files

- `src/auditmanager/comparison/report/chunks.py` (new).
- `src/auditmanager/comparison/report/plan.py`.
- `src/auditmanager/comparison/report/method.py`.
- `src/auditmanager/comparison/report/handler.py`.
- `src/auditmanager/comparison/report/repository.py`.
- `src/auditmanager/comparison/report/pdf/render.py`.
- This report.

The root alone owns the shared zero-call service seam and UI consumers. No other lane files, contracts, DDL/migrations, composition root, dependency/lock files, global styles, tests or fixtures were edited by this lane. No Git writes/tags/pushes were performed.

## Limits and integration

No tests, imports, compilation, lint/typecheck/build, browser, database, provider/model or fixture execution was performed. No PASS or operational correctness claim is made. The source size/line/chunk/request/response/PDF-child/Attempt limits can still explicitly prevent completion; all stored paid answers survive. Full20MiB input admission does not guarantee that every line arrangement fits the256-chunk planner. Failed/unknown effects need investigation or a separately authorised recovery, not automatic re-dispatch. Long PDFs can exceed existing renderer CPU/memory/file limits; this is not silently weakened.

Integrate with the root's `allow_zero_calls` opt-in and UI handling for genuine no-model assembly. Keep API1.14.0/migration0043 unchanged, preserve the source artifact, and publish only to dev under the root integration task. Rollback by forward reverting this planning revision; retain historical replies/artifacts and require fresh consent for any changed paid plan.
