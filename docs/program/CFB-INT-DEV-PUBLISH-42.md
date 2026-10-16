# CFB-INT-DEV-PUBLISH-42 — second W54/W56b/W57a development slice

The published dev41 base is
`6f1307412c94de45e67ffdeba71506dc5a0aa8fb`. Source commits
`16b0bdfa`, `99e3d55c` and `4918087a` were fetched from isolated local
clones and cherry-picked as `9f469ce7`, `6a946ca5` and `9b7c4dab`.
They had no conflicts and changed exactly their twelve allowed paths.

The W54 metadata preflight now accepts only a canonical embedding plan
under its own `content_key` directory with the frozen profile and named
batch files. It bounds the plan to 1 MiB and still does not verify vector
bytes, a DB snapshot or a bundle. The real read-only `bundle-export`
preflight refused `build_checkpoint_unavailable`.

W56b now verifies supplied `prepared.text_layer` canonical JSON bytes
against role, media type, size and SHA-256 in `ArtifactRef`, the version and
page count, then partitions the complete page text. The future caller must
still prove saved StageResult, current Attempt and bounded Blob read.

W57a prepares an unserved v3 draft system/user prompt from reviewed AR
sections, PDF/OCR context and only the selected normative prompt part. Full
rebinding paragraphs remain local. The profile, prompt bundle and model
effect remain unregistered; reviewed map, qualified W54 snapshot/set and
CAP-01 measured output cap are prerequisites for activation.

The combined W54/W56b/W57a/governance selection passed **112 tests**.
The API hash remains
`7257972c55bd5da5ba6c054dfc04703ebf01e81a71ad02fc9217058d2eedd388`
and the frozen 48/55/131 surface, 25 errors and migration head
`0023_norm_citations` are unchanged. No contract, migration, root
dependency, composition root, global style, served path, registered
provider/profile, production DB/S3, deployment workflow, main ref or tag
changes are part of this candidate.

Clean-tree handoff, fresh remote refs and exact dev publication are
completed by the integrator after this report is committed. R-135 defers
the complete beta gate for these unserved code slices. This report makes
no beta or corpus-publication claim.
