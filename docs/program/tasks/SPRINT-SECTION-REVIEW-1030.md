# SPRINT-SECTION-REVIEW-1030

## Outcome
Actualsource-boundcriticandcorrector+normreview+fullcrosssourceanalysisbuildersadaptedfromoriginal,losslessglobalcollectionandreportdata.

## Frozen inputs
Baselinecd4dc8ca / API1.14.0(233paths259ops620schemas) / migration0043. OriginalPDF-proverka3c99481719218b9cfa7560886529916646c61939. Latestownerinstruction30Oct: onehourfinishmaximumcodeandpublishtodev, prioritysectionruns/originalparity, NOchecks/tests/builds/lint/compile/modelruns. Syntheticinputsownedbyanotherusersession: fixtures/** offlimits. Deadline11:48UTC/14:48MSK; lanehandback11:33UTC; integration11:35–11:48.

## Depends on
- HOTFIX-AR-PIPELINE-INT-1030

## Forbidden hotspots
Otherlaneownedfiles, contracts/**, migrations, rootdependency/lockfiles, globalstyles, origin/main/forcepush, productionservices/userdata, fixtures/**, tests/**. RootownsGit/integration/publicseams/costandbootstrap. No test/build/compile/lint or paidmodelcall.

## Deliverables
Actualconnectedruntimecode, preservedv1/v2policy, provenanceforcopiedoriginalsources, knownlimitsandshortlanereport. No claimedverificationPASS.

## Review commands
None: userexplicitlywaivedchecksforonehour. StaticreadingandGitpublicationmetadataonly.

## Rollback
Freshplanversionextended-review-v3; oldacceptedv1/v2retainhistoricalcalls. Disablefreshplanflagorforwardrevert; noextraunapprovedspending, nofakeexpertdecision/rawrewrite.

## Allowed paths
src/auditmanager/analysis/extended/workflow.py
src/auditmanager/analysis/extended/review.py
src/auditmanager/analysis/extended/original_review/**
docs/program/SPRINT-SECTION-REVIEW-1030.md

## Integration contract
RootsoleGitwriter/publisherorigin/devonly. v3authority: enabledtrue,plan_versionextended-review-v3,max_blocks1..1000,window_size16,max_windows1..63,reviewtrue,rules_sha256frozen. Per16-sourcewindowMAX6modelcalls=2blocks+1comprehensive+1norm+1critic+1corrector;unusedcallsnotspent. V3proceduresblock_analysis/comprehensive_analysis/finding_merge/norm_verification/finding_review/finding_correction/report_generation; savedwindowreceipts/coverage, unrevieweditemsretained. v1/v2unchanged. NoAPI/migrationchange; existingextendedreadresultcarriesnewfields. Coordinateexacthelperseamsdirectlybeforecoding.

Authoritative integration addendum after remote dev refresh: preserve incoming HOTFIX-FULL-ANALYSIS-1030 accepted v2 max_blocks="all" and legacy16 behavior. Fresh v3 selects the complete admitted source set: actual max_blocks≤1000, text_page_limit=PDFpages≤500, max_windows=MAXceil≤63, window_size16 and maximum6 additional calls/window. These are source-ingest ceilings, not a first128 selection. Review/context/output bounds still produce explicit partial coverage. Root owns merge/Git; source owners reconcile their files without tests. Incoming owner tests/UI/transport are preserved, not authored or run by this sprint.

## Required task fields

task_id: SPRINT-SECTION-REVIEW-1030

## Non-goals

No production deployment, main publication, acceptance claim, synthetic input generation, canonical promotion of visual candidates, expert decisions by a model, new OCR service, API/migration changes or verification in this window.
