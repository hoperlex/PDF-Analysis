# SPRINT-SECTION-INT-1030

## Outcome
Integratemaximumworkingsectionanalysisoriginalfeatureswithinonehourandpublishtodev.

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
docs/program/**
src/auditmanager/analysis/public.py
src/auditmanager/runs/preflight.py
src/auditmanager/runs/cost_policy.py
src/auditmanager/bootstrap/**
src/auditmanager/analysis/text/stage.py
src/auditmanager/analysis/text/windowed.py
src/auditmanager/analysis/text/prompt.py

## Integration contract
RootsoleGitwriter/publisherorigin/devonly. v3authority: enabledtrue,plan_versionextended-review-v3,max_blocks1..128,window_size16,max_windows1..8,reviewtrue,rules_sha256frozen. Per16-sourcewindowMAX6modelcalls=2blocks+1comprehensive+1norm+1critic+1corrector;unusedcallsnotspent. V3proceduresblock_analysis/comprehensive_analysis/finding_merge/norm_verification/finding_review/finding_correction/report_generation; savedwindowreceipts/coverage, unrevieweditemsretained. v1/v2unchanged. NoAPI/migrationchange; existingextendedreadresultcarriesnewfields. Coordinateexacthelperseamsdirectlybeforecoding.

Rootadditionalownedpath: src/auditmanager/analysis/extended/estimate.py providesactualsourceaccountingthroughanalysispublic, injectedreadonlyblobstoreinRunCostPreflight frombootstrapadapter. No directS3router/UI.

Rootowns jobs/extended_review.py and jobs/public.py additiveboundedhas_ambiguous_provider_effect(run_id) coveringprepared/response_received/outcome_unknown/abandoned beforefreshv3dispatch. NoDDL.

Rootowns analysis/text/artifact.py additiveempty_native_text_observations forimage-onlyv3: 0nativeobservations/0analysedpages/0modelcalls, normalgroundinggateactuallyrunsandterminalselectorremainsauthoritative. No fabricatedLLMresponseorcanonicalimagefinding.

Rootowns analysis/stages/document_context_build.py optionalvisual-onlyemptycontextadmission; normaltextbinding/lengthguardspreservedandnonemptytext+emptyindexstillrefused. Publichandler run_document_context_with_visual_pages onlyselectedbyfreshv3, olddefault unchanged.

Authoritativeseamaddendum: freshv3authorityalsofreezes section_code(currentconfirmedsectionatacceptedstart). RuntimeusesTHISforrules/hash/windowsection; mutablelaterVersionclassificationcannotreroutequeuedRun. v1/v2historicalpolicyunchanged.

Rootowns analysis/text/live.py tinySDKconstructorfix max_retries=0, matchingexistingDBAnthropicadapter. Paidretriesremainonlythedurableexplicitretryprotocol, neverhiddenSDKresends. No testsrun.

Hybridv3accounting: acceptedtext_page_limit=min(PDFpages,128); max_windows=max(ceil(max_blocks/16),ceil(text_page_limit/16)). SparseportalIMAGEcountdoesnotdropcomplexreviewofothernative/OCRpages. Still≤8windows/6callsperwindow. Roottransfers analysis/text/windowed.py and runs/executor.py forced-single-windowcustodytoRuntimeowneronlyforfreshv3; olddirectv1/v2pathskept.
